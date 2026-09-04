import {
  DECISION_OPTIONS,
  journalDecisionAgreement,
  journalMentorBucket,
  buildDebrief,
  isSubmissionReady,
  type UserDecision,
} from "./learningJourney";
import type { Recommendation } from "@/types";

const baseRecommendation: Recommendation = {
  action: "Buy",
  strategy: "Trend Continuation",
  verdict: "The trend is supportive; a pullback entry is possible.",
  summary: "Price holds above the available averages with room before resistance.",
  conviction: "Medium",
  score: 70,
  trend: "bullish",
  confidence: 0.6,
  dataQuality: "Partial",
  holdingPeriod: "1-3 Weeks",
  nextTrigger: "Watch for a pullback to the support zone before entering.",
  beginnerTip: "Patience is a position.",
  idealFor: "Traders who want confirmation before risking capital.",
  why: ["The price is above the available averages.", "Momentum is constructive."],
  positives: ["The trend is supportive."],
  risks: ["Resistance sits just overhead.", "Some history was unavailable."],
  entryCondition: "Wait for a pullback before entering.",
  rationale: "Price holds above the available averages with room before resistance.",
  rulesMatched: ["price_above_ema20", "rsi_healthy"],
  warnings: ["partial_data: EMA50, EMA200 unavailable"],
  levels: {
    entryMin: 100,
    entryMax: 102,
    stopLoss: 97,
    target1: 110,
    target2: 115,
    riskReward: 2.0,
  },
};

describe("learningJourney decison model", () => {
  it("exposes the four user decision options", () => {
    expect(DECISION_OPTIONS).toEqual(["BUY", "SELL", "WATCH", "AVOID"]);
  });

  it("maps mentor actions onto the four-bucket scale", () => {
    expect(journalMentorBucket("Strong Buy")).toBe("BUY");
    expect(journalMentorBucket("Buy")).toBe("BUY");
    expect(journalMentorBucket("Watch")).toBe("WATCH");
    expect(journalMentorBucket("Wait")).toBe("AVOID");
    expect(journalMentorBucket("Avoid")).toBe("AVOID");
  });

  it("classifies agreement between user and mentor buckets", () => {
    expect(journalDecisionAgreement("BUY", "BUY")).toBe("agree");
    expect(journalDecisionAgreement("WATCH", "WATCH")).toBe("agree");
    expect(journalDecisionAgreement("BUY", "AVOID")).toBe("differ");
    expect(journalDecisionAgreement("AVOID", "BUY")).toBe("differ");
    expect(journalDecisionAgreement("SELL", "BUY")).toBe("differ");
    expect(journalDecisionAgreement("WATCH", "BUY")).toBe("partial");
    expect(journalDecisionAgreement("BUY", "WATCH")).toBe("partial");
  });

  it("requires a decision before submission, not a thesis", () => {
    expect(isSubmissionReady(null)).toBe(false);
    expect(isSubmissionReady("BUY")).toBe(true);
  });
});

describe("learningJourney debrief", () => {
  function expectDebrief(
    value: ReturnType<typeof buildDebrief>,
  ): NonNullable<ReturnType<typeof buildDebrief>> {
    expect(value).not.toBeNull();
    return value as NonNullable<ReturnType<typeof buildDebrief>>;
  }

  it("builds an agreement debrief that explains where the user agreed", () => {
    const debrief = expectDebrief(
      buildDebrief("BUY", baseRecommendation, {
        userThesis: "Pullback to support should hold and resume the uptrend.",
        userInvalidation: "A daily close below 97 invalidates the idea.",
      }),
    );
    expect(debrief.mentor.action).toBe("Buy");
    expect(debrief.mentor.bucket).toBe("BUY");
    expect(debrief.agreement).toBe("agree");
    expect(debrief.whereAgreed).toContain("same direction");
  });

  it("builds a differ debrief for an opposing call", () => {
    const debrief = expectDebrief(buildDebrief("AVOID", baseRecommendation));
    expect(debrief.agreement).toBe("differ");
    expect(debrief.whereAgreed).toContain("genuine difference");
    expect(debrief.learning.couldImprove).toContain("AVOID");
  });

  it("surfaces the mentor's reasoning and what would change its view", () => {
    const debrief = expectDebrief(buildDebrief("WATCH", baseRecommendation));
    expect(debrief.whyMentor).toContain(baseRecommendation.verdict);
    expect(debrief.whatWouldChange).toContain("Watch for a pullback");
    expect(debrief.learning.payAttention).toBeDefined();
    expect(debrief.whatMissed).toContain("The Mentor weighed these points");
  });

  it("handles an absent recommendation without leaking or crashing", () => {
    const debrief = expectDebrief(buildDebrief("WATCH", null));
    expect(debrief.mentor.action).toBe("—");
    expect(debrief.whyMentor).toContain("No Mentor conclusion");
    expect(debrief.evidenceQuality).toContain("no Mentor reference view");
  });

  it("encourages a missing thesis and invalidation without requiring them", () => {
    const debrief = expectDebrief(buildDebrief("BUY", baseRecommendation, {}));
    expect(debrief.thesisQuality).toContain("Keep going");
    expect(debrief.invalidationQuality).toContain("Keep going");
  });
});

describe("learningJourney debrief before a decision is made", () => {
  it("returns null (does not throw) when the decision is null", () => {
    expect(buildDebrief(null, baseRecommendation)).toBeNull();
    expect(buildDebrief(null, null)).toBeNull();
  });

  it("does not expose the mentor comparison before a decision is made", () => {
    const debrief = buildDebrief(null, baseRecommendation, {
      userThesis: "Thesis text",
      userInvalidation: "Invalidation text",
    });
    expect(debrief).toBeNull();
  });

  it("produces a comparison only once a valid decision has been submitted", () => {
    expect(buildDebrief(null, baseRecommendation)).toBeNull();
    const after = buildDebrief("BUY", baseRecommendation);
    expect(after).not.toBeNull();
    expect(after?.userDecision).toBe("BUY");
  });
});
