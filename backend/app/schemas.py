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

class AuditResponse(BaseModel):
    audit_id: int
    url: str
    score: int
    dimensions: dict
    pages_discovered: int
    pages_scanned: int
    scan_limit: int
    duration_ms: int
    robots_present: bool = False
    sitemap_present: bool = False
    broken_links: list[dict] = []
    pages: list[dict] = []
    issues: list[IssueOut] = []

class ScanJobResponse(BaseModel):
    job_id: str
    status: str
