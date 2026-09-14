#!/usr/bin/env python3
"""
plot_scores.py — quality against latency, per configuration.

Run after score.py has written eval/scores.csv.

    python tools/plot_scores.py

Writes eval/scores.png. The right-hand panel is the one to look at: anything up
and to the left is strictly better. If the reranked points sit barely above the
plain ones but two seconds to the right, the reranker is not paying for itself.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", default="eval/scores.csv")
    parser.add_argument("--out", default="eval/scores.png")
    args = parser.parse_args()

    source = Path(args.scores)
    if not source.exists():
        raise SystemExit(
            f"{source} not found. Run:\n"
            "  python .agents/skills/corpus-eval/scripts/score.py --csv eval/scores.csv"
        )

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit("matplotlib is missing. pip install matplotlib")

    with source.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    rows.sort(key=lambda r: float(r["mrr@10"]))
    names = [r["config_id"] for r in rows]
    mrr = [float(r["mrr@10"]) for r in rows]
    latency = [float(r["median_ms"]) for r in rows]
    colours = ["#c0392b" if "rerank" in n else "#2c6fa8" for n in names]

    figure, (left, right) = plt.subplots(1, 2, figsize=(13, 5))

    left.barh(names, mrr, color=colours)
    left.set_xlabel("MRR@10")
    left.set_title("Retrieval quality  (red = reranked)")
    left.grid(axis="x", alpha=0.3)

    right.scatter(latency, mrr, c=colours, s=90)
    for name, x, y in zip(names, latency, mrr):
        right.annotate(name, (x, y), fontsize=7, xytext=(5, 4), textcoords="offset points")
    right.set_xlabel("median latency per call (ms)")
    right.set_ylabel("MRR@10")
    right.set_title("Is the reranker worth the wait?")
    right.margins(x=0.22, y=0.12)  # room for the labels
    right.grid(alpha=0.3)

    figure.tight_layout()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(out, dpi=130)
    print(f"Wrote {out}")

    best = max(rows, key=lambda r: float(r["mrr@10"]))
    fastest_good = min(
        (r for r in rows if float(r["mrr@10"]) >= float(best["mrr@10"]) * 0.95),
        key=lambda r: float(r["median_ms"]),
    )
    print(f"\nHighest MRR:     {best['config_id']}  "
          f"({best['mrr@10']} @ {best['median_ms']}ms)")
    print(f"Within 5%, fastest: {fastest_good['config_id']}  "
          f"({fastest_good['mrr@10']} @ {fastest_good['median_ms']}ms)")
    if fastest_good["config_id"] != best["config_id"]:
        print("\nThose differ. That gap is the interesting part of your report.")


if __name__ == "__main__":
    main()
