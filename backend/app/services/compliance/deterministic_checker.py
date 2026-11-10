import logging
import re
from typing import List, Dict, Any, Optional
from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate

logger = logging.getLogger("brandshield.compliance.deterministic")


class DeterministicChecker:
    @staticmethod
    def extract_quoted_terms(text: str) -> List[str]:
        """Extract strings wrapped in single or double quotes (supporting disclaimers up to 1000 chars)."""
        terms = re.findall(r"['\"]([^'\"]{2,1000})['\"]", text)
        return [t.strip() for t in terms if t.strip()]

    @classmethod
    def extract_prohibited_terms_from_rule(cls, rule: BrandRule) -> List[str]:
        """Extract targeted prohibited terms from quotes or enumerated text patterns in the rule description."""
        terms = []
        for q in cls.extract_quoted_terms(rule.description):
            if len(q) <= 100:
                terms.append(q)
        for q in cls.extract_quoted_terms(rule.title):
            if len(q) <= 100:
                terms.append(q)

        # Prohibited expressions / messaging listed after marker phrases
        marker = re.search(
            r"(?:prohibited\s+(?:expressions|messaging|terms|phrases|words|language)\s+(?:include|includes):?|such\s+as:?|e\.g\.:?|do\s+not\s+use:?|avoid:?)\s*(.+)",
            rule.description,
            re.IGNORECASE,
        )
        if marker:
            tail = marker.group(1).strip()
            # Split on sentence-ending period followed by space and capital, or commas/semicolons
            raw_parts = re.split(r"(?<=[a-zA-Z0-9])\.\s+(?=[A-Z0-9])|[,;]\s+|\n+", tail)
            for part in raw_parts:
                p = part.strip().strip(".!?:;\"'")
                if 3 <= len(p) <= 80 and not p.lower().startswith("do not") and not p.lower().startswith("any "):
                    terms.append(p)

        return list(dict.fromkeys(terms))

    @classmethod
    def check_restricted_terminology(
        cls, content: str, rule: BrandRule
    ) -> List[FindingCreate]:
        """
        Scan content for prohibited phrases specified in restricted terminology or content restriction rules.
        """
        findings: List[FindingCreate] = []
        rule_desc_l = rule.description.lower()
        rule_title_l = rule.title.lower()
        is_restricted_cat = (
            rule.category.lower() in ("restricted terminology", "content restrictions", "brand voice and tone")
            or "prohibit" in rule_title_l
            or "restricted" in rule_title_l
            or "never use" in rule_desc_l
            or "do not use" in rule_desc_l
            or "np-comp" in rule_desc_l
        )

        if not is_restricted_cat:
            return findings

        terms = cls.extract_prohibited_terms_from_rule(rule)
        for term in terms:
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            for match in pattern.finditer(content):
                start, end = match.span()
                matched_excerpt = content[start:end]

                t_low = term.lower()
                rep = "approved terminology"
                if "risk-free" in t_low or "risk free" in t_low:
                    rep = "secure, risk-managed"
                elif "guarantee" in t_low:
                    rep = "proven"
                elif "overnight" in t_low:
                    rep = "sustainably"
                elif "rich" in t_low or "millionaire" in t_low:
                    rep = "sustainable business growth"

                findings.append(
                    FindingCreate(
                        severity="critical" if "critical" in rule_desc_l or "statutory" in rule_desc_l or "must never" in rule_desc_l else "major",
                        category=rule.category,
                        excerpt=matched_excerpt,
                        explanation=f"Content contains prohibited terminology '{matched_excerpt}' flagged under rule '{rule.title}'.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=rep,
                        confidence=1.0,
                        status="open",
                    )
                )

        return findings

    @classmethod
    def check_rule_specific_patterns(
        cls, content: str, rule: BrandRule
    ) -> List[FindingCreate]:
        """
        Grounded checks mapped specifically to active approved rules (e.g. NP-COMP-001, NP-COMP-002,
        NP-COMP-003, NP-COMP-004, Rule 11, and NP-DISC-001).
        """
        findings: List[FindingCreate] = []
        rule_title_l = rule.title.lower()
        rule_desc_l = rule.description.lower()
        canonical_ref = f"Rule #{rule.id}: {rule.title}"
        cat = rule.category

        # Performance Guarantees (NP-COMP-001 / Guaranteed Financial Returns)
        if "np-comp-001" in rule_desc_l or "guaranteed financial returns" in rule_title_l or "guarantee" in rule_title_l:
            guarantee_patterns = [
                (r"\bguaranteed to double\b", "designed to help scale", "Performance guarantees ('guaranteed to double') violate financial compliance standards."),
                (r"\bguarantees?\s+instant\s+settlements?\b", "enables fast settlements", "Guarantees of financial outcomes and instant settlements are prohibited."),
                (r"\bguaranteed success\b", "reliable support", "Guarantees of business or investment success are prohibited."),
                (r"\bguaranteed returns?\b", "target returns", "Guaranteed returns violate financial compliance rules."),
                (r"\bguaranteed profits?\b", "potential growth", "Guaranteed profits violate financial compliance rules."),
                (r"\b100%\s+guaranteed\b", "proven", "Absolute guarantees violate governance standards."),
            ]
            for pat, repl, expl in guarantee_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(
                        FindingCreate(
                            severity="critical",
                            category=cat,
                            excerpt=content[m.start() : m.end()],
                            explanation=expl,
                            guideline_reference=canonical_ref,
                            suggested_correction=repl,
                            confidence=1.0,
                            status="open",
                        )
                    )

        # Risk-Free Claims (NP-COMP-002 / Risk-Free Claims)
        if "np-comp-002" in rule_desc_l or "risk-free claims" in rule_title_l or "risk-free" in rule_title_l:
            risk_patterns = [
                (r"\b100%\s*risk-free\b", "secure, risk-managed", "Financial products must never be described as 100% risk-free."),
                (r"\bzero investment risk\b", "managed risk", "Zero risk claims are non-compliant with financial regulations."),
                (r"\bno chance of losing money\b", "risk-mitigated strategies", "Guarantees against capital loss are prohibited."),
                (r"\bcompletely safe investment\b", "regulated financial service", "Absolute safety claims are prohibited."),
            ]
            for pat, repl, expl in risk_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(
                        FindingCreate(
                            severity="critical",
                            category=cat,
                            excerpt=content[m.start() : m.end()],
                            explanation=expl,
                            guideline_reference=canonical_ref,
                            suggested_correction=repl,
                            confidence=1.0,
                            status="open",
                        )
                    )

        # Unrealistic Wealth / Riches Promises (NP-COMP-003 / Unrealistic Wealth Promises)
        if "np-comp-003" in rule_desc_l or "unrealistic wealth" in rule_title_l or "wealth promises" in rule_title_l:
            wealth_patterns = [
                (r"\brevenue overnight\b", "revenue sustainably over time", "Unrealistic rapid wealth and overnight revenue promises are prohibited."),
                (r"\bunlimited\s+(?:revenue\s+)?growth\b", "sustainable revenue growth", "Exaggerated promises of unlimited revenue growth violate responsible brand governance."),
                (r"\bmake you rich overnight\b", "help build long-term business value", "Get-rich-quick claims are prohibited."),
                (r"\bbecome a millionaire instantly\b", "achieve sustained financial growth", "Instant wealth promises violate compliance."),
                (r"\beffortless growth\b", "sustainable growth", "Claims of effortless growth violate responsible brand governance."),
            ]
            for pat, repl, expl in wealth_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(
                        FindingCreate(
                            severity="major",
                            category=cat,
                            excerpt=content[m.start() : m.end()],
                            explanation=expl,
                            guideline_reference=canonical_ref,
                            suggested_correction=repl,
                            confidence=1.0,
                            status="open",
                        )
                    )

        # Misleading Performance Claims / Superlatives / Absolutes (NP-COMP-004)
        if "np-comp-004" in rule_desc_l or "misleading performance" in rule_title_l or "performance claims" in rule_title_l:
            perf_patterns = [
                (r"\bthe world's fastest\b", "a high-performance", "Unsubstantiated superlative claims ('the world's fastest') are prohibited."),
                (r"(?<!the )\bworld's fastest\b", "high-performance", "Superlative claims require verified third-party empirical evidence."),
                (r"\b\d+[\s\w]*(?:million|billion|k)?\s*transactions\s+per\s+second\b", "high-throughput transaction processing", "Unverified numerical performance claims require verifiable empirical evidence."),
                (r"\b(?:absolutely\s+)?zero\s+downtime\b", "industry-leading uptime", "Absolute zero downtime claims are unverifiable and violate governance rules."),
                (r"\b(?:the\s+)?number\s+(?:one|1)\s+payment\s+provider(?:\s+in\s+[a-zA-Z]+)?\b", "a leading payment provider in India", "Comparative superlative claims require third-party independent verification."),
                (r"\btrusted\s+by\s+100%\s+of\s+businesses\b", "Trusted by businesses nationwide", "Fabricated or absolute user adoption statistics are prohibited."),
                (r"\beliminates?\s+(?:every|all)\s+security\s+threats?\b", "delivers advanced multi-layer security protection", "Absolute claims of eliminating all security threats are unverifiable and prohibited."),
                (r"\beliminates all fraud\b", "delivers advanced fraud prevention", "Absolute claims of eliminating 100% of fraud are unverifiable and prohibited."),
                (r"\bzero transaction failures\b", "industry-leading transaction reliability", "Absolute zero failure claims are unverifiable and prohibited."),
            ]
            for pat, repl, expl in perf_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(
                        FindingCreate(
                            severity="major",
                            category=cat,
                            excerpt=content[m.start() : m.end()],
                            explanation=expl,
                            guideline_reference=canonical_ref,
                            suggested_correction=repl,
                            confidence=1.0,
                            status="open",
                        )
                    )

        # Prohibited Sales Messaging and Slang (Rule #11 / Aggressive Language)
        if "prohibited sales messaging" in rule_title_l or "aggressive sales language" in rule_desc_l:
            sales_patterns = [
                (r"\bdestroys? (?:every |all |the )?competitors?(?: in the market)?\b", "Leads the market with reliable solutions", "Excessively aggressive sales language violates brand voice standards."),
                (r"\bcrush(?:es)? the competition\b", "competes effectively", "Aggressive competitive language violates brand tone requirements."),
            ]
            for pat, repl, expl in sales_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    findings.append(
                        FindingCreate(
                            severity="major",
                            category=cat,
                            excerpt=content[m.start() : m.end()],
                            explanation=expl,
                            guideline_reference=canonical_ref,
                            suggested_correction=repl,
                            confidence=1.0,
                            status="open",
                        )
                    )

        # Financial Risk Disclaimer (NP-DISC-001)
        if "np-disc" in rule_desc_l or "financial risk disclaimer" in rule_title_l:
            disclaimer_quotes = cls.extract_quoted_terms(rule.description)
            approved_disc = None
            for q in disclaimer_quotes:
                if len(q) >= 20:
                    approved_disc = q
                    break

            if approved_disc:
                clean_content = " ".join(content.split()).lower()
                clean_disc = " ".join(approved_disc.split()).lower()
                financial_keywords = ["payment", "revenue", "investment", "financial", "profits", "earnings", "returns", "money", "transaction", "settlement"]
                touches_finance = any(k in clean_content for k in financial_keywords)
                if touches_finance and clean_disc not in clean_content:
                    findings.append(
                        FindingCreate(
                            severity="critical",
                            category=cat,
                            excerpt="[Missing Regulatory Disclaimer]",
                            explanation=f"Missing mandatory regulatory disclaimer required by rule '{rule.title}'.",
                            guideline_reference=canonical_ref,
                            suggested_correction=f"\n\nDisclaimer: {approved_disc}",
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
        Check rules requiring mandatory disclosure footers.
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
                continue

            clean_content = " ".join(content.split()).lower()
            clean_disclaimer = " ".join(disclaimer_text.split()).lower()

            if clean_disclaimer not in clean_content:
                findings.append(
                    FindingCreate(
                        severity="critical",
                        category=rule.category,
                        excerpt="[Missing Regulatory Disclaimer]",
                        explanation=f"Missing mandatory regulatory disclaimer required by rule '{rule.title}'.",
                        guideline_reference=f"Rule #{rule.id}: {rule.title}",
                        suggested_correction=f"\n\nDisclaimer: {disclaimer_text}",
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
        raw_findings: List[FindingCreate] = []
        for rule in approved_rules:
            raw_findings.extend(cls.check_restricted_terminology(content, rule))
            raw_findings.extend(cls.check_rule_specific_patterns(content, rule))
            raw_findings.extend(cls.check_preferred_vs_prohibited(content, rule))
            raw_findings.extend(cls.check_required_disclaimers(content, rule))
            raw_findings.extend(cls.check_character_limits(content, rule, content_type))

        # Sort by excerpt length descending to prioritize longer and more specific phrases
        sorted_findings = sorted(raw_findings, key=lambda f: len(f.excerpt), reverse=True)
        deduped: List[FindingCreate] = []
        seen_spans = []

        for f in sorted_findings:
            if f.excerpt == "[Missing Regulatory Disclaimer]":
                # Only include one missing disclaimer finding
                if not any(d.excerpt == "[Missing Regulatory Disclaimer]" for d in deduped):
                    deduped.append(f)
                continue

            pat = re.compile(rf"\b{re.escape(f.excerpt)}\b", re.IGNORECASE)
            matched_spans = [m.span() for m in pat.finditer(content)]
            if not matched_spans:
                continue

            for start, end in matched_spans:
                # Suppress if fully enclosed by a longer matched finding
                is_subspan = any(s <= start and end <= e for (s, e) in seen_spans)
                if not is_subspan:
                    seen_spans.append((start, end))
                    f_copy = f.model_copy(update={"excerpt": content[start:end]})
                    deduped.append(f_copy)

        # Sort findings by order of appearance in content (disclaimer placed at end)
        def sort_key(f: FindingCreate):
            if f.excerpt == "[Missing Regulatory Disclaimer]":
                return 999999
            pos = content.find(f.excerpt)
            return pos if pos != -1 else 999999

        deduped.sort(key=sort_key)
        logger.info(
            f"Deterministic evaluation complete: approved_rules={len(approved_rules)}, "
            f"raw_findings={len(raw_findings)}, deduped_findings={len(deduped)}"
        )
        return deduped


deterministic_checker = DeterministicChecker()
