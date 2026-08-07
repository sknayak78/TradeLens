"""RecommendationEngine — deterministic trade recommendations from live indicators.

The engine answers one question: *is this a good time to open a position in this
stock today?*  It has no portfolio context, so it never returns a
position-management verdict (Hold, Add More, Book Profit, Exit); those belong to
a future Portfolio Advisor.  The five answers it can give are Strong Buy, Buy,
Watch, Wait and Avoid.

**Strategy is the parent decision (ER-0016).**  The engine first classifies the
trading thesis (Trend Continuation, Pullback, Breakout, Consolidation, or
No Entry Yet).  Action, published levels, Watch Next and narrative are all
derived from that thesis so a recommendation can never carry two conflicting
plans (e.g. a buy-now entry range alongside "wait for the breakout").

The engine is pure: no network access, no database access, no LLM, no clock or
randomness.  It consumes a :class:`~recommendation.models.RecommendationInput`
(price, EMA20/50/200, RSI, support, resistance) and returns a
:class:`~recommendation.models.Recommendation`.

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
    ACTION_WATCH_MIN_SCORE,
    BEGINNER_TIPS,
    CONFIDENCE_BANDS,
    CONFIDENCE_CEILING,
    CONVICTION_BANDS,
    HOLDING_PERIODS,
    IDEAL_FOR,
    INDICATOR_LABELS,
    LEVEL_STRATEGIES,
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
        # Candidate geometry only — publishing is gated by strategy below.
        zone = self._entry_zone(market)
        limits = self._limits(market, trend, score, zone)

        # Parent decision: one thesis for the whole recommendation.
        strategy = self._strategy(market, trend, limits, zone)
        action = self._action(strategy, trend, score)
        levels = self._levels_for(strategy, zone)

        story = narrative.build(
            market=market,
            trend=trend,
            action=action,
            strategy=strategy,
            score=score,
            rules_matched=rules_matched,
            levels=levels,
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
            levels=levels,
        )
        logger.debug(_event(
            "recommendation.generated",
            symbol=recommendation.symbol,
            action=recommendation.action,
            strategy=recommendation.strategy,
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

    # ---------- Trend (the three averages read together) ----------

    def _trend(self, market: RecommendationInput) -> Trend:
        """Read the short, medium and long averages as one structure.

        A single average cannot tell a pullback from a breakdown, so the three
        are weighed together: while the price holds above its long-term average
        the larger uptrend is intact and a dip under the shorter averages is a
        pullback, never a downtrend.  Only a price that has lost the long-term
        average — or every average, when there is no long-term one — is bearish.
        """
        emas = [
            value
            for value in (market.ema20, market.ema50, market.ema200)
            if value is not None
        ]
        if not emas:
            return "neutral"
        above = sum(1 for ema in emas if market.price > ema)

        if above == len(emas) and not market.stack_falling:
            return "bullish"
        if market.ema200 is not None and market.price > market.ema200:
            # Below a shorter average but still above the long-term one.
            return "neutral"
        if above == 0 or market.stack_falling:
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

    # ---------- Candidate entry zone (not yet published) ----------

    def _entry_zone(self, market: RecommendationInput) -> Optional[TradeLevels]:
        """Compute pullback/continuation geometry if the numbers support it.

        This is a *candidate* only.  Whether it appears on the recommendation is
        decided by :meth:`_levels_for` after the strategy is known.
        """
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

    def _levels_for(
        self, strategy: Strategy, zone: Optional[TradeLevels]
    ) -> Optional[TradeLevels]:
        """Publish levels only when the strategy's thesis includes a buy zone."""
        if strategy in LEVEL_STRATEGIES:
            return zone
        return None

    # ---------- Blockers ----------

    def _limits(
        self,
        market: RecommendationInput,
        trend: Trend,
        score: int,
        levels: Optional[TradeLevels],
    ) -> Limits:
        """Everything standing between this snapshot and a fresh entry today.

        The same list feeds strategy classification and the "why not stronger?"
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

    # ---------- Strategy (parent) then Action ----------

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
        trend: Trend,
        limits: Limits,
        zone: Optional[TradeLevels],
    ) -> Strategy:
        """Classify the single trading thesis for this snapshot.

        Strategy is decided before action and before levels are published, so
        every downstream field describes the same plan.
        """
        if trend == "bearish":
            return "No Entry Yet"

        # Pullback wins over Breakout when the price has already slipped under a
        # shorter average: the thesis is "let the dip steady", not "buy a break".
        if market.is_pullback or narrative.LIMIT_OVERBOUGHT in limits:
            return "Pullback"

        # Breakout: still trending, but pressed against resistance — only a
        # confirmed break creates an entry.  Must win over a buy-now zone so we
        # never publish Entry Range alongside "wait for the breakout".
        if (
            narrative.LIMIT_THIN_HEADROOM in limits
            and market.resistance is not None
        ):
            return "Breakout"

        # Better-price wait inside a healthy uptrend (poor reward at last price).
        if (
            zone is not None
            and trend == "bullish"
            and narrative.LIMIT_POOR_RISK_REWARD in limits
        ):
            return "Pullback"

        # Trend Continuation: clear path for a fresh entry with the trend today.
        if trend == "bullish" and not any(
            limit in limits for limit in self._ENTRY_BLOCKERS
        ):
            return "Trend Continuation"

        # Bullish but incomplete — either no zone at all, or wait for price.
        if trend == "bullish":
            return "No Entry Yet" if zone is None else "Pullback"

        # Neutral without a classified pullback: range / unclear.
        return "Consolidation"

    def _action(self, strategy: Strategy, trend: Trend, score: int) -> Action:
        """Derive the decision from the parent strategy.

        Strategy owns the thesis; action is the strength of that thesis today.
        """
        if trend == "bearish":
            return "Avoid"
        if strategy == "Trend Continuation":
            if score >= ACTION_STRONG_BUY_MIN_SCORE:
                return "Strong Buy"
            return "Buy"
        if strategy in ("Breakout", "Pullback"):
            if score >= ACTION_WATCH_MIN_SCORE:
                return "Watch"
            return "Wait"
        # Consolidation, or No Entry Yet on a non-bearish (incomplete) tape.
        return "Wait"


# Module-level singleton — pure functions, thread-safe.
engine = RecommendationEngine()
