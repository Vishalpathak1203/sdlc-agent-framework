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
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANK_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

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
            print("sentence-transformers not installed. Install: pip install sentence-transformers")
            print("Falling back to no re-ranking.")
            return None
    return _reranker


def embed(text: str) -> list[float]:
    return next(get_embedder().embed([text])).tolist()


def get_client() -> weaviate.WeaviateClient:
    port = int(WEAVIATE_URL.rstrip("/").split(":")[-1])
    return weaviate.connect_to_local(host="localhost", port=port, grpc_port=port + 1)


def collection_name(base: str, project: str) -> str:
    if not project or project == "default":
        return base
    safe = "".join(c if c.isalnum() else "_" for c in project)
    return f"{base}_{safe}"


COLLECTION_MAP = {
    "codebase":  "CodebaseKnowledge",
    "standards": "CodingStandards",
    "reviews":   "ReviewPatterns",
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
    alpha: float = 0.7,
) -> None:
    base_name = COLLECTION_MAP.get(collection_alias, "CodebaseKnowledge")
    coll_name = collection_name(base_name, project)

    client = get_client()
    try:
        vector = embed(query)
        collection = client.collections.get(coll_name)

        fetch_limit = rerank_candidates if use_rerank else top_k

        # Hybrid search: vector + BM25
        try:
            results = collection.query.hybrid(
                query=query,
                vector=vector,
                alpha=alpha,
                limit=fetch_limit,
                return_metadata=wvc.query.MetadataQuery(score=True),
            )
        except Exception:
            # Fallback to pure vector search if hybrid not available
            results = collection.query.near_vector(
                near_vector=vector,
                limit=fetch_limit,
                return_metadata=wvc.query.MetadataQuery(distance=True),
            )

        if not results.objects:
            print(f"No results for: '{query}' (collection: {coll_name})")
            return

        items = [
            (obj.properties, getattr(obj.metadata, "score", 0) or (1 - getattr(obj.metadata, "distance", 0.5)))
            for obj in results.objects
        ]

        if use_rerank:
            print(f"Re-ranking {len(items)} candidates → top {top_k}...")
            items = rerank(query, items, top_k)
        else:
            items = items[:top_k]

        print(f"\n## RAG Context [{coll_name}]: '{query}' (top {len(items)})\n")

        for i, (props, score) in enumerate(items, 1):
            if collection_alias == "standards":
                print(f"### [{i}] {props.get('source_file', '?')} — {props.get('title', '')} "
                      f"[{props.get('rule_type', '?')}] (score: {score:.3f})")
            elif collection_alias == "reviews":
                print(f"### [{i}] PR #{props.get('pr_number', '?')}: {props.get('pr_title', '')} "
                      f"[{props.get('category', '?')}] (score: {score:.3f})")
                if props.get("file_path"):
                    print(f"File: {props['file_path']} | Reviewer: {props.get('author', '?')}")
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


def store_solution(ticket_id: str, title: str, approach_text: str, project: str) -> None:
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
        collection.data.insert(
            properties={
                "ticket_id": ticket_id,
                "title": title,
                "approach": approach_text,
                "review_notes": "",
                "status": "draft",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            vector=vector,
        )
        print(f"Stored solution for {ticket_id} (status: draft)")
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
    parser.add_argument("--collection", choices=["codebase", "standards", "reviews"],
                        default="codebase", help="Collection to search")
    parser.add_argument("--project", default=os.getenv("AGENTS_PROJECT", "default"),
                        help="Project name")
    parser.add_argument("--rerank", action="store_true",
                        help="Enable cross-encoder re-ranking (more accurate, ~200ms extra)")
    parser.add_argument("--rerank-candidates", type=int, default=20,
                        help="Candidate pool size for re-ranking (default: 20)")
    parser.add_argument("--alpha", type=float, default=0.7,
                        help="Hybrid search weight: 1.0=pure vector, 0.0=pure BM25 (default: 0.7)")

    # Solution management
    parser.add_argument("--store-solution", action="store_true")
    parser.add_argument("--ticket", type=str)
    parser.add_argument("--title", type=str)
    parser.add_argument("--approach-file", type=str)
    parser.add_argument("--approach", type=str)

    parser.add_argument("--get-solution", type=str, metavar="TICKET_ID")
    parser.add_argument("--update-solution", type=str, metavar="TICKET_ID")
    parser.add_argument("--status", choices=["draft", "approved", "rejected"])
    parser.add_argument("--review-notes", type=str)

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
        store_solution(args.ticket, args.title, approach_text, project)
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
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
