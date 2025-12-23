"""
Document Processing Service
Handles document parsing, chunking, and link extraction
"""
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


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


def create_document_processor(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> DocumentProcessor:
    """Factory function for document processor"""
    return DocumentProcessor(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
