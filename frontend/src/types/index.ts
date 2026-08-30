export type Trend = "bullish" | "bearish" | "neutral";
export type RiskLevel = "Low" | "Medium" | "High";
export type TradeSetup =
  | "Momentum"
  | "Breakout"
  | "Pullback"
  | "Trend Continuation"
  | "Consolidation";
export type SuggestedAction = "Watch" | "Buy on Breakout" | "Wait" | "Avoid";

export type RecommendationAction =
  | "Strong Buy"
  | "Buy"
  | "Watch"
  | "Wait"
  | "Avoid";
export type RecommendationStrategy =
  | "Trend Continuation"
  | "Pullback"
  | "Breakout"
  | "Consolidation"
  | "No Entry Yet";
export type Conviction = "High" | "Medium" | "Low";
export type DataQuality = "Complete" | "Partial";

export interface RecommendationLevels {
  entryMin: number;
  entryMax: number;
  stopLoss: number;
  target1: number;
  target2: number;
  riskReward: number;
}

/** The engine's answer to "is this a good time to buy this stock today?". */
export interface Recommendation {
  action: RecommendationAction;
  strategy: RecommendationStrategy;
  verdict: string;
  summary: string;
  conviction: Conviction;
  score: number;
  trend: Trend;
  /** TradeLens' confidence in its own call (0–1), not the odds of a profit. */
  confidence: number;
  dataQuality: DataQuality;
  holdingPeriod: string;
  nextTrigger: string;
  beginnerTip: string;
  idealFor: string;
  why: string[];
  positives: string[];
  risks: string[];
  entryCondition: string;
  rationale: string;
  rulesMatched: string[];
  warnings: string[];
  levels: RecommendationLevels | null;
}

export interface Stock {
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  score: number;
  trend: Trend;
  rsi: number;
  ema20: number;
  vwap: number;
  volume: number;
  sector: string;
}

export interface Ranking {
  rank: number;
  symbol: string;
  name: string;
  price: number;
  changePct: number;
  strengthScore: number;
  stars: number;
  classification: string;
  trend: Trend;
  tradeSetup: TradeSetup;
  riskLevel: RiskLevel;
  suggestedAction: SuggestedAction;
  insight: string;
  reason: string;
  recommendation?: Recommendation | null;
}

// Kept for legacy usage — Opportunity is now the Ranking payload.
export type Opportunity = Ranking;

export interface WatchItem {
  symbol: string;
  name: string;
  price: number;
  rsi: number;
  ema20: number;
  vwap: number;
  score: number;
  trend: Trend;
  changePct: number;
  strengthScore: number;
  stars: number;
  tradeSetup: TradeSetup;
  riskLevel: RiskLevel;
  suggestedAction: SuggestedAction;
}

export interface TodaysFocusItem {
  key: "bestSetup" | "momentum" | "breakout" | "avoid";
  label: string;
  symbol: string;
  name: string;
  note: string;
  changePct: number;
}

/**
 * One point of a stock price series. `v` is always the close (kept for the
 * line-chart fallback and existing consumers); `o`/`h`/`l`/`vol` are the
 * OHLCV fields exposed for candlestick rendering and are optional so older
 * backends or fallback ranges remain valid.
 */
export interface ChartSeriesPoint {
  t: string;
  v: number;
  o?: number | null;
  h?: number | null;
  l?: number | null;
  vol?: number | null;
  /** Optional per-point EMA overlays computed over backend lookback. */
  ema20?: number | null;
  ema50?: number | null;
  ema200?: number | null;
}

export interface Insight {
  symbol: string;
  trend: Trend;
  support: number;
  resistance: number;
  aiInsight: string;
  series: ChartSeriesPoint[];
}

export interface MarketSnapshot {
  name: string;
  symbol: string;
  value: number;
  changePct: number;
}

export interface Settings {
  theme: "dark" | "light";
  defaultTimeframe: string;
  refreshInterval: number;
  notifications: boolean;
  compactMode: boolean;
}
