"""Configurable instrument universe for TradeLens.

The universe is application configuration, not a provider concern. Providers
continue to serve data via MarketDataService; screening and opportunity
selection read the catalogue through this abstraction.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from seed_data import (
    DEFAULT_WATCHLIST_SYMBOLS,
    INSIGHTS,
    MARKET_INDICES,
    OPPORTUNITIES,
    STOCKS,
    TODAYS_FOCUS,
    synthesize_insight,
)
from services.market_data.models import Instrument, OpportunityContext, UniverseConfig


class InstrumentUniverse:
    """Read-only view of the configured TradeLens instrument catalogue."""

    def __init__(
        self,
        stocks: list[dict[str, Any]] | None = None,
        opportunities: list[dict[str, Any]] | None = None,
        watchlist_symbols: list[str] | None = None,
        config: UniverseConfig | None = None,
    ):
        self._stocks = stocks if stocks is not None else STOCKS
        self._stocks_by_symbol = {s["symbol"]: s for s in self._stocks}
        self._opportunities = opportunities if opportunities is not None else OPPORTUNITIES
        self._watchlist_symbols = (
            watchlist_symbols if watchlist_symbols is not None else DEFAULT_WATCHLIST_SYMBOLS
        )
        self._config = config or UniverseConfig(
            name="TradeLens Demo Universe",
            active=True,
            description="Deterministic 40-stock development universe for TradeLens.",
        )

    @property
    def config(self) -> UniverseConfig:
        return self._config

    @property
    def stock_count(self) -> int:
        return len(self._stocks)

    @property
    def opportunity_count(self) -> int:
        return len(self._opportunities)

    def instruments(self) -> list[Instrument]:
        return [
            Instrument(
                symbol=s["symbol"],
                name=s["name"],
                sector=s.get("sector", ""),
                active=True,
            )
            for s in self._stocks
        ]

    def screening_instruments(self) -> list[Instrument]:
        """Return active instruments that form the candidate screening universe."""
        if not self._config.active:
            return []
        return self.instruments()

    def screening_symbols(self) -> list[str]:
        return [instrument.symbol for instrument in self.screening_instruments()]

    def opportunity_symbols(self) -> list[str]:
        return [o["symbol"] for o in self._opportunities]

    def opportunities(self) -> list[OpportunityContext]:
        return [
            OpportunityContext(symbol=o["symbol"], score=o["score"], reason=o["reason"])
            for o in self._opportunities
        ]

    def legacy_reasons(self) -> dict[str, str]:
        """Curated reason strings from the legacy OPPORTUNITIES list."""
        return {o.symbol: o.reason for o in self.opportunities()}

    def watchlist_symbols(self) -> list[str]:
        return list(self._watchlist_symbols)

    def stock_row(self, symbol: str) -> dict[str, Any] | None:
        row = self._stocks_by_symbol.get(symbol.strip().upper())
        return deepcopy(row) if row else None

    def all_stock_rows(self) -> list[dict[str, Any]]:
        return deepcopy(self._stocks)

    def search_stock_rows(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        matches = [
            stock
            for stock in self._stocks
            if not needle
            or needle in stock["symbol"].lower()
            or needle in stock["name"].lower()
        ]
        return deepcopy(matches[: max(1, min(limit, 100))])

    def market_summary_seed(self) -> dict[str, Any]:
        return {
            "indices": deepcopy(MARKET_INDICES),
            "todaysFocus": deepcopy(TODAYS_FOCUS),
        }

    def insight_row(self, symbol: str) -> dict[str, Any]:
        normalized = symbol.strip().upper()
        return deepcopy(INSIGHTS.get(normalized) or synthesize_insight(normalized))


#: Default development universe — 40 stocks screened for Today's Opportunities.
default_universe = InstrumentUniverse()
