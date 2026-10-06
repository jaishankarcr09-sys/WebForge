# WebForge Stack

## PostgreSQL + Supabase

WebForge uses PostgreSQL as its persistent database.

Supabase can provide the managed PostgreSQL instance and later provide authentication/storage/realtime features. The backend only requires a PostgreSQL connection string, so a Supabase database can be supplied through DATABASE_URL without changing the core data layer.

## Redis

Redis is used for fast state, caching, and the background scan queue that will be introduced as scans become asynchronous.

## Railway

Railway is the deployment target for the WebForge API, scanner worker, Redis service, and supporting infrastructure.

## Scanner

- Requests for lightweight HTTP fetching
- BeautifulSoup for HTML parsing
- Playwright for browser-level analysis in the next phase

## AI

The AI layer will consume structured findings from deterministic analyzers and turn them into explanations, prioritized backlog items, and implementation guidance.
