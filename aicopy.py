"""AI copy drafts — generate marketing message drafts via a configurable LLM.

Providers are stored in the database (LlmProvider) and can be any
OpenAI-compatible chat-completions endpoint:
  - local: llama.cpp server, Ollama, llama-swap (no API key needed)
  - cloud: OpenAI, OpenRouter, Groq, etc. (needs an API key)

The first provider marked is_default is used when the caller does not pick one.
If the DB has no providers yet, config.LLM_URL is used as a built-in fallback
so the tool works out of the box.

Pitfall handled: reasoning models (e.g. llama3) spend max_tokens on
internal reasoning first; a small budget leaves `content` empty. 2000+ tokens
is the safe minimum for these models.

Pitfall handled: llama-swap returns 502 Bad Gateway while a cold model is
loading/swapping. We retry a few times with a short backoff before giving up.
"""
import time
import requests

import config

SYSTEM_PROMPT = (
    "You are a concise marketing copywriter for a Malaysian SME audience. "
    "Write short, friendly, honest outreach messages. No hype, no false claims, "
    "no spam trigger words (FREE!!!, ACT NOW, etc.). "
    "Always include one clear call to action. "
    "Output ONLY the message body, no subject line, no markdown, no signatures."
)

# Preferred order when auto-picking a model from a provider's list
PREFERRED_MODELS = ["llama3", "mistral"]

RETRIES = 3
RETRY_BACKOFF_S = 4


def _norm_base(base_url: str) -> str:
    """Normalize a base URL to end with /v1 (OpenAI-compatible convention)."""
    base = (base_url or "").rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base


def _headers(api_key: str) -> dict:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def list_models(provider) -> tuple[list[str], str]:
    """List model ids from a provider. Returns (models, error)."""
    try:
        r = requests.get(f"{_norm_base(provider.base_url)}/models",
                        headers=_headers(provider.api_key), timeout=15)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])], ""
    except requests.RequestException as e:
        return [], f"Cannot reach provider: {e}"
    except (ValueError, KeyError):
        return [], "Unexpected response from /models endpoint"


def pick_model(provider, models: list[str]) -> str | None:
    """Pick the provider's default model, else a preferred one, else the first."""
    if provider.default_model and provider.default_model in models:
        return provider.default_model
    for pref in PREFERRED_MODELS:
        if pref in models:
            return pref
    return models[0] if models else None


def draft_message(brief: str, channel: str = "email",
                 provider=None, model: str | None = None,
                 max_tokens: int = 2000) -> tuple[str | None, str]:
    """Draft an outreach message from a one-line brief.

    provider: an LlmProvider instance. If None, uses the default provider
              (or the built-in config.LLM_URL fallback).
    model:    explicit model id; auto-picked if None.
    Returns (draft, error). draft is None on failure; error explains why.
    """
    if provider is None:
        provider = _default_provider()
    if provider is None:
        return None, "No LLM provider configured. Add one in Settings -> LLM Providers."

    if model is None:
        models, err = list_models(provider)
        if not models:
            return None, err
        model = pick_model(provider, models)
    if not model:
        return None, "Provider has no models available."

    user_prompt = (
        f"Channel: {channel}\n"
        f"Business goal / brief: {brief}\n"
        f"Write the outreach message for this channel. Keep it under 120 words."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    last_err = ""
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.post(
                f"{_norm_base(provider.base_url)}/chat/completions",
                json=payload, headers=_headers(provider.api_key),
                timeout=180,  # local inference on a cold model can be slow
            )
            if r.status_code == 502 and attempt < RETRIES:
                # Cold model swap (llama-swap) — wait and retry
                last_err = "502 Bad Gateway (model loading?)"
                time.sleep(RETRY_BACKOFF_S * attempt)
                continue
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text:
                return None, "Model used all tokens on reasoning — increase max_tokens."
            return text, ""
        except requests.RequestException as e:
            last_err = f"LLM request failed: {e}"
            if attempt < RETRIES:
                time.sleep(RETRY_BACKOFF_S * attempt)
        except (KeyError, ValueError) as e:
            return None, f"Unexpected LLM response shape: {e}"
    return None, last_err


def _default_provider():
    """Return the default provider from DB, or a built-in fallback from config."""
    from models import LlmProvider
    p = LlmProvider.query.filter_by(is_default=True).first()
    if p:
        return p
    p = LlmProvider.query.first()
    if p:
        return p
    if config.LLM_URL:
        # Ephemeral fallback object (not persisted) so the tool works out of the box
        return LlmProvider(name="Default (config LLM_URL)",
                          base_url=config.LLM_URL, api_key="", default_model="")
    return None
