# Similarity model evaluation

Run from repository root:

```bash
python backend/scripts/evaluate_similarity_models.py --data backend/data/similarity_training_pairs.jsonl
```

The benchmark compares logistic regression, random forest, extra trees, histogram gradient boosting, and an RBF support-vector classifier. It reports accuracy, precision, recall, F1, and ROC-AUC on a stratified pair-level holdout.

**This is only a provisional pipeline check.** Pair-level random splits can leak domain-specific patterns between train and test. The current small curated seed data is not representative of the web, so the apparent winning model must not be called production-advanced. Before selecting a deployment model, grow the human-reviewed dataset and use domain-disjoint evaluation (no website domain may appear on both sides), repeated seeds, confidence intervals, and ranking metrics such as precision@k and nDCG@k. Do not treat classifier output as a calibrated similarity percentage.
