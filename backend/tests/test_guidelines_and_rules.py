import io
from pathlib import Path
from unittest.mock import patch
from app.schemas.rule import ExtractedRuleCandidate
from app.services.auth_service import auth_service
from app.schemas.user import UserCreate
from app.core.security import create_access_token


def test_upload_txt_guideline_and_extract(client, auth_headers):
    # 1. Create workspace
    ws_resp = client.post("/api/workspaces", json={"name": "Text Document WS"}, headers=auth_headers)
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Upload sample TXT brand guideline
    sample_txt_content = (
        "NovaPay Brand Tone Guidelines\n"
        "Voice: Authoritative, transparent, and empathetic.\n"
        "Approved Term: Use 'Smart Ledger' instead of 'crypto database'.\n"
        "Prohibited Term: Never use 'guaranteed returns' in marketing copy."
    )
    files = {
        "file": ("novapay_tone.txt", io.BytesIO(sample_txt_content.encode("utf-8")), "text/plain")
    }

    upload_resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines/upload",
        files=files,
        headers=auth_headers,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["filename"] == "novapay_tone.txt"
    assert doc_data["status"] == "extracted"
    assert "Smart Ledger" in doc_data["extracted_text"]
    assert doc_data["workspace_id"] == ws_id


def test_upload_pdf_guideline_and_extract(client, auth_headers):
    import fitz

    # Create workspace
    ws_resp = client.post("/api/workspaces", json={"name": "PDF Document WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    # Generate a real PDF in-memory using PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "NovaPay Visual Identity Manual")
    page.insert_text((50, 100), "Primary Brand Color: Deep Navy #0B1220")
    page.insert_text((50, 120), "Clearspace Requirement: 24px padding around primary logo mark")
    pdf_bytes = doc.tobytes()
    doc.close()

    files = {
        "file": ("visual_identity.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    upload_resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines/upload",
        files=files,
        headers=auth_headers,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["status"] == "extracted"
    assert "Deep Navy #0B1220" in doc_data["extracted_text"]
    assert "--- Page 1 ---" in doc_data["extracted_text"]


def test_upload_docx_guideline_and_extract(client, auth_headers):
    from docx import Document

    ws_resp = client.post("/api/workspaces", json={"name": "DOCX Document WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    # Generate a real DOCX in-memory
    doc = Document()
    doc.add_heading("NovaPay Compliance & Legal Disclaimers", level=1)
    doc.add_paragraph("Mandatory Footer: Past performance is not indicative of future results.")
    docx_io = io.BytesIO()
    doc.save(docx_io)
    docx_io.seek(0)

    files = {
        "file": ("disclaimers.docx", docx_io, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }
    upload_resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines/upload",
        files=files,
        headers=auth_headers,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["status"] == "extracted"
    assert "Mandatory Footer: Past performance" in doc_data["extracted_text"]


def test_upload_invalid_file_extension_fails(client, auth_headers):
    ws_resp = client.post("/api/workspaces", json={"name": "Invalid File WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    files = {
        "file": ("malicious.exe", io.BytesIO(b"dangerous bytes"), "application/octet-stream")
    }
    resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines/upload",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json()["detail"]


def test_upload_oversized_file_fails(client, auth_headers, monkeypatch):
    from app.core.config import settings

    # Temporarily set max upload size to 100 bytes for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 100)

    ws_resp = client.post("/api/workspaces", json={"name": "Oversized WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    big_content = b"A" * 500  # 500 bytes > 100 bytes
    files = {
        "file": ("huge_guidelines.txt", io.BytesIO(big_content), "text/plain")
    }
    resp = client.post(
        f"/api/workspaces/{ws_id}/guidelines/upload",
        files=files,
        headers=auth_headers,
    )
    assert resp.status_code == 413
    assert "exceeds" in resp.json()["detail"]


def test_guideline_management_endpoints(client, auth_headers):
    # Setup workspace & upload document
    ws_resp = client.post("/api/workspaces", json={"name": "Doc Management WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    files = {
        "file": ("manual.txt", io.BytesIO(b"Brand Voice: Respectful and clear."), "text/plain")
    }
    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    doc_id = upload_resp.json()["id"]
    file_path_on_disk = upload_resp.json()["file_path"]

    # 1. List workspace guidelines
    list_resp = client.get(f"/api/workspaces/{ws_id}/guidelines", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # 2. Get single guideline document
    get_resp = client.get(f"/api/guidelines/{doc_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["filename"] == "manual.txt"

    # 3. Get document text endpoint
    text_resp = client.get(f"/api/guidelines/{doc_id}/text", headers=auth_headers)
    assert text_resp.status_code == 200
    text_data = text_resp.json()
    assert text_data["extracted_text"] == "Brand Voice: Respectful and clear."
    assert text_data["character_count"] > 0

    # 4. Delete document
    del_resp = client.delete(f"/api/guidelines/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Verify document no longer exists
    get_after_del = client.get(f"/api/guidelines/{doc_id}", headers=auth_headers)
    assert get_after_del.status_code == 404
    # Verify file unlinked from disk
    assert not Path(file_path_on_disk).exists()


def test_full_ai_rule_extraction_and_governance_workflow(client, auth_headers):
    """
    Test complete lifecycle:
    Upload document -> Extract text -> Call AI extraction -> Receive candidate rules (pending)
    -> Edit candidate -> Approve candidate -> Verify rule is approved and appears in authoritative list.
    """
    # 1. Create Workspace
    ws_resp = client.post("/api/workspaces", json={"name": "End-to-End Governance WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    # 2. Upload Brand Guideline Document
    doc_text = (
        "NovaPay Brand Communication Standards\n"
        "1. Brand Voice: Confident, educational, and free of financial jargon.\n"
        "2. Restricted Words: Do not use 'free money' or 'risk-free liquidity'.\n"
        "3. Mandatory Claim: Always state 'FDIC insured through partner banking institutions'."
    )
    files = {
        "file": ("communication_standards.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")
    }
    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    doc_id = upload_resp.json()["id"]

    # 3. Trigger AI Rule Extraction (mocking the AI provider response to test the engine deterministically)
    mock_candidates = [
        ExtractedRuleCandidate(
            title="Educational Tone Requirement",
            description="All marketing and product copy must remain educational and devoid of complex financial jargon.",
            category="Brand voice and tone",
            source_reference="Section 1",
            confidence=0.96,
        ),
        ExtractedRuleCandidate(
            title="Prohibited Liquidity Claims",
            description="Strictly prohibit using 'free money' or 'risk-free liquidity' anywhere in collateral.",
            category="Restricted terminology",
            source_reference="Section 2",
            confidence=0.98,
        ),
    ]

    with patch("app.services.ai.ai_service.AIService.extract_rules_from_text", return_value=mock_candidates):
        extract_resp = client.post(f"/api/guidelines/{doc_id}/extract-rules", headers=auth_headers)
        assert extract_resp.status_code == 201
        extract_data = extract_resp.json()
        assert extract_data["document_id"] == doc_id
        assert extract_data["extracted_count"] == 2
        rules = extract_data["rules"]
        assert len(rules) == 2
        # Verify initial status is PENDING
        assert all(r["approval_status"] == "pending" for r in rules)

    candidate_rule_id = rules[0]["id"]

    # 4. Verify candidate rule is in pending queue
    pending_resp = client.get(f"/api/workspaces/{ws_id}/rules/pending", headers=auth_headers)
    assert pending_resp.status_code == 200
    pending_rules = pending_resp.json()
    assert len(pending_rules) == 2
    assert any(r["id"] == candidate_rule_id for r in pending_rules)

    # 5. Edit candidate rule prior to approval
    patch_resp = client.patch(
        f"/api/rules/{candidate_rule_id}",
        json={
            "title": "Educational Tone Requirement (Updated)",
            "description": "All customer-facing copy must be educational and avoid jargon. Approved for 2026.",
        },
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "Educational Tone Requirement (Updated)"

    # 6. Approve the candidate rule
    approve_resp = client.post(f"/api/rules/{candidate_rule_id}/approve", headers=auth_headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["approval_status"] == "approved"

    # 7. Reject the second candidate rule
    second_rule_id = rules[1]["id"]
    reject_resp = client.post(
        f"/api/rules/{second_rule_id}/reject?reason=Covered+by+statutory+banking+policy",
        headers=auth_headers,
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["approval_status"] == "rejected"

    # 8. Verify approved rules list contains only the approved rule
    approved_resp = client.get(f"/api/workspaces/{ws_id}/rules?approval_status=approved", headers=auth_headers)
    assert approved_resp.status_code == 200
    approved_list = approved_resp.json()
    assert len(approved_list) == 1
    assert approved_list[0]["id"] == candidate_rule_id
    assert approved_list[0]["approval_status"] == "approved"

    # 9. Verify pending list is now empty
    pending_after_resp = client.get(f"/api/workspaces/{ws_id}/rules/pending", headers=auth_headers)
    assert len(pending_after_resp.json()) == 0


def test_rule_deduplication(client, auth_headers):
    # Setup workspace & document
    ws_resp = client.post("/api/workspaces", json={"name": "Deduplication WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    files = {"file": ("doc.txt", io.BytesIO(b"Rules text"), "text/plain")}
    doc_id = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers).json()["id"]

    duplicate_candidates = [
        ExtractedRuleCandidate(title="Unique Rule A", description="Desc A", category="Brand voice and tone"),
        ExtractedRuleCandidate(title="Unique Rule A", description="Duplicate of Desc A", category="Brand voice and tone"),
    ]

    with patch("app.services.ai.ai_service.AIService.extract_rules_from_text", return_value=duplicate_candidates):
        extract_resp = client.post(f"/api/guidelines/{doc_id}/extract-rules", headers=auth_headers)
        assert extract_resp.status_code == 201
        # Only 1 unique rule should have been added
        assert extract_resp.json()["extracted_count"] == 1
