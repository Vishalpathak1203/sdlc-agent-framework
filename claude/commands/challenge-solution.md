# Challenge Solution — Adversarial Solution Review

Stress-test a proposed solution approach before implementation begins.
Challenges assumptions, surfaces hidden risks, and forces the solution to
earn its approval rather than glide through.

**Usage:**
- `/challenge-solution PROJ-123` — challenge the stored solution for a ticket
- `/challenge-solution` — challenge the solution in the current context

**Target:** $ARGUMENTS

---

## Step 1 — Load the Solution

If a ticket ID was provided:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --get-solution "$ARGUMENTS" --project $AGENTS_PROJECT
```

If no ticket ID, ask the user to paste the solution approach or confirm the
current context contains it.

Verify solution status is `draft`. If already `approved`, confirm the user
wants to challenge it again before proceeding.

---

## Step 2 — Query for Contradicting Evidence

Search the codebase and review history for patterns that challenge the
solution's assumptions:

```bash
# Find how the area being changed currently works
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<core mechanism the solution changes>" \
  --project $AGENTS_PROJECT --multi-query --rerank --top 8

# Find past review comments on similar changes
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<change type> risk pitfall" \
  --collection reviews --project $AGENTS_PROJECT --rerank --top 10

# Find relevant standards the solution must comply with
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  "<domain> constraints rules" \
  --collection standards --project $AGENTS_PROJECT --top 5
```

---

## Step 3 — Apply the Challenge Framework

For each item below, produce a concrete finding (not a generic warning).
Reference actual file paths, function names, or PR patterns from the RAG context.

### 3.1 Assumption Audit
List every implicit assumption the solution makes. For each:
- Is it verified by the RAG context?
- What breaks if the assumption is wrong?

### 3.2 Scope Creep / Scope Gap
- Does the solution touch files outside the stated scope? Should it?
- Are there dependencies that must change but aren't mentioned?
- Does the testing plan cover the actual acceptance criteria?

### 3.3 Edge Cases Not Handled
- What inputs would break the proposed implementation?
- Race conditions, null paths, empty collections, concurrent requests?
- What happens at the boundary (0, 1, max values)?

### 3.4 Past Mistakes (from ReviewPatterns)
- Has this type of change been flagged in past PRs?
- Are there known pitfalls the team has already been burned by?

### 3.5 Performance & Scalability
- Does the solution introduce N+1 queries, missing indexes, or unbounded loops?
- Would it degrade at 10× current load?

### 3.6 Security Surface
- Does the change expose new endpoints, modify auth logic, or touch PII?
- Are inputs validated and outputs sanitized?

### 3.7 Reversibility
- Can this change be rolled back safely if it causes issues in production?
- Is a feature flag or dark launch needed?

---

## Step 4 — Produce the Challenge Report

```markdown
# Solution Challenge: $ARGUMENTS

## Verdict
PASS / NEEDS_REVISION / BLOCK

## Critical Issues (must fix before approval)
- [CRITICAL] <finding> — <file or PR reference>

## Significant Issues (should fix)
- [SIGNIFICANT] <finding>

## Minor Issues (consider fixing)
- [MINOR] <finding>

## Confirmed Strengths
- <what the solution gets right>

## Recommended Changes
1. <specific change to the solution approach>
2. <specific change>
```

---

## Step 5 — Decision

**PASS:** Proceed to update solution status:
```bash
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py \
  --update-solution "$ARGUMENTS" \
  --status approved \
  --review-notes "<summary of challenge findings>" \
  --project $AGENTS_PROJECT
```

**NEEDS_REVISION:** Present the report to the developer. Solution stays in
`draft` until revised and re-challenged.

**BLOCK:** Critical issues that prevent implementation. Stop the pipeline.
Document the blocker so it's visible in the solution record.

---

## Checklist

```
Challenge Solution — $ARGUMENTS:
- [ ] Solution loaded and status confirmed
- [ ] RAG queried for contradicting evidence (codebase + reviews + standards)
- [ ] Assumption audit complete
- [ ] Scope gap / creep assessed
- [ ] Edge cases identified
- [ ] Past review patterns checked
- [ ] Performance concerns evaluated
- [ ] Security surface reviewed
- [ ] Reversibility assessed
- [ ] Challenge report produced with verdict
- [ ] Solution status updated (approved / stays draft)
```
