"""
Unit Tests for Document Use Case
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.domain.entities.document import Document, DocumentType, DocumentStatus
from src.application.use_cases.document_use_case import DocumentUseCase


@pytest.fixture
def mock_deps():
    """Create mock dependencies"""
    return {
        "document_repo": AsyncMock(),
        "chunk_repo": AsyncMock(),
        "tag_repo": AsyncMock(),
        "embedding_service": AsyncMock(),
        "vector_store": AsyncMock(),
        "document_processor": MagicMock(),
        "llm_service": AsyncMock(),
    }


@pytest.fixture
def document_use_case(mock_deps):
    """Create DocumentUseCase with mocks"""
    mock_deps["document_processor"].extract_wiki_links.return_value = []
    mock_deps["document_processor"].extract_tags_from_content.return_value = []
    mock_deps["document_processor"].count_words.return_value = 10
    
    return DocumentUseCase(
        document_repo=mock_deps["document_repo"],
        chunk_repo=mock_deps["chunk_repo"],
        tag_repo=mock_deps["tag_repo"],
        embedding_service=mock_deps["embedding_service"],
        vector_store=mock_deps["vector_store"],
        document_processor=mock_deps["document_processor"],
        llm_service=mock_deps["llm_service"],
        enable_auto_tagging=False,
        enable_summarization=False,
    )


@pytest.mark.asyncio
async def test_create_document(document_use_case, mock_deps):
    """Test document creation"""
    # Arrange
    mock_deps["document_repo"].create.return_value = Document(
        id="test-id",
        title="Test Doc",
        content="Test content",
    )
    mock_deps["tag_repo"].get_by_name.return_value = None
    
    # Act
    doc = await document_use_case.create_document(
        title="Test Doc",
        content="Test content",
        auto_index=False,
    )
    
    # Assert
    assert doc.id == "test-id"
    assert doc.title == "Test Doc"
    mock_deps["document_repo"].create.assert_called_once()


@pytest.mark.asyncio
async def test_get_document(document_use_case, mock_deps):
    """Test getting a document by ID"""
    # Arrange
    expected_doc = Document(id="test-id", title="Test", content="Content")
    mock_deps["document_repo"].get_by_id.return_value = expected_doc
    
    # Act
    doc = await document_use_case.get_document("test-id")
    
    # Assert
    assert doc == expected_doc
    mock_deps["document_repo"].get_by_id.assert_called_once_with("test-id")


@pytest.mark.asyncio
async def test_delete_document(document_use_case, mock_deps):
    """Test document deletion"""
    # Arrange
    mock_deps["document_repo"].get_by_id.return_value = Document(
        id="test-id",
        title="Test",
        content="Content",
        tags=["tag1"],
    )
    mock_deps["document_repo"].delete.return_value = True
    
    # Act
    result = await document_use_case.delete_document("test-id")
    
    # Assert
    assert result is True
    mock_deps["vector_store"].delete_by_document.assert_called_once()
    mock_deps["chunk_repo"].delete_by_document.assert_called_once()
