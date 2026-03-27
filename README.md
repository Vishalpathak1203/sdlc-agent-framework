# SDLC Agent Framework

A generic, project-agnostic AI agent orchestration framework for the full software development lifecycle. Works with any codebase — 20-year-old legacy monolith or greenfield microservice — using local vector search, MCP tools, and LLM agents in Cursor and Claude Code.

---

## Why This Exists

### The Problems

| Problem | Impact |
|---------|--------|
| Context switching costs | Developers spend 30–40% of time re-reading code they already understood |
| Inconsistent code reviews | 100-person teams produce wildly different review quality |
| Lost solution decisions | Why was this architecture chosen? No one remembers |
| PR review patterns not shared | Team A learned the hard way; Team B makes the same mistake |
| AI agents without codebase context | LLMs hallucinate file names, APIs, patterns that don't exist |

### What We Built

A **local RAG (Retrieval-Augmented Generation) pipeline** that gives AI agents ground truth about your codebase, combined with **structured agent playbooks** that orchestrate the full SDLC:

```
Your Codebase ──► Vector DB (Weaviate) ──► AI Agent ──► Grounded Output
    +                                          │
Coding Standards                               │
    +                                       Uses MCP
PR Review History                          ├── Jira (ticket context)
    +                                      └── GitHub (PR context)
Solution Archive
```

---

## Architecture

```
sdlc-agent-framework/
├── scripts/               Python scripts — Weaviate + RAG operations
│   ├── start_weaviate.py  Start local Weaviate (no cloud needed)
│   ├── update_kb.py       Index codebase + standards → vector DB
│   ├── update_pr_kb.py    Index PR review history → vector DB
│   └── query_rag.py       Hybrid search + re-ranking CLI
├── cursor/                Cursor IDE setup
│   ├── README.md          Cursor-specific setup guide
│   └── agents/            Agent playbooks (markdown workflows)
├── claude/                Claude Code setup
│   ├── README.md          Claude Code-specific setup guide
│   └── commands/          Slash commands (/solution, /code, /review, etc.)
├── docs/                  Deep-dive documentation
│   ├── rag-basics.md      What is RAG and how it works here
│   ├── vector-db-setup.md Weaviate setup, algorithms, index tuning
│   ├── embeddings.md      Module-wise embeddings + classification strategy
│   ├── reranking.md       Re-ranking: why and how
│   ├── team-scale.md      Review patterns for 100+ developer teams
│   └── mcp-guide.md       Jira MCP + GitHub MCP usage
└── templates/             Copy these into your project
    ├── CLAUDE.md           Template CLAUDE.md for any project
    └── cursor-rules/       .cursor/rules/ templates
```

---

## Quick Start (5 minutes)

### Prerequisites

- Python 3.10+
- `uv` (recommended) or `pip`
- GitHub CLI (`gh`) — for PR review KB
- Cursor or Claude Code (VS Code extension / CLI)

### 1. Clone this repo

```bash
git clone https://github.com/Vishalpathak1203/sdlc-agent-framework.git
cd sdlc-agent-framework
export AGENTS_ROOT=$(pwd)
```

### 2. Create Python virtual environment

```bash
# Using uv (recommended — faster)
uv venv ~/.sdlc-agents-venv
uv pip install --python ~/.sdlc-agents-venv/bin/python -r scripts/requirements.txt

# Using pip
python3 -m venv ~/.sdlc-agents-venv
~/.sdlc-agents-venv/bin/pip install -r scripts/requirements.txt
```

### 3. Start Weaviate (local vector DB)

```bash
~/.sdlc-agents-venv/bin/python "$AGENTS_ROOT/scripts/start_weaviate.py"
# Runs on http://localhost:8090 — leave this terminal open
```

### 4. Run `/configure` in your project

Open Claude Code (or Cursor) inside your project directory and run:

```
/configure
```

That's it. The configure command handles everything else automatically:
- Detects your tech stack (NestJS, Django, Rails, Spring Boot, Next.js, Go, Laravel, and more)
- Maps your directories to module names
- Detects your test/lint/build commands
- Writes `CLAUDE.md` and `.claude/settings.json` tailored to your stack
- Copies all 10 agent commands into your project
- Initializes the Weaviate schema
- Runs the first KB index
- Validates RAG with a test query

Before writing any files, it shows a full summary and waits for your confirmation.

**Supported stacks:** NestJS · Nuxt · Next.js · Express · FastAPI · Django · Flask · Rails · Spring Boot · Go · Laravel · Rust · any monorepo structure

See [docs/developer-guide.md](docs/developer-guide.md) for the full walkthrough after setup.

---

## How RAG Works Here

See [docs/rag-basics.md](docs/rag-basics.md) for full explanation. Summary:

1. **Indexing:** Your source files are chunked (2000 chars, 200 overlap) and embedded using `BAAI/bge-small-en-v1.5` (22 MB, runs locally, no API key)
2. **Storage:** Embeddings stored in Weaviate with metadata (file path, module, doc_type, category)
3. **Retrieval:** Hybrid search — cosine vector similarity + BM25 keyword — merged via Reciprocal Rank Fusion
4. **Re-ranking:** Top-20 results re-ranked by a cross-encoder to top-5 for precision
5. **Injection:** LLM agent receives the top-5 chunks as grounded context

---

## The 9-Agent SDLC Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│  TICKET                                                          │
├──────────────────────────────────────────────────────────────────┤
│  1. knowledge-update  — Sync codebase to Weaviate     [haiku]   │
│  2. standards-update  — Index coding rules            [haiku]   │
│  3. pr-review-kb      — Index PR review patterns      [haiku]   │
├──────────────────────────────────────────────────────────────────┤
│  4. solution-approach — Draft solution using RAG      [haiku]   │
│  5. solution-review   — Review solution approach      [sonnet]  │ ← GATE ✋
├──────────────────────────────────────────────────────────────────┤
│  6. code-agent        — TDD implementation using RAG  [haiku]   │
│  7. code-review       — Review implementation         [sonnet]  │ ← GATE ✋
│  8. unit-test-review  — Audit test quality            [sonnet]  │
├──────────────────────────────────────────────────────────────────┤
│  9. pr-review-agent   — Respond to reviewer comments  [sonnet]  │
│  +  safe-commit       — Pre-commit validation         [haiku]   │
└──────────────────────────────────────────────────────────────────┘
```

**Gates (✋):** Human must approve before the pipeline continues. The LLM does not self-approve.

---

## Vector DB: What Problem It Solves

Without a vector DB, AI agents have two options:
- **Read everything** — paste the whole codebase into context (expensive, exceeds limits, slow)
- **Read nothing** — make up file names and APIs that don't exist (hallucination)

With Weaviate:
- Agent queries: *"authentication service"* → gets the 5 most semantically relevant chunks
- Grounded in actual code: real file paths, real function names, real patterns
- Fast: sub-100ms queries on a laptop for 50k+ chunks

**Why Weaviate (not Chroma/Qdrant/Pinecone)?**

| | Weaviate | Chroma | Qdrant |
|--|---------|--------|--------|
| Local binary (no Docker) | ✅ | ✅ | ✅ |
| Hybrid search built-in | ✅ | ❌ | ✅ |
| BM25 + vector fusion | ✅ | ❌ | ✅ |
| Multi-tenancy | ✅ | ❌ | ✅ |
| Mature Python client v4 | ✅ | ✅ | ✅ |

---

## Module-Wise Embeddings and Classification

The key to good RAG is **what you store alongside the vector**, not just the vector itself.

Each chunk is classified into:

| Dimension | Values | Used For |
|-----------|--------|----------|
| `module` | `auth`, `billing`, `notifications`, `users`, `api`, `ui`, etc. | Filter by feature area |
| `doc_type` | `service`, `controller`, `component`, `test`, `schema`, `config`, `spec` | Filter by layer |
| `category` | `business-logic`, `data-access`, `api-contract`, `ui-component`, `infrastructure` | Semantic grouping |
| `language` | `typescript`, `python`, `vue`, `markdown` | Language-specific queries |

This lets agents ask precise questions:
- *"authentication service business logic"* → only auth module, service doc_type
- *"billing component UI"* → only billing module, component doc_type

See [docs/embeddings.md](docs/embeddings.md) for the classification algorithm.

---

## Re-ranking

Bi-encoder (embedding model) is fast but imprecise — it scores each chunk independently.
Cross-encoder re-ranking reads the query AND each chunk together — much more accurate.

```
Query: "how does the email notification retry logic work?"

Bi-encoder top-20:
  1. notifications/<email-sender> (score: 0.82)       ← correct
  2. users/<event-handler> (score: 0.80)              ← partially relevant
  3. scheduler/<job-runner> (score: 0.78)             ← noise
  ...

Cross-encoder re-ranked top-5:
  1. notifications/<email-sender> (score: 0.94)       ← correct, now #1
  2. notifications/<retry-handler> (score: 0.91)      ← relevant, was #7
  3. scheduler/<notification-processor> (score: 0.73)
```

Use `--rerank` flag in `query_rag.py`. See [docs/reranking.md](docs/reranking.md).

---

## Setting Up for Any Project

### Step 1: Copy templates

```bash
cp templates/CLAUDE.md /path/to/your/project/CLAUDE.md
cp -r templates/cursor-rules /path/to/your/project/.cursor/rules/
```

Edit `CLAUDE.md` to describe your project's stack, commands, and conventions.

### Step 2: Configure the scripts for your project

The scripts use two environment variables:
- `AGENTS_WEAVIATE_URL` — Weaviate URL (default: `http://localhost:8090`)
- `PROJECT_ROOT` — path to your repo
- `--project <name>` — namespace for your collections (e.g. `myapp`)

No hardcoded paths. Multiple projects can share one Weaviate instance.

### Step 3: Define your modules

Edit `scripts/update_kb.py` and set `MODULE_PATTERNS` for your project structure. Example patterns are provided for NestJS, Django, Rails, Spring, and flat structures.

### Step 4: Point your AI tool at the agents

**Cursor:** Add the `cursor/agents/` folder to your workspace. Reference playbooks by path in Composer.

**Claude Code:** Copy `claude/commands/` to your project's `.claude/commands/`. Commands become `/solution`, `/code`, `/review-code`, etc.

---

## Using Jira MCP + GitHub MCP

See [docs/mcp-guide.md](docs/mcp-guide.md). Summary:

**Jira MCP** — in solution-approach and controller agents:
```
# Fetches ticket title, description, acceptance criteria automatically
mcp__mcp-atlassian__jira_get_issue(issue_id: "PROJ-1234")
```

**GitHub MCP** — in pr-review-agent and pr-review-kb:
```
# Fetches PR diff, existing comments, review threads
mcp__github__get_pull_request(owner, repo, pull_number)
mcp__github__get_pull_request_files(owner, repo, pull_number)
```

---

## Review Patterns for Large Teams (100+ Developers)

See [docs/team-scale.md](docs/team-scale.md). Key concepts:

1. **ReviewPatterns collection** — every merged PR's review comments indexed into Weaviate
2. **Pattern extraction** — comments categorized: security, performance, testing, style, architecture
3. **Agent-assisted review** — before raising a PR, the code-review agent queries ReviewPatterns to surface team-specific feedback patterns
4. **Weekly refresh** — `update_pr_kb.py --limit 100` indexes recent merged PRs

This means a team of 100 devs can capture review patterns across 1000 PRs and have every agent benefit from collective knowledge.

---

## Organization-Wide Rollout

Once the setup works for one repo:

1. **Publish this repo** as a shared tool in your org's GitHub
2. **Create an org-level Weaviate** (Weaviate Cloud or self-hosted) — one instance for all repos
3. **Use `--project <repo-name>`** flag to namespace each project's collections
4. **Standardize `CLAUDE.md`** — have a base template all repos extend
5. **Central PR patterns** — run `update_pr_kb.py` on all repos to build org-wide review intelligence
6. **Claude/Cursor rules** — checked into each repo, auto-loaded per project

Any developer on any repo gets: RAG context, review patterns, solution history, coding standards — from day one.

---

## Cheat Sheet

```bash
# Start Weaviate
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/start_weaviate.py

# Index codebase
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --repo-root $PROJECT_ROOT --project myapp

# Index coding standards
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --standards --repo-root $PROJECT_ROOT --project myapp

# Index PR review history
cd $PROJECT_ROOT
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_pr_kb.py \
  --limit 100 --include-open --project myapp

# Query RAG
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/query_rag.py \
  "your query here" --project myapp --rerank

# Check stats
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_kb.py \
  --stats --project myapp
```

---

## Docs Index

| Doc | What It Covers |
|-----|----------------|
| [docs/developer-guide.md](docs/developer-guide.md) | **Start here** — `/configure`, mindset shift, step-by-step agent commands, how to review output |
| [docs/rag-basics.md](docs/rag-basics.md) | RAG fundamentals, chunking, retrieval, injection |
| [docs/vector-db-setup.md](docs/vector-db-setup.md) | Weaviate install, HNSW, BM25, hybrid search, tuning |
| [docs/embeddings.md](docs/embeddings.md) | Module classification, doc_type taxonomy, category schema |
| [docs/reranking.md](docs/reranking.md) | Cross-encoder re-ranking, when to use it, performance tradeoffs |
| [docs/team-scale.md](docs/team-scale.md) | Review patterns KB, org-wide rollout, 100+ dev teams |
| [docs/mcp-guide.md](docs/mcp-guide.md) | Jira MCP, GitHub MCP, tool use in agents |
| [cursor/README.md](cursor/README.md) | Full Cursor setup guide |
| [claude/README.md](claude/README.md) | Full Claude Code setup guide |
