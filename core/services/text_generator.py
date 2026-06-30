"""
core/services/text_generator.py — AI-powered LinkedIn post text generation.

12 personas (expanded from 4), duplicate prevention via post history,
user preamble as primary instruction, and post validation.
"""

from __future__ import annotations

import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.llm.gateway import LLMGateway
from core.config import AppConfig
from core.database import QueueManager
from core.scraper import Scraper
from core.services.formatter import format_for_linkedin, validate_post
from core.logger import get_logger

logger = get_logger(__name__)

# ── Personas (expanded to 12) ────────────────────────────────────────────────

PERSONAS = [
    {
        "name": "The Contrarian Take",
        "instruction": "Start with an unpopular opinion about modern web development "
        "(e.g. against a popular framework, CSS approach, or architecture). "
        "Prove it with a real technical example from your experience, and end "
        "with a question to your network.",
    },
    {
        "name": "The Post-Mortem",
        "instruction": "Tell a short story about a technical failure, production bug, "
        "or architecture mistake you caused. Explain the technical root cause "
        "simply, and list 3 specific things you learned.",
    },
    {
        "name": "The Deep Dive",
        "instruction": "Explain a complex web dev concept (like React reconciliation, "
        "SQL indexing, or Event Loop) using a simple, real-world non-programming "
        "analogy. Make it highly educational.",
    },
    {
        "name": "The Workflow Hack",
        "instruction": "Share a specific, niche productivity tip or tool you use daily "
        "(like a TypeScript trick, a Git alias, or an obscure CSS property). "
        "Show exactly how it saves time.",
    },
    {
        "name": "The Code Review",
        "instruction": "Walk through a real code change you made recently — explain what "
        "the code looked like before, what you changed, and why. Focus on the "
        "reasoning, not just the syntax.",
    },
    {
        "name": "The Career Reflection",
        "instruction": "Share a meaningful career milestone, turning point, or lesson "
        "you learned the hard way. Be vulnerable and specific. End with advice "
        "for junior developers.",
    },
    {
        "name": "The Tool Discovery",
        "instruction": "Review a dev tool, library, or service you recently discovered "
        "that changed your workflow. Give a specific before/after comparison "
        "of how it improved your work.",
    },
    {
        "name": "The Myth Buster",
        "instruction": "Debunk a common web development myth or misconception with "
        "concrete evidence from your experience. Be provocative but fair.",
    },
    {
        "name": "The Behind-the-Scenes",
        "instruction": "Share a day-in-the-life moment from your development work — "
        "a debugging session, a code review discussion, or an architecture "
        "decision meeting. Make it relatable.",
    },
    {
        "name": "The Hot Take",
        "instruction": "Share a strong, defensible opinion about a current industry "
        "trend (AI in dev, framework wars, remote work, etc.). Take a clear "
        "side and support it with experience.",
    },
    {
        "name": "The Tutorial Teaser",
        "instruction": "Give a micro-tutorial teaching one specific technique in under "
        "10 lines of pseudocode. Make it immediately applicable and explain "
        "the 'aha' moment.",
    },
    {
        "name": "The Numbers Game",
        "instruction": "Share real metrics or statistics from a project you worked on "
        "(performance improvements, bundle size reduction, load time optimization). "
        "Numbers tell stories.",
    },
]


# ── Text Generator ───────────────────────────────────────────────────────────

class TextGenerator:
    """Generates LinkedIn post text using AI with persona rotation and context."""

    def __init__(self, llm: LLMGateway, config: AppConfig) -> None:
        self._llm = llm
        self._config = config

    def generate(self, provider: str = "auto") -> tuple[bool, str, str]:
        """
        Generate a LinkedIn post.

        Returns (success, formatted_text_or_error, persona_name).
        """
        persona = random.choice(PERSONAS)
        user_preamble = self._config.gpt_preamble

        preamble = self._build_preamble(persona, user_preamble)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": preamble},
            {"role": "user", "content": f"My Bio & Context: {self._config.bio}"},
        ]

        # Inject recent post history (prevents duplicates)
        if self._config.num_recent_posts > 0:
            try:
                db = QueueManager()
                recent = db.get_recent_content(self._config.num_recent_posts)
                if recent:
                    history = "\n---\n".join(recent)
                    messages.append({
                        "role": "user",
                        "content": (
                            "IMPORTANT: Here are my recent LinkedIn posts. "
                            "Do NOT repeat similar themes, hooks, or topics:\n"
                            f"{history}"
                        ),
                    })
            except Exception as e:
                logger.warning("Could not load post history: %s", e)

        # Scrape website content if configured
        if self._config.websites:
            scraped = self._fetch_websites()
            for content in scraped[:3]:  # Limit context size
                messages.append({
                    "role": "user",
                    "content": f"Context to include if relevant: {content}",
                })

        success, result = self._llm.ask(
            messages,
            self._config.gpt_token_limit,
            provider=provider,
        )

        if not success:
            return False, result, persona["name"]

        formatted = format_for_linkedin(result)

        # Validate the post
        valid, msg = validate_post(formatted)
        if not valid:
            logger.warning("Post validation failed: %s", msg)
            # Still return it — let the user decide
            return True, formatted, persona["name"]

        return True, formatted, persona["name"]

    def improve(self, text: str, action: str = "improve") -> tuple[bool, str]:
        """Apply an AI transformation to existing text."""
        prompts = {
            "improve": "Improve this LinkedIn post. Make it more engaging, fix any awkward phrasing, and ensure it has a strong hook. Keep the same length and topic. Return ONLY the improved post text.",
            "viral": "Rewrite this LinkedIn post to maximize virality. Use a controversial hook, add a plot twist, make it emotionally compelling. Keep under 1800 characters. Return ONLY the rewritten post text.",
            "shorten": "Shorten this LinkedIn post to under 1000 characters while keeping the core message and impact. Return ONLY the shortened post text.",
            "expand": "Expand this LinkedIn post with more detail, examples, and depth. Keep under 2500 characters. Return ONLY the expanded post text.",
        }

        system_msg = prompts.get(action, prompts["improve"])
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": text},
        ]

        success, result = self._llm.ask(messages, token_limit=800)
        if success:
            result = format_for_linkedin(result)
        return success, result

    def _build_preamble(self, persona: dict, user_preamble: str) -> str:
        """Build the system prompt with persona and user preferences."""
        parts = [
            f"You are an elite, highly experienced web developer writing a viral LinkedIn post. "
            f"The current datetime is {datetime.now().strftime('%B %d, %Y (%A)')}. "
            f"Write in the first person, using a confident, conversational, and highly engaging tone. "
            f"Never sound robotic or like 'ChatGPT'. Avoid generic corporate buzzwords.\n",
        ]

        # User preamble takes priority (if provided)
        if user_preamble:
            parts.append(f"=== USER INSTRUCTIONS (HIGHEST PRIORITY) ===\n{user_preamble}\n")

        parts.append(
            f"=== POST STRUCTURE (PERSONA) ===\n"
            f"Use this specific framework for this post: {persona['name']}\n"
            f"Instruction: {persona['instruction']}\n"
        )

        parts.append(
            "=== FORMATTING RULES (STRICT) ===\n"
            "1. No markdown backticks or markdown headers (like # or ##) in the output.\n"
            "2. Use **bold text** ONLY for section headers or crucial emphasis.\n"
            "3. Use *italic text* for quotes or subtle emphasis.\n"
            "4. Keep paragraphs short (1-3 sentences max) for readability on mobile.\n"
            "5. End the post with exactly 3-5 relevant hashtags.\n"
            "6. Absolute maximum length: 1800 characters.\n"
            "Return ONLY the post text. Do not wrap in quotes or code blocks."
        )

        return "\n".join(parts)

    def _fetch_websites(self) -> list[str]:
        """Scrape configured websites concurrently."""
        content: list[str] = []
        limit = self._config.scrape_char_limit

        try:
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {
                    pool.submit(Scraper(url, limit).fetch_content): url
                    for url in self._config.websites
                }
                for future in as_completed(futures, timeout=30):
                    try:
                        result = future.result()
                        if result:
                            content.append(result)
                    except Exception as e:
                        url = futures[future]
                        logger.warning("Scrape failed for %s: %s", url, e)
        except Exception as e:
            logger.error("Website scraping error: %s", e)

        random.shuffle(content)
        return content
