from time import sleep
import requests
from openai import OpenAI, RateLimitError, APIStatusError
import json

class ChatGpt:
    def __init__(self, open_ai_key: str = None, gemini_key: str = None, openrouter_key: str = None):
        self.open_ai_key = open_ai_key
        self.gemini_key = gemini_key
        self.openrouter_key = openrouter_key

        self.openai_client = OpenAI(api_key=open_ai_key) if open_ai_key else None
        self.openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key
        ) if openrouter_key else None

        # Pool of free OpenRouter models for failover
        self.openrouter_free_models = [
            "openrouter/free",
            "google/gemma-4-31b-it:free",
            "google/gemma-4-26b-a4b-it:free"
        ]

    def ask(
        self,
        messages: list[dict[str, str]],
        token_limit: int = 150,
        model: str = "gpt-4o-mini",
        temp: float = 1.0,
        retry_limit: int = 3,
        provider: str = "auto",
    ) -> tuple[bool, str]:
        """
        Returns (success: bool, content_or_error: str)
        """
        p = provider.lower()
        errors = []
        
        # 1. OpenAI
        if p in ["auto", "openai"] and self.open_ai_key:
            success, res = self.ask_openai(messages, token_limit, model, temp, retry_limit)
            if success: return True, res
            errors.append(f"OpenAI Failed: {res}")

        # 2. Gemini
        if p in ["auto", "gemini"] and self.gemini_key:
            gemini_model = model if model != "gpt-4o-mini" else "gemini-2.0-flash"
            success, res = self.ask_gemini(messages, gemini_model, token_limit, temp, retry_limit)
            if success: return True, res
            errors.append(f"Gemini Failed: {res}")

        # 3. OpenRouter (With Model Rotation)
        if p in ["auto", "openrouter"] and self.openrouter_key:
            if model == "gpt-4o-mini":
                # Rotate through free models
                for or_model in self.openrouter_free_models:
                    success, res = self.ask_openrouter(messages, token_limit, or_model, temp, 1) # 1 retry per model
                    if success: return True, res
                    errors.append(f"OpenRouter ({or_model}) Failed: {res}")
            else:
                success, res = self.ask_openrouter(messages, token_limit, model, temp, retry_limit)
                if success: return True, res
                errors.append(f"OpenRouter Failed: {res}")

        if not errors:
            return False, f"Provider '{provider}' not configured. Please add API keys."
        
        return False, "\n".join(errors)

    def ask_openai(self, messages, token_limit, model, temp, retry_limit) -> tuple[bool, str]:
        retries = retry_limit
        while retries >= 0:
            retries -= 1
            try:
                completion = self.openai_client.chat.completions.create(
                    model=model, messages=messages, max_tokens=token_limit, temperature=temp,
                )
                if completion and completion.choices:
                    return True, completion.choices[0].message.content.strip()
            except RateLimitError as e:
                err_msg = str(e).lower()
                if "quota" in err_msg or "daily" in err_msg or "insufficient" in err_msg:
                    return False, "Quota exceeded or billing required."
                sleep(3)
            except Exception as e:
                return False, str(e)
        return False, "Max retries exceeded."

    def ask_openrouter(self, messages, token_limit, model, temp, retry_limit) -> tuple[bool, str]:
        retries = retry_limit
        while retries >= 0:
            retries -= 1
            try:
                completion = self.openrouter_client.chat.completions.create(
                    model=model, messages=messages, max_tokens=token_limit, temperature=temp,
                )
                if completion and completion.choices:
                    return True, completion.choices[0].message.content.strip()
            except RateLimitError as e:
                err_msg = str(e).lower()
                if "free-models-per-day" in err_msg:
                    return False, "Daily limit reached for free models."
                if "free-models-per-min" in err_msg:
                    sleep(5)
                    continue
                return False, "Rate limit exceeded."
            except Exception as e:
                return False, str(e)
        return False, "Max retries exceeded."

    def ask_gemini(self, messages, model, token_limit, temp, retry_limit) -> tuple[bool, str]:
        system_instruction = None
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": token_limit, "temperature": temp}
        }
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}

        retries = retry_limit
        while retries >= 0:
            retries -= 1
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code != 200:
                    resp_text = response.text.lower()
                    if response.status_code == 429:
                        if "quota" in resp_text or "limit: 0" in resp_text or "resource_exhausted" in resp_text:
                            return False, "Quota exhausted or billing required."
                        sleep(5)
                        continue
                    try:
                        err = response.json().get("error", {}).get("message", response.text)
                        return False, err
                    except:
                        return False, response.text
                        
                res_data = response.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return True, text.strip()
            except Exception as e:
                if retries < 0:
                    return False, str(e)
                sleep(3)
        return False, "Max retries exceeded."
