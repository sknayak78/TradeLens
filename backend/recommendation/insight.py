"""Insight v2 educational copy — one lesson per strategy, no section overlap.

Each TradeLens Insight must teach at least one trading principle.  Fields here
answer dedicated questions so the Recommendation Card can stay concise:

* Mentor's Lesson — the principle being taught
* Who is this setup for? — audience fit
* What would change my view? — thesis invalidation (not Watch Next)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .models import Strategy, Trend

if TYPE_CHECKING:
    from .models import TradeLevels
    from .progress import SetupProgress
    from .setup import TradingSetup


#: One mentor lesson per strategy — the single principle this insight teaches.
MENTOR_LESSONS: dict[str, str] = {
    "Trend Continuation": (
        "Trend continuation means you join an existing move only when price is "
        "still near a planned entry and the exit is defined first. Strength "
        "without a plan is just hope."
    ),
    "Pullback": (
        "A pullback is a pause inside a larger uptrend — not a breakdown. The "
        "discipline is waiting for price to come to your zone instead of chasing "
        "the green candles you already missed."
    ),
    "Breakout": (
        "A breakout is only real after a decisive close through resistance. "
        "Buying underneath the ceiling is guessing; confirmation is the lesson."
    ),
    "Consolidation": (
        "Consolidation is the market catching its breath. Forcing a trade in a "
        "range teaches impatience; waiting for direction teaches process."
    ),
    "No Entry Yet": (
        "Standing aside is an active decision. When the broader trend is against "
        "you, the lesson is capital preservation — not finding a clever entry."
    ),
}


#: Who the setup is for — keyed by strategy so audience matches the thesis.
WHO_IS_THIS_FOR: dict[str, str] = {
    "Trend Continuation": (
        "Traders who can define an exit before they buy and are comfortable "
        "joining a trend near a planned zone — not chasing an extended move."
    ),
    "Pullback": (
        "Patient traders who prefer to wait for price to revisit a structural "
        "buy zone rather than pay up after a sharp run."
    ),
    "Breakout": (
        "Traders willing to wait for confirmation and skip the urge to "
        "anticipate a break that has not closed yet."
    ),
    "Consolidation": (
        "Anyone practising patience. There is no edge in inventing direction "
        "inside a mixed range."
    ),
    "No Entry Yet": (
        "Nobody hunting a fresh long today — especially beginners tempted by "
        "short-term bounces in a weak trend."
    ),
}


def mentor_lesson(strategy: Strategy) -> str:
    return MENTOR_LESSONS[strategy]


def who_is_this_for(strategy: Strategy) -> str:
    return WHO_IS_THIS_FOR[strategy]


def what_would_change_my_view(
    strategy: Strategy,
    trend: Trend,
    levels: Optional["TradeLevels"],
    progress: Optional["SetupProgress"],
    setup: Optional["TradingSetup"],
) -> str:
    """Invalidation / thesis-change line — must not repeat Watch Next wording."""
    plan = levels if levels is not None else (setup.levels if setup else None)

    if strategy == "Trend Continuation" and plan is not None:
        return (
            f"I would abandon this continuation idea if price closes below "
            f"{_p(plan.stop_loss)}, or if the long-term average is lost and the "
            "structure stops supporting a long."
        )
    if strategy == "Pullback" and plan is not None:
        return (
            f"I would drop this pullback plan if price closes below "
            f"{_p(plan.stop_loss)}, or if the bounce fails to hold the "
            "structural zone after arriving there."
        )
    if strategy == "Breakout":
        resistance = None
        if plan is not None:
            resistance = plan.entry_min  # breakout planned entry starts at resistance
        if progress is not None and progress.status == "breakout_holding":
            return (
                "I would treat the breakout as failed if the daily close slips "
                "back under resistance after the first thrust through it."
            )
        if resistance is not None:
            return (
                f"I would stop waiting for this breakout if sellers repeatedly "
                f"reject price at {_p(resistance)} and the range drifts lower "
                "instead of resolving upward."
            )
        return (
            "I would stop waiting for this breakout if overhead resistance keeps "
            "rejecting price and the broader structure turns lower."
        )
    if strategy == "Consolidation":
        return (
            "I would leave the sidelines only after a clear directional close "
            "resolves the range — either a sustained break higher with a plan, "
            "or a break lower that confirms staying out."
        )
    if trend == "bearish":
        return (
            "I would reconsider a long only after price reclaims the long-term "
            "average and holds it for several sessions — a one-day bounce would "
            "not be enough."
        )
    return (
        "I would engage only after structure clarifies: a held reclaim of the "
        "key averages and a defined risk level, not a single noisy session."
    )


def _p(value: float) -> str:
    return f"{value:,.2f}"
