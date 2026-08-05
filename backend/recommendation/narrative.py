"""Plain-English narrative for a recommendation.

Everything a trader reads is built here, from the same facts the engine scored,
so the explanation can never disagree with the action.  The wording is
deliberately human: it describes what buyers and sellers are doing and what it
means for a fresh position, rather than reciting indicator values.  An indicator
number appears only when it is a price a trader can act on (an entry, a stop, a
level to watch).

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
from .models import Action, RecommendationInput, TradeLevels, Trend

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


# ---------- Individual observations ----------

def _trend_observation(trend: Trend, rules_matched: Sequence[str]) -> str:
    if trend == "bullish":
        if "ema_stack_bullish" in rules_matched:
            return (
                "Buyers are firmly in control and the uptrend is intact on both "
                "the short and the long view."
            )
        return "Buyers are in control and the stock is trading in an uptrend."
    if trend == "bearish":
        return (
            "Sellers are in control and the stock is in a downtrend, so every "
            "bounce is likely to be sold into."
        )
    return (
        "Neither buyers nor sellers are in control, so the stock is drifting "
        "without a clear direction."
    )


def _momentum_observation(rsi: Optional[float]) -> Optional[str]:
    if rsi is None:
        return None
    if rsi >= RSI_OVERBOUGHT:
        return (
            "The stock has run up very quickly and is overdue a breather, which "
            "makes buying today an expensive way to join the move."
        )
    if RSI_HEALTHY_MIN <= rsi <= RSI_HEALTHY_MAX:
        return "Buying interest is steady without the move looking overheated."
    if rsi <= RSI_OVERSOLD:
        return (
            "Selling pressure is heavy and there is still no sign that buyers "
            "are stepping in."
        )
    return "Buying interest is lukewarm rather than convincing."


def _headroom_observation(market: RecommendationInput) -> Optional[str]:
    headroom = market.headroom_pct
    if headroom is None or market.resistance is None:
        return None
    if headroom <= 0:
        return (
            "The price has already reached the ceiling it struggled with last "
            f"time, near {_price(market.resistance)}."
        )
    if headroom < MIN_HEADROOM_PCT:
        return (
            "The stock is right underneath the ceiling it struggled with last "
            f"time, near {_price(market.resistance)}, so there is little room "
            "left before sellers reappear."
        )
    if headroom >= COMFORTABLE_HEADROOM_PCT:
        return (
            f"There is roughly {_pct(headroom)} of clear air before the stock "
            f"meets its next real hurdle around {_price(market.resistance)}."
        )
    return (
        f"There is about {_pct(headroom)} of room before the stock meets its "
        f"next hurdle around {_price(market.resistance)}."
    )


def _cushion_observation(market: RecommendationInput) -> Optional[str]:
    cushion = market.support_cushion_pct
    if cushion is None or market.support is None:
        return None
    if cushion < MIN_SUPPORT_CUSHION_PCT:
        return (
            "The price is sitting almost on top of the level buyers last "
            f"defended ({_price(market.support)}), which leaves very little "
            "margin for error."
        )
    return (
        "The price is comfortably above the level buyers last defended "
        f"({_price(market.support)}), so the downside can be measured rather "
        "than guessed."
    )


def _reward_observation(levels: Optional[TradeLevels]) -> Optional[str]:
    if levels is None:
        return None
    if levels.risk_reward >= GOOD_RISK_REWARD:
        return (
            f"The move being aimed at is worth about {levels.risk_reward:.1f} "
            "times what is being risked, which is a healthy trade-off."
        )
    if levels.risk_reward >= MIN_RISK_REWARD:
        return (
            f"The move being aimed at is worth about {levels.risk_reward:.1f} "
            "times what is being risked, which is acceptable but not generous."
        )
    return (
        "You would be risking almost as much as you stand to gain, which is not "
        "a trade worth taking."
    )


# ---------- Grouped explanations ----------

def _positives(
    market: RecommendationInput,
    trend: Trend,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
) -> List[str]:
    if trend == "bearish":
        # Room to the next hurdle and a cushion above support are only
        # encouraging while buyers are still in the picture; listing them under
        # a downtrend would read as an argument to buy.
        return []
    positives: List[str] = []
    if trend == "bullish":
        positives.append(_trend_observation(trend, rules_matched))
    elif trend == "neutral" and "price_above_ema200" in rules_matched:
        positives.append(
            "The stock is still above where it has traded over the past year, "
            "so the longer-term picture has not broken down."
        )

    if "rsi_healthy" in rules_matched:
        positives.append(
            "Buying interest is steady without the move looking overheated."
        )

    headroom = market.headroom_pct
    if headroom is not None and headroom >= MIN_HEADROOM_PCT:
        positives.append(_headroom_observation(market) or "")

    cushion = market.support_cushion_pct
    if cushion is not None and cushion >= MIN_SUPPORT_CUSHION_PCT:
        positives.append(_cushion_observation(market) or "")

    if levels is not None and levels.risk_reward >= MIN_RISK_REWARD:
        positives.append(_reward_observation(levels) or "")

    return [text for text in positives if text]


def _risks(
    market: RecommendationInput,
    trend: Trend,
    action: Action,
    levels: Optional[TradeLevels],
    limits: Limits,
) -> List[str]:
    risks: List[str] = []
    if trend == "bearish":
        risks.append(
            "The downtrend can continue far longer than it looks like it should, "
            "and buying into one is how beginners lose money fastest."
        )
    elif trend == "neutral":
        risks.append(
            "Without a clear trend the stock can swing both ways, so an entry "
            "here is closer to a coin toss than a plan."
        )

    if LIMIT_OVERBOUGHT in limits:
        risks.append(
            "After a run this sharp, even good news can be followed by a pullback "
            "that stops out a fresh position."
        )
    if market.rsi is not None and market.rsi <= RSI_OVERSOLD:
        risks.append(
            "Heavy selling is still in charge, and a stock this weak usually "
            "needs time to steady before it can rise again."
        )
    if LIMIT_THIN_HEADROOM in limits and market.resistance is not None:
        risks.append(
            "Sellers have turned this stock away at the level just overhead "
            f"({_price(market.resistance)}) before, so it can stall or reverse "
            "from here."
        )
    if LIMIT_POOR_RISK_REWARD in limits:
        risks.append(
            "The realistic upside is no bigger than the loss you would take if "
            "you are wrong."
        )
    if LIMIT_NO_LEVELS in limits:
        risks.append(
            "There is no reliable place to put an exit, so a position here could "
            "not be risk-managed properly."
        )
    if LIMIT_PARTIAL_DATA in limits:
        risks.append(
            "Part of the usual market history was unavailable, so this reading is "
            "less complete than normal."
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


def _why_not_stronger(action: Action, limits: Limits, score: int) -> Optional[str]:
    """State plainly what stopped the engine from being more bullish."""
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
            "It is not even a wait-and-see: until sellers lose control there is "
            "nothing here worth tracking."
        )
    if LIMIT_OVERBOUGHT in limits:
        return (
            "It is not a buy because the price has already stretched far ahead "
            "of itself, and paying up here gives away the best part of the move."
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
            "It is not a buy because the price is pressed against overhead "
            "resistance, so a breakout needs to be confirmed first."
        )
    if LIMIT_TREND_NOT_BULLISH in limits:
        return (
            "It is not a buy because the trend has not turned convincingly "
            "upwards yet."
        )
    if LIMIT_WEAK_EVIDENCE in limits:
        return (
            f"Only {score} of a possible 100 points of supporting evidence are "
            "in place, which is too little to justify a stronger call."
        )
    return None


def _why(
    market: RecommendationInput,
    trend: Trend,
    action: Action,
    score: int,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
    limits: Limits,
) -> List[str]:
    why: List[str] = [_trend_observation(trend, rules_matched)]

    momentum = _momentum_observation(market.rsi)
    if momentum:
        why.append(momentum)

    location = None if trend == "bearish" else _headroom_observation(market)
    if location:
        why.append(location)
    elif market.resistance is None or market.support is None:
        why.append(
            "The levels this stock usually respects could not be established, "
            "so there is no map for where to enter or exit."
        )

    if levels is not None and action in ("Strong Buy", "Buy"):
        reward = _reward_observation(levels)
        if reward:
            why.append(reward)

    not_stronger = _why_not_stronger(action, limits, score)
    if not_stronger:
        why.append(not_stronger)
    return why


# ---------- Verdict, summary, triggers ----------

def _verdict(
    market: RecommendationInput,
    trend: Trend,
    action: Action,
    limits: Limits,
) -> str:
    """One line a trader can act on without reading anything else."""
    if action == "Strong Buy":
        return "The setup supports a fresh entry today with clearly defined risk."
    if action == "Buy":
        return (
            "A fresh entry is reasonable here, provided the position is sized "
            "sensibly."
        )
    if action == "Watch":
        opening = (
            "The trend is healthy"
            if trend == "bullish"
            else "The stock is worth tracking"
        )
        if LIMIT_OVERBOUGHT in limits:
            return f"{opening}, but the price has run too far to buy today."
        if LIMIT_NO_LEVELS in limits:
            return (
                f"{opening}, but there is no dependable exit level yet, so a "
                "position cannot be protected."
            )
        if LIMIT_THIN_HEADROOM in limits and market.resistance is not None:
            return (
                f"{opening}, but the price is pressed against resistance, so "
                "today's entry offers limited upside."
            )
        if LIMIT_POOR_RISK_REWARD in limits:
            return (
                f"{opening}, but today's price leaves too little reward for the "
                "risk involved."
            )
        return f"{opening}, but today is not the day to start a position."
    if action == "Wait":
        return "Wait for a better entry before initiating a new position."
    return "This is not a stock to buy today."


def _summary(
    trend: Trend,
    action: Action,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
    next_trigger: str,
) -> str:
    opening = _trend_observation(trend, rules_matched)
    if action in ("Strong Buy", "Buy") and levels is not None:
        middle = (
            f"A position taken between {_price(levels.entry_min)} and "
            f"{_price(levels.entry_max)} can be protected with an exit below "
            f"{_price(levels.stop_loss)}, with the first target near "
            f"{_price(levels.target1)}."
        )
    elif action == "Watch":
        middle = (
            "The stock deserves attention, but today's price is not the place "
            "to start a position."
        )
    elif action == "Wait":
        middle = (
            "There is not enough evidence yet to justify putting money at risk."
        )
    else:
        middle = (
            "Buying weakness like this usually means adding to the loss before "
            "the stock recovers."
        )
    return f"{opening} {middle} {next_trigger}"


def _next_trigger(
    market: RecommendationInput,
    action: Action,
    levels: Optional[TradeLevels],
    limits: Limits,
) -> str:
    if action in ("Strong Buy", "Buy") and levels is not None:
        return (
            f"Watch the {_price(levels.stop_loss)} level: a daily close below it "
            "means the idea has failed, while a push through "
            f"{_price(levels.target1)} opens the way to "
            f"{_price(levels.target2)}."
        )
    if LIMIT_OVERBOUGHT in limits:
        if levels is not None:
            return (
                "Watch for the price to cool off and settle back into "
                f"{_price(levels.entry_min)}-{_price(levels.entry_max)}, which "
                "would offer a far safer entry."
            )
        return (
            "Watch for the price to cool off and steady for a few sessions "
            "before considering an entry."
        )
    if (
        action == "Watch"
        and LIMIT_THIN_HEADROOM in limits
        and market.resistance is not None
    ):
        return (
            "Watch for a daily close above "
            f"{_price(market.resistance)}: that would confirm the breakout and "
            "create a fresh entry."
        )
    if action == "Watch" and levels is not None:
        return (
            "Watch for a pullback into "
            f"{_price(levels.entry_min)}-{_price(levels.entry_max)} that holds, "
            "which would be the entry to act on."
        )
    if action in ("Watch", "Wait"):
        return (
            f"Watch for the price to steady above {_recent_average(market)} and "
            "for clear support to form before considering an entry."
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


def _entry_condition(
    market: RecommendationInput,
    action: Action,
    levels: Optional[TradeLevels],
    limits: Limits,
) -> str:
    """Legacy one-liner kept for v1.0 consumers; ``next_trigger`` supersedes it."""
    if action in ("Strong Buy", "Buy") and levels is not None:
        return (
            f"Consider entering between {_price(levels.entry_min)} and "
            f"{_price(levels.entry_max)}, and exit if the price closes below "
            f"{_price(levels.stop_loss)}."
        )
    if (
        action == "Watch"
        and LIMIT_THIN_HEADROOM in limits
        and market.resistance is not None
    ):
        return (
            "Wait for a daily close above "
            f"{_price(market.resistance)} before entering."
        )
    if action == "Watch" and levels is not None:
        return (
            "Wait for the price to pull back into "
            f"{_price(levels.entry_min)}-{_price(levels.entry_max)} and hold "
            "there."
        )
    if action in ("Watch", "Wait"):
        return (
            f"Wait for the price to steady above {_recent_average(market)} "
            "before considering an entry."
        )
    return "No trade: stay out until buyers take back control."


def build(
    market: RecommendationInput,
    trend: Trend,
    action: Action,
    score: int,
    rules_matched: Sequence[str],
    levels: Optional[TradeLevels],
    limits: Limits,
) -> Narrative:
    """Assemble every prose field for one recommendation."""
    next_trigger = _next_trigger(market, action, levels, limits)
    return Narrative(
        verdict=_verdict(market, trend, action, limits),
        summary=_summary(trend, action, rules_matched, levels, next_trigger),
        next_trigger=next_trigger,
        entry_condition=_entry_condition(market, action, levels, limits),
        why=_why(market, trend, action, score, rules_matched, levels, limits),
        positives=_positives(market, trend, rules_matched, levels),
        risks=_risks(market, trend, action, levels, limits),
    )
