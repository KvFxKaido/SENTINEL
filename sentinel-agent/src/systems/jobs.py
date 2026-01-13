"""
Job board system for SENTINEL.

Handles job template loading, board refresh, job acceptance, and completion.
Extracted to a system module following the leverage.py pattern.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import TYPE_CHECKING

from ..state.schema import (
    ActiveJob,
    FactionName,
    JobBoard,
    JobStatus,
    JobTemplate,
    Location,
    MissionType,
    Region,
)
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.manager import CampaignManager


# Default job templates directory (can be overridden)
DEFAULT_JOBS_DIR = Path(__file__).parent.parent.parent / "data" / "jobs"


class JobSystem:
    """
    Manages job templates, board refresh, and job lifecycle.

    Requires a CampaignManager for state access and persistence.
    """

    def __init__(self, manager: "CampaignManager", jobs_dir: Path | None = None):
        self.manager = manager
        self.jobs_dir = jobs_dir or DEFAULT_JOBS_DIR
        self._templates: dict[str, JobTemplate] = {}
        self._templates_loaded = False

    @property
    def _campaign(self):
        return self.manager.current

    def load_templates(self) -> dict[str, JobTemplate]:
        """
        Load all job templates from JSON files.

        Returns dict of template_id -> JobTemplate.
        Templates are cached after first load.
        """
        if self._templates_loaded:
            return self._templates

        self._templates = {}

        if not self.jobs_dir.exists():
            # Create directory and starter templates if missing
            self._create_starter_templates()

        for json_file in self.jobs_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for job_data in data.get("jobs", []):
                    # Convert string faction names to enums
                    job_data["faction"] = FactionName(job_data["faction"])
                    job_data["type"] = MissionType(job_data["type"])
                    if "opposing_factions" in job_data:
                        job_data["opposing_factions"] = [
                            FactionName(f) for f in job_data["opposing_factions"]
                        ]
                    # Convert region string to enum if present
                    if "region" in job_data and job_data["region"]:
                        job_data["region"] = Region(job_data["region"])

                    template = JobTemplate(**job_data)
                    self._templates[template.id] = template
            except Exception as e:
                print(f"[JobSystem] Error loading {json_file}: {e}")

        self._templates_loaded = True
        return self._templates

    def get_template(self, template_id: str) -> JobTemplate | None:
        """Get a job template by ID."""
        self.load_templates()
        return self._templates.get(template_id)

    def can_afford_buy_in(self, template_id: str) -> tuple[bool, int, int]:
        """
        Check if player can afford a job's buy-in.

        Returns:
            (can_afford, buy_in_amount, player_credits)
        """
        template = self.get_template(template_id)
        if not template or not template.buy_in:
            return (True, 0, 0)  # No buy-in required

        if not self._campaign or not self._campaign.characters:
            return (False, template.buy_in, 0)

        char = self._campaign.characters[0]
        return (char.credits >= template.buy_in, template.buy_in, char.credits)

    def get_available_jobs(
        self,
        location: Location | None = None,
        faction_filter: FactionName | None = None,
    ) -> list[JobTemplate]:
        """
        Get jobs available based on location and standings.

        At Faction HQ: Only that faction's jobs
        At Safe House: All factions based on standing
        At Market: Wanderer jobs + cross-faction
        In Field/Transit: Limited selection (contacts reaching out)
        """
        if not self._campaign:
            return []

        self.load_templates()

        location = location or self._campaign.location
        faction_filter = faction_filter or self._campaign.location_faction

        available = []

        for template in self._templates.values():
            # Skip already completed or active jobs
            if template.id in self._campaign.jobs.completed:
                continue
            if any(j.template_id == template.id for j in self._campaign.jobs.active):
                continue
            if template.id in self._campaign.jobs.failed:
                # Failed jobs have cooldown - skip for now
                continue

            # Check faction filter (at HQ)
            if faction_filter and template.faction != faction_filter:
                continue

            # Check standing requirement
            standing = self._campaign.factions.get(template.faction)
            if standing.numeric_value < template.min_standing:
                continue

            # Location-based filtering
            if location == Location.MARKET:
                # Market shows Wanderer jobs + general jobs
                if template.faction != FactionName.WANDERERS:
                    # Also allow jobs with no strong faction ties
                    if "general" not in template.tags:
                        continue

            available.append(template)

        return available

    def refresh_board(self, count: int = 5) -> list[str]:
        """
        Refresh the job board with new available jobs.

        Args:
            count: Number of jobs to show on the board

        Returns:
            List of template IDs now available
        """
        if not self._campaign:
            return []

        available = self.get_available_jobs()

        # Random selection weighted by faction standing
        if len(available) <= count:
            selected = available
        else:
            # Weight by standing - better standing = higher chance
            weights = []
            for template in available:
                standing = self._campaign.factions.get(template.faction)
                # Convert standing (-50 to 50) to weight (1 to 10)
                weight = max(1, (standing.numeric_value + 60) / 10)
                weights.append(weight)

            selected = random.choices(available, weights=weights, k=count)
            # Remove duplicates while preserving order
            seen = set()
            selected = [t for t in selected if not (t.id in seen or seen.add(t.id))]

        # Update board
        self._campaign.jobs.available = [t.id for t in selected]
        self._campaign.jobs.last_refresh_session = self._campaign.meta.session_count

        self.manager.save_campaign()

        # Emit event
        get_event_bus().emit(
            EventType.JOB_BOARD_REFRESHED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            count=len(selected),
        )

        return self._campaign.jobs.available

    def accept_job(self, template_id: str) -> ActiveJob | None:
        """
        Accept a job from the board.

        Args:
            template_id: ID of the job template to accept

        Returns:
            The created ActiveJob, or None if invalid
        """
        if not self._campaign:
            return None

        template = self.get_template(template_id)
        if not template:
            return None

        # Check it's actually available
        if template_id not in self._campaign.jobs.available:
            return None

        # Handle buy-in if required
        buy_in_paid = None
        if template.buy_in:
            char = self._campaign.characters[0] if self._campaign.characters else None
            if not char:
                return None  # No character to pay buy-in
            if char.credits < template.buy_in:
                return None  # Insufficient credits
            # Deduct buy-in immediately — non-refundable
            char.credits -= template.buy_in
            buy_in_paid = template.buy_in

        # Create active job
        active = ActiveJob(
            template_id=template_id,
            title=template.title,
            faction=template.faction,
            objectives=template.objectives.copy(),
            reward_credits=template.reward_credits,
            reward_standing=template.reward_standing,
            opposing_factions=template.opposing_factions.copy(),
            opposing_penalty=template.opposing_penalty,
            accepted_session=self._campaign.meta.session_count,
            region=template.region,
            buy_in=buy_in_paid,
        )

        # Set deadline if template has time pressure
        if "urgent" in template.tags:
            active.due_session = self._campaign.meta.session_count + 1
        elif "2-3 sessions" in template.time_estimate:
            active.due_session = self._campaign.meta.session_count + 3

        # Move from available to active
        self._campaign.jobs.available.remove(template_id)
        self._campaign.jobs.active.append(active)

        self.manager.save_campaign()

        # Emit event
        get_event_bus().emit(
            EventType.JOB_ACCEPTED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            job_id=active.id,
            title=active.title,
            faction=active.faction.value,
        )

        return active

    def complete_job(self, job_id: str, success: bool = True) -> dict:
        """
        Complete a job and apply rewards/penalties.

        Args:
            job_id: ID of the active job
            success: Whether the job was successful

        Returns:
            Dict with applied changes
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        # Find the active job
        job = None
        for j in self._campaign.jobs.active:
            if j.id == job_id:
                job = j
                break

        if not job:
            return {"error": f"Job not found: {job_id}"}

        result = {
            "job_id": job_id,
            "title": job.title,
            "success": success,
            "credits": 0,
            "faction_changes": [],
        }

        if success:
            job.status = JobStatus.COMPLETED

            # Apply rewards
            if self._campaign.characters:
                char = self._campaign.characters[0]
                char.credits += job.reward_credits
                result["credits"] = job.reward_credits

            # Improve standing with job faction
            self.manager.shift_standing(
                job.faction,
                job.reward_standing,
                f"Completed job: {job.title}",
            )
            result["faction_changes"].append({
                "faction": job.faction.value,
                "change": f"+{job.reward_standing}",
            })

            # Worsen standing with opposing factions
            for opposing in job.opposing_factions:
                self.manager.shift_standing(
                    opposing,
                    -job.opposing_penalty,
                    f"Sided against them: {job.title}",
                )
                result["faction_changes"].append({
                    "faction": opposing.value,
                    "change": f"-{job.opposing_penalty}",
                })

            # Move to completed
            self._campaign.jobs.completed.append(job.template_id)

            get_event_bus().emit(
                EventType.JOB_COMPLETED,
                campaign_id=self._campaign.meta.id,
                session=self._campaign.meta.session_count,
                job_id=job_id,
                title=job.title,
            )
        else:
            job.status = JobStatus.FAILED

            # Penalty with job faction
            self.manager.shift_standing(
                job.faction,
                -1,
                f"Failed job: {job.title}",
            )
            result["faction_changes"].append({
                "faction": job.faction.value,
                "change": "-1",
            })

            # Move to failed
            self._campaign.jobs.failed.append(job.template_id)

            get_event_bus().emit(
                EventType.JOB_FAILED,
                campaign_id=self._campaign.meta.id,
                session=self._campaign.meta.session_count,
                job_id=job_id,
                title=job.title,
            )

        # Remove from active
        self._campaign.jobs.active = [
            j for j in self._campaign.jobs.active if j.id != job_id
        ]

        self.manager.save_campaign()
        return result

    def abandon_job(self, job_id: str) -> dict:
        """
        Abandon a job with standing penalty.

        Args:
            job_id: ID of the active job

        Returns:
            Dict with applied changes
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        job = None
        for j in self._campaign.jobs.active:
            if j.id == job_id:
                job = j
                break

        if not job:
            return {"error": f"Job not found: {job_id}"}

        job.status = JobStatus.ABANDONED

        # Standing penalty
        self.manager.shift_standing(
            job.faction,
            -2,  # Abandonment is worse than failure
            f"Abandoned job: {job.title}",
        )

        # Move to failed list (same cooldown as failed)
        self._campaign.jobs.failed.append(job.template_id)
        self._campaign.jobs.active = [
            j for j in self._campaign.jobs.active if j.id != job_id
        ]

        self.manager.save_campaign()

        get_event_bus().emit(
            EventType.JOB_ABANDONED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            job_id=job_id,
            title=job.title,
        )

        return {
            "job_id": job_id,
            "title": job.title,
            "faction": job.faction.value,
            "standing_penalty": -2,
        }

    def get_active_jobs(self) -> list[ActiveJob]:
        """Get all active jobs."""
        if not self._campaign:
            return []
        return self._campaign.jobs.active

    def check_overdue_jobs(self) -> list[ActiveJob]:
        """
        Check for jobs past their due date.

        Returns list of overdue jobs (caller should handle failure).
        """
        if not self._campaign:
            return []

        current_session = self._campaign.meta.session_count
        overdue = []

        for job in self._campaign.jobs.active:
            if job.due_session and current_session > job.due_session:
                overdue.append(job)

        return overdue

    def _create_starter_templates(self) -> None:
        """Create default job templates if none exist."""
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

        starter = {
            "jobs": [
                {
                    "id": "wanderer_supply_run",
                    "faction": "Wanderers",
                    "title": "Supply Run",
                    "type": "Escort",
                    "description": "Deliver supplies to a remote settlement. Simple work, honest pay.",
                    "objectives": ["Pick up cargo at market", "Deliver to destination", "Return safely"],
                    "reward_credits": 150,
                    "reward_standing": 1,
                    "opposing_factions": [],
                    "opposing_penalty": 0,
                    "time_estimate": "1 session",
                    "tags": ["general", "safe"],
                    "min_standing": -50,
                },
                {
                    "id": "syndicate_debt_collection",
                    "faction": "Steel Syndicate",
                    "title": "Debt Collection",
                    "type": "Investigation",
                    "description": "A settlement owes the Syndicate. Find out why they stopped paying.",
                    "objectives": ["Locate the settlement contact", "Determine reason for default", "Report back or resolve"],
                    "reward_credits": 200,
                    "reward_standing": 1,
                    "opposing_factions": ["Covenant"],
                    "opposing_penalty": 1,
                    "time_estimate": "1 session",
                    "tags": ["social", "investigation"],
                    "min_standing": -20,
                },
                {
                    "id": "nexus_signal_analysis",
                    "faction": "Nexus",
                    "title": "Signal Analysis",
                    "type": "Investigation",
                    "description": "Anomalous signals detected in Sector 44. Investigate and report.",
                    "objectives": ["Travel to Sector 44", "Locate signal source", "Document findings"],
                    "reward_credits": 300,
                    "reward_standing": 1,
                    "opposing_factions": ["Ghost Networks"],
                    "opposing_penalty": 1,
                    "time_estimate": "2-3 sessions",
                    "tags": ["tech", "investigation"],
                    "min_standing": -10,
                },
            ]
        }

        starter_file = self.jobs_dir / "starter.json"
        with open(starter_file, "w", encoding="utf-8") as f:
            json.dump(starter, f, indent=2)
