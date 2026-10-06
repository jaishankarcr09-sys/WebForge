import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET() {
  const r = await backendFetch("/api/v1/projects");
  return NextResponse.json(await r.json(), { status: r.status });
}

export async function POST(req: Request) {
  const body = await req.json();
  const name = String(body.name || "").trim();
  if (!name) return NextResponse.json({ detail: "Project name is required" }, { status: 400 });
  const q = new URLSearchParams({ name, description: String(body.description || "") });
  const r = await backendFetch("/api/v1/projects?" + q.toString(), { method: "POST" });
  return NextResponse.json(await r.json(), { status: r.status });
}
