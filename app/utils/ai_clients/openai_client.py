import json
import logging
import requests
import numpy as np

from openai import AsyncOpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from app.configuration import configuration

logger = logging.getLogger("Open AI Client")

class OpenAI:
    def __init__(self):
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()

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
            "{{user_description}}": user_description
        }

        system_prompt_parts = []

        for section in order:
            match section:
                case "System prompt":
                    part = system_prompt_template
                    for key, value in replacements.items():
                        part = part.replace(key, value)
                    system_prompt_parts.append({
                        "role": "system",
                        "content": part
                    })

                case "Character's information":
                    char_info = character_information.get("character_information", "")
                    if char_info:
                        system_prompt_parts.append({
                            "role": "system",
                            "content": f"[CHARACTER PROFILE]\n{char_info}"
                        })

                case "Persona information":
                    if selected_persona != "None" and selected_persona in personas:
                        persona = personas[selected_persona]
                        persona_text = (
                            f"User Name: {persona['user_name']}\n"
                            f"User Description: {persona['user_description']}"
                        )
                        system_prompt_parts.append({
                            "role": "system",
                            "content": "[USER PROFILE]\n" + persona_text
                        })

                case "Lorebook":
                    if selected_lorebook != "None" and selected_lorebook in lorebooks:
                        activated_entries = self.get_activated_lorebook_entries(selected_lorebook, chat_messages)
                        if activated_entries:
                            lorebook_content = "\n\n".join([
                                f"[ENTRY №{idx}]\n{content}" 
                                for idx, content in enumerate(activated_entries, start=1)
                            ])
                            system_prompt_parts.append({
                                "role": "system",
                                "content": "[LOREBOOK]\n" + lorebook_content
                            })

                case "Author's notes":
                    if author_notes.strip():
                        system_prompt_parts.append({
                            "role": "system",
                            "content": "[AUTHOR NOTES]\n" + author_notes
                        })

        if not smart_memory:
            system_prompt_parts.extend(chat_messages)
        else:
            if len(chat_messages) < 10:
                system_prompt_parts.extend(chat_messages)
            else:
                try:
                    model = SentenceTransformer('app/utils/all-MiniLM-L6-v2')

                    MIN_SEGMENT_WORDS = 10
                    TOP_RELEVANT_FRAGMENTS = 5
                    SHORT_TERM_DEPTH = 3

                    dynamic_history_depth = max(20, min(int(len(chat_messages) * 0.3), 200))

                    if len(chat_messages) > 500:
                        dynamic_history_depth = min(dynamic_history_depth + 100, len(chat_messages))

                    segments = []
                    current_segment = []
                    
                    for msg in chat_messages[-dynamic_history_depth:]:
                        role = msg["role"]
                        content = msg["content"].strip()
                        
                        if not content:
                            continue

                        if current_segment and current_segment[-1]["role"] != role:
                            segment_text = " ".join([m["content"] for m in current_segment])
                            if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                                segments.append({
                                    "messages": current_segment.copy(),
                                    "text": segment_text
                                })
                            current_segment = []
                        
                        current_segment.append(msg)

                    if current_segment:
                        segment_text = " ".join([m["content"] for m in current_segment])
                        if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                            segments.append({
                                "messages": current_segment,
                                "text": segment_text
                            })

                    if len(segments) < 2:
                        system_prompt_parts.extend(chat_messages)
                        return system_prompt_parts
                    
                    segment_texts = [seg["text"] for seg in segments]

                    segment_embeddings = model.encode(segment_texts, convert_to_tensor=True)
                    query_embedding = model.encode([user_message], convert_to_tensor=True)

                    similarities = cosine_similarity(
                        query_embedding.cpu().numpy(),
                        segment_embeddings.cpu().numpy()
                    )[0]

                    top_indices = np.argsort(similarities)[-TOP_RELEVANT_FRAGMENTS:][::-1]

                    memory_fragments = []
                    for i, idx in enumerate(top_indices):
                        seg = segments[idx]
                        fragment = f"[MEMORY FRAGMENT #{i+1}]\n"
                        for msg in seg["messages"]:
                            role = "USER" if msg["role"] == "user" else character_name.upper()
                            fragment += f"{role}: {msg['content'].strip()}\n"
                        memory_fragments.append(fragment.strip())

                    if memory_fragments:
                        system_prompt_parts.append({
                            "role": "system",
                            "content": f"[LONG-TERM MEMORY]\n" + "\n\n".join(memory_fragments)
                        })
                    
                    system_prompt_parts.append({
                        "role": "system",
                        "content": "[SHORT-TERM MEMORY]\n"
                    })
                    system_prompt_parts.extend(chat_messages[-SHORT_TERM_DEPTH:])
                    
                except Exception as e:
                    logger.error(f"Smart memory error: {str(e)}")
                    system_prompt_parts.extend(chat_messages)

        return system_prompt_parts

    def get_activated_lorebook_entries(self, lorebook_name, chat_messages):
        """
        Retrieves a list of activated entries from the specified lorebook, 
        based on the depth of the scan and the presence of keywords in the chat.
        """
        config = self.configuration_settings.load_configuration()
        lorebooks = config.get("user_data", {}).get("lorebooks", {})

        if lorebook_name not in lorebooks:
            return []

        lorebook = lorebooks[lorebook_name]
        scan_depth = lorebook.get("n_depth", 3)
        entries = lorebook.get("entries", [])

        if scan_depth == 0:
            relevant_messages = []
        else:
            relevant_messages = chat_messages[-scan_depth:]

        context_text = " ".join([msg["content"] for msg in relevant_messages]).lower()

        activated_entries = []

        for entry in entries:
            keys = entry.get("key", [])
            for key in keys:
                if key.lower() in context_text:
                    activated_entries.append(entry["content"])
                    break

        return activated_entries
    
    def format_messages_openrouter(self, character_name, user_name, user_description, chat_messages, user_message):
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})
        smart_memory = self.configuration_settings.get_main_setting("smart_memory")

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
            "{{user_description}}": user_description
        }

        for key, value in replacements.items():
            system_prompt_template = system_prompt_template.replace(key, value)

        full_content = ""

        for section in order:
            match section:
                case "System prompt":
                    if system_prompt_template:
                        full_content += f"[SYSTEM PROMPT]\n{system_prompt_template}\n\n"

                case "Character's information":
                    char_info = character_information.get("character_description", "")
                    if char_info:
                        full_content += f"[CHARACTER PROFILE]\n{char_info}\n\n"

                case "Persona information":
                    if selected_persona != "None" and selected_persona in personas:
                        persona = personas[selected_persona]
                        persona_text = (
                            f"[USER PROFILE]\n"
                            f"User Name: {persona['user_name']}\n"
                            f"Description: {persona['user_description']}\n\n"
                        )
                        full_content += persona_text

                case "Lorebook":
                    if selected_lorebook != "None" and selected_lorebook in lorebooks:
                        activated_entries = self.get_activated_lorebook_entries(selected_lorebook, chat_messages)
                        if activated_entries:
                            full_content += "[LOREBOOK ENTRIES]\n"
                            for idx, content in enumerate(activated_entries, start=1):
                                full_content += f"{idx}. {content}\n\n"

                case "Author's notes":
                    if author_notes.strip():
                        full_content += f"[AUTHOR NOTES]\n{author_notes}\n\n"

        if not smart_memory:
            full_content += "[CHAT HISTORY]\n"
            for msg in chat_messages:
                role = msg["role"].capitalize()
                content = msg["content"].strip()
                full_content += f"{role}: {content}\n"
        else:
            if len(chat_messages) < 10:
                full_content += "[CHAT HISTORY]\n"
                for msg in chat_messages:
                    role = msg["role"].capitalize()
                    content = msg["content"].strip()
                    full_content += f"{role}: {content}\n"
            else:
                try:
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer('app/utils/all-MiniLM-L6-v2')

                    MIN_SEGMENT_WORDS = 10
                    MAX_HISTORY_ANALYZE = 50
                    TOP_RELEVANT_FRAGMENTS = 4
                    SHORT_TERM_DEPTH = 3

                    segments = []
                    current_segment = []

                    for msg in chat_messages[-MAX_HISTORY_ANALYZE:]:
                        role = msg["role"]
                        content = msg["content"].strip()
                        if not content:
                            continue

                        if current_segment and current_segment[-1]["role"] != role:
                            segment_text = " ".join([m["content"] for m in current_segment])
                            if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                                segments.append({
                                    "messages": current_segment.copy(),
                                    "text": segment_text
                                })
                            current_segment = []

                        current_segment.append(msg)

                    if current_segment:
                        segment_text = " ".join([m["content"] for m in current_segment])
                        if len(segment_text.split()) >= MIN_SEGMENT_WORDS:
                            segments.append({
                                "messages": current_segment,
                                "text": segment_text
                            })

                    if len(segments) < 2:
                        full_content += "[CHAT HISTORY]\n"
                        for msg in chat_messages:
                            role = msg["role"].capitalize()
                            content = msg["content"].strip()
                            full_content += f"{role}: {content}\n"
                    else:
                        segment_texts = [seg["text"] for seg in segments]
                        segment_embeddings = model.encode(segment_texts, convert_to_tensor=True)
                        query_embedding = model.encode([user_message], convert_to_tensor=True)

                        from sklearn.metrics.pairwise import cosine_similarity
                        import numpy as np

                        similarities = cosine_similarity(
                            query_embedding.cpu().numpy(),
                            segment_embeddings.cpu().numpy()
                        )[0]

                        top_indices = np.argsort(similarities)[-TOP_RELEVANT_FRAGMENTS:][::-1]

                        memory_fragments = []
                        for i, idx in enumerate(top_indices):
                            seg = segments[idx]
                            fragment = f"[MEMORY FRAGMENT #{i+1}]\n"
                            for msg in seg["messages"]:
                                role = "USER" if msg["role"] == "user" else character_name.upper()
                                fragment += f"{role}: {msg['content'].strip()}\n"
                            memory_fragments.append(fragment.strip())

                        if memory_fragments:
                            full_content += f"[LONG-TERM MEMORY]\n" + "\n\n".join(memory_fragments) + "\n\n"

                        full_content += "[SHORT-TERM MEMORY]\n"
                        for msg in chat_messages[-SHORT_TERM_DEPTH:]:
                            role = msg["role"].capitalize()
                            content = msg["content"].strip()
                            full_content += f"{role}: {content}\n"

                except Exception as e:
                    logger.error(f"Smart memory error: {str(e)}")
                    full_content += "[CHAT HISTORY]\n"
                    for msg in chat_messages:
                        role = msg["role"].capitalize()
                        content = msg["content"].strip()
                        full_content += f"{role}: {content}\n"

        full_content += f"User: {user_message}\n"

        return [{"role": "user", "content": full_content}]

    async def send_message(self, conversation_method, context_messages, user_message, character_name, user_name, user_description):
        base_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
        open_ai_api = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
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
            model = "openai/gpt-4o"

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

            new_user_message = {"role": "user", "content": user_message}

            messages = final_system_prompt + [new_user_message]

            logger.info(messages)

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
            base_url = "https://openrouter.ai/api/v1/chat/completions"
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            model = openrouter_model

            messages = self.format_messages_openrouter(
                character_name=character_name,
                user_name=user_name,
                user_description=user_description,
                chat_messages=context_messages,
                user_message=user_message
            )

            logger.info(messages)

            headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "frequency_penalty": repeat_penalty,
                "presence_penalty": 0.7,
                "stop": ["<|im_end|>"]
            }

            buffer = ""
            response_content = ""
            with requests.post(base_url, headers=headers, json=payload, stream=True) as r:
                logger.info(f"Response status code: {r.status_code}")
                if r.status_code != 200:
                    logger.error(f"API returned status code {r.status_code}: {r.text}")
                    yield f"Error: API returned status code {r.status_code}"
                    return

                for chunk in r.iter_content(chunk_size=1024, decode_unicode=True):
                    buffer += chunk
                    while True:
                        try:
                            line_end = buffer.find('\n')
                            if line_end == -1:
                                break

                            line = buffer[:line_end].strip()
                            buffer = buffer[line_end + 1:]

                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break

                                try:
                                    data_obj = json.loads(data)
                                    logger.debug(f"Received data chunk: {data_obj}")
                                    content = data_obj["choices"][0]["delta"].get("content")
                                    if content:
                                        yield content
                                        response_content += content
                                except json.JSONDecodeError:
                                    pass
                        except Exception as e:
                            logger.error(f"Error processing chunk: {e}")
                            break