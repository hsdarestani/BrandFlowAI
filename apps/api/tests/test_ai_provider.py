import json

from app.services.ai.providers import OpenAICompatibleProvider


class FakeResponse:
    status_code = 200
    content = b"{}"
    text = ""

    def json(self):
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": json.dumps({"answer": "ok"}),
                        }
                    ],
                }
            ]
        }


def test_openai_provider_uses_responses_and_strict_schema(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "body": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr("app.services.ai.providers.httpx.post", fake_post)
    provider = OpenAICompatibleProvider(api_key="test-key", model="gpt-5.6-sol", timeout_seconds=12)
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    result = provider.generate_json("Return an answer", schema=schema)

    assert result == {"answer": "ok"}
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "gpt-5.6-sol"
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["type"] == "json_schema"
    assert captured["body"]["text"]["format"]["strict"] is True
    assert captured["body"]["reasoning"]["effort"] == "high"
