import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_member, require_viewer
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, PermissionError_, ValidationAppError
from app.db.session import get_db
from app.models.document import Document, DocumentStatus, DocumentVisibility
from app.models.user import User
from app.models.workspace import WorkspaceRole, role_at_least
from app.schemas.documents import DocumentOut, DocumentUploadResponse
from app.services.jobs.queue import enqueue_ingestion_job

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    workspace_id: uuid.UUID,
    file: UploadFile,
    visibility: DocumentVisibility = DocumentVisibility.workspace,
    current_user: User = Depends(get_current_user),
    _membership=Depends(require_member),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_upload_extensions:
        raise ValidationAppError(
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(settings.allowed_upload_extensions)}"
        )

    max_bytes = settings.max_upload_mb * 1024 * 1024
    hasher = hashlib.sha256()
    size = 0
    chunks: list[bytes] = []
    while True:
        piece = await file.read(1024 * 1024)
        if not piece:
            break
        size += len(piece)
        if size > max_bytes:
            raise ValidationAppError(f"File exceeds the {settings.max_upload_mb}MB upload limit")
        hasher.update(piece)
        chunks.append(piece)
    content = b"".join(chunks)
    checksum = hasher.hexdigest()

    # Dedup: if this exact content was already uploaded to this workspace, don't re-ingest.
    existing = (
        db.query(Document)
        .filter(Document.workspace_id == workspace_id, Document.checksum_sha256 == checksum)
        .first()
    )
    if existing:
        return DocumentUploadResponse(
            document=DocumentOut.model_validate(existing),
            job_id=uuid.uuid4(),  # no new job; nothing to poll
            message="An identical document already exists in this workspace; skipped re-ingestion.",
        )

    # Storage path is derived from a fresh UUID, never the client-supplied
    # filename — the old code trusted `file.filename` directly as a path
    # (writable to `temp.docx` in the CWD), which this design makes
    # structurally impossible regardless of what the client sends.
    workspace_dir = Path(settings.upload_dir) / str(workspace_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    document_id = uuid.uuid4()
    storage_path = workspace_dir / f"{document_id}{suffix}"
    storage_path.write_bytes(content)

    document = Document(
        id=document_id,
        workspace_id=workspace_id,
        uploaded_by=current_user.id,
        filename=Path(file.filename or "upload").name,  # display name only, never used as a path
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
        checksum_sha256=checksum,
        storage_path=str(storage_path),
        status=DocumentStatus.pending,
        visibility=visibility,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    job = enqueue_ingestion_job(db, document_id=document.id)

    return DocumentUploadResponse(document=DocumentOut.model_validate(document), job_id=job.id)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    workspace_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    membership=Depends(require_viewer),
    db: Session = Depends(get_db),
):
    query = db.query(Document).filter(Document.workspace_id == workspace_id)
    if not role_at_least(membership.role, WorkspaceRole.admin):
        query = query.filter(
            (Document.visibility == DocumentVisibility.workspace) | (Document.uploaded_by == current_user.id)
        )
    return query.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    membership=Depends(require_viewer),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise NotFoundError("Document not found")
    if document.visibility == DocumentVisibility.private and document.uploaded_by != current_user.id:
        if not role_at_least(membership.role, WorkspaceRole.admin):
            raise PermissionError_("This document is private to its uploader")
    return document


@router.delete("/{document_id}", status_code=204)
def delete_document(
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    membership=Depends(require_member),
    db: Session = Depends(get_db),
):
    document = db.get(Document, document_id)
    if document is None or document.workspace_id != workspace_id:
        raise NotFoundError("Document not found")
    if document.uploaded_by != current_user.id and not role_at_least(membership.role, WorkspaceRole.admin):
        raise PermissionError_("Only the uploader or a workspace admin can delete this document")

    Path(document.storage_path).unlink(missing_ok=True)
    db.delete(document)
    db.commit()
