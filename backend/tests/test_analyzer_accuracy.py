from types import SimpleNamespace

from app.analyzers import analyze, finding


def test_http_403_does_not_create_html_seo_findings():
    blocked_page = SimpleNamespace(status=403, url="https://example.com/")
    site = SimpleNamespace(
        pages=[blocked_page],
        robots_present=True,
        robots_allowed=True,
        sitemap_present=True,
        broken_links=[],
        root_url="https://example.com/",
    )

    findings = analyze(site)
    titles = [item.title for item in findings]

    assert titles == ["HTTP error (403)"]
    assert "Missing meta description" not in titles
    assert "Missing H1 heading" not in titles
    assert "Page is marked noindex" not in titles


def test_low_severity_finding_does_not_receive_priority_100():
    item = finding(
        "SEO",
        "Title may be too short",
        "low",
        "Low severity example",
        "Review title",
        confidence=90,
        effort="low",
        dimension="seo",
    )

    assert item.priority < 50


def test_high_severity_finding_ranks_above_low_severity():
    low = finding("SEO", "Low", "low", "Low", "Review", confidence=100, effort="low")
    high = finding("Technical", "High", "high", "High", "Fix", confidence=100, effort="low")

    assert high.priority > low.priority


def test_sitewide_missing_files_are_not_reported_when_all_pages_are_blocked():
    blocked_page = SimpleNamespace(status=403, url="https://example.com/")
    site = SimpleNamespace(
        pages=[blocked_page],
        robots_present=False,
        robots_allowed=True,
        sitemap_present=False,
        broken_links=[],
        root_url="https://example.com/",
    )
    titles = [item.title for item in analyze(site)]
    assert "robots.txt not detected" not in titles
    assert "Sitemap not detected at common locations" not in titles


def test_known_domain_is_not_classified_from_hostname_when_crawler_is_blocked():
    from app.site_intelligence import classify

    site = SimpleNamespace(
        root_url="https://www.youtube.com/",
        pages=[SimpleNamespace(status=403, title="Forbidden", description="", headings=[])],
    )
    assert classify(site) == "Unknown / insufficient evidence"


def test_unknown_blocked_site_is_not_classified_from_error_page():
    from app.site_intelligence import classify

    site = SimpleNamespace(
        root_url="https://example.org/",
        pages=[SimpleNamespace(status=403, title="Just a moment", description="", headings=[])],
    )
    assert classify(site) == "Unknown / insufficient evidence"


def test_specific_content_signal_beats_generic_site_vocabulary():
    from app.site_intelligence import classify

    page = SimpleNamespace(
        status=200,
        title="Search the web",
        description="Find search results across the web",
        headings=[("h1", "Search anything")],
    )
    site = SimpleNamespace(root_url="https://example.org/", pages=[page])
    assert classify(site) == "Search Engine"


def test_feature_snapshot_ignores_blocked_error_pages():
    from app.site_intelligence import feature_snapshot

    page = SimpleNamespace(status=403, title="Forbidden", description="", headings=[])
    snapshot = feature_snapshot(SimpleNamespace(root_url="https://example.org/", pages=[page]))
    assert snapshot["pages_scanned"] == 0
    assert snapshot["h1_pages"] == 0
    assert snapshot["json_ld_pages"] == 0



def test_similar_sites_have_category_fallback_when_search_returns_nothing(monkeypatch):
    import app.site_intelligence as intelligence

    monkeypatch.setattr(intelligence, "_search", lambda query, limit=8: [])
    monkeypatch.setattr(
        intelligence,
        "crawl",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("curated entries should not be crawled")),
    )
    site = SimpleNamespace(
        root_url="https://www.youtube.com/",
        pages=[SimpleNamespace(status=403, title="Forbidden", description="", headings=[])],
    )

    results = intelligence.discover_similar(site, "Video / Media Platform", 3)

    assert [item["name"] for item in results] == ["Vimeo", "Dailymotion", "Twitch"]
    assert all(item["source"] == "WebForge curated baseline" for item in results)
    assert all(item["verification_status"] == "curated-reference" for item in results)
    assert all(item["url"] != site.root_url for item in results)


def test_napkin_category_gets_visual_tool_comparables_without_api(monkeypatch):
    import app.site_intelligence as intelligence

    monkeypatch.setattr(intelligence, "_search", lambda query, limit=8: [])
    site = SimpleNamespace(
        root_url="https://www.napkin.ai/",
        pages=[SimpleNamespace(status=403, title="Forbidden", description="", headings=[])],
    )

    results = intelligence.discover_similar(site, "AI Visual Communication Tool", 3)

    assert len(results) == 3
    assert {item["name"] for item in results} == {"Canva", "Miro", "Whimsical"}
    assert all(item["verification_status"] == "curated-reference" for item in results)
