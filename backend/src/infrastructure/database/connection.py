"""
Database Connection Management
Async SQLAlchemy engine and session factory
"""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.infrastructure.database.models import Base


class DatabaseManager:
    """
    Database connection manager
    Handles engine creation and session management
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        
        # Ensure data directory exists for SQLite
        if "sqlite" in database_url:
            db_path = database_url.split("///")[-1]
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        
        # Create async engine
        connect_args = {}
        poolclass = None
        
        if "sqlite" in database_url:
            connect_args = {"check_same_thread": False}
            poolclass = StaticPool
        
        self.engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            connect_args=connect_args,
            poolclass=poolclass,
        )
        
        # Create session factory
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    
    async def create_tables(self) -> None:
        """Create all database tables"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session context manager
        
        Usage:
            async with db_manager.session() as session:
                # use session
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session as dependency injection
        
        Usage with FastAPI:
            @app.get("/")
            async def endpoint(session: AsyncSession = Depends(db.get_session)):
                ...
        """
        async with self.session() as session:
            yield session
    
    async def close(self) -> None:
        """Close database connection"""
        await self.engine.dispose()


# Global database manager instance (initialized in main.py)
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_manager


def init_db(database_url: str) -> DatabaseManager:
    """Initialize global database manager"""
    global _db_manager
    _db_manager = DatabaseManager(database_url)
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    db = get_db_manager()
    async for session in db.get_session():
        yield session
