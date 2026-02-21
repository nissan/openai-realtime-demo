# Plan: openai-realtime-demo (Greenfield Voice AI Tutoring POC)

## Context

This is a **proof-of-concept demo app** that lets a user compare two architectures for voice AI tutoring:
- **Version A**: LiveKit-based (multi-participant rooms, pipeline STT→LLM→TTS, GuardedAgent)
- **Version B**: OpenAI Realtime direct (browser WebRTC to OpenAI, backend orchestrator, Variant 2 backend TTS)

Two user personas: **Student** (asks questions, runs demos) and **Teacher** (joins/observes on escalation).

**Key UX**: A single landing page lets you choose which architecture to demo. Once chosen, you enter as a student. At every point where the two versions behave differently, an **infographic panel** (hover or persistent) explains the tradeoff. The goal is to show the architectures working side-by-side and explicitly call out what differs and why.

**Lessons applied from previous 23-plan project** (all critical failures documented in MEMORY.md):
- OTEL + Langfuse from day 1 (previous project: plan 17)
- Integration tests from day 1 (previous project: plan 19)
- `langfuse-worker` in docker-compose from first commit (without it: 0 traces)
- `tts_node` must return `AsyncIterable[rtc.AudioFrame]` not str (silent failure)
- Never `session.interrupt()` — use `asyncio.sleep()` + `aclose()` instead
- Counters not string matching for LLM-generated state detection
- Orchestrator-only routing (no specialist-to-specialist)
- Sentence-level guardrail must buffer at punctuation boundaries and flush residual

---

## Architecture: Single Frontend, Two Backends

```
openai-realtime-demo/
├── CLAUDE.md                      # Claude Code guidance
├── PLAN.md                        # Plan 1 (this)
├── MEMORY.md                      # Architect audit trail
├── docker-compose.yml             # Full 20-service stack
├── .env.example
│
├── shared/                        # Installable Python packages (used by BOTH backends)
│   ├── guardrail/
│   │   ├── pyproject.toml
│   │   ├── service.py             # check(), rewrite(), check_and_rewrite()
│   │   ├── models.py              # ModerationResult dataclass
│   │   └── tests/                 # Unit tests (mocked API)
│   ├── observability/
│   │   ├── pyproject.toml
│   │   ├── langfuse.py            # setup_langfuse_tracing(), get_tracer()
│   │   └── tests/
│   └── specialists/               # Subject LLM calls (pure async, no LiveKit deps)
│       ├── pyproject.toml
│       ├── math.py                # AsyncGenerator[str]: Claude Sonnet 4.6
│       ├── history.py             # AsyncGenerator[str]: GPT-4o
│       ├── english.py             # AsyncGenerator[str]: text-only English
│       ├── classifier.py          # route_intent(transcript) → "math"|"history"|"english"|"escalate"
│       └── tests/                 # Unit tests (mocked)
│
├── version-a/                     # LiveKit Agents worker
│   ├── livekit.yaml               # rtc.node_ip: 127.0.0.1 (macOS CRITICAL)
│   └── agent/
│       ├── pyproject.toml         # depends on shared/{guardrail,observability,specialists}
│       ├── Dockerfile             # WORKDIR /workspace/agent, ENV PYTHONPATH=/workspace
│       ├── main.py                # Two workers: learning-orchestrator, learning-english
│       ├── agents/
│       │   ├── base.py            # GuardedAgent: tts_node → AsyncIterable[rtc.AudioFrame]
│       │   ├── orchestrator.py    # Claude Haiku; @function_tool routing
│       │   ├── math_agent.py      # Wraps shared/specialists/math.py in GuardedAgent
│       │   ├── history_agent.py   # Wraps shared/specialists/history.py in GuardedAgent
│       │   └── english_agent.py   # OpenAI Realtime native session (separate AgentSession)
│       ├── models/
│       │   └── session_state.py   # SessionUserdata: skip_next_user_turns counter
│       ├── tools/
│       │   └── routing.py         # _route_to_math_impl, _escalate_impl, etc.
│       ├── services/
│       │   ├── transcript_store.py
│       │   └── human_escalation.py  # LiveKit JWT + Supabase insert
│       └── tests/                 # 100+ unit + integration tests
│
├── version-b/                     # FastAPI backend (no LiveKit)
│   └── backend/
│       ├── pyproject.toml         # depends on shared/{guardrail,observability,specialists}
│       ├── Dockerfile
│       ├── main.py                # FastAPI app
│       ├── routers/
│       │   ├── session.py         # POST /session/token → OpenAI ephemeral key
│       │   ├── orchestrator.py    # POST /orchestrate (<100ms), GET /orchestrate/{job_id}
│       │   ├── tts.py             # POST /tts/stream → chunked PCM audio
│       │   └── teacher.py         # WebSocket /ws/teacher/{session_id}
│       ├── models/
│       │   ├── session_state.py   # SessionUserdata (adapted, no LiveKit)
│       │   └── job.py             # OrchestratorJob dataclass
│       ├── services/
│       │   ├── job_store.py       # asyncio dict + Redis TTL cleanup
│       │   ├── transcript_store.py
│       │   └── human_escalation.py  # WebSocket broadcast + Supabase insert
│       └── tests/                 # Unit + integration tests
│
├── frontend/                      # SINGLE Next.js 14 frontend for both versions
│   ├── next.config.mjs            # NOT next.config.ts (Next.js 14 limitation)
│   ├── package.json
│   ├── app/
│   │   ├── layout.tsx             # import "@livekit/components-styles" as JS (not CSS @import)
│   │   ├── page.tsx               # Landing: VersionSelector + tradeoff comparison
│   │   ├── student/
│   │   │   └── page.tsx           # ?v=a (LiveKit) or ?v=b (OpenAI) from URL param
│   │   └── teacher/
│   │       └── page.tsx           # ?v=a or ?v=b; version-appropriate join UI
│   ├── components/
│   │   ├── landing/
│   │   │   ├── VersionSelector.tsx    # Two cards: LiveKit vs OpenAI-only
│   │   │   └── ArchitectureCompare.tsx # Side-by-side architecture diagram
│   │   ├── demo/
│   │   │   ├── TradeoffPanel.tsx      # Hover/persistent infographic
│   │   │   ├── FlowVisualizer.tsx     # Animated pipeline diagram
│   │   │   └── SuggestedQuestions.tsx # Pre-populated demo questions
│   │   ├── shared/
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── SubjectBadge.tsx
│   │   │   └── EscalationBanner.tsx
│   │   ├── livekit/
│   │   │   └── StudentRoom.tsx        # LiveKitRoom > ConnectionGuard (no SessionProvider)
│   │   └── openai/
│   │       ├── RealtimeSession.tsx    # WebRTC to OpenAI Realtime + dual audio management
│   │       └── TeacherObserver.tsx    # WebSocket observer
│   ├── hooks/
│   │   ├── useVersion.ts         # Reads ?v= from URL, exposes "a"|"b"
│   │   ├── livekit/
│   │   │   └── useTranscript.ts  # room.on("dataReceived") with topic filter
│   │   └── openai/
│   │       ├── useRealtimeSession.ts  # WebRTC lifecycle + tool call interface
│   │       └── useBackendTts.ts       # Dual audio stream (filler=Realtime, answer=backend)
│   └── tests/e2e/
│
└── db/
    └── migrations/
        ├── 001_shared_schema.sql  # learning_sessions, transcript_turns, guardrail_events, etc.
        └── 002_version_b_jobs.sql # orchestrator_jobs table
```

---

## Landing Page & Demo UX Design

### Landing Page (`/`)
- Two large cards side-by-side:
  - **Card A — LiveKit Architecture**: highlights multi-participant rooms, media routing, native barge-in
  - **Card B — OpenAI Realtime Direct**: highlights minimal infra, direct browser→AI, Variant 2 safety
- Below cards: collapsible architecture comparison table (latency, safety, infra complexity, teacher options)
- "Start Demo" button on each card → navigates to `/student?v=a` or `/student?v=b`

### Student Demo Flow
1. `?v=a` or `?v=b` drives which session component renders (LiveKit vs OpenAI Realtime)
2. `SuggestedQuestions` panel pre-populates 6 questions covering all specialists:
   - Math: "What is 25% of 80?" / "Solve 2x² + 5x - 3 = 0"
   - History: "Why did World War I start?" / "What was the Roman Empire?"
   - English: "Help me improve this sentence" / "Explain a metaphor"
3. As conversation flows, `FlowVisualizer` animates which pipeline step is active
4. `TradeoffPanel` slides in contextually when the two versions handle something differently

### TradeoffPanel — Trigger Points and Content

| Trigger | LiveKit (Version A) | OpenAI-only (Version B) |
|---|---|---|
| **English question detected** | Separate Realtime AgentSession spins up (~230ms TTFB) | Realtime agent stays in control; calls `dispatch_to_orchestrator` |
| **Guardrail fires** | Pre-TTS: `GuardedAgent.tts_node` intercepts text before synthesis | Pre-TTS: backend guardrail runs before `/tts/stream` is called |
| **Filler while thinking** | Orchestrator speaks during routing (pipeline TTS) | Realtime agent speaks filler at 500ms/1500ms/3000ms thresholds |
| **Teacher escalation** | Teacher joins LiveKit room (audio + video) | Teacher monitors via WebSocket (transcript + text injection) |
| **Barge-in / interrupt** | Pipeline flush, audio queue cleared, VAD resumes | Realtime cancels current response, new turn_id issued |

**TradeoffPanel component design:**
```
┌─────────────────────────────────────────────────────┐
│ ⚡ How this works differently here                   │
├─────────────────────────────────────────────────────┤
│ WITH LIVEKIT              │ WITHOUT LIVEKIT          │
│ Teacher joins WebRTC room │ Teacher observes via WS  │
│ Full audio/video          │ Transcript + text only   │
│ Guaranteed delivery       │ Simpler infra, less rich │
│                           │                          │
│ [Infrastructure: 22 svcs] │ [Infrastructure: 18 svcs]│
└─────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Shared Specialists (DRY)
`shared/specialists/` contains pure async Python functions that both backends call:
- Version A wraps them inside `GuardedAgent` subclasses (LiveKit pipeline)
- Version B calls them directly from asyncio orchestrator tasks
- Same Claude Sonnet 4.6 for Math, GPT-4o for History, in both versions

### 2. Single Frontend, URL-driven version
`?v=a` → renders LiveKit components; `?v=b` → renders OpenAI components. The `useVersion()` hook reads this. No separate frontend deployments.

### 3. Counter-based state everywhere
- `skip_next_user_turns: int` (never string-match LLM output)
- `fillerState: number` (0/1/2/3 for filler thresholds)
- `OrchestratorJob.status` enum with DB constraint

### 4. Backend TTS Streaming — Dual Audio (Version B)
- OpenAI Realtime speaks filler phrases (via existing WebRTC)
- Backend `/tts/stream` delivers guardrailed answer audio (chunked PCM)
- Client mutes Realtime WebRTC output when backend TTS is playing (50ms crossfade)
- `tts_ready` flag on job signals client to start streaming

### 5. Teacher escalation
- Version A: pre-signed LiveKit JWT → teacher joins room with audio
- Version B: WebSocket URL → teacher monitors transcript + injects text
- Both: `escalation_events` table with Supabase Realtime broadcast

---

## Docker-Compose Services (20 total)

**Shared infra (14):** redis, langfuse-db, langfuse-clickhouse, langfuse-minio, langfuse-minio-init, langfuse, **langfuse-worker** _(CRITICAL: must be here from day 1)_, supabase-db, supabase-auth, supabase-kong, supabase-rest, supabase-realtime, supabase-meta, supabase-studio

**Version A (3):** livekit _(livekit.yaml: `rtc.node_ip: 127.0.0.1`)_, agent-a _(two workers: orchestrator + english)_, agent-a-english

**Version B (1):** backend-b _(FastAPI + WebSocket; port 8001)_

**Frontend (1):** frontend _(single Next.js; port 3000; serves both versions)_

**Key notes:**
- `langfuse-worker` depends_on: langfuse (healthy). Without it → 0 traces in UI.
- ClickHouse healthcheck: `http://127.0.0.1:8123/ping` NOT `localhost` (macOS IPv6 routing)
- Kong healthcheck: `http://127.0.0.1:8001/` NOT `localhost:8000`
- Langfuse OTEL: HTTP/protobuf endpoint `/api/public/otel/v1/traces`, NOT gRPC

---

## Database Schema (Shared)

```sql
-- learning_sessions: both versions
-- version: 'a' | 'b'
-- transcript_turns: speaker = 'student'|'orchestrator'|'math'|'history'|'english'|'teacher'
-- routing_decisions: from_agent, to_agent, confidence
-- escalation_events:
--   version='a': teacher_token = LiveKit JWT
--   version='b': teacher_ws_url = wss://backend/ws/teacher/{session_id}
-- guardrail_events: original_text, rewritten_text, categories_flagged[]
-- orchestrator_jobs (Version B only): status enum, safe_text, tts_ready flag
```

Supabase Realtime: `ALTER PUBLICATION supabase_realtime ADD TABLE escalation_events, transcript_turns`

---

## Implementation Phases

### Phase 0 — Foundation (before any agent code)
1. Monorepo directories + `__init__.py` files
2. `docker-compose.yml` with all 20 services including `langfuse-worker`
3. `shared/observability/langfuse.py` — OTEL setup
4. `shared/guardrail/service.py` — check, rewrite, check_and_rewrite
5. Unit tests for both shared packages
6. **Gate**: Send test OTEL span → verify it appears in Langfuse UI (`http://localhost:3001`)

### Phase 1 — Shared Specialists + DB (parallel with Phase 0)
1. `db/migrations/001_shared_schema.sql` — all tables + Realtime publications
2. `shared/specialists/classifier.py` — Claude Haiku routing (temperature 0.1)
3. `shared/specialists/math.py` — Sonnet 4.6 async stream
4. `shared/specialists/history.py` — GPT-4o async stream
5. `shared/specialists/english.py` — text English fallback
6. Unit tests for all specialists (mocked LLM calls)
7. Integration tests (marked `@pytest.mark.integration`): live routing classification

### Phase 2 — Version A Agent
1. `version-a/livekit.yaml` with `rtc.node_ip: 127.0.0.1`
2. `SessionUserdata` dataclass (`skip_next_user_turns` counter from day 1)
3. `GuardedAgent.tts_node` returning `AsyncGenerator[rtc.AudioFrame, None]`
4. Unit test: `object.__new__(GuardedAgent)` for sentence buffering without LiveKit infra
5. `routing.py` — specialists expose only `route_back_to_orchestrator` (no spec-to-spec)
6. Agent impls: orchestrator, math, history (wrap shared specialists), english (Realtime)
7. Synthetic routing tests (63-question parametrised dataset)
8. `main.py` — two workers (pipeline + English Realtime)
9. Integration tests: LLM/TTS/STT live (skippable)
10. Dockerfile: `WORKDIR /workspace/agent`, `ENV PYTHONPATH=/workspace`

### Phase 3 — Version B Backend
1. `models/job.py` — OrchestratorJob with status enum
2. `services/job_store.py` — asyncio task registry + Redis TTL
3. `POST /orchestrate` — spawns `asyncio.create_task()`, returns `{job_id}` in < 100ms
4. Orchestrator task: classifier → specialist stream → sentence guardrail → `job.safe_text`
5. `GET /orchestrate/{job_id}` — poll for status
6. `POST /tts/stream` — chunked PCM streaming (stream as it arrives, never buffer full response)
7. `POST /session/token` — OpenAI ephemeral key endpoint
8. `WebSocket /ws/teacher/{session_id}` — transcript relay + text injection
9. `db/migrations/002_version_b_jobs.sql`
10. Unit + integration tests for all routes

### Phase 4 — Frontend (single Next.js)
1. Landing page — `VersionSelector` + `ArchitectureCompare`
2. `useVersion()` hook — reads `?v=` URL param
3. `FlowVisualizer` — pipeline step animation (lights up as processing flows)
4. `TradeoffPanel` — contextual comparison infographic (see trigger table above)
5. `SuggestedQuestions` — 6 demo questions covering math, history, English
6. Version A path: `StudentRoom.tsx` with LiveKit (NO SessionProvider — ConnectionGuard pattern)
7. Version B path: `RealtimeSession.tsx` with dual audio (Realtime filler + backend TTS answer)
8. `useBackendTts.ts` — Web Audio API + 50ms mute crossfade
9. Teacher portal (`/teacher?v=a` or `?v=b`)
10. Playwright E2E tests: landing page, student flow (both versions), teacher portal

### Phase 5 — Hardening
1. Guardrail security integration tests (true-positive harmful content)
2. E2E tests for teacher escalation flows
3. E2E: TradeoffPanel appears on English question routing
4. `CLAUDE.md` — commands, gotchas, architecture
5. `MEMORY.md` — lessons applied
6. `PLAN.md` — this document saved

---

## Critical Files (Priority Order)

| P | File | Risk if wrong |
|---|---|---|
| P0 | `shared/observability/langfuse.py` | 0 traces in UI for entire session |
| P0 | `docker-compose.yml` (langfuse-worker) | 0 traces in UI, silent queue buildup |
| P0 | `version-a/livekit.yaml` (rtc.node_ip) | Browser WebRTC fails silently on macOS |
| P1 | `version-a/agent/agents/base.py` (tts_node) | Agent thinks, never speaks (silent failure) |
| P1 | `version-a/agent/tools/routing.py` | Infinite routing loops |
| P1 | `version-b/backend/routers/orchestrator.py` | Dispatch blocks, filler threshold broken |
| P1 | `version-b/backend/routers/tts.py` | Answer buffered, not streamed |
| P2 | `frontend/hooks/openai/useBackendTts.ts` | Audio overlap or silence |
| P2 | `frontend/components/demo/TradeoffPanel.tsx` | Core demo UX missing |
| P2 | `frontend/next.config.mjs` | Build fails (`.ts` not supported in Next.js 14) |
| P2 | `frontend/app/layout.tsx` | CSS @import fails for livekit styles |

---

## Test Strategy

**Unit tests** (no network, no Docker; run first):
- `PYTHONPATH=$(pwd) uv run --directory version-a/agent pytest tests/ -v`
- `PYTHONPATH=$(pwd) uv run --directory version-b/backend pytest tests/ -v`
- `PYTHONPATH=$(pwd) uv run --directory shared/guardrail pytest tests/ -v`

**Integration tests** (`@pytest.mark.integration`, skippable when no keys):
- Guardrail true-positive detection
- Live routing classification (Claude Haiku)
- Version B: full dispatch → poll → TTS stream

**E2E** (Playwright):
- `cd frontend && npm run test:e2e`
- Covers: landing page version selection, student demo flow (both), teacher portal, TradeoffPanel trigger

---

## Verification Checklist

1. `docker compose up -d` → all 20 services healthy
2. `curl http://localhost:3001/api/public/health` → `{"status":"ok"}`
3. Send test OTEL span → visible in Langfuse traces
4. Open `http://localhost:3000` → VersionSelector renders with two cards
5. Choose Version A → `/student?v=a` → say "What is 25% of 80?" → hear math answer → Langfuse shows routing span
6. Choose Version B → `/student?v=b` → say same question → hear 500ms filler → hear backend TTS answer
7. Ask English question in both versions → TradeoffPanel slides in explaining the difference
8. Trigger teacher escalation → version-appropriate teacher notification fires
9. All unit tests pass: `pytest tests/ -v` (no network calls)
10. E2E: `npm run test:e2e` passes in chromium + firefox

---

## Architectural Audit Notes

### Service Count Verification
- Shared infra: 14 services (redis + langfuse×7 + supabase×6)
- Version A: 3 services (livekit, agent-a, agent-a-english)
- Version B: 1 service (backend-b)
- Frontend: 1 service (frontend)
- **Total: 19 services** (plan says 20 — verify livekit counts as 1 or if there's an additional service)

### Security Considerations
- All API keys via environment variables (never hardcoded)
- Guardrail runs before TTS synthesis in both versions
- Teacher escalation requires authenticated JWT (Version A) or session ID (Version B)
- Supabase RLS policies should be applied in production

### Performance Targets
- Version B orchestrate endpoint: < 100ms response time (async dispatch)
- Filler audio threshold: 500ms → "Let me think", 1500ms → additional filler, 3000ms → "Almost there"
- English agent session spin-up (Version A): ~230ms TTFB target
- Backend TTS stream: first chunk within 200ms of request
