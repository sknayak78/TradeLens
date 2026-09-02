"""Build chart series and day-range lookups from the market-data providers."""
from __future__ import annotations

import logging
from collections import OrderedDict
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, Sequence

from services.chart_axis_labels import series_timestamp
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

IST_TZ = timezone(timedelta(hours=5, minutes=30))

#: EMA periods overlaid on the chart. Each is warmed over historical lookback
#: that extends beyond the visible window, then clipped to the displayed range.
EMA_PERIODS = (20, 50, 200)

#: Per-timeframe display plan — how far back to fetch, the aggregation, and how
#: many candles to keep on screen. Keeps candle counts visually manageable and
#: keeps OHLC values sourced from the real provider bars (no fabrication).
#:
#: `period`/`interval` describe how much history to fetch. This window doubles
#: as the EMA lookback, so it is deliberately wider than the number of candles
#: shown (`max_points`): intraday timeframes (1D/1W) fetch several sessions / a
#: month so EMA20/EMA50 are fully warmed before the visible session begins, and
#: the daily timeframes (1M/3M/1Y) keep a long daily lookback so EMA200 is
#: converged. `max_points` alone drives the visible candle count, so the
#: aggregation the user sees is unchanged.
_DISPLAY_PLAN: dict[str, dict[str, Any]] = {
    # 1D fetches a full month of 5m intraday bars so EMA20/50/200 are warmed
    # (and EMA200 converges) over history far beyond the ~78 visible candles,
    # rather than the previous 5-day window which barely supported EMA200.
    "1D": {"period": "1mo", "interval": "5m", "max_points": 78, "weekly": False},
    "1W": {"period": "1mo", "interval": "30m", "max_points": 65, "weekly": False},
    "1M": {"period": "1y", "interval": "1d", "max_points": 22, "weekly": False},
    "3M": {"period": "2y", "interval": "1d", "max_points": 66, "weekly": False},
    "1Y": {"period": "5y", "interval": "1d", "max_points": 60, "weekly": True},
}


def _ist(dt: datetime) -> datetime:
    return dt.astimezone(IST_TZ)


def _week_monday(dt: datetime) -> date:
    local = _ist(dt).date()
    return local - timedelta(days=local.weekday())


def aggregate_weekly(bars: Sequence[OHLCVBar]) -> list[OHLCVBar]:
    """Collapse daily bars into weekly OHLC candles using real values only.

    Open is the first bar of the week, high the max, low the min, close the last
    bar, and volume the sum. No OHLC value is invented or inferred.
    """
    groups: "OrderedDict[date, dict[str, Any]]" = OrderedDict()
    for bar in bars:
        key = _week_monday(bar.timestamp)
        bucket = groups.get(key)
        if bucket is None:
            groups[key] = {
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": None if bar.volume is None else bar.volume,
                "ts": bar.timestamp,
            }
        else:
            bucket["high"] = max(bucket["high"], bar.high)
            bucket["low"] = min(bucket["low"], bar.low)
            bucket["close"] = bar.close
            bucket["ts"] = bar.timestamp
            if bar.volume is not None and bucket["volume"] is not None:
                bucket["volume"] += bar.volume

    return [
        OHLCVBar(
            timestamp=g["ts"],
            open=g["open"],
            high=g["high"],
            low=g["low"],
            close=g["close"],
            volume=g["volume"],
        )
        for g in groups.values()
    ]


def compute_ema(
    values: Sequence[float | None],
    period: int,
) -> list[float | None]:
    """Exponential moving average over optionally-gapless numeric values.

    A value is emitted only once `period` valid observations have accumulated
    (seeded by their simple average), so the result never implies meaningfulness
    from too little history.
    """
    out: list[float | None] = [None] * len(values)
    if period <= 0:
        return out
    k = 2.0 / (period + 1)
    seen = 0
    seed_sum = 0.0
    prev = 0.0
    for i, value in enumerate(values):
        if value is None:
            continue
        if seen < period:
            seed_sum += value
            seen += 1
            if seen == period:
                prev = seed_sum / period
                out[i] = prev
            continue
        prev = value * k + prev * (1 - k)
        out[i] = prev
    return out


def _is_finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and (
        not isinstance(value, float) or value == value
    )


def _ema_availability(
    full_bars: Sequence[OHLCVBar],
) -> Dict[str, bool]:
    """Whether each EMA period is supported by the full (lookback) data."""
    count = sum(
        1 for bar in full_bars if _is_finite_number(bar.close)
    )
    return {f"ema{period}": count >= period for period in EMA_PERIODS}


def build_ema_overlay(
    bars: Sequence[OHLCVBar],
) -> Dict[datetime, Dict[str, float | None]]:
    """Compute EMA20/50/200 over a bar list, keyed by bar timestamp.

    The EMA is computed over the *raw fetch / lookback* history so overlays are
    warmed (and, for longer periods, converged) before they are sampled onto the
    shorter visible window. Sampling by timestamp lets a weekly candle pick up
    the daily-converged EMA at the week's last bar rather than recomputing it
    over only a handful of weekly observations.
    """
    closes: list[float | None] = [
        bar.close if _is_finite_number(bar.close) else None for bar in bars
    ]
    columns: Dict[str, list[float | None]] = {
        f"ema{period}": compute_ema(closes, period) for period in EMA_PERIODS
    }
    overlay: Dict[datetime, Dict[str, float | None]] = {}
    for i, bar in enumerate(bars):
        overlay[bar.timestamp] = {
            key: (None if cols[i] is None else round(cols[i], 2))
            for key, cols in columns.items()
        }
    return overlay


def build_display_points(
    display_bars: Sequence[OHLCVBar],
    ema_overlay: Dict[datetime, Dict[str, float | None]],
    max_points: int,
) -> list[dict[str, Any]]:
    """Convert the (possibly aggregate/clipped) display bars to chart points.

    EMA overlays are attached by looking up the candle's anchor timestamp in the
    overlay built over the longer lookback history, so a weekly candle shows the
    daily-EMA sampled at the week's final bar. The visible OHLCV is untouched.
    """
    selected = list(display_bars)[-max_points:]
    points: list[dict[str, Any]] = []
    for bar in selected:
        ema = ema_overlay.get(bar.timestamp, {})
        point: dict[str, Any] = {
            "t": series_timestamp(bar),
            # close price (kept for the existing line-chart fallback and Y domain)
            "v": round(bar.close, 2),
            # OHLCV reused from the existing provider bars (no extra fetch).
            "o": round(bar.open, 2),
            "h": round(bar.high, 2),
            "l": round(bar.low, 2),
            "vol": bar.volume,
        }
        for key in (f"ema{period}" for period in EMA_PERIODS):
            point[key] = ema.get(key)
        points.append(point)
    return points


def bars_to_series(
    bars: Sequence[OHLCVBar],
    *,
    max_points: int,
) -> list[dict[str, Any]]:
    if not bars:
        return []
    selected = list(bars)[-max_points:]
    return [
        {
            "t": series_timestamp(bar),
            # close price (kept for the existing line-chart fallback and Y domain)
            "v": round(bar.close, 2),
            # OHLCV reused from the existing provider bars (no extra fetch).
            "o": round(bar.open, 2),
            "h": round(bar.high, 2),
            "l": round(bar.low, 2),
            "vol": bar.volume,
        }
        for bar in selected
    ]


def _fetch_bars(
    service: MarketDataService,
    symbol: str,
    config: TimeframeConfig,
    *,
    period: str | None = None,
    interval: str | None = None,
) -> list[OHLCVBar]:
    bar_period = period or config.period
    bar_interval = interval or config.interval
    normalized_symbol = symbol.strip().upper()
    primary = service._primary  # noqa: SLF001 — internal reuse within services layer

    if isinstance(primary, YahooFinanceProvider):
        yahoo_symbol = primary._normalized._symbol_mapper.to_yahoo(normalized_symbol)  # noqa: SLF001
        history = primary._history(yahoo_symbol, bar_period, bar_interval)  # noqa: SLF001
        return YahooFinanceProvider._history_to_ohlcv_bars(history)  # noqa: SLF001

    normalized = getattr(primary, "_normalized", None)
    if normalized is None and hasattr(primary, "_adapter"):
        normalized = primary._adapter.normalized  # type: ignore[attr-defined]

    if normalized is not None:
        return list(
            normalized.get_historical_ohlcv(
                normalized_symbol,
                period=bar_period,
                interval=bar_interval,
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


def _build_series_for_plan(
    service: MarketDataService,
    symbol: str,
    timeframe: str,
    plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], Dict[str, bool]]:
    standin = get_timeframe_config(timeframe)
    bars = _fetch_bars(
        service,
        symbol,
        standin,
        period=plan["period"],
        interval=plan["interval"],
    )
    if not bars:
        raise RuntimeError("no bars returned for timeframe")
    # EMA overlay is built over the raw fetched history (the lookback), not the
    # aggregated/clipped window, so intraday EMAs warm before the visible session
    # and the weekly EMA200 converges over the full daily history.
    ema_overlay = build_ema_overlay(bars)
    if plan["weekly"]:
        display_bars = aggregate_weekly(bars)
        if not display_bars:
            raise RuntimeError("no weekly bars aggregated for timeframe")
    else:
        display_bars = bars
    indicators = _ema_availability(bars)
    series = build_display_points(display_bars, ema_overlay, plan["max_points"])
    return series, indicators


def build_chart_series(
    service: MarketDataService,
    symbol: str,
    timeframe: str,
) -> tuple[list[dict[str, Any]], str, bool, Dict[str, bool]]:
    """Return chart points, a human label, fallback flag, and EMA availability."""
    normalized_tf = normalize_timeframe(timeframe)
    config = get_timeframe_config(normalized_tf)
    used_fallback = False
    label = config.label

    try:
        series, indicators = _build_series_for_plan(
            service, symbol, normalized_tf, _DISPLAY_PLAN[normalized_tf]
        )
        if series:
            return series, label, used_fallback, indicators
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
    fallback_plan: dict[str, Any] = {
        "period": fallback.period,
        "interval": fallback.interval,
        "max_points": fallback.max_points,
        "weekly": False,
    }
    series, indicators = _build_series_for_plan(
        service, symbol, normalized_tf, fallback_plan
    )
    if not series:
        raise RuntimeError("no fallback chart points available")
    return series, label, used_fallback, indicators


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
