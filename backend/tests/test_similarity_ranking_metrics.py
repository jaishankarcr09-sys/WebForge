import pytest

from app.similarity_ranking_metrics import ranking_metrics


def pair(source, candidate, label, score):
    return {"source_url": source, "candidate_url": candidate, "label": label, "score": score}


def test_relevant_candidate_ranked_first_has_perfect_reciprocal_rank_and_ndcg():
    rows = [
        pair("https://source.example", "https://good.example", 1, 0.9),
        pair("https://source.example", "https://bad.example", 0, 0.1),
    ]
    report = ranking_metrics(rows, k_values=(1, 2))
    assert report["metrics"]["mean_reciprocal_rank"] == 1.0
    assert report["metrics"]["ndcg_at_1"] == 1.0
    assert report["metrics"]["hit_rate_at_1"] == 1.0


def test_relevant_candidate_ranked_second_penalizes_metrics():
    rows = [
        pair("https://source.example", "https://bad.example", 0, 0.9),
        pair("https://source.example", "https://good.example", 1, 0.1),
    ]
    report = ranking_metrics(rows, k_values=(1, 2))
    assert report["metrics"]["mean_reciprocal_rank"] == 0.5
    assert report["metrics"]["ndcg_at_1"] == 0.0
    assert report["metrics"]["ndcg_at_2"] < 1.0


def test_macro_averages_queries_not_all_pairs_together():
    rows = [
        pair("https://one.example", "https://a.example", 1, 0.9),
        pair("https://two.example", "https://b.example", 0, 0.9),
        pair("https://two.example", "https://c.example", 0, 0.8),
    ]
    report = ranking_metrics(rows, k_values=(1,))
    assert report["query_count"] == 2
    assert report["metrics"]["hit_rate_at_1"] == 0.5
    assert report["metrics"]["mean_reciprocal_rank"] == 1.0


def test_rejects_duplicate_pairs_and_nonfinite_scores():
    with pytest.raises(ValueError, match="Duplicate"):
        ranking_metrics([
            pair("https://s.example", "https://c.example", 1, 0.9),
            pair("https://s.example", "https://c.example", 0, 0.1),
        ])
    with pytest.raises(ValueError, match="finite"):
        ranking_metrics([pair("https://s.example", "https://c.example", 1, float("nan"))])


def test_rejects_self_pairs_and_bad_labels():
    with pytest.raises(ValueError, match="itself"):
        ranking_metrics([pair("https://s.example", "https://s.example", 1, 0.9)])
    with pytest.raises(ValueError, match="binary"):
        ranking_metrics([pair("https://s.example", "https://c.example", 2, 0.9)])


def test_queries_without_relevant_candidates_are_reported():
    rows = [
        pair("https://source.example", "https://candidate.example", 0, 0.1),
        pair("https://source2.example", "https://candidate2.example", 1, 0.9),
    ]
    report = ranking_metrics(rows, k_values=(1,))
    assert report["queries_without_relevant_candidates"] == 1
    assert report["metrics"]["ndcg_at_1"] == 1.0
