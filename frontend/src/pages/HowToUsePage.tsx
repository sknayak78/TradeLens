import { InfoCard, InfoSection } from "@/components/layout/InfoPageLayout";
import { TRADELENS_MENTOR } from "@/lib/mentorPresentation";

const MENTOR_ACTIONS = [
  {
    name: "Strong Buy",
    summary: "Multiple independent signals align constructively.",
    detail: `${TRADELENS_MENTOR} sees a strong educational case for studying an entry. This is not a guarantee of profit — it means the technical picture is unusually supportive for learning about a potential setup.`,
    contrast: "Stronger conviction than Buy; still requires your own risk check.",
  },
  {
    name: "Buy",
    summary: "The evidence leans positive, but confirmation still matters.",
    detail: "Trend and structure look constructive, yet you should still confirm risk, levels, and your own plan before acting.",
    contrast: "More constructive than Watch; less emphatic than Strong Buy.",
  },
  {
    name: "Watch",
    summary: "Something interesting is developing — observe first.",
    detail: "The setup may improve if price comes to a better level or structure tightens. The lesson is patience and observation.",
    contrast: "More engaged than Wait; you are tracking a developing case, not sitting out entirely.",
  },
  {
    name: "Wait",
    summary: "Conditions are mixed or incomplete.",
    detail: "Forcing a trade here is usually low quality. Sitting on your hands is a valid position while evidence improves.",
    contrast: "Less constructive than Watch; more neutral than Avoid.",
  },
  {
    name: "Avoid",
    summary: "The technical picture is weak or unfavourable for a fresh entry.",
    detail: "The learning goal is recognising when staying away is the more disciplined decision — especially for beginners.",
    contrast: "The most cautious fresh-entry view; not a comment on the company forever.",
  },
];

export default function HowToUsePage() {
  return (
    <div data-testid="how-to-use-page" className="space-y-2">
      <InfoSection title="A. Getting Started">
        <p>
          TradeLens is a learning and decision-support platform for Indian markets. It
          combines market data, structured analysis, and {TRADELENS_MENTOR} explanations
          to help you understand <em>how</em> experienced traders evaluate a stock — not
          to tell you what to buy or sell.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 not-prose mt-3">
          <InfoCard title="Dashboard" accent="border-l-[#2962ff]">
            Your home base. Review Today&apos;s Learning Opportunities, study a stock&apos;s
            chart, and read the {TRADELENS_MENTOR} view for the symbol you select.
          </InfoCard>
          <InfoCard title="Watchlist" accent="border-l-[#2962ff]">
            Track symbols you want to study over time. Compare price, RSI, EMA20 and trend
            at a glance.
          </InfoCard>
          <InfoCard title="Trading Journal" accent="border-l-[#2962ff]">
            Log paper or real trades, review outcomes, and build the habit of honest
            reflection after every decision.
          </InfoCard>
          <InfoCard title={TRADELENS_MENTOR} accent="border-l-[#2962ff]">
            A structured guide that translates technical evidence into plain language —
            including when the best lesson is to wait. It is not a prediction engine.
          </InfoCard>
        </div>
        <p className="mt-3 text-[#667085] text-sm">
          TradeLens helps you learn disciplined decision-making. It does not guarantee
          trading outcomes.
        </p>
      </InfoSection>

      <InfoSection title="B. Understanding Technical Indicators">
        <MetricGuide
          title="RSI (Relative Strength Index)"
          what="A momentum indicator on a 0–100 scale that measures the strength of recent price movements."
          indicates="Higher readings often suggest stronger recent buying momentum; lower readings suggest weaker momentum. Readings above ~70 can mean momentum is strong but stretched; below ~30 can mean selling pressure has been heavy."
          use="Use RSI to sense momentum — not as a standalone buy/sell rule. Combine it with trend, support/resistance, and the Mentor view."
          avoid="Do not assume RSI above 70 always means sell, or below 30 always means buy. Trends can stay overbought or oversold for extended periods."
        />
        <MetricGuide
          title="EMA20 (20-day Exponential Moving Average)"
          what="A short-term average price that gives more weight to recent sessions."
          indicates="When price trades above EMA20, short-term momentum is often supportive. Below EMA20 can mean recent momentum has softened."
          use="Compare the current price to EMA20 when reading trend and pullback behaviour on the chart."
          avoid="A single close above or below EMA20 is not a complete trade plan. Context from EMA50 and structure matters."
        />
        <MetricGuide
          title="EMA50 (50-day Exponential Moving Average)"
          what="A medium-term average that smooths price over roughly ten trading weeks."
          indicates="Price above EMA50 often aligns with a healthier medium-term trend; below can signal caution on the intermediate timeframe."
          use="Read EMA50 together with EMA20 — alignment can strengthen the trend story; divergence can signal transition."
          avoid="EMA50 alone does not predict the next move. It is one line of evidence among several."
        />
      </InfoSection>

      <InfoSection title="C. Support & Resistance">
        <MetricGuide
          title="Support"
          what="A price zone where buying interest has historically appeared, slowing or pausing declines."
          indicates="Price holding above support can provide a buffer before the next test of that level."
          use="Use support to think about downside risk and where your thesis might be wrong."
          avoid="Support levels are identified from past behaviour — they can break without warning."
        />
        <MetricGuide
          title="Resistance"
          what="A price zone where selling pressure has historically appeared, slowing or pausing advances."
          indicates="Price approaching resistance may slow down; a clean break with follow-through can change the picture."
          use="Use resistance to judge how much upside room a setup may have before the next hurdle."
          avoid="Resistance is not a fixed ceiling. Markets can gap, news can override technical levels."
        />
      </InfoSection>

      <InfoSection title='D. Sufficient Headroom'>
        <p>
          <strong className="text-[#1F2933]">Headroom</strong> is the percentage distance
          from the current price up to the next resistance level. TradeLens describes
          setups with enough room as having &quot;sufficient headroom.&quot;
        </p>
        <ul className="list-disc pl-5 space-y-2 mt-2">
          <li>More headroom can make a setup more attractive because price has space to move before the next hurdle.</li>
          <li>Thin headroom does not forbid a trade — it means upside may be limited relative to the risk.</li>
          <li>Headroom is calculated from available price and resistance data — it is not a forecast.</li>
        </ul>
      </InfoSection>

      <InfoSection title="E. Risk / Reward">
        <p>
          Every trade has <strong className="text-[#1F2933]">risk</strong> (how much you
          might lose if wrong) and <strong className="text-[#1F2933]">potential reward</strong>{" "}
          (how much you might gain if right). The{" "}
          <strong className="text-[#1F2933]">risk/reward ratio</strong> compares these.
        </p>
        <p>
          TradeLens Mentor may highlight when the ratio is below its preferred minimum.
          That means the estimated reward may not justify the estimated downside for
          this setup — a learning signal to pause and reconsider, not a command.
        </p>
        <p className="text-[#667085] text-sm">
          A favourable ratio does not guarantee profit. An unfavourable ratio does not
          mean the stock cannot rise — it means the geometry of the setup is less
          attractive for disciplined entries.
        </p>
      </InfoSection>

      <InfoSection title={`F. ${TRADELENS_MENTOR} Actions`}>
        <p className="mb-3">
          These classifications describe what the available technical evidence suggests
          for learning. They are not personalized investment advice or trade instructions.
        </p>
        <div className="grid grid-cols-1 gap-2 not-prose">
          {MENTOR_ACTIONS.map((action) => (
            <InfoCard key={action.name} title={action.name} accent="border-l-[#2962ff]">
              <p className="font-medium text-[#1F2933]">{action.summary}</p>
              <p className="mt-1">{action.detail}</p>
              <p className="mt-2 text-[#667085] text-xs">{action.contrast}</p>
            </InfoCard>
          ))}
        </div>
      </InfoSection>

      <InfoSection title="G. Reading a Technical Picture">
        <p>
          Experienced traders rarely act on a single indicator. TradeLens encourages you
          to combine:
        </p>
        <ul className="list-disc pl-5 space-y-1 mt-2">
          <li>Current price and recent trend</li>
          <li>RSI for momentum context</li>
          <li>EMA20 and EMA50 for short/medium-term structure</li>
          <li>Support and resistance for risk geometry</li>
          <li>Headroom before the next resistance hurdle</li>
          <li>Risk/reward when a trading plan is available</li>
          <li>The {TRADELENS_MENTOR} view synthesising the evidence</li>
        </ul>
        <p className="mt-3 font-medium text-[#1F2933]">
          Do not make a decision from one metric. Look at the overall picture.
        </p>
        <p className="mt-2 text-sm text-[#667085]">
          On the Dashboard and stock detail screens, tap the ⓘ icons next to metrics for
          concise contextual explanations using live values where available.
        </p>
      </InfoSection>
    </div>
  );
}

function MetricGuide({
  title,
  what,
  indicates,
  use,
  avoid,
}: {
  title: string;
  what: string;
  indicates: string;
  use: string;
  avoid: string;
}) {
  return (
    <div className="rounded-[4px] border border-[#D9DDE2] bg-white p-4 mb-3 not-prose">
      <h3 className="text-sm font-semibold text-[#1F2933] mb-2">{title}</h3>
      <dl className="space-y-2 text-sm text-[#1F2933]">
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-[#667085]">What is it?</dt>
          <dd className="mt-0.5">{what}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-[#667085]">What does the value generally indicate?</dt>
          <dd className="mt-0.5">{indicates}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-[#667085]">How can I use it?</dt>
          <dd className="mt-0.5">{use}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-widest text-[#667085]">What should I NOT conclude?</dt>
          <dd className="mt-0.5 text-[#667085]">{avoid}</dd>
        </div>
      </dl>
    </div>
  );
}
