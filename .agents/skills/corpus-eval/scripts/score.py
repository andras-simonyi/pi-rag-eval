#!/usr/bin/env python3
"""
score.py — compute retrieval metrics from eval/results.jsonl.

Run this. Do not compute these numbers by reading the results file, and do not
estimate them. Arithmetic over 200 records is exactly the kind of task a
language model does fluently and wrongly.

    python .agents/skills/corpus-eval/scripts/score.py
    python .agents/skills/corpus-eval/scripts/score.py --by-lang
    python .agents/skills/corpus-eval/scripts/score.py --csv eval/scores.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def load(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found. Run tools/run_sweep.py first.")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def gold_rank(record: dict) -> int | None:
    """1-based rank of the gold chunk, or None if it was not retrieved.

    Matches on chunk_id. Deliberately no URL fallback: several chunks can share
    one source page, so a URL hit is not proof the right passage was found and
    would inflate every score.
    """
    gold_id = record.get("gold_chunk_id")
    retrieved = record.get("retrieved") or []
    if gold_id and gold_id in retrieved:
        return retrieved.index(gold_id) + 1
    return None


def summarise(records: list[dict]) -> dict:
    ranks = [gold_rank(r) for r in records]
    hits = [r for r in ranks if r is not None]
    latencies = [r["latency_ms"] for r in records if "latency_ms" in r]
    n = len(records)
    return {
        "n": n,
        "recall@1": sum(1 for r in hits if r <= 1) / n if n else 0.0,
        "recall@3": sum(1 for r in hits if r <= 3) / n if n else 0.0,
        "recall@5": sum(1 for r in hits if r <= 5) / n if n else 0.0,
        "recall@10": sum(1 for r in hits if r <= 10) / n if n else 0.0,
        "mrr@10": sum(1.0 / r for r in hits if r <= 10) / n if n else 0.0,
        "median_ms": statistics.median(latencies) if latencies else 0,
        "p90_ms": (
            sorted(latencies)[int(len(latencies) * 0.9) - 1] if latencies else 0
        ),
    }


COLUMNS = [
    "config_id",
    "n",
    "recall@1",
    "recall@3",
    "recall@5",
    "recall@10",
    "mrr@10",
    "median_ms",
    "p90_ms",
]


def to_row(config_id: str, stats: dict) -> dict:
    row = {"config_id": config_id}
    for key in COLUMNS[1:]:
        value = stats[key]
        row[key] = round(value, 3) if isinstance(value, float) else value
    return row


def print_table(rows: list[dict]) -> None:
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in COLUMNS}
    header = " | ".join(c.ljust(widths[c]) for c in COLUMNS)
    print(header)
    print("-|-".join("-" * widths[c] for c in COLUMNS))
    for row in rows:
        print(" | ".join(str(row[c]).ljust(widths[c]) for c in COLUMNS))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="eval/results.jsonl")
    parser.add_argument("--csv", default="", help="Also write a CSV here.")
    parser.add_argument(
        "--by-lang",
        action="store_true",
        help="Break every config down by question language.",
    )
    args = parser.parse_args()

    records = load(Path(args.results))

    # Every score is computed by matching gold_chunk_id against the retrieved
    # ids. With no ids present, the whole table reads 0.0 and looks like a
    # catastrophic retrieval result rather than a broken endpoint. Abort before
    # printing anything misleading.
    if not any(
        identifier
        for record in records
        for identifier in (record.get("retrieved") or [])
    ):
        sys.exit(
            "No chunk ids in eval/results.jsonl — the retrieval endpoint returned no "
            "chunk_id values.\n"
            "Nothing can be scored, and a table of zeros here would be misleading.\n"
            "This is an endpoint problem: raise it rather than working around it."
        )

    grouped: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        key = record["config_id"]
        if args.by_lang:
            key = f"{key}::{record.get('lang', '?')}"
        grouped[key].append(record)

    rows = [to_row(key, summarise(items)) for key, items in sorted(grouped.items())]
    rows.sort(key=lambda r: r["mrr@10"], reverse=True)

    print_table(rows)

    missing = sum(1 for r in records if gold_rank(r) is None)
    print(
        f"\n{len(records)} records, "
        f"{len({r['question_id'] for r in records})} questions, "
        f"{len({r['config_id'] for r in records})} configs."
    )
    print(f"Gold chunk not in top-10 for {missing} records ({missing / len(records):.1%}).")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
