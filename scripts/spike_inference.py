"""Week-1 spike 1 — Token Factory inference: base URL, model IDs, tool
calling, reasoning control. Logs tokens and latency (never the key).

    python scripts/spike_inference.py            # all checks
    python scripts/spike_inference.py --model nano --tool-calling

Recorded results (2026-09-30) live in docs/00-constraints-and-open-items.md.
This script re-verifies and prints a machine-readable JSON summary for the
feedback log.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from mimi.config import NEMOTRON_MODELS, Settings  # noqa: E402

OUT: list[dict] = []


def record(name: str, ok: bool, detail: str, **extra) -> None:
    entry = {"check": name, "ok": ok, "detail": detail, **extra}
    OUT.append(entry)
    print(f"[{'ok' if ok else 'FAIL'}] {name}: {detail}")


def chat(client: httpx.Client, base: str, key: str, body: dict) -> dict:
    t0 = time.monotonic()
    resp = client.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
    )
    ms = (time.monotonic() - t0) * 1000.0
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    data["_latency_ms"] = ms
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=list(NEMOTRON_MODELS), default="nano")
    parser.add_argument("--tool-calling", action="store_true", help="only run the tool-calling check")
    args = parser.parse_args()

    settings = Settings.from_env()
    if not settings.nebius_api_key:
        print("NEBIUS_API_KEY not set (env var only; never paste keys in chat)", file=sys.stderr)
        return 2

    base = settings.inference_base_url
    mid = NEMOTRON_MODELS[args.model]
    with httpx.Client(timeout=60.0) as client:
        # 1. models list
        try:
            r = client.get(f"{base}/models", headers={"Authorization": f"Bearer {settings.nebius_api_key}"})
            ids = [m.get("id") for m in (r.json().get("data") or [])]
            record("models", r.status_code == 200, f"HTTP {r.status_code}, {len(ids)} models", ids=ids[:20])
        except Exception as e:
            record("models", False, str(e))

        if not args.tool_calling:
            # 2. reasoning ON vs OFF (the enable_thinking knob)
            for thinking in (True, False):
                try:
                    data = chat(
                        client,
                        base,
                        settings.nebius_api_key,
                        {
                            "model": mid,
                            "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
                            "max_tokens": 300,
                            "chat_template_kwargs": {"enable_thinking": thinking},
                        },
                    )
                    msg = (data.get("choices") or [{}])[0].get("message") or {}
                    usage = data.get("usage") or {}
                    record(
                        f"reasoning_{'on' if thinking else 'off'}",
                        bool(msg.get("content")),
                        f"content={msg.get('content')!r} reasoning_len={len(msg.get('reasoning') or '')} "
                        f"tokens={usage.get('prompt_tokens')}+{usage.get('completion_tokens')} "
                        f"latency_ms={data['_latency_ms']:.0f}",
                        usage=usage,
                    )
                except Exception as e:
                    record(f"reasoning_{'on' if thinking else 'off'}", False, str(e))

            # 3. empty-content trap: tiny max_tokens with reasoning on
            try:
                data = chat(
                    client,
                    base,
                    settings.nebius_api_key,
                    {
                        "model": mid,
                        "messages": [{"role": "user", "content": "Reply with the single word: ready"}],
                        "max_tokens": 20,
                        "chat_template_kwargs": {"enable_thinking": True},
                    },
                )
                msg = (data.get("choices") or [{}])[0].get("message") or {}
                record(
                    "tiny_max_tokens_reasoning_on",
                    True,
                    f"content={msg.get('content')!r} (empty content is the known trap)",
                )
            except Exception as e:
                record("tiny_max_tokens_reasoning_on", False, str(e))

        # 4. tool calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "look_up_advisory",
                    "description": "Look up a public security advisory by id",
                    "parameters": {
                        "type": "object",
                        "properties": {"advisory_id": {"type": "string"}},
                        "required": ["advisory_id"],
                    },
                },
            }
        ]
        try:
            data = chat(
                client,
                base,
                settings.nebius_api_key,
                {
                    "model": mid,
                    "messages": [{"role": "user", "content": "Check advisory CVE-2021-44906 for me."}],
                    "tools": tools,
                    "tool_choice": "auto",
                    "max_tokens": 300,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            msg = (data.get("choices") or [{}])[0].get("message") or {}
            calls = msg.get("tool_calls") or []
            record(
                "tool_calling",
                bool(calls),
                f"{len(calls)} tool call(s): {[c.get('function', {}).get('name') for c in calls]}"
                if calls
                else f"no tool_calls; content={str(msg.get('content'))[:120]!r}",
                latency_ms=data["_latency_ms"],
                usage=data.get("usage"),
            )
        except Exception as e:
            record("tool_calling", False, str(e))

    print("\n--- JSON summary ---")
    print(json.dumps(OUT, indent=2))
    return 0 if all(e["ok"] for e in OUT) else 1


if __name__ == "__main__":
    raise SystemExit(main())
