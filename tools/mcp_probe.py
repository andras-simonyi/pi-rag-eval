#!/usr/bin/env python3
"""
mcp_probe.py — reach the SAME search_corpus function over MCP instead of the
plain Gradio REST API.

This exists for one exercise: compare two access paths to one capability.

    python tools/mcp_probe.py list
    python tools/mcp_probe.py call "dagasztógép kapacitás" --mode hybrid

`list` prints the tool schema the server advertises, and the number of tokens
that schema would occupy if it were injected into every model request. That
number is the whole argument, so look at it.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys


def mcp_url() -> str:
    base = os.environ.get("CORPUS_URL", "").rstrip("/")
    if not base:
        sys.exit('No corpus URL. export CORPUS_URL="https://xxxx.gradio.live"')
    return f"{base}/gradio_api/mcp/"


def rough_tokens(text: str) -> int:
    """Crude but honest estimate: ~4 chars per token for JSON-ish English."""
    return max(1, len(text) // 4)


async def do_list() -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(mcp_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            schema_blob = json.dumps(
                [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema,
                    }
                    for tool in tools.tools
                ],
                ensure_ascii=False,
            )

            for tool in tools.tools:
                print(f"\n=== {tool.name} ===")
                print((tool.description or "").strip())
                print(json.dumps(tool.inputSchema, indent=2, ensure_ascii=False))

            print(f"\n---\nTools advertised: {len(tools.tools)}")
            print(f"Schema size:      {len(schema_blob)} chars")
            print(f"Estimated cost:   ~{rough_tokens(schema_blob)} tokens per request")
            print(
                "\nCompare against .agents/skills/corpus-search/SKILL.md, which is\n"
                "loaded only when the agent decides it needs the corpus."
            )


async def do_call(args: argparse.Namespace) -> None:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(mcp_url()) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "search_corpus",
                {
                    "query": args.query,
                    "mode": args.mode,
                    "top_k": args.top_k,
                    "alpha": args.alpha,
                    "rerank": args.rerank,
                },
            )
            for block in result.content:
                print(getattr(block, "text", block))


def main() -> None:
    parser = argparse.ArgumentParser(prog="mcp-probe")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List tools and show the schema token cost.")

    call = sub.add_parser("call", help="Invoke search_corpus over MCP.")
    call.add_argument("query")
    call.add_argument("--mode", default="hybrid", choices=["keyword", "vector", "hybrid"])
    call.add_argument("--top-k", type=int, default=6)
    call.add_argument("--alpha", type=float, default=0.5)
    call.add_argument("--rerank", action="store_true", default=True)
    call.add_argument("--no-rerank", dest="rerank", action="store_false")

    args = parser.parse_args()

    try:
        import mcp  # noqa: F401
    except ImportError:
        sys.exit("The mcp package is missing. pip install -r tools/requirements.txt")

    if args.command == "list":
        asyncio.run(do_list())
    else:
        asyncio.run(do_call(args))


if __name__ == "__main__":
    main()
