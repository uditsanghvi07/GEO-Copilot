# AI GEO Copilot — Frontend

React + Tailwind CSS dashboard for the AI GEO Copilot backend.

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS v4 (design tokens in `src/index.css`)
- Framer Motion (animations, respects `prefers-reduced-motion`)
- Recharts (sentiment charts)
- Lucide React (icons)
- React Router

## Quick start

```bash
# From geo-ai/ — start the API
uvicorn app.main:app --reload

# From frontend/ — start the UI
cp .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. API requests proxy to `http://127.0.0.1:8000` via `/api`.

## Design system

Tokens are defined once in `src/index.css` (`@theme`):

| Token | Value | Usage |
|---|---|---|
| `bg` | `#0B0F17` | Page background |
| `surface` | `#131A26` | Cards, panels |
| `border` | `#1F2836` | Hairline borders |
| `accent` | `#00E6C3` | Score ring, success, primary CTA |
| `coral` | `#FF6B4A` | Warnings, missing indicators |
| `text` / `muted` | `#E8ECF1` / `#7C8798` | Body copy |

Fonts: Space Grotesk (headings), Inter (UI), JetBrains Mono (all numeric values).

## Pages

- `/login`, `/register` — JWT auth
- `/` — Dashboard product grid
- `/products/new` — Add product + kick off crawl
- `/products/:id` — Product detail with tabs
- `/settings` — Account + logout

## API client

All HTTP calls go through `src/api/client.ts` with `VITE_API_BASE_URL` (default `/api`).
