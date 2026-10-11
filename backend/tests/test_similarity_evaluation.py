import json
from pathlib import Path

import pytest

from app.similarity_evaluation import benchmark_models

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_compares_multiple_algorithms():
    rows = [json.loads(line) for line in (ROOT / "data/similarity_training_pairs.jsonl").read_text().splitlines() if line.strip()]
    report = benchmark_models(rows)
    names = {item["algorithm"] for item in report["algorithms"]}
    assert {"logistic_regression", "random_forest", "extra_trees", "hist_gradient_boosting", "rbf_svc"} <= names
    assert report["train_pairs"] + report["test_pairs"] == len(rows)
    assert all(0 <= item["f1"] <= 1 for item in report["algorithms"])
    assert "unseen domains held out" in report["warning"]


def test_benchmark_rejects_tiny_dataset():
    with pytest.raises(ValueError, match="At least 20"):
        benchmark_models([{"label": 0}] * 10)
