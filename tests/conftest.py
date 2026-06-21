"""Shared pytest fixtures."""

import pytest

from app import create_app
from app.utils.validation import FootprintInput


@pytest.fixture()
def client():
    """A Flask test client with testing config enabled."""
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def valid_payload():
    """A representative, valid request payload (high-impact lifestyle)."""
    return {
        "weekly_km": 300,
        "transport_mode": "car_petrol",
        "flights_per_year": 4,
        "diet_type": "high_meat",
        "electricity_kwh": 350,
        "gas_kwh": 600,
        "household_size": 2,
        "region": "Test City",
    }


@pytest.fixture()
def low_impact_input():
    """A validated low-impact lifestyle input."""
    return FootprintInput(
        weekly_km=20,
        transport_mode="bike_walk",
        flights_per_year=0,
        diet_type="vegan",
        electricity_kwh=100,
        gas_kwh=0,
        household_size=3,
        region="",
    )
