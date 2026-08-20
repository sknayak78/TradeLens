import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { useCreateTrade, useUpdateTrade } from "@/hooks/useTrades";
import { useDayRange } from "@/hooks/useMarket";
import { marketService } from "@/services/marketService";
import { showApiError, showSuccess } from "@/lib/feedback";
import type { Trade, TradeSide } from "@/services/tradeService";

interface NewTradeDialogProps {
  open: boolean;
  onClose: () => void;
  trade?: Trade | null;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function toDateInput(iso: string): string {
  return iso.slice(0, 10);
}

type PriceWarning = {
  field: "entry" | "exit";
  message: string;
};

export default function NewTradeDialog({ open, onClose, trade = null }: NewTradeDialogProps) {
  const createTrade = useCreateTrade();
  const updateTrade = useUpdateTrade();
  const isEdit = trade != null;
  const [form, setForm] = useState({
    symbol: "RELIANCE",
    trade_date: todayIso(),
    exit_date: "",
    entry_price: "",
    exit_price: "",
    quantity: "",
    side: "LONG" as TradeSide,
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [symbolValid, setSymbolValid] = useState(true);
  const [priceWarnings, setPriceWarnings] = useState<PriceWarning[]>([]);
  const [confirmOutOfRange, setConfirmOutOfRange] = useState(false);
  const [symbolSuggestions, setSymbolSuggestions] = useState<
    { symbol: string; name: string }[]
  >([]);

  const entryRange = useDayRange(
    form.symbol.trim().toUpperCase(),
    form.trade_date,
    open && Boolean(form.symbol.trim() && form.trade_date),
  );
  const exitRange = useDayRange(
    form.symbol.trim().toUpperCase(),
    form.exit_date,
    open && Boolean(form.symbol.trim() && form.exit_date),
  );

  useEffect(() => {
    if (open) {
      if (trade) {
        setForm({
          symbol: trade.symbol,
          trade_date: toDateInput(trade.trade_date),
          exit_date: trade.exit_date ? toDateInput(trade.exit_date) : "",
          entry_price: String(trade.entry_price),
          exit_price: trade.exit_price != null ? String(trade.exit_price) : "",
          quantity: String(trade.quantity),
          side: trade.side,
          notes: trade.notes,
        });
      } else {
        setForm({
          symbol: "RELIANCE",
          trade_date: todayIso(),
          exit_date: "",
          entry_price: "",
          exit_price: "",
          quantity: "",
          side: "LONG",
          notes: "",
        });
      }
      setError(null);
      setSymbolValid(true);
      setPriceWarnings([]);
      setConfirmOutOfRange(false);
      setSymbolSuggestions([]);
    }
  }, [open, trade]);

  useEffect(() => {
    if (!open) return;
    const query = form.symbol.trim();
    if (query.length < 1) {
      setSymbolSuggestions([]);
      setSymbolValid(false);
      return;
    }
    let cancelled = false;
    marketService.searchStocks(query, 6).then((rows) => {
      if (cancelled) return;
      setSymbolSuggestions(rows.map((row) => ({ symbol: row.symbol, name: row.name })));
      setSymbolValid(rows.some((row) => row.symbol === query.toUpperCase()));
    });
    return () => {
      cancelled = true;
    };
  }, [form.symbol, open]);

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
    } else if (
      entryRange.data &&
      !entryRange.data.available &&
      entryRange.data.message &&
      form.entry_price
    ) {
      warnings.push({ field: "entry", message: entryRange.data.message });
    }

    const exit = parseFloat(form.exit_price);
    if (form.exit_date && exitRange.data?.available && Number.isFinite(exit)) {
      const { low, high } = exitRange.data;
      if (low != null && high != null && (exit < low || exit > high)) {
        warnings.push({
          field: "exit",
          message: `Exit price ₹${exit.toLocaleString("en-IN")} is outside the recorded trading range of ₹${low.toLocaleString("en-IN")}–₹${high.toLocaleString("en-IN")} for ${form.exit_date}.`,
        });
      }
    } else if (
      form.exit_date &&
      exitRange.data &&
      !exitRange.data.available &&
      exitRange.data.message &&
      form.exit_price
    ) {
      warnings.push({ field: "exit", message: exitRange.data.message });
    }

    setPriceWarnings(warnings);
  }, [
    entryRange.data,
    exitRange.data,
    form.entry_price,
    form.exit_price,
    form.trade_date,
    form.exit_date,
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

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const entry = parseFloat(form.entry_price);
    const exit = form.exit_price ? parseFloat(form.exit_price) : NaN;
    const qty = parseInt(form.quantity, 10);
    const symbol = form.symbol.trim().toUpperCase();

    if (!symbol) return setError("Symbol is required.");
    if (!symbolValid) return setError("Please select a valid stock symbol.");
    if (!(entry > 0)) return setError("Entry price must be greater than 0.");
    if (!(qty > 0)) return setError("Quantity must be greater than 0.");
    if (form.exit_date && form.exit_date < form.trade_date) {
      return setError("Exit Date cannot be before Entry Date.");
    }
    if ((form.exit_date && !form.exit_price) || (!form.exit_date && form.exit_price)) {
      return setError("A closed trade requires both Exit Date and Exit Price.");
    }
    if (form.exit_date && !(exit > 0)) {
      return setError("Exit price must be greater than 0 for closed trades.");
    }
    if (hasBlockingRangeWarning) {
      return setError("Confirm the out-of-range prices before saving.");
    }

    const payload = {
      symbol,
      side: form.side,
      trade_date: new Date(form.trade_date).toISOString(),
      entry_price: entry,
      exit_date: form.exit_date ? new Date(form.exit_date).toISOString() : null,
      exit_price: form.exit_date ? exit : null,
      quantity: qty,
      notes: form.notes,
      confirm_out_of_range: confirmOutOfRange,
    };

    if (isEdit && trade) {
      updateTrade.mutate(
        { id: trade.id, payload },
        {
          onSuccess: () => {
            showSuccess("Trade updated.", `${symbol} journal entry saved.`);
            onClose();
          },
          onError: (err) => {
            showApiError("Could not update trade", err);
            setError(
              err instanceof Error ? err.message : "Failed to update trade.",
            );
          },
        },
      );
      return;
    }

    createTrade.mutate(
      payload,
      {
        onSuccess: () => {
          showSuccess("Trade saved.", `${symbol} added to your journal.`);
          onClose();
        },
        onError: (err) => {
          showApiError("Could not save trade", err);
          setError(
            err instanceof Error ? err.message : "Failed to save trade.",
          );
        },
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid={isEdit ? "edit-trade-dialog" : "new-trade-dialog"}
    >
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-lg bg-white border border-[#D9DDE2] rounded-md shadow-2xl tl-fade-in max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#D9DDE2] sticky top-0 bg-white">
          <h3 className="text-[#1F2933] text-sm font-semibold tracking-tight uppercase">
            {isEdit ? "Edit Trade" : "New Trade"}
          </h3>
          <button
            type="button"
            onClick={onClose}
            data-testid="new-trade-close"
            className="p-1 rounded-md text-[#667085] hover:text-[#1F2933] hover:bg-[#F0F1EF]"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <Field label="Symbol">
            <input
              type="text"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
              placeholder="RELIANCE"
              data-testid="new-trade-symbol"
              className={`w-full h-9 px-3 bg-white border rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none ${
                symbolValid ? "border-[#D9DDE2]" : "border-[#ef5350]"
              }`}
            />
            {symbolSuggestions.length > 0 && (
              <div className="rounded-md border border-[#D9DDE2] bg-white shadow-sm overflow-hidden">
                {symbolSuggestions.map((row) => (
                  <button
                    key={row.symbol}
                    type="button"
                    onClick={() => setForm({ ...form, symbol: row.symbol })}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-[#F0F1EF]"
                  >
                    <span className="font-medium text-[#1F2933]">{row.symbol}</span>
                    <span className="text-[#667085] ml-2">{row.name}</span>
                  </button>
                ))}
              </div>
            )}
            {!symbolValid && form.symbol.trim() && (
              <p className="text-xs text-[#ef5350]">Please select a valid stock symbol.</p>
            )}
          </Field>

          <Field label="Side">
            <div className="flex gap-2">
              {(["LONG", "SHORT"] as TradeSide[]).map((side) => (
                <button
                  key={side}
                  type="button"
                  onClick={() => setForm({ ...form, side })}
                  className={`px-3 py-1.5 rounded-md text-xs font-mono border ${
                    form.side === side
                      ? side === "LONG"
                        ? "bg-[#26a69a]/10 text-[#26a69a] border-[#26a69a]/30"
                        : "bg-[#ef5350]/10 text-[#ef5350] border-[#ef5350]/30"
                      : "text-[#667085] border-[#D9DDE2]"
                  }`}
                >
                  {side}
                </button>
              ))}
            </div>
          </Field>

          <div className="grid grid-cols-2 gap-2">
            <Field label="Entry Date">
              <input
                type="date"
                value={form.trade_date}
                onChange={(e) => setForm({ ...form, trade_date: e.target.value })}
                data-testid="new-trade-date"
                className="w-full h-9 px-3 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
            <Field label="Exit Date (optional)">
              <input
                type="date"
                value={form.exit_date}
                onChange={(e) => setForm({ ...form, exit_date: e.target.value })}
                data-testid="new-trade-exit-date"
                className="w-full h-9 px-3 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Field label="Entry Price">
              <input
                type="number"
                step="0.01"
                value={form.entry_price}
                onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
                data-testid="new-trade-entry"
                className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
              {entryRange.data?.available && (
                <span className="text-[10px] text-[#667085]">
                  Range: ₹{entryRange.data.low?.toLocaleString("en-IN")}–₹
                  {entryRange.data.high?.toLocaleString("en-IN")}
                </span>
              )}
            </Field>
            <Field label="Exit Price (optional)">
              <input
                type="number"
                step="0.01"
                value={form.exit_price}
                onChange={(e) => setForm({ ...form, exit_price: e.target.value })}
                data-testid="new-trade-exit"
                className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
              {exitRange.data?.available && form.exit_date && (
                <span className="text-[10px] text-[#667085]">
                  Range: ₹{exitRange.data.low?.toLocaleString("en-IN")}–₹
                  {exitRange.data.high?.toLocaleString("en-IN")}
                </span>
              )}
            </Field>
            <Field label="Qty">
              <input
                type="number"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                data-testid="new-trade-qty"
                className="w-full h-9 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm font-mono tabular-nums text-[#1F2933] focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
          </div>

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

          <Field label="Notes">
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              placeholder="What did you see? What is your invalidation?"
              data-testid="new-trade-notes"
              className="w-full px-3 py-2 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] focus:border-[#2962ff]/60 outline-none resize-none"
            />
          </Field>

          {error && (
            <div
              className="text-xs text-[#ef5350] bg-[#ef5350]/10 border border-[#ef5350]/30 rounded-md px-3 py-2"
              data-testid="new-trade-error"
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
            disabled={createTrade.isPending || updateTrade.isPending}
            data-testid={isEdit ? "edit-trade-submit" : "new-trade-submit"}
            className="px-4 py-1.5 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-white text-sm font-medium transition-colors disabled:opacity-60"
          >
            {createTrade.isPending || updateTrade.isPending
              ? "Saving…"
              : isEdit
                ? "Update Trade"
                : "Save Trade"}
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
