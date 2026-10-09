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
