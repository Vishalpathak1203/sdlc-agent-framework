# Safe Commit

Run all quality gates before committing. Never skip.

**Model:** `claude-haiku-3-5`

---

## Step 1 — Check What Changed

```bash
git status
git diff --stat
```

---

## Step 2 — Run Quality Gates

Run all three. Fix failures before proceeding.

```bash
# Tests
pnpm test

# Lint
pnpm lint

# Type check
pnpm type-check
```

If any fails:
- Fix the error
- Re-run the failing check
- Do not commit until all pass

---

## Step 3 — Commit

Use conventional commit format with ticket reference:

```bash
git add <specific files — not git add .>
git commit -m "TICKET-ID: type: description"
```

**Commit types:**
- `feat` — new feature
- `fix` — bug fix
- `test` — test changes only
- `refactor` — code restructure, no behavior change
- `chore` — dependency, config, build changes
- `docs` — documentation only

**Examples:**
```bash
git commit -m "PROJ-1234: feat: add pagination to orders list endpoint"
git commit -m "PROJ-1234: fix: null check on missing order items"
git commit -m "PROJ-1234: test: add edge cases for empty cart"
```

---

## Rules

- Never `git add .` — add specific files to avoid committing `.env`, secrets, or generated files
- Never `--no-verify` — hooks exist for a reason
- Never `--force-push` to main/master
- One logical change per commit

---

## Checklist

```
Safe Commit:
- [ ] git status reviewed — no unintended files
- [ ] pnpm test — all pass
- [ ] pnpm lint — no errors
- [ ] pnpm type-check — no errors
- [ ] Specific files staged (not git add .)
- [ ] Commit message follows conventional format + ticket reference
```
