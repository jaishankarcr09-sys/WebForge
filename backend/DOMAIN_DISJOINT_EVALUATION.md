# Domain-disjoint model evaluation

Run this after the reviewed dataset contains at least 30 pairs, both classes, and at least five distinct source/query domains:

```bash
python backend/scripts/evaluate_domain_disjoint_similarity.py --data backend/data/human_reviewed_similarity_pairs.jsonl
```

Unlike a random row split, this evaluator keeps source website domains disjoint between training and test. The candidate catalogue may overlap across source queries, which reflects a search/ranking deployment where the candidate catalogue is known but the queried target website is new. The split is rejected if source URLs are missing, too few source domains exist, or a class is missing from either side.

Metrics include accuracy, precision, recall, F1, and ROC-AUC for Logistic Regression, Random Forest, Extra Trees, Histogram Gradient Boosting, and RBF SVC. Model choice should be based on a larger reviewed dataset, ranking metrics such as precision@k/nDCG@k, and a final untouched test set. This evaluator does not itself collect data or claim high accuracy.
