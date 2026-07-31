import { useEffect, useState } from "react";
import { getSettings } from "@/services/marketService";
import type { Settings } from "@/types";
import PanelCard from "@/components/panels/PanelCard";
import { Info } from "lucide-react";

const TIMEFRAMES = ["1D", "1W", "1M", "3M", "1Y"];

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);

  useEffect(() => {
    getSettings().then(setSettings);
  }, []);

  if (!settings) return null;

  const update = <K extends keyof Settings>(k: K, v: Settings[K]) =>
    setSettings((s) => (s ? { ...s, [k]: v } : s));

  return (
    <div data-testid="settings-page" className="p-4 md:p-6">
      <div className="mb-4">
        <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
          Settings
        </h1>
        <p className="text-xs text-[#787b86] mt-1">
          Configure your TradeLens experience
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <PanelCard title="Appearance" testId="settings-appearance">
          <Row label="Theme">
            <div className="flex gap-2">
              {(["dark", "light"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => update("theme", t)}
                  data-testid={`settings-theme-${t}`}
                  className={`px-3 py-1.5 rounded-md text-xs uppercase tracking-widest transition-colors border ${
                    settings.theme === t
                      ? "bg-[#2962ff]/15 text-white border-[#2962ff]/40"
                      : "text-[#787b86] border-[#2a2e39] hover:text-[#d1d4dc]"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </Row>
          <Row label="Compact Mode" divider>
            <Toggle
              on={settings.compactMode}
              onChange={(v) => update("compactMode", v)}
              testId="settings-compact"
            />
          </Row>
        </PanelCard>

        <PanelCard title="Data" testId="settings-data">
          <Row label="Default Timeframe">
            <div className="flex flex-wrap gap-2">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  onClick={() => update("defaultTimeframe", tf)}
                  data-testid={`settings-tf-${tf}`}
                  className={`px-2.5 py-1 rounded text-[11px] font-mono uppercase tracking-wider transition-colors border ${
                    settings.defaultTimeframe === tf
                      ? "bg-[#2962ff]/15 text-white border-[#2962ff]/40"
                      : "text-[#787b86] border-[#2a2e39] hover:text-[#d1d4dc]"
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </Row>
          <Row label="Refresh Interval (s)" divider>
            <input
              type="number"
              min={5}
              max={300}
              value={settings.refreshInterval}
              onChange={(e) =>
                update("refreshInterval", parseInt(e.target.value || "30", 10))
              }
              data-testid="settings-refresh"
              className="w-24 h-8 px-2 bg-[#131722] border border-[#2a2e39] rounded-md text-sm text-white font-mono tabular-nums focus:border-[#2962ff]/50 outline-none"
            />
          </Row>
        </PanelCard>

        <PanelCard title="Notifications" testId="settings-notifications">
          <Row label="Alert Notifications">
            <Toggle
              on={settings.notifications}
              onChange={(v) => update("notifications", v)}
              testId="settings-notif"
            />
          </Row>
        </PanelCard>

        <PanelCard title="About" testId="settings-about">
          <div className="flex items-start gap-3">
            <Info size={16} className="text-[#787b86] mt-0.5 shrink-0" />
            <p className="text-xs text-[#787b86] leading-relaxed">
              TradeLens v0.1 · Frontend preview. All data on this dashboard is
              mocked from local JSON. No backend, API, or persistence is
              connected. Save actions here update local state only.
            </p>
          </div>
        </PanelCard>
      </div>
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
        divider ? "border-t border-[#2a2e39]" : ""
      }`}
    >
      <span className="text-sm text-[#d1d4dc]">{label}</span>
      <div>{children}</div>
    </div>
  );
}

function Toggle({
  on,
  onChange,
  testId,
}: {
  on: boolean;
  onChange: (v: boolean) => void;
  testId?: string;
}) {
  return (
    <button
      role="switch"
      aria-checked={on}
      onClick={() => onChange(!on)}
      data-testid={testId}
      className={`relative w-10 h-5 rounded-full transition-colors ${
        on ? "bg-[#2962ff]" : "bg-[#2a2e39]"
      }`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${
          on ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}
