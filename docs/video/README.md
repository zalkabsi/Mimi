# Demo video

`mimi-demo.mp4` is a 720p screen recording of the current production replay,
with original synthetic narration and burned-in English captions. Its measured
duration is 2:38.32, below the hackathon's three-minute limit. It opens the
actual inbox and dossier, expands a hypothesis, and shows the reply draft.
The last two shots are the repository's architecture diagram and a clearly
labelled summary of the published exploratory pilot.

The narration identifies fixture data and discloses the weak pilot results,
Tavily usage limit, and unverified hostile-code containment. No fixture result
is presented as live analysis. There is no background music or third-party logo.
Narration uses the synthetic `en-US-AriaNeural` voice from Edge TTS.

- `scenes.json` is the narration and shot source.
- `voiceover-script.txt` is the generated narration text.
- `captions.srt` is timed to the generated speech and can also be uploaded to YouTube.
- Refreshed inbox, dossier, and evidence screenshots are in `../assets/`.
- `artifacts/submission/` receives the video, captions, screenshots, source ZIP,
  portable demo ZIP, submission copy, review, and SHA-256 manifest after packaging.

To regenerate from the repository root (ffmpeg and ffprobe must be installed):

```bash
python -m pip install -r docs/video/requirements.txt
python scripts/render_narration.py
cd frontend
npm ci
npx playwright install chromium ffmpeg
npm run build:demo
npm run capture:demo -- --video
cd ..
make submission
```

Narration generation sends only the public script to Microsoft's speech service.
It honors `HTTPS_PROXY` and adds `CODEX_PROXY_CERT` to CA trust when configured;
TLS verification stays enabled. Generated intermediate audio and raw recordings
stay in ignored `artifacts/` directories. For screenshots alone, run
`npm run capture:demo` after building. An existing system Chromium may be selected
with `PLAYWRIGHT_CHROMIUM_EXECUTABLE`.

The owner-approved submission video remains [Mimi](https://youtu.be/y4rlh4hlkcw).
Upstream commit `0dd530a` records that approval on 2026-10-18. This session did
not independently recheck its YouTube playback. The new local MP4 is an optional
updated cut. If using it instead, upload it as a **public YouTube video**, test
signed-out playback, and replace the link in Devpost. This task has not uploaded
the new cut to YouTube. The [readiness review](../readiness-review.md) lists the
remaining submission steps.
