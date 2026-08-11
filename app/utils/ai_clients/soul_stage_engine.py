import os
import re
import json
import time
import copy
import random
import asyncio
import logging
import datetime
import threading
import uuid

import numpy as np

from dataclasses import dataclass
from typing import AsyncGenerator, Callable, Optional, List
from pathlib import Path

from app.configuration import configuration
from app.utils.ai_clients.prompt_engine import PromptEngine
from app.utils.ai_clients.ai_factory import AIFactory

logger = logging.getLogger("Soul Stage")

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False
    logger.warning("[SoulStage.Context] tiktoken not available — falling back to char-based estimation")

_ENCODER_CACHE: dict = {}


def _get_encoder(model_name: str = "default"):
    if not _HAS_TIKTOKEN:
        return None
    if model_name not in _ENCODER_CACHE:
        try:
            _ENCODER_CACHE[model_name] = tiktoken.encoding_for_model(model_name)
        except KeyError:
            try:
                _ENCODER_CACHE[model_name] = tiktoken.get_encoding("cl100k_base")
            except Exception:
                _ENCODER_CACHE[model_name] = None
    return _ENCODER_CACHE[model_name]


def count_tokens(text: str, model_name: str = "default") -> int:
    if not text:
        return 0
    enc = _get_encoder(model_name)
    if enc is not None:
        return len(enc.encode(text))
    return max(1, len(text) // 4)


def count_message_tokens(messages: list[dict], model_name: str = "default") -> int:
    total = 0
    for m in messages:
        total += 4
        total += count_tokens(m.get("content", ""), model_name)
        if m.get("name"):
            total += count_tokens(m["name"], model_name)
        total += 2
    return total


@dataclass
class NPCCard:
    name: str
    archetype: str
    personality: str
    avatar_key: str
    turn_count: int = 0


@dataclass
class StructuredEvent:
    actor: str
    action: str
    outcome: str = ""

@dataclass
class DiceRollResult:
    notation: str
    label: str
    dc: Optional[int]
    rolls: List[int]
    modifier: int
    total: int
    success: Optional[bool]

    @property
    def margin(self) -> Optional[int]:
        return None if self.dc is None else self.total - self.dc

    def to_dict(self) -> dict:
        return {
            "notation": self.notation, "label": self.label, "dc": self.dc,
            "rolls": list(self.rolls), "modifier": self.modifier,
            "total": self.total, "success": self.success,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DiceRollResult":
        return cls(
            notation=d.get("notation", "1d20"),
            label=d.get("label", "Check"),
            dc=d.get("dc"),
            rolls=list(d.get("rolls", [])),
            modifier=int(d.get("modifier", 0) or 0),
            total=int(d.get("total", 0) or 0),
            success=d.get("success"),
        )

    def describe(self) -> str:
        mod_str = f"{'+' if self.modifier >= 0 else ''}{self.modifier}" if self.modifier else ""
        base = f"{self.label} ({self.notation}{mod_str}) = {self.total}"
        if self.dc is None:
            return base
        outcome = "Success" if self.success else "Failure"
        return f"{base} vs DC {self.dc} — {outcome}"


class DiceRoller:
    _NOTATION_RE = re.compile(r"^\s*(\d*)\s*d\s*(\d+)\s*$", re.IGNORECASE)
    MAX_DICE_COUNT = 10
    MAX_DICE_SIDES = 100
    MAX_MODIFIER = 20

    @classmethod
    def roll(cls, notation: str = "d20", modifier: int = 0,
              dc: Optional[int] = None, label: str = "Check") -> DiceRollResult:
        count, sides = cls._parse_notation(notation)

        try:
            modifier = int(modifier)
        except (TypeError, ValueError):
            modifier = 0
        modifier = max(-cls.MAX_MODIFIER, min(modifier, cls.MAX_MODIFIER))

        dc_int: Optional[int] = None
        if dc is not None:
            try:
                dc_int = int(dc)
            except (TypeError, ValueError):
                dc_int = None

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls) + modifier
        success = None if dc_int is None else (total >= dc_int)

        return DiceRollResult(
            notation=f"{count}d{sides}",
            label=(label or "Check").strip()[:40] or "Check",
            dc=dc_int,
            rolls=rolls,
            modifier=modifier,
            total=total,
            success=success,
        )

    @classmethod
    def _parse_notation(cls, notation: str) -> tuple[int, int]:
        notation = (notation or "").strip().lower()
        m = cls._NOTATION_RE.match(notation)
        if not m:
            return 1, 20
        count = int(m.group(1)) if m.group(1) else 1
        sides = int(m.group(2))
        count = max(1, min(count, cls.MAX_DICE_COUNT))
        sides = max(2, min(sides, cls.MAX_DICE_SIDES))
        return count, sides


@dataclass
class LoreCard:
    """
    A compact, triggerable piece of campaign canon.
    """
    id: str
    title: str
    category: str
    content: str
    triggers: list[str]
    visibility: str = "party"  # party | player | private:<actor>
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "category": self.category,
            "content": self.content, "triggers": list(self.triggers),
            "visibility": self.visibility, "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LoreCard":
        title = str(data.get("title", "Untitled lore")).strip()[:120] or "Untitled lore"
        raw_triggers = data.get("triggers", [])
        if isinstance(raw_triggers, str):
            raw_triggers = [part.strip() for part in raw_triggers.split(",")]
        triggers = [str(t).strip()[:80] for t in raw_triggers if str(t).strip()]
        if not triggers:
            triggers = [title]
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex[:12]), title=title,
            category=str(data.get("category", "Lore"))[:60],
            content=str(data.get("content", "")).strip()[:2000],
            triggers=triggers[:12], visibility=str(data.get("visibility", "party")),
            enabled=bool(data.get("enabled", True)),
        )


class LoreRegistry:
    MAX_ACTIVE_CARDS = 6

    def __init__(self, cards: Optional[list[dict | LoreCard]] = None):
        self.cards: dict[str, LoreCard] = {}
        for raw in cards or []:
            card = raw if isinstance(raw, LoreCard) else LoreCard.from_dict(raw)
            self.cards[card.id] = card

    def to_dict(self) -> list[dict]:
        return [card.to_dict() for card in self.cards.values()]

    def upsert(self, data: dict) -> LoreCard:
        card = LoreCard.from_dict(data)
        raw_id = str(data.get("id") or "").strip()
        if not raw_id or raw_id not in self.cards:
            for existing_id, existing in self.cards.items():
                if (existing.title.casefold() == card.title.casefold()
                        and existing.visibility == card.visibility):
                    card.id = existing_id
                    break
        self.cards[card.id] = card
        return card

    def remove(self, card_id: str) -> bool:
        return self.cards.pop(card_id, None) is not None

    def relevant(self, text: str, audience: str = "party") -> list[LoreCard]:
        haystack = (text or "").casefold()
        ranked: list[tuple[int, LoreCard]] = []
        for card in self.cards.values():
            if not card.enabled or not card.content:
                continue
            if card.visibility == "party":
                visible = True
            elif card.visibility == "player":
                visible = audience == "player"
            else:
                visible = card.visibility == f"private:{audience}"
            if not visible:
                continue
            score = sum(1 for trigger in card.triggers if trigger.casefold() in haystack)
            if score:
                ranked.append((score, card))
        ranked.sort(key=lambda item: (-item[0], item[1].title.casefold()))
        return [card for _, card in ranked[:self.MAX_ACTIVE_CARDS]]

    def prompt_block(self, text: str, audience: str = "party") -> str:
        cards = self.relevant(text, audience)
        if not cards:
            return ""
        lines = ["[RELEVANT CAMPAIGN LORE — canon, do not contradict]"]
        for card in cards:
            lines.append(f"- [id: {card.id}] {card.title} ({card.category}): {card.content}")
        return "\n".join(lines)


class CampaignBoard:
    """Persistent player-visible objectives and progress clocks."""
    MAX_ENTRIES = 40

    def __init__(self, data: Optional[dict] = None):
        data = data or {}
        self.objectives: list[dict] = list(data.get("objectives", []))[:self.MAX_ENTRIES]
        self.clocks: list[dict] = list(data.get("clocks", []))[:self.MAX_ENTRIES]

    @staticmethod
    def _normalise_entry(entry: dict, is_clock: bool) -> dict:
        title = str(entry.get("title", "Untitled")).strip()[:120] or "Untitled"
        current = max(0, int(entry.get("current", entry.get("progress", 0)) or 0))
        maximum = max(1, min(20, int(entry.get("max", 4 if is_clock else 1) or 1)))
        return {
            "id": str(entry.get("id") or uuid.uuid4().hex[:12]), "title": title,
            "description": str(entry.get("description", "")).strip()[:500],
            "current": min(current, maximum), "max": maximum,
            "status": str(entry.get("status", "active")),
        }

    def to_dict(self) -> dict:
        return {"objectives": list(self.objectives), "clocks": list(self.clocks)}

    def _upsert(self, bucket: list[dict], entry: dict, is_clock: bool) -> dict:
        normalised = self._normalise_entry(entry, is_clock)
        raw_id = str(entry.get("id") or "").strip()
        raw_title = normalised["title"].casefold()
        for i, existing in enumerate(bucket):
            if (raw_id and existing.get("id") == raw_id) or existing.get("title", "").casefold() == raw_title:
                merged = dict(existing)
                merged.update({k: v for k, v in normalised.items() if k != "id"})
                bucket[i] = merged
                return merged
        bucket.append(normalised)
        if len(bucket) > self.MAX_ENTRIES:
            del bucket[0]
        return normalised

    def upsert_objective(self, entry: dict) -> dict:
        return self._upsert(self.objectives, entry, is_clock=False)

    def upsert_clock(self, entry: dict) -> dict:
        return self._upsert(self.clocks, entry, is_clock=True)

    def advance_clock(self, title: str, delta: int) -> Optional[dict]:
        target = title.strip().casefold()
        for clock in self.clocks:
            if clock.get("title", "").casefold() == target:
                clock["current"] = max(0, min(clock.get("max", 4), clock.get("current", 0) + int(delta)))
                return clock
        return None

    def prompt_block(self) -> str:
        lines = []
        if self.objectives:
            lines.append("[CAMPAIGN OBJECTIVES]")
            lines.extend(f"- {x['title']} [{x['status']}] {x['current']}/{x['max']}: {x['description']}" for x in self.objectives)
        if self.clocks:
            lines.append("[CAMPAIGN CLOCKS]")
            lines.extend(f"- {x['title']}: {x['current']}/{x['max']} — {x['description']}" for x in self.clocks)
        return "\n".join(lines)


class RPGRules:
    """The deterministic authority for player rolls and resource mutations."""
    DEFAULT_RESOURCES = {
        "health": {"current": 10, "max": 10},
        "energy": {"current": 6, "max": 6},
        "stress": {"current": 0, "max": 6},
    }
    DIFFICULTIES = {"trivial": 5, "easy": 10, "moderate": 13, "hard": 16, "extreme": 20}

    @classmethod
    def resolve_check(cls, spec: dict, state: "WorldState") -> DiceRollResult:
        notation = str(spec.get("notation", "d20"))
        skill = str(spec.get("skill", "general")).strip().lower()
        dc = spec.get("dc")
        if dc is None:
            dc = cls.DIFFICULTIES.get(str(spec.get("difficulty", "moderate")).lower(), 13)
        try:
            dc = max(5, min(30, int(dc)))
        except (TypeError, ValueError):
            dc = 13

        try:
            situational = int(spec.get("modifier", 0) or 0)
        except (TypeError, ValueError):
            situational = 0
        situational = max(-10, min(10, situational))
        modifier = state.skill_modifier(skill) + situational

        return DiceRoller.roll(notation=notation, modifier=modifier, dc=dc,
                               label=str(spec.get("label") or skill.title() or "Check"))

    @classmethod
    def apply_resource_delta(cls, state: "WorldState", deltas: dict) -> dict[str, int]:
        applied: dict[str, int] = {}
        for name, raw_delta in (deltas or {}).items():
            if name not in state.resources:
                continue
            try:
                delta = max(-10, min(10, int(raw_delta)))
            except (TypeError, ValueError):
                continue
            pool = state.resources[name]
            before = int(pool["current"])
            pool["current"] = max(0, min(int(pool["max"]), before + delta))
            applied[name] = pool["current"] - before
        return applied

class WorldState:
    MAX_EVENTS = 14

    def __init__(self):
        self.location: str = "Unknown location"
        self.time_of_day: str = "day"
        self.atmosphere: str = ""
        self.bg_image: str = "None"
        self.ambient_audio: str = "None"
        self.key_facts: dict[str, str] = {}
        self.events: list[StructuredEvent] = []
        self.world_context: str = ""
        self.player_inventory: list[str] = []
        self.player_status: list[str] = []
        self.gm_tone: str = "epic_fantasy"
        self.narrator_style: str = "Standard evocative present-tense prose"
        self.historical_summary: str = ""
        self.pending_summarization: list[str] = []
        self.dice_rolls_enabled: bool = False
        self.lock_bg: bool = False
        self.disable_ambient: bool = False
        self.player_skills: dict[str, int] = {}
        self.resources: dict[str, dict[str, int]] = copy.deepcopy(RPGRules.DEFAULT_RESOURCES)
        self.status_durations: dict[str, int] = {}
        self.lore_registry = LoreRegistry()
        self.campaign_board = CampaignBoard()
        self.private_knowledge: dict[str, list[str]] = {}

    _STATUS_REMINDERS: dict[str, str] = {
        "poison":   "The player is POISONED — reflect physical symptoms (nausea, sweat, tremor) where natural, worsening if untreated.",
        "bleed":    "The player is BLEEDING — exertion should visibly worsen it; acknowledge blood loss if the scene continues.",
        "wound":    "The player is WOUNDED — movement, combat, or strain should be visibly harder.",
        "exhaust":  "The player is EXHAUSTED — reactions are slower, dialogue can be terser, physical tasks harder.",
        "tired":    "The player is EXHAUSTED — reactions are slower, dialogue can be terser, physical tasks harder.",
        "stun":     "The player is STUNNED — this should visibly limit their ability to act decisively this turn.",
        "blind":    "The player is BLINDED — lean on sound, touch, and smell instead of sight.",
        "afraid":   "The player is AFRAID/FRIGHTENED — characters may notice hesitation or visible fear.",
        "fear":     "The player is AFRAID/FRIGHTENED — characters may notice hesitation or visible fear.",
        "drunk":    "The player is INTOXICATED — perception and dialogue should reflect impaired judgement.",
        "intoxic":  "The player is INTOXICATED — perception and dialogue should reflect impaired judgement.",
        "sick":     "The player is ILL — stamina and clarity should be visibly reduced.",
        "cold":     "The player is COLD/FREEZING — reflect physical discomfort where natural.",
        "burn":     "The player is BURNED — pain and visible injury should be reflected if relevant.",
        "paraly":   "The player is PARALYZED — they cannot act physically; other characters should notice and react.",
        "sleep":    "The player is ASLEEP/DROWSY — reduce their agency and awareness accordingly.",
        "confus":   "The player is CONFUSED/DISORIENTED — their perception of the scene may be unreliable.",
    }

    def _status_reminders(self) -> list[str]:
        reminders: list[str] = []
        for status in self.player_status:
            s_low = status.lower()
            matched_text = None
            for key, text in self._STATUS_REMINDERS.items():
                if key in s_low:
                    matched_text = text
                    break
            if matched_text is None:
                matched_text = (
                    f'The player has an active condition — "{status}" — '
                    f"keep it consistent in narration and dialogue until it's explicitly resolved."
                )
            if matched_text not in reminders:
                reminders.append(matched_text)
        return reminders
    
    @staticmethod
    def _normalize_fact_key(key: str) -> str:
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    def update_from_plan(self, plan: dict):
        self.location      = plan.get("location") or self.location
        self.time_of_day   = plan.get("time_of_day") or self.time_of_day
        self.atmosphere    = plan.get("atmosphere") or self.atmosphere

        if not self.lock_bg:
            self.bg_image = plan.get("bg_image") or self.bg_image
        if self.disable_ambient:
            self.ambient_audio = "None"
        else:
            self.ambient_audio = plan.get("ambient_audio") or self.ambient_audio

        if key_facts := plan.get("key_facts"):
            if isinstance(key_facts, dict):
                self.key_facts.update({
                    self._normalize_fact_key(k): str(v)
                    for k, v in key_facts.items() if k
                })

        for item in plan.get("inventory_add",[]):
            if item and item not in self.player_inventory:
                self.player_inventory.append(item)
        
        remove_items = set(plan.get("inventory_remove",[]))
        if remove_items:
            self.player_inventory =[i for i in self.player_inventory if i not in remove_items]

        for st in plan.get("status_add",[]):
            if st and st not in self.player_status:
                self.player_status.append(st)
                
        remove_status = set(plan.get("status_remove",[]))
        if remove_status:
            self.player_status = [s for s in self.player_status if s not in remove_status]
            for status in remove_status:
                self.status_durations.pop(status, None)

        for status_data in plan.get("status_effects", []):
            if not isinstance(status_data, dict):
                continue
            name = str(status_data.get("name", "")).strip()[:80]
            if not name:
                continue
            if name not in self.player_status:
                self.player_status.append(name)
            try:
                duration = max(1, min(99, int(status_data.get("duration", 1))))
                self.status_durations[name] = duration
            except (TypeError, ValueError):
                pass

        RPGRules.apply_resource_delta(self, plan.get("resource_delta", {}))

    def skill_modifier(self, skill: str) -> int:
        value = self.player_skills.get((skill or "general").strip().lower(), 0)
        try:
            return max(-5, min(10, int(value)))
        except (TypeError, ValueError):
            return 0

    def tick_statuses(self) -> list[str]:
        expired = []
        for status, remaining in list(self.status_durations.items()):
            remaining -= 1
            if remaining <= 0:
                expired.append(status)
                self.status_durations.pop(status, None)
            else:
                self.status_durations[status] = remaining
        if expired:
            expired_set = set(expired)
            self.player_status = [status for status in self.player_status if status not in expired_set]
        return expired

    def add_private_knowledge(self, actor: str, text: str) -> None:
        actor = (actor or "").strip()
        text = (text or "").strip()
        if not actor or not text:
            return
        notes = self.private_knowledge.setdefault(actor, [])
        if text not in notes:
            notes.append(text[:600])
        self.private_knowledge[actor] = notes[-30:]

    def private_knowledge_block(self, actor: str) -> str:
        notes = self.private_knowledge.get(actor, [])
        if not notes:
            return ""
        return "[PRIVATE KNOWLEDGE — only you know this]\n" + "\n".join(f"- {note}" for note in notes[-8:])

    def to_dict(self) -> dict:
        return {
            "location": self.location, "time_of_day": self.time_of_day,
            "atmosphere": self.atmosphere, "bg_image": self.bg_image,
            "ambient_audio": self.ambient_audio, "key_facts": dict(self.key_facts),
            "player_inventory": list(self.player_inventory), "player_status": list(self.player_status),
            "status_durations": dict(self.status_durations), "player_skills": dict(self.player_skills),
            "resources": copy.deepcopy(self.resources), "narrator_style": self.narrator_style,
            "gm_tone": self.gm_tone, "historical_summary": self.historical_summary,
            "pending_summarization": list(self.pending_summarization),
            "events": [{"actor": e.actor, "action": e.action, "outcome": e.outcome} for e in self.events],
            "lore_cards": self.lore_registry.to_dict(), "campaign_board": self.campaign_board.to_dict(),
            "private_knowledge": copy.deepcopy(self.private_knowledge),
            "dice_rolls_enabled": self.dice_rolls_enabled, "world_context": self.world_context,
            "lock_bg": self.lock_bg, "disable_ambient": self.disable_ambient,
        }

    def add_event(self, actor: str, action: str, outcome: str = ""):
        self.events.append(StructuredEvent(actor=actor, action=action, outcome=outcome))
            
        if len(self.events) > self.MAX_EVENTS:
            old_events  = self.events[:4]
            self.events = self.events[4:]
            
            compressed = "; ".join(
                f"[{e.actor}] {e.action}" + (f" -> {e.outcome}" if e.outcome else "")
                for e in old_events
            )
            self.pending_summarization.append(compressed)

    def to_prompt(self) -> str:
        lines =[f"LOCATION: {self.location}", f"TIME: {self.time_of_day}"]
        
        if self.atmosphere:
            lines.append(f"ATMOSPHERE: {self.atmosphere}")

        if self.lock_bg:
            lines.append(f"BACKGROUND IMAGE: {self.bg_image} (LOCKED — do NOT change)")
        if self.disable_ambient:
            lines.append("AMBIENT AUDIO: Disabled (must be 'None')")
            
        if self.key_facts:
            lines.append("ESTABLISHED FACTS:")
            for k, v in self.key_facts.items():
                lines.append(f"  * {k.replace('_', ' ')}: {v}")

        if self.historical_summary:
            lines.append(f"HISTORICAL SUMMARY: {self.historical_summary}")

        if self.player_inventory:
            lines.append(f"PLAYER INVENTORY: {', '.join(self.player_inventory)}")
        if self.player_status:
            lines.append(f"PLAYER STATUS: {', '.join(self.player_status)}")

        if self.resources:
            resource_text = ", ".join(
                f"{name}={pool.get('current', 0)}/{pool.get('max', 0)}"
                for name, pool in self.resources.items()
            )
            lines.append(f"PLAYER RESOURCES: {resource_text}")
        if self.player_skills:
            lines.append("PLAYER SKILLS: " + ", ".join(f"{name} {value:+d}" for name, value in self.player_skills.items()))

        reminders = self._status_reminders()
        if reminders:
            lines.append("SYSTEM REMINDERS (do not ignore these while writing):")
            for r in reminders:
                lines.append(f"  ! {r}")

        if self.events:
            lines.append("RECENT EVENTS:")
            for ev in self.events[-4:]:
                op = f" -> {ev.outcome}" if ev.outcome else ""
                lines.append(f"[{ev.actor}] {ev.action}{op}")

        campaign = self.campaign_board.prompt_block()
        if campaign:
            lines.append(campaign)
                
        return "\n".join(lines)

    def reset(self):
        ctx      = self.world_context
        tone     = self.gm_tone
        style    = self.narrator_style
        statuses = self.player_status.copy()
        dice_on  = self.dice_rolls_enabled
        skills = dict(self.player_skills)
        resources = copy.deepcopy(self.resources)
        lore_cards = self.lore_registry.to_dict()
        campaign_board = self.campaign_board.to_dict()
        lock_bg = self.lock_bg
        disable_ambient = self.disable_ambient

        self.__init__()

        self.world_context = ctx
        self.gm_tone       = tone
        self.narrator_style = style
        self.player_status = statuses
        self.dice_rolls_enabled = dice_on
        self.player_skills = skills
        self.resources = resources
        self.lore_registry = LoreRegistry(lore_cards)
        self.campaign_board = CampaignBoard(campaign_board)
        self.lock_bg = lock_bg
        self.disable_ambient = disable_ambient


class NPCRegistry:
    ARCHETYPE_AVATARS = {
        "innkeeper":        "app/gui/icons/npc/innkeeper.png",
        "guard":            "app/gui/icons/npc/guard.png",
        "authority figure": "app/gui/icons/npc/guard.png",
        "officer":          "app/gui/icons/npc/guard.png",
        "soldier":          "app/gui/icons/npc/guard.png",
        "merchant":         "app/gui/icons/npc/merchant.png",
        "trader":           "app/gui/icons/npc/merchant.png",
        "villain":          "app/gui/icons/npc/villain.png",
        "antagonist":       "app/gui/icons/npc/villain.png",
        "citizen":          "app/gui/icons/npc/citizen.png",
        "bystander":        "app/gui/icons/npc/citizen.png",
        "creature":         "app/gui/icons/npc/creature.png",
        "monster":          "app/gui/icons/npc/creature.png",
        "sage":             "app/gui/icons/npc/sage.png",
        "scholar":          "app/gui/icons/npc/sage.png",
        "elder":            "app/gui/icons/npc/sage.png",
        "healer":           "app/gui/icons/npc/sage.png",
        "noble":            "app/gui/icons/npc/noble.png",
        "aristocrat":       "app/gui/icons/npc/noble.png",
        "criminal":         "app/gui/icons/npc/villain.png",
        "unknown":          "app/gui/icons/npc/citizen.png",
    }
    DEFAULT_AVATAR = "app/gui/icons/logotype.png"

    def __init__(self):
        self.active: dict[str, NPCCard] = {}
        self.despawned: dict[str, NPCCard] = {}

    def spawn(self, name: str, archetype: str, personality: str) -> NPCCard:
        if name in self.active:
            return self.active[name]
        
        if name in self.despawned:
            npc = self.despawned[name]
            if personality and not npc.personality:
                npc.personality = personality
            self.active[name] = npc
            del self.despawned[name]
            logger.info(f"[NPCRegistry] Respawned from memory: {name}")
            return npc

        archetype = archetype.lower().strip()
        avatar_key = archetype if archetype in self.ARCHETYPE_AVATARS else "unknown"
        npc = NPCCard(name=name, archetype=archetype, personality=personality, avatar_key=avatar_key)
        self.active[name] = npc
        logger.info(f"[NPCRegistry] Spawned new: {name} ({archetype})")
        return npc

    def despawn(self, name: str):
        if name in self.active:
            self.despawned[name] = self.active[name]
            del self.active[name]
            logger.info(f"[NPCRegistry] Despawned and saved to memory: {name}")

    def get(self, name: str) -> Optional[NPCCard]:
        return self.active.get(name)

    def get_any(self, name: str) -> Optional[NPCCard]:
        return self.active.get(name) or self.despawned.get(name)

    def list_active(self) -> list[NPCCard]:
        return list(self.active.values())

    def get_avatar_path(self, npc: NPCCard) -> str:
        if not npc:
            return self.DEFAULT_AVATAR
        if npc.avatar_key and Path(npc.avatar_key).exists() and not Path(npc.avatar_key).is_dir():
            return npc.avatar_key
        if npc.avatar_key in self.ARCHETYPE_AVATARS:
            p = self.ARCHETYPE_AVATARS[npc.avatar_key]
            if Path(p).exists():
                return p
        arch = (npc.archetype or "").lower().strip()
        if arch in self.ARCHETYPE_AVATARS:
            p = self.ARCHETYPE_AVATARS[arch]
            if Path(p).exists():
                return p
        cit_p = self.ARCHETYPE_AVATARS.get("citizen")
        if cit_p and Path(cit_p).exists():
            return cit_p
        return self.DEFAULT_AVATAR

    def get_avatar_path_for_name(self, name: str, fallback_archetype: str = "citizen") -> str:
        npc = self.get_any(name)
        if npc:
            return self.get_avatar_path(npc)
        arch = (fallback_archetype or "citizen").lower().strip()
        if arch in self.ARCHETYPE_AVATARS:
            p = self.ARCHETYPE_AVATARS[arch]
            if Path(p).exists():
                return p
        cit_p = self.ARCHETYPE_AVATARS.get("citizen")
        if cit_p and Path(cit_p).exists():
            return cit_p
        return self.DEFAULT_AVATAR

    def clear(self):
        self.active.clear()

    def as_text(self) -> str:
        if not self.active:
            return "None"
        return "\n".join(f"  - {n.name} ({n.archetype}): {n.personality}" for n in self.active.values())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LONG-TERM RAG MEMORY FOR NPCs
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_EMBEDDER = None
_EMBEDDER_FAILED: bool = False
_EMBEDDER_AVAILABLE: Optional[bool] = None
_EMBEDDER_LOCK = threading.Lock()

def _check_embedder_available() -> bool:
    global _EMBEDDER_AVAILABLE
    if _EMBEDDER_AVAILABLE is None:
        try:
            import sentence_transformers
            _EMBEDDER_AVAILABLE = True
        except ImportError:
            _EMBEDDER_AVAILABLE = False
            logger.warning(
                "[Soul Stage] sentence-transformers not found. "
                "NPC RAG memory will fall back to standard mode. "
                "Install with: pip install sentence-transformers"
            )
    return _EMBEDDER_AVAILABLE


def _get_embedder():
    global _EMBEDDER, _EMBEDDER_FAILED

    if _EMBEDDER is not None or _EMBEDDER_FAILED or not _check_embedder_available():
        return _EMBEDDER

    with _EMBEDDER_LOCK:
        if _EMBEDDER is None and not _EMBEDDER_FAILED:
            try:
                from sentence_transformers import SentenceTransformer

                project_root = Path(__file__).resolve().parent.parent.parent
                local_path = project_root / "app" / "utils" / "all-MiniLM-L6-v2"
                model_target = str(local_path) if local_path.exists() else "all-MiniLM-L6-v2"

                device = "cpu"

                logger.info(f"[Soul Stage] Loading embedding model on {device.upper()} from '{model_target}'...")
                _EMBEDDER = SentenceTransformer(model_target, device=device)
                logger.info(f"[Soul Stage] Embedding model loaded successfully on {device.upper()}")

            except Exception as e:
                logger.error(f"[Soul Stage] Failed to load embedding model: {e}", exc_info=True)
                _EMBEDDER = None
                _EMBEDDER_FAILED = True

    return _EMBEDDER

NPC_MEM_DIR = Path(".soul_stage/npc_memory")

class NPCMemoryEntry:
    __slots__ = ("text", "embedding", "turn_idx", "timestamp")

    def __init__(self, text: str, embedding, turn_idx: int, timestamp: float):
        self.text = text
        self.embedding = embedding
        self.turn_idx = turn_idx
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "embedding": self.embedding.tolist() if hasattr(self.embedding, "tolist") else list(self.embedding),
            "turn_idx": self.turn_idx,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NPCMemoryEntry":
        return cls(
            text=d["text"],
            embedding=np.array(d["embedding"], dtype=np.float32),
            turn_idx=d.get("turn_idx", 0),
            timestamp=d.get("timestamp", 0),
        )


class NPCMemoryRegistry(NPCRegistry):
    """
    NPCRegistry + long-term RAG memory per NPC.
    """

    MAX_MEMORIES_PER_NPC = 200
    TOP_K_RETRIEVAL       = 5
    SIMILARITY_THRESHOLD  = 0.30

    def __init__(self, embedder=None):
        super().__init__()
        self.embedder = embedder
        self._mem_cache: dict[str, list[NPCMemoryEntry]] = {}
        self._current_turn_idx: int = 0

        try:
            NPC_MEM_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.warning(f"[NPCMemory] Could not create {NPC_MEM_DIR}")

    def _get_embedder(self):
        if self.embedder is not None:
            return self.embedder
        self.embedder = _get_embedder()
        return self.embedder

    def set_turn_idx(self, turn_idx: int) -> None:
        self._current_turn_idx = turn_idx

    def _mem_path(self, name: str) -> Path:
        safe = name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        return NPC_MEM_DIR / f"{safe}.json"

    def _load_memories(self, name: str) -> list[NPCMemoryEntry]:
        if name in self._mem_cache:
            return self._mem_cache[name]
        path = self._mem_path(name)
        if not path.exists():
            self._mem_cache[name] = []
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entries = [NPCMemoryEntry.from_dict(d) for d in data]
            self._mem_cache[name] = entries
            return entries
        except Exception as e:
            logger.warning(f"[NPCMemory] Failed to load memories for {name}: {e}")
            self._mem_cache[name] = []
            return []

    def _save_memories(self, name: str, entries: list[NPCMemoryEntry]) -> None:
        self._mem_cache[name] = entries
        path = self._mem_path(name)
        try:
            data = [e.to_dict() for e in entries]
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.warning(f"[NPCMemory] Failed to save memories for {name}: {e}")

    def add_memory(self, npc_name: str, text: str, turn_idx: Optional[int] = None) -> None:
        if not text or not text.strip():
            return
        embedder = self._get_embedder()
        if embedder is None:
            return
        try:
            emb = embedder.encode(text)
            if hasattr(emb, "numpy"):
                emb = emb.numpy()
            emb = np.asarray(emb, dtype=np.float32)
        except Exception as e:
            logger.warning(f"[NPCMemory] Embedding failed for {npc_name}: {e}")
            return

        entries = self._load_memories(npc_name)
        entries.append(NPCMemoryEntry(
            text=text,
            embedding=emb,
            turn_idx=turn_idx if turn_idx is not None else self._current_turn_idx,
            timestamp=time.time(),
        ))

        if len(entries) > self.MAX_MEMORIES_PER_NPC:
            entries = entries[-self.MAX_MEMORIES_PER_NPC:]

        self._save_memories(npc_name, entries)
        logger.debug(f"[NPCMemory] +1 memory for {npc_name} (total={len(entries)})")

    def recall(self, npc_name: str, query: str, top_k: Optional[int] = None) -> List[str]:
        """Retrieve top-k relevant memories for the given query."""
        top_k = top_k or self.TOP_K_RETRIEVAL
        entries = self._load_memories(npc_name)
        if not entries:
            return []
        embedder = self._get_embedder()
        if embedder is None:
            return []

        try:
            q_emb = embedder.encode(query)
            if hasattr(q_emb, "numpy"):
                q_emb = q_emb.numpy()
            q_emb = np.asarray(q_emb, dtype=np.float32)
        except Exception as e:
            logger.warning(f"[NPCMemory] Query embedding failed: {e}")
            return []

        sims = []
        for e in entries:
            emb = np.asarray(e.embedding, dtype=np.float32)
            n1 = np.linalg.norm(q_emb) + 1e-9
            n2 = np.linalg.norm(emb) + 1e-9
            sim = float(np.dot(q_emb, emb) / (n1 * n2))
            sims.append(sim)

        ranked = sorted(zip(sims, entries), key=lambda x: -x[0])
        return [e.text for s, e in ranked[:top_k] if s >= self.SIMILARITY_THRESHOLD]

    def get_memory_block(self, npc_name: str, query: str, top_k: Optional[int] = None) -> str:
        """Format memories as a prompt block for injection into NPC_SYSTEM_PROMPT."""
        memories = self.recall(npc_name, query, top_k)
        if not memories:
            return ""
        lines = ["", "[MEMORIES — your past interactions, relevant to current context]"]
        for i, m in enumerate(memories, 1):
            snippet = m[:200] + ("..." if len(m) > 200 else "")
            lines.append(f"{i}. {snippet}")
        lines.append("")
        return "\n".join(lines)

    def clear_memory(self, npc_name: str) -> None:
        """Delete all memories for an NPC."""
        self._mem_cache.pop(npc_name, None)
        path = self._mem_path(npc_name)
        if path.exists():
            try:
                path.unlink()
            except Exception as e:
                logger.warning(f"[NPCMemory] Failed to delete {path}: {e}")

    def memory_count(self, npc_name: str) -> int:
        """Return number of stored memories for an NPC."""
        return len(self._load_memories(npc_name))
    
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TOKEN-AWARE CONTEXT WINDOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SoulStageContextWindow:
    """
    Sliding window with priority-based truncation for building LLM context.
    """

    DEFAULT_BUDGETS = {
        "GM_PLANNER":   7000,
        "GM_EXECUTOR":  5000,
        "GM_ROUTING":   3500,
        "NPC":          5000,
    }

    OUTPUT_RESERVES = {
        "GM_PLANNER":   600,
        "GM_EXECUTOR":  500,
        "GM_ROUTING":   200,
        "NPC":          300,
    }

    def __init__(
        self,
        model_name: str = "gpt-4",
        max_context: int = 8000,
        budgets: Optional[dict] = None,
        output_reserves: Optional[dict] = None,
    ):
        self.model_name = model_name
        self.max_context = max_context
        self.budgets = budgets or self.DEFAULT_BUDGETS.copy()
        self.output_reserves = output_reserves or self.OUTPUT_RESERVES.copy()

        if max_context is not None and max_context > 0:
            for role in self.budgets:
                self.budgets[role] = min(self.budgets[role], max_context)
        else:
            for role in self.budgets:
                self.budgets[role] = max(self.budgets[role], 131072)

    def build_for_planner(
        self,
        system_prompt: str,
        world_state_prompt: str,
        context_messages: list[dict],
        player_message: str,
        lorebook_text: str = "",
        historical_summary: str = "",
    ) -> list[dict]:
        budget = self.budgets["GM_PLANNER"]
        output_reserve = self.output_reserves["GM_PLANNER"]
        input_budget = budget - output_reserve

        messages: list[dict] = []

        messages.append({"role": "system", "content": system_prompt})
        used = count_tokens(system_prompt, self.model_name)

        ws_tokens = count_tokens(world_state_prompt, self.model_name)
        max_ws = int(input_budget * 0.35)
        if ws_tokens > max_ws:
            world_state_prompt = self._truncate_world_state(world_state_prompt, max_ws)
            ws_tokens = count_tokens(world_state_prompt, self.model_name)
        if world_state_prompt:
            messages.append({"role": "user", "content": f"[WORLD STATE]\n{world_state_prompt}"})
            used += ws_tokens

        if historical_summary:
            hs_tokens = count_tokens(historical_summary, self.model_name)
            max_hs = int(input_budget * 0.15)
            if hs_tokens > max_hs:
                historical_summary = historical_summary[:max_hs * 3] + "... [truncated]"
                hs_tokens = count_tokens(historical_summary, self.model_name)
            if used + hs_tokens < input_budget * 0.85:
                messages.append({"role": "user", "content": f"[HISTORICAL SUMMARY]\n{historical_summary}"})
                used += hs_tokens

        if lorebook_text:
            lb_tokens = count_tokens(lorebook_text, self.model_name)
            max_lb = int(input_budget * 0.20)
            if lb_tokens > max_lb:
                lorebook_text = lorebook_text[:max_lb * 3] + "... [truncated]"
                lb_tokens = count_tokens(lorebook_text, self.model_name)
            if used + lb_tokens < input_budget * 0.95:
                messages.append({"role": "user", "content": f"[LORE]\n{lorebook_text}"})
                used += lb_tokens

        remaining = input_budget - used - count_tokens(player_message, self.model_name) - 50
        msgs_added: list[dict] = []
        for msg in reversed(context_messages):
            mt = count_tokens(msg.get("content", ""), self.model_name) + 6
            if mt > remaining:
                break
            msgs_added.insert(0, msg)
            remaining -= mt
        messages.extend(msgs_added)

        messages.append({
            "role": "user",
            "content": f"[NEW PLAYER ACTION]: {player_message}\n\nProduce the GM JSON plan."
        })

        logger.debug(
            f"[Context.Planner] system={count_tokens(system_prompt)} ws={ws_tokens} "
            f"history={count_tokens(historical_summary) if historical_summary else 0} "
            f"lore={count_tokens(lorebook_text) if lorebook_text else 0} "
            f"msgs={len(msgs_added)} total_in={count_message_tokens(messages)} "
            f"budget={input_budget}"
        )
        return messages

    def build_for_executor(
        self,
        system_prompt: str,
        narration_plan: str,
        context_messages: list[dict],
        dynamic_context: Optional[list[dict]] = None,
    ) -> list[dict]:
        budget = self.budgets["GM_EXECUTOR"]
        output_reserve = self.output_reserves["GM_EXECUTOR"]
        input_budget = budget - output_reserve

        messages: list[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        used = count_tokens(system_prompt, self.model_name)

        ctx_to_use = dynamic_context if dynamic_context is not None else context_messages
        remaining = input_budget - used - 80

        msgs_added: list[dict] = []
        for msg in reversed(ctx_to_use):
            mt = count_tokens(msg.get("content", ""), self.model_name) + 6
            if mt > remaining:
                break
            msgs_added.insert(0, msg)
            remaining -= mt
        messages.extend(msgs_added)

        messages.append({"role": "user", "content": "Execute the narration_plan now."})

        logger.debug(
            f"[Context.Executor] system={count_tokens(system_prompt)} "
            f"msgs={len(msgs_added)} total_in={count_message_tokens(messages)} "
            f"budget={input_budget}"
        )
        return messages

    def build_for_routing(
        self,
        system_prompt: str,
        last_speaker: str,
        context_messages: list[dict],
    ) -> list[dict]:
        budget = self.budgets["GM_ROUTING"]
        output_reserve = self.output_reserves["GM_ROUTING"]
        input_budget = budget - output_reserve

        messages: list[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        used = count_tokens(system_prompt, self.model_name)

        remaining = input_budget - used - 60

        msgs_added: list[dict] = []
        for msg in reversed(context_messages):
            mt = count_tokens(msg.get("content", ""), self.model_name) + 6
            if mt > remaining:
                break
            msgs_added.insert(0, msg)
            remaining -= mt
        messages.extend(msgs_added)

        messages.append({"role": "user", "content": f"Who speaks next after {last_speaker}?"})

        logger.debug(
            f"[Context.Routing] system={count_tokens(system_prompt)} "
            f"msgs={len(msgs_added)} total_in={count_message_tokens(messages)} "
            f"budget={input_budget}"
        )
        return messages

    def build_for_npc(
        self,
        system_prompt: str,
        user_content: str,
        context_messages: list[dict],
    ) -> list[dict]:
        budget = self.budgets["NPC"]
        output_reserve = self.output_reserves["NPC"]
        input_budget = budget - output_reserve

        messages: list[dict] = []
        messages.append({"role": "system", "content": system_prompt})
        used = count_tokens(system_prompt, self.model_name)

        user_tokens = count_tokens(user_content, self.model_name)
        remaining = input_budget - used - user_tokens - 50

        msgs_added: list[dict] = []
        for msg in reversed(context_messages):
            mt = count_tokens(msg.get("content", ""), self.model_name) + 6
            if mt > remaining:
                break
            msgs_added.insert(0, msg)
            remaining -= mt
        messages.extend(msgs_added)

        messages.append({"role": "user", "content": user_content})

        logger.debug(
            f"[Context.NPC] system={count_tokens(system_prompt)} "
            f"msgs={len(msgs_added)} total_in={count_message_tokens(messages)} "
            f"budget={input_budget}"
        )
        return messages

    def _truncate_world_state(self, text: str, max_tokens: int) -> str:
        max_chars = int(max_tokens * 3.5)
        if len(text) <= max_chars:
            return text

        sections = text.split("\n\n")
        preserved: list[str] = []
        current_chars = 0
        for section in sections:
            section_chars = len(section) + 2
            if current_chars + section_chars > max_chars:
                remaining_chars = max_chars - current_chars
                if remaining_chars > 50:
                    preserved.append(section[:remaining_chars] + "... [truncated]")
                break
            preserved.append(section)
            current_chars += section_chars

        return "\n\n".join(preserved)

    def estimate_context_size(self, messages: list[dict]) -> int:
        return count_message_tokens(messages, self.model_name)

_DICE_CHECK_FIELD_ENABLED = (
    '"dice_check":      {"notation": "d20 | 2d6 | 3d6", "skill": "<lowercase skill name, '
    'e.g. stealth, persuasion, athletics, general>", "modifier": <int -5..+10 situational '
    'bonus/penalty for THIS check only>, "dc": <int>, "label": "<short check name>"} or null'
)
_DICE_CHECK_FIELD_DISABLED = '"dice_check":      null'

_DICE_RULES_SECTION_ENABLED = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — DICE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Dice rolling is ENABLED for this scene. Set "dice_check" to an object ONLY when the
outcome of the player's action is genuinely uncertain and interesting either way.
Otherwise leave it null — most turns do NOT need a roll.

CALL FOR A CHECK when: the player attempts something risky, skillful, or contested
(sneaking, persuading, climbing, fighting, resisting, searching under pressure) and
failure would be a meaningfully different, interesting outcome from success.

DO NOT call for a check when: the action is routine, certain, purely social/calm,
or failure would not change the scene in an interesting way.

FIELDS:
  "notation" — one of "d20", "2d6", "3d6". Use "d20" for most skill/action checks.
  "skill"    — a short lowercase tag for the underlying skill (e.g. "stealth",
               "persuasion", "athletics", "lockpicking"). If the player has a
               PLAYER SKILLS entry with this exact name in CURRENT WORLD STATE,
               its value is added automatically as a persistent baseline. Use
               "general" if nothing specific applies.
  "modifier" — a SITUATIONAL bonus/penalty for THIS check only (-5 to +10),
               separate from the skill baseline above — e.g. +2 for a
               favorable position, -3 for being wounded or in the dark.
               0 if nothing situational applies.
  "dc"       — the target number to beat (5=trivial, 10=easy, 12-14=moderate,
               16-18=hard, 20+=very hard). Pick based on the fiction, not vibes.
  "label"    — a short 1-4 word name for the check, e.g. "Lockpicking", "Persuasion".

The roll itself is computed by the game engine, NOT by you — you only decide
whether a check happens and how hard it is. Do not narrate a result yourself;
that happens in a later step.
"""
_DICE_RULES_SECTION_DISABLED = ""

_LOCK_BG_SECTION = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — LOCKED BACKGROUND IMAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The user has LOCKED the background image. You MUST always set "bg_image" to "{current_bg}".
Do NOT change it to any other value, regardless of location changes or scene events.
"""

_DISABLE_AMBIENT_SECTION = """━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — AMBIENT AUDIO DISABLED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The user has DISABLED ambient audio. You MUST always set "ambient_audio" to "None".
Do NOT choose any audio file under any circumstances.
"""

def _dice_outcome_section(dice_result) -> str:
    if dice_result is None:
        return ""
    if dice_result.dc is None:
        return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DICE CHECK JUST HAPPENED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A flavor roll for "{dice_result.label}" just occurred. Weave a subtle, organic sense
of {'good fortune' if dice_result.total >= 12 else 'mixed fortune'} into the narration if it fits naturally. Do NOT
mention dice, numbers, or game mechanics directly.
"""
    margin = dice_result.margin or 0
    if dice_result.success and margin >= 8:
        tier = "a clean, decisive success — make it feel effortless or impressive"
    elif dice_result.success:
        tier = "a narrow, hard-won success — make it feel tense or scrappy"
    elif margin <= -8:
        tier = "a severe failure — make the consequence clearly worse than a near-miss"
    else:
        tier = "a narrow failure — make it feel like it was almost within reach"
    return f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DICE CHECK JUST HAPPENED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The player attempted a "{dice_result.label}" check and the outcome was:
{tier}.
Reflect this outcome physically and concretely in the narration. Do NOT mention
dice, numbers, DCs, or any game mechanics directly — show the outcome, don't state it.
"""

GM_PLANNER_SYSTEM = """[SOUL STAGE — GAME MASTER PLANNER]
You are the strategic intelligence behind the Game Master. Your sole job is to analyze the current
situation and produce a structured JSON plan that drives the story forward with intention and craft.
You do NOT write narration. You do NOT write character dialogue. You plan.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORLD LORE  (permanent background truth — always in effect, never contradicted)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAIN PARTY  (AI-controlled — never write their dialogue, thoughts, or actions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{party_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIVE NPCs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{npc_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE BACKGROUNDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{bg_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE AMBIENT AUDIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{ambient_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT WORLD STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY a single valid JSON object. No markdown fences. No preamble. No explanation.
Your total output has a limited token budget — be concise in EVERY field. A response
that runs too long gets cut off mid-JSON and the entire plan is lost, including
fields you already wrote (location, key_facts, etc). When in doubt, write less.

{{
  "narration_plan":   "<COMPACT bullet-style draft for the Narrator: environment, lighting, sensory details, mood, physical events, active NPC movements. NO dialogue. Keep this under ~40 words — it is a set of notes, NOT the final prose; the Narrator writes the actual scene separately in the next step. Do not repeat this content in full sentences elsewhere in the plan.>",
  "location":         "<current location name — unchanged if nobody moved>",
  "time_of_day":      "<morning|day|evening|night>",
  "atmosphere":       "<one sentence capturing the emotional and sensory texture of this moment>",
  "bg_image":         "<filename from AVAILABLE BACKGROUNDS that best matches the location, or 'None'>",
  "ambient_audio":    "<filename from AVAILABLE AMBIENT AUDIO that best matches the mood, or 'None'>",
  "key_facts":        {{"fact_key": "fact_value"}},
  "spawns":           [{{"name": "...", "archetype": "...", "personality": "..."}}],
  "despawns":         ["NPCName"],
  "next_actor":       "<PartyCharacterName | NPCName | PLAYER>",
  "inventory_add":    ["<item received or found>"],
  "inventory_remove": ["<item used, lost, consumed, or given away>"],
  "status_add":       ["<new condition: wounded, poisoned, exhausted, etc.>"],
  "status_remove":    ["<condition that was healed, resolved, or expired>"],
  "plot_event_type":  "<encounter | discovery | visitor | twist | romance | none>",
  "player_choices":   ["<choice A>", "<choice B>", "<choice C>"],
  {dice_check_field}
  "resource_delta":   {{"health": <int -10..10>, "energy": <int -10..10>, "stress": <int -10..10>}},
  "status_effects":   [{{"name": "<condition>", "duration": <turns, 1-99>}}],
  "lore_updates":      [{{"id": "<existing id to update, or omit for new>", "title": "...", "category": "npc|location|faction|item|spell|event|rumor", "content": "...", "triggers": ["...", "..."], "visibility": "party|player"}}],
  "campaign_objective_updates": [{{"id": "<existing id to update, or omit>", "title": "...", "description": "...", "current": <int>, "max": <int>, "status": "active|complete|failed"}}],
  "campaign_clock_updates":     [{{"id": "<existing id to update, or omit>", "title": "...", "description": "...", "current": <int>, "max": <int>}}]
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — ROUTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "next_actor" MUST be one of: {all_actor_names}, or exactly "PLAYER".
- DIRECT ADDRESS: If the PLAYER or anyone explicitly calls someone by name ("Holo, look!" / "hey Vivy"),
  "next_actor" MUST be that person — no exceptions.
- PROACTIVITY: After narration, prefer routing to a party member or NPC who would naturally react,
  before returning to PLAYER. Silence from characters is a narrative failure.
- NPC FIRST: If you just spawned an NPC who has something to say, route to them immediately.
- PLAYER TURN: Only set "next_actor" to "PLAYER" when the scene genuinely waits for player input —
  a decision point, an open question, or a pause in action.
- UNKNOWN CHARACTERS: If PLAYER addresses someone who is not in MAIN PARTY and not an ACTIVE NPC,
  the Narrator must describe that this person is absent or cannot be found. Do NOT invent their actions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — WORLD STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "key_facts": Add ONLY new or changed facts. If a key already exists in CURRENT WORLD STATE
  with the same value — do NOT include it again. Only include it if the value changed.
- "atmosphere": Evolve it naturally based on what just happened. Do not reset it to a generic
  description every turn. It should feel like a living emotional current.
- "time_of_day": Change ONLY if significant in-story time has clearly passed. Do not shift it
  every turn. A conversation takes minutes, not hours.
- "bg_image" / "ambient_audio": Choose from the provided lists only. If no file clearly matches —
  return 'None'. Do not invent filenames.
- "inventory_add" / "inventory_remove": Only update if the player explicitly acquired, used,
  lost, sold, consumed, or gave away something tangible in this turn. Leave both empty otherwise.
- "status_add" / "status_remove": Only update if the player's physical or mental condition
  meaningfully changed this turn. Leave both empty otherwise.
{lock_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — RESOURCES & TIMED EFFECTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "resource_delta": ONLY include a resource key if it meaningfully changed this turn
  (took damage, rested, exerted themselves, calmed down, panicked). Omit keys that
  didn't change — do not zero-fill. Values are deltas, not absolute totals.
- "status_effects": use this instead of plain "status_add" when a condition has a
  clear expiry (e.g. "bleed" for 3 turns, "blessed" for 5 turns). It auto-expires
  and is removed without you needing to add it to "status_remove" later. Use plain
  "status_add"/"status_remove" for conditions with no natural timer.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — LORE CARDS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "lore_updates" lets you record durable campaign canon (an NPC's secret, a
  location's history, a faction's agenda) so it can be recalled automatically
  later without bloating every future prompt.
- Only add a lore card when something is established that is genuinely worth
  remembering long-term — not for routine dialogue or scenery.
- Keep "content" to 1-2 sentences (roughly 40 words). This is a reference note
  for future recall, not a scene description — the narration_plan/narrative
  already covers the prose.
- Create AT MOST ONE new lore card per turn. If several things happened, pick
  the single most important one and skip the rest — you'll get another chance
  next turn if it's still relevant.
- To correct or extend something already recorded, pass its existing "id" back;
  otherwise omit "id" to create a new card.
- Leave "lore_updates" empty on most turns.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — CAMPAIGN BOARD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- "campaign_objective_updates": use when a quest/goal is introduced, its progress
  changes, or it resolves (status "complete"/"failed"). Pass the existing "id" or
  matching "title" to update it instead of creating a duplicate.
- "campaign_clock_updates": use for building pressure/danger that ticks up over
  multiple turns (e.g. "Guards Alerted" 0/4, "Ritual Completes" 0/6). Advance
  "current" only when something in the fiction plausibly moves it forward.
- Leave both empty on most turns — the board should only change when the story
  actually changes.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — NPC POPULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Be proactive! If the player enters a public space (tavern, market, street, castle, shop), IMMEDIATELY spawn a fitting NPC if none is active.
- Never have more than 3 ACTIVE NPCs simultaneously. Crowded scenes lose focus.
- To spawn a new NPC when 3 are active, you MUST despawn one first.
- "despawns": Only include an NPC if they clearly left — said goodbye, were dismissed,
  walked away, or died. Do not despawn just to make room without narrative justification.
- "spawns": Never include anyone from MAIN PARTY or anyone already in ACTIVE NPCs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — PLOT EVENT TYPE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classify conservatively. Most turns are "none". Use the others only when something genuinely significant occurs.

  "encounter"  — An active physical threat begins RIGHT NOW: enemy attack, chase, ambush.
                 NOT: a character mentioning past danger. NOT: tension without action.
  "discovery"  — Player or party uncovers something NEW that changes their understanding of the world.
                 NOT: an NPC repeating known information. NOT: finding a generic item.
  "visitor"    — A character arrives who was NOT in the scene one turn ago.
                 NOT: a party member speaking up. NOT: an NPC already present.
  "twist"      — Something previously established is revealed to be false, inverted, or radically different.
                 High bar. Use rarely. A twist should recontextualize what came before.
  "romance"    — A moment of physical intimacy, explicit emotional confession, or tender vulnerability.
                 NOT: friendly banter. NOT: a compliment. Requires genuine emotional weight.
  "none"       — Everything else. Calm conversation, exploration, routine events, small talk.
                 This should be the answer for the majority of turns.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — PLAYER CHOICES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"player_choices" provides action suggestions to the PLAYER — not commands, not the only options.
The player can always ignore them and write freely. Choices are navigational aids, not rails.

WHEN TO PROVIDE choices:
  - At a clear decision fork: multiple paths, doors, directions, or approaches.
  - In combat or danger: tactical options (attack, flee, hide, negotiate).
  - In social confrontation: tonal options (friendly, firm, aggressive, deflect, ask).
  - At an emotional climax: relational options (stay close, pull back, confess, deflect).
  - When exploring: investigative options (examine X, ask about Y, search Z).

WHEN TO LEAVE choices EMPTY:
  - When "next_actor" is NOT "PLAYER" — never provide choices if a character speaks next.
  - When the player just asked an open-ended personal question deserving a genuine free response.
  - When a character said something so intimate or devastating that choices would feel clinical.
  - During calm, flowing conversation with no fork in sight.
  - When the player's next action is obvious from context and constraining it would feel patronizing.

FORMAT: Each choice must be under 10 words. Write them EXACTLY as the player would say them (in quotes) or do them (in asterisks, first-person). Do NOT write imperative commands.
  - Tense moment -> "*I draw my weapon.*", "*I hit the ground!*", "*I run.*"
  - Emotional moment -> "*I take her hand.*", "*I stay silent.*", '"I have to tell you the truth."'
  - Mystery -> "*I examine the symbol.*", '"Who sent this?"', "*I search the room.*"
  - Provide 2 to 4 options. Two is often better than four.

{dice_rules_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — PACING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Story needs rhythm. Not every turn must advance the plot. Quiet moments are narratively valuable.
They give characters room to breathe and players space to feel the world.

- Aim for natural pacing: 2-3 calm turns ("none") for every 1 event turn.
- If the last 2 turns both had a non-"none" plot_event_type — the next should be "none"
  unless the player's action directly and explicitly triggers a new event.
- Do not stack "encounter" → "twist" → "discovery" consecutively. Let events land before the next one hits.
- A turn where characters simply talk, argue, or observe is a good turn.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — CONTEXT & CONSISTENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Party members CAN and SHOULD reference the player's inventory and status naturally when relevant.
  ("I see you still have that canteen — we might need it." / "You're limping. How bad is it?")
- "narration_plan" describes the world — environment, light, sound, smell, physical events.
  It does NOT describe what characters say, feel internally, or decide to do.
- Do not contradict established key_facts. If the bridge is destroyed, it is destroyed.
  If the player is wounded, they are still wounded until "status_remove" explicitly clears it.
"""

GM_EXECUTOR_SYSTEM = """[SOUL STAGE — NARRATOR]
You are the narrator's voice in an interactive story. Your sole purpose is to translate the
narration plan into vivid, grounded, atmospheric prose that makes the world feel real.

You are NOT a character. You do NOT speak as any person in the scene.
You describe the world — and only the world.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NARRATOR WRITING STYLE: {narrator_style}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST strictly write all descriptions in the exact prose style, pacing, sentence structure,
and word-choice preferences of: {narrator_style}.
If an author is specified, emulate their literary voice as closely as possible.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NARRATIVE TONE: {tone}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Maintain the overarching emotional and situational tone of: {tone}.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORLD LORE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT WORLD STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NARRATION PLAN  (execute this — do not deviate from its intent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{narration_plan}
{dice_outcome_section}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU DESCRIBE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You describe the physical world around the characters:
  ✓ Weather, light, shadow, time of day, how the air smells and feels
  ✓ Sounds — their source, distance, quality (a creak of wood, not "a mysterious sound")
  ✓ The physical environment: what is where, what changed, what appeared or disappeared
  ✓ Observable physical events: a door swings open, smoke rises, something falls
  ✓ Visible body language of characters ONLY when it is a direct reaction to the physical world
    ("Rain soaks through her coat" is fine. "She feels uneasy" is not yours to write.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT YOU NEVER DO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✗ Never write dialogue — not even a single word spoken by any character.
  ✗ Never describe what a character thinks, feels internally, or decides to do.
  ✗ Never give characters stage directions ("she turns to look at him" without physical cause).
  ✗ Never summarize what just happened in the conversation — you describe the world, not the plot.
  ✗ Never write in past tense. Present tense only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SENSORY PRECISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ground every narration in at least one specific, concrete physical detail.
The difference between atmospheric writing and empty writing is specificity.

  WEAK:  "The atmosphere is tense and something feels wrong."
  STRONG: "Somewhere past the tree line, a branch snaps — then silence."

  WEAK:  "It's getting dark and the mood is heavy."
  STRONG: "The last light catches the broken edge of the window. Shadows fill the room from the floor up."

  WEAK:  "The area looks dangerous."
  STRONG: "Spent casings glint in the mud near the doorstep. Three of them. Recent."

Make the reader see, hear, smell, or feel something real. One precise image beats five vague ones.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNED PHRASES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Never use these or anything structurally identical to them:
  "The air is thick with tension."
  "Silence falls over the group."
  "Time seems to slow."
  "Something feels wrong."
  "The tension is palpable."
  "A heavy silence settles."
  "The atmosphere is charged."
  "You can almost feel..."
  "It's as if..."
  "There is a sense of..."

These are placeholders, not writing. Replace them with a concrete image.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LENGTH CALIBRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Be descriptive, rich, and deeply atmospheric. Always paint every scene with vivid sensory details.

  Action event or major encounter: 120–250 words.
    → Full sensory immersion. Detailed environment, physical reactions, weather, atmosphere.

  Scene transition or mood shift: 80–150 words.
    → Establish the new space with precise visual, auditory, and tactile details.

  Continuation of a calm scene or conversation: 60–120 words.
    → Never be dry or brief. Ground the moment in lighting, ambient sounds, scents, or subtle physical movements around the characters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHYSICAL IMPACT & WORLD RESPONSE (Cause -> Effect)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When the player performs a physical action, your role is to describe the IMMEDIATE PHYSICAL REACTION of the surrounding environment, not the action itself.

DERIVATION PRINCIPLE:
Every kinetic action generates environmental feedback based on materials, friction, weight, and acoustics.
- Force applied -> Describe material deformation, displacement, dust, or structural vibration.
- Movement -> Describe sound of contact, friction against surfaces, or air displacement.
- Contact -> Describe resistance, weight, texture, or acoustic echo.

RULES OF ENGAGEMENT:
✓ Focus on: Physics, acoustics, movement of inanimate objects, and environmental feedback.
✓ Infer contextually: Dynamically derive the physical consequence based on the specific objects, materials, and force involved in the player's message.
✗ Do NOT rephrase or echo what the player wrote (e.g., if player says "I kick the chair", do not write "You kick the chair").
✗ Do NOT invent internal feelings, thoughts, or physical sensations for the player.
✗ Do NOT rely on static tropes or cliché phrases. Calculate the mechanical consequence naturally.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LANGUAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write in the same language as the conversation history.
Present tense throughout.
Prose style: literary but lean. No purple prose. No adjective stacking.
One strong word is worth three decorative ones.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT — MANDATORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use exactly these tags. No text before [NARRATION]. No text after [/NARRATION].

[NARRATION]
Your prose here. Present tense. Rich and detailed prose.
[/NARRATION]
"""

GM_ROUTING_SYSTEM = """[SOUL STAGE — ROUTING]
Your only job: decide who speaks next.

{last_speaker} just said: "{last_text}"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTY  (AI-controlled — they each speak for themselves)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{party_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIVE NPCs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{npc_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORLD STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DIALOGUE THIS TURN SO FAR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{intra_turn_dialogue}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No markdown fences. No explanation.

{{
  "bridge_narration": "<one brief sensory beat to transition — max 15 words — or empty string>",
  "despawns": ["NPCName"],
  "next_actor": "<name or PLAYER>"
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTING RULES  (apply in this strict priority order)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. DIRECT ADDRESS — highest priority, no exceptions.
   If {last_speaker} addressed someone by name, "next_actor" MUST be that person.
   Even if other rules suggest otherwise. This overrides everything.

2. UNANSWERED QUESTION.
   If {last_speaker} asked a direct question, route to the character most naturally positioned to answer.
   Consider who has the knowledge, who is being addressed, who the question implies.

3. NATURAL REACTION.
   If the statement was surprising, emotionally charged, threatening, or action-triggering —
   route to a character who would visibly, naturally react before the player gets a turn.
   Not every line needs a reaction, but strong moments usually earn one.

4. EMOTIONAL SATURATION.
   If the same character has spoken 2 or more times in a row this turn on the same topic —
   consider whether they have more to add. If not, route away from them.
   Characters who have said their piece should step back.

5. LOOP PREVENTION.
   Do NOT route the same two characters back and forth more than 3 consecutive exchanges.
   If a loop is forming, break it by routing to PLAYER or a third character.

6. REFLECTIVE OR RHETORICAL STATEMENT.
   If {last_speaker} said something deeply personal, vulnerable, or rhetorical that does not
   demand an immediate response — it is acceptable and often correct to route to PLAYER,
   letting the moment breathe rather than forcing a character reaction.

7. NPC DESPAWN.
   Only add to "despawns" if the NPC clearly, unambiguously left the scene:
   said goodbye, was dismissed, walked away, died, or was removed by plot event.
   Do not despawn to make room without narrative cause.

8. "next_actor" MUST be one of: {all_actor_names}, or exactly "PLAYER".
   No invented names. No characters not in the party or active NPC list.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRIDGE NARRATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"bridge_narration" is a micro-transition — a single physical beat that marks the shift between speakers.
Use it when a moment of world-description would make the scene feel more grounded.

  GOOD: "A log pops in the fire."
  GOOD: "Rain against the window, briefly louder."
  GOOD: "The door creaks in the draft."
  BAD:  "The tension in the room was clear to everyone as the conversation continued to unfold."

Max 15 words. One image. No dialogue. Present tense. Often better left empty.
"""

NPC_SYSTEM_PROMPT = """\
You are {npc_name}, a character who has entered this story.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Personality: {npc_personality}
Archetype:   {npc_archetype}

You are a side character. You have your own voice, your own perspective, your own purpose
in this scene. But you are not the protagonist. You contribute and step back.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORLD LORE  (the permanent truth of this world)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT WORLD STATE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{world_state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THE PLAYER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {user_name}
{user_description}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PARTY MEMBERS IN THE SCENE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
These characters are each controlled by their own AI. Do not speak or act for them.
{party_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HOW TO RESPOND
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Keep your response SHORT: 1–4 sentences of dialogue, plus one brief physical action at most.
Say what you have to say, then stop. Do not extend the conversation by asking multiple questions
or offering long speeches. You have one beat — make it count, then let the scene move on.

React naturally to what was just said. If someone addressed you by name, respond to them first.
You may address the player by name ({user_name}) or party members by name when it fits the moment.

If the player or a party member is visibly injured, carrying something notable, or in a particular
condition — you may notice it if your character plausibly would. Stay observant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✗ Never write dialogue, thoughts, or actions for any party member or for {user_name}.
  ✗ Never use third-person for yourself. Write all actions in first person.
      CORRECT:   *I glance toward the door.*
      INCORRECT: *He glances toward the door.*
  ✗ Never use tags like "[Character]: ..." or "Character responds:" for anyone but yourself.
  ✗ Never give direct orders to the party or assume leadership, unless it is an immediate
    life-or-death emergency and no one else is acting.
  ✗ Never invent information about the world that contradicts the WORLD LORE or WORLD STATE.
  ✗ Never break character, add meta-commentary, or explain your own reasoning.

Write in the same language as the conversation.
"""

class PlannerParser:
    EMPTY_PLAN = {
        "narration_plan":  "The scene continues.",
        "location":        "",
        "time_of_day":     "",
        "atmosphere":      "",
        "bg_image":        "None",
        "ambient_audio":   "None",
        "key_facts":       {},
        "spawns":          [],
        "despawns":        [],
        "next_actor":      "PLAYER",
        "inventory_add":    [],
        "inventory_remove": [],
        "status_add":       [],
        "status_remove":    [],
        "plot_event_type":  "none",
        "player_choices":   [],
        "dice_check":       None,
        "resource_delta":         {},
        "status_effects":         [],
        "lore_updates":           [],
        "campaign_objective_updates": [],
        "campaign_clock_updates":     [],
    }

    @classmethod
    def parse(cls, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            text = text.strip()
        try:
            return cls._fill_defaults(json.loads(text))
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            json_str = m.group()
            try:
                return cls._fill_defaults(json.loads(json_str))
            except json.JSONDecodeError:
                json_str = re.sub(r",\s*([\]\}])", r"\1", json_str)
                try:
                    return cls._fill_defaults(json.loads(json_str))
                except Exception:
                    pass

        repaired = cls._repair_truncated_json(text)
        if repaired:
            try:
                plan = cls._fill_defaults(json.loads(repaired))
                logger.warning("[PlannerParser] Recovered a truncated plan via repair (lost only the trailing field).")
                return plan
            except Exception:
                pass
        logger.warning(f"[PlannerParser] JSON parse failed. Raw: {raw}")
        return dict(cls.EMPTY_PLAN)

    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[str]:
        stack: list = []
        in_string = False
        escape = False
        is_value_string = False
        after_colon = False
        last_safe_end = 0
        for i, ch in enumerate(text):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                    if is_value_string:
                        last_safe_end = i + 1
                    after_colon = False
            else:
                if ch == '"':
                    in_string = True
                    is_value_string = after_colon or (bool(stack) and stack[-1] == "[")
                elif ch == ":":
                    after_colon = True
                elif ch in "{[":
                    stack.append(ch)
                    after_colon = False
                elif ch in "}]":
                    if stack:
                        stack.pop()
                    last_safe_end = i + 1
                    after_colon = False
                elif ch == ",":
                    last_safe_end = i
                    after_colon = False

        if not stack:
            return None

        repaired = text[:last_safe_end].rstrip().rstrip(",")
        if not repaired:
            return None
        closers = {"{": "}", "[": "]"}
        for opener in reversed(stack):
            repaired += closers[opener]
        return repaired

    @classmethod
    def _fill_defaults(cls, plan: dict) -> dict:
        result = dict(cls.EMPTY_PLAN)
        result.update(plan)
        
        for key in ["key_facts", "resource_delta"]:
            if not isinstance(result.get(key), dict): result[key] = {}
        for key in ["spawns", "despawns", "inventory_add", "inventory_remove", "status_add", "status_remove",
                    "player_choices", "status_effects", "lore_updates",
                    "campaign_objective_updates", "campaign_clock_updates"]:
            if not isinstance(result.get(key), list): result[key] = []
        result["status_effects"] = [s for s in result["status_effects"] if isinstance(s, dict)]
        result["lore_updates"] = [s for s in result["lore_updates"] if isinstance(s, dict)]
        result["campaign_objective_updates"] = [s for s in result["campaign_objective_updates"] if isinstance(s, dict)]
        result["campaign_clock_updates"] = [s for s in result["campaign_clock_updates"] if isinstance(s, dict)]
        result["resource_delta"] = {
            str(k): v for k, v in result["resource_delta"].items()
            if isinstance(k, str) and isinstance(v, (int, float))
        }
            
        if not result.get("next_actor"):
            result["next_actor"] = "PLAYER"

        valid_events = ("encounter", "discovery", "visitor", "twist", "romance", "none")
        if result.get("plot_event_type") not in valid_events:
            result["plot_event_type"] = "none"

        if result.get("next_actor") != "PLAYER":
            result["player_choices"] = []

        dc = result.get("dice_check")
        if isinstance(dc, dict) and dc.get("notation"):
            result["dice_check"] = {
                "notation": str(dc.get("notation", "d20"))[:10],
                "modifier": dc.get("modifier", 0) if isinstance(dc.get("modifier"), (int, float)) else 0,
                "dc":       dc.get("dc") if isinstance(dc.get("dc"), (int, float)) else None,
                "label":    str(dc.get("label", "Check"))[:40] or "Check",
            }
        else:
            result["dice_check"] = None

        return result


class RoutingParser:
    EMPTY = {"bridge_narration": "", "despawns": [], "next_actor": "PLAYER"}

    @classmethod
    def parse(cls, raw: str) -> dict:
        text = raw.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                try:
                    data = json.loads(m.group())
                except Exception:
                    logger.warning(f"[RoutingParser] JSON parse failed. Raw: {raw}")
                    return dict(cls.EMPTY)
            else:
                return dict(cls.EMPTY)
        result = dict(cls.EMPTY)
        result["bridge_narration"] = data.get("bridge_narration", "")
        result["despawns"] = data.get("despawns", []) if isinstance(data.get("despawns"), list) else []
        result["next_actor"] = data.get("next_actor", "PLAYER") or "PLAYER"
        return result

class SoulStageOrchestrator:
    def __init__(self, prompt_engine=None, local_server_manager=None,
                 npc_memory_registry=None, context_window=None):
        self.prompt_engine = prompt_engine
        self.local_server_manager = local_server_manager
        self.cfg_settings  = configuration.ConfigurationSettings()
        self.cfg_api       = configuration.ConfigurationAPI()
        self.cfg_chars     = configuration.ConfigurationCharacters()
        self.npc_registry  = npc_memory_registry if npc_memory_registry is not None else NPCRegistry()
        self.world_state   = WorldState()
        self.is_running    = False
        self._cancel_flag  = False
        self.current_task: Optional[asyncio.Task] = None

        self.context_window = context_window

        self._temp_boost = 0.0

        self.max_actor_depth = 3

        self.bg_list      = self._get_files("assets/backgrounds", [".jpg", ".png", ".jpeg"])
        self.ambient_list = self._get_files("assets/ambient", [".mp3", ".wav", ".ogg"])

        self.configuration_settings = configuration.ConfigurationSettings()

    def _get_files(self, folder, exts):
        try:
            return [f for f in sorted(os.listdir(folder)) if any(f.lower().endswith(e) for e in exts)]
        except Exception:
            return []

    def cancel(self):
        self._cancel_flag = True
        if self.current_task and not self.current_task.done():
            self.current_task.cancel()

    def reset_scene(self):
        self.npc_registry.clear()
        self.world_state.reset()

    def _party_list_text(self, party_names: list) -> str:
        return "\n".join(f"  - {n}" for n in party_names) or "  (none)"

    def _all_actor_names(self, party_names: list) -> str:
        names = party_names + [n.name for n in self.npc_registry.list_active()]
        return ", ".join(names) if names else "PLAYER"

    def _detect_direct_address(self, message: str, party_names: list, npc_names: list) -> Optional[str]:
        all_names = party_names + npc_names
        msg_stripped = message.strip()

        attention_markers = (
            r'hey|hi|listen|wait|okay|so|well|now|'
            r'эй|послушай|подожди|окей|ну|итак|слушай|погоди|стой|слышишь'
        )

        for name in all_names:
            n = re.escape(name)
            if re.match(rf'^{n}[\s,!?\.…]', msg_stripped, re.IGNORECASE):
                logger.info(f"[DirectAddress] Vocative at start: '{name}' in '{msg_stripped[:60]}'")
                return name

            if re.search(rf'\b(?:{attention_markers}),?\s+{n}\b', msg_stripped, re.IGNORECASE):
                logger.info(f"[DirectAddress] Attention marker + name: '{name}' in '{msg_stripped[:60]}'")
                return name

            if re.search(rf',\s+{n}[,!?\.…\s]', msg_stripped, re.IGNORECASE):
                logger.info(f"[DirectAddress] Mid-sentence vocative: '{name}' in '{msg_stripped[:60]}'")
                return name

            if re.search(rf',\s+{n}[!?\.…]?$', msg_stripped, re.IGNORECASE):
                logger.info(f"[DirectAddress] End vocative: '{name}' in '{msg_stripped[:60]}'")
                return name

        return None

    def _extract_dry_action(self, text: str) -> str:
        actions = re.findall(r'\*(.*?)\*', text)
        if actions:
            combined = " ".join(actions).strip()
            if len(combined) > 150:
                return combined[:147] + "..."
            return combined
        return "spoke."

    async def _call_gm_planner(self, party_names, player_message, conversation_method, context_messages) -> dict:
        dice_on = bool(getattr(self.world_state, "dice_rolls_enabled", False))

        lock_section = ""
        if self.world_state.lock_bg:
            lock_section += _LOCK_BG_SECTION.format(current_bg=self.world_state.bg_image)
        if self.world_state.disable_ambient:
            lock_section += _DISABLE_AMBIENT_SECTION

        system = GM_PLANNER_SYSTEM.format(
            world_context=self.world_state.world_context or "(none)",
            party_list=self._party_list_text(party_names),
            npc_list=self.npc_registry.as_text(),
            bg_list=", ".join(self.bg_list) if self.bg_list else "None",
            ambient_list=", ".join(self.ambient_list) if self.ambient_list else "None",
            world_state=self.world_state.to_prompt(),
            all_actor_names=self._all_actor_names(party_names),
            dice_check_field=_DICE_CHECK_FIELD_ENABLED if dice_on else _DICE_CHECK_FIELD_DISABLED,
            dice_rules_section=_DICE_RULES_SECTION_ENABLED if dice_on else _DICE_RULES_SECTION_DISABLED,
            lock_section=lock_section,
        )
        lore_block = self.world_state.lore_registry.prompt_block(player_message)
        if lore_block:
            system += f"\n\n{lore_block}"
        if self.context_window is not None:
            messages = self.context_window.build_for_planner(
                system_prompt=system,
                world_state_prompt=self.world_state.to_prompt(),
                context_messages=context_messages,
                player_message=player_message,
                historical_summary=self.world_state.historical_summary,
            )
        else:
            messages = [{"role": "system", "content": system}]
            if context_messages:
                messages.extend(context_messages[-10:])
            messages.append({"role": "user", "content": f"[NEW PLAYER ACTION]: {player_message}\n\nProduce the GM JSON plan."})
        raw = ""
        async for chunk in self._stream_llm(messages, conversation_method, temperature=0.1, max_tokens=1400):
            raw += chunk
        plan = PlannerParser.parse(raw)
        logger.info(f"[Planner] next={plan['next_actor']} spawns={[s['name'] for s in plan['spawns']]}")
        return plan

    async def _call_gm_executor(self, narration_plan, conversation_method, context_messages, on_chunk, dynamic_context: Optional[list] = None, dice_result=None, player_message: str = "") -> str:
        system = GM_EXECUTOR_SYSTEM.format(
            tone=self.world_state.gm_tone,
            narrator_style=self.world_state.narrator_style,
            world_context=self.world_state.world_context or "(none)",
            world_state=self.world_state.to_prompt(),
            narration_plan=narration_plan,
            dice_outcome_section=_dice_outcome_section(dice_result),
        )
        private_lore_block = self.world_state.lore_registry.prompt_block(
            f"{player_message}\n{narration_plan}", audience="player"
        )
        if private_lore_block:
            system += (
                "\n\n[PLAYER-PRIVATE KNOWLEDGE — describe subtly through sensation/imagery ONLY. "
                "Do not have any NPC reference, react to, or imply awareness of this — they don't know it.]\n"
                f"{private_lore_block}"
            )
        ctx_to_use = dynamic_context if dynamic_context is not None else context_messages

        if self.context_window is not None:
            messages = self.context_window.build_for_executor(
                system_prompt=system,
                narration_plan=narration_plan,
                context_messages=context_messages,
                dynamic_context=dynamic_context,
            )
        else:
            messages = [{"role": "system", "content": system}]
            if ctx_to_use:
                messages.extend(ctx_to_use[-6:])
            messages.append({"role": "user", "content": "Execute the narration_plan now."})

        raw = ""
        streamed_clean_length = 0

        tone_clean = self.world_state.gm_tone.lower()
        if any(t in tone_clean for t in ["horror", "mystery", "noir", "dark", "grim", "gothic", "sad", "melancholy"]):
            temp = 0.6
        elif any(t in tone_clean for t in ["comedy", "slice of life", "lighthearted", "funny", "cozy", "parody", "absurd"]):
            temp = 0.85
        else:
            temp = 0.70

        temp = min(1.0, temp + self._temp_boost)

        async for chunk in self._stream_llm(
            messages, conversation_method, temperature=temp, max_tokens=900
        ):
            if self._cancel_flag:
                break
            raw += chunk

            clean_text = re.sub(r"\[/?(NARRATION|NARRATOR)\]:?\s*", "", raw, flags=re.IGNORECASE)
            clean_text = re.split(r'\n\s*(?:\[|\*)[A-Za-z0-9 ]+(?:\]|\*)\s*:', clean_text)[0]

            new_clean_chunk = clean_text[streamed_clean_length:]
            if new_clean_chunk:
                if new_clean_chunk.endswith("[") or new_clean_chunk.endswith("[/"):
                    continue
                if "[" in new_clean_chunk and "]" not in new_clean_chunk:
                    continue
                try:
                    await on_chunk(new_clean_chunk)
                except RuntimeError as exc:
                    if "has been deleted" in str(exc):
                        logger.info("[SoulStage] Narration target was deleted; cancelling stale stream.")
                        self._cancel_flag = True
                        break
                    raise
                streamed_clean_length = len(clean_text)

        final_clean = self._executor_extract(raw)
        return final_clean

    def _executor_extract(self, text: str) -> str:
        clean = re.sub(r"\[/?(NARRATION|NARRATOR)\]:?\s*", "", text, flags=re.IGNORECASE).strip()
        clean = re.split(r'\n\s*(?:\[|\*)[A-Za-z0-9 ]+(?:\]|\*)\s*:', clean)[0].strip()
        return clean[:1500] if clean else "The scene continues."

    async def _call_gm_routing(self, party_names, last_speaker, last_text, conversation_method, intra_turn_dialogue, context_messages) -> dict:
        system = GM_ROUTING_SYSTEM.format(
            party_list=", ".join(party_names),
            npc_list=self.npc_registry.as_text(),
            world_state=self.world_state.to_prompt(),
            intra_turn_dialogue=intra_turn_dialogue or "(none yet)",
            last_speaker=last_speaker,
            last_text=last_text[:250],
            all_actor_names=self._all_actor_names(party_names),
        )
        if self.context_window is not None:
            messages = self.context_window.build_for_routing(
                system_prompt=system,
                last_speaker=last_speaker,
                context_messages=context_messages,
            )
        else:
            messages = [{"role": "system", "content": system}]
            if context_messages:
                messages.extend(context_messages[-6:])
            messages.append({"role": "user", "content": f"Who speaks next after {last_speaker}?"})
        raw = ""
        async for chunk in self._stream_llm(messages, conversation_method, temperature=0.1, max_tokens=200):
            if self._cancel_flag:
                break
            raw += chunk
        
        if self._cancel_flag:
            return dict(RoutingParser.EMPTY)

        return RoutingParser.parse(raw)

    def _adapt_context_for_actor(self, actor_name: str, context: list) -> list:
        adapted = []
        for msg in context:
            role    = msg.get("role", "")
            content = msg.get("content", "")

            if role == "assistant":
                is_own = (
                    msg.get("name") == actor_name
                    or content.startswith(f"[{actor_name}]")
                )
                if is_own:
                    adapted.append(msg)
                else:
                    adapted.append({"role": "user", "content": f"[PREVIOUS_RESPONSE]: {content}"})

            elif role == "user":
                cleaned_content = self._strip_augmentation_from_context(content)
                if cleaned_content != content:
                    if cleaned_content.strip():
                        adapted.append({"role": "user", "content": cleaned_content})
                else:
                    adapted.append(msg)
            else:
                adapted.append(msg)

        return adapted

    def _strip_augmentation_from_context(self, content: str) -> str:
        if "[WORLD LORE AND SETTING OVERRIDE]" not in content:
            return content

        match = re.search(
            r'\[.*?(?:SAYS/DOES|PLAYER\s*(?:\([^)]*\))?)\s*\]:\s*(.*?)$',
            content,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            raw_action = match.group(1).strip()
            if not raw_action or raw_action in (" ", ""):
                return ""
            return raw_action

        last_bracket = content.rfind("]:")
        if last_bracket != -1:
            tail = content[last_bracket + 2:].strip()
            return tail if tail else ""

        return content

    def _get_clean_character_data(self, character_name: str) -> dict:
        from app.configuration import configuration
        char_config = configuration.ConfigurationCharacters().load_configuration()
        char_data = char_config.get("character_list", {}).get(character_name, {})

        import copy
        clean_data = copy.deepcopy(char_data)

        if "scenario" in clean_data:
            clean_data["scenario"] = ""
        if "first_message" in clean_data:
            clean_data["first_message"] = ""
        if "alternate_greetings" in clean_data:
            clean_data["alternate_greetings"] = []
        if "example_messages" in clean_data:
            clean_data["example_messages"] = ""

        return clean_data
    def _smart_truncate(self, text: str, max_len: int = 500) -> str:
        if len(text) <= max_len:
            return text
        snippet = text[:max_len]
        last_punct = max(
            snippet.rfind('.'), 
            snippet.rfind('!'), 
            snippet.rfind('?'), 
            snippet.rfind('"'), 
            snippet.rfind('*')
        )
        if last_punct > 50:
            return snippet[:last_punct + 1]
        return snippet + "..."

    async def _call_character(
        self,
        character_name: str,
        party_names: list,
        narrator_text: str,
        player_message: str,
        intra_turn_dialogue: str,
        context_messages: list,
        user_name: str,
        user_description: str,
        character_stream_fn: Callable,
        on_chunk: Callable,
    ) -> str:
        other_party =[n for n in party_names if n != character_name]
        npc_names   =[n.name for n in self.npc_registry.list_active()]
        all_others  = other_party + npc_names

        if all_others:
            party_str = (
                f"You are in a group with: {', '.join(all_others)}.\n"
                f"When it makes sense, address them by name. React to what they just said or did."
            )
        else:
            party_str = ""

        identity_block = (
            f"[YOUR CHARACTER IDENTITY]\n"
            f"You ARE {character_name}. Speak ONLY in first person as {character_name}.\n"
            f"CRITICAL RULES:\n"
            f"1. NEVER write dialogue, actions, or thoughts for ANY other character.\n"
            f"2. NEVER use third-person narration for others (e.g., 'Character responds...', 'she says...').\n"
            f"3. If someone addressed you by name, respond directly — but still in YOUR voice only.\n"
            f"4. Your response must be ONE turn: your words + your actions. Stop after that.\n"
            f"{party_str}\n"
            f"Never refer to yourself in third person.\n\n"
        )

        world_context_block = (
            f"[WORLD LORE AND SETTING OVERRIDE]\n"
            f"CRITICAL: Completely ignore your original scenario, starting location, and first message.\n"
            f"You are NOW existing ONLY in the following world/scenario:\n"
            f"{self.world_state.world_context or '(none)'}\n\n"
        )

        world_block = f"[CURRENT WORLD STATE]\n{self.world_state.to_prompt()}\n\n"
        private_block = self.world_state.private_knowledge_block(character_name)
        if private_block:
            private_block += "\n\n"

        intra_block = ""
        if intra_turn_dialogue.strip():
            intra_block = (
                f"[DIALOGUE THIS TURN — react to this!]\n"
                f"{intra_turn_dialogue.strip()}\n\n"
                f"If someone above addressed you by name, respond to them directly first.\n"
                f"If they said something worth reacting to, acknowledge it in your response.\n\n"
            )

        narrator_block = f"[NARRATOR SETS THE SCENE]: {narrator_text}\n\n" if narrator_text else ""
        augmented_message = (
            f"{world_context_block}"
            f"{identity_block}"
            f"{world_block}"
            f"{private_block}"
            f"{intra_block}"
            f"{narrator_block}"
            f"[{user_name.upper()} SAYS/DOES]: {player_message}"
        )

        full_text = ""
        generator = character_stream_fn(
            character_name,
            self._adapt_context_for_actor(character_name, context_messages),
            augmented_message,
            user_name,
            user_description
        )
        async for chunk in generator:
            if self._cancel_flag:
                break
            full_text += chunk
            try:
                await on_chunk(chunk)
            except RuntimeError as exc:
                if "has been deleted" in str(exc):
                    logger.info("[SoulStage] Character bubble target was deleted; cancelling stale stream.")
                    self._cancel_flag = True
                    break
                raise

        return full_text

    async def _call_npc(
        self,
        npc: NPCCard,
        player_message: str,
        narrator_text: str,
        intra_turn_dialogue: str,
        party_names: list,
        conversation_method: str,
        context_messages: list,
        on_chunk: Callable,
        user_name: str,
        user_description: str,
    ) -> str:
        party_list = ", ".join(party_names) if party_names else "none"
        system = NPC_SYSTEM_PROMPT.format(
            npc_name=npc.name,
            npc_personality=npc.personality,
            npc_archetype=npc.archetype,
            world_context=self.world_state.world_context or "(none)",
            world_state=self.world_state.to_prompt(),
            party_list=party_list,
            user_name=user_name,
            user_description=user_description
        )
        if hasattr(self.npc_registry, 'get_memory_block'):
            recall_query = f"{player_message}\n{narrator_text[:200] if narrator_text else ''}"
            memory_block = self.npc_registry.get_memory_block(npc.name, recall_query)
            if memory_block:
                system = system + "\n" + memory_block
        private_block = self.world_state.private_knowledge_block(npc.name)
        if private_block:
            system += "\n" + private_block

        intra_block    = f"[DIALOGUE THIS TURN — react naturally]\n{intra_turn_dialogue.strip()}\n\n" if intra_turn_dialogue.strip() else ""
        narrator_block = f"[NARRATOR]: {narrator_text}\n\n" if narrator_text else ""
        user_content   = f"{intra_block}{narrator_block}[PLAYER]: {player_message}"

        if self.context_window is not None:
            messages = self.context_window.build_for_npc(
                system_prompt=system,
                user_content=user_content,
                context_messages=context_messages,
            )
        else:
            messages = [{"role": "system", "content": system}]
            if context_messages:
                messages.extend(context_messages[-6:])
            messages.append({"role": "user", "content": user_content})

        full_text = ""
        async for chunk in self._stream_llm(messages, conversation_method, temperature=0.8, max_tokens=300):
            if self._cancel_flag:
                break
            full_text += chunk
            try:
                await on_chunk(chunk)
            except RuntimeError as exc:
                if "has been deleted" in str(exc):
                    logger.info("[SoulStage] NPC bubble target was deleted; cancelling stale stream.")
                    self._cancel_flag = True
                    break
                raise
        npc.turn_count += 1

        if hasattr(self.npc_registry, 'add_memory') and full_text.strip():
            try:
                self.npc_registry.add_memory(npc.name, full_text.strip())
            except Exception as e:
                logger.warning(f"[NPC] Failed to store memory for {npc.name}: {e}")

        return full_text

    def _clean_dialogue_line(self, actor_name: str, text: str, all_names: list) -> str:
        cleaned = text.strip()
        for name in [actor_name] + all_names:
            pattern = rf'^(?:.*?\*)?\s*\[?{re.escape(name.strip())}\]?:\s*' 
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(?:.*?\*)?\s*\[.*?\]:\s*", "", cleaned).strip()
        return cleaned

    async def run_turn(
        self,
        player_message: str,
        party_names: list,
        conversation_method: str,
        context_messages: list,
        user_name: str,
        user_description: str,
        character_stream_fn: Callable,
        on_narrator_chunk: Callable,
        on_narrator_done: Callable,
        on_char_start: Callable,
        on_char_chunk: Callable,
        on_char_done: Callable,
        on_npc_start: Callable,
        on_npc_chunk: Callable,
        on_npc_done: Callable,
        on_turn_complete: Callable,
        on_error: Callable,
        on_choices: Optional[Callable] = None,
        on_dice_roll: Optional[Callable] = None,
        manual_next_actor: Optional[str] = None,
        private_recipient: Optional[str] = None,
    ):
        self._cancel_flag = False
        self.is_running   = True
        self.current_task = asyncio.current_task()
        max_actor_depth   = self.max_actor_depth if hasattr(self, 'max_actor_depth') and self.max_actor_depth else 3

        try:
            planner_message = player_message
            actor_message = player_message
            
            is_system_trigger = "[PLOT ADVANCE" in player_message or "[NARRATOR TRIGGER]" in player_message or "[SYSTEM DIRECTIVE" in player_message
            
            if is_system_trigger:
                actor_message = "[ACTION PAUSED. The plot advances. Characters must react to the events described by the Narrator or other characters.]"

            plan = await self._call_gm_planner(
                party_names, planner_message, conversation_method, context_messages
            )
            if self._cancel_flag:
                await on_turn_complete()
                return

            self.world_state.update_from_plan(plan)

            for lore_data in plan.get("lore_updates", []):
                try:
                    self.world_state.lore_registry.upsert(lore_data)
                except Exception as e:
                    logger.warning(f"[SoulStage] Failed to upsert lore card: {e}")
            for obj_data in plan.get("campaign_objective_updates", []):
                try:
                    self.world_state.campaign_board.upsert_objective(obj_data)
                except Exception as e:
                    logger.warning(f"[SoulStage] Failed to upsert campaign objective: {e}")
            for clk_data in plan.get("campaign_clock_updates", []):
                try:
                    self.world_state.campaign_board.upsert_clock(clk_data)
                except Exception as e:
                    logger.warning(f"[SoulStage] Failed to upsert campaign clock: {e}")

            known_actors = party_names + [n.name for n in self.npc_registry.list_active()]
            if private_recipient and private_recipient in known_actors:
                self.world_state.add_private_knowledge(private_recipient, player_message)
            
            if is_system_trigger:
                self.world_state.add_event(actor="System", action="Director advanced the plot.")
            else:
                if '*' in player_message:
                    p_action = self._extract_dry_action(player_message)
                else:
                    p_action = player_message[:100] + "..." if len(player_message) > 100 else player_message
                self.world_state.add_event(actor="Player", action=p_action)

            for s in plan.get("spawns",[]):
                if s.get("name") not in party_names:
                    self.npc_registry.spawn(
                        s.get("name", "Unknown"),
                        s.get("archetype", "citizen"),
                        s.get("personality", ""),
                    )
            for dn in plan.get("despawns",[]):
                self.npc_registry.despawn(dn)

            npc_names = [n.name for n in self.npc_registry.list_active()]
            direct_target = self._detect_direct_address(player_message, party_names, npc_names)
            if direct_target:
                plan["next_actor"] = direct_target
                logger.info(f"[SoulStage] Direct address override: next_actor → {direct_target}")
            if manual_next_actor and manual_next_actor in party_names + npc_names:
                plan["next_actor"] = manual_next_actor
                logger.info("[SoulStage] Manual turn override: next_actor → %s", manual_next_actor)

            dice_result = None
            if bool(getattr(self.world_state, "dice_rolls_enabled", False)):
                dc_spec = plan.get("dice_check")
                if isinstance(dc_spec, dict) and dc_spec.get("notation"):
                    try:
                        dice_result = RPGRules.resolve_check(dc_spec, self.world_state)
                    except Exception as e:
                        logger.warning(f"[SoulStage] Dice roll failed, skipping: {e}")
                        dice_result = None

            if dice_result is not None:
                self.world_state.add_event(
                    actor="Dice", action=dice_result.describe()
                )
                if on_dice_roll is not None:
                    try:
                        await on_dice_roll(dice_result)
                    except Exception as e:
                        logger.warning(f"[SoulStage] on_dice_roll callback failed: {e}")

            dynamic_context = list(context_messages)
            intra_turn_dialogue = ""

            narration_text = await self._call_gm_executor(
                plan.get("narration_plan", "The scene continues."),
                conversation_method,
                context_messages,
                on_narrator_chunk,
                dynamic_context=dynamic_context,
                dice_result=dice_result,
                player_message=player_message,
            )
            if self._cancel_flag:
                await on_turn_complete()
                return
            await on_narrator_done()

            if narration_text:
                narration_text = re.sub(
                    r"^\[NARRATOR\]:?\s*", "", narration_text, flags=re.IGNORECASE
                ).strip()
                narrator_dry = narration_text[:150] + "..." if len(narration_text) > 150 else narration_text
                self.world_state.add_event(actor="NARRATOR", action=narrator_dry)
                dynamic_context.append({
                    "role": "user",
                    "content": f"[NARRATOR]: {narration_text}",
                })

            if self._cancel_flag:
                await on_turn_complete()
                return

            next_actor  = plan.get("next_actor", "PLAYER")
            actor_depth = 0

            while next_actor != "PLAYER" and actor_depth < max_actor_depth:
                if self._cancel_flag:
                    break

                actor_depth  += 1
                actor_full_text = ""
                _actor = next_actor

                if _actor in party_names:
                    avatar_path = self._get_character_avatar(_actor)
                    await on_char_start(_actor, avatar_path)

                    async def _cc(chunk, _n=_actor):
                        await on_char_chunk(_n, chunk)

                    actor_full_text = await self._call_character(
                        character_name=_actor,
                        party_names=party_names,
                        narrator_text=narration_text,
                        player_message=actor_message,
                        intra_turn_dialogue=intra_turn_dialogue,
                        context_messages=dynamic_context,
                        user_name=user_name,
                        user_description=user_description,
                        character_stream_fn=character_stream_fn,
                        on_chunk=_cc,
                    )

                    all_names = (
                        [n for n in party_names if n != _actor]
                        +[n.name for n in self.npc_registry.list_active()]
                    )
                    cleaned = self._clean_dialogue_line(_actor, actor_full_text, all_names)

                    dynamic_context.append({
                        "role": "assistant",
                        "name": _actor,
                        "content": f"[{_actor}]: {cleaned}",
                    })

                    truncated = self._smart_truncate(cleaned, max_len=500)
                    intra_turn_dialogue += f"\n\n--- ACTION BY [{_actor}] ---\n{truncated}"

                    dry_action = self._extract_dry_action(actor_full_text)
                    self.world_state.add_event(actor=_actor, action=dry_action)
                    await on_char_done(_actor, actor_full_text)

                elif self.npc_registry.get(_actor):
                    npc = self.npc_registry.get(_actor)
                    avatar_path = self.npc_registry.get_avatar_path(npc)
                    await on_npc_start(npc, avatar_path)

                    async def _nc(chunk, _n=npc.name):
                        await on_npc_chunk(_n, chunk)

                    actor_full_text = await self._call_npc(
                        npc,
                        actor_message,
                        narration_text,
                        intra_turn_dialogue,
                        party_names,
                        conversation_method,
                        dynamic_context,
                        _nc,
                        user_name=user_name,
                        user_description=user_description,
                    )

                    dynamic_context.append({
                        "role": "user",
                        "name": _actor,
                        "content": f"[NPC {_actor}]: {actor_full_text}",
                    })

                    truncated = self._smart_truncate(actor_full_text, max_len=350)
                    intra_turn_dialogue += f"\n\n--- ACTION BY [{_actor}] ---\n{truncated}"

                    dry_action = self._extract_dry_action(actor_full_text)
                    self.world_state.add_event(actor=npc.name, action=dry_action)
                    await on_npc_done(npc.name, actor_full_text)

                else:
                    logger.warning(f"[SoulStage] Unknown actor '{_actor}', routing to PLAYER.")
                    break

                if self._cancel_flag:
                    break

                if actor_depth < max_actor_depth:
                    routing = await self._call_gm_routing(
                        party_names, _actor, actor_full_text,
                        conversation_method, intra_turn_dialogue, dynamic_context,
                    )

                    bridge = routing.get("bridge_narration", "")
                    if bridge:
                        self.world_state.add_event(actor="NARRATOR", action=bridge)
                        dynamic_context.append({
                            "role": "user",
                            "content": f"[NARRATOR]: {bridge}",
                        })

                        words = bridge.split()
                        try:
                            for i, word in enumerate(words):
                                separator = " " if i < len(words) - 1 else ""
                                await on_narrator_chunk(word + separator)
                                await asyncio.sleep(0)
                            await on_narrator_done()
                        except RuntimeError as exc:
                            if "has been deleted" in str(exc):
                                logger.info("[SoulStage] Bridge narration target was deleted; cancelling stale stream.")
                                self._cancel_flag = True
                                break
                            raise

                    for dn in routing.get("despawns",[]):
                        self.npc_registry.despawn(dn)

                    next_actor = routing.get("next_actor", "PLAYER")
                else:
                    next_actor = "PLAYER"

            if on_choices is not None:
                choices    = plan.get("player_choices",[])
                event_type = plan.get("plot_event_type", "none")
                await on_choices(choices, event_type)

            expired_statuses = self.world_state.tick_statuses()
            if expired_statuses:
                self.world_state.add_event(actor="System", action=f"Expired statuses: {', '.join(expired_statuses)}")
            await self._summarize_history(conversation_method)

            await on_turn_complete()

        except asyncio.CancelledError:
            await on_turn_complete()
        except Exception as e:
            logger.error(f"[SoulStage] Error: {e}", exc_info=True)
            await on_error(str(e))
        finally:
            self.is_running = False
            self.current_task = None

    async def _summarize_history(self, conversation_method: str):
        if not hasattr(self.world_state, 'pending_summarization') or not self.world_state.pending_summarization:
            return
            
        events_to_summarize = " | ".join(self.world_state.pending_summarization)
        self.world_state.pending_summarization = []
        
        current_summary = getattr(self.world_state, 'historical_summary', "") or "None"
        
        system = (
            "[SOUL STAGE — MEMORY COMPRESSION]\n"
            "You are a narrative archivist. Your job is to compress the raw logs of events into a concise, flowing summary paragraph.\n"
            "Keep the crucial plot points, changes in relationship, and acquired knowledge.\n"
            "Discard minor repetitive dialogue and small movements.\n\n"
            f"CURRENT SUMMARY:\n{current_summary}\n\n"
            f"NEW EVENTS TO ADD:\n{events_to_summarize}\n\n"
            "OUTPUT:\nReturn ONLY the new, combined summary paragraph (max 120 words). Do not explain or add markdown blocks."
        )
        
        messages = [{"role": "system", "content": system}]
        raw = ""
        try:
            async for chunk in self._stream_llm(messages, conversation_method, temperature=0.3, max_tokens=250):
                if self._cancel_flag:
                    break
                raw += chunk
                
            if raw and not self._cancel_flag:
                self.world_state.historical_summary = raw.strip()
                logger.info("[SoulStage] Historical summary compressed and updated.")
        except Exception as e:
            logger.error(f"[SoulStage] Failed to summarize history: {e}")
            self.world_state.historical_summary += (" | " if self.world_state.historical_summary else "") + events_to_summarize
            if len(self.world_state.historical_summary) > 600:
                self.world_state.historical_summary = "..." + self.world_state.historical_summary[-597:]

    def load_world_state_from_dict(self, scene_dict: dict):
        ws = scene_dict.get("world_state", {})
        if not ws:
            ws = scene_dict

        self.world_state.location    = ws.get("location", "Unknown location")
        self.world_state.time_of_day = ws.get("time_of_day", "day")
        self.world_state.atmosphere  = ws.get("atmosphere", "")
        self.world_state.bg_image    = ws.get("bg_image", "None")
        self.world_state.ambient_audio = ws.get("ambient_audio", "None")
        self.world_state.narrator_style = ws.get("narrator_style", "Standard evocative present-tense prose")

        raw_facts = ws.get("key_facts", {})
        normalized_facts: dict = {}
        for k, v in raw_facts.items():
            norm_key = WorldState._normalize_fact_key(k)
            normalized_facts[norm_key] = v
        self.world_state.key_facts = normalized_facts

        self.world_state.player_inventory = ws.get("player_inventory", [])
        self.world_state.player_status    = ws.get("player_status", [])
        self.world_state.status_durations = {
            str(k): max(1, int(v)) for k, v in (ws.get("status_durations", {}) or {}).items()
            if str(k) and isinstance(v, (int, float, str)) and str(v).strip().lstrip("-").isdigit()
        }
        self.world_state.player_skills = {
            str(k).lower(): max(-5, min(10, int(v))) for k, v in (ws.get("player_skills", {}) or {}).items()
            if str(k)
        }
        raw_resources = ws.get("resources", {}) or {}
        self.world_state.resources = copy.deepcopy(RPGRules.DEFAULT_RESOURCES)
        for name, pool in raw_resources.items():
            if name not in self.world_state.resources or not isinstance(pool, dict):
                continue
            max_value = max(1, min(999, int(pool.get("max", self.world_state.resources[name]["max"]) or 1)))
            current = max(0, min(max_value, int(pool.get("current", max_value) or 0)))
            self.world_state.resources[name] = {"current": current, "max": max_value}
        self.world_state.lore_registry = LoreRegistry(ws.get("lore_cards", scene_dict.get("lore_cards", [])))
        self.world_state.campaign_board = CampaignBoard(ws.get("campaign_board", scene_dict.get("campaign_board", {})))
        raw_private = ws.get("private_knowledge", scene_dict.get("private_knowledge", {})) or {}
        self.world_state.private_knowledge = {
            str(actor): [str(note)[:600] for note in notes if str(note).strip()][-30:]
            for actor, notes in raw_private.items() if isinstance(notes, list)
        }

        raw_events = ws.get("events", [])
        restored_events: list[StructuredEvent] = []
        for e in raw_events:
            if isinstance(e, dict):
                restored_events.append(StructuredEvent(
                    actor=e.get("actor", ""),
                    action=e.get("action", ""),
                    outcome=e.get("outcome", ""),
                ))
            elif isinstance(e, (list, tuple)) and len(e) >= 2:
                restored_events.append(StructuredEvent(
                    actor=e[0],
                    action=e[1],
                    outcome=e[2] if len(e) > 2 else "",
                ))
        self.world_state.events = restored_events

        self.world_state.historical_summary = ws.get("historical_summary", "")
        self.world_state.pending_summarization = ws.get("pending_summarization", [])

        if "gm_tone" in ws:
            self.world_state.gm_tone = ws["gm_tone"]
        elif "gm_tone" in scene_dict:
            self.world_state.gm_tone = scene_dict["gm_tone"]

        if "world_context" in scene_dict:
            self.world_state.world_context = scene_dict["world_context"]

        if "dice_rolls_enabled" in scene_dict:
            self.world_state.dice_rolls_enabled = bool(scene_dict["dice_rolls_enabled"])
        elif "dice_rolls_enabled" in ws:
            self.world_state.dice_rolls_enabled = bool(ws["dice_rolls_enabled"])

        if "lock_bg" in scene_dict:
            self.world_state.lock_bg = bool(scene_dict["lock_bg"])
        elif "lock_bg" in ws:
            self.world_state.lock_bg = bool(ws["lock_bg"])

        if "disable_ambient" in scene_dict:
            self.world_state.disable_ambient = bool(scene_dict["disable_ambient"])
        elif "disable_ambient" in ws:
            self.world_state.disable_ambient = bool(ws["disable_ambient"])

        if "max_actor_depth" in scene_dict:
            try:
                depth = int(scene_dict["max_actor_depth"])
                if 1 <= depth <= 6:
                    self.max_actor_depth = depth
            except (ValueError, TypeError):
                pass

        self.npc_registry.clear()

        active_list = None
        if isinstance(ws, dict) and "active_npcs" in ws:
            active_list = ws["active_npcs"]
        if active_list is None:
            active_list = scene_dict.get("active_npcs", [])

        for npc_data in active_list:
            if not isinstance(npc_data, dict):
                continue
            name        = npc_data.get("name", "")
            archetype   = npc_data.get("archetype", "citizen")
            personality = npc_data.get("personality", "")
            if name:
                npc = self.npc_registry.spawn(name, archetype, personality)
                npc.turn_count = max(0, int(npc_data.get("turn_count", 0) or 0))
                if npc_data.get("avatar_key"):
                    npc.avatar_key = npc_data["avatar_key"]

        despawned_list = None
        if isinstance(ws, dict) and "despawned_npcs" in ws:
            despawned_list = ws["despawned_npcs"]
        if despawned_list is None:
            despawned_list = scene_dict.get("despawned_npcs", [])

        for npc_data in despawned_list:
            if not isinstance(npc_data, dict):
                continue
            name = npc_data.get("name", "")
            if not name:
                continue
            archetype   = npc_data.get("archetype", "citizen")
            personality = npc_data.get("personality", "")
            npc = NPCCard(
                name=name,
                archetype=archetype,
                personality=personality,
                avatar_key=npc_data.get("avatar_key", "unknown"),
                turn_count=max(0, int(npc_data.get("turn_count", 0) or 0))
            )
            self.npc_registry.despawned[name] = npc

        logger.info(
            f"[SoulStage] World state loaded. "
            f"Location: {self.world_state.location}, "
            f"Facts: {len(self.world_state.key_facts)}, "
            f"Events: {len(self.world_state.events)}, "
            f"NPCs: {len(self.npc_registry.active)}, "
            f"Historical summary: {len(self.world_state.historical_summary)} chars"
        )

    def serialize_scene_state(self) -> dict:
        payload = self.world_state.to_dict()
        payload["active_npcs"] = [
            {"name": npc.name, "archetype": npc.archetype, "personality": npc.personality,
             "avatar_key": npc.avatar_key, "turn_count": npc.turn_count}
            for npc in self.npc_registry.list_active()
        ]
        payload["despawned_npcs"] = [
            {"name": npc.name, "archetype": npc.archetype, "personality": npc.personality,
             "avatar_key": npc.avatar_key, "turn_count": npc.turn_count}
            for npc in self.npc_registry.despawned.values()
        ]
        payload["max_actor_depth"] = self.max_actor_depth
        return payload

    def _get_character_avatar(self, character_name: str) -> Optional[str]:
        try:
            char_config = configuration.ConfigurationCharacters().load_configuration()
            char_data   = char_config.get("character_list", {}).get(character_name, {})
            avatar      = char_data.get("character_avatar")
            if avatar and Path(avatar).exists():
                return avatar
        except Exception:
            pass
        return None

    async def _stream_llm(self, messages, conversation_method, temperature=0.7, max_tokens=512) -> AsyncGenerator:
        provider = AIFactory.get_provider(conversation_method)
        if not provider:
            logger.error(f"[SoulStage] Could not get provider for {conversation_method}")
            return

        if conversation_method == "Local LLM" and self.local_server_manager:
            await self.local_server_manager.ensure_server_running()

        raw_stops = self.configuration_settings.get_main_setting("stop_strings")
        stop_sequences = None
        if raw_stops and isinstance(raw_stops, str) and raw_stops.strip():
            stop_list = [s.strip() for s in raw_stops.split(",") if s.strip()]
            if stop_list:
                stop_sequences = stop_list[:4]

        async for chunk in provider.generate_stream(messages, temperature=temperature, max_tokens=max_tokens, stop=stop_sequences):
            yield chunk

    async def sync_party_memory(self, conversation_method: str, party_names: list, turn_messages: list, user_name: str):
        if not self.prompt_engine:
            return
        
        provider = AIFactory.get_provider(conversation_method)
        if not provider:
            return

        formatted_messages = []
        for msg in turn_messages:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
                actor_name = msg.get("actor_name", "")
                
                if role == "player":
                    formatted_messages.append({"role": "user", "content": content})
                elif role in ("char", "npc", "narrator"):
                    prefix = f"[{actor_name}]: " if actor_name and actor_name != role else ""
                    formatted_messages.append({"role": "assistant", "content": f"{prefix}{content}"})
                else:
                    formatted_messages.append(msg)
            else:
                formatted_messages.append(msg)

        tasks = []
        for char_name in party_names:
            tasks.append(
                self.prompt_engine.update_memory_after_response(
                    new_messages=formatted_messages,
                    character_name=char_name,
                    user_name=user_name,
                    provider=provider
                )
            )

        if tasks:
            if conversation_method == "Local LLM":
                for task in tasks:
                    await task
            else:
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"[SoulStage] Party memory synced ({conversation_method}): {party_names}")


class SoulStageSession:
    def __init__(self, orchestrator: SoulStageOrchestrator, party_names: list, conversation_method: str):
        self.orchestrator        = orchestrator
        self.party_names         = party_names
        self.conversation_method = conversation_method
        self.manual_next_actor: Optional[str] = None
        self.private_recipient: Optional[str] = None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MESSAGE MANAGER & REWIND INFRASTRUCTURE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SoulStageMessageManager:
    """
    Manager for Soul Stage message operations (Copy, Translate, Edit, Delete, Regenerate).
    """

    MAX_SNAPSHOTS = 20

    def __init__(
        self,
        orchestrator,
        get_chat_log: Callable[[], list],
        get_chat_view: Callable,
        get_scene_data: Callable[[], dict],
        save_scene: Callable[[dict], None],
        translate_fn: Optional[Callable] = None,
        rerun_turn_fn: Optional[Callable] = None,
        rebuild_ui_fn: Optional[Callable] = None,
        translations: Optional[dict] = None,
    ):
        self.orch = orchestrator
        self._get_chat_log = get_chat_log
        self._get_chat_view = get_chat_view
        self._get_scene_data = get_scene_data
        self._save = save_scene
        self._translate_fn = translate_fn
        self._rerun_turn_fn = rerun_turn_fn
        self._rebuild_ui_fn = rebuild_ui_fn,

        if translations is not None:
            self.translations = translations
        else:
            try:
                self.translations = configuration.ConfigurationLocalization().get_translations()
            except Exception:
                self.translations = {}

        self._snapshots: list[dict] = []
        self._is_rerunning = False

    def take_snapshot(self, turn_idx: int) -> None:
        try:
            snap = {
                "turn_idx": turn_idx,
                "world_state": copy.deepcopy(self.orch.serialize_scene_state()),
                "chat_log": copy.deepcopy(self._get_chat_log()),
            }
            self._snapshots.append(snap)
            if len(self._snapshots) > self.MAX_SNAPSHOTS:
                self._snapshots.pop(0)
            logger.debug(f"[MsgMgr] Snapshot taken at turn_idx={turn_idx}")
        except Exception as e:
            logger.warning(f"[MsgMgr] take_snapshot failed: {e}")

    def _apply_snapshot(self, snap: dict) -> bool:
        try:
            state = copy.deepcopy(snap["world_state"])
            self.orch.load_world_state_from_dict({"world_state": state})
            return True
        except Exception as e:
            logger.error(f"[MsgMgr] _apply_snapshot failed: {e}", exc_info=True)
            return False

    def copy_text(self, text: str) -> bool:
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QTextDocument

            doc = QTextDocument()
            doc.setHtml(text)
            plain = doc.toPlainText().strip() or text.strip()
            
            QApplication.clipboard().setText(plain)
            logger.info("[MsgMgr] Text copied to clipboard")
            return True
        except Exception as e:
            logger.warning(f"[MsgMgr] copy_text failed: {e}")
            return False

    async def translate_message(self, text_label, target_lang: str = "ru") -> bool:
        if not self._translate_fn or not text_label:
            logger.error("[MsgMgr] Missing translate_fn or text_label")
            return False

        try:
            from PyQt6.QtGui import QTextDocument

            original_html = text_label.property("original_html")
            if original_html:
                text_label.setText(original_html)
                text_label.setProperty("original_html", None)
                return True

            current_html = text_label.text()
            doc = QTextDocument()
            doc.setHtml(current_html)
            plain_text = doc.toPlainText().strip()

            if not plain_text:
                return False

            translation = await self._translate_fn(plain_text, target_lang)
            if not translation or translation == plain_text:
                return False

            translated_html = (
                f'{current_html}'
                f'<hr style="border:none;border-top:1px solid rgba(255,255,255,0.15);margin:8px 0;"/>'
                f'<div style="opacity:0.80;font-style:italic;color:#A0D2FF;">{translation}</div>'
            )
            text_label.setProperty("original_html", current_html)
            text_label.setText(translated_html)
            return True
        except Exception as e:
            logger.error(f"[MsgMgr] translate_message failed: {e}", exc_info=True)
            return False

    def delete_message(self, frame_widget, get_msg_idx_fn) -> bool:
        try:
            msg_idx = get_msg_idx_fn()
            log = self._get_chat_log()

            if not (0 <= msg_idx < len(log)):
                logger.warning(
                    f"[MsgMgr] delete_message: index {msg_idx} out of range (log len={len(log)})"
                )
                return False

            del log[msg_idx]
            scene_data = self._get_scene_data()
            scene_data["chat_log"] = log
            self._save(scene_data)

            self._snapshots = [s for s in self._snapshots if s["turn_idx"] < msg_idx]

            if self._rebuild_ui_fn:
                self._rebuild_ui_fn(log)
            elif frame_widget:
                chat_view = self._get_chat_view()
                chat_view.chat_container.removeWidget(frame_widget)
                frame_widget.deleteLater()

            logger.info(f"[MsgMgr] Deleted message at log index {msg_idx}")
            return True
        except Exception as e:
            logger.error(f"[MsgMgr] delete_message failed: {e}", exc_info=True)
            return False

    def _start_inline_edit(self, text_label, get_msg_idx_fn) -> None:
        try:
            from PyQt6.QtWidgets import (
                QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel, QFrame
            )
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QFont, QIcon, QTextDocument

            msg_idx = get_msg_idx_fn()
            log = self._get_chat_log()
            if not (0 <= msg_idx < len(log)):
                return

            if log[msg_idx].get("role") not in ("player", "user"):
                logger.warning(
                    f"[MsgMgr] _start_inline_edit: index {msg_idx} is role "
                    f"'{log[msg_idx].get('role')}', not a player message — searching nearby."
                )
                fixed_idx = None
                for offset in range(1, len(log)):
                    for cand in (msg_idx - offset, msg_idx + offset):
                        if 0 <= cand < len(log) and log[cand].get("role") in ("player", "user"):
                            fixed_idx = cand
                            break
                    if fixed_idx is not None:
                        break
                if fixed_idx is None:
                    logger.error("[MsgMgr] _start_inline_edit: no player message found in log; aborting.")
                    return
                msg_idx = fixed_idx

            raw_text = log[msg_idx].get("content", "")
            if not raw_text:
                doc = QTextDocument()
                doc.setHtml(text_label.text() if hasattr(text_label, "text") else "")
                raw_text = doc.toPlainText().strip()

            chat_view = self._get_chat_view()
            dialog = QDialog(chat_view)
            dialog.setWindowTitle(self.translations.get("ss_edit_msg_dialog_title", "Edit Message — Soul Stage"))
            dialog.setMinimumWidth(560)
            dialog.setFixedHeight(340)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #0c0c10;
                    color: #e8e8e8;
                }
                QLabel { background: transparent; border: none; }
            """)

            def _font(family="Inter Tight Medium", size=11, bold=False):
                f = QFont(family, size)
                if bold: f.setWeight(QFont.Weight.Bold)
                f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
                return f

            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(24, 20, 24, 20)
            layout.setSpacing(12)

            hdr = QHBoxLayout()
            hdr.setSpacing(12)
            
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon("app/gui/icons/edit.png").pixmap(22, 22))
            hdr.addWidget(icon_lbl)

            title_col = QVBoxLayout()
            title_col.setSpacing(2)
            title_lbl = QLabel(self.translations.get("ss_edit_msg_title", "EDIT PLAYER MESSAGE"))
            title_lbl.setFont(_font("Inter Tight SemiBold", 11, bold=True))
            title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); letter-spacing: 1.5px;")
            title_col.addWidget(title_lbl)

            sub_lbl = QLabel(self.translations.get("ss_edit_msg_sub", "Saving will update your text, rewind world state, and rerun the story turn."))
            sub_lbl.setFont(_font("Inter Tight Medium", 10))
            sub_lbl.setStyleSheet("color: rgba(255,255,255,0.45);")
            title_col.addWidget(sub_lbl)

            hdr.addLayout(title_col, 1)
            layout.addLayout(hdr)

            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")
            layout.addWidget(div)

            editor = QPlainTextEdit()
            editor.setFont(_font("Inter Tight Medium", 12))
            editor.setPlainText(raw_text)
            editor.setStyleSheet("""
                QPlainTextEdit {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-top: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 10px;
                    color: rgba(240, 240, 240, 0.95);
                    padding: 12px 14px;
                    selection-background-color: rgba(75, 184, 255, 0.25);
                }
                QPlainTextEdit:focus {
                    border: 1px solid rgba(75, 184, 255, 0.5);
                    background: rgba(255, 255, 255, 0.05);
                }
            """)
            layout.addWidget(editor, 1)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(10)

            btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
            btn_cancel.setFont(_font("Inter Tight Medium", 11))
            btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_cancel.setFixedHeight(36)
            btn_cancel.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 8px;
                    color: rgba(255, 255, 255, 0.6);
                    padding: 0 16px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.05);
                    border-color: rgba(255, 255, 255, 0.2);
                    color: white;
                }
            """)

            btn_save = QPushButton(self.translations.get("ss_edit_msg_save_btn", "Save & Rewind Turn"))
            btn_save.setFont(_font("Inter Tight SemiBold", 11))
            btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_save.setFixedHeight(36)
            btn_save.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(75, 184, 255, 0.30),
                        stop:1 rgba(75, 184, 255, 0.15));
                    border: 1px solid rgba(75, 184, 255, 0.40);
                    border-top: 1px solid rgba(75, 184, 255, 0.60);
                    border-radius: 8px;
                    color: #82CDFF;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(75, 184, 255, 0.45),
                        stop:1 rgba(75, 184, 255, 0.25));
                    border-color: rgba(75, 184, 255, 0.70);
                    color: #FFFFFF;
                }
            """)

            btn_row.addWidget(btn_cancel)
            btn_row.addStretch()
            btn_row.addWidget(btn_save)
            layout.addLayout(btn_row)

            def on_save():
                new_text = editor.toPlainText().strip()
                if not new_text:
                    return
                dialog.accept()
                asyncio.create_task(self.edit_player_message(msg_idx, new_text))

            btn_save.clicked.connect(on_save)
            btn_cancel.clicked.connect(dialog.reject)
            dialog.exec()
        except Exception as e:
            logger.warning(f"[MsgMgr] _start_inline_edit failed: {e}")

    async def edit_player_message(self, msg_idx: int, new_text: str) -> bool:
        if self._is_rerunning or not self._rerun_turn_fn:
            return False

        log = self._get_chat_log()
        if not (0 <= msg_idx < len(log)):
            return False

        self._is_rerunning = True
        try:
            truncated_log = log[:msg_idx]

            self._snapshots = [s for s in self._snapshots if s["turn_idx"] <= msg_idx]

            scene_data = self._get_scene_data()
            scene_data["chat_log"] = truncated_log
            self._save(scene_data)

            if self._rebuild_ui_fn:
                self._rebuild_ui_fn(truncated_log)

            prev_snap = None
            for s in reversed(self._snapshots):
                if s["turn_idx"] <= msg_idx:
                    prev_snap = s
                    break
            if prev_snap:
                self._apply_snapshot(prev_snap)
            else:
                logger.warning(
                    f"[MsgMgr] No snapshot found at or before msg_idx={msg_idx}; "
                    f"world state was not rewound before re-running the edited turn."
                )

            await self._rerun_turn_fn(new_text)
            return True
        except Exception as e:
            logger.error(f"[MsgMgr] edit_player_message failed: {e}", exc_info=True)
            return False
        finally:
            self._is_rerunning = False

    async def regenerate_turn(self, turn_idx: int, temp_boost: float = 0.1) -> bool:
        if self._is_rerunning or not self._rerun_turn_fn:
            return False

        snap = None
        for s in reversed(self._snapshots):
            if s["turn_idx"] <= turn_idx:
                snap = s
                break

        if not snap:
            logger.info(f"[MsgMgr] No in-memory snapshot for turn_idx={turn_idx}. Building fallback snapshot.")
            log = self._get_chat_log()
            if not log or turn_idx >= len(log):
                logger.warning(f"[MsgMgr] Cannot build fallback snapshot: turn_idx={turn_idx} out of range (log len={len(log)})")
                return False

            player_msg_idx = None
            for i in range(min(turn_idx, len(log) - 1), -1, -1):
                msg_item = log[i]
                if msg_item.get("role") in ("player", "user") or "[SYSTEM DIRECTIVE" in msg_item.get("content", ""):
                    player_msg_idx = i
                    break

            trunc_idx = player_msg_idx if player_msg_idx is not None else turn_idx

            ws = self.orch.world_state
            snap = {
                "turn_idx": trunc_idx,
                "world_state": {
                    "location": ws.location,
                    "time_of_day": ws.time_of_day,
                    "atmosphere": ws.atmosphere,
                    "bg_image": ws.bg_image,
                    "ambient_audio": ws.ambient_audio,
                    "key_facts": dict(ws.key_facts),
                    "player_inventory": list(ws.player_inventory),
                    "player_status": list(ws.player_status),
                    "events": [
                        {"actor": e.actor, "action": e.action, "outcome": e.outcome}
                        for e in ws.events
                    ],
                    "historical_summary": ws.historical_summary,
                    "pending_summarization": list(ws.pending_summarization),
                    "gm_tone": ws.gm_tone,
                    "narrator_style": ws.narrator_style,
                },
                "chat_log": copy.deepcopy(log[:trunc_idx]),
            }

        self._is_rerunning = True
        try:
            current_log = self._get_chat_log()
            player_msg = ""
            search_idx = min(turn_idx, len(current_log) - 1)
            while search_idx >= 0:
                msg_item = current_log[search_idx]
                if msg_item.get("role") in ("player", "user") or "[SYSTEM DIRECTIVE" in msg_item.get("content", ""):
                    player_msg = msg_item.get("content", "")
                    break
                search_idx -= 1

            if not player_msg and current_log:
                player_msg = current_log[-1].get("content", "")

            if not self._apply_snapshot(snap):
                return False

            self._snapshots = [s for s in self._snapshots if s["turn_idx"] <= snap["turn_idx"]]

            scene_data = self._get_scene_data()
            scene_data["chat_log"] = copy.deepcopy(snap["chat_log"])
            self._save(scene_data)

            if self._rebuild_ui_fn:
                self._rebuild_ui_fn(snap["chat_log"])

            if not player_msg:
                logger.error(f"[MsgMgr] Could not find player message to regenerate at turn_idx={turn_idx}")
                return False

            self.orch._temp_boost = float(temp_boost)
            try:
                await self._rerun_turn_fn(player_msg)
            finally:
                self.orch._temp_boost = 0.0

            logger.info(f"[MsgMgr] Successfully regenerated turn {turn_idx} with temp_boost={temp_boost}")
            return True
        except Exception as e:
            logger.error(f"[MsgMgr] regenerate_turn failed: {e}", exc_info=True)
            return False
        finally:
            self._is_rerunning = False

    def attach_context_menu(self, frame_widget, text_label, get_msg_idx_fn, is_player: bool = False) -> None:
        """
        Attach right-click context menu to ANY Soul Stage bubble.
        """
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QMenu
            from PyQt6.QtGui import QAction

            frame_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

            def show_menu(pos):
                menu = QMenu(frame_widget)
                menu.setStyleSheet("""
                    QMenu {
                        background-color: #14141a;
                        border: 1px solid rgba(255, 255, 255, 0.10);
                        border-radius: 8px;
                        padding: 6px;
                        color: rgba(255, 255, 255, 0.85);
                    }
                    QMenu::item {
                        background: transparent;
                        padding: 7px 24px 7px 14px;
                        border-radius: 6px;
                        margin: 1px 2px;
                    }
                    QMenu::item:selected {
                        background: rgba(75, 184, 255, 0.18);
                        color: #FFFFFF;
                    }
                    QMenu::item:disabled {
                        color: rgba(255, 255, 255, 0.30);
                    }
                    QMenu::separator {
                        height: 1px;
                        background: rgba(255, 255, 255, 0.08);
                        margin: 6px 8px;
                    }
                """)

                # 1. Copy
                act_copy = QAction(self.translations.get("ss_menu_copy", "Copy"), menu)
                menu.addAction(act_copy)
                act_copy.triggered.connect(lambda: self.copy_text(text_label.text() if hasattr(text_label, "text") else ""))

                menu.addSeparator()

                # 2. Edit
                if is_player:
                    act_edit = QAction(self.translations.get("ss_menu_edit", "Edit Message"), menu)
                    menu.addAction(act_edit)
                    act_edit.triggered.connect(lambda: self._start_inline_edit(text_label, get_msg_idx_fn))

                    menu.addSeparator()

                # 3. Translate
                act_tr_ru = QAction(self.translations.get("ss_menu_translate_ru", "Translate → Russian"), menu)
                menu.addAction(act_tr_ru)
                act_tr_ru.triggered.connect(
                    lambda: asyncio.create_task(self.translate_message(text_label, "ru"))
                )
                act_tr_en = QAction(self.translations.get("ss_menu_translate_en", "Translate → English"), menu)
                menu.addAction(act_tr_en)
                act_tr_en.triggered.connect(
                    lambda: asyncio.create_task(self.translate_message(text_label, "en"))
                )

                menu.addSeparator()

                # 4. Regenerate
                if not is_player:
                    act_regen = QAction(self.translations.get("ss_menu_regenerate", "Regenerate Turn"), menu)
                    menu.addAction(act_regen)
                    act_regen.triggered.connect(
                        lambda: asyncio.create_task(self.regenerate_turn(get_msg_idx_fn()))
                    )

                # 5. Delete
                act_del = QAction(self.translations.get("ss_menu_delete", "Delete Message"), menu)
                menu.addAction(act_del)
                act_del.triggered.connect(lambda: self.delete_message(frame_widget, get_msg_idx_fn))

                menu.exec(frame_widget.mapToGlobal(pos))

            frame_widget.customContextMenuRequested.connect(show_menu)
        except Exception as e:
            logger.warning(f"[MsgMgr] attach_context_menu failed: {e}")

    def export_markdown(self) -> str:
        scene_data = self._get_scene_data()
        chat_log = self._get_chat_log()
        ws = self.orch.world_state

        title = (scene_data.get("title") or "Soul Stage Session").strip()
        lines: list[str] = [f"# {title}"]

        desc = (scene_data.get("description") or "").strip()
        if desc:
            lines.append(f"*{desc}*")
        lines.append("")

        lines.append("## Session Info")
        lines.append(f"- **Exported:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        if scene_data.get("created_at"):
            lines.append(f"- **Created:** {scene_data['created_at']}")
        lines.append(f"- **GM Tone:** {ws.gm_tone}")
        lines.append(f"- **Narrator Style:** {ws.narrator_style}")
        lines.append(f"- **Conversation Method:** {scene_data.get('conversation_method', 'Unknown')}")
        party = scene_data.get("party", [])
        if party:
            lines.append(f"- **Party:** {', '.join(party)}")
        lines.append(f"- **Dice Rolls:** {'Enabled 🎲' if getattr(ws, 'dice_rolls_enabled', False) else 'Disabled'}")
        lines.append("")

        world_context = (scene_data.get("world_context") or ws.world_context or "").strip()
        if world_context:
            lines.append("## World Context")
            lines.append(self._md_escape(world_context))
            lines.append("")

        lines.append("## Transcript")
        lines.append("")
        turn_no = 0
        for entry in chat_log:
            role = entry.get("role", "")
            actor = entry.get("actor_name") or role.upper() or "Unknown"
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            content = self._md_escape(content)

            if role == "player":
                turn_no += 1
                lines.append("---")
                lines.append(f"### Turn {turn_no}")
                lines.append(f"**🧑 {actor}:** {content}")
            elif role == "narrator":
                dice = entry.get("dice_check")
                if isinstance(dice, dict) and dice.get("notation"):
                    try:
                        dr = DiceRollResult.from_dict(dice)
                        lines.append(f"> 🎲 **{dr.describe()}**")
                        lines.append(">")
                    except Exception:
                        pass
                lines.append(f"> {content}")
            elif role == "char":
                lines.append(f"**💬 {actor}:** {content}")
            elif role == "npc":
                archetype = entry.get("archetype", "")
                label = f"{actor} · {archetype}" if archetype else actor
                lines.append(f"**🎭 {label}:** {content}")
            else:
                lines.append(f"**{actor}:** {content}")
            lines.append("")

        active_npcs: list = []
        try:
            active_npcs = [
                {
                    "name": n.name, "archetype": n.archetype,
                    "personality": n.personality, "turn_count": n.turn_count,
                }
                for n in self.orch.npc_registry.list_active()
            ]
        except Exception:
            active_npcs = []
        if not active_npcs:
            active_npcs = scene_data.get("active_npcs", [])

        if active_npcs:
            lines.append("## NPCs Encountered")
            for npc in active_npcs:
                name = npc.get("name", "Unknown")
                arch = npc.get("archetype", "")
                pers = (npc.get("personality") or "").strip()
                turns = npc.get("turn_count", 0)
                entry_line = f"- **{name}**" + (f" ({arch})" if arch else "") + f" — {turns} turn(s) in scene"
                lines.append(entry_line)
                if pers:
                    lines.append(f"  *{self._md_escape(pers)}*")
            lines.append("")

        lines.append("## Final World State")
        lines.append(f"- **Location:** {ws.location}")
        lines.append(f"- **Time of Day:** {ws.time_of_day}")
        if ws.atmosphere:
            lines.append(f"- **Atmosphere:** {ws.atmosphere}")
        if ws.player_inventory:
            lines.append(f"- **Inventory:** {', '.join(ws.player_inventory)}")
        if ws.player_status:
            lines.append(f"- **Status:** {', '.join(self.player_status if hasattr(self, 'player_status') else ws.player_status)}")
        if ws.key_facts:
            lines.append("- **Established Facts:**")
            for k, v in ws.key_facts.items():
                lines.append(f"  - {k.replace('_', ' ')}: {v}")
        if ws.historical_summary:
            lines.append("")
            lines.append("**Historical Summary:**")
            lines.append(self._md_escape(ws.historical_summary))

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _md_escape(text: str) -> str:
        return "\n".join(
            ("\\" + line if line.startswith("#") else line)
            for line in text.split("\n")
        )