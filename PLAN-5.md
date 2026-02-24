# Plan 5: End-to-End Demo Completion

> Status: **COMPLETE**
> Previous plans: PLAN.md, PLAN-2.md, PLAN-3.md, PLAN-4.md

---

## Summary

Fixed 6 P1 frontend gaps that prevented the demo from functioning end-to-end, plus 8 P2 gaps for
audit trail, error handling, and UI wiring.

---

## Changes Made

### Step 1 — LiveKit Token API Route (P1)

**Created:** `frontend/app/api/livekit-token/route.ts`
- Generates LiveKit JWT using Node.js built-in `crypto` (HMAC-SHA256)
- No external SDK dependency — works in Docker without rebuilding
- Env vars: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `NEXT_PUBLIC_LIVEKIT_ROOM`

### Step 2 — Fix `useRealtimeSession` (P1)

**Modified:** `frontend/hooks/openai/useRealtimeSession.ts`
- Accepts `sessionId` parameter (caller generates UUID once)
- Passes `?session_id={sessionId}` to `POST /session/token`
- `dc.onmessage` handler for:
  - `conversation.item.input_audio_transcription.completed` → `onTranscript("user", ...)`
  - `response.audio_transcript.done` → `onTranscript("assistant", ...)`
  - `response.output_item.done` (function_call) → `onToolCall(name, args)`
- `dc.onopen` → `setConnectionState("connected")`
- Optional callbacks: `onTranscript`, `onToolCall`

### Step 3 — Wire `RealtimeSession` (P1)

**Modified:** `frontend/components/openai/RealtimeSession.tsx`
- Generates stable `sessionId` via `useMemo(() => crypto.randomUUID(), [])`
- `onTranscript` callback → appends turns to transcript display
- `onToolCall` callback → handles `dispatch_to_orchestrator`:
  - `POST /orchestrate` then `POST /orchestrate/{job_id}/wait`
  - Calls `playJobAudio(job_id, sessionId)` when TTS ready
  - Shows `<EscalationBanner>` when `subject === "escalate"`
- `selectedQuestion` prop → `sendText()` when connected

### Step 4 — Wire Student Page (P1)

**Modified:** `frontend/app/student/page.tsx`
- `selectedQuestion` state wired to `<SuggestedQuestions onSelect={...} />`
- Passes `selectedQuestion` to `<StudentRoom>` and `<RealtimeSession>`
- Clears selection after 100ms (so same question can be re-selected)

**Modified:** `frontend/components/livekit/StudentRoom.tsx`
- Accepts `selectedQuestion?: string | null` prop
- Shows `data-testid="say-this-hint"` banner in BOTH pre-join and joined states
- Banner shows in pre-join so user knows what to say before clicking "Join"
- Auto-dismisses after 10s

### Step 5 — DB Audit Trail (P2)

**Modified:** `version-b/backend/routers/orchestrator.py`
- **Fixed `raw_text`**: tee generator captures raw chunks before guardrail
- **`_log_routing_decision()`**: INSERTs into `routing_decisions` table (session_id, from_agent, to_agent, latency_ms)
- **`_log_guardrail_event()`**: INSERTs into `guardrail_events` table (session_id, original_text, rewritten_text, flagged)
- Both functions have try/except — DB failures only log a warning

**Modified:** `version-b/backend/routers/session.py`
- **`_create_learning_session()`**: INSERTs into `learning_sessions` table (session_id, version='b', started_at)
- Called after successful OpenAI session creation
- try/except — DB failure never breaks token creation

### Step 6 — Error Handling Fixes (P2)

**Modified:** `frontend/hooks/livekit/useTranscript.ts`
- `catch {}` → `catch (e) { console.error("useTranscript parse error:", e); }`

**Modified:** `frontend/components/openai/TeacherObserver.tsx`
- Added `ws.onerror = (e) => { console.error("Teacher WS error:", e); setConnected(false); }`
- `catch {}` → `catch (e) { console.error("Teacher WS message parse error:", e); }`

### Step 7 — Infrastructure + Docs (P3)

**Modified:** `.env.example`
- Added: `NEXT_PUBLIC_BACKEND_B_URL`, `BACKEND_B_WS_URL`, `NEXT_PUBLIC_LIVEKIT_ROOM`

### Step 8 — New Tests

**Created:** `version-b/backend/tests/test_orchestrator_audit.py` (6 tests)
- `test_routing_decision_inserted_on_classification`
- `test_guardrail_event_inserted_when_flagged`
- `test_guardrail_event_inserted_when_clean`
- `test_raw_text_differs_from_safe_text_when_guardrail_rewrites`
- `test_learning_session_inserted_on_token_creation`
- `test_audit_failures_do_not_break_orchestration`

**Modified:** `version-b/backend/tests/test_session_route.py`
- Added `_create_learning_session` mock to prevent asyncpg segfault in tests

**Created:** `frontend/tests/e2e/integration.spec.ts` (3 tests × 2 browsers = 6 E2E tests)
- `clicking suggested question shows say-this hint for version-a`
- `clicking suggested question in version-b stores selection`
- `livekit-token route responds with token shape`

---

## Test Results

| Layer | Before | Added | After |
|-------|--------|-------|-------|
| Version A unit | 36 | 0 | 36 |
| Shared/v-b unit | 74 | +6 | 80 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 42 | +6 | 48 |
| **Total** | **166** | **+12** | **178** |

All 80 Python unit tests pass. All 48 E2E tests pass (chromium + firefox).

---

## What is NOT in Plan 5 (Deferred to Plan 6)

- `FlowVisualizer activeStep` real-time pipeline step tracking
- `version-a` agent's `learning_sessions` population
- Version A `routing_decisions` DB inserts
- Mobile/responsive E2E testing
- CSRF token validation for POST endpoints
- Production deployment playbook
