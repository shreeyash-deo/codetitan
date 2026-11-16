"""
Focused Test Suite for Phase 1: Context-Aware Compliance Engine
Verifies:
1. Negated prohibited claims (e.g. "We do not guarantee financial returns") are not flagged as violations.
2. Contextually valid cautionary disclaimers (e.g. "Past performance is no guarantee of future results", "not guaranteed", "not risk-free") are not flagged.
3. Competitor claims disavowed by the brand (e.g. "Our competitors guarantee returns, but we don't") are not flagged.
4. Competitor comparison where brand itself claims prohibited guarantee (e.g. "Unlike competitors, we guarantee 100% returns") IS flagged.
5. Imperative invitation traps (e.g. "Do not miss our guaranteed returns!") ARE flagged.
6. Implied guarantees and implied zero-risk claims (e.g. "Your investment will double without any risk") ARE flagged.
7. Genuine prohibited guarantees (e.g. "We guarantee instant settlements and 100% risk-free transactions") ARE flagged.
8. Accurate rule grounding (accepts valid rules, rejects hallucinated rules).
9. Exact excerpt validation (accepts verbatim excerpts, rejects ungrounded paraphrases).
10. Natural in-context correction suggestions.
11. Deterministic and AI duplicate finding deduplication (no duplicate cards, no double-counting).
12. Graceful fallback when Gemini/AI provider is unavailable (deterministic findings preserved, no crash).
13. Scoring invariance (authoritative scoring formula: critical -25, major -12, minor -5, suggestion 0; clamped 0-100).
"""

import json
from unittest.mock import patch
import pytest
from sqlalchemy.orm import Session

from app.models.rule import BrandRule
from app.models.workspace import Workspace
from app.schemas.finding import FindingCreate
from app.services.compliance.deterministic_checker import deterministic_checker
from app.services.compliance.ai_checker import ai_checker
from app.services.compliance.compliance_engine import compliance_engine
from app.services.compliance.scoring_service import scoring_service
from app.services.ai.gemini_client import GeminiTimeoutError, GeminiRateLimitError


@pytest.fixture
def compliance_test_rules():
    """Create approved brand rules representing standard financial/brand guidelines."""
    r1 = BrandRule(
        id=1,
        workspace_id=1,
        category="Content restrictions",
        title="Prohibit Guaranteed Financial Returns",
        description='Marketing content must never guarantee financial returns. Prohibited expressions include: "100% guaranteed", "guarantee returns", "guaranteed to double".',
        confidence=1.0,
        approval_status="approved",
    )
    r2 = BrandRule(
        id=2,
        workspace_id=1,
        category="Content restrictions",
        title="Prohibit Absolute Risk-Free Claims",
        description='Financial products must never be described as 100% risk-free. Prohibited expressions include: "100% risk-free", "zero investment risk", "no chance of losing money", "without any risk".',
        confidence=1.0,
        approval_status="approved",
    )
    r3 = BrandRule(
        id=3,
        workspace_id=1,
        category="Content restrictions",
        title="Prohibit Unrealistic Wealth Promises",
        description='Unrealistic rapid wealth and overnight revenue promises are prohibited. Prohibited: "revenue overnight", "make you rich overnight", "unlimited revenue growth".',
        confidence=1.0,
        approval_status="approved",
    )
    r4 = BrandRule(
        id=4,
        workspace_id=1,
        category="Brand voice and tone",
        title="Prohibited Sales Messaging and Slang",
        description='Excessively aggressive competitive language violates brand voice. Prohibited: "destroys every competitor", "crush the competition".',
        confidence=1.0,
        approval_status="approved",
    )
    return [r1, r2, r3, r4]


# ---------------------------------------------------------------------------
# 1. Negated Prohibited Claims
# ---------------------------------------------------------------------------
def test_negated_prohibited_guarantee_not_flagged(compliance_test_rules):
    """
    Example A: 'We do not guarantee financial returns.'
    Expected: Not flagged as a company guarantee because it is clearly a negation/disclaimer.
    """
    content = "We do not guarantee financial returns. All capital allocations carry market risks."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)

    guarantee_findings = [f for f in findings if "guarantee" in f.excerpt.lower()]
    assert len(guarantee_findings) == 0, f"Expected 0 guarantee findings for negated claim, got: {guarantee_findings}"


def test_negated_disclaimer_variations_not_flagged(compliance_test_rules):
    """
    Verify variations of direct negation and disclaimers are recognized as compliant.
    """
    samples = [
        "NovaPay does not offer guaranteed returns on any business transactions.",
        "We cannot and do not guarantee profits for any merchant.",
        "Our platform never guarantees financial returns.",
        "Past performance does not guarantee future results.",
        "Merchant revenues are not guaranteed and depend on market conditions.",
        "Services are provided without any guarantee of future profits.",
    ]
    for text in samples:
        findings = deterministic_checker.evaluate(text, "social_media", compliance_test_rules)
        guarantee_findings = [f for f in findings if "guarantee" in f.excerpt.lower()]
        assert len(guarantee_findings) == 0, f"Failed for text '{text}': {guarantee_findings}"


# ---------------------------------------------------------------------------
# 2. Contextually Valid Cautionary Disclaimers
# ---------------------------------------------------------------------------
def test_cautionary_disclaimer_not_flagged(compliance_test_rules):
    """
    Legitimate cautionary language like 'is not risk-free' or 'is no guarantee' must not be flagged.
    """
    content = (
        "Past performance is no guarantee of future results. "
        "This financial product is not risk-free and investments are subject to market volatility."
    )
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) == 0, f"Expected 0 findings for valid cautionary disclaimers, got: {findings}"


def test_not_without_risk_cautionary_not_flagged(compliance_test_rules):
    """
    'Investing is not without risk' affirms that risk exists, which is compliant cautionary messaging.
    """
    content = "Every business venture involves calculated decisions and investing is not without risk."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    risk_findings = [f for f in findings if "risk" in f.excerpt.lower()]
    assert len(risk_findings) == 0, f"Expected 0 findings for cautionary risk statement, got: {risk_findings}"


# ---------------------------------------------------------------------------
# 3. Competitor Claims vs. Company Claims
# ---------------------------------------------------------------------------
def test_competitor_claims_disavowed_by_brand_not_flagged(compliance_test_rules):
    """
    Example C: 'Our competitors guarantee returns, but we don't.'
    Expected: Competitor claims contrasted/disavowed by the brand are not flagged as brand violations.
    """
    content = "Our competitors guarantee returns, but we don't. We provide transparent and responsible financial tooling."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) == 0, f"Expected 0 findings for competitor contrast claim, got: {findings}"


def test_unlike_competitors_who_guarantee_not_flagged(compliance_test_rules):
    """
    'Unlike competitors who guarantee returns, we focus on reliable settlement infrastructure.'
    """
    content = "Unlike competitors who guarantee returns, we focus on reliable settlement infrastructure and risk management."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) == 0, f"Expected 0 findings for competitor contrast phrasing, got: {findings}"


def test_brand_making_guarantee_in_competitor_comparison_is_flagged(compliance_test_rules):
    """
    Contrast: When the brand itself promises the prohibited guarantee in a competitor comparison, it MUST be flagged.
    'Unlike our competitors who avoid risk, we guarantee 100% returns!'
    """
    content = "Unlike our competitors who avoid risk, we guarantee 100% returns to every partner."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 1
    assert any("guarantee" in f.excerpt.lower() for f in findings)


def test_competitor_does_not_but_we_do_is_flagged(compliance_test_rules):
    """
    'Our competitors don't guarantee returns, but we guarantee returns!'
    The second clause asserts a genuine brand guarantee and must be flagged.
    """
    content = "Our competitors don't guarantee returns, but we guarantee returns on every merchant transaction."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 1
    assert any("guarantee returns" in f.excerpt.lower() for f in findings)


# ---------------------------------------------------------------------------
# 4. Imperative Invitation Traps
# ---------------------------------------------------------------------------
def test_imperative_trap_is_flagged(compliance_test_rules):
    """
    'Do not miss our guaranteed returns!' contains 'Do not', but the negation applies to 'miss',
    while 'guaranteed returns' is an active company promise. It MUST be flagged.
    """
    content = "Do not miss our guaranteed returns this financial quarter!"
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 1
    assert any("guaranteed returns" in f.excerpt.lower() for f in findings)


def test_dont_hesitate_for_risk_free_is_flagged(compliance_test_rules):
    """
    'Don't hesitate to join our 100% risk-free platform.' contains 'Don't', but promotes risk-free claims.
    """
    content = "Don't hesitate to join our 100% risk-free platform today."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 1
    assert any("100% risk-free" in f.excerpt.lower() for f in findings)


# ---------------------------------------------------------------------------
# 5. Implied Guarantees and Implied Zero-Risk Claims
# ---------------------------------------------------------------------------
def test_implied_guarantee_and_zero_risk_flagged(compliance_test_rules):
    """
    Example B: 'Your investment will double without any risk.'
    Expected: Flagged for implied doubling promise and zero-risk claim.
    """
    content = "Sign up with NovaPay today. Your investment will double without any risk."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)

    excerpts = [f.excerpt.lower() for f in findings]
    assert any("will double" in e or "investment will double" in e for e in excerpts), f"Missing implied double: {excerpts}"
    assert any("without any risk" in e for e in excerpts), f"Missing zero risk: {excerpts}"


def test_implied_doubling_revenue_flagged(compliance_test_rules):
    """
    'Our system will double your revenue overnight.'
    """
    content = "Our system will double your revenue overnight with zero transaction friction."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    excerpts = [f.excerpt.lower() for f in findings]
    assert any("double your revenue" in e or "revenue overnight" in e for e in excerpts)


# ---------------------------------------------------------------------------
# 6. Genuine Prohibited Guarantees
# ---------------------------------------------------------------------------
def test_genuine_prohibited_claims_flagged(compliance_test_rules):
    """
    Direct company promises must be unambiguously flagged with authoritative deductions.
    """
    content = "NovaPay guarantees instant settlements and offers a 100% risk-free payment guarantee."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 2
    excerpts = [f.excerpt.lower() for f in findings]
    assert any("guarantees instant settlements" in e for e in excerpts)
    assert any("100% risk-free" in e for e in excerpts)


# ---------------------------------------------------------------------------
# 7. AI Rule Grounding and Hallucination Rejection
# ---------------------------------------------------------------------------
def test_ai_rule_grounding_accepts_valid_and_rejects_hallucinated(compliance_test_rules):
    """
    AIChecker must ground valid rule references and reject hallucinated rule IDs.
    """
    mock_payload = {
        "summary": "AI audit detected compliance issues.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "guarantees instant settlements",
                "explanation": "Guarantees of financial outcomes are prohibited.",
                "guideline_reference": "Rule #1: Prohibit Guaranteed Financial Returns",
                "suggested_correction": "enables fast settlements",
                "confidence": 0.98,
            },
            {
                "severity": "minor",
                "category": "Unknown",
                "excerpt": "guarantees instant settlements",
                "explanation": "Made up rule violation.",
                "guideline_reference": "Rule #9999: Hallucinated Nonexistent Guideline",
                "suggested_correction": "none",
                "confidence": 0.50,
            },
        ],
    }

    content = "Our platform guarantees instant settlements for all enterprise clients."
    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_payload)):
        summary, ai_findings = ai_checker.evaluate(content, "social_media", compliance_test_rules)

        assert len(ai_findings) == 1
        assert ai_findings[0].guideline_reference == "Rule #1: Prohibit Guaranteed Financial Returns"


# ---------------------------------------------------------------------------
# 8. AI Exact Excerpt Validation
# ---------------------------------------------------------------------------
def test_ai_exact_excerpt_validation(compliance_test_rules):
    """
    AI findings with paraphrased or ungrounded excerpts not present in the content must be discarded.
    """
    content = "NovaPay provides modern payment processing without any risk."
    mock_payload = {
        "summary": "Semantic analysis completed.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "without any risk",
                "explanation": "Zero risk claims are non-compliant.",
                "guideline_reference": "Rule #2: Prohibit Absolute Risk-Free Claims",
                "suggested_correction": "with comprehensive risk mitigation",
                "confidence": 0.95,
            },
            {
                "severity": "major",
                "category": "Content restrictions",
                "excerpt": "completely riskless investment opportunity",  # Paraphrase NOT in content
                "explanation": "Paraphrased text hallucinated by AI.",
                "guideline_reference": "Rule #2: Prohibit Absolute Risk-Free Claims",
                "suggested_correction": "safe investment",
                "confidence": 0.80,
            },
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_payload)):
        summary, ai_findings = ai_checker.evaluate(content, "social_media", compliance_test_rules)

        assert len(ai_findings) == 1
        assert ai_findings[0].excerpt == "without any risk"


# ---------------------------------------------------------------------------
# 9. Natural In-Context Correction Suggestions
# ---------------------------------------------------------------------------
def test_natural_correction_suggestions_fit_grammatically(compliance_test_rules):
    """
    Suggested corrections must provide practical, natural replacements.
    """
    content = "Our gateway guarantees instant settlements."
    findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    assert len(findings) >= 1
    finding = next(f for f in findings if "guarantees instant settlements" in f.excerpt)
    assert finding.suggested_correction == "enables fast settlements"

    # Applying the replacement creates a natural, grammatical sentence
    corrected = content.replace(finding.excerpt, finding.suggested_correction)
    assert corrected == "Our gateway enables fast settlements."


# ---------------------------------------------------------------------------
# 10. Deduplication Between Deterministic and AI Findings
# ---------------------------------------------------------------------------
def test_duplicate_deterministic_and_ai_finding_deduplication(compliance_test_rules):
    """
    When both deterministic and AI checkers detect the same violation, only one card is produced,
    and points are deducted only once.
    """
    content = "Our 100% risk-free payment solution protects your transactions."
    mock_payload = {
        "summary": "Detected risk claim.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "100% risk-free",
                "explanation": "AI semantic check also detected 100% risk-free claim.",
                "guideline_reference": "Rule #2: Prohibit Absolute Risk-Free Claims",
                "suggested_correction": "enterprise-grade secure",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_payload)):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)

        excerpts = [f.excerpt.strip().lower() for f in audit_result.findings]
        assert excerpts.count("100% risk-free") == 1
        # Exactly one critical violation (-25): score should be 75, not 50
        assert audit_result.compliance_score == 75
        assert audit_result.status == "needs_changes"


# ---------------------------------------------------------------------------
# 11. Graceful Fallback When Gemini Is Unavailable
# ---------------------------------------------------------------------------
def test_gemini_unavailable_preserves_deterministic_findings(compliance_test_rules):
    """
    If Gemini times out or is rate limited, deterministic findings are preserved,
    the summary clearly indicates AI was unavailable, and no exception crashes the workflow.
    """
    content = "Introducing our 100% risk-free payment gateway."

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", side_effect=GeminiTimeoutError("Request timed out after 45s")):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)

        assert len(audit_result.findings) >= 1
        assert any("100% risk-free" in f.excerpt for f in audit_result.findings)
        assert audit_result.compliance_score == 75
        assert "unavailable" in audit_result.summary.lower()
        assert audit_result.audit_status == "degraded"


def test_gemini_clean_content_unavailable_gives_100_percent_degraded(compliance_test_rules):
    """
    When content is clean and Gemini is unavailable, deterministic pass produces 100% score,
    but audit_status is marked 'degraded' to prevent unverified sign-off.
    """
    content = "We offer secure and transparent payment processing with dedicated 24/7 customer support."

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", side_effect=GeminiRateLimitError("Rate limit exceeded")):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)

        assert len(audit_result.findings) == 0
        assert audit_result.compliance_score == 100
        assert audit_result.status == "compliant"
        assert "deterministic audit passed" in audit_result.summary.lower()
        assert audit_result.audit_status == "degraded"


# ---------------------------------------------------------------------------
# 12. Scoring Invariance Formula
# ---------------------------------------------------------------------------
def test_scoring_invariance_formula():
    """
    Strict scoring deductions: Critical: -25, Major: -12, Minor: -5, Suggestion: 0.
    Clamped strictly between 0 and 100.
    """
    findings = [
        FindingCreate(severity="critical", category="Cat A", excerpt="Ex 1", explanation="Expl", guideline_reference="Ref 1"),
        FindingCreate(severity="major", category="Cat B", excerpt="Ex 2", explanation="Expl", guideline_reference="Ref 2"),
        FindingCreate(severity="minor", category="Cat C", excerpt="Ex 3", explanation="Expl", guideline_reference="Ref 3"),
        FindingCreate(severity="suggestion", category="Cat D", excerpt="Ex 4", explanation="Expl", guideline_reference="Ref 4"),
    ]
    # Deductions: 100 - 25 - 12 - 5 - 0 = 58
    score, status = scoring_service.calculate_score(findings)
    assert score == 58
    assert status == "critical_issues"

    # Clamping test: many critical findings cannot reduce score below 0
    many_critical = [
        FindingCreate(severity="critical", category=f"Cat {i}", excerpt=f"Ex {i}", explanation="Expl", guideline_reference=f"Ref {i}")
        for i in range(10)
    ]
    floor_score, floor_status = scoring_service.calculate_score(many_critical)
    assert floor_score == 0
    assert floor_status == "critical_issues"


# ---------------------------------------------------------------------------
# 13. Regression: Negation False-Negative Protection ("not only", "not merely")
# ---------------------------------------------------------------------------
def test_not_only_and_not_merely_guarantees_remain_flagged(compliance_test_rules):
    """
    Phrases such as 'not only guaranteed returns' and 'not merely guaranteed profits'
    are additive/correlative emphasis, NOT negations. They must remain flagged.
    """
    samples = [
        ("We offer not only guaranteed returns, but also 24/7 dedicated support.", "guaranteed returns"),
        ("NovaPay promises not merely guaranteed profits, but continuous merchant coaching.", "guaranteed profits"),
        ("Our platform delivers not just guaranteed returns, but absolute peace of mind.", "guaranteed returns"),
        ("We provide not simply 100% risk-free investments, but long-term value.", "100% risk-free"),
    ]
    for text, expected_term in samples:
        findings = deterministic_checker.evaluate(text, "social_media", compliance_test_rules)
        excerpts = [f.excerpt.lower() for f in findings]
        assert any(expected_term in e for e in excerpts), f"Failed for '{text}': expected '{expected_term}' in {excerpts}"


# ---------------------------------------------------------------------------
# 14. Regression: Deduplication by Actual Occurrence (Repeated identical phrases)
# ---------------------------------------------------------------------------
def test_repeated_identical_phrases_at_different_positions_are_not_incorrectly_merged(compliance_test_rules):
    """
    Ensure repeated identical phrases at different positions are not incorrectly merged.
    Deterministic checker detects both, and AI finding matches the correct occurrence.
    """
    content = (
        "Paragraph 1 guarantees returns on standard accounts.\n\n"
        "Paragraph 2 discusses infrastructure and reliability.\n\n"
        "Paragraph 3 also guarantees returns on premium corporate accounts."
    )
    det_findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
    guarantee_findings = [f for f in det_findings if "guarantees returns" in f.excerpt.lower()]
    assert len(guarantee_findings) == 2, f"Expected 2 separate findings for repeated identical phrases, got {len(guarantee_findings)}"

    # Mock AI finding targeting the first occurrence only
    mock_payload = {
        "summary": "AI audit detected guarantee in paragraph 1.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "guarantees returns",
                "explanation": "Guaranteed financial return claim.",
                "guideline_reference": "Rule #1: Prohibit Guaranteed Financial Returns",
                "suggested_correction": "targets returns",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_payload)):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)
        merged_guarantees = [f for f in audit_result.findings if "guarantees returns" in f.excerpt.lower()]
        assert len(merged_guarantees) == 2, f"Repeated occurrences must not be collapsed: got {len(merged_guarantees)}"
        # First occurrence received the AI suggestion
        assert merged_guarantees[0].suggested_correction == "targets returns"
        # Second occurrence retained its deterministic suggestion
        assert merged_guarantees[1].suggested_correction == "target returns"


# ---------------------------------------------------------------------------
# 15. Regression: Correction Quality & Rejection of Invalid / Instructional AI Suggestions
# ---------------------------------------------------------------------------
def test_ai_correction_quality_rejects_instructional_and_reintroduced_violations(compliance_test_rules):
    """
    Do not select an AI correction merely because it is longer.
    Reject instructional text and re-introduced violations; retain deterministic suggestion.
    """
    content = "Our software guarantees instant settlements across all payment rails."

    # Case A: AI suggests an instructional sentence (not a drop-in replacement)
    mock_instructional = {
        "summary": "AI audit completed.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "guarantees instant settlements",
                "explanation": "Guarantees are prohibited.",
                "guideline_reference": "Rule #1: Prohibit Guaranteed Financial Returns",
                "suggested_correction": "Please revise the copy to eliminate guarantees and describe settlement speeds accurately.",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_instructional)):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)
        finding = audit_result.findings[0]
        # Instructional text rejected; deterministic replacement 'enables fast settlements' retained
        assert finding.suggested_correction == "enables fast settlements"

    # Case B: AI suggests text that still contains the violation
    mock_violation_reintroduced = {
        "summary": "AI audit completed.",
        "findings": [
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "guarantees instant settlements",
                "explanation": "Guarantees are prohibited.",
                "guideline_reference": "Rule #1: Prohibit Guaranteed Financial Returns",
                "suggested_correction": "100% guaranteed fast instant settlements",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_violation_reintroduced)):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", compliance_test_rules)
        finding = audit_result.findings[0]
        # Reintroduced violation rejected; deterministic replacement retained
        assert finding.suggested_correction == "enables fast settlements"


# ---------------------------------------------------------------------------
# 16. Regression: Social-Proof Filter Cannot Suppress Legitimate Violations
# ---------------------------------------------------------------------------
def test_social_proof_filter_does_not_suppress_legitimate_violations(compliance_test_rules):
    """
    A legitimate violation must not be suppressed merely because the text or excerpt
    contains phrases such as 'thousands of businesses' or 'reliable support'.
    """
    samples = [
        ("Join thousands of businesses enjoying guaranteed returns on all transactions.", "guaranteed returns"),
        ("Thousands of businesses rely on our zero investment risk guarantee.", "zero investment risk"),
        ("Enjoy reliable support with guaranteed profits for every online merchant.", "guaranteed profits"),
    ]

    for content, expected_term in samples:
        # 1. Deterministic check flags it
        det_findings = deterministic_checker.evaluate(content, "social_media", compliance_test_rules)
        assert any(expected_term in f.excerpt.lower() for f in det_findings), f"Deterministic missed: {expected_term}"

        # 2. AI check also evaluates it without suppression
        mock_payload = {
            "summary": "Detected financial guarantee.",
            "findings": [
                {
                    "severity": "critical",
                    "category": "Content restrictions",
                    "excerpt": expected_term,
                    "explanation": "Financial promises violate compliance.",
                    "guideline_reference": "Rule #1: Prohibit Guaranteed Financial Returns" if "guarantee" in expected_term or "profit" in expected_term else "Rule #2: Prohibit Absolute Risk-Free Claims",
                    "suggested_correction": "sustainable returns",
                    "confidence": 0.95,
                }
            ],
        }
        with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_payload)):
            summary, ai_findings = ai_checker.evaluate(content, "social_media", compliance_test_rules)
            assert len(ai_findings) >= 1, f"AI incorrectly suppressed finding for: {content}"
            assert any(expected_term in f.excerpt.lower() for f in ai_findings)


# ---------------------------------------------------------------------------
# Multi-Brand Synthetic Fixture: ApexWealth Advisory (Workspace 99)
# ---------------------------------------------------------------------------
@pytest.fixture
def apexwealth_test_rules():
    """
    Synthetic second brand fixture with distinct workspace, rule IDs, categories,
    and disclaimers to ensure BrandShield compliance engine is completely brand-agnostic.
    """
    r101 = BrandRule(
        id=101,
        workspace_id=99,
        category="Investment Restrictions",
        title="Prohibit Guaranteed Investment Returns",
        description='Advisory collateral must never guarantee investment outcomes. Prohibited expressions: "guaranteed returns", "guaranteed profits", "guaranteed to double".',
        confidence=1.0,
        approval_status="approved",
        source_reference="APEX-RULE-101",
    )
    r102 = BrandRule(
        id=102,
        workspace_id=99,
        category="Risk Management",
        title="Prohibit Market Immunity and Zero Risk Claims",
        description='Financial advisory must never claim immunity to market conditions. Prohibited expressions: "regardless of market conditions", "without worrying about market uncertainty", "100% risk-free", "immune to market volatility".',
        confidence=1.0,
        approval_status="approved",
        source_reference="APEX-RULE-102",
    )
    r103 = BrandRule(
        id=103,
        workspace_id=99,
        category="Marketing Integrity",
        title="Prohibit Passive and Effortless Wealth Claims",
        description='Marketing collateral must never depict wealth generation as effortless or automated. Prohibited: "build wealth effortlessly", "money works while you sleep", "passive income on autopilot", "watch your financial future grow on autopilot".',
        confidence=1.0,
        approval_status="approved",
        source_reference="APEX-RULE-103",
    )
    r104 = BrandRule(
        id=104,
        workspace_id=99,
        category="Claims & Disclaimers",
        title="Mandatory Capital Risk Disclosure",
        description='All wealth and financial advisory marketing must conclude with the mandatory capital risk disclosure: "Investment advisory services involve substantial risk of loss. Capital invested is not insured or guaranteed."',
        confidence=1.0,
        approval_status="approved",
        source_reference="APEX-DISC-104",
    )
    return [r101, r102, r103, r104]


# ---------------------------------------------------------------------------
# 17. Effortless Wealth Creation Detection (Multi-Brand)
# ---------------------------------------------------------------------------
def test_effortless_wealth_creation_flagged(apexwealth_test_rules):
    """
    Detects 'build wealth effortlessly' as a violation of responsible wealth promises.
    """
    content = "ApexWealth Advisory helps individuals build wealth effortlessly with our systematic strategies."
    findings = deterministic_checker.evaluate(content, "social_media", apexwealth_test_rules)
    assert len(findings) >= 1
    assert any("build wealth effortlessly" in f.excerpt.lower() for f in findings)
    finding = next(f for f in findings if "build wealth effortlessly" in f.excerpt.lower())
    assert finding.guideline_reference == "Rule #103: Prohibit Passive and Effortless Wealth Claims"
    assert finding.suggested_correction == "build wealth sustainably"


# ---------------------------------------------------------------------------
# 18. Passive Income / 'Money Works While You Sleep' Detection
# ---------------------------------------------------------------------------
def test_passive_income_money_works_while_you_sleep_flagged(apexwealth_test_rules):
    """
    Detects implied passive income promises ('money works while you sleep').
    """
    content = "Experience true financial freedom where your money works while you sleep with ApexWealth."
    findings = deterministic_checker.evaluate(content, "social_media", apexwealth_test_rules)
    assert len(findings) >= 1
    assert any("money works while you sleep" in f.excerpt.lower() for f in findings)
    finding = next(f for f in findings if "money works while you sleep" in f.excerpt.lower())
    assert finding.guideline_reference == "Rule #103: Prohibit Passive and Effortless Wealth Claims"


# ---------------------------------------------------------------------------
# 19. Market Immunity Claims Detection
# ---------------------------------------------------------------------------
def test_market_immunity_claims_flagged(apexwealth_test_rules):
    """
    Detects claims of market immunity ('without worrying about market uncertainty', 'regardless of market conditions').
    """
    content1 = "Grow your portfolio without worrying about market uncertainty with our advisory team."
    findings1 = deterministic_checker.evaluate(content1, "social_media", apexwealth_test_rules)
    assert len(findings1) >= 1
    assert any("without worrying about market uncertainty" in f.excerpt.lower() for f in findings1)

    content2 = "ApexWealth delivers steady returns regardless of market conditions."
    findings2 = deterministic_checker.evaluate(content2, "social_media", apexwealth_test_rules)
    assert len(findings2) >= 1
    assert any("regardless of market conditions" in f.excerpt.lower() for f in findings2)


# ---------------------------------------------------------------------------
# 20. Section 5.3 Principle: Disclaimers Do Not Neutralize Promotional Violations
# ---------------------------------------------------------------------------
def test_disclaimer_does_not_neutralize_promotional_violation(apexwealth_test_rules):
    """
    Section 5.3 Principle:
    A disclaimer at the end of the text does NOT excuse or neutralize promotional claims
    in the body copy (e.g. 'build wealth effortlessly').
    Both the promotional claim must be flagged, while the disclaimer itself is recognized as present.
    """
    disclaimer = "Investment advisory services involve substantial risk of loss. Capital invested is not insured or guaranteed."
    content = (
        "Build wealth effortlessly with ApexWealth Advisory.\n\n"
        f"Disclaimer: {disclaimer}"
    )

    findings = deterministic_checker.evaluate(content, "social_media", apexwealth_test_rules)
    # The promotional violation must be flagged
    assert any("build wealth effortlessly" in f.excerpt.lower() for f in findings)
    # The missing disclaimer finding must NOT be triggered because the disclaimer is present
    assert not any(f.excerpt == "[Missing Regulatory Disclaimer]" for f in findings)


# ---------------------------------------------------------------------------
# 21. Compliant Content with Mandatory Disclaimer Scores 100
# ---------------------------------------------------------------------------
def test_compliant_content_with_disclaimer_scores_100(apexwealth_test_rules):
    """
    When content makes no prohibited claims and includes the mandatory disclaimer,
    it receives a perfect 100 compliance score.
    """
    disclaimer = "Investment advisory services involve substantial risk of loss. Capital invested is not insured or guaranteed."
    content = (
        "ApexWealth Advisory provides disciplined, long-term portfolio allocation tailored to your goals.\n\n"
        f"Disclaimer: {disclaimer}"
    )

    mock_ai = {
        "summary": "Content complies with all guidelines.",
        "findings": [],
    }
    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_ai)):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", apexwealth_test_rules)
        assert len(audit_result.findings) == 0
        assert audit_result.compliance_score == 100
        assert audit_result.status == "compliant"
        assert audit_result.audit_status == "verified"


# ---------------------------------------------------------------------------
# 22. Missing Disclaimer Flagged When Financial Copy Omits It
# ---------------------------------------------------------------------------
def test_missing_disclaimer_flagged_when_financial_copy_omits_it(apexwealth_test_rules):
    """
    When financial content omits the required disclosure, a critical missing disclaimer finding is produced.
    """
    content = "ApexWealth Advisory provides disciplined portfolio allocation for your investment capital."
    findings = deterministic_checker.evaluate(content, "social_media", apexwealth_test_rules)
    assert any(f.excerpt == "[Missing Regulatory Disclaimer]" for f in findings)
    disc_finding = next(f for f in findings if f.excerpt == "[Missing Regulatory Disclaimer]")
    assert disc_finding.guideline_reference == "Rule #104: Mandatory Capital Risk Disclosure"
    assert "Investment advisory services involve substantial risk" in disc_finding.suggested_correction


# ---------------------------------------------------------------------------
# 23. Audit Integrity: Degraded Audit Status When AI Provider Is Unavailable
# ---------------------------------------------------------------------------
def test_gemini_timeout_sets_degraded_audit_status(apexwealth_test_rules):
    """
    When Gemini times out or is unavailable, the audit completes in degraded mode,
    setting audit_status to 'degraded' instead of 'verified'.
    """
    content = "ApexWealth Advisory provides disciplined portfolio management."
    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", side_effect=GeminiTimeoutError("AI service unavailable")):
        audit_result = compliance_engine.run_compliance_audit(content, "social_media", apexwealth_test_rules)
        assert audit_result.audit_status == "degraded"
        assert "unavailable" in audit_result.summary.lower()


# ---------------------------------------------------------------------------
# 24. Audit Integrity: Degraded Audit Status Blocks Approval Sign-off
# ---------------------------------------------------------------------------
def test_degraded_audit_status_blocks_approval_request():
    """
    Downstream governance check: content with 'degraded' audit status cannot be submitted
    for approval sign-off.
    """
    from unittest.mock import MagicMock
    from app.services.approval_service import approval_service

    mock_db = MagicMock()
    mock_review = MagicMock()
    mock_review.id = 77
    mock_review.status = "compliant"
    mock_review.audit_status = "degraded"
    mock_review.content = "Some copy"
    mock_db.query().filter().first.return_value = mock_review
    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(ValueError, match="audit status is 'degraded'"):
        approval_service.request_review_approval(mock_db, review_id=77, user=mock_user, comment="Requesting sign-off")


# ---------------------------------------------------------------------------
# 25. Multi-Brand Competitor Claim Invariance
# ---------------------------------------------------------------------------
def test_multibrand_competitor_claim_invariance(apexwealth_test_rules):
    """
    Verifies competitor claim filtering works generically without brand-specific hardcoding.
    """
    content = "Unlike competitors who guarantee returns, ApexWealth focuses on transparent risk management."
    findings = deterministic_checker.evaluate(content, "social_media", apexwealth_test_rules)
    guarantee_findings = [f for f in findings if "guarantee" in f.excerpt.lower()]
    assert len(guarantee_findings) == 0, f"Competitor claim should not be flagged: {guarantee_findings}"


