"""
Character arc detection system for SENTINEL.

Analyzes campaign history to detect emergent character arcs based on
patterns in hinge moments, faction shifts, and NPC interactions.
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..state.manager import CampaignManager
    from ..state.schema import CharacterArc


class ArcSystem:
    """
    Detects and manages character arcs.

    Requires a CampaignManager for state access and persistence.
    """

    def __init__(self, manager: "CampaignManager"):
        self.manager = manager

    @property
    def _campaign(self):
        return self.manager.current

    def detect_arcs(self, character_id: str | None = None) -> list[dict]:
        """
        Analyze campaign history to detect emergent character arcs.

        Looks for patterns in hinge moments, faction shifts, and NPC interactions
        to identify consistent behavioral themes.

        Args:
            character_id: Optional character ID (defaults to first character)

        Returns:
            List of detected arc candidates with strength scores
        """
        from ..state.schema import ArcType, ARC_PATTERNS, CharacterArc, ArcStatus

        if not self._campaign:
            return []

        # Get character
        char = None
        if character_id:
            for c in self._campaign.characters:
                if c.id == character_id:
                    char = c
                    break
        elif self._campaign.characters:
            char = self._campaign.characters[0]

        if not char:
            return []

        # Gather evidence from campaign
        evidence_text = self._gather_arc_evidence()
        if not evidence_text:
            return []

        # Analyze each arc type
        candidates = []
        for arc_type, pattern in ARC_PATTERNS.items():
            score = self._score_arc_pattern(evidence_text, pattern, arc_type)

            if score >= 0.4:  # Threshold for detection
                # Check if this arc already exists
                existing = next(
                    (a for a in char.arcs if a.arc_type == arc_type),
                    None
                )

                if existing:
                    # Update existing arc
                    if existing.status != ArcStatus.REJECTED:
                        existing.strength = score
                        existing.last_reinforced = self._campaign.meta.session_count
                        existing.times_reinforced += 1
                else:
                    # New detection
                    title = random.choice(pattern["title_templates"])
                    candidates.append({
                        "arc_type": arc_type.value,
                        "title": title,
                        "description": pattern["description"],
                        "strength": score,
                        "effects": pattern["effects"],
                        "evidence": self._find_arc_evidence(evidence_text, pattern),
                    })

        return candidates

    def _gather_arc_evidence(self) -> str:
        """Gather text from campaign history for arc analysis."""
        if not self._campaign:
            return ""

        lines = []

        # Hinge moments (most important)
        for entry in self._campaign.history:
            if entry.hinge:
                lines.append(f"HINGE S{entry.session}: {entry.hinge.choice}")
                if entry.hinge.reasoning:
                    lines.append(f"  Reasoning: {entry.hinge.reasoning}")

        # Faction shifts
        for entry in self._campaign.history:
            if entry.faction_shift:
                shift = entry.faction_shift
                lines.append(f"FACTION S{entry.session}: {shift.faction.value} {shift.from_standing.value} -> {shift.to_standing.value} ({shift.cause})")

        # NPC interactions
        for npc in self._campaign.npcs.active + self._campaign.npcs.dormant:
            for inter in npc.interactions:
                lines.append(f"NPC S{inter.session}: {npc.name} - {inter.action}")

        # Character's hinge history (includes reasoning which has richer keywords)
        for char in self._campaign.characters:
            for hinge in char.hinge_history:
                if f"HINGE S{hinge.session}:" not in "\n".join(lines):
                    lines.append(f"HINGE S{hinge.session}: {hinge.choice}")
                    if hinge.reasoning:
                        lines.append(f"  Reasoning: {hinge.reasoning}")
                    if hinge.what_shifted:
                        lines.append(f"  Shifted: {hinge.what_shifted}")

        return "\n".join(lines)

    def _score_arc_pattern(
        self,
        evidence: str,
        pattern: dict,
        arc_type,
    ) -> float:
        """Score how well evidence matches an arc pattern."""
        evidence_lower = evidence.lower()
        score = 0.0

        # Keyword matching
        keywords = pattern.get("keywords", [])
        keyword_hits = sum(1 for kw in keywords if kw in evidence_lower)
        if keywords:
            score += (keyword_hits / len(keywords)) * 0.6  # 60% weight

        # Anti-keyword penalty
        anti_keywords = pattern.get("anti_keywords", [])
        anti_hits = sum(1 for kw in anti_keywords if kw in evidence_lower)
        if anti_keywords and anti_hits > 0:
            score -= (anti_hits / len(anti_keywords)) * 0.3  # Penalty

        # Faction focus check (for PARTISAN)
        if pattern.get("faction_focus") and self._campaign:
            faction_counts = {}
            for entry in self._campaign.history:
                if entry.faction_shift:
                    faction = entry.faction_shift.faction.value
                    faction_counts[faction] = faction_counts.get(faction, 0) + 1

            if faction_counts:
                max_faction = max(faction_counts.values())
                total = sum(faction_counts.values())
                if max_faction >= 3 and max_faction / total > 0.5:
                    score += 0.3  # Bonus for faction focus

        # Session spread bonus (pattern across multiple sessions)
        sessions_mentioned = set()
        for line in evidence.split("\n"):
            if " S" in line:
                parts = line.split(" S")
                for p in parts[1:]:
                    if p and p[0].isdigit():
                        sessions_mentioned.add(p.split(":")[0].split()[0])

        if len(sessions_mentioned) >= 3:
            score += 0.2  # Bonus for consistency across sessions

        return min(max(score, 0.0), 1.0)

    def _find_arc_evidence(self, evidence: str, pattern: dict) -> list[str]:
        """Find specific evidence lines that support an arc."""
        results = []
        keywords = pattern.get("keywords", [])

        for line in evidence.split("\n"):
            line_lower = line.lower()
            if any(kw in line_lower for kw in keywords):
                # Clean up the line
                clean = line.strip()
                if clean and clean not in results:
                    results.append(clean)

        return results[:5]  # Limit to 5 pieces of evidence

    def suggest_arc(self, character_id: str | None = None) -> dict | None:
        """
        Get the strongest arc candidate for a character.

        Returns the highest-scoring new arc that hasn't been suggested yet,
        or None if no strong candidates exist.
        """
        from ..state.schema import ArcStatus

        if not self._campaign:
            return None

        char = None
        if character_id:
            for c in self._campaign.characters:
                if c.id == character_id:
                    char = c
                    break
        elif self._campaign.characters:
            char = self._campaign.characters[0]

        if not char:
            return None

        # Get candidates
        candidates = self.detect_arcs(character_id)

        # Filter out already-suggested arcs
        existing_types = {a.arc_type.value for a in char.arcs}
        new_candidates = [c for c in candidates if c["arc_type"] not in existing_types]

        if not new_candidates:
            return None

        # Return strongest candidate above threshold
        strongest = max(new_candidates, key=lambda x: x["strength"])
        if strongest["strength"] >= 0.5:
            return strongest

        return None

    def accept_arc(self, character_id: str, arc_type: str) -> "CharacterArc | None":
        """Accept a suggested character arc."""
        from ..state.schema import ArcType, CharacterArc, ArcStatus, ARC_PATTERNS

        if not self._campaign:
            return None

        char = None
        for c in self._campaign.characters:
            if c.id == character_id:
                char = c
                break

        if not char:
            return None

        # Find or create the arc
        try:
            arc_enum = ArcType(arc_type)
        except ValueError:
            return None

        existing = next((a for a in char.arcs if a.arc_type == arc_enum), None)

        if existing:
            existing.status = ArcStatus.ACCEPTED
            self.manager.save_campaign()
            return existing

        # Create new arc
        pattern = ARC_PATTERNS.get(arc_enum, {})
        evidence = self._gather_arc_evidence()

        arc = CharacterArc(
            arc_type=arc_enum,
            title=random.choice(pattern.get("title_templates", [arc_type])),
            description=pattern.get("description", ""),
            detected_session=self._campaign.meta.session_count,
            evidence=self._find_arc_evidence(evidence, pattern),
            strength=0.6,
            status=ArcStatus.ACCEPTED,
            effects=pattern.get("effects", []),
        )

        char.arcs.append(arc)
        self.manager.save_campaign()
        return arc

    def reject_arc(self, character_id: str, arc_type: str) -> bool:
        """Reject a suggested character arc."""
        from ..state.schema import ArcType, ArcStatus, CharacterArc, ARC_PATTERNS

        if not self._campaign:
            return False

        char = None
        for c in self._campaign.characters:
            if c.id == character_id:
                char = c
                break

        if not char:
            return False

        try:
            arc_enum = ArcType(arc_type)
        except ValueError:
            return False

        existing = next((a for a in char.arcs if a.arc_type == arc_enum), None)

        if existing:
            existing.status = ArcStatus.REJECTED
            self.manager.save_campaign()
            return True

        # Create rejected placeholder so it won't be suggested again
        pattern = ARC_PATTERNS.get(arc_enum, {})

        arc = CharacterArc(
            arc_type=arc_enum,
            title=pattern.get("title_templates", [arc_type])[0] if pattern.get("title_templates") else arc_type,
            description=pattern.get("description", ""),
            detected_session=self._campaign.meta.session_count,
            strength=0.0,
            status=ArcStatus.REJECTED,
        )

        char.arcs.append(arc)
        self.manager.save_campaign()
        return True

    def get_active_arcs(self, character_id: str | None = None) -> list["CharacterArc"]:
        """Get all accepted arcs for a character."""
        from ..state.schema import ArcStatus

        if not self._campaign:
            return []

        char = None
        if character_id:
            for c in self._campaign.characters:
                if c.id == character_id:
                    char = c
                    break
        elif self._campaign.characters:
            char = self._campaign.characters[0]

        if not char:
            return []

        return [a for a in char.arcs if a.status == ArcStatus.ACCEPTED]

    def format_arcs_for_gm(self, character_id: str | None = None) -> str:
        """Format active arcs for inclusion in GM context."""
        arcs = self.get_active_arcs(character_id)

        if not arcs:
            return ""

        lines = ["## Character Arcs (recognized patterns)"]
        for arc in arcs:
            lines.append(f"\n**{arc.title}** ({arc.arc_type.value})")
            lines.append(f"_{arc.description}_")
            if arc.effects:
                lines.append("Effects:")
                for effect in arc.effects:
                    lines.append(f"- {effect}")

        return "\n".join(lines)
