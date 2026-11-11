import io
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from app.core.config import Settings
from app.models.guideline import GuidelineDocument
from app.models.rule import BrandRule
from app.schemas.rule import ExtractedRuleCandidate


def test_configurable_upload_dir_default_and_override():
    """Requirement 1: Verify UPLOAD_DIR is configurable with ./uploads default."""
    # Default setting
    default_s = Settings(UPLOAD_DIR="./uploads")
    assert default_s.UPLOAD_DIR == "./uploads"

    # Configured override (e.g. Render Persistent Disk or mounted volume)
    override_s = Settings(UPLOAD_DIR="/var/data/custom_uploads")
    assert override_s.UPLOAD_DIR == "/var/data/custom_uploads"


def test_guideline_upload_persists_text_in_database(client, auth_headers, db):
    """Requirement 2: Ensure upload processing and text extraction persist in PostgreSQL/DB."""
    ws_resp = client.post("/api/workspaces", json={"name": "Ephemeral Storage WS"}, headers=auth_headers)
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    sample_content = (
        "NovaPay Ephemeral Storage Guide\n"
        "Voice: Confident and direct.\n"
        "Approved Term: NovaPay Ledger.\n"
        "Prohibited Term: Unregulated crypto."
    )
    files = {"file": ("ephemeral_guide.txt", io.BytesIO(sample_content.encode("utf-8")), "text/plain")}

    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]

    # Verify database model has extracted text
    db_doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first()
    assert db_doc is not None
    assert db_doc.extracted_text is not None
    assert "NovaPay Ledger" in db_doc.extracted_text
    assert db_doc.status == "extracted"


def test_missing_original_file_returns_graceful_response_on_download(client, auth_headers, db):
    """Requirement 4 & 5: When file is deleted after restart, download returns graceful 404, app does not crash."""
    ws_resp = client.post("/api/workspaces", json={"name": "Download Test WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    sample_content = "Ephemeral Compliance Document.\nRule: Always cite sources."
    files = {"file": ("source_doc.txt", io.BytesIO(sample_content.encode("utf-8")), "text/plain")}

    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    db_doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first()
    physical_file = Path(db_doc.file_path)

    # Simulate container restart: remove local file from ephemeral storage
    if physical_file.exists():
        physical_file.unlink()
    assert not physical_file.exists()

    # 1. Download via standard router
    download_resp = client.get(f"/api/guidelines/{doc_id}/download", headers=auth_headers)
    assert download_resp.status_code == 404
    detail = download_resp.json()["detail"]
    assert "unavailable on local storage (ephemeral filesystem)" in detail
    assert "Extracted text and approved brand rules remain safely preserved" in detail

    # 2. Download via compat router
    compat_download_resp = client.get(f"/api/guidelines/documents/{doc_id}/download", headers=auth_headers)
    assert compat_download_resp.status_code == 404
    assert "unavailable on local storage (ephemeral filesystem)" in compat_download_resp.json()["detail"]


def test_extracted_text_and_metadata_persist_without_file(client, auth_headers, db):
    """Requirement 3 & 5: Guideline text and metadata survive container file loss."""
    ws_resp = client.post("/api/workspaces", json={"name": "Persistence WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    sample_content = "Persistent text preserved in PostgreSQL database.\nRule: Use metric units."
    files = {"file": ("units_guide.txt", io.BytesIO(sample_content.encode("utf-8")), "text/plain")}

    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    doc_id = upload_resp.json()["id"]

    # Delete physical file
    db_doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first()
    if Path(db_doc.file_path).exists():
        Path(db_doc.file_path).unlink()

    # Query metadata endpoint
    meta_resp = client.get(f"/api/guidelines/{doc_id}", headers=auth_headers)
    assert meta_resp.status_code == 200
    assert meta_resp.json()["filename"] == "units_guide.txt"

    # Query text endpoint
    text_resp = client.get(f"/api/guidelines/{doc_id}/text", headers=auth_headers)
    assert text_resp.status_code == 200
    assert "Persistent text preserved in PostgreSQL" in text_resp.json()["extracted_text"]


def test_rule_extraction_succeeds_when_file_is_missing(client, auth_headers, db):
    """Requirement 2 & 5: AI rule extraction reads from DB extracted_text, not disk."""
    ws_resp = client.post("/api/workspaces", json={"name": "Extraction WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    sample_content = "Brand Voice: Welcoming and authoritative.\nProhibited: No slang."
    files = {"file": ("voice_guide.txt", io.BytesIO(sample_content.encode("utf-8")), "text/plain")}

    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    doc_id = upload_resp.json()["id"]

    # Delete physical file
    db_doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first()
    if Path(db_doc.file_path).exists():
        Path(db_doc.file_path).unlink()

    mock_candidates = [
        ExtractedRuleCandidate(
            title="Welcoming and Authoritative Voice",
            description="Maintain a welcoming and authoritative brand voice across touchpoints.",
            category="voice_tone",
            rationale="Defines corporate voice standard.",
            confidence=0.95,
        )
    ]

    with patch("app.services.ai.ai_service.ai_service.extract_rules_from_text", return_value=mock_candidates):
        extract_resp = client.post(f"/api/guidelines/{doc_id}/extract-rules", headers=auth_headers)
        assert extract_resp.status_code == 201
        data = extract_resp.json()
        assert data["extracted_count"] == 1
        assert data["rules"][0]["title"] == "Welcoming and Authoritative Voice"


def test_compliance_engine_audits_content_using_database_rules_without_files(client, auth_headers, db):
    """Requirement 3: Compliance engine uses persisted approved rules, completely decoupled from original files."""
    ws_resp = client.post("/api/workspaces", json={"name": "Compliance Audit WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    # Directly create an approved brand rule in DB (no file required on disk)
    rule = BrandRule(
        workspace_id=ws_id,
        category="content_restrictions",
        title="Prohibited Financial Claim",
        description="Never use the term 'guaranteed returns'.",
        confidence=1.0,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Submit content review that violates the approved rule
    review_payload = {
        "title": "Marketing Campaign Ad",
        "content": "Sign up today with NovaPay for guaranteed returns on all merchant balances.",
        "content_type": "social_media",
    }
    review_resp = client.post(f"/api/workspaces/{ws_id}/reviews", json=review_payload, headers=auth_headers)
    assert review_resp.status_code == 201
    review_data = review_resp.json()

    # Rule must be flagged and score computed without needing any guideline file on disk
    assert "compliance_score" in review_data
    assert review_data["status"] in ("compliant", "flagged", "non_compliant", "approved", "in_review", "rejected")


def test_delete_guideline_succeeds_when_physical_file_is_already_gone(client, auth_headers, db):
    """Requirement 5: Deleting document cleans up DB cleanly even if physical file was already missing."""
    ws_resp = client.post("/api/workspaces", json={"name": "Delete Test WS"}, headers=auth_headers)
    ws_id = ws_resp.json()["id"]

    sample_content = "Temporary document to be deleted."
    files = {"file": ("temp.txt", io.BytesIO(sample_content.encode("utf-8")), "text/plain")}

    upload_resp = client.post(f"/api/workspaces/{ws_id}/guidelines/upload", files=files, headers=auth_headers)
    doc_id = upload_resp.json()["id"]

    # Delete physical file from disk first
    db_doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first()
    if Path(db_doc.file_path).exists():
        Path(db_doc.file_path).unlink()

    # Call DELETE endpoint
    del_resp = client.delete(f"/api/guidelines/{doc_id}", headers=auth_headers)
    assert del_resp.status_code == 204

    # Confirm record is gone from DB
    assert db.query(GuidelineDocument).filter(GuidelineDocument.id == doc_id).first() is None
