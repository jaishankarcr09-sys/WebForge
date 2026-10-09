from __future__ import annotations
from collections import deque
from dataclasses import dataclass, asdict, field
import ipaddress, socket, time
from urllib.parse import urljoin, urlsplit, urlunsplit, urldefrag
import requests
from bs4 import BeautifulSoup

UA="WebForgeBot/1.2"; MAX_BYTES=2_000_000
SECURITY_HEADERS=("strict-transport-security","content-security-policy","x-frame-options","x-content-type-options","referrer-policy","permissions-policy")

@dataclass
class PageData:
    url:str; final_url:str; status:int; response_ms:int; ttfb_ms:int; html_bytes:int
    title:str; description:str; canonical:str; canonical_count:int; h1_count:int
    headings:list[tuple[str,str]]; images:list[dict]; internal_links:list[str]; external_links:list[str]
    scripts:int; lang:str; viewport:str; og_title:str; og_description:str; twitter_card:str; json_ld:int
    noindex:bool; mixed_content:int; security_headers:dict[str,bool]
    forms_without_labels:int; buttons_without_names:int
    server:str; cache_control:str; content_encoding:str; etag:bool; set_cookie_count:int; insecure_cookie_count:int; redirect_count:int
    content_type:str=""; analysis_eligible:bool=True; crawl_note:str=""; html_truncated:bool=False

@dataclass
class SiteData:
    root_url:str; pages:list[PageData]; discovered:list[str]; broken_links:list[dict]
    robots_present:bool; robots_allowed:bool; sitemap_present:bool; sitemap_urls:list[str]; duration_ms:int
    crawl_warnings:list[dict]=field(default_factory=list)

def safe_url(url:str)->str:
    p=urlsplit(url)
    if p.scheme not in {"http","https"} or not p.hostname: raise ValueError("Only http:// and https:// URLs are supported.")
    if p.hostname.lower() in {"localhost","localhost.localdomain"}: raise ValueError("Localhost targets are not allowed.")
    try: infos=socket.getaddrinfo(p.hostname,None,type=socket.SOCK_STREAM)
    except socket.gaierror as exc: raise ValueError(f"Unable to resolve hostname: {p.hostname}") from exc
    for info in infos:
        ip=ipaddress.ip_address(info[4][0])
        if not ip.is_global: raise ValueError("Private, loopback, link-local, or reserved targets are not allowed.")
    return urlunsplit((p.scheme,p.netloc,p.path or "/",p.query,""))

def norm(url:str)->str:
    value,_=urldefrag(url); p=urlsplit(value)
    return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path or "/",p.query,""))

def same_origin(a:str,b:str)->bool:
    x,y=urlsplit(a),urlsplit(b)
    return x.scheme==y.scheme and x.netloc.lower()==y.netloc.lower()

def fetch(session:requests.Session,url:str,timeout:int=15):
    safe_url(url); start=time.perf_counter()
    r=session.get(url,timeout=timeout,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"},allow_redirects=True,stream=True)
    safe_url(r.url)
    data=bytearray()
    for chunk in r.iter_content(32768):
        if chunk:
            data.extend(chunk[:max(0,MAX_BYTES-len(data))])
            if len(data)>=MAX_BYTES: break
    elapsed=int((time.perf_counter()-start)*1000); ttfb=int(r.elapsed.total_seconds()*1000); r.close()
    return r,bytes(data),elapsed,ttfb

def meta(soup:BeautifulSoup,name:str)->str:
    tag=soup.find("meta",attrs={"name":lambda v:v and str(v).lower()==name.lower()})
    return str(tag.get("content","")).strip() if tag else ""

def prop(soup:BeautifulSoup,name:str)->str:
    tag=soup.find("meta",attrs={"property":name})
    return str(tag.get("content","")).strip() if tag else ""

def _is_xml_resource(url:str, content_type:str="", body:bytes=b"")->bool:
    """Identify XML feeds/sitemaps even when the server sends a misleading MIME type."""
    path=urlsplit(url).path.lower()
    if path.endswith(".xml"):
        return True
    if "xml" in (content_type or "").lower():
        return True
    prefix=body[:2048].decode("utf-8",errors="ignore").lstrip("\\ufeff\\r\\n\\t ").lower()
    return prefix.startswith("<?xml") or prefix.startswith("<urlset") or prefix.startswith("<sitemapindex") or prefix.startswith("<rss") or prefix.startswith("<feed")


def parse_page(url:str,r:requests.Response,body:bytes,elapsed:int,ttfb:int)->PageData:
    soup=BeautifulSoup(body.decode(r.encoding or "utf-8",errors="replace"),"html.parser")
    internal=[]; external=[]; si=set(); se=set()
    for a in soup.find_all("a",href=True):
        raw=str(a.get("href","")).strip()
        if not raw or raw.startswith(("#","mailto:","tel:","javascript:")): continue
        target=norm(urljoin(r.url,raw))
        if urlsplit(target).scheme not in {"http","https"}: continue
        if same_origin(target,url):
            if target not in si: internal.append(target); si.add(target)
        elif target not in se: external.append(target); se.add(target)
    images=[]
    for img in soup.find_all("img"):
        images.append({"src":urljoin(r.url,str(img.get("src",""))),"alt":str(img.get("alt","")).strip(),"width":img.get("width"),"height":img.get("height"),"loading":img.get("loading")})
    cans=soup.find_all("link",rel=lambda v:v and "canonical" in v)
    canonical=urljoin(r.url,str(cans[0].get("href",""))) if cans and cans[0].get("href") else ""
    robots=meta(soup,"robots").lower()
    labels=0
    for inp in soup.find_all(["input","textarea","select"]):
        if str(inp.get("type","")).lower()=="hidden": continue
        ident=inp.get("id")
        named=bool(inp.get("aria-label") or inp.get("aria-labelledby") or (ident and soup.find("label",attrs={"for":ident})))
        if not named: labels+=1
    unnamed_buttons=sum(1 for b in soup.find_all("button") if not b.get_text(" ",strip=True) and not b.get("aria-label") and not b.get("aria-labelledby"))
    mixed=0
    if r.url.startswith("https://"):
        mixed=sum(int(str(t.get("src","")).startswith("http://")) for t in soup.find_all(["img","script","iframe"],src=True))
        mixed+=sum(int(str(t.get("href","")).startswith("http://")) for t in soup.find_all("link",href=True))
    content_type=str(r.headers.get("content-type","")).lower()
    xml_resource=_is_xml_resource(r.url,content_type,body)
    html_response="html" in content_type and not xml_resource
    title_text=soup.title.get_text(" ",strip=True) if soup.title else ""
    body_text=soup.get_text(" ",strip=True).lower()[:12000]
    challenge_markers=("verify you are human","checking your browser","attention required","captcha","unusual traffic","request blocked","enable javascript and cookies to continue")
    challenge=any(marker in (title_text+" "+body_text).lower() for marker in challenge_markers)
    status_ok=200 <= r.status_code < 400
    eligible=status_ok and html_response and not challenge
    note=""
    if not status_ok: note=f"HTTP status {r.status_code}; content checks skipped."
    elif xml_resource: note=f"XML/resource response ({content_type or 'URL/body indicates XML'}); HTML checks skipped."
    elif not html_response: note=f"Non-HTML response ({content_type or 'unknown content type'}); HTML checks skipped."
    elif challenge: note="Response resembles a bot challenge or access interstitial; HTML checks skipped."
    content_length=r.headers.get("content-length","")
    try: truncated=int(content_length)>len(body)
    except (TypeError,ValueError): truncated=False
    if truncated:
        eligible=False
        note=(note+" " if note else "")+"Response body may be truncated at the crawler size limit; content checks skipped."
    return PageData(
        url=url,final_url=r.url,status=r.status_code,response_ms=elapsed,ttfb_ms=ttfb,html_bytes=len(body),
        title=title_text,description=meta(soup,"description"),
        canonical=canonical,canonical_count=len(cans),h1_count=len(soup.find_all("h1")),
        headings=[(t.name,t.get_text(" ",strip=True)) for t in soup.find_all(["h1","h2","h3","h4","h5","h6"])],
        images=images,internal_links=internal,external_links=external,scripts=len(soup.find_all("script",src=True)),
        lang=str(soup.html.get("lang","")).strip() if soup.html else "",viewport=meta(soup,"viewport"),
        og_title=prop(soup,"og:title"),og_description=prop(soup,"og:description"),twitter_card=meta(soup,"twitter:card"),
        json_ld=len(soup.find_all("script",type="application/ld+json")),noindex="noindex" in robots,mixed_content=mixed,
        security_headers={h:bool(r.headers.get(h)) for h in SECURITY_HEADERS},
        forms_without_labels=labels,buttons_without_names=unnamed_buttons,
        server=str(r.headers.get("server","")), cache_control=str(r.headers.get("cache-control","")),
        content_encoding=str(r.headers.get("content-encoding","")), etag=bool(r.headers.get("etag")),
        set_cookie_count=len(r.raw.headers.get_all("set-cookie") or []) if hasattr(r.raw.headers,"get_all") else int(bool(r.headers.get("set-cookie"))),
        insecure_cookie_count=sum(1 for c in (r.raw.headers.get_all("set-cookie") or []) if "secure" not in c.lower()) if hasattr(r.raw.headers,"get_all") else 0,
        redirect_count=len(r.history),content_type=content_type,analysis_eligible=eligible,crawl_note=note,html_truncated=truncated
    )

def crawl(url:str,page_limit:int=10)->SiteData:
    root=safe_url(url); limit=max(1,min(int(page_limit),30)); start=time.perf_counter(); session=requests.Session()
    q=deque([root]); seen=set(); pages=[]; discovered={root}
    robots_present=False; robots_allowed=True; sitemap_present=False; sitemap_urls=[]
    try:
        rp=urlsplit(root); robots=urlunsplit((rp.scheme,rp.netloc,"/robots.txt","",""))
        rr,rb,_,_=fetch(session,robots,10); robots_present=rr.status_code==200
        if robots_present:
            lines=rb.decode("utf-8",errors="replace").splitlines()
            robots_allowed=not any("disallow: /" in x.lower().replace(" ","") for x in lines if x.lower().startswith("disallow"))
            sitemap_urls=[x.split(":",1)[1].strip() for x in lines if x.lower().startswith("sitemap:") and ":" in x]
    except Exception: pass
    if not sitemap_urls: sitemap_urls=[urlunsplit((urlsplit(root).scheme,urlsplit(root).netloc,"/sitemap.xml","",""))]
    sitemap_found=[]
    for sm in sitemap_urls[:3]:
        try:
            sr,sb,_,_=fetch(session,sm,10)
            if sr.status_code==200:
                sitemap_present=True
                import re
                sitemap_found += [norm(x.strip()) for x in re.findall(r"<loc>\s*([^<]+?)\s*</loc>",sb.decode("utf-8",errors="ignore"))[:200]]
        except Exception: pass
    for x in sitemap_found[:limit]:
        # Sitemap indexes and XML feeds are crawl resources, not HTML pages to audit.
        if same_origin(x,root) and not _is_xml_resource(x):
            q.append(x); discovered.add(x)
    while q and len(pages)<limit:
        current=norm(q.popleft())
        if current in seen or not same_origin(current,root): continue
        seen.add(current)
        try:
            r,b,elapsed,ttfb=fetch(session,current)
            page=parse_page(current,r,b,elapsed,ttfb); pages.append(page)
            for target in page.internal_links:
                # XML sitemaps/feeds are linked resources, not HTML pages for the page-limit queue.
                if _is_xml_resource(target):
                    continue
                discovered.add(target)
                if target not in seen and len(discovered)<limit*5: q.append(target)
        except Exception:
            pages.append(PageData(url=current,final_url=current,status=0,response_ms=0,ttfb_ms=0,html_bytes=0,title="",description="",canonical="",canonical_count=0,h1_count=0,headings=[],images=[],internal_links=[],external_links=[],scripts=0,lang="",viewport="",og_title="",og_description="",twitter_card="",json_ld=0,noindex=False,mixed_content=0,security_headers={},forms_without_labels=0,buttons_without_names=0,server="",cache_control="",content_encoding="",etag=False,set_cookie_count=0,insecure_cookie_count=0,redirect_count=0,content_type="",analysis_eligible=False,crawl_note="Crawler request failed; page content was not verified."))
    targets=[]; broken=[]; checked=set()
    for p in pages: targets += p.internal_links[:80] + p.external_links[:20]
    for target in targets:
        if target in checked: continue
        checked.add(target)
        try:
            r,_,elapsed,_=fetch(session,target,10)
            if r.status_code>=400: broken.append({"url":target,"status":r.status_code,"response_ms":elapsed})
        except Exception as exc: broken.append({"url":target,"status":0,"error":str(exc)[:160]})
    warnings=[{"url":p.url,"status":p.status,"final_url":p.final_url,"content_type":p.content_type,"reason":p.crawl_note or "Page content was not eligible for analysis."} for p in pages if not p.analysis_eligible]
    return SiteData(root,pages,sorted(discovered),broken,robots_present,robots_allowed,sitemap_present,sorted(set(sitemap_found or sitemap_urls)),int((time.perf_counter()-start)*1000),warnings)

def page_json(page:PageData)->dict: return asdict(page)
