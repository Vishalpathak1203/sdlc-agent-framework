#!/usr/bin/env python3
"""
update_kb.py — Index codebase and coding standards into Weaviate.

Embeddings are generated locally using fastembed. No API key needed.
Supports any project — configure MODULE_PATTERNS and INCLUDE_EXTENSIONS.

Usage:
  python update_kb.py --repo-root . --project myapp
  python update_kb.py --repo-root . --project myapp --full
  python update_kb.py --standards --repo-root . --project myapp
  python update_kb.py --init-schema --project myapp
  python update_kb.py --migrate --project myapp    # drop + recreate (use after model change)
  python update_kb.py --stats --project myapp
  python update_kb.py --prune --repo-root . --project myapp
  python update_kb.py --adrs --repo-root . --project myapp
"""

import argparse
import fnmatch
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import weaviate
import weaviate.classes as wvc
from fastembed import TextEmbedding

WEAVIATE_URL = os.getenv("AGENTS_WEAVIATE_URL", "http://localhost:8090")
WEAVIATE_GRPC_PORT = int(os.getenv("AGENTS_WEAVIATE_GRPC_PORT", "0"))

# Code-aware embedding model (768d). Upgrade from BAAI/bge-small-en-v1.5 (384d).
# If you change this, run --migrate then --full to rebuild all vectors.
EMBED_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"
EMBED_DIMS = 768

BATCH_SIZE = 25
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

# Raise this if large service files are being skipped (check with --stats).
# Common culprits: God-class services, generated clients, large fixtures.
MAX_FILE_BYTES = 150_000

_embedder: TextEmbedding | None = None


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        print(f"Loading embedding model '{EMBED_MODEL_NAME}' (downloads once on first run)...")
        _embedder = TextEmbedding(EMBED_MODEL_NAME)
    return _embedder


def embed(text: str) -> list[float]:
    return next(get_embedder().embed([text])).tolist()


INCLUDE_EXTENSIONS = {
    ".ts", ".tsx", ".vue", ".js", ".jsx",
    ".py", ".rb", ".java", ".go", ".cs", ".php",
    ".md", ".mdx",
}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__",
    ".next", ".nuxt", "coverage", ".turbo", "out", "vendor",
    ".cache", "tmp", "temp", ".output", "public", "generated",
    "migrations", ".venv", "venv", "env",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
}

SKIP_PATTERNS = {"*.d.ts", "*.min.js", "*.map", "*.snap", "*.generated.*"}


# ── Module classification ──────────────────────────────────────────────────
#
# Patterns are checked in order. First match wins.
# Customize this list for your project's directory structure.
# The module name is stored as metadata on each chunk — agents can filter
# queries to a specific module using --module <name>.
#
MODULE_PATTERNS: list[tuple[str, list[str]]] = [
    # Auth / Identity
    ("auth",          ["**/auth/**", "**/authentication/**", "**/user-auth/**", "**/login/**",
                        "**/identity/**", "**/oauth/**", "**/jwt/**"]),
    # Payments / Billing
    ("payments",      ["**/payment*/**", "**/billing/**", "**/stripe/**", "**/braintree/**",
                        "**/invoice/**", "**/subscription*/**", "**/plan*/**"]),
    # Orders
    ("orders",        ["**/order*/**", "**/checkout*/**", "**/purchase*/**"]),
    # Cart
    ("cart",          ["**/cart*/**", "**/basket*/**", "**/shopping*/**"]),
    # Notifications / Messaging
    ("notifications", ["**/notification*/**", "**/email/**", "**/sms/**", "**/push/**",
                        "**/mailer/**", "**/messaging/**"]),
    # Users / Profiles
    ("users",         ["**/user*/**", "**/profile*/**", "**/account*/**", "**/member*/**"]),
    # Products / Catalog / Listings
    ("products",      ["**/product*/**", "**/catalog*/**", "**/listing*/**", "**/inventory*/**"]),
    # Search
    ("search",        ["**/search/**", "**/elastic*/**", "**/solr/**", "**/algolia/**"]),
    # Scheduler / Jobs / Queues
    ("scheduler",     ["**/scheduler/**", "**/cron/**", "**/jobs/**", "**/queue*/**",
                        "**/worker*/**", "**/processor*/**", "**/task*/**"]),
    # Webhooks / Events
    ("webhooks",      ["**/webhook*/**", "**/hooks/**", "**/event*/**"]),
    # Reports / Analytics
    ("reports",       ["**/report*/**", "**/analytics/**", "**/metrics/**", "**/stats/**"]),
    # Fraud / Security / Risk
    ("fraud",         ["**/fraud/**", "**/risk/**", "**/abuse/**", "**/security/**"]),
    # Admin / Dashboard
    ("admin",         ["**/admin*/**", "**/dashboard/**", "**/backoffice/**", "**/cms/**"]),
    # Messages / Chat / Inbox
    ("messages",      ["**/message*/**", "**/chat/**", "**/inbox/**", "**/thread*/**"]),
    # Pricing / Discount
    ("pricing",       ["**/pricing/**", "**/discount*/**", "**/coupon*/**", "**/promo*/**"]),
    # Saved / Bookmarks / Favorites
    ("saved",         ["**/saved*/**", "**/bookmark*/**", "**/wishlist*/**", "**/favorite*/**"]),
    # Refund / Returns
    ("refund",        ["**/refund*/**", "**/return*/**", "**/chargeback*/**"]),
    # Device / Session
    ("device",        ["**/device*/**", "**/session*/**"]),
    # Common / Shared infrastructure
    ("common",        ["**/common/**", "**/shared/**", "**/core/**"]),
    # Cache
    ("cache",         ["**/cache/**", "**/redis/**", "**/memcache*/**"]),
    # Feature flags
    ("feature-flag",  ["**/feature-flag*/**", "**/feature-flags/**", "**/flags/**",
                        "**/launchdarkly/**", "**/unleash/**"]),
    # External integrations
    ("integration",   ["**/integration*/**", "**/external*/**", "**/third-party/**",
                        "**/adapter*/**", "**/connector*/**"]),
    # UI components
    ("ui-components", ["**/components/**"]),
    # UI pages / routes
    ("ui-pages",      ["**/pages/**", "**/views/**", "**/routes/**"]),
    # UI stores / state
    ("ui-stores",     ["**/stores/**", "**/store/**", "**/state/**", "**/context/**"]),
    # UI composables / hooks
    ("ui-composables",["**/composables/**", "**/hooks/**"]),
    # Infrastructure / Config
    ("infra",         ["**/config/**", "**/infra/**", "**/setup/**", "**/middleware/**"]),
]


def classify_module(file_path: str) -> str:
    normalized = file_path.replace("\\", "/")
    for module_name, patterns in MODULE_PATTERNS:
        for pat in patterns:
            if fnmatch.fnmatch(normalized, pat):
                return module_name
    return "general"


# ── Doc type classification ────────────────────────────────────────────────

DOC_TYPE_PATTERNS: list[tuple[str, list[str]]] = [
    ("test",       ["*.spec.*", "*.test.*", "*_test.*", "*Test.*", "*Tests.*"]),
    ("service",    ["*.service.*", "*Service.*", "*_service.*"]),
    ("controller", ["*.controller.*", "*Controller.*", "*_controller.*"]),
    ("component",  ["*.vue", "*.tsx", "*Component.*"]),
    ("schema",     ["*.schema.*", "*Schema.*", "*.model.*", "*Model.*", "*Entity.*", "*.prisma"]),
    ("middleware", ["*.middleware.*", "*Middleware.*", "*.guard.*", "*.interceptor.*", "*.filter.*"]),
    ("constants",  ["*.constants.*", "*Constants.*"]),
    ("dto",        ["*.dto.*", "*Dto.*"]),
    ("types",      ["*.interface.*", "*.type.*", "*.types.*"]),
    ("util",       ["*.util.*", "*Utils.*", "*Helper.*", "*.helper.*"]),
    ("config",     ["*.config.*", "*Config.*", ".env*", "nuxt.config.*", "vite.config.*",
                    "next.config.*", "django_settings*"]),
    ("docs",       ["*.md", "*.mdx"]),
]


def classify_doc_type(file_path: str) -> str:
    name = Path(file_path).name
    for doc_type, patterns in DOC_TYPE_PATTERNS:
        for pat in patterns:
            if fnmatch.fnmatch(name, pat):
                return doc_type
    return "source"


def classify_category(module: str, doc_type: str) -> str:
    if doc_type == "test":
        return "testing"
    if doc_type == "schema":
        return "data-access"
    if doc_type in ("dto", "types"):
        return "api-contract"
    if doc_type == "constants":
        return "constants"
    if doc_type == "component":
        return "ui-component"
    if doc_type in ("config", "middleware"):
        return "infrastructure"
    if module in ("integration", "infra"):
        return "infrastructure"
    if doc_type == "service":
        return "business-logic"
    if doc_type == "controller":
        return "api-contract"
    return "business-logic"


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
    ".md": "markdown", ".mdx": "markdown",
}


def classify_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "other")


# ── Chunking ───────────────────────────────────────────────────────────────

import re as _re

# Class declaration pattern — used to inject enclosing class context into
# chunk embeddings so method-level chunks stay anchored to their class.
# Without this, a method chunk for `UserService.findById()` embeds with no
# class context, making it hard to retrieve when querying "user service".
_CLASS_DECL = _re.compile(
    r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)',
    _re.MULTILINE,
)


def extract_class_context(file_content: str, chunk_start: int) -> str | None:
    """Return the enclosing class name for a chunk at the given byte offset."""
    matches = list(_CLASS_DECL.finditer(file_content, 0, chunk_start))
    return matches[-1].group(1) if matches else None


# Top-level declaration boundaries for smart chunking
_TS_BOUNDARY = _re.compile(
    r'^(?:export\s+(?:default\s+)?(?:class|function|const|async\s+function|abstract\s+class)'
    r'|(?:class|function)\s+\w'
    r'|@\w+)',  # decorators (@Injectable, @Component, etc.)
    _re.MULTILINE,
)

_MD_HEADER = _re.compile(r'^#{1,3} .+', _re.MULTILINE)


def _find_boundaries(text: str, language: str) -> list[int]:
    if language in ("typescript", "javascript", "vue"):
        return [m.start() for m in _TS_BOUNDARY.finditer(text)]
    if language in ("markdown",):
        return [m.start() for m in _MD_HEADER.finditer(text)]
    return []


def chunk_smart(text: str, language: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chunk at logical boundaries (function/class/header); fall back to character split."""
    if len(text) <= max_size:
        return [text]

    boundaries = _find_boundaries(text, language)
    if not boundaries or boundaries[0] != 0:
        boundaries = [0] + boundaries

    chunks: list[str] = []
    current_start = 0

    for i, boundary in enumerate(boundaries):
        if boundary <= current_start:
            continue
        segment = text[current_start:boundary]
        if len(segment) >= max_size:
            chunks.extend(chunk_text(segment, max_size, overlap))
            current_start = boundary
        elif i == len(boundaries) - 1:
            tail = text[current_start:]
            if len(tail) > max_size:
                chunks.extend(chunk_text(tail, max_size, overlap))
            else:
                chunks.append(tail)
            current_start = len(text)

    if current_start < len(text):
        tail = text[current_start:]
        if len(tail) > max_size:
            chunks.extend(chunk_text(tail, max_size, overlap))
        elif tail.strip():
            chunks.append(tail)

    return chunks or [text]


def chunk_text(text: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= max_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_size
        if end < len(text):
            newline = text.rfind("\n", start, end)
            if newline > start:
                end = newline + 1
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def chunk_smart_with_offsets(
    text: str, language: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[tuple[str, int]]:
    """Like chunk_smart but returns (chunk_text, start_offset) tuples.

    The start offset is used to look up the enclosing class name so that
    method-level chunks embed with class context injected.
    """
    chunks = chunk_smart(text, language, max_size, overlap)
    result: list[tuple[str, int]] = []
    pos = 0
    for chunk in chunks:
        idx = text.find(chunk, pos)
        start = idx if idx != -1 else pos
        result.append((chunk, start))
        pos = start + max(1, len(chunk) - overlap)
    return result


# ── Weaviate ───────────────────────────────────────────────────────────────

def get_client(url: str = WEAVIATE_URL) -> weaviate.WeaviateClient:
    port = int(url.rstrip("/").split(":")[-1])
    grpc_port = WEAVIATE_GRPC_PORT if WEAVIATE_GRPC_PORT else port + 1
    return weaviate.connect_to_local(host="localhost", port=port, grpc_port=grpc_port)


def collection_name(base: str, project: str) -> str:
    if not project or project == "default":
        return base
    safe = "".join(c if c.isalnum() else "_" for c in project)
    return f"{base}_{safe}"


def init_schema(client: weaviate.WeaviateClient, project: str) -> None:
    existing = {c.name for c in client.collections.list_all().values()}

    collections = [
        (collection_name("CodebaseKnowledge", project), [
            wvc.config.Property(name="chunk_id",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="file_path",    data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="content",      data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="module",       data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="doc_type",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="category",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="language",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content_hash", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="last_updated", data_type=wvc.config.DataType.DATE),
        ]),
        (collection_name("CodingStandards", project), [
            wvc.config.Property(name="rule_id",      data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="source_file",  data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="rule_type",    data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title",        data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="content",      data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="content_hash", data_type=wvc.config.DataType.TEXT),
        ]),
        (collection_name("ReviewPatterns", project), [
            wvc.config.Property(name="pattern_id",   data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="pr_number",    data_type=wvc.config.DataType.INT),
            wvc.config.Property(name="pr_title",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="file_path",    data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="comment",      data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="category",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="module",       data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="doc_type",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="decision",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="reasoning",    data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="was_resolved", data_type=wvc.config.DataType.BOOL),
            wvc.config.Property(name="author",       data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="pr_author",    data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at",   data_type=wvc.config.DataType.DATE),
        ]),
        (collection_name("SolutionApproach", project), [
            wvc.config.Property(name="ticket_id",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title",         data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="approach",      data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="review_notes",  data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="status",        data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="modules",       data_type=wvc.config.DataType.TEXT_ARRAY),
            wvc.config.Property(name="files_changed", data_type=wvc.config.DataType.TEXT_ARRAY),
            wvc.config.Property(name="pr_number",     data_type=wvc.config.DataType.INT),
            wvc.config.Property(name="created_at",    data_type=wvc.config.DataType.DATE),
        ]),
        (collection_name("ArchitectureDecisions", project), [
            wvc.config.Property(name="adr_id",        data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title",         data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="status",        data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="context",       data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="decision",      data_type=wvc.config.DataType.TEXT,
                                index_searchable=True),
            wvc.config.Property(name="consequences",  data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="modules",       data_type=wvc.config.DataType.TEXT_ARRAY),
            wvc.config.Property(name="source_file",   data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content_hash",  data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at",    data_type=wvc.config.DataType.DATE),
        ]),
    ]

    for coll_name, props in collections:
        if coll_name in existing:
            print(f"Collection exists: {coll_name}")
        else:
            client.collections.create(
                name=coll_name,
                vectorizer_config=wvc.config.Configure.Vectorizer.none(),
                vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
                    distance_metric=wvc.config.VectorDistances.COSINE,
                ),
                properties=props,
            )
            print(f"Created collection: {coll_name}")


def migrate_schema(client: weaviate.WeaviateClient, project: str) -> None:
    """Drop and recreate all collections. Required when EMBED_DIMS changes.

    After running --migrate, re-index everything:
      python update_kb.py --repo-root . --project myapp --full
      python update_kb.py --standards --repo-root . --project myapp
    """
    existing = {c.name for c in client.collections.list_all().values()}
    bases = ["CodebaseKnowledge", "CodingStandards", "ReviewPatterns",
             "SolutionApproach", "ArchitectureDecisions"]
    for base in bases:
        name = collection_name(base, project)
        if name in existing:
            client.collections.delete(name)
            print(f"Dropped: {name}")
    print("Re-creating collections with updated schema...")
    init_schema(client, project)
    print("Migration complete. Re-run --standards and codebase indexing to repopulate.")


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.name in SKIP_FILES:
        return True
    for pat in SKIP_PATTERNS:
        if fnmatch.fnmatch(path.name, pat):
            return True
    if path.suffix.lower() not in INCLUDE_EXTENSIONS:
        return True
    return False


def update_codebase(
    client: weaviate.WeaviateClient,
    repo_root: Path,
    project: str,
    force_full: bool = False,
) -> None:
    coll_name = collection_name("CodebaseKnowledge", project)
    collection = client.collections.get(coll_name)

    existing_hashes: dict[str, str] = {}
    if not force_full:
        try:
            result = collection.query.fetch_objects(limit=50_000,
                return_properties=["chunk_id", "content_hash"])
            for obj in result.objects:
                cid = obj.properties.get("chunk_id", "")
                h = obj.properties.get("content_hash", "")
                if cid:
                    existing_hashes[cid] = h
        except Exception:
            pass

    files = [p for p in repo_root.rglob("*") if p.is_file() and not should_skip(p)]
    print(f"Found {len(files)} files to index in {repo_root}")

    now = datetime.now(timezone.utc).isoformat()
    batch_objects = []
    skipped = added = updated = 0

    for file_path in files:
        try:
            if file_path.stat().st_size > MAX_FILE_BYTES:
                skipped += 1
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                skipped += 1
                continue
        except Exception:
            skipped += 1
            continue

        rel_path = str(file_path.relative_to(repo_root))
        module = classify_module(rel_path)
        doc_type = classify_doc_type(rel_path)
        category = classify_category(module, doc_type)
        language = classify_language(rel_path)

        chunks_with_offsets = chunk_smart_with_offsets(content, language)
        for i, (chunk, chunk_offset) in enumerate(chunks_with_offsets):
            chunk_id = f"{rel_path}::chunk_{i}"
            content_hash = hashlib.md5(chunk.encode()).hexdigest()

            if not force_full and existing_hashes.get(chunk_id) == content_hash:
                skipped += 1
                continue

            # Inject enclosing class name for TS/JS so method chunks stay
            # anchored to their class during retrieval.
            class_ctx = (
                extract_class_context(content, chunk_offset)
                if language in ("typescript", "javascript")
                else None
            )
            class_header = f"// Class: {class_ctx}\n" if class_ctx else ""
            embed_text = f"[module:{module}] [type:{doc_type}]\nFile: {rel_path}\n{class_header}\n{chunk}"
            vector = embed(embed_text)

            props = {
                "chunk_id": chunk_id,
                "file_path": rel_path,
                "content": chunk,
                "module": module,
                "doc_type": doc_type,
                "category": category,
                "language": language,
                "content_hash": content_hash,
                "last_updated": now,
            }

            if chunk_id in existing_hashes:
                old_results = collection.query.fetch_objects(
                    filters=wvc.query.Filter.by_property("chunk_id").equal(chunk_id),
                    limit=1,
                )
                if old_results.objects:
                    collection.data.delete_by_id(old_results.objects[0].uuid)
                updated += 1
            else:
                added += 1

            batch_objects.append((props, vector))

            if len(batch_objects) >= BATCH_SIZE:
                _flush_batch(collection, batch_objects)
                batch_objects = []

    if batch_objects:
        _flush_batch(collection, batch_objects)

    print(f"Codebase KB [{coll_name}]: added={added}, updated={updated}, skipped={skipped}")


def _flush_batch(
    collection: weaviate.collections.Collection,
    batch: list[tuple[dict, list[float]]],
) -> None:
    with collection.batch.dynamic() as b:
        for props, vector in batch:
            b.add_object(properties=props, vector=vector)


def update_standards(
    client: weaviate.WeaviateClient,
    repo_root: Path,
    project: str,
) -> None:
    coll_name = collection_name("CodingStandards", project)
    collection = client.collections.get(coll_name)

    rule_dirs = [
        repo_root / ".claude" / "rules",
        repo_root / ".claude" / "commands",
        repo_root / ".cursor" / "rules",
        repo_root / "docs" / "standards",
        repo_root / "docs" / "guidelines",
        repo_root / ".claude",
    ]

    rule_files: list[Path] = []
    for d in rule_dirs:
        if d.exists():
            rule_files.extend(d.glob("*.md"))
            rule_files.extend(d.glob("*.mdc"))
            rule_files.extend(d.glob("*.txt"))

    docs_root = repo_root / "docs"
    if docs_root.exists():
        for f in docs_root.rglob("*.md"):
            if f not in rule_files:
                rule_files.append(f)

    for root_file in ["CODE_STANDARDS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md",
                       "pull_request_template.md"]:
        p = repo_root / root_file
        if p.exists() and p not in rule_files:
            rule_files.append(p)

    if not rule_files:
        print("No rule files found. Checked: .claude/rules/, .cursor/rules/, docs/standards/")
        return

    existing_hashes: dict[str, str] = {}
    try:
        result = collection.query.fetch_objects(limit=10_000,
            return_properties=["rule_id", "content_hash"])
        for obj in result.objects:
            rid = obj.properties.get("rule_id", "")
            h = obj.properties.get("content_hash", "")
            if rid:
                existing_hashes[rid] = h
    except Exception:
        pass

    added = updated = skipped = 0

    for file_path in rule_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        source_file = file_path.name
        rule_type = _infer_rule_type(source_file, content)

        chunks = chunk_text(content, max_size=3000, overlap=200)
        for i, chunk in enumerate(chunks):
            rule_id = f"{source_file}::rule_{i}"
            content_hash = hashlib.md5(chunk.encode()).hexdigest()

            if existing_hashes.get(rule_id) == content_hash:
                skipped += 1
                continue

            title = _extract_title(chunk, source_file)
            embed_text = f"Rule [{rule_type}]: {title}\n\n{chunk}"
            vector = embed(embed_text)

            props = {
                "rule_id": rule_id,
                "source_file": source_file,
                "rule_type": rule_type,
                "title": title,
                "content": chunk,
                "content_hash": content_hash,
            }

            if rule_id in existing_hashes:
                old = collection.query.fetch_objects(
                    filters=wvc.query.Filter.by_property("rule_id").equal(rule_id),
                    limit=1,
                )
                if old.objects:
                    collection.data.delete_by_id(old.objects[0].uuid)
                updated += 1
            else:
                added += 1

            collection.data.insert(properties=props, vector=vector)

    print(f"Standards KB [{coll_name}]: added={added}, updated={updated}, skipped={skipped}")


def _infer_rule_type(filename: str, content: str) -> str:
    name = filename.lower()
    if "test" in name or "spec" in name:
        return "testing"
    if "security" in name or "auth" in name:
        return "security"
    if "performance" in name or "perf" in name:
        return "performance"
    if "style" in name or "format" in name or "lint" in name:
        return "style"
    if "structure" in name or "architecture" in name or "project" in name:
        return "architecture"
    if "quality" in name:
        return "quality"
    return "general"


def _extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return fallback


def _parse_adr(content: str) -> dict:
    """Extract ADR fields from a Markdown ADR file (MADR/Nygard style)."""
    sections: dict[str, str] = {}
    current_section = "header"
    lines_buf: list[str] = []

    for line in content.splitlines():
        heading = None
        if line.startswith("## "):
            heading = line[3:].strip().lower()
        elif line.startswith("# "):
            heading = "title"

        if heading is not None:
            sections[current_section] = "\n".join(lines_buf).strip()
            lines_buf = []
            current_section = heading
            if heading == "title":
                lines_buf.append(line[2:].strip())
        else:
            lines_buf.append(line)

    sections[current_section] = "\n".join(lines_buf).strip()

    title = sections.get("title", "")
    status = ""
    for key in sections:
        if "status" in key:
            status = sections[key].split("\n")[0].strip()
            break

    context = sections.get("context", sections.get("context and problem statement", ""))
    decision = sections.get("decision", sections.get("decision outcome", ""))
    consequences = sections.get("consequences", sections.get("positive consequences", ""))

    return {
        "title": title,
        "status": status or "accepted",
        "context": context,
        "decision": decision,
        "consequences": consequences,
    }


def update_adrs(
    client: weaviate.WeaviateClient,
    repo_root: Path,
    project: str,
) -> None:
    coll_name = collection_name("ArchitectureDecisions", project)

    try:
        adr_collection = client.collections.get(coll_name)
    except Exception:
        print(f"ArchitectureDecisions collection not found: {coll_name}. Run --init-schema first.")
        return

    adr_dirs = [
        repo_root / "docs" / "adr",
        repo_root / "docs" / "decisions",
        repo_root / "docs" / "architecture",
        repo_root / ".claude" / "decisions",
        repo_root / "adr",
    ]

    adr_files: list[Path] = []
    for d in adr_dirs:
        if d.exists():
            adr_files.extend(sorted(d.glob("*.md")))

    if not adr_files:
        print(f"No ADR files found. Checked: {[str(d) for d in adr_dirs]}")
        print("Create docs/adr/0001-example.md to get started.")
        return

    existing_hashes: dict[str, str] = {}
    try:
        result = adr_collection.query.fetch_objects(
            limit=10_000, return_properties=["adr_id", "content_hash"]
        )
        for obj in result.objects:
            aid = obj.properties.get("adr_id", "")
            h = obj.properties.get("content_hash", "")
            if aid:
                existing_hashes[aid] = h
    except Exception:
        pass

    added = updated = skipped = 0

    for file_path in adr_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        if not content.strip():
            skipped += 1
            continue

        adr_id = file_path.stem
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if existing_hashes.get(adr_id) == content_hash:
            skipped += 1
            continue

        parsed = _parse_adr(content)
        title = parsed["title"] or file_path.stem
        full_text = f"{title}\n\n{parsed['context']}\n\n{parsed['decision']}\n\n{parsed['consequences']}"
        vector = embed(f"ADR: {title}\n\n{full_text}")

        props = {
            "adr_id": adr_id,
            "title": title,
            "status": parsed["status"],
            "context": parsed["context"],
            "decision": parsed["decision"],
            "consequences": parsed["consequences"],
            "modules": [],
            "source_file": str(file_path.relative_to(repo_root)),
            "content_hash": content_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if adr_id in existing_hashes:
            old = adr_collection.query.fetch_objects(
                filters=wvc.query.Filter.by_property("adr_id").equal(adr_id), limit=1
            )
            if old.objects:
                adr_collection.data.delete_by_id(old.objects[0].uuid)
            updated += 1
        else:
            added += 1

        adr_collection.data.insert(properties=props, vector=vector)

    print(f"Architecture Decisions [{coll_name}]: added={added}, updated={updated}, skipped={skipped}")


def prune_stale_chunks(
    client: weaviate.WeaviateClient,
    repo_root: Path,
    project: str,
) -> None:
    """Delete chunks whose source files no longer exist in the repo."""
    coll_name = collection_name("CodebaseKnowledge", project)
    collection = client.collections.get(coll_name)

    all_chunks: list[tuple[str, str, str]] = []
    try:
        result = collection.query.fetch_objects(
            limit=100_000,
            return_properties=["chunk_id", "file_path"],
        )
        for obj in result.objects:
            cid = obj.properties.get("chunk_id", "")
            fp = obj.properties.get("file_path", "")
            if cid:
                all_chunks.append((str(obj.uuid), cid, fp))
    except Exception as e:
        print(f"Failed to fetch chunks: {e}")
        return

    unique_paths = {fp for _, _, fp in all_chunks if fp}
    missing_paths = {fp for fp in unique_paths if not (repo_root / fp).exists()}

    if not missing_paths:
        print(f"Prune [{coll_name}]: no stale chunks found ({len(all_chunks):,} chunks, all files present)")
        return

    stale_uuids = [uuid for uuid, _, fp in all_chunks if fp in missing_paths]
    print(f"Prune [{coll_name}]: found {len(missing_paths)} missing files, "
          f"deleting {len(stale_uuids)} stale chunks...")

    deleted = 0
    for uuid in stale_uuids:
        try:
            collection.data.delete_by_id(uuid)
            deleted += 1
        except Exception:
            pass

    print(f"Prune [{coll_name}]: deleted={deleted}, missing_files={len(missing_paths)}")
    for p in sorted(missing_paths)[:10]:
        print(f"  - {p}")
    if len(missing_paths) > 10:
        print(f"  ... and {len(missing_paths) - 10} more")


def print_stats(client: weaviate.WeaviateClient, project: str) -> None:
    all_collections = client.collections.list_all()
    bases = ["CodebaseKnowledge", "CodingStandards", "ReviewPatterns",
             "SolutionApproach", "ArchitectureDecisions"]
    print(f"\n=== Weaviate Stats (project: {project or 'default'}) ===")
    for base in bases:
        name = collection_name(base, project)
        if name in {c.name for c in all_collections.values()}:
            coll = client.collections.get(name)
            count = coll.aggregate.over_all(total_count=True).total_count
            print(f"  {name}: {count:,} objects")
        else:
            print(f"  {name}: not found")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Index codebase and standards into Weaviate")
    parser.add_argument("--repo-root", type=str, default=".",
                        help="Path to the repository root (default: current directory)")
    parser.add_argument("--project", default=os.getenv("AGENTS_PROJECT", "default"),
                        help="Project name for collection namespacing")
    parser.add_argument("--standards", action="store_true",
                        help="Update CodingStandards collection")
    parser.add_argument("--init-schema", action="store_true",
                        help="Create collections if they don't exist")
    parser.add_argument("--stats", action="store_true",
                        help="Print collection statistics")
    parser.add_argument("--full", action="store_true",
                        help="Force re-embed all files (ignore cached hashes)")
    parser.add_argument("--migrate", action="store_true",
                        help="Drop and recreate all collections (required after EMBED_MODEL change)")
    parser.add_argument("--prune", action="store_true",
                        help="Delete chunks whose source files no longer exist in the repo")
    parser.add_argument("--adrs", action="store_true",
                        help="Index Architecture Decision Records from docs/adr/ or docs/decisions/")
    args = parser.parse_args()

    # Readiness check — fail fast before attempting connection
    import urllib.request
    def _weaviate_ready(url: str = WEAVIATE_URL) -> bool:
        try:
            with urllib.request.urlopen(f"{url}/v1/.well-known/ready", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    if not _weaviate_ready():
        print(f"⚠️  Weaviate not reachable at {WEAVIATE_URL}")
        print("Start it: python scripts/start_weaviate.py")
        sys.exit(1)

    client = get_client()
    try:
        if args.migrate:
            migrate_schema(client, args.project)
            return

        if args.init_schema:
            init_schema(client, args.project)
            return

        if args.stats:
            print_stats(client, args.project)
            return

        repo_root = Path(args.repo_root).resolve()
        if not repo_root.exists():
            print(f"Repo root not found: {repo_root}")
            sys.exit(1)

        if args.prune:
            prune_stale_chunks(client, repo_root, args.project)
        elif args.adrs:
            update_adrs(client, repo_root, args.project)
        elif args.standards:
            update_standards(client, repo_root, args.project)
        else:
            update_codebase(client, repo_root, args.project, force_full=args.full)
    finally:
        client.close()


if __name__ == "__main__":
    main()
