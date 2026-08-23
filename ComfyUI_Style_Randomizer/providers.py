"""Registry of LLM providers and a single dispatch function to call any of them.

Anthropic is paid-only; Gemini, Groq, and OpenRouter each have a usable free
tier (subject to the provider's own rate limits and model availability).
"""

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"
ANTHROPIC_VERSION = "2023-06-01"
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

MAX_TOKENS = 4000
TIMEOUT = 60

PROVIDERS = {
    "anthropic": {
        "label": "Anthropic (Claude)",
        "key_config": "anthropic_api_key",
        "key_hint": "console.anthropic.com — paid API, no free tier",
        "key_url": "https://console.anthropic.com/settings/keys",
        "models": [
            ("claude-sonnet-5", "Claude Sonnet 5"),
            ("claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
        ],
    },
    "gemini": {
        "label": "Google Gemini",
        "key_config": "gemini_api_key",
        "key_hint": "aistudio.google.com/apikey — generous free tier",
        "key_url": "https://aistudio.google.com/apikey",
        "models": [
            ("gemini-2.5-flash", "Gemini 2.5 Flash"),
            ("gemini-2.0-flash", "Gemini 2.0 Flash"),
            ("gemini-2.0-flash-lite", "Gemini 2.0 Flash-Lite"),
        ],
    },
    "groq": {
        "label": "Groq",
        "key_config": "groq_api_key",
        "key_hint": "console.groq.com/keys — free, very fast open-model inference",
        "key_url": "https://console.groq.com/keys",
        "models": [
            ("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile"),
            ("llama-3.1-8b-instant", "Llama 3.1 8B Instant"),
            ("gemma2-9b-it", "Gemma2 9B IT"),
        ],
    },
    "openrouter": {
        "label": "OpenRouter",
        "key_config": "openrouter_api_key",
        "key_hint": "openrouter.ai/keys — pick a model tagged :free (list changes often)",
        "key_url": "https://openrouter.ai/keys",
        "models": [
            ("deepseek/deepseek-chat-v3.1:free", "DeepSeek Chat v3.1 (free)"),
            ("meta-llama/llama-3.3-70b-instruct:free", "Llama 3.3 70B Instruct (free)"),
            ("google/gemma-3-27b-it:free", "Gemma 3 27B IT (free)"),
            ("mistralai/mistral-small-3.2-24b-instruct:free", "Mistral Small 3.2 24B (free)"),
        ],
    },
}


class LLMError(Exception):
    pass


def _extract_openai_style_text(data: dict) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return (message.get("content") or "").strip()


def _call_anthropic(model: str, api_key: str, system_prompt: str, user_message: str) -> str:
    try:
        resp = requests.post(
            ANTHROPIC_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise LLMError(f"Request failed: {e}")

    if resp.status_code != 200:
        raise LLMError(f"API error {resp.status_code}: {_error_detail(resp)}")

    try:
        data = resp.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", [])
            if block.get("type") == "text"
        ).strip()
    except ValueError as e:
        raise LLMError(f"Could not parse response: {e}")

    return text


def _call_gemini(model: str, api_key: str, system_prompt: str, user_message: str) -> str:
    url = GEMINI_URL_TMPL.format(model=model)
    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise LLMError(f"Request failed: {e}")

    if resp.status_code != 200:
        raise LLMError(f"API error {resp.status_code}: {_error_detail(resp)}")

    try:
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason", "")
            raise LLMError(f"No response candidates{f' (blocked: {reason})' if reason else ''}.")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
    except ValueError as e:
        raise LLMError(f"Could not parse response: {e}")

    return text


def _call_openai_style(url: str, model: str, api_key: str, system_prompt: str,
                        user_message: str, extra_headers: dict | None = None) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "content-type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        resp = requests.post(
            url,
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        raise LLMError(f"Request failed: {e}")

    if resp.status_code != 200:
        raise LLMError(f"API error {resp.status_code}: {_error_detail(resp)}")

    try:
        text = _extract_openai_style_text(resp.json())
    except ValueError as e:
        raise LLMError(f"Could not parse response: {e}")

    return text


def _error_detail(resp: requests.Response) -> str:
    try:
        data = resp.json()
        err = data.get("error", {})
        if isinstance(err, dict):
            return err.get("message", "") or str(data)[:300]
        return str(err)[:300]
    except ValueError:
        return resp.text[:300]


def _get_json(url: str, headers: dict | None = None, params: dict | None = None) -> dict:
    try:
        resp = requests.get(url, headers=headers or {}, params=params or {}, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise LLMError(f"Request failed: {e}")
    if resp.status_code != 200:
        raise LLMError(f"API error {resp.status_code}: {_error_detail(resp)}")
    try:
        return resp.json()
    except ValueError as e:
        raise LLMError(f"Could not parse response: {e}")


def _list_anthropic_models(api_key: str) -> list[tuple[str, str]]:
    data = _get_json(ANTHROPIC_MODELS_URL, headers={
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
    })
    return [(m["id"], m.get("display_name", m["id"])) for m in data.get("data", [])]


def _list_gemini_models(api_key: str) -> list[tuple[str, str]]:
    data = _get_json(GEMINI_MODELS_URL, params={"key": api_key, "pageSize": 1000})
    models = []
    for m in data.get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        name = m.get("name", "")
        model_id = name.split("/", 1)[1] if "/" in name else name
        models.append((model_id, m.get("displayName", model_id)))
    return models


def _list_openai_style_models(url: str, api_key: str) -> list[tuple[str, str]]:
    data = _get_json(url, headers={"Authorization": f"Bearer {api_key}"})
    models = sorted(m["id"] for m in data.get("data", []))
    return [(m, m) for m in models]


def _list_openrouter_models(api_key: str) -> list[tuple[str, str]]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key.strip() else {}
    data = _get_json(OPENROUTER_MODELS_URL, headers=headers)
    free = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        pricing = m.get("pricing", {})
        is_free = model_id.endswith(":free") or (
            pricing.get("prompt") == "0" and pricing.get("completion") == "0"
        )
        if is_free:
            free.append((model_id, m.get("name", model_id)))
    return free


def list_models(provider_id: str, api_key: str) -> list[tuple[str, str]]:
    """Fetches the live list of (model_id, label) pairs available for a
    provider. For OpenRouter this is filtered down to free-tagged models
    only, since that's the whole point of listing them here.

    Raises LLMError with a user-facing message on any failure.
    """
    if provider_id != "openrouter" and not api_key.strip():
        raise LLMError("No API key set for this provider — add one in Settings.")

    if provider_id == "anthropic":
        models = _list_anthropic_models(api_key)
    elif provider_id == "gemini":
        models = _list_gemini_models(api_key)
    elif provider_id == "groq":
        models = _list_openai_style_models(GROQ_MODELS_URL, api_key)
    elif provider_id == "openrouter":
        models = _list_openrouter_models(api_key)
    else:
        raise LLMError(f"Unknown provider: {provider_id}")

    if not models:
        raise LLMError("No models returned by the provider.")
    return models


def call_llm(provider_id: str, model: str, api_key: str, system_prompt: str, user_message: str) -> str:
    """Calls the given provider/model and returns the generated text.

    Raises LLMError with a user-facing message on any failure.
    """
    if not api_key.strip():
        raise LLMError("No API key set for this provider — add one in Settings.")

    if provider_id == "anthropic":
        text = _call_anthropic(model, api_key, system_prompt, user_message)
    elif provider_id == "gemini":
        text = _call_gemini(model, api_key, system_prompt, user_message)
    elif provider_id == "groq":
        text = _call_openai_style(GROQ_URL, model, api_key, system_prompt, user_message)
    elif provider_id == "openrouter":
        text = _call_openai_style(
            OPENROUTER_URL, model, api_key, system_prompt, user_message,
            extra_headers={"X-Title": "ComfyUI Style Randomizer"},
        )
    else:
        raise LLMError(f"Unknown provider: {provider_id}")

    if not text:
        raise LLMError("Empty response from API.")
    return text
