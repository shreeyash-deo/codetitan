import re
from typing import List, Dict, Any, Optional
from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate


class DeterministicChecker:
    @staticmethod
    def extract_quoted_terms(text: str) -> List[str]:
        """Extract strings wrapped in single or double quotes."""
        terms = re.findall(r"['\"]([^'\"]{2,80})['\"]", text)
        return [t.strip() for t in terms if t.strip()]

    @classmethod
    def check_restricted_terminology(
        cls, content: str, rule: BrandRule
    ) -> List[FindingCreate]:
        """
        Scan content for prohibited phrases specified in restricted terminology or content restriction rules.
        """
        findings: List[FindingCreate] = []
        is_restricted_cat = (
            rule.category.lower() in ("restricted terminology", "content restrictions")
            or "prohibit" in rule.title.lower()
            or "restricted" in rule.title.lower()
            or "never use" in rule.description.lower()
            or "do not use" in rule.description.lower()
        )

        if not is_restricted_cat:
            return findings

        # Extract targeted terms from quotes, or fallback to patterns
        terms = cls.extract_quoted_terms(rule.description)
        if not terms:
            terms = cls.extract_quoted_terms(rule.title)

        # If still no quotes, look for comma-separated terms after "e.g." or "words:"
        if not terms:
            match = re.search(r"(?:words|terms|such as|e\.g\.:?)\s*([a-zA-Z0-9\s,\-_]+)", rule.description, re.IGNORECASE)
            if match:
                terms = [t.strip() for t in match.group(1).split(",") if 2 <= len(t.strip()) <= 40]

        for term in terms:
            # Word boundary matching (case-insensitive)
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for match in pattern.finditer(content):
                start, end = match.span()
                matched_excerpt = content[start:end]

                findings.append(
                    FindingCreate(
                        severity="critical" if "statutory" in rule.description.lower() or "legal" in rule.description.lower() else "major",
                        category=rule.category,
                        excerpt=matched_excerpt,
                        explanation=f"Content contains prohibited terminology '{term}' flagged under rule '{rule.title}'.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=f"Remove '{matched_excerpt}' or substitute with approved brand language.",
                        confidence=1.0,
                        status="open",
                    )
                )

        return findings

    @classmethod
    def check_preferred_vs_prohibited(
        cls, content: str, rule: BrandRule
    ) -> List[FindingCreate]:
        """
        Check rules that specify 'Use X instead of Y'.
        """
        findings: List[FindingCreate] = []
        pattern = re.search(
            r"use\s+['\"]([^'\"]+)['\"]\s+instead\s+of\s+['\"]([^'\"]+)['\"]",
            rule.description,
            re.IGNORECASE,
        )
        if pattern:
            preferred, prohibited = pattern.group(1).strip(), pattern.group(2).strip()
            regex = re.compile(rf"\b{re.escape(prohibited)}\b", re.IGNORECASE)
            for match in regex.finditer(content):
                start, end = match.span()
                matched_excerpt = content[start:end]
                findings.append(
                    FindingCreate(
                        severity="major",
                        category=rule.category,
                        excerpt=matched_excerpt,
                        explanation=f"Found unapproved phrase '{matched_excerpt}'. Rule '{rule.title}' specifies using '{preferred}' instead.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=preferred,
                        confidence=1.0,
                        status="open",
                    )
                )
        return findings

    @classmethod
    def check_required_disclaimers(
        cls, content: str, rule: BrandRule
    ) -> List[FindingCreate]:
        """
        Check rules in 'Claims and disclaimers' requiring mandatory disclosure footers.
        """
        findings: List[FindingCreate] = []
        is_disclaimer_rule = (
            rule.category.lower() in ("claims and disclaimers", "claims & disclaimers")
            or "disclaimer" in rule.title.lower()
            or "mandatory" in rule.title.lower()
            or "always state" in rule.description.lower()
            or "must include" in rule.description.lower()
        )

        if not is_disclaimer_rule:
            return findings

        # Extract the required disclaimer string
        quoted = cls.extract_quoted_terms(rule.description)
        for disclaimer_text in quoted:
            if len(disclaimer_text) < 15:
                continue  # Skip short words that aren't disclaimer statements

            # Check if disclaimer is present (normalized whitespace)
            clean_content = " ".join(content.split()).lower()
            clean_disclaimer = " ".join(disclaimer_text.split()).lower()

            if clean_disclaimer not in clean_content:
                # Flag the missing disclaimer
                findings.append(
                    FindingCreate(
                        severity="critical",
                        category=rule.category,
                        excerpt=content[-min(len(content), 80):] if content else "[End of Content]",
                        explanation=f"Missing mandatory regulatory disclaimer required by rule '{rule.title}'.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=f"Include mandatory disclaimer: '{disclaimer_text}'",
                        confidence=1.0,
                        status="open",
                    )
                )

        return findings

    @classmethod
    def check_character_limits(
        cls, content: str, rule: BrandRule, content_type: str
    ) -> List[FindingCreate]:
        """
        Check for explicit character limit requirements (e.g. social media max length).
        """
        findings: List[FindingCreate] = []
        match = re.search(r"(?:maximum|max|limit of)\s*(\d{2,4})\s*characters", rule.description, re.IGNORECASE)
        if match:
            limit = int(match.group(1))
            if len(content) > limit:
                findings.append(
                    FindingCreate(
                        severity="major",
                        category=rule.category,
                        excerpt=content[:80] + "...",
                        explanation=f"Content length ({len(content)} characters) exceeds the maximum limit of {limit} characters defined in rule '{rule.title}'.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=f"Trim copy to within {limit} characters.",
                        confidence=1.0,
                        status="open",
                    )
                )
        return findings

    @classmethod
    def evaluate(
        cls, content: str, content_type: str, approved_rules: List[BrandRule]
    ) -> List[FindingCreate]:
        """
        Run all Python deterministic checks across approved rules.
        """
        all_findings: List[FindingCreate] = []
        for rule in approved_rules:
            all_findings.extend(cls.check_restricted_terminology(content, rule))
            all_findings.extend(cls.check_preferred_vs_prohibited(content, rule))
            all_findings.extend(cls.check_required_disclaimers(content, rule))
            all_findings.extend(cls.check_character_limits(content, rule, content_type))
        return all_findings


deterministic_checker = DeterministicChecker()
