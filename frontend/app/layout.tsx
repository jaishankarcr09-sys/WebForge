import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "WebForge — Website Audit Intelligence",
  description: "Full-stack website audit, growth opportunities, and engineering backlog.",
};

export const viewport: Viewport = {
  themeColor: "#f6f8fb",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const supabaseRuntimeConfig = {
    url: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
    publishableKey: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "",
  };

  return (
    <html lang="en">
      <body>
        <script
          dangerouslySetInnerHTML={{
            __html: `window.__WEBFORGE_SUPABASE__ = ${JSON.stringify(supabaseRuntimeConfig)};`,
          }}
        />
        {children}
      </body>
    </html>
  );
}
