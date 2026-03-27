#!/usr/bin/env python3
"""
update_pr_kb.py — Index PR review comments into Weaviate ReviewPatterns collection.

Requires: gh (GitHub CLI) authenticated.

Usage:
  python update_pr_kb.py --project myapp
  python update_pr_kb.py --project myapp --limit 100 --include-open
  python update_pr_kb.py --project myapp --since 2024-01-01
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import weaviate
import weaviate.classes as wvc
from fastembed import TextEmbedding

WEAVIATE_URL = os.getenv("AGENTS_WEAVIATE_URL", "http://localhost:8090")
EMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
MIN_COMMENT_LENGTH = 30

_embedder: TextEmbedding | None = None


def get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(EMBED_MODEL_NAME)
    return _embedder


def embed(text: str) -> list[float]:
    return next(get_embedder().embed([text])).tolist()


def get_client() -> weaviate.WeaviateClient:
    port = int(WEAVIATE_URL.rstrip("/").split(":")[-1])
    return weaviate.connect_to_local(host="localhost", port=port, grpc_port=port + 1)


def collection_name(project: str) -> str:
    if not project or project == "default":
        return "ReviewPatterns"
    safe = "".join(c if c.isalnum() else "_" for c in project)
    return f"ReviewPatterns_{safe}"


CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "security":     ["token", "password", "secret", "auth", "xss", "injection", "csrf",
                     "sanitize", "escape", "vulnerability", "expose", "sensitive"],
    "performance":  ["n+1", "index", "slow", "cache", "query", "memory", "loop",
                     "batch", "optimize", "eager", "lazy", "performance", "latency"],
    "testing":      ["test", "coverage", "mock", "assert", "spec", "edge case", "fixture",
                     "unit test", "integration", "jest", "vitest", "playwright"],
    "correctness":  ["bug", "wrong", "incorrect", "undefined", "null", "crash", "error",
                     "exception", "fail", "broken", "off-by-one", "race condition"],
    "architecture": ["pattern", "structure", "module", "dependency", "coupling", "layer",
                     "service", "controller", "separation", "solid", "dry", "single responsibility"],
    "style":        ["naming", "format", "lint", "convention", "readability", "consistent",
                     "camelCase", "snake_case", "indentation", "whitespace"],
}


def categorize_comment(comment: str) -> str:
    lower = comment.lower()
    scores: dict[str, int] = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        scores[cat] = sum(1 for kw in keywords if kw in lower)
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "general"


def get_repo_info() -> tuple[str, str]:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "owner,name"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("Could not get repo info. Run from a git repo with gh configured.")
        print(result.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    return data["owner"]["login"], data["name"]


def fetch_prs(owner: str, repo: str, limit: int, include_open: bool, since: str | None) -> list[dict]:
    states = ["merged"]
    if include_open:
        states.append("open")

    prs = []
    for state in states:
        cmd = [
            "gh", "pr", "list",
            "--repo", f"{owner}/{repo}",
            "--state", state,
            "--limit", str(limit),
            "--json", "number,title,mergedAt,updatedAt",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"gh pr list failed: {result.stderr}")
            continue
        data = json.loads(result.stdout)
        if since:
            data = [
                pr for pr in data
                if (pr.get("mergedAt") or pr.get("updatedAt") or "") >= since
            ]
        prs.extend(data)

    return prs


def fetch_pr_comments(owner: str, repo: str, pr_number: int) -> list[dict]:
    cmd = [
        "gh", "api",
        f"/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        "--paginate",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def index_pr_comments(
    client: weaviate.WeaviateClient,
    owner: str,
    repo: str,
    prs: list[dict],
    project: str,
) -> None:
    coll_name = collection_name(project)
    collection = client.collections.get(coll_name)

    # Load existing pattern IDs to skip duplicates
    existing_ids: set[str] = set()
    try:
        result = collection.query.fetch_objects(limit=100_000, return_properties=["pattern_id"])
        for obj in result.objects:
            pid = obj.properties.get("pattern_id", "")
            if pid:
                existing_ids.add(pid)
    except Exception:
        pass

    added = skipped_dup = skipped_short = 0

    for pr in prs:
        pr_number = pr["number"]
        pr_title = pr.get("title", "")
        print(f"  PR #{pr_number}: {pr_title[:60]}...", end="\r")

        comments = fetch_pr_comments(owner, repo, pr_number)
        for i, comment in enumerate(comments):
            body = comment.get("body", "").strip()
            if not body or len(body) < MIN_COMMENT_LENGTH:
                skipped_short += 1
                continue

            # Skip trivial comments
            trivial = {"lgtm", "looks good", "nice", "thanks", "👍", "+1", "approved"}
            if body.lower() in trivial:
                skipped_short += 1
                continue

            pattern_id = f"PR_{pr_number}::comment_{i}"
            if pattern_id in existing_ids:
                skipped_dup += 1
                continue

            file_path = comment.get("path", "")
            author = comment.get("user", {}).get("login", "")
            created_at = comment.get("created_at", datetime.now(timezone.utc).isoformat())
            category = categorize_comment(body)

            embed_text = f"Reviewed: {file_path}\nComment: {body}"
            vector = embed(embed_text)

            try:
                collection.data.insert(
                    properties={
                        "pattern_id": pattern_id,
                        "pr_number": pr_number,
                        "pr_title": pr_title,
                        "file_path": file_path,
                        "comment": body,
                        "category": category,
                        "author": author,
                        "created_at": created_at,
                    },
                    vector=vector,
                )
                added += 1
                existing_ids.add(pattern_id)
            except Exception as e:
                print(f"\n  Failed to insert comment: {e}")

    print(f"\nReview Patterns [{coll_name}]: added={added}, skipped_dup={skipped_dup}, skipped_short={skipped_short}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index PR review comments into Weaviate")
    parser.add_argument("--project", default=os.getenv("AGENTS_PROJECT", "default"))
    parser.add_argument("--limit", type=int, default=50, help="Number of PRs to process")
    parser.add_argument("--include-open", action="store_true", help="Include open PRs too")
    parser.add_argument("--since", type=str, help="Only process PRs updated after YYYY-MM-DD")
    parser.add_argument("--owner", type=str, help="GitHub owner (auto-detected from git remote)")
    parser.add_argument("--repo", type=str, help="GitHub repo (auto-detected from git remote)")
    args = parser.parse_args()

    # Verify gh is available
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if result.returncode != 0:
        print("GitHub CLI not authenticated. Run: gh auth login")
        sys.exit(1)

    if args.owner and args.repo:
        owner, repo = args.owner, args.repo
    else:
        owner, repo = get_repo_info()

    print(f"Indexing PR comments from {owner}/{repo}")
    print(f"Fetching {args.limit} PRs...")

    prs = fetch_prs(owner, repo, args.limit, args.include_open, args.since)
    print(f"Found {len(prs)} PRs to process")

    if not prs:
        print("No PRs found.")
        return

    client = get_client()
    try:
        index_pr_comments(client, owner, repo, prs, args.project)
    finally:
        client.close()


if __name__ == "__main__":
    main()
