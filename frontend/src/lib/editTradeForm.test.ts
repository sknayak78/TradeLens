import {
  buildEditTradePayload,
  shouldShowExitFields,
  validateEditTradeForm,
  type EditTradeFormValues,
} from "./editTradeForm";

const openForm: EditTradeFormValues = {
  trade_date: "2026-08-21",
  entry_price: "1316",
  quantity: "4",
  status: "OPEN",
  exit_date: "",
  exit_price: "",
  notes: "my note",
};

describe("editTradeForm", () => {
  it("hides exit fields while trade is OPEN", () => {
    expect(shouldShowExitFields("OPEN")).toBe(false);
    expect(shouldShowExitFields("CLOSED")).toBe(true);
  });

  it("sends null exit fields for OPEN trades", () => {
    const payload = buildEditTradePayload(openForm, false);
    expect(payload.status).toBe("OPEN");
    expect(payload.exit_date).toBeNull();
    expect(payload.exit_price).toBeNull();
  });

  it("requires exit date and price when CLOSED", () => {
    expect(
      validateEditTradeForm({
        ...openForm,
        status: "CLOSED",
        exit_date: "",
        exit_price: "",
      }),
    ).toMatch(/exit date and exit price/i);

    expect(
      validateEditTradeForm({
        ...openForm,
        status: "CLOSED",
        exit_date: "2026-08-25",
        exit_price: "0",
      }),
    ).toMatch(/exit date and exit price/i);
  });

  it("rejects exit date before entry date", () => {
    expect(
      validateEditTradeForm({
        ...openForm,
        status: "CLOSED",
        exit_date: "2026-08-20",
        exit_price: "1365",
      }),
    ).toBe("Exit Date cannot be before Entry Date.");
  });

  it("builds CLOSED payload with user-entered exit values", () => {
    const payload = buildEditTradePayload(
      {
        ...openForm,
        status: "CLOSED",
        exit_date: "2026-08-25",
        exit_price: "1365",
      },
      false,
    );
    expect(payload.status).toBe("CLOSED");
    expect(payload.exit_price).toBe(1365);
    expect(payload.exit_date).toContain("2026-08-25");
  });

  it("does not auto-populate exit price from market data helpers", () => {
    const payload = buildEditTradePayload(openForm, false);
    expect(payload.exit_price).toBeNull();
  });
});
