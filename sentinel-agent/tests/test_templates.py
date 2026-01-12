"""Tests for template engine."""

import pytest
from pathlib import Path

from src.state.templates import (
    TemplateEngine,
    create_template_engine,
    DEFAULT_TEMPLATES,
    WikiTemplateLoader,
)


class TestTemplateEngine:
    """Test TemplateEngine class."""

    def test_create_engine_no_directory(self):
        """Engine works without templates directory."""
        engine = TemplateEngine(templates_dir=None)
        assert engine is not None
        assert engine.templates_dir is None

    def test_create_engine_with_directory(self, tmp_path):
        """Engine accepts templates directory."""
        engine = TemplateEngine(templates_dir=tmp_path)
        assert engine.templates_dir == tmp_path

    def test_render_default_template(self):
        """Can render built-in default templates."""
        engine = TemplateEngine()
        result = engine.render("npc.md.j2", {
            "name": "Test NPC",
            "faction": "Nexus",
            "disposition": "neutral",
            "extends": None,
            "session": 1,
            "first_meeting": True,
            "player_action": "greeted them",
            "npc_reaction": "nodded cautiously",
            "disposition_change_text": "",
        })
        assert "# Test NPC" in result
        assert "**Faction:** [[Nexus]]" in result
        assert "Session 1" in result
        assert "First Meeting" in result

    def test_render_npc_with_extends(self):
        """NPC template includes extends when provided."""
        engine = TemplateEngine()
        result = engine.render("npc.md.j2", {
            "name": "Canon NPC",
            "faction": "Lattice",
            "disposition": "friendly",
            "extends": "NPCs/Canon NPC",
            "session": 2,
            "first_meeting": True,
            "player_action": "asked for help",
            "npc_reaction": "agreed",
            "disposition_change_text": "*(disposition improved)*",
        })
        assert "extends: NPCs/Canon NPC" in result
        assert "*(disposition improved)*" in result

    def test_render_npc_entry(self):
        """Can render NPC entry template."""
        engine = TemplateEngine()
        result = engine.render("npc_entry.md.j2", {
            "session": 5,
            "name": "Cipher",
            "player_action": "traded info",
            "npc_reaction": "seemed pleased",
            "disposition_change_text": "",
        })
        assert "### Session 5" in result
        assert "**Player:** traded info" in result
        assert "**Cipher:** seemed pleased" in result


class TestCalloutTemplates:
    """Test callout templates."""

    def test_hinge_callout_full(self):
        """Hinge callout with all fields."""
        engine = TemplateEngine()
        result = engine.render("callouts/hinge.md.j2", {
            "choice": "Betrayed the contact",
            "situation": "Forced to choose",
            "effects": ["Lost ally", "Gained intel"],
        })
        assert "> [!hinge] Betrayed the contact" in result
        assert "**Situation:** Forced to choose" in result
        assert "**Effects:** Lost ally, Gained intel" in result

    def test_hinge_callout_minimal(self):
        """Hinge callout with only required field."""
        engine = TemplateEngine()
        result = engine.render("callouts/hinge.md.j2", {
            "choice": "Simple choice",
            "situation": None,
            "effects": None,
        })
        assert "> [!hinge] Simple choice" in result
        assert "Situation" not in result
        assert "Effects" not in result

    def test_faction_callout(self):
        """Faction callout renders correctly."""
        engine = TemplateEngine()
        result = engine.render("callouts/faction.md.j2", {
            "faction": "Nexus",
            "from_standing": "Neutral",
            "to_standing": "Friendly",
            "cause": "Helped with mission",
        })
        assert "> [!faction] [[Nexus]]: Neutral → Friendly" in result
        assert "> Helped with mission" in result

    def test_thread_callout_with_trigger(self):
        """Thread callout with trigger."""
        engine = TemplateEngine()
        result = engine.render("callouts/thread.md.j2", {
            "origin": "Abandoned cargo",
            "severity": "major",
            "trigger": "Return to station",
        })
        assert "> [!thread] Abandoned cargo" in result
        assert "**Severity:** MAJOR" in result
        assert "**Trigger:** Return to station" in result

    def test_thread_callout_no_trigger(self):
        """Thread callout without trigger."""
        engine = TemplateEngine()
        result = engine.render("callouts/thread.md.j2", {
            "origin": "Minor debt",
            "severity": "minor",
            "trigger": None,
        })
        assert "> [!thread] Minor debt" in result
        assert "**Severity:** MINOR" in result
        assert "Trigger" not in result


class TestSessionTemplates:
    """Test session note templates."""

    def test_session_template_full(self):
        """Session template with all sections."""
        engine = TemplateEngine()
        result = engine.render("session.md.j2", {
            "session": 3,
            "date": "2025-01-15",
            "campaign": "test_campaign",
            "date_display": "January 15, 2025",
            "hinges": [
                {"choice": "Made a deal", "situation": "Cornered", "what_shifted": "Alliance"},
            ],
            "faction_changes": [
                {"summary": "Nexus improved", "is_permanent": False, "faction_link": "[[Nexus]]"},
            ],
            "threads_created": [
                {"origin": "New threat", "severity": "major", "trigger": "Next jump"},
            ],
            "threads_resolved": [
                {"summary": "Old debt paid"},
            ],
            "npcs_encountered": [
                {"name": "Cipher", "faction": "nexus", "disposition_change": 1},
            ],
            "reflections": {
                "cost": "Trust",
                "learned": "Value of allies",
                "would_refuse": "Nothing",
            },
        })
        assert "session: 3" in result
        assert "## Key Choices" in result
        assert "## Faction Changes" in result
        assert "## Threads Queued" in result
        assert "## Threads Resolved" in result
        assert "## NPCs Encountered" in result
        assert "## Player Reflections" in result

    def test_session_template_empty(self):
        """Session template with no content sections."""
        engine = TemplateEngine()
        result = engine.render("session.md.j2", {
            "session": 1,
            "date": "2025-01-01",
            "campaign": "empty_campaign",
            "date_display": "January 1, 2025",
            "hinges": [],
            "faction_changes": [],
            "threads_created": [],
            "threads_resolved": [],
            "npcs_encountered": [],
            "reflections": None,
        })
        assert "session: 1" in result
        assert "# Session 1" in result
        # Empty sections should not appear
        assert "## Key Choices" not in result
        assert "## Faction Changes" not in result

    def test_session_live_template(self):
        """Session live template for initial creation."""
        engine = TemplateEngine()
        result = engine.render("session_live.md.j2", {
            "session": 2,
            "date": "2025-01-10",
            "campaign": "live_test",
            "date_display": "January 10, 2025",
            "content": "> [!hinge] First choice <!-- eid:abc123 -->",
        })
        assert "session: 2" in result
        assert "## Live Updates" in result
        assert "First choice" in result
        assert "eid:abc123" in result


class TestCustomFilters:
    """Test custom Jinja2 filters."""

    def test_wikilink_filter(self):
        """Wikilink filter wraps text in brackets."""
        engine = TemplateEngine()
        # Use timeline_entry template which uses wikilink filter
        result = engine.render("timeline_entry.md.j2", {
            "timestamp": "12:00",
            "event_type": "faction",
            "event": "Standing changed",
            "related_pages": ["Nexus", "Player"],
        })
        assert "[[Nexus]]" in result
        assert "[[Player]]" in result

    def test_npc_link_filter(self):
        """NPC link filter formats NPC dict."""
        engine = TemplateEngine()
        result = engine.render("session.md.j2", {
            "session": 1,
            "date": "2025-01-01",
            "campaign": "test",
            "date_display": "January 1, 2025",
            "hinges": [],
            "faction_changes": [],
            "threads_created": [],
            "threads_resolved": [],
            "npcs_encountered": [
                {"name": "Cipher", "faction": "nexus", "disposition_change": 2},
            ],
            "reflections": None,
        })
        assert "[[NPCs/Cipher|Cipher]]" in result
        assert "([[Nexus]])" in result
        assert "*(+2 disposition)*" in result

    def test_npc_link_negative_disposition(self):
        """NPC link shows negative disposition correctly."""
        engine = TemplateEngine()
        result = engine.render("session.md.j2", {
            "session": 1,
            "date": "2025-01-01",
            "campaign": "test",
            "date_display": "January 1, 2025",
            "hinges": [],
            "faction_changes": [],
            "threads_created": [],
            "threads_resolved": [],
            "npcs_encountered": [
                {"name": "Enemy", "faction": "", "disposition_change": -1},
            ],
            "reflections": None,
        })
        assert "*(-1 disposition)*" in result


class TestUserTemplates:
    """Test user template override functionality."""

    def test_user_template_overrides_default(self, tmp_path):
        """User template takes precedence over default."""
        # Create user template
        user_template = tmp_path / "npc.md.j2"
        user_template.write_text("CUSTOM: {{ name }}")

        engine = TemplateEngine(templates_dir=tmp_path)
        result = engine.render("npc.md.j2", {"name": "Test"})
        assert result == "CUSTOM: Test"

    def test_has_user_template(self, tmp_path):
        """has_user_template detects user templates."""
        engine = TemplateEngine(templates_dir=tmp_path)
        assert not engine.has_user_template("npc.md.j2")

        (tmp_path / "npc.md.j2").write_text("custom")
        assert engine.has_user_template("npc.md.j2")

    def test_list_templates(self, tmp_path):
        """list_templates shows all templates and customization status."""
        (tmp_path / "npc.md.j2").write_text("custom")

        engine = TemplateEngine(templates_dir=tmp_path)
        templates = engine.list_templates()

        assert "npc.md.j2" in templates
        assert templates["npc.md.j2"] is True  # Customized
        assert "session.md.j2" in templates
        assert templates["session.md.j2"] is False  # Not customized

    def test_fallback_to_default(self, tmp_path):
        """Falls back to default when user template doesn't exist."""
        engine = TemplateEngine(templates_dir=tmp_path)
        # Should use default template
        result = engine.render("npc.md.j2", {
            "name": "Fallback Test",
            "faction": "Test",
            "disposition": "neutral",
            "extends": None,
            "session": 1,
            "first_meeting": True,
            "player_action": "test",
            "npc_reaction": "test",
            "disposition_change_text": "",
        })
        assert "# Fallback Test" in result


class TestFactoryFunction:
    """Test create_template_engine factory."""

    def test_create_without_wiki_dir(self):
        """Factory works without wiki directory."""
        engine = create_template_engine(None)
        assert engine is not None
        assert engine.templates_dir is None

    def test_create_with_wiki_dir_no_templates(self, tmp_path):
        """Factory handles wiki dir without templates folder."""
        engine = create_template_engine(tmp_path)
        assert engine.templates_dir is None  # No templates folder

    def test_create_with_templates_folder(self, tmp_path):
        """Factory uses templates folder when present."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        engine = create_template_engine(tmp_path)
        assert engine.templates_dir == templates_dir


class TestDefaultTemplates:
    """Test default templates are complete."""

    def test_all_default_templates_exist(self):
        """All expected templates are in DEFAULT_TEMPLATES."""
        expected = [
            "npc.md.j2",
            "npc_entry.md.j2",
            "session.md.j2",
            "session_live.md.j2",
            "callouts/hinge.md.j2",
            "callouts/faction.md.j2",
            "callouts/thread.md.j2",
            "timeline_entry.md.j2",
            "faction_extension.md.j2",
        ]
        for template in expected:
            assert template in DEFAULT_TEMPLATES, f"Missing template: {template}"

    def test_default_templates_are_valid_jinja2(self):
        """All default templates parse without errors."""
        engine = TemplateEngine()
        for name in DEFAULT_TEMPLATES:
            # Just getting the template validates syntax
            template = engine._env.get_template(name)
            assert template is not None
