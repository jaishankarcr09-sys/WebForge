# WebForge Similarity Dataset: Collection and Labeling Guide

This guide describes a human-reviewed dataset workflow for the Similar Websites feature. The current seed pairs are illustrative development data, not a representative benchmark of the web.

## 1. Define what “similar” means

Use this label definition consistently:

- **1 — Similar:** a reasonable user comparing the source website would consider the candidate a direct alternative or close substitute for a similar audience and primary job-to-be-done.
- **0 — Not similar:** the candidate serves a materially different primary purpose, audience, or use case, even if it shares generic words or a broad industry.
- **Uncertain — leave unlabeled:** evidence is insufficient or reviewers disagree. Do not force a binary label.

Similarity is about product/service and user intent, not whether two sites look alike or have similar names.

## 2. Collect public metadata responsibly

For each site, collect only fields needed for this task:

- canonical URL and hostname
- website/product name
- primary category
- short factual description of the main product/service
- metadata source and collection date

Prefer public page title, meta description, and visible category information. Do not collect personal data, login-only content, or sensitive data. Respect each site's robots policy and applicable terms. Do not bypass access controls or anti-bot measures. If a page is blocked or robots policy disallows collection, skip it.

The current collector accepts an explicit URL CSV and is metadata-only; it is not an unrestricted recursive crawler. Review each record for accuracy before generating pairs.

## 3. Build balanced, useful pairs

For each source website, choose candidate websites from:
- likely direct alternatives in the same category;
- near-neighbours that sound similar but solve a different problem;
- clear negatives from different categories.

Avoid comparing a site to itself. Keep source and candidate hostnames different. Deduplicate unordered domain pairs. Avoid using many pairs from the same domain as if they were independent examples.

Start with a small pilot of 30–50 pairs across at least 5 source domains. Include both labels and uncertain rows in a separate review queue. This is a pilot, not enough by itself to claim production-grade generalization.

## 4. Review and label

Have a human reviewer inspect both websites' public descriptions and answer: “Would a user looking for this source reasonably consider this candidate a close alternative?”

Record:
- label (`1` or `0`; leave blank if uncertain)
- reviewer identifier (team handle, not personal details)
- review date
- brief rationale/evidence, if available

For ambiguous cases, ask a second reviewer. Resolve disagreements before including the row in the training set. Do not derive labels from the model's own scores.

## 5. Validate before training

Run the repository's dataset-quality audit and domain-disjoint evaluation scripts documented in the similarity model runbook. Fix malformed URLs, missing provenance, duplicates, self-pairs, label imbalance, and insufficient source-domain diversity first.

Keep a final held-out set untouched until model selection is complete. Fit vectorizers and models only on the training split. Report precision@k, hit-rate@k, MRR, and nDCG@k alongside class-based metrics; compare the classical baseline and optional semantic baseline on the same held-out examples.

## 6. API integration status

The similarity API accepts metadata supplied in the request and does not fetch arbitrary URLs. Ranking stays unavailable until a reviewed/evaluated model artifact is explicitly configured with `WEBFORGE_SIMILARITY_MODEL_PATH`. Do not point that variable at an untrusted artifact. Do not deploy a model trained only on illustrative seed pairs as though it were production-ready.
