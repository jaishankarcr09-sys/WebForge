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
    code_before:str=""; code_after:str=""; dimension:str="technical"; layer:str="frontend"; score_eligible:bool=True
    def asdict(self): return asdict(self)

def finding(category,title,severity,impact,recommendation,page_url="",evidence="",confidence=100,effort="medium",code_before="",code_after="",dimension="technical",layer="frontend",score_eligible=True):
    severity_base={"critical":100,"high":80,"medium":55,"low":25}[severity]
    confidence_factor=max(0,min(100,confidence))/100
    effort_factor={"low":1.0,"medium":0.9,"high":0.8}[effort]
    priority=max(1,min(100,round(severity_base*confidence_factor*effort_factor)))
    return Finding(category,title,severity,impact,recommendation,page_url,evidence,confidence,effort,priority,code_before,code_after,dimension,layer,score_eligible)

def analyze(site:SiteData)->list[Finding]:
    out=[]
    titles=[]; descriptions=[]
    unique_pages=[]
    seen_page_urls=set()
    for page in site.pages:
        page_key=getattr(page,"url","")
        if page_key and page_key in seen_page_urls:
            continue
        if page_key:
            seen_page_urls.add(page_key)
        unique_pages.append(page)
    for p in unique_pages:
        # Skip HTML-derived rules for blocked, challenge, non-HTML, or incomplete responses.
        if not getattr(p,"analysis_eligible",True):
            continue
        if p.status==0:
            out.append(finding("Technical","Page could not be fetched","high","The crawler could not obtain a valid response.","Check DNS, TLS, firewall rules, redirects, or upstream availability.",p.url,"Crawler request failed; page-content checks were skipped.",100,"medium",dimension="technical"))
            continue
        if p.status>=400:
            out.append(finding("Technical",f"HTTP error ({p.status})","high","WebForge's crawler received an HTTP error response. This may reflect bot protection or access policy and does not alone prove that ordinary visitors see the same error.","Check the response in a normal browser and confirm whether the crawler is permitted. Page-content SEO checks are skipped for this response.",p.url,f"Crawler-observed HTTP status: {p.status}; HTML-derived findings were skipped because the response may be an error or block page.",100,"medium",dimension="technical"))
            continue
        titles.append(p.title.strip().lower()); descriptions.append(p.description.strip().lower())
        if not p.title:
            out.append(finding("SEO","Missing page title","high","The page lacks a primary title signal.","Add one unique, descriptive <title>.",p.url,"No <title> element found.",100,"low","<head>...</head>","<head>\n  <title>Descriptive page title</title>\n</head>","seo"))
        elif len(p.title)<30:
            out.append(finding("SEO","Title may be too short","low","Short titles can be valid; consider whether more context would help users understand this page.","Expand the title only when additional wording improves clarity or distinctiveness.",p.url,f"Title length: {len(p.title)} characters.",90,"low",dimension="seo",score_eligible=False))
        elif len(p.title)>60:
            out.append(finding("SEO","Title may be too long","low","Long titles can be truncated in search interfaces.","Keep the main intent near the beginning and shorten the title.",p.url,f"Title length: {len(p.title)} characters.",90,"low",dimension="seo"))
        if not p.description:
            out.append(finding("SEO","Missing meta description","low","A search engine may generate its own snippet; a description can help you suggest useful wording.","Add a unique, relevant meta description when it benefits this page.",p.url,"No meta description element was found in the captured HTML.",100,"low",dimension="seo",score_eligible=False))
        elif len(p.description)>170:
            out.append(finding("SEO","Meta description may be too long","low","Long snippets may be truncated.","Keep the important message concise.",p.url,f"Description length: {len(p.description)} characters.",90,"low",dimension="seo"))
        if p.canonical_count==0:
            out.append(finding("SEO","Canonical URL not declared","low","A canonical link is useful when a page has duplicate or alternate URLs, but is not required for every page.","If this page has duplicate or alternate URLs, declare the preferred canonical URL.",p.url,"Canonical tag count: 0; no duplicate-URL condition has been established.",100,"low",dimension="seo",score_eligible=False))
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
        missing=sum(1 for x in p.images if not x.get("alt_present", bool(x.get("alt"))))
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
            out.append(finding("SEO","Incomplete social metadata","low","Social platforms may use fallback page content when sharing this URL.","Add Open Graph title and description if controlled link previews are important.",p.url,f"og:title={bool(p.og_title)}, og:description={bool(p.og_description)}.",90,"low",dimension="seo",score_eligible=False))
        if p.json_ld==0:
            out.append(finding("SEO","No JSON-LD structured data detected","low","Structured data is only useful for supported content types and is not required on every page.","Add valid structured data only when the page content matches an applicable schema type.",p.url,"JSON-LD script count: 0; applicability was not established.",80,"medium",dimension="seo",score_eligible=False))
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
    # Do not infer missing site-wide files when every page fetch failed or was blocked.
    has_successful_page = any(200 <= page.status < 400 for page in site.pages)
    if has_successful_page:
        if not site.robots_present: out.append(finding("SEO","robots.txt not confirmed","low","WebForge did not confirm a usable robots.txt response at the expected location; this may be absence or a fetch restriction.","Check the robots.txt URL and response status before deciding whether a file is needed.",site.root_url,"robots.txt was not confirmed as HTTP 200; absence has not been distinguished from access or network failure.",80,"low",dimension="seo",score_eligible=False))
        elif not site.robots_allowed: out.append(finding("SEO","Crawler appears blocked by robots.txt","medium","The site's robots rules appear to disallow the audit crawler at the root.","Review robots rules if public crawling is intended.",site.root_url,"WebForgeBot cannot fetch the root under current rules.",95,"medium",dimension="seo"))
        if not site.sitemap_present: out.append(finding("SEO","Sitemap not confirmed","low","WebForge did not confirm a sitemap at the locations checked; a sitemap is not required for every site and may be published at another URL.","Check sitemap declarations in robots.txt and the site's known sitemap locations if discoverability requires it.",site.root_url,"No sitemap returned HTTP 200 at the locations checked; other locations and access restrictions were not ruled out.",80,"low",dimension="seo",score_eligible=False))
    if site.broken_links:
        out.append(finding("Technical",f"{len(site.broken_links)} broken link(s) detected","high","Broken destinations create dead ends for users and crawlers.","Repair the link target or update the source page.",site.root_url,f"Broken links observed: {len(site.broken_links)}.",100,"medium",dimension="technical"))
    # Deduplicate identical findings for the same page and evidence.
    deduped=[]
    seen=set()
    for item in out:
        key=(item.category,item.title,item.page_url,item.evidence)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped

def score(findings:list[Finding], page_count:int|None=None)->tuple[int,dict[str,int]]:
    """Score verified pages without letting repeated page-level findings zero every dimension.

    Page findings are grouped by URL and dimension, capped per page, then averaged
    over the verified-page count. Site-wide findings (no page URL) receive a small
    separate capped penalty. Informational/unconfirmed findings remain visible but
    are excluded from scoring.
    """
    dimensions_order=("seo","performance","accessibility","security","technical")
    severity_penalty={"critical":25,"high":16,"medium":9,"low":3}
    eligible=[f for f in findings if getattr(f,"score_eligible",True) and f.dimension in dimensions_order]
    observed_pages={f.page_url for f in eligible if f.page_url}
    denominator=max(1, page_count if page_count is not None else len(observed_pages) or 1)
    page_penalties={dimension:{} for dimension in dimensions_order}
    global_penalties={dimension:0 for dimension in dimensions_order}
    for item in eligible:
        penalty=severity_penalty.get(item.severity,0)
        if item.page_url:
            bucket=page_penalties[item.dimension]
            bucket[item.page_url]=min(45,bucket.get(item.page_url,0)+penalty)
        else:
            global_penalties[item.dimension]=min(20,global_penalties[item.dimension]+penalty)
    scores={}
    for dimension in dimensions_order:
        average_page_penalty=sum(page_penalties[dimension].values())/denominator
        total_penalty=min(75,average_page_penalty+global_penalties[dimension])
        scores[dimension]=max(0,round(100-total_penalty))
    overall=round(sum(scores[k]*DIMENSION_WEIGHTS[k] for k in scores))
    return max(0,min(100,overall)),scores
