"""
Application Configuration Module
Centralized configuration management using Pydantic Settings
"""
from functools import lru_cache
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "Knowledge Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/knowledge.db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # LLM Configuration
    default_llm_provider: Literal["openai", "anthropic", "ollama", "qwen", "deepseek"] = "ollama"
    default_llm_model: str = "llama3.2"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_base_url: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    
    # Qwen
    qwen_api_key: Optional[str] = None
    qwen_model: str = "qwen-turbo"
    
    # DeepSeek
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    
    # Embedding
    embedding_provider: Literal["local", "openai", "ollama"] = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"  # Lightweight model for low-memory servers (~100MB)
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_embedding_model: str = "bge-m3"
    
    # Vector Store
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "knowledge_base"
    
    # Document Processing
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_file_size_mb: int = 50
    
    # Semantic Chunking (embedding-based)
    semantic_chunking_enabled: bool = True
    semantic_similarity_threshold: float = 0.5  # Cosine similarity cutoff
    semantic_min_chunk_size: int = 100
    
    # Vault (Obsidian-style local .md file storage)
    vault_path: str = "./vault"
    
    # Authentication
    enable_auth: bool = False
    jwt_secret_key: str = "jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    # Features
    enable_streaming: bool = True
    enable_hybrid_search: bool = True
    enable_auto_tagging: bool = True
    enable_summarization: bool = True
    
    def get_llm_config(self, provider: Optional[str] = None) -> dict:
        """Get LLM configuration for specified provider"""
        provider = provider or self.default_llm_provider
        
        configs = {
            "openai": {
                "model": f"openai/{self.openai_model}",
                "api_key": self.openai_api_key,
                "api_base": self.openai_base_url,
            },
            "anthropic": {
                "model": f"anthropic/{self.anthropic_model}",
                "api_key": self.anthropic_api_key,
            },
            "ollama": {
                "model": f"ollama/{self.ollama_model}",
                "api_base": self.ollama_base_url,
            },
            "qwen": {
                "model": f"qwen/{self.qwen_model}",
                "api_key": self.qwen_api_key,
            },
            "deepseek": {
                "model": f"deepseek/{self.deepseek_model}",
                "api_key": self.deepseek_api_key,
            },
        }
        
        return configs.get(provider, configs["ollama"])


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Convenience alias
settings = get_settings()
