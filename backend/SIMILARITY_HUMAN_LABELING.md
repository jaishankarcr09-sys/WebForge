# Human labeling workflow

The training pipeline needs reliable ground truth, not guessed labels. Use these scripts to turn candidate pairs into an auditable review process.

1. Collect permitted public metadata using the instructions in `SIMILARITY_DATA_COLLECTION.md`.
2. Build candidate pairs with labels left as `null`.
3. Export a CSV for review:

```bash
python backend/scripts/export_similarity_review_csv.py --input backend/data/pairs_for_review.jsonl --output backend/data/pairs_for_review.csv
```

4. A human reviewer labels each pair: `1` when the sites serve materially similar needs/products, `0` when they do not. Fill `reviewer`, `reviewed_at`, and a short rationale in `review_notes`. Do not label solely because names, keywords, or categories match.
5. Validate and import:

```bash
python backend/scripts/import_reviewed_similarity_csv.py --input backend/data/pairs_for_review.csv --output backend/data/human_reviewed_similarity_pairs.jsonl
```

The importer rejects missing labels/reviewer metadata, self-pairs, duplicate pairs, and datasets that lack either class. It records provenance as `human_reviewed`. Reviewers should resolve disagreements before training; record any changes in version control or a dataset registry.

Do not commit personal reviewer information or scraped page bodies. Use reviewer identifiers appropriate to the project's privacy policy. The current seed set is only a smoke-test set; production model claims require substantially more reviewed pairs and domain-disjoint evaluation.
