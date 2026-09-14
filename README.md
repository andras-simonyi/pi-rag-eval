# pi-rag-eval

Lab exercise: use an agentic CLI assistant to evaluate the RAG retriever you
built in the previous lab, and decide what settings it should ship with.

In the RAG lab, section 19 compared four retrieval pipelines on one question
you picked by hand. Here you do it properly — twenty questions, ten
configurations, two languages, real metrics — and the agent does the work.

## What you will produce

- `eval/questions.jsonl` — an evaluation set generated from the corpus itself
- `eval/results.jsonl` — 200 retrieval calls across the configuration grid
- `eval/scores.csv` — recall@k, MRR@10, latency per configuration
- `REPORT.md` — a recommendation you take back to the notebook

## Setup

**1. Start the environment.** Create a **Blank** Codespace at github.com/codespaces,
then:

```bash
git clone https://github.com/YOUR-INSTRUCTOR/pi-rag-eval.git
cd pi-rag-eval
./setup.sh
```

`setup.sh` checks Node, installs Pi from `@earendil-works/pi-coding-agent`,
installs `pi-mcp-adapter`, and installs the Python dependencies. A blank Codespace
has no repository behind it, so nothing is backed up — push your work before you
finish.

Pi's official npm package is `@earendil-works/pi-coding-agent`. The older
`@mariozechner/pi-coding-agent` is deprecated and frozen below the version the MCP
adapter requires; the adapter names the official package as a peer dependency, so
installing the wrong one fails at startup with `Cannot find module
'@earendil-works/pi-coding-agent'`. `setup.sh` removes the deprecated packages first.

**2. Start the corpus endpoint.** Run the RAG lab notebook in Colab through the
launch cell. Copy the public URL it prints — the app URL, not the MCP one:

```bash
export CORPUS_URL="https://xxxxxxxxxxxx.gradio.live"
```

Leave the Colab runtime running for the whole session. If it dies, relaunch and
re-export — the URL will be different.

Check it works:

```bash
python tools/corpus_search.py "dagasztógép"
```

**3. Get a local copy of the corpus.** Question generation needs the chunk text
locally. In Colab:

```python
from google.colab import files
files.download(str(CHUNKS_PATH))
```

Drag the downloaded `chunks.jsonl` into `data/` in your Codespace.

**4. Start Pi.**

```bash
pi
```

Then work through `prompts/00-orientation.md` onward, pasting one at a time.

## Layout

```
AGENTS.md              Project context Pi reads automatically
TODO.template.md       Shape of the plan file the agent maintains
prompts/               Paste these in order. 00 through 06.
tools/
  corpus_search.py     Query the retriever
  run_sweep.py         Run the config grid, resumable
  sample_chunks.py     Deterministic chunk sampling
  write_mcp_config.py  Point the MCP adapter at the current endpoint
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
instructor/            Runbook, timings, the poisoned chunk
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
adapter's `/mcp` panel toggles between the last two, so the token argument is
something you measure rather than something you are told. Prompt 05 makes you
pick a side.

## Nothing here was handed down

`AGENTS.md`, the skills, `TODO.template.md` and the scripts in `tools/` were all generated
by Pi and then reviewed. They ship with the repo so the lab is reproducible, not because
they are the kind of thing you write by hand.

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
