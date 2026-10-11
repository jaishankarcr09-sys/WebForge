import pytest

from app.domain_disjoint_evaluation import _source_domain, benchmark_domain_disjoint


def test_source_domain_normalizes_www():
    assert _source_domain({"source_url":"https://www.example.com/path"}) == "example.com"


def test_domain_evaluation_requires_urls():
    with pytest.raises(ValueError, match="source_url"):
        _source_domain({"source_name":"Example"})


def test_domain_evaluation_refuses_too_few_pairs():
    with pytest.raises(ValueError, match="At least 30"):
        benchmark_domain_disjoint([{"label":0}] * 10)


def test_domain_evaluation_requires_enough_domains():
    rows = [
        {"label":i%2, "source_url":f"https://domain{i%3}.example/",
         "source_name":"source text", "source_category":"tools", "source_description":"source tool",
         "candidate_name":f"candidate {i}", "candidate_category":"tools", "candidate_description":"candidate tool"}
        for i in range(40)
    ]
    with pytest.raises(ValueError, match="five distinct source domains"):
        benchmark_domain_disjoint(rows)
