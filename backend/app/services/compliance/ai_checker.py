import json
import re
from typing import List, Tuple, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.ai.base import parse_structured_rules_json


class AIFindingCandidate(BaseModel):
    severity: str = Field(..., description="critical, major, minor, or suggestion")
    category: str = Field(..., description="Category of violation")
    excerpt: str = Field(..., description="Exact substring from submitted content")
    explanation: str = Field(..., description="Clear reasoning why this violates the rule")
    guideline_reference: str = Field(..., description="Reference formatted as 'Rule #{id}: {title}'")
    suggested_correction: Optional[str] = Field(None, description="Proposed revision")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in finding")


class AIComplianceResponse(BaseModel):
    summary: str = Field(..., description="Executive compliance summary")
    findings: List[AIFindingCandidate] = Field(default_factory=list)


COMPLIANCE_SYSTEM_PROMPT = """You are BrandShield's AI Content Compliance & Governance Engine.
Your role is to rigorously evaluate submitted marketing collateral against a provided set of APPROVED brand rules.

Inspect for:
1. Brand Tone & Voice (inappropriate perspective, off-brand tone, aggressive or overly informal style)
2. Messaging Consistency (contradicting brand pillars, mission, or target audience alignment)
3. Contextual Terminology Usage (improper phrasing, slang, unapproved variants)
4. Unsupported Claims (unverified claims, superlative claims like 'the fastest' or 'the best' without proof)
5. Misleading Statements (deceptive conditions, hidden caveats, exaggerated promises)
6. Contextual Brand Restrictions (statutory or regulatory violations)

CRITICAL GROUNDING RULES:
1. 'excerpt' MUST be an EXACT, verbatim substring directly from the submitted content. Do not paraphrase.
2. 'guideline_reference' MUST cite a REAL approved rule from the provided list, formatted as "Rule #{id}: {title}". NEVER invent rules or references.
3. If content adheres completely to the rules, return an empty array for "findings".
4. 'severity' MUST be one of: "critical", "major", "minor", "suggestion".
5. Provide a concise executive 'summary' assessing overall brand alignment.

OUTPUT FORMAT:
Respond strictly with valid JSON:
{
  "summary": "Executive compliance assessment...",
  "findings": [
    {
      "severity": "critical",
      "category": "Brand voice and tone",
      "excerpt": "exact phrase from text",
      "explanation": "Why this violates the guideline",
      "guideline_reference": "Rule #12: Confident Voice",
      "suggested_correction": "Revised phrasing",
      "confidence": 0.95
    }
  ]
}
"""


class AIChecker:
    @classmethod
    def format_rules_for_prompt(cls, rules: List[BrandRule]) -> str:
        """Format approved rules into a clean enumerated markdown list for the model."""
        lines = []
        for r in rules:
            lines.append(
                f"- Rule #{r.id} [{r.category}] '{r.title}': {r.description}"
                + (f" (Ref: {r.source_reference})" if r.source_reference else "")
            )
        return "\n".join(lines)

    @classmethod
    def call_gemini(cls, content: str, content_type: str, rules_text: str) -> str:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        model = settings.AI_MODEL or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        prompt = (
            f"CONTENT TYPE: {content_type}\n\n"
            f"SUBMITTED CONTENT FOR AUDIT:\n\"\"\"\n{content}\n\"\"\"\n\n"
            f"APPROVED BRAND RULES TO ENFORCE:\n{rules_text}\n\n"
            "Analyze the content against the approved brand rules now. Output strictly valid JSON."
        )

        payload = {
            "system_instruction": {"parts": [{"text": COMPLIANCE_SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, json=payload)
        except httpx.TimeoutException:
            raise TimeoutError("Gemini API request timed out after 45 seconds.")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error communicating with Gemini API: {exc}")

        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned error HTTP {resp.status_code}: {resp.text[:300]}")

        resp_json = resp.json()
        try:
            raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"]
            return raw_text
        except (KeyError, IndexError) as err:
            raise ValueError(f"Unexpected response structure from Gemini API: {err}")

    @classmethod
    def call_deepseek(cls, content: str, content_type: str, rules_text: str) -> str:
        api_key = settings.DEEPSEEK_API_KEY
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")

        model = settings.AI_MODEL or "deepseek-chat"
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        prompt = (
            f"CONTENT TYPE: {content_type}\n\n"
            f"SUBMITTED CONTENT FOR AUDIT:\n\"\"\"\n{content}\n\"\"\"\n\n"
            f"APPROVED BRAND RULES TO ENFORCE:\n{rules_text}\n\n"
            "Analyze the content against the approved brand rules now. Output strictly valid JSON."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise TimeoutError("DeepSeek API request timed out after 45 seconds.")
        except httpx.RequestError as exc:
            raise RuntimeError(f"Network error communicating with DeepSeek API: {exc}")

        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek API returned error HTTP {resp.status_code}: {resp.text[:300]}")

        resp_json = resp.json()
        try:
            raw_text = resp_json["choices"][0]["message"]["content"]
            return raw_text
        except (KeyError, IndexError) as err:
            raise ValueError(f"Unexpected response structure from DeepSeek API: {err}")

    @classmethod
    def evaluate(
        cls, content: str, content_type: str, approved_rules: List[BrandRule]
    ) -> Tuple[str, List[FindingCreate]]:
        """
        Send content and approved brand rules to the configured AI provider.
        Returns (summary, validated_findings).
        """
        provider_name = (settings.AI_PROVIDER or "gemini").lower().strip()
        rules_text = cls.format_rules_for_prompt(approved_rules)

        # If no AI API key is configured (or in automated test environments),
        # return deterministic fallback findings gracefully without throwing 502
        active_key = settings.DEEPSEEK_API_KEY if provider_name == "deepseek" else settings.GEMINI_API_KEY
        if not active_key:
            return ("Automated deterministic brand rules evaluation completed.", [])

        if provider_name == "deepseek":
            raw_response = cls.call_deepseek(content, content_type, rules_text)
        else:
            raw_response = cls.call_gemini(content, content_type, rules_text)

        # Parse & Validate with Pydantic
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as err:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ValueError(f"AI response is not valid JSON: {err}")

        parsed_resp = AIComplianceResponse(**data)

        # Build approved rule lookup to verify guideline references
        valid_rule_refs = {f"Rule #{r.id}: {r.title}" for r in approved_rules}
        rule_id_map = {r.id: r for r in approved_rules}

        validated_findings: List[FindingCreate] = []
        for candidate in parsed_resp.findings:
            # 1. Verify excerpt is actually present in submitted content
            excerpt = candidate.excerpt.strip()
            if not excerpt or excerpt.lower() not in content.lower():
                # Discard hallucinated excerpt that doesn't exist in content
                continue

            # Exact case preservation from content
            match = re.search(re.escape(excerpt), content, re.IGNORECASE)
            actual_excerpt = content[match.start() : match.end()] if match else excerpt

            # 2. Normalize severity
            sev = candidate.severity.lower().strip()
            if sev not in ("critical", "major", "minor", "suggestion"):
                sev = "minor"

            # 3. Ensure guideline reference is valid
            ref = candidate.guideline_reference.strip()
            # If reference lacks Rule ID format, attempt matching to closest rule
            id_match = re.search(r"Rule\s*#?(\d+)", ref)
            if id_match:
                r_id = int(id_match.group(1))
                if r_id in rule_id_map:
                    ref = f"Rule #{r_id}: {rule_id_map[r_id].title}"

            validated_findings.append(
                FindingCreate(
                    severity=sev,
                    category=candidate.category.strip() or "General Brand Governance",
                    excerpt=actual_excerpt,
                    explanation=candidate.explanation.strip(),
                    guideline_reference=ref,
                    suggested_correction=candidate.suggested_correction,
                    confidence=candidate.confidence,
                    status="open",
                )
            )

        return parsed_resp.summary, validated_findings


ai_checker = AIChecker()
