# Notebook patches needed before the Pi exercise

Three changes to the RAG lab notebook. The first is required, the other two
save pain.

## 1. Required: return `chunk_id` from `search_corpus`

Without this, the evaluation has to match gold chunks by URL. Several chunks
share one source page, so a URL match is not proof the right passage was
retrieved, and every score comes out optimistic.

In the `search_corpus` function, in the result-block loop, add one line:

```python
    for rank, result in enumerate(results, start=1):
        text = result["text"][:1800]
        blocks.append(
            f"""RESULT {rank}
CHUNK_ID: {result.get('chunk_id', '')}
TITLE: {result['title']}
SECTION: {result.get('section_title', '')}
URL: {result['url']}
TEXT:
{text}"""
        )
```

Check that `chunk_id` survives the retrieval path. In the Weaviate collection
definition it must be a stored property, and `normalize_result` (section 13)
must carry it through. If `chunk_id` comes back empty, that is where it was
dropped.

## 2. Strongly recommended: stop the launch cell blocking

As written, `demo.launch()` blocks in Colab, so the lines after it never run —
including the two `print` statements with the URLs.

```python
demo.launch(
    share=True,
    mcp_server=True,
    debug=False,
    prevent_thread_lock=True,
)

public_url = demo.share_url
print("Gradio RAG app:", public_url)
print("MCP endpoint   :", public_url.rstrip("/") + "/gradio_api/mcp/")
```

`prevent_thread_lock=True` runs the server in a background thread and returns
immediately, which also keeps the runtime usable while Pi is hammering the
endpoint.

## 3. Optional: a health-check cell

Put this after the launch cell. When the public URL 504s, it tells you in two
seconds whether the app or the tunnel is at fault.

```python
import requests

for path in ["/", "/gradio_api/mcp/"]:
    try:
        response = requests.get(f"http://127.0.0.1:7860{path}", timeout=10)
        print(f"local  {path:22} {response.status_code}")
    except Exception as exc:
        print(f"local  {path:22} FAILED {type(exc).__name__}")

print("\nIf local is healthy but the public URL 504s, the share tunnel is the")
print("problem, not your app. Check https://status.gradio.app")
```
