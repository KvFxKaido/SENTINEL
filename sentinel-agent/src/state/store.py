"""
Campaign storage abstraction.

Separates persistence from domain logic for testability.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from .schema import Campaign


@runtime_checkable
class CampaignStore(Protocol):
    """
    Abstract storage interface for campaigns.

    Implementations:
    - JsonCampaignStore: File-based persistence (production)
    - MemoryCampaignStore: In-memory storage (testing)
    """

    def save(self, campaign: Campaign) -> None:
        """Persist a campaign."""
        ...

    def load(self, campaign_id: str) -> Campaign | None:
        """Load a campaign by ID. Returns None if not found."""
        ...

    def delete(self, campaign_id: str) -> bool:
        """Delete a campaign. Returns True if deleted."""
        ...

    def list_all(self) -> list[dict]:
        """List all campaigns with metadata."""
        ...

    def exists(self, campaign_id: str) -> bool:
        """Check if a campaign exists."""
        ...


class JsonCampaignStore:
    """
    File-based campaign storage using JSON.

    Features:
    - Automatic backup on save
    - Partial ID matching on load
    - Relative timestamp formatting
    """

    def __init__(self, campaigns_dir: Path | str = "campaigns"):
        self.campaigns_dir = Path(campaigns_dir)
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)

    def save(self, campaign: Campaign) -> None:
        """Save campaign to JSON file with backup."""
        campaign.save_checkpoint()

        campaign_file = self.campaigns_dir / f"{campaign.meta.id}.json"

        # Backup previous save
        if campaign_file.exists():
            backup = campaign_file.with_suffix(".json.bak")
            backup.write_text(campaign_file.read_text())

        # Write new save
        campaign_file.write_text(campaign.model_dump_json(indent=2))

    def load(self, campaign_id: str) -> Campaign | None:
        """
        Load campaign by ID or partial match.

        Supports:
        - Full UUID: "a1b2c3d4"
        - Partial prefix: "a1b2"
        """
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"

        if not campaign_file.exists():
            # Try partial match
            for f in self.campaigns_dir.glob("*.json"):
                if f.stem.startswith(campaign_id):
                    campaign_file = f
                    break

        if campaign_file.exists():
            data = json.loads(campaign_file.read_text())
            return Campaign.model_validate(data)

        return None

    def delete(self, campaign_id: str) -> bool:
        """Delete campaign file."""
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"

        if campaign_file.exists():
            campaign_file.unlink()
            return True

        return False

    def list_all(self) -> list[dict]:
        """
        List all campaigns sorted by modification time.

        Returns list of dicts with: id, name, session_count, phase, updated_at
        """
        campaigns = []

        for f in sorted(
            self.campaigns_dir.glob("*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        ):
            try:
                data = json.loads(f.read_text())
                meta = data.get("meta", {})

                updated = datetime.fromisoformat(
                    meta.get("updated_at", "2000-01-01")
                )

                campaigns.append({
                    "id": meta.get("id", f.stem),
                    "name": meta.get("name", "Unnamed"),
                    "session_count": meta.get("session_count", 0),
                    "phase": meta.get("phase", 1),
                    "updated_at": updated,
                })
            except (json.JSONDecodeError, KeyError):
                continue

        return campaigns

    def exists(self, campaign_id: str) -> bool:
        """Check if campaign file exists."""
        campaign_file = self.campaigns_dir / f"{campaign_id}.json"
        return campaign_file.exists()


class MemoryCampaignStore:
    """
    In-memory campaign storage for testing.

    No file I/O - all data lives in memory.
    """

    def __init__(self):
        self.campaigns: dict[str, Campaign] = {}

    def save(self, campaign: Campaign) -> None:
        """Store campaign in memory."""
        campaign.save_checkpoint()
        self.campaigns[campaign.meta.id] = campaign

    def load(self, campaign_id: str) -> Campaign | None:
        """Load campaign from memory."""
        # Direct match
        if campaign_id in self.campaigns:
            return self.campaigns[campaign_id]

        # Partial match
        for cid, campaign in self.campaigns.items():
            if cid.startswith(campaign_id):
                return campaign

        return None

    def delete(self, campaign_id: str) -> bool:
        """Remove campaign from memory."""
        if campaign_id in self.campaigns:
            del self.campaigns[campaign_id]
            return True
        return False

    def list_all(self) -> list[dict]:
        """List all campaigns in memory."""
        campaigns = []

        for campaign in self.campaigns.values():
            campaigns.append({
                "id": campaign.meta.id,
                "name": campaign.meta.name,
                "session_count": campaign.meta.session_count,
                "phase": campaign.meta.phase,
                "updated_at": campaign.meta.updated_at,
            })

        # Sort by updated_at descending
        campaigns.sort(key=lambda x: x["updated_at"], reverse=True)
        return campaigns

    def exists(self, campaign_id: str) -> bool:
        """Check if campaign exists in memory."""
        return campaign_id in self.campaigns

    def clear(self) -> None:
        """Clear all campaigns (test utility)."""
        self.campaigns.clear()
