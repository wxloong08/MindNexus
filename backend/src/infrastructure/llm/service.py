"""
LLM Service Layer
Unified LLM interface using LiteLLM for multi-provider support
Supports: OpenAI, Anthropic, Ollama, Qwen, DeepSeek, etc.
"""
import asyncio
from typing import AsyncIterator, List, Optional, Dict, Any
from dataclasses import dataclass
import structlog

import litellm
from litellm import acompletion, completion
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


@dataclass
class LLMResponse:
    """Standardized LLM response"""
    content: str
    model: str
    tokens_used: int
    finish_reason: str
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class LLMMessage:
    """Chat message format"""
    role: str  # system, user, assistant
    content: str


class LLMService:
    """
    Unified LLM Service using LiteLLM
    
    Features:
    - Multi-provider support (OpenAI, Anthropic, Ollama, etc.)
    - Automatic retry with exponential backoff
    - Streaming support
    - Token counting
    - Fallback providers
    """
    
    def __init__(
        self,
        default_model: str = "ollama/llama3.2",
        fallback_models: Optional[List[str]] = None,
        api_keys: Optional[Dict[str, str]] = None,
        base_urls: Optional[Dict[str, str]] = None,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.default_model = default_model
        self.fallback_models = fallback_models or []
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Configure API keys
        if api_keys:
            for provider, key in api_keys.items():
                if key:
                    setattr(litellm, f"{provider}_key", key)
        
        # Configure base URLs for self-hosted models
        self.base_urls = base_urls or {}
        
        # Enable verbose logging in debug mode
        litellm.set_verbose = False
    
    def _get_model_kwargs(self, model: str) -> Dict[str, Any]:
        """Get additional kwargs based on model provider"""
        kwargs = {}
        
        # Extract provider from model string (e.g., "ollama/llama3.2" -> "ollama")
        provider = model.split("/")[0] if "/" in model else model.split("-")[0]
        
        # Add base URL for specific providers
        if provider in self.base_urls:
            kwargs["api_base"] = self.base_urls[provider]
        
        return kwargs
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from LLM
        
        Args:
            messages: List of chat messages
            model: Model identifier (e.g., "openai/gpt-4", "ollama/llama3.2")
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional model-specific parameters
        
        Returns:
            LLMResponse with content and metadata
        """
        model = model or self.default_model
        model_kwargs = self._get_model_kwargs(model)
        
        try:
            response = await acompletion(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                **model_kwargs,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=model,
                tokens_used=response.usage.total_tokens if response.usage else 0,
                finish_reason=response.choices[0].finish_reason,
                raw_response=response.model_dump() if hasattr(response, 'model_dump') else None,
            )
            
        except Exception as e:
            logger.error("llm_completion_failed", model=model, error=str(e))
            
            # Try fallback models
            for fallback_model in self.fallback_models:
                if fallback_model != model:
                    try:
                        logger.info("trying_fallback_model", fallback=fallback_model)
                        model_kwargs = self._get_model_kwargs(fallback_model)
                        
                        response = await acompletion(
                            model=fallback_model,
                            messages=[{"role": m.role, "content": m.content} for m in messages],
                            temperature=temperature,
                            max_tokens=max_tokens,
                            timeout=self.timeout,
                            **model_kwargs,
                            **kwargs
                        )
                        
                        return LLMResponse(
                            content=response.choices[0].message.content,
                            model=fallback_model,
                            tokens_used=response.usage.total_tokens if response.usage else 0,
                            finish_reason=response.choices[0].finish_reason,
                        )
                    except Exception as fallback_error:
                        logger.warning("fallback_failed", model=fallback_model, error=str(fallback_error))
                        continue
            
            raise
    
    async def stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from LLM
        
        Yields:
            String chunks as they arrive
        """
        model = model or self.default_model
        model_kwargs = self._get_model_kwargs(model)
        
        try:
            response = await acompletion(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
                stream=True,
                **model_kwargs,
                **kwargs
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error("llm_stream_failed", model=model, error=str(e))
            raise
    
    async def generate_summary(
        self,
        text: str,
        max_length: int = 200,
        model: Optional[str] = None,
    ) -> str:
        """Generate a summary of the given text"""
        messages = [
            LLMMessage(
                role="system",
                content="You are a helpful assistant that creates concise summaries. "
                        "Summarize the following text in a clear and informative way."
            ),
            LLMMessage(
                role="user",
                content=f"Please summarize the following text in about {max_length} words:\n\n{text}"
            )
        ]
        
        response = await self.complete(messages, model=model, temperature=0.3)
        return response.content
    
    async def generate_tags(
        self,
        text: str,
        max_tags: int = 5,
        model: Optional[str] = None,
    ) -> List[str]:
        """Generate relevant tags for the given text"""
        messages = [
            LLMMessage(
                role="system",
                content="You are a helpful assistant that generates relevant tags for documents. "
                        "Return only the tags, one per line, without numbering or bullet points."
            ),
            LLMMessage(
                role="user",
                content=f"Generate up to {max_tags} relevant tags for the following text:\n\n{text}"
            )
        ]
        
        response = await self.complete(messages, model=model, temperature=0.3, max_tokens=100)
        
        # Parse tags from response
        tags = []
        for line in response.content.strip().split("\n"):
            tag = line.strip().lower()
            # Remove common prefixes
            for prefix in ["- ", "* ", "• "]:
                if tag.startswith(prefix):
                    tag = tag[len(prefix):]
            if tag and len(tag) < 50:  # Basic validation
                tags.append(tag)
        
        return tags[:max_tags]
    
    async def answer_with_context(
        self,
        question: str,
        context: List[str],
        conversation_history: Optional[List[LLMMessage]] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        RAG-style question answering with retrieved context
        
        Args:
            question: User's question
            context: List of relevant text chunks
            conversation_history: Previous messages in the conversation
            model: Model to use
        
        Returns:
            Generated answer
        """
        # Build context string
        context_str = "\n\n---\n\n".join([f"[Source {i+1}]\n{c}" for i, c in enumerate(context)])
        
        system_prompt = """You are a helpful knowledge assistant. Answer questions based on the provided context.

Guidelines:
- Use information from the context to answer questions accurately
- If the context doesn't contain relevant information, say so honestly
- Cite sources when possible (e.g., "According to Source 1...")
- Be concise but thorough
- If you're unsure, express uncertainty rather than making things up"""
        
        messages = [LLMMessage(role="system", content=system_prompt)]
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add context and question
        user_message = f"""Context:
{context_str}

Question: {question}

Please answer based on the context provided above."""
        
        messages.append(LLMMessage(role="user", content=user_message))
        
        response = await self.complete(messages, model=model)
        return response.content
    
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text for a specific model"""
        model = model or self.default_model
        try:
            return litellm.token_counter(model=model, text=text)
        except Exception:
            # Rough estimate if token counting fails
            return len(text) // 4
    
    async def check_health(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Check if the LLM service is healthy"""
        model = model or self.default_model
        try:
            response = await self.complete(
                messages=[LLMMessage(role="user", content="Hello")],
                model=model,
                max_tokens=10,
            )
            return {
                "status": "healthy",
                "model": model,
                "response_length": len(response.content),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "model": model,
                "error": str(e),
            }


def create_llm_service(
    default_provider: str = "ollama",
    default_model: str = "llama3.2",
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    ollama_base_url: str = "http://localhost:11434",
    qwen_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
) -> LLMService:
    """
    Factory function to create LLM service with configuration
    """
    # Build model string
    if default_provider in ["openai", "anthropic", "ollama", "qwen", "deepseek"]:
        full_model = f"{default_provider}/{default_model}"
    else:
        full_model = default_model
    
    # Configure API keys
    api_keys = {
        "openai": openai_api_key,
        "anthropic": anthropic_api_key,
        "qwen": qwen_api_key,
        "deepseek": deepseek_api_key,
    }
    
    # Configure base URLs
    base_urls = {
        "ollama": ollama_base_url,
    }
    
    # Define fallback chain
    fallback_models = []
    if openai_api_key:
        fallback_models.append("openai/gpt-4o-mini")
    if anthropic_api_key:
        fallback_models.append("anthropic/claude-3-haiku-20240307")
    
    return LLMService(
        default_model=full_model,
        fallback_models=fallback_models,
        api_keys=api_keys,
        base_urls=base_urls,
    )
