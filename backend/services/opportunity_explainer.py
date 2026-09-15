"""Deterministic explanations for MD-05 ranked opportunities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from services.opportunity_ranker import RankedOpportunity


@dataclass(frozen=True)
class ScoreBreakdown:
    """One MD-05 component as supplied by the ranker."""

    score: float | None
    weighted_contribution: float | None
    available: bool


@dataclass(frozen=True)
class OpportunityExplanation:
    symbol: str
    rank: int
    opportunity_score: float | None
    priority: str
    summary: str
    strengths: tuple[str, ...]
    cautions: tuple[str, ...]
    score_breakdown: Mapping[str, ScoreBreakdown]
    signal_evidence: Mapping[str, Any]
    ranking_factors: tuple[str, ...]
    provider: str | None


class OpportunityExplainer:
    """Explain a RankedOpportunity without recalculating or fetching anything."""

    def explain(self, ranked: RankedOpportunity) -> OpportunityExplanation:
        if not isinstance(ranked, RankedOpportunity):
            raise ValueError("opportunity explanation requires a RankedOpportunity")
        if not ranked.symbol.strip():
            raise ValueError("ranked opportunity symbol must not be empty")

        breakdown = {
            component: ScoreBreakdown(
                score=ranked.component_scores.get(component),
                weighted_contribution=ranked.weighted_components.get(component),
                available=ranked.component_scores.get(component) is not None,
            )
            for component in ranked.component_scores
        }
        available_count = sum(item.available for item in breakdown.values())
        total_components = len(breakdown)
        priority = _priority_for_score(ranked.opportunity_score)
        if ranked.opportunity_score is None:
            summary = (
                "Analysis priority is unavailable because no ranking components "
                "were available."
            )
        else:
            summary = (
                f"{priority} based on {available_count} of {total_components} "
                "available ranking components."
            )
            if ranked.strengths:
                summary += " Supporting factors: " + ", ".join(ranked.strengths) + "."
            if ranked.cautions:
                summary += " Cautions: " + ", ".join(ranked.cautions) + "."

        signal_evidence = {
            "scanner_signals": dict(sorted(ranked.scanner_result.signals.items())),
            "scanner_score": ranked.scanner_result.score,
            "available_weight": ranked.available_weight,
        }
        return OpportunityExplanation(
            symbol=ranked.symbol,
            rank=ranked.rank,
            opportunity_score=ranked.opportunity_score,
            priority=priority,
            summary=summary,
            strengths=ranked.strengths,
            cautions=ranked.cautions,
            score_breakdown=breakdown,
            signal_evidence=signal_evidence,
            ranking_factors=ranked.scanner_result.reason_codes,
            provider=ranked.provider,
        )


def _priority_for_score(score: float | None) -> str:
    if score is None:
        return "Analysis priority unavailable"
    if score >= 80:
        return "High analysis priority"
    if score >= 60:
        return "Moderate analysis priority"
    if score >= 40:
        return "Lower analysis priority"
    return "Low analysis priority"
