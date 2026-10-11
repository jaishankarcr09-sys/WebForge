import pytest

from app.compare_similarity_baselines import _validate_rows, compare_baselines


def row(source, candidate, label):
    return {
        "source_url": source, "candidate_url": candidate,
        "source_name": "Source site", "source_category": "education",
        "source_description": "online learning courses",
        "candidate_name": "Candidate site", "candidate_category": "education",
        "candidate_description": "online learning courses", "label": label,
    }


class FakeClassical:
    def get(self, key, default=None):
        return "test-classical" if key == "model_version" else default


class FakeEncoder:
    def encode(self, texts, **kwargs):
        # identical descriptions should have higher similarity than unrelated descriptions
        return [[1.0, 0.0] if "online learning courses" in text else [0.0, 1.0] for text in texts]


def test_validation_requires_urls_names_and_binary_labels():
    with pytest.raises(ValueError, match="missing required fields"):
        _validate_rows([{"label": 1}])
    with pytest.raises(ValueError, match="binary"):
        _validate_rows([row("https://s.example", "https://c.example", 3)])


def test_validation_rejects_empty_data():
    with pytest.raises(ValueError, match="empty"):
        _validate_rows([])


def test_compare_runs_both_rankers_on_same_heldout_pairs(monkeypatch):
    import app.compare_similarity_baselines as module

    monkeypatch.setattr(module, "score_pair", lambda model, source, candidate: 0.8 if candidate["candidate_name"] == "Candidate site" else 0.2)
    monkeypatch.setattr(module, "score_pairs", lambda rows, encoder: [
        {**row, "score": 0.9 if row["candidate_category"] == "education" else 0.1}
        for row in rows
    ])
    rows = [
        row("https://s1.example", "https://c1.example", 1),
        row("https://s1.example", "https://c2.example", 0),
        row("https://s2.example", "https://c3.example", 1),
        row("https://s2.example", "https://c4.example", 0),
    ]
    for i, item in enumerate(rows):
        item["candidate_name"] = f"Candidate {i}"
        item["candidate_description"] = "online learning courses" if item["label"] else "unrelated recipes"
    report = module.compare_baselines(rows, {"model_version": "classical-test"}, FakeEncoder())
    assert report["training_performed_during_evaluation"] is False
    assert report["pair_count"] == 4
    assert set(report["baselines"]) == {"classical", "semantic_zero_shot"}
    assert "ndcg_at_5" in report["baselines"]["classical"]["ranking_metrics"]["metrics"]
