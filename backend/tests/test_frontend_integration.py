def test_frontend_bridge_lifecycle(client, auth_headers):
    # 1. Verify User Profile & Auth
    me_resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user_data = me_resp.json()
    assert user_data["email"] == "sarah.chen@novapay.io"

    # 2. List Brands
    brands_resp = client.get("/api/v1/brands", headers=auth_headers)
    assert brands_resp.status_code == 200
    brands = brands_resp.json()
    assert len(brands) >= 1
    brand_id = brands[0]["id"]

    # 3. Create Approved Brand Rule via Frontend Endpoint
    rule_payload = {
        "title": "Strict Zero-Guarantee Policy",
        "description": "Never use the word 'guaranteed' in customer promotional messaging.",
        "category": "Claims & Restrictions",
        "sourcePage": "Sec 4.2",
    }
    create_rule_resp = client.post(
        f"/api/v1/guidelines/rules?brand_id={brand_id}",
        json=rule_payload,
        headers=auth_headers,
    )
    assert create_rule_resp.status_code == 200
    rule = create_rule_resp.json()
    assert rule["title"] == "Strict Zero-Guarantee Policy"

    # 4. Fetch Approved Rules
    list_rules_resp = client.get(f"/api/v1/guidelines/rules?brand_id={brand_id}", headers=auth_headers)
    assert list_rules_resp.status_code == 200
    assert any(r["title"] == "Strict Zero-Guarantee Policy" for r in list_rules_resp.json())

    # 5. Run Live Compliance Review Scan via POST /api/v1/reviews/scan
    scan_payload = {
        "title": "Q4 High-Yield Savings Promo",
        "content": "Get guaranteed 15% APY without any waiting or verification checks.",
        "contentType": "Social media",
        "channel": "Social",
        "strictness": "strict",
    }
    scan_resp = client.post(
        f"/api/v1/reviews/scan?brand_id={brand_id}",
        json=scan_payload,
        headers=auth_headers,
    )
    assert scan_resp.status_code == 200
    scan_data = scan_resp.json()
    review_id = scan_data["id"]
    assert scan_data["overallScore"] < 100
    assert len(scan_data["findings"]) >= 1
    assert any("guaranteed" in f["originalText"].lower() for f in scan_data["findings"])

    # 6. Request Approval for the Review
    req_resp = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": "Tier 2 sign-off requested"},
        headers=auth_headers,
    )
    assert req_resp.status_code == 201

    # 7. Check Pending Approvals Queue
    queue_resp = client.get(f"/api/v1/approvals/pending?brand_id={brand_id}", headers=auth_headers)
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    assert any(q["reviewId"] == review_id for q in queue)

    # 8. Approve the Content
    appr_resp = client.post(
        f"/api/v1/approvals/{review_id}/approve",
        json={"comment": "Approved after manual risk assessment"},
        headers=auth_headers,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["success"] is True

    # 9. Verify in History Ledger
    hist_resp = client.get(f"/api/v1/history?brand_id={brand_id}", headers=auth_headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    matching_hist = next((h for h in history if h["id"] == review_id), None)
    assert matching_hist is not None
    assert matching_hist["approvalStatus"] == "approved"

    # 10. Verify Live Telemetry
    telem_resp = client.get(f"/api/v1/brands/{brand_id}/telemetry", headers=auth_headers)
    assert telem_resp.status_code == 200
    telem = telem_resp.json()
    assert telem["contentReviewedCount"] >= 1
    assert telem["activeRulesCount"] >= 1
