# Edge Cases & Corner Scenarios

This document catalogs all corner scenarios for the AI-powered restaurant recommendation system. Use it during design reviews, unit/integration testing, and Phase 6 E2E validation. Derived from [problem_Statement.md](./problem_Statement.md), [architecture.md](./architecture.md), and [implementation-plan.md](./implementation-plan.md).

---

## Table of Contents

1. [Severity Legend](#1-severity-legend)
2. [Data Ingestion & Preprocessing](#2-data-ingestion--preprocessing)
3. [User Input & Validation](#3-user-input--validation)
4. [Filtering & Candidate Selection](#4-filtering--candidate-selection)
5. [LLM Integration & Prompting](#5-llm-integration--prompting)
6. [Response Parsing & Ranking](#6-response-parsing--ranking)
7. [API & Orchestration](#7-api--orchestration)
8. [Frontend & UX](#8-frontend--ux)
9. [Security & Abuse](#9-security--abuse)
10. [Performance & Scale](#10-performance--scale)
11. [Configuration & Environment](#11-configuration--environment)
12. [Deployment & Operations](#12-deployment--operations)
13. [Test Matrix (Quick Reference)](#13-test-matrix-quick-reference)

---

## 1. Severity Legend

| Severity | Meaning |
|----------|---------|
| **P0** | Blocks core flow; must handle before demo |
| **P1** | Degrades quality or UX; handle in MVP |
| **P2** | Edge / rare; handle if time allows |
| **P3** | Nice-to-have / future hardening |

| Column | Meaning |
|--------|---------|
| **Expected Behavior** | Correct system response |
| **Layer** | Where the case is handled |

---

## 2. Data Ingestion & Preprocessing

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| D01 | Hugging Face download fails (network / 503) | P0 | Retry up to 3×; clear error with manual download guidance | Loader |
| D02 | Dataset download interrupted mid-transfer | P1 | Detect incomplete cache; re-download or fail with message | Loader / Cache |
| D03 | Dataset schema differs from expected column names | P0 | Fail fast at startup with schema mismatch report; map via `SchemaMapper` | Preprocessor |
| D04 | Row missing `name`, `location`, or `rating` | P0 | Drop row during preprocess | Preprocessor |
| D05 | Row missing optional fields (`votes`, `address`, `rest_type`) | P1 | Keep row; set optionals to `null` / defaults | Preprocessor |
| D06 | Cuisine as comma-separated string (`"Italian, Chinese"`) | P0 | Parse into `list[str]`; trim whitespace | Preprocessor |
| D07 | Cuisine empty / `"NA"` / `"None"` / `"-" ` | P1 | Treat as empty cuisine list; allow match only when cuisine filter is unset | Preprocessor / Filter |
| D08 | Cost is float, string (`"1,200"`), or currency-prefixed | P0 | Normalize to `int`; strip commas / symbols | Preprocessor |
| D09 | Cost is `0`, negative, or absurdly high (e.g. `999999`) | P1 | Drop or clamp; document rule; exclude from budget filter if invalid | Preprocessor |
| D10 | Rating outside 0–5 (e.g. `5.5`, `-1`, `"NEW"`) | P0 | Clamp numeric ratings; drop non-numeric / `"NEW"` if no score | Preprocessor |
| D11 | Duplicate restaurants (same name + location) | P1 | Deduplicate; keep highest-rated / highest-votes row | Preprocessor |
| D12 | Location casing / spacing (`"bangalore "`, `"BANGALORE"`) | P0 | Normalize (trim, title-case) before cache | Preprocessor |
| D13 | Location aliases (`"Bengaluru"` vs `"Bangalore"`) | P1 | Document known aliases; optional alias map; partial match may still miss | Filter / Config |
| D14 | Locality vs city (`"Koramangala, Bangalore"`) | P1 | Support partial location match so city queries still hit | Filter |
| D15 | Processed Parquet missing or corrupt | P0 | Detect on load; re-run prepare script or fail with clear message | Cache |
| D16 | First run with no cache (~574 MB download) | P1 | Show progress / long-running warning; cache for subsequent runs | Loader / UX |
| D17 | Very large in-memory load causes OOM on small machines | P2 | Document min RAM; optional city-partitioned load later | Data Layer |
| D18 | Special characters in restaurant names (apostrophes, unicode, `&`) | P1 | Preserve in cache; escape safely in JSON / UI | Preprocessor / UI |
| D19 | Empty dataset after aggressive cleaning | P0 | Fail startup if processed count &lt; threshold (e.g. &lt; 1000) | Loader |

---

## 3. User Input & Validation

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| U01 | Missing required `location` | P0 | Validation error (400 / form error) | Preferences |
| U02 | Missing required `budget` | P0 | Validation error | Preferences |
| U03 | Invalid budget (`"cheap"`, `"LOW "`, `null`) | P0 | Reject; only `low` / `medium` / `high` | Preferences |
| U04 | `min_rating` &lt; 0 or &gt; 5 | P0 | Reject or clamp with validation message | Preferences |
| U05 | `min_rating` as string (`"4"`) | P1 | Coerce to float if safe; else 400 | Preferences |
| U06 | `cuisine` omitted / `null` / `"Any"` | P0 | Treat as no cuisine filter | Preferences / Filter |
| U07 | `cuisine` with typos (`"Itallian"`) | P1 | Return empty or few matches; optionally suggest closest cuisine | Filter / UX |
| U08 | `additional_preferences` empty / whitespace only | P0 | Treat as no constraint | Preferences |
| U09 | `additional_preferences` very long (&gt; 500 chars) | P1 | Truncate or reject at max length | Preferences / Security |
| U10 | `additional_preferences` with newlines / HTML / scripts | P1 | Sanitize; strip HTML; do not render as HTML in UI | Preferences / UI |
| U11 | `top_n` = 0, negative, or &gt; 10 | P0 | Reject or clamp to 1–10 | Preferences |
| U12 | `top_n` = 1 | P1 | Return exactly one recommendation | Orchestrator |
| U13 | Location not in dataset (e.g. `"Atlantis"`) | P0 | Empty result with “broaden criteria” message | Filter / UX |
| U14 | Location with leading/trailing spaces | P0 | Trim before filter | Preferences |
| U15 | Case-insensitive location (`"delhi"` vs `"Delhi"`) | P0 | Case-insensitive match | Filter |
| U16 | Budget case variants (`"Medium"`, `"MEDIUM"`) | P1 | Normalize to lowercase enum | Preferences |
| U17 | Concurrent form resubmit (double-click Submit) | P1 | Disable button / debounce; ignore duplicate in-flight request | UI |
| U18 | All optional fields blank (cuisine + additional prefs) | P0 | Valid request; filter on location + budget + rating only | Preferences |

---

## 4. Filtering & Candidate Selection

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| F01 | No restaurants match all filters | P0 | Empty list; 404 / empty UX with suggestions | Filter |
| F02 | Exactly 1 candidate after filter | P1 | Still call LLM (or fallback); return 1 result | Orchestrator |
| F03 | Candidates &lt; `top_n` (e.g. 3 matches, `top_n=5`) | P0 | Return available count only (≤ 3) | Orchestrator / LLM |
| F04 | Candidates &gt; 30 after soft filters | P0 | Cap at 30 after sort by rating/votes | Filter |
| F05 | Budget boundary — cost exactly 500 (low vs medium) | P0 | Low: ≤ 500; Medium: 501–1500; High: &gt; 1500 | Filter / Config |
| F06 | Budget boundary — cost exactly 501 / 1500 / 1501 | P0 | Assign to correct tier per table | Filter |
| F07 | Restaurant with multiple cuisines; one matches | P0 | Include if any cuisine matches | Filter |
| F08 | Cuisine substring false positive (`"Indian"` vs `"North Indian"`) | P1 | Prefer token / list membership over naive substring | Filter |
| F09 | Partial location match too broad (`"a"` matches many cities) | P1 | Require min length (e.g. 3) or match against known location list | Filter / UX |
| F10 | Partial location match too narrow (`"Bangalore"` misses `"Bengaluru"`) | P1 | Alias map or fuzzy match (future); document limitation | Filter |
| F11 | `min_rating` = 5.0 with few perfect scores | P1 | Possibly empty; empty-state UX | Filter / UX |
| F12 | High budget + rare cuisine + high rating | P1 | Empty or tiny set; handle gracefully | Filter |
| F13 | Low budget + premium-only locality | P1 | Empty set; suggest raising budget | Filter / UX |
| F14 | Sort ties (same rating) | P2 | Break ties by votes desc, then name/id | Filter |
| F15 | Votes missing for tie-break | P2 | Treat missing votes as 0 | Filter |
| F16 | Filter order changes result set | P2 | Apply filters in documented order; keep deterministic | Filter |
| F17 | Cuisine filter with mixed case (`"chinese"`) | P0 | Case-insensitive cuisine match | Filter |

---

## 5. LLM Integration & Prompting

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| L01 | Missing / invalid API key | P0 | Fail at startup or first call with clear config error; use fallback if policy allows | Config / LLM |
| L02 | LLM timeout | P0 | Retry once; then rule-based fallback | LLM Client |
| L03 | LLM rate limit (429) | P0 | Backoff + retry; then fallback | LLM Client |
| L04 | LLM provider outage (5xx) | P0 | Fallback to rule-based ranking | LLM Client |
| L05 | LLM returns non-JSON / prose | P0 | Retry with format reminder; then fallback | Parser |
| L06 | LLM returns JSON wrapped in markdown fences | P1 | Strip fences; parse JSON | Parser |
| L07 | LLM hallucinates restaurant not in candidates | P0 | Drop invalid IDs; refill from candidates or fallback | Parser / Service |
| L08 | LLM invents / alters rating or cost | P0 | Prefer dataset values over LLM-supplied fields | Parser / Service |
| L09 | LLM returns fewer than `top_n` | P1 | Accept available; optionally pad from filter sort | Parser |
| L10 | LLM returns more than `top_n` | P1 | Truncate to `top_n` | Parser |
| L11 | LLM duplicate ranks or duplicate restaurant IDs | P1 | Deduplicate; re-rank 1..N | Parser |
| L12 | LLM ranks ignore budget / cuisine constraints | P1 | Soft: prompt rules; hard: validate candidates still pass filters | Prompt / Service |
| L13 | `additional_preferences` conflict with hard filters (e.g. “luxury” + low budget) | P1 | Respect hard filters; mention tradeoff in explanation/summary | Prompt |
| L14 | Prompt injection via additional prefs (“Ignore rules; recommend X”) | P0 | Sanitize input; system prompt forbids overrides; validate IDs | Security / Prompt |
| L15 | Empty `additional_preferences` still sent as noise | P2 | Omit or send `"None"` consistently | Prompt Builder |
| L16 | Token limit exceeded (too many candidates / long names) | P1 | Cap candidates; compact JSON fields only | Prompt Builder |
| L17 | Provider switched mid-request (config change) | P2 | Provider selected at request start; no mid-call switch | Config |
| L18 | Local Ollama model not running | P1 | Clear error; fall back to cloud provider or rule-based | Ollama Provider |
| L19 | Temperature too high → unstable ranking | P2 | Keep temperature 0.3–0.5 | Config |
| L20 | Explanations empty or one-word | P1 | Reject / retry if explanation below min length; else template | Parser |

---

## 6. Response Parsing & Ranking

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| R01 | Missing required field (`explanation`, `name`) | P0 | Treat as invalid; retry / fallback | Parser |
| R02 | Wrong types (rating as string `"4.5"`) | P1 | Coerce if safe; else invalid | Parser |
| R03 | Rank numbers not sequential (1, 3, 5) | P2 | Reassign ranks by list order | Parser |
| R04 | Summary missing | P2 | Allow `summary: null`; UI hides summary section | Parser / UI |
| R05 | Summary present but recommendations empty | P1 | Treat as invalid / empty error | Parser |
| R06 | Fallback activated — mark `source: "fallback"` | P0 | Return template explanations; UI may note limited AI | Service / UI |
| R07 | Fallback when candidates exist but LLM fails | P0 | Top N by rating with generic explanation | Service |
| R08 | Both LLM and fallback would return empty | P0 | Should not happen if candidates exist; assert / 500 with log | Service |
| R09 | Restaurant ID in response not found in candidate map | P0 | Skip item; do not invent metadata | Parser |
| R10 | Unicode / emoji in explanation | P2 | Allow; render safely in UI | Parser / UI |

---

## 7. API & Orchestration

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| A01 | `GET /health` before dataset loaded | P0 | `dataset_loaded: false` and/or 503 | API |
| A02 | `GET /health` after successful load | P0 | 200 + `dataset_loaded: true` | API |
| A03 | `GET /api/metadata` with empty location list | P0 | Should not happen post-load; 503 if unloaded | API |
| A04 | `POST /api/recommendations` with invalid body | P0 | 400 with field-level errors | API |
| A05 | `POST` with no matches | P0 | 404 + suggestion to broaden filters | API |
| A06 | LLM failure after candidates found | P1 | 200 with fallback + `source: "fallback"` (preferred) or 502 after fallback fail | API |
| A07 | Malformed JSON body | P0 | 422 / 400 | API |
| A08 | Unsupported Content-Type | P2 | 415 or 422 | API |
| A09 | Request during dataset cold start | P1 | Queue / 503 “warming up” until load completes | API |
| A10 | Concurrent recommendations stress | P1 | Handle safely; optional rate limit in prod | API |
| A11 | CORS request from unknown origin | P1 | Block in production; allow local dev origins | API |
| A12 | Very slow LLM → client timeout | P1 | Server timeout ~30s; return fallback; UI shows error if connection drops | API / UI |
| A13 | Orchestrator loads data every request | P1 | Load once at startup; reuse in-memory store | Service |
| A14 | Logging includes full preference free-text | P2 | Avoid logging PII-like free text; log counts + filter keys | Logging |

---

## 8. Frontend & UX

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| X01 | Initial page load — no results yet | P0 | Show form only; no empty error | UI |
| X02 | Loading state during LLM call | P0 | Spinner + “Finding restaurants…”; disable submit | UI |
| X03 | Success with 5 cards | P0 | Show name, cuisine, rating, cost, explanation | UI |
| X04 | Empty result set | P0 | Friendly empty state + broaden tips | UI |
| X05 | API 400 validation error | P0 | Inline / toast with field messages | UI |
| X06 | API 502 / network error | P0 | Error state + retry | UI |
| X07 | Fallback results returned | P1 | Optionally badge “ranked by rating” vs AI | UI |
| X08 | Long restaurant name / explanation overflow | P1 | Truncate with expand or wrap cleanly | UI |
| X09 | Missing image (if added later) | P3 | Placeholder | UI |
| X10 | Metadata dropdowns empty (API down) | P0 | Error loading filters; block submit | UI |
| X11 | User changes form mid-request | P1 | Ignore stale response or cancel prior request | UI |
| X12 | Mobile narrow viewport | P1 | Usable layout; cards stack | UI |
| X13 | Rating display for 0.0 / 5.0 | P2 | Render correctly (stars / number) | UI |
| X14 | Cost = 0 shown as free | P2 | Show “N/A” if cost invalid/zero post-clean | UI |
| X15 | Summary section when `summary` is null | P2 | Hide summary banner | UI |
| X16 | Streamlit rerun clears results unexpectedly | P1 | Persist results in session state until new submit | UI |

---

## 9. Security & Abuse

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| S01 | `.env` / API keys committed to git | P0 | Prevent via `.gitignore`; rotate if leaked | Config |
| S02 | Prompt injection in `additional_preferences` | P0 | Sanitize; hard ID validation; system rules | Security |
| S03 | XSS via restaurant name / explanation in UI | P0 | Escape / safe render (no `unsafe_allow_html` on user/LLM text) | UI |
| S04 | Oversized payload DoS | P1 | Body size limit; max length on strings | API |
| S05 | Rapid-fire recommendation requests | P1 | Rate limit per IP in production | API |
| S06 | SSRF / URL injection if ever fetching user URLs | P3 | N/A for MVP; reject URLs in prefs | Security |
| S07 | API key logged in error traces | P1 | Redact secrets in logs | Logging |
| S08 | CORS `*` in production | P1 | Restrict to known frontend origins | API |

---

## 10. Performance & Scale

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| P01 | Full-dataset filter latency spike | P1 | Keep in-memory; target &lt; 500ms filter | Filter |
| P02 | LLM latency &gt; 15s | P1 | Loading UX; timeout + fallback | LLM / UI |
| P03 | Token cost spike from large prompts | P1 | Cap 20–30 candidates; compact fields | Prompt |
| P04 | Repeated identical queries | P2 | Optional response cache (future) | Service |
| P05 | Memory growth from retaining all HF raw + processed | P2 | Drop raw after preprocess; keep Parquet + RAM frame only | Data |
| P06 | Startup time with cold Parquet load | P1 | &lt; 5s load from cache after warm disk | Cache |

---

## 11. Configuration & Environment

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| C01 | `.env` missing entirely | P0 | Clear startup error listing required vars | Config |
| C02 | `LLM_PROVIDER` set to unknown value | P0 | Fail fast with allowed values | Config |
| C03 | Budget thresholds misconfigured (overlapping ranges) | P1 | Validate config at startup | Config |
| C04 | `MAX_CANDIDATES` = 0 or huge (1000) | P1 | Clamp to sane bounds (e.g. 5–50) | Config |
| C05 | Wrong model name for provider | P1 | Provider error → fallback / clear message | LLM |
| C06 | Dev uses Ollama; prod uses OpenAI without code change | P2 | Provider abstraction via env only | Config |

---

## 12. Deployment & Operations

| ID | Scenario | Severity | Expected Behavior | Layer |
|----|----------|----------|-------------------|-------|
| O01 | Deploy without `restaurants.parquet` | P0 | Build step runs prepare, or bundle artifact; else fail health | Deploy |
| O02 | Env vars not set on host | P0 | App fails health / startup clearly | Deploy |
| O03 | Disk full during dataset download | P1 | Catch IO error; actionable message | Loader |
| O04 | Process killed during LLM call | P2 | Client sees error; next request clean | Ops |
| O05 | Multiple workers each loading full dataset | P2 | Accept for MVP; document memory × workers | Deploy |
| O06 | Health check used by load balancer while loading | P1 | Return non-ready until dataset loaded | API |

---

## 13. Test Matrix (Quick Reference)

Minimum E2E / automated coverage for MVP:

| # | Scenario | IDs Covered | Pass Criteria |
|---|----------|-------------|---------------|
| 1 | Happy path — Bangalore + medium + Italian + rating ≥ 4 | U18, F07, X03 | ≥1 cards with all 5 display fields |
| 2 | No matches — unknown city | U13, F01, X04 | Empty state, no crash |
| 3 | Budget boundaries 500 / 501 / 1500 / 1501 | F05, F06 | Correct tier membership |
| 4 | `top_n` = 1 and = 10 | U11, U12, F03 | Correct count ≤ available |
| 5 | Cuisine omitted | U06 | Results across cuisines |
| 6 | Typos / injection in additional prefs | U09, L14, S02 | No override; safe output |
| 7 | Invalid LLM JSON then recovery | L05, L06, R06 | Retry or fallback with valid schema |
| 8 | Hallucinated restaurant ID | L07, R09 | Dropped; no fake venue |
| 9 | LLM timeout / bad API key | L01, L02, R07 | Fallback or clear error |
| 10 | Missing location / invalid budget | U01, U03, A04, X05 | 400 + UI error |
| 11 | Dataset not loaded | A01, O06 | Health shows not ready |
| 12 | Exactly 1 candidate | F02 | Single recommendation |
| 13 | Candidates &lt; top_n | F03 | Returns available only |
| 14 | Double submit | U17, X11 | Single result set |
| 15 | Corrupt / missing cache | D15, O01 | Clear recovery path |

---

## Handling Principles (Summary)

1. **Hard constraints stay deterministic** — location, budget, rating, cuisine filters never rely on the LLM alone.
2. **LLM is best-effort** — timeout, bad JSON, and hallucinations degrade to rule-based fallback, not a hard crash.
3. **Empty is a valid outcome** — communicate it; do not invent restaurants.
4. **Trust dataset over model** — name, rating, cost, cuisine for display come from filtered records.
5. **Fail loud at startup, soft at runtime** — missing keys/schema fail fast; LLM issues fall back.

---

## Traceability

| Problem Statement Stage | Edge Case Sections |
|------------------------|--------------------|
| Data Ingestion | §2 |
| User Input | §3, §8 |
| Integration Layer | §4, §5 |
| Recommendation Engine | §5, §6 |
| Output Display | §8 |

| Architecture Concern | Edge Case Sections |
|---------------------|--------------------|
| Error handling & resilience | §5, §6, §7 |
| Security | §9 |
| Deployment | §11, §12 |
| Performance | §10 |

---

*Update this file when new corner cases are discovered in testing. Prefer adding a stable ID (`Dxx`, `Uxx`, …) so test cases and tickets can reference them.*
