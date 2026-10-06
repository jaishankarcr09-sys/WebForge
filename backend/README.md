# WebForge Backend

FastAPI service for website auditing.

## Run locally

From backend/:
uvicorn app.main:app --reload

Endpoints:
- GET /health
- POST /api/v1/audits/analyze
