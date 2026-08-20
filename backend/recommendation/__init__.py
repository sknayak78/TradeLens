"""Pure, deterministic Mentor Engine for TradeLens.

The authoritative answer to "is this a good time to buy this stock today?",
served additively on ``GET /api/stock/{symbol}``.  A Trading Setup stays stable
while market structure holds; Setup Progress updates with the session.
"""
from .engine import RecommendationEngine, engine
from .models import Recommendation, RecommendationInput, TradeLevels
from .progress import SetupProgress
from .setup import TradingSetup

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "RecommendationInput",
    "SetupProgress",
    "TradeLevels",
    "TradingSetup",
    "engine",
]
