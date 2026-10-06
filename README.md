# WebForge

AI-powered website audit and improvement backlog generator.

WebForge accepts a website URL, analyzes the site for technical, SEO, performance, accessibility, and UX issues, prioritizes findings, and generates actionable improvement recommendations.

## Architecture

Next.js Frontend
→ FastAPI API
→ Redis Job Queue
→ Scanner Worker
→ Rule-based Analyzers
→ PostgreSQL
→ AI Recommendation Layer
→ Dashboard

## Stack

- Next.js
- FastAPI
- PostgreSQL
- Redis
- Playwright
- BeautifulSoup
- Railway
- LLM API

## MVP

URL → crawl → deterministic checks → issues → priority → backlog → dashboard

AI is added after the deterministic auditing pipeline is reliable.
