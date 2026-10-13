# SaaS Similarity Expansion V4 — Review Queue

## Purpose

Add new product domains to the WebForge SaaS similarity pilot so a strict domain-disjoint evaluation can reserve genuinely unseen domains for testing.

This is a **review worksheet**, not labeled training data. The 12 seeds below are distinct from the currently reviewed 21-domain pilot as last audited. This batch creates 66 unordered candidate pairs.

## Files

- `saas_similarity_pilot_urls_v4.csv`: 12 new product-domain seeds with broad categories.
- `saas_similarity_pilot_review_v4.csv`: all 66 unordered pairs, with labels intentionally blank.

## Labeling policy

Use the primary-problem rule consistently:

- `1`: The two products are close alternatives; a user could realistically choose either to solve the same primary problem.
- `0`: They primarily solve different problems, even if features overlap.
- Do not infer labels from category names alone. Check the product descriptions and current official product pages first.
- Leave `reviewer_label` blank until the pair has been assessed. Record a short explanation in `reviewer_notes`, the reviewer identity, and review date.
- If a pair is ambiguous or a product's scope is unclear, leave it pending and note what needs verification instead of guessing.
- These rows are not independent expert labels until a qualified reviewer actually reviews them. Do not describe this worksheet as reviewed ground truth.

## Review sequence

1. Collect and verify product metadata for the 12 seed URLs using the repository's existing collection workflow.
2. Review pairs in manageable batches, checking the official product descriptions for both products.
3. Check label balance and category coverage after actual reviews; do not force an artificial 50/50 split.
4. Merge these rows into the training dataset only after review and duplicate-domain-pair checks.
5. Evaluate using the strict both-endpoint domain-disjoint evaluator. Cross-partition pairs must be excluded, and TF-IDF must be fitted on training rows only.

## Safety and scope

- No existing labels, datasets, or evaluation reports are changed by this worksheet.
- No labels are pre-filled or machine-inferred.
- No model training, merge, or deployment is performed by this change.
- The 66 rows are review candidates, not 66 new verified examples.
