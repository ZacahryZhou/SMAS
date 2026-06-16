from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from config import settings


class DeepSeekError(RuntimeError):
    pass


class TruncatedJsonError(DeepSeekError):
    pass


class DeepSeekClient:
    def __init__(self) -> None:
        if not settings.deepseek_api_key:
            raise DeepSeekError(
                "DEEPSEEK_API_KEY is missing. Copy .env.example to .env and add your key."
            )
        self._client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def chat(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model or settings.deepseek_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        if choice.finish_reason == "length":
            raise TruncatedJsonError("Model output was truncated. Increase max_tokens and retry.")
        return content.strip()

    def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        retries: int = 2,
    ) -> dict[str, Any]:
        json_system = (
            f"{system}\n\n"
            "You must respond with valid json only. "
            "Do not wrap the json in markdown fences."
        )
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                raw = self.chat(
                    system=json_system,
                    user=user,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return json.loads(raw)
            except (json.JSONDecodeError, TruncatedJsonError) as exc:
                last_error = exc
                if attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise DeepSeekError(f"Failed to parse JSON from DeepSeek: {exc}") from exc

        raise DeepSeekError(str(last_error))


def ping() -> str:
    client = DeepSeekClient()
    return client.chat(
        system="Reply with one short sentence.",
        user="Say hello in English.",
        max_tokens=32,
        temperature=0.2,
    )
