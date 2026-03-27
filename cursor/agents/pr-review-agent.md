# PR Review Agent — Respond to Reviewer Comments

Respond to human reviewer comments on your PR with context-aware, grounded replies.

**Model:** `claude-sonnet-4`

---

## Step 1 — Fetch PR Context

```
mcp__github__get_pull_request(owner: "<owner>", repo: "<repo>", pull_number: <number>)
mcp__github__get_pull_request_files(owner: "<owner>", repo: "<repo>", pull_number: <number>)
mcp__github__get_pull_request_comments(owner: "<owner>", repo: "<repo>", pull_number: <number>)
```

Identify all unresolved (non-resolved) review comments.

---

## Step 2 — Retrieve Solution Context

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py --get-solution "[TICKET-ID]" --project $PROJECT
```

This gives context on *why* decisions were made.

---

## Step 3 — Query Codebase for Each Comment

For each reviewer comment, query the codebase for relevant context:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<comment topic>" \
  --project $PROJECT --top 3 --rerank
```

Also check coding standards:
```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$VENV $SCRIPTS/query_rag.py "<comment topic>" \
  --collection standards --project $PROJECT --top 2
```

---

## Step 4 — Categorize Each Comment

| Category | How to Handle |
|----------|--------------|
| Bug fix required | Acknowledge, implement fix, explain change |
| Style/convention | Agree and fix, or explain if intentional deviation |
| Architecture suggestion | Discuss tradeoffs, agree or explain rationale |
| Question | Answer with context from codebase/solution |
| Praise | Acknowledge briefly |
| False positive | Explain why the concern doesn't apply, with evidence |

---

## Step 5 — Draft Responses

For each comment, draft a response that:

1. **Acknowledges** the reviewer's point
2. **Explains** what was done (or why not)
3. **References** solution approach or codebase patterns if relevant
4. Keeps it **concise** — 1–3 sentences, no filler

**Good response:**
```
Good catch — this was using a stale reference. Fixed in the latest commit by
moving the fetch inside the effect cleanup. Thanks.
```

**Bad response:**
```
Thank you for your valuable feedback! I have carefully considered your suggestion
and have made the necessary changes to address your concern. I hope this resolves
the issue you raised. Please let me know if you have any further questions.
```

---

## Step 6 — Post Responses

For each response, post as a reply to the specific comment thread:

```
mcp__github__add_issue_comment(
  owner: "<owner>",
  repo: "<repo>",
  issue_number: <pr_number>,
  body: "<response text>"
)
```

---

## Checklist

```
PR Review Agent — [TICKET-ID] PR #NNN:
- [ ] PR context fetched (PR details + files + comments)
- [ ] Solution approach retrieved
- [ ] Each comment categorized
- [ ] Responses drafted (concise, grounded)
- [ ] Responses posted
- [ ] Fixes committed (if any code changes needed)
```
