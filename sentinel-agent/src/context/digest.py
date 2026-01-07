"""
Campaign Memory Digest - compressed durable memory layer.

The digest is NOT the transcript. It stores:
- Hinge Index: situation -> choice -> consequence
- Standing Reasons: why each faction is where it is
- NPC Memory Anchors: durable memories only
- Open Threads: with trigger conditions

This provides persistent memory that survives context window trimming
and session boundaries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state.schema import Campaign, HingeMoment, DormantThread
    from .window import TranscriptBlock


@dataclass
class HingeEntry:
    """A summarized hinge moment for the digest."""
    session: int
    situation: str
    choice: str
    consequence: str  # What shifted
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session": self.session,
            "situation": self.situation,
            "choice": self.choice,
            "consequence": self.consequence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HingeEntry":
        """Create from dictionary."""
        return cls(
            session=data["session"],
            situation=data["situation"],
            choice=data["choice"],
            consequence=data["consequence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ThreadEntry:
    """A summarized dormant thread for the digest."""
    origin: str
    trigger_condition: str
    consequence: str
    severity: str
    created_session: int

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "origin": self.origin,
            "trigger_condition": self.trigger_condition,
            "consequence": self.consequence,
            "severity": self.severity,
            "created_session": self.created_session,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ThreadEntry":
        """Create from dictionary."""
        return cls(
            origin=data["origin"],
            trigger_condition=data["trigger_condition"],
            consequence=data["consequence"],
            severity=data["severity"],
            created_session=data["created_session"],
        )


@dataclass
class DigestSection:
    """A section of the digest."""
    name: str
    content: str
    max_tokens: int = 500


@dataclass
class CampaignDigest:
    """The compressed campaign memory."""
    hinge_index: list[HingeEntry] = field(default_factory=list)
    standing_reasons: dict[str, str] = field(default_factory=dict)  # faction -> reason
    npc_anchors: dict[str, list[str]] = field(default_factory=dict)  # npc_name -> memories
    open_threads: list[ThreadEntry] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    # Metadata for tracking
    session_count: int = 0
    total_hinges: int = 0
    total_faction_shifts: int = 0

    def to_prompt_text(self) -> str:
        """Format digest for prompt injection."""
        sections = []

        # Hinge Index
        if self.hinge_index:
            hinge_lines = []
            for h in self.hinge_index[-5:]:  # Last 5 hinges
                hinge_lines.append(
                    f"  S{h.session}: {h.situation[:40]}... -> {h.choice[:40]}..."
                )
                if h.consequence:
                    hinge_lines.append(f"    Effect: {h.consequence[:60]}")
            sections.append("HINGE INDEX:\n" + "\n".join(hinge_lines))

        # Standing Reasons
        if self.standing_reasons:
            standing_lines = []
            for faction, reason in self.standing_reasons.items():
                if reason:
                    standing_lines.append(f"  {faction}: {reason[:80]}")
            if standing_lines:
                sections.append("FACTION STANDING REASONS:\n" + "\n".join(standing_lines))

        # NPC Anchors
        if self.npc_anchors:
            npc_lines = []
            for npc_name, memories in list(self.npc_anchors.items())[:5]:  # Top 5 NPCs
                if memories:
                    mem_str = "; ".join(memories[:3])  # First 3 memories each
                    npc_lines.append(f"  {npc_name}: {mem_str[:100]}")
            if npc_lines:
                sections.append("NPC MEMORIES:\n" + "\n".join(npc_lines))

        # Open Threads
        if self.open_threads:
            thread_lines = []
            for t in self.open_threads[:5]:  # Top 5 threads
                thread_lines.append(
                    f"  [{t.severity.upper()}] {t.origin[:40]}..."
                )
                thread_lines.append(f"    Trigger: {t.trigger_condition[:60]}")
            sections.append("OPEN THREADS:\n" + "\n".join(thread_lines))

        if not sections:
            return "[No digest content yet]"

        return "\n\n".join(sections)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "hinge_index": [h.to_dict() for h in self.hinge_index],
            "standing_reasons": self.standing_reasons,
            "npc_anchors": self.npc_anchors,
            "open_threads": [t.to_dict() for t in self.open_threads],
            "last_updated": self.last_updated.isoformat(),
            "session_count": self.session_count,
            "total_hinges": self.total_hinges,
            "total_faction_shifts": self.total_faction_shifts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CampaignDigest":
        """Create from dictionary."""
        return cls(
            hinge_index=[HingeEntry.from_dict(h) for h in data.get("hinge_index", [])],
            standing_reasons=data.get("standing_reasons", {}),
            npc_anchors=data.get("npc_anchors", {}),
            open_threads=[ThreadEntry.from_dict(t) for t in data.get("open_threads", [])],
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.now(),
            session_count=data.get("session_count", 0),
            total_hinges=data.get("total_hinges", 0),
            total_faction_shifts=data.get("total_faction_shifts", 0),
        )


class DigestManager:
    """Manages digest generation and storage."""

    def __init__(self, campaigns_dir: Path | str | None = None):
        """
        Initialize digest manager.

        Args:
            campaigns_dir: Directory where campaign files are stored.
                          Defaults to ./campaigns
        """
        if campaigns_dir is None:
            campaigns_dir = Path("campaigns")
        self.campaigns_dir = Path(campaigns_dir)

    def generate(
        self,
        campaign: "Campaign",
        recent_blocks: list["TranscriptBlock"] | None = None,
    ) -> CampaignDigest:
        """
        Generate/update digest from campaign state and recent blocks.

        Uses template-based approach (no LLM required for v1).

        Args:
            campaign: The campaign to generate digest from
            recent_blocks: Optional recent transcript blocks for additional context

        Returns:
            CampaignDigest with extracted information
        """
        digest = CampaignDigest()
        digest.session_count = campaign.meta.session_count
        digest.last_updated = datetime.now()

        # Extract hinges from character history
        for char in campaign.characters:
            for hinge in char.hinge_history:
                entry = HingeEntry(
                    session=hinge.session,
                    situation=hinge.situation,
                    choice=hinge.choice,
                    consequence=hinge.what_shifted or "",
                    timestamp=hinge.timestamp,
                )
                digest.hinge_index.append(entry)
                digest.total_hinges += 1

        # Extract standing reasons from faction history
        from ..state.schema import HistoryType
        for entry in campaign.history:
            if entry.type == HistoryType.FACTION_SHIFT and entry.faction_shift:
                faction_name = entry.faction_shift.faction.value
                # Build reason from cause and result
                reason = (
                    f"{entry.faction_shift.from_standing.value} -> "
                    f"{entry.faction_shift.to_standing.value}: {entry.faction_shift.cause}"
                )
                # Keep most recent reason for each faction
                digest.standing_reasons[faction_name] = reason
                digest.total_faction_shifts += 1

        # Extract NPC memory anchors
        for npc in campaign.npcs.active + campaign.npcs.dormant:
            if npc.remembers:
                digest.npc_anchors[npc.name] = list(npc.remembers)
            # Also capture significant interactions
            if npc.interactions:
                interaction_summaries = []
                for inter in npc.interactions[-3:]:  # Last 3 interactions
                    if abs(inter.standing_change) >= 5:  # Significant change
                        interaction_summaries.append(
                            f"S{inter.session}: {inter.action[:40]} ({inter.standing_change:+d})"
                        )
                if interaction_summaries:
                    existing = digest.npc_anchors.get(npc.name, [])
                    digest.npc_anchors[npc.name] = existing + interaction_summaries

        # Extract open threads
        for thread in campaign.dormant_threads:
            severity_str = (
                thread.severity.value
                if hasattr(thread.severity, "value")
                else str(thread.severity)
            )
            entry = ThreadEntry(
                origin=thread.origin,
                trigger_condition=thread.trigger_condition,
                consequence=thread.consequence,
                severity=severity_str,
                created_session=thread.created_session,
            )
            digest.open_threads.append(entry)

        # Also include avoided situations as potential threads
        for avoided in campaign.avoided_situations:
            if not avoided.surfaced:
                severity_str = (
                    avoided.severity.value
                    if hasattr(avoided.severity, "value")
                    else str(avoided.severity)
                )
                entry = ThreadEntry(
                    origin=f"[AVOIDED] {avoided.situation}",
                    trigger_condition=avoided.what_was_at_stake,
                    consequence=avoided.potential_consequence,
                    severity=severity_str,
                    created_session=avoided.created_session,
                )
                digest.open_threads.append(entry)

        return digest

    def save(self, campaign_id: str, digest: CampaignDigest) -> Path:
        """
        Save digest to campaign directory.

        Args:
            campaign_id: Campaign ID (used for filename)
            digest: The digest to save

        Returns:
            Path to saved digest file
        """
        digest_dir = self.campaigns_dir / "digests"
        digest_dir.mkdir(parents=True, exist_ok=True)

        digest_path = digest_dir / f"{campaign_id}_digest.json"
        with open(digest_path, "w", encoding="utf-8") as f:
            json.dump(digest.to_dict(), f, indent=2, ensure_ascii=False)

        return digest_path

    def load(self, campaign_id: str) -> CampaignDigest | None:
        """
        Load existing digest.

        Args:
            campaign_id: Campaign ID

        Returns:
            CampaignDigest if found, None otherwise
        """
        digest_path = self.campaigns_dir / "digests" / f"{campaign_id}_digest.json"

        if not digest_path.exists():
            return None

        try:
            with open(digest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CampaignDigest.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def export_session_summary(
        self,
        campaign: "Campaign",
        session_num: int,
    ) -> str:
        """
        Export a session summary to markdown.

        Args:
            campaign: The campaign
            session_num: Session number to summarize

        Returns:
            Markdown-formatted session summary
        """
        lines = [
            f"# Session {session_num} Summary",
            f"Campaign: {campaign.meta.name}",
            f"Date: {datetime.now().strftime('%Y-%m-%d')}",
            "",
        ]

        # Find relevant history entries
        from ..state.schema import HistoryType
        session_entries = [
            e for e in campaign.history if e.session == session_num
        ]

        # Hinges
        hinges = [e for e in session_entries if e.type == HistoryType.HINGE]
        if hinges:
            lines.append("## Key Choices")
            for h in hinges:
                if h.hinge:
                    lines.append(f"- **{h.hinge.choice}**")
                    if h.hinge.what_shifted:
                        lines.append(f"  - Shifted: {h.hinge.what_shifted}")
            lines.append("")

        # Faction shifts
        shifts = [e for e in session_entries if e.type == HistoryType.FACTION_SHIFT]
        if shifts:
            lines.append("## Faction Changes")
            for s in shifts:
                lines.append(f"- {s.summary}")
            lines.append("")

        # Threads created this session
        new_threads = [
            t for t in campaign.dormant_threads
            if t.created_session == session_num
        ]
        if new_threads:
            lines.append("## New Consequence Threads")
            for t in new_threads:
                lines.append(f"- **{t.origin}**")
                lines.append(f"  - Trigger: {t.trigger_condition}")
            lines.append("")

        return "\n".join(lines)

    def prune_old_blocks(
        self,
        blocks: list["TranscriptBlock"],
        keep_count: int = 4,
    ) -> tuple[list["TranscriptBlock"], list["TranscriptBlock"]]:
        """
        Prune old transcript blocks, keeping only recent ones.

        Args:
            blocks: All transcript blocks
            keep_count: Number of recent blocks to keep

        Returns:
            Tuple of (kept_blocks, archived_blocks)
        """
        if len(blocks) <= keep_count:
            return blocks, []

        # Sort by timestamp
        sorted_blocks = sorted(blocks, key=lambda b: b.timestamp)

        # Always keep anchors (hinge-tagged blocks)
        anchors = [b for b in sorted_blocks if b.is_anchor]
        non_anchors = [b for b in sorted_blocks if not b.is_anchor]

        # Keep recent non-anchor blocks
        kept_non_anchors = non_anchors[-keep_count:]
        archived = non_anchors[:-keep_count] if len(non_anchors) > keep_count else []

        # Combine anchors and recent blocks
        kept = anchors + kept_non_anchors
        kept.sort(key=lambda b: b.timestamp)

        return kept, archived
