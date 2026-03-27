# Unit Test Review

Audit unit tests for quality, coverage, and TDD compliance.

**Ticket (optional):** $ARGUMENTS

---

## Step 1 — Find Test Files

```bash
git diff main...HEAD --name-only | grep -E "\.(spec|test)\."
```

Read each test file.

## Step 2 — Query Test Standards

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "testing unit test patterns" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

## Step 3 — Review Each Test File

For each file check:
- [ ] Describe blocks match class/function being tested
- [ ] Test names describe behavior, not implementation
- [ ] `test.each()` for repetitive patterns
- [ ] Happy path, null/empty, boundary values, error cases covered
- [ ] Mocks only at system boundaries
- [ ] Assertions are specific (not just `toBeTruthy()`)
- [ ] Tests are independent (no shared state)

## Output

```markdown
# Unit Test Review: $ARGUMENTS

## Issues
### Critical
- `file.spec.ts:45` — <issue>

### Missing Coverage
- No test for null input to <function>

### Suggestions
- Lines 12–45 repeated 4x — use test.each()

## VERDICT: PASS / NEEDS IMPROVEMENT
```
