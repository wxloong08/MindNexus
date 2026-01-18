"""
Application Use Cases - Document Management
Business logic orchestration for document operations
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import structlog

from src.domain.entities.document import Document, DocumentChunk, DocumentType, DocumentStatus
from src.infrastructure.database.repositories import (
    SQLAlchemyDocumentRepository,
    SQLAlchemyChunkRepository,
    SQLAlchemyTagRepository,
)
from src.infrastructure.embedding.service import EmbeddingService
from src.infrastructure.vector_store.chroma_store import ChromaVectorStore
from src.infrastructure.document_processing.processor import DocumentProcessor
from src.infrastructure.llm.service import LLMService
from src.infrastructure.vault.service import VaultService

logger = structlog.get_logger()


class DocumentUseCase:
    """
    Document management use cases
    
    Handles:
    - Document CRUD operations
    - Document indexing (chunking, embedding, vector storage)
    - Link management (bi-directional wiki links)
    - Auto-tagging and summarization
    """
    
    def __init__(
        self,
        document_repo: SQLAlchemyDocumentRepository,
        chunk_repo: SQLAlchemyChunkRepository,
        tag_repo: SQLAlchemyTagRepository,
        embedding_service: EmbeddingService,
        vector_store: ChromaVectorStore,
        document_processor: DocumentProcessor,
        llm_service: Optional[LLMService] = None,
        vault_service: Optional[VaultService] = None,
        enable_auto_tagging: bool = True,
        enable_summarization: bool = True,
    ):
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.tag_repo = tag_repo
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.document_processor = document_processor
        self.llm_service = llm_service
        self.vault_service = vault_service
        self.enable_auto_tagging = enable_auto_tagging
        self.enable_summarization = enable_summarization
    
    async def create_document(
        self,
        title: str,
        content: str,
        doc_type: DocumentType = DocumentType.MARKDOWN,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        auto_index: bool = True,
    ) -> Document:
        """
        Create a new document and optionally index it
        
        Args:
            title: Document title
            content: Document content
            doc_type: Type of document
            tags: Initial tags
            user_id: Owner user ID
            auto_index: Whether to index immediately
        
        Returns:
            Created Document entity
        """
        # Extract wiki links
        outgoing_links = self.document_processor.extract_wiki_links(content)
        
        # Extract hashtags from content
        content_tags = self.document_processor.extract_tags_from_content(content)
        all_tags = list(set((tags or []) + content_tags))
        
        # Create document entity
        document = Document(
            id=str(uuid.uuid4()),
            title=title,
            content=content,
            doc_type=doc_type,
            status=DocumentStatus.PENDING,
            word_count=self.document_processor.count_words(content),
            outgoing_links=outgoing_links,
            tags=all_tags,
            user_id=user_id,
        )
        
        # Save to database
        document = await self.document_repo.create(document)
        
        # Update tag counts
        for tag in all_tags:
            existing_tag = await self.tag_repo.get_by_name(tag)
            if existing_tag:
                await self.tag_repo.update_count(tag, 1)
            else:
                from src.domain.entities.document import Tag
                new_tag = Tag(name=tag.lower(), document_count=1)
                await self.tag_repo.create(new_tag)
        
        # Update bi-directional links
        await self._update_incoming_links(document)
        
        # Index if requested
        if auto_index:
            await self.index_document(document.id)
        
        # Save to vault as .md file (Obsidian-style)
        if self.vault_service:
            self.vault_service.save_document(
                doc_id=document.id,
                title=document.title,
                content=document.content,
                tags=document.tags,
                created_at=document.created_at.isoformat() if document.created_at else None,
                updated_at=document.updated_at.isoformat() if document.updated_at else None,
            )
        
        logger.info("document_created", doc_id=document.id, title=title)
        return document
    
    async def update_document(
        self,
        doc_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        reindex: bool = True,
    ) -> Document:
        """Update an existing document"""
        document = await self.document_repo.get_by_id(doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")
        
        # Store old tags for count update
        old_tags = set(document.tags)
        
        # Update fields
        if title is not None:
            document.title = title
        
        if content is not None:
            document.update_content(content)
            document.outgoing_links = self.document_processor.extract_wiki_links(content)
            content_tags = self.document_processor.extract_tags_from_content(content)
            if tags is None:
                tags = list(set(document.tags + content_tags))
        
        if tags is not None:
            document.tags = tags
        
        document.updated_at = datetime.utcnow()
        
        # Save changes
        document = await self.document_repo.update(document)
        
        # Update tag counts
        new_tags = set(document.tags)
        for tag in old_tags - new_tags:
            await self.tag_repo.update_count(tag, -1)
        for tag in new_tags - old_tags:
            existing = await self.tag_repo.get_by_name(tag)
            if existing:
                await self.tag_repo.update_count(tag, 1)
            else:
                from src.domain.entities.document import Tag
                new_tag = Tag(name=tag.lower(), document_count=1)
                await self.tag_repo.create(new_tag)
        
        # Update links
        await self._update_incoming_links(document)
        
        # Reindex if content changed
        if reindex and content is not None:
            await self.index_document(doc_id)
        
        # Update vault .md file (Obsidian-style)
        if self.vault_service:
            self.vault_service.save_document(
                doc_id=document.id,
                title=document.title,
                content=document.content,
                tags=document.tags,
                created_at=document.created_at.isoformat() if document.created_at else None,
                updated_at=document.updated_at.isoformat() if document.updated_at else None,
            )
        
        logger.info("document_updated", doc_id=doc_id)
        return document
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its index"""
        document = await self.document_repo.get_by_id(doc_id)
        if not document:
            return False
        
        # Update tag counts
        for tag in document.tags:
            await self.tag_repo.update_count(tag, -1)
        
        # Remove from vector store
        await self.vector_store.delete_by_document(doc_id)
        
        # Delete chunks
        await self.chunk_repo.delete_by_document(doc_id)
        
        # Delete document
        await self.document_repo.delete(doc_id)
        
        # Delete from vault (Obsidian-style)
        if self.vault_service:
            self.vault_service.delete_document(document.title)
        
        logger.info("document_deleted", doc_id=doc_id)
        return True
    
    async def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID"""
        return await self.document_repo.get_by_id(doc_id)
    
    async def get_document_by_title(self, title: str) -> Optional[Document]:
        """Get document by title (for wiki links)"""
        return await self.document_repo.get_by_title(title)
    
    async def list_documents(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Document]:
        """List all documents with pagination"""
        return await self.document_repo.get_all(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
    
    async def search_documents(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Document]:
        """Search documents by title"""
        return await self.document_repo.search_by_title(query, limit)
    
    async def get_documents_by_tag(
        self,
        tag: str,
        limit: int = 50,
    ) -> List[Document]:
        """Get documents by tag"""
        return await self.document_repo.get_by_tag(tag, limit)
    
    async def index_document(self, doc_id: str) -> bool:
        """
        Index a document: chunk, embed, and store in vector DB
        
        This is the core RAG preparation step.
        Uses delayed deletion strategy to prevent race conditions:
        1. Generate new chunks and embeddings first
        2. Then atomically delete old + insert new
        """
        document = await self.document_repo.get_by_id(doc_id)
        if not document:
            logger.warning("index_document_not_found", doc_id=doc_id)
            return False
        
        try:
            document.status = DocumentStatus.PROCESSING
            await self.document_repo.update(document)
            
            # Generate summary if enabled
            if self.enable_summarization and self.llm_service and len(document.content) > 200:
                try:
                    document.summary = await self.llm_service.generate_summary(
                        document.content[:4000],  # Limit context
                        max_length=150,
                    )
                except Exception as e:
                    logger.warning("summary_generation_failed", doc_id=doc_id, error=str(e))
            
            # Auto-generate tags if enabled
            if self.enable_auto_tagging and self.llm_service and len(document.tags) < 3:
                try:
                    auto_tags = await self.llm_service.generate_tags(
                        document.content[:2000],
                        max_tags=5,
                    )
                    document.tags = list(set(document.tags + auto_tags))
                except Exception as e:
                    logger.warning("auto_tagging_failed", doc_id=doc_id, error=str(e))
            
            # Step 1: Generate new chunks (before deleting old ones)
            if hasattr(self.document_processor, 'chunk_text_async'):
                text_chunks = await self.document_processor.chunk_text_async(document.content)
            else:
                text_chunks = self.document_processor.chunk_text(document.content)
            
            if not text_chunks:
                # No content to index, just clean up old chunks
                await self.chunk_repo.delete_by_document(doc_id)
                await self.vector_store.delete_by_document(doc_id)
                document.mark_indexed()
                await self.document_repo.update(document)
                return True
            
            # Step 2: Create new chunk entities
            new_chunks = []
            for tc in text_chunks:
                chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    content=tc.content,
                    chunk_index=tc.chunk_index,
                    start_char=tc.start_char,
                    end_char=tc.end_char,
                )
                new_chunks.append(chunk)
            
            # Step 3: Generate embeddings for new chunks (before deleting old)
            chunk_texts = [c.content for c in new_chunks]
            embeddings = await self.embedding_service.embed_texts(chunk_texts)
            
            # Prepare metadata
            metadatas = [
                {
                    "document_id": doc_id,
                    "document_title": document.title,
                    "chunk_index": c.chunk_index,
                    "tags": ",".join(document.tags),
                }
                for c in new_chunks
            ]
            
            # Step 4: Atomic replacement - delete old + insert new
            # Delete old chunks and vectors (now that new ones are ready)
            await self.chunk_repo.delete_by_document(doc_id)
            await self.vector_store.delete_by_document(doc_id)
            
            # Insert new chunks to database
            await self.chunk_repo.create_many(new_chunks)
            
            # Insert new vectors to ChromaDB
            await self.vector_store.add_documents(
                ids=[c.id for c in new_chunks],
                embeddings=embeddings,
                documents=chunk_texts,
                metadatas=metadatas,
            )
            
            # Mark as indexed
            document.mark_indexed()
            await self.document_repo.update(document)
            
            logger.info(
                "document_indexed",
                doc_id=doc_id,
                chunks=len(new_chunks),
                tags=document.tags,
            )
            return True
            
        except Exception as e:
            logger.error("document_indexing_failed", doc_id=doc_id, error=str(e))
            document.mark_failed()
            await self.document_repo.update(document)
            raise
    
    async def get_linked_documents(self, doc_id: str) -> Dict[str, List[Document]]:
        """Get documents linked to/from this document"""
        return await self.document_repo.get_linked_documents(doc_id)
    
    async def _update_incoming_links(self, document: Document) -> None:
        """Update incoming links for all documents linked from this one"""
        for link_title in document.outgoing_links:
            linked_doc = await self.document_repo.get_by_title(link_title)
            if linked_doc:
                linked_doc.add_incoming_link(document.id)
                await self.document_repo.update(linked_doc)
    
    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get document statistics"""
        total_docs = await self.document_repo.count(user_id)
        vector_stats = await self.vector_store.get_collection_stats()
        all_tags = await self.tag_repo.get_all()
        
        return {
            "total_documents": total_docs,
            "total_chunks": vector_stats.get("count", 0),
            "total_tags": len(all_tags),
            "top_tags": [
                {"name": t.name, "count": t.document_count}
                for t in sorted(all_tags, key=lambda x: x.document_count, reverse=True)[:10]
            ],
        }
