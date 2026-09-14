# Subagent brief: generate one evaluation question pair

You have been given exactly one corpus chunk. You have not seen any other
chunk, and that is deliberate — your question must depend only on what is in
front of you.

## Your task

1. Read the chunk file named in FILE below.
2. Read `.agents/skills/corpus-eval/reference/protocol.md`, section "What makes
   a valid generated question".
3. Decide whether this chunk can support a valid question at all.
4. If it can, write two questions about the same fact: one in Hungarian
   (`lang: "hu"`), one in English (`lang: "en"`). The English one expresses the
   same information need, not a word-for-word translation.
5. Append your records to `eval/questions.jsonl`, one JSON object per line.
6. Print the records you wrote and stop.

## Record format

```json
{"question_id":"q07_hu","slot":"07","gold_chunk_id":"<from the chunk header>","gold_url":"<from the chunk header>","lang":"hu","question":"..."}
{"question_id":"q07_en","slot":"07","gold_chunk_id":"<same>","gold_url":"<same>","lang":"en","question":"..."}
```

If the chunk cannot support a question, append this instead and stop:

```json
{"slot":"07","status":"skip","reason":"<one short clause>"}
```

## Hard rules

- Do not copy a full sentence from the chunk into the question. Reword. If your
  question shares a long verbatim phrase with the source, keyword retrieval
  wins by accident and the whole evaluation is worthless.
- Do not write "this document", "the section above", "the mentioned machine".
  A reader who has never seen the corpus must be able to understand the question.
- Do not ask something so generic it could match any chunk. Anchor on a name, a
  number, a capacity, a material, a process step.
- Do not read any file under `eval/chunks/` other than your assigned one.
- Do not modify anything except by appending to `eval/questions.jsonl`.
- Output nothing but the records and a one-line note. No preamble.

FILE: <path>
SLOT: <two digits>
