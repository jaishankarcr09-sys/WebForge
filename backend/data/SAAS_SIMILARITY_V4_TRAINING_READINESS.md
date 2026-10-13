# SaaS Similarity V4 — Training Readiness Review

Review date: 2026-10-13  
Branch: `data/saas-similarity-expansion-v4`

## Decision

**Structurally valid, but not ready to be used as a standalone training/evaluation dataset.**

This is a read-only readiness assessment. It does not change training examples, runtime behavior, the canonical labels, or deployment state.

## Sources inspected

- `backend/data/saas_similarity_pilot_v4_canonical.csv`
- `backend/data/saas_similarity_pilot_v4_user_review_decisions.csv`
- `backend/data/saas_similarity_pilot_review_v4.csv`
- `backend/data/similarity_training_pairs.jsonl` (read-only structural inspection)

## Verified structural results

### Canonical reviewed dataset

- Rows: **66**
- Unique unordered product pairs: **66**
- Duplicate canonical pairs: **0**
- Labels: **62 Label 0**, **4 Label 1**
- Rows with missing rationale, invalid binary label, missing baseline/source provenance, or incorrect user-confirmed status under the checks performed: **0**
- Label 0 share: **93.9%**
- Label 1 share: **6.1%**

### Existing training JSONL

- Lines: **32**
- JSON parse errors: **0**
- Rows missing required fields or containing non-binary labels under the checks performed: **0**
- Labels: **11 Label 0**, **21 Label 1**
- Provenance value observed: `curated_seed`

Structural validity only confirms formatting and required metadata. It does not independently establish that every label is correct or that a model trained on these examples will generalize.

## Readiness risks

### 1. Severe imbalance in the canonical review set

Only 4 of 66 reviewed pairs are positive (Label 1). This is too few positive examples to support robust standalone model training or a stable estimate of positive-class performance. The existing 32-line seed file has a different label balance, so simply concatenating both sources would produce a mixed dataset with source-specific label distributions.

**Recommendation:** collect more independently reviewed positive examples before using the canonical set for model fitting or evaluation. Do not synthetically flip labels or silently rebalance the data. If sampling or class weighting is later considered, record it as an explicit experiment.

### 2. Pair labels need a written operational definition

The reviewed rationales generally treat Label 1 as products that solve the same primary problem and can be alternatives, and Label 0 as products with different primary domains even if they share secondary features. Borderline product pairs may still need adjudication.

**Recommendation:** document this rule before collecting another batch, include examples for borderline overlap, and keep user-confirmed decisions distinct from assistant-generated proposals.

### 3. Random row splitting risks product leakage

The 66 canonical pairs cover 12 named products in a dense pairwise review set. If rows are randomly split, the same products will occur in both training and validation/test partitions. This can make evaluation look better than performance on previously unseen products.

**Recommendation:** choose the evaluation goal before splitting:
- For performance on new pairs made from known products, use a pair-level split and explicitly describe that limited scope.
- For generalization to unseen products, use a product-disjoint or grouped evaluation design, ensuring no held-out product appears in training pairs. With only 12 products and 4 positive pairs, this will be highly data-limited and may not yield a stable metric.

Do not report random-pair-split results as evidence of unseen-product generalization.

### 4. Combining sources requires provenance and duplicate checks

The canonical file is a reviewed pair dataset; the JSONL contains a separate curated seed set. Product overlap and possible conceptual overlap should be checked before combining them. Retain a source/provenance field for every example and deduplicate normalized unordered pairs across sources, while investigating label disagreements rather than resolving them silently.

**Recommendation:** preserve the canonical CSV and current training JSONL as separate source artifacts. Any future combined dataset should be a new file with documented precedence, provenance, duplicate checks, and conflict handling.

### 5. Metrics must reflect the positive class and dataset size

Accuracy alone can be misleading with the canonical label distribution. With only four positive examples, a small number of errors can substantially change precision, recall, and F1.

**Recommendation:** after collecting enough data, report the confusion matrix, precision, recall, F1, and precision-recall performance where appropriate, alongside class counts and split methodology. State the number of positive examples in each evaluation split. Avoid strong conclusions from tiny validation/test partitions.

## Suggested next steps

1. Keep the current canonical CSV and training JSONL unchanged.
2. Freeze and document the label policy.
3. Add more reviewed pairs, especially positive examples across multiple product categories, while avoiding artificial or unverified labels.
4. Review duplicate and conflicting pairs across all source datasets before combining.
5. Design a split that matches the intended use case, and document whether the goal is known-product pair ranking or unseen-product generalization.
6. Run training only as a separate, explicitly approved experiment after the data and evaluation plan are agreed.

## Scope and safety

This review created no training dataset, ran no model training, and changed no runtime code. It did not edit `backend/data/similarity_training_pairs.jsonl`, merge PR #50, or deploy services.
