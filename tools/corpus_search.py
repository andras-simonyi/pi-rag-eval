#!/usr/bin/env python3
"""
corpus-search — query the Modul-Bake RAG retriever.

Wraps the `search_corpus` endpoint exposed by the Gradio app built in the
RAG lab notebook. Reads the app URL from CORPUS_URL.

Examples
--------
    corpus-search "dagasztógép kapacitás"
    corpus-search "dough mixer capacity" --mode vector --no-rerank
    corpus-search "sütőipari kemence" --mode hybrid --alpha 0.75 --top-k 10 --format json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

DEFAULT_TIMEOUT = 120


def _client(url: str):
    try:
        from gradio_client import Client
    except ImportError:
        sys.exit(
            "gradio_client is not installed. Run:\n"
            "  pip install -r tools/requirements.txt"
        )
    try:
        return Client(url, verbose=False)
    except Exception as exc:  # noqa: BLE001
        sys.exit(
            f"Could not reach the Gradio app at {url}\n"
            f"  {type(exc).__name__}: {exc}\n"
            "Check that the Colab runtime is alive and CORPUS_URL is current."
        )


# The endpoint returns blocks separated by '---'. Each block looks like:
#   RESULT 1
#   CHUNK_ID: abc123        <- only if the notebook patch was applied
#   TITLE: ...
#   SECTION: ...
#   URL: https://...
#   TEXT:
#   ...body...
_FIELD = re.compile(r"^(RESULT|CHUNK_ID|TITLE|SECTION|URL)[: ]\s*(.*)$")


def parse_blocks(raw: str) -> list[dict]:
    """Turn the endpoint's text payload into structured records."""
    results = []
    for block in raw.split("\n---\n"):
        block = block.strip()
        if not block:
            continue
        record: dict[str, object] = {
            "rank": None,
            "chunk_id": None,
            "title": "",
            "section": "",
            "url": "",
            "text": "",
        }
        lines = block.splitlines()
        text_start = None
        for i, line in enumerate(lines):
            if line.strip() == "TEXT:":
                text_start = i + 1
                break
            match = _FIELD.match(line.strip())
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if key == "RESULT":
                record["rank"] = int(value) if value.isdigit() else None
            elif key == "CHUNK_ID":
                record["chunk_id"] = value or None
            else:
                record[key.lower()] = value
        if text_start is not None:
            record["text"] = "\n".join(lines[text_start:]).strip()
        results.append(record)
    return results


def search(
    url: str,
    query: str,
    mode: str = "hybrid",
    top_k: int = 6,
    alpha: float = 0.5,
    rerank: bool = True,
    client=None,
) -> dict:
    """Call the endpoint once. Returns parsed results plus wall-clock latency."""
    client = client or _client(url)
    started = time.perf_counter()
    raw = client.predict(
        query=query,
        mode=mode,
        top_k=int(top_k),
        alpha=float(alpha),
        rerank=bool(rerank),
        api_name="/search_corpus",
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    return {
        "query": query,
        "config": {
            "mode": mode,
            "top_k": top_k,
            "alpha": alpha,
            "rerank": rerank,
        },
        "latency_ms": elapsed_ms,
        "results": parse_blocks(raw or ""),
    }


def render_text(payload: dict) -> str:
    """Compact human/agent readable rendering. Keeps token use modest."""
    lines = []
    cfg = payload["config"]
    lines.append(
        f"# {len(payload['results'])} results | mode={cfg['mode']} "
        f"alpha={cfg['alpha']} rerank={cfg['rerank']} | {payload['latency_ms']}ms"
    )
    for item in payload["results"]:
        lines.append("")
        head = f"[{item['rank']}] {item['title']}"
        if item["section"]:
            head += f" — {item['section']}"
        lines.append(head)
        if item["chunk_id"]:
            lines.append(f"    chunk_id: {item['chunk_id']}")
        lines.append(f"    url: {item['url']}")
        body = " ".join(item["text"].split())
        lines.append(f"    {body[:400]}{'…' if len(body) > 400 else ''}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="corpus-search",
        description="Query the Modul-Bake RAG retriever.",
    )
    parser.add_argument("query", help="Natural-language search query.")
    parser.add_argument(
        "--mode",
        choices=["keyword", "vector", "hybrid"],
        default="hybrid",
        help="Retrieval method (default: hybrid).",
    )
    parser.add_argument("--top-k", type=int, default=6, help="Passages to return.")
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Hybrid weighting, 0.0=keyword … 1.0=vector. Ignored unless mode=hybrid.",
    )
    rerank_group = parser.add_mutually_exclusive_group()
    rerank_group.add_argument(
        "--rerank", dest="rerank", action="store_true", default=True
    )
    rerank_group.add_argument("--no-rerank", dest="rerank", action="store_false")
    parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("CORPUS_URL", ""),
        help="Gradio app base URL. Defaults to $CORPUS_URL.",
    )
    args = parser.parse_args()

    if not args.url:
        sys.exit(
            "No corpus URL. Set it first:\n"
            '  export CORPUS_URL="https://xxxxxxxx.gradio.live"'
        )

    payload = search(
        url=args.url,
        query=args.query,
        mode=args.mode,
        top_k=args.top_k,
        alpha=args.alpha,
        rerank=args.rerank,
    )

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload))


if __name__ == "__main__":
    main()
