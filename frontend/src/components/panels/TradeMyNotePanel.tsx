import { useEffect, useState } from "react";
import { Pencil } from "lucide-react";
import { useUpdateTrade } from "@/hooks/useTrades";
import { showApiError, showSuccess } from "@/lib/feedback";

interface TradeMyNotePanelProps {
  tradeId: number;
  notes: string;
}

export default function TradeMyNotePanel({
  tradeId,
  notes,
}: TradeMyNotePanelProps) {
  const updateTrade = useUpdateTrade();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(notes);

  useEffect(() => {
    if (!editing) {
      setDraft(notes);
    }
  }, [notes, editing]);

  const trimmed = notes.trim();
  const hasNote = Boolean(trimmed);

  const handleSave = () => {
    updateTrade.mutate(
      { id: tradeId, payload: { notes: draft } },
      {
        onSuccess: () => {
          showSuccess("Note saved.");
          setEditing(false);
        },
        onError: (err) => showApiError("Could not save note", err),
      },
    );
  };

  const handleCancel = () => {
    setDraft(notes);
    setEditing(false);
  };

  return (
    <div
      className="mt-2"
      data-testid={`journal-note-${tradeId}`}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="text-[10px] uppercase tracking-widest text-[#667085]">
          My Note
        </div>
        {hasNote && !editing && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            data-testid={`journal-note-edit-${tradeId}`}
            className="inline-flex items-center gap-1 text-[11px] text-[#2962ff] hover:text-[#2962ff]/80"
          >
            <Pencil size={11} />
            Edit
          </button>
        )}
      </div>

      {!hasNote && !editing && (
        <button
          type="button"
          onClick={() => setEditing(true)}
          data-testid={`journal-note-add-${tradeId}`}
          className="text-xs text-[#2962ff] hover:text-[#2962ff]/80 font-medium"
        >
          + Add a note
        </button>
      )}

      {hasNote && !editing && (
        <p
          className="text-xs text-[#1F2933] leading-relaxed break-words [overflow-wrap:anywhere]"
          data-testid={`journal-note-text-${tradeId}`}
        >
          {trimmed}
        </p>
      )}

      {editing && (
        <div className="space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={3}
            placeholder="What did you think about this trade?"
            data-testid={`journal-note-input-${tradeId}`}
            className="w-full px-2.5 py-2 bg-white border border-[#D9DDE2] rounded-md text-xs text-[#1F2933] focus:border-[#2962ff]/60 outline-none resize-none break-words [overflow-wrap:anywhere]"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={updateTrade.isPending}
              data-testid={`journal-note-save-${tradeId}`}
              className="px-2.5 py-1 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-white text-[11px] font-medium disabled:opacity-60"
            >
              {updateTrade.isPending ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              onClick={handleCancel}
              disabled={updateTrade.isPending}
              data-testid={`journal-note-cancel-${tradeId}`}
              className="px-2.5 py-1 rounded-md text-[11px] text-[#667085] hover:text-[#1F2933] hover:bg-[#F0F1EF]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
