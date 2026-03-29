# Write Tests — Unit Test Writer & Fixer

Write or fix unit tests for the given file(s), ticket, or failing test output.
Pulls in repo standards, Weaviate review patterns, and past feedback to produce
tests that will pass review.

**Usage:**
- `/write-tests path/to/file.ts` — write tests for a specific file
- `/write-tests PROJ-123` — write tests for files changed in a ticket branch
- `/write-tests` (no args) — fix currently failing tests

**Target:** $ARGUMENTS

---

## Step 1 — Identify the scope

**If $ARGUMENTS is a file path:**
Read the file. Identify the module type (API service/controller/guard vs. UI composable/store/component).

**If $ARGUMENTS is a ticket ID:**
```bash
git diff main...HEAD --name-only | grep -E '\.(ts|tsx|vue|py|rb|go|java)$' | grep -v '\.spec\.' | grep -v '\.test\.'
```
Use the listed files as the scope.

**If $ARGUMENTS is empty (fix-failing mode):**
Run the test suite and parse the failure output to identify which spec files and test cases are failing. Go directly to Step 5.

---

## Step 2 — Query Weaviate: standards + review patterns

```bash
# Testing standards
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "unit test coverage mock" --collection standards \
  --project $AGENTS_PROJECT --top 8

# Past review patterns about tests
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "missing test edge case mock" --collection reviews \
  --project $AGENTS_PROJECT --top 15 --rerank

# Module-specific review patterns
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module or feature name> test" --collection reviews \
  --project $AGENTS_PROJECT --top 10 --rerank
```

---

## Step 3 — Read ALL module files before writing tests

Read ALL files in the same module directory:
- `*.dto.ts` / `*.schema.*` — import types for mock data shape; do NOT redefine inline if a type exists
- `*.constants.ts` — **import constants for assertions** (e.g. `expect(error.message).toBe(ERROR_MESSAGE_CONSTANT)`); never hardcode the string
- Existing `*.spec.ts` — understand mock setup, naming, `test.each()` usage

Never redefine a constant or type in a test file that already exists in the module. Import it.

---

## Step 4 — Plan the test cases

For each file in scope, list every case to cover:

| Category | What to test |
|----------|-------------|
| **Happy path** | Core logic with valid inputs, expected return values |
| **Edge cases** | Empty arrays, null/undefined, boundary values, optional fields |
| **Error / failure** | Thrown exceptions, rejected promises, validation failures |
| **Branching** | Each `if`/`else` branch, guard clauses, early returns |
| **Side effects** | Calls to dependencies (services, stores, composables) |

**Rules:**
- Use `test.each()` for repetitive patterns with different inputs — reduces duplication
- Do NOT use `test.each()` when tests require unique setup/teardown or validate completely different behaviors
- Group with `describe()` blocks matching the function/method name
- Test names must describe behavior: `should return empty array when no listings found`, not `test 1`
- Always test error states; never leave the error branch uncovered
- Prefer `toBe` for primitives, `toEqual` for objects, `toHaveBeenCalledWith` for mock assertions

---

## Step 5 — Write / fix the tests

### Writing new tests

Locate or create the spec file sibling to the source file.

Structure:
```
describe('<ClassName or function name>', () => {
  // shared setup: beforeEach, mocks

  describe('<method or scenario group>', () => {
    it('should <expected behavior> when <condition>', () => { ... })
    it('should <expected behavior> when <condition>', () => { ... })
  })
})
```

### Fixing failing tests

For each failing test:
1. Read the error message and stack trace carefully
2. Read the source file and the spec file
3. Determine root cause:
   - **Mock mismatch** — mock returns wrong shape, missing method
   - **Assertion wrong** — expected value outdated after code change
   - **Import broken** — path changed, module restructured
   - **Async not awaited** — missing `await`, wrong async handling
4. Fix the spec file (or source if the source has a bug — note this clearly)
5. Do NOT delete tests to make failures go away — fix the underlying cause

---

## Step 6 — Run the tests and confirm they pass

```bash
# Run only the affected spec file — fast feedback loop
<test-runner> <spec-file-name>

# If all pass, run the full suite to catch regressions
<test-all-command>
```

If any test still fails: go back to Step 5. Do not proceed with a failing suite.

---

## Step 7 — Self-check before finishing

```
Test Quality Checklist:
- [ ] Every changed/new function has at least one test
- [ ] Happy path covered
- [ ] At least one error/failure case covered
- [ ] Edge cases covered (null, empty, boundary)
- [ ] test.each() used where there are 3+ similar cases
- [ ] All mocks match the actual interface (no shortcuts)
- [ ] Describe/it names are descriptive behavior statements
- [ ] No tests deleted to fix failures — root cause fixed instead
- [ ] Constants imported from source — not hardcoded or redefined in tests
- [ ] Types imported from source — not redefined inline
- [ ] Full test suite passes
```

Report which files were created/modified and a summary of what cases are covered.
