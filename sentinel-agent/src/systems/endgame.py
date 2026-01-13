"""
Endgame system for SENTINEL.

Tracks campaign readiness for conclusion and manages the epilogue phase.
The system monitors accumulated play (hinges, arcs, faction extremes, thread
pressure) to suggest when a campaign might be ready to conclude.

Design philosophy: Player always chooses when to end. This system provides
visibility into narrative weight, not automatic termination.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..state.schema import (
    ArcStatus,
    CampaignStatus,
    Standing,
)
from ..state.event_bus import get_event_bus, EventType

if TYPE_CHECKING:
    from ..state.manager import CampaignManager
    from ..state.schema import Campaign, EndgameReadiness


class EndgameSystem:
    """
    Manages endgame detection and epilogue flow.

    Requires a CampaignManager for state access and persistence.
    """

    def __init__(self, manager: "CampaignManager"):
        self.manager = manager

    @property
    def _campaign(self) -> "Campaign | None":
        return self.manager.current

    def update_readiness(self) -> "EndgameReadiness | None":
        """
        Recalculate all readiness scores based on current campaign state.

        Call this after significant events (hinges, arc changes, faction shifts).

        Returns:
            Updated EndgameReadiness, or None if no campaign loaded
        """
        if not self._campaign:
            return None

        readiness = self._campaign.meta.endgame_readiness

        # Calculate individual scores
        readiness.hinge_score = self._calculate_hinge_score()
        readiness.arc_score = self._calculate_arc_score()
        readiness.faction_score = self._calculate_faction_score()
        readiness.thread_score = self._calculate_thread_score()

        # Update campaign status based on readiness
        old_status = self._campaign.meta.status
        if self._campaign.meta.status == CampaignStatus.ACTIVE:
            if readiness.overall_score >= 0.6:
                self._campaign.meta.status = CampaignStatus.APPROACHING_END

        # Emit event if status changed or scores updated significantly
        get_event_bus().emit(
            EventType.READINESS_UPDATED,
            campaign_id=self._campaign.meta.id,
            overall_score=readiness.overall_score,
            readiness_level=readiness.readiness_level,
            status_changed=(old_status != self._campaign.meta.status),
        )

        self.manager.save_campaign()
        return readiness

    def _calculate_hinge_score(self) -> float:
        """
        Score based on hinge count and thematic convergence.

        - Count contributes 70% (saturates at 7 hinges)
        - Thematic convergence contributes 30% (shared keywords across hinges)
        """
        if not self._campaign or not self._campaign.characters:
            return 0.0

        char = self._campaign.characters[0]
        if not char.hinge_history:
            return 0.0

        hinges = char.hinge_history
        count = len(hinges)

        # Base score from count (saturates at 7 hinges)
        count_score = min(1.0, count / 7)

        # Convergence bonus: check for keyword overlap across hinges
        convergence_bonus = self._calculate_hinge_convergence(hinges)

        return min(1.0, count_score * 0.7 + convergence_bonus * 0.3)

    def _calculate_hinge_convergence(self, hinges: list) -> float:
        """
        Detect thematic convergence across hinge moments.

        Returns a score 0.0-1.0 based on shared themes.
        """
        if len(hinges) < 2:
            return 0.0

        # Extract words from choices and reasoning
        all_words = []
        for hinge in hinges:
            text = f"{hinge.choice} {hinge.reasoning} {hinge.what_shifted}".lower()
            words = set(text.split())
            all_words.append(words)

        # Check for overlapping significant words across hinges
        # (Excluding common words)
        common_words = {"the", "a", "an", "to", "for", "of", "in", "on", "with", "by", "and", "or", "but", "is", "was", "were", "are", "been"}

        # Find words that appear in multiple hinges
        word_counts = {}
        for words in all_words:
            for word in words:
                if len(word) > 3 and word not in common_words:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Score based on how many words appear in multiple hinges
        recurring_words = [w for w, c in word_counts.items() if c >= 2]
        if not recurring_words:
            return 0.0

        # More recurring themes = higher convergence
        return min(1.0, len(recurring_words) / 5)

    def _calculate_arc_score(self) -> float:
        """
        Score based on arc acceptance and reinforcement.

        - Primary arc reinforcement contributes most (saturates at 8 reinforcements)
        - Multiple accepted arcs provide bonus (up to +0.2)
        """
        if not self._campaign or not self._campaign.characters:
            return 0.0

        char = self._campaign.characters[0]
        accepted_arcs = [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]

        if not accepted_arcs:
            return 0.0

        # Primary arc is the one with highest reinforcement
        primary = max(accepted_arcs, key=lambda a: a.times_reinforced)

        # Score from reinforcement (saturates at 8)
        reinforcement_score = min(1.0, primary.times_reinforced / 8)

        # Bonus for multiple accepted arcs
        multi_arc_bonus = min(0.2, (len(accepted_arcs) - 1) * 0.1)

        return min(1.0, reinforcement_score + multi_arc_bonus)

    def _calculate_faction_score(self) -> float:
        """
        Score based on faction relationship extremes.

        Having strong relationships (Allied or Hostile) with factions
        indicates character has made meaningful choices in the world.
        Saturates at 5 extreme relationships.
        """
        if not self._campaign:
            return 0.0

        standings = self._campaign.factions.standings

        # Count extreme standings (Allied or Hostile)
        extremes = 0
        for standing in standings.values():
            if standing.level in [Standing.ALLIED, Standing.HOSTILE]:
                extremes += 1

        # Score from extremes (saturates at 5 factions)
        return min(1.0, extremes / 5)

    def _calculate_thread_score(self) -> float:
        """
        Score based on dormant thread pressure.

        More threads and older threads indicate accumulated consequences
        waiting to be resolved. Perfect for epilogue surfacing.
        Saturates at pressure = 10.
        """
        if not self._campaign:
            return 0.0

        threads = self._campaign.dormant_threads
        if not threads:
            return 0.0

        current_session = self._campaign.meta.session_count

        # Calculate pressure from threads and their age
        total_pressure = 0.0
        for thread in threads:
            age = current_session - thread.created_session
            severity_mult = {
                "minor": 0.5,
                "moderate": 1.0,
                "major": 1.5
            }.get(thread.severity.value, 1.0)
            total_pressure += (1 + age * 0.1) * severity_mult

        # Saturates at pressure = 10
        return min(1.0, total_pressure / 10)

    def track_player_goal(self, goal: str) -> None:
        """
        Track a player-stated goal from debrief fourth question.

        Args:
            goal: The player's answer to "What would 'enough' look like?"
        """
        if not self._campaign:
            return

        readiness = self._campaign.meta.endgame_readiness

        # Avoid duplicates, keep last 5 goals
        if goal and goal not in readiness.player_goals:
            readiness.player_goals.append(goal)
            if len(readiness.player_goals) > 5:
                readiness.player_goals.pop(0)

        self.manager.save_campaign()

    def begin_epilogue(self) -> dict:
        """
        Transition campaign to epilogue phase.

        The epilogue surfaces all dormant threads and prepares for
        final hinges and campaign conclusion.

        Returns:
            Dict with epilogue info or error
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        # Check minimum readiness
        readiness = self._campaign.meta.endgame_readiness
        if readiness.overall_score < 0.4:
            return {
                "error": "Campaign not ready for epilogue",
                "readiness": readiness.overall_score,
                "suggestion": "Continue playing to accumulate more narrative weight.",
            }

        # Already in epilogue?
        if self._campaign.meta.status == CampaignStatus.EPILOGUE:
            return {
                "error": "Campaign already in epilogue",
                "epilogue_session": self._campaign.meta.epilogue_session,
            }

        # Already concluded?
        if self._campaign.meta.status == CampaignStatus.CONCLUDED:
            return {"error": "Campaign already concluded"}

        # Transition to epilogue
        self._campaign.meta.status = CampaignStatus.EPILOGUE
        self._campaign.meta.epilogue_session = self._campaign.meta.session_count

        # Gather all dormant threads for surfacing
        threads_to_surface = []
        for thread in self._campaign.dormant_threads:
            threads_to_surface.append({
                "id": thread.id,
                "description": thread.description,
                "severity": thread.severity.value,
                "created_session": thread.created_session,
                "potential_consequence": thread.potential_consequence,
            })

        self.manager.save_campaign()

        # Emit event
        get_event_bus().emit(
            EventType.EPILOGUE_STARTED,
            campaign_id=self._campaign.meta.id,
            session=self._campaign.meta.session_count,
            thread_count=len(threads_to_surface),
        )

        return {
            "status": "epilogue_started",
            "session": self._campaign.meta.session_count,
            "threads_to_surface": threads_to_surface,
            "readiness": readiness.overall_score,
            "player_goals": readiness.player_goals,
        }

    def cancel_epilogue(self) -> dict:
        """
        Cancel epilogue and return to active play.

        Only valid if in epilogue phase.

        Returns:
            Dict with result or error
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        if self._campaign.meta.status != CampaignStatus.EPILOGUE:
            return {"error": "Campaign not in epilogue phase"}

        # Return to approaching_end (since we know readiness was high enough)
        self._campaign.meta.status = CampaignStatus.APPROACHING_END
        self._campaign.meta.epilogue_session = None

        self.manager.save_campaign()

        return {
            "status": "epilogue_cancelled",
            "new_status": CampaignStatus.APPROACHING_END.value,
        }

    def conclude_campaign(self) -> dict:
        """
        Mark campaign as concluded after epilogue completion.

        Returns:
            Dict with final summary data
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        if self._campaign.meta.status not in [CampaignStatus.EPILOGUE, CampaignStatus.APPROACHING_END]:
            return {"error": "Campaign must be in epilogue or approaching_end phase to conclude"}

        self._campaign.meta.status = CampaignStatus.CONCLUDED
        self.manager.save_campaign()

        # Emit event
        get_event_bus().emit(
            EventType.CAMPAIGN_CONCLUDED,
            campaign_id=self._campaign.meta.id,
            session_count=self._campaign.meta.session_count,
        )

        # Generate summary data
        summary = self._generate_campaign_summary()
        return summary

    def _generate_campaign_summary(self) -> dict:
        """
        Generate a comprehensive campaign summary for the conclusion.
        """
        if not self._campaign:
            return {}

        char = self._campaign.characters[0] if self._campaign.characters else None
        readiness = self._campaign.meta.endgame_readiness

        # Find primary arc if any
        primary_arc = None
        if char:
            accepted_arcs = [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]
            if accepted_arcs:
                primary_arc = max(accepted_arcs, key=lambda a: a.times_reinforced)

        # Collect faction standings
        faction_standings = {}
        for faction, standing in self._campaign.factions.standings.items():
            faction_standings[faction.value] = {
                "level": standing.level.value,
                "numeric": standing.numeric_value,
            }

        # Collect significant NPCs (those with interactions)
        significant_npcs = []
        for npc in self._campaign.npcs.active:
            if npc.interactions:
                significant_npcs.append({
                    "name": npc.name,
                    "faction": npc.faction.value if npc.faction else "Independent",
                    "disposition": npc.disposition.value,
                    "interaction_count": len(npc.interactions),
                })

        return {
            "status": "concluded",
            "campaign_name": self._campaign.meta.name,
            "session_count": self._campaign.meta.session_count,
            "character": {
                "name": char.name if char else "Unknown",
                "background": char.background.value if char else None,
                "hinge_count": len(char.hinge_history) if char else 0,
                "hinges": [
                    {
                        "session": h.session,
                        "choice": h.choice,
                        "what_shifted": h.what_shifted,
                    }
                    for h in (char.hinge_history if char else [])
                ],
            },
            "primary_arc": {
                "type": primary_arc.arc_type.value if primary_arc else None,
                "title": primary_arc.title if primary_arc else None,
                "times_reinforced": primary_arc.times_reinforced if primary_arc else 0,
            },
            "faction_standings": faction_standings,
            "significant_npcs": significant_npcs,
            "player_goals": readiness.player_goals,
            "final_readiness": readiness.overall_score,
        }

    def get_readiness_display(self) -> dict:
        """
        Get formatted readiness information for display.

        Returns:
            Dict with all readiness data formatted for UI
        """
        if not self._campaign:
            return {"error": "No campaign loaded"}

        readiness = self._campaign.meta.endgame_readiness

        return {
            "status": self._campaign.meta.status.value,
            "overall_score": readiness.overall_score,
            "readiness_level": readiness.readiness_level,
            "readiness_message": readiness.readiness_message,
            "scores": {
                "hinges": {
                    "score": readiness.hinge_score,
                    "label": "Hinges",
                    "description": "Irreversible choices made",
                },
                "arcs": {
                    "score": readiness.arc_score,
                    "label": "Arcs",
                    "description": "Character development",
                },
                "factions": {
                    "score": readiness.faction_score,
                    "label": "Factions",
                    "description": "Extreme relationships",
                },
                "threads": {
                    "score": readiness.thread_score,
                    "label": "Threads",
                    "description": "Pending consequences",
                },
            },
            "player_goals": readiness.player_goals,
            "goals_met": readiness.goals_met,
            "can_begin_epilogue": readiness.overall_score >= 0.4,
            "epilogue_session": self._campaign.meta.epilogue_session,
        }
