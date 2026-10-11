# Semantic similarity baseline

WebForge now has an optional zero-shot semantic-embedding baseline to compare against its TF-IDF/classical ML features. It uses the Sentence Transformers `sentence-transformers/all-MiniLM-L6-v2` model and cosine similarity over a compact text representation of website name, category, and description.

## Run

Install the optional package in the backend environment:

```bash
pip install sentence-transformers
python -m app.semantic_similarity \
  --data data/heldout_source_candidate_pairs.jsonl \
  --output data/semantic_scored_holdout.jsonl
python -m app.similarity_ranking_metrics \
  --data data/semantic_scored_holdout.jsonl \
  --output models/semantic_ranking_metrics.json
```

The input JSONL must contain `source_name`, `source_category`, `source_description`, `candidate_name`, `candidate_category`, and `candidate_description`. For ranking metrics, include source_url, candidate_url, and human-reviewed binary label too.

## Evaluation safeguards

- This is a **zero-shot baseline**, not a model fine-tuned on WebForge's reviewed labels.
- Do not compare scores from unrelated datasets or candidate catalogues as if they were calibrated probabilities.
- Keep source/query domains disjoint between training/model selection and final test where applicable.
- Use identical held-out source queries and candidate catalogues when comparing baselines.
- Report precision@k, hit-rate@k, MRR, nDCG@k, plus classification metrics where relevant.
- Inspect label quality and candidate coverage; a ranking score cannot fix incomplete or noisy ground truth.
- The first run downloads model weights. It is intentionally optional and not added to mandatory backend requirements to avoid making every deployment download a large ML dependency.
- Do not deploy it as the production ranker until it wins on representative held-out data and latency/resource costs are measured.

References: [Sentence Transformers semantic textual similarity](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html).
