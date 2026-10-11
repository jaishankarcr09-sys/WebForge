"""Audit reviewed similarity-pair datasets before training or evaluation.

This is a fail-closed quality gate, not a model-quality guarantee. It checks schema,
labels, duplicate/self pairs, review provenance, domain coverage, and class balance.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _domain(value: Any) -> str:
    parsed = urlparse(str(value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return ""
    return parsed.hostname.lower().removeprefix("www.").rstrip(".")


def audit_dataset(rows: list[dict[str, Any]], *, min_rows: int = 30,
                  min_source_domains: int = 5, min_per_class: int = 10) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    label_counts: Counter[str] = Counter()
    source_domains: set[str] = set()
    candidate_domains: set[str] = set()
    exact_pairs: set[tuple[str, str]] = set()
    duplicate_pairs = 0
    self_pairs = 0
    missing_urls = 0
    missing_review_metadata = 0
    malformed_labels = 0

    if not rows:
        errors.append("Dataset is empty.")

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"Row {index} is not a JSON object.")
            continue
        label = row.get("label")
        if label not in (0, 1, "0", "1") or isinstance(label, bool):
            malformed_labels += 1
        else:
            label_counts[str(int(label))] += 1

        source = _domain(row.get("source_url"))
        candidate = _domain(row.get("candidate_url"))
        if not source or not candidate:
            missing_urls += 1
            continue
        source_domains.add(source)
        candidate_domains.add(candidate)
        if source == candidate:
            self_pairs += 1
        pair = tuple(sorted((str(row.get("source_url", "")).strip().rstrip("/").lower(),
                             str(row.get("candidate_url", "")).strip().rstrip("/").lower())))
        if pair in exact_pairs:
            duplicate_pairs += 1
        exact_pairs.add(pair)
        if not row.get("reviewer") or not row.get("reviewed_at"):
            missing_review_metadata += 1
        if row.get("review_status") not in (None, "reviewed", "human_reviewed"):
            errors.append(f"Row {index} has unexpected review_status {row.get('review_status')!r}.")

    if malformed_labels:
        errors.append(f"{malformed_labels} rows have missing or invalid binary labels (expected 0 or 1).")
    if missing_urls:
        errors.append(f"{missing_urls} rows are missing valid HTTP(S) source_url or candidate_url.")
    if self_pairs:
        errors.append(f"{self_pairs} rows compare a website with itself.")
    if duplicate_pairs:
        errors.append(f"{duplicate_pairs} duplicate unordered website pairs detected.")
    if missing_review_metadata:
        errors.append(f"{missing_review_metadata} rows lack reviewer or reviewed_at provenance.")

    if len(rows) < min_rows:
        warnings.append(f"Only {len(rows)} pairs; at least {min_rows} are recommended before benchmarking.")
    if len(source_domains) < min_source_domains:
        warnings.append(f"Only {len(source_domains)} distinct source domains; target is at least {min_source_domains}.")
    if set(label_counts) != {"0", "1"}:
        errors.append("Both positive (1) and negative (0) labels are required.")
    for label in ("0", "1"):
        if label_counts[label] < min_per_class:
            warnings.append(f"Class {label} has only {label_counts[label]} examples; target is at least {min_per_class}.")
    if rows and len(source_domains) < 2:
        warnings.append("Source-domain diversity is too low to estimate generalization reliably.")

    return {
        "status": "pass" if not errors else "fail",
        "rows": len(rows),
        "label_counts": {"0": label_counts["0"], "1": label_counts["1"]},
        "distinct_source_domains": len(source_domains),
        "distinct_candidate_domains": len(candidate_domains),
        "source_candidate_domain_overlap": len(source_domains & candidate_domains),
        "duplicate_unordered_pairs": duplicate_pairs,
        "self_pairs": self_pairs,
        "rows_missing_valid_urls": missing_urls,
        "rows_missing_review_provenance": missing_review_metadata,
        "errors": errors,
        "warnings": warnings,
        "interpretation": "Passing these checks does not prove labels are correct or that the model generalizes; use a domain-disjoint holdout and inspect representative examples.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="backend/data/human_reviewed_similarity_pairs.jsonl")
    parser.add_argument("--output", default="backend/models/dataset_quality_report.json")
    parser.add_argument("--min-rows", type=int, default=30)
    parser.add_argument("--min-source-domains", type=int, default=5)
    parser.add_argument("--min-per-class", type=int, default=10)
    args = parser.parse_args()
    if min(args.min_rows, args.min_source_domains, args.min_per_class) < 1:
        parser.error("quality thresholds must be positive integers")
    path = Path(args.data)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = audit_dataset(rows, min_rows=args.min_rows,
                           min_source_domains=args.min_source_domains,
                           min_per_class=args.min_per_class)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
