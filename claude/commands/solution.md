# Solution Approach

Draft a codebase-grounded solution approach for a ticket and store in Weaviate.

**Ticket:** $ARGUMENTS

---

## Step 1 — Gather Ticket Details

If Jira MCP is available:
```
mcp__mcp-atlassian__jira_get_issue(issue_id: "$ARGUMENTS")
```

Otherwise ask user for: title, description, acceptance criteria.

## Step 2 — Retrieve RAG Context

Extract 3–5 key concepts from the ticket. For each:

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<concept>" \
  --project $AGENTS_PROJECT --top 5 --rerank
```

Query standards:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<concept>" \
  --collection standards --project $AGENTS_PROJECT --top 3
```

## Step 3 — Generate Solution

Produce a solution approach covering:

1. **Summary** — 2–3 sentences
2. **Files to change** — exact paths from RAG + what changes
3. **New files** — purpose
4. **Implementation steps** — ordered, concrete
5. **Edge cases & risks**
6. **Testing plan (TDD)** — failing tests first, edge cases, error cases
7. **Dependencies**

## Step 4 — Store in Weaviate

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --store-solution \
  --ticket "$ARGUMENTS" \
  --title "<title>" \
  --approach-file solution_$ARGUMENTS.md \
  --project $AGENTS_PROJECT
```

## Output Format

```markdown
# Solution Approach: $ARGUMENTS

## Summary
<2–3 sentences>

## Files to Change
- `path/to/file.ts` — what changes

## New Files
- `path/to/new-file.ts` — purpose

## Implementation Steps
1. Write failing tests for <behavior>
2. Implement <X>

## Edge Cases & Risks
- <risk>

## Testing Plan
- Unit: <test case>

## Dependencies
- None / <list>
```

## Checklist

```
Solution Approach — $ARGUMENTS:
- [ ] Ticket details gathered
- [ ] RAG queried (codebase + standards)
- [ ] Solution generated
- [ ] Stored in Weaviate
```
