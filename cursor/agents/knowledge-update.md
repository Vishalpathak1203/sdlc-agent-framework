# Knowledge Update Agent

Sync the codebase and coding standards to Weaviate. Run after git rebase or when significant code changes have been merged.

**Model:** `claude-haiku-3-5`
**When:** After `git rebase main`, after large PRs merged, weekly minimum.

---

## Step 1 — Ensure Weaviate is Running

```bash
curl http://localhost:8090/v1/.well-known/ready
```

If not running:
```bash
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/start_weaviate.py
```

---

## Step 2 — Update Codebase Knowledge

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --repo-root $PROJECT_ROOT \
  --project $PROJECT
```

Incremental by default — only re-embeds changed files.
Use `--full` after a large rebase to force re-embed everything.

---

## Step 3 — Update Coding Standards

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --standards \
  --repo-root $PROJECT_ROOT \
  --project $PROJECT
```

---

## Step 4 — Verify

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project $PROJECT
```

Expected output:
```
CodebaseKnowledge [project]: N objects
CodingStandards [project]: N objects
ReviewPatterns [project]: N objects
SolutionApproach [project]: N objects
```

---

## Checklist

```
Knowledge Update:
- [ ] Weaviate running
- [ ] Codebase knowledge updated
- [ ] Coding standards updated
- [ ] Stats verified — counts look reasonable
```
