"""Pure, deterministic recommendation engine for TradeLens.

The authoritative answer to "is this a good time to buy this stock today?",
served additively on ``GET /api/stock/{symbol}``.  The package is self-contained
and side-effect free so it can be unit tested without the API.
"""
from .engine import RecommendationEngine, engine
from .models import Recommendation, RecommendationInput, TradeLevels

__all__ = [
    "Recommendation",
    "RecommendationEngine",
    "RecommendationInput",
    "TradeLevels",
    "engine",
]
