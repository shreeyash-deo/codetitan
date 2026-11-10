"""
Regression tests for automatic guideline rule extraction pipeline,
structural fallback, candidate persistence, re-extraction, and rule approval.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.guideline import GuidelineDocument
from app.models.rule import BrandRule
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service
from app.services.rule_service import rule_service
from app.services.ai.ai_service import ai_service
from app.core.security import create_access_token


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def extraction_fixture(db: Session):
    admin = auth_service.create_user(
        db,
        UserCreate(name="Extraction Admin", email="extract_admin@example.com", password="Password123!"),
    )
    ws = workspace_service.create_workspace(db, name="Extraction Test WS", creator_id=admin.id)
    return {
        "admin": admin,
        "ws": ws,
        "headers": _headers_for(admin),
    }


def test_automatic_extraction_on_document_upload(client: TestClient, extraction_fixture, db: Session):
    """Test that document upload automatically initiates rule extraction and persists pending candidates."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    doc_content = (
        "NovaPay Global Brand Standards\n"
        "2.1 Required Brand Voice\n"
        "All communications must maintain a professional and institutional voice.\n\n"
        "4.1 Guaranteed Financial Returns\n"
        "Rule ID: NP-COMP-001\n"
        "Severity: Critical\n"
        "Marketing content must never guarantee financial returns or profits.\n\n"
        "5.1 Financial Risk Disclaimer\n"
        "Rule ID: NP-DISC-001\n"
        "Severity: High\n"
        "Content discussing investments must include: All financial decisions involve risk."
    )

    files = {
        "file": ("brand_rules.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "brand_rules.txt"
    assert data["status"] == "extracted"
    assert data["extractedCandidatesCount"] >= 3

    # Verify pending candidates are in database
    candidates = rule_service.list_rules(db=db, workspace_id=ws.id, approval_status="pending")
    assert len(candidates) >= 3

    titles = [c.title for c in candidates]
    assert any("guarantee" in t.lower() or "return" in t.lower() for t in titles)
    assert any("disclaimer" in t.lower() for t in titles)


def test_re_extract_document_endpoint(client: TestClient, extraction_fixture, db: Session):
    """Test re-extracting an existing document without re-uploading."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    # Create document directly
    doc = GuidelineDocument(
        workspace_id=ws.id,
        filename="policy_handbook.txt",
        file_path="mock/path/policy.txt",
        extracted_text=(
            "4.2 Risk-Free Claims\n"
            "Rule ID: NP-COMP-002\n"
            "Severity: Critical\n"
            "Do not describe investments as 100% risk-free or completely safe.\n\n"
            "4.3 Unrealistic Wealth Promises\n"
            "Rule ID: NP-COMP-003\n"
            "Severity: High\n"
            "Do not promise to make users rich overnight."
        ),
        status="extracted",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    res = client.post(
        f"/api/v1/guidelines/documents/{doc.id}/re-extract?brand_id={ws.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["extractedCandidatesCount"] >= 2
    assert data["status"] == "extracted"

    # Re-extracting again should not create duplicate candidate rules
    res_repeat = client.post(
        f"/api/v1/guidelines/documents/{doc.id}/re-extract?brand_id={ws.id}",
        headers=headers,
    )
    assert res_repeat.status_code == 200
    assert res_repeat.json()["extractedCandidatesCount"] == 0  # Deduplicated


def test_candidate_approval_and_compliance_availability(client: TestClient, extraction_fixture, db: Session):
    """Test candidate approval makes rules authoritative and available to Compliance Studio."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    rule = BrandRule(
        workspace_id=ws.id,
        title="Prohibit Speculative Terms",
        description="Never use get-rich-quick terminology in product copy.",
        category="Brand Voice",
        approval_status="pending",
        confidence=0.95,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    # Approve candidate via API
    res = client.post(f"/api/v1/guidelines/candidates/{rule.id}/approve", headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Prohibit Speculative Terms"

    # Verify rule is now in approved list
    approved_res = client.get(f"/api/v1/guidelines/rules?brand_id={ws.id}", headers=headers)
    assert approved_res.status_code == 200
    approved_titles = [r["title"] for r in approved_res.json()]
    assert "Prohibit Speculative Terms" in approved_titles


def test_empty_document_extraction_rejection(client: TestClient, extraction_fixture):
    """Empty document should be marked empty and not produce silent phantom rules."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    files = {
        "file": ("empty_manual.txt", io.BytesIO(b"   \n  \t  "), "text/plain")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "empty"
    assert data["extractedCandidatesCount"] == 0


def test_valid_docx_extraction(client: TestClient, extraction_fixture, db: Session):
    """Test uploading a valid DOCX document extracts clean text and candidate brand rules."""
    import docx
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    doc = docx.Document()
    doc.add_heading("NovaPay Global DOCX Brand Manual", 0)
    doc.add_paragraph("2.1 Required Brand Voice\nAll marketing collateral must use clear and precise wording.")
    doc.add_paragraph("4.1 Guaranteed Financial Returns\nRule ID: NP-COMP-010\nSeverity: Critical\nDo not guarantee financial returns under any circumstances.")

    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)

    files = {
        "file": ("guidelines.docx", docx_buffer, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    }
    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "DOCX"
    assert data["status"] == "extracted"
    assert data["extractedCandidatesCount"] >= 1


def test_valid_pdf_extraction(client: TestClient, extraction_fixture, db: Session):
    """Test uploading a valid PDF document extracts clean text and candidate brand rules."""
    import fitz
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    pdf_doc = fitz.open()
    page = pdf_doc.new_page()
    page.insert_text(
        fitz.Point(50, 50),
        "NovaPay PDF Standards\nRule ID: NP-PDF-001\nSeverity: Critical\nAll partners must display the registered trademark symbol.\n\n5.1 Financial Risk Disclaimer\nRule ID: NP-DISC-005\nSeverity: High\nAlways state that investments carry risk.",
    )
    pdf_buffer = io.BytesIO(pdf_doc.write())
    pdf_doc.close()

    files = {
        "file": ("standards.pdf", pdf_buffer, "application/pdf")
    }
    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "PDF"
    assert data["status"] == "extracted"
    assert data["extractedCandidatesCount"] >= 1


def test_unreadable_document_text_failure(client: TestClient, extraction_fixture, db: Session):
    """Corrupted or unreadable files must report text_failed status with actionable error details."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    corrupt_bytes = b"CORRUPTED_PDF_HEADER_NOT_A_VALID_DOCUMENT_STREAM\x00\xff\xfe"
    files = {
        "file": ("corrupted_guidelines.pdf", io.BytesIO(corrupt_bytes), "application/pdf")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "text_failed"
    assert data["extractedCandidatesCount"] == 0
    assert "Text extraction failed" in data.get("error", "")

    # Confirm in DB
    doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == int(data["id"])).first()
    assert doc is not None
    assert doc.status == "text_failed"


def test_unsupported_file_types_rejected(client: TestClient, extraction_fixture):
    """Unsupported file types must be rejected with HTTP 400 Bad Request."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    files = {
        "file": ("executable.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")
    }
    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 400
    assert "Unsupported file format" in res.json()["detail"]


def test_ai_provider_failure_preserves_extracted_text(client: TestClient, extraction_fixture, db: Session, monkeypatch):
    """When AI provider extraction fails, the document text must be preserved and status set to ai_failed."""
    from app.services.ai.ai_service import ai_service
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    def mock_extract_failure(text):
        raise RuntimeError("Gemini API quota exhausted (HTTP 429)")

    monkeypatch.setattr(ai_service, "extract_rules_from_text", mock_extract_failure)

    doc_text = "5.1 Mandatory Risk Disclaimer\nRule ID: NP-DISC-099\nSeverity: Critical\nRisk disclosure required."
    files = {
        "file": ("disclaimer_guidelines.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ai_failed"
    assert data["extractedCandidatesCount"] == 0
    assert "AI rule extraction failed" in data.get("error", "")

    # Crucial check: document text is preserved in DB!
    doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == int(data["id"])).first()
    assert doc is not None
    assert doc.status == "ai_failed"
    assert "Rule ID: NP-DISC-099" in doc.extracted_text


def test_successful_extraction_zero_candidates(client: TestClient, extraction_fixture, db: Session, monkeypatch):
    """Document containing no rule patterns produces no_candidates status without phantom rules."""
    from app.services.ai.ai_service import ai_service
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    # AI returns empty list
    monkeypatch.setattr(ai_service, "extract_rules_from_text", lambda text: [])

    doc_text = "General company history and milestones from 2018 to 2024 without any governance policies."
    files = {
        "file": ("company_history.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "no_candidates"
    assert data["extractedCandidatesCount"] == 0
    assert "zero governance rules" in data.get("message", "").lower()


def test_duplicate_only_extraction_outcome(client: TestClient, extraction_fixture, db: Session, monkeypatch):
    """Extracting a document whose rules already exist sets status to duplicate and reports duplicateCount."""
    from app.services.ai.ai_service import ai_service
    from app.schemas.rule import ExtractedRuleCandidate
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    # Pre-seed approved rule with identical title
    rule = BrandRule(
        workspace_id=ws.id,
        title="Required Professional Brand Voice",
        description="Existing approved rule.",
        category="Brand voice and tone",
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Mock extraction returning duplicate candidate
    monkeypatch.setattr(
        ai_service,
        "extract_rules_from_text",
        lambda text: [
            ExtractedRuleCandidate(
                title="Required Professional Brand Voice",
                description="Duplicate description.",
                category="Brand voice and tone",
                source_reference="Section 2.1",
                confidence=0.95,
                subCategory="Voice & Tone",
                severity="high",
                enforcement_level="Strict",
            )
        ],
    )

    doc_content = (
        "NovaPay Guidelines\n"
        "2.1 Required Brand Voice\n"
        "All communications must maintain a professional and institutional voice."
    )
    files = {
        "file": ("duplicate_voice.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")
    }

    res = client.post(
        f"/api/v1/guidelines/documents/upload?brand_id={ws.id}",
        files=files,
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "duplicate"
    assert data["extractedCandidatesCount"] == 0
    assert data.get("duplicateCount", 0) >= 1


def test_retry_after_failed_extraction(client: TestClient, extraction_fixture, db: Session):
    """Retrying a document whose previous extraction failed successfully extracts candidates using preserved text."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    doc_text = (
        "NovaPay Guidelines Manual\n"
        "Rule ID: NP-RETRY-001\n"
        "Severity: Critical\n"
        "Partners must not modify the brand crest color palette."
    )
    # Create document directly in ai_failed status with preserved text
    doc = GuidelineDocument(
        workspace_id=ws.id,
        filename="retry_test_doc.txt",
        file_path="mock/retry_test_doc.txt",
        extracted_text=doc_text,
        status="ai_failed",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Admin calls re-extract
    res = client.post(
        f"/api/v1/guidelines/documents/{doc.id}/re-extract?brand_id={ws.id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "extracted"
    assert data["extractedCandidatesCount"] >= 1

    # Verify DB status updated
    db.refresh(doc)
    assert doc.status == "extracted"


def test_approved_rules_preserved_during_retry(client: TestClient, extraction_fixture, db: Session):
    """Existing approved rules must be preserved and never overwritten or deleted when re-extracting."""
    ws = extraction_fixture["ws"]
    headers = extraction_fixture["headers"]

    # Pre-existing approved rule
    approved_rule = BrandRule(
        workspace_id=ws.id,
        title="Authoritative Brand Primary Color",
        description="Primary color must remain #0A2540.",
        category="Visual Identity",
        approval_status="approved",
    )
    db.add(approved_rule)
    db.commit()
    db.refresh(approved_rule)
    orig_id = approved_rule.id

    doc = GuidelineDocument(
        workspace_id=ws.id,
        filename="identity_update.txt",
        file_path="mock/identity_update.txt",
        extracted_text="Rule ID: NP-ID-002\nSeverity: High\nSecondary accent must be coral.",
        status="extracted",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Re-extract
    res = client.post(
        f"/api/v1/guidelines/documents/{doc.id}/re-extract?brand_id={ws.id}",
        headers=headers,
    )
    assert res.status_code == 200

    # Verify existing approved rule is untouched
    db.refresh(approved_rule)
    assert approved_rule.id == orig_id
    assert approved_rule.approval_status == "approved"
    assert approved_rule.title == "Authoritative Brand Primary Color"
