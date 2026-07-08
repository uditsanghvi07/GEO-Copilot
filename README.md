# AI GEO Copilot

**Full-stack AI Discoverability Platform** — audits and improves how well products are discovered by generative AI systems (ChatGPT, Claude, Gemini, AI search).

```
AI_geo/
├── geo-ai/      ← FastAPI backend (AI agents, RAG, APIs)
└── frontend/    ← React dashboard UI
```

## Quick Start

### Backend

```bash
cd geo-ai
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && playwright install
cp .env.example .env   # set DEEPSEEK_API_KEY
uvicorn app.main:app --reload
```

API: `http://localhost:8000` · Docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173`

## What It Does (One Paragraph)

Crawls a product's website and Google Play Store listing, ingests content into a **RAG vector database** (ChromaDB + local embeddings), scores **AI discoverability** on a 0–100 GEO scale, analyzes reviews via **LLM map-reduce**, compares competitors, generates **grounded marketing content**, and produces HTML audit reports — all orchestrated by **7 specialized AI agents**.

## Documentation

| Doc | Contents |
|-----|----------|
| **[geo-ai/README.md](geo-ai/README.md)** | **Full backend documentation** — architecture, RAG deep dive (chunking, embeddings, retrieval), request/response payloads, all APIs, interview guide, resume bullets |
| [geo-ai/ARCHITECTURE.md](geo-ai/ARCHITECTURE.md) | Module-by-module build log |
| [geo-ai/MIGRATIONS.md](geo-ai/MIGRATIONS.md) | Database schema changes |

## Tech at a Glance

| Layer | Stack |
|-------|-------|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic |
| AI / RAG | DeepSeek LLM, ChromaDB, LlamaIndex, sentence-transformers |
| Crawling | Playwright, BeautifulSoup, google-play-scraper |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |
| Patterns | Multi-agent orchestration, map-reduce LLM, RAG, background jobs, APScheduler |
