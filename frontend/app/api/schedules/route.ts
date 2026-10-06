import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET() {
  const r = await backendFetch("/api/v1/schedules");
  return NextResponse.json(await r.json(), { status: r.status });
}

export async function POST(req: Request) {
  const body = await req.json();
  const q = new URLSearchParams({
    url: String(body.url || ""),
    interval_minutes: String(body.interval_minutes || 1440),
  });
  const r = await backendFetch("/api/v1/schedules?" + q.toString(), { method: "POST" });
  return NextResponse.json(await r.json(), { status: r.status });
}
