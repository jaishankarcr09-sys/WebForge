import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function POST(req: Request) {
  const auditId = new URL(req.url).searchParams.get("audit_id");
  if (!auditId) return NextResponse.json({ detail: "audit_id is required" }, { status: 400 });
  const r = await backendFetch("/api/v1/audits/" + auditId + "/ai", { method: "POST" });
  return NextResponse.json(await r.json(), { status: r.status });
}
