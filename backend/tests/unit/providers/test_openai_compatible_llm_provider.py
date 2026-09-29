import json
import logging

import httpx
import pytest

from src.core.exceptions import LlmException
from src.providers.openai_compatible_llm_provider import OpenAiCompatibleLlmProvider


def _ok(content: str = '{"ok": true}') -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _provider(handler, **overrides) -> OpenAiCompatibleLlmProvider:
    params = {
        "base_url": "https://llm.example/v1",
        "api_key": "test-key",
        "model": "test-model",
        "timeout_seconds": 30,
        "extra_headers": {},
        "http_transport": httpx.MockTransport(handler),
    }
    params.update(overrides)
    return OpenAiCompatibleLlmProvider(**params)


async def test_posts_expected_request():
    captured = {}

    def handler(request):
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return _ok()

    provider = _provider(handler)

    await provider.complete_json("system text", "user text")

    assert captured["method"] == "POST"
    assert captured["url"] == "https://llm.example/v1/chat/completions"
    body = captured["body"]
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert body["messages"] == [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "user text"},
    ]


async def test_trailing_slash_base_url_gives_same_url():
    urls = []

    def handler(request):
        urls.append(str(request.url))
        return _ok()

    provider = _provider(handler, base_url="https://llm.example/v1/")

    await provider.complete_json("system", "user")

    assert urls == ["https://llm.example/v1/chat/completions"]


async def test_sends_authorization_and_extra_headers():
    captured = {}

    def handler(request):
        captured["headers"] = request.headers
        return _ok()

    provider = _provider(handler, extra_headers={"x-opencode-session": "uk-support"})

    await provider.complete_json("system", "user")

    assert captured["headers"]["authorization"] == "Bearer test-key"
    assert captured["headers"]["x-opencode-session"] == "uk-support"


async def test_omits_authorization_without_api_key():
    captured = {}

    def handler(request):
        captured["headers"] = request.headers
        return _ok()

    provider = _provider(handler, api_key="")

    await provider.complete_json("system", "user")

    assert "authorization" not in captured["headers"]


async def test_returns_content_string():
    provider = _provider(lambda request: _ok('{"insight": "text"}'))

    content = await provider.complete_json("system", "user")

    assert content == '{"insight": "text"}'


@pytest.mark.parametrize("status", [400, 401, 500])
async def test_non_200_raises_llm_exception(status):
    def handler(request):
        return httpx.Response(status, json={"error": "boom"})

    provider = _provider(handler)

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


async def test_read_timeout_raises_llm_exception():
    def handler(request):
        raise httpx.ReadTimeout("timed out")

    provider = _provider(handler)

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


async def test_connect_error_raises_llm_exception():
    def handler(request):
        raise httpx.ConnectError("no network")

    provider = _provider(handler)

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


async def test_invalid_base_url_raises_llm_exception():
    provider = _provider(lambda request: _ok(), base_url="http://[::1")

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


async def test_non_json_body_raises_llm_exception():
    def handler(request):
        return httpx.Response(200, content=b"not json")

    provider = _provider(handler)

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


@pytest.mark.parametrize(
    "body",
    [
        [],
        "text",
        None,
        {},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "   "}}]},
        {"choices": [{"message": {"content": 42}}]},
    ],
)
async def test_invalid_response_body_raises_llm_exception(body):
    def handler(request):
        return httpx.Response(200, json=body)

    provider = _provider(handler)

    with pytest.raises(LlmException):
        await provider.complete_json("system", "user")


async def test_failure_does_not_log_api_key_or_prompts(caplog):
    def handler(request):
        return httpx.Response(400, json={"error": "boom"})

    provider = _provider(
        handler,
        api_key="secret-key-123",
        extra_headers={"x-token": "secret-header-value"},
    )

    with caplog.at_level(logging.WARNING), pytest.raises(LlmException):
        await provider.complete_json("system-secret-prompt", "user-secret-prompt")

    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "secret-key-123" not in logged
    assert "secret-header-value" not in logged
    assert "system-secret-prompt" not in logged
    assert "user-secret-prompt" not in logged
    assert any(record.levelno == logging.WARNING for record in caplog.records)
