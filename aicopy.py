"""AI copy drafts — generate marketing message drafts via the local LLM (RM0).

Uses the OpenAI-compatible endpoint at config.LLM_URL (llama-swap on
localhost). Model choice: prefer a fast instruct model; fall back to
any available model. No cost, runs on our own hardware.
"""
import requests
import config

# Preferred order; first available wins
PREFERRED_MODELS = ["llama3", "mistral"]

SYSTEM_PROMPT = (
    "You are a concise marketing copywriter for a Malaysian SME audience. "
    "Write short, friendly, honest outreach messages. No hype, no false claims, "
    "no spam trigger words (FREE!!!, ACT NOW, etc.). "
    "Always include one clear call to action. "
    "Output ONLY the message body, no subject line, no markdown, no signatures."
)


def _pick_model() -> str | None:
    try:
        r = requests.get(f"{config.LLM_URL}/v1/models", timeout=15)
        available = [m["id"] for m in r.json().get("data", [])]
    except (requests.RequestException, ValueError, KeyError):
        return None
    for pref in PREFERRED_MODELS:
        if pref in available:
            return pref
    return available[0] if available else None


def is_available() -> bool:
    return _pick_model() is not None


def draft_message(brief: str, channel: str = "email",
                 max_tokens: int = 2000) -> tuple[str | None, str]:
    """Draft an outreach message from a one-line brief.

    Note: reasoning models (e.g. llama3) spend max_tokens on
    internal reasoning first; a small budget leaves content empty. 2000+
    is the safe minimum for these models.

    Returns (draft, error). draft is None on failure; error explains why.
    """
    model = _pick_model()
    if not model:
        return None, f"LLM not reachable at {config.LLM_URL}"

    user_prompt = (
        f"Channel: {channel}\n"
        f"Business goal / brief: {brief}\n"
        f"Write the outreach message for this channel. Keep it under 120 words."
    )
    try:
        r = requests.post(
            f"{config.LLM_URL}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
            timeout=180,  # local inference on cold model can be slow
        )
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        # Reasoning models may return content plus reasoning_content; prefer content
        text = (msg.get("content") or "").strip()
        if not text:
            return None, ("model used all tokens on reasoning — increase max_tokens")
        return text, ""
    except requests.RequestException as e:
        return None, f"LLM request failed: {e}"
    except (KeyError, ValueError) as e:
        return None, f"Unexpected LLM response shape: {e}"
