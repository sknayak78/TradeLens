"""Rate-limit (HTTP 429 / Retry-After) handling across the provider chain.

All tests are fully mocked: no live Upstox API calls, and no real sleeping.
Every test injects a recording ``sleeper`` and additionally guards
``time.sleep`` so an accidental real wait fails loudly instead of slowing the
suite.
"""
from __future__ import annotations

import time
from typing import Any

import pytest
import requests

from services.market_data.diagnostic_logging import classify_error
from services.market_data_provider import ProviderRateLimitedError
from services.market_data_service import (
    DEFAULT_MAX_RETRY_AFTER_SECONDS,
    MarketDataService,
)
from services.providers.upstox_provider import (
    UpstoxMarketDataProvider,
    _parse_retry_after,
    _rate_limited_error,
)
from services.providers.upstox_instrument_mapper import UpstoxInstrumentMapper

RELIANCE_KEY = "NSE_EQ|RELIANCE-EQ"


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any test that reaches the real ``time.sleep``."""

    def _boom(seconds: float) -> None:
        raise AssertionError(f"real time.sleep({seconds}) must never be called in tests")

    monkeypatch.setattr(time, "sleep", _boom)


class _RecordingSleeper:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _with_cause(error: BaseException, cause: BaseException) -> BaseException:
    """Return ``error`` with ``cause`` attached, mirroring ``raise ... from``."""
    error.__cause__ = cause
    return error


class _ThrottleProvider:
    """Primary that rate-limits ``throttle_times`` times, then serves a value."""

    name = "upstox"

    def __init__(self, *, throttle_times: int = 1, retry_after: Any = "missing") -> None:
        self._throttle_times = throttle_times
        self._retry_after = retry_after
        self.calls: list[str] = []

    def _rate_limit(self) -> ProviderRateLimitedError:
        if self._retry_after == "missing":
            return ProviderRateLimitedError("Upstox rate limited the request")
        return ProviderRateLimitedError(
            "Upstox rate limited the request", retry_after=self._retry_after
        )

    def _serve(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(operation)
        if self.calls.count(operation) <= self._throttle_times:
            raise self._rate_limit()
        return {
            "symbol": "RELIANCE",
            "price": 100.0,
            "candles": [{"close": 100.0}],
        }

    def get_historical_ohlcv(self, symbol: str, *, period: str = "2y", interval: str = "1d"):
        return self._serve("get_historical_ohlcv", symbol, period=period, interval=interval)

    def get_stock(self, symbol: str):
        return self._serve("get_stock", symbol)

    def get_stock_insight(self, symbol: str):
        return self._serve("get_stock_insight", symbol)


class _StubProvider:
    name = "seed"

    def __init__(self, name: str = "seed", *, value: Any = None, error: Exception | None = None):
        self.name = name
        self._value = value if value is not None else {
            "symbol": "RELIANCE",
            "price": 88.0,
            "candles": [{"close": 88.0}],
        }
        self._error = error
        self.calls: list[str] = []

    def _serve(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(operation)
        if self._error is not None:
            raise self._error
        return self._value

    def get_historical_ohlcv(self, symbol: str, *, period: str = "2y", interval: str = "1d"):
        return self._serve("get_historical_ohlcv", symbol, period=period, interval=interval)

    def get_stock(self, symbol: str):
        return self._serve("get_stock", symbol)

    def get_stock_insight(self, symbol: str):
        return self._serve("get_stock_insight", symbol)


def _service(primary: Any, fallback: Any, sleeper: _RecordingSleeper, **kwargs: Any) -> MarketDataService:
    return MarketDataService(primary, fallback, sleeper=sleeper, **kwargs)


# --- 1. Retry-After = 5 (at the cap): wait, then retry successfully ---------


def test_retry_after_at_cap_waits_then_retries_primary() -> None:
    primary = _ThrottleProvider(throttle_times=1, retry_after=5)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == [5.0]
    assert primary.calls.count("get_historical_ohlcv") == 2
    assert fallback.calls == []
    assert result.metadata.provider == "upstox"
    assert result.data["price"] == 100.0


# --- 2. Retry-After = 0: no meaningful wait, retry still happens --------------


def test_retry_after_zero_does_not_wait_but_retries() -> None:
    primary = _ThrottleProvider(throttle_times=1, retry_after=0)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == [0.0]
    assert primary.calls.count("get_historical_ohlcv") == 2
    assert result.metadata.provider == "upstox"


# --- 3. Retry-After = 4: below cap ------------------------------------------


def test_retry_after_below_cap_waits_exactly() -> None:
    primary = _ThrottleProvider(throttle_times=1, retry_after=4)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == [4.0]
    assert primary.calls.count("get_historical_ohlcv") == 2
    assert result.metadata.provider == "upstox"


# --- 4. Retry-After = 30: over cap, fall back without a second attempt --------


def test_retry_after_over_cap_skips_retry_and_falls_back() -> None:
    primary = _ThrottleProvider(retry_after=30)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_historical_ohlcv") == 1
    assert fallback.calls.count("get_historical_ohlcv") == 1
    assert result.metadata.provider == "seed"


# --- 5. Retry-After = 540: the headline regression ---------------------------


def test_retry_after_540_makes_exactly_one_primary_attempt() -> None:
    primary = _ThrottleProvider(retry_after=540)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_historical_ohlcv") == 1
    assert fallback.calls.count("get_historical_ohlcv") == 1
    assert result.metadata.provider == "seed"


# --- 6. Missing Retry-After ---------------------------------------------------


def test_missing_retry_after_skips_retry_and_falls_back() -> None:
    primary = _ThrottleProvider(retry_after="missing")
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_historical_ohlcv") == 1
    assert result.metadata.provider == "seed"


# --- 7. Malformed Retry-After -------------------------------------------------


def test_malformed_retry_after_is_treated_as_missing() -> None:
    # "soon" cannot be expressed as a number, so the provider yields None and the
    # service must treat that exactly like a missing header.
    assert _parse_retry_after("soon") is None
    parsed = _rate_limited_error(_Fake429(retry_after="soon"))
    assert parsed is not None
    assert parsed.retry_after is None

    primary = _ThrottleProvider(retry_after=None)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_historical_ohlcv") == 1
    assert result.metadata.provider == "seed"


# --- 8. Two attempts on a throttled-then-successful retry ---------------------


def test_throttle_then_success_uses_exactly_two_attempts() -> None:
    primary = _ThrottleProvider(throttle_times=1, retry_after=2)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    service = _service(primary, fallback, sleeper)
    result = service.get_historical_ohlcv("RELIANCE")

    assert primary.calls.count("get_historical_ohlcv") == 2
    assert fallback.calls == []
    assert result.metadata.provider == "upstox"
    assert service.provider_status()["rateLimitWaits"] == 1


# --- 9. Throttle persists past the retry: fallback attribution ----------------


def test_repeated_throttle_falls_back_with_correct_attribution() -> None:
    primary = _ThrottleProvider(throttle_times=99, retry_after=5)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert primary.calls.count("get_historical_ohlcv") == 2
    assert fallback.calls.count("get_historical_ohlcv") == 1
    assert result.metadata.provider == "seed"
    assert result.data["price"] == 88.0


# --- 10. HTTP 500 must not sleep and must keep immediate retry ---------------


def test_http_500_never_sleeps_and_still_retries_immediately() -> None:
    error = requests.HTTPError("500 Server Error")
    error.response = requests.Response()  # type: ignore[assignment]
    error.response.status_code = 500
    primary = _StubProvider("upstox", error=error)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_historical_ohlcv") == 2
    assert result.metadata.provider == "seed"


# --- 11. Existing first-link retry expectation is preserved -------------------


def test_non_rate_limit_error_still_retries_twice() -> None:
    primary = _StubProvider("upstox", error=RuntimeError("boom"))
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    service = _service(primary, fallback, sleeper)
    result = service.get_stock("RELIANCE")

    assert primary.calls.count("get_stock") == 2
    assert result.metadata.provider == "seed"
    assert service.provider_status()["healthy"] is False


# --- 12. Diagnostic attribution ----------------------------------------------


def test_diagnostic_attribution_is_preserved_for_429() -> None:
    error = ProviderRateLimitedError("Upstox rate limited the request", retry_after=540)
    # Chain a real requests.HTTPError exactly as the provider does, so the
    # existing status-based classification is exercised rather than bypassed.
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "540"
    chained = requests.HTTPError("429 Too Many Requests", response=response)

    classified = classify_error(_with_cause(error, chained))
    assert classified["rate_limited"] is True
    assert classified["http_status"] == 429

    # The classified payload still names the failing provider for the log.
    from services.market_data_service import _event, _skips_remaining_attempt

    payload = _event(
        "market_data.provider_failed",
        provider="upstox",
        operation="get_historical_ohlcv",
        failed_provider="upstox",
        fallback_provider="yahoo_finance",
        **classified,
        retry_after=error.retry_after,
    )
    assert '"rate_limited": true' in payload
    assert '"http_status": 429' in payload
    assert '"retry_after": 540' in payload
    assert '"failed_provider": "upstox"' in payload
    assert '"fallback_provider": "yahoo_finance"' in payload
    assert _skips_remaining_attempt(error, None, DEFAULT_MAX_RETRY_AFTER_SECONDS) is True


class _FlakyProvider:
    """Primary that succeeds while ``healthy_mode`` is set, then fails as told."""

    name = "upstox"

    def __init__(self, *, error: Exception) -> None:
        self._error = error
        self._healthy_mode = True
        self.calls: list[str] = []

    def _serve(self, operation: str, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(operation)
        if self._healthy_mode:
            return {"symbol": "RELIANCE", "price": 100.0, "candles": [{"close": 100.0}]}
        raise self._error

    def get_stock(self, symbol: str):
        return self._serve("get_stock", symbol)


def test_429_does_not_mark_provider_unhealthy(caplog: pytest.LogCaptureFixture) -> None:
    primary = _ThrottleProvider(retry_after=540)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()
    service = _service(primary, fallback, sleeper)

    with caplog.at_level("INFO"):
        service.get_historical_ohlcv("RELIANCE")

    status = service.provider_status()
    assert status["rateLimitRetrySkips"] == 1
    assert status["rateLimitWaits"] == 0
    assert status["lastRateLimitAt"] is not None
    assert "rateLimitWaits" in status
    # No success has occurred, so health keeps its pre-existing value.
    assert status["healthy"] is False


def test_429_after_success_does_not_flip_healthy_to_false() -> None:
    """The meaningful guard: a transient 429 must not undo a healthy provider."""
    primary = _FlakyProvider(
        error=ProviderRateLimitedError("Upstox rate limited the request", retry_after=540)
    )
    fallback = _StubProvider()
    service = _service(primary, fallback, _RecordingSleeper())

    service.get_stock("RELIANCE")
    assert service.provider_status()["healthy"] is True

    primary._healthy_mode = False
    service.get_stock("RELIANCE-2")

    # Rate limited and still healthy: a throttle is not a broken provider.
    assert service.provider_status()["healthy"] is True


def test_non_429_failure_still_marks_provider_unhealthy() -> None:
    """Contrast case proving the health guard is narrow, not a blanket change."""
    primary = _FlakyProvider(error=RuntimeError("boom"))
    service = _service(primary, _StubProvider(), _RecordingSleeper())

    service.get_stock("RELIANCE")
    assert service.provider_status()["healthy"] is True

    primary._healthy_mode = False
    service.get_stock("RELIANCE-2")

    assert service.provider_status()["healthy"] is False


# --- 13. Regression: 540 halves the wasted primary requests -------------------


def test_540_regression_halves_primary_request_volume() -> None:
    """32 throttled symbols previously cost 64 Upstox requests; now 32."""
    throttled_symbols = 32
    baseline_requests = throttled_symbols * 2

    primary = _ThrottleProvider(throttle_times=32, retry_after=540)
    fallback = _StubProvider()
    service = _service(primary, fallback, _RecordingSleeper())
    for index in range(throttled_symbols):
        # A distinct symbol per iteration keeps each read off the shared cache.
        service.get_historical_ohlcv(f"SYM{index}")

    assert primary.calls.count("get_historical_ohlcv") == throttled_symbols
    assert primary.calls.count("get_historical_ohlcv") * 2 == baseline_requests
    assert fallback.calls.count("get_historical_ohlcv") == throttled_symbols


# --- 14. Deadline safety ------------------------------------------------------


def test_no_long_wait_ever_occurs_across_advisory_values() -> None:
    for advisory in (30, 60, 540, 3600):
        primary = _ThrottleProvider(retry_after=advisory)
        sleeper = _RecordingSleeper()
        start = time.monotonic()
        _service(primary, _StubProvider(), sleeper).get_historical_ohlcv("RELIANCE")
        assert time.monotonic() - start < 1.0
        assert sleeper.calls == []


def test_longest_possible_wait_is_bounded_by_cap() -> None:
    primary = _ThrottleProvider(throttle_times=99, retry_after=DEFAULT_MAX_RETRY_AFTER_SECONDS)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    _service(primary, fallback, sleeper).get_historical_ohlcv("RELIANCE")

    assert sum(sleeper.calls) <= DEFAULT_MAX_RETRY_AFTER_SECONDS


def test_cap_is_configurable_without_redesign() -> None:
    primary = _ThrottleProvider(retry_after=30)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()

    result = _service(primary, fallback, sleeper, max_retry_after_seconds=60.0).get_historical_ohlcv(
        "RELIANCE"
    )

    assert sleeper.calls == [30.0]
    assert primary.calls.count("get_historical_ohlcv") == 2
    assert result.metadata.provider == "upstox"


# --- 15. Deep analysis never waits -------------------------------------------


def test_deep_analysis_operations_never_wait() -> None:
    for operation in ("get_stock", "get_stock_insight"):
        primary = _ThrottleProvider(retry_after=5)
        fallback = _StubProvider()
        sleeper = _RecordingSleeper()
        service = _service(primary, fallback, sleeper)

        getattr(service, operation)("RELIANCE")

        assert sleeper.calls == [], f"{operation} must not wait on Retry-After"
        assert primary.calls.count(operation) == 1
        assert fallback.calls.count(operation) == 1


def test_deep_analysis_pipeline_path_never_sleeps() -> None:
    """Mirrors ExistingTechnicalAnalyzer: get_stock then get_stock_insight.

    The stub payload is not indicator-shaped, so the analyzer raises before
    producing a decision.  The behavior under test is that neither deep-analysis
    read ever waits on a 5s Retry-After, even at the cap.
    """
    from services.deep_analysis_pipeline import ExistingTechnicalAnalyzer

    primary = _ThrottleProvider(retry_after=5)
    fallback = _StubProvider()
    sleeper = _RecordingSleeper()
    service = _service(primary, fallback, sleeper)
    analyzer = ExistingTechnicalAnalyzer(service)

    with pytest.raises(Exception):
        analyzer.analyze("RELIANCE")

    assert sleeper.calls == []
    assert primary.calls.count("get_stock") == 1
    assert primary.calls.count("get_stock_insight") == 1


# --- Provider-level parsing ---------------------------------------------------


class _Fake429:
    def __init__(self, *, retry_after: Any, status_code: int = 429) -> None:
        self.status_code = status_code
        self.headers = {} if retry_after is None else {"Retry-After": retry_after}


class _Fake500Response:
    status_code = 500
    headers: dict[str, str] = {}


def test_rate_limited_error_only_for_429() -> None:
    assert _rate_limited_error(_Fake500Response()) is None
    assert _rate_limited_error(None) is None
    assert _rate_limited_error(_Fake429(retry_after=None)) is not None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5", 5.0),
        (" 30 ", 30.0),
        ("0", 0.0),
        ("540", 540.0),
        ("soon", None),
        ("", None),
        (None, None),
        ("-5", None),
    ],
)
def test_parse_retry_after(raw: Any, expected: float | None) -> None:
    assert _parse_retry_after(raw) == expected


def test_upstox_provider_raises_rate_limited_with_parsed_retry_after() -> None:
    mapper = UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY})
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=mapper,
        fetcher=lambda url, headers, timeout: _Fake429(retry_after="540"),
    )

    with pytest.raises(ProviderRateLimitedError) as excinfo:
        provider.get_historical_ohlcv("RELIANCE")

    assert excinfo.value.retry_after == 540.0


def test_upstox_provider_raises_rate_limited_for_missing_header() -> None:
    mapper = UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY})
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=mapper,
        fetcher=lambda url, headers, timeout: _Fake429(retry_after=None),
    )

    with pytest.raises(ProviderRateLimitedError) as excinfo:
        provider.get_historical_ohlcv("RELIANCE")

    assert excinfo.value.retry_after is None


def test_upstox_provider_does_not_sleep_on_429() -> None:
    """The provider only reports; pacing belongs to the service."""
    mapper = UpstoxInstrumentMapper({"RELIANCE": RELIANCE_KEY})
    provider = UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_mapper=mapper,
        fetcher=lambda url, headers, timeout: _Fake429(retry_after="540"),
    )

    with pytest.raises(ProviderRateLimitedError):
        provider.get_historical_ohlcv("RELIANCE")
    # _no_real_sleep already raises if time.sleep is reached.
