from typing import List
import httpx
from app.core.config import settings
from app.schemas.rule import ExtractedRuleCandidate
from app.services.ai.base import BaseAIProvider, SYSTEM_PROMPT, parse_structured_rules_json


class GeminiProvider(BaseAIProvider):
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.AI_MODEL or "gemini-2.0-flash"

    def extract_rules(self, text: str) -> List[ExtractedRuleCandidate]:
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY is not configured. Please set GEMINI_API_KEY in your environment or .env file."
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "BRAND GUIDELINE DOCUMENT TEXT FOR ANALYSIS:\n\n"
                                f"{text}\n\n"
                                "Extract all concrete, documented rules now in JSON format strictly following the schema."
                            )
                        }
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(url, json=payload)
        except httpx.TimeoutException:
            raise TimeoutError("Gemini API request timed out after 45 seconds.")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error communicating with Gemini API: {exc}")

        if response.status_code == 429:
            raise RuntimeError("Gemini API rate limit exceeded. Please wait a moment before trying again.")
        elif response.status_code in (401, 403):
            raise RuntimeError("Gemini API authentication failed. Please verify your GEMINI_API_KEY.")
        elif response.status_code != 200:
            raise RuntimeError(
                f"Gemini API returned error HTTP {response.status_code}: {response.text[:300]}"
            )

        resp_json = response.json()
        try:
            candidates = resp_json["candidates"]
            first_candidate = candidates[0]
            parts = first_candidate["content"]["parts"]
            raw_text = parts[0]["text"]
        except (KeyError, IndexError) as err:
            raise ValueError(f"Unexpected response structure from Gemini API: {err}")

        return parse_structured_rules_json(raw_text)
