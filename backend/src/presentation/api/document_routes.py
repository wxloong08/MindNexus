"""
Document API Routes
RESTful endpoints for document management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles
import os
import uuid

from src.infrastructure.database.connection import get_session
from src.presentation.schemas.api_schemas import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
    LinkedDocumentsResponse,
    ErrorResponse,
)
from src.presentation.api.dependencies import get_document_use_case
from src.application.use_cases.document_use_case import DocumentUseCase
from src.domain.entities.document import DocumentType

router = APIRouter(prefix="/documents", tags=["Documents"])


def _doc_to_response(doc) -> DocumentResponse:
    """Convert domain entity to response schema"""
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        content=doc.content,
        doc_type=doc.doc_type.value,
        status=doc.status.value,
        file_path=doc.file_path,
        file_size=doc.file_size,
        word_count=doc.word_count,
        outgoing_links=doc.outgoing_links,
        incoming_links=doc.incoming_links,
        tags=doc.tags,
        summary=doc.summary,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        indexed_at=doc.indexed_at,
    )


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def create_document(
    request: DocumentCreate,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Create a new document
    
    Creates a new document and optionally indexes it for RAG search.
    """
    try:
        doc = await use_case.create_document(
            title=request.title,
            content=request.content,
            doc_type=DocumentType(request.doc_type.value),
            tags=request.tags,
            auto_index=request.auto_index,
        )
        return _doc_to_response(doc)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    List all documents
    
    Returns paginated list of documents sorted by update time.
    """
    docs = await use_case.list_documents(skip=skip, limit=limit)
    total = await use_case.document_repo.count()
    
    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/search",
    response_model=DocumentListResponse,
)
async def search_documents(
    q: str,
    limit: int = 10,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Search documents by title
    
    Simple text search on document titles.
    """
    docs = await use_case.search_documents(query=q, limit=limit)
    
    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=len(docs),
        skip=0,
        limit=limit,
    )


@router.get(
    "/by-tag/{tag}",
    response_model=DocumentListResponse,
)
async def get_documents_by_tag(
    tag: str,
    limit: int = 50,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Get documents by tag
    """
    docs = await use_case.get_documents_by_tag(tag=tag, limit=limit)
    
    return DocumentListResponse(
        documents=[_doc_to_response(d) for d in docs],
        total=len(docs),
        skip=0,
        limit=limit,
    )


@router.get(
    "/{doc_id}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_document(
    doc_id: str,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Get a document by ID
    """
    doc = await use_case.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    return _doc_to_response(doc)


@router.put(
    "/{doc_id}",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def update_document(
    doc_id: str,
    request: DocumentUpdate,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Update a document
    
    Updates document content and optionally re-indexes it.
    """
    try:
        doc = await use_case.update_document(
            doc_id=doc_id,
            title=request.title,
            content=request.content,
            tags=request.tags,
            reindex=request.reindex,
        )
        return _doc_to_response(doc)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_document(
    doc_id: str,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Delete a document
    
    Removes the document and its vector index.
    """
    success = await use_case.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )


@router.post(
    "/{doc_id}/index",
    response_model=DocumentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def index_document(
    doc_id: str,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Index or re-index a document
    
    Chunks the document, generates embeddings, and stores in vector DB.
    """
    success = await use_case.index_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    
    doc = await use_case.get_document(doc_id)
    return _doc_to_response(doc)


@router.get(
    "/{doc_id}/links",
    response_model=LinkedDocumentsResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_linked_documents(
    doc_id: str,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Get documents linked to/from this document
    
    Returns bi-directional wiki-style links.
    """
    doc = await use_case.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {doc_id} not found",
        )
    
    links = await use_case.get_linked_documents(doc_id)
    
    return LinkedDocumentsResponse(
        outgoing=[_doc_to_response(d) for d in links["outgoing"]],
        incoming=[_doc_to_response(d) for d in links["incoming"]],
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Upload and create a document from a file
    
    Supports: .md, .txt, .pdf, .docx, .html
    """
    from src.infrastructure.document_processing.processor import FileParser
    
    # Validate file type
    filename = file.filename or "untitled"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    type_map = {
        "md": DocumentType.MARKDOWN,
        "txt": DocumentType.TEXT,
        "pdf": DocumentType.PDF,
        "docx": DocumentType.DOCX,
        "html": DocumentType.HTML,
    }
    
    if ext not in type_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(type_map.keys())}",
        )
    
    doc_type = type_map[ext]
    
    # Save file temporarily for PDF/DOCX
    content = ""
    file_path = None
    
    if ext in ["pdf", "docx"]:
        # Save to temp file
        file_path = f"./data/uploads/{uuid.uuid4()}.{ext}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        async with aiofiles.open(file_path, "wb") as f:
            file_content = await file.read()
            await f.write(file_content)
        
        # Parse content
        if ext == "pdf":
            content = FileParser.parse_pdf(file_path)
        else:
            content = FileParser.parse_docx(file_path)
    else:
        # Read text directly
        file_content = await file.read()
        content = file_content.decode("utf-8")
    
    # Extract title from filename
    title = filename.rsplit(".", 1)[0]
    
    # Create document
    doc = await use_case.create_document(
        title=title,
        content=content,
        doc_type=doc_type,
        auto_index=True,
    )
    
    # Update file path if saved
    if file_path:
        doc.file_path = file_path
        doc.file_size = os.path.getsize(file_path)
        await use_case.document_repo.update(doc)
    
    return _doc_to_response(doc)
