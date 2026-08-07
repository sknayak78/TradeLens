"""Plain-English narrative for a recommendation (ER-0017 mentor voice).

Everything a trader reads is built here from the parent **strategy** and a
multi-timeframe reading of the chart, so the explanation can never disagree
with the trading thesis *or* appear to contradict what the user sees on the
chart.

Section jobs (no repeated guidance across sections):

* ``verdict`` — What should I do today?
* ``summary`` — Chart-aware context (short vs long timeframe reconciled)
* ``why`` — What evidence led to this recommendation?
* ``risks`` — What could go wrong?
* ``entry_condition`` — How should I execute? (Trading Plan)
* ``next_trigger`` — What specific event should make me revisit this stock?

The module is pure and template-based: no LLM, no clock, no randomness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .config import (
    COMFORTABLE_HEADROOM_PCT,
    GOOD_RISK_REWARD,
    MIN_HEADROOM_PCT,
    MIN_RISK_REWARD,
    MIN_SUPPORT_CUSHION_PCT,
    RSI_HEALTHY_MAX,
    RSI_HEALTHY_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)
from .models import Action, RecommendationInput, Strategy, TradeLevels, Trend
from .timeframe import TimeframeContext, long_term_level, read_timeframes

#: Reasons a stronger action was blocked, produced by the engine.
LIMIT_OVERBOUGHT = "overbought"
LIMIT_THIN_HEADROOM = "thin_headroom"
LIMIT_POOR_RISK_REWARD = "poor_risk_reward"
LIMIT_NO_LEVELS = "no_levels"
LIMIT_PARTIAL_DATA = "partial_data"
LIMIT_TREND_NOT_BULLISH = "trend_not_bullish"
LIMIT_TREND_BEARISH = "trend_bearish"
LIMIT_WEAK_EVIDENCE = "weak_evidence"

Limits = Tuple[str, ...]


@dataclass(frozen=True)
class Narrative:
    """Everything a consumer renders as prose for one recommendation."""

    verdict: str
    summary: str
    next_trigger: str
    entry_condition: str
    why: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)


def _price(value: float) -> str:
    return f"{value:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.1f}%"


def _recent_average(market: RecommendationInput) -> str:
    """Name EMA20 the way a beginner thinks of it: the recent average price."""
    if market.ema20 is None:
        return "its recent average price"
    return f"its recent average price of {_price(market.ema20)}"


def _long_average(market: RecommendationInput) -> str:
    level = long_term_level(market)
    if level is None:
        return "its long-term average"
    return f"its long-term average of {_price(level)}"


# ---------- Chart-aware structure (mentor context) ----------

def _structure_summary(
    market: RecommendationInput, ctx: TimeframeContext
) -> str:
    """Reconcile what the chart shows with the broader trend.

    This is the sentence a beginner needs when short-term candles disagree with
    the engine's longer-horizon call.
    """
    if ctx.is_counter_trend_rally:
        return (
            "The stock has recovered over the last few trading sessions, but "
            f"the broader long-term trend remains bearish because price is still "
            f"below {_long_average(market)}. This appears to be a counter-trend "
            "rally — a bounce inside a larger downtrend — rather than a "
            "confirmed trend reversal."
        )
    if ctx.is_pullback:
        return (
            "The stock remains in a long-term uptrend despite the recent "
            "short-term pullback: price is still above "
            f"{_long_average(market)}, even though it has slipped relative to "
            "its recent average."
        )
    if ctx.structure == "aligned_bullish":
        if market.stack_rising:
            return (
                "Recent buying and the broader long-term trend agree: price is "
                "holding above its short, medium and long-term averages, so the "
                "uptrend is intact on every horizon."
            )
        return (
            "Recent buying and the broader long-term trend agree: price is "
            f"holding above {_long_average(market)}, so the uptrend is intact."
        )
    if ctx.structure == "aligned_bearish":
        return (
            "Recent selling and the broader long-term trend agree: price remains "
            f"below {_long_average(market)}, so the downtrend is still in force."
        )
    if ctx.structure == "consolidation":
        return (
            "Short-term and longer-term signals are mixed, so the stock is "
            "consolidating without a clear direction to lean on yet."
        )
    return (
        "There is not enough average-price history to separate a short-term "
        "bounce from a lasting trend, so this reading stays cautious."
    )


# ---------- Section: Verdict (what should I do today?) ----------

def _verdict(
    market: RecommendationInput,
    action: Action,
    strategy: Strategy,
    ctx: TimeframeContext,
    limits: Limits,
) -> str:
    if strategy == "Trend Continuation":
        if action == "Strong Buy":
            return (
                "Take a fresh entry today only with a pre-planned exit and "
                "sensible position size."
            )
        return (
            "A modest fresh entry is reasonable today, provided the exit is "
            "decided before you buy."
        )
    if strategy == "Breakout":
        return (
            "Do not buy today — wait for a confirmed breakout close above "
            "resistance before acting."
        )
    if strategy == "Pullback":
        if LIMIT_OVERBOUGHT in limits:
            return (
                "Do not chase today's price — wait for a short-term pullback "
                "toward the buy zone."
            )
        if ctx.is_pullback:
            return (
                "Do not buy the dip yet — let the short-term pullback steady "
                "before starting a position."
            )
        return (
            "Stay on the sidelines today and wait for a better short-term entry."
        )
    if strategy == "Consolidation":
        return (
            "Do nothing today — wait for the range to resolve into a clearer "
            "direction."
        )
    # No Entry Yet / Avoid
    if ctx.is_counter_trend_rally:
        return (
            "Stay out today — the recent bounce looks like a counter-trend "
            "rally, not a safe fresh entry."
        )
    if action == "Avoid" or ctx.long_term == "bearish":
        return "Stay out today — this is not a stock to buy while the broader trend is down."
    return "Do nothing today — wait for a clearer setup before putting money at risk."


# ---------- Section: Summary (chart context only; no Watch Next) ----------

def _summary(
    market: RecommendationInput,
    strategy: Strategy,
    ctx: TimeframeContext,
) -> str:
    context = _structure_summary(market, ctx)
    if strategy == "Trend Continuation":
        return (
            f"{context} That alignment is what makes a trend-continuation "
            "entry teachable: you are joining the prevailing direction, not "
            "fighting it."
        )
    if strategy == "Breakout":
        return (
            f"{context} Price is pressed against overhead resistance, so the "
            "lesson is breakout confirmation: a close through the ceiling "
            "matters more than hoping from underneath it."
        )
    if strategy == "Pullback":
        if ctx.is_pullback:
            return (
                f"{context} A pullback is a pause inside a larger uptrend — "
                "useful only once the short-term slide stops falling."
            )
        return (
            f"{context} Even so, short-term price has run ahead of itself, so "
            "the disciplined study is to wait for a pullback rather than chase."
        )
    if strategy == "Consolidation":
        return (
            f"{context} Consolidation means patience: there is no edge in "
            "forcing an entry before direction returns."
        )
    if ctx.is_counter_trend_rally:
        return (
            f"{context} Beginners often buy the bounce they see on the chart; "
            "the mentor's job is to show that a rising few sessions do not "
            "erase a long-term downtrend."
        )
    return (
        f"{context} Until buyers reclaim control on the longer timeframe, "
        "standing aside is the disciplined choice."
    )


# ---------- Evidence helpers ----------

def _momentum_observation(rsi: Optional[float]) -> Optional[str]:
    if rsi is None:
        return None
    if rsi >= RSI_OVERBOUGHT:
        return (
            "Short-term momentum has run hot: the stock has advanced very "
            "quickly and is overdue a breather, which makes chasing today an "
            "expensive way to join the move."
        )
    if RSI_HEALTHY_MIN <= rsi <= RSI_HEALTHY_MAX:
        return (
            "Short-term momentum looks steady: recent buying has improved "
            "without the move looking overheated."
        )
    if rsi <= RSI_OVERSOLD:
        return (
            "Short-term momentum is still weak: the stock has been sold down "
            "hard and has not steadied yet."
        )
    return (
        "Short-term momentum is lukewarm rather than convincing on recent "
        "sessions."
    )


def _headroom_observation(market: RecommendationInput) -> Optional[str]:
    headroom = market.headroom_pct
    if headroom is None or market.resistance is None:
        return None
    if headroom <= 0:
        return (
            "Price has already reached the ceiling it struggled with last "
            f"time, near {_price(market.resistance)}."
        )
    if headroom < MIN_HEADROOM_PCT:
        return (
            "There is little room left before sellers may reappear near "
            f"{_price(market.resistance)}."
        )
    if headroom >= COMFORTABLE_HEADROOM_PCT:
        return (
            f"There is roughly {_pct(headroom)} of clear air before the next "
            f"real hurdle around {_price(market.resistance)}."
        )
    return (
        f"There is about {_pct(headroom)} of room before the next hurdle "
        f"around {_price(market.resistance)}."
    )


def _cushion_observation(market: RecommendationInput) -> Optional[str]:
    cushion = market.support_cushion_pct
    if cushion is None or market.support is None:
        return None
    if cushion < MIN_SUPPORT_CUSHION_PCT:
        return (
            "Price is sitting almost on top of the level buyers last defended "
            f"({_price(market.support)}), which leaves little margin for error."
        )
    return (
        "Price is comfortably above the level buyers last defended "
        f"({_price(market.support)}), so downside can be measured rather than "
        "guessed."
    )


def _reward_observation(levels: Optional[TradeLevels]) -> Optional[str]:
    if levels is None:
        return None
    if levels.risk_reward >= GOOD_RISK_REWARD:
        return (
            f"The planned move is worth about {levels.risk_reward:.1f} times "
            "what is being risked, which is a healthy trade-off."
        )
    if levels.risk_reward >= MIN_RISK_REWARD:
        return (
            f"The planned move is worth about {levels.risk_reward:.1f} times "
            "what is being risked, which is acceptable but not generous."
        )
    return (
        "At today's prices you would be risking almost as much as you stand to "
        "gain, which is not a trade worth taking."
    )


# ---------- Section: Strengths ----------

def _positives(
    market: RecommendationInput,
    ctx: TimeframeContext,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
) -> List[str]:
    if ctx.long_term == "bearish" and not ctx.is_counter_trend_rally:
        return []
    # Counter-trend rallies still get no "strengths that sound like buy signals".
    if ctx.is_counter_trend_rally:
        return []

    positives: List[str] = []
    if ctx.structure == "aligned_bullish":
        positives.append(
            "Long-term trend and recent sessions both point higher, which is "
            "the cleanest backdrop for a beginner to study."
        )
    elif ctx.is_pullback:
        positives.append(
            "The broader long-term uptrend is still intact — this soft patch is "
            "a pullback to study, not proof the trend has failed."
        )
    elif "price_above_ema200" in rules_matched:
        positives.append(
            "Price is still above its long-term average, so the longer-term "
            "picture has not broken down."
        )

    if "rsi_healthy" in rules_matched and not ctx.is_pullback:
        positives.append(
            "Short-term buying has been steady without looking overheated."
        )

    headroom = market.headroom_pct
    if headroom is not None and headroom >= MIN_HEADROOM_PCT:
        text = _headroom_observation(market)
        if text:
            positives.append(text)

    cushion = market.support_cushion_pct
    if cushion is not None and cushion >= MIN_SUPPORT_CUSHION_PCT:
        text = _cushion_observation(market)
        if text:
            positives.append(text)

    if levels is not None and levels.risk_reward >= MIN_RISK_REWARD:
        text = _reward_observation(levels)
        if text:
            positives.append(text)

    return positives


# ---------- Section: Risks (what could go wrong?) ----------

def _risks(
    market: RecommendationInput,
    action: Action,
    strategy: Strategy,
    ctx: TimeframeContext,
    levels: Optional[TradeLevels],
    limits: Limits,
) -> List[str]:
    risks: List[str] = []

    if ctx.is_counter_trend_rally:
        risks.append(
            "Counter-trend rallies often fade: buying the bounce you see on "
            "the chart can trap you if sellers regain control before the "
            "long-term average is reclaimed."
        )
    elif ctx.long_term == "bearish":
        risks.append(
            "A long-term downtrend can continue far longer than a short bounce "
            "suggests, and buying into one is how beginners lose money fastest."
        )
    elif ctx.is_pullback or strategy == "Pullback":
        risks.append(
            "A short-term pullback only becomes a buying opportunity once it "
            "stops falling; until it steadies it can just as easily keep going."
        )
    elif strategy == "Consolidation" or ctx.structure == "consolidation":
        risks.append(
            "Without a clear trend the stock can swing both ways, so an entry "
            "here is closer to a coin toss than a plan."
        )
    elif strategy == "Breakout":
        risks.append(
            "A failed breakout often snaps back quickly, so buying before the "
            "daily close confirms the move is how breakout traders get trapped."
        )

    if LIMIT_OVERBOUGHT in limits:
        risks.append(
            "After a run this sharp, even good news can be followed by a "
            "short-term pullback that stops out a fresh position."
        )
    if market.rsi is not None and market.rsi <= RSI_OVERSOLD:
        risks.append(
            "A stock sold down this hard usually needs time to steady before it "
            "can rise again."
        )
    if LIMIT_THIN_HEADROOM in limits and market.resistance is not None:
        risks.append(
            "Sellers have turned this stock away near "
            f"{_price(market.resistance)} before, so it can stall or reverse "
            "from here."
        )
    if LIMIT_POOR_RISK_REWARD in limits:
        risks.append(
            "The realistic upside is no bigger than the loss you would take if "
            "you are wrong."
        )
    if LIMIT_NO_LEVELS in limits and strategy not in ("Breakout", "Consolidation"):
        risks.append(
            "There is no reliable place to put an exit, so a position here could "
            "not be risk-managed properly."
        )
    if LIMIT_PARTIAL_DATA in limits:
        risks.append(
            "Part of the usual market history was unavailable, so this reading "
            "is less complete than normal."
        )
    if levels is not None:
        if action in ("Strong Buy", "Buy"):
            risks.append(
                f"If the price closes below {_price(levels.stop_loss)} the idea "
                "has failed and the position should be closed."
            )
        else:
            risks.append(
                f"If the price closes below {_price(levels.stop_loss)} the setup "
                "breaks down and the stock comes off the shortlist."
            )
    return risks


# ---------- Section: Key Reasons (evidence only) ----------

def _why_not_stronger(action: Action, limits: Limits, score: int) -> Optional[str]:
    if action == "Strong Buy":
        return (
            "This is the most positive call TradeLens issues, and it is still a "
            "probability rather than a promise."
        )
    if action == "Buy":
        return (
            f"It is not a Strong Buy because the supporting evidence adds up to "
            f"{score} out of 100 rather than the near-perfect picture that "
            "warrants full conviction."
        )
    if action in ("Wait", "Avoid") and LIMIT_WEAK_EVIDENCE in limits:
        return (
            f"Only {score} of a possible 100 points of supporting evidence are "
            "in place, which is far too little to put money at risk."
        )
    if LIMIT_TREND_BEARISH in limits:
        return (
            "A fresh buy is off the table until price reclaims the long-term "
            "average and holds it — short bounces alone are not enough."
        )
    if LIMIT_OVERBOUGHT in limits:
        return (
            "It is not a buy because short-term price has already stretched far "
            "ahead of itself, and paying up here gives away the best part of "
            "the move."
        )
    if LIMIT_POOR_RISK_REWARD in limits:
        return (
            "It is not a buy because what you would risk is close to what you "
            "could make, and that is a trade worth skipping."
        )
    if LIMIT_NO_LEVELS in limits:
        return (
            "It is not a buy because there is no dependable exit level, and an "
            "entry without an exit is a gamble."
        )
    if LIMIT_THIN_HEADROOM in limits:
        return (
            "It is not a buy because price is pressed against overhead "
            "resistance, so a breakout needs to be confirmed first."
        )
    if LIMIT_TREND_NOT_BULLISH in limits:
        return (
            "It is not a buy because the broader trend has not turned "
            "convincingly upwards yet."
        )
    if LIMIT_WEAK_EVIDENCE in limits:
        return (
            f"Only {score} of a possible 100 points of supporting evidence are "
            "in place, which is too little to justify a stronger call."
        )
    return None


def _why(
    market: RecommendationInput,
    action: Action,
    strategy: Strategy,
    score: int,
    levels: Optional[TradeLevels],
    limits: Limits,
    ctx: TimeframeContext,
) -> List[str]:
    """Evidence bullets — must not repeat the verdict or the Watch Next line."""
    why: List[str] = []

    # Lead with the multi-timeframe fact the beginner needs.
    if ctx.is_counter_trend_rally:
        why.append(
            "Long-term trend: still bearish (price below "
            f"{_long_average(market)})."
        )
        why.append(
            "Short-term momentum: recent sessions have improved — that is the "
            "rise visible on the chart, not a confirmed reversal."
        )
    elif ctx.is_pullback:
        why.append(
            "Long-term trend: still bullish (price holds above "
            f"{_long_average(market)})."
        )
        why.append(
            "Short-term momentum: soft — price has slipped relative to its "
            "recent average, which is a pullback inside the larger uptrend."
        )
    elif ctx.structure == "aligned_bullish":
        why.append(
            "Long-term and short-term trends agree to the upside, which "
            "supports studying a trend-continuation entry."
        )
    elif ctx.structure == "aligned_bearish":
        why.append(
            "Long-term and short-term trends agree to the downside, so strength "
            "on any single green session is not enough to buy."
        )
    elif ctx.structure == "consolidation":
        why.append(
            "Short-term and longer-term averages disagree, so there is no clear "
            "trend to lean on yet."
        )
    else:
        why.append(
            "Available averages are incomplete, so the trend reading stays "
            "limited to what this snapshot can support."
        )

    momentum = _momentum_observation(market.rsi)
    if momentum and not ctx.is_counter_trend_rally:
        # Counter-trend already covered short-term momentum above.
        why.append(momentum)

    if strategy == "Breakout" and market.resistance is not None:
        why.append(
            "Breakout context: price is pressed against resistance near "
            f"{_price(market.resistance)}, so confirmation must come from a "
            "daily close through that level."
        )
    elif ctx.long_term != "bearish":
        location = _headroom_observation(market)
        if location:
            why.append(location)
        elif market.resistance is None or market.support is None:
            why.append(
                "The levels this stock usually respects could not be "
                "established, so there is no map for where to enter or exit."
            )

    if levels is not None and action in ("Strong Buy", "Buy"):
        reward = _reward_observation(levels)
        if reward:
            why.append(reward)

    not_stronger = _why_not_stronger(action, limits, score)
    if not_stronger:
        why.append(not_stronger)
    return why


# ---------- Section: Watch Next ----------

def _next_trigger(
    market: RecommendationInput,
    strategy: Strategy,
    levels: Optional[TradeLevels],
    limits: Limits,
    ctx: TimeframeContext,
) -> str:
    if strategy == "Trend Continuation" and levels is not None:
        return (
            f"Watch the {_price(levels.stop_loss)} level: a daily close below it "
            "means the idea has failed, while a push through "
            f"{_price(levels.target1)} opens the way to "
            f"{_price(levels.target2)}."
        )
    if strategy == "Breakout":
        if market.resistance is not None:
            return (
                "Watch for a daily close above "
                f"{_price(market.resistance)}: that would confirm the breakout "
                "and create a fresh entry."
            )
        return (
            "Watch for a decisive daily close through overhead resistance "
            "before considering an entry."
        )
    if strategy == "Pullback":
        if LIMIT_OVERBOUGHT in limits and levels is not None:
            return (
                "Watch for the price to cool off and settle back into "
                f"{_price(levels.entry_min)}-{_price(levels.entry_max)}, which "
                "would offer a far safer entry."
            )
        if LIMIT_OVERBOUGHT in limits:
            return (
                "Watch for the price to cool off and steady for a few sessions "
                "before considering an entry."
            )
        if levels is not None:
            return (
                "Watch for a pullback into "
                f"{_price(levels.entry_min)}-{_price(levels.entry_max)} that "
                "holds, which would be the entry to act on."
            )
        return (
            f"Watch for the price to steady above {_recent_average(market)} and "
            "for clear support to form before considering an entry."
        )
    if strategy == "Consolidation":
        return (
            f"Watch for the price to steady above {_recent_average(market)} and "
            "for a clear direction to emerge from the range before considering "
            "an entry."
        )

    # Avoid / No Entry Yet — event must match the chart the user sees.
    if ctx.is_counter_trend_rally or ctx.long_term == "bearish":
        level = long_term_level(market)
        if level is not None:
            return (
                "Watch for a daily close back above "
                f"{_long_average(market)} that holds for a few sessions; until "
                "then, treat short-term rallies as temporary."
            )
        return (
            "Watch for buyers to reclaim and hold the long-term average for "
            "several sessions before revisiting this stock."
        )
    if market.ema20 is not None:
        return (
            "Watch for the price to reclaim "
            f"{_recent_average(market)} and hold it for a few sessions; until "
            "then there is nothing to do."
        )
    return (
        "Watch for buyers to defend a level and push the price back above its "
        "recent average before revisiting this stock."
    )


# ---------- Section: Trading Plan (execution only) ----------

def _entry_condition(
    market: RecommendationInput,
    strategy: Strategy,
    levels: Optional[TradeLevels],
    ctx: TimeframeContext,
) -> str:
    if strategy == "Trend Continuation" and levels is not None:
        return (
            f"Consider entering between {_price(levels.entry_min)} and "
            f"{_price(levels.entry_max)}, and exit if the price closes below "
            f"{_price(levels.stop_loss)}."
        )
    if strategy == "Breakout":
        if market.resistance is not None:
            return (
                "Wait for a daily close above "
                f"{_price(market.resistance)} before entering."
            )
        return "Wait for a confirmed breakout above resistance before entering."
    if strategy == "Pullback":
        if levels is not None:
            return (
                "Wait for the price to pull back into "
                f"{_price(levels.entry_min)}-{_price(levels.entry_max)} and hold "
                "there."
            )
        return (
            f"Wait for the price to steady above {_recent_average(market)} "
            "before considering an entry."
        )
    if strategy == "Consolidation":
        return (
            f"Wait for the price to steady above {_recent_average(market)} "
            "before considering an entry."
        )
    if ctx.is_counter_trend_rally or ctx.long_term == "bearish":
        return (
            "No trade: do not buy the bounce. Wait until price reclaims the "
            "long-term average and holds it."
        )
    return (
        f"Wait for the price to steady above {_recent_average(market)} "
        "before considering an entry."
    )


def build(
    market: RecommendationInput,
    trend: Trend,
    action: Action,
    strategy: Strategy,
    score: int,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
    limits: Limits,
) -> Narrative:
    """Assemble every prose field for one recommendation.

    ``trend`` is the engine's decision horizon; ``TimeframeContext`` shapes the
    teaching language so the card matches the chart the user is looking at.
    """
    ctx = read_timeframes(market)
    # When averages are missing, lean on the engine trend so prose stays honest.
    if ctx.structure == "insufficient" and trend == "bearish":
        ctx = TimeframeContext(
            long_term="bearish", short_term=ctx.short_term, structure="aligned_bearish"
        )
    elif ctx.structure == "insufficient" and trend == "bullish":
        ctx = TimeframeContext(
            long_term="bullish", short_term=ctx.short_term, structure="aligned_bullish"
        )
    next_trigger = _next_trigger(market, strategy, levels, limits, ctx)
    return Narrative(
        verdict=_verdict(market, action, strategy, ctx, limits),
        summary=_summary(market, strategy, ctx),
        next_trigger=next_trigger,
        entry_condition=_entry_condition(market, strategy, levels, ctx),
        why=_why(market, action, strategy, score, levels, limits, ctx),
        positives=_positives(market, ctx, rules_matched, levels),
        risks=_risks(market, action, strategy, ctx, levels, limits),
    )
