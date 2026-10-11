"""Collect minimal metadata from an explicit list of public URLs.

This tool does not discover or recursively crawl links. It checks robots.txt, makes at
most one HTML request per supplied URL, applies a per-host delay, and stores metadata
rather than full page bodies. Use only URLs you are permitted to access.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

USER_AGENT = "WebForgeResearchBot/0.1 (+https://github.com/jaishankarcr09-sys/WebForge; public metadata research)"


def parse_metadata(html: str, url: str, category: str = "") -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else ""
    description = ""
    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            description = " ".join(str(tag["content"]).split())[:1000]
            break
    og_title = soup.find("meta", property="og:title")
    if not title and og_title and og_title.get("content"):
        title = " ".join(str(og_title["content"]).split())
    return {
        "url": url,
        "hostname": (urlparse(url).hostname or "").lower(),
        "title": " ".join(title.split())[:300],
        "description": description,
        "category": category.strip()[:120],
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": "public_metadata_single_page",
    }


def robots_allows(url: str, session: requests.Session, timeout: float = 8.0) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = session.get(robots_url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        if response.status_code == 404:
            return True
        if response.status_code >= 400:
            return False
        parser.parse(response.text.splitlines())
        return parser.can_fetch(USER_AGENT, url) and parser.can_fetch("*", url)
    except requests.RequestException:
        # Fail closed if robots policy cannot be checked.
        return False


def collect_one(url: str, category: str = "", session: requests.Session | None = None,
                timeout: float = 10.0) -> dict:
    session = session or requests.Session()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return {"url": url, "status": "rejected", "reason": "only absolute HTTP(S) URLs are accepted"}
    if not robots_allows(url, session, timeout=min(timeout, 8.0)):
        return {"url": url, "status": "skipped", "reason": "robots policy disallows access or could not be checked"}
    try:
        response = session.get(url, timeout=timeout, allow_redirects=True,
                               headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        content_type = response.headers.get("content-type", "").lower()
        if response.status_code >= 400:
            return {"url": url, "status": "skipped", "reason": f"http_{response.status_code}"}
        if "text/html" not in content_type:
            return {"url": url, "status": "skipped", "reason": "non_html_response"}
        final_url = response.url
        return {"status": "collected", **parse_metadata(response.text[:1_500_000], final_url, category)}
    except requests.RequestException as exc:
        return {"url": url, "status": "error", "reason": type(exc).__name__}


def read_seed_csv(path: str | Path) -> list[dict[str, str]]:
    import csv
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "url" not in reader.fieldnames:
            raise ValueError("Seed CSV must include a 'url' column and may include 'category'.")
        return [{"url": (row.get("url") or "").strip(),
                 "category": (row.get("category") or "").strip()} for row in reader if (row.get("url") or "").strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="CSV with url,category columns")
    parser.add_argument("--output", default="backend/data/public_site_metadata.jsonl")
    parser.add_argument("--delay", type=float, default=2.0, help="minimum delay between requests to same host")
    args = parser.parse_args()
    if args.delay < 1.0:
        raise SystemExit("--delay must be at least 1 second.")
    seeds = read_seed_csv(args.input)
    session = requests.Session()
    last_host_time: dict[str, float] = {}
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    collected = skipped = 0
    with output_path.open("w", encoding="utf-8") as out:
        for seed in seeds:
            host = (urlparse(seed["url"]).hostname or "").lower()
            wait = args.delay - (time.monotonic() - last_host_time.get(host, 0))
            if host and wait > 0:
                time.sleep(wait)
            result = collect_one(seed["url"], seed["category"], session)
            if host:
                last_host_time[host] = time.monotonic()
            out.write(json.dumps(result, ensure_ascii=False) + "\n")
            collected += result.get("status") == "collected"
            skipped += result.get("status") != "collected"
            print(f'{result.get("status")}: {seed["url"]}')
    print(json.dumps({"input_urls": len(seeds), "collected": collected, "skipped_or_errors": skipped,
                      "output": str(output_path)}, indent=2))


if __name__ == "__main__":
    main()
