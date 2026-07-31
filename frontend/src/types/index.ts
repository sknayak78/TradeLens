export type Trend = "bullish" | "bearish" | "neutral";
export type RiskLevel = "Low" | "Medium" | "High";
export type TradeSetup =
  | "Momentum"
  | "Breakout"
  | "Pullback"
  | "Trend Continuation"
  | "Consolidation";
export type SuggestedAction = "Watch" | "Buy on Breakout" | "Wait" | "Avoid";

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
