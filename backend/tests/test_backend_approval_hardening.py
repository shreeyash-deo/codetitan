"""
Unit and integration tests for Improvement 3 — Stage 2: Backend Approval Hardening.
Tests all 15 required validation and governance scenarios:
1. New approval ticket binds to correct version_id and content_hash.
2. Degraded audit cannot be approved.
3. Failed or unverified audit cannot be approved.
4. Open critical finding blocks approval.
5. Resolved critical finding does not incorrectly block approval.
6. Mismatched content hash blocks approval.
7. Stale version ticket cannot approve current content.
8. Legacy unbound approval ticket cannot silently approve.
9. Approving one ticket does not overwrite earlier decisions.
10. Revision requests preserve prior decision history.
11. Rejection preserves prior decision history.
12. Editing approved content requires fresh approval.
13. New approval request correctly binds to the new version.
14. Compatibility endpoint cannot bypass validation.
15. Existing idempotency behavior remains correct.
"""
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.models.review import ContentReview
from app.models.version import ContentVersion
from app.models.finding import Finding
from app.models.approval import Approval
from app.models.rule import BrandRule
from app.core.security import get_password_hash, create_access_token
from app.services.approval_service import approval_service
from app.services.review_service import review_service


@pytest.fixture
def hardening_env(db: Session):
    """Set up workspace, users, rules, and initial review with ContentVersion 1."""
    ws = Workspace(name="Hardening Org", org_id="ORG-HDN-001")
    db.add(ws)
    db.flush()

    admin = User(name="Admin User", email="admin@hdn.com", hashed_password=get_password_hash("pass"), role="Admin")
    author = User(name="Employee User", email="author@hdn.com", hashed_password=get_password_hash("pass"), role="User")
    reviewer = User(name="Reviewer User", email="reviewer@hdn.com", hashed_password=get_password_hash("pass"), role="User")
    db.add_all([admin, author, reviewer])
    db.flush()

    db.add_all([
        WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin", status="approved"),
        WorkspaceMember(workspace_id=ws.id, user_id=author.id, role="Employee", status="approved"),
        WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved"),
    ])
    db.flush()

    rule = BrandRule(
        workspace_id=ws.id,
        category="Claims & Performance",
        title="Prohibit Unsubstantiated Claims",
        description="Never guarantee 100% returns.",
        confidence=0.95,
        approval_status="approved",
    )
    db.add(rule)
    db.flush()

    content_v1 = "NovaPay secure transaction engine delivers enterprise reliability."
    hash_v1 = hashlib.sha256(content_v1.encode("utf-8")).hexdigest()

    review = ContentReview(
        title="Spring Security Announcement",
        content=content_v1,
        original_content=content_v1,
        content_type="article",
        workspace_id=ws.id,
        submitted_by=author.id,
        compliance_score=95,
        status="in_review",
        audit_status="verified",
        audited_content_hash=hash_v1,
        current_version_number=1,
    )
    db.add(review)
    db.flush()

    v1 = ContentVersion(
        review_id=review.id,
        version_number=1,
        content=content_v1,
        content_hash=hash_v1,
        compliance_score=95,
        status="in_review",
        audit_status="verified",
        findings_count=0,
        rule_set_version="rules_count:1",
        summary="Initial audit passed",
        change_description="Initial Submission",
        author_id=author.id,
    )
    db.add(v1)
    db.flush()

    return {
        "workspace": ws,
        "admin": admin,
        "author": author,
        "reviewer": reviewer,
        "rule": rule,
        "review": review,
        "version": v1,
    }


def test_1_new_approval_ticket_binds_to_correct_version_and_hash(db: Session, hardening_env):
    """1. New approval ticket binds to correct version_id and content_hash."""
    env = hardening_env
    review = env["review"]
    v1 = env["version"]
    author = env["author"]

    approval = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="Please sign off v1",
    )

    assert approval.id is not None
    assert approval.version_id == v1.id
    assert approval.version_number == 1
    assert approval.content_hash == v1.content_hash
    assert approval.status == "pending"


def test_2_degraded_audit_cannot_be_approved(db: Session, hardening_env):
    """2. Degraded audit cannot be approved."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]
    v1 = env["version"]

    approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Mutate to degraded state
    v1.audit_status = "degraded"
    review.audit_status = "degraded"
    db.commit()

    with pytest.raises(ValueError, match="Compliance audit status must be 'verified'"):
        approval_service.approve(db=db, approval=approval, reviewer=reviewer)


def test_3_failed_or_unverified_audit_cannot_be_approved(db: Session, hardening_env):
    """3. Failed or unverified audit cannot be approved."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]
    v1 = env["version"]

    approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    v1.audit_status = "unverified"
    review.audit_status = "unverified"
    db.commit()

    with pytest.raises(ValueError, match="Compliance audit status must be 'verified'"):
        approval_service.approve(db=db, approval=approval, reviewer=reviewer)


def test_4_open_critical_finding_blocks_approval(db: Session, hardening_env):
    """4. Open critical finding blocks approval."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]
    v1 = env["version"]

    approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    critical_finding = Finding(
        review_id=review.id,
        version_id=v1.id,
        severity="critical",
        category="Claims & Performance",
        excerpt="guaranteed 100% returns",
        explanation="Strict prohibition violated",
        confidence=1.0,
        status="open",
    )
    db.add(critical_finding)
    db.commit()

    with pytest.raises(ValueError, match="open critical compliance violation"):
        approval_service.approve(db=db, approval=approval, reviewer=reviewer)


def test_5_resolved_critical_finding_does_not_incorrectly_block_approval(db: Session, hardening_env):
    """5. Resolved critical finding does not incorrectly block approval."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]
    v1 = env["version"]

    approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    resolved_finding = Finding(
        review_id=review.id,
        version_id=v1.id,
        severity="critical",
        category="Claims & Performance",
        excerpt="guaranteed 100% returns",
        explanation="Fixed in revised copy",
        confidence=1.0,
        status="resolved",
    )
    db.add(resolved_finding)
    db.commit()

    approved_ticket = approval_service.approve(db=db, approval=approval, reviewer=reviewer)
    assert approved_ticket.status == "approved"
    assert review.status == "approved"


def test_6_mismatched_content_hash_blocks_approval(db: Session, hardening_env):
    """6. Mismatched content hash blocks approval."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Mutate approval ticket hash
    approval.content_hash = "0" * 64
    db.commit()

    with pytest.raises(ValueError, match="content hash does not match"):
        approval_service.approve(db=db, approval=approval, reviewer=reviewer)


def test_7_stale_version_ticket_cannot_approve_current_content(db: Session, hardening_env):
    """7. Stale version ticket cannot approve current content."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    v1_approval = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Review gets updated to Version 2
    v2_content = "NovaPay secure transaction engine delivers enterprise reliability v2."
    v2_hash = hashlib.sha256(v2_content.encode("utf-8")).hexdigest()
    v2 = ContentVersion(
        review_id=review.id,
        version_number=2,
        content=v2_content,
        content_hash=v2_hash,
        compliance_score=98,
        status="in_review",
        audit_status="verified",
        findings_count=0,
        author_id=author.id,
    )
    db.add(v2)
    review.current_version_number = 2
    review.content = v2_content
    review.audited_content_hash = v2_hash
    review.status = "in_review"
    db.commit()

    # Attempting to approve the stale v1 ticket must fail
    with pytest.raises(ValueError, match="Cannot approve stale ticket"):
        approval_service.approve(db=db, approval=v1_approval, reviewer=reviewer)


def test_8_legacy_unbound_approval_ticket_cannot_silently_approve(db: Session, hardening_env):
    """8. Legacy unbound approval ticket cannot silently approve."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    legacy_approval = Approval(
        review_id=review.id,
        submitted_by=author.id,
        status="pending",
        version_id=None,
        content_hash=None,
        version_number=None,
    )
    db.add(legacy_approval)
    db.commit()

    with pytest.raises(ValueError, match="not bound to a verified version snapshot"):
        approval_service.approve(db=db, approval=legacy_approval, reviewer=reviewer)


def test_9_approving_one_ticket_does_not_overwrite_earlier_decisions(db: Session, hardening_env):
    """9. Approving one ticket does not overwrite earlier decisions."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]
    admin = env["admin"]

    ticket_1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.request_changes(db=db, approval=ticket_1, reviewer=reviewer, comment="Need clearer disclosures")

    assert ticket_1.status == "changes_requested"
    assert ticket_1.comment == "Need clearer disclosures"

    # Now create v2
    v2_content = "NovaPay secure transaction engine with full disclosures."
    v2_hash = hashlib.sha256(v2_content.encode("utf-8")).hexdigest()
    v2 = ContentVersion(
        review_id=review.id,
        version_number=2,
        content=v2_content,
        content_hash=v2_hash,
        compliance_score=100,
        status="in_review",
        audit_status="verified",
        findings_count=0,
        author_id=author.id,
    )
    db.add(v2)
    review.current_version_number = 2
    review.content = v2_content
    review.audited_content_hash = v2_hash
    review.status = "in_review"
    db.commit()

    ticket_2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="Ready for v2 review")
    assert ticket_2.id != ticket_1.id
    assert ticket_2.version_number == 2

    # Admin approves ticket 2
    approval_service.approve(db=db, approval=ticket_2, reviewer=admin)

    db.refresh(ticket_1)
    db.refresh(ticket_2)

    # Ticket 1 must remain changes_requested with its original comment and reviewer
    assert ticket_1.status == "changes_requested"
    assert ticket_1.comment == "Need clearer disclosures"
    assert ticket_1.reviewer_id == reviewer.id

    # Ticket 2 is approved
    assert ticket_2.status == "approved"
    assert ticket_2.reviewer_id == admin.id


def test_10_revision_requests_preserve_prior_decision_history(db: Session, hardening_env):
    """10. Revision requests preserve prior decision history."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.request_changes(db=db, approval=t1, reviewer=reviewer, comment="Round 1 changes")

    # Second cycle
    v2 = ContentVersion(
        review_id=review.id,
        version_number=2,
        content="v2 text",
        content_hash=hashlib.sha256(b"v2 text").hexdigest(),
        compliance_score=90,
        status="in_review",
        audit_status="verified",
        author_id=author.id,
    )
    db.add(v2)
    review.current_version_number = 2
    review.content = "v2 text"
    review.audited_content_hash = v2.content_hash
    review.status = "in_review"
    db.commit()

    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.request_changes(db=db, approval=t2, reviewer=reviewer, comment="Round 2 changes")

    db.refresh(t1)
    db.refresh(t2)

    assert t1.comment == "Round 1 changes"
    assert t1.status == "changes_requested"
    assert t2.comment == "Round 2 changes"
    assert t2.status == "changes_requested"


def test_11_rejection_preserves_prior_decision_history(db: Session, hardening_env):
    """11. Rejection preserves prior decision history."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.request_changes(db=db, approval=t1, reviewer=reviewer, comment="Fix paragraph 2")

    # Second cycle
    v2 = ContentVersion(
        review_id=review.id,
        version_number=2,
        content="v2 revised",
        content_hash=hashlib.sha256(b"v2 revised").hexdigest(),
        compliance_score=90,
        status="in_review",
        audit_status="verified",
        author_id=author.id,
    )
    db.add(v2)
    review.current_version_number = 2
    review.content = "v2 revised"
    review.audited_content_hash = v2.content_hash
    review.status = "in_review"
    db.commit()

    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.reject(db=db, approval=t2, reviewer=reviewer, reason="Irreconcilable brand clash")

    db.refresh(t1)
    db.refresh(t2)

    assert t1.status == "changes_requested"
    assert t1.comment == "Fix paragraph 2"

    assert t2.status == "rejected"
    assert t2.comment == "Irreconcilable brand clash"
    assert review.status == "rejected"


def test_12_editing_approved_content_requires_fresh_approval(db: Session, hardening_env):
    """12. Editing approved content requires fresh approval."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.approve(db=db, approval=t1, reviewer=reviewer)
    assert review.status == "approved"

    # Edit review and re-audit
    updated_review = review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="Brand new revised copy after approval was granted.",
        user_id=author.id,
        change_description="Post-approval update",
    )

    # Review status must no longer be approved
    assert updated_review.status in ("in_review", "needs_changes")
    assert updated_review.status != "approved"
    assert updated_review.current_version_number == 2

    # Old ticket remains approved for historical record of v1
    db.refresh(t1)
    assert t1.status == "approved"
    assert t1.version_number == 1

    # Attempting to approve old ticket for v2 must fail
    with pytest.raises(ValueError):
        approval_service.approve(db=db, approval=t1, reviewer=reviewer)


def test_13_new_approval_request_correctly_binds_to_new_version(db: Session, hardening_env):
    """13. New approval request correctly binds to the new version."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    approval_service.approve(db=db, approval=t1, reviewer=reviewer)

    # Update to v2
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="Brand new revised copy after approval was granted.",
        user_id=author.id,
        change_description="Post-approval update",
    )

    t2 = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="Requesting approval for v2",
    )

    assert t2.id != t1.id
    assert t2.version_number == 2
    assert t2.version_id is not None
    assert t2.version_id != t1.version_id
    assert t2.content_hash == review.audited_content_hash
    assert t2.status == "pending"


def test_14_compatibility_endpoint_cannot_bypass_validation(client: TestClient, hardening_env):
    """14. Compatibility endpoint cannot bypass validation."""
    env = hardening_env
    review = env["review"]
    reviewer = env["reviewer"]
    v1 = env["version"]

    reviewer_token = create_access_token(
        subject=reviewer.id,
        extra_claims={"role": reviewer.role, "email": reviewer.email},
    )
    headers = {"Authorization": f"Bearer {reviewer_token}"}

    # Case A: Trying to approve via compat route without any pending approval request
    resp_no_appr = client.post(f"/api/v1/approvals/{review.id}/approve", headers=headers)
    assert resp_no_appr.status_code == 400
    assert "No pending approval request found" in resp_no_appr.json()["detail"]

    # Now create pending approval request for v1
    author = env["author"]
    approval_service.request_review_approval(db=client.app.dependency_overrides[review_service.get_db] if False else None or hardening_env["review"]._sa_instance_state.session, review_id=review.id, user=author)

    # Mutate audit_status to unverified
    v1.audit_status = "unverified"
    review.audit_status = "unverified"
    review._sa_instance_state.session.commit()

    # Case B: Calling compat route on unverified audit must fail with 400
    resp = client.post(f"/api/v1/approvals/{review.id}/approve", headers=headers)
    assert resp.status_code == 400
    assert "Compliance audit status must be 'verified'" in resp.json()["detail"]


def test_15_existing_idempotency_behavior_remains_correct(db: Session, hardening_env):
    """15. Existing idempotency behavior remains correct."""
    env = hardening_env
    review = env["review"]
    author = env["author"]

    t1 = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="First submission click",
    )

    t2 = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="Second submission click (double click)",
    )

    assert t1.id == t2.id
    assert t2.comment == "Second submission click (double click)"

    # Confirm only one approval ticket exists in the database
    approvals = db.query(Approval).filter(Approval.review_id == review.id).all()
    assert len(approvals) == 1


def test_16_v1_pending_ticket_remains_bound_to_v1_and_superseded_on_v2_submission(db: Session, hardening_env):
    """V1 pending ticket remains bound to V1 after V2 submission and is marked superseded."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    v1 = env["version"]

    # 1. Request approval for V1
    t1 = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="Submission for V1",
    )
    assert t1.version_id == v1.id
    assert t1.version_number == 1
    assert t1.content_hash == v1.content_hash
    assert t1.status == "pending"
    assert t1.comment == "Submission for V1"

    # 2. Advance review to V2
    v2_content = "NovaPay secure transaction engine delivering v2 enterprise performance."
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content=v2_content,
        user_id=author.id,
        change_description="Update to v2 copy",
    )
    v2 = db.query(ContentVersion).filter(ContentVersion.review_id == review.id, ContentVersion.version_number == 2).first()
    assert v2 is not None

    # 3. Employee requests approval for V2
    t2 = approval_service.request_review_approval(
        db=db,
        review_id=review.id,
        user=author,
        comment="Submission for V2",
    )

    # 4. Verify V1 ticket is immutable and marked superseded
    db.refresh(t1)
    assert t1.id != t2.id
    assert t1.status == "superseded"
    assert t1.version_id == v1.id
    assert t1.version_number == 1
    assert t1.content_hash == v1.content_hash
    assert t1.comment == "Submission for V1"

    # 5. Verify V2 ticket is bound to V2
    assert t2.status == "pending"
    assert t2.version_id == v2.id
    assert t2.version_number == 2
    assert t2.content_hash == v2.content_hash
    assert t2.comment == "Submission for V2"


def test_17_repeated_v2_requests_reuse_v2_ticket(db: Session, hardening_env):
    """Repeated V2 requests reuse the existing V2 ticket and do not create duplicate tickets."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    v1 = env["version"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="V1 request")

    # Advance to V2
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="Revised text for version two.",
        user_id=author.id,
        change_description="V2 update",
    )

    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="V2 initial request")
    assert t2.version_number == 2
    assert t2.status == "pending"

    # Re-request approval for V2
    t2_retry = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="V2 retry comment")
    assert t2_retry.id == t2.id
    assert t2_retry.comment == "V2 retry comment"

    # Total tickets: 1 superseded (v1), 1 pending (v2)
    tickets = db.query(Approval).filter(Approval.review_id == review.id).all()
    assert len(tickets) == 2
    statuses = {t.status for t in tickets}
    assert statuses == {"superseded", "pending"}


def test_18_v1_ticket_cannot_approve_v2(db: Session, hardening_env):
    """V1 ticket cannot approve V2 when review has advanced."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Advance to V2
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="V2 advanced content for testing.",
        user_id=author.id,
        change_description="V2 change",
    )

    # Request approval for V2
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Attempting to approve V1 ticket must fail
    with pytest.raises(ValueError):
        approval_service.approve(db=db, approval=t1, reviewer=reviewer)


def test_19_superseded_tickets_cannot_be_approved_or_rejected(db: Session, hardening_env):
    """Superseded tickets cannot be approved or have changes requested."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    # Advance to V2 and request approval to supersede t1
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="V2 advanced copy text.",
        user_id=author.id,
        change_description="V2 change",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    db.refresh(t1)
    assert t1.status == "superseded"

    # Attempt to approve superseded ticket
    with pytest.raises(ValueError, match="superseded"):
        approval_service.approve(db=db, approval=t1, reviewer=reviewer)

    # Attempt to request changes on superseded ticket
    with pytest.raises(ValueError, match="superseded"):
        approval_service.request_changes(db=db, approval=t1, reviewer=reviewer, comment="Needs work")


def test_20_previous_decision_history_remains_available(db: Session, hardening_env):
    """Previous decision history remains available and immutable across multiple versions."""
    env = hardening_env
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    # V1: Request changes
    t1 = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="V1 draft")
    approval_service.request_changes(db=db, approval=t1, reviewer=reviewer, comment="Please refine intro")
    db.refresh(t1)
    assert t1.status == "changes_requested"
    assert t1.reviewer_id == reviewer.id
    assert t1.comment == "Please refine intro"

    # V2: Re-audit and submit
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="V2 refined intro text content.",
        user_id=author.id,
        change_description="Refined intro",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="V2 draft ready")
    assert t2.id != t1.id
    assert t2.version_number == 2
    assert t2.status == "pending"

    # V1 ticket remains unchanged
    db.refresh(t1)
    assert t1.status == "changes_requested"
    assert t1.version_number == 1
    assert t1.comment == "Please refine intro"

    # Both tickets appear in review approvals query
    review_approvals = db.query(Approval).filter(Approval.review_id == review.id).order_by(Approval.version_number.asc()).all()
    assert len(review_approvals) == 2
    assert review_approvals[0].id == t1.id
    assert review_approvals[0].status == "changes_requested"
    assert review_approvals[1].id == t2.id
    assert review_approvals[1].status == "pending"


def test_21_concurrent_duplicate_requests_do_not_create_duplicate_tickets(db: Session, hardening_env):
    """Concurrent/repeated approval requests for the same review and version produce exactly one pending ticket."""
    env = hardening_env
    review = env["review"]
    author = env["author"]

    # Simulate rapid duplicate requests
    t_first = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="Rapid 1")
    t_second = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="Rapid 2")
    t_third = approval_service.request_review_approval(db=db, review_id=review.id, user=author, comment="Rapid 3")

    assert t_first.id == t_second.id == t_third.id
    pending_tickets = db.query(Approval).filter(Approval.review_id == review.id, Approval.status == "pending").all()
    assert len(pending_tickets) == 1
