# Repository and submission readiness review

Reviewed October 18–19, 2026 against commit `1f9c5b7` and the readiness changes.
Upstream `0dd530a` records the owner's approval of the existing public video;
that approval and the existing submission link are preserved.
Scope: backend and frontend source, test behavior, package audits, production
builds, container smoke checks, browser flows, demo assets, and submission requirements.

The readiness changes are merged and the updated public Pages replay is
deployed and verified. Tavily funding is restored and the backend research
client is verified. Final submission still depends on hosted live judge access
and the provider-lifetime steps below.

## Problems fixed

| Priority | Finding | Result |
| --- | --- | --- |
| High | Synchronous inference, registry, and research calls blocked the API event loop during live jobs. | Each API job now runs in a worker with its own event loop. Health and report reads remain responsive during a blocking stage. |
| High | A submitted report could return 404 before its worker's first database write. | The API persists an initial dossier before returning the report ID. |
| High | An unexpected worker failure left the dossier without an explanation and published an incomplete event. | The error dossier, typed terminal event, and error status are saved before the stream closes. |
| High | Frontend audit reported 13 affected dependency entries, including 10 high-severity entries. | Updated Vite, React Router, React's Vite plugin, and Tailwind; migrated the Tailwind integration. Final npm audit reports zero known advisories. These are dependency audit results, not proof of exploitable app paths. |
| High | An API test could start a real provider job when credentials were present; cancellation was its only safeguard. | The HTTP-contract test uses a fake pipeline, and the socket guard now applies to every backend test. |
| Medium | Every replay report URL returned the same sample, including nonexistent IDs. | Unknown sample IDs now show a missing-report error. |
| Medium | Navigating between report IDs could leave the previous report's evidence visible after a failed fetch. | Report state is scoped to its ID; browser regression coverage verifies the error view clears previous evidence. |
| Medium | The inbox's clickable table rows had no keyboard-accessible report link. | Each report has a real link, and the replay has an Open sample dossier action. |
| Medium | The tier guide omitted the fixed-version requirement for Confirmed and the thresholds for Contradicted. | The guide now matches the deterministic tier policy. |
| Medium | Grounding bounded compressed downloads but allowed unbounded archive expansion and indexing. | Added a 32 MiB expanded-content budget and a 4096-entry limit. Unsupported, incomplete, or oversized archives produce a note instead of negative evidence. |
| Medium | Large files could be marked absent when their content was skipped; file-name substrings could be mistaken for the cited path. | File existence is indexed separately from content scanning, skipped source content makes symbol absence inconclusive, and file matching uses complete path components. Four grounding regressions cover the limits and evidence behavior. |
| Medium | Provider-generated research URLs were rendered as links without restricting their scheme. | Only absolute HTTP(S) URLs become links; malformed and unsupported schemes remain reviewable text. A browser regression checks both advisory and fix references. |
| Medium | The frontend had no automated browser checks. | Seven checks cover production replay, unknown IDs, mobile overflow, exports, access keys, completed SSE, report navigation, and research URL handling; CI runs them. Test servers use dedicated ports and refuse to reuse an unknown build. |
| Medium | Setup guidance allowed obsolete Node versions; replay launch required shell-specific environment syntax. | Documented the supported Node range and added cross-platform `npm run demo` / `build:demo` commands. |
| Medium | The default virtualenv bootstrap installed an older pip with known advisories. | Updated the local pip and the documented, Make, and Docker bootstrap steps. The final environment's Python dependency audit is clear. |
| Medium | SQLite's `.db-wal` and `.db-shm` sidecar files were not ignored and could be accidentally committed with live report data. | Added ignore patterns for both sidecars. |
| Demo | Current inbox/dossier captures and an exported demo video were missing. | Refreshed three screenshots and prepared a narrated, captioned 720p MP4 under three minutes, with reproducible capture tooling. |
| Demo | There was no portable submission bundle or dossier export. | Added JSON dossier downloads, a replay build manifest, checked source/replay ZIP packaging, and SHA-256 hashes. Packaging verifies that frontend and backend fixtures match. |
| Deployment | Pages is a static replay and cannot run live jobs; frontend/API hosting was separate. | Prepared a combined live image with same-origin API requests, a Free Render Blueprint, an access-control regression, and a CI image smoke check. Render is installed; actual provisioning, hosting secrets, and live verification remain pending. |

## Verification

| Check | Result |
| --- | --- |
| Backend | 200 tests on Python 3.12, including the combined host's static/API routing and access checks. Backend test sockets are guarded against external connections; the isolated web smoke removes provider credentials and makes no provider calls. One upstream Starlette/httpx deprecation warning remains. |
| GitHub CI | Merged readiness PR #6 and post-merge Python 3.12/3.13 and frontend jobs passed in [run 39227969084](https://github.com/zalkabsi/Mimi/actions/runs/39227969084). |
| Branch protection | The owner activated [Protect master](https://github.com/zalkabsi/Mimi/rules/25390422). GitHub reports `master` protected; the active rules block force pushes/deletion, require PRs and all three CI checks, and have no bypass actors. Verified October 19 through GitHub's branch and ruleset APIs. |
| Frontend | Live production build and dedicated replay build pass. Seven Chromium checks pass, including a 390px mobile viewport. |
| Dependencies | `npm audit`: zero known advisories. Python environment audit with pip-audit/PyPI: zero known advisories after upgrading pip. |
| Docker | Both images build. API health, inbox, dossier, events, completed SSE, private-ID denial (401), and submission denial (402) pass. Replay inbox and refreshed dossier route work in Chromium. |
| Combined judge image | Builds and starts on a custom `PORT` as a non-root user. Chromium verifies the same-origin API inbox, dossier, and hash-route refresh with no page errors or external calls. API health, sample dossier, private-ID denial (401), and submission denial (402) pass. Hosting is not yet provisioned. |
| Public replay | PR #6 merged as `4c10ee1`, and [Pages deployment 39227968643](https://github.com/zalkabsi/Mimi/actions/runs/39227968643) passed. A fresh signed-out Chromium context verified the updated inbox, sample link, JSON download, hash-route refresh, and replay manifest with no page errors or backend calls. Requests used TLS-verified HTTP forwarding because Chromium did not trust the session proxy CA. |
| Live providers | A bounded Nemotron Nano inference smoke returned nonempty content (38 input / 45 output tokens). Sandboxes whoami returned all six permissions. On October 19, the owner restored Tavily funding with a 625-credit pay-as-you-go limit: a direct search returned 200, then the real backend client completed four queries and returned three unique advisories without error notes. No new vulnerability-reproduction accuracy claim is made. |
| Demo | 158.32-second, 1280×720 H.264/AAC MP4: actual replay screen recording, original synthetic narration, and burned-in English captions. Refreshed screenshots and narration/shot sources are included. ffprobe metadata is retained locally in `artifacts/demo-raw/export-metadata.json`. |
| Media and packaging | Chromium playback and seeking near the ending pass; full FFmpeg decoding reports no errors. ZIP CRCs and inner SHA-256 hashes pass. The extracted portable replay opens and refreshes under a nested static-host path without API requests. |

Reproduce app checks with `make setup`, `make browser`, and `make verify`.
Use `PLAYWRIGHT_CHROMIUM_EXECUTABLE=/path/to/chromium` when selecting a system
browser. The backend suite's socket guard permits loopback only; the browser
suite uses fixtures and intercepted live-client HTTP responses.

## Remaining submission steps

The [Official Rules](https://nebiusglobalaihackathon.devpost.com/rules) require
a working project, public repository, public YouTube demo, English materials,
track choice, product feedback, and free access for judges through December 15.
The deadline is **October 30, 2026 at 20:00 Asia/Riyadh** (10:00 AM Pacific).
The rules were recovered through indexed official-page results on October 18
after direct retrieval returned 403; recheck the rules before submitting.

1. **Publish and verify free live judge access.** The Render Blueprint and
   combined frontend/API image are prepared, and Render is installed. Its
   deployment tools are not exposed in this chat. Use the prepared
   [Blueprint launch link](judge-access.md#render-launch-and-verification), or
   verify an existing service, with real hosting secrets and a complete public-package
   report. No hosted live URL, funded judge credential, or provider-key lifetime
   through December 15 has been established. Keep Pages as a clearly labelled
   replay. See [judge access](judge-access.md) for the rollout, private credential
   handoff, funding, and Free-plan limits.
2. **Complete the Devpost draft.** Use [the submission kit](submission-kit.md),
   Track 2, the repository URL, the verified hosted-access instructions, the
   approved public video URL, and the Token Factory/Nemotron feedback. The owner
   completes the final submission and attestations.

The approved public video remains [Mimi](https://youtu.be/y4rlh4hlkcw), recorded
in upstream `0dd530a`. This session did not independently recheck YouTube
playback. Uploading the optional updated local MP4 is not required to retain
the approved link. Branch protection, the readiness merge, Pages verification,
and Tavily recovery are complete.

## Product limits to keep visible

The existing E1 pilot produced zero fixed-version-confirmed reproductions in
11 real cases. In E2, none of five fabricated reports was Contradicted and one
incorrectly reached Likely. These results do not establish reliable automated
triage or useful fabricated-report detection. Keep the evidence-first prototype
framing and the [published evaluation limits](evaluation-results.md).

Hostile-code containment and the provider boundary remain unverified. Probe
observations share a writable VM with the PoC, and sandbox costs use raw units
with unknown currency conversion. The shared judge key grants access to every
live report on that deployment. Use public samples for a shared judge service
and keep the execution-boundary review and key lifetime as unresolved items.
