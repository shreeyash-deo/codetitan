"""
Structural Governance Rule Extractor
Deterministic document structure analyzer that extracts concrete, authoritative brand rules
from structured guideline manuals (PDF, DOCX, TXT) when AI provider is unavailable,
rate-limited, or quota-exhausted.
"""

import re
from typing import List, Tuple
from app.schemas.rule import ExtractedRuleCandidate


class StructuralRuleExtractor:
    """
    Parses document structure, headings, section numbers, explicit Rule IDs,
    preferred terminology tables, and policy clauses into validated ExtractedRuleCandidate models.
    """

    @classmethod
    def extract_rules(cls, text: str) -> List[ExtractedRuleCandidate]:
        if not text or not text.strip():
            return []

        candidates: List[ExtractedRuleCandidate] = []
        seen_titles = set()

        def add_candidate(c: ExtractedRuleCandidate):
            t_key = c.title.strip().lower()
            if t_key not in seen_titles:
                seen_titles.add(t_key)
                candidates.append(c)

        # ----------------------------------------------------------------------
        # 1. Explicit Rule ID blocks (e.g. Rule ID: NP-COMP-001, Severity: Critical)
        # ----------------------------------------------------------------------
        rule_blocks = re.findall(
            r"(?:(?:(\d+\.\d+)\s+)?([A-Za-z0-9 &/'\"-]+)\n+)?Rule ID:\s*([A-Za-z0-9_-]+)\s*\n+Severity:\s*([A-Za-z]+)\s*\n+(.*?)(?=\n+\d+\.\d+|\n+Rule ID:|\Z)",
            text,
            re.DOTALL,
        )
        for sec_num, sec_title, rule_id, severity, body in rule_blocks:
            title = sec_title.strip() if sec_title else f"Rule {rule_id}"
            body_clean = " ".join(body.strip().split())
            source_ref = f"Section {sec_num} ({rule_id})" if sec_num else rule_id
            sev_lower = severity.lower()

            if "DISC" in rule_id or "disclaimer" in title.lower():
                cat = "Claims and disclaimers"
                subcat = "Mandatory Disclaimers"
            elif any(k in title.lower() for k in ["guarantee", "risk-free", "return", "wealth", "claim"]):
                cat = "Content restrictions"
                subcat = "Prohibited Marketing Claims"
            else:
                cat = "Content restrictions"
                subcat = "Statutory Standards"

            add_candidate(
                ExtractedRuleCandidate(
                    title=title,
                    description=f"[{rule_id} - Severity: {severity}] {body_clean}",
                    category=cat,
                    source_reference=source_ref,
                    confidence=0.98,
                    subCategory=subcat,
                    severity=sev_lower,
                    enforcement_level="Strict" if sev_lower in ("critical", "high") else "Advisory",
                    rationale=f"Mandatory governance standard under {rule_id}",
                )
            )

        # ----------------------------------------------------------------------
        # 2. Required Brand Voice & Communication Tone
        # ----------------------------------------------------------------------
        voice_match = re.search(
            r"(?:2\.1\s+Required Brand Voice|Required Brand Voice|Brand Voice and Tone)\s*\n+(.*?)(?=(?:2\.2|Tone Restrictions|3\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if voice_match:
            voice_text = " ".join(voice_match.group(1).strip().split())
            if len(voice_text) > 20:
                add_candidate(
                    ExtractedRuleCandidate(
                        title="Required Professional Brand Voice",
                        description=voice_text,
                        category="Brand voice and tone",
                        source_reference="Section 2.1",
                        confidence=0.95,
                        subCategory="Voice & Tone",
                        severity="high",
                        enforcement_level="Strict",
                        rationale="Establishes institutional credibility and transparent customer communications.",
                    )
                )

        # ----------------------------------------------------------------------
        # 3. Tone Restrictions / Prohibited Styles
        # ----------------------------------------------------------------------
        tone_rest_match = re.search(
            r"(?:2\.2\s+Tone Restrictions|Tone Restrictions)\s*\n+(.*?)(?=(?:2\.3|3\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if tone_rest_match:
            tone_text = " ".join(tone_rest_match.group(1).strip().split())
            if len(tone_text) > 20:
                add_candidate(
                    ExtractedRuleCandidate(
                        title="Prohibited Sales Messaging and Slang",
                        description=tone_text,
                        category="Brand voice and tone",
                        source_reference="Section 2.2",
                        confidence=0.95,
                        subCategory="Tone Restrictions",
                        severity="high",
                        enforcement_level="Strict",
                        rationale="Prohibits aggressive, get-rich-quick, or misleading urgency styles.",
                    )
                )

        # ----------------------------------------------------------------------
        # 4. Standardized Terminology (Preferred vs Avoid tables)
        # ----------------------------------------------------------------------
        term_section = re.search(
            r"(?:Preferred Term\s*\|\s*Avoid|3\.1\s+Approved Terminology)(.*?)(?=(?:3\.2|4\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        search_scope = term_section.group(0) if term_section else text
        term_matches = re.findall(r"([A-Za-z0-9 -]{3,40})\s*\|\s*([A-Za-z0-9 -]{3,40})", search_scope)
        term_pairs: List[Tuple[str, str]] = []
        for p, a in term_matches:
            p_clean = p.strip()
            a_clean = a.strip()
            if p_clean.lower() in ("preferred term", "novapay global", "brand governance handbook"):
                continue
            term_pairs.append((p_clean, a_clean))

        if term_pairs:
            pairs_desc = "; ".join([f"Use '{p}' instead of '{a}'" for p, a in term_pairs])
            add_candidate(
                ExtractedRuleCandidate(
                    title="Approved Terminology Standards",
                    description=f"Standardized terminology lexicon: {pairs_desc}",
                    category="Approved terminology",
                    source_reference="Section 3.1",
                    confidence=0.96,
                    subCategory="Terminology Lexicon",
                    severity="medium",
                    enforcement_level="Strict",
                    rationale="Eliminates speculative and misleading vernacular in marketing collateral.",
                )
            )

        # ----------------------------------------------------------------------
        # 5. Brand Naming and Capitalization Conventions
        # ----------------------------------------------------------------------
        naming_match = re.search(
            r"(?:3\.2\s+Naming Convention|Naming Convention)\s*\n+(.*?)(?=(?:4\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if naming_match:
            naming_text = " ".join(naming_match.group(1).strip().split())
            if len(naming_text) > 20:
                add_candidate(
                    ExtractedRuleCandidate(
                        title="Brand Naming and Capitalization Conventions",
                        description=naming_text,
                        category="Product facts",
                        source_reference="Section 3.2",
                        confidence=0.94,
                        subCategory="Brand Identity",
                        severity="medium",
                        enforcement_level="Strict",
                        rationale="Ensures uniform naming conventions across all public disclosures.",
                    )
                )

        # ----------------------------------------------------------------------
        # 6. Advertising and Channel Compliance Standards
        # ----------------------------------------------------------------------
        social_match = re.search(
            r"(?:6\.\s+Social Media and Advertising Standards|Social Media and Advertising Standards)\s*\n+(.*?)(?=(?:7\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if social_match:
            social_text = " ".join(social_match.group(1).strip().split())
            if len(social_text) > 20:
                add_candidate(
                    ExtractedRuleCandidate(
                        title="Advertising and Multi-Channel Governance",
                        description=social_text,
                        category="Content restrictions",
                        source_reference="Section 6",
                        confidence=0.92,
                        subCategory="Channel Compliance",
                        severity="high",
                        enforcement_level="Strict",
                        rationale="Ensures short-form social and ad collateral adhere to long-form compliance.",
                    )
                )

        # ----------------------------------------------------------------------
        # 7. Content Approval Workflow & Governance Sign-Off
        # ----------------------------------------------------------------------
        workflow_match = re.search(
            r"(?:7\.\s+Content Approval Workflow|Content Approval Workflow)\s*\n+(.*?)(?=(?:8\.|\Z))",
            text,
            re.DOTALL | re.IGNORECASE,
        )
        if workflow_match:
            wf_text = " ".join(workflow_match.group(1).strip().split())
            if len(wf_text) > 20:
                add_candidate(
                    ExtractedRuleCandidate(
                        title="Mandatory Reviewer Sign-Off Before Publishing",
                        description=wf_text,
                        category="Content restrictions",
                        source_reference="Section 7",
                        confidence=0.95,
                        subCategory="Governance Workflow",
                        severity="critical",
                        enforcement_level="Strict",
                        rationale="All collateral must clear automated compliance and authorized human approval.",
                    )
                )

        # ----------------------------------------------------------------------
        # 8. Generic Numbered Policy / Directive Fallback (for unformatted docs)
        # ----------------------------------------------------------------------
        if len(candidates) < 3:
            policy_lines = re.findall(
                r"(?:^|\n)(?:(?:\d+\.|\*|-)\s+)?([A-Z][A-Za-z0-9 ,'\"]{10,80}:?\s*(?:must|prohibited|never|always|shall|do not)[^\n.]+[\n.])",
                text,
                re.IGNORECASE,
            )
            for i, pline in enumerate(policy_lines[:8]):
                p_clean = " ".join(pline.strip().split())
                if len(p_clean) > 25:
                    add_candidate(
                        ExtractedRuleCandidate(
                            title=f"Policy Requirement {i+1}",
                            description=p_clean,
                            category="Content restrictions",
                            source_reference=f"Clause {i+1}",
                            confidence=0.90,
                            subCategory="Policy Directives",
                            severity="medium",
                            enforcement_level="Strict",
                        )
                    )

        return candidates


structural_extractor = StructuralRuleExtractor()
