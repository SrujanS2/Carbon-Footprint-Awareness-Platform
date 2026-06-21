"""Domain models describing a carbon-footprint estimate and its insights.

These are plain, serialisable dataclasses with **no Flask or ML dependency**,
so they can be reused by the services, the API layer and the tests alike.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass(frozen=True)
class CategoryBreakdown:
    """Annual CO2e (kg) attributed to each lifestyle category."""

    transport: float
    flights: float
    diet: float
    electricity: float
    gas: float

    def as_dict(self) -> Dict[str, float]:
        """Return the breakdown as a plain dict (JSON-friendly)."""
        return asdict(self)

    def total(self) -> float:
        """Return total annual CO2e across all categories (kg)."""
        return round(
            self.transport
            + self.flights
            + self.diet
            + self.electricity
            + self.gas,
            2,
        )


@dataclass(frozen=True)
class Insight:
    """A single, explainable, actionable recommendation.

    Attributes:
        category: Lifestyle area the insight targets (e.g. ``"transport"``).
        title: Short imperative recommendation.
        detail: Longer explanation of the suggested action.
        annual_saving_kg: Estimated CO2e saved per year if adopted (kg).
        reason: Human-readable, SHAP-style explanation of *why* this insight
            was surfaced (which inputs drove it).
        priority: Integer rank (1 = highest impact).
    """

    category: str
    title: str
    detail: str
    annual_saving_kg: float
    reason: str
    priority: int

    def as_dict(self) -> Dict[str, object]:
        """Return the insight as a plain dict (JSON-friendly)."""
        return asdict(self)


@dataclass(frozen=True)
class FootprintResult:
    """The full result returned to the client for one assessment."""

    total_annual_kg: float
    per_capita_annual_kg: float
    breakdown: CategoryBreakdown
    rating: str
    rating_explanation: str
    feature_contributions: Dict[str, float]
    insights: List[Insight] = field(default_factory=list)

    def as_dict(self) -> Dict[str, object]:
        """Serialise the entire result tree to JSON-friendly primitives."""
        return {
            "total_annual_kg": self.total_annual_kg,
            "per_capita_annual_kg": self.per_capita_annual_kg,
            "breakdown": self.breakdown.as_dict(),
            "rating": self.rating,
            "rating_explanation": self.rating_explanation,
            "feature_contributions": self.feature_contributions,
            "insights": [i.as_dict() for i in self.insights],
        }
