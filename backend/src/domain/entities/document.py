"""
Domain Entities - Core business objects
"""
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum
import uuid


class DocumentType(str, Enum):
    """Supported document types"""
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class DocumentStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


@dataclass
class Document:
    """
    Document entity representing a knowledge item
    Core domain object for the knowledge management system
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    doc_type: DocumentType = DocumentType.MARKDOWN
    status: DocumentStatus = DocumentStatus.PENDING
    
    # Metadata
    file_path: Optional[str] = None
    file_size: int = 0
    word_count: int = 0
    
    # Relationships (Wiki-links)
    outgoing_links: List[str] = field(default_factory=list)  # Links to other docs
    incoming_links: List[str] = field(default_factory=list)  # Docs linking to this
    
    # AI-generated metadata
    tags: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = None
    
    # User ownership
    user_id: Optional[str] = None
    
    def update_content(self, content: str) -> None:
        """Update document content and metadata"""
        self.content = content
        self.word_count = len(content.split())
        self.updated_at = datetime.utcnow()
        self.status = DocumentStatus.PENDING  # Re-index needed
    
    def mark_indexed(self) -> None:
        """Mark document as indexed"""
        self.status = DocumentStatus.INDEXED
        self.indexed_at = datetime.utcnow()
    
    def mark_failed(self) -> None:
        """Mark document indexing as failed"""
        self.status = DocumentStatus.FAILED
    
    def add_tag(self, tag: str) -> None:
        """Add a tag if not exists"""
        tag = tag.lower().strip()
        if tag and tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag"""
        tag = tag.lower().strip()
        if tag in self.tags:
            self.tags.remove(tag)
    
    def add_outgoing_link(self, doc_id: str) -> None:
        """Add an outgoing link to another document"""
        if doc_id not in self.outgoing_links:
            self.outgoing_links.append(doc_id)
    
    def add_incoming_link(self, doc_id: str) -> None:
        """Add an incoming link from another document"""
        if doc_id not in self.incoming_links:
            self.incoming_links.append(doc_id)


@dataclass
class DocumentChunk:
    """
    A chunk of a document for vector storage
    Used in RAG retrieval
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str = ""
    chunk_index: int = 0
    
    # Metadata for retrieval
    start_char: int = 0
    end_char: int = 0
    
    # Embedding (stored in vector DB, not here)
    # embedding: List[float] = field(default_factory=list)
    
    # Parent chunk for hierarchical retrieval
    parent_chunk_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Conversation:
    """
    Conversation entity for chat history
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: Optional[str] = None
    user_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Message:
    """
    Chat message entity
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    role: str = "user"  # user, assistant, system
    content: str = ""
    
    # RAG context
    retrieved_chunks: List[str] = field(default_factory=list)  # Chunk IDs
    
    # Metadata
    model_used: Optional[str] = None
    tokens_used: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Tag:
    """
    Tag entity for document categorization
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    color: str = "#808080"
    document_count: int = 0
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def increment_count(self) -> None:
        self.document_count += 1
    
    def decrement_count(self) -> None:
        if self.document_count > 0:
            self.document_count -= 1


@dataclass
class User:
    """
    User entity (optional, for multi-tenant support)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: str = ""
    hashed_password: str = ""
    is_active: bool = True
    is_admin: bool = False
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
