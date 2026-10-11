import json
from pathlib import Path

from app.similarity_model import load_model, rank_candidates, train_model

ROOT = Path(__file__).resolve().parents[1]


def test_seed_dataset_has_both_labels_and_provenance():
    rows = [json.loads(line) for line in (ROOT / "data/similarity_training_pairs.jsonl").read_text().splitlines() if line.strip()]
    assert len(rows) >= 20
    assert {row["label"] for row in rows} == {0, 1}
    assert all(row.get("provenance") == "curated_seed" for row in rows)


def test_model_trains_saves_loads_and_ranks(tmp_path):
    rows = [json.loads(line) for line in (ROOT / "data/similarity_training_pairs.jsonl").read_text().splitlines() if line.strip()]
    artifact_path = tmp_path / "similarity.joblib"
    report = train_model(rows, artifact_path)
    model = load_model(artifact_path)
    source = {"source_name": "Shopify", "source_category": "ecommerce platform",
              "source_description": "Online store builder product catalog checkout payments inventory"}
    candidates = [
        {"candidate_name": "BigCommerce", "candidate_category": "ecommerce platform",
         "candidate_description": "Online stores catalog checkout payments inventory"},
        {"candidate_name": "Spotify", "candidate_category": "music streaming",
         "candidate_description": "Music streaming playlists podcasts"}
    ]
    ranked = rank_candidates(model, source, candidates)
    assert report["training_rows"] == len(rows)
    assert artifact_path.exists()
    assert ranked[0]["candidate_name"] == "BigCommerce"
    assert all(row["similarity_model_version"] == "webforge-similarity-baseline-1" for row in ranked)


def test_training_rejects_single_class(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="both similar"):
        train_model([{"source_name":"a","source_category":"x","source_description":"x",
                      "candidate_name":"b","candidate_category":"y","candidate_description":"y","label":1}] * 8,
                    tmp_path / "bad.joblib")
