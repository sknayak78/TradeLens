"""Application-symbol mappings for external market-data providers."""
from __future__ import annotations


class SymbolMapper:
    """Translate TradeLens symbols without leaking provider rules into adapters."""

    _YAHOO_SYMBOLS = {
        "RELIANCE": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "HDFCBANK": "HDFCBANK.NS",
        "INFY": "INFY.NS",
        "ICICIBANK": "ICICIBANK.NS",
        "SBIN": "SBIN.NS",
        "TATAMOTORS": "TMPV.NS",
        "BHARTIARTL": "BHARTIARTL.NS",
        "ADANIENT": "ADANIENT.NS",
        "M&M": "M&M.NS",
    }

    _ALIASES = {
        "ZOMATO": "ETERNAL",
    }

    _REVERSE_YAHOO = {
        v: k for k, v in _YAHOO_SYMBOLS.items()
    }

    def resolve_alias(self, symbol_or_query: str) -> str:
        """Resolve corporate renames/aliases (e.g. Zomato -> Eternal)."""
        normalized = symbol_or_query.strip().upper()
        return self._ALIASES.get(normalized, symbol_or_query.strip())

    def to_yahoo(self, symbol: str) -> str:
        """Return the Yahoo NSE ticker for a normalized application symbol."""
        resolved = self.resolve_alias(symbol).upper()
        return self._YAHOO_SYMBOLS.get(resolved, f"{resolved}.NS")

    def to_canonical(self, yahoo_symbol: str) -> str:
        """Return the TradeLens canonical symbol for a Yahoo ticker."""
        normalized = yahoo_symbol.strip().upper()
        if normalized in self._REVERSE_YAHOO:
            return self._REVERSE_YAHOO[normalized]
        if normalized.endswith(".NS"):
            return normalized[:-3]
        return normalized
