import re
import logging
import httpx
from openai import AsyncOpenAI
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("OpenAI Provider")

_REASONING_MODEL_RE = re.compile(r"^(o\d(-|$)|gpt-5)", re.IGNORECASE)

class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str, base_url: str = None, extra_headers: dict = None):
        self.api_key = api_key if api_key else "no-key-required"
        self.model = model if model else "gpt-4o-mini"
        self.base_url = base_url if base_url else "https://api.openai.com/v1"
        self.extra_headers = extra_headers
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=httpx.AsyncClient(timeout=120)
        )

    def _is_reasoning_model(self) -> bool:
        return bool(_REASONING_MODEL_RE.match(self.model or ""))

    def _apply_token_and_sampling_params(self, payload: dict, kwargs: dict, default_max_tokens: int):
        max_tokens = kwargs.get("max_tokens", default_max_tokens)
        if self._is_reasoning_model():
            payload["max_completion_tokens"] = max_tokens
            reasoning_effort = kwargs.get("reasoning_effort")
            if reasoning_effort and reasoning_effort != "none":
                payload["reasoning_effort"] = reasoning_effort
        else:
            payload["max_tokens"] = max_tokens
            payload["temperature"] = kwargs.get("temperature", 0.7)
            payload["top_p"] = kwargs.get("top_p", 0.9)
            if kwargs.get("stop"):
                payload["stop"] = kwargs["stop"]
        return payload

    async def generate_stream(self, messages: list[dict], **kwargs):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        self._apply_token_and_sampling_params(payload, kwargs, 1000)

        if self.extra_headers:
            payload["extra_headers"] = self.extra_headers
            
        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API Stream Error: {e}")
            yield f"\n⚠️ OpenAI API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        self._apply_token_and_sampling_params(payload, kwargs, 1000)
        if "temperature" in payload:
            payload["temperature"] = kwargs.get("temperature", 0.5)

        if "gemini" not in self.model.lower() and not self._is_reasoning_model():
            payload["frequency_penalty"] = kwargs.get("frequency_penalty", 0.5)
            payload["presence_penalty"] = kwargs.get("presence_penalty", 0.0)

        if self.extra_headers:
            payload["extra_headers"] = self.extra_headers

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        self._apply_token_and_sampling_params(payload, kwargs, 1000)

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if self.extra_headers:
            payload["extra_headers"] = self.extra_headers

        try:
            completion = await self.client.chat.completions.create(**payload)
            msg = completion.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except Exception as e:
            logger.error(f"OpenAI API Generate Error: {e}")
            return {"content": None, "tool_calls": None}