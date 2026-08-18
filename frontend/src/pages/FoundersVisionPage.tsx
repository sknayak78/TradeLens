import { InfoSection } from "@/components/layout/InfoPageLayout";

export default function FoundersVisionPage() {
  return (
    <div data-testid="founders-vision-page">
      <InfoSection title="Why TradeLens exists">
        <p>
          TradeLens began with a simple observation: information about markets is everywhere,
          but understanding is rare. Many learners consume tips, indicators, and opinions —
          and still lack confidence in their own decisions.
        </p>
        <p>
          The goal is not to create better followers. The goal is to help learners develop
          disciplined, evidence-based thinking about trading.
        </p>
      </InfoSection>

      <InfoSection title="The problem with blind tips">
        <p>
          Tips and signals can look authoritative, but they rarely teach you <em>why</em> a
          view makes sense. Without that foundation, every loss feels random and every win
          feels lucky. TradeLens was built to close that gap — by explaining market behaviour
          and encouraging patience when evidence is incomplete.
        </p>
      </InfoSection>

      <InfoSection title="Learning to read evidence">
        <p>
          Experienced traders rarely act on a single indicator. They read trend, structure,
          risk, and context together. TradeLens mirrors that process: the Mentor surfaces
          evidence, names what is missing, and helps you practise interpretation rather than
          memorising calls.
        </p>
      </InfoSection>

      <InfoSection title="The role of the Mentor">
        <p>
          The Mentor is not a fortune-teller. It is a structured guide that translates
          technical evidence into plain language — including when the best lesson is to wait.
          Celebrating patience is as important as recognising opportunity.
        </p>
      </InfoSection>

      <InfoSection title="Where we are headed">
        <p>
          The September launch focuses on helping learners study individual stocks with clarity
          and structure. Over time, TradeLens will deepen mentoring, journaling, behavioural
          coaching, and community learning — always with the same north star: build confident,
          independent traders who understand their decisions.
        </p>
      </InfoSection>

      <InfoSection title="A personal note">
        <p>
          TradeLens reflects the product I wished existed when I started learning markets: honest
          about uncertainty, committed to teaching before recommending, and focused on habits
          that last longer than any single trade.
        </p>
        <p className="text-[#787b86]">— Sujeet Nayak</p>
      </InfoSection>
    </div>
  );
}
