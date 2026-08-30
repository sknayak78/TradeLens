"""ER-0029 — launch education and dashboard reliability tests."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from datetime import datetime, timezone

import pytest

from routers import market as market_router
from services.opportunity_selection import (
    _evaluate_candidates_parallel,
    _evaluate_single_candidate,
    select_opportunities,
)


def _stock(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "name": symbol,
        "price": 100.0,
        "changePct": 1.0,
        "rsi": 55.0,
        "ema20": 98.0,
        "ema50": 95.0,
        "ema200": 90.0,
        "vwap": 99.0,
        "volume": 1_000_000,
        "sector": "Test",
    }


def test_evaluate_single_candidate_survives_provider_error():
    service = MagicMock()
    service.get_stock.side_effect = RuntimeError("provider timeout")

    result = _evaluate_single_candidate(_stock("FAIL"), service, {})
    assert result is None


def test_evaluate_candidates_parallel_returns_partial_results():
    service = MagicMock()
    reasons = {}

    def _get_stock(symbol: str):
        if symbol == "BAD":
            raise RuntimeError("boom")
        payload = _stock(symbol)
        result = MagicMock()
        result.data = payload
        return result

    service.get_stock.side_effect = _get_stock
    service.get_stock_insight.return_value = MagicMock(
        data={"support": 90.0, "resistance": 110.0, "series": []}
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.opportunity_selection.decide",
            lambda snapshot, insight: MagicMock(
                trend="bullish",
                score=80,
                recommendation=MagicMock(action="Watch"),
            ),
        )
        mp.setattr(
            "services.opportunity_selection.analysis_service.analyse",
            lambda snapshot: MagicMock(
                strength_score=70,
                classification="Test",
                trade_setup="Momentum",
            ),
        )
        evaluated = _evaluate_candidates_parallel(
            [_stock("GOOD1"), _stock("BAD"), _stock("GOOD2")],
            service,
            reasons,
        )

    assert len(evaluated) == 2
    symbols = {row.symbol for row in evaluated}
    assert symbols == {"GOOD1", "GOOD2"}


def test_parallel_evaluation_faster_than_sequential_for_slow_symbols():
    """Parallel enrichment should beat serial wall-clock when each symbol sleeps."""
    service = MagicMock()
    reasons = {}
    delay = 0.05
    symbols = [f"S{i}" for i in range(4)]

    def _get_stock(symbol: str):
        time.sleep(delay)
        result = MagicMock()
        result.data = _stock(symbol)
        return result

    service.get_stock.side_effect = _get_stock
    service.get_stock_insight.return_value = MagicMock(
        data={"support": 90.0, "resistance": 110.0, "series": []}
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.opportunity_selection.decide",
            lambda snapshot, insight: MagicMock(
                trend="bullish",
                score=80,
                recommendation=MagicMock(action="Watch"),
            ),
        )
        mp.setattr(
            "services.opportunity_selection.analysis_service.analyse",
            lambda snapshot: MagicMock(
                strength_score=70,
                classification="Test",
                trade_setup="Momentum",
            ),
        )
        started = time.perf_counter()
        _evaluate_candidates_parallel([_stock(s) for s in symbols], service, reasons)
        elapsed = time.perf_counter() - started

    serial_estimate = delay * len(symbols)
    assert elapsed < serial_estimate * 0.85


def test_opportunities_endpoint_uses_short_lived_cache(monkeypatch):
    market_router._opportunities_cache["response"] = None
    market_router._opportunities_cache["expires_at"] = 0.0

    calls = {"count": 0}

    def _fake_select(_service):
        calls["count"] += 1
        selection = MagicMock()
        selection.rows = []
        selection.action_counts = {}
        metadata = {
            "provider": "test",
            "cached": False,
            "asOf": datetime.now(timezone.utc),
            "marketStatus": "OPEN",
        }
        return selection, metadata

    monkeypatch.setattr(market_router, "select_opportunities", _fake_select)

    first = market_router.opportunities()
    second = market_router.opportunities()

    assert calls["count"] == 1
    assert first is second


def test_select_opportunities_empty_eligible_universe():
    service = MagicMock()
    service.get_all_stocks.return_value = MagicMock(
        data=[],
        metadata=MagicMock(to_api_dict=lambda: {"provider": "seed", "cached": True, "asOf": "now", "marketStatus": "OPEN"}),
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.opportunity_selection.screen_candidates",
            lambda rows: MagicMock(eligible=[], universe_size=0, eligible_count=0, excluded_count=0),
        )
        result, _meta = select_opportunities(service)

    assert result.rows == ()
    assert result.analysed_count == 0
