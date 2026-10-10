from types import SimpleNamespace

from requests.structures import CaseInsensitiveDict

from app import site_scan


class RawHeaders:
    def get_all(self, name):
        return []


def response(url, status=200, body_type="text/html; charset=utf-8"):
    return SimpleNamespace(
        status_code=status,
        url=url,
        headers=CaseInsensitiveDict({"content-type": body_type}),
        encoding="utf-8",
        history=[],
        raw=SimpleNamespace(headers=RawHeaders()),
    )


def test_same_origin_403_link_gets_bounded_browser_retry(monkeypatch):
    root = "https://example.com/"
    target = "https://example.com/pricing"
    root_body = b'<html><head><title>Example</title></head><body><a href="/pricing">Pricing</a></body></html>'
    target_body = b'<html><head><title>Pricing</title></head><body><h1>Plans</h1></body></html>'

    def fake_fetch(session, url, timeout=15):
        if url.endswith("/robots.txt") or url.endswith("/sitemap.xml"):
            return response(url, 404, "text/plain"), b"not found", 5, 2
        if url == root:
            return response(url), root_body, 10, 4
        if url == target:
            return response(url, 403), b"blocked", 8, 3
        raise AssertionError(f"Unexpected URL fetched: {url}")

    browser_calls = []

    def fake_browser(url, timeout=20):
        browser_calls.append((url, timeout))
        return response(url), target_body, 30, 25

    monkeypatch.setattr(site_scan, "safe_url", lambda url: url)
    monkeypatch.setattr(site_scan, "fetch", fake_fetch)
    monkeypatch.setattr(site_scan, "_browser_fetch", fake_browser)

    result = site_scan.crawl(root, page_limit=1)

    assert browser_calls == [(target, 8)]
    assert result.broken_links == []
    assert result.link_check_warnings == []


def test_browser_challenge_does_not_count_as_verified_link(monkeypatch):
    root = "https://example.com/"
    target = "https://example.com/pricing"
    root_body = b'<html><head><title>Example</title></head><body><a href="/pricing">Pricing</a></body></html>'

    def fake_fetch(session, url, timeout=15):
        if url.endswith("/robots.txt") or url.endswith("/sitemap.xml"):
            return response(url, 404, "text/plain"), b"not found", 5, 2
        if url == root:
            return response(url), root_body, 10, 4
        if url == target:
            return response(url, 403), b"blocked", 8, 3
        raise AssertionError(f"Unexpected URL fetched: {url}")

    challenge_body = b'<html><head><title>Attention Required</title></head><body>Verify you are human</body></html>'

    monkeypatch.setattr(site_scan, "safe_url", lambda url: url)
    monkeypatch.setattr(site_scan, "fetch", fake_fetch)
    monkeypatch.setattr(
        site_scan,
        "_browser_fetch",
        lambda url, timeout=20: (response(url), challenge_body, 30, 25),
    )

    result = site_scan.crawl(root, page_limit=1)

    assert result.broken_links == []
    assert len(result.link_check_warnings) == 1
    assert result.link_check_warnings[0]["status"] == 403
    assert "does not confirm that the link is broken" in result.link_check_warnings[0]["reason"]
