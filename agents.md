# Agents & Responsibilities

This document maps the major “agents” (modules, services, and flows) that live in this repository and explains what each of them is responsible for. Use it as a companion to `README.md` when you need to understand how work is split across the frontend, backend, data, and memory layers.

## Platform Map

```
┌─────────────────────┐       ┌────────────────────────┐        ┌──────────────────────┐
│ React + Vite client │ <---> │ Supabase (auth + data) │ <----> │ Flask / FastAPI APIs │
└─────────────────────┘       └────────────────────────┘        └──────────────────────┘
          │                             │                                    │
          ▼                             ▼                                    ▼
   UI “agents” in `src/`     SQL + policies in `supabase/`      RAG + LLM orchestration (`LLM_calls/`, `Octave_mem/`)
```

## Frontend Discovery & Studio Agents (`src/`)

| Agent | Path | Responsibilities | Upstream | Downstream |
| --- | --- | --- | --- | --- |
| **App Router** | `src/App.tsx` | Boots React Router + React Query; wires all feature routes together inside the shared layout. | N/A | Every route component via `<Routes>` |
| **Shell/Layout** | `src/components/Layout.tsx` | Global nav, footer, responsive chrome, and outlet host; centralizes navigation links, CTA buttons, and mobile menu. | React Router navigation primitives | Routed pages receive layout wrappers |
| **Homepage** | `src/pages/Homepage.tsx` | Marketing hero, featured agent cards, and why-us sections used for first‑time visitors. | Uses static `heroImage` asset | Links users into `/explore` & `/submit` |
| **Explore** | `src/pages/Explore.tsx` + `src/components/SearchAndFilters.tsx` | Rich agent browser with filters, query sorting, status chips, and Supabase powered data fetch. Maintains `filters` state, orchestrates search, attaches toast errors. | Supabase JS client, `useToast` | Agents list UI, `SearchAndFilters` |
| **Agent Detail** | `src/pages/AgentDetail.tsx` | Deep profile page for one agent. Currently uses mock data but shows how runtime cards, documentation tabs, and run panel fit together. | Local React state for run simulation | Buttons for share, run, etc. |
| **Creator Studio** | `src/pages/CreatorStudio.tsx` | Multi-tab workspace for creators: overview dashboard, agent list, foundry, analytics, and admin-only verification tab. Handles CRUD via `lib/api/agents`. | Supabase auth session, hooks, `getUserAgents`, `createAgent`, `updateAgent`, `deleteAgent`, `useToast` | Writes to Supabase `agent_profiles`, drives `AgentVerification` |
| **Agent Verification** | `src/components/AgentVerification.tsx` | Admin-only workflow that pulls pending agents (`status = pending_review`) and lets reviewers approve or reject them while leaving notes. | Supabase JS client; `useToast` | Updates `agent_profiles.status` |
| **Leaderboard** | `src/pages/Leaderboard.tsx` | Pulls top agents and creators via `getTopAgents`/`getTopCreators` with squads/tabs for trending content. | `lib/api/agents.ts` wrappers | UI cards + CTA to studio |
| **Creators Directory** | `src/pages/Creators.tsx` | Filters/sorts creators, mirrors backend creator service logic, and highlights community stats. | Supabase or future API (currently static) | UI badges, CTA buttons |
| **Auth** | `src/pages/Auth.tsx` | Handles email/password sign-in & sign-up flows through Supabase Auth, redirects signed-in users, surfaces toast feedback. | Supabase client, router navigation | Updates Supabase session; redirects to `/` |
| **Leaderboard & Misc pages** | `src/pages/Leaderboard.tsx`, `src/pages/NotFound.tsx`, etc. | Provide specialized experiences (leaderboard, fallback 404). | Shared UI system (`src/components/ui`) | Present data & call-to-actions |
| **UI System** | `src/components/ui/*` | Shadcn-derived primitives (Button, Card, Tabs, etc.) themed for the studio. | Radix UI, Tailwind CSS | Every page/component |

## Client Data & Integration Agents

| Module | Path | Description |
| --- | --- | --- |
| Supabase client | `src/integrations/supabase/client.ts` | Centralized Supabase JS client with URL + anon key (replace with env vars in prod). Handles auth session persistence. |
| Supabase types | `src/integrations/supabase/types.ts` | Generated TypeScript types for the `agent_profiles`, `agent_reviews`, `user_profiles`, etc. tables to keep inserts/updates type-safe. |
| Agent API wrappers | `src/lib/api/agents.ts` | Promise helpers around Supabase queries (`getUserAgents`, `createAgent`, `updateAgent`, `deleteAgent`, `getTopAgents`, `getTopCreators`). Used across pages for consistent error handling and ordering. |
| Utilities | `src/lib/utils.ts`, `src/hooks/*` | Handful of helpers (`cn`, `useMobile`, `useToast`) that give ergonomic primitives to page-level agents. |

## Backend & API Agents

| Agent | Path | Responsibilities | Notes |
| --- | --- | --- | --- |
| **Flask Web App** | `api/index.py` | Production Python backend driving Jinja templates (`templates/`), Supabase-powered routes (`/explore`, `/agent/<id>`, `/creators`, `/submit`), authentication via Flask-Login, email notifications, and integration with `backend_examples`. | Deploy via Render (`render.yaml`) or Vercel (`vercel.json`). Requires `.env` with Supabase URL/keys + SMTP secrets. |
| **Chat + Memory API** | `api/api_chats.py` | Blueprint exposing session CRUD endpoints (`/api/get_sessions`, `/api/create_session`, `/api/sessions/<id>/messages`, `/api/messages`, `/api/chat`). Pipes content through the RAG pipeline and Together AI model via `LLM_calls`. | Depends on `Octave_mem` controllers (Chroma DB) and rewrites queries before retrieval. |
| **FastAPI reference** | `backend_examples/python/api/main.py` | Alternative backend implementing the same agent/creator endpoints via FastAPI for teams that prefer async services. Useful for serverless deployments or testing. |
| **Service layer** | `backend_examples/python/services/{agents,creators}.py` | Encapsulates Supabase CRUD for agents/creators. Shared by Flask templates, FastAPI routes, and any scripts. |
| **Data models** | `backend_examples/python/models.py` | Pydantic models mirroring the TypeScript interfaces (agents, creators, stats, filters). Ensures consistent serialization between tiers. |

## RAG, LLM, and Memory Agents

| Agent | Path | Role |
| --- | --- | --- |
| LLM orchestration | `LLM_calls/context_manager.py`, `LLM_calls/together_get_response.py`, `LLM_calls/intelligent_query_rewritten.py` | Streams Together AI responses (DeepSeek R1 Distill), manages conversation memory (LangChain `ConversationBufferMemory`), and rewrites prompts before hitting models. |
| Vector stores | `Octave_mem/RAG_DB/*`, `Octave_mem/RAG_DB_CONTROLLER/*` | Wrap Chroma DB collections for chat history (`CHAT_HISTORY`) and uploaded files (`FILE_DATA`). Provides read/write controllers used by the chat API. |
| Utilities | `utlis/utlis_functions.py`, `utlis/task_dispatcher.py` | Helper functions to extract code/JSON from model responses and (future) background task dispatcher logic. |

## Database & Infrastructure Agents

| Component | Path | Description |
| --- | --- | --- |
| Supabase migrations | `supabase/migrations/*.sql` | Defines `agent_profiles`, `user_profiles`, reviews, comments, collaboration requests, changelog tables, plus admin verification workflow (`agent_verifications`, `user_roles`) and triggers to keep ratings/status in sync. |
| Supabase config | `supabase/config.toml` | CLI configuration for targeting the right Supabase project. |
| Deployment manifests | `render.yaml`, `vercel.json` | Ready-to-use deployment descriptors for Render (Gunicorn + Flask) and Vercel (Python serverless functions). |
| Node tooling | `package.json`, `vite.config.ts`, `tailwind.config.ts` | Frontend build, linting, and theming configuration. |
| Python deps | `requirements.txt`, `backend_examples/python/requirements.txt` | Dependency pins for the Flask app, RAG controllers, LangChain, and Supabase client. |

## Templates & Static Assets

- `templates/` contains every Jinja template used by the Flask front-end (mirrors the React routes: `homepage.html`, `explore.html`, `agent_detail.html`, etc.) plus shared `base.html` and `styles.css`.
- `public/`, `src/assets/`, and `index.html` host the static assets for the Vite build.

## Extending or Adding New Agents

1. **Decide where the logic belongs.** Presentation-only features go under `src/pages` or `templates/`. Anything involving Supabase/LLM writes usually needs a companion change under `backend_examples` or `Octave_mem`.
2. **Reuse the service layer.** Add new helpers to `src/lib/api/agents.ts` and the Python services simultaneously so both React and Flask clients stay consistent.
3. **Respect database contracts.** Update SQL migrations plus `src/integrations/supabase/types.ts` when you touch tables; regenerate types to keep TS + Python models aligned.
4. **Document the agent.** When you create a new module, add a short note here (and reference it from `README.md`) so future contributors can find it quickly.
