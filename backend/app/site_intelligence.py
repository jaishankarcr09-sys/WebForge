from __future__ import annotations

import logging
import os
import re
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from .site_scan import SiteData, crawl

logger = logging.getLogger(__name__)


def classify(site: SiteData) -> str:
    text = " ".join(
        (p.title + " " + p.description + " " + " ".join(x[1] for x in p.headings)).lower()
        for p in site.pages
    )
    rules = [
        ("E-commerce", ["cart", "checkout", "product", "shop", "add to cart", "price"]),
        ("SaaS / Web App", ["dashboard", "sign in", "login", "workspace", "app", "pricing", "free trial"]),
        ("Blog / Publication", ["blog", "article", "author", "news", "post", "read more"]),
        ("Portfolio / Agency", ["portfolio", "case study", "projects", "work with us"]),
        ("Education", ["course", "lesson", "student", "academy", "university", "learn"]),
        ("Media", ["video", "watch", "episode", "stream", "subscribe"]),
        ("Business / Service", ["services", "solutions", "contact", "about us", "company"]),
    ]
    best = "General Website"
    best_score = 0
    for name, terms in rules:
        current = sum(text.count(t) for t in terms)
        if current > best_score:
            best, best_score = name, current
    return best


def feature_snapshot(site: SiteData) -> dict:
    pages = site.pages
    return {
        "pages_scanned": len(pages),
        "h1_pages": sum(1 for p in pages if p.h1_count),
        "avg_response_ms": round(sum(p.response_ms for p in pages) / len(pages)) if pages else 0,
        "missing_alt_images": sum(sum(1 for x in p.images if not x.get("alt")) for p in pages),
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
    """Prefer the configured web index; fall back to public HTML search."""
    try:
        results = _search_brave(query, limit)
        if results:
            return results
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("Similar-site Brave search failed; using DuckDuckGo fallback (%s)", type(exc).__name__)
    try:
        results = _search_duckduckgo(query, limit)
        if not results:
            logger.info("Similar-site search returned no results for query")
        return results
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Similar-site DuckDuckGo search failed (%s)", type(exc).__name__)
        return []


def _keywords(site: SiteData) -> list[str]:
    raw = " ".join(
        " ".join([p.title, p.description] + [heading for _, heading in p.headings[:8]])
        for p in site.pages[:5]
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
    title = site.pages[0].title.strip() if site.pages else ""
    description = site.pages[0].description.strip() if site.pages else ""
    keywords = _keywords(site)
    topics = [x for x in [title, description, " ".join(keywords)] if x]
    queries = [
        f'"{topics[0][:100]}" alternatives similar websites' if topics else f'{website_type} websites',
        f'{website_type} platforms tools alternatives',
    ]
    if keywords:
        queries.append(f'{" ".join(keywords[:4])} websites platform')
    if description:
        queries.append(f'{description[:100]} alternatives')
    candidates: dict[str, dict] = {}
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
    for host, item in candidates.items():
        candidate_type = "Unknown"
        features = {}
        verified_url = item["url"]
        # Verify that the candidate is crawlable before showing it. Never let one
        # inaccessible candidate fail the whole discovery run.
        try:
            candidate = crawl(verified_url, 1)
            if not candidate.pages or candidate.pages[0].status < 200 or candidate.pages[0].status >= 400:
                continue
            verified_url = candidate.root_url
            candidate_type = classify(candidate)
            features = feature_snapshot(candidate)
        except Exception as exc:
            crawl_failures += 1
            logger.debug("Similar-site candidate validation failed for %s (%s)", host, type(exc).__name__)
            continue
        relevance, reason = _relevance(
            website_type, item.get("name", ""), item.get("snippet", ""), candidate_type
        )
        ranked.append({
            "name": item["name"],
            "url": verified_url,
            "snippet": item.get("snippet", ""),
            "source": item.get("source", "Web search"),
            "website_type": candidate_type,
            "features": features,
            "relevance_score": relevance,
            "match_reason": reason,
        })
    ranked.sort(key=lambda row: (-row["relevance_score"], row["name"].lower()))
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
