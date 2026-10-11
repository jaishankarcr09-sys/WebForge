# Website similarity ranking metrics

Binary classification metrics answer whether individual pairs are predicted correctly. WebForge's user-facing use case is to rank candidate websites for a source website, so ranking metrics should also be measured.

The module expects a JSONL file with one row per reviewed/scored source-candidate pair:

```json
{"source_url":"https://source.example","candidate_url":"https://candidate.example","label":1,"score":0.87}
```

Run:

```bash
cd backend
python -m app.similarity_ranking_metrics --data data/scored_holdout_pairs.jsonl --output models/ranking_metrics.json --k 1,3,5,10
pytest -q tests/test_similarity_ranking_metrics.py
```

Metrics are macro-averaged per source query:
- **Precision@k**: relevant candidates among the top k, divided by k.
- **Hit-rate@k**: fraction of source queries with at least one relevant candidate in the top k.
- **MRR**: reciprocal rank of the first relevant candidate, averaged over queries with at least one relevant candidate.
- **nDCG@k**: ranking quality against an ideal ordering, averaged over queries that have at least one relevant candidate.

Queries with no relevant candidate are explicitly counted. They contribute zero to hit-rate and precision, but are excluded from MRR and nDCG averages because those are undefined when no positive exists. Candidate catalogues must be representative; missing relevant candidates can make a good ranker appear bad, and incomplete labels can make a poor ranker appear good.

This module evaluates supplied scores; it does not train a model, generate labels, collect data, or prove accuracy. Generate scores only on a held-out test set not used for model selection.
