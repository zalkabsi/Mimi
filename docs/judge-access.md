# Judge access

## Verified public replay

Open [Mimi's public replay](https://zalkabsi.github.io/Mimi/) without an account.
Choose **Open sample dossier**, inspect the evidence and reply draft, and use
**Download dossier** to save the JSON. This is labelled fixture data, with no
provider calls. The approved video remains [Mimi](https://youtu.be/y4rlh4hlkcw).

PR #6 was merged to `master` as `4c10ee1` on October 19, 2026. The Pages
[deployment](https://github.com/zalkabsi/Mimi/actions/runs/39227968643) succeeded.
A fresh signed-out Chromium session verified the new sample link, JSON
download, and route refresh; `/Mimi/demo-manifest.json` identifies the replay.

## Live access status

**The live app is verified at [mimi-judge.onrender.com](https://mimi-judge.onrender.com).**
On October 19, 2026, Render created
`mimi-judge` (`srv-dbb4beqjnfac73euoa10`) on its Free plan in Frankfurt with one
instance. It tracks `master` and automatically deploys after CI checks pass.

TLS-verified HTTP checks pass for the frontend and its assets, health, inbox,
sample dossier, events, and completed SSE. Private report reads require the
judge key (401), and anonymous submissions are denied (402). The generated
judge key authenticates, including a 404 for an authenticated missing report.
The host has all three provider settings and a generated `MIMI_JUDGE_KEY`.

After fixing a query-guard false positive, runtime commit `f3257fa` completed
hosted report `a846ce7353c7` for the bundled public `minimist@1.2.5` /
CVE-2021-44906 input. Five Tavily queries returned 17 advisory records, eight
Sandbox runs completed, and the verdict and maintainer reply were saved with
no error-stage events. The final dossier, recorded history, and terminal SSE
were retrieved with the judge key; the live dossier was denied without it.
The result was **Needs human**, with zero triggered hypotheses in one
configuration. This verifies integration, not vulnerability-reproduction
accuracy. Dossier and event exports are retained locally in
`artifacts/hosted-verification/after-fix/` because Render Free storage is
ephemeral. Local verification passes 201 backend tests and seven Chromium
checks; all three required CI jobs passed for the runtime fix.

The operator must add the exact live URL and the shared judge
credential to Devpost's private testing instructions. Do not commit the key or
put provider credentials in the browser. Judges need no paid account of their
own. Keep the service and credentials available through **December 15, 2026**.

The live walkthrough is:

1. Open the live URL, enter the judge access key, and choose **Unlock inbox**.
2. Submit a report about a public npm package and advisory.
3. Watch the timeline, open the evidence and reply draft, and download the
   dossier before leaving.

Use public samples: this shared key lets all holders read the same live
reports. Published pilot accuracy and execution-boundary limits still apply.
The bundled sample remains a fixture even when viewed through the live API.

### Private Devpost testing instructions

Copy the following into the private testing field and replace the key placeholder
with the value of `MIMI_JUDGE_KEY` from Render. Keep this credential out of the
public project description:

> Live app: https://mimi-judge.onrender.com
>
> Judge access key: [copy MIMI_JUDGE_KEY from Render]
>
> Enter the key and choose Unlock inbox. To run a public example, use package
> `minimist@1.2.5` and paste the
> [bundled public report](https://github.com/zalkabsi/Mimi/blob/master/backend/mimi/data/sample_report.md),
> then choose Run triage. Inspect the live timeline, evidence, coverage, verdict,
> and reply draft; choose Download dossier before leaving. The recorded smoke
> result was Needs human; live outputs can vary. The Free host may take about a
> minute to wake and does not retain live reports across restarts.

## Provider and hosting budget

**Verified October 19: Tavily is restored.** After the free allowance reached
1,000 / 1,000 credits and searches returned HTTP 432, the owner enabled $5 of
funded usage. The API now reports a **625-credit pay-as-you-go limit**. A direct
basic search returned HTTP 200. Mimi's actual `TavilyClient.search` then ran
four public-identifier queries for lodash / CVE-2021-23337, returned three
unique advisory records, and produced no error notes. These checks do not
claim a new vulnerability-reproduction accuracy result.

Mimi makes at most six basic Tavily searches per report. Each costs one credit;
pay-as-you-go costs $0.008 per credit. Therefore the Tavily portion is at most
**$0.048 per report** at that rate:

| Live reports | Maximum search credits | Tavily pay-as-you-go cost |
| --- | --- | --- |
| 20 | 120 | $0.96 |
| 50 | 300 | $2.40 |
| 100 | 600 | $4.80 |

A $5 Tavily budget covers roughly 100 report research stages at the current
maximum query count, with a small allowance for service checks. This estimates
the Tavily portion of a run; the provider account separately reports the
625-credit paid-usage limit. The replay, video, and automated test suite
consume zero Tavily credits. Tavily's free allowance
resets monthly; its pricing page states the reset is the first of each month.

Render's selected hosting compute plan is Free. Nebius inference and Sandbox
charges are separate. The current Sandbox cost telemetry is in raw units
whose dollar conversion has not been established; do not treat the app's raw
cost threshold as a USD spending limit. The owner funded Tavily; the assistant
made no billing changes.

See [Tavily pricing](https://www.tavily.com/pricing),
[search credit costs](https://docs.tavily.com/documentation/api-credits), and
[Render Free limitations](https://render.com/docs/free). The operator needs to
check Nebius credits and any expiry in the Token Factory account.

## Render launch and verification

Use the [existing service](https://dashboard.render.com/web/srv-dbb4beqjnfac73euoa10)
and its [environment settings](https://dashboard.render.com/web/srv-dbb4beqjnfac73euoa10/env);
do not create a duplicate. The workspace is `tea-dbatv7fbtjjs738jpdug`.
`NEBIUS_API_KEY`, the funded `TAVILY_API_KEY`, `NEBIUS_PROJECT_ID`, and the
generated `MIMI_JUDGE_KEY` are configured. After changing an environment value,
choose **Save, rebuild, and deploy**. Keep the judge key in Render and copy it
only into Devpost's private testing instructions.
Codex Network secrets are restricted to their provider domains and are not
portable deployment credentials.

For a separate installation, use the prepared
[Deploy to Render link](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fzalkabsi%2FMimi)
to launch this repository's `master` branch using its Blueprint. Confirm
`plan: free`, one instance, and
`/api/health` as the health check. Leave `maxShutdownDelaySeconds` unset:
Render rejects that setting on the Free plan. Render generates `MIMI_JUDGE_KEY`; enter
`NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`, and the funded `TAVILY_API_KEY` directly
in Render's secret settings. Values injected by a development proxy may be
placeholders and must not be assumed portable to another host.

Before marking live access ready, verify the deployed frontend, public sample,
private-report denial without the key, an authenticated Sandbox permission
check, and a complete public-package report including working Tavily research.
Record the resulting live URL, report ID, and any remaining limitations here.

Render Free services sleep after 15 idle minutes and can take about a minute
to wake. Their filesystem is ephemeral: saved live reports disappear on sleep,
restart, or redeployment. Download a completed dossier during the session.
The bundled replay survives because it is in the image. This Blueprint does
not create a Free Postgres database with a 30-day expiry or a paid disk.

Free services also have monthly host usage limits. A service can remain
configured through the judging period, but its actual availability still
depends on the host allowance, provider funding, and valid credentials.
