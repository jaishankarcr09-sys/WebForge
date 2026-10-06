import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function GET(req:Request){
  const q=new URL(req.url).searchParams;
  const auditId=q.get("audit_id");
  if(!auditId)return NextResponse.json({detail:"audit_id is required"},{status:400});
  const r=await fetch(BASE+"/api/v1/audits/"+auditId+"/ticket?issue_index="+encodeURIComponent(q.get("issue_index")||"0")+"&kind="+encodeURIComponent(q.get("kind")||"github"),{cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
