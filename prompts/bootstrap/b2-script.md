# Bootstrap 2 — generate the sweep script

Run before Part 6, in a copy of the repo with the script moved aside:

    mv tools/run_sweep.py tools/run_sweep.shipped.py

---

I need to run every question in eval/questions.jsonl through every retrieval
configuration we care about, and record where the gold chunk ranked.

Do not make these calls yourself — there are several hundred of them. Write a
script.

Before you write anything, read tools/corpus_search.py so you reuse it rather
than reimplementing the endpoint call, and read the corpus-eval skill's
reference/protocol.md for the configuration grid and what the records must
contain.

Two requirements from experience:

- The endpoint dies. The script must be safe to kill and re-run without
  redoing finished work or corrupting the output.
- The reranker is slow and the backend is a free tier. Make concurrency a
  flag, and pick a conservative default.

When it runs, diff it against tools/run_sweep.shipped.py and tell me what each
version does better.
