"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Provider = "google" | "github";

export default function LoginPage() {
  const [loading, setLoading] = useState<Provider | "email" | null>(null);
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  async function oauth(provider: Provider) {
    setLoading(provider);
    setMessage("");

    try {
      const supabase = createClient();
      const redirectTo = new URL("/auth/callback", window.location.origin).toString();

      // Ask Supabase for the provider URL first, then navigate explicitly.
      // This prevents the button from sitting on "Connecting..." when the
      // browser redirect is blocked or the provider is not configured.
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo,
          skipBrowserRedirect: true,
        },
      });

      if (error) {
        setMessage(error.message);
        setLoading(null);
        return;
      }

      if (!data?.url) {
        setMessage("Sign-in could not start. Check the OAuth provider configuration in Supabase.");
        setLoading(null);
        return;
      }

      window.location.assign(data.url);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start sign-in.");
      setLoading(null);
    }
  }

  async function magicLink() {
    const normalizedEmail = email.trim();
    if (!normalizedEmail) return;

    setLoading("email");
    setMessage("");

    try {
      const supabase = createClient();
      const emailRedirectTo = new URL("/auth/callback", window.location.origin).toString();

      const { error } = await supabase.auth.signInWithOtp({
        email: normalizedEmail,
        options: { emailRedirectTo },
      });

      setMessage(error ? error.message : "Check your email for the secure sign-in link.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to send the sign-in link.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <a href="/" className="brand-lockup">
          <span className="brand-mark">W</span>
          <span>
            <strong>WebForge</strong>
            <small>Audit Intelligence</small>
          </span>
        </a>

        <div className="auth-copy">
          <span className="eyebrow">WELCOME BACK</span>
          <h1>Know exactly what to fix.</h1>
          <p>Keep audits, history, engineering backlog, and growth opportunities in one private workspace.</p>
        </div>

        <div className="oauth-grid">
          <button
            type="button"
            className="provider-btn"
            onClick={() => oauth("google")}
            disabled={!!loading}
          >
            <span className="provider-badge">G</span>
            {loading === "google" ? "Opening Google…" : "Continue with Google"}
          </button>

          <button
            type="button"
            className="provider-btn"
            onClick={() => oauth("github")}
            disabled={!!loading}
          >
            <span className="provider-badge dark">GH</span>
            {loading === "github" ? "Opening GitHub…" : "Continue with GitHub"}
          </button>
        </div>

        <div className="divider">
          <span>or use email</span>
        </div>

        <div className="magic-row">
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !loading) magicLink();
            }}
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            disabled={!!loading}
          />
          <button type="button" onClick={magicLink} disabled={!email.trim() || !!loading}>
            {loading === "email" ? "Sending…" : "Send magic link"}
          </button>
        </div>

        {message && <p className="auth-message">{message}</p>}

        <div className="trust-row">
          <span>Private workspace</span>
          <span>Secure cookies</span>
          <span>OAuth-ready</span>
        </div>
      </section>

      <aside className="auth-visual">
        <div className="glow one"></div>
        <div className="glow two"></div>
        <div className="visual-copy">
          <span className="eyebrow">FROM URL TO ACTION</span>
          <h2>Audit the experience. Understand the stack. Build the next sprint.</h2>
          <p>WebForge turns measurable website weaknesses into prioritized engineering work — with evidence, impact, and clear fixes.</p>
          <div className="visual-metrics">
            <div><strong>SEO</strong><span>discoverability</span></div>
            <div><strong>WEB</strong><span>performance</span></div>
            <div><strong>UX</strong><span>accessibility</span></div>
            <div><strong>ENG</strong><span>backlog</span></div>
          </div>
        </div>
      </aside>
    </main>
  );
}
