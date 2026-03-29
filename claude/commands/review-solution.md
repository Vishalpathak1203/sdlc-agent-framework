# Review Solution — Gate: Approve or Block a Solution Approach

Human-in-the-loop gate for solution approaches. Reviews a drafted solution
against codebase reality, standards, and past review patterns before
implementation begins. Blocks or approves progression in the SDLC pipeline.

**Usage:**
- `/review-solution PROJ-123` — review the stored solution for a ticket
- `/review-solution` — review solution in the current context

**Target:** $ARGUMENTS

---

## Step 1 — Load the Solution

If a ticket ID was provided:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "$ARGUMENTS" --project $AGENTS_PROJECT
```

If no ticket ID, ask the user to paste the solution or confirm the current
context contains it.

Verify the solution status is `draft`. If already `approved`, confirm the
user wants to re-review before proceeding.

---

## Step 2 — Verify Against Codebase Reality

For each file the solution claims to change:

```bash
# Does the file exist? Does the function exist?
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<file or function name>" \
  --project $AGENTS_PROJECT --rerank --top 5
```

Flag any file paths, function names, or patterns in the solution that do
NOT appear in the codebase KB. These are hallucinations.

---

## Step 3 — Query Review History for This Area

```bash
# Has this area been flagged in past PRs?
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<module or feature name> review feedback" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 10

# Does the solution approach match team patterns?
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<change type> pattern pitfall" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 8

# Check relevant standards
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<domain> standards constraints" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

---

## Step 4 — Apply the Review Framework

For each dimension below, produce a concrete finding — not a generic warning.
Reference actual file paths, function names, or PR patterns from RAG context.

### 4.1 Completeness
- Does the solution identify all files that must change?
- Are database migrations, schema changes, or config updates included?
- Are callers of changed functions listed in the blast radius?
- Does the testing plan match the acceptance criteria?

### 4.2 Correctness
- Do the file paths and function names actually exist in the codebase?
- Does the implementation approach match how similar features work?
- Are existing abstractions/patterns being respected?

### 4.3 Edge Cases
- Are null/empty/boundary inputs handled?
- Are concurrent or async race conditions considered?
- What happens on failure — is rollback addressed?

### 4.4 Standards Compliance
- Does the approach follow the coding standards in Weaviate?
- Are naming conventions, module structure, and patterns respected?
- Does the testing plan satisfy test coverage requirements?

### 4.5 Risk Assessment
- What is the blast radius? What could break?
- Is this change reversible in production without a deploy?
- Does it touch auth, payments, or PII? If so — is that documented?

### 4.6 Past Mistakes
- Has this type of change been flagged in past PRs?
- Is the approach the same as a pattern the team has already been burned by?

---

## Step 5 — Produce the Review Report

```markdown
## Solution Review: $ARGUMENTS

### Verdict
APPROVED / NEEDS_REVISION / BLOCKED

### Summary
<2–3 sentences on overall quality and readiness to implement>

### Critical Issues (must fix before implementation)
- [CRITICAL] <issue> — <evidence from codebase or review history>

### Significant Issues (should fix)
- [SIGNIFICANT] <issue>

### Minor Issues (consider)
- [MINOR] <issue>

### Confirmed Correct
- <what the solution gets right, with specifics>

### Required Changes Before Approval
1. <concrete change to the solution document>
2. <concrete change>
```

---

## Step 6 — Decision and Status Update

**APPROVED:** Update solution status:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --update-solution "$ARGUMENTS" \
  --status approved \
  --review-notes "<one-sentence summary of review outcome>" \
  --project $AGENTS_PROJECT
```

**NEEDS_REVISION:** Present the report. Solution stays `draft` until the
developer revises and re-submits for review.

**BLOCKED:** Document the blocker. Do not update status. Escalate to the team.

---

## Checklist

```
Review Solution — $ARGUMENTS:
- [ ] Solution loaded and status confirmed
- [ ] All referenced files verified in codebase KB
- [ ] Hallucinated paths or functions identified
- [ ] Review history queried for this module
- [ ] Completeness checked (blast radius, migrations, callers)
- [ ] Edge cases and risk assessed
- [ ] Past mistakes checked against ReviewPatterns
- [ ] Review report produced with verdict
- [ ] Status updated in Weaviate (or blocked)
```
