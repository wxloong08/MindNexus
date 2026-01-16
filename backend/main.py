"""
Knowledge Assistant - Main Application Entry Point

Enterprise-grade personal knowledge management system with RAG capabilities.

Features:
- Document management with wiki-style linking
- Semantic search using vector embeddings
- RAG-powered conversational AI
- Multi-LLM support (OpenAI, Anthropic, Ollama, etc.)
- Auto-tagging and summarization
"""
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import structlog

from config.settings import get_settings
from src.infrastructure.database.connection import init_db, get_db_manager

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    settings = get_settings()
    
    # Startup
    logger.info("application_starting", app_name=settings.app_name, version=settings.app_version)
    
    # Initialize database
    db = init_db(settings.database_url)
    await db.create_tables()
    logger.info("database_initialized", url=settings.database_url)
    
    # Create data directories
    os.makedirs("./data/uploads", exist_ok=True)
    os.makedirs("./data/chroma", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("application_shutting_down")
    
    # Shutdown thread/process pools for document processing
    from src.infrastructure.document_processing.processor import shutdown_executors
    shutdown_executors()
    
    await get_db_manager().close()


def create_app() -> FastAPI:
    """
    Application factory
    Creates and configures the FastAPI application
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description=__doc__,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and register routes
    from src.presentation.api.system_routes import router as system_router
    from src.presentation.api.document_routes import router as document_router
    from src.presentation.api.chat_routes import router as chat_router
    
    app.include_router(system_router)
    app.include_router(document_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    
    # Mount static files
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    # Serve frontend
    @app.get("/app", response_class=HTMLResponse)
    @app.get("/app/{path:path}", response_class=HTMLResponse)
    async def serve_frontend(request: Request, path: str = ""):
        """Serve the frontend application"""
        index_path = static_path / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return HTMLResponse(content="<h1>Frontend not built</h1><p>Run the frontend build process.</p>")
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
