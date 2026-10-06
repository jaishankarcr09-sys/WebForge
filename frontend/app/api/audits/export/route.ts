import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET(req: Request) {
  const q = new URL(req.url).searchParams;
  const id = q.get("audit_id");
  const fmt = q.get("format") || "json";
  if (!id) return NextResponse.json({ detail: "audit_id is required" }, { status: 400 });
  const endpoint = fmt === "pdf" ? "/api/v1/audits/" + id + "/export.pdf" : (fmt === "csv" ? "/api/v1/audits/" + id + "/export.csv" : "/api/v1/audits/" + id + "/export.json");
  const r = await backendFetch(endpoint);
  const body = await r.text();
  return new NextResponse(body, {
    status: r.status,
    headers: {
      "Content-Type": fmt === "pdf" ? "application/pdf" : (fmt === "csv" ? "text/csv" : "application/json"),
      "Content-Disposition": fmt === "pdf" ? "attachment; filename=audit-" + id + ".pdf" : (fmt === "csv" ? "attachment; filename=audit-" + id + ".csv" : "attachment; filename=audit-" + id + ".json"),
    },
  });
}
