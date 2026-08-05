"""RecommendationEngine — deterministic trade recommendations from live indicators.

The engine answers one question: *is this a good time to open a position in this
stock today?*  It has no portfolio context, so it never returns a
position-management verdict (Hold, Add More, Book Profit, Exit); those belong to
a future Portfolio Advisor.  The five answers it can give are Strong Buy, Buy,
Watch, Wait and Avoid.

The engine is pure: no network access, no database access, no LLM, no clock or
randomness.  It consumes a :class:`~recommendation.models.RecommendationInput`
(price, EMA20/50/200, RSI, support, resistance) and returns a
:class:`~recommendation.models.Recommendation` carrying the action, a one-line
verdict, a plain-English summary, the reasoning, the trade levels and the next
thing to watch.

Trend is derived from the EMA stack rather than taken from any snapshot field so
seeded trend values — and every legacy analysis field — cannot influence the
outcome.
"""
from __future__ import annotations

import json
import logging
import math
from typing import Any, List, Optional, Tuple

from . import narrative
from .narrative import Limits
from .config import (
    ACTION_BUY_MIN_SCORE,
    ACTION_STRONG_BUY_MIN_SCORE,
    ACTION_WAIT_MIN_SCORE,
    ACTION_WATCH_MIN_SCORE,
    BEGINNER_TIPS,
    CONFIDENCE_BANDS,
    CONFIDENCE_CEILING,
    CONVICTION_BANDS,
    HOLDING_PERIODS,
    IDEAL_FOR,
    INDICATOR_LABELS,
    MAX_SCORE,
    MIN_HEADROOM_PCT,
    MIN_RISK_REWARD,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SCORING_RULES,
    SECOND_TARGET_BAND_SHARE,
    STOP_SUPPORT_MULTIPLIER,
)
from .models import (
    Action,
    Conviction,
    DataQuality,
    Recommendation,
    RecommendationInput,
    Strategy,
    TradeLevels,
    Trend,
)

logger = logging.getLogger("tradelens.recommendation")

#: Actions that put money to work today.
_ENTRY_ACTIONS: Tuple[Action, ...] = ("Strong Buy", "Buy")
#: Actions whose confidence grows with the bullish evidence.  For the waiting
#: states the opposite holds: the weaker the setup, the surer the call.
_POSITIVE_ACTIONS: Tuple[Action, ...] = ("Strong Buy", "Buy", "Watch")


def _event(event: str, **fields: Any) -> str:
    """Serialize operational fields consistently for standard Python logging."""
    return json.dumps({"event": event, **fields}, sort_keys=True)


class RecommendationEngine:
    """Rule-based recommendation engine for a single live indicator snapshot."""

    def recommend(self, market: RecommendationInput) -> Recommendation:
        rules_matched, score = self._score(market)
        trend = self._trend(market)
        levels = self._levels(market)
        limits = self._limits(market, trend, score, levels)
        action = self._action(trend, score, limits)
        published_levels = None if action == "Avoid" else levels
        strategy = self._strategy(market, action, published_levels, limits)

        story = narrative.build(
            market=market,
            trend=trend,
            action=action,
            score=score,
            rules_matched=rules_matched,
            levels=published_levels,
            limits=limits,
        )
        summary = story.summary

        recommendation = Recommendation(
            symbol=market.symbol,
            action=action,
            strategy=strategy,
            verdict=story.verdict,
            summary=summary,
            conviction=self._conviction(score),
            score=score,
            trend=trend,
            confidence=self._confidence(market, action, score),
            data_quality=self._data_quality(market),
            holding_period=HOLDING_PERIODS[action],
            next_trigger=story.next_trigger,
            beginner_tip=BEGINNER_TIPS[action],
            ideal_for=IDEAL_FOR[action],
            entry_condition=story.entry_condition,
            # Legacy field: v1.0 consumers render `rationale`, which now carries
            # the same plain-English text as `summary`.
            rationale=summary,
            why=story.why,
            positives=story.positives,
            risks=story.risks,
            rules_matched=rules_matched,
            warnings=self._warnings(market, limits),
            levels=published_levels,
        )
        logger.debug(_event(
            "recommendation.generated",
            symbol=recommendation.symbol,
            action=recommendation.action,
            score=recommendation.score,
            trend=recommendation.trend,
        ))
        return recommendation

    def recommend_many(
        self, markets: List[RecommendationInput]
    ) -> List[Recommendation]:
        return [self.recommend(market) for market in markets]

    # ---------- Scoring ----------

    def _score(self, market: RecommendationInput) -> Tuple[List[str], int]:
        matched: List[str] = []
        score = 0
        for rule in SCORING_RULES:
            if rule.check(market):
                matched.append(rule.key)
                score += rule.points
        return matched, min(score, MAX_SCORE)

    def _conviction(self, score: int) -> Conviction:
        for band in CONVICTION_BANDS:
            if score >= band["min"]:
                return band["label"]
        return CONVICTION_BANDS[-1]["label"]

    def _confidence(
        self, market: RecommendationInput, action: Action, score: int
    ) -> float:
        """How sure TradeLens is of *this call* — not the odds of a profit.

        Each action owns a band, so confidence can never contradict the action
        it accompanies, and the position inside that band comes from how much
        evidence the call rests on: the strength of the setup plus how much of
        the market history was actually available.  A waiting call is read the
        other way round — the weaker the setup, the surer TradeLens is that
        standing aside is right.
        """
        low, high = CONFIDENCE_BANDS[action]
        setup_strength = score / MAX_SCORE
        if action not in _POSITIVE_ACTIONS:
            setup_strength = 1.0 - setup_strength
        evidence = 0.5 * setup_strength + 0.5 * market.completeness
        return round(min(low + (high - low) * evidence, CONFIDENCE_CEILING), 2)

    def _data_quality(self, market: RecommendationInput) -> DataQuality:
        return "Complete" if not market.missing_indicators else "Partial"

    # ---------- Trend (EMA stack only) ----------

    def _trend(self, market: RecommendationInput) -> Trend:
        emas = [
            value
            for value in (market.ema20, market.ema50, market.ema200)
            if value is not None
        ]
        if not emas:
            return "neutral"
        above = sum(1 for ema in emas if market.price > ema)
        if above == len(emas):
            return "bullish"
        if above == 0:
            return "bearish"
        return "neutral"

    # ---------- Warnings (machine-readable; prose lives in `risks`) ----------

    def _warnings(self, market: RecommendationInput, limits: Limits) -> List[str]:
        warnings: List[str] = []
        missing = market.missing_indicators
        if missing:
            labels = ", ".join(INDICATOR_LABELS[name] for name in missing)
            warnings.append(
                f"partial_data: {labels} unavailable, so this recommendation is "
                "based on an incomplete indicator set."
            )
        if market.rsi is not None:
            if market.rsi >= RSI_OVERBOUGHT:
                warnings.append("rsi_overbought")
            elif market.rsi <= RSI_OVERSOLD:
                warnings.append("rsi_oversold")
        if market.resistance is not None and market.price >= market.resistance:
            warnings.append("price_at_or_above_resistance")
        if narrative.LIMIT_NO_LEVELS in limits:
            warnings.append("no_usable_levels")
        if narrative.LIMIT_POOR_RISK_REWARD in limits:
            warnings.append("risk_reward_below_minimum")
        return warnings

    # ---------- Trade levels ----------

    def _levels(self, market: RecommendationInput) -> Optional[TradeLevels]:
        if not market.has_valid_levels:
            return None
        support = market.support
        resistance = market.resistance
        if support is None or resistance is None or resistance <= market.price:
            return None

        # Entry zone: pull back to the higher of EMA20 and support, buy up to
        # the last price.
        entry_max = market.price
        entry_min = support if market.ema20 is None else max(market.ema20, support)
        if entry_min >= entry_max:
            return None

        stop_loss = support * STOP_SUPPORT_MULTIPLIER
        if stop_loss >= entry_min:
            return None

        target1 = resistance
        target2 = resistance + SECOND_TARGET_BAND_SHARE * (resistance - support)
        # Measured from the midpoint of the zone — the representative fill.
        entry_reference = (entry_min + entry_max) / 2
        if entry_reference <= stop_loss:
            return None
        risk_reward = (target1 - entry_reference) / (entry_reference - stop_loss)
        computed = (entry_min, entry_max, stop_loss, target1, target2, risk_reward)
        if not all(math.isfinite(value) for value in computed):
            # Levels are all-or-nothing: a partial set is worse than none.
            return None
        return TradeLevels(
            entry_min=round(entry_min, 2),
            entry_max=round(entry_max, 2),
            stop_loss=round(stop_loss, 2),
            target1=round(target1, 2),
            target2=round(target2, 2),
            risk_reward=round(risk_reward, 2),
        )

    # ---------- Blockers ----------

    def _limits(
        self,
        market: RecommendationInput,
        trend: Trend,
        score: int,
        levels: Optional[TradeLevels],
    ) -> Limits:
        """Everything standing between this snapshot and a fresh entry today.

        The same list decides the action and drives the "why not stronger?"
        explanation, so the two can never disagree.
        """
        limits: List[str] = []
        if trend == "bearish":
            limits.append(narrative.LIMIT_TREND_BEARISH)
        elif trend != "bullish":
            limits.append(narrative.LIMIT_TREND_NOT_BULLISH)
        if market.rsi is not None and market.rsi >= RSI_OVERBOUGHT:
            limits.append(narrative.LIMIT_OVERBOUGHT)
        headroom = market.headroom_pct
        if headroom is None or headroom < MIN_HEADROOM_PCT:
            limits.append(narrative.LIMIT_THIN_HEADROOM)
        if levels is None:
            limits.append(narrative.LIMIT_NO_LEVELS)
        elif levels.risk_reward < MIN_RISK_REWARD:
            limits.append(narrative.LIMIT_POOR_RISK_REWARD)
        if score < ACTION_BUY_MIN_SCORE:
            limits.append(narrative.LIMIT_WEAK_EVIDENCE)
        if market.missing_indicators:
            limits.append(narrative.LIMIT_PARTIAL_DATA)
        return tuple(limits)

    # ---------- Action ----------

    _ENTRY_BLOCKERS = (
        narrative.LIMIT_TREND_BEARISH,
        narrative.LIMIT_TREND_NOT_BULLISH,
        narrative.LIMIT_OVERBOUGHT,
        narrative.LIMIT_THIN_HEADROOM,
        narrative.LIMIT_NO_LEVELS,
        narrative.LIMIT_POOR_RISK_REWARD,
        narrative.LIMIT_WEAK_EVIDENCE,
    )

    def _strategy(
        self,
        market: RecommendationInput,
        action: Action,
        levels: Optional[TradeLevels],
        limits: Limits,
    ) -> Strategy:
        """Describe *how* an entry would be taken, separately from the decision.

        Keeping this out of the action means a consumer switching on the action
        never has to parse a strategy out of it.
        """
        if action in _ENTRY_ACTIONS:
            return "Immediate Entry"
        if action != "Watch":
            return "No Entry Yet"
        if narrative.LIMIT_THIN_HEADROOM in limits and market.resistance is not None:
            return "Breakout Confirmation"
        if levels is not None:
            return "Pullback Entry"
        return "No Entry Yet"

    def _action(self, trend: Trend, score: int, limits: Limits) -> Action:
        """Answer "should I open a position today?" and nothing else.

        A fresh entry needs an intact uptrend, strong evidence, room to run, a
        usable exit and a reward worth the risk.  Anything short of that is a
        waiting state, graded by how much of the case is already in place.
        """
        if trend == "bearish":
            return "Avoid"
        if not any(limit in limits for limit in self._ENTRY_BLOCKERS):
            if score >= ACTION_STRONG_BUY_MIN_SCORE:
                return "Strong Buy"
            return "Buy"
        if score >= ACTION_WATCH_MIN_SCORE:
            return "Watch"
        if score >= ACTION_WAIT_MIN_SCORE:
            return "Wait"
        return "Avoid"


# Module-level singleton — pure functions, thread-safe.
engine = RecommendationEngine()
