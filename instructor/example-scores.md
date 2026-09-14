# Example scoring output (SYNTHETIC)

Generated from random data, not from the real corpus. Included so you know
what the table looks like before running the lab for the first time. The
ordering here is invented — do not quote these numbers to students.

```
config_id         | n  | recall@1 | recall@3 | recall@5 | recall@10 | mrr@10 | median_ms | p90_ms
------------------|----|----------|----------|----------|-----------|--------|-----------|-------
hybrid_a50_rerank | 40 | 0.425    | 0.75     | 0.875    | 0.875     | 0.605  | 2118.0    | 2204  
hybrid_a25_rerank | 40 | 0.475    | 0.625    | 0.7      | 0.8       | 0.581  | 2109.5    | 2169  
hybrid_a50_plain  | 40 | 0.45     | 0.675    | 0.725    | 0.775     | 0.569  | 313.0     | 404   
hybrid_a75_rerank | 40 | 0.475    | 0.625    | 0.65     | 0.75      | 0.559  | 2111.5    | 2206  
vector_rerank     | 40 | 0.425    | 0.65     | 0.725    | 0.8       | 0.556  | 2123.0    | 2210  
hybrid_a75_plain  | 40 | 0.375    | 0.6      | 0.675    | 0.775     | 0.509  | 316.5     | 406   
vector_plain      | 40 | 0.35     | 0.6      | 0.7      | 0.775     | 0.496  | 296.0     | 392   
keyword_plain     | 40 | 0.225    | 0.325    | 0.375    | 0.6       | 0.304  | 294.0     | 387   
hybrid_a25_plain  | 40 | 0.15     | 0.375    | 0.5      | 0.675     | 0.3    | 336.5     | 395   
keyword_rerank    | 40 | 0.175    | 0.325    | 0.475    | 0.6       | 0.289  | 2137.0    | 2213  

400 records, 40 questions, 10 configs.
Gold chunk not in top-10 for 103 records (25.8%).
```

## What to look for in the real run

- `keyword_*` should sit near the bottom overall, and collapse hard on
  `lang=en` in the `--by-lang` view. If it does not, dense retrieval is
  probably misconfigured — check that vectors were built from
  `embedding_text` and that the query prefix matches the embedding model.
- The `*_rerank` twins should gain MRR and lose about 1.5-3 seconds per
  call. Whether that trade is worth it is the actual open question, and
  the answer may well be no.
- Hybrid alpha is often flat across 0.25/0.50/0.75. Flat means the slider
  in the Gradio UI is giving users a knob that does nothing.
