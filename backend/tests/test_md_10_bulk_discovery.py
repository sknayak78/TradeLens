"""MD-10 deterministic tests: bulk Upstox quotes, Stage-1 gates, Stage-2 cap,
and bounded historical concurrency.

No live Upstox calls: every test uses fixtures or a fake fetcher.  Shapes mirror
the verified live probe (2,656 keys -> 11 batches of 250; colon-form response
keys joined through ``instrument_token``; TAALTECH-style missing record).
"""
from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

import pytest

from services.market_data.broad_market_prefilter import (
    DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES,
    DEFAULT_YEAR_HIGH_PROXIMITY_PCT,
    StageOneResult,
    apply_stage_one_gates,
    distance_to_year_high_pct,
    select_stage_two_candidates,
)
from services.market_data.models import MarketQuote, OHLCVBar
from services.market_data_provider import MarketDataProvider
from services.market_data_service import (
    MarketDataMetadata,
    MarketDataResult,
    MarketDataService,
)
from services.market_scanner import MarketScanner, ScannerConfig
from services.providers.upstox_provider import (
    _MAX_QUOTE_BATCH_SIZE,
    UpstoxMarketDataProvider,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _quote(**overrides: Any) -> MarketQuote:
    base: dict[str, Any] = {
        "instrument_key": "NSE_EQ|INE000A01001",
        "symbol": "AAA",
        "price": 100.0,
        "volume": 500_000,
        "prev_close": 99.0,
        "year_high": 105.0,
        "year_low": 70.0,
        "upper_circuit": 118.0,
        "lower_circuit": 85.0,
        "observed_at": datetime(2026, 9, 29, 1, 30, tzinfo=IST),
    }
    base.update(overrides)
    return MarketQuote(**base)


def _upstox_record(
    token: str = "NSE_EQ|INE000A01001",
    symbol: str = "AAA",
    **overrides: Any,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "instrument_token": token,
        "symbol": symbol,
        "last_price": 100.0,
        "volume": 500_000,
        "prev_close_price": 99.0,
        "year_high": 105.0,
        "year_low": 70.0,
        "upper_circuit_limit": 118.0,
        "lower_circuit_limit": 85.0,
        "timestamp": "2026-09-29T01:30:41.883+05:30",
    }
    record.update(overrides)
    return record


def _bulk_payload(records: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Build an Upstox Full Market Quotes response keyed in *colon* form.

    The live API keys ``data`` by ``EXCHANGE:SYMBOL`` (e.g. ``NSE_EQ:EIEL``),
    which does not match the master's ``instrument_key``.  Using colon keys here
    keeps every test honest about joining through ``instrument_token``.
    """
    return {
        "status": "success",
        "data": {
            f"{record['instrument_token'].split('|')[0]}:{record['symbol']}": record
            for record in records
        },
    }


class _RecordingQuoteFetcher:
    """Captures requested URLs and replays queued Full Market Quotes payloads."""

    def __init__(self, payloads: Sequence[dict[str, Any]]):
        self._payloads = list(payloads)
        self.urls: list[str] = []
        self.batch_sizes: list[int] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> Any:
        self.urls.append(url)
        # Count instrument_key occurrences so a 500-key request cannot hide.
        self.batch_sizes.append(url.count("instrument_key="))
        if not self._payloads:
            raise AssertionError("fetched more batches than queued")
        return _Response(self._payloads.pop(0))


class _Response:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def json(self) -> dict[str, Any]:
        return self._payload


# --------------------------------------------------------------------------
# A. Upstox bulk batching
# --------------------------------------------------------------------------

def test_bulk_batch_size_is_250_not_500() -> None:
    """500 is documented but rejected by the runtime proxy with HTTP 414."""
    assert _MAX_QUOTE_BATCH_SIZE == 250


def test_bulk_batches_2656_instruments_into_11_requests() -> None:
    keys = [f"NSE_EQ|INE{i:09d}" for i in range(2656)]
    fetcher = _RecordingQuoteFetcher(
        [
            # Unique colon-form keys per record, as the live API produces.
            _bulk_payload(
                [
                    _upstox_record(token=key, symbol=f"S{index:05d}")
                    for index, key in enumerate(batch, start=start)
                ]
            )
            for start, batch in ((i, keys[i : i + 250]) for i in range(0, len(keys), 250))
        ]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quotes = provider.get_bulk_market_quotes(keys)

    assert len(fetcher.urls) == 11
    assert max(fetcher.batch_sizes) == 250
    assert 500 not in fetcher.batch_sizes
    assert fetcher.batch_sizes[-1] == 156  # final partial batch
    assert len(quotes) == 2656


def test_bulk_query_parameters_are_url_encoded() -> None:
    fetcher = _RecordingQuoteFetcher([_bulk_payload([_upstox_record()])])
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    provider.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])

    assert "%7C" in fetcher.urls[0]  # the pipe is percent-encoded
    assert "|" not in fetcher.urls[0]


def test_bulk_uses_quote_fetcher_and_bearer_auth_without_leaking_token() -> None:
    seen_headers: list[dict[str, str]] = []

    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        seen_headers.append(headers)
        return _Response(_bulk_payload([_upstox_record()]))

    provider = UpstoxMarketDataProvider(access_token="s3cret", quote_fetcher=fetcher)
    provider.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])

    assert seen_headers[0]["Authorization"] == "Bearer s3cret"


def test_bulk_empty_key_list_makes_no_request() -> None:
    fetcher = _RecordingQuoteFetcher([])
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    assert provider.get_bulk_market_quotes([]) == []
    assert fetcher.urls == []


# --------------------------------------------------------------------------
# B. Response normalization
# --------------------------------------------------------------------------

def test_bulk_joins_records_by_instrument_token_not_colon_key() -> None:
    """A colon-form ``data`` key must not be used as the instrument identity."""
    token = "NSE_EQ|INE000A01001"
    payload = {
        "status": "success",
        "data": {
            "NSE_EQ:AAA": {
                **_upstox_record(token=token, symbol="AAA"),
                "instrument_token": token,
            }
        },
    }
    fetcher = _RecordingQuoteFetcher([payload])
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quotes = provider.get_bulk_market_quotes([token])

    assert len(quotes) == 1
    assert quotes[0].instrument_key == token
    assert quotes[0].symbol == "AAA"


def test_bulk_normalizes_all_stage_one_fields() -> None:
    fetcher = _RecordingQuoteFetcher(
        [_bulk_payload([_upstox_record(last_price=123.456, volume=987654)])]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quote = provider.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])[0]

    assert quote.price == 123.46
    assert quote.volume == 987654
    assert quote.prev_close == 99.0
    assert quote.year_high == 105.0
    assert quote.year_low == 70.0
    assert quote.upper_circuit == 118.0
    assert quote.lower_circuit == 85.0
    assert quote.observed_at == datetime(2026, 9, 29, 1, 30, 41, 883000, tzinfo=IST)


def test_bulk_tolerates_missing_record_such_as_taaltech() -> None:
    """One instrument is legitimately absent; it must not raise or be fabricated."""
    requested = ["NSE_EQ|INE000A01001", "NSE_EQ|INE524T01011"]
    fetcher = _RecordingQuoteFetcher([_bulk_payload([_upstox_record()])])
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quotes = provider.get_bulk_market_quotes(requested)

    assert [quote.instrument_key for quote in quotes] == ["NSE_EQ|INE000A01001"]


def test_bulk_skips_record_with_unusable_last_price() -> None:
    fetcher = _RecordingQuoteFetcher(
        [_bulk_payload([_upstox_record(), _upstox_record(token="NSE_EQ|INE2", symbol="BBB", last_price=None)])]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    assert len(provider.get_bulk_market_quotes(["NSE_EQ|INE1", "NSE_EQ|INE2"])) == 1


def test_bulk_optional_fields_become_none_not_zero() -> None:
    fetcher = _RecordingQuoteFetcher(
        [_bulk_payload([_upstox_record(year_high=None, upper_circuit_limit="oops")])]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quote = provider.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])[0]

    assert quote.year_high is None
    assert quote.upper_circuit is None


def test_bulk_api_error_status_raises() -> None:
    fetcher = _RecordingQuoteFetcher(
        [{"status": "error", "errors": [{"message": "invalid instrument_key"}]}]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    with pytest.raises(RuntimeError, match="invalid instrument_key"):
        provider.get_bulk_market_quotes(["NSE_EQ|BAD"])


def test_bulk_transport_failure_raises_runtime_error_with_batch_context() -> None:
    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        raise OSError("connection reset")

    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    with pytest.raises(RuntimeError, match="2 instruments"):
        provider.get_bulk_market_quotes(["NSE_EQ|A", "NSE_EQ|B"])


# --------------------------------------------------------------------------
# C. Stage-1 gates
# --------------------------------------------------------------------------

def test_distance_to_year_high_pct_formula() -> None:
    assert distance_to_year_high_pct(95.0, 100.0) == pytest.approx(5.0)
    assert distance_to_year_high_pct(100.0, 100.0) == pytest.approx(0.0)
    # Price above the 52-week high yields a negative distance and still qualifies.
    assert distance_to_year_high_pct(105.0, 100.0) == pytest.approx(-5.0)


@pytest.mark.parametrize(
    "price, year_high, expected",
    [
        (100.0, 100.0, True),   # distance 0.0%
        (95.1, 100.0, True),    # distance 4.9%
        (95.0, 100.0, True),    # distance 5.0% exactly -> inclusive
        (94.9, 100.0, False),   # distance 5.1%
        (60.0, 100.0, False),   # distance 40.0%
    ],
)
def test_stage_one_proximity_threshold_is_inclusive(
    price: float, year_high: float, expected: bool
) -> None:
    result = apply_stage_one_gates(
        [_quote(price=price, year_high=year_high)],
        year_high_proximity_pct=5.0,
    )
    assert (result.eligible_count == 1) is expected


def test_stage_one_excludes_non_positive_price() -> None:
    result = apply_stage_one_gates([_quote(price=0.0), _quote(price=-5.0)])
    assert result.eligible_count == 0
    assert result.excluded["missing_or_invalid_price"] == 2


def test_stage_one_excludes_non_positive_volume() -> None:
    result = apply_stage_one_gates([_quote(volume=0), _quote(volume=None)])
    assert result.eligible_count == 0
    assert result.excluded["missing_or_invalid_volume"] == 2


def test_stage_one_excludes_at_upper_circuit() -> None:
    quote = _quote(price=117.9, upper_circuit=118.0, year_high=200.0)
    result = apply_stage_one_gates([quote])
    assert result.eligible_count == 0
    assert result.excluded["at_upper_circuit"] == 1


def test_stage_one_excludes_at_lower_circuit() -> None:
    quote = _quote(price=84.9, lower_circuit=85.0, year_high=200.0)
    result = apply_stage_one_gates([quote])
    assert result.eligible_count == 0
    assert result.excluded["at_lower_circuit"] == 1


def test_stage_one_includes_symbol_just_below_upper_circuit() -> None:
    quote = _quote(price=110.0, upper_circuit=118.0, year_high=110.5)
    assert apply_stage_one_gates([quote]).eligible_count == 1


@pytest.mark.parametrize("year_high", [None, 0.0, -1.0])
def test_stage_one_excludes_missing_or_invalid_year_high(year_high: Any) -> None:
    result = apply_stage_one_gates([_quote(year_high=year_high)])
    assert result.eligible_count == 0
    assert result.excluded["missing_or_invalid_year_high"] == 1


def test_stage_one_missing_circuit_limit_is_not_a_circuit() -> None:
    quote = _quote(upper_circuit=None, lower_circuit=None, year_high=100.5)
    assert apply_stage_one_gates([quote]).eligible_count == 1


def test_stage_one_default_thresholds_match_measurement() -> None:
    assert DEFAULT_YEAR_HIGH_PROXIMITY_PCT == 10.0
    assert DEFAULT_MAXIMUM_STAGE_TWO_CANDIDATES == 300


# --------------------------------------------------------------------------
# D. Deterministic cap
# --------------------------------------------------------------------------

def _many_quotes(count: int) -> list[MarketQuote]:
    """`count` eligible quotes with a deterministic, deliberately varied spread."""
    return [
        MarketQuote(
            instrument_key=f"NSE_EQ|INE{index:09d}",
            symbol=f"SYM{index:04d}",
            price=100.0,
            # Distance below the 52-week high is index*0.02%, so 500 quotes
            # span 0.00%-9.98% and all sit inside the 10% Stage-1 gate.
            year_high=100.0 / (1 - (index * 0.0002)),
            # volume intentionally anti-correlated with proximity so the
            # tie-break path is exercised separately.
            volume=1_000 - index,
        )
        for index in range(count)
    ]


def test_stage_two_caps_at_300_when_more_eligible() -> None:
    stage_one = apply_stage_one_gates(_many_quotes(450), year_high_proximity_pct=10.0)
    selection = select_stage_two_candidates(stage_one, cap=300)

    assert stage_one.eligible_count == 450
    assert selection.selected_count == 300
    assert selection.was_capped is True


def test_stage_two_selects_closest_to_52w_high_first() -> None:
    stage_one = apply_stage_one_gates(_many_quotes(20), year_high_proximity_pct=10.0)
    selection = select_stage_two_candidates(stage_one, cap=5)

    assert [q.instrument_key for q in selection.selected] == [
        "NSE_EQ|INE000000000",
        "NSE_EQ|INE000000001",
        "NSE_EQ|INE000000002",
        "NSE_EQ|INE000000003",
        "NSE_EQ|INE000000004",
    ]


def test_stage_two_ties_break_on_volume_then_instrument_key() -> None:
    # Identical distance (price 99, year_high 100) for all four.
    quotes = [
        MarketQuote("NSE_EQ|INE_B", "B", 99.0, volume=10, year_high=100.0),
        MarketQuote("NSE_EQ|INE_A", "A", 99.0, volume=10, year_high=100.0),
        MarketQuote("NSE_EQ|INE_C", "C", 99.0, volume=50, year_high=100.0),
        MarketQuote("NSE_EQ|INE_D", "D", 99.0, volume=1, year_high=100.0),
    ]
    selection = select_stage_two_candidates(
        apply_stage_one_gates(quotes), cap=10
    )
    assert [q.instrument_key for q in selection.selected] == [
        "NSE_EQ|INE_C",  # highest volume first
        "NSE_EQ|INE_A",  # then lowest instrument key
        "NSE_EQ|INE_B",
        "NSE_EQ|INE_D",
    ]


def test_stage_two_is_deterministic_across_repeated_execution() -> None:
    quotes = _many_quotes(500)
    first = select_stage_two_candidates(apply_stage_one_gates(quotes), cap=300)
    second = select_stage_two_candidates(apply_stage_one_gates(list(reversed(quotes))), cap=300)
    assert [q.instrument_key for q in first.selected] == [
        q.instrument_key for q in second.selected
    ]


def test_stage_two_processes_all_when_fewer_than_cap() -> None:
    stage_one = apply_stage_one_gates(_many_quotes(42), year_high_proximity_pct=10.0)
    selection = select_stage_two_candidates(stage_one, cap=300)
    assert selection.selected_count == 42
    assert selection.was_capped is False


def test_stage_two_rejects_negative_cap() -> None:
    with pytest.raises(ValueError):
        select_stage_two_candidates(StageOneResult(0, 0, 0, (), {}), cap=-1)


# --------------------------------------------------------------------------
# E. Historical concurrency
# --------------------------------------------------------------------------

def _bars(count: int = 80, *, volume: float = 250_000.0) -> list[OHLCVBar]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        OHLCVBar(
            timestamp=start + timedelta(days=index),
            open=100.0 + index,
            high=102.0 + index,
            low=99.0 + index,
            close=101.0 + index,
            volume=volume,
        )
        for index in range(count)
    ]


class _ConcurrencyService:
    """Tracks peak simultaneous historical fetches and records attempts."""

    name = "concurrency-test"

    def __init__(self, symbols: Sequence[str], *, failing: Sequence[str] = ()):
        self._rows = {symbol: _bars() for symbol in symbols}
        self._failing = set(failing)
        self.attempts: list[str] = []
        self._lock = threading.Lock()
        self._active = 0
        self.peak_concurrency = 0
        self.bulk_keys: list[str] = []

    supports_bulk_market_quotes = False

    def get_bulk_market_quotes(self, instrument_keys: Sequence[str]):
        raise NotImplementedError

    def get_historical_ohlcv(self, symbol: str, *, period: str, interval: str):
        with self._lock:
            self.attempts.append(symbol)
            self._active += 1
            self.peak_concurrency = max(self.peak_concurrency, self._active)
        try:
            time.sleep(0.02)
            if symbol in self._failing:
                raise RuntimeError(f"history unavailable for {symbol}")
            return MarketDataResult(
                self._rows[symbol],
                MarketDataMetadata("upstox", False, datetime.now(timezone.utc), "CLOSED"),
            )
        finally:
            with self._lock:
                self._active -= 1


def _eligible_quotes(count: int) -> list[MarketQuote]:
    return [
        MarketQuote(
            instrument_key=f"NSE_EQ|INE{index:09d}",
            symbol=f"S{index:03d}",
            price=99.0,
            volume=1_000_000,
            year_high=100.0,
        )
        for index in range(count)
    ]


class _BulkService(_ConcurrencyService):
    supports_bulk_market_quotes = True

    def __init__(self, symbols: Sequence[str], quotes: Sequence[MarketQuote], **kwargs: Any):
        super().__init__(symbols, **kwargs)
        self._quotes = tuple(quotes)

    def get_bulk_market_quotes(self, instrument_keys: Sequence[str]):
        self.bulk_keys = list(instrument_keys)
        return MarketDataResult(
            self._quotes,
            MarketDataMetadata("upstox", False, datetime.now(timezone.utc), "OPEN"),
        )


def test_historical_concurrency_never_exceeds_16() -> None:
    symbols = [f"S{index:03d}" for index in range(120)]
    service = _ConcurrencyService(symbols)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={symbol: f"NSE_EQ|INE{i:09d}" for i, symbol in enumerate(symbols)},
        config=ScannerConfig(historical_fetch_concurrency=16),
    )

    scanner.scan()

    assert service.peak_concurrency <= 16
    assert service.peak_concurrency > 1  # actually concurrent
    assert sorted(service.attempts) == sorted(symbols)


def test_concurrency_one_falls_back_to_sequential_single_worker() -> None:
    symbols = ["S000", "S001", "S002"]
    service = _ConcurrencyService(symbols)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={symbol: f"NSE_EQ|INE{i:09d}" for i, symbol in enumerate(symbols)},
        config=ScannerConfig(historical_fetch_concurrency=1),
    )

    scanner.scan()

    assert service.peak_concurrency == 1
    assert len(service.attempts) == 3


def test_one_symbol_failure_does_not_abort_the_scan() -> None:
    symbols = [f"S{index:03d}" for index in range(20)]
    service = _ConcurrencyService(symbols, failing=["S007"])
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={symbol: f"NSE_EQ|INE{i:09d}" for i, symbol in enumerate(symbols)},
    )

    result = scanner.scan()

    assert len(result.results) == 20
    failed = [r for r in result.results if r.symbol == "S007"][0]
    assert failed.passed is False
    assert failed.rejection_reasons == ("data_unavailable",)
    assert failed.error is not None
    # Other symbols were still attempted and screened.
    assert sum(1 for r in result.results if r.rejection_reasons != ("data_unavailable",)) == 19


# --------------------------------------------------------------------------
# F. Scanner integration
# --------------------------------------------------------------------------

def test_stage_one_reduces_the_historical_universe() -> None:
    symbols = [f"S{index:03d}" for index in range(50)]
    quotes = _eligible_quotes(20)  # only 20 of 50 are in the snapshot as eligible
    service = _BulkService(symbols, quotes)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            f"S{index:03d}": f"NSE_EQ|INE{index:09d}" for index in range(50)
        },
    )

    result = scanner.scan()

    assert result.metrics.universe_count == 50
    assert result.metrics.bulk_snapshot_requested == 50
    assert result.metrics.bulk_snapshot_returned == 20
    assert result.metrics.stage_one_eligible_count == 20
    assert result.metrics.stage_two_selected_count == 20
    assert result.metrics.stage_two_cap == 300
    assert result.metrics.bulk_prefilter_applied is True
    assert len(service.attempts) == 20  # historical fetch dropped 50 -> 20


def test_stage_two_cap_bounds_historical_requests_at_300() -> None:
    symbols = [f"S{index:04d}" for index in range(500)]
    quotes = _eligible_quotes(500)
    service = _BulkService(symbols, quotes)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            symbol: f"NSE_EQ|INE{index:09d}" for index, symbol in enumerate(symbols)
        },
    )

    result = scanner.scan()

    assert result.metrics.stage_one_eligible_count == 500
    assert result.metrics.stage_two_selected_count == 300
    assert result.metrics.stage_two_cap == 300
    assert len(service.attempts) == 300
    assert service.peak_concurrency <= 16


def test_existing_screen_still_decides_technical_candidates() -> None:
    """Prefiltered inputs still go through the unchanged `_screen()` rules."""
    symbols = ["LOWVOL", "GOODVOL"]
    service = _BulkService(symbols, _eligible_quotes(2))
    service._rows["LOWVOL"] = _bars(volume=1.0)  # fails minimum_average_volume
    service._rows["GOODVOL"] = _bars(volume=250_000.0)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            "LOWVOL": "NSE_EQ|INE000000001",
            "GOODVOL": "NSE_EQ|INE000000002",
        },
    )
    # Quotes must match the universe keys for the join to work.
    service._quotes = (
        MarketQuote("NSE_EQ|INE000000001", "S000", 99.0, 1_000_000, year_high=100.0),
        MarketQuote("NSE_EQ|INE000000002", "S001", 99.0, 1_000_000, year_high=100.0),
    )

    result = scanner.scan()

    by_symbol = {r.symbol: r for r in result.results}
    assert by_symbol["LOWVOL"].signals["liquidity"] is False
    assert by_symbol["LOWVOL"].passed is False
    assert result.metrics.data_available_count == 2
    assert result.metrics.liquidity_pass_count == 1


def test_results_preserve_input_order_deterministically() -> None:
    symbols = [f"S{index:03d}" for index in range(30)]
    service = _BulkService(symbols, _eligible_quotes(30))
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            symbol: f"NSE_EQ|INE{index:09d}" for i, symbol in enumerate(symbols)
            for index in [i]
        },
    )

    first = [r.symbol for r in scanner.scan().results]
    second = [r.symbol for r in scanner.scan().results]
    assert first == second


# --------------------------------------------------------------------------
# G. Non-Upstox compatibility
# --------------------------------------------------------------------------

def test_provider_without_bulk_capability_scans_full_universe() -> None:
    symbols = [f"S{index:03d}" for index in range(25)]
    service = _ConcurrencyService(symbols)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            symbol: f"NSE_EQ|INE{index:09d}" for index, symbol in enumerate(symbols)
        },
    )

    result = scanner.scan()

    assert result.metrics.bulk_prefilter_applied is False
    assert result.metrics.bulk_prefilter_fallback_reason == "provider_unsupported"
    assert result.metrics.stage_two_selected_count == 0
    assert result.metrics.eligible_count == 25  # full universe, as before
    assert len(service.attempts) == 25


def test_bulk_snapshot_error_falls_back_without_fabricating_results() -> None:
    symbols = [f"S{index:03d}" for index in range(12)]

    class _BoomService(_ConcurrencyService):
        supports_bulk_market_quotes = True

        def get_bulk_market_quotes(self, instrument_keys: Sequence[str]):
            raise RuntimeError("upstream 500")

    service = _BoomService(symbols)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={
            symbol: f"NSE_EQ|INE{index:09d}" for index, symbol in enumerate(symbols)
        },
    )

    result = scanner.scan()

    assert result.metrics.bulk_prefilter_applied is False
    assert result.metrics.bulk_prefilter_fallback_reason == "bulk_snapshot_error:RuntimeError"
    assert len(service.attempts) == 12


def test_empty_bulk_snapshot_falls_back_to_full_universe() -> None:
    symbols = ["S000", "S001"]

    class _EmptyService(_ConcurrencyService):
        supports_bulk_market_quotes = True

        def get_bulk_market_quotes(self, instrument_keys: Sequence[str]):
            return MarketDataResult(
                (), MarketDataMetadata("upstox", False, datetime.now(timezone.utc), "OPEN")
            )

    service = _EmptyService(symbols)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={"S000": "NSE_EQ|INE1", "S001": "NSE_EQ|INE2"},
    )

    result = scanner.scan()

    assert result.metrics.bulk_prefilter_applied is False
    assert result.metrics.bulk_prefilter_fallback_reason == "empty_bulk_snapshot"
    assert len(service.attempts) == 2


def test_stage_one_yielding_nothing_falls_back_rather_than_returning_empty_scan() -> None:
    symbols = ["S000", "S001"]
    quotes = [
        MarketQuote("NSE_EQ|INE1", "S000", 10.0, volume=100, year_high=1000.0),
        MarketQuote("NSE_EQ|INE2", "S001", 10.0, volume=100, year_high=1000.0),
    ]
    service = _BulkService(symbols, quotes)
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={"S000": "NSE_EQ|INE1", "S001": "NSE_EQ|INE2"},
    )

    result = scanner.scan()

    assert result.metrics.bulk_prefilter_applied is False
    assert result.metrics.bulk_prefilter_fallback_reason == "no_stage_one_candidates"
    assert result.metrics.stage_one_eligible_count == 0
    assert len(service.attempts) == 2


def test_bulk_prefilter_can_be_disabled_by_config() -> None:
    symbols = ["S000", "S001"]
    service = _BulkService(symbols, _eligible_quotes(2))
    service._quotes = (
        MarketQuote("NSE_EQ|INE1", "S000", 99.0, 1_000_000, year_high=100.0),
        MarketQuote("NSE_EQ|INE2", "S001", 99.0, 1_000_000, year_high=100.0),
    )
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={"S000": "NSE_EQ|INE1", "S001": "NSE_EQ|INE2"},
        config=ScannerConfig(bulk_prefilter_enabled=False),
    )

    result = scanner.scan()

    assert result.metrics.bulk_prefilter_fallback_reason == "bulk_prefilter_disabled"
    assert service.bulk_keys == []  # bulk was never called
    assert len(service.attempts) == 2


def test_universe_instrument_missing_from_snapshot_is_not_screened() -> None:
    """A snapshot key with no universe entry cannot be joined and is dropped."""
    service = _BulkService(
        ["S000", "S001"],
        [
            MarketQuote("NSE_EQ|INE1", "S000", 99.0, 1_000_000, year_high=100.0),
            MarketQuote("NSE_EQ|UNMAPPED", "SXXX", 99.0, 1_000_000, year_high=100.0),
        ],
    )
    scanner = MarketScanner(
        service,  # type: ignore[arg-type]
        instrument_mapping={"S000": "NSE_EQ|INE1", "S001": "NSE_EQ|INE2"},
    )

    result = scanner.scan()

    assert service.attempts == ["S000"]
    assert result.metrics.stage_one_eligible_count == 2
    assert result.metrics.stage_two_selected_count == 1


class _AlwaysUnsupportedProvider(MarketDataProvider):
    """Minimal provider that does not override the optional bulk capability."""

    name = "unsupported"

    def get_historical_ohlcv(self, symbol: str, *, period: str = "2y", interval: str = "1d"):
        return ()

    def get_market_summary(self):
        return {}

    def get_stock(self, symbol: str):
        return None

    def get_stock_insight(self, symbol: str):
        return {}

    def search_stocks(self, query: str, limit: int = 20):
        return []

    def get_opportunities(self):
        return []

    def get_all_stocks(self):
        return []

    def get_default_watchlist_symbols(self):
        return []


def test_market_data_service_reports_bulk_support_only_when_overridden() -> None:
    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        return _Response(_bulk_payload([_upstox_record()]))

    upstox = UpstoxMarketDataProvider(access_token="t", quote_fetcher=fetcher)
    assert MarketDataService(upstox, _AlwaysUnsupportedProvider()).supports_bulk_market_quotes

    assert not MarketDataService(
        _AlwaysUnsupportedProvider(), _AlwaysUnsupportedProvider()
    ).supports_bulk_market_quotes


def test_market_data_service_raises_not_implemented_without_bulk_support() -> None:
    service = MarketDataService(_AlwaysUnsupportedProvider(), _AlwaysUnsupportedProvider())
    with pytest.raises(NotImplementedError):
        service.get_bulk_market_quotes(["NSE_EQ|A"])


def test_market_data_service_rejects_empty_bulk_key_list() -> None:
    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        return _Response(_bulk_payload([_upstox_record()]))

    service = MarketDataService(
        UpstoxMarketDataProvider(access_token="t", quote_fetcher=fetcher),
        _AlwaysUnsupportedProvider(),
    )
    with pytest.raises(ValueError):
        service.get_bulk_market_quotes([])


def test_market_data_service_bulk_snapshot_cache_key_is_deterministic() -> None:
    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        return _Response(_bulk_payload([_upstox_record()]))

    upstox = UpstoxMarketDataProvider(access_token="t", quote_fetcher=fetcher)
    service = MarketDataService(upstox, _AlwaysUnsupportedProvider())
    key_one = _capture_bulk_cache_key(service, ["A", "B"])
    key_two = _capture_bulk_cache_key(service, ["A", "B"])
    key_other = _capture_bulk_cache_key(service, ["A", "C"])
    assert key_one == key_two
    assert key_one != key_other


def _capture_bulk_cache_key(service: MarketDataService, keys: Sequence[str]) -> str:
    seen: list[str] = []
    original = service._cache.get

    def spy(key: str):  # type: ignore[no-untyped-def]
        seen.append(key)
        return original(key)

    service._cache.get = spy  # type: ignore[method-assign]
    try:
        service.get_bulk_market_quotes(keys)
    finally:
        service._cache.get = original  # type: ignore[method-assign]
    return seen[0]


def test_market_data_service_bulk_snapshot_is_served_from_cache_on_second_call() -> None:
    calls: list[str] = []

    def fetcher(url: str, headers: dict[str, str], timeout: float) -> Any:
        calls.append(url)
        return _Response(_bulk_payload([_upstox_record()]))

    service = MarketDataService(
        UpstoxMarketDataProvider(access_token="t", quote_fetcher=fetcher),
        _AlwaysUnsupportedProvider(),
    )
    first = service.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])
    second = service.get_bulk_market_quotes(["NSE_EQ|INE000A01001"])

    assert len(calls) == 1  # second read served from the existing TTL cache
    assert first.metadata.cached is False
    assert second.metadata.cached is True
    assert len(second.data) == 1


def test_bulk_snapshot_keys_are_requested_in_master_order() -> None:
    tokens = [f"NSE_EQ|INE{index:09d}" for index in range(3)]
    fetcher = _RecordingQuoteFetcher(
        [
            _bulk_payload(
                [
                    _upstox_record(token=token, symbol=f"S{index}")
                    for index, token in enumerate(tokens)
                ]
            )
        ]
    )
    provider = UpstoxMarketDataProvider(access_token="token", quote_fetcher=fetcher)

    quotes = provider.get_bulk_market_quotes(tokens)

    assert [q.instrument_key for q in quotes] == tokens
    assert tokens[0].replace("|", "%7C") in fetcher.urls[0]
