import logging
import numpy as np
import tiktoken
import os
import gc
import yaml

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from pathlib import Path
from mistralai import Mistral
from app.configuration import configuration

logger = logging.getLogger("Mistral AI Client")

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

class MistralAI():
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

        user_msg_tokens = self._count_tokens(user_message)
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

    async def send_message(self, context_messages, user_text, character_name, user_name, user_description):
        """
        Sends a message to the Mistral server and streams the response back in real-time.
        
        This method prepares the full prompt with context,
        sends the request and yields the result as it arrives.

        Args:
            context_messages (list): List of previous conversation messages.
            user_text (str): Current input from the user.
            character_name (str): Name of the AI character.
            user_name (str): Name of the user.
            user_description (str): Description of the user for context.

        Yields:
            str: Chunks of generated text as they are received from the server.
        """
        self.mistral_ai_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
        self.model = self.configuration_settings.get_main_setting("mistral_model_endpoint")
        self.client = Mistral(api_key=self.mistral_ai_token)

        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        temperature = self.configuration_settings.get_main_setting("temperature")
        top_p = self.configuration_settings.get_main_setting("top_p")
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")

        final_system_prompt = self.build_system_prompt(
            character_name=character_name,
            user_name=user_name,
            user_description=user_description,
            chat_messages=context_messages,
            user_message=user_text
        )

        messages = final_system_prompt

        self.log_prompt_structure(messages)

        response = await self.client.chat.stream_async(
            model=self.model,
            messages=messages,
            safe_prompt=False,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            frequency_penalty=repeat_penalty,
            presence_penalty=0.7
        )

        async for chunk in response:
            if chunk.data and chunk.data.choices and chunk.data.choices[0].delta:
                message = chunk.data.choices[0].delta.content
                if message:
                    yield message
    
    async def generate_summary(self, current_summary, new_messages, character_name, user_name):
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
        self.mistral_ai_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
        self.model = self.configuration_settings.get_main_setting("mistral_model_endpoint")
        
        if not self.mistral_ai_token:
            logger.error("Mistral AI Token is missing.")
            yield ""
            return

        self.client = Mistral(api_key=self.mistral_ai_token)

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
            
            if not content:
                continue
                
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

        self.ui.loading_model_label.show()
        self.ui.loading_model_label.setText(self.translations.get("model_generate_summary", "Generating summary..."))

        try:
            response = await self.client.chat.stream_async(
                model=self.model,
                messages=messages,
                safe_prompt=False,
                temperature=0.5,
                top_p=0.9,
                max_tokens=1000,
                frequency_penalty=0.8,
                presence_penalty=0.3
            )

            async for chunk in response:
                if chunk.data and chunk.data.choices and chunk.data.choices[0].delta:
                    content = chunk.data.choices[0].delta.content
                    if content:
                        yield content
        except Exception as e:
            logger.error(f"Mistral Summarization request error: {e}")
            yield ""
        finally:
            self.ui.loading_model_label.hide()
