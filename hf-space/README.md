---
title: Modul-Bake Retrieval Endpoint
emoji: 🥐
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: 6.0.0
app_file: app.py
pinned: false
---

Retrieval-only endpoint for the agentic AI course evaluation lab.

## Deploy

1. Create a Space, SDK Gradio.
2. Upload `app.py` and `requirements.txt`.
3. Settings → Variables and secrets, add `WEAVIATE_URL` (hostname, no scheme)
   and `WEAVIATE_API_KEY`.
4. Optionally set `COLLECTION_NAME`, `EMBED_MODEL`, `RERANK_MODEL` to match
   whatever the notebook used. The defaults must agree with the notebook or
   dense retrieval will return noise.

## Why this exists

`gradio.live` share links are ephemeral, rotate on every relaunch, and go down.
Basing a classroom exercise on one means basing it on someone else's tunnel
infrastructure. This Space gives a stable URL for the whole course.

It exposes only `search_corpus`. There is no generation path and no LLM API key
in the runtime, so a public URL costs nothing if it leaks.
