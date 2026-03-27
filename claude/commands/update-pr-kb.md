# Update PR Review KB

Index merged PR review comments into Weaviate. Run weekly.

---

## Step 1 — Check Weaviate

```bash
curl http://localhost:8090/v1/.well-known/ready
```

## Step 2 — Check GitHub CLI Auth

```bash
gh auth status
```

## Step 3 — Index PR Review History

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_pr_kb.py \
  --limit 100 --include-open --project $AGENTS_PROJECT
```

## Step 4 — Verify

```bash
AGENTS_WEAVIATE_URL=$AGENTS_WEAVIATE_URL \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project $AGENTS_PROJECT
```

ReviewPatterns count should increase.

## Checklist

```
Update PR KB:
- [ ] Weaviate running
- [ ] gh auth status shows authenticated
- [ ] update_pr_kb.py ran without errors
- [ ] ReviewPatterns count increased
```
