# SaaS Similarity V4 — Review CSV Consistency Audit

Audit date: 2026-10-13  
Branch: `data/saas-similarity-expansion-v4`

## Scope

- `backend/data/saas_similarity_pilot_v4_user_review_decisions.csv` — review-decision history
- `backend/data/saas_similarity_pilot_review_v4.csv` — 66-pair baseline review queue
- `backend/data/saas_similarity_pilot_v4_canonical.csv` — canonical one-row-per-pair dataset
- `backend/data/similarity_training_pairs.jsonl` — checked only to confirm it remains unchanged; not edited

## Current verified status

- User-decision history rows (excluding header): **83**
- Unique unordered product pairs in the decision history: **66**
- Baseline review queue pairs: **66**
- Canonical dataset rows: **66**, representing **66 unique unordered pairs**
- Baseline pairs covered by the canonical dataset: **66 of 66**
- Missing baseline decisions: **0**
- Duplicate product-pair groups in the history: **17**
- Conflicting labels within duplicate product-pair groups: **0**
- Malformed/incomplete decision rows found by the audit checks: **0**
- Reused `pair_id` identifiers across different product pairs: **15 IDs**
- Canonical label distribution: **62 Label 0**, **4 Label 1**
- Training JSONL: **32 lines**, unchanged

The two previously missing decisions have now been explicitly recorded:
- Basecamp vs HubSpot — Label 0
- Basecamp vs Salesforce — Label 0

## Canonical dataset

The canonical file is `backend/data/saas_similarity_pilot_v4_canonical.csv`. It contains one row per normalized unordered product pair, keeps the latest explicit user decision, and retains provenance through source pair IDs, source-row count, and baseline pair ID/status.

Use the normalized unordered product pair as the deduplication key. Do not treat `pair_id` as globally unique.

## Duplicate product pairs

The history contains duplicate entries for these 17 unordered pairs. Each duplicate group has matching labels; no label conflicts were found:

1. HubSpot vs Salesforce — Label 1
2. Zendesk vs Intercom — Label 1
3. Vercel vs Netlify — Label 1
4. Miro vs Figma — Label 0
5. Miro vs Airtable — Label 0
6. HubSpot vs Zendesk — Label 0
7. Vercel vs Sentry — Label 0
8. Netlify vs Sentry — Label 0
9. Airtable vs Basecamp — Label 0
10. Salesforce vs Intercom — Label 0
11. HubSpot vs Intercom — Label 0
12. Figma vs Vercel — Label 0
13. Figma vs Airtable — Label 0
14. Airtable vs HubSpot — Label 0
15. Salesforce vs Zendesk — Label 0
16. HubSpot vs Vercel — Label 0
17. Salesforce vs Sentry — Label 0

Preserve the raw decision history, including duplicate rows. Use the canonical CSV for one-row-per-pair downstream review and analysis.

## Label–rationale consistency

- The three previously identified label–rationale contradictions were corrected in commit `9265e5fa47129b7137ada90196c2b9ee097fbb30`.
- HubSpot vs Salesforce uses Label 1 with a rationale describing overlapping CRM/sales capabilities.
- HubSpot vs Intercom and Salesforce vs Intercom use Label 0 with rationales distinguishing CRM/sales from customer messaging/support.
- Basecamp vs HubSpot and Basecamp vs Salesforce are now explicitly recorded as Label 0 with rationales explaining their different primary problems.
- No remaining obvious label–rationale contradictions were detected by the text consistency check. This is a consistency check, not independent product-domain ground truth.

## Identifier quality

The `pair_id` field is not globally unique: **15 identifiers are reused across different product pairs**, because earlier review IDs and later batch IDs overlapped. Do not use `pair_id` alone as a primary key. Use the normalized unordered product pair as the deduplication key, while retaining original IDs as source-history metadata.

## Recommended next steps

1. Treat the canonical CSV as the reviewed one-row-per-pair representation, while preserving the decision-history CSV as history.
2. If preparing training data in a later, explicitly approved step, validate against the canonical labels and rationale; do not assume that this audit changed training data.
3. Keep assistant proposals distinct from user-confirmed decisions.

## Scope / safety

This audit-report refresh updates **only this Markdown report**. It does not merge PR #50, deploy services, or modify `backend/data/similarity_training_pairs.jsonl`.
