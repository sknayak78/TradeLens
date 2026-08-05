"""Configuration for the TradeLens recommendation engine.

Every threshold used by :mod:`recommendation.engine` lives here so the rules can
be tuned without touching engine code.  Rules are declarative: each one
contributes ``points`` when its ``check`` returns True.  The maximum reachable
score is 100.

Only live, OHLCV-derived indicators are referenced (price, EMA20/50/200, RSI,
support, resistance).  Seeded VWAP / trend / average volume / day high are
deliberately not part of any rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import RecommendationInput


@dataclass(frozen=True)
class Rule:
    key: str
    label: str
    points: int
    check: Callable[[RecommendationInput], bool]


# ---------- Rule predicates ----------

def _price_above_ema20(m: RecommendationInput) -> bool:
    return m.ema20 is not None and m.price > m.ema20


def _price_above_ema50(m: RecommendationInput) -> bool:
    return m.ema50 is not None and m.price > m.ema50


def _price_above_ema200(m: RecommendationInput) -> bool:
    return m.ema200 is not None and m.price > m.ema200


def _ema_stack_bullish(m: RecommendationInput) -> bool:
    if m.ema20 is None or m.ema50 is None or m.ema200 is None:
        return False
    return m.ema20 > m.ema50 > m.ema200


def _rsi_in_healthy_zone(m: RecommendationInput) -> bool:
    return m.rsi is not None and RSI_HEALTHY_MIN <= m.rsi <= RSI_HEALTHY_MAX


def _room_to_resistance(m: RecommendationInput) -> bool:
    headroom = m.headroom_pct
    return headroom is not None and headroom >= MIN_HEADROOM_PCT


def _clear_of_support(m: RecommendationInput) -> bool:
    cushion = m.support_cushion_pct
    return cushion is not None and cushion >= MIN_SUPPORT_CUSHION_PCT


# ---------- RSI zones ----------

RSI_HEALTHY_MIN: float = 55.0
RSI_HEALTHY_MAX: float = 70.0
RSI_OVERBOUGHT: float = 80.0
RSI_OVERSOLD: float = 30.0


# ---------- Level geometry ----------

# Minimum distance to resistance for a fresh entry; below it the setup is a
# breakout candidate rather than a buy.
MIN_HEADROOM_PCT: float = 2.0
# Minimum distance above support before a long is considered "clear" of it.
MIN_SUPPORT_CUSHION_PCT: float = 1.0
# Stop sits just under support: stop_loss = support * STOP_SUPPORT_MULTIPLIER.
STOP_SUPPORT_MULTIPLIER: float = 0.99
# Second target extends past resistance by this share of the support-resistance
# band: target2 = resistance + SECOND_TARGET_BAND_SHARE * (resistance - support).
SECOND_TARGET_BAND_SHARE: float = 0.5
# Fresh entries whose reward:risk is below this become "Hold" or "Watch".
MIN_RISK_REWARD: float = 1.2


SCORING_RULES: list[Rule] = [
    Rule("price_above_ema20", "Price above EMA20", 15, _price_above_ema20),
    Rule("price_above_ema50", "Price above EMA50", 10, _price_above_ema50),
    Rule("price_above_ema200", "Price above EMA200", 15, _price_above_ema200),
    Rule("ema_stack_bullish", "EMA20 > EMA50 > EMA200", 20, _ema_stack_bullish),
    Rule("rsi_healthy", "RSI in 55-70 zone", 15, _rsi_in_healthy_zone),
    Rule("room_to_resistance", "At least 2% room to resistance", 15, _room_to_resistance),
    Rule("clear_of_support", "At least 1% above support", 10, _clear_of_support),
]

MAX_SCORE: int = sum(rule.points for rule in SCORING_RULES)  # 100


# ---------- Reward quality bands used by the plain-English narrative ----------

# Reward:risk at or above this reads as "generous" rather than merely acceptable.
GOOD_RISK_REWARD: float = 2.0
# Headroom at or above this reads as "plenty of room" to the next hurdle.
COMFORTABLE_HEADROOM_PCT: float = 6.0


# ---------- Conviction bands (inclusive lower bound) ----------

CONVICTION_BANDS: list[dict] = [
    {"min": 80, "label": "High"},
    {"min": 60, "label": "Medium"},
    {"min": 0, "label": "Low"},
]


# ---------- Actions ----------

#: The only answers the engine may give, strongest first.  Position management
#: (Hold, Add More, Book Profit, Exit) needs portfolio context the engine does
#: not have and belongs to a future Portfolio Advisor.
ACTIONS: tuple[str, ...] = ("Strong Buy", "Buy", "Watch", "Wait", "Avoid")


# ---------- Strategy ----------

#: How an entry would be taken, kept out of the action so the action stays a
#: pure decision.  "No Entry Yet" means there is no entry plan to describe.
STRATEGIES: tuple[str, ...] = (
    "Immediate Entry",
    "Pullback Entry",
    "Breakout Confirmation",
    "No Entry Yet",
)


# ---------- Action thresholds ----------

ACTION_STRONG_BUY_MIN_SCORE: int = 90
ACTION_BUY_MIN_SCORE: int = 80
# Also the floor a blocked entry must clear to stay a "Watch" rather than a "Wait".
ACTION_WATCH_MIN_SCORE: int = 60
ACTION_WAIT_MIN_SCORE: int = 40


# ---------- Confidence bands per action (inclusive, as a 0-1 fraction) ----------

# Confidence expresses how sure TradeLens is of its own call, not the odds of a
# profitable trade, so every action owns a band and 100% is unreachable by
# construction.
CONFIDENCE_BANDS: dict[str, tuple[float, float]] = {
    "Strong Buy": (0.90, 0.95),
    "Buy": (0.80, 0.90),
    "Watch": (0.60, 0.75),
    "Wait": (0.40, 0.60),
    "Avoid": (0.20, 0.40),
}

#: No recommendation may ever claim certainty.
CONFIDENCE_CEILING: float = 0.95


# ---------- Indicator labels for human-readable data-quality warnings ----------

INDICATOR_LABELS: dict[str, str] = {
    "ema20": "EMA20",
    "ema50": "EMA50",
    "ema200": "EMA200",
    "rsi": "RSI",
    "support": "support",
    "resistance": "resistance",
}


# ---------- Holding period per action ----------

# The expected duration of the trade *after* a valid entry, never a status such
# as "Wait": a trader planning an entry needs the horizon before they take it.
# Avoid carries the longest horizon because the trend has to repair itself first.
HOLDING_PERIODS: dict[str, str] = {
    "Strong Buy": "1-3 Months",
    "Buy": "1-3 Weeks",
    "Watch": "1-3 Weeks",
    "Wait": "1-3 Weeks",
    "Avoid": "1-3 Months",
}


# ---------- Who each action suits ----------

IDEAL_FOR: dict[str, str] = {
    "Strong Buy": (
        "Beginners who want a clean trend to follow with a clearly defined exit."
    ),
    "Buy": (
        "Traders who are comfortable entering a healthy trend and sizing the "
        "position modestly."
    ),
    "Watch": (
        "Patient traders happy to keep this on a shortlist and act only when the "
        "price comes to them."
    ),
    "Wait": (
        "Traders who would rather miss a move than pay a poor price; there is "
        "nothing to do here today."
    ),
    "Avoid": (
        "Nobody looking for a fresh position today, and least of all beginners."
    ),
}


# ---------- Beginner coaching per action ----------

BEGINNER_TIPS: dict[str, str] = {
    "Strong Buy": (
        "Even the best-looking setup can fail, so decide your exit price before "
        "you buy and never risk more than a small slice of your capital."
    ),
    "Buy": (
        "Buy in one go only if you are comfortable with the exit price; "
        "otherwise start small and add once the stock proves itself."
    ),
    "Watch": (
        "Chasing a stock that has already moved is the most common beginner "
        "mistake. Set an alert and let the price come to you."
    ),
    "Wait": (
        "Sitting on your hands is a position too. Missing a trade costs you "
        "nothing; a bad entry costs you money."
    ),
    "Avoid": (
        "A falling stock always looks cheap on the way down. Wait for buyers to "
        "show up before you try to catch it."
    ),
}
