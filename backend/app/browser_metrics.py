from __future__ import annotations
from playwright.sync_api import sync_playwright

def measure(url:str)->dict:
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(url,wait_until="domcontentloaded",timeout=30000)
            page.wait_for_timeout(1000)
            metrics=page.evaluate("""() => {
              const n=performance.getEntriesByType('navigation')[0];
              const paints=performance.getEntriesByType('paint');
              const fcp=paints.find(x=>x.name==='first-contentful-paint');
              const lcp=performance.getEntriesByType('largest-contentful-paint').at(-1);
              const shifts=performance.getEntriesByType('layout-shift').filter(x=>!x.hadRecentInput);
              return {
                domContentLoadedMs: n ? Math.round(n.domContentLoadedEventEnd-n.startTime) : 0,
                loadMs: n ? Math.round(n.loadEventEnd-n.startTime) : 0,
                fcpMs: fcp ? Math.round(fcp.startTime) : null,
                lcpMs: lcp ? Math.round(lcp.startTime) : null,
                cls: Math.round(shifts.reduce((s,x)=>s+x.value,0)*1000)/1000,
                resourceCount: performance.getEntriesByType('resource').length
              };
            }""")
            browser.close()
            return {"available":True,**metrics}
    except Exception as exc:
        return {"available":False,"error":str(exc)[:180]}
