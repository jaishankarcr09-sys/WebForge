import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const requestedNext = url.searchParams.get("next") || "/";
  const next = requestedNext.startsWith("/") && !requestedNext.startsWith("//") ? requestedNext : "/";
  const error = url.searchParams.get("error");
  const errorDescription = url.searchParams.get("error_description");

  // OAuth providers can return an error instead of a code. Never swallow it
  // and silently send the user back to a login screen.
  if (error) {
    const login = new URL("/login", url.origin);
    login.searchParams.set(
      "error",
      errorDescription || error || "Authentication failed.",
    );
    return NextResponse.redirect(login);
  }

  if (code) {
    const supabase = await createClient();
    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code);

    if (exchangeError) {
      const login = new URL("/login", url.origin);
      login.searchParams.set("error", exchangeError.message);
      return NextResponse.redirect(login);
    }
  }

  return NextResponse.redirect(new URL(next, url.origin));
}
