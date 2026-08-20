"""Build chart series and day-range lookups from the market-data providers."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Sequence

from services.chart_timeframe import (
    INTRADAY_FALLBACK,
    TimeframeConfig,
    get_timeframe_config,
    normalize_timeframe,
)
from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService
from services.providers.yahoo_finance_provider import YahooFinanceProvider

logger = logging.getLogger("tradelens.chart_series")


def _format_label(bar: OHLCVBar, intraday: bool) -> str:
    timestamp = bar.timestamp
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if intraday:
        return timestamp.astimezone(timezone.utc).strftime("%H:%M")
    return timestamp.strftime("%Y-%m-%d")


def bars_to_series(
    bars: Sequence[OHLCVBar],
    *,
    max_points: int,
    intraday: bool,
) -> list[dict[str, Any]]:
    if not bars:
        return []
    selected = list(bars)[-max_points:]
    return [
        {"t": _format_label(bar, intraday), "v": round(bar.close, 2)}
        for bar in selected
    ]


def _fetch_bars(
    service: MarketDataService,
    symbol: str,
    config: TimeframeConfig,
) -> list[OHLCVBar]:
    normalized_symbol = symbol.strip().upper()
    primary = service._primary  # noqa: SLF001 — internal reuse within services layer

    if isinstance(primary, YahooFinanceProvider):
        yahoo_symbol = primary._normalized._symbol_mapper.to_yahoo(normalized_symbol)  # noqa: SLF001
        history = primary._history(yahoo_symbol, config.period, config.interval)  # noqa: SLF001
        return YahooFinanceProvider._history_to_ohlcv_bars(history)

    normalized = getattr(primary, "_normalized", None)
    if normalized is None and hasattr(primary, "_adapter"):
        normalized = primary._adapter.normalized  # type: ignore[attr-defined]

    if normalized is not None:
        return list(
            normalized.get_historical_ohlcv(
                normalized_symbol,
                period=config.period,
                interval=config.interval,
            )
        )

    # Seed-only fallback via default insight series.
    insight = service.get_stock_insight(normalized_symbol).data
    seed_series = insight.get("series", [])
    return [
        OHLCVBar(
            timestamp=datetime.now(timezone.utc),
            open=point["v"],
            high=point["v"],
            low=point["v"],
            close=point["v"],
            volume=None,
        )
        for point in seed_series
    ]


def build_chart_series(
    service: MarketDataService,
    symbol: str,
    timeframe: str,
) -> tuple[list[dict[str, Any]], str, bool]:
    """Return chart points, a human label, and whether a fallback range was used."""
    normalized_tf = normalize_timeframe(timeframe)
    config = get_timeframe_config(normalized_tf)
    used_fallback = False
    label = config.label

    try:
        bars = _fetch_bars(service, symbol, config)
        if not bars:
            raise RuntimeError("no bars returned for timeframe")
        series = bars_to_series(bars, max_points=config.max_points, intraday=config.intraday)
        if series:
            return series, label, used_fallback
        raise RuntimeError("no chart points built for timeframe")
    except Exception:
        if not config.intraday or normalized_tf not in INTRADAY_FALLBACK:
            logger.warning(
                "chart_series.primary_fetch_failed symbol=%s timeframe=%s",
                symbol,
                normalized_tf,
                exc_info=True,
            )
            raise

    fallback = INTRADAY_FALLBACK[normalized_tf]
    used_fallback = True
    label = fallback.label
    bars = _fetch_bars(service, symbol, fallback)
    series = bars_to_series(
        bars,
        max_points=fallback.max_points,
        intraday=fallback.intraday,
    )
    if not series:
        raise RuntimeError("no fallback chart points available")
    return series, label, used_fallback


def get_day_ohlc_range(
    service: MarketDataService,
    symbol: str,
    trade_date: date,
) -> dict[str, Any]:
    """Return the recorded low/high for a trading day when available."""
    normalized_symbol = symbol.strip().upper()
    config = get_timeframe_config("1Y")
    try:
        bars = _fetch_bars(service, symbol, config)
    except Exception:
        logger.warning(
            "day_range.fetch_failed symbol=%s date=%s",
            normalized_symbol,
            trade_date.isoformat(),
            exc_info=True,
        )
        return {
            "symbol": normalized_symbol,
            "date": trade_date.isoformat(),
            "available": False,
            "low": None,
            "high": None,
            "message": "Historical price range unavailable; price could not be automatically validated.",
        }

    for bar in reversed(bars):
        bar_date = bar.timestamp.date()
        if bar_date == trade_date:
            return {
                "symbol": normalized_symbol,
                "date": trade_date.isoformat(),
                "available": True,
                "low": round(bar.low, 2),
                "high": round(bar.high, 2),
                "message": None,
            }

    return {
        "symbol": normalized_symbol,
        "date": trade_date.isoformat(),
        "available": False,
        "low": None,
        "high": None,
        "message": "Historical price range unavailable; price could not be automatically validated.",
    }
