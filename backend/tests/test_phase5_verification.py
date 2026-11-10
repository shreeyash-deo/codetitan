import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.guideline import GuidelineDocument
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.core.security import get_password_hash, create_access_token
from app.services.workspace_service import workspace_service


def setup_org_with_members(client, db, org_name="Phase5 Org"):
    # Admin
    admin_user = User(
        name=f"Admin {org_name}",
        email=f"admin_{org_name.lower().replace(' ', '')}@shield.corp",
        hashed_password=get_password_hash("AdminPass123!"),
        role="User",
    )
    # Employee
    emp_user = User(
        name=f"Emp {org_name}",
        email=f"emp_{org_name.lower().replace(' ', '')}@shield.corp",
        hashed_password=get_password_hash("EmpPass123!"),
        role="User",
    )
    db.add_all([admin_user, emp_user])
    db.commit()
    db.refresh(admin_user)
    db.refresh(emp_user)

    ws = Workspace(
        name=org_name,
        org_id=workspace_service.generate_org_id(db),
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # Memberships
    m_admin = WorkspaceMember(workspace_id=ws.id, user_id=admin_user.id, role="Admin")
    m_emp = WorkspaceMember(workspace_id=ws.id, user_id=emp_user.id, role="Employee")
    db.add_all([m_admin, m_emp])
    db.commit()

    admin_token = create_access_token(subject=admin_user.id, extra_claims={"role": admin_user.role})
    emp_token = create_access_token(subject=emp_user.id, extra_claims={"role": emp_user.role})

    return {
        "workspace": ws,
        "admin": admin_user,
        "employee": emp_user,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "emp_headers": {"Authorization": f"Bearer {emp_token}"},
    }


def test_scenario_01_new_org_clean_zero_dashboard(client, db):
    """Scenario 1: Dashboard for a brand-new organisation returns clean zero metrics with no fabrication."""
    env = setup_org_with_members(client, db, "Empty Org")
    ws_id = env["workspace"].id
    admin_headers = env["admin_headers"]

    # 1. Direct dashboard endpoint
    res = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_reviews"] == 0
    assert data["has_reviews"] is False
    assert data["pending_approvals"] == 0
    assert data["approved_reviews"] == 0
    assert data["critical_findings"] == 0
    assert data["total_approved_brand_rules"] == 0
    assert data["pending_brand_rules"] == 0
    assert data["uploaded_documents"] == 0
    assert len(data["violations_by_category"]) == 0
    assert len(data["recent_reviews"]) == 0
    assert len(data["recent_activity"]) == 0

    # 2. Compat telemetry endpoint
    tel_res = client.get(f"/api/v1/brands/{ws_id}/telemetry", headers=admin_headers)
    assert tel_res.status_code == 200
    tel_data = tel_res.json()
    assert tel_data["contentReviewedCount"] == 0
    assert tel_data["hasReviews"] is False
    assert tel_data["activeRulesCount"] == 0
    assert tel_data["pendingApprovalsCount"] == 0
    assert tel_data["criticalIssuesCount"] == 0
    assert tel_data["uploadedDocumentsCount"] == 0
    assert len(tel_data["violationsByCategory"]) == 0
    assert len(tel_data["recentActivity"]) == 0


def test_scenario_02_dashboard_tracks_guidelines_and_rules(client, db):
    """Scenario 2: Dashboard updates counts as guideline documents and approved rules are ingested."""
    env = setup_org_with_members(client, db, "Guidelines Org")
    ws_id = env["workspace"].id
    admin_headers = env["admin_headers"]

    # Upload guideline document
    fake_doc_bytes = b"Rule 1: Always communicate with clear, professional clarity. Avoid aggressive jargon."
    up_res = client.post(
        "/api/v1/guidelines/documents/upload",
        files={"file": ("style_guide.txt", fake_doc_bytes, "text/plain")},
        data={"brand_id": str(ws_id)},
        headers=admin_headers,
    )
    assert up_res.status_code == 200, up_res.text
    up_data = up_res.json()
    doc_id = int(up_data["id"])

    # Verify dashboard reflects 1 uploaded document and recent activity
    dash_res = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    dash_data = dash_res.json()
    assert dash_data["uploaded_documents"] == 1
    assert any("Guideline Uploaded" in a["action"] for a in dash_data["recent_activity"])

    # Create approved brand rule
    rule = BrandRule(
        workspace_id=ws_id,
        document_id=doc_id,
        title="Clarity in Product Copy",
        description="Write clear and professional descriptions.",
        category="Brand Voice",
        confidence=0.95,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Verify dashboard reflects approved rule
    dash_res2 = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert dash_res2.json()["total_approved_brand_rules"] == 1


def test_scenario_03_dashboard_tracks_content_reviews_and_violations(client, db):
    """Scenario 3: Audited copy updates total reviews, compliance score, violation breakdown and pending approvals."""
    env = setup_org_with_members(client, db, "Review Audit Org")
    ws_id = env["workspace"].id
    emp_headers = env["emp_headers"]

    # Provide an authoritative rule so audits can be run against it
    seed_rule = BrandRule(
        workspace_id=ws_id,
        title="Prohibit Unsubstantiated Guarantees",
        description='Never use "100% guarantee" in marketing copy.',
        category="Content Restrictions",
        confidence=0.99,
        approval_status="approved",
    )
    db.add(seed_rule)
    db.commit()

    # Scan content that triggers findings
    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Marketing Flyer",
            "content": "Our solution is the single best tool with 100% guarantee.",
            "contentType": "Advertisement",
            "channel": "Social",
        },
        headers=emp_headers,
    )
    assert scan_res.status_code == 200
    rev_id = int(scan_res.json()["id"])

    # Check dashboard
    dash_res = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=emp_headers)
    dash_data = dash_res.json()
    assert dash_data["total_reviews"] == 1
    assert dash_data["has_reviews"] is True
    assert dash_data["average_compliance_score"] < 100.0
    assert len(dash_data["recent_reviews"]) == 1
    assert len(dash_data["violations_by_category"]) >= 1

    # Request approval -> pending approvals increments
    req_res = client.post(
        f"/api/v1/reviews/{rev_id}/request-approval",
        json={"comment": "Please review"},
        headers=emp_headers,
    )
    assert req_res.status_code == 201

    dash_res_pending = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=emp_headers)
    assert dash_res_pending.json()["pending_approvals"] == 1

    # Admin approves
    admin_headers = env["admin_headers"]
    appr_res = client.post(
        f"/api/v1/approvals/{rev_id}/approve",
        json={"comment": "Approved copy"},
        headers=admin_headers,
    )
    assert appr_res.status_code == 200

    dash_res_approved = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=admin_headers)
    assert dash_res_approved.json()["approved_reviews"] == 1
    assert dash_res_approved.json()["pending_approvals"] == 0


def test_scenario_04_tenant_isolation_prevents_dashboard_leakage(client, db):
    """Scenario 4: Two independent organisations do not cross-contaminate dashboard metrics or activity streams."""
    org_a = setup_org_with_members(client, db, "Alpha Corp")
    org_b = setup_org_with_members(client, db, "Beta Ltd")

    ws_a_id = org_a["workspace"].id
    ws_b_id = org_b["workspace"].id

    # Alpha performs activity
    client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_a_id),
            "title": "Alpha Copy",
            "content": "Alpha exclusive release is guaranteed best in industry.",
            "contentType": "Social media",
            "channel": "Social",
        },
        headers=org_a["emp_headers"],
    )

    # Beta dashboard must still be completely empty
    res_b = client.get(f"/api/v1/workspaces/{ws_b_id}/dashboard", headers=org_b["admin_headers"])
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["total_reviews"] == 0
    assert data_b["has_reviews"] is False
    assert len(data_b["recent_reviews"]) == 0
    assert len(data_b["recent_activity"]) == 0

    # Cross-tenant access attempt: Alpha user attempting to read Beta dashboard
    forbidden_res = client.get(f"/api/v1/workspaces/{ws_b_id}/dashboard", headers=org_a["admin_headers"])
    assert forbidden_res.status_code == 403
