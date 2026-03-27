# Review Code

Review the implementation against standards, solution, and team review patterns.

**Ticket (optional):** $ARGUMENTS

---

## Step 1 — Get Changed Files

```bash
git diff main...HEAD --name-only
git diff main...HEAD
```

## Step 2 — Retrieve Solution Context

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "$ARGUMENTS" --project $AGENTS_PROJECT
```

## Step 3 — Query Review Patterns

For each changed file:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<file path>" \
  --collection reviews --project $AGENTS_PROJECT --top 5 --rerank
```

## Step 4 — Query Standards

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "code quality" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

## Step 5 — Review

Evaluate against:
- **Correctness** — matches solution, satisfies ACs, handles null/errors
- **Tests** — every behavior tested, edge cases covered, `test.each()` for repetition
- **Team Patterns** — surface relevant ReviewPatterns with PR reference
- **Security** — input validation, auth checks, no secrets logged
- **Performance** — no N+1, no unindexed queries in hot paths
- **Scope** — only ticket scope, no unrelated changes

## Output

```markdown
# Code Review: $ARGUMENTS

## Issues

### Critical
- `file.ts:42` — <issue> [Team pattern PR #NNN: "<past comment>"]

### Warnings
- `file.ts:88` — <issue>

### Suggestions
- <improvement>

## Test Coverage
- Missing: <uncovered cases>

## VERDICT: APPROVED / CHANGES REQUESTED
```
