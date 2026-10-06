import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET(req: Request) {
  const q = new URL(req.url).search;
  const r = await backendFetch("/api/v1/audits/compare" + q);
  return NextResponse.json(await r.json(), { status: r.status });
}
