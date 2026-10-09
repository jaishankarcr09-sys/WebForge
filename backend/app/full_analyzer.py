from __future__ import annotations
from .analyzers import analyze as base_analyze, score as base_score, finding, Finding
from .site_scan import SiteData

def analyze(site: SiteData) -> list[Finding]:
    findings=base_analyze(site)
    for item in findings:
        if item.category == 'Security': item.layer='backend'
        elif item.category == 'Performance': item.layer='full-stack'
    for p in site.pages[:3]:
        # Backend checks also require a validated HTML response; never infer
        # HTML size/compression/cookie findings from XML, binary, or challenge pages.
        if not getattr(p, "analysis_eligible", True):
            continue
        # A 4xx/5xx body may be a proxy or bot-block page, not the target website.
        if not (200 <= p.status < 400):
            continue
        if p.redirect_count>1:
            findings.append(finding('Backend','Redirect chain detected','medium','Multiple redirects increase latency and can dilute canonical delivery.','Reduce redirects so important URLs resolve directly.',p.url,f'Redirects followed: {p.redirect_count}.',100,'medium',dimension='performance',layer='backend'))
        if p.status and not p.content_encoding and p.html_bytes>100000:
            findings.append(finding('Backend','Compression signal missing','low','Large HTML without a visible content-encoding may increase transfer cost.','Enable Brotli or gzip at the edge/server where appropriate.',p.url,f'HTML size: {round(p.html_bytes/1024)} KB; Content-Encoding header absent.',85,'medium',dimension='performance',layer='backend'))
        if p.insecure_cookie_count:
            findings.append(finding('Backend','Insecure cookie flag detected','high','A response sets cookies without the Secure attribute.','Review session cookies and require Secure, HttpOnly, and appropriate SameSite settings.',p.url,f'Potential insecure Set-Cookie values: {p.insecure_cookie_count}.',100,'medium',dimension='security',layer='backend'))
    if site.broken_links:
        for item in findings:
            if 'broken link' in item.title.lower(): item.layer='full-stack'
    return findings

def score(findings: list[Finding], page_count: int | None = None):
    overall,dimensions=base_score(findings,page_count=page_count)
    frontend=[f for f in findings if f.layer=='frontend']
    backend=[f for f in findings if f.layer=='backend']
    full=[f for f in findings if f.layer=='full-stack']
    severity_penalty={'critical':25,'high':16,'medium':9,'low':3}
    denominator=max(1,page_count if page_count is not None else len({f.page_url for f in findings if f.page_url}) or 1)
    def layer_score(items):
        by_page={}
        global_penalty=0
        for item in items:
            if not getattr(item,'score_eligible',True):
                continue
            penalty=severity_penalty.get(item.severity,0)
            if item.page_url:
                by_page[item.page_url]=min(45,by_page.get(item.page_url,0)+penalty)
            else:
                global_penalty=min(20,global_penalty+penalty)
        average=sum(by_page.values())/denominator
        return max(0,round(100-min(75,average+global_penalty)))
    dimensions['frontend']=layer_score(frontend+full)
    dimensions['backend']=layer_score(backend+full)
    return overall,dimensions
