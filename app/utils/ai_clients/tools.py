import ast
import json
import logging
import asyncio
import operator
import datetime

logger = logging.getLogger("Chat Tools")

try:
    from app.utils.soul_companion.soul_companion import (
        BaseTool,
        WebSearchTool,
        OpenURLTool,
        ClipboardReaderTool,
        GetSystemInfoTool,
    )
    _COMPANION_TOOLS_AVAILABLE = True
except Exception as e:
    logger.warning(
        f"Could not import Soul Companion's tools ({e}); falling back to a "
        f"minimal, locally-defined web search tool instead."
    )
    _COMPANION_TOOLS_AVAILABLE = False

    class BaseTool:
        name = "base_tool"
        description = "Base tool. Override in subclasses."

        def get_schema(self) -> dict:
            raise NotImplementedError

        async def execute(self, args: dict, context: dict) -> dict:
            raise NotImplementedError

    class WebSearchTool(BaseTool):
        name = "web_search"
        description = (
            "Search the web for current information: news, facts, prices, "
            "or anything that might have changed recently or that you're "
            "not sure about."
        )

        def get_schema(self) -> dict:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query."}
                        },
                        "required": ["query"],
                    },
                },
            }

        async def execute(self, args: dict, context: dict) -> dict:
            query = (args.get("query") or "").strip()
            if not query:
                return {"success": False, "result": "Empty search query.", "speak": None}
            try:
                from ddgs import DDGS
            except ImportError:
                return {
                    "success": False,
                    "result": (
                        "Web search is unavailable: Soul Companion's tools module "
                        "could not be loaded and the fallback 'ddgs' package is "
                        "not installed (pip install ddgs)."
                    ),
                    "speak": None,
                }
            try:
                results = await asyncio.to_thread(DDGS().text, query, max_results=5)
            except Exception as ex:
                logger.error(f"Fallback WebSearchTool error: {ex}")
                return {"success": False, "result": f"Search failed: {ex}", "speak": None}
            if not results:
                return {"success": True, "result": f"No results found for '{query}'.", "speak": None}
            lines = [
                f"- {r.get('title', '')}: {r.get('body', '')} ({r.get('href', '')})"
                for r in results
            ]
            return {"success": True, "result": "\n".join(lines), "speak": None}

    OpenURLTool = None
    ClipboardReaderTool = None
    GetSystemInfoTool = None


class GetCurrentDateTimeTool(BaseTool):
    name = "get_current_datetime"
    description = (
        "Get the current real-world date and time. Use this whenever the "
        "user asks what day/date/time it is, or you need to reason about "
        "how much time has passed since something."
    )

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}},
            },
        }

    async def execute(self, args: dict, context: dict) -> dict:
        now = datetime.datetime.now()
        return {
            "success": True,
            "result": now.strftime("%A, %Y-%m-%d %H:%M:%S"),
            "speak": None,
        }

_ALLOWED_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("Only numeric constants are allowed.")
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN_OPS:
        return _ALLOWED_BIN_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Expression contains disallowed operations.")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = (
        "Evaluate a numeric arithmetic expression (+, -, *, /, //, %, **, "
        "parentheses). Use this for any non-trivial math instead of guessing "
        "the answer."
    )

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "A numeric expression, e.g. '(12 + 8) * 3 / 2'",
                        }
                    },
                    "required": ["expression"],
                },
            },
        }

    async def execute(self, args: dict, context: dict) -> dict:
        expression = args.get("expression", "")
        try:
            tree = ast.parse(expression, mode="eval")
            value = _safe_eval(tree)
            return {"success": True, "result": str(value), "speak": None}
        except Exception as e:
            return {
                "success": False,
                "result": f"Could not evaluate '{expression}': {e}",
                "speak": None,
            }


class ToolRegistry:
    def __init__(self, tools=None):
        self.tools = {t.name: t for t in (tools if tools is not None else self.default_tools())}

    @staticmethod
    def default_tools():
        tools = [CalculatorTool(), WebSearchTool()]
        if _COMPANION_TOOLS_AVAILABLE:
            if GetSystemInfoTool:
                tools.append(GetSystemInfoTool())
            if OpenURLTool:
                tools.append(OpenURLTool())
            if ClipboardReaderTool:
                tools.append(ClipboardReaderTool())
        else:
            tools.append(GetCurrentDateTimeTool())
        return tools

    def get_schemas(self) -> list:
        return [tool.get_schema() for tool in self.tools.values()]

    def has_tools(self) -> bool:
        return bool(self.tools)

    def tool_names(self) -> list:
        return list(self.tools.keys())

    async def execute(self, tool_name: str, args: dict, context: dict) -> dict:
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "result": f"Unknown tool: {tool_name}", "speak": None}
        try:
            return await tool.execute(args, context)
        except Exception as e:
            logger.error(f"Tool '{tool_name}' raised an exception: {e}")
            return {"success": False, "result": f"Tool '{tool_name}' failed: {e}", "speak": None}


def normalize_tool_call(tc) -> dict:
    if isinstance(tc, dict):
        call_id = tc.get("id") or ""
        func = tc.get("function", {}) or {}
        name = func.get("name")
        raw_args = func.get("arguments", "{}")
    else:
        call_id = getattr(tc, "id", "") or ""
        func = getattr(tc, "function", None)
        name = getattr(func, "name", None) if func else None
        raw_args = getattr(func, "arguments", "{}") if func else "{}"

    try:
        args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
    except Exception:
        args = {}

    return {"id": call_id, "name": name, "arguments": args}
