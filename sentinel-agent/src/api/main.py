"""
SENTINEL 2D API Server Entry Point.

Run with:
    python -m src.api.main
    
Or with uvicorn directly:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import argparse
import os
from pathlib import Path

import uvicorn

from .server import create_app


def main():
    """Main entry point for SENTINEL 2D API server."""
    parser = argparse.ArgumentParser(description="SENTINEL 2D API Server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    parser.add_argument(
        "--campaigns",
        default="campaigns",
        help="Path to campaigns directory",
    )
    parser.add_argument(
        "--backend",
        default="auto",
        choices=["auto", "lmstudio", "ollama", "claude", "gemini", "codex"],
        help="LLM backend to use (default: auto)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Use local mode (optimized for 8B-12B models)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    base_dir = Path(__file__).parent.parent.parent.parent
    campaigns_dir = Path(args.campaigns)
    if not campaigns_dir.is_absolute():
        campaigns_dir = base_dir / campaigns_dir
    
    # Set environment variables for configuration
    os.environ["SENTINEL_CAMPAIGNS_DIR"] = str(campaigns_dir)
    os.environ["SENTINEL_BACKEND"] = args.backend
    os.environ["SENTINEL_LOCAL_MODE"] = "1" if args.local else "0"
    
    print(f"Starting SENTINEL 2D API Server")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Campaigns: {campaigns_dir}")
    print(f"  Backend: {args.backend}")
    print(f"  Local mode: {args.local}")
    print()
    
    # Run server
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info",
    )


# Create app instance for uvicorn
def get_app():
    """Factory function for creating the FastAPI app."""
    campaigns_dir = os.environ.get("SENTINEL_CAMPAIGNS_DIR", "campaigns")
    backend = os.environ.get("SENTINEL_BACKEND", "auto")
    local_mode = os.environ.get("SENTINEL_LOCAL_MODE", "0") == "1"
    
    return create_app(
        campaigns_dir=campaigns_dir,
        backend=backend,
        local_mode=local_mode,
    )


# App instance for direct uvicorn usage
app = get_app()


if __name__ == "__main__":
    main()
