"""Documents router - RAG document upload and management."""
import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.orm.recipe import RecipeDocument
from app.models.orm.user import User
from app.rag.pipeline import RAGPipeline

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    recipe_id: str | None = Form(None),
    title: str | None = Form(None),
    current_user: User = require_role("ADM", "NUT"),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document, process it through the RAG pipeline, and index it."""
    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate doc_type
    valid_doc_types = {"recipe", "sop", "haccp_guide", "policy"}
    if doc_type not in valid_doc_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type: {doc_type}. Allowed: {', '.join(valid_doc_types)}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")

    # Save to temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        rag = RAGPipeline(db)
        recipe_uuid = UUID(recipe_id) if recipe_id else None
        chunk_count = await rag.ingest_document(
            file_path=tmp_path,
            doc_type=doc_type,
            recipe_id=recipe_uuid,
            title=title or file.filename,
        )
    finally:
        os.unlink(tmp_path)

    return {
        "success": True,
        "data": {
            "filename": file.filename,
            "doc_type": doc_type,
            "recipe_id": recipe_id,
            "chunks_created": chunk_count,
            "message": f"문서 '{file.filename}'이(가) {chunk_count}개 청크로 인덱싱되었습니다.",
        },
    }


@router.get("")
async def list_documents(
    doc_type: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List indexed documents (grouped by title and doc_type)."""
    from sqlalchemy import func

    query = select(
        RecipeDocument.title,
        RecipeDocument.doc_type,
        RecipeDocument.recipe_id,
        func.count(RecipeDocument.id).label("chunk_count"),
        func.min(RecipeDocument.created_at).label("indexed_at"),
    ).group_by(
        RecipeDocument.title,
        RecipeDocument.doc_type,
        RecipeDocument.recipe_id,
    )

    if doc_type:
        query = query.where(RecipeDocument.doc_type == doc_type)

    query = query.order_by(func.min(RecipeDocument.created_at).desc())
    result = await db.execute(query)
    rows = result.all()

    return {
        "success": True,
        "data": [
            {
                "title": row.title,
                "doc_type": row.doc_type,
                "recipe_id": str(row.recipe_id) if row.recipe_id else None,
                "chunk_count": row.chunk_count,
                "indexed_at": row.indexed_at.isoformat() if row.indexed_at else None,
            }
            for row in rows
        ],
    }


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = require_role("ADM"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a document and all its chunks from the index."""
    # Find the document to get its title/type for batch deletion
    doc = (await db.execute(
        select(RecipeDocument).where(RecipeDocument.id == document_id)
    )).scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete all chunks with same title and doc_type
    await db.execute(
        sql_delete(RecipeDocument).where(
            RecipeDocument.title == doc.title,
            RecipeDocument.doc_type == doc.doc_type,
        )
    )
    await db.flush()

    return {
        "success": True,
        "data": {"deleted": True, "title": doc.title, "doc_type": doc.doc_type},
    }
