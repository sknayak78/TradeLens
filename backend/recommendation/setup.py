"""Trading Setup — the stable structural thesis (ER-0036).

A TradingSetup is the structural reason to be interested in a stock: the
strategy (Trend Continuation, Pullback, Breakout...), a *structural* entry zone
whose ceiling is **not** today's close, a planned entry inside that zone, a
stop, targets and a reward:risk measured from the planned entry.

The zone is derived from market structure (EMA20 / support as the floor and a
band off the support-resistance span as the ceiling), so it is deterministic and
stays stable across daily price updates.  What moves daily is :mod:`progress` —
where today's price sits relative to this unchanging setup — never the setup
itself.  This is what prevents contradiction such as "wait for a pullback" being
issued while the price already sits inside the established structural zone.

This module is pure: no network, database, LLM, clock or randomness.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from .config import (
    ENTRY_ZONE_BAND_PCT,
    ENTRY_ZONE_SPAN_SHARE,
    LEVEL_STRATEGIES,
    SECOND_TARGET_BAND_SHARE,
    STOP_SUPPORT_MULTIPLIER,
)
from .models import RecommendationInput, Strategy, Trend


@dataclass(frozen=True)
class TradingSetup:
    """One structural trading thesis owned by market structure, not the price.

    Every price-level value here is derived from support/resistance (and the
    EMA20 floor), never from ``market.price``, so a daily move cannot silently
    rewrite the setup.
    """

    strategy: Strategy
    trend: Trend
    #: Lower bound of the structural entry zone (higher of support and EMA20).
    entry_min: float
    #: Upper bound of the structural entry zone — a level, not today's close.
    entry_max: float
    #: Representative fill inside the zone: the midpoint of ``entry_min`` /
    #: ``entry_max``.  Reward:risk is measured from here, never from the close.
    planned_entry: float
    stop_loss: float
    target1: float
    target2: float
    risk_reward: float
    #: One sentence stating the structural thesis this setup rests on.
    thesis: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _price(value: float) -> str:
    return f"{value:,.2f}"


def _thesis(
    market: RecommendationInput,
    strategy: Strategy,
    entry_min: float,
    entry_max: float,
) -> str:
    """A plain-English structural thesis for the setup."""
    zone = f"{_price(entry_min)} to {_price(entry_max)}"
    if strategy == "Trend Continuation":
        return (
            "The trend is intact and price can be bought inside a defined "
            f"structural zone of {zone} while the trend holds."
        )
    if strategy == "Pullback":
        return (
            "A healthy uptrend invites a refreshed entry on a slip back into a "
            f"structural buy zone of {zone}, provided the dip steadies."
        )
    if strategy == "Breakout":
        return (
            "The stock is building against resistance; the thesis is to buy a "
            "confirmed break above it rather than today's price."
        )
    if strategy == "Consolidation":
        return (
            "The range has no dominant side yet; the thesis is to wait for a "
            "clear direction rather than buy inside the noise."
        )
    return (
        "There is no structural entry plan yet; the thesis is to stand aside "
        "until buyers or sellers take control."
    )


def build_setup(
    market: RecommendationInput,
    strategy: Strategy,
    trend: Trend,
) -> Optional[TradingSetup]:
    """Derive a stable structural setup from market structure only.

    Returns ``None`` when the structure cannot support a usable zone (no
    support/resistance, or a degenerate band), which is exactly the case where
    the legacy engine publishes no levels and the narrative has no zone to
    describe.  A structural zone is only meaningful for strategies whose thesis
    includes a buy zone; for a Breakout / Consolidation / No Entry Yet thesis
    there is no stable zone to track, so no setup is built (the legacy fields
    already describe that plan).
    """
    if strategy not in LEVEL_STRATEGIES:
        return None
    support = market.support
    resistance = market.resistance
    if support is None or resistance is None:
        return None
    if support <= 0 or resistance <= support:
        return None

    floor = support if market.ema20 is None else max(market.ema20, support)
    span = resistance - support
    band = max(
        floor * ENTRY_ZONE_BAND_PCT,
        span * ENTRY_ZONE_SPAN_SHARE,
    )
    entry_min = round(floor, 2)
    # Structural ceiling: the floor plus the band, capped just under resistance
    # so the zone never overlaps the target zone it is aimed at.
    entry_max = round(min(floor + band, resistance * 0.995), 2)
    if entry_min >= entry_max:
        return None

    stop_loss = round(support * STOP_SUPPORT_MULTIPLIER, 2)
    if stop_loss >= entry_min:
        return None

    planned_entry = round((entry_min + entry_max) / 2, 2)
    if planned_entry <= stop_loss:
        return None

    target1 = round(resistance, 2)
    target2 = round(resistance + SECOND_TARGET_BAND_SHARE * span, 2)
    risk_reward = (target1 - planned_entry) / (planned_entry - stop_loss)

    values = (
        entry_min, entry_max, planned_entry, stop_loss,
        target1, target2, risk_reward,
    )
    if not all(math.isfinite(value) for value in values):
        return None

    return TradingSetup(
        strategy=strategy,
        trend=trend,
        entry_min=entry_min,
        entry_max=entry_max,
        planned_entry=planned_entry,
        stop_loss=stop_loss,
        target1=target1,
        target2=target2,
        risk_reward=round(risk_reward, 2),
        thesis=_thesis(market, strategy, entry_min, entry_max),
    )
