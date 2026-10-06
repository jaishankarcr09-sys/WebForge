"use client";

import { FormEvent, useState } from "react";

type Issue = {
  category: string;
  title: string;
  severity: string;
  impact: string;
  recommendation: string;
};

type Audit = {
  score: number;
  issues: Issue[];
};

const API_URL = "";

export default function Home() {
  const [url, setUrl] = useState("");
  const [audit, setAudit] = useState<Audit | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setAudit(null);

    try {
      const response = await fetch(`${API_URL}/api/audits/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Analysis failed");
      setAudit(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">WEBFORGE</p>
        <h1>Turn any website URL into an improvement backlog.</h1>
        <p className="subtitle">
          Scan a site, detect actionable problems, score them, and turn the
          findings into engineering work.
        </p>

        <form onSubmit={handleSubmit} className="scan-form">
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com"
            type="url"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </form>

        {error && <p className="error">{error}</p>}
      </section>

      {audit && (
        <section className="results">
          <div className="score-card">
            <span>Website Health</span>
            <strong>{audit.score}</strong>
            <small>/ 100</small>
          </div>

          <div className="issues">
            <div className="section-heading">
              <h2>Detected backlog</h2>
              <span>{audit.issues.length} issue(s)</span>
            </div>

            {audit.issues.length === 0 ? (
              <div className="empty">No MVP issues detected.</div>
            ) : (
              audit.issues.map((issue) => (
                <article key={issue.title} className="issue">
                  <div className="issue-top">
                    <div>
                      <span className="category">{issue.category}</span>
                      <h3>{issue.title}</h3>
                    </div>
                    <span className={`severity ${issue.severity}`}>
                      {issue.severity}
                    </span>
                  </div>
                  <p>{issue.impact}</p>
                  <div className="recommendation">
                    <strong>Recommended change</strong>
                    <p>{issue.recommendation}</p>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      )}
    </main>
  );
}
