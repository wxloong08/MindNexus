"""
System API Routes
Health checks, tags, and system statistics
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from src.infrastructure.database.connection import get_session
from src.infrastructure.database.repositories import SQLAlchemyTagRepository
from src.presentation.schemas.api_schemas import (
    HealthResponse,
    StatsResponse,
    TagListResponse,
    TagResponse,
)
from src.presentation.api.dependencies import (
    get_document_use_case,
    get_llm_service,
    get_vector_store,
)
from src.application.use_cases.document_use_case import DocumentUseCase

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    session: AsyncSession = Depends(get_session),
):
    """
    Health check endpoint
    
    Returns status of all system components.
    """
    settings = get_settings()
    
    # Check database
    db_status = "healthy"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check vector store
    vector_store = get_vector_store()
    try:
        vector_stats = await vector_store.get_collection_stats()
    except Exception as e:
        vector_stats = {"status": "unhealthy", "error": str(e)}
    
    # Check LLM (lightweight check)
    llm_service = get_llm_service()
    llm_status = {
        "default_model": llm_service.default_model,
        "status": "configured",
    }
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        version=settings.app_version,
        database=db_status,
        vector_store=vector_stats,
        llm=llm_status,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    use_case: DocumentUseCase = Depends(get_document_use_case),
):
    """
    Get system statistics
    
    Returns document counts, tags, and other metrics.
    """
    stats = await use_case.get_stats()
    return StatsResponse(**stats)


@router.get("/tags", response_model=TagListResponse)
async def list_tags(
    session: AsyncSession = Depends(get_session),
):
    """
    List all tags
    
    Returns all tags sorted by document count.
    """
    tag_repo = SQLAlchemyTagRepository(session)
    tags = await tag_repo.get_popular(limit=100)
    
    return TagListResponse(
        tags=[
            TagResponse(
                id=t.id,
                name=t.name,
                color=t.color,
                document_count=t.document_count,
            )
            for t in tags
        ]
    )


@router.get("/")
async def root():
    """
    API root endpoint
    """
    settings = get_settings()
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
