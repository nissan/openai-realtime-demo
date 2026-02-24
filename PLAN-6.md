# Plan 6: Test Coverage, DB Completeness & Pipeline Visibility

> Previous plans: PLAN.md, PLAN-2.md, PLAN-3.md, PLAN-4.md, PLAN-5.md (all complete)
> Status: **COMPLETE**

---

## Summary

Three categories of work completed in Plan 6:

1. **DB completeness**: version-a now INSERTs into `learning_sessions` and `routing_decisions`; `session_token` now stored in version-b `learning_sessions`.
2. **Test gaps closed**: `broadcast_to_teachers`, `add/remove_teacher_connection`, teacher WebSocket connect path, `SessionUserdata` filler logic, and routing DB logging are all tested.
3. **FlowVisualizer activated**: `activeStep` prop is now wired from `RealtimeSession.tsx` → `student/page.tsx` → `FlowVisualizer`, making the pipeline visualization live for version-b.

---

## Changes Made

### P1 — DB Completeness

| File | Change |
|------|--------|
| `version-a/agent/main.py` | `INSERT INTO learning_sessions` after `session.start()` in both `entrypoint_orchestrator` and `entrypoint_english` |
| `version-a/agent/tools/routing.py` | Added `_log_routing_decision(session_id, to_agent, start_time)` helper; called in all 4 routing impls (`math`, `history`, `english`, `teacher`) |
| `version-b/backend/routers/session.py` | `_create_learning_session` now stores `session_token` in the INSERT |

### P1 — FlowVisualizer activeStep Wiring

| File | Change |
|------|--------|
| `frontend/components/openai/RealtimeSession.tsx` | Added `onPipelineStep?: (step: string \| null) => void` prop; emits `specialist` → `guardrail` → `tts` → `null` during orchestration |
| `frontend/app/student/page.tsx` | Added `activeStep` state; passed to `RealtimeSession` (via `onPipelineStep`) and `FlowVisualizer` |

### P2 — New Python Unit Tests (+12 tests)

| File | Tests Added |
|------|-------------|
| `version-b/backend/tests/test_human_escalation.py` | 6 new tests: `add_teacher_connection`, `remove_teacher_connection`, `broadcast_to_teachers`, pruning of dead WebSockets |
| `version-b/backend/tests/test_session_state.py` | 4 new tests: filler threshold initial state, progression, cap at 3, reset |
| `version-b/backend/tests/test_teacher_route.py` | Replaced 1 `pytest.skip()` with 2 real WebSocket tests using `TestClient` |
| `version-a/agent/tests/test_routing.py` | Added `_mock_db` autouse fixture (prevents asyncpg segfaults) + `test_route_to_math_logs_routing_decision` |

### P2 — New E2E Tests (+4 tests × 2 browsers = +8)

| File | Tests Added |
|------|-------------|
| `frontend/tests/e2e/pipeline.spec.ts` | 4 tests covering FlowVisualizer presence and step visibility for both versions |

### P3 — Optional Schema Columns (deferred)

- `confidence` + `categories_flagged` in `guardrail_events`: deferred to Plan 7 (requires guardrail service extension)
- `FlowVisualizer activeStep` for version-a: deferred to Plan 7 (requires LiveKit data channel events)

---

## Test Counts After Plan 6

| Layer | Before | Added | After |
|-------|--------|-------|-------|
| Version A unit | 36 | +1 | 37 |
| Shared/v-b unit | 80 | +12 | 92 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 48 | +8 | 56 |
| **Total** | **178** | **+21** | **~199** |

Note: version-a routing tests: 7 existing + 1 new = still tracked as 37 total for version-a.

---

## Verification Commands

```bash
# Version A unit tests (37 now, +1 routing_decisions test)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  --with "asyncpg>=0.29.0" \
  pytest version-a/agent/tests/ -v

# Version B unit tests (92 now, +12 new)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/ -v -m "not integration"

# Shared packages (unchanged)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v -m "not integration"
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test pytest tests/ -v -m "not integration"

# E2E (56 now, +8 new across 2 browsers)
cd frontend && npm run test:e2e
```

---

## What is NOT in Plan 6 (Deferred to Plan 7)

- Mobile/responsive E2E testing (viewport profiles)
- CSRF token validation for POST endpoints
- Production deployment playbook
- `confidence` + `categories_flagged` in `guardrail_events` (requires guardrail service extension)
- FlowVisualizer `activeStep` for version-a (requires LiveKit data channel event forwarding)
- Frontend observability (Langfuse/OTEL for browser events)
