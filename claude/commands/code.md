# Code Agent — TDD Implementation

Implement the approved solution for a ticket using Test-Driven Development.

**Ticket:** $ARGUMENTS

---

## Step 1 — Retrieve Approved Solution

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "$ARGUMENTS" --project $AGENTS_PROJECT
```

Verify status is `approved`. Stop if `draft` — run `/solution-review $ARGUMENTS` first.

## Step 2 — RAG Context per File

For each file in "Files to Change":

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<file or feature>" \
  --project $AGENTS_PROJECT --top 5 --rerank
```

## Step 3 — TDD Red: Write Failing Tests

For each test case in the testing plan:
1. Read the existing test file
2. Write the failing test
3. Confirm it fails: `pnpm test <file> --testNamePattern "<name>"`

## Step 4 — TDD Green: Implement

For each failing test:
1. Write minimum code to make it pass
2. Run: `pnpm test <file>`
3. Verify pass

## Step 5 — TDD Refactor

After all tests pass:
- Remove duplication
- Apply naming conventions from RAG/standards context
- Run: `pnpm test` (all must still pass)

## Step 6 — Quality Gates

```bash
pnpm test && pnpm lint && pnpm type-check
```

All must pass. Fix failures before committing.

## Step 7 — Commit

```bash
git add <specific files>
git commit -m "$ARGUMENTS: type: description"
```

## Checklist

```
Code Agent — $ARGUMENTS:
- [ ] Solution retrieved and status = approved
- [ ] RAG context fetched for each file
- [ ] Tests written first (red)
- [ ] Implementation makes tests pass (green)
- [ ] Refactored (no behavior change)
- [ ] Full test suite passes
- [ ] Lint + type-check pass
- [ ] Committed with ticket reference
```
