"""Ranking metrics for evaluating similar-website retrieval.

Rows represent source/candidate pairs with a binary human label and a model score.
Ranking metrics are computed within each source query, not across unrelated queries.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite.")
    return result


def ranking_metrics(rows: list[dict[str, Any]], *, k_values: tuple[int, ...] = (1, 3, 5, 10)) -> dict[str, Any]:
    """Calculate macro-averaged P@k, hit-rate@k, reciprocal rank, and nDCG@k.

    Required fields per row: source_url, candidate_url, label (0/1), score.
    Each source URL is one ranking query. Queries without a positive relevant
    candidate remain in the report but are excluded from MRR/nDCG averages,
    because those metrics are undefined when ideal DCG is zero.
    """
    if not rows:
        raise ValueError("At least one scored pair is required.")
    if not k_values or any(isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in k_values):
        raise ValueError("k_values must contain positive integers.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        source = str(row.get("source_url") or "").strip().rstrip("/").lower()
        candidate = str(row.get("candidate_url") or "").strip().rstrip("/").lower()
        if not source or not candidate:
            raise ValueError(f"Row {index} requires source_url and candidate_url.")
        if source == candidate:
            raise ValueError(f"Row {index} compares a website with itself.")
        label = row.get("label")
        if label not in (0, 1, "0", "1") or isinstance(label, bool):
            raise ValueError(f"Row {index} label must be binary 0 or 1.")
        score = _number(row.get("score"), f"Row {index} score")
        pair = (source, candidate)
        if pair in seen:
            raise ValueError(f"Duplicate source/candidate pair at row {index}.")
        seen.add(pair)
        groups[source].append({"candidate": candidate, "label": int(label), "score": score})

    if any(len({item["label"] for item in group}) < 2 for group in groups.values()):
        # Single-class queries are legitimate in production, so this is only noted below.
        pass

    per_query = []
    for source, items in sorted(groups.items()):
        # Stable tie-breaking makes reports reproducible.
        ranked = sorted(items, key=lambda item: (-item["score"], item["candidate"]))
        positives = sum(item["label"] for item in ranked)
        query_result: dict[str, Any] = {
            "source_url": source,
            "candidate_count": len(ranked),
            "relevant_count": positives,
            "has_relevant_candidate": bool(positives),
        }
        if positives:
            first_relevant = next(i for i, item in enumerate(ranked, start=1) if item["label"] == 1)
            query_result["reciprocal_rank"] = 1.0 / first_relevant
            ideal = sorted((item["label"] for item in ranked), reverse=True)
            for k in k_values:
                top = ranked[:k]
                precision = sum(item["label"] for item in top) / k
                hits = sum(item["label"] for item in top)
                dcg = sum(item["label"] / math.log2(rank + 1) for rank, item in enumerate(top, start=1))
                idcg = sum(ideal_label / math.log2(rank + 1)
                           for rank, ideal_label in enumerate(ideal[:k], start=1))
                query_result[f"precision_at_{k}"] = round(precision, 6)
                query_result[f"hit_rate_at_{k}"] = float(hits > 0)
                query_result[f"ndcg_at_{k}"] = round(dcg / idcg if idcg else 0.0, 6)
        else:
            query_result["reciprocal_rank"] = None
            for k in k_values:
                query_result[f"precision_at_{k}"] = round(
                    sum(item["label"] for item in ranked[:k]) / k, 6)
                query_result[f"hit_rate_at_{k}"] = 0.0
                query_result[f"ndcg_at_{k}"] = None
        per_query.append(query_result)

    evaluable = [item for item in per_query if item["has_relevant_candidate"]]
    metrics: dict[str, Any] = {
        "query_count": len(per_query),
        "queries_with_relevant_candidates": len(evaluable),
        "queries_without_relevant_candidates": len(per_query) - len(evaluable),
        "candidate_pair_count": len(rows),
        "macro_averaged_over_queries": True,
        "metrics": {},
        "per_query": per_query,
        "warning": "Ranking metrics depend on candidate catalogue coverage and human labels. Include a representative candidate set for each source query.",
    }
    for k in k_values:
        metrics["metrics"][f"precision_at_{k}"] = round(
            sum(item[f"precision_at_{k}"] for item in per_query) / len(per_query), 6)
        metrics["metrics"][f"hit_rate_at_{k}"] = round(
            sum(item[f"hit_rate_at_{k}"] for item in per_query) / len(per_query), 6)
        valid_ndcg = [item[f"ndcg_at_{k}"] for item in evaluable if item[f"ndcg_at_{k}"] is not None]
        metrics["metrics"][f"ndcg_at_{k}"] = round(sum(valid_ndcg) / len(valid_ndcg), 6) if valid_ndcg else None
    metrics["metrics"]["mean_reciprocal_rank"] = round(
        sum(item["reciprocal_rank"] for item in evaluable) / len(evaluable), 6) if evaluable else None
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="JSONL scored pair file")
    parser.add_argument("--output", default="backend/models/ranking_metrics.json")
    parser.add_argument("--k", default="1,3,5,10", help="Comma-separated positive cutoffs")
    args = parser.parse_args()
    try:
        k_values = tuple(sorted(set(int(value.strip()) for value in args.k.split(",") if value.strip())))
    except ValueError as exc:
        parser.error(f"Invalid --k: {exc}")
    rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = ranking_metrics(rows, k_values=k_values)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
