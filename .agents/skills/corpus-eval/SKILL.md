---
name: corpus-eval
description: >
  Use when evaluating or tuning the Modul-Bake RAG retriever: building an
  evaluation set from corpus chunks, sweeping retrieval configurations,
  computing recall and MRR, or recommending which retrieval settings the
  Gradio app should ship with. Triggers on requests to measure, benchmark,
  compare, or tune retrieval, or to decide whether the reranker is worth it.
---

# Evaluating the Modul-Bake retriever

This skill defines the protocol. Follow it in order. Do not improvise the
metric definitions or the report shape.

## The idea in one paragraph

Every chunk in the corpus can generate a question that only that chunk answers.
That makes the chunk its own gold label — no human annotation, no LLM judge.
Retrieval quality is then just: when we ask that question, how high does the
source chunk rank? Sweep the retrieval settings, measure, pick a winner.

## Phase 1 — build the evaluation set

Sample chunks deterministically:

```bash
python tools/sample_chunks.py --n 20 --seed 42
```

This writes `eval/chunks/chunk_01.md` … `chunk_20.md` and a manifest.

Now generate one question per chunk **using a subagent per chunk**:

```bash
pi -p --tools read,write \
  "$(cat prompts/subagent-question.md)

FILE: eval/chunks/chunk_07.md
SLOT: 07"
```

The isolation is not an optimisation. A subagent that has read only chunk 7
cannot write a question that quietly depends on chunk 12. If you generate all
twenty questions in one context, they contaminate each other and the evaluation
measures nothing. Do not batch them.

Run at most 4 subagents concurrently.

Each subagent appends one line to `eval/questions.jsonl`:

```json
{"question_id":"q07_hu","gold_chunk_id":"...","gold_url":"...","lang":"hu","question":"..."}
```

Rules for a valid question are in `reference/protocol.md`. Read that file
before generating anything.

**Validate before sweeping.** Spawn one more subagent with a fresh context to
check a random 5 of the questions against their chunks. If it rejects more than
one, fix the generation prompt and regenerate — do not proceed with a broken
eval set. A bad eval set produces confident numbers about nothing.

## Phase 2 — run the sweep

This is 200 mechanical calls. Do not make them one at a time from your own
context; that wastes tokens and takes an hour.

```bash
python tools/run_sweep.py --top-k 10 --concurrency 3
```

The script is resumable. If the Colab endpoint dies mid-sweep, restart it,
re-export `CORPUS_URL`, and run the same command — finished work is skipped.

## Phase 3 — score

```bash
python .agents/skills/corpus-eval/scripts/score.py --csv eval/scores.csv
python .agents/skills/corpus-eval/scripts/score.py --by-lang
```

Run the script. Do not compute recall or MRR yourself by reading
`results.jsonl`, and do not estimate them from a sample. If you need a number
that the script does not produce, extend the script.

## Phase 4 — report

Write `REPORT.md` using the structure in `reference/protocol.md`. It must end
with a concrete recommendation: the exact `mode`, `alpha`, `rerank` and `top_k`
values to set as defaults in the notebook's Gradio controls, and the measured
cost of that choice in median latency.

State the limitations honestly. Twenty questions is a small eval set; a 0.02
difference in MRR between two configs is not a result. Say so when it applies.

## Progress tracking

Maintain `TODO.md` in the repo root from the start. Twenty questions across
four phases will not survive in context, and the endpoint will probably drop at
least once. See `TODO.template.md` for the expected shape.
