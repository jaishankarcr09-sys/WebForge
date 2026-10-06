"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const [loading, setLoading] = useState<"google" | "github" | "email" | null>(null);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  async function oauth(provider: "google" | "github") {
    setLoading(provider); setMessage("");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: window.location.origin + "/auth/callback" },
    });
    if (error) { setMessage(error.message); setLoading(null); }
  }

  async function magicLink() {
    if (!email) return;
    setLoading("email"); setMessage("");
    const supabase = createClient();
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin + "/auth/callback" },
    });
    setMessage(error ? error.message : "Check your email for the secure sign-in link.");
    setLoading(null);
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <a href="/" className="brand-lockup"><span className="brand-mark">W</span><span><strong>WebForge</strong><small>Audit Intelligence</small></span></a>
        <div className="auth-copy">
          <span className="eyebrow">WELCOME BACK</span>
          <h1>Know exactly what to fix.</h1>
          <p>Keep audits, history, engineering backlog, and growth opportunities in one private workspace.</p>
        </div>
        <div className="oauth-grid">
          <button className="provider-btn" onClick={() => oauth("google")} disabled={!!loading}><span className="provider-badge">G</span>{loading === "google" ? "Connecting…" : "Continue with Google"}</button>
          <button className="provider-btn" onClick={() => oauth("github")} disabled={!!loading}><span className="provider-badge dark">GH</span>{loading === "github" ? "Connecting…" : "Continue with GitHub"}</button>
        </div>
        <div className="divider"><span>or use email</span></div>
        <div className="magic-row"><input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="you@company.com" /><button onClick={magicLink} disabled={!email || !!loading}>{loading === "email" ? "Sending…" : "Send magic link"}</button></div>
        {message && <p className="auth-message">{message}</p>}
        <div className="trust-row"><span>Private workspace</span><span>Secure cookies</span><span>OAuth-ready</span></div>
      </section>
      <aside className="auth-visual">
        <div className="glow one"></div><div className="glow two"></div>
        <div className="visual-copy"><span className="eyebrow">FROM URL TO ACTION</span><h2>Audit the experience. Understand the stack. Build the next sprint.</h2><p>WebForge turns measurable website weaknesses into prioritized engineering work — with evidence, impact, and clear fixes.</p>
          <div className="visual-metrics"><div><strong>SEO</strong><span>discoverability</span></div><div><strong>WEB</strong><span>performance</span></div><div><strong>UX</strong><span>accessibility</span></div><div><strong>ENG</strong><span>backlog</span></div></div>
        </div>
      </aside>
    </main>
  );
}
