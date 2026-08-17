"""Yahoo Finance adapter for live quote refreshes of supported NSE symbols."""
from __future__ import annotations

from copy import deepcopy
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from pandas import Timestamp

from services.market_data.indicators import (
    calculate_latest_ema,
    calculate_latest_rsi,
    calculate_rolling_vwap,
)
from services.market_data.legacy_adapter import (
    LegacyBatchCatalogueSupport,
    LegacyCatalogueSupport,
    LegacyProviderAdapter,
)
from services.market_data.models import (
    DataFreshness,
    Instrument,
    LatencyClass,
    MarketStatus,
    OHLCVBar,
    OpportunityContext,
    Quote,
    StockInsight,
    StockSnapshot,
)
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.session import current_market_status
from services.market_data_provider import MarketDataProvider
from services.providers.seed_provider import SeedMarketDataProvider, SeedProvider
from services.symbol_mapper import SymbolMapper

logger = logging.getLogger("tradelens.market_data.yahoo")

HistoryFetcher = Callable[[str, str, str], Any]
QuoteFetcher = Callable[[str], tuple[float, float, int | None]]

_DEFAULT_BUNDLE_TTL_SECONDS = 30.0
_MAX_BUNDLE_CACHE_ENTRIES = 128


@dataclass(frozen=True)
class _YahooSymbolBundle:
    """Private per-symbol Yahoo payload reused across stock and insight reads."""

    symbol: str
    quote: Quote
    ohlcv_bars: tuple[OHLCVBar, ...]
    snapshot: StockSnapshot
    insight: StockInsight
    fetched_at: datetime


@dataclass
class _BundleCacheEntry:
    bundle: _YahooSymbolBundle
    expires_at: float


class YahooMarketDataProvider(
    NormalizedMarketDataProvider,
    LegacyCatalogueSupport,
    LegacyBatchCatalogueSupport,
):
    """Normalized Yahoo overlay with seed catalogue delegation and bundle caching."""

    name = "yahoo_finance"

    def __init__(
        self,
        seed_provider: SeedMarketDataProvider,
        *,
        symbol_mapper: SymbolMapper | None = None,
        history_fetcher: HistoryFetcher | None = None,
        quote_fetcher: QuoteFetcher | None = None,
        bundle_ttl_seconds: float = _DEFAULT_BUNDLE_TTL_SECONDS,
        clock: Callable[[], float] | None = None,
    ):
        self._seed = seed_provider
        self._symbol_mapper = symbol_mapper or SymbolMapper()
        self._history_fetcher = history_fetcher or YahooFinanceProvider._fetch_history
        self._quote_fetcher = quote_fetcher
        self._bundle_ttl_seconds = bundle_ttl_seconds
        self._clock = clock or time.monotonic
        self._bundle_cache: dict[str, _BundleCacheEntry] = {}
        self._quote_history_context: dict[str, Any] = {}

    def bind_quote_fetcher(self, fetcher: QuoteFetcher) -> None:
        """Attach the legacy façade quote hook used by compatibility tests."""
        self._quote_fetcher = fetcher

    def bind_history_fetcher(self, fetcher: HistoryFetcher) -> None:
        """Attach the legacy façade history hook used by compatibility tests."""
        self._history_fetcher = fetcher

    def clear_bundle_cache(self) -> None:
        self._bundle_cache.clear()
        self._quote_history_context.clear()

    def bundle_cache_size(self) -> int:
        return len(self._bundle_cache)

    def get_instruments(self) -> Sequence[Instrument]:
        return self._seed.get_instruments()

    def get_quote(self, symbol: str) -> Quote | None:
        bundle = self._load_bundle(symbol)
        if bundle is not None:
            return bundle.quote
        return self._seed.get_quote(symbol)

    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        bundle = self._load_bundle(symbol)
        if bundle is not None:
            return bundle.ohlcv_bars
        return self._seed.get_historical_ohlcv(symbol, period=period, interval=interval)

    def get_market_status(self) -> MarketStatus:
        return current_market_status()

    def freshness(self) -> DataFreshness:
        when = datetime.now(timezone.utc)
        return DataFreshness(
            provider=self.name,
            observed_at=when,
            latency_class=self.latency_class(),
            stale=False,
        )

    def latency_class(self) -> LatencyClass:
        return "delayed"

    def stock_snapshot(self, symbol: str) -> StockSnapshot | None:
        seed_snapshot = self._seed.stock_snapshot(symbol)
        if seed_snapshot is None:
            return None
        bundle = self._load_bundle(symbol)
        if bundle is None:
            return seed_snapshot
        return self._merge_snapshot(seed_snapshot, bundle.snapshot)

    def stock_insight(self, symbol: str) -> StockInsight | None:
        seed_insight = self._seed.stock_insight(symbol)
        if seed_insight is None:
            return None
        if self._seed.stock_snapshot(symbol) is None:
            return seed_insight
        bundle = self._load_bundle(symbol)
        if bundle is None:
            return seed_insight
        return bundle.insight

    def all_stock_snapshots(self) -> Sequence[StockSnapshot]:
        return self._seed.all_stock_snapshots()

    def search_stock_snapshots(self, query: str, limit: int = 20) -> Sequence[StockSnapshot]:
        return self._seed.search_stock_snapshots(query, limit)

    def market_summary(self) -> dict[str, Any]:
        summary = deepcopy(self._seed.market_summary())
        indices: list[dict[str, Any]] = []
        for index in summary["indices"]:
            ticker = YahooFinanceProvider._INDEX_TICKERS[index["symbol"]]
            value, change_pct, _ = self._resolve_quote(ticker)
            live_index = deepcopy(index)
            live_index.update(value=value, changePct=change_pct)
            indices.append(live_index)
        return {"indices": indices, "todaysFocus": summary["todaysFocus"]}

    def opportunity_contexts(self) -> Sequence[OpportunityContext]:
        return self._seed.opportunity_contexts()

    def watchlist_symbols(self) -> Sequence[str]:
        return self._seed.watchlist_symbols()

    def history_call_count(self) -> int:
        return getattr(self._history_fetcher, "call_count", 0)

    def _resolve_quote(self, ticker_symbol: str) -> tuple[float, float, int | None]:
        if self._quote_fetcher is not None:
            return self._quote_fetcher(ticker_symbol)
        cached_history = self._quote_history_context.get(ticker_symbol)
        if cached_history is not None:
            return YahooFinanceProvider._quote_from_history(cached_history)
        return YahooFinanceProvider._fetch_quote(ticker_symbol)

    def _load_bundle(self, symbol: str) -> _YahooSymbolBundle | None:
        normalized = symbol.strip().upper()
        now = self._clock()
        cached = self._bundle_cache.get(normalized)
        if cached is not None and cached.expires_at > now:
            return cached.bundle
        if cached is not None:
            del self._bundle_cache[normalized]

        seed_snapshot = self._seed.stock_snapshot(normalized)
        if seed_snapshot is None:
            return None

        try:
            yahoo_symbol = self._symbol_mapper.to_yahoo(normalized)
            history = self._history_fetcher(yahoo_symbol, period="2y", interval="1d")
            if history is None or getattr(history, "empty", False):
                raise RuntimeError(f"Yahoo returned no history for {yahoo_symbol}")

            self._quote_history_context[yahoo_symbol] = history
            try:
                price, change_pct, volume = self._resolve_quote(yahoo_symbol)
            finally:
                self._quote_history_context.pop(yahoo_symbol, None)

            bundle = self._build_bundle(
                normalized,
                seed_snapshot=seed_snapshot,
                seed_insight=self._seed.stock_insight(normalized),
                history=history,
                price=price,
                change_pct=change_pct,
                volume=volume,
            )
            self._store_bundle(normalized, bundle, now)
            return bundle
        except Exception:
            logger.warning(
                "market_data.yahoo_live_fetch_failed_falling_back_to_seed",
                exc_info=True,
            )
            return None

    def _store_bundle(
        self,
        symbol: str,
        bundle: _YahooSymbolBundle,
        now: float,
    ) -> None:
        if len(self._bundle_cache) >= _MAX_BUNDLE_CACHE_ENTRIES:
            oldest_symbol = min(
                self._bundle_cache,
                key=lambda key: self._bundle_cache[key].expires_at,
            )
            del self._bundle_cache[oldest_symbol]
        self._bundle_cache[symbol] = _BundleCacheEntry(
            bundle=bundle,
            expires_at=now + self._bundle_ttl_seconds,
        )

    def _build_bundle(
        self,
        symbol: str,
        *,
        seed_snapshot: StockSnapshot,
        seed_insight: StockInsight | None,
        history: Any,
        price: float,
        change_pct: float,
        volume: int | None,
    ) -> _YahooSymbolBundle:
        emas = YahooFinanceProvider._build_emas(history)
        support_resistance = YahooFinanceProvider._build_support_resistance(history)
        rsi = YahooFinanceProvider._build_rsi(history)
        vwap = YahooFinanceProvider._build_vwap(history)
        chart_series = YahooFinanceProvider._build_chart_series(history)
        if not chart_series:
            raise RuntimeError(f"Yahoo returned no chart points for {symbol}")

        resolved_volume = volume if volume is not None else seed_snapshot.volume
        when = datetime.now(timezone.utc)
        snapshot = StockSnapshot(
            symbol=seed_snapshot.symbol,
            name=seed_snapshot.name,
            sector=seed_snapshot.sector,
            price=price,
            change_pct=change_pct,
            rsi=rsi,
            ema20=emas["ema20"],
            ema50=emas["ema50"],
            ema200=emas["ema200"],
            vwap=vwap,
            volume=resolved_volume,
            trend=seed_snapshot.trend,
            day_high=seed_snapshot.day_high,
            avg_volume=seed_snapshot.avg_volume,
            score=seed_snapshot.score,
            support=support_resistance["support"],
            resistance=support_resistance["resistance"],
        )
        insight = StockInsight(
            symbol=symbol,
            support=support_resistance["support"],
            resistance=support_resistance["resistance"],
            ai_insight=YahooFinanceProvider._build_ai_insight(
                price,
                emas["ema20"],
                support_resistance["support"],
                support_resistance["resistance"],
            ),
            series=tuple(dict(point) for point in chart_series),
        )
        if seed_insight is not None and not chart_series:
            insight = seed_insight

        quote = Quote(
            symbol=symbol,
            price=price,
            change_pct=change_pct,
            volume=resolved_volume,
            observed_at=when,
        )
        ohlcv_bars = tuple(YahooFinanceProvider._history_to_ohlcv_bars(history))
        return _YahooSymbolBundle(
            symbol=symbol,
            quote=quote,
            ohlcv_bars=ohlcv_bars,
            snapshot=snapshot,
            insight=insight,
            fetched_at=when,
        )

    @staticmethod
    def _merge_snapshot(
        seed_snapshot: StockSnapshot,
        yahoo_snapshot: StockSnapshot,
    ) -> StockSnapshot:
        return StockSnapshot(
            symbol=seed_snapshot.symbol,
            name=seed_snapshot.name,
            sector=seed_snapshot.sector,
            price=yahoo_snapshot.price,
            change_pct=yahoo_snapshot.change_pct,
            rsi=yahoo_snapshot.rsi,
            ema20=yahoo_snapshot.ema20,
            ema50=yahoo_snapshot.ema50,
            ema200=yahoo_snapshot.ema200,
            vwap=yahoo_snapshot.vwap,
            volume=yahoo_snapshot.volume,
            trend=seed_snapshot.trend,
            day_high=seed_snapshot.day_high,
            avg_volume=seed_snapshot.avg_volume,
            score=seed_snapshot.score,
            support=yahoo_snapshot.support,
            resistance=yahoo_snapshot.resistance,
        )


class YahooFinanceProvider(MarketDataProvider):
    """Overlay Yahoo market quotes and historical closes on the compatibility seed dataset.

    Support/resistance now come from Yahoo historical OHLC data, while the rest of the
    compatibility-backed insight contract remains intact.
    """

    name = "yahoo_finance"
    _INDEX_TICKERS = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "INDIAVIX": "^INDIAVIX",
    }

    def __init__(
        self,
        seed_provider: SeedProvider | None = None,
        symbol_mapper: SymbolMapper | None = None,
        *,
        universe: Any | None = None,
        bundle_ttl_seconds: float = _DEFAULT_BUNDLE_TTL_SECONDS,
        clock: Callable[[], float] | None = None,
    ):
        self._seed_provider = seed_provider or SeedProvider(universe)
        seed_normalized = self._seed_provider._adapter.normalized
        if not isinstance(seed_normalized, SeedMarketDataProvider):
            seed_normalized = SeedMarketDataProvider(universe)
        self._normalized = YahooMarketDataProvider(
            seed_normalized,
            symbol_mapper=symbol_mapper,
            history_fetcher=lambda sym, period, interval: self._history(sym, period, interval),
            quote_fetcher=lambda sym: self._quote(sym),
            bundle_ttl_seconds=bundle_ttl_seconds,
            clock=clock,
        )
        self._adapter = LegacyProviderAdapter(self._normalized)

    def _history(self, ticker_symbol: str, period: str = "2y", interval: str = "1d"):
        return YahooFinanceProvider._fetch_history(ticker_symbol, period, interval)

    def _quote(self, ticker_symbol: str) -> tuple[float, float, int | None]:
        cached_history = self._normalized._quote_history_context.get(ticker_symbol)
        if cached_history is not None:
            return YahooFinanceProvider._quote_from_history(cached_history)
        return YahooFinanceProvider._fetch_quote(ticker_symbol)

    def get_market_summary(self) -> dict[str, Any]:
        return self._adapter.get_market_summary()

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        return self._adapter.get_stock(symbol)

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        return self._adapter.get_stock_insight(symbol)

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._adapter.search_stocks(query, limit)

    def get_opportunities(self) -> list[dict[str, Any]]:
        return self._adapter.get_opportunities()

    def get_all_stocks(self) -> list[dict[str, Any]]:
        return self._adapter.get_all_stocks()

    def get_default_watchlist_symbols(self) -> list[str]:
        return self._adapter.get_default_watchlist_symbols()

    @staticmethod
    def _ticker(symbol: str):
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is not installed") from exc
        return yf.Ticker(symbol)

    @staticmethod
    def _fetch_history(ticker_symbol: str, period: str = "2y", interval: str = "1d"):
        history = YahooFinanceProvider._ticker(ticker_symbol).history(
            period=period, interval=interval, auto_adjust=False
        )
        if history is None or history.empty:
            raise RuntimeError(f"Yahoo returned no history for {ticker_symbol}")
        return history

    @staticmethod
    def _finite(value: Any, label: str) -> float:
        """Return ``value`` as a float, rejecting NaN and infinity."""
        number = float(value)
        if not math.isfinite(number):
            raise RuntimeError(f"Yahoo returned a non-finite {label}")
        return number

    @staticmethod
    def _complete_bars(history: Any):
        """Drop rows without a close price."""
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")
        complete = history[history["Close"].notna()]
        if complete.empty:
            raise RuntimeError("Yahoo history has no completed bars")
        return complete

    @staticmethod
    def _quote_from_history(history: Any) -> tuple[float, float, int | None]:
        complete = YahooFinanceProvider._complete_bars(history)
        close = YahooFinanceProvider._finite(complete["Close"].iloc[-1], "close")
        previous = (
            YahooFinanceProvider._finite(complete["Close"].iloc[-2], "previous close")
            if len(complete.index) > 1
            else close
        )
        change_pct = ((close - previous) / previous * 100) if previous else 0.0
        volume: int | None = None
        if "Volume" in history:
            raw_volume = complete["Volume"].iloc[-1]
            if raw_volume is not None and math.isfinite(float(raw_volume)):
                volume = int(raw_volume)
        return round(close, 2), round(change_pct, 2), volume

    @staticmethod
    def _fetch_quote(ticker_symbol: str) -> tuple[float, float, int | None]:
        history = YahooFinanceProvider._complete_bars(
            YahooFinanceProvider._fetch_history(ticker_symbol, period="2d", interval="1d")
        )
        return YahooFinanceProvider._quote_from_history(history)

    @staticmethod
    def _build_chart_series(history: Any, max_points: int = 13) -> list[dict[str, Any]]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for chart series")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")

        points: list[dict[str, Any]] = []
        for _, row in YahooFinanceProvider._complete_bars(history).tail(max_points).iterrows():
            timestamp = row.name
            if isinstance(timestamp, Timestamp):
                label = timestamp.strftime("%Y-%m-%d")
            else:
                label = str(timestamp)
            points.append({
                "t": label,
                "v": round(YahooFinanceProvider._finite(row["Close"], "close"), 2),
            })
        return points

    @staticmethod
    def _build_emas(history: Any) -> dict[str, float]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for EMA calculation")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")

        closes = YahooFinanceProvider._closes(history)
        return {
            "ema20": round(
                YahooFinanceProvider._finite(
                    calculate_latest_ema(closes, 20), "EMA20"
                ), 2
            ),
            "ema50": round(
                YahooFinanceProvider._finite(
                    calculate_latest_ema(closes, 50), "EMA50"
                ), 2
            ),
            "ema200": round(
                YahooFinanceProvider._finite(
                    calculate_latest_ema(closes, 200), "EMA200"
                ), 2
            ),
        }

    @staticmethod
    def _closes(history: Any) -> list[float]:
        return [
            YahooFinanceProvider._finite(value, "close")
            for value in YahooFinanceProvider._complete_bars(history)["Close"].tolist()
        ]

    @staticmethod
    def _build_vwap(history: Any, lookback: int = 20) -> float:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for VWAP calculation")
        if not {"High", "Low", "Close", "Volume"}.issubset(history.columns):
            raise RuntimeError("Yahoo history is missing High/Low/Close/Volume")

        bars = YahooFinanceProvider._complete_bars(history)
        vwap = calculate_rolling_vwap(
            highs=[YahooFinanceProvider._finite(v, "high") for v in bars["High"]],
            lows=[YahooFinanceProvider._finite(v, "low") for v in bars["Low"]],
            closes=[YahooFinanceProvider._finite(v, "close") for v in bars["Close"]],
            volumes=[float(v or 0) for v in bars["Volume"]],
            period=lookback,
        )
        return round(YahooFinanceProvider._finite(vwap, "VWAP"), 2)

    @staticmethod
    def _build_support_resistance(history: Any, lookback: int = 20) -> dict[str, float]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for support/resistance calculation")
        if {"Low", "High"}.issubset(history.columns):
            recent = YahooFinanceProvider._complete_bars(history).tail(lookback)
            support = YahooFinanceProvider._finite(recent["Low"].min(), "support")
            resistance = YahooFinanceProvider._finite(
                recent["High"].max(), "resistance"
            )
            return {
                "support": round(support, 2),
                "resistance": round(resistance, 2),
            }
        raise RuntimeError("Yahoo history is missing Low/High prices")

    @staticmethod
    def _build_rsi(history: Any, period: int = 14) -> float:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for RSI calculation")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")

        closes = YahooFinanceProvider._closes(history)
        return round(
            YahooFinanceProvider._finite(
                calculate_latest_rsi(closes, period), "RSI"
            ), 2
        )

    @staticmethod
    def _build_ai_insight(price: float, ema20: float, support: float, resistance: float) -> str:
        bias = "above" if price >= ema20 else "below"
        return (
            f"Price {price:.2f} is {bias} EMA20 {ema20:.2f}; "
            f"support {support:.2f} and resistance {resistance:.2f}."
        )

    @staticmethod
    def _history_to_ohlcv_bars(history: Any) -> list[OHLCVBar]:
        bars: list[OHLCVBar] = []
        for index, row in YahooFinanceProvider._complete_bars(history).iterrows():
            timestamp = index.to_pydatetime() if isinstance(index, Timestamp) else index
            if not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            volume_value = row["Volume"] if "Volume" in row else None
            bars.append(
                OHLCVBar(
                    timestamp=timestamp,
                    open=YahooFinanceProvider._finite(row["Open"], "open"),
                    high=YahooFinanceProvider._finite(row["High"], "high"),
                    low=YahooFinanceProvider._finite(row["Low"], "low"),
                    close=YahooFinanceProvider._finite(row["Close"], "close"),
                    volume=float(volume_value) if volume_value is not None else None,
                )
            )
        return bars
