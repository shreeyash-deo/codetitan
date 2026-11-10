import os
import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.guideline import GuidelineDocument
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.finding import Finding
from app.models.approval import Approval
from app.models.activity import ReviewActivity

from app.services.workspace_service import workspace_service
from app.services.rule_service import rule_service
from app.services.review_service import review_service
from app.services.approval_service import approval_service
from app.services.dashboard_service import dashboard_service
from app.services.compliance.compliance_engine import compliance_engine, NoApprovedRulesError
from app.schemas.review import ContentReviewSubmission
from app.utils.extractor import extract_document_text

router = APIRouter(tags=["Frontend Bridge & Compatibility API"])


def get_target_workspace_id(db: Session, current_user: User, explicit_id: Optional[str] = None) -> int:
    """Helper to resolve target workspace from explicit param or user's active workspaces."""
    if explicit_id is not None and str(explicit_id).strip() != "":
        clean_id = str(explicit_id).strip()
        ws = None
        if clean_id.isdigit():
            ws = workspace_service.get_by_id(db, int(clean_id))
        if not ws:
            ws = workspace_service.get_by_org_id(db, clean_id)
        if not ws:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
        if not workspace_service.is_member(db, ws.id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not a member of this workspace",
            )
        return ws.id

    # If user belongs to exactly one workspace, use it
    workspaces = workspace_service.list_workspaces_for_user(db, current_user)
    if len(workspaces) == 1:
        return workspaces[0].id
    if len(workspaces) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambiguous organisation context. User belongs to multiple organisations; please specify brand_id.",
        )

    # If user has no workspace yet, create a default workspace
    default_ws = Workspace(name="NovaPay Global", org_id=workspace_service.generate_org_id(db))
    db.add(default_ws)
    db.commit()
    db.refresh(default_ws)

    member = WorkspaceMember(workspace_id=default_ws.id, user_id=current_user.id, role="Admin")
    db.add(member)
    db.commit()
    return default_ws.id


def verify_workspace_admin_in_compat(db: Session, workspace_id: int, user_id: int):
    member = workspace_service.get_member(db, workspace_id, user_id)
    if not member or member.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Required workspace role: Admin",
        )


def verify_workspace_reviewer_or_admin_in_compat(db: Session, workspace_id: int, user_id: int):
    member = workspace_service.get_member(db, workspace_id, user_id)
    if not member or member.role.lower() not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Required workspace role: Reviewer or Admin",
        )


# ============================================================================
# BRANDS ENDPOINTS (Maps Workspaces to Brand format)
# ============================================================================

@router.get("/brands", summary="List brands / workspaces")
def list_brands(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspaces = workspace_service.list_workspaces_for_user(db, current_user)
    if not workspaces:
        ws_id = get_target_workspace_id(db, current_user)
        workspaces = [workspace_service.get_by_id(db, ws_id)]

    results = []
    for w in workspaces:
        stats = dashboard_service.get_dashboard_stats(db, w.id)
        member = workspace_service.get_member(db, w.id, current_user.id)
        results.append({
            "id": str(w.id),
            "org_id": w.org_id,
            "orgId": w.org_id,
            "name": w.name,
            "slug": w.name.lower().replace(" ", "-"),
            "plan": "Enterprise",
            "role": member.role if member else "Employee",
            "complianceScore": int(stats.average_compliance_score),
            "activeRulesCount": stats.total_approved_brand_rules,
            "brandColor": "#0284c7",
            "createdAt": w.created_at.isoformat(),
        })
    return results


@router.get("/brands/{brand_id}", summary="Get brand by ID")
def get_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    w = workspace_service.get_by_id(db, ws_id)
    if not w:
        raise HTTPException(status_code=404, detail="Brand not found")
    stats = dashboard_service.get_dashboard_stats(db, w.id)
    member = workspace_service.get_member(db, w.id, current_user.id)
    return {
        "id": str(w.id),
        "org_id": w.org_id,
        "orgId": w.org_id,
        "name": w.name,
        "slug": w.name.lower().replace(" ", "-"),
        "plan": "Enterprise",
        "role": member.role if member else "Employee",
        "complianceScore": int(stats.average_compliance_score),
        "activeRulesCount": stats.total_approved_brand_rules,
        "brandColor": "#0284c7",
        "createdAt": w.created_at.isoformat(),
    }


@router.get("/brands/{brand_id}/telemetry", summary="Get brand telemetry")
def get_brand_telemetry(
    brand_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    stats = dashboard_service.get_dashboard_stats(db, ws_id)
    return {
        "overallScore": int(stats.average_compliance_score),
        "activeRulesCount": stats.total_approved_brand_rules,
        "contentReviewedCount": stats.total_reviews,
        "pendingApprovalsCount": stats.pending_approvals,
        "criticalIssuesCount": stats.critical_findings,
        "lastUpdated": datetime.now(timezone.utc).strftime("%b %d, %H:%M UTC"),
    }


# ============================================================================
# GUIDELINES & RULES ENDPOINTS (Frontend format compatibility)
# ============================================================================

def _map_rule_to_guideline(r: BrandRule, doc_map: Dict[int, GuidelineDocument]) -> Dict[str, Any]:
    doc = doc_map.get(r.document_id) if r.document_id else None
    cat = r.category or "Brand Voice"
    prefix_map = {
        "Brand Voice": "BV",
        "Terminology": "TM",
        "Brand Facts": "BF",
        "Claims & Restrictions": "CR",
        "Visual Identity": "VI",
    }
    prefix = prefix_map.get(cat, "RULE")
    return {
        "id": str(r.id),
        "code": f"{prefix}-{r.id:02d}",
        "category": cat,
        "subCategory": cat,
        "title": r.title,
        "description": r.description,
        "enforcementLevel": "Strict" if r.confidence >= 0.8 else "Advisory",
        "approvedExample": f"Recommended phrasing adhering to {r.title}",
        "prohibitedExample": f"Avoid statements violating {r.title}",
        "sourceDocument": doc.filename if doc else "Corporate Brand Guidelines",
        "sourcePage": r.source_reference or "Section 1",
        "lastUpdated": r.created_at.strftime("%b %d, %Y"),
        "updatedBy": "Brand Lead",
    }


def _map_rule_to_candidate(r: BrandRule, doc_map: Dict[int, GuidelineDocument]) -> Dict[str, Any]:
    doc = doc_map.get(r.document_id) if r.document_id else None
    cat = r.category or "Brand Voice"
    conf = int(r.confidence * 100) if r.confidence <= 1.0 else int(r.confidence)
    return {
        "id": str(r.id),
        "category": cat,
        "subCategory": cat,
        "title": r.title,
        "extractedText": r.description,
        "rationale": f"Extracted from source guideline citation: {r.source_reference or 'General Standards'}",
        "sourceDocument": doc.filename if doc else "Brand Manual",
        "sourceSection": r.source_reference or "Page 2",
        "confidence": conf,
        "dateExtracted": r.created_at.strftime("%b %d"),
        "suggestedEnforcement": "Strict" if conf >= 85 else "Advisory",
        "status": r.approval_status,
    }


@router.get("/guidelines/rules", summary="List approved brand guidelines")
def get_guidelines_rules(
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    rules = rule_service.list_rules(db=db, workspace_id=ws_id, approval_status="approved")
    docs = db.query(GuidelineDocument).filter(GuidelineDocument.workspace_id == ws_id).all()
    doc_map = {d.id: d for d in docs}
    return [_map_rule_to_guideline(r, doc_map) for r in rules]


@router.post("/guidelines/rules", summary="Create approved brand guideline")
def create_guidelines_rule(
    payload: Dict[str, Any] = Body(...),
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    verify_workspace_admin_in_compat(db, ws_id, current_user.id)
    rule = BrandRule(
        workspace_id=ws_id,
        title=payload.get("title", "New Brand Rule").strip(),
        description=payload.get("description", "").strip(),
        category=payload.get("category", "Brand Voice").strip(),
        source_reference=payload.get("sourcePage") or payload.get("sourceReference") or "Direct Policy",
        confidence=1.0,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _map_rule_to_guideline(rule, {})


@router.put("/guidelines/rules/{rule_id}", summary="Update approved brand guideline")
def update_guidelines_rule(
    rule_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID format")

    rule = rule_service.get_by_id(db, r_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    verify_workspace_admin_in_compat(db, rule.workspace_id, current_user.id)

    if "title" in payload:
        rule.title = payload["title"]
    if "description" in payload:
        rule.description = payload["description"]
    if "category" in payload:
        rule.category = payload["category"]
    if "sourcePage" in payload:
        rule.source_reference = payload["sourcePage"]

    db.commit()
    db.refresh(rule)
    return _map_rule_to_guideline(rule, {})


@router.delete("/guidelines/rules/{rule_id}", status_code=204, summary="Delete brand guideline")
def delete_guidelines_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(rule_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rule ID")

    rule = rule_service.get_by_id(db, r_id)
    if rule:
        verify_workspace_admin_in_compat(db, rule.workspace_id, current_user.id)
        db.delete(rule)
        db.commit()
    return None


@router.get("/guidelines/candidates", summary="List pending candidate extractions")
def get_guidelines_candidates(
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    verify_workspace_admin_in_compat(db, ws_id, current_user.id)
    candidates = rule_service.list_rules(db=db, workspace_id=ws_id, approval_status="pending")
    docs = db.query(GuidelineDocument).filter(GuidelineDocument.workspace_id == ws_id).all()
    doc_map = {d.id: d for d in docs}
    return [_map_rule_to_candidate(c, doc_map) for c in candidates]


@router.post("/guidelines/candidates/{candidate_id}/approve", summary="Promote candidate rule")
def approve_candidate_rule(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID")

    r_obj = rule_service.get_by_id(db, r_id)
    if not r_obj:
        raise HTTPException(status_code=404, detail="Candidate rule not found")
    verify_workspace_admin_in_compat(db, r_obj.workspace_id, current_user.id)
    rule = rule_service.approve_rule(db, r_obj, reviewer_id=current_user.id)
    return _map_rule_to_guideline(rule, {})


@router.post("/guidelines/candidates/{candidate_id}/reject", summary="Reject candidate rule")
def reject_candidate_rule(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(candidate_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid candidate ID")

    r_obj = rule_service.get_by_id(db, r_id)
    if not r_obj:
        raise HTTPException(status_code=404, detail="Candidate rule not found")
    verify_workspace_admin_in_compat(db, r_obj.workspace_id, current_user.id)
    rule_service.reject_rule(db, r_obj, reviewer_id=current_user.id)
    return {"message": "Candidate rejected", "id": candidate_id}


# ============================================================================
# DOCUMENTS ENDPOINTS
# ============================================================================

@router.get("/guidelines/documents", summary="List source documents")
def get_source_documents(
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    docs = db.query(GuidelineDocument).filter(GuidelineDocument.workspace_id == ws_id).order_by(GuidelineDocument.created_at.desc()).all()
    results = []
    for d in docs:
        cand_count = db.query(BrandRule).filter(BrandRule.document_id == d.id, BrandRule.approval_status == "pending").count()
        appr_count = db.query(BrandRule).filter(BrandRule.document_id == d.id, BrandRule.approval_status == "approved").count()
        results.append({
            "id": str(d.id),
            "name": d.filename,
            "format": "DOCX" if d.filename.lower().endswith(".docx") else "PDF",
            "size": f"{round(d.file_size / (1024*1024), 1)} MB" if d.file_size else "1.1 MB",
            "pages": 14,
            "uploadedAt": d.created_at.strftime("%b %d, %Y"),
            "uploadedBy": "Sarah Chen (Brand Lead)",
            "status": d.status,
            "extractedCandidatesCount": cand_count,
            "approvedRulesCount": appr_count,
            "fileUrl": f"/api/guidelines/{d.id}/text",
        })
    return results


@router.post("/guidelines/documents/upload", summary="Upload brand document and extract rules")
async def upload_brand_document(
    file: UploadFile = File(...),
    brand_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    verify_workspace_admin_in_compat(db, ws_id, current_user.id)

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF, DOCX, or TXT.")

    file_bytes = await file.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 15 MB limit.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    safe_filename = f"ws_{ws_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    extracted_text = extract_document_text(file_path, ext)

    doc = GuidelineDocument(
        workspace_id=ws_id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(file_bytes),
        extracted_text=extracted_text,
        status="extracted",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Automatically extract brand rules from the document text
    extracted_candidates = rule_service.extract_and_create_rules(db=db, document_id=doc.id)

    return {
        "id": str(doc.id),
        "name": doc.filename,
        "format": "DOCX" if doc.filename.lower().endswith(".docx") else "PDF",
        "size": f"{round(doc.file_size / (1024*1024), 1)} MB",
        "pages": 12,
        "uploadedAt": "Today",
        "uploadedBy": "Sarah Chen (Brand Lead)",
        "status": "extracted",
        "extractedCandidatesCount": len(extracted_candidates),
        "approvedRulesCount": 0,
    }


# ============================================================================
# REVIEWS & COMPLIANCE SCAN (Frontend format compatibility)
# ============================================================================

@router.post("/reviews/scan", summary="Run live compliance audit on marketing copy")
def scan_content(
    payload: Dict[str, Any] = Body(...),
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id or payload.get("brandId"))

    title = payload.get("title", "Untitled Asset").strip()
    content = payload.get("content", "").strip()
    content_type = payload.get("contentType", "social_media").lower().replace(" ", "_")
    channel = payload.get("channel", "Social")

    if not content:
        raise HTTPException(status_code=400, detail="Submitted content cannot be empty.")

    submission = ContentReviewSubmission(
        title=title,
        content=content,
        content_type=content_type,
    )

    try:
        review = review_service.submit_and_audit(
            db=db,
            workspace_id=ws_id,
            user_id=current_user.id,
            submission=submission,
        )
    except NoApprovedRulesError as err:
        raise HTTPException(
            status_code=400,
            detail=str(err),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance Engine failed: {exc}",
        )

    # Format findings according to frontend ComplianceFinding interface
    frontend_findings = []
    for f in review.findings:
        frontend_findings.append({
            "id": str(f.id),
            "category": f.category,
            "severity": "critical" if f.severity == "critical" else ("moderate" if f.severity == "major" else "minor"),
            "originalText": f.excerpt,
            "explanation": f.explanation,
            "supportingGuidelineCode": f.guideline_reference.split(":")[0].strip() if ":" in f.guideline_reference else "RULE",
            "supportingGuidelineTitle": f.guideline_reference.split(":", 1)[1].strip() if ":" in f.guideline_reference else f.guideline_reference,
            "suggestedCorrection": f.suggested_correction or "",
            "confidence": int(f.confidence * 100) if f.confidence <= 1.0 else int(f.confidence),
            "resolved": f.status in ("accepted", "applied"),
        })

    return {
        "id": str(review.id),
        "title": review.title,
        "contentType": review.content_type,
        "channel": channel,
        "overallScore": review.compliance_score,
        "issuesCount": len(frontend_findings),
        "status": "flagged" if review.compliance_score < 80 else "approved",
        "summary": review.summary or f"Automated audit completed. Score: {review.compliance_score}/100.",
        "contentPreview": review.content[:160] + ("..." if len(review.content) > 160 else ""),
        "findings": frontend_findings,
        "analyzedAt": review.created_at.isoformat(),
    }


# ============================================================================
# APPROVALS ENDPOINTS (Frontend format compatibility)
# ============================================================================

@router.get("/approvals/pending", summary="List pending approvals")
def get_pending_approvals(
    brand_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    verify_workspace_reviewer_or_admin_in_compat(db, ws_id, current_user.id)
    approvals = approval_service.list_workspace_approvals(db=db, workspace_id=ws_id, status="pending")

    results = []
    for app in approvals:
        if app.review_id:
            rev = db.query(ContentReview).filter(ContentReview.id == app.review_id).first()
            if rev:
                sub_user = app.submitter or rev.submitter or current_user
                rev_user = app.reviewer
                results.append({
                    "id": str(app.id),
                    "reviewId": str(rev.id),
                    "title": rev.title,
                    "contentType": rev.content_type,
                    "submittedBy": {
                        "name": sub_user.name,
                        "role": sub_user.role or "Employee",
                        "email": sub_user.email,
                    },
                    "assignedReviewer": {
                        "name": rev_user.name if rev_user else "Designated Reviewer",
                        "role": rev_user.role if rev_user else "Reviewer",
                        "email": rev_user.email if rev_user else "reviewer@brandshield.local",
                    },
                    "score": rev.compliance_score,
                    "status": "pending",
                    "reviewDate": rev.created_at.strftime("%b %d"),
                    "contentExcerpt": rev.content[:140] + "...",
                    "commentsCount": len(rev.activities or []),
                })
    return results


@router.post("/approvals/{item_id}/approve", summary="Approve review or approval ticket")
def approve_content_by_item(
    item_id: str,
    payload: Optional[Dict[str, Any]] = Body(default_factory=dict),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        parsed_id = int(item_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid approval/review ID")

    comment = (payload or {}).get("comment")

    # 1. Check if ID matches an Approval ticket
    approval = db.query(Approval).filter(Approval.id == parsed_id).first()
    if approval:
        if approval.status == "approved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item has already been approved.")
        ws_id = approval_service.get_approval_workspace_id(db, approval)
        if ws_id is not None:
            verify_workspace_reviewer_or_admin_in_compat(db, ws_id, current_user.id)
        try:
            approved_obj = approval_service.approve(db=db, approval=approval, reviewer=current_user)
            rev_id = approval.review_id or approval.id
            return {
                "id": approved_obj.id,
                "status": "approved",
                "success": True,
                "certificateId": f"CERT-BS-2026-{1000 + rev_id}",
                "review_id": approval.review_id,
            }
        except PermissionError as perm_err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(perm_err))
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))

    # 2. Check if ID matches a ContentReview directly
    review = review_service.get_by_id(db, parsed_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request or review not found")

    verify_workspace_reviewer_or_admin_in_compat(db, review.workspace_id, current_user.id)

    review.status = "approved"
    open_approvals = db.query(Approval).filter(Approval.review_id == parsed_id, Approval.status == "pending").all()
    for appr in open_approvals:
        appr.status = "approved"
        appr.reviewer_id = current_user.id
        if comment:
            appr.comment = comment

    activity = ReviewActivity(
        review_id=review.id,
        workspace_id=review.workspace_id,
        user_id=current_user.id,
        action="Review approved",
        details=comment or f"Certified and approved by {current_user.name}.",
    )
    db.add(activity)
    db.commit()

    return {
        "id": review.id,
        "status": "approved",
        "success": True,
        "certificateId": f"CERT-BS-2026-{1000 + review.id}",
        "review_id": review.id,
    }


@router.post("/approvals/{review_id}/request-changes", summary="Request changes on review")
def request_changes_by_review(
    review_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(review_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID")

    review = review_service.get_by_id(db, r_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    verify_workspace_reviewer_or_admin_in_compat(db, review.workspace_id, current_user.id)

    review.status = "needs_revision"
    notes = payload.get("revisionNotes") or payload.get("comment") or "Changes requested by reviewer."

    open_approvals = db.query(Approval).filter(Approval.review_id == r_id, Approval.status == "pending").all()
    for appr in open_approvals:
        appr.status = "changes_requested"
        appr.reviewer_id = current_user.id
        appr.comment = notes

    activity = ReviewActivity(
        review_id=review.id,
        workspace_id=review.workspace_id,
        user_id=current_user.id,
        action="Changes requested",
        details=notes,
    )
    db.add(activity)
    db.commit()

    return {"success": True}


@router.post("/approvals/{review_id}/comments", summary="Add comment to review")
def add_review_comment(
    review_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(review_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID")

    review = review_service.get_by_id(db, r_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if not workspace_service.is_member(db, review.workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of the workspace for this review.",
        )

    comment_text = payload.get("text", "").strip()
    if not comment_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment text cannot be empty.")

    activity = ReviewActivity(
        review_id=r_id,
        workspace_id=review.workspace_id,
        user_id=current_user.id,
        action="Comment Added",
        details=comment_text,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return {
        "id": f"c-{activity.id}",
        "authorName": current_user.name,
        "authorRole": current_user.role,
        "text": comment_text,
        "timestamp": activity.created_at.strftime("%b %d, %H:%M"),
    }


# ============================================================================
# HISTORY ENDPOINTS (Frontend format compatibility)
# ============================================================================

def _map_review_to_historical_record(r: ContentReview, current_user: User) -> Dict[str, Any]:
    findings = []
    for f in (r.findings or []):
        findings.append({
            "id": str(f.id),
            "category": f.category,
            "severity": f.severity,
            "originalText": f.excerpt,
            "explanation": f.explanation,
            "supportingGuidelineCode": f.guideline_reference.split(":")[0] if ":" in f.guideline_reference else "RULE",
            "supportingGuidelineTitle": f.guideline_reference,
            "suggestedCorrection": f.suggested_correction or "",
            "confidence": int(f.confidence * 100) if f.confidence <= 1.0 else int(f.confidence),
        })

    submitter = r.submitter or current_user
    submitted_by = {
        "name": submitter.name,
        "role": submitter.role or "Employee",
        "email": submitter.email,
        "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={submitter.name}",
    }

    # Identify reviewer from approvals or activities
    reviewer_user = None
    approvals_list = getattr(r, "approvals", None) or []
    activities_list = getattr(r, "activities", None) or []
    findings_list = getattr(r, "findings", None) or []

    for appr in approvals_list:
        if getattr(appr, "reviewer", None):
            reviewer_user = appr.reviewer
            break
    if not reviewer_user:
        for act in activities_list:
            if act.action in ("Review approved", "Changes requested") and getattr(act, "user", None):
                reviewer_user = act.user
                break

    if reviewer_user:
        assigned_reviewer = {
            "name": reviewer_user.name,
            "role": getattr(reviewer_user, "role", None) or "Reviewer",
            "email": reviewer_user.email,
            "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={reviewer_user.name}",
        }
    else:
        assigned_reviewer = {
            "name": "Governance Reviewer",
            "role": "Reviewer",
            "email": "reviewer@brandshield.local",
            "avatar": "https://api.dicebear.com/7.x/initials/svg?seed=Reviewer",
        }

    # Extract real comments from activities and approvals
    real_comments = []
    for act in activities_list:
        if act.action == "Comment Added" and act.details:
            act_user = getattr(act, "user", None) or current_user
            real_comments.append({
                "id": f"c-{act.id}",
                "authorName": act_user.name,
                "authorRole": getattr(act_user, "role", None) or "Member",
                "authorAvatar": f"https://api.dicebear.com/7.x/initials/svg?seed={act_user.name}",
                "text": act.details,
                "timestamp": act.created_at.strftime("%b %d, %H:%M"),
            })

    for appr in approvals_list:
        if appr.comment and not any(c["text"] == appr.comment for c in real_comments):
            appr_user = getattr(appr, "reviewer", None) or getattr(appr, "submitter", None) or current_user
            real_comments.append({
                "id": f"appr-c-{appr.id}",
                "authorName": appr_user.name,
                "authorRole": getattr(appr_user, "role", None) or "Reviewer",
                "authorAvatar": f"https://api.dicebear.com/7.x/initials/svg?seed={appr_user.name}",
                "text": appr.comment,
                "timestamp": appr.updated_at.strftime("%b %d, %H:%M"),
            })

    # Construct chronological audit timeline
    timeline = [
        {
            "id": f"tl-1-{r.id}",
            "stage": "Content submitted",
            "actorName": submitted_by["name"],
            "actorRole": submitted_by["role"],
            "timestamp": r.created_at.strftime("%b %d, %H:%M"),
            "status": "completed",
        },
        {
            "id": f"tl-2-{r.id}",
            "stage": "AI review completed",
            "actorName": "BrandShield AI",
            "actorRole": "Automated Sentinel",
            "timestamp": r.created_at.strftime("%b %d, %H:%M"),
            "note": f"Initial compliance score: {r.compliance_score}/100.",
            "status": "completed",
        },
    ]

    for act in activities_list:
        if act.action not in ("Audit Completed", "Content submitted"):
            timeline.append({
                "id": f"tl-act-{act.id}",
                "stage": act.action,
                "actorName": act.user.name if getattr(act, "user", None) else "System",
                "actorRole": getattr(act.user, "role", "Governance") if getattr(act, "user", None) else "Governance",
                "timestamp": act.created_at.strftime("%b %d, %H:%M"),
                "note": act.details,
                "status": "completed",
            })

    if r.status == "approved":
        timeline.append({
            "id": f"tl-dec-{r.id}",
            "stage": "Final approval",
            "actorName": assigned_reviewer["name"],
            "actorRole": assigned_reviewer["role"],
            "timestamp": r.updated_at.strftime("%b %d, %H:%M"),
            "status": "completed",
        })
    elif r.status in ("needs_changes", "needs_revision"):
        timeline.append({
            "id": f"tl-dec-{r.id}",
            "stage": "Changes requested",
            "actorName": assigned_reviewer["name"],
            "actorRole": assigned_reviewer["role"],
            "timestamp": r.updated_at.strftime("%b %d, %H:%M"),
            "status": "current",
        })
    else:
        timeline.append({
            "id": f"tl-dec-{r.id}",
            "stage": "Reviewer decision",
            "actorName": assigned_reviewer["name"],
            "actorRole": assigned_reviewer["role"],
            "timestamp": "Pending",
            "status": "current",
        })

    approval_status = "approved" if r.status == "approved" else ("needs_revision" if r.status in ("needs_changes", "needs_revision") else "pending")

    return {
        "id": str(r.id),
        "title": r.title,
        "contentType": r.content_type,
        "channel": "Social",
        "submittedBy": submitted_by,
        "assignedReviewer": assigned_reviewer,
        "score": r.compliance_score,
        "violationsCount": len(findings),
        "reviewDate": r.created_at.strftime("%b %d, %Y"),
        "approvalStatus": approval_status,
        "originalContent": r.original_content,
        "correctedContent": r.content,
        "findings": findings,
        "acceptedSuggestionsCount": sum(1 for f in findings_list if getattr(f, "status", None) in ("accepted", "applied")),
        "rejectedSuggestionsCount": sum(1 for f in findings_list if getattr(f, "status", None) == "rejected"),
        "comments": real_comments,
        "timeline": timeline,
    }


@router.get("/history", summary="List historical review ledger")
def get_review_history(
    brand_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws_id = get_target_workspace_id(db, current_user, brand_id)
    reviews_res = review_service.list_reviews(
        db=db,
        workspace_id=ws_id,
        page=1,
        size=100,
        search=search,
        status=status,
    )

    return [_map_review_to_historical_record(r, current_user) for r in reviews_res.items]


@router.get("/history/{id}", summary="Get single historical review by ID")
def get_history_by_id(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        r_id = int(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review ID")

    review = review_service.get_by_id(db, r_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review record not found")

    if not workspace_service.is_member(db, review.workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of the workspace for this review.",
        )

    return _map_review_to_historical_record(review, current_user)
