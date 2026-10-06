import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function POST(req:Request){
  const q=new URL(req.url).search;
  const r=await fetch(BASE+"/api/v1/audits/"+new URLSearchParams(q).get("audit_id")+"/ai",{method:"POST",cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
