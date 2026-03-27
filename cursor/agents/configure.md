---
description: Bootstrap the SDLC agent framework for any tech stack
model: claude-sonnet-4-5
---

# Configure — Project Setup Wizard

Bootstrap the SDLC agent framework for this project from scratch.

**How to invoke:** In Cursor Composer, type: `@configure <path-to-project>` or just `@configure` to use the current workspace root.

---

## What This Playbook Does

1. Scans the project to detect the tech stack automatically
2. Maps the actual directory structure to module names
3. Generates a tailored `MODULE_PATTERNS` config for the KB indexer
4. Writes `CLAUDE.md`, `.cursor/rules/`, and agent settings
5. Runs the initial Weaviate schema init and first KB index
6. Validates the setup with a test query

---

## Phase 1 — Detect Tech Stack

Set `PROJECT_ROOT` to the path provided, or to `$workspaceFolder` if none given.

Check for these files in `PROJECT_ROOT`:

```bash
ls "$PROJECT_ROOT"
cat "$PROJECT_ROOT/package.json" 2>/dev/null || true
cat "$PROJECT_ROOT/requirements.txt" 2>/dev/null || true
cat "$PROJECT_ROOT/Gemfile" 2>/dev/null || true
cat "$PROJECT_ROOT/pom.xml" 2>/dev/null || true
cat "$PROJECT_ROOT/build.gradle" 2>/dev/null || true
cat "$PROJECT_ROOT/go.mod" 2>/dev/null || true
cat "$PROJECT_ROOT/composer.json" 2>/dev/null || true
cat "$PROJECT_ROOT/Cargo.toml" 2>/dev/null || true
```

Identify the stack:

| Signal | Stack |
|--------|-------|
| `@nestjs/core` in package.json | NestJS (TypeScript) |
| `nuxt` in package.json | Nuxt (Vue 3) |
| `next` in package.json | Next.js (React) |
| `express` in package.json | Express (Node.js) |
| `fastify` in package.json | Fastify (Node.js) |
| `django` in requirements.txt | Django (Python) |
| `fastapi` in requirements.txt | FastAPI (Python) |
| `flask` in requirements.txt | Flask (Python) |
| Rails in Gemfile | Ruby on Rails |
| pom.xml or build.gradle present | Spring Boot (Java) |
| go.mod present | Go |
| `laravel` in composer.json | Laravel (PHP) |
| Cargo.toml present | Rust |

Also detect:
- **Monorepo?** Check for `pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `lerna.json`, or workspace packages in `apps/`, `services/`, `packages/`, `applications/`
- **ORM?** Mongoose, Prisma, TypeORM, Sequelize, SQLAlchemy, ActiveRecord, GORM, Hibernate
- **Queue?** BullMQ, Celery, Sidekiq, RabbitMQ, AWS SQS patterns in source dirs

---

## Phase 2 — Map Directories to Modules

```bash
find "$PROJECT_ROOT/src" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/app" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/lib" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/apps" -maxdepth 3 -type d 2>/dev/null | head -60
```

Map directories to modules using these signals:

| Module | Directory name contains |
|--------|------------------------|
| `auth` | auth, authentication, login, session, oauth, jwt, identity |
| `users` | user, profile, account, member, customer |
| `payments` | payment, billing, invoice, checkout, subscription, stripe, braintree, paypal |
| `orders` | order, purchase, transaction, cart |
| `listings` | listing, product, catalog, item, inventory |
| `notifications` | notification, email, sms, push, alert, mailer |
| `search` | search, elastic, solr, algolia |
| `reports` | report, analytics, metrics, stats |
| `fraud` | fraud, risk, compliance |
| `scheduler` | scheduler, cron, job, queue, worker, task |
| `webhooks` | webhook, hook, event, callback |
| `admin` | admin, backoffice, management |
| `ui-pages` | pages, views, routes |
| `ui-components` | components, widgets |
| `ui-stores` | store, stores, state |
| `ui-composables` | composables, hooks |
| `config` | config, settings, constants |
| `migrations` | migration, seed, schema |

For unmatched directories, use the actual directory name as the module name.

---

## Phase 3 — Infer Build Commands

Based on the detected stack:

| Stack | Test | Lint | Build | Type check |
|-------|------|------|-------|-----------|
| NestJS | `pnpm test` | `pnpm lint` | `pnpm build` | `pnpm type-check` |
| Nuxt | `pnpm test` | `pnpm lint` | `nuxt build` | `nuxt typecheck` |
| Next.js | `pnpm test` | `next lint` | `next build` | `tsc --noEmit` |
| Express | `npm test` | `npm run lint` | — | `tsc --noEmit` |
| Django | `python manage.py test` | `ruff check .` | — | `mypy .` |
| FastAPI | `pytest` | `ruff check .` | — | `mypy .` |
| Rails | `bundle exec rspec` | `bundle exec rubocop` | `rails assets:precompile` | — |
| Spring Boot | `./mvnw test` | `./mvnw checkstyle:check` | `./mvnw package` | — |
| Go | `go test ./...` | `golangci-lint run` | `go build ./...` | — |
| Laravel | `php artisan test` | `./vendor/bin/pint` | `npm run build` | — |

Check `package.json` scripts for any non-standard overrides.

---

## Phase 4 — Present Configuration Summary

Before writing, show the full plan and wait for confirmation:

```
=== SDLC Agent Framework — Configuration Summary ===

Project:        <PROJECT_NAME>
Root:           <PROJECT_ROOT>
Stack:          <stack>
Monorepo:       yes/no
ORM:            <ORM or not detected>
Queue:          <queue or not detected>

Modules detected (<N> total):
  auth          → **/auth/**, **/authentication/**
  users         → **/user/**, **/profile/**
  ...

Commands:
  Test:         <test command>
  Lint:         <lint command>
  Build:        <build command>
  Type check:   <type check command>

Files to write:
  ✎  <PROJECT_ROOT>/CLAUDE.md
  ✎  <PROJECT_ROOT>/.cursor/rules/project-structure.mdc
  ✎  <PROJECT_ROOT>/.cursor/rules/code-quality.mdc
  ✎  <AGENTS_ROOT>/scripts/project-<PROJECT_NAME>.py

Weaviate:
  URL:          http://localhost:8090
  Project key:  <PROJECT_NAME>

Continue? (say "yes" or correct anything first)
```

Wait. Incorporate any corrections before Phase 5.

---

## Phase 5 — Write Files

### 5.1 — Write MODULE_PATTERNS config

Write `$AGENTS_ROOT/scripts/project-<PROJECT_NAME>.py`:

```python
# Auto-generated by configure agent for project: <PROJECT_NAME>
# Edit MODULE_PATTERNS to adjust module detection for your structure.

PROJECT_NAME = "<PROJECT_NAME>"
PROJECT_ROOT = "<PROJECT_ROOT>"

MODULE_PATTERNS = [
    ("<module>", ["**/<dir>/**"]),
    ...
]

INCLUDE_EXTENSIONS = {
    # Populated based on detected stack
    ".ts", ".js", ".md",  # TypeScript projects
    # ".py", ".md",        # Python projects
    # ".rb", ".md",        # Ruby projects
    # ".java", ".md",      # Java projects
    # ".go", ".mod",       # Go projects
}

TEST_COMMAND = "<test command>"
LINT_COMMAND = "<lint command>"
BUILD_COMMAND = "<build command>"
TYPE_CHECK_COMMAND = "<type check command>"
```

### 5.2 — Write CLAUDE.md

Write `$PROJECT_ROOT/CLAUDE.md` tailored to the detected stack. Include:
- Project overview (inferred from package.json `description` or directory name)
- Dev commands (test, lint, build, type-check — detected in Phase 3)
- Architecture section (top-level directory map)
- Commit format (conventional commits)
- Agent configuration block (project key, Weaviate URL)

### 5.3 — Write .cursor/rules/

Copy and customize from `$AGENTS_ROOT/templates/cursor-rules/`:

```bash
mkdir -p "$PROJECT_ROOT/.cursor/rules"
cp "$AGENTS_ROOT/templates/cursor-rules/"*.mdc "$PROJECT_ROOT/.cursor/rules/"
```

Update `project-structure.mdc` to reflect the detected naming conventions (kebab-case vs PascalCase vs snake_case based on stack).

---

## Phase 6 — Run Initial Setup

### 6.1 — Verify Weaviate is running

```bash
curl -s http://localhost:8090/v1/.well-known/ready
```

If not ready, prompt: "Start Weaviate first: `$AGENTS_VENV $AGENTS_ROOT/scripts/start_weaviate.py`"

### 6.2 — Initialize Schema

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --init-schema --project <PROJECT_NAME>
```

### 6.3 — Index Codebase

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --repo-root "$PROJECT_ROOT" \
  --project <PROJECT_NAME>
```

Report files indexed per module in a table.

### 6.4 — Test Query

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<central module name> core logic" \
  --project <PROJECT_NAME> --top 3 --rerank
```

Show the 3 results. If they look relevant to the project, setup is confirmed.

---

## Phase 7 — Output Summary

```
=== Setup Complete ===

Project:    <PROJECT_NAME>
Stack:      <stack>
Indexed:    <N> files across <M> modules
Weaviate:   http://localhost:8090 (project: <PROJECT_NAME>)

Files written:
  ✅ <PROJECT_ROOT>/CLAUDE.md
  ✅ <PROJECT_ROOT>/.cursor/rules/  (<N> rule files)
  ✅ <AGENTS_ROOT>/scripts/project-<PROJECT_NAME>.py

In Cursor Composer, reference these playbooks:
  @knowledge-update   — sync codebase to RAG
  @solution-approach  — draft solution for a ticket
  @code-agent         — TDD implementation
  @code-review        — review implementation
  @pr-review-agent    — respond to PR comments
  @safe-commit        — validate before commit
  @controller         — full SDLC pipeline

Next steps:
  1. Add Jira + GitHub MCP to Cursor settings (see docs/mcp-guide.md)
  2. Run @pr-review-kb to index review patterns from merged PRs
  3. Open @controller and type your first ticket ID
```

---

## Monorepo Handling

If monorepo detected, list all discovered applications and ask:

```
Monorepo detected with <N> applications:
  1. apps/api     — NestJS (estimated <N> modules)
  2. apps/web     — Next.js (estimated <N> pages)
  3. packages/ui  — React components

Configure: all | just one (which number?)
```

If "all": run Phase 5–6 for each application but use the same `--project` key so they share one Weaviate namespace.

## Stack-Specific Notes

**Legacy codebases (flat structure):** Increase `MAX_FILE_BYTES` to 200_000. Note that module auto-detection may be less accurate — advise the user to review and edit `project-<NAME>.py` after generation.

**Microservices (multiple repos):** Use a shared `--project <org-name>` across all services. Index each repo separately. Point all services at the same Weaviate URL.

**Pure frontend (React/Vue/Svelte):** Skip `--standards` indexing if no backend standards docs exist. Focus module patterns on `pages/`, `components/`, `stores/`, `hooks/`.
