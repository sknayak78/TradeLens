"""Yahoo Finance adapter for live quote refreshes of supported NSE symbols."""
from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any

from pandas import Timestamp

from indicators.ema import calculate_latest_ema
from indicators.rsi import calculate_latest_rsi
from services.market_data_provider import MarketDataProvider
from services.providers.seed_provider import SeedProvider
from services.symbol_mapper import SymbolMapper

logger = logging.getLogger("tradelens.market_data.yahoo")


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
    ):
        self._seed = seed_provider or SeedProvider()
        self._symbol_mapper = symbol_mapper or SymbolMapper()

    @staticmethod
    def _ticker(symbol: str):
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is not installed") from exc
        return yf.Ticker(symbol)

    @staticmethod
    def _history(ticker_symbol: str, period: str = "2y", interval: str = "1d"):
        history = YahooFinanceProvider._ticker(ticker_symbol).history(
            period=period, interval=interval, auto_adjust=False
        )
        if history is None or history.empty:
            raise RuntimeError(f"Yahoo returned no history for {ticker_symbol}")
        return history

    @staticmethod
    def _quote(ticker_symbol: str) -> tuple[float, float, int | None]:
        history = YahooFinanceProvider._history(ticker_symbol, period="2d", interval="1d")
        close = float(history["Close"].iloc[-1])
        previous = float(history["Close"].iloc[-2]) if len(history.index) > 1 else close
        change_pct = ((close - previous) / previous * 100) if previous else 0.0
        volume = int(history["Volume"].iloc[-1]) if "Volume" in history else None
        return round(close, 2), round(change_pct, 2), volume

    @staticmethod
    def _build_chart_series(history: Any, max_points: int = 13) -> list[dict[str, Any]]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for chart series")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")

        points: list[dict[str, Any]] = []
        for _, row in history.tail(max_points).iterrows():
            timestamp = row.name
            if isinstance(timestamp, Timestamp):
                label = timestamp.strftime("%Y-%m-%d")
            else:
                label = str(timestamp)
            points.append({"t": label, "v": round(float(row["Close"]), 2)})
        return points

    @staticmethod
    def _build_emas(history: Any) -> dict[str, float]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for EMA calculation")
        if "Close" not in history:
            raise RuntimeError("Yahoo history is missing Close prices")

        closes = [float(value) for value in history["Close"].tolist()]
        return {
            "ema20": round(calculate_latest_ema(closes, 20), 2),
            "ema50": round(calculate_latest_ema(closes, 50), 2),
            "ema200": round(calculate_latest_ema(closes, 200), 2),
        }

    @staticmethod
    def _build_support_resistance(history: Any, lookback: int = 20) -> dict[str, float]:
        if history is None or history.empty:
            raise RuntimeError("Yahoo returned no history for support/resistance calculation")
        if {"Low", "High"}.issubset(history.columns):
            recent = history.tail(lookback)
            support = float(recent["Low"].min())
            resistance = float(recent["High"].max())
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

        closes = [float(value) for value in history["Close"].tolist()]
        return round(calculate_latest_rsi(closes, period), 2)

    @staticmethod
    def _build_ai_insight(price: float, ema20: float, support: float, resistance: float) -> str:
        bias = "above" if price >= ema20 else "below"
        return (
            f"Price {price:.2f} is {bias} EMA20 {ema20:.2f}; "
            f"support {support:.2f} and resistance {resistance:.2f}."
        )

    def get_market_summary(self) -> dict[str, Any]:
        summary = self._seed.get_market_summary()
        indices: list[dict[str, Any]] = []
        for index in summary["indices"]:
            ticker = self._INDEX_TICKERS[index["symbol"]]
            value, change_pct, _ = self._quote(ticker)
            live_index = deepcopy(index)
            live_index.update(value=value, changePct=change_pct)
            indices.append(live_index)
        return {"indices": indices, "todaysFocus": summary["todaysFocus"]}

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        stock = self._seed.get_stock(symbol)
        if stock is None:
            return None

        try:
            
            yahoo_symbol = self._symbol_mapper.to_yahoo(stock["symbol"])
            price, change_pct, volume = self._quote(yahoo_symbol)
            history = self._history(yahoo_symbol, period="2y", interval="1d")
            emas = self._build_emas(history)
            support_resistance = self._build_support_resistance(history)
            rsi = self._build_rsi(history)

            stock.update(
                price=price,
                changePct=change_pct,
                rsi=rsi,
                ema20=emas["ema20"],
                ema50=emas["ema50"],
                ema200=emas["ema200"],
                support=support_resistance["support"],
                resistance=support_resistance["resistance"],
            )
            if volume is not None:
                stock["volume"] = volume
        except Exception:
            logger.warning("market_data.yahoo_live_fetch_failed_falling_back_to_seed", exc_info=True)
        return stock

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        insight = self._seed.get_stock_insight(symbol)
        normalized = symbol.strip().upper()
        stock = self._seed.get_stock(normalized)
        if stock is None:
            return insight

        try:
            yahoo_symbol = self._symbol_mapper.to_yahoo(stock["symbol"])
            price, _, _ = self._quote(yahoo_symbol)
            history = self._history(yahoo_symbol, period="2y", interval="1d")
            chart_series = self._build_chart_series(history)
            if not chart_series:
                raise RuntimeError(f"Yahoo returned no chart points for {yahoo_symbol}")

            emas = self._build_emas(history)
            support_resistance = self._build_support_resistance(history)

            hydrated = deepcopy(insight)
            hydrated["series"] = chart_series
            hydrated["support"] = support_resistance["support"]
            hydrated["resistance"] = support_resistance["resistance"]
            hydrated["aiInsight"] = self._build_ai_insight(
                price,
                emas["ema20"],
                support_resistance["support"],
                support_resistance["resistance"],
            )
            return hydrated
        except Exception:
            logger.warning("market_data.yahoo_insight_fetch_failed_falling_back_to_seed", exc_info=True)
            return insight

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        # Instrument discovery remains deterministic until a licensed master is added.
        return self._seed.search_stocks(query, limit)

    def get_opportunities(self) -> list[dict[str, Any]]:
        # Ranking signals are deliberately not recalculated in this sprint.
        return self._seed.get_opportunities()

    def get_all_stocks(self) -> list[dict[str, Any]]:
        # Avoid an N-symbol external fan-out; keep rankings compatibility-backed.
        return self._seed.get_all_stocks()

    def get_default_watchlist_symbols(self) -> list[str]:
        return self._seed.get_default_watchlist_symbols()
