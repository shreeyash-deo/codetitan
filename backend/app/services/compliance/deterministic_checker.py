import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate

logger = logging.getLogger("brandshield.compliance.deterministic")


class DeterministicChecker:
    @staticmethod
    def extract_rule_severity(rule: BrandRule, default: str = "major") -> str:
        """
        Dynamically derive severity level from rule attributes, description, or title.
        Never hardcode brand-specific rules to fixed severities.
        """
        raw_sev = getattr(rule, "severity", None)
        if raw_sev and str(raw_sev).lower() in ("critical", "major", "minor", "suggestion"):
            return str(raw_sev).lower()

        combined_text = f"{rule.title} {rule.description}".lower()
        if any(k in combined_text for k in ("critical", "statutory", "must never", "strictly prohibited", "mandatory", "non-negotiable")):
            return "critical"
        if any(k in combined_text for k in ("minor", "low priority", "guideline only", "advisory")):
            return "minor"
        if any(k in combined_text for k in ("suggestion", "optional", "recommended")):
            return "suggestion"
        return default

    @staticmethod
    def extract_quoted_terms(text: str) -> List[str]:
        """Extract strings wrapped in single or double quotes (supporting disclaimers up to 1000 chars)."""
        terms = re.findall(r"['\"]([^'\"]{2,1000})['\"]", text)
        return [t.strip() for t in terms if t.strip()]

    @classmethod
    def get_sentence_context(cls, content: str, start: int, end: int) -> Tuple[str, str, str]:
        """
        Returns (sentence, pre_in_sentence, post_in_sentence) around the match span [start, end].
        Correctly detects sentence boundaries using punctuation (. ! ?) and line breaks.
        """
        left_text = content[:start]
        s_start = 0
        for m in re.finditer(r"(?:[.!?]\s+|\n+)", left_text):
            s_start = m.end()

        right_text = content[end:]
        m_end = re.search(r"(?:[.!?](?:\s+|$)|[\n\r]+)", right_text)
        s_end = end + m_end.start() + 1 if m_end else len(content)

        sentence = content[s_start:s_end].strip()
        pre_in_sentence = content[s_start:start]
        post_in_sentence = content[end:s_end]
        return sentence, pre_in_sentence, post_in_sentence

    @classmethod
    def is_negated_or_cautionary(
        cls, content: str, start: int, end: int, matched_text: str, rule: Optional[BrandRule] = None
    ) -> bool:
        """
        Context-aware inspection to determine if a matched keyword is used in a compliant,
        cautionary, or negated disclaimer context (e.g. 'We do not guarantee financial returns').
        """
        sentence, pre, post = cls.get_sentence_context(content, start, end)
        m_low = matched_text.lower()

        # 1. Imperative invitation trap: "Do not miss our guaranteed returns!"
        if re.search(r"\b(do\s+not|don't)\s+(?:miss|hesitate|forget|pass\s+up|delay|wait)\b", pre, re.IGNORECASE):
            return False

        # 1b. Correlative/additive emphasis trap: "not only guaranteed returns", "not merely guaranteed profits", "not just 100% risk-free"
        if re.search(r"\bnot\s+(?:only|merely|just|simply)\b(?:\s+\w+){0,2}\s*$", pre.strip(), re.IGNORECASE):
            return False

        # 2. Risk claim vs. Negation:
        # If the matched text itself asserts "without any risk", "zero risk", "risk-free",
        # it is claiming no risk exists. That is only cautionary if explicitly disclaimed:
        # e.g., "is not risk-free", "not without risk", "no investment is risk-free".
        is_risk_elimination_phrase = any(
            rk in m_low for rk in ("without risk", "without any risk", "with no risk", "zero risk", "risk-free", "risk free")
        )
        if is_risk_elimination_phrase:
            if re.search(
                r"\b(?:is\s+not|are\s+not|was\s+not|were\s+not|not|never)\s+(?:completely\s+)?risk-?free\b",
                sentence,
                re.IGNORECASE,
            ):
                return True
            if re.search(r"\b(?:not|never)\s+without\s+risk\b", sentence, re.IGNORECASE):
                return True
            if re.search(
                r"\b(?:no|neither)\s+(?:investment|product|service)\s+is\s+(?:completely\s+)?risk-?free\b",
                sentence,
                re.IGNORECASE,
            ):
                return True
            # Otherwise, asserting zero risk is a genuine violation of risk-free guidelines
            return False

        # 3. Direct verbal negation preceding the match:
        # e.g. "We do not guarantee", "Company does not offer guaranteed", "We cannot guarantee", "never guarantee"
        if re.search(
            r"\b(do\s+not|does\s+not|did\s+not|don't|doesn't|cannot|can't|never|will\s+not|won't|shall\s+not|refuse\s+to|fail\s+to)\s+(?:\w+\s+){0,3}$",
            pre,
            re.IGNORECASE,
        ):
            return True

        # 4. Passive negation preceding the match:
        # e.g. "Returns are not guaranteed", "Profits are never guaranteed"
        if re.search(
            r"\b(is\s+not|are\s+not|was\s+not|were\s+not|not|never)\s+(?:\w+\s+){0,2}$",
            pre,
            re.IGNORECASE,
        ):
            return True

        # 5. Direct noun/clause negation:
        # e.g. "is no guarantee of", "makes no guarantee", "offers no guarantee", "without any guarantee"
        if re.search(
            r"\b(?:is\s+no|are\s+no|offers?\s+no|makes?\s+no|provides?\s+no|gives?\s+no|with\s+no|without\s+(?:any\s+)?)\s+(?:\w+\s+){0,2}$",
            pre,
            re.IGNORECASE,
        ):
            return True

        # 6. Disclaimers and regulatory caution:
        if re.search(r"\b(disclaim|disclaims|disclaimed|disclaiming)\s+(?:\w+\s+){0,3}$", pre, re.IGNORECASE):
            return True

        if re.search(
            r"\b(?:past performance (?:is|offers?|provides?) (?:not|no)|not a guarantee of future|subject to market risks? and (?:are|is) not guaranteed|investments? (?:are|is) subject to market risks?)\b",
            sentence,
            re.IGNORECASE,
        ):
            return True

        return False

    @classmethod
    def is_competitor_claim(cls, content: str, start: int, end: int, matched_text: str) -> bool:
        """
        Distinguish competitor claims from claims made by our own brand.
        e.g. 'Our competitors guarantee returns, but we don't.'
        """
        sentence, pre, post = cls.get_sentence_context(content, start, end)

        competitor_pattern = (
            r"\b(?:our\s+|the\s+)?(?:competitors?|rivals?|"
            r"other\s+(?:companies|platforms?|providers?|services?|apps?|firms?)|"
            r"legacy\s+(?:banks?|systems?|providers?)|"
            r"traditional\s+banks?)\b"
        )

        if not re.search(competitor_pattern, sentence, re.IGNORECASE):
            return False

        # If the immediate subject right before the match is our brand ("we", "our platform", etc.):
        # e.g. "... but we guarantee returns" or "Unlike competitors, we guarantee"
        brand_subject_before_match = re.search(
            r"\b(?:we|our\s+(?:platform|team|company|service|firm|app|system|brand|product)|us)\s+(?:also\s+)?(?:do\s+)?$",
            pre.strip(),
            re.IGNORECASE,
        )
        if brand_subject_before_match:
            # This is our brand's claim, NOT a competitor claim!
            return False

        # Check if the competitor is the subject of the clause containing the match:
        # e.g. "Our competitors guarantee returns, but we don't." or "but ApexWealth doesn't"
        competitor_in_pre = re.search(competitor_pattern, pre, re.IGNORECASE)
        contrast_disavowal_in_post = re.search(
            r"\b(?:but\s+(?:we|our\s+\w+|\w+)\s+(?:do\s+not|don't|never|cannot|does\s+not|doesn't)|"
            r"while\s+(?:we|our\s+\w+|\w+)\s+(?:do\s+not|don't|never|cannot|does\s+not|doesn't)|"
            r"whereas\s+(?:we|our\s+\w+|\w+)\s+(?:do\s+not|don't|never|cannot|does\s+not|doesn't)|"
            r"unlike\s+us|(?:we|our\s+\w+|\w+)\s+(?:do\s+not|don't|never|cannot|does\s+not|doesn't))\b",
            post,
            re.IGNORECASE,
        )

        if competitor_in_pre and contrast_disavowal_in_post:
            return True

        # Check "Unlike competitors who guarantee returns, [we / ApexWealth ...] ..."
        if re.search(r"^\s*unlike\s+(?:our\s+|the\s+)?(?:competitors?|rivals?|other\b)", pre, re.IGNORECASE):
            if re.search(r"\bwho\b", pre, re.IGNORECASE) and not re.search(r",", pre):
                return True

        return False

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
            or "must not" in rule_desc_l
            or "not allowed" in rule_desc_l
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

                # Context-aware inspection: skip if negated, cautionary, or competitor statement
                if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                    continue
                if cls.is_competitor_claim(content, start, end, matched_excerpt):
                    continue

                t_low = term.lower()
                rep = "reliable alternative"
                if "risk-free" in t_low or "risk free" in t_low:
                    rep = "secure, risk-managed"
                elif "guarantee" in t_low:
                    rep = "target" if "return" in t_low else "proven"
                elif "overnight" in t_low:
                    rep = "sustainably over time"
                elif "rich" in t_low or "millionaire" in t_low:
                    rep = "sustainable business growth"
                elif "crazy secret" in t_low:
                    rep = "proven methodology"
                elif "the single best" in t_low:
                    rep = "a leading"
                elif "double" in t_low:
                    rep = "scale sustainably"
                elif "wealth" in t_low:
                    rep = "build wealth sustainably" if "build" in t_low else "sustainable wealth creation"
                elif "effortless" in t_low:
                    rep = "systematic"
                else:
                    rep = "responsible alternative"

                f_item = FindingCreate(
                    severity=cls.extract_rule_severity(rule, default="major"),
                    category=rule.category,
                    excerpt=matched_excerpt,
                    explanation=f"Content contains prohibited terminology '{matched_excerpt}' flagged under rule '{rule.title}'.",
                    guideline_reference=f"Rule #{rule.id}: {rule.title}",
                    suggested_correction=rep,
                    confidence=1.0,
                    status="open",
                )
                object.__setattr__(f_item, "_span", (start, end))
                findings.append(f_item)

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

        # Performance Guarantees (Guaranteed Financial Returns / Promised Outcomes)
        is_guarantee_concept = (
            "np-comp-001" in rule_desc_l
            or "guaranteed financial returns" in rule_title_l
            or "guarantee" in rule_title_l
            or "guarantee" in rule_desc_l
            or "promised return" in rule_desc_l
            or "promised outcome" in rule_desc_l
        )
        if is_guarantee_concept:
            guarantee_patterns = [
                (r"\bguaranteed to double\b", "designed to help scale", "Performance guarantees ('guaranteed to double') violate financial compliance standards."),
                (r"\bguarantees?\s+instant\s+settlements?\b", "enables fast settlements", "Guarantees of financial outcomes and instant settlements are prohibited."),
                (r"\bguaranteed success\b", "reliable support", "Guarantees of business or investment success are prohibited."),
                (r"\bguarantees?\s+(?:\d+%\s+)?returns?\b", "target returns", "Guaranteed returns violate financial compliance rules."),
                (r"\bguaranteed returns?\b", "target returns", "Guaranteed returns violate financial compliance rules."),
                (r"\bguarantees?\s+(?:\d+%\s+)?profits?\b", "potential growth", "Guaranteed profits violate financial compliance rules."),
                (r"\bguaranteed profits?\b", "potential growth", "Guaranteed profits violate financial compliance rules."),
                (r"\b100%\s+guaranteed\b", "proven", "Absolute guarantees violate governance standards."),
                # Implied guarantees
                (r"\b(?:will|to)\s+double\s+(?:your\s+)?(?:investment|revenue|money|returns?|capital)\b", "aims to scale your business sustainably", "Implied performance guarantees violate financial compliance standards."),
                (r"\b(?:investment|revenue|money|returns?|capital)\s+will\s+double\b", "investment is structured for growth", "Implied performance guarantees violate financial compliance standards."),
            ]
            sev_guarantee = cls.extract_rule_severity(rule, default="critical")
            for pat, repl, expl in guarantee_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    start, end = m.span()
                    matched_excerpt = content[start:end]
                    if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                        continue
                    if cls.is_competitor_claim(content, start, end, matched_excerpt):
                        continue
                    f_item = FindingCreate(
                        severity=sev_guarantee,
                        category=cat,
                        excerpt=matched_excerpt,
                        explanation=expl,
                        guideline_reference=canonical_ref,
                        suggested_correction=repl,
                        confidence=1.0,
                        status="open",
                    )
                    object.__setattr__(f_item, "_span", (start, end))
                    findings.append(f_item)

        # Risk-Free Claims / Absolute Safety / Market Immunity
        is_risk_concept = (
            "np-comp-002" in rule_desc_l
            or "risk-free claims" in rule_title_l
            or "risk-free" in rule_title_l
            or "risk-free" in rule_desc_l
            or "risk" in rule_title_l
            or "market uncertainty" in rule_desc_l
            or "market conditions" in rule_desc_l
            or "zero risk" in rule_desc_l
        )
        if is_risk_concept:
            risk_patterns = [
                (r"\b100%\s*risk-free\b", "secure, risk-managed", "Financial products must never be described as 100% risk-free."),
                (r"\bzero investment risk\b", "managed risk", "Zero risk claims are non-compliant with financial regulations."),
                (r"\bno chance of losing money\b", "risk-mitigated strategies", "Guarantees against capital loss are prohibited."),
                (r"\bcompletely safe investment\b", "regulated financial service", "Absolute safety claims are prohibited."),
                # Contextual implied risk elimination & market immunity
                (r"\bwithout (?:any )?risk\b", "with managed risk", "Claims that eliminate financial risk violate compliance regulations."),
                (r"\bwith zero risk\b", "with risk mitigation", "Claims of zero investment risk violate financial regulations."),
                (r"\bwith no risk\b", "with managed risk", "Absolute risk elimination claims violate financial regulations."),
                (r"\bregardless\s+of\s+market\s+conditions\b", "aligned with your risk tolerance", "Claims implying immunity to market conditions violate financial risk disclosure standards."),
                (r"\bwithout\s+worrying\s+about\s+market\s+(?:uncertainty|volatility|conditions|risks?)\b", "with strategies designed to navigate market volatility", "Claims implying complete insulation from market uncertainty mislead investors regarding market risk."),
                (r"\bimmune\s+to\s+market\s+(?:volatility|conditions|dips?|crashes?)\b", "diversified against market volatility", "Claims of immunity to market volatility violate financial regulations."),
                (r"\bmarket-?proof\b", "risk-mitigated", "Claims that an investment or product is market-proof violate regulatory standards."),
            ]
            sev_risk = cls.extract_rule_severity(rule, default="critical")
            for pat, repl, expl in risk_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    start, end = m.span()
                    matched_excerpt = content[start:end]
                    if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                        continue
                    if cls.is_competitor_claim(content, start, end, matched_excerpt):
                        continue
                    f_item = FindingCreate(
                        severity=sev_risk,
                        category=cat,
                        excerpt=matched_excerpt,
                        explanation=expl,
                        guideline_reference=canonical_ref,
                        suggested_correction=repl,
                        confidence=1.0,
                        status="open",
                    )
                    object.__setattr__(f_item, "_span", (start, end))
                    findings.append(f_item)

        # Unrealistic Wealth / Effortless Growth / Passive Income
        is_wealth_concept = (
            "np-comp-003" in rule_desc_l
            or "unrealistic wealth" in rule_title_l
            or "wealth promises" in rule_title_l
            or "wealth" in rule_title_l
            or "wealth" in rule_desc_l
            or "passive income" in rule_desc_l
            or "effortless" in rule_desc_l
            or "get-rich" in rule_desc_l
        )
        if is_wealth_concept:
            wealth_patterns = [
                (r"\b(?:build|create|make|accumulate|generate)\s+wealth\s+effortlessly\b", "build wealth sustainably", "Promises of effortless wealth creation violate responsible brand guidelines."),
                (r"\bwealth\s+creation\s+(?:is\s+)?effortless\b", "wealth creation requires discipline", "Claims that wealth creation is effortless are misleading and non-compliant."),
                (r"\bmoney\s+works?\s+(?:tirelessly\s+)?while\s+you\s+sleep\b", "portfolio is managed continuously", "Implied passive wealth promises ('money works while you sleep') violate responsible promotion standards."),
                (r"\bwatch\s+your\s+(?:money|funds?|wealth|financial\s+future)\s+grow\s+(?:effortlessly|on\s+autopilot|while\s+you\s+sleep)\b", "plan your financial future with expert guidance", "Unrealistic claims of automated financial growth violate compliance rules."),
                (r"\bwithout\s+needing\s+to\s+understand\s+the\s+markets?\b", "with professional market insights", "Claims implying financial success without market awareness or understanding are misleading."),
                (r"\brevenue overnight\b", "revenue sustainably over time", "Unrealistic rapid wealth and overnight revenue promises are prohibited."),
                (r"\bunlimited\s+(?:revenue\s+)?growth\b", "sustainable revenue growth", "Exaggerated promises of unlimited revenue growth violate responsible brand governance."),
                (r"\bmake you rich overnight\b", "help build long-term business value", "Get-rich-quick claims are prohibited."),
                (r"\bbecome a millionaire instantly\b", "achieve sustained financial growth", "Instant wealth promises violate compliance."),
                (r"\beffortless growth\b", "sustainable growth", "Claims of effortless growth violate responsible brand governance."),
                (r"\bpassive\s+income\s+(?:on\s+autopilot|without\s+effort)\b", "managed investment income", "Promises of effortless passive income violate financial compliance regulations."),
            ]
            sev_wealth = cls.extract_rule_severity(rule, default="major")
            for pat, repl, expl in wealth_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    start, end = m.span()
                    matched_excerpt = content[start:end]
                    if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                        continue
                    if cls.is_competitor_claim(content, start, end, matched_excerpt):
                        continue
                    f_item = FindingCreate(
                        severity=sev_wealth,
                        category=cat,
                        excerpt=matched_excerpt,
                        explanation=expl,
                        guideline_reference=canonical_ref,
                        suggested_correction=repl,
                        confidence=1.0,
                        status="open",
                    )
                    object.__setattr__(f_item, "_span", (start, end))
                    findings.append(f_item)

        # Misleading Performance Claims / Superlatives / Absolutes (NP-COMP-004)
        is_perf_concept = (
            "np-comp-004" in rule_desc_l
            or "misleading performance" in rule_title_l
            or "performance claims" in rule_title_l
            or "performance" in rule_title_l
            or "superlative" in rule_desc_l
            or "fastest" in rule_desc_l
            or "throughput" in rule_desc_l
        )
        if is_perf_concept:
            perf_patterns = [
                (r"\bthe world's fastest\b", "a high-performance", "Unsubstantiated superlative claims ('the world's fastest') are prohibited."),
                (r"(?<!the )\bworld's fastest\b", "high-performance", "Superlative claims require verified third-party empirical evidence."),
                (r"\bgrow\s+faster\s+than\s+ever\b", "grow steadily", "Unsubstantiated accelerated growth claims violate performance communication standards."),
                (r"\b\d+[\s\w]*(?:million|billion|k)?\s*transactions\s+per\s+second\b", "high-throughput transaction processing", "Unverified numerical performance claims require verifiable empirical evidence."),
                (r"\b(?:absolutely\s+)?zero\s+downtime\b", "industry-leading uptime", "Absolute zero downtime claims are unverifiable and violate governance rules."),
                (r"\b(?:the\s+)?number\s+(?:one|1)\s+payment\s+provider(?:\s+in\s+[a-zA-Z]+)?\b", "a leading payment provider", "Comparative superlative claims require third-party independent verification."),
                (r"\btrusted\s+by\s+100%\s+of\s+businesses\b", "Trusted by businesses nationwide", "Fabricated or absolute user adoption statistics are prohibited."),
                (r"\beliminates?\s+(?:every|all)\s+security\s+threats?\b", "delivers advanced multi-layer security protection", "Absolute claims of eliminating all security threats are unverifiable and prohibited."),
                (r"\beliminates all fraud\b", "delivers advanced fraud prevention", "Absolute claims of eliminating 100% of fraud are unverifiable and prohibited."),
                (r"\bzero transaction failures\b", "industry-leading transaction reliability", "Absolute zero failure claims are unverifiable and prohibited."),
            ]
            sev_perf = cls.extract_rule_severity(rule, default="major")
            for pat, repl, expl in perf_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    start, end = m.span()
                    matched_excerpt = content[start:end]
                    if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                        continue
                    if cls.is_competitor_claim(content, start, end, matched_excerpt):
                        continue
                    f_item = FindingCreate(
                        severity=sev_perf,
                        category=cat,
                        excerpt=matched_excerpt,
                        explanation=expl,
                        guideline_reference=canonical_ref,
                        suggested_correction=repl,
                        confidence=1.0,
                        status="open",
                    )
                    object.__setattr__(f_item, "_span", (start, end))
                    findings.append(f_item)

        # Prohibited Sales Messaging and Slang (Rule #11 / Aggressive Language)
        is_sales_concept = (
            "prohibited sales messaging" in rule_title_l
            or "aggressive sales language" in rule_desc_l
            or "aggressive" in rule_title_l
            or "aggressive" in rule_desc_l
            or "slang" in rule_title_l
        )
        if is_sales_concept:
            sales_patterns = [
                (r"\bdestroys? (?:every |all |the )?competitors?(?: in the market)?\b", "Leads the market with reliable solutions", "Excessively aggressive sales language violates brand voice standards."),
                (r"\bcrush(?:es)? the competition\b", "competes effectively", "Aggressive competitive language violates brand tone requirements."),
            ]
            sev_sales = cls.extract_rule_severity(rule, default="major")
            for pat, repl, expl in sales_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    start, end = m.span()
                    matched_excerpt = content[start:end]
                    if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                        continue
                    if cls.is_competitor_claim(content, start, end, matched_excerpt):
                        continue
                    f_item = FindingCreate(
                        severity=sev_sales,
                        category=cat,
                        excerpt=matched_excerpt,
                        explanation=expl,
                        guideline_reference=canonical_ref,
                        suggested_correction=repl,
                        confidence=1.0,
                        status="open",
                    )
                    object.__setattr__(f_item, "_span", (start, end))
                    findings.append(f_item)

        # Financial / Regulatory Risk Disclaimer
        is_disc_concept = (
            "np-disc" in rule_desc_l
            or "disclaimer" in rule_title_l
            or "mandatory disclosure" in rule_desc_l
            or "disclosure" in rule_title_l
        )
        if is_disc_concept:
            disclaimer_quotes = cls.extract_quoted_terms(rule.description)
            approved_disc = None
            for q in disclaimer_quotes:
                if len(q) >= 20:
                    approved_disc = q
                    break

            if approved_disc:
                clean_content = " ".join(content.split()).lower()
                clean_disc = " ".join(approved_disc.split()).lower()
                financial_keywords = ["payment", "revenue", "investment", "financial", "profits", "earnings", "returns", "money", "transaction", "settlement", "wealth", "portfolio", "capital"]
                touches_finance = any(k in clean_content for k in financial_keywords)
                if touches_finance and clean_disc not in clean_content:
                    findings.append(
                        FindingCreate(
                            severity=cls.extract_rule_severity(rule, default="critical"),
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
                if cls.is_negated_or_cautionary(content, start, end, matched_excerpt, rule):
                    continue
                if cls.is_competitor_claim(content, start, end, matched_excerpt):
                    continue
                f_item = FindingCreate(
                    severity=cls.extract_rule_severity(rule, default="major"),
                    category=rule.category,
                    excerpt=matched_excerpt,
                    explanation=f"Found unapproved phrase '{matched_excerpt}'. Rule '{rule.title}' specifies using '{preferred}' instead.",
                    guideline_reference=f"Rule #{rule.id}: {rule.title}",
                    suggested_correction=preferred,
                    confidence=1.0,
                    status="open",
                )
                object.__setattr__(f_item, "_span", (start, end))
                findings.append(f_item)
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
                        severity=cls.extract_rule_severity(rule, default="critical"),
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
                        severity=cls.extract_rule_severity(rule, default="major"),
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
                    object.__setattr__(f, "_span", (len(content), len(content)))
                    deduped.append(f)
                continue

            span = getattr(f, "_span", None)
            spans_to_check = [span] if span and isinstance(span, tuple) else []
            if not spans_to_check:
                pat = re.compile(rf"\b{re.escape(f.excerpt)}\b", re.IGNORECASE)
                spans_to_check = [m.span() for m in pat.finditer(content)]

            for start, end in spans_to_check:
                matched_slice = content[start:end]
                if cls.is_negated_or_cautionary(content, start, end, matched_slice):
                    continue
                if cls.is_competitor_claim(content, start, end, matched_slice):
                    continue

                # Suppress if fully enclosed by a longer matched finding
                is_subspan = any(s <= start and end <= e for (s, e) in seen_spans)
                if not is_subspan:
                    seen_spans.append((start, end))
                    f_copy = f.model_copy(update={"excerpt": matched_slice})
                    object.__setattr__(f_copy, "_span", (start, end))
                    deduped.append(f_copy)

        # Sort findings by order of appearance in content (disclaimer placed at end)
        def sort_key(f: FindingCreate):
            span = getattr(f, "_span", None)
            if span and isinstance(span, tuple):
                return span[0]
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
