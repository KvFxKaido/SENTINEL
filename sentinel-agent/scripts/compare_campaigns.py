#!/usr/bin/env python3
"""
Cross-campaign comparison tool for SENTINEL.

Parses wiki overlay files from multiple campaigns and generates
comparative analysis to test whether "no correct answers" holds up.

Usage:
    python compare_campaigns.py [wiki_dir]

Output:
    wiki/campaigns/_meta/comparison_report.md
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class FactionShift:
    """A faction standing change."""
    faction: str
    from_standing: str
    to_standing: str
    cause: str
    session: int


@dataclass
class HingeMoment:
    """An irreversible choice."""
    description: str
    session: int


@dataclass
class Thread:
    """A dormant thread."""
    description: str
    session: int


@dataclass
class NPCInteraction:
    """An NPC relationship change."""
    npc: str
    faction: str
    direction: str  # "improved" or "worsened"
    session: int


@dataclass
class CampaignData:
    """Extracted data from a single campaign."""
    id: str
    name: str = ""
    sessions: int = 0
    hinges: list[HingeMoment] = field(default_factory=list)
    faction_shifts: list[FactionShift] = field(default_factory=list)
    threads: list[Thread] = field(default_factory=list)
    npc_interactions: list[NPCInteraction] = field(default_factory=list)

    @property
    def final_standings(self) -> dict[str, str]:
        """Get final faction standings from shift history."""
        standings = {}
        for shift in self.faction_shifts:
            standings[shift.faction] = shift.to_standing
        return standings


def parse_events_file(events_path: Path) -> CampaignData:
    """Parse a campaign's _events.md file."""
    campaign_id = events_path.parent.name
    data = CampaignData(id=campaign_id)

    if not events_path.exists():
        return data

    content = events_path.read_text(encoding="utf-8")
    current_session = 0

    # Parse session headers
    for line in content.split("\n"):
        line = line.strip()

        # Session header: ## Session N
        session_match = re.match(r"^## Session (\d+)", line)
        if session_match:
            current_session = int(session_match.group(1))
            data.sessions = max(data.sessions, current_session)
            continue

        # Event line: - (date) [TYPE]: description
        event_match = re.match(r"^- \([^)]+\) \[([A-Z]+)\]: (.+)$", line)
        if not event_match:
            # Try legacy format: - **Session N** (date) [TYPE]: description
            legacy_match = re.match(r"^- \*\*Session (\d+)\*\* \([^)]+\) \[([A-Z]+)\]: (.+)$", line)
            if legacy_match:
                current_session = int(legacy_match.group(1))
                event_type = legacy_match.group(2)
                description = legacy_match.group(3)
            else:
                continue
        else:
            event_type = event_match.group(1)
            description = event_match.group(2)

        # Parse by event type
        if event_type == "HINGE":
            data.hinges.append(HingeMoment(
                description=description,
                session=current_session,
            ))

        elif event_type == "FACTION":
            # Format: Faction Name: From → To. Cause — [[links]]
            faction_match = re.match(
                r"([^:]+): (\w+) → (\w+)\. (.+?)(?:\s*—|$)",
                description
            )
            if faction_match:
                data.faction_shifts.append(FactionShift(
                    faction=faction_match.group(1).strip(),
                    from_standing=faction_match.group(2),
                    to_standing=faction_match.group(3),
                    cause=faction_match.group(4).strip(),
                    session=current_session,
                ))

        elif event_type == "THREAD":
            data.threads.append(Thread(
                description=description,
                session=current_session,
            ))

        elif event_type == "NPC":
            # Format: Interaction with [[NPCs/Name|Name]] (Faction): relationship direction
            npc_match = re.match(
                r"Interaction with (?:\[\[NPCs/[^|]+\|)?([^\]]+)\]?\]? \(([^)]+)\): relationship (\w+)",
                description
            )
            if npc_match:
                data.npc_interactions.append(NPCInteraction(
                    npc=npc_match.group(1),
                    faction=npc_match.group(2),
                    direction=npc_match.group(3),
                    session=current_session,
                ))

    return data


def discover_campaigns(wiki_dir: Path) -> list[CampaignData]:
    """Find and parse all campaigns in the wiki."""
    campaigns_dir = wiki_dir / "campaigns"
    if not campaigns_dir.exists():
        return []

    campaigns = []
    for campaign_path in campaigns_dir.iterdir():
        if not campaign_path.is_dir():
            continue
        if campaign_path.name.startswith("_"):
            continue  # Skip _meta

        events_file = campaign_path / "_events.md"
        if events_file.exists():
            data = parse_events_file(events_file)
            if data.sessions > 0:  # Only include campaigns with actual events
                campaigns.append(data)

    return campaigns


def generate_report(campaigns: list[CampaignData], wiki_dir: Path) -> str:
    """Generate markdown comparison report."""
    lines = [
        "# Cross-Campaign Comparison Report",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        f"**Campaigns analyzed:** {len(campaigns)}",
        "",
    ]

    if not campaigns:
        lines.append("No campaigns with events found.")
        return "\n".join(lines)

    # Campaign overview
    lines.extend([
        "## Campaign Overview",
        "",
        "| Campaign | Sessions | Hinges | Faction Shifts | Threads |",
        "|----------|----------|--------|----------------|---------|",
    ])

    for c in sorted(campaigns, key=lambda x: x.sessions, reverse=True):
        lines.append(
            f"| {c.id} | {c.sessions} | {len(c.hinges)} | "
            f"{len(c.faction_shifts)} | {len(c.threads)} |"
        )

    lines.append("")

    # Faction divergence analysis
    lines.extend([
        "## Faction Divergence",
        "",
        "How different campaigns ended up with different faction relationships.",
        "",
    ])

    # Collect all factions mentioned
    all_factions: set[str] = set()
    for c in campaigns:
        for shift in c.faction_shifts:
            all_factions.add(shift.faction)

    if all_factions:
        # Build comparison table
        header = "| Faction |" + "|".join(f" {c.id} " for c in campaigns) + "|"
        separator = "|---------|" + "|".join("-" * (len(c.id) + 2) for c in campaigns) + "|"
        lines.extend([header, separator])

        for faction in sorted(all_factions):
            row = f"| {faction} |"
            for c in campaigns:
                standing = c.final_standings.get(faction, "Neutral")
                row += f" {standing} |"
            lines.append(row)

        lines.append("")

        # Divergence analysis
        lines.append("### Divergence Notes")
        lines.append("")

        for faction in sorted(all_factions):
            standings = [c.final_standings.get(faction, "Neutral") for c in campaigns]
            unique_standings = set(standings)

            if len(unique_standings) == 1:
                lines.append(f"- **{faction}**: All campaigns reached {standings[0]} ⚠️ *possible 'obvious' path*")
            elif len(unique_standings) == len(campaigns):
                lines.append(f"- **{faction}**: All campaigns diverged ✓ *good design*")
            else:
                lines.append(f"- **{faction}**: Mixed outcomes ({', '.join(unique_standings)})")

        lines.append("")

    # Hinge analysis
    lines.extend([
        "## Hinge Moments",
        "",
        "Irreversible choices across campaigns.",
        "",
    ])

    # Group hinges by similarity (simple keyword matching)
    hinge_clusters: dict[str, list[tuple[str, HingeMoment]]] = defaultdict(list)
    for c in campaigns:
        for h in c.hinges:
            # Use first few words as cluster key
            key_words = h.description.split()[:3]
            key = " ".join(key_words).lower()
            hinge_clusters[key].append((c.id, h))

    for cluster_key, hinges in sorted(hinge_clusters.items()):
        if len(hinges) > 1:
            lines.append(f"### Recurring: {cluster_key.title()}...")
            for campaign_id, h in hinges:
                lines.append(f"- **{campaign_id}** (S{h.session}): {h.description}")
            lines.append("")

    # Unique hinges
    lines.append("### Unique Hinges")
    lines.append("")
    for cluster_key, hinges in sorted(hinge_clusters.items()):
        if len(hinges) == 1:
            campaign_id, h = hinges[0]
            lines.append(f"- **{campaign_id}** (S{h.session}): {h.description}")

    lines.append("")

    # NPC interaction patterns
    lines.extend([
        "## NPC Relationships",
        "",
        "Which NPCs players engaged with and how.",
        "",
    ])

    npc_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"improved": 0, "worsened": 0})
    for c in campaigns:
        for npc in c.npc_interactions:
            npc_stats[npc.npc][npc.direction] += 1

    if npc_stats:
        lines.extend([
            "| NPC | Times Improved | Times Worsened | Tendency |",
            "|-----|----------------|----------------|----------|",
        ])

        for npc, stats in sorted(npc_stats.items()):
            improved = stats["improved"]
            worsened = stats["worsened"]
            if improved > worsened:
                tendency = "👍 Likeable"
            elif worsened > improved:
                tendency = "👎 Antagonistic"
            else:
                tendency = "⚖️ Balanced"
            lines.append(f"| {npc} | {improved} | {worsened} | {tendency} |")

        lines.append("")

    # Dormant threads
    lines.extend([
        "## Dormant Threads",
        "",
        "Consequences players are carrying forward.",
        "",
    ])

    for c in campaigns:
        if c.threads:
            lines.append(f"### {c.id}")
            for t in c.threads:
                lines.append(f"- (S{t.session}) {t.description}")
            lines.append("")

    # Design insights
    lines.extend([
        "## Design Insights",
        "",
    ])

    # Calculate metrics
    total_hinges = sum(len(c.hinges) for c in campaigns)
    total_shifts = sum(len(c.faction_shifts) for c in campaigns)

    if len(campaigns) >= 2:
        # Check for convergence (bad) vs divergence (good)
        convergent_factions = []
        divergent_factions = []

        for faction in all_factions:
            standings = [c.final_standings.get(faction, "Neutral") for c in campaigns]
            if len(set(standings)) == 1:
                convergent_factions.append(faction)
            else:
                divergent_factions.append(faction)

        convergence_ratio = len(convergent_factions) / len(all_factions) if all_factions else 0

        lines.append(f"- **Faction divergence rate:** {(1 - convergence_ratio) * 100:.0f}%")
        lines.append(f"- **Avg hinges per campaign:** {total_hinges / len(campaigns):.1f}")
        lines.append(f"- **Avg faction shifts per campaign:** {total_shifts / len(campaigns):.1f}")

        if convergence_ratio > 0.5:
            lines.append("")
            lines.append("⚠️ **Warning:** High faction convergence suggests some factions may have 'obvious' optimal paths.")
            lines.append(f"   Convergent factions: {', '.join(convergent_factions)}")

        if convergence_ratio < 0.3:
            lines.append("")
            lines.append("✓ **Good:** Low convergence indicates meaningful player agency in faction relationships.")

    lines.append("")

    return "\n".join(lines)


def main():
    # Determine wiki directory
    if len(sys.argv) > 1:
        wiki_dir = Path(sys.argv[1])
    else:
        # Try to find wiki relative to script
        script_dir = Path(__file__).parent
        wiki_dir = script_dir.parent.parent / "wiki"
        if not wiki_dir.exists():
            wiki_dir = Path("wiki")

    if not wiki_dir.exists():
        print(f"Error: Wiki directory not found: {wiki_dir}")
        sys.exit(1)

    print(f"Scanning campaigns in: {wiki_dir}")

    # Discover and parse campaigns
    campaigns = discover_campaigns(wiki_dir)
    print(f"Found {len(campaigns)} campaigns with events")

    for c in campaigns:
        print(f"  - {c.id}: {c.sessions} sessions, {len(c.hinges)} hinges, {len(c.faction_shifts)} shifts")

    # Generate report
    report = generate_report(campaigns, wiki_dir)

    # Write to _meta directory
    meta_dir = wiki_dir / "campaigns" / "_meta"
    meta_dir.mkdir(exist_ok=True)

    report_path = meta_dir / "comparison_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"\nReport written to: {report_path}")

    # Also print to stdout (handle encoding issues on Windows)
    print("\n" + "=" * 60 + "\n")
    try:
        print(report)
    except UnicodeEncodeError:
        # Fall back to ASCII-safe version
        safe_report = report.encode("ascii", errors="replace").decode("ascii")
        print(safe_report)


if __name__ == "__main__":
    main()
