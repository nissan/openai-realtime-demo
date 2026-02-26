# Architecture Comparison & Reflection
## openai-realtime-demo (new) vs livekit-openai-realtime-demo (reference)

> Fact-checked against actual source files in both repositories.
> All claims verified by independent code inspection.

---

## Context

Both projects build the same concept: voice AI tutoring with LiveKit agents, content
guardrails, subject routing, and Langfuse observability. The reference project
(`livekit-openai-realtime-demo`) was built first across ~23 plan iterations. The new
project (`openai-realtime-demo`) was rebuilt from scratch across 12 plans with the
explicit goal of A/B-comparing two architectures (LiveKit pipeline vs OpenAI Realtime
Direct) and with higher quality standards across several dimensions.

---

## Side-by-Side Snapshot

| Dimension | Reference (livekit-openai-realtime-demo) | New (openai-realtime-demo) |
|-----------|------------------------------------------|---------------------------|
| **Services** | 17 (6 Langfuse + 2 LiveKit + 7 Supabase + 2 app) | 20 (14 shared infra + 3 version-a + 1 version-b + 1 frontend + 1 db-migrate) |
| **Backends** | 1 (LiveKit agent worker only) | 2 (version-a LiveKit + version-b FastAPI) |
| **Unit tests** | 113 | 140 (non-integration) |
| **E2E tests** | 33 (6 spec files) | 82 (8 spec files, chromium + firefox + mobile) |
| **Integration tests** | None marked separately | 14 |
| **CSRF protection** | None (Supabase RLS only) | Stateless HMAC double-submit (`expire:hmac`, 300s TTL) |
| **Rate limiting** | None | slowapi per-IP (20/30/10 req/min) |
| **Routing mechanism** | `@function_tool` (LLM decides contextually) | Explicit Claude Haiku classifier → `RoutingResult(subject, confidence)` |
| **DB client** | `acreate_client` (Supabase async SDK) | `asyncpg` directly (raw pool) |
| **Session summary** | `session_report JSONB` written on close | Migration 003 adds column; `POST /session/{id}/close` writes snapshot |
| **Teacher escalation** | DB insert → Supabase Realtime → teacher frontend | WebSocket (v-b) / LiveKit JWT (v-a) |
| **Shared packages** | Monolithic `agent/` package | `shared/` (guardrail, observability, specialists) |
| **Frontend** | Role selector + LiveKit room | FlowVisualizer + TradeoffPanel + dual-version UI |
| **Agent healthchecks** | None | stdlib `HTTPServer` daemon thread on port 8080 |
| **Frontend observability** | None | `POST /events` proxy → OTEL spans |
| **Model runtime config** | `OPENAI_HISTORY_MODEL` env var (default: `gpt-5.2`) | All model IDs via env vars (`OPENAI_HISTORY_MODEL`, `ANTHROPIC_MATH_MODEL`, etc.) |
| **Postgres version** | 17.6.1 | 15.1.0.117 |
| **History model default** | `gpt-5.2` (env-var overridable) | `gpt-4o` (env-var overridable via `OPENAI_HISTORY_MODEL`) |
| **Math model** | `claude-sonnet-4-6` | `claude-sonnet-4-6` (env-var overridable via `ANTHROPIC_MATH_MODEL`) |
| **Classifier model** | `claude-haiku-4-5-20251001` | `claude-haiku-4-5-20251001` (env-var overridable via `ANTHROPIC_CLASSIFIER_MODEL`) |

---

## Where the New Project Did Better

### 1. Explicit A/B Comparison is the Whole Point

The new project's core value is making architectural tradeoffs **visible and interactive**.
`TradeoffPanel` triggers on 5 specific events (English routing, guardrail, filler, teacher,
barge-in) and explains the Version A vs Version B difference in the UI. The reference was
a single-architecture implementation with no comparison layer.

**Lesson:** When building a POC to compare approaches, make the comparison explicit in the
UI. Don't just implement both — show *why* they differ and when each matters.

### 2. Stronger Test Coverage (113+33 → 140+82)

The reference has 113 unit tests and 33 Playwright E2E tests — a respectable baseline.
The new project raises that to 140 unit (plus 14 integration) and 82 E2E tests across
Chromium, Firefox, and two mobile device profiles. The E2E tests in the reference focus
on page rendering and token API; the new project covers dual-version flows, mobile
layouts, FlowVisualizer step highlighting, and observability event interception.

The new project's testing infrastructure is also more sophisticated: CSRF bypass via
`conftest.py` dependency override, per-test `real_csrf_check` fixture restoration,
`_mock_db` autouse fixture preventing asyncpg segfaults on macOS, and integration tests
that skip cleanly when API keys are absent.

**Lesson:** The reference already showed good test discipline. The new project extended
it with more cross-cutting concerns (security, mobile, observability). The most valuable
addition was the cross-browser and mobile E2E suite — these catch CSS regressions that
unit tests cannot.

### 3. Shared Package Architecture

The `shared/` layout (guardrail, observability, specialists) means identical guardrail
logic runs in Version A's `tts_node()` and Version B's orchestrator. The same Claude
Haiku classifier is used in both versions. This prevented drift and enabled parallel
development without code duplication.

**Lesson:** Extract shared concerns into packages *before* building multiple consumers.
The PYTHONPATH complexity (`/workspace/shared:/workspace`) is a manageable tax for the
reusability benefit. Hatchling's `packages = ["."]` in `[tool.hatch.build.targets.wheel]`
resolves the directory basename correctly.

### 4. Confidence-Scored Routing vs LLM Function-Tool Routing

The reference uses `@function_tool` routing — the orchestrator LLM decides when to call
`route_to_math()` etc., with full conversation context available. This is natural for
multi-turn dialogue but opaque: routing decisions are embedded in LLM completions with no
structured confidence score.

The new project uses an explicit Claude Haiku classifier returning
`RoutingResult(subject, confidence, raw_response)`. This gives:
- Auditable decisions (confidence stored in `routing_decisions` table)
- Independently testable routing (mock the classifier, verify dispatch)
- Observable routing in Langfuse (spans carry confidence scores)

The cost: the classifier only sees the latest utterance, not the full conversation history.

**Lesson:** Explicit classifiers win on auditability and testability. LLM function-tool
routing wins on contextual reasoning across turns. The right choice depends on whether
routing decisions need to be explained and audited, or whether multi-turn context is more
important than explainability.

### 5. Agent Healthchecks (Zero-Dependency Daemon Thread)

The reference has no agent healthchecks — Docker marks them as "(no healthcheck)".
The new project adds a stdlib `HTTPServer` on port 8080 in a daemon thread, started before
`cli.run_app()`. `start_period: 60s` in the Docker healthcheck accounts for Silero VAD
model download on cold start. The daemon thread exits automatically with the process — no
cleanup needed.

**Lesson:** Always add healthchecks to custom services. A daemon-thread stdlib HTTP server
is the zero-dependency solution when the main thread is blocked by a framework's event loop.

### 6. CSRF and Rate Limiting

The reference has no CSRF protection and no rate limiting. The new project adds stateless
HMAC double-submit CSRF tokens (300s TTL, `expire_timestamp:hmac_sha256` format,
`hmac.compare_digest()` for timing-safe comparison) and per-IP slowapi rate limits
(20/min orchestrate, 30/min TTS, 10/min escalate). Frontend refreshes the CSRF token
at 80% TTL (240s) to prevent mid-session expiry.

**Lesson:** Design CSRF and rate limiting in plan 1, not as a retrofit. The stateless
HMAC double-submit pattern is ideal for stateless APIs — no session store, survives
horizontal scaling, and the only server-side secret is a 32-byte hex `CSRF_SECRET`.

### 7. Frontend Observability via `/events` Proxy

The reference traces backend operations only. Browser-side events (page load, question
selection, subject changes) are invisible to Langfuse.

The new project's `POST /events` endpoint + `useTrace()` hook lets the frontend emit
OTEL spans fire-and-forget. The endpoint is CSRF-exempt (append-only, no state mutation)
and always returns 200 regardless of tracing success — observability never breaks the UI.

**Lesson:** Observability needs to include client-side events. A simple proxy endpoint
that converts JSON events to OTEL spans is low-cost and gives end-to-end trace coverage
including user interactions before any audio is sent.

---

## Where the Reference Did Better

### 1. Simpler Operational Footprint

17 services vs 20. More importantly, the reference runs one backend; the new project
runs two (version-a + version-b) plus a DB migration service. Every additional service
adds discovery, healthcheck, dependency graph, log aggregation, and restart-policy costs.
The split is intentional (it's the comparison), but in a real production deployment you
pick one architecture.

**Lesson:** Service count is a complexity multiplier. Only add services for the comparison
you're actually making.

### 2. `@function_tool` Routing Has Contextual Awareness

The reference's `@function_tool` decorator lets the orchestrator LLM see the full
conversation history when making routing decisions. With function-tool routing, the model
can reason: "the student was working on a math problem two turns ago, so this ambiguous
question is probably math." A per-utterance classifier cannot do this.

**Lesson:** Function-tool routing is more contextually aware but harder to audit and test.
For educational apps where routing errors confuse students, the traceability of an explicit
classifier may be worth the loss of multi-turn context.

### 3. `session_report JSONB` at Session Close

The reference writes a full conversation summary to `session_report JSONB` when a session
ends via `close_session_record(session_id, session_report)`. This gives operators a
self-contained document per session — invaluable for debugging, compliance, and analytics
without joining four tables.

**Status: Implemented in this project.** Migration `003_session_report.sql` adds the
column; `POST /session/{session_id}/close` writes the snapshot (with server-side fallback
that builds a report from audit tables if the client does not provide one).

**Lesson:** Store a session summary snapshot at close time. Real-time audit tables are
good for operational queries; a JSONB snapshot document is good for post-hoc review.
These are not alternatives — have both.

### 4. Supabase Realtime for Escalations

The reference broadcasts teacher escalations via infrastructure, not application code:
the agent inserts into `escalation_events`; Supabase Realtime publishes the change;
the teacher frontend subscribes via `postgres_changes` and shows a browser notification.
If the agent restarts, the next insert still fires the notification.

The new project manages WebSocket connections in Python memory (`add_teacher_connection`,
`remove_teacher_connection`). If `backend-b` restarts, all teacher WebSocket sessions
drop and notifications are lost.

**Note:** `escalation_events` is already in the `supabase_realtime` publication
(migration 001). The remaining work is migrating the teacher frontend from the WebSocket
observer pattern to a Supabase Realtime `postgres_changes` subscription.

**Lesson:** Use existing real-time infrastructure (Supabase Realtime, Redis pub/sub,
Kafka) for event broadcasting rather than managing WebSocket state in application memory.
DB-triggered notifications survive process restarts; in-memory connections do not.

### 5. Runtime Model Configuration via Env Var

The reference externalises the history model: `os.environ.get("OPENAI_HISTORY_MODEL", "gpt-5.2")`.
Operators can swap history models (e.g., to a newer GPT release) without rebuilding the
image.

**Status: Implemented in this project.** All four model IDs are now env-var-driven:
- `OPENAI_HISTORY_MODEL` (default: `gpt-4o`)
- `ANTHROPIC_MATH_MODEL` (default: `claude-sonnet-4-6`)
- `ANTHROPIC_CLASSIFIER_MODEL` (default: `claude-haiku-4-5-20251001`)
- `OPENAI_REALTIME_MODEL` (default: `gpt-4o-realtime-preview-2024-12-17`)

All four are plumbed through `docker-compose.yml` with `${VAR:-default}` syntax.

**Lesson:** Externalise LLM model IDs as env vars from the start. Models iterate on
6–12 month cycles; the cost of an env var is negligible and the operational flexibility
is significant.

### 6. Async Supabase Client vs Raw asyncpg

The reference uses `acreate_client` from the `supabase` Python SDK — the same client
used in the frontend, with consistent RLS context, auto-reconnect, and typed query
results. The new project uses `asyncpg` directly, which required special mock fixtures
to prevent C-level segfaults in tests on macOS Python 3.13.

**Lesson:** Use the async SDK client for your backend database when it exists. Raw asyncpg
gives more control but the asyncpg segfault-in-tests problem on macOS (requiring careful
patching of `get_pool()` or `_create_learning_session`) is a real maintenance cost.

### 7. Newer Postgres (17.6.1 vs 15.1.0.117)

Minor in practice for a POC, but the reference uses Postgres 17.6.1 vs the new project's
15.1.0.117. New JSON functions, improved VACUUM, and better logical replication are
available in 17 but not used in either project at this scale.

---

## Neutral Tradeoffs (Neither Is Clearly Better)

### LiveKit Pipeline vs OpenAI Realtime Direct

- **LiveKit (Version A):** More control over each pipeline stage. STT, LLM, and TTS
  are independently replaceable. Guardrail integrates cleanly at the `tts_node` boundary.
  Higher latency (~1–2s) because each stage serialises.
- **Realtime Direct (Version B):** Lower latency (~230–290ms TTFB). Native barge-in
  cancellation. But guardrail must run *before* streaming starts (harder to integrate),
  and TTS is locked to OpenAI's voice selection.

The new project correctly identifies these as complementary and makes the tradeoffs
visible. The right choice depends on latency requirements vs pipeline flexibility.

### Two-Session English Architecture

Both projects independently arrived at the same solution: English requires a separate
LiveKit `AgentSession` dispatched on-demand. The LLM orchestrator cannot host both a
traditional STT→LLM→TTS pipeline and an OpenAI Realtime speech-to-speech session in
the same `AgentSession`. The handoff is metadata-driven in both implementations.

---

## Universal Lessons for Building Voice AI Systems

**1. Two-session architecture for English (speech-to-speech) is non-obvious.**
Both projects discovered independently that OpenAI Realtime cannot coexist with
STT+LLM+TTS pipeline agents in a single `AgentSession`. This cascades into routing
logic, session state, and frontend state management. Document this constraint before
writing any agent code.

**2. macOS Docker IPv6 routing kills healthchecks.**
`localhost` resolves to `::1` (IPv6) in macOS Docker; many services only bind
`0.0.0.0` (IPv4). Always write healthchecks with explicit `127.0.0.1`. This affected
ClickHouse, Kong, and Langfuse in both projects.

**3. PYTHONPATH in Python monorepos is fragile.**
`uv pip install -e .` adds the *package directory* to `sys.path`, not its parent.
If your package is at `shared/guardrail/`, then `shared/guardrail/` is on the path —
not `shared/`. You must add the parent explicitly or `import guardrail` fails. Both
projects spent significant debugging time on this.

**4. Sentence-boundary guardrail buffering must flush residual.**
Both projects independently implemented buffering at `[.!?]` punctuation before calling
the guardrail API, and both hit the same bug: not flushing the tail after the stream
ends. Make the end-of-stream flush part of the pattern, not something you remember.

**5. `tts_node` returning the wrong type fails silently.**
The LiveKit Agents SDK drops `tts_node` output with no exception and no log if the
method returns `str` instead of `AsyncIterable[AudioFrame]`. This is the most dangerous
silent failure in the SDK.

**6. Langfuse v3 is four backing services, not one.**
PostgreSQL + ClickHouse + MinIO (S3-compatible event storage) + `langfuse-worker`
(queue processor) are all mandatory. Without `langfuse-worker`, spans are generated
and silently queued but 0 traces appear in the UI. Both projects hit this.

**7. Explicit routing confidence scores pay dividends across the whole stack.**
Routing confidence flows into Langfuse traces, DB audit logs, test assertions, and the
UI. Design routing to return a confidence score from day 1 — even if you don't use it
immediately, it's invaluable later for debugging and analytics.

**8. Fire-and-forget for every non-critical path.**
Both versions need sub-100ms response times for orchestration endpoints. The pattern
is consistent: `asyncio.create_task()` for background jobs, `BackgroundTasks` in
FastAPI, never `await` in the request path for audit logging, transcript saving, or
guardrail event logging. All of these should be best-effort (`try/except`, never block
the pipeline).

**9. `docker compose build --no-cache` after every dependency addition.**
Docker layer caching hides missing runtime dependencies. Both projects hit this: a
missing package in the Dockerfile was invisible until `--no-cache`. After any new
`pyproject.toml` dependency, always verify with a no-cache build.

**10. Observability needs client-side events too.**
The reference traces backend operations; the new project adds a `/events` endpoint
for frontend events. Without browser-side tracing, you cannot see when users abandon
sessions, which questions they ask most, or whether UI interactions correlate with
routing decisions. A simple JSON-to-OTEL proxy is 30 lines and gives full end-to-end
visibility.

**11. Use DB-layer event broadcasting, not in-memory WebSocket state.**
For any event that needs to survive a backend restart (escalations, session close,
teacher notifications), write to a DB table with Realtime or pub/sub enabled. Don't
manage WebSocket connection state in application memory — it disappears on restart.

**12. Store a session summary snapshot at close time.**
Audit tables are good for operational queries. A `session_report JSONB` written when
the session ends gives operators a self-contained, human-readable summary without
joining multiple tables. Have both: real-time audit tables *and* a snapshot document.

**13. Externalise LLM model IDs as env vars.**
Models iterate on 6–12 month cycles. An env var costs one line of code and lets
operators upgrade models without rebuilding images. Never bake model IDs into source
code when env vars serve equally well.

**14. Rate-limit and CSRF from day 1.**
Both are easy to add early; both become harder to retrofit. CSRF required updating
5+ test files when added late in the new project. The stateless HMAC double-submit
pattern costs nothing architecturally and protects mutating endpoints immediately.

---

## Final Assessment

The new project is a **significant quality improvement** over the reference in testing
breadth, security (CSRF, rate limiting), observability (frontend events, structured
confidence scores), shared package architecture, and operational completeness
(agent healthchecks).

The reference is **closer to production patterns** for a single-architecture deployment:
Supabase async SDK, DB-triggered Realtime escalations, session summary at close,
runtime model configuration, and simpler operational footprint (17 services vs 20).

**The ideal system combines both:**
- New project: shared packages + CSRF/rate limiting + dual-version UI + frontend
  observability + comprehensive E2E tests + agent healthchecks
- Reference: `acreate_client` + Supabase Realtime escalations + `session_report JSONB`
  + `@function_tool` contextual routing + env-var model IDs + Postgres 17

Neither project is wrong. Each made reasonable tradeoffs given its goals. The patterns
that appear in both — sentence-boundary guardrail buffering, two-session English
architecture, fire-and-forget audit logging, OTEL HTTP/protobuf to Langfuse — represent
the settled conventions for this class of voice AI system.

---

## Implementation Status

Items from "Where the Reference Did Better" that have been backported to this project:

| Item | Status |
|------|--------|
| Env-var model IDs (all 4 models) | Done — `OPENAI_HISTORY_MODEL`, `ANTHROPIC_MATH_MODEL`, `ANTHROPIC_CLASSIFIER_MODEL`, `OPENAI_REALTIME_MODEL` |
| `session_report JSONB` at session close | Done — migration `003_session_report.sql` + `POST /session/{id}/close` |
| Supabase Realtime escalations (vs in-memory WS) | Partial — `escalation_events` already in Realtime publication; teacher frontend migration pending |
| Postgres 17 upgrade | Not done — Supabase image `15.1.0.117` still in use; upgrade requires data migration |
| Async Supabase SDK (vs raw asyncpg) | Not done — significant refactor; asyncpg works with careful test fixtures |
