# TradeLens — Product Vision

## The one question

TradeLens exists to answer a single question for a novice Indian trader:

> **Is this a good time to buy this stock today?**

Everything else — charts, indicators, scores — is supporting evidence. If a
feature does not help answer that question, it is decoration.

## Who we build for

A beginner with a full-time job and a demat account. They have seen RSI and
moving averages mentioned online but cannot trade off them. They do not want a
dashboard of numbers; they want the judgement of an experienced trader, in
plain English, with the reasoning shown.

## Principles

1. **Decision quality over indicator visibility.** Optimise for the quality of
   the decision the user makes, not for how many indicators we can display.
2. **Human-centric, not indicator-centric.** Describe what buyers and sellers
   are doing and what it means. A number appears only when it is a price the
   user can act on — an entry, an exit, a level to watch.
3. **One authoritative answer.** The Recommendation Engine is the single source
   of truth for the verdict. Legacy analysis fields may remain on the API for
   compatibility, but they must never influence or contradict it.
4. **Explain the downside first.** Every recommendation states what could go
   wrong and where the idea fails, before it states the upside.
5. **Honest confidence.** Confidence is TradeLens' confidence in its own call,
   never the probability of a profitable trade, and it is never 100%.
6. **Deterministic and reproducible.** The same market snapshot always produces
   the same recommendation. No LLM, no randomness, no hidden clock.
7. **Degrade loudly.** When data is incomplete, say so and lower confidence
   rather than quietly issuing a weaker recommendation as if it were sound.

## The five questions

A novice must be able to answer all five within 30 seconds of opening a stock:

1. Should I buy today? → `recommendation.action`, `recommendation.verdict`
2. Why? → `recommendation.summary`, `why[]`, `positives[]`
3. At what price should I enter? → `recommendation.levels.entryMin/entryMax`
4. What is my downside risk? → `recommendation.levels.stopLoss`, `risks[]`
5. What should I watch before entering? → `recommendation.nextTrigger`

## Scope of the Recommendation Engine

The engine answers "should I *initiate* a position today?". It has no portfolio
context, so it never returns a position-management verdict. Its allowed actions
are **Strong Buy, Buy, Watch, Wait and Avoid**.

Hold, Add More, Book Profit and Exit are reserved for a future **Portfolio
Advisor** module, which will have entry price, quantity and holding duration.

## What we will not do

- Present a wall of indicator readings and call it analysis.
- Imply certainty, guarantee outcomes, or quote a probability of profit.
- Recommend an entry we cannot attach an exit to.
- Let a seeded or legacy field silently change a recommendation.
