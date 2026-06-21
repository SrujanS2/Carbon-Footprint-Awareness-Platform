"""Tests for the data-trained Random Forest rating model."""

import pytest

from app.services.rating_model import (
    APP_DIET_TO_FOOD,
    APP_TRANSPORT_TO_DATASET,
    DataRatingModel,
)
from app.utils.validation import FootprintInput


def _input(**overrides):
    base = dict(
        weekly_km=140,
        transport_mode="car_petrol",
        flights_per_year=2,
        diet_type="omnivore",
        electricity_kwh=250,
        gas_kwh=150,
        household_size=2,
        region="",
    )
    base.update(overrides)
    return FootprintInput(**base)


@pytest.fixture(scope="module")
def model():
    """A trained model (shared across this module for speed)."""
    return DataRatingModel()


def test_model_trains_on_real_dataset(model):
    assert model.available is True
    assert model.n_samples > 500


def test_reported_accuracy_is_reasonable(model):
    acc = model.accuracy
    assert acc is not None
    # The level is a strong function of the features, so a forest should do
    # clearly better than the majority-class baseline (~0.62).
    assert 0.7 <= acc <= 1.0


def test_rate_returns_valid_level_and_confidence(model):
    result = model.rate(_input())
    assert result is not None
    level, confidence = result
    assert level in {"Low", "Medium", "High"}
    assert 0.0 <= confidence <= 1.0


def test_high_impact_rates_at_least_as_high_as_low(model):
    order = {"Low": 0, "Medium": 1, "High": 2}
    high = model.rate(_input(
        weekly_km=700, transport_mode="car_petrol", diet_type="high_meat",
        electricity_kwh=600, household_size=1))
    low = model.rate(_input(
        weekly_km=14, transport_mode="bike_walk", diet_type="vegan",
        electricity_kwh=60, household_size=4))
    assert order[high[0]] >= order[low[0]]


def test_mapping_tables_cover_app_vocabulary():
    # Every app transport mode and diet maps to a dataset category.
    for mode in ("car_petrol", "car_electric", "bus", "train", "bike_walk"):
        assert mode in APP_TRANSPORT_TO_DATASET
    for diet in ("vegan", "vegetarian", "pescatarian", "omnivore", "high_meat"):
        assert diet in APP_DIET_TO_FOOD


def test_missing_dataset_is_handled_gracefully():
    absent = DataRatingModel(csv_path="/no/such/file.csv")
    assert absent.available is False
    assert absent.rate(_input()) is None
    assert absent.accuracy is None
