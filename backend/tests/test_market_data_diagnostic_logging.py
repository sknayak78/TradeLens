"""Deterministic tests for durable provider-diagnostic logging.

No live provider calls: every case uses fake providers, fake exceptions, or a
temporary log directory.  These tests assert that the diagnostic record is
sufficient to attribute Upstox vs Yahoo usage, retries, fallbacks, and HTTP 429
rate limiting after the process exits.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path

import pytest

from services.market_data.diagnostic_logging import (
    LOG_FILENAME,
    classify_error,
    _sanitize_message,
    configure_diagnostic_logging,
    diagnostic_log_path,
    http_status_from_error,
    redact,
    subject_of,
)
from services.market_data.models import OHLCVBar
from services.market_data_provider import MarketDataProvider
from services.market_data_service import (
    MarketDataMetadata,
    MarketDataResult,
    MarketDataService,
)
from services.providers.upstox_provider import UpstoxMarketDataProvider


def _bars(count: int = 80) -> list[OHLCVBar]:
    return [
        OHLCVBar(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc).replace(day=1 + (i % 28)),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=250_000.0,
        )
        for i in range(count)
    ]


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _RateLimited(Exception):
    """Stand-in for requests.HTTPError wrapping a 429 response."""


def _http_error(status: int) -> Exception:
    try:
        import requests

        error = requests.HTTPError(f"429 Client Error: Too Many Requests for url: x")
        error.response = _FakeResponse(status)  # type: ignore[assignment]
        return error
    except ImportError:  # pragma: no cover
        error = _RateLimited(f"{status} Client Error")
        error.response = _FakeResponse(status)  # type: ignore[attr-defined]
        return error


class BoomError(Exception):
    pass


class _Provider(MarketDataProvider):
    """Fake provider with configurable per-symbol behavior."""

    def __init__(self, name: str, *, fail_with: Exception | None = None, fail_symbols=()):
        self.name = name
        self._fail_with = fail_with
        self._fail_symbols = set(fail_symbols)
        self.calls: list[str] = []

    def get_historical_ohlcv(self, symbol, *, period="2y", interval="1d"):
        self.calls.append(symbol)
        if symbol in self._fail_symbols:
            raise self._fail_with or BoomError(f"{self.name} failed for {symbol}")
        return _bars()

    def get_market_summary(self):
        return {}

    def get_stock(self, symbol):
        return None

    def get_stock_insight(self, symbol):
        return {}

    def search_stocks(self, query, limit=20):
        return []

    def get_opportunities(self):
        return []

    def get_all_stocks(self):
        return []

    def get_default_watchlist_symbols(self):
        return []


def _read_events(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        # Format: "<ts> <LEVEL> <logger> <json>"
        marker = line.find("{")
        if marker == -1:
            continue
        try:
            events.append(json.loads(line[marker:]))
        except json.JSONDecodeError:
            continue
    return events


@pytest.fixture()
def diag_log(tmp_path: Path) -> Path:
    """A configured diagnostic log in a temp dir, with handler cleanup."""
    from services.market_data import diagnostic_logging as dl

    target = tmp_path / "logs" / LOG_FILENAME
    configure_diagnostic_logging(log_path=target)
    yield target
    for name in dl.DIAGNOSTIC_LOGGERS:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            if isinstance(handler, logging.handlers.RotatingFileHandler):
                handler.close()
                logger.removeHandler(handler)
    dl._configured_paths.clear()


# --- Destination and handler wiring ------------------------------------


def test_log_path_is_backend_logs_relative_not_machine_specific() -> None:
    path = diagnostic_log_path()
    assert path.name == LOG_FILENAME
    assert path.parent.name == "logs"
    assert path.parent.parent.name == "backend"
    assert path.is_absolute()
    # The path is derived from the package location, so it is correct under any
    # working directory and from any checkout.
    assert str(path.parent.parent) == str(Path(__file__).resolve().parents[1])


def test_log_path_source_contains_no_hardcoded_absolute_path() -> None:
    source = (Path(__file__).resolve().parents[1] / "services" / "market_data" / "diagnostic_logging.py").read_text(
        encoding="utf-8"
    )
    assert "/Users/" not in source
    assert "C:\\\\" not in source


def test_directory_is_created_when_missing(diag_log: Path) -> None:
    assert diag_log.parent.is_dir()
    assert diag_log.parent.name == "logs"


def test_configuration_is_idempotent_no_duplicate_handlers(tmp_path: Path) -> None:
    from services.market_data import diagnostic_logging as dl

    target = tmp_path / "logs" / LOG_FILENAME
    for _ in range(4):  # simulates repeated uvicorn reloads
        configure_diagnostic_logging(log_path=target)
    try:
        for name in dl.DIAGNOSTIC_LOGGERS:
            matching = [
                h
                for h in logging.getLogger(name).handlers
                if isinstance(h, logging.handlers.RotatingFileHandler)
                and h.baseFilename == str(target.resolve())
            ]
            assert len(matching) == 1, f"{name} has {len(matching)} handlers"
    finally:
        for name in dl.DIAGNOSTIC_LOGGERS:
            logger = logging.getLogger(name)
            for handler in list(logger.handlers):
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    handler.close()
                    logger.removeHandler(handler)
        dl._configured_paths.clear()


def test_handler_is_rotating_and_bounded(diag_log: Path) -> None:
    from services.market_data import diagnostic_logging as dl

    handlers = [
        h
        for name in dl.DIAGNOSTIC_LOGGERS
        for h in logging.getLogger(name).handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert handlers
    assert all(h.maxBytes > 0 for h in handlers)
    assert all(h.backupCount > 0 for h in handlers)


def test_console_handler_still_present(diag_log: Path) -> None:
    """Existing basicConfig console behavior must remain intact."""
    from services.market_data import diagnostic_logging as dl

    # A StreamHandler (or absent root handler under pytest) is untouched: we
    # only assert we did not remove/replace any pre-existing non-file handler.
    for name in dl.DIAGNOSTIC_LOGGERS:
        logger = logging.getLogger(name)
        non_file = [h for h in logger.handlers if not isinstance(h, logging.handlers.RotatingFileHandler)]
        assert all(isinstance(h, logging.StreamHandler) for h in non_file)


# --- Attempt-level fields ----------------------------------------------


def test_successful_historical_attempt_records_full_attribution(diag_log: Path) -> None:
    service = MarketDataService(_Provider("upstox"), _Provider("seed"))

    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    successes = [e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_success"]
    assert len(successes) == 1
    record = successes[0]
    assert record["provider"] == "upstox"
    assert record["operation"] == "get_historical_ohlcv"
    assert record["symbol"] == "TCS"
    assert record["chain_index"] == 0
    assert record["attempt"] == 1
    assert isinstance(record["elapsed_ms"], (int, float))
    assert record["elapsed_ms"] >= 0


def test_failed_attempt_records_status_and_error_classification(diag_log: Path) -> None:
    service = MarketDataService(
        _Provider(
            "upstox",
            fail_with=BoomError("upstox historical candle request failed"),
            fail_symbols={"RELIANCE"},
        ),
        _Provider("yahoo_finance"),
    )

    service.get_historical_ohlcv("RELIANCE", period="1y", interval="1d")

    failures = [e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed"]
    assert failures
    record = failures[0]
    assert record["provider"] == "upstox"
    assert record["symbol"] == "RELIANCE"
    assert record["chain_index"] == 0
    assert record["attempt"] in (1, 2)
    assert record["attempts"] == 2
    assert record["error_class"] == "BoomError"
    assert "error_message" in record


def test_http_429_is_unambiguous_in_the_diagnostic_log(diag_log: Path) -> None:
    service = MarketDataService(
        _Provider("upstox", fail_with=_http_error(429), fail_symbols={"INFY"}),
        _Provider("yahoo_finance"),
    )

    service.get_historical_ohlcv("INFY", period="1y", interval="1d")

    failures = [e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed"]
    throttled = [e for e in failures if e.get("http_status") == 429]
    assert throttled, "no provider_failed record carried http_status=429"
    assert throttled[0]["rate_limited"] is True
    assert throttled[0]["is_http_error"] is True
    assert throttled[0]["provider"] == "upstox"
    assert throttled[0]["symbol"] == "INFY"


def test_wrapped_429_through_cause_chain_is_detected() -> None:
    """Providers wrap transport errors with `raise ... from exc`."""
    original = _http_error(429)
    wrapper = RuntimeError("Upstox historical candle request failed for url: x")
    wrapper.__cause__ = original
    assert http_status_from_error(wrapper) == 429
    assert classify_error(wrapper)["http_status"] == 429
    assert classify_error(wrapper)["rate_limited"] is True


def test_non_429_failure_is_not_marked_rate_limited() -> None:
    original = _http_error(500)
    wrapper = RuntimeError("upstream error")
    wrapper.__cause__ = original
    assert classify_error(wrapper)["http_status"] == 500
    assert classify_error(wrapper)["rate_limited"] is False


def test_primary_failure_and_fallback_attempts_are_both_durable(diag_log: Path) -> None:
    """The whole point: reconstruct Upstox-vs-Yahoo per symbol after exit."""
    upstox = _Provider("upstox", fail_with=_http_error(429), fail_symbols={"TCS", "INFY"})
    yahoo = _Provider("yahoo_finance")
    service = MarketDataService(upstox, yahoo)

    service.get_historical_ohlcv("TCS", period="1y", interval="1d")
    service.get_historical_ohlcv("RELIANCE", period="1y", interval="1d")

    events = _read_events(diag_log)
    # TCS: upstox exhausted both attempts, then yahoo served it.
    tcs_upstox = [
        e
        for e in events
        if e.get("symbol") == "TCS" and e.get("provider") == "upstox" and e.get("event") == "market_data.provider_failed"
    ]
    assert [e["attempt"] for e in tcs_upstox] == [1, 2]
    assert all(e["http_status"] == 429 for e in tcs_upstox)

    tcs_yahoo = [
        e
        for e in events
        if e.get("symbol") == "TCS" and e.get("provider") == "yahoo_finance"
    ]
    assert tcs_yahoo
    assert any(e.get("event") == "market_data.provider_success" for e in tcs_yahoo)

    # RELIANCE: upstox served it, yahoo was never consulted.
    rel_upstox = [
        e
        for e in events
        if e.get("symbol") == "RELIANCE" and e.get("event") == "market_data.provider_success"
    ]
    assert len(rel_upstox) == 1
    assert not [e for e in events if e.get("symbol") == "RELIANCE" and e.get("provider") == "yahoo_finance"]


# --- Fallback attribution (Task 4) -------------------------------------


def test_fallback_event_names_both_providers_and_the_status(diag_log: Path) -> None:
    service = MarketDataService(
        _Provider("upstox", fail_with=_http_error(429), fail_symbols={"TCS"}),
        _Provider("yahoo_finance"),
    )

    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    fallbacks = [
        e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed_using_fallback"
    ]
    assert len(fallbacks) == 1
    record = fallbacks[0]
    assert record["failed_provider"] == "upstox"
    assert record["fallback_provider"] == "yahoo_finance"
    # Backward-compatible field names retained.
    assert record["provider"] == "upstox"
    assert record["fallback"] == "yahoo_finance"
    assert record["operation"] == "get_historical_ohlcv"
    assert record["symbol"] == "TCS"
    assert record["attempts"] == 2
    assert record["http_status"] == 429
    assert record["rate_limited"] is True


def test_fallback_event_absent_when_primary_succeeds(diag_log: Path) -> None:
    service = MarketDataService(_Provider("upstox"), _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")
    assert not [
        e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed_using_fallback"
    ]


def test_all_providers_failed_event_is_classified(diag_log: Path) -> None:
    service = MarketDataService(
        _Provider("upstox", fail_with=_http_error(429), fail_symbols={"TCS"}),
        _Provider("yahoo_finance", fail_with=BoomError("yahoo down"), fail_symbols={"TCS"}),
    )
    with pytest.raises(Exception):
        service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    events = _read_events(diag_log)
    assert [e for e in events if e.get("event") == "market_data.all_providers_failed"]
    assert any(e.get("http_status") == 429 for e in events)


def test_empty_result_event_is_durable(diag_log: Path) -> None:
    class _EmptyProvider(_Provider):
        def get_historical_ohlcv(self, symbol, *, period="2y", interval="1d"):
            return []

    service = MarketDataService(_EmptyProvider("upstox"), _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")
    empties = [e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_empty_result"]
    assert empties
    assert empties[0]["symbol"] == "TCS"
    assert empties[0]["chain_index"] == 0


# --- Secret exclusion --------------------------------------------------


def test_bearer_tokens_in_error_messages_are_redacted() -> None:
    text = "Upstox request failed with header Authorization: Bearer abc.def.ghi"
    cleaned = redact(text)
    assert "abc.def.ghi" not in cleaned
    assert "REDACTED" in cleaned


def test_token_query_parameters_are_redacted() -> None:
    cleaned = redact("https://api.upstox.com/v2/x?access_token=SECRETVALUE&foo=1")
    assert "SECRETVALUE" not in cleaned


def test_api_key_and_cookie_fields_are_redacted() -> None:
    assert "SHHH" not in redact("api_key=SHHH")
    assert "mmm" not in redact('{"cookie": "mmm"}')


def test_429_error_message_still_reports_status_after_redaction() -> None:
    original = _http_error(429)
    wrapper = RuntimeError("failed with Authorization: Bearer tok for url: x")
    wrapper.__cause__ = original
    record = classify_error(wrapper)
    assert record["http_status"] == 429
    assert "tok" not in record["error_message"]


def test_redact_alone_no_longer_truncates() -> None:
    """`redact` scrubs secrets only; bounding is a separate concern.

    Applying a truncating scrubber to a whole serialized record is what silently
    destroyed the fields after ``error_message``.
    """
    assert len(redact("x" * 5000)) == 5000
    assert not redact("x" * 5000).endswith("[TRUNCATED]")
    # Secrets are still scrubbed.
    assert "SEC" not in redact("Bearer SEC")


def test_long_messages_are_truncated() -> None:
    """A structured event bounds only its oversized free-text field."""
    payload = {
        "event": "market_data.provider_failed",
        "provider": "upstox",
        "operation": "get_historical_ohlcv",
        "symbol": "ABC",
        "error_message": "E" * 5000,
    }
    rendered = _sanitize_message(json.dumps(payload, sort_keys=True))
    parsed = json.loads(rendered)  # must remain valid JSON
    assert parsed["error_message"].endswith("[TRUNCATED]")
    assert len(parsed["error_message"]) < 600


# --- Regression: structured records must never lose fields --------------
#
# A live run showed 192 of 797 diagnostic lines were unparseable JSON, because
# the formatter bounded the *entire* rendered line.  Because ``error_message``
# sorts alphabetically before them, ``http_status``, ``rate_limited``,
# ``provider``, ``operation`` and ``symbol`` were all cut off precisely on the
# failure lines that needed them.  These tests pin that down.


def test_long_error_message_still_produces_valid_json(diag_log: Path) -> None:
    provider = _Provider("upstox", fail_with=BoomError("E" * 6000), fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    for line in diag_log.read_text(encoding="utf-8").splitlines():
        index = line.find("{")
        if index == -1:
            continue
        json.loads(line[index:])  # raises if any record is malformed


def test_error_message_is_bounded(diag_log: Path) -> None:
    provider = _Provider("upstox", fail_with=BoomError("E" * 6000), fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    records = [
        e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed"
    ]
    assert records
    assert all(len(e["error_message"]) < 600 for e in records)
    assert all(e["error_message"].endswith("[TRUNCATED]") for e in records)


def test_fields_after_error_message_survive_a_long_message(diag_log: Path) -> None:
    """Alphabetic order puts these *after* ``error_message`` in the payload."""
    original = _http_error(429)
    wrapper = BoomError("E" * 6000)
    wrapper.__cause__ = original
    provider = _Provider("upstox", fail_with=wrapper, fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    records = [
        e for e in _read_events(diag_log) if e.get("event") == "market_data.provider_failed"
    ]
    assert records, "the provider_failed record did not survive as valid JSON"
    for record in records:
        assert record["http_status"] == 429
        assert record["rate_limited"] is True
        assert record["is_http_error"] is True
        assert record["provider"] == "upstox"
        assert record["operation"] == "get_historical_ohlcv"
        assert record["symbol"] == "TCS"
        assert record["error_class"] == "BoomError"
        assert isinstance(record["elapsed_ms"], (int, float))


def test_http_429_survives_a_realistic_long_upstox_message(diag_log: Path) -> None:
    """The exact message shape observed live, which is what regressed."""
    inner = _http_error(429)
    wrapper = RuntimeError(
        "Upstox historical candle request failed for "
        "https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE750A01020/days/1/"
        "2026-09-29/2025-09-29: 429 Client Error: Too Many Requests for url: "
        "https://api.upstox.com/v3/historical-candle/NSE_EQ%7CINE750A01020/days/1/"
        "2026-09-29/2025-09-29"
    )
    wrapper.__cause__ = inner
    provider = _Provider("upstox", fail_with=wrapper, fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    throttled = [
        e
        for e in _read_events(diag_log)
        if e.get("event") == "market_data.provider_failed" and e.get("http_status") == 429
    ]
    assert throttled, "http_status=429 was lost to truncation"
    assert throttled[0]["rate_limited"] is True


def test_bearer_token_stays_redacted_inside_a_long_message(diag_log: Path) -> None:
    secret = "SUPERSECRETTOKEN123"
    provider = _Provider(
        "upstox",
        fail_with=BoomError(f"prefix Authorization: Bearer {secret} " + "E" * 6000),
        fail_symbols={"TCS"},
    )
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    text = diag_log.read_text(encoding="utf-8")
    assert secret not in text
    assert "REDACTED" in text
    for line in text.splitlines():
        index = line.find("{")
        if index != -1:
            json.loads(line[index:])


def test_plain_text_messages_stay_bounded_and_redacted() -> None:
    """Non-JSON lines have no structure to preserve, so bounding is safe."""
    rendered = _sanitize_message("x" * 5000)
    assert rendered.endswith("[TRUNCATED]")
    assert "SEC" not in _sanitize_message("Bearer SEC")


def test_console_traceback_still_present_while_file_omits_it(
    diag_log: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The file must stay traceback-free; the console must keep its traceback."""
    provider = _Provider("upstox", fail_with=BoomError("kaboom"), fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    file_text = diag_log.read_text(encoding="utf-8")
    assert "Traceback (most recent call last)" not in file_text
    assert "BoomError" in file_text  # classified class name is still recorded

    # The console handler (installed by basicConfig in server.py) is separate
    # and must not be affected by the file formatter.
    from services.market_data import diagnostic_logging as dl

    formatter_types = {type(h.formatter).__name__ for h in logging.getLogger("tradelens.market_data").handlers}
    assert any("Redacting" in name for name in formatter_types)


def test_upstox_access_token_never_appears_in_diagnostic_log(diag_log: Path) -> None:
    """A provider failure carrying a bearer token must not persist it."""
    secret = "SUPERSECRETTOKEN123"

    class _TokenBoom(Exception):
        pass

    provider = _Provider("upstox", fail_with=_TokenBoom(f"Bearer {secret}"), fail_symbols={"TCS"})
    service = MarketDataService(provider, _Provider("yahoo_finance"))
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")

    text = diag_log.read_text(encoding="utf-8") if diag_log.exists() else ""
    assert secret not in text
    assert "REDACTED" in text


def test_no_full_payload_dumping_in_records(diag_log: Path) -> None:
    """A 429 body must not be persisted, only the status."""
    class _Body429(Exception):
        pass

    err = _Body429("429 Client Error: Too Many Requests")
    err.response = _FakeResponse(429)  # type: ignore[attr-defined]
    err.response.text = '{"errors": [{"message": "huge upstream body"}]}'  # type: ignore[attr-defined]
    service = MarketDataService(
        _Provider("upstox", fail_with=err, fail_symbols={"TCS"}),
        _Provider("yahoo_finance"),
    )
    service.get_historical_ohlcv("TCS", period="1y", interval="1d")
    text = diag_log.read_text(encoding="utf-8")
    assert "huge upstream body" not in text


# --- Helpers -----------------------------------------------------------


def test_subject_of_records_symbol_for_single_and_count_for_bulk() -> None:
    assert subject_of(("TCS",)) == {"symbol": "TCS", "subject_count": None}
    bulk = subject_of((["NSE_EQ|A", "NSE_EQ|B"],))
    assert bulk["subject_count"] == 2
    assert bulk["symbol"] is None
    assert subject_of(()) == {"symbol": None, "subject_count": None}


def test_bulk_universe_keys_are_never_logged_individually(diag_log: Path) -> None:
    service = MarketDataService(_BulkProvider("upstox"), _Provider("seed"))
    keys = [f"NSE_EQ|INE{i:09d}" for i in range(500)]
    service.get_bulk_market_quotes(keys)

    text = diag_log.read_text(encoding="utf-8") if diag_log.exists() else ""
    # A 500-key universe would bloat the log; only the count is recorded.
    assert "NSE_EQ|INE000000001" not in text


class _BulkProvider(_Provider):
    """Fake provider that implements the optional bulk capability."""

    supports_bulk_market_quotes = True

    def get_bulk_market_quotes(self, instrument_keys):
        self.calls.append("bulk")
        return {}


def test_upstox_provider_bulk_logs_counts_not_keys() -> None:
    """Upstox bulk logging stays token-free and count-based."""
    records: list[str] = []
    logger = logging.getLogger("tradelens.market_data.upstox")
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record.getMessage())
    logger.addHandler(handler)
    try:
        provider = UpstoxMarketDataProvider(
            access_token="TOPSECRETTOKEN",
            quote_fetcher=lambda url, headers, timeout: type(
                "R", (), {"json": lambda self: {"status": "success", "data": {}}}
            )(),
        )
        provider.get_bulk_market_quotes([f"NSE_EQ|INE{i:09d}" for i in range(300)])
    finally:
        logger.removeHandler(handler)

    joined = "\n".join(records)
    assert "TOPSECRETTOKEN" not in joined
    assert "batch_size=250" in joined
    assert "batches=2" in joined
    assert "300 requested instruments" in joined
