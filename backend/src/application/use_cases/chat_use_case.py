"""
Application Use Cases - Chat and RAG
Business logic for conversational AI with knowledge retrieval
"""
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
import uuid
import structlog

from src.domain.entities.document import Conversation, Message
from src.infrastructure.database.repositories import (
    SQLAlchemyConversationRepository,
    SQLAlchemyMessageRepository,
    SQLAlchemyDocumentRepository,
)
from src.infrastructure.embedding.service import EmbeddingService
from src.infrastructure.vector_store.chroma_store import ChromaVectorStore
from src.infrastructure.llm.service import LLMService, LLMMessage

logger = structlog.get_logger()


class ChatUseCase:
    """
    Chat and RAG use cases
    
    Handles:
    - Conversation management
    - RAG-based question answering
    - Streaming responses
    - Context retrieval
    """
    
    def __init__(
        self,
        conversation_repo: SQLAlchemyConversationRepository,
        message_repo: SQLAlchemyMessageRepository,
        document_repo: SQLAlchemyDocumentRepository,
        embedding_service: EmbeddingService,
        vector_store: ChromaVectorStore,
        llm_service: LLMService,
        enable_streaming: bool = True,
        enable_hybrid_search: bool = True,
        max_context_chunks: int = 5,
        max_conversation_history: int = 10,
    ):
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.document_repo = document_repo
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.enable_streaming = enable_streaming
        self.enable_hybrid_search = enable_hybrid_search
        self.max_context_chunks = max_context_chunks
        self.max_conversation_history = max_conversation_history
    
    async def create_conversation(
        self,
        title: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            title=title or "New Conversation",
            user_id=user_id,
        )
        return await self.conversation_repo.create(conversation)
    
    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """Get conversation by ID"""
        return await self.conversation_repo.get_by_id(conv_id)
    
    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Conversation]:
        """List conversations"""
        return await self.conversation_repo.get_all(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
    
    async def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation and its messages"""
        return await self.conversation_repo.delete(conv_id)
    
    async def get_messages(
        self,
        conv_id: str,
        limit: int = 50,
    ) -> List[Message]:
        """Get messages in a conversation"""
        return await self.message_repo.get_by_conversation(conv_id, limit)
    
    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context chunks for a query
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve
            filters: Optional metadata filters
        
        Returns:
            List of relevant chunks with metadata
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_text(query)
        
        # Search vector store
        if self.enable_hybrid_search:
            results = await self.vector_store.hybrid_search(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
            )
        else:
            results = await self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
                filters=filters,
            )
        
        logger.info(
            "context_retrieved",
            query_preview=query[:50],
            results_count=len(results),
        )
        
        return results
    
    async def chat(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = True,
        model: Optional[str] = None,
    ) -> Message:
        """
        Send a message and get a response (non-streaming)
        
        Args:
            conversation_id: Conversation ID
            user_message: User's message
            use_rag: Whether to use RAG for context
            model: Optional model override
        
        Returns:
            Assistant's response message
        """
        # Verify conversation exists
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Save user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )
        await self.message_repo.create(user_msg)
        
        # Get conversation history
        history = await self.message_repo.get_by_conversation(
            conversation_id,
            limit=self.max_conversation_history,
        )
        
        # Convert to LLM messages
        llm_history = [
            LLMMessage(role=m.role, content=m.content)
            for m in history[:-1]  # Exclude the just-added user message
        ]
        
        # Retrieve context if RAG enabled
        retrieved_chunks = []
        context_texts = []
        if use_rag:
            results = await self.retrieve_context(
                user_message,
                top_k=self.max_context_chunks,
            )
            retrieved_chunks = [r["id"] for r in results]
            context_texts = [r["content"] for r in results]
        
        # Generate response
        if context_texts:
            response_content = await self.llm_service.answer_with_context(
                question=user_message,
                context=context_texts,
                conversation_history=llm_history,
                model=model,
            )
        else:
            # Direct chat without context
            messages = llm_history + [LLMMessage(role="user", content=user_message)]
            if not any(m.role == "system" for m in messages):
                messages.insert(0, LLMMessage(
                    role="system",
                    content="You are a helpful knowledge assistant. Be concise and accurate."
                ))
            response = await self.llm_service.complete(messages, model=model)
            response_content = response.content
        
        # Save assistant message
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            retrieved_chunks=retrieved_chunks,
            model_used=model or self.llm_service.default_model,
        )
        await self.message_repo.create(assistant_msg)
        
        # Update conversation title if it's the first exchange
        if len(history) <= 1 and conversation.title == "New Conversation":
            # Generate title from first message
            conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")
            conversation.updated_at = datetime.utcnow()
            # Note: Would need to add update method to conversation repo
        
        logger.info(
            "chat_response_generated",
            conv_id=conversation_id,
            chunks_used=len(retrieved_chunks),
        )
        
        return assistant_msg
    
    async def chat_stream(
        self,
        conversation_id: str,
        user_message: str,
        use_rag: bool = True,
        model: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Send a message and stream the response
        
        Yields:
            Dict with type ('context', 'token', 'done') and data
        """
        # Verify conversation exists
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Save user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="user",
            content=user_message,
        )
        await self.message_repo.create(user_msg)
        
        # Get conversation history
        history = await self.message_repo.get_by_conversation(
            conversation_id,
            limit=self.max_conversation_history,
        )
        
        # Retrieve context if RAG enabled
        retrieved_chunks = []
        context_texts = []
        if use_rag:
            results = await self.retrieve_context(
                user_message,
                top_k=self.max_context_chunks,
            )
            retrieved_chunks = [r["id"] for r in results]
            context_texts = [r["content"] for r in results]
            
            # Yield context info
            yield {
                "type": "context",
                "data": {
                    "chunks": [
                        {
                            "id": r["id"],
                            "content": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                            "score": r.get("score", 0),
                            "metadata": r.get("metadata", {}),
                        }
                        for r in results
                    ]
                }
            }
        
        # Build messages
        messages = []
        
        # System prompt
        if context_texts:
            context_str = "\n\n---\n\n".join([f"[Source {i+1}]\n{c}" for i, c in enumerate(context_texts)])
            system_prompt = f"""You are a helpful knowledge assistant. Answer questions based on the provided context.

Context:
{context_str}

Guidelines:
- Use information from the context to answer questions accurately
- If the context doesn't contain relevant information, say so honestly
- Cite sources when possible (e.g., "According to Source 1...")
- Be concise but thorough"""
        else:
            system_prompt = "You are a helpful knowledge assistant. Be concise and accurate."
        
        messages.append(LLMMessage(role="system", content=system_prompt))
        
        # Add history
        for m in history[:-1]:
            messages.append(LLMMessage(role=m.role, content=m.content))
        
        # Add current message
        messages.append(LLMMessage(role="user", content=user_message))
        
        # Stream response
        full_response = ""
        async for token in self.llm_service.stream(messages, model=model):
            full_response += token
            yield {"type": "token", "data": token}
        
        # Save assistant message
        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            retrieved_chunks=retrieved_chunks,
            model_used=model or self.llm_service.default_model,
        )
        await self.message_repo.create(assistant_msg)
        
        # Yield completion
        yield {
            "type": "done",
            "data": {
                "message_id": assistant_msg.id,
                "total_length": len(full_response),
            }
        }
        
        logger.info(
            "streaming_chat_completed",
            conv_id=conversation_id,
            response_length=len(full_response),
        )
    
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        include_documents: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across all documents
        
        Args:
            query: Search query
            top_k: Number of results
            include_documents: Whether to include full document info
        
        Returns:
            Search results with relevance scores
        """
        results = await self.retrieve_context(query, top_k=top_k)
        
        if include_documents:
            # Enrich with document info
            for result in results:
                doc_id = result.get("metadata", {}).get("document_id")
                if doc_id:
                    doc = await self.document_repo.get_by_id(doc_id)
                    if doc:
                        result["document"] = {
                            "id": doc.id,
                            "title": doc.title,
                            "tags": doc.tags,
                        }
        
        return results
