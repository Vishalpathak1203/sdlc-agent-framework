#!/usr/bin/env python3
"""
query_rag.py — Hybrid search + re-ranking RAG query and solution management.

Combines vector similarity search and BM25 keyword search, with optional
cross-encoder re-ranking for maximum precision.

Usage:
  # Hybrid search (vector + BM25) with re-ranking
  python query_rag.py "payment retry logic" --project myapp --rerank

  # Specific collection
  python query_rag.py "N+1 query pattern" --collection reviews --project myapp

  # Scope to a module (codebase only)
  python query_rag.py "email send" --collection codebase --module notifications --project myapp

  # Multi-query: auto-generate variants to reduce phrasing sensitivity
  python query_rag.py "auth token validation" --multi-query --rerank --project myapp

  # Filter low-relevance results
  python query_rag.py "cache invalidation" --min-score 0.5 --project myapp

  # Store a solution approach
  python query_rag.py --store-solution --ticket PROJ-123 \
    --title "Add pagination" --approach-file solution.md --project myapp

  # Retrieve a solution
  python query_rag.py --get-solution PROJ-123 --project myapp

  # Update solution status
  python query_rag.py --update-solution PROJ-123 --status approved --project myapp
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import weaviate
import weaviate.classes as wvc
from fastembed import TextEmbedding

WEAVIATE_URL = os.getenv("AGENTS_WEAVIATE_URL", "http://localhost:8090")
WEAVIATE_GRPC_PORT = int(os.getenv("AGENTS_WEAVIATE_GRPC_PORT", "0"))

# Code-aware embedding model: understands TypeScript, Python, etc. better than
# general-purpose English models. Produces 768-dim vectors.
# Upgrade from BAAI/bge-small-en-v1.5 (384d) — meaningfully better retrieval
# for code, type names, decorators, and framework-specific patterns.
EMBED_MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"

# 12-layer cross-encoder for re-ranking (vs the common 6-layer MiniLM-L6).
# Better at distinguishing relevant from near-miss code chunks.
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-12-v2"

_embedder: TextEmbedding | None = None
_reranker = None


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(EMBED_MODEL_NAME)
    return _embedder


def get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(RERANK_MODEL_NAME)
        except ImportError:
            print("sentence-transformers not installed. Run: pip install sentence-transformers")
            print("Falling back to no re-ranking.")
            return None
    return _reranker


def embed(text: str) -> list[float]:
    return next(get_embedder().embed([text])).tolist()


def check_weaviate_ready(url: str = WEAVIATE_URL) -> bool:
    """Fast pre-flight check before attempting any Weaviate connection."""
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/v1/.well-known/ready", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


# Stopwords stripped in multi-query keyword-only variant
_STOPWORDS = {
    "the", "a", "an", "in", "for", "of", "to", "with", "from", "how", "does", "what", "is", "are",
    "we", "our", "this", "that", "it", "on", "at", "by", "or", "and", "not", "do", "be", "as", "was",
    "but", "have", "had", "has", "can", "will", "when", "where", "which", "who", "if", "then", "than",
    "there", "their", "they", "some", "any", "all", "each", "use", "using", "used", "into", "its",
}


def generate_query_variants(query: str, collection_alias: str) -> list[str]:
    """Generate 2-3 query variants to improve recall across phrasing differences.

    Why: "how does auth token work" and "token validation logic" describe the
    same thing but embed differently. Multi-query runs all variants, merges
    results, and deduplicates — net more coverage, same re-ranking pass.
    """
    variants = [query]
    tokens = [t for t in query.lower().split() if t not in _STOPWORDS and len(t) > 2]
    if tokens and len(tokens) < len(query.split()):
        variants.append(" ".join(tokens))
    if collection_alias == "codebase":
        variants.append(f"typescript {query}")
    elif collection_alias == "reviews":
        variants.append(f"code review {query}")
    elif collection_alias == "standards":
        variants.append(f"rule {query}")
    seen: set[str] = set()
    result: list[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


def _run_single_query(
    query: str,
    collection,
    vector: list[float],
    fetch_limit: int,
    alpha: float,
    filters,
) -> list[tuple[dict, float]]:
    try:
        results = collection.query.hybrid(
            query=query,
            vector=vector,
            alpha=alpha,
            limit=fetch_limit,
            filters=filters,
            return_metadata=wvc.query.MetadataQuery(score=True),
        )
    except Exception:
        results = collection.query.near_vector(
            near_vector=vector,
            limit=fetch_limit,
            filters=filters,
            return_metadata=wvc.query.MetadataQuery(distance=True),
        )
    return [
        (obj.properties, getattr(obj.metadata, "score", 0) or (1 - getattr(obj.metadata, "distance", 0.5)))
        for obj in results.objects
    ]


def _merge_results(all_items: list[list[tuple[dict, float]]]) -> list[tuple[dict, float]]:
    """Merge multi-query result sets, deduplicating by identity key and keeping best score."""
    seen: dict[str, tuple[dict, float]] = {}
    for items in all_items:
        for props, score in items:
            key = (
                props.get("chunk_id")
                or props.get("pattern_id")
                or props.get("rule_id")
                or (props.get("file_path", "") + "::" + props.get("content", props.get("comment", ""))[:80])
            )
            if key not in seen or score > seen[key][1]:
                seen[key] = (props, score)
    return list(seen.values())


def get_client() -> weaviate.WeaviateClient:
    port = int(WEAVIATE_URL.rstrip("/").split(":")[-1])
    grpc_port = WEAVIATE_GRPC_PORT if WEAVIATE_GRPC_PORT else port + 1
    return weaviate.connect_to_local(host="localhost", port=port, grpc_port=grpc_port)


def collection_name(base: str, project: str) -> str:
    if not project or project == "default":
        return base
    safe = "".join(c if c.isalnum() else "_" for c in project)
    return f"{base}_{safe}"


COLLECTION_MAP = {
    "codebase":   "CodebaseKnowledge",
    "standards":  "CodingStandards",
    "reviews":    "ReviewPatterns",
    "decisions":  "ArchitectureDecisions",
}

# Per-collection hybrid search alpha (1.0 = pure vector, 0.0 = pure BM25)
# Tuned based on what retrieval mode dominates each collection's use case.
COLLECTION_ALPHA: dict[str, float] = {
    "codebase":  0.6,   # balanced — function/type names matter for BM25
    "standards": 0.5,   # keyword-heavy — exact rule names and linting terms
    "reviews":   0.8,   # semantic — similar pattern intent > keywords
    "decisions": 0.7,   # semantic — architectural reasoning, not exact keywords
}


def rerank(query: str, items: list[tuple[dict, float]], top_k: int) -> list[tuple[dict, float]]:
    reranker = get_reranker()
    if reranker is None or len(items) <= top_k:
        return items[:top_k]

    content_key = _get_content_key(items)
    pairs = [(query, item[0].get(content_key, "")) for item in items]

    try:
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, items), key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:top_k]]
    except Exception as e:
        print(f"Re-ranking failed ({e}), using original order.")
        return items[:top_k]


def _get_content_key(items: list[tuple[dict, float]]) -> str:
    if items and "comment" in items[0][0]:
        return "comment"
    return "content"


def query_collection(
    query: str,
    collection_alias: str = "codebase",
    project: str = "default",
    top_k: int = 5,
    use_rerank: bool = False,
    rerank_candidates: int = 20,
    alpha: float | None = None,
    reviewer: str | None = None,
    module_filter: str | None = None,
    min_score: float = 0.0,
    multi_query: bool = False,
) -> None:
    if not check_weaviate_ready():
        print(f"⚠️  Weaviate not reachable at {WEAVIATE_URL}")
        print("Start it: python scripts/start_weaviate.py")
        sys.exit(1)

    if alpha is None:
        alpha = COLLECTION_ALPHA.get(collection_alias, 0.7)
    base_name = COLLECTION_MAP.get(collection_alias, "CodebaseKnowledge")
    coll_name = collection_name(base_name, project)

    client = get_client()
    try:
        collection = client.collections.get(coll_name)
        fetch_limit = rerank_candidates if (use_rerank or multi_query) else top_k

        filters = None
        if reviewer and collection_alias == "reviews":
            filters = wvc.query.Filter.by_property("author").equal(reviewer)
        if module_filter and collection_alias == "codebase":
            module_f = wvc.query.Filter.by_property("module").equal(module_filter)
            filters = (filters & module_f) if filters else module_f

        queries = generate_query_variants(query, collection_alias) if multi_query else [query]
        all_result_sets = []
        for q in queries:
            vector = embed(q)
            items = _run_single_query(q, collection, vector, fetch_limit, alpha, filters)
            all_result_sets.append(items)

        if multi_query and len(all_result_sets) > 1:
            items = _merge_results(all_result_sets)
            print(f"Multi-query: {len(queries)} variants → {len(items)} unique candidates")
        else:
            items = all_result_sets[0]

        if not items:
            print(f"No results for: '{query}' (collection: {coll_name})")
            return

        if use_rerank:
            print(f"Re-ranking {len(items)} candidates → top {top_k}...")
            items = rerank(query, items, top_k)
        else:
            items = sorted(items, key=lambda x: x[1], reverse=True)[:top_k]

        if min_score > 0:
            below_count = sum(1 for _, s in items if s < min_score)
            items = [(p, s) for p, s in items if s >= min_score]
            if below_count:
                print(f"⚠️  {below_count} result(s) below min-score {min_score:.2f} filtered out")
            if not items:
                print(f"⚠️  No results above min-score {min_score:.2f} for: '{query}'")
                return

        print(f"\n## RAG Context [{coll_name}]: '{query}' (top {len(items)})\n")

        for i, (props, score) in enumerate(items, 1):
            if collection_alias == "standards":
                print(f"### [{i}] {props.get('source_file', '?')} — {props.get('title', '')} "
                      f"[{props.get('rule_type', '?')}] (score: {score:.3f})")
            elif collection_alias == "reviews":
                decision = props.get("decision", "") or "unknown"
                print(f"### [{i}] PR #{props.get('pr_number', '?')}: {props.get('pr_title', '')} "
                      f"[{props.get('category', '?')}] decision={decision} (score: {score:.3f})")
                if props.get("file_path"):
                    print(f"File: {props['file_path']} | Module: {props.get('module', '?')} "
                          f"| Type: {props.get('doc_type', '?')} | Reviewer: {props.get('author', '?')} "
                          f"| Author: {props.get('pr_author', '?')}")
                if props.get("reasoning"):
                    print(f"Reasoning: {props['reasoning']}")
            elif collection_alias == "decisions":
                print(f"### [{i}] ADR: {props.get('title', props.get('adr_id', '?'))} "
                      f"[{props.get('status', '?')}] (score: {score:.3f})")
                print(f"File: {props.get('source_file', '?')}")
                if props.get("context"):
                    print(f"\n**Context:** {props['context'][:300]}")
                if props.get("decision"):
                    print(f"\n**Decision:** {props['decision'][:300]}")
                if props.get("consequences"):
                    print(f"\n**Consequences:** {props['consequences'][:200]}")
                print("\n---\n")
                continue
            else:
                print(f"### [{i}] {props.get('file_path', 'unknown')} (score: {score:.3f})")
                print(f"Module: {props.get('module', '?')} | Type: {props.get('doc_type', '?')} "
                      f"| Category: {props.get('category', '?')}")

            print()
            content_key = "comment" if collection_alias == "reviews" else "content"
            print(props.get(content_key, ""))
            print("\n---\n")
    finally:
        client.close()


def store_solution(
    ticket_id: str,
    title: str,
    approach_text: str,
    project: str,
    modules: list[str] | None = None,
    files_changed: list[str] | None = None,
    pr_number: int | None = None,
) -> None:
    coll_name = collection_name("SolutionApproach", project)
    client = get_client()
    try:
        collection = client.collections.get(coll_name)
        existing = collection.query.fetch_objects(
            filters=wvc.query.Filter.by_property("ticket_id").equal(ticket_id),
            limit=1,
        )
        if existing.objects:
            collection.data.delete_by_id(existing.objects[0].uuid)
            print(f"Replaced existing solution for {ticket_id}")

        vector = embed(f"{title}\n{approach_text}")
        props: dict = {
            "ticket_id": ticket_id,
            "title": title,
            "approach": approach_text,
            "review_notes": "",
            "status": "draft",
            "modules": modules or [],
            "files_changed": files_changed or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if pr_number is not None:
            props["pr_number"] = pr_number
        collection.data.insert(properties=props, vector=vector)
        print(f"Stored solution for {ticket_id} (status: draft)")
    finally:
        client.close()


def update_decision(
    pr_number: int,
    file_path: str,
    decision: str,
    reasoning: str,
    project: str,
) -> None:
    coll_name = collection_name("ReviewPatterns", project)
    client = get_client()
    try:
        collection = client.collections.get(coll_name)
        filters = wvc.query.Filter.by_property("pr_number").equal(pr_number)
        if file_path:
            filters = filters & wvc.query.Filter.by_property("file_path").equal(file_path)
        results = collection.query.fetch_objects(filters=filters, limit=50)
        if not results.objects:
            print(f"No pattern found for PR #{pr_number} / {file_path}")
            return
        updated = 0
        for obj in results.objects:
            if not obj.properties.get("decision", ""):
                collection.data.update(
                    uuid=obj.uuid,
                    properties={"decision": decision, "reasoning": reasoning},
                )
                updated += 1
        print(f"Updated {updated} pattern(s) for PR #{pr_number} / {file_path} → {decision}")
    finally:
        client.close()


def get_solution(ticket_id: str, project: str) -> None:
    coll_name = collection_name("SolutionApproach", project)
    client = get_client()
    try:
        collection = client.collections.get(coll_name)
        results = collection.query.fetch_objects(
            filters=wvc.query.Filter.by_property("ticket_id").equal(ticket_id),
            limit=1,
        )
        if not results.objects:
            print(f"No solution found for: {ticket_id}")
            sys.exit(1)

        props = results.objects[0].properties
        print(f"## Solution Approach: {ticket_id}\n")
        print(f"**Title:** {props.get('title', '')}")
        print(f"**Status:** {props.get('status', 'draft')}")
        print(f"**Created:** {props.get('created_at', '')}")
        if props.get("review_notes"):
            print(f"\n**Review Notes:**\n{props['review_notes']}")
        print(f"\n---\n\n{props.get('approach', '')}")
    finally:
        client.close()


def update_solution(
    ticket_id: str,
    project: str,
    status: str | None = None,
    review_notes: str | None = None,
) -> None:
    coll_name = collection_name("SolutionApproach", project)
    client = get_client()
    try:
        collection = client.collections.get(coll_name)
        results = collection.query.fetch_objects(
            filters=wvc.query.Filter.by_property("ticket_id").equal(ticket_id),
            limit=1,
        )
        if not results.objects:
            print(f"No solution found for: {ticket_id}")
            sys.exit(1)

        uuid = results.objects[0].uuid
        updates: dict = {}
        if status:
            updates["status"] = status
        if review_notes:
            updates["review_notes"] = review_notes

        collection.data.update(uuid=uuid, properties=updates)
        print(f"Updated solution for {ticket_id}: {updates}")
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hybrid RAG search + solution management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--top", type=int, default=5, help="Results to return (default: 5)")
    parser.add_argument("--collection", choices=["codebase", "standards", "reviews", "decisions"],
                        default="codebase", help="Collection to search")
    parser.add_argument("--project", default=os.getenv("AGENTS_PROJECT", "default"),
                        help="Project name (namespaces Weaviate collections)")
    parser.add_argument("--rerank", action="store_true",
                        help="Enable cross-encoder re-ranking (~200ms extra, meaningfully more accurate)")
    parser.add_argument("--rerank-candidates", type=int, default=20,
                        help="Candidate pool size for re-ranking (default: 20)")
    parser.add_argument("--alpha", type=float, default=None,
                        help="Hybrid search weight: 1.0=pure vector, 0.0=pure BM25 "
                             "(default: auto per collection)")
    parser.add_argument("--reviewer", type=str, default=None,
                        help="Filter reviews collection by reviewer GitHub login")
    parser.add_argument("--module", type=str, default=None,
                        help="Filter codebase collection by module name "
                             "(e.g. --module auth, --module billing)")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Warn and filter results below this relevance score "
                             "(e.g. --min-score 0.5)")
    parser.add_argument("--multi-query", action="store_true",
                        help="Generate 2-3 query variants, merge results, then rerank "
                             "(reduces phrasing sensitivity)")

    parser.add_argument("--store-solution", action="store_true")
    parser.add_argument("--ticket", type=str)
    parser.add_argument("--title", type=str)
    parser.add_argument("--approach-file", type=str)
    parser.add_argument("--approach", type=str)
    parser.add_argument("--modules", type=str,
                        help="Comma-separated module names touched by the solution")
    parser.add_argument("--files", type=str,
                        help="Comma-separated file paths changed by the solution")
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--get-solution", type=str, metavar="TICKET_ID")
    parser.add_argument("--update-solution", type=str, metavar="TICKET_ID")
    parser.add_argument("--status", choices=["draft", "approved", "rejected"])
    parser.add_argument("--review-notes", type=str)

    parser.add_argument("--update-decision", action="store_true",
                        help="Record ACCEPT/DECLINE decision on a review pattern")
    parser.add_argument("--decision", choices=["ACCEPT", "DECLINE", "DISCUSS"])
    parser.add_argument("--file-path", type=str)
    parser.add_argument("--reasoning", type=str)

    args = parser.parse_args()
    project = args.project

    if args.get_solution:
        get_solution(args.get_solution, project)
        return
    if args.update_solution:
        update_solution(args.update_solution, project, args.status, args.review_notes)
        return
    if args.store_solution:
        if not args.ticket or not args.title:
            parser.error("--store-solution requires --ticket and --title")
        if args.approach_file:
            approach_text = Path(args.approach_file).read_text(encoding="utf-8")
        elif args.approach:
            approach_text = args.approach
        else:
            parser.error("--store-solution requires --approach-file or --approach")
        modules = [m.strip() for m in args.modules.split(",")] if args.modules else []
        files = [f.strip() for f in args.files.split(",")] if args.files else []
        store_solution(args.ticket, args.title, approach_text, project,
                       modules=modules, files_changed=files, pr_number=args.pr_number)
        return
    if args.update_decision:
        if not args.pr_number or not args.decision:
            parser.error("--update-decision requires --pr-number and --decision")
        update_decision(
            pr_number=args.pr_number,
            file_path=args.file_path or "",
            decision=args.decision,
            reasoning=args.reasoning or "",
            project=project,
        )
        return
    if args.query:
        query_collection(
            args.query,
            collection_alias=args.collection,
            project=project,
            top_k=args.top,
            use_rerank=args.rerank,
            rerank_candidates=args.rerank_candidates,
            alpha=args.alpha,
            reviewer=args.reviewer,
            module_filter=args.module,
            min_score=args.min_score,
            multi_query=args.multi_query,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
