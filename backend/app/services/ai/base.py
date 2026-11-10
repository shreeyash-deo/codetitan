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

Extract rules under these required governance domains:
1. Brand voice and tone rules (e.g. required professional tone, style restrictions, communication principles)
2. Approved and prohibited terminology (e.g. preferred terminology, avoided terms, naming conventions)
3. Prohibited marketing claims (e.g. guaranteed returns, risk-free claims, unrealistic wealth promises)
4. Mandatory disclaimers (e.g. financial risk disclaimers, performance disclaimers, footnote integrity)
5. Factual and performance restrictions (e.g. unverified statistics, comparative claims, evidence requirements)
6. Content approval requirements (e.g. reviewer sign-off workflows, revision mandates before publication)
7. Visual identity guidelines (e.g. logo rules, clearspace, color references, typography conventions)

CRITICAL INSTRUCTIONS:
- Extract ONLY facts and guidelines explicitly supported by the uploaded text.
- NEVER fabricate, extrapolate, or invent brand rules not present in the document.
- If a section contains no rules for a category, do NOT invent one.
- For each candidate rule, identify:
  - "title": A concise, unambiguous rule title (5-10 words).
  - "category": Exactly one of the standard categories: "Brand voice and tone", "Approved terminology", "Restricted terminology", "Claims and disclaimers", "Content restrictions", "Product facts", "Visual identity guidelines".
  - "subCategory": Specific subcategory topic (e.g. "Voice & Tone", "Banned Claims", "Disclaimers", "Terminology").
  - "description": The exact actionable guidance, prohibition, or rule requirement.
  - "rationale": Clear explanation of why this rule exists and why violation poses risk.
  - "severity": One of "critical", "high", "medium", "low".
  - "enforcement_level": "Strict" or "Advisory".
  - "approved_example": Approved sample wording/phrasing if mentioned or derived from the text.
  - "prohibited_example": Prohibited sample wording/phrasing if mentioned or derived from the text.
  - "source_reference": Citation such as "Section 4.1" or "Section 2.1" if available in text.
  - "confidence": Float between 0.0 and 1.0 indicating clarity/authority in the text.

OUTPUT FORMAT:
You MUST respond with valid JSON containing a top-level key "rules" mapped to an array of rule objects:
{
  "rules": [
    {
      "title": "Guaranteed Returns Prohibition",
      "category": "Content restrictions",
      "subCategory": "Prohibited Marketing Claims",
      "description": "Marketing content must never guarantee financial returns, profits or investment outcomes.",
      "rationale": "Prevents statutory regulatory violations and deceptive marketing.",
      "severity": "critical",
      "enforcement_level": "Strict",
      "approved_example": "Explore financial tools designed to help you make informed decisions.",
      "prohibited_example": "Guaranteed profits are waiting for you!",
      "source_reference": "Section 4.1",
      "confidence": 0.98
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
                subCategory=item.get("subCategory") or item.get("sub_category"),
                rationale=item.get("rationale"),
                severity=item.get("severity"),
                enforcement_level=item.get("enforcement_level") or item.get("enforcementLevel"),
                approved_example=item.get("approved_example") or item.get("approvedExample"),
                prohibited_example=item.get("prohibited_example") or item.get("prohibitedExample"),
            )
            if candidate.title and candidate.description:
                candidates.append(candidate)

    return candidates


class BaseAIProvider(ABC):
    @abstractmethod
    def extract_rules(self, text: str) -> List[ExtractedRuleCandidate]:
        """Send extracted text to the AI provider and return validated rule candidates."""
        pass
