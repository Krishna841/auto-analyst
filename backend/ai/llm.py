"""
Shared LLM client: Ollama (default, free local) with optional OpenAI fallback.
"""

from __future__ import annotations

import os
from typing import Any


def get_default_model() -> str:
    """Ollama model name. Set OLLAMA_MODEL env or use a sensible default."""
    return os.environ.get("OLLAMA_MODEL", "llama3.2")


def chat(messages: list[dict[str, str]], model: str | None = None) -> str | None:
    """
    Send messages to the LLM and return the assistant reply text.
    Uses Ollama by default (local, free). Returns None on failure.
    """
    model = model or get_default_model()
    # Prefer Ollama (free, local)
    try:
        from ollama import Client
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        client = Client(host=host)
        response = client.chat(model=model, messages=messages)
        if response and isinstance(response.get("message"), dict):
            return (response["message"].get("content") or "").strip()
        return None
    except Exception:
        pass
    # Optional: OpenAI fallback if key is set and Ollama failed
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI  # pip install openai
            client = OpenAI(api_key=api_key)
            r = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                max_tokens=500,
            )
            return (r.choices[0].message.content or "").strip() if r.choices else None
        except Exception:
            pass
    return None
