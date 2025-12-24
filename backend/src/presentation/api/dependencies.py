"""
FastAPI Dependency Injection
Provides use cases and services as dependencies
"""
from typing import AsyncGenerator
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import Settings, get_settings
from src.infrastructure.database.connection import get_session
from src.infrastructure.database.repositories import (
    SQLAlchemyDocumentRepository,
    SQLAlchemyChunkRepository,
    SQLAlchemyTagRepository,
    SQLAlchemyConversationRepository,
    SQLAlchemyMessageRepository,
)
from src.infrastructure.llm.service import LLMService, create_llm_service
from src.infrastructure.embedding.service import EmbeddingService, create_embedding_service
from src.infrastructure.vector_store.chroma_store import ChromaVectorStore, create_vector_store
from src.infrastructure.document_processing.processor import DocumentProcessor, create_document_processor
from src.infrastructure.vault.service import VaultService
from src.application.use_cases.document_use_case import DocumentUseCase
from src.application.use_cases.chat_use_case import ChatUseCase


# ============== Cached Service Instances ==============

@lru_cache()
def get_llm_service() -> LLMService:
    """Get cached LLM service instance"""
    settings = get_settings()
    return create_llm_service(
        default_provider=settings.default_llm_provider,
        default_model=settings.default_llm_model,
        openai_api_key=settings.openai_api_key,
        anthropic_api_key=settings.anthropic_api_key,
        ollama_base_url=settings.ollama_base_url,
        qwen_api_key=settings.qwen_api_key,
        deepseek_api_key=settings.deepseek_api_key,
    )


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get cached embedding service instance"""
    settings = get_settings()
    return create_embedding_service(
        provider=settings.embedding_provider,
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
        ollama_base_url=settings.ollama_base_url,
    )


@lru_cache()
def get_vector_store() -> ChromaVectorStore:
    """Get cached vector store instance"""
    settings = get_settings()
    return create_vector_store(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.chroma_collection_name,
    )


@lru_cache()
def get_document_processor() -> DocumentProcessor:
    """Get cached document processor instance"""
    settings = get_settings()
    
    if settings.semantic_chunking_enabled:
        # Get embedding service for semantic chunking
        embedding_service = get_embedding_service()
        return create_document_processor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            semantic_enabled=True,
            similarity_threshold=settings.semantic_similarity_threshold,
            min_chunk_size=settings.semantic_min_chunk_size,
            embedding_function=embedding_service.embed_texts,
        )
    else:
        return create_document_processor(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )


# ============== Use Case Dependencies ==============

async def get_document_use_case(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[DocumentUseCase, None]:
    """
    Provide DocumentUseCase with all dependencies injected
    """
    settings = get_settings()
    
    # Create repositories (session-scoped)
    document_repo = SQLAlchemyDocumentRepository(session)
    chunk_repo = SQLAlchemyChunkRepository(session)
    tag_repo = SQLAlchemyTagRepository(session)
    
    # Get cached services
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    document_processor = get_document_processor()
    llm_service = get_llm_service()
    
    use_case = DocumentUseCase(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        tag_repo=tag_repo,
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_processor=document_processor,
        llm_service=llm_service,
        vault_service=VaultService(vault_path=settings.vault_path),  # Obsidian-style .md files
        enable_auto_tagging=settings.enable_auto_tagging,
        enable_summarization=settings.enable_summarization,
    )
    
    yield use_case


async def get_chat_use_case(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[ChatUseCase, None]:
    """
    Provide ChatUseCase with all dependencies injected
    """
    settings = get_settings()
    
    # Create repositories (session-scoped)
    conversation_repo = SQLAlchemyConversationRepository(session)
    message_repo = SQLAlchemyMessageRepository(session)
    document_repo = SQLAlchemyDocumentRepository(session)
    
    # Get cached services
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    llm_service = get_llm_service()
    
    use_case = ChatUseCase(
        conversation_repo=conversation_repo,
        message_repo=message_repo,
        document_repo=document_repo,
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_service=llm_service,
        enable_streaming=settings.enable_streaming,
        enable_hybrid_search=settings.enable_hybrid_search,
    )
    
    yield use_case
