from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"

load_dotenv(BASE_DIR / ".env")


class Config:
    API_KEY = os.getenv("API_KEY", "").strip()
    API_BASE_URL = os.getenv("API_BASE_URL", "https://api.jiekou.ai/openai").rstrip("/")
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4.1-mini").strip()
    FALLBACK_MODEL_1 = os.getenv("FALLBACK_MODEL_1", "gemini-2.5-flash").strip()
    FALLBACK_MODEL_2 = os.getenv("FALLBACK_MODEL_2", "gpt-4.1").strip()
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "45"))
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
    TEMP_DIR = TEMP_DIR

    @classmethod
    def validate(cls) -> list[str]:
        errors: list[str] = []
        if not cls.API_KEY:
            errors.append("Missing API_KEY.")
        if not cls.API_BASE_URL:
            errors.append("Missing API_BASE_URL.")
        for name in ("PRIMARY_MODEL", "FALLBACK_MODEL_1", "FALLBACK_MODEL_2"):
            if not getattr(cls, name):
                errors.append(f"Missing {name}.")
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return errors
