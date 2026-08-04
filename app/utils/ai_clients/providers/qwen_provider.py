import logging
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Qwen Provider")

class QwenProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model if model else "qwen3.5-flash"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )

    async def generate_stream(self, messages: list[dict], **kwargs):
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.9),
                max_tokens=kwargs.get("max_tokens", 1000),
                frequency_penalty=kwargs.get("frequency_penalty", 0.0),
                presence_penalty=kwargs.get("presence_penalty", 0.0),
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Qwen API Stream Error: {e}")
            yield f"\n⚠️ Qwen API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.5),
                top_p=kwargs.get("top_p", 0.9),
                max_tokens=kwargs.get("max_tokens", 1000),
                frequency_penalty=kwargs.get("frequency_penalty", 0.8),
                presence_penalty=kwargs.get("presence_penalty", 0.3),
                stream=False,
            )
            yield response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Qwen API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "max_tokens": kwargs.get("max_tokens", 1000)
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**payload)
            msg = response.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except Exception as e:
            logger.error(f"Qwen API Generate Error: {e}")
            return {"content": None, "tool_calls": None}
