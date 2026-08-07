"""Future-only Watch Next triggers (ER-0018).

A recommendation must never ask the trader to wait for a market event that has
already happened at the latest price.  Triggers are resolved as a short state
machine: pick the thesis-appropriate hurdle, and if the latest price has already
cleared it, advance to the next logical hurdle (or a hold/cancel confirmation).

This module is pure: no I/O, no clock, no randomness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

from .models import RecommendationInput, Strategy, TradeLevels, Trend

Direction = Literal["above", "below", "toward"]
Limits = Tuple[str, ...]

#: Mirrors narrative.LIMIT_OVERBOUGHT — kept local to avoid an import cycle.
_LIMIT_OVERBOUGHT = "overbought"


@dataclass(frozen=True)
class Trigger:
    """One concrete, price-checkable market event."""

    level: float
    direction: Direction
    #: Human label used inside the sentence.
    label: str

    def is_satisfied(self, price: float) -> bool:
        """True when the latest price has already met this hurdle."""
        if self.direction == "above":
            return price >= self.level
        if self.direction == "below":
            return price <= self.level
        # toward: a pullback into the level from above — satisfied near/at the floor.
        return price <= self.level


def _price(value: float) -> str:
    return f"{value:,.2f}"


def _recent_level(market: RecommendationInput) -> Optional[float]:
    return market.ema20


def _long_level(market: RecommendationInput) -> Optional[float]:
    return market.ema200


def _first_future(
    price: float, candidates: Sequence[Optional[Trigger]]
) -> Optional[Trigger]:
    """Return the first trigger the latest price has not already satisfied."""
    for trigger in candidates:
        if trigger is None:
            continue
        if not trigger.is_satisfied(price):
            return trigger
    return None


def _reclaim_chain(market: RecommendationInput) -> list[Trigger]:
    """Ascending reclaim hurdles: short average → medium → long → resistance."""
    chain: list[Trigger] = []
    for level, name in (
        (market.ema20, "its recent average price"),
        (market.ema50, "its medium-term average"),
        (market.ema200, "its long-term average"),
        (market.resistance, "overhead resistance"),
    ):
        if level is None:
            continue
        chain.append(
            Trigger(
                level=level,
                direction="above",
                label=f"{name} of {_price(level)}",
            )
        )
    return chain


def _hold_above(level: float, name: str) -> str:
    return (
        f"Watch for price to hold above {name} of {_price(level)} for a few "
        "sessions; a slip back below would cancel the progress."
    )


def resolve_watch_next(
    market: RecommendationInput,
    strategy: Strategy,
    levels: Optional[TradeLevels],
    limits: Limits,
    trend: Trend,
) -> str:
    """Build a Watch Next line that is always a *future* event at ``market.price``."""
    del trend  # Thesis is carried by strategy; trend reserved for callers.
    price = market.price

    if strategy == "Trend Continuation" and levels is not None:
        # Failure is below the stop (future while price holds above it).
        # Upside: advance target if price has already cleared target1.
        if price >= levels.target1:
            return (
                f"Watch the {_price(levels.stop_loss)} level: a daily close "
                "below it means the idea has failed, while a push through "
                f"{_price(levels.target2)} extends the trend-continuation plan."
            )
        return (
            f"Watch the {_price(levels.stop_loss)} level: a daily close below it "
            "means the idea has failed, while a push through "
            f"{_price(levels.target1)} opens the way to "
            f"{_price(levels.target2)}."
        )

    if strategy == "Breakout":
        if market.resistance is None:
            return (
                "Watch for a decisive daily close through overhead resistance "
                "before considering an entry."
            )
        resistance = market.resistance
        if price < resistance:
            return (
                "Watch for a daily close above "
                f"{_price(resistance)}: that would confirm the breakout and "
                "create a fresh entry."
            )
        # Price already cleared resistance — advance to hold confirmation.
        return (
            f"Price is already above {_price(resistance)}; watch for a daily "
            "close that holds above it. A slip back below would mean the "
            "breakout failed."
        )

    if strategy == "Pullback":
        if _LIMIT_OVERBOUGHT in limits and levels is None:
            return (
                "Watch for the price to cool off and steady for a few sessions "
                "before considering an entry."
            )
        if levels is not None:
            floor = Trigger(
                level=levels.entry_min,
                direction="toward",
                label=_price(levels.entry_min),
            )
            if not floor.is_satisfied(price):
                return (
                    "Watch for a pullback toward "
                    f"{_price(levels.entry_min)} that holds, which would be the "
                    "entry to act on."
                )
            # Already at/under the buy-zone floor — next state is execution risk.
            return (
                f"The pullback zone near {_price(levels.entry_min)} is in play: "
                f"a daily close below {_price(levels.stop_loss)} cancels the "
                "setup, while holding here keeps the entry valid."
            )
        future = _first_future(price, _reclaim_chain(market))
        if future is not None:
            return (
                f"Watch for the price to steady above {future.label} and for "
                "clear support to form before considering an entry."
            )
        recent = _recent_level(market)
        if recent is not None:
            return _hold_above(recent, "its recent average price")
        return (
            "Watch for clear support to form and for a direction to emerge "
            "before considering an entry."
        )

    if strategy == "Consolidation":
        future = _first_future(price, _reclaim_chain(market))
        if future is not None:
            return (
                f"Watch for the price to steady above {future.label} and for a "
                "clear direction to emerge from the range before considering an "
                "entry."
            )
        if market.resistance is not None and price < market.resistance:
            return (
                "Watch for a daily close above "
                f"{_price(market.resistance)} or a break back below support to "
                "resolve this consolidation."
            )
        if market.resistance is not None:
            return (
                f"Price is already above {_price(market.resistance)}; watch "
                "whether the break holds on a daily close or fails back into "
                "the range."
            )
        recent = _recent_level(market)
        if recent is not None:
            return _hold_above(recent, "its recent average price")
        return (
            "Watch for a clear direction to emerge from the range before "
            "considering an entry."
        )

    # No Entry Yet / Avoid — never ask to reclaim a level already held.
    future = _first_future(price, _reclaim_chain(market))
    if future is not None:
        return (
            f"Watch for the price to reclaim {future.label} and hold it for a "
            "few sessions; until then there is nothing to do."
        )
    recent = _recent_level(market)
    if recent is not None and price >= recent:
        top = _long_level(market) or recent
        name = (
            "its long-term average"
            if _long_level(market) is not None
            else "its recent average price"
        )
        return _hold_above(top, name)
    return (
        "Watch for buyers to defend a level and push the price back above its "
        "recent average before revisiting this stock."
    )


def resolve_entry_condition(
    market: RecommendationInput,
    strategy: Strategy,
    levels: Optional[TradeLevels],
    trend: Trend,
) -> str:
    """Trading-plan line kept consistent with the future-only Watch Next thesis."""
    price = market.price

    if strategy == "Trend Continuation" and levels is not None:
        return (
            f"Consider entering between {_price(levels.entry_min)} and "
            f"{_price(levels.entry_max)}, and exit if the price closes below "
            f"{_price(levels.stop_loss)}."
        )
    if strategy == "Breakout":
        if market.resistance is None:
            return "Wait for a confirmed breakout above resistance before entering."
        if price < market.resistance:
            return (
                "Wait for a daily close above "
                f"{_price(market.resistance)} before entering."
            )
        return (
            f"Do not chase yet: wait for a daily close that holds above "
            f"{_price(market.resistance)} before entering."
        )
    if strategy == "Pullback":
        if levels is not None:
            if price > levels.entry_min:
                return (
                    "Wait for the price to pull back toward "
                    f"{_price(levels.entry_min)} and hold there."
                )
            return (
                f"The pullback zone near {_price(levels.entry_min)} is available: "
                f"enter only with an exit below {_price(levels.stop_loss)}."
            )
        future = _first_future(price, _reclaim_chain(market))
        if future is not None:
            return (
                f"Wait for the price to steady above {future.label} before "
                "considering an entry."
            )
        return "Wait for clear support to form before considering an entry."
    if strategy == "Consolidation":
        future = _first_future(price, _reclaim_chain(market))
        if future is not None:
            return (
                f"Wait for the price to steady above {future.label} before "
                "considering an entry."
            )
        return (
            "Wait for the range to resolve into a clear direction before "
            "considering an entry."
        )
    if trend == "bearish":
        future = _first_future(price, _reclaim_chain(market))
        if future is not None:
            return (
                "No trade: stay out until price reclaims "
                f"{future.label} and holds it."
            )
        return "No trade: stay out until buyers take back control."
    future = _first_future(price, _reclaim_chain(market))
    if future is not None:
        return (
            f"Wait for the price to steady above {future.label} before "
            "considering an entry."
        )
    return "Wait for clear support to form before considering an entry."
