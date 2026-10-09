from types import SimpleNamespace

from app import site_scan


def response(status):
    return SimpleNamespace(status_code=status)


def test_browser_fallback_is_not_used_for_normal_success(monkeypatch):
    normal = (response(200), b"<html>ok</html>", 12, 5)
    monkeypatch.setattr(site_scan, "fetch", lambda *args, **kwargs: normal)
    monkeypatch.setattr(
        site_scan, "_browser_fetch",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected browser fallback")),
    )

    assert site_scan._fetch_with_browser_fallback(object(), "https://example.com/") is normal


def test_browser_fallback_replaces_403_when_browser_gets_html(monkeypatch):
    blocked = (response(403), b"blocked", 12, 5)
    rendered = (response(200), b"<html><title>Rendered</title></html>", 800, 800)
    monkeypatch.setattr(site_scan, "fetch", lambda *args, **kwargs: blocked)
    monkeypatch.setattr(site_scan, "_browser_fetch", lambda *args, **kwargs: rendered)

    assert site_scan._fetch_with_browser_fallback(object(), "https://example.com/") is rendered


def test_browser_fallback_preserves_403_when_browser_is_also_blocked(monkeypatch):
    blocked = (response(403), b"blocked", 12, 5)
    still_blocked = (response(403), b"challenge", 800, 800)
    monkeypatch.setattr(site_scan, "fetch", lambda *args, **kwargs: blocked)
    monkeypatch.setattr(site_scan, "_browser_fetch", lambda *args, **kwargs: still_blocked)

    assert site_scan._fetch_with_browser_fallback(object(), "https://example.com/") is blocked


def test_browser_fallback_failure_keeps_original_response(monkeypatch):
    blocked = (response(403), b"blocked", 12, 5)
    monkeypatch.setattr(site_scan, "fetch", lambda *args, **kwargs: blocked)

    def fail(*args, **kwargs):
        raise RuntimeError("browser unavailable")

    monkeypatch.setattr(site_scan, "_browser_fetch", fail)
    assert site_scan._fetch_with_browser_fallback(object(), "https://example.com/") is blocked
