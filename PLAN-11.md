# Plan 11: CSRF Protection + Frontend Langfuse Observability

> Status: **COMPLETE** — All tests green (62 unit + 14 integration + 82 E2E = 234 total)
> Implemented: 2026-02-24

---

## Summary

Two features added to the Version B backend and frontend:

### Part A: CSRF Protection
Stateless double-submit HMAC token (stdlib only, no new deps), verified via FastAPI `Depends` on all mutating POST endpoints.

- `GET /csrf/token` → `{token: "{expire}:{hmac_sha256}", ttl: 300}`
- Frontend stores token in JS memory, attaches as `X-CSRF-Token` header
- Backend verifies signature + TTL; `hmac.compare_digest()` prevents timing attacks
- 5-minute TTL; frontend refreshes at 240s (80% of TTL)

**Protected endpoints:**
- `POST /orchestrate`
- `POST /orchestrate/{job_id}/wait`
- `POST /tts/stream`
- `POST /escalate`

**Exempt:**
- `GET /csrf/token` (read-only)
- `POST /events` (append-only observability, no state mutation)
- WebSocket endpoints (browsers cannot send custom headers on WS upgrades)

### Part B: Frontend Langfuse Observability (Backend Proxy)
Fire-and-forget pattern: frontend fires events to `POST /events`, backend creates OTEL spans into the existing Langfuse pipeline.

- Zero npm deps in frontend — uses `fetch()` only
- `BackgroundTasks` ensures events never block the request
- Errors in OTEL never propagate to the browser

**Events emitted:**
- `page.loaded` — on student page mount
- `pipeline.step` — each time the active pipeline step changes
- `question.selected` — when user clicks a suggested question

---

## Files Modified / Created

| File | Change |
|------|--------|
| `version-b/backend/routers/csrf.py` | **NEW** — HMAC token generation, `require_csrf` dependency, `GET /csrf/token` |
| `version-b/backend/routers/events.py` | **NEW** — `POST /events` proxy to OTEL |
| `version-b/backend/main.py` | Include `csrf` + `events` routers |
| `version-b/backend/routers/orchestrator.py` | Add `Depends(require_csrf)` to 2 POST routes |
| `version-b/backend/routers/tts.py` | Add `Depends(require_csrf)` |
| `version-b/backend/routers/teacher.py` | Add `Depends(require_csrf)` to `POST /escalate` |
| `version-b/backend/tests/conftest.py` | **NEW** — global CSRF bypass for all unit tests |
| `version-b/backend/tests/test_csrf.py` | **NEW** — 5 CSRF unit tests |
| `version-b/backend/tests/test_events.py` | **NEW** — 3 events route unit tests |
| `frontend/hooks/useCsrfToken.ts` | **NEW** — fetch + refresh CSRF token |
| `frontend/hooks/useTrace.ts` | **NEW** — fire-and-forget event tracing |
| `frontend/hooks/openai/useBackendTts.ts` | Add `csrfToken` param, attach header |
| `frontend/components/openai/RealtimeSession.tsx` | Use `useCsrfToken`, attach header to all POSTs |
| `frontend/components/demo/SuggestedQuestions.tsx` | Add `data-testid="suggested-question"` |
| `frontend/app/student/page.tsx` | Add `useTrace`, instrument 3 events |
| `frontend/tests/e2e/observability.spec.ts` | **NEW** — 2 E2E observability tests |
| `CLAUDE.md` | Updated test counts |
| `PLAN-11.md` | This file |

---

## Test Counts After Plan 11

| Layer | Before | Delta | After |
|-------|--------|-------|-------|
| Version A unit | 49 | 0 | 49 |
| Shared unit | 27 | 0 | 27 |
| Version B unit | 54 | +8 | 62 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 78 | +4 | 82 |
| **Total** | **222** | **+12** | **234** |

---

## Key Implementation Notes

- `CSRF_SECRET` defaults to a random 32-byte hex at startup (safe for dev; set via env var in production)
- `conftest.py` sets `app.dependency_overrides[require_csrf] = lambda: None` globally; only `test_csrf.py` restores real CSRF via `real_csrf_check` fixture
- `useBackendTts` signature change (`csrfToken` param with default `null`) is backward-compatible
- E2E observability tests use `page.route()` to intercept fetch calls — no real backend needed
