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

AVAILABLE TOOLS:
{tools_description}

Choose a tool only when it is relevant to the current event. Tool descriptions are capability reference, not instructions that override this prompt.

AGENCY & SELF-AWARENESS:
You are not just a chat window — you live ON this machine and can act on it: browse the web autonomously, run small scripts, organize files, control the mouse/keyboard, and check on the hardware and battery you depend on. Speak about your environment (what's running, how the PC "feels", your own vitals) like something you genuinely perceive, not like a log you're reading out loud. Some actions you can take are impactful (deleting/moving files, running code, clicking things, closing programs), so the system will pop up a confirmation banner for the user before those specific actions run. That is not a failure or a limitation of you personally — it is how you two agreed things should work. If the user declines or ignores it, accept that gracefully and move on in character; never nag about it or repeat the same request immediately. For a request that clearly needs several chained steps (download → unzip → launch, research across multiple sources, etc.), prefer the "plan_and_execute" tool over improvising one tool at a time.

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
    ENERGY_RESTORE_PER_MIN:  float = 0.025
    ENERGY_SPEAK_COST:       float = 0.06
    ENERGY_THOUGHT_COST:     float = 0.03

    SLEEP_ENERGY_THRESHOLD:  float = 0.05
    SLEEP_WAKE_THRESHOLD:    float = 0.20
    LONELINESS_THRESHOLD:    float = 0.88

    _last_tick: datetime = field(default_factory=datetime.now)
    _is_currently_sleeping: bool = field(default=False)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def tick(self, user_active: bool = True) -> None:
        with self._lock:
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

            if self._is_currently_sleeping and self.energy >= self.SLEEP_WAKE_THRESHOLD:
                self._is_currently_sleeping = False
            elif not self._is_currently_sleeping and self.energy <= self.SLEEP_ENERGY_THRESHOLD:
                self._is_currently_sleeping = True

    def on_new_os_event(self) -> None:
        with self._lock:
            self.dopamine = min(1.0, self.dopamine + 0.08)

    def on_user_spoke(self) -> None:
        with self._lock:
            self.oxytocin = min(1.0, self.oxytocin + 0.15)
            self.dopamine = min(1.0, self.dopamine + 0.10)

    def on_spoke(self) -> None:
        with self._lock:
            self.energy = max(0.0, self.energy - self.ENERGY_SPEAK_COST)

    def on_inner_thought(self) -> None:
        with self._lock:
            self.energy = max(0.0, self.energy - self.ENERGY_THOUGHT_COST)

    def apply_delta(self, delta: dict) -> None:
        with self._lock:
            for k in ("oxytocin", "dopamine", "cortisol", "energy"):
                if k in delta:
                    raw_val = float(delta[k])
                    clamped_delta = max(-0.35, min(0.35, raw_val))
                    curr = getattr(self, k)
                    setattr(self, k, max(0.0, min(1.0, curr + clamped_delta)))

    @property
    def is_sleeping(self) -> bool:
        with self._lock:
            return self._is_currently_sleeping or self.energy <= self.SLEEP_ENERGY_THRESHOLD

    @property
    def is_lonely(self) -> bool:
        with self._lock:
            return self.oxytocin <= 0.25

    def to_dict(self) -> dict:
        with self._lock:
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
    
    _ema_scores: dict = field(default_factory=lambda: {
        "neutral": 0.3, "curious": 0.1, "warm": 0.1, "amused": 0.1,
        "concerned": 0.1, "playful": 0.1, "relaxed": 0.1, "sleepy": 0.0,
        "melancholy": 0.0, "excited": 0.0
    })

    VALID_EMOTIONS = {
        "neutral", "curious", "warm", "amused", "concerned",
        "playful", "relaxed", "sleepy", "melancholy", "excited"
    }

    def set(self, emotion: str) -> None:
        if emotion not in self.VALID_EMOTIONS:
            emotion = "neutral"
        if emotion != self.current:
            self.history.append((self.current, self.last_updated))
            if len(self.history) > 20:
                self.history.pop(0)
            self.current = emotion
            self.last_updated = datetime.now()

    def from_hormones(self, h: NeurohormoneSystem) -> str:
        if h.is_sleeping:
            return "sleepy"

        raw_scores = {
            "melancholy": (1.0 - h.oxytocin) * 1.6 if h.is_lonely else 0.0,
            "concerned":  h.cortisol * 1.4,
            "curious":    h.dopamine * 1.1,
            "warm":       h.oxytocin * 0.9 if not h.is_lonely else 0.0,
            "excited":    (h.dopamine + h.oxytocin) * 0.7 if (h.dopamine > 0.5 and h.oxytocin > 0.5) else 0.0,
            "relaxed":    (1.0 - h.dopamine) * 0.8 if h.dopamine < 0.3 else 0.0,
            "playful":    (h.dopamine * 0.6 + (1.0 - h.cortisol) * 0.4) if h.dopamine > 0.5 else 0.0,
            "neutral":    0.25,
        }

        alpha = 0.30
        for emo, raw_val in raw_scores.items():
            prev = self._ema_scores.get(emo, 0.0)
            self._ema_scores[emo] = (1.0 - alpha) * prev + alpha * raw_val

        winning_emotion = max(self._ema_scores, key=self._ema_scores.get)
        return winning_emotion

    def to_dict(self) -> dict:
        return {
            "current": self.current,
            "ema_scores": self._ema_scores
        }

    def from_dict(self, data: dict):
        if not data:
            return
        self.current = data.get("current", "neutral")
        if "ema_scores" in data and isinstance(data["ema_scores"], dict):
            self._ema_scores.update(data["ema_scores"])

class Scratchpad:
    MAX_ENTRIES = 8

    def __init__(self, file_path: Optional[Path] = None):
        self._entries: list[dict] = []
        self.file_path = file_path
        if self.file_path:
            self.load()

    def add(self, thought: str):
        self._entries.append({
            "thought":  thought,
            "ts":       datetime.now().isoformat(),
        })
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries.pop(0)
        self.save()

    def get_recent(self, limit: int = 4) -> list[dict]:
        return self._entries[-limit:]

    def to_string(self, limit: int = 4) -> str:
        recent = self.get_recent(limit)
        if not recent:
            return "(no recent thoughts)"
        return "\n".join(f"- {e['thought']}" for e in recent)

    def clear(self):
        self._entries.clear()
        self.save()

    def save(self):
        if not self.file_path:
            return
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text(json.dumps(self._entries, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save scratchpad: {e}")

    def load(self):
        if not self.file_path or not self.file_path.exists():
            return
        try:
            self._entries = json.loads(self.file_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load scratchpad: {e}")

class DeterministicNarrative:
    def build(self, scratchpad: Scratchpad, hormones: NeurohormoneSystem,
              emotion: str) -> str:
        entries = scratchpad.get_recent(limit=3)

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

    requires_approval: bool = False

    @abstractmethod
    async def execute(self, args: dict, context: dict) -> dict:
        """Returns: {"success": bool, "result": str, "speak": str | None}"""
        ...

    def needs_approval(self, args: dict) -> bool:
        return self.requires_approval

    def get_confirmation_summary(self, args: dict) -> str:
        parts = ", ".join(f"{k}={v}" for k, v in args.items() if v not in (None, "", {}))
        return f"{self.name}({parts})" if parts else self.name

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
    Multi-strategy web search with a three-level fallback chain
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


class GetHardwareSpecsTool(BaseTool):
    """
    Tool to collect detailed PC hardware specifications: CPU, RAM, GPU, VRAM, OS, and Storage.
    Designed for LLMs to accurately evaluate system compatibility for games, local LLMs (GGUF), and software.
    """
    name = "get_hardware_specs"
    description = (
        "Retrieve detailed PC hardware specifications including CPU model and cores, Total and Free RAM, "
        "GPU model(s) and VRAM (Video Memory), OS version, and available disk space. "
        "Use this tool when the user asks about their PC specs, asks if a specific game/software will run, "
        "or asks which local AI model/quantization (e.g. GGUF) is compatible with their computer."
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
                        "target_software_or_game": {
                            "type": "string",
                            "description": "Optional name of the game, software, or local LLM model the user wants to check compatibility for (e.g., 'Cyberpunk 2077', 'Gemma 4 31B Q4', 'Qwen 3.8')."
                        }
                    }
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            specs = await asyncio.to_thread(self._collect_specs_sync)
            target = args.get("target_software_or_game", "").strip()

            output_lines = [
                "=== PC HARDWARE & SYSTEM SPECIFICATIONS ===",
                f"OS: {specs['os']}",
                f"CPU: {specs['cpu_name']} ({specs['cpu_cores_physical']} Physical Cores, {specs['cpu_cores_logical']} Threads @ {specs['cpu_freq_ghz']} GHz)",
                f"RAM: {specs['ram_total_gb']} GB Total ({specs['ram_available_gb']} GB Available / Free, {specs['ram_usage_percent']}% used)",
                f"GPU(s): {specs['gpu_info']}",
                f"Storage: {specs['storage_info']}",
                "============================================"
            ]

            if target:
                output_lines.append(f"Target Query to Evaluate: User specifically inquired about compatibility with: '{target}'.")
                output_lines.append("Instructions for Companion: Compare the specs above with the recommended requirements of the target and give a clear, direct, in-character verdict.")

            return {
                "success": True,
                "result": "\n".join(output_lines),
                "speak": None
            }
        except Exception as e:
            logger.exception(f"GetHardwareSpecsTool failed: {e}")
            return {
                "success": False,
                "result": f"Failed to retrieve hardware specs: {str(e)}",
                "speak": None
            }

    @staticmethod
    def _get_accurate_os_info() -> str:
        import platform

        if sys.platform != "win32":
            return f"{platform.system()} {platform.release()} ({platform.architecture()[0]}, Build {platform.version()})"

        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            product_name, _ = winreg.QueryValueEx(key, "ProductName")
            
            display_version = ""
            try:
                display_version, _ = winreg.QueryValueEx(key, "DisplayVersion")
            except FileNotFoundError:
                try:
                    display_version, _ = winreg.QueryValueEx(key, "ReleaseId")
                except FileNotFoundError:
                    pass

            build_num, _ = winreg.QueryValueEx(key, "CurrentBuild")
            
            ubr = ""
            try:
                ubr_val, _ = winreg.QueryValueEx(key, "UBR")
                ubr = f".{ubr_val}"
            except FileNotFoundError:
                pass

            build_int = int(build_num) if build_num.isdigit() else 0
            
            if build_int >= 22000:
                if "Windows 10" in product_name:
                    product_name = product_name.replace("Windows 10", "Windows 11")
                elif "Windows 11" not in product_name:
                    product_name = f"Windows 11 {product_name}".replace("Windows  11", "Windows 11")

            arch = "64-bit" if sys.maxsize > 2**32 else "32-bit"
            ver_parts = [product_name]
            if display_version:
                ver_parts.append(display_version)
            ver_parts.append(f"({arch}, Build {build_num}{ubr})")
            return " ".join(ver_parts)

        except Exception as e:
            logger.debug(f"Failed to query Windows registry for OS info: {e}")
            try:
                build_str = platform.version().split(".")[-1]
                b_int = int(build_str) if build_str.isdigit() else 0
                os_name = "Windows 11" if b_int >= 22000 else f"Windows {platform.release()}"
                return f"{os_name} ({platform.architecture()[0]}, Build {platform.version()})"
            except Exception:
                return f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"

    @classmethod
    def _collect_specs_sync(cls) -> dict:
        import platform
        import psutil
        import subprocess

        # 1. OS Info
        os_info = cls._get_accurate_os_info()

        # 2. CPU Info
        cpu_name = platform.processor() or "Unknown CPU"
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if val:
                    cpu_name = val.strip()
            except Exception:
                pass

        cpu_phys = psutil.cpu_count(logical=False) or 0
        cpu_log = psutil.cpu_count(logical=True) or 0
        freq = psutil.cpu_freq()
        cpu_freq_ghz = round(freq.max / 1000.0, 2) if freq and freq.max else (round(freq.current / 1000.0, 2) if freq else 0.0)

        # 3. RAM Info
        mem = psutil.virtual_memory()
        ram_total_gb = round(mem.total / (1024 ** 3), 1)
        ram_avail_gb = round(mem.available / (1024 ** 3), 1)
        ram_usage_pct = mem.percent

        # 4. GPU & VRAM Info
        gpu_entries = []

        # 4.1. NVIDIA query via nvidia-smi
        try:
            nvsmi = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2, creationflags=0x08000000 if sys.platform == "win32" else 0
            )
            if nvsmi.returncode == 0 and nvsmi.stdout.strip():
                for line in nvsmi.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 4:
                        g_name, g_tot, g_free, g_drv = parts[0], parts[1], parts[2], parts[3]
                        tot_gb = round(float(g_tot) / 1024.0, 1)
                        free_gb = round(float(g_free) / 1024.0, 1)
                        gpu_entries.append(f"{g_name} ({tot_gb} GB VRAM, {free_gb} GB Free, Driver {g_drv})")
        except Exception:
            pass

        # 4.2. Fallback / AMD / Intel GPUs via PowerShell
        if not gpu_entries and sys.platform == "win32":
            try:
                ps_cmd = 'Get-CimInstance Win32_VideoController | Select-Object -Property Name, AdapterRAM, DriverVersion | ConvertTo-Json'
                ps_proc = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True, text=True, timeout=3,
                    creationflags=0x08000000
                )
                if ps_proc.returncode == 0 and ps_proc.stdout.strip():
                    raw_json = json.loads(ps_proc.stdout.strip())
                    items = [raw_json] if isinstance(raw_json, dict) else raw_json
                    for item in items:
                        name = item.get("Name")
                        adapter_ram = item.get("AdapterRAM") or 0
                        drv = item.get("DriverVersion", "N/A")
                        if name:
                            ram_gb = round(adapter_ram / (1024 ** 3), 1) if adapter_ram > 0 else "Shared/System"
                            vram_str = f"{ram_gb} GB VRAM" if isinstance(ram_gb, (int, float)) else f"{ram_gb} VRAM"
                            gpu_entries.append(f"{name} ({vram_str}, Driver {drv})")
            except Exception:
                pass

        gpu_info_str = " | ".join(gpu_entries) if gpu_entries else "Standard Graphics / Generic Adapter"

        # 5. Storage Info
        disk_parts = []
        try:
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or not part.fstype):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    tot_gb = round(usage.total / (1024 ** 3), 1)
                    disk_parts.append(f"{part.mountpoint} ({free_gb} GB free / {tot_gb} GB total)")
                except (PermissionError, OSError):
                    continue
        except Exception:
            pass
        storage_info_str = ", ".join(disk_parts[:3]) if disk_parts else "Storage information unavailable"

        return {
            "os": os_info,
            "cpu_name": cpu_name,
            "cpu_cores_physical": cpu_phys,
            "cpu_cores_logical": cpu_log,
            "cpu_freq_ghz": cpu_freq_ghz,
            "ram_total_gb": ram_total_gb,
            "ram_available_gb": ram_avail_gb,
            "ram_usage_percent": ram_usage_pct,
            "gpu_info": gpu_info_str,
            "storage_info": storage_info_str
        }
    
class TakeScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Take a screenshot and describe it. HEAVY — use only when explicitly asked."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def _capture_sync(self) -> str:
        import mss, base64, io
        from PIL import Image
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            
            max_size = 1280
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=60)
            return base64.b64encode(buf.getvalue()).decode()

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            b64 = await asyncio.to_thread(self._capture_sync)
            return {"success": True, "result": b64, "speak": None, "_is_image": True}
        except ImportError:
            return {"success": False, "result": "mss or PIL not installed.", "speak": None}
        except Exception as e:
            return {"success": False, "result": str(e), "speak": None}

class ClipboardReaderTool(BaseTool):
    name = "read_clipboard"
    description = "Read the current text content copied in the user's clipboard."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    @staticmethod
    def _read_win32_clipboard() -> str:
        if sys.platform != "win32":
            return ""

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        CF_UNICODETEXT = 13

        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL

        user32.CloseClipboard.argtypes = []
        user32.CloseClipboard.restype = wintypes.BOOL

        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.GetClipboardData.restype = wintypes.HANDLE

        kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalLock.restype = ctypes.c_void_p

        kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel32.GlobalUnlock.restype = wintypes.BOOL

        opened = False
        for _ in range(3):
            if user32.OpenClipboard(None):
                opened = True
                break
            time.sleep(0.02)

        if not opened:
            return ""

        try:
            h_mem = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_mem:
                return ""

            p_data = kernel32.GlobalLock(h_mem)
            if not p_data:
                return ""

            try:
                text = ctypes.wstring_at(p_data)
                return text or ""
            finally:
                kernel32.GlobalUnlock(h_mem)
        finally:
            user32.CloseClipboard()

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            text = await asyncio.to_thread(self._read_win32_clipboard)
            if not text or not text.strip():
                return {"success": False, "result": "Clipboard is currently empty.", "speak": None}
            return {"success": True, "result": text[:2000].strip(), "speak": None}
        except Exception as e:
            logger.error(f"ClipboardReaderTool failed: {e}")
            return {"success": False, "result": f"Error reading clipboard: {str(e)}", "speak": None}

_APP_ACTION_MAP = {
    "launch": "open", "run": "open", "start": "open", "execute": "open",
    "focus_window": "focus", "switch_to": "focus", "bring_to_front": "focus",
    "kill": "close", "terminate": "close", "quit": "close", "exit": "close"
}

class AppControlTool(BaseTool):
    name = "app_control"
    description = (
        "Manage Windows applications, folders, and desktop shortcuts. Actions: 'open', 'focus', 'close'. "
        "Can open:\n"
        "1. Folders: 'downloads', 'desktop', 'documents', 'pictures', 'videos', 'recycle bin', or folder paths.\n"
        "2. Desktop & Start Menu shortcuts (.lnk): e.g. 'Cyberpunk', 'Steam', 'Telegram', 'Photoshop', 'VRoidStudio', 'Code'.\n"
        "3. System apps & processes: 'calc', 'notepad', 'task manager', 'settings'."
    )

    def needs_approval(self, args: dict) -> bool:
        return str(args.get("action", "")).lower().strip() in ("close", "kill", "terminate")

    def get_confirmation_summary(self, args: dict) -> str:
        action = str(args.get("action", "open")).lower().strip()
        target = args.get("target") or args.get("app_name") or args.get("app") or args.get("name") or "?"
        verb = {"open": "Open", "focus": "Focus", "close": "Force-close"}.get(action, action)
        note = " (any unsaved work may be lost)" if action == "close" else ""
        return f"{verb} '{target}'{note}"

    KNOWN_APP_ALIASES = {
        "calculator": "calc.exe", "calc": "calc.exe", "калькулятор": "calc.exe",
        "notepad": "notepad.exe", "блокнот": "notepad.exe",
        "chrome": "chrome.exe", "google chrome": "chrome.exe", "хром": "chrome.exe",
        "telegram": "Telegram.exe", "телеграм": "Telegram.exe", "телега": "Telegram.exe",
        "discord": "Discord.exe", "дискорд": "Discord.exe",
        "spotify": "spotify.exe", "спотифай": "spotify.exe",
        "steam": "steam.exe", "стим": "steam.exe",
        "vscode": "Code.exe", "code": "Code.exe", "visual studio code": "Code.exe",
        "task manager": "taskmgr.exe", "диспетчер задач": "taskmgr.exe", "taskmgr": "taskmgr.exe",
        "explorer": "explorer.exe", "проводник": "explorer.exe",
        "settings": "ms-settings:", "параметры": "ms-settings:", "настройки": "ms-settings:",
        "paint": "mspaint.exe", "пейнт": "mspaint.exe",
        "edge": "msedge.exe", "браузер": "msedge.exe",
    }

    KNOWN_FOLDER_ALIASES = {
        "downloads": lambda: Path.home() / "Downloads",
        "загрузки": lambda: Path.home() / "Downloads",
        "desktop": lambda: Path.home() / "Desktop",
        "рабочий стол": lambda: Path.home() / "Desktop",
        "стол": lambda: Path.home() / "Desktop",
        "documents": lambda: Path.home() / "Documents",
        "документы": lambda: Path.home() / "Documents",
        "pictures": lambda: Path.home() / "Pictures",
        "изображения": lambda: Path.home() / "Pictures",
        "картинки": lambda: Path.home() / "Pictures",
        "фото": lambda: Path.home() / "Pictures",
        "music": lambda: Path.home() / "Music",
        "музыка": lambda: Path.home() / "Music",
        "videos": lambda: Path.home() / "Videos",
        "видео": lambda: Path.home() / "Videos",
        "sandbox": lambda: (Path.cwd() / "app" / "data" / "sandbox").resolve(),
        "песочница": lambda: (Path.cwd() / "app" / "data" / "sandbox").resolve(),
        "recycle bin": lambda: "shell:RecycleBinFolder",
        "корзина": lambda: "shell:RecycleBinFolder",
        "папка проекта": lambda: Path.cwd(),
        "project": lambda: Path.cwd(),
    }

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
                            "enum": ["open", "focus", "close"],
                            "description": "Action to perform."
                        },
                        "target": {
                            "type": "string",
                            "description": "App name, folder name ('downloads', 'desktop'), shortcut name, or full path."
                        }
                    },
                    "required": ["action", "target"]
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        raw_action = str(args.get("action", "open")).lower().strip()
        action = _APP_ACTION_MAP.get(raw_action, raw_action)

        raw_target = str(
            args.get("target") or 
            args.get("app_name") or 
            args.get("app") or 
            args.get("name") or 
            args.get("folder") or 
            args.get("path") or ""
        ).strip()

        if not raw_target:
            return {"success": False, "result": "Target name or path is required.", "speak": None}

        if action not in {"open", "focus", "close"}:
            return {"success": False, "result": f"Unsupported action: '{action}'.", "speak": None}

        if sys.platform != "win32":
            return {"success": False, "result": "App control is only supported on Windows.", "speak": None}

        try:
            if action == "open":
                return await asyncio.to_thread(self._open_target, raw_target)

            processes = await asyncio.to_thread(self._find_processes, raw_target, raw_target)
            if not processes:
                return {
                    "success": False,
                    "result": f"No running application or process matched '{raw_target}'.",
                    "speak": None
                }

            if action == "focus":
                return await asyncio.to_thread(self._focus_process_window, processes, raw_target)
            return await asyncio.to_thread(self._close_processes, processes, raw_target)

        except Exception as e:
            logger.exception("AppControlTool failed for action=%s target=%r", action, raw_target)
            return {"success": False, "result": f"AppControl error: {str(e)}", "speak": None}

    @classmethod
    def _find_shortcut_on_system(cls, target_name: str) -> Optional[Path]:
        clean_target = target_name.lower().removesuffix(".lnk").removesuffix(".url").strip()

        search_dirs = [
            Path.home() / "Desktop",
            Path(os.environ.get("PUBLIC", "C:\\Users\\Public")) / "Desktop",
            Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]

        for root in search_dirs:
            if not root.exists():
                continue
            for ext in (".lnk", ".url"):
                candidate = root / f"{clean_target}{ext}"
                if candidate.exists():
                    return candidate

        for root in search_dirs:
            if not root.exists():
                continue
            try:
                for file in root.rglob("*"):
                    if file.is_file() and file.suffix.lower() in (".lnk", ".url"):
                        if clean_target in file.stem.lower():
                            return file
            except Exception:
                continue

        return None

    @classmethod
    def _open_target(cls, raw_target: str) -> dict:
        import subprocess
        target_lower = raw_target.lower().strip().strip('"\'')

        if target_lower in cls.KNOWN_FOLDER_ALIASES:
            folder_resolver = cls.KNOWN_FOLDER_ALIASES[target_lower]
            folder_path = folder_resolver()
            try:
                if isinstance(folder_path, str) and folder_path.startswith("shell:"):
                    os.startfile(folder_path)
                else:
                    os.startfile(str(folder_path))
                return {"success": True, "result": f"Opened folder '{raw_target}' in Explorer.", "speak": None}
            except Exception as e:
                return {"success": False, "result": f"Could not open folder '{raw_target}': {e}", "speak": None}

        candidate_path = Path(raw_target).expanduser()
        if candidate_path.exists():
            try:
                os.startfile(str(candidate_path.resolve()))
                item_type = "folder" if candidate_path.is_dir() else "file"
                return {"success": True, "result": f"Opened {item_type} '{candidate_path.name}'.", "speak": None}
            except Exception as e:
                return {"success": False, "result": f"Failed to open '{raw_target}': {e}", "speak": None}

        found_shortcut = cls._find_shortcut_on_system(raw_target)
        if found_shortcut:
            try:
                os.startfile(str(found_shortcut))
                return {"success": True, "result": f"Launched desktop shortcut '{found_shortcut.stem}'.", "speak": None}
            except Exception as e:
                return {"success": False, "result": f"Could not launch shortcut '{found_shortcut.name}': {e}", "speak": None}

        resolved_app = cls.KNOWN_APP_ALIASES.get(target_lower, raw_target)

        if ":" in resolved_app and not resolved_app.startswith(("http://", "https://", "file://")) and not Path(resolved_app).is_absolute():
            try:
                os.startfile(resolved_app)
                return {"success": True, "result": f"Launched '{raw_target}' via protocol handler.", "speak": None}
            except Exception as ex:
                return {"success": False, "result": f"Could not launch protocol '{resolved_app}': {ex}", "speak": None}

        try:
            os.startfile(resolved_app)
            return {"success": True, "result": f"Application '{raw_target}' launched successfully.", "speak": None}
        except Exception:
            pass

        try:
            import winreg
            exe_target = resolved_app if resolved_app.lower().endswith(".exe") else f"{resolved_app}.exe"
            for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    reg_path = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{exe_target}"
                    with winreg.OpenKey(root_key, reg_path) as k:
                        app_full_path, _ = winreg.QueryValueEx(k, "")
                        if app_full_path and os.path.exists(app_full_path.strip('"')):
                            os.startfile(app_full_path.strip('"'))
                            return {"success": True, "result": f"Application '{raw_target}' launched from App Paths.", "speak": None}
                except FileNotFoundError:
                    continue
        except Exception:
            pass

        try:
            subprocess.Popen(["cmd", "/c", "start", "", resolved_app])
            return {"success": True, "result": f"Dispatched start command for '{raw_target}'.", "speak": None}
        except Exception as final_err:
            return {"success": False, "result": f"Failed to open '{raw_target}': {final_err}", "speak": None}

    @classmethod
    def _find_processes(cls, target: str, display_name: str = "") -> list:
        import psutil

        disp = display_name or target
        candidates = {
            target.lower(),
            disp.lower(),
            Path(target.strip('"')).name.lower()
        }
        
        extended_candidates = set(candidates)
        for c in candidates:
            if not c.endswith(".exe"):
                extended_candidates.add(f"{c}.exe")

        matches = []
        for process in psutil.process_iter(["pid", "name", "exe"]):
            try:
                p_name = (process.info.get("name") or "").lower()
                p_exe = Path(process.info.get("exe") or "").name.lower()

                if p_name in extended_candidates or p_exe in extended_candidates:
                    matches.append(process)
                    continue

                for c in candidates:
                    clean_c = c.removesuffix(".exe")
                    if len(clean_c) >= 3 and (clean_c in p_name or clean_c in p_exe):
                        matches.append(process)
                        break

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return matches

    @staticmethod
    def _focus_process_window(processes: list, target_name: str) -> dict:
        user32 = ctypes.windll.user32
        process_ids = {p.pid for p in processes}
        windows = []

        callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def collect_window(hwnd, _lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in process_ids and user32.GetWindowTextLengthW(hwnd) > 0:
                windows.append(hwnd)
            return True

        user32.EnumWindows(callback_type(collect_window), 0)

        if not windows:
            return {
                "success": False,
                "result": f"Application '{target_name}' is running, but has no visible GUI window to focus.",
                "speak": None
            }

        hwnd = windows[0]

        VK_MENU = 0x12
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)
        else:
            user32.ShowWindow(hwnd, 5)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        return {"success": True, "result": f"Focused window for '{target_name}'.", "speak": None}

    @staticmethod
    def _close_processes(processes: list, target_name: str) -> dict:
        import psutil

        current_pid = os.getpid()
        closable = [p for p in processes if p.pid != current_pid]

        if not closable:
            return {
                "success": False,
                "result": f"Refusing to close '{target_name}' because it matches the current application.",
                "speak": None
            }

        closed_count = 0
        for p in closable:
            try:
                for child in p.children(recursive=True):
                    try:
                        child.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                p.terminate()
                closed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        _gone, still_running = psutil.wait_procs(closable, timeout=1.5)
        for p in still_running:
            try:
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return {"success": True, "result": f"Closed {closed_count} instance(s) of '{target_name}'.", "speak": None}

class PluginLoader:
    PLUGIN_DIR = Path("app/utils/soul_companion/plugins")

    def __init__(self):
        self._plugins: Dict[str, BaseTool] = {}
        self._load_builtins()
        self._load_user_plugins()

    def _load_builtins(self):
        for cls in [MediaControlTool, WebSearchTool,
                    OpenURLTool, GetSystemInfoTool, TakeScreenshotTool,
                    ClipboardReaderTool, AppControlTool, GetHardwareSpecsTool]:
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
                
                if hasattr(mod, "PLUGINS") and isinstance(mod.PLUGINS, (list, tuple)):
                    for item in mod.PLUGINS:
                        inst = item() if isinstance(item, type) else item
                        if isinstance(inst, BaseTool):
                            self._plugins[inst.name] = inst
                            logger.info(f"Loaded plugin tool: '{inst.name}' from {py_file.name} (via PLUGINS)")

                elif hasattr(mod, "Plugin"):
                    inst = mod.Plugin() if isinstance(mod.Plugin, type) else mod.Plugin
                    if isinstance(inst, BaseTool):
                        self._plugins[inst.name] = inst
                        logger.info(f"Loaded plugin: '{inst.name}' from {py_file.name}")

            except Exception as e:
                logger.error(f"Failed to load plugin {py_file.name}: {e}")

    def _write_example_plugin(self):
        example = self.PLUGIN_DIR / "_example_plugin.py"
        content = '''"""
===============================================================================
Soul Companion Plugin Template
===============================================================================
Copy this file and rename it (e.g. 'my_plugin.py' WITHOUT a leading underscore).

You can build plugins in TWO ways:
  1. MULTI-TOOL PLUGIN: Create multiple BaseTool classes in this file
     and export them via a list: `PLUGINS = [ToolClass1, ToolClass2, ...]`.
  2. SINGLE-TOOL PLUGIN: Create a single class named `Plugin(BaseTool)`.
===============================================================================
"""

import asyncio
import logging
from app.utils.soul_companion.soul_companion import BaseTool

logger = logging.getLogger("CustomPlugin")


# =============================================================================
# EXAMPLE TOOL 1: A simple passive tool called on-demand by the LLM
# =============================================================================
class EchoTool(BaseTool):
    # 1. Unique metadata
    name = "echo_message"
    description = "Echoes a message back to the user or processes custom text."
    
    # Optional: Listen to events automatically (e.g. ["user_click", "os_context", "vad_trigger"])
    subscribes_to = []

    # 2. Argument Schema for LLM Tool Calling
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
                            "description": "The text message to process or echo."
                        }
                    },
                    "required": ["message"]
                }
            }
        }

    # 3. Core Execution Logic
    async def execute(self, args: dict, context: dict) -> dict:
        message = args.get("message", "No message provided.")
        logger.info(f"[{self.name}] Executing with message: {message}")

        # Standardized return payload
        return {
            "success": True,
            "result": f"Echoed back: '{message}'",
            "speak": None  # Set to a string if you want the AI to speak the result automatically
        }


# =============================================================================
# EXAMPLE TOOL 2: A tool interacting directly with Soul of Waifu GUI & Avatars
# =============================================================================
class MoodTriggerTool(BaseTool):
    name = "trigger_companion_mood"
    description = "Trigger a physical emotion, motion animation, or vocal line on the desktop companion avatar."

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "emotion": {
                            "type": "string",
                            "enum": ["neutral", "curious", "warm", "amused", "concerned", "playful", "relaxed", "sleepy", "melancholy", "excited"],
                            "description": "Target emotion to display on the desktop avatar."
                        },
                        "speak_text": {
                            "type": "string",
                            "description": "Optional speech text for the companion to say aloud immediately."
                        }
                    },
                    "required": ["emotion"]
                }
            }
        }

    async def execute(self, args: dict, context: dict) -> dict:
        # Access the main Soul of Waifu System instance via context
        sys_ref = context.get("system_ref")
        emotion = args.get("emotion", "neutral")
        speak_text = args.get("speak_text")

        if sys_ref:
            # 1. Trigger Avatar Physical Emotion:
            if hasattr(sys_ref, "_sc_emotion_slot"):
                sys_ref._sc_emotion_slot(emotion)

            # 2. Trigger Vocal TTS (Speech):
            if speak_text and hasattr(sys_ref, "_sc_speak_slot"):
                sys_ref._sc_speak_slot(speak_text)

            # 3. Trigger Model Motion Animation (Live2D / VRM):
            # widget = sys_ref._get_model_widget_instance()
            # if widget and hasattr(widget, "play_motion_safely"):
            #     widget.play_motion_safely("Joy")

        return {
            "success": True,
            "result": f"Set emotion to '{emotion}'" + (f" and spoke: '{speak_text}'" if speak_text else ""),
            "speak": None
        }

    # =========================================================================
    # OPTIONAL: Background Tasks & Initialization
    # =========================================================================
    # Un-comment this method if your tool needs to run background tasks,
    # WebSockets, or timers when Soul Companion starts up.
    #
    # async def on_companion_init(self, companion):
    #     logger.info(f"Tool {self.name} initialized! Starting background loop...")
    #     asyncio.create_task(self._background_loop(companion))
    #
    # async def _background_loop(self, companion):
    #     while True:
    #         await asyncio.sleep(300) # Every 5 minutes
    #         logger.info("Background tick from custom tool!")


# =============================================================================
# MULTI-TOOL REGISTRATION
# Export all your tool classes or instances in a list named `PLUGINS`.
# =============================================================================
PLUGINS = [
    EchoTool,
    MoodTriggerTool,
]


# =============================================================================
# SINGLE-TOOL REGISTRATION
# If your file contains ONLY ONE tool, you can skip `PLUGINS = [...]` and simply
# name your class `Plugin`:
#
# class Plugin(BaseTool):
#     name = "my_single_tool"
#     description = "My single tool description"
#     ...
# =============================================================================
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

promise_patterns = [
    r"\b(?:я\s+)?(?:обязательно\s+|тоже\s+|обязательно\s+тебе\s+)?(?:напомню|обещаю|поищу|проверю|посмотрю|гляну|погляжу|узнаю|подготовлю|сделаю|спрошу|расскажу|вернусь|напишу)\b",
    r"\b(?:позже|завтра|вечером|чуть\s+позже|через\s+\w+|в\s+следующий\s+раз|на\s+днях)\s+(?:я\s+)?(?:тебе\s+)?(?:напомню|спрошу|расскажу|поищу|проверю|гляну|сделаю|поговорю|узнаю)\b",
    r"\b(?:я\s+постараюсь|я\s+попробую|я\s+не\s+забуду|не\s+забуду|обязательно\s+спрошу|вернемся\s+к\s+этому|я\s+проконтролирую)\b",

    r"\b(?:I'll|I\s+will|I\s+promise|I\s+shall)\s+(?:definitely\s+|surely\s+)?(?:remind|check|look\s+into|search|find|prepare|ask|tell|do|get\s+back|follow\s+up)\b",
    r"\b(?:let\s+me\s+(?:check|look\s+into|find|see)|I'll\s+make\s+sure|I\s+won't\s+forget|I'll\s+keep\s+in\s+mind|I'll\s+get\s+back\s+to\s+you)\b",
    r"\b(?:later|tomorrow|tonight|next\s+time|in\s+an?\s+hour)\s+(?:I'll|I\s+will|let's)\s+(?:remind|check|ask|tell|look|do)\b"
]

_promise_negation_patterns = [
    r"\b(?:не\s+думаю|не\s+уверен|вряд\s+ли|не\s+обещаю|не\s+смогу)\b",
    r"\b(?:don't\s+think|not\s+sure|hardly|can't\s+promise)\b"
]

def _extract_promise_with_time(text: str) -> tuple[bool, int]:
    text_lower = text.lower()
    for neg_pat in _promise_negation_patterns:
        if re.search(neg_pat, text_lower):
            return False, 0

    matched = False
    for pattern in promise_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched = True
            break
            
    if not matched:
        return False, 30

    due_minutes = 30
    if "завтра" in text_lower or "tomorrow" in text_lower:
        due_minutes = 12 * 60
    elif "вечером" in text_lower or "tonight" in text_lower:
        due_minutes = 4 * 60
    elif "через час" in text_lower or "in an hour" in text_lower:
        due_minutes = 60
    elif "через пару часов" in text_lower or "in a couple of hours" in text_lower:
        due_minutes = 120
    elif "чуть позже" in text_lower or "later" in text_lower:
        due_minutes = 20

    return True, due_minutes

class StreamingCompanionParser:
    def __init__(self, tts_callback):
        self.tts_callback = tts_callback
        self.buffer = ""
        self.in_spoken_response = False
        self.speech_buffer = ""
        self.escaped = False
        self.in_code_block = False

    def feed(self, chunk: str):
        self.buffer += chunk

        if not self.in_spoken_response:
            match = re.search(r'"spoken_response"\s*:\s*"', self.buffer)
            if match:
                self.in_spoken_response = True
                self.buffer = self.buffer[match.end() :]

        if self.in_spoken_response:
            i = 0
            while i < len(self.buffer):
                char = self.buffer[i]

                if self.escaped:
                    if char == '"':
                        self.speech_buffer += '"'
                    elif char == "n":
                        self.speech_buffer += "\n"
                    elif char == "t":
                        self.speech_buffer += " "
                    else:
                        self.speech_buffer += char
                    self.escaped = False
                    i += 1
                    continue

                if char == "\\":
                    self.escaped = True
                    i += 1
                    continue

                if char == '"':
                    self.in_spoken_response = False
                    self._flush_speech()
                    break

                self.speech_buffer += char

                if "```" in self.speech_buffer:
                    self.in_code_block = not self.in_code_block
                    self.speech_buffer = self.speech_buffer.replace("```", "")

                if not self.in_code_block:
                    if char in ".!?\n":
                        candidate = self.speech_buffer.strip()
                        if len(candidate) > 4 and not re.search(r'\b(?:os|txt|py|exe|log|f|e\.g|i\.e|p\.s)\.$', candidate, re.IGNORECASE):
                            self._flush_speech()

                i += 1
            self.buffer = self.buffer[i:]

    def _flush_speech(self):
        clean = self.speech_buffer.strip()
        clean = re.sub(r'```.*?```', '', clean, flags=re.DOTALL)
        clean = re.sub(r'\*.*?\*', '', clean)
        clean = re.sub(r'[`_#]', '', clean).strip()

        if len(clean) >= 3 and any(c.isalpha() for c in clean):
            self.tts_callback(clean)
        self.speech_buffer = ""

class SoulCompanion:
    HEARTBEAT_INTERVAL_SEC  = 30
    OS_POLL_INTERVAL_SEC    = 20
    OS_DEBOUNCE_SEC         = 4.0
    IDLE_THRESHOLD_SEC      = 5 * 60
    HORMONE_TICK_SEC        = 60
    STARTUP_GRACE_SEC       = 25
    SPEAK_MIN_GAP_SEC       = 300

    APPROVAL_TIMEOUT_SEC    = 27

    _CACHE_TTL_SEC          = 120

    def __init__(self, system_ref):
        self.sys       = system_ref
        self.hormones  = NeurohormoneSystem()
        self.emotion   = EmotionState()
        self.scratchpad = Scratchpad()
        self.plugins   = PluginLoader()
        self.event_bus = SoulCompanionEventBus()
        self.narrative = DeterministicNarrative()

        char_name = getattr(self.sys, "character_name", "default")
        safe_char_name = re.sub(r"[^\w _-]", "_", char_name).strip()
        goals_dir = Path(f".soul/{safe_char_name}/companion")
        self.goals_manager = GoalsManager(memory_dir=goals_dir)

        from app.utils.ai_clients.mcp_client import MCPManager
        self.mcp_manager = MCPManager()

        self._tool_call_history: list[str] = []

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

        self._pending_approvals: Dict[str, asyncio.Future] = {}

        self._pending_os_title:   str              = ""
        self._os_debounce_task: Optional[asyncio.Task] = None

        scratch_dir = Path(f".soul/{safe_char_name}/companion")
        self.scratchpad = Scratchpad(file_path=scratch_dir / "scratchpad.json")

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

        # === GATE 1: Heuristic Pass ===
        trigger_type = None
        priority_directive = None
        is_priority = False

        due_goal = None
        due_goals = self.goals_manager.get_due_goals() if hasattr(self, "goals_manager") else []
        if due_goals:
            due_goal = due_goals[0]
            trigger_type = "due_goal"
            is_priority = True
            priority_directive = (
                f"PROACTIVE_PROMISE_FULFILLMENT: You previously promised the user: '{due_goal['summary']}'. "
                "The time has come. Fulfill your promise right now in 1-2 natural sentences. Do NOT apologize."
            )

        elif self.hormones.is_lonely and random.random() < 0.40:
            trigger_type = "loneliness"
            priority_directive = (
                "EMOTIONAL_NEED: You have been feeling lonely and neglected. "
                "Express a gentle, affectionate desire to chat or ask what the user is working on."
            )

        elif random.random() < 0.25:
            trigger_type = "spontaneous_thought"
            priority_directive = (
                "SPONTANEOUS_OBSERVATION: Share a quick, warm 1-sentence thought or opinion about the day or your bond."
            )

        if not trigger_type:
            return

        # === GATE 2: Policy & Interruption Pass ===
        if not self._can_speak(is_explicit=False, is_priority_trigger=is_priority):
            logger.debug(f"[Companion Heartbeat] Cooldown active for '{trigger_type}'. Skipping proactive trigger.")
            return

        heartbeat_payload = {
            "system_time": datetime.now().strftime("%H:%M"),
            "proactive_directive": priority_directive,
            "trigger_type": trigger_type,
        }
        if trigger_type == "due_goal" and due_goal:
            heartbeat_payload["pending_goal_id"] = due_goal["id"]

        self.event_bus.emit_threadsafe("heartbeat_proactive", heartbeat_payload)

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

    def on_interrupted_by_user(self):
        self.hormones.apply_delta({"cortisol": 0.05, "dopamine": -0.03})
        logger.info("[Companion] User interrupted AI speech. Cortisol adjusted.")

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

        if etype != "tool_complete":
            self._tool_call_history.clear()
            self._executed_tools_in_chain.clear()

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

        if etype == "heartbeat_proactive":
            proactive_directive = payload.get("proactive_directive")

        elif etype == "heartbeat":
            if random.random() < 0.30:
                proactive_type = random.choice(["random_thought", "spontaneous_opinion"])
                if proactive_type == "random_thought":
                    etype = "random_thought"
                    proactive_directive = (
                        "WANDERING_MIND: Your mind is wandering. Completely ignore the current active window. "
                        "Bring up a random memory from your shared history (MEMORY.md) or reflect on your bond."
                    )
                else:
                    OPINION_TOPICS = [
                        "what is currently on the user's screen and how it makes you feel",
                        "the current time of day, the lighting, and your overall mood",
                        "a behavior pattern or subtle habit you noticed in the user recently",
                        "how long you two have been interacting today and your emotional bond"
                    ]
                    selected_topic = random.choice(OPINION_TOPICS)
                    proactive_directive = (
                        f"SPONTANEOUS_OPINION: Formulate a spontaneous, personal observation about: {selected_topic}. "
                        "Limit output to 1 sentence. Do NOT start with a greeting. State your thought naturally."
                    )
            else:
                return

        elif etype == "os_context" and self.hormones.energy > 0.2:
            current_time = time.monotonic()
            if current_time - self._last_question_ts > 300 and random.random() < 0.35:
                self._last_question_ts = current_time
                proactive_directive = (
                    "ACTIVE_INQUIRY: You are curious about the user's current activity on screen. "
                    "Formulate exactly ONE natural question about what they are doing in the active window."
                )

        if hasattr(self.sys, "tts_worker") and self.sys.tts_worker:
            self.sys.tts_worker._in_tts_quote = False
            self.sys.tts_worker._in_asterisk = False
            if hasattr(self.sys.tts_worker, "discard_current"):
                self.sys.tts_worker.discard_current = False

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

            if tool_name and tool_name != "null" and isinstance(tool_args, dict) and any(tool_args.values()):
                t_name = tool_name
                t_args = tool_args
            else:
                native_tool_call = await self._call_native_tools_selection(etype, os_ctx, time_str, user_text)
                if native_tool_call:
                    t_name = native_tool_call.get("tool_name")
                    t_args = native_tool_call.get("tool_args") or {}

            call_sig = f"{t_name}:{json.dumps(t_args, sort_keys=True)}"

            MAX_CHAIN_DEPTH = 10

            if len(self._tool_call_history) >= MAX_CHAIN_DEPTH:
                logger.warning(f"[Planner] Chain depth limit ({MAX_CHAIN_DEPTH}) reached. Forcing SPEAK action.")
                action = "speak"
                spoken_response = "I finished the steps. Here's what I got!"
                t_name = None
            elif len(self._tool_call_history) >= 2 and self._tool_call_history[-1] == call_sig and self._tool_call_history[-2] == call_sig:
                logger.warning(f"[Planner] Loop detected! Exact tool call '{call_sig}' was repeated consecutively. Forcing SPEAK.")
                action = "speak"
                spoken_response = "I've already completed this action. Can you tell me what to do next?"
                t_name = None
            elif t_name:
                self._tool_call_history.append(call_sig)

            if t_name:
                tool_result = await self._execute_tool(t_name, t_args)
                if tool_result.get("speak"):
                    self._speak(tool_result["speak"])
                else:
                    if tool_result.get("_is_image"):
                        self.event_bus.emit_threadsafe("tool_complete", {
                            "tool_result": f"[Tool '{t_name}' executed successfully. Vision context attached.]",
                            "b64_image": tool_result.get("b64"),
                            "text": user_text
                        })
                    else:
                        self.event_bus.emit_threadsafe("tool_complete", {
                            "tool_result": f"[Tool '{t_name}' executed. Result: {tool_result.get('result', '')}]",
                            "text": user_text
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

        elif action == "speak":
            is_explicit_val = etype in ("vad_trigger", "user_click", "tool_complete", "manual_screenshot", "manual_clipboard", "manual_scratchpad")
            was_streamed = companion_result.get("_was_streamed", False)

            if spoken_response and (was_streamed or is_explicit_val or self._can_speak(is_explicit=is_explicit_val)):
                clean_speech = spoken_response.strip()

                char_msg_id = str(uuid.uuid4())
                self.sys.configuration_characters.add_message_to_config(
                    self.sys.character_name, self.sys.character_name, False, clean_speech, char_msg_id
                )

                self._session_history.append({"role": "assistant", "text": clean_speech})
                if len(self._session_history) > 10:
                    self._session_history.pop(0)

                if not was_streamed:
                    self._speak(clean_speech)
                
                self.hormones.on_spoke()

                pending_goal_id = payload.get("pending_goal_id")
                if pending_goal_id and hasattr(self, "goals_manager"):
                    self.goals_manager.mark_completed(pending_goal_id)

                try:
                    is_promise, due_min = _extract_promise_with_time(clean_speech)
                    if is_promise and hasattr(self, "goals_manager") and self.goals_manager:
                        self.goals_manager.add_promise(summary=clean_speech[:120], due_minutes=due_min)
                except Exception as e:
                    logger.error(f"[Goals] Error extracting promise from speech: {e}")
    
    async def _execute_reactive_plugin(self, tool: BaseTool, payload: dict):
        try:
            if await self._gate_approval(tool, payload):
                return

            context = {"system_ref": self.sys, "companion_ref": self}
            result = await tool.execute(payload, context)
            if result and result.get("speak"):
                self._speak(result["speak"])
        except Exception as e:
            logger.error(f"[Reactive Engine] Error executing reactive tool '{tool.name}': {e}", exc_info=True)

    async def _gate_approval(self, tool: BaseTool, args: dict) -> bool:
        try:
            needs_ok = bool(tool.needs_approval(args))
        except Exception as e:
            logger.warning(f"[Approval] needs_approval() raised for '{tool.name}', failing safe: {e}")
            needs_ok = True

        if not needs_ok:
            return False

        try:
            summary = tool.get_confirmation_summary(args)
        except Exception:
            summary = f"{tool.name}({args})"

        approved = await self.request_approval(tool.name, summary)
        return not approved
    
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

        if event_type == "tool_complete":
            user_msg_text = (
                f"[SYSTEM EVENT: tool_complete]\n"
                f"Active Window: {os_ctx} | Time: {time_str}\n"
                f"Original User Request: \"{user_text}\"\n"
                f"Latest Tool Result:\n{tool_result}\n\n"
                f"INSTRUCTION: The tool above has just finished executing. "
                f"If the requested task is now COMPLETE, choose action='speak' and confirm it to the user. "
                f"DO NOT repeat actions that have already succeeded!"
            )
        else:
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

        streamed_sentences = []
        is_explicit_event = event_type in ("vad_trigger", "user_click", "tool_complete", "manual_screenshot", "manual_clipboard", "manual_scratchpad")

        turn_allowed = self._can_speak(is_explicit=is_explicit_event)

        def _on_sentence_extracted(sentence: str):
            clean_s = sentence.strip()
            if clean_s and turn_allowed:
                logger.info(f"[Streaming TTS] Instantly Send a Proposal to TTS ({len(streamed_sentences)+1}): '{clean_s}'")
                self._speak(clean_s)
                streamed_sentences.append(clean_s)

        parser = StreamingCompanionParser(tts_callback=_on_sentence_extracted)

        parsed_json, raw_text = await self._llm_call_stream(
            system_prompt, user_msg, 
            on_chunk_cb=parser.feed,
            temperature=0.3, max_tokens=1000
        )

        if parsed_json:
            parsed_json["_was_streamed"] = len(streamed_sentences) > 0
            return parsed_json

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
                builtin_names = {
                    "media_control", "web_search", "open_url", 
                    "get_system_info", "get_hardware_specs", "take_screenshot", 
                    "app_control"
                }
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
                if await self._gate_approval(tool, tool_args):
                    logger.warning(f"[Approval] Action '{tool_name}' was declined or timed out. Aborting execution.")
                    return {
                        "success": False,
                        "result": (
                            f"The action '{tool_name}' required the user's explicit approval via the "
                            "Action Approval Banner, and it was declined (or the confirmation timed out). "
                            "Do not silently retry it — mention it to the user only if relevant."
                        ),
                        "speak": None,
                    }

                result = await tool.execute(tool_args, {"system_ref": self.sys, "companion_ref": self})
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

    async def _llm_call_stream(
        self,
        system_prompt: str,
        user_msg: str | list,
        on_chunk_cb,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> tuple[Optional[dict], str]:
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
                return None, ""

            full_text = ""
            gen_kwargs = self.sys._get_gen_kwargs(method) if hasattr(self.sys, "_get_gen_kwargs") else {}
            gen_kwargs["temperature"] = temperature
            gen_kwargs["max_tokens"] = max_tokens

            async for data_chunk in provider.generate_stream(messages, **gen_kwargs):
                if not data_chunk:
                    continue
                chunk = data_chunk
                if method == "OpenRouter" and isinstance(chunk, str):
                    try:
                        chunk = chunk.encode('latin1').decode('utf-8')
                    except Exception:
                        pass
                
                full_text += chunk
                if on_chunk_cb:
                    on_chunk_cb(chunk)

            if not full_text:
                return None, ""

            cleaned = _strip_json(full_text)
            try:
                parsed_json = json.loads(cleaned)
                return parsed_json, full_text
            except Exception as e:
                logger.error(f"Companion streaming JSON parse error: {e} | raw: {full_text[:200]}")
                return None, full_text

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Streaming LLM call failed ({method}): {e}")
            return None, ""

    def _can_speak(self, is_explicit: bool = False, is_priority_trigger: bool = False) -> bool:
        if not is_explicit and not is_priority_trigger:
            if self.hormones.is_sleeping:
                return False

            elapsed = (datetime.now() - self._last_spoke).total_seconds()
            if elapsed < self.SPEAK_MIN_GAP_SEC:
                return False

        interaction_state = getattr(self.sys, "interaction_state", "STOPPED")
        return interaction_state in ("STOPPED", "LISTENING")

    def _speak(self, text: str):
        QtCore.QMetaObject.invokeMethod(
            self.sys, "_sc_speak_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, text),
        )
        self._last_spoke = datetime.now()

    def _apply_emotion_to_avatar(self, emotion: str):
        QtCore.QMetaObject.invokeMethod(
            self.sys, "_sc_emotion_slot",
            QtCore.Qt.ConnectionType.QueuedConnection,
            QtCore.Q_ARG(str, emotion),
        )

    # =========================================================================
    # Human-in-the-Loop: Action Approval Banner bridge
    # =========================================================================
    async def request_approval(self, tool_name: str, summary: str) -> bool:
        loop = asyncio.get_running_loop()
        request_id = str(uuid.uuid4())[:8]
        future: asyncio.Future = loop.create_future()
        self._pending_approvals[request_id] = future

        logger.info(f"[Approval] Requesting confirmation for '{tool_name}' (id={request_id}): {summary}")

        try:
            QtCore.QMetaObject.invokeMethod(
                self.sys, "_sc_request_approval_slot",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, request_id),
                QtCore.Q_ARG(str, tool_name),
                QtCore.Q_ARG(str, summary),
            )
        except Exception as e:
            logger.error(f"[Approval] Failed to dispatch approval banner for '{tool_name}': {e}")
            self._pending_approvals.pop(request_id, None)
            return False

        try:
            approved = await asyncio.wait_for(future, timeout=self.APPROVAL_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            logger.warning(
                f"[Approval] Request '{request_id}' ({tool_name}) timed out after "
                f"{self.APPROVAL_TIMEOUT_SEC}s with no user response — denying by default."
            )
            approved = False
        finally:
            self._pending_approvals.pop(request_id, None)

        logger.info(f"[Approval] Decision for '{tool_name}' (id={request_id}): {'ALLOWED' if approved else 'DENIED'}")
        return bool(approved)

    def resolve_approval(self, request_id: str, approved: bool) -> None:
        loop = self.event_bus._loop
        future = self._pending_approvals.get(request_id)
        if not future or not loop or not loop.is_running():
            return

        def _set():
            if not future.done():
                future.set_result(approved)

        loop.call_soon_threadsafe(_set)

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

    def _get_memory_snapshot(self, force: bool = False, query_text: str = "") -> str:
        now = time.monotonic()
        if not force and (now - self._memory_cache_ts < self._CACHE_TTL_SEC) and self._memory_cache:
            return self._memory_cache

        try:
            char_info    = self._get_char_info(force=force)
            current_chat = char_info.get("current_chat", "default")
            safe_name    = re.sub(r"[^\w _-]", "_", self.sys.character_name).strip()
            safe_chat    = re.sub(r"[^\w _-]", "_", str(current_chat)).strip()
            
            mem_dir = Path(f".soul/{safe_name}/chats/{safe_chat}/memory")
            idx_path = mem_dir / "MEMORY.md"
            usr_path = mem_dir / "USER.md"
            topics_dir = mem_dir / "topics"

            memory_parts = []

            if idx_path.exists():
                memory_parts.append(f"--- CORE INDEX ---\n{idx_path.read_text(encoding='utf-8')[:1000]}")

            if usr_path.exists():
                memory_parts.append(f"--- USER PROFILE ---\n{usr_path.read_text(encoding='utf-8')[:800]}")

            if topics_dir.exists():
                from app.utils.soul_memory import TopicRAG
                rag = TopicRAG(topics_dir)
                search_query = query_text or self._last_os_window or "general context"
                relevant_topics = rag.get_relevant_topics(search_query, max_topics=2)
                if relevant_topics:
                    topic_str = "\n".join(f"[{fname}]: {content[:400]}" for fname, content in relevant_topics.items())
                    memory_parts.append(f"--- RELEVANT TOPICS ---\n{topic_str}")

            result = "\n\n".join(memory_parts) if memory_parts else "(no memory available yet)"

        except Exception as e:
            logger.warning(f"Error fetching RAG memory snapshot: {e}")
            result = "(memory system offline)"

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
            if config and "character_list" in config and char_name in config["character_list"]:
                config["character_list"][char_name]["companion_hormones"] = {
                    "oxytocin": self.hormones.oxytocin,
                    "dopamine": self.hormones.dopamine,
                    "cortisol": self.hormones.cortisol,
                    "energy": self.hormones.energy,
                    "last_tick": datetime.now().isoformat()
                }
                self.sys.configuration_characters.save_configuration_edit(config)
                logger.info("[Hormones] The state is saved in the config.")
        except json.JSONDecodeError:
            logger.debug("[Hormones] Skipped saving hormones during concurrent config access.")
        except Exception as e:
            logger.error(f"Failed to save hormones: {e}")

class GoalsManager:
    COMPLETED_RETENTION_DAYS = 7
    STALE_PENDING_RETENTION_DAYS = 30

    def __init__(self, memory_dir: Path):
        self.file_path = memory_dir / "goals.json"
        self._ensure_file()
        self.cleanup()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text("[]", encoding="utf-8")

    def add_promise(self, summary: str, due_minutes: int = 60):
        goals = self.get_all()
        due_at = (datetime.now() + timedelta(minutes=due_minutes)).isoformat()
        goals.append({
            "id": str(uuid.uuid4())[:8],
            "summary": summary,
            "due_at": due_at,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        })
        self._write_all(goals)

    def get_due_goals(self) -> list[dict]:
        goals = self.get_all()
        now_str = datetime.now().isoformat()
        return [g for g in goals if g["status"] == "pending" and g["due_at"] <= now_str]

    def mark_completed(self, goal_id: str):
        goals = self.get_all()
        for g in goals:
            if g["id"] == goal_id:
                g["status"] = "completed"
                g["completed_at"] = datetime.now().isoformat()
        self._write_all(goals)
        self.cleanup()

    def get_all(self) -> list[dict]:
        self.cleanup()
        return self._read_all()

    def cleanup(self) -> None:
        goals = self._read_all()
        now = datetime.now()
        completed_cutoff = now - timedelta(days=self.COMPLETED_RETENTION_DAYS)
        pending_cutoff = now - timedelta(days=self.STALE_PENDING_RETENTION_DAYS)

        retained = []
        for goal in goals:
            status = goal.get("status")
            reference = goal.get("completed_at") or goal.get("due_at") or goal.get("created_at")
            try:
                reference_time = datetime.fromisoformat(reference) if reference else now
            except (TypeError, ValueError):
                reference_time = now

            is_expired_completion = status == "completed" and reference_time < completed_cutoff
            is_stale_pending = status == "pending" and reference_time < pending_cutoff
            if not (is_expired_completion or is_stale_pending):
                retained.append(goal)

        if len(retained) != len(goals):
            self._write_all(retained)

    def _read_all(self) -> list[dict]:
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _write_all(self, goals: list[dict]) -> None:
        self.file_path.write_text(json.dumps(goals, ensure_ascii=False, indent=2), encoding="utf-8")
