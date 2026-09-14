# Prompt 02 — build the evaluation set (25 min)

Purpose: the subagent phase. This is where students watch context isolation
happen. Have them run `htop` or watch the process list in a second terminal.

---

Execute phase 1 of the plan.

Sample 20 chunks with seed 42, then generate the question pairs. One subagent
per chunk, at most 4 running at once, each using prompts/subagent-question.md.
Do not generate questions in your own context.

When all subagents are done, run the validation subagent. Show me its verdict
before continuing, and update TODO.md.
