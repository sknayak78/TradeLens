"""Yahoo Finance adapter for live quote refreshes of supported NSE symbols."""
from __future__ import annotations

from copy import deepcopy
import logging
from typing import Any

from services.market_data_provider import MarketDataProvider
from services.providers.seed_provider import SeedProvider
from services.symbol_mapper import SymbolMapper

logger = logging.getLogger("tradelens.market_data.yahoo")


class YahooFinanceProvider(MarketDataProvider):
    """Overlay current Yahoo quotes on the compatibility seed dataset.

    Indicators and chart series intentionally remain seed-backed in Sprint 1.
    The adapter accepts only the existing catalogue, preserving the API's
    historical 404 behaviour for unknown symbols.
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
    def _quote(ticker_symbol: str) -> tuple[float, float, int | None]:
        history = YahooFinanceProvider._ticker(ticker_symbol).history(
            period="2d", interval="1d", auto_adjust=False
        )
        if history is None or history.empty:
            raise RuntimeError(f"Yahoo returned no history for {ticker_symbol}")
        close = float(history["Close"].iloc[-1])
        previous = float(history["Close"].iloc[-2]) if len(history.index) > 1 else close
        change_pct = ((close - previous) / previous * 100) if previous else 0.0
        volume = int(history["Volume"].iloc[-1]) if "Volume" in history else None
        return round(close, 2), round(change_pct, 2), volume

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
        price, change_pct, volume = self._quote(
            self._symbol_mapper.to_yahoo(stock["symbol"])
        )
        stock.update(price=price, changePct=change_pct)
        if volume is not None:
            stock["volume"] = volume
        return stock

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        # Intraday chart series remains seed-backed until indicator/candle work.
        return self._seed.get_stock_insight(symbol)

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
