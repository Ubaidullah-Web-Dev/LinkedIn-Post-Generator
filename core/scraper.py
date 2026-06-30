"""
core/scraper.py — Web/RSS content scraper.

v2 improvements:
- Logging instead of print()
- Type hints throughout
- Timeout on feedparser via requests fallback
"""

from __future__ import annotations

import random
import re

import feedparser
import requests
from bs4 import BeautifulSoup
from feedparser import FeedParserDict

from core.logger import get_logger

logger = get_logger(__name__)


class Scraper:
    """Fetches and cleans text content from web pages or RSS feeds."""

    def __init__(self, url: str, character_limit: int = 2000) -> None:
        self.url = url
        self.character_limit = character_limit

    def fetch_content(self) -> str | None:
        """Fetch content from URL (auto-detects RSS vs HTML)."""
        try:
            # 1) Try RSS feed first
            feed = feedparser.parse(self.url)
            if not feed.bozo and feed.entries:
                return self.rss_parse(feed)

            # 2) Fallback to HTML scraping
            resp = requests.get(self.url, timeout=10)
            resp.raise_for_status()
            return self.parse(resp.text)

        except Exception as e:
            logger.warning("Scrape failed for %s: %s", self.url, e)
            return None

    def parse(self, content: str) -> str:
        """Extract clean text from HTML content."""
        soup = BeautifulSoup(content, "html.parser")

        # Remove non-content elements
        for element in soup.find_all(["nav", "header", "footer", "aside"]):
            element.decompose()

        for script in soup(["script", "style"]):
            script.extract()

        all_text = soup.get_text()
        lines = (line.strip() for line in all_text.splitlines())
        clean = re.sub(r"\s+", " ", " ".join(line for line in lines if line))

        return clean[: self.character_limit]

    def rss_parse(self, feed: FeedParserDict) -> str | None:
        """Extract text from a random RSS feed entry."""
        if not feed.entries:
            return None

        entry = random.choice(feed.entries)

        raw = (
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
            or (
                entry.content[0].value
                if getattr(entry, "content", None)
                else None
            )
            or entry.title
        )
        if raw is None:
            return None

        text = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
        return text[: self.character_limit]
