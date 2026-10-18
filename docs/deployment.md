# Deployment guide

## Read-only hosted replay

The repository can produce a static, no-credential demo. Build it from
`frontend/`:

```bash
npm ci
VITE_USE_MOCK=1 npm run build
```

The build embeds the labelled fixture, makes no backend or provider calls,
hides the submission and access-key fields, and is safe to expose publicly. It
is a UI replay, not an end-to-end live analysis.

### GitHub Pages

The `Deploy read-only demo` workflow publishes the fixture to GitHub Pages
when frontend changes are pushed to `master`; it can also be run manually.
It builds with the repository base path and hash routing,
so direct links work without server-side SPA fallback. The public URL is
[`https://zalkabsi.github.io/Mimi/`](https://zalkabsi.github.io/Mimi/). The
published page is a read-only replay, not a live vulnerability analysis.

The owner has enabled the public repository, Actions, and Pages. Merging
frontend or workflow changes to `master` starts a deployment automatically;
you can also open **Actions → Deploy read-only demo → Run workflow** to deploy
manually. The workflow token cannot create or enable the Pages site, so the
one-time owner setting must remain enabled. After each deployment, check the
URL in a clean browser and open the inbox and sample dossier. Keep the page
free of login requirements through the judging period. This hosted replay is
read-only and must not be presented as a live Mimi analysis.

For a container host, the frontend includes a self-contained static replay
image. Build it from `frontend/` and route traffic to port `8080`:

```bash
docker build -t mimi-replay .
docker run --rm -p 127.0.0.1:8080:8080 mimi-replay
```

The image builds with `VITE_USE_MOCK=1`, serves the single-page app with a
history fallback, runs Nginx as an unprivileged user, and exposes `/healthz`
for a container health check. It contains no backend, credentials, or live
submission path. Use the static bundle or this image for a free, read-only
judge walkthrough; do not describe it as a live analysis service.

## Self-hosted API

Build the backend container from the repository root:

```bash
docker build -f backend/Dockerfile -t mimi-api .
docker run --rm -p 127.0.0.1:8000:8000 \
  -v mimi-data:/data \
  -e MIMI_DB_PATH=/data/mimi.db \
  mimi-api
```

Without provider keys and `MIMI_JUDGE_KEY`, the API remains read-only and
serves the bundled dossier and timeline. Set `MIMI_CORS_ORIGINS` to the
frontend's exact origin when the frontend is on another origin. Keep secrets
in the host's secret manager; never add them to the image or its build args.

Live submissions require `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`, and `MIMI_JUDGE_KEY`; live report
contents and event streams also require the judge key. `TAVILY_API_KEY` enables live research.
This is one shared key, not per-user report isolation: every key holder can read all live
reports. Do not accept private reports on a shared demo.

Keep the live submission endpoint unavailable until a real vulnerability run and a security
review of the execution boundary are complete. A harmless no-op Sandbox operation succeeded:
Mimi confirmed its child network namespace and its probe observed an outbound TCP attempt
blocked with ENETUNREACH. This verifies the basic integration and app-level guard for that
run, not arbitrary PoC containment or provider-level microVM security. See [constraints and
open items](00-constraints-and-open-items.md).

A judge credential must be configured by the deployment owner and remain available through
the judging period. No credential is included in this repository.

Run one backend worker. Job tracking and live event fan-out are process-local;
multiple Uvicorn workers would not share the active job registry or SSE queues.
If the process restarts during a job, the inbox marks its orphaned `running`
row as `error` rather than leaving it stuck.

## Current deployment status

The static build and `mimi-replay` container image built locally on
2026-10-16. The backend image also rebuilt from the current patch on
2026-10-18; no-credential health, inbox, and sample-dossier checks passed.
After the reviewed changes were merged, Pages run
[39055999541](https://github.com/zalkabsi/Mimi/actions/runs/39055999541)
completed both build and deploy successfully on 2026-10-17. The owner
confirmed that the public URL loads the inbox and fixed sample dossier on
2026-10-16. A private or clean-browser check remains to be done before
submission. A direct HTTPS request returned HTTP 200 on 2026-10-18; that
does not replace the pending clean-browser check. The page remains a replay,
not a live pipeline result.
