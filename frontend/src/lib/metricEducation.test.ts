import { buildMetricHelp } from "./metricEducation";

describe("metricEducation", () => {
  it("builds RSI help with live value", () => {
    const help = buildMetricHelp("rsi", { value: 47.5 });
    expect(help.title).toBe("RSI");
    expect(help.meaning).toContain("47.5");
    expect(help.meaning).not.toMatch(/undefined|null|NaN/i);
  });

  it("builds support help with price and level", () => {
    const help = buildMetricHelp("support", { value: 1150, price: 1180.7 });
    expect(help.meaning).toContain("₹");
    expect(help.meaning).toContain("above support");
  });

  it("avoids inventing values when data is missing", () => {
    const help = buildMetricHelp("ema50", {});
    expect(help.meaning).not.toMatch(/undefined|null|NaN/i);
  });

  it("explains risk reward with ratio", () => {
    const help = buildMetricHelp("riskReward", { riskReward: 0.9 });
    expect(help.meaning).toContain("0.90");
  });
});
