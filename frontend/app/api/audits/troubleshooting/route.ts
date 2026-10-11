import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

function getAuditId(req: Request) {
  const auditId = new URL(req.url).searchParams.get("audit_id");
  if (!auditId || !/^\d+$/.test(auditId)) return null;
  return auditId;
}

export async function GET(req: Request) {
  const auditId = getAuditId(req);
  if (!auditId) return NextResponse.json({ detail: "A valid audit_id is required." }, { status: 400 });
  const response = await backendFetch("/api/v1/audits/" + auditId + "/troubleshooting");
  return NextResponse.json(await response.json(), { status: response.status });
}

export async function POST(req: Request) {
  const auditId = getAuditId(req);
  if (!auditId) return NextResponse.json({ detail: "A valid audit_id is required." }, { status: 400 });
  const response = await backendFetch("/api/v1/audits/" + auditId + "/troubleshooting/assistant", { method: "POST" });
  return NextResponse.json(await response.json(), { status: response.status });
}
