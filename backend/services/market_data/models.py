"""Provider-independent market data models used by universe and screening."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    """A tradable instrument in the application universe."""

    symbol: str
    name: str
    sector: str = ""
    active: bool = True


@dataclass(frozen=True)
class UniverseConfig:
    """Metadata describing a configured instrument universe."""

    name: str
    active: bool = True
    description: str = ""


@dataclass(frozen=True)
class OpportunityContext:
    """Curated ranking context from the legacy OPPORTUNITIES list."""

    symbol: str
    score: int
    reason: str
