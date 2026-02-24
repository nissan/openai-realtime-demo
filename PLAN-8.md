# Plan 8: E2E Fix, Routing Confidence, datetime Deprecation & Audit Coverage

> Previous plans: PLAN.md → PLAN-7.md (all complete)
> Status: **COMPLETE**

---

## What Was Done

### Step 1 — Fix E2E Mobile Scope (P1) ✅

**File:** `frontend/playwright.config.ts`

Added `grep: /Mobile layout smoke tests/` to the `mobile-chrome` and `mobile-safari`
projects so they only run `mobile.spec.ts`. Without this filter, all 32 specs ran on
all 4 browsers (128 tests). With the filter: 32×2 desktop + 4×2 mobile = **72 E2E tests**.

### Step 2 — Fix `datetime.utcnow()` Deprecation (P2) ✅

Replaced all 17 occurrences across 6 source files + 2 test files:

| File | Fix |
|------|-----|
| `version-a/agent/tools/routing.py` | 5× `utcnow` → `now(timezone.utc)` |
| `version-b/backend/routers/orchestrator.py` | 2× `utcnow` + `from datetime import timezone` |
| `version-b/backend/models/job.py` | 4× `utcnow` + `default_factory=lambda: datetime.now(timezone.utc)` |
| `version-b/backend/services/job_store.py` | 1× `utcnow` + `timezone` import |
| `version-b/backend/tests/test_job_store.py` | 2× `utcnow` |
| `version-b/backend/tests/test_orchestrator_audit.py` | 1× `utcnow` |

The `default_factory=datetime.utcnow` (no parentheses) form in `job.py` required a
special fix: `default_factory=lambda: datetime.now(timezone.utc)`.

### Step 3 — Routing Confidence + Transcript Excerpt (P2) ✅

#### `shared/specialists/classifier.py`
- Added `RoutingResult` dataclass with `subject`, `confidence`, `raw_response` fields
- Updated `route_intent` return type from `SubjectRoute` (str) to `RoutingResult`
- Confidence scoring: `1.0`=exact word, `0.8`=partial match, `0.5`=fallback

#### `version-b/backend/routers/orchestrator.py`
- Updated `_run_orchestration` to use `routing = await route_intent(...)` and `routing.subject`
- Updated `_log_routing_decision` signature: added `confidence: float = 0.0` and
  `transcript_excerpt: str = ""` parameters
- Updated INSERT SQL to include `confidence` and `transcript_excerpt` columns
- Passed `routing.confidence` and `job.student_text[:200]` at call site

#### Test mock fixes (mock classifiers returning RoutingResult-like objects)
- `version-b/backend/tests/test_orchestrator_audit.py` — 2 mock classifiers updated
- `version-b/backend/tests/test_orchestrator_route.py` — 1 mock classifier updated;
  also added `_log_routing_decision` + `_log_guardrail_event` patches to prevent
  asyncpg segfault (known Python 3.13/macOS issue)

### Step 4 — Audit Test Coverage for New Columns (P2) ✅

#### `shared/specialists/tests/test_classifier.py`
- Updated 7 existing tests to use `result.subject` instead of `result == "string"`
- Added 3 new confidence tests:
  - `test_classify_exact_match_has_confidence_1` — exact response → 1.0
  - `test_classify_partial_match_has_confidence_0_8` — "I think math" → 0.8
  - `test_classify_unknown_falls_back_to_english_confidence_0_5` — nonsense → 0.5

#### `version-b/backend/tests/test_orchestrator_audit.py`
- `test_routing_decision_inserted_on_classification`: now asserts `confidence` and
  `transcript_excerpt` columns are in the SQL and bound params include `1.0` and excerpt
- `test_guardrail_event_inserted_when_flagged`: now passes `confidence=0.95` and
  `categories_flagged=["harassment"]`; asserts `len(args) == 7` (query + 6 params)

#### `shared/specialists/tests/integration/test_specialists_live.py`
- Updated 3 classify tests: `result.subject == "math"` + `result.confidence > 0.0`

### Step 5 — Update CLAUDE.md + Create PLAN-8.md (P3) ✅

CLAUDE.md updated with Plan 8 test counts (72 E2E, 211 total, 27 shared unit).

---

## Final Test Counts

| Layer | Before | Delta | After |
|-------|--------|-------|-------|
| Version A unit | 46 | 0 | 46 |
| Shared unit | 24 | +3 | 27 |
| Version B unit | 52 | 0 | 52 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 128 (bug) | −56 (scope fix) | 72 |
| **Total** | **~223** | | **~211** |

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/playwright.config.ts` | Added `grep` to mobile projects |
| `CLAUDE.md` | Updated E2E count (72) and total (~211) |
| `version-a/agent/tools/routing.py` | 5× `utcnow` → `now(timezone.utc)` |
| `version-b/backend/routers/orchestrator.py` | `utcnow` fix + `RoutingResult` usage + `_log_routing_decision` expanded |
| `version-b/backend/models/job.py` | 4× `utcnow` + lambda default_factory |
| `version-b/backend/services/job_store.py` | 1× `utcnow` |
| `version-b/backend/tests/test_job_store.py` | 2× `utcnow` |
| `version-b/backend/tests/test_orchestrator_audit.py` | `utcnow` + column value assertions + mock RoutingResult |
| `version-b/backend/tests/test_orchestrator_route.py` | Mock RoutingResult + asyncpg patch |
| `shared/specialists/classifier.py` | Added `RoutingResult`, updated `route_intent` return type |
| `shared/specialists/tests/test_classifier.py` | Updated 7 tests + added 3 confidence tests |
| `shared/specialists/tests/integration/test_specialists_live.py` | Updated 3 classify tests |
| `PLAN-8.md` | **Created** (this file) |

---

## Deferred to Plan 9

- **FlowVisualizer `activeStep` for version-a** — requires LiveKit data channel emit
- **CSRF token validation + rate limiting** — production security concern
- **Frontend observability (Langfuse SDK in browser)**
- **PaaS deployment configs**
