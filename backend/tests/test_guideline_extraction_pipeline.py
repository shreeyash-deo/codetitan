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
