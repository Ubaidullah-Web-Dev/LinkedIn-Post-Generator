"""
core/services/image_generator.py — Image generation orchestration.

v2.5: Template-driven infographic engine as PRIMARY.
AI image generation (DALL-E, Gemini, Pollinations) is OPTIONAL fallback only.

Three explicit modes:
- "template_only" (default): deterministic, no AI usage
- "hybrid": template first, AI assets as fallback
- "ai_only": force AI generation (skip templates)
"""

from __future__ import annotations

import base64
import json
import os
import random
import re
from urllib.parse import quote
from uuid import uuid4

import requests

from core.llm.gateway import LLMGateway
from core.constants import GENERATED_DIR
from core.infographic import InfographicEngine
from core.infographic.selector import select_template
from core.logger import get_logger

logger = get_logger(__name__)


# ── JSON Extraction ──────────────────────────────────────────────────────────

def extract_json(text: str) -> dict | None:
    """Robustly extract JSON from LLM output (handles markdown wrapping)."""
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    json_str = match.group()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM output")
            return None


# ── LLM Extraction Prompts ───────────────────────────────────────────────────

_EXTRACTION_PROMPTS: dict[str, str] = {
    "tips_list": (
        "Extract structured data as JSON: "
        '{"title": "short title", "subtitle": "optional subtitle", '
        '"tips": ["Tip header: description", "Another tip: description"]}. '
        "Return ONLY raw JSON."
    ),
    "comparison": (
        "Extract comparison data as JSON: "
        '{"title": "X vs Y", "subtitle": "optional", '
        '"left": {"name": "X"}, "right": {"name": "Y"}, '
        '"rows": [{"feature": "Feature Name", "left": true, "right": false}]}. '
        "Return ONLY raw JSON."
    ),
    "stat_highlight": (
        "Extract the key statistic as JSON: "
        '{"stat": "42%", "label": "short label", '
        '"body": "context explanation", "tag": "#Category"}. '
        "Return ONLY raw JSON."
    ),
    "step_flow": (
        "Extract steps as JSON: "
        '{"title": "How to...", "steps": ["Step 1: desc", "Step 2: desc"]}. '
        "Return ONLY raw JSON."
    ),
    "quote_card": (
        "Extract the key quote as JSON: "
        '{"quote": "the quote text", "author": "attribution if any", '
        '"tag": "#Topic"}. '
        "Return ONLY raw JSON."
    ),
    "code_snippet": (
        "Extract topic info as JSON: "
        '{"title": "Concept Title", "body": "brief explanation", '
        '"tag": "#Tech"}. '
        "Return ONLY raw JSON."
    ),
    "minimal_card": (
        "Extract key info as JSON: "
        '{"title": "main point", "body": "supporting detail", '
        '"tag": "#Topic"}. '
        "Return ONLY raw JSON."
    ),
}


# ── Image Generator ──────────────────────────────────────────────────────────

class ImageGenerator:
    """
    Image generation with three explicit modes:
    - template_only: deterministic infographic (default, no AI for image)
    - hybrid: infographic first, AI fallback
    - ai_only: skip infographics entirely
    """

    def __init__(self, llm: LLMGateway) -> None:
        self._llm = llm
        self._engine = InfographicEngine()

    def generate(
        self,
        post_text: str,
        image_model: str = "template_only",
        template: str = "auto",
        theme: str = "random",
    ) -> tuple[bool, str, str]:
        """
        Generate an image for the given post text.

        Args:
            post_text: the LinkedIn post text
            image_model: "template_only", "hybrid", "ai_only",
                         "dall-e-3", "gemini", "pollinations"
            template: template name or "auto"
            theme: theme name or "random"

        Returns (success, path_or_error, image_type).
        """
        os.makedirs(str(GENERATED_DIR), exist_ok=True)
        uid = uuid4().hex[:8]

        # ── Mode: template_only (DEFAULT — deterministic) ────────────
        if image_model in ("template_only", "auto", "infographic"):
            return self._generate_template(post_text, template, theme, uid)

        # ── Mode: hybrid (template first, AI fallback) ───────────────
        if image_model == "hybrid":
            success, path, itype = self._generate_template(post_text, template, theme, uid)
            if success:
                return success, path, itype
            logger.info("Template failed, falling back to AI generation")
            return self._generate_ai(post_text, uid)

        # ── Mode: ai_only ────────────────────────────────────────────
        if image_model == "ai_only":
            return self._generate_ai(post_text, uid)

        # ── Specific AI provider ─────────────────────────────────────
        if image_model in ("dall-e-3", "gemini", "pollinations"):
            return self._generate_ai(post_text, uid, provider=image_model)

        return False, f"Unknown image_model: {image_model}", ""

    # ── Template Generation ──────────────────────────────────────────

    def _generate_template(
        self, post_text: str, template: str, theme: str, uid: str
    ) -> tuple[bool, str, str]:
        """Generate using the infographic template engine."""
        try:
            # Step 1: Determine template
            if template == "auto":
                selection = select_template(post_text)
                tpl_name = selection.template
                logger.info(
                    "Auto-selected template: %s (confidence: %.0f%%, reason: %s)",
                    tpl_name, selection.confidence * 100, selection.reason,
                )
            else:
                tpl_name = template

            # Step 2: Extract structured data via LLM
            data = self._extract_data(post_text, tpl_name)
            if not data:
                # Fallback: use post text directly as minimal card
                data = {"title": post_text[:100], "body": post_text[100:500], "tag": "#Dev"}
                tpl_name = "minimal_card"

            # Step 3: Render
            save_path = str(GENERATED_DIR / f"{tpl_name}_{uid}.png")
            result = self._engine.render(
                data, template=tpl_name, theme=theme, save_path=save_path,
            )

            if result and os.path.exists(result):
                return True, result, f"template:{tpl_name}"
            return False, "Template render produced no output", ""

        except Exception as e:
            logger.error("Template generation error: %s", e)
            return False, str(e), ""

    def _extract_data(self, post_text: str, template_name: str) -> dict | None:
        """Use LLM to extract structured data for the chosen template."""
        prompt = _EXTRACTION_PROMPTS.get(template_name, _EXTRACTION_PROMPTS["minimal_card"])
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": post_text[:1200]},
        ]
        success, result = self._llm.ask(messages, token_limit=600, use_cache=True)
        if not success:
            return None
        return extract_json(result)

    # ── AI Generation (fallback only) ────────────────────────────────

    def _generate_ai(
        self, post_text: str, uid: str, provider: str | None = None,
    ) -> tuple[bool, str, str]:
        """Generate via AI image providers (DALL-E, Gemini, Pollinations)."""
        prompt = self._get_image_prompt(post_text)
        errors: list[str] = []

        providers = [provider] if provider else ["dall-e-3", "gemini", "pollinations"]

        for prov in providers:
            try:
                if prov == "dall-e-3" and self._llm.openai_client:
                    path = self._dalle_generate(prompt, uid)
                    if path:
                        return True, path, "dall-e-3"
                elif prov == "gemini" and self._llm.gemini_key:
                    path = self._gemini_generate(prompt, uid)
                    if path:
                        return True, path, "gemini"
                elif prov == "pollinations":
                    path = self._pollinations_generate(prompt, uid)
                    if path:
                        return True, path, "pollinations"
            except Exception as e:
                errors.append(f"{prov}: {e}")

        return False, "\n".join(errors) or "No AI providers configured", ""

    def _get_image_prompt(self, post_text: str) -> str:
        """Generate an AI image prompt from post text."""
        messages = [
            {"role": "system", "content": (
                "Write ONE short image prompt for this post. "
                "Dark background. Code/tech theme. NO people. NO text. "
                "Return ONLY the prompt."
            )},
            {"role": "user", "content": post_text[:600]},
        ]
        success, result = self._llm.ask(messages, token_limit=120, use_cache=True)
        if success:
            return result
        return "abstract dark code visualization, glowing neon lines, 4K, no people"

    def _dalle_generate(self, prompt: str, uid: str) -> str | None:
        client = self._llm.openai_client
        response = client.images.generate(
            model="dall-e-3", prompt=prompt[:1000], size="1792x1024", n=1
        )
        url = response.data[0].url
        if not url:
            return None
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            path = str(GENERATED_DIR / f"dalle_{uid}.png")
            with open(path, "wb") as f:
                f.write(r.content)
            return path
        return None

    def _gemini_generate(self, prompt: str, uid: str) -> str | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash-image:generateContent?key={self._llm.gemini_key}"
        )
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt[:1000]}]}]},
            timeout=90,
        )
        if r.status_code != 200:
            return None
        parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        if parts and "inlineData" in parts[0]:
            img_data = base64.b64decode(parts[0]["inlineData"]["data"])
            path = str(GENERATED_DIR / f"gemini_{uid}.png")
            with open(path, "wb") as f:
                f.write(img_data)
            return path
        return None

    def _pollinations_generate(self, prompt: str, uid: str) -> str | None:
        seed = random.randint(1, 999999)
        encoded = quote(prompt)
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1216&height=832&nologo=true&model=flux&seed={seed}&enhance=true"
        )
        r = requests.get(url, timeout=120, stream=True)
        if r.status_code == 200:
            path = str(GENERATED_DIR / f"pollinations_{uid}.png")
            with open(path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return path
        return None
