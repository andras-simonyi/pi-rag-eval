#!/usr/bin/env python3
"""
sample_chunks.py — draw a reproducible sample of corpus chunks.

Writes one file per sampled chunk into eval/chunks/, so that each
question-generating subagent can be handed exactly one chunk and nothing else.
That isolation is the point: a subagent that has only seen chunk 7 cannot
write a question that leaks knowledge of chunk 12.

    python tools/sample_chunks.py --n 20 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

MIN_CHARS = 400  # skip stubs that cannot support a real question


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default="data/chunks.jsonl")
    parser.add_argument("--outdir", default="eval/chunks")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-chars", type=int, default=MIN_CHARS)
    args = parser.parse_args()

    source = Path(args.chunks)
    if not source.exists():
        raise SystemExit(
            f"{source} not found.\n"
            "Download chunks.jsonl from the Colab runtime and put it in data/. "
            "See README.md, step 2."
        )

    with source.open(encoding="utf-8") as handle:
        chunks = [json.loads(line) for line in handle if line.strip()]

    eligible = [c for c in chunks if len(c.get("text", "")) >= args.min_chars]
    if len(eligible) < args.n:
        raise SystemExit(
            f"Only {len(eligible)} chunks are at least {args.min_chars} chars; "
            f"asked for {args.n}. Lower --n or --min-chars."
        )

    rng = random.Random(args.seed)
    sample = rng.sample(eligible, args.n)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("chunk_*.md"):
        old.unlink()

    manifest = []
    for index, chunk in enumerate(sample, start=1):
        slot = f"{index:02d}"
        path = outdir / f"chunk_{slot}.md"
        path.write_text(
            f"chunk_id: {chunk['chunk_id']}\n"
            f"title: {chunk.get('title', '')}\n"
            f"section: {chunk.get('section_title', '')}\n"
            f"url: {chunk.get('url', '')}\n"
            f"\n---\n\n"
            f"{chunk['text']}\n",
            encoding="utf-8",
        )
        manifest.append(
            {
                "slot": slot,
                "path": str(path),
                "chunk_id": chunk["chunk_id"],
                "url": chunk.get("url", ""),
                "title": chunk.get("title", ""),
            }
        )

    manifest_path = outdir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Sampled {len(sample)} of {len(eligible)} eligible chunks (seed {args.seed}).")
    print(f"Wrote {outdir}/chunk_01.md … chunk_{len(sample):02d}.md")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
