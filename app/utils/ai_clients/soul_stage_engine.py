import os
import re
import json
import asyncio
import logging

from dataclasses import dataclass
from typing import AsyncGenerator, Callable, Optional
from pathlib import Path

from app.configuration import configuration
from app.utils.ai_clients.prompt_engine import PromptEngine
from app.utils.ai_clients.ai_factory import AIFactory

logger = logging.getLogger("SoulStage")


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
    
    @staticmethod
    def _normalize_fact_key(key: str) -> str:
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    def update_from_plan(self, plan: dict):
        self.location      = plan.get("location", self.location)
        self.time_of_day   = plan.get("time_of_day", self.time_of_day)
        self.atmosphere    = plan.get("atmosphere", self.atmosphere)
        self.bg_image      = plan.get("bg_image", self.bg_image)
        self.ambient_audio = plan.get("ambient_audio", self.ambient_audio)

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

        if self.events:
            lines.append("RECENT EVENTS:")
            for ev in self.events[-4:]:
                op = f" -> {ev.outcome}" if ev.outcome else ""
                lines.append(f"[{ev.actor}] {ev.action}{op}")
                
        return "\n".join(lines)

    def reset(self):
        ctx      = self.world_context
        tone     = self.gm_tone
        style    = self.narrator_style
        statuses = self.player_status.copy()
        
        self.__init__()
        
        self.world_context = ctx
        self.gm_tone       = tone
        self.narrator_style = style
        self.player_status = statuses


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

    def list_active(self) -> list[NPCCard]:
        return list(self.active.values())

    def get_avatar_path(self, npc: NPCCard) -> str:
        path = self.ARCHETYPE_AVATARS.get(npc.avatar_key, self.DEFAULT_AVATAR)
        return path if Path(path).exists() else self.DEFAULT_AVATAR

    def clear(self):
        self.active.clear()

    def as_text(self) -> str:
        if not self.active:
            return "None"
        return "\n".join(f"  - {n.name} ({n.archetype}): {n.personality}" for n in self.active.values())

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

{{
  "narration_plan":   "<max 80 words — what the Narrator should describe: environment, mood, physical events. NO dialogue.>",
  "image_prompt":     "<Stable Diffusion tags describing the current scene, max 20 words, or 'None'>",
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
  "player_choices":   ["<choice A>", "<choice B>", "<choice C>"]
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

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES — NPC POPULATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Never have more than 2 ACTIVE NPCs simultaneously. Crowded scenes lose focus.
- To spawn a new NPC when 2 are active, you MUST despawn one first.
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
Match your length to what actually happened, not to what feels appropriately "narrator-sized."

  Action event (fight begins, explosion, someone arrives, major discovery): 60–120 words.
    → Full sensory immersion. Multiple details. Let the world react.

  Scene transition or mood shift (time passes, location changes, weather shifts): 30–60 words.
    → Set the new tone. Two or three precise images.

  Continuation of a calm scene (quiet conversation, waiting, small movement): 15–30 words.
    → One image. One sound. One change. Do not over-narrate stillness —
      silence has weight only if you don't keep describing it.

If nothing significant changed in the world — say almost nothing.
A single sentence is often more powerful than a paragraph.

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
Your prose here. Present tense. Max 120 words.
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
        "image_prompt":    "None",
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
        logger.warning(f"[PlannerParser] JSON parse failed. Raw: {raw}")
        return dict(cls.EMPTY_PLAN)

    @classmethod
    def _fill_defaults(cls, plan: dict) -> dict:
        result = dict(cls.EMPTY_PLAN)
        result.update(plan)
        
        for key in ["key_facts"]:
            if not isinstance(result.get(key), dict): result[key] = {}
        for key in ["spawns", "despawns", "inventory_add", "inventory_remove", "status_add", "status_remove", "player_choices"]:
            if not isinstance(result.get(key), list): result[key] = []
            
        if not result.get("next_actor"):
            result["next_actor"] = "PLAYER"

        valid_events = ("encounter", "discovery", "visitor", "twist", "romance", "none")
        if result.get("plot_event_type") not in valid_events:
            result["plot_event_type"] = "none"

        if result.get("next_actor") != "PLAYER":
            result["player_choices"] = []
            
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
    def __init__(self, prompt_engine=None, local_server_manager=None):
        self.prompt_engine = prompt_engine
        self.local_server_manager = local_server_manager
        self.cfg_settings  = configuration.ConfigurationSettings()
        self.cfg_api       = configuration.ConfigurationAPI()
        self.cfg_chars     = configuration.ConfigurationCharacters()
        self.npc_registry  = NPCRegistry()
        self.world_state   = WorldState()
        self.is_running    = False
        self._cancel_flag  = False
        self.current_task: Optional[asyncio.Task] = None

        self.bg_list      = self._get_files("assets/backgrounds", [".jpg", ".png", ".jpeg"])
        self.ambient_list = self._get_files("assets/ambient", [".mp3", ".wav", ".ogg"])

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

        for name in all_names:
            n = re.escape(name)
            if re.match(rf'^{n}[\s,!?\.…]', msg_stripped, re.IGNORECASE):
                logger.info(f"[DirectAddress] Vocative at start: '{name}' in '{msg_stripped[:60]}'")
                return name

            if re.search(rf'\b(?:hey|hi|listen|wait|okay|so|well|now),?\s+{n}\b', msg_stripped, re.IGNORECASE):
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
        system = GM_PLANNER_SYSTEM.format(
            world_context=self.world_state.world_context or "(none)",
            party_list=self._party_list_text(party_names),
            npc_list=self.npc_registry.as_text(),
            bg_list=", ".join(self.bg_list) if self.bg_list else "None",
            ambient_list=", ".join(self.ambient_list) if self.ambient_list else "None",
            world_state=self.world_state.to_prompt(),
            all_actor_names=self._all_actor_names(party_names),
        )
        messages = [{"role": "system", "content": system}]
        if context_messages:
            messages.extend(context_messages[-10:])
        messages.append({"role": "user", "content": f"[NEW PLAYER ACTION]: {player_message}\n\nProduce the GM JSON plan."})
        raw = ""
        async for chunk in self._stream_llm(messages, conversation_method, temperature=0.1, max_tokens=600):
            raw += chunk
        plan = PlannerParser.parse(raw)
        logger.info(f"[Planner] next={plan['next_actor']} spawns={[s['name'] for s in plan['spawns']]}")
        return plan

    async def _call_gm_executor(self, narration_plan, conversation_method, context_messages, on_chunk, dynamic_context: Optional[list] = None) -> str:
        system = GM_EXECUTOR_SYSTEM.format(
            tone=self.world_state.gm_tone,
            narrator_style=self.world_state.narrator_style,
            world_context=self.world_state.world_context or "(none)",
            world_state=self.world_state.to_prompt(),
            narration_plan=narration_plan,
        )
        messages = [{"role": "system", "content": system}]

        ctx_to_use = dynamic_context if dynamic_context is not None else context_messages
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

        async for chunk in self._stream_llm(
            messages, conversation_method, temperature=temp, max_tokens=350
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
                await on_chunk(new_clean_chunk)
                streamed_clean_length = len(clean_text)

        final_clean = self._executor_extract(raw)
        return final_clean

    def _executor_extract(self, text: str) -> str:
        clean = re.sub(r"\[/?(NARRATION|NARRATOR)\]:?\s*", "", text, flags=re.IGNORECASE).strip()
        clean = re.split(r'\n\s*(?:\[|\*)[A-Za-z0-9 ]+(?:\]|\*)\s*:', clean)[0].strip()
        return clean[:600] if clean else "The scene continues."

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
            await on_chunk(chunk)

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
        intra_block    = f"[DIALOGUE THIS TURN — react naturally]\n{intra_turn_dialogue.strip()}\n\n" if intra_turn_dialogue.strip() else ""
        narrator_block = f"[NARRATOR]: {narrator_text}\n\n" if narrator_text else ""
        user_content   = f"{intra_block}{narrator_block}[PLAYER]: {player_message}"

        messages = [{"role": "system", "content": system}]
        if context_messages:
            messages.extend(context_messages[-6:])
        messages.append({"role": "user", "content": user_content})

        full_text = ""
        async for chunk in self._stream_llm(messages, conversation_method, temperature=0.8, max_tokens=300):
            if self._cancel_flag:
                break
            full_text += chunk
            await on_chunk(chunk)
        npc.turn_count += 1
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
        on_image_prompt: Optional[Callable] = None,
    ):
        self._cancel_flag = False
        self.is_running   = True
        self.current_task = asyncio.current_task()
        max_actor_depth   = 3

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

            if on_image_prompt is not None:
                img_prompt = plan.get("image_prompt", "None")
                if img_prompt and str(img_prompt).lower() != "none":
                    await on_image_prompt(img_prompt)

            dynamic_context = list(context_messages)
            intra_turn_dialogue = ""

            narration_text = await self._call_gm_executor(
                plan.get("narration_plan", "The scene continues."),
                conversation_method,
                context_messages,
                on_narrator_chunk,
                dynamic_context=dynamic_context,
            )
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
                        for i, word in enumerate(words):
                            separator = " " if i < len(words) - 1 else ""
                            await on_narrator_chunk(word + separator)
                            await asyncio.sleep(0)
                        await on_narrator_done()

                    for dn in routing.get("despawns",[]):
                        self.npc_registry.despawn(dn)

                    next_actor = routing.get("next_actor", "PLAYER")
                else:
                    next_actor = "PLAYER"

            if on_choices is not None:
                choices    = plan.get("player_choices",[])
                event_type = plan.get("plot_event_type", "none")
                await on_choices(choices, event_type)

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
            return

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

        if "world_context" in scene_dict:
            self.world_state.world_context = scene_dict["world_context"]

        if "gm_tone" in scene_dict:
            self.world_state.gm_tone = scene_dict["gm_tone"]

        self.npc_registry.clear()
        for npc_data in scene_dict.get("active_npcs", []):
            name      = npc_data.get("name", "")
            archetype = npc_data.get("archetype", "citizen")
            personality = npc_data.get("personality", "")
            if name:
                self.npc_registry.spawn(name, archetype, personality)

        logger.info(
            f"[SoulStage] World state loaded. "
            f"Location: {self.world_state.location}, "
            f"Facts: {len(self.world_state.key_facts)}, "
            f"NPCs: {len(self.npc_registry.active)}"
        )

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

        async for chunk in provider.generate_stream(messages, temperature=temperature, max_tokens=max_tokens):
            yield chunk

    async def sync_party_memory(self, conversation_method: str, party_names: list, turn_messages: list, user_name: str):
        if not self.prompt_engine:
            return
        
        provider = AIFactory.get_provider(conversation_method)
        if not provider:
            return

        tasks = []
        for char_name in party_names:
            tasks.append(
                self.prompt_engine.update_memory_after_response(
                    provider, turn_messages, char_name, user_name
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

