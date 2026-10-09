from types import SimpleNamespace

from app.analyzers import analyze


def make_site(page_or_pages):
    pages = page_or_pages if isinstance(page_or_pages, list) else [page_or_pages]
    return SimpleNamespace(
        pages=pages,
        robots_present=True,
        robots_allowed=True,
        sitemap_present=True,
        broken_links=[],
        root_url="https://example.com/",
    )


def test_http_200_bot_challenge_is_not_analyzed_as_real_page():
    page = SimpleNamespace(
        status=200,
        url="https://example.com/",
        analysis_eligible=False,
        crawl_note="Response resembles a bot challenge or access interstitial; HTML checks skipped.",
    )

    assert analyze(make_site(page)) == []


def test_non_html_success_response_is_not_analyzed_for_missing_h1():
    page = SimpleNamespace(
        status=200,
        url="https://example.com/document.pdf",
        analysis_eligible=False,
        crawl_note="Non-HTML response (application/pdf); HTML checks skipped.",
    )

    titles = [finding.title for finding in analyze(make_site(page))]
    assert "Missing H1 heading" not in titles
    assert "Missing page title" not in titles


def valid_page():
    return SimpleNamespace(
        status=200,
        url="https://example.com/",
        analysis_eligible=True,
        title="Example page with a sufficiently descriptive title",
        description="A description",
        canonical_count=1,
        canonical="https://example.com/",
        noindex=False,
        h1_count=0,
        headings=[],
        images=[],
        forms_without_labels=0,
        buttons_without_names=0,
        lang="en",
        viewport="width=device-width",
        og_title="Example",
        og_description="Description",
        json_ld=1,
        mixed_content=0,
        security_headers={},
        response_ms=100,
        ttfb_ms=100,
        html_bytes=1000,
        scripts=1,
    )


def test_valid_html_missing_h1_reports_page_url_and_evidence():
    findings = analyze(make_site(valid_page()))
    h1 = [finding for finding in findings if finding.title == "Missing H1 heading"]
    assert len(h1) == 1
    assert h1[0].page_url == "https://example.com/"
    assert h1[0].evidence == "H1 count: 0."


def test_duplicate_page_url_does_not_duplicate_findings_or_title_groups():
    findings = analyze(make_site([valid_page(), valid_page()]))
    h1 = [finding for finding in findings if finding.title == "Missing H1 heading"]
    duplicate_titles = [finding for finding in findings if finding.title == "Duplicate page titles"]
    assert len(h1) == 1
    assert duplicate_titles == []
