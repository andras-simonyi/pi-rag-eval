#!/usr/bin/env python3
"""
measure_tool_cost.py — what does an MCP tool cost before you use it?

Runs the same trivial prompt twice: once with search_corpus reachable only
through the adapter's proxy, once registered as a direct tool. The prompt is
the control; .mcp.json is the variable. The difference in input tokens is the
standing charge for having the tool available.

    python tools/measure_tool_cost.py

Restores your original .mcp.json afterwards, including on Ctrl-C.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROMPT = "What is 2+2? Do not use any tools."


def find_input_tokens(blob) -> int | None:
    """Pull input_tokens out of a JSON event, wherever the schema hides it."""
    if isinstance(blob, dict):
        for key, value in blob.items():
            if key in ("input_tokens", "inputTokens", "prompt_tokens") and isinstance(
                value, int
            ):
                return value
            found = find_input_tokens(value)
            if found is not None:
                return found
    elif isinstance(blob, list):
        for item in blob:
            found = find_input_tokens(item)
            if found is not None:
                return found
    return None


def run_once(timeout: int) -> tuple[int | None, str]:
    """One Pi turn in json mode. Returns (input_tokens, raw output)."""
    result = subprocess.run(
        ["pi", "--mode", "json", "-p", PROMPT],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    raw = result.stdout
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        tokens = find_input_tokens(event)
        if tokens is not None:
            return tokens, raw
    return None, raw + result.stderr


def set_mode(mode: str) -> None:
    subprocess.run(
        [sys.executable, "tools/write_mcp_config.py", f"--{mode}"],
        check=True,
        capture_output=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--runs-per-mode",
        type=int,
        default=2,
        help="Direct needs 2: the metadata cache is empty on the first session.",
    )
    args = parser.parse_args()

    config = Path(".mcp.json")
    if not config.exists():
        sys.exit("No .mcp.json. Run: python tools/write_mcp_config.py")
    if not shutil.which("pi"):
        sys.exit("pi is not on PATH.")

    backup = Path(tempfile.mkdtemp()) / "mcp.json.bak"
    shutil.copy2(config, backup)

    results: dict[str, list[int | None]] = {"proxy": [], "direct": []}
    try:
        for mode in ("proxy", "direct"):
            set_mode(mode)
            print(f"\n{mode}:")
            for run in range(1, args.runs_per_mode + 1):
                tokens, raw = run_once(args.timeout)
                if tokens is None:
                    print(f"  run {run}: could not find input_tokens in the output")
                    print("  " + "\n  ".join(raw.splitlines()[:6]))
                else:
                    print(f"  run {run}: {tokens:,} input tokens")
                results[mode].append(tokens)
    except subprocess.TimeoutExpired:
        print("\nTimed out. Is a model configured and reachable?", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
    finally:
        shutil.copy2(backup, config)
        print(f"\nRestored {config} to its original state.")

    # Use the last run of each mode: direct only registers once the cache exists.
    proxy = next((t for t in reversed(results["proxy"]) if t is not None), None)
    direct = next((t for t in reversed(results["direct"]) if t is not None), None)

    if proxy is None or direct is None:
        sys.exit("\nNot enough measurements to compare.")

    print("\n" + "-" * 46)
    print(f"{'proxy only':<22}{proxy:>10,} tokens")
    print(f"{'direct tool':<22}{direct:>10,} tokens")
    print("-" * 46)
    delta = direct - proxy
    print(f"{'difference':<22}{delta:>+10,} tokens per request")

    if abs(delta) < 20:
        print(
            "\nEssentially no difference. Almost certainly the metadata cache was still\n"
            "empty, so the tool stayed on proxy in both runs. Start pi, run\n"
            "'/mcp reconnect corpus', exit, and try again."
        )
    else:
        print(
            f"\nThat is the standing charge for one tool, paid on every request whether\n"
            f"or not it is used. A typical desktop setup has six or eight servers with\n"
            f"twenty tools each. At this rate that is roughly {abs(delta) * 100:,} tokens\n"
            f"of tool schema resident in every single message."
        )


if __name__ == "__main__":
    main()
