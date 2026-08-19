import {
  BookOpen,
  MessageCircle,
  MessagesSquare,
  Sparkles,
  Users,
} from "lucide-react";
import InfoPageLayout, { InfoCard, InfoSection } from "@/components/layout/InfoPageLayout";

const DISCUSSION_TOPICS = [
  {
    title: "Reading trend and structure",
    description:
      "Share how you interpret bullish, bearish, and neutral trends on the dashboard. What questions do you ask before trusting a trend label?",
    icon: BookOpen,
    replies: 0,
  },
  {
    title: "When Wait is the right answer",
    description:
      "Discuss moments when the Mentor said Wait or Avoid and what you learned from sitting out. Discipline is a skill worth practising together.",
    icon: Sparkles,
    replies: 0,
  },
  {
    title: "Using Learn Why effectively",
    description:
      "Walk through a stock you studied this week. Which evidence lines matched the chart? What still felt unclear?",
    icon: MessageCircle,
    replies: 0,
  },
  {
    title: "Risk, invalidation, and position sizing",
    description:
      "Explore how support, resistance, and risk levels help you think about downside — without turning the conversation into trade calls.",
    icon: MessagesSquare,
    replies: 0,
  },
];

const GUIDELINES = [
  "This is a learning community — not a stock-tip or execution forum.",
  "Share reasoning and questions, not buy/sell calls for others to follow.",
  "Be respectful. Beginners and experienced learners study here together.",
  "When in doubt, ask how the evidence supports a view — not what to buy tomorrow.",
];

export default function CommunityPage() {
  return (
    <InfoPageLayout
      title="Community Learning Hub"
      subtitle="A place to discuss market concepts, Mentor interpretations, and the habits of disciplined learners."
      testId="community-page"
    >
      <InfoSection title="How this community works">
        <p>
          TradeLens Community is designed for structured learning conversations. Explore
          starter topics below, reflect on your own studies, and prepare for live discussions
          as the platform grows toward the September launch.
        </p>
        <p>
          Full threaded discussions will arrive in a future release. For now, use these
          curated spaces to orient your learning and know where conversations will live.
        </p>
      </InfoSection>

      <InfoSection title="Community guidelines">
        <ul className="list-disc pl-5 space-y-2">
          {GUIDELINES.map((guideline) => (
            <li key={guideline}>{guideline}</li>
          ))}
        </ul>
      </InfoSection>

      <InfoSection title="Starter learning spaces">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 not-prose">
          {DISCUSSION_TOPICS.map((topic) => {
            const Icon = topic.icon;
            return (
              <InfoCard key={topic.title} title={topic.title} accent="border-l-[#2962ff]">
                <div className="flex items-start gap-3">
                  <span className="w-8 h-8 rounded-md bg-[#2962ff]/10 border border-[#2962ff]/25 text-[#2962ff] flex items-center justify-center shrink-0">
                    <Icon size={15} />
                  </span>
                  <div className="min-w-0">
                    <p>{topic.description}</p>
                    <div className="mt-3 flex items-center gap-2 text-[10px] uppercase tracking-widest text-[#667085]">
                      <Users size={11} />
                      <span>Learning space · {topic.replies} replies</span>
                    </div>
                    <button
                      type="button"
                      disabled
                      className="mt-3 px-3 py-1.5 rounded-[4px] border border-[#D9DDE2] text-[11px] uppercase tracking-wider text-[#667085] cursor-not-allowed"
                      title="Discussion threads will open in a future release"
                    >
                      Join conversation (opening soon)
                    </button>
                  </div>
                </div>
              </InfoCard>
            );
          })}
        </div>
      </InfoSection>

      <InfoSection title="Share your learning journey">
        <InfoCard title="Reflection prompt">
          <p>
            What is one thing the Mentor helped you notice this week that you would have
            missed on your own? Save your answer in the Trading Journal today — community
            threads will build on reflections like these.
          </p>
        </InfoCard>
      </InfoSection>
    </InfoPageLayout>
  );
}
