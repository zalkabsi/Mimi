"""Post-PoC probe, plus the in-process observation shim.

Two channels, both outside the PoC's own stdout:

1. **The shim** (``SHIM_JS``) is preloaded into the PoC's own Node process
   (``NODE_OPTIONS=--require=...``) *before* the untrusted code runs. It can
   therefore see things a later process cannot: prototype pollution (heap state
   dies with the process) and network calls the PoC actually made. At process
   exit it writes a JSON verdict file.

2. **The probe** (``PROBE_JS``) runs in a fresh process *after* the PoC. It
   reads the shim's verdict file plus real filesystem state (marker files,
   path traversal) and prints verdict tokens. Those tokens — captured into
   ``RunRecord.probe_output`` — are the only thing probe oracles read.

The PoC's stdout is not used for probe-oracle verdicts. The shim state file is
still in the same writable VM as the PoC, so hostile code can tamper with it;
this channel is not tamper-proof and the dossier must disclose that limitation.

Honest limits, stated in the dossier rather than papered over:
- The shim writes its verdict at process exit. A PoC that removes Node's exit
  listeners suppresses the write; a *missing* verdict file is therefore
  reported as ``__MIMI_PROBE_MISSING__`` and every probe oracle is
  **inconclusive** — never a clean negative.
- A PoC can remove the exit listeners and write a fake verdict file, or
  overwrite the file after the shim writes it. This residual risk of same-VM
  observation is disclosed in the dossier. A fresh-process-only probe could
  never observe in-process state, but the shim does not provide tamper-proof
  evidence against hostile code.
- The probe scripts live here (trusted, reviewed) and are never taken from a
  report or from a hypothesis. The one exception is ``probe_snippet`` for
  CUSTOM_PROBE: that is hypothesis-declared code, run in the sandbox like any
  other untrusted code, and its output is labelled as such.
"""

from __future__ import annotations

from .schemas import Oracle, OracleType

# Printed once so the executor and the tests can tell a real probe run from an
# empty capture. Oracles never treat this line as evidence either way.
PROBE_BEGIN = "__MIMI_PROBE_BEGIN__"

# Fixed paths inside /work. The PoC runs first, so these names must not collide
# with the staged PoC file name (which is a validated bare *.js name).
SHIM_FILE = "/work/.mimi_shim.js"
STATE_FILE = "/work/.mimi_probe_state.json"

# In-process observation shim: preloaded into the PoC's Node process. It must
# never throw at load time (that would break every PoC) and must never change
# the PoC's observable exit behaviour — so no signal handlers, only 'exit'.
SHIM_JS = r"""
'use strict';
// Mimi observation shim. Loads before the untrusted PoC in the SAME process.
// Records (a) properties added to Object.prototype while the PoC ran and
// (b) egress APIs the PoC actually called. Writes them at process exit for a
// fresh process to read. The PoC shares this VM and can tamper with the file.
const fs = require('fs');
const path = require('path');

const STATE_PATH = process.env.MIMI_STATE_PATH || '/work/.mimi_probe_state.json';

const NATIVE_KEYS = new Set([
  'constructor', 'hasOwnProperty', 'isPrototypeOf', 'propertyIsEnumerable',
  'toLocaleString', 'toString', 'valueOf', '__defineGetter__', '__defineSetter__',
  '__lookupGetter__', '__lookupSetter__',
]);

function protoKeys() {
  try {
    return Object.getOwnPropertyNames(Object.prototype).filter(function (k) {
      return !NATIVE_KEYS.has(k);
    });
  } catch (e) {
    return [];
  }
}

const baseline = protoKeys();
const netAttempts = [];

function recordAttempt(kind, detail) {
  if (netAttempts.length < 32) {
    netAttempts.push({ kind: kind, detail: String(detail).slice(0, 120) });
  }
}

function wrap(obj, name, kind) {
  try {
    const orig = obj[name];
    if (typeof orig !== 'function') return;
    const patched = function () {
      const a = arguments[0];
      let detail = '';
      try {
        detail = (a && (a.href || a.host || a.hostname || a)) || '';
      } catch (e) { detail = ''; }
      recordAttempt(kind, detail);
      return orig.apply(this, arguments);
    };
    obj[name] = patched;
  } catch (e) { /* never break the PoC */ }
}

try {
  const net = require('net');
  wrap(net, 'connect', 'net.connect');
  wrap(net, 'createConnection', 'net.createConnection');
  const http = require('http');
  wrap(http, 'request', 'http.request');
  wrap(http, 'get', 'http.get');
  const https = require('https');
  wrap(https, 'request', 'https.request');
  wrap(https, 'get', 'https.get');
  const dns = require('dns');
  wrap(dns, 'lookup', 'dns.lookup');
  wrap(dns, 'resolve', 'dns.resolve');
  wrap(dns, 'resolve4', 'dns.resolve4');
  if (typeof globalThis.fetch === 'function') wrap(globalThis, 'fetch', 'fetch');
} catch (e) {}

function writeState(extra) {
  try {
    const now = protoKeys();
    const added = now.filter(function (k) { return baseline.indexOf(k) === -1; });
    const body = Object.assign({
      shim: 'ok',
      proto_added: added,
      proto_added_count: added.length,
      net_attempts: netAttempts,
      net_attempted: netAttempts.length > 0,
    }, extra || {});
    fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
    fs.writeFileSync(STATE_PATH, JSON.stringify(body));
  } catch (e) {
    try {
      fs.writeFileSync(STATE_PATH, JSON.stringify({ shim: 'error', error: String(e).slice(0, 200) }));
    } catch (e2) { /* nothing else we can do */ }
  }
}

// Mark that the shim loaded at all, so a missing exit write can be told apart
// from "NODE_OPTIONS never loaded us".
try {
  fs.mkdirSync(path.dirname(STATE_PATH), { recursive: true });
  fs.writeFileSync(STATE_PATH, JSON.stringify({ shim: 'loaded' }));
} catch (e) {}

process.on('exit', function () { writeState(); });
"""

# Fresh-process probe: reads the shim's verdict file, inspects filesystem
# state, optionally measures sandbox egress, runs the custom snippet.
# Verdict tokens are the probe-oracle contract (backend/mimi/oracles.py).
PROBE_JS = r"""
'use strict';
const fs = require('fs');
const path = require('path');

function emit(kind, verdict) {
  process.stdout.write('__MIMI_' + kind + '__:' + verdict + '\n');
}

function safe(fn, fallback) {
  try { return fn(); } catch (e) { return fallback; }
}

const STATE_PATH = process.env.MIMI_STATE_PATH || '/work/.mimi_probe_state.json';

// 1. In-process observations (prototype pollution, network attempts) come
//    from the shim's exit file. Missing or half-written state is NOT a negative.
let state = null;
const stateRaw = safe(() => fs.readFileSync(STATE_PATH, 'utf8'), null);
if (stateRaw === null) {
  emit('PROBE_MISSING', STATE_PATH);
} else {
  state = safe(() => JSON.parse(stateRaw), null);
  if (!state || typeof state !== 'object') {
    emit('PROBE_MISSING', 'unparseable-state');
  } else if (state.shim !== 'ok') {
    emit('PROBE_MISSING', 'shim-' + String(state.shim || 'unknown'));
  }
}

if (state && state.shim === 'ok') {
  // 1a. Prototype pollution: properties added to Object.prototype while the
  //     PoC ran. Measured in-process; a fresh node could never see this.
  const added = Array.isArray(state.proto_added) ? state.proto_added : null;
  if (added === null) {
    emit('PROBE_MISSING', 'no-proto-report');
  } else {
    emit('PROTO_POLLUTED', added.length > 0 ? 'true' : 'false');
    if (added.length > 0) emit('PROTO_KEYS', added.slice(0, 16).join(','));
  }
  // 1b. Egress attempts the PoC actually issued (wrapped APIs).
  const attempted = state.net_attempted === true ||
    (Array.isArray(state.net_attempts) && state.net_attempts.length > 0);
  emit('NETWORK', attempted ? 'attempted' : 'none');
}

// 2. Marker file: did the PoC create/leave a marker at this path? Relative
//    paths resolve against /work (the workdir contract), never against the
//    probe's own cwd.
const markerRel = process.env.MIMI_MARKER_PATH || '';
if (markerRel) {
  const p = path.isAbsolute(markerRel) ? markerRel : path.join('/work', markerRel);
  const present = safe(() => fs.existsSync(p), false);
  emit('MARKER_VERDICT', markerRel + ':' + (present ? 'present' : 'absent'));
}

// 3. Path traversal: can this path be read from inside the sandbox?
const trav = process.env.MIMI_TRAVERSAL_PATH || '';
if (trav) {
  let ok = false;
  try {
    fs.readFileSync(trav);
    ok = true;
  } catch (e) {
    ok = false;
  }
  emit('TRAVERSAL', trav + ':' + (ok ? 'read' : 'blocked'));
}

// 4. Custom probe snippet (hypothesis-declared code, run as untrusted code in
//    a child user+network namespace). A small fixed loader compiles it with a
//    virtual filename in /work so ordinary package imports resolve there;
//    the snippet itself is never written to a PoC-writable file.
//    Its output is labelled CUSTOM_* so it cannot masquerade as a fixed probe.
if (process.env.MIMI_CUSTOM_PROBE_B64) {
  try {
    emit('CUSTOM_PROBE_BEGIN', 'stdin');
    const childEnv = { ...process.env };
    childEnv.HOME = '/home/node';
    childEnv.USER = 'node';
    childEnv.LOGNAME = 'node';
    delete childEnv.NODE_OPTIONS;
    const loader = [
      "const Module = require('module');",
      "const filename = '/work/.mimi_custom_probe.js';",
      'const mod = new Module(filename);',
      'mod.filename = filename;',
      "mod.paths = Module._nodeModulePaths('/work');",
      "const source = Buffer.from(process.env.MIMI_CUSTOM_PROBE_B64, 'base64').toString('utf8');",
      'delete process.env.MIMI_CUSTOM_PROBE_B64;',
      'mod._compile(source, filename);',
    ].join('\n');
    const out = safe(() => require('child_process').execFileSync(
      '/usr/sbin/runuser', [
        '--preserve-environment', '-u', 'node', '--',
        '/bin/sh', '-c',
        'test ! -w /usr/bin/unshare && test ! -w /usr/sbin/runuser && ' +
          'exec /usr/bin/unshare --user --map-root-user --net -- "$1" -',
        'mimi-custom-probe', process.execPath,
      ],
      {
        input: loader, cwd: '/work', timeout: 10000, encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe'], env: childEnv,
      }
    ), null);
    if (out === null) throw new Error('custom probe namespace could not be created');
    process.stdout.write(String(out).slice(0, 64000));
    emit('CUSTOM_PROBE_END', 'ran');
  } catch (e) {
    emit('CUSTOM_PROBE_ERROR', String(e).slice(0, 200));
  }
}

// 5. Optional sandbox-egress measurement (not the PoC's attempts — those are
//    the shim's job). Reported separately so the two are never conflated.
if (process.env.MIMI_PROBE_EGRESS === '1') {
  try {
    const net = require('net');
    const sock = net.connect({ host: '1.1.1.1', port: 80 });
    let settled = false;
    const done = (v) => {
      if (settled) return;
      settled = true;
      emit('EGRESS', v);
      process.stdout.write('__MIMI_PROBE_END__\n');
    };
    const timer = setTimeout(() => {
      try { sock.destroy(); } catch (e) {}
      done('unmeasured');
    }, 1500);
    sock.on('connect', () => {
      clearTimeout(timer);
      try { sock.destroy(); } catch (e) {}
      done('connected');
    });
    sock.on('error', () => {
      clearTimeout(timer);
      done('blocked');
    });
  } catch (e) {
    emit('EGRESS', 'unmeasured');
    process.stdout.write('__MIMI_PROBE_END__\n');
  }
} else {
  process.stdout.write('__MIMI_PROBE_END__\n');
}
"""


def probe_command() -> str:
    """Run trusted probe source supplied directly over stdin.

    The source never resides on the PoC-writable filesystem, so a PoC cannot
    replace the code that produces the independent probe-output channel.
    """
    return "node -"


def shim_node_options() -> str:
    """``NODE_OPTIONS`` value that preloads the observation shim into the PoC."""
    return f"--require={SHIM_FILE}"


def probe_env_for(oracle: Oracle) -> dict[str, str]:
    """Env the trusted probe/shim read to know what to inspect.

    Derived only from the oracle's own declared targets (an Oracle field),
    never from report prose.
    """
    env: dict[str, str] = {"MIMI_STATE_PATH": STATE_FILE}
    if oracle.marker_path:
        env["MIMI_MARKER_PATH"] = oracle.marker_path
    if oracle.expect_traversal_to:
        env["MIMI_TRAVERSAL_PATH"] = oracle.expect_traversal_to
    if oracle.type is OracleType.NETWORK_CALL:
        # Measure sandbox reachability alongside the PoC-attempt verdict from
        # the shim. The oracle fires on attempts; EGRESS is context only.
        env["MIMI_PROBE_EGRESS"] = "1"
    return env
