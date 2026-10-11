# Comparing website similarity baselines

This command compares a **previously trained** classical model with the optional zero-shot Sentence Transformers baseline on exactly the same held-out pairs.

```bash
cd backend
pip install sentence-transformers
python -m app.compare_similarity_baselines \
  --data data/final_heldout_pairs.jsonl \
  --classical-model models/similarity_model.joblib \
  --output models/baseline_comparison.json
```

Input rows need source/candidate URL, name, category, description, and human-reviewed binary label. The classical artifact must have been trained without any rows or labels from this held-out set.

The report contains per-baseline scored pairs and query-level precision@k, hit-rate@k, MRR, and nDCG@k. It deliberately does not declare a winner or automatically deploy a model.

## Before trusting the result

1. Use the same source queries and candidate catalogue for both rankers.
2. Ensure relevance labels were reviewed consistently and cover the candidates.
3. Keep final test source domains untouched during feature/model selection.
4. Report query and pair counts alongside metrics.
5. Evaluate latency, memory, and ranking stability before deployment.

No dataset or accuracy claim is bundled with this code. A benchmark report is only as good as its held-out examples and labels.
