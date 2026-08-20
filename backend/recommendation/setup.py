"""Trading Setup — the stable mentor thesis (Mentor Engine).

A Trading Setup is derived from **market structure** (averages, support,
resistance).  It does not use today's close as the entry ceiling, and risk/
reward is always measured from the planned entry inside the structural zone.

Daily price movement must not rewrite the setup; that belongs to Setup Progress.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    ACTION_BUY_MIN_SCORE,
    BREAKOUT_ENTRY_BAND_PCT,
    ENTRY_ZONE_BAND_PCT,
    ENTRY_ZONE_SPAN_SHARE,
    LEVEL_STRATEGIES,
    MIN_HEADROOM_PCT,
    MIN_RISK_REWARD,
    RSI_OVERBOUGHT,
    SECOND_TARGET_BAND_SHARE,
    STOP_SUPPORT_MULTIPLIER,
)
from .models import RecommendationInput, Strategy, TradeLevels, Trend
from .structure import StructureSnapshot, read_structure

#: Limit keys kept identical to narrative so explanations stay aligned.
LIMIT_OVERBOUGHT = "overbought"
LIMIT_THIN_HEADROOM = "thin_headroom"
LIMIT_POOR_RISK_REWARD = "poor_risk_reward"
LIMIT_NO_LEVELS = "no_levels"
LIMIT_PARTIAL_DATA = "partial_data"
LIMIT_TREND_NOT_BULLISH = "trend_not_bullish"
LIMIT_TREND_BEARISH = "trend_bearish"
LIMIT_WEAK_EVIDENCE = "weak_evidence"

Limits = Tuple[str, ...]


@dataclass(frozen=True)
class TradingSetup:
    """One coherent trading thesis owned by market structure."""

    strategy: Strategy
    trend: Trend
    structure_key: str
    planned_entry: Optional[float]
    levels: Optional[TradeLevels]
    limits: Limits
    score: int
    rules_matched: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        return payload


def build_setup(
    market: RecommendationInput,
    rules_matched: List[str],
    score: int,
) -> TradingSetup:
    """Classify strategy and build structure-based levels + R:R."""
    structure = read_structure(market)
    levels = _structural_levels(market, structure)
    limits = _limits(market, structure, score, levels)
    strategy = _classify_strategy(market, structure, limits, levels)
    if strategy == "Breakout":
        setup_levels = _breakout_levels(market)
    elif strategy in LEVEL_STRATEGIES:
        setup_levels = levels
    else:
        setup_levels = None

    planned = None if setup_levels is None else _planned_entry(setup_levels)
    return TradingSetup(
        strategy=strategy,
        trend=structure.trend,
        structure_key=structure.structure_key,
        planned_entry=planned,
        levels=setup_levels,
        limits=limits,
        score=score,
        rules_matched=tuple(rules_matched),
    )


def _planned_entry(levels: TradeLevels) -> float:
    return round((levels.entry_min + levels.entry_max) / 2, 2)


def _structural_levels(
    market: RecommendationInput, structure: StructureSnapshot
) -> Optional[TradeLevels]:
    """Buy zone from structure only — never ``market.price`` as entry_max."""
    del structure  # reserved for future ATR / regime overlays
    support = market.support
    resistance = market.resistance
    if support is None or resistance is None:
        return None
    if support <= 0 or resistance <= support:
        return None

    floor = support if market.ema20 is None else max(market.ema20, support)
    band = max(
        floor * ENTRY_ZONE_BAND_PCT,
        (resistance - support) * ENTRY_ZONE_SPAN_SHARE,
    )
    entry_min = floor
    entry_max = min(floor + band, resistance * 0.995)
    if entry_min >= entry_max:
        return None

    stop_loss = support * STOP_SUPPORT_MULTIPLIER
    if stop_loss >= entry_min:
        return None

    planned = (entry_min + entry_max) / 2
    if planned <= stop_loss:
        return None

    target1 = resistance
    target2 = resistance + SECOND_TARGET_BAND_SHARE * (resistance - support)
    # R:R from planned entry — never from today's close.
    risk_reward = (target1 - planned) / (planned - stop_loss)
    values = (entry_min, entry_max, stop_loss, target1, target2, risk_reward)
    if not all(math.isfinite(value) for value in values):
        return None
    return TradeLevels(
        entry_min=round(entry_min, 2),
        entry_max=round(entry_max, 2),
        stop_loss=round(stop_loss, 2),
        target1=round(target1, 2),
        target2=round(target2, 2),
        risk_reward=round(risk_reward, 2),
    )


def _breakout_levels(market: RecommendationInput) -> Optional[TradeLevels]:
    """Planned entry *above* resistance — the breakout thesis's structural plan."""
    support = market.support
    resistance = market.resistance
    if support is None or resistance is None or support <= 0:
        return None
    if resistance <= support:
        return None

    entry_min = resistance
    entry_max = resistance * (1.0 + BREAKOUT_ENTRY_BAND_PCT)
    stop_loss = support * STOP_SUPPORT_MULTIPLIER
    if stop_loss >= entry_min:
        return None
    planned = (entry_min + entry_max) / 2
    span = resistance - support
    target1 = resistance + 0.5 * span
    target2 = resistance + span
    if planned <= stop_loss:
        return None
    risk_reward = (target1 - planned) / (planned - stop_loss)
    values = (entry_min, entry_max, stop_loss, target1, target2, risk_reward)
    if not all(math.isfinite(value) for value in values):
        return None
    return TradeLevels(
        entry_min=round(entry_min, 2),
        entry_max=round(entry_max, 2),
        stop_loss=round(stop_loss, 2),
        target1=round(target1, 2),
        target2=round(target2, 2),
        risk_reward=round(risk_reward, 2),
    )


def _limits(
    market: RecommendationInput,
    structure: StructureSnapshot,
    score: int,
    levels: Optional[TradeLevels],
) -> Limits:
    limits: List[str] = []
    if structure.trend == "bearish":
        limits.append(LIMIT_TREND_BEARISH)
    elif structure.trend != "bullish":
        limits.append(LIMIT_TREND_NOT_BULLISH)
    if market.rsi is not None and market.rsi >= RSI_OVERBOUGHT:
        limits.append(LIMIT_OVERBOUGHT)
    # Headroom from the structural zone ceiling — not today's close — so the
    # Breakout vs Continuation thesis stays stable across quiet sessions.
    headroom = None
    if levels is not None and market.resistance is not None and levels.entry_max > 0:
        headroom = (market.resistance - levels.entry_max) / levels.entry_max * 100
    elif structure.structure_headroom_pct is not None:
        headroom = structure.structure_headroom_pct
    if headroom is None or headroom < MIN_HEADROOM_PCT:
        limits.append(LIMIT_THIN_HEADROOM)
    if levels is None:
        limits.append(LIMIT_NO_LEVELS)
    elif levels.risk_reward < MIN_RISK_REWARD:
        limits.append(LIMIT_POOR_RISK_REWARD)
    if score < ACTION_BUY_MIN_SCORE:
        limits.append(LIMIT_WEAK_EVIDENCE)
    if market.missing_indicators:
        limits.append(LIMIT_PARTIAL_DATA)
    return tuple(limits)


_ENTRY_BLOCKERS = (
    LIMIT_TREND_BEARISH,
    LIMIT_TREND_NOT_BULLISH,
    LIMIT_OVERBOUGHT,
    LIMIT_THIN_HEADROOM,
    LIMIT_NO_LEVELS,
    LIMIT_POOR_RISK_REWARD,
    LIMIT_WEAK_EVIDENCE,
)


def _classify_strategy(
    market: RecommendationInput,
    structure: StructureSnapshot,
    limits: Limits,
    levels: Optional[TradeLevels],
) -> Strategy:
    if structure.trend == "bearish":
        return "No Entry Yet"

    # Pullback regime (price under short average while long-term holds) wins
    # over breakout so we never mix theses.
    if market.is_pullback or LIMIT_OVERBOUGHT in limits:
        return "Pullback"

    if LIMIT_THIN_HEADROOM in limits and market.resistance is not None:
        return "Breakout"

    if (
        levels is not None
        and structure.trend == "bullish"
        and LIMIT_POOR_RISK_REWARD in limits
    ):
        return "Pullback"

    if structure.trend == "bullish" and not any(
        limit in limits for limit in _ENTRY_BLOCKERS
    ):
        return "Trend Continuation"

    if structure.trend == "bullish":
        return "No Entry Yet" if levels is None else "Pullback"

    return "Consolidation"
