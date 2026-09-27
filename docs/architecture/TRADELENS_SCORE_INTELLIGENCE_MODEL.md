# TradeLens Score & Intelligence Model

> The TradeLens Score is a deterministic, evidence-based assessment of market opportunity quality. AI synthesis explains the score — it never calculates or overrides it.

---

## Core Principle

**Deterministic Analytics → Authoritative Score → AI Explanation**

This separation is architectural (ADR-004, ADR-005) and non-negotiable.

---

## Deterministic Analytics

All analytics are pure functions of normalized market data.

### Input: EvidenceBundle
See `docs/architecture/MARKET_INTELLIGENCE_ARCHITECTURE.md` Stage 4 for full structure.

Key evidence categories:
1. **Trend Evidence** — EMA alignment, price vs EMAs, trend classification
2. **Momentum Evidence** — RSI, RSI zone, momentum persistence
3. **Structure Evidence** — Support/resistance, distance to key levels, pattern recognition
4. **Volume Evidence** — Volume ratio, volume trend, volume at key levels
5. **Volatility Evidence** — ATR, ATR%, volatility regime
6. **Risk/Reward Evidence** — Computed entry/stop/target geometry

### Computation Rules
- **No external dependencies** — no network, no LLM, no clock, no randomness
- **Idempotent** — identical EvidenceBundle → identical analytics
- **Traceable** — every output value references specific input evidence
- **Bounded** — all intermediate values clamped to sensible ranges
- **Explicit** — no hidden heuristics; every formula documented

---

## Scoring Pipeline

### Component Scores (0-100 each)

| Component | Weight | Description |
|-----------|--------|-------------|
| Trend Alignment | 25% | Price position relative to EMA20/50/200; trend consistency |
| Momentum Quality | 20% | RSI zone, momentum persistence, divergence signals |
| Structure Favorability | 20% | Distance to support/resistance, pattern clarity, level strength |
| Risk/Reward Ratio | 15% | Computed R:R from entry zone to stop/targets; minimum 1.5:1 |
| Volume Confirmation | 10% | Volume at signal vs average; volume trend confirmation |
| Data Quality | 10% | Bars count, completeness, live overlay freshness |

### Weighted Composite
```
TradeLens Score = Σ(component_score × weight)
```
Result: **0-100** (never 100 — uncertainty acknowledged)

### Score Properties
| Property | Guarantee |
|----------|-----------|
| Deterministic | Same EvidenceBundle → Same Score |
| Monotonic (mostly) | Better evidence → same or higher score |
| Explainable | Component breakdown always available |
| Auditable | Full evidence trail stored with score |
| No LLM | Zero external calls in scoring path |

---

## TradeLens Score Terminology

| Term | Definition |
|------|------------|
| **TradeLens Score** | The authoritative 0-100 deterministic composite score |
| **Component Score** | Individual 0-100 score for each evidence category |
| **Evidence Strength** | Synonym for component score; reflects supporting evidence |
| **Conviction** | Qualitative band derived from score: `high` / `medium` / `low` / `avoid` |
| **Action** | Trading decision derived from score + strategy: `Strong Buy` / `Buy` / `Watch` / `Wait` / `Avoid` |

> **Critical:** "Confidence" or "Evidence Strength" ≠ Probability of Profit. It reflects the *strength of supporting evidence* for the deterministic assessment. See Regression Suite PROV-009, ACC-010.

---

## Evidence / Strength Semantics

### Evidence Strength (Component Level)
- **0-20:** Contradictory or absent evidence
- **21-40:** Weak evidence, significant gaps
- **41-60:** Moderate evidence, some confirming factors
- **61-80:** Strong evidence, multiple confirming factors
- **81-100:** Very strong evidence, high clarity (rare)

### Conviction Bands (Composite Level)
| Score | Conviction | Typical Action |
|-------|------------|----------------|
| 80-99 | High | Strong Buy / Buy |
| 65-79 | High/Medium | Buy |
| 50-64 | Medium | Watch |
| 35-49 | Low/Medium | Wait |
| 0-34 | Low | Avoid |

### Action Derivation
Action = `f(Score, Strategy, Risk/Reward, Data Quality)`

Strategy modifies action thresholds:
- **Trend Continuation / Pullback:** Lower score threshold for Buy (zone defined)
- **Breakout:** Requires higher score + volume confirmation
- **Consolidation / No Entry Yet:** Caps action at Watch/Wait

---

## AI Synthesis Boundary

### What AI Receives
```python
@dataclass
class AISynthesisInput:
    symbol: str
    score: int
    components: Dict[str, int]      # Component scores
    evidence: EvidenceBundle         # Full evidence
    strategy: str
    levels: Levels                  # Entry, stop, targets
    action: str
    conviction: str
```

### What AI Produces
```python
@dataclass
class AISynthesisOutput:
    summary: str                    # 2-3 sentence plain-English summary
    why: List[str]                  # Bullet points: supporting evidence
    risks: List[str]                # Bullet points: risk factors
    watch_next: str                 # Specific trigger to monitor
    beginner_tip: str               # Educational guidance
    ideal_for: str                  # Trader profile suitability
```

### AI Constraints (Enforced by Architecture)
1. **Input-only** — AI never fetches additional data
2. **No score modification** — AI output never feeds back into scoring
3. **Non-blocking** — Recommendation API returns without waiting for AI
4. **Separate storage** — AI synthesis stored separately from authoritative recommendation
5. **Failure isolation** — AI failure does not degrade core recommendation

### AI Prompting Principles
- "Explain this evidence to a beginner trader"
- "Translate technical factors into plain English"
- "Highlight what would invalidate this thesis"
- Never: "Predict the next move", "Guarantee profit", "Override the score"

---

## Relationship to Recommendation Engine

### Recommendation Engine (ER-0014/ER-0016 — IMPLEMENTED)
- **Single source of truth** for all trading decisions (ADR-001)
- Consumes `TradeLens Score` + `EvidenceBundle` + `Strategy`
- Produces `Recommendation` block: action, strategy, levels, narrative
- Strategy is parent decision (ADR-002): levels/narrative derived from strategy
- Legacy fields (`suggestedAction`, `classification`, `strengthScore`, etc.) deprecated but served

### Recommendation Block Structure
```python
@dataclass
class Recommendation:
    action: str                    # Strong Buy, Buy, Watch, Wait, Avoid
    strategy: str                  # Trend Continuation, Pullback, Breakout, Consolidation, No Entry Yet
    conviction: str                # high, medium, low, avoid
    score: int                     # TradeLens Score (0-100)
    verdict: str                   # One-sentence thesis
    summary: str                   # Plain-English summary (from AI or fallback)
    why: List[str]                 # Supporting evidence bullets
    risks: List[str]               # Risk factors
    levels: Optional[Levels]       # Entry zone, stop, targets (only for level strategies)
    watch_next: str                # Specific trigger
    beginner_tip: str
    ideal_for: str
```

### Deprecated Legacy Fields (Per DATA_PROVENANCE.md)
| Legacy Field | Replacement |
|--------------|-------------|
| `suggestedAction` | `recommendation.action` |
| `classification` | `recommendation.conviction` |
| `insight` | `recommendation.summary` |
| `tradeSetup` | `recommendation.strategy` |
| `riskLevel` | `recommendation.levels` + `confidence` |
| `strengthScore` | `recommendation.score` |
| `stars` | Derived from `recommendation.conviction` |
| `aiInsight` (provider-generated) | `recommendation.summary` (AI synthesis) |

---

## Relationship to MD-05 / MD-06

### MD-05: Recommendation Engine Architecture
- Defines the Recommendation Engine as the authoritative decision service
- Documents strategy-driven pipeline (ER-0016)
- Specifies single-source-of-truth enforcement (ER-0014B)
- **This document (Score Model) feeds MD-05** — Score is an input to Recommendation

### MD-06: AI Mentor Architecture
- Defines AI Mentor as synthesis/explanation layer
- Documents Mentor Challenge, Practice Portfolio, Learning Framework
- **This document bounds MD-06** — AI Mentor receives Score+Evidence, never influences Score

---

## Regression Test Expectations

See `docs/docs/06-testing/TradeLens_Regression_Suite.md` for full suite.

### Key Determinism Tests (PROV-*)
- **PROV-007:** Recommendation deterministic for identical input
- **PROV-008:** No network dependency in recommendation engine
- **PROV-009:** No LLM dependency in recommendation engine
- **PROV-010:** No clock/randomness dependency

### Strategy Consistency Tests (REC-*)
- **REC-010:** One recommendation = one parent strategy
- **REC-011:** Action valid for selected strategy
- **REC-014:** Pullback strategy never produces contradictory immediate-entry
- **REC-015:** Trend Continuation never produces pullback contradiction
- **REC-007:** Strategy, action, levels, narrative mutually consistent

### Confidence/Evidence Strength Tests (REC-030 to REC-035)
- **REC-031:** Confidence never presented as probability of profit
- **REC-032:** UI explanatory hint states it reflects strength of supporting evidence
- **REC-034:** Not described as historically calibrated unless calibration exists

### Accuracy Framework Tests (ACC-*) — FUTURE / PLANNED
- **ACC-001:** Replay historical snapshot reproduces original recommendation
- **ACC-003:** Forward return measured after recommendation timestamp
- **ACC-010:** Calibration evaluated before describing evidence strength as predictive probability
- **ACC-012:** Avoid survivorship/look-ahead bias

> **Current State:** ACC-* tests are PLANNED. Until historical snapshots exist and calibration is validated, "confidence/evidence strength" remains an internal measure only.

---

## Implementation Location

| Component | Location |
|-----------|----------|
| EvidenceBundle computation | `backend/services/indicators/`, `backend/services/analysis/` |
| TradeLens Score calculation | `backend/services/scoring/score_engine.py` |
| Strategy determination | `backend/services/recommendation/strategy.py` |
| Recommendation assembly | `backend/services/recommendation/engine.py` |
| AI synthesis | `backend/services/ai/synthesis.py` |
| API endpoints | `backend/routers/opportunities.py`, `backend/routers/stocks.py` |

---

## Configuration

Scoring weights configurable via environment (with sensible defaults):

```bash
SCORE_WEIGHT_TREND=0.25
SCORE_WEIGHT_MOMENTUM=0.20
SCORE_WEIGHT_STRUCTURE=0.20
SCORE_WEIGHT_RISK_REWARD=0.15
SCORE_WEIGHT_VOLUME=0.10
SCORE_WEIGHT_DATA_QUALITY=0.10

# Minimum R:R for positive score contribution
MIN_RISK_REWARD=1.5

# Maximum score (never 100)
MAX_SCORE=99
```

---

## References

- ADR-001: Single Source of Truth for Market Data
- ADR-002: Strategy is the Parent Trading Thesis
- ADR-004: Deterministic Market Intelligence Pipeline
- ADR-005: AI Synthesis Boundary
- ADR-006: Market Intelligence Cache and Prepared Data
- `docs/architecture/MARKET_INTELLIGENCE_ARCHITECTURE.md`
- `docs/05-engineering/DATA_PROVENANCE.md`
- `docs/05-engineering/ER-0016-STRATEGY-DRIVEN-RECOMMENDATION-ENGINE.md`
- `docs/docs/06-testing/TradeLens_Regression_Suite.md` (PROV-*, REC-*, ACC-*)