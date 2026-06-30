"""
core/constants.py — Central constants for the LinkedIn Post Automator.
All magic numbers, enums, and paths live here.
"""

from enum import Enum
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
CORE_DIR = PROJECT_ROOT / "core"
MEDIA_DIR = PROJECT_ROOT / "media"
GENERATED_DIR = MEDIA_DIR / "generated"
FONTS_DIR = MEDIA_DIR / "fonts"
CONFIG_PATH = PROJECT_ROOT / "config.json"
ENV_PATH = PROJECT_ROOT / ".env"
DB_PATH = PROJECT_ROOT / "automator.db"
LOG_PATH = PROJECT_ROOT / "automator.log"
HEARTBEAT_PATH = PROJECT_ROOT / "daemon_heartbeat.json"


# ── Enums ─────────────────────────────────────────────────────────────────────

class PostStatus(str, Enum):
    """Post lifecycle states."""
    DRAFT = "DRAFT"
    QUEUED = "QUEUED"
    POSTED = "POSTED"
    FAILED = "FAILED"
    DELETED = "DELETED"


class MediaCategory(str, Enum):
    """LinkedIn media upload categories (fixed — no trailing comma bug)."""
    IMAGE = "IMAGE"


class ImageModel(str, Enum):
    """Available image generation backends."""
    AUTO = "auto"
    INFOGRAPHIC = "infographic"
    DALL_E_3 = "dall-e-3"
    GEMINI = "gemini"
    POLLINATIONS = "pollinations"


class TextProvider(str, Enum):
    """Available LLM providers for text generation."""
    AUTO = "auto"
    OPENAI = "openai"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"


# ── Limits ────────────────────────────────────────────────────────────────────

LINKEDIN_CHAR_LIMIT = 3000
DEFAULT_TOKEN_LIMIT = 700
DEFAULT_IMAGE_TOKEN_LIMIT = 120
INFOGRAPHIC_TOKEN_LIMIT = 600
DAEMON_POLL_INTERVAL = 60          # seconds
DAEMON_MIN_POST_GAP = 300          # 5 minutes between consecutive posts
DAEMON_MAX_RETRIES = 3
SCRAPE_CHAR_LIMIT = 4000
SCRAPER_TIMEOUT = 10               # seconds
MAX_SCRAPER_WORKERS = 5

# ── DB Schema Version ────────────────────────────────────────────────────────

DB_SCHEMA_VERSION = 2              # Increment when adding migrations
