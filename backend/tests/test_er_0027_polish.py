"""Tests for chart timeframe and enhanced trade journal behavior."""
from __future__ import annotations

from services.chart_timeframe import normalize_timeframe
from services.opportunity_selection import EvaluatedCandidate, select_featured_candidates
from routers.trades import _calc_realized_pnl, _calc_unrealized_pnl


def test_normalize_timeframe_defaults_invalid_values():
    assert normalize_timeframe(None) == "1W"
    assert normalize_timeframe("bad") == "1W"
    assert normalize_timeframe("1M") == "1M"


def test_short_realized_pnl_matches_drreddy_example():
    assert _calc_realized_pnl("SHORT", 590, 578, 20) == 240


def test_long_realized_pnl():
    assert _calc_realized_pnl("LONG", 100, 110, 10) == 100


def test_unrealized_pnl_for_open_positions():
    assert _calc_unrealized_pnl("LONG", 600, 605, 10) == 50
    assert _calc_unrealized_pnl("SHORT", 590, 578, 20) == 240


def test_featured_opportunities_include_multiple_action_buckets():
    from tests.test_er_0024_opportunity_ranking import _candidate

    candidates = [
        _candidate("W1", action="Watch", recommendation_score=95, strength_score=90),
        _candidate("W2", action="Watch", recommendation_score=90, strength_score=85),
        _candidate("WAIT1", action="Wait", recommendation_score=80, strength_score=70),
        _candidate("AVOID1", action="Avoid", recommendation_score=70, strength_score=60),
        _candidate("BUY1", action="Buy", recommendation_score=85, strength_score=50),
    ]
    featured = select_featured_candidates(candidates, max_rows=5)
    actions = {row.action for row in featured}
    assert {"Buy", "Watch", "Wait", "Avoid"}.issubset(actions)
