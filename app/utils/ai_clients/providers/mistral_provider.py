import logging
from mistralai import Mistral
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Mistral Provider")

class MistralProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model if model else "mistral-small-latest"
        self.client = Mistral(api_key=self.api_key)

    async def generate_stream(self, messages: list[dict], **kwargs):
        try:
            response = await self.client.chat.stream_async(
                model=self.model,
                messages=messages,
                safe_prompt=False,
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.9),
                max_tokens=kwargs.get("max_tokens", 1000),
                frequency_penalty=kwargs.get("frequency_penalty", 0.0),
                presence_penalty=kwargs.get("presence_penalty", 0.0)
            )

            async for chunk in response:
                if chunk.data and chunk.data.choices and chunk.data.choices[0].delta:
                    content = chunk.data.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Mistral API Stream Error: {e}")
            yield f"\n⚠️ Mistral API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        try:
            response = await self.client.chat.stream_async(
                model=self.model,
                messages=messages,
                safe_prompt=False,
                temperature=kwargs.get("temperature", 0.5),
                top_p=kwargs.get("top_p", 0.9),
                max_tokens=kwargs.get("max_tokens", 1000),
                frequency_penalty=kwargs.get("frequency_penalty", 0.8),
                presence_penalty=kwargs.get("presence_penalty", 0.3)
            )

            async for chunk in response:
                if chunk.data and chunk.data.choices and chunk.data.choices[0].delta:
                    content = chunk.data.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Mistral API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 1000)
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
                
            response = await self.client.chat.complete_async(**payload)
            msg = response.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except Exception as e:
            logger.error(f"Mistral API Generate Error: {e}")
            return {"content": None, "tool_calls": None}