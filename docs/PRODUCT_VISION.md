# TradeLens Product Vision

> The primary reference for product decisions. When a feature request, design
> proposal or implementation choice conflicts with this document, this document
> wins until it is deliberately revised.

**Audience:** engineers, designers and product owners.
**Not** a technical design or architecture document — see
`ARCHITECTURE_DECISIONS.md` for those.

---

## 1. Vision

TradeLens helps retail traders make better **entry decisions** using simple,
explainable technical analysis.

Every screen, field and feature exists to answer one question:

> **"Is this a good time to buy this stock?"**

A user should be able to open TradeLens, look at a single stock, and leave with
a clear answer, the reasoning behind it, and a plan. If a feature does not help
answer that question — or help the user understand the answer — it does not
belong in the product yet.

TradeLens optimises for **decision quality**, not for information volume. A
screen full of accurate indicators that leaves the user unsure what to do is a
product failure, even if every number on it is correct.

---

## 2. Target Users

### Primary: the novice trader

Has opened a broking account recently. Knows that terms like RSI and moving
averages matter, but not what to do when they conflict. Is most at risk of
buying at the wrong moment — chasing a stock that has already run, or averaging
into a falling one.

They need: a verdict, in plain language, with the reasoning attached, and an
explicit statement of what would make the answer change.

### Primary: the intermediate swing trader

Holds positions for days to weeks. Can read a chart and already has a rough
process, but wants a faster, consistent second opinion and a disciplined
framing of entry, stop loss and targets.

They need: speed, consistency, and a visible rationale they can disagree with.
They will not trust a black box, so the reasoning must be inspectable.

### Explicitly not the current focus

Intraday scalpers, options and derivatives traders, and algorithmic traders.
Serving them well would require different data, timeframes and risk models, and
attempting it early would dilute the product for the two personas above.

### Clarity over jargon

Technical vocabulary is never the interface. Where a technical term is used, it
is used *because the user benefits from learning it*, and it is always
accompanied by its interpretation in plain English. "RSI is 78" is data;
"momentum is stretched, so the risk of buying here is elevated" is product.

---

## 3. Product Philosophy

**Recommendation before indicators.**
The recommendation is the headline; indicators are supporting evidence. The user
sees the verdict first and can drill down into the data behind it. We never ask
the user to assemble a conclusion from raw indicators themselves.

**Explain every recommendation.**
A recommendation with no reasoning is not shippable. If the product cannot
articulate *why* in plain language, the recommendation is not ready to be shown.

**Plain English first.**
Write for someone reading their first chart. Prefer "the price is holding above
its recent average" to naming the indicator alone. Precision matters, but
comprehension comes first.

**One recommendation, one source of truth.**
For a given stock at a given moment there is exactly one recommendation, derived
from one consistent dataset. Different parts of the product must never imply
different verdicts, and no screen may compute its own.

**Transparency over complexity.**
Given a choice between a sophisticated model the user cannot follow and a simpler
one they can, TradeLens chooses the one that can be explained. We also disclose
our own limitations: when data is incomplete or a signal is weak, we say so
rather than presenting a confident-looking answer.

**Always explain what to watch next.**
A recommendation is a snapshot, and most snapshots are not "act now". Every
recommendation states the condition that would change it, so the user leaves
with something to monitor rather than a dead end.

---

## 4. Recommendation Framework

Every recommendation TradeLens produces follows the same structure. The
consistency is deliberate: users learn the shape once and can then read any
recommendation quickly.

| Section | Purpose |
| --- | --- |
| **Recommendation** | The action itself — the answer to "is this a good time to buy?" in one or two words. |
| **Verdict** | A one-line plain-English judgement that gives the recommendation its meaning: what kind of situation this is, and how strong it is. |
| **Why** | The evidence, in plain language. The handful of observations that drove the verdict, stated so the user can agree or disagree with each one. |
| **Trading Plan** | What acting on this would concretely look like: where to enter, where the exit sits if the idea fails, and what the realistic upside is. Present only when there is an actionable setup. |
| **Risks** | What could go wrong and what is unfavourable about this setup, including the weaknesses of our own analysis (stretched momentum, thin room to the next resistance, incomplete data). Never omitted to make a recommendation look stronger. |
| **Next Trigger** | The specific, observable condition that would change the recommendation. This turns a "not yet" into a plan to watch. |
| **Beginner Tip** | One piece of durable education tied to this situation, so the user learns something transferable rather than only receiving a verdict. |

The framework is a contract with the user, not a template to be trimmed. When a
section genuinely does not apply — a trading plan for a stock we advise avoiding
— it is omitted rather than filled with filler.

---

## 5. Recommendation Actions

TradeLens uses a deliberately small action vocabulary, because a user who has to
interpret the label has not been helped.

| Action | Meaning to the user |
| --- | --- |
| **Strong Buy** | The setup is favourable and unusually well aligned. Conditions are as good as this framework recognises. |
| **Buy** | A reasonable entry is available now, with an acceptable balance of risk and reward. |
| **Watch** | The situation is promising but the entry is not attractive yet. Track it and wait for the stated trigger. |
| **Wait** | Conditions are unclear or stretched. Doing nothing is the correct action for now. |
| **Avoid** | The evidence is unfavourable. No entry is justified regardless of price. |

### Recommendation ≠ Strategy

These are two different axes, and conflating them makes both harder to reason
about.

- A **Recommendation** answers *should I act, and how strongly?*
- A **Strategy** describes *what kind of setup this is* and therefore how an
  entry would be approached.

Example — the same stock, two independent statements:

> **Recommendation:** Watch
> **Strategy:** Pullback Entry

Read together: the trend is constructive, but the right entry is on a pullback
that has not happened yet. "Watch" carries the urgency; "Pullback Entry" carries
the method. A user can be shown several strategies over time while the action
vocabulary above stays stable, and the action can change without redefining the
strategy.

Strategy names (Pullback Entry, Breakout, Trend Following, and others) are
descriptive labels for a setup type. They must never be smuggled into the action
field, and the action must never be used to imply a method.

---

## 6. Recommendation Card Vision

The Recommendation Card is the intended primary surface for a single stock: one
self-contained answer the user can read top to bottom. This section describes the
destination, not a build specification.

Reading order matters — the card is designed to be understood by someone who
stops after the first two lines, and to reward someone who reads all of it.

- **Recommendation** — the action, unmissable and at the top.
- **Confidence** — how much weight to place on this recommendation, including an
  honest signal when the underlying data is incomplete.
- **Summary** — the verdict in one plain-English line.
- **Positives** — what is working in this stock's favour.
- **Risks** — what is working against it, and the limits of our analysis.
- **Entry** — where an entry would sensibly sit, expressed as a zone rather than
  a single price, because a real fill is never a single number.
- **Stop Loss** — the level at which the idea is considered wrong.
- **Targets** — a realistic first objective and a stretch objective.
- **Next Trigger** — the condition to watch for a change in the recommendation.
- **Beginner Tip** — one transferable lesson drawn from this situation.

Design intent: positives and risks always appear together and with equal visual
weight. A card that shows only what is favourable is a card that misleads. A card
that shows a trading plan without its risks is worse than one that shows neither.

---

## 7. Product Principles

These are the tests to apply when evaluating a proposed feature or change.

1. **One source of truth for recommendations.** A single stock has one
   recommendation at a time. No screen, client or report derives its own.
2. **The recommendation answers whether this is a good time to buy.** Features
   that do not serve that question wait their turn, however interesting.
3. **Every recommendation explains itself.** No verdict ships without reasoning
   the user can read and challenge.
4. **Never present technical indicators without interpretation.** A number on
   screen without its meaning transfers the analytical work back to the user.
5. **Make complex trading concepts approachable for beginners.** Teach through
   normal use, in context, rather than through separate documentation.
6. **Be honest about uncertainty.** Incomplete data, weak signals and
   conflicting evidence are disclosed, never smoothed over.

---

## 8. Future Roadmap

Conceptual direction, not a commitment or a sequence. Each item is listed with
the user problem it addresses, since that is what determines when it becomes
worth building.

**Portfolio Advisor** — moves TradeLens from single-stock decisions to
portfolio-level context: concentration, correlation, and whether an otherwise
good entry is a good idea *for this particular user's holdings*.

**Position Sizing** — turns a recommendation into a decision about *how much*.
Most retail losses come from size rather than selection, so this converts the
existing risk framing into a concrete quantity.

**AI Trading Coach** — a conversational layer for follow-up questions on a
recommendation, and durable feedback on the user's own patterns and discipline
over time.

**Recommendation Accuracy Dashboard** — public, honest reporting on how
recommendations have performed. This is a trust feature: a product that issues
verdicts should be accountable for them, including when the record is unflattering.

**Multi-timeframe Analysis** — reconciles what different timeframes say about the
same stock and explains the conflict, since disagreement across timeframes is
itself a signal.

**Backtesting** — lets a user see how a recommendation approach would have
behaved historically, framed as education about variability and drawdown rather
than as validation.

---

## 9. Out of Scope

TradeLens is **not financial advice**. It is educational, decision-support
software. It does not know the user's finances, obligations or risk tolerance,
and it does not tell anyone what to do with their money.

TradeLens is **not a prediction engine**. It assesses conditions in the present
based on observable market data. It does not forecast prices, and it should never
be presented as knowing what happens next.

TradeLens offers **no guarantee of future performance**. Past behaviour of a
stock, and the past accuracy of a recommendation, imply nothing about future
outcomes.

Every recommendation is therefore framed as decision support: evidence,
reasoning, and an explicit statement of risk, leaving the decision — and its
consequences — with the user. Product copy must never imply certainty,
entitlement to profit, or an obligation to act.

---

## 10. Engineering Principles

Product commitments only hold if the implementation enforces them. These are the
engineering rules that make the sections above true in practice.

1. **Business rules belong in the Recommendation Engine, not the frontend.**
   Trading logic lives in one place so there is one behaviour to reason about,
   test and change.
2. **The frontend renders recommendation data; it does not derive trading
   decisions.** A client that computes its own verdict creates a second source of
   truth and breaks Principle 1 of Section 7.
3. **Recommendation logic remains deterministic and explainable.** The same
   inputs always produce the same recommendation, and every output can be traced
   to the rules that produced it. Non-explainable techniques are not adopted for
   core recommendations, however capable.
4. **Backward compatibility is preserved wherever practical.** Existing
   consumers keep working; breaking changes are a deliberate, announced decision
   rather than a side effect.
5. **New recommendation fields are additive unless a major version change is
   planned.** Enrich by adding, not by redefining or removing.
6. **Every recommendation is testable through unit tests.** Each rule, action and
   level calculation is covered by tests that run without a network or a
   database, so behaviour is pinned down and regressions are caught immediately.
7. **External market data is validated and sanitized at the provider boundary
   before reaching the Recommendation Engine.** Providers own fetching,
   validation, normalisation and sanitisation. Invalid or incomplete external
   data must never propagate into the application; where data cannot be trusted,
   its absence is reported honestly rather than disguised.

---

## Maintaining This Document

This document is expected to change as the product learns, but not casually.
Revise it when a product decision genuinely supersedes what is written here, and
revise the text itself rather than adding exceptions elsewhere. If an
implementation has drifted from this document, one of the two is wrong and the
discrepancy should be resolved explicitly.
