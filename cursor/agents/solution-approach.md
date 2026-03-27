# Solution Approach Agent

Draft a detailed, codebase-grounded solution for a Jira ticket and store it in Weaviate.

**Model:** `claude-haiku-3-5`

---

## Step 1 — Gather Ticket Details

### Option A: Jira MCP (if configured)

```
mcp__mcp-atlassian__jira_get_issue(issue_id: "[TICKET-ID]")
```

Extract: title, description, acceptance criteria, labels, linked issues.

### Option B: Manual

Ask the user to paste: ticket title, description, acceptance criteria.

---

## Step 2 — Retrieve RAG Context

Extract 3–5 key concepts from the ticket (module names, feature areas, entity names).

For each concept:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<concept>" \
  --project $PROJECT --top 5 --rerank
```

Also query coding standards for relevant patterns:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<concept>" \
  --collection standards --project $PROJECT --top 3
```

Collect all results as codebase context.

**Example concepts for "Add pagination to the orders list API":**
- `orders list endpoint`
- `pagination helper`
- `API response schema`
- `database query offset limit`

---

## Step 3 — Generate the Solution Approach

Using ticket details + RAG context, produce a solution covering:

1. **Summary** — 2–3 sentence overview
2. **Files to change** — exact file paths + what changes in each
3. **New files** — any new files + purpose
4. **Implementation steps** — ordered, concrete steps
5. **Edge cases & risks** — what could go wrong
6. **Testing plan (TDD)** — concrete test cases: happy path, edge cases, error cases
7. **Dependencies** — new packages or migrations needed

Stay grounded in actual RAG context. Use the exact file paths returned. Do not invent APIs.

---

## Step 4 — Store in Weaviate

Save the solution as a markdown file, then store it:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py \
  --store-solution \
  --ticket "[TICKET-ID]" \
  --title "<ticket title>" \
  --approach-file solution_[TICKET-ID].md \
  --project $PROJECT
```

---

## Step 5 — Update Jira (optional, if MCP configured)

```
mcp__mcp-atlassian__jira_add_comment(
  issue_id: "[TICKET-ID]",
  comment: "Solution approach drafted and stored. Ready for review."
)
mcp__mcp-atlassian__jira_transition_issue(
  issue_id: "[TICKET-ID]",
  transition: "In Progress"
)
```

---

## Output Format

```markdown
# Solution Approach: [TICKET-ID]

## Summary
<2–3 sentences>

## Files to Change
- `path/to/file.ts` — what changes and why

## New Files
- `path/to/new-file.ts` — purpose

## Implementation Steps
1. Write failing tests for <feature>
2. Implement <X> in <file>
3. ...

## Edge Cases & Risks
- <what could go wrong>

## Testing Plan
- Unit: test <behavior> in <file>
- Integration: <scenario>

## Dependencies
- None / <list any>
```

---

## Checklist

```
Solution Approach — [TICKET-ID]:
- [ ] Ticket details collected (via MCP or manual)
- [ ] RAG queried for 3–5 key concepts (codebase + standards)
- [ ] Solution generated (summary, files, steps, edge cases, tests, deps)
- [ ] Stored in Weaviate via --store-solution
- [ ] Jira updated (optional)
```
