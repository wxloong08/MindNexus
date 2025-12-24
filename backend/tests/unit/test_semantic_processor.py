"""
Unit Tests for Semantic Document Processor
Tests Markdown preprocessing and semantic chunking
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.infrastructure.document_processing.processor import (
    DocumentProcessor,
    SemanticDocumentProcessor,
    MarkdownPreprocessor,
    TextChunk,
    create_document_processor,
)


class TestMarkdownPreprocessor:
    """Test Markdown header-based splitting"""
    
    def test_split_simple_headers(self):
        """Test splitting by # and ## headers"""
        content = """# Title
Some intro text.

## Section 1
Content of section 1.

## Section 2
Content of section 2.
"""
        sections = MarkdownPreprocessor.split_by_headers(content)
        
        assert len(sections) == 3
        assert sections[0]["title"] == "Title"
        assert sections[0]["level"] == 1
        assert sections[1]["title"] == "Section 1"
        assert sections[1]["level"] == 2
        assert sections[2]["title"] == "Section 2"
        
    def test_split_nested_headers(self):
        """Test splitting with nested ### headers"""
        content = """# Main Title

## Chapter 1

### Subsection 1.1
Details here.

### Subsection 1.2
More details.

## Chapter 2
Another chapter.
"""
        sections = MarkdownPreprocessor.split_by_headers(content)
        
        assert len(sections) == 5
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2
        assert sections[2]["level"] == 3
        assert sections[3]["level"] == 3
        assert sections[4]["level"] == 2
    
    def test_no_headers(self):
        """Test content without headers returns single section"""
        content = "Just plain text without any headers."
        sections = MarkdownPreprocessor.split_by_headers(content)
        
        assert len(sections) == 1
        assert sections[0]["title"] == ""
        assert sections[0]["level"] == 0
    
    def test_empty_content(self):
        """Test empty content handling"""
        sections = MarkdownPreprocessor.split_by_headers("")
        
        assert len(sections) == 1
        assert sections[0]["content"] == ""
    
    def test_start_char_tracking(self):
        """Test that start_char positions are tracked correctly"""
        content = """# First
Content A.

# Second
Content B.
"""
        sections = MarkdownPreprocessor.split_by_headers(content)
        
        assert sections[0]["start_char"] == 0
        assert sections[1]["start_char"] > 0


class TestSemanticDocumentProcessor:
    """Test SemanticDocumentProcessor"""
    
    @pytest.fixture
    def mock_embedding_fn(self):
        """Mock embedding function"""
        async def embed(texts):
            # Return mock embeddings (dimension 3 for simplicity)
            return [[0.1, 0.2, 0.3] for _ in texts]
        return embed
    
    def test_fallback_to_recursive_split(self, mock_embedding_fn):
        """Test that processor falls back when SemanticChunker unavailable"""
        processor = SemanticDocumentProcessor(
            embedding_function=mock_embedding_fn,
            similarity_threshold=0.5,
            min_chunk_size=50,
        )
        
        # Force chunker to be None (simulating import failure)
        processor._semantic_chunker = None
        
        content = "This is a test. " * 20  # Make it long enough
        chunks = processor.chunk_text(content)
        
        assert len(chunks) > 0
        assert all(isinstance(c, TextChunk) for c in chunks)
    
    def test_short_content_single_chunk(self, mock_embedding_fn):
        """Test short content returns single chunk"""
        processor = SemanticDocumentProcessor(
            embedding_function=mock_embedding_fn,
            min_chunk_size=100,
        )
        
        content = "Short text."
        chunks = processor.chunk_text(content)
        
        assert len(chunks) == 1
        assert chunks[0].content == content
    
    def test_empty_content(self, mock_embedding_fn):
        """Test empty content returns empty list"""
        processor = SemanticDocumentProcessor(
            embedding_function=mock_embedding_fn,
        )
        
        chunks = processor.chunk_text("")
        assert chunks == []
    
    def test_section_metadata(self, mock_embedding_fn):
        """Test that chunks include section metadata"""
        processor = SemanticDocumentProcessor(
            embedding_function=mock_embedding_fn,
            min_chunk_size=10,
        )
        # Force fallback
        processor._semantic_chunker = None
        
        content = """# Introduction
This is the intro section.

# Methods
This describes the methods.
"""
        chunks = processor.chunk_text(content)
        
        # Should have chunks with section metadata
        assert len(chunks) >= 2


class TestCreateDocumentProcessor:
    """Test factory function"""
    
    def test_create_standard_processor(self):
        """Test creating standard DocumentProcessor"""
        processor = create_document_processor(
            chunk_size=500,
            chunk_overlap=50,
        )
        
        assert isinstance(processor, DocumentProcessor)
        assert not isinstance(processor, SemanticDocumentProcessor)
    
    def test_create_semantic_processor(self):
        """Test creating SemanticDocumentProcessor"""
        async def mock_embed(texts):
            return [[0.1] * 3 for _ in texts]
        
        processor = create_document_processor(
            chunk_size=500,
            chunk_overlap=50,
            semantic_enabled=True,
            similarity_threshold=0.5,
            embedding_function=mock_embed,
        )
        
        assert isinstance(processor, SemanticDocumentProcessor)
    
    def test_semantic_without_embedding_fn_fallback(self):
        """Test semantic mode falls back without embedding function"""
        processor = create_document_processor(
            semantic_enabled=True,
            embedding_function=None,  # No embedding function
        )
        
        # Should fall back to standard processor
        assert isinstance(processor, DocumentProcessor)
        assert not isinstance(processor, SemanticDocumentProcessor)
