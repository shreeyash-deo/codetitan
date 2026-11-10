import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.core.security import get_password_hash, create_access_token
from app.services.workspace_service import workspace_service
from app.services.approval_service import approval_service


def setup_remediation_env(client, db):
    admin = User(
        name="Admin Test",
        email="admin_rem1@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    reviewer = User(
        name="Reviewer Test",
        email="rev_rem1@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    employee = User(
        name="Employee Test",
        email="emp_rem1@example.com",
        hashed_password=get_password_hash("Pass123!"),
        role="User",
    )
    db.add_all([admin, reviewer, employee])
    db.commit()

    ws = Workspace(name="Remediation Workspace", org_id=workspace_service.generate_org_id(db))
    db.add(ws)
    db.commit()

    m_admin = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin", status="approved")
    m_rev = WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved")
    m_emp = WorkspaceMember(workspace_id=ws.id, user_id=employee.id, role="Employee", status="approved")
    db.add_all([m_admin, m_rev, m_emp])
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


def test_history_serialization_provides_both_field_pairs(client, db):
    """
    DEFECT A: Verify GET /api/v1/history/{id} serializes both
    (snippet, suggestion) and (originalText, suggestedCorrection)
    so neither the old nor new frontend contracts fail.
    """
    env = setup_remediation_env(client, db)
    ws_id = env["ws"].id

    review = ContentReview(
        workspace_id=ws_id,
        title="Evidence Serialization Test",
        content="Working text with claim.",
        original_content="Original text with claim.",
        content_type="blog",
        status="pending",
        compliance_score=85,
        submitted_by=env["employee"].id,
    )
    db.add(review)
    db.commit()

    finding1 = Finding(
        review_id=review.id,
        severity="critical",
        category="Claims",
        excerpt="100% guarantee",
        explanation="Prohibited superlative claim",
        guideline_reference="RULE-1: No Superlatives",
        suggested_correction="industry-leading standard",
        confidence=0.95,
        status="open",
    )
    db.add(finding1)
    db.commit()

    res = client.get(f"/api/v1/history/{review.id}", headers=env["admin_headers"])
    assert res.status_code == 200
    data = res.json()
    assert len(data["findings"]) == 1
    f = data["findings"][0]

    # Authoritative fields must be present and identical
    assert f["originalText"] == "100% guarantee"
    assert f["snippet"] == "100% guarantee"
    assert f["suggestedCorrection"] == "industry-leading standard"
    assert f["suggestion"] == "industry-leading standard"
    assert f["supportingGuidelineTitle"] == "RULE-1: No Superlatives"


def test_history_serialization_handles_empty_evidence_gracefully(client, db):
    """
    DEFECT A: When finding evidence or suggested correction is genuinely empty/None,
    it must serialize as empty strings, never crashing or inventing fake data.
    """
    env = setup_remediation_env(client, db)
    ws_id = env["ws"].id

    review = ContentReview(
        workspace_id=ws_id,
        title="Empty Evidence Test",
        content="Some content",
        original_content="Some content",
        content_type="blog",
        status="pending",
        compliance_score=70,
        submitted_by=env["employee"].id,
    )
    db.add(review)
    db.commit()

    finding_empty = Finding(
        review_id=review.id,
        severity="major",
        category="Tone",
        excerpt="",
        explanation="Tone inconsistency detected",
        guideline_reference="RULE-2: Brand Tone",
        suggested_correction=None,
        confidence=0.8,
        status="open",
    )
    db.add(finding_empty)
    db.commit()

    res = client.get(f"/api/v1/history/{review.id}", headers=env["admin_headers"])
    assert res.status_code == 200
    f = res.json()["findings"][0]
    assert f["originalText"] == ""
    assert f["snippet"] == ""
    assert f["suggestedCorrection"] == ""
    assert f["suggestion"] == ""


def test_automated_submission_summary_classified_as_system_event(client, db):
    """
    DEFECT B: When an automated submission summary is sent during request-approval,
    the backend sets user_id=None and the history mapper classifies the actor
    as 'BrandShield Sentinel' ('Automated System').
    """
    env = setup_remediation_env(client, db)
    ws_id = env["ws"].id

    review = ContentReview(
        workspace_id=ws_id,
        title="Automated Summary Test",
        content="Working copy",
        original_content="Original copy",
        content_type="blog",
        status="pending",
        compliance_score=90,
        submitted_by=env["employee"].id,
    )
    db.add(review)
    db.commit()

    summary_note = "Submitted for sign-off with 3 corrections applied. Current compliance score: 90%."
    req_res = client.post(
        f"/api/v1/reviews/{review.id}/request-approval",
        json={"summary": summary_note},
        headers=env["emp_headers"],
    )
    assert req_res.status_code == 201

    # Check ReviewActivity in database: user_id must be None for automated summary
    act = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == review.id,
        ReviewActivity.action == "Approval requested"
    ).first()
    assert act is not None
    assert act.user_id is None, "Automated submission summary activity must have user_id=None"
    assert act.details == summary_note

    # Check GET /api/v1/history/{id} timeline mapping
    h_res = client.get(f"/api/v1/history/{review.id}", headers=env["admin_headers"])
    assert h_res.status_code == 200
    timeline = h_res.json()["timeline"]

    appr_event = next((e for e in timeline if e["stage"] == "Approval requested"), None)
    assert appr_event is not None
    assert appr_event["actorName"] == "BrandShield Sentinel"
    assert appr_event["actorRole"] == "Automated System"
    assert appr_event["note"] == summary_note


def test_human_comments_and_actions_remain_attributed_to_user(client, db):
    """
    DEFECT B: Genuine human reviewer comments and manual decisions must remain
    accurately attributed to the human user.
    """
    env = setup_remediation_env(client, db)
    ws_id = env["ws"].id

    review = ContentReview(
        workspace_id=ws_id,
        title="Human Comment Test",
        content="Working copy",
        original_content="Original copy",
        content_type="blog",
        status="pending",
        compliance_score=90,
        submitted_by=env["employee"].id,
    )
    db.add(review)
    db.commit()

    # Reviewer adds genuine human comment
    comment_text = "Please verify the third paragraph citations before publishing."
    c_res = client.post(
        f"/api/v1/approvals/{review.id}/comments",
        json={"text": comment_text},
        headers=env["rev_headers"],
    )
    assert c_res.status_code == 200

    # Verify history ledger comments
    h_res = client.get(f"/api/v1/history/{review.id}", headers=env["admin_headers"])
    assert h_res.status_code == 200
    comments = h_res.json()["comments"]
    assert len(comments) == 1
    assert comments[0]["authorName"] == "Reviewer Test"
    assert comments[0]["authorRole"] == "Reviewer"
    assert comments[0]["text"] == comment_text


def test_approvals_endpoint_resolves_review_over_colliding_approval(client, db):
    """
    DEFECT C: If an Approval ticket (e.g. for a brand rule) has ID X and status 'approved',
    and a ContentReview also has ID X with status 'pending', calling
    POST /api/v1/approvals/X/approve MUST resolve the ContentReview and approve it,
    never erroneously returning 'Item has already been approved' from the colliding ticket.
    """
    env = setup_remediation_env(client, db)
    ws_id = env["ws"].id

    # 1. Create a ContentReview with a specific ID (or note its ID)
    review = ContentReview(
        workspace_id=ws_id,
        title="Colliding ID Review",
        content="Safe marketing copy",
        original_content="Safe marketing copy",
        content_type="blog",
        status="pending",
        compliance_score=95,
        submitted_by=env["employee"].id,
    )
    db.add(review)
    db.commit()
    target_id = review.id

    # 2. Seed an unrelated Approval record with the EXACT same ID, but status='approved'
    # In SQLite, if ID is available, we can insert an Approval with id=target_id if not taken,
    # or ensure an approved approval has id == target_id.
    colliding_approval = db.query(Approval).filter(Approval.id == target_id).first()
    if not colliding_approval:
        colliding_approval = Approval(
            id=target_id,
            brand_rule_id=999,
            submitted_by=env["admin"].id,
            reviewer_id=env["admin"].id,
            status="approved",
            comment="Approved brand rule with colliding ID",
        )
        db.add(colliding_approval)
        db.commit()
    else:
        colliding_approval.status = "approved"
        db.commit()

    # 3. Verify that review.status is still 'pending'
    db.refresh(review)
    assert review.status == "pending"
    assert colliding_approval.id == review.id
    assert colliding_approval.status == "approved"

    # 4. Reviewer approves via /api/v1/approvals/{target_id}/approve
    appr_res = client.post(
        f"/api/v1/approvals/{target_id}/approve",
        json={"comment": "Approved by reviewer"},
        headers=env["rev_headers"],
    )
    # MUST NOT return 400 'Item has already been approved.'!
    assert appr_res.status_code == 200, f"Expected 200, got {appr_res.status_code}: {appr_res.text}"
    data = appr_res.json()
    assert data["status"] == "approved"
    assert data["id"] == target_id

    # 5. Review in database is now approved
    db.refresh(review)
    assert review.status == "approved"
