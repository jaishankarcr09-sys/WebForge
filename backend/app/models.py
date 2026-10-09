from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Website(Base):
    __tablename__ = "websites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    audits: Mapped[list["Audit"]] = relationship(back_populates="website")

class Audit(Base):
    __tablename__ = "audits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("websites.id"), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    website: Mapped["Website"] = relationship(back_populates="audits")
    issues: Mapped[list["Issue"]] = relationship(back_populates="audit", cascade="all, delete-orphan")

class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_id: Mapped[int] = mapped_column(ForeignKey("audits.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    impact: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    audit: Mapped["Audit"] = relationship(back_populates="issues")


class AuditDetail(Base):
    __tablename__ = "wf_audit_details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_id: Mapped[int] = mapped_column(Integer, index=True)
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_scanned: Mapped[int] = mapped_column(Integer, default=0)
    scan_limit: Mapped[int] = mapped_column(Integer, default=10)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict)

class PageDetail(Base):
    __tablename__ = "wf_page_details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_id: Mapped[int] = mapped_column(Integer, index=True)
    url: Mapped[str] = mapped_column(Text)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    ttfb_ms: Mapped[int] = mapped_column(Integer, default=0)
    html_size: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(Text, default="")
    meta_description: Mapped[str] = mapped_column(Text, default="")
    canonical: Mapped[str] = mapped_column(Text, default="")
    h1_count: Mapped[int] = mapped_column(Integer, default=0)
    images_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_alt_count: Mapped[int] = mapped_column(Integer, default=0)
    external_scripts_count: Mapped[int] = mapped_column(Integer, default=0)
    internal_links_count: Mapped[int] = mapped_column(Integer, default=0)
    external_links_count: Mapped[int] = mapped_column(Integer, default=0)
    robots_indexable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)

class IssueDetail(Base):
    __tablename__ = "wf_issue_details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[int] = mapped_column(Integer, index=True)
    page_url: Mapped[str] = mapped_column(Text, default="")
    evidence: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    effort: Mapped[str] = mapped_column(String(16), default="medium")
    priority: Mapped[int] = mapped_column(Integer, default=50)
    code_before: Mapped[str] = mapped_column(Text, default="")
    code_after: Mapped[str] = mapped_column(Text, default="")
    layer: Mapped[str] = mapped_column(String(24), default="frontend")

class BackendMetrics(Base):
    __tablename__ = "webforge_backend_metrics"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    server: Mapped[str] = mapped_column(Text, default="")
    cache_control: Mapped[str] = mapped_column(Text, default="")
    content_encoding: Mapped[str] = mapped_column(Text, default="")
    etag: Mapped[bool] = mapped_column(Boolean, default=False)
    insecure_cookie_count: Mapped[int] = mapped_column(Integer, default=0)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0)

class AuditIntelligence(Base):
    __tablename__ = "webforge_audit_intelligence"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_type: Mapped[str] = mapped_column(Text, default="Unknown")
    frontend_score: Mapped[int] = mapped_column(Integer, default=0)
    backend_score: Mapped[int] = mapped_column(Integer, default=0)
    reach_score: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    similar_sites: Mapped[list] = mapped_column(JSON, default=list)
    opportunities: Mapped[list] = mapped_column(JSON, default=list)

class UserWebsite(Base):
    __tablename__ = "webforge_user_websites"
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, primary_key=True)

class UserAudit(Base):
    __tablename__ = "webforge_user_audits"
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True)

class UserProject(Base):
    __tablename__ = "webforge_user_projects"
    user_id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, primary_key=True)

class Schedule(Base):
    __tablename__ = "wf_schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    website_id: Mapped[int] = mapped_column(Integer, index=True)
    user_id: Mapped[str | None] = mapped_column(Uuid(as_uuid=False), nullable=True, index=True)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Project(Base):
    __tablename__ = "wf_project_catalog"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, default="")
    owner_key: Mapped[str] = mapped_column(Text, default="default")
