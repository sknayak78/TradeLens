"""Single-flight protection around the /api/opportunities compute.

Concurrent cache misses must share one broad-market compute instead of
launching duplicate (up to 60s) scans, and all waiters must reuse the same
result object the winner built.
"""
from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

import routers.market as market_router


def _fallback():
    from datetime import datetime, timezone

    selection = SimpleNamespace(
        rows=(),
        action_counts={},
        screening=SimpleNamespace(universe_size=40, eligible_count=40),
        analysed_count=0,
    )
    metadata = {
        "provider": "seed",
        "cached": False,
        "asOf": datetime.now(timezone.utc),
        "marketStatus": "CLOSED",
    }
    return selection, metadata


def _install_slow_selector(monkeypatch, calls: dict[str, int]):
    def slow_select(service):
        calls["n"] += 1
        time.sleep(0.3)
        return _fallback()

    monkeypatch.setattr(market_router, "select_opportunities", slow_select)


def test_concurrent_misses_share_one_compute(monkeypatch) -> None:
    calls = {"n": 0}
    _install_slow_selector(monkeypatch, calls)
    responses: list = []
    errors: list[Exception] = []

    def _call() -> None:
        try:
            responses.append(market_router.opportunities())
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=_call) for _ in range(3)]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall_ms = (time.monotonic() - started) * 1000

    assert not errors
    assert calls["n"] == 1, "concurrent misses must share one compute"
    assert wall_ms < 1000, f"serialized wait too long: {wall_ms:.0f}ms"
    assert len({id(response) for response in responses}) == 1


def test_ttl_reuse_after_compute(monkeypatch) -> None:
    calls = {"n": 0}
    _install_slow_selector(monkeypatch, calls)

    first = market_router.opportunities()
    second = market_router.opportunities()

    assert calls["n"] == 1
    assert first is second


def test_clearing_cache_forces_one_recompute(monkeypatch) -> None:
    calls = {"n": 0}
    _install_slow_selector(monkeypatch, calls)

    market_router.opportunities()
    market_router.clear_opportunities_cache()
    market_router.opportunities()

    assert calls["n"] == 2


def test_failed_compute_does_not_block_later_requests(monkeypatch) -> None:
    calls = {"n": 0}

    def _flaky_select(_service):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("provider exploded")
        return _fallback()

    monkeypatch.setattr(market_router, "select_opportunities", _flaky_select)

    with pytest.raises(RuntimeError, match="provider exploded"):
        market_router.opportunities()

    # The flight must be released on failure, or every later request would
    # inherit the dead compute forever.
    assert market_router._opportunities_flight is None
    assert market_router._opportunities_cache["response"] is None

    recovered = market_router.opportunities()

    assert calls["n"] == 2
    assert recovered.rankings == []


def test_concurrent_waiters_share_the_failure(monkeypatch) -> None:
    calls = {"n": 0}

    def _failing_select(_service):
        calls["n"] += 1
        time.sleep(0.3)
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(market_router, "select_opportunities", _failing_select)
    errors: list[str] = []

    def _call() -> None:
        try:
            market_router.opportunities()
        except Exception as exc:  # noqa: BLE001 - recorded and asserted
            errors.append(str(exc))

    threads = [threading.Thread(target=_call) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert calls["n"] == 1, "concurrent failures must share one compute"
    assert errors == ["provider exploded"] * 3
    assert market_router._opportunities_flight is None


def test_lock_is_not_held_while_the_scan_runs(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def _inspecting_select(_service):
        observed["flight"] = market_router._opportunities_flight
        joined = threading.Thread(
            target=lambda: observed.setdefault(
                "join", market_router._begin_opportunities_flight()
            )
        )
        joined.start()
        joined.join(timeout=2.0)
        observed["joined"] = not joined.is_alive()
        return _fallback()

    monkeypatch.setattr(market_router, "select_opportunities", _inspecting_select)

    market_router.opportunities()

    assert observed["flight"] is not None, "owner must publish the flight"
    assert observed["joined"] is True, "the global lock must be free during the scan"
    flight, is_owner = observed["join"]
    assert flight is observed["flight"]
    assert is_owner is False


def test_fallback_branch_still_preserved(monkeypatch) -> None:
    """The dev/test substitution path must still bypass the production scan."""
    calls = {"n": 0}
    _install_slow_selector(monkeypatch, calls)

    response = market_router.opportunities()

    assert response.sourceMode == "curated_fallback"
    assert response.pipelineError is None
    assert calls["n"] == 1
