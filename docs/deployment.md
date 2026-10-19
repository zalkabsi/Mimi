# Deployment guide

## Read-only hosted replay

The repository can produce a static, no-credential demo. Build it from
`frontend/`:

```bash
npm ci
npm run build:demo
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

The image builds with `npm run build:demo`, serves the single-page app with a
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

## Combined live judge service on Render

`render.yaml` defines one Free web service built with `Dockerfile.judge`.
The image serves the live React app and the API from one origin through
`mimi.web:app`. The frontend uses hash routing and an empty API base, so it
requires neither a separate frontend deployment nor cross-origin requests.
The existing replay and API-only containers remain available separately.

Render generates the judge access key and prompts for the three provider
settings. Put real deployment credentials in its secret manager. Session-proxy
credential placeholders are not portable hosting secrets. See
[judge access and budget](judge-access.md) for current status, provider costs,
the verification walkthrough, and Free-plan sleep/data-retention limits.

The Free plan does not support `maxShutdownDelaySeconds`; leave that setting
unset. A process restart can interrupt an active report, which the API marks
as an error when it next reads the orphaned job.

For a local image smoke check without provider access:

```bash
docker build -f Dockerfile.judge -t mimi-judge .
docker run --rm -p 127.0.0.1:8000:8000 mimi-judge
```

Open `http://localhost:8000`; without a judge key, live submissions remain
unavailable. The image honors the host's `PORT` and runs one Uvicorn worker.

## Current deployment status

On 2026-10-18, both images rebuilt from the readiness changes. The API passed
health, inbox, sample dossier, recorded events, completed SSE, private-report
denial (401), and unauthenticated submission denial (402). Chromium opened and
refreshed the container replay's sample dossier successfully.

PR #6 merged as `4c10ee1` on October 19. The Pages deployment and post-merge CI
both passed. A fresh signed-out Chromium context opened the updated public
replay, used **Open sample dossier**, downloaded the JSON, and refreshed the
hash route without page errors or backend requests. Its replay manifest also
passed validation. Browser requests used TLS-verified HTTP forwarding because
Chromium did not trust the session proxy CA.

On October 19, the Render API created `mimi-judge`
(`srv-dbb4beqjnfac73euoa10`) on the Free plan in Frankfurt, with one instance,
`master` as its source, and deployment after CI checks pass. The first deployment
of `36405e3` is live at [mimi-judge.onrender.com](https://mimi-judge.onrender.com).
TLS-verified HTTP checks pass for the root page, both frontend assets, API health,
sample inbox, dossier, recorded events, and completed SSE. Private report reads
without a key return 401; unauthenticated submissions return 402. The generated
judge key authenticates, and a missing private report returns 404 with it.

`NEBIUS_PROJECT_ID` and a generated `MIMI_JUDGE_KEY` are configured in Render.
The operator still needs to add `NEBIUS_API_KEY` and `TAVILY_API_KEY` in the
service's environment settings, deploy, and complete a hosted public-package
report. Codex's domain-restricted Network secrets must not be copied as hosting
credentials. Tavily's funded usage limit is 625 credits; the previously verified
backend research client returned three unique advisories without errors.
Provider funding and key lifetime through December 15 remain owner checks. See
[judge access](judge-access.md) and the [readiness review](readiness-review.md).
