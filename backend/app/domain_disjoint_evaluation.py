"""Evaluate similarity models on source domains held out from training.

Candidate websites may be shared across queries because the deployed use case ranks a
catalogue. Source/query domains are kept disjoint to test generalization to new target
websites. This still requires many reviewed source domains for meaningful metrics.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from app.similarity_model import _text, pair_features


def _normalized_host(value: Any, row_number: int, field: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if (parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None):
        raise ValueError(
            f"Evaluation row {row_number}: {field} must be an absolute HTTP(S) URL "
            "without embedded credentials."
        )
    return parsed.hostname.lower().rstrip(".").removeprefix("www.")


def _source_domain(row: dict[str, Any]) -> str:
    return _normalized_host(row.get("source_url"), 1, "source_url")


def _validate_records(records: list[dict[str, Any]]) -> None:
    seen_pairs: set[tuple[str, str]] = set()
    required = ("source_name", "candidate_name", "label", "source_url", "candidate_url")
    for index, row in enumerate(records, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Evaluation row {index} must be a JSON object.")
        missing = [field for field in required if row.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Evaluation row {index} is missing required fields: {', '.join(missing)}")
        label = row["label"]
        if isinstance(label, bool) or str(label).strip() not in {"0", "1"}:
            raise ValueError(f"Evaluation row {index} label must be 0 or 1.")
        source_host = _normalized_host(row["source_url"], index, "source_url")
        candidate_host = _normalized_host(row["candidate_url"], index, "candidate_url")
        if source_host == candidate_host:
            raise ValueError(f"Evaluation row {index} compares a website with itself (same hostname).")
        pair = tuple(sorted((source_host, candidate_host)))
        if pair in seen_pairs:
            raise ValueError(f"Evaluation row {index} duplicates an unordered domain pair.")
        seen_pairs.add(pair)


def _features(rows: list[dict[str, Any]], word: TfidfVectorizer,
              char: TfidfVectorizer) -> np.ndarray:
    return np.vstack([pair_features(row, row, word, char) for row in rows])


def benchmark_domain_disjoint(records: list[dict[str, Any]], random_state: int = 42) -> dict[str, Any]:
    if len(records) < 30:
        raise ValueError("At least 30 reviewed pairs are required for domain-disjoint evaluation.")
    _validate_records(records)
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("Evaluation needs both positive and negative reviewed pairs.")
    groups = np.asarray([_source_domain(row) for row in records])
    unique_groups = set(groups.tolist())
    if len(unique_groups) < 5:
        raise ValueError("At least five distinct source domains are required for a meaningful split.")

    splitter = GroupShuffleSplit(n_splits=20, test_size=0.25, random_state=random_state)
    chosen = None
    for train_idx, test_idx in splitter.split(np.zeros(len(records)), labels, groups):
        if set(labels[train_idx].tolist()) == {0, 1} and set(labels[test_idx].tolist()) == {0, 1}:
            chosen = (train_idx, test_idx)
            break
    if chosen is None:
        raise ValueError("Could not find a domain-disjoint split containing both classes; collect more reviewed pairs across domains.")

    train_idx, test_idx = chosen
    train_rows = [records[i] for i in train_idx]
    test_rows = [records[i] for i in test_idx]
    train_domains = set(groups[train_idx].tolist())
    test_domains = set(groups[test_idx].tolist())
    if train_domains & test_domains:
        raise AssertionError("Source-domain leakage detected.")

    texts = [_text(row, "source") for row in train_rows] + [_text(row, "candidate") for row in train_rows]
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=12000).fit(texts)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=18000).fit(texts)
    x_train = _features(train_rows, word, char)
    x_test = _features(test_rows, word, char)
    y_train, y_test = labels[train_idx], labels[test_idx]

    models = {
        "logistic_regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state),
        "random_forest": RandomForestClassifier(n_estimators=200, class_weight="balanced", min_samples_leaf=2, random_state=random_state),
        "extra_trees": ExtraTreesClassifier(n_estimators=200, class_weight="balanced", min_samples_leaf=2, random_state=random_state),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=100, l2_regularization=1.0, random_state=random_state),
        "rbf_svc": make_pipeline(StandardScaler(), SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=random_state)),
    }
    results = []
    for name, model in models.items():
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        scores = model.predict_proba(x_test)[:, 1]
        results.append({
            "algorithm": name,
            "accuracy": round(float(accuracy_score(y_test, predicted)), 4),
            "precision": round(float(precision_score(y_test, predicted, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, predicted, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, predicted, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, scores)), 4),
        })
    results.sort(key=lambda row: (row["f1"], row["roc_auc"]), reverse=True)
    return {
        "evaluation_protocol": "source_domain_disjoint_group_holdout",
        "train_pairs": len(train_idx),
        "test_pairs": len(test_idx),
        "train_source_domains": sorted(train_domains),
        "test_source_domains": sorted(test_domains),
        "source_domain_overlap": sorted(train_domains & test_domains),
        "algorithms": results,
        "provisional_leader": results[0]["algorithm"],
        "warning": "Results are meaningful only with sufficiently large, representative, independently reviewed labels. Candidate catalogues may overlap by design; source query domains do not overlap.",
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="backend/data/human_reviewed_similarity_pairs.jsonl")
    parser.add_argument("--output", default="backend/models/domain_disjoint_benchmark.json")
    args = parser.parse_args()
    rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = benchmark_domain_disjoint(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
