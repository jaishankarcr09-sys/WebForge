# Similarity dataset quality gate

Run this before training or benchmarking reviewed website-pair labels:

```bash
cd backend
python -m app.similarity_dataset_quality \
  --data data/human_reviewed_similarity_pairs.jsonl \
  --output models/dataset_quality_report.json
pytest -q tests/test_similarity_dataset_quality.py
```

The gate checks binary labels, valid HTTP(S) URLs, self-pairs, duplicate unordered pairs, reviewer/date provenance, label presence, class counts, and source/candidate domain coverage. It writes a machine-readable JSON report and exits nonzero on errors. Warnings are not silently promoted to proof of quality.

## Important limits

- A valid schema does not prove that a human label is correct.
- Similarity needs a written rubric: compare purpose, audience, product/service, information architecture, and interaction patterns; do not label two sites similar only because they share a broad category.
- Keep reviewer identity and review date for auditability. Double-review a sample and adjudicate disagreements before relying on the benchmark.
- Run the source-domain-disjoint benchmark only after this gate. Do not tune the model against the final holdout repeatedly.
- Do not publish accuracy claims until the dataset is large and representative enough; report class balance, precision, recall, F1, ROC-AUC, and the evaluation protocol.

This script is a quality control check, not a model or accuracy guarantee.
