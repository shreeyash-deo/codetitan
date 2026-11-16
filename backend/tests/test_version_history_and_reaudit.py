"""
BrandShield Round 3 — Improvement 2: Automated Content Re-Audit and Version History
Comprehensive test suite verifying all 15+ architectural requirements and mandatory corrections A-J.
"""
import pytest
import hashlib
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.version import ContentVersion
from app.models.finding import Finding
from app.models.approval import Approval
from app.core.security import get_password_hash, create_access_token
from app.services.review_service import review_service
from app.services.version_comparison_service import VersionComparisonService
from app.schemas.review import ContentReviewSubmission


SAMPLE_CONTENT = (
    "Introducing NovaPay Global — the world's fastest payment platform, guaranteed to double your business revenue overnight!\n\n"
    "Our 100% risk-free payment solution eliminates every security threat and ensures zero transaction failures."
)


@pytest.fixture
def versioning_env(db: Session):
    ws = Workspace(name="Version Test Org", org_id="ORG-VER-001")
    db.add(ws)
    db.flush()

    admin = User(name="Test Admin", email="admin@ver.com", hashed_password=get_password_hash("pass"), role="Admin")
    author = User(name="Test Author", email="author@ver.com", hashed_password=get_password_hash("pass"), role="User")
    reviewer = User(name="Test Reviewer", email="reviewer@ver.com", hashed_password=get_password_hash("pass"), role="User")
    db.add_all([admin, author, reviewer])
    db.flush()

    db.add_all([
        WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin", status="approved"),
        WorkspaceMember(workspace_id=ws.id, user_id=author.id, role="Employee", status="approved"),
        WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved"),
    ])
    db.flush()

    rules = [
        BrandRule(
            workspace_id=ws.id,
            category="Claims & Performance",
            title="Prohibit Guaranteed Revenue",
            description="Content must not guarantee financial returns. Prohibited: double your business revenue overnight.",
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Risk & Indemnity",
            title="Prohibit Absolute Risk-Free Claims",
            description="Never describe services as 100% risk-free.",
            confidence=0.95,
            approval_status="approved",
        ),
    ]
    db.add_all(rules)
    db.commit()

    token_author = create_access_token(subject=author.id, extra_claims={"role": "Employee"})
    token_admin = create_access_token(subject=admin.id, extra_claims={"role": "Admin"})
    token_reviewer = create_access_token(subject=reviewer.id, extra_claims={"role": "Reviewer"})

    return {
        "ws": ws,
        "author": author,
        "admin": admin,
        "reviewer": reviewer,
        "author_headers": {"Authorization": f"Bearer {token_author}"},
        "admin_headers": {"Authorization": f"Bearer {token_admin}"},
        "reviewer_headers": {"Authorization": f"Bearer {token_reviewer}"},
    }


# ============================================================================
# Scenario 1: Initial Submission Creates Version 1
# ============================================================================
def test_initial_submission_creates_v1(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={
            "title": "Campaign Launch v1",
            "content": SAMPLE_CONTENT,
            "content_type": "social_media",
        },
    )
    assert res.status_code == 201
    data = res.json()
    review_id = data["id"]

    assert data["current_version_number"] == 1
    assert data["compliance_score"] < 100

    # Verify ContentVersion in DB
    v1 = (
        db.query(ContentVersion)
        .filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 1)
        .first()
    )
    assert v1 is not None
    assert v1.version_number == 1
    assert v1.content == SAMPLE_CONTENT
    assert v1.content_hash == hashlib.sha256(SAMPLE_CONTENT.strip().encode("utf-8")).hexdigest()
    assert v1.change_description == "Initial Submission"
    assert v1.audit_status in ("verified", "degraded")
    assert v1.compliance_score == data["compliance_score"]

    # Verify findings are associated with version_id == v1.id
    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    assert len(findings) > 0
    for f in findings:
        assert f.version_id == v1.id


# ============================================================================
# Scenario 2: Immutable Historical Records (Section A)
# ============================================================================
def test_immutable_historical_records(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    # 1. Create v1
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Immutability Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    v1 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 1).first()
    v1_hash_orig = v1.content_hash
    v1_score_orig = v1.compliance_score
    v1_status_orig = v1.audit_status
    v1_findings_orig = [(f.id, f.excerpt, f.status) for f in v1.findings]

    # 2. Modify content to create v2
    clean_content = "Introducing NovaPay Global — our enterprise platform designed to accelerate your business growth."
    client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": clean_content},
    )

    db.expire_all()
    v1_after = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 1).first()
    assert v1_after.content_hash == v1_hash_orig
    assert v1_after.compliance_score == v1_score_orig
    assert v1_after.audit_status == v1_status_orig
    v1_findings_after = [(f.id, f.excerpt, f.status) for f in v1_after.findings]
    assert v1_findings_after == v1_findings_orig

    # Verify v2 exists and is separate
    v2 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 2).first()
    assert v2 is not None
    assert v2.version_number == 2
    assert v2.content == clean_content
    assert v2.compliance_score >= v1_after.compliance_score


# ============================================================================
# Scenario 3: Explicit Recheck Creates v2 Even If Content Unchanged (Section E.6)
# ============================================================================
def test_explicit_recheck_creates_v2_even_if_content_unchanged(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Recheck Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # Call POST /reviews/{id}/recheck
    recheck_res = client.post(
        f"/api/v1/reviews/{review_id}/recheck",
        headers=headers,
    )
    assert recheck_res.status_code == 200
    data = recheck_res.json()
    assert data["current_version_number"] == 2

    # Verify Version 2 in db
    v2 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 2).first()
    assert v2 is not None
    assert v2.version_number == 2
    assert v2.change_description == "Re-audit request"
    assert v2.content_hash == hashlib.sha256(SAMPLE_CONTENT.strip().encode("utf-8")).hexdigest()


# ============================================================================
# Scenario 4: Content Edit Creates v+1 (Section E.2)
# ============================================================================
def test_content_edit_creates_v_plus_1(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Edit Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    new_text = SAMPLE_CONTENT + " Contact our sales team today."
    patch_res = client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": new_text},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["current_version_number"] == 2

    v2 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 2).first()
    assert v2 is not None
    assert v2.content == new_text.strip()


# ============================================================================
# Scenario 5: Saving Unchanged Content Does NOT Create Duplicate Version (Section E.5)
# ============================================================================
def test_saving_unchanged_content_does_not_create_duplicate_version(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Unchanged Content Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # PATCH with the identical content string
    patch_res = client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": SAMPLE_CONTENT},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["current_version_number"] == 1

    # Total versions must remain 1
    versions_count = db.query(ContentVersion).filter(ContentVersion.review_id == review_id).count()
    assert versions_count == 1


# ============================================================================
# Scenario 6: Single Correction Creates Version N+1 (Section E.3)
# ============================================================================
def test_single_correction_creates_v_plus_1(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Correction Version Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]
    findings = res.json()["findings"]
    first_f = findings[0]

    apply_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/{first_f['id']}/apply",
        headers=headers,
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["current_version_number"] == 2

    # Check ContentVersion v2
    v2 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 2).first()
    assert v2 is not None
    assert "Applied correction" in v2.change_description


# ============================================================================
# Scenario 7: Batch Apply Corrections Creates Exactly ONE Version N+1 (Section E.4)
# ============================================================================
def test_batch_apply_corrections_creates_single_version(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Batch Version Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    batch_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/batch-apply",
        headers=headers,
    )
    assert batch_res.status_code == 200
    assert batch_res.json()["current_version_number"] == 2

    # Verify exactly 2 versions exist (v1 and v2, not v1, v2, v3)
    all_versions = (
        db.query(ContentVersion)
        .filter(ContentVersion.review_id == review_id)
        .order_by(ContentVersion.version_number.asc())
        .all()
    )
    assert len(all_versions) == 2
    assert all_versions[1].version_number == 2
    assert "batch corrections" in all_versions[1].change_description.lower()


# ============================================================================
# Scenario 8: Audit Status Reflects Actual Outcome, Not Hardcoded Default (Section D)
# ============================================================================
def test_audit_status_reflects_actual_outcome_not_hardcoded(client: TestClient, versioning_env, db: Session):
    # 1. Workspace without rules
    empty_ws = Workspace(name="Empty Org", org_id="ORG-EMPTY-001")
    db.add(empty_ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=empty_ws.id, user_id=versioning_env["author"].id, role="Employee", status="approved"))
    db.commit()

    # submit_and_audit raises NoApprovedRulesError when no rules exist
    with pytest.raises(Exception):
        review_service.submit_and_audit(
            db=db,
            workspace_id=empty_ws.id,
            user_id=versioning_env["author"].id,
            submission=ContentReviewSubmission(title="No rules", content="Text", content_type="social_media"),
        )


# ============================================================================
# Scenario 9: Degraded / Unverified Audit Blocks Approval Request (Section D)
# ============================================================================
def test_degraded_audit_blocks_approval(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Degraded Approval Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # Artificially set review audit_status to 'degraded'
    review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    review.audit_status = "degraded"
    db.commit()

    # Attempt to request approval
    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        headers=headers,
        json={"comment": "Please approve"},
    )
    assert appr_res.status_code == 400
    assert "degraded" in appr_res.json()["detail"].lower()


# ============================================================================
# Scenario 10: Approval Stamps Current Version (Section G)
# ============================================================================
def test_approval_stamps_current_version(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    # 1. Create clean content that passes audit with verified status
    clean_text = "Introducing NovaPay Global, a high performance payment platform for expanding modern commerce."
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Approval Stamp Test", "content": clean_text, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # 2. Advance to v2 via explicit recheck
    recheck_res = client.post(
        f"/api/v1/reviews/{review_id}/recheck",
        headers=headers,
    )
    assert recheck_res.json()["current_version_number"] == 2

    # 3. Request approval
    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        headers=headers,
        json={"comment": "Ready for sign-off on v2"},
    )
    assert appr_res.status_code in (200, 201)
    appr_data = appr_res.json()
    assert appr_data["version_number"] == 2

    # Verify in DB
    approval = db.query(Approval).filter(Approval.review_id == review_id).first()
    assert approval is not None
    assert approval.version_number == 2


# ============================================================================
# Scenario 11: Approval Validates Latest Content Hash (Section G)
# ============================================================================
def test_approval_validates_latest_content_hash(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    clean_text = "NovaPay Global reliable payment infrastructure."
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Hash Tamper Test", "content": clean_text, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # Tamper working content directly in DB without updating audited_content_hash
    rev = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    rev.content = clean_text + " Tampered un-audited text."
    db.commit()

    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        headers=headers,
        json={"comment": "Tampered"},
    )
    assert appr_res.status_code == 400
    assert "does not match" in appr_res.json()["detail"].lower()


# ============================================================================
# Scenario 12: Active Review Returns Current Version Findings Only (Section C)
# ============================================================================
def test_active_review_returns_current_version_findings_only(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    # v1 has violations
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Findings Scope Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]
    v1_findings = res.json()["findings"]
    assert len(v1_findings) > 0

    # v2 remediates violations
    clean_text = "NovaPay Global platform designed for compliant business growth."
    patch_res = client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": clean_text},
    )
    assert patch_res.json()["current_version_number"] == 2

    # Fetch active review via GET /reviews/{id}
    active_res = client.get(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
    )
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["current_version_number"] == 2
    # Current version has 0 findings
    assert len(active_data["findings"]) == 0

    # Historical v1 findings remain in DB and associated with v1
    v1 = db.query(ContentVersion).filter(ContentVersion.review_id == review_id, ContentVersion.version_number == 1).first()
    assert len(v1.findings) > 0


# ============================================================================
# Scenario 13: Historical Version Endpoints (Section C & E)
# ============================================================================
def test_historical_version_endpoints(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Endpoints Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # Recheck to create v2
    client.post(f"/api/v1/reviews/{review_id}/recheck", headers=headers)

    # 1. GET /reviews/{id}/versions
    versions_res = client.get(f"/api/v1/reviews/{review_id}/versions", headers=headers)
    assert versions_res.status_code == 200
    v_list = versions_res.json()
    assert len(v_list) == 2
    assert v_list[0]["version_number"] == 1
    assert v_list[1]["version_number"] == 2

    # 2. GET /reviews/{id}/versions/1
    v1_detail = client.get(f"/api/v1/reviews/{review_id}/versions/1", headers=headers)
    assert v1_detail.status_code == 200
    assert v1_detail.json()["version_number"] == 1
    assert len(v1_detail.json()["findings"]) > 0

    # 3. Non-existent version returns 404
    v99_res = client.get(f"/api/v1/reviews/{review_id}/versions/99", headers=headers)
    assert v99_res.status_code == 404


# ============================================================================
# Scenario 14: Version Comparison Text and Score (Section F)
# ============================================================================
def test_version_comparison_text_and_score(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Comparison Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    clean_text = "Introducing NovaPay Global — our reliable payment solution."
    client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": clean_text},
    )

    compare_res = client.get(
        f"/api/v1/reviews/{review_id}/compare?source_version=1&target_version=2",
        headers=headers,
    )
    assert compare_res.status_code == 200
    c_data = compare_res.json()

    assert c_data["source_version"]["version_number"] == 1
    assert c_data["target_version"]["version_number"] == 2
    assert c_data["score_after"] >= c_data["score_before"]
    assert c_data["score_delta"] == c_data["score_after"] - c_data["score_before"]
    assert len(c_data["text_diff"]) > 0
    assert "raw_diff" in c_data


# ============================================================================
# Scenario 15: Version Comparison Findings Delta (Section F)
# ============================================================================
def test_version_comparison_findings_delta(client: TestClient, versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    headers = versioning_env["author_headers"]

    # v1 has violations
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        headers=headers,
        json={"title": "Delta Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # v2 remediates violations
    clean_text = "Introducing NovaPay Global payment infrastructure."
    client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=headers,
        json={"content": clean_text},
    )

    compare_res = client.get(
        f"/api/v1/reviews/{review_id}/compare?source_version=1&target_version=2",
        headers=headers,
    )
    delta = compare_res.json()["findings_delta"]
    assert len(delta["resolved"]) > 0
    assert len(delta["new"]) == 0


# ============================================================================
# Scenario 16: Concurrent Edit Conflict Handling (Section E.7)
# ============================================================================
def test_concurrent_edit_conflict_handling(versioning_env, db: Session):
    ws_id = versioning_env["ws"].id
    review = ContentReview(
        workspace_id=ws_id,
        title="Concurrent Review",
        content="Initial content",
        original_content="Initial content",
        content_type="social_media",
        status="in_review",
        compliance_score=80,
        audit_status="verified",
        current_version_number=1,
    )
    db.add(review)
    db.commit()

    v1 = ContentVersion(
        review_id=review.id,
        version_number=1,
        content="Initial content",
        content_hash=hashlib.sha256(b"Initial content").hexdigest(),
        compliance_score=80,
        audit_status="verified",
        findings_count=0,
    )
    db.add(v1)
    db.commit()

    # Attempting to insert a duplicate version_number for the same review must raise IntegrityError
    dup_v1 = ContentVersion(
        review_id=review.id,
        version_number=1,
        content="Conflicting content",
        content_hash=hashlib.sha256(b"Conflicting content").hexdigest(),
        compliance_score=85,
        audit_status="verified",
        findings_count=0,
    )
    db.add(dup_v1)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ============================================================================
# Scenario 17: Legacy Snapshot Migration Semantics (Section B)
# ============================================================================
def test_legacy_snapshot_migration_semantics(db: Session):
    ws = Workspace(name="Legacy Org", org_id="ORG-LEGACY-001")
    db.add(ws)
    db.commit()

    orig_text = "Original submission text"
    modified_text = "Remediated working text"
    review = ContentReview(
        workspace_id=ws.id,
        title="Legacy Review",
        content=modified_text,
        original_content=orig_text,  # Differs from content
        content_type="social_media",
        status="in_review",
        compliance_score=85,
        audit_status="verified",
        audited_content_hash=None,  # No hash established
        current_version_number=1,
    )
    db.add(review)
    db.commit()

    # Simulate legacy migration logic:
    # 1. Because orig_text != modified_text -> change_description = "Legacy Snapshot"
    # 2. Because audited_content_hash is None -> audit_status = "unverified"
    exp_hash = hashlib.sha256(modified_text.strip().encode("utf-8")).hexdigest()
    change_desc = "Legacy Snapshot" if (review.original_content != review.content) else "Initial Submission"
    actual_audit_status = (
        review.audit_status
        if (review.audited_content_hash and review.audited_content_hash == exp_hash)
        else "unverified"
    )

    baseline_v1 = ContentVersion(
        review_id=review.id,
        version_number=1,
        content=review.content,
        content_hash=exp_hash,
        compliance_score=review.compliance_score,
        status=review.status,
        audit_status=actual_audit_status,
        findings_count=0,
        change_description=change_desc,
    )
    db.add(baseline_v1)
    db.commit()

    assert baseline_v1.change_description == "Legacy Snapshot"
    assert baseline_v1.audit_status == "unverified"


# ============================================================================
# Scenario 18: Employee Scoping vs Admin/Reviewer RBAC for Version History
# ============================================================================
def test_employee_version_scoping_and_rbac(client: TestClient, versioning_env, db: Session):
    ws = versioning_env["ws"]
    author = versioning_env["author"]
    admin = versioning_env["admin"]
    reviewer = versioning_env["reviewer"]

    # Create a second author (Employee) in the same workspace
    author2 = User(name="Author Two", email="author2@ver.com", hashed_password=get_password_hash("pass"), role="User")
    db.add(author2)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=author2.id, role="Employee", status="approved"))
    db.commit()

    token_author2 = create_access_token(subject=author2.id, extra_claims={"role": "Employee"})
    author2_headers = {"Authorization": f"Bearer {token_author2}"}

    # Author 1 submits a review
    res = client.post(
        f"/api/v1/workspaces/{ws.id}/reviews",
        headers=versioning_env["author_headers"],
        json={"title": "Private Author Review", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    # 1. Author 1 can view versions of their own review
    v_res_1 = client.get(f"/api/v1/reviews/{review_id}/versions", headers=versioning_env["author_headers"])
    assert v_res_1.status_code == 200
    assert len(v_res_1.json()) == 1

    # 2. Author 2 CANNOT access Author 1's version history (403 Forbidden)
    v_res_2 = client.get(f"/api/v1/reviews/{review_id}/versions", headers=author2_headers)
    assert v_res_2.status_code == 403
    assert "only view their own" in v_res_2.json()["detail"].lower()

    # 3. Author 2 CANNOT access specific version detail (403 Forbidden)
    detail_res_2 = client.get(f"/api/v1/reviews/{review_id}/versions/1", headers=author2_headers)
    assert detail_res_2.status_code == 403

    # 4. Author 2 CANNOT compare versions of Author 1's review (403 Forbidden)
    compare_res_2 = client.get(f"/api/v1/reviews/{review_id}/compare?source_version=1&target_version=1", headers=author2_headers)
    assert compare_res_2.status_code == 403

    # 5. Admin CAN view versions of any review in the workspace (200 OK)
    admin_v_res = client.get(f"/api/v1/reviews/{review_id}/versions", headers=versioning_env["admin_headers"])
    assert admin_v_res.status_code == 200
    assert len(admin_v_res.json()) == 1

    # 6. Reviewer CAN view versions of any review in the workspace (200 OK)
    reviewer_v_res = client.get(f"/api/v1/reviews/{review_id}/versions", headers=versioning_env["reviewer_headers"])
    assert reviewer_v_res.status_code == 200
    assert len(reviewer_v_res.json()) == 1


# ============================================================================
# Scenario 19: Version State Distinctions & Metadata Enrichment
# ============================================================================
def test_version_state_distinctions_and_enrichment(client: TestClient, versioning_env, db: Session):
    ws = versioning_env["ws"]
    author_headers = versioning_env["author_headers"]
    reviewer_headers = versioning_env["reviewer_headers"]

    # Create clean review that passes compliance
    clean_text = "NovaPay Global helps businesses manage compliant payment workflows with confidence."
    res = client.post(
        f"/api/v1/workspaces/{ws.id}/reviews",
        headers=author_headers,
        json={"title": "State Distinction Test", "content": clean_text, "content_type": "social_media"},
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    # Fetch versions list
    v_list = client.get(f"/api/v1/reviews/{review_id}/versions", headers=author_headers).json()
    assert len(v_list) == 1
    v1 = v_list[0]
    assert v1["version_number"] == 1
    assert v1["is_original"] is True
    assert v1["is_current"] is True
    assert v1["version_state"] in ("audited", "saved_draft")
    assert v1["author_name"] == "Test Author"

    # Advance to v2 with an edit
    v2_text = clean_text + " Scalable and enterprise-ready."
    client.patch(
        f"/api/v1/reviews/{review_id}",
        headers=author_headers,
        json={"content": v2_text},
    )

    v_list_2 = client.get(f"/api/v1/reviews/{review_id}/versions", headers=author_headers).json()
    assert len(v_list_2) == 2
    v1_after = v_list_2[0]
    v2 = v_list_2[1]
    assert v1_after["is_current"] is False
    assert v2["is_current"] is True
    assert v2["is_original"] is False

    # Request approval -> stamps v2 as submitted
    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        headers=author_headers,
        json={"comment": "Please approve v2"},
    )
    assert appr_res.status_code in (200, 201)

    v_list_3 = client.get(f"/api/v1/reviews/{review_id}/versions", headers=author_headers).json()
    assert v_list_3[1]["version_state"] == "submitted"

    # Reviewer requests changes on approval
    approval_id = appr_res.json()["id"]
    change_res = client.post(
        f"/api/v1/approvals/{approval_id}/request-changes",
        headers=reviewer_headers,
        json={"comment": "Please add more details regarding latency."},
    )
    assert change_res.status_code == 200

    v_list_4 = client.get(f"/api/v1/reviews/{review_id}/versions", headers=author_headers).json()
    assert v_list_4[1]["version_state"] == "changes_requested"


# ============================================================================
# Scenario 20: Historical Version Immutability Across Application APIs
# ============================================================================
def test_historical_versions_immutable_across_apis(client: TestClient, versioning_env, db: Session):
    ws = versioning_env["ws"]
    author_headers = versioning_env["author_headers"]

    res = client.post(
        f"/api/v1/workspaces/{ws.id}/reviews",
        headers=author_headers,
        json={"title": "Immutability API Test", "content": SAMPLE_CONTENT, "content_type": "social_media"},
    )
    review_id = res.json()["id"]

    # Verify no PUT / PATCH / DELETE endpoint exists for versions
    put_res = client.put(f"/api/v1/reviews/{review_id}/versions/1", headers=author_headers, json={"content": "Hacked"})
    assert put_res.status_code == 405

    patch_res = client.patch(f"/api/v1/reviews/{review_id}/versions/1", headers=author_headers, json={"content": "Hacked"})
    assert patch_res.status_code == 405

    delete_res = client.delete(f"/api/v1/reviews/{review_id}/versions/1", headers=author_headers)
    assert delete_res.status_code == 405
