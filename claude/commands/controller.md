# Controller — Ticket Pipeline Orchestrator

Run the full SDLC pipeline for a Jira ticket.

**Ticket:** $ARGUMENTS

---

## Pipeline Overview

```
Stage 1 → solution-approach   [RAG + Jira MCP]
Stage 2 → solution-review     [GATE ✋]
Stage 3 → code-agent          [RAG + TDD]
Stage 4 → code-review         [GATE ✋]
Stage 5 → raise PR
```

---

## Stage 1 — Solution Approach

### 1.1 Fetch ticket

If Jira MCP is available:
```
mcp__mcp-atlassian__jira_get_issue(issue_id: "$ARGUMENTS")
```

Otherwise ask user for title and description.

### 1.2 RAG query

Extract 3–5 key concepts from the ticket. For each:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<concept>" \
  --project $AGENTS_PROJECT --top 5 --rerank
```

Also query standards:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<concept>" \
  --collection standards --project $AGENTS_PROJECT --top 3
```

### 1.3 Generate solution

Produce:
- Summary (2–3 sentences)
- Files to change (exact paths from RAG results)
- New files (if needed)
- Implementation steps (ordered)
- Edge cases and risks
- Testing plan (TDD: failing tests first)
- Dependencies

### 1.4 Store solution

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --store-solution \
  --ticket "$ARGUMENTS" \
  --title "<title>" \
  --approach-file solution_$ARGUMENTS.md \
  --project $AGENTS_PROJECT
```

Output:
```
=== STAGE 1 COMPLETE ===
Solution stored for $ARGUMENTS.
Type "review solution" to continue.
```

---

## Stage 2 — Solution Review [GATE]

Wait for user to type **"review solution"**.

Retrieve and review the solution:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "$ARGUMENTS" --project $AGENTS_PROJECT
```

Evaluate: AC coverage, file path accuracy, TDD plan, risks, scope.

If approved:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --update-solution "$ARGUMENTS" --status approved \
  --project $AGENTS_PROJECT
```

Output:
```
=== STAGE 2 COMPLETE ===
Verdict: APPROVED
Type "write code" to proceed.
```

---

## Stage 3 — Code Agent

Wait for **"write code"**.

For each file in the solution:
1. RAG query the file/feature area
2. Write failing tests first
3. Implement to make tests pass
4. Refactor

Run after each file:
```bash
pnpm test
```

Run when all files done:
```bash
pnpm test && pnpm lint && pnpm type-check
```

Output:
```
=== STAGE 3 COMPLETE ===
Files changed: <list>
Type "review code" to proceed.
```

---

## Stage 4 — Code Review [GATE]

Wait for **"review code"**.

```bash
git diff main...HEAD
```

Query review patterns:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<changed files>" \
  --collection reviews --project $AGENTS_PROJECT --top 5 --rerank
```

Review: correctness, tests, standards, security, performance, scope.

Output:
```
=== STAGE 4 COMPLETE ===
Verdict: APPROVED / CHANGES REQUESTED
Type "raise pr" if approved.
```

---

## Stage 5 — Raise PR

Wait for **"raise pr"**.

Verify all quality gates pass:
```bash
pnpm test && pnpm lint && pnpm type-check
```

Push and create PR:
```bash
git push -u origin HEAD
gh pr create \
  --title "$ARGUMENTS: <title>" \
  --body "$(cat <<'EOF'
## Summary
<1–3 bullet summary>

## Ticket
$ARGUMENTS

## Test Plan
- [ ] Unit tests pass
- [ ] Lint passes
- [ ] Type check passes
EOF
)"
```

Output PR URL.

---

## State Tracking

When user asks "where are we?":
```
Pipeline: $ARGUMENTS
✅/🔄/⬜ Stage 1: Solution approach
✅/🔄/⬜ Stage 2: Solution review
✅/🔄/⬜ Stage 3: Code agent
✅/🔄/⬜ Stage 4: Code review
✅/🔄/⬜ Stage 5: PR raised
```

## Loop Commands

- **"revise solution"** → re-fetch solution, revise with review feedback, re-run Stage 2
- **"fix code"** → return to Stage 3 with code review notes, re-run Stage 4
