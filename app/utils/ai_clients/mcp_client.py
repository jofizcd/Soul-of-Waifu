import logging
import asyncio
import json
import aiohttp
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from app.configuration import configuration

logger = logging.getLogger("MCP Client")

class MCPClient:
    """
    MCP Client that connects to a remote HTTP/SSE (Server-Sent Events) server.
    """
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url.strip()
        self.session: Optional[aiohttp.ClientSession] = None
        self.post_url: Optional[str] = None
        self._sse_response: Optional[aiohttp.ClientResponse] = None
        
        self._message_id = 1
        self._receive_task: Optional[asyncio.Task] = None
        self._pending_requests: Dict[int, asyncio.Future] = {}

    async def start(self) -> bool:
        self.session = aiohttp.ClientSession()
        try:
            logger.info(f"Connecting to MCP SSE server at: {self.url}")
            self._sse_response = await self.session.get(self.url)
            if self._sse_response.status != 200:
                logger.error(f"Failed to connect to SSE stream: HTTP {self._sse_response.status}")
                await self.session.close()
                self.session = None
                return False
                
            self._receive_task = asyncio.create_task(self._read_sse_stream())
            
            for _ in range(50):
                if self.post_url:
                    break
                await asyncio.sleep(0.1)
                
            if not self.post_url:
                logger.error(f"Timed out waiting for SSE endpoint initialization from {self.url}")
                await self.stop()
                return False
                
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "Soul-of-Waifu", "version": "2.4.0"}
            })
            
            await self._send_notification("notifications/initialized", {})
            logger.info(f"MCP SSE Server '{self.name}' initialized successfully on {self.post_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SSE MCP client '{self.name}': {e}")
            await self.stop()
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
            
        self.post_url = None
        self._pending_requests.clear()

    async def _read_sse_stream(self):
        if not self._sse_response:
            return
            
        current_event = "message"
        try:
            async for line in self._sse_response.content:
                line_str = line.decode('utf-8').strip()
                if not line_str:
                    continue
                    
                if line_str.startswith("event:"):
                    current_event = line_str[6:].strip()
                elif line_str.startswith("data:"):
                    data_str = line_str[5:].strip()
                    
                    if current_event == "endpoint":
                        self.post_url = urljoin(self.url, data_str)
                        logger.info(f"Resolved remote MCP POST endpoint: {self.post_url}")
                    elif current_event == "message":
                        try:
                            message = json.loads(data_str)
                            self._handle_incoming_message(message)
                        except json.JSONDecodeError:
                            pass
                    current_event = "message"
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

    async def _send_request(self, method: str, params: dict = None) -> Any:
        if not self.post_url or not self.session:
            raise RuntimeError(f"SSE Server '{self.name}' is not fully initialized.")
            
        req_id = self._message_id
        self._message_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            async with self.session.post(self.post_url, json=request, timeout=10.0) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP POST failed with status: {resp.status}")
                
                response_data = await resp.json()
                if "error" in response_data:
                    raise Exception(response_data["error"])
                return response_data.get("result")
        except Exception as e:
            logger.error(f"HTTP POST Request to '{self.name}' failed: {e}")
            raise

    async def _send_notification(self, method: str, params: dict = None):
        if not self.post_url or not self.session:
            return
            
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        try:
            async with self.session.post(self.post_url, json=notification) as resp:
                pass
        except Exception as e:
            logger.error(f"Failed to send notification to SSE server '{self.name}': {e}")

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
            })
            
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