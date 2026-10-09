from types import SimpleNamespace

from app.analyzers import analyze
from app.full_analyzer import analyze as analyze_full
from app.site_scan import _is_xml_resource


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



def test_xml_sitemap_detected_even_if_server_claims_html():
    url = "https://example.com/jobs/sitemap.xml"
    assert _is_xml_resource(url, "text/html", b"<urlset><url></url></urlset>")


def test_xml_page_never_generates_html_findings_or_backend_size_findings():
    page = SimpleNamespace(
        status=200,
        url="https://example.com/sitemap.xml",
        final_url="https://example.com/sitemap.xml",
        analysis_eligible=False,
        crawl_note="XML/resource response (application/xml); HTML checks skipped.",
        title="",
        description="",
        canonical_count=0,
        canonical="",
        noindex=False,
        h1_count=0,
        headings=[],
        images=[],
        forms_without_labels=0,
        buttons_without_names=0,
        lang="",
        viewport="",
        og_title="",
        og_description="",
        json_ld=0,
        mixed_content=0,
        security_headers={},
        response_ms=100,
        ttfb_ms=100,
        html_bytes=700_000,
        scripts=0,
        redirect_count=0,
        content_encoding="",
        insecure_cookie_count=0,
    )
    site = make_site(page)
    findings = analyze_full(site)
    invalid_titles = {
        "Missing page title",
        "Missing meta description",
        "Missing H1 heading",
        "Missing viewport meta tag",
        "Incomplete social metadata",
        "No JSON-LD structured data detected",
        "Large HTML document",
        "Compression signal missing",
    }
    assert not invalid_titles.intersection({finding.title for finding in findings})
