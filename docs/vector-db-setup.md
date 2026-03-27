# Vector DB Setup: Weaviate

This guide covers installing, configuring, and tuning Weaviate for the SDLC agent framework.

---

## Why a Local Binary (No Docker)

Weaviate ships a single self-contained binary for macOS and Linux. No Docker required, no daemon to manage, no compose file.

Benefits:
- Boots in <2 seconds
- Data persists at a configurable path
- Zero Docker overhead
- Works on M1/M2/M3 Macs natively

---

## Installation

The `start_weaviate.py` script downloads the binary automatically on first run.

```bash
# Manual download (optional)
# macOS Apple Silicon
curl -L https://github.com/weaviate/weaviate/releases/download/v1.28.4/weaviate-v1.28.4-darwin-arm64.zip \
  -o /tmp/weaviate.zip && unzip /tmp/weaviate.zip -d ~/.weaviate-bin/

# macOS Intel
curl -L https://github.com/weaviate/weaviate/releases/download/v1.28.4/weaviate-v1.28.4-darwin-amd64.zip \
  -o /tmp/weaviate.zip && unzip /tmp/weaviate.zip -d ~/.weaviate-bin/

# Linux amd64
curl -L https://github.com/weaviate/weaviate/releases/download/v1.28.4/weaviate-v1.28.4-linux-amd64.zip \
  -o /tmp/weaviate.zip && unzip /tmp/weaviate.zip -d ~/.weaviate-bin/
```

---

## Ports

| Service | Port | Purpose |
|---------|------|---------|
| HTTP REST + GraphQL | 8090 | Client connections, query API |
| gRPC | 8091 | gRPC streaming (weaviate-client v4) |

The weaviate-client v4 (Python) uses gRPC for data operations and HTTP for admin operations. Both ports must be available.

---

## Data Persistence

Data is stored at: `~/.weaviate-<project>/data/`

Each project gets its own data directory. Multiple projects can run on separate ports.

```bash
# Project A — port 8090
PERSISTENCE_DATA_PATH=~/.weaviate-myapp/data

# Project B — port 8092
PERSISTENCE_DATA_PATH=~/.weaviate-otherapp/data
```

---

## Schema: Collections

### CodebaseKnowledge

Stores chunked source code files.

```python
Properties:
  chunk_id     TEXT    — unique: "file_path::chunk_N"
  file_path    TEXT    — relative path from repo root
  content      TEXT    — chunk text (2000 chars max)
  module       TEXT    — feature module (auth, billing, notifications...)
  doc_type     TEXT    — service | controller | component | test | schema | config
  category     TEXT    — business-logic | data-access | api-contract | ui-component | infrastructure
  language     TEXT    — typescript | python | vue | markdown | other
  content_hash TEXT    — MD5 of content (for incremental updates)
  last_updated DATE    — ISO8601 timestamp

Vector index: HNSW, cosine distance, 384 dims
BM25 index:   enabled on content, file_path
```

### CodingStandards

Stores coding rules, lint docs, architecture guidelines.

```python
Properties:
  rule_id      TEXT    — unique: "source_file::rule_N"
  source_file  TEXT    — which file defines this rule
  rule_type    TEXT    — architecture | testing | style | security | performance
  title        TEXT    — short rule name
  content      TEXT    — rule text
  content_hash TEXT    — for incremental updates

Vector index: HNSW, cosine distance, 384 dims
BM25 index:   enabled on content, title
```

### ReviewPatterns

Stores PR review comment history.

```python
Properties:
  pattern_id   TEXT    — unique: "PR_NNN::comment_N"
  pr_number    INT     — GitHub PR number
  pr_title     TEXT    — PR title
  file_path    TEXT    — file the comment was on
  comment      TEXT    — reviewer comment text
  category     TEXT    — security | performance | testing | style | architecture | correctness
  author       TEXT    — reviewer GitHub login
  created_at   DATE    — comment timestamp

Vector index: HNSW, cosine distance, 384 dims
BM25 index:   enabled on comment, file_path
```

### SolutionApproach

Stores per-ticket solution drafts.

```python
Properties:
  ticket_id    TEXT    — e.g. "PROJ-1234"
  title        TEXT    — ticket title
  approach     TEXT    — full solution markdown
  review_notes TEXT    — feedback from solution-review agent
  status       TEXT    — draft | approved | rejected
  created_at   DATE    — timestamp

Vector index: HNSW, cosine distance, 384 dims
```

---

## HNSW Index: How It Works

HNSW (Hierarchical Navigable Small World) is the default ANN (Approximate Nearest Neighbor) algorithm.

```
Layer 2 (sparse): long-range connections
    ◎ ——————————————— ◎
    │                  │
Layer 1 (medium):
    ◎ ——— ◎ ——— ◎ ——— ◎
    │     │     │     │
Layer 0 (dense): all vectors
    ◎ ◎ ◎ ◎ ◎ ◎ ◎ ◎ ◎ ◎
```

Search starts at a random node in the top layer, greedily navigates toward the query vector, then descends to layer 0 for fine search.

**Parameters (defaults are fine for most use cases):**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `ef` | 128 | Search width at query time. Higher = better recall, slower |
| `efConstruction` | 128 | Build-time search width. Higher = better graph, slower indexing |
| `maxConnections` | 64 | Edges per node. Higher = better recall, more RAM |

For a 50k-chunk codebase:
- Build time: ~30s
- Query time: <10ms
- RAM usage: ~400MB

---

## BM25 (Keyword Search)

BM25 is the industry-standard keyword ranking algorithm (used by Elasticsearch, Solr, Lucene).

Formula (simplified):
```
score(query, doc) = Σ IDF(term) × TF(term, doc) / (TF + k1 × (1 - b + b × |doc|/avgdl))
```

- **IDF:** rare terms score higher than common terms
- **TF:** term frequency, with diminishing returns (k1 parameter)
- **b:** length normalization (0.75 default — penalizes very long documents)

BM25 catches exact identifier matches that embedding models might miss:
- `processOrderPayment` — exact match → BM25 scores high
- "order payment processing" — semantic match → vector scores high

---

## Hybrid Search: Reciprocal Rank Fusion

RRF merges two ranked lists without needing comparable score scales:

```
RRF_score(doc) = 1/(k + rank_vector(doc)) + 1/(k + rank_bm25(doc))
```

Where k=60 (constant, reduces impact of very high ranks).

Example:
```
Doc A: vector rank 1, bm25 rank 3  → 1/61 + 1/63 = 0.0321
Doc B: vector rank 5, bm25 rank 1  → 1/65 + 1/61 = 0.0318
Doc C: vector rank 2, bm25 rank 2  → 1/62 + 1/62 = 0.0322  ← wins
```

Consistent top-rankers in both lists win. Outliers in one list are penalized.

---

## Tuning for Your Codebase

### Large repos (>100k files)

```python
# In update_kb.py, increase batch size and reduce chunk size
MAX_FILE_BYTES = 100_000   # allow larger files
BATCH_SIZE = 50            # larger batches
CHUNK_SIZE = 1500          # smaller chunks = more chunks but better precision
```

### Microservices repos

```python
# More granular module detection
# Add service-level patterns to MODULE_PATTERNS
MODULE_PATTERNS = {
    "payment-service": ["**/payment-service/**"],
    "auth-service": ["**/auth-service/**"],
    ...
}
```

### Legacy codebases (Java, PHP, Ruby)

```python
# Add extensions
INCLUDE_EXTENSIONS = {
    ".java", ".php", ".rb", ".go", ".cs", ".py",
    ".ts", ".js", ".vue", ".md"
}
```

---

## Backup and Migration

```bash
# Backup data directory
cp -r ~/.weaviate-myapp/data ~/.weaviate-myapp/data.backup

# Migrate to Weaviate Cloud
~/.sdlc-agents-venv/bin/python scripts/migrate_to_cloud.py \
  --source http://localhost:8090 \
  --target https://your-cluster.weaviate.network \
  --api-key YOUR_KEY \
  --project myapp
```

---

## Health Check

```bash
curl http://localhost:8090/v1/.well-known/ready
# 200 OK — Weaviate is running

curl http://localhost:8090/v1/meta
# Returns version, modules, hostname
```
