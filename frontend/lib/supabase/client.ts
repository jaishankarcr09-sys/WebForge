import { createBrowserClient } from "@supabase/ssr";

declare global {
  interface Window {
    __WEBFORGE_SUPABASE__?: {
      url?: string;
      publishableKey?: string;
    };
  }
}

export function createClient() {
  const runtimeConfig =
    typeof window !== "undefined" ? window.__WEBFORGE_SUPABASE__ : undefined;

  return createBrowserClient(
    runtimeConfig?.url || process.env.NEXT_PUBLIC_SUPABASE_URL!,
    runtimeConfig?.publishableKey || process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  );
}
