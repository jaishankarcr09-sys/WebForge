import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(backend + "/health", {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) {
      return NextResponse.json({ status: "degraded", backend: response.status }, { status: 503 });
    }
    const data = await response.json();
    return NextResponse.json({ status: "ok", frontend: "ok", backend: data }, { status: 200 });
  } catch {
    return NextResponse.json({ status: "degraded", backend: "unavailable" }, { status: 503 });
  }
}
