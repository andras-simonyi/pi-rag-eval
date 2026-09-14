# Instructor runbook

## Before the course

**Two weeks out.** Ask students to create a GitHub account and verify their
email, from their own network. Twenty signups from one venue IP inside ten
minutes trips GitHub's abuse detection, and a flagged account cannot open a
Codespace until a human clears it.

**One week out.**

- Host this repo somewhere students can clone it. They start from a **Blank**
  Codespace and clone, so it does not need to be a template — but it must be
  reachable, and their Codespace must be on a **personal** account, since
  org-owned Codespaces bill from the first core-hour.
- Pin `PI_VERSION` and `MCP_ADAPTER_VERSION` at the top of `setup.sh`. An
  unpinned install means half the room is on a different build and the token
  measurements in Part 9.3 stop being comparable.
- Run `./setup.sh` yourself in a fresh blank Codespace and time it. The Node
  upgrade path through nvm is the slow step; if the base image already ships
  22.19+, it is much faster.
- Apply the notebook patches in
  `.agents/skills/corpus-eval/reference/notebook-patch.md` to the RAG lab
  notebook. The `chunk_id` one is required.
- Deploy `hf-space/` as a Hugging Face Space and keep it running. This is your
  fallback endpoint when someone's Colab dies, and it is worth having as the
  *primary* endpoint if you would rather not depend on `gradio.live` at all.
- Create the run yourself end to end. Note the actual sweep wall-clock time on
  your hardware and adjust `--n` accordingly.

**Day of.**

- Verify the fallback Space is warm (free Spaces sleep).
- Have the poisoned chunk ready but not yet injected.
- Test `*.gradio.live` from the venue network. Training venues block it more
  often than you would expect.

## Session shape (2h 15m)

| Time | Segment | Prompt |
|---|---|---|
| 0:00 | Why an agent and not the chatbot you already built | — |
| 0:10 | Orientation, endpoint check | `prompts/00-orientation.md` |
| 0:15 | Planning, TODO.md appears | `prompts/01-plan.md` |
| 0:30 | Question generation, subagents | `prompts/02-generate.md` |
| 0:55 | **Break — and kill your Colab runtime during it** | — |
| 1:05 | Resume, sweep, score | `prompts/03-sweep.md` |
| 1:25 | Report and recommendation | `prompts/04-report.md` |
| 1:45 | MCP: proxy vs direct, measured | Part 9, then `prompts/05-mcp-comparison.md` |
| 2:00 | The poisoned chunk | `prompts/06-injection.md` |
| 2:10 | Debrief |  — |

### With more time (add 45-60 min)

| Time | Segment | Prompt |
|---|---|---|
| +0:00 | Write a skill from the session | `prompts/bootstrap/b3-skill.md` (Part 12) |
| +0:20 | Test it fires from a fresh session | — |
| +0:30 | Regenerate AGENTS.md and diff | `prompts/bootstrap/b1-agents-md.md` |

Or hand out the **starter variant** from the beginning:

```bash
./instructor/make-starter.sh ../pi-rag-eval-starter
```

That strips `AGENTS.md`, `run_sweep.py`, `TODO.template.md` and the `corpus-eval` skill,
keeping each as a `.shipped` copy to diff against. Students generate them with the
bootstrap prompts. It is the better version of this lab if you have a half-day, and too
slow if you have two hours.

Note the deliberate ordering problem the starter creates: `corpus-eval` describes a
procedure, so the honest way to write it is to run the evaluation with the protocol in
hand and capture the skill at the end. Students feel why skills come last. The full repo
hides that.

Cut in this order if you are short: 05, then 06, then reduce `--n` to 10.
Never cut 02 — the subagent phase is the part that does not transfer from
reading documentation.

## The set pieces

**Kill the runtime during the break.** Do not announce it. Students come back,
the sweep fails, and they discover that `TODO.md` plus an append-only results
file means they lose nothing. This teaches more about agent engineering than
any slide about state management.

**Watch for hand-execution in phase 2.** Some agents will start making the 200
sweep calls one at a time instead of running the script. Let three or four go
through, then stop the room and ask what it is costing. "A good agent writes a
loop" is a lesson best delivered from evidence.

**The reranker result is genuinely uncertain.** You may find it adds very
little MRR for one to three seconds per call. That is a real finding about
their own system, and it is more valuable than a tidy confirmation.

**Part 12 is the one people remember.** An agent writing a skill, using a skill about
writing skills, from a transcript of work it just did. Do not cut it before cutting 05 or
06. If you are very short, drop the sweep to `--n 10` and keep Part 12.

**The proxy/direct toggle is the best MCP demo you will get.** Flipping one tool from
proxy to direct and watching the session's baseline input tokens jump makes an
abstract argument concrete in thirty seconds. Have students do it themselves rather
than showing it from the front.

**Cross-lingual is the reliable crowd-pleaser.** BM25 collapses on English
queries against Hungarian text while hybrid holds. It justifies every
architectural decision from the earlier lab in one table.

## Failure playbook

| Symptom | First move |
|---|---|
| Public URL 504s | `curl` localhost:7860 inside Colab. Healthy → tunnel problem, switch to the HF Space |
| `demo.launch()` never returns | Expected. Apply patch 2; the URL is in the printed output meanwhile |
| Codespace won't start | Check the repo is personal, not org-owned |
| `pi` not on PATH | `source ~/.bashrc` or re-run `./setup.sh` |
| `/mcp` unrecognised | Adapter not installed, or Pi older than 0.84.0 |
| Node too old for the adapter | Needs 22.19+. `setup.sh` handles it via nvm; check nvm exists |
| Student lost all work | Blank Codespaces have no repo. Remind everyone at the break, not at the end |
| All searches return nothing | Weaviate collection empty — rerun the notebook's upload cell |
| `chunk_id` empty everywhere | Patch 1 not applied. Scores will be optimistic; say so and continue |
| Sweep crawling | Drop `--n` to 10, or set `--concurrency 2` if Weaviate free tier is throttling |
| One student's Colab dead | Point them at the shared HF Space URL |

## Cost

Retrieval calls are free (Weaviate free tier, local reranker). The model cost
is Pi's own inference: roughly 20 question-generation subagents plus an
orchestrator plus a report. With a cheap model on the leaves and a strong model
on the orchestration, budget well under a dollar per student. Set per-student
spend caps anyway.
