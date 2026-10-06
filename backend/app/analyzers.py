from dataclasses import dataclass
from .scanner import ScanResult

SEVERITY_WEIGHT = {"critical": 25, "high": 15, "medium": 8, "low": 3}

@dataclass
class Finding:
    category: str
    title: str
    severity: str
    impact: str
    recommendation: str

def analyze(scan: ScanResult) -> list[Finding]:
    soup = scan.soup
    findings: list[Finding] = []

    title = soup.find("title")
    if title is None or not title.get_text(strip=True):
        findings.append(Finding(
            "SEO", "Missing page title", "high",
            "Search engines and users lose an important signal about page purpose.",
            "Add a unique, descriptive <title> element.",
        ))

    meta_description = soup.find(
        "meta",
        attrs={"name": lambda value: value and value.lower() == "description"},
    )
    if meta_description is None or not meta_description.get("content", "").strip():
        findings.append(Finding(
            "SEO", "Missing meta description", "medium",
            "Search results may lack a useful page summary.",
            "Add a concise, relevant meta description.",
        ))

    h1_tags = soup.find_all("h1")
    if not h1_tags:
        findings.append(Finding(
            "Technical", "Missing H1 heading", "high",
            "The page has no clear primary heading for users and assistive technologies.",
            "Add one descriptive H1 representing the page's main topic.",
        ))
    elif len(h1_tags) > 1:
        findings.append(Finding(
            "Technical", "Multiple H1 headings", "low",
            "Multiple primary headings can make document structure less clear.",
            "Keep one primary H1 and use H2/H3 headings for subsections.",
        ))

    images = soup.find_all("img")
    missing_alt = [img for img in images if not img.get("alt", "").strip()]
    if missing_alt:
        findings.append(Finding(
            "Accessibility", f"{len(missing_alt)} image(s) missing alt text", "medium",
            "Screen-reader users may not receive the meaning or purpose of informative images.",
            "Add meaningful alt text to informative images; use empty alt text for decorative images.",
        ))

    scripts = soup.find_all("script", src=True)
    if len(scripts) > 20:
        findings.append(Finding(
            "Performance", f"High external script count ({len(scripts)})", "medium",
            "Many JavaScript resources can increase network and execution overhead.",
            "Audit third-party scripts, remove unused dependencies, and defer non-critical scripts.",
        ))

    if scan.html_size > 500_000:
        findings.append(Finding(
            "Performance", f"Large HTML document ({scan.html_size // 1024} KB)", "medium",
            "Large HTML increases initial transfer cost and can delay page rendering.",
            "Reduce unnecessary markup and compress responses.",
        ))

    return findings

def calculate_score(findings: list[Finding]) -> int:
    return max(0, min(100, 100 - sum(SEVERITY_WEIGHT[x.severity] for x in findings)))
