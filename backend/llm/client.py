"""Shared Gemini client — loads the key from backend/.env and exposes a
module-level singleton."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google import genai

MODEL_ID = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite").strip()


@lru_cache(maxsize=1)
def client() -> genai.Client:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            f"GEMINI_API_KEY is missing from {env_path}. Paste your key there."
        )
    return genai.Client(api_key=api_key)
