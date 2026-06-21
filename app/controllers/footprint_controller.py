"""Footprint controller.

Orchestrates validation, calculation, rating and explanation into a single
result object. Contains no Flask code, so the whole pipeline is unit-testable.

Rating strategy:
* Primary: a Random Forest trained on the real
  ``personal_carbon_footprint_behavior`` dataset (:mod:`rating_model`).
* Fallback: the synthetic-data rating in :mod:`insight_engine`, used only when
  the dataset file is unavailable, so the app never breaks.

The deterministic per-category breakdown and the SHAP-style explanation are
always produced by the calculator and insight engine.
"""

from typing import Any

from app.models.footprint import FootprintResult
from app.services.carbon_calculator import calculate_breakdown
from app.services.insight_engine import BASELINE_PROFILE, InsightEngine
from app.services.rating_model import DataRatingModel
from app.utils.validation import FootprintInput, validate_payload

# Shared singletons: the ML models train once and are reused across requests.
_engine = InsightEngine()
_rating_model = DataRatingModel()


def _rating_explanation(
    rating: str, confidence: float, total_kg: float, source: str
) -> str:
    """Build a plain-language explanation for the assigned rating."""
    if source == "dataset":
        return (
            "A Random Forest trained on {n} real behaviour records "
            "(held-out accuracy {acc:.0f}%) rates your daily habits as "
            "'{rating}' impact (confidence {conf:.0f}%). Your estimated annual "
            "footprint is about {kg:,.0f} kg CO2e."
        ).format(
            n=_rating_model.n_samples,
            acc=(_rating_model.accuracy or 0.0) * 100,
            rating=rating,
            conf=confidence * 100,
            kg=total_kg,
        )
    return (
        "Your estimated footprint of {kg:,.0f} kg CO2e per year places you in "
        "the '{rating}' band (model confidence {conf:.0f}%)."
    ).format(kg=total_kg, rating=rating, conf=confidence * 100)


def assess(payload: Any) -> FootprintResult:
    """Run the full assessment pipeline for a raw request payload.

    Steps:
        1. Validate & sanitise the payload (raises ``ValidationError`` on bad
           input - handled by the route as HTTP 400).
        2. Compute the deterministic per-category breakdown.
        3. Rate the lifestyle with the data-trained model (fallback: synthetic).
        4. Explain with SHAP-style additive contributions.
        5. Generate ranked, actionable insights.

    Args:
        payload: Decoded JSON request body.

    Returns:
        A fully-populated :class:`FootprintResult`.
    """
    data: FootprintInput = validate_payload(payload)

    breakdown = calculate_breakdown(data)
    per_capita_total = breakdown.total()

    # Household-inclusive total (undo the per-person division of shared energy).
    household_energy_personal = breakdown.electricity + breakdown.gas
    household_energy_full = household_energy_personal * data.household_size
    total_annual_kg = round(
        breakdown.transport
        + breakdown.flights
        + breakdown.diet
        + household_energy_full,
        2,
    )

    # Primary rating from the data-trained model; fall back to synthetic.
    data_rating = _rating_model.rate(data)
    if data_rating is not None:
        rating, confidence = data_rating
        rating_source = "dataset"
    else:
        rating, confidence = _engine.classify(breakdown)
        rating_source = "synthetic"

    contributions = _engine.feature_contributions(breakdown)
    insights = _engine.generate_insights(data, breakdown)

    return FootprintResult(
        total_annual_kg=total_annual_kg,
        per_capita_annual_kg=per_capita_total,
        breakdown=breakdown,
        rating=rating,
        rating_explanation=_rating_explanation(
            rating, confidence, per_capita_total, rating_source
        ),
        feature_contributions=contributions,
        insights=insights,
    )


def baseline_profile() -> dict:
    """Expose the average-person baseline used for explanations (UI reference)."""
    return dict(BASELINE_PROFILE)
