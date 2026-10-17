"""Execution layer: untrusted PoC code runs only inside Token Factory Sandboxes.

- ``SandboxExecutor``: real microVMs via ``contree-sdk``. Build once
  (``disposable=False`` keeps the result image UUID), then each hypothesis runs
  as an independent fork from that UUID. Network is on for install only; the
  PoC phase is refused unless a user and network namespace can be created.
- ``FixtureExecutor``: replay of recorded runs for unit tests and the
  recorded-LLM golden suite (no credits, deterministic). Fixtures are never
  presented as real results — dossiers record which executor produced them.

The app host never executes PoC code. No secrets are ever passed into a
sandbox environment or image (docs/02-architecture.md security model).
"""

from __future__ import annotations

import base64
import json
import re
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional, Protocol

from .probe import (
    SHIM_FILE,
    STATE_FILE,
    PROBE_JS,
    SHIM_JS,
    probe_command,
    shim_node_options,
)
from .schemas import RunConfig, RunRecord, validate_package_spec

_Phase = Literal["build", "poc", "fixed", "other"]
_PHASES: dict[str, _Phase] = {"build": "build", "poc": "poc", "fixed": "fixed", "other": "other"}

# Printed by the build shell only after every step succeeded under `set -e`.
# Its presence in the log is the build's own claim that the install and the
# package-manifest check both passed — the image UUID proves nothing alone.
BUILD_OK_TOKEN = "__MIMI_BUILD_OK__"
_STAGE_OK_TOKEN = "__MIMI_STAGE_OK__"


def _norm_phase(phase: str) -> _Phase:
    return _PHASES.get(phase, "poc")


def _stage_file_command(destination: str) -> str:
    """Atomically replace a workspace file without following a planted link."""
    return (
        "set -e; tmp=$(mktemp /work/.mimi-stage.XXXXXX); "
        "cat > \"$tmp\"; chmod 0644 \"$tmp\"; "
        f"mv -T -- \"$tmp\" {shlex.quote(destination)}; "
        f"echo {_STAGE_OK_TOKEN}"
    )


def _require_staged(result, what: str) -> None:
    """Fail closed if a source file could not be atomically staged."""
    exit_code = getattr(result, "exit_code", None)
    stdout = str(getattr(result, "stdout", "") or "")
    if exit_code not in (0, None) or _STAGE_OK_TOKEN not in stdout:
        raise ExecutorError(f"could not stage {what} into the sandbox")


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
        probe_env: Optional[dict[str, str]] = None,
        probe_snippet: Optional[str] = None,
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

# Shell metacharacters that must never appear in a command we did not write.
_FORBIDDEN_CHARS = set("\n\r;&|`$(){}<>*?~\\\"'")

# Commands the model is allowed to propose. Everything else is refused at
# validation time — this is the prompt-injection boundary (docs/02-architecture).
_ALLOWED_POC_COMMANDS = {
    "node poc.js",
    "node poc.mjs",
    "node index.js",
    "node exploit.js",
    "node test.js",
    "node --experimental-vm-modules poc.js",
}
_ALLOWED_SETUP_COMMANDS = {
    "mkdir -p out",
    "mkdir -p tmp",
    "cp -r node_modules/orig node_modules/pkg",
    "npm rebuild",
    "chmod +x poc.js",
}
_ALLOWED_INSTALL_COMMANDS = {
    "npm install --no-audit --no-fund",
    "npm install --no-audit --no-fund --ignore-scripts",
    "npm ci --no-audit --no-fund",
}
# node_version is a docker tag suffix: digits and dots only.
_NODE_VERSION_RE = re.compile(r"^\d{1,2}(\.\d{1,2}){0,2}$")
# The PoC file is a bare script name; .mjs is allowed because one allowlisted
# poc_command is `node poc.mjs`.
_POC_FILE_RE = re.compile(r"^[A-Za-z0-9._-]+\.(?:js|mjs)$")
_MARKER_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
# Env keys the executor owns. A hypothesis that sets these could disable the
# observation shim or redirect its verdict file.
_EXECUTOR_ENV_KEYS = {
    "NODE_OPTIONS", "NODE_PATH", "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH",
    "LD_AUDIT", "BASH_ENV", "ENV", "IFS", "SHELLOPTS", "BASHOPTS",
    "MIMI_STATE_PATH", "MIMI_MARKER_PATH", "MIMI_TRAVERSAL_PATH",
    "MIMI_PROBE_NETWORK", "MIMI_PROBE_EGRESS", "MIMI_CUSTOM_PROBE_B64",
}


class ConfigRejected(ValueError):
    """A RunConfig field did not match the fixed command set."""


@dataclass
class RunBudget:
    """Shared run allowance and best-effort cost threshold for one report.

    ``max_runs_per_report`` bounds *executions*, not hypotheses: the
    fixed-version differential re-runs every hypothesis that fired and must
    draw from the same allowance. Left unshared, a report with many firing
    hypotheses could execute up to twice the configured number of untrusted
    runs while still claiming the cap held.

    ``cost_cap`` is ``per_report_cost_cap`` in the same units the sandbox
    returns (contree cost units, not USD — the two are never conflated).
    ``charge()`` is called after measured builds and runs; once measured spend
    reaches the threshold, no further work is reserved. The threshold is
    best-effort: an in-flight build/run can cross it, and missing cost data
    cannot be charged. The dossier states when cost was unmeasured rather than
    implying a hard dollar limit.
    """

    remaining: int
    cost_cap: Optional[float] = None
    spent: float = 0.0

    def can_continue(self) -> bool:
        """Whether another build or run may be started under measured limits."""
        return self.remaining > 0 and (
            self.cost_cap is None or self.spent < self.cost_cap
        )

    def take(self) -> bool:
        """Reserve one PoC execution. False once a cap is reached."""
        if not self.can_continue():
            return False
        self.remaining -= 1
        return True

    def charge(self, cost: Optional[float]) -> None:
        """Record measured build/run cost against the best-effort threshold."""
        if cost is not None:
            self.spent += float(cost)


def _poc_command_script(poc_command: str) -> str:
    """The script name an allowlisted ``poc_command`` actually executes."""
    parts = (poc_command or "").split()
    return parts[-1] if parts else ""


def validate_run_config(config: "RunConfig", *, where: str = "run_config") -> None:
    """Reject anything outside the fixed command set. Raises ConfigRejected."""
    if config.offline is not True:
        raise ConfigRejected(f"{where}.offline must be true; online PoC execution is disabled")
    if not _NODE_VERSION_RE.match(config.node_version or ""):
        raise ConfigRejected(
            f"{where}.node_version must be a plain version like '20' (got {config.node_version!r})"
        )
    if config.poc_command not in _ALLOWED_POC_COMMANDS:
        raise ConfigRejected(
            f"{where}.poc_command is not in the fixed command set: {config.poc_command!r}"
        )
    if config.install_command not in _ALLOWED_INSTALL_COMMANDS:
        raise ConfigRejected(
            f"{where}.install_command is not in the fixed command set: {config.install_command!r}"
        )
    if config.package_spec is not None:
        _reject_meta(f"{where}.package_spec", config.package_spec)
    _reject_meta(f"{where}.poc_file_name", config.poc_file_name)
    if not _POC_FILE_RE.match(config.poc_file_name or ""):
        raise ConfigRejected(f"{where}.poc_file_name must be a simple .js/.mjs name")
    # The staged PoC file and the command that runs it must name the same
    # script. A mismatch is a dead run (file not found) that would otherwise be
    # graded as a clean negative — a fabricated "did not trigger".
    script = _poc_command_script(config.poc_command)
    if script != config.poc_file_name:
        raise ConfigRejected(
            f"{where}.poc_command {config.poc_command!r} runs {script!r} but "
            f"poc_file_name is {config.poc_file_name!r}"
        )
    for i, cmd in enumerate(config.setup_commands):
        if cmd not in _ALLOWED_SETUP_COMMANDS:
            raise ConfigRejected(
                f"{where}.setup_commands[{i}] is not in the fixed allowlist: {cmd!r}"
            )
    for k, v in config.env.items():
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", k):
            raise ConfigRejected(f"{where}.env key {k!r} is not a plain identifier")
        if k in _EXECUTOR_ENV_KEYS or k.startswith("MIMI_"):
            raise ConfigRejected(f"{where}.env[{k}] is reserved for the executor")
        _reject_meta(f"{where}.env[{k}]", v)


def _reject_meta(where: str, value: str) -> None:
    bad = _FORBIDDEN_CHARS.intersection(value or "")
    if bad:
        raise ConfigRejected(
            f"{where} contains shell metacharacters {sorted(bad)!r}: {value!r}"
        )


def _cap(text: str, cap_bytes: int) -> tuple[str, bool]:
    raw = text or ""
    if len(raw.encode("utf-8", "ignore")) <= cap_bytes:
        return raw, False
    return raw.encode("utf-8", "ignore")[:cap_bytes].decode("utf-8", "ignore") + "\n…[truncated]", True


def _first_net_marker(stdout: str) -> Optional[tuple[str, bool]]:
    """The first ``__MIMI_NET__:`` marker in the stream, if any.

    The wrapper prints its marker *before* the PoC starts, so the first
    occurrence is the wrapper's. Later occurrences are PoC output and cannot
    be trusted — a PoC that prints ``__MIMI_NET__:open`` used to flip its own
    isolation record under a later-match-wins parse.
    """
    i_iso = stdout.find("__MIMI_NET__:isolated")
    i_open = stdout.find("__MIMI_NET__:open")
    candidates = [(i_iso, "__MIMI_NET__:isolated", True), (i_open, "__MIMI_NET__:open", False)]
    present = [c for c in candidates if c[0] != -1]
    if not present:
        return None
    _, token, value = min(present, key=lambda c: c[0])
    return token, value


def config_key(config: "RunConfig") -> str:
    """Fingerprint of the **built image** a run executed in.

    This is the identity ``compute_coverage`` counts as one "config", and it
    is deliberately the *image* identity — node version, install command and
    the ordered setup — not the hypothesis's declared PoC command or file
    name. Those change what runs inside the image, not which environment was
    exercised, and counting them invented configuration diversity: three
    hypotheses forked from one base image were reported as three configs.

    ``package_spec`` is included because the affected and fixed phases build
    different packages into the image; coverage only counts affected-phase
    runs, where the spec is the pinned affected one.
    """
    setup = ",".join(config.setup_commands)  # order-sensitive: && -joined at build
    return (
        f"node{config.node_version}|{config.package_spec or ''}|"
        f"{config.install_command}|setup={setup}"
    )


def build_group_key(config: "RunConfig") -> str:
    """Fingerprint settings that change an image built for one package spec.

    Setup order matters because the commands run sequentially. The package
    spec is omitted so affected and fixed versions of the same configuration
    share the same group identity in their respective build maps.
    """
    setup = ",".join(config.setup_commands)
    return f"node{config.node_version}|{config.install_command}|setup={setup}"


def package_name(spec: str) -> str:
    """Package name of a ``name@version`` spec (scoped names included).

    ``@babel/traverse@7.20.0`` -> ``@babel/traverse``; ``lodash@4.17.20`` ->
    ``lodash``. Split on the last ``@`` that is not the leading scope marker.
    """
    s = (spec or "").strip()
    if not s:
        return ""
    if s.startswith("@"):
        head, sep, tail = s.rpartition("@")
        return head if sep else s
    name, sep, _ = s.partition("@")
    return name if sep else s


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
            from contree_sdk import Contree
            from contree_sdk.auth import IAMAuth
            from contree_sdk.config import ContreeConfig
        except ImportError as e:
            raise ExecutorError(
                "contree-sdk is not installed (pip install contree-sdk)"
            ) from e
        # contree-sdk 0.3.x exposes an async Contree client. Pass the key,
        # project, and Token Factory endpoint through IAMAuth so the SDK sends
        # both the Bearer token and required Project header.
        auth = IAMAuth(
            token=self.settings.nebius_api_key,
            project_id=self.settings.nebius_project_id,
            base_url=self.settings.sandboxes_base_url,
        )
        self._client = Contree(config=ContreeConfig(auth=auth))
        return self._client

    async def build(self, config: RunConfig, *, package_spec: str, build_timeout_s: int) -> BuildResult:
        client = self._ensure_client()
        t0 = time.monotonic()
        spec = config.package_spec or package_spec
        try:
            validate_run_config(config, where="build_config")
            # The submission's spec is an argument, not a RunConfig field, so
            # validate_run_config never sees it. Validate its npm name/version
            # before using the name to check the installed package manifest.
            name, _version = validate_package_spec(spec)
            _reject_meta("package_spec", spec)
        except (ConfigRejected, ValueError) as e:
            return BuildResult(
                image_id="",
                ok=False,
                detail=f"build config rejected: {e}",
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )
        setup = " && ".join(config.setup_commands) if config.setup_commands else "true"
        # The allowlisted install_command is what actually runs. `npm ci`
        # installs from the lockfile only and takes no package argument, so it
        # is given a lockfile that pins the target first — dropping the spec
        # entirely left the image without the dependency while still reporting
        # a successful build, and every fork then ran against nothing.
        if config.install_command.startswith("npm ci"):
            install = (
                f"npm install --package-lock-only --no-audit --no-fund {shlex.quote(spec)} && "
                f"{config.install_command}"
            )
        else:
            install = f"{config.install_command} {shlex.quote(spec)}"
        # Check the installed manifest rather than CommonJS resolution:
        # require.resolve rejects some valid ESM-only packages with conditional
        # exports even though npm installed them correctly.
        manifest = f"node_modules/{name}/package.json"
        verify = (
            f"node -e 'if (!require(\"fs\").existsSync({json.dumps(manifest)})) process.exit(1)'"
        )
        build_runner = (
            "set -e; test ! -w /usr/bin/unshare && test ! -w /usr/sbin/runuser; "
            "cd /work; export HOME=/home/node USER=node LOGNAME=node; "
            "npm init -y >/dev/null 2>&1 || true; "
            f"{install}; "
            f"{setup}; "
            f"{verify}; "
            f"echo {BUILD_OK_TOKEN}"
        )
        # Package lifecycle scripts are untrusted too. Build under the
        # image's unprivileged node account so scripts may prepare the target
        # package without being able to replace system tools used by later
        # PoC/probe invocations. The same boundary includes allowlisted setup
        # commands such as npm rebuild.
        cmd = (
            "set -e; mkdir -p /work && chmod 1777 /work && "
            "/usr/sbin/runuser --preserve-environment -u node -- /bin/sh -c "
            + shlex.quote(build_runner)
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
        sdk_result = getattr(result, "result", None)
        cost = getattr(sdk_result, "cost", None)
        raw_image_id = getattr(result, "uuid", None)
        image_id = str(raw_image_id) if raw_image_id else ""
        log = str(getattr(result, "stdout", "") or "") + str(getattr(result, "stderr", "") or "")
        exit_code = getattr(result, "exit_code", None)
        # ok is the build's claim that the environment is usable. An image UUID
        # only means the sandbox returned one: an install that failed or never
        # installed the target package used to report ok=True, and a PoC's
        # MODULE_NOT_FOUND was then graded as a conclusive "did not trigger".
        if exit_code not in (0, None):
            ok, detail = False, f"build failed (exit {exit_code})"
        elif not image_id:
            ok, detail = False, "build produced no image id"
        elif BUILD_OK_TOKEN not in log:
            ok, detail = False, (
                "build did not reach its success marker — the install or the "
                "package check failed, so the environment cannot be trusted"
            )
        else:
            ok, detail = True, "built base image"
        return BuildResult(
            image_id=image_id,
            log=log,
            ok=ok,
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            cost=cost,
            cost_units="contree-cost-units" if cost is not None else None,
            detail=detail,
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
        probe_env: Optional[dict[str, str]] = None,
        probe_snippet: Optional[str] = None,
    ) -> RunRecord:
        t0 = time.monotonic()
        if offline is not True:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase=_norm_phase(phase),
                command=config.poc_command,
                error="online PoC execution is disabled",
                network_isolated=False,
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )
        try:
            validate_run_config(config)
            marker_name = (probe_env or {}).get("MIMI_MARKER_PATH", "")
            if marker_name and (
                not _MARKER_FILE_RE.fullmatch(marker_name)
                or marker_name.startswith(".mimi_")
                or marker_name in {
                    "node_modules", "package.json", "package-lock.json",
                    config.poc_file_name,
                }
            ):
                raise ConfigRejected(
                    "probe marker path must be a simple non-reserved filename in /work"
                )
        except ConfigRejected as e:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase=_norm_phase(phase),
                command=config.poc_command,
                error=f"config rejected: {e}",
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )
        client = self._ensure_client()
        try:
            image = await client.images.use(build.image_id)  # fork point
            # Stage only the PoC and preloaded shim. The fixed-source probe is
            # supplied over stdin, never from the PoC-writable filesystem.
            write = await image.run(
                shell=_stage_file_command(f"/work/{config.poc_file_name}"),
                stdin=poc_code,
                timeout=30,
                disposable=False,
            )
            _require_staged(write, "the PoC")
            write = await write.run(
                shell=_stage_file_command(SHIM_FILE),
                stdin=SHIM_JS,
                timeout=30,
                disposable=False,
            )
            _require_staged(write, "the observation shim")
            # A package lifecycle script can leave a state file or symlink in
            # the persisted build image. Remove it and the marker target before
            # the PoC starts so build-time artifacts cannot become evidence.
            marker_name = (probe_env or {}).get("MIMI_MARKER_PATH", "")
            cleanup = "rm -rf -- /work/.mimi_probe_state.json"
            if marker_name:
                cleanup += " && rm -rf -- " + shlex.quote(f"/work/{marker_name}")
            write = await write.run(
                shell=f"set -e; {cleanup}; echo {_STAGE_OK_TOKEN}",
                timeout=30,
                disposable=False,
            )
            _require_staged(write, "the clean probe state")
            # Run the PoC. The command string is already validated against the
            # fixed set, so it is safe to interpolate as a shell command —
            # quoting it would make the shell try to exec a literal path.
            runner = (
                "set -e; cd /work; command -v node >/dev/null; "
                "test \"$(id -u)\" -eq 0; "
                "echo __MIMI_NET__:isolated; "
                + config.poc_command
            )
            # Make /work writable for the image's unprivileged node account,
            # then enter the user and network namespace as that account. The
            # marker is emitted inside the exact namespace that runs the PoC.
            # Running as node keeps PoC code from replacing system binaries
            # such as /usr/bin/unshare, even inside its user namespace.
            namespace_runner = (
                "test \"$(id -u)\" -ne 0 && "
                "test ! -w /usr/bin/unshare && test ! -w /usr/sbin/runuser && exec "
                "/usr/bin/unshare --user --map-root-user --net -- /bin/sh -c "
                + shlex.quote(runner)
            )
            wrapped = (
                "chmod 1777 /work && /usr/sbin/runuser --preserve-environment -u node -- /bin/sh -c "
                + shlex.quote(namespace_runner)
            )
            # The shim is preloaded into the PoC's own process so it can see
            # in-process state (prototype pollution, real egress attempts).
            # NODE_OPTIONS is executor-owned: validate_run_config refuses a
            # hypothesis that tries to set it.
            poc_env = dict(config.env or {})
            poc_env.update(probe_env or {})
            # A model-selected PATH could resolve a package-supplied fake
            # unshare before the system binary and forge the isolation marker.
            # The wrapper also uses the absolute unshare path above.
            poc_env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            poc_env["HOME"] = "/home/node"
            poc_env["USER"] = "node"
            poc_env["LOGNAME"] = "node"
            poc_env["NODE_OPTIONS"] = shim_node_options()
            poc_env["MIMI_STATE_PATH"] = STATE_FILE
            result = await write.run(
                shell=wrapped,
                timeout=timeout_s,
                env=poc_env or None,
                disposable=False,
            )
        except Exception as e:
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase=_norm_phase(phase),
                command=config.poc_command,
                error=f"run failed: {e}",
                elapsed_ms=(time.monotonic() - t0) * 1000.0,
            )

        raw_stdout = str(getattr(result, "stdout", "") or "")
        raw_stderr = str(getattr(result, "stderr", "") or "")

        # Fixed-source probe, run after the PoC in the same image so it sees
        # post-PoC state. Its output is separate from PoC stdout, but the
        # sandbox state it reads can still be tampered with by hostile code.
        # The post-PoC process must not inherit model-selected executable or
        # loader settings (PATH, LD_PRELOAD, NODE_OPTIONS, etc.). Pass only the
        # fixed probe inputs and a stable system PATH.
        env = dict(probe_env or {})
        env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        env["MIMI_STATE_PATH"] = STATE_FILE
        if probe_snippet:
            env["MIMI_CUSTOM_PROBE_B64"] = base64.b64encode(
                probe_snippet.encode("utf-8")
            ).decode("ascii")
        probe_out = ""
        try:
            probe_result = await result.run(
                shell=probe_command(),
                stdin=PROBE_JS,
                timeout=min(30, timeout_s),
                env=env or None,
            )
            probe_out = str(getattr(probe_result, "stdout", "") or "")
        except Exception as e:
            probe_out = f"__MIMI_PROBE_ERROR__:{e}"

        # Strip the network marker from the PoC output and record the truth.
        # Only the FIRST marker counts: the wrapper prints it before the PoC
        # starts, so anything later in the stream is PoC output and may be a
        # forged __MIMI_NET__ token. A later-match-wins parse let the code under
        # test flip its own isolation record.
        isolated: Optional[bool] = None
        first = _first_net_marker(raw_stdout)
        if first is not None:
            raw_stdout = raw_stdout.replace(first[0], "", 1)
            isolated = first[1]
            raw_stdout = raw_stdout.replace(first[0], "")  # scrub any forgeries too
        else:
            isolated = False if offline else None  # marker missing: do not claim isolation

        run_error = None
        if offline and isolated is not True:
            run_error = (
                "network isolation was unavailable; the PoC was not executed"
                if first is not None and first[0] == "__MIMI_NET__:open"
                else "network isolation could not be verified; the run is inconclusive"
            )

        stdout, trunc1 = _cap(raw_stdout, self.settings.output_cap_bytes)
        stderr, trunc2 = _cap(raw_stderr, self.settings.output_cap_bytes)
        probe_output, trunc3 = _cap(probe_out, self.settings.output_cap_bytes)
        sdk_result = getattr(result, "result", None)
        cost = getattr(sdk_result, "cost", None)
        elapsed = getattr(result, "elapsed", None)
        elapsed_ms = (
            elapsed.total_seconds() * 1000.0
            if callable(getattr(elapsed, "total_seconds", None))
            else (time.monotonic() - t0) * 1000.0
        )
        image_id = getattr(result, "uuid", None)
        run_id = getattr(result, "id", None)
        return RunRecord(
            hypothesis_id=hypothesis_id,
            phase=_norm_phase(phase),
            command=config.poc_command,
            exit_code=getattr(result, "exit_code", None),
            signal=getattr(result, "signal", None),
            stdout=stdout,
            stderr=stderr,
            probe_output=probe_output,
            elapsed_ms=elapsed_ms,
            cost=cost,
            cost_units="contree-cost-units" if cost is not None else None,
            sandbox_image_id=str(image_id) if image_id else None,
            sandbox_run_id=str(run_id) if run_id else None,
            network_isolated=isolated,
            error=run_error,
            truncated=trunc1 or trunc2 or trunc3,
            config_key=config_key(config),
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
        probe_env: Optional[dict[str, str]] = None,
        probe_snippet: Optional[str] = None,
    ) -> RunRecord:
        data_map = self._load().get("fixed_runs" if phase == "fixed" else "runs", {})
        data = data_map.get(hypothesis_id)
        # Fixtures only ever replay an affected ("poc") or fixed-version run.
        run_phase: _Phase = "fixed" if phase == "fixed" else "poc"
        if data is None:
            # A missing fixture is NOT evidence of anything. In particular a
            # missing fixed-phase fixture must not be read as "does not fire on
            # the fixed version" — that would fabricate a Confirmed tier.
            return RunRecord(
                hypothesis_id=hypothesis_id,
                phase=run_phase,
                command=config.poc_command,
                error=f"no fixture for hypothesis {hypothesis_id} (phase={phase})",
                config_key=config_key(config),
            )
        record = RunRecord.model_validate(
            {**data, "hypothesis_id": hypothesis_id, "phase": run_phase}
        )
        if not record.config_key:
            record.config_key = config_key(config)
        return record

    async def close(self) -> None:
        return None


async def whoami(settings) -> dict:
    """Read Sandboxes permissions from the current Token Factory endpoint.

    The service root is ``https://api.tokenfactory.nebius.com/sandboxes``;
    the versioned endpoint is ``GET /v1/whoami``. This read-only probe never
    returns or logs credentials.
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
        path = "/v1/whoami"
        try:
            r = await client.get(base + path, headers=headers)
        except httpx.HTTPError as e:
            out[path] = {"error": str(e)}
            return out
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
