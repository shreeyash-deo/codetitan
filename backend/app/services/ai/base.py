import json
import re
from abc import ABC, abstractmethod
from typing import List
from app.schemas.rule import ExtractedRuleCandidate

STANDARD_CATEGORIES = [
    "Brand voice and tone",
    "Approved terminology",
    "Restricted terminology",
    "Brand messaging",
    "Product facts",
    "Claims and disclaimers",
    "Content restrictions",
    "Visual identity guidelines",
]

SYSTEM_PROMPT = """You are an expert enterprise brand compliance analyst and governance specialist.
Your task is to analyze the provided brand guideline document text and extract all concrete, enforceable rules.

Extract rules under these categories:
1. Brand voice and tone (e.g. style, perspective, communication principles)
2. Approved terminology (e.g. preferred product names, acceptable terms)
3. Restricted terminology (e.g. prohibited words, obsolete names, competitor mentions)
4. Brand messaging (e.g. value propositions, mission statements, elevator pitches)
5. Product facts (e.g. verified statistics, features, technical specifications)
6. Claims and disclaimers (e.g. mandatory legal footers, claims needing qualification)
7. Content restrictions (e.g. statutory restrictions, prohibited promises, regulatory boundaries)
8. Visual identity guidelines (e.g. logo rules, color references, typography conventions)

CRITICAL INSTRUCTIONS:
- Extract ONLY facts and guidelines explicitly supported by the uploaded text.
- NEVER fabricate, extrapolate, or invent brand rules not present in the document.
- If a section contains no rules for a category, do NOT invent one.
- For each rule, identify:
  - "title": A concise, unambiguous rule title (5-10 words).
  - "description": The exact actionable guidance or restriction.
  - "category": Exactly one of the standard categories listed above.
  - "source_reference": Citation such as "Page 2" or "Section 3.1" if available in text.
  - "confidence": Float between 0.0 and 1.0 indicating clarity/authority in the text.

OUTPUT FORMAT:
You MUST respond with valid JSON containing a top-level key "rules" mapped to an array of rule objects:
{
  "rules": [
    {
      "title": "...",
      "description": "...",
      "category": "...",
      "source_reference": "...",
      "confidence": 0.95
    }
  ]
}
"""


def parse_structured_rules_json(raw_response_text: str) -> List[ExtractedRuleCandidate]:
    """
    Parse and validate raw model output into a list of ExtractedRuleCandidate objects.
    Robustly handles markdown code fences and extraneous text.
    """
    cleaned = raw_response_text.strip()
    # Strip markdown code fences if present (```json ... ```)
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as err:
        # Attempt regex fallback to extract JSON object
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            raise ValueError(f"Model response is not valid JSON: {err}. Raw text preview: {cleaned[:200]}")

    rules_data = data.get("rules", [])
    if not isinstance(rules_data, list):
        raise ValueError("Invalid format: 'rules' key must be an array.")

    candidates: List[ExtractedRuleCandidate] = []
    for item in rules_data:
        if isinstance(item, dict):
            # Validate with Pydantic
            candidate = ExtractedRuleCandidate(
                title=item.get("title", "").strip(),
                description=item.get("description", "").strip(),
                category=item.get("category", "Brand voice and tone").strip(),
                source_reference=item.get("source_reference"),
                confidence=float(item.get("confidence", 1.0)),
            )
            if candidate.title and candidate.description:
                candidates.append(candidate)

    return candidates


class BaseAIProvider(ABC):
    @abstractmethod
    def extract_rules(self, text: str) -> List[ExtractedRuleCandidate]:
        """Send extracted text to the AI provider and return validated rule candidates."""
        pass
