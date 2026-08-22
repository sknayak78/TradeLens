"""Pydantic schemas for TradeLens API."""
from datetime import datetime
from typing import Any, Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field


#: Reason attached to every deprecated legacy analysis field, so the note appears
#: once in the OpenAPI schema instead of being restated per model.
LEGACY_ANALYSIS_DEPRECATION = (
    "Deprecated: superseded by the `recommendation` block. Retained for "
    "backward compatibility and scheduled for removal once the UI reads "
    "`recommendation` exclusively."
)


def _legacy_field() -> Any:
    """Declare a legacy analysis field as deprecated in the published schema."""
    return Field(..., deprecated=True, description=LEGACY_ANALYSIS_DEPRECATION)


class MarketMetadata(BaseModel):
    provider: str
    cached: bool
    asOf: datetime
    marketStatus: Literal["OPEN", "PRE_OPEN", "CLOSED", "WEEKEND"]


# ---------- Watchlist ----------

class WatchlistCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    created_at: datetime


class WatchlistEnriched(BaseModel):
    """Watchlist row enriched with market data for the UI table."""
    symbol: str
    name: str
    price: float
    rsi: float
    ema20: float
    vwap: float
    score: int
    trend: Literal["bullish", "bearish", "neutral"]
    changePct: float


# ---------- Trades ----------

class MentorSnapshotOut(BaseModel):
    """Immutable Mentor recommendation captured when the trade was recorded."""

    action: Optional[str] = None
    strategy: Optional[str] = None
    entry_range_low: Optional[float] = None
    entry_range_high: Optional[float] = None
    actual_entry_price: Optional[float] = None
    planned_stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    risk_reward: Optional[float] = None
    holding_period: Optional[str] = None
    reason: Optional[str] = None
    captured_at: Optional[datetime] = None


class TradeCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: datetime = Field(..., description="Entry date for the trade.")
    symbol: str = Field(..., min_length=1, max_length=32)
    side: Literal["LONG", "SHORT"] = "LONG"
    entry_price: float = Field(..., gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    exit_date: Optional[datetime] = None
    quantity: int = Field(..., gt=0)
    notes: str = ""
    confirm_out_of_range: bool = False


class TradeUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_date: Optional[datetime] = None
    side: Optional[Literal["LONG", "SHORT"]] = None
    entry_price: Optional[float] = Field(default=None, gt=0)
    exit_price: Optional[float] = Field(default=None, gt=0)
    exit_date: Optional[datetime] = None
    quantity: Optional[int] = Field(default=None, gt=0)
    notes: Optional[str] = None
    status: Optional[Literal["OPEN", "CLOSED"]] = None
    confirm_out_of_range: bool = False


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_date: datetime
    symbol: str
    side: Literal["LONG", "SHORT"]
    entry_price: float
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    quantity: int
    notes: str
    status: Literal["OPEN", "CLOSED"] = "CLOSED"
    pnl: float = 0.0
    unrealized_pnl: Optional[float] = None
    current_price: Optional[float] = None
    holding_period_days: Optional[int] = None
    mentor_snapshot: Optional[MentorSnapshotOut] = None


# ---------- Settings ----------

class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    capital: float
    risk_per_trade: float
    preferred_timeframe: str


class SettingsUpdate(BaseModel):
    capital: Optional[float] = Field(default=None, gt=0)
    risk_per_trade: Optional[float] = Field(default=None, ge=0, le=100)
    preferred_timeframe: Optional[str] = Field(default=None, min_length=1, max_length=8)


# ---------- Market ----------

class IndexItem(BaseModel):
    name: str
    symbol: str
    value: float
    changePct: float


class TodaysFocusItem(BaseModel):
    key: Literal["bestSetup", "momentum", "breakout", "avoid"]
    label: str
    symbol: str
    name: str
    note: str
    changePct: float


class MarketSummary(BaseModel):
    indices: List[IndexItem]
    todaysFocus: List[TodaysFocusItem]
    status: Literal["open", "closed"] = "open"
    asOf: datetime
    provider: str
    cached: bool
    marketStatus: Literal["OPEN", "PRE_OPEN", "CLOSED", "WEEKEND"]


class Opportunity(BaseModel):
    symbol: str
    name: str
    score: int
    trend: Literal["bullish", "bearish", "neutral"]
    price: float
    changePct: float
    reason: str


class SeriesPoint(BaseModel):
    t: str
    v: float


class DayRangeOut(BaseModel):
    symbol: str
    date: str
    available: bool
    low: Optional[float] = None
    high: Optional[float] = None
    message: Optional[str] = None


class StockSummary(MarketMetadata):
    symbol: str
    name: str
    price: float
    changePct: float
    trend: Literal["bullish", "bearish", "neutral"]
    sector: str


class RecommendationLevels(BaseModel):
    """Long entry zone and exit geometry from the recommendation engine."""
    entryMin: float
    entryMax: float
    stopLoss: float
    target1: float
    target2: float
    riskReward: float


class RecommendationOut(BaseModel):
    """Recommendation derived from live indicators only.

    Additive: consumers that ignore this block see the unchanged contract.
    This block is the authoritative answer to "is this a good time to buy this
    stock today?"; the legacy `suggestedAction` / `insight` / `classification`
    fields on the response are retained for compatibility only.
    """
    # Position management (Hold, Add More, Book Profit, Exit) needs portfolio
    # context the engine does not have, so it is out of scope here.
    action: Literal["Strong Buy", "Buy", "Watch", "Wait", "Avoid"]
    # Parent trading thesis.  Drives action, levels, Watch Next and narrative
    # so one recommendation never carries two conflicting plans (ER-0016).
    # "Fresh Entry" was renamed to "Trend Continuation" — timing is not a strategy.
    strategy: Literal[
        "Trend Continuation",
        "Pullback",
        "Breakout",
        "Consolidation",
        "No Entry Yet",
    ]
    verdict: str
    summary: str
    conviction: Literal["High", "Medium", "Low"]
    score: int
    trend: Literal["bullish", "bearish", "neutral"]
    # TradeLens' confidence in its own call, not the odds of a profitable trade.
    confidence: float
    # "Partial" when any live indicator was missing; `warnings` says which.
    dataQuality: Literal["Complete", "Partial"]
    # Expected duration of the trade once a valid entry is taken.
    holdingPeriod: str
    nextTrigger: str
    beginnerTip: str
    idealFor: str
    why: List[str]
    positives: List[str]
    risks: List[str]
    # Superseded by `nextTrigger`; kept for v1.0 consumers.
    entryCondition: str
    # Deprecated alias of `summary`.
    rationale: str
    rulesMatched: List[str]
    warnings: List[str]
    levels: Optional[RecommendationLevels] = None


class StockDetail(MarketMetadata):
    """One stock, as the detail screen consumes it.

    `trend` and `score` are the Recommendation Engine's own values, so they can
    never disagree with the `recommendation` block below them.
    """
    symbol: str
    name: str
    price: float
    changePct: float
    score: int = Field(
        ..., description="Recommendation score (0-100). Mirrors `recommendation.score`."
    )
    trend: Literal["bullish", "bearish", "neutral"] = Field(
        ..., description="Recommendation trend. Mirrors `recommendation.trend`."
    )
    rsi: float
    ema20: float
    vwap: float = Field(
        ...,
        description=(
            "Rolling 20-session volume-weighted average price, recomputed from "
            "live bars."
        ),
    )
    volume: int
    sector: str
    support: float
    resistance: float
    aiInsight: str
    series: List[SeriesPoint]
    timeframe: str = "1W"
    timeframeLabel: str = "1 Week"
    timeframeFallback: bool = False
    # Legacy analysis fields — deprecated, never inputs to the engine.
    strengthScore: int = _legacy_field()
    stars: int = _legacy_field()
    classification: str = _legacy_field()
    tradeSetup: str = _legacy_field()
    riskLevel: Literal["Low", "Medium", "High"] = _legacy_field()
    suggestedAction: str = _legacy_field()
    insight: str = _legacy_field()
    # Additive: absent only when live indicators are too sparse to score.
    recommendation: Optional[RecommendationOut] = None


class Ranking(MarketMetadata):
    """Row in the 'Today's Rankings' table."""
    rank: int
    symbol: str
    name: str
    price: float
    changePct: float
    trend: Literal["bullish", "bearish", "neutral"] = Field(
        ..., description="Recommendation trend for this stock."
    )
    reason: str
    # Legacy analysis fields — deprecated, never inputs to the engine.
    strengthScore: int = _legacy_field()
    stars: int = _legacy_field()
    classification: str = _legacy_field()
    tradeSetup: str = _legacy_field()
    riskLevel: Literal["Low", "Medium", "High"] = _legacy_field()
    suggestedAction: str = _legacy_field()
    insight: str = _legacy_field()
    recommendation: Optional["RecommendationOut"] = Field(
        default=None,
        description="Authoritative Mentor recommendation for this featured row.",
    )


class OpportunitiesResponse(MarketMetadata):
    """Featured opportunity rows plus universe-wide Mentor action counts."""

    rankings: List[Ranking]
    actionCounts: dict[str, int] = Field(
        ...,
        description="Count of each Mentor action across all eligible candidates.",
    )


class WatchlistAnalysis(MarketMetadata):
    """Watchlist row enriched with analysis for badges on the dashboard."""
    symbol: str
    name: str
    price: float
    rsi: float
    ema20: float
    vwap: float
    score: int = Field(
        ..., description="Recommendation score (0-100) for this stock."
    )
    trend: Literal["bullish", "bearish", "neutral"] = Field(
        ..., description="Recommendation trend for this stock."
    )
    changePct: float
    # Legacy analysis fields — deprecated, never inputs to the engine.
    strengthScore: int = _legacy_field()
    stars: int = _legacy_field()
    tradeSetup: str = _legacy_field()
    riskLevel: Literal["Low", "Medium", "High"] = _legacy_field()
    suggestedAction: str = _legacy_field()
