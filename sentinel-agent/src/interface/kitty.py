"""
Kitty Graphics Protocol support.

Provides progressive enhancement for terminals that support the Kitty Graphics Protocol.
On unsupported terminals (or on platforms where querying is unreliable), functions degrade
gracefully by returning False/empty sequences.
"""

from __future__ import annotations

import base64
import os
import sys
import time
from functools import lru_cache
from pathlib import Path

ESC = "\x1b"
ST = "\x1b\\"


def _build_kitty_sequence(params: dict[str, str | int], payload: str = "") -> str:
    param_str = ",".join(f"{k}={v}" for k, v in params.items())
    return f"{ESC}_G{param_str};{payload}{ST}"


def _query_kitty_support(timeout_s: float) -> bool:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False

    if sys.platform == "win32":
        return False

    try:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            query = _build_kitty_sequence({"a": "q", "i": 31})
            sys.stdout.write(query)
            sys.stdout.flush()

            deadline = time.monotonic() + max(0.0, timeout_s)
            buf = ""
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                ready, _, _ = select.select([sys.stdin], [], [], remaining)
                if not ready:
                    break
                chunk = os.read(fd, 4096).decode(errors="ignore")
                buf += chunk
                if ST in buf:
                    break

            return ("i=31" in buf or "Gi=31" in buf) and "OK" in buf
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return False


@lru_cache(maxsize=1)
def kitty_available() -> bool:
    """
    Return True if the current terminal appears to support Kitty Graphics Protocol.

    Uses a best-effort query on POSIX terminals; falls back to environment heuristics
    when querying isn't possible.
    """
    if not sys.stdout.isatty():
        return False

    term = os.environ.get("TERM", "").lower()
    term_program = os.environ.get("TERM_PROGRAM", "").lower()

    # Strong signals - trust these environment variables directly
    if os.environ.get("KITTY_WINDOW_ID") or "kitty" in term:
        return True

    # WezTerm supports Kitty protocol on all platforms (including Windows)
    if os.environ.get("WEZTERM_EXECUTABLE") or "wezterm" in term_program:
        return True

    # Other terminals: try a fast query on POSIX (skip on Windows)
    if sys.platform != "win32":
        return _query_kitty_support(timeout_s=0.05)

    return False


def display_image(path: str | Path, width: int, height: int) -> str:
    """
    Return the escape sequence to display an image at the current cursor position.

    Args:
        path: Path to an image file (preferably PNG)
        width: Target width in terminal cells
        height: Target height in terminal cells
    """
    image_path = Path(path)
    try:
        data = image_path.read_bytes()
    except OSError:
        return ""

    b64 = base64.b64encode(data).decode("ascii")
    chunk_size = 4096

    sequences: list[str] = []
    offset = 0
    while offset < len(b64):
        chunk = b64[offset: offset + chunk_size]
        offset += len(chunk)
        more = 1 if offset < len(b64) else 0

        if not sequences:
            params: dict[str, str | int] = {
                "a": "T",  # transmit and display
                "f": 100,  # PNG
                "c": max(1, int(width)),
                "r": max(1, int(height)),
                "m": more,
            }
        else:
            params = {"m": more}

        sequences.append(_build_kitty_sequence(params, payload=chunk))

    return "".join(sequences)


def clear_image() -> str:
    """Return the escape sequence to clear displayed Kitty images."""
    return _build_kitty_sequence({"a": "d", "d": "A"})

