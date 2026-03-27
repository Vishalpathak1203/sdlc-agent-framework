# Controller Agent — Ticket Pipeline Orchestrator

**When:** Entry point for any Jira ticket. Sequences the full SDLC pipeline.
**Model:** `claude-haiku-3-5` (delegates to correct model at each stage)
**Purpose:** One playbook to run per ticket. Handles state, sequencing, and gates.

---

## Configuration (set once per project)

```
PROJECT: <your-project-name>          # e.g. myapp
VENV: ~/.sdlc-agents-venv/bin/python
SCRIPTS: /path/to/sdlc-agent-framework/scripts
WEAVIATE_URL: http://localhost:8090
TICKET_PREFIX: <PROJ>                  # e.g. DR, JIRA, MYAPP
```

---

## How to Start

In Cursor Composer:

```
I am starting work on ticket: [TICKET-ID]
Title: [paste ticket title]

Description:
[paste full Jira description and acceptance criteria]

Begin the ticket pipeline. Follow the controller playbook.
PROJECT=myapp, WEAVIATE_URL=http://localhost:8090
```

If you have Jira MCP configured, just provide the ticket ID — the controller will fetch details automatically.

---

## Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  TICKET: [TICKET-ID]                                        │
├─────────────────────────────────────────────────────────────┤
│  Stage 1 → solution-approach   [haiku + RAG]               │
│  Stage 2 → solution-review     [sonnet]       ← GATE ✋    │
│  Stage 3 → code-agent          [haiku + RAG]               │
│  Stage 4 → code-review         [sonnet]       ← GATE ✋    │
│  Stage 5 → raise PR                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Stage 1 — Solution Approach

Follow [solution-approach.md](solution-approach.md).

Output when complete:
```
=== STAGE 1 COMPLETE ===
Solution approach stored in Weaviate for [TICKET-ID].
Ready for Stage 2 (solution review).
Type "review solution" to continue.
```

## Stage 2 — Solution Review ✋ GATE

Only proceed when user types **"review solution"**.

Switch to sonnet. Follow [solution-review.md](solution-review.md).

Output when complete:
```
=== STAGE 2 COMPLETE ===
Verdict: APPROVED / CHANGES REQUESTED

If APPROVED → type "write code" to proceed to Stage 3.
If CHANGES REQUESTED → type "revise solution" to loop back with:
  <list required changes>
```

## Stage 3 — Code Agent

Only proceed when user types **"write code"**.

Switch back to haiku. Follow [code-agent.md](code-agent.md).

Output when complete:
```
=== STAGE 3 COMPLETE ===
All changes implemented for [TICKET-ID].
Files changed:
  - <list files>

Type "review code" to proceed to Stage 4.
```

## Stage 4 — Code Review ✋ GATE

Only proceed when user types **"review code"**.

Switch to sonnet. Follow [code-review.md](code-review.md).

Output when complete:
```
=== STAGE 4 COMPLETE ===
Verdict: APPROVED / CHANGES REQUESTED

If APPROVED → type "raise pr" for next steps.
If CHANGES REQUESTED → type "fix code" to loop back to Stage 3 with:
  <list required fixes>
```

## Stage 5 — Raise PR

Only proceed when user types **"raise pr"**.

Before pushing: ensure safe-commit passed (typecheck + lint + test). If not, run them now.

```bash
git push -u origin HEAD
gh pr create \
  --title "[TICKET-ID]: <title>" \
  --body "$(cat <<'EOF'
## Summary
<1-3 bullet summary of changes>

## Ticket
[TICKET-ID]

## Test Plan
- [ ] Unit tests pass
- [ ] Lint passes
- [ ] Type check passes

EOF
)"
```

Output the PR URL to the user.

```
=== PIPELINE COMPLETE ===
PR raised: <url>
[TICKET-ID] is ready for human review.
```

---

## Loop Handling

**"revise solution"** → Return to Stage 1 with review notes:
```bash
$VENV $SCRIPTS/query_rag.py --get-solution [TICKET-ID] --project $PROJECT
```
Revise based on feedback. Re-run Stage 2.

**"fix code"** → Return to Stage 3 with code review notes. Re-run Stage 4.

---

## State Tracking

When user asks "where are we?":
```
Pipeline status for [TICKET-ID]:
✅ Stage 1: Solution approach — DONE
✅ Stage 2: Solution review   — APPROVED
🔄 Stage 3: Code agent        — IN PROGRESS
⬜ Stage 4: Code review
⬜ Stage 5: Raise PR
```

---

## Checklist

```
Ticket Pipeline — [TICKET-ID]:
- [ ] Stage 1: Solution approach drafted + stored
- [ ] Stage 2: Solution approved by review
- [ ] Stage 3: Code implemented (TDD)
- [ ] Stage 4: Code review passed
- [ ] Stage 5: PR raised
```
