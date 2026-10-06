import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "WebForge",
  description: "AI-powered website audit and improvement backlog generator.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
