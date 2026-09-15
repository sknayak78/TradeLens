# MD-06 Opportunity Explainability

## Purpose

MD-06 explains why an MD-05 candidate received its analysis-priority rank. It
consumes `RankedOpportunity` and performs no market-data retrieval, deep
analysis, recommendation generation, or frontend work.

## Structure

`OpportunityExplanation` contains the symbol, rank, `opportunity_score`, a
priority band, deterministic summary, strengths, cautions, score breakdown,
raw scanner signal evidence, ranking reason codes, and provider provenance.

The score breakdown is copied from MD-05 component scores and weighted
contributions. MD-06 does not recalculate ranking weights or indicators.

## Priority Bands

- `80-100`: High analysis priority
- `60-79`: Moderate analysis priority
- `40-59`: Lower analysis priority
- `0-39`: Low analysis priority
- No available components: Analysis priority unavailable

These bands describe priority for deeper analysis only. They are not BUY
probability, expected return, investment quality, or a recommendation.

Missing components remain unavailable in the explanation and are never turned
into fabricated negative evidence. Provider provenance is copied unchanged.

Future UI and deep-analysis layers can consume the structured explanation
without parsing prose. BUY/SELL/WATCH/WAIT/AVOID decisions remain downstream.
