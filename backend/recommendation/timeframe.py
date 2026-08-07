"""Multi-timeframe market structure for mentor-quality narratives (ER-0017).

The Recommendation Engine's single ``trend`` answers "is the tape safe to buy?".
Beginners also see a chart that may be rising for a few sessions inside a larger
downtrend (or dipping inside a larger uptrend).  This module names that
structure so the narrative can reconcile what the user *sees* with what the
engine *decided* — without changing the decision itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from .models import RecommendationInput

Horizon = Literal["bullish", "bearish", "neutral", "unknown"]
Structure = Literal[
    "aligned_bullish",
    "aligned_bearish",
    "pullback",
    "counter_trend_rally",
    "consolidation",
    "insufficient",
]


@dataclass(frozen=True)
class TimeframeContext:
    """Short- vs long-horizon reading of one indicator snapshot.

    ``structure`` is the educational label the narrative should teach.  It never
    overrides the engine's action — it only explains the chart.
    """

    long_term: Horizon
    short_term: Horizon
    structure: Structure

    @property
    def horizons_disagree(self) -> bool:
        return self.structure in ("pullback", "counter_trend_rally")

    @property
    def is_counter_trend_rally(self) -> bool:
        return self.structure == "counter_trend_rally"

    @property
    def is_pullback(self) -> bool:
        return self.structure == "pullback"


def _long_term(market: RecommendationInput) -> Horizon:
    if market.ema200 is None:
        return "unknown"
    return "bullish" if market.price > market.ema200 else "bearish"


def _short_term(market: RecommendationInput) -> Horizon:
    """Recent-session bias from price vs the short average (and RSI as a tie-break)."""
    if market.ema20 is not None:
        if market.price > market.ema20:
            return "bullish"
        if market.price < market.ema20:
            return "bearish"
        return "neutral"
    if market.rsi is None:
        return "unknown"
    if market.rsi >= 55:
        return "bullish"
    if market.rsi <= 45:
        return "bearish"
    return "neutral"


def _structure(
    market: RecommendationInput, long_term: Horizon, short_term: Horizon
) -> Structure:
    if long_term == "unknown" and short_term == "unknown":
        return "insufficient"

    # Pullback: larger uptrend intact, recent sessions soft (engine's own flag
    # or price under the short average while still above the long one).
    if market.is_pullback or (
        long_term == "bullish" and short_term in ("bearish", "neutral")
    ):
        return "pullback"

    # Counter-trend rally: chart is lifting recently, but price is still below
    # the long-term average — the classic beginner trap.
    if long_term == "bearish" and short_term == "bullish":
        return "counter_trend_rally"

    if long_term == "bullish" and short_term == "bullish":
        return "aligned_bullish"

    if long_term == "bearish" and short_term in ("bearish", "neutral"):
        return "aligned_bearish"

    if long_term in ("unknown", "neutral") or short_term == "neutral":
        return "consolidation"

    return "consolidation"


def read_timeframes(market: RecommendationInput) -> TimeframeContext:
    """Derive the multi-timeframe context a mentor would point at on the chart."""
    long_term = _long_term(market)
    short_term = _short_term(market)
    return TimeframeContext(
        long_term=long_term,
        short_term=short_term,
        structure=_structure(market, long_term, short_term),
    )


def long_term_level(market: RecommendationInput) -> Optional[float]:
    """Price a trader can watch to confirm a long-term reclaim, when available."""
    return market.ema200
