"""Pydantic schemas for TradeLens API."""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, ConfigDict, Field


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

class TradeCreate(BaseModel):
    trade_date: datetime
    symbol: str = Field(..., min_length=1, max_length=32)
    entry_price: float = Field(..., gt=0)
    exit_price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    notes: str = ""


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trade_date: datetime
    symbol: str
    entry_price: float
    exit_price: float
    quantity: int
    notes: str
    pnl: float = 0.0
    side: Literal["LONG", "SHORT"] = "LONG"


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
    # How an entry would be taken.  Trading strategy is kept out of `action` so
    # the action stays a pure decision.
    strategy: Literal["Fresh Entry", "Pullback", "Breakout", "No Entry Yet"]
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
    symbol: str
    name: str
    price: float
    changePct: float
    score: int
    trend: Literal["bullish", "bearish", "neutral"]
    rsi: float
    ema20: float
    vwap: float
    volume: int
    sector: str
    support: float
    resistance: float
    aiInsight: str
    series: List[SeriesPoint]
    # Analysis fields
    strengthScore: int
    stars: int
    classification: str
    tradeSetup: str
    riskLevel: Literal["Low", "Medium", "High"]
    suggestedAction: str
    insight: str
    # Additive: absent only when live indicators are too sparse to score.
    recommendation: Optional[RecommendationOut] = None


class Ranking(MarketMetadata):
    """Row in the 'Today's Rankings' table."""
    rank: int
    symbol: str
    name: str
    price: float
    changePct: float
    strengthScore: int
    stars: int
    classification: str
    trend: Literal["bullish", "bearish", "neutral"]
    tradeSetup: str
    riskLevel: Literal["Low", "Medium", "High"]
    suggestedAction: str
    insight: str
    reason: str


class WatchlistAnalysis(MarketMetadata):
    """Watchlist row enriched with analysis for badges on the dashboard."""
    symbol: str
    name: str
    price: float
    rsi: float
    ema20: float
    vwap: float
    score: int
    trend: Literal["bullish", "bearish", "neutral"]
    changePct: float
    strengthScore: int
    stars: int
    tradeSetup: str
    riskLevel: Literal["Low", "Medium", "High"]
    suggestedAction: str
