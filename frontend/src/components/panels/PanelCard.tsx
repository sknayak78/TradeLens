import type { ReactNode } from "react";

interface PanelCardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  testId?: string;
}

export default function PanelCard({
  title,
  subtitle,
  action,
  children,
  className = "",
  testId,
}: PanelCardProps) {
  return (
    <section
      data-testid={testId}
      className={`bg-[#1e222d] border border-[#2a2e39] rounded-[4px] flex flex-col min-w-0 ${className}`}
    >
      <header className="px-4 pt-3 pb-2 flex items-center justify-between border-b border-[#2a2e39]">
        <div className="min-w-0">
          <h2 className="text-white text-xs font-semibold uppercase tracking-[0.14em]">
            {title}
          </h2>
          {subtitle && (
            <p className="text-[11px] text-[#787b86] mt-0.5">{subtitle}</p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <div className="p-4 flex-1 min-w-0">{children}</div>
    </section>
  );
}
