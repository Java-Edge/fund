import os
import re
from typing import Any

import requests


def is_lmstudio_backend() -> bool:
    api_base = os.getenv("LLM_API_BASE", "")
    return ":1234" in api_base or "lmstudio" in api_base.lower()


def get_lmstudio_chat_options() -> dict[str, Any]:
    options: dict[str, Any] = {}

    enable_thinking = os.getenv("LLM_ENABLE_THINKING")
    if enable_thinking is not None:
        options["enable_thinking"] = enable_thinking.strip().lower() in {"1", "true", "yes", "on"}

    reasoning_effort = os.getenv("LLM_REASONING_EFFORT")
    if reasoning_effort:
        options["reasoning"] = {"effort": reasoning_effort}

    return options


def build_raw_chat_payload(messages: list[dict[str, Any]], *, max_tokens: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
        "messages": messages,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    payload.update(get_lmstudio_chat_options())
    return payload


def extract_reasoning_parts(response_json: dict[str, Any]) -> dict[str, Any]:
    choices = response_json.get("choices") or []
    message = ((choices[0] or {}).get("message") or {}) if choices else {}

    content = message.get("content") or ""
    reasoning = (
        message.get("reasoning_content")
        or message.get("reasoning")
        or ((choices[0] or {}).get("delta") or {}).get("reasoning")
        or ""
    )

    return {
        "content": content,
        "reasoning_content": reasoning,
        "finish_reason": (choices[0] or {}).get("finish_reason") if choices else None,
        "usage": response_json.get("usage", {}),
        "raw_message": message,
        "raw_response": response_json,
    }


def call_lmstudio_raw(messages: list[dict[str, Any]], *, max_tokens: int | None = None, timeout: int = 120) -> dict[str, Any]:
    api_base = os.getenv("LLM_API_BASE", "http://localhost:1234/v1").rstrip("/")
    api_key = os.getenv("LLM_API_KEY", "lm-studio")
    response = requests.post(
        f"{api_base}/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json=build_raw_chat_payload(messages, max_tokens=max_tokens),
        timeout=timeout,
    )
    response.raise_for_status()
    return extract_reasoning_parts(response.json())


def should_fallback_to_reasoning() -> bool:
    value = os.getenv("LLM_DEBUG_FALLBACK_TO_REASONING", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def extract_html_from_reasoning(reasoning_content: str) -> str:
    if not reasoning_content:
        return ""

    candidates = [
        reasoning_content.replace('\\"', '"').replace("\\n", "\n"),
        reasoning_content,
    ]

    for candidate in candidates:
        if "<p" not in candidate and "<ul" not in candidate:
            continue

        start_positions = [pos for pos in [candidate.find("<p"), candidate.find("<ul")] if pos != -1]
        if not start_positions:
            continue
        start = min(start_positions)

        end_candidates = []
        for closing in ("</ul>", "</p>", "</ol>", "</div>"):
            pos = candidate.rfind(closing)
            if pos != -1:
                end_candidates.append((pos + len(closing), closing))

        if end_candidates:
            end = max(end_candidates, key=lambda item: item[0])[0]
            html = candidate[start:end].strip()
        else:
            html = candidate[start:].strip()

        if re.search(r"<(p|ul|li|span)\b", html):
            return html

    return ""
