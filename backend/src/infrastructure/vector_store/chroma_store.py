"""
Vector Store Service
Chroma-based vector storage for semantic search
Supports hybrid search (vector + keyword)
"""
from typing import List, Optional, Dict, Any
import os
import structlog

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = structlog.get_logger()


class ChromaVectorStore:
    """
    Chroma vector store for document embeddings
    
    Features:
    - Persistent storage
    - Metadata filtering
    - Hybrid search (semantic + keyword via metadata)
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        collection_name: str = "knowledge_base",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize Chroma client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
        
        logger.info(
            "chroma_initialized",
            persist_dir=persist_directory,
            collection=collection_name,
            count=self.collection.count()
        )
    
    async def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Add documents with embeddings to the vector store
        
        Args:
            ids: Unique identifiers for each document
            embeddings: Pre-computed embeddings
            documents: Original text content
            metadatas: Optional metadata for each document
        """
        if not ids:
            return
        
        # Ensure metadata is provided
        if metadatas is None:
            metadatas = [{}] * len(ids)
        
        # Clean metadata (Chroma doesn't support None values)
        clean_metadatas = []
        for meta in metadatas:
            clean_meta = {}
            for k, v in meta.items():
                if v is not None:
                    # Convert complex types to strings
                    if isinstance(v, (list, dict)):
                        import json
                        clean_meta[k] = json.dumps(v)
                    else:
                        clean_meta[k] = v
            clean_metadatas.append(clean_meta)
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_metadatas,
        )
        
        logger.info("added_documents_to_chroma", count=len(ids))
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using embedding similarity
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filters: Metadata filters (Chroma where clause)
        
        Returns:
            List of results with id, content, metadata, and score
        """
        where = filters if filters else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append({
                    "id": doc_id,
                    "content": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0,  # Convert distance to similarity
                })
        
        return formatted
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining semantic and keyword matching
        
        Note: True hybrid search requires BM25 index. This implementation
        uses Chroma's built-in keyword search capabilities.
        
        Args:
            query: Text query for keyword matching
            query_embedding: Query vector for semantic matching
            top_k: Number of results
            filters: Metadata filters
            semantic_weight: Weight for semantic vs keyword (0-1)
        
        Returns:
            Combined and re-ranked results
        """
        # Get semantic results
        semantic_results = await self.search(
            query_embedding=query_embedding,
            top_k=top_k * 2,  # Get more results for re-ranking
            filters=filters,
        )
        
        # Simple keyword boost: increase score if query terms appear in content
        query_terms = set(query.lower().split())
        
        for result in semantic_results:
            content_lower = result["content"].lower()
            keyword_matches = sum(1 for term in query_terms if term in content_lower)
            keyword_score = keyword_matches / len(query_terms) if query_terms else 0
            
            # Combine scores
            result["score"] = (
                semantic_weight * result["score"] + 
                (1 - semantic_weight) * keyword_score
            )
        
        # Re-sort by combined score
        semantic_results.sort(key=lambda x: x["score"], reverse=True)
        
        return semantic_results[:top_k]
    
    async def delete_by_document(self, doc_id: str) -> None:
        """Delete all vectors associated with a document"""
        # Get all chunk IDs for this document
        results = self.collection.get(
            where={"document_id": doc_id},
            include=[]
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
            logger.info("deleted_document_vectors", doc_id=doc_id, count=len(results["ids"]))
    
    async def delete_by_ids(self, ids: List[str]) -> None:
        """Delete vectors by their IDs"""
        if ids:
            self.collection.delete(ids=ids)
            logger.info("deleted_vectors_by_ids", count=len(ids))
    
    async def get_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Get documents by their IDs"""
        results = self.collection.get(
            ids=ids,
            include=["documents", "metadatas"]
        )
        
        formatted = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                formatted.append({
                    "id": doc_id,
                    "content": results["documents"][i] if results["documents"] else "",
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                })
        
        return formatted
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": self.persist_directory,
        }
    
    async def reset(self) -> None:
        """Reset the collection (delete all data)"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.warning("collection_reset", collection=self.collection_name)


def create_vector_store(
    persist_directory: str = "./data/chroma",
    collection_name: str = "knowledge_base",
) -> ChromaVectorStore:
    """Factory function to create vector store"""
    return ChromaVectorStore(
        persist_directory=persist_directory,
        collection_name=collection_name,
    )
