"""Unit tests for input validation and sanitisation."""

import pytest

from app.utils.security import sanitize_text
from app.utils.validation import (
    FootprintInput,
    ValidationError,
    validate_payload,
)


def _base_payload():
    """Return a minimal valid payload dict for mutation in tests."""
    return {
        "weekly_km": 100,
        "transport_mode": "train",
        "flights_per_year": 1,
        "diet_type": "vegetarian",
        "electricity_kwh": 200,
        "gas_kwh": 100,
        "household_size": 2,
        "region": "Anytown",
    }


def test_validate_payload_returns_dataclass():
    result = validate_payload(_base_payload())
    assert isinstance(result, FootprintInput)
    assert result.transport_mode == "train"
    assert result.diet_type == "vegetarian"


def test_payload_must_be_object():
    with pytest.raises(ValidationError):
        validate_payload(["not", "a", "dict"])


@pytest.mark.parametrize("field", [
    "weekly_km", "flights_per_year", "electricity_kwh", "gas_kwh",
    "household_size",
])
def test_missing_numeric_field_rejected(field):
    payload = _base_payload()
    del payload[field]
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_non_numeric_value_rejected():
    payload = _base_payload()
    payload["weekly_km"] = "fast"
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_boolean_not_accepted_as_number():
    payload = _base_payload()
    payload["weekly_km"] = True
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_out_of_range_value_rejected():
    payload = _base_payload()
    payload["weekly_km"] = 99999  # above the 5000 km bound
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_negative_value_rejected():
    payload = _base_payload()
    payload["flights_per_year"] = -1
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_infinite_value_rejected():
    payload = _base_payload()
    payload["gas_kwh"] = float("inf")
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_invalid_transport_mode_rejected():
    payload = _base_payload()
    payload["transport_mode"] = "teleport"
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_invalid_diet_rejected():
    payload = _base_payload()
    payload["diet_type"] = "carnivore"
    with pytest.raises(ValidationError):
        validate_payload(payload)


def test_region_is_sanitised():
    payload = _base_payload()
    payload["region"] = "<script>alert('x')</script>City"
    result = validate_payload(payload)
    assert "<" not in result.region
    assert "script" in result.region  # text kept, tags neutralised


def test_household_minimum_enforced():
    payload = _base_payload()
    payload["household_size"] = 0
    with pytest.raises(ValidationError):
        validate_payload(payload)


# --- sanitize_text directly ------------------------------------------------
def test_sanitize_text_escapes_html():
    out = sanitize_text("<b>hi</b>")
    assert "<" not in out and "&lt;" in out


def test_sanitize_text_handles_non_string():
    assert sanitize_text(12345) == ""


def test_sanitize_text_truncates():
    out = sanitize_text("a" * 500, max_length=10)
    assert len(out) <= 10
