import type { Recommendation } from "@/types";

/** A user's own call — mirrors the ER-0034 `user_decision` union. */
export type UserDecision = "BUY" | "SELL" | "WATCH" | "AVOID";

export const DECISION_OPTIONS: UserDecision[] = ["BUY", "SELL", "WATCH", "AVOID"];

export const DECISION_LABELS: Record<UserDecision, string> = {
  BUY: "Buy",
  SELL: "Sell",
  WATCH: "Watch",
  AVOID: "Avoid",
};

export type Agreement = "agree" | "partial" | "differ";

/** Map a Mentor action on to the user's four-bucket scale for comparison. */
export function mentorBucket(action: string): UserDecision {
  switch (action) {
    case "Strong Buy":
    case "Buy":
      return "BUY";
    case "Watch":
      return "WATCH";
    case "Wait":
      return "AVOID";
    default:
      return "AVOID";
  }
}

/** Classify how close a user decision is to the Mentor's direction. */
export function decisionAgreement(
  user: UserDecision,
  mentor: UserDecision,
): Agreement {
  if (user === mentor) return "agree";
  if (user === "BUY" && mentor === "AVOID") return "differ";
  if (user === "AVOID" && mentor === "BUY") return "differ";
  if (user === "SELL" && mentor === "BUY") return "differ";
  return "partial";
}

export interface MentorDecision {
  action: string;
  bucket: UserDecision;
}

export interface LearningDebrief {
  userDecision: UserDecision;
  mentor: MentorDecision;
  agreement: Agreement;
  whereAgreed: string;
  whatMissed: string;
  thesisQuality: string;
  evidenceQuality: string;
  invalidationQuality: string;
  whyMentor: string;
  whatWouldChange: string;
  learning: {
    wentWell: string;
    couldImprove: string;
    watchNext: string;
    payAttention: string;
  };
}

function mentorFromRecommendation(
  recommendation: Recommendation | null,
): MentorDecision {
  if (!recommendation) return { action: "—", bucket: "WATCH" };
  return { action: recommendation.action, bucket: mentorBucket(recommendation.action) };
}

export interface DebriefInput {
  userThesis?: string;
  userInvalidation?: string;
}

function quality(value: string | undefined, prompt: string): string {
  if (!value || !value.trim()) return `Keep going — ${prompt}`;
  if (value.trim().length < 20) {
    return `A good start. ${prompt} Adding a bit more detail makes the reason easier to test later.`;
  }
  return `Clear and specific. ${prompt}`;
}

/**
 * Build the educational comparison and "key learning" for one journey.
 * Returns null when the user has not yet made a decision, so a comparison
 * can never be produced (or the Mentor view surfaced) before the user has
 * committed to their own call. This is deliberately narrative and
 * non-prescriptive — never advice.
 */
export function buildDebrief(
  userDecision: UserDecision | null,
  recommendation: Recommendation | null,
  input: DebriefInput = {},
): LearningDebrief | null {
  if (userDecision === null) return null;

  const mentor = mentorFromRecommendation(recommendation);
  const agreement = decisionAgreement(userDecision, mentor.bucket);

  const whereAgreed =
    agreement === "agree"
      ? `You and the Mentor read the same direction: ${DECISION_LABELS[userDecision].toUpperCase()}. When your own reasoning matches an independent analysis, that is a useful signal — but keep checking the reasons, not just the label.`
      : agreement === "partial"
        ? `You lean ${DECISION_LABELS[userDecision].toUpperCase()} while the Mentor leans ${mentor.action}. The two of you largely agree on the backdrop but not on the action — that is exactly the kind of nuance worth studying.`
        : `You chose ${DECISION_LABELS[userDecision].toUpperCase()} while the Mentor chose ${mentor.action}. A genuine difference is valuable: write down the single piece of evidence that changed your mind, and see whether it holds up.`;

  const mentorContext = recommendation
    ? Array.from(
        new Set([
          ...(recommendation.why ?? []),
          ...(recommendation.positives ?? []),
          ...(recommendation.risks ?? []),
        ]),
      )
    : [];
  const whatMissed = recommendation
    ? mentorContext.length
      ? `The Mentor weighed these points: ${mentorContext
          .slice(0, 3)
          .join(" ")}`
      : `The Mentor reached ${mentor.action} from the evidence available. Compare its reasoning with the evidence you weighed.`
    : "The Mentor did not have enough data to form a full view for this symbol today, so there is no reference comparison here.";

  const evidenceQuality = recommendation
    ? recommendation.dataQuality === "Complete"
      ? "The indicator set for this symbol was complete, so the Mentor's reference view uses all the headline metrics shown on the Study screen."
      : "Some indicators (often EMA50/EMA200 on thinly-served symbols) were unavailable, so the comparison rests on a partial picture. Note where the gaps are."
    : "There was no Mentor reference view for this symbol today.";

  const whyMentor = recommendation
    ? `${recommendation.verdict} ${recommendation.summary}`
    : "No Mentor conclusion was produced for this symbol.";

  const whatWouldChange = recommendation
    ? recommendation.nextTrigger
      ? `In the Mentor's view, ${recommendation.nextTrigger}`
      : "The Mentor's view would change if the underlying technical evidence moved — watch the levels and indicators you studied."
    : "Watch price action and the indicators on the Study screen; that evidence drives the Mentor's view when it is available.";

  return {
    userDecision,
    mentor,
    agreement,
    whereAgreed,
    whatMissed,
    thesisQuality: quality(
      input.userThesis,
      "State what you believe will happen and why, so you can check it against what actually follows.",
    ),
    evidenceQuality,
    invalidationQuality: quality(
      input.userInvalidation,
      "Name the specific level or condition that would prove your thesis wrong — a clear invalidation protects you from holding a losing idea.",
    ),
    whyMentor,
    whatWouldChange,
    learning: {
      wentWell: recommendation
        ? `You placed your own call before seeing the Mentor's ${mentor.action} view, which is the core habit this journey is built to train.`
        : "You completed a study and made your own call before seeking the Mentor's view.",
      couldImprove:
        agreement === "agree"
          ? "Since you agreed with the Mentor, test whether you can articulate the reasons independently rather than only the direction."
          : `Your call was ${DECISION_LABELS[userDecision].toUpperCase()} against the Mentor's ${mentor.action}. Focus on the evidence that drove the difference.`,
      watchNext: recommendation
        ? recommendation.nextTrigger
        : "Watch the levels and indicators you studied on the Study screen.",
      payAttention: recommendation
        ? `Pay attention to ${
            recommendation.rulesMatched && recommendation.rulesMatched.length
              ? `the signals the Mentor used: ${recommendation.rulesMatched.join(", ")}`
              : "the trend, momentum, and support/resistance levels you studied"
          }.${recommendation.warnings && recommendation.warnings.length ? " Note the data-quality warnings the Mentor flagged." : ""}`
        : "Pay attention to trend, momentum, and support/resistance on the next stock you study.",
    },
  };
}

/** Follow the ER-0034 convention: a decision is required; thesis is encouraged. */
export function isSubmissionReady(decision: UserDecision | null): boolean {
  return decision !== null;
}
