# Review Tests — Audit Test Quality and Coverage

Audit existing tests on the current branch against team standards, review
patterns, and coverage expectations. Does NOT write tests — use `/write-tests`
for that. This command gates test quality before the PR is raised.

**Usage:**
- `/review-tests` — audit all test files changed on the current branch
- `/review-tests path/to/file.spec.ts` — audit a specific test file
- `/review-tests PROJ-123` — audit tests for a specific ticket branch

**Target:** $ARGUMENTS

---

## Step 1 — Identify Scope

**If $ARGUMENTS is a file path:** Read that test file directly.

**If $ARGUMENTS is a ticket ID or empty:**
```bash
git diff main...HEAD --name-only | grep -E '\.(spec|test)\.(ts|js|py|rb|go|java)$'
```

Also collect the source files under test:
```bash
git diff main...HEAD --name-only | grep -vE '\.(spec|test)\.'
```

---

## Step 2 — Query Test Standards and Review History

```bash
# Team testing standards
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "unit test coverage standards mock boundary" \
  --collection standards --project $AGENTS_PROJECT --top 8

# Past review comments about test quality
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "missing test edge case incomplete coverage" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 12

# Module-specific test patterns
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module name> test spec" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 8
```

---

## Step 3 — Read Source and Test Files

For each changed source file:
1. Read the source file — identify every function, branch, and error path
2. Read the corresponding test file
3. Map source code paths to test coverage

Do NOT produce findings before reading both files.

---

## Step 4 — Audit Each Test File

### 4.1 Structure and Organization
- [ ] `describe()` blocks map to classes or functions, not file names
- [ ] Test names describe behavior: `should return X when Y`, not `test 1`
- [ ] No `describe` blocks with a single test (merge or expand)
- [ ] No deeply nested describes (max 3 levels)

### 4.2 Coverage
- [ ] Every public function has at least one test
- [ ] Every `if`/`else` branch covered (not just the happy path)
- [ ] Null, undefined, empty string, empty array inputs tested
- [ ] Boundary values tested (0, 1, max, negative)
- [ ] Every thrown exception / rejection has a test
- [ ] Every early return / guard clause has a test

### 4.3 Mock Quality
- [ ] Mocks only at system boundaries (DB, external APIs, file system)
- [ ] Mocks match the actual interface (no stubbed-out shapes)
- [ ] No mocking of the module under test itself
- [ ] Mock setup is in `beforeEach`, not scattered in individual tests

### 4.4 Assertion Quality
- [ ] Assertions are specific: `toBe`, `toEqual`, `toHaveBeenCalledWith`
- [ ] No `toBeTruthy()` or `toBeDefined()` where a specific value is known
- [ ] Error assertions check the message, not just the type
- [ ] Side effect assertions use `toHaveBeenCalledWith` (not just `toHaveBeenCalled`)

### 4.5 Test Independence
- [ ] No shared mutable state between tests
- [ ] `beforeEach` resets all mocks
- [ ] Tests pass in any order
- [ ] No `test.only()` or `it.skip()` left in

### 4.6 Patterns
- [ ] `test.each()` used for 3+ similar cases with different inputs
- [ ] No copy-pasted test blocks that differ only by data
- [ ] Constants and types imported from source — not redefined in tests

### 4.7 Past Review Patterns (from ReviewPatterns KB)
- Check each pattern found in Step 2 against the test files

---

## Step 5 — Produce the Review Report

```markdown
## Test Review: $ARGUMENTS

### Verdict
PASS / NEEDS IMPROVEMENT / BLOCK

### Summary
<1–2 sentences: overall test quality and readiness>

### Critical Issues (block PR)
- [ ] **[CRITICAL]** `file.spec.ts:45` — <issue> — <what to do>

### Coverage Gaps (should fix)
- [ ] **[COVERAGE]** `file.ts:fn()` — no test for <null input / error path / edge case>

### Quality Issues (should fix)
- [ ] **[QUALITY]** `file.spec.ts:23` — <issue, e.g. assertion too weak>

### Suggestions
- [ ] **[SUGGESTION]** Lines 12–45 repeated — use `test.each()`

### Confirmed Good
- <what was done well — be specific>

### Coverage Summary
| Function | Happy | Null/Empty | Error | Boundary |
|----------|-------|------------|-------|----------|
| `fnName` | ✅ | ❌ | ✅ | ❌ |
```

---

## Checklist

```
Review Tests — $ARGUMENTS:
- [ ] All changed test files identified
- [ ] Source files read to map coverage
- [ ] Team test standards queried
- [ ] Review history queried for this module
- [ ] Structure and organization reviewed
- [ ] Coverage gaps identified (branches, nulls, errors, boundaries)
- [ ] Mock quality reviewed
- [ ] Assertion quality reviewed
- [ ] Past review patterns checked
- [ ] Report produced with verdict
```
