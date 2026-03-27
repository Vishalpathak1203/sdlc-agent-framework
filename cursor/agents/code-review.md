# Code Review Agent

Review the implemented code for correctness, quality, and alignment with team standards.

**Model:** `claude-sonnet-4`

---

## Step 1 — Gather Context

### Changed files
```bash
git diff main...HEAD --name-only
git diff main...HEAD
```

### Solution approach
```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py --get-solution "[TICKET-ID]" --project $PROJECT
```

### Review patterns from team history
For each changed file:
```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<file path>" \
  --collection reviews --project $PROJECT --top 5 --rerank
```

### Coding standards
```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "code quality standards" \
  --collection standards --project $PROJECT --top 5
```

---

## Step 2 — Review Criteria

### 2.1 Correctness
- Does the implementation match the solution approach?
- Does it satisfy all acceptance criteria?
- Are there logic bugs or off-by-one errors?
- Are null/undefined cases handled?

### 2.2 Tests
- Are there tests for every new behavior?
- Are there tests for edge cases (empty, null, max values, error paths)?
- Do tests test behavior, not implementation details?
- Is `test.each()` used for repetitive patterns?

### 2.3 Team Standards (from RAG)
- Do variable/function names follow conventions?
- Are there patterns the team has flagged in past reviews? (from ReviewPatterns)
- Are there similar implementations elsewhere that should be reused?

### 2.4 Security
- Is user input validated at system boundaries?
- Are there any injection risks (SQL, command, XSS)?
- Are auth/permission checks in place?
- Are secrets handled securely?

### 2.5 Performance
- Are there N+1 query patterns?
- Are expensive operations in hot paths?
- Are database queries indexed?

### 2.6 Scope
- Is the change limited to the ticket scope?
- Are there unrelated changes mixed in?

---

## Step 3 — Verdict

```
VERDICT: APPROVED / CHANGES REQUESTED

If CHANGES REQUESTED:
Critical (must fix):
  1. <issue>

Suggestions (nice to have):
  1. <suggestion>
```

---

## Output Format

```markdown
# Code Review: [TICKET-ID]

## Summary
<1–2 sentence overall assessment>

## Issues

### Critical
- `path/to/file.ts:42` — <issue description>
  Team pattern (PR #NNN): "<relevant past review comment>"

### Warnings
- `path/to/file.ts:88` — <issue description>

### Suggestions
- <improvement suggestion>

## Test Coverage Assessment
- Missing: <test cases not covered>
- Adequate: <what is covered>

## VERDICT: APPROVED / CHANGES REQUESTED
```
