# Evaluation protocol — details

## What makes a valid generated question

A question is valid when all of these hold:

1. **Answerable from the chunk alone.** Someone holding only this chunk could
   answer it correctly and completely.
2. **Self-contained.** No "this document", "the above section", "the mentioned
   machine". The question must make sense to a person who has never seen the
   corpus. This is the rule that gets broken most often.
3. **Specific enough to be discriminating.** "What does the company sell?"
   matches half the corpus and measures nothing. Anchor on a named product, a
   number, a material, a capacity, a process step.
4. **Natural.** Phrased the way a customer or technician would actually ask,
   not as a quiz item lifted from the text.
5. **Not a verbatim substring.** If the question copies a whole sentence from
   the chunk, BM25 wins trivially and the comparison becomes meaningless.
   Reword. This one matters more than it looks: the entire point of the sweep
   is to separate lexical from semantic retrieval, and copied phrasing
   destroys that.

Reject the chunk if it cannot support a valid question — navigation boilerplate,
a bare table of contents, a contact block. Write a `skip` record instead:

```json
{"slot":"07","status":"skip","reason":"navigation boilerplate, no factual content"}
```

## Language pairs

The corpus is Hungarian. For each chunk generate **two** questions:

- `lang: "hu"` — natural Hungarian
- `lang: "en"` — the same information need expressed in English, not a
  word-for-word translation

Question ids follow `q<slot>_<lang>`, e.g. `q07_hu`, `q07_en`. Both carry the
same `gold_chunk_id`.

The cross-lingual pair is the sharpest instrument in this evaluation. BM25 over
Hungarian text cannot match an English query, so `keyword_*` configs should
collapse on `lang=en` while dense and hybrid hold up. If that pattern does not
appear, something is wrong with the setup — check that the dense vectors were
built from `embedding_text` and that the reranker model is the multilingual
one.

## The configuration grid

Ten configurations, defined in `tools/run_sweep.py`:

| mode | alpha | rerank |
|---|---|---|
| keyword | — | off, on |
| vector | — | off, on |
| hybrid | 0.25, 0.50, 0.75 | off, on |

`alpha` runs from 0.0 (pure keyword) to 1.0 (pure vector) and only affects
hybrid mode. `top_k` is fixed at 10 for the sweep so that MRR@10 is well
defined; it is a separate question from which `top_k` to ship.

## Metrics

- **recall@k** — fraction of questions where the gold chunk appears in the top
  k results.
- **MRR@10** — mean of 1/rank over questions, counting only ranks 1–10, and 0
  when the gold chunk is missing. This is the headline number because it
  rewards putting the right passage first, which is what matters when the top
  passages get fed to a generator.
- **median_ms / p90_ms** — wall-clock latency per retrieval call, measured
  client-side. Includes the network hop to Colab, so treat it as a comparison
  between configurations, not as an absolute.

## Report structure

`REPORT.md`, in this order:

1. **Recommendation** — first, not last. The exact settings to ship, in one
   sentence, with the MRR and latency they buy.
2. **Setup** — corpus size, sample size, seed, date, endpoint type, how many
   questions were skipped and why.
3. **Results table** — the score script's output, all ten configs.
4. **Does the reranker earn its latency?** — compare each `*_plain` against its
   `*_rerank` twin. Report the MRR delta and the latency delta together. A
   reranker that adds 0.04 MRR and 1800 ms may not be worth shipping.
5. **Cross-lingual breakdown** — the `--by-lang` table, with a note on which
   configs degrade on English queries.
6. **Alpha sensitivity** — is hybrid flat across 0.25/0.50/0.75, or is there a
   real optimum? Flat means the parameter is not worth exposing to users.
7. **Limitations** — sample size, single seed, URL-vs-chunk_id matching if the
   notebook patch was not applied, and the fact that retrieval quality is not
   answer quality.
8. **What to change in the notebook** — the specific widget defaults in the
   Gradio Blocks section.

## Anti-patterns

- Reporting a winner on a 0.01 MRR difference across 40 questions.
- Comparing configs on different question sets.
- Letting the reranker score questions it helped generate.
- Computing metrics in prose instead of running `score.py`.
- Deleting `results.jsonl` to "start clean" after a partial failure. It is
  append-only and resumable on purpose.
