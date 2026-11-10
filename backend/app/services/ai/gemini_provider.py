from typing import List, Optional
from app.schemas.rule import ExtractedRuleCandidate
from app.services.ai.base import BaseAIProvider, SYSTEM_PROMPT, parse_structured_rules_json
from app.services.ai.gemini_client import (
    GeminiClient,
    GeminiError,
    GeminiConfigurationError,
    gemini_client,
)


class GeminiProvider(BaseAIProvider):
    """
    Brand rule extraction provider using Google Gemini API.
    Uses centralized GeminiClient for model management and error handling.
    """

    def __init__(self, api_key: str = "", model: str = ""):
        self.client = GeminiClient(
            api_key=api_key or None,
            model=model or None,
        )

    @property
    def api_key(self) -> str:
        return self.client.api_key

    @property
    def model(self) -> str:
        return self.client.model

    def extract_rules(self, text: str) -> List[ExtractedRuleCandidate]:
        """
        Send guideline text to Gemini to extract candidate rules conforming to schema.
        """
        # Validate that API key exists; raises GeminiConfigurationError if missing
        self.client.validate_configuration()

        prompt = (
            "BRAND GUIDELINE DOCUMENT TEXT FOR ANALYSIS:\n\n"
            f"{text}\n\n"
            "Extract all concrete, documented rules now in JSON format strictly following the schema."
        )

        raw_text = self.client.generate_content(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        )

        return parse_structured_rules_json(raw_text)
