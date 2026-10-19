"""Package the current source, portable replay and reviewable demo assets.

Run `make submission` from the repository root. No credentials or remote writes.
Only Git-visible files enter the source ZIP; ignored local data stays local.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "submission"


def main() -> None:
    dist = ROOT / "frontend" / "dist"
    manifest_path = dist / "demo-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("Build the replay first: cd frontend && npm run build:demo")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("mode") != "read-only-replay" or manifest.get("provider_calls") is not False:
        raise SystemExit("Refusing to package a build without the replay manifest")
    frontend_fixture = json.loads((ROOT / "frontend/src/mocks/dossier.json").read_text(encoding="utf-8"))
    backend_fixture = json.loads((ROOT / "backend/mimi/data/sample_dossier.json").read_text(encoding="utf-8"))
    if frontend_fixture != backend_fixture or manifest.get("fixture_report_id") != frontend_fixture["report_id"]:
        raise SystemExit("Replay fixtures and the build manifest must agree before packaging")
    OUTPUT.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(OUTPUT / "mimi-demo.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dist.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(dist))
        archive.write(ROOT / "LICENSE", "LICENSE")
        archive.writestr("START-HERE.txt", (
            "Mimi — read-only replay\n\n"
            "Extract this ZIP, then run: python3 -m http.server 8080\n"
            "Open http://localhost:8080 and choose Open sample dossier.\n"
            "No account, backend, credentials, credits or provider calls.\n"
            "All evidence and timings shown are labelled fixture data.\n"
            "Upload index.html and assets/ together to any static host.\n"
            "Use an HTTP server; opening index.html as file:// is unsupported.\n"
        ))

    try:
        files = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT, stderr=subprocess.DEVNULL,
        ).decode().split("\0")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Extracted source ZIPs do not contain .git. Reuse their explicit
        # source manifest rather than walking ignored local directories.
        source_manifest = ROOT / "source-files.json"
        if not source_manifest.is_file():
            raise SystemExit("Package from a Git checkout or an extracted Mimi source ZIP")
        files = json.loads(source_manifest.read_text(encoding="utf-8"))
    included: list[str] = []
    with zipfile.ZipFile(OUTPUT / "mimi-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(files)):
            if not name:
                continue
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise SystemExit("Source manifest paths must stay inside the project")
            path = ROOT / name
            # Never follow links or include local secret material, even if an
            # operator accidentally added it to Git's index.
            if path.is_symlink() or not path.is_file():
                continue
            if (path.name.startswith(".env") and path.name != ".env.example") or path.suffix in {".key", ".pem", ".db", ".sqlite"}:
                raise SystemExit(f"Refusing to archive sensitive file: {name}")
            archive.write(path, Path("Mimi") / name)
            included.append(name)
        archive.writestr("Mimi/source-files.json", json.dumps(included, indent=2) + "\n")

    for name in ("mimi-demo.mp4", "captions.srt", "voiceover-script.txt", "README.md"):
        path = ROOT / "docs" / "video" / name
        if path.is_file():
            (OUTPUT / ("VIDEO-README.md" if name == "README.md" else name)).write_bytes(path.read_bytes())
    for name in ("submission-kit.md", "readiness-review.md", "branch-protection.md", "judge-access.md"):
        path = ROOT / "docs" / name
        if path.is_file():
            (OUTPUT / name).write_bytes(path.read_bytes())
    (OUTPUT / "master-ruleset.json").write_bytes((ROOT / ".github/rulesets/master.json").read_bytes())
    for path in (ROOT / "docs" / "assets").glob("demo-*.png"):
        (OUTPUT / path.name).write_bytes(path.read_bytes())
    deliverables = {
        "mimi-demo.zip", "mimi-source.zip", "mimi-demo.mp4", "VIDEO-README.md",
        "captions.srt", "voiceover-script.txt", "submission-kit.md", "readiness-review.md",
        "branch-protection.md", "master-ruleset.json",
        "judge-access.md",
        "demo-inbox.png", "demo-dossier.png", "demo-evidence.png",
    }
    hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(OUTPUT.iterdir()) if path.is_file() and path.name in deliverables
    }
    (OUTPUT / "sha256.json").write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(OUTPUT / "mimi-submission.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name in [*hashes, "sha256.json"]:
            archive.write(OUTPUT / name, name)
    print(f"Submission files: {OUTPUT}")
    for path in sorted(OUTPUT.iterdir()):
        print(f"  {path.name} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
