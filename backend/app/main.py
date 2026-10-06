from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .analyzers import analyze, calculate_score
from .config import settings
from .db import Base, engine
from .redis_client import ping
from .schemas import AuditRequest, AuditResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="WebForge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "redis": ping()}

@app.post("/api/v1/audits/analyze", response_model=AuditResponse)
def create_audit(payload: AuditRequest) -> AuditResponse:
    url = str(payload.url)
    try:
        from .scanner import scan_url
        scan = scan_url(url)
        findings = analyze(scan)
        score = calculate_score(findings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to analyze URL: {exc}") from exc

    return AuditResponse(
        url=url,
        score=score,
        issues=[
            {
                "category": item.category,
                "title": item.title,
                "severity": item.severity,
                "impact": item.impact,
                "recommendation": item.recommendation,
            }
            for item in findings
        ],
    )
