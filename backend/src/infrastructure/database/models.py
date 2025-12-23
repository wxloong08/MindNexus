"""
SQLAlchemy Database Models
ORM layer for persistent storage
"""
from datetime import datetime
from typing import List
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, 
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
import enum


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models"""
    pass


class DocumentTypeEnum(str, enum.Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"


class DocumentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class DocumentModel(Base):
    """Document database model"""
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    doc_type = Column(SQLEnum(DocumentTypeEnum), default=DocumentTypeEnum.MARKDOWN)
    status = Column(SQLEnum(DocumentStatusEnum), default=DocumentStatusEnum.PENDING)
    
    # Metadata
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    
    # JSON fields for lists
    outgoing_links = Column(JSON, default=list)
    incoming_links = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    
    # AI-generated
    summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)
    
    # User
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")
    user = relationship("UserModel", back_populates="documents")
    
    # Indexes for search
    __table_args__ = (
        Index("idx_document_title_search", "title"),
        Index("idx_document_user_id", "user_id"),
        Index("idx_document_status", "status"),
    )


class DocumentChunkModel(Base):
    """Document chunk database model"""
    __tablename__ = "document_chunks"
    
    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    
    start_char = Column(Integer, default=0)
    end_char = Column(Integer, default=0)
    
    parent_chunk_id = Column(String(36), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    document = relationship("DocumentModel", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_chunk_document_id", "document_id"),
    )


class ConversationModel(Base):
    """Conversation database model"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(500), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    user = relationship("UserModel", back_populates="conversations")


class MessageModel(Base):
    """Message database model"""
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="user")
    content = Column(Text, nullable=False)
    
    retrieved_chunks = Column(JSON, default=list)
    model_used = Column(String(100), nullable=True)
    tokens_used = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    conversation = relationship("ConversationModel", back_populates="messages")
    
    __table_args__ = (
        Index("idx_message_conversation_id", "conversation_id"),
    )


class TagModel(Base):
    """Tag database model"""
    __tablename__ = "tags"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(20), default="#808080")
    document_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class UserModel(Base):
    """User database model"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("DocumentModel", back_populates="user")
    conversations = relationship("ConversationModel", back_populates="user")
