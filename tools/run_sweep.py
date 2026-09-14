#!/usr/bin/env python3
"""
run_sweep.py — run every question through every retrieval configuration.

Reads  eval/questions.jsonl
Writes eval/results.jsonl  (one record per question x config)

Resumable: records already present in the output file are skipped, so you can
kill this mid-run, restart the Colab endpoint, and run it again.

    python tools/run_sweep.py --top-k 10 --concurrency 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus_search import _client, search  # noqa: E402

# The configuration grid. Alpha is only meaningful for hybrid, so the keyword
# and vector rows pin it to a fixed value to keep config_id stable.
GRID = [
    {"config_id": "keyword_plain", "mode": "keyword", "alpha": 0.5, "rerank": False},
    {"config_id": "keyword_rerank", "mode": "keyword", "alpha": 0.5, "rerank": True},
    {"config_id": "vector_plain", "mode": "vector", "alpha": 0.5, "rerank": False},
    {"config_id": "vector_rerank", "mode": "vector", "alpha": 0.5, "rerank": True},
    {"config_id": "hybrid_a25_plain", "mode": "hybrid", "alpha": 0.25, "rerank": False},
    {"config_id": "hybrid_a50_plain", "mode": "hybrid", "alpha": 0.50, "rerank": False},
    {"config_id": "hybrid_a75_plain", "mode": "hybrid", "alpha": 0.75, "rerank": False},
    {"config_id": "hybrid_a25_rerank", "mode": "hybrid", "alpha": 0.25, "rerank": True},
    {"config_id": "hybrid_a50_rerank", "mode": "hybrid", "alpha": 0.50, "rerank": True},
    {"config_id": "hybrid_a75_rerank", "mode": "hybrid", "alpha": 0.75, "rerank": True},
]

WRITE_LOCK = threading.Lock()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def retrieved_ids(results: list[dict]) -> list[str]:
    """Chunk ids of the retrieved passages, in rank order."""
    return [item.get("chunk_id") or "" for item in results]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", default="eval/questions.jsonl")
    parser.add_argument("--out", default="eval/results.jsonl")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="Cap questions, 0 = all.")
    parser.add_argument("--url", default=os.environ.get("CORPUS_URL", ""))
    args = parser.parse_args()

    if not args.url:
        sys.exit('No corpus URL. export CORPUS_URL="https://xxxx.gradio.live"')

    all_records = load_jsonl(Path(args.questions))

    # Phase 1 writes a skip record for any chunk that could not support a valid
    # question (navigation boilerplate, contact blocks, bare tables of
    # contents). Those are not questions and have no question_id.
    skipped = [r for r in all_records if r.get("status") == "skip"]
    questions = [
        r for r in all_records
        if r.get("status") != "skip" and r.get("question_id") and r.get("question")
    ]
    malformed = len(all_records) - len(skipped) - len(questions)

    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        sys.exit(
            f"No usable questions in {args.questions} "
            f"({len(skipped)} skip records, {malformed} malformed). Run phase 1 first."
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {
        (record["question_id"], record["config_id"])
        for record in load_jsonl(out_path)
    }

    jobs = [
        (question, config)
        for question in questions
        for config in GRID
        if (question["question_id"], config["config_id"]) not in done
    ]

    # Show the arithmetic. There is no single "correct" total: it depends on how
    # many sampled chunks survived phase 1 and whether both language variants
    # were generated for each.
    languages = Counter(q.get("lang", "?") for q in questions)
    slots = len({q.get("slot") for q in questions})
    total = len(questions) * len(GRID)

    print(
        f"{len(questions)} questions from {slots} chunks "
        f"({', '.join(f'{n} {lang}' for lang, n in sorted(languages.items()))})"
    )
    if skipped:
        print(f"{len(skipped)} chunks skipped in phase 1:")
        for record in skipped:
            print(f"    {record.get('slot', '??')}: {record.get('reason', 'no reason given')}")
    if malformed:
        print(f"WARNING: {malformed} records were neither a question nor a skip.")
    if len(languages) == 1:
        print(
            "NOTE: only one language present. The protocol asks for a Hungarian and an\n"
            "      English question per chunk — the cross-lingual comparison is the\n"
            "      sharpest result in this evaluation and you will not get it this way."
        )
    print(
        f"\n{len(questions)} questions x {len(GRID)} configs = {total} calls. "
        f"{len(done)} already done, {len(jobs)} to run."
    )
    if not jobs:
        print("Nothing to do.")
        return

    # One client shared across threads; gradio_client is safe for concurrent
    # predicts against a queued app, and this avoids a handshake per call.
    client = _client(args.url)
    completed = 0
    failed = 0

    def run_one(job):
        question, config = job
        payload = search(
            url=args.url,
            query=question["question"],
            mode=config["mode"],
            top_k=args.top_k,
            alpha=config["alpha"],
            rerank=config["rerank"],
            client=client,
        )
        return {
            "question_id": question["question_id"],
            "config_id": config["config_id"],
            "lang": question.get("lang", ""),
            "gold_chunk_id": question["gold_chunk_id"],
            "gold_url": question.get("gold_url", ""),
            "retrieved": retrieved_ids(payload["results"]),
            "retrieved_urls": [r.get("url", "") for r in payload["results"]],
            "latency_ms": payload["latency_ms"],
        }

    with out_path.open("a", encoding="utf-8") as handle:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(run_one, job): job for job in jobs}
            for future in as_completed(futures):
                question, config = futures[future]
                try:
                    record = future.result()
                except Exception as exc:  # noqa: BLE001
                    failed += 1
                    print(
                        f"  FAIL {question['question_id']}/{config['config_id']}: "
                        f"{type(exc).__name__}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                with WRITE_LOCK:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    handle.flush()
                completed += 1
                if completed % 10 == 0:
                    print(f"  {completed}/{len(jobs)}")

    print(f"Done. {completed} written, {failed} failed. -> {out_path}")
    if failed:
        print("Re-run this command to retry the failures; finished work is skipped.")


if __name__ == "__main__":
    main()
