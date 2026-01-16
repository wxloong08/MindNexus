"""
Document Processing Service
Handles document parsing, chunking, and link extraction
"""
import re
import asyncio
from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
import structlog

logger = structlog.get_logger()

# Global executors for concurrent processing
# ThreadPool: For embedding (C extensions release GIL)
# ProcessPool: For pure Python CPU-intensive work
_thread_executor: Optional[ThreadPoolExecutor] = None
_process_executor: Optional[ProcessPoolExecutor] = None

def get_thread_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get or create thread pool executor"""
    global _thread_executor
    if _thread_executor is None:
        _thread_executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info("thread_pool_created", max_workers=max_workers)
    return _thread_executor

def get_process_executor(max_workers: int = 2) -> ProcessPoolExecutor:
    """Get or create process pool executor"""
    global _process_executor
    if _process_executor is None:
        _process_executor = ProcessPoolExecutor(max_workers=max_workers)
        logger.info("process_pool_created", max_workers=max_workers)
    return _process_executor

def shutdown_executors():
    """Shutdown executors gracefully (call on app shutdown)"""
    global _thread_executor, _process_executor
    if _thread_executor:
        _thread_executor.shutdown(wait=True)
        _thread_executor = None
    if _process_executor:
        _process_executor.shutdown(wait=True)
        _process_executor = None
    logger.info("executors_shutdown")


@dataclass
class TextChunk:
    """A chunk of text with metadata"""
    content: str
    start_char: int
    end_char: int
    chunk_index: int
    metadata: Dict[str, Any] = None


class DocumentProcessor:
    """
    Document processing utilities
    
    Features:
    - Multiple chunking strategies
    - Wiki-link extraction ([[link]])
    - Markdown parsing
    - Metadata extraction
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks
        Uses recursive character splitting for better semantic boundaries
        
        Args:
            text: Text to chunk
            chunk_size: Override default chunk size
            chunk_overlap: Override default overlap
        
        Returns:
            List of TextChunk objects
        """
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        if not text or len(text) < self.min_chunk_size:
            if text:
                return [TextChunk(
                    content=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                )]
            return []
        
        # Separators in order of preference
        separators = ["\n\n", "\n", ". ", "。", "! ", "? ", "; ", ", ", " ", ""]
        
        chunks = self._recursive_split(text, separators, chunk_size)
        
        # Create overlapping chunks
        result = []
        for i, chunk in enumerate(chunks):
            # Add overlap from previous chunk
            if i > 0 and chunk_overlap > 0:
                prev_chunk = chunks[i - 1]
                overlap_text = prev_chunk[-chunk_overlap:] if len(prev_chunk) > chunk_overlap else prev_chunk
                chunk = overlap_text + chunk
            
            # Find position in original text
            start_char = text.find(chunk[:50])  # Use first 50 chars to find position
            if start_char == -1:
                start_char = 0
            end_char = start_char + len(chunk)
            
            result.append(TextChunk(
                content=chunk,
                start_char=start_char,
                end_char=end_char,
                chunk_index=i,
            ))
        
        return result
    
    def _recursive_split(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
    ) -> List[str]:
        """Recursively split text using separators"""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []
        
        # Find the best separator to use
        separator = separators[-1]  # Default to empty string
        for sep in separators:
            if sep in text:
                separator = sep
                break
        
        # Split by separator
        if separator:
            splits = text.split(separator)
        else:
            # Character-level split as last resort
            splits = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        # Merge small splits
        chunks = []
        current_chunk = ""
        
        for split in splits:
            if not split.strip():
                continue
            
            test_chunk = current_chunk + separator + split if current_chunk else split
            
            if len(test_chunk) <= chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If split itself is too large, recurse
                if len(split) > chunk_size and len(separators) > 1:
                    sub_chunks = self._recursive_split(
                        split,
                        separators[1:],  # Try next separator
                        chunk_size,
                    )
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""
                else:
                    current_chunk = split
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def chunk_with_parents(
        self,
        text: str,
        parent_chunk_size: int = 2000,
        child_chunk_size: int = 400,
        child_overlap: int = 50,
    ) -> Tuple[List[TextChunk], List[TextChunk]]:
        """
        Create parent-child chunk hierarchy
        Good for retrieval: search on small chunks, return larger context
        
        Returns:
            Tuple of (parent_chunks, child_chunks)
        """
        # Create parent chunks
        parent_chunks = self.chunk_text(
            text,
            chunk_size=parent_chunk_size,
            chunk_overlap=0,  # No overlap for parents
        )
        
        # Create child chunks within each parent
        child_chunks = []
        for parent in parent_chunks:
            children = self.chunk_text(
                parent.content,
                chunk_size=child_chunk_size,
                chunk_overlap=child_overlap,
            )
            
            # Adjust positions relative to original text
            for child in children:
                child.start_char += parent.start_char
                child.end_char = child.start_char + len(child.content)
                child.metadata = {"parent_index": parent.chunk_index}
            
            child_chunks.extend(children)
        
        return parent_chunks, child_chunks
    
    def extract_wiki_links(self, content: str) -> List[str]:
        """
        Extract wiki-style links from content
        Supports: [[Page Name]], [[Page Name|Display Text]]
        
        Returns:
            List of linked page names
        """
        # Pattern: [[page_name]] or [[page_name|display_text]]
        pattern = r'\[\[([^\|\]]+)(?:\|[^\]]+)?\]\]'
        matches = re.findall(pattern, content)
        
        # Clean and deduplicate
        links = []
        for match in matches:
            link = match.strip()
            if link and link not in links:
                links.append(link)
        
        return links
    
    def extract_tags_from_content(self, content: str) -> List[str]:
        """
        Extract hashtag-style tags from content
        Supports: #tag, #multi-word-tag
        """
        # Pattern: #tag (alphanumeric and hyphens)
        pattern = r'#([a-zA-Z0-9\u4e00-\u9fa5][\w\-]*)'
        matches = re.findall(pattern, content)
        
        # Clean and deduplicate
        tags = []
        for match in matches:
            tag = match.lower().strip()
            if tag and tag not in tags:
                tags.append(tag)
        
        return tags
    
    def extract_title_from_markdown(self, content: str) -> Optional[str]:
        """Extract title from first H1 heading in markdown"""
        lines = content.strip().split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return None
    
    def extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract YAML frontmatter from markdown
        
        Returns:
            Tuple of (metadata dict, content without frontmatter)
        """
        if not content.startswith('---'):
            return {}, content
        
        # Find closing ---
        end_match = re.search(r'\n---\s*\n', content[3:])
        if not end_match:
            return {}, content
        
        frontmatter_end = end_match.end() + 3
        frontmatter_str = content[3:end_match.start() + 3]
        remaining_content = content[frontmatter_end:]
        
        # Parse YAML
        try:
            import yaml
            metadata = yaml.safe_load(frontmatter_str) or {}
        except Exception:
            metadata = {}
        
        return metadata, remaining_content
    
    def render_markdown_to_html(self, content: str) -> str:
        """Convert markdown to HTML"""
        try:
            import mistune
            markdown = mistune.create_markdown(
                escape=False,
                plugins=['strikethrough', 'table']
            )
            return markdown(content)
        except ImportError:
            # Fallback to basic markdown
            import markdown
            return markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    def count_words(self, text: str) -> int:
        """Count words in text (supports CJK)"""
        # Remove markdown syntax
        clean = re.sub(r'[#*_`\[\]()]', ' ', text)
        
        # Count CJK characters as words
        cjk_count = len(re.findall(r'[\u4e00-\u9fa5\u3040-\u309f\u30a0-\u30ff]', clean))
        
        # Count space-separated words
        word_count = len(clean.split())
        
        return word_count + cjk_count


class FileParser:
    """
    File content parser for different formats
    """
    
    @staticmethod
    def parse_text(content: str) -> str:
        """Parse plain text (no-op)"""
        return content
    
    @staticmethod
    def parse_markdown(content: str) -> str:
        """Parse markdown file"""
        return content
    
    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """Parse PDF file"""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("pdf_parse_error", path=file_path, error=str(e))
            raise
    
    @staticmethod
    def parse_docx(file_path: str) -> str:
        """Parse DOCX file"""
        try:
            from docx import Document
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(paragraphs)
        except Exception as e:
            logger.error("docx_parse_error", path=file_path, error=str(e))
            raise
    
    @staticmethod
    def parse_html(content: str) -> str:
        """Parse HTML and extract text"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            return soup.get_text(separator='\n', strip=True)
        except Exception as e:
            logger.error("html_parse_error", error=str(e))
            raise


class MarkdownPreprocessor:
    """
    Preprocess Markdown by splitting on header boundaries
    Preserves document structure before semantic chunking
    """
    
    @staticmethod
    def split_by_headers(content: str) -> List[Dict[str, Any]]:
        """
        Split Markdown content by headers (# ## ###)
        
        Returns:
            List of sections with title, level, content, start_char
        """
        # Pattern matches # ## ### etc at start of line
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        sections = []
        lines = content.split('\n')
        current_section = {
            "title": "",
            "level": 0,
            "content": "",
            "start_char": 0,
        }
        current_char = 0
        
        for line in lines:
            match = re.match(header_pattern, line)
            
            if match:
                # Save previous section if has content
                if current_section["content"].strip():
                    sections.append(current_section)
                
                # Start new section
                level = len(match.group(1))
                title = match.group(2).strip()
                current_section = {
                    "title": title,
                    "level": level,
                    "content": line + "\n",
                    "start_char": current_char,
                }
            else:
                current_section["content"] += line + "\n"
            
            current_char += len(line) + 1  # +1 for newline
        
        # Don't forget last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        # If no headers found, return entire content as one section
        if not sections:
            sections.append({
                "title": "",
                "level": 0,
                "content": content,
                "start_char": 0,
            })
        
        return sections


class SemanticDocumentProcessor(DocumentProcessor):
    """
    Semantic document chunking using embedding similarity
    
    Strategy:
    1. Preprocess Markdown by splitting on headers
    2. Within each section, use LangChain SemanticChunker
    3. Merge small chunks, respect min_chunk_size
    
    This preserves document structure while ensuring
    semantically coherent chunks for better RAG retrieval.
    """
    
    def __init__(
        self,
        embedding_function: Any,
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 100,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        super().__init__(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
        )
        self.embedding_function = embedding_function
        self.similarity_threshold = similarity_threshold
        self._semantic_chunker = None
        
        logger.info(
            "semantic_processor_initialized",
            similarity_threshold=similarity_threshold,
            min_chunk_size=min_chunk_size,
        )
    
    def _get_semantic_chunker(self):
        """Lazy initialization of SemanticChunker"""
        if self._semantic_chunker is None:
            try:
                from langchain_text_splitters import SemanticChunker
                from langchain_core.embeddings import Embeddings
                
                # Wrap our embedding function for LangChain compatibility
                class EmbeddingWrapper(Embeddings):
                    def __init__(wrapper_self, embed_fn):
                        wrapper_self.embed_fn = embed_fn
                    
                    def embed_documents(wrapper_self, texts: List[str]) -> List[List[float]]:
                        """Embed documents - sync wrapper for async function"""
                        import asyncio
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Already in async context, create new loop
                                import concurrent.futures
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(
                                        asyncio.run,
                                        wrapper_self.embed_fn(texts)
                                    )
                                    return future.result()
                            else:
                                return loop.run_until_complete(wrapper_self.embed_fn(texts))
                        except RuntimeError:
                            return asyncio.run(wrapper_self.embed_fn(texts))
                    
                    def embed_query(wrapper_self, text: str) -> List[float]:
                        """Embed single query"""
                        results = wrapper_self.embed_documents([text])
                        return results[0] if results else []
                
                embeddings = EmbeddingWrapper(self.embedding_function)
                
                # Configure SemanticChunker
                # breakpoint_threshold_type: "percentile" works well
                # Lower percentile = more aggressive splitting
                self._semantic_chunker = SemanticChunker(
                    embeddings=embeddings,
                    breakpoint_threshold_type="percentile",
                    breakpoint_threshold_amount=int(self.similarity_threshold * 100),
                )
                
                logger.info("semantic_chunker_created")
                
            except ImportError as e:
                logger.warning(
                    "semantic_chunker_import_failed",
                    error=str(e),
                    fallback="using recursive character split",
                )
                return None
        
        return self._semantic_chunker
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[TextChunk]:
        """
        Semantic chunking with Markdown preprocessing
        
        Flow:
        1. Split by Markdown headers
        2. Semantic chunk each section
        3. Build TextChunk objects with positions
        """
        if not text or len(text) < self.min_chunk_size:
            if text:
                return [TextChunk(
                    content=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                )]
            return []
        
        # Step 1: Markdown preprocessing
        sections = MarkdownPreprocessor.split_by_headers(text)
        logger.debug("markdown_sections_split", count=len(sections))
        
        # Step 2: Semantic chunking per section
        chunker = self._get_semantic_chunker()
        all_chunks = []
        chunk_index = 0
        
        for section in sections:
            section_content = section["content"]
            section_start = section["start_char"]
            
            # Skip very short sections
            if len(section_content.strip()) < self.min_chunk_size:
                if section_content.strip():
                    all_chunks.append(TextChunk(
                        content=section_content.strip(),
                        start_char=section_start,
                        end_char=section_start + len(section_content),
                        chunk_index=chunk_index,
                        metadata={"section_title": section["title"]},
                    ))
                    chunk_index += 1
                continue
            
            if chunker:
                try:
                    # Use SemanticChunker
                    semantic_docs = chunker.split_text(section_content)
                    
                    for doc_text in semantic_docs:
                        # Find position in original text
                        start = text.find(doc_text[:50])
                        if start == -1:
                            start = section_start
                        
                        all_chunks.append(TextChunk(
                            content=doc_text,
                            start_char=start,
                            end_char=start + len(doc_text),
                            chunk_index=chunk_index,
                            metadata={"section_title": section["title"]},
                        ))
                        chunk_index += 1
                    
                except Exception as e:
                    logger.warning(
                        "semantic_chunk_failed",
                        section=section["title"],
                        error=str(e),
                    )
                    # Fallback to parent's recursive split
                    fallback_chunks = super().chunk_text(
                        section_content,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                    for fc in fallback_chunks:
                        fc.chunk_index = chunk_index
                        fc.start_char += section_start
                        fc.end_char = fc.start_char + len(fc.content)
                        fc.metadata = {"section_title": section["title"]}
                        all_chunks.append(fc)
                        chunk_index += 1
            else:
                # No SemanticChunker available, use fallback
                fallback_chunks = super().chunk_text(
                    section_content,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                for fc in fallback_chunks:
                    fc.chunk_index = chunk_index
                    fc.start_char += section_start
                    fc.end_char = fc.start_char + len(fc.content)
                    fc.metadata = {"section_title": section["title"]}
                    all_chunks.append(fc)
                    chunk_index += 1
        
        logger.info(
            "semantic_chunking_complete",
            total_chunks=len(all_chunks),
            sections=len(sections),
        )
        
        return all_chunks
    
    async def chunk_text_async(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[TextChunk]:
        """
        Async version of chunk_text using thread pool for embedding computation.
        
        This method runs CPU-intensive embedding calculations in a thread pool,
        allowing the event loop to handle other requests.
        
        Note: Thread pool is effective because embedding libraries (PyTorch,
        sentence-transformers) release the GIL during C/CUDA operations.
        """
        if not text or len(text) < self.min_chunk_size:
            if text:
                return [TextChunk(
                    content=text,
                    start_char=0,
                    end_char=len(text),
                    chunk_index=0,
                )]
            return []
        
        # Markdown preprocessing is fast (pure Python but simple)
        sections = MarkdownPreprocessor.split_by_headers(text)
        logger.debug("markdown_sections_split_async", count=len(sections))
        
        # Process sections concurrently using thread pool
        loop = asyncio.get_event_loop()
        executor = get_thread_executor()
        
        all_chunks = []
        chunk_index = 0
        
        # Process each section - embedding computation happens in thread pool
        for section in sections:
            section_content = section["content"]
            section_start = section["start_char"]
            
            # Skip very short sections
            if len(section_content.strip()) < self.min_chunk_size:
                if section_content.strip():
                    all_chunks.append(TextChunk(
                        content=section_content.strip(),
                        start_char=section_start,
                        end_char=section_start + len(section_content),
                        chunk_index=chunk_index,
                        metadata={"section_title": section["title"]},
                    ))
                    chunk_index += 1
                continue
            
            # Run semantic chunking in thread pool
            try:
                section_chunks = await loop.run_in_executor(
                    executor,
                    self._chunk_section_sync,
                    section_content,
                    section["title"],
                    text,
                    section_start,
                )
                
                for chunk in section_chunks:
                    chunk.chunk_index = chunk_index
                    all_chunks.append(chunk)
                    chunk_index += 1
                    
            except Exception as e:
                logger.warning(
                    "async_semantic_chunk_failed",
                    section=section["title"],
                    error=str(e),
                )
                # Fallback to recursive split
                fallback_chunks = super().chunk_text(
                    section_content,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                for fc in fallback_chunks:
                    fc.chunk_index = chunk_index
                    fc.start_char += section_start
                    fc.end_char = fc.start_char + len(fc.content)
                    fc.metadata = {"section_title": section["title"]}
                    all_chunks.append(fc)
                    chunk_index += 1
        
        logger.info(
            "async_semantic_chunking_complete",
            total_chunks=len(all_chunks),
            sections=len(sections),
        )
        
        return all_chunks
    
    def _chunk_section_sync(
        self,
        section_content: str,
        section_title: str,
        original_text: str,
        section_start: int,
    ) -> List[TextChunk]:
        """
        Synchronous helper for chunking a single section.
        Called from thread pool in async context.
        """
        chunker = self._get_semantic_chunker()
        chunks = []
        
        if chunker:
            try:
                semantic_docs = chunker.split_text(section_content)
                
                for doc_text in semantic_docs:
                    start = original_text.find(doc_text[:50])
                    if start == -1:
                        start = section_start
                    
                    chunks.append(TextChunk(
                        content=doc_text,
                        start_char=start,
                        end_char=start + len(doc_text),
                        chunk_index=0,  # Will be set by caller
                        metadata={"section_title": section_title},
                    ))
            except Exception:
                # Will be caught by caller
                raise
        else:
            # Return empty, caller will use fallback
            raise RuntimeError("SemanticChunker not available")
        
        return chunks


def create_document_processor(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    semantic_enabled: bool = False,
    similarity_threshold: float = 0.5,
    min_chunk_size: int = 100,
    embedding_function: Any = None,
) -> DocumentProcessor:
    """
    Factory function for document processor
    
    Args:
        chunk_size: Max characters per chunk
        chunk_overlap: Overlap between chunks
        semantic_enabled: Use embedding-based semantic chunking
        similarity_threshold: Cosine similarity cutoff (0-1)
        min_chunk_size: Minimum chunk size
        embedding_function: Async function to generate embeddings
    
    Returns:
        DocumentProcessor or SemanticDocumentProcessor
    """
    if semantic_enabled and embedding_function is not None:
        logger.info("creating_semantic_document_processor")
        return SemanticDocumentProcessor(
            embedding_function=embedding_function,
            similarity_threshold=similarity_threshold,
            min_chunk_size=min_chunk_size,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    else:
        logger.info("creating_standard_document_processor")
        return DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

