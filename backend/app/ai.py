from __future__ import annotations
import os
import httpx

def build_context(audit:dict)->str:
    return "\n".join(
        f"- {x.get('severity')} | {x.get('title')} | page={x.get('page_url')} | evidence={x.get('evidence')} | priority={x.get('priority')}"
        for x in audit.get("issues",[])[:20]
    )

def generate_ai_backlog(audit:dict)->dict:
    key=os.getenv("AI_API_KEY","").strip()
    base=os.getenv("AI_BASE_URL","https://api.openai.com/v1").rstrip("/")
    model=os.getenv("AI_MODEL","").strip()
    top=sorted(audit.get("issues",[]),key=lambda x:-x.get("priority",50))[:8]
    fallback={"mode":"deterministic","summary":"No AI provider configured. This backlog is generated from measured audit evidence.","items":[{"title":x["title"],"why":x["impact"],"action":x["recommendation"],"priority":x["priority"]} for x in top]}
    if not key or not model:return fallback
    prompt="Convert these observed website findings into a concise engineering backlog. Never invent measurements. Return JSON with summary and items[].\n\n"+build_context(audit)
    try:
        r=httpx.post(f"{base}/chat/completions",headers={"Authorization":f"Bearer {key}"},json={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.1},timeout=45)
        r.raise_for_status()
        return {"mode":"llm","summary":"Generated only from observed audit evidence.","raw":r.json()["choices"][0]["message"]["content"]}
    except Exception as exc:return {**fallback,"mode":"fallback","error":str(exc)[:180]}

def ticket_markdown(audit:dict,issue:dict,kind:str)->str:
    label="GitHub Issue" if kind=="github" else "Jira Task"
    return f"# {label}: {issue['title']}\n\n**Severity:** {issue['severity']}\n**Page:** {issue.get('page_url') or audit['url']}\n**Priority:** P{max(1,4-min(3,issue.get('priority',50)//35))}\n\n## Why\n{issue['impact']}\n\n## Evidence\n{issue.get('evidence','Not captured')}\n\n## Recommended change\n{issue['recommendation']}\n\n## Done when\n- The observed issue is no longer reproducible.\n- The audit check passes on the next scan.\n"
