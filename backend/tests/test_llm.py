from mimi.config import Stage, Settings
from mimi.llm import LLMClient, LLMResponse


def test_chat_json_retries_truncated_response_with_larger_budget(monkeypatch):
    client = LLMClient(Settings())
    calls = []

    def fake_chat(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return LLMResponse(
                content='{"hypotheses": [',
                model="test",
                usage={},
                latency_ms=1,
                raw={"choices": [{"finish_reason": "length"}]},
            )
        return LLMResponse(
            content='{"hypotheses": []}',
            model="test",
            usage={},
            latency_ms=1,
            raw={"choices": [{"finish_reason": "stop"}]},
        )

    monkeypatch.setattr(client, "chat", fake_chat)
    try:
        result = client.chat_json(
            stage=Stage.HYPOTHESIZE,
            messages=[{"role": "user", "content": "Generate hypotheses."}],
            schema_hint='{"hypotheses": []}',
            max_tokens=1500,
        )
    finally:
        client.close()

    assert result == {"hypotheses": []}
    assert [call["max_tokens"] for call in calls] == [1500, 3000]
    retry_messages = calls[1]["messages"]
    assert not any(message.get("content") == '{"hypotheses": [' for message in retry_messages)
    assert "cut off by the output-token limit" in retry_messages[-1]["content"]
