"""Structural market reading for the Mentor Engine.

Structure is everything that should stay stable when only the last price ticks:
EMA relationships, support/resistance, and the fingerprint used to prove a
Trading Setup did not silently regenerate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .models import RecommendationInput, Trend


@dataclass(frozen=True)
class StructureSnapshot:
    """Price-independent structural facts (plus regime flags that use price)."""

    trend: Trend
    #: Fingerprint of the structural inputs that define a setup's identity.
    structure_key: str
    #: Room from the structural buy floor to resistance, when both exist.
    structure_headroom_pct: Optional[float]
    above_long_term: bool
    below_short_term: bool


def structural_trend(market: RecommendationInput) -> Trend:
    """EMA-stack trend — identical to the engine's historical definition."""
    emas = [
        value
        for value in (market.ema20, market.ema50, market.ema200)
        if value is not None
    ]
    if not emas:
        return "neutral"
    above = sum(1 for ema in emas if market.price > ema)

    if above == len(emas) and not market.stack_falling:
        return "bullish"
    if market.ema200 is not None and market.price > market.ema200:
        return "neutral"
    if above == 0 or market.stack_falling:
        return "bearish"
    return "neutral"


def structure_key(market: RecommendationInput) -> str:
    """Identity of the market structure that owns a Trading Setup.

    Deliberately excludes last price so a quiet session cannot rewrite the setup.
    """
    parts = [
        market.symbol,
        _fmt(market.ema20),
        _fmt(market.ema50),
        _fmt(market.ema200),
        _fmt(market.support),
        _fmt(market.resistance),
    ]
    return "|".join(parts)


def structure_headroom_pct(market: RecommendationInput) -> Optional[float]:
    """Headroom from the structural floor (not today's close) to resistance."""
    if market.resistance is None or market.resistance <= 0:
        return None
    floor = _structural_floor(market)
    if floor is None or floor <= 0:
        return None
    return (market.resistance - floor) / floor * 100


def _structural_floor(market: RecommendationInput) -> Optional[float]:
    if market.support is None and market.ema20 is None:
        return None
    if market.support is None:
        return market.ema20
    if market.ema20 is None:
        return market.support
    return max(market.ema20, market.support)


def read_structure(market: RecommendationInput) -> StructureSnapshot:
    return StructureSnapshot(
        trend=structural_trend(market),
        structure_key=structure_key(market),
        structure_headroom_pct=structure_headroom_pct(market),
        above_long_term=market.ema200 is not None and market.price > market.ema200,
        below_short_term=market.ema20 is not None and market.price < market.ema20,
    )


def _fmt(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.4f}"
