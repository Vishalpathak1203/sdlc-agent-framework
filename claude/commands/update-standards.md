# Update Standards — Sync Coding Standards to the Knowledge Base

Index or re-index coding standards, rules, and guidelines into Weaviate so
agents can retrieve them during code generation and review. Run after adding
or modifying standards documents.

**Usage:**
- `/update-standards` — index all standards in the repo
- `/update-standards path/to/rules/` — index a specific standards directory

**Target:** $ARGUMENTS

---

## Step 1 — Check Weaviate Is Running

```bash
curl -s http://localhost:8090/v1/.well-known/ready
```

If not ready:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/start_weaviate.py
```

---

## Step 2 — Locate Standards Files

If $ARGUMENTS is a path, use it. Otherwise look in standard locations:

```bash
# Common standards locations
ls .claude/rules/
ls .cursor/rules/
ls docs/standards/
ls STANDARDS.md CONTRIBUTING.md CODE_STANDARDS.md 2>/dev/null
```

Standards files are typically:
- `.claude/rules/*.mdc` or `.cursor/rules/*.mdc` — AI-specific rules
- `docs/standards/*.md` — human-readable coding guidelines
- `CONTRIBUTING.md`, `CODE_STANDARDS.md` — top-level standards
- `*.json` ESLint configs, `pyproject.toml` — linting rules (optional)

---

## Step 3 — Index Standards

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --standards \
  --repo-root . \
  --project $AGENTS_PROJECT
```

Add `--full` to force re-embed all standards (after large rewrites):

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --standards --full \
  --repo-root . \
  --project $AGENTS_PROJECT
```

---

## Step 4 — Verify Standards Are Retrievable

Run a test query to confirm the updated content is indexed:

```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "naming convention error handling" \
  --collection standards \
  --project $AGENTS_PROJECT \
  --top 5
```

The results should reference your standards files. If the expected content
doesn't appear, check that the files are in a directory the indexer scans.

---

## Step 5 — Verify Stats

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project $AGENTS_PROJECT
```

Confirm the `Standards_<project>` collection count increased.

---

## When to Run

| Event | Action |
|-------|--------|
| Added a new standards file | `/update-standards` |
| Edited an existing rule | `/update-standards` |
| Deleted a rule | `/update-standards --full` (to remove stale embeddings) |
| After a fresh repo clone | `/update-standards` once after `/update-kb` |
| Agent is citing wrong standards | `/update-standards --full` to force re-embed |

---

## Checklist

```
Update Standards:
- [ ] Weaviate running
- [ ] Standards files located (rules/, docs/, CONTRIBUTING.md)
- [ ] Standards indexed (--full if large changes)
- [ ] Test query returns expected content
- [ ] Stats verified — collection count updated
```
