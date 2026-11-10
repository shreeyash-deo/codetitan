"""
Phase 3 Verification Test Suite — Reviewer Comments and Approval Timeline (DEF-06)
Verifies:
1. Submission without a comment leaves the comments collection empty.
2. Submission creates the appropriate system activity event in the timeline.
3. Human-authored reviewer comments remain visible and correctly attributed.
4. Existing historical comments (e.g. reviewer change requests) are preserved with author metadata.
5. System events and human comments are strictly distinguishable.
6. Repeated submission attempts do not create duplicate activity entries.
7. Automated submission summaries are never converted into fake human comments.
"""

import pytest
from app.models.user import User
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.core.security import create_access_token


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


def setup_test_workspace(client, db, org_suffix: str):
    admin = auth_service.create_user(
        db, UserCreate(name="Timeline Admin", email=f"admin_{org_suffix}@org.io", password="Password123!")
    )
    admin_headers = _headers_for(admin)
    ws_res = client.post("/api/workspaces", json={"name": f"Org {org_suffix}"}, headers=admin_headers)
    assert ws_res.status_code == 201
    ws = ws_res.json()

    reviewer = auth_service.create_user(
        db, UserCreate(name="Lead Reviewer", email=f"reviewer_{org_suffix}@org.io", password="Password123!")
    )
    client.post(f"/api/workspaces/{ws['id']}/members", json={"user_id": reviewer.id, "role": "Reviewer"}, headers=admin_headers)
    reviewer_headers = _headers_for(reviewer)

    employee = auth_service.create_user(
        db, UserCreate(name="Marketing Author", email=f"author_{org_suffix}@org.io", password="Password123!")
    )
    client.post(f"/api/workspaces/{ws['id']}/members", json={"user_id": employee.id, "role": "Employee"}, headers=admin_headers)
    employee_headers = _headers_for(employee)

    # Seed an approved brand rule
    client.post(
        f"/api/workspaces/{ws['id']}/rules",
        json={
            "title": "Prohibited Superlatives",
            "description": "Restricted terminology: 'the single best' is prohibited in marketing copy.",
            "category": "Restricted terminology",
            "approval_status": "approved",
        },
        headers=admin_headers,
    )

    return {
        "workspace": ws,
        "admin": admin,
        "admin_headers": admin_headers,
        "reviewer": reviewer,
        "reviewer_headers": reviewer_headers,
        "employee": employee,
        "employee_headers": employee_headers,
    }


def test_01_submission_without_comment_leaves_comments_empty(client, db):
    """Submitting content for review without a comment must not create a fake comment."""
    env = setup_test_workspace(client, db, "tl01")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Product Launch Post",
            "content": "Introducing our leading global platform.",
            "contentType": "Social",
            "channel": "LinkedIn",
        },
        headers=emp_headers,
    )
    assert scan_res.status_code == 200
    review_id = int(scan_res.json()["id"])

    # Submit for approval without comment
    req_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"summary": "Submitted for sign-off with 0 corrections applied. Current compliance score: 100%."},
        headers=emp_headers,
    )
    assert req_res.status_code == 201

    # Check detail endpoint
    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()

    # Requirement 1 & 6: Comments collection must remain completely empty
    assert detail["comments"] == []

    # Pending queue commentsCount must be 0
    pending_res = client.get(f"/api/v1/approvals/pending?brand_id={ws_id}", headers=rev_headers)
    assert pending_res.status_code == 200
    pending_item = next(p for p in pending_res.json() if p["reviewId"] == str(review_id))
    assert pending_item["commentsCount"] == 0


def test_02_submission_creates_appropriate_system_activity_event(client, db):
    """Submissions record submission summaries as system timeline/activity events."""
    env = setup_test_workspace(client, db, "tl02")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Ad Copy Fall 2026",
            "content": "Enjoy reliable services with clear pricing.",
            "contentType": "Ad",
            "channel": "Search",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])

    summary_text = "Submitted for sign-off with 1 corrections applied. Current compliance score: 95%."
    client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"summary": summary_text},
        headers=emp_headers,
    )

    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    detail = detail_res.json()

    # Timeline must record the event without misrepresenting author as writing a comment
    timeline_stages = [t["stage"] for t in detail["timeline"]]
    assert "Content submitted" in timeline_stages
    assert "Approval requested" in timeline_stages

    approval_event = next(t for t in detail["timeline"] if t["stage"] == "Approval requested")
    assert approval_event["actorName"] == env["employee"].name
    assert approval_event["note"] == summary_text

    # Comments must NOT have this summary
    assert detail["comments"] == []


def test_03_human_authored_reviewer_comments_remain_visible_and_correctly_attributed(client, db):
    """Reviewers posting genuine comments have them visible in the comments section with correct attribution."""
    env = setup_test_workspace(client, db, "tl03")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Campaign Deck",
            "content": "Our solution delivers instant results.",
            "contentType": "Presentation",
            "channel": "Sales",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={}, headers=emp_headers)

    # Lead reviewer adds a human comment
    comment_text = "Headline needs review: please ensure substantiation for 'instant results'."
    comment_res = client.post(
        f"/api/approvals/{review_id}/comments",
        json={"text": comment_text},
        headers=rev_headers,
    )
    assert comment_res.status_code == 200
    res_data = comment_res.json()
    assert res_data["authorName"] == env["reviewer"].name
    assert res_data["text"] == comment_text

    # Verify detail view has the comment
    detail_res = client.get(f"/api/v1/history/{review_id}", headers=emp_headers)
    detail = detail_res.json()
    assert len(detail["comments"]) == 1
    c = detail["comments"][0]
    assert c["text"] == comment_text
    assert c["authorName"] == env["reviewer"].name
    assert c["authorRole"] in ("Reviewer", "reviewer")

    # Pending queue reflects 1 comment
    pending_res = client.get(f"/api/v1/approvals/pending?brand_id={ws_id}", headers=rev_headers)
    pending_item = next(p for p in pending_res.json() if p["reviewId"] == str(review_id))
    assert pending_item["commentsCount"] == 1


def test_04_existing_historical_comments_preserved(client, db):
    """Reviewer decision feedback (e.g. request changes) is preserved in comments with author metadata."""
    env = setup_test_workspace(client, db, "tl04")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Blog Post",
            "content": "We are the number one payment platform.",
            "contentType": "Blog",
            "channel": "Blog",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={}, headers=emp_headers)

    # Reviewer requests changes with specific notes
    change_notes = "Please remove 'number one' claim and replace with compliant phrasing."
    change_res = client.post(
        f"/api/approvals/{review_id}/request-changes",
        json={"revisionNotes": change_notes},
        headers=rev_headers,
    )
    assert change_res.status_code == 200

    detail_res = client.get(f"/api/v1/history/{review_id}", headers=emp_headers)
    detail = detail_res.json()
    assert detail["approvalStatus"] == "needs_revision"
    assert any(c["text"] == change_notes and c["authorName"] == env["reviewer"].name for c in detail["comments"])


def test_05_system_events_and_human_comments_are_distinguishable(client, db):
    """System timeline events are not listed as comments, and human comments appear in comments list."""
    env = setup_test_workspace(client, db, "tl05")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Press Release",
            "content": "NovaPay announces strategic partnership.",
            "contentType": "Press",
            "channel": "PR",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={}, headers=emp_headers)

    client.post(
        f"/api/approvals/{review_id}/comments",
        json={"text": "PR team approved the quotes."},
        headers=rev_headers,
    )

    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    detail = detail_res.json()

    # Comments contains ONLY the human comment
    assert len(detail["comments"]) == 1
    assert detail["comments"][0]["text"] == "PR team approved the quotes."

    # Timeline contains system events
    timeline_stages = [t["stage"] for t in detail["timeline"]]
    assert "Content submitted" in timeline_stages
    assert "AI review completed" in timeline_stages
    assert "Approval requested" in timeline_stages
    assert "Comment Added" in timeline_stages


def test_06_repeated_submission_attempts_do_not_create_duplicate_activity_entries(client, db):
    """Repeatedly calling request-approval on the same review does not create duplicate activities or approval tickets."""
    env = setup_test_workspace(client, db, "tl06")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Newsletter",
            "content": "Monthly treasury insights.",
            "contentType": "Newsletter",
            "channel": "Email",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])

    # Call request-approval 3 times in a row
    for _ in range(3):
        res = client.post(
            f"/api/v1/reviews/{review_id}/request-approval",
            json={"summary": "Submission summary: 0 corrections applied. Current compliance score: 100%."},
            headers=emp_headers,
        )
        assert res.status_code == 201

    # Verify database has exactly 1 pending Approval ticket
    approvals = db.query(Approval).filter(Approval.review_id == review_id, Approval.status == "pending").all()
    assert len(approvals) == 1

    # Verify timeline does not duplicate "Approval requested"
    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    detail = detail_res.json()
    req_stages = [t for t in detail["timeline"] if t["stage"] == "Approval requested"]
    assert len(req_stages) == 1


def test_07_automated_submission_summary_filtered_from_comments(client, db):
    """Legacy clients or payloads sending automated summary strings in 'comment' field are safely routed to activity."""
    env = setup_test_workspace(client, db, "tl07")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Legacy Payload Review",
            "content": "Compliant content for testing.",
            "contentType": "Social",
            "channel": "Twitter",
        },
        headers=emp_headers,
    )
    review_id = int(scan_res.json()["id"])

    # Old client sends automated summary in comment field
    automated_text = "Submitted for sign-off with 2 corrections applied. Current compliance score: 98%."
    res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": automated_text},
        headers=emp_headers,
    )
    assert res.status_code == 201

    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    detail = detail_res.json()

    # The automated text must NOT be in comments
    assert detail["comments"] == []

    # The automated text must be in the timeline activity
    req_stage = next(t for t in detail["timeline"] if t["stage"] == "Approval requested")
    assert req_stage["note"] == automated_text
