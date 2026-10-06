from __future__ import annotations
import asyncio, csv, io
from datetime import datetime, timezone, timedelta
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .audit_engine import load_result, run_and_persist
from .ai import generate_ai_backlog, ticket_markdown
from .config import settings
from .db import get_db
from .job_store import create_job, get_job, update_job
from .models import Audit, Project, Schedule, UserAudit, UserProject, UserWebsite, Website
from .redis_client import ping
from .schemas import AuditRequest, AuditResponse, ScanJobResponse

app=FastAPI(title="WebForge API",version="0.6.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def current_user(x_webforge_user_id: str | None = Header(default=None)) -> str:
    if not x_webforge_user_id:
        raise HTTPException(status_code=401,detail="Please sign in to continue.")
    return x_webforge_user_id

def run_job(job_id:str,url:str,page_limit:int,user_id:str):
    from .db import SessionLocal
    db=SessionLocal()
    try:
        update_job(job_id,"running")
        result=run_and_persist(url,page_limit,db,user_id)
        update_job(job_id,"completed",result=result)
    except Exception as exc:
        db.rollback(); update_job(job_id,"failed",error=str(exc)[:500])
    finally: db.close()

@app.get("/health")
def health(db:Session=Depends(get_db)):
    try: db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc: raise HTTPException(status_code=503,detail="PostgreSQL unavailable") from exc
    return {"status":"ok","postgres":"ok","redis":ping()}

@app.post("/api/v1/audits/analyze",response_model=AuditResponse)
def create_audit(payload:AuditRequest,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    try:return AuditResponse(**run_and_persist(str(payload.url),payload.page_limit,db,user_id))
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=400,detail=str(exc)[:500]) from exc

@app.post("/api/v1/audits/scan",response_model=ScanJobResponse,status_code=202)
def queue_scan(payload:AuditRequest,background:BackgroundTasks,user_id:str=Depends(current_user)):
    job_id=create_job(str(payload.url),payload.page_limit,user_id)
    background.add_task(run_job,job_id,str(payload.url),payload.page_limit,user_id)
    return ScanJobResponse(job_id=job_id,status="queued")

@app.get("/api/v1/jobs/{job_id}")
def job_status(job_id:str,user_id:str=Depends(current_user)):
    job=get_job(job_id,user_id)
    if not job: raise HTTPException(status_code=404,detail="Job not found")
    return job

@app.get("/api/v1/audits/{audit_id}")
def audit_detail(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    try:return load_result(db,audit_id,user_id)
    except ValueError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc

@app.get("/api/v1/audits/{audit_id}/backlog")
def audit_backlog(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    result=load_result(db,audit_id,user_id)
    return {"audit_id":audit_id,"backlog":sorted(result["issues"],key=lambda x:-x.get("priority",50))}

@app.get("/api/v1/websites")
def websites(db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    rows=db.query(UserWebsite.website_id).filter(UserWebsite.user_id==user_id).all()
    ids=[x[0] for x in rows]
    if not ids:return []
    return [{"id":w.id,"url":w.url,"audits":db.query(UserAudit).filter(UserAudit.user_id==user_id).filter(UserAudit.audit_id.in_( [a.id for a in w.audits] )).count()} for w in db.query(Website).filter(Website.id.in_(ids)).order_by(Website.created_at.desc()).all()]

@app.get("/api/v1/websites/history")
def website_history(
    url:str|None=None,
    db:Session=Depends(get_db),
    user_id:str=Depends(current_user),
):
    audit_ids=[x.audit_id for x in db.query(UserAudit).filter_by(user_id=user_id).all()]
    if not audit_ids:
        return []

    query=db.query(Audit).filter(Audit.id.in_(audit_ids))
    if url:
        website=db.query(Website).filter(Website.url==url).first()
        if not website or not db.query(UserWebsite).filter_by(user_id=user_id,website_id=website.id).first():
            return []
        query=query.filter(Audit.website_id==website.id)

    return [
        {
            "audit_id":a.id,
            "url":a.website.url,
            "score":a.score,
            "status":a.status,
            "created_at":a.created_at.isoformat(),
        }
        for a in query.order_by(Audit.created_at.desc()).all()
    ]

@app.get("/api/v1/audits/compare")
def compare_audits(left:int=Query(...),right:int=Query(...),db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    a,b=load_result(db,left,user_id),load_result(db,right,user_id)
    li={x["title"] for x in a["issues"]}; ri={x["title"] for x in b["issues"]}
    return {"left":a["score"],"right":b["score"],"delta":b["score"]-a["score"],"resolved":sorted(li-ri),"new":sorted(ri-li)}

@app.get("/api/v1/audits/{audit_id}/export.json")
def export_json(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):return JSONResponse(load_result(db,audit_id,user_id))

@app.get("/api/v1/audits/{audit_id}/export.csv")
def export_csv(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    result=load_result(db,audit_id,user_id); out=io.StringIO(); fields=["category","title","severity","priority","effort","confidence","page_url","evidence","recommendation"]
    writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader()
    for item in result["issues"]:writer.writerow({k:item.get(k,"") for k in fields})
    return PlainTextResponse(out.getvalue(),media_type="text/csv")

@app.get("/api/v1/audits/{audit_id}/export.pdf")
def export_pdf(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    from .report_pdf import render_pdf
    pdf=render_pdf(load_result(db,audit_id,user_id))
    return Response(pdf,media_type="application/pdf",headers={"Content-Disposition":f"attachment; filename=webforge-audit-{audit_id}.pdf"})

@app.post("/api/v1/audits/{audit_id}/ai")
def ai_backlog(audit_id:int,db:Session=Depends(get_db),user_id:str=Depends(current_user)):return generate_ai_backlog(load_result(db,audit_id,user_id))

@app.get("/api/v1/audits/{audit_id}/ticket")
def ticket(audit_id:int,issue_index:int=0,kind:str="github",db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    result=load_result(db,audit_id,user_id); issues=result["issues"]
    if not issues:raise HTTPException(status_code=404,detail="No issues")
    if issue_index<0 or issue_index>=len(issues):raise HTTPException(status_code=400,detail="Invalid issue index")
    return {"kind":kind,"markdown":ticket_markdown(result,issues[issue_index],kind)}

@app.post("/api/v1/projects")
def create_project(name:str,description:str="",db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    project=Project(name=name,description=description,owner_key=user_id); db.add(project); db.flush(); db.add(UserProject(user_id=user_id,project_id=project.id)); db.commit()
    return {"id":project.id,"name":project.name,"description":project.description}

@app.get("/api/v1/projects")
def list_projects(db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    ids=[x.project_id for x in db.query(UserProject).filter_by(user_id=user_id).all()]
    if not ids:return []
    return [{"id":p.id,"name":p.name,"description":p.description} for p in db.query(Project).filter(Project.id.in_(ids)).order_by(Project.id.desc()).all()]

@app.post("/api/v1/schedules")
def create_schedule(url:str,interval_minutes:int=1440,db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    if interval_minutes<5:raise HTTPException(status_code=400,detail="Interval must be at least 5 minutes")
    website=db.query(Website).filter(Website.url==url).first()
    if not website:website=Website(url=url);db.add(website);db.flush()
    if not db.query(UserWebsite).filter_by(user_id=user_id,website_id=website.id).first():db.add(UserWebsite(user_id=user_id,website_id=website.id))
    row=Schedule(website_id=website.id,user_id=user_id,interval_minutes=interval_minutes,next_run_at=datetime.now(timezone.utc)+timedelta(minutes=interval_minutes));db.add(row);db.commit()
    return {"id":row.id,"url":url,"interval_minutes":interval_minutes,"enabled":True}

@app.get("/api/v1/schedules")
def list_schedules(db:Session=Depends(get_db),user_id:str=Depends(current_user)):
    rows=db.query(Schedule).filter(Schedule.user_id==user_id).all()
    return [{"id":s.id,"website_id":s.website_id,"interval_minutes":s.interval_minutes,"enabled":s.enabled,"next_run_at":s.next_run_at.isoformat()} for s in rows]

@app.on_event("startup")
async def schedule_loop():
    async def loop():
        from .db import SessionLocal
        while True:
            await asyncio.sleep(60)
            db=SessionLocal()
            try:
                now=datetime.now(timezone.utc)
                rows=db.query(Schedule).filter(Schedule.enabled.is_(True),Schedule.next_run_at<=now,Schedule.user_id.is_not(None)).all()
                for row in rows:
                    website=db.get(Website,row.website_id)
                    if website:
                        try:run_and_persist(website.url,10,db,row.user_id)
                        except Exception:db.rollback()
                    row.last_run_at=now;row.next_run_at=now+timedelta(minutes=row.interval_minutes);db.commit()
            finally:db.close()
    asyncio.create_task(loop())
