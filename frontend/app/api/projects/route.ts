import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function GET(){const r=await fetch(BASE+"/api/v1/projects",{cache:"no-store"});return NextResponse.json(await r.json(),{status:r.status})}
export async function POST(req:Request){
  const body=await req.json();
  const name=String(body.name||"").trim();
  if(!name)return NextResponse.json({detail:"Project name is required"},{status:400});
  const params=new URLSearchParams({name,description:String(body.description||"")});
  const r=await fetch(BASE+"/api/v1/projects?"+params.toString(),{method:"POST",cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
