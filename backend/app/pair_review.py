"""Build an unlabeled candidate-pair review queue from collected metadata.

Generated pairs deliberately have label=null. A human must review and assign 1 (similar)
or 0 (not similar) before a row is copied into the supervised training set.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path


def build_review_pairs(records: list[dict], max_pairs: int = 5000) -> list[dict]:
    eligible = [row for row in records if row.get("status") == "collected" and
                row.get("title") and row.get("url")]
    eligible.sort(key=lambda row: row["url"].lower())
    pairs = []
    seen_domains = set()
    for left, right in itertools.combinations(eligible, 2):
        left_host = (left.get("hostname") or "").lower()
        right_host = (right.get("hostname") or "").lower()
        if not left_host or not right_host or left_host == right_host:
            continue
        # Treat a domain pair as unordered so reversing URL order cannot create duplicates.
        key = tuple(sorted((left_host, right_host)))
        if key in seen_domains:
            continue
        seen_domains.add(key)
        pairs.append({
            "source_name": left.get("title", ""),
            "source_category": left.get("category", ""),
            "source_description": left.get("description", ""),
            "source_url": left.get("url", ""),
            "candidate_name": right.get("title", ""),
            "candidate_category": right.get("category", ""),
            "candidate_description": right.get("description", ""),
            "candidate_url": right.get("url", ""),
            "label": None,
            "review_status": "needs_human_label",
            "provenance": "public_metadata_pair_candidate",
        })
        if len(pairs) >= max_pairs:
            break
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="backend/data/public_site_metadata.jsonl")
    parser.add_argument("--output", default="backend/data/pairs_for_review.jsonl")
    parser.add_argument("--max-pairs", type=int, default=5000)
    args = parser.parse_args()
    if args.max_pairs < 1:
        raise SystemExit("--max-pairs must be positive.")
    rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = build_review_pairs(rows, args.max_pairs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in pairs), encoding="utf-8")
    print(json.dumps({"candidate_pairs_for_review": len(pairs), "labels_assigned_automatically": 0,
                      "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
