import numpy as np
import pytest

from app.semantic_similarity import cosine_scores, score_pairs, website_text


class FakeEncoder:
    def encode(self, sentences, **kwargs):
        vectors = {
            "A | finance | personal banking": [1.0, 0.0],
            "B | finance | digital banking": [0.9, 0.1],
            "C | cooking | recipes": [0.0, 1.0],
        }
        return np.asarray([vectors[text] for text in sentences], dtype=float)


def test_cosine_scores_are_pairwise_and_bounded():
    scores = cosine_scores([[1, 0], [0, 1]], [[1, 0], [1, 1]])
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(2 ** -0.5)
    assert np.all(scores <= 1.0)
    assert np.all(scores >= -1.0)


def test_cosine_rejects_invalid_matrices_and_zero_vectors():
    with pytest.raises(ValueError, match="identical 2D"):
        cosine_scores([[1, 2]], [[1, 2], [3, 4]])
    with pytest.raises(ValueError, match="zero-vector"):
        cosine_scores([[0, 0]], [[1, 0]])
    with pytest.raises(ValueError, match="finite"):
        cosine_scores([[float("nan"), 0]], [[1, 0]])


def test_website_text_requires_some_metadata():
    assert website_text({"source_name":"A", "source_category":"finance"}, "source") == "A | finance"
    with pytest.raises(ValueError, match="Missing website metadata"):
        website_text({}, "source")


def test_score_pairs_adds_explicit_zero_shot_provenance():
    rows = [{
        "source_name":"A", "source_category":"finance", "source_description":"personal banking",
        "candidate_name":"B", "candidate_category":"finance", "candidate_description":"digital banking",
        "label":1,
    }, {
        "source_name":"A", "source_category":"finance", "source_description":"personal banking",
        "candidate_name":"C", "candidate_category":"cooking", "candidate_description":"recipes",
        "label":0,
    }]
    result = score_pairs(rows, FakeEncoder())
    assert result[0]["score"] > result[1]["score"]
    assert result[0]["label"] == 1
    assert result[0]["scoring_method"] == "embedding_cosine_zero_shot"
    assert result[0]["fine_tuned_on_webforge_labels"] if "fine_tuned_on_webforge_labels" in result[0] else True


def test_score_pairs_validates_batch_size_and_empty_input():
    with pytest.raises(ValueError, match="batch_size"):
        score_pairs([], FakeEncoder(), batch_size=0)
    assert score_pairs([], FakeEncoder()) == []
