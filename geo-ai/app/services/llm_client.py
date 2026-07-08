"""Shared DeepSeek (OpenAI-compatible) LLM client.

Every agent that needs an LLM call must go through this wrapper — never
duplicate raw HTTP calls to DeepSeek elsewhere. Handles timeout, exponential
backoff retry, rate-limit (HTTP 429) backoff, and optional JSON response
validation with a one-shot strict retry on parse failure.
"""

import asyncio
import json
import re
from typing import Any, TypeVar

import httpx
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.utils.exceptions import ExternalServiceError

T = TypeVar("T", bound=BaseModel)

STRICT_JSON_SUFFIX = (
    "\n\nIMPORTANT: Return ONLY valid JSON matching the requested schema. "
    "No markdown fences, no commentary, no text before or after the JSON object."
)


class LLMClient:
    """Thin async wrapper around DeepSeek chat completions."""

    def __init__(self) -> None:
        self._base_url = settings.DEEPSEEK_BASE_URL.rstrip("/")
        self._api_key = settings.DEEPSEEK_API_KEY
        self._model = settings.DEEPSEEK_MODEL
        self._timeout = settings.LLM_TIMEOUT_SECONDS
        self._max_retries = settings.LLM_MAX_RETRIES
        self._base_delay = settings.LLM_RETRY_BASE_DELAY_SECONDS

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant message text.

        Inputs: OpenAI-style messages list, optional temperature/max_tokens.
        Outputs: assistant response content (str).
        Raises: ExternalServiceError after retries are exhausted.
        """
        if not self._api_key:
            raise ExternalServiceError("DEEPSEEK_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = f"{self._base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", self._base_delay * attempt))
                        logger.warning(f"LLM rate limited (429), backing off {retry_after:.1f}s")
                        await asyncio.sleep(retry_after)
                        continue
                    response.raise_for_status()
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(f"LLM chat_completion attempt {attempt}/{self._max_retries} failed: {exc!r}")
                if attempt < self._max_retries:
                    delay = self._base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        raise ExternalServiceError(
            f"LLM chat_completion failed after {self._max_retries} attempts: {last_error}"
        ) from last_error

    async def chat_completion_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        *,
        temperature: float = 0.1,
        strict_on_failure: bool = True,
    ) -> T:
        """Call the LLM and parse/validate the response against a Pydantic schema.

        On parse/validation failure, retries once with a stricter JSON-only
        instruction appended to the last user message.
        """
        attempts = 2 if strict_on_failure else 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            msgs = list(messages)
            if attempt > 1:
                msgs = msgs.copy()
                if msgs and msgs[-1]["role"] == "user":
                    msgs[-1] = {
                        "role": "user",
                        "content": msgs[-1]["content"] + STRICT_JSON_SUFFIX,
                    }
                else:
                    msgs.append({"role": "user", "content": STRICT_JSON_SUFFIX.strip()})
                logger.warning(f"LLM JSON parse failed, retrying with strict instruction (attempt {attempt})")

            raw = await self.chat_completion(msgs, temperature=temperature)
            try:
                parsed = _extract_json_object(raw)
                return schema.model_validate(parsed)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                logger.warning(f"LLM response JSON validation failed: {exc!r}")

        raise ExternalServiceError(f"LLM response is not valid JSON for {schema.__name__}: {last_error}")


def _extract_json_object(text: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


# Module-level singleton — import and use this rather than instantiating per call.
llm_client = LLMClient()
