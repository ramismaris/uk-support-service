import logging

import httpx

from src.core.exceptions import LlmException
from src.providers.llm_provider import LlmProvider

logger = logging.getLogger(__name__)


class OpenAiCompatibleLlmProvider(LlmProvider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
        extra_headers: dict[str, str],
        http_transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._extra_headers = extra_headers
        self._http_transport = http_transport

    async def complete_json(self, system: str, user: str) -> str:
        headers = {"Content-Type": "application/json", **self._extra_headers}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        body = {
            "model": self._model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                transport=self._http_transport,
            ) as client:
                response = await client.post(self._url, headers=headers, json=body)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            logger.warning("LLM request failed: %s", type(exc).__name__)
            raise LlmException() from exc

        if response.status_code != 200:
            logger.warning("LLM request failed: status %s", response.status_code)
            raise LlmException()

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("LLM response is not valid JSON")
            raise LlmException() from exc

        content = _extract_content(payload)
        if not isinstance(content, str) or not content.strip():
            logger.warning("LLM response has no content")
            raise LlmException()

        return content


def _extract_content(payload: object) -> object:
    if not isinstance(payload, dict):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    return message.get("content")
