"use client";

import { FormEvent, useMemo, useState } from "react";

type Issue = {category:string; title:string; severity:string; impact:string; recommendation:string; page_url:string; evidence:string; confidence:number; effort:string; priority:number; code_after:string};
type Page = {url:string; status:number; response_ms:number; ttfb_ms:number; html_bytes:number; title:string; description:string; canonical:string; h1_count:number; images:any[]; scripts:number};
type Audit = {audit_id:number; url:string; score:number; dimensions:Record<string,any>; pages_discovered:number; pages_scanned:number; duration_ms:number; robots_present:boolean; sitemap_present:boolean; broken_links:any[]; pages:Page[]; issues:Issue[]};
type History = {audit_id:number; score:number; status:string; created_at:string};

const label:Record<string,string>={seo:"SEO",performance:"Performance",accessibility:"Accessibility",security:"Security",technical:"Technical"};

export default function Home(){
  const [url,setUrl]=useState("");
  const [limit,setLimit]=useState(10);
  const [audit,setAudit]=useState<Audit|null>(null);
  const [history,setHistory]=useState<History[]>([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const [tab,setTab]=useState("overview");
  const [filter,setFilter]=useState("all");
  const [ai,setAi]=useState<any>(null);
  const [ticket,setTicket]=useState("");
  const [projectName,setProjectName]=useState("");
  const [projectMsg,setProjectMsg]=useState("");

  const runAudit=async(e:FormEvent)=>{
    e.preventDefault(); setLoading(true); setError(""); setAudit(null); setAi(null); setTicket("");
    try{
      const r=await fetch("/api/audits/scan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url,page_limit:limit})});
      const data=await r.json();
      if(!r.ok) throw new Error(data.detail || "Could not start scan");
      let done:any=null;
      for(let i=0;i<180;i++){
        await new Promise(x=>setTimeout(x,1000));
        const s=await fetch("/api/audits/jobs/"+data.job_id,{cache:"no-store"});
        const state=await s.json();
        if(state.status==="completed"){done=state.result;break}
        if(state.status==="failed") throw new Error(state.error || "Scan failed");
      }
      if(!done) throw new Error("Scan timed out. Try a smaller page limit.");
      setAudit(done);
      const h=await fetch("/api/audits/history?url="+encodeURIComponent(done.url),{cache:"no-store"});
      const hist=await h.json(); if(Array.isArray(hist)) setHistory(hist);
    }catch(err){setError(err instanceof Error?err.message:"Scan failed")}
    finally{setLoading(false)}
  };

  const issues=useMemo(()=>audit ? audit.issues.filter(x=>filter==="all"||x.severity===filter):[],[audit,filter]);
  const dims=useMemo(()=>audit ? Object.entries(audit.dimensions).filter(([,v])=>typeof v==="number") as [string,number][]:[],[audit]);
  const browser=audit?.dimensions.browser || {};

  const askAI=async()=>{
    if(!audit)return;
    const r=await fetch("/api/audits/ai?audit_id="+audit.audit_id,{method:"POST"});
    setAi(await r.json());
  };
  const getTicket=async(issueIndex:number)=>{
    if(!audit)return;
    const r=await fetch("/api/audits/ticket?audit_id="+audit.audit_id+"&issue_index="+issueIndex+"&kind=github");
    const data=await r.json(); setTicket(data.markdown||"");
  };
  const createProject=async(e:FormEvent)=>{
    e.preventDefault(); if(!projectName.trim())return;
    const r=await fetch("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:projectName})});
    const data=await r.json(); setProjectMsg(r.ok?"Project #"+data.id+" created":(data.detail||"Could not create project")); if(r.ok)setProjectName("");
  };

  return <main className="app">
    <header><div><span className="eyebrow">WEBFORGE</span><h1>Website Audit Intelligence</h1><p>Measure a website, prove every finding, and turn evidence into engineering work.</p></div><div className="status">LIVE AUDIT ENGINE</div></header>
    <section className="scan"><form onSubmit={runAudit}><input value={url} onChange={e=>setUrl(e.target.value)} type="url" required placeholder="https://example.com"/><select value={limit} onChange={e=>setLimit(Number(e.target.value))}>{[5,10,20,30].map(n=><option key={n} value={n}>{n} pages</option>)}</select><button disabled={loading}>{loading?"Auditing…":"Run audit"}</button></form>{loading&&<div className="progress"><span className="pulse"/> Crawling pages • checking links • measuring performance • scoring evidence</div>}{error&&<p className="error">{error}</p>}</section>

    {audit && <>
      <div className="urlbar">{audit.url}<span>Audit #{audit.audit_id}</span></div>
      <nav className="tabs">{["overview","issues","pages","history","backlog"].map(t=><button key={t} className={tab===t?"active":""} onClick={()=>setTab(t)}>{t}</button>)}</nav>

      {tab==="overview" && <section className="grid">
        <div className="card score"><span>Overall health</span><strong>{audit.score}</strong><small>/100</small><div className="dims">{dims.map(([k,v])=><div key={k}><label>{label[k]||k}</label><b>{v}</b></div>)}</div></div>
        <div className="card"><h2>Audit facts</h2><div className="facts"><span>Pages scanned <b>{audit.pages_scanned}</b></span><span>Discovered <b>{audit.pages_discovered}</b></span><span>Broken links <b>{audit.broken_links.length}</b></span><span>Duration <b>{(audit.duration_ms/1000).toFixed(1)}s</b></span><span>robots.txt <b>{audit.robots_present?"PASS":"MISSING"}</b></span><span>sitemap.xml <b>{audit.sitemap_present?"PASS":"MISSING"}</b></span></div></div>
        <div className="card"><h2>Browser performance</h2><div className="facts"><span>FCP <b>{browser.fcpMs ?? "—"}ms</b></span><span>LCP <b>{browser.lcpMs ?? "—"}ms</b></span><span>CLS <b>{browser.cls ?? "—"}</b></span><span>Load <b>{browser.loadMs ?? "—"}ms</b></span><span>Resources <b>{browser.resourceCount ?? "—"}</b></span><span>TTFB <b>{audit.pages[0]?.ttfb_ms ?? "—"}ms</b></span></div></div>
        <div className="card"><div className="row"><h2>Priority backlog</h2><button className="ghost" onClick={askAI}>Explain with AI</button></div>{issues.slice(0,5).map((x,i)=><IssueCard key={i} issue={x} onTicket={()=>getTicket(audit.issues.indexOf(x))}/>)}</div>
        {audit.broken_links.length>0&&<div className="card"><h2>Broken links</h2>{audit.broken_links.slice(0,10).map((x:any,i:number)=><div className="linkrow" key={i}><span>{x.url}</span><b>{x.status||"ERR"}</b></div>)}</div>}
        {ai&&<div className="card ai"><h2>{ai.mode==="llm"?"AI engineering brief":"Precision backlog assistant"}</h2><p>{ai.summary}</p>{ai.items?.map((x:any,i:number)=><div className="aiitem" key={i}><b>{x.title}</b><span>P{x.priority}</span><p>{x.action||x.why}</p></div>)}{ai.raw&&<pre>{ai.raw}</pre>}</div>}
      </section>}

      {tab==="issues" && <section className="card"><div className="row"><h2>{audit.issues.length} findings</h2><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>{issues.map((x,i)=><IssueCard key={i} issue={x} onTicket={()=>getTicket(audit.issues.indexOf(x))}/>)}</section>}

      {tab==="pages" && <section className="card"><h2>Pages & measurements</h2><div className="table"><div className="tr head"><b>URL</b><b>Status</b><b>Resp</b><b>TTFB</b><b>HTML</b><b>H1</b><b>Alt</b></div>{audit.pages.map((p,i)=><div className="tr" key={i}><span>{p.url}</span><b>{p.status||"—"}</b><b>{p.response_ms}ms</b><b>{p.ttfb_ms}ms</b><b>{Math.round((p.html_bytes||0)/1024)}KB</b><b>{p.h1_count}</b><b>{p.images?.filter((x:any)=>!x.alt).length||0}</b></div>)}</div></section>}

      {tab==="history" && <section className="card"><div className="row"><h2>Scan history</h2><div className="actions"><a href={"/api/audits/export?audit_id="+audit.audit_id+"&format=json"}>JSON</a><a href={"/api/audits/export?audit_id="+audit.audit_id+"&format=csv"}>CSV</a></div></div>{history.map((h,i)=><div className="history" key={h.audit_id}><span>Audit #{h.audit_id}</span><b>{h.score}/100</b><small>{new Date(h.created_at).toLocaleString()}</small>{i>0&&<button className="ghost" onClick={async()=>{const r=await fetch("/api/audits/compare?left="+history[i].audit_id+"&right="+history[i-1].audit_id); alert(JSON.stringify(await r.json(),null,2))}}>Compare</button>}</div>)}</section>}

      {tab==="backlog" && <section className="card"><h2>Engineering backlog</h2>{audit.issues.slice().sort((a,b)=>b.priority-a.priority).map((x,i)=><div className="backlog" key={i}><span className={"pill "+x.severity}>{x.severity}</span><div><b>{x.title}</b><p>{x.recommendation}</p><small>Priority {x.priority}/100 • {x.effort} effort • {x.confidence}% confidence</small></div></div>)}</section>}
      {ticket&&<section className="card"><div className="row"><h2>Ticket template</h2><button className="ghost" onClick={()=>navigator.clipboard.writeText(ticket)}>Copy</button></div><pre>{ticket}</pre></section>}
    </>}

    <section className="card project-card"><div className="row"><h2>Projects & automation</h2><span className="section-note">Workspace organization</span></div><form onSubmit={createProject} className="project-form"><input value={projectName} onChange={e=>setProjectName(e.target.value)} placeholder="Project name"/><button>Create project</button></form>{audit&&<button className="ghost schedule-btn" onClick={async()=>{const r=await fetch("/api/schedules",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:audit.url,interval_minutes:1440})});const data=await r.json();setProjectMsg(r.ok?"Daily rescan scheduled":(data.detail||"Could not schedule rescan"))}}>Schedule daily rescan</button>}{projectMsg&&<small className="evidence">{projectMsg}</small>}</section>
</main>
}

function IssueCard({issue,onTicket}:{issue:Issue;onTicket:()=>void}){
  return <article className="issue"><div className="row"><div><span className="cat">{issue.category}</span><h3>{issue.title}</h3></div><span className={"pill "+issue.severity}>{issue.severity}</span></div><p>{issue.impact}</p>{issue.page_url&&<small className="evidence">Page: {issue.page_url}</small>}{issue.evidence&&<small className="evidence">Evidence: {issue.evidence}</small>}<p className="fix"><b>Fix:</b> {issue.recommendation}</p>{issue.code_after&&<pre>{issue.code_after}</pre>}<div className="issue-meta"><span>P{issue.priority}</span><span>{issue.effort} effort</span><span>{issue.confidence}% confidence</span><button className="ghost" onClick={onTicket}>Ticket</button></div></article>
}
