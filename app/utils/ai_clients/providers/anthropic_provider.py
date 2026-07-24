import json
import logging
import httpx
from app.utils.ai_clients.base_provider import BaseAIProvider

logger = logging.getLogger("Anthropic Provider")

class AnthropicProvider(BaseAIProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key if api_key else "no-key-required"
        self.model = model if model else "claude-sonnet-4-6"
        self.base_url = "https://api.anthropic.com/v1/messages"

    async def generate_stream(self, messages: list[dict], **kwargs):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                if system_text:
                    system_text += "\n\n" + msg["content"]
                else:
                    system_text = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        if system_text:
            payload["system"] = system_text

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        yield f"\n⚠️ Anthropic API Error ({response.status_code}): {err_body.decode('utf-8')}"
                        return

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    yield data["delta"].get("text", "")
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"Anthropic API Stream Error: {e}")
            yield f"\nAnthropic API Error: {str(e)}"

    async def generate_summary(self, messages: list[dict], **kwargs):
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                if system_text:
                    system_text += "\n\n" + msg["content"]
                else:
                    system_text = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "stream": False,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.5)
        }
        if system_text:
            payload["system"] = system_text

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    yield data.get("content", [{}])[0].get("text", "")
                else:
                    yield ""
        except Exception as e:
            logger.error(f"Anthropic API Summary Error: {e}")
            yield ""

    async def generate(self, messages: list[dict], tools: list = None, **kwargs) -> dict:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        system_text = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                if system_text:
                    system_text += "\n\n" + msg["content"]
                else:
                    system_text = msg["content"]
            else:
                content = msg["content"]
                if isinstance(content, list):
                    anthropic_content = []
                    for block in content:
                        if block.get("type") == "text":
                            anthropic_content.append({"type": "text", "text": block["text"]})
                        elif block.get("type") == "image_url":
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
                    anthropic_messages.append({"role": msg["role"], "content": anthropic_content})
                else:
                    anthropic_messages.append({"role": msg["role"], "content": content})

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "stream": False,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        if system_text:
            payload["system"] = system_text

        if tools:
            anthropic_tools = []
            for t in tools:
                if "function" in t:
                    anthropic_tools.append({
                        "name": t["function"]["name"],
                        "description": t["function"].get("description", ""),
                        "input_schema": t["function"].get("parameters", {"type": "object", "properties": {}})
                    })
            if anthropic_tools:
                payload["tools"] = anthropic_tools

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(self.base_url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    
                    content_str = ""
                    tool_calls = []
                    
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content_str += block.get("text", "")
                        elif block.get("type") == "tool_use":
                            tool_calls.append({
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
                else:
                    logger.error(f"Anthropic API Generate Error: {response.text}")
                    return {"content": None, "tool_calls": None}
        except Exception as e:
            logger.error(f"Anthropic API Generate Error: {e}")
            return {"content": None, "tool_calls": None}
