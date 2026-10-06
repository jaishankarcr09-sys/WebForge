from __future__ import annotations
import time
from sqlalchemy.orm import Session
from .analyzers import analyze, score
from .models import Audit, Issue, Website, AuditDetail, PageDetail, IssueDetail
from .site_scan import crawl
from .browser_metrics import measure

def run_and_persist(url: str, page_limit: int, db: Session) -> dict:
    started = time.perf_counter()
    site = crawl(url, page_limit)
    findings = analyze(site)
    overall, dimensions = score(findings)
    browser = measure(site.root_url)
    dimensions["browser"] = browser
    website = db.query(Website).filter(Website.url == site.root_url).first()
    if website is None:
        website = Website(url=site.root_url)
        db.add(website)
        db.flush()
    audit = Audit(website_id=website.id, score=overall, status="completed")
    db.add(audit)
    db.flush()
    detail = AuditDetail(audit_id=audit.id, pages_discovered=len(site.discovered), pages_scanned=len(site.pages), scan_limit=page_limit, duration_ms=int((time.perf_counter()-started)*1000), dimensions=dimensions)
    db.add(detail)
    for p in site.pages:
        db.add(PageDetail(audit_id=audit.id,url=p.url,status_code=p.status,response_time_ms=p.response_ms,ttfb_ms=p.ttfb_ms,html_size=p.html_bytes,title=p.title,meta_description=p.description,canonical=p.canonical,h1_count=p.h1_count,images_count=len(p.images),missing_alt_count=sum(1 for x in p.images if not x.get("alt")),external_scripts_count=p.scripts,internal_links_count=len(p.internal_links),external_links_count=len(p.external_links),robots_indexable=not p.noindex,data=p.__dict__))
    for f in findings:
        issue=Issue(audit_id=audit.id,category=f.category,title=f.title,severity=f.severity,impact=f.impact,recommendation=f.recommendation)
        db.add(issue); db.flush()
        db.add(IssueDetail(issue_id=issue.id,page_url=f.page_url,evidence=f.evidence,confidence=f.confidence,effort=f.effort,priority=f.priority,code_before=f.code_before,code_after=f.code_after))
    db.commit()
    return build_result(audit,detail,findings,site,dimensions)

def build_result(audit,detail,findings,site,dimensions):
    return {"audit_id":audit.id,"url":site.root_url,"score":audit.score,"dimensions":dimensions,"pages_discovered":len(site.discovered),"pages_scanned":len(site.pages),"scan_limit":detail.scan_limit,"duration_ms":detail.duration_ms,"robots_present":site.robots_present,"sitemap_present":site.sitemap_present,"broken_links":site.broken_links,"pages":[p.__dict__ for p in site.pages],"issues":[f.asdict() for f in sorted(findings,key=lambda x:(-x.priority,x.severity,x.title))]}

def load_result(db: Session,audit_id:int)->dict:
    audit=db.get(Audit,audit_id)
    if not audit: raise ValueError("Audit not found")
    detail=db.query(AuditDetail).filter_by(audit_id=audit.id).first()
    pages=db.query(PageDetail).filter_by(audit_id=audit.id).all()
    issues=db.query(Issue).filter_by(audit_id=audit.id).all()
    ids=[x.id for x in issues]
    extra={d.issue_id:d for d in db.query(IssueDetail).filter(IssueDetail.issue_id.in_(ids)).all()} if ids else {}
    return {"audit_id":audit.id,"url":audit.website.url,"score":audit.score,"dimensions":detail.dimensions if detail else {},"pages_discovered":detail.pages_discovered if detail else len(pages),"pages_scanned":detail.pages_scanned if detail else len(pages),"scan_limit":detail.scan_limit if detail else len(pages),"duration_ms":detail.duration_ms if detail else 0,"pages":[p.data for p in pages],"issues":[dict(category=i.category,title=i.title,severity=i.severity,impact=i.impact,recommendation=i.recommendation,page_url=extra.get(i.id).page_url if i.id in extra else "",evidence=extra.get(i.id).evidence if i.id in extra else "",confidence=extra.get(i.id).confidence if i.id in extra else 100,effort=extra.get(i.id).effort if i.id in extra else "medium",priority=extra.get(i.id).priority if i.id in extra else 50,code_before=extra.get(i.id).code_before if i.id in extra else "",code_after=extra.get(i.id).code_after if i.id in extra else "") for i in issues]}
