"""Deterministic opportunity prioritization over MD-04 scanner candidates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from services.market_scanner import ScreeningResult


@dataclass(frozen=True)
class RankingWeights:
    """Weights for the signals actually exposed by MD-04."""

    trend: float = 20.0
    momentum: float = 15.0
    liquidity: float = 15.0
    structure: float = 20.0
    breakout: float = 15.0
    volatility: float = 15.0

    def as_mapping(self) -> Mapping[str, float]:
        return {
            "trend": self.trend,
            "momentum": self.momentum,
            "liquidity": self.liquidity,
            "structure": self.structure,
            "breakout": self.breakout,
            "volatility": self.volatility,
        }


@dataclass(frozen=True)
class RankedOpportunity:
    rank: int
    symbol: str
    instrument_key: str
    overall_score: float | None
    available_weight: float
    component_scores: Mapping[str, float | None]
    weighted_components: Mapping[str, float | None]
    strengths: tuple[str, ...]
    cautions: tuple[str, ...]
    provider: str | None
    scanner_result: ScreeningResult

    @property
    def opportunity_score(self) -> float | None:
        """MD-05 public terminology; ``overall_score`` remains compatible."""
        return self.overall_score


@dataclass(frozen=True)
class RankingResult:
    opportunities: tuple[RankedOpportunity, ...]
    candidate_count: int


_SIGNAL_FOR_COMPONENT = {
    "trend": "trend",
    "momentum": "momentum",
    "liquidity": "liquidity",
    "structure": "support_resistance",
    "breakout": "breakout_breakdown",
    "volatility": "volatility",
}

_SIGNAL_LABELS = {
    "trend": "EMA trend alignment",
    "momentum": "positive momentum",
    "liquidity": "healthy liquidity",
    "structure": "support/resistance structure",
    "breakout": "breakout/breakdown structure",
    "volatility": "healthy volatility",
}


class OpportunityRanker:
    """Rank eligible scanner results without market-data or recommendation calls."""

    def __init__(self, weights: RankingWeights | None = None) -> None:
        self._weights = weights or RankingWeights()
        if any(weight < 0 for weight in self._weights.as_mapping().values()):
            raise ValueError("ranking weights must be non-negative")
        if sum(self._weights.as_mapping().values()) <= 0:
            raise ValueError("ranking weights must have a positive total")

    def rank(
        self,
        candidates: Sequence[ScreeningResult],
        *,
        limit: int = 20,
    ) -> RankingResult:
        """Return a stable, limited ranking of eligible MD-04 candidates."""
        if limit < 0:
            raise ValueError("ranking limit must not be negative")

        eligible = self._unique_eligible(candidates)
        scored = [self._score(candidate) for candidate in eligible]
        scored.sort(key=self._sort_key)
        ranked = tuple(
            RankedOpportunity(
                rank=index,
                symbol=opportunity.symbol,
                instrument_key=opportunity.instrument_key,
                overall_score=opportunity.overall_score,
                available_weight=opportunity.available_weight,
                component_scores=opportunity.component_scores,
                weighted_components=opportunity.weighted_components,
                strengths=opportunity.strengths,
                cautions=opportunity.cautions,
                provider=opportunity.provider,
                scanner_result=opportunity.scanner_result,
            )
            for index, opportunity in enumerate(scored[:limit], start=1)
        )
        return RankingResult(opportunities=ranked, candidate_count=len(eligible))

    @staticmethod
    def _unique_eligible(
        candidates: Sequence[ScreeningResult],
    ) -> tuple[ScreeningResult, ...]:
        selected: dict[str, ScreeningResult] = {}
        for candidate in candidates:
            if not candidate.passed:
                continue
            current = selected.get(candidate.symbol)
            if current is None or candidate.instrument_key < current.instrument_key:
                selected[candidate.symbol] = candidate
        return tuple(selected[symbol] for symbol in sorted(selected))

    def _score(self, candidate: ScreeningResult) -> RankedOpportunity:
        weights = self._weights.as_mapping()
        component_scores: dict[str, float | None] = {}
        strengths: list[str] = []
        cautions: list[str] = []
        weighted_total = 0.0
        available_weight = 0.0

        for component, signal_name in _SIGNAL_FOR_COMPONENT.items():
            raw_signal = candidate.signals.get(signal_name)
            if not isinstance(raw_signal, bool):
                component_scores[component] = None
                cautions.append(f"{_SIGNAL_LABELS[component]} unavailable")
                continue

            score = 100.0 if raw_signal else 0.0
            component_scores[component] = score
            available_weight += weights[component]
            weighted_total += score * weights[component]
            if raw_signal:
                strengths.append(_SIGNAL_LABELS[component])
            else:
                cautions.append(f"{_SIGNAL_LABELS[component]} weak")

        overall_score = (
            None
            if available_weight == 0
            else round(weighted_total / available_weight, 2)
        )
        weighted_components = {
            component: (
                None
                if score is None or available_weight == 0
                else round(score * weights[component] / available_weight, 2)
            )
            for component, score in component_scores.items()
        }
        return RankedOpportunity(
            rank=0,
            symbol=candidate.symbol,
            instrument_key=candidate.instrument_key,
            overall_score=overall_score,
            available_weight=available_weight,
            component_scores=component_scores,
            weighted_components=weighted_components,
            strengths=tuple(strengths),
            cautions=tuple(cautions),
            provider=candidate.provider,
            scanner_result=candidate,
        )

    @staticmethod
    def _sort_key(opportunity: RankedOpportunity) -> tuple[float, float, float, str, str]:
        components = opportunity.component_scores
        score = -1.0 if opportunity.overall_score is None else -opportunity.overall_score
        trend = components.get("trend")
        momentum = components.get("momentum")
        return (
            score,
            -(trend if trend is not None else -1.0),
            -(momentum if momentum is not None else -1.0),
            opportunity.symbol,
            opportunity.instrument_key,
        )
