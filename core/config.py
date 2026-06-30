"""
core/config.py — Centralised configuration with validation, python-dotenv,
caching with hot-reload, secret masking, and source tracking.

v2.5: Uses python-dotenv, tracks secret sources, enforces masking.
"""

from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.constants import CONFIG_PATH, ENV_PATH, PROJECT_ROOT
from core.logger import get_logger

logger = get_logger(__name__)


# ── AppConfig Dataclass ──────────────────────────────────────────────────────

@dataclass
class AppConfig:
    """Typed, validated application configuration."""

    bio: str = "Web Developer"
    gpt_preamble: str = ""
    gpt_token_limit: int = 700
    api_provider: str = "auto"
    openrouter_api_key: str = ""
    gemini_api_key: str = ""
    open_ai_api_key: str = ""
    cookies: dict[str, str] = field(default_factory=dict)
    hour_interval: int = 24
    random_hour_offset: int = 3
    random_min_offset: int = 25
    num_recent_posts: int = 3
    scrape_char_limit: int = 4000
    websites: list[str] = field(default_factory=list)

    # Source tracking: which secrets came from .env vs config.json
    _secret_sources: dict[str, str] = field(default_factory=dict, repr=False)

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_dict(cls, data: dict[str, Any], secret_sources: dict[str, str] | None = None) -> AppConfig:
        """Build config from a dict, ignoring unknown keys."""
        known = {f.name for f in cls.__dataclass_fields__.values() if not f.name.startswith("_")}
        cfg = cls(**{k: v for k, v in data.items() if k in known})
        if secret_sources:
            cfg._secret_sources = secret_sources
        return cfg

    # ── Validation ───────────────────────────────────────────────────────

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if not self.cookies.get("li_at"):
            errors.append("Missing LinkedIn 'li_at' cookie — add LINKEDIN_LI_AT to .env")
        if not self.cookies.get("JSESSIONID"):
            errors.append("Missing LinkedIn 'JSESSIONID' cookie — add LINKEDIN_JSESSIONID to .env")
        if not any([self.openrouter_api_key, self.gemini_api_key, self.open_ai_api_key]):
            errors.append("No AI API keys configured — add at least one to .env")
        return errors

    def mask_key(self, key: str) -> str:
        """Mask an API key for display: show first 4 + last 4 chars."""
        if not key:
            return "(not set)"
        if len(key) <= 10:
            return "****"
        return f"{key[:4]}····{key[-4:]}"

    def get_secret_source(self, key: str) -> str:
        """Return where a secret was loaded from: '.env', 'config.json', or 'not set'."""
        return self._secret_sources.get(key, "not set")

    def secrets_in_config_json(self) -> list[str]:
        """Return list of secrets that are sourced from config.json (not .env)."""
        return [k for k, v in self._secret_sources.items() if v == "config.json"]

    @property
    def has_openai(self) -> bool:
        return bool(self.open_ai_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_openrouter(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def has_linkedin(self) -> bool:
        return bool(self.cookies.get("li_at") and self.cookies.get("JSESSIONID"))


# ── Config Loading with .env Override & Caching ──────────────────────────────

_cached_config: AppConfig | None = None
_cached_mtime: float = 0.0


def load_config(path: Path = CONFIG_PATH, force: bool = False) -> AppConfig:
    """
    Load config from JSON, with .env overrides for secrets.

    Priority: .env > config.json
    Caches the result and only re-reads if the file mtime has changed.
    """
    global _cached_config, _cached_mtime

    try:
        mtime = path.stat().st_mtime if path.exists() else 0.0
    except OSError:
        mtime = 0.0

    if not force and _cached_config is not None and mtime == _cached_mtime:
        return _cached_config

    # Load .env with python-dotenv (does NOT overwrite existing env vars)
    load_dotenv(ENV_PATH, override=False)

    # Load JSON config
    data: dict[str, Any] = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to read config.json: %s", e)

    # Track where each secret comes from
    secret_sources: dict[str, str] = {}
    _ENV_MAP = {
        "openrouter_api_key": "OPENROUTER_API_KEY",
        "gemini_api_key": "GEMINI_API_KEY",
        "open_ai_api_key": "OPENAI_API_KEY",
    }

    for config_key, env_key in _ENV_MAP.items():
        env_val = os.environ.get(env_key)
        json_val = data.get(config_key, "")

        if env_val:
            data[config_key] = env_val
            secret_sources[config_key] = ".env"
        elif json_val:
            secret_sources[config_key] = "config.json"
            logger.warning(
                "⚠ Secret '%s' loaded from config.json — move to .env for security",
                config_key,
            )

    # LinkedIn cookies from env
    li_at_env = os.environ.get("LINKEDIN_LI_AT")
    jsession_env = os.environ.get("LINKEDIN_JSESSIONID")
    cookies = data.get("cookies", {})

    if li_at_env:
        cookies["li_at"] = li_at_env
        secret_sources["li_at"] = ".env"
    elif cookies.get("li_at"):
        secret_sources["li_at"] = "config.json"
        logger.warning("⚠ LinkedIn 'li_at' cookie in config.json — move to .env")

    if jsession_env:
        cookies["JSESSIONID"] = jsession_env
        secret_sources["JSESSIONID"] = ".env"
    elif cookies.get("JSESSIONID"):
        secret_sources["JSESSIONID"] = "config.json"

    data["cookies"] = cookies

    config = AppConfig.from_dict(data, secret_sources)
    _cached_config = config
    _cached_mtime = mtime
    return config


def invalidate_config_cache() -> None:
    """Force the next load_config() call to re-read from disk."""
    global _cached_config, _cached_mtime
    _cached_config = None
    _cached_mtime = 0.0


# ── Utility ──────────────────────────────────────────────────────────────────

def get_content_type(file_path: str | Path) -> str | None:
    """Guess MIME type for a file path."""
    content_type, _ = mimetypes.guess_type(str(file_path))
    return content_type
