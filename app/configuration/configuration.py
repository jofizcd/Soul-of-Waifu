import os
import uuid
import json
import logging
import datetime
import traceback

logger = logging.getLogger("Configuration")

class ConfigurationSettings():
    """
    A class that manages a JSON configuration file containing application settings and user data.
    """
    def __init__(self):
        self.settings_path = "app/configuration/settings.json"

    def load_configuration(self):
        """
        Loads and returns the configuration data from the JSON file.
        """
        if not os.path.exists(self.settings_path):
            
            return {
                "main_settings": {
                    "conversation_method": "0",
                    "stt_method": "0",
                    "sow_system_status": "",
                    "emotions_method": "",
                    "program_language": "0",
                    "input_device": "0",
                    "output_device": "0",
                    "translator": "0",
                    "target_language": "0"
                },
                "user_data": {
                    "default_persona": "None",
                    "personas": {},
                    "presets": {},
                    "current_character_image": "None"
                }
            }
        with open(self.settings_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration_edit(self, data):
        """
        Saves provided configuration data to the JSON file.
        """
        with open(self.settings_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def update_main_setting(self, setting, value):
        """
        Updates a specific main setting in the configuration.

        Args:
            setting (str): The key of the main setting to update.
            value (any): The new value to assign to the specified key.
        """
        configuration_data = self.load_configuration()
        
        if "main_settings" not in configuration_data:
            configuration_data["main_settings"] = {}
        
        configuration_data["main_settings"][setting] = value
        self.save_configuration_edit(configuration_data)

    def get_main_setting(self, setting):
        """
        Retrieves the value of a main setting from the configuration.

        Args:
            setting (str): The key of the main setting to retrieve.

        Returns:
            value (any): The value associated with the specified key, or None if the key is not found.
        """
        configuration_data = self.load_configuration()
        return configuration_data["main_settings"].get(setting, None)

    def update_user_data(self, key, value):
        """
        Updates a user data field in the configuration.

        Args:
            key (str): The key of the user data field to update.
            value (any): The new value to assign to the specified key.
        """
        configuration_data = self.load_configuration()
        
        if "user_data" not in configuration_data:
            configuration_data["user_data"] = {}
        
        configuration_data["user_data"][key] = value
        self.save_configuration_edit(configuration_data)

    def get_user_data(self, key):
        """
        Retrieves a user data field from the configuration.

        Args:
            key (str): The key of the user data field to retrieve.

        Returns:
            value (any): The value associated with the specified key, or None if the key is not found.
        """
        configuration_data = self.load_configuration()
        return configuration_data["user_data"].get(key, None)
    
    def update_preset(self, preset_name, preset_data):
        config = self.load_configuration()
        if "user_data" not in config:
            config["user_data"] = {}
        if "presets" not in config["user_data"]:
            config["user_data"]["presets"] = {}

        config["user_data"]["presets"][preset_name] = preset_data
        self.save_configuration_edit(config)

    def get_all_presets(self):
        return self.load_configuration().get("user_data", {}).get("presets", {})
    
    def delete_preset(self, name):
        presets = self.load_configuration().get("user_data", {}).get("presets", {})

        if name in presets:
            del presets[name]

            self.update_user_data("presets", presets)

    def update_lorebook(self, name, lorebook_data):
        """
        Adds or updates a single lorebook entry in the configuration.
        """
        config = self.load_configuration()
        if "user_data" not in config:
            config["user_data"] = {}
        if "lorebooks" not in config["user_data"]:
            config["user_data"]["lorebooks"] = {}

        config["user_data"]["lorebooks"][name] = lorebook_data
        self.save_configuration_edit(config)
    
    def delete_lorebook(self, name):
        """
        Deletes a lorebook by name from the configuration.
        """
        config = self.load_configuration()
        lorebooks = config.get("user_data", {}).get("lorebooks", {})

        if name in lorebooks:
            del lorebooks[name]
            config["user_data"]["lorebooks"] = lorebooks  # Update reference
            self.save_configuration_edit(config)

    def save_lorebooks(self, lorebooks):
        """
        Replaces all existing lorebooks with the provided dictionary of lorebooks.
        """
        config = self.load_configuration()
        if "user_data" not in config:
            config["user_data"] = {}

        config["user_data"]["lorebooks"] = lorebooks
        self.save_configuration_edit(config)
    
class ConfigurationAPI():
    """
    A class for managing API tokens stored in a JSON configuration file.
    """
    def __init__(self):
        self.api_tokens_path = "app/configuration/api.json"

    def load_configuration(self):
        """
        Loads the current API token configuration from the JSON file.
        """
        if not os.path.exists(self.api_tokens_path):
            return {}
        with open(self.api_tokens_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration_edit(self, data):
        """
        Saves provided configuration data directly to the JSON file.
        """
        with open(self.api_tokens_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    
    def save_api_token(self, variable, variable_value):
        """
        Saves or updates an API token in the configuration file.
        
        Args:
            variable (str): Variable name.
            value (any): Variable value.
        """
        configuration_data = self.load_configuration()
        
        configuration_data[variable] = variable_value
        self.save_configuration_edit(configuration_data)

    def get_token(self, api):
        """
        Retrieves the value of an API token from the configuration file.
        """
        configuration_data = self.load_configuration()
        
        return configuration_data.get(api)

class ConfigurationCharacters():
    """
    A class for managing character data stored in a JSON configuration file.
    """
    def __init__(self):
        self.characters_path = "app/configuration/characters.json"
        self.configuration_data = self.load_configuration()

    def load_configuration(self):
        """
        Loads the characters configuration data from the JSON file.
        """
        if not os.path.exists(self.characters_path):
            return {}
        with open(self.characters_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration_edit(self, data):
        """
        Saves the provided character configuration data directly to the JSON file.
        """
        with open(self.characters_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def save_character_card(self, character_name, character_title, character_avatar, character_description, character_personality, first_message, scenario, example_messages, alternate_greetings, selected_persona, selected_system_prompt_preset, selected_lorebook, elevenlabs_voice_id, voice_type, rvc_enabled, rvc_file, expression_images_folder, live2d_model_folder, vrm_model_file, conversation_method):
        """
        Saves or updates a character's card information in the configuration.
        
        Args:
            character_name (str): Character's name.
            character_title (str): Title or role of the character.
            character_avatar (str): Path to the avatar image file.
            character_description (str): Description of the character.
            character_personality (str): Personality traits and behavior style.
            first_message (str): Character's first message.
            elevenlabs_voice_id (str): Voice ID for ElevenLabs TTS.
            voice_type (str): Type of voice used for TTS.
            rvc_enabled (bool): Whether RVC is enabled.
            rvc_file (str): Path to RVC model file.
            expression_images_folder (str): Path to emotion images folder.
            live2d_model_folder (str): Path to Live2D model folder.
            conversation_method (str): Character's conversation method.
        """
        configuration_data = self.load_configuration()
        if 'character_list' not in configuration_data:
            configuration_data['character_list'] = {}

        message_id = str(uuid.uuid4())

        variants = [
            {"variant_id": "default", "text": first_message}
        ]

        for i, greeting in enumerate(alternate_greetings):
            variants.append({
                "variant_id": f"v{i+1}",
                "text": greeting.strip()
            })

        main_message = {
            "message_id": message_id,
            "sequence_number": 1,
            "author_name": character_name,
            "is_user": False,
            "current_variant_id": "default",
            "variants": variants
        }

        chat_content = {message_id: main_message}

        chat_history = []
        chat_history.append({
            "user": "",
            "character": first_message
        })
        
        character_information_parts = []

        if character_description.strip():
            character_information_parts.append(character_description.strip())

        if character_personality.strip():
            character_information_parts.append(f"{character_personality.strip()}.")

        if scenario.strip():
            character_information_parts.append(f"Here is the dialogue script: {scenario.strip()}.\n\n")

        if example_messages.strip():
            character_information_parts.append(
                f"[Example Chat]:\n{example_messages.strip()}\n\n"
                "Your response should follow the same pattern and style as above."
            )

        if character_information_parts:
            character_information_parts.append("Respond as the character, do not break role or add extra explanations.")

        character_information = " ".join(character_information_parts)

        configuration_data['character_list'][character_name] = {
            "character_avatar": character_avatar,
            "character_title": character_title,
            "character_description": character_description,
            "character_personality": character_personality,
            "first_message": first_message,
            "scenario": scenario,
            "example_messages": example_messages,
            "alternate_greetings": alternate_greetings,
            "selected_persona": selected_persona,
            "selected_system_prompt_preset": selected_system_prompt_preset,
            "selected_lorebook": selected_lorebook,
            "current_text_to_speech": "Nothing",
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "voice_type": voice_type,
            "rvc_enabled": rvc_enabled,
            "rvc_file": rvc_file,
            "current_sow_system_mode": "Nothing",
            "expression_images_folder": expression_images_folder,
            "live2d_model_folder": live2d_model_folder,
            "vrm_model_file": vrm_model_file,
            "conversation_method": conversation_method,
            "character_information": character_information,
            "current_chat": "default",
            "chats": {
                "default": {
                    "name": "default",
                    "created_at": datetime.datetime.now().isoformat(),
                    "current_emotion": "neutral",
                    "chat_history": chat_history,
                    "chat_content": chat_content
                }
            }
        }

        self.save_configuration_edit(configuration_data)
    
    def update_chat_history(self, character_name):
        """
        Updates the chat history for a specific character based on their chat content.
        """
        configuration_data = self.load_configuration()
        character_data = configuration_data['character_list'].get(character_name)

        if not character_data or "chats" not in character_data:
            return

        current_chat_id = character_data.get("current_chat", None)
        if not current_chat_id or current_chat_id not in character_data["chats"]:
            return
        
        chat_data = character_data["chats"][current_chat_id]
        chat_content = chat_data.get("chat_content", {})
        
        chat_history = []
        user_turn = {"user": "", "character": ""}

        for msg_id, msg_data in sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", 0)):
            current_variant_id = msg_data.get("current_variant_id", "default")
            current_text = next(
                (variant["text"] for variant in msg_data.get("variants", []) if variant["variant_id"] == current_variant_id),
                ""
            )

            if msg_data["is_user"]:
                if user_turn["user"] or user_turn["character"]:
                    chat_history.append(user_turn)
                    user_turn = {"user": current_text, "character": ""}
                else:
                    user_turn["user"] = current_text
            else:
                if user_turn["user"] or not user_turn["character"]:
                    user_turn["character"] = current_text
                else:
                    user_turn["character"] += "\n" + current_text

        if user_turn["user"] or user_turn["character"]:
            chat_history.append(user_turn)

        chat_data["chat_history"] = chat_history
        character_data["chats"][current_chat_id] = chat_data
        configuration_data['character_list'][character_name] = character_data
        
        self.save_configuration_edit(configuration_data)

    def add_message_to_config(self, character_name, author_name, is_user, text, message_id):
        """
        Adds a new message to the chat content of a specific character in the configuration.
        """
        configuration_data = self.load_configuration()
        character_data = configuration_data['character_list'].get(character_name)

        if not character_data or "chats" not in character_data:
            return

        current_chat_id = character_data.get("current_chat", None)
        if not current_chat_id or current_chat_id not in character_data["chats"]:
            return

        chat_data = character_data["chats"][current_chat_id]
        chat_content = chat_data.get("chat_content", {})

        sequence_number = len(chat_content) + 1
        new_message = {
            "message_id": message_id,
            "sequence_number": sequence_number,
            "author_name": author_name,
            "is_user": is_user,
            "current_variant_id": "default",
            "variants": [
                {
                    "variant_id": "default",
                    "text": text
                }
            ]
        }
        
        chat_content[message_id] = new_message
        chat_data["chat_content"] = chat_content
        character_data["chats"][current_chat_id] = chat_data
        configuration_data['character_list'][character_name] = character_data

        self.save_configuration_edit(configuration_data)

        self.renumber_sequence_numbers(character_name)
        self.update_chat_history(character_name)

    def regenerate_message_in_config(self, character_name, message_id, text):
        """
        Regenerates a message by adding a new variant to the same message_id.
        """
        configuration_data = self.load_configuration()
        character_data = configuration_data['character_list'].get(character_name)

        if not character_data or "chats" not in character_data:
            logger.error(f"Character '{character_name}' not found or has no chats.")
            return

        current_chat_id = character_data.get("current_chat")
        if not current_chat_id or current_chat_id not in character_data["chats"]:
            logger.error(f"Current chat for '{character_name}' is invalid or missing.")
            return

        chat_data = character_data["chats"][current_chat_id]
        chat_content = chat_data.get("chat_content", {})

        msg = chat_content.get(message_id)
        if not msg:
            logger.error(f"Message with ID {message_id} not found.")
            return

        variant_ids = [v["variant_id"] for v in msg.get("variants", [])]
        regen_count = sum(1 for vid in variant_ids if vid.startswith("regen_"))
        new_variant_id = f"regen_{regen_count}"

        msg["variants"].append({
            "variant_id": new_variant_id,
            "text": text
        })

        msg["current_variant_id"] = new_variant_id

        chat_content[message_id] = msg
        chat_data["chat_content"] = chat_content
        character_data["chats"][current_chat_id] = chat_data
        configuration_data['character_list'][character_name] = character_data

        self.save_configuration_edit(configuration_data)

        self.renumber_sequence_numbers(character_name)
        self.update_chat_history(character_name)

    def edit_chat_message(self, message_id, character_name, edited_text):
        """
        Edits the text of an existing chat message (only the current variant) inside the currently selected chat of a character.
        """
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                logger.error(f"Character {character_name} not found")
                return False

            char_data = character_list[character_name]

            current_chat_id = char_data.get("current_chat")
            if not current_chat_id or current_chat_id not in char_data["chats"]:
                logger.error(f"Current chat for {character_name} is invalid or missing.")
                return False

            chat_data = char_data["chats"][current_chat_id]
            chat_content = chat_data.get("chat_content", {})

            if message_id not in chat_content:
                logger.error(f"Message {message_id} not found")
                return False

            target = chat_content[message_id]
            current_variant_id = target.get("current_variant_id", "default")
            variants = target.get("variants", [])

            updated = False

            for variant in variants:
                if variant["variant_id"] == current_variant_id:
                    variant["text"] = edited_text
                    updated = True
                    break

            if not updated and variants:
                logger.warning(f"Current variant {current_variant_id} not found in variants. Creating new default variant.")
                variants.append({
                    "variant_id": "default",
                    "text": edited_text
                })
                target["variants"] = variants
                target["current_variant_id"] = "default"
                updated = True

            if not variants:
                target["variants"] = [{
                    "variant_id": "default",
                    "text": edited_text
                }]
                target["current_variant_id"] = "default"
                updated = True

            if not updated:
                logger.warning(f"Failed to update message {message_id}")
                return False

            chat_content[message_id] = target
            chat_data["chat_content"] = chat_content
            char_data["chats"][current_chat_id] = chat_data
            configuration_data["character_list"][character_name] = char_data

            self.save_configuration_edit(configuration_data)

            self.renumber_sequence_numbers(character_name)
            self.update_chat_history(character_name)

            return True

        except Exception as e:
            logger.error(f"Edit message error: {e}")
            traceback.print_exc()
            return False
    
    def delete_chat_message(self, message_id, character_name):
        """
        Deletes a message from the currently selected chat of a character.
        """
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                logger.error(f"Character {character_name} not found")
                return False

            char_data = character_list[character_name]

            current_chat_id = char_data.get("current_chat")
            if not current_chat_id or current_chat_id not in char_data["chats"]:
                logger.error(f"Current chat for {character_name} is invalid or missing.")
                return False

            chat_data = char_data["chats"][current_chat_id]
            chat_content = chat_data.get("chat_content", {})
            
            if message_id in chat_content:
                del chat_content[message_id]
                
            chat_data["chat_content"] = chat_content
            char_data["chats"][current_chat_id] = chat_data
            configuration_data["character_list"][character_name] = char_data
            
            self.save_configuration_edit(configuration_data)
            
            self.renumber_sequence_numbers(character_name)
            self.update_chat_history(character_name)
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            traceback.print_exc()
            return False
    
    def delete_chat_messages(self, character_name, message_ids):
        """
        Deletes multiple messages from the currently selected chat of a character.
        """
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                logger.error(f"Character {character_name} not found")
                return False

            char_data = character_list[character_name]

            current_chat_id = char_data.get("current_chat")
            if not current_chat_id or current_chat_id not in char_data["chats"]:
                logger.error(f"Current chat for {character_name} is invalid or missing.")
                return False

            chat_data = char_data["chats"][current_chat_id]
            chat_content = chat_data.get("chat_content", {})

            for message_id in message_ids:
                if message_id in chat_content:
                    del chat_content[message_id]

            chat_data["chat_content"] = chat_content
            char_data["chats"][current_chat_id] = chat_data
            configuration_data["character_list"][character_name] = char_data

            self.save_configuration_edit(configuration_data)
            
            self.renumber_sequence_numbers(character_name)
            self.update_chat_history(character_name)
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting messages: {e}")
            traceback.print_exc()
            return False
    
    def create_new_chat(self, character_name, conversation_method, new_name, new_description, new_personality, new_scenario, new_first_message, new_example_messages, new_alternate_greetings, new_creator_notes, chat_name):
        """
        Creates a new chat session for the specified character with updated information, including support for variants.

        Args:
            character_name (str): Name of the existing character to start a new chat with.
            conversation_method (str): Method used for conversation (e.g., "Character AI", "Local LLM").
            new_name (str): New name for the character (optional).
            new_description (str): Character description.
            new_personality (str): Personality traits.
            new_scenario (str): Scenario or background context.
            new_first_message (str): First message from the character.
            new_example_messages (list): Example messages for training.
            new_alternate_greetings (list): Alternative greetings as message variants.
            new_creator_notes (str): Creator notes or title.
            chat_name (str): The custom name for this chat (used as chat_id).
        """
        configuration_data = self.load_configuration()
        character_list = configuration_data.get("character_list", {})

        if character_name not in character_list:
            logger.error(f"Character '{character_name}' not found in configuration.")
            return

        character_data = character_list[character_name]

        new_chat_id = str(uuid.uuid4())

        current_chat_id = character_data.get("current_chat", None)
        if not current_chat_id or current_chat_id not in character_data["chats"]:
            return

        message_id = str(uuid.uuid4())

        variants = [
            {"variant_id": "default", "text": new_first_message}
        ]

        for i, greeting in enumerate(new_alternate_greetings):
            variants.append({
                "variant_id": f"v{i+1}",
                "text": greeting.strip()
            })

        main_message = {
            "message_id": message_id,
            "sequence_number": 1,
            "author_name": new_name or character_name,
            "is_user": False,
            "current_variant_id": "default",
            "variants": variants
        }

        chat_content = {message_id: main_message}

        chat_history = []
        chat_history.append({
            "user": "",
            "character": new_first_message
        })

        system_prompt_parts = []

        if new_description.strip():
            system_prompt_parts.append(new_description.strip())

        if new_personality.strip():
            system_prompt_parts.append(f"{new_personality.strip()}.")

        if new_scenario.strip():
            system_prompt_parts.append(f"Here is the dialogue script: {new_scenario.strip()}.\n\n")

        if new_example_messages.strip():
            system_prompt_parts.append(
                f"[Example Chat]:\n{new_example_messages.strip()}\n\n"
                "Your response should follow the same pattern and style as above.[End Example Chat]"
            )

        system_prompt_parts.append("Respond as the character, do not break role or add extra explanations.")
        system_prompt = " ".join(system_prompt_parts)

        character_data.update({
            "character_title": new_creator_notes,
            "character_description": new_description,
            "character_personality": new_personality,
            "first_message": new_first_message,
            "scenario": new_scenario,
            "example_messages": new_example_messages,
            "alternate_greetings": new_alternate_greetings,
            "conversation_method": conversation_method,
            "system_prompt": system_prompt
        })

        new_chat = {
            "name": chat_name,
            "created_at": datetime.datetime.now().isoformat(),
            "current_emotion": "neutral",
            "chat_history": chat_history,
            "chat_content": chat_content,
        }
        
        if "chats" not in character_data:
            character_data["chats"] = {}

        character_data["chats"][new_chat_id] = new_chat
        character_data["current_chat"] = new_chat_id

        if new_name and new_name != character_name:
            del character_list[character_name]
            character_list[new_name] = character_data
        else:
            character_list[character_name] = character_data

        configuration_data['character_list'] = character_list
        self.save_configuration_edit(configuration_data)
        logger.info(f"Created new chat '{chat_name}' for character '{character_name}'")
    
    def get_character_data(self, name, key):
        """
        Retrieves a specific value from a character's configuration data.
        """
        configuration_data = self.load_configuration()
        return configuration_data["character_list"][name].get(key, None)

    def delete_character(self, character_name):
        """
        Deletes a character from the configuration file.
        """
        configuration_data = self.load_configuration()
        if "character_list" in configuration_data and character_name in configuration_data["character_list"]:
            del configuration_data["character_list"][character_name]
            self.save_configuration_edit(configuration_data)
            logger.info(f"Character '{character_name}' has been deleted successfully.")
        else:
            logger.error(f"Character '{character_name}' not found in the configuration.")

    def renumber_sequence_numbers(self, character_name):
        config = self.load_configuration()
        char_data = config["character_list"].get(character_name)
        if not char_data:
            return
        
        chat_id = char_data.get("current_chat")

        chat_data = char_data["chats"][chat_id]
        chat_content = chat_data.get("chat_content", {})

        sorted_messages = sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf')))

        for idx, (msg_id, msg) in enumerate(sorted_messages):
            msg["sequence_number"] = idx + 1

        chat_data["chat_content"] = chat_content
        char_data["chats"][chat_id] = chat_data
        config["character_list"][character_name] = char_data
        self.save_configuration_edit(config)
