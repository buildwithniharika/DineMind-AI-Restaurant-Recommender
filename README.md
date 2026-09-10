# AI-Powered Restaurant Recommendation System (Zomato Use Case)

Personalized restaurant recommendations using the Hugging Face Zomato dataset and an LLM.

**Docs:** [Problem Statement](Docs/problem_Statement.md) · [Architecture](Docs/architecture.md) · [Implementation Plan](Docs/implementation-plan.md) · [Edge Cases](Docs/edge-case.md)

---

## Current status

**Phases 1–5 are implemented.** Data → filter → LLM → FastAPI → **DineMind Streamlit UI** (Stitch white-light design).

---

## Requirements

| Item | Details |
|------|---------|
| Python | **3.11+** (3.12 recommended) |
| Git | Repository already initialized |
| LLM API key | **Groq** (`GROQ_API_KEY`) for Phase 3; OpenAI / Ollama optional |
| Network | Hugging Face download (~574 MB) for first data prep |

---

## Setup

```bash
# 1. Use Python 3.11+
python3.12 --version   # or python3.11

# 2. Create and activate a virtual environment
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set GROQ_API_KEY=gsk-... (LLM_PROVIDER=groq by default)

# 5. Verify prerequisites
python scripts/check_prerequisites.py
```

### Environment variables

See [`.env.example`](.env.example). Important keys:

- `LLM_PROVIDER` — `groq` (default) | `openai` | `ollama`
- `GROQ_API_KEY` (required for Groq) / `OPENAI_API_KEY` (if using OpenAI)
- `LLM_MODEL` — default `qwen/qwen3.8-27b`
- `MAX_CANDIDATES`, `TOP_N_DEFAULT`
- Budget tier caps and dataset paths

---

## Phase 1 — Prepare the dataset

The Hugging Face dataset [`ManikaSaini/zomato-restaurant-recommendation`](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) is a Bangalore Zomato listings dump (~51,717 rows). The prepare script downloads it (once), cleans it, and writes a local Parquet cache.

```bash
python scripts/prepare_data.py
# Rebuild from the Hugging Face cache:
python scripts/prepare_data.py --force
```

Output: `data/processed/restaurants.parquet`

Each cached record includes: `id`, `name`, `location`, `cuisines`, `average_cost_for_two`, `rating`, plus `city`, `votes`, `address`, and `rest_type`.

**Note:** Raw rows repeat the same restaurant under multiple listing types. After dropping missing name/location/rating and deduplicating by name + location, the unique restaurant count is lower than the raw 51k (typically ~10–12k). `location` is a Bangalore locality (e.g. Koramangala); `city` is set to Bangalore.

### Field mapping (raw → internal)

| Raw column | Internal field |
|------------|----------------|
| `name` | `name` |
| `location` | `location` (locality) |
| `cuisines` | `cuisines` (list) |
| `approx_cost(for two people)` | `average_cost_for_two` |
| `rate` | `rating` (from `"4.1/5"`) |
| `votes` | `votes` |
| `address` | `address` |
| `rest_type` | `rest_type` |

---

## Phase 2 — Filter against preferences

Domain models live under `src/models/`. Deterministic filtering is in `src/filters/restaurant_filter.py`.

```bash
# Demo: run 3 sample preference queries against the cache
python scripts/demo_filter.py
```

Location matches both locality (`location`) and metro (`city`), so `Bangalore` works even when rows store localities like Koramangala. Cuisine uses case-insensitive token membership (`"Italian"` must appear in the cuisine list; `"Indian"` does not match `"North Indian"`).

Budget tiers (cost for two, INR): low ≤ 500 · medium 501–1500 · high > 1500.

## Phase 3 — LLM ranking & explanations

Primary provider is **Groq** (`qwen/qwen3.8-27b`). OpenAI and Ollama remain available via `LLM_PROVIDER`. Prompts/parsing live under `src/llm/`; fallback under `src/services/`. See [Docs/prompts.md](Docs/prompts.md).

```bash
# Demo: filter → LLM (or fallback) → ranked recommendations
python scripts/demo_llm.py

# Force rule-based ranking (no API key needed)
python scripts/demo_llm.py --fallback-only
```

On LLM failure or invalid JSON, the service retries once, then returns `source: "fallback"` with template explanations.

## Phase 4 — API & orchestration

FastAPI app: `src/main.py`. Dataset loads once at startup; routes live in `src/api/routes.py`.

```bash
# Start API (Swagger UI at http://127.0.0.1:8000/docs)
uvicorn src.main:app --reload --port 8000

# In another terminal — hit health, metadata, recommendations
python scripts/demo_api.py
```

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health + dataset loaded |
| GET | `/api/metadata` | Locations, cuisines, budgets |
| POST | `/api/recommendations` | Ranked recommendations |

Errors: `400` validation · `404` no matches · `502` engine failure · `503` dataset not loaded.

## Phase 5 — DineMind UI (Stitch)

Streamlit app styled from [`Docs/design/stitch/`](Docs/design/stitch/) (exported from `stitch_dinemind_ai_restaurant_recommender_ui.zip`): preference panel, loading / empty / error canvases, and ranked recommendation cards.

```bash
streamlit run streamlit_app.py
# equivalent: streamlit run app/streamlit_app.py
```

Uses `RecommendationService` in-process (same pipeline as the API). Set `GROQ_API_KEY` for LLM explanations; without a key, cards still render via filter + fallback rationales.

## Deploy on Streamlit Community Cloud

The public repo is [buildwithniharika/DineMind-AI-Restaurant-Recommender](https://github.com/buildwithniharika/DineMind-AI-Restaurant-Recommender). Community Cloud builds from GitHub and does not read a local `.env`.

1. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2. **Create app** and select this repository (`main`).
3. Set **Main file path** to `streamlit_app.py`.
4. In **Advanced settings**, choose **Python 3.12** (avoid a 3.13+ default if the deploy UI offers it).
5. Paste secrets from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example) and set a real `GROQ_API_KEY` from the [Groq console](https://console.groq.com/):

```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "gsk_your_key_here"
LLM_MODEL = "qwen/qwen3.8-27b"
```

6. Deploy. The live URL will look like `https://<app-name>.streamlit.app`.

The processed dataset (`data/processed/restaurants.parquet`) is in git so Cloud does not download the Hugging Face dump at startup. Without `GROQ_API_KEY`, the UI still ranks restaurants using the rule-based fallback.

One-click deploy (GitHub must already be connected): [Deploy DineMind](https://share.streamlit.io/deploy?repository=buildwithniharika/DineMind-AI-Restaurant-Recommender&branch=main&mainModule=streamlit_app.py).

## Tests

```bash
pytest tests/ -v
```

- Phase 1: preprocessor + cache round-trip
- Phase 2: preference validation, filter rules, metadata helper
- Phase 3: prompt builder, response parser, fallback / retry
- Phase 4: FastAPI health / metadata / recommendations

---

## Project layout

```
Zomato_MS/
├── .streamlit/           # Community Cloud theme + secrets example
├── Docs/
│   ├── design/stitch/    # Stitch HTML + design tokens
│   └── …                 # Specs & plans
├── app/
│   ├── streamlit_app.py
│   ├── components/
│   └── styles/dinemind.css
├── data/processed/restaurants.parquet
├── scripts/
├── src/
├── tests/
├── streamlit_app.py      # Streamlit Cloud entrypoint
├── .env.example
├── requirements.txt
└── README.md
```

---

## Polish (Phase 6)

Follow [Docs/implementation-plan.md](Docs/implementation-plan.md) for E2E tests. Streamlit Community Cloud setup is in [Deploy on Streamlit Community Cloud](#deploy-on-streamlit-community-cloud).
