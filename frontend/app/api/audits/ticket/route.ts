import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams;
  const auditId = q.get("audit_id");
  if (!auditId) return NextResponse.json({ detail: "audit_id is required" }, { status: 400 });
  const path = "/api/v1/audits/" + auditId + "/ticket?issue_index=" + encodeURIComponent(q.get("issue_index") || "0") + "&kind=" + encodeURIComponent(q.get("kind") || "github");
  const r = await backendFetch(path);
  return NextResponse.json(await r.json(), { status: r.status });
}
