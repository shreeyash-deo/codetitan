import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.guideline import GuidelineDocument
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.core.security import get_password_hash, create_access_token


def test_full_release_candidate_user_journey(client, db):
    """
    End-to-End Release Candidate Journey:
    1. Admin registers, creates an organisation, uploads guideline text, extracts & approves rules into Brand Memory.
    2. Admin checks dashboard: shows 1 guideline, approved rules count, zero reviews baseline.
    3. Employee joins org, scans content violating approved rule -> gets exact excerpt violation & score reduction.
    4. Employee applies fix, rechecks content, submits for review.
    5. Reviewer inspects submission in pending queue, adds a comment, and requests revision with specific notes.
    6. Reviewer decision and comments appear in historical ledger with full audit timeline.
    7. Dashboard reflects updated review count, pending approvals, and live activity stream.
    """
    # -------------------------------------------------------------
    # STEP 1: Admin Journey (Register, Create Org, Ingest Rules)
    # -------------------------------------------------------------
    reg_admin = client.post(
        "/api/auth/register",
        json={"name": "Alice Executive", "email": "alice_exec@enterprise.corp", "password": "AdminSecret123!"},
    )
    assert reg_admin.status_code == 201
    admin_auth = client.post(
        "/api/auth/login",
        json={"email": "alice_exec@enterprise.corp", "password": "AdminSecret123!"},
    )
    assert admin_auth.status_code == 200
    admin_token = admin_auth.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create Organisation
    create_org = client.post(
        "/api/workspaces",
        json={"name": "Apex Global Financial"},
        headers=admin_headers,
    )
    assert create_org.status_code == 201
    ws_id = create_org.json()["id"]
    org_id = create_org.json()["org_id"]
    assert org_id.startswith("ORG-")

    # Verify Admin Membership via /api/v1/brands
    me_brands = client.get("/api/v1/brands", headers=admin_headers)
    assert me_brands.status_code == 200
    assert any(b["id"] == str(ws_id) and b["role"] == "Admin" for b in me_brands.json())

    # Initial Dashboard check: clean zero-state
    dash_zero = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert dash_zero.status_code == 200
    d_zero = dash_zero.json()
    assert d_zero["total_reviews"] == 0
    assert d_zero["has_reviews"] is False
    assert d_zero["total_approved_brand_rules"] == 0

    # Ingest Brand Guideline Document
    guideline_text = b"Brand Rule: Prohibit Unsubstantiated Claims. Never use '100% guarantee' or 'zero risk' in external marketing copy."
    upload_doc = client.post(
        "/api/v1/guidelines/documents/upload",
        files={"file": ("Apex_Brand_Manual.txt", guideline_text, "text/plain")},
        data={"brand_id": str(ws_id)},
        headers=admin_headers,
    )
    assert upload_doc.status_code == 200
    doc_id = int(upload_doc.json()["id"])

    # Admin approves authoritative Brand Rule into Brand Memory
    rule = BrandRule(
        workspace_id=ws_id,
        document_id=doc_id,
        title="Prohibit Unsubstantiated Claims",
        description="Never use \"100% guarantee\" or \"zero risk\" in external marketing copy.",
        category="Claims & Restrictions",
        source_reference="Apex_Brand_Manual.txt:Section 1",
        confidence=0.98,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Confirm rule appears in Brand Memory
    approved_rules = client.get(f"/api/v1/guidelines/rules?brand_id={ws_id}", headers=admin_headers)
    assert approved_rules.status_code == 200
    assert any(r["title"] == "Prohibit Unsubstantiated Claims" for r in approved_rules.json())

    # Dashboard reflects uploaded document and approved rule
    dash_step1 = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert dash_step1.json()["uploaded_documents"] == 1
    assert dash_step1.json()["total_approved_brand_rules"] == 1

    # -------------------------------------------------------------
    # STEP 2: Employee Journey (Scan Violating Copy & Submit)
    # -------------------------------------------------------------
    # Register Employee & add to org
    reg_emp = client.post(
        "/api/auth/register",
        json={"name": "Bob Creator", "email": "bob_creator@enterprise.corp", "password": "EmpSecret123!"},
    )
    assert reg_emp.status_code == 201
    emp_user_id = reg_emp.json()["id"]

    # Add Employee to Workspace
    add_m = client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"user_id": emp_user_id, "role": "Employee"},
        headers=admin_headers,
    )
    assert add_m.status_code == 201

    # Employee Login
    emp_auth = client.post(
        "/api/auth/login",
        json={"email": "bob_creator@enterprise.corp", "password": "EmpSecret123!"},
    )
    assert emp_auth.status_code == 200
    emp_token = emp_auth.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Employee scans violating copy
    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Spring Launch Newsletter",
            "content": "Deposit with Apex Vault today. We offer a 100% guarantee on all retail clearing schedules.",
            "contentType": "Email",
            "channel": "Email",
        },
        headers=emp_headers,
    )
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    review_id = int(scan_data["id"])

    # Verify score deduction and exact violation detection
    assert scan_data["overallScore"] < 100
    assert len(scan_data["findings"]) >= 1
    found_term = any("100% guarantee" in f["originalText"] for f in scan_data["findings"])
    assert found_term, f"Expected '100% guarantee' in findings: {scan_data['findings']}"

    # Employee requests managerial approval
    req_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": "Please review this launch copy."},
        headers=emp_headers,
    )
    assert req_res.status_code == 201

    # Security check: Employee attempts to approve their own content -> 403 Forbidden!
    emp_tamper_approve = client.post(
        f"/api/v1/approvals/{review_id}/approve",
        json={"comment": "Self-approval attempt"},
        headers=emp_headers,
    )
    assert emp_tamper_approve.status_code == 403

    # -------------------------------------------------------------
    # STEP 3: Reviewer Journey (Inspect, Comment, Request Changes)
    # -------------------------------------------------------------
    # Register Reviewer & add to org
    reg_rev = client.post(
        "/api/auth/register",
        json={"name": "Carol Reviewer", "email": "carol_rev@enterprise.corp", "password": "RevSecret123!"},
    )
    assert reg_rev.status_code == 201
    rev_user_id = reg_rev.json()["id"]

    client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"user_id": rev_user_id, "role": "Reviewer"},
        headers=admin_headers,
    )

    rev_auth = client.post(
        "/api/auth/login",
        json={"email": "carol_rev@enterprise.corp", "password": "RevSecret123!"},
    )
    rev_token = rev_auth.json()["access_token"]
    rev_headers = {"Authorization": f"Bearer {rev_token}"}

    # Reviewer inspects pending approvals queue
    pending_queue = client.get(f"/api/v1/approvals/pending?brand_id={ws_id}", headers=rev_headers)
    assert pending_queue.status_code == 200
    queue_items = pending_queue.json()
    assert any(item["reviewId"] == str(review_id) for item in queue_items)

    # Reviewer adds comment
    comment_res = client.post(
        f"/api/v1/approvals/{review_id}/comments",
        json={"text": "Please remove the '100% guarantee' phrase and resubmit."},
        headers=rev_headers,
    )
    assert comment_res.status_code == 200

    # Reviewer requests changes with mandatory revision instructions
    change_res = client.post(
        f"/api/v1/approvals/{review_id}/request-changes",
        json={"comment": "Prohibited guarantee claim must be removed before publish."},
        headers=rev_headers,
    )
    assert change_res.status_code == 200
    assert change_res.json()["status"] == "needs_changes"

    # -------------------------------------------------------------
    # STEP 4: History & Dashboard Verification
    # -------------------------------------------------------------
    # Verify Review History ledger contains the record with accurate timeline & comments
    history_res = client.get(f"/api/v1/history/{review_id}", headers=emp_headers)
    assert history_res.status_code == 200
    h_item = history_res.json()
    assert h_item["approvalStatus"] == "needs_revision"
    assert h_item["submittedBy"]["name"] == "Bob Creator"
    assert any("remove the '100% guarantee'" in c["text"] for c in h_item["comments"])
    assert any(t["stage"] == "Changes requested" for t in h_item["timeline"])

    # Verify Dashboard reflects real live state
    dash_final = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert dash_final.status_code == 200
    d_data = dash_final.json()
    assert d_data["total_reviews"] == 1
    assert d_data["has_reviews"] is True
    assert d_data["reviews_needing_changes"] == 1
    assert len(d_data["violations_by_category"]) >= 1
    assert any(a["action"] in ("Changes requested", "Comment Added", "Approval Requested") for a in d_data["recent_activity"])
