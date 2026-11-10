def test_approvals_workflow_and_dashboard(client, auth_headers):
    # 1. Create Workspace
    ws_resp = client.post("/api/workspaces", json={"name": "Dashboard WS"}, headers=auth_headers)
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Add guideline & approved rule
    doc_resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines",
        json={
            "filename": "security_policy.txt",
            "file_path": "/uploads/security_policy.txt",
            "extracted_text": "Never mention unverified zero-day vulnerabilities in public marketing.",
            "status": "extracted",
        },
        headers=auth_headers,
    )
    doc_id = doc_resp.json()["id"]

    rule_resp = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={
            "document_id": doc_id,
            "title": "Zero-day Disclosures",
            "description": "Restricted terminology: 'unverified' vulnerabilities must never be cited.",
            "category": "Restricted terminology",
            "source_reference": "Sec 2",
            "confidence": 0.95,
            "approval_status": "approved",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    # 3. Submit Content Review
    review_resp = client.post(
        f"/api/workspaces/{ws_id}/reviews",
        json={
            "title": "Spring Product Announcement",
            "content": "Our solution protects against unverified threats in real-time.",
            "content_type": "blog",
        },
        headers=auth_headers,
    )
    assert review_resp.status_code == 201
    review = review_resp.json()
    review_id = review["id"]

    # 4. Request Review Approval via POST /api/reviews/{id}/request-approval
    req_resp = client.post(
        f"/api/reviews/{review_id}/request-approval",
        json={"comment": "Ready for security team review"},
        headers=auth_headers,
    )
    assert req_resp.status_code == 201
    approval = req_resp.json()
    approval_id = approval["id"]
    assert approval["status"] == "pending"

    # 5. List approvals for workspace
    list_appr_resp = client.get(f"/api/workspaces/{ws_id}/approvals", headers=auth_headers)
    assert list_appr_resp.status_code == 200
    assert len(list_appr_resp.json()) == 1

    # 6. Check single approval details
    get_appr_resp = client.get(f"/api/approvals/{approval_id}", headers=auth_headers)
    assert get_appr_resp.status_code == 200
    assert get_appr_resp.json()["id"] == approval_id

    # 7. Approve via POST /api/approvals/{id}/approve
    approve_resp = client.post(f"/api/approvals/{approval_id}/approve", headers=auth_headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # Verifying item cannot be approved twice
    duplicate_resp = client.post(f"/api/approvals/{approval_id}/approve", headers=auth_headers)
    assert duplicate_resp.status_code == 400

    # 8. Check review status transitioned to approved
    rev_check = client.get(f"/api/reviews/{review_id}", headers=auth_headers).json()
    assert rev_check["status"] == "approved"

    # 9. Verify activity timeline
    act_resp = client.get(f"/api/reviews/{review_id}/activity", headers=auth_headers)
    assert act_resp.status_code == 200
    activities = act_resp.json()
    assert len(activities) >= 2  # Audit completed, Approval requested, Review approved

    # 10. Verify Dashboard Metrics
    dash_resp = client.get(f"/api/workspaces/{ws_id}/dashboard", headers=auth_headers)
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total_reviews"] == 1
    assert dash_data["approved_reviews"] == 1
    assert dash_data["total_approved_brand_rules"] == 1
    assert len(dash_data["recent_reviews"]) == 1
    assert len(dash_data["recent_activity"]) >= 1

    # 11. Test Review Search and Pagination
    search_resp = client.get(f"/api/workspaces/{ws_id}/reviews?search=Spring", headers=auth_headers)
    assert search_resp.status_code == 200
    assert search_resp.json()["total"] == 1

    search_empty = client.get(f"/api/workspaces/{ws_id}/reviews?search=NonExistent", headers=auth_headers)
    assert search_empty.status_code == 200
    assert search_empty.json()["total"] == 0
