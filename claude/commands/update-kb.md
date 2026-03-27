# Update Knowledge Base

Sync the codebase to Weaviate. Run after git rebase or significant merges.

---

## Step 1 — Check Weaviate

```bash
curl http://localhost:8090/v1/.well-known/ready
```

If not ready:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/start_weaviate.py
```

## Step 2 — Update Codebase KB

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --repo-root . --project $AGENTS_PROJECT
```

Add `--full` to force re-embed everything (after large rebases).

## Step 3 — Update Standards KB

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --standards --repo-root . --project $AGENTS_PROJECT
```

## Step 4 — Verify Stats

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project $AGENTS_PROJECT
```

## Checklist

```
Update KB:
- [ ] Weaviate running
- [ ] Codebase KB updated
- [ ] Standards KB updated
- [ ] Stats verified
```
