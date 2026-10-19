"""Render original synthetic narration and timed captions for the demo.

Requires ffmpeg/ffprobe and docs/video/requirements.txt. Uses the configured
HTTPS proxy and extends CA trust with CODEX_PROXY_CERT when provided.
No report data or provider keys are used. The script sends scenes.json text
to Microsoft's Edge speech service.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import textwrap
from pathlib import Path

import edge_tts
import edge_tts.communicate

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "docs" / "video"
WORK = ROOT / "artifacts" / "narration"


def timestamp(milliseconds: float) -> str:
    total = round(milliseconds)
    seconds, ms = divmod(total, 1000)
    minutes, sec = divmod(seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02}:{minute:02}:{sec:02},{ms:03}"


def duration(path: Path) -> float:
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path),
    ])) * 1000


async def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    scenes = json.loads((VIDEO / "scenes.json").read_text(encoding="utf-8"))
    ca = os.environ.get("CODEX_PROXY_CERT")
    if ca:
        edge_tts.communicate._SSL_CTX.load_verify_locations(cafile=ca)
    captions: list[str] = []
    offset = 0.0
    audio_files: list[Path] = []
    for scene in scenes:
        raw = WORK / f"{scene['id']}.mp3"
        words = []
        speech = edge_tts.Communicate(
            scene["text"], voice="en-US-AriaNeural", rate="+0%",
            boundary="WordBoundary", proxy=os.environ.get("HTTPS_PROXY"),
        )
        with raw.open("wb") as media:
            async for chunk in speech.stream():
                if chunk["type"] == "audio":
                    media.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append(chunk)
        padded = WORK / f"{scene['id']}.wav"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
            "-af", "adelay=500,apad=pad_dur=0.7", "-ar", "48000", "-ac", "1", str(padded),
        ], check=True)
        scene["duration_ms"] = round(duration(padded))
        scene["start_ms"] = round(offset)
        audio_files.append(padded)
        # Keep cues short enough for two readable lines on a 720p video.
        for index in range(0, len(words), 10):
            group = words[index:index + 10]
            start = offset + 500 + group[0]["offset"] / 10_000
            end = offset + 500 + (group[-1]["offset"] + group[-1]["duration"]) / 10_000
            text = " ".join(word["text"] for word in group)
            captions.append(
                f"{len(captions) + 1}\n{timestamp(start)} --> {timestamp(end)}\n"
                + "\n".join(textwrap.wrap(text, width=49)) + "\n"
            )
        offset += scene["duration_ms"]
        print(f"{scene['id']}: {scene['duration_ms'] / 1000:.1f}s", flush=True)
    if offset >= 179_000:
        raise SystemExit("Narration exceeds the three-minute budget; shorten scenes.json")
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for audio in audio_files:
        args.extend(["-i", str(audio)])
    inputs = "".join(f"[{index}:a]" for index in range(len(audio_files)))
    args.extend([
        "-filter_complex", f"{inputs}concat=n={len(audio_files)}:v=0:a=1[a]",
        "-map", "[a]", "-b:a", "192k", str(WORK / "voiceover.mp3"),
    ])
    subprocess.run(args, check=True)
    (VIDEO / "captions.srt").write_text("\n".join(captions), encoding="utf-8")
    (VIDEO / "voiceover-script.txt").write_text(
        "Mimi demo — original script; synthetic narration (en-US-AriaNeural).\n\n"
        + "\n\n".join(scene["text"] for scene in scenes) + "\n", encoding="utf-8",
    )
    (WORK / "scene-timing.json").write_text(json.dumps(scenes, indent=2) + "\n", encoding="utf-8")
    print(f"Narration complete: {offset / 1000:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
