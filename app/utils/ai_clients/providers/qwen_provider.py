import re
import logging
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Qwen Provider")

REASONING_EFFORT_TO_BUDGET = {
    "low": 1000,
    "medium": 4000,
    "high": 10000,
    "xhigh": 20000,
}

_ALWAYS_THINKING_RE = re.compile(r"qwen3.*-thinking|qvq", re.IGNORECASE)


class QwenProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model if model else "qwen3.5-flash"
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
        )

    def _thinking_extra_body(self, kwargs: dict, allow_thinking: bool) -> dict:
        reasoning_effort = kwargs.get("reasoning_effort")
        always_thinking = bool(_ALWAYS_THINKING_RE.search(self.model or ""))
        enable_thinking = always_thinking or (allow_thinking and bool(reasoning_effort) and reasoning_effort != "none")

        extra_body = {"enable_thinking": enable_thinking}
        if enable_thinking:
            budget = REASONING_EFFORT_TO_BUDGET.get(reasoning_effort, 4000)
            extra_body["thinking_budget"] = budget
        return extra_body

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
                extra_body=self._thinking_extra_body(kwargs, allow_thinking=True),
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
                extra_body=self._thinking_extra_body(kwargs, allow_thinking=False),
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
                "max_tokens": kwargs.get("max_tokens", 1000),
                "extra_body": self._thinking_extra_body(kwargs, allow_thinking=False),
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
