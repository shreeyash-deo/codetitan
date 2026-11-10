import hashlib
import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.approval import Approval
from app.core.security import get_password_hash, create_access_token
from app.services.workspace_service import workspace_service
from app.services.review_service import review_service


def setup_scoring_env(db):
    admin = User(
        name="Scoring Admin",
        email="scoring_admin@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    reviewer = User(
        name="Scoring Reviewer",
        email="scoring_rev@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    employee = User(
        name="Scoring Author",
        email="scoring_emp@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    db.add_all([admin, reviewer, employee])
    db.commit()

    ws = Workspace(name="Scoring Workspace", org_id=workspace_service.generate_org_id(db))
    db.add(ws)
    db.commit()

    m_admin = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin", status="approved")
    m_rev = WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved")
    m_emp = WorkspaceMember(workspace_id=ws.id, user_id=employee.id, role="Employee", status="approved")
    db.add_all([m_admin, m_rev, m_emp])
    db.commit()

    # Create approved brand rules for testing
    rule_unsupported = BrandRule(
        workspace_id=ws.id,
        category="Content restrictions",
        title="Prohibit Guaranteed Financial Returns",
        description='Marketing content must never guarantee financial returns. Prohibited expressions include: "100% guaranteed", "crazy secret".',
        confidence=0.95,
        approval_status="approved",
    )
    db.add(rule_unsupported)
    db.commit()

    admin_token = create_access_token(subject=admin.id, extra_claims={"role": admin.role})
    rev_token = create_access_token(subject=reviewer.id, extra_claims={"role": reviewer.role})
    emp_token = create_access_token(subject=employee.id, extra_claims={"role": employee.role})

    return {
        "ws": ws,
        "admin": admin,
        "reviewer": reviewer,
        "employee": employee,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "rev_headers": {"Authorization": f"Bearer {rev_token}"},
        "emp_headers": {"Authorization": f"Bearer {emp_token}"},
    }


def test_initial_submission_receives_persisted_score_and_hash(client, db):
    env = setup_scoring_env(db)
    content = "Our revolutionary platform is 100% guaranteed to eliminate all risk and deliver results."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Initial Guaranteed Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    data = res.json()
    review_id = data["id"]

    # Verify score is calculated and persisted in DB
    db_review = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    assert db_review is not None
    assert db_review.audit_status == "verified"
    assert db_review.audited_content_hash == hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
    assert db_review.audited_at is not None
    # Critical violation ("100% guaranteed") deducts 25 points from 100 -> 75
    assert db_review.compliance_score <= 75
    assert db_review.original_content == content
    assert db_review.content == content


def test_apply_single_correction_updates_score_and_preserves_original(client, db):
    env = setup_scoring_env(db)
    content = "This tool is 100% guaranteed for all users."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Copy To Correct",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    assert len(findings) > 0
    f_crit = next(f for f in findings if "100% guaranteed" in f.excerpt.lower())

    # Set suggested correction
    f_crit.suggested_correction = "rigorously tested"
    db.commit()

    # Apply correction via endpoint
    apply_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/{f_crit.id}/apply",
        headers=env["emp_headers"],
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()

    # Working content was updated
    assert "rigorously tested" in apply_data["updated_content"]
    assert "100% guaranteed" not in apply_data["updated_content"]

    # Original content preserved untouched
    assert apply_data["original_content"] == content

    # DB state verified
    db.expire_all()
    db_rev = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    assert db_rev.original_content == content
    assert "rigorously tested" in db_rev.content
    assert db_rev.audit_status == "verified"
    assert db_rev.audited_content_hash == hashlib.sha256(db_rev.content.strip().encode("utf-8")).hexdigest()
    # Now that the critical issue is gone, score is 100
    assert db_rev.compliance_score == 100


def test_manual_edit_via_patch_triggers_recalculation(client, db):
    env = setup_scoring_env(db)
    content = "Our software has a crazy secret algorithm."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Crazy Secret Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]
    initial_score = res.json()["compliance_score"]
    assert initial_score < 100  # "crazy secret" is minor -> -5 -> 95

    # Edit manually to clean text via PATCH
    clean_content = "Our software has an advanced predictive algorithm."
    patch_res = client.patch(
        f"/api/v1/reviews/{review_id}",
        json={"content": clean_content},
        headers=env["emp_headers"],
    )
    assert patch_res.status_code == 200
    patched_data = patch_res.json()

    assert patched_data["compliance_score"] == 100
    assert patched_data["audit_status"] == "verified"
    assert patched_data["audited_content_hash"] == hashlib.sha256(clean_content.strip().encode("utf-8")).hexdigest()

    # Verify findings were refreshed
    open_findings = db.query(Finding).filter(Finding.review_id == review_id, Finding.status == "open").all()
    assert len(open_findings) == 0


def test_unverified_content_hash_mismatch_blocks_approval_submission(client, db):
    env = setup_scoring_env(db)
    content = "This product is 100% guaranteed to perform."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Submission Hash Integrity Check",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    # Directly mutate content in DB without auditing to simulate unverified edits
    db_rev = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    db_rev.content = "Sneaky un-audited alteration made to copy."
    db.commit()

    # Submitting for approval must fail because audited_content_hash does not match
    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": "Ready for approval"},
        headers=env["emp_headers"],
    )
    assert appr_res.status_code == 400
    assert "Current working content does not match" in appr_res.json()["detail"]


def test_clean_document_receives_100_percent_verified(client, db):
    env = setup_scoring_env(db)
    clean_copy = "Our platform is built on enterprise-grade infrastructure with transparent performance metrics."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Pristine Copy",
            "content": clean_copy,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    data = res.json()
    assert data["compliance_score"] == 100
    assert data["audit_status"] == "verified"
    assert data["status"] == "compliant"

    # Submit for approval succeeds cleanly
    appr_res = client.post(
        f"/api/v1/reviews/{data['id']}/request-approval",
        json={"comment": "Clean compliant copy"},
        headers=env["emp_headers"],
    )
    assert appr_res.status_code == 201


def test_admin_employee_reviewer_read_same_persisted_score(client, db):
    env = setup_scoring_env(db)
    content = "Check out our crazy secret for better results."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Consistent Role Access Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    # Request history endpoint as Employee
    h_emp = client.get(f"/api/v1/history/{review_id}", headers=env["emp_headers"]).json()
    # Request history endpoint as Reviewer
    h_rev = client.get(f"/api/v1/history/{review_id}", headers=env["rev_headers"]).json()
    # Request history endpoint as Admin
    h_admin = client.get(f"/api/v1/history/{review_id}", headers=env["admin_headers"]).json()

    assert h_emp["score"] == h_rev["score"] == h_admin["score"]
    assert h_emp["score"] < 100
    assert h_emp["auditStatus"] == h_rev["auditStatus"] == h_admin["auditStatus"] == "verified"
    assert h_emp["auditedContentHash"] == h_rev["auditedContentHash"] == h_admin["auditedContentHash"]


def test_batch_apply_corrections_recalculates_score_and_findings(client, db):
    env = setup_scoring_env(db)
    content = "Our product has a 100% guaranteed result and a crazy secret engine."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Multiple Violations Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    assert len(findings) >= 2
    for f in findings:
        if "100% guaranteed" in f.excerpt.lower():
            f.suggested_correction = "high-performance"
        elif "crazy secret" in f.excerpt.lower():
            f.suggested_correction = "advanced"
    db.commit()

    # Call batch-apply endpoint
    batch_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/batch-apply",
        headers=env["emp_headers"],
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()

    assert batch_data["compliance_score"] == 100
    assert batch_data["audit_status"] == "verified"
    assert "high-performance" in batch_data["content"]
    assert "advanced" in batch_data["content"]
    assert batch_data["audited_content_hash"] == hashlib.sha256(batch_data["content"].strip().encode("utf-8")).hexdigest()

    # Immutable original preserved
    assert batch_data["original_content"] == content


def test_recheck_endpoint_recalculates_score(client, db):
    env = setup_scoring_env(db)
    content = "Pristine copy ready for review."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Recheck Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    recheck_res = client.post(
        f"/api/v1/reviews/{review_id}/recheck",
        headers=env["emp_headers"],
    )
    assert recheck_res.status_code == 200
    data = recheck_res.json()
    assert data["compliance_score"] == 100
    assert data["audit_status"] == "verified"


def test_failed_audit_status_blocks_approval_submission(client, db):
    env = setup_scoring_env(db)
    content = "Clean copy here."

    res = client.post(
        f"/api/v1/workspaces/{env['ws'].id}/reviews",
        json={
            "title": "Failed Status Copy",
            "content": content,
            "content_type": "social_media",
        },
        headers=env["emp_headers"],
    )
    assert res.status_code == 201
    review_id = res.json()["id"]

    # Invalidate audit_status to 'failed'
    db_rev = db.query(ContentReview).filter(ContentReview.id == review_id).first()
    db_rev.audit_status = "failed"
    db.commit()

    # Submission must be rejected
    appr_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": "Submit failed audit copy"},
        headers=env["emp_headers"],
    )
    assert appr_res.status_code == 400
    assert "Content compliance audit status is 'failed'" in appr_res.json()["detail"]
