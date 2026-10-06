from __future__ import annotations
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup
from .site_scan import SiteData, crawl

def classify(site: SiteData) -> str:
    text = " ".join((p.title + " " + p.description + " " + " ".join(x[1] for x in p.headings)).lower() for p in site.pages)
    rules = [
        ("E-commerce", ["cart","checkout","product","shop","add to cart","price"]),
        ("SaaS / Web App", ["dashboard","sign in","login","workspace","app","pricing","free trial"]),
        ("Blog / Publication", ["blog","article","author","news","post","read more"]),
        ("Portfolio / Agency", ["portfolio","case study","projects","work with us"]),
        ("Education", ["course","lesson","student","academy","university","learn"]),
        ("Media", ["video","watch","episode","stream","subscribe"]),
        ("Business / Service", ["services","solutions","contact","about us","company"]),
    ]
    best="General Website"; best_score=0
    for name, terms in rules:
        current=sum(text.count(t) for t in terms)
        if current>best_score: best, best_score=name, current
    return best

def feature_snapshot(site: SiteData) -> dict:
    pages=site.pages
    return {
        "pages_scanned":len(pages),
        "h1_pages":sum(1 for p in pages if p.h1_count),
        "avg_response_ms":round(sum(p.response_ms for p in pages)/len(pages)) if pages else 0,
        "missing_alt_images":sum(sum(1 for x in p.images if not x.get("alt")) for p in pages),
        "json_ld_pages":sum(1 for p in pages if p.json_ld),
        "social_ready_pages":sum(1 for p in pages if p.og_title and p.og_description),
        "security_header_coverage":round(100*sum(sum(p.security_headers.values()) for p in pages)/(len(pages)*6)) if pages else 0,
    }

def _search(query: str, limit: int=5) -> list[dict]:
    try:
        r=requests.get("https://html.duckduckgo.com/html/",params={"q":query},headers={"User-Agent":"WebForgeBot/1.2"},timeout=10)
        soup=BeautifulSoup(r.text,"html.parser")
        out=[]
        for item in soup.select(".result")[:limit]:
            a=item.select_one(".result__a"); sn=item.select_one(".result__snippet")
            if not a: continue
            href=a.get("href","")
            if href.startswith("http"): out.append({"name":a.get_text(" ",strip=True),"url":href,"snippet":sn.get_text(" ",strip=True) if sn else ""})
        return out
    except Exception:
        return []

def discover_similar(site: SiteData, website_type: str, limit: int=3) -> list[dict]:
    root=urlsplit(site.root_url).hostname or ""
    title=site.pages[0].title if site.pages else ""
    query=(website_type+" "+title+" websites")[:180]
    results=[]; seen=set()
    for item in _search(query,7):
        host=urlsplit(item["url"]).hostname or ""
        if not host or host==root or host in seen: continue
        try:
            candidate=crawl(item["url"],1)
            if not candidate.pages: continue
            results.append({**item,"features":feature_snapshot(candidate),"website_type":classify(candidate)})
            seen.add(host)
            if len(results)>=limit: break
        except Exception:
            continue
    return results

def opportunities(target:dict, similar:list[dict])->list[dict]:
    out=[]
    if not target.get("social_ready_pages"):
        out.append({"title":"Own the share preview","reason":"Important pages are not fully prepared for link sharing.","action":"Add complete Open Graph and social preview metadata."})
    if not target.get("json_ld_pages"):
        out.append({"title":"Add structured search context","reason":"No structured data was detected.","action":"Add accurate JSON-LD that matches the website type and page content."})
    if target.get("missing_alt_images",0)>0:
        out.append({"title":"Make visuals searchable and accessible","reason":"Image metadata is incomplete.","action":"Add meaningful alt text and image dimensions."})
    if target.get("security_header_coverage",100)<70:
        out.append({"title":"Strengthen browser trust","reason":"Several important response security headers are missing.","action":"Configure and validate HSTS, CSP, framing, MIME, referrer, and permissions policies."})
    if similar and len(out)<5:
        stronger=next((s for s in similar if s.get("features",{}).get("social_ready_pages",0)>target.get("social_ready_pages",0)),None)
        if stronger:
            out.append({"title":"Borrow a proven pattern, then differentiate","reason":"A comparable site has stronger social-preview coverage.","action":"Study its information hierarchy and build a differentiated version for your audience."})
    if not out:
        out.append({"title":"Differentiate on product value","reason":"The baseline experience is comparatively healthy.","action":"Add one distinctive workflow or feature that competitors cannot explain in one sentence."})
    return out[:5]
