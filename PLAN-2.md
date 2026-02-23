# Plan 2: Run & Complete Test Suite

**Date:** 2026-02-23
**Status:** COMPLETED

## Objective

Run the 9 existing test files (45 Python unit tests) for the first time, identify and fix all failures, add missing Version B test coverage (~12 new tests), and verify all suites exit 0.

---

## Failures Found & Root Causes

### Issue 1: Hatchling packaging error (shared packages)

**Packages affected:** `shared/guardrail`, `shared/observability`, `shared/specialists`

**Error:**
```
ValueError: Unable to determine which files to ship inside the wheel
The most likely cause of this is that there is no directory that matches the name of your project (guardrail).
```

**Root cause:** Each shared package has its source files directly at the project root (e.g., `shared/guardrail/__init__.py`, `shared/guardrail/service.py`) but hatchling expects a subdirectory named after the project (e.g., `shared/guardrail/guardrail/`).

**Fix:** Added `[tool.hatch.build.targets.wheel] packages = ["."]` to each shared package's `pyproject.toml`. When the working directory is `shared/guardrail`, hatchling resolves `.` to the actual directory name `guardrail` (via `Path('.').resolve().name`), then packages everything at the root under that namespace. Also added `[tool.hatch.build] exclude = ["tests/**"]` to prevent test files being bundled in the wheel.

**Files changed:**
- `shared/guardrail/pyproject.toml`
- `shared/observability/pyproject.toml`
- `shared/specialists/pyproject.toml`

---

### Issue 2: Missing `--extra test` in test commands

**Root cause:** The `pyproject.toml` files for shared packages declare pytest under `[project.optional-dependencies]` with key `test`, but the CLAUDE.md test commands omitted the `--extra test` flag. Without it, `uv` didn't install pytest into the shared package venvs.

**Fix:** Updated all test commands to include `--extra test`:
```bash
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v
```

---

### Issue 3: Cross-package import failure for `specialists` in version-b

**Error:**
```
AttributeError: module 'specialists' has no attribute 'classifier'
```

**Root cause:** `test_full_orchestration_pipeline` used `patch("specialists.classifier.route_intent")`. Python's `unittest.mock.patch` imports `specialists.classifier` to apply the patch. Since `specialists.classifier` requires `anthropic` (not installed in version-b's venv), the import failed silently and fell back to `getattr(specialists, 'classifier')` which also failed.

**Fix:** Replaced `patch()` calls with `patch.dict(sys.modules, {...})` to inject fake module objects directly, bypassing the import chain entirely. This is the correct testing pattern when patching across package boundaries.

**File changed:** `version-b/backend/tests/test_orchestrator_route.py`

---

### Issue 4: `specialists` and `guardrail` not in PYTHONPATH for cross-package tests

**Root cause:** PYTHONPATH was set to `$(pwd)` (project root), but shared packages live under `$(pwd)/shared/`. Tests that imported `from guardrail.models import ModerationResult` or `from specialists.classifier import route_intent` would fail because Python couldn't find those packages at the project root.

**Fix:** Updated all test commands to include `$(pwd)/shared` in PYTHONPATH:
```bash
PYTHONPATH=$(pwd)/shared:$(pwd) uv run ...
```

---

### Issue 5: version-a tests would require installing livekit-agents

**Root cause:** `version-a/agent/pyproject.toml` lists `livekit-agents[openai,silero,deepgram]` as a dependency. Installing this would take minutes and require native build tools. However, the actual test files (`test_session_state.py`, `test_guarded_agent.py`) don't import from LiveKit at module level — they only need `openai` and `pydantic`.

**Fix:** Use `uv run --no-project` for version-a to skip project installation, and `--with` to install only the required test packages:
```bash
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  pytest version-a/agent/tests/ -v
```

---

## Test Commands (corrected)

```bash
cd /Users/nissan/code/openai-realtime-demo

# Shared packages
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/guardrail --extra test pytest tests/ -v
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/observability --extra test pytest tests/ -v
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory shared/specialists --extra test pytest tests/ -v -m "not integration"

# Version A (--no-project to skip heavy livekit installation)
PYTHONPATH=$(pwd)/shared:$(pwd)/version-a/agent uv run --no-project \
  --with "pytest>=8" --with "pytest-asyncio>=0.23" \
  --with "openai>=1.0.0" --with "pydantic>=2.0.0" \
  pytest version-a/agent/tests/ -v

# Version B
PYTHONPATH=$(pwd)/shared:$(pwd) uv run --directory version-b/backend --extra dev pytest tests/ -v
```

---

## New Test Files Added (Step 2)

### `version-b/backend/tests/test_session_route.py` (3 tests)
- `test_session_token_endpoint` — verifies POST /session/token returns `client_secret` + `session_id`
- `test_session_token_returns_provided_session_id` — verifies session_id echoed back
- `test_session_token_openai_error` — verifies 500 on OpenAI API failure

### `version-b/backend/tests/test_tts_route.py` (5 tests)
- `test_tts_stream_returns_chunks` — verifies StreamingResponse with PCM headers
- `test_tts_stream_job_not_found` — 404 for unknown job_id
- `test_tts_stream_job_not_ready` — 409 for pending job
- `test_tts_stream_job_error_state` — 422 for failed job
- `test_tts_stream_missing_job_id` — 422 for missing required field

### `version-b/backend/tests/test_teacher_route.py` (4 tests + 1 skipped)
- `test_escalate_returns_session_id` — verifies session_id in POST /escalate response
- `test_escalate_calls_notify_escalation` — verifies service function is called with right args
- `test_escalate_missing_required_fields` — 422 for missing session_id
- `test_escalate_with_custom_ws_base_url` — respects optional ws_base_url param
- `test_teacher_websocket_connect` — skipped (covered by Playwright E2E)

### `version-b/backend/tests/test_job_store.py` (6 tests)
- `test_store_create_and_get` — create job, retrieve by id
- `test_store_returns_none_for_missing` — None for unknown id
- `test_store_remove_job` — remove deletes from store
- `test_store_remove_missing_is_safe` — no error on missing id
- `test_store_multiple_jobs` — multiple jobs coexist
- `test_store_cleanup_removes_expired` — TTL cleanup removes old completed jobs, keeps recent + pending

---

## Final Test Results

| Package | Tests | Result |
|---------|-------|--------|
| `shared/guardrail` | 9 | ✅ 9 passed |
| `shared/observability` | 4 | ✅ 4 passed |
| `shared/specialists` | 15 (16 total, 1 integration deselected) | ✅ 15 passed |
| `version-a/agent` | 15 | ✅ 15 passed |
| `version-b/backend` | 31 passed, 1 skipped | ✅ All pass |
| **Total** | **74 pass, 1 skip** | ✅ |

---

## Architectural Decisions

### sys.modules injection over `patch()`

When mocking across package boundaries where the target package has unresolvable transitive dependencies in the test environment, use `patch.dict(sys.modules, ...)` instead of `patch("pkg.module.func")`. This avoids the need to install all transitive dependencies just for unit tests.

### `--no-project` for heavy-dependency packages

For packages with large native dependencies (like `livekit-agents`) that aren't needed by the unit tests, use `uv run --no-project --with <minimal-deps>` to install only what's actually exercised by the tests. This keeps test execution fast and avoids native build failures.

### PYTHONPATH strategy

Use `PYTHONPATH=$(pwd)/shared:$(pwd)` for all test runs so shared packages (`guardrail`, `specialists`, `observability`) are importable without requiring them to be installed in each package's separate venv.

---

## What Was NOT Tested

- Integration tests (`-m integration`) — require live API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
- Playwright E2E tests (`frontend/tests/e2e/`) — require port 3000 running + browser drivers
- `version-a/agent/agents/*.py` full pipeline — requires LiveKit server + audio infrastructure
