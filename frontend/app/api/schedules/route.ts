import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function POST(req:Request){
  const body=await req.json();
  const url=String(body.url||"");
  const interval=String(body.interval_minutes||1440);
  const r=await fetch(BASE+"/api/v1/schedules?url="+encodeURIComponent(url)+"&interval_minutes="+interval,{method:"POST",cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
export async function GET(){
  const r=await fetch(BASE+"/api/v1/schedules",{cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
