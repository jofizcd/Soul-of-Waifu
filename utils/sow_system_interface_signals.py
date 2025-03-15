import re
import os
import json
import asyncio
import traceback
import numpy as np
import OpenGL.GL as gl
import onnxruntime as ort
import live2d.v3 as live2d

from PIL import Image
from transformers import AutoTokenizer

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimerEvent
from PyQt6.QtGui import QPixmap, QFont, QPainter, QMouseEvent, QCursor, QGuiApplication
from PyQt6.QtWidgets import QLabel, QMainWindow, QWidget, QHBoxLayout, QMainWindow, QVBoxLayout, QFrame, QSizePolicy

from resources.data.sowSystem import sow_System
from configuration import configuration
from api_clients.character_ai_client import CharacterAI
from api_clients.mistral_ai_client import MistralAI
from api_clients.local_ai_client import LocalAI
from utils.translator import Translator
from utils.text_to_speech import ElevenLabs, XTTSv2
from utils.speech_to_text import Speech_To_Text

class Soul_Of_Waifu_System(QMainWindow):
    def __init__(self, parent, character_name):
        """
        Initializes the Soul of Waifu System (SOW) for a specific character.
        """
        super(Soul_Of_Waifu_System, self).__init__()
        self.ui = sow_System(parent=parent)
        self.ui.setupUi()
        self.character_name = character_name
        
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.parent_window = parent
        self.running_avatar = False
        self.running_image = False
        self.running_live2d = False
        self.avatar_task = None
        self.image_task = None
        self.live2d_task = None
        self.running_live2d_no_gui = False
        self.live2d_no_gui_task = None
        self.tokenizer = None
        self.session = None

        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]
        current_sow_system_mode = character_information["current_sow_system_mode"]
        
        self.live2d_no_gui = None
        self.live2d_expression_widget = None

        # Timers and counters for each tab
        self.timer1 = QtCore.QTimer(self)
        self.timer1.timeout.connect(self.updateTimerAvatar)
        self.elapsed1 = 0

        self.timer2 = QtCore.QTimer(self)
        self.timer2.timeout.connect(self.updateTimerImage)
        self.elapsed2 = 0

        self.timer3 = QtCore.QTimer(self)
        self.timer3.timeout.connect(self.updateTimerLive2D)
        self.elapsed3 = 0

        # Initialize AI clients and other utilities
        self.character_ai_client = CharacterAI()
        self.mistral_ai_client = MistralAI()
        self.local_ai_client = LocalAI()
        self.eleven_labs_client = ElevenLabs()
        self.xttsv2_client = XTTSv2()
        self.translator = Translator()
        self.speech_to_text = Speech_To_Text()

        # Main settings and variables
        self.speech_to_text_method = self.configuration_settings.get_main_setting("stt_method")
        self.live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")
        self.input_device = self.configuration_settings.get_main_setting("input_device")
        self.output_device = self.configuration_settings.get_main_setting("output_device")
        self.current_translator = self.configuration_settings.get_main_setting("translator")
        self.target_language = self.configuration_settings.get_main_setting("target_language")
        self.translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        character_info = character_data["character_list"][character_name]
        self.character_id = character_info.get("character_id")
        self.chat_id = character_info.get("chat_id")
        self.character_avatar_url = character_info.get("character_avatar")
        self.character_title = character_info.get("character_title")
        self.character_description = character_info.get("character_description")
        self.character_personality = character_info.get("character_personality")
        self.first_message = character_info.get("first_message")
        self.chat_content = character_info.get("chat_content", {})

        # Retrieve voice-related data for the character
        self.voice_name = character_info.get("voice_name")
        self.character_ai_voice_id = character_info.get("character_ai_voice_id")
        self.elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
        self.xttsv2_voice_type = character_info.get("xttsv2_voice_type")
        self.xttsv2_rvc_enabled = character_info.get("xttsv2_rvc_enabled")
        self.xttsv2_rvc_file = character_info.get("xttsv2_rvc_file")

        # Paths for expression images and Live2D models
        self.expression_images_folder = character_info.get("expression_images_folder", None)
        self.live2d_model_folder = character_info.get("live2d_model_folder", None)

        self.current_conversation_method = character_information["conversation_method"]

        # Chat container for displaying messages
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setSpacing(5)
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background-color: transparent;")
        self.chat_widget.setLayout(self.chat_container)
        
        match current_sow_system_mode:
            case "Nothing":
                self.ui.scrollArea_chat_page1.setWidget(self.chat_widget)
            case "Expressions Images":
                self.ui.scrollArea_chat_page2.setWidget(self.chat_widget)
            case "Live2D Model":
                self.ui.scrollArea_chat_page3.setWidget(self.chat_widget)
        
        self.messages = {}

        emotions_path = "resources/data/emotions"
        self.emotion_resources = {
            emotion: {
                "image": emotion,
                "live2d_emotion": f"{emotions_path}\\{emotion}_animation.exp3.json",
            }
            for emotion in [
                "admiration", "amusement", "anger", "annoyance", "approval", "caring",
                "confusion", "curiosity", "desire", "disappointment", "disapproval",
                "disgust", "embarrassment", "excitement", "fear", "gratitude", "grief",
                "love", "nervousness", "neutral", "optimism", "pride", "realization",
                "relief", "remorse", "surprise", "joy", "sadness"
            ]
        }

    async def speech_to_speech_loop(self, mode):
        """
        Continuously runs the speech-to-speech process until the corresponding stop button is pressed.
        """
        try:
            while getattr(self, f"running_{mode}"):
                await self.speech_to_speech_main()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            print(f"{mode.capitalize()} task was cancelled.")
        finally:
            print(f"{mode.capitalize()} loop has stopped.")

    async def speech_to_speech_loop_no_gui(self):
        """
        Continuously runs the speech-to-speech process for Live2D No GUI mode.
        """
        if not self.running_live2d_no_gui:
            self.running_live2d_no_gui = True

        while self.running_live2d_no_gui:
            try:
                await self.speech_to_speech_no_gui()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                print("No GUI task was cancelled.")
                break
            except Exception as e:
                print(f"No GUI loop: {e}")
                break
    
    def toggleStartStopAvatar(self):
        """
        Toggles the Start/Stop state for the Avatar tab and manages the associated task.
        """
        if not hasattr(self, "running_avatar"):
            self.running_avatar = False 

        if not self.running_avatar:
            self.ui.pushButton_start_page1.setText(self.tr("Stop"))
            self.running_avatar = True
            self.timer1.start(1000)
            self.avatar_task = asyncio.create_task(self.speech_to_speech_loop("avatar"))
        else:
            self.ui.pushButton_start_page1.setText(self.tr("Start"))
            self.running_avatar = False
            self.timer1.stop()
            if self.avatar_task:
                self.avatar_task.cancel()
                self.avatar_task = None

    def toggleStartStopImage(self):
        """
        Toggles the Start/Stop state for the Expression Image tab and manages the associated task.
        """
        if not self.running_image:
            self.ui.pushButton_start_page2.setText(self.tr("Stop"))
            self.running_image = True
            self.timer2.start(1000)
            self.image_task = asyncio.create_task(self.speech_to_speech_loop("image"))
        else:
            self.ui.pushButton_start_page2.setText(self.tr("Start"))
            self.running_image = False
            self.timer2.stop()
            if self.image_task:
                self.image_task.cancel()
                self.image_task = None

    def toggleStartStopLive2D(self):
        """
        Toggles the Start/Stop state for the Live2D tab and manages the associated task.
        """
        if not self.running_live2d:
            self.ui.pushButton_start_page3.setText(self.tr("Stop"))
            self.running_live2d = True
            self.timer3.start(1000)
            self.live2d_task = asyncio.create_task(self.speech_to_speech_loop("live2d"))
        else:
            self.ui.pushButton_start_page3.setText(self.tr("Start"))
            self.running_live2d = False
            self.timer3.stop()
            if self.live2d_task:
                self.live2d_task.cancel()
                self.live2d_task = None

    def updateTimerAvatar(self):
        """
        Updates the timer display on the Avatar tab.
        """
        self.elapsed1 += 1
        minutes, seconds = divmod(self.elapsed1, 60)
        self.ui.timer_page1.setText(f"{minutes:02d}:{seconds:02d}")
    
    def updateTimerImage(self):
        """
        Updates the timer display on the Image tab.
        """
        self.elapsed2 += 1
        minutes, seconds = divmod(self.elapsed2, 60)
        self.ui.timer_page2.setText(f"{minutes:02d}:{seconds:02d}")
    
    def updateTimerLive2D(self):
        """
        Updates the timer display on the Live2D tab.
        """
        self.elapsed3 += 1
        minutes, seconds = divmod(self.elapsed3, 60)
        self.ui.timer_page3.setText(f"{minutes:02d}:{seconds:02d}")

    def draw_circle_avatar(self, avatar_path, widget):
        """
        Draws a circular avatar from the given image path and applies it to the specified widget.
        """
        pixmap = QPixmap(avatar_path)
        
        mask = QPixmap(pixmap.size())
        mask.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtCore.Qt.GlobalColor.black)
        painter.setPen(QtCore.Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()

        pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))

        def add_avatar(widget):
            widget.setPixmap(pixmap.scaled(100, 
                                           100, 
                                           QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
                                           QtCore.Qt.TransformationMode.SmoothTransformation)
                                        )
            widget.setFixedSize(40, 40)
            widget.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
            widget.setScaledContents(True)
        
        add_avatar(widget)
    
    def markdown_to_html(self, text):
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i><span style="color: #a3a3a3;">\1</span></i>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
        return text
    
    async def add_message(self, text, is_user, message_id=None):
        """
        Adds a message to the chat interface.
        """
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]

        current_sow_system_mode = character_information["current_sow_system_mode"]
        current_conversation_method = character_information["conversation_method"]
        character_avatar = character_information["character_avatar"]

        if current_conversation_method == "Character AI":
            character_avatar = self.character_ai_client.get_from_cache(character_avatar)
        
        self.user_avatar = self.configuration_settings.get_user_data("user_avatar")
        if not self.user_avatar:
            self.user_avatar = "resources/icons/person.png"

        if message_id is None:
            message_id = len(self.messages) + 1

        # Load user data and convert the message text to Markdown formatting
        user_name = self.configuration_settings.get_user_data("user_name")
        html_text = self.markdown_to_html(text)
        html_text = html_text.replace("{{user}}", user_name).replace("{{char}}", self.character_name)

        message_container = QHBoxLayout()
        message_container.setSpacing(5)
        message_container.setContentsMargins(10, 5, 10, 5)

        avatar_label = QLabel()

        # Create the message label with rich text formatting
        message_label = QLabel()
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setText(html_text)
        message_label.setWordWrap(True)
        message_label.setFont(QFont("Arial", 20))
        message_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        message_label.setMaximumWidth(350)

        small_name_label = QLabel()
        small_name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        small_name_label.setStyleSheet("font-size: 10px; color: gray;")

        message_frame = QFrame(None)
        message_frame.setStyleSheet("background-color: transparent; border-radius: 15px; padding: 0px;")
        message_frame.setLayout(message_container)

        # Configure the message appearance based on whether it's from the user or the character
        if is_user:
            message_label.setStyleSheet("background-color: #384a69; color: white; border-radius: 15px; padding: 12px; font-size: 14px; margin: 5px; line-height: 2.4;")
            avatar_pixmap = QPixmap(self.user_avatar)
            avatar_label.setPixmap(avatar_pixmap.scaled(45, 45, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            mask = QPixmap(avatar_pixmap.size())
            mask.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, avatar_pixmap.width(), avatar_pixmap.height())
            painter.end()

            avatar_pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))

            avatar_label.setPixmap(avatar_pixmap)
            avatar_label.setFixedSize(35, 35)
            avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
            avatar_label.setScaledContents(True)

            first_word = user_name.split()[0]
            small_name_label.setText(first_word)

            message_container.addStretch()
            message_container.addWidget(avatar_label)
            message_container.addWidget(message_label)
            message_container.addWidget(small_name_label)
        else:
            message_label.setStyleSheet("background-color: #222d40; color: white; border-radius: 15px; padding: 12px; font-size: 14px; margin: 5px; line-height: 2.4;")
            avatar_pixmap = QPixmap(character_avatar)
            avatar_label.setPixmap(avatar_pixmap.scaled(45, 45, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            mask = QPixmap(avatar_pixmap.size())
            mask.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, avatar_pixmap.width(), avatar_pixmap.height())
            painter.end()

            avatar_pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))

            avatar_label.setPixmap(avatar_pixmap)
            avatar_label.setFixedSize(35, 35)
            avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
            avatar_label.setScaledContents(True)
            first_word = self.character_name.split()[0]
            small_name_label.setText(first_word)

            message_container.addWidget(avatar_label)
            message_container.addWidget(message_label)
            message_container.addWidget(small_name_label)
            message_container.addStretch()

        self.chat_container.addWidget(message_frame)
        await asyncio.sleep(0.05)
        match current_sow_system_mode:
            case "Nothing":
                self.ui.scrollArea_chat_page1.verticalScrollBar().setValue(self.ui.scrollArea_chat_page1.verticalScrollBar().maximum())
            case "Expressions Images":
                self.ui.scrollArea_chat_page2.verticalScrollBar().setValue(self.ui.scrollArea_chat_page2.verticalScrollBar().maximum())
            case "Live2D Model":
                self.ui.scrollArea_chat_page3.verticalScrollBar().setValue(self.ui.scrollArea_chat_page3.verticalScrollBar().maximum())
        
        # Store the message data for future reference
        self.messages[message_id] = {
            "text": text,
            "html": html_text,
            "layout": message_container,
            "label": message_label,
            "is_user": is_user,
            "frame": message_frame
        }

        return {
            "label": message_label,
            "frame": message_frame
        }
    
    async def speech_to_speech_main(self):
        """
        Handles the main speech-to-speech process: captures user input via speech-to-text,
        processes translations if needed, and prepares the message for further handling.
        """
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]
        current_sow_system_mode = character_information["current_sow_system_mode"]
        current_text_to_speech = character_information["current_text_to_speech"]
        first_message = character_information["first_message"]
        current_emotion = character_information["current_emotion"]

        try:
            user_name = self.configuration_settings.get_user_data("user_name")
            user_description = self.configuration_settings.get_user_data("user_description")
            
            match self.speech_to_text_method:
                case 0: # Google STT English
                    user_text_original = await self.speech_to_text.speech_recognition_google()
                case 1: # Google STT Russian
                    user_text_original = await self.speech_to_text.speech_recognition_google()
                case 2: # Vosk English
                    user_text_original = await self.speech_to_text.speech_recognition_vosk()
                case 3: # Vosk Russian
                    user_text_original = await self.speech_to_text.speech_recognition_vosk()
                case 4: # Local Whisper
                    user_text_original = await self.speech_to_text.speech_recognition_whisper()
                
            user_text = user_text_original

            match self.current_translator:
                case 0:
                    pass
                case 1:
                    # Google Translate
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", 'en')
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 2:
                    # Yandex Translate
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", 'en')
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 3:
                    # Local MarianMT Translator
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 2:
                            pass

            user_text_markdown = self.markdown_to_html(user_text_original)
            if user_text:
                await self.add_message(user_text_markdown, is_user=True)
                await asyncio.sleep(0.05)
                match self.current_conversation_method:
                    case "Character AI":
                        character_answer_container = await self.add_message("", is_user=False)
                        character_answer_label = character_answer_container["label"]
                        full_text = ""
                        turn_id = ""
                        candidate_id = ""

                        async for message in self.character_ai_client.send_message(self.character_id, self.chat_id, user_text):
                            text = message.get_primary_candidate().text
                            turn_id = message.turn_id
                            candidate_id = message.get_primary_candidate().candidate_id
                            if text != full_text:
                                full_text = text
                                original_text = text
                                full_text = self.markdown_to_html(full_text)
                                character_answer_label.setText(full_text)
                                await asyncio.sleep(0.05)
                                match current_sow_system_mode:
                                    case "Nothing":
                                        self.ui.scrollArea_chat_page1.verticalScrollBar().setValue(self.ui.scrollArea_chat_page1.verticalScrollBar().maximum())
                                    case "Expressions Images":
                                        self.ui.scrollArea_chat_page2.verticalScrollBar().setValue(self.ui.scrollArea_chat_page2.verticalScrollBar().maximum())
                                    case "Live2D Model":
                                        self.ui.scrollArea_chat_page3.verticalScrollBar().setValue(self.ui.scrollArea_chat_page3.verticalScrollBar().maximum())
                                
                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, original_text))

                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translator
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "Character AI":
                                await asyncio.sleep(0.05)
                                await self.character_ai_client.generate_speech(self.chat_id, turn_id, candidate_id, self.character_ai_voice_id)
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

                        await self.character_ai_client.fetch_chat(
                                    self.chat_id, self.character_name, self.character_id, self.character_avatar_url, self.character_title,
                                    self.character_description, self.character_personality, first_message, current_text_to_speech,
                                    self.voice_name, self.character_ai_voice_id, self.elevenlabs_voice_id, self.xttsv2_voice_type, self.xttsv2_rvc_enabled,
                                    self.xttsv2_rvc_file, current_sow_system_mode, self.expression_images_folder, self.live2d_model_folder,
                                    self.current_conversation_method, current_emotion
                                )

                    case "Mistral AI":
                        configuration_data = self.configuration_characters.load_configuration()
                        character_data = configuration_data["character_list"].get(self.character_name)
                        system_prompt = character_data["system_prompt"]
                        chat_history = character_data.get("chat_history", [])

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")

                            if user_message:
                                context_messages.append(f"{user_name}: {user_message}")
                            if character_message:
                                context_messages.append(f"{self.character_name}: {character_message}")

                        context_messages = context_messages[-10:]
                        context = "\n".join(context_messages)
                        final_system_prompt = (
                            f"[INST] {system_prompt} [/INST]\n\n"
                            f"Context of dialogue:\n{context}\n\n"
                            f"Information about User:\nName: {user_name},\nDescription: {user_description}\n\n"
                        )

                        final_user_message = f"Current message:\nUser: {user_text}"
                        answer_generator = self.mistral_ai_client.send_message(final_user_message, final_system_prompt, self.character_name, user_name)
                        character_answer_container = await self.add_message("", is_user=False)
                        character_answer_label = character_answer_container["label"]

                        full_text = ""
                        async for message in answer_generator:
                            if message:
                                full_text += message
                                full_text_html = self.markdown_to_html(full_text)
                                character_answer_label.setText(full_text_html)
                                await asyncio.sleep(0.05)
                                match current_sow_system_mode:
                                    case "Nothing":
                                        self.ui.scrollArea_chat_page1.verticalScrollBar().setValue(self.ui.scrollArea_chat_page1.verticalScrollBar().maximum())
                                    case "Expressions Images":
                                        self.ui.scrollArea_chat_page2.verticalScrollBar().setValue(self.ui.scrollArea_chat_page2.verticalScrollBar().maximum())
                                    case "Live2D Model":
                                        self.ui.scrollArea_chat_page3.verticalScrollBar().setValue(self.ui.scrollArea_chat_page3.verticalScrollBar().maximum())

                        if full_text_html.startswith(f"{self.character_name}:"):
                            full_text_html = full_text_html[len(f"{self.character_name}:"):].lstrip()

                        full_text_html = (full_text_html.replace("{{user}}", user_name)
                        .replace("{{char}}", self.character_name)
                        .replace("{{User}}", user_name)
                        .replace("{{Char}}", self.character_name)
                        .replace("{{пользователь}}", user_name)
                        .replace("{{персонаж}}", self.character_name)
                        .replace("{{шар}}", self.character_name)
                        .replace("{{символ}}", self.character_name)
                        )
                        
                        character_answer_label.setText(full_text_html)

                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, full_text))

                        self.configuration_characters.add_message_to_chat_content(self.character_name, "User", True, user_text)
                        self.configuration_characters.add_message_to_chat_content(self.character_name, self.character_name, False, full_text)

                        await asyncio.sleep(0.5)

                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

                    case "Local LLM":
                        configuration_data = self.configuration_characters.load_configuration()
                        character_data = configuration_data["character_list"].get(self.character_name)
                        system_prompt = character_data["system_prompt"]
                        chat_history = character_data.get("chat_history", [])

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")
                            if user_message:
                                context_messages.append(f"<start_of_turn>user\n{user_name}: {user_message}</start_of_turn>")
                            if character_message:
                                context_messages.append(f"<start_of_turn>model\n{self.character_name}: {character_message}</start_of_turn>")

                        context_messages = context_messages[-20:]
                        context = "\n".join(context_messages)

                        character_answer_container = await self.add_message("", is_user=False)
                        character_answer_label = character_answer_container["label"]

                        full_text = ""
                        full_text_html = ""
                        async for chunk in self.local_ai_client.send_message(system_prompt, context, user_text, self.character_name, user_name):
                            if chunk:
                                full_text += chunk
                                full_text_html = self.markdown_to_html(full_text)
                                character_answer_label.setText(full_text_html)
                                await asyncio.sleep(0.05)
                                match current_sow_system_mode:
                                    case "Nothing":
                                        self.ui.scrollArea_chat_page1.verticalScrollBar().setValue(self.ui.scrollArea_chat_page1.verticalScrollBar().maximum())
                                    case "Expressions Images":
                                        self.ui.scrollArea_chat_page2.verticalScrollBar().setValue(self.ui.scrollArea_chat_page2.verticalScrollBar().maximum())
                                    case "Live2D Model":
                                        self.ui.scrollArea_chat_page3.verticalScrollBar().setValue(self.ui.scrollArea_chat_page3.verticalScrollBar().maximum())

                        if full_text_html.startswith(f"{self.character_name}:"):
                            full_text_html = full_text_html[len(f"{self.character_name}:"):].lstrip()

                        full_text_html = (full_text_html.replace("{{user}}", user_name)
                                          .replace("{{char}}", self.character_name)
                                          .replace("{{User}}", user_name)
                                          .replace("{{Char}}", self.character_name)
                                          .replace("{{пользователь}}", user_name)
                                          .replace("{{персонаж}}", self.character_name)
                                          .replace("{{шар}}", self.character_name)
                                          .replace("{{символ}}", self.character_name)
                        )

                        character_answer_label.setText(full_text_html)
                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, full_text))

                        self.configuration_characters.add_message_to_chat_content(self.character_name, "User", True, user_text)
                        self.configuration_characters.add_message_to_chat_content(self.character_name, self.character_name, False, full_text)

                        await asyncio.sleep(0.5)

                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru').replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru').replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru").replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru").replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translate
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru").replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru").replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

        except Exception as e:
            error_message = traceback.format_exc()
            print(f"Full error: {error_message}")
    
    async def speech_to_speech_no_gui(self):
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]
        current_sow_system_mode = character_information["current_sow_system_mode"]
        current_text_to_speech = character_information["current_text_to_speech"]
        first_message = character_information["first_message"]
        current_emotion = character_information["current_emotion"]

        try:
            user_name = self.configuration_settings.get_user_data("user_name")
            user_description = self.configuration_settings.get_user_data("user_description")
            
            match self.speech_to_text_method:
                case 0: # Google STT English
                    user_text_original = await self.speech_to_text.speech_recognition_google()
                case 1: # Google STT Russian
                    user_text_original = await self.speech_to_text.speech_recognition_google()
                case 2: # Vosk English
                    user_text_original = await self.speech_to_text.speech_recognition_vosk()
                case 3: # Vosk Russian
                    user_text_original = await self.speech_to_text.speech_recognition_vosk()
                case 4: # Local Whisper
                    user_text_original = await self.speech_to_text.speech_recognition_whisper()
            
            user_text = user_text_original

            match self.current_translator:
                case 0:
                    pass
                case 1:
                    # Google Translate
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", 'en')
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 2:
                    # Yandex Translate
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", 'en')
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 3:
                    # Local MarianMT Translate
                    match self.translator_mode:
                        case 0:
                            if self.target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 1:
                            if self.target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 2:
                            pass

            if user_text:
                match self.current_conversation_method:
                    case "Character AI":
                        full_text = ""
                        turn_id = ""
                        candidate_id = ""

                        async for message in self.character_ai_client.send_message(self.character_id, self.chat_id, user_text):
                            text = message.get_primary_candidate().text
                            turn_id = message.turn_id
                            candidate_id = message.get_primary_candidate().candidate_id
                            if text != full_text:
                                full_text = text
                                
                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, full_text))

                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "Character AI":
                                await asyncio.sleep(0.05)
                                await self.character_ai_client.generate_speech(self.chat_id, turn_id, candidate_id, self.character_ai_voice_id)
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

                        await self.character_ai_client.fetch_chat(
                                    self.chat_id, self.character_name, self.character_id, self.character_avatar_url, self.character_title,
                                    self.character_description, self.character_personality, first_message, current_text_to_speech,
                                    self.voice_name, self.character_ai_voice_id, self.elevenlabs_voice_id, self.xttsv2_voice_type, self.xttsv2_rvc_enabled,
                                    self.xttsv2_rvc_file, current_sow_system_mode, self.expression_images_folder, self.live2d_model_folder,
                                    self.current_conversation_method, current_emotion
                                )

                    case "Mistral AI":
                        configuration_data = self.configuration_characters.load_configuration()
                        character_data = configuration_data["character_list"].get(self.character_name)
                        system_prompt = character_data["system_prompt"]
                        chat_history = character_data.get("chat_history", [])

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")

                            if user_message:
                                context_messages.append(f"{user_name}: {user_message}")
                            if character_message:
                                context_messages.append(f"{self.character_name}: {character_message}")

                        context_messages = context_messages[-10:]
                        context = "\n".join(context_messages)
                        final_system_prompt = (
                            f"[INST] {system_prompt} [/INST]\n\n"
                            f"Context of dialogue:\n{context}\n\n"
                            f"Information about User:\nName: {user_name},\nDescription: {user_description}\n\n"
                        )

                        final_user_message = f"Current message:\nUser: {user_text}"
                        answer_generator = self.mistral_ai_client.send_message(final_user_message, final_system_prompt, self.character_name, user_name)
                        full_text = ""
                        async for message in answer_generator:
                            if message:
                                full_text += message
                                await asyncio.sleep(0.05)

                        if full_text_html.startswith(f"{self.character_name}:"):
                            full_text_html = full_text_html[len(f"{self.character_name}:"):].lstrip()

                        full_text_html = full_text_html.replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)

                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, full_text))

                        self.configuration_characters.add_message_to_chat_content(self.character_name, "User", True, user_text)
                        self.configuration_characters.add_message_to_chat_content(self.character_name, self.character_name, False, full_text)
                        await asyncio.sleep(0.5)
                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

                    case "Local LLM":
                        configuration_data = self.configuration_characters.load_configuration()
                        character_data = configuration_data["character_list"].get(self.character_name)
                        system_prompt = character_data["system_prompt"]
                        chat_history = character_data.get("chat_history", [])

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")

                            if user_message:
                                context_messages.append(f"<start_of_turn>user\n{user_name}: {user_message}</start_of_turn>")

                            if character_message:
                                context_messages.append(f"<start_of_turn>model\n{self.character_name}: {character_message}</start_of_turn>")

                        context_messages = context_messages[-20:]
                        context = "\n".join(context_messages)

                        full_text = ""
                        full_text_html = ""
                        async for chunk in self.local_ai_client.send_message(system_prompt, context, user_text, self.character_name, user_name):
                            if chunk:
                                full_text += chunk
                                await asyncio.sleep(0.05)

                        if full_text_html.startswith(f"{self.character_name}:"):
                            full_text_html = full_text_html[len(f"{self.character_name}:"):].lstrip()

                        full_text_html = full_text_html.replace("{{user}}", user_name).replace("{{char}}", self.character_name).replace("{{User}}", user_name).replace("{{Char}}", self.character_name).replace("{{пользователь}}", user_name).replace("{{персонаж}}", self.character_name).replace("{{шар}}", self.character_name).replace("{{символ}}", self.character_name)

                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model":
                                asyncio.create_task(self.detect_emotion(self.character_name, full_text))

                        self.configuration_characters.add_message_to_chat_content(self.character_name, "User", True, user_text)
                        self.configuration_characters.add_message_to_chat_content(self.character_name, self.character_name, False, full_text)

                        await asyncio.sleep(0.5)

                        match self.current_translator:
                            case 0:
                                pass
                            case 1:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match self.translator_mode:
                                    case 0:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if self.target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                        else:
                                            pass

                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text, self.elevenlabs_voice_id)
                            case "XTTSv2":
                                if self.current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=self.character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=self.character_name)

        except Exception as e:
            error_message = traceback.format_exc()
            print(f"Full error: {error_message}")
    
    async def detect_emotion(self, character_name, text):
        """
        Detects emotion based on the input text and updates the character's expression (image or Live2D model).
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]

        expression_images_folder = character_information["expression_images_folder"]
        live2d_model_folder = character_information["live2d_model_folder"]
        current_sow_system_mode = character_information["current_sow_system_mode"]

        if current_sow_system_mode == "Nothing":
            return

        if self.tokenizer is None or self.session is None:
            self.tokenizer = AutoTokenizer.from_pretrained("Cohee/distilbert-base-uncased-go-emotions-onnx")
            model_path = "resources/data/emotions/detector.onnx"
            self.session = ort.InferenceSession(model_path)
        inputs = self.tokenizer(text, return_tensors="np", truncation=True, padding=True)
        input_feed = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
        }
        outputs = self.session.run(None, input_feed)
        logits = outputs[0]
        predicted_class_id = np.argmax(logits, axis=1).item()
        emotions = [
            "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity",
            "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear",
            "gratitude", "grief", "love", "nervousness", "neutral", "optimism", "pride", "realization",
            "relief", "remorse", "surprise", "joy", "sadness"
        ]
        emotion = emotions[predicted_class_id]

        if current_sow_system_mode == "Expressions Images":
            image_path = self.emotion_resources[emotion]["image"]
            await self.show_emotion_image(expression_images_folder, image_path)
        elif current_sow_system_mode == "Live2D Model":
            model_json_path = self.find_model_json(live2d_model_folder)
            if model_json_path:
                self.update_model_json(model_json_path, self.emotion_resources)
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["current_emotion"] = emotion
                self.configuration_characters.save_configuration_edit(configuration_data)

    def find_model_json(self, live2d_model_folder):
        for root, dirs, files in os.walk(live2d_model_folder):
            for file in files:
                if file.endswith(".model3.json"):
                    return os.path.join(root, file)
        return None

    def update_model_json(self, model_json_path, emotion_resources):
        emotions_path = "../../../../resources/data/emotions"
        
        with open(model_json_path, "r", encoding="utf-8") as file:
            model_data = json.load(file)

        file_references = model_data.get("FileReferences", {})
        if "Expressions" not in file_references:
            file_references["Expressions"] = []

        expressions = file_references["Expressions"]

        existing_expressions = {expr["Name"] for expr in expressions}

        for emotion in emotion_resources.keys():
            if emotion not in existing_expressions:
                expressions.append({
                    "Name": emotion,
                    "File": f"{emotions_path}/{emotion}_animation.exp3.json"
                })

        file_references["Expressions"] = expressions
        model_data["FileReferences"] = file_references

        with open(model_json_path, "w", encoding="utf-8") as file:
            json.dump(model_data, file, indent=4, ensure_ascii=False)

    async def show_emotion_image(self, expression_images_folder, image_name):
        """
        Shows an image or GIF
        """
        if self.ui.image_label is not None:
            gif_path = os.path.join(expression_images_folder, f"{image_name}.gif")
            if os.path.exists(gif_path):
                movie = QtGui.QMovie(gif_path)
                self.ui.image_label.setMovie(movie)
                movie.setScaledSize(self.ui.image_label.size())
                movie.start()
            else:
                png_path = os.path.join(expression_images_folder, f"{image_name}.png")
                if os.path.exists(png_path):
                    pixmap = QPixmap(png_path)
                    scaled_pixmap = pixmap.scaled(
                        530, 
                        530,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.ui.image_label.setPixmap(scaled_pixmap)
                else:
                    print(f"{image_name} not found.")

    async def initialize_live2d_no_gui(self):
        """
        Initializes the Live2D model without a GUI.
        """
        character_data = self.configuration_characters.load_configuration()
        live2d_model_folder = character_data["character_list"][self.character_name]["live2d_model_folder"]
        model_json_path = self.find_model_json(live2d_model_folder)
        if model_json_path:
            self.update_model_json(model_json_path, self.emotion_resources)
            self.live2d_no_gui_task = asyncio.create_task(self.speech_to_speech_loop_no_gui())
            await asyncio.sleep(0.5)
            self.live2d_no_gui = Live2DWidget_NoGUI(parent=self.parent_window, model_path=model_json_path, character_name=self.character_name, running_live2d_no_gui=self.running_live2d_no_gui, live2d_no_gui_task=self.live2d_no_gui_task)
            self.live2d_no_gui.show()
            
        else:
            print("Model not found.")

    async def open_soul_of_waifu_system(self):
        self.parent_window.hide()
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]
        
        current_emotion = character_information.get("current_emotion")
        if not current_emotion:
            character_information["current_emotion"] = "neutral"
            character_data["character_list"][self.character_name]["current_emotion"] = "neutral"
            self.configuration_characters.save_configuration_edit(character_data)
        
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][self.character_name]
        current_emotion = character_information["current_emotion"]
        
        current_sow_system_mode = character_information["current_sow_system_mode"]
        current_conversation_method = character_information["conversation_method"]
        character_avatar = character_information["character_avatar"]
        first_message = character_information["first_message"]
        chat_content = character_information["chat_content"]
        
        if self.live2d_mode == 0:
            self.ui.show()
            match current_conversation_method:
                case "Character AI":
                    character_id = character_information["character_id"]
                    chat_id = character_information["chat_id"]
                    character_title = character_information["character_title"]
                    character_description = character_information["character_description"]
                    character_personality = character_information["character_personality"]

                    voice_name = character_information["voice_name"]
                    character_ai_voice_id = character_information["character_ai_voice_id"]
                    elevenlabs_voice_id = character_information["elevenlabs_voice_id"]
                    xttsv2_voice_type = character_information["xttsv2_voice_type"]
                    xttsv2_rvc_enabled = character_information["xttsv2_rvc_enabled"]
                    xttsv2_rvc_file = character_information["xttsv2_rvc_file"]
                    

                    expression_images_folder = character_information["expression_images_folder"]
                    live2d_model_folder = character_information["live2d_model_folder"]
                    current_text_to_speech = character_information["current_text_to_speech"]

                    await self.character_ai_client.fetch_chat(
                                chat_id, self.character_name, character_id, character_avatar, character_title,
                                character_description, character_personality, first_message, current_text_to_speech,
                                voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled,
                                xttsv2_rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                                current_conversation_method, current_emotion
                            )
                    
                    chat_content = character_data["character_list"][self.character_name].get("chat_content", {})
                    await asyncio.sleep(0.05)
                    
                    for message_id, message_data in chat_content.items():
                        text = message_data["text"]
                        is_user = message_data["is_user"]

                        if self.current_translator != 0:
                            if self.current_translator == 1:  # Google Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "google", "ru")
                            elif self.current_translator == 2:  # Yandex Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "yandex", "ru")
                            elif self.current_translator == 3:  # MarianMT (локальный переводчик)
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate_local(text, "en", "ru")

                        asyncio.create_task(
                            self.add_message(text, is_user, int(message_id))
                        )
                    
                    character_avatar = self.character_ai_client.get_from_cache(character_avatar)
                    match current_sow_system_mode:
                        case "Nothing":
                            pixmap = QPixmap(character_avatar)
                            self.ui.avatar_label.setPixmap(pixmap)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page1)
                            self.ui.character_name_page1.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page1.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page1.clicked.connect(self.toggleStartStopAvatar)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(0)
                        
                        case "Expressions Images":
                            image_name = "neutral"
                            await self.show_emotion_image(expression_images_folder, image_name)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page2)
                            self.ui.character_name_page2.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page2.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page2.clicked.connect(self.toggleStartStopImage)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(1)
                        
                        case "Live2D Model":
                            model_json_path = self.find_model_json(live2d_model_folder)
                            if model_json_path:
                                self.update_model_json(model_json_path, self.emotion_resources)
                            else:
                                print("Model not found.")
                            
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page3)
                            self.ui.character_name_page3.setText(self.character_name)
                            
                            await asyncio.sleep(0.5)
                            self.live2d_expression_widget = QtWidgets.QWidget(self.ui.frame_main_live2d)
                            self.live2d_expression_widget.setStyleSheet("background-color: rgb(23,23,23); border: 2px solid rgb(42,42,42);")
                            live2d_layout = QtWidgets.QVBoxLayout(self.live2d_expression_widget)
                            live2d_layout.setContentsMargins(0, 0, 0, 0)
                            self.live2d_widget_page3 = Live2DWidget(model_path=model_json_path, character_name=self.character_name)
                            self.live2d_widget_page3.setStyleSheet("background-color: transparent;")
                            live2d_layout.addWidget(self.live2d_widget_page3)
                            self.ui.main_layout3.addWidget(self.live2d_expression_widget, 3)
                            
                            try:
                                self.ui.pushButton_start_page3.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page3.clicked.connect(self.toggleStartStopLive2D)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(2)
                
                case "Mistral AI":
                    expression_images_folder = character_information["expression_images_folder"]
                    live2d_model_folder = character_information["live2d_model_folder"]
                    current_text_to_speech = character_information["current_text_to_speech"]
                    chat_content = character_data["character_list"][self.character_name].get("chat_content", {})
                    await asyncio.sleep(0.05)
                    
                    for message_id, message_data in chat_content.items():
                        text = message_data["text"]
                        is_user = message_data["is_user"]

                        if self.current_translator != 0:
                            if self.current_translator == 1:  # Google Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "google", "ru")
                            elif self.current_translator == 2:  # Yandex Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "yandex", "ru")
                            elif self.current_translator == 3:  # MarianMT (локальный переводчик)
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate_local(text, "en", "ru")

                        asyncio.create_task(
                            self.add_message(text, is_user, int(message_id))
                        )

                    match current_sow_system_mode:
                        case "Nothing":
                            pixmap = QPixmap(character_avatar)
                            self.ui.avatar_label.setPixmap(pixmap)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page1)
                            self.ui.character_name_page1.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page1.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page1.clicked.connect(self.toggleStartStopAvatar)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(0)
                        
                        case "Expressions Images":
                            image_name = "neutral"
                            await self.show_emotion_image(expression_images_folder, image_name)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page2)
                            self.ui.character_name_page2.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page2.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page2.clicked.connect(self.toggleStartStopImage)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(1)
                        
                        case "Live2D Model":
                            model_json_path = self.find_model_json(live2d_model_folder)
                            if model_json_path:
                                self.update_model_json(model_json_path, self.emotion_resources)
                            else:
                                print("Model not found.")
                            
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page3)
                            self.ui.character_name_page3.setText(self.character_name)
                            
                            await asyncio.sleep(0.5)
                            self.live2d_expression_widget = QtWidgets.QWidget(self.ui.frame_main_live2d)
                            self.live2d_expression_widget.setStyleSheet("background-color: rgb(23,23,23); border: 2px solid rgb(42,42,42);")
                            live2d_layout = QtWidgets.QVBoxLayout(self.live2d_expression_widget)
                            live2d_layout.setContentsMargins(0, 0, 0, 0)
                            self.live2d_widget_page3 = Live2DWidget(model_path=model_json_path, character_name=self.character_name)
                            self.live2d_widget_page3.setStyleSheet("background-color: transparent;")
                            live2d_layout.addWidget(self.live2d_widget_page3)
                            self.ui.main_layout3.addWidget(self.live2d_expression_widget, 3)
                            
                            try:
                                self.ui.pushButton_start_page3.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page3.clicked.connect(self.toggleStartStopLive2D)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(2)
                
                case "Local LLM":
                    expression_images_folder = character_information["expression_images_folder"]
                    live2d_model_folder = character_information["live2d_model_folder"]
                    current_text_to_speech = character_information["current_text_to_speech"]
                    chat_content = character_data["character_list"][self.character_name].get("chat_content", {})
                    await asyncio.sleep(0.05)

                    for message_id, message_data in chat_content.items():
                        text = message_data["text"]
                        is_user = message_data["is_user"]

                        if self.current_translator != 0:
                            if self.current_translator == 1:  # Google Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "google", "ru")
                            elif self.current_translator == 2:  # Yandex Translate
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate(text, "yandex", "ru")
                            elif self.current_translator == 3:  # MarianMT (локальный переводчик)
                                if self.translator_mode == 0 or self.translator_mode == 2:
                                    if self.target_language == 0:
                                        if not is_user or (self.translator_mode == 0):
                                            text = self.translator.translate_local(text, "en", "ru")

                        asyncio.create_task(
                            self.add_message(text, is_user, int(message_id))
                        )

                    match current_sow_system_mode:
                        case "Nothing":
                            pixmap = QPixmap(character_avatar)
                            self.ui.avatar_label.setPixmap(pixmap)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page1)
                            self.ui.character_name_page1.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page1.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page1.clicked.connect(self.toggleStartStopAvatar)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(0)
                        
                        case "Expressions Images":
                            image_name = "neutral"
                            await self.show_emotion_image(expression_images_folder, image_name)
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page2)
                            self.ui.character_name_page2.setText(self.character_name)
                            
                            try:
                                self.ui.pushButton_start_page2.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page2.clicked.connect(self.toggleStartStopImage)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(1)
                        
                        case "Live2D Model":
                            model_json_path = self.find_model_json(live2d_model_folder)
                            if model_json_path:
                                self.update_model_json(model_json_path, self.emotion_resources)
                            else:
                                print("[detect_emotion] Файл модели не найден.")
                            
                            self.draw_circle_avatar(character_avatar, self.ui.character_avatar_label_page3)
                            self.ui.character_name_page3.setText(self.character_name)
                            
                            await asyncio.sleep(0.5)
                            self.live2d_expression_widget = QtWidgets.QWidget(self.ui.frame_main_live2d)
                            self.live2d_expression_widget.setStyleSheet("background-color: rgb(23,23,23); border: 2px solid rgb(42,42,42);")
                            live2d_layout = QtWidgets.QVBoxLayout(self.live2d_expression_widget)
                            live2d_layout.setContentsMargins(0, 0, 0, 0)
                            self.live2d_widget_page3 = Live2DWidget(model_path=model_json_path, character_name=self.character_name)
                            self.live2d_widget_page3.setStyleSheet("background-color: transparent;")
                            live2d_layout.addWidget(self.live2d_widget_page3)
                            self.ui.main_layout3.addWidget(self.live2d_expression_widget, 3)
                            
                            try:
                                self.ui.pushButton_start_page3.clicked.disconnect()
                            except TypeError:
                                pass
                            
                            self.ui.pushButton_start_page3.clicked.connect(self.toggleStartStopLive2D)
                            self.ui.stackedWidget_sow_system.setCurrentIndex(2)
        else:
            await self.initialize_live2d_no_gui()

class Live2DWidget(QOpenGLWidget):
    """
    Initializes the Live2DWidget for rendering Live2D models.
    """
    def __init__(self, parent=None, model_path=None, character_name=None):
        super().__init__(parent)
        
        # Validate input parameters
        if model_path is None:
            raise ValueError("model_path must be provided")
        
        # Initialize configuration and settings
        self.configuration_characters = configuration.ConfigurationCharacters()
        self.configuration_settings = configuration.ConfigurationSettings()

        # Store model path and character name
        self.model_path = model_path
        self.character_name = character_name

        print("[Live2DWidget] Initializing Live2D...")
        live2d.init()
        print("[Live2DWidget] Live2D initialized.")
        
        # Initialize model-related attributes
        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.read = False
        self.timerId = None
        
        # Set widget attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        print("[Live2DWidget] Widget initialized.")
        
    def initializeGL(self) -> None:
        """
        Initializes OpenGL and loads the Live2D model.
        """
        if self.opengl_initialized:
            print("[Live2DWidget] OpenGL already initialized, skipping initialization.")
            return
        
        print("[Live2DWidget] Initializing OpenGL...")
        try:
            self.makeCurrent()
        except Exception as e:
            print(f"[Live2DWidget] Error activating OpenGL context: {e}")
            return
        
        if live2d.LIVE2D_VERSION == 3:
            print("[Live2DWidget] Initializing GLEW...")
            try:
                live2d.glewInit()
                print("[Live2DWidget] GLEW successfully initialized.")
            except Exception as e:
                print(f"[Live2DWidget] Error initializing GLEW: {e}")
                return
        
        print("[Live2DWidget] OpenGL инициализирован.")
        self.opengl_initialized = True
        
        # Load the Live2D model if not already loaded
        if not self.live2d_model_loaded:
            print(f"[Live2DWidget] Loading model from {self.model_path}...")
            try:
                self.live2d_model = live2d.LAppModel()
                self.live2d_model.SetAutoBreathEnable(True)
                self.live2d_model.SetAutoBlinkEnable(True)
                
                self.live2d_model.LoadModelJson(self.model_path)
                self.live2d_model_loaded = True
                print("[Live2DWidget] Model successfully loaded.")
            except Exception as e:
                print(f"[Live2DWidget] Error loading model: {e}")
                return

            print("[Live2DWidget] Starting the cycle...")
            try:
                self.timerId = self.startTimer(int(1000 / 60))
                print("[Live2DWidget] Timer started.")
            except Exception as e:
                print(f"[Live2DWidget] Error starting timer: {e}")
                return

    def resizeGL(self, w: int, h: int) -> None:
        """
        Handles resizing of the OpenGL viewport.

        Args:
            w (int): New width of the widget.
            h (int): New height of the widget.
        """
        if self.live2d_model:
            try:
                self.live2d_model.Resize(w, h)
                print("[Win] Model size updated.")
            except Exception as e:
                print(f"[Win] Error resizing model: {e}")
    
    def paintGL(self) -> None:
        """
        Renders the Live2D model and saves a screenshot on the first frame.
        """
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        if self.live2d_model:
            self.live2d_model.Update()
            self.live2d_model.Draw()

        if not self.read:
            print("[Live2DWidget] Saving screenshot...")
            self.savePng('cache\\screenshot_call.png')
            self.read = True

    def savePng(self, fName):
        """
        Saves the current frame as a PNG image.

        Args:
            fName (str): File name to save the screenshot as.
        """
        if self.width() <= 0 or self.height() <= 0:
            print(f"[Live2DWidget] Error: Invalid widget dimensions: {self.width()}x{self.height()}")
        
        print(f"Saving frame to {fName}...")
        data = gl.glReadPixels(0, 0, self.width(), self.height(), gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        data = np.frombuffer(data, dtype=np.uint8).reshape(self.height(), self.width(), 4)
        data = np.flipud(data)
        new_data = np.zeros_like(data)
        for rid, row in enumerate(data):
            for cid, col in enumerate(row):
                color = None
                new_data[rid][cid] = col
                if cid > 0 and data[rid][cid - 1][3] == 0 and col[3] != 0:
                    color = new_data[rid][cid - 1]
                elif cid > 0 and data[rid][cid - 1][3] != 0 and col[3] == 0:
                    color = new_data[rid][cid]
                if color is not None:
                    color[0] = 255
                    color[1] = 0
                    color[2] = 0
                    color[3] = 255
                color = None
                if rid > 0:
                    if data[rid - 1][cid][3] == 0 and col[3] != 0:
                        color = new_data[rid - 1][cid]
                    elif data[rid - 1][cid][3] != 0 and col[3] == 0:
                        color = new_data[rid][cid]
                elif col[3] != 0:
                    color = new_data[rid][cid]
                if color is not None:
                    color[0] = 255
                    color[1] = 0
                    color[2] = 0
                    color[3] = 255
        img = Image.fromarray(new_data, 'RGBA')
        img.save(fName)
        print("Frame saved.")

    def timerEvent(self, a0: QTimerEvent | None):
        """
        Updates the Live2D model and triggers a repaint.
        """
        self.update_live2d_emotion()
        self.update()

    def update_live2d_emotion(self):
        """
        Updates the emotion of the Live2D model based on the current character's emotion.
        """
        if self.live2d_model:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]

            self.current_emotion = character_info.get("current_emotion")
            self.live2d_model.SetExpression(self.current_emotion)
        else:
            print('Emotion not detected')

    def cleanup(self):
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None

        if self.live2d_model:
            try:
                live2d.dispose()
            except Exception as e:
                print(f"[Live2DWidget] Error releasing Live2D: {e}")
            self.live2d_model = None
        
        # Деактивация текущего контекста OpenGL
        if self.opengl_initialized:
            print("[Live2DWidget] Deactivating OpenGL context...")
            try:
                self.doneCurrent()
            except Exception as e:
                print(f"[Live2DWidget] Error deactivating OpenGL context: {e}")

        self.live2d_model_loaded = False
        self.opengl_initialized = False
        print("[Live2DWidget] All resources released.")

    def hideEvent(self, event):
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        self.cleanup()
        super().hideEvent(event)

    def closeEvent(self, event):
        print("[Live2DWidget] Closing widget...")
        self.cleanup()
        super().closeEvent(event)

class Live2DWidget_NoGUI(QOpenGLWidget):
    def __init__(self, parent=None, model_path=None, character_name=None, running_live2d_no_gui=None, live2d_no_gui_task=None):
        super().__init__()
        if model_path is None:
            raise ValueError("model_path must be provided")
        
        self.configuration_characters = configuration.ConfigurationCharacters()
        self.model_path = model_path
        self.character_name = character_name
        self.parent = parent

        print("[Live2DWidget] Initializing Live2D...")
        live2d.init()
        print("[Live2DWidget] Live2D initialized.")

        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.read = False
        self.isInLA = False
        self.clickInLA = False
        self.clickX = -1
        self.clickY = -1
        self.timerId = None
        self.systemScale = QGuiApplication.primaryScreen().devicePixelRatio()

        self.running_live2d_no_gui = running_live2d_no_gui
        self.live2d_no_gui_task = live2d_no_gui_task

        self.resize(500, 500)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        print("[Live2DWidget] Widget initialized.")
        
    def initializeGL(self) -> None:
        if self.opengl_initialized:
            return
        try:
            self.makeCurrent()
        except Exception as e:
            return
        
        if live2d.LIVE2D_VERSION == 3:
            try:
                live2d.glewInit()
            except Exception as e:
                return

        self.opengl_initialized = True
        
        if not self.live2d_model_loaded:
            try:
                self.live2d_model = live2d.LAppModel()
                self.live2d_model.SetAutoBreathEnable(True)
                self.live2d_model.SetAutoBlinkEnable(True)
                
                self.live2d_model.LoadModelJson(self.model_path)
                self.live2d_model_loaded = True
            except Exception as e:
                return
            try:
                self.timerId = self.startTimer(int(1000 / 60))
            except Exception as e:
                return

    def resizeGL(self, w: int, h: int) -> None:
        if self.live2d_model:
            try:
                self.live2d_model.Resize(w, h)
            except Exception as e:
                print(f"[Win] Error resizing model: {e}")

    def paintGL(self) -> None:
        """
        Renders the Live2D model and saves a screenshot on the first frame.
        """
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        if self.live2d_model:
            self.live2d_model.Update()
            self.live2d_model.Draw()

        if not self.read:
            print("[Live2DWidget] Saving screenshot...")
            self.savePng('cache\\screenshot_call.png')
            self.read = True

    def savePng(self, fName):
        """
        Saves the current frame as a PNG image.
        """
        if self.width() <= 0 or self.height() <= 0:
            print(f"[Live2DWidget] Error: Invalid widget dimensions: {self.width()}x{self.height()}")
            return
        
        print(f"Saving frame to {fName}...")
        data = gl.glReadPixels(0, 0, self.width(), self.height(), gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        data = np.frombuffer(data, dtype=np.uint8).reshape(self.height(), self.width(), 4)
        data = np.flipud(data)
        new_data = np.zeros_like(data)
        for rid, row in enumerate(data):
            for cid, col in enumerate(row):
                color = None
                new_data[rid][cid] = col
                if cid > 0 and data[rid][cid - 1][3] == 0 and col[3] != 0:
                    color = new_data[rid][cid - 1]
                elif cid > 0 and data[rid][cid - 1][3] != 0 and col[3] == 0:
                    color = new_data[rid][cid]
                if color is not None:
                    color[0] = 255
                    color[1] = 0
                    color[2] = 0
                    color[3] = 255
                color = None
                if rid > 0:
                    if data[rid - 1][cid][3] == 0 and col[3] != 0:
                        color = new_data[rid - 1][cid]
                    elif data[rid - 1][cid][3] != 0 and col[3] == 0:
                        color = new_data[rid][cid]
                elif col[3] != 0:
                    color = new_data[rid][cid]
                if color is not None:
                    color[0] = 255
                    color[1] = 0
                    color[2] = 0
                    color[3] = 255
        img = Image.fromarray(new_data, 'RGBA')
        img.save(fName)
        print("Frame saved.")

    def timerEvent(self, a0: QTimerEvent | None):
        """
        Updates the Live2D model and triggers a repaint.
        """
        self.update_live2d_emotion()
        
        local_x, local_y = QCursor.pos().x() - self.x(), QCursor.pos().y() - self.y()
        if self.isInL2DArea(local_x, local_y):
            self.isInLA = True
        else:
            self.isInLA = False

        self.update()

    def cleanup(self):
        """
        Cleans up resources used by the Live2D model and OpenGL context.
        """
        print("[Live2DWidget] Releasing model resources...")
        if self.timerId is not None:
            print("[Live2DWidget] Stopping timer...")
            self.killTimer(self.timerId)
            self.timerId = None

        if self.live2d_model:
            print("[Live2DWidget] Releasing Live2D model...")
            try:
                live2d.dispose()
            except Exception as e:
                print(f"[Live2DWidget] Error releasing Live2D: {e}")
            self.live2d_model = None

        if self.opengl_initialized:
            print("[Live2DWidget] Deactivating OpenGL context...")
            try:
                self.doneCurrent()
            except Exception as e:
                print(f"[Live2DWidget] Error deactivating OpenGL context: {e}")

        self.live2d_model_loaded = False
        self.opengl_initialized = False
        print("[Live2DWidget] All resources released.")

    def hideEvent(self, event):
        print("[Live2DWidget] Widget hidden, stopping timer and releasing resources.")
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        self.cleanup()
        super().hideEvent(event)

    def stop_live2d_no_gui_tasks(self):
        self.running_live2d_no_gui = False

        if hasattr(self, "live2d_no_gui_task") and self.live2d_no_gui_task:
            self.live2d_no_gui_task.cancel()
            self.live2d_no_gui_task = None

    def closeEvent(self, event):
        self.cleanup()
        self.stop_live2d_no_gui_tasks()
        if self.parent:
            self.parent.show()
        super().closeEvent(event)

    def isInL2DArea(self, click_x, click_y):
        h = self.height()
        alpha = gl.glReadPixels(click_x * self.systemScale, (h - click_y) * self.systemScale, 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)[3]
        return alpha > 0

    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = event.scenePosition().x(), event.scenePosition().y()
        if self.isInL2DArea(x, y):
            self.clickInLA = True
            self.clickX, self.clickY = x, y

    def mouseReleaseEvent(self, event):
        x, y = event.scenePosition().x(), event.scenePosition().y()
        if self.isInLA:
            self.clickInLA = False

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        x, y = event.scenePosition().x(), event.scenePosition().y()
        if self.clickInLA:
            self.move(int(self.x() + x - self.clickX), int(self.y() + y - self.clickY))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        new_width = self.width()
        new_height = self.height()

        if delta > 0:
            new_width += 10
            new_height += 10
        elif delta < 0:
            new_width -= 10
            new_height -= 10

        new_width = max(100, min(new_width, 1000))
        new_height = max(100, min(new_height, 1000))

        self.resize(new_width, new_height)

        if self.live2d_model:
            self.live2d_model.Resize(new_width, new_height)

    def update_live2d_emotion(self):
        if self.live2d_model:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]
            
            self.current_emotion = character_info.get("current_emotion")
            self.live2d_model.SetExpression(self.current_emotion)
        else:
            print('Emotion not detected')