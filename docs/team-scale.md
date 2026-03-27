# Review Patterns for Large Teams (100+ Developers)

At scale, the biggest problem isn't writing code — it's knowledge distribution. A senior engineer on Team A learned the hard way about a subtle concurrency bug. Six months later, a developer on Team B makes the same mistake because the lesson was never captured.

This framework solves that with the **ReviewPatterns collection**.

---

## The Core Idea

Every time a PR is merged, the reviewer's comments represent a micro-lesson. Over 1000 PRs, you have 1000 lessons. Index them. Make every agent benefit from all of them.

```
PR #1234: "Missing index on user_id — this will cause full table scans"
PR #1235: "Don't store session tokens in localStorage — use httpOnly cookies"
PR #1400: "This query runs N+1 — use a JOIN or DataLoader"
PR #2100: "Same N+1 issue, different file"  ← pattern emerging

Agent: "I see you're writing a loop that queries the DB — our PRs show
       this pattern causes N+1 issues (PR #1235, #1400, #2100). Consider..."
```

---

## Building the ReviewPatterns KB

### Initial build (run once)

```bash
cd /path/to/your/repo
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_pr_kb.py \
  --limit 200 --include-open --project myapp
```

### Weekly refresh (add to cron or CI)

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
~/.sdlc-agents-venv/bin/python $AGENTS_ROOT/scripts/update_pr_kb.py \
  --limit 50 --project myapp
```

---

## Comment Categorization

Each review comment is automatically categorized:

| Category | Trigger Keywords | Example |
|----------|-----------------|---------|
| `security` | token, password, auth, xss, injection, csrf, secret | "Don't log the auth token" |
| `performance` | n+1, index, slow, cache, query, memory, loop | "This causes N+1 queries" |
| `testing` | test, coverage, mock, assert, spec, edge case | "Missing error case test" |
| `correctness` | bug, wrong, incorrect, undefined, null, crash | "This will crash on null input" |
| `architecture` | pattern, structure, module, dependency, coupling | "This should be in the service layer" |
| `style` | naming, format, lint, convention, readability | "Use camelCase for this variable" |

Categorization is keyword-based first, then semantic (embedding similarity to category descriptions) for ambiguous comments.

---

## Using ReviewPatterns in Code Review

The `code-review` agent queries ReviewPatterns before giving feedback:

```
## Step 2 — Query review patterns

Run:
python query_rag.py "database query loop" --collection reviews --project myapp --top 5 --rerank

If results found: include the team's historical patterns as additional review criteria.
Prefix such feedback with: "Team pattern (PR #{number}):"
```

Example output in code review:
```
### Security Issues
- Line 42: You're storing the JWT in a variable that gets logged.
  Team pattern (PR #891): "Never log tokens or secrets — use a sanitizer middleware"

### Performance Issues
- Line 78: This loops over orders and queries the DB for each one.
  Team pattern (PR #1400, #2100): "N+1 pattern — use batch query or JOIN"
```

---

## Multi-Repo at Scale

For 100+ developers across many repos:

### Option A: Shared Weaviate (Recommended)

Deploy one Weaviate instance (cloud or self-hosted). Each repo uses a different `--project` namespace:

```
myapp-api      → CodebaseKnowledge_myapp_api, ReviewPatterns_myapp_api
myapp-ui       → CodebaseKnowledge_myapp_ui, ReviewPatterns_myapp_ui
legacy-service → CodebaseKnowledge_legacy_service, ...
```

Agents can query across projects:
```bash
# Query ALL repos' review patterns
python query_rag.py "authentication bug" --collection reviews --project "*"
```

### Option B: Per-Team Weaviate

Each team runs their own Weaviate. Less coordination overhead, less cross-team learning.

### Option C: Hybrid

One shared Weaviate for ReviewPatterns (org-wide lessons), per-team for CodebaseKnowledge (too large to share).

---

## Aggregate Review Intelligence

Over time, you can extract org-wide patterns:

```bash
# Find the most common review pattern categories
python scripts/analyze_patterns.py --project myapp --by-category

# Find which files receive the most review comments
python scripts/analyze_patterns.py --project myapp --by-file

# Find patterns from a specific reviewer
python query_rag.py "" --collection reviews --project myapp \
  --filter "author = 'senior_dev_login'" --top 20
```

This tells you:
- What the team cares most about (top categories)
- Which parts of the codebase need attention (hotspot files)
- Which reviewers have the deepest expertise in which areas

---

## Onboarding New Developers

A new developer joins Team A. Before their first PR:

```bash
# Query the team's top review patterns
python query_rag.py "common mistakes" --collection reviews --project myapp --top 10
```

They get the top 10 historical patterns from 1000 PRs. No shadow review needed. No "I wish someone had told me that earlier."

---

## CI/CD Integration

Add a pre-PR check that queries ReviewPatterns for common issues:

```yaml
# .github/workflows/pre-pr-check.yml
- name: Check for known review patterns
  run: |
    AGENTS_WEAVIATE_URL=${{ secrets.WEAVIATE_URL }} \
    python $AGENTS_ROOT/scripts/query_rag.py \
      "$(git diff main...HEAD --stat | head -20)" \
      --collection reviews --project myapp --top 5
```

This surfaces potential review issues before the PR even opens.

---

## Metrics and Quality Gates

Track review pattern coverage:

| Metric | Target |
|--------|--------|
| PRs indexed | >80% of merged PRs |
| Average comments per PR | >2 (filter trivial PRs) |
| Coverage by category | All 6 categories represented |
| Freshness | Updated within 7 days |

```bash
AGENTS_WEAVIATE_URL=http://localhost:8090 \
python scripts/update_kb.py --stats --project myapp

# Example output:
# ReviewPatterns: 3,421 objects
#   security: 412 | performance: 891 | testing: 623
#   correctness: 744 | architecture: 389 | style: 362
# Last updated: 2 days ago
```
