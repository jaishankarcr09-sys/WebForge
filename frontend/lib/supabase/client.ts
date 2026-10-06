import { createBrowserClient } from "@supabase/ssr";

const SUPABASE_URL = "https://abgbryuiemydynvdwrbp.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_Y1vmU0ZtyaYWnk3quqGQhQ_drih6Ti3";

export function createClient() {
  // These are Supabase's public browser credentials. Keeping the fallback
  // here makes the client independent of Next.js build-time env injection.
  const url =
    typeof window !== "undefined"
      ? window.__WEBFORGE_SUPABASE__?.url || SUPABASE_URL
      : SUPABASE_URL;

  const key =
    typeof window !== "undefined"
      ? window.__WEBFORGE_SUPABASE__?.publishableKey || SUPABASE_PUBLISHABLE_KEY
      : SUPABASE_PUBLISHABLE_KEY;

  return createBrowserClient(url, key);
}

declare global {
  interface Window {
    __WEBFORGE_SUPABASE__?: {
      url?: string;
      publishableKey?: string;
    };
  }
}
