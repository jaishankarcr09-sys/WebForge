from app.site_intelligence import _host, _relevance


def test_host_normalizes_www_and_case():
    assert _host("https://WWW.Example.com/path") == "example.com"


def test_same_category_gets_higher_relevance():
    same, same_reason = _relevance("SaaS / Web App", "Workflow platform", "tools for teams", "SaaS / Web App")
    different, _ = _relevance("SaaS / Web App", "Cooking recipes", "food and recipes", "Blog / Publication")
    assert same > different
    assert "same website category" in same_reason


def test_relevance_score_is_bounded():
    score, reason = _relevance("E-commerce", "E-commerce platform alternatives", "software tool", "E-commerce")
    assert 0 <= score <= 100
    assert reason
