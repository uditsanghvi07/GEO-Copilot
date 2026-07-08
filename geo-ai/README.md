# AI GEO Copilot — Backend

**Enterprise AI Discoverability Platform** that audits and improves how well a product can be discovered, understood, and recommended by generative AI systems (ChatGPT, Claude, Gemini, Perplexity, AI search).

> **One-line pitch (resume / interview):**  
> *Built a multi-agent FastAPI backend with RAG (ChromaDB + LlamaIndex + local embeddings) that crawls websites and Play Store listings, scores AI discoverability (GEO score 0–100), analyzes reviews via LLM map-reduce, compares competitors, and generates grounded marketing content using DeepSeek.*

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [Simple Workflow (Start Here)](#simple-workflow-start-here)
3. [Tech Stack](#tech-stack)
4. [System Architecture](#system-architecture)
5. [AI & RAG Pipeline (Deep Dive)](#ai--rag-pipeline-deep-dive)
6. [Multi-Agent System](#multi-agent-system)
7. [GEO Scoring Engine](#geo-scoring-engine)
8. [How the Server Sends Responses](#how-the-server-sends-responses)
9. [All API Endpoints](#all-api-endpoints)
10. [Database & Data Flow](#database--data-flow)
11. [External Services & Connections](#external-services--connections)
12. [Enterprise / Advanced Patterns](#enterprise--advanced-patterns)
13. [How to Explain This in an Interview](#how-to-explain-this-in-an-interview)
14. [Resume Bullet Points](#resume-bullet-points)
15. [Setup & Run](#setup--run)
16. [Project Structure](#project-structure)

---

## What This Project Does

Traditional SEO optimizes for Google search rankings. **GEO (Generative Engine Optimization)** optimizes for **AI systems** that answer user questions and recommend products.

This backend answers:

| Question | How |
|----------|-----|
| Can AI systems find and understand our product? | Website crawler + Play Store analyzer extract signals |
| How discoverable are we vs competitors? | Rule-based GEO score + competitor comparison |
| What do users complain about? | LLM map-reduce over Play Store reviews |
| What should we fix first? | LLM-generated prioritized action plan |
| What content should we publish? | RAG-grounded FAQ, blog, meta, campaign copy |

**Input:** Product name, website URL, Play Store URL, optional competitor URLs  
**Output:** GEO score (0–100), review intelligence, competitor analysis, AI-generated content, HTML audit report

---

## Simple Workflow (Start Here)

### User journey (3 steps)

```
1. Register product     →  POST /products
2. Run full audit       →  POST /run-full-audit
3. View results         →  GET /dashboard  or  GET /report/{product_id}
```

### What happens inside (6 pipeline stages)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         POST /run-full-audit                            │
│                    (Orchestrator coordinates all agents)               │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
┌───────────────────┐                               ┌───────────────────┐
│  Website Crawler  │  (parallel)                   │ Play Store Agent  │
│  Playwright crawl │                               │ google-play-scraper│
│  → website_data   │                               │ → play_store_data │
│  → HTML snapshots │                               │ → reviews table   │
└─────────┬─────────┘                               └─────────┬─────────┘
          │                                                     │
          └──────────────────────┬──────────────────────────────┘
                                 ▼
                    ┌────────────────────────┐
                    │   RAG INGESTION        │
                    │   Chunk → Embed →      │
                    │   ChromaDB (per product)│
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ Review Intelligence    │
                    │ LLM map-reduce         │
                    │ → review_summaries     │
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ Audit Agent            │
                    │ Rule GEO score +       │
                    │ LLM action plan        │
                    │ → audit_reports        │
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ Competitor Agent       │
                    │ (optional) crawl+score │
                    │ + LLM comparison       │
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ Content Generation     │
                    │ RAG retrieve top-5     │
                    │ + DeepSeek LLM         │
                    │ → generated_content    │
                    └────────────┬───────────┘
                                 ▼
                    ┌────────────────────────┐
                    │ Reporting Agent        │
                    │ Jinja2 HTML report     │
                    │ → reports/*.html       │
                    └────────────────────────┘
```

### Poll for progress

Long-running jobs return `202 Accepted` immediately. Poll status endpoints:

| Job | Start | Poll |
|-----|-------|------|
| Website crawl | `POST /crawl` | `GET /crawl/status/{product_id}` |
| Play Store audit | `POST /playstore-audit` | `GET /playstore-audit/status/{product_id}` |
| Review analysis | `POST /reviews/analyze` | `GET /reviews/summary/{product_id}` |
| Competitor compare | `POST /compare` | `GET /compare/status/{product_id}` |
| Full pipeline | `POST /run-full-audit` | `GET /run-full-audit/status/{pipeline_run_id}` |

---

## Tech Stack

### Core frameworks

| Layer | Technology | Why |
|-------|------------|-----|
| API | **FastAPI** + **Uvicorn** | Async REST API, auto OpenAPI docs at `/docs` |
| ORM | **SQLAlchemy 2.x** | Type-safe DB access; SQLite now, Postgres-ready |
| Validation | **Pydantic v2** | Request/response schemas + settings |
| Auth | **JWT** (python-jose) + **bcrypt** | User registration/login scaffold |
| Logging | **loguru** | Structured logs + rotating file sink |

### AI / ML / RAG

| Component | Technology | Role |
|-----------|------------|------|
| LLM | **DeepSeek API** (OpenAI-compatible) | Review analysis, action plans, content, comparisons |
| Embeddings | **sentence-transformers** (`BAAI/bge-small-en-v1.5`) | Local, free — no paid embedding API |
| Vector DB | **ChromaDB** (persistent, cosine HNSW) | One collection per product: `product_{id}` |
| RAG framework | **LlamaIndex** | Retrieval over ChromaVectorStore |
| LLM gateway | Custom `LLMClient` | Retries, 429 backoff, JSON validation |

### Data collection

| Tool | Role |
|------|------|
| **Playwright** | Headless browser crawl (JS-rendered pages) |
| **BeautifulSoup4** | HTML parsing, text extraction |
| **google-play-scraper** | Play Store listing + reviews (unofficial) |

### Infrastructure patterns

| Tool | Role |
|------|------|
| **APScheduler** | Weekly automated full-audit for all products |
| **FastAPI BackgroundTasks** | Async job execution (Celery-ready design) |
| **Jinja2** | HTML audit report templates |

### Testing

| Tool | Role |
|------|------|
| **pytest** + **pytest-asyncio** | API and service unit tests |
| **httpx** | Async HTTP client for tests |

### Frontend (companion app)

React 19 + TypeScript + Vite + Tailwind CSS 4 — lives in `../frontend/`, talks to this API on port 8000.

---

## System Architecture

```
┌──────────────┐     HTTP/JSON      ┌──────────────────────────────────────┐
│   Frontend   │ ◄────────────────► │           FastAPI (main.py)          │
│  React/Vite  │                    │  api/  →  thin route controllers      │
└──────────────┘                    └──────────────┬───────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    ▼                              ▼                              ▼
           ┌────────────────┐            ┌─────────────────┐           ┌─────────────────┐
           │  Orchestrator  │            │ Shared Services │           │   SQLAlchemy    │
           │  6-stage pipe  │            │ llm_client      │           │   SQLite/Postgres│
           └───────┬────────┘            │ geo_scoring     │           │   13 tables     │
                   │                     │ rag_ingestion   │           └─────────────────┘
                   ▼                     │ rag_retrieval   │
           ┌────────────────┐            │ embedding_svc   │           ┌─────────────────┐
           │  7 Agents      │            │ dashboard_svc   │           │    ChromaDB     │
           │  crawler       │            │ scheduler_svc   │           │  ./chroma/      │
           │  playstore     │            └────────┬────────┘           │  per-product    │
           │  reviews       │                     │                    │  collections    │
           │  audit         │                     ▼                    └─────────────────┘
           │  competitor    │            ┌─────────────────┐
           │  content       │            │  DeepSeek API   │
           │  reporting     │            │  (external LLM) │
           └────────────────┘            └─────────────────┘
```

**Design principle:** Each agent is isolated — `BaseAgent.execute()` catches failures and returns `AgentResult` without crashing the pipeline. One failed stage does not stop the rest.

---

## AI & RAG Pipeline (Deep Dive)

This section explains **how RAG works in this project** in plain language — useful for understanding the code and explaining it in interviews.

### The problem RAG solves

A normal LLM call looks like this:

```
You:  "Write an FAQ for my fitness app"
LLM:  *guesses from training data* → generic, possibly wrong answers
```

**RAG (Retrieval-Augmented Generation)** fixes this:

```
You:  "Write an FAQ for my fitness app"
         ↓
System: searches YOUR real website + Play Store text first
         ↓
LLM:  reads those real chunks → writes FAQ grounded in YOUR product
```

The LLM still generates text, but it is **fed real context first** — so answers are factual and product-specific, not hallucinated.

---

### RAG in 3 simple steps

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. INGEST  │ ──► │  2. STORE   │ ──► │  3. RETRIEVE│
│  Crawl text │     │  Vector DB  │     │  + Generate │
└─────────────┘     └─────────────┘     └─────────────┘
```

| Step | What happens | File |
|------|--------------|------|
| **Ingest** | Crawl website + Play Store → split into chunks | `rag_ingestion.py` |
| **Store** | Convert chunks to numbers (embeddings) → save in ChromaDB | `embedding_service.py`, `vector_db/` |
| **Retrieve + Generate** | Find most relevant chunks → send to LLM with prompt | `rag_retrieval.py`, `content/service.py` |

---

### Step 1 — What gets ingested?

After a crawl or Play Store audit, `build_ingestion_chunks()` collects text from:

| Source | Sections ingested |
|--------|-------------------|
| **Website** | Title, meta description, H1/H2/H3 headings |
| **Website** | Full body text from HTML snapshots (homepage, FAQ, blog) |
| **Play Store** | Short description, full description |

Example raw text collected for product ID `3`:

```
Title:        "FitTrack Pro — Smart Fitness Companion"
Meta:         "Track workouts, calories, and goals with AI coaching"
Headings:     "Features" "Pricing" "How it works"
Homepage:     "FitTrack Pro helps you build habits with personalized..."
Play Store:   "The #1 fitness tracker for busy professionals..."
```

---

### Step 2 — Chunking (why we split text)

LLMs have token limits. We cannot send an entire website in one prompt. So text is split into **chunks**.

**Settings in code:**
- Target size: **~300 words** per chunk
- Overlap: **50 words** between consecutive chunks (so meaning is not cut off at boundaries)

**Example — one paragraph split into 2 chunks:**

```
Chunk 0 (words 0–300):
  "FitTrack Pro helps you build habits with personalized workout plans.
   Track steps, calories, and sleep. Our AI coach adapts to your goals..."

Chunk 1 (words 250–550):   ← starts 50 words before Chunk 0 ends (overlap)
  "...adapts to your goals. Premium users get meal planning and
   integration with Apple Health. Download free on Google Play..."
```

Each chunk is stored with metadata:

```json
{
  "id": "3_website_homepage_0",
  "text": "FitTrack Pro helps you build habits...",
  "metadata": {
    "source": "website",
    "section": "homepage",
    "product_id": 3
  }
}
```

---

### Step 3 — Embeddings (text → numbers)

An **embedding** converts text into a list of numbers (a vector) that captures **meaning**.

Think of it like GPS coordinates for ideas:
- "workout tracking app" and "fitness monitor" → vectors close together
- "workout tracking app" and "pizza recipe" → vectors far apart

**Model used:** `BAAI/bge-small-en-v1.5` (runs locally via `sentence-transformers` — free, no API call)

```python
# embedding_service.py — simplified
text  = "FitTrack Pro helps you track workouts"
vector = embed_texts([text])
# → [0.023, -0.118, 0.441, ...]  (384 numbers)
```

**Why local embeddings?**
- No per-request cost (important at scale)
- Works offline after first model download
- Data never leaves your server

---

### Step 4 — Storing in ChromaDB

Each product gets its **own isolated collection**:

```
chroma/
  └── product_3/     ← only FitTrack Pro's chunks
  └── product_7/     ← only another product's chunks
```

Storage uses **cosine similarity** (HNSW index) — when you search, ChromaDB finds chunks whose vectors point in a similar direction to your query vector.

```python
# collection_service.py
collection = get_product_collection(product_id=3)
collection.upsert(
    ids=["3_website_homepage_0", "3_play_store_short_description_0"],
    documents=[chunk_text_1, chunk_text_2],
    embeddings=[vector_1, vector_2],
    metadatas=[{"source": "website", "section": "homepage"}, ...]
)
```

Ingestion runs **automatically** after every successful crawl or Play Store audit — no separate API call needed.

---

### Step 5 — Retrieval (finding relevant chunks)

When you call `POST /generate-faq` for product `3`:

```
1. Build query string:  "faq"  (or "faq {topic_hint}" for blog/campaign)

2. Embed the query locally (same BGE model)

3. ChromaDB + LlamaIndex search collection "product_3"
   → return top 5 most similar chunks (cosine similarity)

4. Example retrieved chunks:
   Chunk A (homepage):  "...personalized workout plans, track steps..."
   Chunk B (faq page):  "...How do I sync with Google Fit? Open Settings..."
   Chunk C (play_store): "...AI coach adapts to your fitness goals..."
   Chunk D (headings):  "Features Pricing How it works FAQ"
   Chunk E (meta):      "Track workouts, calories, and goals..."
```

**Safety check:** If ChromaDB has zero documents for this product, the server returns an error immediately — it will not call the LLM with empty context.

---

### Step 6 — Prompt construction (what the LLM actually sees)

Retrieved chunks are joined and injected into the user prompt:

```
SYSTEM PROMPT (from prompts.py):
  "You are an AI discoverability content writer.
   Generate 6-10 FAQ question/answer pairs grounded ONLY in the
   provided product context..."

USER PROMPT (built dynamically):
  Product context:
  ---
  FitTrack Pro helps you build habits with personalized workout plans...
  ---
  How do I sync with Google Fit? Open Settings and tap Connected Apps...
  ---
  AI coach adapts to your fitness goals. Premium users get meal planning...
  ---
  (3 more chunks)

  Generate content type: faq
```

Then sent to DeepSeek:

```json
POST https://api.deepseek.com/v1/chat/completions
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "You are an AI discoverability..."},
    {"role": "user",   "content": "Product context:\n---\nFitTrack Pro..."}
  ],
  "temperature": 0.4,
  "max_tokens": 2000
}
```

**Response saved to database:**

```json
{
  "product_id": 3,
  "content_type": "faq",
  "content_body": "Q: How do I sync with Google Fit?\nA: Open Settings...",
  "prompt_used": "Product context:\n---\nFitTrack Pro helps...",
  "chunks_used": 5
}
```

The `prompt_used` field lets you audit exactly what context the LLM saw.

---

### Full RAG flow — one diagram

```
  CRAWL / PLAY STORE AUDIT
           │
           ▼
  ┌────────────────────────────────────────────┐
  │ build_ingestion_chunks()                   │
  │  website title, meta, headings, page bodies│
  │  play store short + full descriptions      │
  └──────────────────┬─────────────────────────┘
                     ▼
  ┌────────────────────────────────────────────┐
  │ _chunk_text()  →  ~300 words, 50 overlap   │
  └──────────────────┬─────────────────────────┘
                     ▼
  ┌────────────────────────────────────────────┐
  │ embed_texts()  →  BGE-small-en vectors     │
  │ (local, sentence-transformers)             │
  └──────────────────┬─────────────────────────┘
                     ▼
  ┌────────────────────────────────────────────┐
  │ ChromaDB upsert  →  collection product_{id}│
  └──────────────────┬─────────────────────────┘
                     │
        POST /generate-faq (later)
                     ▼
  ┌────────────────────────────────────────────┐
  │ retrieve_relevant_chunks(query, top_k=5)  │
  │ LlamaIndex + cosine similarity search      │
  └──────────────────┬─────────────────────────┘
                     ▼
  ┌────────────────────────────────────────────┐
  │ build_user_prompt(chunks) + system prompt  │
  └──────────────────┬─────────────────────────┘
                     ▼
  ┌────────────────────────────────────────────┐
  │ llm_client.chat_completion()  →  DeepSeek  │
  └──────────────────┬─────────────────────────┘
                     ▼
           generated_content table
```

---

### RAG vs non-RAG LLM calls in this project

| Feature | Uses RAG? | Why |
|---------|-----------|-----|
| FAQ / Blog / Meta / Campaign | **Yes** | Must be grounded in real product text |
| Review intelligence | No | Reads reviews directly from DB (not vector search) |
| Audit action plan | No | Uses structured GEO score breakdown as context |
| Competitor comparison | No | Uses crawled competitor signals as context |
| GEO scoring | No | Pure rules — no LLM at all |

---

### LLM usage across the system

| Stage | Uses LLM? | Pattern |
|-------|-----------|---------|
| Website crawl | No | Playwright + heuristics |
| Play Store audit | No | google-play-scraper + heuristics |
| Review intelligence | **Yes** | **Map-reduce**: batch ~45 reviews → per-batch analysis → single merged summary |
| Audit action plan | **Yes** | Rule score first, then LLM prioritizes fixes |
| Competitor comparison | **Yes** | Crawl + rule scores, then LLM narrative |
| Content generation | **Yes** | **RAG + LLM** (refuses if no ingested content) |
| GEO scoring | No | Pure rule-based (deterministic, auditable) |
| HTML reporting | No | Jinja2 template only |

### LLM client features (`services/llm_client.py`)

- Single gateway — all agents use one client (no duplicate HTTP calls)
- Exponential backoff retry (configurable `LLM_MAX_RETRIES`)
- HTTP 429 rate-limit handling
- JSON schema validation with one-shot strict retry on parse failure
- Configurable timeout (`LLM_TIMEOUT_SECONDS`)

---

## Multi-Agent System

Every agent lives in `app/agents/{name}/` with:
- `agent.py` — thin wrapper implementing `BaseAgent`
- `service.py` — core business logic
- `prompts.py` — LLM prompt templates

| Agent | Input | Output | Key tech |
|-------|-------|--------|----------|
| **Website Crawler** | `website_url` | `website_data`, HTML snapshots | Playwright, BeautifulSoup |
| **Play Store Analyzer** | `play_store_url` | `play_store_data`, `reviews` | google-play-scraper |
| **Review Intelligence** | `product_id` | `review_summaries` | LLM map-reduce |
| **Audit** | `product_id` | `audit_reports` | Rule scoring + LLM plan |
| **Competitor** | `competitor_urls[]` | `competitors`, `comparison_summaries` | Reuses crawler + LLM |
| **Content Generation** | `content_type` | `generated_content` | RAG + LLM |
| **Reporting** | `product_id` | `reports/*.html` | Jinja2 |

### Orchestrator pipeline order

```python
# app/orchestrator/orchestrator.py
1. Website Crawler + Play Store Analyzer  (asyncio.gather — parallel)
2. Review Intelligence Agent
3. Audit Agent
4. Competitor Agent  (skipped if no competitor_urls)
5. Content Generation  (FAQ + meta_description)
6. Reporting Agent  (always runs)
```

Each stage updates `pipeline_runs.stage_statuses` JSON so the frontend can show per-stage progress.

---

## GEO Scoring Engine

**GEO Score: 0–100** — deterministic, rule-based, no LLM (auditable and reproducible).

| Component | Max Points | What it measures |
|-----------|------------|------------------|
| Documentation depth | 20 | Word count, help/docs/blog pages |
| FAQ presence | 15 | FAQ page detected, FAQ count |
| Metadata quality | 15 | Title, meta description quality |
| Structured data | 15 | schema.org JSON-LD types |
| Authority signals | 15 | Internal link graph (proxy for site structure) |
| Review quality | 10 | Average rating, review volume |
| Freshness | 10 | Days since last update signal |

The Audit Agent computes this score, then asks the LLM for a **prioritized action plan** based on the breakdown — separating *measurement* (rules) from *recommendations* (AI).

---

## How the Server Sends Responses

Every API route follows the same pattern: **validate request → run logic → return typed JSON**.  
FastAPI uses **Pydantic schemas** (`app/schemas/`) so every request body and response is structured and documented in Swagger (`/docs`).

### Request → Response flow (how any API call works)

```
Client (browser / frontend / curl)
    │
    │  HTTP Request
    │  ├── Method:  POST / GET / PATCH / DELETE
    │  ├── Headers: Content-Type: application/json
    │  │            Authorization: Bearer <jwt>   (only /auth/me)
    │  └── Body:    JSON payload (for POST/PATCH)
    ▼
FastAPI Route (app/api/*.py)
    │
    │  1. Pydantic validates request body → rejects bad input with 422
    │  2. Route calls agent / service / DB
    │  3. Pydantic serializes response → JSON
    ▼
Client receives HTTP Response
    ├── Status code: 200 / 201 / 202 / 204 / 400 / 404 / 422 / 500
    └── Body: JSON payload (or empty for 204)
```

---

### Two response patterns

#### Pattern A — Synchronous (wait for result)

Used when the work is fast enough to finish in one HTTP request.

| Endpoint | Status | Meaning |
|----------|--------|---------|
| `POST /products` | `201 Created` | Product saved, full object returned |
| `POST /audit` | `201 Created` | GEO score computed, report returned |
| `POST /generate-faq` | `201 Created` | RAG + LLM done, content returned |
| `GET /dashboard` | `200 OK` | Data fetched from DB |

#### Pattern B — Asynchronous (start job, poll later)

Used for slow work (crawling, full pipeline, review analysis). Server responds immediately; work runs in background.

| Endpoint | Status | Meaning |
|----------|--------|---------|
| `POST /crawl` | `202 Accepted` | Job started — not done yet |
| `POST /run-full-audit` | `202 Accepted` | Pipeline started — poll for status |
| `POST /reviews/analyze` | `202 Accepted` | Analysis started — poll for result |

**Client must poll** the matching status endpoint until `status` is `success`, `partial`, or `failed`.

---

### Real request & response examples

#### 1. Create a product

**Request:**
```http
POST /products
Content-Type: application/json

{
  "name": "FitTrack Pro",
  "website_url": "https://fittrackpro.com",
  "play_store_url": "https://play.google.com/store/apps/details?id=com.fittrack",
  "category": "Health & Fitness"
}
```

**Response `201 Created`:**
```json
{
  "id": 3,
  "name": "FitTrack Pro",
  "website_url": "https://fittrackpro.com",
  "play_store_url": "https://play.google.com/store/apps/details?id=com.fittrack",
  "category": "Health & Fitness",
  "created_at": "2026-07-07T10:00:00",
  "updated_at": "2026-07-07T10:00:00"
}
```

---

#### 2. Start full audit (async)

**Request:**
```http
POST /run-full-audit
Content-Type: application/json

{
  "product_id": 3,
  "competitor_urls": [
    "https://competitor1.com",
    "https://competitor2.com"
  ]
}
```

**Immediate response `202 Accepted`:**
```json
{
  "pipeline_run_id": 12,
  "product_id": 3,
  "status": "running",
  "message": "Full audit pipeline started. Poll GET /run-full-audit/status/{pipeline_run_id}."
}
```

**Poll every few seconds:**
```http
GET /run-full-audit/status/12
```

**Response while running `200 OK`:**
```json
{
  "id": 12,
  "product_id": 3,
  "started_at": "2026-07-07T10:05:00",
  "completed_at": null,
  "status": "running",
  "competitor_urls": ["https://competitor1.com", "https://competitor2.com"],
  "error_message": null,
  "stage_statuses": {
    "website_crawler":      { "status": "success", "duration_ms": 8420,  "error_message": null },
    "play_store_analyzer":  { "status": "success", "duration_ms": 3100,  "error_message": null },
    "review_intelligence":  { "status": "running", "duration_ms": 0,     "error_message": null },
    "audit":                { "status": "pending", "duration_ms": 0,     "error_message": null },
    "competitor":           { "status": "pending", "duration_ms": 0,     "error_message": null },
    "content_faq":          { "status": "pending", "duration_ms": 0,     "error_message": null },
    "content_meta_description": { "status": "pending", "duration_ms": 0, "error_message": null },
    "reporting":            { "status": "pending", "duration_ms": 0,     "error_message": null }
  }
}
```

**Response when done `200 OK`:**
```json
{
  "id": 12,
  "product_id": 3,
  "started_at": "2026-07-07T10:05:00",
  "completed_at": "2026-07-07T10:12:30",
  "status": "success",
  "stage_statuses": {
    "website_crawler":          { "status": "success", "duration_ms": 8420,  "error_message": null },
    "play_store_analyzer":      { "status": "success", "duration_ms": 3100,  "error_message": null },
    "review_intelligence":      { "status": "success", "duration_ms": 18500, "error_message": null },
    "audit":                    { "status": "success", "duration_ms": 4200,  "error_message": null },
    "competitor":               { "status": "success", "duration_ms": 12000, "error_message": null },
    "content_faq":              { "status": "success", "duration_ms": 6800,  "error_message": null },
    "content_meta_description": { "status": "success", "duration_ms": 5100,  "error_message": null },
    "reporting":                { "status": "success", "duration_ms": 900,   "error_message": null }
  },
  "error_message": null
}
```

**Stage status values:** `success` | `partial` | `failed` | `skipped` | `pending` | `running`

---

#### 3. Sync audit (GEO score + action plan)

**Request:**
```http
POST /audit
Content-Type: application/json

{ "product_id": 3 }
```

**Response `201 Created`:**
```json
{
  "id": 7,
  "product_id": 3,
  "geo_score": 62,
  "score_breakdown": {
    "documentation_depth": { "max_points": 20, "earned": 14.0, "details": "Word count 1840, has blog page" },
    "faq_presence":        { "max_points": 15, "earned": 10.0, "details": "FAQ page found, 6 Q&A pairs" },
    "metadata_quality":    { "max_points": 15, "earned": 11.0, "details": "Title present, meta 142 chars" },
    "structured_data":     { "max_points": 15, "earned": 8.0,  "details": "schema.org: WebApplication, FAQPage" },
    "authority_signals":   { "max_points": 15, "earned": 7.0,  "details": "42 internal links" },
    "review_quality":      { "max_points": 10, "earned": 7.5,  "details": "4.2 avg rating, 87 reviews" },
    "freshness":           { "max_points": 10, "earned": 4.5,  "details": "Last update signal: 45 days ago" },
    "total": 62
  },
  "recommendations": {
    "action_plan": [
      { "step": "Add schema.org Organization markup", "component": "structured_data", "estimated_point_impact": 5.0 },
      { "step": "Expand FAQ to cover pricing and integrations", "component": "faq_presence", "estimated_point_impact": 4.0 },
      { "step": "Update Play Store listing with recent changelog", "component": "freshness", "estimated_point_impact": 3.0 }
    ]
  },
  "created_at": "2026-07-07T10:08:00"
}
```

---

#### 4. Crawl status (poll after `POST /crawl`)

**Request:**
```http
GET /crawl/status/3
```

**Response `200 OK`:**
```json
{
  "product_id": 3,
  "status": "success",
  "title": "FitTrack Pro — Smart Fitness Companion",
  "meta_description": "Track workouts, calories, and goals with AI coaching",
  "has_faq": true,
  "has_schema_markup": true,
  "word_count": 1840,
  "schema_types": ["WebApplication", "FAQPage"],
  "failed_pages": [],
  "error_message": null,
  "last_crawled_at": "2026-07-07T10:05:42"
}
```

**`status` values:** `pending` → `running` → `success` | `partial` | `failed`

---

#### 5. Review summary (after analysis)

**Response `200 OK` from `GET /reviews/summary/3`:**
```json
{
  "id": 4,
  "product_id": 3,
  "top_complaints": ["App crashes on login", "Sync with Google Fit broken", "Battery drain"],
  "top_feature_requests": ["Dark mode", "Apple Watch support", "Meal planner"],
  "positive_themes": ["Easy to use", "Good workout variety", "Helpful AI coach"],
  "negative_themes": ["Bugs after updates", "Premium paywall too aggressive"],
  "overall_sentiment_score": 0.35,
  "reviews_analyzed_count": 87,
  "batches_processed": 2,
  "batches_failed": 0,
  "status": "success",
  "total_reviews": 100,
  "average_rating": 4.2,
  "rating_distribution": { "one": 3, "two": 5, "three": 12, "four": 28, "five": 52 },
  "sentiment_counts": { "positive": 80, "neutral": 12, "negative": 8 },
  "created_at": "2026-07-07T10:07:00"
}
```

---

#### 6. RAG content generation

**Request:**
```http
POST /generate-faq
Content-Type: application/json

{ "product_id": 3 }
```

**Response `201 Created`:**
```json
{
  "id": 15,
  "product_id": 3,
  "content_type": "faq",
  "content_body": "Q: How do I sync with Google Fit?\nA: Open Settings, tap Connected Apps, and select Google Fit...\n\nQ: Is there a free version?\nA: Yes, FitTrack Pro offers a free tier with basic workout tracking...",
  "prompt_used": "Product context:\n---\nFitTrack Pro helps you build habits...",
  "created_at": "2026-07-07T10:11:00"
}
```

---

#### 7. Dashboard (aggregated view)

**Response `200 OK` from `GET /dashboard`:**
```json
{
  "products": [
    {
      "product_id": 3,
      "name": "FitTrack Pro",
      "category": "Health & Fitness",
      "geo_score": 62,
      "last_audit_date": "2026-07-07T10:08:00",
      "pipeline_status": "success",
      "last_pipeline_date": "2026-07-07T10:12:30",
      "website_url": "https://fittrackpro.com",
      "play_store_url": "https://play.google.com/store/apps/details?id=com.fittrack"
    }
  ],
  "total": 1
}
```

---

#### 8. HTML report

**Response `200 OK` from `GET /report/3`:**
```json
{
  "id": 9,
  "product_id": 3,
  "file_path": "reports/report_3_20260707_101230.html",
  "created_at": "2026-07-07T10:12:30",
  "html_content": "<!DOCTYPE html><html><head><title>GEO Audit Report...</title>..."
}
```

The frontend renders `html_content` directly in an iframe — no second file download needed.

---

### Error responses

When something goes wrong, FastAPI returns a standard error JSON:

| Status | When | Example body |
|--------|------|--------------|
| `404` | Resource not found | `{ "detail": "Product not found" }` |
| `422` | Invalid request body | `{ "detail": [{ "loc": ["body","name"], "msg": "field required" }] }` |
| `400` | Business rule violation | `{ "detail": "No ingested content found for this product" }` |
| `500` | Unhandled server error | `{ "detail": "Internal server error" }` |

**Example — generate content before crawl:**
```http
POST /generate-faq
{ "product_id": 99 }

→ 400 Bad Request
{
  "detail": "No ingested content found for this product. Run POST /crawl and POST /playstore-audit first."
}
```

---

### Internal agent envelope (not sent to client directly)

Inside the backend, every agent returns a typed wrapper — this is what the Orchestrator uses to track partial failures:

```json
{
  "success": true,
  "data": { "product_id": 3, "geo_score": 62, "audit_report_id": 7 },
  "error_message": null,
  "duration_ms": 4200.5
}
```

On failure:
```json
{
  "success": false,
  "data": null,
  "error_message": "Play Store URL returned no reviews",
  "duration_ms": 3100.0
}
```

The Orchestrator converts these into `stage_statuses` in the pipeline response — the client never sees `AgentResult` directly.

---

### HTTP status code cheat sheet

| Code | Name | Used for |
|------|------|----------|
| `200` | OK | GET requests, status polling |
| `201` | Created | POST that returns new resource (product, audit, content) |
| `202` | Accepted | Background job started (crawl, pipeline, reviews) |
| `204` | No Content | DELETE success (empty body) |
| `404` | Not Found | Product / pipeline run / report not found |
| `422` | Unprocessable | Pydantic validation failed (missing field, wrong type) |

---

## All API Endpoints

Interactive docs: **`http://localhost:8000/docs`**

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |

### Auth (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Create user, return JWT |
| `POST` | `/auth/login` | Login, return JWT |
| `GET` | `/auth/me` | Current user (Bearer token required) |

### Products (`/products`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/products` | Create product |
| `GET` | `/products` | List all products |
| `GET` | `/products/{id}` | Get one product |
| `PATCH` | `/products/{id}` | Update product |
| `DELETE` | `/products/{id}` | Delete product + all related data (cascade) |

### Website Crawler

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/crawl` | Start background crawl → `202` |
| `GET` | `/crawl/status/{product_id}` | Crawl status + extracted signals |

### Play Store

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/playstore-audit` | Start background audit → `202` |
| `GET` | `/playstore-audit/status/{product_id}` | Audit status + listing metadata |

### Review Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reviews/analyze` | Start LLM review analysis → `202` |
| `GET` | `/reviews/summary/{product_id}` | Merged summary + live stats |

### Audit

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/audit` | **Sync** — compute GEO score + action plan |
| `GET` | `/audit/{product_id}` | Latest audit report |

### Competitor Comparison

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/compare` | Start competitor crawl/compare → `202` |
| `GET` | `/compare/status/{product_id}` | Comparison result |

### Content Generation (RAG-powered)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/generate-faq` | RAG-grounded FAQ |
| `POST` | `/generate-blog` | RAG-grounded blog post |
| `POST` | `/generate-meta` | RAG-grounded meta description |
| `POST` | `/generate-campaign` | RAG-grounded campaign bundle |
| `GET` | `/content/{product_id}` | List all generated content |

### Pipeline, Reports & Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/run-full-audit` | Trigger full 6-stage pipeline → `202` |
| `GET` | `/run-full-audit/status/{pipeline_run_id}` | Per-stage pipeline status |
| `GET` | `/report/{product_id}` | Latest HTML report |
| `GET` | `/reports/{product_id}` | All reports for product |
| `DELETE` | `/reports/{report_id}` | Delete report + file |
| `GET` | `/dashboard` | Aggregated product grid |
| `POST` | `/dev/trigger-scheduled-audit` | Dev-only: run weekly scheduler manually |

---

## Database & Data Flow

**Default:** SQLite (`geo.db`) — swap `DATABASE_URL` to Postgres with zero business-logic changes.

### Tables (all cascade-delete from `products`)

```
products
├── website_data          (one crawl snapshot per product)
├── play_store_data       (one Play Store snapshot)
├── reviews               (individual Play Store reviews)
├── review_summaries      (LLM-merged intelligence)
├── audit_reports         (GEO score + breakdown + recommendations)
├── competitors           (per-competitor crawl + score)
├── comparison_summaries  (product-level comparison result)
├── generated_content     (AI content by type: faq, blog, meta, campaign)
├── pipeline_runs         (full audit run tracking + stage_statuses JSON)
└── reports               (HTML report file metadata)

users                     (JWT auth, independent)
```

### Status enums

- **`IngestionStatus`:** `pending` → `running` → `success` | `partial` | `failed`
- **`PipelineRunStatus`:** `pending` → `running` → `success` | `partial` | `failed`

---

## External Services & Connections

| Service | Protocol | Used for | Config |
|---------|----------|----------|--------|
| **DeepSeek API** | HTTPS REST (OpenAI-compatible) | All LLM calls | `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` |
| **Target websites** | HTTPS + Playwright | Product/competitor crawling | — |
| **Google Play Store** | google-play-scraper lib | Listing + reviews | No API key (unofficial scraper) |
| **HuggingFace Hub** | HTTPS | Download embedding model on first run | `EMBEDDING_MODEL_NAME` |
| **ChromaDB** | Local filesystem | Vector storage | `CHROMA_PERSIST_DIR` |
| **SQLite / Postgres** | SQLAlchemy | Relational data | `DATABASE_URL` |

**Not used (stubs ready):** SMTP email, PDF export, paid embedding APIs, OpenAI directly.

---

## Enterprise / Advanced Patterns

These are the **senior-level engineering decisions** worth highlighting:

| Pattern | Implementation | Why it matters |
|---------|----------------|----------------|
| **Multi-agent orchestration** | `Orchestrator` + `BaseAgent` with failure isolation | One agent crash does not kill the pipeline |
| **Partial failure tolerance** | `PARTIAL` status, per-stage `stage_statuses` JSON | Production-grade resilience |
| **Concurrent ingestion** | `asyncio.gather` for crawler + playstore | Faster pipeline, independent I/O |
| **RAG with local embeddings** | No paid embedding API — cost control at scale | Enterprise cost optimization |
| **Per-tenant vector isolation** | One ChromaDB collection per product | Multi-tenant ready |
| **LLM map-reduce** | Review batches → merge | Handles 100+ reviews within token limits |
| **Deterministic + LLM hybrid** | Rule GEO score + LLM recommendations | Auditable metrics + actionable AI advice |
| **Single LLM gateway** | `LLMClient` with retry/429/JSON validation | Centralized observability and error handling |
| **Background job pattern** | `202 Accepted` + polling | Celery/Redis swap without API changes |
| **Scheduled automation** | APScheduler weekly full-audit | Hands-off monitoring |
| **Prompt traceability** | `prompt_used` stored on every generated content row | Debuggable, auditable AI outputs |
| **Postgres migration path** | URL swap only, no SQLite-specific logic | Production deployment ready |
| **JWT auth scaffold** | bcrypt + python-jose, `get_current_user` dependency | Security layer ready to enforce |

---

## How to Explain This in an Interview

### 30-second version

> "I built an AI discoverability platform — think SEO but for ChatGPT and Gemini. It crawls a company's website and Play Store listing, ingests that content into a vector database using local embeddings, scores how AI-friendly the product is on a 0–100 scale, analyzes user reviews with an LLM map-reduce pattern, compares competitors, and generates marketing content grounded in real product data via RAG. It's a FastAPI backend with seven specialized agents coordinated by an orchestrator."

### If they ask "What is GEO?"

> "GEO is Generative Engine Optimization — making your product easy for AI systems to find, understand, and recommend. Unlike SEO which optimizes for search rankings, GEO optimizes for how LLMs retrieve and cite your product when users ask questions."

### If they ask "How does RAG work in your project?"

> "After we crawl the website and Play Store, we chunk the text into ~300-word segments with overlap, embed them locally using BGE-small-en, and store in ChromaDB — one collection per product. When generating content, LlamaIndex retrieves the top 5 most relevant chunks for the query, injects them into the prompt, and DeepSeek generates grounded copy. The system refuses to generate if no content has been ingested — no hallucination from empty context."

### If they ask "Why map-reduce for reviews?"

> "A product can have 100+ reviews — too many for one LLM call. I batch them into groups of ~45, run a map step analyzing each batch independently, then a reduce step merging all batch analyses into one summary. This stays within token limits while preserving full coverage."

### If they ask "How do you handle failures?"

> "Each agent implements a base class where `execute()` never raises — it returns a success/failure result. The orchestrator logs failed stages, marks them in `stage_statuses`, and continues the pipeline. A crawl failure doesn't block report generation. The final run status is `success`, `partial`, or `failed` based on which stages completed."

### If they ask "What would you change for production?"

> "Swap BackgroundTasks for Celery + Redis, move SQLite to Postgres, add Alembic migrations, enforce JWT on all routes, add rate limiting, deploy ChromaDB as a managed service or migrate to Pinecone/Weaviate, and add proper SMTP for report delivery. The architecture is already structured for these swaps — only the dispatch and storage layers change."

---

## Resume Bullet Points

Copy-paste ready (adjust numbers to your experience):

- Architected and built a **multi-agent AI discoverability platform** (FastAPI) that audits product visibility across generative AI systems using **RAG**, **vector search**, and **LLM orchestration**
- Implemented **Retrieval-Augmented Generation** pipeline: local embeddings (BGE), **ChromaDB** vector store, **LlamaIndex** retrieval — generating grounded FAQ, blog, and campaign content from crawled product data
- Designed **7 specialized AI agents** (crawler, Play Store analyzer, review intelligence, audit, competitor, content, reporting) coordinated by a central **Orchestrator** with partial-failure tolerance
- Built **LLM map-reduce** pattern for review intelligence — batching 100+ Play Store reviews into token-safe chunks with merged sentiment and complaint analysis
- Created deterministic **GEO scoring engine** (0–100, 7 weighted components) combined with LLM-generated prioritized action plans
- Integrated **DeepSeek API** via centralized LLM gateway with exponential backoff, rate-limit handling, and JSON schema validation
- Used **Playwright** headless crawling and **google-play-scraper** for automated data ingestion with **APScheduler** for weekly audit automation

**Skills to list:** Python, FastAPI, RAG, LLM, ChromaDB, LlamaIndex, sentence-transformers, SQLAlchemy, Playwright, Pydantic, APScheduler, REST API design, Multi-agent systems

---

## Setup & Run

```bash
# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Dependencies
pip install -r requirements.txt
playwright install

# 3. Environment
cp .env.example .env
# Required: DEEPSEEK_API_KEY, JWT_SECRET

# 4. Start API (auto-creates DB tables)
uvicorn app.main:app --reload
```

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | API base |
| `http://localhost:8000/docs` | Swagger UI (try all endpoints) |
| `http://localhost:8000/health` | Health check |

### Run tests

```bash
pytest
```

### Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENVIRONMENT` | `dev` | `dev` or `prod` |
| `DEEPSEEK_API_KEY` | — | **Required** for LLM features |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | LLM endpoint |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Model name |
| `DATABASE_URL` | `sqlite:///./geo.db` | Database connection |
| `CHROMA_PERSIST_DIR` | `./chroma` | Vector DB storage |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-small-en-v1.5` | Local embedding model |
| `JWT_SECRET` | — | **Required** for auth |
| `SCHEDULER_ENABLED` | `true` | Weekly auto-audit |
| `SCHEDULER_INTERVAL_DAYS` | `7` | Scheduler interval |

See `.env.example` for the full list.

---

## Project Structure

```
geo-ai/
├── app/
│   ├── main.py                 # FastAPI entry, CORS, lifespan, routers
│   ├── api/                    # Route controllers (11 modules)
│   ├── agents/                 # 7 agents (crawler, playstore, reviews, audit,
│   │   ├── base.py             #   competitor, content, reporting)
│   │   ├── crawler/
│   │   ├── playstore/
│   │   ├── reviews/
│   │   ├── audit/
│   │   ├── competitor/
│   │   ├── content/
│   │   └── reporting/          # + templates/audit_report.html.j2
│   ├── orchestrator/           # Full pipeline sequencing
│   ├── services/               # LLM, RAG, scoring, dashboard, scheduler
│   ├── models/                 # SQLAlchemy ORM (13 tables)
│   ├── schemas/                # Pydantic request/response types
│   ├── database/               # Session, Base, init_db
│   ├── vector_db/              # ChromaDB client + collection helpers
│   ├── config/                 # Settings singleton
│   └── utils/                  # Logging, security, retry, exceptions
├── tests/                      # pytest suite
├── chroma/                     # ChromaDB data (runtime)
├── reports/                    # Generated HTML reports (runtime)
├── uploads/website_snapshots/  # Crawled HTML (runtime)
├── logs/app.log                # Rotating application logs
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md             # Detailed module build log
└── MIGRATIONS.md               # Schema change notes
```

---

## Related Docs

- **`ARCHITECTURE.md`** — detailed module-by-module build log
- **`MIGRATIONS.md`** — database schema change history
- **`../frontend/`** — React dashboard UI

---

*AI GEO Copilot — making products discoverable in the age of generative AI.*
