"""Explainable AI insight engine.

This is the "smart assistant" at the heart of the product. It combines two
complementary techniques:

1. **A scikit-learn Random Forest classifier** that learns to rate a person's
   overall footprint (Low / Moderate / High / Very High) from their per-category
   emissions. The model is trained once, in-memory, on a synthetic but
   physically-grounded dataset, so the repository ships **no large binary model
   file** and stays well under the size budget.

2. **A transparent logic-tree recommender** that turns the same inputs into
   ranked, real-world actions, each annotated with an estimated annual saving.

Explainability (the "SHAP principles" requirement) is delivered by computing
**additive feature contributions**: for an additive footprint model the
contribution of each category is its signed deviation from an average-person
baseline. These contributions satisfy SHAP's core additivity property
(``baseline_total + sum(contributions) == prediction``), so the user can see
exactly *why* a rating and each suggestion were produced.
"""

from typing import Dict, List

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from app.models.footprint import CategoryBreakdown, Insight
from app.services.carbon_calculator import EMISSION_FACTORS
from app.utils.validation import FootprintInput

# Order of categories used consistently for every feature vector.
CATEGORIES = ("transport", "flights", "diet", "electricity", "gas")

# Reference "average person" per-category annual CO2e (kg). Used as the SHAP
# baseline so contributions are interpretable as "above / below average".
BASELINE_PROFILE: Dict[str, float] = {
    "transport": 1400.0,
    "flights": 500.0,
    "diet": 2500.0,
    "electricity": 700.0,
    "gas": 500.0,
}

# Rating bands keyed by total per-capita annual CO2e (kg). Ordered low -> high.
RATING_BANDS = (
    (3000.0, "Low"),
    (6000.0, "Moderate"),
    (10000.0, "High"),
    (float("inf"), "Very High"),
)


def _rating_for_total(total_kg: float) -> str:
    """Map a per-capita annual total (kg) to a rating label via the bands."""
    for threshold, label in RATING_BANDS:
        if total_kg < threshold:
            return label
    return RATING_BANDS[-1][1]  # pragma: no cover - inf guarantees a match


class InsightEngine:
    """Trains the classifier and produces ratings, explanations and insights.

    The model is trained lazily on first use and then cached on the instance,
    giving fast O(1) inference per request after a one-off O(N) training pass.
    """

    def __init__(self, n_samples: int = 1500, random_state: int = 42) -> None:
        """Create the engine.

        Args:
            n_samples: Size of the synthetic training set.
            random_state: Seed for fully reproducible training and predictions.
        """
        self._n_samples = n_samples
        self._random_state = random_state
        self._model = None  # type: RandomForestClassifier | None

    # ------------------------------------------------------------------ #
    # Model training
    # ------------------------------------------------------------------ #
    def _build_training_data(self):
        """Generate a synthetic, class-balanced training set.

        Sampling each category independently makes totals cluster around the
        mean (central-limit effect), starving the extreme rating bands. We
        instead use a two-stage generator that guarantees balanced classes:

        1. Pick a target rating band uniformly at random.
        2. Sample a total within that band's range, then split it across the
           five categories using a Dirichlet draw (so category proportions vary
           realistically while the total lands in the chosen band).

        Returns:
            ``(X, y)`` where ``X`` has shape ``(n_samples, 5)`` and ``y`` holds
            the string rating labels.
        """
        rng = np.random.default_rng(self._random_state)
        n = self._n_samples

        # Per-band sampling ranges for the total (kg CO2e / year). The upper
        # bound of "Very High" is capped to keep totals physically plausible.
        band_ranges = [
            (500.0, 3000.0),
            (3000.0, 6000.0),
            (6000.0, 10000.0),
            (10000.0, 18000.0),
        ]

        # Stage 1: choose a band per sample, then a total within it.
        band_idx = rng.integers(0, len(band_ranges), n)
        totals = np.array([rng.uniform(*band_ranges[i]) for i in band_idx])

        # Stage 2: split each total across the five categories with a Dirichlet
        # draw. ``alpha`` mildly favours diet/transport (real-world dominance)
        # while every category still varies widely.
        alpha = np.array([1.2, 1.0, 1.4, 1.0, 0.8])
        weights = rng.dirichlet(alpha, n)
        features = weights * totals[:, None]

        # Label from the single source of truth so training and inference agree.
        labels = np.array([_rating_for_total(t) for t in totals])
        return features, labels

    def _ensure_trained(self):
        """Train (once) and return the cached classifier."""
        if self._model is None:
            features, labels = self._build_training_data()
            # A small forest keeps training fast and the in-memory model tiny
            # while still capturing the decision boundaries cleanly.
            model = RandomForestClassifier(
                n_estimators=60,
                max_depth=8,
                random_state=self._random_state,
                n_jobs=1,
            )
            model.fit(features, labels)
            self._model = model
        return self._model

    # ------------------------------------------------------------------ #
    # Inference + explainability
    # ------------------------------------------------------------------ #
    @staticmethod
    def _vector(breakdown):
        """Convert a breakdown into the ordered feature vector."""
        values = breakdown.as_dict()
        return [values[cat] for cat in CATEGORIES]

    def classify(self, breakdown):
        """Predict the footprint rating and its confidence.

        Args:
            breakdown: Per-capita category breakdown.

        Returns:
            ``(rating, confidence)`` where ``confidence`` is the model's
            predicted-class probability in ``[0, 1]``.
        """
        model = self._ensure_trained()
        vector = np.array([self._vector(breakdown)])
        rating = str(model.predict(vector)[0])

        # Confidence = probability mass on the predicted class. ``predict`` only
        # ever returns a label in ``classes_``; the ``in`` guard is defensive so
        # confidence is always well-defined.
        proba = model.predict_proba(vector)[0]
        classes = list(model.classes_)
        if rating in classes:
            confidence = float(proba[classes.index(rating)])
        else:  # pragma: no cover - defensive only
            confidence = float(proba.max())
        return rating, confidence

    @staticmethod
    def feature_contributions(breakdown):
        """Compute SHAP-style additive contributions per category.

        For this additive footprint model, the contribution of a category is
        its signed deviation from the average-person baseline. The values
        satisfy the additivity property::

            baseline_total + sum(contributions) == prediction_total

        Positive values push the footprint above average; negative values pull
        it below.

        Args:
            breakdown: Per-capita category breakdown.

        Returns:
            Mapping of category -> signed contribution (kg CO2e), rounded.
        """
        values = breakdown.as_dict()
        return {
            cat: round(values[cat] - BASELINE_PROFILE[cat], 2)
            for cat in CATEGORIES
        }

    # ------------------------------------------------------------------ #
    # Recommendation logic tree
    # ------------------------------------------------------------------ #
    def generate_insights(self, data, breakdown):
        """Produce ranked, explainable actions tailored to the user.

        The logic tree inspects each lifestyle category and, where there is a
        meaningful reduction opportunity, emits an :class:`Insight` with a
        quantified annual saving and a plain-language reason. Insights are
        sorted by impact (largest saving first) and assigned a priority.

        Args:
            data: The validated raw inputs (needed for mode/diet context).
            breakdown: The computed per-capita breakdown.

        Returns:
            A list of insights ordered by descending annual saving.
        """
        contributions = self.feature_contributions(breakdown)
        insights = []  # type: List[Insight]

        # --- Transport: shift some petrol-car km to rail/active travel ------
        if data.transport_mode == "car_petrol" and data.weekly_km > 50:
            petrol = EMISSION_FACTORS["transport_per_km"]["car_petrol"]
            train = EMISSION_FACTORS["transport_per_km"]["train"]
            shift_fraction = 0.30  # assume ~30% of km can realistically shift
            saving = breakdown.transport * shift_fraction * (1 - train / petrol)
            reason = (
                "Transport adds %+.0f kg vs an average person - one of your "
                "largest levers." % contributions["transport"]
            )
            insights.append(Insight(
                category="transport",
                title="Shift ~30% of car trips to rail or active travel",
                detail=(
                    "Replacing roughly a third of your petrol-car kilometres "
                    "with train, bus, cycling or walking keeps the journeys "
                    "you need while cutting the most carbon-intensive ones."
                ),
                annual_saving_kg=round(saving, 1),
                reason=reason,
                priority=0,
            ))

        # --- Flights: remove one one-way flight per year --------------------
        if data.flights_per_year >= 2:
            saving = EMISSION_FACTORS["flight_per_trip"]
            reason = (
                "You logged %.0f flights/year, contributing %+.0f kg vs "
                "average." % (data.flights_per_year, contributions["flights"])
            )
            insights.append(Insight(
                category="flights",
                title="Take one fewer flight per year",
                detail=(
                    "Air travel is carbon-dense per hour. Combining trips, "
                    "choosing rail for short hops, or holidaying closer to "
                    "home removes a whole flight's worth of emissions."
                ),
                annual_saving_kg=round(saving, 1),
                reason=reason,
                priority=0,
            ))

        # --- Diet: shift toward plant-based meals ---------------------------
        if data.diet_type in ("omnivore", "high_meat"):
            target = EMISSION_FACTORS["diet_per_year"]["vegetarian"]
            saving = max(0.0, breakdown.diet - target)
            reason = (
                "Your diet contributes %+.0f kg vs average; plant-rich meals "
                "close most of that gap." % contributions["diet"]
            )
            insights.append(Insight(
                category="diet",
                title="Move toward more plant-based meals",
                detail=(
                    "Shifting several meat-heavy meals a week to vegetarian "
                    "options is one of the highest-impact everyday changes you "
                    "can make."
                ),
                annual_saving_kg=round(saving, 1),
                reason=reason,
                priority=0,
            ))

        # --- Electricity: only if above the average share -------------------
        if contributions["electricity"] > 0:
            saving = breakdown.electricity * 0.80  # green tariff ~ -80% grid
            reason = (
                "Electricity is %+.0f kg above the average per-person share."
                % contributions["electricity"]
            )
            insights.append(Insight(
                category="electricity",
                title="Switch to a certified renewable electricity tariff",
                detail=(
                    "A green tariff plus simple efficiency wins (LED lighting, "
                    "switching appliances off standby) sharply lowers the "
                    "carbon intensity of the power you use."
                ),
                annual_saving_kg=round(saving, 1),
                reason=reason,
                priority=0,
            ))

        # --- Gas / heating: only if above the average share -----------------
        if contributions["gas"] > 0:
            saving = breakdown.gas * 0.15  # insulation + thermostat ~ -15%
            reason = (
                "Heating gas is %+.0f kg above the average per-person share."
                % contributions["gas"]
            )
            insights.append(Insight(
                category="gas",
                title="Cut heating demand with insulation and a lower thermostat",
                detail=(
                    "Turning the thermostat down a degree, draught-proofing "
                    "and better insulation reduce the gas burned for heating "
                    "without sacrificing comfort."
                ),
                annual_saving_kg=round(saving, 1),
                reason=reason,
                priority=0,
            ))

        # Rank by impact (largest saving first) and assign 1-based priority.
        insights.sort(key=lambda item: item.annual_saving_kg, reverse=True)
        ranked = [
            Insight(
                category=item.category,
                title=item.title,
                detail=item.detail,
                annual_saving_kg=item.annual_saving_kg,
                reason=item.reason,
                priority=rank,
            )
            for rank, item in enumerate(insights, start=1)
        ]
        return ranked
