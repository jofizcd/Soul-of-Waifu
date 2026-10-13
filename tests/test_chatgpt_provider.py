"""Offline protocol tests: python -m unittest discover -s tests -p test_chatgpt_provider.py"""

import json
import unittest
from unittest.mock import patch

import httpx

from app.utils.ai_clients.providers.chatgpt_provider import (
    API_ROOT, TOOL_NAMESPACE, ChatGPTProvider, ChatGPTProviderError,
)


class FakeAuth:
    def __init__(self):
        self.refreshes = []
        self.account_id = "test-account"

    def active_account(self):
        return {"id": self.account_id, "connected": True}

    def get_access_token(self, force_refresh=False, expected_account_id=None):
        if expected_account_id != self.account_id:
            raise RuntimeError("Account changed")
        self.refreshes.append(force_refresh)
        return "fresh-secret" if force_refresh else "test-secret"


def message(text):
    return {"type": "message", "content": [{"type": "output_text", "text": text}]}


def completed(*output):
    return {"type": "response.completed", "response": {"status": "completed", "output": list(output)}}


def sse(*events):
    body = ": keepalive\n\n" + "".join("event: " + e["type"] + "\ndata: " + json.dumps(e) + "\n\n" for e in events)
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    def provider(self, handler, model="test-model"):
        self.auth = FakeAuth()
        return ChatGPTProvider(model=model, auth=self.auth, transport=httpx.MockTransport(handler))

    async def test_stream_maps_context_and_omits_unsupported_fields(self):
        requests = []

        def handler(request):
            requests.append(json.loads(request.content))
            self.assertEqual(str(request.url), API_ROOT + "/responses")
            self.assertEqual(request.headers["Authorization"], "Bearer test-secret")
            return sse({"type": "response.output_text.delta", "delta": "Hello"}, completed(message("Hello")))

        provider = self.provider(handler)
        messages = [{"role": "system", "content": "Be helpful"},
                    {"role": "assistant", "content": "Earlier answer"},
                    {"role": "user", "content": [{"type": "text", "text": "Look"},
                     {"type": "image_url", "image_url": {"url": "data:image/png;base64,aA==", "detail": "low"}}]}]
        chunks = [c async for c in provider.generate_stream(messages, temperature=.7, max_tokens=900, top_p=.9, stop=["stop"])]
        self.assertEqual(chunks, ["Hello"])
        payload = requests[0]
        self.assertEqual(set(payload), {"model", "input", "store", "stream"})
        self.assertFalse(payload["store"])
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["input"][0]["role"], "developer")
        self.assertEqual(payload["input"][1]["content"], "Earlier answer")
        self.assertEqual(payload["input"][2]["content"][1]["type"], "input_image")
        self.assertEqual(messages[0]["role"], "system")  # no in-place mutation

    async def test_tools_are_namespaced_and_replay_with_call_ids(self):
        requests = []
        call = {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": '{"q":"x"}', "namespace": TOOL_NAMESPACE}

        def handler(request):
            requests.append(json.loads(request.content))
            return sse({"type": "response.function_call_arguments.delta", "delta": "invalid partial"}, completed(call))

        provider = self.provider(handler)
        tools = [{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}}]
        result = await provider.generate([{"role": "user", "content": "Look up x"}], tools=tools)
        returned = result["tool_calls"][0]
        self.assertEqual(returned.id, "call_1")
        self.assertEqual(returned.function.name, "lookup")
        self.assertEqual(json.loads(returned.function.arguments), {"q": "x"})
        await provider.generate([{"role": "assistant", "content": None, "tool_calls": [returned.model_dump()]},
                                 {"role": "tool", "tool_call_id": returned.id, "content": "Found it"}], tools=tools)
        self.assertEqual(requests[0]["tools"][0]["type"], "namespace")
        self.assertFalse(requests[0]["tools"][0]["tools"][0]["strict"])
        self.assertEqual(requests[1]["input"][0], call)
        self.assertEqual(requests[1]["input"][1], {"type": "function_call_output", "call_id": "call_1", "output": "Found it"})

    async def test_summary_and_final_only_stream(self):
        provider = self.provider(lambda r: sse(completed(message("A summary"))))
        self.assertEqual([c async for c in provider.generate_summary([{"role": "user", "content": "Summarize"}])], ["A summary"])

    async def test_tool_stream_delivers_text_before_completion_but_holds_tool_calls(self):
        import asyncio

        waiting, release = asyncio.Event(), asyncio.Event()
        call = {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"}
        payloads = []

        class GatedStream(httpx.AsyncByteStream):
            closed = False

            async def __aiter__(self):
                for event in (
                    {"type": "response.output_text.delta", "delta": "Checking"},
                    {"type": "response.function_call_arguments.delta", "delta": "{"},
                    {"type": "response.output_item.done", "output_index": 0, "item": call},
                ):
                    yield ("data: " + json.dumps(event) + "\n\n").encode()
                waiting.set()
                await release.wait()
                yield ("data: " + json.dumps(completed(message("Checking"), call)) + "\n\n").encode()

            async def aclose(self):
                self.closed = True

        stream = GatedStream()

        def handler(request):
            payloads.append(json.loads(request.content))
            return httpx.Response(200, stream=stream)

        provider = self.provider(handler)
        tools = [{"type": "function", "function": {"name": "lookup"}}]
        events = provider.generate_tool_stream([], tools=tools, reasoning_effort="low")
        self.assertEqual(await anext(events), {"type": "text_delta", "text": "Checking"})
        next_event = asyncio.create_task(anext(events))
        await asyncio.wait_for(waiting.wait(), 2)
        self.assertFalse(next_event.done())
        release.set()
        terminal = await asyncio.wait_for(next_event, 2)
        self.assertTrue(stream.closed)
        self.assertEqual(terminal["type"], "completed")
        self.assertEqual(terminal["result"]["content"], "Checking")
        self.assertEqual(terminal["result"]["tool_calls"][0].function.name, "lookup")
        self.assertEqual(terminal["result"]["tool_calls"][0].function.arguments, "{}")
        self.assertEqual(payloads[0]["tools"][0]["tools"][0]["name"], "lookup")
        self.assertEqual(payloads[0]["reasoning"], {"effort": "low"})
        with self.assertRaises(StopAsyncIteration):
            await anext(events)

    async def test_tool_stream_fallback_and_refusal_do_not_duplicate_text(self):
        refusal = {"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}
        cases = [
            ([], message("Answer"), "Answer"),
            ([{"type": "response.output_text.delta", "delta": "Answer"}], message("Answer"), "Answer"),
            ([{"type": "response.refusal.delta", "delta": "No"}], refusal, "No"),
            ([], refusal, "No"),
            ([], {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"}, ""),
        ]
        for deltas, output, expected in cases:
            with self.subTest(deltas=deltas, output=output["type"]):
                provider = self.provider(lambda r: sse(*deltas, completed(output)))
                events = [event async for event in provider.generate_tool_stream([])]
                self.assertEqual("".join(e["text"] for e in events if e["type"] == "text_delta"), expected)
                self.assertEqual(sum(e["type"] == "completed" for e in events), 1)
                self.assertEqual(events[-1]["type"], "completed")
                self.assertEqual(events[-1]["result"]["content"], expected or None)

    async def test_tool_stream_failure_after_text_never_publishes_calls_or_completion(self):
        call = {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"}
        for ending in ([], [{"type": "response.incomplete"}], [{"type": "response.failed"}], [{"type": "error"}]):
            with self.subTest(ending=ending):
                provider = self.provider(lambda r: sse(
                    {"type": "response.output_text.delta", "delta": "Partial"},
                    {"type": "response.output_item.done", "output_index": 0, "item": call},
                    *ending))
                events = []
                with self.assertRaises(ChatGPTProviderError):
                    async for event in provider.generate_tool_stream([]):
                        events.append(event)
                self.assertEqual(events, [{"type": "text_delta", "text": "Partial"}])

    async def test_empty_terminal_output_uses_completed_items_in_order(self):
        call = {"type": "function_call", "call_id": "call_1", "name": "lookup",
                "arguments": "{}", "namespace": TOOL_NAMESPACE}
        provider = self.provider(lambda r: sse(
            {"type": "response.output_item.done", "output_index": 1, "item": call},
            {"type": "response.output_item.done", "output_index": 0, "item": message("Checking")},
            completed()))
        result = await provider.generate([])
        self.assertEqual(result["content"], "Checking")
        self.assertEqual(result["tool_calls"][0].function.name, "lookup")

    async def test_completed_tool_item_is_not_executable_on_failed_stream(self):
        call = {"type": "function_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"}
        for terminal in ([], [{"type": "response.failed", "response": {"error": {"code": "subscription_sharing_usage_limit_exceeded"}}}]):
            with self.subTest(terminal=terminal):
                provider = self.provider(lambda r: sse(
                    {"type": "response.output_item.done", "output_index": 0, "item": call}, *terminal))
                with self.assertRaises(ChatGPTProviderError):
                    await provider.generate([])

    async def test_refusal_is_returned_as_text(self):
        provider = self.provider(lambda r: sse(completed({"type": "message", "content": [{"type": "refusal", "refusal": "Cannot help"}]})))
        self.assertEqual((await provider.generate([]))["content"], "Cannot help")

    async def test_failures_after_deltas_never_return_success(self):
        cases = [
            ({"type": "response.failed", "response": {"error": {"code": "subscription_sharing_usage_limit_exceeded", "message": "test-secret"}}}, "limit reached"),
            ({"type": "response.failed", "response": {"error": {"code": "subscription_sharing_usage_unavailable"}}}, "unavailable"),
            ({"type": "response.incomplete"}, "incomplete"),
            ({"type": "error", "message": "test-secret"}, "failed"),
        ]
        for event, expected in cases:
            with self.subTest(event=event):
                provider = self.provider(lambda r: sse({"type": "response.output_text.delta", "delta": "Partial"}, event))
                with self.assertRaises(ChatGPTProviderError) as cm:
                    await provider.generate([])
                self.assertIn(expected, str(cm.exception))
                self.assertNotIn("test-secret", str(cm.exception))

    async def test_interrupted_stream_fails_in_chat_and_memory(self):
        provider = self.provider(lambda r: sse({"type": "response.output_text.delta", "delta": "Partial"}))
        for method in (provider.generate_stream, provider.generate_summary):
            with self.subTest(method=method.__name__):
                received = []
                with self.assertRaisesRegex(ChatGPTProviderError, "before the response completed"):
                    async for chunk in method([]):
                        received.append(chunk)
                self.assertEqual(received, ["Partial"])

    async def test_done_sentinel_is_not_success(self):
        provider = self.provider(lambda r: httpx.Response(200, content="data: [DONE]\n\n"))
        with self.assertRaises(ChatGPTProviderError):
            await provider.generate([])

    async def test_completed_response_does_not_wait_for_trailing_events(self):
        provider = self.provider(lambda r: sse(completed(message("answer")), {"type": "error"}))
        self.assertEqual((await provider.generate([]))["content"], "answer")

    async def test_completed_response_closes_stream_without_another_read(self):
        class TerminalStream(httpx.AsyncByteStream):
            closed = False
            read_after_completion = False

            async def __aiter__(self):
                yield ("data: " + json.dumps(completed(message("answer"))) + "\n\n").encode()
                self.read_after_completion = True
                raise httpx.ReadTimeout("secret-token")

            async def aclose(self):
                self.closed = True

        for method in ("generate", "generate_stream", "generate_summary"):
            with self.subTest(method=method):
                stream = TerminalStream()
                provider = self.provider(lambda r: httpx.Response(200, stream=stream))
                if method == "generate":
                    self.assertEqual((await provider.generate([]))["content"], "answer")
                else:
                    self.assertEqual("".join([c async for c in getattr(provider, method)([])]), "answer")
                self.assertFalse(stream.read_after_completion)
                self.assertTrue(stream.closed)

    async def test_real_http_stream_closes_on_completion_early_close_and_cancel(self):
        import asyncio
        import gc
        import sys

        from httpcore._async.http11 import HTTP11ConnectionByteStream

        # MockTransport omits httpcore's nested async iterators/cancel scopes.
        # Keep a real chunked HTTP response open after the last SSE event.
        loop = asyncio.get_running_loop()
        loop_errors, unraisable, close_tasks = [], [], []
        previous_handler = loop.get_exception_handler()
        original_close = HTTP11ConnectionByteStream.aclose

        async def tracked_close(stream):
            if not stream._closed:
                close_tasks.append(asyncio.current_task())
            await original_close(stream)

        loop.set_exception_handler(lambda _loop, context: loop_errors.append(context))
        try:
            with patch.object(sys, "unraisablehook", unraisable.append), \
                    patch.object(HTTP11ConnectionByteStream, "aclose", tracked_close):
                for mode in ("completed", "close", "cancel", "tool_completed", "tool_close", "tool_cancel"):
                    with self.subTest(mode=mode):
                        action = mode.removeprefix("tool_")
                        disconnected = loop.create_future()
                        requests = []

                        async def serve(reader, writer):
                            try:
                                head = await reader.readuntil(b"\r\n\r\n")
                                requests.append(head)
                                length = next(int(line.split(b":", 1)[1]) for line in head.split(b"\r\n")
                                              if line.lower().startswith(b"content-length:"))
                                await reader.readexactly(length)
                                event = completed(message("answer")) if action == "completed" else {
                                    "type": "response.output_text.delta", "delta": "partial"}
                                body = ("data: " + json.dumps(event) + "\n\n").encode()
                                writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
                                             b"Transfer-Encoding: chunked\r\n\r\n")
                                writer.write(f"{len(body):x}\r\n".encode() + body + b"\r\n")
                                await writer.drain()
                                await reader.read()  # No EOF until the client closes.
                            finally:
                                writer.close()
                                await writer.wait_closed()
                                if not disconnected.done():
                                    disconnected.set_result(None)

                        server = await asyncio.start_server(serve, "127.0.0.1", 0)
                        port = server.sockets[0].getsockname()[1]
                        async with server:
                            with patch("app.utils.ai_clients.providers.chatgpt_provider.API_ROOT",
                                       f"http://127.0.0.1:{port}"):
                                provider = ChatGPTProvider(model="test-model", auth=FakeAuth())
                                stream_method = provider.generate_tool_stream if mode.startswith("tool_") else provider.generate_stream
                                if action == "completed":
                                    async def complete():
                                        if mode.startswith("tool_"):
                                            events = [event async for event in stream_method([])]
                                            self.assertEqual(events[0], {"type": "text_delta", "text": "answer"})
                                            self.assertEqual(events[-1]["type"], "completed")
                                            return events[-1]["result"]
                                        return await provider.generate([])
                                    task = asyncio.create_task(complete())
                                    self.assertEqual((await asyncio.wait_for(task, 3))["content"], "answer")
                                elif action == "close":
                                    async def read_and_close():
                                        chunks = stream_method([])
                                        expected = {"type": "text_delta", "text": "partial"} if mode.startswith("tool_") else "partial"
                                        self.assertEqual(await anext(chunks), expected)
                                        await chunks.aclose()
                                    task = asyncio.create_task(read_and_close())
                                    await asyncio.wait_for(task, 3)
                                else:
                                    first_chunk = asyncio.Event()

                                    async def read_until_cancelled():
                                        async for chunk in stream_method([]):
                                            first_chunk.set()
                                    task = asyncio.create_task(read_until_cancelled())
                                    await asyncio.wait_for(first_chunk.wait(), 3)
                                    task.cancel()
                                    with self.assertRaises(asyncio.CancelledError):
                                        await task
                                await asyncio.wait_for(disconnected, 3)
                                self.assertIs(close_tasks[-1], task)
                                self.assertEqual(len(requests), 1)
                        gc.collect()
                        for _ in range(10):
                            await asyncio.sleep(0)
                self.assertEqual(loop_errors, [])
                self.assertEqual(unraisable, [])
        finally:
            loop.set_exception_handler(previous_handler)

    async def test_unsuccessful_terminal_event_cannot_be_overridden_by_completion(self):
        for terminal in (
            {"type": "response.incomplete"},
            {"type": "response.failed", "response": {"error": {"code": "context_length_exceeded"}}},
            {"type": "error", "code": "model_not_found"},
            {"type": "response.completed", "response": {"status": "in_progress"}},
        ):
            with self.subTest(terminal=terminal["type"]):
                provider = self.provider(lambda r: sse(terminal, completed(message("invalid success"))))
                with self.assertRaises(ChatGPTProviderError):
                    await provider.generate([])

    async def test_401_refreshes_once_before_streaming(self):
        requests = []

        def handler(request):
            requests.append(request.headers["Authorization"])
            return httpx.Response(401) if len(requests) == 1 else sse(completed(message("OK")))

        provider = self.provider(handler)
        self.assertEqual((await provider.generate([]))["content"], "OK")
        self.assertEqual(requests, ["Bearer test-secret", "Bearer fresh-secret"])
        self.assertEqual(self.auth.refreshes, [False, True])

    async def test_permanent_401_is_bounded_and_safe(self):
        provider = self.provider(lambda r: httpx.Response(401, json={"error": {"message": "test-secret"}}))
        with self.assertRaisesRegex(ChatGPTProviderError, "Sign in again"):
            await provider.generate([])
        self.assertEqual(len(self.auth.refreshes), 2)

    async def test_account_switch_during_401_does_not_retry_as_another_account(self):
        requests = []

        def handler(request):
            requests.append(request)
            self.auth.account_id = "another-account"
            return httpx.Response(401)

        provider = self.provider(handler)
        with self.assertRaisesRegex(RuntimeError, "Account changed"):
            await provider.generate([])
        self.assertEqual(len(requests), 1)
        self.assertEqual(self.auth.refreshes, [False])

    async def test_http_limit_error_is_actionable(self):
        provider = self.provider(lambda r: httpx.Response(429, json={"error": {"code": "subscription_sharing_usage_unavailable"}}))
        with self.assertRaisesRegex(ChatGPTProviderError, "plan sharing"):
            await provider.generate([])

    async def test_transport_exception_does_not_leak_credentials(self):
        def handler(request):
            raise httpx.ReadError("test-secret", request=request)

        provider = self.provider(handler)
        with self.assertLogs("app.utils.ai_clients.providers.chatgpt_provider", level="WARNING") as logs:
            with self.assertRaises(ChatGPTProviderError) as cm:
                await provider.generate([])
        self.assertNotIn("test-secret", str(cm.exception))
        self.assertNotIn("test-secret", " ".join(logs.output))
        self.assertIn("type=ReadError phase=request", logs.output[0])
        self.assertIsNone(logs.records[0].exc_info)

    async def test_transport_failure_is_classified_without_retry_or_sensitive_logs(self):
        for error_type, expected in (
            (httpx.ConnectTimeout, "Connecting to ChatGPT timed out"),
            (httpx.ReadTimeout, "read timeout"),
            (httpx.WriteTimeout, "request timed out"),
            (httpx.ConnectError, "connection interrupted"),
            (httpx.RemoteProtocolError, "connection interrupted"),
        ):
            with self.subTest(error=error_type.__name__):
                requests = []

                def handler(request):
                    requests.append(request)
                    raise error_type("secret-token private-prompt", request=request)

                provider = self.provider(handler)
                with self.assertLogs("app.utils.ai_clients.providers.chatgpt_provider", level="WARNING") as logs:
                    with self.assertRaisesRegex(ChatGPTProviderError, expected):
                        await provider.generate([{"role": "user", "content": "private-prompt"}])
                self.assertEqual(len(requests), 1)
                self.assertIn("type=" + error_type.__name__, logs.output[0])
                self.assertIn("events=0 received_text=False", logs.output[0])
                for private in ("secret-token", "private-prompt", "test-secret", "Authorization"):
                    self.assertNotIn(private, " ".join(logs.output))

    async def test_cancel_is_not_swallowed(self):
        import asyncio

        def handler(request):
            raise asyncio.CancelledError()

        provider = self.provider(handler)
        with self.assertRaises(asyncio.CancelledError):
            await provider.generate([])

    async def test_catalog_filters_visibility_preserves_order_and_refreshes(self):
        requests = []

        def handler(request):
            requests.append(str(request.url))
            return httpx.Response(200, json={"models": [
                {"slug": "hidden", "visibility": "hidden"},
                {"slug": "b", "display_name": "Beta", "visibility": "list"},
                {"slug": "a", "visibility": "list"}]})

        provider = self.provider(handler, model=None)
        for _ in range(2):
            self.assertEqual(await provider.list_models(), [{"id": "b", "label": "Beta"}, {"id": "a", "label": "a"}])
        self.assertEqual(requests, [API_ROOT + "/models"] * 2)

    async def test_missing_model_does_not_make_request(self):
        def handler(request):
            self.fail("Request should not have been made")

        with self.assertRaisesRegex(ChatGPTProviderError, "Select a model"):
            await self.provider(handler, model=None).generate([])

    async def test_invalid_sse_is_safe(self):
        for content in ("data: not-json-test-secret\n\n", "data: []\n\n"):
            with self.subTest(content=content):
                provider = self.provider(lambda r: httpx.Response(200, content=content))
                with self.assertRaisesRegex(ChatGPTProviderError, "invalid event stream"):
                    await provider.generate([])

    async def test_unsupported_audio_and_hosted_tools_fail_before_request(self):
        provider = self.provider(lambda r: self.fail("Unexpected HTTP request"))
        with self.assertRaisesRegex(ChatGPTProviderError, "unsupported ChatGPT input"):
            await provider.generate([{"role": "user", "content": [{"type": "input_audio"}]}])
        with self.assertRaisesRegex(ChatGPTProviderError, "local function tools"):
            await provider.generate([], tools=[{"type": "tool_search"}])

    async def test_all_application_kwargs_only_forward_reasoning(self):
        payloads = []

        def handler(request):
            payloads.append(json.loads(request.content))
            return sse(completed(message("ok")))

        provider = self.provider(handler)
        for effort in ("none", "medium"):
            await provider.generate([], stop=["end"], temperature=.7, top_p=.9,
                max_tokens=4096, frequency_penalty=.5, presence_penalty=.2,
                reasoning_effort=effort, reasoning_mode=False)
        for payload, effort in zip(payloads, ("none", "medium")):
            if effort == "none":
                self.assertEqual(set(payload), {"model", "input", "store", "stream"})
            else:
                self.assertEqual(set(payload), {"model", "input", "store", "stream", "reasoning"})
                self.assertEqual(payload["reasoning"], {"effort": effort})

    async def test_multiple_tools_replay_in_full_without_names_or_vendor_fields(self):
        requests = []
        calls = [{"type": "function_call", "call_id": "call_" + str(i),
                  "name": "lookup_" + str(i), "arguments": "{}", "namespace": TOOL_NAMESPACE}
                 for i in range(2)]

        def handler(request):
            requests.append(json.loads(request.content))
            return sse(completed(*calls))

        provider = self.provider(handler)
        result = await provider.generate([])
        history = [{"role": "user", "content": "start"},
                   {"role": "assistant", "content": "checking", "tool_calls": result["tool_calls"]}]
        history.extend({"role": "tool", "tool_call_id": c.id, "name": c.function.name, "content": "value"}
                       for c in result["tool_calls"])
        history.append({"role": "user", "content": "finish"})
        await provider.generate(history)
        items = requests[-1]["input"]
        self.assertEqual(items[2:4], calls)
        self.assertEqual([i["call_id"] for i in items[4:6]], ["call_0", "call_1"])
        self.assertEqual(items[-1], {"role": "user", "content": "finish"})

    async def test_streaming_refusal_no_duplicate_terminal_text(self):
        provider = self.provider(lambda r: sse(
            {"type": "response.refusal.delta", "delta": "Cannot "},
            {"type": "response.refusal.delta", "delta": "help"},
            completed({"type": "message", "content": [{"type": "refusal", "refusal": "Cannot help"}]})))
        self.assertEqual("".join([c async for c in provider.generate_stream([])]), "Cannot help")

    async def test_midstream_auth_error_is_not_retried(self):
        calls = []

        def handler(request):
            calls.append(request)
            return sse({"type": "response.output_text.delta", "delta": "partial"},
                       {"type": "error", "code": "invalid_api_key", "status": 401})

        with self.assertRaises(ChatGPTProviderError):
            await self.provider(handler).generate([])
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.auth.refreshes, [False])

    async def test_midstream_timeout_and_cancel_close_transport(self):
        import asyncio

        class BrokenStream(httpx.AsyncByteStream):
            def __init__(self, error):
                self.error, self.closed = error, False

            async def __aiter__(self):
                yield b'data: {"type":"response.output_text.delta","delta":"partial"}\n\n'
                raise self.error

            async def aclose(self):
                self.closed = True

        for error, expected in ((httpx.ReadTimeout("secret-token"), ChatGPTProviderError),
                                (asyncio.CancelledError(), asyncio.CancelledError)):
            with self.subTest(expected=expected):
                stream = BrokenStream(error)
                provider = self.provider(lambda r: httpx.Response(200, stream=stream))
                with self.assertRaises(expected) as cm:
                    await provider.generate([])
                self.assertNotIn("secret-token", str(cm.exception))
                self.assertTrue(stream.closed)

    async def test_multiline_sse_and_final_event_without_blank_line(self):
        event = completed(message("complete"))
        body = "\n".join("data: " + line for line in json.dumps(event, indent=2).splitlines())
        provider = self.provider(lambda r: httpx.Response(200, content=body))
        self.assertEqual((await provider.generate([]))["content"], "complete")

    async def test_model_catalog_401_refresh_and_malformed_payload(self):
        count = 0

        def handler(request):
            nonlocal count
            count += 1
            return httpx.Response(401) if count == 1 else httpx.Response(200, json={"models": []})

        provider = self.provider(handler)
        self.assertEqual(await provider.list_models(), [])
        self.assertEqual(self.auth.refreshes, [False, True])
        malformed = self.provider(lambda r: httpx.Response(200, json={"models": "not-a-list"}))
        with self.assertRaisesRegex(ChatGPTProviderError, "invalid model catalog"):
            await malformed.list_models()


if __name__ == "__main__":
    unittest.main()
