# SaaS Similarity V4 — Review CSV Consistency Audit

Audit date: 2026-10-13  
Branch: `data/saas-similarity-expansion-v4`  
Scope:
- `backend/data/saas_similarity_pilot_v4_user_review_decisions.csv`
- `backend/data/saas_similarity_pilot_review_v4.csv`

## Summary

- User-decision CSV rows: **81**
- Unique unordered product pairs represented: **64**
- Baseline review queue pairs: **66**
- Duplicate product-pair groups: **17** (each duplicate group currently has the same label across its rows)
- Conflicting labels within duplicate product-pair groups: **0**
- Missing decisions relative to the baseline queue: **2**
- Malformed/incomplete decision rows (missing rationale, invalid label, or wrong review status/type): **0**
- Duplicate pair IDs reused across different product pairs: **15 IDs**

## Duplicate product pairs

The decision log contains duplicate entries for these 17 unordered product pairs. The duplicate entries have matching labels, so no label conflict was found, but the raw review log should be preserved as history rather than silently deleting prior user-confirmed rows.

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

## Missing decisions

The following pairs appear in the 66-pair baseline queue but do not have a user-confirmed decision row:

- Basecamp vs HubSpot
- Basecamp vs Salesforce

These remain **unreviewed**. Do not convert assistant proposals into user-confirmed decisions without explicit user approval.

## Label–rationale consistency

- The three previously identified contradictions were corrected in commit `9265e5fa47129b7137ada90196c2b9ee097fbb30`.
- The latest rows for HubSpot vs Salesforce use Label 1 with a rationale explaining overlapping CRM/sales capabilities.
- HubSpot vs Intercom and Salesforce vs Intercom use Label 0 with rationales distinguishing CRM/sales from customer messaging/support.
- No remaining obvious label–rationale contradictions were detected in this audit. This is a text consistency check, not independent product-domain ground truth.

## Identifier quality

The `pair_id` field is not globally unique: 15 identifiers are reused for different product pairs because earlier review IDs and later batch IDs overlapped. Do not use `pair_id` alone as a primary key. Use the normalized unordered product pair as the deduplication key, and preserve the original IDs as source-history metadata.

## Recommended next steps

1. Keep the existing user-decision CSV as the append-only review history; do not delete duplicate historical decisions.
2. Create a separate canonical dataset with one row per normalized unordered product pair, keeping the latest explicit user decision and retaining provenance to the source row(s).
3. Ask the user to decide the two missing Basecamp pairs.
4. Only after review, run training-data validation. This audit does not modify training pairs or runtime behavior.

## Scope / safety

This audit did not merge the pull request, deploy services, or modify `similarity_training_pairs.jsonl`.
