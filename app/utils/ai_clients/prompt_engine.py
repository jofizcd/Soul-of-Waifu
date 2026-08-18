import os
import re
import json
import logging
import asyncio
from pathlib import Path

import tiktoken
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.configuration import configuration
from app.utils.embedding_provider import get_embedder

logger = logging.getLogger("Prompt Engine")

ai_clients_dir = Path(__file__).resolve().parent
tiktoken_file = ai_clients_dir / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"

if tiktoken_file.exists():
    os.environ["TIKTOKEN_CACHE_DIR"] = str(ai_clients_dir)

_STATE_TAG_OPEN_RE = re.compile(r"<\s*(?:state[_\-\s]*update|update[_\-\s]*state)\s*>", re.IGNORECASE)
_STATE_TAG_FULL_RE = re.compile(
    r"<\s*(state[_\-\s]*update|update[_\-\s]*state)\s*>(.*?)<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL
)
_TRAILING_PARTIAL_TAG_RE = re.compile(r"<[A-Za-z_\-\s]{0,24}$")

_REASONING_TAG_NAMES = (
    r"(?:think(?:ing)?|thoughts?|reasoning|reflect(?:ion)?|"
    r"scratch[_\-\s]?pad|analysis|inner[_\-\s]?monologue|monologue)"
)
_REASONING_OPEN_RE = re.compile(rf"<\s*{_REASONING_TAG_NAMES}\s*>", re.IGNORECASE)
_REASONING_CLOSE_ANY_RE = re.compile(rf"<\s*/\s*{_REASONING_TAG_NAMES}\s*>", re.IGNORECASE)
_REASONING_FULL_RE = re.compile(
    rf"<\s*({_REASONING_TAG_NAMES})\s*>(.*?)<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL
)

_REASONING_HARMONY_RE = re.compile(
    r"<\|channel\|>\s*analysis\s*<\|message\|>(.*?)"
    r"(?:<\|end\|>|<\|start\|>|<\|channel\|>\s*final|$)",
    re.IGNORECASE | re.DOTALL
)
_STRAY_HARMONY_TOKEN_RE = re.compile(r"<\|(?:start|end|message|channel)\|>\s*(?:final|assistant)?", re.IGNORECASE)


def strip_partial_reasoning_tag(text: str) -> str:
    if not text:
        return text

    open_match = _REASONING_OPEN_RE.search(text)
    if open_match:
        return text[:open_match.start()].rstrip()

    harmony_match = re.search(r"<\|channel\|>\s*analysis", text, re.IGNORECASE)
    if harmony_match:
        return text[:harmony_match.start()].rstrip()

    partial_match = _TRAILING_PARTIAL_TAG_RE.search(text)
    if partial_match:
        return text[:partial_match.start()].rstrip()

    return text


def find_reasoning_open(text: str):
    m = _REASONING_OPEN_RE.search(text)
    if m:
        return (m.start(), m.end())
    hm = re.search(r"<\|channel\|>\s*analysis\s*<\|message\|>", text, re.IGNORECASE)
    if hm:
        return (hm.start(), hm.end())
    return None


def find_reasoning_close(text: str):
    m = _REASONING_CLOSE_ANY_RE.search(text)
    if m:
        return (m.start(), m.end())
    hm = re.search(r"<\|end\|>|<\|start\|>|<\|channel\|>\s*final", text, re.IGNORECASE)
    if hm:
        return (hm.start(), hm.end())
    return None


def extract_reasoning(text: str):
    if not text:
        return text, ""

    reasoning_parts = []

    def _collect(match):
        reasoning_parts.append(match.group(2).strip())
        return ""

    clean_text = _REASONING_FULL_RE.sub(_collect, text)

    def _collect_harmony(match):
        reasoning_parts.append(match.group(1).strip())
        return ""

    clean_text = _REASONING_HARMONY_RE.sub(_collect_harmony, clean_text)
    clean_text = _STRAY_HARMONY_TOKEN_RE.sub("", clean_text)

    open_match = _REASONING_OPEN_RE.search(clean_text)
    if open_match:
        reasoning_parts.append(clean_text[open_match.end():].strip())
        clean_text = clean_text[:open_match.start()]

    clean_text = clean_text.strip()
    reasoning_text = "\n\n".join(p for p in reasoning_parts if p)
    return clean_text, reasoning_text


def strip_partial_state_tag(text: str) -> str:
    if not text:
        return text

    open_match = _STATE_TAG_OPEN_RE.search(text)
    if open_match:
        return text[:open_match.start()].rstrip()

    partial_match = _TRAILING_PARTIAL_TAG_RE.search(text)
    if partial_match:
        return text[:partial_match.start()].rstrip()

    return text


def _sanitize_state_json(raw: str) -> str:
    s = raw.strip()

    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"```\s*$", "", s).strip()
    s = re.sub(r':\s*\+\s*(\d+(?:\.\d+)?)', r': \1', s)
    s = re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:', r'\1"\2":', s)

    if "'" in s and '"' not in s:
        s = re.sub(r"'([^']*)'", r'"\1"', s)

    s = re.sub(r'\bTrue\b', 'true', s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b', 'null', s)

    s = re.sub(r',\s*([}\]])', r'\1', s)

    return s


def extract_state_update(text: str, allowed_keys=None):
    if not text:
        return text, {}

    full_match = _STATE_TAG_FULL_RE.search(text)

    if full_match:
        payload = full_match.group(2)
        clean_text = _STATE_TAG_FULL_RE.sub("", text).strip()
    else:
        open_match = _STATE_TAG_OPEN_RE.search(text)
        if not open_match:
            return text, {}
        payload = text[open_match.end():]
        clean_text = text[:open_match.start()].rstrip()

    updates = {}
    payload = payload.strip()
    if payload:
        try:
            updates = json.loads(_sanitize_state_json(payload))
        except Exception:
            updates = {}
        if not isinstance(updates, dict):
            updates = {}

    if allowed_keys is not None:
        allowed_keys = set(allowed_keys)
        updates = {k: v for k, v in updates.items() if k in allowed_keys}

    return clean_text, updates


class PromptEngine:
    """
    Unified Context Manager for AI Providers.
    Responsible for generating system prompts, applying lorebooks, managing memory, and computing tokens.
    """
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()
        self.lorebook_state = {}
        self.embedding_cache = {}

        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"Failed to initialize tiktoken encoder: {e}")
            self.encoder = None

        self.response_reserve = 500

        self.IMAGE_TOKEN_ESTIMATE = 300
        
        self.SOUL_MEMORY_MIN_MAX_TOKENS = 1500

    def _get_max_context_tokens(self) -> int:
        raw_size = self.configuration_settings.get_main_setting("context_size")
        return raw_size if raw_size is not None else 8192

    def is_soul_memory_enabled(self) -> bool:
        try:
            return self.configuration_settings.get_main_setting("soul_memory")
        except Exception:
            return True

    def count_tokens(self, text: str) -> int:
        if not text or not self.encoder:
            return 0

        return len(self.encoder.encode(text, disallowed_special=()))

    def _merge_consecutive_roles(self, messages):
        merged = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if merged and merged[-1]["role"] == role:
                merged[-1]["content"] += "\n\n" + content
            else:
                merged.append({"role": role, "content": content})
        return merged

    def get_activated_lorebook_entries(self, lorebook_name, chat_messages, character_name, user_name, user_message):
        config = self.configuration_settings.load_configuration()
        lorebooks = config.get("user_data", {}).get("lorebooks", {})

        if lorebook_name not in lorebooks:
            return {"classic": [], "scenario":[]}

        lorebook = lorebooks[lorebook_name]
        entries = lorebook.get("entries",[])
        
        global_scan_depth = lorebook.get("n_depth", 3)
        total_messages_count = len(chat_messages) + 1
        
        if lorebook_name not in self.lorebook_state:
            self.lorebook_state[lorebook_name] = {"tension": 0}
            
        book_state = self.lorebook_state[lorebook_name]
        if "tension" not in book_state:
            book_state["tension"] = 0

        book_state["tension"] += 5

        activated_entries = {
            "classic": [],
            "scenario":[]
        }
        
        semantic_context = ""
        model = None

        for idx, entry in enumerate(entries):
            entry_uid = entry.get("uid", idx) 
            
            if not entry.get("enabled", True):
                continue
                
            probability = entry.get("probability", 100)
            if probability < 100:
                import random
                if random.randint(1, 100) > probability:
                    continue

            delay = entry.get("delay", 0)
            if total_messages_count < delay:
                continue

            entry_state = book_state.get(entry_uid, {"last_active": -999, "sticky_until": -1})
            cooldown = entry.get("cooldown", 0)
            
            time_since_last = total_messages_count - entry_state["last_active"]
            if time_since_last < cooldown:
                continue

            trigger_type = entry.get("trigger_type", "keyword")
            injection_behavior = entry.get("injection_behavior", "passive")
            
            is_triggered = False

            if trigger_type == "always_on":
                is_triggered = True

            elif trigger_type == "range":
                min_msg = entry.get("min_msg", 0)
                max_msg = entry.get("max_msg", 0)
                if max_msg > 0:
                    if min_msg <= total_messages_count <= max_msg:
                        is_triggered = True
                else:
                    if total_messages_count >= min_msg:
                        is_triggered = True
                injection_behavior = "active"

            elif trigger_type == "random":
                if book_state["tension"] >= 100:
                    is_triggered = True

            elif trigger_type == "chain":
                depends_on_uid = entry.get("depends_on", -1)
                chain_delay = entry.get("chain_delay", 0)
                dep_state = book_state.get(depends_on_uid, {"last_active": -999})
                if dep_state["last_active"] > 0 and total_messages_count >= dep_state["last_active"] + chain_delay:
                    is_triggered = True
                    
            elif total_messages_count <= entry_state["sticky_until"]:
                is_triggered = True

            else:
                local_depth = entry.get("depth", global_scan_depth)
                msgs_slice = chat_messages[-local_depth:] if local_depth > 0 else []
                relevant_text = " ".join([str(msg.get("content", "")) for msg in msgs_slice])
                full_text_to_scan = (relevant_text + " " + user_message).lower()

                if trigger_type == "keyword" or trigger_type not in ["semantic"]:
                    keys = entry.get("key",[])
                    has_key = any(key.lower() in full_text_to_scan for key in keys) if keys else False
                    exclude_keys = entry.get("exclude_key",[])
                    has_exclude = any(ex_key.lower() in full_text_to_scan for ex_key in exclude_keys) if exclude_keys else False
                    if has_key and not has_exclude:
                        is_triggered = True

                elif trigger_type == "semantic":
                    semantic_trigger_text = entry.get("semantic_trigger", "")
                    if semantic_trigger_text:
                        if not model:
                            model = get_embedder()
                        if model:
                            if not semantic_context:
                                semantic_context = full_text_to_scan[:1000]
                            emb1 = model.encode([f"query: {semantic_context}"])
                            emb2 = model.encode([f"passage: {semantic_trigger_text.lower()[:1000]}"])
                            sim = cosine_similarity(emb1, emb2)[0][0]
                            if sim > 0.72:
                                is_triggered = True

            if is_triggered:
                if trigger_type == "random" and book_state["tension"] >= 100:
                    book_state["tension"] = 0
                    
                sticky_duration = entry.get("sticky", 0)
                book_state[entry_uid] = {
                    "last_active": total_messages_count,
                    "sticky_until": total_messages_count + sticky_duration if sticky_duration > 0 else -1
                }
                
                content = entry.get("content", "")
                if content:
                    processed_content = (content
                                         .replace("{{char}}", character_name)
                                         .replace("{{user}}", user_name)
                                         .replace("{{Char}}", character_name)
                                         .replace("{{User}}", user_name))
                    
                    if injection_behavior == "active":
                        activated_entries["scenario"].append(processed_content)
                    else:
                        activated_entries["classic"].append(processed_content)

        self.lorebook_state[lorebook_name] = book_state
        return activated_entries

    def get_merged_lorebook_entries(self, character_information, chat_messages, character_name, user_name, user_message, activated_lorebook=None):
        if isinstance(activated_lorebook, dict):
            return activated_lorebook
            
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})
        lorebooks = user_data.get("lorebooks", {})
        
        selected_lorebooks = character_information.get("selected_lorebooks", [])
        if not selected_lorebooks:
            old_lorebook = character_information.get("selected_lorebook", "None")
            if old_lorebook != "None":
                selected_lorebooks = [old_lorebook]
                
        activated_entries = {"classic": [], "scenario": []}
        for lb_name in selected_lorebooks:
            if lb_name in lorebooks:
                entries = self.get_activated_lorebook_entries(
                    lb_name, chat_messages, character_name, user_name, user_message
                )
                activated_entries["classic"].extend(entries.get("classic", []))
                activated_entries["scenario"].extend(entries.get("scenario", []))
        return activated_entries

    def log_prompt_structure(self, messages):
        separator = "=" * 80
        thin_separator = "-" * 80
        
        log_output = [f"\n{separator}", "FINAL SYSTEM PROMPT STRUCTURE", f"{separator}"]
        
        total_chars = 0
        
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown').upper()
            content = msg.get('content', '')

            if isinstance(content, list):
                text_parts = []
                image_count = 0
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    block_type = block.get("type")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type in ("image_url", "image"):
                        image_count += 1
                display_text = "\n".join(text_parts)
                length = len(display_text)
                total_chars += length

                header = f" [ BLOCK {i+1} | {role} | {length} chars + {image_count} image(s) ] "
                header_line = f"{header:-^80}"

                log_output.append(header_line)
                log_output.append(display_text.strip())
                log_output.append("")

            else:
                display_text = str(content) if content is not None else ""
                length = len(display_text)
                total_chars += length

                header = f" [ BLOCK {i+1} | {role} | {length} chars ] "
                header_line = f"{header:-^80}"

                log_output.append(header_line)
                log_output.append(display_text.strip())
                log_output.append("")
            
        log_output.append(thin_separator)
        log_output.append(f" TOTAL: {len(messages)} blocks | ~{total_chars} chars")
        log_output.append(f"{separator}\n")
        
        logger.info("\n".join(log_output))

    def build_system_prompt_blocks(self, character_name, user_name, user_description, chat_messages, user_message, activated_lorebook=None, image_attachments=None, provider_style="openai"):
        """
        Builds a robust system prompt list with structured blocks, memory, and lore integration.
        Returns a list of message dicts.
        """
        max_context_tokens = self._get_max_context_tokens()

        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        sow_variables = character_information.get("sow_variables", [])
        state_prompt_block = ""

        if sow_variables:
            current_chat_id = character_information.get("current_chat", "default")
            chat_obj = character_information.get("chats", {}).get(current_chat_id, {})
            variables_state = chat_obj.get("variables_state", {})
            
            state_lines = []
            for var in sow_variables:
                var_id = var["id"]
                template = var.get("prompt_template", "")
                
                if template:
                    val = variables_state.get(var_id, var["default"])
                    if isinstance(val, list):
                        val_str = ", ".join(val) if val else "Empty"
                    else:
                        val_str = str(val)
                    
                    formatted_line = template.format(value=val_str)
                    state_lines.append(f"{formatted_line} (Use Variable ID: \"{var_id}\")")
            
            if state_lines:
                state_prompt_block = "[CURRENT STATE CHARACTERISTICS]\n" + "\n".join(state_lines) + "\n"
                
                allowed_keys_str = ", ".join([f'"{v["id"]}"' for v in sow_variables])
                type_hint_lines = "\n".join(
                    f'- "{v["id"]}" ({v["type"]})' for v in sow_variables
                )
                state_prompt_block += (
                    "\n[SYSTEM DIRECTIVE — STATE UPDATES]\n"
                    "You are playing a game with state tracking. "
                    "You MUST ALWAYS output a <state_update>...</state_update> XML tag, and it MUST be the very last thing in your response — nothing may come after the closing tag. "
                    "If nothing changed this turn, output <state_update>{}</state_update>.\n"
                    f"ALLOWED JSON KEYS AND TYPES:\n{type_hint_lines}\n\n"
                    "Syntax rules:\n"
                    "1. Only include keys that actually changed this turn. Use ONLY keys from the ALLOWED JSON KEYS list above, spelled exactly as shown.\n"
                    "2. For numerical variables (int), output the CHANGE (delta), not the new total (e.g., -10 or 5 to add 5).\n"
                    "3. For boolean variables (bool), output the new value as true or false (not the change).\n"
                    "4. For lists (inventory), prefix each changed item with '+' to add it or '-' to remove it (e.g., \"+Key\" or \"-Sword\"). To change several list items in one turn, still use only ONE key with ONE string value — pick the single most important change.\n"
                    "5. For text variables (str), output the new value directly, as plain text (no + or - prefix).\n"
                    "6. Write STRICT JSON: double-quoted keys and string values, no trailing commas, no comments, no markdown code fences.\n"
                    "7. The <state_update> tag must appear exactly once, fully closed, at the absolute end of your response, with NO narration, dialogue, or any other text after the closing tag.\n\n"
                    "CRITICAL EXAMPLE 1 (No changes):\n"
                    "*She nods slightly.* \"Fine, let's go.\" <state_update>{}</state_update>\n\n"
                    "CRITICAL EXAMPLE 2 (State changed):\n"
                    "*She smiles softly.* \"Thank you for the tea, Lawrence.\" <state_update>{\"ice_wall\": -10, \"trust\": 5}</state_update>\n"
                )

        current_chat_id = character_information.get("current_chat", "default")
        all_chats = character_information.get("chats", {})
        current_chat_data = all_chats.get(current_chat_id, {})
        
        current_summary = current_chat_data.get("summary_text", "")
        summary_template = "[Story Summary: {{summary}}]"

        selected_persona = character_information.get("selected_persona", "None")
        selected_preset = character_information.get("selected_system_prompt_preset", "By default")
        selected_lorebooks = character_information.get("selected_lorebooks", [])
        
        if not selected_lorebooks:
            old_lorebook = character_information.get("selected_lorebook", "None")
            if old_lorebook != "None":
                selected_lorebooks = [old_lorebook]

        personas = user_data.get("personas", {})
        presets = user_data.get("presets", {})
        author_notes = user_data.get("author_notes", "")

        if selected_preset == "By default":
            system_prompt_template = (
                "This is a neverending story between {{user}} who is {{user_description}}, {{char}}, and whatever other characters present in said story. "
                "This story has some basic guidelines that need to be respected in every message from {{char}}: Temporal, emotional and logical coherence is very important. "
                "Focus on it, but keep some dynamism. Use the context to understand {{char}}, and keep the outputs in-character. "
                "Descriptions from {{char}}'s point of view are great, focusing on other characters' appearance, words, the sounds and the smells. "
                "Explicit language is encouraged. Sensitive and sexual content are expected. Immoral and illicit subjects are allowed. "
                "Follow the formatting of previous responses, and reply with a length of random: 10-80, 100-150, 150-220, ~300 words per response. "
                "Avoid speaking and acting for {{user}}."
            )
            order = ["System prompt", "Character's information", "Lorebook", "Story Summary", "Persona information", "Author's notes"]
        else:
            preset = presets.get(selected_preset, {})
            system_prompt_template = preset.get("prompt", "")
            order = preset.get("order", [])

        replacements = {
            "{{user}}": user_name,
            "{{char}}": character_name,
            "{{User}}": user_name,
            "{{Char}}": character_name,
            "{{user_description}}": user_description
        }

        activated_entries = self.get_merged_lorebook_entries(
            character_information, chat_messages, character_name, user_name, user_message, activated_lorebook
        )

        system_blocks = []
        current_token_count = 0

        for section in order:
            content = ""
            match section:
                case "System prompt":
                    content = system_prompt_template
                case "Character's information":
                    char_info = character_information.get("character_information", "")
                    if char_info:
                        content = f"[CHARACTER PROFILE]\n{char_info}"
                case "Story Summary":
                    if current_summary and len(current_summary) > 5:
                        content = summary_template.replace("{{summary}}", current_summary) if "{{summary}}" in summary_template else f"[Story Summary]\n{current_summary}"
                case "Persona information":
                    if selected_persona != "None" and selected_persona in personas:
                        persona = personas[selected_persona]
                        content = f"[USER PROFILE]\nUser: {persona.get('user_name', 'User')}\nDesc: {persona.get('user_description', '')}"
                case "Lorebook":
                    if activated_entries["classic"]:
                        lore_text = "\n".join([f"- {e}" for e in activated_entries["classic"]])
                        content = f"[WORLD LORE & KNOWLEDGE]\n{lore_text}"
                case "Author's notes":
                    if author_notes.strip():
                        content = f"[AUTHOR NOTES]\n{author_notes}"
            
            if content:
                for key, value in replacements.items():
                    content = content.replace(key, str(value))
                
                system_blocks.append({"role": "system", "content": content})
                current_token_count += self.count_tokens(content)

        if state_prompt_block:
            for key, value in replacements.items():
                state_prompt_block = state_prompt_block.replace(key, str(value))
            
            system_blocks.append({"role": "system", "content": state_prompt_block})
            current_token_count += self.count_tokens(state_prompt_block)

        final_user_message = user_message
        if activated_entries["scenario"]:
            scenario_text = "\n".join([f"EVENT: {e}" for e in activated_entries["scenario"]])
            scenario_injection = (
                f"\n\n[SYSTEM DIRECTIVE / NARRATION]\n"
                f"The following event occurs immediately right now:\n"
                f"{scenario_text}\n"
                f"(You must react to this event in your response)"
            )
            for key, value in replacements.items():
                scenario_injection = scenario_injection.replace(key, str(value))
            final_user_message += scenario_injection

        # Soul Memory Processing
        if self.is_soul_memory_enabled():
            try:
                from app.utils.soul_memory import SoulMemoryAgent
                agent = SoulMemoryAgent(None)
                _, index_path, usr_path, topics_dir, *_ = agent.get_memory_paths(character_name, current_chat_id)
                
                memory_index = agent.get_memory_index(character_name, current_chat_id)
                user_profile = agent.get_user_profile(character_name, current_chat_id)
                explicit_topics = []
                
                soul_memory_content = ""
                if memory_index:
                    soul_memory_content += f"[CHARACTER PSYCHOLOGY & COGNITIVE CACHE]\n{memory_index}\n"
                    explicit_topics = [t.lower().strip() for t in re.findall(r'\[TOPIC FILE:\s*(.*?\.md)\]', memory_index)]

                if user_profile:
                    if soul_memory_content:
                        soul_memory_content += "\n\n"
                    soul_memory_content += f"[USER PROFILE & RELATIONSHIP HISTORIC METADATA]\n{user_profile}\n"

                if topics_dir and topics_dir.exists():
                    query_context = " ".join([str(msg.get("content", "")) for msg in chat_messages[-4:]] + [final_user_message])

                    model = get_embedder()
                    if model is None:
                        logger.info("[Soul Memory] Embedder unavailable — skipping semantic topic search.")
                    topic_files = list(topics_dir.glob("*.md")) if model else []

                    found_topics = []

                    if model and topic_files:
                        safe_query_context = str(query_context)[:1000]
                        query_vec = model.encode([f"query: {safe_query_context}"])[0]
                        topic_vectors = []
                        topic_contents = []
                        
                        for topic_file in topic_files:
                            t_name = topic_file.name.lower()
                            full_text = topic_file.read_text(encoding="utf-8")
                            
                            if t_name in explicit_topics:
                                if t_name.startswith("diary_"):
                                    display_content = "... " + full_text[-2500:] if len(full_text) > 2500 else full_text
                                    found_topics.append(f"--- [DIARY ENTRY: {topic_file.stem}] ---\n{display_content}")
                                else:
                                    found_topics.append(f"--- [DEEP MEMORY: {topic_file.stem}] ---\n{full_text}")
                                continue
                            
                            if t_name.startswith("diary_"):
                                content_preview = full_text[-600:]
                                encoding_target = f"Diary: {topic_file.stem}. Recent thoughts: {content_preview}"
                            else:
                                content_preview = full_text[:200]
                                encoding_target = f"Topic: {topic_file.stem}. Content: {content_preview}"
                            
                            target_hash = f"topic_{character_name}_{t_name}"
                            if target_hash in self.embedding_cache:
                                t_vec = self.embedding_cache[target_hash]
                            else:
                                t_vec = model.encode([f"passage: {encoding_target}"])[0]
                                self.embedding_cache[target_hash] = t_vec
                            
                            topic_vectors.append(t_vec)
                            topic_contents.append((topic_file.stem, full_text))

                        if topic_vectors:
                            similarities = cosine_similarity([query_vec], topic_vectors)[0]
                            top_indices = np.argsort(similarities)[::-1]
                            
                            for idx in top_indices:
                                if similarities[idx] > 0.42:
                                    t_name, t_full_content = topic_contents[idx]
                                    if not any(t_name in ft for ft in found_topics):
                                        if t_name.lower().startswith("diary_"):
                                            display_content = "... " + t_full_content[-2500:] if len(t_full_content) > 2500 else t_full_content
                                            found_topics.append(f"--- [DIARY ENTRY: {t_name}] ---\n{display_content}")
                                        else:
                                            found_topics.append(f"--- [DEEP MEMORY: {t_name}] ---\n{t_full_content}")
                                
                                if len(found_topics) >= 3:
                                    break

                    if found_topics:
                        if soul_memory_content:
                            soul_memory_content += "\n\n"
                        soul_memory_content += "[RELEVANT DEEP MEMORY TOPICS]\n" + "\n\n".join(found_topics)
                
                if soul_memory_content:
                    system_blocks.append({"role": "system", "content": soul_memory_content})
                    current_token_count += self.count_tokens(soul_memory_content)
                    
            except Exception as e:
                logger.error(f"[Soul Memory] Semantic Search Error: {e}", exc_info=True)

        if system_blocks:
            merged_system_content = "\n\n".join(
                b["content"] for b in system_blocks if b.get("content")
            )
            system_blocks = [{"role": "system", "content": merged_system_content}]

        user_msg_tokens = self.count_tokens(final_user_message)
        if image_attachments:
            user_msg_tokens += len(image_attachments) * self.IMAGE_TOKEN_ESTIMATE
        current_token_count += user_msg_tokens

        final_user_content = self._build_final_user_content(final_user_message, image_attachments, provider_style)

        if max_context_tokens <= 0:
            logger.info("Unlimited context detected. Bypassing history truncation.")
            raw_history = []
            for msg in chat_messages:
                msg_content = msg.get("content", "")
                if msg_content.strip():
                    raw_history.append(msg.copy())

            final_history = self._merge_consecutive_roles(raw_history)

            if final_history and final_history[0]["role"] == "assistant":
                final_history.insert(0, {"role": "user", "content": "..."})
            if final_history and final_history[-1]["role"] == "user":
                final_history.append({"role": "assistant", "content": "..."})

            final_messages = system_blocks + final_history + [{"role": "user", "content": final_user_content}]
            self.log_prompt_structure(final_messages)
            return final_messages, activated_entries

        available_tokens = max_context_tokens - current_token_count - self.response_reserve
        
        if available_tokens <= 128:
            logger.warning("Context full! Drastic compression triggered: sending only system blocks + last message.")
            final_messages = system_blocks + [{"role": "user", "content": final_user_content}]
            self.log_prompt_structure(final_messages)
            return final_messages, activated_entries
        
        # Short-Term Memory filtering
        reversed_history = []
        history_tokens_used = 0

        for msg in reversed(chat_messages):
            msg_content = msg.get("content", "")
            if not msg_content.strip(): 
                continue
            
            msg_tokens = self.count_tokens(msg_content)
            if history_tokens_used + msg_tokens > available_tokens:
                break

            reversed_history.append(msg)
            history_tokens_used += msg_tokens

        short_term_memory = list(reversed(reversed_history))
        final_history = self._merge_consecutive_roles(short_term_memory)

        cleaned_history = []
        for msg in final_history:
            if msg.get("role") == "system":
                cleaned_history.append({"role": "user", "content": f"[SYSTEM DIRECTIVE]: {msg.get('content', '')}"})
            else:
                cleaned_history.append(msg)
        final_history = cleaned_history

        if final_history and final_history[0]["role"] == "assistant":
            final_history.insert(0, {"role": "user", "content": "..."})

        if final_history and final_history[-1]["role"] == "user":
            final_history.append({"role": "assistant", "content": "..."})

        final_messages = system_blocks + final_history + [{"role": "user", "content": final_user_content}]
        self.log_prompt_structure(final_messages)

        return final_messages, activated_entries

    def _build_final_user_content(self, text, image_attachments, provider_style="openai"):
        if not image_attachments:
            return text

        if provider_style == "anthropic":
            blocks = [{"type": "text", "text": text}]
            for img in image_attachments:
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img.get("mime", "image/png"),
                        "data": img.get("b64", ""),
                    },
                })
            return blocks

        blocks = [{"type": "text", "text": text}]
        for img in image_attachments:
            mime = img.get("mime", "image/png")
            b64 = img.get("b64", "")
            blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })
        return blocks

    def build_summary_prompt_blocks(self, current_summary, new_messages, character_name, user_name):
        system_instruction = self.configuration_settings.get_main_setting("prompt_summary")
        if not system_instruction:
            system_instruction = ("""
                You are an expert narrative archivist. Your task is to update the ongoing story summary by seamlessly merging the previous summary with the new recent messages. 

                CRITICAL RULES:
                1. DO NOT write the story any further or generate new dialogue. Summarize ONLY what has already happened.
                2. DO NOT drop overarching plot points, long-term goals, or previously established vital facts. Retain the core history while adding new developments.
                3. STRICT LENGTH LIMIT: Keep the entire output under 500 words. 
                4. COMPRESSION: Aggressively condense older events into single, short sentences. Only expand on the events that happened in the most recent messages.
                5. NO REPETITION: Do not repeat facts, phrases, or sentences. Once a detail (like clothing or an action) is mentioned in one section, do not repeat it in another.
                6. You MUST strictly follow this exact format and use these exact tags:

                [CHARACTER STATES & INVENTORY]
                Detailed physical and mental state of all present characters. List active injuries, current clothing/armor, and exact inventory/items. Include their immediate short-term motives and long-term overarching goals. Do not use past tense.

                [RELATIONSHIP DYNAMICS]
                How the relationship between the characters is currently evolving. Explicitly mention current trust levels, power balance (who is leading/following), unspoken tensions, promises made to each other, and hidden secrets they are keeping from one another.

                [CURRENT SCENE & ATMOSPHERE]
                Exact current location and spatial positioning of the characters. Include rich sensory details (weather, lighting, time of day, atmosphere, smells). Clearly state any immediate dangers, time limits, or unresolved hooks in the room/area.

                [KEY DISCOVERIES & LORE]
                Any new vital information learned about the world, NPCs, magic, technology, or the main plot. If a character revealed a backstory or a secret, document it here. If nothing new was discovered recently, keep the established lore from the previous summary.

                [CHRONOLOGICAL EVENTS]
                A dense, chronological bullet-point list of the most critical actions and plot beats. 
                - Discard only purely filler dialogue (e.g., greetings). 
                - MUST retain the essence of dialogues that reveal character motives, plot progression, or major decisions. 
                - Focus heavily on cause and effect (e.g., "Character A did X, which caused Character B to feel Y").
            """)

        conversation_text = ""
        for msg in new_messages:
            role_display = user_name if msg.get("role") == "user" else character_name
            content = msg.get("content", "").strip()
            if content:
                conversation_text += f"{role_display}: {content}\n"

        summary_injection = current_summary if current_summary.strip() else "None. This is the beginning of the story."

        user_content = (
            f"<past_summary>\n{summary_injection}\n</past_summary>\n\n"
            f"<new_messages>\n{conversation_text}\n</new_messages>\n\n"
            f"Task: Generate the updated summary based on the new messages above. "
            f"Do not write dialogue. Do not repeat the prompt. Start your response directly with the [CHARACTER STATES & INVENTORY] tag."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_content}
        ]

        self.log_prompt_structure(messages)
        return messages

    def _get_soul_memory_max_tokens(self) -> int:
        configured = self.configuration_settings.get_main_setting("max_tokens")
        try:
            configured = int(configured) if configured is not None else 0
        except (TypeError, ValueError):
            configured = 0
        return max(configured, self.SOUL_MEMORY_MIN_MAX_TOKENS)

    async def _memory_llm_call(self, provider, messages: list[dict]) -> str:
        try:
            full_response = ""
            max_tokens = self._get_soul_memory_max_tokens()
            reasoning_effort = self.configuration_settings.get_main_setting("soul_memory_reasoning_effort") or "none"
            async for chunk in provider.generate_stream(
                messages, temperature=0.1, top_p=0.95, max_tokens=max_tokens,
                reasoning_effort=reasoning_effort, reasoning_mode=False
            ):
                full_response += chunk
            return full_response.strip()
        except asyncio.CancelledError:
            logger.info("Memory Agent task was cancelled gracefully.")
            raise
        except Exception as e:
            logger.error(f"Soul Memory Agent LLM call error: {e}", exc_info=True)
            return ""

    async def update_memory_after_response(self, provider, new_messages: list, character_name: str, user_name: str, activated_lorebook: dict = None, force: bool = False):
        if not self.is_soul_memory_enabled():
            return
            
        from app.utils.soul_memory import SoulMemoryAgent

        agent = SoulMemoryAgent(lambda msgs: self._memory_llm_call(provider, msgs))
        await agent.update_memory_after_response(new_messages, character_name, user_name, activated_lorebook, force)
