import {
  CASES,
  CASE_10_ID,
  CASE_7_ID,
  CASE_8_ID,
  CASE_9_ID,
  CASE_IDS,
  CONFIDENCE_OPTIONS,
  DECISION_ACTIONS,
  buildAssessmentFeedback,
  buildCaseOutcome,
  buildMentorComparison,
  caseCount,
  decisionAgreement,
  caseKind,
  mentorDecisionBucket,
  expandCaseChart,
  revealStopLossDay,
  stopLossDayCount,
  type CaseStudy,
} from "./howToUseLessons";

const byId = (id: string): CaseStudy => {
  const c = CASES.find((x) => x.id === id);
  if (!c) throw new Error(`missing case ${id}`);
  return c;
};

describe("howToUseLessons: case catalogue", () => {
  it("exposes exactly 10 cases", () => {
    expect(caseCount()).toBe(10);
    expect(CASES).toHaveLength(10);
    expect(CASE_IDS).toHaveLength(10);
  });

  it("numbers the cases 1..10 in sequence with unique ids", () => {
    const ids = CASES.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
    CASES.forEach((c, index) => {
      expect(c.number).toBe(index + 1);
    });
  });

  it("every case carries a situation, takeaway, learn-why and a mentor view", () => {
    for (const c of CASES) {
      expect(c.title.length).toBeGreaterThan(0);
      expect(c.theme.length).toBeGreaterThan(0);
      expect(c.summary.length).toBeGreaterThan(0);
      expect(c.situation.length).toBeGreaterThan(0);
      expect(c.takeaway.length).toBeGreaterThan(0);
      expect(c.learnWhy.length).toBeGreaterThan(0);
      expect(c.mentorView.action.length).toBeGreaterThan(0);
      expect(c.mentorView.rationale.length).toBeGreaterThan(0);
      expect(c.mentorView.reasoning.length).toBeGreaterThan(0);
    }
  });

  it("standard and stop-loss cases reveal evidence after a decision; self-assessment embeds it in the flow", () => {
    const selfAssessment = byId(CASE_10_ID);
    expect(caseKind(selfAssessment)).toBe("selfAssessment");
    for (const c of CASES) {
      expect(c.evidence.length).toBeGreaterThan(0);
    }
  });

  it("decision cases (1–7, 9) carry a deterministic outcome with 3 steps", () => {
    for (const c of CASES) {
      if (c.id === CASE_8_ID || c.id === CASE_10_ID) continue;
      expect(c.outcome?.steps.length).toBe(3);
      const steps = c.outcome!.steps;
      expect(steps[0].label).toContain("5");
      expect(steps[1].label).toContain("10");
      expect(steps[2].label).toContain("20");
      for (const step of steps) {
        expect(typeof step.returnPct).toBe("number");
        expect(typeof step.maxFavourableExcursion).toBe("number");
        expect(typeof step.maxAdverseExcursion).toBe("number");
        expect(typeof step.targetReached).toBe("boolean");
        expect(typeof step.invalidationReached).toBe("boolean");
      }
    }
  });

  it("case 7 is the guarded mentor-reveal case; case 8 is stop-loss; case 10 is self-assessment", () => {
    expect(byId(CASE_7_ID).interaction.kind).toBe("decision");
    expect(byId(CASE_8_ID).interaction.kind).toBe("stopLoss");
    expect(byId(CASE_10_ID).interaction.kind).toBe("selfAssessment");
  });
});

describe("howToUseLessons: decision vocabulary", () => {
  it("offers four actions and three confidence levels", () => {
    expect(DECISION_ACTIONS).toEqual(["BUY", "WATCH", "WAIT", "AVOID"]);
    expect(CONFIDENCE_OPTIONS).toEqual(["Low", "Medium", "High"]);
  });

  it("maps mentor-style actions onto the scale", () => {
    expect(mentorDecisionBucket("Strong Buy")).toBe("BUY");
    expect(mentorDecisionBucket("Buy")).toBe("BUY");
    expect(mentorDecisionBucket("Watch")).toBe("WATCH");
    expect(mentorDecisionBucket("Wait")).toBe("WAIT");
    expect(mentorDecisionBucket("Avoid")).toBe("AVOID");
  });

  it("classifies agreement between user and mentor buckets", () => {
    expect(decisionAgreement("BUY", "BUY")).toBe("agree");
    expect(decisionAgreement("WATCH", "WATCH")).toBe("agree");
    expect(decisionAgreement("BUY", "AVOID")).toBe("differ");
    expect(decisionAgreement("AVOID", "BUY")).toBe("differ");
    expect(decisionAgreement("WATCH", "BUY")).toBe("partial");
    expect(decisionAgreement(null, "BUY")).toBe("partial");
  });
});

describe("howToUseLessons: mentor reveal guard", () => {
  const case7 = byId(CASE_7_ID);

  it("does NOT build a comparison (mentor view) before the learner decides", () => {
    expect(buildMentorComparison(case7, null)).toBeNull();
  });

  it("builds a comparison only after the learner submits a decision", () => {
    const comparison = buildMentorComparison(case7, {
      action: "WAIT",
      confidence: "Medium",
    });
    expect(comparison).not.toBeNull();
    expect(comparison?.learner.action).toBe("WAIT");
    expect(comparison?.mentor.action.length).toBeGreaterThan(0);
    expect(typeof comparison?.agreement).toBe("string");
  });

  it("case 9 produces an independent user-vs-mentor comparison", () => {
    const case9 = byId(CASE_9_ID);
    const comparison = buildMentorComparison(case9, {
      action: "BUY",
      confidence: "High",
    });
    expect(comparison).not.toBeNull();
    expect(comparison?.learner.action).toBe("BUY");
    expect(comparison?.agreement).toBeTruthy();
    expect(comparison?.mentor.action.length).toBeGreaterThan(0);
  });
});

describe("howToUseLessons: case 8 stop-loss test", () => {
  const case8 = byId(CASE_8_ID);

  it("has a multi-day sequence (4 days)", () => {
    expect(caseKind(case8)).toBe("stopLoss");
    expect(stopLossDayCount(case8)).toBe(4);
    expect(case8.interaction.kind).toBe("stopLoss");
    expect(case8.interaction.days).toHaveLength(4);
  });

  it("hides each day's resolution until a choice is made that day", () => {
    expect(revealStopLossDay(case8, 0, null)).toBeUndefined();
    const revealed = revealStopLossDay(case8, 0, "hold");
    expect(revealed).toBeDefined();
    expect(revealed?.day.resolution.detail.length).toBeGreaterThan(0);
  });

  it("teaches that a losing outcome can still be a correct decision", () => {
    const case8 = byId(CASE_8_ID) as CaseStudy & { interaction: { kind: "stopLoss" } };
    // The takeaway frames decisions by process, not by whether they made money.
    expect(case8.takeaway.toLowerCase()).toMatch(/measure|made or lost|sound plan|process/);
    const anyProcessNote = case8.interaction.days.some((d) =>
      d.resolution.processNote.toLowerCase().includes("process"),
    );
    expect(anyProcessNote).toBe(true);
  });
});

describe("howToUseLessons: case 10 self-assessment feedback", () => {
  const aligned: Record<string, string> = {
    trend: "bullish",
    entry: "pullback",
    invalidation: "below-support",
    setup: "above-min",
    action: "WATCH",
    confidence: "medium",
  };

  it("covers the six reasoning dimensions and names a biggest improvement area", () => {
    const feedback = buildAssessmentFeedback(aligned);
    expect(feedback.dimensions).toHaveLength(6);
    const labels = feedback.dimensions.map((d) => d.label);
    expect(labels).toContain("Trend identification");
    expect(labels).toContain("Entry discipline");
    expect(labels).toContain("Risk management");
    expect(labels).toContain("Setup selection");
    expect(labels).toContain("Decision quality");
    expect(labels).toContain("Confidence calibration");
    expect(feedback.biggestImprovementArea.length).toBeGreaterThan(0);
    expect(feedback.bigImprovementLabel).toContain("Focus on");
  });

  it("does not grade price direction or predict performance", () => {
    const feedback = buildAssessmentFeedback(aligned);
    for (const dim of feedback.dimensions) {
      expect(dim.score).toBeGreaterThanOrEqual(0);
      expect(dim.score).toBeLessThanOrEqual(1);
    }
    expect(feedback.biggestImprovementArea).not.toMatch(/gain|profit|return|price/i);
  });

  it("highlights the lowest-scoring dimension", () => {
    const weak = buildAssessmentFeedback({ ...aligned, risk: "none", invalidation: "none" });
    const risk = weak.dimensions.find((d) => d.key === "risk-management");
    expect(risk?.score).toBeLessThan(1);
    expect(weak.biggestImprovementArea).toBe("Risk management");
  });
});

describe("howToUseLessons: outcome reveal guard", () => {
  it("hides a case's historical outcome before the learner commits", () => {
    const case1 = byId(CASES[0].id);
    expect(buildCaseOutcome(case1, false)).toBeNull();
  });

  it("reveals deterministic outcomes only after the learner commits", () => {
    const case1 = byId(CASES[0].id);
    const outcome = buildCaseOutcome(case1, true);
    expect(outcome).not.toBeNull();
    expect(outcome?.decisionPointPrice).toBeGreaterThan(0);
    expect(outcome?.steps).toHaveLength(3);
  });
});

describe("howToUseLessons: chart data expansion", () => {
  it("expands case candles into ordered, deterministic ChartSeriesPoint rows", () => {
    const case1 = byId(CASES[0].id);
    expect(case1.chart).toBeDefined();
    const series = expandCaseChart(case1.chart!.candles);
    expect(series.length).toBe(case1.chart!.candles.length);
    for (const point of series) {
      expect(typeof point.t).toBe("string");
      expect(typeof point.v).toBe("number");
      expect(typeof point.o).toBe("number");
      expect(typeof point.h).toBe("number");
      expect(typeof point.l).toBe("number");
    }
    // Deterministic: expanding twice yields identical rows.
    expect(expandCaseChart(case1.chart!.candles)).toEqual(series);
  });
});
