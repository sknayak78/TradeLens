import type { ReactNode } from "react";

interface InfoPageLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  testId?: string;
}

export default function InfoPageLayout({
  title,
  subtitle,
  children,
  testId,
}: InfoPageLayoutProps) {
  return (
    <div data-testid={testId} className="min-h-full">
      <div className="px-4 md:px-6 pt-5 pb-4 border-b border-[#2a2e39]">
        <h1 className="text-white text-xl md:text-2xl font-semibold tracking-tight">
          {title}
        </h1>
        <p className="text-sm text-[#787b86] mt-1 max-w-3xl">{subtitle}</p>
      </div>
      <div className="p-4 md:p-6 max-w-4xl">{children}</div>
    </div>
  );
}

export function InfoSection({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="mb-8">
      <h2 className="text-white text-base font-semibold mb-3">{title}</h2>
      <div className="text-sm text-[#d1d4dc] leading-relaxed space-y-3">
        {children}
      </div>
    </section>
  );
}

export function InfoCard({
  title,
  children,
  accent,
}: {
  title: string;
  children: ReactNode;
  accent?: string;
}) {
  return (
    <div
      className={`rounded-[4px] border border-[#2a2e39] bg-[#1e222d] p-4 ${
        accent ? `border-l-2 ${accent}` : ""
      }`}
    >
      <h3 className="text-white text-sm font-semibold mb-2">{title}</h3>
      <div className="text-sm text-[#d1d4dc] leading-relaxed space-y-2">
        {children}
      </div>
    </div>
  );
}
