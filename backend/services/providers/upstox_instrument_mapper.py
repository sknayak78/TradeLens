"""Symbol-to-instrument-key mapping seam for the Upstox provider.

Upstox identifies tradable instruments by an ``instrument_key`` (for example
``NSE_EQ|INE002A01018``), not by the application's Yahoo-style symbols.  This
module hosts a small, explicit mapping seam so MD-02 never guesses an
instrument key from an arbitrary string.

The mapping is deliberately provider-specific and intentionally minimal: MD-02
only proves the provider works cleanly.  A dedicated instrument-master ER can
later replace this seam without touching the HTTP provider.
"""
from __future__ import annotations

import os
from typing import Mapping

_INSTRUMENT_KEYS_ENV = "UPSTOX_INSTRUMENT_KEYS"


def _instrument_keys_from_env() -> dict[str, str]:
    """Parse ``UPSTOX_INSTRUMENT_KEYS`` as ``SYMBOL=KEY`` comma-separated pairs."""
    raw = os.environ.get(_INSTRUMENT_KEYS_ENV, "").strip()
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(
                f"invalid {_INSTRUMENT_KEYS_ENV} entry {entry!r}; expected SYMBOL=KEY"
            )
        symbol, key = entry.split("=", 1)
        symbol_name = symbol.strip().upper()
        instrument_key = key.strip()
        if not symbol_name or not instrument_key:
            raise ValueError(
                f"invalid {_INSTRUMENT_KEYS_ENV} entry {entry!r}; SYMBOL=KEY must be non-empty"
            )
        mapping[symbol_name] = instrument_key
    return mapping


class UpstoxInstrumentMapper:
    """Translate normalized application symbols to Upstox instrument keys.

    Symbols are matched exactly against an explicit configured mapping.  A
    symbol that cannot be resolved raises ``RuntimeError`` so the existing
    MarketDataService fallback behaviour applies — the provider never guesses.
    """

    def __init__(self, mapping: Mapping[str, str] | None = None):
        seeded = dict(mapping or _instrument_keys_from_env())
        self._mapping = {
            symbol.strip().upper(): key for symbol, key in seeded.items()
        }

    def to_instrument_key(self, symbol: str) -> str:
        normalized = symbol.strip().upper()
        instrument_key = self._mapping.get(normalized)
        if instrument_key is None:
            raise RuntimeError(f"no Upstox instrument_key for symbol {normalized}")
        return instrument_key