from app import browser_metrics


def test_measure_rejects_unsafe_target_before_launching_browser(monkeypatch):
    def reject(url):
        raise ValueError("private address")

    monkeypatch.setattr(browser_metrics, "safe_url", reject)
    monkeypatch.setattr(
        browser_metrics,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(AssertionError("browser must not launch")),
    )

    result = browser_metrics.measure("http://127.0.0.1/")

    assert result == {"available": False, "error": "ValueError"}


def test_measure_does_not_expose_network_exception_details(monkeypatch):
    monkeypatch.setattr(browser_metrics, "safe_url", lambda url: url)

    class FakePlaywright:
        def __enter__(self):
            raise RuntimeError("internal host and request details")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(browser_metrics, "sync_playwright", lambda: FakePlaywright())

    result = browser_metrics.measure("https://example.com/")

    assert result == {"available": False, "error": "RuntimeError"}
