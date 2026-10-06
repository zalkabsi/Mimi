"""Thin LLM client for Token Factory (OpenAI-compatible) with stage routing.

- One class, per-stage model choice (see ``config.STAGE_MODEL_TABLE``).
- Retry once on invalid JSON for schema-validated calls (stage 1 contract).
- Logs tokens and latency into the report's EventLog. ``completion_tokens_details``
  is null on Token Factory (2026-09-30), so reasoning tokens are not itemised —
  we never fabricate that split.
- Reasoning control: Nemotron Nano is a reasoning model. For cheap calls pass
  ``chat_template_kwargs: {"enable_thinking": false}`` (verified working).
  A tiny ``max_tokens`` with reasoning on returns empty content — avoid it.
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional

import httpx

from .config import NEMOTRON_MODELS, Settings, Stage
from .events import EventLog


class LLMError(RuntimeError):
    pass


class LLMResponse:
    def __init__(self, content: str, model: str, usage: dict[str, Any], latency_ms: float, raw: dict[str, Any]):
        self.content = content
        self.model = model
        self.usage = usage or {}
        self.latency_ms = latency_ms
        self.raw = raw

    @property
    def tokens_in(self) -> int:
        return int(self.usage.get("prompt_tokens") or 0)

    @property
    def tokens_out(self) -> int:
        return int(self.usage.get("completion_tokens") or 0)


class LLMClient:
    def __init__(self, settings: Settings, events: Optional[EventLog] = None, client: Optional[httpx.Client] = None):
        self.settings = settings
        self.events = events
        self._client = client or httpx.Client(timeout=180.0)

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------
    def chat(
        self,
        *,
        stage: Stage,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        enable_thinking: bool = False,
        temperature: float = 0.2,
        model_id: Optional[str] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        force_model: Optional[str] = None,
    ) -> LLMResponse:
        """One chat call. ``force_model`` overrides the routing table (used by
        the E3 ablation and by stage 8 escalation)."""
        self.settings.require_inference()
        mid = model_id or (
            NEMOTRON_MODELS.get(force_model, force_model) if force_model else self.settings.model_id(stage)
        )

        body: dict[str, Any] = {
            "model": mid,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            # vLLM-style reasoning switch, verified on Token Factory 2026-09-30.
            "chat_template_kwargs": {"enable_thinking": enable_thinking},
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        t0 = time.monotonic()
        try:
            resp = self._client.post(
                f"{self.settings.inference_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.nebius_api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            latency_ms = (time.monotonic() - t0) * 1000.0
            if resp.status_code != 200:
                self._log(stage, mid, None, latency_ms, f"HTTP {resp.status_code}: {resp.text[:200]}")
                raise LLMError(f"inference HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
        except httpx.HTTPError as e:
            latency_ms = (time.monotonic() - t0) * 1000.0
            self._log(stage, mid, None, latency_ms, f"transport error: {e}")
            raise LLMError(f"inference transport error: {e}") from e

        usage = data.get("usage") or {}
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        content = msg.get("content") or ""
        # Token Factory puts reasoning in message.reasoning; keep it out of content.
        result = LLMResponse(content=content, model=mid, usage=usage, latency_ms=latency_ms, raw=data)
        self._log(
            stage,
            mid,
            result,
            latency_ms,
            f"{len(content)} chars, finish={ (data.get('choices') or [{}])[0].get('finish_reason') }",
        )
        return result

    def _log(self, stage: Stage, model: str, result: Optional[LLMResponse], latency_ms: float, detail: str) -> None:
        if self.events is not None:
            self.events.emit(
                stage.value,
                "ok" if result is not None else "error",
                detail,
                model=model,
                tokens_in=result.tokens_in if result else None,
                tokens_out=result.tokens_out if result else None,
                latency_ms=latency_ms,
            )

    # ------------------------------------------------------------------
    def chat_json(
        self,
        *,
        stage: Stage,
        messages: list[dict[str, str]],
        schema_hint: str,
        max_tokens: int = 1500,
        enable_thinking: bool = False,
        temperature: float = 0.1,
        max_retries: int = 1,
        force_model: Optional[str] = None,
    ) -> dict[str, Any]:
        """Ask for a JSON object and parse it. Retries once with the error
        appended when parsing fails (stage 1 contract)."""
        msgs = list(messages)
        msgs.append(
            {
                "role": "system",
                "content": (
                    f"Respond with a single JSON object only, matching this schema:\n{schema_hint}\n"
                    "No markdown fences, no commentary."
                ),
            }
        )
        last_err: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            resp = self.chat(
                stage=stage,
                messages=msgs,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
                temperature=temperature,
                force_model=force_model,
            )
            text = _strip_fences(resp.content)
            try:
                obj = json.loads(text)
                if not isinstance(obj, dict):
                    raise ValueError("expected a JSON object")
                return obj
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
                if attempt < max_retries:
                    msgs = msgs[: len(messages)] + [
                        {
                            "role": "system",
                            "content": (
                                f"Respond with a single JSON object only, matching this schema:\n{schema_hint}\n"
                                "No markdown fences, no commentary."
                            ),
                        },
                        {"role": "assistant", "content": resp.content or ""},
                        {"role": "user", "content": f"That was not valid JSON ({e}). Return only the JSON object."},
                    ]
        raise LLMError(f"model did not return valid JSON: {last_err}")


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()
