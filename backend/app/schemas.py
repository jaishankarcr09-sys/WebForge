from pydantic import BaseModel, Field, HttpUrl

class AuditRequest(BaseModel):
    url: HttpUrl
    page_limit: int = Field(default=10, ge=1, le=30)

class IssueOut(BaseModel):
    category: str
    title: str
    severity: str
    impact: str
    recommendation: str
    page_url: str = ""
    evidence: str = ""
    confidence: int = 100
    effort: str = "medium"
    priority: int = 50
    code_before: str = ""
    code_after: str = ""
    layer: str = "frontend"

class AuditResponse(BaseModel):
    audit_id: int
    url: str
    score: int
    score_status: str = "verified"
    verified_pages: int = 0
    unverified_pages: int = 0
    crawl_warnings: list[dict] = []
    dimensions: dict = {}
    pages_discovered: int = 0
    pages_scanned: int = 0
    scan_limit: int = 10
    duration_ms: int = 0
    robots_present: bool = False
    sitemap_present: bool = False
    broken_links: list[dict] = []
    link_check_warnings: list[dict] = []
    pages: list[dict] = []
    website_type: str = "Unknown"
    frontend_score: int = 0
    backend_score: int = 0
    reach_score: int = 0
    intelligence_summary: str = ""
    features: dict = {}
    similar_sites: list[dict] = []
    opportunities: list[dict] = []
    issues: list[IssueOut] = []

class ScanJobResponse(BaseModel):
    job_id: str
    status: str
