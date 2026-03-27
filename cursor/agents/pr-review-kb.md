# PR Review KB Update Agent

Index merged PR review comments into Weaviate to build team review intelligence.

**Model:** `claude-haiku-3-5`
**When:** Weekly, or after significant PRs are merged.

---

## Step 1 — Ensure Weaviate is Running

```bash
curl http://localhost:8090/v1/.well-known/ready
```

---

## Step 2 — Index PR Review History

Run from the project repo directory (so `gh` uses the correct repo):

```bash
cd $PROJECT_ROOT

AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_pr_kb.py \
  --limit 100 \
  --include-open \
  --project $PROJECT
```

**Options:**
- `--limit N` — number of recent PRs to process (default: 50)
- `--include-open` — also include open PRs with existing review comments
- `--since YYYY-MM-DD` — only process PRs updated after this date

---

## Step 3 — Verify

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project $PROJECT
```

ReviewPatterns count should increase.

---

## Checklist

```
PR Review KB Update:
- [ ] Weaviate running
- [ ] gh auth status shows logged in
- [ ] update_pr_kb.py ran successfully
- [ ] ReviewPatterns count increased in stats
```
