# RAGcoon

Senior-project RAG app: React frontend + FastAPI backend + Postgres + Ollama (+ Qdrant Cloud).

## Quick start (Docker — recommended)

**Requirements**
- Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux)
- Enough RAM for Ollama + embeddings (8GB+ recommended)
- A Qdrant Cloud URL + API key (for RAG/chat features)

### Option 1 — click / run script

**Windows**
- Double-click `start.bat`  
  or in PowerShell: `.\start.ps1`

**Mac / Linux**
```bash
chmod +x start.sh stop.sh scripts/start.sh scripts/stop.sh
./start.sh
```

The start script will:
1. Create `.env` and `backend/.env` from `.env.example` if missing
2. Warn if Qdrant/JWT values still look like placeholders
3. Run `docker compose -p ragcoon up -d --build`
4. Wait until backend + frontend are healthy
5. Open http://localhost:5173

**Stop**
- Windows: double-click `stop.bat` or `.\stop.ps1`
- Mac/Linux: `./stop.sh`

### Option 2 — commands only

```bash
# first time: copy env
cp .env.example .env
cp .env.example backend/.env
# then edit backend/.env — set QDRANT_URL and QDRANT_API_KEY

docker compose -p ragcoon up -d --build
```

Or from repo root on Windows:

```bash
npm run stack:start
npm run stack:stop
```

```bash
npm run docker:up
npm run docker:down
npm run docker:logs
```

### URLs

| Service   | URL                      |
|-----------|--------------------------|
| Frontend  | http://localhost:5173    |
| Backend   | http://localhost:8000/docs |
| pgAdmin   | http://localhost:8080    |
| Ollama    | http://localhost:11434   |
| Postgres  | localhost:5432           |

### After clone — edit secrets

Edit `backend/.env` (and optionally root `.env` for Compose variable substitution):

- `QDRANT_URL`
- `QDRANT_API_KEY`
- optionally `JWT_SECRET`, admin passwords, Gemini/OpenAI keys

Scripts never overwrite an existing `.env`.

## What runs in Docker

- `frontend` — Vite dev server (hot reload; source bind-mounted)
- `backend` — FastAPI with `--reload` (source bind-mounted)
- `postgres` — PostgreSQL + pgvector
- `pgadmin` — DB UI
- `ollama` — local LLM (`gemma3:4b` pulled on first start)

First start can take a long time (image pulls + Ollama model).

## Hybrid local frontend (optional)

If you only want infra/backend in Docker and Vite on the host:

```bash
npm run dev
```

This uses `scripts/dev.ps1` (Windows).

## Project layout

```text
RAGcoon/
├── backend/           # FastAPI + RAG
├── frontend/          # React + Vite
├── scripts/           # start/stop/dev helpers
├── docker-compose.yml # full stack
├── start.bat / start.sh
├── stop.bat / stop.sh
├── .env.example
└── README.md
```
