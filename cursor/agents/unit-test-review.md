# Unit Test Review Agent

Audit existing or newly written unit tests for quality, coverage, and TDD compliance.

**Model:** `claude-sonnet-4`

---

## Step 1 — Gather Test Files

```bash
git diff main...HEAD --name-only | grep -E "\.(spec|test)\."
```

For each test file, read its contents.

---

## Step 2 — Query Test Standards

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "testing standards unit test patterns" \
  --collection standards --project $PROJECT --top 5
```

---

## Step 3 — Review Criteria

For each test file:

### 3.1 Structure
- [ ] Describe blocks match the class/function being tested
- [ ] Test names describe the behavior, not the implementation
- [ ] `test.each()` used for repetitive input variations (not copy-paste)
- [ ] Setup/teardown uses `beforeEach`/`afterEach` appropriately

### 3.2 Coverage
- [ ] Happy path tested
- [ ] Empty/null/undefined input tested
- [ ] Boundary values tested (0, -1, max)
- [ ] Error/exception cases tested
- [ ] Async errors tested (rejected promises)

### 3.3 Quality
- [ ] Tests test behavior, not implementation details
- [ ] No testing of private methods directly
- [ ] Mocks used only at system boundaries (external services, DB)
- [ ] Assertions are specific (not just `toBeTruthy()`)
- [ ] Each test has exactly one reason to fail

### 3.4 Independence
- [ ] Tests do not depend on execution order
- [ ] No shared mutable state between tests
- [ ] Each test sets up its own data

---

## Step 4 — Verdict

```
TEST QUALITY: PASS / NEEDS IMPROVEMENT

Issues:
- <specific issue with file + line reference>

Missing test cases:
- <behavior not covered>
```

---

## Output Format

```markdown
# Unit Test Review: [TICKET-ID]

## Files Reviewed
- `path/to/file.spec.ts`

## Issues Found

### Critical (test suite doesn't provide confidence)
- `file.spec.ts:45` — Tests implementation detail (calls private method directly)

### Missing Coverage
- No test for null input to `processPayment(null)`
- No test for network timeout error case

### Suggestions
- Lines 12–45 repeat the same pattern 4x — use `test.each()`

## VERDICT: PASS / NEEDS IMPROVEMENT
```
