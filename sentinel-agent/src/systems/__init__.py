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
from .interrupts import InterruptDetector, InterruptCandidate, InterruptTrigger, InterruptUrgency
from .turns import TurnOrchestrator, TurnPhase, TurnError, StaleStateError
from .validation import ActionValidator
from .cascades import CascadeProcessor, CascadeResult, Notice, NoticeSeverity

__all__ = [
    "LeverageSystem",
    "ArcSystem",
    "JobSystem",
    "FavorSystem",
    "EndgameSystem",
    "InterruptDetector",
    "InterruptCandidate",
    "InterruptTrigger",
    "InterruptUrgency",
    # Turn-based engine (Phases 5-8)
    "TurnOrchestrator",
    "TurnPhase",
    "TurnError",
    "StaleStateError",
    "ActionValidator",
    "CascadeProcessor",
    "CascadeResult",
    "Notice",
    "NoticeSeverity",
]
