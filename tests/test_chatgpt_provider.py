"""Offline protocol tests: python -m unittest discover -s tests -p test_chatgpt_provider.py"""

import json
import unittest

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

    async def test_event_after_completion_is_consumed(self):
        provider = self.provider(lambda r: sse(completed(message("answer")), {"type": "error"}))
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
        with self.assertRaises(ChatGPTProviderError) as cm:
            await provider.generate([])
        self.assertNotIn("test-secret", str(cm.exception))

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
