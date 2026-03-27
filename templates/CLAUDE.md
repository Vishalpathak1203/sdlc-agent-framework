# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

When writing code, only add comments when necessary.

---

## Project Overview

**[PROJECT NAME]** is a [brief description — e.g., "NestJS API + Nuxt 3 frontend monorepo"].

**Stack:**
- Backend: [e.g., NestJS, Express, Django, Rails, Spring Boot]
- Frontend: [e.g., Nuxt 3, Next.js, React, Vue]
- Database: [e.g., MongoDB, PostgreSQL, MySQL]
- Cache: [e.g., Redis]
- Queue: [e.g., BullMQ, Sidekiq, Celery]

---

## Development Commands

```bash
# Install dependencies
[pnpm install / npm install / bundle install / pip install -r requirements.txt]

# Run development server
[pnpm dev / npm run dev / rails server / python manage.py runserver]

# Run tests
[pnpm test / npm test / bundle exec rspec / pytest]

# Lint
[pnpm lint / npm run lint / rubocop / flake8]

# Type check (if applicable)
[pnpm type-check / npx tsc]

# Build
[pnpm build / npm run build / mvn package]
```

---

## Architecture

### Key Directories

```
[project-root]/
├── [backend-dir]/          # Backend application
│   ├── src/                # Source code
│   │   ├── [module-A]/     # Feature module A
│   │   ├── [module-B]/     # Feature module B
│   │   └── common/         # Shared utilities
│   └── test/               # Tests
└── [frontend-dir]/         # Frontend application
    ├── pages/              # Route pages
    ├── components/         # UI components
    ├── stores/             # State management
    └── composables/        # Reusable logic
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `auth` | Authentication and authorization |
| `[module]` | [purpose] |

---

## Coding Conventions

### File Naming
- Backend: `kebab-case` (e.g., `user-profile.service.ts`)
- Frontend: `PascalCase` for components (e.g., `UserProfile.vue`)

### Error Handling
- [Describe your error handling pattern]

### Commit Format
Commits must follow conventional commit format with ticket reference:
```
TICKET-1234: feat: add user authentication
TICKET-1234: fix: resolve cart calculation bug
```

---

## Agent Configuration

### RAG Scripts

```bash
# Weaviate must be running
export AGENTS_WEAVIATE_URL=http://localhost:8090
export AGENTS_PROJECT=[project-name]
export AGENTS_ROOT=/path/to/sdlc-agent-framework
export AGENTS_VENV=~/.sdlc-agents-venv/bin/python
```

### When to Update KB

Run `update-kb` after:
- `git rebase main`
- Significant feature merges
- Adding new modules or refactoring structure

---

## Testing Strategy

- Unit tests: [Jest / Vitest / RSpec / pytest]
- Integration tests: [Supertest / Cypress / etc.]
- E2E tests: [Playwright / Cypress / etc.]
- Use `test.each()` for repetitive test patterns

---

## Pre-Commit Requirements

1. Run tests — all must pass
2. Run lint — fix all errors
3. Run type-check — fix all errors (if TypeScript)

**Never skip hooks (`--no-verify`).**

---

## Environment Variables

Create `.env` from `.env.example`. Key variables:

```
# Backend
DATABASE_URL=
REDIS_URL=
APP_ENV=local

# Frontend
PUBLIC_API_URL=
```
