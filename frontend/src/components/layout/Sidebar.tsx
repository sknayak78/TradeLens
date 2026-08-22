import { NavLink } from "react-router-dom";
import {
  BookOpen,
  LayoutDashboard,
  NotebookPen,
  Settings as SettingsIcon,
  Sparkles,
  Star,
  X,
} from "lucide-react";

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard", end: true },
  { to: "/watchlist", label: "Watchlist", icon: Star, testId: "nav-watchlist", end: true },
  { to: "/journal", label: "Trading Journal", icon: NotebookPen, testId: "nav-journal", end: true },
  {
    to: "/how-to-use",
    label: "How to Use TradeLens",
    icon: BookOpen,
    testId: "nav-how-to-use",
    end: true,
  },
  {
    to: "/founders-vision",
    label: "Founder's Vision",
    icon: Sparkles,
    testId: "nav-founders-vision",
    end: true,
  },
  { to: "/settings", label: "Settings", icon: SettingsIcon, testId: "nav-settings", end: true },
];

export default function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  return (
    <>
      <aside
        className="hidden md:flex w-56 flex-shrink-0 border-r border-[#D9DDE2] bg-white flex-col"
        data-testid="sidebar-desktop"
      >
        <SidebarNav onNavigate={() => undefined} />
        <SidebarFooter />
      </aside>

      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 flex"
          data-testid="sidebar-mobile-overlay"
        >
          <div
            className="absolute inset-0 bg-black/60"
            onClick={onCloseMobile}
          />
          <aside className="relative w-64 bg-white border-r border-[#D9DDE2] flex flex-col tl-fade-in">
            <div className="h-14 flex items-center justify-between px-4 border-b border-[#D9DDE2]">
              <span className="text-[#1F2933] text-sm font-semibold tracking-tight">
                Menu
              </span>
              <button
                onClick={onCloseMobile}
                className="p-2 rounded-md hover:bg-[#F0F1EF] text-[#667085]"
                data-testid="mobile-nav-close"
                aria-label="Close menu"
              >
                <X size={18} />
              </button>
            </div>
            <SidebarNav onNavigate={onCloseMobile} />
            <SidebarFooter />
          </aside>
        </div>
      )}
    </>
  );
}

function SidebarNav({ onNavigate }: { onNavigate: () => void }) {
  return (
    <nav className="flex-1 py-3 px-2 space-y-1" data-testid="sidebar-nav">
      <div className="px-3 pb-2 text-[10px] uppercase tracking-widest text-[#667085]">
        Workspace
      </div>
      {NAV_ITEMS.map(({ to, label, icon: Icon, testId, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          data-testid={testId}
          className={({ isActive }) =>
            [
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
              isActive
                ? "bg-[#2962ff]/10 text-[#1F2933] border-l-2 border-[#2962ff] pl-[10px]"
                : "text-[#1F2933] hover:bg-[#F0F1EF] hover:text-[#1F2933] border-l-2 border-transparent pl-[10px]",
            ].join(" ")
          }
        >
          <Icon size={16} strokeWidth={2} />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function SidebarFooter() {
  return (
    <div className="p-3 border-t border-[#D9DDE2]" data-testid="sidebar-footer">
      <div className="rounded-md bg-white border border-[#D9DDE2] p-3">
        <div className="text-[10px] uppercase tracking-widest text-[#667085] mb-1">
          Session
        </div>
        <div className="text-xs text-[#1F2933]">Paper trading · Demo</div>
        <div className="mt-2 flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-[#26a69a] tl-pulse" />
          <span className="text-[10px] font-mono tabular-nums text-[#667085]">
            LIVE FEED · MOCK
          </span>
        </div>
      </div>
    </div>
  );
}
