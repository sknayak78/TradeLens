import type { TradeStatus, TradeUpdatePayload } from "@/services/tradeService";

export interface EditTradeFormValues {
  trade_date: string;
  entry_price: string;
  quantity: string;
  status: TradeStatus;
  exit_date: string;
  exit_price: string;
  notes: string;
}

export function shouldShowExitFields(status: TradeStatus): boolean {
  return status === "CLOSED";
}

export function validateEditTradeForm(
  form: EditTradeFormValues,
): string | null {
  const entry = parseFloat(form.entry_price);
  const qty = parseInt(form.quantity, 10);

  if (!(entry > 0)) return "Entry price must be greater than 0.";
  if (!(qty > 0)) return "Quantity must be greater than 0.";

  if (form.status === "CLOSED") {
    if (!form.exit_date) {
      return "Please enter the exit date and exit price before closing this trade.";
    }
    const exit = parseFloat(form.exit_price);
    if (!form.exit_price || !(exit > 0)) {
      return "Please enter the exit date and exit price before closing this trade.";
    }
    if (form.exit_date < form.trade_date) {
      return "Exit Date cannot be before Entry Date.";
    }
  }

  return null;
}

export function buildEditTradePayload(
  form: EditTradeFormValues,
  confirmOutOfRange: boolean,
): TradeUpdatePayload {
  const payload: TradeUpdatePayload = {
    trade_date: new Date(form.trade_date).toISOString(),
    entry_price: parseFloat(form.entry_price),
    quantity: parseInt(form.quantity, 10),
    notes: form.notes,
    status: form.status,
    confirm_out_of_range: confirmOutOfRange,
  };

  if (form.status === "CLOSED") {
    payload.exit_date = new Date(form.exit_date).toISOString();
    payload.exit_price = parseFloat(form.exit_price);
  } else {
    payload.exit_date = null;
    payload.exit_price = null;
  }

  return payload;
}
