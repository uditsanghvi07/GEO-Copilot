# Migrations Log

We are not using Alembic yet in the MVP - tables are created via
SQLAlchemy's `Base.metadata.create_all()` on startup
(`app/database/session.py: init_db()`). This file is the Alembic-style
change log we'll replay as real migrations once we introduce Alembic.

## Module 1 - Initial schema

**Date:** 2026-07-07

Created all tables fresh (no prior schema existed):

| Table | Notes |
|---|---|
| `products` | Root entity. Indexed on `name`, `created_at`. |
| `website_data` | FK `product_id` -> `products.id` (indexed, `ON DELETE CASCADE`). Indexed on `last_crawled_at`. |
| `reviews` | FK `product_id` -> `products.id` (indexed, `ON DELETE CASCADE`). Indexed on `review_date`, `fetched_at`. `sentiment_label` nullable (populated later by Module 3). |
| `competitors` | FK `product_id` -> `products.id` (indexed, `ON DELETE CASCADE`). |
| `audit_reports` | FK `product_id` -> `products.id` (indexed, `ON DELETE CASCADE`). `score_breakdown`/`recommendations` are JSON columns. Indexed on `created_at`. |
| `generated_content` | FK `product_id` -> `products.id` (indexed, `ON DELETE CASCADE`). `content_type` is a native `Enum` (faq/blog/meta/release_notes/campaign). Indexed on `created_at`. |
| `users` | Auth scaffold. Unique index on `email`. |

No data migrations needed (fresh schema).

## Module 2 - Ingestion signals

**Date:** 2026-07-07

Added columns to `website_data`:

| Column | Type | Notes |
|---|---|---|
| `faq_count` | Integer, nullable | count of FAQ-style headings/elements found |
| `schema_types` | JSON list, default `[]` | schema.org `@type` values found across crawled pages |
| `internal_links_count` | Integer, nullable | |
| `images_missing_alt_count` | Integer, nullable | |
| `last_updated_signal` | String(255), nullable | best-effort freshness signal |
| `crawled_pages` | JSON list, default `[]` | `[{url, role, snapshot_path}]` |
| `failed_pages` | JSON list, default `[]` | `[{url, reason}]` |
| `status` | Enum `IngestionStatus`, default `pending` | |
| `error_message` | Text, nullable | |

New table `play_store_data` (see ARCHITECTURE.md for why it's a separate
table rather than columns on `website_data`):

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `product_id` | FK -> `products.id`, indexed, `ON DELETE CASCADE` | |
| `app_title`, `short_description`, `full_description` | String/Text, nullable | |
| `rating` | Float, nullable | |
| `rating_count` | Integer, nullable | |
| `rating_distribution` | JSON dict, default `{}` | `{"1": n, ..., "5": n}` |
| `category` | String(255), nullable | |
| `store_last_updated` | String(64), nullable | human-readable date from the store |
| `current_version` | String(64), nullable | |
| `installs` | String(64), nullable | bucketed range, e.g. `"10,000,000+"` |
| `permissions` | JSON list, default `[]` | |
| `description_word_count` | Integer, nullable | derived |
| `has_faq_content` | Boolean, default `false` | derived |
| `keyword_density` | JSON dict, default `{}` | derived, heuristic keyword -> ratio |
| `days_since_update` | Integer, nullable | derived |
| `reviews_fetched_count` | Integer, nullable | |
| `status` | Enum `IngestionStatus`, default `pending` | |
| `error_message` | Text, nullable | |
| `fetched_at` | DateTime, indexed | |

No new columns on `reviews` - Play Store reviews are inserted as normal
rows (`source="play_store"`, `sentiment_label=null` until Module 3).

**Caveat (documented, not fixed in MVP):** since we use `create_all()`
instead of a real migration tool, an *existing* `geo.db` created before this
change will **not** automatically get the new `website_data` columns or the
new `play_store_data` table - `create_all()` only creates missing tables,
it does not alter existing ones. Delete `geo.db` and let it recreate, or
add real Alembic migrations, once this matters outside the MVP.

## Module 3 - Review intelligence

**Date:** 2026-07-07

Added column to `reviews`:

| Column | Type | Notes |
|---|---|---|
| `is_analyzed` | Boolean, default `false`, indexed | set true after review is processed by Review Intelligence agent |

New table `review_summaries` (see ARCHITECTURE.md for rationale vs `audit_reports`):

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `product_id` | FK -> `products.id`, indexed, `ON DELETE CASCADE` | |
| `top_complaints` | JSON list, default `[]` | ranked up to 10 |
| `top_feature_requests` | JSON list, default `[]` | ranked up to 10 |
| `positive_themes` | JSON list, default `[]` | 3-5 bullets |
| `negative_themes` | JSON list, default `[]` | 3-5 bullets |
| `overall_sentiment_score` | Float, nullable | -1.0 to 1.0 |
| `reviews_analyzed_count` | Integer, default 0 | |
| `batches_processed` | Integer, default 0 | |
| `batches_failed` | Integer, default 0 | |
| `batch_outputs` | JSON list, default `[]` | raw per-batch LLM outputs |
| `status` | Enum `IngestionStatus`, default `pending` | |
| `error_message` | Text, nullable | |
| `created_at` | DateTime, indexed | |

New shared service: `app/services/llm_client.py` — all future LLM calls must
use this wrapper.

## Module 4 - Audit + Competitor

**Date:** 2026-07-07

Extended `competitors` table:

| Column | Type | Notes |
|---|---|---|
| `geo_score` | Integer, nullable | rule-based GEO score |
| `score_breakdown` | JSON, nullable | component breakdown |
| `crawl_signals` | JSON, nullable | extracted crawl signals |

New table `comparison_summaries`:

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `product_id` | FK, indexed | |
| `missing_features` | JSON list | from LLM comparison |
| `missing_faqs` | JSON list | from LLM comparison |
| `improvement_plan` | JSON list | prioritized actions |
| `narrative_summary` | Text, nullable | |
| `competitor_scores` | JSON list | per-competitor scores |
| `status` | IngestionStatus | for polling |
| `error_message` | Text, nullable | |
| `created_at` | DateTime, indexed | |

New shared service: `app/services/geo_scoring_service.py` — pure scoring function.

## Module 5 - RAG + Content Generation

**Date:** 2026-07-07

Extended `ContentType` enum: `meta_description`, `product_description`, `campaign_bundle`.

New services:
- `app/services/embedding_service.py`
- `app/services/rag_ingestion.py`
- `app/services/rag_retrieval.py`
- `app/vector_db/collection_service.py`

ChromaDB collections: `product_{product_id}` per product, created on first ingest.

## Module 6 - Orchestrator, Reporting, Scheduling

**Date:** 2026-07-07

New table `pipeline_runs`:

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `product_id` | FK -> `products.id`, indexed, `ON DELETE CASCADE` | |
| `started_at` | DateTime, indexed | default `utcnow` |
| `completed_at` | DateTime, nullable | |
| `status` | Enum `PipelineRunStatus` | pending/running/success/partial/failed |
| `stage_statuses` | JSON dict | per-stage `{status, duration_ms, error_message}` |
| `competitor_urls` | JSON list | URLs passed to competitor stage |
| `error_message` | String(1024), nullable | top-level crash message |

New table `reports`:

| Column | Type | Notes |
|---|---|---|
| `id` | PK | |
| `product_id` | FK -> `products.id`, indexed, `ON DELETE CASCADE` | |
| `file_path` | String(1024) | path to rendered HTML in `reports/` |
| `pipeline_run_id` | Integer, nullable, indexed | links report to a pipeline run |
| `created_at` | DateTime, indexed | from `CreatedAtMixin` |

New services:
- `app/services/dashboard_service.py` — batch dashboard aggregation
- `app/services/scheduler_service.py` — APScheduler weekly full-audit job

Orchestrator completed: sequences all Module 2–6 agents with partial-failure
tolerance and `pipeline_runs` persistence.

Reporting agent: Jinja2 HTML reports written to `reports/` directory on disk.

Settings: `SCHEDULER_ENABLED`, `SCHEDULER_INTERVAL_DAYS`.

**Caveat:** delete `geo.db` to pick up new tables if using an existing MVP DB.
