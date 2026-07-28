"""The TUI must boot.

Every unit test and a module-level smoke import passed while the primary
interface crashed on launch with a TypeError (caught in review on #63):
construction-time wiring inside on_mount is reachable only by actually
mounting the app. Textual's run_test drives a headless terminal, which
makes really mounting it cheap enough to do everywhere.
"""

import pytest

from src.interface.tui import SentinelTUI


@pytest.mark.asyncio
async def test_tui_boots_and_wires_the_manager():
    app = SentinelTUI()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.manager is not None
