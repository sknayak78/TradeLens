"""Regression tests for Upstox provider-level symbol alias resolution.

Tata Motors demerged into ``TMCV``/``TMPV``, so the canonical TradeLens symbol
``TATAMOTORS`` no longer matches any NSE trading symbol and the Upstox
instrument master does not list it.  Resolution therefore happens in
``UpstoxMarketDataProvider`` via :meth:`SymbolMapper.to_listing_symbol`,
immediately before the instrument mapper performs its exact ``trading_symbol``
-> ``instrument_key`` lookup.

``UpstoxInstrumentMapper`` is intentionally exact-match and must not guess, so
these tests pin the alias seam on the provider and the non-guessing contract on
the mapper separately.

All tests are deterministic and never call the real Upstox API: HTTP is
simulated through the provider's injected ``fetcher`` seam.
"""
from __future__ import annotations

from typing import Any

import pytest

from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
from services.providers.upstox_provider import UpstoxMarketDataProvider
from services.symbol_mapper import SymbolMapper

TATAMOTORS_KEY = "NSE_EQ|INE155A01022"
TMPV_KEY = "NSE_EQ|INE155A01022"
ETERNAL_KEY = "NSE_EQ|INE0R2S01018"

#: Mirrors the shape of the bundled master: keyed by exchange trading symbol.
MASTER_MAPPING = {
    "TCS": "NSE_EQ|INE467B01029",
    "INFY": "NSE_EQ|INE009A01021",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TMPV": TMPV_KEY,
    "ETERNAL": ETERNAL_KEY,
}

CANDLE = ["2026-09-04T09:15:00+05:30", 980.0, 995.0, 975.0, 990.5, 42000, 0]


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _RecordingFetcher:
    """Records the requested URL so tests can assert the instrument key used."""

    def __init__(self):
        self.calls: list[str] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Any:
        # Upstox path segments URL-encode the "|" separator as "%7C".
        self.calls.append(url.replace("%7C", "|"))
        return _FakeResponse(
            {"status": "success", "data": {"candles": [CANDLE, CANDLE]}}
        )


def _provider(fetcher: Any, mapping: dict[str, str] | None = None) -> UpstoxMarketDataProvider:
    return UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=UpstoxInstrumentMapper(
            master_mapping=mapping if mapping is not None else dict(MASTER_MAPPING)
        ),
        symbol_mapper=SymbolMapper(),
        fetcher=fetcher,
    )


# ---------------------------------------------------------------------------
# Provider-level alias resolution
# ---------------------------------------------------------------------------

def test_tatamotors_resolves_to_demerged_listing_through_provider() -> None:
    """TATAMOTORS must reach the master as TMPV and fetch without error."""
    recording = _RecordingFetcher()
    provider = _provider(recording)

    bars = provider.get_historical_ohlcv("TATAMOTORS", period="1mo", interval="1d")

    assert len(bars) == 2
    assert recording.calls, "expected one upstream request"
    assert TATAMOTORS_KEY in recording.calls[0], (
        f"expected {TATAMOTORS_KEY} in requested URL, got: {recording.calls[0]}"
    )
    # The canonical TradeLens symbol must not leak into the provider URL.
    assert "TATAMOTORS" not in recording.calls[0]


def test_identity_symbols_resolve_unchanged_through_provider() -> None:
    """TCS, INFY, HDFCBANK and RELIANCE keep exact-match behaviour."""
    for symbol, key in (
        ("TCS", "NSE_EQ|INE467B01029"),
        ("INFY", "NSE_EQ|INE009A01021"),
        ("HDFCBANK", "NSE_EQ|INE040A01034"),
        ("RELIANCE", "NSE_EQ|INE002A01018"),
    ):
        recording = _RecordingFetcher()
        provider = _provider(recording)

        bars = provider.get_historical_ohlcv(symbol, period="1mo", interval="1d")

        assert len(bars) == 2, symbol
        assert key in recording.calls[0], f"{symbol}: {recording.calls[0]}"


def test_zomato_alias_resolves_through_same_mechanism() -> None:
    """ZOMATO -> ETERNAL uses the identical alias seam as TATAMOTORS -> TMPV."""
    recording = _RecordingFetcher()
    provider = _provider(recording)

    bars = provider.get_historical_ohlcv("ZOMATO", period="1mo", interval="1d")

    assert len(bars) == 2
    assert ETERNAL_KEY in recording.calls[0], recording.calls[0]
    assert "ZOMATO" not in recording.calls[0]


def test_unmapped_symbol_still_raises_so_chain_can_fall_back() -> None:
    """An unknown symbol keeps failing loudly rather than being guessed."""
    provider = _provider(_RecordingFetcher())

    with pytest.raises(RuntimeError, match="no Upstox instrument_key for symbol NOTREAL"):
        provider.get_historical_ohlcv("NOTREAL", period="1mo", interval="1d")


# ---------------------------------------------------------------------------
# SymbolMapper: provider-neutral vocabulary seam
# ---------------------------------------------------------------------------

def test_to_listing_symbol_maps_demerger_and_alias() -> None:
    mapper = SymbolMapper()
    assert mapper.to_listing_symbol("TATAMOTORS") == "TMPV"
    assert mapper.to_listing_symbol("ZOMATO") == "ETERNAL"


def test_to_listing_symbol_is_identity_for_normal_symbols() -> None:
    mapper = SymbolMapper()
    for symbol in ("TCS", "INFY", "HDFCBANK", "RELIANCE"):
        assert mapper.to_listing_symbol(symbol) == symbol
        assert mapper.to_listing_symbol(symbol.lower()) == symbol


def test_to_listing_symbol_does_not_mutate_canonical_vocabulary() -> None:
    """The alias seam is read-only with respect to TradeLens' own symbols."""
    mapper = SymbolMapper()
    assert mapper.to_canonical("TMPV.NS") == "TATAMOTORS"
    assert mapper.to_yahoo("TATAMOTORS") == "TMPV.NS"


# ---------------------------------------------------------------------------
# UpstoxInstrumentMapper: exact-match contract must remain intact
# ---------------------------------------------------------------------------

def test_instrument_mapper_still_exact_matches_and_never_guesses() -> None:
    """The mapper alone must not resolve TATAMOTORS; the provider owns that."""
    mapper = UpstoxInstrumentMapper(master_mapping=dict(MASTER_MAPPING))

    assert mapper.to_instrument_key("TMPV") == TMPV_KEY
    with pytest.raises(RuntimeError, match="no Upstox instrument_key for symbol TATAMOTORS"):
        mapper.to_instrument_key("TATAMOTORS")
    with pytest.raises(RuntimeError, match="no Upstox instrument_key for symbol TMP"):
        mapper.to_instrument_key("TMP")


def test_instrument_mapper_does_not_contain_provider_aliases() -> None:
    """Alias vocabulary belongs to SymbolMapper, not the instrument mapper."""
    assert not hasattr(UpstoxInstrumentMapper, "_LISTING_SYMBOLS")
    assert not hasattr(UpstoxInstrumentMapper, "_ALIASES")
