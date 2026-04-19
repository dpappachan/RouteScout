"""Runtime configuration loaded from environment (backend/.env).

Keeping config centralized makes it easy to override any knob per-environment
(local vs. staging vs. production) without code changes.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    # CORS allowlist — comma-separated. Use "*" only during local development.
    cors_origins: list[str]

    # Per-IP rate limit for /plan (slowapi syntax, e.g. "20/hour")
    plan_rate_limit: str

    # Global per-day cap across all IPs (safety net on Gemini free tier)
    daily_plan_cap: int

    # Beam width for the optimizer — higher is slower but finds better plans
    beam_width: int

    # Bind address for local dev (uvicorn picks this up if launched from app.main)
    host: str
    port: int


@lru_cache(maxsize=1)
def settings() -> Settings:
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        plan_rate_limit=os.environ.get("PLAN_RATE_LIMIT", "20/hour"),
        daily_plan_cap=int(os.environ.get("DAILY_PLAN_CAP", "200")),
        beam_width=int(os.environ.get("BEAM_WIDTH", "12")),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
