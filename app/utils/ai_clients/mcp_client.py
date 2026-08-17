import logging
import asyncio
import json
import aiohttp
from typing import Dict, Any, List, Optional, AsyncIterator, Tuple
from urllib.parse import urljoin
from app.configuration import configuration

logger = logging.getLogger("MCP Client")

async def _iter_sse_events(content: aiohttp.StreamReader) -> AsyncIterator[Tuple[str, str]]:
    """
    Parses a raw byte stream according to the Server-Sent Events wire format
    and yields (event_type, data) pairs.
    """
    event_type = "message"
    data_lines: List[str] = []

    async for raw_line in content:
        line = raw_line.decode("utf-8", errors="ignore").rstrip("\r\n")

        if line == "":
            if data_lines:
                yield event_type, "\n".join(data_lines)
            event_type = "message"
            data_lines = []
            continue

        if line.startswith(":"):
            continue

        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
        elif line.startswith("data:"):
            data_lines.append(line[len("data:"):].strip())


class MCPClient:
    """
    MCP Client that connects to a remote MCP server.
    """

    _PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url.strip()
        self.session: Optional[aiohttp.ClientSession] = None

        self.transport: Optional[str] = None
        self.protocol_version: Optional[str] = None
        self.session_id: Optional[str] = None

        self.post_url: Optional[str] = None
        self._sse_response: Optional[aiohttp.ClientResponse] = None

        self._message_id = 1
        self._receive_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[int, "asyncio.Future"] = {}

    def _next_id(self) -> int:
        req_id = self._message_id
        self._message_id += 1
        return req_id

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> bool:
        self.session = aiohttp.ClientSession()
        try:
            logger.info(f"Connecting to MCP server '{self.name}' at: {self.url}")

            if await self._try_streamable_http():
                pass
            elif await self._try_legacy_sse():
                pass
            else:
                logger.error(
                    f"MCP server '{self.name}' did not respond to either the "
                    f"Streamable HTTP or the legacy HTTP+SSE handshake."
                )
                await self.stop()
                return False

            await self._send_notification("notifications/initialized", {})
            logger.info(
                f"MCP server '{self.name}' initialized via {self.transport} "
                f"transport (protocol {self.protocol_version})."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MCP client '{self.name}': {e}")
            await self.stop()
            return False

    async def _try_streamable_http(self) -> bool:
        """Attempts the current single-endpoint Streamable HTTP handshake."""
        init_id = self._next_id()
        init_request = {
            "jsonrpc": "2.0",
            "id": init_id,
            "method": "initialize",
            "params": {
                "protocolVersion": self._PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "Soul-of-Waifu", "version": "2.4.5"}
            }
        }
        headers = {"Accept": "application/json, text/event-stream"}

        try:
            async with self.session.post(
                self.url, json=init_request, headers=headers,
                timeout=aiohttp.ClientTimeout(total=10.0)
            ) as resp:
                if resp.status in (400, 404, 405, 406):
                    logger.info(
                        f"'{self.name}' rejected Streamable HTTP POST "
                        f"(HTTP {resp.status}); trying legacy SSE transport."
                    )
                    return False
                if resp.status >= 400:
                    raise RuntimeError(f"Streamable HTTP initialize failed: HTTP {resp.status}")

                session_id = resp.headers.get("Mcp-Session-Id")
                if session_id:
                    self.session_id = session_id

                content_type = resp.headers.get("Content-Type", "")
                if "text/event-stream" in content_type:
                    result = await self._consume_sse_response(resp, init_id)
                else:
                    body = await resp.json(content_type=None)
                    if "error" in body:
                        raise RuntimeError(f"Initialize error: {body['error']}")
                    result = body.get("result")

                if not result:
                    return False

                self.protocol_version = result.get("protocolVersion", self._PROTOCOL_VERSION)
                self.post_url = self.url
                self.transport = "streamable_http"
                return True
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.info(
                f"Streamable HTTP attempt failed for '{self.name}' ({e}); "
                f"trying legacy SSE transport."
            )
            return False

    async def _try_legacy_sse(self) -> bool:
        """Falls back to the deprecated two-endpoint HTTP+SSE transport."""
        try:
            self._sse_response = await self.session.get(
                self.url, timeout=aiohttp.ClientTimeout(total=10.0)
            )
            if self._sse_response.status != 200:
                logger.info(f"'{self.name}' legacy SSE GET failed: HTTP {self._sse_response.status}")
                return False

            self._receive_task = asyncio.create_task(self._read_sse_stream())

            for _ in range(50):
                if self.post_url:
                    break
                await asyncio.sleep(0.1)

            if not self.post_url:
                logger.error(f"Timed out waiting for SSE endpoint initialization from {self.url}")
                return False

            self.transport = "legacy_sse"

            result = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "Soul-of-Waifu", "version": "2.4.5"}
            })
            if result is None:
                self.transport = None
                return False

            self.protocol_version = "2024-11-05"
            logger.info(
                f"'{self.name}' connected via the legacy HTTP+SSE transport "
                f"(deprecated since MCP spec 2025-03-26 - consider asking the "
                f"server operator for a Streamable HTTP endpoint)."
            )
            return True
        except Exception as e:
            logger.info(f"Legacy SSE attempt failed for '{self.name}': {e}")
            return False

    async def stop(self):
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None

        if self._sse_response:
            self._sse_response.close()
            self._sse_response = None

        if self.session:
            await self.session.close()
            self.session = None

        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        self.post_url = None
        self.session_id = None
        self.protocol_version = None
        self.transport = None

    # ------------------------------------------------------------------
    # Legacy HTTP+SSE stream reading
    # ------------------------------------------------------------------

    async def _read_sse_stream(self):
        if not self._sse_response:
            return

        try:
            async for event_type, data_str in _iter_sse_events(self._sse_response.content):
                if event_type == "endpoint":
                    self.post_url = urljoin(self.url, data_str)
                    logger.info(f"Resolved remote MCP POST endpoint: {self.post_url}")
                elif event_type == "message":
                    try:
                        message = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    self._handle_incoming_message(message)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error reading SSE stream for '{self.name}': {e}")

    def _handle_incoming_message(self, message: dict):
        if "id" in message and message["id"] in self._pending_requests:
            future = self._pending_requests.pop(message["id"])
            if not future.done():
                if "error" in message:
                    future.set_exception(Exception(message["error"]))
                else:
                    future.set_result(message.get("result"))

    async def _consume_sse_response(self, resp: aiohttp.ClientResponse, expected_id: int,
                                     timeout: float = 30.0) -> Any:
        async def _read():
            async for event_type, data_str in _iter_sse_events(resp.content):
                if event_type != "message" or not data_str:
                    continue
                try:
                    message = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if message.get("id") == expected_id:
                    if "error" in message:
                        raise Exception(message["error"])
                    return message.get("result")
                self._handle_incoming_message(message)
            return None

        return await asyncio.wait_for(_read(), timeout=timeout)

    # ------------------------------------------------------------------
    # Request / notification sending
    # ------------------------------------------------------------------

    async def _send_request(self, method: str, params: dict = None, timeout: float = 30.0) -> Any:
        if not self.post_url or not self.session:
            raise RuntimeError(f"MCP server '{self.name}' is not fully initialized.")

        req_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        try:
            if self.transport == "legacy_sse":
                return await self._send_request_legacy(request, timeout)
            return await self._send_request_streamable(request, timeout)
        except Exception as e:
            logger.error(f"Request '{method}' to '{self.name}' failed: {e}")
            raise

    async def _send_request_streamable(self, request: dict, timeout: float) -> Any:
        headers = {"Accept": "application/json, text/event-stream"}
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version

        async with self.session.post(
            self.post_url, json=request, headers=headers,
            timeout=aiohttp.ClientTimeout(total=timeout)
        ) as resp:
            if resp.status == 404 and self.session_id:
                raise RuntimeError(
                    f"MCP session for '{self.name}' expired or was reset by the "
                    f"server (HTTP 404) - a reconnect is required."
                )
            if resp.status >= 400:
                raise RuntimeError(f"HTTP POST failed with status: {resp.status}")

            session_id = resp.headers.get("Mcp-Session-Id")
            if session_id:
                self.session_id = session_id

            content_type = resp.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return await self._consume_sse_response(resp, request["id"], timeout=timeout)

            body = await resp.json(content_type=None)
            if "error" in body:
                raise Exception(body["error"])
            return body.get("result")

    async def _send_request_legacy(self, request: dict, timeout: float) -> Any:
        req_id = request["id"]
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = future

        try:
            async with self.session.post(
                self.post_url, json=request, timeout=aiohttp.ClientTimeout(total=10.0)
            ) as resp:
                if resp.status not in (200, 202, 204):
                    raise RuntimeError(f"HTTP POST failed with status: {resp.status}")

                if resp.status == 200:
                    try:
                        body = await resp.json(content_type=None)
                    except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
                        body = None
                    if isinstance(body, dict) and body.get("id") == req_id:
                        self._pending_requests.pop(req_id, None)
                        if "error" in body:
                            raise Exception(body["error"])
                        return body.get("result")

            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Timed out waiting for a response to '{request['method']}' from '{self.name}'."
            )
        finally:
            self._pending_requests.pop(req_id, None)

    async def _send_notification(self, method: str, params: dict = None):
        if not self.post_url or not self.session:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        headers = {}
        if self.transport == "streamable_http":
            headers["Accept"] = "application/json, text/event-stream"
            if self.session_id:
                headers["Mcp-Session-Id"] = self.session_id
            if self.protocol_version:
                headers["MCP-Protocol-Version"] = self.protocol_version

        try:
            async with self.session.post(
                self.post_url, json=notification, headers=headers or None,
                timeout=aiohttp.ClientTimeout(total=10.0)
            ) as resp:
                pass
        except Exception as e:
            logger.error(f"Failed to send notification to MCP server '{self.name}': {e}")

    # ------------------------------------------------------------------
    # Public tool API
    # ------------------------------------------------------------------

    async def get_tools(self) -> List[dict]:
        try:
            result = await self._send_request("tools/list")
            if not result:
                return []

            tools = result.get("tools", [])
            openai_tools = []

            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{self.name}__{t['name']}",
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", {"type": "object", "properties": {}})
                    }
                })
            return openai_tools
        except Exception as e:
            logger.error(f"Failed to fetch tools from '{self.name}': {e}")
            return []

    async def call_tool(self, name: str, args: dict) -> dict:
        try:
            original_name = name
            if name.startswith(f"{self.name}__"):
                original_name = name[len(f"{self.name}__"):]

            result = await self._send_request("tools/call", {
                "name": original_name,
                "arguments": args
            }, timeout=60.0)

            if not result:
                return {"success": False, "result": "Empty response from server.", "speak": None}

            content = result.get("content", [])
            text_result = ""
            for item in content:
                if item.get("type") == "text":
                    text_result += item.get("text", "")

            return {"success": not result.get("isError", False), "result": text_result, "speak": None}
        except Exception as e:
            logger.error(f"Failed to call tool '{name}' on '{self.name}': {e}")
            return {"success": False, "result": str(e), "speak": None}


class MCPManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance.clients = {}
            cls._instance._config = configuration.ConfigurationSettings()
        return cls._instance

    async def initialize_all(self):
        enable_mcp = self._config.get_main_setting("enable_mcp")
        if not enable_mcp:
            logger.info("MCP Proxy Integration is disabled. Skipping initialization.")
            return

        mcp_url = self._config.get_main_setting("mcp_server")
        if mcp_url and (mcp_url.startswith("http://") or mcp_url.startswith("https://")):
            if "proxy_server" not in self.clients:
                client = MCPClient("proxy_server", mcp_url)
                success = await client.start()
                if success:
                    self.clients["proxy_server"] = client
                else:
                    logger.warning(f"Failed to initialize proxy MCP server on {mcp_url}")
        else:
            logger.warning("No valid HTTP/SSE MCP URL configured in settings.")

    async def get_all_tools(self) -> List[dict]:
        all_tools = []
        for client in self.clients.values():
            tools = await client.get_tools()
            all_tools.extend(tools)
        return all_tools

    async def call_tool(self, name: str, args: dict) -> Optional[dict]:
        for client_name, client in self.clients.items():
            prefix = f"{client_name}__"
            if name.startswith(prefix):
                return await client.call_tool(name, args)
        return None

    async def shutdown(self):
        for client in self.clients.values():
            await client.stop()
        self.clients.clear()
