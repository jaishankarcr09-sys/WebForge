import {NextResponse} from "next/server";
const BASE=process.env.BACKEND_URL||process.env.NEXT_PUBLIC_API_URL;
export async function GET(_:Request,ctx:{params:Promise<{job_id:string}>}){
  const {job_id}=await ctx.params;
  const r=await fetch(BASE+"/api/v1/jobs/"+job_id,{cache:"no-store"});
  return NextResponse.json(await r.json(),{status:r.status});
}
