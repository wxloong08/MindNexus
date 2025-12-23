"""
Embedding Service Layer
Supports multiple embedding providers: local (sentence-transformers), OpenAI, Ollama
"""
from abc import ABC, abstractmethod
from typing import List, Optional
import asyncio
from functools import lru_cache

import structlog
import numpy as np

logger = structlog.get_logger()


class EmbeddingService(ABC):
    """Abstract base class for embedding services"""
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        pass


class LocalEmbeddingService(EmbeddingService):
    """
    Local embedding service using sentence-transformers
    Supports BGE-M3, all-MiniLM, and other HuggingFace models
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        normalize: bool = True,
    ):
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self._model = None
        self._dimension = None
    
    def _get_model(self):
        """Lazy load the model"""
        if self._model is None:
            try:
                # Try FlagEmbedding first for BGE models
                if "bge" in self.model_name.lower():
                    try:
                        from FlagEmbedding import FlagModel
                        self._model = FlagModel(
                            self.model_name,
                            use_fp16=False,
                        )
                        self._model_type = "flag"
                        logger.info("loaded_flag_embedding_model", model=self.model_name)
                    except ImportError:
                        pass
                
                # Fallback to sentence-transformers
                if self._model is None:
                    from sentence_transformers import SentenceTransformer
                    self._model = SentenceTransformer(
                        self.model_name,
                        device=self.device,
                    )
                    self._model_type = "sentence_transformer"
                    logger.info("loaded_sentence_transformer_model", model=self.model_name)
                
                # Get dimension
                test_embedding = self._encode_sync(["test"])
                self._dimension = len(test_embedding[0])
                
            except Exception as e:
                logger.error("failed_to_load_embedding_model", model=self.model_name, error=str(e))
                raise
        
        return self._model
    
    def _encode_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous encoding"""
        model = self._get_model()
        
        if self._model_type == "flag":
            embeddings = model.encode(texts)
        else:
            embeddings = model.encode(
                texts,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
        
        # Convert to list of lists
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return [e.tolist() if hasattr(e, 'tolist') else list(e) for e in embeddings]
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.embed_texts([text])
        return embeddings[0]
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_sync, texts)
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        if self._dimension is None:
            self._get_model()  # This will set _dimension
        return self._dimension


class OpenAIEmbeddingService(EmbeddingService):
    """
    OpenAI embedding service
    Uses text-embedding-3-small by default
    """
    
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }
    
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
    ):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimension = self.DIMENSIONS.get(model, 1536)
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        embeddings = await self.embed_texts([text])
        return embeddings[0]
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
    
    def get_dimension(self) -> int:
        return self._dimension


class OllamaEmbeddingService(EmbeddingService):
    """
    Ollama embedding service
    Uses local Ollama server for embeddings
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "bge-m3",
    ):
        import httpx
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
        self._dimension = None
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        response = await self.client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text}
        )
        response.raise_for_status()
        embedding = response.json()["embedding"]
        
        if self._dimension is None:
            self._dimension = len(embedding)
        
        return embedding
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        # Ollama doesn't support batch embeddings, so we do it sequentially
        embeddings = []
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        return embeddings
    
    def get_dimension(self) -> int:
        if self._dimension is None:
            # Get dimension by making a test request
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.embed_text("test"))
        return self._dimension


def create_embedding_service(
    provider: str = "local",
    model: str = "BAAI/bge-m3",
    openai_api_key: Optional[str] = None,
    ollama_base_url: str = "http://localhost:11434",
) -> EmbeddingService:
    """
    Factory function to create embedding service
    
    Args:
        provider: "local", "openai", or "ollama"
        model: Model name/path
        openai_api_key: OpenAI API key (required for openai provider)
        ollama_base_url: Ollama server URL
    
    Returns:
        Configured EmbeddingService instance
    """
    if provider == "openai":
        if not openai_api_key:
            raise ValueError("OpenAI API key required for openai embedding provider")
        return OpenAIEmbeddingService(
            api_key=openai_api_key,
            model=model,
        )
    elif provider == "ollama":
        return OllamaEmbeddingService(
            base_url=ollama_base_url,
            model=model,
        )
    else:  # local
        return LocalEmbeddingService(
            model_name=model,
        )
