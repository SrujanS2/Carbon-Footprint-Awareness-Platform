"""Strict input validation for the carbon-footprint API.

All numeric inputs are validated against explicit, physically-reasonable
bounds. Validation is centralised here so both the controller and the test
suite share one source of truth. A failed validation raises
:class:`ValidationError`, which the route layer maps to an HTTP 400.
"""

from dataclasses import dataclass
from typing import Any, Dict

from app.utils.security import sanitize_text


class ValidationError(ValueError):
    """Raised when user input fails validation.

    Carries a human-readable ``message`` describing the first problem found so
    the frontend can show a precise, actionable error.
    """


# Allowed categorical values. Using explicit allow-lists (rather than free
# text) is itself a security control: unexpected values are rejected outright.
DIET_TYPES = ("vegan", "vegetarian", "pescatarian", "omnivore", "high_meat")
TRANSPORT_MODES = ("car_petrol", "car_electric", "bus", "train", "bike_walk")

# (minimum, maximum) bounds for each numeric field. Bounds are generous enough
# for real users but tight enough to reject nonsense / abusive input.
_NUMERIC_BOUNDS: Dict[str, tuple] = {
    "weekly_km": (0.0, 5000.0),          # distance travelled per week (km)
    "flights_per_year": (0.0, 200.0),    # number of one-way flights / year
    "electricity_kwh": (0.0, 5000.0),    # household electricity / month (kWh)
    "gas_kwh": (0.0, 8000.0),            # household gas / month (kWh)
    "household_size": (1.0, 20.0),       # people sharing the household
}


@dataclass(frozen=True)
class FootprintInput:
    """Validated, immutable representation of a user's lifestyle inputs.

    Using a frozen dataclass guarantees the validated payload cannot be mutated
    further downstream, removing a class of accidental-tampering bugs.
    """

    weekly_km: float
    transport_mode: str
    flights_per_year: float
    diet_type: str
    electricity_kwh: float
    gas_kwh: float
    household_size: float
    region: str


def _coerce_number(field: str, raw: Any) -> float:
    """Coerce ``raw`` to ``float`` and bounds-check it.

    Args:
        field: Field name (used for bounds lookup and error messages).
        raw: The raw value from the request payload.

    Returns:
        The validated floating-point value.

    Raises:
        ValidationError: If the value is missing, non-numeric or out of bounds.
    """
    if raw is None or raw == "":
        raise ValidationError(f"'{field}' is required.")
    try:
        # ``bool`` is a subclass of ``int``; reject it explicitly so True/False
        # cannot masquerade as 1/0.
        if isinstance(raw, bool):
            raise ValueError
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a number.")

    # NaN/inf are never valid footprint inputs.
    if value != value or value in (float("inf"), float("-inf")):
        raise ValidationError(f"'{field}' must be a finite number.")

    low, high = _NUMERIC_BOUNDS[field]
    if not (low <= value <= high):
        raise ValidationError(
            f"'{field}' must be between {low:g} and {high:g}."
        )
    return value


def validate_payload(payload: Any) -> FootprintInput:
    """Validate and sanitise a raw request payload.

    Args:
        payload: The decoded JSON body (expected to be a ``dict``).

    Returns:
        A :class:`FootprintInput` with every field validated.

    Raises:
        ValidationError: On any missing field, wrong type or out-of-range value.
    """
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object.")

    # --- Numeric fields -----------------------------------------------------
    numbers = {
        field: _coerce_number(field, payload.get(field))
        for field in _NUMERIC_BOUNDS
    }

    # --- Categorical fields (validated against allow-lists) -----------------
    transport_mode = str(payload.get("transport_mode", "")).strip().lower()
    if transport_mode not in TRANSPORT_MODES:
        raise ValidationError(
            "'transport_mode' must be one of: " + ", ".join(TRANSPORT_MODES)
        )

    diet_type = str(payload.get("diet_type", "")).strip().lower()
    if diet_type not in DIET_TYPES:
        raise ValidationError(
            "'diet_type' must be one of: " + ", ".join(DIET_TYPES)
        )

    # --- Free-text field (sanitised; optional) ------------------------------
    region = sanitize_text(str(payload.get("region", "")), max_length=60)

    return FootprintInput(
        weekly_km=numbers["weekly_km"],
        transport_mode=transport_mode,
        flights_per_year=numbers["flights_per_year"],
        diet_type=diet_type,
        electricity_kwh=numbers["electricity_kwh"],
        gas_kwh=numbers["gas_kwh"],
        household_size=numbers["household_size"],
        region=region,
    )
