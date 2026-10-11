import pytest

from app.similarity_service import model_status, rank_metadata


def test_status_fails_closed_without_configured_model(tmp_path):
    status = model_status(str(tmp_path / "missing.joblib"))
    assert status["status"] == "model_not_configured"
    assert status["model_artifact_exists"] is False


def test_rank_rejects_bad_payload_before_loading_model():
    with pytest.raises(ValueError, match="source.name is required"):
        rank_metadata({"source": {"name": ""}, "candidates": [{"name": "B"}]},
                      model_path="/does/not/exist.joblib")


def test_rank_requires_candidates():
    with pytest.raises(ValueError, match="non-empty list"):
        rank_metadata({"source": {"name": "A", "category": "retail"}, "candidates": []},
                      model_path="/does/not/exist.joblib")


def test_rank_caps_candidate_count():
    source = {"name": "Source", "category": "retail"}
    candidates = [{"name": f"Candidate {i}", "category": "retail"} for i in range(51)]
    with pytest.raises(ValueError, match="maximum of 50"):
        rank_metadata({"source": source, "candidates": candidates},
                      model_path="/does/not/exist.joblib")


def test_rank_returns_unavailable_without_artifact():
    payload = {
        "source": {"name": "Source", "category": "retail"},
        "candidates": [{"name": "Candidate", "category": "retail"}],
    }
    with pytest.raises(FileNotFoundError, match="not configured"):
        rank_metadata(payload, model_path="/does/not/exist.joblib")
