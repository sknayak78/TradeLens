"""Typed inputs and outputs for the TradeLens recommendation engine.

``RecommendationInput`` carries only live, OHLCV-derived indicators.  Seeded
fields (VWAP, trend, average volume, day high) are intentionally absent so they
cannot leak into recommendation logic.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Mapping, Optional

Trend = Literal["bullish", "bearish", "neutral"]
#: The engine answers "should I open a position today?" and has no portfolio
#: context, so position-management verdicts (Hold, Add More, Book Profit, Exit)
#: belong to a future Portfolio Advisor and are deliberately absent here.
Action = Literal["Strong Buy", "Buy", "Watch", "Wait", "Avoid"]
#: How an entry would be taken.  Trading strategy is deliberately kept out of
#: ``Action`` so the action stays a pure decision.
Strategy = Literal[
    "Immediate Entry", "Pullback Entry", "Breakout Confirmation", "No Entry Yet"
]
Conviction = Literal["High", "Medium", "Low"]
#: "Partial" whenever any live indicator was unavailable, so consumers can flag
#: the recommendation instead of trusting a silently degraded one.
DataQuality = Literal["Complete", "Partial"]


def _optional_float(source: Mapping[str, Any], key: str) -> Optional[float]:
    """Read a usable float, treating anything non-computable as absent.

    Providers can emit NaN or infinity for an indicator they could not compute
    (an unfinished bar, too little history), and those values silently poison
    every comparison they touch, so they are read as missing.
    """
    value = source.get(key)
    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class RecommendationInput:
    """A single symbol's live indicator snapshot.

    ``price`` is required; every other indicator is optional so a degraded
    provider payload yields a lower-confidence recommendation instead of an
    error.
    """

    symbol: str
    price: float
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None
    rsi: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None

    #: Indicators that participate in the completeness/confidence calculation.
    OPTIONAL_FIELDS = ("ema20", "ema50", "ema200", "rsi", "support", "resistance")

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol must not be empty")
        if not math.isfinite(self.price):
            raise ValueError("price must be a finite number")
        if self.price <= 0:
            raise ValueError("price must be positive")
        # Non-computable indicators are absent indicators: keeping NaN here
        # would make every threshold comparison silently False and could reach
        # the API as a non-JSON-compliant number.
        for name in self.OPTIONAL_FIELDS:
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                object.__setattr__(self, name, None)

    @classmethod
    def from_snapshot(
        cls,
        stock: Mapping[str, Any],
        insight: Optional[Mapping[str, Any]] = None,
    ) -> "RecommendationInput":
        """Build an input from provider dictionaries, reading live keys only.

        ``stock`` supplies price and the EMA/RSI indicators; ``insight`` supplies
        support and resistance when they are served separately.  Support and
        resistance present on ``stock`` win, since that is the same payload the
        indicators were derived from.
        """
        levels: Dict[str, Any] = dict(insight or {})
        support = _optional_float(stock, "support")
        if support is None:
            support = _optional_float(levels, "support")
        resistance = _optional_float(stock, "resistance")
        if resistance is None:
            resistance = _optional_float(levels, "resistance")

        price = _optional_float(stock, "price")
        if price is None:
            raise ValueError("snapshot is missing a usable numeric price")

        return cls(
            symbol=str(stock["symbol"]).strip().upper(),
            price=price,
            ema20=_optional_float(stock, "ema20"),
            ema50=_optional_float(stock, "ema50"),
            ema200=_optional_float(stock, "ema200"),
            rsi=_optional_float(stock, "rsi"),
            support=support,
            resistance=resistance,
        )

    @property
    def has_valid_levels(self) -> bool:
        """True when support/resistance form a usable band around the price."""
        if self.support is None or self.resistance is None:
            return False
        if self.support <= 0 or self.resistance <= self.support:
            return False
        return self.support < self.price

    @property
    def headroom_pct(self) -> Optional[float]:
        """Distance from price up to resistance, in percent of price."""
        if self.resistance is None or self.resistance <= 0:
            return None
        return (self.resistance - self.price) / self.price * 100

    @property
    def support_cushion_pct(self) -> Optional[float]:
        """Distance from support up to price, in percent of price."""
        if self.support is None or self.support <= 0:
            return None
        return (self.price - self.support) / self.price * 100

    @property
    def missing_indicators(self) -> List[str]:
        """Names of the optional indicators the provider did not supply."""
        return [
            name for name in self.OPTIONAL_FIELDS if getattr(self, name) is None
        ]

    @property
    def completeness(self) -> float:
        """Fraction of optional indicators that are present."""
        present = sum(
            1 for name in self.OPTIONAL_FIELDS if getattr(self, name) is not None
        )
        return present / len(self.OPTIONAL_FIELDS)


@dataclass(frozen=True)
class TradeLevels:
    """Entry/exit geometry for a long setup.

    The entry is a zone rather than a single price: ``entry_min`` is the higher
    of EMA20 and support (the level a pullback should hold) and ``entry_max`` is
    the last price.  ``risk_reward`` is measured from the midpoint of the zone,
    the representative fill.
    """

    entry_min: float
    entry_max: float
    stop_loss: float
    target1: float
    target2: float
    risk_reward: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class Recommendation:
    """Deterministic recommendation derived from live indicators only.

    The decision fields a consumer should render are ``action``, ``verdict``,
    ``summary``, ``levels`` and ``next_trigger``; the remaining fields explain
    that decision or preserve the v1.0 contract.
    """

    symbol: str
    action: Action
    #: The shape of the entry, if any: immediate, on a pullback, or only once a
    #: breakout confirms.  Never folded into ``action``.
    strategy: Strategy
    #: One line a trader can act on without reading anything else.
    verdict: str
    #: Two or three plain-English sentences: the call, the catch, the next step.
    summary: str
    conviction: Conviction
    score: int
    trend: Trend
    #: TradeLens' confidence in its own call (0-1), never the odds of a profit
    #: and never 1.0.
    confidence: float
    data_quality: DataQuality
    #: Expected duration of the trade once a valid entry is taken.
    holding_period: str
    #: The single thing that has to happen before this call changes.
    next_trigger: str
    beginner_tip: str
    ideal_for: str
    #: Plain-language next step for a beginner, e.g. "Wait for a daily close
    #: above resistance 120.00 before entering."  Superseded by ``next_trigger``.
    entry_condition: str
    #: Deprecated alias of ``summary``, kept so v1.0 consumers keep rendering.
    rationale: str
    #: Why this call was made, including why it was not upgraded further.
    why: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    rules_matched: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    levels: Optional[TradeLevels] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
