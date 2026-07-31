export type Trend = "bullish" | "bearish" | "neutral";

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

export interface Opportunity {
  symbol: string;
  name: string;
  score: number;
  trend: Trend;
  price: number;
  changePct: number;
  reason: string;
}

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
