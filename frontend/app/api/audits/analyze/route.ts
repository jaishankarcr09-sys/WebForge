import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;

export async function POST(request: Request) {
  if (!BACKEND_URL) {
    return NextResponse.json(
      { detail: "Backend URL is not configured." },
      { status: 500 },
    );
  }

  try {
    const body = await request.text();

    const response = await fetch(
      `${BACKEND_URL.replace(/\\/$/, "")}/api/v1/audits/analyze`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(120_000),
      },
    );

    const contentType = response.headers.get("content-type") ?? "";
    const responseBody = contentType.includes("application/json")
      ? await response.json()
      : { detail: await response.text() };

    return NextResponse.json(responseBody, {
      status: response.status,
    });
  } catch (error) {
    const detail =
      error instanceof Error ? error.message : "Backend request failed.";
    return NextResponse.json({ detail }, { status: 502 });
  }
}
