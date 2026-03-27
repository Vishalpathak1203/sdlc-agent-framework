# Re-ranking

Re-ranking is the step between "candidate retrieval" and "context injection" that dramatically improves precision for the cost of ~200ms latency.

---

## The Two-Stage Retrieval Problem

### Stage 1: Bi-encoder (fast but imprecise)

The embedding model encodes the query *independently* from each document. At query time:

```
embed(query) → vector_q
embed(doc_i) → vector_di

score = cosine(vector_q, vector_di)
```

This is fast (pre-computed doc vectors, single dot product) but misses nuanced query-document interactions. The model doesn't "see" the document when encoding the query.

### Stage 2: Cross-encoder (slow but precise)

A cross-encoder reads the query AND document together in a single forward pass:

```
cross_encoder(query + [SEP] + doc_i) → relevance_score
```

This captures:
- Exact term overlap
- Query-specific context ("retry" in the query matters when the doc has "retry logic")
- Negation and qualification
- Multi-hop reasoning across the chunk

The downside: you can't pre-compute scores. Every (query, doc) pair requires a full forward pass. That's why we run it only on the top-20 from stage 1, not the full corpus.

---

## The Two-Stage Pipeline

```
Query
  │
  ▼
Hybrid search (vector + BM25)
  │   Fast: <10ms
  │   Retrieve: top-20 candidates
  ▼
Cross-encoder re-ranking
  │   Slower: ~200ms for 20 docs
  │   Re-rank → top-5
  ▼
Inject into LLM context
```

---

## Model Used

**Default:** `cross-encoder/ms-marco-MiniLM-L-6-v2`
- 23MB
- Trained on MS-MARCO passage ranking dataset
- Excellent at code + natural language mixed content
- Runs locally via `sentence-transformers`

```python
from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
scores = model.predict([(query, doc1), (query, doc2), ...])
```

---

## When to Use `--rerank`

| Scenario | Use rerank? | Why |
|----------|------------|-----|
| Simple keyword search | No | BM25 alone is sufficient |
| Semantic code search | Yes | Bi-encoder misses code-specific patterns |
| Solution approach (complex) | Yes | Precision matters for code generation |
| Quick `--top 3` sanity check | No | Overhead not worth it |
| PR review patterns | Yes | Category specificity matters |
| Incremental KB update check | No | Speed matters |

Add `--rerank` flag:
```bash
python scripts/query_rag.py "payment retry logic" --project myapp --rerank --top 5
```

---

## Why Re-ranking Improves Code Retrieval

Embedding models are trained predominantly on text. Code has patterns that confuse them:

| Challenge | Bi-encoder behavior | Cross-encoder behavior |
|-----------|--------------------|-----------------------|
| Identifier names | "processOrder" ≠ "orderProcess" | Recognizes same concept |
| Method signatures | Ignores parameter types | Considers full signature |
| Comments vs. code | May rank comment-heavy files higher | Balances both |
| Negation | "don't use deprecated API" → ranks deprecated API files | Handles negation |

---

## Performance Tradeoffs

| Config | Latency | Recall@5 |
|--------|---------|----------|
| Vector only, top-5 | 8ms | 0.71 |
| Hybrid, top-5 | 12ms | 0.79 |
| Hybrid top-20 + rerank top-5 | 210ms | 0.91 |
| Hybrid top-50 + rerank top-5 | 380ms | 0.93 |

For interactive agent use, 210ms is imperceptible. For batch operations (KB updates), skip re-ranking.

---

## Tuning Re-ranking

### Candidate pool size

```bash
# Fetch more candidates before re-ranking → better recall, slower
python query_rag.py "auth middleware" --top 5 --rerank --rerank-candidates 30
```

### Score threshold

Only return chunks above a minimum relevance score:

```bash
python query_rag.py "auth middleware" --top 5 --rerank --min-score 0.5
```

Useful when you'd rather get 2 highly relevant chunks than 5 mixed-quality ones.

---

## Alternative Re-ranking Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | 23MB | Fast | Good (default) |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | 34MB | Medium | Better |
| `BAAI/bge-reranker-base` | 278MB | Slow | Best for code |
| `BAAI/bge-reranker-large` | 561MB | Slowest | Best overall |

Change in `query_rag.py`:
```python
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"
```
