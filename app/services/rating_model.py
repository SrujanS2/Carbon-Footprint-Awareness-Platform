"""Data-trained carbon impact-rating model.

Trains a scikit-learn Random Forest on the real
``personal_carbon_footprint_behavior`` dataset to predict a person's
``carbon_impact_level`` (Low / Medium / High) from their daily behaviour, then
uses it to rate a user's lifestyle in the app.

Design:
* The dataset is loaded with the standard-library ``csv`` module (no pandas
  dependency, keeping the build small).
* Categorical features are encoded with explicit, emission-ordered maps so the
  exact same encoding is used at training time and at inference time.
* The model is trained once and cached, with a held-out accuracy score reported
  for transparency.
* If the dataset file is missing (e.g. it was not deployed), the model reports
  itself unavailable and the caller falls back to the synthetic rating engine -
  so the app never breaks.
"""

import csv
import os
import statistics
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from app.utils.validation import FootprintInput

# Location of the bundled training data (overridable via env for flexibility).
_DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "personal_carbon_footprint_behavior.csv",
)
DATASET_PATH = os.environ.get("FOOTPRINT_DATASET", _DEFAULT_CSV)

# --- Explicit, emission-ordered categorical encodings ---------------------- #
# Ordering low-impact -> high-impact gives the trees a meaningful axis.
TRANSPORT_ENC = {"Walk": 0, "Bike": 1, "Bus": 2, "EV": 3, "Car": 4}
FOOD_ENC = {"Veg": 0, "Mixed": 1, "Non-Veg": 2}
DAY_ENC = {"Weekday": 0, "Weekend": 1}

# Feature column order used for every vector (training and inference).
FEATURE_ORDER = (
    "day_type", "transport_mode", "distance_km", "electricity_kwh",
    "renewable_usage_pct", "food_type", "screen_time_hours",
    "waste_generated_kg", "eco_actions",
)

# --- Maps from the app's input vocabulary to the dataset's vocabulary ------ #
APP_TRANSPORT_TO_DATASET = {
    "bike_walk": "Walk",
    "bus": "Bus",
    "train": "Bus",        # rail has no dataset category; treat as public transit
    "car_electric": "EV",
    "car_petrol": "Car",
}
APP_DIET_TO_FOOD = {
    "vegan": "Veg",
    "vegetarian": "Veg",
    "pescatarian": "Mixed",
    "omnivore": "Mixed",
    "high_meat": "Non-Veg",
}


class DataRatingModel:
    """Random Forest rating model trained on the real behaviour dataset."""

    def __init__(self, csv_path: str = DATASET_PATH, random_state: int = 42):
        self._csv_path = csv_path
        self._random_state = random_state
        self._model = None            # type: Optional[RandomForestClassifier]
        self._accuracy = None         # type: Optional[float]
        self._n_samples = 0
        self._defaults = {}           # type: Dict[str, float]
        self._loaded = False
        self._available = False

    # ------------------------------------------------------------------ #
    # Training
    # ------------------------------------------------------------------ #
    def _encode_row(self, row: Dict[str, str]) -> List[float]:
        """Encode one dataset row into the ordered numeric feature vector."""
        return [
            DAY_ENC.get(row["day_type"], 0),
            TRANSPORT_ENC.get(row["transport_mode"], 0),
            float(row["distance_km"]),
            float(row["electricity_kwh"]),
            float(row["renewable_usage_pct"]),
            FOOD_ENC.get(row["food_type"], 1),
            float(row["screen_time_hours"]),
            float(row["waste_generated_kg"]),
            float(row["eco_actions"]),
        ]

    def _train(self) -> None:
        """Load the dataset and fit the classifier (idempotent)."""
        if self._loaded:
            return
        self._loaded = True

        if not os.path.exists(self._csv_path):
            # No dataset available -> stay unavailable; caller will fall back.
            self._available = False
            return

        with open(self._csv_path, newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            self._available = False
            return

        features = np.array([self._encode_row(r) for r in rows], dtype=float)
        labels = np.array([r["carbon_impact_level"] for r in rows])
        self._n_samples = len(rows)

        # Remember typical values for the fields the app form does not collect,
        # so we can supply realistic defaults at inference time.
        self._defaults = {
            "renewable_usage_pct": statistics.median(
                float(r["renewable_usage_pct"]) for r in rows),
            "screen_time_hours": statistics.median(
                float(r["screen_time_hours"]) for r in rows),
            "waste_generated_kg": statistics.median(
                float(r["waste_generated_kg"]) for r in rows),
            "eco_actions": statistics.median(
                float(r["eco_actions"]) for r in rows),
        }

        # Held-out split for an honest accuracy estimate, stratified by label.
        x_train, x_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2,
            random_state=self._random_state, stratify=labels,
        )
        model = RandomForestClassifier(
            n_estimators=120, max_depth=10,
            random_state=self._random_state, n_jobs=1,
        )
        model.fit(x_train, y_train)
        self._accuracy = float(accuracy_score(y_test, model.predict(x_test)))

        # Refit on the full dataset for the best production model.
        model.fit(features, labels)
        self._model = model
        self._available = True

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        """True when the dataset loaded and the model is ready."""
        self._train()
        return self._available

    @property
    def accuracy(self) -> Optional[float]:
        """Held-out accuracy of the trained model, or ``None`` if unavailable."""
        self._train()
        return self._accuracy

    @property
    def n_samples(self) -> int:
        """Number of training rows used."""
        self._train()
        return self._n_samples

    def _vector_from_input(self, data: FootprintInput) -> List[float]:
        """Map a validated app input to the model's daily feature vector.

        The app collects weekly travel and monthly household energy, so values
        are converted to the dataset's per-person, per-day basis. Fields the
        form does not collect are filled with dataset-typical defaults.
        """
        transport = APP_TRANSPORT_TO_DATASET.get(data.transport_mode, "Car")
        food = APP_DIET_TO_FOOD.get(data.diet_type, "Mixed")

        distance_daily = data.weekly_km / 7.0
        # Monthly household kWh -> per-person daily kWh.
        electricity_daily = data.electricity_kwh / 30.0 / data.household_size

        return [
            DAY_ENC["Weekday"],                       # rate a typical weekday
            TRANSPORT_ENC[transport],
            distance_daily,
            electricity_daily,
            self._defaults.get("renewable_usage_pct", 25.0),
            FOOD_ENC[food],
            self._defaults.get("screen_time_hours", 5.5),
            self._defaults.get("waste_generated_kg", 0.7),
            self._defaults.get("eco_actions", 1.0),
        ]

    def rate(self, data: FootprintInput) -> Optional[Tuple[str, float]]:
        """Return ``(level, confidence)`` from the data-trained model.

        Returns ``None`` when the model is unavailable so the caller can fall
        back to the synthetic rating engine.
        """
        if not self.available:
            return None
        vector = np.array([self._vector_from_input(data)])
        level = str(self._model.predict(vector)[0])
        proba = self._model.predict_proba(vector)[0]
        classes = list(self._model.classes_)
        confidence = (
            float(proba[classes.index(level)]) if level in classes
            else float(proba.max())
        )
        return level, confidence
