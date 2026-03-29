# Mate Review — Peer Code Review Before Raising PR

Act as a senior peer reviewer. Review the current branch changes before a PR
is opened, surfacing the issues a human reviewer would flag — grounded in the
team's actual review history.

**Usage:**
- `/mate-review` — review all staged/unstaged changes on current branch
- `/mate-review PROJ-123` — review changes for a specific ticket

---

## Step 1 — Get the Diff

```bash
git diff main...HEAD
git diff main...HEAD --name-only
```

If no changes vs main, check staged changes: `git diff --staged`

---

## Step 2 — Load Review Pattern Context

For each file type changed, query past review patterns:

```bash
# General code quality patterns the team has flagged
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "code review quality issues" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 15

# Pattern specific to the module being changed
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module name> review feedback" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 10

# Relevant standards
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<change type> standards" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

---

## Step 3 — Review Each Changed File

For each file in the diff, read it and evaluate:

### Code Quality
- [ ] Functions do one thing (Single Responsibility)
- [ ] Names describe intent, not implementation
- [ ] No dead code or commented-out blocks
- [ ] No magic numbers or hardcoded strings that belong in constants
- [ ] Complex logic has a brief comment explaining *why* (not *what*)

### Correctness
- [ ] Edge cases handled (null, empty, boundary values)
- [ ] Error states handled and not swallowed silently
- [ ] Async operations properly awaited
- [ ] No race conditions in concurrent paths

### Security
- [ ] User inputs validated at system boundaries
- [ ] No sensitive data in logs or error messages
- [ ] Auth/permission checks in place for new endpoints
- [ ] No new SQL/command injection surface

### Performance
- [ ] No N+1 queries introduced
- [ ] No unbounded loops over large collections
- [ ] Caching not broken by this change

### Tests
- [ ] New/changed logic has corresponding tests
- [ ] Tests cover the happy path AND at least one error/edge case
- [ ] No tests deleted to make failures go away

### Team Patterns (from ReviewPatterns KB)
- Check each issue found in Step 2 against the diff

---

## Step 4 — Produce the Review Report

```markdown
## Mate Review — <branch or ticket>

### Summary
<1-2 sentences: overall quality and readiness>

### Must Fix Before PR
- [ ] **[CRITICAL]** <file>:<line> — <issue> — <what to do>

### Should Fix
- [ ] **[IMPORTANT]** <file>:<line> — <issue>

### Consider
- [ ] **[SUGGESTION]** <file>:<line> — <optional improvement>

### Confirmed Good
- <what was done well — be specific>

### Checklist
- [ ] No critical issues
- [ ] Tests cover new logic
- [ ] Standards compliance confirmed
```

---

## Checklist

```
Mate Review:
- [ ] Full diff read
- [ ] ReviewPatterns queried for this module's history
- [ ] Standards queried for relevant rules
- [ ] Each changed file reviewed against all categories
- [ ] Report produced with severity-tagged findings
- [ ] Critical issues identified and documented
```
