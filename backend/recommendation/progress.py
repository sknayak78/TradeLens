"""Setup Progress — daily reading of price against a stable Trading Setup.

Progress answers: where is today's price relative to the mentor's plan?
It must never rewrite the setup's strategy, entry zone, or risk/reward.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional

from .config import (
    ACTION_STRONG_BUY_MIN_SCORE,
    ACTION_WATCH_MIN_SCORE,
)
from .models import Action
from .models import RecommendationInput, Strategy, TradeLevels
from .setup import (
    LIMIT_OVERBOUGHT,
    TradingSetup,
)

ProgressStatus = Literal[
    "awaiting_entry",
    "in_entry_zone",
    "ready",
    "breakout_pending",
    "breakout_holding",
    "extended",
    "invalidated",
    "no_setup",
]


@dataclass(frozen=True)
class SetupProgress:
    """Session-level progress against an unchanged Trading Setup."""

    status: ProgressStatus
    price: float
    distance_to_entry_pct: Optional[float]
    distance_to_stop_pct: Optional[float]
    distance_to_target1_pct: Optional[float]
    next_event: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_progress(
    market: RecommendationInput, setup: TradingSetup
) -> SetupProgress:
    """Derive progress solely from last price vs the stable setup plan."""
    price = market.price
    levels = setup.levels
    strategy = setup.strategy

    if strategy == "No Entry Yet" or (
        strategy == "Consolidation" and levels is None
    ):
        return SetupProgress(
            status="no_setup" if strategy == "No Entry Yet" else "awaiting_entry",
            price=price,
            distance_to_entry_pct=None,
            distance_to_stop_pct=None,
            distance_to_target1_pct=None,
            next_event=_no_setup_event(market, setup),
        )

    if strategy == "Breakout":
        return _breakout_progress(market, setup)

    if levels is None:
        return SetupProgress(
            status="no_setup",
            price=price,
            distance_to_entry_pct=None,
            distance_to_stop_pct=None,
            distance_to_target1_pct=None,
            next_event=_no_setup_event(market, setup),
        )

    return _zone_progress(market, setup, levels)


def _pct(distance: float, reference: float) -> Optional[float]:
    if reference == 0:
        return None
    return round(distance / reference * 100, 2)


def _distances(
    price: float, levels: TradeLevels, planned: Optional[float]
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    entry_ref = planned if planned is not None else levels.entry_min
    to_entry = _pct(price - entry_ref, entry_ref)
    to_stop = _pct(price - levels.stop_loss, price)
    to_t1 = _pct(levels.target1 - price, price)
    return to_entry, to_stop, to_t1


def _zone_progress(
    market: RecommendationInput, setup: TradingSetup, levels: TradeLevels
) -> SetupProgress:
    price = market.price
    to_entry, to_stop, to_t1 = _distances(price, levels, setup.planned_entry)

    if price <= levels.stop_loss:
        return SetupProgress(
            status="invalidated",
            price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            next_event=(
                f"Setup invalidated below {_p(levels.stop_loss)}. Wait for "
                "structure to repair before revisiting."
            ),
        )

    if levels.entry_min <= price <= levels.entry_max:
        if LIMIT_OVERBOUGHT in setup.limits:
            return SetupProgress(
                status="in_entry_zone",
                price=price,
                distance_to_entry_pct=to_entry,
                distance_to_stop_pct=to_stop,
                distance_to_target1_pct=to_t1,
                next_event=(
                    "Short-term momentum is stretched: watch for the price to "
                    f"cool off and hold inside {_p(levels.entry_min)}-"
                    f"{_p(levels.entry_max)} before acting."
                ),
            )
        status: ProgressStatus = "in_entry_zone"
        if setup.strategy == "Trend Continuation":
            status = "ready"
        return SetupProgress(
            status=status,
            price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            next_event=(
                f"Price is inside the structural entry zone "
                f"{_p(levels.entry_min)}-{_p(levels.entry_max)}. A daily close "
                f"below {_p(levels.stop_loss)} cancels the plan."
            ),
        )

    if price < levels.entry_min:
        # Below the zone but above stop — still approaching from underneath.
        return SetupProgress(
            status="awaiting_entry",
            price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            next_event=(
                f"Watch for price to reclaim the entry zone near "
                f"{_p(levels.entry_min)} and hold it."
            ),
        )

    # Above the structural zone.
    if setup.strategy == "Trend Continuation" and LIMIT_OVERBOUGHT not in setup.limits:
        # Still a valid continuation if R:R and structure allowed the setup;
        # price above zone means extended — wait for pullback into structure.
        if price > levels.entry_max:
            return SetupProgress(
                status="extended",
                price=price,
                distance_to_entry_pct=to_entry,
                distance_to_stop_pct=to_stop,
                distance_to_target1_pct=to_t1,
                next_event=(
                    f"Price is extended above the structural buy zone. Watch for "
                    f"a pullback toward {_p(levels.entry_min)}-"
                    f"{_p(levels.entry_max)}."
                ),
            )

    return SetupProgress(
        status="awaiting_entry",
        price=price,
        distance_to_entry_pct=to_entry,
        distance_to_stop_pct=to_stop,
        distance_to_target1_pct=to_t1,
        next_event=(
            f"Watch for a pullback toward {_p(levels.entry_min)} that holds, "
            "which would bring price into the planned entry."
        ),
    )


def _breakout_progress(
    market: RecommendationInput, setup: TradingSetup
) -> SetupProgress:
    price = market.price
    resistance = market.resistance
    levels = setup.levels
    to_entry = to_stop = to_t1 = None
    if levels is not None:
        to_entry, to_stop, to_t1 = _distances(price, levels, setup.planned_entry)

    if resistance is None:
        return SetupProgress(
            status="breakout_pending",
            price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            next_event=(
                "Watch for a decisive daily close through overhead resistance "
                "before considering an entry."
            ),
        )

    if price < resistance:
        return SetupProgress(
            status="breakout_pending",
            price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            next_event=(
                f"Watch for a daily close above {_p(resistance)}: that would "
                "confirm the breakout and activate the planned entry."
            ),
        )

    return SetupProgress(
        status="breakout_holding",
        price=price,
        distance_to_entry_pct=to_entry,
        distance_to_stop_pct=to_stop,
        distance_to_target1_pct=to_t1,
        next_event=(
            f"Price is already above {_p(resistance)}; watch for a daily close "
            "that holds above it. A slip back below would mean the breakout "
            "failed."
        ),
    )


def _no_setup_event(market: RecommendationInput, setup: TradingSetup) -> str:
    if setup.trend == "bearish":
        if market.ema200 is not None and market.price < market.ema200:
            return (
                f"Watch for a daily close back above its long-term average of "
                f"{_p(market.ema200)} that holds for a few sessions; until then "
                "treat short-term rallies as temporary."
            )
        if market.ema20 is not None and market.price < market.ema20:
            return (
                f"Watch for the price to reclaim its recent average price of "
                f"{_p(market.ema20)} and hold it for a few sessions; until then "
                "there is nothing to do."
            )
        return (
            "Watch for buyers to reclaim the long-term average and hold it "
            "before revisiting this stock."
        )
    if market.ema20 is not None and market.price < market.ema20:
        return (
            f"Watch for the price to steady above its recent average price of "
            f"{_p(market.ema20)} and for a clear direction to emerge before "
            "considering an entry."
        )
    if market.resistance is not None and market.price < market.resistance:
        return (
            f"Watch for a daily close above {_p(market.resistance)} or a break "
            "back below support to resolve this consolidation."
        )
    return (
        "Watch for a clear direction to emerge from the range before "
        "considering an entry."
    )


def action_from_progress(setup: TradingSetup, progress: SetupProgress) -> Action:
    """Map stable setup + daily progress onto the public action enum."""
    strategy = setup.strategy
    status = progress.status
    score = setup.score

    if setup.trend == "bearish":
        return "Avoid"
    if status == "invalidated":
        return "Wait"

    if strategy == "Trend Continuation":
        if status in ("ready", "in_entry_zone"):
            if score >= ACTION_STRONG_BUY_MIN_SCORE:
                return "Strong Buy"
            return "Buy"
        if status == "extended":
            return "Watch" if score >= ACTION_WATCH_MIN_SCORE else "Wait"
        return "Watch" if score >= ACTION_WATCH_MIN_SCORE else "Wait"

    if strategy in ("Pullback", "Breakout"):
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        return "Wait"

    if strategy == "Consolidation":
        return "Wait"

    return "Wait"


def _p(value: float) -> str:
    return f"{value:,.2f}"
