# DineMind — AI Restaurant Recommender

Personalized restaurant recommendations for Bangalore. You set location, budget, cuisine, and rating; DineMind filters a real Zomato listings dataset and an LLM ranks the matches with a short explanation for each pick.

**Live demo:** deploy from GitHub on [Streamlit Community Cloud](#deploy-on-streamlit-community-cloud) · **Repo:** [buildwithniharika/DineMind-AI-Restaurant-Recommender](https://github.com/buildwithniharika/DineMind-AI-Restaurant-Recommender)

**Docs:** [Problem statement](Docs/problem_Statement.md) · [Architecture](Docs/architecture.md) · [Implementation plan](Docs/implementation-plan.md) · [Edge cases](Docs/edge-case.md) · [Prompts](Docs/prompts.md)

---

## How it works

**Retrieve → Filter → Reason → Present**

1. Load a cleaned Zomato Bangalore cache (`data/processed/restaurants.parquet`).
2. Filter by location (city or locality), budget, cuisine, and minimum rating.
3. Rank remaining candidates with Groq (default). If the LLM is missing or fails, a rule-based fallback still returns results.
4. Show the top picks in the Streamlit UI (or via FastAPI).

| Preference | What it means |
|------------|----------------|
| Location | Bangalore or a locality such as Koramangala |
| Budget | Low ≤ ₹500 for two · medium ₹501–1,500 · high > ₹1,500 |
| Cuisine | Optional; `"Any"` skips cuisine filter |
| Minimum rating | 0.0–5.0 |
| Extra notes | Free text for the LLM (e.g. family-friendly) |

---

## Requirements

| Item | Details |
|------|---------|
| Python | **3.11+** (3.12 recommended; use 3.12 on Streamlit Cloud) |
| LLM key | **Groq** `GROQ_API_KEY` for AI explanations ([console.groq.com](https://console.groq.com/)). OpenAI / Ollama optional. |
| Dataset | Processed Parquet is in the repo. Rebuilding from Hugging Face needs network (~574 MB first download). |

Without an API key the app still runs; cards use fallback rationales instead of LLM text.

---

## Quick start (local)

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Set GROQ_API_KEY=gsk-... in .env

python scripts/check_prerequisites.py
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501). Equivalent entrypoint: `streamlit run app/streamlit_app.py`.

### Rebuild the dataset (optional)

The repo already includes `data/processed/restaurants.parquet` (~9k unique restaurants after cleaning). To rebuild from [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation):

```bash
python scripts/prepare_data.py
python scripts/prepare_data.py --force   # ignore existing cache
```

Raw listings repeat venues across types. After dropping incomplete rows and deduping on name + location, the unique count is lower than the raw ~52k. `location` is a Bangalore locality; `city` is Bangalore.

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

### Environment variables

See [`.env.example`](.env.example). Main keys:

| Variable | Default | Role |
|----------|---------|------|
| `LLM_PROVIDER` | `groq` | `groq` \| `openai` \| `ollama` |
| `GROQ_API_KEY` | empty | Required for Groq ranking |
| `OPENAI_API_KEY` | empty | Only if provider is `openai` |
| `LLM_MODEL` | `qwen/qwen3.8-27b` | Chat model id |
| `MAX_CANDIDATES` | `30` | Filter cap sent to the LLM |
| `TOP_N_DEFAULT` | `5` | Default number of cards |
| `BUDGET_LOW_MAX` / `BUDGET_MEDIUM_MAX` | `500` / `1500` | Cost-for-two (INR) |

---

## Deploy on Streamlit Community Cloud

Community Cloud builds from GitHub and does **not** read a local `.env`.

1. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2. **Create app** → this repository → branch `main`.
3. **Main file path:** `streamlit_app.py`.
4. **Advanced settings:** Python **3.12**.
5. Paste secrets (from [`.streamlit/secrets.toml.example`](.streamlit/secrets.toml.example)) and set a real Groq key:

```toml
LLM_PROVIDER = "groq"
GROQ_API_KEY = "gsk_your_key_here"
LLM_MODEL = "qwen/qwen3.8-27b"
```

6. Deploy. The URL looks like `https://<app-name>.streamlit.app`.

[One-click deploy](https://share.streamlit.io/deploy?repository=buildwithniharika/DineMind-AI-Restaurant-Recommender&branch=main&mainModule=streamlit_app.py) (GitHub must already be connected).

---

## API (optional)

The Streamlit app calls `RecommendationService` in-process. FastAPI exposes the same pipeline.

```bash
uvicorn src.main:app --reload --port 8000
# Swagger: http://127.0.0.1:8000/docs
python scripts/demo_api.py
```

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health + dataset loaded |
| `GET` | `/api/metadata` | Locations, cuisines, budgets |
| `POST` | `/api/recommendations` | Ranked recommendations |

Errors: `400` validation · `404` no matches · `502` engine failure · `503` dataset not loaded.

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "location": "Bangalore",
    "budget": "medium",
    "cuisine": "Italian",
    "min_rating": 4.0,
    "additional_preferences": "family-friendly",
    "top_n": 5
  }'
```

Example response shape:

```json
{
  "recommendations": [
    {
      "rank": 1,
      "restaurant_id": "...",
      "name": "Truffles",
      "cuisine": "Italian, Continental",
      "rating": 4.5,
      "estimated_cost": 1200,
      "explanation": "Matches Italian cuisine in your budget with a strong rating.",
      "location": "Koramangala"
    }
  ],
  "summary": "Top Italian picks in Bangalore for a medium budget.",
  "source": "llm"
}
```

`source` is `"llm"` or `"fallback"`.

### CLI demos

```bash
python scripts/demo_filter.py          # filter only
python scripts/demo_llm.py             # filter → LLM (or fallback)
python scripts/demo_llm.py --fallback-only
```

---

## Tests

```bash
pytest tests/ -v
```

Covers preprocessor/cache, filter rules, prompt + JSON parse, fallback/retry, FastAPI routes, and the shipped Parquet load.

```bash
ruff check src/ tests/
```

---

## Project layout

```
.
├── streamlit_app.py              # Streamlit Cloud entrypoint
├── app/                          # DineMind UI (Stitch white-light theme)
│   ├── streamlit_app.py
│   ├── components/
│   └── styles/dinemind.css
├── src/
│   ├── data/                     # load, preprocess, parquet cache
│   ├── filters/                  # preference matching
│   ├── llm/                      # prompts, Groq/OpenAI/Ollama, parser
│   ├── services/                 # orchestration + fallback
│   ├── api/                      # FastAPI routes
│   └── models/
├── data/processed/restaurants.parquet
├── scripts/                      # prepare_data, demos, prerequisites
├── tests/
├── Docs/                         # specs, architecture, Stitch design
├── .streamlit/                   # Cloud theme + secrets example
├── .env.example
└── requirements.txt
```

---

## License

Use this repository for the DineMind / Zomato recommendation case study. Dataset terms follow the Hugging Face source above.
