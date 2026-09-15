# MD-07 Ranked Candidate Deep Analysis

## Purpose

MD-07 spends the existing expensive technical-analysis path only on the
highest-priority MD-05 candidates. It is an orchestrator, not a new indicator,
scanner, ranker, recommendation engine, or provider layer.

```text
Broad universe -> Scanner -> Rank -> Explain -> Top-N -> Deep Analysis -> Technical view
```

## Delegation and Limit

`DeepAnalysisPipeline` defaults to `limit=20` and processes candidates in the
rank order supplied by MD-05. It stops selecting after the limit, so 2,656
ranked candidates can trigger at most 20 deep-analysis calls. Processing is
sequential; concurrency and caching are deliberately deferred.

The default adapter uses the established `MarketDataService` snapshot/insight
boundary, `analysis.service`, and `stock_decision.decide`. Tests inject a
deterministic analyzer instead.

## Results and Failures

Each `DiscoveredOpportunity` preserves the MD-05 rank and MD-06 explanation,
then attaches either a `DeepAnalysisResult` or a deterministic error. One
candidate failure does not abort later candidates, and results are never
re-ranked or compacted.

The existing recommendation engine remains authoritative. A high opportunity
score may still produce `Wait` or `Avoid`; MD-07 never translates ranking into
a recommendation.
