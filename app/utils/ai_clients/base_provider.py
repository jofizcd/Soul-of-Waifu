from abc import ABC, abstractmethod
from typing import AsyncGenerator

class BaseAIProvider(ABC):
    """
    Abstract base class for all AI providers.
    """
    
    @abstractmethod
    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """
        Sends messages to the AI provider and yields the text chunks as they arrive.
        
        Args:
            messages (list[dict]): The conversation context, formatted as [{"role": "system"/"user"/"assistant", "content": "..."}].
            **kwargs: Generation parameters (temperature, max_tokens, top_p, etc.).
            
        Yields:
            str: Chunks of the generated text.
        """
        pass

    @abstractmethod
    async def generate_summary(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        """
        Sends messages specifically formatted for summarization and yields the summary chunks.
        
        Args:
            messages (list[dict]): The summarization context.
            **kwargs: Generation parameters for summarization.
            
        Yields:
            str: Chunks of the generated summary text.
        """
        pass

    @abstractmethod
    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        """
        Non-streaming generation with optional Tool Calling support.
        
        Args:
            messages (list[dict]): The conversation context.
            tools (list): Optional list of OpenAI-compatible tool schemas.
            **kwargs: Generation parameters.
            
        Returns:
            dict: Format {"content": str | None, "tool_calls": list | None}
        """
        pass
