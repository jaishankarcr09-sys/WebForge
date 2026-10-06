import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function POST(request: Request) {
  const body = await request.text();
  const r = await backendFetch("/api/v1/audits/scan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  return NextResponse.json(await r.json(), { status: r.status });
}
