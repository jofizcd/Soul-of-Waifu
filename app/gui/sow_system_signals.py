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
from app.utils.ai_clients.local_server_manager import LocalServerManager
from app.utils.ai_clients.prompt_engine import (
    PromptEngine, strip_partial_state_tag, extract_state_update,
    strip_partial_reasoning_tag, extract_reasoning, find_reasoning_open, find_reasoning_close
)
from app.utils.ai_clients.ai_factory import AIFactory
from app.utils.soul_companion.soul_companion import SoulCompanion
from app.utils.translator import Translator
from app.utils.text_to_speech import TTSWorker, PipelinedTTSWorker
from app.utils.speech_to_text import AudioInputWorker, STTWorker
from app.utils.vrm_server import VRMServerThread
from app.gui.custom_widgets import sow_toast, safe_paint

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

        self.prompt_engine = PromptEngine()
        self.local_server_manager = LocalServerManager(self.ui)

        self.translator = Translator()
        self.tokenizer = None
        self.session = None

        self.live2d_no_gui = None
        self.vrm_no_gui = None

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

        self.live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")

        character_data = self.configuration_characters.load_configuration()
        character_info = character_data["character_list"][character_name]
        self.current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        self.conversation_method = character_info["conversation_method"]
        self.expression_images_folder = character_info.get("expression_images_folder", None)
        self.live2d_model_folder = character_info.get("live2d_model_folder", None)
        self.vrm_model_file = character_info.get("vrm_model_file", None)
        self.current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

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

        self.audio_worker = None 
        self.input_device_index = self.configuration_settings.get_main_setting("input_device_real_index")

        self.interaction_state = "STOPPED" # STOPPED, LISTENING, PROCESSING, SPEAKING
        self.is_interrupted = False
        self.llm_task = None

        self.stt_worker = STTWorker(model_size="small", device="cuda", compute_type="float16")
        self.stt_worker.text_ready_signal.connect(self.on_user_speech_recognized)
        self.stt_worker.start()

        self.tts_worker = PipelinedTTSWorker(
            self.current_text_to_speech, character_name,
            self.elevenlabs_voice_id, language="en"
        )
        self.tts_worker.queue_empty_signal.connect(self.on_audio_finished)
        self.tts_worker.lipsync_signal.connect(self.update_avatar_lips)
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
            current_mode = self._get_current_mode()
            if current_mode == "VRM" and hasattr(self, 'vrm_webview'):
                self.vrm_webview.page().runJavaScript(f"if (typeof window.setAppState !== 'undefined') window.setAppState('{state}');")
        except Exception as e:
            logger.error(f"Failed to send state to VRM: {e}")
    
    def toggle_voice_interaction(self, character_name):
        if self.interaction_state == "STOPPED":
            logger.info("Starting Voice Interaction Pipeline...")
            
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
        self._stop_companion_systems()
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

        logger.info("INTERRUPT DETECTED! Stop the processes...")

        self.is_interrupted = True
        if self.llm_task and not self.llm_task.done():
            self.llm_task.cancel()
            logger.info("The LLM stop signal has been sent")

        if hasattr(self, 'tts_worker') and self.tts_worker:
            self.tts_worker.clear_queue()
            logger.info("The TTS and player queues are cleared")

        if getattr(self, '_companion_speaking', False):
            self._companion_speaking = False
            if hasattr(self, 'soul_companion'):
                try:
                    self.soul_companion.on_interrupted_by_user()
                except Exception:
                    pass

        self._subtitle_clear()
        self.set_state("LISTENING")
    
    def on_audio_finished(self):
        if self.interaction_state != "SPEAKING":
            if getattr(self, '_companion_speaking', False):
                self._companion_speaking = False
            return

        if self.is_interrupted:
            self._companion_speaking = False
            self._subtitle_clear()
            return

        self._subtitle_on_speech_ended()
        if getattr(self, '_companion_speaking', False):
            self._companion_speaking = False
            self.set_state("STOPPED")
        else:
            self.set_state("LISTENING")
    
    def _subtitle_on_speech_ended(self):
        try:
            current_mode = self._get_current_mode()
            if current_mode == "Live2D Model":
                widget = self._get_model_widget_instance()
                if widget and hasattr(widget, "subtitle_overlay"):
                    widget.subtitle_overlay.on_speech_ended()
            elif current_mode == "VRM":
                if hasattr(self, "vrm_no_gui") and self.vrm_no_gui:
                    if hasattr(self.vrm_no_gui, "subtitle_overlay"):
                        self.vrm_no_gui.subtitle_overlay.on_speech_ended()
        except Exception:
            pass
 
    def _subtitle_clear(self):
        try:
            current_mode = self._get_current_mode()
            if current_mode == "Live2D Model":
                widget = self._get_model_widget_instance()
                if widget and hasattr(widget, "subtitle_overlay"):
                    widget.subtitle_overlay.clear_subtitles()
            elif current_mode == "VRM":
                if hasattr(self, "vrm_no_gui") and self.vrm_no_gui:
                    if hasattr(self.vrm_no_gui, "subtitle_overlay"):
                        self.vrm_no_gui.subtitle_overlay.clear_subtitles()
        except Exception:
            pass
    
    def update_avatar_lips(self, mouth_value):
        """Update avatar lip sync and voice indicator animation."""
        current_mode = self._get_current_mode()

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
        
        current_chat = character_info["current_chat"]
        chats = character_info.get("chats", {})

        current_emotion = chats[current_chat]["current_emotion"]
        if not current_emotion:
            configuration_data["character_list"][character_name]["chats"][current_chat]["current_emotion"] = "neutral"
            self.configuration_characters.save_configuration_edit(configuration_data)

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        conversation_method = character_info["conversation_method"]
        current_sow_system_mode = character_info["current_sow_system_mode"]
        self.current_sow_system_mode = current_sow_system_mode
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")

        current_emotion = chats[current_chat]["current_emotion"]

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        character_avatar = character_info.get("character_avatar")

        elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
        voice_type = character_info.get("voice_type")
        rvc_enabled = character_info.get("rvc_enabled")
        rvc_file = character_info.get("rvc_file")

        if conversation_method == "Local LLM":
            local_llm = self.configuration_settings.get_main_setting("local_llm")
            if local_llm is None:
                sow_toast(
                    parent=self.parent_window,
                    title=self.translations.get("llm_error_title", "No Local LLM"),
                    text=self.translations.get("llm_error_body", "Choose Local LLM in the options."),
                    msg_type="error"
                )
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
                sow_toast(
                    parent=self.parent_window,
                    title=self.translations.get("persona_error_title", "Change persona"),
                    text=self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."),
                    msg_type="error"
                )
                return

            self.ui.character_name_label.setText(character_name)

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

                self.vrm_webview = QWebEngineView()
                self.vrm_webview.setStyleSheet("""
                    border-top-right-radius: 10px;
                    border-top-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                    border-bottom-left-radius: 10px;
                """)

                self.vrm_webview.setPage(CustomWebEnginePage(self.vrm_webview))
                self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.WebGLEnabled, True)
                self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True)

                if hasattr(self, 'server_thread') and self.server_thread is not None:
                    if self.server_thread.is_alive():
                        logger.info("Stopping existing VRM server before creating new one...")
                        self.server_thread.stop()

                self.server_thread = VRMServerThread(preferred_port=8002)
                self.server_thread.start()

                html_url = f"http://127.0.0.1:{self.server_thread.port}/app/utils/emotions/vrm_module.html"
                
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
            
            self.draw_circle_avatar(character_avatar, current_sow_system_mode)

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
                sow_toast(
                    parent=self.parent_window,
                    title=self.translations.get("persona_error_title", "Change persona"),
                    text=self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."),
                    msg_type="error"
                )
                return
            
            try:
                await self.initialize_sow_system_no_gui(current_sow_system_mode)
            except Exception as e:
                return

    def on_user_speech_recognized(self, text: str, is_text_input: bool = False):
        logger.info(f"UI received text: {text}")

        live2d_mode = self.configuration_settings.get_main_setting("live2d_mode")
        is_no_gui = (live2d_mode != 0)

        if not is_text_input and not is_no_gui and self.interaction_state != "LISTENING":
            logger.debug("Speech ignored: interaction state is not LISTENING")
            return

        if self.interaction_state == "SPEAKING":
            self.interrupt_ai()

        if is_no_gui and hasattr(self, "soul_companion"):
            self.soul_companion.on_user_spoke(text)
            return

        if is_no_gui:
            return

        add_msg_task = asyncio.create_task(
            self.add_message(self.character_name, text, is_user=True, message_id=None, no_gui=False)
        )
        
        self.llm_task = asyncio.create_task(self.process_llm_response(text, add_msg_task))

    def _get_gen_kwargs(self, conversation_method: str) -> dict:
        raw_stops = self.configuration_settings.get_main_setting("stop_strings")
        stop_sequences = None
        if raw_stops and isinstance(raw_stops, str) and raw_stops.strip():
            stop_list = [s.strip() for s in raw_stops.split(",") if s.strip()]
            if stop_list:
                stop_sequences = stop_list[:4]

        gen_kwargs = {
            "stop": stop_sequences,
            "temperature": self.configuration_settings.get_main_setting("temperature"),
            "max_tokens": self.configuration_settings.get_main_setting("max_tokens"),
            "top_p": self.configuration_settings.get_main_setting("top_p"),
            "frequency_penalty": self.configuration_settings.get_main_setting("frequency_penalty"),
            "presence_penalty": self.configuration_settings.get_main_setting("presence_penalty")
        }

        if conversation_method == "Local LLM":
            gen_kwargs["reasoning_mode"] = self.configuration_settings.get_main_setting("reasoning_mode")

        return gen_kwargs
    
    async def process_llm_response(self, user_text, user_message_task):
        self.set_state("PROCESSING")
        self.is_interrupted = False

        if hasattr(self, 'tts_worker') and self.tts_worker:
            self.tts_worker._in_tts_quote = False
            self.tts_worker._in_asterisk = False

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
        _state_tag_started = False
        _in_reasoning = False
        _reasoning_scan_buffer = ""

        translator_engine = self.configuration_settings.get_main_setting("translator") # 0-Off, 1-Google, 2-Yandex, 3-LLM
        target_lang = self.configuration_settings.get_main_setting("target_language") # 0-RU

        try:
            self.llm_task = asyncio.current_task()
            
            context_messages = []
            current_chat = char_info["current_chat"]
            chat_history = char_info.get("chats", {}).get(current_chat, {}).get("chat_history", [])
            for msg in chat_history:
                if msg.get("user"): context_messages.append({"role": "user", "content": msg["user"].strip()})
                if msg.get("character"): context_messages.append({"role": "assistant", "content": msg["character"].strip()})
            
            messages, activated_lorebook_entries = self.prompt_engine.build_system_prompt_blocks(
                self.character_name, user_name, user_description, context_messages, user_text
            )

            provider = AIFactory.get_provider(conversation_method)
            if not provider:
                raise ValueError(f"Unknown method: {conversation_method}")

            gen_kwargs = self._get_gen_kwargs(conversation_method)

            stream_generator = provider.generate_stream(messages, **gen_kwargs)
            
            async for data_chunk in stream_generator:
                if self.is_interrupted:
                    logger.info("LLM generation is interrupted by the user")
                    break

                chunk = data_chunk
                if conversation_method == "OpenRouter":
                    chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk

                if not chunk:
                    continue

                full_text += chunk

                if not _state_tag_started:
                    if _in_reasoning:
                        _reasoning_scan_buffer += chunk
                        close_span = find_reasoning_close(_reasoning_scan_buffer)
                        if close_span:
                            _in_reasoning = False
                            sentence_buffer += _reasoning_scan_buffer[close_span[1]:]
                            _reasoning_scan_buffer = ""
                    else:
                        combined_buffer = sentence_buffer + chunk
                        open_span = find_reasoning_open(combined_buffer)
                        if open_span:
                            _in_reasoning = True
                            sentence_buffer = combined_buffer[:open_span[0]]
                            _reasoning_scan_buffer = combined_buffer[open_span[1]:]
                            close_span = find_reasoning_close(_reasoning_scan_buffer)
                            if close_span:
                                _in_reasoning = False
                                sentence_buffer += _reasoning_scan_buffer[close_span[1]:]
                                _reasoning_scan_buffer = ""
                        else:
                            safe_buffer = strip_partial_state_tag(combined_buffer)
                            if len(safe_buffer) < len(combined_buffer):
                                _state_tag_started = True
                            sentence_buffer = safe_buffer

                display_text = full_text
                if display_text.startswith(f"{self.character_name}:"):
                    display_text = display_text[len(f"{self.character_name}:"):].lstrip()

                display_text = strip_partial_state_tag(display_text)

                display_html = self.markdown_to_html(display_text)
                display_html = display_html.replace("{{user}}", user_name).replace("{{char}}", self.character_name)
                character_answer_label.setText(display_html)
                
                if current_sow_system_mode in ["Nothing", "Expressions Images", "Live2D Model", "VRM"]:
                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                await asyncio.sleep(0.01)

                if not _state_tag_started:
                    match = re.search(r'([.!?\n]+["”’\'»*_]*)', sentence_buffer)
                    if match:
                        split_idx = match.end()
                        sentence = sentence_buffer[:split_idx].strip()
                        
                        if len(sentence) > 2:
                            logger.info(f"Sending raw sentence to TTS: {sentence}")
                            if self.interaction_state != "SPEAKING":
                                self.set_state("SPEAKING")
                            
                            self.tts_worker.add_text(sentence)
                        
                        sentence_buffer = sentence_buffer[split_idx:]
        
        except asyncio.CancelledError:
            logger.info("The LLM task has been cancelled externally (Interrupt).")
            self.is_interrupted = True
        
        except Exception as e:
            logger.error(f"Error when generating LLM: {e}")

        if self.is_interrupted:
            full_text += " ... [Interrupted]"
            display_html = self.markdown_to_html(full_text).replace("{{user}}", user_name).replace("{{char}}", self.character_name)
            character_answer_label.setText(display_html)
            sentence_buffer = ""

        if not self.is_interrupted and not _state_tag_started and len(sentence_buffer.strip()) > 1:
            logger.info(f"Sending the remaining raw text to TTS: {sentence_buffer.strip()}")
            if self.interaction_state != "SPEAKING":
                self.set_state("SPEAKING")
            self.tts_worker.add_text(sentence_buffer.strip())

        char_data_for_vars = self.configuration_characters.load_configuration()
        sow_variables_schema = char_data_for_vars.get("character_list", {}).get(self.character_name, {}).get("sow_variables", [])
        allowed_var_ids = [v["id"] for v in sow_variables_schema] if sow_variables_schema else None

        full_text, _reasoning_text_discarded = extract_reasoning(full_text)
        full_text, state_updates = extract_state_update(full_text, allowed_keys=allowed_var_ids)
        full_text = full_text.strip()

        if state_updates:
            for var_id, delta_or_val in state_updates.items():
                try:
                    self.modify_variable_value(self.character_name, var_id, delta_or_val, operation="add")
                except Exception as e:
                    logger.error(f"Failed to apply state update for '{var_id}': {e}")

        display_html = self.markdown_to_html(full_text).replace("{{user}}", user_name).replace("{{char}}", self.character_name)
        character_answer_label.setText(display_html)

        auto_translate_setting = self.configuration_settings.get_main_setting("auto_translate_new_messages")
        auto_translate_new_messages = True if auto_translate_setting is None else bool(auto_translate_setting)
        if translator_engine in [1, 2, 3] and target_lang == 0 and auto_translate_new_messages:
            engine_name = "google" if translator_engine == 1 else "yandex"
            try:
                translated_html = self.translator.translate(display_html, engine_name, 'ru')
                character_answer_label.setText(translated_html)
                character_answer_label.setProperty("original_text", display_html)
                character_answer_label.setProperty("is_translated", True)
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

        for message_id, msg_data in sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf'))):
            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants", [])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")

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
    
    def markdown_to_html(self, text: str) -> str:
        import html
        import re

        s = {}

        qc = s.get("quote_color", "#F59E0B")
        ic = s.get("italic_color", "#9CA3AF")
        cbg = s.get("code_bg_color", "#0D0E15")
        header_bg = s.get("code_header_bg", "#161822")
        border_color = s.get("code_border", "rgba(255, 255, 255, 0.1)")
        text_color = s.get("code_text_color", "#E2E8F0")

        code_blocks = []
        inline_blocks = []
        think_blocks = []

        def replace_code_block(match):
            lang = match.group(1).strip()
            code_content = match.group(2)

            escaped_code = html.escape(code_content.strip())
            lang_display = lang.upper() if lang else "CODE"

            block_html = f'''<table width="100%" style="background-color: {cbg}; border: 1px solid {border_color}; border-radius: 8px; margin: 10px 0; border-collapse: separate; border-spacing: 0; overflow: hidden;">
        <tr>
            <td style="background-color: {header_bg}; color: #A78BFA; font-size: 10px; font-weight: bold; padding: 6px 12px; font-family: 'Consolas', 'Fira Code', monospace; border-bottom: 1px solid {border_color}; letter-spacing: 0.5px;">
                ⚡ {lang_display}
            </td>
        </tr>
        <tr>
            <td style="padding: 12px; color: {text_color}; font-size: 12px; font-family: 'Consolas', 'Fira Code', monospace; background-color: {cbg}; line-height: 1.45;">
                <pre style="margin: 0; padding: 0; font-family: 'Consolas', 'Fira Code', monospace; white-space: pre-wrap; background-color: {cbg}; color: {text_color};">{escaped_code}</pre>
            </td>
        </tr>
    </table>'''

            placeholder = f"@@@CODEBLOCK{len(code_blocks)}@@@"
            code_blocks.append(block_html)
            return placeholder

        text = re.sub(r'```([a-zA-Z0-9_+-]*)\n?(.*?)```', replace_code_block, text, flags=re.DOTALL)

        def replace_inline_code(match):
            code_content = html.escape(match.group(1))
            inline_html = f'<code style="background-color: rgba(139, 92, 246, 0.15); color: #C084FC; padding: 2px 7px; border-radius: 5px; border: 1px solid rgba(139, 92, 246, 0.3); font-family: \'Consolas\', \'Fira Code\', monospace; font-size: 0.9em; font-weight: 500;">{code_content}</code>'
            
            placeholder = f"@@@INLINECODE{len(inline_blocks)}@@@"
            inline_blocks.append(inline_html)
            return placeholder

        text = re.sub(r'`([^`]+)`', replace_inline_code, text)

        def replace_think_block(match):
            think_content = match.group(2).strip()
            if not think_content:
                return ""

            escaped_thought = html.escape(think_content).replace("\n", "<br>")

            think_html = f'''<table width="100%" style="background-color: rgba(18, 18, 26, 0.85); border: 1px solid rgba(139, 92, 246, 0.25); border-left: 4px solid #8B5CF6; border-radius: 8px; margin: 10px 0; border-collapse: separate; border-spacing: 0;">
        <tr>
            <td style="padding: 6px 12px; background-color: rgba(139, 92, 246, 0.12); color: #C084FC; font-size: 11px; font-weight: bold; font-family: 'Inter Tight', 'Segoe UI', sans-serif; letter-spacing: 0.8px;">
                💭 THINKING PROCESS
            </td>
        </tr>
        <tr>
            <td style="padding: 10px 12px; color: #A1A1AA; font-size: 12px; font-style: italic; line-height: 1.5; font-family: 'Inter Tight', 'Segoe UI', sans-serif;">
                {escaped_thought}
            </td>
        </tr>
    </table>'''

            placeholder = f"@@@THINKBLOCK{len(think_blocks)}@@@"
            think_blocks.append(think_html)
            return placeholder

        _reasoning_tag_names = (
            r"(?:think(?:ing)?|thoughts?|reasoning|reflect(?:ion)?|"
            r"scratch[_\-\s]?pad|analysis|inner[_\-\s]?monologue|monologue)"
        )
        text = re.sub(rf'<\s*({_reasoning_tag_names})\s*>(.*?)<\s*/\s*\1\s*>', replace_think_block, text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(rf'<\s*({_reasoning_tag_names})\s*>(.*)$', replace_think_block, text, flags=re.DOTALL | re.IGNORECASE)

        text = re.sub(r'"(.*?)"', rf'<span style="color: {qc}; font-weight: 500;">"\1"</span>', text)
        text = re.sub(r'“(.*?)”', rf'<span style="color: {qc}; font-weight: 500;">“\1”</span>', text)

        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

        text = re.sub(r'\*(.*?)\*', rf'<i><span style="color: {ic};">\1</span></i>', text)
        text = re.sub(r'_(.*?)_', rf'<i><span style="color: {ic};">\1</span></i>', text)

        text = re.sub(r'^#\s+(.*)$', r'<h1 style="color: #F3F4F6; font-size: 1.35em; margin: 12px 0 6px 0; font-weight: 700;">\1</h1>', text, flags=re.MULTILINE)
        text = re.sub(r'^##\s+(.*)$', r'<h2 style="color: #E5E7EB; font-size: 1.18em; margin: 10px 0 5px 0; font-weight: 600;">\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^###\s+(.*)$', r'<h3 style="color: #D1D5DB; font-size: 1.05em; margin: 8px 0 4px 0; font-weight: 600;">\1</h3>', text, flags=re.MULTILINE)

        def process_ol(match):
            block = match.group(0)
            items = re.findall(r'^\d+\.\s+(.*)$', block, flags=re.MULTILINE)
            lis = ''.join([f'<li style="margin-bottom: 3px;">{item}</li>' for item in items])
            return f'<ol style="margin: 6px 0 8px 0; padding-left: 22px; color: #D1D5DB;">{lis}</ol>'

        text = re.sub(r'(?:^\d+\.\s+.*(?:\n|$))+', process_ol, text, flags=re.MULTILINE)

        def process_ul(match):
            block = match.group(0)
            items = re.findall(r'^[\*\-]\s+(.*)$', block, flags=re.MULTILINE)
            lis = ''.join([f'<li style="margin-bottom: 3px;">{item}</li>' for item in items])
            return f'<ul style="margin: 6px 0 8px 0; padding-left: 22px; color: #D1D5DB;">{lis}</ul>'

        text = re.sub(r'(?:^[\*\-]\s+.*(?:\n|$))+', process_ul, text, flags=re.MULTILINE)

        text = text.replace('\n', '<br>')

        for i, block in enumerate(inline_blocks):
            text = text.replace(f"@@@INLINECODE{i}@@@", block)

        for i, block in enumerate(code_blocks):
            text = text.replace(f"@@@CODEBLOCK{i}@@@", block)

        for i, block in enumerate(think_blocks):
            text = text.replace(f"@@@THINKBLOCK{i}@@@", block)

        return text
    
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
            self.session = AutoModelForSequenceClassification.from_pretrained(model_path)

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)

        with torch.no_grad():
            outputs = self.session(**inputs)

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

        current_chat = character_info["current_chat"]
        configuration_data["character_list"][character_name]["chats"][current_chat]["current_emotion"] = emotion
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
        self.sanitize_and_validate_model_json(model_json_path)

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
        
        current_chat = character_info["current_chat"]
        chats = character_info.get("chats", {})
        current_emotion = chats[current_chat]["current_emotion"]

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

    async def initialize_sow_system_no_gui(self, current_sow_system_mode):
        """
        Soul Companion init
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
        """Initialize Soul Companion variables."""

        # Eye Tracker
        self._eye_tracker_timer = QtCore.QTimer(self)
        self._eye_tracker_timer.timeout.connect(self._update_eye_tracking)
        self._eye_update_interval = 100
        self._current_eye_x = 0.0
        self._current_eye_y = 0.0
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

        # Drag physics
        self._drag_velocity_x = 0.0
        self._drag_last_pos = None
        self._drag_last_time = 0

        self._drag_vel_buf = []
        self._drag_vel_buf_size = 8
        self._drag_smoothed_vx = 0.0
        self._drag_is_active = False

        self._body_tilt_target = 0.0
        self._body_tilt_current = 0.0
        self._body_tilt_alpha = 0.12

        self._target_eye_x  = 0.0
        self._target_eye_y  = 0.0
        self._target_head_x = 0.0
        self._target_head_y = 0.0
        self._target_body_x = 0.0

        self._current_eye_x  = 0.0
        self._current_eye_y  = 0.0
        self._current_head_x = 0.0
        self._current_head_y = 0.0
        self._current_body_x = 0.0

        self._eye_update_interval = 50
        self._eye_alpha   = 0.18
        self._head_alpha  = 0.10
        self._body_alpha  = 0.04

        self._eye_max_rotation      = 0.7
        self._tracking_speed_preset = "Normal"

        self._spring_return_timer = QtCore.QTimer(self)
        self._spring_return_timer.timeout.connect(self._spring_return_tick)
        self._spring_body_x    = 0.0
        self._spring_body_vel  = 0.0
        self._spring_angle_z   = 0.0
        self._spring_angle_vel = 0.0

        self._idle_anim_timer = QtCore.QTimer(self)
        self._idle_anim_timer.timeout.connect(self._idle_anim_tick)
        self._idle_target_head_x   = 0.0
        self._idle_target_head_y   = 0.0
        self._idle_target_body_x   = 0.0
        self._idle_anim_head_x     = 0.0
        self._idle_anim_head_y     = 0.0
        self._idle_anim_body_x     = 0.0
        self._idle_anim_timer.start(33)

        # Breathing micro-sway
        self._breath_timer = QtCore.QTimer(self)
        self._breath_timer.timeout.connect(self._breath_sway_tick)
        self._breath_phase  = 0.0
        self._breath_speed  = 0.018
        self._breath_amp_x  = 0.8
        self._breath_amp_z  = 0.4
        self._breath_timer.start(33)

        self._breath_sway_x = 0.0
        self._breath_sway_z = 0.0

        self._check_time_context()
        self.soul_companion = SoulCompanion(system_ref=self)
        logger.info("Desktop Companion variables initialized (Soul Companion ready)")
    
    def _start_companion_systems(self):
        self._eye_tracker_timer.start(self._eye_update_interval)
        self._idle_timer.start(self._idle_timer_interval)
        self._sleep_check_timer.start(self._sleep_check_interval)
        self._time_context_timer.start(self._time_context_interval)
        self._check_time_context()
        self.soul_companion.start()
        logger.info("Companion systems started (Soul Companion)")

    @QtCore.pyqtSlot(str)
    def _sc_speak_slot(self, text: str):
        if not (hasattr(self, "tts_worker") and self.tts_worker):
            return
        if not text or not text.strip():
            return

        is_subtitle_continuation = getattr(self, "_companion_speaking", False)
        self._companion_speaking = True
        self.is_interrupted = False
        self.tts_worker.add_text(text)
        self.set_state("SPEAKING")

        tts_duration_ms = max(8000, int(len(text) * 250 + 5000))

        current_mode = self._get_current_mode()

        if current_mode == "Live2D Model":
            widget = self._get_model_widget_instance()
            if widget and hasattr(widget, "subtitle_overlay"):
                if getattr(widget, "_subtitles_enabled", True):
                    if is_subtitle_continuation:
                        widget.subtitle_overlay.append_text(text, tts_duration_ms)
                    else:
                        widget.subtitle_overlay.show_text(text, tts_duration_ms)

        elif current_mode == "VRM":
            if hasattr(self, "vrm_no_gui") and self.vrm_no_gui:
                if hasattr(self.vrm_no_gui, "subtitle_overlay"):
                    if getattr(self.vrm_no_gui, "_subtitles_enabled", True):
                        if is_subtitle_continuation:
                            self.vrm_no_gui.subtitle_overlay.append_text(text, tts_duration_ms)
                        else:
                            self.vrm_no_gui.subtitle_overlay.show_text(text, tts_duration_ms)

        if current_mode == "Live2D Model":
            widget = self._get_model_widget_instance()
            if widget and hasattr(widget, "play_motion_safely"):
                widget.play_motion_safely("Talk")

    @QtCore.pyqtSlot(str)
    def _sc_emotion_slot(self, emotion: str):
        try:
            self._companion_set_expression(emotion)
        except Exception:
            pass

    @QtCore.pyqtSlot(str, str, str)
    def _sc_request_approval_slot(self, request_id: str, tool_name: str, summary: str):
        try:
            ActionApprovalOverlay(self, request_id, tool_name, summary)
        except Exception as e:
            logger.error(f"Failed to display Action Approval Banner for '{tool_name}': {e}")
            if hasattr(self, "soul_companion"):
                self.soul_companion.resolve_approval(request_id, False)

    def _stop_companion_systems(self):
        self._eye_tracker_timer.stop()
        self._idle_timer.stop()
        self._sleep_check_timer.stop()
        self._time_context_timer.stop()
        self._sleep_animation_timer.stop()
        self._spring_return_timer.stop()
        self._idle_anim_timer.stop()
        self._breath_timer.stop()

        if hasattr(self, "soul_companion"):
            self.soul_companion.stop()
        logger.info("Companion systems stopped (Soul Companion)")

    def get_companion_state_snapshot(self) -> dict:
        if not hasattr(self, 'soul_companion'):
            return {}
        sc = self.soul_companion
        return {
            "hormones": sc.hormones.to_dict(),
            "emotion": sc.emotion.current,
            "scratchpad": sc.scratchpad.to_string(limit=3),
            "is_sleeping": sc.hormones.is_sleeping,
            "is_lonely": sc.hormones.is_lonely,
            "last_spoke_sec_ago": int((datetime.now() - sc._last_spoke).total_seconds()),
            "last_user_input_sec_ago": int((datetime.now() - sc._last_user_input).total_seconds()),
            "is_afk": sc._is_afk,
            "enabled": sc._enabled,
        }

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
        if hasattr(self, "current_sow_system_mode"):
            return self.current_sow_system_mode
        
        try:
            return self.configuration_characters.load_configuration()[
                "character_list"][self.character_name]["current_sow_system_mode"]
        except Exception:
            return "Nothing"

    def _get_model_widget_instance(self):
        """Return the active Live2D Widget."""
        if hasattr(self, 'live2d_no_gui') and self.live2d_no_gui:
            return self.live2d_no_gui
        if hasattr(self, 'live2d_openGL_widget') and self.live2d_openGL_widget:
            return self.live2d_openGL_widget
        return None
    
    # === EYE TRACKER ===
    def _set_tracking_speed(self, preset: str):
        presets = {
            #          eye   head   body
            "Slow":   (0.08, 0.05, 0.02),
            "Normal": (0.18, 0.10, 0.04),
            "Fast":   (0.30, 0.18, 0.08),
        }
        ea, ha, ba = presets.get(preset, presets["Normal"])
        self._eye_alpha  = ea
        self._head_alpha = ha
        self._body_alpha = ba
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

            self._target_eye_x = max(-self._eye_max_rotation, min(self._eye_max_rotation, raw_x))
            self._target_eye_y = max(-self._eye_max_rotation, min(self._eye_max_rotation, raw_y))
            self._target_head_x = self._target_eye_x * 28.0
            self._target_head_y = self._target_eye_y * 22.0
            self._target_body_x = self._current_head_x * 0.30

            mode = self._get_current_mode()
            if mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(
                        f"updateLookAtTarget({self._target_eye_x:.3f}, {self._target_eye_y:.3f});"
                    )
                    wv.page().runJavaScript(
                        f"setHeadAngle({self._target_head_x:.2f}, {self._target_head_y:.2f}, 0);"
                    )
                    wv.page().runJavaScript(
                        f"setBodyAngle({self._target_body_x:.2f}, 0);"
                    )
        except Exception as e:
            logger.debug(f"Eye tracking error: {e}")

    def _step_tracking_frame(self):
        if self._is_sleeping:
            return

        if self._drag_is_active:
            vx = self._drag_smoothed_vx
            tilt_target = max(-15.0, min(15.0, vx * 0.035))
            self._body_tilt_target = tilt_target
        else:
            self._body_tilt_target = 0.0

        self._body_tilt_current += (self._body_tilt_target - self._body_tilt_current) * self._body_tilt_alpha
        tilt_z = self._body_tilt_current * 0.6

        if not self._spring_return_timer.isActive() and not self._drag_is_active:
            ea = self._eye_alpha
            ha = self._head_alpha
            ba = self._body_alpha

            self._current_eye_x  += (self._target_eye_x  - self._current_eye_x)  * ea
            self._current_eye_y  += (self._target_eye_y  - self._current_eye_y)  * ea
            self._current_head_x += (self._target_head_x - self._current_head_x) * ha
            self._current_head_y += (self._target_head_y - self._current_head_y) * ha
            self._current_body_x += (self._target_body_x - self._current_body_x) * ba

        try:
            model = self._get_model()
            if model:
                sway_x = getattr(self, "_breath_sway_x", 0.0)
                sway_z = getattr(self, "_breath_sway_z", 0.0)

                if self._drag_is_active:
                    model.SetParameterValue("ParamBodyAngleX", self._body_tilt_current)
                    model.SetParameterValue("ParamAngleZ",     tilt_z)
                elif self._spring_return_timer.isActive():
                    model.SetParameterValue("ParamEyeBallX",   self._current_eye_x)
                    model.SetParameterValue("ParamEyeBallY",   self._current_eye_y)
                    model.SetParameterValue("ParamAngleX",     self._current_head_x)
                    model.SetParameterValue("ParamAngleY",     self._current_head_y)
                else:
                    model.SetParameterValue("ParamEyeBallX",   self._current_eye_x)
                    model.SetParameterValue("ParamEyeBallY",   self._current_eye_y)
                    model.SetParameterValue("ParamAngleX",     self._current_head_x)
                    model.SetParameterValue("ParamAngleY",     self._current_head_y)
                    model.SetParameterValue("ParamBodyAngleX", self._current_body_x + sway_x)
                    model.SetParameterValue("ParamAngleZ",     sway_z)
        except Exception as e:
            logger.debug(f"Tracking frame step error: {e}")

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

    def _start_spring_return(self, initial_body_x: float, initial_angle_z: float,
                             initial_vel_x: float = 0.0, initial_vel_z: float = 0.0):
        self._spring_body_x    = initial_body_x
        self._spring_angle_z   = initial_angle_z
        self._spring_body_vel  = initial_vel_x * 0.015
        self._spring_angle_vel = initial_vel_z * 0.008
        self._spring_return_timer.start(16)

    def _spring_return_tick(self):
        k = 0.15
        d = 0.68

        for attr_x, attr_v in [("_spring_body_x",  "_spring_body_vel"),
                                ("_spring_angle_z", "_spring_angle_vel")]:
            x = getattr(self, attr_x)
            v = getattr(self, attr_v)
            f = -k * x - d * v
            v += f
            x += v
            setattr(self, attr_x, x)
            setattr(self, attr_v, v)

        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetParameterValue("ParamBodyAngleX", self._spring_body_x)
                    model.SetParameterValue("ParamAngleZ",     self._spring_angle_z)
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"setBodyAngle({self._spring_body_x:.2f}, 0);")
        except Exception as e:
            logger.debug(f"Spring return error: {e}")

        self._body_tilt_current = self._spring_body_x

        if abs(self._spring_body_x) < 0.08 and abs(self._spring_body_vel) < 0.05:
            self._spring_return_timer.stop()
            self._spring_body_x    = 0.0
            self._spring_angle_z   = 0.0
            self._spring_body_vel  = 0.0
            self._spring_angle_vel = 0.0
            self._body_tilt_current = 0.0
            self._body_tilt_target  = 0.0

    # === SMOOTH IDLE ANIMATION ===
    def _idle_anim_tick(self):
        alpha = 0.06
        self._idle_anim_head_x += (self._idle_target_head_x - self._idle_anim_head_x) * alpha
        self._idle_anim_head_y += (self._idle_target_head_y - self._idle_anim_head_y) * alpha
        self._idle_anim_body_x += (self._idle_target_body_x - self._idle_anim_body_x) * alpha

        if self._is_sleeping or not self._eye_tracker_timer.isActive():
            try:
                mode = self._get_current_mode()
                if mode == "Live2D Model":
                    model = self._get_model()
                    if model and not self._spring_return_timer.isActive():
                        model.SetParameterValue("ParamAngleX",    self._idle_anim_head_x)
                        model.SetParameterValue("ParamAngleY",    self._idle_anim_head_y)
                        model.SetParameterValue("ParamBodyAngleX", self._idle_anim_body_x)
                elif mode == "VRM":
                    wv = self._get_webview()
                    if wv and not self._spring_return_timer.isActive():
                        wv.page().runJavaScript(
                            f"setHeadAngle({self._idle_anim_head_x:.2f},"
                            f"{self._idle_anim_head_y:.2f}, 0);"
                        )
                        wv.page().runJavaScript(
                            f"setBodyAngle({self._idle_anim_body_x:.2f}, 0);"
                        )
            except Exception as e:
                logger.debug(f"Idle anim tick error: {e}")

    # === BREATHING SWAY ===
    def _breath_sway_tick(self):
        if self._is_sleeping or self.interaction_state != "STOPPED":
            return

        import math
        self._breath_phase += self._breath_speed

        self._breath_sway_x = math.sin(self._breath_phase) * self._breath_amp_x
        self._breath_sway_z = math.sin(self._breath_phase * 0.7) * self._breath_amp_z
    
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
        self._idle_target_head_x = x
        self._idle_target_head_y = y
        try:
            mode = self._get_current_mode()
            if mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"if (typeof setHeadAngle === 'function') setHeadAngle({x}, {y}, 0);")
        except Exception as e:
            logger.debug(f"Set head angle error: {e}")

    def _set_body_angle(self, x):
        self._idle_target_body_x = x
        try:
            mode = self._get_current_mode()
            if mode == "VRM":
                wv = self._get_webview()
                if wv:
                    wv.page().runJavaScript(f"if (typeof setBodyAngle === 'function') setBodyAngle({x}, 0);")
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

    _EMOTION_ANIMATION_MAP = {
        "neutral": "neutral",
        "curious": "curiosity",
        "warm": "love",
        "amused": "amusement",
        "concerned": "confusion",
        "playful": "joy",
        "relaxed": "relief",
        "sleepy": "neutral",
        "melancholy": "sadness",
        "excited": "excitement"
    }

    def _companion_set_expression(self, expression):
        try:
            mapped_expression = self._EMOTION_ANIMATION_MAP.get(expression, expression)
            
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                model = self._get_model()
                if model:
                    model.SetExpression(mapped_expression)
                    widget = self._get_model_widget_instance()
                    if widget and hasattr(widget, "play_motion_safely"):
                        widget.play_motion_safely("Idle")
            elif mode == "VRM":
                wv = self._get_webview()
                if wv:
                    vrm_expr = self._VRM_EXPRESSION_MAP.get(mapped_expression, "neutral")
                    wv.page().runJavaScript(f"setExpression('{vrm_expr}');")
        except Exception as e:
            logger.debug(f"Set expression error: {e}")
    
    def _companion_stretch(self):
        try:
            mode = self._get_current_mode()
            if mode == "Live2D Model":
                widget = self._get_model_widget_instance()
                if widget and hasattr(widget, "play_motion_safely"):
                    widget.play_motion_safely("Idle")
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
        
        if hasattr(self, "soul_companion"):
            self.soul_companion.hormones.energy = 0.0
            
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
        
        if hasattr(self, "soul_companion"):
            self.soul_companion.on_user_return_from_afk()

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

    # === INTERACTION HANDLER ===
    def companion_on_click(self):
        self._idle_time_ms = 0
        self._last_interaction_timestamp = datetime.now()

        if self._is_sleeping:
            self._wake_up()
            return

        self._companion_set_expression(random.choice(["surprise", "joy", "amusement"]))
        self._companion_blink()

        if self.interaction_state == "STOPPED" and hasattr(self, "soul_companion"):
            self.soul_companion.on_user_click()
    
    def sanitize_and_validate_model_json(self, model_json_path):
        """
        Validates and repairs .model3.json and its associated motion files.
        """
        try:
            if not model_json_path or not os.path.exists(model_json_path):
                return
                
            with open(model_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            modified = False
            base_dir = os.path.dirname(model_json_path)
            
            expressions = data.get("FileReferences", {}).get("Expressions", [])
            valid_expressions = []
            for expr in expressions:
                rel_path = expr.get("File", "")
                full_path = os.path.join(base_dir, rel_path).replace("\\", "/")
                if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                    try:
                        with open(full_path, "r", encoding="utf-8") as ef:
                            json.load(ef)
                        valid_expressions.append(expr)
                    except Exception:
                        logger.warning(f"[Live2D Sanitizer] Removing corrupted expression: {rel_path}")
                        modified = True
                else:
                    logger.warning(f"[Live2D Sanitizer] Removing missing/empty expression: {rel_path}")
                    modified = True
            if modified:
                data["FileReferences"]["Expressions"] = valid_expressions
                
            motions = data.get("FileReferences", {}).get("Motions", {})
            valid_motions = {}
            
            for group_name, motion_list in list(motions.items()):
                if isinstance(motion_list, list):
                    valid_group_list = []
                    for motion_entry in motion_list:
                        rel_path = motion_entry.get("File", "")
                        full_path = os.path.join(base_dir, rel_path).replace("\\", "/")
                        
                        if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                            try:
                                with open(full_path, "r", encoding="utf-8") as mf:
                                    motion_data = json.load(mf)
                                
                                curves = motion_data.get("Curves", [])
                                computed_segments = 0
                                computed_points = 0
                                
                                for curve in curves:
                                    segments = curve.get("Segments", [])
                                    if not segments or len(segments) < 2:
                                        continue
                                        
                                    curve_points = 1
                                    curve_segments = 0
                                    
                                    i = 2
                                    while i < len(segments):
                                        seg_type = int(segments[i])
                                        curve_segments += 1
                                        
                                        if seg_type == 0:    # Linear
                                            curve_points += 1
                                            i += 3
                                        elif seg_type == 1:  # Bezier
                                            curve_points += 3
                                            i += 7
                                        elif seg_type == 2:  # Stepped
                                            curve_points += 1
                                            i += 3
                                        elif seg_type == 3:  # Inverse Stepped
                                            curve_points += 1
                                            i += 3
                                        else:
                                            i += 1
                                            
                                    computed_segments += curve_segments
                                    computed_points += curve_points
                                    
                                meta = motion_data.get("Meta", {})
                                declared_segments = meta.get("TotalSegmentCount", 0)
                                declared_points = meta.get("TotalPointCount", 0)
                                
                                if computed_segments != declared_segments or computed_points != declared_points:
                                    logger.info(
                                        f"[Live2D Sanitizer] Fixing broken header in {os.path.basename(rel_path)}: "
                                        f"Segments: {declared_segments}➔{computed_segments}, Points: {declared_points}➔{computed_points}"
                                    )
                                    meta["TotalSegmentCount"] = computed_segments
                                    meta["TotalPointCount"] = computed_points
                                    motion_data["Meta"] = meta
                                    
                                    with open(full_path, "w", encoding="utf-8") as mf_write:
                                        json.dump(motion_data, mf_write, indent=4, ensure_ascii=False)
                                
                                valid_group_list.append(motion_entry)
                            except Exception as e:
                                logger.error(f"[Live2D Sanitizer] Discarding corrupted motion file {rel_path}: {e}")
                                modified = True
                        else:
                            logger.warning(f"[Live2D Sanitizer] Discarding missing motion: {rel_path}")
                            modified = True
                            
                    if valid_group_list:
                        valid_motions[group_name] = valid_group_list
                else:
                    valid_motions[group_name] = motion_list
                    
            if modified:
                data["FileReferences"]["Motions"] = valid_motions
                with open(model_json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                logger.info(f"[Live2D Sanitizer] Model metadata is synchronized successfully.")
                
        except Exception as e:
            logger.error(f"[Live2D Sanitizer] Error during self-healing: {e}")


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
        if not self.live2d_model:
            return

        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]
            
            current_chat = character_info["current_chat"]
            current_emotion = character_info.get("chats", {}).get(current_chat, {}).get("current_emotion", "neutral")

            if current_emotion != getattr(self, '_last_emotion_applied', None):
                self._last_emotion_applied = current_emotion
                self.live2d_model.SetExpression(current_emotion)
                
        except Exception as e:
            logger.debug(f"update_live2d_emotion error: {e}")
    
    def get_available_motions(self) -> dict[str, int]:
        try:
            if not self.model_path or not os.path.exists(self.model_path):
                return {}
            with open(self.model_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            motions_dict = data.get("FileReferences", {}).get("Motions", {})
            
            result = {}
            for group_name, motion_list in motions_dict.items():
                if isinstance(motion_list, list):
                    result[group_name] = len(motion_list)
                else:
                    result[group_name] = 1
            return result
        except Exception as e:
            logger.debug(f"Failed to parse motion groups from JSON: {e}")
            return {}

    def start_motion(self, group_name: str, no: int = 0, priority: int = 3):
        if not self.live2d_model:
            return False
        try:
            if self.sow_system_ref and hasattr(self.sow_system_ref, "_spring_return_timer"):
                self.sow_system_ref._spring_return_timer.stop()

            p = getattr(live2d, "MotionPriority", None)
            priority_val = getattr(p, "FORCE", 3) if priority == 3 else priority
            self.live2d_model.StartMotion(group_name, no, priority_val)
            return True
        except Exception as e:
            logger.debug(f"[Live2D] Failed to play motion {group_name}_{no}: {e}")
            return False

    def play_motion_safely(self, target_group: str):
        if not self.live2d_model:
            return
        available = self.get_available_motions()
        if not available:
            try:
                self.live2d_model.StartRandomMotion(priority=3)
            except Exception:
                pass
            return
        
        matched_group = None
        for g in available.keys():
            if g.lower() == target_group.lower():
                matched_group = g
                break
        
        if matched_group:
            max_index = available[matched_group]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(matched_group, random_index, 3)
        else:
            fallback_groups = ["Idle", "idle", "TapBody", "motion", "Motion"]
            for f_g in fallback_groups:
                for avail_g in available.keys():
                    if avail_g.lower() == f_g.lower():
                        max_index = available[avail_g]
                        random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
                        self.start_motion(avail_g, random_index, 3)
                        return
            
            random_g = random.choice(list(available.keys()))
            max_index = available[random_g]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(random_g, random_index, 3)

    def cleanup(self):
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
        logger.info("Widget hidden, stopping timer and releasing resources.")
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        
        self.cleanup()
        super().hideEvent(event)

    def closeEvent(self, event):
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

        self.subtitle_overlay = CompanionSubtitleOverlay(self)

        live2d.init()
        self.live2d_model = None
        self.live2d_model_loaded = False
        self.opengl_initialized = False
        self.timerId = None

        self._click_through = False
        self._always_on_top = True
        self._subtitles_enabled = True

        self._text_chat_enabled = False
        self.text_input_overlay = CompanionTextInputOverlay(self)
        self.text_input_overlay.text_submitted_signal.connect(self._on_text_chat_submitted)

        app = QtWidgets.QApplication.instance()
        existing_trays = app.findChildren(QtWidgets.QSystemTrayIcon)
        for tray in existing_trays:
            if "Desktop Companion" in tray.toolTip():
                tray.hide()
                tray.deleteLater()

        self.tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon("app/gui/icons/logotype.png"), self)
        self.tray_icon.setToolTip("Desktop Companion (Live2D)")
        tray_menu = QtWidgets.QMenu()
        action_toggle_click = tray_menu.addAction("👁‍🗨 Toggle Click-Through")
        action_toggle_click.triggered.connect(self._toggle_click_through_tray)
        action_quit = tray_menu.addAction("❌ Quit Companion")
        action_quit.triggered.connect(self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.dragging_window = False
        self.drag_offset = QtCore.QPoint()

        self.right_button_pressed = False
        self.systemScale = QGuiApplication.primaryScreen().devicePixelRatio()

    def _toggle_click_through_tray(self):
        self._click_through = not getattr(self, "_click_through", False)
        self.update_window_properties()

    def _raise_subtitle_overlay(self):
        overlay = getattr(self, "subtitle_overlay", None)
        if overlay is not None and overlay.isVisible():
            overlay.raise_()

    def update_window_properties(self):
        flags = QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
        if self._always_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        if self._click_through:
            flags |= QtCore.Qt.WindowType.WindowTransparentForInput
            
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.show()

        self._raise_subtitle_overlay()

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
        if self.sow_system_ref:
            self.sow_system_ref._step_tracking_frame()
        self.update()

    def update_live2d_emotion(self):
        if not self.live2d_model:
            return

        try:
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][self.character_name]
            
            current_chat = character_info["current_chat"]
            current_emotion = character_info.get("chats", {}).get(current_chat, {}).get("current_emotion", "neutral")

            if current_emotion != getattr(self, '_last_emotion_applied', None):
                self._last_emotion_applied = current_emotion
                self.live2d_model.SetExpression(current_emotion)
                
        except Exception as e:
            logger.debug(f"update_live2d_emotion error: {e}")
    
    def get_available_motions(self) -> dict[str, int]:
        try:
            if not self.model_path or not os.path.exists(self.model_path):
                return {}
            with open(self.model_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            motions_dict = data.get("FileReferences", {}).get("Motions", {})
            
            result = {}
            for group_name, motion_list in motions_dict.items():
                if isinstance(motion_list, list):
                    result[group_name] = len(motion_list)
                else:
                    result[group_name] = 1
            return result
        except Exception as e:
            logger.debug(f"Failed to parse motion groups from JSON: {e}")
            return {}

    def start_motion(self, group_name: str, no: int = 0, priority: int = 3):
        if not self.live2d_model:
            return False
        try:
            if self.sow_system_ref and hasattr(self.sow_system_ref, "_spring_return_timer"):
                self.sow_system_ref._spring_return_timer.stop()

            p = getattr(live2d, "MotionPriority", None)
            priority_val = getattr(p, "FORCE", 3) if priority == 3 else priority
            self.live2d_model.StartMotion(group_name, no, priority_val)
            return True
        except Exception as e:
            logger.debug(f"[Live2D] Failed to play motion {group_name}_{no}: {e}")
            return False

    def play_motion_safely(self, target_group: str):
        if not self.live2d_model:
            return
        available = self.get_available_motions()
        if not available:
            try:
                self.live2d_model.StartRandomMotion(priority=3)
            except Exception:
                pass
            return
        
        matched_group = None
        for g in available.keys():
            if g.lower() == target_group.lower():
                matched_group = g
                break
        
        if matched_group:
            max_index = available[matched_group]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(matched_group, random_index, 3)
        else:
            fallback_groups = ["Idle", "idle", "TapBody", "motion", "Motion"]
            for f_g in fallback_groups:
                for avail_g in available.keys():
                    if avail_g.lower() == f_g.lower():
                        max_index = available[avail_g]
                        random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
                        self.start_motion(avail_g, random_index, 3)
                        return
            
            random_g = random.choice(list(available.keys()))
            max_index = available[random_g]
            random_index = random.randint(0, max_index - 1) if max_index > 1 else 0
            self.start_motion(random_g, random_index, 3)

    def update_window_properties(self):
        flags = QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
        if self._always_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        if self._click_through:
            flags |= QtCore.Qt.WindowType.WindowTransparentForInput
            
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.show()

    def show_hormones_hud(self):
        if not self.sow_system_ref or not hasattr(self.sow_system_ref, "soul_companion"):
            return
        h_dict = self.sow_system_ref.soul_companion.hormones.to_dict()
        hud = HormonesHUDOverlay(self, h_dict)
        
        global_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        target_x = global_pos.x() - hud.width() - 15
        if target_x < 10:
            target_x = global_pos.x() + self.width() + 15
            
        hud.move(target_x, global_pos.y() + 40)
        hud.show()

    def show_scratchpad_hud(self):
        if not self.sow_system_ref or not hasattr(self.sow_system_ref, "soul_companion"):
            return
        scratch_str = self.sow_system_ref.soul_companion.scratchpad.to_string(limit=6)
        hud = ScratchpadHUDOverlay(self, scratch_str)
        
        global_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        target_x = global_pos.x() - hud.width() - 15
        if target_x < 10:
            target_x = global_pos.x() + self.width() + 15
            
        hud.move(target_x, global_pos.y() + 40)
        hud.show()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "subtitle_overlay"):
            self.subtitle_overlay._reposition()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._raise_subtitle_overlay()
            if self.sow_system_ref:
                ref = self.sow_system_ref
                ref._drag_is_active = True
                ref._drag_vel_buf.clear()
                ref._drag_smoothed_vx = 0.0
                ref._spring_return_timer.stop()
                ref.companion_on_click()
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = True

    def mouseMoveEvent(self, event):
        cur_pos = event.globalPosition().toPoint()
        if self.dragging_window:
            self.move(cur_pos - self.drag_offset)

            if self.sow_system_ref:
                ref = self.sow_system_ref
                now = time.time()
                ref._drag_is_active = True
                if ref._drag_last_pos is not None and (now - ref._drag_last_time) > 0:
                    dt = now - ref._drag_last_time
                    raw_vx = (cur_pos.x() - ref._drag_last_pos.x()) / max(dt, 0.001)
                    ref._drag_vel_buf.append((raw_vx, now))
                    cutoff = now - 0.15
                    ref._drag_vel_buf = [(v, t) for v, t in ref._drag_vel_buf if t >= cutoff]
                    if len(ref._drag_vel_buf) > ref._drag_vel_buf_size:
                        ref._drag_vel_buf = ref._drag_vel_buf[-ref._drag_vel_buf_size:]
                    total_w, total_v = 0.0, 0.0
                    for idx, (v, t) in enumerate(ref._drag_vel_buf):
                        w = idx + 1
                        total_v += v * w
                        total_w += w
                    ref._drag_smoothed_vx = total_v / total_w if total_w else 0.0
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
            if self.sow_system_ref:
                ref = self.sow_system_ref
                ref._drag_is_active = False

                body_x  = ref._body_tilt_current
                angle_z = body_x * 0.6
                ref._drag_vel_buf.clear()
                ref._drag_smoothed_vx = 0.0
                ref._drag_last_pos = None

                ref._spring_body_x  = body_x
                ref._spring_angle_z = angle_z
                ref._start_spring_return(body_x, angle_z)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_button_pressed = False

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(28, 28, 30, 245);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                padding: 6px;
                color: #E0E0E0;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
                margin: 2px 4px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 20);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 25);
                margin: 4px 6px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        ref = self.sow_system_ref

        def t(key, default):
            return ref.translations.get(key, default) if ref else default

        # --- 1. QUICK ACTIONS ---
        qa_menu = menu.addMenu(t("sc_menu_quick_actions", "⚡  Quick Actions"))
        qa_menu.setStyleSheet(menu.styleSheet())
        action_vision = qa_menu.addAction(t("sc_menu_vision", "📸  Look at my Screen (Vision)"))
        action_clip   = qa_menu.addAction(t("sc_menu_clipboard", "📋  Read Clipboard (Analyze)"))
        action_mind   = qa_menu.addAction(t("sc_menu_mind", "🧠  What is on your Mind?"))
        menu.addSeparator()

        # --- 2. CORE CONTROLS & DYNAMIC ANIMATIONS ---
        mic_status = t("sc_menu_mic_on", "Turn on the microphone")
        mic_icon = "🎙️"
        if ref and ref.interaction_state != "STOPPED":
            mic_status = t("sc_menu_mic_off", "Turn off the microphone")
            mic_icon = "🔇"

        action_voice  = menu.addAction(f"{mic_icon}  {mic_status}")
        action_pet    = menu.addAction(t("sc_menu_pet", "🤚  Pet"))

        available_motions = self.get_available_motions()
        if available_motions:
            anim_menu = menu.addMenu(t("sc_menu_play_animation", "🎭  Play Animation"))
            anim_menu.setStyleSheet(menu.styleSheet())
            for g_name, count in available_motions.items():
                act = anim_menu.addAction(f"🎬 {g_name} ({count} {t('sc_menu_motions', 'motions')})")
                act.triggered.connect(lambda checked, gn=g_name: self.play_motion_safely(gn))

        menu.addSeparator()

        # --- 3. HARDWARE & WIN CONTROLS ---
        click_thr_status = t("sc_menu_click_through_on", "👁‍🗨  Click-Through: ON") if getattr(self, "_click_through", False) else t("sc_menu_click_through_off", "👁‍🗨  Click-Through: OFF")
        aot_status = t("sc_menu_aot_on", "📌  Always on Top: ON") if getattr(self, "_always_on_top", True) else t("sc_menu_aot_off", "📌  Always on Top: OFF")
        action_click_thr = menu.addAction(click_thr_status)
        action_aot       = menu.addAction(aot_status)

        eye_on   = ref._eye_tracker_timer.isActive() if ref else True
        react_on = ref.soul_companion._enabled if (ref and hasattr(ref, "soul_companion")) else True
        sub_on   = getattr(self, "_subtitles_enabled", True)

        eye_lbl   = t("sc_menu_eye_on", "👁  Eye Tracking: ON")   if eye_on   else t("sc_menu_eye_off", "👁  Eye Tracking: OFF")
        react_lbl = t("sc_menu_react_on", "💬  Window Reactions: ON") if react_on else t("sc_menu_react_off", "💬  Window Reactions: OFF")
        sub_lbl   = t("sc_menu_sub_on", "📝  Subtitles: ON") if sub_on else t("sc_menu_sub_off", "📝  Subtitles: OFF")

        action_eye    = menu.addAction(eye_lbl)
        action_react  = menu.addAction(react_lbl)
        action_sub    = menu.addAction(sub_lbl)
        menu.addSeparator()

        # --- 4. COMPANION SETTINGS ---
        settings_menu = menu.addMenu(t("sc_menu_settings", "⚙️  Companion Settings"))
        settings_menu.setStyleSheet(menu.styleSheet())

        proactive_menu  = settings_menu.addMenu(t("sc_menu_proactive", "🗓  Proactive Interval"))
        proactive_menu.setStyleSheet(menu.styleSheet())
        action_3min     = proactive_menu.addAction(t("sc_menu_min_3", "3 minutes"))
        action_5min     = proactive_menu.addAction(t("sc_menu_min_5", "5 minutes"))
        action_10min    = proactive_menu.addAction(t("sc_menu_min_10", "10 minutes"))
        action_15min    = proactive_menu.addAction(t("sc_menu_min_15", "15 minutes"))
        action_30min    = proactive_menu.addAction(t("sc_menu_min_30", "30 minutes"))
        action_60min    = proactive_menu.addAction(t("sc_menu_min_60", "60 minutes"))

        sleep_menu         = settings_menu.addMenu(t("sc_menu_sleep", "😴  Sleep After"))
        sleep_menu.setStyleSheet(menu.styleSheet())
        action_sleep_3min  = sleep_menu.addAction(t("sc_menu_min_3", "3 minutes"))
        action_sleep_5min  = sleep_menu.addAction(t("sc_menu_min_5", "5 minutes"))
        action_sleep_10min = sleep_menu.addAction(t("sc_menu_min_10", "10 minutes"))

        speed_menu         = settings_menu.addMenu(t("sc_menu_speed", "👁  Tracking Speed"))
        speed_menu.setStyleSheet(menu.styleSheet())
        action_speed_slow  = speed_menu.addAction(t("sc_menu_speed_slow", "Slow"))
        action_speed_norm  = speed_menu.addAction(t("sc_menu_speed_normal", "Normal"))
        action_speed_fast  = speed_menu.addAction(t("sc_menu_speed_fast", "Fast"))

        size_menu          = settings_menu.addMenu(t("sc_menu_size", "📐  Model Size"))
        size_menu.setStyleSheet(menu.styleSheet())
        action_size_small  = size_menu.addAction(t("sc_menu_size_small", "Small  (200 × 300)"))
        action_size_medium = size_menu.addAction(t("sc_menu_size_medium", "Medium (400 × 600)"))
        action_size_large  = size_menu.addAction(t("sc_menu_size_large", "Large  (600 × 900)"))

        action_hud = settings_menu.addAction(t("sc_menu_hud", "📊  Show Hormones HUD"))
        action_scratch = qa_menu.addAction(t("sc_menu_scratchpad", "🧠  ScratchPad Thoughts"))
        action_text_mode = settings_menu.addAction(t("sc_menu_text_bar_hover", "💬  Text Chat Bar (Hover)"))

        menu.addSeparator()
        action_center = menu.addAction(t("sc_menu_center", "📍  Center on Screen"))
        action_reset  = menu.addAction(t("sc_menu_reset", "🔄  Reset Size"))
        action_close  = menu.addAction(t("sc_menu_hide", "❌  Hide Companion"))

        action = menu.exec(event.globalPos())

        if action == action_vision and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_screenshot", {})
        elif action == action_clip and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_clipboard", {})
        elif action == action_mind and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_scratchpad", {})

        elif action == action_scratch:
            self.show_scratchpad_hud()
        elif action == action_text_mode:
            self._text_chat_enabled = not getattr(self, "_text_chat_enabled", True)

        elif action == action_voice and self.toggle_voice_cb:
            self.toggle_voice_cb()
        elif action == action_pet and ref:
            ref.companion_on_click()

        elif action == action_click_thr:
            self._click_through = not getattr(self, "_click_through", False)
            self.update_window_properties()
        elif action == action_aot:
            self._always_on_top = not getattr(self, "_always_on_top", True)
            self.update_window_properties()

        elif action == action_eye and ref:
            if ref._eye_tracker_timer.isActive():
                ref._eye_tracker_timer.stop()
            else:
                ref._eye_tracker_timer.start(ref._eye_update_interval)
        elif action == action_react and ref:
            if hasattr(ref, "soul_companion"):
                ref.soul_companion.set_enabled(not ref.soul_companion._enabled)
        
        elif action == action_sub:
            self._subtitles_enabled = not getattr(self, "_subtitles_enabled", True)
            if not self._subtitles_enabled and hasattr(self, "subtitle_overlay"):
                self.subtitle_overlay.clear_subtitles()

        # Proactive Interval
        elif action == action_3min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(3 * 60)
        elif action == action_5min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(5 * 60)
        elif action == action_10min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(10 * 60)
        elif action == action_15min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(15 * 60)
        elif action == action_30min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(30 * 60)
        elif action == action_60min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(60 * 60)

        # Sleep
        elif action == action_sleep_3min  and ref: ref._sleep_threshold_ms = 3  * 60 * 1000
        elif action == action_sleep_5min  and ref: ref._sleep_threshold_ms = 5  * 60 * 1000
        elif action == action_sleep_10min and ref: ref._sleep_threshold_ms = 10 * 60 * 1000

        # Speed
        elif action == action_speed_slow and ref: ref._set_tracking_speed("Slow")
        elif action == action_speed_norm and ref: ref._set_tracking_speed("Normal")
        elif action == action_speed_fast and ref: ref._set_tracking_speed("Fast")

        # Sizes
        elif action == action_size_small:
            self.resize(200, 300)
        elif action == action_size_medium:
            self.resize(400, 600)
        elif action == action_size_large:
            self.resize(600, 900)

        elif action == action_hud:
            self.show_hormones_hud()

        # Position
        elif action == action_center:
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(screen.width() // 2 - self.width() // 2,
                      screen.height() // 2 - self.height() // 2)
        elif action == action_reset:
            self.resize(400, 600)
        elif action == action_close:
            self.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "subtitle_overlay"):
            self.subtitle_overlay._reposition()

        if hasattr(self, "text_input_overlay"):
            w = max(200, self.width() - 40)
            self.text_input_overlay.setGeometry(20, self.height() - 75, w, 36)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        step = 20 if delta > 0 else -20
        new_w, new_h = max(200, self.width() + step), max(300, self.height() + int(step * 1.5))
        self.resize(new_w, new_h)

    def enterEvent(self, event):
        if getattr(self, "_text_chat_enabled", False):
            self.text_input_overlay.show()
            self.text_input_overlay.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.text_input_overlay.hasFocus():
            self.text_input_overlay.hide()
        super().leaveEvent(event)

    def _on_text_chat_submitted(self, text: str):
        if self.sow_system_ref:
            self.sow_system_ref.on_user_speech_recognized(text, is_text_input=True)

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
 
        self.server_thread = VRMServerThread(preferred_port=8002)
        self.server_thread.start()
 
        self.vrm_webview = QWebEngineView(self)
        self.vrm_webview.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.vrm_webview.setStyleSheet("background: transparent;")
 
        web_page = CustomWebEnginePage(self.vrm_webview)
        web_page.setBackgroundColor(QColor(0, 0, 0, 0))
        self.vrm_webview.setPage(web_page)
 
        self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.WebGLEnabled, True)
        self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.vrm_webview)
 
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background: transparent;")

        self.dragging_window = False
        self.drag_offset = QtCore.QPoint()

        self._click_through = False
        self._always_on_top = True
        self._subtitles_enabled = True

        self._text_chat_enabled = False
        self.text_input_overlay = CompanionTextInputOverlay(self)
        self.text_input_overlay.text_submitted_signal.connect(self._on_text_chat_submitted)

        self.subtitle_overlay = CompanionSubtitleOverlay(self)

        self.vrm_webview.page().loadFinished.connect(self.on_load_finished)
        self.load_vrm_model()

        app = QtWidgets.QApplication.instance()
        existing_trays = app.findChildren(QtWidgets.QSystemTrayIcon)
        for tray in existing_trays:
            if "Desktop Companion" in tray.toolTip():
                tray.hide()
                tray.deleteLater()

        self.tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon("app/gui/icons/logotype.png"), self)
        self.tray_icon.setToolTip("Desktop Companion (VRM)")
        tray_menu = QtWidgets.QMenu()
        action_toggle_click = tray_menu.addAction("👁‍🗨 Toggle Click-Through")
        action_toggle_click.triggered.connect(self._toggle_click_through_tray)
        action_quit = tray_menu.addAction("❌ Quit Companion")
        action_quit.triggered.connect(self.close)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
 
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if hasattr(self, "overlay") and self.overlay:
            self.overlay.resize(self.size())
            self.overlay.raise_()

        if hasattr(self, "subtitle_overlay"):
            self.subtitle_overlay._reposition()

        if hasattr(self, "text_input_overlay"):
            w = max(200, self.width() - 40)
            self.text_input_overlay.setGeometry(20, self.height() - 75, w, 36)
            self.text_input_overlay.raise_()

    def enterEvent(self, event):
        if getattr(self, "_text_chat_enabled", False):
            self.text_input_overlay.show()
            self.text_input_overlay.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.text_input_overlay.hasFocus():
            self.text_input_overlay.hide()
        super().leaveEvent(event)

    def _toggle_click_through_tray(self):
        self._click_through = not getattr(self, "_click_through", False)
        self.update_window_properties()

    def _raise_subtitle_overlay(self):
        overlay = getattr(self, "subtitle_overlay", None)
        if overlay is not None and overlay.isVisible():
            overlay.raise_()

    def update_window_properties(self):
        flags = QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool
        if self._always_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        if self._click_through:
            flags |= QtCore.Qt.WindowType.WindowTransparentForInput
            
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.show()
        self._raise_subtitle_overlay()

    def _on_text_chat_submitted(self, text: str):
        if self.sow_system_ref:
            self.sow_system_ref.on_user_speech_recognized(text, is_text_input=True)
 
    def load_vrm_model(self):
        html_url = f"http://127.0.0.1:{self.server_thread.port}/app/utils/emotions/vrm_module_companion.html"
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

    def show_hormones_hud(self):
        if not self.sow_system_ref or not hasattr(self.sow_system_ref, "soul_companion"):
            return
        h_dict = self.sow_system_ref.soul_companion.hormones.to_dict()
        hud = HormonesHUDOverlay(self, h_dict)
        
        global_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        target_x = global_pos.x() - hud.width() - 15
        if target_x < 10:
            target_x = global_pos.x() + self.width() + 15
            
        hud.move(target_x, global_pos.y() + 40)
        hud.show()

    def show_scratchpad_hud(self):
        if not self.sow_system_ref or not hasattr(self.sow_system_ref, "soul_companion"):
            return
        scratch_str = self.sow_system_ref.soul_companion.scratchpad.to_string(limit=6)
        hud = ScratchpadHUDOverlay(self, scratch_str)
        
        global_pos = self.mapToGlobal(QtCore.QPoint(0, 0))
        target_x = global_pos.x() - hud.width() - 15
        if target_x < 10:
            target_x = global_pos.x() + self.width() + 15
            
        hud.move(target_x, global_pos.y() + 40)
        hud.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_window = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._raise_subtitle_overlay()
            if self.sow_system_ref:
                self.sow_system_ref.companion_on_click()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "subtitle_overlay"):
            self.subtitle_overlay._reposition()

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
            if self.sow_system_ref:
                ref = self.sow_system_ref
                last_vx = ref._drag_velocity_x
                last_vz = ref._drag_velocity_x
                ref._drag_velocity_x = 0.0
                ref._drag_velocity_y = 0.0
                body_x  = max(-15.0, min(15.0, last_vx * 0.04))
                angle_z = max(-10.0, min(10.0, last_vz * 0.02))
                ref._spring_body_x  = body_x
                ref._spring_angle_z = angle_z
                ref._start_spring_return(body_x, angle_z)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu(self)
        
        menu.setStyleSheet("""
            QMenu {
                background-color: rgba(28, 28, 30, 245);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 12px;
                padding: 6px;
                color: #E0E0E0;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 6px;
                margin: 2px 4px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 20);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 25);
                margin: 4px 6px;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(menu)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        menu.setGraphicsEffect(shadow)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        ref = self.sow_system_ref

        def t(key, default):
            return ref.translations.get(key, default) if ref else default

        # 1. QUICK ACTIONS
        qa_menu = menu.addMenu(t("sc_menu_quick_actions", "⚡  Quick Actions"))
        qa_menu.setStyleSheet(menu.styleSheet())
        action_vision = qa_menu.addAction(t("sc_menu_vision", "📸  Look at my Screen (Vision)"))
        action_clip   = qa_menu.addAction(t("sc_menu_clipboard", "📋  Read Clipboard (Analyze)"))
        action_mind   = qa_menu.addAction(t("sc_menu_mind", "🧠  What is on your Mind?"))
        menu.addSeparator()

        # 2. CORE CONTROLS & DYNAMIC VRM ANIMATIONS
        mic_status = t("sc_menu_mic_on", "Turn on the microphone")
        mic_icon = "🎙️"
        if ref and ref.interaction_state != "STOPPED":
            mic_status = t("sc_menu_mic_off", "Turn off the microphone")
            mic_icon = "🔇"

        action_voice  = menu.addAction(f"{mic_icon}  {mic_status}")
        action_pet    = menu.addAction(t("sc_menu_pet", "🤚  Pet"))

        vrm_anims = ["neutral", "joy", "anger", "sadness", "surprise", "relief", "love", "curiosity", "excitement"]
        anim_menu = menu.addMenu(t("sc_menu_play_animation", "🎭  Play Animation"))
        anim_menu.setStyleSheet(menu.styleSheet())
        for anim in vrm_anims:
            act = anim_menu.addAction(f"🎬 {anim.capitalize()}")
            act.triggered.connect(lambda checked, a=anim: (self.set_expression(a), self.play_animation(a)))

        menu.addSeparator()

        # 3. HARDWARE & WIN CONTROLS
        click_thr_status = t("sc_menu_click_through_on", "👁‍🗨  Click-Through: ON") if getattr(self, "_click_through", False) else t("sc_menu_click_through_off", "👁‍🗨  Click-Through: OFF")
        aot_status = t("sc_menu_aot_on", "📌  Always on Top: ON") if getattr(self, "_always_on_top", True) else t("sc_menu_aot_off", "📌  Always on Top: OFF")
        action_click_thr = menu.addAction(click_thr_status)
        action_aot       = menu.addAction(aot_status)

        eye_on   = ref._eye_tracker_timer.isActive() if ref else True
        react_on = ref.soul_companion._enabled if (ref and hasattr(ref, "soul_companion")) else True
        sub_on   = getattr(self, "_subtitles_enabled", True)

        eye_lbl   = t("sc_menu_eye_on", "👁  Eye Tracking: ON")   if eye_on   else t("sc_menu_eye_off", "👁  Eye Tracking: OFF")
        react_lbl = t("sc_menu_react_on", "💬  Window Reactions: ON") if react_on else t("sc_menu_react_off", "💬  Window Reactions: OFF")
        sub_lbl   = t("sc_menu_sub_on", "📝  Subtitles: ON") if sub_on else t("sc_menu_sub_off", "📝  Subtitles: OFF")

        action_eye    = menu.addAction(eye_lbl)
        action_react  = menu.addAction(react_lbl)
        action_sub    = menu.addAction(sub_lbl)
        menu.addSeparator()

        # 4. COMPANION SETTINGS
        settings_menu = menu.addMenu(t("sc_menu_settings", "⚙️  Companion Settings"))
        settings_menu.setStyleSheet(menu.styleSheet())

        proactive_menu  = settings_menu.addMenu(t("sc_menu_proactive", "🗓  Proactive Interval"))
        proactive_menu.setStyleSheet(menu.styleSheet())
        action_3min     = proactive_menu.addAction(t("sc_menu_min_3", "3 minutes"))
        action_5min     = proactive_menu.addAction(t("sc_menu_min_5", "5 minutes"))
        action_10min    = proactive_menu.addAction(t("sc_menu_min_10", "10 minutes"))
        action_15min    = proactive_menu.addAction(t("sc_menu_min_15", "15 minutes"))
        action_30min    = proactive_menu.addAction(t("sc_menu_min_30", "30 minutes"))
        action_60min    = proactive_menu.addAction(t("sc_menu_min_60", "60 minutes"))

        sleep_menu         = settings_menu.addMenu(t("sc_menu_sleep", "😴  Sleep After"))
        sleep_menu.setStyleSheet(menu.styleSheet())
        action_sleep_3min  = sleep_menu.addAction(t("sc_menu_min_3", "3 minutes"))
        action_sleep_5min  = sleep_menu.addAction(t("sc_menu_min_5", "5 minutes"))
        action_sleep_10min = sleep_menu.addAction(t("sc_menu_min_10", "10 minutes"))

        speed_menu         = settings_menu.addMenu(t("sc_menu_speed", "👁  Tracking Speed"))
        speed_menu.setStyleSheet(menu.styleSheet())
        action_speed_slow  = speed_menu.addAction(t("sc_menu_speed_slow", "Slow"))
        action_speed_norm  = speed_menu.addAction(t("sc_menu_speed_normal", "Normal"))
        action_speed_fast  = speed_menu.addAction(t("sc_menu_speed_fast", "Fast"))

        size_menu          = settings_menu.addMenu(t("sc_menu_size", "📐  Model Size"))
        size_menu.setStyleSheet(menu.styleSheet())
        action_size_small  = size_menu.addAction(t("sc_menu_size_small", "Small  (200 × 300)"))
        action_size_medium = size_menu.addAction(t("sc_menu_size_medium", "Medium (400 × 600)"))
        action_size_large  = size_menu.addAction(t("sc_menu_size_large", "Large  (600 × 900)"))

        action_hud = settings_menu.addAction(t("sc_menu_hud", "📊  Show Hormones HUD"))
        action_scratch = settings_menu.addAction(t("sc_menu_scratchpad", "🧠  ScratchPad Thoughts"))
        text_status = t("sc_menu_text_bar_on", "💬  Text Chat Bar (ON)") if getattr(self, "_text_chat_enabled", False) else t("sc_menu_text_bar_off", "💬  Text Chat Bar (OFF)")
        action_text_mode = settings_menu.addAction(text_status)

        menu.addSeparator()
        action_center = menu.addAction(t("sc_menu_center", "📍  Center on Screen"))
        action_reset  = menu.addAction(t("sc_menu_reset", "🔄  Reset Size"))
        action_close  = menu.addAction(t("sc_menu_hide", "❌  Hide Companion"))

        action = menu.exec(event.globalPos())

        if action == action_vision and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_screenshot", {})
        elif action == action_clip and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_clipboard", {})
        elif action == action_mind and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.event_bus.emit_threadsafe("manual_scratchpad", {})

        elif action == action_scratch:
            self.show_scratchpad_hud()
        elif action == action_text_mode:
            self._text_chat_enabled = not getattr(self, "_text_chat_enabled", False)
            if self._text_chat_enabled:
                self.text_input_overlay.show()
                self.text_input_overlay.raise_()
            else:
                self.text_input_overlay.hide()

        elif action == action_voice and self.toggle_voice_cb:
            self.toggle_voice_cb()
        elif action == action_pet and ref:
            ref.companion_on_click()

        elif action == action_click_thr:
            self._click_through = not getattr(self, "_click_through", False)
            self.update_window_properties()
        elif action == action_aot:
            self._always_on_top = not getattr(self, "_always_on_top", True)
            self.update_window_properties()

        elif action == action_eye and ref:
            if ref._eye_tracker_timer.isActive():
                ref._eye_tracker_timer.stop()
            else:
                ref._eye_tracker_timer.start(ref._eye_update_interval)
        elif action == action_react and ref:
            if hasattr(ref, "soul_companion"):
                ref.soul_companion.set_enabled(not ref.soul_companion._enabled)

        elif action == action_sub:
            self._subtitles_enabled = not getattr(self, "_subtitles_enabled", True)
            if not self._subtitles_enabled and hasattr(self, "subtitle_overlay"):
                self.subtitle_overlay.clear_subtitles()

        # Proactive Interval
        elif action == action_3min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(3 * 60)
        elif action == action_5min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(5 * 60)
        elif action == action_10min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(10 * 60)
        elif action == action_15min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(15 * 60)
        elif action == action_30min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(30 * 60)
        elif action == action_60min and ref and hasattr(ref, "soul_companion"):
            ref.soul_companion.set_heartbeat_interval(60 * 60)

        # Sleep
        elif action == action_sleep_3min  and ref: ref._sleep_threshold_ms = 3  * 60 * 1000
        elif action == action_sleep_5min  and ref: ref._sleep_threshold_ms = 5  * 60 * 1000
        elif action == action_sleep_10min and ref: ref._sleep_threshold_ms = 10 * 60 * 1000

        # Speed
        elif action == action_speed_slow and ref: ref._set_tracking_speed("Slow")
        elif action == action_speed_norm and ref: ref._set_tracking_speed("Normal")
        elif action == action_speed_fast and ref: ref._set_tracking_speed("Fast")

        # Sizes
        elif action == action_size_small:
            self.resize(200, 300)
        elif action == action_size_medium:
            self.resize(400, 600)
        elif action == action_size_large:
            self.resize(600, 900)

        elif action == action_hud:
            self.show_hormones_hud()

        # Position
        elif action == action_center:
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
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
            self.tray_icon.deleteLater()
            
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

class CompanionSubtitleOverlay(QWidget):
    FONT_MAX_PX    = 40
    FONT_MIN_PX    = 18
    PADDING_X      = 22
    PADDING_Y      = 10
    BOTTOM_MARGIN  = 130
    MAX_LINES      = 3
    FADE_IN_MS     = 85
    FADE_OUT_MS    = 380
    MIN_INTERVAL   = 80
    MAX_INTERVAL   = 700
 
    def __init__(self, parent=None):
        super().__init__(None)
        self._anchor_widget = parent
        if parent is not None:
            try:
                parent.destroyed.connect(self.deleteLater)
            except Exception:
                pass
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setStyleSheet("background: transparent; border: none;")

        self._full_text    : str   = ""
        self._words        : list  = []
        self._revealed_idx : int   = 0
        self._opacity      : float = 0.0

        self._reveal_timer = QtCore.QTimer(self)
        self._reveal_timer.timeout.connect(self._reveal_next)
 
        self._hide_timer = QtCore.QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)
 
        self._fade_anim = None

        self._font = QFont()
        self._font.setFamily("Comfortaa")
        self._font.setStyleHint(QFont.StyleHint.SansSerif)
        self._font.setWeight(QFont.Weight.Bold)
        self._font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self._font_px = self.FONT_MAX_PX
        self._font.setPixelSize(self._font_px)
 
        self.hide()

    @QtCore.pyqtProperty(float)
    def opacity(self) -> float:
        return self._opacity
 
    @opacity.setter
    def opacity(self, val: float):
        self._opacity = max(0.0, min(1.0, float(val)))
        self.update()

    def _calculate_word_delay(self, word: str) -> int:
        clean_word = re.sub(r"[^\wа-яА-Яa-zA-Z]", "", word)
        
        char_time = len(clean_word) * 45
        base_gap = 100
        total_delay = char_time + base_gap
        
        if "," in word or ";" in word or ":" in word or "—" in word:
            total_delay += 200
        if "." in word or "!" in word or "?" in word:
            total_delay += 450

        return max(self.MIN_INTERVAL, min(self.MAX_INTERVAL, total_delay))
 
    def show_text(self, text: str, tts_duration_ms: int = 5000):
        text = text.strip()
        if not text:
            self.clear_subtitles()
            return
 
        self._stop_all()
 
        self._full_text    = text
        self._words        = text.split()
        self._revealed_idx = 0
        self._opacity      = 0.0
 
        if not self._words:
            return

        self._font_px = self._calc_font_px(text)
        self._font.setPixelSize(self._font_px)

        self._reposition()
 
        self.show()
        self.raise_()

        self._reveal_next()
        
        first_interval = self._calculate_word_delay(self._words[0])
        self._reveal_timer.start(first_interval)

        self._hide_timer.start(tts_duration_ms + 3000)
 
    def append_text(self, text: str, tts_duration_ms: int = 5000):
        text = text.strip()
        if not text:
            return

        if not self._full_text:
            self.show_text(text, tts_duration_ms)
            return

        self._hide_timer.stop()

        self._full_text = f"{self._full_text} {text}".strip()
        new_words = text.split()
        self._words.extend(new_words)

        self._font_px = self._calc_font_px(self._full_text)
        self._font.setPixelSize(self._font_px)
        self._reposition()

        if not self.isVisible():
            self.show()
            self.raise_()

        if not self._reveal_timer.isActive():
            if self._revealed_idx < len(self._words):
                next_interval = self._calculate_word_delay(self._words[self._revealed_idx])
                self._reveal_timer.start(next_interval)

        self._hide_timer.start(tts_duration_ms + 3000)

    def on_speech_ended(self):
        if not self._full_text:
            return

        if self._revealed_idx < len(self._words):
            self._reveal_timer.stop()
            self._revealed_idx = len(self._words)
            self.update()

        self._hide_timer.stop()
        self._hide_timer.start(1200)
 
    def clear_subtitles(self):
        self._stop_all()
        self._full_text    = ""
        self._words        = []
        self._revealed_idx = 0
        self._opacity      = 0.0
        self.hide()
        self.update()
 
    def _revealed_text(self) -> str:
        return " ".join(self._words[:self._revealed_idx])
 
    def _reveal_next(self):
        if self._revealed_idx >= len(self._words):
            self._reveal_timer.stop()
            return
        
        self._revealed_idx += 1
        if self._opacity < 1.0:
            self._animate_opacity(self._opacity, 1.0, self.FADE_IN_MS)
        self.update()
        self.raise_()

        if self._revealed_idx < len(self._words):
            next_word = self._words[self._revealed_idx]
            next_interval = self._calculate_word_delay(next_word)
            self._reveal_timer.setInterval(next_interval)
 
    def _start_fade_out(self):
        self._reveal_timer.stop()
        self._animate_opacity(
            self._opacity, 0.0, self.FADE_OUT_MS,
            on_finish=self._on_fade_done
        )
 
    def _on_fade_done(self):
        if self._opacity <= 0.02:
            self.clear_subtitles()
 
    def _animate_opacity(self, start: float, end: float, dur_ms: int,
                         on_finish=None):
        if self._fade_anim is not None:
            try:
                self._fade_anim.stop()
            except Exception:
                pass
            self._fade_anim = None
 
        anim = QtCore.QPropertyAnimation(self, b"opacity", self)
        anim.setDuration(dur_ms)
        anim.setStartValue(float(start))
        anim.setEndValue(float(end))
        anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        if on_finish:
            anim.finished.connect(on_finish)
        anim.start()
        self._fade_anim = anim
 
    def _stop_all(self):
        if self._fade_anim is not None:
            try:
                self._fade_anim.stop()
            except Exception:
                pass
            self._fade_anim = None
        self._reveal_timer.stop()
        self._hide_timer.stop()
 
    def _get_available_width(self) -> int:
        w = self.width()
        if w <= 0:
            p = self._anchor_widget
            if p:
                w = p.width() - 30
            else:
                w = 370
        return max(w - self.PADDING_X * 2, 80)
 
    def _calc_font_px(self, text: str) -> int:
        avail_w = self._get_available_width()
        for px in range(self.FONT_MAX_PX, self.FONT_MIN_PX - 1, -1):
            f = QFont(self._font)
            f.setPixelSize(px)
            fm = QtGui.QFontMetrics(f)
            br = fm.boundingRect(
                0, 0, avail_w, 100000,
                int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.TextFlag.TextWordWrap),
                text
            )
            if br.height() <= fm.height() * self.MAX_LINES + 4:
                return px
        return self.FONT_MIN_PX
 
    def _calc_needed_height(self, text: str) -> int:
        avail_w = self._get_available_width()
        f = QFont(self._font)
        f.setPixelSize(self._font_px)
        fm = QtGui.QFontMetrics(f)
        br = fm.boundingRect(
            0, 0, avail_w, 100000,
            int(Qt.AlignmentFlag.AlignHCenter) | int(Qt.TextFlag.TextWordWrap),
            text
        )
        return br.height() + self.PADDING_Y * 2
 
    def _reposition(self):
        parent = self._anchor_widget
        if not parent:
            return
 
        pw = parent.width()
        ph = parent.height()
 
        slot_w = max(pw - 30, 60)
        slot_x = 15

        self.resize(slot_w, self.height() if self.height() > 0 else 80)
 
        if self._full_text:
            self._font_px = self._calc_font_px(self._full_text)
            self._font.setPixelSize(self._font_px)
            needed_h = max(self._calc_needed_height(self._full_text), 36)
        else:
            needed_h = 80
 
        new_y = ph - needed_h - self.BOTTOM_MARGIN
        global_pos = parent.mapToGlobal(QtCore.QPoint(slot_x, new_y))
        self.setGeometry(global_pos.x(), global_pos.y(), slot_w, needed_h)
 
    @safe_paint
    def paintEvent(self, event):
        text = self._revealed_text()
        if not text or self._opacity <= 0.01:
            return
 
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
 
        alpha = int(self._opacity * 255)
        rect  = self.rect().adjusted(
            self.PADDING_X, self.PADDING_Y,
            -self.PADDING_X, -self.PADDING_Y
        )
        flags = (
            int(Qt.AlignmentFlag.AlignHCenter) |
            int(Qt.AlignmentFlag.AlignVCenter) |
            int(Qt.TextFlag.TextWordWrap)
        )
 
        painter.setFont(self._font)
 
        os_ = max(2, self._font_px // 10)
        oc  = QColor(0, 0, 0, int(alpha * 0.93))
        painter.setPen(oc)
        for dx, dy in [
            (-os_, -os_), (0, -os_), (os_, -os_),
            (-os_,    0),            (os_,    0),
            (-os_,  os_), (0,  os_), (os_,  os_),
            (-os_,  0  ), (os_,  0  ),
            (0,    -os_), (0,    os_),
        ]:
            painter.drawText(rect.translated(dx, dy), flags, text)
 
        painter.setPen(QColor(255, 255, 255, alpha))
        painter.drawText(rect, flags, text)

class HormonesHUDOverlay(QtWidgets.QWidget):
    def __init__(self, parent, hormones_dict):
        super().__init__(None)

        ref = getattr(parent, "sow_system_ref", None)
        def t(k, default):
            return ref.translations.get(k, default) if ref and hasattr(ref, "translations") else default
        
        self.setWindowFlags(
            QtCore.Qt.WindowType.Tool | 
            QtCore.Qt.WindowType.FramelessWindowHint | 
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(0)

        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("HormonesCard")
        self.card.setStyleSheet("""
            QFrame#HormonesCard {
                background-color: #13131C;
                border: 2px solid #8B5CF6;
                border-radius: 16px;
            }
            QLabel {
                color: #F3F4F6;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 11px;
                border: none;
                background: transparent;
            }
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                background-color: #09090D;
                text-align: right;
                color: transparent;
                height: 8px;
            }
            QProgressBar::chunk {
                border-radius: 3px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(8)
        
        title_lbl = QtWidgets.QLabel(t("sc_hud_hormones_title", "Endocrine & Hormone Balance"))
        title_lbl.setStyleSheet("font-size: 12px; color: #A78BFA; font-weight: bold; margin-bottom: 2px;")
        card_layout.addWidget(title_lbl)
        
        bars_info = [
            (t("sc_hud_oxytocin", "🧪 Oxytocin (Love)"), "oxytocin", "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff758c, stop:1 #ff7eb3)"),
            (t("sc_hud_dopamine", "⚡ Dopamine (Focus)"), "dopamine", "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4facfe, stop:1 #00f2fe)"),
            (t("sc_hud_cortisol", "🔥 Cortisol (Stress)"), "cortisol", "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0844, stop:1 #ffb199)"),
            (t("sc_hud_energy", "🔋 Energy (Vigor)"), "energy", "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #43e97b, stop:1 #38f9d7)"),
        ]
        
        for label_text, key, chunk_style in bars_info:
            val = hormones_dict.get(key, 0.5)
            pct = int(max(0, min(1, val)) * 100)
            
            lbl = QtWidgets.QLabel(f"{label_text}: {pct}%")
            bar = QtWidgets.QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setStyleSheet(f"QProgressBar::chunk {{ background: {chunk_style}; }}")
            
            card_layout.addWidget(lbl)
            card_layout.addWidget(bar)

        outer_layout.addWidget(self.card)
        self.setFixedWidth(300)
        self.adjustSize()
        
        self._opacity = 0.0
        self._opacity_anim = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(220)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()
        
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)
        self._timer.start(7000)

    def _start_fade_out(self):
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(300)
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.deleteLater)
        self._opacity_anim.start()
        
    @QtCore.pyqtProperty(float)
    def windowOpacity(self) -> float:
        return self._opacity
        
    @windowOpacity.setter
    def windowOpacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)

class ScratchpadHUDOverlay(QtWidgets.QWidget):
    def __init__(self, parent, scratchpad_str: str):
        super().__init__(None)

        ref = getattr(parent, "sow_system_ref", None)
        def t(k, default):
            return ref.translations.get(k, default) if ref and hasattr(ref, "translations") else default
        
        self.setWindowFlags(
            QtCore.Qt.WindowType.Tool | 
            QtCore.Qt.WindowType.FramelessWindowHint | 
            QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(0)

        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("ScratchCard")
        self.card.setStyleSheet("""
            QFrame#ScratchCard {
                background-color: #13131C;
                border: 2px solid #C084FC;
                border-radius: 16px;
            }
            QLabel {
                color: #E5E7EB;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                border: none;
                background: transparent;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(8)
        
        title_lbl = QtWidgets.QLabel(t("sc_hud_scratchpad_title", "🧠 Companion's Internal Thoughts"))
        title_lbl.setStyleSheet("font-size: 12px; color: #C084FC; font-weight: bold; margin-bottom: 4px;")
        card_layout.addWidget(title_lbl)

        body_lbl = QtWidgets.QLabel(scratchpad_str)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("font-size: 11px; color: #D1D5DB; line-height: 1.45;")
        card_layout.addWidget(body_lbl)

        outer_layout.addWidget(self.card)
        self.setFixedWidth(340)
        self.adjustSize()

        self._opacity = 0.0
        self._opacity_anim = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(220)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()
        
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)
        self._timer.start(8000)

    def _start_fade_out(self):
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(300)
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.deleteLater)
        self._opacity_anim.start()

    @QtCore.pyqtProperty(float)
    def windowOpacity(self) -> float:
        return self._opacity

    @windowOpacity.setter
    def windowOpacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)

class ActionApprovalOverlay(QtWidgets.QWidget):
    """
    Human-in-the-Loop confirmation banner.
    """
    TIMEOUT_SEC = 25

    def __init__(self, sow_system_ref, request_id: str, tool_name: str, summary: str):
        super().__init__(None)

        self.sow_system_ref = sow_system_ref
        self.request_id = request_id
        self._resolved = False

        self._target_hwnd = None
        if sys.platform == "win32":
            try:
                self._target_hwnd = ctypes.windll.user32.GetForegroundWindow()
            except Exception:
                pass

        def t(k, default):
            return sow_system_ref.translations.get(k, default) if sow_system_ref and hasattr(sow_system_ref, "translations") else default

        self.setWindowFlags(
            QtCore.Qt.WindowType.Tool |
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(14, 14, 14, 14)
        outer_layout.setSpacing(0)

        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("ApprovalCard")
        self.card.setStyleSheet("""
            QFrame#ApprovalCard {
                background-color: #13131C;
                border: 2px solid #F59E0B;
                border-radius: 16px;
            }
            QLabel {
                color: #E5E7EB;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                border: none;
                background: transparent;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QtWidgets.QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        title_lbl = QtWidgets.QLabel(t("sc_approval_title", "⚠️ Companion wants to perform an action"))
        title_lbl.setStyleSheet("font-size: 13px; color: #F59E0B; font-weight: bold;")
        card_layout.addWidget(title_lbl)

        tool_lbl = QtWidgets.QLabel(f"{t('sc_approval_action', 'Action')}: {tool_name}")
        tool_lbl.setWordWrap(True)
        tool_lbl.setStyleSheet("font-size: 11px; color: #A78BFA; font-weight: bold;")
        card_layout.addWidget(tool_lbl)

        body_lbl = QtWidgets.QLabel(summary)
        body_lbl.setWordWrap(True)
        body_lbl.setStyleSheet("font-size: 12px; color: #D1D5DB; line-height: 1.4;")
        card_layout.addWidget(body_lbl)

        self._timer_bar = QtWidgets.QProgressBar()
        self._timer_bar.setRange(0, self.TIMEOUT_SEC * 10)
        self._timer_bar.setValue(self.TIMEOUT_SEC * 10)
        self._timer_bar.setTextVisible(False)
        self._timer_bar.setFixedHeight(4)
        self._timer_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 2px;
                background-color: #09090D;
            }
            QProgressBar::chunk {
                border-radius: 2px;
                background-color: #F59E0B;
            }
        """)
        card_layout.addWidget(self._timer_bar)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        self.deny_btn = QtWidgets.QPushButton(t("sc_approval_deny", "✕ Decline"))
        self.deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.deny_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(239, 68, 68, 0.15);
                color: #F87171;
                border: 1px solid #EF4444;
                border-radius: 10px;
                padding: 8px 14px;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(239, 68, 68, 0.30); }
        """)
        self.deny_btn.clicked.connect(lambda: self._resolve(False))

        self.allow_btn = QtWidgets.QPushButton(t("sc_approval_allow", "✓ Allow"))
        self.allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.allow_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(34, 197, 94, 0.18);
                color: #4ADE80;
                border: 1px solid #22C55E;
                border-radius: 10px;
                padding: 8px 14px;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(34, 197, 94, 0.32); }
        """)
        self.allow_btn.clicked.connect(lambda: self._resolve(True))

        btn_row.addWidget(self.deny_btn)
        btn_row.addWidget(self.allow_btn)
        card_layout.addLayout(btn_row)

        outer_layout.addWidget(self.card)

        self.setFixedWidth(380)
        self.adjustSize()

        screen = QGuiApplication.primaryScreen().geometry()
        self.move(
            screen.width() // 2 - self.width() // 2,
            screen.height() - self.height() - 70
        )

        self._opacity = 0.0
        self._opacity_anim = QtCore.QPropertyAnimation(self, b"windowOpacity", self)
        self._opacity_anim.setDuration(220)
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()

        self._elapsed_ticks = 0
        self._countdown_timer = QtCore.QTimer(self)
        self._countdown_timer.timeout.connect(self._tick)
        self._countdown_timer.start(100)

        self.show()
        self.raise_()

    def _tick(self):
        self._elapsed_ticks += 1
        remaining = self.TIMEOUT_SEC * 10 - self._elapsed_ticks
        self._timer_bar.setValue(max(0, remaining))
        if remaining <= 0:
            self._resolve(False)

    def _resolve(self, approved: bool):
        if self._resolved:
            return
        self._resolved = True
        self._countdown_timer.stop()

        if approved and sys.platform == "win32" and self._target_hwnd:
            try:
                user32 = ctypes.windll.user32
                VK_MENU = 0x12
                user32.keybd_event(VK_MENU, 0, 0, 0)
                user32.keybd_event(VK_MENU, 0, 2, 0)
                user32.SetForegroundWindow(self._target_hwnd)
                time.sleep(0.06)
            except Exception as e:
                logger.debug(f"[Approval] Error restoring target window focus: {e}")

        if self.sow_system_ref and hasattr(self.sow_system_ref, "soul_companion"):
            try:
                self.sow_system_ref.soul_companion.resolve_approval(self.request_id, approved)
            except Exception as e:
                logger.error(f"Failed to resolve approval '{self.request_id}': {e}")

        self._start_fade_out()

    def _start_fade_out(self):
        self._opacity_anim.stop()
        self._opacity_anim.setDuration(250)
        self._opacity_anim.setStartValue(self._opacity)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self.deleteLater)
        self._opacity_anim.start()

    @QtCore.pyqtProperty(float)
    def windowOpacity(self) -> float:
        return self._opacity

    @windowOpacity.setter
    def windowOpacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)

class CompanionTextInputOverlay(QtWidgets.QLineEdit):
    """
    A semi-transparent, compact text input field for communicating with companion without a microphone.
    """
    text_submitted_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        ref = getattr(parent, "sow_system_ref", None) if parent else None
        def t(k, default):
            return ref.translations.get(k, default) if ref and hasattr(ref, "translations") else default

        self.setPlaceholderText(t("sc_input_placeholder", "Write your text..."))
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(24, 24, 32, 0.85);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                padding: 6px 12px;
                font-family: 'Comfortaa', 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #A78BFA;
                background-color: rgba(24, 24, 32, 0.95);
            }
        """)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

        self.returnPressed.connect(self._on_submit)
        self.hide()

    def _on_submit(self):
        text = self.text().strip()
        if text:
            self.text_submitted_signal.emit(text)
            self.clear()
            self.hide()
