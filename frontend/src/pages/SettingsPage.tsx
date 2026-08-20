import { useEffect, useState } from "react";
import PanelCard from "@/components/panels/PanelCard";
import LoadingState from "@/components/common/LoadingState";
import ErrorState from "@/components/common/ErrorState";
import { useAppSettings } from "@/context/SettingsContext";
import { Info, Check } from "lucide-react";

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

export default function SettingsPage() {
  const { settings, isLoading, isError, error, refetch, update, isUpdating } =
    useAppSettings();

  const [capital, setCapital] = useState<string>("");
  const [risk, setRisk] = useState<string>("");
  const [timeframe, setTimeframe] = useState<string>("1D");
  const [savedAt, setSavedAt] = useState<Date | null>(null);

  useEffect(() => {
    if (settings) {
      setCapital(settings.capital.toString());
      setRisk(settings.risk_per_trade.toString());
      setTimeframe(settings.preferred_timeframe);
    }
  }, [settings]);

  const handleSave = () => {
    const capNum = parseFloat(capital);
    const riskNum = parseFloat(risk);
    update({
      capital: Number.isFinite(capNum) && capNum > 0 ? capNum : undefined,
      risk_per_trade:
        Number.isFinite(riskNum) && riskNum >= 0 && riskNum <= 100
          ? riskNum
          : undefined,
      preferred_timeframe: timeframe,
    });
    setSavedAt(new Date());
  };

  const handleTimeframe = (tf: string) => {
    setTimeframe(tf);
    update({ preferred_timeframe: tf });
    setSavedAt(new Date());
  };

  return (
    <div data-testid="settings-page" className="p-4 md:p-6">
      <div className="mb-4 flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-[#1F2933] text-xl md:text-2xl font-semibold tracking-tight">
            Settings
          </h1>
          <p className="text-xs text-[#667085] mt-1">
            Configure your TradeLens experience — stored in SQLite.
          </p>
        </div>
        {savedAt && (
          <span
            className="inline-flex items-center gap-1.5 text-[10px] font-mono tabular-nums text-[#26a69a] uppercase tracking-widest"
            data-testid="settings-saved-at"
          >
            <Check size={12} /> Saved{" "}
            {savedAt.toLocaleTimeString("en-IN", { hour12: false })}
          </span>
        )}
      </div>

      {isLoading && <LoadingState label="Loading settings" />}
      {isError && !isLoading && (
        <ErrorState
          message={error?.message ?? "Failed to load settings."}
          onRetry={refetch}
          testId="settings-error"
        />
      )}

      {!isLoading && !isError && settings && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PanelCard title="Risk & Capital" testId="settings-risk">
            <Row label="Capital (₹)">
              <input
                type="number"
                min={0}
                step={1000}
                value={capital}
                onChange={(e) => setCapital(e.target.value)}
                data-testid="settings-capital"
                className="w-40 h-8 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] font-mono tabular-nums focus:border-[#2962ff]/50 outline-none"
              />
            </Row>
            <Row label="Risk per Trade (%)" divider>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                value={risk}
                onChange={(e) => setRisk(e.target.value)}
                data-testid="settings-risk-input"
                className="w-40 h-8 px-2 bg-white border border-[#D9DDE2] rounded-md text-sm text-[#1F2933] font-mono tabular-nums focus:border-[#2962ff]/50 outline-none"
              />
            </Row>
            <div className="pt-3 flex justify-end">
              <button
                onClick={handleSave}
                disabled={isUpdating}
                data-testid="settings-save"
                className="px-3 py-1.5 rounded-md bg-[#2962ff] hover:bg-[#2962ff]/85 text-[#1F2933] text-xs uppercase tracking-widest transition-colors disabled:opacity-60"
              >
                {isUpdating ? "Saving…" : "Save Changes"}
              </button>
            </div>
          </PanelCard>

          <PanelCard title="Chart Preferences" testId="settings-preferences">
            <Row label="Default Timeframe">
              <div className="flex flex-wrap gap-2">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => handleTimeframe(tf)}
                    data-testid={`settings-tf-${tf}`}
                    className={`px-2.5 py-1 rounded text-[11px] font-mono uppercase tracking-wider transition-colors border ${
                      timeframe === tf
                        ? "bg-[#2962ff]/15 text-[#1F2933] border-[#2962ff]/40"
                        : "text-[#667085] border-[#D9DDE2] hover:text-[#1F2933]"
                    }`}
                  >
                    {tf}
                  </button>
                ))}
              </div>
            </Row>
          </PanelCard>

          <PanelCard title="Summary" testId="settings-summary">
            <div className="grid grid-cols-3 gap-2 font-mono tabular-nums text-sm">
              <Tile
                label="Capital"
                value={`₹${settings.capital.toLocaleString("en-IN")}`}
              />
              <Tile label="Risk" value={`${settings.risk_per_trade}%`} />
              <Tile label="Timeframe" value={settings.preferred_timeframe} />
            </div>
            <div className="text-[11px] text-[#667085] mt-3">
              Per-trade risk ≈{" "}
              <span className="text-[#1F2933] font-mono tabular-nums">
                ₹
                {(
                  (settings.capital * settings.risk_per_trade) /
                  100
                ).toLocaleString("en-IN", {
                  minimumFractionDigits: 0,
                  maximumFractionDigits: 0,
                })}
              </span>
              .
            </div>
          </PanelCard>

          <PanelCard title="About" testId="settings-about">
            <div className="flex items-start gap-3">
              <Info size={16} className="text-[#667085] mt-0.5 shrink-0" />
              <p className="text-xs text-[#667085] leading-relaxed">
                TradeLens helps you learn how to read the market. Study
                opportunities, understand the evidence, and reflect on your
                trading decisions.
              </p>
            </div>
          </PanelCard>
        </div>
      )}
    </div>
  );
}

function Row({
  label,
  children,
  divider,
}: {
  label: string;
  children: React.ReactNode;
  divider?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between py-3 ${
        divider ? "border-t border-[#D9DDE2]" : ""
      }`}
    >
      <span className="text-sm text-[#1F2933]">{label}</span>
      <div>{children}</div>
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-white px-3 py-2">
      <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
        {label}
      </div>
      <div className="text-[#1F2933] text-sm">{value}</div>
    </div>
  );
}
