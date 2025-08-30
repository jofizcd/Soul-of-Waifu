import re
import os
import json
import yaml
import uuid
import torch
import asyncio
import logging
import threading
import traceback
import OpenGL.GL as gl
import live2d.v3 as live2d

from socketserver import TCPServer
from http.server import SimpleHTTPRequestHandler
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimerEvent, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont, QPainter, QCursor, QGuiApplication, QColor
from PyQt6.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QFrame
from PyQt6.QtWidgets import (
    QApplication, QLabel, QMessageBox,
    QWidget, QHBoxLayout, QVBoxLayout,
    QGraphicsDropShadowEffect, QFrame
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from app.gui.sowSystem import SOW_System
from app.configuration import configuration
from app.utils.ai_clients.local_ai_client import LocalAI
from app.utils.ai_clients.mistral_ai_client import MistralAI
from app.utils.ai_clients.openai_client import OpenAI
from app.utils.ai_clients.character_ai_client import CharacterAI
from app.utils.translator import Translator
from app.utils.text_to_speech import ElevenLabs, XTTSv2_SOW_System, EdgeTTS, KokoroTTS_SOW_System
from app.utils.speech_to_text import Speech_To_Text

logger = logging.getLogger("SOW System Interface Signals")

class Soul_Of_Waifu_System():
    def __init__(self, parent, character_name):
        """
        Initializes the Soul of Waifu System for a specific character.
        """
        super(Soul_Of_Waifu_System, self).__init__()

        self.ui = SOW_System(parent=None)
        self.ui.setupUi()
        self.character_name = character_name
        self.parent_window = parent
        
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
        
        self.running_avatar = False
        self.running_image = False
        self.running_live2d = False
        self.running_vrm = False
        self.running_live2d_no_gui = False
        self.running_vrm_no_gui = False
        self.stt_worker = None
        
        self.avatar_task = None
        self.image_task = None
        self.live2d_task = None
        self.vrm_task = None
        self.live2d_no_gui_task = None
        self.vrm_no_gui_task = None

        # Initialize AI clients and other utilities
        self.character_ai_client = CharacterAI()
        self.mistral_ai_client = MistralAI()
        self.open_ai_client = OpenAI()
        self.local_ai_client = LocalAI()
        
        self.eleven_labs_client = ElevenLabs()
        self.xttsv2_client = XTTSv2_SOW_System()
        self.edge_tts_client = EdgeTTS()
        self.kokoro_client = KokoroTTS_SOW_System()

        self.translator = Translator()
        self.speech_to_text = Speech_To_Text()
        self.tokenizer = None
        self.session = None

        self.live2d_no_gui = None
        self.live2d_expression_widget = None
        self.vrm_no_gui = None
        self.vrm_expression_widget = None

        self.messages = {}
        self.message_order = []
        
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setSpacing(5)
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background-color: transparent;")
        self.chat_widget.setLayout(self.chat_container)

        self.ui.scrollArea_chat.setWidget(self.chat_widget)

        # --- General settings ---
        self.model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        self.model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        self.model_background_image = self.configuration_settings.get_main_setting("model_background_image")

        self.speech_to_text_method = self.configuration_settings.get_main_setting("stt_method")
        self.live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")
        self.input_device = self.configuration_settings.get_main_setting("input_device")
        self.output_device = self.configuration_settings.get_main_setting("output_device")
        self.current_translator = self.configuration_settings.get_main_setting("translator")
        self.target_language = self.configuration_settings.get_main_setting("target_language")
        self.translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        character_data = self.configuration_characters.load_configuration()
        character_info = character_data["character_list"][character_name]
        self.conversation_method = character_info["conversation_method"]
        self.expression_images_folder = character_info.get("expression_images_folder", None)
        self.live2d_model_folder = character_info.get("live2d_model_folder", None)
        self.vrm_model_file = character_info.get("vrm_model_file", None)
        self.current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        self.character_avatar = character_info.get("character_avatar")
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        if self.conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})

        self.character_title = character_info.get("character_title")
        self.character_description = character_info.get("character_description")
        self.character_personality = character_info.get("character_personality")
        self.first_message = character_info.get("first_message")

        match self.conversation_method:
            case "Character AI":
                self.character_id = character_info.get("character_id")
                self.chat_id = character_info.get("chat_id")
                self.character_avatar_url = character_info.get("character_avatar")
                self.voice_name = character_info.get("voice_name")
                self.character_ai_voice_id = character_info.get("character_ai_voice_id")

                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)

                self.chat_content = character_information.get("chat_content", {})
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)
                current_chat = character_information["current_chat"]
                chats = character_information.get("chats", {})

                self.chat_content = chats[current_chat].get("chat_content", {})

                self.character_avatar = character_info.get("character_avatar")

        self.elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
        self.voice_type = character_info.get("voice_type")
        self.rvc_enabled = character_info.get("rvc_enabled")
        self.rvc_file = character_info.get("rvc_file")

        self.expression_images_folder = character_info.get("expression_images_folder", None)
        self.live2d_model_folder = character_info.get("live2d_model_folder", None)

        emotions_path = "app/utils/emotions/live2d/expressions"
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

        self.icon_play = QtGui.QIcon()
        self.icon_play.addPixmap(QtGui.QPixmap("app/gui/icons/play.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.icon_stop = QtGui.QIcon()
        self.icon_stop.addPixmap(QtGui.QPixmap("app/gui/icons/stop.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)

        self.ui.title_label.setText(self.translations.get("soul_of_waifu_system_title", "Soul of Waifu System"))

    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
    
    async def initialize_sow_system(self, character_name):
        self.parent_window.setVisible(False)
        
        self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))

        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        model_background_image = self.configuration_settings.get_main_setting("model_background_image")

        live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")

        character_data = self.configuration_characters.load_configuration()
        character_info = character_data["character_list"][character_name]
        conversation_method = character_info["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})

            current_emotion = chats[current_chat]["current_emotion"]
            if not current_emotion:
                configuration_data["character_list"][character_name]["chats"][current_chat]["current_emotion"] = "neutral"
                self.configuration_characters.save_configuration_edit(configuration_data)
        else:
            current_emotion = character_info["current_emotion"]
            if not current_emotion:
                configuration_data["character_list"][character_name]["current_emotion"] = "neutral"
                self.configuration_characters.save_configuration_edit(configuration_data)

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        conversation_method = character_info["conversation_method"]
        current_sow_system_mode = character_info["current_sow_system_mode"]
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")

        if conversation_method != "Character AI":
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        match conversation_method:
            case "Character AI":
                character_id = character_info.get("character_id")
                chat_id = character_info.get("chat_id")
                character_avatar_url = character_info.get("character_avatar")
                voice_name = character_info.get("voice_name")
                character_ai_voice_id = character_info.get("character_ai_voice_id")
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
                character_avatar = character_info.get("character_avatar")

        elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
        voice_type = character_info.get("voice_type")
        rvc_enabled = character_info.get("rvc_enabled")
        rvc_file = character_info.get("rvc_file")

        if conversation_method == "Local LLM":
            local_llm = self.configuration_settings.get_main_setting("local_llm")
            if local_llm is None:
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("llm_error_title", "No Local LLM"))
                message_box_information.setText(self.translations.get("llm_error_body", "Choose Local LLM in the options."))
                message_box_information.exec()
                return

        if live2d_mode == 0:
            self.ui.show()

            try:
                personas_data = self.configuration_settings.get_user_data("personas")
                current_persona = character_info.get("selected_persona")
                if current_persona == "None" or current_persona is None:
                    self.user_avatar = "app/gui/icons/person.png"
                else:
                    self.user_avatar = personas_data[current_persona].get("user_avatar", "app/gui/icons/person.png")
            except Exception as e:
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("persona_error_title", "Change persona"))
                message_box_information.setText(self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."))
                message_box_information.exec()
                return

            self.ui.character_name_label.setText(character_name)
            if conversation_method == "Character AI":
                self.ui.character_description_label.setText(character_title)
            else:
                max_words = 3
                if character_title:
                    words = character_title.split()
                    if len(words) > max_words:
                        cropped_description = " ".join(words[:max_words]) + "..."
                        self.ui.character_description_label.setText(cropped_description)
                    else:
                        cropped_description = character_title
                        self.ui.character_description_label.setText(cropped_description)
            
            if current_sow_system_mode == "Nothing":
                if model_background_type == 0:
                    match model_background_color:
                        case 0:
                            background_color = 0x000000
                        case 1:
                            background_color = 0x1A202F
                        case 2:
                            background_color = 0x2C1A22
                        case 3:
                            background_color = 0x222B24
                        case 4:
                            background_color = 0x2E2232
                        case 5:
                            background_color = 0x292929
                        
                    css_background = f"#{background_color:06X}"

                    self.ui.avatar_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.ui.avatar_widget.setStyleSheet(f"""
                        border-image: url({model_background_image}); 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
            elif current_sow_system_mode == "Expressions Images":
                if model_background_type == 0:
                    match model_background_color:
                        case 0:
                            background_color = 0x000000
                        case 1:
                            background_color = 0x1A202F
                        case 2:
                            background_color = 0x2C1A22
                        case 3:
                            background_color = 0x222B24
                        case 4:
                            background_color = 0x2E2232
                        case 5:
                            background_color = 0x292929
                        
                    css_background = f"#{background_color:06X}"

                    self.ui.avatar_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.ui.avatar_widget.setStyleSheet(f"""
                        border-image: url({model_background_image}); 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
            elif current_sow_system_mode == "Live2D Model":
                if model_background_type == 0:
                    match model_background_color:
                        case 0:
                            background_color = 0x000000
                        case 1:
                            background_color = 0x1A202F
                        case 2:
                            background_color = 0x2C1A22
                        case 3:
                            background_color = 0x222B24
                        case 4:
                            background_color = 0x2E2232
                        case 5:
                            background_color = 0x292929
                        
                    css_background = f"#{background_color:06X}"

                    self.ui.live2d_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                        border-top-right-radius: 10px;
                        border-bottom-right-radius: 10px;
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.ui.live2d_widget.setStyleSheet(f"""
                        border-image: url({model_background_image}); 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
            elif current_sow_system_mode == "VRM":
                if model_background_type == 0:
                    match model_background_color:
                        case 0:
                            background_color = 0x000000
                        case 1:
                            background_color = 0x1A202F
                        case 2:
                            background_color = 0x2C1A22
                        case 3:
                            background_color = 0x222B24
                        case 4:
                            background_color = 0x2E2232
                        case 5:
                            background_color = 0x292929
                        
                    css_background = f"#{background_color:06X}"

                    self.ui.vrm_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.ui.vrm_widget.setStyleSheet(f"""
                        border-image: url({model_background_image}); 
                        border-top-right-radius: 10px;
                        border-top-left-radius: 10px;
                        border-bottom-right-radius: 10px;
                        border-bottom-left-radius: 10px;
                    """)

            if current_sow_system_mode == "Live2D Model":
                model_json_path = self.find_model_json(live2d_model_folder)
                self.update_model_json(model_json_path, self.emotion_resources)

                self.live2d_openGL_widget = Live2DWidget(model_path=model_json_path, character_name=character_name)
                self.live2d_openGL_widget.setStyleSheet("background: transparent;")
                self.live2d_openGL_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

                self.ui.verticalLayout_5.addWidget(self.live2d_openGL_widget)

            elif current_sow_system_mode == "VRM":
                class CustomWebEnginePage(QWebEnginePage):
                    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
                        levels = {0: "DEBUG", 1: "LOG", 2: "WARN", 3: "ERROR"}
                        level_name = levels.get(level, f"LEVEL{level}")
                        logger.info(f"[JS Console] {level_name} in {source_id} (line {line_number}): {message}")

                class ServerThread(threading.Thread):
                    def __init__(self, port=8000):
                        super().__init__()
                        self.port = port
                        self.daemon = True
                        self.server = None

                    def run(self):
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                        os.chdir(project_root)
                        
                        handler = SimpleHTTPRequestHandler
                        self.server = TCPServer(("", self.port), handler)
                        self.server.serve_forever()
                    
                    def stop(self):
                        if self.server:
                            self.server.shutdown()
                            self.server.server_close()

                self.vrm_webview = QWebEngineView()
                self.vrm_webview.setStyleSheet("""
                    border-top-right-radius: 10px;
                    border-top-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                    border-bottom-left-radius: 10px;
                """)

                self.vrm_webview.setPage(CustomWebEnginePage(self.vrm_webview))

                self.vrm_webview.settings().setAttribute(
                    self.vrm_webview.settings().WebAttribute.WebGLEnabled, True
                )
                self.vrm_webview.settings().setAttribute(
                    self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True
                )

                if not hasattr(self, 'server_thread') or not self.server_thread.is_alive():
                    self.server_thread = ServerThread(port=8002)
                    self.server_thread.start()

                html_url = f"http://localhost:8002/app/utils/emotions/vrm_module.html"
                
                if vrm_model_file:
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                    model_rel_path = os.path.relpath(vrm_model_file, project_root)
                    safe_path = model_rel_path.replace("\\", "/")
                    html_url += f"?model=/{safe_path}"
                
                def set_background_vrm(bg_type, color=None, image=None):
                    if bg_type == 0:
                        match color:
                            case 0:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x000000)")
                            case 1:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x1A202F)")
                            case 2:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x2C1A22)")
                            case 3:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x222B24)")
                            case 4:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x2E2232)")
                            case 5:
                                self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x292929)")
                    elif bg_type == 1:
                        safe_path = image.replace("\\", "/")
                        imageUrl = f"/{safe_path}"
                        self.vrm_webview.page().runJavaScript(f"setBackground('image', null, '{imageUrl}')")

                def set_expression_vrm(emotion):
                    if emotion in ['anger', 'disapproval', 'annoyance', 'disgust']:
                        self.vrm_webview.page().runJavaScript(f"setExpression('angry')")
                    elif emotion in ['admiration', 'amusement', 'approval', 'desire', 'gratitude', 'love', 'optimism', 'pride', 'joy']:
                        self.vrm_webview.page().runJavaScript(f"setExpression('happy')")
                    elif emotion == 'neutral':
                        self.vrm_webview.page().runJavaScript(f"setExpression('neutral')")
                    elif emotion in ['caring', 'relief']:
                        self.vrm_webview.page().runJavaScript(f"setExpression('relaxed')")
                    elif emotion in ['disappointment', 'grief', 'remorse', 'sadness']:
                        self.vrm_webview.page().runJavaScript(f"setExpression('sad')")
                    elif emotion in ['confusion', 'curiosity', 'embarrassment', 'fear', 'nervousness', 'realization', 'surprise']:
                        self.vrm_webview.page().runJavaScript(f"setExpression('surprised')")

                def play_vrm_animation(emotion):
                    animation_map = {
                        "admiration": "admiration.fbx",
                        "amusement": "amusement.fbx", 
                        "anger": "anger.fbx",
                        "annoyance": "annoyance.fbx",
                        "approval": "approval.fbx",
                        "caring": "caring.fbx",
                        "confusion": "confusion.fbx",
                        "curiosity": "curiosity.fbx",
                        "desire": "desire.fbx",
                        "disappointment": "disappointment.fbx",
                        "disapproval": "disapproval.fbx",
                        "disgust": "disgust.fbx",
                        "embarrassment": "embarrassment.fbx",
                        "excitement": "excitement.fbx",
                        "fear": "fear.fbx",
                        "gratitude": "gratitude.fbx",
                        "grief": "grief.fbx",
                        "love": "love.fbx",
                        "nervousness": "nervousness.fbx",
                        "neutral": "neutral.fbx",
                        "optimism": "optimism.fbx",
                        "pride": "pride.fbx",
                        "realization": "realization.fbx",
                        "relief": "relief.fbx",
                        "remorse": "remorse.fbx",
                        "surprise": "surprise.fbx",
                        "joy": "joy.fbx",
                        "sadness": "sadness.fbx"
                    }

                    anim_file = animation_map.get(emotion, "neutral.fbx")
                    animation_url = f"/app/utils/emotions/vrm/expressions/{anim_file}"
                    
                    self.vrm_webview.page().runJavaScript(f"loadFBX('{animation_url}')")

                self.set_background_vrm = set_background_vrm
                self.set_expression_vrm = set_expression_vrm
                self.play_vrm_animation = play_vrm_animation

                self.vrm_webview.load(QtCore.QUrl(html_url))

                def on_load_finished(ok):
                    if ok:
                        self.vrm_webview.page().runJavaScript(
                            "window.vrmLoaded",
                            lambda is_loaded: on_vrm_loaded(is_loaded)
                        )
                    else:
                        logger.info("Error loading page")

                def on_vrm_loaded(is_loaded):
                    if is_loaded:
                        QtCore.QTimer.singleShot(500, lambda: set_background_vrm(model_background_type, model_background_color, model_background_image))
                        QtCore.QTimer.singleShot(500, lambda: set_expression_vrm(current_emotion))
                        QtCore.QTimer.singleShot(500, lambda: play_vrm_animation(current_emotion))
                    else:
                        QtCore.QTimer.singleShot(1000, lambda: 
                            self.vrm_webview.page().runJavaScript(
                                "window.vrmLoaded",
                                lambda is_loaded: on_vrm_loaded(is_loaded))
                            )

                self.vrm_webview.page().loadFinished.connect(on_load_finished)
                self.ui.verticalLayout_6.addWidget(self.vrm_webview)
            try:
                self.ui.pushButton_play.clicked.disconnect()
            except TypeError:
                pass
            
            if current_sow_system_mode == "Nothing":
                self.ui.pushButton_play.clicked.connect(lambda: self.toggleStartStopAvatar(character_name))
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_avatar)
            if current_sow_system_mode == "Expressions Images":
                await self.show_emotion_image(expression_images_folder, character_name)
                self.ui.pushButton_play.clicked.connect(lambda: self.toggleStartStopImage(character_name))
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_avatar)
            elif current_sow_system_mode == "Live2D Model":
                model_json_path = self.find_model_json(live2d_model_folder)
                self.update_model_json(model_json_path, self.emotion_resources)
                self.ui.pushButton_play.clicked.connect(lambda: self.toggleStartStopLive2D(character_name))
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_live2d_model)
            elif current_sow_system_mode == "VRM":
                self.ui.pushButton_play.clicked.connect(lambda: self.toggleStartStopVRM(character_name))
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_vrm_model)
            
            match conversation_method:
                case "Character AI":
                    await self.character_ai_client.fetch_chat(
                        chat_id, character_name, character_id, character_avatar_url, character_title,
                        character_description, character_personality, first_message, current_text_to_speech,
                        voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                        rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                        vrm_model_file, conversation_method, current_emotion
                    )
                    character_avatar = self.character_ai_client.get_from_cache(character_avatar_url)
                    
                case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
                    pass

            self.draw_circle_avatar(character_avatar, current_sow_system_mode)

            if conversation_method == "Character AI":
                await self.first_render_cai_messages(character_name)
            else:
                await self.first_render_messages(character_name)
            
            QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
                self.ui.scrollArea_chat.verticalScrollBar().maximum()
            ))

        else:
            try:
                personas_data = self.configuration_settings.get_user_data("personas")
                current_persona = character_info.get("selected_persona")
                if current_persona == "None" or current_persona is None:
                    self.user_avatar = "app/gui/icons/person.png"
                else:
                    self.user_avatar = personas_data[current_persona].get("user_avatar", "app/gui/icons/person.png")
            except Exception as e:
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("persona_error_title", "Change persona"))
                message_box_information.setText(self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."))
                message_box_information.exec()
                return
            
            await self.initialize_sow_system_no_gui(current_sow_system_mode)

    async def first_render_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setVisible(False)
        QApplication.processEvents()

        for i in reversed(range(self.chat_container.count())):
            item = self.chat_container.itemAt(i)

            if item.widget() and isinstance(item.widget(), QLabel) and item.widget().pixmap():
                widget = item.widget()
                widget.deleteLater()
                self.chat_container.removeItem(item)
                continue

            if item.layout():
                layout = item.layout()

                for j in reversed(range(layout.count())):
                    inner_item = layout.itemAt(j)
                    if inner_item.widget() and isinstance(inner_item.widget(), QLabel) and inner_item.widget().pixmap():
                        widget = inner_item.widget()
                        layout.removeItem(inner_item)
                        widget.deleteLater()

        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.messages.clear()
        self.message_order.clear()

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        for message_id, msg_data in sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf'))):
            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants", [])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
                
            if translator != 0:
                if translator == 1: # Google Translator
                    if translator_mode in (0, 2):
                        if target_language == 0:
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate(text, "google", "ru")
                elif translator == 2:  # Yandex Translator
                    if translator_mode in (0, 2):  # Translate all messages or only model messages
                        if target_language == 0:  # Target language is Russian
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate(text, "yandex", "ru")
                elif translator == 3:  # MarianMT (local translator)
                    if translator_mode in (0, 2):  # Translate all messages or only model messages
                        if target_language == 0:  # Target language is Russian
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate_local(text, "en", "ru")

            await self.add_message(
                character_name=character_name,
                text=text,
                is_user=is_user,
                message_id=message_id
            )

        self.chat_widget.setUpdatesEnabled(True)
        self.chat_container.update()

        self.ui.scrollArea_chat.setVisible(True)
        self.ui.scrollArea_chat.update()

        QApplication.processEvents()
    
    async def render_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setVisible(False)

        for i in reversed(range(self.chat_container.count())):
            item = self.chat_container.itemAt(i)

            if item.widget() and isinstance(item.widget(), QLabel) and item.widget().pixmap():
                widget = item.widget()
                widget.deleteLater()
                self.chat_container.removeItem(item)
                continue

            if item.layout():
                layout = item.layout()

                for j in reversed(range(layout.count())):
                    inner_item = layout.itemAt(j)
                    if inner_item.widget() and isinstance(inner_item.widget(), QLabel) and inner_item.widget().pixmap():
                        widget = inner_item.widget()
                        layout.removeItem(inner_item)
                        widget.deleteLater()

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        new_message_ids = list(chat_content.keys())
        existing_ids = set(self.messages.keys())

        for msg_id in list(existing_ids - set(new_message_ids)):
            widget = self.messages[msg_id].get("frame")
            if widget:
                widget.deleteLater()
            del self.messages[msg_id]
            if msg_id in self.message_order:
                self.message_order.remove(msg_id)

        for message_id, msg_data in chat_content.items():
            if not message_id:
                continue

            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants", [])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
            author_name = msg_data.get("author_name", character_name if not is_user else "User")

            if translator != 0:
                if translator == 1 or translator == 2:
                    if translator_mode in (0, 2) and target_language == 0:
                        if not is_user or translator_mode == 0:
                            service = "google" if translator == 1 else "yandex"
                            text = self.translator.translate(text, service, "ru")
                elif translator == 3:
                    if translator_mode in (0, 2) and target_language == 0:
                        if not is_user or translator_mode == 0:
                            text = self.translator.translate_local(text, "en", "ru")
            
            if message_id in self.messages:
                message_entry = self.messages[message_id]
                message_label = message_entry.get("label")
                personas_data = self.configuration_settings.get_user_data("personas")
                current_persona = character_information.get("selected_persona")
                if current_persona == "None" or current_persona is None:
                    user_name = "User"
                else:
                    try:
                        user_name = personas_data[current_persona].get("user_name", "User")
                    except Exception as e:
                        user_name = "User"

                html_text = re.sub(r'\s*!\[.*?\]\(.*?\)\s*', ' ', text)
                html_text = self.markdown_to_html(html_text)
                html_text = (html_text.replace("{{user}}", user_name)
                                    .replace("{{char}}", character_name)
                                    .replace("{{User}}", user_name)
                                    .replace("{{Char}}", character_name)
                                    .replace("{{пользователь}}", user_name)
                                    .replace("{{Пользователь}}", user_name)
                                    .replace("{{персонаж}}", character_name)
                                    .replace("{{Персонаж}}", character_name)
                                    .replace("{{шар}}", character_name)
                                    .replace("{{Шар}}", character_name)
                                    .replace("{{символ}}", character_name)
                                    .replace("{{Символ}}", character_name)
                            )

                if message_label:
                    message_label.setText(html_text)
                message_entry.update({
                    "text": text,
                    "author_name": author_name,
                    "is_user": is_user
                })
            else:
                await self.add_message(
                    character_name=character_name,
                    text=text,
                    is_user=is_user,
                    message_id=message_id
                )

        self.message_order = [msg_id for msg_id in new_message_ids if msg_id in self.messages]

        for idx, msg_id in enumerate(self.message_order):
            if msg_id in self.messages:
                widget = self.messages[msg_id]["frame"]
                if self.chat_container.indexOf(widget) == -1:
                    self.chat_container.insertWidget(idx, widget)

        self.chat_widget.setUpdatesEnabled(True)
        self.chat_container.update()
        self.ui.scrollArea_chat.setVisible(True)
        QApplication.processEvents()

    async def first_render_cai_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setVisible(False)

        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.messages.clear()
        self.message_order.clear()

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)

        chat_content = character_information.get("chat_content", {})

        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        sorted_messages = sorted(
            chat_content.items(),
            key=lambda item: item[1].get("sequence_number", float('inf'))
        )

        for original_message_id, msg_data in sorted_messages:
            try:
                message_id = original_message_id
                sequence = msg_data.get("sequence_number") or len(self.messages) + 1
                is_user = msg_data.get("is_user", False)
                text = msg_data.get("text", "")

                if translator != 0:
                    if translator == 1:  # Google Translator
                        if translator_mode in (0, 2):  # Translate all messages or only model messages
                            if target_language == 0:  # Target language is Russian
                                if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                    text = self.translator.translate(text, "google", "ru")
                    elif translator == 2:  # Yandex Translator
                        if translator_mode in (0, 2):  # Translate all messages or only model messages
                            if target_language == 0:  # Target language is Russian
                                if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                    text = self.translator.translate(text, "yandex", "ru")
                    elif translator == 3:  # MarianMT (local translator)
                        if translator_mode in (0, 2):  # Translate all messages or only model messages
                            if target_language == 0:  # Target language is Russian
                                if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                    text = self.translator.translate_local(text, "en", "ru")

                message_entry = await self.add_message(
                    character_name=character_name,
                    text=text,
                    is_user=is_user,
                    message_id=message_id
                )

                if message_entry:
                    self.messages[message_id] = {
                        "message_id": message_id,
                        "sequence_number": sequence,
                        "author_name": msg_data.get("author_name", "User" if is_user else character_name),
                        "is_user": is_user,
                        "text": text,
                        "label": message_entry["label"],
                        "frame": message_entry["frame"]
                    }
                    self.message_order.append(message_id)

            except Exception as e:
                logger.error(f"Error processing {message_id}: {str(e)}")
                traceback.print_exc()

        self.chat_widget.setUpdatesEnabled(True)
        self.ui.scrollArea_chat.setVisible(True)
        self.ui.scrollArea_chat.update()
        self.chat_container.update()
        QApplication.processEvents()

    async def render_cai_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setVisible(False)
        
        try:
            translator = self.configuration_settings.get_main_setting("translator")
            target_language = self.configuration_settings.get_main_setting("target_language")
            translator_mode = self.configuration_settings.get_main_setting("translator_mode")

            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            new_chat_content = character_information.get("chat_content", {})

            new_messages = {
                msg_id: {
                    "sequence_number": data.get("sequence_number", float('inf')),
                    "is_user": data.get("is_user", False),
                    "text": data.get("text", ""),
                    "author_name": data.get("author_name", "User" if data.get("is_user") else character_name)
                }
                for msg_id, data in new_chat_content.items()
            }

            current_ids = set(self.messages.keys())
            new_ids = set(new_messages.keys())

            for msg_id in current_ids - new_ids:
                if msg_id in self.messages:
                    widget = self.messages[msg_id].get("frame")
                    if widget and widget.parent():
                        widget.deleteLater()
                    del self.messages[msg_id]
                    if msg_id in self.message_order:
                        self.message_order.remove(msg_id)

            for msg_id in current_ids & new_ids:
                current = self.messages[msg_id]
                new_data = new_messages[msg_id]

                if (current["text"] != new_data["text"] or current["is_user"] != new_data["is_user"]):
                    current.update({
                        "text": new_data["text"],
                        "is_user": new_data["is_user"],
                        "author_name": new_data["author_name"]
                    })

            for msg_id in new_ids - current_ids:
                try:
                    msg_data = new_chat_content[msg_id]
                    is_user = msg_data.get("is_user", False)
                    text = msg_data.get("text", "")

                    if translator != 0:
                        if translator == 1:  # Google Translator
                            if translator_mode in (0, 2):  # Translate all messages or only model messages
                                if target_language == 0:  # Target language is Russian
                                    if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                        text = self.translator.translate(text, "google", "ru")
                        elif translator == 2:  # Yandex Translator
                            if translator_mode in (0, 2):  # Translate all messages or only model messages
                                if target_language == 0:  # Target language is Russian
                                    if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                        text = self.translator.translate(text, "yandex", "ru")
                        elif translator == 3:  # MarianMT (local translator)
                            if translator_mode in (0, 2):  # Translate all messages or only model messages
                                if target_language == 0:  # Target language is Russian
                                    if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                        text = self.translator.translate_local(text, "en", "ru")

                    message_entry = await self.add_message(
                        character_name=character_name,
                        text=text,
                        is_user=is_user,
                        message_id=msg_id
                    )

                    if message_entry:
                        self.messages[msg_id] = {
                            "message_id": msg_id,
                            "sequence_number": msg_data.get("sequence_number", len(self.messages) + 1),
                            "author_name": msg_data.get("author_name", "User" if msg_data["is_user"] else character_name),
                            "is_user": msg_data["is_user"],
                            "text": text,
                            "label": message_entry["label"],
                            "frame": message_entry["frame"],
                        }

                except Exception as e:
                    logger.error(f"Error processing message {msg_id}: {str(e)}")
                    traceback.print_exc()

            self.message_order = sorted(
                new_ids, 
                key=lambda x: new_messages[x]["sequence_number"]
            )

            for idx, msg_id in enumerate(self.message_order):
                if msg_id in self.messages:
                    widget = self.messages[msg_id]["frame"]
                    self.chat_container.insertWidget(idx, widget)

        finally:
            self.chat_widget.setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setVisible(True)
            QApplication.processEvents()

    async def speech_to_speech_loop(self, mode, character_name):
        """
        Continuously runs the speech-to-speech process until the corresponding stop button is pressed.
        """
        try:
            while getattr(self, f"running_{mode}"):
                await self.speech_to_speech_main(character_name)
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            logger.info(f"{mode.capitalize()} task was cancelled.")
        finally:
            logger.info(f"{mode.capitalize()} loop has stopped.")

    async def speech_to_speech_loop_no_gui(self, character_name, expression_mode):
        """
        Continuously runs the speech-to-speech process for Live2D and VRM NO GUI mode.
        """
        if expression_mode == "Live2D Model":
            if not self.running_live2d_no_gui:
                self.running_live2d_no_gui = True

            while self.running_live2d_no_gui:
                try:
                    await self.speech_to_speech_no_gui(character_name)
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    logger.info("No GUI task was cancelled.")
                    break
                except Exception as e:
                    logger.info(f"No GUI loop: {e}")
                    break

        elif expression_mode == "VRM":
            if not self.running_vrm_no_gui:
                self.running_vrm_no_gui = True

            while self.running_vrm_no_gui:
                try:
                    await self.speech_to_speech_no_gui(character_name)
                    await asyncio.sleep(0.1)
                except asyncio.CancelledError:
                    logger.info("No GUI task was cancelled.")
                    break
                except Exception as e:
                    logger.info(f"No GUI loop: {e}")
                    break
    
    async def speech_to_speech_main(self, character_name):
        """
        Handles the main speech-to-speech process: captures user input via speech-to-text,
        processes translations if needed, and prepares the message for further handling.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        current_translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        elevenlabs_voice_id = character_info["elevenlabs_voice_id"]
        voice_type = character_info["voice_type"]
        rvc_enabled = character_info["rvc_enabled"]
        rvc_file = character_info["rvc_file"]

        self.user_text_original = None

        if conversation_method == "Character AI":
            character_id = character_info.get("character_id")
            chat_id = character_info.get("chat_id")
            character_avatar_url = character_info.get("character_avatar")
            voice_name = character_info.get("voice_name")
            character_ai_voice_id = character_info.get("character_ai_voice_id")

        try:
            personas_data = self.configuration_settings.get_user_data("personas")
            current_persona = character_info.get("selected_persona")
            if current_persona == "None" or current_persona is None:
                user_name = "User"
            else:
                user_name = personas_data[current_persona].get("user_name", "User")
                user_description = personas_data[current_persona].get("user_description", "")
            
            self.user_text_original = await self.speech_to_text.speech_recognition()
            user_text = self.user_text_original

            match current_translator:
                case 0:
                    pass
                case 1:
                    # Google Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "google", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "google", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 2:
                    # Yandex Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "yandex", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "yandex", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 3:
                    # Local MarianMT Translator
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate_local(self.user_text_original, "ru", "en")
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate_local(self.user_text_original, "ru", "en")
                            else:
                                pass
                        case 2:
                            pass

            user_text_markdown = self.markdown_to_html(self.user_text_original)
            
            if user_text:
                user_message_container = await self.add_message(character_name, "", is_user=True, message_id=None)
                user_message_label = user_message_container["label"]

                user_message_label.setText(user_text_markdown)
                await asyncio.sleep(0.05)

                match conversation_method:
                    case "Character AI":
                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None)
                        character_answer_label = character_answer_container["label"]
                        
                        full_text = ""
                        turn_id = ""
                        candidate_id = ""

                        async for message in self.character_ai_client.send_message(character_id, chat_id, user_text):
                            text = message.get_primary_candidate().text
                            turn_id = message.turn_id
                            candidate_id = message.get_primary_candidate().candidate_id
                            
                            if text != full_text:
                                full_text = text
                                original_text = text
                                full_text_html = self.markdown_to_html(full_text)
                                full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                )
                                character_answer_label.setText(full_text_html)
                                await asyncio.sleep(0.05)

                                match current_sow_system_mode:
                                    case "Nothing":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "Expressions Images":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "Live2D Model":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "VRM":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model" | "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, original_text))

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translator
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                        
                        full_text = (full_text.replace("{{user}}", user_name)
                                        .replace("{{char}}", character_name)
                                        .replace("{{User}}", user_name)
                                        .replace("{{Char}}", character_name)
                                        .replace("{{пользователь}}", user_name)
                                        .replace("{{Пользователь}}", user_name)
                                        .replace("{{персонаж}}", character_name)
                                        .replace("{{Персонаж}}", character_name)
                                        .replace("{{шар}}", character_name)
                                        .replace("{{Шар}}", character_name)
                                        .replace("{{символ}}", character_name)
                                        .replace("{{Символ}}", character_name)
                                    )
                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "Character AI":
                                await asyncio.sleep(0.05)
                                await self.character_ai_client.generate_speech(chat_id, turn_id, candidate_id, character_ai_voice_id)
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                    await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)

                        await self.character_ai_client.fetch_chat(
                            chat_id, character_name, character_id, character_avatar_url, character_title,
                            character_description, character_personality, first_message, current_text_to_speech,
                            voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                            rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                            vrm_model_file, conversation_method, current_emotion
                        )

                    case "Mistral AI":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list")
                        character_info = character_list.get(character_name)
                        current_chat = character_info["current_chat"]
                        chats = character_info.get("chats", {})

                        chat_history = chats[current_chat]["chat_history"]

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")
                            if user_message:
                                context_messages.append({"role": "user", "content": f"{user_message.strip()}"})
                            if character_message:
                                context_messages.append({"role": "assistant", "content": f"{character_message.strip()}"})

                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None)
                        character_answer_label = character_answer_container["label"]

                        full_text = ""
                        
                        async for message in self.mistral_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description):
                            if message:
                                full_text += message
                                full_text_html = self.markdown_to_html(full_text)
                                full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                )
                                character_answer_label.setText(full_text_html)
                                await asyncio.sleep(0.05)
                                
                                match current_sow_system_mode:
                                    case "Nothing":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "Expressions Images":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "Live2D Model":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                    case "VRM":
                                        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                        if full_text_html.startswith(f"{character_name}:"):
                            full_text_html = full_text_html[len(f"{character_name}:"):].lstrip()

                        full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                    )
                        character_answer_label.setText(full_text_html)

                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model" | "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, full_text))

                        user_message_message_id = user_message_container["message_id"]
                        character_answer_message_id = character_answer_container["message_id"]
                        
                        self.configuration_characters.add_message_to_config(character_name, "User", True, user_text, user_message_message_id)
                        self.configuration_characters.add_message_to_config(character_name, character_name, False, full_text, character_answer_message_id)
                        await asyncio.sleep(0.5)

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translator
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                        
                        full_text = (full_text.replace("{{user}}", user_name)
                                        .replace("{{char}}", character_name)
                                        .replace("{{User}}", user_name)
                                        .replace("{{Char}}", character_name)
                                        .replace("{{пользователь}}", user_name)
                                        .replace("{{Пользователь}}", user_name)
                                        .replace("{{персонаж}}", character_name)
                                        .replace("{{Персонаж}}", character_name)
                                        .replace("{{шар}}", character_name)
                                        .replace("{{Шар}}", character_name)
                                        .replace("{{символ}}", character_name)
                                        .replace("{{Символ}}", character_name)
                                    )
                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)

                    case "Local LLM" | "Open AI" | "OpenRouter":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list")
                        character_info = character_list.get(character_name)
                        current_chat = character_info["current_chat"]
                        chats = character_info.get("chats", {})

                        chat_history = chats[current_chat]["chat_history"]

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")
                            if user_message:
                                context_messages.append({"role": "user", "content": f"{user_message.strip()}"})
                            if character_message:
                                context_messages.append({"role": "assistant", "content": f"{character_message.strip()}"})

                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None)
                        character_answer_label = character_answer_container["label"]

                        full_text = ""
                        full_text_html = ""

                        if conversation_method == "Local LLM":
                            async for chunk in self.local_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description):
                                if chunk:
                                    full_text += chunk
                                    full_text_html = self.markdown_to_html(full_text)
                                    full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                )
                                    character_answer_label.setText(full_text_html)
                                    await asyncio.sleep(0.05)
                                    
                                    match current_sow_system_mode:
                                        case "Nothing":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "Expressions Images":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "Live2D Model":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "VRM":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                        elif conversation_method in ["Open AI", "OpenRouter"]:
                            async for chunk in self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description):
                                if chunk:
                                    corrected_chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk
                                    full_text += corrected_chunk
                                    full_text_html = self.markdown_to_html(full_text)
                                    full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                )
                                    character_answer_label.setText(full_text_html)
                                    await asyncio.sleep(0.05)
                                    
                                    match current_sow_system_mode:
                                        case "Nothing":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "Expressions Images":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "Live2D Model":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                                        case "VRM":
                                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                        if full_text_html.startswith(f"{character_name}:"):
                            full_text_html = full_text_html[len(f"{character_name}:"):].lstrip()

                        full_text_html = (full_text_html.replace("{{user}}", user_name)
                                                        .replace("{{char}}", character_name)
                                                        .replace("{{User}}", user_name)
                                                        .replace("{{Char}}", character_name)
                                                        .replace("{{пользователь}}", user_name)
                                                        .replace("{{Пользователь}}", user_name)
                                                        .replace("{{персонаж}}", character_name)
                                                        .replace("{{Персонаж}}", character_name)
                                                        .replace("{{шар}}", character_name)
                                                        .replace("{{Шар}}", character_name)
                                                        .replace("{{символ}}", character_name)
                                                        .replace("{{Символ}}", character_name)
                                                )
                        character_answer_label.setText(full_text_html)
                        
                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Expressions Images" | "Live2D Model" | "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, full_text))

                        user_message_message_id = user_message_container["message_id"]
                        character_answer_message_id = character_answer_container["message_id"]
                        self.configuration_characters.add_message_to_config(character_name, "User", True, user_text, user_message_message_id)
                        self.configuration_characters.add_message_to_config(character_name, character_name, False, full_text, character_answer_message_id)
                        await asyncio.sleep(0.5)

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                            case 3:
                                # Local MarianMT Translator
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text_html = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text_html)
                                        else:
                                            pass
                        
                        full_text = (full_text.replace("{{user}}", user_name)
                                        .replace("{{char}}", character_name)
                                        .replace("{{User}}", user_name)
                                        .replace("{{Char}}", character_name)
                                        .replace("{{пользователь}}", user_name)
                                        .replace("{{Пользователь}}", user_name)
                                        .replace("{{персонаж}}", character_name)
                                        .replace("{{Персонаж}}", character_name)
                                        .replace("{{шар}}", character_name)
                                        .replace("{{Шар}}", character_name)
                                        .replace("{{символ}}", character_name)
                                        .replace("{{Символ}}", character_name)
                                    )
                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)
            
            if conversation_method == "Character AI":
                await self.render_cai_messages(character_name)
            else:
                await self.render_messages(character_name)
        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(f"Error processing the message: {error_message}")
    
    async def speech_to_speech_no_gui(self, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        current_translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        conversation_method = character_info["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        elevenlabs_voice_id = character_info["elevenlabs_voice_id"]
        voice_type = character_info["voice_type"]
        rvc_enabled = character_info["rvc_enabled"]
        rvc_file = character_info["rvc_file"]

        if conversation_method == "Character AI":
            character_id = character_info.get("character_id")
            chat_id = character_info.get("chat_id")
            character_avatar_url = character_info.get("character_avatar")
            voice_name = character_info.get("voice_name")
            character_ai_voice_id = character_info.get("character_ai_voice_id")

        try:
            personas_data = self.configuration_settings.get_user_data("personas")
            current_persona = character_info.get("selected_persona")
            if current_persona == "None" or current_persona is None:
                user_name = "User"
            else:
                user_name = personas_data[current_persona].get("user_name", "User")
                user_description = personas_data[current_persona].get("user_description", "")
            
            self.user_text_original = await self.speech_to_text.speech_recognition()
            user_text = self.user_text_original

            match current_translator:
                case 0:
                    pass
                case 1:
                    # Google Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "google", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "google", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 2:
                    # Yandex Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "yandex", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(self.user_text_original, "yandex", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 3:
                    # Local MarianMT Translator
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate_local(self.user_text_original, "ru", "en")
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate_local(self.user_text_original, "ru", "en")
                            else:
                                pass
                        case 2:
                            pass
            
            if user_text:
                user_message_container = await self.add_message(character_name, "", is_user=True, message_id=None, no_gui=True)
                match conversation_method:
                    case "Character AI":
                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None, no_gui=True)

                        full_text = ""
                        turn_id = ""
                        candidate_id = ""

                        async for message in self.character_ai_client.send_message(character_id, chat_id, user_text):
                            text = message.get_primary_candidate().text
                            turn_id = message.turn_id
                            candidate_id = message.get_primary_candidate().candidate_id
                            
                            if text != full_text:
                                full_text = text
                                
                        match current_sow_system_mode:
                            case "Nothing":
                                pass
                            case "Live2D Model" | "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, full_text))

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                        
                        full_text = (full_text.replace("{{user}}", user_name)
                                        .replace("{{char}}", character_name)
                                        .replace("{{User}}", user_name)
                                        .replace("{{Char}}", character_name)
                                        .replace("{{пользователь}}", user_name)
                                        .replace("{{Пользователь}}", user_name)
                                        .replace("{{персонаж}}", character_name)
                                        .replace("{{Персонаж}}", character_name)
                                        .replace("{{шар}}", character_name)
                                        .replace("{{Шар}}", character_name)
                                        .replace("{{символ}}", character_name)
                                        .replace("{{Символ}}", character_name)
                                    )
                        
                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "Character AI":
                                await asyncio.sleep(0.05)
                                await self.character_ai_client.generate_speech(chat_id, turn_id, candidate_id, character_ai_voice_id)
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)

                        await self.character_ai_client.fetch_chat(
                            chat_id, character_name, character_id, character_avatar_url, character_title,
                            character_description, character_personality, first_message, current_text_to_speech,
                            voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                            rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                            vrm_model_file, conversation_method, current_emotion
                        )

                    case "Mistral AI":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list")
                        character_info = character_list.get(character_name)
                        current_chat = character_info["current_chat"]
                        chats = character_info.get("chats", {})

                        chat_history = chats[current_chat]["chat_history"]

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")
                            if user_message:
                                context_messages.append({"role": "user", "content": f"{user_message.strip()}"})
                            if character_message:
                                context_messages.append({"role": "assistant", "content": f"{character_message.strip()}"})
                        
                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None, no_gui=True)

                        full_text = ""

                        async for message in self.mistral_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description):
                            if message:
                                full_text += message
                                await asyncio.sleep(0.05)

                        if full_text.startswith(f"{character_name}:"):
                            full_text = full_text[len(f"{character_name}:"):].lstrip()

                        full_text = (full_text.replace("{{user}}", user_name)
                                                .replace("{{char}}", character_name)
                                                .replace("{{User}}", user_name)
                                                .replace("{{Char}}", character_name)
                                                .replace("{{пользователь}}", user_name)
                                                .replace("{{Пользователь}}", user_name)
                                                .replace("{{персонаж}}", character_name)
                                                .replace("{{Персонаж}}", character_name)
                                                .replace("{{шар}}", character_name)
                                                .replace("{{Шар}}", character_name)
                                                .replace("{{символ}}", character_name)
                                                .replace("{{Символ}}", character_name)
                                            )

                        match current_sow_system_mode:
                            case "Live2D Model" | "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, full_text))

                        user_message_message_id = user_message_container["message_id"]
                        character_answer_message_id = character_answer_container["message_id"]

                        self.configuration_characters.add_message_to_config(character_name, "User", True, user_text, user_message_message_id)
                        self.configuration_characters.add_message_to_config(character_name, character_name, False, full_text, character_answer_message_id)
                        await asyncio.sleep(0.5)

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                        
                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)

                    case "Local LLM" | "Open AI" | "OpenRouter":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list")
                        character_info = character_list.get(character_name)
                        current_chat = character_info["current_chat"]
                        chats = character_info.get("chats", {})

                        chat_history = chats[current_chat]["chat_history"]

                        context_messages = []
                        for message in chat_history:
                            user_message = message.get("user", "")
                            character_message = message.get("character", "")
                            if user_message:
                                context_messages.append({"role": "user", "content": f"{user_message.strip()}"})
                            if character_message:
                                context_messages.append({"role": "assistant", "content": f"{character_message.strip()}"})
                        
                        character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None, no_gui=True)

                        full_text = ""

                        if conversation_method == "Local LLM":
                            async for chunk in self.local_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description):
                                if chunk:
                                    full_text += chunk
                                    await asyncio.sleep(0.05)
                        elif conversation_method in ["Open AI", "OpenRouter"]:
                            async for chunk in self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description):
                                if chunk:
                                    corrected_chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk
                                    full_text += corrected_chunk
                                    await asyncio.sleep(0.05)

                        if full_text.startswith(f"{character_name}:"):
                            full_text = full_text[len(f"{character_name}:"):].lstrip()

                        full_text = (full_text.replace("{{user}}", user_name)
                                                .replace("{{char}}", character_name)
                                                .replace("{{User}}", user_name)
                                                .replace("{{Char}}", character_name)
                                                .replace("{{пользователь}}", user_name)
                                                .replace("{{Пользователь}}", user_name)
                                                .replace("{{персонаж}}", character_name)
                                                .replace("{{Персонаж}}", character_name)
                                                .replace("{{шар}}", character_name)
                                                .replace("{{Шар}}", character_name)
                                                .replace("{{символ}}", character_name)
                                                .replace("{{Символ}}", character_name)
                                            )

                        match current_sow_system_mode:
                            case "Live2D Model":
                                asyncio.create_task(self.detect_emotion(character_name, full_text))
                            case "VRM":
                                asyncio.create_task(self.detect_emotion(character_name, full_text, vrm_mode=True))

                        user_message_message_id = user_message_container["message_id"]
                        character_answer_message_id = character_answer_container["message_id"]

                        self.configuration_characters.add_message_to_config(character_name, "User", True, user_text, user_message_message_id)
                        self.configuration_characters.add_message_to_config(character_name, character_name, False, full_text, character_answer_message_id)
                        await asyncio.sleep(0.5)

                        match current_translator:
                            case 0:
                                pass
                            case 1:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "google", 'ru')
                                        else:
                                            pass
                            case 2:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text, "yandex", "ru")
                                        else:
                                            pass
                            case 3:
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text, "en", "ru")
                                        else:
                                            pass

                        full_text_tts = self.clean_text_for_tts(full_text)
                        match current_text_to_speech:
                            case "Nothing" | None:
                                pass
                            case "ElevenLabs":
                                await asyncio.sleep(0.05)
                                await self.eleven_labs_client.generate_speech_with_elevenlabs(full_text_tts, elevenlabs_voice_id)
                            case "XTTSv2":
                                if current_translator != 0:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="ru", character_name=character_name)
                                else:
                                    await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(text=full_text_tts, language="en", character_name=character_name)
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                await self.kokoro_client.generate_speech_with_kokoro(text=full_text_tts, character_name=character_name)

        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(f"Error processing the message: {error_message}")

    def toggleStartStopAvatar(self, character_name):
        """
        Toggles the Start/Stop state for the Avatar tab and manages the associated task.
        """
        if not hasattr(self, "running_avatar"):
            self.running_avatar = False 

        if not self.running_avatar:
            self.ui.pushButton_play.setIcon(self.icon_stop)
            self.ui.status_label.setText(self.translations.get("sow_system_status_speak", "Speak..."))
            self.running_avatar = True
            self.avatar_task = asyncio.create_task(self.speech_to_speech_loop("avatar", character_name))
        else:
            self.ui.pushButton_play.setIcon(self.icon_play)
            self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))
            self.running_avatar = False
            if self.avatar_task:
                self.avatar_task.cancel()
                self.avatar_task = None

    def toggleStartStopImage(self, character_name):
        """
        Toggles the Start/Stop state for the Expression Image tab and manages the associated task.
        """
        if not self.running_image:
            self.ui.pushButton_play.setIcon(self.icon_stop)
            self.ui.status_label.setText(self.translations.get("sow_system_status_speak", "Speak..."))
            self.running_image = True
            self.image_task = asyncio.create_task(self.speech_to_speech_loop("image", character_name))
        else:
            self.ui.pushButton_play.setIcon(self.icon_play)
            self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))
            self.running_image = False
            if self.image_task:
                self.image_task.cancel()
                self.image_task = None

    def toggleStartStopLive2D(self, character_name):
        """
        Toggles the Start/Stop state for the Live2D tab and manages the associated task.
        """
        if not self.running_live2d:
            self.ui.pushButton_play.setIcon(self.icon_stop)
            self.ui.status_label.setText(self.translations.get("sow_system_status_speak", "Speak..."))
            self.running_live2d = True
            self.live2d_task = asyncio.create_task(self.speech_to_speech_loop("live2d", character_name))
        else:
            self.ui.pushButton_play.setIcon(self.icon_play)
            self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))
            self.running_live2d = False
            if self.live2d_task:
                self.live2d_task.cancel()
                self.live2d_task = None
    
    def toggleStartStopVRM(self, character_name):
        """
        Toggles the Start/Stop state for the VRM tab and manages the associated task.
        """
        if not self.running_vrm:
            self.ui.pushButton_play.setIcon(self.icon_stop)
            self.ui.status_label.setText(self.translations.get("sow_system_status_speak", "Speak..."))
            self.running_vrm = True
            self.vrm_task = asyncio.create_task(self.speech_to_speech_loop("vrm", character_name))
        else:
            self.ui.pushButton_play.setIcon(self.icon_play)
            self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))
            self.running_vrm = False
            if self.vrm_task:
                self.vrm_task.cancel()
                self.vrm_task = None

    def draw_circle_avatar(self, avatar_path, current_sow_system_mode):
        """
        Draws a character's avatar
        """
        pixmap = QPixmap(avatar_path)
        mask = QPixmap(pixmap.size())
        mask.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QtCore.Qt.GlobalColor.black)
        painter.setPen(QtCore.Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()

        pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
        self.ui.character_avatar_label.setPixmap(pixmap.scaled(40, 40, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        self.ui.character_avatar_label.setFixedSize(40, 40)
        self.ui.character_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

        if current_sow_system_mode == "Nothing":
            self.ui.avatar_label.setPixmap(pixmap.scaled(200, 200, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            self.ui.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
    
    def markdown_to_html(self, text):
        # 1. Text in double quotes ("text")
        text = re.sub(r'"(.*?)"', r'<span style="color: orange;">"\1"</span>', text)
        text = re.sub(r'“(.*?)”', r'<span style="color: orange;">"\1"</span>', text)

        # 2. Bold text (**text** or __text__)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

        # 3. Italics (*text* or _text_)
        text = re.sub(r'\*(.*?)\*', r'<i><span style="color: #a3a3a3;">\1</span></i>', text)
        text = re.sub(r'_(.*?)_', r'<i><span style="color: #a3a3a3;">\1</span></i>', text)

        # 4. Headers (#, ##, ###)
        text = re.sub(r'^#\s+(.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)

        # 5. Numbered lists (1. element)
        text = re.sub(r'^(\d+\.)\s+(.*)$', r'<ol><li>\2</li></ol>', text, flags=re.MULTILINE)

        # 6. Lists (* element or - element)
        text = re.sub(r'^[\*\-]\s+(.*)$', r'<ul><li>\1</li></ul>', text, flags=re.MULTILINE)

        # 7. Code blocks (```code```)
        text = re.sub(
            r'```(.*?)```',
            r'<pre style="background-color: #1a1a1a; color: #c7c7c7; border-radius: 6px; font-family: Inter Tight Light;">\1</pre>',
            text,
            flags=re.DOTALL
        )

        # 8. Inline code (`code`)
        text = re.sub(
            r'`([^`]+)`',
            r'<code style="background-color: #1a1a1a; color: #c7c7c7; border-radius: 6px; font-family: Inter Tight Light;">\1</code>',
            text
        )

        # 9. Line break (\n)
        text = text.replace('\n', '<br>')

        return text
    
    def clean_text_for_tts(self, full_text):
        cleaned_text = re.sub(r"[^a-zA-Zа-яА-Я0-9\s.,!?]", "", full_text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text
    
    async def add_message(self, character_name, text, is_user, message_id, no_gui=False):
        """
        Adds a message to the chat interface
        """
        if not message_id:
            message_id = str(uuid.uuid4())
        
        if message_id in self.messages:
            return self.messages[message_id]
        
        configuration_data = self.configuration_characters.load_configuration()
        char_info = configuration_data["character_list"][character_name]
        conversation_method = char_info.get("conversation_method", {})
        character_avatar = char_info.get("character_avatar", {})
        if conversation_method == "Character AI":
            character_avatar = self.character_ai_client.get_from_cache(character_avatar)

        personas_data = self.configuration_settings.get_user_data("personas")
        current_persona = char_info.get("selected_persona")
        if current_persona == "None" or current_persona is None:
            user_name = "User"
        else:
            user_name = personas_data[current_persona].get("user_name", "User")
        
        html_text = re.sub(r'\s*!\[.*?\]\(.*?\)\s*', ' ', text)
        html_text = self.markdown_to_html(html_text)
        html_text = (html_text.replace("{{user}}", user_name)
                            .replace("{{char}}", character_name)
                            .replace("{{User}}", user_name)
                            .replace("{{Char}}", character_name)
                            .replace("{{пользователь}}", user_name)
                            .replace("{{Пользователь}}", user_name)
                            .replace("{{персонаж}}", character_name)
                            .replace("{{Персонаж}}", character_name)
                            .replace("{{шар}}", character_name)
                            .replace("{{Шар}}", character_name)
                            .replace("{{символ}}", character_name)
                            .replace("{{Символ}}", character_name)
                    )
        
        message_container = QHBoxLayout()
        message_container.setSpacing(5)
        message_container.setContentsMargins(10, 5, 10, 5)

        message_label = QLabel()
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setText(html_text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        message_label.setFont(font)

        message_frame = QFrame(None)
        message_frame.setStyleSheet("""
            QMenu {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #383838;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
        """)
        message_frame.setLayout(message_container)

        if no_gui == False:
            if is_user:
                message_label.setStyleSheet("""
                    QLabel {
                        border: none;
                        background-color: #292929;
                        color: rgb(220, 220, 220);
                        border-top-left-radius: 15px;
                        border-bottom-left-radius: 15px;
                        border-bottom-right-radius: 0px;
                        border-top-right-radius: 15px;
                        padding: 12px;
                        font-size: 12px;
                        margin: 5px;
                        letter-spacing: 0.5px;
                        text-align: justify;
                        white-space: pre-line;
                    }
                """)
                avatar_pixmap = QPixmap(self.user_avatar)
            else:
                message_label.setStyleSheet("""
                    QLabel {
                        border: none;
                        background-color: #222222;
                        color: rgb(220, 220, 220);
                        border-top-right-radius: 15px;
                        border-bottom-right-radius: 15px;
                        border-top-left-radius: 15px;
                        border-bottom-left-radius: 0px;
                        padding: 12px;
                        font-size: 12px;
                        margin: 5px;
                        letter-spacing: 0.5px;
                        text-align: justify;
                        min-width: 290px;
                        max-width: 70%;
                        white-space: pre-line;
                    }
                """)
                avatar_pixmap = QPixmap(character_avatar)

            avatar_label = QLabel()
            avatar_label.setStyleSheet("border: none;")
            avatar_pixmap = avatar_pixmap.scaled(45, 45, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
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
            avatar_label.setScaledContents(True)

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 2)
            message_label.setGraphicsEffect(shadow)

            if is_user:
                message_container.addStretch()
                message_container.addWidget(message_label)
                message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
            else:
                message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
                message_container.addWidget(message_label)
                message_container.addStretch()

            self.chat_container.addWidget(message_frame)
            await asyncio.sleep(0.005)
            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
        else:
            pass

        self.messages[message_id] = {
            "message_id": message_id,
            "text": text,
            "author_name": user_name if is_user else character_name,
            "label": message_label,
            "frame": message_frame,
            "layout": message_container,
            "is_user": is_user
        }

        self.message_order.append(message_id)

        return {
            "message_id": message_id,
            "label": message_label,
            "frame": message_frame,
            "layout": message_container
        }

    async def detect_emotion(self, character_name, text, vrm_mode=False):
        """
        Detects emotion based on the input text and updates the character's expression (image, Live2D model or VRM).
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]

        expression_images_folder = character_information["expression_images_folder"]
        live2d_model_folder = character_information["live2d_model_folder"]
        current_sow_system_mode = character_information["current_sow_system_mode"]
        conversation_method = character_information["conversation_method"]

        if current_sow_system_mode == "Nothing":
            return

        if self.tokenizer is None or self.session is None:
            tokenizer_path = os.path.join("app", "utils", "emotions", "detector")
            self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
            model_path = os.path.join("app", "utils", "emotions", "detector")
            model = AutoModelForSequenceClassification.from_pretrained(model_path)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)

        with torch.no_grad():
            outputs = model(**inputs)

        logits = outputs.logits
        predicted_class_id = torch.argmax(logits, dim=1).item()
        
        emotions = [
            "admiration", "amusement", "anger", "annoyance", "approval", "caring", "confusion", "curiosity",
            "desire", "disappointment", "disapproval", "disgust", "embarrassment", "excitement", "fear",
            "gratitude", "grief", "love", "nervousness", "neutral", "optimism", "pride", "realization",
            "relief", "remorse", "surprise", "joy", "sadness"
        ]
        emotion = emotions[predicted_class_id]

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            configuration_data["character_list"][character_name]["chats"][current_chat]["current_emotion"] = emotion
            self.configuration_characters.save_configuration_edit(configuration_data)
        else:
            configuration_data["character_list"][character_name]["current_emotion"] = emotion
            self.configuration_characters.save_configuration_edit(configuration_data)

        if current_sow_system_mode == "Expressions Images":
            self.show_emotion_image(expression_images_folder, character_name)
        elif current_sow_system_mode == "Live2D Model":
            model_json_path = self.find_model_json(live2d_model_folder)
            if model_json_path:
                self.update_model_json(model_json_path, self.emotion_resources)
        elif current_sow_system_mode == "VRM":
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][character_name]
            conversation_method = character_info["conversation_method"]
            vrm_model_path = character_info["vrm_model_file"]
            
            if conversation_method != "Character AI":
                current_chat = character_info["current_chat"]
                chats = character_info.get("chats", {})
                current_emotion = chats[current_chat]["current_emotion"]
            else:
                current_emotion = character_info["current_emotion"]

            if vrm_mode == True:
                vrm_no_gui = VRMWidget_NoGUI(
                    parent=self.parent_window,
                    vrm_model_path=vrm_model_path,
                    character_name=self.character_name,
                    current_emotion=current_emotion,
                    running_vrm_no_gui=self.running_vrm_no_gui,
                    vrm_no_gui_task=None
                )
                vrm_no_gui.play_animation(emotion)
            else:
                self.show_emotion_animation(character_name)

    def find_model_json(self, live2d_model_folder):
        """
        Searches for a .model3.json file in the Live2D model folder.
        """
        for root, dirs, files in os.walk(live2d_model_folder):
            for file in files:
                if file.endswith(".model3.json"):
                    return os.path.join(root, file)
        return None

    def update_model_json(self, model_json_path, emotion_resources):
        """
        Updates the .model3.json file by adding missing emotions to the Expressions section.
        """
        emotions_path = "../../../../app/utils/emotions/live2d/expressions"
        
        with open(model_json_path, "r", encoding="utf-8") as file:
            model_data = json.load(file)

        file_references = model_data.get("FileReferences", {})
        
        if "Expressions" not in file_references:
            file_references["Expressions"] = []

        expressions = file_references["Expressions"]

        expressions_dict = {expr["Name"]: expr for expr in expressions}

        for emotion_name in emotion_resources.keys():
            expressions_dict[emotion_name] = {
                "Name": emotion_name,
                "File": f"{emotions_path}/{emotion_name}_animation.exp3.json"
            }
        
        file_references["Expressions"] = list(expressions_dict.values())
        model_data["FileReferences"] = file_references

        with open(model_json_path, "w", encoding="utf-8") as file:
            json.dump(model_data, file, indent=4, ensure_ascii=False)

    def show_emotion_image(self, expression_images_folder, character_name):
        """
        Displays an image or GIF representing the character's current emotion.
        """
        configuration_data = self.configuration_characters.load_configuration()
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        image_name = self.emotion_resources[current_emotion]["image"]

        if self.ui.avatar_label is not None:
            gif_path = os.path.join(expression_images_folder, f"{image_name}.gif")
            png_path = os.path.join(expression_images_folder, f"{image_name}.png")
            neutral_gif_path = os.path.join(expression_images_folder, "neutral.gif")
            neutral_png_path = os.path.join(expression_images_folder, "neutral.png")

            if os.path.exists(gif_path):
                movie = QtGui.QMovie(gif_path)
                movie.setScaledSize(QtCore.QSize(320, 530))
                self.ui.avatar_label.setMovie(movie)
                movie.start()
            elif os.path.exists(neutral_gif_path):
                movie = QtGui.QMovie(neutral_gif_path)
                movie.setScaledSize(QtCore.QSize(320, 530))
                self.ui.avatar_label.setMovie(movie)
                movie.start()
            elif os.path.exists(png_path):
                pixmap = QPixmap(png_path)
                scaled_pixmap = pixmap.scaled(
                    self.ui.avatar_label.width(),
                    self.ui.avatar_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.ui.avatar_label.setPixmap(scaled_pixmap)
            elif os.path.exists(neutral_png_path):
                pixmap = QPixmap(neutral_png_path)
                scaled_pixmap = pixmap.scaled(
                    self.ui.avatar_label.width(),
                    self.ui.avatar_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.ui.avatar_label.setPixmap(scaled_pixmap)
            else:
                logger.error(f"Files for emotion {image_name} and neutral not found.")
    
    def show_emotion_animation(self, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        self.set_expression_vrm(current_emotion)
        self.play_vrm_animation(current_emotion)

    async def initialize_sow_system_no_gui(self, current_sow_system_mode):
        """
        Initializes the Live2D or VRM model without a GUI
        """
        character_data = self.configuration_characters.load_configuration()

        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        model_background_image = self.configuration_settings.get_main_setting("model_background_image")

        if current_sow_system_mode == "Live2D Model":
            live2d_model_folder = character_data["character_list"][self.character_name]["live2d_model_folder"]
            model_json_path = self.find_model_json(live2d_model_folder)
            if model_json_path:
                self.update_model_json(model_json_path, self.emotion_resources)
                self.live2d_no_gui_task = asyncio.create_task(self.speech_to_speech_loop_no_gui(self.character_name, current_sow_system_mode))
                await asyncio.sleep(0.5)
                self.live2d_no_gui = Live2DWidget_NoGUI(
                    parent=self.parent_window, 
                    model_path=model_json_path, 
                    character_name=self.character_name, 
                    running_live2d_no_gui=self.running_live2d_no_gui, 
                    live2d_no_gui_task=self.live2d_no_gui_task
                )

                self.live2d_no_gui.show()

        elif current_sow_system_mode == "VRM":
            vrm_model_path = character_data["character_list"][self.character_name]["vrm_model_file"]
            if vrm_model_path:
                configuration_data = self.configuration_characters.load_configuration()
                character_info = configuration_data["character_list"][self.character_name]
                current_chat = character_info["current_chat"]
                chats = character_info.get("chats", {})

                self.vrm_no_gui_task = asyncio.create_task(self.speech_to_speech_loop_no_gui(self.character_name, current_sow_system_mode))
                await asyncio.sleep(0.5)

                current_emotion = chats[current_chat]["current_emotion"]
                self.vrm_no_gui = VRMWidget_NoGUI(
                    parent=self.parent_window,
                    vrm_model_path=vrm_model_path,
                    character_name=self.character_name,
                    model_background_color=model_background_color,
                    model_background_image=model_background_image,
                    model_background_type=model_background_type,
                    current_emotion=current_emotion,
                    running_vrm_no_gui=self.running_vrm_no_gui,
                    vrm_no_gui_task=self.vrm_no_gui_task
                )
                self.vrm_no_gui.show()
            else:
                logger.error("VRM model path not specified for character")
            
    
class Live2DWidget(QOpenGLWidget):
    """
    Initializes the Live2DWidget for rendering Live2D models.
    """
    def __init__(self, parent=None, model_path=None, character_name=None):
        super().__init__(parent)

        if model_path is None:
            logger.error("model_path must be provided")

        self.configuration_characters = configuration.ConfigurationCharacters()
        self.configuration_settings = configuration.ConfigurationSettings()

        self.model_path = model_path
        self.character_name = character_name
        self.parent = parent

        self.output_device = self.configuration_settings.get_main_setting("output_device_real_index")

        logger.info("Initializing Live2D...")
        live2d.init()
        logger.info("Live2D initialized.")

        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.timerId = None

        self.dragging = False
        self.right_button_pressed = False
        self.dx = 0.0
        self.dy = 0.0
        self.last_mouse_x = 0.0
        self.last_mouse_y = 0.0
        self.scale = 1.0
        self.min_scale = 0.5
        self.max_scale = 2.0
        self.drag_sensitivity = 0.5

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        logger.info("Widget initialized.")
        
    def initializeGL(self) -> None:
        """
        Initializes OpenGL and loads the Live2D model.
        """
        if self.opengl_initialized:
            logger.info("OpenGL already initialized, skipping initialization.")
            return
        
        logger.info("Initializing OpenGL...")
        try:
            self.makeCurrent()
            logger.info("Current OpenGL context activated.")
        except Exception as e:
            logger.info(f"Error activating OpenGL context: {e}")
            return
        
        if live2d.LIVE2D_VERSION == 3:
            logger.info("Initializing GLEW...")
            try:
                live2d.glInit()
                logger.info("GLEW successfully initialized.")
            except Exception as e:
                logger.info(f"Error initializing GLEW: {e}")
                return
        
        logger.info("OpenGL initialized.")
        self.opengl_initialized = True

        if not self.live2d_model_loaded:
            logger.info(f"Loading model from {self.model_path}...")
            try:
                self.live2d_model = live2d.LAppModel()
                self.live2d_model.SetAutoBreathEnable(True)
                self.live2d_model.SetAutoBlinkEnable(True)
                self.live2d_model.LoadModelJson(self.model_path)
                self.live2d_model_loaded = True
                self.live2d_model.Resize(self.width(), self.height())
                logger.info("Model successfully loaded.")
            except Exception as e:
                logger.info(f"Error loading model: {e}")
                return

            logger.info("Starting the cycle...")
            try:
                model_fps = self.configuration_settings.get_main_setting("model_fps")
                if model_fps == 0:
                    self.timerId = self.startTimer(int(1000 / 30))
                    logger.info("30 FPS MODE")
                elif model_fps == 1:
                    self.timerId = self.startTimer(int(1000 / 60))
                    logger.info("60 FPS MODE")
                elif model_fps == 2:
                    self.timerId = self.startTimer(int(1000 / 120))
                    logger.info("120 FPS MODE")
                logger.info("Timer started.")
            except Exception as e:
                logger.error(f"Error starting timer: {e}")
                return

    def resizeGL(self, w: int, h: int) -> None:
        """
        Handles resizing of the OpenGL viewport.

        Args:
            w (int): New width of the widget.
            h (int): New height of the widget.
        """
        gl.glViewport(0, 0, w, h)

        if self.live2d_model:
            try:
                self.live2d_model.Resize(w, h)
            except Exception as e:
                logger.error(f"Error resizing model: {e}")
    
    def paintGL(self) -> None:
        """
        Renders the Live2D model.
        """
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

        live2d.clearBuffer()
        
        if self.live2d_model:
            gl.glLoadIdentity()
            self.live2d_model.Update()
            self.live2d_model.Draw()

    def timerEvent(self, a0: QTimerEvent | None):
        """
        Updates the Live2D model and triggers a repaint.
        """
        self.update_live2d_emotion()
        self.repaint()
        self.update()

    def update_live2d_emotion(self):
        """
        Updates the emotion of the Live2D model based on the current character's emotion.
        """
        if self.live2d_model:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]

            conversation_method = character_info["conversation_method"]
        
            if conversation_method != "Character AI":
                current_chat = character_info["current_chat"]
                chats = character_info.get("chats", {})
                current_emotion = chats[current_chat]["current_emotion"]
            else:
                current_emotion = character_info["current_emotion"]

            self.live2d_model.SetExpression(current_emotion)
        else:
            logger.error('Emotion not detected')

    def cleanup(self):
        """
        Cleans up resources used by the Live2D model and OpenGL context.
        """
        logger.info("Releasing model resources...")
        if self.timerId is not None:
            logger.info("Stopping timer...")
            self.killTimer(self.timerId)
            self.timerId = None

        if self.live2d_model:
            logger.info("Releasing Live2D model...")
            try:
                live2d.dispose()
            except Exception as e:
                logger.error(f"Error releasing Live2D: {e}")
            self.live2d_model = None

        if self.opengl_initialized:
            logger.info("Deactivating OpenGL context...")
            try:
                self.doneCurrent()
            except Exception as e:
                logger.error(f"Error deactivating OpenGL context: {e}")

        self.live2d_model_loaded = False
        self.opengl_initialized = False
        logger.info("All resources released.")

    def hideEvent(self, event):
        """
        Handles the hide event by stopping the timer and cleaning up resources.
        """
        logger.info("Widget hidden, stopping timer and releasing resources.")
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        
        self.cleanup()
        super().hideEvent(event)

    def closeEvent(self, event):
        """
        Handles the close event by cleaning up resources.
        """
        logger.info("Closing widget...")
        self.cleanup()
        super().closeEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        new_width = self.width()
        new_height = self.height()
        self.resize(new_width, new_height)
    
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()
        
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = False

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        if self.live2d_model and self.right_button_pressed:
            norm_x = (x / self.width()) * 2 - 1
            norm_y = (y / self.height()) * 2 - 1

            angle_x = norm_x * 30
            angle_y = norm_y * 30

            eye_x = norm_x * 1.0
            eye_y = norm_y * 1.0

            self.live2d_model.SetParameterValue("ParamAngleX", angle_x)
            self.live2d_model.SetParameterValue("ParamAngleY", -angle_y)
            self.live2d_model.SetParameterValue("ParamEyeBallX", eye_x)
            self.live2d_model.SetParameterValue("ParamEyeBallY", -eye_y)

        if self.dragging:
            dx_mouse = x - self.last_mouse_x
            dy_mouse = y - self.last_mouse_y

            scale_x = 2.0 / self.width()
            scale_y = 2.0 / self.height()
            scale_xy = min(scale_x, scale_y)

            self.dx += dx_mouse * scale_xy * self.drag_sensitivity
            self.dy -= dy_mouse * scale_xy * self.drag_sensitivity

            self.live2d_model.SetOffset(self.dx, self.dy)

            self.last_mouse_x = x
            self.last_mouse_y = y

        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        delta = event.angleDelta().y()
        scale_step = 0.1 if delta > 0 else -0.1
        new_scale = self.scale + scale_step

        new_scale = max(self.min_scale, min(self.max_scale, new_scale))

        self.scale = new_scale
        if self.live2d_model:
            self.live2d_model.SetScale(self.scale)
        
        self.update()

class Live2DWidget_NoGUI(QOpenGLWidget):
    def __init__(self, parent=None, model_path=None, character_name=None, running_live2d_no_gui=None, live2d_no_gui_task=None):
        super().__init__()

        self.resize(500, 500)
        self.setWindowTitle(f"Soul of Waifu System - Call with {character_name}")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet("background: transparent;")
        
        if model_path is None:
            logger.error("model_path must be provided")

        self.configuration_characters = configuration.ConfigurationCharacters()
        self.configuration_settings = configuration.ConfigurationSettings()

        self.model_path = model_path
        self.character_name = character_name
        self.parent = parent

        self.output_device = self.configuration_settings.get_main_setting("output_device_real_index")

        logger.info("Initializing Live2D...")
        live2d.init()
        logger.info("Live2D initialized.")

        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.timerId = None

        self.isInLA = False
        self.clickInLA = False
        self.clickX = -1
        self.clickY = -1
        self.systemScale = QGuiApplication.primaryScreen().devicePixelRatio()

        self.dragging = False
        self.right_button_pressed = False
        self.left_button_pressed = False
        self.dx = 0.0
        self.dy = 0.0
        self.last_mouse_x = 0.0
        self.last_mouse_y = 0.0
        self.scale = 1.0
        self.min_scale = 0.5
        self.max_scale = 2.0
        self.drag_sensitivity = 0.5

        self.running_live2d_no_gui = running_live2d_no_gui
        self.live2d_no_gui_task = live2d_no_gui_task

        logger.info("Widget initialized.")
        
    def initializeGL(self) -> None:
        """
        Initializes OpenGL and loads the Live2D model.
        """
        if self.opengl_initialized:
            logger.info("OpenGL already initialized, skipping initialization.")
            return
        
        logger.info("Initializing OpenGL...")
        try:
            self.makeCurrent()
            logger.info("Current OpenGL context activated.")
        except Exception as e:
            logger.info(f"Error activating OpenGL context: {e}")
            return
        
        if live2d.LIVE2D_VERSION == 3:
            logger.info("Initializing GLEW...")
            try:
                live2d.glInit()
                logger.info("GLEW successfully initialized.")
            except Exception as e:
                logger.info(f"Error initializing GLEW: {e}")
                return
        
        logger.info("OpenGL initialized.")
        self.opengl_initialized = True

        if not self.live2d_model_loaded:
            logger.info(f"Loading model from {self.model_path}...")
            try:
                self.live2d_model = live2d.LAppModel()
                self.live2d_model.SetAutoBreathEnable(True)
                self.live2d_model.SetAutoBlinkEnable(True)
                self.live2d_model.LoadModelJson(self.model_path)
                self.live2d_model_loaded = True
                logger.info("Model successfully loaded.")
            except Exception as e:
                logger.info(f"Error loading model: {e}")
                return

            logger.info("Starting the cycle...")
            try:
                model_fps = self.configuration_settings.get_main_setting("model_fps")
                if model_fps == 0:
                    self.timerId = self.startTimer(int(1000 / 30))
                    logger.info("30 FPS MODE")
                elif model_fps == 1:
                    self.timerId = self.startTimer(int(1000 / 60))
                    logger.info("60 FPS MODE")
                elif model_fps == 2:
                    self.timerId = self.startTimer(int(1000 / 120))
                    logger.info("120 FPS MODE")
                logger.info("Timer started.")
            except Exception as e:
                logger.error(f"Error starting timer: {e}")
                return

    def resizeGL(self, w: int, h: int):
        """
        Handles resizing of the OpenGL viewport.

        Args:
            w (int): New width of the widget.
            h (int): New height of the widget.
        """
        if self.live2d_model:
            try:
                self.live2d_model.Resize(w, h)
            except Exception as e:
                logger.error(f"Error resizing model: {e}")

    def paintGL(self):
        """
        Renders the Live2D model.
        """
        gl.glClearColor(0.0, 0.0, 0.0, 0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        
        if self.live2d_model:
            self.live2d_model.Update()
            self.live2d_model.Draw()

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
        logger.info("Releasing model resources...")
        if self.timerId is not None:
            logger.info("Stopping timer...")
            self.killTimer(self.timerId)
            self.timerId = None

        if self.live2d_model:
            logger.info("Releasing Live2D model...")
            try:
                live2d.dispose()
            except Exception as e:
                logger.error(f"Error releasing Live2D: {e}")
            self.live2d_model = None

        if self.opengl_initialized:
            logger.info("Deactivating OpenGL context...")
            try:
                self.doneCurrent()
            except Exception as e:
                logger.error(f"Error deactivating OpenGL context: {e}")

        self.live2d_model_loaded = False
        self.opengl_initialized = False
        logger.info("All resources released.")

    def stop_live2d_no_gui_tasks(self):
        self.running_live2d_no_gui = False

        if hasattr(self, "live2d_no_gui_task") and self.live2d_no_gui_task:
            self.live2d_no_gui_task.cancel()
            self.live2d_no_gui_task = None

    def closeEvent(self, event):
        """
        Handles the close event by cleaning up resources.
        """
        logger.info("Closing widget...")
        self.cleanup()
        self.stop_live2d_no_gui_tasks()
        if self.parent:
            self.parent.show()
        super().closeEvent(event)

    def isInL2DArea(self, click_x, click_y):
        h = self.height()
        try:
            pixel = gl.glReadPixels(int(click_x * self.systemScale), int((h - click_y) * self.systemScale), 1, 1, gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
            alpha = pixel[3] if isinstance(pixel, bytes) else pixel[0][3]
            return alpha > 0
        except Exception as e:
            logger.error(f"Error in isInL2DArea: {e}")
            return False

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()
        
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True
            self.last_mouse_x = event.position().x()
            self.last_mouse_y = event.position().y()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = False

    def mouseMoveEvent(self, event):
        x = event.position().x()
        y = event.position().y()

        if self.live2d_model and self.right_button_pressed:
            norm_x = (x / self.width()) * 2 - 1
            norm_y = (y / self.height()) * 2 - 1

            angle_x = norm_x * 30
            angle_y = norm_y * 30

            eye_x = norm_x * 1.0
            eye_y = norm_y * 1.0

            self.live2d_model.SetParameterValue("ParamAngleX", angle_x)
            self.live2d_model.SetParameterValue("ParamAngleY", -angle_y)
            self.live2d_model.SetParameterValue("ParamEyeBallX", eye_x)
            self.live2d_model.SetParameterValue("ParamEyeBallY", -eye_y)

        if self.dragging:
            dx_mouse = x - self.last_mouse_x
            dy_mouse = y - self.last_mouse_y

            scale_x = 2.0 / self.width()
            scale_y = 2.0 / self.height()
            scale_xy = min(scale_x, scale_y)

            self.dx += dx_mouse * scale_xy * self.drag_sensitivity
            self.dy -= dy_mouse * scale_xy * self.drag_sensitivity

            self.live2d_model.SetOffset(self.dx, self.dy)

            self.last_mouse_x = x
            self.last_mouse_y = y

        self.update()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        delta = event.angleDelta().y()
        scale_step = 0.1 if delta > 0 else -0.1
        new_scale = self.scale + scale_step

        new_scale = max(self.min_scale, min(self.max_scale, new_scale))

        self.scale = new_scale
        if self.live2d_model:
            self.live2d_model.SetScale(self.scale)
        
        self.update()

    def update_live2d_emotion(self):
        """
        Updates the emotion of the Live2D model based on the current character's emotion.
        """
        if self.live2d_model:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]

            conversation_method = character_info["conversation_method"]
        
            if conversation_method != "Character AI":
                current_chat = character_info["current_chat"]
                chats = character_info.get("chats", {})
                current_emotion = chats[current_chat]["current_emotion"]
            else:
                current_emotion = character_info["current_emotion"]

            self.live2d_model.SetExpression(current_emotion)
        else:
            logger.error('Emotion not detected')

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        levels = {0: "DEBUG", 1: "LOG", 2: "WARN", 3: "ERROR"}
        level_name = levels.get(level, f"LEVEL{level}")
        logger.debug(f"[JS Console] {level_name} in {source_id} (line {line_number}): {message}")

class ServerThread(threading.Thread):
    def __init__(self, port=8002):
        super().__init__()
        self.port = port
        self.daemon = True
        self.server = None
        self.running = False

    def run(self):
        try:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            os.chdir(project_root)
            
            handler = SimpleHTTPRequestHandler
            self.server = TCPServer(("", self.port), handler)
            self.running = True
            logger.info(f"VRM HTTP server started on port {self.port}")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Error starting VRM HTTP server: {e}")
            self.running = False

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            logger.info("VRM HTTP server stopped")

class VRMWidget_NoGUI(QWidget):
    vrm_loaded = pyqtSignal(bool)
    vrm_load_error = pyqtSignal(str)

    def __init__(self, parent=None, vrm_model_path=None, character_name=None, 
                 model_background_type=0, model_background_color=0, model_background_image=None,
                 current_emotion="neutral", running_vrm_no_gui=None, vrm_no_gui_task=None):
        super().__init__()
        
        if vrm_model_path is None:
            logger.error("vrm_model_path must be provided")
            raise ValueError("vrm_model_path must be provided")
            
        self.character_name = character_name
        self.parent = parent
        self.vrm_model_path = vrm_model_path
        self.model_background_type = model_background_type
        self.model_background_color = model_background_color
        self.model_background_image = model_background_image
        self.current_emotion = current_emotion
        self.running_vrm_no_gui = running_vrm_no_gui
        self.vrm_no_gui_task = vrm_no_gui_task

        self.setWindowTitle(f"Soul of Waifu System - Call with {character_name}")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self.server_thread = ServerThread(port=8002)
        self.server_thread.start()

        self.vrm_webview = QWebEngineView()
        self.vrm_webview.setPage(CustomWebEnginePage(self.vrm_webview))

        self.vrm_webview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.vrm_webview.setStyleSheet("background: transparent;")

        self.vrm_webview.settings().setAttribute(
            self.vrm_webview.settings().WebAttribute.WebGLEnabled, True
        )
        self.vrm_webview.settings().setAttribute(
            self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True
        )
        self.vrm_webview.settings().setAttribute(
            self.vrm_webview.settings().WebAttribute.PluginsEnabled, True
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.vrm_webview)

        self.is_vrm_loaded = False
        self.load_attempts = 0
        self.max_load_attempts = 10

        self.resize(500, 500)

        self.dragging = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        self.vrm_webview.page().loadFinished.connect(self.on_load_finished)
        self.vrm_loaded.connect(self.on_vrm_loaded)
        self.vrm_load_error.connect(self.handle_load_error)

        self.load_vrm_model()
    
    def load_vrm_model(self):
        html_url = f"http://localhost:8002/app/utils/emotions/vrm_module.html"
        
        if self.vrm_model_path:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            model_rel_path = os.path.relpath(self.vrm_model_path, project_root)
            safe_path = model_rel_path.replace("\\", "/")
            html_url += f"?model=/{safe_path}"
            logger.info(f"Loading VRM model from: {self.vrm_model_path}")
        else:
            logger.error("VRM model path is not specified")
            self.vrm_load_error.emit("VRM model path is not specified")
            return
            
        self.vrm_webview.load(QtCore.QUrl(html_url))
    
    def on_load_finished(self, ok):
        if ok:
            logger.info("VRM module HTML loaded successfully")
            self.check_vrm_loaded()
        else:
            logger.error("Failed to load VRM module HTML")
            self.vrm_load_error.emit("Failed to load VRM module HTML")
    
    def check_vrm_loaded(self):
        self.vrm_webview.page().runJavaScript(
            "window.vrmLoaded",
            self.handle_vrm_loaded_check
        )
    
    def handle_vrm_loaded_check(self, is_loaded):
        if is_loaded:
            logger.info("VRM model loaded successfully")
            self.is_vrm_loaded = True
            self.vrm_loaded.emit(True)

            self.set_background(self.model_background_type, 
                               self.model_background_color, 
                               self.model_background_image)
            self.set_expression(self.current_emotion)
            self.play_animation(self.current_emotion)
        else:
            self.load_attempts += 1
            if self.load_attempts < self.max_load_attempts:
                logger.info(f"VRM model not loaded yet, attempt {self.load_attempts}/{self.max_load_attempts}")
                QtCore.QTimer.singleShot(500, self.check_vrm_loaded)
            else:
                logger.error("Failed to load VRM model after maximum attempts")
                self.vrm_load_error.emit("Failed to load VRM model after maximum attempts")
    
    def on_vrm_loaded(self, is_loaded):
        logger.info("VRM model fully loaded and ready")
    
    def handle_load_error(self, error_message):
        logger.error(f"VRM load error: {error_message}")
    
    def set_background(self, bg_type, color=None, image=None):
        if not self.is_vrm_loaded:
            logger.warning("Cannot set background: VRM model not loaded yet")
            return
            
        if bg_type == 0 and color is not None:
            bg_colors = {
                0: "0x000000",
                1: "0x1A202F",
                2: "0x2C1A22",
                3: "0x222B24",
                4: "0x2E2232",
                5: "0x292929"
            }
            color_hex = bg_colors.get(color, "0x000000")
            self.vrm_webview.page().runJavaScript(f"setBackground('color', {color_hex})")
        elif bg_type == 1 and image is not None:
            safe_path = image.replace("\\", "/")
            self.vrm_webview.page().runJavaScript(f"setBackground('image', null, '/{safe_path}')")
        else:
            self.vrm_webview.page().runJavaScript("setBackground('transparent')")
    
    def set_expression(self, emotion):
        if not self.is_vrm_loaded:
            return
            
        expression_map = {
            'anger': 'angry',
            'disapproval': 'angry',
            'annoyance': 'angry',
            'disgust': 'angry',
            'admiration': 'happy',
            'amusement': 'happy',
            'approval': 'happy',
            'desire': 'happy',
            'gratitude': 'happy',
            'love': 'happy',
            'optimism': 'happy',
            'pride': 'happy',
            'joy': 'happy',
            'neutral': 'neutral',
            'caring': 'relaxed',
            'relief': 'relaxed',
            'disappointment': 'sad',
            'grief': 'sad',
            'remorse': 'sad',
            'sadness': 'sad',
            'confusion': 'surprised',
            'curiosity': 'surprised',
            'embarrassment': 'surprised',
            'fear': 'surprised',
            'nervousness': 'surprised',
            'realization': 'surprised',
            'surprise': 'surprised'
        }
        
        expression = expression_map.get(emotion, 'neutral')
        self.vrm_webview.page().runJavaScript(f"setExpression('{expression}')")
    
    def play_animation(self, emotion):
        if not self.is_vrm_loaded:
            return
            
        animation_map = {
            "admiration": "admiration.fbx",
            "amusement": "amusement.fbx", 
            "anger": "anger.fbx",
            "annoyance": "annoyance.fbx",
            "approval": "approval.fbx",
            "caring": "caring.fbx",
            "confusion": "confusion.fbx",
            "curiosity": "curiosity.fbx",
            "desire": "desire.fbx",
            "disappointment": "disappointment.fbx",
            "disapproval": "disapproval.fbx",
            "disgust": "disgust.fbx",
            "embarrassment": "embarrassment.fbx",
            "excitement": "excitement.fbx",
            "fear": "fear.fbx",
            "gratitude": "gratitude.fbx",
            "grief": "grief.fbx",
            "love": "love.fbx",
            "nervousness": "nervousness.fbx",
            "neutral": "neutral.fbx",
            "optimism": "optimism.fbx",
            "pride": "pride.fbx",
            "realization": "realization.fbx",
            "relief": "relief.fbx",
            "remorse": "remorse.fbx",
            "surprise": "surprise.fbx",
            "joy": "joy.fbx",
            "sadness": "sadness.fbx"
        }
        
        anim_file = animation_map.get(emotion, "neutral.fbx")
        animation_url = f"/app/utils/emotions/vrm/expressions/{anim_file}"
        self.vrm_webview.page().runJavaScript(f"loadFBX('{animation_url}')")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_mouse_x = event.globalX()
            self.last_mouse_y = event.globalY()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            dx = event.globalX() - self.last_mouse_x
            dy = event.globalY() - self.last_mouse_y
            self.move(self.x() + dx, self.y() + dy)
            self.last_mouse_x = event.globalX()
            self.last_mouse_y = event.globalY()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
    
    def stop_live2d_no_gui_tasks(self):
        self.running_live2d_no_gui = False

        if hasattr(self, "live2d_no_gui_task") and self.live2d_no_gui_task:
            self.live2d_no_gui_task.cancel()
            self.live2d_no_gui_task = None

    def cleanup(self):
        if hasattr(self, "vrm_no_gui_task") and self.vrm_no_gui_task and not self.vrm_no_gui_task.done():
            try:
                self.vrm_no_gui_task.cancel()
            except Exception as e:
                logger.warning(f"Error when stopping an async task: {e}")

        if hasattr(self, "running_vrm_no_gui"):
            self.running_vrm_no_gui = False

        if hasattr(self, "vrm_webview"):
            try:
                self.vrm_webview.page().loadFinished.disconnect()

                self.vrm_webview.setHtml("")

                if self.vrm_webview.parent():
                    layout = self.vrm_webview.parent().layout()
                    if layout:
                        layout.removeWidget(self.vrm_webview)

                self.vrm_webview.deleteLater()
                self.vrm_webview = None
                logger.info("QWebEngineView is cleared")
            except Exception as e:
                logger.error(f"Error during cleaning QWebEngineView: {e}")
        logger.info("Cleaning of VRM resources is completed!")
    
    def closeEvent(self, event):
        logger.info("Closing VRM widget...")
        
        self.cleanup()
        
        if self.parent:
            self.parent.show()

        super().closeEvent(event)
