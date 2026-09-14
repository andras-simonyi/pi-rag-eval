Execute phase 1 of the plan.

Sample 20 chunks with seed 42, then generate the question pairs. One subagent
per chunk, at most 4 running at once, each using prompts/subagent-question.md.
Do not generate questions in your own context.

When all subagents are done, run the validation subagent. Show me its verdict
before continuing, and update TODO.md.
