import json
import logging
import re
from typing import List, Tuple, Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.ai.gemini_client import gemini_client, redact_sensitive
from app.services.compliance.deterministic_checker import deterministic_checker

logger = logging.getLogger("brandshield.compliance.ai")


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
5. Misleading Statements (deceptive conditions, hidden caveats, exaggerated promises, implied guarantees)
6. Contextual Brand Restrictions (statutory or regulatory violations, absolute safety or return promises)

CRITICAL EVALUATION GUIDELINES:
1. SEMANTIC INTENT & CONTEXT: Evaluate the full sentence and grammatical context, not isolated keywords.
2. NEGATION & CAUTIONARY STATEMENTS: Do NOT flag statements where prohibited outcomes or guarantees are explicitly negated, disclaimed, or cautioned against (e.g. "We do not guarantee financial returns", "Past performance is no guarantee of future results", "Investing carries risk of capital loss"). These are compliant risk disclosures, NOT violations.
3. BRAND VS. COMPETITOR CLAIMS: Distinguish between claims made by our brand and descriptive statements about competitors or industry practices (e.g., "Our competitors guarantee returns, but we don't" - the competitor guarantees, our brand does not; this is compliant). However, if the text claims our brand matches or exceeds prohibited competitor practices, flag our brand's claim.
4. DIRECT & IMPLIED CLAIMS: Detect implied promises, subtle guarantees, and evasive risk claims (e.g. "Your investment will double without any risk", "Watch your money multiply safely", "A foolproof path to riches", "build wealth effortlessly", "money works while you sleep", "watch your financial future grow faster than ever", "without worrying about market uncertainty", "regardless of market conditions", "without needing to understand the markets") even if literal words like "guarantee" are omitted.
5. NATURAL CORRECTION SUGGESTIONS: 'suggested_correction' MUST provide a natural, grammatically correct drop-in replacement tailored to fit seamlessly into the author's original sentence while removing the non-compliant claim. Never introduce new unverified claims.
6. STANDARD MARKETING SOCIAL PROOF: Do NOT flag conventional marketing phrases (e.g. 'thousands of businesses', 'trusted partners', 'reliable support') as unverified performance statistics unless the copy asserts specific empirical throughput numbers (e.g. '10 million TPS') or fabricated absolute claims ('trusted by 100% of businesses').
7. DISCLAIMER INDEPENDENCE (Section 5.3): Disclaimers do NOT neutralize, justify, or excuse prohibited promotional claims in the main text. If promotional body copy promises effortless wealth, market immunity, or guaranteed outcomes, it MUST be flagged even if a standard regulatory disclaimer is appended.

CRITICAL GROUNDING RULES:
1. 'excerpt' MUST be an EXACT, verbatim substring directly from the submitted content. Do not paraphrase.
2. 'guideline_reference' MUST cite a REAL approved rule from the provided list, formatted as "Rule #{id}: {title}". NEVER invent rules or references.
3. If content adheres completely to the rules (or is solely a compliant risk disclosure), return an empty array for "findings". Never dismiss prohibited claims in the body text because a disclaimer was added.
4. 'severity' MUST be one of: "critical", "major", "minor", "suggestion".
5. Provide a concise executive 'summary' assessing overall brand alignment.

OUTPUT FORMAT:
Respond strictly with valid JSON:
{
  "summary": "Executive compliance assessment...",
  "findings": [
    {
      "severity": "critical",
      "category": "Content restrictions",
      "excerpt": "exact phrase from text",
      "explanation": "Why this specific context violates the guideline",
      "guideline_reference": "Rule #12: Confident Voice",
      "suggested_correction": "Natural in-context replacement phrasing",
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
    def resolve_rule_reference(
        cls, ref: str, approved_rules: List[BrandRule]
    ) -> Optional[BrandRule]:
        """
        Grounding resolver: maps a guideline reference output from AI to an actual
        approved BrandRule in the workspace. Rejects hallucinated rules that don't exist.
        """
        if not ref or not ref.strip():
            return None

        ref_clean = ref.strip().lower()

        # 1. Direct Rule ID match: "Rule #7", "Rule 7", "#7"
        id_match = re.search(r"(?:rule\s*#?|#)\s*(\d+)", ref, re.IGNORECASE)
        if id_match:
            r_id = int(id_match.group(1))
            for r in approved_rules:
                if r.id == r_id:
                    return r

        # 2. Exact or clean title match
        for r in approved_rules:
            r_title_l = r.title.lower()
            if r_title_l == ref_clean or r_title_l in ref_clean:
                return r

        # 3. Rule Code match (e.g. NP-COMP-001, NP-COMP-004, NP-DISC-001, CR-04)
        code_match = re.search(r"\b([A-Z]{2,4}-[A-Z0-9]+(?:-\d+)?)\b", ref, re.IGNORECASE)
        if code_match:
            target_code = code_match.group(1).lower()
            for r in approved_rules:
                r_desc_l = (r.description or "").lower()
                r_title_l = (r.title or "").lower()
                r_ref_l = (getattr(r, "source_reference", None) or "").lower()
                if target_code in r_desc_l or target_code in r_title_l or target_code in r_ref_l:
                    return r

        return None

    @classmethod
    def call_gemini(cls, content: str, content_type: str, rules_text: str) -> str:
        """
        Invoke centralized GeminiClient to run compliance audit against brand rules.
        """
        prompt = (
            f"CONTENT TYPE: {content_type}\n\n"
            f"SUBMITTED CONTENT FOR AUDIT:\n\"\"\"\n{content}\n\"\"\"\n\n"
            f"APPROVED BRAND RULES TO ENFORCE:\n{rules_text}\n\n"
            "INSTRUCTIONS:\n"
            "1. Evaluate semantic intent, direct claims, and implied claims in context.\n"
            "2. Detect implied wealth promises ('build wealth effortlessly', 'money works while you sleep') and market immunity ('without worrying about market uncertainty', 'regardless of market conditions').\n"
            "3. Disclaimers do NOT neutralize promotional body copy: flag prohibited claims in promotional copy even if a disclaimer is present.\n"
            "4. Do NOT flag valid negations, disclaimers, or cautionary statements when the brand itself disclaims the outcome (e.g. 'We do not guarantee returns').\n"
            "5. Do NOT flag claims attributed to competitors when the brand clearly disavows or contrasts them (e.g. 'Our competitors guarantee returns, but we don't').\n"
            "6. DO flag direct and implied guarantees (e.g. 'Your investment will double without any risk').\n"
            "7. Provide natural, grammatically seamless suggested corrections that fit directly into the original sentence.\n"
            "8. Output strictly valid JSON matching the schema."
        )

        return gemini_client.generate_content(
            prompt=prompt,
            system_instruction=COMPLIANCE_SYSTEM_PROMPT,
            response_mime_type="application/json",
        )

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
            "INSTRUCTIONS:\n"
            "1. Evaluate semantic intent, direct claims, and implied claims in context.\n"
            "2. Detect implied wealth promises ('build wealth effortlessly', 'money works while you sleep') and market immunity ('without worrying about market uncertainty', 'regardless of market conditions').\n"
            "3. Disclaimers do NOT neutralize promotional body copy: flag prohibited claims in promotional copy even if a disclaimer is present.\n"
            "4. Do NOT flag valid negations, disclaimers, or cautionary statements when the brand itself disclaims the outcome (e.g. 'We do not guarantee returns').\n"
            "5. Do NOT flag claims attributed to competitors when the brand clearly disavows or contrasts them (e.g. 'Our competitors guarantee returns, but we don't').\n"
            "6. DO flag direct and implied guarantees (e.g. 'Your investment will double without any risk').\n"
            "7. Provide natural, grammatically seamless suggested corrections that fit directly into the original sentence.\n"
            "8. Output strictly valid JSON matching the schema."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": settings.AI_TEMPERATURE,
        }

        try:
            with httpx.Client(timeout=float(settings.AI_TIMEOUT)) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise TimeoutError(f"DeepSeek API request timed out after {settings.AI_TIMEOUT}s.")
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
        Preserves deterministic fallback findings if AI provider is unconfigured or fails.
        """
        provider_name = (settings.AI_PROVIDER or "gemini").lower().strip()
        rules_text = cls.format_rules_for_prompt(approved_rules)

        active_key = (
            settings.DEEPSEEK_API_KEY
            if provider_name == "deepseek"
            else settings.active_gemini_api_key
        )
        if not active_key:
            logger.info("AI semantic analysis skipped: no API key configured.")
            return (
                "AI semantic analysis unavailable (no API key configured); deterministic compliance checks completed.",
                [],
            )

        logger.info(
            f"AI evaluation initiated: provider={provider_name}, "
            f"content_len={len(content)}, approved_rules_count={len(approved_rules)}"
        )

        try:
            if provider_name == "deepseek":
                raw_response = cls.call_deepseek(content, content_type, rules_text)
            else:
                raw_response = cls.call_gemini(content, content_type, rules_text)
        except Exception as exc:
            # Fallback gracefully to deterministic checks if AI provider is unavailable
            error_snippet = redact_sensitive(str(exc))[:60]
            logger.warning(f"AI provider failed ({error_snippet}), falling back to deterministic.")
            return (
                f"AI semantic analysis unavailable ({error_snippet}); deterministic compliance checks completed.",
                [],
            )

        # Parse & Validate with Pydantic
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                except Exception:
                    logger.error("AI response failed JSON fallback extraction.")
                    return (
                        "AI semantic analysis unavailable (invalid JSON response); deterministic compliance checks completed.",
                        [],
                    )
            else:
                logger.error("AI response contained no JSON object.")
                return (
                    "AI semantic analysis unavailable (malformed response); deterministic compliance checks completed.",
                    [],
                )

        try:
            parsed_resp = AIComplianceResponse(**data)
        except Exception as p_err:
            logger.error(f"AI response failed schema validation: {p_err}")
            return (
                "AI semantic analysis unavailable (schema validation failed); deterministic compliance checks completed.",
                [],
            )

        logger.info(f"AI response parsed: received {len(parsed_resp.findings)} candidate findings.")

        # Normalize content for search (normalize smart quotes)
        normalized_content = content.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        validated_findings: List[FindingCreate] = []
        discarded_count = 0

        for candidate in parsed_resp.findings:
            # 1. Clean excerpt of any surrounding quotes
            raw_excerpt = candidate.excerpt.strip().strip('"\'')
            if not raw_excerpt:
                discarded_count += 1
                continue

            # Verify excerpt exists in content
            norm_excerpt = raw_excerpt.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
            matches = list(re.finditer(re.escape(raw_excerpt), content, re.IGNORECASE))
            if not matches:
                matches = list(re.finditer(re.escape(norm_excerpt), normalized_content, re.IGNORECASE))

            if not matches:
                logger.debug(f"Discarding candidate with ungrounded excerpt: '{raw_excerpt[:40]}'")
                discarded_count += 1
                continue

            # 2. Normalize severity
            sev = candidate.severity.lower().strip()
            if sev not in ("critical", "major", "minor", "suggestion"):
                sev = "minor"

            # 3. Grounding enforcement: Resolve guideline reference to an approved rule
            matched_rule = cls.resolve_rule_reference(candidate.guideline_reference, approved_rules)
            if not matched_rule:
                logger.debug(f"Discarding finding with unresolvable reference: '{candidate.guideline_reference}'")
                discarded_count += 1
                continue

            canonical_ref = f"Rule #{matched_rule.id}: {matched_rule.title}"

            # Context safeguard: find occurrence that is not a negation/cautionary or competitor claim
            chosen_match = None
            for m in matches:
                m_start, m_end = m.span()
                m_slice = content[m_start:m_end]
                if deterministic_checker.is_negated_or_cautionary(content, m_start, m_end, m_slice, matched_rule):
                    continue
                if deterministic_checker.is_competitor_claim(content, m_start, m_end, m_slice):
                    continue
                chosen_match = m
                break

            if not chosen_match:
                logger.info(f"Discarding candidate with negated/cautionary/competitor context: '{raw_excerpt[:40]}'")
                discarded_count += 1
                continue

            actual_excerpt = content[chosen_match.start() : chosen_match.end()]
            span = chosen_match.span()

            # Safeguard: do not flag standard conversational social proof (e.g. 'thousands of businesses')
            # as an unverified performance statistic, UNLESS it contains a genuine prohibited claim or empirical metric.
            is_social_proof_phrase = any(sp in actual_excerpt.lower() for sp in ("thousands of businesses", "join thousands", "reliable support", "trusted partners"))
            if is_social_proof_phrase:
                has_prohibited_terms = any(
                    pt in actual_excerpt.lower()
                    for pt in (
                        "guarantee", "risk-free", "risk free", "zero risk", "no risk",
                        "double", "overnight", "rich", "millionaire", "100%", "million",
                        "billion", "fastest", "downtime", "threat", "fraud", "destroy", "crush"
                    )
                )
                is_performance_rule = (
                    "np-comp-004" in (matched_rule.description or "").lower()
                    or "performance" in (matched_rule.title or "").lower()
                    or "statistic" in (matched_rule.description or "").lower()
                )
                if not has_prohibited_terms and is_performance_rule:
                    logger.info(f"Discarding candidate with benign social proof: '{actual_excerpt[:40]}'")
                    discarded_count += 1
                    continue

            # 4. Normalize suggested correction
            correction = candidate.suggested_correction
            if not correction or not correction.strip():
                correction = f"Revise '{actual_excerpt}' to align with {matched_rule.title}."

            finding_obj = FindingCreate(
                severity=sev,
                category=candidate.category.strip() or matched_rule.category,
                excerpt=actual_excerpt,
                explanation=candidate.explanation.strip(),
                guideline_reference=canonical_ref,
                suggested_correction=correction.strip(),
                confidence=candidate.confidence,
                status="open",
            )
            object.__setattr__(finding_obj, "_span", span)
            validated_findings.append(finding_obj)

        logger.info(
            f"AI validation completed: validated={len(validated_findings)}, "
            f"discarded={discarded_count} candidate(s)."
        )

        return parsed_resp.summary, validated_findings


ai_checker = AIChecker()
