"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Issue={
  category:string; title:string; severity:string; impact:string; recommendation:string;
  page_url:string; evidence:string; confidence:number; effort:string; priority:number;
  code_before:string; code_after:string; layer:string;
};
type Page={
  url:string; status:number; response_ms:number; ttfb_ms:number; html_bytes:number;
  title:string; description:string; canonical:string; h1_count:number; images:any[];
  scripts:number; server:string; cache_control:string; content_encoding:string;
  redirect_count:number; insecure_cookie_count:number;
};
type Similar={
  name:string; url:string; snippet:string; website_type:string; source?:string;
  relevance_score?:number|null; match_reason?:string; match_type?:string; verification_status?:string;
  features?:{pages_scanned:number;avg_response_ms:number;missing_alt_images:number;json_ld_pages:number;social_ready_pages:number;security_header_coverage:number};
};
type Audit={
  audit_id:number; url:string; score:number; score_status?:string; verified_pages?:number; unverified_pages?:number; crawl_warnings?:any[]; dimensions:Record<string,any>;
  pages_discovered:number; pages_scanned:number; duration_ms:number;
  robots_present:boolean; sitemap_present:boolean; broken_links:any[]; link_check_warnings?:any[];
  pages:Page[]; issues:Issue[]; website_type:string; frontend_score:number;
  backend_score:number; reach_score:number; intelligence_summary:string;
  features:Record<string,any>; similar_sites:Similar[]; opportunities:any[];
};
type History={audit_id:number;url:string;score:number;status:string;created_at:string};
type Project={id:number;name:string;description:string};
type Schedule={id:number;website_id:number;interval_minutes:number;enabled:boolean;next_run_at:string};
type User={id:string;email:string;name:string;avatar:string};
type Props={user:User};

const nav=[
  {id:"overview",label:"Overview",icon:"grid"},
  {id:"audit",label:"New audit",icon:"scan"},
  {id:"issues",label:"Weaknesses",icon:"issue"},
  {id:"pages",label:"Pages",icon:"pages"},
  {id:"opportunities",label:"Opportunities",icon:"spark"},
  {id:"history",label:"History",icon:"history"},
  {id:"workspace",label:"Workspace",icon:"workspace"},
  {id:"learn",label:"How it works",icon:"book"},
];

export default function DashboardClient({user}:Props){
  const [view,setView]=useState("overview");
  const [url,setUrl]=useState("");
  const [scheme,setScheme]=useState<"https"|"http">("https");
  const [limit,setLimit]=useState(5);
  const [audit,setAudit]=useState<Audit|null>(null);
  const [history,setHistory]=useState<History[]>([]);
  const [filter,setFilter]=useState("all");
  const [layerFilter,setLayerFilter]=useState("all");
  const [loading,setLoading]=useState(false);
  const [progress,setProgress]=useState("Ready to scan.");
  const [error,setError]=useState("");
  const [ai,setAi]=useState<any>(null);
  const [ticket,setTicket]=useState("");
  const [projectName,setProjectName]=useState("");
  const [workspaceMsg,setWorkspaceMsg]=useState("");
  const [projects,setProjects]=useState<Project[]>([]);
  const [schedules,setSchedules]=useState<Schedule[]>([]);
  const [workspaceLoading,setWorkspaceLoading]=useState(true);

  const filteredIssues=useMemo(
    ()=>audit?.issues.filter(x=>(filter==="all"||x.severity===filter)&&(layerFilter==="all"||x.layer===layerFilter))??[],
    [audit,filter,layerFilter]
  );
  const topIssues=useMemo(()=>{
    if(!audit)return [];
    const grouped=new Map<string,Issue&{occurrences:number}>();
    for(const issue of audit.issues){
      const key=issue.title+"|"+issue.layer;
      const existing=grouped.get(key);
      if(existing){existing.occurrences+=1;if(issue.priority>existing.priority){existing.priority=issue.priority;existing.page_url=issue.page_url;existing.evidence=issue.evidence;}}
      else grouped.set(key,{...issue,occurrences:1});
    }
    return [...grouped.values()].sort((a,b)=>b.priority-a.priority).slice(0,5);
  },[audit]);

  useEffect(()=>{
    let active=true;
    (async()=>{
      try{
        const [h,p,s]=await Promise.all([
          fetch("/api/audits/history",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
          fetch("/api/projects",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
          fetch("/api/schedules",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
        ]);
        if(!active)return;
        setHistory(Array.isArray(h)?h:[]);
        setProjects(Array.isArray(p)?p:[]);
        setSchedules(Array.isArray(s)?s:[]);
      } finally {
        if(active)setWorkspaceLoading(false);
      }
    })();
    return ()=>{active=false};
  },[]);

  async function refreshWorkspace(){
    const [h,p,s]=await Promise.all([
      fetch("/api/audits/history",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
      fetch("/api/projects",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
      fetch("/api/schedules",{cache:"no-store"}).then(r=>r.ok?r.json():[]),
    ]);
    setHistory(Array.isArray(h)?h:[]);
    setProjects(Array.isArray(p)?p:[]);
    setSchedules(Array.isArray(s)?s:[]);
  }

  async function runAudit(e?:FormEvent){
    e?.preventDefault();
    if(!url.trim())return;
    const targetUrl=scheme+"://"+url.trim().replace(/^https?:\/\//i,"").replace(/\/$/,"");
    setLoading(true);setError("");setAi(null);setTicket("");setView("overview");
    try{
      setProgress("Validating target and checking crawler access…");
      const start=await fetch("/api/audits/scan",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:targetUrl,page_limit:limit})});
      const startData=await start.json();
      if(!start.ok)throw new Error(startData.detail||"Could not start audit.");
      for(let i=0;i<180;i++){
        await new Promise(r=>setTimeout(r,1000));
        const state=await fetch("/api/audits/jobs/"+startData.job_id,{cache:"no-store"}).then(r=>r.json());
        setProgress(state.status==="queued"?"Queued securely for your workspace…":state.status==="running"?"Crawling pages • measuring browser performance • checking backend delivery…":"Finishing the report…");
        if(state.status==="completed"){
          setAudit(state.result);
          setProgress("Audit complete.");
          await refreshWorkspace();
          break;
        }
        if(state.status==="failed")throw new Error(state.error||"Audit failed.");
        if(i===179)throw new Error("Audit timed out. Try 5–10 pages first.");
      }
    }catch(err){setError(err instanceof Error?err.message:"Audit failed.");}
    finally{setLoading(false);}
  }

  async function signOut(){
    const supabase=createClient();await supabase.auth.signOut();window.location.href="/login";
  }

  async function askAI(){if(!audit)return;const r=await fetch("/api/audits/ai?audit_id="+audit.audit_id,{method:"POST"});setAi(await r.json());}
  async function makeTicket(index:number){if(!audit)return;const r=await fetch("/api/audits/ticket?audit_id="+audit.audit_id+"&issue_index="+index+"&kind=github");const data=await r.json();setTicket(data.markdown||"");}
  async function createProject(e:FormEvent){
    e.preventDefault();if(!projectName.trim())return;
    const r=await fetch("/api/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:projectName})});
    const data=await r.json();setWorkspaceMsg(r.ok?"Project #"+data.id+" created.":data.detail||"Could not create project.");if(r.ok){setProjectName("");await refreshWorkspace();}
  }
  async function scheduleDaily(){
    if(!audit)return;
    const r=await fetch("/api/schedules",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:audit.url,interval_minutes:1440})});
    const data=await r.json();setWorkspaceMsg(r.ok?"Daily rescan enabled for this website.":data.detail||"Could not schedule rescan.");if(r.ok)await refreshWorkspace();
  }

  return <div className="shell">
    <aside className="sidebar">
      <a className="sidebar-brand" href="/"><span className="brand-mark">W</span><span><b>WebForge</b><small>Audit Intelligence</small></span></a>
      <div className="sidebar-section"><small>Audit workspace</small>{nav.slice(0,6).map(item=><button key={item.id} className={"nav-item "+(view===item.id?"active":"")} onClick={()=>setView(item.id)}><Icon name={item.icon}/><span>{item.label}</span>{item.id==="issues"&&audit?<em>{audit.issues.length}</em>:null}</button>)}</div>
      <div className="sidebar-section"><small>Workspace</small>{nav.slice(6).map(item=><button key={item.id} className={"nav-item "+(view===item.id?"active":"")} onClick={()=>setView(item.id)}><Icon name={item.icon}/><span>{item.label}</span></button>)}</div>
      <div className="sidebar-help"><span className="help-icon">?</span><div><b>What is WebForge?</b><p>Measure first. Fix second. Every recommendation is tied to evidence.</p></div></div>
      <div className="sidebar-user"><div className="avatar">{user.avatar?<img src={user.avatar} alt=""/>:user.name.slice(0,1).toUpperCase()}</div><div className="user-meta"><b>{user.name}</b><span>{user.email}</span></div><button className="icon-btn" onClick={signOut} title="Sign out">↗</button></div>
    </aside>

    <main className="content">
      <header className="topbar"><div><span className="crumb">WebForge / {nav.find(x=>x.id===view)?.label}</span><h1>{view==="overview"?"Website health at a glance":view==="audit"?"Start a new audit":view==="issues"?"What needs fixing":view==="pages"?"Page-by-page evidence":view==="opportunities"?"Reach & competitive opportunities":view==="history"?"Progress over time":view==="workspace"?"Projects & automation":"How WebForge works"}</h1></div><div className="top-actions">{audit&&<button className="secondary">Current audit <span>#{audit.audit_id}</span></button>}<button className="avatar-top" onClick={signOut}>{user.avatar?<img src={user.avatar} alt=""/>:user.name.slice(0,1).toUpperCase()}</button></div></header>

      {(view==="overview"||view==="audit")&&<section className="hero-card">
        <div className="hero-copy"><span className="eyebrow">FULL-STACK WEBSITE AUDIT</span><h2>Understand the website before you change it.</h2><p>Enter a public URL and WebForge crawls the experience, measures browser performance, inspects delivery and security signals, classifies the product, and turns findings into a prioritized engineering plan.</p></div>
        <form className="audit-form" onSubmit={runAudit}><div className="url-input"><select aria-label="URL protocol" className="url-scheme" value={scheme} onChange={e=>setScheme(e.target.value as "https"|"http")}><option value="https">https://</option><option value="http">http://</option></select><input value={url} onChange={e=>setUrl(e.target.value.replace(/^https?:\/\//i,""))} placeholder="yourwebsite.com" required/></div><select value={limit} onChange={e=>setLimit(Number(e.target.value))}>{[5,10,20,30].map(n=><option key={n} value={n}>{n} pages</option>)}</select><button className="primary" disabled={loading}>{loading?"Auditing…":"Analyze website"}</button></form>
        {loading&&<div className="progress-line"><span></span>{progress}</div>}{error&&<div className="inline-error">{error}</div>}
      </section>}

      {!audit&&view==="overview"&&<section className="onboarding">
        <div className="section-title"><div><span className="eyebrow">START HERE</span><h2>From URL to an actionable plan</h2></div></div>
        <div className="step-grid">{[["01","Discover","Crawl key pages, links, metadata, assets and delivery signals."],["02","Measure","Check SEO, UX, accessibility, browser performance and backend behavior."],["03","Prioritize","Separate frontend vs backend weaknesses with confidence, impact and effort."],["04","Improve","Generate fixes, growth opportunities, similar-site patterns and an engineering backlog."]].map(x=><div className="step" key={x[0]}><span>{x[0]}</span><h3>{x[1]}</h3><p>{x[2]}</p></div>)}</div>
        <div className="concept-grid"><Concept title="Projects" text="Projects group related websites and audits into one workspace. They matter when you manage more than one product, client, or environment."/><Concept title="Automation" text="Automation schedules recurring rescans so you can catch regressions after releases instead of manually checking the site again."/><Concept title="Frontend + Backend" text="A polished UI can still be slowed by server delivery, caching, security headers, redirects, or APIs. WebForge reports both layers together."/><Concept title="Evidence first" text="Every important finding shows what was observed, where it happened, and what change would improve it. AI never replaces measurement." /></div>
      </section>}

      <div className="view-body">
        {view==="overview"&&<OverviewState audit={audit} topIssues={topIssues} onView={setView} onAI={askAI}/>}
        {view==="audit"&&<AuditState audit={audit} topIssues={topIssues} onView={setView} onAI={askAI}/>}
        {view==="issues"&&(audit?<Issues audit={audit} filter={filter} setFilter={setFilter} layerFilter={layerFilter} setLayerFilter={setLayerFilter} issues={filteredIssues} onTicket={makeTicket}/>:<EmptyPage title="Run an audit first" text="Your findings will appear here after WebForge measures a website." action={()=>setView("audit")} actionLabel="Start audit"/>)}
        {view==="pages"&&(audit?<Pages audit={audit}/>:<EmptyPage title="No page measurements yet" text="Run your first website audit to populate the page evidence table." action={()=>setView("audit")} actionLabel="Measure a website"/>)}
        {view==="opportunities"&&(audit?<Opportunities audit={audit}/>:<EmptyPage title="No opportunities yet" text="WebForge will classify the website, compare patterns and build reach opportunities after your first audit." action={()=>setView("audit")} actionLabel="Find opportunities"/>)}
        {view==="history"&&<HistoryView history={history} setAudit={setAudit} loading={workspaceLoading}/>}
        {view==="workspace"&&<Workspace projectName={projectName} setProjectName={setProjectName} createProject={createProject} scheduleDaily={scheduleDaily} msg={workspaceMsg} setMsg={setWorkspaceMsg} projects={projects} schedules={schedules} audit={audit} loading={workspaceLoading}/>}
        {view==="learn"&&<Learn/>}
      </div>

      {audit&&ai&&<section className="panel ai-panel"><div className="section-title"><div><span className="eyebrow">OPTIONAL AI LAYER</span><h2>Engineering brief</h2></div><button className="secondary" onClick={()=>setAi(null)}>Close</button></div><p className="ai-summary">{ai.summary}</p>{ai.items?.map((x:any,i:number)=><div className="ai-row" key={i}><b>{x.title}</b><span>P{x.priority}</span><p>{x.action||x.why}</p></div>)}{ai.raw&&<pre>{ai.raw}</pre>}</section>}
      {ticket&&<section className="panel ticket-panel"><div className="section-title"><div><span className="eyebrow">ENGINEERING HANDOFF</span><h2>Ticket template</h2></div><button className="secondary" onClick={()=>navigator.clipboard.writeText(ticket)}>Copy</button></div><pre>{ticket}</pre></section>}
    </main>
  </div>
}

function OverviewState({audit,topIssues,onView,onAI}:{audit:Audit|null;topIssues:Issue[];onView:(v:string)=>void;onAI:()=>void}){
  if(!audit) return <section className="panel empty-dashboard"><span className="eyebrow">YOUR WORKSPACE</span><h2>Start with a website.</h2><p>Run a full-stack audit and this workspace will fill with health scores, evidence, weaknesses, page measurements, reach opportunities and an engineering backlog.</p><button className="primary" onClick={()=>onView("audit")}>Start your first audit</button></section>;
  return <Overview audit={audit} topIssues={topIssues} onView={onView} onAI={onAI}/>;
}

function AuditState({audit,topIssues,onView,onAI}:{audit:Audit|null;topIssues:Issue[];onView:(v:string)=>void;onAI:()=>void}){
  return <>{!audit&&<section className="panel empty-dashboard"><span className="eyebrow">NEW AUDIT</span><h2>Measure before you change.</h2><p>Use the audit controls above to create the first baseline. Once complete, the report remains available across this workspace.</p></section>}{audit&&<Overview audit={audit} topIssues={topIssues} onView={onView} onAI={onAI}/>}</>;
}

function Overview({audit,topIssues,onView,onAI}:{audit:Audit;topIssues:Issue[];onView:(v:string)=>void;onAI:()=>void}){
  const browser=audit.dimensions.browser||{};
  const scoreClass=audit.score>=85?"good":audit.score>=65?"fair":"risk";
  const verifiedCount=audit.verified_pages??audit.pages.filter(p=>p.status>=200&&p.status<400).length;
  const scoreUnverified=verifiedCount===0;
  const linkWarnings=audit.link_check_warnings??[];
  return <div>
    {(scoreUnverified||(audit.unverified_pages??0)>0)&&<section className="panel crawl-warning"><span className="eyebrow">CRAWL RELIABILITY</span><h2>{scoreUnverified?"Health score unavailable":"Partial crawl coverage"}</h2><p>{scoreUnverified?"WebForge could not verify any page content, so it cannot produce a trustworthy health score. Findings from blocked, challenge, non-HTML, or incomplete responses were skipped.":"Verified HTML pages: "+(audit.verified_pages??0)+" • Unverified pages: "+(audit.unverified_pages??0)+". Findings are based only on pages that passed crawl validation."}</p>{(audit.crawl_warnings??[]).slice(0,4).map((w:any,i:number)=><small key={i}>{w.url}: {w.reason}</small>)}</section>}{linkWarnings.length>0&&<section className="panel crawl-warning"><span className="eyebrow">LINK CHECK LIMITATIONS</span><h2>{linkWarnings.length} destination(s) could not be verified</h2><p>These responses may reflect access restrictions, rate limits, or network failures. WebForge does not count them as confirmed broken links.</p>{linkWarnings.slice(0,4).map((w:any,i:number)=><small key={i}>{w.url}: {w.reason}</small>)}</section>}
    <div className="summary-grid">
      <section className={"panel score-panel "+scoreClass}><div className={"score-ring "+(scoreUnverified?"unverified":"")} style={{"--score":scoreUnverified?0:audit.score} as React.CSSProperties}><div><strong>{scoreUnverified?"—":audit.score}</strong><small>{scoreUnverified?"unverified":"/100"}</small></div></div><div><span className="eyebrow">OVERALL HEALTH</span><h2>{audit.website_type}</h2><p>{audit.intelligence_summary}</p><div className="score-note">{scoreUnverified?"Insufficient verified data":audit.score>=85?"Healthy baseline":audit.score>=65?"Needs focused improvement":"High-priority improvement required"}</div></div></section>
      <section className="panel"><div className="section-title"><div><span className="eyebrow">FULL-STACK VIEW</span><h2>Where the weakness lives</h2></div></div><div className="layer-cards"><Metric title="Frontend" value={scoreUnverified?null:audit.frontend_score} text="SEO, UX, accessibility and browser experience"/><Metric title="Backend" value={scoreUnverified?null:audit.backend_score} text="Delivery, security, caching and server behavior"/><Metric title="Reach" value={scoreUnverified?null:audit.reach_score} text="Search readiness, shareability and discoverability"/></div></section>
    </div>
    <div className="grid-2">
      <section className="panel"><div className="section-title"><div><span className="eyebrow">WHY USERS MAY STRUGGLE</span><h2>Top weaknesses</h2></div><button className="link-btn" onClick={()=>onView("issues")}>View all</button></div>{topIssues.map((x,i)=><div className="compact-issue" key={i}><span className={"severity-dot "+x.severity}></span><div><b>{x.title}</b><small>{x.layer} • P{x.priority} • {x.confidence}% confidence{(x as Issue&{occurrences?:number}).occurrences&&((x as Issue&{occurrences?:number}).occurrences!>1)?` • ${(x as Issue&{occurrences:number}).occurrences} occurrences`:""}</small></div><span className="issue-arrow">→</span></div>)}{audit.issues.length===0&&<Empty text="No actionable weaknesses were detected in the current rule set."/>}</section>
      <section className="panel"><div className="section-title"><div><span className="eyebrow">BROWSER REALITY</span><h2>Performance snapshot</h2></div></div><div className="metric-table"><MetricLine k="FCP" v={browser.fcpMs==null?"—":browser.fcpMs+" ms"}/><MetricLine k="LCP" v={browser.lcpMs==null?"—":browser.lcpMs+" ms"}/><MetricLine k="CLS" v={browser.cls??"—"}/><MetricLine k="Page load" v={browser.loadMs==null?"—":browser.loadMs+" ms"}/><MetricLine k="TTFB" v={audit.pages[0]?.ttfb_ms==null?"—":audit.pages[0].ttfb_ms+" ms"}/><MetricLine k="Resources" v={browser.resourceCount??"—"}/></div><button className="secondary full" onClick={()=>onView("pages")}>Open page measurements</button></section>
    </div>
    <section className="panel reach-panel"><div><span className="eyebrow">MAX-REACH PLAYBOOK</span><h2>What should improve next</h2><p>Opportunity-level recommendations connect reach, trust and product clarity to concrete work.</p></div><div className="opportunity-list">{audit.opportunities.slice(0,4).map((x:any,i:number)=><div key={i}><span>{String(i+1).padStart(2,"0")}</span><b>{x.title}</b><p>{x.action}</p></div>)}</div><button className="secondary" onClick={()=>onAI()}>Get AI engineering brief</button></section>
  </div>
}

function Issues({audit,filter,setFilter,layerFilter,setLayerFilter,issues,onTicket}:{audit:Audit;filter:string;setFilter:(x:string)=>void;layerFilter:string;setLayerFilter:(x:string)=>void;issues:Issue[];onTicket:(i:number)=>void}){
  return <section className="panel issue-panel"><div className="section-title"><div><span className="eyebrow">EVIDENCE-BASED FINDINGS</span><h2>{audit.issues.length} weaknesses found</h2><p>Frontend and backend findings are separated so the team knows who should act.</p></div><div className="filters"><select value={layerFilter} onChange={e=>setLayerFilter(e.target.value)}><option value="all">All layers</option><option value="frontend">Frontend</option><option value="backend">Backend</option><option value="full-stack">Full stack</option></select><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All severity</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div></div>{issues.map((x,i)=><IssueDetail key={i} issue={x} onTicket={()=>onTicket(audit.issues.indexOf(x))}/>)}</section>
}

function IssueDetail({issue,onTicket}:{issue:Issue;onTicket:()=>void}){
  return <article className="issue-detail"><div className="issue-head"><div><div className="issue-tags"><span>{issue.category}</span><span>{issue.layer}</span><span>P{issue.priority}</span></div><h3>{issue.title}</h3></div><span className={"pill "+issue.severity}>{issue.severity}</span></div><div className="issue-body"><div><p><b>Why it matters</b>{issue.impact}</p>{issue.page_url&&<p><b>Where</b>{issue.page_url}</p>}<p><b>Evidence</b><span className="evidence-box">{issue.evidence||"Measured condition detected by the audit engine."}</span></p></div><div><p><b>Recommended fix</b>{issue.recommendation}</p>{issue.code_after&&<pre>{issue.code_after}</pre>}<button className="secondary" onClick={onTicket}>Create ticket template</button></div></div><div className="issue-footer"><span>{issue.confidence}% confidence</span><span>{issue.effort} effort</span><span>Priority {issue.priority}/100</span></div></article>
}

function Pages({audit}:{audit:Audit}){
  return <section className="panel"><div className="section-title"><div><span className="eyebrow">PAGE-BY-PAGE</span><h2>{audit.pages_scanned} pages measured</h2><p>Each row is evidence, not a guess.</p></div><div className="page-count">{audit.pages_discovered} discovered</div></div><div className="data-table"><div className="data-row header"><span>Page</span><span>Status</span><span>Response</span><span>TTFB</span><span>HTML</span><span>H1</span><span>Images</span></div>{audit.pages.map((p,i)=><div className="data-row" key={i}><span title={p.url}>{p.url}</span><b>{p.status||"ERR"}</b><span>{p.response_ms}ms</span><span>{p.ttfb_ms}ms</span><span>{Math.round((p.html_bytes||0)/1024)} KB</span><span>{p.h1_count}</span><span>{p.images?.length||0}</span></div>)}</div></section>
}

function Opportunities({audit}:{audit:Audit}){
  return <div className="grid-2">
    <section className="panel"><span className="eyebrow">WEBSITE POSITION</span><h2>{audit.website_type}</h2><p>{audit.intelligence_summary}</p><div className="feature-list">{Object.entries(audit.features).map(([k,v])=><MetricLine key={k} k={k.replaceAll("_"," ")} v={String(v)}/>)}</div></section>
    <section className="panel"><span className="eyebrow">GROWTH OPPORTUNITIES</span><h2>How to improve reach</h2>{audit.opportunities.map((x:any,i:number)=><div className="growth-card" key={i}><span>{String(i+1).padStart(2,"0")}</span><div><b>{x.title}</b><p>{x.reason}</p><small>{x.action}</small></div></div>)}</section>
    <section className="panel wide similar-discovery-panel">
      <div className="section-title">
        <div><span className="eyebrow">COMPETITIVE DISCOVERY</span><h2>Similar websites & patterns</h2><p>Use these references to study market patterns—not as proof that two products are identical.</p></div>
      </div>
      <div className="similar-discovery-note flex items-start gap-3 rounded-2xl border border-sky-500/20 bg-sky-500/[0.06] p-4 sm:p-5">
        <span className="similar-note-icon" aria-hidden="true">✦</span>
        <div><b className="text-sm font-semibold tracking-tight">Evidence before percentages</b><p className="mt-1 text-sm leading-6">WebForge no longer displays a similarity percentage unless it has a defensible, validated scoring model. Each card tells you whether it is a curated category reference or a candidate found through search, and whether a live crawl succeeded.</p></div>
      </div>
      <div className="similar-results-meta"><span>{audit.similar_sites?.length||0} references</span><span>Live metrics shown only after a successful crawl</span></div>
      <div className="similar-grid">{audit.similar_sites?.length?audit.similar_sites.map((s,i)=><article className="similar-card group rounded-2xl border border-slate-700/70 bg-slate-900/40 p-5 transition duration-200 hover:-translate-y-0.5 hover:border-sky-400/50 hover:bg-slate-900/70 hover:shadow-xl hover:shadow-sky-950/20" key={s.url||i}>
        <div className="similar-top">
          <span className="similar-index">{String(i+1).padStart(2,"0")}</span>
          <div className="min-w-0 flex-1"><b className="block truncate text-base font-semibold tracking-tight">{s.name}</b><small className="mt-1 block text-xs leading-5">{s.website_type}</small></div>
        </div>
        <div className="similar-badges">
          <span className={s.match_type==="Adjacent alternative"?"similar-badge badge-adjacent":"similar-badge"}>{s.match_type||"Search-discovered candidate"}</span>
          <span className={s.verification_status==="crawl-verified"?"similar-badge badge-verified":"similar-badge badge-unverified"}>{s.verification_status==="crawl-verified"?"Live crawl verified":s.verification_status==="curated-reference"?"Curated reference":s.verification_status?.startsWith("crawler-http-")?"Crawler blocked":s.verification_status==="crawler-unavailable"?"Crawl unavailable":"Search result only"}</span>
        </div>
        <p className="similar-snippet">{s.snippet||"A public website surfaced during category-level discovery."}</p>
        <div className="similar-reason"><span className="similar-reason-label">Why it appears</span><p>{s.match_reason||"Discovered through a public web search. Product-level similarity has not been independently confirmed."}</p></div>
        <div className="similar-source"><span>Discovery source</span><b>{s.source||"Web search"}</b></div>
        {s.features && s.features.pages_scanned > 0?<div className="similar-metrics"><span><b>{s.features.social_ready_pages??0}</b> social-ready</span><span><b>{s.features.json_ld_pages??0}</b> JSON-LD</span><span><b>{s.features.missing_alt_images??0}</b> alt gaps</span><span><b>{s.features.avg_response_ms??0}ms</b> avg response</span></div>:<p className="similar-no-metrics">Live metrics unavailable — no successful candidate crawl, so WebForge will not invent measurements.</p>}
        <a className="similar-link inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition hover:bg-sky-400/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400" href={s.url} target="_blank" rel="noreferrer">Visit website <span aria-hidden="true">↗</span></a>
      </article>):<Empty text="No candidate websites were discovered for this target. The rest of the audit is still available."/>}</div>
    </section>
  </div>
}

function HistoryView({history,setAudit,loading}:{history:History[];setAudit:(x:Audit)=>void;loading:boolean}){
  async function load(id:number){
    const r=await fetch("/api/audits/"+id,{cache:"no-store"});
    const data=await r.json();
    if(data.audit_id)setAudit(data);
  }
  return <section className="panel">
    <div className="section-title"><div><span className="eyebrow">REGRESSION CONTROL</span><h2>Scan history</h2><p>Every authenticated audit stays in this workspace.</p></div></div>
    {loading?<Empty text="Loading your workspace history…"/>:history.length?history.map(h=><div className="history-row" key={h.audit_id}>
      <div><b>Audit #{h.audit_id}</b><small>{h.url} • {new Date(h.created_at).toLocaleString()}</small></div>
      <strong>{h.score}</strong><span className="history-status">{h.status}</span>
      <button className="secondary" onClick={()=>load(h.audit_id)}>Open</button>
    </div>):<Empty text="No audits yet. Start your first audit and it will appear here automatically."/>}
  </section>
}

function Workspace({projectName,setProjectName,createProject,scheduleDaily,msg,setMsg,projects,schedules,audit,loading}:{projectName:string;setProjectName:(x:string)=>void;createProject:(e:FormEvent)=>void;scheduleDaily:()=>void;msg:string;setMsg:(m:string)=>void;projects:Project[];schedules:Schedule[];audit:Audit|null;loading:boolean}){
  return <div className="grid-2">
    <section className="panel">
      <span className="eyebrow">PROJECTS</span><h2>Group work intentionally</h2>
      <p>Projects organize products, clients or environments without leaving the WebForge workspace.</p>
      <form className="project-form" onSubmit={createProject}><input value={projectName} onChange={e=>setProjectName(e.target.value)} placeholder="e.g. Marketing website"/><button className="primary">Create project</button></form>
      <div className="workspace-list">{loading?<Empty text="Loading projects…"/>:projects.length?projects.map(p=><div className="workspace-row" key={p.id}><div><b>{p.name}</b><small>{p.description||"WebForge workspace"}</small></div><span>#{p.id}</span></div>):<Empty text="No projects yet. Projects are optional until you manage multiple products."/>}</div>
    </section>
    <section className="panel">
      <span className="eyebrow">AUTOMATION</span><h2>Catch regressions automatically</h2>
      <p>Schedules live in the same authenticated workspace and run against websites you already audited.</p>
      {audit?<button className="secondary" onClick={scheduleDaily}>Enable daily rescan for current site</button>:<button className="secondary" onClick={()=>setMsg("Run an audit first so WebForge knows which website to rescan.")}>Choose a website from an audit</button>}
      <div className="workspace-list">{loading?<Empty text="Loading automation…"/>:schedules.length?schedules.map(s=><div className="workspace-row" key={s.id}><div><b>{s.interval_minutes===1440?"Daily rescan":"Recurring rescan"}</b><small>Next run {new Date(s.next_run_at).toLocaleString()}</small></div><span>{s.enabled?"Active":"Paused"}</span></div>):<Empty text="No automated rescans yet."/>}</div>
    </section>
    {msg&&<div className="panel wide success-panel"><b>{msg}</b></div>}
  </div>
}

function Learn(){
  return <div className="learn-grid"><section className="panel wide"><span className="eyebrow">THE PROCESS</span><h2>What the user should do</h2><div className="process-grid">{[["01","Sign in","Your private workspace is tied to your Supabase account."],["02","Enter a URL","Choose 5–30 pages. Start with 5–10 for a fast baseline."],["03","Read the full-stack report","Review website type, frontend health, backend health, reach score, and evidence."],["04","Fix the P1 work","Use priority, impact, effort and confidence to decide what enters the next sprint."],["05","Explore similar sites","Study comparable patterns and then build a differentiated version rather than copying."],["06","Rescan","Compare history after changes and schedule recurring scans for regression control."]].map(x=><div className="process-step" key={x[0]}><span>{x[0]}</span><div><b>{x[1]}</b><p>{x[2]}</p></div></div>)}</div></section><Concept title="Projects" text="Projects are optional organization for multiple websites, clients, or environments."/><Concept title="Automation" text="Automation is optional recurrence. It watches a known website and helps identify regressions after releases."/><Concept title="AI" text="AI is an interpretation layer. The scanner remains deterministic; AI explains measured findings and drafts work."/><Concept title="Similar websites" text="Comparables answer what the market baseline looks like, which features are common, and where a differentiated opportunity exists."/></div>
}

function EmptyPage({title,text,action,actionLabel}:{title:string;text:string;action:()=>void;actionLabel:string}){
  return <section className="panel empty-dashboard"><span className="eyebrow">WEBFORGE WORKSPACE</span><h2>{title}</h2><p>{text}</p><button className="primary" onClick={action}>{actionLabel}</button></section>
}

function Concept({title,text}:{title:string;text:string}){return <div className="concept panel"><span className="eyebrow">{title.toUpperCase()}</span><h3>{title}</h3><p>{text}</p></div>}
function Metric({title,value,text}:{title:string;value:number|null;text:string}){return <div className="layer-card"><div className="layer-top"><span>{title}</span><b>{value===null?"—":value}</b></div>{value!==null&&<div className="meter"><span style={{width:value+"%"}}></span></div>}<p>{value===null?"Insufficient verified page evidence":text}</p></div>}
function MetricLine({k,v}:{k:string;v:string|number}){return <div className="metric-line"><span>{k}</span><b>{v}</b></div>}
function Empty({text}:{text:string}){return <div className="empty-state">{text}</div>}
function Icon({name}:{name:string}){const d:Record<string,string>={grid:"M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",scan:"M4 7V4h3M17 4h3v3M20 17v3h-3M7 20H4v-3",issue:"M12 4l8 16H4L12 4zM12 9v5m0 3h.01",pages:"M6 4h12v16H6zM9 8h6M9 12h6M9 16h4",spark:"M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z",history:"M4 12a8 8 0 108-8M4 4v5h5",workspace:"M4 7h16v13H4zM8 4h8v3H8z",book:"M5 4h12v16H5zM8 8h6M8 12h6M8 16h4"};return <span className="nav-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d={d[name]}/></svg></span>}
