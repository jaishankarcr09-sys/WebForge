"use client";

import { FormEvent, useEffect, useState } from "react";

type Site = { name: string; category: string; description: string };
type Status = { status?: string; note?: string; model_version?: string | null };

const blankSite = (): Site => ({ name: "", category: "", description: "" });

export default function SimilarWebsitesPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [source, setSource] = useState<Site>(blankSite());
  const [candidates, setCandidates] = useState<Site[]>([blankSite(), blankSite()]);
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function refreshStatus() {
    try {
      const response = await fetch("/api/similarity/status", { cache: "no-store" });
      const data = await response.json();
      setStatus(response.ok ? data : { status: response.status === 401 ? "sign_in_required" : "unavailable", note: data.detail || "Similarity status could not be loaded." });
    } catch {
      setStatus({ status: "unavailable", note: "Could not connect to the similarity service." });
    }
  }

  useEffect(() => { void refreshStatus(); }, []);

  function updateCandidate(index: number, field: keyof Site, value: string) {
    setCandidates(current => current.map((site, i) => i === index ? { ...site, [field]: value } : site));
  }

  async function rank(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(""); setMessage(""); setResults([]);
    try {
      const response = await fetch("/api/similarity/rank", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, candidates }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Similarity ranking is not available yet.");
      setResults(data.results || []);
      setMessage("Ranked candidates using model " + (data.model_version || "unknown") + ". Scores are ranking signals, not identity probabilities.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ranking request failed.");
    } finally {
      setBusy(false);
      void refreshStatus();
    }
  }

  return <main className="content" style={{ maxWidth: 1120, margin: "0 auto", width: "100%" }}>
    <header className="topbar">
      <div><span className="crumb">WebForge / Similar websites</span><h1>Similar Websites & Patterns</h1></div>
      <a className="secondary" href="/dashboard">Back to dashboard</a>
    </header>
    <section className="hero-card" style={{ marginBottom: 20 }}>
      <div className="hero-copy">
        <span className="eyebrow">SIMILARITY ENGINE · EARLY ACCESS</span>
        <h2>Find alternatives by what a website does.</h2>
        <p>Compare website metadata to rank potential substitutes. This first workbench deliberately uses supplied descriptions only; it does not crawl arbitrary URLs or claim that two companies are identical.</p>
      </div>
      <div className="panel" style={{ marginTop: 18 }}>
        <div className="section-title"><div><span className="eyebrow">MODEL STATUS</span><h2>{status?.status === "ready" ? "Model configured" : status?.status === "sign_in_required" ? "Sign in required" : status?.status === "unavailable" ? "Service unavailable" : "Model not ready"}</h2></div><button className="secondary" type="button" onClick={() => void refreshStatus()}>Refresh</button></div>
        <p>{status?.note || "Checking whether an evaluated model artifact is configured…"}</p>
      </div>
    </section>

    <form onSubmit={rank} className="panel" style={{ display: "grid", gap: 20 }}>
      <section>
        <div className="section-title"><div><span className="eyebrow">STEP 1</span><h2>Describe the source website</h2></div></div>
        <div className="form-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 12 }}>
          <label>Website / product name<input required value={source.name} onChange={e => setSource({ ...source, name: e.target.value })} placeholder="e.g. Shopify" /></label>
          <label>Primary category<input required value={source.category} onChange={e => setSource({ ...source, category: e.target.value })} placeholder="e.g. ecommerce platform" /></label>
          <label style={{ gridColumn: "1 / -1" }}>What does it help users do?<textarea required rows={3} value={source.description} onChange={e => setSource({ ...source, description: e.target.value })} placeholder="Describe its main product, audience, and use case." /></label>
        </div>
      </section>

      <section>
        <div className="section-title"><div><span className="eyebrow">STEP 2</span><h2>Add candidate websites</h2><p>Use public, factual descriptions. Include plausible alternatives and clear non-alternatives when testing.</p></div><button className="secondary" type="button" disabled={candidates.length >= 10} onClick={() => setCandidates(current => [...current, blankSite()])}>+ Add candidate</button></div>
        <div style={{ display: "grid", gap: 14 }}>
          {candidates.map((site, index) => <article key={index} className="panel similarity-workbench-enter" style={{ padding: 16 }}>
            <div className="section-title"><h3>Candidate {index + 1}</h3>{candidates.length > 1 && <button className="secondary" type="button" onClick={() => setCandidates(current => current.filter((_, i) => i !== index))}>Remove</button>}</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12 }}>
              <label>Name<input required value={site.name} onChange={e => updateCandidate(index, "name", e.target.value)} placeholder="Website name" /></label>
              <label>Category<input required value={site.category} onChange={e => updateCandidate(index, "category", e.target.value)} placeholder="Primary category" /></label>
              <label style={{ gridColumn: "1 / -1" }}>Description<textarea required rows={2} value={site.description} onChange={e => updateCandidate(index, "description", e.target.value)} placeholder="Main product, audience, and use case." /></label>
            </div>
          </article>)}
        </div>
      </section>

      {error && <div className="inline-error" role="alert">{error}</div>}
      {message && <p role="status">{message}</p>}
      <div><button className="primary" disabled={busy || status?.status === "model_not_configured"}>{busy ? "Ranking…" : "Rank similar websites"}</button></div>
    </form>

    {results.length > 0 && <section className="panel" style={{ marginTop: 20 }}>
      <div className="section-title"><div><span className="eyebrow">RANKING RESULTS</span><h2>Closest candidates first</h2></div></div>
      <div style={{ display: "grid", gap: 12 }}>{results.map((item, index) => <article key={item.name + index} className="panel similarity-workbench-enter" style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 12, alignItems: "center" }}><strong>#{index + 1}</strong><div><h3>{item.name}</h3><p>{item.category}</p><small>{item.description}</small></div><strong>{Number(item.score).toFixed(3)}</strong></article>)}</div>
    </section>}
    <p style={{ marginTop: 16, opacity: .75, fontSize: 13 }}>Early-stage feature: a trained artifact must be configured before scores are available. Do not treat seed-data results as production quality.</p>
  </main>;
}
