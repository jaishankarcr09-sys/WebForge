"""Repeated evaluation with both products' domains held out by partition.

Only pairs whose source and candidate domains both belong to the same partition are
used. Cross-partition pairs are excluded, so a domain cannot appear in training and
test under opposite roles. This is intentionally stricter and can produce small test
sets; repeated splits are not independent experiments.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import ShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from app.domain_disjoint_evaluation import _normalized_host, _validate_records
from app.similarity_model import _text, pair_features


def _row_domains(row: dict[str, Any], row_number: int = 1) -> tuple[str, str]:
    return (
        _normalized_host(row.get("source_url"), row_number, "source_url"),
        _normalized_host(row.get("candidate_url"), row_number, "candidate_url"),
    )


def partition_pair_indices(
    records: list[dict[str, Any]],
    train_domains: set[str],
    test_domains: set[str],
) -> tuple[list[int], list[int], list[int]]:
    """Return train, test, and excluded cross-partition pair indices."""
    if train_domains & test_domains:
        raise ValueError("Training and test domain sets must be disjoint.")

    train_indices: list[int] = []
    test_indices: list[int] = []
    excluded_indices: list[int] = []
    for index, row in enumerate(records):
        source_domain, candidate_domain = _row_domains(row, index + 1)
        if source_domain in train_domains and candidate_domain in train_domains:
            train_indices.append(index)
        elif source_domain in test_domains and candidate_domain in test_domains:
            test_indices.append(index)
        else:
            # A row is excluded unless both endpoints belong to one partition.
            excluded_indices.append(index)
    return train_indices, test_indices, excluded_indices


def build_strict_splits(
    records: list[dict[str, Any]],
    n_splits: int = 100,
    test_size: float = 0.25,
    random_state: int = 42,
) -> list[dict[str, Any]]:
    """Build viable domain-disjoint splits, excluding cross-partition pairs."""
    if len(records) < 30:
        raise ValueError("At least 30 reviewed pairs are required for strict evaluation.")
    if n_splits < 1:
        raise ValueError("n_splits must be at least 1.")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    _validate_records(records)
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("Evaluation needs both positive and negative reviewed pairs.")

    row_domains = [_row_domains(row, i + 1) for i, row in enumerate(records)]
    domains = sorted({domain for pair in row_domains for domain in pair})
    if len(domains) < 6:
        raise ValueError("At least six distinct domains are required for strict evaluation.")

    splitter = ShuffleSplit(n_splits=n_splits, test_size=test_size, random_state=random_state)
    viable: list[dict[str, Any]] = []
    for split_number, (train_domain_idx, test_domain_idx) in enumerate(
        splitter.split(np.asarray(domains)), start=1
    ):
        train_domains = {domains[i] for i in train_domain_idx}
        test_domains = {domains[i] for i in test_domain_idx}
        train_idx, test_idx, excluded_idx = partition_pair_indices(
            records, train_domains, test_domains
        )
        y_train = labels[train_idx]
        y_test = labels[test_idx]
        if set(y_train.tolist()) != {0, 1} or set(y_test.tolist()) != {0, 1}:
            continue
        # Explicit invariant: neither endpoint domain in one partition appears in the other.
        train_hosts = {
            domain for i in train_idx for domain in row_domains[i]
        }
        test_hosts = {
            domain for i in test_idx for domain in row_domains[i]
        }
        if train_hosts & test_hosts:
            raise AssertionError("Strict domain leakage detected.")
        viable.append({
            "split": split_number,
            "train_indices": train_idx,
            "test_indices": test_idx,
            "excluded_indices": excluded_idx,
            "train_domains": sorted(train_domains),
            "test_domains": sorted(test_domains),
        })
    if not viable:
        raise ValueError(
            "No strict split contains both labels in train and test. Collect more reviewed "
            "pairs across domains before evaluating."
        )
    return viable


def _features(rows: list[dict[str, Any]], word: TfidfVectorizer,
              char: TfidfVectorizer) -> np.ndarray:
    return np.vstack([pair_features(row, row, word, char) for row in rows])


def _models(random_state: int) -> dict[str, Any]:
    return {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=random_state
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", min_samples_leaf=2,
            random_state=random_state,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=200, class_weight="balanced", min_samples_leaf=2,
            random_state=random_state,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=100, l2_regularization=1.0, random_state=random_state
        ),
        "rbf_svc": make_pipeline(
            StandardScaler(),
            SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced",
                random_state=random_state),
        ),
    }


def evaluate_strict_domain_disjoint(
    records: list[dict[str, Any]],
    n_splits: int = 100,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict[str, Any]:
    """Evaluate classifiers using pairs wholly contained in disjoint domain sets."""
    splits = build_strict_splits(records, n_splits, test_size, random_state)
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    per_model: dict[str, list[dict[str, Any]]] = {}
    split_details = []

    for split in splits:
        train_idx = split["train_indices"]
        test_idx = split["test_indices"]
        train_rows = [records[i] for i in train_idx]
        test_rows = [records[i] for i in test_idx]

        # Fit vectorizers on training rows only. Test text never enters vocabulary fitting.
        train_texts = (
            [_text(row, "source") for row in train_rows]
            + [_text(row, "candidate") for row in train_rows]
        )
        word = TfidfVectorizer(
            ngram_range=(1, 2), sublinear_tf=True, max_features=12000
        ).fit(train_texts)
        char = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), max_features=18000
        ).fit(train_texts)
        x_train = _features(train_rows, word, char)
        x_test = _features(test_rows, word, char)
        y_train, y_test = labels[train_idx], labels[test_idx]

        counts = {
            "train_pairs": len(train_idx),
            "test_pairs": len(test_idx),
            "excluded_cross_partition_pairs": len(split["excluded_indices"]),
            "train_positive": int(y_train.sum()),
            "train_negative": int((y_train == 0).sum()),
            "test_positive": int(y_test.sum()),
            "test_negative": int((y_test == 0).sum()),
        }
        split_details.append({
            "split": split["split"],
            **counts,
            "train_domains": split["train_domains"],
            "test_domains": split["test_domains"],
            "domain_overlap": sorted(set(split["train_domains"]) & set(split["test_domains"])),
        })

        for name, model in _models(random_state).items():
            model.fit(x_train, y_train)
            predicted = model.predict(x_test)
            scores = model.predict_proba(x_test)[:, 1]
            metrics = {
                "accuracy": float(accuracy_score(y_test, predicted)),
                "precision": float(precision_score(y_test, predicted, zero_division=0)),
                "recall": float(recall_score(y_test, predicted, zero_division=0)),
                "f1": float(f1_score(y_test, predicted, zero_division=0)),
                "roc_auc": float(roc_auc_score(y_test, scores)),
            }
            per_model.setdefault(name, []).append(metrics)

    summary = []
    for name, observations in per_model.items():
        summary.append({
            "algorithm": name,
            "successful_splits": len(observations),
            "metrics": {
                metric: {
                    "mean": round(mean(row[metric] for row in observations), 4),
                    "population_std": round(pstdev(row[metric] for row in observations), 4),
                }
                for metric in ("accuracy", "precision", "recall", "f1", "roc_auc")
            },
        })

    return {
        "evaluation_protocol": "strict_both_endpoint_domain_disjoint_repeated_holdout",
        "dataset_rows": len(records),
        "unique_domains": len({d for row in records for d in _row_domains(row)}),
        "requested_splits": n_splits,
        "successful_splits": len(splits),
        "test_size_fraction_of_domains": test_size,
        "random_state": random_state,
        "algorithms": summary,
        "split_details": split_details,
        "warning": (
            "Exploratory only. Splits reuse the same small set of domains and pairs and are not "
            "independent experiments. Test sets may be tiny or class-imbalanced. Labels should "
            "be independently reviewed before model selection or deployment. Cross-partition "
            "pairs are excluded; only pairs with both endpoints in one partition are evaluated."
        ),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", default="backend/data/saas_similarity_pilot_combined.jsonl"
    )
    parser.add_argument(
        "--output", default="backend/models/strict_domain_disjoint_benchmark.json"
    )
    parser.add_argument("--splits", type=int, default=100)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = [
        json.loads(line)
        for line in Path(args.data).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = evaluate_strict_domain_disjoint(
        records, n_splits=args.splits, test_size=args.test_size, random_state=args.seed
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
