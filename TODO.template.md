# TODO — retrieval evaluation

Copy this to `TODO.md` and keep it current. This file is the plan of record.
The context window is not.

Status markers: `[ ]` pending, `[~]` in progress, `[x]` done, `[!]` blocked.

## Setup
- [ ] CORPUS_URL set and endpoint responding
- [ ] data/chunks.jsonl present locally
- [ ] chunk_id appears in search results
- [ ] Estimated total endpoint calls: ___  (= 2 x surviving chunks x 10)

## Phase 1 — evaluation set
- [ ] Sample 20 chunks, seed 42
- [ ] chunk_01 … chunk_20 question pairs generated (one subagent each)
  - [ ] 01  - [ ] 02  - [ ] 03  - [ ] 04  - [ ] 05
  - [ ] 06  - [ ] 07  - [ ] 08  - [ ] 09  - [ ] 10
  - [ ] 11  - [ ] 12  - [ ] 13  - [ ] 14  - [ ] 15
  - [ ] 16  - [ ] 17  - [ ] 18  - [ ] 19  - [ ] 20
- [ ] Skipped chunks recorded with reasons: ___
- [ ] Validation subagent run — verdict: ___

## Phase 2 — sweep
- [ ] run_sweep.py started
- [ ] All question x config records present in eval/results.jsonl
- [ ] Failures retried: ___
- [ ] Wall-clock time: ___

## Phase 3 — scoring
- [ ] score.py run, eval/scores.csv written
- [ ] --by-lang breakdown captured

## Phase 4 — report
- [ ] REPORT.md written
- [ ] Reranker verdict: MRR delta ___ / latency delta ___ / worth it: ___
- [ ] Cross-lingual finding recorded
- [ ] Recommended defaults: mode=___ alpha=___ rerank=___ top_k=___

## Notes and interruptions

Record anything that broke and how far you got, so the next session can resume:
