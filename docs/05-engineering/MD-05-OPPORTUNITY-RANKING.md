# MD-05 Opportunity Ranking

## Objective

MD-05 prioritizes eligible MD-04 scanner candidates for later analysis. It is
an opportunity-quality ranking, not a recommendation, trade signal, or
probability of profit.

## Boundary

`OpportunityRanker` consumes `ScreeningResult` objects from `MarketScanner`.
It does not call `MarketDataService`, the recommendation engine, deep analysis,
LLMs, the database, or the frontend.

Rejected scanner results are ignored. Eligible candidates are ranked in memory
and can be limited with `rank(candidates, limit=20)`.

## Score

The score is normalized from 0 to 100 using the boolean signals currently
exposed by MD-04:

| Component | Weight |
| --- | ---: |
| Trend | 20% |
| Momentum | 15% |
| Liquidity | 15% |
| Support/resistance structure | 20% |
| Breakout/breakdown | 15% |
| Volatility | 15% |

MD-04 exposes support/resistance as one combined signal, not separate distance
or headroom measurements, so MD-05 does not invent separate precision for
those values.

Each available `True` signal scores 100 and each available `False` signal
scores 0. Missing signals are unavailable, not failed: their weights are
removed and the remaining weighted score is renormalized. If every component
is unavailable, the score is `None`. `opportunity_score` is the public name;
`overall_score` remains as a compatibility alias. `weighted_components` exposes
the normalized contribution of each available component and sums to the total.

## Ordering and Explainability

Results sort by descending score, then trend score, momentum score, symbol, and
instrument key. Strengths and cautions are structured component labels. The
original scanner result and provider provenance are retained for later
explainability work.

BUY/WATCH/WAIT/AVOID decisions, narrative explanations, deep analysis, and
recommendations remain outside MD-05 and are deferred to later ERs.
