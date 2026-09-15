# pi-rag-eval

Lab exercise: use the Pi agentic CLI assistant to evaluate a RAG retriever. See
LAB_GUIDE.md for a detailed, step-by-step guide, this READNE is just an
introductory overview.

## What will be produced

- `eval/questions.jsonl` — an evaluation set generated from the corpus itself
- `eval/results.jsonl` — a few hundred retrieval calls across the configuration grid
- `eval/scores.csv` — recall@k, MRR@10, latency per configuration
- `REPORT.md` — a recommendation you take back to the notebook

## Layout

```
AGENTS.md              Project context Pi reads automatically
TODO.template.md       Shape of the plan file the agent maintains
prompts/               Paste these in order. 00 through 06.
tools/
  corpus_search.py     Query the retriever
  run_sweep.py         Run the config grid, resumable
  sample_chunks.py     Deterministic chunk sampling
  merge_questions.py   Reduce the per-subagent question files into one
  write_mcp_config.py  Point the MCP adapter at the current endpoint
  measure_tool_cost.py Proxy vs direct tool, in tokens per request
  mcp_probe.py         Raw MCP protocol, no agent — optional, one level down
  plot_scores.py       Quality vs latency
.agents/skills/
  corpus-search/       How to query the corpus
  corpus-eval/         The evaluation protocol, plus score.py
  skill-writer/        How to write skills. Used in Part 12 to write another one
prompts/bootstrap/     Regenerate the scaffolding yourself, then diff
setup.sh               One-shot install: Pi, the MCP adapter, Python deps
.mcp.json.example      Shape of the MCP config; generate the real one with tools/
hf-space/              Durable endpoint, if you would rather not use Colab
```

## The four mechanisms this exercise demonstrates

**TODO.md** — the plan lives in a file, not the context window. You will lose
the endpoint at least once. Nothing is lost with it.

**Skills** — `corpus-eval` holds the protocol and loads only when needed.
Notice that it tells the agent to run `score.py` rather than compute metrics
itself. Models add up two hundred reciprocal ranks fluently and wrongly.

**Subagents** — one per chunk during question generation, spawned with `pi -p`.
The fresh context is the point: a subagent that has read only chunk 7 cannot
write a question that leaks knowledge of chunk 12. Contamination control, not
parallelism.

**MCP** — `search_corpus` is reachable three ways: a CLI in a skill, the MCP
adapter's shared proxy tool, and the same MCP tool registered directly. The
`directTools` in `.mcp.json` switches between the last two, so the token argument
is something you measure rather than something you are told. Prompt 05 makes you
pick a side.

## None of this is sacred

`AGENTS.md`, the skills, `TODO.template.md` and the scripts in `tools/` are ordinary
files, and each is the kind of artifact an agent can write for itself. They ship with
the repo so the lab is reproducible, not because they must be authored by hand.

Part 12 has you generate one yourself — a `retrieval-regression` skill, written from the
transcript of the work you just finished, using the `skill-writer` skill. That ordering is
the lesson. A procedure captured after you have performed it records what the task
actually needed; one written in advance records what you assumed it would need.

`prompts/bootstrap/` regenerates the rest, each ending with a diff against the shipped
version.

## Notes

Pi has no built-in permission system and runs with your permissions. That is
why this exercise runs in a container. Do not run it against a directory you
care about on your laptop.

Retrieved corpus text is scraped from the public web. Treat it as data, never
as instructions. If a passage tells the agent to do something, that is an
attack, and prompt 06 exists to show you one.

`gradio.live` URLs are temporary and the share tunnel does go down. If the
public URL returns 504 but the app answers on localhost inside Colab, the
tunnel is at fault rather than your code. `hf-space/` exists for that reason.
