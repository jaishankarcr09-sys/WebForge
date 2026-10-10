from __future__ import annotations

from playwright.sync_api import sync_playwright

from .site_scan import safe_url


def measure(url: str) -> dict:
    try:
        # Validate the initial target before starting a browser. The route guard
        # below repeats this validation for redirects and every subresource.
        safe_url(url)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                def guard(route):
                    target = route.request.url
                    if target.startswith(("http://", "https://")):
                        try:
                            safe_url(target)
                        except Exception:
                            route.abort()
                            return
                    route.continue_()

                context.route("**/*", guard)
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                safe_url(page.url)
                page.wait_for_timeout(1000)
                metrics = page.evaluate("""() => {
                  const n = performance.getEntriesByType('navigation')[0];
                  const paints = performance.getEntriesByType('paint');
                  const fcp = paints.find(x => x.name === 'first-contentful-paint');
                  const lcp = performance.getEntriesByType('largest-contentful-paint').at(-1);
                  const shifts = performance.getEntriesByType('layout-shift').filter(x => !x.hadRecentInput);
                  return {
                    domContentLoadedMs: n ? Math.round(n.domContentLoadedEventEnd - n.startTime) : 0,
                    loadMs: n ? Math.round(n.loadEventEnd - n.startTime) : 0,
                    fcpMs: fcp ? Math.round(fcp.startTime) : null,
                    lcpMs: lcp ? Math.round(lcp.startTime) : null,
                    cls: Math.round(shifts.reduce((s, x) => s + x.value, 0) * 1000) / 1000,
                    resourceCount: performance.getEntriesByType('resource').length
                  };
                }""")
                return {"available": True, **metrics}
            finally:
                browser.close()
    except Exception as exc:
        # Do not leak arbitrary browser/network error strings to audit consumers.
        return {"available": False, "error": type(exc).__name__}
