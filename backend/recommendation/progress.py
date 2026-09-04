"""Setup Progress — where today's price sits against a stable TradingSetup.

Progress answers: is the price awaiting entry, already inside the structural
zone, extended beyond it, or has the setup been invalidated?  It is derived
**only** from the last price vs the unchanging setup's levels, and it never
rewrites the setup's strategy, zone, stop or targets.  The ``action`` it carries
is the engine's ongoing recommendation for that strategy, so progress never
introduces a second authority; the ``next_event`` is the *timing* guidance for
today.

The key invariant (ER-0036): once the price is inside the structural entry
zone, the progress must never tell the trader to "wait for a pullback into the
zone" — the price is already there.  It instead asks for the thesis to
confirm (a hold in-zone, or the momentum cooling) or to act.

This module is pure: no network, database, LLM, clock or randomness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal, Optional

from .models import Action
from .setup import TradingSetup

#: Where today's price sits relative to the structural setup.
ProgressStatus = Literal[
    "no_setup",
    "awaiting_entry",
    "in_entry_zone",
    "ready",
    "extended",
    "invalidated",
]


@dataclass(frozen=True)
class SetupProgress:
    """Daily reading of price against an unchanged Trading Setup."""

    status: ProgressStatus
    current_price: float
    #: Distance from price up to the structural zone floor, % of that floor.
    distance_to_entry_pct: Optional[float]
    #: Distance from price down to the stop, % of price.
    distance_to_stop_pct: Optional[float]
    #: Distance from price up to target1, % of price.
    distance_to_target1_pct: Optional[float]
    #: The engine's ongoing recommendation for the setup's strategy.
    action: Optional[Action]
    #: A human next event for *today* — never contradicts an in-zone price.
    next_event: str
    #: Plain-English invalidation note when the setup has broken down.
    invalidation: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _price(value: float) -> str:
    return f"{value:,.2f}"


def _pct(distance: float, reference: float) -> Optional[float]:
    if reference == 0:
        return None
    return round(distance / reference * 100, 2)


def _distances(
    price: float, setup: TradingSetup
) -> tuple[Optional[float], Optional[float], Optional[float]]:
    floor = setup.entry_min
    to_entry = _pct(price - floor, floor)
    to_stop = _pct(price - setup.stop_loss, price)
    to_t1 = _pct(setup.target1 - price, price)
    return to_entry, to_stop, to_t1


def evaluate_progress(
    market_price: float, setup: TradingSetup, action: Optional[Action]
) -> SetupProgress:
    """Derive progress solely from price vs the stable setup plan."""
    price = market_price
    to_entry, to_stop, to_t1 = _distances(price, setup)

    if price <= setup.stop_loss:
        return SetupProgress(
            status="invalidated",
            current_price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            action=action,
            next_event=(
                f"Setup invalidated below the stop {_price(setup.stop_loss)}; "
                "wait for structure to repair before revisiting."
            ),
            invalidation=(
                f"Price closed at/below the planned stop {_price(setup.stop_loss)}; "
                "the structural setup has broken down and is no longer actionable."
            ),
        )

    if setup.entry_min <= price <= setup.entry_max:
        ready = setup.strategy == "Trend Continuation"
        if ready:
            return SetupProgress(
                status="ready",
                current_price=price,
                distance_to_entry_pct=to_entry,
                distance_to_stop_pct=to_stop,
                distance_to_target1_pct=to_t1,
                action=action,
                next_event=(
                    f"Price {_price(price)} is inside the structural entry zone "
                    f"{_price(setup.entry_min)}-{_price(setup.entry_max)}; the "
                    "plan is actionable today. A daily close below "
                    f"{_price(setup.stop_loss)} cancels it."
                ),
                invalidation=None,
            )
        return SetupProgress(
            status="in_entry_zone",
            current_price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            action=action,
            next_event=(
                f"Price {_price(price)} is already inside the structural entry "
                f"zone {_price(setup.entry_min)}-{_price(setup.entry_max)}; no "
                "further pullback is required — just wait for the dip to hold "
                f"above {_price(setup.stop_loss)} before acting."
            ),
            invalidation=None,
        )

    if price > setup.entry_max:
        return SetupProgress(
            status="extended",
            current_price=price,
            distance_to_entry_pct=to_entry,
            distance_to_stop_pct=to_stop,
            distance_to_target1_pct=to_t1,
            action=action,
            next_event=(
                f"Price {_price(price)} is above the structural entry ceiling "
                f"{_price(setup.entry_max)}; wait for it to come back into the "
                "zone rather than chase the move."
            ),
            invalidation=None,
        )

    return SetupProgress(
        status="awaiting_entry",
        current_price=price,
        distance_to_entry_pct=to_entry,
        distance_to_stop_pct=to_stop,
        distance_to_target1_pct=to_t1,
        action=action,
        next_event=(
            f"Price {_price(price)} is below the structural entry floor "
            f"{_price(setup.entry_min)} but above the stop; watch for it to "
            "reclaim the zone and hold before considering an entry."
        ),
        invalidation=None,
    )
