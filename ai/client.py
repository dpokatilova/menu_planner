import json
import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class AIError(Exception):
    """Помилка виклику AI-провайдера."""

def call_ai_json(system: str, user_prompt: str, timeout: int | None = None) -> dict:
    if timeout is None:
        timeout = _get_timeout()

    providers = _configured_providers()
    if not providers:
        raise AIError("Не налаштовано жодного AI-провайдера")

    last_error = None
    for name, call_provider in providers:
        try:
            return call_provider(system, user_prompt, timeout)
        except AIError as exc:
            logger.warning("AI-провайдер %s не відповів: %s", name, exc)
            last_error = exc

    raise AIError("Усі AI-провайдери недоступні") from last_error


def _call_gemini(system, user_prompt, timeout):
    api_key = os.environ["GEMINI_API_KEY"]
    model = os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    data = _post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        payload=payload,
        timeout=timeout,
    )
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise AIError("Gemini: неочікувана структура відповіді") from None
    return _parse_json_object(text)


def _call_groq(system, user_prompt, timeout):
    api_key = os.environ["GROQ_API_KEY"]
    model = os.environ.get("GROQ_MODEL") or DEFAULT_GROQ_MODEL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    data = _post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload=payload,
        timeout=timeout,
    )
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AIError("Groq: неочікувана структура відповіді") from None
    return _parse_json_object(text)


def _configured_providers():
    providers = []
    if os.environ.get("GEMINI_API_KEY"):
        providers.append(("gemini", _call_gemini))
    if os.environ.get("GROQ_API_KEY"):
        providers.append(("groq", _call_groq))
    return providers


def _get_timeout():
    try:
        return int(os.environ.get("AI_TIMEOUT", DEFAULT_TIMEOUT))
    except ValueError:
        return DEFAULT_TIMEOUT


def _post(url, headers, payload, timeout):
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout:
        raise AIError("тайм-аут") from None
    except requests.RequestException as exc:
        raise AIError(f"помилка мережі ({type(exc).__name__})") from None

    if response.status_code != 200:
        raise AIError(f"HTTP {response.status_code}")

    try:
        return response.json()
    except ValueError:
        raise AIError("відповідь провайдера не є JSON") from None


_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _parse_json_object(text):
    if not isinstance(text, str):
        raise AIError("порожня відповідь моделі")
    text = text.strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1)
    try:
        result = json.loads(text)
    except ValueError:
        raise AIError("модель повернула невалідний JSON") from None
    if not isinstance(result, dict):
        raise AIError("очікувався JSON-об'єкт")
    return result
