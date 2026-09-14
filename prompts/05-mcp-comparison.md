# Prompt 05 — three roads to one function (20 min, optional)

Purpose: the MCP argument, settled with measurements rather than opinion. Run after
students have done the proxy/direct token comparison in Part 9.3, so they have numbers.

---

We can reach search_corpus three ways now:

1. tools/corpus_search.py, documented in the corpus-search skill
2. the MCP server, through the adapter's shared proxy tool
3. the same MCP tool registered directly, with its full schema in every request

I have measured what 2 and 3 cost per session. Read .mcp.json and the corpus-search
skill, then argue for one of them for this specific job.

Address these, concretely:

- What does each path cost, and when is that cost paid — per session, or per call?
- The proxy adds a discovery step before the agent can call anything. What does that
  cost in round trips, and when does it stop being worth the token saving?
- The CLI route needed someone to write and document a script. The MCP route needed
  someone to run a server. Which burden is lighter, and for whom?
- Which would you choose if this agent ran a hundred times a day? Which if a
  non-technical colleague had to wire it up once and never touch it again?

Write it as eval/access-paths.md. Take a position. Do not list trade-offs neutrally and
leave me to decide.
