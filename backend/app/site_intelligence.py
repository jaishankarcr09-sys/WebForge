from __future__ import annotations

import logging
import os
import re
import time
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .site_scan import SiteData, crawl

logger = logging.getLogger(__name__)

_SEARCH_CACHE: dict[str, tuple[float, list[dict]]] = {}
_SEARCH_CACHE_TTL_SECONDS = 1800
_SEARCH_EMPTY_TTL_SECONDS = 120


def classify(site: SiteData) -> str:
    """Classify from successful page evidence, using specific signals before broad terms."""
    host = _host(site.root_url)
    known_domains = {
        "google.com": "Search Engine",
        "youtube.com": "Video / Media Platform",
        "youtu.be": "Video / Media Platform",
        "napkin.ai": "AI Visual Communication Tool",
        "leetcode.com": "Coding Practice / Education",
        "github.com": "Developer Platform",
        "python.org": "Programming Language / Documentation",
        "wikipedia.org": "Reference / Encyclopedia",
        "reddit.com": "Community / Discussion",
        "linkedin.com": "Professional Network",
        "instagram.com": "Social Media",
        "facebook.com": "Social Media",
        "netflix.com": "Streaming / Media",
        "amazon.com": "E-commerce",
        "coursera.org": "Online Education",
    }
    for domain, category in known_domains.items():
        if host == domain or host.endswith("." + domain):
            return category

    successful = [p for p in site.pages if getattr(p, "analysis_eligible", True) and 200 <= getattr(p, "status", 0) < 400]
    if not successful:
        return "Unknown / insufficient evidence"

    title_text = " ".join(getattr(p, "title", "") for p in successful).lower()
    description_text = " ".join(getattr(p, "description", "") for p in successful).lower()
    heading_text = " ".join(
        heading for p in successful for _, heading in getattr(p, "headings", [])[:8]
    ).lower()
    rules = [
        ("Search Engine", ["search engine", "search the web", "search results", "search anything"]),
        ("AI / Developer Tool", ["ai-powered", "artificial intelligence", "developer api", "code editor", "ai assistant"]),
        ("E-commerce", ["add to cart", "shopping cart", "checkout", "buy now", "online store"]),
        ("Coding Practice / Education", ["coding challenge", "programming problems", "practice problems", "coding interview"]),
        ("Video / Media Platform", ["watch videos", "video streaming", "music streaming", "episodes and movies"]),
        ("Online Education", ["online courses", "course catalog", "learn online", "lessons and courses"]),
        ("Community / Discussion", ["community discussion", "ask the community", "forum", "discussions"]),
        ("Blog / Publication", ["latest news", "editorial", "articles and insights", "read our blog"]),
        ("SaaS / Web App", ["manage your workspace", "project management", "sign in to your account", "free trial"]),
        ("Portfolio / Agency", ["our portfolio", "selected projects", "case studies", "work with us"]),
        ("Business / Service", ["our services", "contact our team", "business solutions", "request a quote"]),
    ]
    scores = {}
    for category, phrases in rules:
        score = sum(4 * title_text.count(term) + 3 * description_text.count(term) + heading_text.count(term) for term in phrases)
        if score:
            scores[category] = score
    if not scores:
        return "General Website"
    best_category, best_score = max(scores.items(), key=lambda item: item[1])
    # A verified page with weak category signals is still a real site; reserve
    # the insufficient-evidence label for crawls with no verified HTML above.
    return best_category if best_score >= 3 else "General Website"


def feature_snapshot(site: SiteData) -> dict:
    # Exclude failed/error responses: their block-page HTML is not site evidence.
    pages = [p for p in site.pages if getattr(p, "analysis_eligible", True) and 200 <= getattr(p, "status", 0) < 400]
    return {
        "pages_scanned": len(pages),
        "h1_pages": sum(1 for p in pages if p.h1_count),
        "avg_response_ms": round(sum(p.response_ms for p in pages) / len(pages)) if pages else 0,
        "missing_alt_images": sum(sum(1 for x in p.images if not x.get("alt_present", bool(x.get("alt")))) for p in pages),
        "json_ld_pages": sum(1 for p in pages if p.json_ld),
        "social_ready_pages": sum(1 for p in pages if p.og_title and p.og_description),
        "security_header_coverage": round(100 * sum(sum(p.security_headers.values()) for p in pages) / (len(pages) * 6)) if pages else 0,
    }


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def _search_brave(query: str, limit: int) -> list[dict]:
    """Search a broad public web index when a Brave Search API key is configured."""
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        return []
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        params={"q": query, "count": min(max(limit, 1), 20), "safesearch": "moderate"},
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("web", {}).get("results", [])
    return [
        {"name": row.get("title", "").strip(), "url": row.get("url", ""), "snippet": row.get("description", "").strip(), "source": "Brave Search"}
        for row in rows if row.get("url", "").startswith(("https://", "http://"))
    ]


def _extract_result_url(href: str) -> str:
    """Resolve a DuckDuckGo result link to its actual HTTP(S) destination.

    DuckDuckGo may render result anchors as relative or absolute /l/?uddg=...
    redirect links. Only return a direct public-web URL, never the redirect URL.
    """
    href = (href or "").strip()
    if not href:
        return ""
    resolved = urljoin("https://duckduckgo.com", href)
    parsed = urlsplit(resolved)
    if (parsed.hostname or "").lower().removeprefix("www.") == "duckduckgo.com":
        if parsed.path.rstrip("/") != "/l":
            return ""
        destination = parse_qs(parsed.query).get("uddg", [""])[0]
        if not destination:
            return ""
        resolved = unquote(destination)
        parsed = urlsplit(resolved)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return ""
    if (parsed.hostname or "").lower().removeprefix("www.") == "duckduckgo.com":
        return ""
    return resolved


def _parse_duckduckgo_results(html: str, limit: int, source: str = "DuckDuckGo") -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    # The standard HTML endpoint and the lite endpoint use different markup.
    anchors = soup.select(".result__a, a.result-link")
    seen = set()
    for anchor in anchors:
        href = _extract_result_url(str(anchor.get("href", "")))
        name = anchor.get_text(" ", strip=True)
        if not href or not name or href in seen:
            continue
        seen.add(href)
        container = anchor.find_parent(class_=re.compile(r"result")) or anchor.parent
        snippet_node = (
            container.select_one(".result__snippet")
            or container.select_one(".result-snippet")
            or container.select_one(".result-snippet")
        ) if container else None
        out.append({
            "name": name,
            "url": href,
            "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
            "source": source,
        })
        if len(out) >= limit:
            break
    return out


def _search_duckduckgo(query: str, limit: int = 8) -> list[dict]:
    """Best-effort public HTML search with the lite endpoint as a fallback."""
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
    endpoints = [
        ("https://html.duckduckgo.com/html/", "DuckDuckGo"),
        ("https://lite.duckduckgo.com/lite/", "DuckDuckGo Lite"),
    ]
    for endpoint, source in endpoints:
        try:
            response = requests.get(endpoint, params={"q": query}, headers=headers, timeout=10)
            response.raise_for_status()
            results = _parse_duckduckgo_results(response.text, limit, source)
            logger.info("Similar-site %s search parsed %d results", source, len(results))
            if results:
                return results
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Similar-site %s request failed (%s)", source, type(exc).__name__)
    return []


def _search(query: str, limit: int = 8) -> list[dict]:
    """Use an optional configured index, then a bounded no-key best-effort fallback."""
    cache_key = query.strip().lower()
    now = time.monotonic()
    cached = _SEARCH_CACHE.get(cache_key)
    if cached and cached[0] > now:
        return cached[1][:limit]
    results: list[dict] = []
    try:
        results = _search_brave(query, limit)
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Configured search provider failed (%s); trying no-key fallback", type(exc).__name__)
    if not results:
        try:
            results = _search_duckduckgo(query, limit)
        except (requests.RequestException, ValueError) as exc:
            logger.warning("No-key search fallback failed (%s)", type(exc).__name__)
            results = []
    ttl = _SEARCH_CACHE_TTL_SECONDS if results else _SEARCH_EMPTY_TTL_SECONDS
    _SEARCH_CACHE[cache_key] = (now + ttl, results[:limit])
    if len(_SEARCH_CACHE) > 500:
        for key in [key for key, (expires, _) in _SEARCH_CACHE.items() if expires <= now]:
            _SEARCH_CACHE.pop(key, None)
        while len(_SEARCH_CACHE) > 500:
            _SEARCH_CACHE.pop(next(iter(_SEARCH_CACHE)))
    return results[:limit]

def _keywords(site: SiteData) -> list[str]:
    successful = [p for p in site.pages if getattr(p, "analysis_eligible", True) and 200 <= getattr(p, "status", 0) < 400]
    raw = " ".join(
        " ".join([p.title, p.description] + [heading for _, heading in p.headings[:8]])
        for p in successful[:5]
    ).lower()
    words = re.findall(r"[a-z][a-z0-9+-]{2,}", raw)
    stop = {
        "the", "and", "for", "with", "your", "you", "our", "from", "this", "that",
        "are", "was", "www", "com", "home", "page", "best", "more", "about", "all",
        "get", "use", "how", "into", "can", "not", "new", "now", "web", "site",
    }
    counts: dict[str, int] = {}
    for word in words:
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:6]]


def _curated_comparables(site_type: str) -> list[dict]:
    """Small transparent fallback catalog for common categories when web search fails."""
    kind = site_type.lower()
    catalogs = [
        (("video", "media", "streaming"), [
            ("Vimeo", "https://vimeo.com/", "Video hosting and creator-focused publishing.", "Video / Media Platform"),
            ("Dailymotion", "https://www.dailymotion.com/", "Video discovery and publishing platform.", "Video / Media Platform"),
            ("Twitch", "https://www.twitch.tv/", "Live-streaming and creator community platform.", "Video / Media Platform"),
        ]),
        (("search engine",), [
            ("Bing", "https://www.bing.com/", "Web search and discovery.", "Search Engine"),
            ("DuckDuckGo", "https://duckduckgo.com/", "Privacy-focused web search.", "Search Engine"),
            ("Brave Search", "https://search.brave.com/", "Independent web search.", "Search Engine"),
        ]),
        (("ai visual", "visual communication", "diagram", "whiteboard"), [
            ("Canva", "https://www.canva.com/", "Visual design and presentation creation.", "AI Visual Communication Tool"),
            ("Miro", "https://miro.com/", "Collaborative visual whiteboards and diagramming.", "AI Visual Communication Tool"),
            ("Whimsical", "https://whimsical.com/", "Flowcharts, wireframes, and visual collaboration.", "AI Visual Communication Tool"),
            ("Lucidchart", "https://www.lucidchart.com/", "Diagramming and visual documentation.", "AI Visual Communication Tool"),
        ]),
        (("coding practice", "education", "programming"), [
            ("HackerRank", "https://www.hackerrank.com/", "Programming challenges and technical skills practice.", "Coding Practice / Education"),
            ("Codewars", "https://www.codewars.com/", "Community-driven coding kata and practice.", "Coding Practice / Education"),
            ("Codeforces", "https://codeforces.com/", "Competitive programming contests and problems.", "Coding Practice / Education"),
            ("CodeChef", "https://www.codechef.com/", "Programming practice and competitive contests.", "Coding Practice / Education"),
        ]),
        (("e-commerce", "commerce", "online store"), [
            ("Etsy", "https://www.etsy.com/", "Online marketplace for independent sellers.", "E-commerce"),
            ("eBay", "https://www.ebay.com/", "Online marketplace for new and used goods.", "E-commerce"),
            ("Shopify", "https://www.shopify.com/", "Tools for building and operating online stores.", "E-commerce"),
        ]),
    ]
    for triggers, entries in catalogs:
        if any(trigger in kind for trigger in triggers):
            return [{"name": name, "url": url, "snippet": snippet, "source": "WebForge curated baseline", "website_type": category} for name, url, snippet, category in entries]
    return []

def _relevance(site_type: str, title: str, snippet: str, candidate_type: str) -> tuple[int, str]:
    text = (title + " " + snippet).lower()
    score = 35
    reasons = []
    if site_type.lower() in text:
        score += 25
        reasons.append(f"mentions the {site_type.lower()} category")
    if candidate_type == site_type:
        score += 25
        reasons.append("classified in the same website category")
    if any(word in text for word in ("alternative", "similar", "platform", "software", "tool", "service")):
        score += 8
        reasons.append("describes a related product or service")
    return min(score, 98), "; ".join(reasons) or "discovered from searches based on the target website's topic"


def discover_similar(site: SiteData, website_type: str, limit: int = 10) -> list[dict]:
    """Discover and rank similar public websites using multiple topic-specific web searches.

    Set BRAVE_SEARCH_API_KEY in the backend environment to use Brave's web index.
    DuckDuckGo HTML search is a best-effort fallback, not an exhaustive index.
    """
    root = _host(site.root_url)
    successful_pages = [p for p in site.pages if getattr(p, "analysis_eligible", True) and 200 <= getattr(p, "status", 0) < 400]
    title = successful_pages[0].title.strip() if successful_pages else ""
    description = successful_pages[0].description.strip() if successful_pages else ""
    keywords = _keywords(site)
    topics = [x for x in [title, description, " ".join(keywords)] if x]
    queries = [
        f'"{topics[0][:100]}" alternatives similar websites' if topics else f'{website_type} websites',
        f'{website_type} platforms tools alternatives',
    ]
    if keywords:
        queries.append(f'{" ".join(keywords[:4])} websites platform')
    candidates: dict[str, dict] = {}
    # Seed common categories so blocked/empty search providers cannot leave the
    # feature blank. Dynamic results are merged and ranked alongside these.
    for item in _curated_comparables(website_type):
        host = _host(item["url"])
        if host and host != root:
            candidates[host] = item
    search_result_count = 0
    for query in queries:
        results = _search(query, 10)
        search_result_count += len(results)
        for item in results:
            host = _host(item.get("url", ""))
            if not host or host == root or not item.get("name"):
                continue
            # Search engines may return the same site from several queries.
            if host not in candidates:
                candidates[host] = item
            elif len(item.get("snippet", "")) > len(candidates[host].get("snippet", "")):
                candidates[host] = item

    logger.info(
        "Similar-site discovery search phase complete: queries=%d raw_results=%d unique_candidates=%d",
        len(queries), search_result_count, len(candidates),
    )
    ranked = []
    crawl_failures = 0
    for host, item in list(candidates.items())[:12]:
        candidate_type = item.get("website_type", "Unverified")
        features = {}
        verified_url = item["url"]
        is_curated = item.get("source") == "WebForge curated baseline"
        verification_status = "curated-reference" if is_curated else "search-result-only"
        # Curated references are category-level suggestions, not live-crawl claims.
        # Dynamic search results are crawled when possible and retained if blocked.
        if not is_curated:
            try:
                candidate = crawl(verified_url, 1)
                if candidate.pages and 200 <= candidate.pages[0].status < 400:
                    verified_url = candidate.root_url
                    candidate_type = classify(candidate)
                    features = feature_snapshot(candidate)
                    verification_status = "crawl-verified"
                elif candidate.pages:
                    status = candidate.pages[0].status
                    verification_status = f"crawler-http-{status}" if status else "crawler-fetch-failed"
                    crawl_failures += 1
                else:
                    verification_status = "crawler-no-page"
                    crawl_failures += 1
            except Exception as exc:
                crawl_failures += 1
                verification_status = "crawler-unavailable"
                logger.debug("Similar-site candidate validation failed for %s (%s)", host, type(exc).__name__)
        if is_curated:
            if item.get("name") == "Twitch":
                match_type = "Adjacent alternative"
                reason = "Especially relevant to live streaming and creator communities; broader YouTube similarity is not verified."
            else:
                match_type = "Category reference"
                reason = "Curated example in the same broad category; product overlap has not been independently verified."
            ranking_score = 72  # Internal ordering only; never presented as a measured percentage.
        else:
            ranking_score, reason = _relevance(
                website_type, item.get("name", ""), item.get("snippet", ""), candidate_type
            )
            match_type = (
                "Same-category candidate"
                if verification_status == "crawl-verified" and candidate_type == website_type
                else "Search-discovered candidate"
            )
        ranked.append({
            "name": item["name"],
            "url": verified_url,
            "snippet": item.get("snippet", ""),
            "source": item.get("source", "Web search"),
            "website_type": candidate_type,
            "verification_status": verification_status,
            "features": features,
            "relevance_score": None,
            "match_type": match_type,
            "match_reason": reason,
            "_ranking_score": ranking_score,
        })
    # A private heuristic can order candidates, but it is not a user-facing similarity percentage.
    ranked.sort(key=lambda row: -row["_ranking_score"])
    for row in ranked:
        row.pop("_ranking_score", None)
    logger.info(
        "Similar-site discovery complete: accepted=%d candidate_validation_failures=%d",
        len(ranked), crawl_failures,
    )
    if candidates and not ranked:
        logger.warning(
            "Similar-site discovery found %d unique candidates but none passed candidate validation",
            len(candidates),
        )
    return ranked[:max(0, min(int(limit), 20))]


def opportunities(target: dict, similar: list[dict]) -> list[dict]:
    out = []
    if not target.get("social_ready_pages"):
        out.append({"title": "Own the share preview", "reason": "Important pages are not fully prepared for link sharing.", "action": "Add complete Open Graph and social preview metadata."})
    if not target.get("json_ld_pages"):
        out.append({"title": "Add structured search context", "reason": "No structured data was detected.", "action": "Add accurate JSON-LD that matches the website type and page content."})
    if target.get("missing_alt_images", 0) > 0:
        out.append({"title": "Make visuals searchable and accessible", "reason": "Image metadata is incomplete.", "action": "Add meaningful alt text and image dimensions."})
    if target.get("security_header_coverage", 100) < 70:
        out.append({"title": "Strengthen browser trust", "reason": "Several important response security headers are missing.", "action": "Configure and validate HSTS, CSP, framing, MIME, referrer, and permissions policies."})
    if similar and len(out) < 5:
        stronger = next((s for s in similar if s.get("features", {}).get("social_ready_pages", 0) > target.get("social_ready_pages", 0)), None)
        if stronger:
            out.append({"title": "Borrow a proven pattern, then differentiate", "reason": "A comparable site has stronger social-preview coverage.", "action": "Study its information hierarchy and build a differentiated version for your audience."})
    if not out:
        out.append({"title": "Differentiate on product value", "reason": "The baseline experience is comparatively healthy.", "action": "Add one distinctive workflow or feature that competitors cannot explain in one sentence."})
    return out[:5]
