# Plan 4: Audit Gap Remediation

**Status**: COMPLETE
**Date**: 2026-02-24

## Summary

Plan 4 closed three gaps identified after Plans 1–3:

1. **Version A agent unit test coverage** — Added 21 new tests covering `orchestrator.py` constants, `math_agent.py`/`history_agent.py`/`english_agent.py` constants, `tools/routing.py` impl functions, and `services/transcript_store.py`/`services/human_escalation.py`.
2. **Frontend E2E coverage** — Added `data-testid` attributes to 4 components and 3 new spec files (14 new tests × 2 browsers = 28 new E2E tests).
3. **Docker placeholder images** — Activated real Dockerfile builds for `agent-a` and `agent-a-english`.

---

## Changes Made

### Python — Import Bug Fixes

Corrected `version_a.agent.*` imports (which don't work due to dashes in folder name) across 3 files:

| File | Fix |
|------|-----|
| `version-a/agent/tools/routing.py` | `from agents.*` / `from services.*` |
| `version-a/agent/services/human_escalation.py` | `from services.transcript_store` |
| `version-a/agent/agents/orchestrator.py` | `from tools.routing` |

### Python — New Test Files

| File | Tests |
|------|-------|
| `version-a/agent/tests/test_agent_constants.py` | 8 |
| `version-a/agent/tests/test_routing.py` | 8 |
| `version-a/agent/tests/test_services.py` | 6 |

### Frontend — data-testid Attributes

| Component | Attributes Added |
|-----------|-----------------|
| `TradeoffPanel.tsx` | `data-testid="tradeoff-panel"`, `data-testid="tradeoff-dismiss"` |
| `FlowVisualizer.tsx` | `data-testid="flow-visualizer"`, `data-testid={`flow-step-${step.id}`}` |
| `EscalationBanner.tsx` | `data-testid="escalation-banner"` |
| `TeacherObserver.tsx` | `data-testid="teacher-inject-input"`, `data-testid="teacher-inject-submit"` |

### Frontend — Student Page

`frontend/app/student/page.tsx`: Added `?tradeoff=<trigger>` URL param support.
When a valid `TradeoffTrigger` is provided, renders `<TradeoffPanel>` directly (dismissable).
Enables E2E testing of TradeoffPanel without requiring audio/WebRTC.

### Frontend — TeacherObserver

Changed injection UI to always be visible for version-b (not hidden behind `connected` flag).
Submit button is disabled when not connected. Changed input to `<textarea>` for multi-line hints.

### Frontend — New E2E Specs

| File | Tests (each browser) |
|------|---------------------|
| `frontend/tests/e2e/flow.spec.ts` | 4 |
| `frontend/tests/e2e/tradeoff.spec.ts` | 5 |
| `frontend/tests/e2e/teacher.spec.ts` | 5 |

### Docker

Activated real Dockerfile builds for `agent-a` and `agent-a-english`:
- Removed `image: python:3.11-slim` placeholder
- Removed `time.sleep(86400)` placeholder command
- Uncommented `build: context: ./version-a/agent/Dockerfile` sections

---

## Test Counts After Plan 4

| Layer | Before | Added | After |
|-------|--------|-------|-------|
| Version A unit | 15 | +21 | 36 |
| Shared/v-b unit | 74 | 0 | 74 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 14 | +28 | 42 |
| **Total** | **117** | **+49** | **166** |

---

## Verification

```bash
# Version A unit tests (36 pass)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  --with "asyncpg>=0.29.0" \
  pytest version-a/agent/tests/ -v

# Playwright E2E (42 pass across chromium + firefox)
cd frontend && npm run test:e2e
```
