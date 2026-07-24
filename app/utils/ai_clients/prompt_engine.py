import os
import gc
import asyncio
import logging
import tiktoken
import numpy as np
import re

from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.configuration import configuration

logger = logging.getLogger("Prompt Engine")

tiktoken_dir = Path(__file__).parent.parent.parent / "app" / "utils" / "ai_clients"
if (tiktoken_dir / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4").exists():
    os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_dir)

class EmbeddingCache:
    _instance = None
    _model = None
    
    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = SentenceTransformer('app/utils/all-MiniLM-L6-v2')
            logger.info("Embedding model loaded to memory")
        return cls._model
    
    @classmethod
    def clear(cls):
        if cls._model:
            del cls._model
            cls._model = None
            gc.collect()
            logger.info("Embedding model unloaded")

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

        raw_size = self.configuration_settings.get_main_setting("context_size")
        self.max_context_tokens = raw_size if raw_size is not None else 8192
        self.response_reserve = 500

    def is_soul_memory_enabled(self) -> bool:
        try:
            return self.configuration_settings.get_main_setting("soul_memory")
        except Exception:
            return True

    def count_tokens(self, text: str) -> int:
        if not text or not self.encoder:
            return 0

        return len(self.encoder.encode(text, disallowed_special=()))

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
                            model = EmbeddingCache.get_model()
                        if model:
                            if not semantic_context:
                                semantic_context = full_text_to_scan
                            emb1 = model.encode([semantic_context])
                            emb2 = model.encode([semantic_trigger_text.lower()])
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
            length = len(content)
            total_chars += length

            header = f" [ BLOCK {i+1} | {role} | {length} chars ] "
            header_line = f"{header:-^80}"
            
            log_output.append(header_line)
            log_output.append(content.strip())
            log_output.append("")
            
        log_output.append(thin_separator)
        log_output.append(f" TOTAL: {len(messages)} blocks | ~{total_chars} chars")
        log_output.append(f"{separator}\n")
        
        logger.info("\n".join(log_output))

    def build_system_prompt_blocks(self, character_name, user_name, user_description, chat_messages, user_message, activated_lorebook=None):
        """
        Builds a robust system prompt list with structured blocks, memory, and lore integration.
        Returns a list of message dicts.
        """
        raw_size = self.configuration_settings.get_main_setting("context_size")
        self.max_context_tokens = raw_size if raw_size is not None else 8192

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
                state_prompt_block += (
                    "\n[SYSTEM DIRECTIVE — STATE UPDATES]\n"
                    "You are playing a game with state tracking. "
                    "You MUST ALWAYS output the <state_update>...</state_update> XML tag at the absolute end of your response, even if no variables changed (in which case, output an empty JSON: <state_update>{}</state_update>).\n"
                    f"ALLOWED JSON KEYS: [{allowed_keys_str}]\n\n"
                    "Syntax rules:\n"
                    "1. Only update variables that actually changed during this turn of dialogue. Use ONLY keys from the ALLOWED JSON KEYS list.\n"
                    "2. For numerical variables (int), output the change delta (e.g., -10 or +5).\n"
                    "3. For boolean variables (bool), output the new value (true or false).\n"
                    "4. For lists (inventory), prefix the item with '+' to add or '-' to remove (e.g., \"+Key\" or \"-Sword\").\n"
                    "5. Output the <state_update> tag at the absolute end of your response, with NO text after it.\n\n"
                    "CRITICAL EXAMPLE 1 (No changes):\n"
                    "*She nods slightly.* \"Fine, let's go.\" <state_update>{}</state_update>\n\n"
                    "CRITICAL EXAMPLE 2 (State changed):\n"
                    "*She smiles softly.* \"Thank you for the tea, Lawrence.\" <state_update>{\"ice_wall\": -10, \"trust\": +5}</state_update>\n"
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
                    
                    model = EmbeddingCache.get_model()
                    query_vec = model.encode([query_context])[0]
                    
                    found_topics = []
                    topic_files = list(topics_dir.glob("*.md"))
                    
                    if topic_files:
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
                                t_vec = model.encode([encoding_target])[0]
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

        user_msg_tokens = self.count_tokens(final_user_message)
        current_token_count += user_msg_tokens

        if self.max_context_tokens == -1:
            logger.info("Unlimited context detected. Bypassing history truncation.")
            final_history = []
            for msg in chat_messages:
                msg_content = msg.get("content", "")
                if msg_content.strip():
                    final_history.append(msg.copy())
            
            if final_history and final_history[0]["role"] == "assistant":
                final_history.insert(0, {"role": "user", "content": "..."})
            if final_history and final_history[-1]["role"] == "user":
                final_history.append({"role": "assistant", "content": "..."})
                
            return system_blocks + final_history + [{"role": "user", "content": final_user_message}], activated_entries

        available_tokens = self.max_context_tokens - current_token_count - self.response_reserve
        
        if available_tokens <= 128:
            logger.warning("Context full! Drastic compression triggered: sending only system blocks + last message.")
            return system_blocks + [{"role": "user", "content": final_user_message}], activated_entries
        
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
        
        final_history = []
        for msg in short_term_memory:
            if not final_history:
                final_history.append(msg.copy())
            else:
                if final_history[-1]["role"] == msg["role"]:
                    final_history[-1]["content"] += "\n\n" + msg["content"]
                else:
                    final_history.append(msg.copy())

        if final_history and final_history[0]["role"] == "assistant":
            final_history.insert(0, {"role": "user", "content": "..."})

        if final_history and final_history[-1]["role"] == "user":
            final_history.append({"role": "assistant", "content": "..."})

        final_messages = system_blocks + final_history + [{"role": "user", "content": final_user_message}]
        
        return final_messages, activated_entries

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

    async def _memory_llm_call(self, provider, messages: list[dict]) -> str:
        try:
            full_response = ""
            async for chunk in provider.generate_stream(messages, temperature=0.1, top_p=0.95, max_tokens=1500):
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
