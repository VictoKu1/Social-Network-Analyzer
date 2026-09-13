"""Explicit OpenAI/local Ollama configuration and readiness checks."""

import os

import requests
from openai import OpenAI
from security_limits import MAX_COMPLETION_TOKENS


class LLMError(Exception):
    """An actionable provider error safe to return to the browser."""

    def __init__(self, code, message, status=503):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def resolve_provider(provider=None):
    """Use only the selected provider; never silently fall back to another."""
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "openai")
    if provider not in ("openai", "ollama"):
        raise LLMError("unsupported_provider", "Choose OpenAI or Ollama.", 400)
    return provider


def get_llm_settings():
    """Expose configuration status without exposing credentials or endpoints."""
    default_provider = os.getenv("LLM_PROVIDER", "openai")
    if default_provider not in ("openai", "ollama"):
        default_provider = "openai"
    return {
        "default_provider": default_provider,
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "model": os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o",
        },
        "ollama": {"configured_model": os.getenv("OLLAMA_MODEL", "").strip()},
    }


def _ollama_base_url():
    # This is server configuration, never a URL accepted from the request body.
    base = os.getenv("OLLAMA_BASE_URL", "").strip().rstrip("/")
    base = base or "http://127.0.0.1:11434"
    return base[:-3] if base.endswith("/v1") else base


def get_ollama_models():
    """List models already installed in the configured Ollama instance."""
    try:
        # Local requests should not use a machine's HTTP proxy or netrc credentials.
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(
                f"{_ollama_base_url()}/api/tags", timeout=(3, 5), allow_redirects=False
            )
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Unexpected model-list response")
            payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Invalid model list")
        models = []
        for entry in payload["models"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise ValueError("Invalid model entry")
            # Ollama can list cloud models and their renamed aliases alongside local files.
            if entry.get("remote_host") or entry.get("remote_model"):
                continue
            name = entry["name"].strip()
            if not name:
                raise ValueError("Empty model name")
            if name not in models:
                models.append(name)
    except (requests.RequestException, ValueError) as exc:
        raise LLMError(
            "ollama_unavailable",
            "Can't connect to Ollama. Start Ollama on the machine running this app, "
            "then refresh models.",
        ) from exc
    if not models:
        raise LLMError(
            "ollama_no_models",
            "No local Ollama models are installed. Pull a local model on the machine running "
            "this app, then refresh models.",
        )
    configured_model = os.getenv("OLLAMA_MODEL", "").strip()
    return {
        "models": models,
        "default_model": configured_model if configured_model in models else models[0],
    }


def resolve_model(provider, model=None):
    """Fail before social scraping when the selected engine cannot be used."""
    if provider == "openai":
        if not get_llm_settings()["openai"]["configured"]:
            raise LLMError(
                "openai_key_missing",
                "OpenAI API key required. Set OPENAI_API_KEY on the server and "
                "restart this app, or choose Ollama.",
            )
        return get_llm_settings()["openai"]["model"]
    available = get_ollama_models()
    selected = model if model is not None else (
        os.getenv("OLLAMA_MODEL", "").strip() or available["default_model"]
    )
    if not isinstance(selected, str) or selected not in available["models"]:
        raise LLMError(
            "ollama_model_missing",
            "The selected Ollama model isn't installed. Refresh models and choose one.",
            400,
        )
    return selected


def create_client(provider):
    """Create the cloud client; local inference uses its own isolated transport."""
    if provider != "openai":
        raise LLMError("unsupported_provider", "Choose OpenAI or Ollama.", 400)
    return OpenAI(
        api_key=os.environ["OPENAI_API_KEY"].strip(),
        base_url="https://api.openai.com/v1",
        timeout=120.0,
        max_retries=0,
    )


def generate_ollama_completion(model, messages):
    """Use Ollama's compatible endpoint without inheriting cloud credentials/proxies."""
    try:
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(
                f"{_ollama_base_url()}/v1/chat/completions",
                json={"model": model, "messages": messages, "stream": False,
                      "max_tokens": MAX_COMPLETION_TOKENS},
                headers={"Authorization": "Bearer ollama"},
                timeout=(3, 180),
                allow_redirects=False,
            )
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("Unexpected completion response")
            payload = response.json()
        choices = payload.get("choices") if isinstance(payload, dict) else None
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ValueError("Invalid completion choices")
        message = choices[0].get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Empty completion")
        return content
    except (requests.RequestException, ValueError) as exc:
        raise LLMError(
            "analysis_failed",
            "Ollama couldn't complete the analysis. Check the local service and try again.",
            502,
        ) from exc
