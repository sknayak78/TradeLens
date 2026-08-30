"""Offline tests for the Learning Journey endpoint (ER-0035).

The endpoint functions are called directly with a seed-backed service, so these
tests need no network, no database and no running server.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

import routers.learning as learning_router
from services.market_data_service import MarketDataService
from services.providers.seed_provider import SeedProvider


@pytest.fixture
def seeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve the endpoint from the deterministic seed provider only."""
    service = MarketDataService(
        primary_provider=SeedProvider(), fallback_provider=SeedProvider()
    )
    monkeypatch.setattr(learning_router, "market_data_service", service)


def _study(symbol: str = "RELIANCE") -> Dict[str, Any]:
    return learning_router.learning_stock(symbol).model_dump()


def _revealed(symbol: str = "RELIANCE") -> Dict[str, Any]:
    return learning_router.learning_stock(symbol, reveal=True).model_dump()


def test_study_payload_has_all_headline_metrics(seeded: None) -> None:
    study = _study()

    for field in (
        "symbol", "name", "price", "changePct", "trend", "sector",
        "rsi", "ema20", "ema50", "ema200", "vwap", "volume",
        "support", "resistance", "series",
    ):
        assert field in study, f"missing {field}"

    assert study["symbol"] == "RELIANCE"
    assert study["series"]


def test_study_payload_never_reveals_the_mentor(seeded: None) -> None:
    study = _study()
    assert study["recommendation"] is None
    # No Mentor decision, strategy, confidence, or conclusion leaks.
    assert not any(key for key in study if key.startswith("mentor"))


def test_reveal_includes_the_mentor_recommendation(seeded: None) -> None:
    revealed = _revealed()
    assert revealed["recommendation"] is not None
    rec = revealed["recommendation"]
    assert rec["action"] in {"Strong Buy", "Buy", "Watch", "Wait", "Avoid"}
    assert "verdict" in rec
    assert "confidence" in rec
    assert "why" in rec
    assert "risks" in rec


def test_mentor_hidden_and_revealed_study_data_are_consistent(seeded: None) -> None:
    hidden = _study()
    revealed = _revealed()
    # The evidence shown never changes because the Mentor view was revealed.
    for key in ("price", "rsi", "ema20", "ema50", "ema200", "support", "resistance"):
        assert revealed[key] == hidden[key]


def test_seeded_indicators_mark_partial_quality(seeded: None) -> None:
    # Seed data has no EMA50/EMA200 history, so they surface as unavailable.
    study = _study()
    assert study["ema50"] is None
    assert study["ema200"] is None
    assert study["dataQuality"] == "Partial"


def test_unknown_symbol_still_returns_404(seeded: None) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        learning_router.learning_stock("NOSUCHSYMBOL")

    assert excinfo.value.status_code == 404


def test_unknown_symbol_reveal_still_returns_404(seeded: None) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        learning_router.learning_stock("NOSUCHSYMBOL", reveal=True)

    assert excinfo.value.status_code == 404


def test_timeframe_is_normalized(seeded: None) -> None:
    study = learning_router.learning_stock("RELIANCE", timeframe="1y").model_dump()
    assert study["timeframe"] == "1Y"


def test_series_points_carry_ohlcv_for_candles(seeded: None) -> None:
    """The study's series must expose OHLCV so DIY Research can draw candles.

    The series shares the same `SeriesPoint` model as Dashboard; it must not
    strip the o/h/l/vol keys that `bars_to_series()` produces. Seed data is
    degenerate (open=high=low=close) but never fabricated.
    """
    study = _study()
    series = study["series"]

    assert series
    for point in series:
        assert "t" in point and "v" in point
        assert "o" in point and "h" in point and "l" in point
        assert "vol" in point
        assert point["o"] == point["h"] == point["l"] == point["v"]
