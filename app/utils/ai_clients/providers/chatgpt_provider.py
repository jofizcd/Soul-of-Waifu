"""ChatGPT plan inference through the public, stateless Responses API."""

import asyncio
import json
import logging
import time
from contextlib import aclosing

import httpx
from openai.types.chat import ChatCompletionMessageToolCall

from app.utils.ai_clients.base_provider import BaseAIProvider


API_ROOT = "https://api.openai.com/v1"
TOOL_NAMESPACE = "soul_of_waifu"
logger = logging.getLogger(__name__)


class ChatGPTProviderError(RuntimeError):
    """A safe, user-facing error that never includes remote bodies or credentials."""


def _transport_error(error, *, operation, started, phase, events=0, received_text=False):
    # Exception messages/tracebacks may contain URLs, credentials or request data.
    # Keep diagnostics limited to local metadata and the exception class.
    logger.warning(
        "ChatGPT transport failure: operation=%s type=%s phase=%s elapsed=%.1fs events=%d received_text=%s",
        operation, type(error).__name__, phase, time.monotonic() - started, events, received_text,
    )
    if isinstance(error, httpx.ConnectTimeout):
        message = "Connecting to ChatGPT timed out. Check your connection and try again."
    elif isinstance(error, httpx.ReadTimeout):
        message = "ChatGPT stopped sending data before the response completed (read timeout). Try again."
    elif isinstance(error, httpx.TimeoutException):
        message = "The ChatGPT request timed out. Check your connection and try again."
    else:
        message = "ChatGPT connection interrupted. Check your connection and try again."
    return ChatGPTProviderError(message)


def _error(code=None, status=None):
    messages = {
        "subscription_sharing_usage_limit_exceeded":
            "ChatGPT plan usage limit reached. Manage usage at https://chatgpt.com/settings/usage or wait for the limit to reset.",
        "subscription_sharing_usage_unavailable":
            "ChatGPT plan usage is unavailable. Check plan sharing at https://chatgpt.com/settings/usage.",
        "model_not_found": "This model is unavailable. Refresh the ChatGPT model list.",
        "context_length_exceeded": "The conversation exceeds this ChatGPT model's context limit.",
    }
    if code in messages:
        return ChatGPTProviderError(messages[code])
    if status == 401:
        return ChatGPTProviderError("ChatGPT authorization expired. Sign in again.")
    if status == 403:
        return ChatGPTProviderError("ChatGPT access denied. Check account and plan sharing permissions.")
    if status == 429:
        return ChatGPTProviderError("ChatGPT usage limit reached. Manage usage at https://chatgpt.com/settings/usage or try again later.")
    return ChatGPTProviderError("ChatGPT request failed. Check your account and try again.")


def _as_dict(value):
    return value if isinstance(value, dict) else value.model_dump()


def _content(content, role):
    if isinstance(content, str):
        return content
    parts = []
    for part in content or []:
        kind = part.get("type")
        if kind in ("text", "input_text", "output_text"):
            parts.append({"type": "output_text" if role == "assistant" else "input_text",
                          "text": part.get("text", "")})
        elif kind in ("image_url", "input_image") and role == "user":
            image = part.get("image_url")
            image = {"url": image} if isinstance(image, str) else image or {}
            parts.append({"type": "input_image", "image_url": image.get("url", ""),
                          "detail": image.get("detail", part.get("detail", "auto"))})
        else:
            raise ChatGPTProviderError("This message contains an unsupported ChatGPT input type.")
    return parts


def _input(messages):
    """Replay the caller's complete history, including local function results."""
    items = []
    for message in messages:
        role = message.get("role", "user")
        if role == "tool":
            content = message.get("content")
            items.append({"type": "function_call_output", "call_id": message["tool_call_id"],
                          "output": content if isinstance(content, str) else json.dumps(content)})
            continue
        role = "developer" if role == "system" else role
        if role not in ("user", "assistant", "developer"):
            raise ChatGPTProviderError("This message role is not supported by ChatGPT.")
        content = _content(message.get("content"), role)
        if content:
            items.append({"role": role, "content": content})
        for raw in message.get("tool_calls") or []:
            call = _as_dict(raw)
            function = call["function"]
            items.append({"type": "function_call", "call_id": call["id"],
                          "namespace": TOOL_NAMESPACE, "name": function["name"],
                          "arguments": function["arguments"]})
    return items


def _tools(tools):
    functions = []
    for tool in tools or []:
        if tool.get("type") != "function":
            raise ChatGPTProviderError("ChatGPT supports local function tools only in this integration.")
        function = tool["function"]
        functions.append({"type": "function", "name": function["name"],
                          "description": function.get("description", ""),
                          "parameters": function.get("parameters", {"type": "object", "properties": {}}),
                          "strict": function.get("strict", False)})
    if not functions:
        return []
    return [{"type": "namespace", "name": TOOL_NAMESPACE,
             "description": "Soul of Waifu application tools, executed locally with application permissions.",
             "tools": functions}]


async def _sse(response):
    data = []
    lines = response.aiter_lines()
    try:
        async for line in lines:
            if line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
            elif not line and data:
                raw = "\n".join(data)
                data = []
                if raw == "[DONE]":
                    return
                try:
                    event = json.loads(raw)
                    if not isinstance(event, dict):
                        raise ValueError()
                except (ValueError, TypeError):
                    raise ChatGPTProviderError("ChatGPT returned an invalid event stream.") from None
                yield event
    finally:
        # Close the transport in this task while httpx's nested iterators are
        # still alive. Dropping them first can defer httpcore I/O cleanup to
        # async-generator finalizers (notably under Qt's event loop).
        try:
            await response.aclose()
        finally:
            await lines.aclose()
    # A final event need not have a trailing empty line.
    if data and "\n".join(data) != "[DONE]":
        try:
            event = json.loads("\n".join(data))
            if not isinstance(event, dict):
                raise ValueError()
        except (ValueError, TypeError):
            raise ChatGPTProviderError("ChatGPT returned an invalid event stream.") from None
        yield event


def _result(response):
    text, calls = [], []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    text.append(part.get("text", ""))
                elif part.get("type") == "refusal":
                    text.append(part.get("refusal", ""))
        elif item.get("type") == "function_call":
            if item.get("namespace") not in (None, TOOL_NAMESPACE):
                raise ChatGPTProviderError("ChatGPT returned an unexpected tool namespace.")
            calls.append(ChatCompletionMessageToolCall(
                id=item["call_id"], type="function",
                function={"name": item["name"], "arguments": item["arguments"]}))
    return {"content": "".join(text) or None, "tool_calls": calls or None}


class ChatGPTProvider(BaseAIProvider):
    def __init__(self, model=None, auth=None, transport=None):
        if auth is None:
            from app.utils.chatgpt_auth import get_chatgpt_auth
            auth = get_chatgpt_auth()
        self.model = model
        self.auth = auth
        self.transport = transport

    async def _account_id(self):
        account = await asyncio.to_thread(self.auth.active_account)
        if not account or not account.get("connected"):
            raise ChatGPTProviderError("Continue with ChatGPT in Configuration to sign in first.")
        return account["id"]

    async def _token(self, account_id, force_refresh=False):
        return await asyncio.to_thread(self.auth.get_access_token,
                                       force_refresh=force_refresh, expected_account_id=account_id)

    async def list_models(self):
        """The catalog is account-specific; deliberately do not cache it."""
        account_id = await self._account_id()
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=30, transport=self.transport) as client:
                for attempt in range(2):
                    token = await self._token(account_id, force_refresh=bool(attempt))
                    response = await client.get(API_ROOT + "/models", headers={"Authorization": f"Bearer {token}"})
                    if response.status_code == 401 and not attempt:
                        continue
                    if response.is_error:
                        raise _error(status=response.status_code)
                    models = response.json().get("models")
                    if not isinstance(models, list):
                        raise ChatGPTProviderError("ChatGPT returned an invalid model catalog.")
                    return [{"id": m["slug"], "label": m.get("display_name") or m["slug"]}
                            for m in models if m.get("visibility") == "list" and m.get("slug")]
        except httpx.HTTPError as error:
            raise _transport_error(error, operation="models", started=started, phase="catalog") from None
        except (ValueError, TypeError, KeyError):
            raise ChatGPTProviderError("ChatGPT returned an invalid model catalog.") from None

    async def _events(self, messages, tools=None, **kwargs):
        if not self.model:
            raise ChatGPTProviderError("Select a model from the ChatGPT account model list first.")
        payload = {"model": self.model, "input": _input(messages), "store": False, "stream": True}
        if tools:
            payload["tools"] = _tools(tools)
        # The plan-sharing route rejects ordinary chat sampling and token limits.
        effort = kwargs.get("reasoning_effort")
        # The app's "none" means no effort override, as for OpenAIProvider.
        # Some account models reject the literal Responses effort "none".
        if effort and effort != "none":
            payload["reasoning"] = {"effort": effort}
        account_id = await self._account_id()
        started = time.monotonic()
        phase = "request"
        event_count = 0
        received_text = False
        try:
            async with httpx.AsyncClient(timeout=120, transport=self.transport) as client:
                for attempt in range(2):
                    token = await self._token(account_id, force_refresh=bool(attempt))
                    async with client.stream("POST", API_ROOT + "/responses", json=payload,
                                             headers={"Authorization": f"Bearer {token}",
                                                      "Accept": "text/event-stream"}) as response:
                        if response.status_code == 401 and not attempt:
                            continue
                        if response.is_error:
                            await response.aread()
                            try:
                                code = response.json().get("error", {}).get("code")
                            except (ValueError, AttributeError):
                                code = None
                            raise _error(code, response.status_code)
                        phase = "stream"
                        output_items = {}
                        async with aclosing(_sse(response)) as events:
                            async for event in events:
                                event_count += 1
                                kind = event.get("type")
                                if kind in ("response.output_text.delta", "response.refusal.delta") and event.get("delta"):
                                    received_text = True
                                if kind in ("error", "response.failed"):
                                    details = event.get("response", {}).get("error") or event.get("error") or event
                                    raise _error(details.get("code") if isinstance(details, dict) else None)
                                if kind == "response.incomplete":
                                    raise ChatGPTProviderError("ChatGPT response was incomplete. Try again.")
                                if kind == "response.output_item.done":
                                    item = event.get("item")
                                    index = event.get("output_index")
                                    if isinstance(item, dict) and isinstance(index, int):
                                        output_items[index] = item
                                if kind == "response.completed":
                                    final = event.get("response")
                                    if not isinstance(final, dict) or final.get("status") != "completed":
                                        raise ChatGPTProviderError("ChatGPT returned an invalid completion event.")
                                    # The plan-sharing stream may leave terminal output
                                    # empty: completed items arrived in earlier events.
                                    # Never release those tools before terminal success.
                                    if not final.get("output") and output_items:
                                        event = dict(event, response=dict(final, output=[
                                            output_items[index] for index in sorted(output_items)]))
                                    # response.completed is terminal. Do not wait for
                                    # the server/proxy to close the HTTP connection.
                                    yield event
                                    return
                                yield event
                        raise ChatGPTProviderError("ChatGPT connection ended before the response completed. Try again.")
        except httpx.HTTPError as error:
            raise _transport_error(error, operation="response", started=started, phase=phase,
                                   events=event_count, received_text=received_text) from None

    async def generate_stream(self, messages, **kwargs):
        emitted = False
        async with aclosing(self._events(messages, **kwargs)) as events:
            async for event in events:
                if event.get("type") in ("response.output_text.delta", "response.refusal.delta"):
                    delta = event.get("delta", "")
                    emitted = emitted or bool(delta)
                    yield delta
                elif event.get("type") == "response.completed" and not emitted:
                    content = _result(event["response"])["content"]
                    if content:
                        yield content

    async def generate_summary(self, messages, **kwargs):
        async with aclosing(self.generate_stream(messages, **kwargs)) as chunks:
            async for chunk in chunks:
                yield chunk

    async def generate_tool_stream(self, messages, tools=None, **kwargs):
        """Stream visible text, then publish tool calls only on terminal success.

        The completed event includes the full content and tool calls for replay;
        its content must not be appended to text already emitted as deltas.
        """
        emitted = False
        result = None
        async with aclosing(self._events(messages, tools=tools, **kwargs)) as events:
            async for event in events:
                kind = event.get("type")
                if kind in ("response.output_text.delta", "response.refusal.delta"):
                    delta = event.get("delta", "")
                    if delta:
                        emitted = True
                        yield {"type": "text_delta", "text": delta}
                elif kind == "response.completed":
                    result = _result(event["response"])
        # The HTTP stream is closed before callers can execute these tools.
        if not emitted and result["content"]:
            yield {"type": "text_delta", "text": result["content"]}
        yield {"type": "completed", "result": result}

    async def generate(self, messages, tools=None, **kwargs):
        final = None
        async for event in self._events(messages, tools=tools, **kwargs):
            if event.get("type") == "response.completed":
                final = event["response"]
        # Only the terminal response can authorize execution of returned tools.
        return _result(final)
