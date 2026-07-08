# Architecture Log

Running log of every agent, service, and table introduced, in build order.
Keep this current - add an entry whenever a module introduces something new.

## Module 1 - Project Foundation

**Goal:** stable schema, config, logging, auth, and the Agent + Orchestrator
skeleton, with no agent business logic yet.

### Config
- `app/config/settings.py` - single `Settings` (Pydantic v2 `BaseSettings`)
  object, loaded from `.env`. Nothing else in the codebase should read
  `os.environ` directly. Includes DeepSeek, database, ChromaDB/embedding,
  JWT, and CORS config.

### Logging
- `app/utils/logging_config.py` - loguru configured with a console sink and
  a rotating file sink (`logs/app.log`, 10MB rotation, 7-day retention),
  level driven by `Settings.LOG_LEVEL`. Called once from `main.py`'s
  lifespan startup.

### Database (tables)
All tables created via SQLAlchemy `Base.metadata.create_all()` on startup
(`app/database/session.py: init_db()`). No migration tool yet (MVP) - see
`MIGRATIONS.md` for the change log that will feed a future migration tool.

- **products** (`app/models/product.py`) - root entity: the company/product
  being audited. Every other table FKs to this.
- **website_data** (`app/models/website_data.py`) - one row per crawl
  snapshot of a product's website (title, meta description, headings
  summary, FAQ/schema-markup flags, word count). Will be populated by the
  future Website Crawler agent (Module 2).
- **reviews** (`app/models/review.py`) - individual reviews fetched from
  Play Store or other sources. `sentiment_label` is nullable until the
  Module 3 sentiment analysis agent runs.
- **competitors** (`app/models/competitor.py`) - competitor products
  tracked for comparison. Populated by the future Competitor Analysis agent
  (Module 4).
- **audit_reports** (`app/models/audit_report.py`) - the scored output of a
  full pipeline run: `geo_score`, `score_breakdown` (JSON), `recommendations`
  (JSON). Populated by the future Scoring agent (Module 5).
- **generated_content** (`app/models/generated_content.py`) - AI-generated
  artifacts (faq/blog/meta/release_notes/campaign), with the prompt used
  recorded for traceability. Populated by future content-generation agents
  (Module 6).
- **users** (`app/models/user.py`) - minimal auth table (email + bcrypt
  hash) for the MVP JWT scaffold. Structured to allow adding OAuth columns
  later without breaking the table.

### Schemas
- `app/schemas/common.py` - `AgentResult` (the standard envelope every
  agent's `execute()` returns), `HealthResponse`, `ErrorResponse`, and
  `ORMBase` (shared `from_attributes=True` base for "Read" schemas).
- One schema file per table under `app/schemas/`, each split into a
  `*Create` (input) and `*Read` (output, includes id/timestamps) schema.
- `app/schemas/auth.py` - `UserCreate`, `UserLogin`, `UserRead`, `Token`.

### Agent + Orchestrator skeleton
- `app/agents/base.py` - `BaseAgent` abstract class. Every agent implements
  `name` and `run(input) -> output`; `execute()` (not abstract) wraps `run`
  with start/end/duration logging and converts any exception into a
  non-throwing `AgentResult(success=False, ...)`, so one agent's failure
  never crashes the pipeline.
- `app/orchestrator/orchestrator.py` - `Orchestrator` class with an internal
  pipeline list, `register_agent()`, and `run_pipeline(product_id)`. No real
  agents are registered yet; TODO comments mark exactly where Modules 2-6
  agents will be plugged in and in what order.

### Services / Vector DB (scaffolded, unused so far)
- `app/vector_db/client.py` - persistent local ChromaDB client wrapper
  (`get_chroma_client()`, `get_or_create_collection()`). No collections
  created yet - reserved for future RAG-based agents.
- `app/services/` - empty package, reserved for shared cross-agent services
  (LLM client wrapper, embedding service, crawler service) starting Module 2.
- `app/prompts/` - empty package, reserved for standalone prompt template
  files (in addition to each agent's own `prompts.py`).

### Auth scaffold
- `app/utils/security.py` - bcrypt password hashing (`passlib`) and JWT
  encode/decode (`python-jose`), reading secret/expiry from `Settings`.
- `app/api/deps.py` - `get_current_user` FastAPI dependency, resolves the
  `User` from a Bearer JWT. Usable on any future protected route.
- `app/api/auth.py` - `POST /auth/register`, `POST /auth/login`,
  `GET /auth/me` (demonstrates `get_current_user`).

### Cross-cutting utilities
- `app/utils/exceptions.py` - typed exception hierarchy (`AppError`,
  `ExternalServiceError`, `AgentExecutionError`, `NotFoundError`,
  `AuthError`) so `except` blocks never swallow errors silently.
- `app/utils/retry.py` - `with_retry_and_timeout()` decorator for wrapping
  every future external call (LLM, website fetch, Play Store fetch) with a
  per-attempt timeout and exponential backoff (default max 3 attempts),
  raising `ExternalServiceError` on final failure.

### API
- `app/api/health.py` - `GET /health`.
- `app/main.py` - FastAPI app factory, CORS for `localhost:5173` /
  `localhost:3000`, lifespan startup (logging config + `init_db()`), mounts
  the health and auth routers. Swagger UI at `/docs`.

## Module 2 - Data-Ingestion Agents (Website Crawler + Play Store Analyzer)

**Goal:** two independent, orchestrator-pluggable ingestion agents that
populate `website_data`, `play_store_data`, and `reviews` with raw/derived
signals. No scoring, sentiment, or content generation yet.

### Design decision: `play_store_data` is its own table, not columns on `website_data`
Considered bolting Play Store fields onto `website_data` (one row per
product either way) but rejected it: a website crawl and a Play Store audit
are fetched by two independent agents on independent schedules, have almost
no overlapping columns, and can each fail/succeed independently. Cramming
both into one table would mean every website-only product carries a wall of
always-null Play Store columns (and vice versa), and a partial failure in
one agent would be harder to reason about against a single shared row.
Keeping them as sibling 1:1-with-`Product` tables (`website_data`,
`play_store_data`) mirrors how the two source agents are structured and
keeps each row's `status`/`error_message` meaningful on its own.

### `website_data` additions (Module 2)
Extended `app/models/website_data.py` with the signals the Website Crawler
agent produces: `faq_count`, `schema_types` (JSON list), `internal_links_count`,
`images_missing_alt_count`, `last_updated_signal`, `crawled_pages`/`failed_pages`
(JSON), and `status`/`error_message` (see `IngestionStatus` below). Each
crawl UPSERTs the single row for a product rather than keeping history, to
keep the MVP simple.

### New table: `play_store_data` (`app/models/play_store_data.py`)
One row per product, populated by the Play Store Analyzer agent: listing
metadata (title, descriptions, rating, rating distribution, category,
version, installs, permissions) plus heuristic derived signals
(`description_word_count`, `has_faq_content`, `keyword_density`,
`days_since_update`, `reviews_fetched_count`) and the same `status`/
`error_message` pattern as `website_data`. Raw reviews are **not** stored
here - they go into the existing `reviews` table (`source="play_store"`),
left for the Module 3 sentiment agent to enrich (`sentiment_label` stays
`null` until then).

### New shared enum: `IngestionStatus` (`app/models/common_enums.py`)
`pending | running | success | partial | failed`. Persisted directly on the
`website_data`/`play_store_data` row it describes, so `GET .../status/{id}`
endpoints can report progress/outcome without a separate jobs table -
appropriate for the MVP's BackgroundTasks-based job model (see below).

### Agent 1: Website Crawler (`app/agents/crawler/`)
- `constants.py` - user agent string, timeouts, retry/backoff config,
  politeness delay, FAQ/Blog link-discovery hints, FAQ element class hints.
- `service.py` - all the actual work: robots.txt fetch+parse (best-effort,
  defaults to allow-all), Playwright page load wrapped in
  `app.utils.retry.with_retry_and_timeout` (20s timeout, 3 attempts,
  exponential backoff), BeautifulSoup extraction (title, meta description,
  H1-H3 headings summarized to a capped list, FAQ heuristic detection via
  "?"-ending headings + FAQ/accordion class/id hints, schema.org JSON-LD
  `@type` extraction including `@graph` unwrapping, main-content word count,
  internal link count, images-missing-alt count, best-effort "last updated"
  signal from `<time>`/footer copyright/`sitemap.xml <lastmod>`), homepage
  nav-link discovery of an FAQ/Help page and a Blog page, HTML snapshot
  persistence to `uploads/website_snapshots/{product_id}/{role}.html`, and
  `persist_website_data()` (the UPSERT into `website_data`).
- `agent.py` - `WebsiteCrawlerAgent(BaseAgent)`. Always persists whatever it
  found (even on total failure, so `status=FAILED` + `error_message` are on
  the row); only raises `AgentExecutionError` when *no* page could be loaded
  at all, converting to `AgentResult(success=False, ...)` at the `execute()`
  boundary. A partial crawl (homepage OK, FAQ/Blog blocked) returns normally
  with `status=PARTIAL`.
- `prompts.py` - empty placeholder (no LLM calls in this agent yet), kept for
  structural consistency with every other agent.

### Agent 2: Play Store Analyzer (`app/agents/playstore/`)
- `constants.py` - retry/timeout config, review fetch count (100), and the
  hand-written `CATEGORY_KEYWORDS`/`GENERIC_KEYWORDS` heuristic lists used
  for keyword-density (no AI/embeddings involved - purely a word-count ratio).
- `service.py` - package-id resolution from a Play Store URL or bare
  package name, `google-play-scraper` calls (`app`, `reviews`,
  `permissions`) each wrapped in `asyncio.to_thread` + `with_retry_and_timeout`
  (they're synchronous/blocking under the hood), rating-histogram ->
  `rating_distribution` mapping, derived signals (`description_word_count`,
  `has_faq_content`, `keyword_density`, `days_since_update` from the
  listing's `updated` unix timestamp), and `persist_play_store_data()`
  (UPSERTs `play_store_data`, inserts any new `Review` rows deduped by
  review text, source="play_store").
- `agent.py` - `PlayStoreAnalyzerAgent(BaseAgent)`. Same failure-isolation
  pattern as the crawler: a failed *reviews* fetch still returns
  `status=PARTIAL` (listing data is still useful); only a failed *listing*
  fetch (bad package id, app not found, network failure after retries)
  raises `AgentExecutionError` -> `AgentResult(success=False, ...)`.
- `prompts.py` - empty placeholder, same rationale as the crawler's.

### API additions
- `app/api/crawler.py` - `POST /crawl` (looks up the product, marks its
  `website_data` row `RUNNING`, schedules `WebsiteCrawlerAgent.execute()` via
  FastAPI `BackgroundTasks`, returns an immediate `CrawlJobAck`) and
  `GET /crawl/status/{product_id}` (reads back the `website_data` row).
- `app/api/playstore.py` - same background-task pattern:
  `POST /playstore-audit` + `GET /playstore-audit/status/{product_id}`.
- `app/api/products.py` - **new, not explicitly requested by Module 1/2 but
  required plumbing**: minimal `POST /products`, `GET /products/{id}`,
  `GET /products` so a `product_id` exists to crawl/audit against. Thin
  CRUD only, reuses Module 1's `ProductCreate`/`ProductRead` schemas.
- Both ingestion endpoints validate the product exists and has the relevant
  URL configured *synchronously* (404/400, no crash) before scheduling the
  background job, so invalid input never reaches a 500.
- Background jobs are plain async functions passed to `BackgroundTasks` -
  structured so swapping to Celery + Redis later only means replacing
  `background_tasks.add_task(...)` with `celery_task.delay(...)`; the agent
  and its `execute()` contract don't change.

## Module 3 - Review Intelligence Agent

**Goal:** analyze stored Play Store reviews via batched map/reduce LLM calls,
producing a merged intelligence summary for downstream audit (Module 4).

### Design decision: `review_summaries` is its own table
Considered storing the merged summary on `audit_reports`, but rejected it:
review intelligence is produced independently of a GEO audit, can be re-run
when new reviews arrive (`is_analyzed` flags track per-review progress),
and Module 4's Audit Agent reads this table as input without owning it.

### Shared LLM client (`app/services/llm_client.py`)
Single wrapper for all DeepSeek (OpenAI-compatible) chat completion calls.
Every agent that needs an LLM must import `llm_client` from here — never
duplicate raw HTTP. Handles: timeout, exponential backoff retry (max 3),
HTTP 429 rate-limit backoff, JSON extraction from fenced/markdown responses,
Pydantic schema validation, and a one-shot strict JSON retry on parse failure.

### `reviews` table addition
- `is_analyzed` (Boolean, default `false`, indexed) — set `true` after a
  review is included in a completed map/reduce run.

### New table: `review_summaries` (`app/models/review_summary.py`)
One row per product (UPSERTed on each run): `top_complaints`,
`top_feature_requests`, `positive_themes`, `negative_themes` (JSON lists),
`overall_sentiment_score` (-1 to 1), `reviews_analyzed_count`,
`batches_processed`/`batches_failed`, raw `batch_outputs` (JSON, for
debugging), `status`/`error_message` (`IngestionStatus`).

### Agent: Review Intelligence (`app/agents/reviews/`)
- `constants.py` — batch size (target 45, max 50), conservative token budget
  (~6000 tokens/batch, ~4 chars/token estimate).
- `prompts.py` — `BATCH_ANALYSIS_SYSTEM_PROMPT` (map step) and
  `REDUCE_SUMMARY_SYSTEM_PROMPT` (reduce step), plus builder functions.
- `service.py` — pulls unanalyzed reviews, chunks into token-aware batches,
  runs per-batch LLM map calls via `llm_client.chat_completion_json()` ->
  `BatchReviewAnalysis`, then one reduce call -> `MergedReviewSummary`,
  marks reviews `is_analyzed=true`, persists to `review_summaries`.
  Zero reviews returns informative "not enough data" without raising.
  Failed batches are recorded as partial failures; reduce still runs on
  successful batches.
- `agent.py` - `ReviewIntelligenceAgent(BaseAgent)`.

### API additions
- `app/api/reviews.py` - `POST /reviews/analyze` (BackgroundTasks, same
  pattern as Module 2) and `GET /reviews/summary/{product_id}`.
- Zero reviews: `POST /reviews/analyze` returns HTTP 202 with
  `status=not_enough_data` and an informative message (no 500).

## Module 4 - Audit Agent + Competitor Agent

**Goal:** rule-based GEO scoring (no LLM in the score itself) plus LLM-powered
action plans and competitor comparisons.

### Shared GEO Scoring Service (`app/services/geo_scoring_service.py`)
Pure function `compute_geo_score(signals) -> GeoScoreBreakdown` used by both
Audit and Competitor agents. Components sum to max 100:
- documentation_depth (20) — help/docs/blog pages + word count
- faq_presence (15) — has_faq + faq_count
- metadata_quality (10) — meta description presence + length 50-160 chars
- structured_data (20) — Organization/Product/FAQPage schema types
- authority_signals (10) — **proxy:** `internal_links_count` (no backlink API in MVP)
- review_quality (15) — avg rating + review volume
- freshness (10) — days_since_update / last_updated_signal

### Agent: Audit (`app/agents/audit/`)
Requires successful `website_data` + `play_store_data`. Computes score via
shared service, loads `review_summaries` from Module 3, one LLM call for
action plan via `llm_client`, persists to `audit_reports`.

### Agent: Competitor (`app/agents/competitor/`)
Reuses `crawl_external_url()` from Module 2 crawler service (no duplicated
crawl logic). Scores each competitor with the same `compute_geo_score()`.
Per-competitor scores stored on `competitors` rows (`geo_score`,
`score_breakdown`, `crawl_signals`). Merged LLM comparison stored in new
`comparison_summaries` table (product-level polling for GET /compare/status).

### API additions
- `POST /audit` — synchronous, returns score + action plan
- `POST /compare` + `GET /compare/status/{product_id}` — BackgroundTasks

## Module 5 - Content Generation + RAG Pipeline

**Goal:** RAG-grounded content generation using local embeddings + ChromaDB.

### RAG Pipeline
- `app/services/embedding_service.py` — local sentence-transformers (Settings.EMBEDDING_MODEL_NAME), never paid API
- `app/vector_db/collection_service.py` — one collection per product: `product_{id}`
- `app/services/rag_ingestion.py` — chunks website + Play Store text (~300 words, 50 overlap), embeds, upserts to ChromaDB
- `app/services/rag_retrieval.py` — LlamaIndex retriever over ChromaDB (top-k=5)
- **Hooks:** `ingest_product_content()` called automatically after crawler and playstore agent persist (small callback, no duplicated Module 2 logic)

### Agent: Content Generation (`app/agents/content/`)
Distinct prompt per content_type in `prompts.py`. Retrieves RAG chunks, generates
via `llm_client`, stores in `generated_content` with `prompt_used`.
Returns clear error if ChromaDB has no ingested content (no ungrounded generation).

### ContentType enum extended
Added: `meta_description`, `product_description`, `campaign_bundle` (kept legacy `meta`, `campaign`).

### API additions
- `POST /generate-faq`, `/generate-blog`, `/generate-meta`, `/generate-campaign`
- `GET /content/{product_id}` — list generated content, newest first

## Module 6 - Orchestrator, Reporting Agent, Scheduling

**Goal:** wire every agent into a single end-to-end pipeline, produce HTML
reports, expose dashboard/pipeline APIs, and schedule weekly re-audits.

### New tables
- **`pipeline_runs`** (`app/models/pipeline_run.py`) — one row per full
  orchestrated run: `product_id`, `started_at`, `completed_at`, overall
  `status` (`pending|running|success|partial|failed`), `stage_statuses`
  (JSON per-stage map), `competitor_urls`, `error_message`.
- **`reports`** (`app/models/report.py`) — persisted HTML report metadata:
  `product_id`, `file_path`, optional `pipeline_run_id`, `created_at`.

### Orchestrator (`app/orchestrator/orchestrator.py`)
`Orchestrator.run_full_pipeline(pipeline_run_id, product_id, competitor_urls)`
sequences all agents in order:

1. **Concurrent ingestion** — `WebsiteCrawlerAgent` + `PlayStoreAnalyzerAgent`
   run in parallel via `asyncio.gather` (skipped individually if URL missing).
2. **Review Intelligence** — `ReviewIntelligenceAgent`.
3. **Audit** — `AuditAgent` (rule-based GEO score + LLM action plan).
4. **Competitor** — `CompetitorAgent` (skipped if no `competitor_urls`).
5. **Content Generation** — `ContentGenerationAgent` for `faq` and
   `meta_description` (minimum default set).
6. **Reporting** — `ReportingAgent` (always runs, even after partial failures).

**Partial-failure policy:** each stage is wrapped in `BaseAgent.execute()`,
which never raises. Failed stages are logged and recorded in
`stage_statuses` with `status=failed`; the pipeline continues to later
stages where sensible (reporting always runs). Overall run status is
`success` if all stages succeeded/skipped, `partial` if mixed, `failed` if
everything failed.

`create_pipeline_run()` creates a `PENDING` row before background execution.
`Orchestrator._log_email_stub()` logs where SMTP would send a report summary
(real email is a future seam).

### Agent: Reporting (`app/agents/reporting/`)
- `service.py` — gathers latest audit, review summary, comparison summary,
  and generated content; renders Jinja2 template
  `templates/audit_report.html.j2`; writes HTML to `reports/` folder
  (`report_{product_id}_{timestamp}.html`); persists `reports` row.
- `export_pdf_stub()` — clearly marked ReportLab seam (not implemented).
- `agent.py` — `ReportingAgent(BaseAgent)`.

### Dashboard service (`app/services/dashboard_service.py`)
`get_dashboard()` returns all products with latest GEO score, last audit
date, and last pipeline status. Uses **3 batch queries** (products, audits,
pipeline runs) with Python dedupe — no N+1.

### Scheduler (`app/services/scheduler_service.py`)
APScheduler (`AsyncIOScheduler`) runs `run_scheduled_audits()` on an
interval driven by `Settings.SCHEDULER_INTERVAL_DAYS` (default 7).
Iterates all products, creates a `PipelineRun`, and calls the full
orchestrator. Started/stopped in `main.py` lifespan when
`SCHEDULER_ENABLED=true`.

### API additions (`app/api/pipeline.py`)
- `POST /run-full-audit` — `{product_id, competitor_urls}` → BackgroundTasks,
  returns `pipeline_run_id` immediately (HTTP 202).
- `GET /run-full-audit/status/{pipeline_run_id}` — per-stage status for polling.
- `GET /report/{product_id}` — latest HTML report (path + inline content).
- `GET /dashboard` — aggregated product grid data.
- `POST /dev/trigger-scheduled-audit` — dev-only manual scheduler trigger.

### Settings additions
- `SCHEDULER_ENABLED` (default `true`)
- `SCHEDULER_INTERVAL_DAYS` (default `7`)

---

## End-to-end pipeline (full system)

A product enters the system via `POST /products` (name, website URL, Play
Store URL, category). From there, either an operator triggers a one-off full
audit (`POST /run-full-audit`) or the weekly scheduler runs it automatically.

**Data flows left-to-right through agents; only the Orchestrator sequences them:**

```
Product (products table)
    │
    ├─[concurrent]─► Website Crawler ──► website_data + RAG ingest (ChromaDB)
    │              Play Store Analyzer ─► play_store_data + reviews + RAG ingest
    │
    ├─► Review Intelligence ──► review_summaries (LLM map/reduce on reviews)
    │
    ├─► Audit Agent ──► audit_reports (rule-based GEO score + LLM action plan)
    │
    ├─► Competitor Agent (optional) ──► competitors + comparison_summaries
    │
    ├─► Content Generation (faq, meta_description) ──► generated_content (RAG + LLM)
    │
    └─► Reporting Agent ──► reports/ HTML file + reports table row
```

**Shared infrastructure used throughout:**
- `llm_client` — all LLM calls (reviews, audit action plan, competitor
  comparison, content generation).
- `geo_scoring_service` — shared 100-point scoring for audit + competitor.
- `embedding_service` + `rag_ingestion` + `rag_retrieval` + ChromaDB
  `product_{id}` collections — grounding for content generation; auto-fed
  by crawler/playstore after persist.
- `pipeline_runs` — tracks per-stage progress for frontend polling.
- `GET /dashboard` — reads products + latest audit + latest pipeline run
  in batch queries for a grid view.

**Failure handling:** any agent failure is non-fatal to the pipeline. The
Orchestrator records the stage as failed/partial, continues, and the Reporting
Agent still produces an HTML report with unavailable sections clearly marked.
After completion, an email stub is logged (SMTP integration is a future seam);
PDF export via ReportLab is likewise stubbed in the reporting service.

**Auth:** JWT scaffold from Module 1 protects routes in production; MVP
endpoints are open for local dev/testing.
