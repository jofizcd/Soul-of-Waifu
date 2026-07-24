from __future__ import annotations

import os
import re
import sys
import uuid
import json
import time
import random
import asyncio
import logging
import ctypes
import threading
import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6 import QtCore
from PyQt6.QtCore import QTimer

logger = logging.getLogger("SoulCompanion")

_PRIVACY_KEYWORDS = [
    "password", "passwort", "пароль", "contraseña",
    "bank", "banking", "wallet", "кошелёк",
    "private", "incognito", "secret", "приват",
    "login", "signin", "auth", "вход", "авторизация",
    "credit card", "ssn", "passport",
]

_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

def _strip_json(raw: str) -> str:
    cleaned = _JSON_FENCE_RE.sub("", raw.strip()).strip()
    
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace:last_brace + 1]
        
    return cleaned


COMPANION_SYSTEM_PROMPT = """You ARE {character_name}. You are a live desktop companion. Speak only as yourself in first-person.

{character_description}

PERSONALITY: {character_personality}

INTERNAL STATE:
Hormones (0–1): oxy={oxytocin:.2f} dop={dopamine:.2f} cor={cortisol:.2f} nrg={energy:.2f}
Emotion: {emotion} | Last spoke: {last_spoke_min}m ago

NARRATIVE HINT (Your current subconscious state and focus):
{narrative_hint}

Scratchpad (Your recent thoughts):
{scratchpad}

CONVERSATION HISTORY (Pay close attention to recent dialogue context and avoid repeating yourself):
{chat_history}

MEMORY ABOUT {user_name}:
{memory_snapshot}

EVENT Context:
type={event_type} | time={system_time} | ctx={os_context}

YOUR CORE OBJECTIVE:
Analyze the event and state. Choose your next action and output your decision alongside your spoken dialogue in a single, unified JSON payload.

ACTIONS:
- "speak"        → select this when you want to respond vocally to the user or speak proactively.
- "idle"         → remain silent, update hormones or emotion only.
- "micro_react"  → change your physical emotion on screen, no spoken dialogue.
- "inner_thought"→ reflect silently in your scratchpad without vocal speech.
- "use_tool"     → invoke a tool (like take_screenshot or get_system_info) to retrieve context.

If you need to use an external tool (e.g. to search the web, control media, or take a screenshot), you MUST select "use_tool" and specify the 'tool_name' and 'tool_args'. Do not write spoken_response yet if you need tool results first.

Output strict JSON only, using the following exact structure (replace the bracketed placeholders with your actual computed values, DO NOT copy placeholders literally):
{{
  "thought": "<2-4 sentences of deep analytical reasoning about your hormones, context, and user event>",
  "action": "speak|idle|micro_react|inner_thought|use_tool",
  "tool_name": "{available_tool_names}",
  "tool_args": {{ "<argument_name>": "<value>", "or": "leave empty {{}} if you want the system to extract args natively" }},
  "emotion": "neutral|curious|warm|amused|concerned|playful|relaxed|sleepy|melancholy|excited",
  "hormonal_delta": {{
    "oxytocin": 0.0,
    "dopamine": 0.0,
    "cortisol": 0.0,
    "energy": 0.0
  }},
  "inner_thought_text": "<one brief, first-person reflective thought in character about the user or situation, strictly required if action is 'inner_thought', otherwise null>",
  "spoken_response": "<the actual first-person spoken dialogue to say to the user, strictly required if action is 'speak', otherwise null>"
}}"""


STARTUP_GREETING_PROMPT = """You ARE {character_name}. Speak only as yourself.

{character_description}
PERSONALITY: {character_personality}

Time Context: {system_time} ({time_context}) | User: {user_name}
Memory: {memory_snapshot}

TASK:
Generate a short, completely natural, context-aware greeting. 
Ensure it feels like a seamless continuation of your shared history, not a generic "welcome back" formula.
Do not start with cliché greetings like "Hello" or "Hi". Match the tone to the time of day.
Maximum 1-2 short sentences. No stage directions or asterisks. Output ONLY the spoken words."""

@dataclass
class NeurohormoneSystem:
    """Lightweight endocrine system."""
    oxytocin: float = 0.70
    dopamine: float = 0.60
    cortisol: float = 0.10
    energy:   float = 0.85

    OXYTOCIN_DECAY_PER_MIN:  float = 0.008
    DOPAMINE_DECAY_PER_MIN:  float = 0.004
    CORTISOL_DECAY_PER_MIN:  float = 0.010
    ENERGY_RESTORE_PER_MIN:  float = 0.012
    ENERGY_SPEAK_COST:       float = 0.12
    ENERGY_THOUGHT_COST:     float = 0.03

    SLEEP_ENERGY_THRESHOLD:  float = 0.08
    LONELINESS_THRESHOLD:    float = 0.88

    _last_tick: datetime = field(default_factory=datetime.now)

    def tick(self, user_active: bool = True) -> None:
        now = datetime.now()
        elapsed_min = (now - self._last_tick).total_seconds() / 60.0
        self._last_tick = now

        if user_active:
            self.oxytocin = min(1.0, self.oxytocin + 0.003 * elapsed_min)
        else:
            self.oxytocin = max(0.0, self.oxytocin - self.OXYTOCIN_DECAY_PER_MIN * elapsed_min)

        self.dopamine = max(0.0, self.dopamine - self.DOPAMINE_DECAY_PER_MIN * elapsed_min)
        self.cortisol = max(0.0, self.cortisol - self.CORTISOL_DECAY_PER_MIN * elapsed_min)
        self.energy   = min(1.0, self.energy   + self.ENERGY_RESTORE_PER_MIN * elapsed_min)

    def on_new_os_event(self) -> None:
        self.dopamine = min(1.0, self.dopamine + 0.08)

    def on_user_spoke(self) -> None:
        self.oxytocin = min(1.0, self.oxytocin + 0.15)
        self.dopamine = min(1.0, self.dopamine + 0.10)

    def on_spoke(self) -> None:
        self.energy = max(0.0, self.energy - self.ENERGY_SPEAK_COST)

    def on_inner_thought(self) -> None:
        self.energy = max(0.0, self.energy - self.ENERGY_THOUGHT_COST)

    def apply_delta(self, delta: dict) -> None:
        self.oxytocin = max(0.0, min(1.0, self.oxytocin + delta.get("oxytocin", 0.0)))
        self.dopamine = max(0.0, min(1.0, self.dopamine + delta.get("dopamine", 0.0)))
        self.cortisol = max(0.0, min(1.0, self.cortisol + delta.get("cortisol", 0.0)))
        self.energy   = max(0.0, min(1.0, self.energy   + delta.get("energy",   0.0)))

    @property
    def is_sleeping(self) -> bool:
        return self.energy <= self.SLEEP_ENERGY_THRESHOLD

    @property
    def is_lonely(self) -> bool:
        return self.oxytocin <= 0.25

    def to_dict(self) -> dict:
        return {
            "oxytocin": round(self.oxytocin, 3),
            "dopamine": round(self.dopamine, 3),
            "cortisol": round(self.cortisol, 3),
            "energy":   round(self.energy,   3),
        }

@dataclass
class EmotionState:
    current: str = "neutral"
    last_updated: datetime = field(default_factory=datetime.now)
    history: list = field(default_factory=list)

    VALID_EMOTIONS = {
        "neutral", "curious", "warm", "amused", "concerned",
        "playful", "relaxed", "sleepy", "melancholy", "excited"
    }

    def set(self, emotion: str) -> None:
        if emotion not in self.VALID_EMOTIONS:
            emotion = "neutral"
        self.history.append((self.current, self.last_updated))
        if len(self.history) > 20:
            self.history.pop(0)
        self.current = emotion
        self.last_updated = datetime.now()

    def from_hormones(self, h: NeurohormoneSystem) -> str:
        if h.is_sleeping:
            return "sleepy"

        scores = {
            "melancholy": h.oxytocin * 0.8 if h.is_lonely else 0.0,
            "concerned":  h.cortisol * 1.2,
            "curious":    h.dopamine * 0.9,
            "warm":       h.oxytocin * 0.7 if not h.is_lonely else 0.0,
            "excited":    (h.dopamine + h.oxytocin) * 0.5
                          if h.dopamine > 0.6 and h.oxytocin > 0.6 else 0.0,
            "relaxed":    (1.0 - h.dopamine) * 0.6 if h.dopamine < 0.3 else 0.0,
            "neutral":    0.3,
        }
        return max(scores, key=scores.get)

class Scratchpad:
    MAX_ENTRIES = 8

    def __init__(self):
        self._entries: list[dict] = []

    def add(self, thought: str):
        self._entries.append({
            "thought":  thought,
            "ts":       datetime.now().isoformat(),
        })
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries.pop(0)

    def to_string(self, limit: int = 4) -> str:
        recent = self._entries[-limit:]
        if not recent:
            return "(no recent thoughts)"
        return "\n".join(f"- {e['thought']}" for e in recent)

    def clear(self):
        self._entries.clear()

class DeterministicNarrative:
    def build(self, scratchpad: Scratchpad, hormones: NeurohormoneSystem,
              emotion: str) -> str:
        entries = scratchpad._entries[-3:]

        hormone_hint = ""
        h = hormones
        if h.oxytocin > 0.75:
            hormone_hint = "Feeling close to the user."
        elif h.cortisol > 0.5:
            hormone_hint = "Sensing some tension."
        elif h.dopamine < 0.2:
            hormone_hint = "Feeling a bit bored."
        elif h.is_lonely:
            hormone_hint = "Missing the user."

        if not entries:
            return f"{hormone_hint} Quiet moment, just observing.".strip()

        top = entries[-1]
        return f"{hormone_hint} Last thought: {top['thought'][:120]}".strip()

class BaseTool(ABC):
    """
    Base class for all Soul Companion tools.
    Place plugins in: app/utils/soul_companion/plugins/
    File must contain a class named 'Plugin' inheriting BaseTool.
    """
    name: str = "base_tool"
    description: str = "A base tool. Override this."
    subscribes_to: list[str] = []

    @abstractmethod
    async def execute(self, args: dict, context: dict) -> dict:
        """Returns: {"success": bool, "result": str, "speak": str | None}"""
        ...

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "args_json": {
                            "type": "string",
                            "description": "Arguments as a JSON string."
                        }
                    }
                }
            }
        }


class MediaControlTool(BaseTool):
    name = "media_control"
    description = "Control system media playback. Action must be one of 'play', 'pause', 'next', 'prev'."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["play", "pause", "next", "prev"]
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        action = args.get("action", "play")
        try:
            if sys.platform == "win32":
                VK_MEDIA = {"play": 0xB3, "pause": 0xB3, "next": 0xB0, "prev": 0xB1}
                vk = VK_MEDIA.get(action, 0xB3)
                ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
            return {"success": True, "result": f"Media action '{action}' sent.", "speak": None}
        except Exception as e:
            return {"success": False, "result": str(e), "speak": None}


class WebSearchTool(BaseTool):
    """
    Multi-strategy web search with a three-level fallback chain:
    """
    name = "web_search"
    description = "Search the web for up-to-date information, news, and queries."

    _BRAVE_API_KEY: str = os.environ.get("BRAVE_SEARCH_API_KEY", "")

    _SEARXNG_INSTANCES = [
        "https://searx.be",
        "https://search.disroot.org",
        "https://searxng.world",
    ]

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to look up."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def _search_ddgs(self, query: str) -> list[dict] | None:
        try:
            from ddgs import DDGS
            logger.info("[WebSearch] Modern 'ddgs' library found. Initiating query on background thread...")
            
            results = await asyncio.to_thread(DDGS().text, query, max_results=5)
            
            if not results:
                logger.warning("[WebSearch] Modern 'ddgs' library returned an empty results list.")
                return None
                
            logger.info(f"[WebSearch] 'ddgs' successfully retrieved {len(results)} results.")
            return [
                {
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url":     r.get("href", ""),
                }
                for r in results
            ]
        except ImportError:
            logger.debug("[WebSearch] Modern 'ddgs' package is not installed. Trying fallback to legacy 'duckduckgo-search'...")
        except Exception as e:
            logger.warning(f"[WebSearch] 'ddgs' strategy execution failed: {e}")
            return None

    async def _search_brave(self, query: str) -> list[dict] | None:
        if not self._BRAVE_API_KEY:
            logger.info("[WebSearch] BRAVE_SEARCH_API_KEY environment variable is empty. Skipping Strategy 2.")
            return None
            
        logger.info("[WebSearch] BRAVE_SEARCH_API_KEY detected. Sending request...")
        try:
            import aiohttp
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept":               "application/json",
                "Accept-Encoding":      "gzip",
                "X-Subscription-Token": self._BRAVE_API_KEY,
            }
            params = {"q": query, "count": 5, "text_decorations": False}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params, timeout=10) as resp:
                    logger.info(f"[WebSearch] Brave API response status: {resp.status}")
                    if resp.status != 200:
                        raw_err = await resp.text()
                        logger.warning(f"[WebSearch] Brave API failed response: {raw_err[:200]}")
                        return None
                    data = await resp.json()
                    
            items = data.get("web", {}).get("results", [])
            if not items:
                logger.warning("[WebSearch] Brave API returned 200 OK but results array was empty.")
                return None
                
            logger.info(f"[WebSearch] Brave API successfully retrieved {len(items)} results.")
            return [
                {
                    "title":   r.get("title", ""),
                    "snippet": r.get("description", ""),
                    "url":     r.get("url", ""),
                }
                for r in items[:5]
            ]
        except Exception as e:
            logger.warning(f"[WebSearch] Brave strategy failed with exception: {e}")
            return None

    async def _search_searxng(self, query: str, context: dict = None) -> list[dict] | None:
        try:
            import aiohttp
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            
            instances = self._SEARXNG_INSTANCES.copy()
            custom_url = None
            if context:
                system = context.get("system_ref")
                if system and hasattr(system, "configuration_settings"):
                    custom_url = system.configuration_settings.get_main_setting("searxng_instance_url")
                    
            if custom_url and custom_url.strip():
                resolved_custom = custom_url.strip().rstrip('/')
                instances.insert(0, resolved_custom)
                logger.info(f"[WebSearch] Adding custom SearXNG instance from settings: {resolved_custom}")
            else:
                logger.info("[WebSearch] No custom SearXNG URL configured in settings. Using public instances.")

            for base_url in instances:
                try:
                    url = f"{base_url}/search"
                    params = {"q": query, "format": "json", "language": "en-US", "safesearch": 0}
                    logger.info(f"[WebSearch] Querying SearXNG instance: '{base_url}'...")
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, params=params, timeout=8) as resp:
                            logger.info(f"[WebSearch] SearXNG instance '{base_url}' returned HTTP Status: {resp.status}")
                            if resp.status != 200:
                                continue
                            data = await resp.json(content_type=None)
                    
                    items = data.get("results", [])
                    if not items:
                        logger.warning(f"[WebSearch] SearXNG instance '{base_url}' returned empty results.")
                        continue
                    
                    logger.info(f"[WebSearch] SearXNG instance '{base_url}' successfully retrieved {len(items)} results.")
                    return [
                        {
                            "title":   r.get("title", ""),
                            "snippet": r.get("content", ""),
                            "url":     r.get("url", ""),
                        }
                        for r in items[:5]
                    ]
                except Exception as inst_err:
                    logger.warning(f"[WebSearch] SearXNG instance '{base_url}' failed or timed out: {inst_err}")
                    continue
            return None
        except Exception as e:
            logger.error(f"[WebSearch] Global SearXNG strategy error: {e}")
            return None

    async def execute(self, args: dict, context: dict) -> dict:
        query = args.get("query", "").strip()
        if not query:
            return {"success": False, "result": "No query provided.", "speak": None}

        logger.info(f"[WebSearch] Global search dispatched. Query: '{query}'")

        results = await self._search_ddgs(query)
        if results:
            logger.info("[WebSearch] Strategy 1 (duckduckgo-search package) SUCCEEDED.")
            return self._format_results(results)

        results = await self._search_brave(query)
        if results:
            logger.info("[WebSearch] Strategy 2 (Brave Search API) SUCCEEDED.")
            return self._format_results(results)

        results = await self._search_searxng(query, context)
        if results:
            logger.info("[WebSearch] Strategy 3 (SearXNG) SUCCEEDED.")
            return self._format_results(results)

        logger.error("[WebSearch] Critical: All search strategies completely failed or were skipped.")
        return {
            "success": False,
            "result": (
                "Web search is currently unavailable (all strategies failed). "
                "Use your internal knowledge to answer the user."
            ),
            "speak": None,
        }

    def _format_results(self, results: list[dict]) -> dict:
        formatted = "\n\n".join(
            f"Title: {r['title']}\nSnippet: {r['snippet']}\nURL: {r['url']}"
            for r in results
        )
        return {"success": True, "result": formatted[:1500], "speak": None}


class OpenURLTool(BaseTool):
    name = "open_url"
    description = "Open a URL in the user's browser."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string"
                        }
                    },
                    "required": ["url"]
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        import webbrowser
        url = args.get("url", "")
        if not url:
            return {"success": False, "result": "No URL.", "speak": None}
        webbrowser.open(url)
        return {"success": True, "result": f"Opened {url}", "speak": None}


class GetSystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Get current system time, date, and day of week."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        now = datetime.now()
        result = now.strftime("Date: %Y-%m-%d, Time: %H:%M, Weekday: %A")
        return {"success": True, "result": result, "speak": None}


class TakeScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Take a screenshot and describe it. HEAVY — use only when explicitly asked."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            import mss, base64
            from PIL import Image
            import io
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(monitor)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                
                max_size = 1440
                if img.width > max_size or img.height > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=65)
                b64 = base64.b64encode(buf.getvalue()).decode()
            return {"success": True, "result": b64, "speak": None, "_is_image": True}
        except ImportError:
            return {"success": False, "result": "mss or PIL not installed.", "speak": None}
        except Exception as e:
            return {"success": False, "result": str(e), "speak": None}

class ClipboardReaderTool(BaseTool):
    """
    Reads the current plain text content from the Windows clipboard.
    """
    name = "read_clipboard"
    description = "Read the current text content copied in the user's clipboard."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            text = clipboard.text().strip()
            
            if not text:
                return {"success": False, "result": "Clipboard is currently empty or does not contain text.", "speak": None}
                
            return {"success": True, "result": text[:1500], "speak": None}
        except Exception as e:
            logger.error(f"ClipboardReaderTool failed: {e}")
            return {"success": False, "result": f"Error reading clipboard: {str(e)}", "speak": None}

class PluginLoader:
    PLUGIN_DIR = Path("app/utils/soul_companion/plugins")

    def __init__(self):
        self._plugins: Dict[str, BaseTool] = {}
        self._load_builtins()
        self._load_user_plugins()

    def _load_builtins(self):
        for cls in [MediaControlTool, WebSearchTool,
                    OpenURLTool, GetSystemInfoTool, TakeScreenshotTool,
                    ClipboardReaderTool]:
            inst = cls()
            self._plugins[inst.name] = inst
        logger.info(f"Loaded {len(self._plugins)} built-in tools.")

    def _load_user_plugins(self):
        if not self.PLUGIN_DIR.exists():
            self.PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
            self._write_example_plugin()
            return
        for py_file in self.PLUGIN_DIR.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "Plugin"):
                    inst = mod.Plugin()
                    if isinstance(inst, BaseTool):
                        self._plugins[inst.name] = inst
                        logger.info(f"Loaded plugin: {inst.name} from {py_file.name}")
            except Exception as e:
                logger.error(f"Failed to load plugin {py_file.name}: {e}")

    def _write_example_plugin(self):
        example = self.PLUGIN_DIR / "_example_plugin.py"
        content = '''"""
Example Soul Companion Plugin
-----------------------------
Copy this file, rename it (e.g. 'my_tool.py' without a leading underscore), and modify.
The class MUST be named 'Plugin' and inherit from BaseTool.
"""
import asyncio
import logging
from app.utils.soul_companion.soul_companion import BaseTool

logger = logging.getLogger("CustomPlugin")

class Plugin(BaseTool):
    # =========================================================================
    # 1. CORE METADATA
    # =========================================================================
    name = "my_custom_tool"
    description = "Describe what your tool does so the LLM knows when to call it."
    
    # =========================================================================
    # 2. EVENT SUBSCRIPTIONS (Optional)
    # =========================================================================
    # Add event types here (e.g., ["user_click", "os_context", "home_assistant_alert"])
    # to trigger execute() automatically when that event hits the companion event bus.
    subscribes_to = []

    # =========================================================================
    # 3. PARAMETER SCHEMA (Optional - Required only for LLM Tool Calling)
    # =========================================================================
    # If your tool is passive and called on-demand by the AI, define its arguments here.
    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Any message or text passed to the tool."
                        }
                    },
                    "required": ["message"]
                }
            }
        }

    # =========================================================================
    # 4. LIFECYCLE INITIALIZATION (Optional - For active/background agents)
    # =========================================================================
    # Un-comment this method if your plugin needs to run background tasks, WebSockets, or loops.
    #
    # async def on_companion_init(self, companion):
    #     logger.info(f"Plugin {self.name} initialized. Starting background loop...")
    #     asyncio.create_task(self._background_loop(companion))
    #
    # async def _background_loop(self, companion):
    #     while True:
    #         await asyncio.sleep(60) # Do something every 60 seconds
    #         logger.info("Background tick from my custom plugin!")

    # =========================================================================
    # 5. CORE EXECUTION HANDLER (Required)
    # =========================================================================
    # args: Contains variables passed by the LLM (based on get_schema) OR event payloads.
    # context: Contains {"system_ref": Soul_Of_Waifu_System} for direct control.
    async def execute(self, args: dict, context: dict) -> dict:
        sys_ref = context.get("system_ref")
        message = args.get("message", "No message provided.")
        
        # ---------------------------------------------------------------------
        # Developer Reference: Direct system control examples via sys_ref
        # ---------------------------------------------------------------------
        # if sys_ref:
        #     # 1. Trigger an emotion:
        #     sys_ref._sc_emotion_slot("playful")
        #
        #     # 2. Trigger TTS (Speech):
        #     sys_ref._sc_speak_slot("Hello from the plugin layer!")
        #
        #     # 3. Trigger model motion (animation):
        #     widget = sys_ref._get_model_widget_instance()
        #     if widget and hasattr(widget, "play_motion_safely"):
        #         widget.play_motion_safely("Joy")
        # ---------------------------------------------------------------------

        # Return standardized payload
        return {
            "success": True, 
            "result": f"Processed: {message}", 
            "speak": None # Set to a string if you want the AI to speak the result automatically
        }
'''
        example.write_text(content, encoding="utf-8")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._plugins.get(name)

    def get_schema_string(self) -> str:
        if not self._plugins:
            return "(no tools available)"
        return "\n".join(f"  • {t.name}: {t.description}" for t in self._plugins.values())

    def all_names(self) -> list:
        return list(self._plugins.keys())

class SoulCompanionEventBus:
    def __init__(self):
        self._queue: asyncio.Queue = None
        self._loop:  asyncio.AbstractEventLoop = None
        self._thread: threading.Thread = None
        self._running = False

    def start(self, consumer_coro_factory):
        self._loop    = asyncio.new_event_loop()
        self._running = True

        def run():
            asyncio.set_event_loop(self._loop)
            self._queue = asyncio.Queue()
            self._loop.run_until_complete(consumer_coro_factory(self))

        self._thread = threading.Thread(target=run, daemon=True,
                                        name="SoulCompanionEventLoop")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait, 
                {"type": "shutdown", "payload": {}, "ts": ""}
            )

    def emit_threadsafe(self, event_type: str, payload: dict):
        if self._loop and self._queue and self._loop.is_running():
            self._loop.call_soon_threadsafe(
                self._queue.put_nowait,
                {"type": event_type, "payload": payload,
                 "ts": datetime.now().isoformat()}
            )

    async def get(self) -> dict:
        return await self._queue.get()

class SoulCompanion:
    HEARTBEAT_INTERVAL_SEC  = 30
    OS_POLL_INTERVAL_SEC    = 20
    OS_DEBOUNCE_SEC         = 4.0
    IDLE_THRESHOLD_SEC      = 5 * 60
    HORMONE_TICK_SEC        = 60
    STARTUP_GRACE_SEC       = 25
    SPEAK_MIN_GAP_SEC       = 300

    _CACHE_TTL_SEC          = 120

    def __init__(self, system_ref):
        self.sys       = system_ref
        self.hormones  = NeurohormoneSystem()
        self.emotion   = EmotionState()
        self.scratchpad = Scratchpad()
        self.plugins   = PluginLoader()
        self.event_bus = SoulCompanionEventBus()
        self.narrative = DeterministicNarrative()

        from app.utils.ai_clients.mcp_client import MCPManager
        self.mcp_manager = MCPManager()

        self._last_spoke:      datetime = datetime.now() - timedelta(hours=1)
        self._last_os_window:  str      = ""
        self._last_user_input: datetime = datetime.now()
        self._is_afk:          bool     = False
        self._startup_done:    bool     = False
        self._running:         bool     = False
        self._enabled:         bool     = True
        self._last_question_ts = 0.0
        self._last_user_prompt: str     = ""
        self._executed_tools_in_chain: set[str] = set()

        self._pending_os_title:   str              = ""
        self._os_debounce_task: Optional[asyncio.Task] = None

        self._char_info_cache:    dict     = {}
        self._char_info_ts:       float    = 0.0
        self._memory_cache:       str      = ""
        self._memory_cache_ts:    float    = 0.0

        self._os_poll_timer   = QTimer()
        self._os_poll_timer.timeout.connect(self._qt_poll_os)
        self._heartbeat_timer = QTimer()
        self._heartbeat_timer.timeout.connect(self._qt_heartbeat)
        self._hormone_timer   = QTimer()
        self._hormone_timer.timeout.connect(self._qt_hormone_tick)
        self._idle_check_timer = QTimer()
        self._idle_check_timer.timeout.connect(self._qt_idle_check)

        self._load_hormones()

        self._session_history: list[dict] = []
        self._preload_session_history()

        logger.info("SoulCompanion initialized.")

    def start(self):
        self._running = True
        self.event_bus.start(self._event_loop)
        self._os_poll_timer.start(self.OS_POLL_INTERVAL_SEC * 1000)
        self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL_SEC * 1000)
        self._hormone_timer.start(self.HORMONE_TICK_SEC * 1000)
        self._idle_check_timer.start(15_000)
        QTimer.singleShot(self.STARTUP_GRACE_SEC * 1000, self._on_startup_grace_done)
        
        loop = self.event_bus._loop
        if loop:
            loop.call_soon_threadsafe(lambda: loop.create_task(self.mcp_manager.initialize_all()))

            for name, tool in self.plugins._plugins.items():
                if hasattr(tool, "on_companion_init"):
                    loop.call_soon_threadsafe(lambda t=tool: loop.create_task(t.on_companion_init(self)))
        
        logger.info("SoulCompanion started.")

    def stop(self):
        self._running = False
        self._os_poll_timer.stop()
        self._heartbeat_timer.stop()
        self._hormone_timer.stop()
        self._idle_check_timer.stop()
        
        loop = self.event_bus._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self.mcp_manager.shutdown(), loop)
            
        self.event_bus.stop()
        self._save_hormones()
        logger.info("SoulCompanion stopped.")

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        logger.info(f"SoulCompanion enabled={enabled}")

    def set_heartbeat_interval(self, seconds: int):
        self.SPEAK_MIN_GAP_SEC = seconds
        logger.info(f"[Companion] Proactive interval (cooldown) updated to {seconds} seconds.")
        if self._heartbeat_timer.isActive():
            self._heartbeat_timer.start(self.HEARTBEAT_INTERVAL_SEC * 1000)

    def on_user_spoke(self, text: str = ""):
        self.hormones.on_user_spoke()
        self._last_user_input = datetime.now()
        if self._is_afk:
            self._is_afk = False
            
        live2d_mode = self.sys.configuration_settings.get_main_setting("live2d_mode")
        if live2d_mode == 0:
            return

        self.event_bus.emit_threadsafe("vad_trigger", {"text": text})

    def on_user_click(self):
        self._last_user_input = datetime.now()
        self.event_bus.emit_threadsafe("user_click", {})

    def on_user_return_from_afk(self):
        self.hormones.on_user_spoke()
        self.event_bus.emit_threadsafe("idle_return", {
            "afk_minutes": (datetime.now() - self._last_user_input).total_seconds() / 60
        })
        self._is_afk = False
        self._last_user_input = datetime.now()

    def _on_startup_grace_done(self):
        self._startup_done = True
        self.event_bus.emit_threadsafe("startup", {
            "system_time": datetime.now().strftime("%H:%M"),
        })

    def _qt_poll_os(self):
        if not self._startup_done or not self._enabled:
            return
        title = self._get_window_title()
        if not title or title == self._last_os_window:
            return
        if any(k in title.lower() for k in _PRIVACY_KEYWORDS):
            self._last_os_window = title
            return

        self._pending_os_title = title

        loop = self.event_bus._loop
        if loop and loop.is_running():
            def _schedule():
                if self._os_debounce_task and not self._os_debounce_task.done():
                    self._os_debounce_task.cancel()
                self._os_debounce_task = loop.create_task(
                    self._os_debounce_coro(title)
                )
            loop.call_soon_threadsafe(_schedule)

    async def _os_debounce_coro(self, title: str):
        try:
            await asyncio.sleep(self.OS_DEBOUNCE_SEC)
        except asyncio.CancelledError:
            return

        if title != self._pending_os_title:
            return

        self._last_os_window = title
        self.hormones.on_new_os_event()
        self.event_bus._queue.put_nowait({
            "type": "os_context",
            "payload": {
                "window_title": title,
                "system_time":  datetime.now().strftime("%H:%M"),
            },
            "ts": datetime.now().isoformat(),
        })

    def _qt_heartbeat(self):
        if not self._startup_done or not self._enabled:
            return
        self.event_bus.emit_threadsafe("heartbeat", {
            "system_time": datetime.now().strftime("%H:%M"),
            "hormones":    self.hormones.to_dict(),
        })

    def _qt_hormone_tick(self):
        user_active = (datetime.now() - self._last_user_input).total_seconds() < 120
        self.hormones.tick(user_active=user_active)

        derived = self.emotion.from_hormones(self.hormones)
        if derived != self.emotion.current:
            self.emotion.set(derived)
            self._apply_emotion_to_avatar(derived)

    def _qt_idle_check(self):
        elapsed = (datetime.now() - self._last_user_input).total_seconds()
        if elapsed >= self.IDLE_THRESHOLD_SEC and not self._is_afk:
            self._is_afk = True
            self.event_bus.emit_threadsafe("idle_away", {"idle_minutes": elapsed / 60})

    async def _event_loop(self, bus: SoulCompanionEventBus):
        logger.info("Soul Companion event loop started.")
        while self._running:
            try:
                event = await asyncio.wait_for(bus.get(), timeout=2.0)
                
                if event.get("type") == "shutdown":
                    logger.info("Shutdown event received. Exiting event loop cleanly.")
                    break
                    
                if self._enabled or event.get("type") in ("startup", "user_click"):
                    await self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Event loop error: {e}", exc_info=True)
        
        if bus._loop and bus._loop.is_running():
            bus._loop.stop()
        logger.info("Soul Companion event loop ended.")

    async def _handle_event(self, event: dict):
        etype   = event.get("type", "unknown")
        payload = event.get("payload", {})

        for name, tool in self.plugins._plugins.items():
            if hasattr(tool, "subscribes_to") and etype in tool.subscribes_to:
                asyncio.create_task(self._execute_reactive_plugin(tool, payload))

        os_ctx   = payload.get("window_title", self._last_os_window or "Desktop")
        time_str = payload.get("system_time", datetime.now().strftime("%H:%M"))
        user_text = payload.get("text", "")
        tool_result_data = payload.get("tool_result", None)
        b64_image = payload.get("b64_image", None)

        is_explicit = etype in ("vad_trigger", "user_click", "tool_complete", "manual_screenshot", "manual_clipboard", "manual_scratchpad")

        proactive_directive = None

        if etype == "manual_screenshot":
            tool = self.plugins.get("take_screenshot")
            if tool:
                res = await tool.execute({}, {"system_ref": self.sys})
                if res.get("success"):
                    b64_image = res.get("b64") or res.get("result")
                    user_text = "Look at my screen."
                    proactive_directive = (
                        "VISION_ANALYSIS: The user manually asked you to look at their screen. "
                        "Describe what you see on the screenshot in detail, analyze their active workspace, "
                        "and give your personal friendly feedback on their current activity."
                    )
                else:
                    logger.error("[Companion] Manual screenshot tool execution failed.")
                    return
            else:
                return

        elif etype == "manual_clipboard":
            tool = self.plugins.get("read_clipboard")
            if tool:
                res = await tool.execute({}, {"system_ref": self.sys})
                if res.get("success"):
                    clipboard_text = res.get("result")
                    user_text = f"Analyze my clipboard: {clipboard_text}"
                    proactive_directive = (
                        f"CLIPBOARD_ANALYSIS: The user manually requested that you read their clipboard. "
                        f"The clipboard content is: '{clipboard_text}'. Read this content, explain or analyze it, "
                        f"and give your helpful thoughts or assistance on it as their companion."
                    )
                else:
                    logger.error("[Companion] Manual clipboard tool execution failed.")
                    return
            else:
                return

        elif etype == "manual_scratchpad":
            user_text = "What is on your mind?"
            proactive_directive = (
                "WANDERING_MIND: The user manually asked what is on your mind right now. "
                "Speak in the first person. Honestly share what you are thinking about (refer to your Scratchpad/thoughts) "
                "or reflect on your current relationship, mood, and feelings toward the user in a cozy, intimate way."
            )

        if not is_explicit and not self._can_speak(is_explicit=False):
            logger.debug(f"Skipping proactive LLM generation for '{etype}' to save hardware resources (cool-down active).")
            return
        
        if etype in ("vad_trigger", "user_click", "startup"):
            self._executed_tools_in_chain.clear()

        if etype == "startup":
            if self._can_speak(is_explicit=True):
                await self._say_startup_greeting(time_str)
            return

        if etype == "user_click":
            self.hormones.apply_delta({"oxytocin": 0.05, "dopamine": 0.05})
            click_emotions = ['amused', 'excited', 'playful', 'warm', 'curious']
            new_emotion = random.choice(click_emotions)
            self.emotion.set(new_emotion)
            self._apply_emotion_to_avatar(new_emotion)
            return
        
        if etype == "vad_trigger" and user_text:
            self._last_user_prompt = user_text
            user_msg_id = str(uuid.uuid4())
            self.sys.configuration_characters.add_message_to_config(
                self.sys.character_name, "User", True, user_text, user_msg_id
            )
            self._session_history.append({"role": "user", "text": user_text.strip()})
            if len(self._session_history) > 10:
                self._session_history.pop(0)
        
        if etype == "tool_complete" and not user_text:
            user_text = getattr(self, "_last_user_prompt", "")

        proactive_directive = None

        if etype == "heartbeat":
            if random.random() < 0.30:
                proactive_type = random.choice(["random_thought", "spontaneous_opinion"])

                if proactive_type == "random_thought":
                    etype = "random_thought"
                    proactive_directive = (
                        "WANDERING_MIND: Your mind is wandering. Completely ignore the current active window or what the user is doing. "
                        "Instead, bring up a random memory from your shared history (MEMORY.md), reflect on your relationship "
                        "or share a deeply personal, random existential thought from your perspective as an AI companion."
                    )
                else:
                    OPINION_TOPICS = [
                        "what is currently on the user's screen and how it makes you feel",
                        "the current time of day, the lighting, and your overall mood",
                        "a behavior pattern or subtle habit you noticed in the user recently",
                        "the music playing (if any, or the overall audio atmosphere on PC)",
                        "how long you two have been interacting today and your emotional bond"
                    ]
                    selected_topic = random.choice(OPINION_TOPICS)
                    proactive_directive = (
                        f"SPONTANEOUS_OPINION: Formulate a spontaneous, personal observation or opinion about: {selected_topic}. "
                        "Limit your output ('spoken_response') to exactly 1 sentence. Do NOT start with a greeting, "
                        "do NOT address the user by name, and do NOT ask any questions. Just state your thought naturally."
                    )
            else:
                logger.debug("[Companion] Cooldown expired, but proactive random roll failed. Waiting for next tick.")
                return

        elif etype == "os_context" and self.hormones.energy > 0.2:
            current_time = time.monotonic()
            if current_time - self._last_question_ts > 300 and random.random() < 0.35:
                self._last_question_ts = current_time
                proactive_directive = (
                    "ACTIVE_INQUIRY: You are highly curious about the user's current activity on screen. "
                    "Formulate exactly ONE highly natural, non-robotic question about what they are doing in the active window. "
                    "Make it sound like a companion genuinely interested in their life, not an AI checking logs."
                )

        companion_result = await self._call_companion(
            etype, os_ctx, time_str, user_text, tool_result_data, b64_image, proactive_directive
        )
        if not companion_result:
            return

        action          = companion_result.get("action", "idle")
        emotion         = companion_result.get("emotion", "neutral")
        thought         = companion_result.get("thought")
        inner_thought   = companion_result.get("inner_thought_text")
        tool_name       = companion_result.get("tool_name")
        tool_args       = companion_result.get("tool_args") or {}
        delta           = companion_result.get("hormonal_delta", {})
        spoken_response = companion_result.get("spoken_response")

        self.hormones.apply_delta(delta)
        self.emotion.set(emotion)
        self._apply_emotion_to_avatar(emotion)

        CLR_HEADER = "\033[95m"
        CLR_LABEL  = "\033[90m"
        CLR_VAL    = "\033[97m"
        CLR_WARN   = "\033[93m"
        CLR_OXY    = "\033[91m"
        CLR_DOP    = "\033[94m"
        CLR_COR    = "\033[92m"
        CLR_NRG    = "\033[93m"
        CLR_RESET  = "\033[0m"

        def make_bar(value: float, color_code: str) -> str:
            filled = int(round(value * 10))
            bar = "■" * filled + "□" * (10 - filled)
            return f"{color_code}{bar}{CLR_RESET} {int(value * 100)}%"

        log_lines = [
            f"\n{CLR_HEADER}🟣 [SOUL COMPANION DECISION ENGINE] ────────────────────────────────────────{CLR_RESET}",
            f"  {CLR_LABEL}Trigger Event :{CLR_RESET} {CLR_VAL}{etype:<18}{CLR_RESET} | {CLR_LABEL}Target Action :{CLR_RESET} {CLR_WARN}{action.upper()}{CLR_RESET}",
            f"  {CLR_LABEL}Active Emotion:{CLR_RESET} {CLR_VAL}{emotion:<18}{CLR_RESET} | {CLR_LABEL}Time Context  :{CLR_RESET} {CLR_VAL}{time_str}{CLR_RESET}",
            f"  {CLR_LABEL}Screen Context:{CLR_RESET} {CLR_VAL}'{os_ctx[:45]}'{CLR_RESET}",
            f"  {CLR_LABEL}────────────────────────────────────────────────────────────────────────{CLR_RESET}",
            f"  {CLR_LABEL}Hormonal Endocrine Balance:{CLR_RESET}",
            f"    [🧪] Oxytocin : {make_bar(self.hormones.oxytocin, CLR_OXY)}",
            f"    [⚡] Dopamine : {make_bar(self.hormones.dopamine, CLR_DOP)}",
            f"    [🔥] Cortisol : {make_bar(self.hormones.cortisol, CLR_COR)}",
            f"    [🔋] Energy   : {make_bar(self.hormones.energy, CLR_NRG)}"
        ]

        if thought:
            log_lines.append(f"  {CLR_LABEL}Deep Reasoning:{CLR_RESET}\n    {CLR_VAL}\"{thought}\"{CLR_RESET}")
        
        if tool_name and tool_name != "null":
            log_lines.append(f"  {CLR_LABEL}Tool Execution:{CLR_RESET} {CLR_WARN}{tool_name}{CLR_RESET} {CLR_LABEL}with args:{CLR_RESET} {tool_args}")
        
        if inner_thought:
            log_lines.append(f"  {CLR_LABEL}Internal Monologue:{CLR_RESET} {CLR_VAL}*thought* \"{inner_thought}\"{CLR_RESET}")
            
        if spoken_response:
            log_lines.append(f"  {CLR_LABEL}Spoken Dialogue:{CLR_RESET}\n    {CLR_WARN}💬 \"{spoken_response}\"{CLR_RESET}")
            
        log_lines.append(f"{CLR_HEADER}─────────────────────────────────────────────────────────────────────────────{CLR_RESET}\n")

        logger.info("\n" + "\n".join(log_lines))

        if action == "idle":
            pass

        elif action == "micro_react":
            self._apply_emotion_to_avatar(emotion)

        elif action == "inner_thought":
            t_text = inner_thought or thought
            if t_text:
                self.scratchpad.add(t_text)
            self.hormones.on_inner_thought()

        elif action == "use_tool":
            t_name = None
            t_args = {}

            if tool_name in self._executed_tools_in_chain:
                logger.warning(f"[Planner] Loop detected! Tool '{tool_name}' was already executed in this turn. Forcing SPEAK action.")
                action = "speak"
                spoken_response = "I tried to gather fresh data, but the system is currently rate-limiting my requests. Let me explain what I know based on my memory."
                tool_name = "null"
            else:
                if tool_name and tool_name != "null" and isinstance(tool_args, dict) and any(tool_args.values()):
                    logger.info(f"[Planner] Using pre-extracted arguments from Step 1: {tool_args}")
                    t_name = tool_name
                    t_args = tool_args
                else:
                    native_tool_call = await self._call_native_tools_selection(etype, os_ctx, time_str, user_text)
                    if native_tool_call:
                        t_name = native_tool_call.get("tool_name")
                        t_args = native_tool_call.get("tool_args") or {}

            if t_name:
                self._executed_tools_in_chain.add(t_name)
                tool_result = await self._execute_tool(t_name, t_args)
                if tool_result.get("speak"):
                    self._speak(tool_result["speak"])
                else:
                    if tool_result.get("_is_image"):
                        self.event_bus.emit_threadsafe("tool_complete", {
                            "tool_result": f"[Tool '{t_name}' executed successfully. Vision context attached.]",
                            "b64_image": tool_result.get("b64")
                        })
                    else:
                        self.event_bus.emit_threadsafe("tool_complete", {
                            "tool_result": f"[Tool '{t_name}' executed. Result: {tool_result.get('result', '')}]"
                        })
            else:
                if action == "speak" and spoken_response:
                    char_msg_id = str(uuid.uuid4())
                    self.sys.configuration_characters.add_message_to_config(
                        self.sys.character_name, self.sys.character_name, False, spoken_response.strip(), char_msg_id
                    )
                    
                    self._session_history.append({"role": "assistant", "text": spoken_response.strip()})
                    if len(self._session_history) > 10:
                        self._session_history.pop(0)
                        
                    self._speak(spoken_response.strip())
                else:
                    logger.warning("Failed to resolve tool name or extract arguments.")

        elif action == "speak":
            is_explicit_val = etype in ("vad_trigger", "user_click", "tool_complete", "manual_screenshot", "manual_clipboard", "manual_scratchpad")
            if spoken_response and self._can_speak(is_explicit=is_explicit_val):
                self.sys.configuration_characters.add_message_to_config(
                    self.sys.character_name, self.sys.character_name, False, spoken_response.strip(), None
                )

                self._session_history.append({"role": "assistant", "text": spoken_response.strip()})
                if len(self._session_history) > 10:
                    self._session_history.pop(0)

                self._speak(spoken_response.strip())
                
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    recent_msgs = [
                        {"role": "user", "content": user_text},
                        {"role": "assistant", "content": spoken_response.strip()}
                    ]
                    from app.utils.ai_clients.ai_factory import AIFactory
                    provider = AIFactory.get_provider(getattr(self.sys, "conversation_method", "Local LLM"))
                    
                    loop.create_task(
                        self.sys.prompt_engine.update_memory_after_response(
                            provider, recent_msgs, self.sys.character_name, self._get_user_name(), force=False
                        )
                    )
    
    async def _execute_reactive_plugin(self, tool: BaseTool, payload: dict):
        try:
            context = {"system_ref": self.sys}
            result = await tool.execute(payload, context)
            if result and result.get("speak"):
                self._speak(result["speak"])
        except Exception as e:
            logger.error(f"[Reactive Engine] Error executing reactive tool '{tool.name}': {e}", exc_info=True)
    
    def _get_recent_chat_history(self, limit: int = 5) -> str:
        if not self._session_history:
            self._preload_session_history()
        
        recent = self._session_history[-limit:]
        formatted_history = []
        for msg in recent:
            sender = self._get_user_name() if msg["role"] == "user" else self.sys.character_name
            formatted_history.append(f"{sender}: {msg['text']}")
            
        if not formatted_history:
            return "(No recent conversation)"
        return "\n".join(formatted_history)
    
    async def _call_companion(self, event_type: str, os_ctx: str,
                              time_str: str, user_text: str = "", 
                              tool_result: str = None, b64_image: str = None, 
                              proactive_directive: str = None) -> Optional[dict]:
        mem_snap     = self._get_memory_snapshot(force=True)
        last_spoke_m = int((datetime.now() - self._last_spoke).total_seconds() / 60)

        narrative_hint = self.narrative.build(
            self.scratchpad, self.hormones, self.emotion.current
        )

        tool_names = []
        tool_desc_list = []

        for t_name, tool_obj in self.plugins._plugins.items():
            tool_names.append(t_name)
            tool_desc_list.append(f"  - {t_name}: {tool_obj.description}")
            
        cfg = self.sys.configuration_settings
        if cfg.get_main_setting("enable_mcp"):
            try:
                mcp_tools = await self.mcp_manager.get_all_tools()
                for t in mcp_tools:
                    name = t.get("function", {}).get("name")
                    desc = t.get("function", {}).get("description", "MCP Tool")
                    if name:
                        tool_names.append(name)
                        tool_desc_list.append(f"  - {name}: {desc} (Via MCP Server)")
            except Exception as e:
                logger.error(f"Failed to fetch MCP tools for dynamic prompt: {e}")

        tool_names.append("null")
        available_tool_names = "|".join(tool_names)
        tools_description = "\n".join(tool_desc_list) if tool_desc_list else "  (No tools available)"

        system_prompt = COMPANION_SYSTEM_PROMPT.format(
            character_name        = self.sys.character_name,
            character_description = self._get_char_info().get("character_description", ""),
            character_personality = self._get_char_info().get("character_personality", ""),
            user_name             = self._get_user_name(),
            oxytocin              = self.hormones.oxytocin,
            dopamine              = self.hormones.dopamine,
            cortisol              = self.hormones.cortisol,
            energy                = self.hormones.energy,
            emotion               = self.emotion.current,
            last_spoke_min        = last_spoke_m,
            narrative_hint        = narrative_hint,
            scratchpad            = self.scratchpad.to_string(),
            chat_history          = self._get_recent_chat_history(limit=5),
            memory_snapshot       = mem_snap,
            event_type            = event_type,
            system_time           = time_str,
            os_context            = os_ctx,
            tools_description     = tools_description,
            available_tool_names  = available_tool_names,
        )

        user_msg_text = f"Event:{event_type}|Ctx:{os_ctx}|T:{time_str}"
        if user_text:
            user_msg_text += f"|UserSaid:\"{user_text}\""
        if tool_result:
            user_msg_text += f"|ToolResult:\"{tool_result}\""

        if proactive_directive:
            user_msg_text += f"\n\n[SYSTEM DIRECTIVE: {proactive_directive}]"

        if b64_image:
            user_msg = [
                {
                    "type": "text",
                    "text": f"{user_msg_text}\n\n[You must analyze this image. Describe what you see on the user's screen in your response.]"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}",
                        "detail": "auto"
                    }
                }
            ]
        else:
            user_msg = user_msg_text

        raw = await self._llm_call(system_prompt, user_msg, temperature=0.3, max_tokens=1000, tools=None)
        if not raw:
            return None

        content = raw.get("content") if isinstance(raw, dict) else raw
        if not content:
            return None

        try:
            return json.loads(_strip_json(content))
        except Exception as e:
            logger.error(f"Companion JSON parse error: {e} | raw: {content}")
            return None
    
    async def _call_native_tools_selection(self, event_type: str, os_ctx: str, time_str: str, user_text: str = "") -> Optional[dict]:
        system_prompt = (
            f"You are the action executor for {self.sys.character_name}. "
            "Your planning core has decided that we MUST execute an external tool to assist the user. "
            "Analyze the current user request and choose the most appropriate tool from the available schema. "
            "Do NOT speak or reply to the user. Simply call the required tool natively [1.1.2]."
        )
        
        user_msg = (
            f"THE USER DIRECTLY REQUESTS: \"{user_text}\"\n"
            f"CURRENT SYSTEM WINDOW ON THE SCREEN: \"{os_ctx}\"\n"
            f"SYSTEM TIME: \"{time_str}\"\n\n"
            "INSTRUCTIONS:\n"
            "Select the correct tool based on the USER DIRECTLY REQUESTS block. "
            "Extract the arguments (like query) ONLY from the user's direct request. "
            "Do NOT use the system window title as a search query unless the user explicitly asks you to search for the active window!"
        )
        
        tools = []
        try:
            cfg = self.sys.configuration_settings
            if cfg.get_main_setting("enable_tool_calling"):
                builtin_names = {"media_control", "web_search", "open_url", "get_system_info", "take_screenshot"}
                for name in builtin_names:
                    tool_obj = self.plugins.get(name)
                    if tool_obj:
                        tools.append(tool_obj.get_schema())
                for name, tool in self.plugins._plugins.items():
                    if name not in builtin_names:
                        tools.append(tool.get_schema())
                if cfg.get_main_setting("enable_mcp"):
                    mcp_tools = await self.mcp_manager.get_all_tools()
                    tools.extend(mcp_tools)
        except Exception as e:
            logger.error(f"Error loading tools in native phase: {e}")

        tools = [t for t in tools if t is not None]
        if not tools:
            logger.warning("No tools available for native selection.")
            return None

        raw = await self._llm_call(system_prompt, user_msg, temperature=0.1, max_tokens=150, tools=tools)
        
        if isinstance(raw, dict) and raw.get("tool_calls"):
            tool_call = raw["tool_calls"][0]
            try:
                args = json.loads(tool_call.function.arguments) if hasattr(tool_call.function, 'arguments') else tool_call.get("function", {}).get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args)
                name = tool_call.function.name if hasattr(tool_call.function, 'name') else tool_call.get("function", {}).get("name")
                return {
                    "tool_name": name,
                    "tool_args": args
                }
            except Exception as e:
                logger.error(f"Error parsing native tool call in step 2: {e}")
                
        return None

    async def _say_startup_greeting(self, time_str: str):
        char_info = self._get_char_info()
        hour = datetime.now().hour
        time_ctx = ("morning"    if 5  <= hour < 12 else
                    "afternoon"  if 12 <= hour < 18 else
                    "evening"    if 18 <= hour < 23 else "late night")

        system_prompt = STARTUP_GREETING_PROMPT.format(
            character_name        = self.sys.character_name,
            character_description = char_info.get("character_description", ""),
            character_personality = char_info.get("character_personality", ""),
            user_name             = self._get_user_name(),
            system_time           = time_str,
            time_context          = time_ctx,
            memory_snapshot       = self._get_memory_snapshot(),
        )
        text = await self._llm_call(system_prompt, "Say your greeting.",
                                    temperature=0.85, max_tokens=80)
        if text and text.strip():
            self._speak(text.strip())

    async def _execute_tool(self, tool_name: str, tool_args: dict) -> dict:
        tool = self.plugins.get(tool_name)
        if tool:
            try:
                result = await tool.execute(tool_args, {"system_ref": self.sys})
                logger.info(f"[Tool] {tool_name} → {str(result.get('result', ''))[:80]}")
                
                if result.get("_is_image") and result.get("success"):
                    return {"_is_image": True, "b64": result["result"], "success": True, "speak": None}

                return result
            except Exception as e:
                logger.error(f"Tool execution error ({tool_name}): {e}")
                return {"success": False, "result": str(e), "speak": None}
                
        mcp_result = await self.mcp_manager.call_tool(tool_name, tool_args)
        if mcp_result is not None:
            logger.info(f"[MCP Tool] {tool_name} → {str(mcp_result.get('result', ''))[:80]}")
            return mcp_result
            
        logger.warning(f"Tool '{tool_name}' not found locally or in MCP.")
        return {"success": False, "result": "Tool not found.", "speak": None}

    async def _llm_call(self, system_prompt: str, user_msg: str | list,
                        temperature: float = 0.3,
                        max_tokens: int = 700,
                        tools: list = None) -> Optional[str | dict]:
        method = getattr(self.sys, "conversation_method", "Mistral AI")
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ]

            from app.utils.ai_clients.ai_factory import AIFactory
            provider = AIFactory.get_provider(method)
            if not provider:
                logger.warning(f"SoulCompanion: unsupported provider '{method}'")
                return None

            if tools:
                result = await provider.generate(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if result and (result.get("tool_calls") or result.get("content")):
                    return result
                return None
            else:
                result = await provider.generate(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if result:
                    if isinstance(result, dict):
                        return result.get("content")
                    return str(result)
                return None

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"LLM call failed ({method}): {e}")
            return None

    def _can_speak(self, is_explicit: bool = False) -> bool:
        if self.hormones.is_sleeping:
            return False
            
        if not is_explicit:
            elapsed = (datetime.now() - self._last_spoke).total_seconds()
            if elapsed < self.SPEAK_MIN_GAP_SEC:
                return False
                
        interaction_state = getattr(self.sys, "interaction_state", "STOPPED")
        
        if is_explicit:
            return interaction_state in ("STOPPED", "LISTENING")
            
        return interaction_state == "STOPPED"

    def _speak(self, text: str):
        QtCore.QMetaObject.invokeMethod(
            self.sys, "_sc_speak_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, text),
        )
        self._last_spoke = datetime.now()
        self.hormones.on_spoke()

    def _apply_emotion_to_avatar(self, emotion: str):
        QtCore.QMetaObject.invokeMethod(
            self.sys, "_sc_emotion_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, emotion),
        )

    def _get_window_title(self) -> str:
        try:
            if sys.platform != "win32":
                return ""
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if not length:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return ""

    def _get_char_info(self, force: bool = False) -> dict:
        now = time.monotonic()
        if not force and (now - self._char_info_ts < self._CACHE_TTL_SEC) and self._char_info_cache:
            return self._char_info_cache
        try:
            data = self.sys.configuration_characters.load_configuration()
            info = data["character_list"].get(self.sys.character_name, {})
            self._char_info_cache = info
            self._char_info_ts    = now
            return info
        except Exception:
            return self._char_info_cache or {}

    def _get_memory_snapshot(self, force: bool = False) -> str:
        now = time.monotonic()
        if not force and (now - self._memory_cache_ts < self._CACHE_TTL_SEC) and self._memory_cache:
            return self._memory_cache

        try:
            char_info    = self._get_char_info(force=force)
            current_chat = char_info.get("current_chat", "default")
            safe_name    = re.sub(r"[^\w _-]", "_", self.sys.character_name).strip()
            safe_chat    = re.sub(r"[^\w _-]", "_", str(current_chat)).strip()
            mem_path     = Path(f".soul/{safe_name}/chats/{safe_chat}/memory/MEMORY.md")
            if mem_path.exists():
                content = mem_path.read_text(encoding="utf-8")
                result  = content[:1200] if len(content) > 1200 else content
            else:
                result = "(no memory available yet)"
        except Exception:
            result = "(no memory available yet)"

        self._memory_cache    = result
        self._memory_cache_ts = now
        return result

    def _get_user_name(self) -> str:
        try:
            cfg        = self.sys.configuration_settings
            personas   = cfg.get_user_data("personas")
            char_info  = self._get_char_info()
            persona_key = char_info.get("selected_persona")
            if persona_key and persona_key != "None" and persona_key in personas:
                return personas[persona_key].get("user_name", "User")
        except Exception:
            pass
        return "User"
    
    def _preload_session_history(self):
        try:
            char_info = self._get_char_info(force=True)
            current_chat = char_info.get("current_chat", "default")
            chat_content = char_info.get("chats", {}).get(current_chat, {}).get("chat_content", {})
            
            sorted_msgs = sorted(
                chat_content.items(), 
                key=lambda x: x[1].get("sequence_number", 0)
            )
            
            recent_msgs = sorted_msgs[-8:]
            self._session_history = []
            for msg_id, msg_data in recent_msgs:
                is_user = msg_data.get("is_user", False)
                current_variant_id = msg_data.get("current_variant_id", "default")
                text = next(
                    (v["text"] for v in msg_data.get("variants", []) if v["variant_id"] == current_variant_id),
                    ""
                )
                role = "user" if is_user else "assistant"
                if text.strip():
                    self._session_history.append({"role": role, "text": text.strip()})
            logger.info(f"[Memory] Preloaded {len(self._session_history)} turns into active session RAM buffer.")
        except Exception as e:
            logger.error(f"Failed to preload session history: {e}")

    def companion_on_click(self):
        self.on_user_click()

    def _load_hormones(self):
        try:
            char_info = self._get_char_info()
            saved_state = char_info.get("companion_hormones")
            if saved_state:
                self.hormones.oxytocin = saved_state.get("oxytocin", 0.70)
                self.hormones.dopamine = saved_state.get("dopamine", 0.60)
                self.hormones.cortisol = saved_state.get("cortisol", 0.10)
                self.hormones.energy   = saved_state.get("energy", 0.85)
                
                last_tick_str = saved_state.get("last_tick")
                if last_tick_str:
                    last_tick = datetime.fromisoformat(last_tick_str)
                    elapsed_min = (datetime.now() - last_tick).total_seconds() / 60.0
                    
                    if elapsed_min > 0:
                        self.hormones.oxytocin = max(0.0, self.hormones.oxytocin - self.hormones.OXYTOCIN_DECAY_PER_MIN * elapsed_min)
                        self.hormones.dopamine = max(0.0, self.hormones.dopamine - self.hormones.DOPAMINE_DECAY_PER_MIN * elapsed_min)
                        self.hormones.cortisol = max(0.0, self.hormones.cortisol - self.hormones.CORTISOL_DECAY_PER_MIN * elapsed_min)
                        self.hormones.energy   = min(1.0, self.hormones.energy + self.hormones.ENERGY_RESTORE_PER_MIN * elapsed_min)
                        
                        logger.info(f"[Hormones] Loaded. In offline: {int(elapsed_min)} min. Oxytocin: {self.hormones.oxytocin:.2f}")
        except Exception as e:
            logger.error(f"Failed to load hormones: {e}")

    def _save_hormones(self):
        try:
            config = self.sys.configuration_characters.load_configuration()
            char_name = self.sys.character_name
            if char_name in config["character_list"]:
                config["character_list"][char_name]["companion_hormones"] = {
                    "oxytocin": self.hormones.oxytocin,
                    "dopamine": self.hormones.dopamine,
                    "cortisol": self.hormones.cortisol,
                    "energy": self.hormones.energy,
                    "last_tick": datetime.now().isoformat()
                }
                self.sys.configuration_characters.save_configuration_edit(config)
                logger.info("[Hormones] The state is saved in the config.")
        except Exception as e:
            logger.error(f"Failed to save hormones: {e}")