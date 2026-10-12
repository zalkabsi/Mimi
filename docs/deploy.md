# Hosting for judges (until Dec 15, 2026, 12:00 PM PT)

The app is one container: FastAPI plus the built React UI on the same origin (`Dockerfile`). Verified locally: with `MIMI_FRONTEND_DIST` set, uvicorn serves the UI and `/api/*`, and the seeded demo inbox loads with no keys. The Docker image itself has **not** been built in this environment (no daemon), so build it once before relying on it.

```bash
docker build -t mimi .
docker run -p 8000:8000 -v mimi-data:/data \
  -e NEBIUS_API_KEY -e NEBIUS_PROJECT_ID -e TAVILY_API_KEY -e MIMI_JUDGE_KEY mimi
```

Access tiers: with no `MIMI_JUDGE_KEY` the app is read-only demo mode (recorded real runs from `backend/mimi/data/demo/`, free, no login). With the key set, a request carrying `X-Mimi-Key` can run live reports.

## Decisions only the owner can make

1. **Host and monthly ceiling.** Any container host that keeps a volume for `/data` and stays up until Dec 15 works. Pick one, note the fixed monthly cost, and confirm it fits the credits.
2. **Judge credential.** Generate a long random `MIMI_JUDGE_KEY` and put it in the Devpost testing instructions. Live runs spend the owner's Nebius credits, so set a spend ceiling (`per_report_cost_cap`, `max_runs_per_report` in `config.py`) and watch the balance.
3. **Key lifetime.** The Nebius key used by the hosted app must stay valid through Dec 15, 2026 (check the expiry in the console; `whoami`'s `token_expiration` is a rolling value, not the lifetime).
4. **Keep demo mode always on.** If credits run out, the recorded inbox must still work; do not remove it.
