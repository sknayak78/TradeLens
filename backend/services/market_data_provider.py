"""Provider contract for market data used by the TradeLens API."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MarketDataProvider(ABC):
    """Read-only source of market data.

    Providers return the existing internal dictionary shapes.  API routers keep
    ownership of response models so provider changes cannot alter REST contracts.
    """

    name: str

    @abstractmethod
    def get_market_summary(self) -> dict[str, Any]:
        """Return indices and today's focus entries."""

    @abstractmethod
    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        """Return one stock snapshot, or ``None`` when unknown."""

    @abstractmethod
    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        """Return compatibility chart/support/insight data for a stock."""

    @abstractmethod
    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search the provider's instrument catalogue."""

    @abstractmethod
    def get_opportunities(self) -> list[dict[str, Any]]:
        """Return curated opportunity context."""

    @abstractmethod
    def get_all_stocks(self) -> list[dict[str, Any]]:
        """Return stock snapshots used by the rankings engine."""

    @abstractmethod
    def get_default_watchlist_symbols(self) -> list[str]:
        """Return symbols to seed on an empty application watchlist."""
