from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import Counter
from .site_scan import SiteData, PageData

DIMENSION_WEIGHTS={"seo":.24,"performance":.22,"accessibility":.20,"security":.16,"technical":.18}
EFFORT={"low":1,"medium":2,"high":3}
IMPACT={"critical":10,"high":8,"medium":5,"low":2}

@dataclass
class Finding:
    category:str; title:str; severity:str; impact:str; recommendation:str
    page_url:str=""; evidence:str=""; confidence:int=100; effort:str="medium"; priority:int=50
    code_before:str=""; code_after:str=""; dimension:str="technical"; layer:str="frontend"
    def asdict(self): return asdict(self)

def finding(category,title,severity,impact,recommendation,page_url="",evidence="",confidence=100,effort="medium",code_before="",code_after="",dimension="technical",layer="frontend"):
    priority=max(1,min(100,round(IMPACT[severity]*confidence/EFFORT[effort])))
    return Finding(category,title,severity,impact,recommendation,page_url,evidence,confidence,effort,priority,code_before,code_after,dimension,layer)

def analyze(site:SiteData)->list[Finding]:
    out=[]
    titles=[]; descriptions=[]
    for p in site.pages:
        titles.append(p.title.strip().lower()); descriptions.append(p.description.strip().lower())
        if p.status==0:
            out.append(finding("Technical","Page could not be fetched","high","The crawler could not obtain a valid response.","Check DNS, TLS, firewall rules, redirects, or upstream availability.",p.url,"Crawler request failed.",100,"medium",dimension="technical")); continue
        if p.status>=400:
            out.append(finding("Technical",f"HTTP error ({p.status})","high","Users and search engines receive an error response.","Fix the route or redirect the URL to the correct destination.",p.url,f"HTTP status: {p.status}.",100,"medium",dimension="technical"))
        if not p.title:
            out.append(finding("SEO","Missing page title","high","The page lacks a primary title signal.","Add one unique, descriptive <title>.",p.url,"No <title> element found.",100,"low","<head>...</head>","<head>\n  <title>Descriptive page title</title>\n</head>","seo"))
        elif len(p.title)<30:
            out.append(finding("SEO","Title may be too short","low","Very short titles provide weak topical context.","Expand the title with useful page context.",p.url,f"Title length: {len(p.title)} characters.",90,"low",dimension="seo"))
        elif len(p.title)>60:
            out.append(finding("SEO","Title may be too long","low","Long titles can be truncated in search interfaces.","Keep the main intent near the beginning and shorten the title.",p.url,f"Title length: {len(p.title)} characters.",90,"low",dimension="seo"))
        if not p.description:
            out.append(finding("SEO","Missing meta description","medium","Search engines may generate a less useful snippet.","Add a unique, relevant meta description.",p.url,"No meta description found.",100,"low",dimension="seo"))
        elif len(p.description)>170:
            out.append(finding("SEO","Meta description may be too long","low","Long snippets may be truncated.","Keep the important message concise.",p.url,f"Description length: {len(p.description)} characters.",90,"low",dimension="seo"))
        if p.canonical_count==0:
            out.append(finding("SEO","Missing canonical URL","medium","Canonicalization intent is not explicit.","Add one canonical URL pointing to the preferred page.",p.url,"Canonical tag count: 0.",100,"low",dimension="seo"))
        elif p.canonical_count>1:
            out.append(finding("SEO","Multiple canonical tags","medium","Conflicting canonical tags can create ambiguous indexing signals.","Keep exactly one canonical link.",p.url,f"Canonical tags found: {p.canonical_count}.",100,"low",dimension="seo"))
        if p.noindex:
            out.append(finding("SEO","Page is marked noindex","high","This directive prevents normal indexing.","Remove noindex only when the page should be discoverable.",p.url,"robots metadata contains noindex.",100,"low",dimension="seo"))
        if p.h1_count==0:
            out.append(finding("Technical","Missing H1 heading","high","The document has no explicit primary heading.","Add one descriptive H1 for the page's main topic.",p.url,"H1 count: 0.",100,"low",dimension="technical"))
        elif p.h1_count>1:
            out.append(finding("Technical","Multiple H1 headings","low","Multiple primary headings can reduce document clarity.","Use one H1 and H2-H6 for subsections.",p.url,f"H1 count: {p.h1_count}.",100,"low",dimension="technical"))
        for i in range(1,len(p.headings)):
            prev=int(p.headings[i-1][0][1]); cur=int(p.headings[i][0][1])
            if cur-prev>1:
                out.append(finding("Accessibility","Heading hierarchy skip","low","Skipped heading levels can make navigation harder for assistive technology.","Avoid jumping more than one heading level.",p.url,f"Observed: {p.headings[i-1][0]} → {p.headings[i][0]}.",95,"low",dimension="accessibility")); break
        missing=sum(1 for x in p.images if not x.get("alt"))
        if missing:
            out.append(finding("Accessibility",f"{missing} image(s) missing alt text","medium","Informative images may be inaccessible to screen-reader users.","Add meaningful alt text; use empty alt for decorative images.",p.url,f"Images without alt: {missing}.",100,"low",'<img src="hero.jpg">','<img src="hero.jpg" alt="Descriptive image">',"accessibility"))
        no_dims=sum(1 for x in p.images if not x.get("width") or not x.get("height"))
        if no_dims:
            out.append(finding("Performance",f"{no_dims} image(s) lack dimensions","low","Missing intrinsic dimensions can contribute to layout movement.","Provide width and height or equivalent aspect-ratio constraints.",p.url,f"Images missing dimensions: {no_dims}.",95,"low",dimension="performance"))
        if p.forms_without_labels:
            out.append(finding("Accessibility",f"{p.forms_without_labels} input(s) lack accessible labeling","high","Unnamed form controls are difficult to operate with assistive technology.","Associate each control with a visible label or accessible name.",p.url,f"Potential unlabeled controls: {p.forms_without_labels}.",90,"medium",dimension="accessibility"))
        if p.buttons_without_names:
            out.append(finding("Accessibility",f"{p.buttons_without_names} button(s) lack accessible names","medium","Unnamed buttons are ambiguous to assistive technology users.","Add visible text or an accessible aria-label.",p.url,f"Potential unnamed buttons: {p.buttons_without_names}.",90,"low",dimension="accessibility"))
        if not p.lang:
            out.append(finding("Accessibility","Missing document language","medium","Assistive technologies may not know which language rules to apply.","Set the html lang attribute.",p.url,"<html lang> is missing.",100,"low","<html>","<html lang=\"en\">","accessibility"))
        if not p.viewport:
            out.append(finding("Technical","Missing viewport meta tag","medium","Mobile layout behavior may be inconsistent.","Add a responsive viewport declaration.",p.url,"No viewport meta tag found.",100,"low","<head>","<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">","technical"))
        if not p.og_title or not p.og_description:
            out.append(finding("SEO","Incomplete social metadata","low","Shared links may lack a useful title or description.","Add og:title and og:description for important pages.",p.url,f"og:title={bool(p.og_title)}, og:description={bool(p.og_description)}.",90,"low",dimension="seo"))
        if p.json_ld==0:
            out.append(finding("SEO","No JSON-LD structured data detected","low","Eligible structured-data opportunities may be missing.","Add accurate schema.org JSON-LD where it represents the page.",p.url,"JSON-LD script count: 0.",80,"medium",dimension="seo"))
        if p.mixed_content:
            out.append(finding("Security","Mixed content detected","high","An HTTPS page references insecure HTTP resources.","Serve all resources over HTTPS.",p.url,f"HTTP resources detected: {p.mixed_content}.",100,"medium",dimension="security"))
        missing_headers=[h for h,v in p.security_headers.items() if not v]
        if missing_headers:
            out.append(finding("Security","Security headers missing","medium","Important browser security controls are not explicitly configured.","Review HSTS, CSP, framing, MIME sniffing, referrer, and permissions policies.",p.url,"Missing: "+", ".join(missing_headers)+".",95,"medium",dimension="security"))
        if p.response_ms>1500:
            out.append(finding("Performance","Slow page response","high","Slow server response delays content delivery.","Profile server work, caching, database calls, and upstream dependencies.",p.url,f"Response time: {p.response_ms} ms.",100,"high",dimension="performance"))
        elif p.response_ms>800:
            out.append(finding("Performance","Elevated page response time","medium","Response latency is high enough to affect perceived speed.","Profile the request path and add caching where safe.",p.url,f"Response time: {p.response_ms} ms.",100,"medium",dimension="performance"))
        if p.ttfb_ms>800:
            out.append(finding("Performance","High TTFB","medium","The server takes a long time to start the response.","Profile server-side execution and infrastructure latency.",p.url,f"TTFB: {p.ttfb_ms} ms.",100,"high",dimension="performance"))
        if p.html_bytes>500_000:
            out.append(finding("Performance","Large HTML document","medium","Large HTML increases transfer and parsing cost.","Reduce unnecessary markup and compress responses.",p.url,f"HTML size: {round(p.html_bytes/1024)} KB.",100,"medium",dimension="performance"))
        if p.scripts>20:
            out.append(finding("Performance","High external script count","medium","Many JavaScript resources can increase network and execution overhead.","Remove unused scripts and defer non-critical dependencies.",p.url,f"External scripts: {p.scripts}.",100,"medium",dimension="performance"))
    dup_titles=[x for x,c in Counter(titles).items() if x and c>1]
    if dup_titles: out.append(finding("SEO","Duplicate page titles","medium","Multiple pages share the same title and can target the same search intent poorly.","Make titles unique for each important page.",evidence=f"Duplicate title groups: {len(dup_titles)}.",confidence=100,effort="medium",dimension="seo"))
    dup_desc=[x for x,c in Counter(descriptions).items() if x and c>1]
    if dup_desc: out.append(finding("SEO","Duplicate meta descriptions","low","Repeated descriptions provide weak page differentiation.","Write unique descriptions for important pages.",evidence=f"Duplicate description groups: {len(dup_desc)}.",confidence=100,effort="medium",dimension="seo"))
    if not site.robots_present: out.append(finding("SEO","robots.txt missing","medium","Crawler directives are not explicitly published.","Add a valid robots.txt at the site root.",site.root_url,"robots.txt returned no 200 response.",95,"low",dimension="seo"))
    elif not site.robots_allowed: out.append(finding("SEO","Crawler appears blocked by robots.txt","high","The site's robots rules appear to disallow the audit crawler at the root.","Review robots rules if public crawling is intended.",site.root_url,"WebForgeBot cannot fetch the root under current rules.",100,"medium",dimension="seo"))
    if not site.sitemap_present: out.append(finding("SEO","sitemap.xml missing","medium","No XML sitemap was detected at common sitemap locations.","Publish and reference a valid XML sitemap.",site.root_url,"No sitemap returned 200.",95,"medium",dimension="seo"))
    if site.broken_links:
        out.append(finding("Technical",f"{len(site.broken_links)} broken link(s) detected","high","Broken destinations create dead ends for users and crawlers.","Repair the link target or update the source page.",site.root_url,f"Broken links observed: {len(site.broken_links)}.",100,"medium",dimension="technical"))
    return out

def score(findings:list[Finding])->tuple[int,dict[str,int]]:
    deductions={"seo":0.0,"performance":0.0,"accessibility":0.0,"security":0.0,"technical":0.0}
    for f in findings:
        deductions[f.dimension]+=min(25,IMPACT[f.severity]*2.5)
    dimensions={k:max(0,round(100-v)) for k,v in deductions.items()}
    overall=round(sum(dimensions[k]*DIMENSION_WEIGHTS[k] for k in dimensions))
    return max(0,min(100,overall)),dimensions
