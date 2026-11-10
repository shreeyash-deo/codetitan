from typing import List
import httpx
from app.core.config import settings
from app.schemas.rule import ExtractedRuleCandidate
from app.services.ai.base import BaseAIProvider, SYSTEM_PROMPT, parse_structured_rules_json


class DeepSeekProvider(BaseAIProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.model = model or settings.AI_MODEL or "deepseek-chat"

    def extract_rules(self, text: str) -> List[ExtractedRuleCandidate]:
        if not self.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not configured. Please set DEEPSEEK_API_KEY in your environment or .env file."
            )

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "BRAND GUIDELINE DOCUMENT TEXT FOR ANALYSIS:\n\n"
                        f"{text}\n\n"
                        "Extract all concrete, documented rules now in JSON format strictly following the schema."
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise TimeoutError("DeepSeek API request timed out after 45 seconds.")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error communicating with DeepSeek API: {exc}")

        if response.status_code == 429:
            raise RuntimeError("DeepSeek API rate limit exceeded. Please wait a moment before trying again.")
        elif response.status_code in (401, 403):
            raise RuntimeError("DeepSeek API authentication failed. Please verify your DEEPSEEK_API_KEY.")
        elif response.status_code != 200:
            raise RuntimeError(
                f"DeepSeek API returned error HTTP {response.status_code}: {response.text[:300]}"
            )

        resp_json = response.json()
        try:
            choices = resp_json["choices"]
            raw_text = choices[0]["message"]["content"]
        except (KeyError, IndexError) as err:
            raise ValueError(f"Unexpected response structure from DeepSeek API: {err}")

        return parse_structured_rules_json(raw_text)
