# MD-08 Today's Opportunities

## Flow

Today's Opportunities now composes the existing pipeline in one backend run:

```text
NSE universe -> MD-04 scan -> MD-05 rank -> MD-06 explain -> MD-07 deep analysis
```

The curated catalogue is no longer the primary discovery source. It remains
an explicit `curated_fallback` when discovery cannot produce a successfully
analysed shortlist. Discovery responses expose `sourceMode` so fallback is
never presented as broad-market discovery.

Broad discovery and curated fallback are both execution-bounded. If the
scanner or fallback cannot complete within its service deadline, the response
uses `discovery_failed` with an empty opportunity list and an explicit error;
it does not fabricate counts or wait indefinitely on a provider call.

## Response

The existing opportunities response remains backward-compatible and gains
additive discovery metadata: source mode, scanned/candidate/ranked/deeply
analysed counts, and final opportunity count. Rows preserve the existing
technical recommendation plus MD-05 priority score, MD-06 explanation, and
deep-analysis provider provenance.

"Scanned", "candidates", and "deeply analysed" are separate counts. A high
opportunity score remains analysis priority, not a BUY signal. The deep
technical recommendation remains authoritative and may be WAIT or AVOID.

## Non-Curated and Live Data

Candidates such as VOLTAS and PIDILITIND flow through the instrument master,
scanner, ranker, explainer, and deep-analysis pipeline without catalogue
membership. Provider provenance is copied from the deep result. Live Upstox
activation remains dependent on `UPSTOX_ACCESS_TOKEN`; deterministic fallback
and development data must remain explicitly identifiable.

The current implementation runs one pipeline execution per cached refresh and
does not add persistence, background scheduling, or frontend-side ranking.
