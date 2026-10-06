# WebForge Architecture

URL
→ Next.js
→ FastAPI
→ Redis jobs/cache
→ Scanner
→ analyzers
→ PostgreSQL
→ AI recommendations
→ dashboard

The first slice is synchronous so the product can be validated quickly.

Planned evolution:
1. Persist audits/issues in PostgreSQL.
2. Move scans to Redis-backed workers.
3. Add Playwright browser analysis.
4. Expand SEO, accessibility, performance and UX checks.
5. Add AI explanations and implementation guidance.
6. Add authentication and audit history.
7. Deploy on Railway.

Production crawlers must enforce SSRF protections and never expose arbitrary internal-network access.
