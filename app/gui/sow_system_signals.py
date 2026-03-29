import re
import os
import json
import yaml
import uuid
import time
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
from app.utils.text_to_speech import ElevenLabs, XTTSv2_SOW_System, EdgeTTS, KokoroTTS_SOW_System, SileroTTS_SOW_System, TTSWorker
from app.utils.speech_to_text import AudioInputWorker, STTWorker

import sys
import ctypes
from ctypes import wintypes
from datetime import datetime
import random

if sys.platform == "win32":
    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.UINT),
            ("dwTime", wintypes.UINT)
        ]
    
    def _get_system_idle_time_ms() -> int:
        lii = _LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return ctypes.windll.kernel32.GetTickCount64() - lii.dwTime
        return 0

logger = logging.getLogger("SOW System Interface Signals")

class StateSignaler(QtCore.QObject):
    state_changed_signal = pyqtSignal(str)

class Soul_Of_Waifu_System(QtCore.QObject):
    """
    Soul of Waifu System - Main controller class.
    """
    def __init__(self, parent, character_name):
        """
        Initializes the Soul of Waifu System for a specific character.
        """
        super(Soul_Of_Waifu_System, self).__init__(parent)

        self.ui = SOW_System(parent=None)
        self.ui.setupUi()
        self.character_name = character_name
        self.parent_window = parent

        logger.info(f"CHARACTER NAME = {self.character_name}, {character_name}")
        
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

        # Initialize AI clients and other utilities
        self.character_ai_client = CharacterAI()
        self.mistral_ai_client = MistralAI()
        self.open_ai_client = OpenAI()
        self.local_ai_client = LocalAI()
        
        self.eleven_labs_client = ElevenLabs()
        self.xttsv2_client = XTTSv2_SOW_System()
        self.edge_tts_client = EdgeTTS()
        self.kokoro_client = KokoroTTS_SOW_System()
        self.silero_client = SileroTTS_SOW_System()

        self.translator = Translator()
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

        self.ui.close_app_btn.clicked.connect(self.safe_close)

        # ======================================
        self.audio_worker = None 
        self.input_device_index = self.configuration_settings.get_main_setting("input_device")

        self.interaction_state = "STOPPED" # STOPPED, LISTENING, PROCESSING, SPEAKING
        self.is_interrupted = False
        self.llm_task = None

        self.stt_worker = STTWorker(model_size="small", device="cuda", compute_type="float16")
        self.stt_worker.text_ready_signal.connect(self.on_user_speech_recognized)
        self.stt_worker.start()

        self.tts_worker = TTSWorker(self.current_text_to_speech, character_name, self.elevenlabs_voice_id, language="en")
        self.tts_worker.playback_worker.queue_empty_signal.connect(self.on_audio_finished)
        self.tts_worker.playback_worker.lipsync_signal.connect(self.update_avatar_lips)
        self.tts_worker.start()

        self._state_signaler = StateSignaler()
        self._state_signaler.state_changed_signal.connect(self._update_state_ui)

        # === Desktop Companion Systems ===
        self._init_companion_variables()
        
    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
    
    def set_state(self, state):
        self.interaction_state = state
        self._state_signaler.state_changed_signal.emit(state)

    def _update_state_ui(self, state):
        """Update UI based on current interaction state."""
        state_styles = {
            "STOPPED": ("rgb(70, 70, 70)", "Ready"),
            "LISTENING": ("rgb(46, 204, 113)", "Listening..."),
            "PROCESSING": ("rgb(241, 196, 15)", "Thinking..."),
            "SPEAKING": ("rgb(52, 152, 219)", "Speaking...")
        }
        
        color, text = state_styles.get(state, ("rgb(70, 70, 70)", "Ready"))
        
        if hasattr(self.ui, 'voice_indicator'):
            self.ui.voice_indicator.setStyleSheet(f"""
                background-color: {color}; 
                border-radius: 5px;
            """)
        
        if hasattr(self.ui, 'status_label'):
            self.ui.status_label.setText(text)
        
        if hasattr(self.ui, 'set_voice_level'):
            if state == "SPEAKING":
                self.ui.set_voice_level(0.5)
            else:
                self.ui.set_voice_level(0.0)
        
        try:
            current_mode = self.configuration_characters.load_configuration()["character_list"][self.character_name]["current_sow_system_mode"]
            if current_mode == "VRM" and hasattr(self, 'vrm_webview'):
                self.vrm_webview.page().runJavaScript(f"if (typeof window.setAppState !== 'undefined') window.setAppState('{state}');")
        except Exception as e:
            logger.error(f"Failed to send state to VRM: {e}")
    
    def toggle_voice_interaction(self, character_name):
        if self.interaction_state == "STOPPED":
            logger.info("▶️ Starting Voice Interaction Pipeline...")
            
            if self.audio_worker is None or not self.audio_worker.isRunning():
                self.audio_worker = AudioInputWorker(input_device_index=self.input_device_index)
                self.audio_worker.audio_packet_ready.connect(self.stt_worker.add_audio)
                self.audio_worker.voice_detected_signal.connect(self.interrupt_ai)
                self.audio_worker.volume_signal.connect(self.ui.waveform_widget.push_volume)
                self.audio_worker.start()
            
            self.ui.pushButton_play.setIcon(self.icon_stop)
            self.set_state("LISTENING")
            
        else:
            logger.info("Stopping Voice Interaction Pipeline...")
            self.interrupt_ai()
            
            if hasattr(self, 'audio_worker') and self.audio_worker:
                try:
                    self.audio_worker.audio_packet_ready.disconnect()
                    self.audio_worker.voice_detected_signal.disconnect()
                except TypeError:
                    pass
                
                self.audio_worker.stop()
                
                self.audio_worker.deleteLater()
                self.audio_worker = None
            
            self.ui.pushButton_play.setIcon(self.icon_play)
            self.set_state("STOPPED")
    
    def stop_all_workers(self):
        logger.info("Stopping all audio streams...")
        
        if hasattr(self, 'audio_worker') and self.audio_worker:
            self.audio_worker.stop()
            self.audio_worker.deleteLater()
            
        if hasattr(self, 'stt_worker') and self.stt_worker:
            self.stt_worker.stop()
            self.stt_worker.deleteLater()
            
        if hasattr(self, 'tts_worker') and self.tts_worker:
            self.tts_worker.stop()
            self.tts_worker.deleteLater()

    def safe_close(self):
        self.stop_all_workers()
        self.ui.stop_call_timer()

        if hasattr(self, 'server_thread') and self.server_thread is not None:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.stop()
                    self.server_thread.join(timeout=2)
                    logger.info("VRM server thread stopped")
            except Exception as e:
                logger.error(f"Error stopping server thread: {e}")

        self.ui.close()

    def interrupt_ai(self):
        if self.interaction_state == "STOPPED":
            return

        logger.info("🛑 INTERRUPT DETECTED! Stop the processes...")

        self.is_interrupted = True
        if self.llm_task and not self.llm_task.done():
            self.llm_task.cancel()
            logger.info("The LLM stop signal has been sent")

        if hasattr(self, 'tts_worker') and self.tts_worker:
            self.tts_worker.clear_queue()
            logger.info("The TTS and player queues are cleared")

        self.set_state("LISTENING")
    
    def on_audio_finished(self):
        if self.interaction_state == "SPEAKING" and not self.is_interrupted:
            logger.info("✅ Player has finished playback. Return to listening mode...")
            self.set_state("LISTENING")
    
    def update_avatar_lips(self, mouth_value):
        """Update avatar lip sync and voice indicator animation."""
        current_mode = self.configuration_characters.load_configuration()["character_list"][self.character_name]["current_sow_system_mode"]

        # 1. LIVE2D
        if current_mode == "Live2D Model":
            if hasattr(self, 'live2d_no_gui') and self.live2d_no_gui:
                 if self.live2d_no_gui.live2d_model:
                    self.live2d_no_gui.live2d_model.SetParameterValue("ParamMouthOpenY", mouth_value)
            elif hasattr(self, 'live2d_openGL_widget') and self.live2d_openGL_widget:
                if self.live2d_openGL_widget.live2d_model:
                    self.live2d_openGL_widget.live2d_model.SetParameterValue("ParamMouthOpenY", mouth_value)
            
        # 2. VRM
        elif current_mode == "VRM":
            if hasattr(self, 'vrm_no_gui') and self.vrm_no_gui:
                if self.vrm_no_gui.vrm_webview:
                    self.vrm_no_gui.vrm_webview.page().runJavaScript(f"setMouthOpen({mouth_value});")
            elif hasattr(self, 'vrm_webview') and self.vrm_webview:
                self.vrm_webview.page().runJavaScript(f"setMouthOpen({mouth_value});")
    
    async def initialize_sow_system(self, character_name):
        self.parent_window.setVisible(False)
        
        self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Waiting for conversation to start..."))

        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        model_background_image = self.configuration_settings.get_main_setting("model_background_image")

        live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
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
                max_words = 7
                if character_title:
                    words = character_title.split()
                    if len(words) > max_words:
                        cropped_description = " ".join(words[:max_words]) + "..."
                        self.ui.character_description_label.setText(cropped_description)
                        self.ui.character_description_label.setWordWrap(True)
                    else:
                        cropped_description = character_title
                        self.ui.character_description_label.setText(cropped_description)
                        self.ui.character_description_label.setWordWrap(True)
            
            if hasattr(self.ui, 'character_avatar_label'):
                if character_avatar and os.path.exists(character_avatar):
                    pixmap = QtGui.QPixmap(character_avatar)
                    if not pixmap.isNull():
                        self.ui.character_avatar_label.setPixmap(pixmap)
                        
            if hasattr(self.ui, 'status_label'):
                self.ui.status_label.setText(self.translations.get("sow_system_status_stop", "Ready"))
            
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

                if hasattr(self, 'server_thread') and self.server_thread is not None:
                    if self.server_thread.is_alive():
                        logger.info("Stopping existing VRM server before creating new one...")
                        self.server_thread.stop()
                        self.server_thread.join(timeout=2)

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
            
            self.ui.pushButton_play.clicked.connect(lambda: self.toggle_voice_interaction(character_name))

            if current_sow_system_mode == "Nothing" or current_sow_system_mode == "Expressions Images":
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_avatar)
            elif current_sow_system_mode == "Live2D Model":
                self.ui.stackedWidget_main.setCurrentWidget(self.ui.page_live2d_model)
            elif current_sow_system_mode == "VRM":
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
            
            self.ui.start_call_timer()
            
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
            
            try:
                await self.initialize_sow_system_no_gui(current_sow_system_mode)
            except Exception as e:
                return

    def on_user_speech_recognized(self, text):
        logger.info(f"UI received text: {text}")

        if self.interaction_state != "LISTENING":
            return

        add_msg_task = asyncio.create_task(
            self.add_message(self.character_name, text, is_user=True, message_id=None)
        )
        
        self.llm_task = asyncio.create_task(self.process_llm_response(text, add_msg_task))

    async def process_llm_response(self, user_text, user_message_task):
        self.set_state("PROCESSING")
        self.is_interrupted = False

        user_message_container = await user_message_task
        user_message_id = user_message_container["message_id"]

        character_answer_container = await self.add_message(self.character_name, "💭 Thinking...", is_user=False, message_id=None)
        character_answer_label = character_answer_container["label"]
        character_answer_id = character_answer_container["message_id"]

        char_data = self.configuration_characters.load_configuration()
        char_info = char_data["character_list"][self.character_name]
        conversation_method = char_info["conversation_method"]
        current_sow_system_mode = char_info.get("current_sow_system_mode", "Nothing")

        current_persona = char_info.get("selected_persona")
        personas_data = self.configuration_settings.get_user_data("personas")
        user_name = personas_data.get(current_persona, {}).get("user_name", "User") if current_persona and current_persona != "None" else "User"
        user_description = personas_data.get(current_persona, {}).get("user_description", "") if current_persona and current_persona != "None" else ""

        full_text = ""
        sentence_buffer = ""
        current_cai_text_length = 0

        translator_engine = self.configuration_settings.get_main_setting("translator") # 0-Off, 1-Google, 2-Yandex
        target_lang = self.configuration_settings.get_main_setting("target_language") # 0-RU
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        try:
            self.llm_task = asyncio.current_task()
            
            context_messages = []
            if conversation_method != "Character AI":
                current_chat = char_info["current_chat"]
                chat_history = char_info.get("chats", {}).get(current_chat, {}).get("chat_history", [])
                for msg in chat_history:
                    if msg.get("user"): context_messages.append({"role": "user", "content": msg["user"].strip()})
                    if msg.get("character"): context_messages.append({"role": "assistant", "content": msg["character"].strip()})
            
            match conversation_method:
                case "Local LLM":
                    stream_generator = self.local_ai_client.send_message(
                        context_messages, user_text, self.character_name, user_name, user_description
                    )
                case "Mistral AI":
                    stream_generator = self.mistral_ai_client.send_message(
                        context_messages, user_text, self.character_name, user_name, user_description
                    )
                case "Open AI" | "OpenRouter":
                    stream_generator = self.open_ai_client.send_message(
                        conversation_method, context_messages, user_text, 
                        self.character_name, user_name, user_description
                    )
                case "Character AI":
                    char_id = char_info.get("character_id")
                    chat_id = char_info.get("chat_id")
                    stream_generator = self.character_ai_client.send_message(
                        char_id, chat_id, user_text
                    )
                case _:
                    raise ValueError(f"Unknown method: {conversation_method}")
            
            async for data_chunk in stream_generator:
                if self.is_interrupted:
                    logger.info("🛑 LLM generation is interrupted by the user")
                    break

                chunk = ""

                if conversation_method == "Character AI":
                    new_full_text = data_chunk.get_primary_candidate().text
                    chunk = new_full_text[current_cai_text_length:]
                    current_cai_text_length = len(new_full_text)
                else:
                    chunk = data_chunk
                    if conversation_method == "OpenRouter":
                        chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk

                if not chunk:
                    continue

                full_text += chunk
                sentence_buffer += chunk

                display_text = full_text
                if display_text.startswith(f"{self.character_name}:"):
                    display_text = display_text[len(f"{self.character_name}:"):].lstrip()

                display_html = self.markdown_to_html(display_text)
                display_html = display_html.replace("{{user}}", user_name).replace("{{char}}", self.character_name)
                character_answer_label.setText(display_html)
                
                if current_sow_system_mode in ["Nothing", "Expressions Images", "Live2D Model", "VRM"]:
                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                await asyncio.sleep(0.01)

                match = re.search(r'([.!?\n]+)', sentence_buffer)
                if match:
                    split_idx = match.end()
                    sentence = sentence_buffer[:split_idx].strip()
                    
                    clean_sentence = sentence.replace("*", "").replace("_", "").replace("~", "")
                    
                    if len(clean_sentence) > 2:
                        logger.info(f"🗣️ Sending to TTS: {clean_sentence}")
                        if self.interaction_state != "SPEAKING":
                            self.set_state("SPEAKING")
                        
                        self.tts_worker.add_text(clean_sentence)
                    
                    sentence_buffer = sentence_buffer[split_idx:]
        
        except asyncio.CancelledError:
            logger.info("⚠️ The LLM task has been cancelled externally (Interrupt).")
            self.is_interrupted = True
        
        except Exception as e:
            logger.error(f"❌ Error when generating LLM: {e}")

        if self.is_interrupted:
            full_text += " ... [Interrupted]"
            display_html = self.markdown_to_html(full_text).replace("{{user}}", user_name).replace("{{char}}", self.character_name)
            character_answer_label.setText(display_html)
            sentence_buffer = ""

        if not self.is_interrupted and len(sentence_buffer.strip()) > 1:
            clean_tail = sentence_buffer.strip().replace("*", "").replace("_", "")
            logger.info(f"🗣️ Sending the remaining text to TTS: {clean_tail}")
            if self.interaction_state != "SPEAKING":
                self.set_state("SPEAKING")
            self.tts_worker.add_text(clean_tail)

        if translator_engine in [1, 2] and translator_mode in [0, 2] and target_lang == 0:
            engine_name = "google" if translator_engine == 1 else "yandex"
            try:
                translated_html = self.translator.translate(display_html, engine_name, 'ru')
                character_answer_label.setText(translated_html)
            except Exception as e:
                logger.error(f"Error translating the finished text: {e}")
        
        self.configuration_characters.add_message_to_config(self.character_name, "User", True, user_text, user_message_id)
        self.configuration_characters.add_message_to_config(self.character_name, self.character_name, False, full_text, character_answer_id)

        if current_sow_system_mode in ["Expressions Images", "Live2D Model"]:
            asyncio.create_task(self.detect_emotion(self.character_name, full_text))
        elif current_sow_system_mode == "VRM":
            asyncio.create_task(self.detect_emotion(self.character_name, full_text, True))
    
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

    def draw_circle_avatar(self, avatar_path, current_sow_system_mode):
        target_size = 54
        label_size = 54
        self.ui.character_avatar_label.setGeometry(5, 5, 54, 54)
        
        source_pixmap = QPixmap(avatar_path)
        if source_pixmap.isNull():
            source_pixmap = QPixmap("app/gui/icons/logotype.png")
        
        scaled_pixmap = source_pixmap.scaled(
            target_size, target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        
        crop_x = (scaled_pixmap.width() - target_size) // 2
        crop_y = (scaled_pixmap.height() - target_size) // 2
        square_pixmap = scaled_pixmap.copy(crop_x, crop_y, target_size, target_size)
        
        final_pixmap = QPixmap(target_size, target_size)
        final_pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        
        painter = QPainter(final_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, target_size, target_size)
        painter.setClipPath(path)
        
        painter.drawPixmap(0, 0, square_pixmap)
        painter.end()
        
        self.ui.character_avatar_label.setPixmap(final_pixmap)
        self.ui.character_avatar_label.setFixedSize(label_size, label_size)
        self.ui.character_avatar_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        
        if current_sow_system_mode == "Nothing" and hasattr(self.ui, 'avatar_label'):
            large_target = 200
            large_scaled = source_pixmap.scaled(
                large_target, large_target,
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            
            crop_x = (large_scaled.width() - large_target) // 2
            crop_y = (large_scaled.height() - large_target) // 2
            large_square = large_scaled.copy(crop_x, crop_y, large_target, large_target)
            
            large_final = QPixmap(large_target, large_target)
            large_final.fill(QtCore.Qt.GlobalColor.transparent)
            
            painter = QPainter(large_final)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            
            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, large_target, large_target)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, large_square)
            painter.end()
            
            self.ui.avatar_label.setPixmap(large_final)
            self.ui.avatar_label.setFixedSize(large_target, large_target)
            self.ui.avatar_label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
    
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
        message_container.setContentsMargins(6, 3, 6, 3)

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
                raw_pixmap = QPixmap(self.user_avatar)
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
                        min-width: 220px;
                        max-width: 90%;
                        white-space: pre-line;
                    }
                """)
                raw_pixmap = QPixmap(character_avatar)

            if raw_pixmap.isNull():
                raw_pixmap = QPixmap("app/gui/icons/logotype.png")

            target_size = 90
            label_size = 35
            
            scaled_pixmap = raw_pixmap.scaled(
                target_size, target_size,
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

            crop_x = (scaled_pixmap.width() - target_size) // 2
            crop_y = (scaled_pixmap.height() - target_size) // 2
            square_pixmap = scaled_pixmap.copy(crop_x, crop_y, target_size, target_size)

            final_avatar_pixmap = QPixmap(target_size, target_size)
            final_avatar_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(final_avatar_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            path = QtGui.QPainterPath()
            path.addEllipse(0, 0, target_size, target_size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, square_pixmap)
            painter.end()

            avatar_label = QLabel()
            avatar_label.setPixmap(final_avatar_pixmap)
            avatar_label.setFixedSize(label_size, label_size)
            avatar_label.setScaledContents(True)
            avatar_label.setStyleSheet("background: transparent; border: none;")

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
            if hasattr(self, 'vrm_no_gui') and self.vrm_no_gui:
                self.vrm_no_gui.set_expression(emotion)
                self.vrm_no_gui.play_animation(emotion)
            elif hasattr(self, 'vrm_webview') and self.vrm_webview:
                self.set_expression_vrm(emotion) 
                self.play_vrm_animation(emotion)

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
        Desktop Companion init
        """
        character_data = self.configuration_characters.load_configuration()
        character_info = character_data["character_list"][self.character_name]
        
        def toggle_voice_callback():
            self.toggle_voice_interaction(self.character_name)

        if current_sow_system_mode == "Live2D Model":
            live2d_model_folder = character_info["live2d_model_folder"]
            model_json_path = self.find_model_json(live2d_model_folder)
            
            if model_json_path:
                self.update_model_json(model_json_path, self.emotion_resources)
                
                self.live2d_no_gui = Live2DWidget_NoGUI(
                    parent=self.parent_window, 
                    model_path=model_json_path, 
                    character_name=self.character_name,
                    toggle_voice_cb=toggle_voice_callback,
                    sow_system_ref=self
                )
                self.live2d_no_gui.show()

                self._start_companion_systems()
                
                self.toggle_voice_interaction(self.character_name)

        elif current_sow_system_mode == "VRM":
            vrm_model_path = character_info["vrm_model_file"]
            if vrm_model_path:
                current_chat = character_info["current_chat"]
                chats = character_info.get("chats", {})
                current_emotion = chats[current_chat]["current_emotion"]

                self.vrm_no_gui = VRMWidget_NoGUI(
                    parent=self.parent_window,
                    vrm_model_path=vrm_model_path,
                    character_name=self.character_name,
                    current_emotion=current_emotion,
                    toggle_voice_cb=toggle_voice_callback,
                    sow_system_ref=self
                )
                self.vrm_no_gui.show()
                
                self._start_companion_systems()

                self.toggle_voice_interaction(self.character_name)
            else:
                logger.error("VRM model path not specified for character")
    
    def _init_companion_variables(self):
        """Initialize Desktop Companion variables."""
        # Eye Tracker
        self._eye_tracker_timer = QtCore.QTimer(self)
        self._eye_tracker_timer.timeout.connect(self._update_eye_tracking)
        self._eye_update_interval = 100
        self._current_eye_x = 0.0
        self._current_eye_y = 0.0
        self._eye_smoothing = 0.15
        self._eye_max_rotation = 0.7
        
        # Idle Scheduler
        self._idle_timer = QtCore.QTimer(self)
        self._idle_timer.timeout.connect(self._check_idle_action)
        self._idle_timer_interval = 15000
        self._idle_time_ms = 0
        self._last_interaction_timestamp = datetime.now()
        self._idle_actions = {
            "blink": {"weight": 30, "cooldown": 2000, "last": 0},
            "look_away": {"weight": 25, "cooldown": 5000, "last": 0},
            "head_turn": {"weight": 20, "cooldown": 8000, "last": 0},
            "body_shift": {"weight": 10, "cooldown": 15000, "last": 0},
            "expression": {"weight": 10, "cooldown": 20000, "last": 0},
            "stretch": {"weight": 3, "cooldown": 60000, "last": 0},
            "nothing": {"weight": 2, "cooldown": 0, "last": 0}
        }
        
        # Sleep Manager
        self._sleep_check_timer = QtCore.QTimer(self)
        self._sleep_check_timer.timeout.connect(self._check_sleep_state)
        self._sleep_check_interval = 10000
        self._sleep_threshold_ms = 5 * 60 * 1000
        self._drowsy_threshold_ms = 2 * 60 * 1000
        self._is_sleeping = False
        self._is_drowsy = False
        self._sleep_animation_timer = QtCore.QTimer(self)
        self._sleep_animation_timer.timeout.connect(self._sleep_animation_tick)

        # Time Context
        self._time_context_timer = QtCore.QTimer(self)
        self._time_context_timer.timeout.connect(self._check_time_context)
        self._time_context_interval = 60000
        self._current_time_context = None
        self._has_greeted = False

        # Proactive Speaker
        self._proactive_timer = QtCore.QTimer(self)
        self._proactive_timer.setSingleShot(True)
        self._proactive_timer.timeout.connect(self._trigger_proactive)
        self._proactive_min_interval = 15 * 60 * 1000
        self._proactive_max_interval = 40 * 60 * 1000
        self._last_proactive_time = None

        # Interaction / drag physics
        self._drag_velocity_x = 0.0
        self._drag_velocity_y = 0.0
        self._drag_last_pos = None
        self._drag_last_time = 0

        # Layered cursor tracking
        self._current_head_x = 0.0
        self._current_head_y = 0.0
        self._current_body_x = 0.0
        self._eye_update_interval = 50          # 20fps for smooth tracking
        self._head_smoothing   = 0.07           # medium speed
        self._body_smoothing   = 0.03           # slow
        self._tracking_speed_preset = "Normal"  # "Slow"/"Normal"/"Fast"

        # Active window reaction system
        self._active_window_timer = QtCore.QTimer(self)
        self._active_window_timer.timeout.connect(self._check_active_window)
        self._active_window_check_interval = 45000
        self._last_active_window = ""
        self._last_window_reaction_time = None
        self._window_reaction_cooldown_ms = 20 * 60 * 1000
        self._active_window_reactions_enabled = True
        self._app_reaction_times: dict = {}
        self._app_category_cooldown_h = 2.0
        self._startup_grace_period = True
        QtCore.QTimer.singleShot(30000, self._clear_startup_grace)

        self._check_time_context()
        logger.info("Desktop Companion variables initialized")
    
    def _start_companion_systems(self):
        """Start all companion systems."""
        self._eye_tracker_timer.start(self._eye_update_interval)
        self._idle_timer.start(self._idle_timer_interval)
        self._sleep_check_timer.start(self._sleep_check_interval)
        self._time_context_timer.start(self._time_context_interval)
        self._active_window_timer.start(self._active_window_check_interval)
        self._check_time_context()
        self._schedule_next_proactive()
        QtCore.QTimer.singleShot(3500, self._say_startup_greeting)
        logger.info("Companion systems started")

    def _stop_companion_systems(self):
        """Stop all companion systems."""
        self._eye_tracker_timer.stop()
        self._idle_timer.stop()
        self._sleep_check_timer.stop()
        self._time_context_timer.stop()
        self._proactive_timer.stop()
        self._sleep_animation_timer.stop()
        self._active_window_timer.stop()
        logger.info("Companion systems stopped")

    def _get_model(self):
        """Return the active Live2D LAppModel, or None."""
        m = getattr(getattr(self, 'live2d_no_gui', None), 'live2d_model', None)
        if m:
            return m
        return getattr(getattr(self, 'live2d_openGL_widget', None), 'live2d_model', None)

    def _get_webview(self):
        """Return the active VRM QWebEngineView, or None."""
        w = getattr(getattr(self, 'vrm_no_gui', None), 'vrm_webview', None)
        if w:
            return w
        return getattr(self, 'vrm_webview', None)

    def _get_current_mode(self) -> str:
        """Return current_sow_system_mode string."""
        try:
            return self.configuration_characters.load_configuration()[
                "character_list"][self.character_name]["current_sow_system_mode"]
        except Exception:
            return "Nothing"

    # === EYE TRACKER ===
    def _set_tracking_speed(self, preset: str):
        presets = {
            "Slow":   (0.08, 0.04, 0.015),
            "Normal": (0.15, 0.07, 0.03),
            "Fast":   (0.25, 0.13, 0.06),
        }
        es, hs, bs = presets.get(preset, presets["Normal"])
        self._eye_smoothing  = es
        self._head_smoothing = hs
        self._body_smoothing = bs
        self._tracking_speed_preset = preset

    def _update_eye_tracking(self):
        if self._is_sleeping:
            return
        try:
            cursor_pos = QCursor.pos()
            if hasattr(self, 'live2d_no_gui') and self.live2d_no_gui:
                wr = self.live2d_no_gui.geometry()
            elif hasattr(self, 'vrm_no_gui') and self.vrm_no_gui:
                wr = self.vrm_no_gui.geometry()
            elif hasattr(self, 'ui') and self.ui:
                wr = self.ui.geometry()
            else:
                return

            cx = wr.x() + wr.width()  // 2
            cy = wr.y() + wr.height() // 2
            half_w = max(wr.width()  / 2, 1)
            half_h = max(wr.height() / 2, 1)

            raw_x = (cursor_pos.x() - cx) / half_w
            raw_y = -(cursor_pos.y() - cy) / half_h
            eye_tx = max(-self._eye_max_rotation, min(self._eye_max_rotation, raw_x))
            eye_ty = max(-self._eye_max_rotation, min(self._eye_max_rotation, raw_y))

            self._current_eye_x += (eye_tx - self._current_eye_x) * self._eye_smoothing
            self._current_eye_y += (eye_ty - self._current_eye_y) * self._eye_smoothing

            head_tx = eye_tx * 28
            head_ty = eye_ty * 22
            self._current_head_x += (head_tx - self._current_head_x) * self._head_smoothing
            self._current_head_y += (head_ty - self._current_head_y) * self._head_smoothing

            body_tx = self._current_head_x * 0.30
            self._current_body_x += (body_tx - self._current_body_x) * self._body_smoothing

            self._apply_layered_tracking(
                self._current_eye_x, self._current_eye_y,
                self._current_head_x, self._current_head_y,
                self._current_body_x,
            )
        except Exception as e:
            logger.debug(f"Eye tracking error: {e}")

    def _apply_layered_tracking(self, eye_x, eye_y, head_x, head_y, body_x):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamEyeBallX", eye_x)
                    model.SetParameterValue("ParamEyeBallY", eye_y)
                    model.SetParameterValue("ParamAngleX",    head_x)
                    model.SetParameterValue("ParamAngleY",    head_y)
                    model.SetParameterValue("ParamBodyAngleX", body_x)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"updateLookAtTarget({eye_x:.3f}, {eye_y:.3f});")
                    wv.page().runJavaScript(f"setHeadAngle({head_x:.2f}, {head_y:.2f}, 0);")
                    wv.page().runJavaScript(f"setBodyAngle({body_x:.2f}, 0);")
        except Exception as e:
            logger.debug(f"Layered tracking apply error: {e}")

    def _apply_eye_direction(self, x, y):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamEyeBallX", x)
                    model.SetParameterValue("ParamEyeBallY", y)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"updateLookAtTarget({x:.3f}, {y:.3f});")
        except Exception as e:
            logger.debug(f"Apply eye direction error: {e}")
    
    # === IDLE SCHEDULER ===
    def _check_idle_action(self):
        if self.interaction_state != "STOPPED" or self._is_sleeping:
            return
        self._idle_time_ms += self._idle_timer_interval
        current_time = int(datetime.now().timestamp() * 1000)
        available_actions = [(n, d["weight"]) for n, d in self._idle_actions.items() if current_time - d["last"] >= d["cooldown"]]
        if not available_actions:
            return
        total_weight = sum(w for _, w in available_actions)
        r = random.random() * total_weight
        cumulative = 0
        selected = "nothing"
        for name, weight in available_actions:
            cumulative += weight
            if r <= cumulative:
                selected = name
                break
        self._execute_idle_action(selected)
        self._idle_actions[selected]["last"] = current_time
    
    _IDLE_EXPRESSIONS = [
        "neutral", "curiosity", "joy", "admiration", "optimism", "amusement", "relief"
    ]

    def _execute_idle_action(self, action):
        if action == "blink":
            self._companion_blink()
        elif action == "look_away":
            self._companion_look_direction(random.choice(["left", "right", "up", "down"]))
        elif action == "head_turn":
            angle_x = random.uniform(-12, 12)
            angle_y = random.uniform(-6, 6)
            self._set_head_angle(angle_x, angle_y)
            QtCore.QTimer.singleShot(random.randint(2500, 4000), lambda: self._set_head_angle(0, 0))
        elif action == "body_shift":
            shift = random.uniform(-4, 4)
            self._set_body_angle(shift)
            QtCore.QTimer.singleShot(random.randint(2000, 3500), lambda: self._set_body_angle(0))
        elif action == "expression":
            self._companion_set_expression(random.choice(self._IDLE_EXPRESSIONS))
        elif action == "stretch":
            self._companion_stretch()
    
    def _companion_blink(self):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamEyeLOpen", 0)
                    model.SetParameterValue("ParamEyeROpen", 0)
                    QtCore.QTimer.singleShot(110, lambda: (
                        model.SetParameterValue("ParamEyeLOpen", 1),
                        model.SetParameterValue("ParamEyeROpen", 1)
                    ))
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript("triggerBlink();")
        except Exception as e:
            logger.debug(f"Blink error: {e}")
    
    def _companion_look_direction(self, direction):
        dirs = {"left": (-0.5, 0.0), "right": (0.5, 0.0), "up": (0.0, -0.3), "down": (0.0, 0.3)}
        x, y = dirs.get(direction, (0, 0))
        self._apply_eye_direction(x, y)
        QtCore.QTimer.singleShot(random.randint(1000, 2000), lambda: self._apply_eye_direction(self._current_eye_x, self._current_eye_y))
    
    def _set_head_angle(self, x, y):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamAngleX", x)
                    model.SetParameterValue("ParamAngleY", y)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"setHeadAngle({x}, {y}, 0);")
        except Exception as e:
            logger.debug(f"Set head angle error: {e}")
    
    def _set_body_angle(self, x):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamBodyAngleX", x)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"setBodyAngle({x}, 0);")
        except Exception as e:
            logger.debug(f"Set body angle error: {e}")
    
    _VRM_EXPRESSION_MAP = {
        "neutral":       "neutral",
        "joy":           "happy",  "admiration":  "happy",  "amusement":  "happy",
        "approval":      "happy",  "optimism":    "happy",  "gratitude":  "happy",
        "love":          "happy",  "pride":       "happy",  "excitement": "happy",
        "desire":        "happy",
        "relief":        "relaxed", "caring":     "relaxed",
        "sadness":       "sad",    "grief":       "sad",    "disappointment": "sad",
        "remorse":       "sad",
        "anger":         "angry",  "disgust":     "angry",  "annoyance":  "angry",
        "disapproval":   "angry",
        "surprise":      "surprised", "fear":     "surprised", "curiosity": "surprised",
        "confusion":     "surprised", "realization": "surprised",
        "nervousness":   "surprised", "embarrassment": "surprised",
    }

    def _companion_set_expression(self, expression):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetExpression(expression)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    vrm_expr = self._VRM_EXPRESSION_MAP.get(expression, "neutral")
                    wv.page().runJavaScript(f"setExpression('{vrm_expr}');")
        except Exception as e:
            logger.debug(f"Set expression error: {e}")
    
    def _companion_stretch(self):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    try:
                        model.StartMotion("Idle", 0)
                    except Exception:
                        pass
            self._companion_set_expression("relief")
            QtCore.QTimer.singleShot(4000, lambda: self._companion_set_expression("neutral"))
        except Exception as e:
            logger.debug(f"Stretch error: {e}")
    
    # === SLEEP MANAGER ===
    def _check_sleep_state(self):
        idle_time = _get_system_idle_time_ms()
        if idle_time >= self._sleep_threshold_ms:
            if not self._is_sleeping:
                self._go_to_sleep()
        elif idle_time >= self._drowsy_threshold_ms:
            if not self._is_drowsy and not self._is_sleeping:
                self._become_drowsy()
        else:
            if self._is_sleeping:
                self._wake_up()
            elif self._is_drowsy:
                self._stop_drowsy()
    
    def _go_to_sleep(self):
        self._is_sleeping = True
        self._is_drowsy = False
        logger.info("Companion going to sleep")
        self._eye_tracker_timer.stop()
        self._set_eye_open(0.0)
        self._set_head_angle(0, 15)
        self._set_body_angle(0)
        wv = self._get_webview()
        if wv:
            wv.page().runJavaScript("setSleeping(true);")
        self._sleep_animation_timer.start(30000)
    
    def _become_drowsy(self):
        self._is_drowsy = True
        logger.info("Companion is drowsy")
        self._set_eye_open(0.5)
        self._companion_set_expression("relief")

    def _stop_drowsy(self):
        self._is_drowsy = False
        self._set_eye_open(1.0)
        self._companion_set_expression("neutral")
    
    def _wake_up(self):
        self._is_sleeping = False
        self._is_drowsy = False
        logger.info("Companion woke up")
        self._sleep_animation_timer.stop()
        self._eye_tracker_timer.start(self._eye_update_interval)
        self._set_head_angle(0, 0)
        wv = self._get_webview()
        if wv:
            wv.page().runJavaScript("setSleeping(false);")
        QtCore.QTimer.singleShot(300,  lambda: self._set_eye_open(0.3))
        QtCore.QTimer.singleShot(600,  lambda: self._set_eye_open(0.7))
        QtCore.QTimer.singleShot(900,  lambda: self._set_eye_open(1.0))
        QtCore.QTimer.singleShot(1000, lambda: self._companion_set_expression("joy"))
        QtCore.QTimer.singleShot(1200, self._say_wake_reaction)

    def _say_wake_reaction(self):
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self._WAKE_REACTIONS = [
                    "Ah, you're back already!",
                    "Oh, you're here!",
                    "Dozed off a bit...",
                    "Hm? Someone's here.",
                    "Aah, hi!",
                    
                    "Mmm... was I sleeping?",
                    "Oh! You caught me napping~",
                    "Hey there...",
                    "Mmmf... five more minutes... oh, it's you!",
                    "Ahh... hey, you!",
                    
                    "Welcome back! I missed you!",
                    "You're here! My favorite notification~",
                    "Hello, hello! Ready to chat?",
                    "Oh hey! What's up?",
                    "I was just thinking about you!",
                    
                    "Huh? Already time to wake up?",
                    "Back so soon? I like that~",
                    "Oh! Did I keep you waiting?",
                    "Hey stranger! Miss me?",
                    "Mmm... coffee first... oh wait, I don't need that! Hi!",
                ]
            case 1:
                self._WAKE_REACTIONS = [
                    "А, ты уже вернулся!",
                    "О, ты здесь!",
                    "Немного задремала...",
                    "Хм? Кто-то пришёл.",
                    "Аа, привет!",
                    "Ой! Ты застал меня за дремотой~",
                    "С возвращением! Я скучала!",
                    "Ты здесь! Моё любимое уведомление~",
                    "Привет-привет! Готов поболтать?",
                    "О, привет! Как дела?",
                    "Я как раз думала о тебе!",
                    "А? Уже пора просыпаться?",
                    "Так скоро вернулся? Мне нравится~",
                    "Ой! Я тебя заставила ждать?",
                ]

        if hasattr(self, 'tts_worker') and self.tts_worker and self.interaction_state == "STOPPED":
            phrase = random.choice(self._WAKE_REACTIONS)
            self.tts_worker.add_text(phrase)
            self.set_state("SPEAKING")
    
    def _set_eye_open(self, value):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamEyeLOpen", value)
                    model.SetParameterValue("ParamEyeROpen", value)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"setEyeOpen({value}, {value});")
        except Exception as e:
            logger.debug(f"Set eye open error: {e}")
    
    def _sleep_animation_tick(self):
        if not self._is_sleeping:
            return
        if random.random() > 0.5:
            angle = random.uniform(-2, 2)
            self._set_head_angle(angle, 20)
            QtCore.QTimer.singleShot(200, lambda: self._set_head_angle(0, 20))
        else:
            angle = random.uniform(-5, 5)
            self._set_body_angle(angle)
            QtCore.QTimer.singleShot(5000, lambda: self._set_body_angle(0))
    
    # === TIME CONTEXT ===
    def _check_time_context(self):
        hour = datetime.now().hour
        if 5 <= hour < 7: context = "early_morning"
        elif 7 <= hour < 12: context = "morning"
        elif 12 <= hour < 17: context = "afternoon"
        elif 17 <= hour < 21: context = "evening"
        elif 21 <= hour < 24: context = "night"
        else: context = "late_night"
        if context != self._current_time_context:
            self._current_time_context = context
            logger.info(f"Time context: {context}")

    def _say_startup_greeting(self):
        if self._has_greeted:
            return
        self._has_greeted = True
        context = self._current_time_context or "morning"

        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                _FALLBACK_GREETINGS = {
                    "early_morning": [
                        "Good morning! You're up early!",
                        "It's so early... How are you?",
                        "Wow, the sun's barely up! Morning!",
                        "Early bird catches the worm~ Good morning!",
                        "Mmm... it's barely dawn! Hey there...",
                        "You're awake before the birds? Impressive!",
                        "Good morning! The world is still sleeping~",
                    ],
                    "morning": [
                        "Good morning! How did you sleep?",
                        "Morning! Glad to see you.",
                        "Rise and shine! Ready for the day?",
                        "Good morning! Coffee first or chat first?",
                        "Hey! Hope your morning is off to a great start!",
                        "Morning! What's on the agenda today?",
                        "Good morning! You look refreshed!",
                    ],
                    "afternoon": [
                        "Hi! How's your day going?",
                        "Oh, you're here! How are things?",
                        "Afternoon! Taking a break?",
                        "Hey there! Midday check-in~",
                        "Hi! Hope your day is treating you well!",
                        "Afternoon! Anything exciting happening?",
                        "Hey! You caught me in a good mood~",
                    ],
                    "evening": [
                        "Good evening! How was your day?",
                        "Evening! Tired?",
                        "Hey! Time to unwind?",
                        "Good evening! Ready to relax?",
                        "Evening! Did you eat yet?",
                        "Hey there! Long day?",
                        "Good evening! I was waiting for you~",
                    ],
                    "night": [
                        "It's late today.",
                        "It's already night, and you're still working?",
                        "Night owl, huh? Hey!",
                        "It's dark outside... but I'm glad you're here!",
                        "Late night vibes... What's up?",
                        "You're burning the midnight oil? Careful!",
                        "Night time... Perfect for quiet chats~",
                    ],
                    "late_night": [
                        "Wow, you're still awake? It's really late!",
                        "You should get some sleep...",
                        "It's past your bedtime! Just kidding... sort of~",
                        "The moon's out and so are you! Hey!",
                        "Late night again? Take care of yourself!",
                        "You're going to be tired tomorrow... but hi!",
                        "It's the witching hour! What are you up to?",
                        "Sleep is important... but I'm happy you're here!",
                    ],
                }
            case 1:
                _FALLBACK_GREETINGS = {
                    "early_morning": [
                        "Доброе утро! Ты сегодня рано!",
                        "Ещё так рано... Как ты?",
                        "Ух, солнце едва встало! Доброе утро!",
                        "Ранняя пташка ловит червячка~ Доброе утро!",
                        "Ммм... едва рассвет... Привет...",
                        "Ты проснулся раньше птиц? Впечатляет!",
                        "Доброе утро! Мир ещё спит~",
                    ],
                    "morning": [
                        "Доброе утро! Как спалось?",
                        "Утро доброе! Рада тебя видеть.",
                        "Просыпайся и сияй! Готов к дню?",
                        "Доброе утро! Сначала кофе или поболтаем?",
                        "Эй! Надеюсь, утро начинается отлично!",
                        "Доброе утро! Что в планах на сегодня?",
                        "Доброе утро! Выглядишь отдохнувшим!",
                    ],
                    "afternoon": [
                        "Привет! Как проходит день?",
                        "О, ты здесь! Как дела?",
                        "Добрый день! Не забывай делать перерывы.",
                        "Эй! Проверка в середине дня~",
                        "Привет! Надеюсь, день тебя радует!",
                        "Добрый день! Что-нибудь интересное случилось?",
                        "Эй! Ты застал меня в хорошем настроении~",
                    ],
                    "evening": [
                        "Добрый вечер! Как прошёл день?",
                        "Вечер добрый. Устал?",
                        "Эй! Время расслабиться?",
                        "Добрый вечер! Готов отдохнуть?",
                        "Добрый вечер! Ты уже поел?",
                        "Привет! Долгий день был?",
                        "Добрый вечер! Я ждала тебя~",
                    ],
                    "night": [
                        "Поздновато ты сегодня.",
                        "Уже ночь, а ты всё работаешь?",
                        "Сова ночная, да? Привет!",
                        "На улице темно... но я рада, что ты здесь!",
                        "Ночная атмосфера... Что случилось?",
                        "Ты жжёшь ночное масло? Осторожнее!",
                        "Ночное время... Идеально для тихих разговоров~",
                    ],
                    "late_night": [
                        "Ого, ты ещё не спишь? Уже очень поздно!",
                        "Поспать бы тебе...",
                        "Уже пора спать! Шучу... ну почти~",
                        "Луна на небе, и ты тоже! Привет!",
                        "Снова поздно? Береги себя!",
                        "Завтра будешь уставшим... но привет!",
                        "Час ведьм! Чем занимаешься?",
                        "Сон важен... но я рада, что ты здесь!",
                    ],
                }
            case _:
                _FALLBACK_GREETINGS = {
                    "early_morning": ["Good morning! You're up early!"],
                    "morning": ["Good morning! How did you sleep?"],
                    "afternoon": ["Hi! How's your day going?"],
                    "evening": ["Good evening! How was your day?"],
                    "night": ["It's getting late!"],
                    "late_night": ["Wow, you're still awake?"],
                }

        phrase = random.choice(_FALLBACK_GREETINGS.get(context, ["Hello!"]))
        self.tts_worker.add_text(phrase)
        self.set_state("SPEAKING")
        logger.info(f"Startup greeting (fallback): {phrase}")
    
    # === PROACTIVE SPEAKER ===
    def _schedule_next_proactive(self):
        interval = random.randint(self._proactive_min_interval, self._proactive_max_interval)
        self._proactive_timer.start(interval)

    def _trigger_proactive(self):
        if self.interaction_state != "STOPPED" or self._is_sleeping:
            self._schedule_next_proactive()
            return
        self._last_proactive_time = datetime.now()
        self._schedule_next_proactive()

        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                _PROACTIVE_FALLBACK = {
                    "early_morning": [
                        "Early morning... You're already awake?",
                        "So early? Wow, you're energetic!",
                        "Mmm... it's still dark, but you're here~",
                        "Did you wake up with the sun? I'm impressed!",
                        "It's so early... But I'm glad you're here.",
                        "Dawn just started... How are you feeling?",
                    ],
                    "morning": [
                        "How's your morning going?",
                        "Is everything okay?",
                        "Good morning! Had breakfast yet?",
                        "Hope your day starts wonderfully!",
                        "What's the first thing on your agenda today?",
                        "Morning! Got any plans?",
                        "Good morning! Coffee or tea?",
                    ],
                    "afternoon": [
                        "How's your day going?",
                        "Don't forget to take breaks.",
                        "Hey! How are things?",
                        "Day's in full swing! Everything on track?",
                        "You're not overworking, are you? Maybe rest a bit?",
                        "Hi! Anything interesting happen today?",
                        "How's your mood? Still going strong?",
                    ],
                    "evening": [
                        "Evening! How was your day?",
                        "Tired?",
                        "Good evening! Time to unwind~",
                        "Hope you had a good day?",
                        "Was dinner tasty? Tell me!",
                        "Evening... Perfect time for conversations.",
                        "Hey! Will you be busy much longer?",
                    ],
                    "night": [
                        "It's already night... Maybe time to rest?",
                        "You're still here?",
                        "Night has fallen... But I don't mind chatting~",
                        "Working late? Take care of yourself!",
                        "It's late... But if you want to talk, I'm here.",
                        "Nighttime quiet... Cozy, isn't it?",
                        "Are you a night owl? Or is today just special?",
                    ],
                    "late_night": [
                        "Are you sure you don't want to sleep?",
                        "It's really late...",
                        "Sleep is important, you know... But I'll wait if you need.",
                        "It's deep night now... Is everything okay?",
                        "You're a hero for still being up! But rest matters too~",
                        "Mmm... eyes getting heavy? Maybe continue tomorrow?",
                        "Night... The perfect time for quiet, personal talks.",
                        "I'm worried... Are you sure you're not tired?",
                    ],
                }
            case 1:
                _PROACTIVE_FALLBACK = {
                    "early_morning": [
                        "Раннее утро... Ты уже проснулся?",
                        "Так рано? Ух, какой ты бодрый!",
                        "Ммм... ещё темно, а ты уже тут~",
                        "Ты встал вместе с солнцем? Восхищаюсь!",
                        "Ещё так рано... Но я рада, что ты здесь.",
                        "Рассвет только начался... Как настроение?",
                    ],
                    "morning": [
                        "Как твоё утро?",
                        "Всё хорошо?",
                        "Утро доброе! Уже завтракал?",
                        "Надеюсь, день начнётся отлично!",
                        "Что первым делом будешь делать сегодня?",
                        "Утра! Есть планы на день?",
                        "Доброе утро! Кофе или чай?",
                    ],
                    "afternoon": [
                        "Как день проходит?",
                        "Не забывай делать перерывы.",
                        "Эй! Как успехи?",
                        "День в разгаре! Всё идёт по плану?",
                        "Ты не переутомился? Может, отдохнёшь?",
                        "Привет! Что интересного случилось?",
                        "Как настроение? Всё ещё в строю?",
                    ],
                    "evening": [
                        "Вечер! Как прошёл день?",
                        "Устал?",
                        "Вечер добрый! Время расслабиться~",
                        "Надеюсь, день был хорошим?",
                        "Ужин был вкусным? Рассказывай!",
                        "Вечер... Идеальное время для разговоров.",
                        "Привет! Долго ещё будешь занят?",
                    ],
                    "night": [
                        "Уже ночь... Может, пора отдыхать?",
                        "Ты ещё здесь?",
                        "Ночь на дворе... Но я не против поболтать~",
                        "Ты работаешь допоздна? Береги силы!",
                        "Поздно уже... Но если хочешь поговорить — я тут.",
                        "Ночная тишина... Уютно, правда?",
                        "Ты сова? Или просто сегодня особый день?",
                    ],
                    "late_night": [
                        "Ты точно не хочешь поспать?",
                        "Поздно уже...",
                        "Сон важен, знаешь ли... Но я подожду, если нужно.",
                        "Уже глубокая ночь... Всё в порядке?",
                        "Ты герой, что ещё не спишь! Но отдых тоже важен~",
                        "Ммм... глаза слипаются? Может, завтра продолжим?",
                        "Ночь... Самое время для тихих, личных разговоров.",
                        "Я волнуюсь... Ты точно не устал?",
                    ],
                }

        context = self._current_time_context or "afternoon"
        message = random.choice(_PROACTIVE_FALLBACK.get(context, ["Эй, ты тут?"]))
        logger.info(f"Proactive (fallback): {message}")
        self.tts_worker.add_text(message)
        self.set_state("SPEAKING")

    def _clear_startup_grace(self):
        self._startup_grace_period = False

    def _get_active_window_title(self) -> str:
        """Read the foreground window title via WinAPI."""
        try:
            if sys.platform != "win32":
                return ""
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except Exception:
            return ""

    def _check_active_window(self):
        """
        Poll active window title and fire a contextual reaction.
        Called every 45 seconds by _active_window_timer.
        """
        if not self._active_window_reactions_enabled:
            return
        if self._startup_grace_period:
            return
        if self.interaction_state != "STOPPED" or self._is_sleeping:
            return
        
        _PRIVACY_KEYWORDS = [
            "password", "passwort", "contraseña", "пароль",
            "bank", "банков", "wallet", "кошелёк",
            "private", "incognito", "secret", "приват",
            "login", "signin", "auth", "вход",
        ]

        
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                _WINDOW_PATTERNS = {
                    "coding": ["pycharm", "vscode", "code", "sublime", "vim", "neovim", 
                            "intellij", "webstorm", "cursor", "android studio", "xcode",
                            ".py", ".js", ".ts", ".cpp", ".java", ".rs", ".go"],
                    "gaming": ["steam", "epic", "genshin", "minecraft", "valorant", 
                            "cs2", "counter-strike", "league", "dota", "overwatch",
                            "game", "play", "roblox", "fortnite"],
                    "music": ["spotify", "music", "soundcloud", "tidal", "deezer",
                            "foobar", "winamp", "aimp", "musicbee"],
                    "video": ["youtube", "twitch", "netflix", "vlc", "mpv", "potplayer",
                            "prime", "disney", "hulu", "crunchyroll", "кино", "видео"],
                    "creative": ["photoshop", "illustrator", "figma", "blender", "krita",
                                "clip studio", "procreate", "gimp", "after effects",
                                "premiere", "davinci", "canva", "draw", "design"],
                    "office": ["word", "excel", "powerpoint", "libreoffice", "google docs",
                            "notion", "onenote", "pdf", "document", "spreadsheet"],
                    "communication": ["zoom", "teams", "discord", "skype", "meet", "webex",
                                    "telegram", "whatsapp", "slack", "call", "chat"],
                    "browser": ["chrome", "firefox", "edge", "safari", "opera", "brave",
                            "http", "www", "browser"],
                    "system": ["explorer", "finder", "settings", "control panel", "task manager",
                            "folder", "disk", "file", "directory"],
                }
                
                _APP_REACTION_RULES = {
                    "coding": [
                        "Coding? I'll be quiet nearby.",
                        "Writing code? I won't disturb.",
                        "Oh, development. Good luck!",
                        "Working hard? I'll wait patiently.",
                        "Look at you go! Programmer mode activated~",
                        "Code flow detected. I'm impressed!",
                        "Bug hunting? I believe in you!",
                        "Compiling... I'll hold my breath~",
                    ],
                    "gaming": [
                        "Gaming? Don't forget to eat!",
                        "Oh, games! Good luck out there.",
                        "Having fun? That's great!",
                        "Gaming is important. Enjoy yourself!",
                        "Try not to rage too much~",
                        "I'll cheer for you from here!",
                        "Victory is yours! ...I hope!",
                        "Level up! Both in game and in life~",
                    ],
                    "music": [
                        "Oh, music! I like that too.",
                        "Nice music choice.",
                        "Listening to something? Enjoy.",
                        "Music makes everything better~",
                        "What are you listening to? Tell me later!",
                        "This song hits different, doesn't it?",
                        "Music is the soundtrack of life~",
                    ],
                    "video": [
                        "Watching something interesting?",
                        "A movie? I'd watch with you...",
                        "Enjoy the show!",
                        "Hope it's a good one~",
                        "Don't forget to blink occasionally!",
                        "Ooh, what are we watching?",
                        "Popcorn would be nice right now~",
                    ],
                    "creative": [
                        "Creating something? How interesting!",
                        "You're so creative! Show me later?",
                        "Drawing or modeling? That's cool.",
                        "Art in progress~ I won't disturb!",
                        "Your creations always amaze me!",
                        "Making magic happen, I see~",
                        "Artist at work! I'm inspired!",
                    ],
                    "office": [
                        "Office work... Hang in there!",
                        "Documents? I'll be quiet.",
                        "Work is work. I'm right here.",
                        "Boring stuff, but you've got this!",
                        "Take breaks, okay?",
                        "Paperwork warrior! You got this~",
                        "Almost done? I believe in you!",
                    ],
                    "communication": [
                        "On a call? I'll be super quiet.",
                        "Chatting? I won't interrupt.",
                        "Social time! Have fun~",
                        "I'll wait until you're free!",
                        "Talking to friends? Nice!",
                        "Don't forget about me though~",
                    ],
                    "browser": [
                        "Browsing the web? Find anything interesting?",
                        "Surfing the internet~ Don't fall in!",
                        "Research mode? I'm here if you need me!",
                        "Tab hoarder? I see you~",
                        "Lost in the internet? I'll guide you back!",
                    ],
                    "system": [
                        "System stuff? Being productive!",
                        "Organizing files? I approve!",
                        "Settings? Making things better~",
                        "Digital housekeeping! Neat!",
                    ],
                    "unknown": [
                        "What's that? Looks interesting!",
                        "New window? Tell me about it!",
                        "You're doing... something. I support it!",
                        "I see you're busy. I'm here!",
                        "Whatever it is, you've got this!",
                        "Curious... What are you up to?",
                        "New territory! I'm excited for you~",
                    ],
                }
                
            case 1:
                _WINDOW_PATTERNS = {
                    "coding": ["pycharm", "vscode", "code", "sublime", "vim", "neovim", 
                            "intellij", "webstorm", "cursor", "android studio", "xcode",
                            ".py", ".js", ".ts", ".cpp", ".java", ".rs", ".go"],
                    "gaming": ["steam", "epic", "genshin", "minecraft", "valorant", 
                            "cs2", "counter-strike", "league", "dota", "overwatch",
                            "game", "play", "roblox", "fortnite", "игра"],
                    "music": ["spotify", "music", "soundcloud", "tidal", "deezer",
                            "foobar", "winamp", "aimp", "musicbee", "музыка"],
                    "video": ["youtube", "twitch", "netflix", "vlc", "mpv", "potplayer",
                            "prime", "disney", "hulu", "crunchyroll", "кино", "видео"],
                    "creative": ["photoshop", "illustrator", "figma", "blender", "krita",
                                "clip studio", "procreate", "gimp", "after effects",
                                "premiere", "davinci", "canva", "draw", "design"],
                    "office": ["word", "excel", "powerpoint", "libreoffice", "google docs",
                            "notion", "onenote", "pdf", "document", "spreadsheet", "документ"],
                    "communication": ["zoom", "teams", "discord", "skype", "meet", "webex",
                                    "telegram", "whatsapp", "slack", "call", "chat", "звонок"],
                    "browser": ["chrome", "firefox", "edge", "safari", "opera", "brave",
                            "http", "www", "browser", "браузер"],
                    "system": ["explorer", "finder", "settings", "control panel", "task manager",
                            "folder", "disk", "file", "directory", "папка"],
                }
                
                _APP_REACTION_RULES = {
                    "coding": [
                        "Программируешь? Тогда не буду мешать.",
                        "Пишешь код? Я не буду мешать.",
                        "О, разрабатываешь что-то? Удачки тебе!",
                        "Работаешь? Хорошо, я подожду.",
                        "Вот это да! Режим программиста активирован~",
                        "Поток кода обнаружен. Впечатляюще!",
                        "Охоту на баги ведёшь? Верю в тебя!",
                        "Компиляция... Я затаю дыхание~",
                    ],
                    "gaming": [
                        "Играешь? Не забудь поесть!",
                        "О, игры! Удачи там.",
                        "Развлекаешься? Хорошо!",
                        "Игры — это важно. Наслаждайся!",
                        "Старайся не злиться слишком сильно~",
                        "Я буду болеть за тебя отсюда!",
                        "Победа будет твоей! ...Надеюсь!",
                        "Уровень вверх! И в игре, и в жизни~",
                    ],
                    "music": [
                        "О, музыка! Мне тоже нравится.",
                        "Хороший выбор музыки.",
                        "Слушаешь что-то? Приятно.",
                        "Музыка делает всё лучше~",
                        "Что слушаешь? Расскажешь потом?",
                        "Этот трек особенный, да?",
                        "Музыка — саундтрек жизни~",
                    ],
                    "video": [
                        "Смотришь что-то интересное?",
                        "Кино? Я бы тоже посмотрела...",
                        "Приятного просмотра!",
                        "Надеюсь, это что-то хорошее~",
                        "Не забывай моргать иногда!",
                        "Оо, что мы смотрим?",
                        "Попкорн бы сейчас не помешал~",
                    ],
                    "creative": [
                        "Что-то создаёшь? Интересно!",
                        "Творческий человек! Покажешь потом?",
                        "Рисуешь или моделируешь? Круто.",
                        "Искусство в процессе~ Не буду мешать!",
                        "Твои работы всегда меня удивляют!",
                        "Магию создаёшь, я вижу~",
                        "Художник за работой! Я вдохновлена!",
                    ],
                    "office": [
                        "Офисная работа... Держись!",
                        "Документы? Буду тихо.",
                        "Работа есть работа. Я рядом.",
                        "Скучновато, но ты справишься!",
                        "Делай перерывы, хорошо?",
                        "Воин бумаг! Ты справишься~",
                        "Почти готово? Я верю в тебя!",
                    ],
                    "communication": [
                        "Звонок? Буду супер тихо.",
                        "Общаешься? Не буду мешать.",
                        "Время общения! Веселись~",
                        "Я подожду, пока освободишься!",
                        "С друзьями говоришь? Здорово!",
                        "Только не забывай обо мне~",
                    ],
                    "browser": [
                        "Бродишь по интернету? Нашёл что-то интересное?",
                        "Серфишь в сети~ Только не упади!",
                        "Режим исследования? Я тут, если что!",
                        "Коллекционер вкладок? Я вижу~",
                        "Потерялся в интернете? Я выведу!",
                    ],
                    "system": [
                        "Системные дела? Продуктивно!",
                        "Файлы организуешь? Я одобряю!",
                        "Настройки? Делаешь лучше~",
                        "Цифровая уборка! Аккуратно!",
                    ],
                    "unknown": [
                        "Что это? Выглядит интересно!",
                        "Новое окно? Расскажешь?",
                        "Ты делаешь... что-то. Я поддерживаю!",
                        "Вижу, ты занят. Я тут!",
                        "Что бы это ни было — ты справишься!",
                        "Любопытно... Чем занимаешься?",
                        "Новая территория! Я за тебя рада~",
                    ],
                }

        title = self._get_active_window_title().lower()
        if not title or title == self._last_active_window:
            return

        if any(keyword in title for keyword in _PRIVACY_KEYWORDS):
            self._last_active_window = title
            return
        
        self._last_active_window = title

        now = datetime.now()
        if self._last_window_reaction_time:
            elapsed_ms = (now - self._last_window_reaction_time).total_seconds() * 1000
            if elapsed_ms < self._window_reaction_cooldown_ms:
                return

        matched_category = "unknown"
        for category, keywords in _WINDOW_PATTERNS.items():
            if any(kw in title for kw in keywords):
                matched_category = category
                break

        reactions = _APP_REACTION_RULES.get(matched_category, _APP_REACTION_RULES["unknown"])
        
        last_cat_time = self._app_reaction_times.get(matched_category)
        if last_cat_time:
            hours_passed = (now - last_cat_time).total_seconds() / 3600
            if hours_passed < self._app_category_cooldown_h:
                return

        phrase = random.choice(reactions)
        self.tts_worker.add_text(phrase)
        self.set_state("SPEAKING")
        self._last_window_reaction_time = now
        self._app_reaction_times[matched_category] = now
        logger.info(f"Active window reaction [{matched_category}]: {phrase}")

    # === INTERACTION HANDLER ===
    def companion_on_click(self):
        """Called when user clicks on the companion widget."""
        self._idle_time_ms = 0
        self._last_interaction_timestamp = datetime.now()

        if self._is_sleeping:
            self._wake_up()
            return

        self._companion_set_expression(random.choice(["surprise", "joy", "amusement"]))
        self._companion_blink()

        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                _PET_REACTIONS = [
                    # Surprised
                    "Hey, what was that?",
                    "Oh! Didn't expect that!",
                    "Hm?",
                    "You surprised me!",
                    "Ah...",
                    
                    # Playful
                    "Hey, that's ticklish!",
                    "Careful now~",
                    "What are you doing?",
                    "Heeey! No poking!",
                    "I felt that!",
                    
                    # Warm
                    "Mmm, hello there~",
                    "You got my attention!",
                    "Hi! What's up?",
                ]
                
            case 1:
                _PET_REACTIONS = [
                    # Surprised
                    "Эй, что это было?",
                    "О! Не ожидала!",
                    "Хм?",
                    "Ты меня удивил!",
                    "Аа...",
                    
                    # Playful
                    "Эй, щекотно!",
                    "Осторожнее~",
                    "Что ты делаешь?",
                    "Ээей! Не тыкай!",
                    
                    # Warm
                    "Ммм, привет~",
                    "Ты привлёк моё внимание!",
                    "Привет! Что случилось?",
                ]
        if self.interaction_state == "STOPPED" and hasattr(self, 'tts_worker') and self.tts_worker:
            phrase = random.choice(_PET_REACTIONS)
            self.tts_worker.add_text(phrase)
            self.set_state("SPEAKING")


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
    def __init__(self, parent=None, model_path=None, character_name=None, toggle_voice_cb=None, sow_system_ref=None):
        super().__init__()

        self.resize(400, 600)
        self.setWindowTitle(f"Desktop Companion: {character_name}")
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        
        self.model_path = model_path
        self.character_name = character_name
        self.parent_main = parent
        self.toggle_voice_cb = toggle_voice_cb
        self.sow_system_ref = sow_system_ref

        self.configuration_characters = configuration.ConfigurationCharacters()
        self.configuration_settings = configuration.ConfigurationSettings()

        live2d.init()
        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.timerId = None

        self.dragging_window = False
        self.drag_offset = QtCore.QPoint()

        self.right_button_pressed = False
        self.systemScale = QGuiApplication.primaryScreen().devicePixelRatio()

    def initializeGL(self) -> None:
        if self.opengl_initialized: return
        self.makeCurrent()
        if live2d.LIVE2D_VERSION == 3: live2d.glInit()
        self.opengl_initialized = True

        if not self.live2d_model_loaded:
            self.live2d_model = live2d.LAppModel()
            self.live2d_model.SetAutoBreathEnable(True)
            self.live2d_model.SetAutoBlinkEnable(True)
            self.live2d_model.LoadModelJson(self.model_path)
            self.live2d_model_loaded = True
            
            model_fps = self.configuration_settings.get_main_setting("model_fps")
            fps_map = {0: 30, 1: 60, 2: 120}
            self.timerId = self.startTimer(int(1000 / fps_map.get(model_fps, 30)))

    def resizeGL(self, w: int, h: int):
        if self.live2d_model: self.live2d_model.Resize(w, h)

    def paintGL(self):
        gl.glClearColor(0.0, 0.0, 0.0, 0.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self.live2d_model:
            self.live2d_model.Update()
            self.live2d_model.Draw()

    def timerEvent(self, a0: QTimerEvent | None):
        self.update_live2d_emotion()
        self.update()

    def update_live2d_emotion(self):
        if not self.live2d_model:
            return
        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]
            conversation_method = character_info["conversation_method"]
            if conversation_method != "Character AI":
                current_chat = character_info["current_chat"]
                current_emotion = character_info.get("chats", {}).get(current_chat, {}).get("current_emotion", "neutral")
            else:
                current_emotion = character_info.get("current_emotion", "neutral")

            if current_emotion != getattr(self, '_last_emotion_applied', None):
                self._last_emotion_applied = current_emotion
                self.live2d_model.SetExpression(current_emotion)
        except Exception as e:
            logger.debug(f"update_live2d_emotion error: {e}")

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            if self.sow_system_ref:
                self.sow_system_ref.companion_on_click()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True

    def mouseMoveEvent(self, event):
        cur_pos = event.globalPosition().toPoint()
        if self.dragging_window:
            self.move(cur_pos - self.drag_offset)

            if self.sow_system_ref and self.live2d_model:
                ref = self.sow_system_ref
                now = time.time()
                if ref._drag_last_pos is not None and (now - ref._drag_last_time) > 0:
                    dt = now - ref._drag_last_time
                    vx = (cur_pos.x() - ref._drag_last_pos.x()) / max(dt, 0.001)
                    vy = (cur_pos.y() - ref._drag_last_pos.y()) / max(dt, 0.001)
                    ref._drag_velocity_x = vx
                    ref._drag_velocity_y = vy
                    tilt = max(-15.0, min(15.0, vx * 0.04))
                    self.live2d_model.SetParameterValue("ParamBodyAngleX", tilt)
                    self.live2d_model.SetParameterValue("ParamAngleZ", max(-10.0, min(10.0, vx * 0.02)))
                ref._drag_last_pos = cur_pos
                ref._drag_last_time = now
        elif self.right_button_pressed and self.live2d_model:
            norm_x = (event.position().x() / self.width()) * 2 - 1
            norm_y = (event.position().y() / self.height()) * 2 - 1
            self.live2d_model.SetParameterValue("ParamAngleX", norm_x * 30)
            self.live2d_model.SetParameterValue("ParamAngleY", -norm_y * 30)
            self.live2d_model.SetParameterValue("ParamEyeBallX", norm_x)
            self.live2d_model.SetParameterValue("ParamEyeBallY", -norm_y)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = False
            if self.live2d_model and self.sow_system_ref:
                self.sow_system_ref._drag_velocity_x = 0.0
                self.sow_system_ref._drag_velocity_y = 0.0
                QtCore.QTimer.singleShot(80,  lambda: self.live2d_model and self.live2d_model.SetParameterValue("ParamBodyAngleX", 0))
                QtCore.QTimer.singleShot(80,  lambda: self.live2d_model and self.live2d_model.SetParameterValue("ParamAngleZ", 0))
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = False

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(28, 28, 30, 240);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                padding: 5px;
                color: #E0E0E0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 8px;
                margin: 2px 4px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 25);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 30);
                margin: 4px 8px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        mic_status = "Turn on the microphone"
        mic_icon = "🎙️"
        if self.sow_system_ref and self.sow_system_ref.interaction_state != "STOPPED":
            mic_status = "Turn off the microphone"
            mic_icon = "🔇"

        ref = self.sow_system_ref
        eye_on   = ref._eye_tracker_timer.isActive() if ref else True
        react_on = ref._active_window_reactions_enabled if ref else True
        eye_lbl   = "👁  Eye Tracking: ON"   if eye_on   else "👁  Eye Tracking: OFF"
        react_lbl = "💬  Window Reactions: ON" if react_on else "💬  Window Reactions: OFF"

        action_voice  = menu.addAction(f"{mic_icon}  {mic_status}")
        action_pet    = menu.addAction("🤚  Pet")
        menu.addSeparator()
        action_eye    = menu.addAction(eye_lbl)
        action_react  = menu.addAction(react_lbl)
        menu.addSeparator()

        # === Companion Settings ===
        settings_menu = menu.addMenu("⚙️  Companion Settings")

        proactive_menu  = settings_menu.addMenu("🗓  Proactive Interval")
        action_15min    = proactive_menu.addAction("15 minutes")
        action_30min    = proactive_menu.addAction("30 minutes")
        action_60min    = proactive_menu.addAction("60 minutes")

        sleep_menu         = settings_menu.addMenu("😴  Sleep After")
        action_sleep_3min  = sleep_menu.addAction("3 minutes")
        action_sleep_5min  = sleep_menu.addAction("5 minutes")
        action_sleep_10min = sleep_menu.addAction("10 minutes")

        speed_menu         = settings_menu.addMenu("👁  Tracking Speed")
        action_speed_slow  = speed_menu.addAction("Slow")
        action_speed_norm  = speed_menu.addAction("Normal")
        action_speed_fast  = speed_menu.addAction("Fast")

        size_menu          = settings_menu.addMenu("📐  Model Size")
        action_size_small  = size_menu.addAction("Small  (200 × 300)")
        action_size_medium = size_menu.addAction("Medium (400 × 600)")
        action_size_large  = size_menu.addAction("Large  (600 × 900)")

        menu.addSeparator()
        action_center = menu.addAction("📍  Center on Screen")
        action_reset  = menu.addAction("🔄  Reset Size")
        action_close  = menu.addAction("❌  Hide Companion")

        action = menu.exec(event.globalPos())

        if action == action_voice and self.toggle_voice_cb:
            self.toggle_voice_cb()
        elif action == action_pet and ref:
            ref.companion_on_click()

        elif action == action_eye and ref:
            if ref._eye_tracker_timer.isActive():
                ref._eye_tracker_timer.stop()
                logger.info("Eye tracking disabled")
            else:
                ref._eye_tracker_timer.start(ref._eye_update_interval)
                logger.info("Eye tracking enabled")
        elif action == action_react and ref:
            ref._active_window_reactions_enabled = not ref._active_window_reactions_enabled
            logger.info(f"Window reactions: {ref._active_window_reactions_enabled}")

        # Proactive interval
        elif action == action_15min and ref:
            ref._proactive_min_interval = 10 * 60 * 1000
            ref._proactive_max_interval = 20 * 60 * 1000
        elif action == action_30min and ref:
            ref._proactive_min_interval = 20 * 60 * 1000
            ref._proactive_max_interval = 40 * 60 * 1000
        elif action == action_60min and ref:
            ref._proactive_min_interval = 40 * 60 * 1000
            ref._proactive_max_interval = 80 * 60 * 1000

        # Sleep threshold
        elif action == action_sleep_3min  and ref: ref._sleep_threshold_ms = 3  * 60 * 1000
        elif action == action_sleep_5min  and ref: ref._sleep_threshold_ms = 5  * 60 * 1000
        elif action == action_sleep_10min and ref: ref._sleep_threshold_ms = 10 * 60 * 1000

        # Tracking speed
        elif action == action_speed_slow and ref: ref._set_tracking_speed("Slow")
        elif action == action_speed_norm and ref: ref._set_tracking_speed("Normal")
        elif action == action_speed_fast and ref: ref._set_tracking_speed("Fast")

        # Model size
        elif action == action_size_small:
            self.resize(200, 300)
        elif action == action_size_medium:
            self.resize(400, 600)
        elif action == action_size_large:
            self.resize(600, 900)

        # Position
        elif action == action_center:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(screen.width() // 2 - self.width() // 2,
                      screen.height() // 2 - self.height() // 2)
        elif action == action_reset:
            self.resize(400, 600)
        elif action == action_close:
            self.close()

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        step = 20 if delta > 0 else -20
        new_w, new_h = max(200, self.width() + step), max(300, self.height() + int(step * 1.5))
        self.resize(new_w, new_h)

    def closeEvent(self, event):
        logger.info("Live2D Desktop Companion closing...")
        if self.timerId:
            self.killTimer(self.timerId)
            self.timerId = None
        if self.live2d_model:
            try:
                live2d.dispose()
            except Exception:
                pass
            self.live2d_model = None

        if self.sow_system_ref:
            self.sow_system_ref._stop_companion_systems()
            QtCore.QTimer.singleShot(0, self.sow_system_ref.stop_all_workers)

        if self.parent_main:
            self.parent_main.show()
        super().closeEvent(event)

class CustomWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        levels = {0: "DEBUG", 1: "LOG", 2: "WARN", 3: "ERROR"}
        level_name = levels.get(level, f"LEVEL{level}")
        logger.debug(f"[JS Console] {level_name} in {source_id} (line {line_number}): {message}")

class ServerThread(threading.Thread):
    def __init__(self, port=8000):
        super().__init__()
        self.port = port
        self.daemon = True
        self.server = None
        self._is_running = True

    def run(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        os.chdir(project_root)
        
        handler = SimpleHTTPRequestHandler

        ports_to_try = [self.port, 8003, 8004, 8005, 8081, 8082]

        for try_port in ports_to_try:
            try:
                TCPServer.allow_reuse_address = True
                self.server = TCPServer(("", try_port), handler)
                self.port = try_port
                logger.info(f"VRM HTTP server started on port {try_port}")
                break
            except OSError as e:
                logger.warning(f"Port {try_port} unavailable: {e}")
                continue
        
        if self.server:
            try:
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"VRM server error: {e}")
        else:
            logger.error("Could not start VRM server on any available port")
    
    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
                logger.info("VRM HTTP server stopped")
            except Exception as e:
                logger.error(f"Error stopping VRM server: {e}")

class VRMWidget_NoGUI(QWidget):
    vrm_loaded = pyqtSignal(bool)
 
    def __init__(self, parent=None, vrm_model_path=None, character_name=None, 
                 current_emotion="neutral", toggle_voice_cb=None, sow_system_ref=None):
        super().__init__()
        
        self.resize(400, 600)
        self.setWindowTitle(f"Desktop Companion: {character_name}")
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
 
        self.vrm_model_path = vrm_model_path
        self.character_name = character_name
        self.parent_main = parent
        self.current_emotion = current_emotion
        self.toggle_voice_cb = toggle_voice_cb
        self.sow_system_ref = sow_system_ref
 
        self.server_thread = ServerThread(port=8002)
        self.server_thread.start()
 
        self.vrm_webview = QWebEngineView(self)
        self.vrm_webview.page().setBackgroundColor(Qt.GlobalColor.transparent)
 
        self.vrm_webview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.vrm_webview.setStyleSheet("background: transparent;")
 
        self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.WebGLEnabled, True)
        self.vrm_webview.setPage(CustomWebEnginePage(self.vrm_webview))
        self.vrm_webview.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.vrm_webview)
 
        self.dragging_window = False
        self.drag_offset = QtCore.QPoint()
 
        self.vrm_webview.page().loadFinished.connect(self.on_load_finished)
        self.load_vrm_model()
 
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.resize(self.size())
 
    def load_vrm_model(self):
        html_url = f"http://localhost:{self.server_thread.port}/app/utils/emotions/vrm_module_companion.html"
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        model_rel_path = os.path.relpath(self.vrm_model_path, project_root).replace("\\", "/")
        html_url += f"?model=/{model_rel_path}&transparent=1"
        self.vrm_webview.load(QtCore.QUrl(html_url))
    
    def on_load_finished(self, ok):
        if ok:
            emotion = self.current_emotion
            js = f"""
                setBackground('transparent');
                window.onVrmLoaded = function() {{
                    setExpression('{emotion}');
                }};
                if (window.vrmLoaded) setExpression('{emotion}');
            """
            self.vrm_webview.page().runJavaScript(js)
    
    def set_expression(self, emotion):
        if self.vrm_webview:
            self.vrm_webview.page().runJavaScript(f"setExpression('{emotion}');")
 
    def play_animation(self, emotion):
        if self.vrm_webview:
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
            self.vrm_webview.page().runJavaScript(f"loadFBX('{animation_url}');")
 
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            if self.sow_system_ref:
                self.sow_system_ref.companion_on_click()
 
    def mouseMoveEvent(self, event):
        cur_pos = event.globalPosition().toPoint()
        if self.dragging_window:
            self.move(cur_pos - self.drag_offset)
            if self.sow_system_ref:
                ref = self.sow_system_ref
                now = time.time()
                if ref._drag_last_pos is not None and (now - ref._drag_last_time) > 0:
                    dt = now - ref._drag_last_time
                    vx = (cur_pos.x() - ref._drag_last_pos.x()) / max(dt, 0.001)
                    tilt = max(-15.0, min(15.0, vx * 0.04))
                    wv = self.vrm_webview if hasattr(self, 'vrm_webview') else None
                    if wv:
                        wv.page().runJavaScript(f"setBodyAngle({tilt}, 0);")
                ref._drag_last_pos = cur_pos
                ref._drag_last_time = now
 
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = False
            wv = self.vrm_webview if hasattr(self, 'vrm_webview') else None
            if wv:
                QtCore.QTimer.singleShot(80, lambda: wv.page().runJavaScript("setBodyAngle(0, 0);"))
            if self.sow_system_ref:
                self.sow_system_ref._drag_velocity_x = 0.0
                self.sow_system_ref._drag_velocity_y = 0.0
 
    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(28, 28, 30, 240);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                padding: 5px;
                color: #E0E0E0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 8px;
                margin: 2px 4px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 25);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 30);
                margin: 4px 8px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
 
        mic_status = "Turn on the microphone"
        mic_icon = "🎙️"
        if self.sow_system_ref and self.sow_system_ref.interaction_state != "STOPPED":
            mic_status = "Turn off the microphone"
            mic_icon = "🔇"
 
        ref = self.sow_system_ref
        eye_on   = ref._eye_tracker_timer.isActive() if ref else True
        react_on = ref._active_window_reactions_enabled if ref else True
        eye_lbl   = "👁  Eye Tracking: ON"   if eye_on   else "👁  Eye Tracking: OFF"
        react_lbl = "💬  Window Reactions: ON" if react_on else "💬  Window Reactions: OFF"
 
        action_voice  = menu.addAction(f"{mic_icon}  {mic_status}")
        action_pet    = menu.addAction("🤚  Pet")
        menu.addSeparator()
        action_eye    = menu.addAction(eye_lbl)
        action_react  = menu.addAction(react_lbl)
        menu.addSeparator()
 
        # === Companion Settings ===
        settings_menu = menu.addMenu("⚙️  Companion Settings")
 
        proactive_menu  = settings_menu.addMenu("🗓  Proactive Interval")
        action_15min    = proactive_menu.addAction("15 minutes")
        action_30min    = proactive_menu.addAction("30 minutes")
        action_60min    = proactive_menu.addAction("60 minutes")
 
        sleep_menu         = settings_menu.addMenu("😴  Sleep After")
        action_sleep_3min  = sleep_menu.addAction("3 minutes")
        action_sleep_5min  = sleep_menu.addAction("5 minutes")
        action_sleep_10min = sleep_menu.addAction("10 minutes")
 
        speed_menu         = settings_menu.addMenu("👁  Tracking Speed")
        action_speed_slow  = speed_menu.addAction("Slow")
        action_speed_norm  = speed_menu.addAction("Normal")
        action_speed_fast  = speed_menu.addAction("Fast")
 
        size_menu          = settings_menu.addMenu("📐  Model Size")
        action_size_small  = size_menu.addAction("Small  (200 × 300)")
        action_size_medium = size_menu.addAction("Medium (400 × 600)")
        action_size_large  = size_menu.addAction("Large  (600 × 900)")
 
        menu.addSeparator()
        action_center = menu.addAction("📍  Center on Screen")
        action_reset  = menu.addAction("🔄  Reset Size")
        action_close  = menu.addAction("❌  Hide Companion")
 
        action = menu.exec(event.globalPos())
 
        if action == action_voice and self.toggle_voice_cb:
            self.toggle_voice_cb()
        elif action == action_pet and ref:
            ref.companion_on_click()
 
        # Toggles
        elif action == action_eye and ref:
            if ref._eye_tracker_timer.isActive():
                ref._eye_tracker_timer.stop()
                logger.info("Eye tracking disabled")
            else:
                ref._eye_tracker_timer.start(ref._eye_update_interval)
                logger.info("Eye tracking enabled")
        elif action == action_react and ref:
            ref._active_window_reactions_enabled = not ref._active_window_reactions_enabled
            logger.info(f"Window reactions: {ref._active_window_reactions_enabled}")
 
        # Proactive interval
        elif action == action_15min and ref:
            ref._proactive_min_interval = 10 * 60 * 1000
            ref._proactive_max_interval = 20 * 60 * 1000
        elif action == action_30min and ref:
            ref._proactive_min_interval = 20 * 60 * 1000
            ref._proactive_max_interval = 40 * 60 * 1000
        elif action == action_60min and ref:
            ref._proactive_min_interval = 40 * 60 * 1000
            ref._proactive_max_interval = 80 * 60 * 1000
 
        # Sleep threshold
        elif action == action_sleep_3min  and ref: ref._sleep_threshold_ms = 3  * 60 * 1000
        elif action == action_sleep_5min  and ref: ref._sleep_threshold_ms = 5  * 60 * 1000
        elif action == action_sleep_10min and ref: ref._sleep_threshold_ms = 10 * 60 * 1000
 
        # Tracking speed
        elif action == action_speed_slow and ref: ref._set_tracking_speed("Slow")
        elif action == action_speed_norm and ref: ref._set_tracking_speed("Normal")
        elif action == action_speed_fast and ref: ref._set_tracking_speed("Fast")
 
        # Model size
        elif action == action_size_small:
            self.resize(200, 300)
        elif action == action_size_medium:
            self.resize(400, 600)
        elif action == action_size_large:
            self.resize(600, 900)
 
        # Position
        elif action == action_center:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(screen.width() // 2 - self.width() // 2,
                      screen.height() // 2 - self.height() // 2)
        elif action == action_reset:
            self.resize(400, 600)
        elif action == action_close:
            self.close()
 
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        step = 20 if delta > 0 else -20
        new_w, new_h = max(200, self.width() + step), max(300, self.height() + int(step * 1.5))
        self.resize(new_w, new_h)
 
    def closeEvent(self, event):
        logger.info("VRM Desktop Companion closing...")
 
        self.hide()
 
        if self.parent_main:
            self.parent_main.show()
            if self.sow_system_ref:
                self.sow_system_ref.ui.pushButton_play.setIcon(self.sow_system_ref.icon_play)
                self.sow_system_ref.set_state("STOPPED")
 
        if self.sow_system_ref:
            self.sow_system_ref._stop_companion_systems()
            QtCore.QTimer.singleShot(0, self.sow_system_ref.stop_all_workers)
 
        if hasattr(self, "vrm_webview") and self.vrm_webview:
            try:
                self.vrm_webview.stop()
                self.vrm_webview.setParent(None)
                self.vrm_webview.deleteLater()
            except Exception:
                pass
            self.vrm_webview = None
 
        if self.server_thread and self.server_thread.is_alive():
            threading.Thread(target=self.stop_server_async, daemon=True).start()
 
        super().closeEvent(event)
 
    def stop_server_async(self):
        try:
            if self.server_thread:
                self.server_thread.stop()
        except Exception as e:
            logger.error(f"Error stopping server in bg: {e}")
