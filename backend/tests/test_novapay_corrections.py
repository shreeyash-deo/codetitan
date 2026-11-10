"""
Focused Verification of NovaPay Correction Workflow (Step 4 & Step 5)
Testing single correction application and batch correction application on the NovaPay marketing asset.
"""
import pytest
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.finding import Finding
from app.core.security import get_password_hash, create_access_token


NOVAPAY_CONTENT = (
    "Introducing NovaPay Global — the world's fastest payment platform, guaranteed to double your business revenue overnight!\n\n"
    "Our 100% risk-free payment solution eliminates every security threat and ensures zero transaction failures.\n\n"
    "With 10 million transactions per second and absolutely zero downtime, our platform guarantees instant settlements."
)


@pytest.fixture
def novapay_env(db: Session):
    ws = Workspace(name="NovaPay Global", org_id="ORG-NOVAPAY-01")
    db.add(ws)
    db.flush()

    emp = User(name="Nova Author", email="author@novapay.com", hashed_password=get_password_hash("pass"), role="User")
    db.add(emp)
    db.flush()

    mem = WorkspaceMember(workspace_id=ws.id, user_id=emp.id, role="Employee", status="approved")
    db.add(mem)
    db.flush()

    # Create approved rules targeting the forbidden claims
    rules = [
        BrandRule(
            workspace_id=ws.id,
            category="Claims & Performance",
            title="Prohibit Guaranteed Revenue",
            description="Content must not guarantee financial returns. Prohibited: double your business revenue overnight.",
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Risk & Indemnity",
            title="Prohibit Absolute Risk-Free Claims",
            description="Never describe services as 100% risk-free.",
            confidence=0.95,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Security Claims",
            title="Prohibit Absolute Security Claims",
            description="Avoid claiming to eliminate every security threat.",
            confidence=0.90,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Operational Performance",
            title="Prohibit Unsubstantiated Throughput",
            description="Avoid claiming 10 million transactions per second or zero transaction failures.",
            confidence=0.90,
            approval_status="approved",
        ),
        BrandRule(
            workspace_id=ws.id,
            category="Uptime Claims",
            title="Prohibit Zero Downtime",
            description="Never promise absolutely zero downtime or instant settlements without caveats.",
            confidence=0.90,
            approval_status="approved",
        ),
    ]
    db.add_all(rules)
    db.commit()

    token = create_access_token(subject=emp.id, extra_claims={"role": "Employee"})
    headers = {"Authorization": f"Bearer {token}"}

    return {"ws": ws, "emp": emp, "headers": headers}


def test_novapay_single_and_batch_correction_workflow(client: TestClient, db: Session, novapay_env):
    headers = novapay_env["headers"]
    ws_id = novapay_env["ws"].id

    # 1. Submit review
    res = client.post(
        f"/api/v1/workspaces/{ws_id}/reviews",
        json={
            "title": "NovaPay Q4 Campaign",
            "content": NOVAPAY_CONTENT,
            "content_type": "social_media",
        },
        headers=headers,
    )
    assert res.status_code == 201
    rev_data = res.json()
    review_id = rev_data["id"]
    initial_score = rev_data["compliance_score"]
    assert initial_score < 100

    # Ensure findings exist with suggested corrections
    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    assert len(findings) > 0

    # Populate realistic suggestions if any finding lacked one
    for f in findings:
        if not f.suggested_correction:
            if "risk-free" in f.excerpt.lower():
                f.suggested_correction = "risk-managed"
            elif "downtime" in f.excerpt.lower():
                f.suggested_correction = "99.99% targeted uptime"
            elif "revenue" in f.excerpt.lower():
                f.suggested_correction = "sustainably grow revenue"
            elif "security" in f.excerpt.lower():
                f.suggested_correction = "mitigates security threats"
            elif "settlements" in f.excerpt.lower():
                f.suggested_correction = "rapid settlements"
            elif "failures" in f.excerpt.lower():
                f.suggested_correction = "minimized transaction failures"
            else:
                f.suggested_correction = "industry-leading performance"
    db.commit()

    # Refresh findings
    findings = db.query(Finding).filter(Finding.review_id == review_id).all()
    first_finding = findings[0]
    initial_count = len(findings)

    # 2. Apply ONE correction first (Step 4 Requirement)
    apply_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/{first_finding.id}/apply",
        headers=headers,
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()

    # Contract Verification: Verify both 'content' and 'updated_content' exist
    assert "content" in apply_data and apply_data["content"] is not None
    assert "updated_content" in apply_data and apply_data["updated_content"] is not None
    assert apply_data["content"] == apply_data["updated_content"]
    assert "findings" in apply_data and apply_data["findings"] is not None
    assert apply_data["compliance_score"] >= initial_score
    assert apply_data["audit_status"] == "verified"
    assert apply_data["audited_content_hash"] == hashlib.sha256(apply_data["content"].strip().encode("utf-8")).hexdigest()

    # Verify original content preserved
    assert apply_data["original_content"] == NOVAPAY_CONTENT

    # Verify other findings remain intact
    updated_findings = apply_data["findings"]
    applied_f = next(f for f in updated_findings if f["id"] == first_finding.id)
    assert applied_f["status"] == "applied"
    open_findings = [f for f in updated_findings if f["status"] == "open"]
    assert len(open_findings) == initial_count - 1

    # 3. Test Batch Correction (Step 4 Requirement)
    batch_res = client.post(
        f"/api/v1/reviews/{review_id}/findings/batch-apply",
        headers=headers,
    )
    assert batch_res.status_code == 200
    batch_data = batch_res.json()

    # Contract Verification on Batch: Verify content, compliance_score, audit_status, hash
    assert "content" in batch_data and batch_data["content"] is not None
    assert "updated_content" in batch_data and batch_data["updated_content"] is not None
    assert batch_data["audit_status"] == "verified"
    assert batch_data["audited_content_hash"] == hashlib.sha256(batch_data["content"].strip().encode("utf-8")).hexdigest()
    assert batch_data["original_content"] == NOVAPAY_CONTENT
    assert batch_data["compliance_score"] > initial_score
