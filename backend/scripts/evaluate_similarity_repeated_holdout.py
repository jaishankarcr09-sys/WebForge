
"""Repeated source-domain-disjoint evaluation for WebForge similarity models.

This is a research diagnostic, not a production-training script.
Candidate domains may overlap by design; source domains must not overlap
between train and test within each split.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean, stdev

import numpy as np
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain_disjoint_evaluation import (  # noqa: E402
    _features,
    _source_domain,
    _validate_records,
)
from app.similarity_model import _text  # noqa: E402


METRICS = ("accuracy", "precision", "recall", "f1", "roc_auc")


def _make_models(seed: int) -> dict:
    return {
        "logistic_regression": LogisticRegression(
            class_weight="balanced", max_iter=1000, random_state=seed
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced",
            min_samples_leaf=2, random_state=seed,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=200, class_weight="balanced",
            min_samples_leaf=2, random_state=seed,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=100, l2_regularization=1.0, random_state=seed
        ),
        "rbf_svc": make_pipeline(
            StandardScaler(),
            SVC(
                C=1.0, kernel="rbf", probability=True,
                class_weight="balanced", random_state=seed,
            ),
        ),
    }


def evaluate_repeated_holdouts(
    records: list[dict],
    n_splits: int = 100,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict:
    if n_splits < 1:
        raise ValueError("n_splits must be at least 1.")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")
    if len(records) < 30:
        raise ValueError("At least 30 pairs are required for this diagnostic.")

    _validate_records(records)
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    if set(labels.tolist()) != {0, 1}:
        raise ValueError("Evaluation requires both label classes.")

    groups = np.asarray([_source_domain(row) for row in records])
    if len(set(groups.tolist())) < 5:
        raise ValueError("At least five distinct source domains are required.")

    splitter = GroupShuffleSplit(
        n_splits=n_splits,
        test_size=test_size,
        random_state=random_state,
    )

    per_model = {}
    successful_splits = []
    skipped_splits = 0

    for split_number, (train_idx, test_idx) in enumerate(
        splitter.split(np.zeros(len(records)), labels, groups), start=1
    ):
        y_train, y_test = labels[train_idx], labels[test_idx]

        # ROC-AUC and the classification metrics need both classes.
        if set(y_train.tolist()) != {0, 1} or set(y_test.tolist()) != {0, 1}:
            skipped_splits += 1
            continue

        train_domains = set(groups[train_idx].tolist())
        test_domains = set(groups[test_idx].tolist())
        if train_domains & test_domains:
            raise AssertionError("Source-domain leakage detected.")

        train_rows = [records[i] for i in train_idx]
        test_rows = [records[i] for i in test_idx]

        # Fit all text preprocessing on this split's training partition only.
        texts = [
            _text(row, prefix)
            for row in train_rows
            for prefix in ("source", "candidate")
        ]
        try:
            word = TfidfVectorizer(
                ngram_range=(1, 2), sublinear_tf=True, max_features=12000
            ).fit(texts)
            char = TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), max_features=18000
            ).fit(texts)
        except ValueError:
            skipped_splits += 1
            continue

        x_train = _features(train_rows, word, char)
        x_test = _features(test_rows, word, char)

        split_results = {}
        for name, model in _make_models(random_state + split_number).items():
            model.fit(x_train, y_train)
            predicted = model.predict(x_test)
            scores = model.predict_proba(x_test)[:, 1]

            metrics = {
                "accuracy": accuracy_score(y_test, predicted),
                "precision": precision_score(
                    y_test, predicted, zero_division=0
                ),
                "recall": recall_score(
                    y_test, predicted, zero_division=0
                ),
                "f1": f1_score(y_test, predicted, zero_division=0),
                "roc_auc": roc_auc_score(y_test, scores),
            }
            split_results[name] = {
                key: float(value) for key, value in metrics.items()
            }
            per_model.setdefault(name, []).append(split_results[name])

        successful_splits.append({
            "split": split_number,
            "train_pairs": len(train_idx),
            "test_pairs": len(test_idx),
            "train_positive_pairs": int(y_train.sum()),
            "test_positive_pairs": int(y_test.sum()),
            "train_source_domains": sorted(train_domains),
            "test_source_domains": sorted(test_domains),
            "source_domain_overlap": [],
            "algorithms": split_results,
        })

    if not successful_splits:
        raise ValueError(
            "No valid splits contained both classes in train and test. "
            "Collect more reviewed pairs across source domains."
        )

    summary = []
    for name, results in per_model.items():
        row = {"algorithm": name, "successful_splits": len(results)}
        for metric in METRICS:
            values = [result[metric] for result in results]
            row[f"{metric}_mean"] = round(mean(values), 4)
            row[f"{metric}_std"] = round(stdev(values), 4) if len(values) > 1 else 0.0
            row[f"{metric}_min"] = round(min(values), 4)
            row[f"{metric}_max"] = round(max(values), 4)
        summary.append(row)

    summary.sort(
        key=lambda row: (row["f1_mean"], row["roc_auc_mean"]), reverse=True
    )

    return {
        "evaluation_protocol": "repeated_source_domain_disjoint_group_holdout",
        "requested_splits": n_splits,
        "successful_splits": len(successful_splits),
        "skipped_splits": skipped_splits,
        "test_size": test_size,
        "random_state": random_state,
        "total_pairs": len(records),
        "label_counts": {
            "0": int((labels == 0).sum()),
            "1": int((labels == 1).sum()),
        },
        "models": summary,
        "split_details": successful_splits,
        "warning": (
            "Exploratory results only. Repeated holdouts may reuse domains and "
            "test examples, so split scores are not independent. Results require "
            "larger, representative, independently reviewed labels. Candidate "
            "domains may overlap by design; source domains do not overlap within "
            "any individual split."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data",
        default="backend/data/saas_similarity_pilot_combined.jsonl",
    )
    parser.add_argument(
        "--output",
        default="backend/models/saas_similarity_repeated_holdout.json",
    )
    parser.add_argument("--splits", type=int, default=100)
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data_path = Path(args.data)
    rows = [
        json.loads(line)
        for line in data_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = evaluate_repeated_holdouts(
        rows,
        n_splits=args.splits,
        test_size=args.test_size,
        random_state=args.seed,
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(output),
        "requested_splits": report["requested_splits"],
        "successful_splits": report["successful_splits"],
        "skipped_splits": report["skipped_splits"],
        "models": report["models"],
    }, indent=2))


if __name__ == "__main__":
    main()
