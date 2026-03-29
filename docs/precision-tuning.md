# RAG Precision Tuning Guide

Seven concrete improvements that meaningfully lift retrieval quality. Each one
is implemented in `scripts/query_rag.py` and `scripts/update_kb.py` and can be
adopted independently.

---

## 1. Code-Aware Embedding Model

**Change:** `BAAI/bge-small-en-v1.5` (384d) → `jinaai/jina-embeddings-v2-base-code` (768d)

**Why it matters:**

General-purpose English embedding models were trained on web text. They treat
`UserService`, `@Injectable()`, and `findByIdOrThrow` as opaque tokens. The
jina-code model was trained on GitHub code across 30+ languages — it understands
class hierarchies, decorator patterns, type annotations, and framework idioms.

Practical impact:
- Query `"authentication guard"` retrieves the `@UseGuards(AuthTokenGuard)` decorator site, not just files with the word "auth"
- Query `"database schema user"` retrieves the Mongoose/Prisma/SQLAlchemy model, not the word "user" in a README

**How to switch:**

```python
# scripts/update_kb.py and scripts/query_rag.py
EMBED_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"
EMBED_DIMS = 768  # update_kb.py only
```

**⚠️ Breaking change:** Vector dimensions changed from 384 → 768. Existing
collections must be migrated before re-indexing:

```bash
python scripts/update_kb.py --migrate --project myapp
python scripts/update_kb.py --repo-root . --project myapp --full
python scripts/update_kb.py --standards --repo-root . --project myapp
```

---

## 2. Stronger Cross-Encoder Reranker

**Change:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (6 layers) → `cross-encoder/ms-marco-MiniLM-L-12-v2` (12 layers)

**Why it matters:**

The reranker reads the query and each candidate chunk *together* and scores
their relevance as a pair. More layers = more attention heads = better at
distinguishing "this chunk answers the query" from "this chunk merely shares
vocabulary with the query".

The L-12 model is ~2× slower per prediction but still fast enough at the
scale of 20 candidates (~300–400ms on CPU). For code retrieval where precision
matters more than latency, this is the right tradeoff.

```python
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-12-v2"
```

Usage:
```bash
python scripts/query_rag.py "payment retry logic" --project myapp --rerank
```

---

## 3. Multi-Query Retrieval

**Flag:** `--multi-query`

**Why it matters:**

A query like `"how does auth token work"` and `"token validation logic"` describe
the same concept but embed differently. If your exact phrasing happens to miss
the chunk that would answer it, you get no result — even though the chunk exists.

Multi-query generates 2–3 variants of your query:
1. Original query
2. Keyword-only variant (stopwords stripped)
3. Context-prefixed variant (`typescript <query>`, `code review <query>`, etc.)

Each variant runs as a separate search. Results are merged and deduplicated by
chunk identity, keeping the highest score per chunk. The merged pool is then
reranked to top-K.

Net effect: more coverage without increasing the number of results shown.

```bash
python scripts/query_rag.py "email notification retry" \
  --project myapp --multi-query --rerank
```

**When to use:** Any time you're not confident your exact phrasing matches
how the code was written. Adds ~2× retrieval time, same reranking pass.

---

## 4. Module Filter

**Flag:** `--module <name>`

**Why it matters:**

Without filtering, a query for `"send email"` retrieves chunks from the
notifications module, the user registration flow, the order confirmation
handler, and test fixtures — ranked by vector similarity. With `--module
notifications`, only chunks classified in that module are considered.

This improves precision when you know which feature area you're working in.

```bash
# Only return results from the notifications module
python scripts/query_rag.py "send email" \
  --collection codebase --module notifications --project myapp

# Only return results from the auth module
python scripts/query_rag.py "token expiry" \
  --collection codebase --module auth --project myapp
```

Module names come from `MODULE_PATTERNS` in `update_kb.py`. Every chunk is
classified at index time — no re-indexing needed to use the filter.

---

## 5. Min-Score Threshold

**Flag:** `--min-score <float>`

**Why it matters:**

By default, `query_rag.py` always returns `--top N` results. If the query has
no good match in the index (e.g. querying for a feature that hasn't been built
yet), you get low-relevance noise injected into agent context — which can
mislead the agent.

`--min-score` surfaces a warning and filters out results below the threshold:

```bash
python scripts/query_rag.py "webhook signature verification" \
  --project myapp --min-score 0.5 --rerank
# ⚠️  2 result(s) below min-score 0.50 filtered out
```

**Recommended values:**
- `0.4` — conservative, catches only very low confidence results
- `0.5` — balanced for most use cases
- `0.6` — strict, use when false positives are costly (e.g. security queries)

Agents should treat a "no results above min-score" response as a signal that
this area of the codebase may not be indexed or the feature doesn't exist yet.

---

## 6. Class Context Injection

**Where:** `scripts/update_kb.py` — `update_codebase()`

**Why it matters:**

When a large service file is chunked, method-level chunks lose their class
context. A chunk containing `findById(id: string): Promise<User>` has no
indication that it belongs to `UserService`. When you query `"user service find
by id"`, the chunk doesn't embed with that context and may not be retrieved.

The fix: for TypeScript and JavaScript files, detect the enclosing class at
the chunk's byte offset and prepend `// Class: ClassName` to the embedding
text:

```python
embed_text = f"[module:{module}] [type:{doc_type}]\nFile: {rel_path}\n// Class: UserService\n\n{chunk}"
```

This is a zero-cost improvement applied at index time. The stored chunk content
is unchanged — only the embedding input includes the class prefix.

**Implementation:** `extract_class_context()` + `chunk_smart_with_offsets()`
work together: offsets tell us where each chunk starts in the original file,
so we can scan backward for the nearest class declaration.

---

## 7. Weaviate Readiness Check

**Where:** Both `query_rag.py` and `update_kb.py`

**Why it matters:**

Without a pre-flight check, a connection attempt to a stopped Weaviate instance
produces a cryptic gRPC or socket error after a 30-second timeout. Agents
get confused by the error and may retry or hallucinate.

With the check, failure is immediate and clear:

```
⚠️  Weaviate not reachable at http://localhost:8090
Start it: python scripts/start_weaviate.py
```

```python
def check_weaviate_ready(url: str = WEAVIATE_URL) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/v1/.well-known/ready", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False
```

Uses only stdlib (`urllib.request`) — no extra dependency.

---

## 8. Per-Collection Hybrid Alpha

**Where:** `scripts/query_rag.py` — `COLLECTION_ALPHA`

**Why it matters:**

Hybrid search blends vector similarity (semantic) and BM25 (keyword) via an
`alpha` parameter (1.0 = pure vector, 0.0 = pure BM25). The optimal balance
differs by collection:

| Collection | Alpha | Reason |
|---|---|---|
| `codebase` | 0.6 | Function/type names are exact keywords; balanced |
| `standards` | 0.5 | Rule names and lint terms are keyword-heavy |
| `reviews` | 0.8 | PR comment intent is semantic; phrasing varies |
| `decisions` | 0.7 | Architectural reasoning is semantic |

Previously a single `alpha=0.75` was used everywhere. Tuning per-collection
meaningfully improves precision for standards queries (more BM25) and review
pattern queries (more vector).

---

## 9. Larger File Size Limit

**Change:** `MAX_FILE_BYTES = 50_000` → `MAX_FILE_BYTES = 150_000`

**Why it matters:**

God-class service files common in monoliths (order management, user profiles,
checkout flows) routinely exceed 50KB. With the old limit, these files were
silently skipped — the most important service files in the codebase had zero
representation in the KB.

Check what's being skipped in your repo:

```bash
find . -type f \( -name "*.ts" -o -name "*.py" -o -name "*.rb" \) \
  | grep -v node_modules | xargs wc -c 2>/dev/null \
  | awk '$1 > 50000 {print $1, $2}' | sort -rn
```

150KB covers virtually all real service files. Files larger than that are
usually generated code (GraphQL clients, OpenAPI clients, migration files)
which should be in `SKIP_DIRS` or `SKIP_PATTERNS` instead.

---

## Putting It All Together

A high-precision agent query combining multiple improvements:

```bash
# Semantic + keyword, scoped to billing module, filtered by confidence,
# multi-query for phrasing resilience, L-12 reranked
python scripts/query_rag.py "subscription renewal payment failure" \
  --project myapp \
  --collection codebase \
  --module payments \
  --multi-query \
  --rerank \
  --rerank-candidates 30 \
  --min-score 0.45
```

In agent commands, the pattern is:

```bash
# 1. Broad semantic search with multi-query
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<feature concept>" \
  --project $AGENTS_PROJECT --multi-query --rerank --top 8

# 2. Scoped to module when editing a known area
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<specific method behavior>" \
  --project $AGENTS_PROJECT --collection codebase --module <module> --rerank --top 5

# 3. Standards check
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<rule or pattern>" \
  --project $AGENTS_PROJECT --collection standards --top 5

# 4. Past review patterns
$AGENTS_VENV $AGENTS_ROOT/scripts/query_rag.py "<concern>" \
  --project $AGENTS_PROJECT --collection reviews --rerank --top 10
```

---

## Migration Checklist

When upgrading an existing installation from the old `BAAI/bge-small-en-v1.5`
setup to the new `jinaai/jina-embeddings-v2-base-code` setup:

```bash
# 1. Install updated dependencies
pip install -r scripts/requirements.txt

# 2. Drop and recreate all collections (dimension change: 384 → 768)
python scripts/update_kb.py --migrate --project myapp

# 3. Re-index codebase
python scripts/update_kb.py --repo-root /path/to/project --project myapp --full

# 4. Re-index standards
python scripts/update_kb.py --standards --repo-root /path/to/project --project myapp

# 5. Re-index PR review patterns (uses same embedding model)
cd /path/to/project
python /path/to/sdlc-agent-framework/scripts/update_pr_kb.py \
  --project myapp --limit 200 --include-open --extract-solutions --mark-resolved

# 6. Verify
python scripts/update_kb.py --stats --project myapp
```

Total time: 10–30 minutes depending on codebase size and number of PRs.
Models download once on first run (~130MB for jina-code, ~65MB for L-12 reranker).
