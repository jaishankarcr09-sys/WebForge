"""Compare a trained classical model and a semantic baseline on identical held-out pairs.

Input must be a human-labeled, held-out JSONL dataset. The script refuses to train
on that dataset and reports ranking metrics per source query. It does not pick a
production winner automatically.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from app.semantic_similarity import load_encoder, score_pairs
from app.similarity_model import load_model, score_pair
from app.similarity_ranking_metrics import ranking_metrics


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("Held-out dataset is empty.")
    required = ("source_url", "candidate_url", "source_name", "candidate_name", "label")
    seen_pairs: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Held-out row {index} must be a JSON object.")
        missing = [key for key in required if row.get(key) in (None, "")]
        if missing:
            raise ValueError(f"Held-out row {index} is missing required fields: {', '.join(missing)}")
        if row["label"] not in (0, 1, "0", "1") or isinstance(row["label"], bool):
            raise ValueError(f"Held-out row {index} must have binary label 0 or 1.")

        normalized_urls = []
        for field in ("source_url", "candidate_url"):
            value = str(row[field]).strip()
            parsed = urlparse(value)
            if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None):
                raise ValueError(
                    f"Held-out row {index} field {field} must be an absolute HTTP(S) URL "
                    "without embedded credentials."
                )
            normalized_urls.append(value.rstrip("/").lower())

        source_host = urlparse(normalized_urls[0]).hostname
        candidate_host = urlparse(normalized_urls[1]).hostname
        if source_host == candidate_host:
            raise ValueError(f"Held-out row {index} compares a website with itself (same hostname).")
        pair = tuple(sorted(normalized_urls))
        if pair in seen_pairs:
            raise ValueError(f"Held-out row {index} duplicates an earlier website pair.")
        seen_pairs.add(pair)


def compare_baselines(rows: list[dict[str, Any]], classical_model: dict[str, Any],
                      encoder: Any) -> dict[str, Any]:
    _validate_rows(rows)
    classical_rows = []
    for row in rows:
        item = dict(row)
        item["score"] = float(score_pair(classical_model, row, row))
        item["scoring_model"] = classical_model.get("model_version", "unknown_classical_model")
        item["scoring_method"] = "trained_classical_pair_classifier"
        classical_rows.append(item)
    semantic_rows = score_pairs(rows, encoder)
    return {
        "evaluation_protocol": "same_held_out_pairs_per_source_query",
        "pair_count": len(rows),
        "query_count": len({str(row["source_url"]).strip().rstrip("/").lower() for row in rows}),
        "training_performed_during_evaluation": False,
        "baselines": {
            "classical": {
                "model_version": classical_model.get("model_version", "unknown"),
                "ranking_metrics": ranking_metrics(classical_rows),
                "scored_pairs": classical_rows,
            },
            "semantic_zero_shot": {
                "model_version": "sentence-transformers/all-MiniLM-L6-v2",
                "ranking_metrics": ranking_metrics(semantic_rows),
                "scored_pairs": semantic_rows,
            },
        },
        "warning": "Use a final untouched and representative holdout. Incomplete relevance labels and candidate catalogues can bias ranking metrics. Do not interpret similarity scores as calibrated probabilities.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Human-labeled held-out JSONL pairs")
    parser.add_argument("--classical-model", required=True, help="Previously trained joblib artifact")
    parser.add_argument("--output", default="backend/models/baseline_comparison.json")
    parser.add_argument("--semantic-model", default="sentence-transformers/all-MiniLM-L6-v2")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    classical = load_model(args.classical_model)
    encoder = load_encoder(args.semantic_model)
    report = compare_baselines(rows, classical, encoder)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Print summary rather than duplicating every scored row in terminal output.
    print(json.dumps({
        "evaluation_protocol": report["evaluation_protocol"],
        "pair_count": report["pair_count"],
        "query_count": report["query_count"],
        "classical_metrics": report["baselines"]["classical"]["ranking_metrics"]["metrics"],
        "semantic_metrics": report["baselines"]["semantic_zero_shot"]["ranking_metrics"]["metrics"],
        "output": str(output),
        "warning": report["warning"],
    }, indent=2))


if __name__ == "__main__":
    main()
