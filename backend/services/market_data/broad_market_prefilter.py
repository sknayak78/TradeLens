"""Stage-1 broad-market prefilter and Stage-2 historical-candidate selection.

Pure, provider-neutral screening over normalized ``MarketQuote`` snapshots.  This
module contains no I/O, no provider knowledge, and no thresholds from
``_screen()``: it only decides *which* instruments deserve the expensive
historical fetch, never whether a fetched instrument is technically sound.

Thresholds are measured, not assumed.  A live Upstox Full Market Quotes sweep of
the 2,656-instrument NSE_EQ master showed that price/volume/circuit-limit gates
alone reject under 2% of the universe (2,651 -> 2,603), so they cannot make the
sequential historical fetch affordable.  52-week-high proximity is the term that
actually discriminates (within 5% -> 133, 10% -> 452, 25% -> 1,496), so it is
the gate; the remaining cheap gates are kept as data-quality guards because
they are already paid for in the same payload.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from services.market_data.models import MarketQuote

#: Maximum distance below the 52-week high for a Stage-1 eligible instrument.
#: Measured on a live intraday sweep: 10% -> 452 of 2,655 returned quotes.
DEFAULT_YEAR_HIGH_PROXIMITY_PCT = 10.0

#: Hard cap on Stage-2 historical-screening inputs.  Concurrency makes 300
#: affordable inside the existing 60s discovery deadline; the cap is a hard
#: truncation, not a soft target, so a quiet market cannot blow the budget.
DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES = 300


@dataclass(frozen=True)
class StageOneResult:
    """Outcome of the Stage-1 prefilter over a bulk snapshot."""

    total_universe: int
    snapshot_requested: int
    snapshot_returned: int
    eligible: tuple[MarketQuote, ...]
    excluded: Mapping[str, int]

    @property
    def eligible_count(self) -> int:
        return len(self.eligible)


@dataclass(frozen=True)
class StageTwoSelection:
    """Deterministically truncated Stage-2 historical-candidate set."""

    selected: tuple[MarketQuote, ...]
    eligible_count: int
    cap: int

    @property
    def selected_count(self) -> int:
        return len(self.selected)

    @property
    def was_capped(self) -> bool:
        return self.eligible_count > self.cap


#: Reason keys are ordered by the first failing gate, mirroring the order the
#: gates are applied, so diagnostics attribute each exclusion to exactly one
#: cause.
_EXCLUSION_ORDER = (
    "missing_or_invalid_price",
    "missing_or_invalid_volume",
    "missing_or_invalid_year_high",
    "at_upper_circuit",
    "at_lower_circuit",
    "outside_year_high_proximity",
)


def distance_to_year_high_pct(price: float, year_high: float) -> float | None:
    """Percentage distance below a 52-week high, or ``None`` if not computable.

    ``distance_pct = ((year_high - price) / year_high) * 100``
    """
    if not _is_positive_finite(price) or not _is_positive_finite(year_high):
        return None
    return (year_high - price) / year_high * 100.0


def _is_positive_finite(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    number = float(value)
    return math.isfinite(number) and number > 0


def _at_upper_circuit(price: float, limit: object) -> bool:
    """True when ``price`` sits at the upper circuit limit (0.1% tolerance)."""
    if not _is_positive_finite(limit):
        return False
    return price >= float(limit) * 0.999


def _at_lower_circuit(price: float, limit: object) -> bool:
    """True when ``price`` sits at the lower circuit limit (0.1% tolerance).

    A missing or non-positive limit is not a circuit: absence of data must not
    silently exclude an otherwise valid instrument.
    """
    if not _is_positive_finite(limit):
        return False
    return price <= float(limit) * 1.001


def apply_stage_one_gates(
    quotes: Sequence[MarketQuote],
    *,
    year_high_proximity_pct: float = DEFAULT_YEAR_HIGH_PROXIMITY_PCT,
) -> StageOneResult:
    """Filter bulk quotes down to Stage-1 eligible instruments.

    Exactly the measured gates: price > 0, volume > 0, not at upper circuit, not
    at lower circuit, and within ``year_high_proximity_pct`` of the 52-week high.
    Malformed or missing values fail the gate instead of raising.
    """
    eligible: list[MarketQuote] = []
    excluded: dict[str, int] = {reason: 0 for reason in _EXCLUSION_ORDER}

    for quote in quotes:
        if not _is_positive_finite(quote.price):
            excluded["missing_or_invalid_price"] += 1
            continue
        if not _is_positive_finite(quote.volume):
            excluded["missing_or_invalid_volume"] += 1
            continue
        if not _is_positive_finite(quote.year_high):
            excluded["missing_or_invalid_year_high"] += 1
            continue
        if _at_upper_circuit(quote.price, quote.upper_circuit):
            excluded["at_upper_circuit"] += 1
            continue
        if _at_lower_circuit(quote.price, quote.lower_circuit):
            excluded["at_lower_circuit"] += 1
            continue
        distance = distance_to_year_high_pct(quote.price, quote.year_high)
        if distance is None or distance > year_high_proximity_pct:
            excluded["outside_year_high_proximity"] += 1
            continue
        eligible.append(quote)

    return StageOneResult(
        total_universe=len(quotes),
        snapshot_requested=len(quotes),
        snapshot_returned=len(quotes),
        eligible=tuple(eligible),
        excluded=excluded,
    )


def select_stage_two_candidates(
    result: StageOneResult,
    *,
    cap: int = DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES,
) -> StageTwoSelection:
    """Truncate Stage-1 survivors to at most ``cap``, deterministically.

    Ordering is fully deterministic and uses only fields already present in the
    bulk payload: distance to 52-week high ascending, then volume descending,
    then instrument key ascending.  No randomness, so repeated runs over the
    same snapshot always select the same instruments.
    """
    if cap < 0:
        raise ValueError("cap must not be negative")

    def sort_key(quote: MarketQuote) -> tuple[float, float, str]:
        distance = distance_to_year_high_pct(quote.price, quote.year_high)
        # Eligible quotes always have a computable distance; guard anyway so a
        # surprising value can never raise mid-sort.
        distance_value = distance if distance is not None else math.inf
        volume = quote.volume if _is_positive_finite(quote.volume) else 0.0
        return (distance_value, -volume, quote.instrument_key)

    ordered = sorted(result.eligible, key=sort_key)
    return StageTwoSelection(
        selected=tuple(ordered[:cap]),
        eligible_count=result.eligible_count,
        cap=cap,
    )
