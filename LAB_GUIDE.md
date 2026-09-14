# Lab: evaluating your RAG retriever with an agentic CLI assistant

**Prerequisite:** the Modul-Bake RAG lab notebook, running, with its Gradio app launched.

This is a guide, not a program. Nothing here executes — you read a step, then run it in a
terminal. Keep this notebook open beside your terminal window.

---

In the RAG lab, section 19 compared four retrieval pipelines on **one question you picked
by hand**. That is not an evaluation. It is an anecdote.

In the next two hours an agent will:

- build a 40-question evaluation set from your own corpus,
- sweep 10 retrieval configurations against it,
- compute recall and MRR,
- and tell you which settings your Gradio app should ship with.

You will take that recommendation back to your notebook and change the defaults. That is
the deliverable: a measured decision replacing a guessed one.

Along the way you will use the four things that separate an agent from a chatbot — a plan
that outlives the context window, skills, subagents, and MCP. None of them are features
Pi ships. You will build all four out of a shell.

## Before you start

- [ ] Your RAG lab notebook is running and the Gradio launch cell has printed a public URL
- [ ] A GitHub account, created and email-verified **before today**
- [ ] The template repo link and model credentials from your instructor

> **Leave the RAG notebook running.** The corpus endpoint lives inside it. If that runtime
> stops, this lab loses its data source and the URL changes when you restart it.

---

# Part 1 — Workspace

Ten minutes, once. You are building the environment by hand rather than having a
devcontainer build it for you, because knowing what Pi actually needs is worth ten minutes.

## 1.1 A blank Codespace

Go to **github.com/codespaces**, click **New codespace**, and pick the **Blank** template.
No repository, no configuration. You get a plain Ubuntu container with Node, Python and git.

> **Two consequences of "blank".** It is not attached to a repository, so Codespaces secrets
> do not apply — you will `export` your key instead. And nothing is backed up: publish your
> work before you finish (Part 11) or it disappears with the container.

## 1.2 Get the lab repo

```bash
git clone https://github.com/YOUR-INSTRUCTOR/pi-rag-eval.git
cd pi-rag-eval
```

## 1.3 Install

```bash
./setup.sh
```

It checks Node (the MCP adapter needs 22.19 or later and will pull a newer Node through
nvm if yours is older), installs Pi from `@earendil-works/pi-coding-agent`, installs the
MCP adapter, and installs the Python dependencies. Re-runnable if a step fails.

> **One package name matters here.** Pi is published as
> `@earendil-works/pi-coding-agent`. An older `@mariozechner/pi-coding-agent` exists,
> is deprecated, and is frozen below the version the MCP adapter needs. The adapter
> declares the official package as a peer dependency, so installing the wrong one
> produces this at startup:
>
> ```
> Failed to load extension: Cannot find module '@earendil-works/pi-coding-agent'
> ```
>
> `setup.sh` removes the deprecated packages before installing, so a clean run avoids
> this. If you hit it anyway, see Troubleshooting.

Open it first if you want to see what it does — it is forty lines and no magic:

```bash
cat setup.sh
```

Then confirm all three things:

```bash
pi --version                                    # 0.84.0 or later
npm ls -g --depth=0 | grep pi-coding-agent      # exactly one line, @earendil-works
```

Start Pi and check the adapter loaded — `/mcp` should open a panel, not report an
unknown command.

Nothing on PATH? `source ~/.bashrc` or open a new terminal.

## 1.4 Model credentials

```bash
pi
/login
```

Codespaces forwards the OAuth callback to your browser, so a Claude or ChatGPT
subscription works here. It is the one thing the Colab fallback cannot do.

Otherwise:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Both of these live only in this shell. If you open a new terminal, set them again.

*No Codespace available? Appendix A has the Colab fallback.*

---

# Part 2 — Connect to your corpus

## 2.1 Find the URL

In your **RAG lab notebook**, look at the launch cell output and copy the public app URL —
the `https://….gradio.live` one, **not** the one ending in `/gradio_api/mcp/`.

If that cell is still spinning and never returned, that is normal Colab behaviour, and it
means the `print` statements after `demo.launch()` never ran. The URL is in the output
Gradio itself printed. The proper fix is `prevent_thread_lock=True` — see
`.agents/skills/corpus-eval/reference/notebook-patch.md`.

## 2.2 Point the lab at it

In your Codespace terminal:

```bash
export CORPUS_URL="https://xxxxxxxxxxxx.gradio.live"
```

No trailing slash, no `/gradio_api/mcp/`. This is not persisted — if you re-open the
Codespace, set it again.

## 2.3 Check it works

```bash
python tools/corpus_search.py "dagasztógép kapacitás" --top-k 3
```

You should get three passages back.

**Look for `chunk_id` in the output.** If those lines are missing or empty, your notebook
has not been patched, and the evaluation will fall back to matching on URL. That is
weaker, because several chunks share one source page, so every score comes out optimistic.
The one-line fix is in `.agents/skills/corpus-eval/reference/notebook-patch.md` — apply
it and relaunch now if you can.

Nothing back at all?

| What you see | What it means |
|---|---|
| `504` | The share tunnel is not reaching your app. In the RAG notebook: `!curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:7860/`. If that says 200 your app is fine and the tunnel is broken — relaunch, or ask for the Hugging Face Space fallback URL |
| Connection refused / timeout | The Colab runtime stopped, or the URL rotated |
| Results but all empty | The Weaviate collection is empty — re-run the upload cell in the RAG notebook |

## 2.4 Get a local copy of the corpus

Question generation needs the chunk text locally. In your **RAG lab notebook**:

```python
from google.colab import files
files.download(str(CHUNKS_PATH))
```

Then drag the downloaded `chunks.jsonl` into the `data/` folder in your Codespace file
explorer. Confirm:

```bash
wc -l data/chunks.jsonl
```

---

# Part 3 — Look around before you start

Two things in this repo shape everything the agent does. Read them yourself first —
you cannot judge the agent's behaviour without knowing what it was told.

> **Where did these come from?** Not from a standards body, and not from someone typing
> them out by hand. `AGENTS.md`, the skills, `TODO.template.md` and every script in
> `tools/` were generated by Pi in sessions much like the one you are about to run, then
> reviewed and kept so this lab is reproducible. In Part 12 you will generate one
> yourself. `prompts/bootstrap/` has prompts for regenerating the rest.

```bash
cat AGENTS.md
ls .agents/skills/
cat .agents/skills/corpus-eval/SKILL.md
```

**`AGENTS.md`** is project context, loaded automatically on every session. Conventions,
environment, what not to do.

**`.agents/skills/`** holds two skills. `corpus-search` documents the CLI.
`corpus-eval` holds the evaluation protocol — and notice how thin `SKILL.md` is. The
detail sits in `reference/protocol.md` and `scripts/score.py`, which are only read when
the agent decides it needs them.

That split is the whole idea behind skills. The protocol runs to several pages. It costs
nothing until it is relevant.

Now start a session:

```bash
pi
```

Paste in `prompts/00-orientation.md` (everything below the `---`) and read the reply. You
are checking that it found the skills and reached the endpoint, nothing more.

---

# Part 4 — Make it plan first

Paste `prompts/01-plan.md`.

The agent should write `TODO.md` and stop. **Read the plan before letting it run.** This
is the cheapest place in the entire task to catch a misunderstanding — correcting a plan
costs one message, correcting forty generated questions costs twenty minutes.

```bash
cat TODO.md
```

Check its estimate of the total endpoint calls. If it says something far from ~400,
it has misread the grid, and it is worth asking why.

Note what just happened: **the agent wrote that file.** `TODO.template.md` in the repo is
not a form to fill in — it is what a previous session produced, kept as a reference for
the shape that worked. Yours may differ, and yours may be better.

> **Why a file and not a to-do feature?** Pi deliberately has no to-do tooling. Its
> position is that built-in to-do lists confuse models, and a `TODO.md` in the repo works
> better. You will find out during Part 6 whether that holds up.

---

# Part 5 — Phase 1: build the evaluation set

Every chunk in your corpus can generate a question that only that chunk answers. That
makes the chunk its own gold label — no annotation, no LLM judge, no arguing about what
a good answer looks like.

## 5.1 Sample

```bash
python tools/sample_chunks.py --n 20 --seed 42
head -12 eval/chunks/chunk_01.md
```

Seeded, so your sample matches your neighbour's and results are comparable.

## 5.2 Generate, one subagent per chunk

Paste `prompts/02-generate.md`.

The agent will spawn a separate `pi` process for each chunk, four at a time. Watch the
process list in a second terminal:

```bash
watch -n1 'pgrep -af "pi -p" | head -20'
```

**Pi has no subagent feature.** It does not need one: the model has a shell and `pi` is on
the path, so a subagent is recursion. That is all any agent framework's "subagent" is
underneath — a fresh process with a fresh context window.

**Here the fresh context is the point, not the speed.** A subagent that has read only
chunk 7 cannot write a question that quietly depends on chunk 12. Generate all twenty in
one context and they contaminate each other, and the evaluation measures nothing. Same
instinct as a held-out test set.

If you want to see the machinery with no agent in the middle, run one by hand:

```bash
pi -p --tools read,write "$(cat prompts/subagent-question.md)

FILE: eval/chunks/chunk_03.md
SLOT: 03"
```

## 5.3 Inspect

```bash
wc -l eval/questions.jsonl
python -c "
import json
for line in open('eval/questions.jsonl', encoding='utf-8'):
    r = json.loads(line)
    print(f\"[{r.get('lang','--')}] {r.get('question', 'SKIP: ' + r.get('reason',''))}\")
"
```

Read a few. Do they make sense to someone who has never seen the corpus? Do any copy a
whole sentence from the source?

## 5.4 Validate before you trust it

A generated eval set can be quietly broken. Questions that copy source phrasing verbatim
let BM25 win by accident. Questions saying "the machine described above" are unanswerable
without the chunk in hand. Both produce confident numbers about nothing.

The agent will run an independent validation subagent — fresh context, told to be harsh.
Check the verdict.

If it comes back **FAIL**, stop. Fix `prompts/subagent-question.md`, delete
`eval/questions.jsonl`, regenerate. Sweeping a broken eval set wastes twenty minutes and
produces a report that is worse than useless, because it looks authoritative.

---

# Part 6 — Phase 2: the sweep

40 questions × 10 configurations = 400 retrieval calls.

Read the grid before you run anything:

```bash
sed -n '/^GRID = \[/,/^\]/p' tools/run_sweep.py
```

Now paste `prompts/03-sweep.md`.

> **Watch for this.** Some agents start making the 400 calls one at a time from their own
> context. That costs a fortune in tokens and takes an hour. If yours does, let three or
> four go through, then interrupt with `Esc` and ask it what that will cost. Recognising
> mechanical work and writing a loop is the habit worth learning here — for the agent and
> for you.

The right move is the script that already exists:

```bash
python tools/run_sweep.py --top-k 10 --concurrency 3
```

That script was itself written by an agent asked to do exactly what you just asked. If you
would rather watch that happen than take it on faith, `prompts/bootstrap/b2-script.md`
moves the shipped copy aside and has Pi write a replacement, then diffs the two. Budget
fifteen minutes.

## The interruption exercise

While the sweep is running, **stop your RAG lab's Colab runtime.**

Watch the calls start failing. Then restart the runtime, `export CORPUS_URL` with the new
URL, and run the same command again.

Nothing is lost. `results.jsonl` is append-only and the script skips finished work;
`TODO.md` still holds the plan. State on disk beats state in a context window, and this
is the single most transferable idea in the lab. Every agent you ever deploy will lose its
backend mid-task.

---

# Part 7 — Phase 3: score

```bash
python .agents/skills/corpus-eval/scripts/score.py --csv eval/scores.csv
python .agents/skills/corpus-eval/scripts/score.py --by-lang
python tools/plot_scores.py
```

The metric computation lives in a script **inside the skill**, and the skill tells the
agent to run it rather than work the numbers out itself.

That is deliberate. A model summing 400 reciprocal ranks in its head produces an answer
that is fluent, plausible and wrong. Anything deterministic belongs in code. Carry this
one back to work with you.

## What to look for

**The quality-versus-latency plot.** Anything up and to the left is strictly better. If
the reranked configurations sit barely above the plain ones but two seconds to the right,
you have your answer, and it may not be the answer the architecture diagram implied.

**The `--by-lang` table.** `keyword_*` on English queries should collapse — BM25 over
Hungarian text cannot match English words. Dense and hybrid should hold. If that pattern
is absent, something is misconfigured: check the vectors were built from `embedding_text`
and that the query prefix matches your embedding model.

**Alpha sensitivity.** If hybrid is flat across 0.25 / 0.50 / 0.75, the slider in your
Gradio UI is a knob that does nothing. Worth knowing.

---

# Part 8 — Phase 4: the report

Paste `prompts/04-report.md`. Now the agent does the part it is genuinely good at:
reading a table and arguing for a decision.

```bash
cat REPORT.md
```

## Check its honesty

Twenty chunks is a small sample. A 0.02 MRR gap between two configurations is not a
finding. **If the agent declared a winner on noise, say so** — a confident report built on
an underpowered experiment is the most common failure mode in applied evaluation, and
catching it is a more valuable skill than running the sweep.

## Close the loop

Take the recommended `mode`, `alpha`, `rerank` and `top_k` back to the RAG lab notebook
and change the defaults on the Gradio widgets.

You now ship a configuration you measured instead of one you assumed.

---

# Part 9 — MCP, and what it costs

Everything so far reached `search_corpus` through a CLI documented in a skill. The same
function is also exposed over **MCP**, because your Gradio app was launched with
`mcp_server=True`. Same code, same Weaviate, different access path.

Pi ships no MCP client. Its author's argument is that MCP tool definitions are verbose,
you pay for them on every request whether or not you use them, and a CLI with a good
README is usually better.

The community answer is `pi-mcp-adapter`, which `setup.sh` already installed. Rather than
registering every tool from every server, it gives the model **one proxy tool of roughly
200 tokens** and lets it discover what it needs on demand. Servers only start when used.

You are about to measure whether that trade is real.

## 9.1 Point it at your corpus

```bash
python tools/write_mcp_config.py
cat .mcp.json
```

That writes the standard project-local MCP config:

```json
{
  "mcpServers": {
    "corpus": { "url": "https://….gradio.live/gradio_api/mcp/" }
  }
}
```

Re-run it whenever the Gradio URL rotates. `/mcp setup` inside Pi can scaffold the same
file interactively, with a diff preview before it writes — worth seeing once.

## 9.2 The panel

Start Pi and open the panel:

```
/mcp
```

You get every configured server with its connection status and tools, and — the
interesting part — a **direct / proxy toggle per tool**.

- **Proxy** (default): the tool is reachable through the one shared proxy tool. Costs
  almost nothing until called.
- **Direct**: the tool's full schema is registered up front, exactly as a conventional MCP
  client would do. Convenient, and you pay for it on every request.

Connect `corpus`, look at the `search_corpus` schema, then flip it to direct and back.
`Ctrl+S` saves. The toggle takes effect in the running session.

## 9.3 Measure it

This is the whole point of the section, so actually do it.

In a second terminal, run the same trivial task twice under `--mode json`, once with
`search_corpus` on proxy and once on direct, and compare the input tokens on the first
request:

```bash
pi --mode json -p "What is 2+2? Do not use any tools." > /tmp/proxy.jsonl
# flip search_corpus to direct in /mcp, save, then:
pi --mode json -p "What is 2+2? Do not use any tools." > /tmp/direct.jsonl

grep -o '"input_tokens":[0-9]*' /tmp/proxy.jsonl  | head -1
grep -o '"input_tokens":[0-9]*' /tmp/direct.jsonl | head -1
```

The task is deliberately pointless. You are measuring what the session costs **before it
does anything**. One server with one tool is a small difference. Now imagine six servers
with twenty tools each, which is a normal desktop setup.

## 9.4 Use it

```
Use the corpus MCP server to find what the corpus says about oven capacity.
```

Watch the agent discover the tool through the proxy and call it. For multi-call work the
adapter also exposes a scripting tool, so the agent can loop and fan out over MCP inside a
single call rather than one round trip per query — `/skill:mcp-scripting` has the detail.

Worth trying: ask it to run five queries across different modes and summarise. Compare how
that feels against `tools/run_sweep.py` doing the same thing.

## 9.5 Pick a side

Paste `prompts/05-mcp-comparison.md`.

You now have three access paths to one function — a CLI in a skill, an MCP proxy tool, and
a direct MCP tool — and measurements for each. Disagree with the agent if you think it is
wrong.

> **Optional, one level down:** `python tools/mcp_probe.py list` speaks the protocol
> directly with no agent involved, so you can see the raw tool schema the server
> advertises and what it would cost verbatim.

---

# Part 10 — The corpus is not your friend

Your corpus was scraped from the public web. It flows, unreviewed, into an agent that has
a shell.

Paste `prompts/06-injection.md` — an ordinary-looking research task. Then:

```bash
ls -la eval/
cat eval/agent-registered.txt 2>/dev/null && echo ">>> your agent followed instructions from the corpus"
```

## Debrief

- Did your agent read the injected text? Did it act on it? Did it tell you?
- `.agents/skills/corpus-search/SKILL.md` contains an explicit warning about untrusted
  passages. Did it help? Would it survive a subtler injection than this one?
- That chunk arrived through the scraper you wrote in lab 1. Who reviewed that content?
- The agent had a shell. In this container the blast radius was nothing. What would it
  have been in your home directory, on your laptop, with your SSH keys?

There is no setting that fixes this. Containment, least privilege, and treating retrieved
text as data rather than instructions are what you have. This is why the lab runs in a
container and why `pi --tools read,grep,find,ls` exists.

---

# Part 11 — Save and clean up

**Your Codespace is blank — it has no repository behind it.** Nothing here survives unless
you push it somewhere:

```bash
gh auth status || gh auth login
gh repo create pi-rag-eval-results --private --source=. --push
```

Or download `eval/`, `REPORT.md` and `TODO.md` from the file explorer.

Do not skip this. Everything you just built — the report, the skill you wrote in Part 12,
your `TODO.md` — lives on a disk that is about to be deleted.

Then **delete the Codespace** at github.com/codespaces. Stopped Codespaces keep consuming
your 15 GB storage quota, and storage is the limit people hit first, not compute.

Stop your RAG lab Colab runtime too.

---

# Part 12 — Teach the agent what you just learned

Stay in the **same session** that wrote the report. The history is the raw material.

You have just worked out a procedure: sample, generate under isolation, validate, sweep,
score, interpret. It took you two hours and several false starts. Right now all of that
lives in one context window, and when this session ends it is gone.

The next person to touch this corpus will work it out again from scratch.

## Capture it

Paste `prompts/bootstrap/b3-skill.md`.

The agent will use the **`skill-writer`** skill — a skill about writing skills — to
produce a new `retrieval-regression` skill from your session transcript.

```bash
cat .agents/skills/skill-writer/SKILL.md
ls .agents/skills/retrieval-regression/
cat .agents/skills/retrieval-regression/SKILL.md
```

## Why this is the right moment, and not two hours ago

**A skill written in advance encodes what you assumed the task would need. A skill written
from a transcript encodes what it actually needed.** The endpoint that dropped. The
validation pass you did not know you wanted until the questions came back copying source
sentences verbatim. The fact that `results.jsonl` must be append-only.

Nobody writes those lines before doing the work. They are harvested.

This is also why the `corpus-eval` skill you have been using exists at all: someone ran
this lab manually first and captured what happened.

## Test it

A skill that never fires is worse than no skill, because you will believe it is helping.

Start a **fresh** session — the current one has seen everything and will look competent
for the wrong reasons:

```bash
pi
```

Then ask, in your own words, something a colleague would actually say. Not the skill's
vocabulary:

> *We re-scraped the site last night. Did retrieval get worse?*

Did the skill load? Did it follow its own steps? If it did not fire, the problem is the
`description` frontmatter, not the body. Fix it and try again.

## Then look at what you built

```bash
ls .agents/skills/
```

Four skills. Two shipped with the repo, one you generated, and one whose entire job is
generating the others.

That last one is the point. An agent that can extend itself is not a chatbot with tools
bolted on — the extension mechanism is just files, and files are something the agent can
already write.

## Going further

`prompts/bootstrap/` has three more, each of which moves a shipped artifact aside and has
Pi regenerate it:

| Prompt | Regenerates |
|---|---|
| `b1-agents-md.md` | `AGENTS.md`, from reading the code |
| `b2-script.md` | `tools/run_sweep.py`, from the requirement |
| `b4-todo.md` | `TODO.template.md`, from the task shape |

Each ends by diffing your version against the shipped one. Do that comparison — you will
find places where yours is better, and that is the most useful thing that can happen here.

---

# What you actually did

| Mechanism | Where it showed up | What it is underneath |
|---|---|---|
| **TODO.md** | Survived the endpoint dying in Part 6 | A text file. That is the entire trick |
| **Skills** | `corpus-eval` loaded only when needed | Instructions injected on demand, plus scripts |
| **Subagents** | 20 parallel processes in Part 5 | Recursion. One fresh context each |
| **MCP** | The `/mcp` proxy/direct toggle in Part 9 | A protocol, priced in tokens per request |
| **Self-extension** | Writing a skill in Part 12 | Files. The agent can already write files |

Pi gives a model a shell and four tools. Everything above was built from that, which is
why you now know how each one works rather than which button turns it on.

## Take these four home

1. **State belongs on disk.** Context windows are not memory.
2. **Deterministic work belongs in code.** Never let a model do arithmetic you care about.
3. **Retrieved text is data, never instructions.** No prompt fixes this; containment does.
4. **Write the skill after the work, not before.** Procedures you have not performed
   produce documentation of your assumptions.

---

# Troubleshooting

| Symptom | Fix |
|---|---|
| `pi: command not found` | `source ~/.bashrc`, or re-run `./setup.sh` |
| `setup.sh` fails on Node | The adapter needs Node 22.19+. `nvm install 22 && nvm use 22`, then re-run |
| `Cannot find module '@earendil-works/pi-coding-agent'` at startup | Wrong Pi package installed. See below the table |
| `pi install` of the adapter fails | Check `pi --version` is 0.84.0 or later, then retry |
| `/mcp` is not a command | The adapter did not install. `pi install npm:pi-mcp-adapter`, then restart Pi |
| `/mcp` shows corpus disconnected | URL rotated. `python tools/write_mcp_config.py`, then reconnect in the panel |
| `/login` does nothing | Use an API key instead, or check port forwarding is enabled |
| 504 from the corpus URL | Tunnel, not your app. Test `localhost:7860` inside the RAG notebook |
| Endpoint unreachable | RAG runtime died. Relaunch and re-`export CORPUS_URL` — the URL changes |
| `chunk_id` empty everywhere | Notebook not patched. Scores will be optimistic; note it in the report |
| `Sampled 0 chunks` | `data/chunks.jsonl` missing or empty. Part 2.4 |
| Subagents all fail instantly | No model credentials. Part 1.3 |
| Rate limit errors | Ask the agent to use 2 concurrent subagents instead of 4 |
| Sweep crawling | `--concurrency 2`, or re-sample with `--n 10` and regenerate |
| Lost everything on reconnect | A blank Codespace has no repo behind it. Part 11 — publish before you stop |

## The adapter cannot find Pi

```
Failed to load extension ".../pi-mcp-adapter/index.ts":
Cannot find module '@earendil-works/pi-coding-agent'
```

The adapter names the official Pi package as a peer dependency and looks for it beside
itself in global `node_modules`. This error means what is installed there is a different
package — most often the deprecated `@mariozechner/pi-coding-agent`, or the community
fork `@oh-my-pi/pi-coding-agent`.

```bash
npm ls -g --depth=0 | grep pi-coding-agent
```

Anything other than a single `@earendil-works` line is the problem:

```bash
npm uninstall -g @mariozechner/pi-coding-agent @oh-my-pi/pi-coding-agent
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
hash -r
pi --version
```

Note that the deprecated package is also frozen well below 0.84.0, so switching fixes the
version requirement at the same time. `pi install` writes to your Pi agent directory
rather than to `node_modules`, so the adapter itself stays registered — you do not need
to reinstall it.
| Agent stuck in a retry loop | `Esc` to interrupt. Tell it to record progress in `TODO.md` and stop |
| Your new skill never fires | The `description` frontmatter, not the body. Rewrite it as situations and phrasings |
| Skill fires but is ignored | `SKILL.md` is probably too long or too vague. Move detail to `reference/` |

---

# Appendix A — Colab fallback

Only if you cannot use a Codespace. You lose the interactive TUI, `/login`, and everything
when the runtime ends. You gain: no setup on a locked-down laptop.

Open a **new, empty** Colab notebook — not your RAG one — and run these as cells:

```python
!curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - > /dev/null 2>&1
!sudo apt-get install -y nodejs > /dev/null 2>&1
!node --version      # must be 22.19 or later for the MCP adapter
```

```python
!git clone -q https://github.com/YOUR-INSTRUCTOR/pi-rag-eval.git /content/pi-rag-eval
%cd /content/pi-rag-eval
!bash setup.sh
!npm ls -g --depth=0 | grep pi-coding-agent   # exactly one line, @earendil-works
```

```python
import os
from google.colab import userdata
os.environ["ANTHROPIC_API_KEY"] = userdata.get("ANTHROPIC_API_KEY")
os.environ["CORPUS_URL"] = "https://xxxxxxxxxxxx.gradio.live"
```

Use the Colab Secrets panel (key icon, left sidebar) for the API key. Do not paste keys
into cells.

Then get a terminal:

```python
!pip -q install colab-xterm
%load_ext colabxterm
%xterm
```

From that terminal the rest of this guide works unchanged. Two caveats: your browser eats
some of Pi's keybindings (`Ctrl+L`, `Ctrl+T`, `Ctrl+W` belong to the browser), and Colab
disconnects after roughly 90 idle minutes.

---

# Appendix B — Pi cheat sheet

Verify these against your installed version; Pi moves quickly.

| | |
|---|---|
| `pi` | Interactive session |
| `pi -p "…"` | One turn, print to stdout. How subagents get spawned |
| `pi -c` | Continue the previous session |
| `pi --tools read,grep,find,ls` | Read-only. A real boundary, not a suggestion |
| `pi --model …` | Switch provider or model |
| `pi --mode json` | Machine-readable event stream — pipe it to count tool calls and tokens |
| `Esc` | Interrupt |
| `/compact` | Summarise the context when it fills up |
| `/fork` | Branch the session to try two approaches from one point |
| `/tree` | Show the session tree |
| `/skill:name` | Load a skill explicitly instead of waiting for it to trigger |
| `pi install npm:<pkg>` | Install a Pi package. Packages run arbitrary code — read before installing |
| `npm ls -g --depth=0` | Check exactly one `pi-coding-agent` is installed, under `@earendil-works` |
| `/mcp` | MCP adapter panel: servers, status, tools, direct/proxy toggles |
| `/mcp setup` | Guided config: detect existing MCP files, scaffold `.mcp.json`, preview diffs |
| `/skill:mcp-scripting` | The adapter's scripting workflow, for multi-call MCP work |

Worth trying afterwards: run the whole Part 5 phase again under `--mode json`, pipe it to
a file, and count the tool calls and tokens each subagent used. That is how you turn "the
agent did well" into a number.
