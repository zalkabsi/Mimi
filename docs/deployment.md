# Deployment guide

## Read-only hosted replay

The repository can produce a static, no-credential demo. Build it from
`frontend/`:

```bash
npm ci
VITE_USE_MOCK=1 npm run build
```

Upload `frontend/dist/` to a static host and enable single-page-app fallback
to `index.html` so links such as `/reports/mock0000demo` load directly. This
build embeds the labelled fixture, makes no backend or provider calls, hides
the submission and access-key fields, and is safe to expose publicly. It is a
UI replay, not an end-to-end live analysis.

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

Live submissions require `NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`, and
`MIMI_JUDGE_KEY`; live report contents and event streams also require the
judge key. `TAVILY_API_KEY` enables live research. This is one shared key, not
per-user report isolation: every key holder can read all live reports. Do not
accept private reports on a shared demo. Keep the live submission endpoint
unavailable until Sandboxes permissions and per-run network isolation are
verified. The latest recorded Sandboxes response is HTTP 403; see
[`00-constraints-and-open-items.md`](00-constraints-and-open-items.md). A
judge credential must be configured by the deployment owner and remain
available through the judging period. No credential is included in this
repository.

Run one backend worker. Job tracking and live event fan-out are process-local;
multiple Uvicorn workers would not share the active job registry or SSE queues.
If the process restarts during a job, the inbox marks its orphaned `running`
row as `error` rather than leaving it stuck.

## Current deployment status

The static build is ready for upload, and the `mimi-replay` container image
built locally on 2026-10-15. Neither has been published to a host or container
registry. No public URL or hosted backend is configured yet; creating a URL,
setting the correct audience, and checking it from a clean browser are still
required before submission. If published as a replay demo, label it read-only
and do not describe the fixture as a live pipeline result.
