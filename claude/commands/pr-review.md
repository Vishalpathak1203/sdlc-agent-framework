# PR Review Agent

Respond to reviewer comments on your PR.

**PR Number:** $ARGUMENTS

---

## Step 1 — Fetch PR Context

```
mcp__github__get_pull_request(owner: "<owner>", repo: "<repo>", pull_number: $ARGUMENTS)
mcp__github__get_pull_request_files(owner: "<owner>", repo: "<repo>", pull_number: $ARGUMENTS)
mcp__github__get_pull_request_comments(owner: "<owner>", repo: "<repo>", pull_number: $ARGUMENTS)
```

Identify all unresolved comments.

## Step 2 — Get Solution Context

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "<TICKET-ID>" --project $AGENTS_PROJECT
```

## Step 3 — Query Context per Comment

For each reviewer comment:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<comment topic>" \
  --project $AGENTS_PROJECT --top 3 --rerank
```

## Step 4 — Draft Responses

For each comment:
- Acknowledge the point
- Explain what was done (or why not changed)
- Reference RAG context if relevant
- Keep to 1–3 sentences

## Step 5 — Post Responses

```
mcp__github__add_issue_comment(
  owner: "<owner>", repo: "<repo>",
  issue_number: $ARGUMENTS,
  body: "<response>"
)
```

## Checklist

```
PR Review — #$ARGUMENTS:
- [ ] PR context fetched
- [ ] All unresolved comments identified
- [ ] Responses drafted (concise)
- [ ] Responses posted
- [ ] Any required fixes committed
```
