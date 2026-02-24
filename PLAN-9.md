# Plan 9: CI Pipeline, Rate Limiting & FlowVisualizer Version-A

> Previous plans: PLAN.md → PLAN-8.md (all complete, 211 tests all green)
> Status: **COMPLETE**

---

## Summary

This plan addressed four deferred items from Plan 8:

- **P1a** — Documented `npx playwright install` in `CLAUDE.md` Frontend commands to prevent WebKit-missing errors for new devs/CI runners.
- **P1b** — Created `.github/workflows/ci.yml` with two jobs (`unit-tests`, `e2e-tests`) running on push/PR to `main`.
- **P2a** — Added `slowapi>=0.1.9` rate limiting to `POST /orchestrate`: 20 req/min per IP. Wired in `main.py`, decorated in `orchestrator.py`. 2 new tests verify the limiter is active.
- **P2b** — Wired `FlowVisualizer.activeStep` for Version-A: agent emits JSON via LiveKit data channel (`topic="pipeline-steps"`), `StudentRoom` subscribes via `useDataChannel`, `StudentPage` passes `onPipelineStep` to both `StudentRoom` and `RealtimeSession`.

---

## Files Changed

| File | Change |
|------|--------|
| `CLAUDE.md` | Added `npx playwright install` to Frontend commands; updated test counts to Plan 9 figures |
| `.github/workflows/ci.yml` | **Created** — unit-tests + e2e-tests jobs |
| `version-b/backend/pyproject.toml` | Added `slowapi>=0.1.9` |
| `version-b/backend/main.py` | Wired `Limiter`, `RateLimitExceeded` exception handler |
| `version-b/backend/routers/orchestrator.py` | Added `Request` param + `@limiter.limit("20/minute")` to `dispatch_orchestration` |
| `version-b/backend/tests/test_rate_limiting.py` | **Created** — 2 tests: 200 under limit, rate-limit headers present |
| `version-a/agent/tools/routing.py` | Added `_emit_pipeline_step`; emit `orchestrator`/`specialist` in 3 routing fns; emit `orchestrator`+`null` in escalate |
| `version-a/agent/agents/base.py` | Added `_emit_step`; emit `guardrail` at tts_node entry, `tts` at first safe sentence, `null` at generator end |
| `frontend/components/livekit/StudentRoom.tsx` | Added `onPipelineStep` prop + `useDataChannel("pipeline-steps", ...)` in `ConnectionGuard` |
| `frontend/app/student/page.tsx` | Wired `onPipelineStep={(step) => setActiveStep(step ?? undefined)}` to `StudentRoom` |
| `version-a/agent/tests/test_routing.py` | Added `room.local_participant.publish_data` mock to `session` fixture; +3 tests for emit assertions |
| `PLAN-9.md` | **Created** this file |

---

## Test Counts After Plan 9

| Layer | Before | Delta | After |
|-------|--------|-------|-------|
| Version A unit | 46 | +3 | 49 |
| Shared unit | 27 | 0 | 27 |
| Version B unit | 52 | +2 | 54 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 72 | 0 | 72 |
| **Total** | **211** | **+5** | **~216** |

---

## Verification Commands

```bash
# Version A unit tests (expect 49)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  --with "asyncpg>=0.29.0" \
  pytest version-a/agent/tests/ -v

# Version B unit tests (expect 54)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/ -v -m "not integration"

# Rate limit smoke test (after docker compose up)
for i in $(seq 1 22); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/orchestrate \
    -H "Content-Type: application/json" \
    -d '{"session_id":"test","student_text":"test"}'; done
# First 20 → 200, last 2 → 429
```

---

## What Is NOT in Plan 9 (Deferred to Plan 10)

- **CSRF protection** — requires session cookie/token pattern; beyond POC scope
- **Frontend Langfuse observability** — major dep + cross-origin OTEL
- **PaaS deployment configs** (Render/Railway/Fly) — outside POC scope
- **FlowVisualizer E2E test for step highlighting** — requires running full agent stack
