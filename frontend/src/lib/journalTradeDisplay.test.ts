/** Journal display rules for open vs closed trades. */

export function formatExitPrice(
  isOpen: boolean,
  exitPrice: number | null | undefined,
): string {
  if (isOpen) return "—";
  if (exitPrice == null || Number.isNaN(exitPrice)) return "—";
  return exitPrice.toLocaleString("en-IN");
}

export function pnlLabel(isOpen: boolean): string {
  return isOpen ? "unrealized" : "realized";
}

describe("journalTradeDisplay", () => {
  it("shows dash for open trade exit price, never current market price", () => {
    expect(formatExitPrice(true, null)).toBe("—");
    expect(formatExitPrice(true, 1320)).toBe("—");
  });

  it("shows actual exit price for closed trades", () => {
    expect(formatExitPrice(false, 1365)).toBe("1,365");
  });

  it("labels P&L as unrealized vs realized", () => {
    expect(pnlLabel(true)).toBe("unrealized");
    expect(pnlLabel(false)).toBe("realized");
  });
});
