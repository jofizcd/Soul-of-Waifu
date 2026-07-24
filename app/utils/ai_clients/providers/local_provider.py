import logging
import httpx
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Local Provider")

class LocalProvider(BaseAIProvider):
    def __init__(self, port: int = 48596, advanced_params: dict = None):
        self.base_url = f"http://127.0.0.1:{port}/v1"
        self.api_key = "no-key-required"
        self.advanced_params = advanced_params or {}
        
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=httpx.AsyncClient(timeout=None)
        )

    async def generate_stream(self, messages: list[dict], **kwargs):
        payload = {
            "model": "local-model",
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stop": kwargs.get("stop", ["<|im_end|>"]),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
        }

        if self.advanced_params:
            payload["extra_body"] = self.advanced_params

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Local API Stream Error: {e}")
            yield f"\n⚠️ Local API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        payload = {
            "model": "local-model",
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.5),
            "top_p": kwargs.get("top_p", 0.9),
            "stop": kwargs.get("stop", ["<|im_end|>"]),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.8),
            "presence_penalty": kwargs.get("presence_penalty", 0.3)
        }

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Local API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        payload = {
            "model": "local-model",
            "messages": messages,
            "stream": False,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "stop": kwargs.get("stop", ["<|im_end|>"]),
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if self.advanced_params:
            payload["extra_body"] = self.advanced_params

        try:
            completion = await self.client.chat.completions.create(**payload)
            msg = completion.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except Exception as e:
            logger.error(f"Local API Generate Error: {e}")
            return {"content": None, "tool_calls": None}
