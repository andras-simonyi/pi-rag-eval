#!/usr/bin/env python3
"""
merge_questions.py — combine the per-subagent files into eval/questions.jsonl.

Phase 1 runs subagents concurrently, and each writes only its own file:

    eval/questions/chunk_01.jsonl
    eval/questions/chunk_02.jsonl
    ...

They cannot share one output file. A subagent running with --tools read,write
has no shell, so it appends by rewriting the whole file — read, modify, write.
Two of those overlapping means one subagent's records are silently overwritten.
Disjoint files remove the race entirely; this script does the reduce step.

    python tools/merge_questions.py

Validates every record, reports which sampled chunks are missing, and refuses to
write a merged file if anything is malformed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REQUIRED = ("question_id", "slot", "gold_chunk_id", "lang", "question")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--indir", default="eval/questions")
    parser.add_argument("--out", default="eval/questions.jsonl")
    parser.add_argument("--manifest", default="eval/chunks/manifest.json")
    parser.add_argument(
        "--force", action="store_true", help="Write the merge even if records are bad."
    )
    args = parser.parse_args()

    indir = Path(args.indir)
    if not indir.is_dir():
        sys.exit(
            f"{indir} not found. Phase 1 writes one file per subagent there.\n"
            "If your subagents wrote to eval/questions.jsonl directly, they were "
            "racing each other — check for missing slots before trusting the result."
        )

    files = sorted(indir.glob("chunk_*.jsonl"))
    if not files:
        sys.exit(f"No chunk_*.jsonl files in {indir}.")

    questions, skips, problems = [], [], []
    seen_ids: set[str] = set()

    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"{path.name}:{lineno} not valid JSON ({exc.msg})")
                continue

            if record.get("status") == "skip":
                if not record.get("slot"):
                    problems.append(f"{path.name}:{lineno} skip record without a slot")
                skips.append(record)
                continue

            missing = [field for field in REQUIRED if not record.get(field)]
            if missing:
                problems.append(
                    f"{path.name}:{lineno} missing {', '.join(missing)}"
                )
                continue
            if record["question_id"] in seen_ids:
                problems.append(
                    f"{path.name}:{lineno} duplicate question_id {record['question_id']}"
                )
                continue
            seen_ids.add(record["question_id"])
            questions.append(record)

    # Which sampled chunks produced nothing at all?
    expected = set()
    manifest_path = Path(args.manifest)
    if manifest_path.exists():
        expected = {
            entry["slot"] for entry in json.loads(manifest_path.read_text(encoding="utf-8"))
        }
    accounted = {record.get("slot") for record in questions + skips}
    silent = sorted(expected - accounted) if expected else []

    languages = Counter(record["lang"] for record in questions)
    slots_with_questions = {record["slot"] for record in questions}

    print(f"{len(files)} subagent files")
    print(f"{len(questions)} questions from {len(slots_with_questions)} chunks "
          f"({', '.join(f'{n} {lang}' for lang, n in sorted(languages.items())) or 'none'})")
    print(f"{len(skips)} chunks skipped")

    if silent:
        print(f"\n{len(silent)} sampled chunks produced NOTHING — neither a question "
              f"nor a skip: {', '.join(silent)}")
        print("  Those subagents failed, timed out, or were rate limited. Re-run them.")

    unpaired = sorted(
        slot for slot in slots_with_questions
        if len({r["lang"] for r in questions if r["slot"] == slot}) < 2
    )
    if unpaired:
        print(f"\n{len(unpaired)} chunks have only one language: {', '.join(unpaired)}")
        print("  The protocol asks for a Hungarian and an English question per chunk.")

    if problems:
        print(f"\n{len(problems)} malformed records:")
        for problem in problems[:15]:
            print(f"  {problem}")
        if len(problems) > 15:
            print(f"  … and {len(problems) - 15} more")
        if not args.force:
            sys.exit("\nRefusing to merge. Fix these, or re-run with --force.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in questions + skips:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nWrote {out}: {len(questions)} questions + {len(skips)} skips")
    print(f"Sweep will make {len(questions)} x 10 = {len(questions) * 10} calls.")


if __name__ == "__main__":
    main()
