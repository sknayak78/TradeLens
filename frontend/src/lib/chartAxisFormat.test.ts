import {
  formatChartAxisTickLabel,
  getXAxisLabelPresentation,
} from "@/lib/chartAxisFormat";

describe("getXAxisLabelPresentation", () => {
  it("never uses vertical (90 deg) labels", () => {
    for (const tf of ["1D", "1W", "1M", "3M", "1Y"]) {
      expect(getXAxisLabelPresentation(tf).angle).not.toBe(90);
    }
  });

  it("1D uses roughly 40-45 degrees with adequate axis height", () => {
    const cfg = getXAxisLabelPresentation("1D");
    expect(cfg.angle).toBeGreaterThanOrEqual(40);
    expect(cfg.angle).toBeLessThanOrEqual(45);
    expect(cfg.height).toBeGreaterThan(30);
    expect(cfg.textAnchor).toBe("end");
  });

  it("1W uses a gentle 25-30 degree angle", () => {
    const cfg = getXAxisLabelPresentation("1W");
    expect(cfg.angle).toBeGreaterThanOrEqual(25);
    expect(cfg.angle).toBeLessThanOrEqual(30);
  });

  it("1M uses 30-35 degrees", () => {
    const cfg = getXAxisLabelPresentation("1M");
    expect(cfg.angle).toBeGreaterThanOrEqual(30);
    expect(cfg.angle).toBeLessThanOrEqual(35);
  });

  it("3M uses roughly 30 degrees", () => {
    const cfg = getXAxisLabelPresentation("3M");
    expect(cfg.angle).toBeGreaterThanOrEqual(28);
    expect(cfg.angle).toBeLessThanOrEqual(32);
  });

  it("1Y uses a steeper 35-45 degree angle for monthly labels", () => {
    const cfg = getXAxisLabelPresentation("1Y");
    expect(cfg.angle).toBeGreaterThanOrEqual(35);
    expect(cfg.angle).toBeLessThanOrEqual(45);
    expect(cfg.height).toBeGreaterThan(30);
  });

  it("provides a sane default for unknown timeframes", () => {
    const cfg = getXAxisLabelPresentation("9M" as string);
    expect(cfg.angle).toBeGreaterThan(0);
    expect(cfg.angle).toBeLessThan(90);
    expect(cfg.height).toBeGreaterThan(0);
  });
});

describe("formatChartAxisTickLabel", () => {
  it("formats intraday labels as HH:mm", () => {
    expect(formatChartAxisTickLabel("1D", "2026-08-21T14:30:00+05:30")).toMatch(
      /^\d{2}:\d{2}$/,
    );
  });

  it("formats monthly (1Y) labels with month and year", () => {
    const label = formatChartAxisTickLabel("1Y", "2025-08-21T10:00:00+05:30");
    expect(label).toMatch(/\w{3} \d{4}/);
  });
});
