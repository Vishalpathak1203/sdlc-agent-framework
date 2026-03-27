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
  python update_kb.py --stats --project myapp
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
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIMS = 384
BATCH_SIZE = 25
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200

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

MAX_FILE_BYTES = 50_000

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

# Patterns are checked in order. First match wins.
# Add your project's module structure here.
MODULE_PATTERNS: list[tuple[str, list[str]]] = [
    # Auth / Identity
    ("auth",          ["**/auth/**", "**/authentication/**", "**/user-auth/**", "**/login/**",
                       "**/identity/**", "**/sso/**"]),
    # Payments / Billing
    ("payments",      ["**/payment*/**", "**/billing/**", "**/invoice*/**",
                       "**/subscription-billing/**", "**/checkout-payment/**"]),
    # Orders
    ("orders",        ["**/order*/**"]),
    # Cart / Checkout
    ("cart",          ["**/cart*/**", "**/checkout*/**", "**/shopping*/**", "**/basket*/**"]),
    # Listings / Products / Catalog
    ("listings",      ["**/listing*/**", "**/product*/**", "**/catalog*/**", "**/item*/**"]),
    # Notifications
    ("notifications", ["**/notification*/**", "**/email/**", "**/sms/**", "**/push/**",
                       "**/mailer/**", "**/emailer/**"]),
    # Users / Profiles
    ("users",         ["**/user*/**", "**/profile*/**", "**/account*/**", "**/member*/**"]),
    # Search
    ("search",        ["**/search/**", "**/elastic*/**", "**/solr/**", "**/index*/**"]),
    # Scheduler / Jobs / Queues
    ("scheduler",     ["**/scheduler/**", "**/cron/**", "**/jobs/**", "**/queue*/**",
                       "**/worker*/**", "**/processor*/**", "**/task*/**"]),
    # Webhooks / Events
    ("webhooks",      ["**/webhook*/**", "**/hooks/**", "**/event*/**", "**/listener*/**"]),
    # Reports / Documents
    ("reports",       ["**/report*/**", "**/document*/**", "**/export*/**", "**/pdf*/**"]),
    # Fraud / Risk
    ("fraud",         ["**/fraud/**", "**/risk/**", "**/compliance/**", "**/abuse/**"]),
    # Saved items / Favorites
    ("saved",         ["**/saved*/**", "**/bookmark*/**", "**/wishlist*/**", "**/favorite*/**"]),
    # Admin / Dashboard
    ("admin",         ["**/admin*/**", "**/dashboard/**", "**/backoffice/**", "**/internal/**"]),
    # Messages / Chat
    ("messages",      ["**/message*/**", "**/chat/**", "**/inbox/**", "**/thread*/**",
                       "**/conversation*/**"]),
    # Pricing / Discount
    ("pricing",       ["**/pricing/**", "**/discount*/**", "**/coupon*/**", "**/promo*/**"]),
    # Subscriptions / Plans
    ("subscriptions", ["**/subscription*/**", "**/plan*/**", "**/tier*/**"]),
    # Device / Session
    ("device",        ["**/device*/**", "**/session*/**", "**/token*/**"]),
    # Refund / Returns
    ("refund",        ["**/refund*/**", "**/return*/**", "**/chargeback*/**"]),
    # UI common / components
    ("ui-common",     ["**/components/common/**", "**/components/shared/**",
                       "**/components/ui/**", "**/design-system/**"]),
    # UI pages
    ("ui-pages",      ["**/pages/**", "**/views/**", "**/screens/**"]),
    # UI stores / state
    ("ui-stores",     ["**/stores/**", "**/store/**", "**/state/**", "**/context/**"]),
    # UI composables / hooks
    ("ui-composables",["**/composables/**", "**/hooks/**", "**/use-*.ts", "**/use-*.js"]),
    # Infrastructure / Config
    ("infra",         ["**/config/**", "**/infra/**", "**/setup/**", "**/middleware/**",
                       "**/bootstrap/**"]),
    # External service integrations
    # Add your 3rd-party service directories here, e.g.:
    #   ("payments-gateway", ["**/stripe/**", "**/paypal/**"]),
    #   ("analytics",        ["**/segment/**", "**/mixpanel/**"]),
    ("integration",   ["**/external*/**", "**/third-party/**", "**/partner*/**",
                       "**/api-client*/**", "**/sdk*/**"]),
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
    ("util",       ["*.util.*", "*Utils.*", "*Helper.*", "*.helper.*"]),
    ("spec",       ["*.dto.*", "*Dto.*", "*.interface.*", "*.type.*", "*.types.*"]),
    ("config",     ["*.config.*", "*Config.*", ".env*", "nuxt.config.*", "vite.config.*"]),
    ("docs",       ["*.md", "*.mdx"]),
]


def classify_doc_type(file_path: str) -> str:
    name = Path(file_path).name
    for doc_type, patterns in DOC_TYPE_PATTERNS:
        for pat in patterns:
            if fnmatch.fnmatch(name, pat):
                return doc_type
    return "source"


# ── Category classification ────────────────────────────────────────────────

def classify_category(module: str, doc_type: str) -> str:
    if doc_type == "test":
        return "testing"
    if doc_type in ("schema",):
        return "data-access"
    if doc_type in ("dto", "spec", "interface"):
        return "api-contract"
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


# ── Language classification ────────────────────────────────────────────────

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


# ── Weaviate ───────────────────────────────────────────────────────────────

def get_client(url: str = WEAVIATE_URL) -> weaviate.WeaviateClient:
    port = int(url.rstrip("/").split(":")[-1])
    return weaviate.connect_to_local(host="localhost", port=port, grpc_port=port + 1)


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
            wvc.config.Property(name="author",       data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at",   data_type=wvc.config.DataType.DATE),
        ]),
        (collection_name("SolutionApproach", project), [
            wvc.config.Property(name="ticket_id",    data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title",        data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="approach",     data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="review_notes", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="status",       data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="created_at",   data_type=wvc.config.DataType.DATE),
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

    # Load existing hashes
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

        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{rel_path}::chunk_{i}"
            content_hash = hashlib.md5(chunk.encode()).hexdigest()

            if not force_full and existing_hashes.get(chunk_id) == content_hash:
                skipped += 1
                continue

            # Build embedding text with classification prefix for better retrieval
            embed_text = f"[module:{module}] [type:{doc_type}]\nFile: {rel_path}\n\n{chunk}"
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
                # Update existing — delete and re-insert
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

    # Look for rule files in common locations
    rule_dirs = [
        repo_root / ".claude" / "rules",
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


def print_stats(client: weaviate.WeaviateClient, project: str) -> None:
    all_collections = client.collections.list_all()
    prefix = "" if not project or project == "default" else f"_{project.replace('-', '_')}"
    bases = ["CodebaseKnowledge", "CodingStandards", "ReviewPatterns", "SolutionApproach"]
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
                        help="Update CodingStandards collection (looks in .claude/rules/, .cursor/rules/)")
    parser.add_argument("--init-schema", action="store_true",
                        help="Create collections if they don't exist")
    parser.add_argument("--stats", action="store_true",
                        help="Print collection statistics")
    parser.add_argument("--full", action="store_true",
                        help="Force re-embed all files (ignore cached hashes)")
    args = parser.parse_args()

    client = get_client()
    try:
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

        if args.standards:
            update_standards(client, repo_root, args.project)
        else:
            update_codebase(client, repo_root, args.project, force_full=args.full)
    finally:
        client.close()


if __name__ == "__main__":
    main()
