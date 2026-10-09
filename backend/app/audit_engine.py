from __future__ import annotations
import time
from sqlalchemy.orm import Session

from .full_analyzer import analyze, score
from .models import (
    Audit, AuditDetail, AuditIntelligence, Issue, IssueDetail, PageDetail,
    UserAudit, UserWebsite, Website,
)
from .site_scan import crawl
from .browser_metrics import measure
from .site_intelligence import classify, discover_similar, feature_snapshot, opportunities

def run_and_persist(url: str, page_limit: int, db: Session, user_id: str | None = None) -> dict:
    started=time.perf_counter()
    site=crawl(url,page_limit)
    findings=analyze(site)
    overall,dimensions=score(findings)
    verified_pages=sum(1 for p in site.pages if getattr(p,"analysis_eligible",True) and 200 <= p.status < 400)
    unverified_pages=len(site.pages)-verified_pages
    coverage=round(100*verified_pages/len(site.pages)) if site.pages else 0
    score_status="verified" if verified_pages else "insufficient_verified_data"
    if not verified_pages:
        # The legacy database score column is integer-only; the UI must display this as unavailable.
        overall=0
    dimensions["audit_reliability"]={
        "score_status":score_status,
        "verified_pages":verified_pages,
        "unverified_pages":unverified_pages,
        "crawl_coverage_percent":coverage,
        "crawl_warnings":site.crawl_warnings,
    }
    browser=measure(site.root_url)
    dimensions["browser"]=browser
    website=db.query(Website).filter(Website.url==site.root_url).first()
    if website is None:
        website=Website(url=site.root_url); db.add(website); db.flush()
    if user_id and not db.query(UserWebsite).filter_by(user_id=user_id,website_id=website.id).first():
        db.add(UserWebsite(user_id=user_id,website_id=website.id))
    audit=Audit(website_id=website.id,score=overall,status="completed")
    db.add(audit); db.flush()
    if user_id:
        db.add(UserAudit(user_id=user_id,audit_id=audit.id))
    detail=AuditDetail(
        audit_id=audit.id,
        pages_discovered=len(site.discovered),
        pages_scanned=len(site.pages),
        scan_limit=page_limit,
        duration_ms=int((time.perf_counter()-started)*1000),
        dimensions=dimensions,
    )
    db.add(detail)
    for p in site.pages:
        db.add(PageDetail(
            audit_id=audit.id,url=p.url,status_code=p.status,response_time_ms=p.response_ms,ttfb_ms=p.ttfb_ms,
            html_size=p.html_bytes,title=p.title,meta_description=p.description,canonical=p.canonical,
            h1_count=p.h1_count,images_count=len(p.images),
            missing_alt_count=sum(1 for x in p.images if not x.get("alt")),
            external_scripts_count=p.scripts,internal_links_count=len(p.internal_links),
            external_links_count=len(p.external_links),robots_indexable=not p.noindex,
            data=p.__dict__,
        ))
    website_type=classify(site)
    features=feature_snapshot(site)
    similar=discover_similar(site,website_type,3)
    growth=opportunities(features,similar)
    frontend_score=int(dimensions.get("frontend",dimensions.get("seo",0)))
    backend_score=int(dimensions.get("backend",dimensions.get("security",0)))
    reach_score=round((int(dimensions.get("seo",0))*0.65)+((100 if site.sitemap_present else 55)*0.15)+(100 if site.robots_present else 55)*0.1+(int(dimensions.get("accessibility",0))*0.1))
    intelligence=AuditIntelligence(
        audit_id=audit.id,
        website_type=website_type,
        frontend_score=frontend_score,
        backend_score=backend_score,
        reach_score=max(0,min(100,reach_score)),
        summary=f"This looks like a {website_type.lower()}. WebForge found {len(findings)} actionable findings across {verified_pages} verified page(s); {unverified_pages} page(s) could not be fully verified.",
        features=features,
        similar_sites=similar,
        opportunities=growth,
    )
    db.add(intelligence)
    for f in findings:
        issue=Issue(audit_id=audit.id,category=f.category,title=f.title,severity=f.severity,impact=f.impact,recommendation=f.recommendation)
        db.add(issue); db.flush()
        db.add(IssueDetail(
            issue_id=issue.id,page_url=f.page_url,evidence=f.evidence,confidence=f.confidence,
            effort=f.effort,priority=f.priority,code_before=f.code_before,code_after=f.code_after,layer=f.layer
        ))
    db.commit()
    return load_result(db,audit.id,user_id,extra={
        "robots_present": site.robots_present,
        "sitemap_present": site.sitemap_present,
        "broken_links": site.broken_links,
        "crawl_warnings": site.crawl_warnings,
        "verified_pages": verified_pages,
        "unverified_pages": unverified_pages,
        "score_status": score_status,
    })

def load_result(db: Session, audit_id: int, user_id: str | None = None, extra: dict | None = None) -> dict:
    audit=db.get(Audit,audit_id)
    if not audit: raise ValueError("Audit not found")
    if user_id and not db.query(UserAudit).filter_by(user_id=user_id,audit_id=audit_id).first():
        raise ValueError("Audit not found")
    detail=db.query(AuditDetail).filter_by(audit_id=audit.id).first()
    pages=db.query(PageDetail).filter_by(audit_id=audit.id).all()
    issues=db.query(Issue).filter_by(audit_id=audit.id).all()
    ids=[x.id for x in issues]
    extras={d.issue_id:d for d in db.query(IssueDetail).filter(IssueDetail.issue_id.in_(ids)).all()} if ids else {}
    intel=db.get(AuditIntelligence,audit_id)
    result={
        "audit_id":audit.id,"url":audit.website.url,"score":audit.score,
        "score_status":(detail.dimensions.get("audit_reliability",{}).get("score_status","verified") if detail else "verified"),
        "verified_pages":(detail.dimensions.get("audit_reliability",{}).get("verified_pages",len(pages)) if detail else len(pages)),
        "unverified_pages":(detail.dimensions.get("audit_reliability",{}).get("unverified_pages",0) if detail else 0),
        "crawl_warnings":(detail.dimensions.get("audit_reliability",{}).get("crawl_warnings",[]) if detail else []),
        "dimensions":detail.dimensions if detail else {},
        "pages_discovered":detail.pages_discovered if detail else len(pages),
        "pages_scanned":detail.pages_scanned if detail else len(pages),
        "scan_limit":detail.scan_limit if detail else len(pages),
        "duration_ms":detail.duration_ms if detail else 0,
        "website_type":intel.website_type if intel else "Unknown",
        "frontend_score":intel.frontend_score if intel else 0,
        "backend_score":intel.backend_score if intel else 0,
        "reach_score":intel.reach_score if intel else 0,
        "intelligence_summary":intel.summary if intel else "",
        "features":intel.features if intel else {},
        "similar_sites":intel.similar_sites if intel else [],
        "opportunities":intel.opportunities if intel else [],
        "pages":[p.data for p in pages],
        "issues":[dict(
            category=i.category,title=i.title,severity=i.severity,impact=i.impact,recommendation=i.recommendation,
            page_url=extras.get(i.id).page_url if i.id in extras else "",
            evidence=extras.get(i.id).evidence if i.id in extras else "",
            confidence=extras.get(i.id).confidence if i.id in extras else 100,
            effort=extras.get(i.id).effort if i.id in extras else "medium",
            priority=extras.get(i.id).priority if i.id in extras else 50,
            code_before=extras.get(i.id).code_before if i.id in extras else "",
            code_after=extras.get(i.id).code_after if i.id in extras else "",
            layer=extras.get(i.id).layer if i.id in extras else "frontend",
        ) for i in issues]
    }
    if extra:
        result.update(extra)
    return result
