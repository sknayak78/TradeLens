"""Normalized market-data provider contract for ER-0022."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from services.market_data.models import (
    DataFreshness,
    Instrument,
    LatencyClass,
    MarketStatus,
    OHLCVBar,
    Quote,
)


class NormalizedMarketDataProvider(ABC):
    """Provider-independent read contract used by the legacy adapter in Phase 1B."""

    name: str

    @abstractmethod
    def get_instruments(self) -> Sequence[Instrument]:
        """Return the configured instrument catalogue."""

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None:
        """Return the latest normalized quote for one symbol."""

    @abstractmethod
    def get_historical_ohlcv(
        self,
        symbol: str,
        *,
        period: str = "2y",
        interval: str = "1d",
    ) -> Sequence[OHLCVBar]:
        """Return historical OHLCV bars for one symbol."""

    def get_intraday_ohlcv(self, symbol: str) -> Sequence[OHLCVBar]:
        """Return intraday bars when supported by the provider."""
        raise NotImplementedError(
            f"{self.name} does not provide intraday OHLCV in Phase 1"
        )

    @abstractmethod
    def get_market_status(self) -> MarketStatus:
        """Return the current market session state."""

    @abstractmethod
    def freshness(self) -> DataFreshness:
        """Return provider freshness metadata for the latest read."""

    @abstractmethod
    def latency_class(self) -> LatencyClass:
        """Return the coarse latency bucket for this provider."""
