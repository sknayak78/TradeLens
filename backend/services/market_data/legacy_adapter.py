"""Bridge normalized providers onto the legacy MarketDataProvider contract."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol, Sequence, runtime_checkable

from services.market_data.models import StockInsight, StockSnapshot
from services.market_data.normalized_provider import NormalizedMarketDataProvider
from services.market_data.snapshot_builder import (
    build_legacy_insight_dict,
    build_legacy_opportunity_rows,
    build_legacy_stock_dict,
)
from services.market_data_provider import MarketDataProvider


@runtime_checkable
class LegacyCatalogueSupport(Protocol):
    """Optional catalogue helpers used before providers are fully normalized."""

    def stock_snapshot(self, symbol: str) -> StockSnapshot | None:
        """Return a full normalized snapshot for legacy stock conversion."""

    def stock_insight(self, symbol: str) -> StockInsight | None:
        """Return a normalized insight payload for one symbol."""

    def market_summary(self) -> dict[str, Any]:
        """Return legacy market summary payload."""

    def opportunity_contexts(self) -> Sequence[Any]:
        """Return curated opportunity contexts or legacy opportunity rows."""

    def watchlist_symbols(self) -> Sequence[str]:
        """Return default watchlist seed symbols."""


class LegacyProviderAdapter(MarketDataProvider):
    """Expose a NormalizedMarketDataProvider through the legacy dict contract.

    Compatibility conversion to legacy dictionaries happens exclusively through
    ``StockSnapshot.to_legacy_dict``, ``StockInsight.to_legacy_dict``, and the
  helpers in ``snapshot_builder``.
    """

    def __init__(self, normalized: NormalizedMarketDataProvider):
        self._normalized = normalized
        self.name = normalized.name

    @property
    def normalized(self) -> NormalizedMarketDataProvider:
        return self._normalized

    def _catalogue(self) -> LegacyCatalogueSupport | None:
        if isinstance(self._normalized, LegacyCatalogueSupport):
            return self._normalized
        return None

    def get_market_summary(self) -> dict[str, Any]:
        catalogue = self._catalogue()
        if catalogue is not None:
            return deepcopy(catalogue.market_summary())
        return {"indices": [], "todaysFocus": []}

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        normalized_symbol = symbol.strip().upper()
        catalogue = self._catalogue()
        if catalogue is not None:
            snapshot = catalogue.stock_snapshot(normalized_symbol)
            if snapshot is not None:
                return build_legacy_stock_dict(snapshot)
        quote = self._normalized.get_quote(normalized_symbol)
        if quote is None:
            return None
        instrument = next(
            (
                item
                for item in self._normalized.get_instruments()
                if item.symbol == normalized_symbol
            ),
            None,
        )
        if instrument is None:
            return None
        raise RuntimeError(
            "normalized provider lacks catalogue snapshot support for legacy stock rows"
        )

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        normalized_symbol = symbol.strip().upper()
        catalogue = self._catalogue()
        if catalogue is not None:
            insight = catalogue.stock_insight(normalized_symbol)
            if insight is not None:
                return build_legacy_insight_dict(insight)
        raise RuntimeError(
            "normalized provider lacks catalogue insight support for legacy insight rows"
        )

    def search_stocks(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        needle = query.strip().lower()
        matches: list[dict[str, Any]] = []
        for instrument in self._normalized.get_instruments():
            if (
                not needle
                or needle in instrument.symbol.lower()
                or needle in instrument.name.lower()
            ):
                stock = self.get_stock(instrument.symbol)
                if stock is not None:
                    matches.append(stock)
            if len(matches) >= max(1, min(limit, 100)):
                break
        return deepcopy(matches)

    def get_opportunities(self) -> list[dict[str, Any]]:
        catalogue = self._catalogue()
        if catalogue is None:
            return []
        contexts = catalogue.opportunity_contexts()
        if not contexts:
            return []
        first = contexts[0]
        if isinstance(first, dict):
            return deepcopy(list(contexts))  # type: ignore[arg-type]
        return build_legacy_opportunity_rows(contexts)  # type: ignore[arg-type]

    def get_all_stocks(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for instrument in self._normalized.get_instruments():
            stock = self.get_stock(instrument.symbol)
            if stock is not None:
                rows.append(stock)
        return deepcopy(rows)

    def get_default_watchlist_symbols(self) -> list[str]:
        catalogue = self._catalogue()
        if catalogue is not None:
            return list(catalogue.watchlist_symbols())
        return [instrument.symbol for instrument in self._normalized.get_instruments()]
