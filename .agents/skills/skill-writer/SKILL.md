---
name: skill-writer
description: >
  Use when creating, editing, or reviewing a skill for this project — writing a
  new SKILL.md, capturing a procedure you just performed so it becomes
  repeatable, splitting an overgrown skill, or fixing one that never triggers.
  Also use when the user says something like "remember how to do this",
  "make this repeatable", or "turn that into a skill".
---

# Writing skills

A skill is a folder with a `SKILL.md` in it. That is the whole format. What
makes one good or bad is entirely about what you put in it.

## The single most important rule

**Write the skill after doing the work, not before.**

A skill written from imagination encodes what you assumed the task would need.
A skill written from a transcript encodes what it actually needed — the failure
you hit at step four, the flag you had to look up, the thing that was slower
than expected. The second kind is worth having.

If you are asked to write a skill for a procedure nobody has performed yet, say
so and offer to do the procedure first.

## Structure

```
.agents/skills/<name>/
├── SKILL.md              short. the map, not the territory
├── reference/            detail, loaded only when the map points at it
│   └── <topic>.md
└── scripts/              anything deterministic
    └── <thing>.py
```

Scaffold it:

```bash
python .agents/skills/skill-writer/scripts/new_skill.py <name>
```

## The frontmatter

```yaml
---
name: kebab-case-name
description: >
  Use when <situations>. Also triggers on <phrasings a user would actually type>.
---
```

The `description` is not documentation. It is the only thing an agent sees when
deciding whether to open this skill, so write it as a list of **situations and
phrasings**, not as a summary of contents.

Bad: `Tools for evaluating retrieval.`
Good: `Use when evaluating or tuning the retriever: building an eval set,
sweeping configurations, computing recall and MRR, or deciding whether the
reranker is worth its latency.`

The bad one describes the skill. The good one describes the moments it should
fire.

## What goes in SKILL.md

Keep it under roughly 150 lines. It should read like a procedure someone hands a
competent new colleague: the steps in order, the decisions, and pointers to
where the detail lives.

Push out to `reference/` anything that is: long, only needed sometimes, or a
lookup table. Push out to `scripts/` anything deterministic.

**This is the payoff of the format.** Everything in `SKILL.md` costs tokens
whenever the skill loads. Everything in `reference/` costs nothing until the
agent reads that specific file. A five-page protocol becomes a one-page map plus
four pages that are usually free.

## Prefer a script to a paragraph

If a step involves arithmetic, parsing, sorting, or applying a rule to many
items, write a script and tell the skill to run it. Do not describe how to do it
in prose and hope.

A model asked to compute a mean reciprocal rank over four hundred records will
produce a number. It will look right. Verifying it costs more than writing the
script did.

## Write down what went wrong

The most valuable lines in a mature skill are the ones that read like scar
tissue:

> The endpoint drops roughly once an hour. The sweep script is append-only and
> resumable for that reason — do not delete `results.jsonl` to "start clean".

Nobody writes that in advance. Harvest it from what actually happened.

## Test it

A skill that never triggers is worse than no skill, because you will believe it
is helping.

1. Start a **fresh** session — the current one has already seen everything.
2. Phrase a request the way a real user would, not using the skill's own words.
3. Check the skill loaded and the steps were followed.
4. If it did not fire, the `description` is the problem, not the body.

Also try `/skill:<name>` to load it explicitly and confirm the body works even
when triggering does not.

## Reviewing an existing skill

Check, in this order:

- Does the description list situations, or does it summarise contents?
- Is anything in `SKILL.md` that only matters occasionally? Move it to `reference/`.
- Is any instruction telling the model to compute something? Replace with a script.
- Are there rules that no longer match how the code works?
- Would a competent colleague following this literally get a good result?

## Anti-patterns

- A skill that restates what the model already knows about Python or git.
- A description written for humans browsing a directory.
- Instructions with no failure modes, as if the happy path were the only path.
- One giant skill covering three unrelated jobs. Split it.
- A skill duplicating `AGENTS.md`. Project-wide conventions belong in `AGENTS.md`;
  task-specific procedures belong in a skill.
