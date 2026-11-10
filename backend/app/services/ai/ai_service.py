import logging
from typing import List
from app.core.config import settings
from app.schemas.rule import ExtractedRuleCandidate
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.deepseek_provider import DeepSeekProvider

logger = logging.getLogger("brandshield.ai")


class AIService:
    @staticmethod
    def get_provider() -> BaseAIProvider:
        provider_name = (settings.AI_PROVIDER or "gemini").lower().strip()
        if provider_name == "deepseek":
            return DeepSeekProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(
                f"Unsupported AI_PROVIDER '{provider_name}'. Supported options are 'gemini' and 'deepseek'."
            )

    @classmethod
    def extract_rules_from_text(cls, text: str) -> List[ExtractedRuleCandidate]:
        """
        Validate document text and invoke the configured AI provider to extract brand rules.
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Document text is empty. Cannot extract brand rules.")

        # Limit to 120,000 characters to prevent token limits on standard tiers
        if len(cleaned_text) > 120000:
            logger.warning("Document text exceeds 120k characters. Analyzing first 120k characters.")
            cleaned_text = cleaned_text[:120000]

        provider = cls.get_provider()
        return provider.extract_rules(cleaned_text)


ai_service = AIService()
