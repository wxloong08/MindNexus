"""
Chat API Routes
Endpoints for conversational AI with RAG
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.presentation.schemas.api_schemas import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
    ChatRequest,
    ChatResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    ErrorResponse,
)
from src.presentation.api.dependencies import get_chat_use_case
from src.application.use_cases.chat_use_case import ChatUseCase

router = APIRouter(prefix="/chat", tags=["Chat"])


def _conv_to_response(conv) -> ConversationResponse:
    """Convert domain entity to response schema"""
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def _msg_to_response(msg) -> MessageResponse:
    """Convert domain entity to response schema"""
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        role=msg.role,
        content=msg.content,
        retrieved_chunks=msg.retrieved_chunks,
        model_used=msg.model_used,
        tokens_used=msg.tokens_used,
        created_at=msg.created_at,
    )


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: ConversationCreate,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Create a new conversation
    """
    conv = await use_case.create_conversation(title=request.title)
    return _conv_to_response(conv)


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
)
async def list_conversations(
    skip: int = 0,
    limit: int = 20,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    List all conversations
    """
    convs = await use_case.list_conversations(skip=skip, limit=limit)
    return ConversationListResponse(
        conversations=[_conv_to_response(c) for c in convs],
        total=len(convs),
    )


@router.get(
    "/conversations/{conv_id}",
    response_model=ConversationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_conversation(
    conv_id: str,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Get a conversation by ID
    """
    conv = await use_case.get_conversation(conv_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conv_id} not found",
        )
    return _conv_to_response(conv)


@router.delete(
    "/conversations/{conv_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_conversation(
    conv_id: str,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Delete a conversation and its messages
    """
    success = await use_case.delete_conversation(conv_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conv_id} not found",
        )


@router.get(
    "/conversations/{conv_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    conv_id: str,
    limit: int = 50,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Get messages in a conversation
    """
    messages = await use_case.get_messages(conv_id, limit=limit)
    return [_msg_to_response(m) for m in messages]


@router.post(
    "/conversations/{conv_id}/messages",
    response_model=ChatResponse,
    responses={404: {"model": ErrorResponse}},
)
async def send_message(
    conv_id: str,
    request: ChatRequest,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Send a message and get a response (non-streaming)
    
    Set `use_rag=true` to include knowledge base context.
    """
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use /messages/stream endpoint for streaming",
        )
    
    try:
        # Get context for response
        context = []
        if request.use_rag:
            context = await use_case.retrieve_context(request.message)
        
        msg = await use_case.chat(
            conversation_id=conv_id,
            user_message=request.message,
            use_rag=request.use_rag,
            model=request.model,
        )
        
        return ChatResponse(
            message=_msg_to_response(msg),
            context_used=context,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/conversations/{conv_id}/messages/stream",
)
async def send_message_stream(
    conv_id: str,
    request: ChatRequest,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Send a message and stream the response using Server-Sent Events
    
    Events:
    - `context`: Retrieved context chunks (if RAG enabled)
    - `token`: Response token
    - `done`: Completion signal with metadata
    - `error`: Error message
    
    Example client:
    ```javascript
    const eventSource = new EventSource('/chat/conversations/{id}/messages/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'token') {
            // Append token to response
        }
    };
    ```
    """
    async def event_generator():
        try:
            async for event in use_case.chat_stream(
                conversation_id=conv_id,
                user_message=request.message,
                use_rag=request.use_rag,
                model=request.model,
            ):
                yield {
                    "event": event["type"],
                    "data": json.dumps(event["data"]) if isinstance(event["data"], dict) else event["data"],
                }
        except ValueError as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": str(e)}),
            }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"detail": f"Internal error: {str(e)}"}),
            }
    
    return EventSourceResponse(event_generator())


@router.post(
    "/search",
    response_model=SearchResponse,
)
async def semantic_search(
    request: SearchRequest,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Semantic search across all documents
    
    Uses vector similarity to find relevant content.
    """
    results = await use_case.semantic_search(
        query=request.query,
        top_k=request.top_k,
        include_documents=request.include_documents,
    )
    
    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                id=r["id"],
                content=r["content"],
                score=r.get("score", 0),
                metadata=r.get("metadata", {}),
                document=r.get("document"),
            )
            for r in results
        ],
        total=len(results),
    )


@router.post(
    "/ask",
    response_model=ChatResponse,
)
async def quick_ask(
    request: ChatRequest,
    use_case: ChatUseCase = Depends(get_chat_use_case),
):
    """
    Quick question without creating a conversation
    
    Creates a temporary conversation, asks the question, and returns the response.
    Useful for one-off queries.
    """
    # Create temporary conversation
    conv = await use_case.create_conversation(title="Quick Question")
    
    try:
        # Get context for response
        context = []
        if request.use_rag:
            context = await use_case.retrieve_context(request.message)
        
        msg = await use_case.chat(
            conversation_id=conv.id,
            user_message=request.message,
            use_rag=request.use_rag,
            model=request.model,
        )
        
        return ChatResponse(
            message=_msg_to_response(msg),
            context_used=context,
        )
    except Exception as e:
        # Clean up on error
        await use_case.delete_conversation(conv.id)
        raise
