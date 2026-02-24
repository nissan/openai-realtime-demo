# Plan 7: Guardrail DB Completeness, Agent Test Coverage, Mobile E2E & Deployment Readiness

> Previous plans: PLAN.md → PLAN-6.md (all complete)
> Status: **COMPLETE**

---

## What Was Implemented

### Step 1 — CLAUDE.md Test Count Fix

Corrected version-b unit count (56 → 49 → 52 after Plan-7 additions) and updated
all test count entries to reflect Plan-7 final state.

### Step 2 — Guardrail DB Completeness

#### 2a. version-b: `confidence` + `categories_flagged` columns populated

**File:** `version-b/backend/routers/orchestrator.py`

- Updated `_log_guardrail_event` signature to accept `confidence: float = 0.0` and
  `categories_flagged: list[str] | None = None`
- Updated INSERT to include both new columns
- In `_run_orchestration`: when `safe_text != raw_text` (i.e., content was flagged),
  calls `guardrail.service.check()` on `raw_text` to retrieve confidence/categories,
  then passes them to `_log_guardrail_event`. Best-effort: wrapped in try/except.

#### 2b. version-a: `guardrail_events` INSERT in `GuardedAgent._guardrail_text`

**File:** `version-a/agent/agents/base.py`

- After every `check_and_rewrite()` call, attempts to INSERT into `guardrail_events`
  including `session_id`, `original_text`, `rewritten_text`, `flagged`, `confidence`,
  `categories_flagged`
- Session ID extracted via `self.session.userdata.session_id` when available
- Double-wrapped in try/except — inner for DB errors, outer for guardrail import errors
- Never breaks the TTS pipeline

### Step 3 — Missing Version-A Agent Unit Tests

Created 3 new test files, each with 3 tests:

| File | Tests |
|------|-------|
| `version-a/agent/tests/test_math_agent.py` | instantiation, system prompt, back-routing only |
| `version-a/agent/tests/test_history_agent.py` | instantiation, system prompt, back-routing only |
| `version-a/agent/tests/test_english_agent.py` | instantiation, system prompt, back-routing only |

All use `object.__new__()` to bypass LiveKit runtime and `monkeypatch.setitem` to mock
livekit modules. Tests verify the critical architectural constraint: no spec-to-spec routing.

### Step 4 — Version-B `_get_specialist_stream` Tests

Extended `version-b/backend/tests/test_orchestrator_route.py` with 3 new tests:

- `test_get_specialist_stream_routes_math` — math subject dispatches to math specialist
- `test_get_specialist_stream_routes_history` — history subject dispatches to history specialist
- `test_get_specialist_stream_escalate_returns_escalation_text` — escalate returns human handoff message

Uses `patch.dict(sys.modules, {...})` pattern to inject mock specialist modules without
requiring anthropic/openai in the test environment.

### Step 5 — Mobile E2E Coverage

**File:** `frontend/playwright.config.ts`
- Added `mobile-chrome` project: `devices["Pixel 5"]`
- Added `mobile-safari` project: `devices["iPhone 13"]`

**File:** `frontend/tests/e2e/mobile.spec.ts` (new)
- 4 smoke tests: landing page, version-a student, version-b student, suggested questions
- Tests use text and testids that exist in the actual components
- 4 tests × 2 mobile browsers = 8 new E2E tests

### Step 6 — README.md

Created `README.md` at project root with:
- Overview and architecture diagram
- Subject/LLM mapping table
- Version differences (TradeoffPanel triggers)
- Prerequisites (Docker, Node, Python, uv, API keys)
- Quick Start commands
- Full test command reference with counts
- Plans reference (PLAN.md → PLAN-7.md)

---

## Final Test Counts (Plan 7)

| Layer | Before Plan 7 | Added | After Plan 7 |
|-------|--------------|-------|-------------|
| Version A unit | 37 | +9 (3 agent files × 3 tests) | 46 |
| Shared unit | 24 | 0 | 24 |
| Version B unit | 49 | +3 (_get_specialist_stream) | 52 |
| Python integration | 14 | 0 (verified existing) | 14 |
| Playwright E2E | 56 | +8 (mobile) | 64 |
| **Total** | **~193** | **+20** | **~213** |

---

## Files Modified

| File | Change |
|------|--------|
| `CLAUDE.md` | Updated test counts to Plan-7 state |
| `version-b/backend/routers/orchestrator.py` | `_log_guardrail_event` now includes confidence + categories_flagged |
| `version-a/agent/agents/base.py` | `_guardrail_text` now inserts into guardrail_events table |
| `version-a/agent/tests/test_math_agent.py` | **Created** (3 tests) |
| `version-a/agent/tests/test_history_agent.py` | **Created** (3 tests) |
| `version-a/agent/tests/test_english_agent.py` | **Created** (3 tests) |
| `version-b/backend/tests/test_orchestrator_route.py` | Extended (+3 specialist routing tests) |
| `frontend/playwright.config.ts` | Added Pixel 5 + iPhone 13 device projects |
| `frontend/tests/e2e/mobile.spec.ts` | **Created** (4 tests × 2 browsers = 8) |
| `README.md` | **Created** at project root |
| `PLAN-7.md` | **Created** (this file) |

---

## What Is NOT in Plan 7 (Deferred to Plan 8)

- FlowVisualizer `activeStep` for version-a (requires LiveKit data channel emit)
- CSRF token validation + rate limiting
- Frontend observability / Langfuse SDK in browser
- `routing_decisions.confidence` + `transcript_excerpt` (requires classifier API change)
- PaaS deployment configs (Render/Railway/Fly)
- Full integration test verification with real API keys
