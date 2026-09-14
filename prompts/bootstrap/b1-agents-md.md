# Bootstrap 1 — generate AGENTS.md

Run in a fresh session, in a copy of the repo with AGENTS.md moved aside:

    mv AGENTS.md AGENTS.shipped.md

---

Look around this repository and write AGENTS.md for it: the context file you
would want loaded automatically at the start of every session here.

Work out what it needs by reading the code, not by guessing from directory
names. Pay attention to what would trip up an agent that had not read the
source — the ephemeral endpoint, the append-only files, anything that looks
optional but is not.

Keep it under 60 lines. Everything in it costs tokens on every single session,
so anything that is only sometimes relevant belongs in a skill instead.

When you are done, diff it against AGENTS.shipped.md and tell me: what did you
include that it does not, and what did it know that you could not have?
