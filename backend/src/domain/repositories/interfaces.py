"""
Repository Interfaces - Abstract base classes for data access
Following the Repository Pattern for clean architecture
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.domain.entities.document import (
    Document, 
    DocumentChunk, 
    Conversation, 
    Message,
    Tag,
    User
)


class DocumentRepository(ABC):
    """Abstract repository for Document operations"""
    
    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Create a new document"""
        pass
    
    @abstractmethod
    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        pass
    
    @abstractmethod
    async def get_by_title(self, title: str) -> Optional[Document]:
        """Get document by title (for wiki-links)"""
        pass
    
    @abstractmethod
    async def get_all(
        self, 
        user_id: Optional[str] = None,
        skip: int = 0, 
        limit: int = 100
    ) -> List[Document]:
        """Get all documents with pagination"""
        pass
    
    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Update an existing document"""
        pass
    
    @abstractmethod
    async def delete(self, doc_id: str) -> bool:
        """Delete a document"""
        pass
    
    @abstractmethod
    async def search_by_title(self, query: str, limit: int = 10) -> List[Document]:
        """Full-text search by title"""
        pass
    
    @abstractmethod
    async def get_by_tag(self, tag: str, limit: int = 100) -> List[Document]:
        """Get documents by tag"""
        pass
    
    @abstractmethod
    async def get_linked_documents(self, doc_id: str) -> Dict[str, List[Document]]:
        """Get documents linked to/from this document"""
        pass
    
    @abstractmethod
    async def count(self, user_id: Optional[str] = None) -> int:
        """Count total documents"""
        pass


class ChunkRepository(ABC):
    """Abstract repository for DocumentChunk operations"""
    
    @abstractmethod
    async def create_many(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        """Create multiple chunks"""
        pass
    
    @abstractmethod
    async def get_by_document(self, doc_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document"""
        pass
    
    @abstractmethod
    async def delete_by_document(self, doc_id: str) -> int:
        """Delete all chunks for a document"""
        pass


class ConversationRepository(ABC):
    """Abstract repository for Conversation operations"""
    
    @abstractmethod
    async def create(self, conversation: Conversation) -> Conversation:
        """Create a new conversation"""
        pass
    
    @abstractmethod
    async def get_by_id(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        pass
    
    @abstractmethod
    async def get_all(
        self, 
        user_id: Optional[str] = None,
        skip: int = 0, 
        limit: int = 50
    ) -> List[Conversation]:
        """Get all conversations"""
        pass
    
    @abstractmethod
    async def delete(self, conv_id: str) -> bool:
        """Delete a conversation and its messages"""
        pass


class MessageRepository(ABC):
    """Abstract repository for Message operations"""
    
    @abstractmethod
    async def create(self, message: Message) -> Message:
        """Create a new message"""
        pass
    
    @abstractmethod
    async def get_by_conversation(
        self, 
        conv_id: str,
        limit: int = 50
    ) -> List[Message]:
        """Get messages for a conversation"""
        pass
    
    @abstractmethod
    async def delete_by_conversation(self, conv_id: str) -> int:
        """Delete all messages in a conversation"""
        pass


class TagRepository(ABC):
    """Abstract repository for Tag operations"""
    
    @abstractmethod
    async def create(self, tag: Tag) -> Tag:
        """Create a new tag"""
        pass
    
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name"""
        pass
    
    @abstractmethod
    async def get_all(self) -> List[Tag]:
        """Get all tags"""
        pass
    
    @abstractmethod
    async def get_popular(self, limit: int = 20) -> List[Tag]:
        """Get most popular tags"""
        pass
    
    @abstractmethod
    async def update_count(self, name: str, delta: int) -> None:
        """Update document count for a tag"""
        pass


class UserRepository(ABC):
    """Abstract repository for User operations"""
    
    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user"""
        pass
    
    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def update(self, user: User) -> User:
        """Update user"""
        pass


class VectorStoreRepository(ABC):
    """Abstract repository for Vector Store operations"""
    
    @abstractmethod
    async def add_documents(
        self, 
        chunks: List[DocumentChunk],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]]
    ) -> None:
        """Add document chunks with embeddings"""
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Semantic search by embedding"""
        pass
    
    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid search (semantic + keyword)"""
        pass
    
    @abstractmethod
    async def delete_by_document(self, doc_id: str) -> None:
        """Delete all vectors for a document"""
        pass
    
    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector collection statistics"""
        pass
