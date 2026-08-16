"""Candidate screening for the market universe.

Removes only instruments that cannot be analysed reliably.  WAIT and AVOID
recommendations are valid downstream outcomes and are never filtered here.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

MIN_VOLUME = 1

_REQUIRED_FIELDS = (
    "symbol",
    "name",
    "price",
    "changePct",
    "rsi",
    "ema20",
    "vwap",
    "volume",
    "trend",
    "day_high",
    "avg_volume",
    "sector",
)

_NUMERIC_FIELDS = (
    "price",
    "changePct",
    "rsi",
    "ema20",
    "vwap",
    "volume",
    "day_high",
    "avg_volume",
)


@dataclass(frozen=True)
class ScreeningOutcome:
    symbol: str
    eligible: bool
    exclusion_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreeningSummary:
    universe_size: int
    eligible: tuple[dict[str, Any], ...]
    excluded: tuple[ScreeningOutcome, ...]

    @property
    def eligible_count(self) -> int:
        return len(self.eligible)

    @property
    def excluded_count(self) -> int:
        return len(self.excluded)


def _is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def screen_candidate(stock: dict[str, Any]) -> ScreeningOutcome:
    """Evaluate one stock snapshot for analysis eligibility."""
    symbol = str(stock.get("symbol", "")).strip().upper()
    reasons: list[str] = []

    for field in _REQUIRED_FIELDS:
        if field not in stock or stock[field] is None:
            reasons.append(f"missing_{field}")

    for field in _NUMERIC_FIELDS:
        if field in stock and stock[field] is not None and not _is_finite_number(stock[field]):
            reasons.append(f"non_finite_{field}")

    price = stock.get("price")
    if _is_finite_number(price) and float(price) <= 0:
        reasons.append("non_positive_price")

    volume = stock.get("volume")
    if _is_finite_number(volume) and float(volume) < MIN_VOLUME:
        reasons.append("insufficient_volume")

    avg_volume = stock.get("avg_volume")
    if avg_volume is not None and _is_finite_number(avg_volume) and float(avg_volume) < MIN_VOLUME:
        reasons.append("insufficient_avg_volume")

    rsi = stock.get("rsi")
    if _is_finite_number(rsi) and not 0.0 <= float(rsi) <= 100.0:
        reasons.append("invalid_rsi")

    for field in ("ema20", "vwap"):
        value = stock.get(field)
        if _is_finite_number(value) and float(value) <= 0:
            reasons.append(f"non_positive_{field}")

    return ScreeningOutcome(
        symbol=symbol or "UNKNOWN",
        eligible=not reasons,
        exclusion_reasons=tuple(reasons),
    )


def screen_candidates(stocks: list[dict[str, Any]]) -> ScreeningSummary:
    """Screen a batch of stock snapshots, returning eligible rows only."""
    eligible: list[dict[str, Any]] = []
    excluded: list[ScreeningOutcome] = []

    for stock in stocks:
        outcome = screen_candidate(stock)
        if outcome.eligible:
            eligible.append(stock)
        else:
            excluded.append(outcome)

    return ScreeningSummary(
        universe_size=len(stocks),
        eligible=tuple(eligible),
        excluded=tuple(excluded),
    )
