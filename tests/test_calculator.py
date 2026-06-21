"""Unit tests for the deterministic carbon calculator."""

from app.models.footprint import CategoryBreakdown
from app.services.carbon_calculator import (
    EMISSION_FACTORS,
    WEEKS_PER_YEAR,
    MONTHS_PER_YEAR,
    calculate_breakdown,
)
from app.utils.validation import FootprintInput


def _make_input(**overrides):
    base = dict(
        weekly_km=100,
        transport_mode="car_petrol",
        flights_per_year=2,
        diet_type="omnivore",
        electricity_kwh=300,
        gas_kwh=200,
        household_size=2,
        region="",
    )
    base.update(overrides)
    return FootprintInput(**base)


def test_breakdown_type_and_total():
    breakdown = calculate_breakdown(_make_input())
    assert isinstance(breakdown, CategoryBreakdown)
    # Total equals the sum of categories.
    assert breakdown.total() == round(
        breakdown.transport
        + breakdown.flights
        + breakdown.diet
        + breakdown.electricity
        + breakdown.gas,
        2,
    )


def test_transport_factor_applied():
    breakdown = calculate_breakdown(_make_input(weekly_km=100,
                                                transport_mode="car_petrol"))
    expected = 100 * WEEKS_PER_YEAR * EMISSION_FACTORS["transport_per_km"]["car_petrol"]
    assert breakdown.transport == round(expected, 2)


def test_bike_walk_is_zero_transport():
    breakdown = calculate_breakdown(_make_input(transport_mode="bike_walk"))
    assert breakdown.transport == 0.0


def test_flights_factor_applied():
    breakdown = calculate_breakdown(_make_input(flights_per_year=3))
    assert breakdown.flights == round(3 * EMISSION_FACTORS["flight_per_trip"], 2)


def test_diet_lookup():
    breakdown = calculate_breakdown(_make_input(diet_type="vegan"))
    assert breakdown.diet == EMISSION_FACTORS["diet_per_year"]["vegan"]


def test_energy_divided_by_household():
    one = calculate_breakdown(_make_input(electricity_kwh=300, household_size=1))
    two = calculate_breakdown(_make_input(electricity_kwh=300, household_size=2))
    # Doubling household size halves the per-capita electricity share.
    assert two.electricity == round(one.electricity / 2, 2)


def test_electricity_value_matches_factor():
    breakdown = calculate_breakdown(_make_input(electricity_kwh=100, household_size=1))
    expected = 100 * MONTHS_PER_YEAR * EMISSION_FACTORS["electricity_per_kwh"]
    assert breakdown.electricity == round(expected, 2)


def test_zero_everything_low():
    breakdown = calculate_breakdown(
        _make_input(weekly_km=0, transport_mode="bike_walk",
                    flights_per_year=0, diet_type="vegan",
                    electricity_kwh=0, gas_kwh=0)
    )
    assert breakdown.transport == 0
    assert breakdown.flights == 0
    assert breakdown.electricity == 0
    assert breakdown.gas == 0
    assert breakdown.total() == breakdown.diet
