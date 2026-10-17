# Mimi frontend

Evidence-first triage UI for Mimi: report inbox, live stage timeline, and the
dossier view (tier, coverage, hypotheses, runs, oracles, differential, reply
draft, cost, limitations).

Vite + React + TypeScript + Tailwind CSS. Dark UI; monospace for code,
commands and outputs. Text names only — no third-party logos.

## Run it

```bash
cd frontend
npm install
npm run dev
```

Then open the URL Vite prints (default <http://localhost:5173>).

The UI expects the Mimi backend on `http://localhost:8000`:

```bash
cd backend
uvicorn mimi.api:app --reload --port 8000
```

With no provider credentials, the backend serves one read-only, clearly labelled
sample dossier and its recorded timeline. This is fixture data, not a live
analysis. Live submissions require `MIMI_JUDGE_KEY` plus the provider
credentials and Sandboxes access described in the root README.

## Configuration

| Variable          | Default                 | Meaning                                              |
| ----------------- | ----------------------- | ---------------------------------------------------- |
| `VITE_API_BASE`   | `http://localhost:8000` | Backend base URL (single constant in `src/lib/api.ts`). |
| `VITE_USE_MOCK`   | unset                   | `1` serves `src/mocks/dossier.json` instead of live data. |

Examples (PowerShell):

```powershell
$env:VITE_API_BASE = "http://localhost:8000"
npm run dev
```

```powershell
# Develop without any backend: fixture data, header shows "sample".
$env:VITE_USE_MOCK = "1"
npm run dev
```

On bash-like shells: `VITE_USE_MOCK=1 npm run dev`.

## Scripts

| Command             | What it does                        |
| ------------------- | ----------------------------------- |
| `npm run dev`       | Vite dev server with HMR            |
| `npm run build`     | Type-check then production build    |
| `npm run preview`   | Serve the production build locally  |
| `npm run typecheck` | TypeScript only, no emit            |

## Layout

- `src/lib/api.ts` — typed client: `listReports`, `getReport`, `getEvents`,
  `submitReport` (optional `X-Mimi-Key`), `streamEvents` (SSE on
  `/api/reports/{id}/stream` with polling fallback).
- `src/types.ts` — UI mirror of `backend/mimi/schemas.py` (Dossier, StageEvent,
  Tier, RunRecord, Hypothesis, OracleResult, Coverage, …).
- `src/views/InboxView.tsx` — submit form + report table.
- `src/views/ReportView.tsx` — live timeline + dossier sections.
- `src/mocks/dossier.json` — fixture shaped exactly like a real Dossier.

Missing values render as `—` or "not measured" — the UI never invents a metric.
