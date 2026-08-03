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

    def to_yahoo(self, symbol: str) -> str:
        """Return the Yahoo NSE ticker for a normalized application symbol."""
        normalized = symbol.strip().upper()
        return self._YAHOO_SYMBOLS.get(normalized, f"{normalized}.NS")
