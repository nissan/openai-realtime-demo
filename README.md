# Voice AI Tutor — OpenAI Realtime Demo

A POC comparing two architectures for voice AI tutoring:
- **Version A** — LiveKit Agents pipeline (STT → LLM → guardrail → TTS)
- **Version B** — OpenAI Realtime Direct (WebRTC session, native TTS)

Both versions share the same frontend, database, and specialist LLMs; only the
voice pipeline differs. The app displays a `TradeoffPanel` when an architectural
difference is triggered, making the comparison explicit.

---

## Architecture

```
shared/             Python packages shared by both backends
  guardrail/        OpenAI moderation + sentence-buffered rewrite
  observability/    OTEL + Langfuse HTTP/protobuf setup
  specialists/      Classifier (Haiku), Math (Sonnet 4.6), History (GPT-4o), English (GPT-4o)

version-a/agent/    LiveKit Agents worker
  agents/           GuardedAgent base, OrchestratorAgent, MathAgent, HistoryAgent, EnglishAgent
  services/         transcript_store, session management

version-b/backend/  FastAPI backend (no LiveKit)
  routers/          /orchestrate, /tts/stream, /teacher WebSocket
  models/           OrchestratorJob, SessionUserdata
  services/         job_store, transcript_store

frontend/           Next.js 14 app (?v=a or ?v=b URL param)
  components/       LiveKit room, Realtime session, FlowVisualizer, TradeoffPanel

db/migrations/      Shared Postgres schema + Version B jobs table

.github/workflows/ci.yml    GitHub Actions: unit-tests + e2e-tests on push/PR to main
                             POST /orchestrate: 20 req/min per-IP rate limit (slowapi)
```

See [PLAN.md](PLAN.md) through [PLAN-12.md](PLAN-12.md) for detailed decision history.

---

## Subjects

| Subject  | Specialist LLM        | Notes |
|----------|-----------------------|-------|
| Math     | Claude Sonnet 4.6     | `shared/specialists/math.py` |
| History  | GPT-4o                | `shared/specialists/history.py` |
| English  | OpenAI Realtime native| Version A: separate session; Version B: same session |
| Routing  | Claude Haiku          | `shared/specialists/classifier.py`, temperature=0.1 |

---

## Version Differences (TradeoffPanel triggers)

| # | Trigger | Version A | Version B |
|---|---------|-----------|-----------|
| 1 | English question | Spins up separate Realtime AgentSession | Keeps same Realtime agent |
| 2 | Guardrail | Pre-TTS in `GuardedAgent.tts_node` | Pre-TTS in `/tts/stream` |
| 3 | Filler words | Orchestrator speaks filler | Realtime speaks at 500ms/1500ms/3000ms |
| 4 | Teacher mode | LiveKit room (audio + video) | WebSocket (transcript + text) |
| 5 | Barge-in | Pipeline flush | Realtime cancels response |

---

## Prerequisites

- Docker Desktop 4.x (for all 20 services)
- Node.js 20+
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager (`pip install uv`)
- API keys:
  - `OPENAI_API_KEY` (for GPT-4o specialists + moderation + Realtime)
  - `ANTHROPIC_API_KEY` (for Claude Sonnet 4.6 math + Haiku classifier)
  - `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET` (for Version A)
- Optional:
  - `CSRF_SECRET` — 32-byte hex string for HMAC token signing. Defaults to a random
    secret at startup (safe for dev; set explicitly in production so tokens survive restarts)

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/nissan/openai-realtime-demo
cd openai-realtime-demo

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env with your API keys

# 3. Start all 20 services
docker compose up -d
docker compose ps   # verify all services healthy

# 4. Open the app
open http://localhost:3000
```

### Verify services

```bash
curl http://localhost:3001/api/public/health   # Langfuse
open http://localhost:54323                     # Supabase Studio
```

---

## Running Tests

### Unit tests (no API keys required)

```bash
# Shared packages
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test \
  pytest tests/ -v -m "not integration"
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test \
  pytest tests/ -v -m "not integration"

# Version A — 49 tests
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  --with "asyncpg>=0.29.0" \
  pytest version-a/agent/tests/ -v

# Version B — 64 tests
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/ -v -m "not integration"
```

### Integration tests (requires real API keys)

```bash
set -a && source .env && set +a

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/integration/ -v -s -m integration
```

### Playwright E2E tests

```bash
cd frontend
npm install
npm run test:e2e   # 82 tests: 35 chromium + 35 firefox + 4 mobile-chrome + 4 mobile-safari + 4 observability
```

### Total test counts (Plan 12)

| Layer | Count |
|-------|-------|
| Version A unit | 49 |
| Shared unit (guardrail + specialists) | 27 |
| Version B unit | 64 |
| Python integration | 14 |
| Playwright E2E | 82 |
| **Total** | **236** |

---

## Plans

This project was built incrementally across 10 plans:

- [PLAN.md](PLAN.md) — Initial architecture + 20-service Docker setup
- [PLAN-2.md](PLAN-2.md) — Shared packages (guardrail, observability, specialists)
- [PLAN-3.md](PLAN-3.md) — Version A LiveKit agents + Version B FastAPI backend
- [PLAN-4.md](PLAN-4.md) — Frontend (Next.js 14, LiveKit room, Realtime session)
- [PLAN-5.md](PLAN-5.md) — TradeoffPanel, FlowVisualizer, audit trail, teacher WebSocket
- [PLAN-6.md](PLAN-6.md) — Human escalation, session state, E2E pipeline tests
- [PLAN-7.md](PLAN-7.md) — Guardrail DB completeness, agent test coverage, mobile E2E
- [PLAN-8.md](PLAN-8.md) — RoutingResult confidence, FlowVisualizer version-b wiring, mobile E2E
- [PLAN-9.md](PLAN-9.md) — CI pipeline, rate limiting on /orchestrate, FlowVisualizer version-a wiring
- [PLAN-10.md](PLAN-10.md) — FlowVisualizer E2E highlighting tests, README & housekeeping
- [PLAN-11.md](PLAN-11.md) — CSRF protection (stateless HMAC) + frontend Langfuse observability via `/events` proxy
- [PLAN-12.md](PLAN-12.md) — Rate limiting on /tts/stream + /escalate, agent healthchecks, .env.example CSRF_SECRET
