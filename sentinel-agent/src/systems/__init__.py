"""
Game systems for SENTINEL.

Extracted from manager.py to separate domain logic from persistence.
Each system operates on campaign state and delegates save/log back to manager.
"""

from .leverage import LeverageSystem
from .arcs import ArcSystem
from .jobs import JobSystem
from .favors import FavorSystem
from .endgame import EndgameSystem

__all__ = ["LeverageSystem", "ArcSystem", "JobSystem", "FavorSystem", "EndgameSystem"]
