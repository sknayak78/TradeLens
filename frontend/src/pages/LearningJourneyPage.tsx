import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  GraduationCap,
  Search,
  EyeOff,
  ShieldCheck,
  Compass,
  ArrowRight,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Star,
  Check,
  NotebookPen,
} from "lucide-react";
import { useLearningJourney } from "@/hooks/useMarket";
import { useWatchlist, useAddToWatchlist } from "@/hooks/useWatchlist";
import { showApiError, showSuccess } from "@/lib/feedback";
import { useAppSettings } from "@/context/SettingsContext";
import { marketService, StockSummary, LearningJourneyData } from "@/services/marketService";
import CandlestickChart from "@/components/charts/CandlestickChart";
import NewTradeDialog from "@/components/panels/NewTradeDialog";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";
import MetricHelp from "@/components/common/MetricHelp";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import { type ChartTimeframe } from "@/lib/chartTimeAxis";
import {
  DECISION_OPTIONS,
  journalDecisionLabels,
  buildDebrief,
  isSubmissionReady,
  type UserDecision,
} from "@/lib/learningJourney";

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"] as const;

type Stage = "intro" | "study" | "decide" | "compare" | "learn";

const QUICK_PICKS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "WIPRO"];

function money(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "Not available";
  return `₹${value.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function notAvailable(value: number | null | undefined): boolean {
  return value == null || !Number.isFinite(value);
}

export default function LearningJourneyPage() {
  const navigate = useNavigate();
  const { settings } = useAppSettings();
  const defaultTimeframe = settings?.preferred_timeframe ?? "1W";

  const [stage, setStage] = useState<Stage>("intro");
  const [symbol, setSymbol] = useState<string>("");
  const [timeframe, setTimeframe] = useState<string>(defaultTimeframe);
  const [reveal, setReveal] = useState(false);
  const [decision, setDecision] = useState<UserDecision | null>(null);
  const [thesis, setThesis] = useState("");
  const [invalidation, setInvalidation] = useState("");

  const { data: study, isLoading, isError, error, refetch } = useLearningJourney(
    symbol,
    timeframe,
    reveal,
  );

  useEffect(() => {
    setTimeframe(defaultTimeframe);
  }, [defaultTimeframe]);

  useEffect(() => {
    setReveal(false);
    setStage(symbol ? "study" : "intro");
    setDecision(null);
    setThesis("");
    setInvalidation("");
  }, [symbol]);

  const debrief = useMemo(
    () => buildDebrief(decision, reveal && study ? study.recommendation : null, {
      userThesis: thesis,
      userInvalidation: invalidation,
    }),
    [decision, reveal, study, thesis, invalidation],
  );

  const handleSelectSymbol = (next: string) => {
    setSymbol(next);
  };

  const handleSubmitDecision = () => {
    if (!isSubmissionReady(decision)) return;
    setReveal(true);
    setStage("compare");
  };

  const handleStartAnother = () => {
    setSymbol("");
    setStage("intro");
  };

  return (
    <div data-testid="learning-journey-page" className="p-4 md:p-6 min-w-0">
      <PageHeader stage={stage} symbol={symbol} />

      {/* Stepper */}
      <div
        className="mb-4 flex items-center gap-1 overflow-x-auto text-[10px] font-mono uppercase tracking-widest text-[#667085]"
        data-testid="lj-stepper"
      >
        {(["study", "decide", "compare", "learn"] as const).map((s, i) => {
          const reached =
            stage === "intro" ||
            (["study", "decide", "compare", "learn"].indexOf(stage) >= i);
          return (
            <div key={s} className="flex items-center gap-1 shrink-0">
              {i > 0 && <span className="text-[#D9DDE2]">/</span>}
              <span
                className={
                  reached ? "text-[#2962ff]" : "text-[#C5CAD3]"
                }
                data-testid={`lj-step-${s}`}
              >
                {s}
              </span>
            </div>
          );
        })}
      </div>

      {stage === "intro" && (
        <IntroState onSelect={handleSelectSymbol} />
      )}

      {stage !== "intro" && study && (
        <>
          <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.15fr)_minmax(300px,38%)] gap-4 items-start">
            <div className="min-w-0 order-1 flex flex-col gap-4">
              <EvidencePanel
                study={study}
                timeframe={timeframe}
                setTimeframe={setTimeframe}
                hidden={!reveal}
              />

              {stage === "study" && (
                <StudyBanner
                  onProceed={() => setStage("decide")}
                />
              )}

              {stage === "decide" && (
                <DecisionForm
                  decision={decision}
                  setDecision={setDecision}
                  thesis={thesis}
                  setThesis={setThesis}
                  invalidation={invalidation}
                  setInvalidation={setInvalidation}
                  onSubmit={handleSubmitDecision}
                  disabled={!isSubmissionReady(decision)}
                />
              )}

              {debrief !== null && (stage === "compare" || stage === "learn") && (
                <ComparisonAndLearning
                  stage={stage}
                  decision={decision}
                  recommendation={study.recommendation}
                  debrief={debrief}
                  onGoLearning={() => setStage("learn")}
                  onStartAnother={handleStartAnother}
                  onDashboard={() => navigate("/")}
                />
              )}
            </div>

            <div className="min-w-0 order-2">
              <QuickSnapshot study={study} />
            </div>
          </div>

          <div className="mt-4">
            <EducationalDisclaimer />
          </div>
        </>
      )}

      {(stage !== "intro" && isLoading) && (
        <LoadingState testId="lj-loading" label="Loading study evidence" />
      )}
      {stage !== "intro" && isError && !isLoading && (
        <ErrorState
          message={error?.message ?? "Failed to load learning data."}
          onRetry={() => refetch()}
          testId="lj-error"
        />
      )}
    </div>
  );
}

function PageHeader({ stage, symbol }: { stage: Stage; symbol: string }) {
  return (
    <div className="mb-3 flex items-end justify-between flex-wrap gap-2">
      <div className="max-w-3xl">
        <h1 className="text-[#1F2933] text-xl md:text-2xl font-semibold tracking-tight flex items-center gap-2">
          <GraduationCap size={22} className="text-[#2962ff]" />
          Guided Research
        </h1>
        <p className="text-xs text-[#667085] mt-1">
          Study the evidence. Make your own call. Compare it with the TradeLens
          Mentor. This is guided research for learning, not a trade.
        </p>
      </div>
      {symbol && (
        <div className="text-[10px] font-mono tabular-nums text-[#667085]">
          <span className="px-2 py-1 rounded-[3px] bg-[#F0F1EF] border border-[#D9DDE2] uppercase tracking-widest">
            {symbol} · NSE
          </span>
        </div>
      )}
    </div>
  );
}

function IntroState({ onSelect }: { onSelect: (symbol: string) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<StockSummary[]>([]);
  const [spinning, setSpinning] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const q = query.trim();
      if (!q) {
        setResults([]);
        setSpinning(false);
        return;
      }
      setSpinning(true);
      marketService
        .searchStocks(q, 8)
        .then((rows) => {
          setResults(rows);
          setSpinning(false);
        })
        .catch(() => {
          setResults([]);
          setSpinning(false);
        });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  return (
    <div data-testid="lj-intro" className="max-w-2xl">
      <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-5">
        <div className="flex items-center gap-2 mb-1">
          <Compass size={15} className="text-[#2962ff]" />
          <h2 className="text-sm font-semibold text-[#1F2933] tracking-tight">
            Choose any stock to study
          </h2>
        </div>
        <p className="text-xs text-[#667085] mb-4">
          Search any supported NSE stock. You are not limited to today's
          opportunities or your watchlist.
        </p>

        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[#667085] pointer-events-none"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search e.g. RELIANCE, TCS, INFY…"
            data-testid="lj-search-input"
            className="w-full h-10 pl-9 pr-3 rounded-md bg-white border border-[#D9DDE2] text-sm text-[#1F2933] placeholder:text-[#667085] focus:border-[#2962ff]/60 focus:outline-none transition-colors"
          />
        </div>

        {spinning && (
          <div className="mt-3 flex items-center gap-2 text-xs text-[#667085]">
            <RefreshCw size={13} className="animate-spin" /> Searching…
          </div>
        )}

        {results.length > 0 && (
          <div className="mt-3 border border-[#D9DDE2] rounded-[4px] divide-y divide-[#D9DDE2]">
            {results.map((s) => (
              <button
                key={s.symbol}
                onClick={() => onSelect(s.symbol)}
                data-testid={`lj-result-${s.symbol}`}
                className="w-full flex items-center justify-between px-3 py-2 hover:bg-[#F0F1EF] transition-colors text-left"
              >
                <div className="min-w-0">
                  <div className="text-sm text-[#1F2933] font-medium">
                    {s.symbol}
                  </div>
                  <div className="text-xs text-[#667085] truncate">
                    {s.name}
                  </div>
                </div>
                <div className="text-right shrink-0 ml-3">
                  <div className="font-mono tabular-nums text-sm text-[#1F2933]">
                    {money(s.price)}
                  </div>
                  <div
                    className={`font-mono tabular-nums text-xs ${
                      s.changePct >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
                    }`}
                  >
                    {s.changePct >= 0 ? "+" : ""}
                    {s.changePct.toFixed(2)}%
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-2">
            Quick picks
          </div>
          <div className="flex flex-wrap gap-2">
            {QUICK_PICKS.map((s) => (
              <button
                key={s}
                onClick={() => onSelect(s)}
                data-testid={`lj-quick-${s}`}
                className="px-3 py-1.5 rounded-[4px] border border-[#D9DDE2] text-[11px] font-mono tracking-wide text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="mt-4">
        <EducationalDisclaimer variant="inline" />
      </div>
    </div>
  );
}

function StudyBanner({ onProceed }: { onProceed: () => void }) {
  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-[#fffbea] p-4">
      <div className="flex items-center gap-2 text-[#1F2933] font-semibold text-sm mb-1">
        <EyeOff size={15} />
        Mentor view is hidden
      </div>
      <p className="text-xs text-[#667085] mb-3">
        Make your own decision based on the evidence before seeing the Mentor's
        view.
      </p>
      <button
        onClick={onProceed}
        data-testid="lj-proceed-to-decide"
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded bg-[#2962ff] hover:bg-[#2962ff]/80 text-white text-sm font-medium transition-colors"
      >
        Make My Decision <ArrowRight size={14} />
      </button>
    </div>
  );
}

function EvidencePanel({
  study,
  timeframe,
  setTimeframe,
  hidden,
}: {
  study: LearningJourneyData;
  timeframe: string;
  setTimeframe: (tf: string) => void;
  hidden: boolean;
}) {
  const { data: watchlist = [] } = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const [journalOpen, setJournalOpen] = useState(false);

  const inWatchlist = useMemo(
    () => watchlist.some((w) => w.symbol === study.symbol),
    [watchlist, study.symbol],
  );

  const handleAddToWatchlist = () => {
    if (inWatchlist || addToWatchlist.isPending) return;
    addToWatchlist.mutate(study.symbol, {
      onSuccess: () => {
        showSuccess(`${study.symbol} added to your watchlist.`);
      },
      onError: (err) => {
        showApiError(`Could not add ${study.symbol} to watchlist`, err);
      },
    });
  };

  const stats = useMemo(() => {
    const values = study.series.map((p) => p.v);
    if (!values.length) return null;
    const first = values[0];
    const last = values[values.length - 1];
    return { changePct: ((last - first) / first) * 100, min: Math.min(...values), max: Math.max(...values) };
  }, [study.series]);

  const isUp = study.trend === "bullish";
  const lineColor = isUp ? "#26a69a" : study.trend === "bearish" ? "#ef5350" : "#2962ff";

  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg text-[#1F2933] font-semibold tracking-tight">
              {study.name}
            </h2>
            <span className="text-[10px] font-mono text-[#667085] uppercase tracking-widest px-2 py-0.5 rounded-[3px] bg-[#F0F1EF] border border-[#D9DDE2]">
              {study.symbol}
            </span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-mono tabular-nums text-[#1F2933]">
              {money(study.price)}
            </span>
            <span
              className={`font-mono tabular-nums text-sm ${
                study.changePct >= 0 ? "text-[#26a69a]" : "text-[#ef5350]"
              }`}
              data-testid="lj-price-change"
            >
              {study.changePct >= 0 ? "+" : ""}
              {study.changePct.toFixed(2)}%
            </span>
          </div>
          <div className="text-[11px] text-[#667085] mt-0.5">
            {study.sector}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button
              onClick={handleAddToWatchlist}
              disabled={inWatchlist || addToWatchlist.isPending}
              data-testid="lj-add-watchlist"
              aria-label={inWatchlist ? "Already in watchlist" : "Add to watchlist"}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                inWatchlist
                  ? "text-[#26a69a] bg-[#26a69a]/10 border border-[#26a69a]/30 cursor-default"
                  : "text-[#1F2933] bg-white border border-[#D9DDE2] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5"
              }`}
            >
              {inWatchlist ? <Check size={13} /> : <Star size={13} />}
              {inWatchlist ? "In Watchlist" : "Add to Watchlist"}
            </button>
            <button
              onClick={() => setJournalOpen(true)}
              data-testid="lj-add-journal"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium text-[#1F2933] bg-white border border-[#D9DDE2] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5 transition-colors"
            >
              <NotebookPen size={13} />
              Add to Trade Journal
            </button>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-1" data-testid="lj-timeframes">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                data-testid={`lj-timeframe-${tf}`}
                className={`px-2 py-1 rounded text-[10px] font-mono uppercase tracking-wider transition-colors ${
                  tf === timeframe
                    ? "bg-[#2962ff]/10 text-[#2962ff]"
                    : "text-[#667085] hover:bg-[#F0F1EF] hover:text-[#1F2933]"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
          <DataQualityTag quality={study.dataQuality} />
        </div>
      </div>

      <CandlestickChart
        series={study.series}
        timeframe={timeframe as ChartTimeframe}
        support={study.support}
        resistance={study.resistance}
        lineColor={lineColor}
      />

      <div className="text-[10px] text-[#667085] uppercase tracking-widest">
        {study.timeframeLabel ?? study.timeframe}
        {study.timeframeFallback ? " (daily fallback)" : ""} · change over period{" "}
        {stats ? `${stats.changePct >= 0 ? "+" : ""}${stats.changePct.toFixed(2)}%` : "—"}
      </div>

      {hidden && (
        <div
          className="rounded-[4px] border border-[#f5a623]/30 bg-[#fffbea] px-3 py-2 flex items-center gap-2"
          data-testid="lj-hidden-notice"
        >
          <EyeOff size={14} className="text-[#f5a623]" />
          <span className="text-[11px] text-[#667085]">
            The Mentor view (recommendation, confidence, strategy) stays hidden
            until you submit your decision.
          </span>
        </div>
      )}

      <NewTradeDialog
        open={journalOpen}
        onClose={() => setJournalOpen(false)}
        initialSymbol={study.symbol}
      />
    </div>
  );
}

function DataQualityTag({ quality }: { quality: "Complete" | "Partial" }) {
  const complete = quality === "Complete";
  return (
    <span
      data-testid="lj-data-quality"
      className={`flex items-center gap-1 px-2 py-0.5 rounded-[3px] text-[10px] font-mono uppercase tracking-widest border ${
        complete
          ? "text-[#26a69a] bg-[#26a69a]/10 border-[#26a69a]/30"
          : "text-[#f5a623] bg-[#f5a623]/10 border-[#f5a623]/30"
      }`}
    >
      <ShieldCheck size={11} />
      {complete ? "All indicators available" : "Partial indicators"}
    </span>
  );
}

function QuickSnapshot({
  study,
}: {
  study: LearningJourneyData;
}) {
  const metrics: {
    label: string;
    value: string;
    tone?: string;
    help?: React.ReactNode;
    hint?: string;
  }[] = [
    {
      label: "EMA20",
      value: money(study.ema20),
      hint: priceVs(study.price, study.ema20),
      help: (
        <MetricHelp
          metric="ema20"
          context={{ value: study.ema20, price: study.price }}
          testId="lj-ema20-help"
        />
      ),
    },
    {
      label: "EMA50",
      value: money(study.ema50),
      hint: priceVs(study.price, study.ema50),
      help: (
        <MetricHelp
          metric="ema50"
          context={{ value: study.ema50, price: study.price }}
          testId="lj-ema50-help"
        />
      ),
    },
    {
      label: "EMA200",
      value: money(study.ema200),
      hint: priceVs(study.price, study.ema200),
      help: (
        <MetricHelp
          metric="ema200"
          context={{ value: study.ema200, price: study.price }}
          testId="lj-ema200-help"
        />
      ),
    },
    {
      label: "RSI",
      value: notAvailable(study.rsi) ? "Not available" : study.rsi!.toFixed(1),
      help: (
        <MetricHelp metric="rsi" context={{ value: study.rsi }} testId="lj-rsi-help" />
      ),
    },
    {
      label: "VWAP",
      value: money(study.vwap),
      hint: notAvailable(study.vwap) ? undefined : "20-session avg",
    },
    {
      label: "Volume",
      value:
        notAvailable(study.volume) ? "Not available" : study.volume!.toLocaleString("en-IN"),
    },
    {
      label: "Support",
      value: money(study.support),
      tone: "up",
    },
    {
      label: "Resistance",
      value: money(study.resistance),
      tone: "down",
    },
  ];

  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4" data-testid="lj-quick-snapshot">
      <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-3">
        Quick snapshot
      </div>
      <div className="grid grid-cols-1 gap-2">
        {metrics.map((m) => (
          <div
            key={m.label}
            className="flex items-center justify-between rounded-[3px] border border-[#D9DDE2] bg-[#F6F7F5] px-3 py-2"
          >
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] text-[#667085]">{m.label}</span>
              {m.help}
            </div>
            <div className="text-right">
              <div
                data-testid={`lj-metric-${m.label.toLowerCase()}`}
                className={`font-mono tabular-nums text-sm font-${m.tone === "up" ? "semibold text-[#26a69a]" : m.tone === "down" ? "semibold text-[#ef5350]" : "medium text-[#1F2933]"}`}
              >
                {m.value}
              </div>
              {m.hint && (
                <div className={`text-[10px] font-mono ${m.hint.startsWith("Price") ? "text-[#667085]" : ""}`}>
                  {m.hint}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function priceVs(price: number | null | undefined, ema: number | null | undefined): string {
  if (notAvailable(price) || notAvailable(ema)) return "";
  const above = price! > ema!;
  return `Price ${above ? "above" : "below"} EMA`;
}

function DecisionForm({
  decision,
  setDecision,
  thesis,
  setThesis,
  invalidation,
  setInvalidation,
  onSubmit,
  disabled,
}: {
  decision: UserDecision | null;
  setDecision: (d: UserDecision | null) => void;
  thesis: string;
  setThesis: (v: string) => void;
  invalidation: string;
  setInvalidation: (v: string) => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  return (
    <div className="rounded-[4px] border border-[#2962ff]/25 bg-[#2962ff]/[0.04] p-4" data-testid="lj-decision-form">
      <div className="text-[10px] uppercase tracking-widest text-[#2962ff] font-semibold mb-1">
        Your Turn
      </div>
      <h3 className="text-base text-[#1F2933] font-semibold tracking-tight">
        What would you do?
      </h3>

      <div className="mt-3 flex flex-wrap gap-2" data-testid="lj-decision-options">
        {DECISION_OPTIONS.map((opt) => (
          <button
            key={opt}
            onClick={() => setDecision(opt)}
            data-testid={`lj-decision-${opt}`}
            className={`px-4 py-2 rounded-[4px] border text-sm font-medium transition-colors ${
              decision === opt
                ? "bg-[#2962ff] border-[#2962ff] text-white"
                : "bg-white border-[#D9DDE2] text-[#1F2933] hover:border-[#2962ff]/40 hover:bg-[#2962ff]/5"
            }`}
          >
            {journalDecisionLabels[opt]}
          </button>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3">
        <label className="block">
          <span className="text-[11px] text-[#667085]">My Thesis</span>
          <span className="text-[10px] text-[#C5CAD3]"> · encouraged</span>
          <textarea
            value={thesis}
            onChange={(e) => setThesis(e.target.value)}
            data-testid="lj-thesis"
            placeholder="What do you believe will happen, and why?"
            className="mt-1 w-full rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-2 text-sm text-[#1F2933] placeholder:text-[#667085] focus:border-[#2962ff]/60 focus:outline-none transition-colors resize-y"
            rows={2}
          />
        </label>
        <label className="block">
          <span className="text-[11px] text-[#667085]">My Invalidation</span>
          <span className="text-[10px] text-[#C5CAD3]"> · encouraged</span>
          <textarea
            value={invalidation}
            onChange={(e) => setInvalidation(e.target.value)}
            data-testid="lj-invalidation"
            placeholder="What would prove your thesis wrong?"
            className="mt-1 w-full rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-2 text-sm text-[#1F2933] placeholder:text-[#667085] focus:border-[#2962ff]/60 focus:outline-none transition-colors resize-y"
            rows={2}
          />
        </label>
      </div>

      <div className="mt-4 flex items-center gap-3 flex-wrap">
        <button
          onClick={onSubmit}
          disabled={disabled}
          data-testid="lj-submit"
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            disabled
              ? "bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed"
              : "bg-[#26a69a] hover:bg-[#26a69a]/80 text-white"
          }`}
        >
          Submit My Decision
        </button>
        {disabled && (
          <span className="text-[11px] text-[#667085]">
            Choose a decision to continue.
          </span>
        )}
      </div>
    </div>
  );
}

function ComparisonAndLearning({
  stage,
  decision,
  recommendation,
  debrief,
  onGoLearning,
  onStartAnother,
  onDashboard,
}: {
  stage: Stage;
  decision: UserDecision | null;
  recommendation: LearningJourneyData["recommendation"];
  debrief: NonNullable<ReturnType<typeof buildDebrief>>;
  onGoLearning: () => void;
  onStartAnother: () => void;
  onDashboard: () => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4" data-testid="lj-comparison">
        <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
          Comparison
        </div>
        <h3 className="text-base text-[#1F2933] font-semibold tracking-tight mb-3">
          Your Decision · vs · Mentor View
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="rounded-[4px] border border-[#2675D9]/30 bg-[#2675D9]/[0.06] p-3" data-testid="lj-your-side">
            <div className="text-[10px] uppercase tracking-widest text-[#2962ff] mb-1">
              Your Decision
            </div>
            <div className="text-lg font-mono font-semibold text-[#1F2933]">
              {decision ? journalDecisionLabels[decision] : "—"}
            </div>
          </div>
          <div className="rounded-[4px] border border-[#26a69a]/30 bg-[#26a69a]/[0.06] p-3" data-testid="lj-mentor-side">
            <div className="text-[10px] uppercase tracking-widest text-[#26a69a] mb-1">
              Mentor View
            </div>
            <div className="text-lg font-mono font-semibold text-[#1F2933]">
              {recommendation ? recommendation.action : "No view"}
            </div>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-3">
          <Point title="Where you agreed">{debrief.whereAgreed}</Point>
          <Point title="What you missed">{debrief.whatMissed}</Point>
          <Point title="Thesis quality">{debrief.thesisQuality}</Point>
          <Point title="Evidence quality">{debrief.evidenceQuality}</Point>
          <Point title="Invalidation quality">{debrief.invalidationQuality}</Point>
          <Point title="Why the Mentor reached its conclusion">{debrief.whyMentor}</Point>
          <Point title="What evidence would change the Mentor's view">
            {debrief.whatWouldChange}
          </Point>
        </div>

        {stage === "compare" && (
          <button
            onClick={onGoLearning}
            data-testid="lj-go-learning"
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded bg-[#2962ff] hover:bg-[#2962ff]/80 text-white text-sm font-medium transition-colors"
          >
            See My Key Learning <ArrowRight size={14} />
          </button>
        )}
      </div>

      {stage === "learn" && (
        <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4" data-testid="lj-learning">
          <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
            Your Key Learning
          </div>
          <h3 className="text-base text-[#1F2933] font-semibold tracking-tight mb-3">
            What to take into next time
          </h3>
          <div className="grid grid-cols-1 gap-3">
            <Point title="What went well">{debrief.learning.wentWell}</Point>
            <Point title="What could be improved">{debrief.learning.couldImprove}</Point>
            <Point title="What to watch next time">{debrief.learning.watchNext}</Point>
            <Point title="Evidence to pay more attention to">
              {debrief.learning.payAttention}
            </Point>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button
              onClick={onStartAnother}
              data-testid="lj-study-another"
              className="px-4 py-2 rounded bg-[#2962ff] hover:bg-[#2962ff]/80 text-white text-sm font-medium transition-colors"
            >
              Study Another Stock
            </button>
            <button
              onClick={onStartAnother}
              data-testid="lj-back-to-journey"
              className="px-4 py-2 rounded border border-[#D9DDE2] bg-white text-[#1F2933] text-sm font-medium hover:bg-[#F0F1EF] transition-colors"
            >
              Back to Guided Research
            </button>
            <button
              onClick={onDashboard}
              data-testid="lj-go-dashboard"
              className="px-4 py-2 rounded border border-[#D9DDE2] bg-white text-[#1F2933] text-sm font-medium hover:bg-[#F0F1EF] transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Point({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-[#F6F7F5] px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-[#667085] mb-1">
        {title === "What went well" || title === "Where you agreed" ? (
          <TrendingUp size={11} className="text-[#26a69a]" />
        ) : title === "What could be improved" || title === "What you missed" ? (
          <TrendingDown size={11} className="text-[#ef5350]" />
        ) : (
          <Compass size={11} className="text-[#2962ff]" />
        )}
        {title}
      </div>
      <p className="text-[13px] text-[#1F2933] leading-relaxed">{children}</p>
    </div>
  );
}
