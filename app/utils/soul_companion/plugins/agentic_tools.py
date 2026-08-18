from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.utils.soul_companion.soul_companion import BaseTool

logger = logging.getLogger("SoulCompanion.Agentic")

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_plan_json(raw: str) -> str:
    cleaned = _FENCE_RE.sub("", raw.strip()).strip()
    first, last = cleaned.find("["), cleaned.rfind("]")
    if first != -1 and last != -1 and last > first:
        return cleaned[first:last + 1]
    return cleaned

PROJECT_ROOT = Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) >= 5 else Path.cwd()
SANDBOX_DIR = (PROJECT_ROOT / "app" / "data" / "sandbox").resolve()

DOWNLOAD_WATCH_EXT_IN_PROGRESS = {".crdownload", ".part", ".tmp", ".download"}

_FOLDER_ALIASES = {
    "desktop": "Desktop", "рабочий стол": "Desktop", "стол": "Desktop",
    "downloads": "Downloads", "загрузки": "Downloads",
    "documents": "Documents", "документы": "Documents",
    "pictures": "Pictures", "изображения": "Pictures", "картинки": "Pictures",
    "sandbox": str(SANDBOX_DIR),
}

_CATEGORY_MAP = {
    ".png": "Images", ".jpg": "Images", ".jpeg": "Images", ".gif": "Images",
    ".webp": "Images", ".bmp": "Images", ".svg": "Images", ".ico": "Images",
    ".pdf": "Documents", ".docx": "Documents", ".doc": "Documents", ".txt": "Documents",
    ".xlsx": "Documents", ".xls": "Documents", ".pptx": "Documents", ".csv": "Documents",
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives", ".gz": "Archives",
    ".exe": "Installers", ".msi": "Installers",
    ".mp4": "Videos", ".mkv": "Videos", ".mov": "Videos", ".avi": "Videos", ".webm": "Videos",
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".ogg": "Audio",
}


def _resolve_friendly_folder(raw: str) -> Optional[Path]:
    raw = (raw or "").strip()
    if not raw:
        return Path.home() / "Desktop"

    key = raw.lower()
    if key in _FOLDER_ALIASES:
        mapped = _FOLDER_ALIASES[key]
        return Path(mapped) if os.path.isabs(mapped) else Path.home() / mapped

    candidate = Path(raw).expanduser()
    return candidate if candidate.is_absolute() else Path.home() / raw


def _is_protected_path(p: Path) -> bool:
    try:
        resolved = p.resolve()
    except Exception:
        return True

    if len(str(resolved)) <= 3 or resolved == resolved.parent:
        return True

    protected_roots = [
        Path(os.environ.get("SystemRoot", "C:\\Windows")),
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")),
        Path(os.environ.get("ProgramData", "C:\\ProgramData")),
        Path.home() / "AppData" / "Local" / "Microsoft",
        Path.home() / "AppData" / "Roaming" / "Microsoft",
    ]

    for prot in protected_roots:
        try:
            if resolved == prot or resolved.is_relative_to(prot):
                return True
        except (ValueError, AttributeError):
            continue

    return False


def _fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def _collect_vitals_sync() -> dict:
    out: dict = {"ts": datetime.now().isoformat()}
    try:
        import psutil

        out["cpu_percent"] = psutil.cpu_percent(interval=0.3)
        vm = psutil.virtual_memory()
        out["ram_used_pct"] = vm.percent
        out["ram_total"] = _fmt_bytes(vm.total)
        out["ram_free"] = _fmt_bytes(vm.available)

        try:
            du = psutil.disk_usage(str(Path.home().anchor or "/"))
            out["disk_free"] = _fmt_bytes(du.free)
            out["disk_total"] = _fmt_bytes(du.total)
            out["disk_used_pct"] = du.percent
        except Exception:
            pass

        batt = psutil.sensors_battery()
        if batt is not None:
            out["battery_pct"] = batt.percent
            out["battery_plugged"] = bool(batt.power_plugged)
        else:
            out["battery_pct"] = None

        out["process_count"] = len(psutil.pids())
        out["uptime_min"] = int((time.time() - psutil.boot_time()) / 60)
    except ImportError:
        out["error"] = "psutil not installed"

    gpu_info = None
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        name = name.decode() if isinstance(name, bytes) else name
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        gpu_info = {
            "name": name, "load_pct": util.gpu, "temp_c": temp,
            "vram_used": _fmt_bytes(mem.used), "vram_total": _fmt_bytes(mem.total),
        }
        pynvml.nvmlShutdown()
    except Exception:
        try:
            r = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=4,
            )
            if r.returncode == 0 and r.stdout.strip():
                name, load, temp, vram_u, vram_t = [x.strip() for x in r.stdout.strip().splitlines()[0].split(",")]
                gpu_info = {
                    "name": name, "load_pct": float(load), "temp_c": float(temp),
                    "vram_used": f"{vram_u}MB", "vram_total": f"{vram_t}MB",
                }
        except Exception:
            gpu_info = None

    out["gpu"] = gpu_info
    return out


def _format_vitals(v: dict) -> str:
    lines = []
    if "cpu_percent" in v:
        lines.append(f"CPU: {v['cpu_percent']:.0f}%")
    if "ram_used_pct" in v:
        lines.append(f"RAM: {v['ram_used_pct']:.0f}% used ({v.get('ram_free', '?')} free of {v.get('ram_total', '?')})")
    if v.get("disk_free"):
        lines.append(f"Disk: {v['disk_used_pct']:.0f}% used, {v['disk_free']} free")
    if v.get("battery_pct") is not None:
        plug = "plugged in" if v.get("battery_plugged") else "on battery"
        lines.append(f"Battery: {v['battery_pct']:.0f}% ({plug})")
    gpu = v.get("gpu")
    if gpu:
        lines.append(f"GPU: {gpu['name']} — {gpu['load_pct']:.0f}% load, {gpu['temp_c']:.0f}°C, "
                      f"VRAM {gpu['vram_used']}/{gpu['vram_total']}")
    if "uptime_min" in v:
        h, m = divmod(v["uptime_min"], 60)
        lines.append(f"System uptime: {h}h {m}m")
    if "process_count" in v:
        lines.append(f"Running processes: {v['process_count']}")
    return "\n".join(lines) if lines else "(vitals unavailable — psutil not installed)"


# =============================================================================
# 1. GUI Agent / Computer Use
# =============================================================================
class GUIActionTool(BaseTool):
    name = "gui_action"
    description = (
        "Low-level GUI/computer-use control: move & click mouse, type text, press hotkeys, scroll, or get cursor position.\n"
        "- click / double_click / right_click / move_mouse: requires x and y coordinates.\n"
        "- type_text: types text at current cursor location into active window.\n"
        "- hotkey: press key combo (e.g. 'ctrl+s', 'alt+tab', 'enter', 'esc').\n"
        "- scroll: scroll page up/down."
    )
    requires_approval = True

    ACTION_ALIASES = {
        "press_hotkey": "hotkey", "press_keys": "hotkey", "shortcut": "hotkey", "key": "hotkey",
        "type": "type_text", "write": "type_text", "input_text": "type_text", "send_keys": "type_text",
        "move": "move_mouse", "mouse_move": "move_mouse",
        "pos": "get_cursor_position", "cursor": "get_cursor_position", "get_cursor": "get_cursor_position",
        "wheel": "scroll"
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
                            "enum": ["click", "double_click", "right_click", "move_mouse",
                                     "type_text", "hotkey", "scroll", "get_cursor_position"],
                        },
                        "x": {"type": "integer", "description": "Screen X coordinate."},
                        "y": {"type": "integer", "description": "Screen Y coordinate."},
                        "text": {"type": "string", "description": "Text to type (for type_text)."},
                        "keys": {"type": "string", "description": "Hotkey combo, e.g. 'ctrl+s', 'ctrl+shift+esc', 'enter'."},
                        "scroll_amount": {"type": "integer", "description": "Scroll amount (positive=up, negative=down, e.g. -500)."},
                        "direction": {"type": "string", "enum": ["up", "down"], "description": "Optional scroll direction."},
                        "amount": {"type": "integer", "description": "Optional scroll amount."},
                    },
                    "required": ["action"],
                },
            },
        }

    def _normalize_action(self, raw_action: str) -> str:
        act = raw_action.lower().strip()
        return self.ACTION_ALIASES.get(act, act)

    def needs_approval(self, args: dict) -> bool:
        act = self._normalize_action(str(args.get("action", "")))
        return act != "get_cursor_position"

    def get_confirmation_summary(self, args: dict) -> str:
        act = self._normalize_action(str(args.get("action", "")))
        if act in ("click", "double_click", "right_click", "move_mouse"):
            return f"{act.replace('_', ' ').title()} at screen position ({args.get('x')}, {args.get('y')})"
        if act == "type_text":
            text = args.get("text") or args.get("message") or ""
            preview = str(text)[:60]
            return f"Type text on your keyboard: \"{preview}\""
        if act == "hotkey":
            keys = args.get("keys") or args.get("hotkey") or args.get("key") or ""
            return f"Press keyboard shortcut: {keys}"
        if act == "scroll":
            return "Scroll active window"
        return f"gui_action: {act}"

    @staticmethod
    def _type_text_reliably(text: str):
        time.sleep(0.14)

        if sys.platform != "win32":
            import pyautogui
            pyautogui.write(text, interval=0.01)
            return

        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        try:
            CF_UNICODETEXT = 13
            GMEM_MOVEABLE = 0x0002

            utf16_bytes = (text + '\0').encode('utf-16le')
            h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(utf16_bytes))
            if h_mem:
                p_mem = kernel32.GlobalLock(h_mem)
                ctypes.memmove(p_mem, utf16_bytes, len(utf16_bytes))
                kernel32.GlobalUnlock(h_mem)

                if user32.OpenClipboard(None):
                    user32.EmptyClipboard()
                    user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                    user32.CloseClipboard()

                    time.sleep(0.04)
                    VK_CONTROL = 0x11
                    VK_V = 0x56
                    user32.keybd_event(VK_CONTROL, 0, 0, 0)
                    user32.keybd_event(VK_V, 0, 0, 0)
                    user32.keybd_event(VK_V, 0, 2, 0)
                    user32.keybd_event(VK_CONTROL, 0, 2, 0)
                    return
        except Exception as e:
            logger.debug(f"[GUIAction] Win32 clipboard paste fallback: {e}")

        ULONG_PTR = ctypes.c_ulonglong if sys.maxsize > 2**32 else ctypes.c_ulong

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)
            ]

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR)
            ]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)
            ]

        class _INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("mi", MOUSEINPUT),
                ("ki", KEYBDINPUT),
                ("hi", HARDWAREINPUT)
            ]

        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", wintypes.DWORD),
                ("u", _INPUT_UNION)
            ]

        INPUT_KEYBOARD = 1
        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002

        for char in text:
            code = ord(char)
            if char in ('\n', '\r'):
                vk_enter = 0x0D
                inp_d = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk_enter, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)))
                inp_u = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=vk_enter, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                user32.SendInput(1, ctypes.byref(inp_d), ctypes.sizeof(INPUT))
                user32.SendInput(1, ctypes.byref(inp_u), ctypes.sizeof(INPUT))
            elif code <= 0xFFFF:
                inp_d = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)))
                inp_u = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                user32.SendInput(1, ctypes.byref(inp_d), ctypes.sizeof(INPUT))
                user32.SendInput(1, ctypes.byref(inp_u), ctypes.sizeof(INPUT))
            else:
                code -= 0x10000
                high = 0xD800 + (code >> 10)
                low = 0xDC00 + (code & 0x3FF)
                for part in (high, low):
                    inp_d = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=0, wScan=part, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)))
                    inp_u = INPUT(type=INPUT_KEYBOARD, u=_INPUT_UNION(ki=KEYBDINPUT(wVk=0, wScan=part, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)))
                    user32.SendInput(1, ctypes.byref(inp_d), ctypes.sizeof(INPUT))
                    user32.SendInput(1, ctypes.byref(inp_u), ctypes.sizeof(INPUT))
            time.sleep(0.003)

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            import pyautogui
        except ImportError:
            return {"success": False, "result": "pyautogui is not installed.", "speak": None}

        pyautogui.FAILSAFE = True
        action = self._normalize_action(str(args.get("action", "")))

        try:
            screen_w, screen_h = pyautogui.size()

            def _clamp(x, y):
                return max(0, min(int(x), screen_w - 1)), max(0, min(int(y), screen_h - 1))

            if action == "get_cursor_position":
                x, y = await asyncio.to_thread(pyautogui.position)
                return {"success": True, "result": f"Cursor is at ({x}, {y})", "speak": None}

            if action in ("click", "double_click", "right_click", "move_mouse"):
                if args.get("x") is None or args.get("y") is None:
                    return {"success": False, "result": f"'{action}' requires x and y.", "speak": None}
                x, y = _clamp(args["x"], args["y"])

                def _do():
                    if action == "click":
                        pyautogui.click(x, y)
                    elif action == "double_click":
                        pyautogui.doubleClick(x, y)
                    elif action == "right_click":
                        pyautogui.rightClick(x, y)
                    else:
                        pyautogui.moveTo(x, y, duration=0.15)

                await asyncio.to_thread(_do)
                return {"success": True, "result": f"{action} at ({x}, {y}) done.", "speak": None}

            if action == "type_text":
                text = str(args.get("text") or args.get("message") or "")
                if not text:
                    return {"success": False, "result": "No text provided.", "speak": None}

                await asyncio.to_thread(self._type_text_reliably, text)
                return {"success": True, "result": f"Typed {len(text)} characters into active window.", "speak": None}

            if action == "hotkey":
                keys_raw = str(args.get("keys") or args.get("hotkey") or args.get("key") or "").strip()
                if not keys_raw:
                    return {"success": False, "result": "No hotkey provided.", "speak": None}

                keys = [k.strip().lower() for k in re.split(r"[+, ]+", keys_raw) if k.strip()]
                KEY_MAP = {
                    "plus": "+", "esc": "escape", "ctrl": "ctrl", "control": "ctrl",
                    "alt": "alt", "shift": "shift", "enter": "enter", "return": "enter",
                    "tab": "tab", "space": "space", "backspace": "backspace",
                    "win": "win", "windows": "win", "cmd": "win"
                }
                mapped_keys = [KEY_MAP.get(k, k) for k in keys if k != "+"]
                if not mapped_keys and "+" in keys_raw:
                    mapped_keys = ["+"]

                time.sleep(0.08)
                await asyncio.to_thread(pyautogui.hotkey, *mapped_keys)
                return {"success": True, "result": f"Pressed hotkey: {'+'.join(mapped_keys)}", "speak": None}

            if action == "scroll":
                amount = args.get("scroll_amount")
                if amount is None:
                    raw_amount = int(args.get("amount", 400) or 400)
                    direction = str(args.get("direction", "down")).lower().strip()
                    amount = -abs(raw_amount) if direction == "down" else abs(raw_amount)
                else:
                    amount = int(amount)

                if amount == 0:
                    amount = -400

                await asyncio.to_thread(pyautogui.scroll, amount)
                return {"success": True, "result": f"Scrolled {amount} units.", "speak": None}

            return {"success": False, "result": f"Unknown gui_action: '{action}'.", "speak": None}

        except Exception as e:
            logger.exception("GUIActionTool failed")
            return {"success": False, "result": f"GUI action error: {e}", "speak": None}


# =============================================================================
# 2. Autonomous Web Browsing Agent (Playwright)
# =============================================================================
class BrowserAgentTool(BaseTool):
    name = "browse_web"
    description = (
        "Autonomous web browsing agent. 'read' opens a URL and extracts its visible text "
        "(use this for 'read this article', 'check the latest release notes at <url>', "
        "price/spec lookups, etc). 'click' and 'fill' interact with a page by the VISIBLE "
        "TEXT/label of the element. 'download' clicks a link/button and saves the resulting "
        "file. Prefer 'web_search' for open-ended queries and use 'browse_web' once you "
        "have a concrete URL to visit."
    )

    DOWNLOAD_DIR = SANDBOX_DIR / "downloads"

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["read", "click", "fill", "download"]},
                        "url": {"type": "string", "description": "Page to visit."},
                        "target_text": {"type": "string", "description": "Visible text/label of the link, button, or form field to act on."},
                        "value": {"type": "string", "description": "Text to type into the field (for 'fill')."},
                    },
                    "required": ["action", "url"],
                },
            },
        }

    def needs_approval(self, args: dict) -> bool:
        return str(args.get("action", "read")).lower().strip() in ("click", "fill", "download")

    def get_confirmation_summary(self, args: dict) -> str:
        action = str(args.get("action", "read")).lower().strip()
        url = args.get("url", "?")
        target = args.get("target_text", "")
        if action == "click":
            return f"Click '{target}' on {url}"
        if action == "fill":
            return f"Fill field '{target}' with '{str(args.get('value',''))[:40]}' on {url}"
        if action == "download":
            return f"Download the file behind '{target}' on {url}"
        return f"Open and read {url}"

    async def execute(self, args: dict, context: dict) -> dict:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "success": False,
                "result": "playwright is not installed. Run: pip install playwright && playwright install chromium",
                "speak": None,
            }

        action = str(args.get("action", "read")).lower().strip()
        url = str(args.get("url", "")).strip()
        target_text = str(args.get("target_text", "")).strip()
        value = str(args.get("value", "")).strip()

        if not url:
            return {"success": False, "result": "No URL provided.", "speak": None}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900},
                    locale="en-EN"
                )
                page = await context.new_page()
                try:
                    await page.goto(url, timeout=15000, wait_until="domcontentloaded")

                    if action == "read":
                        text = await page.inner_text("body")
                        text = re.sub(r"\n{3,}", "\n\n", text).strip()
                        title = await page.title()
                        return {
                            "success": True,
                            "result": f"Title: {title}\n\n{text[:2500]}",
                            "speak": None,
                        }

                    if action == "click":
                        if not target_text:
                            return {"success": False, "result": "click requires target_text.", "speak": None}
                        await page.get_by_text(target_text, exact=False).first.click(timeout=8000)
                        await page.wait_for_load_state("domcontentloaded", timeout=8000)
                        return {"success": True, "result": f"Clicked '{target_text}' on {url}.", "speak": None}

                    if action == "fill":
                        if not target_text:
                            return {"success": False, "result": "fill requires target_text (the field label).", "speak": None}
                        try:
                            locator = page.get_by_label(target_text, exact=False)
                            await locator.fill(value, timeout=8000)
                        except Exception:
                            locator = page.get_by_placeholder(target_text, exact=False)
                            await locator.fill(value, timeout=8000)
                        return {"success": True, "result": f"Filled '{target_text}' with '{value}' on {url}.", "speak": None}

                    if action == "download":
                        if not target_text:
                            return {"success": False, "result": "download requires target_text.", "speak": None}
                        self.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
                        async with page.expect_download(timeout=15000) as dl_info:
                            await page.get_by_text(target_text, exact=False).first.click()
                        download = await dl_info.value
                        dest = self.DOWNLOAD_DIR / download.suggested_filename
                        await download.save_as(str(dest))
                        return {"success": True, "result": f"Downloaded to {dest}", "speak": None}

                    return {"success": False, "result": f"Unknown browse_web action: '{action}'.", "speak": None}
                finally:
                    await browser.close()

        except Exception as e:
            logger.exception("BrowserAgentTool failed")
            return {"success": False, "result": f"Browser agent error: {e}", "speak": None}


# =============================================================================
# 3. Local Code Interpreter (Python / PowerShell)
# =============================================================================
class ExecuteCodeTool(BaseTool):
    name = "execute_code"
    description = (
        "Write and run a short Python or PowerShell script for a concrete, well-defined "
        "chore (batch-convert/compress files, sum a CSV column, init a git repo, rename a "
        "batch of files, etc). Runs sandboxed in a dedicated working folder with a timeout. "
        "Not for open-ended or long-running programs."
    )
    requires_approval = True

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string", "enum": ["python", "powershell"]},
                        "code": {"type": "string", "description": "The full script source."},
                        "timeout_seconds": {"type": "integer", "description": "Max runtime, default 20, hard cap 60."},
                    },
                    "required": ["language", "code"],
                },
            },
        }

    def get_confirmation_summary(self, args: dict) -> str:
        lang = args.get("language", "python")
        code_preview = str(args.get("code", "")).strip().replace("\n", " ⏎ ")[:180]
        return f"Run a {lang} script in the sandbox folder:\n\"{code_preview}\""

    async def execute(self, args: dict, context: dict) -> dict:
        language = str(args.get("language", "python")).lower().strip()
        code = args.get("code", "")
        timeout_s = min(max(int(args.get("timeout_seconds", 20) or 20), 1), 60)

        if not code.strip():
            return {"success": False, "result": "No code provided.", "speak": None}
        if language not in ("python", "powershell"):
            return {"success": False, "result": f"Unsupported language '{language}'.", "speak": None}
        if language == "powershell" and sys.platform != "win32":
            return {"success": False, "result": "PowerShell execution is only available on Windows.", "speak": None}

        try:
            SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {"success": False, "result": f"Could not prepare sandbox folder: {e}", "speak": None}

        suffix = ".py" if language == "python" else ".ps1"
        script_path = SANDBOX_DIR / f"_run_{uuid.uuid4().hex[:8]}{suffix}"

        try:
            script_path.write_text(code, encoding="utf-8")

            if language == "python":
                cmd = [sys.executable, str(script_path)]
            else:
                cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]

            def _run():
                return subprocess.run(
                    cmd, cwd=str(SANDBOX_DIR), capture_output=True, text=True, timeout=timeout_s
                )

            try:
                proc = await asyncio.to_thread(_run)
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "result": f"Script timed out after {timeout_s}s and was killed.",
                    "speak": None,
                }

            stdout = (proc.stdout or "").strip()[:1800]
            stderr = (proc.stderr or "").strip()[:600]
            ok = proc.returncode == 0

            result_text = f"[exit={proc.returncode}] Working dir: {SANDBOX_DIR}\nSTDOUT:\n{stdout or '(empty)'}"
            if stderr:
                result_text += f"\nSTDERR:\n{stderr}"

            return {"success": ok, "result": result_text, "speak": None}

        except Exception as e:
            logger.exception("ExecuteCodeTool failed")
            return {"success": False, "result": f"Execution error: {e}", "speak": None}
        finally:
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass


# =============================================================================
# 4. File Organizer & Local Search
# =============================================================================
class FileOrganizerTool(BaseTool):
    name = "file_organizer"
    description = (
        "Inspect, view contents, search, preview, or organize files and folders on the user's PC.\n"
        "- action='list': View all files, folders, and desktop shortcuts (.lnk/.url) inside a folder (e.g. 'desktop', 'downloads', 'documents').\n"
        "- action='search': Find specific files by name query across directories.\n"
        "- action='preview': Preview how files would be sorted into categories without moving them.\n"
        "- action='organize': Actually move files into neat category subfolders (requires user confirmation)."
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
                        "action": {
                            "type": "string",
                            "enum": ["list", "preview", "organize", "search"],
                            "description": "Action to perform."
                        },
                        "target_folder": {
                            "type": "string",
                            "description": "Folder name ('desktop', 'downloads', 'documents') or path. Defaults to 'desktop'.",
                        },
                        "query": {"type": "string", "description": "Filename substring to search for."},
                    },
                    "required": ["action"],
                },
            },
        }

    def needs_approval(self, args: dict) -> bool:
        return str(args.get("action", "")).lower().strip() == "organize"

    def get_confirmation_summary(self, args: dict) -> str:
        folder = args.get("target_folder") or args.get("folder") or args.get("path") or "Desktop"
        return f"Move files in '{folder}' into category subfolders"

    async def execute(self, args: dict, context: dict) -> dict:
        action = str(args.get("action", "list")).lower().strip()

        if action == "search":
            return await self._search(args)

        raw_folder = args.get("target_folder") or args.get("folder") or args.get("path") or args.get("target") or "desktop"
        folder = _resolve_friendly_folder(str(raw_folder))
        
        if not folder.exists() or not folder.is_dir():
            return {"success": False, "result": f"Folder not found: {folder}", "speak": None}
        if _is_protected_path(folder) and action == "organize":
            return {"success": False, "result": f"Refusing to organize protected system path: {folder}", "speak": None}

        if action == "list":
            return await asyncio.to_thread(self._list_sync, folder)

        return await asyncio.to_thread(self._organize_sync, folder, action == "organize")

    def _list_sync(self, folder: Path) -> dict:
        folders = []
        shortcuts = []
        files = []

        try:
            for item in folder.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    folders.append(f"📁 {item.name}/")
                elif item.suffix.lower() in (".lnk", ".url"):
                    shortcuts.append(f"🚀 {item.stem} (Shortcut)")
                else:
                    cat = _CATEGORY_MAP.get(item.suffix.lower(), "Other")
                    size_str = _fmt_bytes(item.stat().st_size) if item.is_file() else ""
                    files.append(f"📄 {item.name} [{cat}, {size_str}]")
        except Exception as e:
            return {"success": False, "result": f"Could not list directory {folder}: {e}", "speak": None}

        out = [f"=== Contents of '{folder.name}' ({folder}) ==="]
        if shortcuts:
            out.append("SHORTCUTS & APPLICATIONS:\n" + "\n".join(f"  {s}" for s in sorted(shortcuts)))
        if folders:
            out.append("DIRECTORIES & FOLDERS:\n" + "\n".join(f"  {f}" for f in sorted(folders)))
        if files:
            out.append(f"FILES ({len(files)} total):\n" + "\n".join(f"  {f}" for f in sorted(files)[:30]))
            if len(files) > 30:
                out.append(f"  ... and {len(files) - 30} more files.")
        if not shortcuts and not folders and not files:
            out.append("(This folder is completely empty)")

        return {"success": True, "result": "\n\n".join(out), "speak": None}

    def _organize_sync(self, folder: Path, apply_changes: bool) -> dict:
        moves = []
        errors = []
        counts: dict[str, int] = {}

        try:
            entries = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() not in (".lnk", ".url")]
        except Exception as e:
            return {"success": False, "result": f"Could not list folder: {e}", "speak": None}

        for f in entries:
            if f.name.startswith("."):
                continue
            category = _CATEGORY_MAP.get(f.suffix.lower(), "Other")
            dest_dir = folder / category
            dest = dest_dir / f.name
            counts[category] = counts.get(category, 0) + 1

            if apply_changes:
                try:
                    dest_dir.mkdir(exist_ok=True)
                    if dest.exists():
                        dest = dest_dir / f"{f.stem}_{uuid.uuid4().hex[:6]}{f.suffix}"
                    shutil.move(str(f), str(dest))
                    moves.append(f"{f.name} → {category}/")
                except Exception as e:
                    errors.append(f"{f.name}: {e}")

        if not counts:
            return {"success": True, "result": f"'{folder.name}' has no loose files to organize.", "speak": None}

        summary = ", ".join(f"{n} {cat}" for cat, n in sorted(counts.items()))
        if apply_changes:
            text = f"Organized {folder.name}: {summary}."
            if errors:
                text += f" {len(errors)} file(s) failed: {'; '.join(errors[:5])}"
            return {"success": len(errors) == 0 or len(moves) > 0, "result": text, "speak": None}
        else:
            return {
                "success": True,
                "result": f"Preview for {folder.name}: would sort into → {summary}. "
                          f"Call file_organizer with action='organize' to execute.",
                "speak": None,
            }

    async def _search(self, args: dict) -> dict:
        query = str(args.get("query", "")).strip().lower()
        if not query:
            return {"success": False, "result": "No search query provided.", "speak": None}

        raw_folder = args.get("target_folder") or args.get("folder") or args.get("path") or ""
        root = _resolve_friendly_folder(str(raw_folder)) if raw_folder else Path.home()
        if _is_protected_path(root):
            return {"success": False, "result": f"Refusing to search a protected system path: {root}", "speak": None}

        return await asyncio.to_thread(self._search_sync, root, query)

    def _search_sync(self, root: Path, query: str, max_depth: int = 5, max_results: int = 15) -> dict:
        matches = []
        root_depth = len(root.parts)
        start = time.monotonic()

        try:
            for dirpath, dirnames, filenames in os.walk(root):
                if time.monotonic() - start > 8:
                    break
                depth = len(Path(dirpath).parts) - root_depth
                if depth >= max_depth:
                    dirnames[:] = []
                    continue
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d.lower() not in ("node_modules", "__pycache__")]

                for fname in filenames:
                    if query in fname.lower():
                        matches.append(str(Path(dirpath) / fname))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
        except Exception as e:
            return {"success": False, "result": f"Search error: {e}", "speak": None}

        if not matches:
            return {"success": True, "result": f"No files matching '{query}' found under {root}.", "speak": None}
        return {"success": True, "result": f"Found {len(matches)} match(es):\n" + "\n".join(matches), "speak": None}


# =============================================================================
# 5 & 6. Environment Self-Awareness + Background Vitals Watchdog
# =============================================================================
class SystemVitalsMonitorTool(BaseTool):
    name = "get_environment_snapshot"
    description = (
        "Get a live snapshot of the machine you (the companion) live on — CPU/RAM/disk load, "
        "battery, and GPU temperature/utilization. Use this to ground your self-awareness or "
        "answer questions like 'how are you feeling' / 'is my PC okay' / 'how hot is my GPU'."
    )
    requires_approval = False

    POLL_INTERVAL_SEC = 45
    BATTERY_LOW_PCT = 15
    BATTERY_ALERT_COOLDOWN_SEC = 20 * 60
    GPU_HOT_TEMP_C = 85
    GPU_ALERT_COOLDOWN_SEC = 15 * 60
    DOWNLOAD_ALERT_COOLDOWN_SEC = 60

    async def execute(self, args: dict, context: dict) -> dict:
        vitals = await asyncio.to_thread(_collect_vitals_sync)
        return {"success": True, "result": _format_vitals(vitals), "speak": None}

    async def on_companion_init(self, companion):
        logger.info("[VitalsMonitor] Background watchdog starting (battery/GPU/downloads).")
        self._last_battery_alert = 0.0
        self._last_gpu_alert = 0.0
        self._last_download_alert = 0.0
        self._prev_partials: set[str] = set()
        self._announced_downloads: set[str] = set()
        self._battery_warned_missing = False

        asyncio.create_task(self._loop(companion))

    async def _loop(self, companion):
        while getattr(companion, "_running", False):
            try:
                await self._tick(companion)
            except Exception as e:
                logger.error(f"[VitalsMonitor] Tick failed: {e}", exc_info=True)
            await asyncio.sleep(self.POLL_INTERVAL_SEC)

    async def _tick(self, companion):
        vitals = await asyncio.to_thread(_collect_vitals_sync)
        now = time.monotonic()

        # --- Battery ---
        batt = vitals.get("battery_pct")
        if batt is not None:
            if (batt <= self.BATTERY_LOW_PCT and not vitals.get("battery_plugged")
                    and now - self._last_battery_alert > self.BATTERY_ALERT_COOLDOWN_SEC):
                self._last_battery_alert = now
                self._emit_proactive(
                    companion,
                    f"BATTERY_LOW: The laptop battery just dropped to {batt:.0f}% and is not charging. "
                    "Gently warn the user to plug in, in 1 short natural sentence."
                )

        # --- GPU heat ---
        gpu = vitals.get("gpu")
        if gpu and gpu.get("temp_c") and gpu["temp_c"] >= self.GPU_HOT_TEMP_C:
            if now - self._last_gpu_alert > self.GPU_ALERT_COOLDOWN_SEC:
                self._last_gpu_alert = now
                self._emit_proactive(
                    companion,
                    f"GPU_HOT: The GPU ({gpu.get('name','GPU')}) is running at {gpu['temp_c']:.0f}°C under "
                    f"{gpu['load_pct']:.0f}% load. Casually mention it might be worth checking the fans/airflow, "
                    "in 1 short natural sentence."
                )

        # --- Downloads folder watcher ---
        await self._check_downloads(companion, now)

    async def _check_downloads(self, companion, now: float):
        downloads_dir = Path.home() / "Downloads"
        if not downloads_dir.is_dir():
            return

        def _list():
            try:
                return list(downloads_dir.iterdir())
            except Exception:
                return []

        entries = await asyncio.to_thread(_list)
        partials_now = {p.stem for p in entries if p.suffix.lower() in DOWNLOAD_WATCH_EXT_IN_PROGRESS}
        finals_now = {p.stem: p.name for p in entries if p.suffix.lower() not in DOWNLOAD_WATCH_EXT_IN_PROGRESS and p.is_file()}

        finished = self._prev_partials - partials_now
        for stem in finished:
            fname = finals_now.get(stem)
            if fname and fname not in self._announced_downloads and now - self._last_download_alert > self.DOWNLOAD_ALERT_COOLDOWN_SEC:
                self._last_download_alert = now
                self._announced_downloads.add(fname)
                self._emit_proactive(
                    companion,
                    f"DOWNLOAD_FINISHED: The file '{fname}' just finished downloading in the Downloads folder. "
                    "Let the user know it's ready, in 1 short natural sentence."
                )
                break

        self._prev_partials = partials_now
        if len(self._announced_downloads) > 200:
            self._announced_downloads.clear()

    @staticmethod
    def _emit_proactive(companion, directive: str):
        companion.event_bus.emit_threadsafe("heartbeat_proactive", {
            "system_time": datetime.now().strftime("%H:%M"),
            "proactive_directive": directive,
            "trigger_type": "system_vitals",
        })


# =============================================================================
# 7. Hierarchical Plan-and-Execute Engine
# =============================================================================
class TaskPlannerTool(BaseTool):
    name = "plan_and_execute"
    description = (
        "For a goal that clearly needs MULTIPLE chained steps across different tools "
        "(e.g. 'download this mod, unzip it into the game folder, then launch the game'; "
        "'check 3 sites and tell me the cheapest RTX 4070'). Breaks the goal into an ordered "
        "plan and runs it step by step, one tool call at a time. Do NOT use this for a single "
        "simple action — call that tool directly instead."
    )
    requires_approval = False
    MAX_STEPS = 6

    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string", "description": "The full multi-step goal, in natural language."},
                    },
                    "required": ["goal"],
                },
            },
        }

    def get_confirmation_summary(self, args: dict) -> str:
        return f"Run a multi-step plan for: {args.get('goal', '')}"

    async def execute(self, args: dict, context: dict) -> dict:
        companion = context.get("companion_ref")
        if companion is None:
            return {"success": False, "result": "plan_and_execute requires companion context.", "speak": None}

        goal = str(args.get("goal", "")).strip()
        if not goal:
            return {"success": False, "result": "No goal provided.", "speak": None}

        catalog = "\n".join(
            f"- {n}: {t.description}" for n, t in companion.plugins._plugins.items() if n != self.name
        )

        planning_prompt = (
            "You are a task-planning engine for a desktop AI companion. Break the GOAL below into "
            f"an ORDERED JSON array of at most {self.MAX_STEPS} tool-call steps, using ONLY the tools "
            "listed under AVAILABLE TOOLS. Each element must look exactly like: "
            '{"tool": "<tool_name>", "args": {"<arg>": "<value>"}}. '
            "Keep the plan as short as possible and only include steps that are strictly necessary. "
            "Output ONLY the raw JSON array — no prose, no markdown fences.\n\n"
            f"AVAILABLE TOOLS:\n{catalog}\n\nGOAL: {goal}"
        )

        raw = await companion._llm_call(planning_prompt, "Produce the plan now.", temperature=0.1, max_tokens=600)
        if not raw:
            return {"success": False, "result": "Planner LLM produced no output.", "speak": None}

        raw_text = raw if isinstance(raw, str) else json.dumps(raw)
        try:
            cleaned = _strip_plan_json(raw_text)
            steps = json.loads(cleaned)
            if not isinstance(steps, list):
                raise ValueError("plan is not a JSON array")
        except Exception as e:
            logger.warning(f"[Planner] Failed to parse plan JSON: {e} | raw={raw_text[:300]}")
            return {"success": False, "result": "Could not parse a valid plan from the goal.", "speak": None}

        steps = steps[: self.MAX_STEPS]
        if not steps:
            return {"success": False, "result": "Planner produced an empty plan.", "speak": None}

        results = []
        for i, step in enumerate(steps, start=1):
            t_name = str(step.get("tool", "")).strip()
            t_args = step.get("args") or {}

            if t_name in ("hotkey", "click", "double_click", "type_text", "scroll", "move_mouse"):
                t_args["action"] = t_name
                t_name = "gui_action"
            elif t_name in ("open_app", "focus_app", "close_app"):
                t_args["action"] = t_name.replace("_app", "")
                t_name = "app_control"

            if not t_name or t_name == self.name:
                results.append(f"Step {i}: skipped (invalid or recursive tool reference).")
                continue
            if not companion.plugins.get(t_name):
                results.append(f"Step {i}: skipped — unknown tool '{t_name}'.")
                continue

            step_result = await companion._execute_tool(t_name, t_args)
            ok = bool(step_result.get("success"))
            snippet = str(step_result.get("result", ""))[:150]
            results.append(f"Step {i} ({t_name}): {'OK' if ok else 'FAILED'} — {snippet}")

            if not ok and "approval" in snippet.lower():
                results.append(f"Plan halted after step {i}: the user did not approve a required action.")
                break

        summary = "\n".join(results)
        logger.info(f"[Planner] Goal '{goal}' finished:\n{summary}")
        return {"success": True, "result": f"Plan for \"{goal}\":\n{summary}", "speak": None}


PLUGINS = [
    GUIActionTool,
    BrowserAgentTool,
    ExecuteCodeTool,
    FileOrganizerTool,
    SystemVitalsMonitorTool,
    TaskPlannerTool,
]
