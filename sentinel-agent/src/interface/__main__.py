"""
Run the WebSocket server for desktop UI.

Usage:
    python -m src.interface.websocket_server
"""

import asyncio
import logging

from ..state import CampaignManager
from .websocket_server import SentinelWebSocketServer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


def handle_command(command: str) -> str:
    """Process a command from the UI (placeholder)."""
    # This will be connected to the actual game engine
    if command.startswith('/'):
        return f"Command received: {command}"
    else:
        return f"Input received: {command}"


async def main():
    """Main entry point for WebSocket server."""
    # Initialize campaign manager
    manager = CampaignManager()

    # Try to load most recent campaign
    campaigns = manager.list_campaigns()
    if campaigns:
        most_recent = campaigns[0]
        # load_campaign takes index (1-based) or campaign ID
        campaign = manager.load_campaign("1")  # Load first campaign
        if campaign:
            logger.info(f"Loaded campaign: {campaign.meta.name}")
            logger.info(f"  Characters: {len(campaign.characters)}")
            logger.info(f"  Session: {campaign.session is not None}")
        else:
            logger.warning(f"Failed to load campaign")
    else:
        logger.info("No campaigns found. Create one via CLI first.")

    # Create and start server
    server = SentinelWebSocketServer(
        manager=manager,
        host="localhost",
        port=8765,
        on_command=handle_command,
    )

    await server.start()
    logger.info("SENTINEL WebSocket server running on ws://localhost:8765")
    logger.info("Press Ctrl+C to stop")

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
