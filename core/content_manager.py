from core.linkedin import LinkedIn
from core.chatgpt import ChatGpt
from core.scraper import Scraper

from datetime import datetime
import os
import re
import random
import requests
import json
from re import sub
from urllib.parse import quote
from utils import get_file_data

PERSONAS = [
    {
        "name": "The Contrarian Take",
        "instruction": "Start with an unpopular opinion about modern web development (e.g. against a popular framework, CSS approach, or architecture). Prove it with a real technical example from your experience, and end with a question to your network."
    },
    {
        "name": "The Post-Mortem",
        "instruction": "Tell a short story about a technical failure, production bug, or architecture mistake you caused. Explain the technical root cause simply, and list 3 specific things you learned."
    },
    {
        "name": "The Deep Dive",
        "instruction": "Explain a complex web dev concept (like React reconciliation, SQL indexing, or Event Loop) using a simple, real-world non-programming analogy. Make it highly educational."
    },
    {
        "name": "The Workflow Hack",
        "instruction": "Share a specific, niche productivity tip or tool you use daily (like a TypeScript trick, a Git alias, or an obscure CSS property). Show exactly how it saves time."
    }
]

TECH_IMAGE_PROMPTS = [
    "ultra-detailed dark terminal screen filled with glowing JavaScript code, VSCode editor with syntax highlighting, deep navy background, electric blue and neon green glow, floating brackets and semicolons, ultra-sharp 4K digital art, no people",
    "photorealistic browser DevTools panel open, CSS grid inspector highlighted in purple, dark mode, neon orange performance flamechart, vibrant tech illustration, ultra-detailed, 4K, no people",
    "abstract isometric illustration of React Next.js TypeScript and Tailwind CSS logos stacked as glowing 3D blocks on a dark grid, neon purple and cyan accents, ultra-sharp, 4K, no people",
    "glowing git branch tree diagram on dark background, teal and orange node commits floating in space, cinematic depth of field, abstract tech art, 4K, ultra-detailed, no people",
]

class ContentManager:
    def __init__(self, config_input):
        if isinstance(config_input, dict):
            self.config = config_input
        else:
            self.config = get_file_data(config_input)

        self.cookies = self.config.get("cookies")
        self.chatgpt = ChatGpt(
            open_ai_key=self.config.get("open_ai_api_key"),
            gemini_key=self.config.get("gemini_api_key"),
            openrouter_key=self.config.get("openrouter_api_key")
        )
        self.urls = self.config.get("websites", [])
        self.bio = self.config.get("bio", "Web Developer")
        self.gpt_token_limit = self.config.get("gpt_token_limit", 700)
        self.scrape_char_limit = self.config.get("scrape_char_limit", 4000)

    def fetch_website_content(self):
        content = []
        for url in self.urls:
            data = Scraper(url, self.scrape_char_limit).fetch_content()
            if data:
                content.append(data)
        random.shuffle(content)
        return content

    def generate_draft_text(self, provider="auto") -> tuple[bool, str]:
        """Returns (success: bool, content_or_error: str)"""
        persona = random.choice(PERSONAS)
        
        # Pull the custom preamble from config if the user set one, else default to empty
        user_preamble = self.config.get("gpt_preamble", "")
        
        preamble = (
            f"You are an elite, highly experienced web developer writing a viral LinkedIn post. "
            f"The current datetime is {datetime.now().strftime('%B %d, %Y (%A)')}. "
            f"Write in the first person, using a confident, conversational, and highly engaging tone. "
            f"Never sound robotic or like 'ChatGPT'. Avoid generic corporate buzzwords.\n\n"
            f"=== POST STRUCTURE (PERSONA) ===\n"
            f"Use this specific framework for this post: {persona['name']}\n"
            f"Instruction: {persona['instruction']}\n\n"
            f"=== FORMATTING RULES (STRICT) ===\n"
            f"1. No markdown backticks or markdown headers (like # or ##) in the output.\n"
            f"2. Use **bold text** ONLY for section headers or crucial emphasis.\n"
            f"3. Use *italic text* for quotes or subtle emphasis.\n"
            f"4. Keep paragraphs short (1-3 sentences max) for readability on mobile.\n"
            f"5. End the post with exactly 3-5 relevant hashtags.\n"
            f"6. Absolute maximum length: 1800 characters.\n\n"
            f"=== USER PREFERENCES ===\n"
            f"Additional Instructions from user: {user_preamble}\n"
            f"Return ONLY the post text. Do not wrap in quotes or code blocks."
        )

        gpt_messages = [
            {"role": "system", "content": preamble},
            {"role": "user", "content": f"My Bio & Context: {self.bio}"},
        ]

        if self.urls:
            scraped = self.fetch_website_content()
            if scraped:
                gpt_messages.extend([{"role": "user", "content": f"Context to include if relevant: {c}"} for c in scraped])

        success, res = self.chatgpt.ask(gpt_messages, self.gpt_token_limit, provider=provider)
        
        if not success:
            return False, res
            
        formatted_text = self.format_for_linkedin(res)
        return True, formatted_text

    def generate_draft_image(self, formatted_text, image_model="auto") -> tuple[bool, str]:
        """Returns (success: bool, path_or_error: str)"""
        image_path = "media/post_image.png"
        infographic_path = "media/infographic.png"
        errors = []

        # 1. Pillow Infographic (PRIORITY — our premium custom visuals)
        if image_model in ["auto", "infographic"]:
            try:
                path = self.generate_infographic(formatted_text, save_path=infographic_path)
                if path and os.path.exists(path):
                    return True, path
                errors.append("Infographic: AI failed to extract structured data")
            except Exception as e:
                errors.append(f"Infographic: {e}")

        # 2. OpenAI DALL-E 3
        if image_model in ["auto", "dall-e-3"] and self.chatgpt.open_ai_key:
            try:
                success, prompt = self.generate_image_prompt(formatted_text)
                if not success: prompt = random.choice(TECH_IMAGE_PROMPTS)
                response = self.chatgpt.openai_client.images.generate(model="dall-e-3", prompt=prompt[:1000], size="1792x1024", n=1)
                url = response.data[0].url
                if url:
                    r = requests.get(url, timeout=60)
                    if r.status_code == 200:
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        with open(image_path, "wb") as f: f.write(r.content)
                        return True, image_path
            except Exception as e:
                errors.append(f"DALL-E: {e}")

        # 3. Gemini Image
        if image_model in ["auto", "gemini"] and self.chatgpt.gemini_key:
            try:
                success, prompt = self.generate_image_prompt(formatted_text)
                if not success: prompt = random.choice(TECH_IMAGE_PROMPTS)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={self.chatgpt.gemini_key}"
                r = requests.post(url, headers={"Content-Type": "application/json"}, json={"contents": [{"parts": [{"text": prompt[:1000]}]}]}, timeout=90)
                if r.status_code == 200:
                    parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    if parts and "inlineData" in parts[0]:
                        import base64
                        img_data = base64.b64decode(parts[0]["inlineData"]["data"])
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)
                        with open(image_path, "wb") as f: f.write(img_data)
                        return True, image_path
                else:
                    errors.append(f"Gemini Image API Error {r.status_code}")
            except Exception as e:
                errors.append(f"Gemini: {e}")

        # 4. Pollinations.ai (Flux) — LAST resort fallback
        if image_model in ["auto", "pollinations"]:
            try:
                success, prompt = self.generate_image_prompt(formatted_text)
                if not success: prompt = random.choice(TECH_IMAGE_PROMPTS)
                seed = random.randint(1, 999999)
                encoded_prompt = quote(prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1216&height=832&nologo=true&model=flux&seed={seed}&enhance=true"
                r = requests.get(url, timeout=120, stream=True)
                if r.status_code == 200:
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    with open(image_path, "wb") as f:
                        for chunk in r.iter_content(8192): f.write(chunk)
                    return True, image_path
                errors.append(f"Pollinations HTTP {r.status_code}")
            except Exception as e:
                errors.append(f"Pollinations: {e}")

        if not errors:
            return False, f"Provider '{image_model}' not configured."
        return False, "\n".join(errors)

    def generate_image_prompt(self, post_text) -> tuple[bool, str]:
        styles = ["8-bit Pixel Art", "Isometric Claymation", "Synthwave", "Origami Papercraft", "Low-Poly 3D"]
        chosen_style = random.choice(styles)
        
        system_msg = (
            f"Write ONE short prompt visualizing this post. Art Style: {chosen_style}. "
            "Dark background. Code/tech theme. NO people. NO text. Return ONLY the prompt text."
        )
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": post_text[:600]}]
        
        return self.chatgpt.ask(messages, token_limit=120)

    def generate_infographic(self, post_text, save_path="media/infographic.png"):
        system_msg = (
            "Extract structured data as JSON. Choose ONE type: \n"
            "1. 'comparison' (X vs Y): {'type': 'comparison', 'data': {'title':'..', 'subtitle':'..', 'left':{'name':'X'}, 'right':{'name':'Y'}, 'rows':[{'feature':'..','left':true,'right':false}]}}\n"
            "2. 'tips': {'type': 'tips', 'data': {'title':'..', 'subtitle':'..', 'tips':['t1','t2']}}\n"
            "3. 'scene': {'type': 'scene', 'data': {'title':'..', 'body':'..', 'tag':'#Dev'}}\n"
            "Return ONLY raw JSON. No markdown backticks."
        )
        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": post_text[:1000]}]
        success, res = self.chatgpt.ask(messages, token_limit=600)
        if not success: return None

        # Robust JSON extraction
        start = res.find('{')
        end = res.rfind('}')
        if start != -1 and end != -1:
            json_str = res[start:end+1]
        else:
            json_str = res.strip()
            
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None
            
        itype = data.get("type")
        idata = data.get("data", {})

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        from core.render_image import render_comparison, render_tips, render_scene_card
        
        if itype == "comparison": return render_comparison(idata, save_path)
        elif itype == "tips": return render_tips(idata, save_path)
        elif itype == "scene": return render_scene_card(idata, save_path)
        return None

    def publish_post(self, text, image_path=None) -> tuple[bool, str]:
        linkedin = LinkedIn(self.cookies)
        try:
            if image_path and os.path.exists(image_path):
                linkedin.post_file(text, image_path)
            else:
                linkedin.post(text)
            return True, "Posted to LinkedIn successfully."
        except Exception as e:
            return False, str(e)

    # ── Unicode Formatting ───────────────────────────────────────────────────
    @staticmethod
    def _to_bold(t): return ''.join(chr(ord(c)-65+0x1D400) if 65<=ord(c)<=90 else chr(ord(c)-97+0x1D41A) if 97<=ord(c)<=122 else chr(ord(c)-48+0x1D7CE) if 48<=ord(c)<=57 else c for c in t)
    @staticmethod
    def _to_italic(t): return ''.join(chr(ord(c)-65+0x1D434) if 65<=ord(c)<=90 else chr(0x210E) if c=='h' else chr(ord(c)-97+0x1D44E) if 97<=ord(c)<=122 else c for c in t)
    @staticmethod
    def _to_bold_italic(t): return ''.join(chr(ord(c)-65+0x1D468) if 65<=ord(c)<=90 else chr(ord(c)-97+0x1D482) if 97<=ord(c)<=122 else c for c in t)
    @staticmethod
    def _to_monospace(t): return ''.join(chr(ord(c)-65+0x1D670) if 65<=ord(c)<=90 else chr(ord(c)-97+0x1D68A) if 97<=ord(c)<=122 else chr(ord(c)-48+0x1D7F6) if 48<=ord(c)<=57 else c for c in t)

    def format_for_linkedin(self, raw_text):
        text = re.sub(r'^[ \t]*[-*]\s+', '• ', raw_text, flags=re.MULTILINE)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        def replacer(m):
            if m.group(1): return self._to_bold_italic(m.group(1))
            if m.group(2): return self._to_bold(m.group(2))
            if m.group(3): return self._to_italic(m.group(3))
            if m.group(4): return self._to_monospace(m.group(4))
            return m.group(0)
        pattern = re.compile(r'\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`', re.DOTALL)
        return sub(r'^"([^"]*)"$', r'\1', pattern.sub(replacer, text).strip())
