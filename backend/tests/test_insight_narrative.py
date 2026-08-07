"""Insight v2 — educational narrative consistency (ER-0020).

Acceptance:
* No repeated information across sections
* Every insight teaches at least one trading principle
* Users understand both what to do and why
"""
from __future__ import annotations

import re
from typing import Iterable, List

import pytest

from recommendation.config import STRATEGIES
from recommendation.engine import RecommendationEngine
from recommendation.insight import MENTOR_LESSONS, WHO_IS_THIS_FOR
from recommendation.models import Recommendation, RecommendationInput

engine = RecommendationEngine()


def _bullish(**overrides) -> RecommendationInput:
    values = {
        "symbol": "RELIANCE",
        "price": 110.0,
        "ema20": 105.0,
        "ema50": 100.0,
        "ema200": 90.0,
        "rsi": 60.0,
        "support": 100.0,
        "resistance": 120.0,
    }
    values.update(overrides)
    return RecommendationInput(**values)


#: Representative inputs that should cover every strategy (Mentor Engine fixtures).
STRATEGY_FIXTURES: dict[str, RecommendationInput] = {
    "Trend Continuation": _bullish(price=110.0),
    "Pullback": _bullish(price=110.0, rsi=85.0, resistance=125.0),
    "Breakout": _bullish(
        price=100.0,
        ema20=99.0,
        ema50=98.0,
        ema200=97.0,
        support=99.0,
        resistance=101.9,
    ),
    "Consolidation": RecommendationInput(
        symbol="INFY",
        price=102.0,
        ema20=100.0,
        ema50=104.0,
        support=95.0,
        resistance=130.0,
    ),
    "No Entry Yet": _bullish(price=80.0, support=70.0, resistance=95.0),
}


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def _section_blobs(recommendation: Recommendation) -> dict[str, List[str]]:
    """Map each Insight v2 section to its prose units."""
    return {
        "verdict": [recommendation.verdict],
        "summary": [recommendation.summary],
        "mentor_lesson": [recommendation.mentor_lesson],
        "what_would_change_my_view": [recommendation.what_would_change_my_view],
        "who_is_this_for": [recommendation.ideal_for],
        "watch_next": [recommendation.next_trigger],
        "entry_condition": [recommendation.entry_condition],
        "why": list(recommendation.why),
        "positives": list(recommendation.positives),
        "risks": list(recommendation.risks),
        "beginner_tip": [recommendation.beginner_tip],
    }


def _all_lines(blobs: dict[str, List[str]]) -> Iterable[tuple[str, str]]:
    for section, lines in blobs.items():
        for line in lines:
            yield section, line


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_every_strategy_teaches_one_mentor_lesson(strategy: str):
    assert strategy in MENTOR_LESSONS
    assert MENTOR_LESSONS[strategy]
    assert strategy in WHO_IS_THIS_FOR
    assert WHO_IS_THIS_FOR[strategy]


@pytest.mark.parametrize("strategy,market", STRATEGY_FIXTURES.items())
def test_insight_exposes_educational_fields(
    strategy: str, market: RecommendationInput
):
    recommendation = engine.recommend(market)

    assert recommendation.strategy == strategy
    assert recommendation.mentor_lesson == MENTOR_LESSONS[strategy]
    assert recommendation.ideal_for == WHO_IS_THIS_FOR[strategy]
    assert recommendation.what_would_change_my_view
    assert recommendation.what_would_change_my_view[0].isupper()
    assert recommendation.what_would_change_my_view.endswith(".")


@pytest.mark.parametrize("strategy,market", STRATEGY_FIXTURES.items())
def test_no_identical_prose_across_sections(
    strategy: str, market: RecommendationInput
):
    """No full sentence may appear in more than one section."""
    recommendation = engine.recommend(market)
    blobs = _section_blobs(recommendation)
    seen: dict[str, str] = {}
    for section, line in _all_lines(blobs):
        key = _normalise(line)
        if not key:
            continue
        if key in seen:
            pytest.fail(
                f"{strategy}: duplicate prose in '{seen[key]}' and '{section}': {line}"
            )
        seen[key] = section


@pytest.mark.parametrize("strategy,market", STRATEGY_FIXTURES.items())
def test_section_purposes_stay_distinct(
    strategy: str, market: RecommendationInput
):
    """Lesson teaches; change-view invalidates; watch-next is operational."""
    recommendation = engine.recommend(market)
    lesson = recommendation.mentor_lesson.casefold()
    change = recommendation.what_would_change_my_view.casefold()
    watch = recommendation.next_trigger.casefold()
    who = recommendation.ideal_for.casefold()

    assert change.startswith("i would")
    assert not watch.startswith("i would")
    assert (
        "watch" in watch
        or "close" in watch
        or "pullback" in watch
        or "reclaim" in watch
        or "defend" in watch
    )
    # Lesson is principle language, not a personal invalidation.
    assert not lesson.startswith("i would")
    assert recommendation.summary.casefold() != lesson
    assert recommendation.verdict.casefold() != lesson


@pytest.mark.parametrize("strategy,market", STRATEGY_FIXTURES.items())
def test_users_get_what_and_why(strategy: str, market: RecommendationInput):
    recommendation = engine.recommend(market)

    # What to do
    assert recommendation.verdict
    assert recommendation.summary
    assert recommendation.entry_condition
    # Why + principle
    assert recommendation.why
    assert recommendation.mentor_lesson
    assert recommendation.risks
    assert recommendation.what_would_change_my_view


def test_trend_continuation_change_view_names_stop():
    recommendation = engine.recommend(_bullish())
    assert recommendation.strategy == "Trend Continuation"
    assert recommendation.levels is not None
    stop = f"{recommendation.levels.stop_loss:,.2f}"
    assert stop in recommendation.what_would_change_my_view
    # Risks must not repeat the same "closes below stop" sentence.
    for risk in recommendation.risks:
        assert stop not in risk


def test_summary_does_not_repeat_trend_evidence():
    recommendation = engine.recommend(_bullish())
    assert recommendation.why
    trend_line = recommendation.why[0]
    assert _normalise(trend_line) not in _normalise(recommendation.summary)
