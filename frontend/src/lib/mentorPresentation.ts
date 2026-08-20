import type { RecommendationLevels } from "@/types";

/** Branded product name for user-facing Mentor references. */
export const TRADELENS_MENTOR = "TradeLens Mentor";

/** Preferred minimum risk/reward — mirrors backend MIN_RISK_REWARD. */
export const PREFERRED_MIN_RISK_REWARD = 1.2;

export interface MarketContext {
  price?: number;
  ema20?: number;
  ema50?: number;
  ema200?: number;
  rsi?: number;
  support?: number;
  resistance?: number;
}

export interface HumanizedRule {
  key: string;
  title: string;
  status: string;
  values: { label: string; value: string }[];
  explanation: string;
}

export interface HumanizedWarning {
  key: string;
  title: string;
  summary: string;
  explanation: string;
  values: { label: string; value: string }[];
}

function money(value: number): string {
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function pct(value: number): string {
  return `${value.toFixed(1)}%`;
}

/** Format a TradeLens Mentor action label for display. */
export function formatMentorAction(action: string): string {
  return `${TRADELENS_MENTOR}: ${action}`;
}

/** Translate a matched rule key into novice-friendly copy with values. */
export function humanizeRule(
  ruleKey: string,
  context: MarketContext = {},
): HumanizedRule {
  const { price, ema20, ema50, ema200, rsi, support, resistance } = context;

  switch (ruleKey) {
    case "price_above_ema20": {
      const above = ema20 != null && price != null && price > ema20;
      const values = [
        ...(price != null ? [{ label: "Current Price", value: money(price) }] : []),
        ...(ema20 != null ? [{ label: "EMA20", value: money(ema20) }] : []),
      ];
      return {
        key: ruleKey,
        title: "Price vs EMA20",
        status: above ? "Above EMA20" : "Below EMA20",
        values,
        explanation: above
          ? "The current price is above its 20-day Exponential Moving Average, which suggests recent price momentum is stronger than the short-term average."
          : "The current price is below its 20-day Exponential Moving Average, which suggests recent price momentum is weaker than the average.",
      };
    }
    case "price_above_ema50": {
      const above = ema50 != null && price != null && price > ema50;
      const values = [
        ...(price != null ? [{ label: "Current Price", value: money(price) }] : []),
        ...(ema50 != null ? [{ label: "EMA50", value: money(ema50) }] : []),
      ];
      return {
        key: ruleKey,
        title: "Price vs EMA50",
        status: above ? "Above EMA50" : "Below EMA50",
        values,
        explanation: above
          ? "Price is trading above the 50-day average, a sign of medium-term strength."
          : "Price is below the 50-day average, suggesting medium-term momentum is soft.",
      };
    }
    case "price_above_ema200": {
      const above = ema200 != null && price != null && price > ema200;
      const values = [
        ...(price != null ? [{ label: "Current Price", value: money(price) }] : []),
        ...(ema200 != null ? [{ label: "EMA200", value: money(ema200) }] : []),
      ];
      return {
        key: ruleKey,
        title: "Price vs EMA200",
        status: above ? "Above EMA200" : "Below EMA200",
        values,
        explanation: above
          ? "Price is above the long-term 200-day average, indicating the broader trend is supportive."
          : "Price is below the 200-day average, a sign the long-term trend is not yet supportive.",
      };
    }
    case "ema_stack_bullish": {
      const stacked =
        ema20 != null &&
        ema50 != null &&
        ema200 != null &&
        ema20 > ema50 &&
        ema50 > ema200;
      const values = [
        ...(ema20 != null ? [{ label: "EMA20", value: money(ema20) }] : []),
        ...(ema50 != null ? [{ label: "EMA50", value: money(ema50) }] : []),
        ...(ema200 != null ? [{ label: "EMA200", value: money(ema200) }] : []),
      ];
      return {
        key: ruleKey,
        title: "EMA Stack",
        status: stacked ? "Bullish alignment" : "Not fully aligned",
        values,
        explanation: stacked
          ? "Short, medium, and long moving averages are stacked bullishly (EMA20 > EMA50 > EMA200), a classic sign of trend strength."
          : "Moving averages are not in a clean bullish stack, so trend confirmation is weaker.",
      };
    }
    case "rsi_healthy": {
      const healthy = rsi != null && rsi >= 55 && rsi <= 70;
      const values = rsi != null ? [{ label: "RSI", value: rsi.toFixed(1) }] : [];
      return {
        key: ruleKey,
        title: "RSI Momentum",
        status: healthy ? "Healthy zone (55–70)" : "Outside healthy zone",
        values,
        explanation: healthy
          ? "RSI sits in a constructive zone — momentum is positive without being overextended."
          : "RSI is outside the preferred 55–70 zone, so momentum may be too weak or too stretched.",
      };
    }
    case "room_to_resistance": {
      const headroom =
        resistance != null && price != null && resistance > price
          ? ((resistance - price) / price) * 100
          : null;
      const values = [
        ...(price != null ? [{ label: "Current Price", value: money(price) }] : []),
        ...(resistance != null ? [{ label: "Resistance", value: money(resistance) }] : []),
        ...(headroom != null ? [{ label: "Room to resistance", value: pct(headroom) }] : []),
      ];
      return {
        key: ruleKey,
        title: "Room to Resistance",
        status:
          headroom != null && headroom >= 2
            ? "Sufficient headroom"
            : "Limited headroom",
        values,
        explanation:
          headroom != null && headroom >= 2
            ? "There is enough room before the next resistance level, giving the setup space to work."
            : "Price is close to resistance with limited upside room before the next hurdle.",
      };
    }
    case "clear_of_support": {
      const cushion =
        support != null && price != null && price > support
          ? ((price - support) / support) * 100
          : null;
      const values = [
        ...(price != null ? [{ label: "Current Price", value: money(price) }] : []),
        ...(support != null ? [{ label: "Support", value: money(support) }] : []),
      ];
      return {
        key: ruleKey,
        title: "Clear of Support",
        status:
          cushion != null && cushion >= 1 ? "Clear of support" : "Near support",
        values,
        explanation:
          cushion != null && cushion >= 1
            ? "The current price is above the identified support level, providing some buffer before that support level is tested."
            : "Price is close to support with limited cushion — a break below could invalidate the setup.",
      };
    }
    default:
      return {
        key: ruleKey,
        title: ruleKey.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        status: "Matched",
        values: [],
        explanation: "This technical condition is present in the current setup.",
      };
  }
}

/** Translate an engine warning id into novice-friendly copy. */
export function humanizeWarning(
  warning: string,
  context: MarketContext = {},
  levels: RecommendationLevels | null = null,
): HumanizedWarning {
  if (warning.startsWith("partial_data:")) {
    const detail = warning.replace("partial_data:", "").trim();
    return {
      key: "partial_data",
      title: "Incomplete data",
      summary: "Some indicators were unavailable for this analysis.",
      explanation: detail,
      values: [],
    };
  }

  switch (warning) {
    case "risk_reward_below_minimum": {
      const values: { label: string; value: string }[] = [];
      if (levels) {
        const entryRef = (levels.entryMin + levels.entryMax) / 2;
        const estimatedRisk = entryRef - levels.stopLoss;
        const estimatedReward = levels.target1 - entryRef;
        values.push(
          { label: "Estimated Risk", value: money(Math.max(estimatedRisk, 0)) },
          { label: "Estimated Reward", value: money(Math.max(estimatedReward, 0)) },
          { label: "Risk / Reward", value: `1 : ${levels.riskReward.toFixed(2)}` },
          {
            label: "Preferred Minimum",
            value: `1 : ${PREFERRED_MIN_RISK_REWARD.toFixed(1)}`,
          },
        );
      }
      return {
        key: warning,
        title: "Risk / Reward",
        summary: "Risk–reward ratio is below the preferred minimum.",
        explanation:
          "The potential reward relative to the estimated downside risk does not meet the level preferred by TradeLens Mentor for this setup.",
        values,
      };
    }
    case "rsi_overbought": {
      const values =
        context.rsi != null ? [{ label: "RSI", value: context.rsi.toFixed(1) }] : [];
      return {
        key: warning,
        title: "RSI Overbought",
        summary: "RSI suggests the stock may be overextended.",
        explanation:
          "When RSI is very high, recent buying may have pushed price too far too fast — pullbacks become more likely.",
        values,
      };
    }
    case "rsi_oversold": {
      const values =
        context.rsi != null ? [{ label: "RSI", value: context.rsi.toFixed(1) }] : [];
      return {
        key: warning,
        title: "RSI Oversold",
        summary: "RSI suggests selling pressure has been heavy.",
        explanation:
          "Very low RSI can signal exhaustion, but a falling stock can stay oversold — context matters before acting.",
        values,
      };
    }
    case "price_at_or_above_resistance": {
      const values = [
        ...(context.price != null
          ? [{ label: "Current Price", value: money(context.price) }]
          : []),
        ...(context.resistance != null
          ? [{ label: "Resistance", value: money(context.resistance) }]
          : []),
      ];
      return {
        key: warning,
        title: "At or Above Resistance",
        summary: "Price is at or above the identified resistance level.",
        explanation:
          "Buying directly into resistance is risky — price often pauses or reverses at these levels.",
        values,
      };
    }
    case "no_usable_levels": {
      return {
        key: warning,
        title: "No Usable Levels",
        summary: "A clear entry plan could not be constructed.",
        explanation:
          "Without reliable support, resistance, and risk geometry, TradeLens Mentor cannot suggest specific entry and exit levels.",
        values: [],
      };
    }
    default:
      return {
        key: warning,
        title: warning.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        summary: warning.replace(/_/g, " "),
        explanation:
          "This condition affects how TradeLens Mentor evaluates the setup.",
        values: [],
      };
  }
}
