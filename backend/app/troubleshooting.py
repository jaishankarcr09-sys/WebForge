"""Evidence-first troubleshooting context for incomplete website audits.

This module classifies only recorded crawler facts. It does not crawl URLs,
infer hidden website state, or attempt to bypass access controls.
"""
from __future__ import annotations

from urllib.parse import urlsplit


def _failure_for_page(page: dict) -> str | None:
    status = page.get("status")
    note = str(page.get("crawl_note") or "").lower()
    content_type = str(page.get("content_type") or "").lower()
    final_url = str(page.get("final_url") or "")
    requested_url = str(page.get("url") or "")

    if isinstance(status, int) and status == 401:
        return "authentication_required"
    if isinstance(status, int) and status == 403:
        return "access_forbidden"
    if isinstance(status, int) and status == 429:
        return "rate_limited"
    if isinstance(status, int) and status >= 500:
        return "upstream_server_error"
    if isinstance(status, int) and status >= 400:
        return "http_error"
    if "authentication page" in note or _looks_like_login_redirect(requested_url, final_url):
        return "login_redirect"
    if "challenge" in note or "captcha" in note or "bot challenge" in note:
        return "challenge_or_access_interstitial"
    if "truncated" in note or page.get("html_truncated") is True:
        return "incomplete_response"
    if status is not None and not (200 <= status < 400):
        return "http_error"
    if "html" not in content_type:
        if content_type or "non-html" in note or "xml/resource" in note:
            return "non_html_response"
    if page.get("analysis_eligible") is False:
        return "content_not_eligible"
    return None


def _looks_like_login_redirect(requested_url: str, final_url: str) -> bool:
    if not requested_url or not final_url or requested_url == final_url:
        return False
    try:
        requested = urlsplit(requested_url)
        final = urlsplit(final_url)
    except ValueError:
        return False
    if requested.netloc.lower() != final.netloc.lower():
        return False
    parts = [part.lower() for part in final.path.split("/") if part]
    return any(part in {"login", "log-in", "signin", "sign-in", "authenticate"} for part in parts)


def _next_actions(reason_code: str) -> list[str]:
    actions = {
        "authentication_required": ["confirm_public_url", "request_permitted_public_test_url"],
        "access_forbidden": ["confirm_public_url", "review_site_owner_access_rules", "retry_later"],
        "rate_limited": ["reduce_scan_frequency", "retry_later"],
        "upstream_server_error": ["retry_later", "check_site_status"],
        "http_error": ["check_requested_url", "retry_later"],
        "login_redirect": ["confirm_public_url", "audit_login_page_as_separate_url"],
        "challenge_or_access_interstitial": ["review_site_owner_crawler_policy", "request_permitted_public_test_url"],
        "incomplete_response": ["retry_later", "review_response_size_or_timeout"],
        "non_html_response": ["confirm_expected_resource_type", "audit_html_page_url"],
        "content_not_eligible": ["review_recorded_crawl_warning", "retry_later"],
    }
    return actions.get(reason_code, ["review_recorded_crawl_warning"])


def build_troubleshooting_context(audit: dict) -> dict:
    """Return bounded, sanitized evidence for the UI or an evidence-grounded AI."""
    pages = audit.get("pages") if isinstance(audit.get("pages"), list) else []
    page_evidence = []
    for page in pages[:50]:
        if not isinstance(page, dict):
            continue
        reason_code = _failure_for_page(page)
        if reason_code is None:
            continue
        page_evidence.append({
            "url": str(page.get("url") or "")[:500],
            "final_url": str(page.get("final_url") or "")[:500],
            "http_status": page.get("status") if isinstance(page.get("status"), int) else None,
            "content_type": str(page.get("content_type") or "")[:120],
            "analysis_eligible": page.get("analysis_eligible") is True,
            "crawl_note": str(page.get("crawl_note") or "")[:500],
            "reason_code": reason_code,
            "allowed_actions": _next_actions(reason_code),
        })

    reliability = audit.get("dimensions", {}).get("audit_reliability", {})
    if not isinstance(reliability, dict):
        reliability = {}
    warnings = audit.get("crawl_warnings", reliability.get("crawl_warnings", []))
    if not isinstance(warnings, list):
        warnings = []
    sanitized_warnings = [
        {
            "url": str(item.get("url") or "")[:500],
            "reason": str(item.get("reason") or "")[:500],
            "status": item.get("status") if isinstance(item.get("status"), int) else None,
        }
        for item in warnings[:20]
        if isinstance(item, dict)
    ]
    return {
        "audit_id": audit.get("audit_id"),
        "requested_url": str(audit.get("url") or "")[:500],
        "score_status": str(audit.get("score_status") or "unknown"),
        "verified_pages": audit.get("verified_pages", 0),
        "unverified_pages": audit.get("unverified_pages", 0),
        "pages_discovered": audit.get("pages_discovered", 0),
        "pages_scanned": audit.get("pages_scanned", len(pages)),
        "crawl_coverage_percent": reliability.get("crawl_coverage_percent"),
        "page_failures": page_evidence,
        "crawl_warnings": sanitized_warnings,
        "policy": {
            "may_bypass_authentication": False,
            "may_bypass_captcha_or_bot_protection": False,
            "may_ignore_access_controls": False,
            "may_claim_unrecorded_action_succeeded": False,
        },
    }
