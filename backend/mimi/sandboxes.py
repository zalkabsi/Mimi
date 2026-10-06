"""Execution layer: untrusted PoC code runs only inside Token Factory Sandboxes.

- ``SandboxExecutor``: real microVMs via ``contree-sdk``. Build once
  (``disposable=False`` keeps the result image UUID), then each hypothesis runs
  as an independent fork from that UUID. Network is on for install only; the
  PoC phase is wrapped so it has no network when ``unshare -n`` works (the
  week-1 spike verifies this).
- ``FixtureExecutor``: replay of recorded runs for unit tests and the
  recorded-LLM golden suite (no credits, deterministic). Fixtures are never
  presented as real results — dossiers record which executor produced them.

The app host never executes PoC code. No secrets are ever passed into a
sandbox environment or image (docs/02-architecture.md security model).
"""

from __future__ import annotations

import json
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

from .schemas import RunConfig, RunRecord


class ExecutorError(RuntimeError):
    pass


class Executor(Protocol):
    """What the pipeline needs from an execution backend."""

    name: str

    async def build(self, config: RunConfig, *, package_spec: str, build_timeout_s: int) -> "BuildResult":
        ...

    async def run_poc(
        self,
        build: "BuildResult",
        config: RunConfig,
        *,
        poc_code: str,
        hypothesis_id: str,
        timeout_s: int,
        offline: bool = True,
        phase: str = "poc",
    ) -> RunRecord:
        ...

    async def close(self) -> None:
        ...


@dataclass
class BuildResult:
    image_id: str  # fork point for hypothesis runs
    log: str = ""
    ok: bool = True
    elapsed_ms: float = 0.0
    cost: Optional[float] = None
    cost_units: Optional[str] = None
    detail: str = ""


# ---------------------------------------------------------------------------
# The fixed command set (prompt-injection rule): commands come from RunConfig
# fields with allowlisted shapes, never free-form strings parsed from a report.
# ---------------------------------------------------------------------------
_OFFLINE_WRAP = (
    "if command -v unshare >/dev/null 2>&1; then unshare -n -- %s; else %s; fi"
)


def _cap(text: str, cap_bytes: int) -> tuple[str, bool]:
    raw = text or ""
    if len(raw.encode("utf-8", "ignore")) <= cap_bytes:
        return raw, False
    return raw.encode("utf-8", "ignore")[:cap_bytes].decode("utf-8", "ignore") + "\n…[truncated]", True


class SandboxExecutor:
    """Real execution on Token Factory Sandboxes through contree-sdk."""

    name = "sandbox"

    def __init__(self, settings):
        self.settings = settings
        self._client = None  # lazy: contree client
        self._base_image = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        self.settings.require_sandboxes()
        try:
            from contree import ContreeAsyncClient  # type: ignore
        except ImportError:
            try:  # older package layout
                from contree_sdk import ContreeAsyncClient  # type: ignore
            except ImportError as e:
                raise ExecutorError(
                    "contree-sdk is not installed (pip install contree-sdk)"
                ) from e
        # Contree accepts an API key + base URL directly; project id travels as
        # the Project header (the SDK profile loader can also supply it).
        self._client = ContreeAsyncClient(
            api_key=self.settings.nebius_api_key,
            base_url=self.settings.sandboxes_base_url,
            project_id=self.settings.nebius_project_id,
        )
        return self._client

    async def build(self, config: RunConfig, *, package_spec: str, build_timeout_s: int) -> BuildResult:
        client = self._ensure_client()
        t0 = time.monotonic()
        spec = config.package_spec or package_spec
        setup = " && ".join(config.setup_commands) if config.setup_commands else "true"
        cmd = (
            f"set -e; mkdir -p /work && cd /work && "
            f"npm init -y >/dev/null 2>&1 || true; "
            f"npm install {shlex.quote(spec)} --no-audit --no-fund; "
            f"{setup}"
        )
        try:
            image = await client.images.use(f"node:{config.node_version}")
            result = await image.run(shell=cmd, timeout=build_timeout_s, disposable=False)
        except Exception as e:  # SDK raises its own error types
            return BuildResult(
                image_id="",
                ok=False,
                detail=f"build failed: {e}",
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )
        cost = getattr(getattr(result, "resources", None), "cost", None)
        return BuildResult(
            image_id=getattr(result, "uuid", "") or "",
            log=str(getattr(result, "stdout", "") or "") + str(getattr(result, "stderr", "") or ""),
            ok=bool(getattr(result, "uuid", "")),
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            cost=cost,
            cost_units="contree-cost-units" if cost is not None else None,
            detail="built base image",
        )

    async def run_poc(
        self,
        build: BuildResult,
        config: RunConfig,
        *,
        poc_code: str,
        hypothesis_id: str,
        timeout_s: int,
        offline: bool = True,
        phase: str = "poc",
    ) -> RunRecord:
        client = self._ensure_client()
        t0 = time.monotonic()
        try:
            image = await client.images.use(build.image_id)  # fork point
            # Stage the PoC file, then run it under the optional network-less wrap.
            write = await image.run(
                shell=f"cat > /work/{shlex.quote(config.poc_file_name)}",
                stdin=poc_code,
                timeout=30,
            )
            runner = shlex.quote(f"cd /work && {config.poc_command}")
            wrapped = _OFFLINE_WRAP % (runner, runner) if offline else runner
            result = await write.run(shell=wrapped, timeout=timeout_s, env=dict(config.env) or None)
        except Exception as e:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase="poc",
                command=config.poc_command,
                error=f"run failed: {e}",
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )
        stdout, trunc1 = _cap(str(getattr(result, "stdout", "") or ""), self.settings.output_cap_bytes)
        stderr, trunc2 = _cap(str(getattr(result, "stderr", "") or ""), self.settings.output_cap_bytes)
        cost = getattr(getattr(result, "resources", None), "cost", None)
        return RunRecord(
            hypothesis_id=hypothesis_id,
            phase=phase,
            command=config.poc_command,
            exit_code=getattr(result, "exit_code", None),
            signal=getattr(result, "signal", None),
            stdout=stdout,
            stderr=stderr,
            elapsed_ms=getattr(result, "elapsed_time", None) or (time.monotonic() - t0) * 1000.0,
            cost=cost,
            cost_units="contree-cost-units" if cost is not None else None,
            sandbox_image_id=getattr(result, "uuid", None),
            sandbox_run_id=getattr(result, "id", None) or getattr(result, "uuid", None),
            network_isolated=offline,
            truncated=trunc1 or trunc2,
        )

    async def close(self) -> None:
        closer = getattr(self._client, "aclose", None) or getattr(self._client, "close", None)
        if callable(closer):
            try:
                r = closer()
                if hasattr(r, "__await__"):
                    await r
            except Exception:
                pass
        self._client = None


# ---------------------------------------------------------------------------
# Fixture replay — deterministic, no network, no credits. For tests and CI.
# ---------------------------------------------------------------------------

@dataclass
class FixtureExecutor:
    """Replays recorded runs from a JSON file of the shape:

    ``{"build": {...BuildResult fields...}, "runs": {"h1": {...RunRecord fields...}}}``
    """

    fixtures_path: str
    name: str = "fixture"
    _data: dict = field(default_factory=dict)

    def _load(self) -> dict:
        if not self._data:
            self._data = json.loads(Path(self.fixtures_path).read_text(encoding="utf-8"))
        return self._data

    async def build(self, config: RunConfig, *, package_spec: str, build_timeout_s: int) -> BuildResult:
        data = self._load().get("build", {})
        return BuildResult(
            image_id=data.get("image_id", "fixture-image"),
            log=data.get("log", ""),
            ok=data.get("ok", True),
            elapsed_ms=data.get("elapsed_ms", 0.0),
            detail=data.get("detail", "fixture build"),
        )

    async def run_poc(
        self,
        build: BuildResult,
        config: RunConfig,
        *,
        poc_code: str,
        hypothesis_id: str,
        timeout_s: int,
        offline: bool = True,
        phase: str = "poc",
    ) -> RunRecord:
        data_map = self._load().get("fixed_runs" if phase == "fixed" else "runs", {})
        data = data_map.get(hypothesis_id)
        if data is None and phase == "fixed":
            # A fixed-phase miss means the fixture asserts the bug does NOT
            # reproduce there: run with empty output so the oracle does not fire.
            data = {"command": config.poc_command, "exit_code": 1, "stdout": "", "stderr": "", "elapsed_ms": 10}
        if data is None:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase="poc",
                command=config.poc_command,
                error=f"no fixture for hypothesis {hypothesis_id}",
            )
        return RunRecord.model_validate({**data, "hypothesis_id": hypothesis_id, "phase": phase})

    async def close(self) -> None:
        return None


async def whoami(settings) -> dict:
    """Raw HTTP permission probe (status and permissions only — never keys).

    ``GET {base}/whoami`` and ``{base}/v1/whoami`` are both tried; the 2026-09-30
    check used ``/v1/whoami`` and returned every permission as ``false`` on a
    valid key.
    """
    import httpx

    settings.require_sandboxes()
    headers = {
        "Authorization": f"Bearer {settings.nebius_api_key}",
        "Project": settings.nebius_project_id or "",
    }
    base = settings.sandboxes_base_url.rstrip("/")
    out: dict = {"base": base}
    async with httpx.AsyncClient(timeout=20.0) as client:
        for path in ("/whoami", "/v1/whoami"):
            try:
                r = await client.get(base + path, headers=headers)
            except httpx.HTTPError as e:
                out[path] = {"error": str(e)}
                continue
            if r.status_code == 200:
                data = r.json() if "json" in r.headers.get("content-type", "") else {}
                perms = data.get("permissions") or {
                    k: v for k, v in data.items() if isinstance(v, bool)
                }
                out["ok"] = True
                out["path"] = path
                out["permissions"] = perms
                # token_expiration is a rolling 5-minute value — record but label it.
                if "token_expiration" in data:
                    out["token_expiration_is_rolling"] = True
                return out
            out[path] = {"status": r.status_code, "body": r.text[:200]}
    return out
