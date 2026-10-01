import json
import logging
import httpx
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("DeepSeek Provider")

REASONING_EFFORT_TO_BUDGET = {
    "low": 2000,
    "medium": 6000,
    "high": 16000,
    "xhigh": 32000,
}


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

    def _is_thinking_model(self) -> bool:
        model_lower = self.model.lower()
        return "pro" in model_lower or "reasoner" in model_lower or "thinking" in model_lower

    def _build_payload(self, messages: list[dict], kwargs: dict, default_max_tokens: int, stream: bool) -> dict:
        max_tokens = kwargs.get("max_tokens", default_max_tokens)
        reasoning_effort = kwargs.get("reasoning_effort")
        thinking_enabled = self._is_thinking_model() and reasoning_effort != "none"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            **({"stop": kwargs["stop"]} if kwargs.get("stop") else {})
        }

        if thinking_enabled:
            budget = REASONING_EFFORT_TO_BUDGET.get(reasoning_effort, 6000)
            payload["max_tokens"] = max(max_tokens, budget + 1024)
            payload["reasoning_effort"] = reasoning_effort if reasoning_effort in REASONING_EFFORT_TO_BUDGET else "medium"
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            payload["max_tokens"] = max_tokens
            payload["temperature"] = kwargs.get("temperature", 0.7)
            payload["top_p"] = kwargs.get("top_p", 0.9)
            if "frequency_penalty" in kwargs:
                payload["frequency_penalty"] = kwargs["frequency_penalty"]
            if "presence_penalty" in kwargs:
                payload["presence_penalty"] = kwargs["presence_penalty"]

        return payload

    async def generate_stream(self, messages: list[dict], **kwargs):
        payload = self._build_payload(messages, kwargs, 1000, True)
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
        payload = self._build_payload(messages, {**kwargs, "reasoning_effort": "none"}, 1000, True)

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"DeepSeek API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        payload = self._build_payload(messages, {**kwargs, "reasoning_effort": "none"}, 1000, False)

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