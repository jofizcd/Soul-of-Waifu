import json
import httpx
import logging
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Anthropic Provider")

class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key)
        self.model = model if model else "claude-sonnet-5"
        self.base_url = "https://api.anthropic.com/v1/messages"

    def _build_anthropic_messages(self, messages: list[dict]):
        system_text = ""
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role")

            if role == "system":
                piece = msg.get("content") or ""
                system_text = f"{system_text}\n\n{piece}" if system_text else piece
                continue

            if role == "tool":
                tool_use_id = msg.get("tool_call_id") or msg.get("id") or ""
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": str(msg.get("content", "")),
                    }]
                })
                continue

            content = msg.get("content")
            tool_calls = msg.get("tool_calls")

            if role == "assistant" and tool_calls:
                blocks = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        call_id = tc.get("id", "")
                        func = tc.get("function", {}) or {}
                        name = func.get("name")
                        raw_args = func.get("arguments", "{}")
                    else:
                        call_id = getattr(tc, "id", "")
                        func = getattr(tc, "function", None)
                        name = getattr(func, "name", None) if func else None
                        raw_args = getattr(func, "arguments", "{}") if func else "{}"
                    try:
                        tool_input = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    except Exception:
                        tool_input = {}
                    blocks.append({
                        "type": "tool_use",
                        "id": call_id,
                        "name": name,
                        "input": tool_input,
                    })
                anthropic_messages.append({"role": "assistant", "content": blocks})
                continue

            if isinstance(content, list):
                anthropic_content = []
                for block in content:
                    block_type = block.get("type")
                    if block_type == "text":
                        anthropic_content.append({"type": "text", "text": block.get("text", "")})
                    elif block_type == "image_url":
                        image_data = block["image_url"]["url"]
                        media_type = image_data.split(";")[0].split(":")[1]
                        b64_data = image_data.split(",")[1]
                        anthropic_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data
                            }
                        })
                    elif block_type == "image":
                        anthropic_content.append(block)
                anthropic_messages.append({"role": role, "content": anthropic_content})
            else:
                anthropic_messages.append({"role": role, "content": content or ""})

        return system_text, anthropic_messages

    async def generate_stream(self, messages: list[dict], **kwargs):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text, anthropic_messages = self._build_anthropic_messages(messages)

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": True
        }

        if system_text:
            payload["system"] = system_text

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    logger.error(f"Anthropic API Error {response.status_code}: {error_body.decode('utf-8', errors='ignore')}")
                    raise RuntimeError(f"Anthropic API Error: {response.status_code}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = data.get("type")
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta.get("text", "")
                        elif event_type == "error":
                            error_info = data.get("error", {})
                            logger.error(f"Anthropic API Stream Error event: {error_info}")
                            yield f"\n⚠️ Anthropic API Error: {error_info.get('message', 'stream error')}"
                            break
                        elif event_type == "message_stop":
                            break

    async def generate_summary(self, messages: list[dict], **kwargs) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text, anthropic_messages = self._build_anthropic_messages(messages)

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 1024),
            "stream": False
        }

        if system_text:
            payload["system"] = system_text

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Anthropic API Error {response.status_code}: {response.text}")
                return ""

            data = response.json()
            content_blocks = data.get("content", [])
            full_text = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    full_text += block.get("text", "")

            return full_text.strip()

    async def generate(self, messages: list[dict], **kwargs) -> dict:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text, anthropic_messages = self._build_anthropic_messages(messages)

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False
        }

        if system_text:
            payload["system"] = system_text

        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]

        tools = kwargs.get("tools")
        if tools:
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
            payload["tools"] = anthropic_tools

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Anthropic API Error {response.status_code}: {response.text}")
                raise RuntimeError(f"Anthropic API Error: {response.status_code}")

            data = response.json()
            content_blocks = data.get("content", [])

            content_str = ""
            tool_calls = []

            for block in content_blocks:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        content_str += block.get("text", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {}))
                            }
                        })

            return {
                "content": content_str if content_str else None,
                "tool_calls": tool_calls if tool_calls else None
            }