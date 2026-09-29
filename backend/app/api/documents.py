import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models import Document, User
from app.schemas.records import DocumentOut, SignedLink
from app.services.access import authorize_patient_access
from app.services.scan import scan
from app.services.storage import get_storage

router = APIRouter(prefix="/api", tags=["documents"])

MAX_BYTES = 10 * 1024 * 1024
DOC_TYPES = {"lab_report", "imaging", "referral", "insurance", "consent", "other"}
# content type -> (extension, magic-byte prefixes)
ALLOWED = {
    "application/pdf": (".pdf", (b"%PDF-",)),
    "image/png": (".png", (b"\x89PNG\r\n\x1a\n",)),
    "image/jpeg": (".jpg", (b"\xff\xd8\xff",)),
}
LINK_TTL = 300
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1]
    return _SAFE.sub("_", base).strip("._")[:120] or "file"


def _can_view_documents(user: User) -> bool:
    return user.role.name in ("staff", "doctor", "patient")


@router.post(
    "/patients/{patient_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    patient_id: uuid.UUID,
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    if not _can_view_documents(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    await authorize_patient_access(db, user, patient_id)
    if doc_type not in DOC_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown document type")
    if file.content_type not in ALLOWED:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF, PNG, JPEG allowed")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 10 MB")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Empty file")
    ext, magics = ALLOWED[file.content_type]
    if not data.startswith(magics):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content does not match type"
        )
    threat = scan(data)
    if threat:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"File rejected by scanner: {threat}"
        )
    key = f"{patient_id}/{uuid.uuid4().hex}{ext}"
    await get_storage().put(key, data, file.content_type)
    doc = Document(
        patient_id=patient_id,
        doc_type=doc_type,
        filename=_safe_name(file.filename or "file"),
        content_type=file.content_type,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_key=key,
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/patients/{patient_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    if not _can_view_documents(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    await authorize_patient_access(db, user, patient_id)
    rows = (
        await db.execute(
            select(Document)
            .where(Document.patient_id == patient_id, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
    ).scalars()
    return list(rows)


async def _authorized_doc(db: AsyncSession, user: User, doc_id: uuid.UUID) -> Document:
    doc = (
        await db.execute(
            select(Document).where(Document.id == doc_id, Document.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if doc is None or not _can_view_documents(user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    await authorize_patient_access(db, user, doc.patient_id)
    return doc


@router.get("/documents/{doc_id}/link", response_model=SignedLink)
async def signed_link(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignedLink:
    doc = await _authorized_doc(db, user, doc_id)
    exp = datetime.now(UTC) + timedelta(seconds=LINK_TTL)
    token = jwt.encode(
        {"doc": str(doc.id), "type": "download", "exp": exp}, get_settings().secret_key, "HS256"
    )
    return SignedLink(url=f"/api/documents/download?token={token}", expires_in=LINK_TTL)


@router.get("/documents/download")
async def download(token: str = Query(...), db: AsyncSession = Depends(get_db)) -> Response:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        if payload.get("type") != "download":
            raise jwt.InvalidTokenError
        doc_id = uuid.UUID(payload["doc"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid or expired link") from None
    doc = (
        await db.execute(
            select(Document).where(Document.id == doc_id, Document.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    data = await get_storage().get(doc.storage_key)
    return Response(
        data,
        media_type=doc.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if user.role.name not in ("staff", "doctor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
    doc = await _authorized_doc(db, user, doc_id)
    doc.deleted_at = datetime.now(UTC)  # soft delete; the stored object is retained
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
