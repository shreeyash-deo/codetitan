import os
import re
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import verify_workspace_access, get_current_user, require_workspace_admin
from app.models.guideline import GuidelineDocument
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.schemas.guideline import GuidelineDocumentOut, GuidelineDocumentCreate
from app.schemas.rule import ExtractedRulesResponse, BrandRuleOut
from app.utils.extractor import extract_document_text
from app.services.ai.ai_service import ai_service
from app.services.rule_service import rule_service
from app.services.workspace_service import workspace_service

router = APIRouter(tags=["Guideline Documents"])


def get_document_with_access(
    document_id: int,
    db: Session,
    current_user: User,
) -> GuidelineDocument:
    """Helper to retrieve guideline document and verify current user has workspace access."""
    doc = db.query(GuidelineDocument).filter(GuidelineDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guideline document not found.",
        )

    if not workspace_service.is_member(db, doc.workspace_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You are not a member of the workspace containing this document.",
        )
    return doc


def verify_doc_admin_access(doc: GuidelineDocument, user_id: int, db: Session):
    member = workspace_service.get_member(db, doc.workspace_id, user_id)
    if not member or member.role.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. Required workspace role: Admin",
        )


@router.post(
    "/workspaces/{workspace_id}/guidelines",
    response_model=GuidelineDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create guideline document record via JSON metadata",
)
def create_guideline_record(
    workspace_id: int,
    doc_in: GuidelineDocumentCreate,
    db: Session = Depends(get_db),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    doc = GuidelineDocument(
        workspace_id=workspace_id,
        filename=doc_in.filename,
        file_path=doc_in.file_path,
        extracted_text=doc_in.extracted_text,
        status=doc_in.status or "extracted",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.post(
    "/workspaces/{workspace_id}/guidelines/upload",
    response_model=GuidelineDocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload guideline document (PDF, DOCX, TXT) with automated text extraction",
)
async def upload_guideline(
    workspace_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: WorkspaceMember = Depends(require_workspace_admin),
):
    """
    Upload a brand guideline document (PDF, DOCX, or TXT).
    Validates file type and size (max 15MB), writes securely to local storage,
    and extracts text automatically via PyMuPDF or python-docx.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload payload.",
        )

    # 1. Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{ext}'. Supported formats are: PDF, DOCX, TXT.",
        )

    # 2. Sanitize and generate safe unique filename
    raw_name = Path(file.filename).name
    clean_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", raw_name)
    unique_filename = f"{uuid.uuid4().hex[:10]}_{clean_name}"

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination_path = upload_dir / unique_filename

    # 3. Stream write with 15MB file size enforcement
    total_bytes = 0
    chunk_size = 64 * 1024  # 64KB chunks
    try:
        with open(destination_path, "wb") as buffer:
            while chunk := await file.read(chunk_size):
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
                    # Clean up oversized file immediately
                    buffer.close()
                    if destination_path.exists():
                        destination_path.unlink()
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds the 15 MB maximum limit.",
                    )
                buffer.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        if destination_path.exists():
            destination_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store file on disk: {exc}",
        )

    # 4. Extract document text
    status_str = "extracted"
    extracted_text = ""
    try:
        extracted_text = extract_document_text(str(destination_path), ext)
        if not extracted_text:
            status_str = "empty"
    except Exception as exc:
        status_str = "text_failed"
        extracted_text = f"[Text extraction failed: {str(exc)}]"

    # 5. Persist document metadata in database
    doc = GuidelineDocument(
        workspace_id=workspace_id,
        filename=raw_name,
        file_path=str(destination_path),
        extracted_text=extracted_text,
        status=status_str,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return doc


@router.get(
    "/workspaces/{workspace_id}/guidelines",
    response_model=List[GuidelineDocumentOut],
    summary="List all guideline documents for a workspace",
)
def list_workspace_guidelines(
    workspace_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(verify_workspace_access),
):
    """List all uploaded guideline documents in the workspace ordered by upload date."""
    return (
        db.query(GuidelineDocument)
        .filter(GuidelineDocument.workspace_id == workspace_id)
        .order_by(GuidelineDocument.uploaded_at.desc())
        .all()
    )


@router.get(
    "/guidelines/{document_id}",
    response_model=GuidelineDocumentOut,
    summary="Get guideline document metadata by ID",
)
def get_guideline_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve metadata for a single guideline document."""
    return get_document_with_access(document_id, db, current_user)


@router.get(
    "/guidelines/{document_id}/text",
    summary="Get extracted text content of a guideline document",
)
def get_guideline_text(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the raw extracted text along with character count and processing status."""
    doc = get_document_with_access(document_id, db, current_user)
    return {
        "id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "uploaded_at": doc.uploaded_at,
        "character_count": len(doc.extracted_text or ""),
        "extracted_text": doc.extracted_text or "",
    }


@router.get(
    "/guidelines/{document_id}/download",
    summary="Download original guideline document file",
)
def download_guideline_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download the original uploaded guideline document.
    On ephemeral hosting (such as Render Free tier without a persistent disk),
    local files do not persist across restarts. If the physical file is absent,
    this endpoint returns a graceful 404 response indicating that the original
    file is unavailable while extracted text and approved brand rules remain safely preserved.
    """
    doc = get_document_with_access(document_id, db, current_user)

    file_path = Path(doc.file_path) if doc.file_path else None
    if not file_path or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Original file '{doc.filename}' is unavailable on local storage (ephemeral filesystem). "
                "Extracted text and approved brand rules remain safely preserved in the database."
            ),
        )

    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/octet-stream",
    )


@router.delete(
    "/guidelines/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a guideline document and its local file",
)
def delete_guideline_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the guideline document record and unlinks its file from storage."""
    doc = get_document_with_access(document_id, db, current_user)
    verify_doc_admin_access(doc, current_user.id, db)

    # Remove file from disk if present
    try:
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass  # Proceed with DB deletion even if file was already removed

    db.delete(doc)
    db.commit()
    return None


@router.post(
    "/guidelines/{document_id}/extract-rules",
    response_model=ExtractedRulesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI rule extraction on an uploaded guideline document",
)
def extract_rules_from_guideline(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extract concrete brand rules from guideline text using the configured AI provider (Gemini or DeepSeek).
    Extracted rules start with 'pending' status for human-in-the-loop governance.
    """
    doc = get_document_with_access(document_id, db, current_user)
    verify_doc_admin_access(doc, current_user.id, db)

    if not doc.extracted_text or doc.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document text is empty or failed extraction. Cannot extract rules.",
        )

    try:
        candidates = ai_service.extract_rules_from_text(doc.extracted_text)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except TimeoutError as timeout_err:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(timeout_err),
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI Provider error: {str(run_err)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during AI rule extraction: {str(exc)}",
        )

    # Persist extracted rules in workspace as pending (with deduplication)
    created_rules = rule_service.save_extracted_rules(
        db=db,
        workspace_id=doc.workspace_id,
        document_id=doc.id,
        candidates=candidates,
    )

    return ExtractedRulesResponse(
        document_id=doc.id,
        extracted_count=len(created_rules),
        rules=created_rules,
    )
