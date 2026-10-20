"""Run with: python -m unittest discover -s tests -v

Only aiohttp and PyQt6 from requirements.txt are needed. HTTP is local; model
responses in the companion test are scripted, not a live-model evaluation.
"""
import asyncio
from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import aiohttp
from aiohttp import web

from app.configuration.configuration import ConfigurationSettings
from app.utils.ai_clients import mcp_client
from app.utils.ai_clients.mcp_client import MCPClient, MCPManager
from app.utils.soul_companion.soul_companion import (
    DeterministicNarrative, EmotionState, NeurohormoneSystem, Scratchpad,
    SoulCompanion, WebSearchTool,
)


class ParallelMCPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.config = ConfigurationSettings()
        self.config.settings_path = str(Path(self.temp.name) / "settings.json")
        self.config.save_configuration_edit({"main_settings": {}, "user_data": {}})
        MCPManager._instance = None
        self.manager = MCPManager()
        self.manager._config = self.config
        self.requests = []
        self.mode = "json"
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        app = web.Application()
        app.router.add_post("/mcp", self.handle)
        app.router.add_post("/custom", self.handle)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        self.url = f"http://127.0.0.1:{site._server.sockets[0].getsockname()[1]}"
        self.endpoint = patch.object(MCPManager, "PARALLEL_URL", self.url + "/mcp")
        self.endpoint.start()

    async def asyncTearDown(self):
        self.release.set()
        await self.manager.shutdown()
        await self.runner.cleanup()
        self.endpoint.stop()
        MCPManager._instance = None
        self.temp.cleanup()

    async def handle(self, request):
        body = await request.json()
        self.requests.append((request.path, dict(request.headers), body))
        method = body["method"]
        if method == "notifications/initialized":
            return web.Response(status=202)
        if method == "initialize":
            if self.mode == "slow_init":
                self.started.set()
                await self.release.wait()
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "fixture", "version": "1"}}
        elif method == "tools/list":
            result = {"tools": [
                {"name": "web_search", "description": "Find current information.",
                 "inputSchema": {"type": "object", "properties": {
                     "objective": {"type": "string"},
                     "search_queries": {"type": "array", "items": {"type": "string"}}},
                     "required": ["objective", "search_queries"]}},
                {"name": "web_fetch", "description": "Read a web page.",
                 "inputSchema": {"type": "object", "properties": {
                     "urls": {"type": "array", "items": {"type": "string"}}},
                     "required": ["urls"]}},
            ]}
        elif method == "tools/call":
            if self.mode == "http_error":
                return web.Response(status=503)
            if self.mode == "rpc_error":
                return web.json_response({"jsonrpc": "2.0", "id": body["id"],
                                          "error": {"code": -32602, "message": "Invalid arguments"}})
            if self.mode == "malformed":
                return web.Response(text="not json", content_type="application/json")
            if self.mode == "slow":
                self.started.set()
                await self.release.wait()
            result = {"content": [{"type": "text", "text": "MCP specification: https://modelcontextprotocol.io/"}]}
            if self.mode == "quota":
                result = {"isError": True, "content": [{"type": "text", "text": "Free anonymous quota exceeded"}]}
        else:
            raise AssertionError(method)
        response = {"jsonrpc": "2.0", "id": body["id"], "result": result}
        if self.mode == "sse":
            return web.Response(text=f"event: message\ndata: {json.dumps(response)}\n\n",
                                content_type="text/event-stream")
        return web.json_response(response)

    async def enable(self):
        self.config.update_main_setting("enable_mcp", True)
        self.config.update_main_setting("enable_parallel_search", True)
        await self.manager.initialize_all()

    async def search(self):
        return await self.manager.call_tool("parallel_search__web_search", {
            "objective": "Find the MCP specification", "search_queries": ["MCP protocol specification"]})

    async def test_defaults_and_custom_server_are_preserved(self):
        await self.manager.initialize_all()
        self.assertEqual(self.requests, [])
        self.config.update_main_setting("enable_mcp", True)
        self.config.update_main_setting("mcp_server", self.url + "/custom")
        await self.manager.initialize_all()
        self.assertEqual(set(self.manager.clients), {"proxy_server"})
        await self.enable()
        self.assertEqual(set(self.manager.clients), {"proxy_server", "parallel_search"})
        self.assertEqual(self.config.get_main_setting("mcp_server"), self.url + "/custom")
        names = [t["function"]["name"] for t in await self.manager.get_all_tools()]
        self.assertIn("proxy_server__web_search", names)
        self.assertIn("parallel_search__web_search", names)
        self.assertIn("parallel_search__web_fetch", names)
        self.assertEqual(WebSearchTool.name, "web_search")
        # An explicit existing custom URL works without enabling the preset.
        self.config.update_main_setting("enable_parallel_search", False)
        result = await self.manager.call_tool("proxy_server__web_fetch", {"urls": ["https://example.org/"]})
        self.assertTrue(result["success"])

    async def test_disabled_settings_block_cached_preset_without_network(self):
        await self.enable()
        for setting in ("enable_parallel_search", "enable_mcp"):
            with self.subTest(setting=setting):
                self.config.update_main_setting(setting, False)
                count = len(self.requests)
                self.assertEqual(await self.manager.get_all_tools(), [])
                self.assertFalse((await self.search())["success"])
                self.assertEqual(len(self.requests), count)
                self.config.update_main_setting(setting, True)
        self.config.update_main_setting("enable_parallel_search", False)
        client = self.manager.clients["parallel_search"]
        await self.manager.initialize_all()
        self.assertNotIn("parallel_search", self.manager.clients)
        self.assertIsNone(client.session)

    async def test_search_fetch_json_and_sse_with_project_headers(self):
        for mode in ("json", "sse"):
            with self.subTest(mode=mode):
                self.mode = mode
                await self.enable()
                schemas = await self.manager.get_all_tools()
                self.assertEqual(schemas[0]["function"]["parameters"]["required"], ["objective", "search_queries"])
                self.assertTrue((await self.search())["success"])
                result = await self.manager.call_tool("parallel_search__web_fetch", {"urls": ["https://example.org/docs?a=1&b=2"]})
                self.assertIn("https://modelcontextprotocol.io/", result["result"])
                self.assertIsNone(result["speak"])
                await self.manager.shutdown()
        for path, headers, body in self.requests:
            self.assertEqual(path, "/mcp")
            self.assertEqual(headers["User-Agent"], MCPManager.PARALLEL_USER_AGENT)
            self.assertNotIn("Authorization", headers)
            self.assertEqual(body["jsonrpc"], "2.0")
            if body["method"] == "tools/call":
                # No invented process-wide or MCP-transport conversation ID.
                self.assertNotIn("session_id", body["params"]["arguments"])
        last_call = [b for _, _, b in self.requests if b["method"] == "tools/call"][-1]
        self.assertEqual(last_call["params"]["arguments"]["urls"], ["https://example.org/docs?a=1&b=2"])

    async def test_errors_return_to_caller_without_provider_fallback(self):
        await self.enable()
        for mode, text in (("http_error", "503"), ("rpc_error", "Invalid arguments"),
                           ("quota", "quota exceeded"), ("malformed", "")):
            with self.subTest(mode=mode):
                self.mode = mode
                count = len(self.requests)
                result = await self.search()
                self.assertFalse(result["success"])
                self.assertIn(text, result["result"])
                self.assertEqual(len(self.requests), count + 1)
                self.assertEqual(self.requests[-1][0], "/mcp")

    async def test_timeout_and_cancellation(self):
        await self.enable()
        self.mode = "slow"
        # Use the real timeout machinery with a shorter test deadline.
        timeout_type = aiohttp.ClientTimeout
        with patch.object(mcp_client.aiohttp, "ClientTimeout", side_effect=lambda **kw: timeout_type(total=0.03)):
            result = await self.search()
        self.assertFalse(result["success"])
        self.started.clear()
        task = asyncio.create_task(self.search())
        await self.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        session = self.manager.clients["parallel_search"].session
        await self.manager.shutdown()
        self.assertTrue(session.closed)

    async def test_cancelled_initialization_closes_session(self):
        self.mode = "slow_init"
        client = MCPClient("parallel_search", self.url + "/mcp",
                           headers={"User-Agent": MCPManager.PARALLEL_USER_AGENT})
        task = asyncio.create_task(client.start())
        await self.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertIsNone(client.session)

    async def test_scripted_companion_consumes_search_then_fetch_results(self):
        await self.enable()
        companion = SoulCompanion.__new__(SoulCompanion)
        companion.sys = SimpleNamespace(configuration_settings=self.config, character_name="Test companion")
        companion.mcp_manager = self.manager
        companion.plugins = SimpleNamespace(_plugins={}, get=lambda name: None)
        companion.hormones = NeurohormoneSystem()
        companion.emotion = EmotionState()
        companion.scratchpad = Scratchpad()
        companion.narrative = DeterministicNarrative()
        companion._last_spoke = datetime.now()
        companion._last_os_window = "Desktop"
        companion._tool_call_history = []
        companion._executed_tools_in_chain = set()
        companion._session_history = []
        companion._get_memory_snapshot = lambda **kw: ""
        companion._get_char_info = lambda: {}
        companion._get_user_name = lambda: "Test user"
        companion._get_recent_chat_history = lambda **kw: ""
        companion._can_speak = lambda **kw: True
        companion._apply_emotion_to_avatar = lambda emotion: None
        pending = []
        companion.event_bus = SimpleNamespace(emit_threadsafe=lambda kind, payload: pending.append({"type": kind, "payload": payload}))
        prompts = []
        async def model(system, user, **kwargs):
            prompts.append((system, user))
            self.assertIn("parallel_search__web_search", system)
            self.assertIn("parallel_search__web_fetch", system)
            if len(prompts) == 1:
                return {"action": "use_tool", "tool_name": "parallel_search__web_search", "tool_args": {
                    "objective": "Find the MCP specification", "search_queries": ["MCP protocol specification"]}}, ""
            self.assertIn("Latest Tool Result:", user)
            self.assertIn("https://modelcontextprotocol.io/", user)
            if len(prompts) == 2:
                return {"action": "use_tool", "tool_name": "parallel_search__web_fetch", "tool_args": {
                    "urls": ["https://modelcontextprotocol.io/"]}}, ""
            return {"action": "idle"}, ""
        companion._llm_call_stream = model
        await companion._handle_event({"type": "tool_complete", "payload": {"text": "Find and read the MCP specification"}})
        while pending:
            await companion._handle_event(pending.pop(0))
        self.assertEqual(len(prompts), 3)
        calls = [b["params"]["name"] for _, _, b in self.requests if b["method"] == "tools/call"]
        self.assertEqual(calls, ["web_search", "web_fetch"])
        # Existing local approval remains ahead of local tool execution.
        tool = SimpleNamespace(execute=AsyncMock(), needs_approval=lambda args: True,
                               get_confirmation_summary=lambda args: "Run local action", name="local")
        companion.plugins = SimpleNamespace(get=lambda name: tool)
        companion.request_approval = AsyncMock(return_value=False)
        self.assertFalse((await companion._execute_tool("local", {}))["success"])
        tool.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
