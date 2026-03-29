# Refactor — Safe, RAG-Grounded Code Refactoring

Refactor existing code without changing external behavior. Uses the codebase
KB to understand the full blast radius before touching anything.

**Usage:**
- `/refactor path/to/file.ts` — refactor a specific file
- `/refactor "description of what to refactor"` — refactor by description

**Target:** $ARGUMENTS

---

## Step 1 — Understand What to Refactor

Read the target file completely. Identify:
- What exactly needs to change (naming, structure, duplication, complexity)
- What the external interface is (what callers depend on)
- What the existing tests cover

Do NOT start writing code yet.

---

## Step 2 — Find All Callers and Dependents

```bash
# Find usages of the function/class being refactored
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<function or class name>" \
  --project $AGENTS_PROJECT --multi-query --top 10

# Check review history for this area
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module or file name> refactor pattern" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 8

# Check naming/structure standards
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "naming convention structure" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

---

## Step 3 — Define the Refactor Scope

State clearly before making changes:

```
Refactor scope:
- What changes: <specific thing>
- What does NOT change: external interface, behavior, return values
- Blast radius: <list of files that call the refactored code>
- Test coverage: <what tests exist that validate the current behavior>
```

If any part of the external interface will change, that is no longer a
refactor — it is a feature change. Stop and raise it with the user.

---

## Step 4 — Apply the Refactor

Refactor guidelines:
- **One change at a time** — rename OR restructure OR extract, not all three
- **Tests must stay green** throughout — run after each change
- **No behavior changes** — same inputs produce same outputs
- **No new features** — refactor is not the time to add error handling that didn't exist
- **Preserve error messages** — callers may depend on exact error text

Common safe refactors:
- Extract a long function into smaller named helpers
- Rename a variable/function to better reflect its purpose
- Remove duplication by extracting a shared utility
- Flatten deeply nested conditionals using early returns
- Move a utility function to a more appropriate module

---

## Step 5 — Verify Behavior is Unchanged

```bash
# Run existing tests — they must all pass without modification
<test-runner> <spec-file>

# If tests needed modification to pass: STOP
# This means behavior changed. Re-evaluate the refactor scope.

# Run full suite
<test-all-command>

# Lint and type-check
<lint-command> && <type-check-command>
```

If any existing test needed to change to pass, the refactor changed behavior.
Revert and re-scope.

---

## Step 6 — Commit

```bash
git add <only refactored files>
git commit -m "refactor: <what changed and why>"
```

Refactor commits should be separate from feature/fix commits so reviewers
can diff them independently.

---

## Checklist

```
Refactor — $ARGUMENTS:
- [ ] Target file read completely
- [ ] All callers identified via RAG
- [ ] Scope defined (what changes, what doesn't, blast radius)
- [ ] External interface unchanged
- [ ] All existing tests pass without modification
- [ ] Lint and type-check pass
- [ ] Commit is refactor-only (no features or fixes mixed in)
```
