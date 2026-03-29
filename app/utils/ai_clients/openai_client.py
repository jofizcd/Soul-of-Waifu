import json
import yaml
import httpx
import logging
import requests
import numpy as np
import tiktoken
import os
import gc

from pathlib import Path
from openai import AsyncOpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from app.configuration import configuration

logger = logging.getLogger("Open AI Client")

tiktoken_dir = Path(__file__).parent.parent.parent.parent / "app" / "utils" / "ai_clients"
assert (tiktoken_dir / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4").exists(), "File not found!"
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

class OpenAI:
    def __init__(self, ui=None):
        self.ui = ui

        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.lorebook_state = {}
        self.embedding_cache = {}
        self.max_context_tokens = 16384
        self.response_reserve = 500
    
    def load_translation(self, language):
        """
        Loads translation strings from a YAML file based on the language code.
        """
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

    def load_openrouter_models(self):
        url = "https://openrouter.ai/api/v1/models"
        try:
            response = requests.get(url, timeout=4)

            if response.status_code == 200:
                data = response.json()
                return [{"id": model["id"], "name": model["name"], "description": model["description"]} for model in data["data"]]
            else:
                logger.error(f"Error: Received status code {response.status_code} while fetching model data.")
                return []
        except requests.exceptions.Timeout:
            logger.error("Error: The request timed out. Please check your internet connection or try again later.")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Error: A network error occurred - {e}")
            return []
    
    def build_system_prompt(self, character_name, user_name, user_description, chat_messages, user_message):
        """
        Builds a system prompt based on the order from the preset, 
        with substitution of person data, lorebook, and author's notes.
        """
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})
        smart_memory = self.configuration_settings.get_main_setting("smart_memory")

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        current_chat_id = character_information.get("current_chat", "default")
        all_chats = character_information.get("chats", {})
        current_chat_data = all_chats.get(current_chat_id, {})
        
        current_summary = current_chat_data.get("summary_text", "")
        summary_template = "[Story Summary: {{summary}}]"

        selected_persona = character_information.get("selected_persona", "None")
        selected_preset = character_information.get("selected_system_prompt_preset", "By default")
        selected_lorebook = character_information.get("selected_lorebook", "None")

        personas = user_data.get("personas", {})
        presets = user_data.get("presets", {})
        lorebooks = user_data.get("lorebooks", {})
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
            order = [
                "System prompt",
                "Character's information",
                "Lorebook",
                "Story Summary",
                "Persona information",
                "Author's notes"
            ]
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

        activated_entries = {"classic": [], "scenario": []}
        if selected_lorebook != "None" and selected_lorebook in lorebooks:
            activated_entries = self.get_activated_lorebook_entries(
                selected_lorebook, chat_messages, character_name, user_name, user_message
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
                        if "{{summary}}" in summary_template:
                            content = summary_template.replace("{{summary}}", current_summary)
                        else:
                            content = f"[Story Summary]\n{current_summary}"

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
                current_token_count += self._count_tokens(content)

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
        
        user_msg_tokens = self._count_tokens(final_user_message)
        current_token_count += user_msg_tokens

        available_tokens = self.max_context_tokens - current_token_count - self.response_reserve

        final_messages = []

        if available_tokens <= 0:
            logger.warning("Context full! Only system prompt sent.")
            return system_blocks + [{"role": "user", "content": user_message}]
        
        # --- Short-Term Memory ---
        reversed_history = []
        history_tokens_used = 0
        
        rag_budget = int(available_tokens * 0.2) if smart_memory else 0
        linear_budget = available_tokens - rag_budget

        messages_processed_count = 0 

        for msg in reversed(chat_messages):
            msg_content = msg["content"]
            msg_tokens = self._count_tokens(msg_content)
            
            if history_tokens_used + msg_tokens > linear_budget:
                break
            
            reversed_history.append(msg)
            history_tokens_used += msg_tokens
            messages_processed_count += 1

        short_term_memory = list(reversed(reversed_history))
        
        # --- Smart Memory (RAG / Long-Term) ---
        long_term_memory = []
        
        if smart_memory and rag_budget > 100 and len(chat_messages) > messages_processed_count:
            try:
                older_messages = chat_messages[:-messages_processed_count]
                
                model = EmbeddingCache.get_model()
                
                vectors_to_search = []
                contents_map = []

                for msg in older_messages:
                    content = msg["content"].strip()
                    if len(content) < 10: continue
                    
                    msg_hash = self._get_message_hash(msg)
                    
                    if msg_hash in self.embedding_cache:
                        vector = self.embedding_cache[msg_hash]
                    else:
                        vector = model.encode([content])[0]
                        self.embedding_cache[msg_hash] = vector
                    
                    vectors_to_search.append(vector)
                    role_display = "User" if msg["role"] == "user" else "Char"
                    contents_map.append(f"{role_display}: {content}")

                if vectors_to_search:
                    last_bot_reply = ""
                    if chat_messages and chat_messages[-1]["role"] == "assistant":
                         last_bot_reply = chat_messages[-1]["content"]
                    
                    query_text = f"{last_bot_reply}\n{user_message}"
                    query_vec = model.encode([query_text])[0]

                    similarities = cosine_similarity([query_vec], vectors_to_search)[0]
                    top_k_indices = np.argsort(similarities)[-3:][::-1]

                    rag_tokens_current = 0
                    found_fragments = []

                    for idx in top_k_indices:
                        if similarities[idx] < 0.35: 
                            continue
                            
                        fragment = contents_map[idx]
                        frag_tokens = self._count_tokens(fragment)
                        
                        if rag_tokens_current + frag_tokens > rag_budget:
                            break
                            
                        found_fragments.append(fragment)
                        rag_tokens_current += frag_tokens

                    if found_fragments:
                        memory_block = "[RECALLED MEMORIES]\n" + "\n---\n".join(found_fragments)
                        long_term_memory.append({"role": "system", "content": memory_block})

            except Exception as e:
                logger.error(f"Smart Memory Error: {e}")
        
        final_messages = system_blocks + long_term_memory + short_term_memory + [{"role": "user", "content": final_user_message}]

        for msg in final_messages:
            for key, value in replacements.items():
                if key in msg["content"]:
                    msg["content"] = msg["content"].replace(key, str(value))
        
        return final_messages

    def _count_tokens(self, text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(text))
        
        return num_tokens

    def _get_message_hash(self, message):
        return hash(f"{message['role']}:{message['content']}")
    
    def get_activated_lorebook_entries(self, lorebook_name, chat_messages, character_name, user_name, user_message):
        """
        Retrieves a list of activated entries from the specified lorebook:
        - Keywords & Exclude Keywords
        - Message Count Ranges (Scenario)
        - Timed Effects: Duration, Cooldown, Delay
        - Probability
        """
        config = self.configuration_settings.load_configuration()
        lorebooks = config.get("user_data", {}).get("lorebooks", {})

        if lorebook_name not in lorebooks:
            return []

        lorebook = lorebooks[lorebook_name]
        entries = lorebook.get("entries", [])
        
        global_scan_depth = lorebook.get("n_depth", 3)

        total_messages_count = len(chat_messages) + 1 
        
        if not hasattr(self, "lorebook_state"):
            self.lorebook_state = {}
        
        if lorebook_name not in self.lorebook_state:
            self.lorebook_state[lorebook_name] = {}
            
        book_state = self.lorebook_state[lorebook_name]

        activated_entries = {
            "classic": [],
            "scenario": []
        }

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
            is_triggered = False
            effective_type = trigger_type

            if trigger_type == "range":
                min_msg = entry.get("min_msg", 0)
                max_msg = entry.get("max_msg", 0)
                
                if max_msg > 0:
                    if min_msg <= total_messages_count <= max_msg:
                        is_triggered = True
                else:
                    if total_messages_count >= min_msg:
                        is_triggered = True
            else:
                if total_messages_count <= entry_state["sticky_until"]:
                    is_triggered = True
                    effective_type = entry_state.get("original_type", "keyword")
                else:
                    local_depth = entry.get("depth", global_scan_depth)
                    
                    if local_depth == 0:
                        relevant_text = ""
                    else:
                        msgs_slice = chat_messages[-local_depth:]
                        relevant_text = " ".join([str(msg.get("content", "")) for msg in msgs_slice])

                    full_text_to_scan = (relevant_text + " " + user_message).lower()

                    keys = entry.get("key", [])
                    has_key = any(key.lower() in full_text_to_scan for key in keys)
                    
                    exclude_keys = entry.get("exclude_key", [])
                    has_exclude = any(ex_key.lower() in full_text_to_scan for ex_key in exclude_keys)
                    
                    if has_key and not has_exclude:
                        is_triggered = True

            if is_triggered:
                sticky_duration = entry.get("sticky", 0)
                
                new_state = {
                    "last_active": total_messages_count,
                    "sticky_until": total_messages_count + sticky_duration if sticky_duration > 0 else -1,
                    "original_type": trigger_type
                }
                book_state[entry_uid] = new_state
                
                content = entry.get("content", "")
                if content:
                    processed_content = (content
                                         .replace("{{char}}", character_name)
                                         .replace("{{user}}", user_name)
                                         .replace("{{Char}}", character_name)
                                         .replace("{{User}}", user_name))
                    
                    if effective_type == "range":
                        activated_entries["scenario"].append(processed_content)
                    else:
                        activated_entries["classic"].append(processed_content)

        self.lorebook_state[lorebook_name] = book_state
        
        return activated_entries
    
    def format_messages_openrouter(self, character_name, user_name, user_description, chat_messages, user_message):
        """
        Advanced Prompt Builder for OpenRouter (Single-Message Format)
        """
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})
        smart_memory = self.configuration_settings.get_main_setting("smart_memory")

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        current_chat_id = character_information.get("current_chat", "default")
        all_chats = character_information.get("chats", {})
        current_chat_data = all_chats.get(current_chat_id, {})
        
        current_summary = current_chat_data.get("summary_text", "")
        summary_template = "[Story Summary: {{summary}}]"

        selected_persona = character_information.get("selected_persona", "None")
        selected_preset = character_information.get("selected_system_prompt_preset", "By default")
        selected_lorebook = character_information.get("selected_lorebook", "None")

        personas = user_data.get("personas", {})
        presets = user_data.get("presets", {})
        lorebooks = user_data.get("lorebooks", {})
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
            order = [
                "System prompt",
                "Character's information",
                "Lorebook",
                "Story Summary",
                "Persona information",
                "Author's notes"
            ]
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

        activated_entries = {"classic": [], "scenario": []}
        if selected_lorebook != "None" and selected_lorebook in lorebooks:
            activated_entries = self.get_activated_lorebook_entries(
                selected_lorebook, chat_messages, character_name, user_name, user_message
            )

        full_content_parts = []
        
        for section in order:
            block_text = ""
            match section:
                case "System prompt":
                    block_text = f"[SYSTEM INSTRUCTIONS]\n{system_prompt_template}"
                
                case "Character's information":
                    char_info = character_information.get("character_information", "")
                    if char_info:
                        block_text = f"[CHARACTER PROFILE]\n{char_info}"
                
                case "Story Summary":
                    if current_summary and len(current_summary) > 5:
                        if "{{summary}}" in summary_template:
                            block_text = summary_template.replace("{{summary}}", current_summary)
                        else:
                            block_text = f"[Story Summary]\n{current_summary}"
                
                case "Persona information":
                    if selected_persona != "None" and selected_persona in personas:
                        p = personas[selected_persona]
                        block_text = f"[USER PROFILE]\nName: {p['user_name']}\nDescription: {p['user_description']}"
                
                case "Lorebook":
                    if activated_entries["classic"]:
                        lore_text = "\n".join([f"- {e}" for e in activated_entries["classic"]])
                        block_text = f"[WORLD LORE & KNOWLEDGE]\n{lore_text}"
                
                case "Author's notes":
                    if author_notes.strip():
                        block_text = f"[AUTHOR NOTES]\n{author_notes}"

            if block_text:
                for k, v in replacements.items():
                    block_text = block_text.replace(k, str(v))
                full_content_parts.append(block_text)

        final_user_message = user_message
        
        if activated_entries["scenario"]:
            scenario_text = "\n".join([f"EVENT: {e}" for e in activated_entries["scenario"]])
            
            scenario_injection = (
                f"\n\n[SYSTEM DIRECTIVE / NARRATION]\n"
                f"The following event occurs immediately right now:\n"
                f"{scenario_text}\n"
                f"(You must react to this event in your response)"
            )
            for k, v in replacements.items():
                scenario_injection = scenario_injection.replace(k, str(v))
            
            final_user_message += scenario_injection

        static_text = "\n\n".join(full_content_parts)
        static_tokens = self._count_tokens(static_text)
        user_msg_tokens = self._count_tokens(final_user_message)
        
        setting_limit = self.configuration_settings.get_main_setting("context_size")
        
        if setting_limit is None:
            setting_limit = 8192
            
        if setting_limit < 4096:
            max_total = 16384
        else:
            max_total = setting_limit

        reserve = 600
        available_for_history = max_total - static_tokens - user_msg_tokens - reserve

        short_term_list = []
        long_term_text = ""
        
        rag_budget = int(available_for_history * 0.2) if smart_memory else 0
        linear_budget = available_for_history - rag_budget

        history_tokens = 0
        used_indices = set()
        
        for i in range(len(chat_messages)-1, -1, -1):
            msg = chat_messages[i]
            msg_str = f"{msg['role'].capitalize()}: {msg['content']}\n"
            t = self._count_tokens(msg_str)
            
            if history_tokens + t > linear_budget:
                break
            
            short_term_list.insert(0, msg_str)
            history_tokens += t
            used_indices.add(i)

        if smart_memory and rag_budget > 100:
            try:
                older_msgs = [chat_messages[i] for i in range(len(chat_messages)) if i not in used_indices]
                if older_msgs:
                    model = EmbeddingCache.get_model()
                    
                    vectors = []
                    mapping = []
                    for m in older_msgs:
                        m_hash = self._get_message_hash(m)
                        if m_hash in self.embedding_cache:
                            v = self.embedding_cache[m_hash]
                        else:
                            v = model.encode([m['content']])[0]
                            self.embedding_cache[m_hash] = v
                        vectors.append(v)
                        mapping.append(f"{m['role'].upper()}: {m['content']}")
                    
                    last_bot = chat_messages[-1]['content'] if chat_messages else ""
                    query_vec = model.encode([f"{last_bot}\n{user_message}"])[0]
                    
                    sims = cosine_similarity([query_vec], vectors)[0]
                    top_idx = np.argsort(sims)[-3:][::-1]
                    
                    mem_parts = []
                    curr_rag_t = 0
                    for idx in top_idx:
                        if sims[idx] < 0.35: continue
                        frag = mapping[idx]
                        ft = self._count_tokens(frag)
                        if curr_rag_t + ft > rag_budget: break
                        mem_parts.append(frag)
                        curr_rag_t += ft
                    
                    if mem_parts:
                        long_term_text = "[RECALLED MEMORIES]\n" + "\n---\n".join(mem_parts)
            except Exception as e:
                logger.error(f"OpenRouter Smart Memory Error: {e}")

        final_string = static_text + "\n\n"
        
        if long_term_text:
            final_string += long_term_text + "\n\n"
            
        if short_term_list:
            final_string += "[CHAT HISTORY]\n" + "".join(short_term_list) + "\n"

        final_string += f"User: {final_user_message}\nAssistant:"

        for k, v in replacements.items():
            final_string = final_string.replace(k, str(v))

        return [{"role": "user", "content": final_string}]
    
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

    async def send_message(self, conversation_method, context_messages, user_message, character_name, user_name, user_description):
        base_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
        open_ai_api = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
        model = self.configuration_settings.get_main_setting("openai_model")
        openrouter_model = self.configuration_settings.get_main_setting("openrouter_model")

        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")

        if conversation_method == "Open AI":
            base_url = base_url.rstrip('/')
            base_url = base_url if base_url.endswith('/v1') else f"{base_url}/v1"
            
            if base_url:
                base_url = base_url.rstrip('/')
                base_url = base_url if base_url.endswith('/v1') else f"{base_url}/v1"
            else:
                base_url = "https://api.openai.com/v1"

            api_token = open_ai_api if open_ai_api else "no-key-required"
           
            if not model:
                model = "gpt-5-mini-2025-08-07" 

            client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_token
            )

            final_system_prompt = self.build_system_prompt(
                character_name=character_name,
                user_name=user_name,
                user_description=user_description,
                chat_messages=context_messages,
                user_message=user_message
            )
            
            messages = final_system_prompt

            self.log_prompt_structure(messages)

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=repeat_penalty,
                presence_penalty=0.7,
                stop=["<|im_end|>"]
            )

            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        elif conversation_method == "OpenRouter":
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            model = openrouter_model

            messages = self.format_messages_openrouter(
                character_name=character_name,
                user_name=user_name,
                user_description=user_description,
                chat_messages=context_messages,
                user_message=user_message
            )

            self.log_prompt_structure(messages)

            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_token if api_token else "no-key-required",
                http_client=httpx.AsyncClient(timeout=None)
            )

            try:
                completion = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    frequency_penalty=repeat_penalty,
                    presence_penalty=0.7,
                    stop=["<|im_end|>"],
                    extra_headers={
                        "HTTP-Referer": "https://github.com/jofizcd/Soul-of-Waifu",
                        "X-Title": "Soul of Waifu"
                    }
                )

                async for chunk in completion:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            except Exception as e:
                logger.error(f"OpenRouter Request error: {e}")
                yield f"\n⚠️ OpenRouter API Error: {str(e)}"
            finally:
                await client.close()

    async def generate_summary(self, conversation_method, current_summary, new_messages, character_name, user_name):
        """
        Generates a summary update based on the previous summary and new chat messages.
        
        Args:
            current_summary (str): The existing summary text (can be empty).
            new_messages (list): List of dicts [{'role': 'user', 'content': '...'}, ...].
            character_name (str): Name of the character for formatting.
            user_name (str): Name of the user for formatting.

        Yields:
            str: Chunks of the generated summary.
        """
        if conversation_method == "Open AI":
            open_ai_api = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
            model = self.configuration_settings.get_main_setting("openai_model")

            if base_url:
                base_url = base_url.rstrip('/')
                base_url = base_url if base_url.endswith('/v1') else f"{base_url}/v1"
            else:
                base_url = "https://api.openai.com/v1"
            
            api_token = open_ai_api if open_ai_api else "no-key-required"
            if not model:
                model = "gpt-5-mini-2025-08-07"

        elif conversation_method == "OpenRouter":
            base_url = "https://openrouter.ai/api/v1"
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            model = self.configuration_settings.get_main_setting("openrouter_model")

        try:
            client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_token
            )
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client for summary: {e}")
            yield ""
            return

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
            if not content: continue
            conversation_text += f"{role_display}: {content}\n"

        summary_injection = current_summary if current_summary.strip() else "None. This is the beginning of the story."

        user_content = (
            f"<past_summary>\n{summary_injection}\n</past_summary>\n\n"
            f"<new_messages>\n{conversation_text}\n</new_messages>\n\n"
            f"Task: Generate the updated summary based on the new messages above. "
            f"Do not write dialogue. Do not repeat the prompt. Start your response directly with the [CHARACTER STATES & INVENTORY] tag."
        )

        if conversation_method == "Open AI":
            messages_payload = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ]
        else:
            messages_payload = {"role": "user", "content": system_instruction + user_content}

        self.log_prompt_structure(messages_payload)

        self.ui.loading_model_label.show()
        self.ui.loading_model_label.setText(self.translations.get("model_generate_summary", "Generating summary..."))

        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=messages_payload,
                stream=True,
                max_tokens=1000,
                temperature=0.5,
                top_p=0.9,
                frequency_penalty=0.5,
                presence_penalty=0.0,
                stop=["<|im_end|>"]
            )

            async for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Summarization request error ({conversation_method}): {e}")
            yield ""
        finally:
            self.ui.loading_model_label.hide()
            await client.close()
