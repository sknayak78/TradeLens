import {
  formatEntryRange,
  formatMoney,
  formatRiskReward,
  formatSnapshotLabel,
  hasMentorSnapshot,
  mentorSnapshotRows,
  type MentorSnapshot,
} from "./tradeMentorSnapshot";

const fullSnapshot: MentorSnapshot = {
  action: "Buy",
  strategy: "Pullback",
  entry_range_low: 1942,
  entry_range_high: 1946,
  actual_entry_price: 1943.4,
  planned_stop_loss: 1871.1,
  target_1: 2031,
  target_2: 2101,
  risk_reward: 1.14,
  holding_period: "1-3 Weeks",
  reason: "Healthy trend with pullback into preferred entry zone.",
  captured_at: "2026-08-21T09:30:00+00:00",
};

describe("tradeMentorSnapshot", () => {
  it("detects when a mentor snapshot is present", () => {
    expect(hasMentorSnapshot(fullSnapshot)).toBe(true);
    expect(hasMentorSnapshot(null)).toBe(false);
  });

  it("renders human-readable labels without raw rule keys", () => {
    const rows = mentorSnapshotRows(fullSnapshot);
    expect(rows.map((row) => row.label)).toEqual([
      "Mentor view",
      "Strategy",
      "Entry range",
      "Actual entry",
      "Planned stop",
      "Target 1",
      "Target 2",
      "Risk / Reward",
      "Holding period",
    ]);
    expect(rows[0].value).toBe("Buy");
    expect(rows[1].value).toBe("Pullback");
    expect(rows.some((row) => row.value.includes("rulesMatched"))).toBe(false);
  });

  it("formats money and ranges for the journal UI", () => {
    expect(formatMoney(1943.4)).toContain("₹");
    expect(formatEntryRange(1942, 1946)).toContain("–");
    expect(formatRiskReward(1.14)).toBe("1 : 1.14");
  });

  it("shows friendly text for missing values", () => {
    expect(formatMoney(null)).toBe("Not available at entry");
    expect(formatEntryRange(null, 1946)).toBe("Not available at entry");
    expect(formatRiskReward(undefined)).toBe("Not available at entry");
    expect(formatSnapshotLabel("")).toBe("Not available at entry");
  });

  it("keeps user notes separate from mentor snapshot fields", () => {
    const rows = mentorSnapshotRows(fullSnapshot);
    expect(rows.find((row) => row.label === "Mentor view")?.value).toBe("Buy");
    expect(rows.find((row) => row.label === "Strategy")?.value).toBe("Pullback");
  });

  it("preserves historical snapshot values in formatted output", () => {
    const unchanged = mentorSnapshotRows({
      ...fullSnapshot,
      action: "Buy",
    });
    expect(unchanged[0].value).toBe("Buy");
    expect(unchanged[0].value).not.toBe("Watch");
  });
});
