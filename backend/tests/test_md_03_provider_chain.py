"""MD-03 focused tests: provider chain, instrument master, and Upstox snapshot.

All tests are deterministic and never call the real Upstox API.  HTTP is
simulated through the provider's injected ``fetcher`` / ``quote_fetcher`` seams.
"""
from __future__ import annotations

import json
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from services.chart_series import build_chart_series, build_chart_series_with_provider
from services.market_data.models import OHLCVBar
from services.market_data.snapshot_builder import assert_legacy_stock_fields
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper
from services.providers.upstox_instrument_source import (
    UpstoxInstrumentMasterError,
    build_master_payload,
    default_master_path,
    load_instrument_master,
    validate_instrument_master,
    validate_instrument_master_file,
)
from services.providers.upstox_provider import UpstoxMarketDataProvider
from services.providers.yahoo_finance_provider import YahooFinanceProvider

IST = timezone(timedelta(hours=5, minutes=30))
RELIANCE_KEY = "NSE_EQ|INE002A01018"
WIPRO_KEY = "NSE_EQ|INE075A01022"
SUNPHARMA_KEY = "NSE_EQ|INE044A01036"
VOLTAS_KEY = "NSE_EQ|INE226A01021"
PIDILITIND_KEY = "NSE_EQ|INE259A01022"
FIXED_NOW = datetime(2026, 9, 7, 6, 0, tzinfo=timezone.utc)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


class _RecordingFetcher:
    def __init__(self, payload: Any, *, error: Exception | None = None):
        self._payload = payload
        self._error = error
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Any:
        self.calls.append((url, headers, timeout))
        if self._error is not None:
            raise self._error
        return _FakeResponse(dict(self._payload))


class _StubProvider:
    """Minimal chain link with switchable behaviour per operation."""

    def __init__(self, name: str, *, value: Any = None, error: Exception | None = None):
        self.name = name
        self._value = value
        self._error = error
        self.calls: list[str] = []

    def _serve(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(operation)
        if self._error is not None:
            raise self._error
        return self._value

    def get_historical_ohlcv(self, symbol: str, *, period: str = "2y", interval: str = "1d"):
        return self._serve("get_historical_ohlcv", symbol, period=period, interval=interval)

    def get_stock(self, symbol: str) -> dict[str, Any] | None:
        return self._serve("get_stock", symbol)

    def get_stock_insight(self, symbol: str) -> dict[str, Any]:
        return self._serve("get_stock_insight", symbol)

    def get_market_summary(self) -> dict[str, Any]:
        return self._serve("get_market_summary")


class _StructuralSkipProvider(_StubProvider):
    def get_market_summary(self) -> dict[str, Any]:
        self.calls.append("get_market_summary")
        raise NotImplementedError("no catalogue")


def _candles_from_bars(bars: list[OHLCVBar], *, reverse: bool = False) -> list[list[Any]]:
    rows = [
        [
            bar.timestamp.isoformat(),
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
            0,
        ]
        for bar in bars
    ]
    if reverse:
        rows.reverse()
    return rows


def _daily_bars(n: int = 260) -> list[OHLCVBar]:
    """Deterministic, non-degenerate trending daily bars, oldest first."""
    bars: list[OHLCVBar] = []
    newest = datetime(2026, 9, 7, 9, 15, tzinfo=IST)
    for i in range(n):
        ts = newest - timedelta(days=(n - 1 - i))
        base = 1000.0 + i * 1.0
        open_ = base
        close = base + 2.0
        high = max(open_, close) + 1.0
        low = min(open_, close) - 1.0
        bars.append(
            OHLCVBar(
                timestamp=ts,
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=100000.0 + i,
            )
        )
    return bars


def _response(candles: list[list[Any]]) -> dict[str, Any]:
    return {"status": "success", "data": {"candles": candles}}


def _ltp_payload(instrument_key: str, *, price: str = "1234.5", volume: int = 777) -> dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "NSE_EQ:NHPC": {
                "last_price": price,
                "instrument_token": instrument_key,
                "volume": volume,
            },
        },
    }


def _upstox_provider(*, candle_payload: dict[str, Any], ltp_payload: dict[str, Any], mapper=None) -> "tuple[UpstoxMarketDataProvider, _RecordingFetcher, _RecordingFetcher]":
    candle_fetcher = _RecordingFetcher(candle_payload)
    quote_fetcher = _RecordingFetcher(ltp_payload)
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=mapper or UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY}),
        fetcher=candle_fetcher,
        quote_fetcher=quote_fetcher,
        now=lambda: FIXED_NOW,
        seed_provider=SeedProvider(),
    )
    return provider, candle_fetcher, quote_fetcher


# ---------------------------------------------------------------------------
# Instrument master loader / validation / deploy gate
# ---------------------------------------------------------------------------

_SAMPLE_FIXTURE = "tests/fixtures/upstox_instruments_sample.json"


def test_sample_fixture_validates_below_deployment_threshold() -> None:
    with open(_SAMPLE_FIXTURE, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    metadata = validate_instrument_master(payload, min_count=1)
    assert metadata["scope"] == "NSE_EQ"
    # The physically-separate sample is NOT a release artifact.
    with pytest.raises(UpstoxInstrumentMasterError, match="below the deployment safety threshold"):
        validate_instrument_master(payload)


def test_production_master_passes_deploy_gate() -> None:
    metadata = validate_instrument_master_file(default_master_path())
    assert metadata["scope"] == "NSE_EQ"
    assert metadata["count"] >= 1500


def test_fetch_normalizes_official_trading_symbol_field() -> None:
    script_path = Path(__file__).parents[2] / "scripts" / "fetch_upstox_instruments.py"
    spec = importlib.util.spec_from_file_location("fetch_upstox_instruments", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    records = module._records_from_raw([
        {
            "trading_symbol": "VOLTAS",
            "name": "Voltas Limited",
            "instrument_key": VOLTAS_KEY,
            "instrument_type": "EQ",
        },
        {
            "trading_symbol": "VOLTAS",
            "name": "Voltas Warrant",
            "instrument_key": "NSE_EQ|INE226A08ZZZ",
            "instrument_type": "W1",
        },
    ])

    assert records == [{
        "symbol": "VOLTAS",
        "name": "Voltas Limited",
        "instrument_key": VOLTAS_KEY,
    }]


def test_instrument_metadata_rejects_invalid_timestamp_and_placeholder_version() -> None:
    payload = build_master_payload(
        [{"symbol": "RELIANCE", "name": "Reliance", "instrument_key": RELIANCE_KEY}],
        version="release-1.0",
    )
    payload["metadata"]["generated_at"] = "not-a-timestamp"
    with pytest.raises(UpstoxInstrumentMasterError, match="ISO-8601"):
        validate_instrument_master(payload, min_count=1)

    payload["metadata"]["generated_at"] = "2026-09-07T00:00:00Z"
    payload["metadata"]["source_version"] = "PLACEHOLDER"
    with pytest.raises(UpstoxInstrumentMasterError, match="placeholder"):
        validate_instrument_master(payload, min_count=1)


def test_loader_rejects_duplicate_symbols() -> None:
    records = [
        {"symbol": "RELIANCE", "name": "Reliance", "instrument_key": "NSE_EQ|INE002A01018"},
        {"symbol": "reliance", "name": "Reliance again", "instrument_key": "NSE_EQ|INE1111111111"},
    ]
    payload = build_master_payload(records, version="dup-test")
    with pytest.raises(UpstoxInstrumentMasterError, match="duplicate symbol"):
        validate_instrument_master(payload, min_count=1)


def test_loader_rejects_duplicate_instrument_keys() -> None:
    records = [
        {"symbol": "RELIANCE", "name": "Reliance", "instrument_key": "NSE_EQ|INE002A01018"},
        {"symbol": "INFY", "name": "Infosys", "instrument_key": "NSE_EQ|INE002A01018"},
    ]
    payload = build_master_payload(records, version="dup-test")
    with pytest.raises(UpstoxInstrumentMasterError, match="duplicate instrument_key"):
        validate_instrument_master(payload, min_count=1)


def test_loader_rejects_non_nse_eq_keys_and_missing_required_fields() -> None:
    records = [
        {"symbol": "RELIANCE", "name": "Reliance", "instrument_key": "BSE_EQ|INE002A01018"},
    ]
    payload = build_master_payload(records, version="bad-key")
    with pytest.raises(UpstoxInstrumentMasterError, match="not an NSE_EQ key"):
        validate_instrument_master(payload, min_count=1)

    bad = {"metadata": payload["metadata"], "instruments": [{"symbol": "RELIANCE"}]}
    with pytest.raises(UpstoxInstrumentMasterError, match="missing required field"):
        validate_instrument_master(bad, min_count=1)


def test_loader_rejects_count_metadata_mismatch_and_bad_scope() -> None:
    records = [
        {"symbol": "RELIANCE", "name": "Reliance", "instrument_key": "NSE_EQ|INE002A01018"},
    ]
    payload = build_master_payload(records, version="count-test")
    payload["metadata"]["count"] = 99
    with pytest.raises(UpstoxInstrumentMasterError, match="count mismatch"):
        validate_instrument_master(payload, min_count=1)

    payload["metadata"]["count"] = 1
    payload["metadata"]["scope"] = "MCX"
    with pytest.raises(UpstoxInstrumentMasterError, match="scope must be NSE_EQ"):
        validate_instrument_master(payload, min_count=1)


def test_load_full_master_returns_symbol_mapping(tmp_path) -> None:
    records = [
        {"symbol": f"STOCK{i:05d}", "name": f"Stock {i}", "instrument_key": f"NSE_EQ|INE{i:09d}"}
        for i in range(1500)
    ]
    records.append({"symbol": "WIPRO", "name": "Wipro", "instrument_key": WIPRO_KEY})
    payload = build_master_payload(records, version="release-1.0")
    path = tmp_path / "master.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)

    mapping = load_instrument_master(path)
    assert mapping["WIPRO"] == WIPRO_KEY
    assert len(mapping) == 1501


# ---------------------------------------------------------------------------
# Mapper: master_mapping merged, env override wins
# ---------------------------------------------------------------------------

def test_mapper_merges_master_mapping(monkeypatch) -> None:
    monkeypatch.delenv("UPSTOX_INSTRUMENT_KEYS", raising=False)
    mapper = UpstoxInstrumentMapper(
        master_mapping={"WIPRO": WIPRO_KEY, "SUNPHARMA": SUNPHARMA_KEY}
    )
    assert mapper.to_instrument_key("wipro") == WIPRO_KEY
    assert mapper.to_instrument_key("SUNPHARMA") == SUNPHARMA_KEY


def test_mapper_env_override_wins_over_master(monkeypatch) -> None:
    monkeypatch.setenv("UPSTOX_INSTRUMENT_KEYS", f"RELIANCE={WIPRO_KEY}")
    mapper = UpstoxInstrumentMapper(master_mapping={"RELIANCE": RELIANCE_KEY})
    assert mapper.to_instrument_key("RELIANCE") == WIPRO_KEY


# ---------------------------------------------------------------------------
# Upstox snapshot semantics (ADR-003): price = LTP, indicators from OHLCV
# ---------------------------------------------------------------------------

def test_get_stock_price_is_the_live_ltp() -> None:
    bars = _daily_bars()
    candle_payload = _response(_candles_from_bars(bars, reverse=True))
    provider, candle_fetcher, quote_fetcher = _upstox_provider(
        candle_payload=candle_payload,
        ltp_payload=_ltp_payload(RELIANCE_KEY, price="1234.5", volume=888),
    )

    stock = provider.get_stock("RELIANCE")

    assert stock is not None
    assert stock["symbol"] == "RELIANCE"
    assert stock["price"] == 1234.5
    assert stock["priceSource"] == "ltp"
    previous_close = bars[-2].close
    expected_change = round((1234.5 - previous_close) / previous_close * 100, 2)
    assert stock["changePct"] == expected_change
    assert stock["volume"] == 888
    # Moving-average magnitude sanity: LTP sits near the trend, EMA20 close to it.
    assert 0 <= stock["rsi"] <= 100
    assert stock["ema20"] > 0
    assert stock["vwap"] > 0
    assert_legacy_stock_fields(stock)


def test_ltp_request_uses_documented_v2_endpoint_and_token_matching() -> None:
    bars = _daily_bars()
    provider, _, quote_fetcher = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload=_ltp_payload(RELIANCE_KEY, price="1234.5"),
    )

    provider.get_stock("RELIANCE")

    url = quote_fetcher.calls[0][0]
    assert url == (
        "https://api.upstox.com/v2/market-quote/ltp?"
        "instrument_key=NSE_EQ%7CINE002A01018"
    )


def test_get_stock_change_pct_falls_back_to_previous_close_wire_order_independent() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload=_ltp_payload(RELIANCE_KEY, price="1234.5"),
    )
    stock = provider.get_stock("RELIANCE")
    # Same expectation whether the candles arrive ascending or descending.
    previous_close = bars[-2].close
    assert stock["changePct"] == round((1234.5 - previous_close) / previous_close * 100, 2)


def test_one_historical_candle_cannot_calculate_change_pct() -> None:
    bars = _daily_bars(1)
    provider, _, _ = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload=_ltp_payload(RELIANCE_KEY),
    )

    with pytest.raises(RuntimeError, match="previous close"):
        provider.get_stock("RELIANCE")


def test_get_stock_uses_seeded_catalogue_metadata_and_provides_insight() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload=_ltp_payload(RELIANCE_KEY),
    )
    stock = provider.get_stock("RELIANCE")
    assert stock["name"] == "Reliance Industries"  # seeded, not invented
    assert stock["sector"] == "Energy"
    assert stock["trend"] in {"bullish", "bearish", "neutral"}

    insight = provider.get_stock_insight("RELIANCE")
    assert insight["support"] > 0
    assert insight["resistance"] > insight["support"]
    assert "EMA20" in insight["aiInsight"]
    assert insight["series"]


def test_unknown_symbol_still_fails_clearly_for_snapshot() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(candle_payload=_response(_candles_from_bars(bars)), ltp_payload=_ltp_payload("NSE_EQ|INE9999999999"))
    with pytest.raises(RuntimeError, match="no Upstox instrument_key for symbol NOSUCH"):
        provider.get_stock("NOSUCH")


def test_previous_close_cannot_be_published_as_ltp() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload={"status": "success", "data": {RELIANCE_KEY: {"prev_close": "1500.25"}}},
    )
    with pytest.raises(RuntimeError, match="no usable last_price field"):
        provider.get_stock("RELIANCE")


def test_ltp_quote_missing_price_raises_and_chain_falls_through() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload={"status": "success", "data": {RELIANCE_KEY: {"volume": 5}}},
    )
    second = _StubProvider(name="stub", value={"symbol": "RELIANCE", "price": 99.0})
    service = MarketDataService(provider, SeedProvider(), chain=[provider, second, SeedProvider()])

    result = service.get_stock("RELIANCE")

    assert result.metadata.provider == "stub"
    assert result.data["price"] == 99.0


# ---------------------------------------------------------------------------
# Chain semantics
# ---------------------------------------------------------------------------

def test_empty_ohlcv_falls_through_to_the_next_provider() -> None:
    empty = _StubProvider(name="empty", value=[])
    bars = _daily_bars(10)
    next_provider = _StubProvider(name="next", value=bars)
    service = MarketDataService(empty, SeedProvider(), chain=[empty, next_provider, SeedProvider()])

    result = service.get_historical_ohlcv("RELIANCE", period="1mo", interval="1d")

    assert result.metadata.provider == "next"
    assert len(result.data) == 10
    assert empty.calls.count("get_historical_ohlcv") == 1


def test_not_implemented_skip_is_structural_no_retry_no_health_flip() -> None:
    primary = _StructuralSkipProvider(name="upstox")
    fallback = _StubProvider(name="seed", value={"indices": []})
    service = MarketDataService(primary, fallback)

    healthy_before = service.provider_status()["healthy"]
    result = service.get_market_summary()

    assert result.metadata.provider == "seed"
    # A structural skip neither flips health nor retries.
    assert service.provider_status()["healthy"] == healthy_before
    assert primary.calls == ["get_market_summary"]


def test_first_link_failure_is_retried_before_moving_on() -> None:
    primary = _StubProvider(name="primary", error=RuntimeError("boom"))
    fallback = _StubProvider(name="seed", value={"symbol": "RELIANCE", "price": 88.0})
    service = MarketDataService(primary, fallback)

    result = service.get_stock("RELIANCE")

    assert result.metadata.provider == "seed"
    assert primary.calls.count("get_stock") == 2
    assert service.provider_status()["healthy"] is False


def test_provider_status_exposes_chain_and_active_provider() -> None:
    primary = _StubProvider(name="upstox", value={"symbol": "RELIANCE", "price": 10.0})
    fallback = _StubProvider(name="yahoo_finance", value={"symbol": "RELIANCE", "price": 9.0})
    seed = _StubProvider(name="seed", value={"symbol": "RELIANCE", "price": 8.0})
    service = MarketDataService(primary, fallback, chain=[primary, fallback, seed])

    status = service.provider_status()
    assert status["provider"] == "upstox"
    assert status["chain"] == ["upstox", "yahoo_finance", "seed"]
    assert status["activeProvider"] is None

    service.get_stock("RELIANCE")
    assert service.provider_status()["activeProvider"] == "upstox"


def test_yahoo_seed_fallback_reports_seed_provenance(monkeypatch) -> None:
    seed = SeedProvider()
    yahoo = YahooFinanceProvider(seed)
    monkeypatch.setattr(yahoo._normalized, "_load_bundle", lambda symbol: None)
    service = MarketDataService(yahoo, seed, chain=[yahoo, seed])

    result = service.get_stock("RELIANCE")

    assert result.metadata.provider == "seed"
    assert result.data["price"] == seed.get_stock("RELIANCE")["price"]
    assert service.provider_status()["healthy"] is False


def test_yahoo_catalogue_operations_report_seed_provenance() -> None:
    seed = SeedProvider()
    yahoo = YahooFinanceProvider(seed, search_fetcher=lambda *args, **kwargs: [])
    service = MarketDataService(yahoo, seed, chain=[yahoo, seed])

    results = [
        service.get_all_stocks(),
        service.search_stocks("RELIANCE"),
        service.get_opportunities(),
        service.get_default_watchlist_symbols(),
    ]

    assert all(result.metadata.provider == "seed" for result in results)


def test_genuine_yahoo_catalogue_result_keeps_yahoo_provenance() -> None:
    class YahooCatalogue(_StubProvider):
        name = "yahoo_finance"

        def get_all_stocks(self):
            return self._serve("get_all_stocks")

        def search_stocks(self, query: str, limit: int = 20):
            return self._serve("search_stocks")

        def get_opportunities(self):
            return self._serve("get_opportunities")

        def get_default_watchlist_symbols(self):
            return self._serve("get_default_watchlist_symbols")

    yahoo = YahooCatalogue(name="yahoo_finance", value=[{"symbol": "RELIANCE"}])
    seed = SeedProvider()
    service = MarketDataService(yahoo, seed, chain=[yahoo, seed])

    assert service.get_all_stocks().metadata.provider == "yahoo_finance"


def test_ltp_request_does_not_bypass_the_service_cache() -> None:
    bars = _daily_bars()
    provider, candle_fetcher, quote_fetcher = _upstox_provider(
        candle_payload=_response(_candles_from_bars(bars)),
        ltp_payload=_ltp_payload(RELIANCE_KEY),
    )
    service = MarketDataService(provider, SeedProvider(), chain=[provider, SeedProvider()])

    first = service.get_stock("RELIANCE")
    candles_after_first = len(candle_fetcher.calls)
    quotes_after_first = len(quote_fetcher.calls)
    assert first.metadata.provider == "upstox"
    assert candles_after_first >= 1
    assert quotes_after_first == 1

    second = service.get_stock("RELIANCE")
    assert second.metadata.cached is True
    assert len(candle_fetcher.calls) == candles_after_first
    assert len(quote_fetcher.calls) == quotes_after_first


def test_catalogue_operations_delegate_to_seed_through_the_chain() -> None:
    bars = _daily_bars()
    provider, _, _ = _upstox_provider(candle_payload=_response(_candles_from_bars(bars)), ltp_payload=_ltp_payload(RELIANCE_KEY))
    seed = SeedProvider()
    service = MarketDataService(provider, seed, chain=[provider, seed])

    result = service.get_default_watchlist_symbols()

    assert result.metadata.provider == "seed"
    assert result.data


# ---------------------------------------------------------------------------
# Chart intraday guard (D3): seed-only rejection
# ---------------------------------------------------------------------------

def test_chart_intraday_accepts_real_non_seed_provider_data() -> None:
    bars = _daily_bars(5)
    primary = _StubProvider(name="upstox", value=bars)
    yahoo = _StubProvider(name="yahoo_finance", value=bars)
    service = MarketDataService(primary, SeedProvider(), chain=[primary, yahoo, SeedProvider()])

    series, _, used_fallback, _ = build_chart_series(service, "RELIANCE", "1W")

    assert used_fallback is False
    assert series
    # 30m window requested by the 1W plan stays with the real provider.
    assert service.provider_status()["activeProvider"] == "upstox"


@pytest.mark.parametrize("provider_name", ["upstox", "yahoo_finance", "seed"])
def test_chart_routing_returns_actual_provider(provider_name: str) -> None:
    bars = _daily_bars(260)
    provider = _StubProvider(name=provider_name, value=bars)
    service = MarketDataService(provider, provider, chain=[provider])

    _, _, _, _, chart_provider = build_chart_series_with_provider(
        service, "RELIANCE", "1M"
    )

    assert chart_provider == provider_name


def test_chart_intraday_rejects_seed_sourced_data_even_as_primary() -> None:
    bars = _daily_bars(5)
    seed_like = _StubProvider(name="seed", value=bars)
    service = MarketDataService(seed_like, seed_like, chain=[seed_like])

    series_result = build_chart_series(service, "RELIANCE", "1D")

    # Seed intraday is rejected; the daily fallback plan serves and marks it.
    series, label, used_fallback, _ = series_result
    assert used_fallback is True
    assert label == "Recent Sessions"
    assert series


# ---------------------------------------------------------------------------
# Broad-universe acceptance: non-catalogue real NSE_EQ symbols resolve
# ---------------------------------------------------------------------------

def test_broad_universe_symbols_flow_through_snapshot_and_chart(tmp_path) -> None:
    records = [
        {"symbol": f"STOCK{i:05d}", "name": f"Stock {i}", "instrument_key": f"NSE_EQ|INE{i:09d}"}
        for i in range(1500)
    ]
    records += [
        {"symbol": "VOLTAS", "name": "Voltas", "instrument_key": VOLTAS_KEY},
        {"symbol": "PIDILITIND", "name": "Pidilite Industries", "instrument_key": PIDILITIND_KEY},
    ]
    payload = build_master_payload(records, version="b-univ")
    path = tmp_path / "master.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle)

    mapping = load_instrument_master(path)
    bars = _daily_bars()
    for symbol, key in (("VOLTAS", VOLTAS_KEY), ("PIDILITIND", PIDILITIND_KEY)):
        mapper = UpstoxInstrumentMapper(master_mapping=mapping)
        provider = UpstoxMarketDataProvider(
            access_token="test-token",
            instrument_mapper=mapper,
            fetcher=_RecordingFetcher(_response(_candles_from_bars(bars))),
            quote_fetcher=_RecordingFetcher(_ltp_payload(key)),
            now=lambda: FIXED_NOW,
            seed_provider=SeedProvider(),
        )
        service = MarketDataService(provider, SeedProvider(), chain=[provider, SeedProvider()])

        snapshot = service.get_stock(symbol).data
        assert snapshot is not None
        assert snapshot["priceSource"] == "ltp"
        assert snapshot["price"] == 1234.5  # the mocked live LTP
        assert snapshot["sector"] == "Equities"  # not in the catalogue -> neutral metadata
        assert_legacy_stock_fields(snapshot)

        series, _, used_fallback, _ = build_chart_series(service, symbol, "1M")
        assert used_fallback is False
        assert series


# ---------------------------------------------------------------------------
# MD-02 fixes under test at the provider level
# ---------------------------------------------------------------------------

def test_v3_error_object_message_is_used() -> None:
    payload = {"status": "error", "errors": [{"message": "Instrument data missing"}]}
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY}),
        fetcher=_RecordingFetcher(payload),
        now=lambda: FIXED_NOW,
    )
    with pytest.raises(RuntimeError, match="Upstox API error: Instrument data missing"):
        provider.get_historical_ohlcv("RELIANCE")


@pytest.mark.parametrize(
    ("interval", "period", "days_back"),
    [
        ("30m", "1mo", 90),
        ("1h", "1mo", 90),
        ("1d", "30d", 30),
    ],
)
def test_intraday_lookback_caps_apply_to_30m_and_hourly(interval: str, period: str, days_back: int) -> None:
    fetcher = _RecordingFetcher(_response([]))
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY}),
        fetcher=fetcher,
        now=lambda: FIXED_NOW,
    )
    provider.get_historical_ohlcv("RELIANCE", period=period, interval=interval)

    _, _, _, to_date, from_date = fetcher.calls[0][0].rsplit("/", 4)
    assert to_date == "2026-09-07"
    expected = (FIXED_NOW.astimezone(IST).date() - timedelta(days=days_back)).isoformat()
    assert from_date == expected


def test_to_date_is_in_ist_not_utc() -> None:
    fetcher = _RecordingFetcher(_response([]))
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY}),
        fetcher=fetcher,
        # 23:30 UTC on 2026-09-07 is already 09-08 in IST.
        now=lambda: datetime(2026, 9, 7, 23, 30, tzinfo=timezone.utc),
    )
    provider.get_historical_ohlcv("RELIANCE", period="1d", interval="1d")
    _, _, _, to_date, from_date = fetcher.calls[0][0].rsplit("/", 4)
    assert to_date == "2026-09-08"
    assert from_date == "2026-09-07"
