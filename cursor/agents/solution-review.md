# Solution Review Agent

Review a drafted solution approach for correctness, completeness, and codebase alignment.

**Model:** `claude-sonnet-4` (or opus for complex architectural decisions)

---

## Step 1 — Retrieve the Solution

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py \
  --get-solution "[TICKET-ID]" --project $PROJECT
```

If a solution file was saved locally, read it directly.

---

## Step 2 — Retrieve Ticket Details

If not already in context:
```
mcp__mcp-atlassian__jira_get_issue(issue_id: "[TICKET-ID]")
```

---

## Step 3 — Review Criteria

Evaluate the solution against each criterion. For each: PASS / FAIL / CONCERN.

### 3.1 Acceptance Criteria Coverage
- Does the solution address every acceptance criterion?
- Are there ACs not mentioned in the implementation steps?

### 3.2 Codebase Alignment
- Do the file paths actually exist? (Cross-check against RAG results)
- Are the APIs and patterns consistent with what RAG returned?
- Does the approach follow team coding standards?

### 3.3 TDD Coverage
- Are there failing tests written *before* implementation steps?
- Does the test plan cover: happy path, empty/null edge cases, error/exception cases?
- Are integration tests mentioned where needed?

### 3.4 Risk Assessment
- Are edge cases identified?
- Are there performance risks? (N+1 queries, missing indexes, large payloads)
- Are there security risks? (input validation, auth checks, data exposure)
- Are there breaking changes that need migration or coordination?

### 3.5 Scope
- Is the solution scoped to the ticket, or does it add unrequested scope?
- Are there unstated dependencies on other tickets?

---

## Step 4 — Verdict

```
VERDICT: APPROVED / CHANGES REQUESTED

If CHANGES REQUESTED, list each required change:
1. <specific change needed>
2. <specific change needed>
```

---

## Step 5 — Store Review Notes

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py \
  --update-solution "[TICKET-ID]" \
  --status "approved" \
  --review-notes "<summary of feedback>" \
  --project $PROJECT
```

---

## Output Format

```markdown
# Solution Review: [TICKET-ID]

## Review Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC Coverage | ✅ PASS | All 3 ACs addressed |
| Codebase Alignment | ⚠️ CONCERN | File X doesn't exist — check path |
| TDD Coverage | ❌ FAIL | No error case tests defined |
| Risk Assessment | ✅ PASS | Edge cases identified |
| Scope | ✅ PASS | Properly scoped |

## Issues Found

### Critical
- <must fix before coding>

### Suggestions
- <nice-to-have improvements>

## VERDICT: APPROVED / CHANGES REQUESTED
```
