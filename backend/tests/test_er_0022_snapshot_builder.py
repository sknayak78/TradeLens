"""ER-0022 snapshot builder compatibility tests."""
from __future__ import annotations

from services.market_data.models import Instrument, Quote, StockInsight, StockSnapshot
from services.market_data.screening import screen_candidate
from services.market_data.snapshot_builder import (
    SCREENING_REQUIRED_FIELDS,
    assert_legacy_stock_fields,
    build_legacy_insight_dict,
    build_legacy_stock_dict,
    build_legacy_stock_from_quote,
    legacy_row_to_stock_insight,
    legacy_row_to_stock_snapshot,
)


def _snapshot() -> StockSnapshot:
    return StockSnapshot(
        symbol="RELIANCE",
        name="Reliance Industries",
        price=2934.55,
        change_pct=1.24,
        rsi=62.4,
        ema20=2891.32,
        vwap=2918.75,
        volume=4_820_000,
        trend="bullish",
        day_high=2940.0,
        avg_volume=4_097_000,
        sector="Energy",
        ema50=2880.0,
        ema200=2800.0,
        score=88,
        support=2890.0,
        resistance=2985.0,
    )


def test_build_legacy_stock_dict_preserves_all_screening_fields() -> None:
    payload = build_legacy_stock_dict(_snapshot())
    for field in SCREENING_REQUIRED_FIELDS:
        assert field in payload, f"missing {field}"


def test_assert_legacy_stock_fields_detects_missing_keys() -> None:
    payload = build_legacy_stock_dict(_snapshot())
    payload.pop("sector")
    try:
        assert_legacy_stock_fields(payload)
    except ValueError as exc:
        assert "sector" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_build_legacy_stock_from_quote_composes_expected_payload() -> None:
    instrument = Instrument(symbol="RELIANCE", name="Reliance", sector="Energy")
    quote = Quote(symbol="RELIANCE", price=100.0, change_pct=1.0, volume=1000)
    payload = build_legacy_stock_from_quote(
        instrument,
        quote,
        rsi=55.0,
        ema20=99.0,
        vwap=100.0,
        trend="bullish",
        day_high=101.0,
        avg_volume=900,
    )
    assert payload["symbol"] == "RELIANCE"
    assert payload["price"] == 100.0
    assert payload["sector"] == "Energy"


def test_legacy_payload_passes_screening() -> None:
    payload = build_legacy_stock_dict(_snapshot())
    outcome = screen_candidate(payload)
    assert outcome.eligible is True


def test_build_legacy_insight_dict_preserves_keys() -> None:
    insight = StockInsight(
        symbol="RELIANCE",
        support=2890.0,
        resistance=2985.0,
        ai_insight="test",
        series=({"t": "09:15", "v": 2905.2},),
    )
    payload = build_legacy_insight_dict(insight)
    assert set(payload) == {"support", "resistance", "aiInsight", "series"}


def test_legacy_row_to_stock_snapshot_matches_seed_row() -> None:
    from seed_data import STOCKS_BY_SYMBOL

    legacy = STOCKS_BY_SYMBOL["RELIANCE"]
    snapshot = legacy_row_to_stock_snapshot(legacy)
    payload = snapshot.to_legacy_dict()
    for field in SCREENING_REQUIRED_FIELDS:
        assert payload[field] == legacy[field]
    assert payload.get("ema50") == legacy.get("ema50")
    assert payload.get("score") == legacy.get("score")


def test_legacy_row_to_stock_insight_matches_seed_row() -> None:
    from seed_data import INSIGHTS

    legacy = INSIGHTS["RELIANCE"]
    insight = legacy_row_to_stock_insight(legacy, "RELIANCE")
    payload = insight.to_legacy_dict()
    assert payload["support"] == legacy["support"]
    assert payload["resistance"] == legacy["resistance"]
    assert payload["aiInsight"] == legacy["aiInsight"]
    assert payload["series"] == legacy["series"]
