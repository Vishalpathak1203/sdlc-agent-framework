# Safe Commit

Run quality gates before committing. Never skip.

---

## Step 1 — Review Changes

```bash
git status
git diff --stat
```

## Step 2 — Quality Gates

```bash
pnpm test
pnpm lint
pnpm type-check
```

Fix all failures. Do not commit until all three pass.

## Step 3 — Commit

```bash
git add <specific files — never git add .>
git commit -m "TICKET-ID: type: description"
```

Commit types: `feat` | `fix` | `test` | `refactor` | `chore` | `docs`

## Rules

- Never `git add .`
- Never `--no-verify`
- Never force-push to main/master

## Checklist

```
Safe Commit:
- [ ] Status reviewed — no unintended files
- [ ] pnpm test — pass
- [ ] pnpm lint — pass
- [ ] pnpm type-check — pass
- [ ] Specific files staged
- [ ] Commit message: TICKET-ID: type: description
```
