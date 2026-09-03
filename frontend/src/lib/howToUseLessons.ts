/**
 * Case-study content model for the How to Use TradeLens Case Lab (ER-0043 v2).
 *
 * The concept-based quiz lessons were replaced by ten realistic case studies
 * ("case lab"). Each case embeds the concepts (trend, EMA, support/resistance,
 * risk/reward, entry discipline) inside a trading situation.
 *
 * Learner flow per case:
 *   OBSERVE → ANALYSE → FORM A VIEW → MAKE A DECISION → REVEAL MENTOR VIEW →
 *   UNDERSTAND THE REASONING → SEE WHAT HAPPENED → LEARN.
 *
 * The Mentor/outcome view must never be shown before the learner submits their
 * own decision. All scenario/chart data is deterministic educational example
 * data — nothing here queries a backend, and none of it is an investment
 * recommendation or a forecast. Scenario data is kept separate from rendering
 * so real market-data-backed cases can replace these later without a UI change.
 */

import { TRADELENS_MENTOR, PREFERRED_MIN_RISK_REWARD } from "./mentorPresentation";
import type { ChartSeriesPoint } from "@/types";
import type { ChartTimeframe } from "@/lib/chartAxisFormat";

/* ---------------------------------------------------------------------------
 * Shared decision vocabulary
 * ------------------------------------------------------------------------- */

/** The four-bucket decision scale used by the product and Guided Research. */
export const DECISION_ACTIONS = ["BUY", "WATCH", "WAIT", "AVOID"] as const;
export type DecisionAction = (typeof DECISION_ACTIONS)[number];

export const DECISION_LABELS: Record<DecisionAction, string> = {
  BUY: "Buy",
  WATCH: "Watch",
  WAIT: "Wait",
  AVOID: "Avoid",
};

export type Confidence = "Low" | "Medium" | "High";

export const CONFIDENCE_OPTIONS: Confidence[] = ["Low", "Medium", "High"];

/** Compatiible single-select option shape reused by small UI controls. */
export interface AnswerOption {
  id: string;
  label: string;
  hint?: string;
  preferred?: boolean;
}

export type Agreement = "agree" | "partial" | "differ";

/** Map a Mentor-style action label onto the Academy four-bucket scale. */
export function mentorDecisionBucket(action: string): DecisionAction {
  switch (action) {
    case "Strong Buy":
      return "BUY";
    case "Buy":
      return "BUY";
    case "Watch":
      return "WATCH";
    case "Wait":
      return "WAIT";
    case "Avoid":
      return "AVOID";
    default:
      return "AVOID";
  }
}

export function decisionAgreement(
  user: DecisionAction | null,
  mentor: DecisionAction | null,
): Agreement {
  if (user === null || mentor === null) return "partial";
  if (user === mentor) return "agree";
  if (user === "BUY" && mentor === "AVOID") return "differ";
  if (user === "AVOID" && mentor === "BUY") return "differ";
  return "partial";
}

/* ---------------------------------------------------------------------------
 * Case types
 * ------------------------------------------------------------------------- */

export type CaseId =
  | "case-01-trend-vs-trade"
  | "case-02-ema-bull-trap"
  | "case-03-falling-knife"
  | "case-04-breakout-no-headroom"
  | "case-05-great-rr-bad-trade"
  | "case-06-all-but-one-thing"
  | "case-07-buy-or-wait"
  | "case-08-stop-loss-test"
  | "case-09-was-mentor-better"
  | "case-10-you-are-mentor";

/** One row of revealed technical evidence (shown after the learner decides). */
export interface CaseEvidence {
  label: string;
  value: string;
  note: string;
  tone?: "bullish" | "bearish" | "neutral";
}

/** Deterministic chart for the situation — nothing queried from a backend. */
export interface CaseChart {
  timeframe: ChartTimeframe;
  support?: number | null;
  resistance?: number | null;
  candles: CandlesSpec;
}

/** Compact deterministic OHLCV spec, expanded into ChartSeriesPoint by a helper. */
export type CandlesSpec = Array<{
  t: string;
  o: number;
  h: number;
  l: number;
  v: number;
  vol: number;
}>;

export interface MentorView {
  action: DecisionAction;
  actionLabel: string;
  rationale: string;
  reasoning: string[];
  takeaway: string;
}

export interface CaseOutcomeStep {
  label: string;
  returnPct: number;
  maxFavourableExcursion: number;
  maxAdverseExcursion: number;
  targetReached: boolean;
  invalidationReached: boolean;
}

export interface CaseOutcome {
  decisionPointPrice: number;
  steps: CaseOutcomeStep[];
  narrative: string;
}

/** A single day in the Case 08 stop-loss mini-scenario. */
export interface StopLossDay {
  day: string;
  headline: string;
  detail: string;
  currentPrice: number;
  /** Choices the learner has that day. */
  choices: StopLossChoice[];
  /** Revealed only after the learner picks a choice that day. */
  resolution: {
    headline: string;
    detail: string;
    /** Educational framing of whether the chosen process held up. */
    processNote: string;
  };
}

export interface StopLossChoice {
  id: string;
  label: string;
  /** Whether this choice is the process-consistent one for the day. */
  preferred?: boolean;
  noteWhenChosen: string;
}

/** One field in the Case 10 "You Are the Mentor" plan assessment. */
export interface AssessmentField {
  key: string;
  label: string;
  options: AnswerOption[];
}

export type CaseInteraction =
  | { kind: "decision"; prompt: string }
  | { kind: "stopLoss"; prompt: string; days: StopLossDay[] }
  | { kind: "selfAssessment"; prompt: string; fields: AssessmentField[] };

export interface CaseStudy {
  id: CaseId;
  number: number;
  title: string;
  /** Short concept label shown on the card and shell (e.g. "Trend ≠ Trade"). */
  theme: string;
  summary: string;
  situation: string;
  chart?: CaseChart;
  interaction: CaseInteraction;
  /** Revealed after the learner submits their own call. */
  evidence: CaseEvidence[];
  mentorView: MentorView;
  outcome?: CaseOutcome;
  /** The takeaway/meta-lesson surfaced after everything is revealed. */
  takeaway: string;
  learnWhy: string[];
}

export type CaseKind = "decision" | "stopLoss" | "selfAssessment";

export function caseKind(c: CaseStudy): CaseKind {
  if (c.interaction.kind === "stopLoss") return "stopLoss";
  if (c.interaction.kind === "selfAssessment") return "selfAssessment";
  return "decision";
}

/* ---------------------------------------------------------------------------
 * Case data
 * ------------------------------------------------------------------------- */

export const CASES: CaseStudy[] = [
  /* ------------------------------------------------------------------ 01 */
  {
    id: "case-01-trend-vs-trade",
    number: 1,
    title: "The Perfect Trend That Wasn't a Trade",
    theme: "Trend ≠ Trade",
    summary:
      "A flawless uptrend with no entry. A great trend is not the same as a good trade right now.",
    situation:
      "CopperMine Ltd. is in a textbook uptrend — higher highs, higher lows, EMA20 above EMA50 above EMA200, and price holding above every average. It looks perfect. But the stock has now run straight up for eight consecutive sessions with no pullback, RSI is overbought at 78, and price sits just ₹2 below a well-tested resistance zone. Every long-term signal is bullish; the immediate entry is the problem.",
    chart: {
      timeframe: "3M",
      support: 152,
      resistance: 176,
      candles: buildFromCloses([
        [152, 154],
        [153, 155],
        [156, 158],
        [158, 159],
        [160, 162],
        [162, 164],
        [163, 161],
        [158, 159],
        [160, 162],
        [162, 165],
        [166, 168],
        [168, 167],
        [166, 169],
        [170, 172],
        [172, 171],
        [170, 173],
        [174, 175],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "The trend is beautiful. Do you buy here?",
    },
    evidence: [
      {
        label: "Trend",
        value: "Strong uptrend",
        note: "Higher highs and higher lows, price above all key averages.",
        tone: "bullish",
      },
      {
        label: "EMA structure",
        value: "Bullish stack",
        note: "EMA20 > EMA50 > EMA200 and price above all three.",
        tone: "bullish",
      },
      {
        label: "Momentum",
        value: "Overbought (RSI 78)",
        note: "Eight up-sessions with no pullback — the move is extended.",
        tone: "bearish",
      },
      {
        label: "Entry location",
        value: "Extended, at resistance",
        note: "No pullback has offered a clean risk point; price is jammed against resistance.",
        tone: "bearish",
      },
      {
        label: "Headroom",
        value: "Limited",
        note: "Only ~1% room to the tested resistance before any real upside.",
        tone: "bearish",
      },
    ],
    mentorView: {
      action: "WAIT",
      actionLabel: "Wait",
      rationale:
        "CopperMine's trend is outstanding — but a trade needs an entry, not just a direction. Chasing an extended price into a tested resistance with no pullback and an overbought RSI gives you poor risk and almost no headroom.",
      reasoning: [
        "The trend answers 'what direction' — it does not answer 'where to get in'.",
        "Buying the highest, most extended candle is the worst risk location in the whole uptrend.",
        "The disciplined move is to want this stock, and wait for it to come to you.",
      ],
      takeaway:
        "A great trend is not automatically a good trade. Separate 'the stock is good' from 'now is a good time to enter'.",
    },
    outcome: {
      decisionPointPrice: 175,
      steps: [
        {
          label: "+5 days",
          returnPct: -3.1,
          maxFavourableExcursion: 0.4,
          maxAdverseExcursion: -3.4,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -5.6,
          maxFavourableExcursion: 1.0,
          maxAdverseExcursion: -6.2,
          targetReached: false,
          invalidationReached: true,
        },
        {
          label: "+20 days",
          returnPct: -2.4,
          maxFavourableExcursion: 2.8,
          maxAdverseExcursion: -6.2,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "The overextended price pulled back hard — a buyer at the top would have been stopped out before the trend resumed months later. The trend was right; the entry was wrong.",
    },
    takeaway:
      "Always ask two questions separately: is the trend with me, and is this a good place to enter.",
    learnWhy: [
      "Trend tells you direction; it does not hand you a good entry.",
      "An extended, overbought price at resistance is a poor place to buy no matter how strong the trend.",
      "Patience that waits for a better entry is a skill, not a form of missing out.",
    ],
  },

  /* ------------------------------------------------------------------ 02 */
  {
    id: "case-02-ema-bull-trap",
    number: 2,
    title: "The EMA Bull Trap",
    theme: "Context over the signal",
    summary:
      "A bullish EMA cross that fires inside a downtrend at resistance. Signals need their bigger context.",
    situation:
      "Vidhan Motors has been in a steady downtrend for three months, printing a descending series of lower highs and lower lows below EMA200. This week EMA20 crossed back above EMA50 and RSI recovered to 52 — a classic 'moving-average bullish cross' signal. Price also reclaimed EMA20. Many traders would call it a fresh bull move. But the cross happened right at the underside of a major resistance where every prior bounce has failed.",
    chart: {
      timeframe: "3M",
      support: 88,
      resistance: 103,
      candles: buildFromCloses([
        [104, 103],
        [102, 101],
        [100, 99],
        [97, 98],
        [96, 95],
        [94, 93],
        [92, 93],
        [95, 96],
        [97, 96],
        [95, 94],
        [92, 91],
        [90, 89],
        [88, 90],
        [92, 93],
        [95, 94],
        [96, 95],
        [94, 93],
        [95, 96],
        [98, 99],
        [100, 101],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "The EMA cross fired. Do you buy the reversal?",
    },
    evidence: [
      {
        label: "Primary trend",
        value: "Downtrend",
        note: "Lower highs and lower lows; price below EMA200 for three months.",
        tone: "bearish",
      },
      {
        label: "EMA cross",
        value: "Bullish EMA20>50 cross",
        note: "A real short-term crossover — but against the bigger trend.",
        tone: "neutral",
      },
      {
        label: "Resistance",
        value: "Under resistance (~₹103)",
        note: "The cross happened at the bottom of a resistance that has held every bounce.",
        tone: "bearish",
      },
      {
        label: "Momentum",
        value: "Neutral RSI 52",
        note: "A mild recovery, not yet confirmatory of a durable reversal.",
        tone: "neutral",
      },
    ],
    mentorView: {
      action: "AVOID",
      actionLabel: "Avoid",
      rationale:
        "A short-term EMA cross against a three-month downtrend, into the same resistance that has rejected every bounce, is a low-probability counter-trend signal — the classic bull trap. The averages are giving you a signal, but the structure is saying no.",
      reasoning: [
        "Signals need context: a bullish cross matters most when it lines up with the primary trend.",
        "Reversals are hardest to trade at the first bounce off a down-move — the market usually tests it again.",
        "Avoiding a counter-trend signal is a valid, disciplined decision.",
      ],
      takeaway:
        "Read a moving-average signal inside its structure, not in isolation. A signal against the primary trend is a trap until proven otherwise.",
    },
    outcome: {
      decisionPointPrice: 99,
      steps: [
        {
          label: "+5 days",
          returnPct: 1.2,
          maxFavourableExcursion: 2.1,
          maxAdverseExcursion: -1.0,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -3.0,
          maxFavourableExcursion: 2.6,
          maxAdverseExcursion: -3.8,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: -8.1,
          maxFavourableExcursion: 3.0,
          maxAdverseExcursion: -8.4,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "The cross lured early buyers in, then the stock turned back down through it and fell far below the previous lows. Anyone who traded the reversal against the trend paid the price.",
    },
    takeaway:
      "A signal that aligns with the primary trend is far more reliable than one fighting it.",
    learnWhy: [
      "A moving-average cross is context, never a standalone reason to trade.",
      "Trading a bullish signal against a clear downtrend is chasing a trap.",
      "The structure (trend + resistance) outranks the freshness of a crossover.",
    ],
  },

  /* ------------------------------------------------------------------ 03 */
  {
    id: "case-03-falling-knife",
    number: 3,
    title: "Buy the Dip — or Catch the Falling Knife?",
    theme: "Wait for the base",
    summary:
      "A stock that's down 25% looks cheap — but there's no support and the sellers are still in control.",
    situation:
      "AgroNova has fallen 25% from its high in a little over a month, and today it's down another 4% on heavy volume. New traders see a 'cheap' stock and want to buy the dip. But the stock is still printing lower lows with no base, no floor of support has formed yet, and volume confirms the selling. Buying here is trying to catch a falling knife — the price may keep falling before any support appears.",
    chart: {
      timeframe: "3M",
      support: null,
      resistance: 84,
      candles: buildFromCloses([
        [112, 110],
        [108, 106],
        [104, 105],
        [103, 100],
        [98, 96],
        [94, 92],
        [91, 93],
        [95, 92],
        [90, 88],
        [87, 85],
        [84, 86],
        [88, 85],
        [83, 81],
        [80, 78],
        [77, 76],
        [75, 74],
        [73, 72],
        [71, 70],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "It's down 25% and 'cheap'. Do you buy the dip here?",
    },
    evidence: [
      {
        label: "Structure",
        value: "Lower lows",
        note: "Every bounce has failed and price keeps making new lows — no base yet.",
        tone: "bearish",
      },
      {
        label: "Support",
        value: "None formed",
        note: "There is no tested floor; support has not had time to build.",
        tone: "bearish",
      },
      {
        label: "Volume",
        value: "Heavy on the way down",
        note: "Distribution volume confirms sellers are still in control.",
        tone: "bearish",
      },
      {
        label: "Trend",
        value: "Downtrend",
        note: "Below the falling EMA20 and far below EMA200.",
        tone: "bearish",
      },
    ],
    mentorView: {
      action: "WAIT",
      actionLabel: "Wait",
      rationale:
        "A big decline alone is not a reason to buy. AgroNova has no base, no tested support, and sellers still controlling the tape. Waiting for the first sign of a floor — not buying into free-fall — is the disciplined call.",
      reasoning: [
        "'Cheap' is not a trade. A falling stock can stay cheap for a long time.",
        "You cannot catch a knife safely before support has actually formed.",
        "A base (higher low / sideways range) is what gives a dip trade a floor to rest on.",
      ],
      takeaway:
        "Don't average into free-fall. Let the stock build a base and a support level before you call a dip worth buying.",
    },
    outcome: {
      decisionPointPrice: 72,
      steps: [
        {
          label: "+5 days",
          returnPct: -4.8,
          maxFavourableExcursion: 0.6,
          maxAdverseExcursion: -5.2,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -3.2,
          maxFavourableExcursion: 2.2,
          maxAdverseExcursion: -5.6,
          targetReached: false,
          invalidationReached: true,
        },
        {
          label: "+20 days",
          returnPct: 3.9,
          maxFavourableExcursion: 5.0,
          maxAdverseExcursion: -5.6,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "Price fell further, then finally built a base and recovered. A buyer at the early 'dip' suffered a deep drawdown; the patient buyer who waited for the base paid a much better price.",
    },
    takeaway:
      "A dip is only a dip once support holds. Before that, it's a falling knife.",
    learnWhy: [
      "A large decline does not make a stock cheap enough to buy.",
      "A base and a tested support level are what let you call a low-risk 'dip'.",
      "Patience that waits for the floor is discipline, not hesitation.",
    ],
  },

  /* ------------------------------------------------------------------ 04 */
  {
    id: "case-04-breakout-no-headroom",
    number: 4,
    title: "The Breakout With No Headroom",
    theme: "Headroom & risk/reward",
    summary:
      "A genuine volume breakout — but a heavy ceiling two percent higher kills the risk/reward.",
    situation:
      "SteelForge just broke above ₹120 resistance on strong volume — a textbook breakout with a big up-day. Momentum traders get excited. But directly above sits a very thick, long-serving resistance shelf at ₹123 that has capped this stock for over a year. That leaves only ~2.5% of room before the ceiling, while the stop back below the breakout level is ~5%. The breakout is real; the risk/reward and headroom are not.",
    chart: {
      timeframe: "3M",
      support: 114,
      resistance: 123,
      candles: buildFromCloses([
        [110, 112],
        [113, 115],
        [116, 117],
        [118, 119],
        [120, 121],
        [121, 120],
        [119, 121],
        [122, 123],
        [123, 122],
        [121, 120],
        [119, 118],
        [117, 119],
        [120, 121],
        [122, 122],
        [121, 120],
        [119, 118],
        [118, 119],
        [120, 121],
        [122, 124],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "Clean breakout on volume. Do you buy it?",
    },
    evidence: [
      {
        label: "Breakout",
        value: "Genuine, on volume",
        note: "A real break above ₹120 with volume support — the signal itself is valid.",
        tone: "bullish",
      },
      {
        label: "Headroom",
        value: "~2.5% to the ceiling",
        note: "A heavy ₹123 shelf sits almost immediately above — almost no room.",
        tone: "bearish",
      },
      {
        label: "Risk / reward",
        value: "Poor (≈ 1 : 0.5)",
        note: "Stop ~5% below vs. target ~2.5% above — more risk than reward.",
        tone: "bearish",
      },
      {
        label: "Location",
        value: "Between two levels",
        note: "Bought above support but with upside immediately capped.",
        tone: "neutral",
      },
    ],
    mentorView: {
      action: "WAIT",
      actionLabel: "Wait",
      rationale:
        "The breakout is legitimate, but a trade is about risk and reward, not just catching the signal. With a heavy ceiling barely 2.5% away and a stop 5% below, this setup offers about 1 : 0.5 — you risk more than you stand to gain.",
      reasoning: [
        "A breakout needs headroom to be worth taking.",
        "Thin headroom plus a wide stop means the risk/reward is upside-down.",
        "Waiting (or avoiding) is right because the geometry of the trade is poor, even though the signal fired.",
      ],
      takeaway:
        "Always weigh headroom against the stop distance. A great signal with no room is a poor trade.",
    },
    outcome: {
      decisionPointPrice: 122,
      steps: [
        {
          label: "+5 days",
          returnPct: 1.1,
          maxFavourableExcursion: 2.0,
          maxAdverseExcursion: -1.4,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -1.8,
          maxFavourableExcursion: 2.3,
          maxAdverseExcursion: -3.1,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: -4.9,
          maxFavourableExcursion: 2.5,
          maxAdverseExcursion: -5.3,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "Price stalled right under the ₹123 ceiling and rolled over, stopping out late breakout chasers. The signal was correct; the room to make money was never there.",
    },
    takeaway:
      "A breakout with no headroom is a breakout with no payoff. Let the geometry decide.",
    learnWhy: [
      "Headroom is the space the price has to move in your favour before the next hurdle.",
      "Risk/reward should compare the stop distance to the actual room to the next resistance.",
      "A good signal does not override a bad risk/reward.",
    ],
  },

  /* ------------------------------------------------------------------ 05 */
  {
    id: "case-05-great-rr-bad-trade",
    number: 5,
    title: "Great Risk/Reward. Bad Trade?",
    theme: "Edge, not just ratio",
    summary:
      "A superb 1:3 setup in a directionless, low-volume market with no reason to act. The ratio isn't enough.",
    situation:
      "A trader has drawn a setup with genuinely excellent numbers: entry ₹90, a tight stop at ₹87 (only 3.3% risk), and a target at ₹99 (10% reward) — a 1:3 risk/reward. It looks like a gift. The problem: the stock is in a sideways, low-volume range with no trending structure, no breakout, and no catalyst. The ratio is mathematically great, but there is no edge — no reason this direction wins out over the other.",
    chart: {
      timeframe: "3M",
      support: 87,
      resistance: 92,
      candles: buildFromCloses([
        [89, 90],
        [91, 90],
        [89, 88],
        [88, 89],
        [90, 91],
        [92, 91],
        [90, 89],
        [88, 87],
        [87, 88],
        [89, 90],
        [91, 90],
        [89, 88],
        [88, 89],
        [90, 91],
        [91, 90],
        [89, 88],
        [88, 89],
        [90, 91],
        [92, 91],
        [90, 89],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "The numbers are 1:3. Do you take it?",
    },
    evidence: [
      {
        label: "Risk / reward",
        value: "1 : 3",
        note: "Mathematically attractive — more to gain than to risk.",
        tone: "bullish",
      },
      {
        label: "Market structure",
        value: "Sideways range",
        note: "No trend, no breakout — price is chopping between ₹87 and ₹92.",
        tone: "bearish",
      },
      {
        label: "Volume",
        value: "Low, contracting",
        note: "No participation behind the move — nothing to confirm direction.",
        tone: "bearish",
      },
      {
        label: "Edge",
        value: "None defined",
        note: "A single nice ratio is not a reason the trade wins.",
        tone: "bearish",
      },
    ],
    mentorView: {
      action: "AVOID",
      actionLabel: "Avoid",
      rationale:
        "A 1:3 ratio describes the geometry of a trade, not whether the trade has a reason to exist. In a low-volume, directionless range there is no edge — the favourable ratio is an attractive wrapper around a random bet.",
      reasoning: [
        "Risk/reward is a filter, not a thesis. You still need a reason the price goes to your target.",
        "In a sideways market both directions are coin flips; a coin flip with good odds is still a coin flip.",
        "The disciplined move is to stand aside until structure and volume give you an edge.",
      ],
      takeaway:
        "Great risk/reward on a trade with no edge is not a trade — it's a spreadsheet with hopes.",
    },
    outcome: {
      decisionPointPrice: 90,
      steps: [
        {
          label: "+5 days",
          returnPct: -0.8,
          maxFavourableExcursion: 1.0,
          maxAdverseExcursion: -1.2,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -1.5,
          maxFavourableExcursion: 1.4,
          maxAdverseExcursion: -2.2,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: -3.3,
          maxFavourableExcursion: 1.6,
          maxAdverseExcursion: -3.6,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "The chop continued until the stock drifted down and finally tripped the stop. The appealing 1:3 ratio never had any structure behind it to reach the far target.",
    },
    takeaway:
      "Risk/reward tells you if the trade is worth the size — it does not tell you if the trade is worth taking at all.",
    learnWhy: [
      "A favourable risk/reward is necessary but never sufficient.",
      "You need an edge: structure, trend, or a catalyst — not just a good-looking ratio.",
      "Avoiding a coin-flip-with-nice-odds is a disciplined decision.",
    ],
  },

  /* ------------------------------------------------------------------ 06 */
  {
    id: "case-06-all-but-one-thing",
    number: 6,
    title: "Everything Looks Good — Except One Thing",
    theme: "The missing discipline check",
    summary:
      "Trend, averages, momentum all line up. The single missing piece is a clean risk location.",
    situation:
      "SwiftAuto checks almost every box: an uptrend, a bullish EMA stack, healthy RSI, volume supporting the advance, and a clearly defined support level below. And yet, as you zoom out for the one last check — trade location — you see price is already sitting right at the top of the recent range, extended after a fast leg up, with the nearest strong support far below. Every ingredient of a good setup is there except one: a clean, low-risk place to enter.",
    chart: {
      timeframe: "3M",
      support: 40,
      resistance: 47,
      candles: buildFromCloses([
        [36, 37],
        [38, 39],
        [40, 41],
        [42, 41],
        [40, 42],
        [43, 44],
        [45, 44],
        [43, 45],
        [46, 47],
        [47, 46],
        [45, 44],
        [43, 44],
        [45, 46],
        [46, 45],
        [44, 46],
        [47, 47],
        [46, 45],
        [47, 48],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "Five of six checks pass. Do you enter here?",
    },
    evidence: [
      {
        label: "Trend",
        value: "Uptrend",
        note: "Higher highs with a constructive pullback base.",
        tone: "bullish",
      },
      {
        label: "EMA stack",
        value: "Bullish alignment",
        note: "EMA20 > EMA50 > EMA200, price holding above.",
        tone: "bullish",
      },
      {
        label: "Momentum",
        value: "Healthy",
        note: "RSI in a constructive zone, volume confirming.",
        tone: "bullish",
      },
      {
        label: "Support",
        value: "Defined below (₹40)",
        note: "A clear level exists — but it is far below an extended price.",
        tone: "neutral",
      },
      {
        label: "Entry location",
        value: "Extended, at the top",
        note: "The one missing piece: price is far from support, right at the range top.",
        tone: "bearish",
      },
    ],
    mentorView: {
      action: "WAIT",
      actionLabel: "Wait",
      rationale:
        "This is the case where everything is right except the price you'd pay. Buying an extended candle at the top of the range, far from the nearest support, means a wide stop and a poor risk/reward — the one discipline check that overrides the others.",
      reasoning: [
        "A great setup at the wrong price is a bad trade.",
        "Your stop distance is set by where support is; the farther the support, the more you risk per share.",
        "Every other signal being good doesn't fix a poor entry location.",
      ],
      takeaway:
        "No matter how many checks pass, a bad entry location is the one thing that can sink the whole trade.",
    },
    outcome: {
      decisionPointPrice: 47,
      steps: [
        {
          label: "+5 days",
          returnPct: -2.0,
          maxFavourableExcursion: 1.2,
          maxAdverseExcursion: -2.4,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: -3.6,
          maxFavourableExcursion: 1.8,
          maxAdverseExcursion: -4.0,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: 1.4,
          maxFavourableExcursion: 3.6,
          maxAdverseExcursion: -4.0,
          targetReached: false,
          invalidationReached: false,
        },
      ],
      narrative:
        "Price stalled at the top, pulled back hard and only later recovered. The trader who waited for the pullback toward support got a far better risk/reward than the one who bought the extension.",
    },
    takeaway:
      "Run every check — but the entry-location check is the one you cannot skip.",
    learnWhy: [
      "A good setup at a bad price is not a good trade.",
      "Trade location (entry vs. support) sets your risk per share.",
      "One skipped discipline check can undo five that passed.",
    ],
  },

  /* ------------------------------------------------------------------ 07 */
  {
    id: "case-07-buy-or-wait",
    number: 7,
    title: "BUY or WAIT?",
    theme: "Full read, your call first",
    summary:
      "A complete, moderately-supportive setup. Commit to your own call before the Mentor reveals anything.",
    situation:
      "Here is a full picture. NorthGate Bank has a rising trend with higher lows, price above EMA20 and EMA50, a clean support at ₹210 and resistance at ₹228, and price now at ₹218 with a plan that clears the preferred minimum risk/reward. RSI is constructive-rounded at ~60. Everything is supportive but not screaming. The honest question: is this a BUY right now, or a WAIT for a better entry near support? Your call comes first — the Mentor's view stays hidden until you commit.",
    chart: {
      timeframe: "3M",
      support: 210,
      resistance: 228,
      candles: buildFromCloses([
        [204, 206],
        [207, 209],
        [210, 208],
        [209, 211],
        [212, 213],
        [214, 212],
        [211, 213],
        [215, 216],
        [217, 218],
        [219, 218],
        [217, 219],
        [220, 221],
        [222, 220],
        [219, 221],
        [223, 224],
        [225, 224],
        [223, 225],
        [226, 226],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "Form your own view before revealing the Mentor. What do you do?",
    },
    evidence: [
      {
        label: "Trend",
        value: "Uptrend",
        note: "Higher lows, price above the averages and holding.",
        tone: "bullish",
      },
      {
        label: "EMA structure",
        value: "Supportive",
        note: "Above EMA20 and EMA50 with a constructive order.",
        tone: "bullish",
      },
      {
        label: "Support / resistance",
        value: "₹210 / ₹228",
        note: "A defined floor and ceiling with price mid-zone at ₹218.",
        tone: "neutral",
      },
      {
        label: "Risk / reward",
        value: `≥ 1 : ${PREFERRED_MIN_RISK_REWARD}`,
        note: "The plan clears the preferred minimum from ₹218.",
        tone: "bullish",
      },
      {
        label: "Momentum",
        value: "Constructive",
        note: "RSI ~60 — positive but not overextended.",
        tone: "bullish",
      },
    ],
    mentorView: {
      action: "WATCH",
      actionLabel: "Watch",
      rationale:
        "NorthGate is a genuinely balanced setup: everything is constructive, yet price sits mid-zone rather than at a clean low-risk entry. The Mentor views this as a 'watch for an entry' — optimistic, patient, and happy to buy a pullback or a confirmed break rather than chase the middle of the range.",
      reasoning: [
        "A constructive but non-extreme setup is worth tracking, not forcing.",
        "The best risk is near support or on a confirmed break, not the middle of the range.",
        "You formed your view first — that is the habit that matters, regardless of agreement.",
      ],
      takeaway:
        "A balanced setup can still favour patience. The discipline of choosing before seeing the answer is the real learning.",
    },
    outcome: {
      decisionPointPrice: 218,
      steps: [
        {
          label: "+5 days",
          returnPct: 1.3,
          maxFavourableExcursion: 2.4,
          maxAdverseExcursion: -0.9,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: 3.4,
          maxFavourableExcursion: 4.1,
          maxAdverseExcursion: -1.6,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: 4.2,
          maxFavourableExcursion: 6.0,
          maxAdverseExcursion: -1.9,
          targetReached: true,
          invalidationReached: false,
        },
      ],
      narrative:
        "The stock drifted higher and eventually reached its target. Both a patient WAIT (which bought a mild pullback) and holding through worked; the less disciplined chase-to-the-top earned less per unit of risk.",
    },
    takeaway:
      "Commit to your own call before seeking any answer — compare to learn, not to chase a label.",
    learnWhy: [
      "Reach your own conclusion before you ever see the Mentor view.",
      "Compare your call with the Mentor's to sharpen reasoning, not to be 'right'.",
      "Confidence should reflect how complete the evidence felt, not how much you want to buy.",
    ],
  },

  /* ------------------------------------------------------------------ 08 */
  {
    id: "case-08-stop-loss-test",
    number: 8,
    title: "The Stop-Loss Test",
    theme: "Process over outcome",
    summary:
      "You already hold a position. React day by day and learn that a losing outcome can still be a correct decision.",
    situation:
      "This is not a fresh entry decision — you already own a position. You are long Acme Construct at ₹100 with a plan: a hard stop-loss at ₹95 and a target at ₹112. So far the stock has been behaving. Over the next few sessions the price moves day by day, and each day you decide how to manage: hold to the plan, or exit. There is no single 'right' answer from hindsight — the lesson is whether your process holds up.",
    interaction: {
      kind: "stopLoss",
      prompt: "You are long at ₹100 (stop ₹95, target ₹112). Manage the position.",
      days: [
        {
          day: "Day 1",
          headline: "A quiet, unremarkable day",
          detail:
            "The stock opens around ₹100 and drifts in a narrow band, closing near ₹100.6. Nothing has changed against your plan.",
          currentPrice: 100.6,
          choices: [
            {
              id: "hold",
              label: "Hold to the plan",
              preferred: true,
              noteWhenChosen:
                "Holding to an unbroken plan is standard risk management — the stop is still intact and the thesis is unchanged.",
            },
            {
              id: "exit",
              label: "Exit now",
              noteWhenChosen:
                "Exiting a position that has not broken any premise after one quiet day is cutting a valid trade early.",
            },
          ],
          resolution: {
            headline: "Price closes ₹100.6, stop untouched",
            detail:
              "A single quiet day changes nothing. The stop at ₹95 and target at ₹112 remain valid. The disciplined action is to hold.",
            processNote:
              "Holding an intact plan is correct even though 'nothing happened' — you are not being paid to trade every day.",
          },
        },
        {
          day: "Day 2",
          headline: "A strong move in your favour",
          detail:
            "The stock gaps up to ₹102.2 and holds strength through the day, closing near ₹103. Your position is now showing a small profit.",
          currentPrice: 103,
          choices: [
            {
              id: "hold",
              label: "Hold — let it run toward ₹112",
              preferred: true,
              noteWhenChosen:
                "The trade is working and the target is unbroken; moving the stop up is optional but holding the plan is fine.",
            },
            {
              id: "exit-profit",
              label: "Take the small profit now",
              noteWhenChosen:
                "Cashing out at the first green day protects little and abandons the plan's reward before the target is reached.",
            },
          ],
          resolution: {
            headline: "Price closes ₹103, well above the stop",
            detail:
              "Profit is small but the move is intact. Exiting now would lock in a tiny gain and give up a plan built around reaching ₹112.",
            processNote:
              "A working trade left to its plan is the point of having a target. Exiting at the first profit is cutting winners short.",
          },
        },
        {
          day: "Day 3",
          headline: "The market turns against you",
          detail:
            "The stock falls hard, closing at ₹96.8 — above your ₹95 stop, but the move has reversed and broken the short-term up-structure. Your thesis is now materially in danger.",
          currentPrice: 96.8,
          choices: [
            {
              id: "hold-below-stop",
              label: "Hold, it's not at ₹95 yet",
              preferred: false,
              noteWhenChosen:
                "The thesis that made you buy has broken even though the literal stop hasn't. Holding 'just above the stop' is hoping, not managing.",
            },
            {
              id: "exit-before-stop",
              label: "Exit at ₹96.8 — the setup has broken",
              preferred: true,
              noteWhenChosen:
                "The reason for the trade is gone. Exiting before a broken thesis worsens is disciplined risk management, even before the hard stop is hit.",
            },
          ],
          resolution: {
            headline: "The setup broke before the stop did",
            detail:
              "Your invalidation was 'the bullish structure breaks'. It broke here at ₹96.8 — above the ₹95 stop, but the trade's reason is gone. Getting out near ₹96.8 manages risk proactively.",
            processNote:
              "A stop is the maximum you'll lose, not a target you must reach. Exiting on a broken thesis early is better process than waiting to be stopped out.",
          },
        },
        {
          day: "Day 4",
          headline: "Aftermath",
          detail:
            "The stock continues lower to ₹94.2 — through your original stop. From here it eventually bounces back toward ₹104 over the following weeks.",
          currentPrice: 94.2,
          choices: [
            {
              id: "no-action",
              label: "Continue to the takeaway",
              preferred: true,
              noteWhenChosen:
                "The scenario resolves. What matters is which decisions were process-consistent — you'll see that now.",
            },
          ],
          resolution: {
            headline: "A stopped-out trade can still be a correct decision",
            detail:
              "Respecting the plan cost you a defined loss (down to your stop, or better if you exited at ₹96.8 on the broken thesis). Holding blindly and hoping would have meant a worse drawdown and a broken plan. The later bounce to ₹104 does not make waiting-and-hoping the right process.",
            processNote:
              "You lost money — but by process you were correct. A losing outcome does not prove a bad decision, just as this lucky bounce would not have proved a good one.",
          },
        },
      ],
    },
    evidence: [
      {
        label: "Position",
        value: "Long @ ₹100, stop ₹95",
        note: "A plan you entered with: stop, target, and an invalidation.",
        tone: "neutral",
      },
      {
        label: "Target",
        value: "₹112",
        note: "The reward side of the plan.",
        tone: "bullish",
      },
      {
        label: "Invalidation",
        value: "Bullish structure breaks",
        note: "The condition that means the trade's reason is gone.",
        tone: "neutral",
      },
    ],
    mentorView: {
      action: "WAIT",
      actionLabel: "Wait / manage",
      rationale:
        "The Stop-Loss Test teaches that process, not outcome, is what you can control and judge. Respecting the stop and exiting on a broken thesis were the disciplined calls — whether the price later bounced is hindsight that does not change the quality of the decision.",
      reasoning: [
        "Judge a decision by the information available at the time, not the final price.",
        "A defined loss taken according to plan is a successful trade by process.",
        "The dangerous habit is holding past an invalidation because 'it legally hadn't hit the stop yet' — or hating to take any loss.",
      ],
      takeaway:
        "A losing trade executed to plan is a good trade. The outcome is luck; the process is skill.",
    },
    outcome: {
      decisionPointPrice: 100,
      steps: [
        {
          label: "+5 days",
          returnPct: -3.2,
          maxFavourableExcursion: 3.0,
          maxAdverseExcursion: -5.8,
          targetReached: false,
          invalidationReached: true,
        },
        {
          label: "+10 days",
          returnPct: -4.4,
          maxFavourableExcursion: 3.0,
          maxAdverseExcursion: -6.0,
          targetReached: false,
          invalidationReached: true,
        },
        {
          label: "+20 days",
          returnPct: 3.1,
          maxFavourableExcursion: 4.2,
          maxAdverseExcursion: -6.0,
          targetReached: false,
          invalidationReached: true,
        },
      ],
      narrative:
        "The position was stopped out around the invalidation area and the price later recovered. The disciplined manager capped risk and moved on; the hopeful holder took the worst of it.",
    },
    takeaway:
      "Never measure a decision purely by whether it made or lost money. Measure it by whether you followed a sound plan.",
    learnWhy: [
      "A losing outcome does not imply a bad decision, and a winning outcome does not imply a good one.",
      "Protect the thesis: exit when the reason for the trade breaks, not only at the hard stop.",
      "A defined, pre-planned loss is acceptable; a plan abandoned on hope is not.",
    ],
  },

  /* ------------------------------------------------------------------ 09 */
  {
    id: "case-09-was-mentor-better",
    number: 9,
    title: "Was the Mentor Actually Better?",
    theme: "Mentor ≠ oracle",
    summary:
      "You decide, the Mentor decides, then the outcome lands. See that the Mentor is a reasoning aid, not a profit oracle.",
    situation:
      "For the first time, we'll show you a complete setup, have you commit to your call, then show the Mentor's decision, and finally the actual outcome at +5, +10 and +20 days with return, max favourable and adverse excursion, and whether target or invalidation was reached. ChemLab is rising with price above EMA20, support at ₹60, resistance at ₹72, and price now ₹66. You decide first — the Mentor's call and the outcome stay hidden until you commit.",
    chart: {
      timeframe: "3M",
      support: 60,
      resistance: 72,
      candles: buildFromCloses([
        [58, 59],
        [60, 61],
        [62, 63],
        [64, 63],
        [62, 64],
        [65, 66],
        [67, 66],
        [65, 67],
        [68, 69],
        [70, 69],
        [68, 70],
        [71, 70],
        [69, 71],
        [72, 71],
        [70, 69],
        [68, 69],
        [70, 71],
        [72, 72],
        [71, 70],
        [69, 70],
        [72, 73],
      ]),
    },
    interaction: {
      kind: "decision",
      prompt: "Commit to your call before the Mentor and the outcome are revealed.",
    },
    evidence: [
      {
        label: "Trend",
        value: "Uptrend",
        note: "Higher lows with price above the averages.",
        tone: "bullish",
      },
      {
        label: "EMA structure",
        value: "Supportive",
        note: "Price above EMA20 and EMA50.",
        tone: "bullish",
      },
      {
        label: "Support / resistance",
        value: "₹60 / ₹72",
        note: "Price mid-zone at ₹66 with a defined floor and ceiling.",
        tone: "neutral",
      },
      {
        label: "Risk / reward",
        value: "Moderate",
        note: `Above the preferred minimum (1 : ${PREFERRED_MIN_RISK_REWARD}).`,
        tone: "bullish",
      },
    ],
    mentorView: {
      action: "BUY",
      actionLabel: "Buy",
      rationale:
        "ChemLab presents a clean, constructive trend with price above the averages, a defined support at ₹60, and a plan that clears the preferred minimum risk/reward. Unlike previous setups that were extended or mid-zone, this read is straightforward — the Mentor sees a reasonable case to study an entry near ₹66 with the stop below ₹60.",
      reasoning: [
        "The trend, EMA structure and risk geometry are aligned.",
        "A clear stop below support and a defined target give a testable plan.",
        "The Mentor is stating a reasoned read — not promising a profit. You'll judge it against the outcome.",
      ],
      takeaway:
        "Whatever the outcome, the Mentor is a reasoning aid. Your process is what you control and improve.",
    },
    outcome: {
      decisionPointPrice: 66,
      steps: [
        {
          label: "+5 days",
          returnPct: 2.6,
          maxFavourableExcursion: 3.1,
          maxAdverseExcursion: -0.8,
          targetReached: false,
          invalidationReached: false,
        },
        {
          label: "+10 days",
          returnPct: 6.4,
          maxFavourableExcursion: 7.0,
          maxAdverseExcursion: -1.2,
          targetReached: true,
          invalidationReached: false,
        },
        {
          label: "+20 days",
          returnPct: 5.1,
          maxFavourableExcursion: 9.0,
          maxAdverseExcursion: -1.8,
          targetReached: true,
          invalidationReached: false,
        },
      ],
      narrative:
        "ChemLab rose steadily and hit its target at +10 days before retracing. Here the Mentor's constructive call worked well. But notice: this is one case — the Mentor is not always right. Whether you agreed or stood aside, keep evaluating your own decisions case by case.",
    },
    takeaway:
      "The Mentor can be better, worse, or equal to you on any given case. Use it to learn, never to outsource your judgment.",
    learnWhy: [
      "The Mentor is not an oracle — it can be right, wrong, or merely average on any case.",
      "The value of comparison is improving your own process, not importing a label.",
      "Measure both the decision and the outcome independently: outcome is luck; decision is skill.",
    ],
  },

  /* ------------------------------------------------------------------ 10 */
  {
    id: "case-10-you-are-mentor",
    number: 10,
    title: "You Are the Mentor",
    theme: "Self-assessment",
    summary:
      "The final case puts you in the Mentor's seat: build the read, then get feedback on how you reason — never a performance forecast.",
    situation:
      "You've worked through nine cases. Now the tables turn: a fresh setup appears and you play the Mentor. Given a rising stock at ₹132 with price above EMA20 and EMA50, support at ₹125, and resistance at ₹142, build your assessment across six dimensions the way the Mentor would — trend, entry discipline, risk management, setup selection, decision quality, and confidence calibration. When you submit, you'll receive a learning profile with a clear biggest-improvement area. This assesses how you reason about a setup — it is not a prediction of investment performance.",
    interaction: {
      kind: "selfAssessment",
      prompt: "You are the Mentor. Build the assessment for this setup.",
      fields: [
        {
          key: "trend",
          label: "Trend identification",
          options: [
            { id: "bullish", label: "Uptrend", preferred: true },
            { id: "sideways", label: "Sideways" },
            { id: "bearish", label: "Downtrend" },
          ],
        },
        {
          key: "entry",
          label: "Entry discipline",
          options: [
            { id: "pullback", label: "Wait for a pullback near support", preferred: true },
            { id: "breakout", label: "Wait for a confirmed break of ₹142" },
            { id: "immediate", label: "Enter at market ₹132 now" },
          ],
        },
        {
          key: "invalidation",
          label: "Risk management",
          options: [
            { id: "below-support", label: "A close below ₹125 support", preferred: true },
            { id: "below-130", label: "A close below ₹130" },
            { id: "none", label: "No defined invalidation" },
          ],
        },
        {
          key: "setup",
          label: "Setup selection",
          options: [
            { id: "above-min", label: "Risk/reward above the preferred minimum", preferred: true },
            { id: "marginal", label: "Marginal, roughly 1 : 1" },
            { id: "below-min", label: "Below the preferred minimum" },
          ],
        },
        {
          key: "action",
          label: "Decision quality",
          options: [
            { id: "WATCH", label: "Watch / staged entry", preferred: true },
            { id: "BUY", label: "Buy at ₹132" },
            { id: "AVOID", label: "Avoid" },
          ],
        },
        {
          key: "confidence",
          label: "Confidence calibration",
          options: [
            { id: "medium", label: "Medium — constructive but not certain", preferred: true },
            { id: "high", label: "High — near-certain" },
            { id: "low", label: "Low — little conviction" },
          ],
        },
      ],
    },
    evidence: [
      {
        label: "Trend",
        value: "Uptrend",
        note: "Rising price above EMA20 and EMA50.",
        tone: "bullish",
      },
      {
        label: "Support / resistance",
        value: "₹125 / ₹142",
        note: "A defined floor and ceiling with headroom.",
        tone: "bullish",
      },
      {
        label: "Entry location",
        value: "Mid-zone (₹132)",
        note: "Sound but not at a clean low-risk pullback.",
        tone: "neutral",
      },
    ],
    mentorView: {
      action: "WATCH",
      actionLabel: "Watch",
      rationale:
        "As the Mentor you'd want the strongest single view of this setup: a real uptrend, a defined risk/reward that clears the preferred minimum, and an entry best taken near support rather than mid-zone. The self-assessment grades how completely and consistently you built that read.",
      reasoning: [
        "The most complete plan names the trend, a clean entry, a defined invalidation and a healthy risk/reward.",
        "A constructive-but-not-certain setup calls for a measured, mid-confidence stance.",
        "Your profile is about reasoning quality — never a bet on the stock's price direction.",
      ],
      takeaway:
        "The goal is not a winning 'pick' — it is a complete, honest, repeatable way of thinking about any setup.",
    },
    takeaway:
      "You've learned to observe, form a view, compare with the Mentor, and understand outcomes. Carry that process into real analysis.",
    learnWhy: [
      "Self-assessment sharpens the six dimensions: trend, entry, risk, setup, decision, confidence.",
      "The profile reflects how you reason, never a performance prediction.",
      "Your biggest improvement area is the next place to focus as you keep practising.",
    ],
  },
];

/* ---------------------------------------------------------------------------
 * Lookups & helpers
 * ------------------------------------------------------------------------- */

export const CASE_BY_ID: Record<CaseId, CaseStudy> = Object.fromEntries(
  CASES.map((c) => [c.id, c]),
) as Record<CaseId, CaseStudy>;

export function getCase(id: CaseId): CaseStudy {
  return CASE_BY_ID[id];
}

export function caseCount(): number {
  return CASES.length;
}

/** All case ids in display order (used by progress/context). */
export const CASE_IDS: CaseId[] = CASES.map((c) => c.id);

export const CASE_7_ID: CaseId = "case-07-buy-or-wait";
export const CASE_8_ID: CaseId = "case-08-stop-loss-test";
export const CASE_9_ID: CaseId = "case-09-was-mentor-better";
export const CASE_10_ID: CaseId = "case-10-you-are-mentor";

/* ---------------------------------------------------------------------------
 * Decision reveal guards
 * ------------------------------------------------------------------------- */

export interface DecisionSubmission {
  action: DecisionAction;
  confidence: Confidence;
}

export interface MentorComparison {
  learner: DecisionSubmission;
  mentor: MentorView;
  agreement: Agreement;
  targetProvided: boolean;
  invalidationProvided: boolean;
}

export const CASE_7_DECISION_ONLY_FIELDS = true;

/**
 * A decision is driven by a CaseStudy's evidence + mentor view revealing after
 * the learner submits. Returns a comparison when the learner has committed.
 * This guard keeps the Mentor view hidden before a call is made.
 */
export function buildMentorComparison(
  caseStudy: CaseStudy,
  submission: DecisionSubmission | null,
): MentorComparison | null {
  if (submission === null) return null;
  return {
    learner: submission,
    mentor: caseStudy.mentorView,
    agreement: decisionAgreement(submission.action, caseStudy.mentorView.action),
    targetProvided: true,
    invalidationProvided: true,
  };
}

/* ---------------------------------------------------------------------------
 * Case 08 — stop-loss day reveal
 * ------------------------------------------------------------------------- */

export function stopLossDayCount(c: CaseStudy): number {
  if (c.interaction.kind !== "stopLoss") return 0;
  return c.interaction.days.length;
}

/**
 * Reveal one day's resolution only after the learner picks a choice that day.
 * Returns null until a choice is made for the requested day index.
 */
export function revealStopLossDay(
  c: CaseStudy,
  dayIndex: number,
  choiceId: string | null,
):
  | { day: StopLossDay; chosen: StopLossChoice }
  | undefined {
  if (c.interaction.kind !== "stopLoss" || dayIndex < 0) return undefined;
  const day = c.interaction.days[dayIndex];
  if (!day || choiceId === null) return undefined;
  const chosen = day.choices.find((choice) => choice.id === choiceId);
  if (!chosen) return undefined;
  return { day, chosen };
}

/* ---------------------------------------------------------------------------
 * Case 10 — self-assessment feedback
 * ------------------------------------------------------------------------- */

export interface AssessmentSubmission {
  [key: string]: string;
}

export interface AssessmentDimension {
  key: string;
  label: string;
  score: number; // 0..1
  note: string;
}

export interface AssessmentFeedback {
  dimensions: AssessmentDimension[];
  biggestImprovementArea: string;
  bigImprovementLabel: string;
}

type AssessmentFieldKey =
  | "trend"
  | "entry"
  | "invalidation"
  | "setup"
  | "action"
  | "confidence";

const PREFERRED_ASSESSMENT: Record<AssessmentFieldKey, string> = {
  trend: "bullish",
  entry: "pullback",
  invalidation: "below-support",
  setup: "above-min",
  action: "WATCH",
  confidence: "medium",
};

/**
 * Build the Case 10 learning profile. It scores the soundness of the reasoning
 * process — never a prediction of investment performance or price direction.
 */
export function buildAssessmentFeedback(
  submission: AssessmentSubmission,
): AssessmentFeedback {
  const score = (keys: AssessmentFieldKey[]) =>
    keys.filter((key) => submission[key] === PREFERRED_ASSESSMENT[key]).length /
    keys.length;

  const dimensions: AssessmentDimension[] = [
    {
      key: "trend-identification",
      label: "Trend identification",
      score: score(["trend"]),
      note: "Names the structural trend from the chart.",
    },
    {
      key: "entry-discipline",
      label: "Entry discipline",
      score: score(["entry"]),
      note: "Chooses a defined entry tied to a level.",
    },
    {
      key: "risk-management",
      label: "Risk management",
      score: score(["invalidation"]),
      note: "Defines a clear invalidation to protect the trade.",
    },
    {
      key: "setup-selection",
      label: "Setup selection",
      score: score(["setup"]),
      note: "Requires risk/reward above the preferred minimum.",
    },
    {
      key: "decision-quality",
      label: "Decision quality",
      score: score(["action"]),
      note: "Makes a testable, measured decision.",
    },
    {
      key: "confidence-calibration",
      label: "Confidence calibration",
      score: score(["confidence"]),
      note: "Sets confidence to match the completeness of the evidence.",
    },
  ];

  const weakest = dimensions.reduce((min, dim) =>
    dim.score <= min.score ? dim : min,
  );

  return {
    dimensions,
    biggestImprovementArea: weakest.label,
    bigImprovementLabel: `Focus on ${weakest.label.toLowerCase()} to strengthen the next setup you evaluate.`,
  };
}

/* ---------------------------------------------------------------------------
 * Outcome reveal guard (uniform across cases)
 * ------------------------------------------------------------------------- */

/**
 * Reveal a case's deterministic outcome only after the learner commits a
 * decision. Returns null before submission so the "what happened" stays hidden.
 */
export function buildCaseOutcome(
  caseStudy: CaseStudy,
  submitted: boolean,
): CaseOutcome | null {
  if (!submitted) return null;
  return caseStudy.outcome ?? null;
}

/* ---------------------------------------------------------------------------
 * Chart data expansion (kept here, separate from rendering)
 * ------------------------------------------------------------------------- */

/**
 * Deterministic OHLCV series for the situation charts. `candles` is authored as
 * [open, close] pairs extended with a modest range/volume; each row is given a
 * business-day IST timestamp so the shared candle chart and its axis render
 * correctly. Nothing here is market data.
 */
function buildFromCloses(
  pairs: Array<[number, number]>,
  opts: { start?: string; time?: string } = {},
): CandlesSpec {
  const time = opts.time ?? "10:15:00+05:30";
  const start = opts.start ?? "2026-01-05";
  const startDate = new Date(`${start}T${time}`);
  let cursor = startDate.getTime();
  const day = 24 * 60 * 60 * 1000;

  return pairs.map(([o, close], index) => {
    const [min, max] = o < close ? [o, close] : [close, o];
    const range = Math.max((max - min) * 0.4, (max + min) * 0.0015);
    // Deterministic pseudo-noise from the index so the series is stable.
    const wick = ((index * 37 + 11) % 100) / 100;
    const wick2 = ((index * 53 + 29) % 100) / 100;
    const high = close + wick * range;
    const low = Math.max(close - wick2 * range, min - range * 0.5);
    const row = {
      t: new Date(cursor).toISOString(),
      o,
      v: close,
      h: Number(high.toFixed(2)),
      l: Number(low.toFixed(2)),
      vol: Math.round(50000 + (((index * 97 + 13) % 100) / 100) * 200000),
    };
    // Advance to the next trading day (skip weekends) deterministically.
    cursor += day;
    while (new Date(cursor).getDay() === 0 || new Date(cursor).getDay() === 6) {
      cursor += day;
    }
    return row;
  });
}

/** Expand a CandlesSpec to ChartSeriesPoint[] for the shared chart component. */
export function expandCaseChart(candles: CandlesSpec): ChartSeriesPoint[] {
  return candles.map((row) => ({
    t: row.t,
    v: row.v,
    o: row.o,
    h: row.h,
    l: row.l,
    vol: row.vol,
  }));
}

/* Backwards-compatible aliases (kept for the shared components' vocabulary). */
export type Lesson = CaseStudy;
export const LESSONS: CaseStudy[] = CASES;
export type LessonId = CaseId;
export const LESSON_BY_ID: Record<LessonId, CaseStudy> = CASE_BY_ID;
export const LESSON_7_ID: CaseId = CASE_7_ID;
export function lessonCount(): number {
  return caseCount();
}
