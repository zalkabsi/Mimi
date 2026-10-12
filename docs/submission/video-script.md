# Demo video

`scripts/video/record_demo.py` records the video from the real UI and a **real live run** (the public CVE-2021-44906 example on `minimist@1.2.5`); nothing is mocked. It writes `demo.mp4` (about 2:15, captions burned in), `demo.srt` and `narration.txt`. A finished cut is committed as `docs/submission/demo-video.mp4`.

Rules it follows (docs/00): text names only, no third-party logos, no music, narration that names Nebius Token Factory, Token Factory Sandboxes and the Nemotron models, footage of the project working, under 3:00.

The narration in the committed cut is a **placeholder text-to-speech voice** (`espeak-ng`). For the final upload, replace the audio with your own voice reading `narration.txt` (the SRT timings match the scenes), or keep the placeholder if you prefer. Re-run the script for a fresh cut; it needs the API on :8000 started with `MIMI_JUDGE_KEY=local-demo-key` and the UI on :5173.

| Scene | On screen | Narration idea |
|---|---|---|
| 1 | Inbox in demo mode | The problem; Mimi reproduces the claim in isolated Token Factory Sandboxes and never auto-closes |
| 2 | Load the public example, enter the key, run | Nemotron Nano extracts the claim; Tavily gets only package and version |
| 3 | Live stage timeline | Nemotron Ultra hypotheses; build once, fork per hypothesis, offline, parallel |
| 4 | Verdict | Fires on 1.2.5, not on 1.2.6: Confirmed |
| 5 | Hypotheses, runs, differential | Commands, outputs, network isolation; the tier is code, not opinion |
| 6 | Recorded fabricated report (labelled synthetic) | Contradicted with coverage; a crashed script is inconclusive, never a negative |
| 7 | Recorded case where the oracle fired on both versions | Mimi refuses to confirm and asks a human |
| 8 | Limits | npm only; results vary; 7/11 oracle fired in three passes, 2-3/11 confirmed; Apache-2.0 |

Every figure spoken is from `docs/eval-logs/`. YouTube upload and the public link are yours to do.
