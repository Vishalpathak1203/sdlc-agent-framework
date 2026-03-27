# Embeddings Strategy: Module Classification

The quality of RAG depends not just on the embedding model but on how you **classify and store** metadata alongside each vector. Good classification means agents can filter results *before* semantic scoring — narrowing 50k chunks to a relevant 500 before even running the embedding search.

---

## The Classification Dimensions

Every chunk gets four classification labels:

### 1. `module` — Feature Area

What business capability does this file belong to?

```python
MODULE_PATTERNS = {
    # NestJS / Express backend
    "auth":          ["**/auth/**", "**/authentication/**", "**/user-auth/**"],
    "billing":       ["**/billing*/**", "**/invoice*/**", "**/subscription*/**"],
    "orders":        ["**/order*/**", "**/orders/**"],
    "payments":      ["**/payment*/**", "**/billing/**"],
    "listings":      ["**/listing*/**", "**/product*/**", "**/catalog/**"],
    "notifications": ["**/notification*/**", "**/email/**", "**/sms/**"],
    "users":         ["**/user*/**", "**/profile*/**", "**/account/**"],
    "search":        ["**/search/**", "**/elastic*/**", "**/solr/**"],
    "scheduler":     ["**/scheduler/**", "**/cron/**", "**/jobs/**", "**/queue*/**"],
    "webhooks":      ["**/webhook*/**", "**/hooks/**"],
    "admin":         ["**/admin*/**", "**/dashboard/**"],
    # Nuxt / Vue frontend
    "ui-common":     ["**/components/common/**", "**/components/shared/**"],
    "ui-pages":      ["**/pages/**"],
    "ui-stores":     ["**/stores/**", "**/store/**"],
    "ui-composables":["**/composables/**"],
    # Infrastructure
    "config":        ["**/config/**", "**/env/**", "**/settings/**"],
    "migrations":    ["**/migrations/**", "**/seeds/**"],
    "scripts":       ["**/scripts/**", "**/tools/**"],
}
```

If no pattern matches, module = `"general"`.

### 2. `doc_type` — Code Layer

What type of code is this?

| `doc_type` | File Patterns | Example |
|------------|--------------|---------|
| `service` | `*.service.ts`, `*_service.py`, `*Service.java` | Business logic |
| `controller` | `*.controller.ts`, `*_controller.rb`, `*Controller.java` | HTTP handlers |
| `component` | `*.vue`, `*.tsx` components, `*Component.ts` | UI components |
| `test` | `*.spec.ts`, `*.test.ts`, `*_test.py`, `*Test.java` | Unit/integration tests |
| `schema` | `*.schema.ts`, `*.model.ts`, `*Entity.java`, `*.prisma` | Data models |
| `config` | `*.config.ts`, `*.env*`, `nuxt.config.ts` | Configuration |
| `spec` | `*.dto.ts`, `*.interface.ts`, `*.type.ts` | Type definitions |
| `middleware` | `*.middleware.ts`, `*.guard.ts`, `*.interceptor.ts` | Cross-cutting concerns |
| `util` | `*.util.ts`, `*.helper.ts`, `*utils*` | Utilities |
| `docs` | `*.md`, `*.mdx` | Documentation |

### 3. `category` — Semantic Purpose

A higher-level semantic grouping that cuts across modules:

| `category` | Description | Example files |
|------------|-------------|--------------|
| `business-logic` | Core domain rules | `<users/account-manager>`, `<billing/invoice-manager>` |
| `data-access` | DB queries, ORM, repositories | `<module/data-repository>`, `<module/data-schema>` |
| `api-contract` | Request/response shapes | `<module/request-dto>`, `<module/response-type>`, OpenAPI specs |
| `ui-component` | Visual UI components | `<feature/display-component>`, `<feature/form-component>` |
| `infrastructure` | Config, queues, caching | `<app/bootstrap>`, `<app/cache-config>` |
| `testing` | Test helpers, fixtures, factories | `<module/feature-test>`, `<shared/test-utils>` |
| `integration` | External service clients | Payment gateway, analytics, CRM clients |

### 4. `language`

```python
LANGUAGE_MAP = {
    ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript",
    ".vue": "vue",
    ".py": "python",
    ".rb": "ruby",
    ".java": "java",
    ".go": "go",
    ".cs": "csharp",
    ".php": "php",
    ".md": "markdown",
}
```

---

## Why This Matters for RAG Quality

### Without classification

```
Query: "how does user subscription billing work"

Results (top 5):
  1. <billing/invoice-manager>     ← relevant ✅
  2. README.md                     ← noise ❌
  3. <billing/invoice-manager-test>← partially relevant
  4. package.json                  ← noise ❌
  5. <users/account-manager>       ← partially relevant
```

### With classification + filtered query

```
Query: "how does user subscription billing work"
Filter: module IN ["billing", "subscriptions"], doc_type IN ["service"]

Results (top 5):
  1. <billing/invoice-manager>        ← relevant ✅
  2. <subscriptions/plan-manager>     ← relevant ✅
  3. <billing/invoice-processor>      ← relevant ✅
  4. <payments/gateway-connector>     ← relevant ✅
  5. <billing/refund-processor>       ← relevant ✅
```

Filters reduce the search space before vector scoring. Results are all relevant.

---

## Module-Wise Embedding Strategy

For large codebases, embed **module by module** with module-aware prefixing:

```python
def build_embedding_text(file_path: str, content: str, module: str, doc_type: str) -> str:
    """Build text to embed — adds classification context to improve retrieval."""
    prefix = f"[module:{module}] [type:{doc_type}]\n"
    return prefix + content
```

The prefix biases the embedding toward the module's semantic space. "auth service" and "payment service" both contain "service" — but their embeddings now live in different regions of the vector space.

---

## Incremental Updates

Files are only re-embedded when their content changes:

```python
content_hash = hashlib.md5(content.encode()).hexdigest()

# Compare with stored hash
existing = collection.query.fetch_objects(
    filters=Filter.by_property("chunk_id").equal(chunk_id),
    limit=1
)

if existing.objects and existing.objects[0].properties["content_hash"] == content_hash:
    skip()   # unchanged
else:
    upsert() # re-embed
```

After `git rebase` or large merges, run `--full` to force re-embed everything.

---

## Embedding Text Construction for Different File Types

### Source code files

```python
# Include file path as context — "<auth/login-handler>" carries semantic meaning
embedding_text = f"File: {file_path}\n\n{chunk_content}"
```

### Documentation (Markdown)

```python
# Include section header if available
embedding_text = f"Section: {section_title}\n\n{chunk_content}"
```

### PR review comments

```python
# Include file path + comment — reviewer context
embedding_text = f"Reviewed: {file_path}\nComment: {comment_text}"
```

### Coding standards / rules

```python
# Include rule type and title for disambiguation
embedding_text = f"Rule [{rule_type}]: {title}\n\n{rule_content}"
```

---

## Choosing the Right Embedding Model

| Model | Dims | Size | Quality | Use When |
|-------|------|------|---------|----------|
| `BAAI/bge-small-en-v1.5` | 384 | 22MB | Good | Default — best balance |
| `BAAI/bge-base-en-v1.5` | 768 | 109MB | Better | Larger codebases, more RAM |
| `BAAI/bge-large-en-v1.5` | 1024 | 338MB | Best | When quality > speed |
| `nomic-ai/nomic-embed-text-v1.5` | 768 | 274MB | Great for long docs | Documentation-heavy repos |

All models run locally via `fastembed` (ONNX runtime). No API key. First run downloads the model.

Change the model in `update_kb.py`:
```python
EMBED_MODEL_NAME = "BAAI/bge-base-en-v1.5"
EMBED_DIMS = 768
```

**Important:** If you change the model, you must re-initialize the schema and re-embed everything (`--init-schema --full`).
