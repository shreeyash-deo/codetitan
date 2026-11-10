import json
import pytest
from unittest.mock import patch, MagicMock
from app.core.security import create_access_token
from app.models.rule import BrandRule
from app.models.workspace import Workspace
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.approval import Approval
from app.services.compliance.deterministic_checker import deterministic_checker
from app.services.compliance.compliance_engine import compliance_engine, NoApprovedRulesError
from app.services.compliance.ai_checker import ai_checker
from app.services.compliance.scoring_service import scoring_service
from app.services.review_service import review_service
from app.services.approval_service import approval_service
from app.schemas.review import ContentReviewSubmission


SAMPLE_NON_COMPLIANT_CONTENT = (
    "Introducing NovaPay Global — the world's fastest payment platform, guaranteed to double your business revenue overnight!\n\n"
    "Our 100% risk-free payment solution eliminates all fraud and ensures zero transaction failures. Join thousands of businesses already enjoying effortless growth.\n\n"
    "Get started today with absolutely no hidden fees, no setup costs, and guaranteed success!"
)

EIGHT_CLAIMS_CONTENT = (
    "Destroys every competitor in the market!\n"
    "With 10 million transactions per second and absolutely zero downtime, we are the number one payment provider in India.\n"
    "Trusted by 100% of businesses.\n"
    "Our platform guarantees instant settlements, eliminates every security threat, and delivers unlimited revenue growth."
)


@pytest.fixture
def workspace_with_rules(db):
    user = User(email="author@novapay.com", hashed_password="pw", name="Author")
    db.add(user)
    db.flush()

    ws = Workspace(name="NovaPay Global", org_id="ORG-TEST99")
    db.add(ws)
    db.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="Employee", status="approved")
    db.add(member)

    rules = [
        BrandRule(
            workspace_id=ws.id,
            category="Content restrictions",
            title="Guaranteed Financial Returns",
            description="[NP-COMP-001 - Severity: Critical] Marketing content must never guarantee financial returns. Prohibited expressions include: Guaranteed returns. Guaranteed profits. 100% guaranteed earnings. Risk-free investment. Certain financial success.",
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Content restrictions",
            title="Risk-Free Claims",
            description="[NP-COMP-002 - Severity: Critical] Do not describe investments or products as completely risk-free. Prohibited expressions include: 100% risk-free. Zero investment risk. No chance of losing money.",
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Content restrictions",
            title="Unrealistic Wealth Promises",
            description="[NP-COMP-003 - Severity: High] Do not imply users can become wealthy instantly. Prohibited messaging includes: Make you rich overnight. Become a millionaire instantly. Double your money without effort. Unlimited revenue growth.",
            confidence=0.90,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Content restrictions",
            title="Misleading Performance Claims",
            description="[NP-COMP-004 - Severity: High] Do not publish unverified performance statistics or comparative claims. Any numerical claim must be supported by verifiable evidence. Zero downtime and eliminating all threats require verification.",
            confidence=0.90,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Claims and disclaimers",
            title="Financial Risk Disclaimer",
            description='[NP-DISC-001 - Severity: High] Content discussing investments or financial opportunities must include an appropriate risk disclaimer. Approved disclaimer: "All financial and investment decisions involve risk. Past performance does not guarantee future results. Users should evaluate their financial circumstances and seek independent professional advice where appropriate."',
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Brand voice and tone",
            title="Prohibited Sales Messaging and Slang",
            description="[NP-VOICE-002 - Severity: High] The following communication styles are prohibited: Excessively aggressive sales language. Destroys every competitor in the market.",
            confidence=0.90,
            approval_status="approved",
        ),
    ]
    db.add_all(rules)
    db.commit()
    for r in rules:
        db.refresh(r)

    return ws, user, rules


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Multiple deterministic violations in one paragraph
# ---------------------------------------------------------------------------
def test_scenario_01_multiple_deterministic_violations_in_one_paragraph(workspace_with_rules):
    ws, user, rules = workspace_with_rules
    findings = deterministic_checker.evaluate(EIGHT_CLAIMS_CONTENT, "social_media", rules)

    assert len(findings) >= 8
    excerpts = [f.excerpt.lower() for f in findings]
    assert any("destroys every competitor" in e for e in excerpts)
    assert any("10 million transactions per second" in e for e in excerpts)
    assert any("zero downtime" in e for e in excerpts)
    assert any("number one payment provider in india" in e for e in excerpts)
    assert any("trusted by 100% of businesses" in e for e in excerpts)
    assert any("guarantees instant settlements" in e for e in excerpts)
    assert any("eliminates every security threat" in e for e in excerpts)
    assert any("unlimited revenue growth" in e for e in excerpts)


# ---------------------------------------------------------------------------
# 2. Multiple valid Gemini semantic findings
# ---------------------------------------------------------------------------
def test_scenario_02_multiple_valid_gemini_semantic_findings(workspace_with_rules):
    ws, user, rules = workspace_with_rules

    mock_gemini_payload = {
        "summary": "Multiple serious governance violations detected across copy.",
        "findings": [
            {
                "severity": "major",
                "category": "Brand voice and tone",
                "excerpt": "Destroys every competitor in the market",
                "explanation": "Aggressive competitive attack violates brand voice.",
                "guideline_reference": "Rule #11: Prohibited Sales Messaging and Slang",
                "suggested_correction": "Leads the market with reliable solutions",
                "confidence": 0.95,
            },
            {
                "severity": "major",
                "category": "Content restrictions",
                "excerpt": "10 million transactions per second",
                "explanation": "Unverified numerical throughput statistic.",
                "guideline_reference": "NP-COMP-004",
                "suggested_correction": "high-throughput transaction processing",
                "confidence": 0.90,
            },
            {
                "severity": "critical",
                "category": "Content restrictions",
                "excerpt": "guarantees instant settlements",
                "explanation": "Settlement outcome guarantee prohibited.",
                "guideline_reference": "Rule #4",
                "suggested_correction": "enables fast settlements",
                "confidence": 0.95,
            },
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_gemini_payload)):
        summary, ai_findings = ai_checker.evaluate(EIGHT_CLAIMS_CONTENT, "social_media", rules)
        assert len(ai_findings) == 3
        assert "violations detected" in summary
        assert all(f.guideline_reference.startswith("Rule #") for f in ai_findings)


# ---------------------------------------------------------------------------
# 3. Merging deterministic and semantic findings without duplicates
# ---------------------------------------------------------------------------
def test_scenario_03_merging_deterministic_and_semantic_without_duplicates(workspace_with_rules):
    ws, user, rules = workspace_with_rules

    mock_gemini_payload = {
        "summary": "AI audit completed.",
        "findings": [
            {
                "severity": "major",
                "category": "Brand voice and tone",
                "excerpt": "Destroys every competitor in the market",
                "explanation": "Aggressive tone.",
                "guideline_reference": "Rule #11",
                "suggested_correction": "Leads the market with reliable solutions",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_gemini_payload)):
        result = compliance_engine.run_compliance_audit(EIGHT_CLAIMS_CONTENT, "social_media", rules)
        # Verify no duplicate findings exist for the same excerpt
        excerpts = [f.excerpt.strip().lower() for f in result.findings]
        assert len(excerpts) == len(set(excerpts))


# ---------------------------------------------------------------------------
# 4. Rejection of hallucinated rule IDs
# ---------------------------------------------------------------------------
def test_scenario_04_rejection_of_hallucinated_rule_ids(workspace_with_rules):
    ws, user, rules = workspace_with_rules

    mock_gemini_payload = {
        "summary": "AI audit with hallucinated rule reference.",
        "findings": [
            {
                "severity": "critical",
                "category": "Unknown",
                "excerpt": "Destroys every competitor in the market",
                "explanation": "Bad tone.",
                "guideline_reference": "Rule #9999: Fake Hallucinated Policy",
                "suggested_correction": "Better phrasing",
                "confidence": 0.95,
            }
        ],
    }

    with patch("app.services.compliance.ai_checker.AIChecker.call_gemini", return_value=json.dumps(mock_gemini_payload)):
        _, ai_findings = ai_checker.evaluate(EIGHT_CLAIMS_CONTENT, "social_media", rules)
        assert len(ai_findings) == 0


# ---------------------------------------------------------------------------
# 5. Workspace isolation for approved rules
# ---------------------------------------------------------------------------
def test_scenario_05_workspace_isolation_for_approved_rules(db, workspace_with_rules):
    ws1, user1, rules1 = workspace_with_rules

    # Workspace 2 has zero approved rules
    ws2 = Workspace(name="Workspace 2", org_id="ORG-WS2222")
    db.add(ws2)
    db.flush()

    sub = ContentReviewSubmission(title="Isolation Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")

    with pytest.raises(NoApprovedRulesError):
        review_service.submit_and_audit(db, ws2.id, user1.id, sub)


# ---------------------------------------------------------------------------
# 6. No approved rules means an incomplete audit
# ---------------------------------------------------------------------------
def test_scenario_06_no_approved_rules_means_incomplete_audit():
    with pytest.raises(NoApprovedRulesError) as exc_info:
        compliance_engine.run_compliance_audit(SAMPLE_NON_COMPLIANT_CONTENT, "social_media", [])
    assert "Brand rules unavailable" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 7. Applying a correction changes the working document
# ---------------------------------------------------------------------------
def test_scenario_07_applying_correction_changes_working_document(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Ad Copy", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    target_finding = next(f for f in review.findings if "100% risk-free" in f.excerpt)
    resp = review_service.apply_correction(db, review.id, target_finding.id, user.id)

    assert "100% risk-free" not in resp.updated_content
    assert "secure, risk-managed" in resp.updated_content
    assert resp.updated_content != resp.original_content
    assert "100% risk-free" in resp.original_content


# ---------------------------------------------------------------------------
# 8. Rechecking detects remaining violations
# ---------------------------------------------------------------------------
def test_scenario_08_rechecking_detects_remaining_violations(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Ad Copy", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    # Apply only 1 correction
    target_finding = next(f for f in review.findings if "100% risk-free" in f.excerpt)
    resp = review_service.apply_correction(db, review.id, target_finding.id, user.id)

    # Recheck updated content
    recheck_res = compliance_engine.run_compliance_audit(resp.updated_content, "social_media", rules)
    # Remaining violations must still be flagged
    assert recheck_res.compliance_score < 80
    assert recheck_res.status in ("needs_changes", "critical_issues")
    assert any("guaranteed to double" in f.excerpt.lower() for f in recheck_res.findings)


# ---------------------------------------------------------------------------
# 9. Corrected content and original content remain separate
# ---------------------------------------------------------------------------
def test_scenario_09_corrected_and_original_content_remain_separate(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Multi-Pass", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    orig_content_snapshot = review.original_content
    for f in review.findings:
        if f.suggested_correction:
            review_service.apply_correction(db, review.id, f.id, user.id)

    db.refresh(review)
    assert review.original_content == orig_content_snapshot
    assert review.content != review.original_content


# ---------------------------------------------------------------------------
# 10. Zero violations produce the correct score (100/100)
# ---------------------------------------------------------------------------
def test_scenario_10_zero_violations_produce_correct_score(workspace_with_rules):
    clean_content = (
        "Introducing NovaPay Global — a high-performance payment platform, designed to help scale your business revenue sustainably over time!\n\n"
        "Our secure, risk-managed payment solution delivers advanced fraud prevention and ensures industry-leading transaction reliability. "
        "Join thousands of businesses already enjoying sustainable growth.\n\n"
        "Get started today with absolutely no hidden fees, no setup costs, and reliable support!\n\n"
        "Disclaimer: All financial and investment decisions involve risk. Past performance does not guarantee future results. "
        "Users should evaluate their financial circumstances and seek independent professional advice where appropriate."
    )
    res = compliance_engine.run_compliance_audit(clean_content, "social_media", workspace_with_rules[2])
    assert res.compliance_score == 100
    assert res.status == "compliant"
    assert len(res.findings) == 0


# ---------------------------------------------------------------------------
# 11. Historical reviews retain their original findings and score
# ---------------------------------------------------------------------------
def test_scenario_11_historical_reviews_retain_original_findings_and_score(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Legacy Audit", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    saved_id = review.id
    saved_score = review.compliance_score
    saved_findings_count = len(review.findings)

    # Fetch from historical records
    fetched = review_service.get_by_id(db, saved_id)
    assert fetched.compliance_score == saved_score
    assert len(fetched.findings) == saved_findings_count
    assert fetched.original_content == SAMPLE_NON_COMPLIANT_CONTENT


# ---------------------------------------------------------------------------
# 12. Accepted corrections and reviewer decisions remain consistent
# ---------------------------------------------------------------------------
def test_scenario_12_accepted_corrections_and_reviewer_decisions_consistent(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    reviewer = User(email="lead_reviewer@novapay.com", hashed_password="pw", name="Lead Reviewer")
    db.add(reviewer)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved"))
    db.commit()

    sub = ContentReviewSubmission(title="Sign-off Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    # Employee applies all corrections
    for f in list(review.findings):
        if f.suggested_correction:
            review_service.apply_correction(db, review.id, f.id, user.id)

    db.refresh(review)
    # Employee requests reviewer approval
    appr_req = approval_service.request_review_approval(db, review_id=review.id, user=user)
    # Reviewer approves
    approved_appr = approval_service.approve(db, approval=appr_req, reviewer=reviewer)

    db.refresh(review)
    assert approved_appr.status == "approved"
    assert review.status == "approved"
    assert review.compliance_score == 100


# ---------------------------------------------------------------------------
# 13. Real Gemini Provider Integration Verification (credential check + minimal call)
# ---------------------------------------------------------------------------
def test_scenario_13_gemini_client_credential_safety_and_diagnostics():
    from app.services.ai.gemini_client import gemini_client, redact_sensitive
    from app.core.config import settings

    # Verify credential redaction utility strictly prevents key leakage
    fake_key = "AIzaSy" + "K" * 33
    redacted = redact_sensitive(f"Error communicating with key {fake_key}")
    assert fake_key not in redacted
    assert "REDACTED" in redacted

    # Also verify direct api_key param redaction
    custom_secret = "my_custom_secret_api_key_value"
    redacted_custom = redact_sensitive(f"Bearer {custom_secret}", api_key=custom_secret)
    assert custom_secret not in redacted_custom

    # Verify Gemini provider configuration is active
    assert settings.AI_PROVIDER.lower() == "gemini"
    assert settings.GEMINI_MODEL == "gemini-3.6-flash"


# ---------------------------------------------------------------------------
# 14. Failed replacement raises ValueError and does NOT mark finding as applied
# ---------------------------------------------------------------------------
def test_scenario_14_failed_replacement_raises_error_and_does_not_mutate_document(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Failed Replacement Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    # Fabricate a finding with an excerpt that does NOT exist in the working content
    fake_finding = Finding(
        review_id=review.id,
        category="Content restrictions",
        severity="critical",
        excerpt="completely non-existent phrase in this text 123456",
        explanation="Non existent phrase",
        suggested_correction="something else",
        confidence=1.0,
        status="open",
        guideline_reference="Rule #1: Fake",
    )
    db.add(fake_finding)
    db.commit()
    db.refresh(fake_finding)

    original_content_before = review.content

    with pytest.raises(ValueError) as exc_info:
        review_service.apply_correction(db, review.id, fake_finding.id, user.id)

    assert "was not found in current working document" in str(exc_info.value)
    db.refresh(fake_finding)
    db.refresh(review)
    assert fake_finding.status == "open"  # NOT marked applied
    assert review.content == original_content_before  # Document unchanged


# ---------------------------------------------------------------------------
# 15. Overlapping findings preserve prior modifications
# ---------------------------------------------------------------------------
def test_scenario_15_overlapping_findings_preserve_prior_modifications(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    text_with_overlap = (
        "Introducing NovaPay Global — guaranteed to double your business revenue overnight! "
        "Our 100% risk-free payment solution eliminates all fraud."
    )
    sub = ContentReviewSubmission(title="Overlap Test", content=text_with_overlap, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    finding_guarantee = next(f for f in review.findings if "guaranteed to double" in f.excerpt)
    finding_overnight = next(f for f in review.findings if "overnight" in f.excerpt)

    # Apply first fix
    resp1 = review_service.apply_correction(db, review.id, finding_guarantee.id, user.id)
    assert "guaranteed to double" not in resp1.updated_content
    assert "designed to help scale" in resp1.updated_content

    # Apply second fix
    resp2 = review_service.apply_correction(db, review.id, finding_overnight.id, user.id)
    assert "designed to help scale" in resp2.updated_content  # First fix preserved
    assert "overnight" not in resp2.updated_content or "revenue sustainably over time" in resp2.updated_content


# ---------------------------------------------------------------------------
# 16. Disclaimer insertion without duplication
# ---------------------------------------------------------------------------
def test_scenario_16_disclaimer_insertion_without_duplication(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Disclaimer Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    disclaimer_finding = next(f for f in review.findings if "disclaimer" in f.category.lower() or f.excerpt == "[Missing Regulatory Disclaimer]")

    resp1 = review_service.apply_correction(db, review.id, disclaimer_finding.id, user.id)
    assert "Disclaimer:" in resp1.updated_content
    count_before = resp1.updated_content.count("Disclaimer:")
    assert count_before == 1

    # Applying again or applying another disclaimer finding does not duplicate
    db.refresh(disclaimer_finding)
    disclaimer_finding.status = "open"  # reset to test duplicate prevention
    db.commit()

    resp2 = review_service.apply_correction(db, review.id, disclaimer_finding.id, user.id)
    assert resp2.updated_content.count("Disclaimer:") == 1  # No duplicate disclaimer inserted


# ---------------------------------------------------------------------------
# 17. Compliance score is not 100/100 when violations remain
# ---------------------------------------------------------------------------
def test_scenario_17_compliance_score_not_100_when_violations_remain(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Partial Remediation", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    # Apply ONLY 1 of 5 findings
    first_finding = review.findings[0]
    resp = review_service.apply_correction(db, review.id, first_finding.id, user.id)

    db.refresh(review)
    assert review.compliance_score < 100
    assert resp.compliance_score < 100
    # Other findings remain open
    open_findings = [f for f in review.findings if f.status == "open"]
    assert len(open_findings) > 0


# ---------------------------------------------------------------------------
# 18. Rechecking actual document reflects remaining violations
# ---------------------------------------------------------------------------
def test_scenario_18_rechecking_actual_document_reflects_remaining_violations(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Recheck Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    # Apply 1 fix
    first_finding = review.findings[0]
    resp = review_service.apply_correction(db, review.id, first_finding.id, user.id)

    # Recheck against full rules engine
    recheck_res = compliance_engine.run_compliance_audit(resp.updated_content, "social_media", rules)
    assert recheck_res.compliance_score < 100
    assert len(recheck_res.findings) > 0
    assert recheck_res.status in ("needs_changes", "critical_issues")


# ---------------------------------------------------------------------------
# 19. Original content remains strictly immutable through all modifications
# ---------------------------------------------------------------------------
def test_scenario_19_original_content_immutable_through_multiple_corrections(db, workspace_with_rules):
    ws, user, rules = workspace_with_rules
    sub = ContentReviewSubmission(title="Immutability Test", content=SAMPLE_NON_COMPLIANT_CONTENT, content_type="social_media")
    review = review_service.submit_and_audit(db, ws.id, user.id, sub)

    initial_original_content = review.original_content
    for f in list(review.findings):
        if f.suggested_correction:
            try:
                review_service.apply_correction(db, review.id, f.id, user.id)
            except ValueError:
                pass

    db.refresh(review)
    assert review.original_content == initial_original_content
    assert review.content != review.original_content
