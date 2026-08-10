import type { Recommendation } from "@/types";
import type { StockDetail } from "@/services/marketService";
import {
  resolveChartSetup,
  resolveChartSuggestedAction,
  resolveRankingAction,
  resolveRankingSetup,
} from "./stockDetailAuthority";

function baseStock(
  overrides: Partial<StockDetail> & Pick<StockDetail, "suggestedAction" | "tradeSetup">
): StockDetail {
  return {
    symbol: "EICHERMOT",
    name: "Eicher Motors",
    price: 100,
    changePct: 0,
    score: 70,
    trend: "bullish",
    rsi: 55,
    ema20: 99,
    vwap: 99,
    volume: 1,
    sector: "Auto",
    support: 95,
    resistance: 105,
    aiInsight: "",
    series: [],
    strengthScore: 70,
    stars: 3,
    classification: "Good",
    riskLevel: "Medium",
    insight: "",
    recommendation: null,
    ...overrides,
  };
}

function recommendation(
  overrides: Partial<Recommendation> = {}
): Recommendation {
  return {
    action: "Watch",
    strategy: "Breakout",
    verdict: "Watch",
    summary: "summary",
    conviction: "Medium",
    score: 70,
    trend: "bullish",
    confidence: 0.7,
    dataQuality: "Complete",
    holdingPeriod: "swing",
    nextTrigger: "Watch for a daily close above 105",
    beginnerTip: "",
    idealFor: "",
    mentorLesson: "",
    whatWouldChangeMyView: "",
    why: [],
    positives: [],
    risks: [],
    entryCondition: "Wait for confirmation",
    rationale: "",
    rulesMatched: [],
    warnings: [],
    levels: null,
    setup: {
      strategy: "Breakout",
      trend: "bullish",
      structureKey: "k",
      plannedEntry: null,
      levels: null,
      score: 70,
    },
    progress: {
      status: "breakout_pending",
      price: 100,
      distanceToEntryPct: null,
      distanceToStopPct: null,
      distanceToTarget1Pct: null,
      nextEvent: "Watch for a daily close above 105",
    },
    ...overrides,
  };
}

describe("stockDetailAuthority (ER-0021)", () => {
  test("F: recommendation WATCH/BREAKOUT wins over legacy Buy on Breakout", () => {
    const stock = baseStock({
      suggestedAction: "Buy on Breakout",
      tradeSetup: "Breakout",
      recommendation: recommendation({
        action: "Watch",
        strategy: "Breakout",
      }),
    });

    expect(resolveChartSuggestedAction(stock)).toBe("Watch");
    expect(resolveChartSetup(stock)).toBe("Breakout");
    expect(resolveChartSuggestedAction(stock)).not.toBe("Buy on Breakout");
  });

  test("G: legacy fallback when recommendation is absent", () => {
    const stock = baseStock({
      suggestedAction: "Buy on Breakout",
      tradeSetup: "Breakout",
      recommendation: null,
    });

    expect(resolveChartSuggestedAction(stock)).toBe("Buy on Breakout");
    expect(resolveChartSetup(stock)).toBe("Breakout");
  });

  test("H/I conceptual shapes: Bharti / Eicher / Maruti / Tata", () => {
    const bharti = baseStock({
      symbol: "BHARTIARTL",
      suggestedAction: "Buy on Breakout",
      tradeSetup: "Breakout",
      recommendation: recommendation({
        action: "Watch",
        strategy: "Pullback",
        setup: {
          strategy: "Pullback",
          trend: "bullish",
          structureKey: "b",
          plannedEntry: 1958,
          levels: null,
          score: 80,
        },
      }),
    });
    expect(resolveChartSuggestedAction(bharti)).toBe("Watch");
    expect(resolveChartSetup(bharti)).toBe("Pullback");

    const eicher = baseStock({
      suggestedAction: "Buy on Breakout",
      tradeSetup: "Breakout",
      recommendation: recommendation({ action: "Watch", strategy: "Breakout" }),
    });
    expect(resolveChartSuggestedAction(eicher)).toBe("Watch");
    expect(resolveChartSetup(eicher)).toBe("Breakout");

    const maruti = baseStock({
      suggestedAction: "Watch",
      tradeSetup: "Breakout",
      recommendation: recommendation({ action: "Watch", strategy: "Breakout" }),
    });
    expect(resolveChartSuggestedAction(maruti)).toBe("Watch");
    expect(resolveChartSetup(maruti)).toBe("Breakout");

    const tata = baseStock({
      suggestedAction: "Avoid",
      tradeSetup: "Consolidation",
      recommendation: recommendation({
        action: "Avoid",
        strategy: "No Entry Yet",
        setup: {
          strategy: "No Entry Yet",
          trend: "bearish",
          structureKey: "t",
          plannedEntry: null,
          levels: null,
          score: 20,
        },
      }),
    });
    expect(resolveChartSuggestedAction(tata)).toBe("Avoid");
    expect(resolveChartSetup(tata)).toBe("No Entry Yet");
  });

  test("prefers setup.strategy when present", () => {
    const stock = baseStock({
      suggestedAction: "Watch",
      tradeSetup: "Momentum",
      recommendation: recommendation({
        action: "Watch",
        strategy: "Pullback",
        setup: {
          strategy: "Pullback",
          trend: "bullish",
          structureKey: "x",
          plannedEntry: 1,
          levels: null,
          score: 1,
        },
      }),
    });
    expect(resolveChartSetup(stock)).toBe("Pullback");
  });

  test("rankings: mentor Wait/Breakout wins over legacy Buy on Breakout / Trend Continuation", () => {
    const row = {
      action: "Wait" as const,
      strategy: "Breakout" as const,
      suggestedAction: "Buy on Breakout" as const,
      tradeSetup: "Trend Continuation" as const,
    };
    expect(resolveRankingAction(row)).toBe("Wait");
    expect(resolveRankingSetup(row)).toBe("Breakout");
    expect(resolveRankingAction(row)).not.toBe("Buy on Breakout");
    expect(resolveRankingSetup(row)).not.toBe("Trend Continuation");
  });

  test("rankings: fallback when action/strategy absent", () => {
    const row = {
      suggestedAction: "Buy on Breakout" as const,
      tradeSetup: "Trend Continuation" as const,
    };
    expect(resolveRankingAction(row)).toBe("Buy on Breakout");
    expect(resolveRankingSetup(row)).toBe("Trend Continuation");
  });

  test("rankings: INFY / Bharti / Eicher / Maruti / Tata authority shapes", () => {
    expect(
      resolveRankingSetup({
        strategy: "Breakout",
        action: "Wait",
        tradeSetup: "Trend Continuation",
        suggestedAction: "Buy on Breakout",
      })
    ).toBe("Breakout");
    expect(
      resolveRankingAction({
        strategy: "Breakout",
        action: "Wait",
        tradeSetup: "Trend Continuation",
        suggestedAction: "Buy on Breakout",
      })
    ).toBe("Wait");

    expect(
      resolveRankingSetup({
        strategy: "Pullback",
        action: "Watch",
        tradeSetup: "Breakout",
        suggestedAction: "Buy on Breakout",
      })
    ).toBe("Pullback");
    expect(
      resolveRankingAction({
        strategy: "Breakout",
        action: "Watch",
        tradeSetup: "Breakout",
        suggestedAction: "Buy on Breakout",
      })
    ).toBe("Watch");
    expect(
      resolveRankingSetup({
        strategy: "No Entry Yet",
        action: "Avoid",
        tradeSetup: "Consolidation",
        suggestedAction: "Avoid",
      })
    ).toBe("No Entry Yet");
  });
});
