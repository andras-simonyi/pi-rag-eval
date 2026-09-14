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
    args = parser.parse_args()

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

    previous = config["mcpServers"].get(args.name, {}).get("url")
    config["mcpServers"][args.name] = {"url": endpoint}
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {path}")
    print(f"  {args.name} -> {endpoint}")
    if previous and previous != endpoint:
        print(f"  (was {previous})")
    print(
        "\nIn Pi: /mcp, then reconnect '"
        + args.name
        + "'. If Pi is not running yet, just start it."
    )


if __name__ == "__main__":
    main()
