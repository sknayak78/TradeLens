"""Provider exposing TradeLens' existing deterministic seed dataset."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from services.market_data_provider import MarketDataProvider
from seed_data import (
    DEFAULT_WATCHLIST_SYMBOLS,
    MARKET_INDICES,
    OPPORTUNITIES,
    INSIGHTS,
    STOCKS,
    STOCKS_BY_SYMBOL,
    TODAYS_FOCUS,
    synthesize_insight,
)


class SeedProvider(MarketDataProvider):
    """Canonical compatibility provider for the pre-existing mock dataset."""

    name = "seed"

    def get_market_summary(self) -> dict[str, Any]:
        return {
            "indices": deepcopy(MARKET_INDICES),
            "todaysFocus": deepcopy(TODAYS_FOCUS),
        }

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        stock = STOCKS_BY_SYMBOL.get(symbol.strip().upper())
        return deepcopy(stock) if stock else None

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        return deepcopy(INSIGHTS.get(normalized) or synthesize_insight(normalized))

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        matches = [
            stock for stock in STOCKS
            if not needle
            or needle in stock["symbol"].lower()
            or needle in stock["name"].lower()
        ]
        return deepcopy(matches[:max(1, min(limit, 100))])

    def get_opportunities(self) -> list[dict[str, Any]]:
        return deepcopy(OPPORTUNITIES)

    def get_all_stocks(self) -> list[dict[str, Any]]:
        return deepcopy(STOCKS)

    def get_default_watchlist_symbols(self) -> list[str]:
        return list(DEFAULT_WATCHLIST_SYMBOLS)
