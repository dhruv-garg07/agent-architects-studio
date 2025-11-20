# Agent Architects Studio (The Manhattan Project)

The Manhattan Project is a full-stack AI agent marketplace that lets the community publish, discover, verify, and run autonomous agents. This repository is a monorepo that contains:

- A Vite + React + TypeScript frontend (the “Agent Architects Studio”) for discovery, leaderboards, and the creator studio.
- A Flask application (with a FastAPI reference) that renders the same experience for server-rendered deployments and exposes chat/RAG APIs.
- Supabase migrations, LLM orchestration, and Chroma-powered memory utilities.

👉 **Need a component-by-component walkthrough?** See [`agents.md`](agents.md).

## Highlights

- **Single source of truth** for agent/creator services shared between React, Flask, and FastAPI apps.
- **Supabase-first data layer** with migrations, row-level security, and generated TS/Pydantic types.
- **Integrated RAG loop**: Together AI streaming completions + LangChain memory + Chroma DB history/file stores.
- **Deployment ready** with `render.yaml`, `vercel.json`, and infrastructure-as-code friendly configs.

## Repository Layout

| Path | What lives here |
| --- | --- |
| `src/` | Vite/React UI, route components, layout shell, Supabase client + hooks, and the shared UI system (`components/ui`). |
| `api/` | Flask entry point (`index.py`), chat blueprint (`api_chats.py`), uploads, and templates wiring. |
| `backend_examples/python/` | FastAPI sample (`api/main.py`), Supabase service layer, and shared Pydantic models. |
| `LLM_calls/` | Together AI streaming client, context manager, and query rewriting helpers. |
| `Octave_mem/` | Chroma DB wrapper + controllers for chat/file memory. |
| `supabase/` | Database configuration and migrations for agents, creators, reviews, verification, and policies. |
| `templates/` | Jinja templates that mirror the React routes for the Flask deployment path. |
| `requirements.txt`, `package.json` | Python and Node dependency manifests. |

## Prerequisites

- Node.js 18+ (recommended 20 LTS) and npm (or pnpm/yarn if you prefer, but scripts are npm based).
- Python 3.10+ (3.11 used in Render config).
- Supabase project + CLI if you plan to run migrations locally.
- Access to a Together AI API key and Chroma DB instances if you want to run the chat endpoint end-to-end.

## Frontend (Vite + React) Setup

1. **Install deps**
   ```bash
   npm install
   ```
2. **Configure env**
   - Copy `.env.example` (create one if missing) to `.env.local`.
   - Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. Update `src/integrations/supabase/client.ts` to read from those envs before committing.
3. **Run the dev server**
   ```bash
   npm run dev
   ```
   The studio is now on `http://localhost:5173`.
4. **Production build**
   ```bash
   npm run build && npm run preview
   ```
5. **Linting**
   ```bash
   npm run lint
   ```

## Backend & Chat API Setup (Flask)

1. **Create a virtualenv**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. **Install requirements**
   ```bash
   pip install -r requirements.txt
   ```
3. **Env variables (`.env`)**
   ```env
   FLASK_ENV=development
   SECRET_KEY=change-me
   SUPABASE_URL=...
   SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_ROLE_KEY=...
   TOGETHER_API_KEY=...
   CHROMA_DATABASE_CHAT_HISTORY=/path/to/chroma/db
   CHROMA_DATABASE_FILE_DATA=/path/to/file/db
   SMTP_* (if you are sending emails)
   ```
4. **Run the Flask server**
   ```bash
   export FLASK_APP=api/index.py
   flask run --reload
   ```
5. **Chat endpoints**
   - Mounted at `/api/*` by `api/api_chats.py`.
   - Requires Chroma to be reachable and the Together AI key to be valid.
6. **FastAPI alternative**
   ```bash
   cd backend_examples/python
   uvicorn api.main:app --reload
   ```

## Supabase & Database

- Install the Supabase CLI and log in.
- Update `supabase/config.toml` with your project ref if needed.
- Apply migrations locally:
  ```bash
  supabase db reset   # destructive
  # or
  supabase migration up
  ```
- Key tables: `agent_profiles`, `user_profiles`, `agent_reviews`, `agent_comments`, `collaboration_requests`, `agent_changelog`, `agent_verifications`, and `user_roles`.
- Generated TypeScript types (`src/integrations/supabase/types.ts`) should be regenerated after schema changes to keep front-end typings honest. Use `supabase gen types typescript --linked` if you have the CLI configured.

## LLM, Memory & RAG Requirements

- **Together AI**: Set `TOGETHER_API_KEY` so `LLM_calls/together_get_response.py` can stream completions.
- **Chroma DB paths**: `CHROMA_DATABASE_CHAT_HISTORY` and `CHROMA_DATABASE_FILE_DATA` point to persistent vector stores. `Octave_mem/RAG_DB_CONTROLLER/*` and `api/api_chats.py` expect them to exist.
- **LangChain/LlamaIndex**: Installed via `requirements.txt` for orchestrating retrieval + memory summarization.

## Useful npm Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start Vite dev server. |
| `npm run build` | Production build (uses `vite build`). |
| `npm run build:dev` | Dev-mode build for staging preview. |
| `npm run preview` | Serve built assets locally. |
| `npm run lint` | Run ESLint across the repo. |

## Python Entry Points

| Command | Purpose |
| --- | --- |
| `flask run --app api.index --reload` | Serve the Flask UI/API locally. |
| `gunicorn api.index:app --workers 4 --bind 0.0.0.0:$PORT` | Production server command (see `render.yaml`). |
| `uvicorn backend_examples.python.api.main:app --reload` | Run the FastAPI example. |

## Onboarding Checklist for New Joiners

- [ ] Read [`agents.md`](agents.md) to understand each module’s role.
- [ ] Create Supabase credentials and update your `.env` + `supabase/config.toml`.
- [ ] Stand up the frontend (`npm run dev`) and verify you can hit Supabase locally.
- [ ] Run the Flask API + chat blueprint and confirm `/api/get_sessions` responds (requires Chroma + Together AI).
- [ ] Seed agent and creator data using Supabase SQL or the FastAPI routes.
- [ ] Review deployment manifests (`render.yaml`, `vercel.json`) if you will own hosting.

## Additional Documentation

- [`README_FLASK.md`](README_FLASK.md) &mdash; detailed walkthrough of the Flask-only implementation.
- [`agents.md`](agents.md) &mdash; “which file does what” index.
- Supabase SQL in `supabase/migrations/` &mdash; canonical schema definition.

Feel free to open an issue or drop a note in the project channel if anything here is unclear. Happy hacking!
