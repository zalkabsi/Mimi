# Hosting for judges (until Dec 15, 2026, 12:00 PM PT) at minimal cost

The app is one container: FastAPI plus the built React UI on the same origin (`Dockerfile`).

## What was and was not verified

- **Verified here:** the UI builds with relative API URLs; a clean (non-editable) install of the backend in a fresh virtualenv starts, serves the UI and `/api/*`, and loads the three recorded demo reports with no keys (this caught missing package data, now fixed in `backend/pyproject.toml`).
- **Not verified here:** `docker build`. The build environment's network policy blocks Docker Hub (`python:3.12-slim`, `node:20-slim` could not be pulled), so build the image once on your machine or on the host before relying on it. Everything the Dockerfile runs was exercised separately as above.

```bash
docker build -t mimi .
docker run -p 8000:8000 -v mimi-data:/data \
  -e NEBIUS_API_KEY -e NEBIUS_PROJECT_ID -e TAVILY_API_KEY \
  -e MIMI_JUDGE_KEY -e MIMI_MAX_LIVE_RUNS_PER_DAY=30 mimi
```

## Cheapest way to meet "free and unrestricted until Dec 15"

1. **Host: a scale-to-zero or free container host.** Any of these costs about nothing for judge traffic: Google Cloud Run (pay per request, free tier, set max instances 1), or a free Docker Space on Hugging Face (set `app_port: 8000` in the Space's README front matter). The database is SQLite and may reset when the container restarts; that is fine because the three recorded demo reports are re-seeded from files on every start.
2. **Spend ceiling is built in.** Live runs cost roughly $0.01-0.10 each in inference at the rates I assumed (sandbox cost is not measured). The API refuses live runs after `MIMI_MAX_LIVE_RUNS_PER_DAY` (default 50, 429 with a clear message) and each report is capped by `max_runs_per_report`. Pick the daily number from your remaining credits; demo mode is unaffected.
3. **Judge key:** `python -c "import secrets; print(secrets.token_urlsafe(32))"`, store it as `MIMI_JUDGE_KEY` in the host's secret settings, and paste it into the Devpost testing instructions.
4. **Nebius key:** use a key created for this demo with an expiry on or after Dec 15, 2026 and confirm that expiry in the Nebius console. The API's `token_expiration` field is a rolling value and cannot show it.
5. **Keep demo mode on.** If credits run out the recorded inbox still works.

Nothing here needs a paid plan. The only recurring cost is the Nebius credits that live runs spend.
