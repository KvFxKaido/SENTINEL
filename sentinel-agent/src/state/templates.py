"""
Template engine for wiki page generation.

Provides Jinja2-based templates with user customization support.
Templates are loaded from wiki/templates/ with fallback to built-in defaults.
"""

from pathlib import Path
from typing import Any
import logging

from jinja2 import Environment, BaseLoader, TemplateNotFound

logger = logging.getLogger(__name__)


# =============================================================================
# Default Templates (Built-in)
# =============================================================================

DEFAULT_TEMPLATES = {
    # -------------------------------------------------------------------------
    # Session Note with Transclusion
    # -------------------------------------------------------------------------
    "session_with_transclusion.md.j2": """---
date: "{{ date }}"
campaign: "{{ campaign }}"
title: "Session: {{ date }}"
---
# Session Debrief: {{ date }}

## Player Reflections

{{ reflections }}

## Summary

{{ summary }}

## Game Log

![[_game_log]]
""",

    # -------------------------------------------------------------------------
    # MOC: Campaign Index
    # -------------------------------------------------------------------------
    "moc_campaign.md.j2": """# {{ campaign_name }}

[[_meta|Campaign Metadata]]

## Maps of Content

- [[sessions/_index|All Sessions]]
- [[NPCs/_index|All NPCs]]
- [[_events|Timeline of Events]]
""",

    # -------------------------------------------------------------------------
    # MOC: NPCs Index
    # -------------------------------------------------------------------------
    "moc_npcs.md.j2": """# NPCs

{% for faction, npcs in npcs_by_faction.items() %}
## {{ faction | title }}
{% for npc in npcs %}
- [[{{ npc.path }}|{{ npc.name }}]]
{% endfor %}
{% endfor %}
""",

    # -------------------------------------------------------------------------
    # MOC: Sessions Index
    # -------------------------------------------------------------------------
    "moc_sessions.md.j2": """# Sessions

{% for session in sessions %}
- [[{{ session.name }}]]
{% endfor %}
""",

    # -------------------------------------------------------------------------
    # NPC Page Template
    # -------------------------------------------------------------------------
    "npc.md.j2": """\
---
{% if extends %}extends: {{ extends }}
{% endif %}type: npc
faction: {{ faction }}
portrait: "assets/portraits/npcs/{{ name | lower | replace(' ', '_') | replace(\"'\", '') }}.png"
---

# {{ name }}

![[assets/portraits/npcs/{{ name | lower | replace(' ', '_') | replace(\"'\", '') }}.png|portrait]]

**Faction:** [[{{ faction }}]]
**Current Disposition:** {{ disposition }}

## Interaction History

### Session {{ session }}{% if first_meeting %} *(First Meeting)*{% endif %}

**Player:** {{ player_action }}

**{{ name }}:** {{ npc_reaction }}{% if disposition_change_text %} {{ disposition_change_text }}{% endif %}
""",

    # -------------------------------------------------------------------------
    # NPC Interaction Entry (appended to existing page)
    # -------------------------------------------------------------------------
    "npc_entry.md.j2": """\

### Session {{ session }}

**Player:** {{ player_action }}

**{{ name }}:** {{ npc_reaction }}{% if disposition_change_text %} {{ disposition_change_text }}{% endif %}
""",

    # -------------------------------------------------------------------------
    # Player Character Page Template (SUBJECT FILE format)
    # -------------------------------------------------------------------------
    "character.md.j2": """\
---
type: character
tags:
  - character
  - {{ background | lower }}
  - {{ campaign_id }}
campaign: {{ campaign_id }}
background: {{ background }}
{% if aligned_faction %}faction: {{ aligned_faction }}{% endif %}
portrait: "[[assets/portraits/campaigns/{{ campaign_id }}/{{ name_slug }}.png]]"
---

# SUBJECT FILE — SENTINEL ROLEPLAY RECORD

> **Access Level:** PROVISIONAL
> **Status:** ACTIVE CASE
> **Sessions:** {{ session_count }}

![[assets/portraits/campaigns/{{ campaign_id }}/{{ name_slug }}.png|portrait]]

---

## IDENTIFICATION

| Field | Entry |
|-------|-------|
| LEGAL NAME | {{ name }} |
{% if callsign %}| CALLSIGN | {{ callsign }} |{% endif %}
{% if pronouns %}| PRONOUNS | {{ pronouns }} |{% endif %}
{% if appearance_data and appearance_data.age %}| AGE | {{ appearance_data.age }} |{% elif age %}| AGE | {{ age }} |{% endif %}
{% if appearance_data %}| APPEARANCE | {{ appearance_data.build }} build, {{ appearance_data.skin_tone }} skin, {{ appearance_data.hair_color }} {{ appearance_data.hair_length }} hair{% if appearance_data.hair_style %} ({{ appearance_data.hair_style }}){% endif %}, {{ appearance_data.eye_color }} eyes{% if appearance_data.default_expression %}, {{ appearance_data.default_expression }} expression{% endif %} |{% elif appearance %}| APPEARANCE | {{ appearance }} |{% endif %}

{% if appearance_data %}
{% if appearance_data.facial_features or appearance_data.distinguishing_marks or appearance_data.augmentations or appearance_data.other_features %}
### Distinguishing Features
{% if appearance_data.facial_features %}- **Facial:** {{ appearance_data.facial_features | join(', ') }}{% endif %}
{% if appearance_data.distinguishing_marks %}- **Marks:** {{ appearance_data.distinguishing_marks | join(', ') }}{% endif %}
{% if appearance_data.augmentations %}- **Augmentations:** {{ appearance_data.augmentations }}{% endif %}
{% if appearance_data.other_features %}- **Other:** {{ appearance_data.other_features | join('; ') }}{% endif %}
{% endif %}
{% endif %}

---

## BACKGROUND CLASSIFICATION

{% for bg in backgrounds %}
- [{% if bg == background %}x{% else %} {% endif %}] {{ bg }}{% if bg == background %} — *{{ background_desc }}*{% endif %}
{% endfor %}

{% if survival_note %}
**Why this person is still alive:**
```
{{ survival_note }}
```
{% endif %}

---

{% if establishing_incident %}
## ESTABLISHING INCIDENT

```
Incident: {{ establishing_incident.description }}

Location: {{ establishing_incident.location | default('Unknown') }}

Costs: {{ establishing_incident.costs | default('Unknown') }}
```

---

{% endif %}
## SOCIAL ENERGY — {{ energy_track | upper | default('PISTACHIOS') }}

> Current: {{ social_energy }}% {% if social_energy >= 70 %}(Centered){% elif social_energy >= 40 %}(Managing){% elif social_energy >= 20 %}(Strained){% else %}(Critical){% endif %}

{% if restorers %}
**Restorers:**
{% for r in restorers %}
- {{ r }}
{% endfor %}
{% endif %}

{% if drains %}
**Drains:**
{% for d in drains %}
- {{ d }}
{% endfor %}
{% endif %}

---

## REPUTATION TRACKS

| Faction | Standing | Notes |
|---------|----------|-------|
{% for f in factions %}
| {{ f.name }} | {{ f.standing }} | {{ f.notes | default('—') }} |
{% endfor %}

---

## HINGE MOMENTS

> Permanent events that define your story. No bonuses. Only consequences.

| Moment | What Shifted |
|--------|--------------|
{% if hinges %}
{% for h in hinges %}
| **Session {{ h.session }}:** {{ h.title }} | {{ h.consequence | default(h.choice) }} |
{% endfor %}
{% else %}
| *None yet* | |
{% endif %}

---

## ENHANCEMENTS

{% if enhancements %}
**Accepted:**
| Enhancement | Source | Benefit | Cost |
|-------------|--------|---------|------|
{% for e in enhancements %}
| {{ e.name }} | {{ e.source_faction }} | {{ e.description }} | {{ e.leverage_cost | default('—') }} |
{% endfor %}
{% else %}
**Accepted:** None
{% endif %}

{% if refused_enhancements %}
**Refused:**
| Enhancement | Source | Benefit | Reason Refused |
|-------------|--------|---------|----------------|
{% for e in refused_enhancements %}
| {{ e.name }} | {{ e.source_faction }} | {{ e.benefit }} | {{ e.reason }} |
{% endfor %}
{% else %}
**Refused:** None
{% endif %}

> *Refusal is a meaningful choice. What you don't accept defines you as much as what you do.*

---

## EQUIPMENT

**Credits:** {{ credits }}c

{% if gear %}
{% for item in gear %}
- {{ item.name }}{% if item.description %} *({{ item.description }})*{% endif %}
{% endfor %}
{% else %}
*No notable equipment.*
{% endif %}

{% if vehicles %}
**Vehicles:**
{% for v in vehicles %}
- {{ v.name }} ({{ v.type }})
{% endfor %}
{% endif %}

---

{% if arcs %}
## CHARACTER ARCS

{% for arc in arcs %}
### {{ arc.title }} ({{ arc.arc_type }})
*{{ arc.description }}*
- **Status:** {{ arc.status }}
- **Detected:** Session {{ arc.detected_session }}
- **Strength:** {{ (arc.strength * 100) | int }}%
{% endfor %}

---

{% endif %}
{% if reflections %}
## AFTER ACTION — PERSONAL REFLECTION

> This is not scoring. This is perspective.

{% if reflections.cost %}
**What did this cost you?**
```
{{ reflections.cost }}
```
{% endif %}

{% if reflections.learned %}
**What did you learn?**
```
{{ reflections.learned }}
```
{% endif %}

{% if reflections.would_refuse %}
**What would you refuse to do again?**
```
{{ reflections.would_refuse }}
```
{% endif %}

---

{% endif %}
> **Filing reminder:** This record reflects the subject's account. Cross-reference with local witnesses and system logs when possible.

---

*Campaign data: `sentinel-agent/campaigns/{{ campaign_id }}.json`*
""",

    # -------------------------------------------------------------------------
    # Session Summary (Full Debrief)
    # -------------------------------------------------------------------------
    "session.md.j2": """\
---
session: {{ session }}
date: {{ date }}
campaign: {{ campaign }}
type: session
---

# Session {{ session }} — {{ date_display }}
{% if hinges %}

## Key Choices
{% for hinge in hinges %}

> [!hinge] {{ hinge.choice }}
{% if hinge.situation %}> **Situation:** {{ hinge.situation }}
{% endif %}{% if hinge.what_shifted %}> **Shifted:** {{ hinge.what_shifted }}
{% endif %}{% endfor %}{% endif %}
{% if faction_changes %}

## Faction Changes
{% for change in faction_changes %}

> [!{% if change.is_permanent %}danger{% else %}faction{% endif %}] {{ change.summary }}
{% if change.faction_link %}> Related: {{ change.faction_link }}
{% endif %}{% endfor %}{% endif %}
{% if threads_created %}

## Threads Queued
{% for thread in threads_created %}

> [!thread] {{ thread.origin }}
> **Severity:** {{ thread.severity | upper }}
> **Trigger:** {{ thread.trigger }}
{% endfor %}{% endif %}
{% if threads_resolved %}

## Threads Resolved
{% for thread in threads_resolved %}
- {{ thread.summary }}
{% endfor %}{% endif %}
{% if npcs_encountered %}

## NPCs Encountered
{% for npc in npcs_encountered %}
- {{ npc | npc_link }}
{% endfor %}{% endif %}
{% if reflections %}

## Player Reflections
{% if reflections.cost %}
- **What it cost:** {{ reflections.cost }}
{% endif %}{% if reflections.learned %}
- **What I learned:** {{ reflections.learned }}
{% endif %}{% if reflections.would_refuse %}
- **What I'd refuse:** {{ reflections.would_refuse }}
{% endif %}{% endif %}
""",

    # -------------------------------------------------------------------------
    # Session Live Update Skeleton (created on first append)
    # -------------------------------------------------------------------------
    "session_live.md.j2": """\
---
session: {{ session }}
date: {{ date }}
campaign: {{ campaign }}
type: session
---

# Session {{ session }} — {{ date_display }}

## Live Updates

{{ content }}
""",

    # -------------------------------------------------------------------------
    # Callout Templates
    # -------------------------------------------------------------------------
    "callouts/hinge.md.j2": """\
> [!hinge] {{ choice }}
{% if situation %}> **Situation:** {{ situation }}
{% endif %}{% if effects %}> **Effects:** {{ effects | join(', ') }}
{% endif %}""",

    "callouts/faction.md.j2": """\
> [!faction] [[{{ faction }}]]: {{ from_standing }} → {{ to_standing }}
> {{ cause }}
""",

    "callouts/thread.md.j2": """\
> [!thread] {{ origin }}
> **Severity:** {{ severity | upper }}
{% if trigger %}> **Trigger:** {{ trigger }}
{% endif %}""",

    # -------------------------------------------------------------------------
    # Timeline Entry
    # -------------------------------------------------------------------------
    "timeline_entry.md.j2": """\
- ({{ timestamp }}){% if event_type and event_type != 'event' %} [{{ event_type | upper }}]{% endif %}: {{ event }}{% if related_pages %} — {{ related_pages | map('wikilink') | join(', ') }}{% endif %}
""",

    # -------------------------------------------------------------------------
    # Faction Extension
    # -------------------------------------------------------------------------
    "faction_extension.md.j2": """\
### Session {{ session }}

- Standing changed: {{ from_standing }} → {{ to_standing }}
- Cause: {{ cause }}
""",
}


# =============================================================================
# Custom Jinja2 Loader
# =============================================================================

class WikiTemplateLoader(BaseLoader):
    """
    Custom Jinja2 loader that checks wiki/templates/ first,
    then falls back to built-in defaults.
    """

    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir

    def get_source(self, environment: Environment, template: str) -> tuple[str, str | None, callable]:
        # Try user templates first
        if self.templates_dir:
            user_template = self.templates_dir / template
            if user_template.exists():
                source = user_template.read_text(encoding="utf-8")
                return source, str(user_template), lambda: user_template.stat().st_mtime == user_template.stat().st_mtime

        # Fall back to built-in defaults
        if template in DEFAULT_TEMPLATES:
            return DEFAULT_TEMPLATES[template], None, lambda: True

        raise TemplateNotFound(template)


# =============================================================================
# Template Engine
# =============================================================================

class TemplateEngine:
    """
    Jinja2-based template engine for wiki page generation.

    Loads templates from wiki/templates/ with fallback to built-in defaults.
    Provides custom filters for SENTINEL-specific formatting.
    """

    def __init__(self, templates_dir: Path | None = None):
        """
        Initialize template engine.

        Args:
            templates_dir: Path to user templates directory (wiki/templates/).
                          If None, only built-in defaults are used.
        """
        self.templates_dir = templates_dir
        self._env = Environment(
            loader=WikiTemplateLoader(templates_dir),
            trim_blocks=True,
            lstrip_blocks=False,
            keep_trailing_newline=True,
        )

        # Register custom filters
        self._env.filters["wikilink"] = self._filter_wikilink
        self._env.filters["npc_link"] = self._filter_npc_link
        self._env.filters["upper"] = lambda s: str(s).upper() if s else ""

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of template file (e.g., "npc.md.j2")
            context: Dictionary of variables to pass to template

        Returns:
            Rendered template string
        """
        try:
            template = self._env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            logger.error(f"Template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Template render error ({template_name}): {e}")
            raise

    def has_user_template(self, template_name: str) -> bool:
        """Check if a user-customized template exists."""
        if not self.templates_dir:
            return False
        return (self.templates_dir / template_name).exists()

    def list_templates(self) -> dict[str, bool]:
        """
        List all available templates and whether they're customized.

        Returns:
            Dict mapping template name to True if user-customized
        """
        result = {}
        for name in DEFAULT_TEMPLATES:
            result[name] = self.has_user_template(name)
        return result

    # -------------------------------------------------------------------------
    # Custom Filters
    # -------------------------------------------------------------------------

    @staticmethod
    def _filter_wikilink(text: str) -> str:
        """Convert text to Obsidian wikilink."""
        return f"[[{text}]]"

    @staticmethod
    def _filter_npc_link(npc: dict) -> str:
        """
        Format NPC dict as wikilink with faction and disposition.

        Expected keys: name, faction, disposition_change
        """
        name = npc.get("name", "Unknown")
        faction = npc.get("faction", "")
        disp_change = npc.get("disposition_change", 0)

        # Build NPC line with wikilink
        npc_link = f"[[NPCs/{name}|{name}]]"
        faction_link = f"([[{faction.replace('_', ' ').title()}]])" if faction else ""

        if disp_change > 0:
            disposition = f"*(+{disp_change} disposition)*"
        elif disp_change < 0:
            disposition = f"*({disp_change} disposition)*"
        else:
            disposition = ""

        return f"{npc_link} {faction_link} {disposition}".strip()


# =============================================================================
# Factory Function
# =============================================================================

def create_template_engine(wiki_dir: Path | None = None) -> TemplateEngine:
    """
    Create a template engine for the given wiki directory.

    Args:
        wiki_dir: Path to wiki root. Templates loaded from wiki/templates/.
                 If None, only built-in defaults are used.

    Returns:
        Configured TemplateEngine instance
    """
    templates_dir = None
    if wiki_dir:
        templates_dir = wiki_dir / "templates"
        if not templates_dir.exists():
            templates_dir = None

    return TemplateEngine(templates_dir)
