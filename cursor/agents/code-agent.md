# Code Agent — TDD Implementation

Implement the approved solution using Test-Driven Development.

**Model:** `claude-haiku-3-5`

---

## Step 1 — Retrieve Approved Solution

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py \
  --get-solution "[TICKET-ID]" --project $PROJECT
```

Verify status is `approved`. If `draft`, stop and ask for solution review first.

---

## Step 2 — RAG Context for Each File

For each file listed in "Files to Change", query the codebase:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<file path or feature name>" \
  --project $PROJECT --top 5 --rerank
```

Also query for existing patterns:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<pattern to follow>" \
  --collection standards --project $PROJECT --top 3
```

---

## Step 3 — Write Failing Tests First (TDD Red)

For each test case in the testing plan:

1. Read the existing test file (if any)
2. Write the failing test — it must fail before implementation
3. Verify it fails by running the test suite

```bash
# Run specific test file to confirm failure
pnpm test <test-file-path> --testNamePattern "<test name>"
```

**Test structure (follow existing patterns from RAG context):**
- Describe block names match the class/function being tested
- Each test case covers exactly one behavior
- Use `test.each()` for repetitive cases with different inputs

---

## Step 4 — Implement to Make Tests Pass (TDD Green)

For each failing test:

1. Read the file to implement (using RAG context for patterns)
2. Write the minimum code to make the test pass
3. Run the test — verify it now passes

```bash
pnpm test <test-file-path>
```

Do not add features not required by the tests.

---

## Step 5 — Refactor (TDD Refactor)

After all tests pass:
- Remove duplication
- Apply naming conventions from coding standards
- Ensure the code matches patterns found in RAG context
- Do NOT change behavior — tests must still pass

---

## Step 6 — Run Full Test Suite

```bash
pnpm test
pnpm lint
pnpm type-check
```

All must pass before proceeding.

---

## Step 7 — Commit (Safe Commit)

Follow [safe-commit.md](safe-commit.md).

---

## Implementation Rules

- Read existing code before modifying — use RAG context + direct file reads
- Match existing code style exactly (indentation, naming, import order)
- Do not add comments unless logic is non-obvious
- Do not add features beyond the ticket scope
- Do not change unrelated code

---

## Checklist

```
Code Agent — [TICKET-ID]:
- [ ] Approved solution retrieved from Weaviate
- [ ] RAG context fetched for each file to change
- [ ] Failing tests written first (TDD Red)
- [ ] Implementation makes tests pass (TDD Green)
- [ ] Refactored without breaking tests
- [ ] Full test suite passes
- [ ] Lint + type-check pass
- [ ] Changes committed
```
