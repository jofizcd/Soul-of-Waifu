import logging
import httpx
from openai import AsyncOpenAI, APIConnectionError, APITimeoutError
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Local Provider")

REASONING_EFFORT_TO_BUDGET = {
    "low": 1000,
    "medium": 4000,
    "high": 10000,
    "xhigh": 20000,
}

class LocalProvider(BaseAIProvider):
    def __init__(self, port: int = 48596, advanced_params: dict = None):
        self.base_url = f"http://127.0.0.1:{port}/v1"
        self.api_key = "no-key-required"
        self.advanced_params = advanced_params or {}

        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
            )
        )

    def _connection_error_message(self, e: Exception) -> str:
        logger.error(f"Local API Connection Error: {e}")
        return (
            "\n⚠️ Local API Error: Could not reach the local server. "
            "It may still be loading the model, may have crashed, or the port may be blocked."
        )

    def _apply_thinking_budget(self, extra_body: dict, kwargs: dict, payload: dict) -> None:
        reasoning_mode = kwargs.get("reasoning_mode")
        if reasoning_mode is False:
            extra_body["thinking_budget_tokens"] = 0
            return

        reasoning_effort = kwargs.get("reasoning_effort")
        if reasoning_effort and reasoning_effort != "none":
            budget = REASONING_EFFORT_TO_BUDGET.get(reasoning_effort, 4000)
            extra_body["thinking_budget_tokens"] = budget
            payload["max_tokens"] = max(payload["max_tokens"], budget + 1024)

    async def generate_stream(self, messages: list[dict], **kwargs):
        payload = {
            "model": "local-model",
            "messages": messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
            "top_p": kwargs.get("top_p", 0.9),
            "frequency_penalty": kwargs.get("frequency_penalty", 0.0),
            "presence_penalty": kwargs.get("presence_penalty", 0.0),
        }

        stop_sequences = kwargs.get("stop")
        if stop_sequences:
            payload["stop"] = stop_sequences

        extra_body = dict(self.advanced_params) if self.advanced_params else {}
        self._apply_thinking_budget(extra_body, kwargs, payload)
        if extra_body:
            payload["extra_body"] = extra_body

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except (APIConnectionError, APITimeoutError) as e:
            yield self._connection_error_message(e)
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
            "frequency_penalty": kwargs.get("frequency_penalty", 0.8),
            "presence_penalty": kwargs.get("presence_penalty", 0.3)
        }

        stop_sequences = kwargs.get("stop")
        if stop_sequences:
            payload["stop"] = stop_sequences

        reasoning_mode = kwargs.get("reasoning_mode", False)
        if reasoning_mode is False:
            payload["extra_body"] = {"thinking_budget_tokens": 0}

        try:
            completion = await self.client.chat.completions.create(**payload)
            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except (APIConnectionError, APITimeoutError) as e:
            logger.error(f"Local API Connection Error (summary): {e}")
            yield ""
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
        }

        stop_sequences = kwargs.get("stop")
        if stop_sequences:
            payload["stop"] = stop_sequences

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        extra_body = dict(self.advanced_params) if self.advanced_params else {}
        reasoning_mode = kwargs.get("reasoning_mode")
        if reasoning_mode is False:
            extra_body["thinking_budget_tokens"] = 0
        if extra_body:
            payload["extra_body"] = extra_body

        try:
            completion = await self.client.chat.completions.create(**payload)
            msg = completion.choices[0].message
            return {
                "content": msg.content,
                "tool_calls": msg.tool_calls
            }
        except (APIConnectionError, APITimeoutError) as e:
            logger.error(f"Local API Connection Error (generate): {e}")
            return {"content": None, "tool_calls": None}
        except Exception as e:
            logger.error(f"Local API Generate Error: {e}")
            return {"content": None, "tool_calls": None}
