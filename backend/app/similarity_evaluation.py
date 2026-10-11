"""Compare classical ML rankers on a provisional stratified pair split.

This small seed-set benchmark is a pipeline smoke test, not production model selection.
For trustworthy metrics, use a larger reviewed dataset and a held-out-domain split.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from app.similarity_model import _text, pair_features


def build_features(records: list[dict[str, Any]], word: TfidfVectorizer,
                   char: TfidfVectorizer) -> np.ndarray:
    return np.vstack([pair_features(row, row, word, char) for row in records])


def benchmark_models(records: list[dict[str, Any]], random_state: int = 42) -> dict[str, Any]:
    if len(records) < 20:
        raise ValueError("At least 20 reviewed pairs are required for a provisional benchmark.")
    labels = np.asarray([int(row["label"]) for row in records], dtype=int)
    if set(labels.tolist()) != {0, 1} or min(np.bincount(labels)) < 4:
        raise ValueError("Benchmark needs at least four positive and four negative reviewed pairs.")

    indices = np.arange(len(records))
    train_idx, test_idx = train_test_split(
        indices, test_size=0.25, random_state=random_state, stratify=labels
    )
    train_rows = [records[i] for i in train_idx]
    test_rows = [records[i] for i in test_idx]
    train_labels, test_labels = labels[train_idx], labels[test_idx]

    train_texts = [_text(row, "source") for row in train_rows] + [_text(row, "candidate") for row in train_rows]
    word = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=12000).fit(train_texts)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=18000).fit(train_texts)
    x_train = build_features(train_rows, word, char)
    x_test = build_features(test_rows, word, char)

    models = {
        "logistic_regression": LogisticRegression(class_weight="balanced", max_iter=1000, random_state=random_state),
        "random_forest": RandomForestClassifier(n_estimators=200, class_weight="balanced", min_samples_leaf=2, random_state=random_state),
        "extra_trees": ExtraTreesClassifier(n_estimators=200, class_weight="balanced", min_samples_leaf=2, random_state=random_state),
        "hist_gradient_boosting": HistGradientBoostingClassifier(max_iter=100, l2_regularization=1.0, random_state=random_state),
        "rbf_svc": make_pipeline(StandardScaler(), SVC(C=1.0, kernel="rbf", probability=True, class_weight="balanced", random_state=random_state)),
    }
    results = []
    for name, model in models.items():
        model.fit(x_train, train_labels)
        prediction = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1]
        results.append({
            "algorithm": name,
            "accuracy": round(float(accuracy_score(test_labels, prediction)), 4),
            "precision": round(float(precision_score(test_labels, prediction, zero_division=0)), 4),
            "recall": round(float(recall_score(test_labels, prediction, zero_division=0)), 4),
            "f1": round(float(f1_score(test_labels, prediction, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(test_labels, probabilities)), 4),
        })
    results.sort(key=lambda row: (row["f1"], row["roc_auc"]), reverse=True)
    return {
        "benchmark_type": "provisional_stratified_pair_split",
        "train_pairs": len(train_idx),
        "test_pairs": len(test_idx),
        "algorithms": results,
        "selected_candidate": results[0]["algorithm"],
        "warning": "Do not use these small-seed results to claim production quality. Re-evaluate on a larger human-reviewed dataset with unseen domains held out.",
    }


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="backend/data/similarity_training_pairs.jsonl")
    parser.add_argument("--output", default="backend/models/similarity_benchmark.json")
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = benchmark_models(records)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
