import json
import logging
import httpx
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("DeepSeek Provider")

class DeepSeekProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key if api_key else "no-key-required"
        self.model = model if model else "deepseek-v4-flash"
        self.base_url = "https://api.deepseek.com"

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=httpx.AsyncClient(timeout=120)
        )

    async def generate_stream(self, messages: list[dict], **kwargs):
        is_thinking_model = "pro" in self.model.lower()

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            **({"stop": kwargs["stop"]} if kwargs.get("stop") else {})
        }

        if is_thinking_model:
            payload["reasoning_effort"] = kwargs.get("reasoning_effort", "high")
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            payload["temperature"] = kwargs.get("temperature", 0.7)
            payload["top_p"] = kwargs.get("top_p", 0.9)
            if "frequency_penalty" in kwargs:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                payload["presence_penalty"] = kwargs["presence_penalty"]

        thinking_active = False

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    reasoning = getattr(delta, "reasoning_content", None)
                    if reasoning:
                        if not thinking_active:
                            thinking_active = True
                            yield "<think>\n"
                        yield reasoning
                        continue

                    if thinking_active and delta.content:
                        thinking_active = False
                        yield "\n</think>\n"

                    if delta.content:
                        yield delta.content

            if thinking_active:
                yield "\n</think>\n"

        except Exception as e:
            logger.error(f"DeepSeek API Stream Error: {e}")
            yield f"\n⚠️ DeepSeek API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            **({"stop": kwargs["stop"]} if kwargs.get("stop") else {})
        }

        if "pro" in self.model.lower():
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            payload["temperature"] = kwargs.get("temperature", 0.5)
            payload["top_p"] = kwargs.get("top_p", 0.9)

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "max_tokens": kwargs.get("max_tokens", 1000),
            **({"stop": kwargs["stop"]} if kwargs.get("stop") else {})
        }

        if "pro" in self.model.lower():
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            payload["temperature"] = kwargs.get("temperature", 0.7)
            payload["top_p"] = kwargs.get("top_p", 0.9)

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            completion = await self.client.chat.completions.create(**payload)
            msg = completion.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except Exception as e:
            logger.error(f"DeepSeek API Generate Error: {e}")
            return {"content": None, "tool_calls": None}
