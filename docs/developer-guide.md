# Developer Guide: Becoming an Agent Manager

This guide is for developers who are new to AI-assisted development. It covers the mindset shift, how to run each agent command step by step, and how to review and direct agent output effectively.

---

## The Mindset Shift

Traditional development: **You write code.**

Agent-assisted development: **You direct agents and review their work.**

Your job changes from:
- Writing functions → **Defining requirements clearly in ticket descriptions**
- Debugging logic → **Reviewing agent output and pointing out what's wrong**
- Remembering patterns → **Letting RAG surface the patterns; you validate them**
- Writing tests → **Reviewing test coverage and specifying edge cases the agent missed**

You become a **senior reviewer and decision-maker**, not a typist.

**The agent is fast but not infallible.** It will produce ~80% correct work on the first pass. Your 20% — catching domain mistakes, flagging wrong assumptions, redirecting — is what makes the output production-ready.

---

## Prerequisites Checklist

Before running any agents, complete these one-time steps:

```bash
# 1. Clone the framework
git clone https://github.com/Vishalpathak1203/sdlc-agent-framework.git
cd sdlc-agent-framework
export AGENTS_ROOT=$(pwd)

# 2. Create Python virtual environment
uv venv ~/.sdlc-agents-venv
uv pip install --python ~/.sdlc-agents-venv/bin/python -r scripts/requirements.txt

# 3. Start Weaviate (keep this terminal open permanently)
~/.sdlc-agents-venv/bin/python "$AGENTS_ROOT/scripts/start_weaviate.py"
```

**Steps 4–6 are handled automatically by `/configure`.** See below.

---

## Step 0 — Configure for Your Stack (Run Once Per Project)

Before anything else, run the configure command. It detects your tech stack, maps your directories to modules, writes all config files, and runs the first KB index — all in one shot.

**Claude Code:**
```
/configure /path/to/your/project
```

Or if you're already inside your project directory in the Claude Code session:
```
/configure
```

**Cursor:** Open Composer → reference `cursor/agents/configure.md` → type the project path → send.

**What the configure command does automatically:**
1. Detects your stack (NestJS, Django, Rails, Spring Boot, Next.js, Go, Laravel, etc.)
2. Scans your directories and maps them to module names (`auth`, `payments`, `orders`, etc.)
3. Detects your test/lint/build commands
4. Writes `CLAUDE.md` tailored to your stack
5. Writes `.claude/settings.json` with correct script paths and permissions
6. Copies all 10 agent commands into your project
7. Initializes the Weaviate schema for your project
8. Runs the first full KB index
9. Runs a test query to confirm RAG is working

**Before it writes anything**, it shows you a full summary and asks for confirmation. You can correct anything — wrong module names, missed directories, wrong test command — before it proceeds.

After `/configure` completes, you're ready to run all other agents.

---

## Supported Stacks

`/configure` handles these stacks out of the box:

| Stack | Detected by |
|-------|------------|
| NestJS (TypeScript) | `@nestjs/core` in package.json |
| Nuxt / Vue 3 | `nuxt` in package.json |
| Next.js / React | `next` in package.json |
| Express / Fastify | `express`/`fastify` in package.json |
| Django | `django` in requirements.txt |
| FastAPI | `fastapi` in requirements.txt |
| Flask | `flask` in requirements.txt |
| Ruby on Rails | Rails in Gemfile |
| Spring Boot | pom.xml / build.gradle present |
| Go | go.mod present |
| Laravel | `laravel` in composer.json |
| Rust | Cargo.toml present |
| Monorepo | pnpm-workspace.yaml / nx.json / turbo.json / apps/ dir |

For anything not in this list, the configure agent falls back to scanning directory names and detecting patterns generically — it will still produce a usable config, but you may want to review and tune the generated `project-<name>.py` file.

---

## The 9-Agent Pipeline: When to Run What

```
Daily / per-ticket:
  [1] knowledge-update   ← run when code has changed since last session
  [2] standards-update   ← run when coding standards docs have changed
  [3] pr-review-kb       ← run weekly to keep review patterns current

Per-ticket (in order):
  [4] solution-approach  ← draft solution for a Jira ticket
  [5] solution-review    ← YOU review the draft           ← HUMAN GATE ✋
  [6] code-agent         ← implement the approved solution
  [7] code-review        ← YOU review the implementation  ← HUMAN GATE ✋
  [8] unit-test-review   ← audit test quality
  [9] pr-review-agent    ← respond to GitHub reviewer comments
   +  safe-commit        ← validate before every commit
```

---

## Step-by-Step: Running Each Agent

### Step 1 — Update the Knowledge Base

**When:** Start of each work session, or after merging branches.

**Claude Code:**
```
/update-kb
```

**Cursor:** Open Composer → reference `cursor/agents/knowledge-update.md` → send.

**What it does:** Crawls your codebase, re-embeds changed files, updates Weaviate. Unchanged files are skipped (hash comparison).

**Your job after:** Check the output line counts. If it shows 0 files updated when you know code changed, run with `--full` flag.

---

### Step 2 — Update Standards (when rules change)

**When:** Your team updates lint rules, architecture docs, or coding standards.

**Claude Code:**
```
/update-kb
```
(same command — it has a `--standards` mode built in; or run the standards step separately as shown in the cheat sheet)

**What it does:** Indexes your coding standards and architecture decision records into `CodingStandards` collection.

---

### Step 3 — Update PR Review Patterns (weekly)

**When:** Weekly, or before starting a new feature area.

**Claude Code:**
```
/update-pr-kb
```

**What it does:** Fetches the last 100 merged PRs via GitHub MCP, extracts review comments, categorizes them (security, performance, testing, architecture), stores them in `ReviewPatterns`.

**Your job after:** Nothing required. The next time a code-review agent runs, it will automatically draw from this knowledge.

---

### Step 4 — Draft a Solution Approach

**When:** You have a Jira ticket and are ready to plan implementation.

**Claude Code:**
```
/solution PROJ-1234
```

**Cursor:** Open Composer → reference `cursor/agents/solution-approach.md` → type `Ticket: PROJ-1234` → send.

**What it does:**
1. Fetches the Jira ticket (title, description, acceptance criteria) via MCP
2. Queries RAG: finds relevant services, schemas, patterns in your codebase
3. Queries `CodingStandards` for applicable rules
4. Produces a structured solution: files to create/modify, approach rationale, risks

**Your job after (GATE):** This is your first gate. Read the solution carefully and ask yourself:

> - Does the agent understand what the ticket is actually asking?
> - Are the files it plans to touch the right ones?
> - Is the approach consistent with how similar features work in the codebase?
> - Are there side effects the agent hasn't mentioned?

**If something is wrong:** Reply directly in the chat:
```
The solution mentions modifying <orders/payment-handler> but that file handles
refunds, not new payments. Use <payments/checkout-handler> instead.
Also, you missed that this feature requires updating the order status schema.
```

**If it looks right:** Reply: `Approved. Proceed to implementation.`

---

### Step 5 — Implement the Code

**When:** After you have approved the solution approach.

**Claude Code:**
```
/code PROJ-1234
```

**Cursor:** Open Composer → reference `cursor/agents/code-agent.md` → type `Ticket: PROJ-1234` → send.

**What it does:**
1. Retrieves the approved solution from `SolutionApproach` collection
2. Queries RAG for existing code patterns to follow
3. Implements using TDD: writes failing tests first, then makes them pass
4. Follows your project's file naming, module structure, error handling conventions

**Your job after (GATE):** This is your most important gate. Review the diff as you would any PR:

> - Does every new function have a corresponding test?
> - Are edge cases handled (null inputs, empty arrays, API failures)?
> - Are there magic numbers or hardcoded strings that should be constants?
> - Does the implementation match your project's patterns (not a generic solution)?
> - Is there anything the agent invented that doesn't exist in your codebase?

**Giving correction feedback:**
```
The test for the error case is asserting the wrong status code. Our API
returns 422 for validation errors, not 400. Also, the agent used a raw
fetch() call — we use the <http/api-client> wrapper everywhere. Fix both.
```

---

### Step 6 — Review Test Quality

**When:** After code implementation, before committing.

**Claude Code:**
```
/unit-test-review
```

**What it does:** Audits the test files against `CodingStandards` and `ReviewPatterns`. Checks for: missing edge cases, incorrect mocking patterns, missing assertions, test isolation.

**Your job after:** Read the audit report. If the agent flags gaps you agree with, ask it to fill them. If it flags a "gap" that's intentional (e.g., an integration test is elsewhere), tell it so.

---

### Step 7 — Safe Commit

**When:** Before every `git commit`.

**Claude Code:**
```
/safe-commit
```

**What it does:** Runs lint, type-check, tests. Reads the diff and generates a conventional commit message following your project's format. Shows you the message for approval before committing.

**Your job after:** Read the generated commit message. Edit it if the description is inaccurate. Approve to proceed.

---

### Step 8 — Respond to PR Review Comments

**When:** After pushing a PR and receiving reviewer comments.

**Claude Code:**
```
/pr-review 123
```
(where 123 is the PR number)

**What it does:**
1. Fetches the PR diff and all reviewer comments via GitHub MCP
2. For each comment: decides whether to accept, push back, or ask for clarification
3. Makes code changes where the reviewer is correct
4. Drafts polite responses where the reviewer may be mistaken
5. Submits the review responses via GitHub MCP

**Your job after:** Read the drafted responses before they are submitted. Make sure the agent hasn't:
- Agreed to something you don't want to change
- Pushed back in a way that sounds defensive
- Missed the reviewer's actual concern

---

## How to Give Effective Feedback to Agents

### Be specific about what's wrong

Bad: `This isn't right.`

Good: `The agent is importing from <auth/user-model> but in this project, user models live in <users/schema>. Fix the import path.`

### Reference real files and functions

The agent can read your codebase. If you say "follow the pattern in `<payments/gateway-connector>`", it will look it up.

### Tell the agent what you know that it doesn't

The agent doesn't know:
- That a third-party API has a bug at a specific endpoint
- That a particular pattern was abandoned six months ago
- That a specific PR reviewer cares deeply about test coverage

You do. Say so explicitly.

### Separate "must fix" from "nice to have"

```
MUST FIX: The retry logic is missing — the ticket explicitly requires 3 retries.
NICE TO HAVE: Consider extracting the validation into a helper, but it's fine as-is.
```

---

## What Good Agent Output Looks Like

### Solution approach output
- References actual files that exist in your codebase (not invented ones)
- Identifies the correct layer to modify (service vs controller vs schema)
- Notes risks and side effects
- Is achievable in one PR (not trying to refactor everything)

### Code output
- Follows your project's naming conventions exactly
- Imports from the right modules
- Tests cover the happy path, error cases, and edge cases
- No `any` types, no commented-out code, no debug logs

### What to flag and correct
- Any file path that doesn't exist in the codebase
- Any pattern that contradicts your coding standards
- Missing test cases for error scenarios
- Unused imports or dead code

---

## Common Mistakes and How to Fix Them

### "The agent invented a file that doesn't exist"

This means RAG didn't find the right context. Run `/update-kb` to refresh the knowledge base, then retry. If it persists, the relevant file may need better module classification — check `MODULE_PATTERNS` in `update_kb.py`.

### "The agent used the wrong pattern"

Add the correct pattern to your coding standards documents and re-run `/update-kb --standards`. The agent will find it in `CodingStandards` next time.

### "The agent keeps making the same mistake"

This is the most valuable signal. Add a rule to your `.cursor/rules/` or `CLAUDE.md` that explicitly prohibits the wrong pattern and specifies the right one. Then update the KB.

### "The solution approach missed important context"

Update the Jira ticket description to include the missing context, then re-run `/solution`. Better ticket descriptions → better agent output.

---

## Daily Workflow Summary

```
Morning:
  1. /update-kb                    ← sync codebase changes overnight

Per ticket:
  2. /solution PROJ-XXXX             ← agent drafts the plan
  3. Review + correct              ← YOU approve or redirect
  4. /code PROJ-XXXX                 ← agent implements
  5. Review diff + give feedback   ← YOU review as you would a junior dev's PR
  6. /unit-test-review             ← agent audits tests
  7. /safe-commit                  ← agent runs checks + generates commit message
  8. Push PR

After PR review comments:
  9. /pr-review <PR number>        ← agent responds to reviewers
 10. Review responses              ← YOU approve before submission

Weekly:
 11. /update-pr-kb                 ← index recent review patterns
```

---

## Cursor vs Claude Code

| | Claude Code | Cursor |
|--|------------|--------|
| Invoke agent | `/command` in chat | Reference `.md` playbook in Composer |
| Context | Reads project CLAUDE.md automatically | Reads `.cursor/rules/` automatically |
| Best for | Terminal + file editing workflows | IDE-integrated, visual diff review |
| Model selection | Set in Claude Code settings | Set per-agent in playbook frontmatter |

Both tools use the same RAG scripts and the same Weaviate instance. You can switch between them for different tasks.

---

## Escalating Beyond Agents

Agents are not a replacement for engineering judgment. Escalate to manual work when:

- The ticket involves a fundamental architectural change that affects 10+ modules
- The agent has been corrected 3+ times on the same issue without improvement
- The change requires knowledge that cannot be expressed in code (e.g., legal requirements, infrastructure access)
- The codebase context is so outdated that RAG results are unreliable (run `--full` re-index first)

In these cases, use the agent for the parts it's good at (boilerplate, tests, PR responses) and write the critical logic yourself.
