import { NavLink, Outlet } from "react-router-dom";
import InfoPageLayout from "@/components/layout/InfoPageLayout";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";

const TABS = [
  { to: "/learn", label: "How to Use", end: true },
  { to: "/learn/vision", label: "Founder's Vision", end: false },
];

export default function LearnHubPage() {
  return (
    <div data-testid="learn-hub-page" className="min-h-full">
      <InfoPageLayout
        title="Learn"
        subtitle="Understand how TradeLens helps you learn disciplined, evidence-based thinking — not follow tips."
        testId="learn-hub-header"
      >
        <nav
          className="flex flex-wrap gap-2 mb-6"
          data-testid="learn-hub-nav"
          aria-label="Learn sections"
        >
          {TABS.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  "px-3 py-1.5 rounded-[4px] border text-xs font-semibold uppercase tracking-wider transition-colors",
                  isActive
                    ? "bg-[#2962ff]/15 text-white border-[#2962ff]/40"
                    : "text-[#787b86] border-[#2a2e39] hover:text-[#d1d4dc] hover:border-[#3a3f4b]",
                ].join(" ")
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <Outlet />
        <div className="mt-8">
          <EducationalDisclaimer />
        </div>
      </InfoPageLayout>
    </div>
  );
}
