import {
  BookOpen,
  Brain,
  Compass,
  Eye,
  Lightbulb,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
} from "lucide-react";
import { InfoCard } from "@/components/layout/InfoPageLayout";
import { TRADELENS_MENTOR } from "@/lib/mentorPresentation";

const PRINCIPLES = [
  {
    title: "Discipline",
    description:
      "The best traders know when not to act. TradeLens celebrates patience as much as opportunity.",
    icon: Shield,
    accent: "border-l-[#26a69a]",
  },
  {
    title: "Explainability",
    description:
      "Every classification comes with reasoning you can read, question, and learn from.",
    icon: Lightbulb,
    accent: "border-l-[#2962ff]",
  },
  {
    title: "Learning",
    description:
      "The goal is not to follow signals — it is to understand why a view makes sense.",
    icon: BookOpen,
    accent: "border-l-[#f5a623]",
  },
  {
    title: "Risk awareness",
    description:
      "Support, resistance, and risk–reward are explained so you see downside before upside.",
    icon: Target,
    accent: "border-l-[#ef5350]",
  },
  {
    title: "Reflection",
    description:
      "The Trading Journal turns every trade into a lesson — wins and losses alike.",
    icon: Brain,
    accent: "border-l-[#667085]",
  },
];

export default function FoundersVisionPage() {
  return (
    <div data-testid="founders-vision-page" className="space-y-8">
      {/* Hero */}
      <section className="rounded-[6px] border border-[#D9DDE2] bg-gradient-to-br from-[#2962ff]/8 via-white to-[#26a69a]/5 p-6 md:p-8">
        <div className="flex items-start gap-4">
          <div className="hidden sm:flex w-12 h-12 rounded-[6px] bg-[#2962ff]/15 border border-[#2962ff]/30 items-center justify-center shrink-0">
            <Sparkles size={22} className="text-[#2962ff]" />
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-widest text-[#2962ff] font-semibold mb-2">
              Founder&apos;s Vision
            </p>
            <h2 className="text-[#1F2933] text-xl md:text-2xl font-semibold leading-snug max-w-2xl">
              Understand before you act. Learn before you trade.
            </h2>
            <p className="text-sm text-[#667085] leading-relaxed mt-3 max-w-2xl">
              TradeLens exists to help Indian market learners build disciplined,
              evidence-based thinking — not to hand out tips or chase the next hot stock.
            </p>
          </div>
        </div>
      </section>

      {/* Why TradeLens exists */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Compass size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">Why TradeLens exists</h2>
        </div>
        <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-5 space-y-3">
          <p className="text-sm text-[#1F2933] leading-relaxed">
            Information about markets is everywhere, but understanding is rare. Many learners
            consume tips, indicators, and opinions — and still lack confidence in their own
            decisions.
          </p>
          <p className="text-sm text-[#1F2933] leading-relaxed">
            The goal is not to create better followers. The goal is to help you develop
            disciplined, evidence-based thinking about trading — so every decision feels
            considered, not random.
          </p>
        </div>
      </section>

      {/* The TradeLens Mentor */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Eye size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">The {TRADELENS_MENTOR}</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <InfoCard title="What it does" accent="border-l-[#2962ff]">
            <p>
              {TRADELENS_MENTOR} guides, explains, highlights risks, and encourages reflection.
              It translates technical evidence into plain language — including when the best
              lesson is to wait.
            </p>
          </InfoCard>
          <InfoCard title="What it is not" accent="border-l-[#ef5350]">
            <p>
              It is not a fortune-teller or a guaranteed prediction engine. Classifications
              like Strong Buy, Watch, or Avoid describe what the evidence suggests for
              learning — not instructions to trade.
            </p>
          </InfoCard>
        </div>
      </section>

      {/* Learn before you act */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <BookOpen size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">Learn before you act</h2>
        </div>
        <p className="text-sm text-[#1F2933] leading-relaxed">
          Tips and signals can look authoritative, but they rarely teach you <em>why</em> a
          view makes sense. Without that foundation, every loss feels random and every win
          feels lucky. TradeLens closes that gap by explaining market behaviour and
          encouraging patience when evidence is incomplete.
        </p>
      </section>

      {/* From signals to understanding */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">
            From signals to understanding
          </h2>
        </div>
        <p className="text-sm text-[#1F2933] leading-relaxed mb-3">
          Experienced traders rarely act on a single indicator. They read trend, structure,
          risk, and context together. TradeLens mirrors that process:
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            "Technical signals are evaluated together, not in isolation.",
            "Results are translated into readable explanations with actual values.",
            "You practise connecting evidence to conclusions — the same skill traders develop over years.",
          ].map((text) => (
            <div
              key={text}
              className="rounded-[4px] border border-[#D9DDE2] bg-[#F0F1EF] px-4 py-3 text-sm text-[#1F2933] leading-relaxed"
            >
              {text}
            </div>
          ))}
        </div>
      </section>

      {/* Principles */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Shield size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">Principles we believe in</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PRINCIPLES.map(({ title, description, icon: Icon, accent }) => (
            <InfoCard key={title} title={title} accent={accent}>
              <div className="flex items-start gap-2">
                <Icon size={14} className="text-[#667085] shrink-0 mt-0.5" />
                <p>{description}</p>
              </div>
            </InfoCard>
          ))}
        </div>
      </section>

      {/* Future vision */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={16} className="text-[#2962ff]" />
          <h2 className="text-[#1F2933] text-base font-semibold">Where we are headed</h2>
        </div>
        <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-5 space-y-3">
          <p className="text-sm text-[#1F2933] leading-relaxed">
            Today, TradeLens helps learners study individual stocks with clarity and structure.
            Over time, we will deepen mentoring, journaling, behavioural coaching, and
            community learning.
          </p>
          <p className="text-sm text-[#1F2933] leading-relaxed">
            The north star never changes: build confident, independent traders who understand
            their decisions.
          </p>
        </div>
      </section>

      {/* Personal note */}
      <section className="rounded-[4px] border border-dashed border-[#D9DDE2] bg-[#F0F1EF]/50 p-5">
        <p className="text-sm text-[#1F2933] leading-relaxed italic">
          &ldquo;TradeLens reflects the product I wished existed when I started learning markets:
          honest about uncertainty, committed to teaching before recommending, and focused on
          habits that last longer than any single trade.&rdquo;
        </p>
        <p className="text-sm text-[#667085] mt-3 not-italic">— Sujeet Nayak</p>
      </section>
    </div>
  );
}
