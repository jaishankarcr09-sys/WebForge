from types import SimpleNamespace

from requests.structures import CaseInsensitiveDict

from app import site_scan


class RawHeaders:
    def get_all(self, name):
        return []


def response(url, status=200, headers=None, history=None):
    return SimpleNamespace(
        status_code=status,
        url=url,
        headers=CaseInsensitiveDict(headers or {"content-type": "text/html; charset=utf-8"}),
        encoding="utf-8",
        history=history or [],
        raw=SimpleNamespace(headers=RawHeaders()),
    )


def test_root_redirected_to_login_is_not_misreported_as_verified_homepage():
    page = response("https://example.com/login")
    parsed = site_scan.parse_page(
        "https://example.com/", page,
        b"<html><head><title>Sign in</title></head><body><form></form></body></html>",
        40, 10,
    )

    assert parsed.analysis_eligible is False
    assert "redirected to an authentication page" in parsed.crawl_note
    assert parsed.final_url == "https://example.com/login"


def test_direct_login_page_can_still_be_audited():
    page = response("https://example.com/login")
    parsed = site_scan.parse_page(
        "https://example.com/login", page,
        b"<html><head><title>Sign in</title></head><body><form></form></body></html>",
        40, 10,
    )

    assert parsed.analysis_eligible is True


def test_blocked_robots_and_sitemap_are_reported_as_unverified(monkeypatch):
    root = "https://example.com/"
    robots_url = "https://example.com/robots.txt"
    sitemap_url = "https://example.com/sitemap.xml"

    def fake_fetch(session, url, timeout=15):
        if url == robots_url:
            return response(url, 403, {"content-type": "text/plain"}), b"blocked", 10, 5
        if url == sitemap_url:
            return response(url, 403, {"content-type": "text/plain"}), b"blocked", 10, 5
        if url == root:
            return response(url), b"<html><head><title>Example</title></head><body>Public page</body></html>", 10, 5
        raise AssertionError(f"Unexpected URL fetched: {url}")

    monkeypatch.setattr(site_scan, "safe_url", lambda url: url)
    monkeypatch.setattr(site_scan, "fetch", fake_fetch)

    result = site_scan.crawl(root, page_limit=1)

    assert result.robots_present is False
    assert result.sitemap_present is False
    assert result.robots_status == 403
    assert result.sitemap_status == 403
    reasons = " ".join(item["reason"] for item in result.crawl_warnings)
    assert "does not prove the file is absent" in reasons
    assert "does not prove that no sitemap exists" in reasons
    assert "confirmed missing" not in reasons


def test_confirmed_missing_robots_and_sitemap_are_distinguished(monkeypatch):
    root = "https://example.com/"
    robots_url = "https://example.com/robots.txt"
    sitemap_url = "https://example.com/sitemap.xml"

    def fake_fetch(session, url, timeout=15):
        if url in {robots_url, sitemap_url}:
            return response(url, 404, {"content-type": "text/plain"}), b"not found", 10, 5
        if url == root:
            return response(url), b"<html><head><title>Example</title></head><body>Public page</body></html>", 10, 5
        raise AssertionError(f"Unexpected URL fetched: {url}")

    monkeypatch.setattr(site_scan, "safe_url", lambda url: url)
    monkeypatch.setattr(site_scan, "fetch", fake_fetch)

    result = site_scan.crawl(root, page_limit=1)

    assert result.robots_status == 404
    assert result.sitemap_status == 404
    reasons = " ".join(item["reason"] for item in result.crawl_warnings)
    assert "robots.txt is confirmed missing" in reasons
    assert "server returned 404/410" in reasons
