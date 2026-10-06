import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function POST(req:Request){
  const body=await req.text();
  const r=await fetch(BASE+"/api/v1/audits/scan",{method:"POST",headers:{"Content-Type":"application/json"},body,cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
