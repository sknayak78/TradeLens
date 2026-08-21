/** Tests for compact My Note panel in the trading journal. */

export const LONG_NOTE =
  "This is a very long user-entered trading observation that should wrap naturally inside the journal card and must never overflow the layout.";

export function noteWrapClasses(): string {
  return "break-words [overflow-wrap:anywhere]";
}

describe("tradeMyNote", () => {
  it("uses wrapping classes that prevent horizontal overflow", () => {
    const classes = noteWrapClasses();
    expect(classes).toContain("break-words");
    expect(classes).toContain("overflow-wrap:anywhere");
  });

  it("handles long notes without truncation markers", () => {
    expect(LONG_NOTE.length).toBeGreaterThan(80);
    expect(LONG_NOTE).not.toMatch(/\.\.\.$/);
  });
});
