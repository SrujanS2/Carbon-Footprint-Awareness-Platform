"""Unit tests for the explainable AI insight engine."""

from app.models.footprint import CategoryBreakdown
from app.services.carbon_calculator import calculate_breakdown
from app.services.insight_engine import (
    BASELINE_PROFILE,
    CATEGORIES,
    InsightEngine,
    _rating_for_total,
)
from app.utils.validation import FootprintInput


def _input(**overrides):
    base = dict(
        weekly_km=300,
        transport_mode="car_petrol",
        flights_per_year=4,
        diet_type="high_meat",
        electricity_kwh=400,
        gas_kwh=500,
        household_size=1,
        region="",
    )
    base.update(overrides)
    return FootprintInput(**base)


def test_rating_bands():
    assert _rating_for_total(1000) == "Low"
    assert _rating_for_total(4000) == "Moderate"
    assert _rating_for_total(8000) == "High"
    assert _rating_for_total(20000) == "Very High"


def test_classify_returns_known_label_and_confidence():
    engine = InsightEngine(n_samples=400)
    breakdown = calculate_breakdown(_input())
    rating, confidence = engine.classify(breakdown)
    assert rating in {"Low", "Moderate", "High", "Very High"}
    assert 0.0 <= confidence <= 1.0


def test_high_lifestyle_rated_higher_than_low():
    engine = InsightEngine(n_samples=600)
    high = calculate_breakdown(_input())
    low = calculate_breakdown(
        _input(weekly_km=10, transport_mode="bike_walk", flights_per_year=0,
               diet_type="vegan", electricity_kwh=80, gas_kwh=0,
               household_size=4)
    )
    order = {"Low": 0, "Moderate": 1, "High": 2, "Very High": 3}
    high_rating, _ = engine.classify(high)
    low_rating, _ = engine.classify(low)
    assert order[high_rating] >= order[low_rating]


def test_feature_contributions_additivity():
    """SHAP additivity: baseline_total + sum(contributions) == prediction."""
    engine = InsightEngine(n_samples=200)
    breakdown = calculate_breakdown(_input())
    contributions = engine.feature_contributions(breakdown)

    assert set(contributions.keys()) == set(CATEGORIES)
    baseline_total = sum(BASELINE_PROFILE.values())
    reconstructed = baseline_total + sum(contributions.values())
    assert round(reconstructed, 2) == round(breakdown.total(), 2)


def test_insights_are_ranked_by_saving():
    engine = InsightEngine(n_samples=200)
    breakdown = calculate_breakdown(_input())
    insights = engine.generate_insights(_input(), breakdown)
    savings = [i.annual_saving_kg for i in insights]
    assert savings == sorted(savings, reverse=True)
    # Priorities are 1-based and strictly increasing.
    assert [i.priority for i in insights] == list(range(1, len(insights) + 1))


def test_high_impact_lifestyle_produces_insights():
    engine = InsightEngine(n_samples=200)
    breakdown = calculate_breakdown(_input())
    insights = engine.generate_insights(_input(), breakdown)
    categories = {i.category for i in insights}
    # A petrol-driving, frequent-flying, high-meat user should get advice in
    # all the obvious categories.
    assert {"transport", "flights", "diet"}.issubset(categories)


def test_low_impact_lifestyle_produces_few_or_no_insights():
    engine = InsightEngine(n_samples=200)
    low = _input(weekly_km=5, transport_mode="bike_walk", flights_per_year=0,
                 diet_type="vegan", electricity_kwh=50, gas_kwh=0,
                 household_size=4)
    breakdown = calculate_breakdown(low)
    insights = engine.generate_insights(low, breakdown)
    # No high-impact levers => no transport/flight/diet suggestions.
    assert all(i.category not in {"transport", "flights", "diet"}
               for i in insights)


def test_every_insight_has_explanation():
    engine = InsightEngine(n_samples=200)
    breakdown = calculate_breakdown(_input())
    for insight in engine.generate_insights(_input(), breakdown):
        assert insight.reason
        assert insight.annual_saving_kg >= 0


def test_model_is_cached():
    engine = InsightEngine(n_samples=200)
    breakdown = calculate_breakdown(_input())
    engine.classify(breakdown)
    first = engine._ensure_trained()
    second = engine._ensure_trained()
    assert first is second  # trained only once
