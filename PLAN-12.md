# Plan 12: Rate Limiting, Agent Healthchecks, .env.example, and Langfuse Smoke Test

> Previous plans: PLAN.md → PLAN-11.md (all complete, 234 tests all green)
> Status: **COMPLETE**

---

## Context

Plan 11 completed CSRF protection and frontend observability. Four housekeeping items
remain before the POC is fully production-ready:

1. **Rate limiting on remaining endpoints** — `/tts/stream` and `/escalate` are
   mutating POST endpoints with no per-IP rate limit, unlike `/orchestrate` (20/min).
2. **Agent healthchecks** — `agent-a` and `agent-a-english` have no `healthcheck:` block
   in docker-compose.yml; Docker marks them as "(no healthcheck)", making it impossible
   to express service dependencies reliably. A tiny stdlib HTTP server (port 8080) on a
   daemon thread solves this with zero new deps.
3. **`.env.example` update** — `CSRF_SECRET` was added in Plan 11 but was absent from
   `.env.example`, making it invisible to new contributors.
4. **Langfuse trace verification** — Smoke-test commands to verify traces end-to-end.

---

## Part A: Rate Limiting on /tts/stream and /escalate

### Pattern (from orchestrator.py)

Each router creates its own `Limiter` instance. `app.state.limiter` (from main.py) is
used only for the 429 exception handler. `request: Request` MUST be the first positional
parameter for slowapi to extract the client IP.

### Changes Made

- **`version-b/backend/routers/tts.py`** — Added `limiter = Limiter(key_func=get_remote_address)`
  and `@limiter.limit("30/minute")` on `POST /tts/stream`. Added `request: Request` as
  first positional param.
- **`version-b/backend/routers/teacher.py`** — Added `limiter = Limiter(key_func=get_remote_address)`
  and `@limiter.limit("10/minute")` on `POST /escalate`. Added `request: Request` as
  first positional param.
- **`version-b/backend/tests/test_rate_limiting.py`** — Added 2 tests verifying the
  rate limiter doesn't block single requests to `/tts/stream` and `/escalate`.

### Rate Limits

| Endpoint | Limit | Rationale |
|----------|-------|-----------|
| `POST /orchestrate` | 20/min | CPU-bound LLM + guardrail |
| `POST /tts/stream` | 30/min | I/O-bound TTS streaming |
| `POST /escalate` | 10/min | Human escalation is rare |

---

## Part B: Agent Healthchecks (stdlib HTTP server)

### Design

`cli.run_app()` blocks the main thread forever. A daemon `threading.Thread` running a
stdlib `http.server.HTTPServer` on port 8080 starts before `cli.run_app()` and survives
as long as the process lives. Docker's `curl`-based healthcheck confirms liveness.

`start_period: 60s` is critical — LiveKit agent workers download the Silero VAD model
on first start (10–30s) before the agent loop begins.

### Changes Made

- **`version-a/agent/main.py`** — Added `_HealthHandler` (silenced access log),
  `_start_health_server()` (daemon thread on port 8080). Called just before
  `cli.run_app(...)` in `__main__`.
- **`docker-compose.yml`** — Added `healthcheck:` blocks to `agent-a` and
  `agent-a-english`:
  ```yaml
  healthcheck:
    test: ["CMD-SHELL", "curl -sf http://127.0.0.1:8080/ || exit 1"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 60s
  ```

---

## Part C: .env.example Update

Added `CSRF_SECRET=` with a comment explaining how to generate the value:

```bash
# Security (Version B)
# CSRF_SECRET: 32-byte hex string for HMAC token signing.
# Defaults to a random secret at startup (safe for dev; set in production
# so tokens survive restarts and horizontal scaling).
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
CSRF_SECRET=
```

---

## Part D: Langfuse Trace Verification (Smoke Tests)

No code changes. Commands to verify the OTEL → Langfuse pipeline end-to-end:

```bash
# 1. Check Langfuse is healthy
curl http://localhost:3001/api/public/health

# 2. Send a test frontend event via /events
curl -s -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke-test","event_name":"smoke.test","attributes":{"env":"local"}}' | jq .
# Expected: {"ok": true}

# 3. Verify trace appears in Langfuse UI
open http://localhost:3001
# Navigate to Traces → search for "frontend.smoke.test"

# 4. Get a CSRF token and fire a rate-limited request
TOKEN=$(curl -s http://localhost:8001/csrf/token | jq -r .token)
curl -s -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $TOKEN" \
  -d '{"session_id":"smoke-test","student_text":"What is 2+2?"}' | jq .
# Expected: {"job_id": "..."}
```

---

## Files Modified

| File | Change |
|------|--------|
| `version-b/backend/routers/tts.py` | Added `Limiter`, `Request` param, `@limiter.limit("30/minute")` |
| `version-b/backend/routers/teacher.py` | Added `Limiter`, `Request` param, `@limiter.limit("10/minute")` on `/escalate` |
| `version-b/backend/tests/test_rate_limiting.py` | Added 2 tests for tts + escalate endpoints |
| `version-a/agent/main.py` | Added `_HealthHandler`, `_start_health_server()`, call before `cli.run_app()` |
| `docker-compose.yml` | Added `healthcheck:` blocks to `agent-a` and `agent-a-english` |
| `.env.example` | Added `CSRF_SECRET=` with comment |
| `PLAN-12.md` | This file |
| `CLAUDE.md` | Updated test counts (Version B: 62→64, total: 234→236) |
| `README.md` | Updated test counts (Version B: 62→64, total: 234→236) |

---

## Test Counts After Plan 12

| Layer | Before | Delta | After |
|-------|--------|-------|-------|
| Version A unit | 49 | 0 | 49 |
| Shared unit | 27 | 0 | 27 |
| Version B unit | 62 | +2 | 64 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 82 | 0 | 82 |
| **Total** | **234** | **+2** | **236** |

---

## Verification

```bash
# 1. Version B unit tests — expect 64 total
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/ -v -m "not integration"

# 2. Version A unit tests — expect 49 (unchanged)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  --with "asyncpg>=0.29.0" \
  pytest version-a/agent/tests/ -v

# 3. Fresh Docker rebuild to confirm healthchecks work
docker compose down
docker compose build --no-cache agent-a agent-a-english
docker compose up -d agent-a agent-a-english
docker compose ps   # agent-a and agent-a-english should show healthy after ~90s

# 4. Langfuse smoke test (with docker-compose running)
curl http://localhost:3001/api/public/health
curl -s -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{"session_id":"smoke","event_name":"smoke.test","attributes":{}}' | jq .
```

---

## Key Constraints / Gotchas

- **`request: Request` MUST be first positional param** for slowapi to extract the IP.
  Body model (`TtsStreamRequest`, `EscalationRequest`) comes after.
- **Each router creates its own `Limiter`** — slowapi supports multiple Limiter instances;
  `app.state.limiter` (from main.py) is only used for the 429 exception handler.
- **`start_period: 60s`** prevents Docker from marking agents unhealthy during Silero
  VAD model download and LiveKit connection (can take 30–60s on cold start).
- **`daemon=True`** on the health server thread means it exits automatically when the
  main LiveKit agent process exits — no cleanup needed.
- **`log_message` override** silences the 30-second GET / log spam in container logs.
- **`.env.example` CSRF_SECRET left empty** — committing a real value would expose a
  secret in git. Users generate with:
  `python -c "import secrets; print(secrets.token_hex(32))"`
