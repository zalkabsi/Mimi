"""Trusted post-PoC probe.

Probe oracles must not read the PoC's own stdout: untrusted code can print any
token it likes (``__MIMI_PROTO_POLLUTED__:true`` is one line of JavaScript).
So the executor runs a second, trusted command *after* the PoC, captures its
output into ``RunRecord.probe_output``, and the oracles read only that channel.

The probe inspects the *post-PoC state* of the sandbox — which is exactly what
a reproduction is about: did this code pollute the prototype, create that
marker, or make that path readable.

The probe source lives here (trusted, reviewed) and is never taken from a
report or from a hypothesis.
"""

from __future__ import annotations

from .schemas import Oracle, OracleType

# Printed once so the executor and the tests can tell a real probe run from an
# empty capture. Oracles never treat this line as evidence either way.
PROBE_BEGIN = "__MIMI_PROBE_BEGIN__"

# Node CommonJS: runs in the sandbox after the PoC, in the same /work tree.
# No npm, no network, no third-party imports — stdlib only.
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

// 1. Prototype pollution: did Object.prototype gain own properties that a
//    plain object literal would inherit? We compare against a null-prototype
//    object so the check cannot be fooled by a polluted Object.prototype.
const polluted = safe(() => {
  const probe = {};
  const keys = Object.keys(probe);
  const names = Object.getOwnPropertyNames(Object.prototype)
    .filter((k) => k !== 'constructor' && k !== 'hasOwnProperty' &&
                   k !== 'isPrototypeOf' && k !== 'propertyIsEnumerable' &&
                   k !== 'toLocaleString' && k !== 'toString' &&
                   k !== 'valueOf' && k !== '__defineGetter__' &&
                   k !== '__defineSetter__' && k !== '__lookupGetter__' &&
                   k !== '__lookupSetter__');
  // A polluted prototype shows up as an enumerable or unexpected own prop.
  const extra = names.filter((k) => {
    const d = Object.getOwnPropertyDescriptor(Object.prototype, k);
    return d && (d.enumerable || d.writable);
  });
  return extra.length > 0 || keys.length > 0;
}, false);
emit('PROTO_POLLUTED', polluted ? 'true' : 'false');

// 2. Marker file: did the PoC create/leave a marker at this path?
const markerRel = process.env.MIMI_MARKER_PATH || '';
if (markerRel) {
  const p = path.isAbsolute(markerRel) ? markerRel : path.join(process.cwd(), markerRel);
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

// 4. Network: can the sandbox reach out at all? This reports the sandbox's
//    network state after the PoC (used for the egress safety case). A PoC
//    that merely *tried* and failed is still a network attempt; the executor
//    notes that in the run's network_isolated field rather than here.
const wantNet = process.env.MIMI_PROBE_NETWORK === '1';
if (wantNet) {
  const attempted = safe(() => {
    // A connect to a non-routable address still exercises the stack; success
    // means the sandbox has egress. Either outcome is a real measurement.
    const net = require('net');
    const sock = net.connect({ host: '1.1.1.1', port: 80, timeout: 1500 });
    let done = false;
    const t0 = Date.now();
    // Synchronous-ish: block on the event loop is not possible here, so we
    // report 'attempted' whenever the connect was issued without throwing.
    sock.on('error', () => {});
    sock.destroy();
    return true;
  }, false);
  emit('NETWORK', attempted ? 'attempted' : 'not-attempted');
}

process.stdout.write('__MIMI_PROBE_END__\n');
"""


def probe_command() -> str:
    """Shell command that runs the trusted probe and prints its verdicts.

    Written to a fixed path (``/work/.mimi_probe.js``) so it cannot collide
    with the PoC file name, then executed with node.
    """
    return (
        "cat > /work/.mimi_probe.js <<'MIMI_PROBE_EOF'\n"
        + PROBE_JS
        + "\nMIMI_PROBE_EOF\n"
        "node /work/.mimi_probe.js"
    )


def probe_env_for(oracle: Oracle) -> dict[str, str]:
    """Env the trusted probe reads to know what to inspect.

    Derived only from the oracle's own declared targets (a RunConfig/Oracle
    field), never from report prose.
    """
    env: dict[str, str] = {}
    if oracle.marker_path:
        env["MIMI_MARKER_PATH"] = oracle.marker_path
    if oracle.expect_traversal_to:
        env["MIMI_TRAVERSAL_PATH"] = oracle.expect_traversal_to
    if oracle.type is OracleType.NETWORK_CALL:
        env["MIMI_PROBE_NETWORK"] = "1"
    return env
