# Carbon Footprint Assistant

A lightweight, production-ready web app that helps individuals **understand,
track, and reduce their carbon footprint**. It pairs a **3D animated AI
assistant** ("Terra") that answers carbon-footprint questions with a
personalised, *explainable* footprint calculator.

Built with **Python (Flask)**, a **scikit-learn** AI core (Random Forest for
rating + TF-IDF retrieval for the chatbot), and an **accessibility-first vanilla
HTML/CSS/JS** frontend with a **Three.js** 3D avatar.

---

## Chosen Vertical

**Personal Carbon Footprint Management.**

The product targets everyday individuals who want a clear, honest picture of
their annual emissions, concrete actions to lower them, and a friendly assistant
to answer their questions - without needing any climate-science background.

---

## Approach and Logic

### 1. The 3D AI assistant ("Terra")

A conversational assistant answers free-text questions about carbon footprints
(travel, food, home energy, recycling, offsetting, EVs, net zero and more). It
uses a **hybrid** strategy so it is both reliable and flexible:

- **Knowledge base (always on, no secrets):** a curated set of carbon-footprint
  Q&A entries (`app/services/knowledge_base.py`) is indexed with a **TF-IDF +
  cosine-similarity** retriever (`app/services/chat_assistant.py`). This answers
  a broad range of questions instantly, fully offline, with **no API key**.
- **Optional LLM augmentation:** if (and only if) an `LLM_API_KEY` environment
  variable is set, low-confidence questions are forwarded to an
  OpenAI-compatible endpoint for an open-ended answer. The call uses only the
  Python standard library (no extra dependency), is time-limited, and **falls
  back gracefully** to the knowledge base on any error. **No key is ever
  hard-coded or committed.**

The assistant is visualised as a **3D animated globe** rendered with Three.js.
It reacts to conversation state - idling (gentle float and spin), *thinking*
(faster spin and warmer glow while a reply is fetched), and *speaking* (a soft
pulse as the answer arrives) - making the experience attractive and interactive
while remaining fully accessible (the canvas is decorative; the conversation
carries all meaning, and there is a reduced-motion / no-WebGL fallback).

### 2. Deterministic carbon calculation

`app/services/carbon_calculator.py` converts inputs into annual CO2e using
named, auditable emission factors. Shared **household** energy is divided by
household size for a fair per-capita share; personal categories (transport,
flights, diet) are attributed in full. The calculation is pure and **O(1)**.

### 3. Data-trained AI rating (Random Forest on a real dataset)

The footprint **rating** (Low / Medium / High) is produced by a
**scikit-learn `RandomForestClassifier` trained on a real Kaggle dataset** -
`data/personal_carbon_footprint_behavior.csv` (1,400 behaviour records).
`app/services/rating_model.py` loads the CSV with the standard-library `csv`
module (no pandas), encodes its categorical features with explicit
emission-ordered maps, trains the forest to predict `carbon_impact_level`, and
reports a **held-out accuracy** score for transparency. The model trains once
and is cached.

At assessment time the user's form inputs are mapped into the dataset's
per-person, per-day feature space (weekly travel and monthly energy are
converted to daily values; transport mode and diet map to the dataset's
categories; fields the form does not collect are filled with dataset-typical
defaults). If the CSV is ever unavailable, the app **falls back** to a synthetic
class-balanced Random Forest (`app/services/insight_engine.py`, a two-stage
band-then-Dirichlet generator) so it never breaks.

Explainability follows **SHAP principles**: because the deterministic footprint
model is additive, each category's contribution is its signed deviation from an
average-person baseline, satisfying the additivity property:

```
baseline_total + sum(contributions) == predicted_total
```

A transparent **logic tree** then turns the inputs into ranked, quantified,
explained actions.

### Architecture (clean / MVC separation)

Flask is confined to the `routes` layer; all logic lives in framework-free
`services`, `controllers`, `models`, and `utils`, so the core is fully
unit-testable without a web server.

```
Carbon Footprint Awareness Platform/
|-- app/
|   |-- __init__.py              # Flask application factory + security headers
|   |-- config.py               # Env-driven config; SECURITY_HEADERS (no secrets)
|   |-- models/
|   |   `-- footprint.py         # Framework-free domain dataclasses
|   |-- services/
|   |   |-- carbon_calculator.py # Deterministic emission-factor calculator
|   |   |-- rating_model.py       # Random Forest trained on the real CSV dataset
|   |   |-- insight_engine.py    # Synthetic-fallback rating + SHAP explanation
|   |   |-- chat_assistant.py    # Hybrid chatbot (TF-IDF KB + optional LLM)
|   |   `-- knowledge_base.py    # Curated carbon-footprint Q&A data
|   |-- controllers/
|   |   |-- footprint_controller.py  # Assessment pipeline
|   |   `-- chat_controller.py       # Chat assistant orchestration
|   |-- routes/
|   |   `-- api.py               # Thin HTTP layer (assess, baseline, chat)
|   `-- utils/
|       |-- validation.py        # Strict input validation (bounds + allow-lists)
|       `-- security.py          # Input sanitisation (anti-XSS)
|-- frontend/
|   |-- index.html               # Semantic, WCAG 2.1 AA accessible UI
|   |-- css/styles.css           # Glass/gradient theme, high contrast, a11y
|   `-- js/
|       |-- app.js               # Chat + form logic (textContent only)
|       `-- avatar.js            # Three.js 3D animated assistant
|-- data/
|   `-- personal_carbon_footprint_behavior.csv  # Kaggle training data (~80 KB)
|-- tests/
|   |-- conftest.py
|   |-- test_validation.py
|   |-- test_calculator.py
|   |-- test_insight_engine.py
|   |-- test_rating_model.py
|   |-- test_chat.py
|   `-- test_api.py
|-- run.py                       # Entry point (python run.py / gunicorn run:app)
|-- requirements.txt
|-- pytest.ini
|-- Procfile / render.yaml / runtime.txt   # Deployment
|-- .gitignore                   # Keeps the repo well under 10 MB
`-- README.md
```

---

## How it works

### Setup and run (local)

> Requires Python 3.11+ (3.10 also works).

```bash
git clone <your-public-github-repo-url>
cd "Carbon Footprint Awareness Platform"

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python run.py
# Open http://localhost:5000
```

### Using the app

1. **Chat with Terra:** type a question (or tap a suggestion chip) in the "Ask
   the carbon assistant" panel. The 3D avatar animates as it thinks and replies.
2. **Measure your footprint:** fill in the short form (travel, flights, diet,
   home energy, household size) and press **"Get my insights"**.
3. **Read your result:** an overall rating, your annual footprint (per person
   and household-inclusive), an animated breakdown, and a ranked action plan
   where each suggestion explains its reasoning and estimated yearly saving.

### Optional: enable the LLM brain

The chatbot works fully without any key. To enable open-ended answers for
questions outside the knowledge base, set these environment variables (e.g. in
your hosting dashboard - never commit them):

| Variable      | Required | Default                                        |
|---------------|----------|------------------------------------------------|
| `LLM_API_KEY` | no       | (unset; KB-only when absent)                   |
| `LLM_API_URL` | no       | `https://api.openai.com/v1/chat/completions`   |
| `LLM_MODEL`   | no       | `gpt-4o-mini`                                   |

### API

| Method | Endpoint                | Purpose                                   |
|--------|-------------------------|-------------------------------------------|
| POST   | `/api/assess`           | Run a full footprint assessment (JSON).   |
| POST   | `/api/chat`             | Ask the assistant (`{"message": "..."}`). |
| GET    | `/api/chat/suggestions` | Seed topics for the chat UI.              |
| GET    | `/api/baseline`         | Average-person baseline used in reasons.  |
| GET    | `/health`               | Liveness probe.                           |

Example:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How do I reduce my flights?"}'
```

### Running the tests

```bash
pytest
```

Runs the full suite with coverage (`--cov=app`). It covers the calculator, the
AI rating engine (class balance, classification, SHAP additivity, insight
ranking), the chat assistant (knowledge-base matching, fallback, sanitisation,
endpoints), validation/sanitisation, and the API including security headers.

### Deployment (free tier)

The repo includes `Procfile`, `render.yaml`, and `runtime.txt`. On
**Render.com**, "New + > Blueprint" reads `render.yaml` and deploys
`gunicorn run:app`. `SECRET_KEY` is generated by the platform and never
committed; add `LLM_API_KEY` only if you want the LLM brain. The same `Procfile`
works on Heroku.

---

## How this maps to the evaluation criteria

- **Code Quality** - Clean MVC/clean-architecture separation, heavy docstrings
  and comments, PEP-8 style, descriptive naming, framework-free core logic.
- **Security** - Strict input validation (bounds + categorical allow-lists),
  server-side sanitisation against XSS for both the form and the chat, hardened
  HTTP security headers (CSP with a single documented cdnjs exception for
  Three.js, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy),
  request-size cap, frontend rendering via `textContent` only, and **no
  hard-coded secrets** (all env-driven, including the optional LLM key).
- **Efficiency** - O(1) calculation per request; ML rating model and TF-IDF
  index each built once and cached; minimal dependencies; Three.js loaded from
  CDN (off-repo); no large binaries - the repo stays well under 10 MB.
- **Testing** - Comprehensive `pytest` suite across all core modules, designed
  for high (>85%) coverage of the application logic.
- **Accessibility** - WCAG 2.1 AA: semantic HTML, labelled controls, ARIA live
  regions (chat log + results), skip link, full keyboard navigability, visible
  focus rings, >= 4.5:1 colour contrast, non-colour cues, a decorative 3D canvas
  with a text label, and reduced-motion / no-WebGL fallbacks.
- **Problem Statement Alignment** - A dynamic assistant takes real user context
  (travel, food, energy) and provides logical, explainable, actionable insights,
  plus a conversational coach for any carbon question.

---

## Assumptions made during development

1. **Emission factors** are rounded mid-range values from public life-cycle
   datasets (e.g. UK DEFRA, IPCC); they are global-average approximations, not
   region-specific. Exact values live in `EMISSION_FACTORS`.
2. **One flight** is a single one-way trip at 250 kg CO2e (short/medium-haul
   average incl. radiative forcing); a return trip counts as two.
3. **Diet** is modelled as a representative annual figure per dietary pattern.
4. **Home energy is shared**: electricity and gas are entered at the household
   level and divided by household size.
5. **Rating** comes from the Random Forest trained on the Kaggle
   `personal_carbon_footprint_behavior` dataset and uses that dataset's classes
   (Low / Medium / High, which are bands of daily `carbon_footprint_kg`). The
   app form does not collect every dataset feature (renewable %, screen time,
   waste, eco-actions, day type), so those are filled with dataset-typical
   defaults at inference; the synthetic fallback uses bands of the annual total
   (Low < 3000, Moderate < 6000, High < 10000, else Very High kg/person/year).
6. **No database / accounts**: the app is stateless per request; data lives only
   in the browser session and is never persisted.
7. **The ML model and chatbot index are built at runtime** on bundled data, so
   the repository ships no large model binary; rating results are reproducible
   via a fixed random seed.
8. **The chatbot is scoped to carbon and sustainability.** The knowledge base
   covers the core topics; the optional LLM (if enabled) is instructed to stay
   on-topic. Without an LLM key, out-of-scope questions get a helpful fallback
   with suggested topics.
9. **Three.js is loaded from cdnjs** to keep the repo tiny; this is the only
   external origin permitted by the Content-Security-Policy, and the 3D avatar
   degrades gracefully to a CSS fallback if the CDN or WebGL is unavailable.

---

## Credits & Data Sources

All application code (backend, frontend, AI logic, and tests) was written
originally for this project. The following third-party resources are used with
attribution:

- **Training data:** *Personal Carbon Footprint Behavior Dataset* by
  **sonalshinde123**, via Kaggle
  (`kaggle.com/datasets/sonalshinde123/personal-carbon-footprint-behavior-dataset`).
  Used to train the Random Forest impact-rating model. All credit for the
  dataset belongs to its original author.
- **Emission factors** in `carbon_calculator.py` are rounded mid-range values
  derived from publicly available life-cycle datasets, primarily the UK
  Government **DEFRA / BEIS Greenhouse Gas Conversion Factors** and **IPCC**
  guidance. They are approximations for awareness, not certified figures.
- **Open-source libraries:** Flask, scikit-learn, NumPy, python-dotenv
  (backend) and Three.js (3D avatar, loaded from cdnjs). These remain the
  property of their respective maintainers under their open-source licences.

No code, text, or assets were copied from existing carbon-footprint
applications; any resemblance in boilerplate (e.g. a Flask app factory or a
Three.js scene setup) reflects standard, widely used patterns.

---

*Estimates are for awareness and guidance only and should not be treated as a
certified carbon audit.*
