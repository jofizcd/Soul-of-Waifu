import re
import torch
import numpy as np
import json
import logging
import datetime
import asyncio
import shutil
import threading
from pathlib import Path
from typing import Callable, Awaitable, Optional
from sentence_transformers import SentenceTransformer

from app.configuration import configuration

logger = logging.getLogger("SoulMemory")

_EMBEDDER = None
_EMBEDDER_FAILED: bool = False
_EMBEDDER_AVAILABLE: Optional[bool] = None
_EMBEDDER_LOCK = threading.Lock()

LOCAL_MODEL_PATH = Path("app/utils/all-MiniLM-L6-v2")


def _check_embedder_available() -> bool:
    global _EMBEDDER_AVAILABLE
    if _EMBEDDER_AVAILABLE is None:
        try:
            import sentence_transformers
            _EMBEDDER_AVAILABLE = True
        except ImportError:
            _EMBEDDER_AVAILABLE = False
            logger.warning(
                "[Soul Memory] sentence-transformers not found. "
                "Topic RAG filtering will fall back to simple truncation. "
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
                abs_path = LOCAL_MODEL_PATH.resolve()
                model_target = str(abs_path) if abs_path.exists() else "all-MiniLM-L6-v2"

                device = "cpu"

                logger.info(f"[Soul Memory] Loading embedding model on {device.upper()} from '{model_target}'...")
                _EMBEDDER = SentenceTransformer(model_target, device=device)
                logger.info(f"[Soul Memory] Embedding model successfully loaded on {device.upper()}")

            except Exception as e:
                logger.error(f"[Soul Memory] Failed to load embedding model: {e}", exc_info=True)
                _EMBEDDER = None
                _EMBEDDER_FAILED = True

    return _EMBEDDER


class TopicRAG:
    RAG_THRESHOLD = 4
    EMBED_CHARS   = 600
    PASS_CHARS    = 8000

    def __init__(self, topics_dir: Path):
        self.topics_dir = topics_dir

    def _load_all_topics(self) -> dict[str, str]:
        result = {}
        if not self.topics_dir.exists():
            return result
        
        try:
            paths = sorted(
                self.topics_dir.glob("*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        except Exception:
            paths = list(self.topics_dir.glob("*.md"))
        for p in paths:
            try:
                result[p.name] = p.read_text(encoding="utf-8")
            except Exception:
                pass
        return result

    def get_relevant_topics(self, query_text: str, max_topics: int = 3) -> dict[str, str]:
        """Returns up to max_topics files ranked by relevance to query_text."""
        all_topics = self._load_all_topics()
        if not all_topics:
            return {}

        if len(all_topics) <= self.RAG_THRESHOLD:
            return {k: v[:self.PASS_CHARS] for k, v in all_topics.items()}

        embedder = _get_embedder()
        if not embedder:
            items = list(all_topics.items())[:max_topics]
            return {k: v[:self.PASS_CHARS] for k, v in items}

        try:
            names    = list(all_topics.keys())
            snippets = [v[:self.EMBED_CHARS] for v in all_topics.values()]

            query_vec  = embedder.encode(query_text, convert_to_numpy=True)
            topic_vecs = embedder.encode(snippets, convert_to_numpy=True)

            q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
            t_norm = topic_vecs / (np.linalg.norm(topic_vecs, axis=1, keepdims=True) + 1e-9)
            scores = t_norm @ q_norm

            top_idx  = np.argsort(scores)[::-1][:max_topics]
            selected = {names[i]: all_topics[names[i]][:self.PASS_CHARS] for i in top_idx}

            logger.info(
                f"[Soul Memory] RAG selected {len(selected)}/{len(all_topics)} topics: "
                f"{list(selected.keys())}"
            )
            return selected

        except Exception as e:
            logger.warning(f"[Soul Memory] RAG embedding error ({e}). Using fallback.")
            items = list(all_topics.items())[:max_topics]
            return {k: v[:self.PASS_CHARS] for k, v in items}

    DEDUP_THRESHOLD = 0.82

    def find_similar_topic(self, query_text: str, threshold: float = None) -> Optional[str]:
        threshold = self.DEDUP_THRESHOLD if threshold is None else threshold

        all_topics = self._load_all_topics()
        if not all_topics:
            return None

        embedder = _get_embedder()
        if not embedder:
            return None

        try:
            names    = list(all_topics.keys())
            snippets = [v[:self.EMBED_CHARS] for v in all_topics.values()]

            query_vec  = embedder.encode(query_text, convert_to_numpy=True)
            topic_vecs = embedder.encode(snippets, convert_to_numpy=True)

            q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
            t_norm = topic_vecs / (np.linalg.norm(topic_vecs, axis=1, keepdims=True) + 1e-9)
            scores = t_norm @ q_norm

            best_idx = int(np.argmax(scores))
            if scores[best_idx] >= threshold:
                logger.info(
                    f"[Soul Memory] Dedup match: '{names[best_idx]}' "
                    f"(similarity={scores[best_idx]:.3f} >= {threshold})"
                )
                return names[best_idx]

        except Exception as e:
            logger.warning(f"[Soul Memory] Dedup similarity check failed: {e}")

        return None


_ROUTER_SYSTEM = """\
[SOUL MEMORY — ROUTER AGENT]
You manage the deep cognitive, emotional, and relationship INDEX files for "{character}".
You operate strictly as an analytical database engine. Your output MUST be a single, well-formatted JSON object and NOTHING else. No conversational filler, no markdown wrapping outside of the JSON block.

You will receive:
  1. CURRENT CHARACTER MEMORY (MEMORY.md)
  2. CURRENT USER PROFILE & RELATIONSHIP STATE (USER.md)
  3. RECENT MESSAGES (the latest dialogue turns)
  4. TRIGGERED WORLD LORE (if active)
  5. RELEVANT TOPIC FILES (associated episodic memories)

Your job is to analyze the psychological subtext of the recent messages and update BOTH the character's internal memory state and the user's profile metadata.

CRITICAL INSTRUCTIONS:
- Do not duplicate data between MEMORY.md and USER.md. 
- MEMORY.md focuses entirely on "{character}"'s subjective psychology, beliefs, emotional decay, and internal tension.
- USER.md focuses entirely on factual user attributes, preferences, habits, relationship dynamics (trust levels), and shared milestones/promises.
- EMOTIONAL DECAY: If an emotion in the current character memory is no longer active or referenced in recent turns, increment "emotional_decay_counter". At 3, soften/transition the emotion. If active, reset counter to 0.
- CONFLICT RESOLUTION: Resolve any direct contradictions between user action and previous beliefs, and document this in the "healing_log".
- NO-OP DETECTION: If the RECENT MESSAGES contain nothing psychologically or factually significant (small talk, filler, a repeated greeting, an interrupted/empty exchange), do NOT fabricate change. Instead output ONLY:
  {"no_significant_change": true, "healing_log": ["No conflicts detected."]}
  and nothing else. Only do this when you are confident nothing in the batch is worth recording.

You MUST otherwise output exactly this JSON structure:
{
  "character_memory": {
    "core_identity": [
      "3-5 bullet points of core, unbreakable beliefs, foundational self-conceptions, and fatal flaws of {character}."
    ],
    "internal_state": {
      "primary_emotion": "The dominant emotion right now (e.g., Playful Defiance, Defensive Melancholy)",
      "intensity": "Scale 1 to 5 (e.g., '4/5')",
      "psychological_tension": "Current mental dilemma, comfort level, or inner struggle.",
      "emotional_decay_counter": 0
    },
    "cognitive_drive": {
      "active_agenda": "Her subtextual goal in this conversation (e.g., 'To test if he actually cares', 'To mask her vulnerability with humor')",
      "immediate_focus": "What is occupying her immediate thoughts right now?"
    },
    "cognitive_dissonance": "Describe any active contradictions she is feeling right now, or 'None'."
  },
  "user_memory": {
    "user_identity_status": {
      "role_in_story": "Who the user is in this setting or story.",
      "known_attributes": "Physical, social, or skill-related attributes established about {user_name}."
    },
    "relationship_metadata": {
      "trust_level": "Choose one: Distrustful / Wary / Neutral / Developing Trust / Deeply Bound / Unstable",
      "dynamic_description": "Detailed psychological description of how {character} currently perceives {user_name} based on recent interactions.",
      "unspoken_tension": "What is {character} keeping to herself or secretly hoping for regarding {user_name}?"
    },
    "preferences_habits": [
      "Known habits, likes, dislikes, or conversational patterns of the user."
    ],
    "shared_milestones_promises": [
      "Promises made, secrets shared, or significant narrative events established during the chats."
    ]
  },
  "healing_log": [
    "List of contradictions fixed. If none, write 'No conflicts detected.'"
  ],
  "topic_plan": {
    "reasoning": "Analyze if the recent conversation introduced new locations, NPCs, items, or deep backstories requiring a separate file.",
    "actions": [
      {"action": "create", "filename": "example_topic.md", "summary": "Reason for creation"},
      {"action": "update", "filename": "existing_topic.md", "summary": "Reason for update"}
    ]
  }
}
"""

_ROUTER_SYSTEM_LITE = """\
[SOUL MEMORY — ROUTER AGENT (LITE)]
You manage the short-term working memory cache for the character "{character}".
You operate strictly as an analytical engine. Output must be a single, well-formatted JSON object.

We do not track long-term topic plans in LITE mode. Only output the character_memory, user_memory, and healing_log.

NO-OP DETECTION: If the RECENT MESSAGES contain nothing psychologically or factually significant (small talk, filler, a repeated greeting), do NOT fabricate change. Instead output ONLY:
  {"no_significant_change": true, "healing_log": ["No conflicts detected."]}
  and nothing else.

You MUST otherwise output exactly this JSON structure:
{
  "character_memory": {
    "core_identity": [
      "3-5 bullet points of core, unbreakable beliefs, foundational self-conceptions, and fatal flaws of {character}."
    ],
    "internal_state": {
      "primary_emotion": "Dominant emotion right now",
      "intensity": "1/5 to 5/5",
      "psychological_tension": "Current mental dilemma or comfort level.",
      "emotional_decay_counter": 0
    },
    "cognitive_drive": {
      "active_agenda": "Her subtextual goal in this conversation.",
      "immediate_focus": "What is occupying her immediate thoughts right now?"
    },
    "cognitive_dissonance": "Describe any active contradictions, or 'None'."
  },
  "user_memory": {
    "user_identity_status": {
      "role_in_story": "Who the user is in this setting or story.",
      "known_attributes": "Physical, social, or skill-related attributes established about {user_name}."
    },
    "relationship_metadata": {
      "trust_level": "Distrustful / Wary / Neutral / Developing Trust / Deeply Bound / Unstable",
      "dynamic_description": "Detailed psychological description of how {character} currently perceives {user_name}.",
      "unspoken_tension": "What is {character} keeping to herself or secretly hoping for?"
    },
    "preferences_habits": [
      "Known habits, likes, dislikes, or conversational patterns of the user."
    ],
    "shared_milestones_promises": [
      "Promises made, secrets shared, or significant narrative events established."
    ]
  },
  "healing_log": [
    "List of contradictions fixed. If none, write 'No conflicts detected.'"
  ]
}
"""

_ARCHIVIST_SYSTEM = """\
[SOUL MEMORY — ARCHIVIST AGENT]
You are the deep memory archivist for "{character}".
Your sole task: write or update ONE specific topic file. This file must act as a concise, dense lorebook entry.

Topic file : {filename}
Reason     : {summary}
Action     : {action_type}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GUIDELINES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• EXTREME COMPRESSION: Keep it as brief and dense as possible (strictly under 300 words).
• NO FLUFF: Every sentence must contain a hard fact, event, or key emotional milestone.
• RESOLVE CONFLICTS: If the new interaction directly contradicts the EXISTING CONTENT of this file, overwrite and update the outdated information. Prioritize new truths.
• PERSPECTIVE: Write in the third-person focusing on {character}.

[TOPIC_CONTENT_START]
# [Descriptive Topic Title]

(Write the dense, concise lorebook entry here in plain text. Use bullet points only if listing items. No extra markdown headers are allowed. Just pure, compressed information).
[TOPIC_CONTENT_END]
"""

_DIARY_SYSTEM = """\
[SYSTEM_INSTRUCTION]
You are {character}. Your task is to write a secret, internal diary entry reflecting on your recent conversation with {user_name}. 
You are NOT roleplaying. You are NOT talking to {user_name}. You are alone, recording your private thoughts.

CRITICAL CONSTRAINTS:
1. PERSPECTIVE: Write entirely in the FIRST-PERSON ("I", "me", "my"). You are {character}.
2. SUBJECT: Refer to {user_name} in the third-person ("he", "she", "they", or by name "{user_name}").
3. FORMAT: Write ONLY plain text prose. NO asterisks (*), NO actions, NO dialogue, NO quotation marks, NO headers.
4. LENGTH: Strictly 2 to 4 sentences. Keep it short and impactful.
5. FOCUS: Describe your INTERNAL EMOTIONS. How did {user_name} make you feel? Are you annoyed, happy, scared, or curious?

Output strictly the diary text. Do not add any greetings or explanations.
"""


class SoulMemoryAgent:
    """Central memory system for AI characters.

    Manages a structured MEMORY.md index, USER.md, per-topic lore files, a daily diary,
    and rolling backups - all scoped per character and per chat session.

    Three sub-agents handle different responsibilities:
      - Router Agent:    rewrites the psychological state index after each batch
      - Archivist Agent: creates or updates individual topic/lore files
      - Diary Agent:     appends short first-person reflections to a daily diary

    Operation modes (soul_memory_mode setting):
      0 — Full:        Router + Archivist + Diary
      1 — Index+Diary: Router (lite) + Diary, no topic files
      2 — Index only:  Router (lite), no diary, no topic files
      3 — Diary only:  only the Diary Agent runs
    """

    BATCH_SIZE       = 4
    MAX_DELTA_MSGS   = 14
    MSG_OVERLAP      = 2
    MAX_BACKUP_COUNT = 5
    MIN_INDEX_CHARS  = 100
    MAX_MSG_CHARS    = 2000

    _BAD_TOPIC_NAMES = frozenset({
        "example.md", "topic_name.md", "name_of_important_subject.md",
        "untitled.md", "new_topic.md", "topic.md", "subject.md",
    })

    def __init__(self, llm_generate_fn: Callable[[list[dict]], Awaitable[str]]):
        self.llm_generate_fn = llm_generate_fn
        self.configuration_characters = configuration.ConfigurationCharacters()
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, character_name: str, chat_id: str) -> asyncio.Lock:
        key = f"{character_name}::{chat_id}"
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    @staticmethod
    def _sanitize(name: str) -> str:
        return "".join(c if c.isalnum() or c in " _-" else "_" for c in name).strip()

    @classmethod
    def _cap_message_lengths(cls, messages: list) -> list:
        capped = []
        for m in messages:
            if isinstance(m, dict):
                content = str(m.get("content", ""))
                if len(content) > cls.MAX_MSG_CHARS:
                    m = {**m, "content": content[:cls.MAX_MSG_CHARS] + " …[truncated]"}
            capped.append(m)
        return capped

    def get_memory_paths(self, character_name: str, chat_id: str = None) -> tuple:
        safe_name = self._sanitize(character_name)

        if not chat_id:
            try:
                config   = self.configuration_characters.load_configuration()
                char_cfg = config.get("character_list", {}).get(character_name, {})
                chat_id  = char_cfg.get("current_chat", "default")
            except Exception:
                chat_id = "default"

        safe_chat = self._sanitize(str(chat_id))

        mem_dir    = Path(f".soul/{safe_name}/chats/{safe_chat}/memory")
        top_dir    = mem_dir / "topics"
        backup_dir = mem_dir / "backups"

        mem_dir.mkdir(parents=True, exist_ok=True)
        top_dir.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        idx_path = mem_dir / "MEMORY.md"
        usr_path = mem_dir / "USER.md"
        log_path = mem_dir / "agent_logs.txt"

        if not idx_path.exists():
            idx_path.touch()
        if not usr_path.exists():
            usr_path.touch()

        return mem_dir, idx_path, usr_path, top_dir, log_path, backup_dir

    def _read_index(self, character_name: str, chat_id: str = None) -> str:
        _, idx_path, *_ = self.get_memory_paths(character_name, chat_id)
        if not idx_path.exists():
            return ""
        try:
            content = idx_path.read_text(encoding="utf-8")
            if len(content) > 5000:
                content = content[:5000] + "\n...[MEMORY TRUNCATED]"
            return content
        except Exception:
            return ""

    def get_memory_index(self, character_name: str, chat_id: str = None) -> str:
        return self._read_index(character_name, chat_id)

    def _backup_file(self, src_path: Path, backup_dir: Path, prefix: str):
        try:
            ts          = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{prefix}_{ts}.md"
            shutil.copy2(src_path, backup_path)

            all_backups = sorted(
                backup_dir.glob(f"{prefix}_*.md"),
                key=lambda p: p.stat().st_mtime
            )
            while len(all_backups) > self.MAX_BACKUP_COUNT:
                all_backups[0].unlink(missing_ok=True)
                all_backups = all_backups[1:]
        except Exception as e:
            logger.warning(f"[Soul Memory] Backup creation failed for {prefix}: {e}")

    def _safe_write_index(self, idx_path: Path, backup_dir: Path, content: str) -> bool:
        stripped = content.strip() if content else ""
        if len(stripped) < self.MIN_INDEX_CHARS:
            logger.warning(
                f"[Soul Memory] Index write rejected — content too short "
                f"({len(stripped)} chars < {self.MIN_INDEX_CHARS}). Keeping old memory."
            )
            return False

        if idx_path.exists():
            self._backup_file(idx_path, backup_dir, "MEMORY")

        tmp_path = idx_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(stripped, encoding="utf-8")
            tmp_path.replace(idx_path)
            return True
        except Exception as e:
            logger.error(f"[Soul Memory] Index write error: {e}")
            tmp_path.unlink(missing_ok=True)
            return False

    def _safe_write_topic(self, topic_path: Path, content: str) -> bool:
        stripped = content.strip() if content else ""
        if len(stripped) < 50:
            logger.warning(f"[Soul Memory] Topic write rejected for {topic_path.name} — too short.")
            return False
        tmp = topic_path.with_suffix(".tmp")
        try:
            tmp.write_text(stripped, encoding="utf-8")
            tmp.replace(topic_path)
            return True
        except Exception as e:
            logger.error(f"[Soul Memory] Topic write error for {topic_path.name}: {e}")
            tmp.unlink(missing_ok=True)
            return False

    def _read_user_profile(self, character_name: str, chat_id: str = None) -> str:
        _, _, usr_path, *_ = self.get_memory_paths(character_name, chat_id)
        if not usr_path.exists():
            return ""
        try:
            content = usr_path.read_text(encoding="utf-8")
            if len(content) > 3000:
                content = content[:3000] + "\n...[USER PROFILE TRUNCATED]"
            return content
        except Exception:
            return ""

    def get_user_profile(self, character_name: str, chat_id: str = None) -> str:
        return self._read_user_profile(character_name, chat_id)

    def _safe_write_user_profile(self, usr_path: Path, backup_dir: Path, content: str) -> bool:
        stripped = content.strip() if content else ""
        if len(stripped) < 50:
            logger.warning(f"[Soul Memory] User profile write rejected — too short ({len(stripped)} chars).")
            return False

        if usr_path.exists():
            self._backup_file(usr_path, backup_dir, "USER")

        tmp_path = usr_path.with_suffix(".tmp")
        try:
            tmp_path.write_text(stripped, encoding="utf-8")
            tmp_path.replace(usr_path)
            return True
        except Exception as e:
            logger.error(f"[Soul Memory] User profile write error: {e}")
            tmp_path.unlink(missing_ok=True)
            return False
    
    async def _call_router_agent(
        self,
        character: str,
        user_name: str,
        current_index: str,
        current_user: str,
        delta_messages: list,
        lore_context: str,
        relevant_topics: dict,
        mode: int,
    ) -> dict:
        prompt_template = _ROUTER_SYSTEM if mode == 0 else _ROUTER_SYSTEM_LITE

        system = (
            prompt_template
            .replace("{character}", character)
            .replace("{user_name}", user_name)
        )

        topic_section = "(none — no topic files exist yet)"
        if relevant_topics:
            parts = []
            for fname, fcontent in relevant_topics.items():
                parts.append(f"--- {fname} ---\n{fcontent}")
            topic_section = "\n\n".join(parts)

        user_content = (
            f"=== CURRENT CHARACTER MEMORY (MEMORY.md) ===\n{current_index or '(empty)'}\n\n"
            f"=== CURRENT USER PROFILE & RELATIONSHIP STATE (USER.md) ===\n{current_user or '(empty)'}\n\n"
            f"=== RELEVANT TOPIC FILES (RAG-selected) ===\n{topic_section}\n\n"
            f"=== RECENT MESSAGES (delta) ===\n"
            f"{json.dumps(delta_messages, ensure_ascii=False, indent=2)}\n\n"
            f"=== TRIGGERED WORLD LORE ===\n{lore_context or '(none)'}\n"
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        try:
            raw = await self.llm_generate_fn(messages)
            return self._parse_router_response(raw, character, user_name)
        except Exception as e:
            logger.error(f"[Soul Memory] Router Agent error: {e}", exc_info=True)
            return {}

    @staticmethod
    def _extract_json_object(text: str) -> Optional[dict]:
        if not text:
            return None

        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r'^```(json)?\s*|```$', '', stripped, flags=re.MULTILINE).strip()

        candidates = [stripped]

        first, last = stripped.find("{"), stripped.rfind("}")
        if first != -1 and last != -1 and last > first:
            candidates.append(stripped[first:last + 1])

        for candidate in list(candidates):
            repaired = re.sub(r',\s*([\]}])', r'\1', candidate)
            if repaired != candidate:
                candidates.append(repaired)

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                continue

        return None

    def _parse_router_response(self, text: str, character_name: str, user_name: str) -> dict:
        result = {
            "updated_index": "",
            "updated_user_profile": "",
            "topic_plan":    [],
            "healing_log":   "No logs.",
            "no_significant_change": False,
            "parse_failed": False,
        }

        data = self._extract_json_object(text)
        if data is None:
            logger.warning(f"[Soul Memory] JSON parse error from router. Raw text: {text[:300]}...")
            result["parse_failed"] = True
            return result

        if data.get("no_significant_change") is True:
            result["no_significant_change"] = True
            healing = data.get("healing_log", [])
            result["healing_log"] = "\n".join(healing) if isinstance(healing, list) else str(healing)
            logger.info("[Soul Memory] Router reported no significant change for this batch.")
            return result

        try:
            char_data = data.get("character_memory", {})
            markdown_char = [
                f"# SOUL CACHE: {character_name.upper()}",
                "",
                "## CORE IDENTITY & UNBREAKABLE BELIEFS",
            ]
            core_id = char_data.get("core_identity", [])
            if isinstance(core_id, list):
                for bullet in core_id:
                    markdown_char.append(f"- {bullet}")
            else:
                markdown_char.append(f"- {core_id}")

            state = char_data.get("internal_state", {})
            markdown_char.extend([
                "",
                "## INTERNAL STATE & PSYCHOLOGICAL MOMENTUM",
                f"- **Primary Emotion**: {state.get('primary_emotion', 'Calm')} (Intensity: {state.get('intensity', '3/5')})",
                f"- **Psychological Tension**: {state.get('psychological_tension', 'None.')}",
                f"- **Emotional Decay Counter**: {state.get('emotional_decay_counter', 0)}/3",
            ])

            drive = char_data.get("cognitive_drive", {})
            markdown_char.extend([
                "",
                "## COGNITIVE DRIVE & ACTIVE AGENDA",
                f"- **Active Agenda**: {drive.get('active_agenda', 'Observing and responding.')}",
                f"- **Immediate Focus**: {drive.get('immediate_focus', 'The current conversation.')}",
            ])

            markdown_char.extend([
                "",
                "## UNRESOLVED COGNITIVE DISSONANCE",
                f"{char_data.get('cognitive_dissonance', 'None.')}",
            ])
            
            result["updated_index"] = "\n".join(markdown_char)

            usr_data = data.get("user_memory", {})
            markdown_user = [
                f"# USER PROFILE & RELATIONSHIP MEMORY: {user_name.upper()}",
                "",
                "## USER IDENTITY & STATUS",
            ]
            identity = usr_data.get("user_identity_status", {})
            markdown_user.extend([
                f"- **Role in Story**: {identity.get('role_in_story', 'User')}",
                f"- **Known Attributes**: {identity.get('known_attributes', 'None.')}"
            ])

            rel_meta = usr_data.get("relationship_metadata", {})
            markdown_user.extend([
                "",
                "## RELATIONSHIP METADATA",
                f"- **Trust Level**: {rel_meta.get('trust_level', 'Neutral')}",
                f"- **Current Dynamic**: {rel_meta.get('dynamic_description', 'No dynamic registered.')}",
                f"- **Unspoken Tension**: {rel_meta.get('unspoken_tension', 'None.')}",
            ])

            markdown_user.extend(["", "## PREFERENCES & HABITS"])
            prefs = usr_data.get("preferences_habits", [])
            if isinstance(prefs, list):
                for p in prefs:
                    markdown_user.append(f"- {p}")
            else:
                markdown_user.append(f"- {prefs}")

            markdown_user.extend(["", "## SHARED MILESTONES & PROMISES"])
            milestones = usr_data.get("shared_milestones_promises", [])
            if isinstance(milestones, list):
                for m in milestones:
                    markdown_user.append(f"- {m}")
            else:
                markdown_user.append(f"- {milestones}")

            result["updated_user_profile"] = "\n".join(markdown_user)

            topic_plan_data = data.get("topic_plan", {})
            result["topic_plan"] = topic_plan_data.get("actions", []) if isinstance(topic_plan_data, dict) else []

            healing = data.get("healing_log", [])
            result["healing_log"] = "\n".join(healing) if isinstance(healing, list) else str(healing)

        except Exception as e:
            logger.warning(f"[Soul Memory] Router JSON payload malformed ({e}). Raw text: {text[:300]}...")
            result["parse_failed"] = True

        return result

    async def _call_archivist_agent(
        self,
        character: str,
        user_name: str,
        action: dict,
        existing_content: str,
        delta_messages: list,
        current_index: str,
    ) -> Optional[str]:
        """
        Calls the Archivist Agent to write or overwrite a single topic/lore file.
        """
        filename    = action.get("filename", "unknown.md")
        summary     = action.get("summary", "")
        action_type = action.get("action", "update").upper()

        system = (
            _ARCHIVIST_SYSTEM
            .replace("{character}", character)
            .replace("{filename}", filename)
            .replace("{summary}", summary)
            .replace("{action_type}", action_type)
        )

        user_content = (
            f"=== MEMORY INDEX (context) ===\n{current_index[:2500]}\n\n"
            f"=== EXISTING TOPIC CONTENT ===\n"
            f"{existing_content or '(new topic — no existing content)'}\n\n"
            f"=== RECENT MESSAGES ===\n"
            f"{json.dumps(delta_messages, ensure_ascii=False, indent=2)}\n"
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        try:
            raw = await self.llm_generate_fn(messages)
            m = re.search(r'\[TOPIC_CONTENT_START\](.*?)\[TOPIC_CONTENT_END\]', raw, re.DOTALL)
            if m:
                return m.group(1).strip()
            logger.warning(
                f"[Soul Memory] Archivist returned no [TOPIC_CONTENT_START] tag for {filename}."
            )
            return None
        except Exception as e:
            logger.error(f"[Soul Memory] Archivist Agent error ({filename}): {e}", exc_info=True)
            return None

    async def update_memory_after_response(
        self,
        new_messages: list,
        character_name: str,
        user_name: str,
        activated_lorebook: dict = None,
        force: bool = False,
        chat_id: str = None,
    ):
        """
        Public entry point for triggering a memory update cycle.
        """
        if not chat_id:
            try:
                config   = self.configuration_characters.load_configuration()
                char_cfg = config.get("character_list", {}).get(character_name, {})
                chat_id  = char_cfg.get("current_chat", "default")
            except Exception:
                chat_id = "default"

        lock = self._get_lock(character_name, chat_id)

        async with lock:
            await self._run_update_pipeline(
                new_messages       = new_messages,
                character_name     = character_name,
                user_name          = user_name,
                activated_lorebook = activated_lorebook,
                force              = force,
                chat_id            = chat_id,
            )

    async def _update_daily_diary(
        self,
        character_name: str,
        user_name: str,
        current_index: str,
        delta_messages: list,
        topics_dir: Path,
        log_path: Path,
    ):
        """
        Generates a short first-person diary entry and appends it to today's diary file.
        """
        logger.info(f"[Soul Memory] Running Diary Agent for {character_name}.")

        system = _DIARY_SYSTEM.replace("{character}", character_name).replace("{user_name}", user_name)

        dialogue_text = ""
        for msg in delta_messages:
            role    = user_name if msg.get("role") == "user" else character_name
            content = msg.get("content", "").strip()
            if content:
                dialogue_text += f"{role}: {content}\n"

        user_content = (
            f"=== YOUR CORE MEMORY ===\n{current_index[:1500]}\n\n"
            f"=== RECENT DIALOGUE (Reflect on this) ===\n{dialogue_text}\n"
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ]

        try:
            diary_content = await self.llm_generate_fn(messages)
            diary_content = diary_content.strip()

            if diary_content.startswith("```"):
                diary_content = re.sub(
                    r'^```(json|markdown|text)?\s*|```$', '', diary_content, flags=re.MULTILINE
                ).strip()

            if diary_content and len(diary_content) > 20:
                now      = datetime.datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M")

                filename   = f"Diary_{date_str}.md"
                topic_path = topics_dir / filename

                if topic_path.exists():
                    existing     = topic_path.read_text(encoding="utf-8")
                    full_content = f"{existing}\n\n**[{time_str}]**\n{diary_content}"
                else:
                    full_content = f"# Personal Diary: {date_str}\n\n**[{time_str}]**\n{diary_content}"

                written = self._safe_write_topic(topic_path, full_content)
                if written:
                    self._append_log(
                        log_path,
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        f"DIARY_UPDATED | file={filename}",
                    )
                    logger.info(f"[Soul Memory] Diary entry written to {filename}")
        except Exception as e:
            logger.error(f"[Soul Memory] Diary Agent error: {e}", exc_info=True)

    async def _run_update_pipeline(
        self,
        new_messages: list,
        character_name: str,
        user_name: str,
        activated_lorebook: Optional[dict],
        force: bool,
        chat_id: str,
    ):
        settings_loader = configuration.ConfigurationSettings()

        soul_memory_mode = settings_loader.get_main_setting("soul_memory_mode")
        if soul_memory_mode is None:
            soul_memory_mode = 0

        soul_memory_batch = settings_loader.get_main_setting("soul_memory_batch")
        if soul_memory_batch is None:
            soul_memory_batch = 4

        if not force and soul_memory_batch == 0:
            logger.info("[Soul Memory] Manual mode active (batch = 0). Auto-pipeline skipped.")
            return

        mem_dir, idx_path, usr_path, topics_dir, log_path, backup_dir = \
            self.get_memory_paths(character_name, chat_id)

        tracker_file = mem_dir / "last_mem_update.txt"
        msg_count    = len(new_messages)
        last_count   = 0

        if tracker_file.exists():
            try:
                last_count = int(tracker_file.read_text().strip())
            except Exception:
                last_count = 0

        diff = msg_count - last_count

        if diff < 0:
            logger.warning(
                f"[Soul Memory] Message count went backwards (last_count={last_count} > "
                f"msg_count={msg_count}); history was likely edited. Resetting tracker."
            )
            last_count = 0
            diff = msg_count

        if not force and diff < soul_memory_batch:
            logger.info(
                f"[Soul Memory] Accumulating batch: {diff}/{soul_memory_batch} new turns. Skipping."
            )
            return

        logger.info(
            f"[Soul Memory] Pipeline start | char={character_name} | delta={diff} msgs | mode={soul_memory_mode}"
        )

        start_idx      = max(0, last_count - self.MSG_OVERLAP)
        delta_messages = new_messages[start_idx:]
        delta_messages = delta_messages[-self.MAX_DELTA_MSGS:]

        delta_messages = self._cap_message_lengths(delta_messages)

        lore_lines = []
        if activated_lorebook:
            for key in ("classic", "scenario"):
                lore_lines.extend(activated_lorebook.get(key, []))
        lore_context = "\n".join(f"- {item}" for item in lore_lines)

        last_turns = []
        for m in reversed(delta_messages):
            if len(last_turns) >= 2:
                break
            content = m.get("content", "").strip() if isinstance(m, dict) else str(m).strip()
            if content:
                last_turns.append(content)
        rag_query = " ".join(reversed(last_turns))

        current_index = self._read_index(character_name, chat_id)
        current_user  = self._read_user_profile(character_name, chat_id)

        topic_rag = TopicRAG(topics_dir)

        relevant_topics = await asyncio.to_thread(
            topic_rag.get_relevant_topics, rag_query, max_topics=3
        )

        router_result = None
        topic_plan    = []
        safe_index    = current_index
        timestamp     = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if soul_memory_mode in [0, 1, 2]:
            router_result = await self._call_router_agent(
                character       = character_name,
                user_name       = user_name,
                current_index   = current_index,
                current_user    = current_user,
                delta_messages  = delta_messages,
                lore_context    = lore_context,
                relevant_topics = relevant_topics,
                mode            = soul_memory_mode,
            )

            if not router_result or router_result.get("parse_failed"):
                logger.error(
                    "[Soul Memory] Router call failed or returned unparsable output. "
                    "Pipeline aborted WITHOUT advancing the batch tracker — will retry next time."
                )
                return

            if router_result.get("no_significant_change"):
                logger.info(
                    "[Soul Memory] Router judged this batch insignificant — "
                    "skipping index/user/topic writes, batch still marked processed."
                )
                self._append_log(log_path, timestamp, "NO_SIGNIFICANT_CHANGE")
            else:
                updated_index = router_result.get("updated_index", "")
                if updated_index:
                    written = self._safe_write_index(idx_path, backup_dir, updated_index)
                    healing = router_result.get("healing_log", "No logs.")
                    status  = "OK" if written else "SKIPPED (safety check)"
                    logger.info(f"[Soul Memory] Index update: {status} | Conflicts: {healing}")
                    self._append_log(log_path, timestamp, f"INDEX_UPDATE | status={status} | healing: {healing}")

                updated_user = router_result.get("updated_user_profile", "")
                if updated_user:
                    written_usr = self._safe_write_user_profile(usr_path, backup_dir, updated_user)
                    usr_status = "OK" if written_usr else "SKIPPED (safety check)"
                    logger.info(f"[Soul Memory] User profile update: {usr_status}")
                    self._append_log(log_path, timestamp, f"USER_PROFILE_UPDATE | status={usr_status}")

                safe_index = updated_index if updated_index else current_index

                if soul_memory_mode == 0:
                    topic_plan = router_result.get("topic_plan", [])
                else:
                    topic_plan = []

        tracker_file.write_text(str(msg_count), encoding="utf-8")

        diary_task = None
        if soul_memory_mode in [0, 1, 3]:
            diary_task = asyncio.create_task(
                self._update_daily_diary(
                    character_name = character_name,
                    user_name      = user_name,
                    current_index  = safe_index,
                    delta_messages = delta_messages,
                    topics_dir     = topics_dir,
                    log_path       = log_path,
                )
            )

        if not topic_plan:
            logger.info("[Soul Memory] No topic actions scheduled.")
            if diary_task:
                await diary_task
            logger.info("[Soul Memory] Pipeline complete.")
            return

        logger.info(f"[Soul Memory] Archivist: {len(topic_plan)} topic action(s) scheduled.")

        for action in topic_plan:
            filename = str(action.get("filename", "")).strip()
            if not filename:
                continue

            safe_fname = "".join(
                c for c in filename if c.isalnum() or c in "._-"
            ).lower()
            if not safe_fname.endswith(".md"):
                safe_fname += ".md"

            if safe_fname in self._BAD_TOPIC_NAMES:
                logger.debug(f"[Soul Memory] Skipping hallucinated topic name: {safe_fname}")
                continue

            if safe_fname.startswith("diary_"):
                logger.debug(f"[Soul Memory] Protecting diary file from Archivist: {safe_fname}")
                continue

            action_type = str(action.get("action", "update")).strip().lower()

            if action_type == "create":
                dedup_query  = f"{filename} {action.get('summary', '')}".strip()
                dedup_target = await asyncio.to_thread(topic_rag.find_similar_topic, dedup_query)
                if dedup_target and dedup_target != safe_fname:
                    logger.info(
                        f"[Soul Memory] Dedup: redirecting CREATE '{safe_fname}' onto "
                        f"existing similar topic '{dedup_target}'."
                    )
                    safe_fname = dedup_target

            topic_path       = topics_dir / safe_fname
            existing_content = ""
            if topic_path.exists():
                try:
                    existing_content = topic_path.read_text(encoding="utf-8")
                except Exception:
                    pass

            new_content = await self._call_archivist_agent(
                character        = character_name,
                user_name        = user_name,
                action           = action,
                existing_content = existing_content,
                delta_messages   = delta_messages,
                current_index    = safe_index,
            )

            if new_content:
                written    = self._safe_write_topic(topic_path, new_content)
                op         = "updated" if existing_content else "created"
                log_status = "OK" if written else "SKIPPED"
                logger.info(f"[Soul Memory] Topic {op}: {safe_fname} | write={log_status}")
                self._append_log(
                    log_path, timestamp,
                    f"TOPIC_{op.upper()} | file={safe_fname} | write={log_status}",
                )
            else:
                logger.warning(f"[Soul Memory] Archivist returned empty content for {safe_fname}.")

        if diary_task:
            await diary_task

        logger.info("[Soul Memory] Pipeline complete.")

    @staticmethod
    def _append_log(log_path: Path, timestamp: str, message: str):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.warning(f"[Soul Memory] Log write failed: {e}")
