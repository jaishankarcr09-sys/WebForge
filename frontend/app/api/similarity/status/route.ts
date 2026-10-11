import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/backend";

export async function GET() {
  const response = await backendFetch("/api/v1/similarity/status", { method: "GET" });
  return NextResponse.json(await response.json(), { status: response.status });
}
