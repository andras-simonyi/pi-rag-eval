"""
Durable retrieval endpoint for the Pi evaluation lab.

Deploy to a Hugging Face Space to get a stable MCP + REST endpoint that does
not die with a Colab runtime. Exposes ONLY search_corpus — no generation, no
OpenAI key, nothing that costs money when strangers find the URL.

Space secrets required:
    WEAVIATE_URL     cluster REST endpoint, without https://
    WEAVIATE_API_KEY read access is enough

Space hardware: CPU basic is fine. The cross-encoder is slow there, so RERANK
defaults to off; the sweep turns it on explicitly.
"""

from __future__ import annotations

import os

import gradio as gr
import weaviate
from sentence_transformers import CrossEncoder, SentenceTransformer
from weaviate.classes.init import Auth
from weaviate.classes.query import MetadataQuery

COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "ModulBakeChunks")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "intfloat/multilingual-e5-base")
RERANK_MODEL = os.environ.get(
    "RERANK_MODEL", "jinaai/jina-reranker-v2-base-multilingual"
)
CANDIDATE_POOL = 25

# Load once at startup. Keep these module-level; Spaces restarts are expensive.
embedder = SentenceTransformer(EMBED_MODEL)
_reranker: CrossEncoder | None = None


def reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL, trust_remote_code=True)
    return _reranker


client = weaviate.connect_to_weaviate_cloud(
    cluster_url=f"https://{os.environ['WEAVIATE_URL']}",
    auth_credentials=Auth.api_key(os.environ["WEAVIATE_API_KEY"]),
)
collection = client.collections.get(COLLECTION_NAME)


def embed_query(text: str):
    # e5 models expect the query: prefix. Drop this if your model does not.
    return embedder.encode(f"query: {text}", normalize_embeddings=True)


def normalize(objects) -> list[dict]:
    return [
        {
            "chunk_id": obj.properties.get("chunk_id", ""),
            "title": obj.properties.get("title", ""),
            "section_title": obj.properties.get("section_title", ""),
            "url": obj.properties.get("url", ""),
            "text": obj.properties.get("text", ""),
        }
        for obj in objects
    ]


def retrieve(query: str, mode: str, top_k: int, alpha: float, rerank: bool):
    pool = max(top_k, CANDIDATE_POOL if rerank else top_k)

    if mode == "keyword":
        response = collection.query.bm25(
            query=query, limit=pool, return_metadata=MetadataQuery(score=True)
        )
    elif mode == "vector":
        response = collection.query.near_vector(
            near_vector=embed_query(query).tolist(),
            limit=pool,
            return_metadata=MetadataQuery(distance=True),
        )
    else:
        response = collection.query.hybrid(
            query=query,
            vector=embed_query(query).tolist(),
            alpha=alpha,
            limit=pool,
            return_metadata=MetadataQuery(score=True),
        )

    results = normalize(response.objects)

    if rerank and results:
        pairs = [(query, item["text"]) for item in results]
        scores = reranker().predict(pairs)
        order = sorted(range(len(results)), key=lambda i: scores[i], reverse=True)
        results = [results[i] for i in order]

    return results[:top_k]


def search_corpus(
    query: str,
    mode: str = "hybrid",
    top_k: int = 6,
    alpha: float = 0.5,
    rerank: bool = False,
) -> str:
    """
    Search the Modul-Bake corpus and return ranked source passages.

    Args:
        query: Natural-language search query.
        mode: Retrieval method: keyword, vector, or hybrid.
        top_k: Number of final passages to return.
        alpha: Hybrid weighting from 0.0 (keyword) to 1.0 (vector).
        rerank: Whether to apply the multilingual neural reranker.

    Returns:
        Ranked passages with chunk ids, titles, sections, URLs, and source text.
    """
    results = retrieve(query, mode, int(top_k), float(alpha), bool(rerank))

    blocks = []
    for rank, result in enumerate(results, start=1):
        blocks.append(
            f"""RESULT {rank}
CHUNK_ID: {result['chunk_id']}
TITLE: {result['title']}
SECTION: {result['section_title']}
URL: {result['url']}
TEXT:
{result['text'][:1800]}"""
        )
    return "\n\n---\n\n".join(blocks)


with gr.Blocks(title="Modul-Bake retrieval endpoint") as demo:
    gr.Markdown(
        "# Modul-Bake retrieval endpoint\n"
        "Retrieval only. No answer generation. Used by the agentic AI course "
        "evaluation lab.\n\n"
        "MCP endpoint: append `/gradio_api/mcp/` to this Space's URL."
    )
    with gr.Row():
        query_box = gr.Textbox(label="Query", scale=3)
        mode_box = gr.Radio(
            ["keyword", "vector", "hybrid"], value="hybrid", label="Mode"
        )
    with gr.Row():
        alpha_box = gr.Slider(0.0, 1.0, value=0.5, step=0.05, label="Alpha")
        topk_box = gr.Slider(1, 10, value=6, step=1, label="Top-k")
        rerank_box = gr.Checkbox(value=False, label="Rerank")
    output = gr.Textbox(label="Results", lines=20)
    gr.Button("Search").click(
        search_corpus,
        [query_box, mode_box, topk_box, alpha_box, rerank_box],
        output,
        api_name="search_corpus",
    )

if __name__ == "__main__":
    demo.launch(mcp_server=True, ssr_mode=False)
