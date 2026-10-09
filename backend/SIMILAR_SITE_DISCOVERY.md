# Similar website discovery

WebForge discovers candidate sites from multiple topic-specific web searches, deduplicates them by hostname, attempts a one-page crawl to verify that each candidate is reachable, and ranks the surviving candidates using a transparent heuristic based on search-result text and the detected website category.

## Search provider configuration

- `BRAVE_SEARCH_API_KEY` (optional): when set, WebForge queries the Brave Search API first. Obtain a key from Brave Search API and configure it as a backend/Railway environment variable.
- If Brave is not configured, returns no results, or errors, WebForge falls back to best-effort DuckDuckGo HTML search.

The search providers index only part of the public web. Results are not an exhaustive inventory of every website, and the fallback provider may limit automated requests. Candidate verification and crawling can also fail for sites that block bots, require authentication, or have temporary outages.

## Result fields

Each `similar_sites` item includes the candidate name, URL, search snippet, source, detected website category, measured feature snapshot, heuristic `relevance_score`, and `match_reason`. The relevance score is a ranking heuristic, not a probability or an AI-verified claim of business similarity.

Discovery runs as part of the audit's intelligence phase. Errors for individual candidates are isolated so a single inaccessible website does not stop the main audit.
