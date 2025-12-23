"""
API Request/Response Schemas
Pydantic models for API validation
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============== Enums ==============

class DocumentTypeSchema(str, Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class DocumentStatusSchema(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


# ============== Document Schemas ==============

class DocumentCreate(BaseModel):
    """Request schema for creating a document"""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    doc_type: DocumentTypeSchema = DocumentTypeSchema.MARKDOWN
    tags: Optional[List[str]] = None
    auto_index: bool = True


class DocumentUpdate(BaseModel):
    """Request schema for updating a document"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    reindex: bool = True


class DocumentResponse(BaseModel):
    """Response schema for a document"""
    id: str
    title: str
    content: str
    doc_type: DocumentTypeSchema
    status: DocumentStatusSchema
    file_path: Optional[str] = None
    file_size: int = 0
    word_count: int = 0
    outgoing_links: List[str] = []
    incoming_links: List[str] = []
    tags: List[str] = []
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response schema for document list"""
    documents: List[DocumentResponse]
    total: int
    skip: int
    limit: int


class LinkedDocumentsResponse(BaseModel):
    """Response schema for linked documents"""
    outgoing: List[DocumentResponse]
    incoming: List[DocumentResponse]


# ============== Chat Schemas ==============

class ConversationCreate(BaseModel):
    """Request schema for creating a conversation"""
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """Response schema for a conversation"""
    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response schema for conversation list"""
    conversations: List[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    """Response schema for a message"""
    id: str
    conversation_id: str
    role: str
    content: str
    retrieved_chunks: List[str] = []
    model_used: Optional[str] = None
    tokens_used: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Request schema for chat"""
    message: str = Field(..., min_length=1)
    use_rag: bool = True
    model: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Response schema for chat (non-streaming)"""
    message: MessageResponse
    context_used: List[Dict[str, Any]] = []


# ============== Search Schemas ==============

class SearchRequest(BaseModel):
    """Request schema for semantic search"""
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    include_documents: bool = True


class SearchResult(BaseModel):
    """Single search result"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    document: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """Response schema for search"""
    query: str
    results: List[SearchResult]
    total: int


# ============== Tag Schemas ==============

class TagResponse(BaseModel):
    """Response schema for a tag"""
    id: str
    name: str
    color: str
    document_count: int
    
    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Response schema for tag list"""
    tags: List[TagResponse]


# ============== Stats Schemas ==============

class StatsResponse(BaseModel):
    """Response schema for system stats"""
    total_documents: int
    total_chunks: int
    total_tags: int
    top_tags: List[Dict[str, Any]]


# ============== Health Schemas ==============

class HealthResponse(BaseModel):
    """Response schema for health check"""
    status: str
    version: str
    database: str
    vector_store: Dict[str, Any]
    llm: Dict[str, Any]


# ============== Error Schemas ==============

class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    code: Optional[str] = None
