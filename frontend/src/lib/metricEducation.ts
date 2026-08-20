import { TRADELENS_MENTOR } from "./mentorPresentation";

export type MetricId =
  | "rsi"
  | "ema20"
  | "ema50"
  | "support"
  | "resistance"
  | "headroom"
  | "riskReward";

export interface MetricContext {
  value?: number | null;
  price?: number | null;
  resistance?: number | null;
  support?: number | null;
  riskReward?: number | null;
}

export interface MetricHelpContent {
  title: string;
  what: string;
  meaning: string;
  usage: string;
}

function formatMoney(value: number): string {
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function finite(value: number | null | undefined): value is number {
  return value != null && Number.isFinite(value);
}

function rsiMeaning(value: number): string {
  if (value >= 70) {
    return `A reading of ${value.toFixed(1)} suggests strong recent momentum. Very high RSI can also mean the move is stretched — context matters.`;
  }
  if (value <= 30) {
    return `A reading of ${value.toFixed(1)} suggests weak recent momentum or heavy selling pressure. Oversold readings can persist in downtrends.`;
  }
  if (value >= 55 && value <= 70) {
    return `A reading of ${value.toFixed(1)} sits in a constructive zone — positive momentum without being extremely stretched.`;
  }
  return `A reading around ${value.toFixed(1)} indicates relatively neutral momentum on the 0–100 scale.`;
}

const STATIC: Record<MetricId, Omit<MetricHelpContent, "meaning">> = {
  rsi: {
    title: "RSI",
    what: "The Relative Strength Index (RSI) measures the strength of recent price movements on a 0–100 scale.",
    usage:
      "Use RSI to sense momentum, not as a standalone buy/sell trigger. Combine it with trend, support/resistance, and the TradeLens Mentor view.",
  },
  ema20: {
    title: "EMA20",
    what: "The 20-day Exponential Moving Average (EMA20) is a short-term average price that reacts quickly to recent moves.",
    usage:
      "Compare the current price to EMA20 to sense short-term strength. Price above EMA20 often suggests recent momentum is supportive; below can mean momentum is soft.",
  },
  ema50: {
    title: "EMA50",
    what: "The 50-day Exponential Moving Average (EMA50) reflects medium-term price direction.",
    usage:
      "EMA50 helps you see whether the stock is holding above a medium-term average. It is one piece of the picture — not a guarantee of future direction.",
  },
  support: {
    title: "Support",
    what: "Support is a price zone where buying interest has historically appeared, slowing or reversing declines.",
    usage:
      "Support helps you think about downside risk. A break below support can weaken the setup; holding above can provide a buffer — but levels are not guaranteed to hold.",
  },
  resistance: {
    title: "Resistance",
    what: "Resistance is a price zone where selling pressure has historically appeared, slowing or reversing advances.",
    usage:
      "Resistance helps you judge upside room. Buying directly into resistance can be risky; clearing resistance with volume can change the picture.",
  },
  headroom: {
    title: "Sufficient Headroom",
    what: "Headroom is the percentage distance from the current price up to the next resistance level.",
    usage:
      "More headroom can make a setup more attractive because there is space for price to move before the next hurdle. Thin headroom does not forbid a move — it means upside may be limited.",
  },
  riskReward: {
    title: "Risk / Reward",
    what: "Risk/reward compares the estimated downside (to a stop) with the potential upside (to a target).",
    usage: `TradeLens Mentor may flag setups when the ratio is below its preferred minimum. A stronger ratio does not guarantee profit — it helps you ask whether the trade is worth the risk.`,
  },
};

/** Build contextual help copy for a metric, using live values when available. */
export function buildMetricHelp(
  metric: MetricId,
  context: MetricContext = {},
): MetricHelpContent {
  const base = STATIC[metric];
  let meaning = "";

  switch (metric) {
    case "rsi":
      meaning = finite(context.value)
        ? rsiMeaning(context.value)
        : "RSI summarises recent momentum. Mid-range readings are neutral; extremes can signal strength or exhaustion — always read alongside trend and structure.";
      break;
    case "ema20":
      if (finite(context.value) && finite(context.price)) {
        const above = context.price > context.value;
        meaning = `Current price ${formatMoney(context.price)} is ${above ? "above" : "below"} EMA20 ${formatMoney(context.value)}, suggesting ${above ? "supportive" : "soft"} short-term momentum.`;
      } else if (finite(context.value)) {
        meaning = `EMA20 is ${formatMoney(context.value)}. Compare the current price to this average to sense short-term momentum.`;
      } else {
        meaning = base.usage;
      }
      break;
    case "ema50":
      if (finite(context.value) && finite(context.price)) {
        const above = context.price > context.value;
        meaning = `Current price ${formatMoney(context.price)} is ${above ? "above" : "below"} EMA50 ${formatMoney(context.value)}, a ${above ? "supportive" : "cautious"} medium-term signal.`;
      } else {
        meaning =
          "EMA50 reflects medium-term direction. Compare price to EMA50 alongside EMA20 and the broader trend.";
      }
      break;
    case "support":
      if (finite(context.value) && finite(context.price)) {
        const buffer = ((context.price - context.value) / context.value) * 100;
        meaning =
          buffer >= 0
            ? `Price ${formatMoney(context.price)} is ${buffer.toFixed(1)}% above support ${formatMoney(context.value)}, providing some cushion before that level is tested.`
            : `Price ${formatMoney(context.price)} is below support ${formatMoney(context.value)} — the level may now act as resistance unless reclaimed.`;
      } else if (finite(context.value)) {
        meaning = `Support is near ${formatMoney(context.value)}. Watch whether price holds above this zone.`;
      } else {
        meaning = base.usage;
      }
      break;
    case "resistance":
      if (finite(context.value) && finite(context.price)) {
        const room =
          context.value > context.price
            ? ((context.value - context.price) / context.price) * 100
            : 0;
        meaning =
          room > 0
            ? `Price ${formatMoney(context.price)} has about ${room.toFixed(1)}% room before resistance ${formatMoney(context.value)}.`
            : `Price ${formatMoney(context.price)} is at or above resistance ${formatMoney(context.value)} — upside may face selling pressure.`;
      } else if (finite(context.value)) {
        meaning = `Resistance is near ${formatMoney(context.value)}. Consider how much room price has before reaching it.`;
      } else {
        meaning = base.usage;
      }
      break;
    case "headroom":
      if (finite(context.price) && finite(context.resistance) && context.resistance > context.price) {
        const headroom = ((context.resistance - context.price) / context.price) * 100;
        meaning = `With price ${formatMoney(context.price)} and resistance ${formatMoney(context.resistance)}, headroom is about ${headroom.toFixed(1)}%. ${headroom >= 2 ? "This is generally considered sufficient room for the setup to work." : "This is relatively thin headroom — upside may be limited."}`;
      } else {
        meaning = base.usage;
      }
      break;
    case "riskReward":
      if (finite(context.riskReward)) {
        meaning = `The estimated risk/reward ratio is 1 : ${context.riskReward.toFixed(2)}. Ratios below TradeLens Mentor's preferred minimum suggest the potential reward may not justify the estimated risk.`;
      } else {
        meaning = base.usage;
      }
      break;
    default:
      meaning = base.usage;
  }

  return {
    title: base.title,
    what: base.what,
    meaning,
    usage: base.usage.replace("TradeLens Mentor", TRADELENS_MENTOR),
  };
}
