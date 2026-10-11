# SaaS and Software Tools Similarity Pilot

This is a **seed URL list**, not a dataset of labels. It contains 10 public product sites across team communication, productivity, project management, developer tools, and payments. The mix is intended to produce plausible alternatives and clear non-alternatives. The model must not assign labels automatically.

## Guardrails

- Collect only public page metadata from the explicit URLs in the CSV.
- The collector checks robots policy, refuses non-public/private destinations, avoids automatic redirects, and stores metadata rather than full page bodies.
- Collection can skip sites because of robots policy, temporary failures, or site changes. Do not bypass those controls.
- Treat the category column as a starting hint; verify the actual product name, category, and description from the collected metadata.
- Use label `1` only when the candidate is a close substitute for the same audience and primary job-to-be-done.
- Use label `0` when the primary purpose/audience differs materially.
- Leave uncertain pairs unlabeled in your own notes and do not import them into the binary training set until reviewed.
- Do not assume Slack vs Discord, Notion vs Trello, or any other borderline pair is automatically positive/negative. Decide from evidence and the definition above.

## Step 1 — Collect public metadata

Run from the repository root (requires the backend dependencies installed):

```bash
python backend/app/public_metadata.py --input backend/data/saas_similarity_pilot_urls.csv --output backend/data/saas_similarity_pilot_metadata.jsonl --delay 2
```

Expected output: one JSONL row per input URL with a status. Check the summary and inspect the output. If a URL is skipped/rejected/error, keep that status visible and do not invent missing metadata.

## Step 2 — Build the unlabeled pair queue

```bash
python backend/scripts/build_similarity_review_pairs.py --input backend/data/saas_similarity_pilot_metadata.jsonl --output backend/data/saas_similarity_pilot_pairs.jsonl --max-pairs 100
```

With 10 successfully collected sites, at most 45 unique unordered pairs can be created. Only records with status `collected`, title, and URL are eligible. Generated pairs have `label: null`; no labels are inferred.

## Step 3 — Export a human-review CSV

```bash
python backend/scripts/export_similarity_review_csv.py --input backend/data/saas_similarity_pilot_pairs.jsonl --output backend/data/saas_similarity_pilot_review.csv
```

Open `backend/data/saas_similarity_pilot_review.csv` in a spreadsheet editor. For each pair:
1. Read both names, categories, and descriptions.
2. Optionally open both public URLs manually to verify their current product purpose.
3. Set `label` to `1` or `0`; do not force a label if uncertain.
4. Fill `reviewer` with a team handle/alias, `reviewed_at` with the review date (YYYY-MM-DD), and `review_notes` with a concise reason/evidence.
5. Keep the source and candidate URL fields intact. Do not duplicate a pair in reverse order.

Suggested review target: 30–45 reviewed pairs across the available source domains, with both classes represented. The repository quality gate recommends at least 30 rows, 5 source domains, and 10 examples per class before benchmarking; treat this pilot as a starting point, not proof of production quality.

## Step 4 — Validate and import reviewed labels

After saving the reviewed CSV, run the existing label importer through the repository script:

```bash
python backend/scripts/import_similarity_review_csv.py --input backend/data/saas_similarity_pilot_review.csv --output backend/data/saas_similarity_pilot_human_reviewed.jsonl
```

The importer rejects blank/non-binary labels, missing reviewer/date, invalid URLs, self-pairs, duplicate unordered domain pairs, and datasets without both classes. Uncertain rows must be resolved or removed before import.

## Step 5 — Quality gate

From the repository root:

```bash
python backend/app/similarity_dataset_quality.py --data backend/data/saas_similarity_pilot_human_reviewed.jsonl --output backend/models/saas_similarity_pilot_quality_report.json --min-rows 30 --min-source-domains 5 --min-per-class 10
```

Review every error and warning. The quality gate is not a model-quality guarantee. Keep a separate untouched holdout for evaluation; do not train and evaluate on the same pairs.

## Pull-request workflow

- Keep this seed list and workflow in a reviewable PR.
- Do not commit actual labels until a human has reviewed them.
- Treat collected metadata and labeled examples as data artifacts; review them for accuracy and unintended sensitive content before sharing.
- Do not merge or deploy this work until the PRs and CI are reviewed and explicitly approved.
