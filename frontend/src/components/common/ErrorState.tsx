import { AlertTriangle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  testId?: string;
}

export default function ErrorState({
  title = "Something went wrong",
  message = "We couldn't load the data. Please try again.",
  onRetry,
  testId = "error-state",
}: ErrorStateProps) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col items-center justify-center text-center py-8 gap-2"
    >
      <span className="w-10 h-10 rounded-md bg-[#ef5350]/10 border border-[#ef5350]/30 flex items-center justify-center text-[#ef5350]">
        <AlertTriangle size={18} />
      </span>
      <p className="text-sm text-[#1F2933] font-medium">{title}</p>
      <p className="text-xs text-[#667085] max-w-xs">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          data-testid={`${testId}-retry`}
          className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#2962ff]/15 border border-[#2962ff]/40 text-[#2962ff] text-xs uppercase tracking-widest hover:bg-[#2962ff]/25 transition-colors"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
