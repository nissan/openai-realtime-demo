# Plan 10: FlowVisualizer E2E Highlighting, README & Housekeeping

> Previous plans: PLAN.md → PLAN-9.md (all complete, 216 tests all green)
> Status: **COMPLETE**

---

## Context

Plan 9 completed all P1/P2 items and left four items deferred. Three are explicitly
outside POC scope (CSRF, Frontend Langfuse, PaaS configs). The remaining one —
**FlowVisualizer activeStep E2E test** — was deferred because it "requires running
full agent stack." This plan resolves it without the agent stack by seeding
`activeStep` from a URL param (`?activeStep=xxx`), enabling pure-frontend assertion.

Two housekeeping items are also addressed:
- **README.md** was frozen at Plan 7 figures (46/24/52/14/64 = ~200 tests).
- **`.gitignore`** was missing Playwright output directories.

---

## Changes Made

### Step 1 — `.gitignore`: Add Playwright output directories

Added to the `# Testing` section:

```
# Playwright output
frontend/playwright-report/
frontend/test-results/
```

### Step 2 — `FlowVisualizer.tsx`: Add `data-active` attribute

Added `data-active` attribute to the step `div` for stable E2E assertions:

```tsx
<div
  data-testid={`flow-step-${step.id}`}
  data-active={activeStep === step.id ? "true" : undefined}
  className={...}
>
```

Using `undefined` (not `"false"`) keeps inactive steps clean.

### Step 3 — `StudentPage`: Seed `activeStep` from URL param

```typescript
const initialStep = searchParams.get("activeStep") ?? undefined;
const [activeStep, setActiveStep] = useState<string | undefined>(initialStep);
```

Real pipeline events still update it normally; the URL param only seeds the initial value.

### Step 4 — `pipeline.spec.ts`: 3 new activeStep highlighting tests

Added inside the existing `FlowVisualizer pipeline steps` describe block:

1. Active step highlighted when seeded via URL param (version-b)
2. Inactive steps have no `data-active` attribute when another step is active
3. Active step highlighted for version-a (STT step)

These 3 tests × 2 desktop browsers = **+6 E2E tests**.

### Step 5 — `README.md`: Update test counts and plan links

- Test counts table updated: Plan 7 → Plan 10 figures
- Version A comment: 46 → 49 tests
- Version B comment: 52 → 54 tests
- E2E comment: 64 → 78 tests
- Plans list extended to PLAN-10.md
- Architecture section: added CI workflow + rate limiting mention

### Step 6 — `CLAUDE.md`: Update E2E count

Updated test count header: Plan 9 ~216 total → Plan 10 ~222 total (78 E2E).

### Step 7 — `PLAN-10.md`: Created this file

---

## Files Modified

| File | Change |
|------|--------|
| `.gitignore` | Added `frontend/playwright-report/` + `frontend/test-results/` |
| `frontend/components/demo/FlowVisualizer.tsx` | Added `data-active` attribute to step `div` |
| `frontend/app/student/page.tsx` | Seeded `activeStep` state from `?activeStep` URL param |
| `frontend/tests/e2e/pipeline.spec.ts` | +3 activeStep highlighting tests |
| `README.md` | Updated test counts (Plan 7→10), plan links, CI/rate limit mention |
| `CLAUDE.md` | Updated E2E count 72→78 |
| `PLAN-10.md` | **Created** at project root |

---

## Test Counts After Plan 10

| Layer | Before | Delta | After |
|-------|--------|-------|-------|
| Version A unit | 49 | 0 | 49 |
| Shared unit | 27 | 0 | 27 |
| Version B unit | 54 | 0 | 54 |
| Python integration | 14 | 0 | 14 |
| Playwright E2E | 72 | +6 | 78 |
| **Total** | **216** | **+6** | **~222** |

---

## What Is NOT in Plan 10 (Permanently deferred — outside POC scope)

- **CSRF protection** — requires session cookie/token pattern
- **Frontend Langfuse observability** — major dep + cross-origin OTEL complexity
- **PaaS deployment configs** (Render/Railway/Fly) — outside POC scope
