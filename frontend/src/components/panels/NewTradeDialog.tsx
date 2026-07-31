import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { useCreateTrade } from "@/hooks/useTrades";

interface NewTradeDialogProps {
  open: boolean;
  onClose: () => void;
}

function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

export default function NewTradeDialog({ open, onClose }: NewTradeDialogProps) {
  const createTrade = useCreateTrade();
  const [form, setForm] = useState({
    symbol: "",
    trade_date: todayIso(),
    entry_price: "",
    exit_price: "",
    quantity: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setForm({
        symbol: "",
        trade_date: todayIso(),
        entry_price: "",
        exit_price: "",
        quantity: "",
        notes: "",
      });
      setError(null);
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const entry = parseFloat(form.entry_price);
    const exit = parseFloat(form.exit_price);
    const qty = parseInt(form.quantity, 10);
    if (!form.symbol.trim()) return setError("Symbol is required.");
    if (!(entry > 0)) return setError("Entry price must be greater than 0.");
    if (!(exit > 0)) return setError("Exit price must be greater than 0.");
    if (!(qty > 0)) return setError("Quantity must be greater than 0.");

    createTrade.mutate(
      {
        symbol: form.symbol.trim().toUpperCase(),
        trade_date: new Date(form.trade_date).toISOString(),
        entry_price: entry,
        exit_price: exit,
        quantity: qty,
        notes: form.notes,
      },
      {
        onSuccess: () => onClose(),
        onError: (err: Error) => setError(err.message || "Failed to save trade."),
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="new-trade-dialog"
    >
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-md bg-[#1e222d] border border-[#2a2e39] rounded-md shadow-2xl tl-fade-in"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2e39]">
          <h3 className="text-white text-sm font-semibold tracking-tight uppercase">
            New Trade
          </h3>
          <button
            type="button"
            onClick={onClose}
            data-testid="new-trade-close"
            className="p-1 rounded-md text-[#787b86] hover:text-white hover:bg-[#2a2e39]"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <Field label="Symbol">
            <input
              type="text"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              placeholder="RELIANCE"
              data-testid="new-trade-symbol"
              className="w-full h-9 px-3 bg-[#131722] border border-[#2a2e39] rounded-md text-sm text-white focus:border-[#2962ff]/60 outline-none"
            />
          </Field>
          <Field label="Trade Date">
            <input
              type="date"
              value={form.trade_date}
              onChange={(e) => setForm({ ...form, trade_date: e.target.value })}
              data-testid="new-trade-date"
              className="w-full h-9 px-3 bg-[#131722] border border-[#2a2e39] rounded-md text-sm text-white focus:border-[#2962ff]/60 outline-none"
            />
          </Field>
          <div className="grid grid-cols-3 gap-2">
            <Field label="Entry">
              <input
                type="number"
                step="0.01"
                value={form.entry_price}
                onChange={(e) => setForm({ ...form, entry_price: e.target.value })}
                data-testid="new-trade-entry"
                className="w-full h-9 px-2 bg-[#131722] border border-[#2a2e39] rounded-md text-sm font-mono tabular-nums text-white focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
            <Field label="Exit">
              <input
                type="number"
                step="0.01"
                value={form.exit_price}
                onChange={(e) => setForm({ ...form, exit_price: e.target.value })}
                data-testid="new-trade-exit"
                className="w-full h-9 px-2 bg-[#131722] border border-[#2a2e39] rounded-md text-sm font-mono tabular-nums text-white focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
            <Field label="Qty">
              <input
                type="number"
                value={form.quantity}
                onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                data-testid="new-trade-qty"
                className="w-full h-9 px-2 bg-[#131722] border border-[#2a2e39] rounded-md text-sm font-mono tabular-nums text-white focus:border-[#2962ff]/60 outline-none"
              />
            </Field>
          </div>
          <Field label="Notes">
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={3}
              placeholder="What did you see? What is your invalidation?"
              data-testid="new-trade-notes"
              className="w-full px-3 py-2 bg-[#131722] border border-[#2a2e39] rounded-md text-sm text-[#d1d4dc] focus:border-[#2962ff]/60 outline-none resize-none"
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
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-[#2a2e39]">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-md text-sm text-[#787b86] hover:text-white hover:bg-[#2a2e39] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createTrade.isPending}
            data-testid="new-trade-submit"
            className="px-4 py-1.5 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-white text-sm font-medium transition-colors disabled:opacity-60"
          >
            {createTrade.isPending ? "Saving…" : "Save Trade"}
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
      <span className="text-[10px] uppercase tracking-widest text-[#787b86]">
        {label}
      </span>
      {children}
    </label>
  );
}
