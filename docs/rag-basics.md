# RAG Basics

Retrieval-Augmented Generation (RAG) solves the fundamental problem of LLMs: they know the world up to their training cutoff but know nothing about *your* codebase.

---

## The Core Loop

```
User Query
    │
    ▼
[1] Embed query → vector
    │
    ▼
[2] Search vector DB → top-N relevant chunks
    │
    ▼
[3] (Optional) Re-rank top-N → top-K precise chunks
    │
    ▼
[4] Inject chunks into LLM context
    │
    ▼
[5] LLM generates grounded response
```

---

## Step 1: Chunking

Before indexing, source files are split into overlapping chunks.

**Why overlap?** A function that spans chunk boundaries would be cut in half without it. Overlap ensures context continuity.

```
File: orders.service.ts (8000 chars)

Chunk 1: chars 0–2000
Chunk 2: chars 1800–3800   ← 200 char overlap with chunk 1
Chunk 3: chars 3600–5600   ← 200 char overlap with chunk 2
...
```

**Our settings:**
- Max chunk size: 2000 characters
- Overlap: 200 characters
- Split boundary: newline (never mid-token)

---

## Step 2: Embedding

Each chunk is converted to a dense vector using a bi-encoder model.

**Model used:** `BAAI/bge-small-en-v1.5`
- 22 MB download (once, cached in `~/.cache`)
- 384 dimensions
- No API key — runs fully locally via ONNX
- Optimized for code + natural language mixed content

The vector captures *semantic meaning* — not just keywords. "authentication" and "login" will have nearby vectors even without shared words.

---

## Step 3: Storage

Weaviate stores each chunk as an object with:
- The dense vector (384 floats)
- Metadata: `file_path`, `module`, `doc_type`, `category`, `language`
- The raw text content
- A content hash (for incremental updates — only re-embed changed files)

**Index type:** HNSW (Hierarchical Navigable Small World)
- Approximate nearest neighbor search
- Sub-10ms queries even at 100k+ chunks
- Trade-off: ~10% recall loss vs. flat index, fully acceptable for RAG

---

## Step 4: Hybrid Retrieval

Pure vector search misses exact identifier matches. Pure keyword search misses semantic similarity.

We use **hybrid search** combining both:

```
Vector score (cosine similarity)  ×  α
      +
BM25 score (keyword relevance)    ×  (1 - α)
      ↓
Reciprocal Rank Fusion (RRF) merge
      ↓
Top-20 results
```

**α = 0.7** (tunable via `--alpha` flag) — biased toward semantic but keeps keyword precision.

Example:
```
Query: "OrdersService processPayment"

Vector search finds:     BM25 finds:
- orders.service.ts      - orders.service.ts   ← both agree = rank 1
- payments.service.ts    - payments.model.ts
- cart.service.ts        - order-processor.ts
```

---

## Step 5: Re-ranking

The bi-encoder scores each chunk independently — it can't model the interaction between query and chunk.

A **cross-encoder** reads query + chunk *together* and produces a more accurate relevance score.

```
Top-20 from hybrid search
         │
         ▼
Cross-encoder: score(query, chunk_i) for i in 1..20
         │
         ▼
Top-5 re-ranked results
         │
         ▼
Injected into LLM context
```

Cost: ~200ms extra latency. Worth it for complex queries.

---

## Step 6: Context Injection

The top-5 chunks are formatted and prepended to the LLM prompt:

```
## RAG Context [CodebaseKnowledge]: 'payment retry logic' (top 5)

### [1] src/payments/braintree.service.ts (distance: 0.041)
Module: payments | Type: service

<content of chunk>

---

### [2] src/payments/retry-handler.ts (distance: 0.063)
...
```

The LLM now has grounded, real context. It can reference actual file paths, actual function names, actual patterns — no hallucination.

---

## What Each Collection Stores

| Collection | Content | Query Use Case |
|------------|---------|----------------|
| `CodebaseKnowledge` | Source file chunks | "how does X work", "find the file that does Y" |
| `CodingStandards` | Lint rules, architecture docs | "what's the pattern for Z", "is this approach correct" |
| `ReviewPatterns` | Past PR review comments | "what does this team care about in reviews" |
| `SolutionApproach` | Per-ticket solution drafts | retrieve/update solution for a ticket |

---

## When RAG Helps Most

✅ "How does the cart pricing calculation work?" — finds the relevant service files
✅ "What's the pattern for creating a new NestJS module?" — finds standards + examples
✅ "What did reviewers say about error handling in PRs?" — finds review patterns
✅ "Write a new payment processor following our patterns" — grounds generation in real code

## When RAG Helps Less

❌ Very short queries with no semantic signal ("fix bug")
❌ Queries about code you haven't indexed yet
❌ Questions requiring full file context (solution: increase chunk size or use file-level retrieval)
