"""Single conversion boundary from normalized models to legacy provider dicts.

Compatibility conversion for screening, analysis, recommendation, and routers
happens here and on ``StockSnapshot`` / ``StockInsight`` model helpers.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.market_data.models import (
    Instrument,
    OpportunityContext,
    Quote,
    StockInsight,
    StockSnapshot,
)

#: Fields required by ``services.market_data.screening.screen_candidate``.
SCREENING_REQUIRED_FIELDS: tuple[str, ...] = (
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


def build_legacy_stock_dict(snapshot: StockSnapshot) -> dict[str, Any]:
    """Convert one normalized snapshot into the legacy stock dictionary shape."""
    return snapshot.to_legacy_dict()


def build_legacy_insight_dict(insight: StockInsight) -> dict[str, Any]:
    """Convert one normalized insight into the legacy insight dictionary shape."""
    return insight.to_legacy_dict()


def build_legacy_stock_from_quote(
    instrument: Instrument,
    quote: Quote,
    *,
    rsi: float,
    ema20: float,
    vwap: float,
    trend: str,
    day_high: float,
    avg_volume: int,
    ema50: float | None = None,
    ema200: float | None = None,
    score: int | None = None,
    support: float | None = None,
    resistance: float | None = None,
) -> dict[str, Any]:
    """Compose a legacy stock dict from normalized quote + indicator fields."""
    snapshot = StockSnapshot(
        symbol=instrument.symbol,
        name=instrument.name,
        price=quote.price,
        change_pct=quote.change_pct,
        rsi=rsi,
        ema20=ema20,
        vwap=vwap,
        volume=int(quote.volume or 0),
        trend=trend,
        day_high=day_high,
        avg_volume=avg_volume,
        sector=instrument.sector,
        ema50=ema50,
        ema200=ema200,
        score=score,
        support=support,
        resistance=resistance,
    )
    return build_legacy_stock_dict(snapshot)


def build_legacy_opportunity_rows(
    contexts: Sequence[OpportunityContext],
) -> list[dict[str, Any]]:
    """Convert curated opportunity contexts to the legacy opportunities list."""
    return [
        {"symbol": context.symbol, "score": context.score, "reason": context.reason}
        for context in contexts
    ]


def assert_legacy_stock_fields(payload: Mapping[str, Any]) -> None:
    """Raise when a legacy stock dict is missing screening-required fields."""
    missing = [field for field in SCREENING_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"legacy stock dict missing required fields: {missing}")


def _optional_float(row: Mapping[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value is None:
        return None
    return float(value)


def _optional_int(row: Mapping[str, Any], key: str) -> int | None:
    value = row.get(key)
    if value is None:
        return None
    return int(value)


def legacy_row_to_stock_snapshot(row: Mapping[str, Any]) -> StockSnapshot:
    """Convert one legacy catalogue stock row into a normalized snapshot."""
    return StockSnapshot(
        symbol=str(row["symbol"]).strip().upper(),
        name=str(row["name"]),
        price=float(row["price"]),
        change_pct=float(row["changePct"]),
        rsi=float(row["rsi"]),
        ema20=float(row["ema20"]),
        vwap=float(row["vwap"]),
        volume=int(row["volume"]),
        trend=str(row["trend"]),
        day_high=float(row["day_high"]),
        avg_volume=int(row["avg_volume"]),
        sector=str(row.get("sector", "")),
        ema50=_optional_float(row, "ema50"),
        ema200=_optional_float(row, "ema200"),
        score=_optional_int(row, "score"),
        support=_optional_float(row, "support"),
        resistance=_optional_float(row, "resistance"),
    )


def legacy_row_to_stock_insight(row: Mapping[str, Any], symbol: str) -> StockInsight:
    """Convert one legacy insight row into a normalized insight payload."""
    normalized = symbol.strip().upper()
    return StockInsight(
        symbol=normalized,
        support=float(row["support"]),
        resistance=float(row["resistance"]),
        ai_insight=str(row["aiInsight"]),
        series=tuple(dict(point) for point in row.get("series", [])),
    )
