# Configure — Project Setup Wizard

Bootstrap the SDLC agent framework for any tech stack from scratch.

**Project path (optional):** $ARGUMENTS
If no argument is given, use the current working directory.

---

## What This Command Does

1. Scans the project to detect the tech stack automatically
2. Maps the directory structure to module names
3. Generates a tailored `MODULE_PATTERNS` config for the indexing script
4. Writes `.claude/settings.json`, `CLAUDE.md`, and agent commands into the project
5. Runs the initial Weaviate schema init and first KB index
6. Validates the setup with a test query

---

## Phase 1 — Detect Tech Stack

Set `PROJECT_ROOT` to `$ARGUMENTS` or the current working directory.

Scan these files to determine the stack:

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

From the scan, identify:

| Signal | Stack |
|--------|-------|
| `package.json` with `@nestjs/core` | NestJS (TypeScript) |
| `package.json` with `nuxt` | Nuxt (Vue 3) |
| `package.json` with `next` | Next.js (React) |
| `package.json` with `express` | Express (Node.js) |
| `package.json` with `fastify` | Fastify (Node.js) |
| `requirements.txt` with `django` | Django (Python) |
| `requirements.txt` with `fastapi` | FastAPI (Python) |
| `requirements.txt` with `flask` | Flask (Python) |
| `Gemfile` with `rails` | Ruby on Rails |
| `pom.xml` or `build.gradle` | Spring Boot (Java) |
| `go.mod` | Go |
| `composer.json` with `laravel` | Laravel (PHP) |
| `Cargo.toml` | Rust |

Also detect:
- Is this a **monorepo**? Check for `pnpm-workspace.yaml`, `nx.json`, `turbo.json`, `lerna.json`, or multiple `package.json` files in subdirectories.
- What are the **top-level application directories**? (`apps/`, `services/`, `packages/`, `applications/`)
- Is there a database ORM? (Mongoose schemas, Prisma, TypeORM, Sequelize, ActiveRecord, SQLAlchemy, GORM, Hibernate)
- Is there a queue system? (BullMQ, Celery, Sidekiq, RabbitMQ, AWS SQS patterns)

---

## Phase 2 — Map Directory Structure to Modules

Scan the source directories to discover actual module/feature folders:

```bash
# For each detected app root, list top-level subdirectories
find "$PROJECT_ROOT/src" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/app" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/lib" -maxdepth 2 -type d 2>/dev/null | head -60
find "$PROJECT_ROOT/apps" -maxdepth 3 -type d 2>/dev/null | head -60
```

Group the discovered directories into these logical categories and build the `MODULE_PATTERNS` accordingly:

| Category | Directory signals |
|----------|------------------|
| `auth` | dirs containing: auth, authentication, login, session, oauth, jwt, identity |
| `users` | dirs containing: user, profile, account, member, customer |
| `payments` | dirs containing: payment, billing, invoice, checkout, subscription, stripe, braintree, paypal |
| `orders` | dirs containing: order, purchase, transaction, cart |
| `listings` | dirs containing: listing, product, catalog, item, inventory |
| `notifications` | dirs containing: notification, email, sms, push, alert, mailer |
| `search` | dirs containing: search, elastic, solr, algolia, query |
| `reports` | dirs containing: report, analytics, metrics, dashboard, stats, vhr, history |
| `fraud` | dirs containing: fraud, risk, compliance, kount, verify |
| `scheduler` | dirs containing: scheduler, cron, job, queue, worker, task, background |
| `webhooks` | dirs containing: webhook, hook, event, callback |
| `admin` | dirs containing: admin, backoffice, dashboard, management |
| `ui-pages` | dirs containing: pages, views, routes |
| `ui-components` | dirs containing: components, widgets |
| `ui-stores` | dirs containing: store, stores, state, redux, zustand, pinia |
| `ui-composables` | dirs containing: composables, hooks |
| `config` | dirs containing: config, settings, env, constants |
| `migrations` | dirs containing: migration, seed, schema, prisma |
| `scripts` | dirs containing: script, tool, bin, cli |

For any directories that don't match the above, create a module entry using the actual directory name.

---

## Phase 3 — Determine Build Commands

Based on the stack, infer the standard commands:

**NestJS:**
```
test: pnpm test / npm test
lint: pnpm lint / npm run lint
build: pnpm build / npm run build
type-check: pnpm type-check / npm run type-check
```

**Nuxt:**
```
test: pnpm test
lint: pnpm lint
build: nuxt build
```

**Next.js:**
```
test: npm test / pnpm test
lint: next lint
build: next build
type-check: tsc --noEmit
```

**Django:**
```
test: python manage.py test
lint: flake8 . / ruff check .
build: (none / docker build)
type-check: mypy .
```

**FastAPI:**
```
test: pytest
lint: ruff check .
build: (none / docker build)
type-check: mypy .
```

**Rails:**
```
test: bundle exec rails test / bundle exec rspec
lint: bundle exec rubocop
build: bundle exec rails assets:precompile
```

**Spring Boot:**
```
test: ./mvnw test / ./gradlew test
lint: ./mvnw checkstyle:check
build: ./mvnw package / ./gradlew build
```

**Go:**
```
test: go test ./...
lint: golangci-lint run
build: go build ./...
```

**Laravel:**
```
test: php artisan test
lint: ./vendor/bin/pint
build: npm run build
```

---

## Phase 4 — Generate Project Name

Derive `PROJECT_NAME` from the directory name:
- Take `basename "$PROJECT_ROOT"`
- Convert to lowercase, replace spaces and hyphens with underscores
- Example: `my-app` → `my_app`, `BillingService` → `billingservice`

---

## Phase 5 — Present Configuration Summary

Before writing any files, output this summary and ask for confirmation:

```
=== SDLC Agent Framework — Configuration Summary ===

Project:        <PROJECT_NAME>
Root:           <PROJECT_ROOT>
Stack:          <detected stack(s)>
Monorepo:       yes/no
DB/ORM:         <detected ORM or "not detected">
Queue:          <detected queue or "not detected">

Module Patterns detected (<N> modules):
  auth          → **/auth/**, **/authentication/**
  users         → **/user/**, **/profile/**
  payments      → **/payment/**, **/billing/**
  ... (full list)

Test command:   <command>
Lint command:   <command>
Build command:  <command>

Files to write:
  ✎  <PROJECT_ROOT>/CLAUDE.md
  ✎  <PROJECT_ROOT>/.claude/settings.json
  ✎  <PROJECT_ROOT>/.claude/commands/  (10 agent commands)
  ✎  <AGENTS_ROOT>/scripts/project-<PROJECT_NAME>.py  (MODULE_PATTERNS config)

Weaviate:
  URL:          http://localhost:8090  (override with AGENTS_WEAVIATE_URL)
  Project key:  <PROJECT_NAME>

Continue? (say "yes" to proceed, or give corrections first)
```

Wait for user confirmation or corrections. If the user corrects anything (wrong stack, missing module, wrong test command), incorporate the corrections before proceeding.

---

## Phase 6 — Write Files

### 6.1 — Write MODULE_PATTERNS config

Write `$AGENTS_ROOT/scripts/project-<PROJECT_NAME>.py`:

```python
# Auto-generated by /configure for project: <PROJECT_NAME>
# Edit this file to adjust module detection for your codebase.
# Run update_kb.py with --module-config project-<PROJECT_NAME>.py to use it.

PROJECT_NAME = "<PROJECT_NAME>"
PROJECT_ROOT = "<PROJECT_ROOT>"

MODULE_PATTERNS = [
    # (module_name, [glob_patterns])
    # Generated from directory scan — add or remove entries as needed
    ("<module>", ["**/<dir>/**", ...]),
    ...
]

INCLUDE_EXTENSIONS = {
    # Generated based on detected stack
    # NestJS: .ts, .js, .json, .md
    # Django: .py, .html, .md
    # Rails: .rb, .erb, .md
    # Go: .go, .mod, .md
    "<ext>",
    ...
}

TEST_COMMAND = "<test command>"
LINT_COMMAND = "<lint command>"
BUILD_COMMAND = "<build command>"
TYPE_CHECK_COMMAND = "<type check command or empty string>"
```

### 6.2 — Write CLAUDE.md

Write `$PROJECT_ROOT/CLAUDE.md`. Tailor the content to the detected stack:

```markdown
# CLAUDE.md

## Project Overview

**<PROJECT_NAME>** — <one sentence description based on directory names and package.json description if present>

Stack: <stack>
ORM: <ORM or N/A>
Queue: <queue or N/A>

## Development Commands

### Running

```bash
<start command>
```

### Testing

```bash
<test command>       # unit tests
<e2e command>        # e2e tests (if detected)
```

### Code Quality

```bash
<lint command>
<type-check command>
<format command>
```

### Build

```bash
<build command>
```

## Architecture

<Brief generated summary of top-level directory structure>

## Commit Format

Use conventional commits: feat, fix, chore, docs, refactor, test
Reference ticket IDs in commit messages.

## Agent Configuration

- Project key: <PROJECT_NAME>
- Weaviate URL: $AGENTS_WEAVIATE_URL (default: http://localhost:8090)
- Scripts: $AGENTS_ROOT/scripts/
```

### 6.3 — Write .claude/settings.json

Write `$PROJECT_ROOT/.claude/settings.json`:

```json
{
  "env": {
    "AGENTS_ROOT": "<absolute path to sdlc-agent-framework>",
    "AGENTS_VENV": "<absolute path to ~/.sdlc-agents-venv/bin/python>",
    "AGENTS_WEAVIATE_URL": "http://localhost:8090",
    "AGENTS_PROJECT": "<PROJECT_NAME>"
  },
  "permissions": {
    "allow": [
      "Bash(<test command>)",
      "Bash(<lint command>)",
      "Bash(<build command>)",
      "Bash(git diff*)",
      "Bash(git log*)",
      "Bash(git push*)",
      "Bash(gh pr*)",
      "Bash(<AGENTS_VENV> <AGENTS_ROOT>/scripts/query_rag.py*)",
      "Bash(<AGENTS_VENV> <AGENTS_ROOT>/scripts/update_kb.py*)",
      "Bash(<AGENTS_VENV> <AGENTS_ROOT>/scripts/update_pr_kb.py*)",
      "Bash(<AGENTS_VENV> <AGENTS_ROOT>/scripts/start_weaviate.py*)"
    ]
  }
}
```

### 6.4 — Copy Agent Commands

```bash
mkdir -p "$PROJECT_ROOT/.claude/commands"
cp "$AGENTS_ROOT/claude/commands/"*.md "$PROJECT_ROOT/.claude/commands/"
```

### 6.5 — Update Controller Command

In `$PROJECT_ROOT/.claude/commands/controller.md`, update the test/lint/build commands to match the detected stack (replace `pnpm test && pnpm lint && pnpm type-check` with the project's actual commands).

---

## Phase 7 — Run Initial Setup

### 7.1 — Start Weaviate (if not already running)

```bash
curl -s http://localhost:8090/v1/.well-known/ready 2>/dev/null | grep -q "true" \
  || $AGENTS_VENV $AGENTS_ROOT/scripts/start_weaviate.py --project $PROJECT_NAME &
sleep 3
```

### 7.2 — Initialize Schema

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --init-schema --project $PROJECT_NAME
```

### 7.3 — Index Codebase

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/update_kb.py \
  --repo-root "$PROJECT_ROOT" \
  --project $PROJECT_NAME
```

Report how many files were indexed, by module.

### 7.4 — Validate with Test Query

Run a test query using the most central module detected:

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module name> service" \
  --project $PROJECT_NAME --top 3 --rerank
```

Show the top 3 results so the user can confirm RAG is working.

---

## Phase 8 — Output Setup Summary

```
=== Setup Complete ===

Project:   <PROJECT_NAME>
Indexed:   <N> files across <M> modules
Weaviate:  http://localhost:8090 (project: <PROJECT_NAME>)

Files written:
  ✅ <PROJECT_ROOT>/CLAUDE.md
  ✅ <PROJECT_ROOT>/.claude/settings.json
  ✅ <PROJECT_ROOT>/.claude/commands/ (<N> commands)
  ✅ <AGENTS_ROOT>/scripts/project-<PROJECT_NAME>.py

Available commands:
  /solution <TICKET-ID>   — draft solution approach
  /code <TICKET-ID>       — TDD implementation
  /review-code            — code review
  /safe-commit            — pre-commit validation
  /update-kb              — re-sync codebase to RAG
  /update-pr-kb           — index PR review history
  /controller <TICKET-ID> — full SDLC pipeline

Next steps:
  1. Configure Jira MCP in .claude/settings.json (see docs/mcp-guide.md)
  2. Configure GitHub MCP in .claude/settings.json
  3. Run /update-pr-kb to index review patterns from merged PRs
  4. Run /solution <your-first-ticket> to start your first pipeline
```

---

## Stack-Specific Notes

### Monorepos

If monorepo detected, ask the user which application to configure first:
```
Monorepo detected. Found these applications:
  1. apps/api      (NestJS — 23 modules)
  2. apps/web      (Next.js — 12 pages)
  3. packages/ui   (React components)

Configure all, or start with one? (default: all)
```

Run separate KB indexing per application with the same `--project` key but differentiated modules.

### Legacy Codebases

For codebases with flat or inconsistent structure (Java enterprise, old PHP, etc.):
- Include more file extensions (`INCLUDE_EXTENSIONS`)
- Increase `MAX_FILE_BYTES` to 200_000 in the config
- Note in the summary that module detection may be less accurate and advise reviewing `project-<NAME>.py` before proceeding

### Microservices

For microservices with separate repos per service:
- Use `--project <org-name>` as the shared project key across all services
- Index each service repo separately — they all go into the same Weaviate collections
- Advise setting up a shared Weaviate instance (see `docs/vector-db-setup.md`)
