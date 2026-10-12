"""Record the Mimi demo video from the real UI and a real live run.

Needs: Playwright + Chromium, ffmpeg, espeak-ng (placeholder narration; replace
the audio with a human voice for the final cut), the API on :8000 started with
MIMI_JUDGE_KEY=local-demo-key and the UI dev server on :5173.

    python scripts/video/record_demo.py OUT_DIR

Writes OUT_DIR/demo.mp4 (captions burned in), demo.srt and narration.txt.
Nothing is mocked: scene 2-4 submit the public CVE-2021-44906 example live.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import wave
from pathlib import Path

from playwright.async_api import async_playwright

UI = "http://localhost:5173/"
KEY = "local-demo-key"

SCENES = [
    ("inbox",
     "Open-source maintainers get vulnerability reports they cannot cheaply verify. "
     "Mimi reproduces the claim in isolated Nebius Token Factory Sandboxes, at the exact affected version, "
     "and returns a verdict with receipts. It never auto-closes a report."),
    ("submit",
     "I load a public example: minimist 1.2.5, CVE 2021 44906. Nemotron Nano extracts the claim. "
     "Tavily looks up public advisories using only the package name and version, never the report text."),
    ("live",
     "Nemotron Ultra writes up to eight hypotheses, each with a test script and a pass or fail rule fixed in advance. "
     "The environment is built once in a Token Factory Sandbox, and every hypothesis runs as its own fork, offline, in parallel."),
    ("verdict",
     "Hypotheses that fire are re-run on the fixed version. This one fires on 1.2.5 and not on 1.2.6, "
     "so the tier is Confirmed, with every command and output attached."),
    ("evidence",
     "Each run shows the exact command, its output, and whether the network was isolated. "
     "The tier is assigned by code from the oracle results, not by a model's opinion."),
    ("negative",
     "When a report is fabricated, Mimi says how hard it tried. This invented chalk bug: six hypotheses tested, none triggered. "
     "That is a negative result with coverage, not a closed report. A script that crashes is recorded as inconclusive, never as a negative."),
    ("human",
     "And when an oracle fires on both the affected and the fixed version, Mimi refuses to confirm and asks a human to look."),
    ("limits",
     "Mimi covers npm only, and results vary between runs. In our development runs, three passes over eleven real vulnerabilities "
     "fired an oracle on seven each time, and confirmed two or three against the fixed version. "
     "It is open source under Apache 2.0, built on Nebius Token Factory, Sandboxes and Nemotron, with Tavily for research."),
]


def tts(text: str, path: Path) -> float:
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "158", "-p", "45", "-w", str(path), text], check=True)
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


async def smooth_to(page, selector_text: str, block: str = "start") -> None:
    loc = page.get_by_text(selector_text, exact=False).first
    await loc.scroll_into_view_if_needed()
    await page.evaluate(f"window.scrollBy(0, -80)")


async def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    durs, wavs = [], []
    for i, (_, text) in enumerate(SCENES):
        p = out / f"n{i}.wav"
        durs.append(tts(text, p))
        wavs.append(p)

    starts: list[float] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(out / "raw"),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await ctx.new_page()
        t0 = time.monotonic()

        async def scene(i: int, action) -> None:
            starts.append(time.monotonic() - t0)
            t = time.monotonic()
            await action()
            remain = durs[i] + 0.8 - (time.monotonic() - t)
            if remain > 0:
                await page.wait_for_timeout(int(remain * 1000))

        async def s_inbox():
            await page.goto(UI)
            await page.wait_for_timeout(800)

        async def s_submit():
            await page.get_by_text("load public example").click()
            await page.wait_for_timeout(600)
            await page.get_by_placeholder("judge credential").fill(KEY)
            await page.wait_for_timeout(600)
            await page.get_by_role("button", name="Run triage").click()
            await page.wait_for_url("**/reports/**", timeout=20000)

        async def s_live():
            # Real run, real time. Follow the timeline to the newest event, then wait for the
            # API to report the run complete AND for the UI to show the verdict.
            rid = page.url.rstrip("/").split("/")[-1]
            for _ in range(300):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                rows = await (await page.request.get("http://localhost:8000/api/reports")).json()
                row = next((r for r in rows if r["id"] == rid), None)
                if row and row["status"] == "complete":
                    break
                await page.wait_for_timeout(2000)
            await page.wait_for_selector("text=tier assigned by the harness", timeout=30000)
            await page.wait_for_timeout(1500)

        async def s_verdict():
            await page.evaluate("window.scrollTo(0,0)")
            await page.wait_for_timeout(1200)

        async def s_evidence():
            for text in ("Hypotheses", "Runs", "Differential"):
                try:
                    await smooth_to(page, text)
                except Exception:
                    pass
                await page.wait_for_timeout(2200)

        async def open_report(substr: str):
            await page.goto(UI)
            await page.get_by_text(substr).first.click()
            await page.wait_for_selector("text=Verdict", timeout=10000)

        async def s_negative():
            await open_report("e2-synth-chalk")
            await page.wait_for_timeout(2500)
            await smooth_to(page, "Runs")

        async def s_human():
            await open_report("e1-underscore")
            await page.wait_for_timeout(2500)
            await smooth_to(page, "Differential")

        async def s_limits():
            await page.goto(UI)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        actions = [s_inbox, s_submit, s_live, s_verdict, s_evidence, s_negative, s_human, s_limits]
        # scenes 2 and 3 are one continuous flow: the narration for "live" starts as the run starts.
        for i, act in enumerate(actions):
            await scene(i, act)
        total = time.monotonic() - t0
        await ctx.close()
        await browser.close()

    raw = next((out / "raw").glob("*.webm"))

    # The live pipeline run takes about a minute in real time. Keep it real, but
    # speed that scene up if it would push the video past the 3:00 limit, and say
    # so on screen. Everything else plays at normal speed.
    ends = starts[1:] + [total]
    factors = []
    for (name, _), s0, e0, d in zip(SCENES, starts, ends, durs):
        length = e0 - s0
        target = d + 6.0
        factors.append(max(1.0, length / target) if name == "live" else 1.0)
    new_len = [(e0 - s0) / f for s0, e0, f in zip(starts, ends, factors)]
    new_starts = [sum(new_len[:i]) for i in range(len(new_len))]
    new_total = sum(new_len)

    vparts, vlabels = [], []
    for i, (s0, e0, f) in enumerate(zip(starts, ends, factors)):
        chain = f"[0:v]trim=start={s0:.3f}:end={e0:.3f},setpts=(PTS-STARTPTS)/{f:.4f}"
        if f > 1.01:
            chain += (
                f",drawtext=text='live run, sped up {f:.0f}x':x=w-tw-24:y=24:fontsize=22:"
                "fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=8"
            )
        vparts.append(chain + f"[v{i}]")
        vlabels.append(f"[v{i}]")
    vparts.append("".join(vlabels) + f"concat=n={len(vlabels)}:v=1:a=0[vc]")

    inputs, afilters, alabels = [], [], []
    for i, (w, st) in enumerate(zip(wavs, new_starts)):
        inputs += ["-i", str(w)]
        afilters.append(f"[{i + 1}:a]adelay={int(st * 1000)}|{int(st * 1000)}[a{i}]")
        alabels.append(f"[a{i}]")
    afilters.append("".join(alabels) + f"amix=inputs={len(wavs)}:normalize=0[aout]")

    def ts(sec: float) -> str:
        h, rem = divmod(sec, 3600)
        m, s_ = divmod(rem, 60)
        return f"{int(h):02}:{int(m):02}:{s_:06.3f}".replace(".", ",")

    srt, n = [], 1
    for (name, text), st, d in zip(SCENES, new_starts, durs):
        words = text.split()
        chunk = 14
        parts = [" ".join(words[j:j + chunk]) for j in range(0, len(words), chunk)]
        per = d / max(1, len(parts))
        for k, part in enumerate(parts):
            srt.append(f"{n}\n{ts(st + k * per)} --> {ts(st + (k + 1) * per)}\n{part}\n")
            n += 1
    (out / "demo.srt").write_text("\n".join(srt), encoding="utf-8")
    (out / "narration.txt").write_text("\n\n".join(t for _, t in SCENES), encoding="utf-8")

    style = "FontName=Inter,FontSize=11,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=24"
    graph = ";".join(vparts + afilters) + f";[vc]subtitles={out / 'demo.srt'}:force_style='{style}'[v]"
    cmd = [
        "ffmpeg", "-y", "-i", str(raw), *inputs,
        "-filter_complex", graph,
        "-map", "[v]", "-map", "[aout]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
        "-c:a", "aac", "-b:a", "128k", "-t", f"{new_total:.1f}", str(out / "demo.mp4"),
    ]
    subprocess.run(cmd, check=True)
    print(f"done: {out / 'demo.mp4'}  length {new_total:.1f}s (live scene speed x{max(factors):.1f})")


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))
