# WebForge similarity model: reproducible runbook

This runbook describes the current experimental pipeline from permitted public metadata to reviewed labels and offline evaluation. It does **not** imply that a production model has been trained or deployed.

Run commands from the repository root unless a step explicitly says otherwise.

## 0. Install the backend dependencies

```bash
python -m pip install -r backend/requirements.txt
python -m pip install pytest
```

The optional semantic baseline has an extra dependency:

```bash
python -m pip install sentence-transformers
```

## 1. Prepare an explicit seed list

Create `backend/data/public_site_seeds.csv` with a header and rows such as:

```csv
url,category
https://example.com,reference
https://www.python.org,developer_tools
```

These are format examples, not a recommended benchmark dataset. Add a diverse list of websites you are allowed to access. The collector does not discover or recursively crawl links; it checks robots.txt, uses a descriptive user-agent, waits between requests to the same host, and stores minimal metadata. A robots check that fails cannot be treated as permission.

## 2. Collect minimal public metadata

```bash
python backend/scripts/collect_public_metadata.py \
  --input backend/data/public_site_seeds.csv \
  --output backend/data/public_site_metadata.jsonl \
  --delay 2
```

Inspect the output and collection statuses. Do not assume every URL was collected successfully.

## 3. Build unlabeled pairs and review them

```bash
python backend/scripts/build_similarity_review_pairs.py \
  --input backend/data/public_site_metadata.jsonl \
  --output backend/data/pairs_for_review.jsonl \
  --max-pairs 1000

python backend/scripts/export_similarity_review_csv.py \
  --input backend/data/pairs_for_review.jsonl \
  --output backend/data/pairs_for_review.csv
```

Have a person review each pair using a consistent written definition of “similar website” (for example, similar audience and primary use case, not merely a matching keyword). Fill the label and reviewer/date fields in the CSV. Use `1` for relevant/similar and `0` for not relevant. Do not infer labels automatically from category or model scores.

Import the reviewed file:

```bash
python backend/scripts/import_reviewed_similarity_csv.py \
  --input backend/data/pairs_for_review.csv \
  --output backend/data/human_reviewed_similarity_pairs.jsonl
```

Keep a separate, untouched final holdout. Do not use final-holdout labels to tune the model or select features.

## 4. Audit dataset quality before training

```bash
python -m backend.app.similarity_dataset_quality \
  --data backend/data/human_reviewed_similarity_pairs.jsonl \
  --output backend/models/dataset_quality_report.json
```

The quality gate checks structural issues and basic diversity. Passing is not proof that labels are correct or representative. Resolve all errors and read the warnings before continuing.

## 5. Benchmark classical algorithms with source-domain separation

```bash
python backend/scripts/evaluate_domain_disjoint_similarity.py \
  --data backend/data/human_reviewed_similarity_pairs.jsonl \
  --output backend/models/domain_disjoint_benchmark.json
```

Review the reported train/test domains and confirm there is no source-domain overlap. This benchmark is for model selection, not final unbiased performance reporting.

## 6. Train the classical baseline

Only after choosing the training dataset and preserving a separate holdout:

```bash
python backend/scripts/train_similarity_model.py \
  --data backend/data/similarity_training_pairs.jsonl \
  --output backend/models/similarity_baseline.joblib
```

Ensure `similarity_training_pairs.jsonl` contains only training rows. Do not point this command at the final holdout.

## 7. Compare classical and semantic ranking on the same holdout

```bash
python -m pip install sentence-transformers
python -m backend.app.compare_similarity_baselines \
  --data backend/data/final_heldout_pairs.jsonl \
  --classical-model backend/models/similarity_baseline.joblib \
  --output backend/models/baseline_comparison.json
```

The JSON report includes scored pairs and query-level precision@k, hit-rate@k, MRR, and nDCG@k for both approaches. Confirm that the classical artifact was trained without any holdout rows and that both methods were evaluated on identical source/candidate pairs. Do not interpret cosine or classifier scores as calibrated probabilities.

## 8. Run tests

```bash
cd backend
pytest tests/ -q
cd ..
```

## Decision gate before production

Do not ship a model solely because CI passes or one benchmark looks good. Require:
- enough human-reviewed pairs across many independent source domains;
- a documented, consistent relevance rubric and auditable reviewer provenance;
- a final untouched holdout with representative queries and candidate catalogues;
- side-by-side ranking quality and latency/memory measurements;
- a safe fallback if the artifact or optional semantic dependency is unavailable;
- an explicit review of privacy, robots policy, retention, and user-facing claims.

The current code provides experimental tooling. This runbook does not claim that a representative dataset exists, that any algorithm has won, or that the model is enabled in production.
