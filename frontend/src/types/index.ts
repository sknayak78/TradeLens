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

export interface TradingSetup {
  strategy: RecommendationStrategy;
  trend: Trend;
  structureKey: string;
  plannedEntry: number | null;
  levels: RecommendationLevels | null;
  score: number;
}

export type SetupProgressStatus =
  | "awaiting_entry"
  | "in_entry_zone"
  | "ready"
  | "breakout_pending"
  | "breakout_holding"
  | "extended"
  | "invalidated"
  | "no_setup";

export interface SetupProgress {
  status: SetupProgressStatus;
  price: number;
  distanceToEntryPct: number | null;
  distanceToStopPct: number | null;
  distanceToTarget1Pct: number | null;
  nextEvent: string;
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
  /** Insight v2 — one trading principle this setup teaches. */
  mentorLesson: string;
  /** Insight v2 — what would invalidate the mentor's thesis. */
  whatWouldChangeMyView: string;
  why: string[];
  positives: string[];
  risks: string[];
  entryCondition: string;
  rationale: string;
  rulesMatched: string[];
  warnings: string[];
  levels: RecommendationLevels | null;
  /** Additive Mentor Engine fields. */
  setup?: TradingSetup | null;
  progress?: SetupProgress | null;
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
  /** ER-0021 — Mentor Engine action when available. */
  action?: RecommendationAction | null;
  /** ER-0021 — Mentor Engine strategy when available. */
  strategy?: RecommendationStrategy | null;
  tradeSetup: TradeSetup;
  riskLevel: RiskLevel;
  suggestedAction: SuggestedAction;
  insight: string;
  reason: string;
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

export interface Insight {
  symbol: string;
  trend: Trend;
  support: number;
  resistance: number;
  aiInsight: string;
  series: { t: string; v: number }[];
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
