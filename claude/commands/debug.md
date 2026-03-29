# Debug — RAG-Grounded Bug Investigation

Investigate a bug, error, or unexpected behavior. Uses the codebase KB and
review patterns to ground the investigation in actual code, not assumptions.

**Usage:**
- `/debug` — debug from current error/context
- `/debug "error message or description"` — debug a specific error
- `/debug PROJ-123` — debug a reported bug ticket

**Input:** $ARGUMENTS

---

## Step 1 — Capture the Problem

If $ARGUMENTS is a ticket ID, fetch it:
```
mcp__mcp-atlassian__jira_get_issue(issue_id: "$ARGUMENTS")
```

Otherwise extract from $ARGUMENTS or current context:
- Error message (exact text)
- Stack trace (which file, which line)
- Steps to reproduce
- Expected vs. actual behavior
- Environment (dev / staging / production)

---

## Step 2 — Query Weaviate for the Affected Code

```bash
# Find the code around the error
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<error message or affected function>" \
  --project $AGENTS_PROJECT --multi-query --rerank --top 8

# Scope to the affected module if known
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<error context>" \
  --collection codebase --module <module> \
  --project $AGENTS_PROJECT --rerank --top 5

# Check if this pattern has appeared in past PRs
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<error type or behavior>" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 8
```

---

## Step 3 — Read the Relevant Files

Based on the stack trace and RAG results:
1. Read the file where the error originates
2. Read callers up the call stack (2–3 levels)
3. Read the test file — does a test cover this path?

Do NOT propose a fix before reading the actual code.

---

## Step 4 — Root Cause Analysis

Work through these layers in order:

**Layer 1 — Data**
- Is the input what we expect? (null, empty, wrong type, wrong shape)
- Is the database/API returning what we expect?
- Is a cache returning stale data?

**Layer 2 — Logic**
- Is there a missing guard clause or null check?
- Is an `if` branch handling the wrong case?
- Is an async operation not being awaited?
- Is there a race condition between concurrent operations?

**Layer 3 — Integration**
- Is a dependency (service, library, external API) behaving differently than expected?
- Did a contract change (DTO, schema, API response shape) without updating the consumer?
- Is an environment variable missing or misconfigured?

**Layer 4 — Infrastructure**
- Is this a deployment issue (wrong build, missing migration, wrong config)?
- Is this environment-specific?

---

## Step 5 — Propose and Implement the Fix

State the root cause clearly before writing any code:

```
Root cause: <one sentence>
Fix: <one sentence>
Risk: <what could the fix break?>
```

Then implement the minimal fix:
- Do not refactor surrounding code unless it is part of the bug
- Do not add features while fixing the bug
- Add or update the test that would have caught this

---

## Step 6 — Verify

```bash
# Run the specific test covering the fixed path
<test-runner> <spec-file>

# Run the full module tests
<test-runner> --module <module>

# Run lint and type-check
<lint-command> && <type-check-command>
```

All must pass before committing.

---

## Checklist

```
Debug — $ARGUMENTS:
- [ ] Problem captured (error, steps to reproduce, expected vs. actual)
- [ ] Weaviate queried for affected code and past patterns
- [ ] Relevant files read (not just the error line — callers too)
- [ ] Root cause identified (data / logic / integration / infra)
- [ ] Fix scoped to the root cause (no unrelated changes)
- [ ] Test added or updated that covers the fixed path
- [ ] Full test suite passes
- [ ] Root cause documented in commit message
```
