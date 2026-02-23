# Plan 3: Full Integration Test Suite (Real API Keys)

## Context

Plan-2 completed all unit tests (74 passing, all mocked). Plan-3 adds integration tests
that hit the real APIs — Claude Haiku, Claude Sonnet 4.6, GPT-4o, OpenAI TTS, and
OpenAI Realtime — following the patterns from the reference project.

## What Was Added

### Integration test directories (3 packages)
- `shared/guardrail/tests/integration/` — 4 tests hitting real OpenAI moderation API
- `shared/specialists/tests/integration/` — 6 tests: classifier (Haiku), math (Sonnet 4.6), history + english (GPT-4o)
- `version-b/backend/tests/integration/` — 4 tests: full pipeline math/history, session token, health

### Pattern used (reference project approach)
- `conftest.py` captures real API keys at module-load time (before monkeypatching)
- `@pytest.fixture(autouse=True)` skips the entire file if keys are absent/fake
- `@pytest.mark.integration` + `@pytest.mark.timeout(N)` on each test
- Session router singleton `_openai` reset in version-b conftest

### Stream aliases added to specialist files
- `specialists/math.py`: `stream_math_response = answer_math_question`
- `specialists/history.py`: `stream_history_response = answer_history_question`
- `specialists/english.py`: `stream_english_response = answer_english_question`
These aliases fix a latent bug where `orchestrator.py` imported non-existent function names.

### Moved test
- `test_route_intent_live` removed from `shared/specialists/tests/test_classifier.py`
- Equivalent coverage now in `shared/specialists/tests/integration/test_specialists_live.py`

### Playwright upgraded
- Added `fullyParallel: true`, `forbidOnly`, `retries` (CI-aware)
- Added `reporter: "html"` and `trace: "on-first-retry"`
- Added Firefox project alongside Chromium

### Deps added
- `pytest-timeout>=2.3.0` added to all three test dependency groups
- `integration` marker added to guardrail's `pyproject.toml`

## Test Count Summary

| Layer | Count |
|-------|-------|
| Unit (Python) | 74 |
| Integration (Python) | 14 |
| E2E (Playwright) | 8–16 (Chromium + Firefox) |
| **Total** | **96–104** |

## Expected Outcomes

**With real keys:**
- `shared/guardrail` integration: 4 passed
- `shared/specialists` integration: 6 passed (~2–4 minutes due to streaming)
- `version-b/backend` integration: 4 passed (ASGI transport, no Docker needed)

**Without real keys:**
- Integration tests: SKIPPED (not FAILED) — CI-safe
- Total: 74 unit passed, 14 integration skipped

## Run Commands

```bash
# Unit only (no keys needed)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v -m "not integration"
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test pytest tests/ -v -m "not integration"
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev pytest tests/ -v -m "not integration"

# Integration only (keys required)
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test \
  pytest tests/integration/ -v -s -m integration

PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev \
  pytest tests/integration/ -v -s -m integration

# Playwright E2E
cd frontend && npx playwright install --with-deps chromium firefox
npm run test:e2e
```

## Files Changed

| File | Action |
|------|--------|
| `shared/guardrail/pyproject.toml` | Added `pytest-timeout`, `integration` marker |
| `shared/specialists/pyproject.toml` | Added `pytest-timeout` |
| `version-b/backend/pyproject.toml` | Added `pytest-timeout` |
| `shared/specialists/math.py` | Added `stream_math_response` alias |
| `shared/specialists/history.py` | Added `stream_history_response` alias |
| `shared/specialists/english.py` | Added `stream_english_response` alias |
| `shared/guardrail/tests/integration/__init__.py` | Created (empty) |
| `shared/guardrail/tests/integration/conftest.py` | Created (key capture pattern) |
| `shared/guardrail/tests/integration/test_guardrail_live.py` | Created (4 tests) |
| `shared/specialists/tests/integration/__init__.py` | Created (empty) |
| `shared/specialists/tests/integration/conftest.py` | Created (key capture pattern) |
| `shared/specialists/tests/integration/test_specialists_live.py` | Created (6 tests) |
| `shared/specialists/tests/test_classifier.py` | Removed `test_route_intent_live` (moved) |
| `version-b/backend/tests/integration/__init__.py` | Created (empty) |
| `version-b/backend/tests/integration/conftest.py` | Created (key capture + client fixture) |
| `version-b/backend/tests/integration/test_orchestrator_live.py` | Created (4 tests) |
| `frontend/playwright.config.ts` | Upgraded with multi-browser + CI config |
| `CLAUDE.md` | Updated integration test commands |
| `PLAN-3.md` | This file |
