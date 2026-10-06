import { createClient } from "@/lib/supabase/server";

const BASE = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

export async function backendFetch(path:string, init:RequestInit = {}) {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  const userId = data?.claims?.sub;
  if (!userId) {
    return new Response(JSON.stringify({ detail: "Please sign in to continue." }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }
  const headers = new Headers(init.headers);
  headers.set("x-webforge-user-id", String(userId));
  return fetch(BASE + path, { ...init, headers, cache: init.cache || "no-store" });
}
