"""MD-02 focused tests for the Upstox historical OHLCV provider.

All tests are deterministic and never call the real Upstox API.  HTTP is
simulated through the provider's injected ``fetcher`` seam.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from services.market_data.models import OHLCVBar
from services.market_data_service import MarketDataService
from services.market_data_provider import MarketDataProvider
from services.providers.seed_provider import SeedProvider
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
from services.providers.upstox_provider import UpstoxMarketDataProvider

RELIANCE_KEY = "NSE_EQ|INE002A01018"
FIXED_NOW = datetime(2026, 9, 7, 6, 0, tzinfo=timezone.utc)

CANDLE = [
    "2026-09-07T09:15:00+05:30",
    3000.5,
    3010.0,
    2995.0,
    3008.25,
    12500,
    0,
]


def _realistic_response(*candles: list[Any]) -> dict[str, Any]:
    return {"status": "success", "data": {"candles": list(candles)}}


class _FakeResponse:
    """Response-like object with a ``.json()`` method (requests.Response shape)."""

    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _RecordingFetcher:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Any:
        self.calls.append((url, headers, timeout))
        return _FakeResponse(dict(self._payload))


def _provider(
    *,
    fetcher: Any = None,
    instrument_keys: dict[str, str] | None = None,
    access_token: str = "test-token",
) -> UpstoxMarketDataProvider:
    mapper = UpstoxInstrumentMapper(
        instrument_keys or {"RELIANCE": RELIANCE_KEY}
    )
    return UpstoxMarketDataProvider(
        access_token=access_token,
        instrument_mapper=mapper,
        fetcher=fetcher,
        now=lambda: FIXED_NOW,
    )


# ---------------------------------------------------------------------------
# Happy path: response -> OHLCVBar conversion
# ---------------------------------------------------------------------------

def test_successful_candle_response_converts_to_ohlcv_bars() -> None:
    recording = _RecordingFetcher(
        _realistic_response(CANDLE, [
            "2026-09-04T09:15:00+05:30", 2980.0, 2990.0, 2975.0, 2985.1, 9000, 0,
        ])
    )
    provider = _provider(fetcher=recording)

    bars = provider.get_historical_ohlcv("RELIANCE", period="1mo", interval="1d")

    assert len(bars) == 2
    first, second = bars
    assert isinstance(first, OHLCVBar)
    assert first.timestamp.isoformat() == "2026-09-07T09:15:00+05:30"
    assert (first.open, first.high, first.low, first.close) == (3000.5, 3010.0, 2995.0, 3008.25)
    assert first.volume == 12500.0
    assert (second.open, second.high, second.low, second.close) == (2980.0, 2990.0, 2975.0, 2985.1)
    assert second.volume == 9000.0


def test_candle_open_interest_column_is_ignored() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    bars = _provider(fetcher=recording).get_historical_ohlcv("RELIANCE")
    assert bars[0].close == 3008.25  # open interest (index 6) does not leak into the bar


# ---------------------------------------------------------------------------
# Endpoint / unit / interval / date / instrument-key construction
# ---------------------------------------------------------------------------

def test_correct_endpoint_and_path_are_constructed() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    provider = _provider(fetcher=recording)

    provider.get_historical_ohlcv("RELIANCE", period="2y", interval="1d")

    url = recording.calls[0][0]
    assert url.startswith("https://api.upstox.com/v3/historical-candle/")
    # Instrument key is URL-encoded exactly as the Upstox docs show (NSE_EQ%7CINE...).
    assert "NSE_EQ%7CINE002A01018" in url


def test_correct_instrument_key_is_used() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    provider = _provider(fetcher=recording)

    provider.get_historical_ohlcv("RELIANCE")

    assert "NSE_EQ%7CINE002A01018" in recording.calls[0][0]


def test_correct_unit_interval_and_dates_are_sent() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    provider = _provider(fetcher=recording)

    provider.get_historical_ohlcv("RELIANCE", period="1mo", interval="5m")

    path = recording.calls[0][0]
    # .../historical-candle/<key>/<unit>/<interval>/<to_date>/<from_date>
    _, unit, interval, to_date, from_date = path.rsplit("/", 4)
    assert unit == "minutes"
    assert interval == "5"
    assert to_date == "2026-09-07"
    assert from_date == "2026-08-07"


def test_period_translation_for_years_and_days() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    provider = _provider(fetcher=recording)

    provider.get_historical_ohlcv("RELIANCE", period="5y", interval="1d")
    provider.get_historical_ohlcv("RELIANCE", period="5d", interval="1d")

    _, _, _, to_y, from_y = recording.calls[0][0].rsplit("/", 4)
    _, _, _, to_d, from_d = recording.calls[1][0].rsplit("/", 4)
    assert (to_y, from_y) == ("2026-09-07", "2021-09-07")
    assert (to_d, from_d) == ("2026-09-07", "2026-09-02")


def test_unsupported_interval_fails_clearly() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    with pytest.raises(RuntimeError, match="unsupported Upstox interval"):
        provider.get_historical_ohlcv("RELIANCE", interval="7m")


def test_unsupported_period_fails_clearly() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    with pytest.raises(RuntimeError, match="unsupported Upstox period"):
        provider.get_historical_ohlcv("RELIANCE", period="monthly")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def test_authentication_header_is_constructed_correctly() -> None:
    recording = _RecordingFetcher(_realistic_response(CANDLE))
    provider = _provider(fetcher=recording)

    provider.get_historical_ohlcv("RELIANCE")

    headers = recording.calls[0][1]
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Accept"] == "application/json"


def test_missing_access_token_fails_clearly() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)), access_token="")
    with pytest.raises(RuntimeError, match="access token is not configured"):
        provider.get_historical_ohlcv("RELIANCE")


# ---------------------------------------------------------------------------
# Empty / error / malformed responses
# ---------------------------------------------------------------------------

def test_empty_candle_response_returns_no_bars() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response()))
    bars = provider.get_historical_ohlcv("RELIANCE")
    assert bars == []


def test_missing_candles_key_is_rejected() -> None:
    provider = _provider(fetcher=_RecordingFetcher({"status": "success", "data": {}}))
    with pytest.raises(RuntimeError, match="missing 'data.candles'"):
        provider.get_historical_ohlcv("RELIANCE")


def test_candles_not_a_list_is_rejected() -> None:
    provider = _provider(
        fetcher=_RecordingFetcher({"status": "success", "data": {"candles": {}}})
    )
    with pytest.raises(RuntimeError, match="not a list"):
        provider.get_historical_ohlcv("RELIANCE")


def test_api_error_status_uses_provider_error_pattern() -> None:
    provider = _provider(
        fetcher=_RecordingFetcher({"status": "error", "message": "Rate limit exceeded"})
    )
    with pytest.raises(RuntimeError, match="Upstox API error: Rate limit exceeded"):
        provider.get_historical_ohlcv("RELIANCE")


def test_http_failure_is_converted_to_provider_error() -> None:
    import requests

    def failing(url: str, headers: dict[str, str], timeout: float) -> Any:
        raise requests.exceptions.HTTPError("401 Client Error: Unauthorized")

    provider = _provider(fetcher=failing)
    with pytest.raises(RuntimeError, match="Upstox historical candle request failed"):
        provider.get_historical_ohlcv("RELIANCE")


def test_non_json_response_is_rejected() -> None:
    provider = _provider(fetcher=lambda url, headers, timeout: "<html>not json</html>")
    with pytest.raises(RuntimeError, match="not a JSON object"):
        provider.get_historical_ohlcv("RELIANCE")


def test_malformed_candle_shape_is_rejected() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(["2026-09-07T00:00:00+05:30", 1.0])))
    with pytest.raises(RuntimeError, match="invalid shape"):
        provider.get_historical_ohlcv("RELIANCE")


def test_malformed_candle_timestamp_is_rejected() -> None:
    provider = _provider(
        fetcher=_RecordingFetcher(_realistic_response(["not-a-date", 1.0, 2.0, 0.5, 1.5, 100]))
    )
    with pytest.raises(RuntimeError, match="invalid timestamp"):
        provider.get_historical_ohlcv("RELIANCE")


def test_non_numeric_candle_value_is_rejected() -> None:
    provider = _provider(
        fetcher=_RecordingFetcher(_realistic_response(["2026-09-07T00:00:00+05:30", "abc", 2.0, 0.5, 1.5, 100]))
    )
    with pytest.raises(RuntimeError, match="open is not a number"):
        provider.get_historical_ohlcv("RELIANCE")


def test_non_finite_candle_value_is_rejected() -> None:
    provider = _provider(
        fetcher=_RecordingFetcher(
            _realistic_response(["2026-09-07T00:00:00+05:30", float("inf"), 2.0, 0.5, 1.5, 100])
        )
    )
    with pytest.raises(RuntimeError, match="open is not finite"):
        provider.get_historical_ohlcv("RELIANCE")


# ---------------------------------------------------------------------------
# Instrument mapping
# ---------------------------------------------------------------------------

def test_unknown_symbol_fails_clearly() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    with pytest.raises(RuntimeError, match="no Upstox instrument_key for symbol NOSUCH"):
        provider.get_historical_ohlcv("NOSUCH")


def test_mapper_accepts_explicit_instrument_keys() -> None:
    mapper = UpstoxInstrumentMapper({"infy": "NSE_EQ|INE009A01021"})
    assert mapper.to_instrument_key("infy") == "NSE_EQ|INE009A01021"
    assert mapper.to_instrument_key("INFY") == "NSE_EQ|INE009A01021"


# ---------------------------------------------------------------------------
# Contract conformance
# ---------------------------------------------------------------------------

def test_provider_conforms_to_market_data_provider() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    assert isinstance(provider, MarketDataProvider)
    assert provider.name == "upstox"
    assert provider.get_historical_ohlcv("RELIANCE")


def test_unsupported_operations_raise_not_implemented() -> None:
    provider = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    for operation in (
        lambda: provider.get_market_summary(),
        lambda: provider.get_stock("RELIANCE"),
        lambda: provider.get_stock_insight("RELIANCE"),
        lambda: provider.search_stocks("RELIANCE"),
        lambda: provider.get_opportunities(),
        lambda: provider.get_all_stocks(),
        lambda: provider.get_default_watchlist_symbols(),
    ):
        with pytest.raises(NotImplementedError):
            operation()


# ---------------------------------------------------------------------------
# MarketDataService boundary interop
# ---------------------------------------------------------------------------

def test_service_falls_back_to_seed_when_upstox_cannot_resolve_symbol() -> None:
    primary = _provider(fetcher=_RecordingFetcher(_realistic_response(CANDLE)))
    service = MarketDataService(primary, SeedProvider())

    result = service.get_historical_ohlcv("NOSUCH")

    assert result.metadata.provider == "seed"
    assert result.data is not None