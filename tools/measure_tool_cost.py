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


TOKEN_FIELDS = {
    "input_tokens": "input",
    "inputTokens": "input",
    "prompt_tokens": "input",
    "cache_read_input_tokens": "cache_read",
    "cacheRead": "cache_read",
    "cacheReadInputTokens": "cache_read",
    "cache_creation_input_tokens": "cache_write",
    "cacheWrite": "cache_write",
    "cacheWriteInputTokens": "cache_write",
}


def collect_tokens(blob, found: dict[str, int] | None = None) -> dict[str, int]:
    """Gather every token field in an event.

    The `input` field counts only NON-CACHED input. Once prompt caching is
    warm, the tool schema moves into cache_read and an input-only measurement
    collapses to nothing. Context size is input + cache_read + cache_write, so
    all three have to be summed or the comparison is meaningless.
    """
    found = {} if found is None else found
    if isinstance(blob, dict):
        for key, value in blob.items():
            if key in TOKEN_FIELDS and isinstance(value, int):
                found[TOKEN_FIELDS[key]] = found.get(TOKEN_FIELDS[key], 0) + value
            else:
                collect_tokens(value, found)
    elif isinstance(blob, list):
        for item in blob:
            collect_tokens(item, found)
    return found


def run_once(timeout: int) -> tuple[dict[str, int] | None, str]:
    """One Pi turn in json mode. Returns (token breakdown, raw output)."""
    result = subprocess.run(
        ["pi", "--mode", "json", "-p", PROMPT],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    raw = result.stdout
    totals: dict[str, int] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        found = collect_tokens(event)
        # Keep the event with the largest input figure: the final usage report.
        if found.get("input", 0) + found.get("cache_read", 0) > totals.get(
            "input", 0
        ) + totals.get("cache_read", 0):
            totals = found
    if not totals:
        return None, raw + result.stderr
    return totals, raw


def context_size(totals: dict[str, int]) -> int:
    """Everything the model was sent, cached or not."""
    return (
        totals.get("input", 0)
        + totals.get("cache_read", 0)
        + totals.get("cache_write", 0)
    )


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

    results: dict[str, list[dict[str, int] | None]] = {"proxy": [], "direct": []}
    try:
        for mode in ("proxy", "direct"):
            set_mode(mode)
            print(f"\n{mode}:")
            for run in range(1, args.runs_per_mode + 1):
                totals, raw = run_once(args.timeout)
                if totals is None:
                    print(f"  run {run}: no token counts found in the output")
                    print("  " + "\n  ".join(raw.splitlines()[:6]))
                else:
                    parts = ", ".join(
                        f"{name}={value:,}" for name, value in sorted(totals.items())
                    )
                    print(f"  run {run}: {context_size(totals):,} context tokens ({parts})")
                results[mode].append(totals)
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

    proxy_total, direct_total = context_size(proxy), context_size(direct)

    print("\n" + "-" * 52)
    print(f"{'':<22}{'context':>12}{'of which cached':>18}")
    for label, totals in (("proxy only", proxy), ("direct tool", direct)):
        cached = totals.get("cache_read", 0) + totals.get("cache_write", 0)
        print(f"{label:<22}{context_size(totals):>12,}{cached:>18,}")
    print("-" * 52)
    delta = direct_total - proxy_total
    print(f"{'difference':<22}{delta:>+12,} tokens per request")
    print(
        "\nContext = input + cache_read + cache_write. The input field alone counts\n"
        "only non-cached tokens, so once caching is warm a schema you are paying for\n"
        "shows up as cache_read rather than input."
    )

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
