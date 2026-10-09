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

def score(findings: list[Finding]):
    overall,dimensions=base_score(findings)
    frontend=[f for f in findings if f.layer=='frontend']
    backend=[f for f in findings if f.layer=='backend']
    full=[f for f in findings if f.layer=='full-stack']
    def layer_score(items):
        penalty=sum(min(12, {'critical':18,'high':12,'medium':7,'low':3}[f.severity]) for f in items)
        return max(0,100-penalty)
    dimensions['frontend']=layer_score(frontend+full)
    dimensions['backend']=layer_score(backend+full)
    return overall,dimensions
