"""Provider contract for market data used by the TradeLens API."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from services.market_data.models import MarketQuote, OHLCVBar


class MarketDataProvider(ABC):
    """Read-only source of market data.

    Providers return the existing internal dictionary shapes.  API routers keep
    ownership of response models so provider changes cannot alter REST contracts.
    """

    name: str

    def get_bulk_market_quotes(
        self, instrument_keys: Sequence[str]
    ) -> Sequence[MarketQuote]:
        """Return normalized live snapshots for many instruments in one round trip.

        Optional capability (MD-10).  Providers that cannot serve the whole
        universe in bulk leave this as ``NotImplementedError``; callers treat
        that as "no bulk prefilter available" and keep their existing
        per-instrument path unchanged.  Implementations must return only the
        records they actually received - a short list is valid, because some
        instruments are legitimately absent from a provider response.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not support bulk market quotes"
        )

    @abstractmethod
    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        """Return historical OHLCV bars for one symbol."""

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
