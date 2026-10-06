import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function GET(req:Request){
  const q=new URL(req.url).search;
  const r=await fetch(BASE+"/api/v1/websites/history"+q,{cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
