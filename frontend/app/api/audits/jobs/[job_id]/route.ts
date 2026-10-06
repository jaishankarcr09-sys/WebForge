import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET(_: Request, ctx: { params: Promise<{ job_id: string }> }) {
  const { job_id } = await ctx.params;
  const r = await backendFetch("/api/v1/jobs/" + job_id);
  return NextResponse.json(await r.json(), { status: r.status });
}
