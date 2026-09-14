#!/usr/bin/env python3
"""
write_mcp_config.py — point the MCP adapter at your running corpus endpoint.

    export CORPUS_URL="https://xxxx.gradio.live"
    python tools/write_mcp_config.py

Writes .mcp.json in the repo root. That is the standard project-local MCP
config file, so the adapter picks it up with no further setup. Re-run it every
time the Gradio URL rotates, then reconnect the server from Pi's /mcp panel.

`/mcp setup` inside Pi can scaffold this file interactively instead. This
script exists because the URL changes often enough that typing it into a panel
gets old.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.environ.get("CORPUS_URL", ""))
    parser.add_argument("--name", default="corpus", help="Server name shown in /mcp.")
    parser.add_argument("--out", default=".mcp.json")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Promote search_corpus to a direct tool (full schema in every request).",
    )
    parser.add_argument(
        "--proxy",
        action="store_true",
        help="Return search_corpus to proxy-only access. The default.",
    )
    args = parser.parse_args()

    if args.direct and args.proxy:
        sys.exit("--direct and --proxy are mutually exclusive.")

    base = args.url.strip().rstrip("/")
    if not base:
        sys.exit('No URL. export CORPUS_URL="https://xxxx.gradio.live" first.')
    if base.endswith("/gradio_api/mcp"):
        base = base[: -len("/gradio_api/mcp")]
    if not base.startswith("https://"):
        sys.exit(f"Expected an https:// URL, got: {base}")

    endpoint = f"{base}/gradio_api/mcp/"
    path = Path(args.out)

    # Preserve any other servers already configured.
    config = {"mcpServers": {}}
    if path.exists():
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            config.setdefault("mcpServers", {})
        except json.JSONDecodeError:
            print(f"{path} was not valid JSON; replacing it.")
            config = {"mcpServers": {}}

    previous = config["mcpServers"].get(args.name, {})
    previous_url = previous.get("url")
    entry: dict[str, object] = {"url": endpoint}

    # Keep whatever directTools setting was there unless asked to change it.
    if args.direct:
        entry["directTools"] = ["search_corpus"]
    elif not args.proxy and "directTools" in previous:
        entry["directTools"] = previous["directTools"]

    config["mcpServers"][args.name] = entry
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    mode = "direct" if "directTools" in entry else "proxy"
    print(f"Wrote {path}")
    print(f"  {args.name} -> {endpoint}")
    print(f"  search_corpus access: {mode}")
    if previous_url and previous_url != endpoint:
        print(f"  (url was {previous_url})")

    if args.direct:
        print(
            "\nRestart Pi for this to take effect.\n"
            "On the FIRST restart after adding directTools the metadata cache does not\n"
            "exist yet, so the tool silently falls back to proxy-only while the cache\n"
            "populates. Restart a second time, or run /mcp reconnect "
            f"{args.name} then restart.\n"
            "If your token measurement shows no change, this is why."
        )
    else:
        print(
            "\nIn Pi: /mcp, then reconnect '"
            + args.name
            + "'. If Pi is not running yet, just start it."
        )


if __name__ == "__main__":
    main()
