import pytest
from unittest.mock import patch, MagicMock

from app.models.rule import BrandRule
from app.schemas.finding import FindingCreate
from app.services.compliance.deterministic_checker import deterministic_checker, DeterministicChecker
from app.services.compliance.compliance_engine import compliance_engine
from app.services.compliance.scoring_service import scoring_service
from app.services.ai.gemini_client import GeminiClient, GeminiModelError


@pytest.fixture
def brand_rules():
    rule_02 = BrandRule(
        id=2,
        workspace_id=1,
        category="Tone & Voice",
        title="Professional Terminology",
        description="Avoid informal slang like 'crazy secret' or 'miracle cure'.",
        approval_status="approved",
    )
    cr_01 = BrandRule(
        id=1,
        workspace_id=1,
        category="Claims & Restrictions",
        title="Absolute Guarantee Prohibited",
        description="Content must not promise absolute or 100% guaranteed results without qualification.",
        approval_status="approved",
    )
    return [rule_02, cr_01]


@pytest.fixture
def production_violation_copy():
    return """🚨 THIS SERUM IS A MIRACLE CURE! 🚨

NovaGlow Vitamin C Serum is our CRAZY SECRET to perfect skin!

We guarantee 100% flawless skin for EVERY customer. Dark spots will disappear FOREVER, no exceptions!

This revolutionary serum guarantees unbelievable results. Try it today and experience the magic!

BUY NOW! ❤️"""


def test_deterministic_detects_all_five_production_violations(brand_rules, production_violation_copy):
    """
    Deterministic engine must detect all 5 violations even with AI disabled.
    1. 'MIRACLE CURE' under RULE-02
    2. 'CRAZY SECRET' under RULE-02
    3. 'guarantee 100% flawless skin' under CR-01
    4. 'Dark spots will disappear FOREVER, no exceptions' under CR-01
    5. 'guarantees unbelievable results' under CR-01
    """
    findings = deterministic_checker.evaluate(
        content=production_violation_copy,
        content_type="Social",
        approved_rules=brand_rules,
    )

    assert len(findings) == 5, f"Expected exactly 5 findings, got {len(findings)}: {[f.excerpt for f in findings]}"

    excerpts = [f.excerpt for f in findings]
    assert "MIRACLE CURE" in excerpts
    assert "CRAZY SECRET" in excerpts
    assert "guarantee 100% flawless skin" in excerpts
    assert "Dark spots will disappear FOREVER, no exceptions" in excerpts
    assert "guarantees unbelievable results" in excerpts

    # Check guideline references
    f_map = {f.excerpt: f for f in findings}
    assert "Rule #2: Professional Terminology" in f_map["MIRACLE CURE"].guideline_reference
    assert "Rule #2: Professional Terminology" in f_map["CRAZY SECRET"].guideline_reference
    assert "Rule #1: Absolute Guarantee Prohibited" in f_map["guarantee 100% flawless skin"].guideline_reference
    assert "Rule #1: Absolute Guarantee Prohibited" in f_map["Dark spots will disappear FOREVER, no exceptions"].guideline_reference
    assert "Rule #1: Absolute Guarantee Prohibited" in f_map["guarantees unbelievable results"].guideline_reference


def test_deterministic_scoring_penalizes_violations(brand_rules, production_violation_copy):
    """
    Non-compliant content must never receive 100/100 or compliant status.
    """
    findings = deterministic_checker.evaluate(
        content=production_violation_copy,
        content_type="Social",
        approved_rules=brand_rules,
    )
    score, status_label = scoring_service.calculate_score(findings)

    # 3 criticals (-75) + 2 majors (-24) = score 1/100
    assert score < 20, f"Expected low score for severe violations, got {score}"
    assert status_label == "critical_issues"


def test_deterministic_case_and_punctuation_insensitivity(brand_rules):
    """
    Violations with lowercase or trailing punctuation must still be flagged.
    """
    content = "Our serum is a miracle cure! It is a crazy secret. We guarantee 100% flawless skin."
    findings = deterministic_checker.evaluate(
        content=content,
        content_type="Social",
        approved_rules=brand_rules,
    )
    excerpts = [f.excerpt.lower() for f in findings]
    assert "miracle cure" in excerpts
    assert "crazy secret" in excerpts
    assert "guarantee 100% flawless skin" in excerpts


def test_compliant_qualified_content_no_false_positives(brand_rules):
    """
    Grounded check: disclaimed or qualified claims must not be flagged as violations.
    """
    compliant_copy = """NovaGlow Vitamin C Serum is formulated to support radiant, healthy-looking skin.

Consistent daily use may help reduce the appearance of dark spots over time.

Individual results vary. Results are not guaranteed. We do not guarantee 100% flawless skin.

Always consult your dermatologist before introducing new active serums."""

    findings = deterministic_checker.evaluate(
        content=compliant_copy,
        content_type="Social",
        approved_rules=brand_rules,
    )

    assert len(findings) == 0, f"Compliant copy should have 0 findings, but got: {[f.excerpt for f in findings]}"
    score, status_label = scoring_service.calculate_score(findings)
    assert score == 100
    assert status_label == "compliant"


def test_subject_quantifier_negation_not_flagged(brand_rules):
    """
    Statements like 'No procedure guarantees unbelievable results' must be recognized as negated.
    """
    negated_content = "No skincare procedure guarantees unbelievable results or flawless skin."
    findings = deterministic_checker.evaluate(
        content=negated_content,
        content_type="Social",
        approved_rules=brand_rules,
    )
    assert len(findings) == 0


def test_degraded_audit_status_when_ai_fails(brand_rules, production_violation_copy):
    """
    When AI provider fails or is unconfigured:
    - audit_status must be 'degraded'
    - deterministic findings must be preserved
    - score must be calculated from deterministic findings
    """
    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", side_effect=Exception("Model not found")):
        result = compliance_engine.run_compliance_audit(
            content=production_violation_copy,
            content_type="Social",
            approved_rules=brand_rules,
        )

        assert result.audit_status == "degraded"
        assert result.compliance_score < 20
        assert result.status == "critical_issues"
        assert len(result.findings) == 5
        assert "unavailable" in result.summary.lower()
        assert result.compliance_score < 20
        assert result.status == "critical_issues"
        assert len(result.findings) == 5
        assert "unavailable" in result.summary.lower()


def test_gemini_client_fallback_from_retired_model():
    """
    When GeminiClient is initialized with retired 'gemini-2.0-flash', it should
    catch the 404 model error and automatically fall back to 'gemini-3.8-flash'.
    """
    client = GeminiClient(model="gemini-2.0-flash")

    def mock_call(model_name, payload, headers):
        if model_name == "gemini-2.0-flash":
            raise GeminiModelError("Configured model 'gemini-2.0-flash' not found (HTTP 404)")
        return '{"summary": "Fallback audit", "findings": []}'

    with patch.object(client, "_call_model_api", side_effect=mock_call):
        res = client.generate_content("test prompt")
        assert res == '{"summary": "Fallback audit", "findings": []}'
        assert client.model == "gemini-3.8-flash"


def test_hybrid_audit_merges_without_duplicate_findings(brand_rules, production_violation_copy):
    """
    When AI semantic analysis runs alongside deterministic checks:
    - Overlapping findings for the same violation must be deduplicated
    - Natural drop-in replacement suggestions from AI should upgrade deterministic replacements
    - Total count remains 5 (not 10)
    """
    mock_ai_findings = [
        FindingCreate(
            severity="major",
            category="Tone & Voice",
            excerpt="THIS SERUM IS A MIRACLE CURE!",
            explanation="Unapproved slang phrase",
            guideline_reference="Rule #2: Professional Terminology",
            suggested_correction="DISCOVER OUR TARGETED SKINCARE SOLUTION!",
            confidence=0.95,
        ),
        FindingCreate(
            severity="major",
            category="Tone & Voice",
            excerpt="CRAZY SECRET",
            explanation="Unapproved slang phrase",
            guideline_reference="Rule #2: Professional Terminology",
            suggested_correction="advanced formula",
            confidence=0.95,
        ),
        FindingCreate(
            severity="critical",
            category="Claims & Restrictions",
            excerpt="We guarantee 100% flawless skin for EVERY customer.",
            explanation="Absolute efficacy guarantee",
            guideline_reference="Rule #1: Absolute Guarantee Prohibited",
            suggested_correction="Designed to help reveal noticeably healthier, glowing skin.",
            confidence=0.95,
        ),
        FindingCreate(
            severity="critical",
            category="Claims & Restrictions",
            excerpt="Dark spots will disappear FOREVER, no exceptions!",
            explanation="Absolute permanence promise",
            guideline_reference="Rule #1: Absolute Guarantee Prohibited",
            suggested_correction="Formulated to help noticeably fade the appearance of dark spots over time.",
            confidence=0.95,
        ),
        FindingCreate(
            severity="critical",
            category="Claims & Restrictions",
            excerpt="guarantees unbelievable results",
            explanation="Unqualified results guarantee",
            guideline_reference="Rule #1: Absolute Guarantee Prohibited",
            suggested_correction="delivers visible results",
            confidence=0.95,
        ),
    ]

    with patch("app.services.compliance.ai_checker.ai_checker.evaluate", return_value=("Semantic audit completed.", mock_ai_findings)):
        result = compliance_engine.run_compliance_audit(
            content=production_violation_copy,
            content_type="Social",
            approved_rules=brand_rules,
        )

        assert result.audit_status == "verified"
        assert len(result.findings) == 5, f"Expected 5 deduplicated findings, got {len(result.findings)}"
        assert result.compliance_score < 20
        assert result.status == "critical_issues"
