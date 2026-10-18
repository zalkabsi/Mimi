// Capture the actual production replay. Requires `npm run build:demo`, a
// Playwright Chromium installation, and ffmpeg/ffprobe for video export.
import { chromium } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";
import { spawn, execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../../", import.meta.url));
const assets = path.join(root, "docs/assets");
const raw = path.join(root, "artifacts/demo-raw");
const narration = path.join(root, "artifacts/narration");
const videoMode = process.argv.includes("--video");
await mkdir(raw, { recursive: true });
const server = spawn(process.execPath, ["node_modules/vite/bin/vite.js", "preview", "--host", "127.0.0.1", "--port", "4173", "--strictPort"], {
  cwd: path.join(root, "frontend"), stdio: "ignore",
});
let browser;
try {
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { ready = (await fetch("http://127.0.0.1:4173")).ok; } catch { /* wait for preview */ }
    if (ready) break;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (!ready) throw new Error("Production preview did not start");
  browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 }, reducedMotion: "reduce",
    ...(videoMode ? { recordVideo: { dir: raw, size: { width: 1280, height: 720 } } } : {}),
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("http://127.0.0.1:4173");
  await page.getByRole("link", { name: "Open sample dossier" }).waitFor();
  await page.screenshot({ path: path.join(assets, "demo-inbox.png"), fullPage: true });
  if (!videoMode) {
    await page.getByRole("link", { name: "Open sample dossier" }).click();
    await page.getByRole("heading", { name: "Verdict", exact: true }).waitFor();
    await page.getByRole("heading", { name: "Verdict", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(assets, "demo-dossier.png") });
    await page.getByRole("heading", { name: "Hypotheses", exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(assets, "demo-evidence.png") });
  } else {
    const scenes = JSON.parse(await readFile(path.join(narration, "scene-timing.json"), "utf8"));
    const began = performance.now();
    for (const scene of scenes) {
      console.log(`Recording: ${scene.id}`);
      if (scene.id === "timeline") {
        await page.getByRole("link", { name: "Open sample dossier" }).click();
        await page.getByRole("heading", { name: "Verdict", exact: true }).waitFor();
      } else if (scene.id === "verdict") {
        await page.getByRole("heading", { name: "Verdict", exact: true }).scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(assets, "demo-dossier.png") });
      } else if (scene.id === "evidence") {
        await page.getByRole("heading", { name: "Hypotheses", exact: true }).scrollIntoViewIfNeeded();
        await page.screenshot({ path: path.join(assets, "demo-evidence.png") });
        // Show actual expansion of generated code and recorded run output.
        const toggle = page.getByRole("button", { name: /harness code/ }).first();
        await toggle.click();
      } else if (scene.id === "reply") {
        await page.getByRole("heading", { name: "Reply draft", exact: true }).scrollIntoViewIfNeeded();
      } else if (scene.id === "architecture") {
        const svg = await readFile(path.join(assets, "architecture.svg"), "utf8");
        await page.setContent(`<html><head><title>Mimi architecture</title><style>body{margin:0;background:#020617;display:grid;place-items:center;height:100vh}svg{width:100%;max-height:650px}</style></head><body>${svg}</body></html>`);
      } else if (scene.id === "limits") {
        await page.setContent(`<html><head><title>Mimi pilot results</title><style>body{margin:0;padding:80px;box-sizing:border-box;background:#020617;color:#cbd5e1;font:24px/1.6 system-ui;height:100vh}h1{color:#f1f5f9;font-size:44px;margin:0 0 16px}.eyebrow{color:#7dd3fc;font:16px monospace}strong{color:#fbbf24}.footer{font:18px monospace;color:#94a3b8;margin-top:32px}</style></head><body><p class="eyebrow">MIMI · EXPLORATORY LIVE PILOT · OCTOBER 18, 2026</p><h1>Evidence first. Human decision.</h1><p>11 real cases: <strong>0 fixed-version confirmations</strong>.<br>5 fabricated reports: <strong>0 Contradicted</strong>; 1 false Likely.</p><p>Tavily usage limit blocks advisory research.<br>Hostile-code containment remains unverified.</p><p class="footer">Replay uses labelled fixture data. Mimi never auto-closes a report.<br>Full results: docs/evaluation-results.md</p></body></html>`);
      }
      await page.waitForTimeout(Math.max(0, began + scene.start_ms + scene.duration_ms - performance.now()));
    }
    const video = page.video();
    await context.close();
    const recording = await video.path();
    const subtitles = path.join(root, "docs/video/captions.srt");
    const output = path.join(root, "docs/video/mimi-demo.mp4");
    const duration = scenes.reduce((total, scene) => total + scene.duration_ms, 0) / 1000;
    execFileSync("ffmpeg", [
      "-hide_banner", "-loglevel", "error", "-y", "-i", recording, "-i", path.join(narration, "voiceover.mp3"),
      "-vf", `subtitles='${subtitles}':force_style='FontName=DejaVu Sans,FontSize=20,BorderStyle=3,Outline=1,MarginV=18'`,
      "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "25",
      "-c:a", "aac", "-b:a", "160k", "-t", duration.toFixed(3), "-shortest", "-movflags", "+faststart", output,
    ], { stdio: "inherit" });
    const metadata = JSON.parse(execFileSync("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", output], { encoding: "utf8" }));
    if (Number(metadata.format.duration) >= 180) throw new Error("Demo exceeds three minutes");
    await import("node:fs/promises").then(({ writeFile }) => writeFile(path.join(raw, "export-metadata.json"), JSON.stringify(metadata, null, 2)));
    console.log(`Exported ${output} (${metadata.format.duration}s)`);
  }
  if (errors.length) throw new Error(errors.join("\n"));
  await browser.close();
  console.log("Capture complete; no browser errors");
} finally {
  await browser?.close();
  server.kill();
}
