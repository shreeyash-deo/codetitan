def test_guideline_and_rule_lifecycle(client, auth_headers):
    # 1. Create Workspace
    ws_resp = client.post("/api/workspaces", json={"name": "Governance Test WS"}, headers=auth_headers)
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Create Guideline Document record
    doc_payload = {
        "filename": "brand_voice_guide_2026.pdf",
        "file_path": "/uploads/brand_voice_guide_2026.pdf",
        "extracted_text": "Always maintain an authoritative and respectful tone.",
        "status": "extracted",
    }
    doc_resp = client.post(f"/api/workspaces/{ws_id}/guidelines", json=doc_payload, headers=auth_headers)
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    # 3. Create Brand Rule referencing the document
    rule_payload = {
        "document_id": doc_id,
        "title": "Authoritative Tone Requirement",
        "description": "Marketing copy must avoid overly casual slang.",
        "category": "Brand Voice",
        "source_reference": "Section 2.1, Page 4",
        "confidence": 0.95,
        "approval_status": "pending",
    }
    rule_resp = client.post(f"/api/workspaces/{ws_id}/rules", json=rule_payload, headers=auth_headers)
    assert rule_resp.status_code == 201
    rule_id = rule_resp.json()["id"]
    assert rule_resp.json()["approval_status"] == "pending"

    # 4. Update Rule to Approved
    patch_resp = client.patch(
        f"/api/workspaces/{ws_id}/rules/{rule_id}",
        json={"approval_status": "approved"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["approval_status"] == "approved"

    # 5. List rules filtered by status
    list_rules_resp = client.get(f"/api/workspaces/{ws_id}/rules?approval_status=approved", headers=auth_headers)
    assert list_rules_resp.status_code == 200
    assert len(list_rules_resp.json()) == 1


def test_review_and_approval_flow(client, auth_headers):
    # 1. Create Workspace
    ws_resp = client.post("/api/workspaces", json={"name": "Audit Test WS"}, headers=auth_headers)
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Create Approved Rule for this workspace so compliance engine has active guidelines
    doc_resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines",
        json={
            "filename": "compliance_guide.txt",
            "file_path": "/uploads/compliance_guide.txt",
            "extracted_text": "Restricted terminology: Do not use 'guaranteed' in financial promotions.",
            "status": "extracted",
        },
        headers=auth_headers,
    )
    doc_id = doc_resp.json()["id"]

    rule_resp = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={
            "document_id": doc_id,
            "title": "Prohibited Guarantee Terminology",
            "description": "Restricted terminology: 'guaranteed' is strictly prohibited.",
            "category": "Restricted terminology",
            "source_reference": "Compliance Section 4.1",
            "confidence": 0.99,
            "approval_status": "approved",
        },
        headers=auth_headers,
    )
    assert rule_resp.status_code == 201

    # 3. Submit Content Review
    review_payload = {
        "title": "Q4 Social Campaign Headline",
        "content": "Instant approval guaranteed for all fintech users without verification.",
        "content_type": "social_media",
    }
    review_resp = client.post(f"/api/workspaces/{ws_id}/reviews", json=review_payload, headers=auth_headers)
    assert review_resp.status_code == 201
    review_data = review_resp.json()
    review_id = review_data["id"]
    assert review_data["compliance_score"] < 100
    assert len(review_data["findings"]) >= 1

    # 4. Create Approval Request
    approval_payload = {
        "review_id": review_id,
        "comment": "Requesting tier 2 compliance review for guarantee claim.",
    }
    appr_resp = client.post(f"/api/workspaces/{ws_id}/approvals", json=approval_payload, headers=auth_headers)
    assert appr_resp.status_code == 201
    approval_id = appr_resp.json()["id"]

    # 5. Reviewer requests changes
    decision_resp = client.patch(
        f"/api/workspaces/{ws_id}/approvals/{approval_id}?decision_status=changes_requested&comment=Please+apply+statutory+qualification+clause",
        headers=auth_headers,
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "changes_requested"

    # 6. Check review status transitioned to needs_revision
    updated_rev = client.get(f"/api/workspaces/{ws_id}/reviews/{review_id}", headers=auth_headers).json()
    assert updated_rev["status"] == "needs_revision"
