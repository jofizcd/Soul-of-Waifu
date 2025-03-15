import os
import re
import io
import asyncio
import aiohttp
import numpy as np
import soundfile as sf
import sounddevice as sd

from io import BytesIO
from PIL import Image
from pydub import AudioSegment
from PyCharacterAI import Client
from configuration import configuration

CACHE_DIR = os.path.join(os.getcwd(), "cache")

class CharacterAI():
    def __init__(self):
        self.client = Client()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        self.character_ai_token = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
        
    async def get_client(self):
        await self.client.authenticate(self.character_ai_token)

    async def create_character(self, character_id):
        await self.get_client()

        chat, greeting_message = await self.client.chat.create_chat(character_id)
        character_information = await self.client.character.fetch_character_info(character_id)
        
        character_name = character_information.name
        character_title = character_information.title
        greeting_message = character_information.greeting
        character_avatar = character_information.avatar
        character_avatar_url = character_avatar.get_url()
        chat_id = chat.chat_id

        all_messages = []
        next_token = None
            
        while True:
            try:
                messages, next_token = await self.client.chat.fetch_messages(chat_id, next_token=next_token)
                if not messages:
                    break
                all_messages.extend(messages)
                if not next_token:
                    break
            except Exception as e:
                print(f"Error: {e}")
                break
            
        all_messages.reverse()

        chat_content = {}
        message_id = 1
        for message in all_messages:
            try:
                author_name = message.author_name
                turn_id = message.turn_id
                primary_candidate = message.get_primary_candidate()
                primary_candidate_id = primary_candidate.candidate_id
                text = primary_candidate.text
                if author_name == character_name:
                    chat_content[message_id] = {
                        "turn_id": turn_id,
                        "candidate_id": primary_candidate_id,
                        "author_name": author_name,
                        "is_user": False,
                        "text": text
                    }
                else:
                    chat_content[message_id] = {
                        "turn_id": turn_id,
                        "candidate_id": primary_candidate_id,
                        "author_name": author_name,
                        "is_user": True,
                        "text": text
                    }

                message_id += 1
            except Exception as e:
                print(f"Error: {e}")

        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                character_list[character_name] = {
                    "character_id": character_id,
                    "chat_id": chat_id,
                    "character_avatar": character_avatar_url,
                    "character_title": character_title,
                    "character_description": None,
                    "character_personality": None,
                    "first_message": greeting_message,
                    "current_text_to_speech": "Nothing",
                    "voice_name": None,
                    "character_ai_voice_id": None,
                    "elevenlabs_voice_id": None,
                    "xttsv2_voice_type": None, 
                    "xttsv2_rvc_enabled": None, 
                    "xttsv2_rvc_file": None,
                    "current_sow_system_mode": "Nothing",
                    "expression_images_folder": None,
                    "live2d_model_folder": None,
                    "conversation_method": "Character AI",
                    "chat_content": {}
                }

            character_list[character_name]["chat_content"] = chat_content
            configuration_data["character_list"] = character_list

            self.configuration_characters.save_configuration_edit(configuration_data)
        except Exception as e:
            print(f"Error: {e}")
        
        return character_name

    async def download_image(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Download error: {response.status}")
        except Exception as e:
            print(f"Error when uploading an image: {e}")
            return None

    def save_to_cache(self, url, data):
        file_name = os.path.basename(url)
        file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
        file_path = os.path.join(CACHE_DIR, file_name)

        os.makedirs(CACHE_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def get_from_cache(self, url):
        file_name = os.path.basename(url)
        file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
        file_path = os.path.join(CACHE_DIR, file_name)
        
        if os.path.exists(file_path):
            return file_path
        else:
            return None

    def process_image(self, data):
        with BytesIO(data) as bio:
            image = Image.open(bio)
            with BytesIO() as output:
                image.convert("RGBA").save(output, format="PNG")
                return output.getvalue()

    async def load_image(self, url):
        cached_path = self.get_from_cache(url)
        if cached_path:
            return cached_path
        else:
            data = await self.download_image(url)
            if data:
                if url.lower().endswith((".webp",)):
                    data = self.process_image(data)
                file_path = self.save_to_cache(url, data)
                return file_path

    async def fetch_chat(self, chat_id, character_name, character_id, character_avatar_url, character_title, character_description, character_personality, first_message, current_text_to_speech, voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder, conversation_method, current_emotion):
        await self.get_client()
        
        all_messages = []
        next_token = None

        while True:
            try:
                messages, next_token = await self.client.chat.fetch_messages(chat_id, next_token=next_token)
                if not messages:
                    break
                all_messages.extend(messages)
                if not next_token:
                    break
            except Exception as e:
                print(f"Error when receiving messages: {e}")
                break
        
        all_messages.reverse()
        
        chat_content = {}
        message_id = 1
        for message in all_messages:
            try:
                author_name = message.author_name
                turn_id = message.turn_id
                primary_candidate = message.get_primary_candidate()
                primary_candidate_id = primary_candidate.candidate_id
                text = primary_candidate.text
                if author_name == character_name:
                    chat_content[message_id] = {
                        "turn_id": turn_id,
                        "candidate_id": primary_candidate_id,
                        "author_name": author_name,
                        "is_user": False,
                        "text": text
                    }
                else:
                    chat_content[message_id] = {
                        "turn_id": turn_id,
                        "candidate_id": primary_candidate_id,
                        "author_name": author_name,
                        "is_user": True,
                        "text": text
                    }

                message_id += 1
            except Exception as e:
                print(f"Error processing the message: {e}")
        
        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                character_list[character_name] = {
                    "character_id": character_id,
                    "chat_id": chat_id,
                    "character_avatar": character_avatar_url,
                    "character_title": character_title,
                    "character_description": character_description,
                    "character_personality": character_personality,
                    "first_message": first_message,
                    "current_text_to_speech": current_text_to_speech,
                    "voice_name": voice_name,
                    "character_ai_voice_id": character_ai_voice_id,
                    "elevenlabs_voice_id": elevenlabs_voice_id,
                    "xttsv2_voice_type": xttsv2_voice_type, 
                    "xttsv2_rvc_enabled": xttsv2_rvc_enabled, 
                    "xttsv2_rvc_file": xttsv2_rvc_file,
                    "current_sow_system_mode": current_sow_system_mode,
                    "expression_images_folder": expression_images_folder,
                    "live2d_model_folder": live2d_model_folder,
                    "conversation_method": conversation_method,
                    "current_emotion": current_emotion,
                    "chat_content": {}
                    }
            else:
                character_list[character_name] = {
                    "character_id": character_id,
                    "chat_id": chat_id,
                    "character_avatar": character_avatar_url,
                    "character_title": character_title,
                    "character_description": character_description,
                    "character_personality": character_personality,
                    "first_message": first_message,
                    "current_text_to_speech": current_text_to_speech,
                    "voice_name": voice_name,
                    "character_ai_voice_id": character_ai_voice_id,
                    "elevenlabs_voice_id": elevenlabs_voice_id,
                    "xttsv2_voice_type": xttsv2_voice_type, 
                    "xttsv2_rvc_enabled": xttsv2_rvc_enabled, 
                    "xttsv2_rvc_file": xttsv2_rvc_file,
                    "current_sow_system_mode": current_sow_system_mode,
                    "expression_images_folder": expression_images_folder,
                    "live2d_model_folder": live2d_model_folder,
                    "conversation_method": conversation_method,
                    "current_emotion": current_emotion,
                    "chat_content": {}
                    }

            character_list[character_name]["chat_content"] = chat_content
            configuration_data["character_list"] = character_list
            
            self.configuration_characters.save_configuration_edit(configuration_data)
        except Exception as e:
            print(f"Error when working with the configuration: {e}")

    async def search_voices(self, voice_name):
        await self.get_client()
        voices = await self.client.utils.search_voices(voice_name)
        return voices
        
    async def download_file(self, url, filename):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(filename, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)
                    return True
                return False

    async def play_preview_voice(self, voice_id):
        await self.get_client()
        voice = await self.client.utils.fetch_voice(voice_id)
        voice_preview_url = voice.preview_audio_url
        filename = "cache/character_voice_preview.wav"

        if await self.download_file(voice_preview_url, filename):
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                try:
                    data, samplerate = await asyncio.to_thread(sf.read, filename, dtype='float32')
                    await asyncio.to_thread(sd.play, data, samplerate)
                    await asyncio.to_thread(sd.wait)
                except Exception as e:
                    print(f"Audio playback error: {e}")
                finally:
                    os.remove(filename)
            else:
                print("Downloaded file is empty or corrupt.")
        else:
            print("Failed to download the preview file.")
        
    async def fetch_feature(self):
        await self.get_client()
        featured_characters = await self.client.character.fetch_featured_characters()
        return featured_characters
    
    async def fetch_recommended(self):
        await self.get_client()
        recommended_characters = await self.client.character.fetch_recommended_characters()
        return recommended_characters
        
    async def search_character(self, search_key):
        await self.get_client()
        searched_characters = await self.client.character.search_characters(search_key)
        return searched_characters
        
    def save_to_cache_character_card(self, url, data):
        file_name = os.path.basename(url)
        file_name = url.split("/")[-2] + "_" + url.split("/")[-1]
        file_path = os.path.join(CACHE_DIR, file_name)

        os.makedirs(CACHE_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def get_from_cache_character_card(self, url):
        file_name = os.path.basename(url)
        file_name = url.split("/")[-2] + "_" + url.split("/")[-1]
        file_path = os.path.join(CACHE_DIR, file_name)
        
        if os.path.exists(file_path):
            return file_path
        else:
            return None
        
    async def load_image_character_card(self, url):
        cached_path = self.get_from_cache_character_card(url)
        if cached_path:
            return cached_path
        else:
            data = await self.download_image(url)
            if data:
                if url.lower().endswith((".webp",)):
                    data = self.process_image(data)
                file_path = self.save_to_cache_character_card(url, data)
                return file_path
    
    async def fetch_character_information(self, character_id):
        await self.get_client()
        character_information = await self.client.character.fetch_character_info(character_id)
        
        character_name = character_information.name
        character_title = character_information.title
        greeting_message = character_information.greeting
        character_avatar = character_information.avatar
        character_avatar_url = character_avatar.get_url()
        character_avatar = await self.load_image(character_avatar_url)
        
        return character_name, character_title, greeting_message, character_avatar

    async def create_new_chat(self, character_id):
        await self.get_client()
        chat, greeting_message = await self.client.chat.create_chat(character_id)
        character_information = await self.client.character.fetch_character_info(character_id)
        
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data.get("character_list", {})

        character_name = character_information.name
        character_title = character_information.title
        greeting_message = character_information.greeting
        character_description = character_list[character_name]["character_description"]
        character_personality = character_list[character_name]["character_personality"]
        current_text_to_speech = character_list[character_name]["current_text_to_speech"]
        voice_name = character_list[character_name]["voice_name"]
        character_ai_voice_id = character_list[character_name]["character_ai_voice_id"]
        elevenlabs_voice_id = character_list[character_name]["elevenlabs_voice_id"]
        xttsv2_voice_type = character_list[character_name]["xttsv2_voice_type"]
        xttsv2_rvc_enabled = character_list[character_name]["xttsv2_rvc_enabled"]
        xttsv2_rvc_file = character_list[character_name]["xttsv2_rvc_file"]
        current_sow_system_mode = character_list[character_name]["current_sow_system_mode"]
        expression_images_folder = character_list[character_name]["expression_images_folder"]
        live2d_model_folder = character_list[character_name]["live2d_model_folder"]
        character_avatar = character_information.avatar
        character_avatar_url = character_avatar.get_url()
        chat_id = chat.chat_id
        current_emotion = character_list[character_name]["current_emotion"]
        
        await self.fetch_chat(chat_id, character_name, character_id, character_avatar_url, character_title, character_description, character_personality, greeting_message, current_text_to_speech, voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder, conversation_method="Character AI", current_emotion=current_emotion)
    
    async def edit_message(self, character_name, message_id, chat_id, turn_id, candidate_id, text):
        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_list = configuration_data.get("character_list", {})

            if character_name not in character_list:
                print(f"The character '{character_name}' was not found in the configuration.")
                return

            chat_content = character_list[character_name].get("chat_content", {})
            if message_id not in chat_content:
                print(f"The message with the ID {message_id} was not found in chat_content.")
                return

            await self.get_client()
            edited_message = await self.client.chat.edit_message(chat_id, turn_id, candidate_id, text)
            author_name = edited_message.author_name
            edited_message_primary = edited_message.get_primary_candidate()
            primary_candidate_id = edited_message_primary.candidate_id
            edited_text = edited_message_primary.text

            print(f"Updating the {message_id} message for the character {character_name}")
            print(f"New text: {edited_text}")

            chat_content[message_id] = {
                "turn_id": turn_id,
                "candidate_id": primary_candidate_id,
                "author_name": author_name,
                "is_user": True,
                "text": edited_text
            }

            character_list[character_name]["chat_content"] = chat_content
            configuration_data["character_list"] = character_list
            self.configuration_characters.save_configuration_edit(configuration_data)

            print("The configuration has been successfully updated.")

        except Exception as e:
            print(f"Error editing the message: {e}")
            import traceback
            traceback.print_exc()
    
    async def delete_message(self, character_name, message_id, chat_id, turn_id):
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data.get("character_list", {})
        chat_content = character_list[character_name]["chat_content"]
        
        if message_id in chat_content:
            del chat_content[message_id]

        character_list[character_name]["chat_content"] = chat_content
        configuration_data["character_list"] = character_list
        
        self.configuration_characters.save_configuration_edit(configuration_data)
        
        await self.get_client()
        await self.client.chat.delete_message(chat_id, turn_id)

    async def delete_messages(self, character_name, message_ids, chat_id, turn_ids):
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data.get("character_list", {})
        chat_content = character_list[character_name]["chat_content"]

        for message_id in message_ids:
            if message_id in chat_content:
                del chat_content[message_id]

        character_list[character_name]["chat_content"] = chat_content
        configuration_data["character_list"] = character_list
        
        self.configuration_characters.save_configuration_edit(configuration_data)

        await self.get_client()
        await self.client.chat.delete_messages(chat_id, turn_ids)

    async def send_message(self, character_id, chat_id, user_message, streaming=True):
        await self.get_client()
        answer = await self.client.chat.send_message(character_id, chat_id, user_message, streaming=True)

        async for message in answer:
            yield message
    
    async def generate_speech(self, chat_id, turn_id, candidate_id, voice_id):
        await self.get_client()

        speech = await self.client.utils.generate_speech(chat_id, turn_id, candidate_id, voice_id)
        audio_stream = io.BytesIO(speech)
        audio = await asyncio.to_thread(AudioSegment.from_file, audio_stream, format="mp3")

        wav_stream = io.BytesIO()
        await asyncio.to_thread(audio.export, wav_stream, format="wav")
        wav_stream.seek(0)
        wav_audio = await asyncio.to_thread(AudioSegment.from_file, wav_stream, format="wav")

        raw_data = np.array(wav_audio.get_array_of_samples())
        sample_rate = wav_audio.frame_rate

        await asyncio.to_thread(sd.play, raw_data, samplerate=sample_rate)
        await asyncio.to_thread(sd.wait)