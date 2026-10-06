from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .analyzers import analyze, calculate_score
from .config import settings
from .db import get_db
from .models import Audit, Issue, Website
from .redis_client import ping
from .schemas import AuditRequest, AuditResponse

app = FastAPI(title="WebForge API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL unavailable") from exc

    return {"status": "ok", "postgres": db_status, "redis": ping()}


@app.post("/api/v1/audits/analyze", response_model=AuditResponse)
def create_audit(
    payload: AuditRequest,
    db: Session = Depends(get_db),
) -> AuditResponse:
    url = str(payload.url)

    try:
        from .scanner import scan_url

        scan = scan_url(url)
        findings = analyze(scan)
        score = calculate_score(findings)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to analyze URL: {exc}",
        ) from exc

    try:
        website = db.query(Website).filter(Website.url == url).first()
        if website is None:
            website = Website(url=url)
            db.add(website)
            db.flush()

        audit = Audit(
            website_id=website.id,
            score=score,
            status="completed",
        )
        db.add(audit)
        db.flush()

        for item in findings:
            db.add(
                Issue(
                    audit_id=audit.id,
                    category=item.category,
                    title=item.title,
                    severity=item.severity,
                    impact=item.impact,
                    recommendation=item.recommendation,
                )
            )

        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to persist audit results.",
        ) from exc

    return AuditResponse(
        audit_id=audit.id,
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
