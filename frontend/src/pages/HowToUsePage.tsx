import { InfoCard, InfoSection } from "@/components/layout/InfoPageLayout";
import { TRADELENS_MENTOR } from "@/lib/mentorPresentation";

const ACTIONS = [
  {
    name: "Strong Buy",
    meaning: `Multiple independent signals align constructively. ${TRADELENS_MENTOR} sees a strong educational case for studying an entry — still not a guarantee of profit.`,
  },
  {
    name: "Buy",
    meaning: `The evidence leans positive, but ${TRADELENS_MENTOR} still expects you to confirm structure and risk before acting.`,
  },
  {
    name: "Watch",
    meaning: `Something interesting is developing. ${TRADELENS_MENTOR} suggests observing price behaviour and waiting for clearer confirmation.`,
  },
  {
    name: "Wait",
    meaning:
      "Conditions are mixed or incomplete. Patience is part of the lesson — forcing a trade here is usually low quality.",
  },
  {
    name: "Avoid",
    meaning:
      "The technical picture is weak or unfavourable. The learning goal is to recognise when staying away is the better decision.",
  },
];

export default function HowToUsePage() {
  return (
    <div data-testid="how-to-use-page">
      <InfoSection title="What TradeLens is">
        <p>
          TradeLens is an educational decision-support platform for Indian markets. It
          combines market data, structured analysis, and {TRADELENS_MENTOR} explanations to help you
          understand <em>how</em> experienced traders evaluate a stock — not to tell you
          what to buy or sell.
        </p>
        <p>
          Think of it as a patient guide: it shows evidence, explains trade-offs, and
          encourages disciplined thinking.
        </p>
      </InfoSection>

      <InfoSection title="What TradeLens is not">
        <ul className="list-disc pl-5 space-y-2">
          <li>A brokerage or order-execution platform</li>
          <li>A stock-tipping service or guaranteed-return product</li>
          <li>Personalized investment advice tailored to your financial situation</li>
          <li>A prediction engine that knows what the market will do next</li>
        </ul>
      </InfoSection>

      <InfoSection title="Navigating the application">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 not-prose">
          <InfoCard title="Dashboard">
            Start here. Review featured learning opportunities, your watchlist, and the
            stock you are studying. Select a symbol to open its chart and {TRADELENS_MENTOR} view.
          </InfoCard>
          <InfoCard title="Learn">
            You are here. Read how to interpret {TRADELENS_MENTOR} classifications, trends, and the
            Learn Why experience.
          </InfoCard>
          <InfoCard title="Community">
            A learning hub for questions, concepts, and shared study — not stock tips.
          </InfoCard>
          <InfoCard title="Watchlist & Journal">
            Track symbols you want to study and reflect on paper trades over time.
          </InfoCard>
        </div>
      </InfoSection>

      <InfoSection title="Using the dashboard">
        <ol className="list-decimal pl-5 space-y-2">
          <li>Scan Today&apos;s Learning Opportunities for stocks worth studying today.</li>
          <li>Click a card to load its chart and {TRADELENS_MENTOR} classification on the right.</li>
          <li>Use <strong className="text-[#1F2933]">Learn Why</strong> to see the evidence behind the classification.</li>
          <li>Add interesting symbols to your watchlist from the header search.</li>
        </ol>
      </InfoSection>

      <InfoSection title={`${TRADELENS_MENTOR} classifications (educational context)`}>
        <div className="grid grid-cols-1 gap-2 not-prose">
          {ACTIONS.map((action) => (
            <InfoCard key={action.name} title={action.name} accent="border-l-[#2962ff]">
              <p>{action.meaning}</p>
            </InfoCard>
          ))}
        </div>
      </InfoSection>

      <InfoSection title="What Trend means">
        <p>
          Trend describes the directional bias suggested by the technical evidence — bullish,
          bearish, or neutral. It helps you read whether price structure currently supports
          upside, downside, or balance. Trend is context for learning, not a forecast.
        </p>
      </InfoSection>

      <InfoSection title="Using Learn Why">
        <p>
          Learn Why opens the {TRADELENS_MENTOR} reasoning: what the system sees, supporting
          evidence, risks, and what a learner should take away. Use it to practice
          connecting indicators to conclusions — the same skill experienced traders develop
          over time.
        </p>
      </InfoSection>

      <InfoSection title="How to learn from TradeLens">
        <ul className="list-disc pl-5 space-y-2">
          <li>Ask &quot;what evidence supports this view?&quot; before acting.</li>
          <li>Compare the {TRADELENS_MENTOR} explanation with the chart and key levels.</li>
          <li>Notice when Wait or Avoid is the more disciplined answer.</li>
          <li>Record your thinking in the Trading Journal — learning compounds through reflection.</li>
        </ul>
      </InfoSection>
    </div>
  );
}
