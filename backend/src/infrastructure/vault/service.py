"""
Vault Service - Obsidian-style local markdown file storage
Manages a vault directory where notes are stored as .md files
"""
import os
import re
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import structlog
import yaml

logger = structlog.get_logger()


class VaultService:
    """
    Manages a local vault directory for markdown files.
    Like Obsidian, notes are stored as real .md files on disk.
    """
    
    def __init__(self, vault_path: str = "./vault"):
        self.vault_path = Path(vault_path).resolve()
        self._ensure_vault_exists()
    
    def _ensure_vault_exists(self) -> None:
        """Create vault directory if it doesn't exist"""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        logger.info("vault_initialized", path=str(self.vault_path))
    
    def _sanitize_filename(self, title: str) -> str:
        """Convert title to valid filename"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = filename.strip()
        if not filename:
            filename = "untitled"
        return filename
    
    def _generate_frontmatter(self, doc_id: str, tags: List[str], created_at: str, updated_at: str) -> str:
        """Generate YAML frontmatter for the markdown file"""
        frontmatter = {
            "id": doc_id,
            "tags": tags,
            "created": created_at,
            "updated": updated_at,
        }
        return f"---\n{yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)}---\n"
    
    def save_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        tags: List[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> str:
        """
        Save a document as a markdown file in the vault.
        Returns the file path.
        """
        filename = self._sanitize_filename(title) + ".md"
        filepath = self.vault_path / filename
        
        # Generate frontmatter
        now = datetime.utcnow().isoformat()
        frontmatter = self._generate_frontmatter(
            doc_id=doc_id,
            tags=tags or [],
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
        
        # Write file
        full_content = frontmatter + "\n" + content
        filepath.write_text(full_content, encoding="utf-8")
        
        logger.info("document_saved_to_vault", filepath=str(filepath), doc_id=doc_id)
        return str(filepath)
    
    def delete_document(self, title: str) -> bool:
        """Delete a document file from the vault"""
        filename = self._sanitize_filename(title) + ".md"
        filepath = self.vault_path / filename
        
        if filepath.exists():
            filepath.unlink()
            logger.info("document_deleted_from_vault", filepath=str(filepath))
            return True
        return False
    
    def get_document_path(self, title: str) -> Optional[str]:
        """Get the full path to a document file"""
        filename = self._sanitize_filename(title) + ".md"
        filepath = self.vault_path / filename
        return str(filepath) if filepath.exists() else None
    
    def list_documents(self) -> List[dict]:
        """List all markdown files in the vault"""
        docs = []
        for filepath in self.vault_path.glob("*.md"):
            content = filepath.read_text(encoding="utf-8")
            
            # Parse frontmatter if exists
            doc_info = {
                "filename": filepath.name,
                "path": str(filepath),
                "title": filepath.stem,
            }
            
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        doc_info.update(frontmatter)
                    except yaml.YAMLError:
                        pass
            
            docs.append(doc_info)
        
        return docs
    
    def get_vault_path(self) -> str:
        """Return the absolute path to the vault directory"""
        return str(self.vault_path)
