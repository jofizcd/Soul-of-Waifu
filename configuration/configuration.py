import os
import json

class ConfigurationSettings():
    """
    This class manages a JSON configuration file that contains program settings and user data.
    """
    def __init__(self):
        self.settings_path = "configuration/settings.json"

    def load_configuration(self):
        """
        Loads configuration data from the JSON file.
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
                    "user_name": "User",
                    "user_description": "",
                    "user_avatar": "../resources/icons/person.png"
                }
            }
        with open(self.settings_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration(self):
        """
        Saves the current configuration data to the JSON file.
        """
        with open(self.settings_path, 'w', encoding="utf-8") as file:
            json.dump(self.configuration_data, file, ensure_ascii=False, indent=4)

    def save_configuration_edit(self, data):
        """
        Saving the current configuration data to a file.
        """
        with open(self.settings_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def update_main_setting(self, setting, value):
        """
        Updates a main setting in the configuration file.

        Args:
            setting (str): The key of the main setting to update.
            value (any): The value to set for the specified key.
        """
        configuration_data = self.load_configuration()
        if "main_settings" not in configuration_data:
            configuration_data["main_settings"] = {}
        configuration_data["main_settings"][setting] = value
        self.save_configuration_edit(configuration_data)

    def get_main_setting(self, setting):
        """
        Retrieves the value of a main setting from the configuration file.

        Args:
            setting (str): The key of the main setting to retrieve.

        Returns:
            any: The value of the specified key, or None if the key does not exist.
        """
        configuration_data = self.load_configuration()
        return configuration_data["main_settings"].get(setting, None)

    def update_user_data(self, key, value):
        """
        Updates a user data field in the configuration file.

        Args:
            key (str): The key of the user data field to update.
            value (any): The value to set for the specified key.
        """
        configuration_data = self.load_configuration()
        if "user_data" not in configuration_data:
            configuration_data["user_data"] = {}
        configuration_data["user_data"][key] = value
        self.save_configuration_edit(configuration_data)

    def get_user_data(self, key):
        """
        Retrieves a user data field from the configuration file.

        Args:
            key (str): The key of the user data field to retrieve.

        Returns:
            any: The value of the specified key, or None if the key does not exist.
        """
        configuration_data = self.load_configuration()
        return configuration_data["user_data"].get(key, None)
    
class ConfigurationAPI():
    """
    Configuration file with API-tokens.
    """
    def __init__(self):
        self.api_tokens_path = "configuration/api.json"

    def load_configuration(self):
        """
        Loading configuration data from a file.
        """
        if not os.path.exists(self.api_tokens_path):
            return {}
        with open(self.api_tokens_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration(self):
        """
        Saving the current configuration data to a file.
        """
        configuration_data = self.load_configuration()
        with open(self.api_tokens_path, 'w', encoding="utf-8") as file:
            json.dump(configuration_data, file, ensure_ascii=False, indent=4)

    def save_configuration_edit(self, data):
        """
        Saving the current configuration data to a file.
        """
        with open(self.api_tokens_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    
    def save_api_token(self, variable, variable_value):
        """
        Saves the API value to a configuration file.
        
        Args:
            variable (str): Variable name.
            variable_value (any): Variable value.
        """
        configuration_data = self.load_configuration()
        configuration_data[variable] = variable_value
        self.save_configuration_edit(configuration_data)

    def get_token(self, api):
        configuration_data = self.load_configuration()
        return configuration_data.get(api)

class ConfigurationCharacters():
    """
    Configuration file with characters information.
    """
    def __init__(self):
        self.characters_path = "configuration/characters.json"
        self.configuration_data = self.load_configuration()

    def load_configuration(self):
        """
        Loading configuration data from a file.
        """
        if not os.path.exists(self.characters_path):
            return {}
        with open(self.characters_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration(self):
        """
        Saving the current configuration data to a file.
        """
        configuration_data = self.load_configuration()
        with open(self.characters_path, 'w', encoding="utf-8") as file:
            json.dump(configuration_data, file, ensure_ascii=False, indent=4)

    def save_configuration_edit(self, data):
        """
        Saving the current configuration data to a file.
        """
        with open(self.characters_path, 'w', encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def save_characterai_to_list(self, character_name, character_id, chat_id, character_avatar, character_title, character_description, character_personality, first_message, voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file, expression_images_folder, live2d_model_folder, conversation_method):
        """
        Adding character information from Character AI to the configuration file.
        
        Args:
            character_name (str): Character's name,
            character_id (str): Character identifier,
            chat_id (str): Current chat ID,
            character_avatar (str): The url address to avatar,
            character_title (str): Character title,
            character_description (str): Brief character description,
            character_personality (str): Long information about character,
            first_message (str): Character's first message,
            voice_name (str): Name for TTS voice,
            character_ai_voice_id (str): Voice ID for TTS voice,
            elevenlabs_voice_id (str): Voice ID for TTS voice from ElevenLabs,
            conversation_method (str): Character's conversation method.
        """
        configuration_data = self.load_configuration()
        if 'character_list' not in configuration_data:
            configuration_data['character_list'] = {}

        configuration_data['character_list'][character_name] = {
            "character_id": character_id,
            "chat_id": chat_id, 
            "character_avatar": character_avatar,
            "character_title": character_title, 
            "character_description": character_description, 
            "character_personality": character_personality,
            "first_message": first_message,
            "voice_name": voice_name,
            "character_ai_voice_id": character_ai_voice_id,
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "xttsv2_voice_type": xttsv2_voice_type,
            "xttsv2_rvc_enabled": xttsv2_rvc_enabled,
            "xttsv2_rvc_file": xttsv2_rvc_file,
            "current_sow_system_mode": "Nothing",
            "expression_images_folder": expression_images_folder,
            "live2d_model_folder": live2d_model_folder,
            "conversation_method": conversation_method
            }
        
        self.save_configuration_edit(configuration_data)

    def save_character_card(self, character_name, character_title, character_avatar, character_description, character_personality, first_message, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file, expression_images_folder, live2d_model_folder, conversation_method):
        """
        Adding information about the character in the card format to the configuration file.
        
        Args:
            character_name (str): Character's name,
            character_title (str),
            character_avatar (str): Character's directory to image,
            character_description (str): Character's short description,
            character_personality (str): Character's main information about personality,
            first_message (str): Character's first message,
            elevenlabs_voice_id (str): Voice ID for TTS voice from ElevenLabs,
            xttsv2_voice_type (str): Voice type for XTTSv2 TTS,
            xttsv2_rvc_enabled (bool): RVC enabled for character,
            xttsv2_rvc_file (str): RVC file path, 
            conversation_method (str): Character's conversation method.
        """
        configuration_data = self.load_configuration()
        if 'character_list' not in configuration_data:
            configuration_data['character_list'] = {}

        chat_content = {
            1: {
                "author_name": character_name,
                "is_user": False,
                "text": first_message
            }
        }

        chat_history = []
        for message_id, message_data in chat_content.items():
            if message_data["is_user"]:
                chat_history.append({"user": message_data["text"], "character": ""})
            else:
                if chat_history:
                    chat_history[-1]["character"] = message_data["text"]
                else:
                    chat_history.append({"user": "", "character": message_data["text"]})
        
        configuration_data['character_list'][character_name] = {
            "character_avatar": character_avatar,
            "character_title": character_title,
            "character_description": character_description,
            "character_personality": character_personality,
            "first_message": first_message,
            "current_text_to_speech": "Nothing",
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "xttsv2_voice_type": xttsv2_voice_type,
            "xttsv2_rvc_enabled": xttsv2_rvc_enabled,
            "xttsv2_rvc_file": xttsv2_rvc_file,
            "current_sow_system_mode": "Nothing",
            "expression_images_folder": expression_images_folder,
            "live2d_model_folder": live2d_model_folder,
            "conversation_method": conversation_method,
            "system_prompt": f"{character_description} {character_personality}",
            "chat_history": chat_history,
            "chat_content": chat_content
        }

        self.save_configuration_edit(configuration_data)
    
    def update_chat_history(self, character_name):
        configuration_data = self.load_configuration()

        if 'character_list' not in configuration_data:
            raise ValueError("Character list not found in configuration data.")

        character_data = configuration_data['character_list'].get(character_name)
        if not character_data:
            raise ValueError(f"Character '{character_name}' not found in character list.")

        chat_content = character_data.get("chat_content", {})
        
        chat_history = []
        current_user_message = None

        sorted_messages = sorted(chat_content.items(), key=lambda x: int(x[0]))

        for message_id, message_data in sorted_messages:
            if message_data["is_user"]:
                current_user_message = message_data["text"]
            else:
                chat_history.append({
                    "user": current_user_message if current_user_message else "",
                    "character": message_data["text"]
                })
                current_user_message = None

        character_data["chat_history"] = chat_history
        configuration_data['character_list'][character_name] = character_data
        self.save_configuration_edit(configuration_data)

        print(f"Updated chat_history for {character_name}:")
        for entry in chat_history:
            print(f"User: {entry['user']}")
            print(f"Character: {entry['character']}")
            print("---")

    def add_message_to_chat_content(self, character_name, author_name, is_user, text):
        configuration_data = self.load_configuration()
        if 'character_list' not in configuration_data:
            raise ValueError("Character list not found in configuration data.")

        character_data = configuration_data['character_list'].get(character_name)
        if not character_data:
            raise ValueError(f"Character '{character_name}' not found in character list.")

        chat_content = character_data.get("chat_content", {})
        new_message_id = str(max((int(k) for k in chat_content.keys()), default=0) + 1)

        chat_content[new_message_id] = {
            "author_name": author_name,
            "is_user": is_user,
            "text": text
        }

        character_data["chat_content"] = chat_content
        configuration_data['character_list'][character_name] = character_data
        
        self.save_configuration_edit(configuration_data)
        self.update_chat_history(character_name)

    def edit_chat_message(self, message_id, character_name, edited_text, original_text):
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                return

            chat_content = character_list[character_name].get("chat_content", {})
            chat_history = character_list[character_name].get("chat_history", [])

            if message_id not in chat_content:
                return

            is_user = chat_content[message_id]["is_user"]
            author_name = chat_content[message_id]["author_name"]

            chat_content[message_id] = {
                "author_name": author_name,
                "is_user": is_user,
                "text": edited_text
            }

            for message in chat_history:
                if message.get("user") == original_text:
                    message["user"] = edited_text
                elif message.get("character") == original_text:
                    message["character"] = edited_text

            character_list[character_name]["chat_content"] = chat_content
            character_list[character_name]["chat_history"] = chat_history
            configuration_data["character_list"] = character_list
            self.save_configuration_edit(configuration_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def delete_chat_message(self, message_id, character_name):
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                return

            chat_content = character_list[character_name].get("chat_content", {})
            chat_history = character_list[character_name].get("chat_history", [])
            
            deleted_text = chat_content[message_id]["text"]

            if message_id not in chat_content:
                return

            if message_id in chat_content:
                del chat_content[message_id]

            chat_history = [
                message for message in chat_history
                if message.get("user") != deleted_text and message.get("character") != deleted_text
            ]

            character_list[character_name]["chat_content"] = chat_content
            character_list[character_name]["chat_history"] = chat_history
            configuration_data["character_list"] = character_list

            self.save_configuration_edit(configuration_data)
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def delete_chat_messages(self, message_ids, character_name):
        try:
            configuration_data = self.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                return

            chat_content = character_list[character_name]["chat_content"]
            chat_history = character_list[character_name]["chat_history"]

            deleted_texts = set()
            for message_id in message_ids:
                if message_id in chat_content:
                    deleted_texts.add(chat_content[message_id]["text"])
                    del chat_content[message_id]

            chat_history = [
                message for message in chat_history
                if message.get("user") not in deleted_texts and message.get("character") not in deleted_texts
            ]

            character_list[character_name]["chat_content"] = chat_content
            character_list[character_name]["chat_history"] = chat_history
            configuration_data["character_list"] = character_list

            self.save_configuration_edit(configuration_data)

        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def create_new_chat(self, character_name, conversation_method, new_description, new_personality, new_first_message):
        configuration_data = self.load_configuration()
        character_list = configuration_data.get("character_list", {})

        character_avatar = character_list[character_name]["character_avatar"]
        character_title = character_list[character_name]["character_title"]
        first_message = new_first_message
        character_description = new_description
        character_personality = new_personality
        current_text_to_speech = character_list[character_name]["current_text_to_speech"]
        elevenlabs_voice_id = character_list[character_name]["elevenlabs_voice_id"]
        xttsv2_voice_type = character_list[character_name]["xttsv2_voice_type"]
        xttsv2_rvc_enabled = character_list[character_name]["xttsv2_rvc_enabled"]
        xttsv2_rvc_file = character_list[character_name]["xttsv2_rvc_file"]
        current_sow_system_mode = character_list[character_name]["current_sow_system_mode"]
        expression_images_folder = character_list[character_name]["expression_images_folder"]
        live2d_model_folder = character_list[character_name]["live2d_model_folder"]

        chat_content = {
            1: {
                "author_name": character_name,
                "is_user": False,
                "text": first_message
            }
        }

        chat_history = []
        for message_id, message_data in chat_content.items():
            if message_data["is_user"]:
                chat_history.append({"user": message_data["text"], "character": ""})
            else:
                if chat_history:
                    chat_history[-1]["character"] = message_data["text"]
                else:
                    chat_history.append({"user": "", "character": message_data["text"]})
        
        configuration_data['character_list'][character_name] = {
            "character_avatar": character_avatar,
            "character_title": character_title,
            "character_description": character_description,
            "character_personality": character_personality,
            "first_message": first_message,
            "current_text_to_speech": current_text_to_speech,
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "xttsv2_voice_type": xttsv2_voice_type,
            "xttsv2_rvc_enabled": xttsv2_rvc_enabled,
            "xttsv2_rvc_file": xttsv2_rvc_file,
            "current_sow_system_mode": current_sow_system_mode,
            "expression_images_folder": expression_images_folder,
            "live2d_model_folder": live2d_model_folder,
            "conversation_method": conversation_method,
            "system_prompt": f"[INST] {character_description} {character_personality} [/INST]",
            "chat_history": chat_history,
            "chat_content": chat_content
        }

        self.save_configuration_edit(configuration_data)
    
    def get_character_data(self, name, key):
        """
        Retrieves a user data field from the configuration file.
        """
        configuration_data = self.load_configuration()
        return configuration_data["character_list"][name].get(key, None)

    def delete_character(self, character_name):
        """
        Deletes the character from the configuration file.

        Args:
            character_name (str): Character Name.
        """
        configuration_data = self.load_configuration()
        if "character_list" in configuration_data and character_name in configuration_data["character_list"]:
            del configuration_data["character_list"][character_name]
            self.save_configuration_edit(configuration_data)
            print(f"Character '{character_name}' has been deleted successfully.")
        else:
            print(f"Character '{character_name}' not found in the configuration.")



