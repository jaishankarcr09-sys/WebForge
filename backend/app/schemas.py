from pydantic import BaseModel, HttpUrl

class AuditRequest(BaseModel):
    url: HttpUrl

class IssueOut(BaseModel):
    category: str
    title: str
    severity: str
    impact: str
    recommendation: str

class AuditResponse(BaseModel):
    url: str
    score: int
    issues: list[IssueOut]
