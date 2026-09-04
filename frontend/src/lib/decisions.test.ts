import { type Agreement } from "./decisions";
import {
  caseDecisionLabels,
  caseMentorBucket,
  caseDecisionAgreement,
  DECISION_ACTIONS as academyActions,
} from "./howToUseLessons";
import {
  journalDecisionLabels,
  journalMentorBucket,
  journalDecisionAgreement,
  DECISION_OPTIONS as journalActions,
} from "./learningJourney";

describe("decisions module", () => {
  it("defines the shared Agreement union", () => {
    const values: Agreement[] = ["agree", "partial", "differ"];
    expect(values).toHaveLength(3);
    expect(values).toEqual(expect.arrayContaining(["agree", "partial", "differ"]));
  });

  it("keeps the Academy and Journal taxonomies distinct", () => {
    expect(academyActions).toEqual(["BUY", "WATCH", "WAIT", "AVOID"]);
    expect(journalActions).toEqual(["BUY", "SELL", "WATCH", "AVOID"]);
    expect(journalActions).toContain("SELL");
    expect(academyActions).not.toContain("SELL");
    expect(academyActions).toContain("WAIT");
    expect(journalActions).not.toContain("WAIT");
  });

  it("keeps the Academy WAIT bucket distinct from the Journal", () => {
    expect(caseMentorBucket("Wait")).toBe("WAIT");
    expect(journalMentorBucket("Wait")).toBe("AVOID");
    expect(caseDecisionLabels.WAIT).toBe("Wait");
    expect(journalDecisionLabels).not.toHaveProperty("WAIT");
  });

  it("keeps Academy caseDecisionAgreement behaviour without a SELL differ case", () => {
    expect(caseDecisionAgreement("BUY", "BUY")).toBe("agree");
    expect(caseDecisionAgreement("BUY", "AVOID")).toBe("differ");
    expect(caseDecisionAgreement("AVOID", "BUY")).toBe("differ");
    expect(caseDecisionAgreement(null, "BUY")).toBe("partial");
    expect(caseDecisionAgreement("WATCH", "BUY")).toBe("partial");
  });

  it("keeps Journal journalDecisionAgreement including the SELL differ case", () => {
    expect(journalDecisionAgreement("BUY", "BUY")).toBe("agree");
    expect(journalDecisionAgreement("SELL", "BUY")).toBe("differ");
    expect(journalDecisionAgreement("AVOID", "BUY")).toBe("differ");
    expect(journalDecisionAgreement("WATCH", "BUY")).toBe("partial");
  });
});
