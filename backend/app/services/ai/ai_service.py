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
        If the AI provider encounters quota exhaustion, timeouts, or network failures,
        seamlessly fall back to deterministic structural governance extraction so rule extraction never fails silently.
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Document text is empty. Cannot extract brand rules.")

        # Limit to 120,000 characters to prevent token limits on standard tiers
        if len(cleaned_text) > 120000:
            logger.warning("Document text exceeds 120k characters. Analyzing first 120k characters.")
            cleaned_text = cleaned_text[:120000]

        candidates: List[ExtractedRuleCandidate] = []
        ai_error = None

        try:
            provider = cls.get_provider()
            logger.info(f"Initiating AI brand rule extraction using configured provider '{settings.AI_PROVIDER}' (model: {getattr(provider, 'model', 'default')}).")
            candidates = provider.extract_rules(cleaned_text)
            if candidates:
                logger.info(f"AI provider successfully extracted {len(candidates)} candidate brand rules.")
                return candidates
        except Exception as exc:
            ai_error = exc
            logger.warning(
                f"AI provider extraction failed or reached quota limit ({exc}). "
                "Activating deterministic structural governance rule extractor."
            )

        # Fallback to structural extraction if AI provider produced no candidates or errored
        from app.services.ai.structural_extractor import structural_extractor
        candidates = structural_extractor.extract_rules(cleaned_text)
        if candidates:
            logger.info(f"Structural extractor extracted {len(candidates)} grounded candidate rules from document structure.")
            return candidates

        if ai_error:
            raise ai_error

        return []


ai_service = AIService()
