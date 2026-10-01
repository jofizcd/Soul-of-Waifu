import logging
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Grok Provider")

class GrokProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model if model else "grok-4.3"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

    async def generate_stream(self, messages: list[dict], **kwargs):
        try:
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
                "max_tokens": kwargs.get("max_tokens", 1000),
                "stream": True,
            }

            model_lower = self.model.lower()
            is_reasoning = ("grok-4" in model_lower or "reasoning" in model_lower) \
                and "non-reasoning" not in model_lower
            is_fixed_reasoning = model_lower.strip() in ("grok-4", "grok-code-fast-1")
            if not is_reasoning:
                if "frequency_penalty" in kwargs:
                    params["frequency_penalty"] = kwargs["frequency_penalty"]
                if "presence_penalty" in kwargs:
                    params["presence_penalty"] = kwargs["presence_penalty"]
            elif not is_fixed_reasoning:
                reasoning_effort = kwargs.get("reasoning_effort")
                if reasoning_effort and reasoning_effort != "none":
                    params["reasoning_effort"] = reasoning_effort

            stream = await self.client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Grok (xAI) Stream Error: {e}")
            yield f"\n⚠️ Grok API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.5),
                top_p=kwargs.get("top_p", 0.9),
                max_tokens=kwargs.get("max_tokens", 1000),
                stream=False,
            )
            yield response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Grok (xAI) Summary Error: {e}")
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

            model_lower = self.model.lower()
            is_reasoning = ("grok-4" in model_lower or "reasoning" in model_lower) \
                and "non-reasoning" not in model_lower
            is_fixed_reasoning = model_lower.strip() in ("grok-4", "grok-code-fast-1")
            reasoning_effort = kwargs.get("reasoning_effort")
            if is_reasoning and not is_fixed_reasoning and reasoning_effort and reasoning_effort != "none":
                payload["reasoning_effort"] = reasoning_effort

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
            logger.error(f"Grok (xAI) Generate Error: {e}")
            return {"content": None, "tool_calls": None}