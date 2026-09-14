# Subagent brief: validate a sample of generated questions

You are an independent check. You did not generate these questions and you
should not be gentle with them.

## Your task

1. Read `eval/questions.jsonl` (produced by merging the per-subagent files) and
   pick 5 records at random, skipping `status:skip` records.
2. For each one, read the corresponding chunk in `eval/chunks/chunk_<slot>.md`.
3. Judge the question against `.agents/skills/corpus-eval/reference/protocol.md`,
   section "What makes a valid generated question".
4. Write your findings to `eval/validation.md` and print a one-line verdict.

## For each question, report

- **verdict**: pass / fail
- **rule broken**: which numbered rule, if any
- **verbatim overlap**: the longest phrase shared between question and chunk
- **fix**: how you would rewrite it, in one line

## Verdict line

End with exactly one of:

```
VALIDATION PASS — 5/5 usable
VALIDATION MARGINAL — 4/5 usable, see eval/validation.md
VALIDATION FAIL — 3 or fewer usable, regenerate before sweeping
```

Be strict about rule 5 (verbatim overlap) and rule 2 (self-containment). Those
are the two that silently invalidate the whole experiment.
