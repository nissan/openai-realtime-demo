# Claude Code Guidance — openai-realtime-demo

## Project Overview
Voice AI tutoring POC comparing LiveKit (Version A) vs OpenAI Realtime Direct (Version B).

## Commands

### Start all services
```bash
docker compose up -d
docker compose ps  # verify all 20 services healthy
```

### Run unit tests (no network required)
```bash
# Shared packages (PYTHONPATH must include shared/ so packages find each other)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v -m "not integration"
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/observability --extra test pytest tests/ -v
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test pytest tests/ -v -m "not integration"

# Version A (--no-project to skip heavy livekit-agents installation)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  pytest version-a/agent/tests/ -v

# Version B (dev extra contains pytest)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev pytest tests/ -v -m "not integration"
```

### Run integration tests (requires real API keys)
```bash
# Per package
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/integration/ -v -s -m integration

# All tests (unit + integration): integration shows SKIPPED if keys absent
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test pytest tests/ -v
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev pytest tests/ -v
```

### Frontend
```bash
cd frontend && npm install && npm run dev
cd frontend && npm run test:e2e
```

### Verify Langfuse
```bash
curl http://localhost:3001/api/public/health
```

## Critical Gotchas

### macOS LiveKit WebRTC
`version-a/livekit.yaml` MUST have `rtc.node_ip: 127.0.0.1` or browser WebRTC fails silently.

### langfuse-worker
`docker-compose.yml` MUST include `langfuse-worker` service. Without it: 0 traces in UI, silent queue buildup.

### OTEL endpoint
Use HTTP/protobuf: `/api/public/otel/v1/traces` — NOT gRPC. Port 3001, not 4317.

### tts_node return type
`GuardedAgent.tts_node` MUST return `AsyncIterable[rtc.AudioFrame]` — NOT str. Silent failure otherwise.

### session.interrupt()
NEVER use `session.interrupt()`. Use `asyncio.sleep()` + `aclose()` instead.

### State detection
ALWAYS use counters (`skip_next_user_turns: int`), NEVER string-match LLM output.

### Agent routing
Orchestrator-only routing. No specialist-to-specialist transitions.

### Sentence guardrail
Must buffer at punctuation boundaries and flush residual at stream end.

### ClickHouse healthcheck
Use `http://127.0.0.1:8123/ping` NOT `localhost` (macOS IPv6 routing issue).

### Kong healthcheck  
Use `http://127.0.0.1:8001/` NOT `localhost:8000`.

### next.config
Use `next.config.mjs` NOT `next.config.ts` (Next.js 14 limitation).

### LiveKit styles import
Use JS import in layout.tsx: `import "@livekit/components-styles"` — CSS @import fails.

### LiveKit Room component
Use `ConnectionGuard` pattern — NO `SessionProvider` wrapper.

## Architecture
- `shared/` — Python packages used by both backends
- `version-a/` — LiveKit Agents worker (pipeline STT→LLM→TTS, GuardedAgent)
- `version-b/` — FastAPI backend (no LiveKit, direct OpenAI Realtime)
- `frontend/` — Single Next.js 14 app, URL-driven version selection (?v=a|b)
- `db/` — SQL migrations

## Subjects
- Math: Claude Sonnet 4.6 (shared/specialists/math.py)
- History: GPT-4o (shared/specialists/history.py)  
- English: OpenAI Realtime native (english_agent.py in Version A, Realtime session in Version B)
- Routing: Claude Haiku classifier (shared/specialists/classifier.py)

## Version Differences (TradeoffPanel triggers)
1. English question: Version A spins up separate Realtime AgentSession; Version B keeps Realtime agent
2. Guardrail: Version A pre-TTS in GuardedAgent.tts_node; Version B pre-TTS in /tts/stream
3. Filler: Version A orchestrator speaks; Version B Realtime speaks at 500ms/1500ms/3000ms
4. Teacher: Version A LiveKit room (audio+video); Version B WebSocket (transcript+text)
5. Barge-in: Version A pipeline flush; Version B Realtime cancels response
