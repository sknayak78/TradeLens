import { useEffect, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";
import { useUpdateTrade } from "@/hooks/useTrades";
import { useDayRange, useStock } from "@/hooks/useMarket";
import {
  buildEditTradePayload,
  shouldShowExitFields,
  validateEditTradeForm,
  type EditTradeFormValues,
} from "@/lib/editTradeForm";
import { showApiError, showSuccess } from "@/lib/feedback";
import type { Trade, TradeStatus } from "@/services/tradeService";

interface EditTradeDialogProps {
  trade: Trade | null;
  onClose: () => void;
}

type PriceWarning = {
  field: "entry" | "exit";
  message: string;
};

function toDateInput(iso: string | null): string {
  if (!iso) return "";
  return iso.slice(0, 10);
}

function formFromTrade(trade: Trade): EditTradeFormValues {
  return {
    trade_date: toDateInput(trade.trade_date),
    entry_price: String(trade.entry_price),
    quantity: String(trade.quantity),
    status: trade.status,
    exit_date: toDateInput(trade.exit_date),
    exit_price: trade.exit_price != null ? String(trade.exit_price) : "",
    notes: trade.notes ?? "",
  };
}

export default function EditTradeDialog({ trade, onClose }: EditTradeDialogProps) {
  const updateTrade = useUpdateTrade();
  const submittingRef = useRef(false);
  const open = trade !== null;

  const [form, setForm] = useState<EditTradeFormValues>({
    trade_date: "",
    entry_price: "",
    quantity: "",
    status: "OPEN",
    exit_date: "",
    exit_price: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [priceWarnings, setPriceWarnings] = useState<PriceWarning[]>([]);
  const [confirmOutOfRange, setConfirmOutOfRange] = useState(false);

  const symbol = trade?.symbol ?? "";
  const { data: stock } = useStock(symbol, "1W");
  const showExitFields = shouldShowExitFields(form.status);

  const entryRange = useDayRange(
    symbol,
    form.trade_date,
    open && Boolean(symbol && form.trade_date),
  );
  const exitRange = useDayRange(
    symbol,
    form.exit_date,
    open && showExitFields && Boolean(symbol && form.exit_date),
  );

  useEffect(() => {
    if (!trade) return;
    submittingRef.current = false;
    setForm(formFromTrade(trade));
    setError(null);
    setPriceWarnings([]);
    setConfirmOutOfRange(false);
  }, [trade]);

  useEffect(() => {
    const warnings: PriceWarning[] = [];
    const entry = parseFloat(form.entry_price);
    if (entryRange.data?.available && Number.isFinite(entry)) {
      const { low, high } = entryRange.data;
      if (low != null && high != null && (entry < low || entry > high)) {
        warnings.push({
          field: "entry",
          message: `Entry price ₹${entry.toLocaleString("en-IN")} is outside the recorded trading range of ₹${low.toLocaleString("en-IN")}–₹${high.toLocaleString("en-IN")} for ${form.trade_date}.`,
        });
      }
    }

    const exit = parseFloat(form.exit_price);
    if (
      showExitFields &&
      form.exit_date &&
      exitRange.data?.available &&
      Number.isFinite(exit)
    ) {
      const { low, high } = exitRange.data;
      if (low != null && high != null && (exit < low || exit > high)) {
        warnings.push({
          field: "exit",
          message: `Exit price ₹${exit.toLocaleString("en-IN")} is outside the recorded trading range of ₹${low.toLocaleString("en-IN")}–₹${high.toLocaleString("en-IN")} for ${form.exit_date}.`,
        });
      }
    }

    setPriceWarnings(warnings);
  }, [
    entryRange.data,
    exitRange.data,
    form.entry_price,
    form.exit_price,
    form.trade_date,
    form.exit_date,
    showExitFields,
  ]);

  const hasBlockingRangeWarning = useMemo(
    () =>
      priceWarnings.some(
        (warning) =>
          warning.message.includes("outside the recorded trading range") &&
          !confirmOutOfRange,
      ),
    [priceWarnings, confirmOutOfRange],
  );

  if (!open || !trade) return null;

  const handleStatusChange = (status: TradeStatus) => {
    setForm((prev) => ({ ...prev, status }));
  };

  const handleUseCurrentPrice = () => {
    if (stock?.price) {
      setForm((prev) => ({ ...prev, exit_price: String(stock.price) }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (updateTrade.isPending || submittingRef.current) return;
    setError(null);

    const validationError = validateEditTradeForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }
    if (hasBlockingRangeWarning) {
      setError("Confirm the out-of-range prices before saving.");
      return;
    }

    const payload = buildEditTradePayload(form, confirmOutOfRange);

    submittingRef.current = true;
    updateTrade.mutate(
      { id: trade.id, payload },
      {
        onSuccess: () => {
          submittingRef.current = false;
          showSuccess("Trade updated.", `${trade.symbol} journal entry saved.`);
          onClose();
        },
        onError: (err) => {
          submittingRef.current = false;
          showApiError("Could not update trade", err);
          setError(
            err instanceof Error ? err.message : "Failed to update trade.",
          );
        },
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="edit-trade-dialog"
    >
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-lg bg-white border border-[#D9DDE2] rounded-md shadow-2xl tl-fade-in max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#D9DDE2] sticky top-0 bg-white">
          <h3 className="text-[#1F2933] text-sm font-semibold tracking-tight uppercase">
            Edit Trade
          </h3>
          <button
            type="button"
            onClick={onClose}
            data-testid="edit-trade-close"
            className="p-1 rounded-md text-[#667085] hover:text-[#1F2933] hover:bg-[#F0F1EF]"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div className="rounded-md border border-[#D9DDE2] bg-[#F8F9FA] px-3 py-2 text-sm">
            <span className="text-[#667085]">Stock: </span>
            <span className="font-medium text-[#1F2933]">{trade.symbol}</span>
            <span className="text-[#667085] ml-3">Side: </span>
            <span className="font-mono text-xs text-[#1F2933]">{trade.side}</span>
          </div>

          <Field label="Entry Date">
            <input
              type="date"
              value={form.trade_date}
              onChange={(e) => setForm({ ...form, trade_date: e.target.value })}
              data-testid="edit-trade-date"
              className="w-full h-9 px-3 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
            />
          </Field>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Entry Price">
              <input
                type="number"
                step="0.01"
                value={form.entry_price}
                onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
                data-testid="edit-trade-entry"
                className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
            <Field label="Quantity">
              <input
                type="number"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                data-testid="edit-trade-qty"
                className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
          </div>

          <Field label="Status">
            <div className="flex gap-2">
              {(["OPEN", "CLOSED"] as TradeStatus[]).map((status) => {
                const selected = form.status === status;
                return (
                  <button
                    key={status}
                    type="button"
                    onClick={() => handleStatusChange(status)}
                    data-testid={`edit-trade-status-${status.toLowerCase()}`}
                    className={`px-3 py-1.5 rounded-md text-xs font-mono border transition-colors ${
                      selected
                        ? status === "OPEN"
                          ? "bg-[#2962ff]/10 text-[#2962ff] border-[#2962ff]/30"
                          : "bg-[#667085]/10 text-[#1F2933] border-[#667085]/40"
                        : "text-[#667085] border-[#D9DDE2] hover:bg-[#F0F1EF]"
                    }`}
                  >
                    {status}
                  </button>
                );
              })}
            </div>
          </Field>

          {form.status === "OPEN" && (
            <div
              className="rounded-md border border-[#2962ff]/20 bg-[#2962ff]/5 px-3 py-2 text-xs text-[#2962ff]"
              data-testid="edit-trade-open-hint"
            >
              Position is still open. No exit has been recorded. Select{" "}
              <span className="font-semibold">CLOSED</span> to enter exit date and
              exit price.
            </div>
          )}

          {showExitFields && (
            <div
              className="rounded-md border border-[#D9DDE2] bg-[#FCFCFB] p-3 space-y-2"
              data-testid="edit-trade-exit-section"
            >
              <div className="text-[10px] uppercase tracking-widest text-[#667085]">
                Exit details
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Exit Date">
                  <input
                    type="date"
                    value={form.exit_date}
                    onChange={(e) =>
                      setForm({ ...form, exit_date: e.target.value })
                    }
                    data-testid="edit-trade-exit-date"
                    className="w-full h-9 px-3 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
                  />
                </Field>
                <Field label="Exit Price">
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={form.exit_price}
                    onChange={(e) =>
                      setForm({ ...form, exit_price: e.target.value })
                    }
                    data-testid="edit-trade-exit"
                    className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
                  />
                  {stock?.price != null && (
                    <button
                      type="button"
                      onClick={handleUseCurrentPrice}
                      data-testid="edit-trade-use-current-price"
                      className="text-[10px] text-[#2962ff] hover:underline mt-0.5 text-left"
                    >
                      Use current market price (₹
                      {stock.price.toLocaleString("en-IN")})
                    </button>
                  )}
                </Field>
              </div>
            </div>
          )}

          {priceWarnings.length > 0 && (
            <div className="space-y-2">
              {priceWarnings.map((warning) => (
                <div
                  key={warning.field}
                  className="text-xs text-[#f5a623] bg-[#f5a623]/10 border border-[#f5a623]/30 rounded-md px-3 py-2"
                >
                  {warning.message}
                </div>
              ))}
              {priceWarnings.some((warning) =>
                warning.message.includes("outside the recorded trading range"),
              ) && (
                <label className="flex items-center gap-2 text-xs text-[#667085]">
                  <input
                    type="checkbox"
                    checked={confirmOutOfRange}
                    onChange={(e) => setConfirmOutOfRange(e.target.checked)}
                  />
                  I understand these prices are outside the recorded range and want to save anyway.
                </label>
              )}
            </div>
          )}

          <Field label="My Note">
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              data-testid="edit-trade-notes"
              className="w-full px-3 py-2 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none resize-none break-words [overflow-wrap:anywhere]"
            />
          </Field>

          {error && (
            <div
              className="text-xs text-[#ef5350] bg-[#ef5350]/10 border border-[#ef5350]/30 rounded-md px-3 py-2"
              data-testid="edit-trade-error"
            >
              {error}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-[#D9DDE2] sticky bottom-0 bg-white">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-sm text-[#667085] hover:text-[#1F2933] hover:bg-[#F0F1EF] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={updateTrade.isPending}
            data-testid="edit-trade-submit"
            className="px-4 py-1.5 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-white text-sm font-medium transition-colors disabled:opacity-60"
          >
            {updateTrade.isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-widest text-[#667085]">
        {label}
      </span>
      {children}
    </label>
  );
}
