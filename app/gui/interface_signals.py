import os
import re
import ssl
import shutil
import uuid
import json
import base64
import hashlib
import logging
import threading
import datetime
import time
import webbrowser
import urllib.request
from pathlib import Path

import yaml
import torch
import aiohttp
import asyncio
import tiktoken
import edge_tts
import sounddevice as sd
from socketserver import TCPServer
from PIL import Image, PngImagePlugin
from qasync import asyncSlot
from http.server import SimpleHTTPRequestHandler
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtCore import QUrl, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QPainter, QAction, QColor, QCursor
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QMessageBox, QPushButton,
    QWidget, QHBoxLayout, QDialog, QVBoxLayout, QStackedWidget, QFileDialog,
    QGraphicsDropShadowEffect, QFrame, QMenu, QTextEdit, QLineEdit, QColorDialog, QSlider, QSpinBox,
    QScrollArea, QSizePolicy, QGridLayout, QFormLayout
)

from app.utils.ai_clients.local_server_manager import LocalServerManager
from app.utils.ai_clients.prompt_engine import PromptEngine
from app.utils.ai_clients.ai_factory import AIFactory
from app.utils.ai_clients.soul_stage_engine import (
        SoulStageOrchestrator,
        SoulStageSession,
    )

from app.gui.custom_widgets import PersonasEditorDialog, SystemPromptEditorDialog, DiscordGatewayDialog, LorebookEditorDialog, AuthorNotesEditorDialog, SummaryEditorDialog, ImageGenSettingsDialog
from app.gui.custom_widgets import (
    Live2DWidget, AnimatedHoverButton, TextEditUserMessage, SmoothMessageFrame, TypingIndicatorWidget, TypewriterEffect,
    CharacterCardCharactersGateway, SceneGatewayCard, LorebookGatewayCard, CharacterCardList, CharacterFolderCard, MethodCard, ModelListItemWidget, 
    EditorCharacterItemWidget, BackgroundChangerWindow, SoulMemoryViewer, AboutDialog,
    ResponsiveEmotionLabel, MultiSelectDialog, UpdaterDialog, sow_toast, SowConfirmDialog, Live2DMotionLinkerDialog
)

from app.utils.translator import Translator
from app.utils.character_cards import CharactersCard, SoulGateway
from app.utils.text_to_speech import ElevenLabs, XTTSv2_SOW_System, EdgeTTS, KokoroTTS_SOW_System, SileroTTS_SOW_System, Qwen3TTS_SOW_System, AudioPlaybackWorker
from app.utils.ambient_client import AmbientPlayer
from app.utils.models_hub import ModelSearch, ModelRecommendations, ModelPopular, ModelInformation, ModelRepoFiles, FileSelectorDialog, FileDownloader, ModelItemWidget, RecommendedModelItemWidget
from app.gui.sow_system_signals import Soul_Of_Waifu_System
from app.configuration import configuration

logger = logging.getLogger("Interface Signals")

CACHE_DIR = os.path.join(os.getcwd(), "app/cache")

tiktoken_dir = Path(__file__).parent.parent.parent / "app" / "utils" / "ai_clients"
if not (tiktoken_dir / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4").exists():
    logger.warning("Tiktoken offline cache file is missing. Token counting may fail!")
os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_dir)

DEFAULT_EMOTION_MOTIONS = {
    "admiration": "Happy",     "amusement": "Laugh",     "anger": "Anger",
    "annoyance": "Anger",      "approval": "Happy",      "caring": "Idle",
    "confusion": "Doubt",      "curiosity": "Doubt",     "desire": "Happy",
    "disappointment": "Sad",   "disapproval": "Anger",   "disgust": "Anger",
    "embarrassment": "Shame",  "excitement": "Happy",     "fear": "Cry",
    "gratitude": "Happy",      "grief": "Cry",           "love": "Happy",
    "nervousness": "Doubt",    "neutral": "Idle",        "optimism": "Happy",
    "pride": "Pride",          "realization": "Surprise","relief": "Idle",
    "remorse": "Sad",          "surprise": "Surprise",   "joy": "Happy",
    "sadness": "Sad"
}

class InterfaceSignals():
    """
    A central class managing UI signals, widgets, and integration with backend services.
    """
    def __init__(self, ui, main_window):
        super(InterfaceSignals, self).__init__()
        self.ui = ui
        self.main_window = main_window

        # --- Model & Session Data ---
        self.model = None
        self.tokenizer = None
        self.models = []
        self.filtered_models = []
        self._openrouter_models_task = None
        self._model_test_task = None
        self._editor_provider_value = None

        self.emotion_task = None

        self.web_server_task = None
        self.web_server_instance = None
        self.web_server_running = False

        # --- Card Management ---
        self.cards = []
        self.soul_cards = []
        self.gate_cards = []
        self.lorebook_cards = []
        self.scene_cards = []

        # --- Scroll Area Setup ---
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(0, 20, 20, 20)
        self.container = QWidget()
        self.container.setLayout(self.grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_characters_list, self.container)

        self.soul_gateway_grid_layout = QtWidgets.QGridLayout()
        self.soul_gateway_grid_layout.setSpacing(10)
        self.soul_gateway_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.soul_gateway_container = QWidget()
        self.soul_gateway_container.setLayout(self.soul_gateway_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_soul_gateway, self.soul_gateway_container)

        self.gate_cards_grid_layout = QtWidgets.QGridLayout()
        self.gate_cards_grid_layout.setSpacing(10)
        self.gate_cards_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.gate_container = QWidget()
        self.gate_container.setLayout(self.gate_cards_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_character_card, self.gate_container)

        self.lorebooks_grid_layout = QtWidgets.QGridLayout()
        self.lorebooks_grid_layout.setSpacing(10)
        self.lorebooks_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.lorebooks_container = QWidget()
        self.lorebooks_container.setLayout(self.lorebooks_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_lorebooks, self.lorebooks_container)

        self.scenes_grid_layout = QtWidgets.QGridLayout()
        self.scenes_grid_layout.setSpacing(10)
        self.scenes_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.scenes_container = QWidget()
        self.scenes_container.setLayout(self.scenes_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_scenes, self.scenes_container)

        # --- Chat Input Setup ---
        self.textEdit_write_user_message = self._replace_text_edit()

        # --- Chat Display Setup ---
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setSpacing(5)

        self.messages = {}

        # --- Emotion Resources ---
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

        # --- UI Components ---
        self.live2d_widget = None
        self.expression_widget = None
        self.stackedWidget_expressions = None

        self.model_information_widget = None
        self.search_worker = None
        self.recommendations_worker = None
        self.popular_worker = None

        self.is_loading = False
        self.abort_loading = False
        self.abort_generation = False

        self._editing_character_name = None

        self.active_hud_widgets = {}

        # --- Configuration Initialization ---
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.configuration_settings.update_main_setting("conversation_method", "Local LLM")

        # --- AI Client Initialization ---
        self.prompt_engine = PromptEngine()
        self.local_server_manager = LocalServerManager(self.ui)

        # --- Soul Stage ---
        self.soul_stage_orchestrator = SoulStageOrchestrator(
            prompt_engine=self.prompt_engine,
            local_server_manager=self.local_server_manager
        )
        self.soul_stage_session = None
        self._soul_stage_scene_id: str = None
        self.soul_stage_party_bar = None

        # --- Utility Modules ---
        self.translator = Translator()
        self.character_card_client = CharactersCard()
        self.soul_gateway_client = SoulGateway()

        # --- AUDIO PLAYER & LIPSYNC SETUP ---
        output_device = self.configuration_settings.get_main_setting("output_device_real_index")
        
        self.playback_worker = AudioPlaybackWorker(output_device)
        self.playback_worker.lipsync_signal.connect(self.update_lip_sync)
        self.playback_worker.start()

        self.current_active_character = None

        # --- Token Counter ---
        self.tokenizer_character = tiktoken.get_encoding("cl100k_base")

        # --- Translation System Setup ---
        self.translations = {}
        self.selected_language = self.configuration_settings.get_main_setting("program_language")
        match self.selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.ui.toggle_sidebar_btn.clicked.connect(self.toggle_sidebar)
        s = self.get_chat_appearance()
        wt = self.get_window_theme()
        u = self.get_ui_appearance()
        self.ui.appearance_settings_tab.set_data(s, wt, u)
        
        self.ui.appearance_settings_tab.chatAppearanceChanged.connect(self.on_chat_appearance_changed)
        self.ui.appearance_settings_tab.windowThemeChanged.connect(self.on_window_theme_changed)
        self.ui.appearance_settings_tab.uiAppearanceChanged.connect(self.on_ui_appearance_changed)
        self.ui.appearance_settings_tab.requestChatPreviewUpdate.connect(self.on_request_chat_preview_update)
        self.ui.appearance_settings_tab.resetAppearanceRequested.connect(self.on_reset_appearance)
        self.ui.appearance_settings_tab.saveChatAppearanceRequested.connect(self.on_save_chat_appearance)
        self.ui.lineEdit_search_openrouter_models.textChanged.connect(self.filter_models)
        self.ui.comboBox_openrouter_models.currentIndexChanged.connect(self.on_comboBox_openrouter_models_changed)
        self.ui.pushButton_reload_openrouter_models.clicked.connect(self.initialize_openrouter_models)
        QtCore.QTimer.singleShot(100, lambda: self.apply_gui_theme(self.get_gui_theme()))
        self.apply_window_theme()
        
        self._selected_lorebooks_building = []
        self._replace_lorebook_building_with_button()
        if hasattr(self.ui, "button_tts_inworld_load_voices"):
            self.ui.button_tts_inworld_load_voices.clicked.connect(
                lambda: asyncio.create_task(self.load_global_inworld_voices())
            )
            self.ui.button_tts_inworld_preview.clicked.connect(
                lambda: asyncio.create_task(self.preview_global_inworld_voice())
            )
        QtCore.QTimer.singleShot(0, self.refresh_provider_verification_status)

    def _replace_lorebook_building_with_button(self):
        self.ui.comboBox_lorebook_building.hide()
        
        self.btn_lorebook_building = QPushButton("None")
        self.btn_lorebook_building.setFont(self.ui.comboBox_lorebook_building.font())
        self.btn_lorebook_building.setFixedHeight(40)
        self.btn_lorebook_building.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.btn_lorebook_building.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 15, 18, 0.4);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        
        if self.ui.comboBox_lorebook_building.parentWidget():
            parent_layout = self.ui.comboBox_lorebook_building.parentWidget().layout()
            if parent_layout:
                parent_layout.replaceWidget(self.ui.comboBox_lorebook_building, self.btn_lorebook_building)
            else:
                self.btn_lorebook_building.setParent(self.ui.comboBox_lorebook_building.parentWidget())
        
        self.btn_lorebook_building.clicked.connect(self.open_lorebook_selector_main)

    def _update_lorebook_button_text(self):
        """Updates the text on the lorebook button based on selected books."""
        selected = self._selected_lorebooks_building
        if not selected:
            self.btn_lorebook_building.setText("None")
        elif len(selected) == 1:
            self.btn_lorebook_building.setText(selected[0])
        else:
            self.btn_lorebook_building.setText(f"Selected: {len(selected)}")

    def open_lorebook_selector_main(self):
        """Opens the multi-select dialog for lorebooks in the main character editor."""
        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})
        all_lorebooks = sorted(list(user_data.get("lorebooks", {}).keys()))
        
        dialog = MultiSelectDialog(
            self.translations.get("lorebook_selector_title", "Select Lorebooks"),
            all_lorebooks,
            self._selected_lorebooks_building,
            self.translations,
            self.main_window
        )
        
        if dialog.exec():
            self._selected_lorebooks_building = dialog.get_selected_items()
            self._update_lorebook_button_text()
            self.update_token_count()

    ### SETUP BUTTONS ==================================================================================
    def load_local_tiktoken_bpe(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        bpe_merges = [
            tuple(line.strip().split()) for line in lines
            if line.strip() and not line.startswith("#")
        ]

        mergeable_ranks = {
            bytes(part1 + part2, encoding="utf-8"): idx
            for idx, (part1, part2) in enumerate(bpe_merges)
        }

        return mergeable_ranks

    def toggle_sidebar(self):
        width = self.ui.SideBar_Left.width()
        
        if width == 0:
            new_width = 190
        else:
            new_width = 0

        self.animation_min = QPropertyAnimation(self.ui.SideBar_Left, b"minimumWidth")
        self.animation_min.setDuration(300)
        self.animation_min.setStartValue(width)
        self.animation_min.setEndValue(new_width)
        self.animation_min.setEasingCurve(QEasingCurve.Type.InOutQuart)

        self.animation_max = QPropertyAnimation(self.ui.SideBar_Left, b"maximumWidth")
        self.animation_max.setDuration(300)
        self.animation_max.setStartValue(width)
        self.animation_max.setEndValue(new_width)
        self.animation_max.setEasingCurve(QEasingCurve.Type.InOutQuart)

        self.animation_min.start()
        self.animation_max.start()

    def get_chat_appearance(self):
        defaults = {
            "user_bubble_color": "#292929",
            "char_bubble_color": "#222222",
            "text_color": "#DCDCDC",
            "font_size": 14,
            "font_family": "Inter Tight Medium",
            "border_radius": 15,
            "bubble_opacity": 100,
            "quote_color": "#FFA500",
            "italic_color": "#a3a3a3",
            "code_bg_color": "#1a1a1a",
            "max_width": 750,
        }
        saved = self.configuration_settings.get_main_setting("chat_appearance") or {}
        return {**defaults, **saved}

    def _hex_to_rgba(self, hex_color, alpha_pct):
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = round(alpha_pct / 100, 2)
        return f"rgba({r},{g},{b},{a})"

    def _bubble_stylesheet(self, s, is_user):
        r = s["border_radius"]
        fs = s["font_size"]
        tc = s["text_color"]
        op = s["bubble_opacity"]
        if is_user:
            bg = self._hex_to_rgba(s["user_bubble_color"], op)
            return f"""
                QLabel {{
                    background-color: {bg};
                    color: {tc};
                    border-top-left-radius: {r}px;
                    border-bottom-left-radius: {r}px;
                    border-bottom-right-radius: 0px;
                    border-top-right-radius: {r}px;
                    padding: 12px;
                    font-size: {fs}px;
                    margin: 5px;
                    letter-spacing: 0.5px;
                }}
            """
        else:
            bg = self._hex_to_rgba(s["char_bubble_color"], op)
            return f"""
                QLabel {{
                    background-color: {bg};
                    color: {tc};
                    border-top-right-radius: {r}px;
                    border-bottom-right-radius: {r}px;
                    border-top-left-radius: {r}px;
                    border-bottom-left-radius: 0px;
                    padding: 12px;
                    font-size: {fs}px;
                    margin: 5px;
                    letter-spacing: 0.5px;
                    text-align: justify;
                    white-space: pre-line;
                }}
            """

    def apply_chat_appearance_to_all(self, s):
        for msg in self.messages.values():
            label = msg.get("label")
            is_user = msg.get("is_user", False)
            if label:
                label.setStyleSheet(self._bubble_stylesheet(s, is_user))
    
    def on_chat_appearance_changed(self, s):
        self.apply_chat_appearance_to_all(s)

    def on_window_theme_changed(self, wt):
        self.apply_window_theme(wt)
        self.apply_gui_theme(wt["theme_name"])
        self.apply_sidebar_styles(self.ui.appearance_settings_tab.u, wt)
        self.configuration_settings.update_main_setting("window_theme", dict(wt))
        self.configuration_settings.update_main_setting("ui_appearance", dict(self.ui.appearance_settings_tab.u))

    def on_ui_appearance_changed(self, u):
        wt = self.ui.appearance_settings_tab.wt
        self.apply_sidebar_styles(u, wt)
        self.configuration_settings.update_main_setting("ui_appearance", dict(u))
        
    def on_request_chat_preview_update(self):
        self.ui.appearance_settings_tab.update_preview()
        
    def on_reset_appearance(self):
        self.configuration_settings.update_main_setting("chat_appearance", {})
        s = self.get_chat_appearance()
        wt = self.get_window_theme()
        u = self.get_ui_appearance()
        self.ui.appearance_settings_tab.set_data(s, wt, u)
        self.apply_chat_appearance_to_all(s)
        
    def on_save_chat_appearance(self, s):
        self.configuration_settings.update_main_setting("chat_appearance", dict(s))

    def get_window_theme(self):
        defaults = {
            "theme_name": "default",
            "bg_primary":   "27,27,27",
            "bg_secondary": "22,22,22", 
            "border_color": "50,50,55",
        }
        saved = self.configuration_settings.get_main_setting("window_theme") or {}
        return {**defaults, **saved}

    def apply_window_theme(self, t=None):
        if t is None:
            t = self.get_window_theme()

        bp  = t["bg_primary"]
        bs  = t["bg_secondary"]
        bdr = t["border_color"]

        self.ui.main_widget.setStyleSheet(
            f"#main_widget {{ border: 1px solid rgb({bdr}); }}"
        )

        self.ui.menu_bar.setStyleSheet(
            f"#menu_bar {{ background-color: rgb({bp}); }}"
        )

        self.apply_sidebar_styles(wt=t)

        page_ss = f"background-color: rgb({bp});"
        for widget_name in [
            "SideBar_Right", "stackedWidget",
            "main_no_characters_page", "main_characters_page",
            "create_character_page", "charactersgateway_page",
            "modelshub_page", "options_page",
        ]:
            w = getattr(self.ui, widget_name, None)
            if w:
                if widget_name == "SideBar_Right":
                    w.setStyleSheet(
                        f"#SideBar_Right {{ background-color: rgb({bp}); color: rgb(227,227,227); }}"
                    )
                else:
                    w.setStyleSheet(page_ss)

    def get_gui_theme(self):
        return self.configuration_settings.get_main_setting("gui_theme") or "default"

    def apply_gui_theme(self, theme_name):
        THEMES = {
            "default": {"name": "Default Dark", "bg": "27, 27, 27",  "bg2": "43, 43, 43",  "bg3": "60, 60, 60",  "border": "55, 55, 55", "text": "227, 227, 227", "text_dim": "179, 179, 179"},
            "darker":  {"name": "Abyss",        "bg": "15, 15, 15",  "bg2": "28, 28, 28",  "bg3": "40, 40, 40",  "border": "38, 38, 38", "text": "210, 210, 210", "text_dim": "150, 150, 150"},
            "slate":   {"name": "Slate",        "bg": "22, 28, 36",  "bg2": "32, 40, 50",  "bg3": "45, 55, 70",  "border": "44, 56, 72", "text": "220, 230, 240", "text_dim": "160, 175, 190"},
            "warm":    {"name": "Warm Dark",    "bg": "30, 24, 18",  "bg2": "42, 34, 26",  "bg3": "55, 45, 35",  "border": "60, 48, 36", "text": "235, 225, 215", "text_dim": "190, 180, 170"},
            "violet":  {"name": "Violet",       "bg": "20, 18, 30",  "bg2": "32, 28, 45",  "bg3": "45, 40, 60",  "border": "48, 42, 70", "text": "230, 225, 240", "text_dim": "180, 170, 200"},
            "forest":  {"name": "Forest",       "bg": "18, 26, 20",  "bg2": "26, 36, 28",  "bg3": "35, 48, 38",  "border": "30, 48, 35", "text": "220, 235, 225", "text_dim": "160, 180, 170"},
        }

        t = THEMES.get(theme_name, THEMES["default"])
        bg = t["bg"]
        bg2 = t["bg2"]
        bg3 = t["bg3"]
        border = t["border"]

        qss = f"""
            QWidget#main_widget, QWidget#centralwidget,
            QStackedWidget,
            QWidget#main_characters_page,
            QWidget#main_no_characters_page,
            QWidget#options_page,
            QWidget#menu_bar,
            QWidget#SideBar_Right,
            QFrame#frame_character_building,
            QWidget#scrollAreaWidgetContents_character_building,
            QFrame#frame_send_message_full {{
                background-color: rgb({bg});
            }}

            QWidget#SideBar_Right {{
                color: rgb(227, 227, 227);
            }}

            QScrollArea#scrollArea_characters_list {{
                background-color: rgb({bg});
                color: rgb(227, 227, 227);
                border: none;
                padding-left: 25px;
            }}

            QScrollArea#scrollArea_character_building {{
                border: none;
                background-color: rgb({bg});
                margin-right: 50px;
                margin-left: 50px;
            }}

            QScrollArea#scrollArea_modules {{
                border: none;
                background-color: rgb({bg});
            }}

            QScrollBar:vertical {{
                background: transparent;
                background-color: transparent;
                width: 12px;
                margin: 15px 0px 15px 0px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: transparent;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgb({bg3});
            }}
            QScrollBar::handle:vertical:pressed {{
                background-color: rgb({border});
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                background-color: transparent;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
                background-color: transparent;
            }}

            QScrollArea#scrollArea_characters_list QScrollBar:vertical,
            QScrollArea#scrollArea_characters_list QScrollBar:horizontal {{
                width: 0px;
                height: 0px;
                background: transparent;
                background-color: transparent;
            }}

            QScrollBar:horizontal {{
                background-color: rgb({bg});
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: rgb({bg2});
                width: 10px;
                border-radius: 3px;
                margin: 2px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: rgb({bg3});
            }}
            QScrollBar::handle:horizontal:pressed {{
                background-color: rgb({border});
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                border: none;
                background: none;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}

            QFrame#frame_main_button {{
                background-color: rgb({bg2});
            }}
            QTabWidget::pane {{
                background-color: rgb({bg2});
                border: 1px solid rgb({border});
            }}
            QTabBar::tab {{
                background-color: rgb({bg3});
                color: rgb(190,190,190);
                border-radius: 4px;
                padding: 5px 12px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: rgb({bg});
                color: rgb(220,220,220);
            }}
            QTabBar::tab:hover {{
                background-color: rgb({bg2});
            }}
        """

        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)

        self.configuration_settings.update_main_setting("gui_theme", theme_name)

    def get_ui_appearance(self):
        defaults = {
            "sidebar_accent":    "#A0A0A0",
            "sidebar_hover":     "#1B1B1B",
            "sidebar_opacity":   100,
            "sidebar_text":      "#D2D2D2",
        }
        saved = self.configuration_settings.get_main_setting("ui_appearance") or {}
        return {**defaults, **saved}

    def apply_sidebar_styles(self, u=None, wt=None):
        if u is None:
            u = self.get_ui_appearance()
            
        ac = u["sidebar_accent"]
        hv = u["sidebar_hover"]
        op = u["sidebar_opacity"]
        alpha = int(op * 2.55)

        tc = u.get("sidebar_text", "#D2D2D2")
        btn_style = f"""
            QPushButton {{
                color: {tc};
                background-position: left center;
                background-repeat: no-repeat;
                border: none;
                background-color: transparent;
                text-align: left;
                padding-left: 10px;
                height: 50px;
            }}
            QPushButton:hover {{
                background-color: {hv};
                color: rgb(210, 210, 210);
            }}
            QPushButton:pressed {{
                background-color: {hv};
                color: rgb(210, 210, 210);
            }}
            QPushButton:checked {{
                background-color: {hv};
                color: rgb(210, 210, 210);
                border-left: 3px solid {ac};
            }}
        """
        nav_buttons = [
            self.ui.pushButton_main,
            self.ui.pushButton_soul_stage,
            self.ui.pushButton_rp_editors,
            self.ui.pushButton_characters_gateway,
            self.ui.pushButton_models_hub,
            self.ui.pushButton_options,
        ]
        for btn in nav_buttons:
            btn.setStyleSheet(btn_style)

        if wt is None:
            wt = self.get_window_theme()
            
        bp  = wt["bg_primary"]
        try:
            r, g, b = [int(x.strip()) for x in bp.split(",")]
            r2, g2, b2 = min(r+11, 255), min(g+11, 255), min(b+11, 255)
            r3, g3, b3 = min(r+15, 255), min(g+15, 255), min(b+15, 255)
            r4, g4, b4 = min(r+19, 255), min(g+19, 255), min(b+19, 255)
            r5, g5, b5 = min(r+23, 255), min(g+23, 255), min(b+23, 255)
        except:
            r, g, b = 27, 27, 27
            r2,g2,b2, r3,g3,b3, r4,g4,b4, r5,g5,b5 = 38,38,38, 42,42,42, 46,46,46, 50,50,50

        self.ui.SideBar_Left.setStyleSheet(
            f"#SideBar_Left {{ "
            f"background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 rgba({r},{g},{b},{alpha}), stop:0.25 rgba({r2},{g2},{b2},{alpha}), "
            f"stop:0.5 rgba({r3},{g3},{b3},{alpha}), stop:0.75 rgba({r4},{g4},{b4},{alpha}), "
            f"stop:1 rgba({r5},{g5},{b5},{alpha})); }}"
        )

    def _scroll_character_creation(self, index):
        if hasattr(self.ui, 'creation_cards_mapping') and index in self.ui.creation_cards_mapping:
            target_widget = self.ui.creation_cards_mapping[index]
            
            target_y = target_widget.pos().y()
            
            scrollbar = self.ui.scrollArea_character_building.verticalScrollBar()
            
            if hasattr(self, 'creation_scroll_anim') and self.creation_scroll_anim.state() == QtCore.QAbstractAnimation.State.Running:
                self.creation_scroll_anim.stop()
                
            self.creation_scroll_anim = QPropertyAnimation(scrollbar, b"value")
            self.creation_scroll_anim.setDuration(450)
            self.creation_scroll_anim.setStartValue(scrollbar.value())
            self.creation_scroll_anim.setEndValue(min(target_y, scrollbar.maximum())) 
            self.creation_scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.creation_scroll_anim.start()
    
    def _update_anchor_menu_from_scroll(self, value):
        if not hasattr(self.ui, 'creation_cards_mapping'):
            return

        if hasattr(self, 'creation_scroll_anim') and self.creation_scroll_anim.state() == QtCore.QAbstractAnimation.State.Running:
            return

        current_index = 0
        scroll_area = self.ui.scrollArea_character_building
        viewport_height = scroll_area.viewport().height()

        for idx, card in self.ui.creation_cards_mapping.items():
            card_y = card.pos().y()
            if value + (viewport_height / 3) >= card_y:
                current_index = idx

        if self.ui.anchor_menu_building.currentRow() != current_index:
            self.ui.anchor_menu_building.blockSignals(True)
            self.ui.anchor_menu_building.setCurrentRow(current_index)
            self.ui.anchor_menu_building.blockSignals(False)
    
    def _show_raw_prompt_preview(self):
        char_name = self.ui.lineEdit_character_name_building.text().strip() or "Char"
        user_name = "User"
        
        description = self.ui.textEdit_character_description_building.toPlainText().strip()
        personality = self.ui.textEdit_character_personality_building.toPlainText().strip()
        scenario = self.ui.textEdit_scenario.toPlainText().strip()
        examples = self.ui.textEdit_example_messages.toPlainText().strip()
        
        raw_prompt = f"System:\nWrite {{char}}'s next reply in a fictional roleplay chat with {{user}}.\n\n"
        raw_prompt += f"[Character Name: {char_name}]\n\n"
        
        if description:
            raw_prompt += f"[Description:\n{description}]\n\n"
        if personality:
            raw_prompt += f"[Personality:\n{personality}]\n\n"
        if scenario:
            raw_prompt += f"[Scenario: {scenario}]\n\n"
        if examples:
            raw_prompt += f"[Dialogue Examples:\n{examples}]\n\n"
            
        raw_prompt = self.apply_macros(raw_prompt, char_name, user_name)

        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(self.translations.get("preview_prompt_title", "Raw Prompt Preview"))
        dialog.setMinimumSize(700, 600)
        dialog.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QTextEdit {
                background-color: #151518;
                color: #a0a0b0;
                font-family: 'Consolas', 'Courier New';
                font-size: 13px;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel { color: #d0d0d0; font-family: 'Inter Tight SemiBold'; font-size: 14px; }
        """)
        
        layout = QVBoxLayout(dialog)
        
        title = QLabel(self.translations.get("preview_prompt_desc", "This is approximately how the LLM model sees your character card before generating a response:"))
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        title.setFont(font)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(raw_prompt)
        text_edit.setFont(font)
        
        layout.addWidget(title)
        layout.addWidget(text_edit)
        
        dialog.exec()

    def on_tts_audio_ready(self, audio_b64: str):
        if hasattr(self, 'web_bridge') and self.web_bridge:
            asyncio.create_task(self.web_bridge.broadcast_audio(audio_b64))

    def update_lip_sync(self, value):
        if hasattr(self, 'web_bridge') and self.web_bridge:
            asyncio.create_task(self.web_bridge.manager.broadcast({"type": "avatar_telemetry", "volume": value}))

        if not self.current_active_character:
            return

        if not hasattr(self, 'expression_widget') or not self.expression_widget or not self.expression_widget.isVisible():
            return
            
        config = self.configuration_characters.load_configuration()
        if self.current_active_character not in config["character_list"]:
            return
            
        mode = config["character_list"][self.current_active_character]["current_sow_system_mode"]

        if mode == "Live2D Model":
            if hasattr(self, 'live2d_widget') and self.live2d_widget and self.live2d_widget.isVisible():
                if self.live2d_widget.live2d_model:
                    self.live2d_widget.live2d_model.SetParameterValue("ParamMouthOpenY", value)
                    
        elif mode == "VRM":
            if hasattr(self, 'vrm_webview') and self.vrm_webview and self.vrm_webview.isVisible():
                self.vrm_webview.page().runJavaScript(f"setMouthOpen({value});")

    def _setup_scroll_area(self, scroll_area, widget):
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setWidget(widget)
    
    def _replace_text_edit(self):
        original_name = self.ui.textEdit_write_user_message.objectName()
        original_parent = self.ui.textEdit_write_user_message.parent()
        layout = self.ui.horizontalLayout_3

        self.ui.textEdit_write_user_message.deleteLater()

        self.ui.textEdit_write_user_message = TextEditUserMessage(parent=original_parent)
        self.ui.textEdit_write_user_message.setObjectName(original_name)
        
        font_input = QtGui.QFont("Inter Tight Medium", 10)
        font_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.ui.textEdit_write_user_message.setFont(font_input)

        self.ui.textEdit_write_user_message.setMinimumSize(QtCore.QSize(0, 40))
        self.ui.textEdit_write_user_message.setMaximumSize(QtCore.QSize(800, 16777215))
        self.ui.textEdit_write_user_message.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.ui.textEdit_write_user_message.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhMultiLine)
        self.ui.textEdit_write_user_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.ui.textEdit_write_user_message.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.ui.textEdit_write_user_message.setAutoFormatting(QtWidgets.QTextEdit.AutoFormattingFlag.AutoNone)
        self.ui.textEdit_write_user_message.setAcceptRichText(False)
        self.ui.textEdit_write_user_message.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.ui.textEdit_write_user_message.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        layout.insertWidget(1, self.ui.textEdit_write_user_message)

        self.ui.frame_send_message.setMinimumHeight(40)
        self.ui.frame_send_message.setMaximumHeight(40)

        self.ui.frame_send_message_full.setMinimumHeight(40)
        self.ui.frame_send_message_full.setMaximumHeight(40)

        self.ui.textEdit_write_user_message.textChanged.connect(self._adjust_frame_height)

        return self.ui.textEdit_write_user_message
    
    def _adjust_frame_height(self):
        """
        Dynamically and smoothly adjusts the height of the message input frame.
        """
        doc_height = self.ui.textEdit_write_user_message.document().size().height()
        padding_vertical = 16
        target_height = int(doc_height + padding_vertical)

        target_height = max(40, min(target_height, 400))

        current_height = self.ui.frame_send_message.height()

        if current_height == target_height:
            return

        if hasattr(self, '_resize_animation_group') and self._resize_animation_group.state() == QtCore.QAbstractAnimation.State.Running:
            self._resize_animation_group.stop()

        self._resize_animation_group = QtCore.QParallelAnimationGroup(self.main_window)
        duration = 100

        anim1 = QPropertyAnimation(self.ui.frame_send_message, b"minimumHeight")
        anim1.setDuration(duration)
        anim1.setStartValue(current_height)
        anim1.setEndValue(target_height)
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim2 = QPropertyAnimation(self.ui.frame_send_message, b"maximumHeight")
        anim2.setDuration(duration)
        anim2.setStartValue(current_height)
        anim2.setEndValue(target_height)
        anim2.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim3 = QPropertyAnimation(self.ui.frame_send_message_full, b"minimumHeight")
        anim3.setDuration(duration)
        anim3.setStartValue(current_height)
        anim3.setEndValue(target_height)
        anim3.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim4 = QPropertyAnimation(self.ui.frame_send_message_full, b"maximumHeight")
        anim4.setDuration(duration)
        anim4.setStartValue(current_height)
        anim4.setEndValue(target_height)
        anim4.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._resize_animation_group.addAnimation(anim1)
        self._resize_animation_group.addAnimation(anim2)
        self._resize_animation_group.addAnimation(anim3)
        self._resize_animation_group.addAnimation(anim4)

        def scroll_down():
            scroll_bar = self.ui.scrollArea_chat.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())

        anim1.valueChanged.connect(lambda val: scroll_down())

        self._resize_animation_group.start()

    def load_translation(self, language):
        """
        Loads translation data from a YAML file based on the program language.
        """
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
    
    def set_about_program_button(self):
        dialog = AboutDialog(parent=self.main_window, translations=self.translations)
        dialog.exec()

    def on_pushButton_main_clicked(self):
        asyncio.create_task(self.set_main_tab())

    def on_pushButton_options_clicked(self):
        self.ui.pushButton_options.setChecked(True)
        self.ui.stackedWidget.setCurrentWidget(self.ui.options_page)

    def on_pushButton_models_hub_clicked(self):
        self.ui.pushButton_models_hub.setChecked(True)
        self.ui.stackedWidget.setCurrentWidget(self.ui.modelshub_page)
        QApplication.processEvents()
        self.show_my_models()

    def on_pushButton_launch_server_clicked(self):
        asyncio.create_task(self.local_server_manager.ensure_server_running())

    def on_toggle_web_server(self):
        if not self.web_server_running:
            self.web_server_running = True
            self.ui.label_web_server_status.setText(self.translations.get("web_server_starting_lbl", "Status: Starting..."))
            self.ui.label_web_server_status.setStyleSheet("color: #ff9d00; padding-left: 5px;")
            self.ui.pushButton_toggle_web_server.setText("Starting...")
            
            self.web_server_task = asyncio.create_task(self.start_server_async())
            
            self.ui.label_web_server_status.setText(self.translations.get("web_server_starting_lbl_2", "Status: Running on http://127.0.0.1:8000"))
            self.ui.label_web_server_status.setStyleSheet("color: #4ade80; padding-left: 5px;")
            self.ui.pushButton_toggle_web_server.setText(self.translations.get("web_server_stop_btn", "Stop Server"))
            self.ui.pushButton_open_web_browser.setEnabled(True)
        else:
            asyncio.create_task(self.stop_server_async())
            
            self.web_server_running = False
            self.ui.label_web_server_status.setText(self.translations.get("web_server_status_stopped", "Status: Stopped"))
            self.ui.label_web_server_status.setStyleSheet("color: #909090; padding-left: 5px;")
            self.ui.pushButton_toggle_web_server.setText(self.translations.get("web_server_start_btn", "Start Server"))
            self.ui.pushButton_open_web_browser.setEnabled(False)

    async def start_server_async(self):
        try:
            from app.utils.web_server import WebBridge
            import uvicorn
            
            self.web_bridge = WebBridge(self)
            
            config = uvicorn.Config(
                app=self.web_bridge.app,
                host="0.0.0.0",
                port=8000,
                log_level="warning",
                loop="asyncio"
            )
            
            self.web_server_instance = uvicorn.Server(config)
            await self.web_server_instance.serve()
            
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Failed to start local Web Server: {e}")
            
            self.web_server_running = False
            self.ui.label_web_server_status.setText(self.translations.get("web_server_error", "Status: Port 8000 busy or Error"))
            self.ui.label_web_server_status.setStyleSheet("color: #f87171; padding-left: 5px;")
            self.ui.pushButton_toggle_web_server.setText(self.translations.get("web_server_start_btn", "Start Server"))
            self.ui.pushButton_open_web_browser.setEnabled(False)
            self.web_server_instance = None
            self.web_server_task = None

    async def stop_server_async(self):
        if self.web_server_instance:
            self.web_server_instance.should_exit = True
            await self.web_server_instance.shutdown()
            
        if self.web_server_task:
            self.web_server_task.cancel()
            try:
                await self.web_server_task
            except asyncio.CancelledError:
                pass
            self.web_server_task = None
            
        self.web_server_instance = None

    def on_open_web_browser(self):
        webbrowser.open("http://127.0.0.1:8000")

    def on_youtube(self):
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/@jofizcd"))

    def on_discord(self):
        QDesktopServices.openUrl(QUrl("https://discord.gg/6vFtQGVfxM"))

    def on_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/jofizcd/Soul-of-Waifu"))

    def open_personas_editor(self):
        dialog = PersonasEditorDialog(self.translations, self.configuration_settings, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_system_prompt_editor(self):
        dialog = SystemPromptEditorDialog(self.translations, self.configuration_settings, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_discord_gateway(self):
        dialog = DiscordGatewayDialog(self.translations, self.configuration_api, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_lorebook_editor(self):
        dialog = LorebookEditorDialog(self.translations, self.configuration_settings, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_author_notes_editor(self):
        dialog = AuthorNotesEditorDialog(self.translations, self.configuration_settings, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_summary_editor(self, character_name, conversation_method):
        dialog = SummaryEditorDialog(self.translations, self.configuration_characters, self.configuration_settings, character_name, conversation_method, self.main_window, parent=self.main_window)
        dialog.exec()

    def open_chat_background_changer(self):
        dialog = BackgroundChangerWindow(ui=self.ui, translation=self.translations)
        dialog.exec()

    def add_character_sync(self):
        task = asyncio.create_task(self.add_character())
        task.add_done_callback(self.on_add_character_done)

    def on_add_character_done(self, task):
        """
        Handles the result of adding a character to the program.
        Displays a sleek success or error message based on the task result.
        """
        result = task.result()

        if result:
            character_name = result
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("add_character_title", "Character Added"),
                text=f"{character_name} · {self.translations.get('add_character_text_1', 'was successfully added!')}",
                msg_type="success"
            )
        else:
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("error_title", "Import Error"),
                text=self.translations.get("add_character_text_3", "There was an error while adding the character."),
                msg_type="error",
                duration=6000
            )

    async def add_character(self):
        """
        Adds a character to the list based on the currently selected conversation method.
        """
        character_configuration = self.configuration_characters.load_configuration()
        character_list = character_configuration["character_list"]
        conversation_method = self._editor_provider_value or self.configuration_settings.get_main_setting("conversation_method")
        if self._editing_character_name is None and not self._editor_provider_value:
            sow_toast(
                parent=self.main_window,
                title="Character Settings",
                text="Check a provider model in Configuration before creating a character.",
                msg_type="error"
            )
            return None
        
        def handle_generic_ai(method_name):
            """
            Handles adding a character for generic AI methods.
            """
            try:
                character_name = self.ui.lineEdit_character_name_building.text().strip()
                character_avatar_directory = self.configuration_settings.get_user_data("current_character_image")

                if character_avatar_directory == "None" or character_avatar_directory is None:
                    character_avatar_directory = "app/gui/icons/logotype.png"

                character_description = self.ui.textEdit_character_description_building.toPlainText()
                character_personality = self.ui.textEdit_character_personality_building.toPlainText()
                character_first_message = self.ui.textEdit_first_message_building.toPlainText()

                if not character_name or not character_first_message:
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("add_character_error_title", "Creation Error"),
                        text=self.translations.get("add_character_error", "Please set a name and the first message for your character."),
                        msg_type="error",
                        duration=5000
                    )
                    return None

                scenario = self.ui.textEdit_scenario.toPlainText()
                example_messages = self.ui.textEdit_example_messages.toPlainText()
                alternate_greetings_raw = self.ui.textEdit_alternate_greetings.toPlainText()
                creator_notes = self.ui.textEdit_creator_notes.toPlainText()
                character_version = self.ui.textEdit_character_version.toPlainText().strip() or "1.0.0"

                parts = alternate_greetings_raw.split("<GREETING>")
                greetings = [part.strip() for part in parts if part.strip()]

                selected_persona = self.ui.comboBox_user_persona_building.currentText()
                selected_system_prompt_preset = self.ui.comboBox_system_prompt_building.currentText()
                selected_lorebooks = self._selected_lorebooks_building
                selected_lorebook = selected_lorebooks[0] if selected_lorebooks else "None"

                sow_variables = self.ui.get_variables_data()

                if hasattr(self, '_editing_character_name') and self._editing_character_name is not None:
                    old_name = self._editing_character_name

                    if character_name != old_name and character_name in character_list:
                        character_name = f"{character_name}_{str(uuid.uuid4())[:4]}"

                    char_data = character_list.get(old_name, {})

                    char_data.update({
                        "character_avatar": character_avatar_directory,
                        "character_description": character_description,
                        "character_personality": character_personality,
                        "first_message": character_first_message,
                        "scenario": scenario,
                        "example_messages": example_messages,
                        "alternate_greetings": greetings,
                        "character_title": creator_notes,
                        "character_version": character_version,
                        "selected_persona": selected_persona,
                        "selected_system_prompt_preset": selected_system_prompt_preset,
                        "selected_lorebook": selected_lorebook,
                        "selected_lorebooks": selected_lorebooks,
                        "conversation_method": method_name,
                        "model_override": self._editor_model_override() or None,
                        "sow_variables": sow_variables
                    })

                    current_chat_id = char_data.get("current_chat", "default")
                    if "chats" in char_data and current_chat_id in char_data["chats"]:
                        chat_obj = char_data["chats"][current_chat_id]
                        if "variables_state" not in chat_obj:
                            chat_obj["variables_state"] = {}
                        for var in sow_variables:
                            if var["id"] not in chat_obj["variables_state"]:
                                chat_obj["variables_state"][var["id"]] = var["default"]

                    if character_name != old_name:
                        character_list.pop(old_name, None)

                    character_list[character_name] = char_data
                    character_configuration["character_list"] = character_list
                    self.configuration_characters.save_configuration_edit(character_configuration)

                    self._editing_character_name = character_name
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("character_edit_title", "Character Settings"),
                        text=self.translations.get("character_edit_saved_2", "The changes were saved successfully!"),
                        msg_type="success"
                    )

                    self.populate_editor_character_list()
                    asyncio.create_task(self.set_main_tab())
                    return character_name

                else:
                    if character_name in character_list:
                        suffix = 1
                        while f"{character_name}_{suffix}" in character_list:
                            suffix += 1
                        suggested_name = f"{character_name}_{suffix}"

                        sow_toast(
                            parent=self.main_window,
                            title=self.translations.get("duplicate_character_error_title", "Duplicate Name"),
                            text=f"{self.translations.get('duplicate_character_error', 'Character already exists. Renamed to:')} {suggested_name}",
                            msg_type="warning",
                            duration=6000
                        )

                        character_name = suggested_name

                    self.configuration_characters.save_character_card(
                        character_name=character_name,
                        character_title=creator_notes,
                        character_avatar=character_avatar_directory,
                        character_description=character_description,
                        character_personality=character_personality,
                        first_message=character_first_message,
                        scenario=scenario,
                        example_messages=example_messages,
                        alternate_greetings=greetings,
                        selected_persona=selected_persona,
                        selected_system_prompt_preset=selected_system_prompt_preset,
                        selected_lorebook=selected_lorebook,
                        elevenlabs_voice_id=None,
                        voice_type=None,
                        rvc_enabled=False,
                        rvc_file=None,
                        expression_images_folder=None,
                        live2d_model_folder=None,
                        vrm_model_file=None,
                        conversation_method=method_name,
                        model_override=self._editor_model_override(),
                        selected_lorebooks=selected_lorebooks,
                        sow_variables=sow_variables
                    )

                    clear_input_fields()
                    reset_image_button_icon()
                    self.populate_editor_character_list()
                    asyncio.create_task(self.set_main_tab())

                    return character_name
            except Exception as e:
                logger.error(f"Error adding character ({method_name}): {e}")
                return None

        def clear_input_fields():
            """
            Clears all input fields related to character creation.
            """
            self.ui.lineEdit_character_name_building.clear()
            self.ui.textEdit_character_description_building.clear()
            self.ui.textEdit_character_personality_building.clear()
            self.ui.textEdit_first_message_building.clear()
            self.ui.textEdit_scenario.clear()
            self.ui.textEdit_example_messages.clear()
            self.ui.textEdit_alternate_greetings.clear()
            self.ui.textEdit_creator_notes.clear()
            self.ui.textEdit_character_version.clear()

        def reset_image_button_icon():
            """
            Resets the image button icon to its default state.
            """
            self._set_editor_avatar(None)
            self.configuration_settings.update_user_data("current_character_image", None)

        match conversation_method:
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM" | "Anthropic" | "Google Gemini" | "DeepSeek" | "Grok" | "Qwen" | "Z.AI":
                return handle_generic_ai(conversation_method)
            case _:
                logger.error(f"Unsupported conversation method: {conversation_method}")
                return None
    
    def on_stacked_widget_changed(self, index):
        if not hasattr(self, '_previous_index'):
            self._previous_index = 0

        CHAT_WIDGET_INDEX = self.ui.stackedWidget.indexOf(self.ui.chat_page)
        RP_EDITORS_INDEX = self.ui.stackedWidget.indexOf(self.ui.rp_editors_page)
        SOUL_STAGE_INDEX = self.ui.stackedWidget.indexOf(self.ui.soul_stage_page)

        if self._previous_index == CHAT_WIDGET_INDEX and index != CHAT_WIDGET_INDEX:
            self.ui.character_description_chat.setText("")

            if hasattr(self, 'playback_worker') and self.playback_worker is not None:
                try:
                    self.playback_worker.clear_queue()
                    logger.info("TTS playback cleared on chat exit.")
                except Exception as e:
                    logger.warning(f"Could not clear TTS playback queue: {e}")
            
            if hasattr(self, 'chat_tts_worker') and self.chat_tts_worker is not None:
                try:
                    self.chat_tts_worker.stop()
                    self.chat_tts_worker.deleteLater()
                    self.chat_tts_worker = None
                    logger.info("Chat TTS Worker stopped on chat exit.")
                except Exception as e:
                    logger.warning(f"Error stopping chat TTS worker: {e}")

            if hasattr(self, 'expression_widget') and self.expression_widget is not None:
                self.expression_widget.setParent(None)
                self.expression_widget.deleteLater()
                self.expression_widget = None
                if index == 1:
                    asyncio.create_task(self.set_main_tab())

            if hasattr(self, 'stackedWidget_expressions') and self.stackedWidget_expressions is not None:
                self.stackedWidget_expressions.setCurrentIndex(-1)
                self.stackedWidget_expressions.setParent(None)
                self.stackedWidget_expressions.deleteLater()
                self.stackedWidget_expressions = None
            
            if hasattr(self, 'ambient_thread'):
                self.ambient_thread.stop_audio()
                self.ambient_thread.terminate()
                self.ambient_thread.wait()
                self.ambient_thread.deleteLater()
                del self.ambient_thread

        if self._previous_index == 4 and index != 4:
            self.abort_loading = True
        
        if self._previous_index == 7 and index != 7:
            self.stop_recommendation_worker()
            self.stop_popular_worker()
            self.stop_search_worker()
            if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
                self.model_information_widget.setParent(None)
                self.model_information_widget.deleteLater()
                self.model_information_widget = None
                if index == 1:
                    asyncio.create_task(self.set_main_tab())
        
        if index == RP_EDITORS_INDEX:
            QtCore.QTimer.singleShot(50, self.ui.update_rp_layout)
        
        if index == SOUL_STAGE_INDEX:
            self.ui.soul_stage_page.on_page_shown()
            if (self.soul_stage_session and
                    self.ui.soul_stage_page.inner_stack.currentIndex() == self.ui.soul_stage_page.IDX_CHAT):
                self._ss_apply_environment(
                    self.soul_stage_orchestrator.world_state.bg_image,
                    self.soul_stage_orchestrator.world_state.ambient_audio
                )

        if hasattr(self, '_previous_index') and self._previous_index == SOUL_STAGE_INDEX and index != SOUL_STAGE_INDEX:
            if hasattr(self, 'ambient_thread'):
                try:
                    self.ambient_thread.stop_audio()
                    self.ambient_thread.terminate()
                    self.ambient_thread.wait()
                    del self.ambient_thread
                    logger.info("[SoulStage] Ambient stopped due to tab change.")
                except:
                    pass
        
        self._previous_index = index
    
    # ══════════════════════════════════════════════════════════════════════════
    #  SOUL STAGE PAGE NAVIGATION & HANDLERS
    # ══════════════════════════════════════════════════════════════════════════
    def _open_soul_stage_page(self):
        idx = self.ui.stackedWidget.indexOf(self.ui.soul_stage_page)
        if idx == -1:
            return

        try:
            self.ui.soul_stage_page.launch_scene.disconnect()
        except Exception:
            pass
        self.ui.soul_stage_page.launch_scene.connect(self._on_soul_stage_launch)

        try:
            self.ui.soul_stage_page.chat_view.interrupted.disconnect()
        except Exception:
            pass
        self.ui.soul_stage_page.chat_view.interrupted.connect(self._soul_stage_interrupt)

        self.ui.soul_stage_page.on_page_shown()
        self.ui.stackedWidget.setCurrentIndex(idx)

        try:
            for btn in [
                self.ui.pushButton_main,
                self.ui.pushButton_rp_editors,
                self.ui.pushButton_characters_gateway,
                self.ui.pushButton_models_hub,
                self.ui.pushButton_options
            ]:
                btn.setChecked(False)
            self.ui.pushButton_soul_stage.setChecked(True)
        except Exception:
            pass

    def _on_soul_stage_launch(self, scene_id: str, scene_data: dict):
        self._soul_stage_scene_id = scene_id
        party_names       = scene_data.get("party",[])
        conv_method       = scene_data.get("conversation_method", "Local LLM")
        opening_narration = scene_data.get("opening_narration", "")
        first_message     = scene_data.get("first_message", "")
        world_context     = scene_data.get("world_context", "")
        starting_location = scene_data.get("starting_location", "Unknown location")
        time_of_day       = scene_data.get("time_of_day", "day")
        atmosphere        = scene_data.get("atmosphere", "")
        gm_tone           = scene_data.get("gm_tone", "epic_fantasy")
        narrator_style    = scene_data.get("narrator_style", "Standard evocative present-tense prose")

        if not party_names:
            logger.error("[SoulStage] No party members in scene!")
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("soul_stage_title", "Soul Stage"),
                text=self.translations.get(
                    "soul_stage_no_party_error", 
                    "No party members in the scene! Please add at least one character before launching."
                ),
                msg_type="error",
                duration=5000
            )
            return

        self.soul_stage_orchestrator.reset_scene()
        self.soul_stage_orchestrator.world_state.world_context = world_context
        self.soul_stage_orchestrator.world_state.gm_tone = gm_tone
        self.soul_stage_orchestrator.world_state.narrator_style = narrator_style

        if "world_state" in scene_data:
            self.soul_stage_orchestrator.load_world_state_from_dict(scene_data)
        else:
            starting_location = scene_data.get("starting_location", "Unknown location")
            potential_bg  = scene_data.get("starting_bg", "None")
            potential_amb = scene_data.get("starting_ambient", "None")

            if potential_bg == "None":
                loc_safe = starting_location.lower().strip()
                for f in self.soul_stage_orchestrator.bg_list:
                    if loc_safe in f.lower():
                        potential_bg = f
                        break

            initial_plan = {
                "location":    starting_location,
                "time_of_day": time_of_day,
                "atmosphere":  scene_data.get("world_context", "")[:200] if scene_data.get("world_context") else scene_data.get("atmosphere", ""),
                "bg_image":    potential_bg,
                "ambient_audio": potential_amb,
                "key_facts":   {},
                "spawns":      [],
                "despawns":    [],
                "inventory_add":[],
                "status_add":[]
            }
            self.soul_stage_orchestrator.world_state.world_context = scene_data.get("world_context", "")
            self.soul_stage_orchestrator.world_state.gm_tone = scene_data.get("gm_tone", "epic_fantasy")
            self.soul_stage_orchestrator.world_state.narrator_style = narrator_style
            self.soul_stage_orchestrator.world_state.update_from_plan(initial_plan)

        self._ss_apply_environment(
            self.soul_stage_orchestrator.world_state.bg_image,
            self.soul_stage_orchestrator.world_state.ambient_audio
        )

        self.soul_stage_session = SoulStageSession(self.soul_stage_orchestrator, party_names, conv_method)

        chat_view = self.ui.soul_stage_page.chat_view
        try:
            chat_view.btn_send.clicked.disconnect()
            chat_view.text_input.handle_enter_key.disconnect()
            chat_view.world_info_clicked.disconnect()
            chat_view.continue_plot.disconnect()
            chat_view.choice_made.disconnect()
            self.ui.soul_stage_page.open_memory_requested.disconnect()
        except Exception:
            pass

        try:
            chat_view.inventory_hud.open_full_requested.disconnect()
        except Exception:
            pass
        chat_view.inventory_hud.open_full_requested.connect(
            lambda: self._ss_open_inventory_panel()
        )

        try:
            self.ui.soul_stage_page.chat_view.exit_clicked.disconnect(self._ss_stop_ambient)
        except Exception:
            pass
        self.ui.soul_stage_page.chat_view.exit_clicked.connect(self._ss_stop_ambient)

        chat_view.btn_send.clicked.connect(lambda: asyncio.create_task(self._ss_send_message()))
        chat_view.text_input.handle_enter_key.connect(lambda: asyncio.create_task(self._ss_send_message()))
        chat_view.btn_stop.clicked.connect(self._soul_stage_interrupt)
        chat_view.world_info_clicked.connect(self._ss_open_world_info)
        chat_view.continue_plot.connect(lambda: asyncio.create_task(self._ss_continue_plot()))
        chat_view.choice_made.connect(lambda: asyncio.create_task(self._ss_send_message()))
        self.ui.soul_stage_page.open_memory_requested.connect(self._ss_open_memory)

        chat_view.clear_chat()
        
        chat_log = scene_data.get("chat_log",[])
        if chat_log:
            self._ss_restore_chat(chat_log)
        else:
            asyncio.create_task(self._ss_show_opening(opening_narration, first_message, party_names))
        
        QtCore.QTimer.singleShot(200, lambda: (
            self.ui.soul_stage_page.chat_view.update_inventory_hud(
                self.soul_stage_orchestrator.world_state.player_inventory
            )
        ))
        
    def _ss_stop_ambient(self):
        if hasattr(self, 'ambient_thread'):
            try:
                self.ambient_thread.stop_audio()
                self.ambient_thread.terminate()
                self.ambient_thread.wait()
                del self.ambient_thread
                logger.info("[SoulStage] Ambient audio stopped on exit to lobby.")
            except Exception as e:
                logger.error(f"[SoulStage] Error stopping ambient: {e}")

    def _ss_apply_environment(self, bg_file: str, ambient_file: str):
        chat_view = self.ui.soul_stage_page.chat_view

        chat_view.chat_page.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)
        
        ss_scroll_style = """
            QScrollArea {
                background: transparent;
                border: none;
                padding: 5px;
            }
            QScrollArea > QWidget, 
            QScrollArea #qt_scrollarea_viewport, 
            QScrollArea QWidget {
                background: transparent;
                background-color: transparent;
            }
            QScrollArea QScrollBar {
                background: transparent;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 2px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.15), 
                    stop:1 rgba(255, 255, 255, 0.08)
                );
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 4px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.25), 
                    stop:1 rgba(255, 255, 255, 0.16)
                );
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            QScrollBar::handle:vertical:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.35), 
                    stop:1 rgba(255, 255, 255, 0.24)
                );
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 2px 4px 2px 4px;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.15), 
                    stop:1 rgba(255, 255, 255, 0.08)
                );
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 4px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.25), 
                    stop:1 rgba(255, 255, 255, 0.16)
                );
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            QScrollBar::handle:horizontal:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.35), 
                    stop:1 rgba(255, 255, 255, 0.24)
                );
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: transparent;
                border: none;
                width: 0px;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
            }
        """

        if bg_file and bg_file != "None":
            abs_path = os.path.abspath(f"assets/backgrounds/{bg_file}").replace("\\", "/")
            
            if os.path.exists(abs_path):
                chat_view.setStyleSheet(f"""
                    QWidget#soul_stage_chat_view {{
                        border-image: url('{abs_path}') 0 0 0 0 stretch stretch;
                    }}
                """)
                chat_view.chat_page.setStyleSheet("QWidget#chat_content_area { background: transparent; }")
                chat_view.scroll_area.setStyleSheet(ss_scroll_style)
                logger.info(f"[SoulStage] FULLSCREEN Background applied: {bg_file}")
            else:
                logger.warning(f"[SoulStage] Background file not found: {abs_path}")
        else:
            chat_view.setStyleSheet("""
                QWidget#soul_stage_chat_view {
                    background: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(12, 12, 15, 255),
                        stop:0.5 rgba(15, 15, 20, 255),
                        stop:1 rgba(10, 10, 12, 255));
                }
            """)
            chat_view.chat_page.setStyleSheet("QWidget#chat_content_area { background: transparent; }")
            chat_view.scroll_area.setStyleSheet(ss_scroll_style)

        if ambient_file and ambient_file != "None":
            amb_path = f"assets/ambient/{ambient_file}".replace("\\", "/")
            if os.path.exists(amb_path):
                output_device = self.configuration_settings.get_main_setting("output_device_real_index")
                if hasattr(self, "ambient_thread") and self.ambient_thread.isRunning():
                    self.ambient_thread.stop()
                    self.ambient_thread.wait()
                self.ambient_thread = AmbientPlayer(amb_path, device_index=output_device)
                self.ambient_thread.start()
                logger.info(f"[SoulStage] Ambient sound started: {ambient_file}")

    def get_current_memory_dir(self, character_name: str) -> Path:
        from app.utils.soul_memory import SoulMemoryAgent
        agent = SoulMemoryAgent(None)
        mem_dir, _, _, _, _, _ = agent.get_memory_paths(character_name)
        return mem_dir
    
    def _ss_open_memory(self, party_names: list):
        if not party_names:
            return
        from app.gui.soul_stage_page import RPGMemorySelectDialog
        char_name = RPGMemorySelectDialog.ask(party_names, parent=self.main_window)
        if not char_name:
            return

        mem_dir = self.get_current_memory_dir(char_name)
        dialog = SoulMemoryViewer(char_name, mem_dir, self.main_window, 
                                subtitle_tr=self.translations.get("soul_memory_subtitle"),
                                content_view_tr=self.translations.get("soul_memory_content_placeholder"),
                                title_text_tr=self.translations.get("soul_memory_title"),
                                tab_database_tr=self.translations.get("soul_memory_tab_db"),
                                tab_user_profile_tr=self.translations.get("soul_memory_tab_user"),
                                tab_diary_tr=self.translations.get("soul_memory_tab_diary"),
                                tab_logs_tr=self.translations.get("soul_memory_tab_logs"),
                                btn_save_tr=self.translations.get("soul_memory_btn_save"),
                                btn_delete_tr=self.translations.get("soul_memory_btn_delete"),
                                btn_refresh_tr=self.translations.get("soul_memory_btn_refresh"),
                                btn_open_folder_tr=self.translations.get("soul_memory_btn_open"),
                                msg_save_success_tr=self.translations.get("soul_memory_save_success"),
                                msg_save_error_tr=self.translations.get("soul_memory_save_error"),
                                msg_delete_confirm_title_tr=self.translations.get("soul_memory_del_title"),
                                msg_delete_confirm_text_tr=self.translations.get("soul_memory_del_text"),
                                msg_delete_success_tr=self.translations.get("soul_memory_del_success"),
                                msg_delete_error_tr=self.translations.get("soul_memory_del_error"),
                                msg_logs_empty_tr=self.translations.get("soul_memory_logs_empty"),
                                btn_edit_tr=self.translations.get("soul_memory_btn_edit"),
                                btn_preview_tr=self.translations.get("soul_memory_btn_preview")
                            )
        dialog.exec()
    
    def _ss_open_inventory_panel(self):
        if not self.soul_stage_session:
            return
        from app.gui.soul_stage_page import InventoryPanel
        orch = self.soul_stage_session.orchestrator
        panel = InventoryPanel(orch.world_state, parent=self.main_window)

        def on_item_used(item: str):
            chat_view = self.ui.soul_stage_page.chat_view
            chat_view.inventory_hud._use_item(item)

        def on_item_dropped(item: str):
            chat_view = self.ui.soul_stage_page.chat_view
            chat_view.update_inventory_hud(orch.world_state.player_inventory)

        panel.item_used.connect(on_item_used)
        panel.item_dropped.connect(on_item_dropped)
        panel.exec()
    
    def _ss_open_world_info(self):
        if not self.soul_stage_session:
            return
        from app.gui.soul_stage_page import WorldInfoDialog
        orch = self.soul_stage_session.orchestrator
        dlg  = WorldInfoDialog(
            world_state  = orch.world_state,
            npc_registry = orch.npc_registry,
            parent       = self.main_window,
        )
        dlg.exec()
        if self._soul_stage_scene_id:
            from app.gui.soul_stage_page import _load_scenes, _save_scenes
            d = _load_scenes()
            if self._soul_stage_scene_id in d["scenes"]:
                ws = orch.world_state
                d["scenes"][self._soul_stage_scene_id]["world_state"] = {
                    "location":         ws.location,
                    "time_of_day":      ws.time_of_day,
                    "atmosphere":       ws.atmosphere,
                    "bg_image":         ws.bg_image,
                    "ambient_audio":    ws.ambient_audio,
                    "key_facts":        ws.key_facts,
                    "player_inventory": ws.player_inventory,
                    "player_status":    ws.player_status,
                    "narrator_style":   ws.narrator_style,
                }
                _save_scenes(d)

        chat_view = self.ui.soul_stage_page.chat_view
        chat_view.update_inventory_hud(orch.world_state.player_inventory)

    async def _ss_continue_plot(self):
        if not self.soul_stage_session:
            return
        if self.soul_stage_session.orchestrator.is_running:
            return

        class PlotWishDialog(QDialog):
            def __init__(self, parent=None, translations=None):
                super().__init__(parent)
                self.translations = translations or {}
                self.setWindowTitle(self.translations.get("plot_wish_dialog_title", "Continue Plot"))
                self.setMinimumWidth(500)
                self.setFixedHeight(320)
                self.setStyleSheet("""
                    QDialog { 
                        background-color: #0d0d10; 
                        color: #e8e8e8; 
                    }
                    QLabel { 
                        background: transparent; 
                        border: none; 
                    }
                    QTextEdit {
                        background: rgba(0, 0, 0, 0.2);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-top: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 8px;
                        color: rgba(240, 240, 240, 0.95);
                        padding: 12px 14px;
                        selection-background-color: rgba(255, 255, 255, 0.20);
                    }
                    QTextEdit:focus {
                        background: rgba(255, 255, 255, 0.04);
                        border: 1px solid rgba(255, 255, 255, 0.25);
                    }
                """)
                
                def _set_font(widget, family="Inter Tight Medium", size=12, bold=False):
                    f = QFont(family, size)
                    if bold:
                        f.setWeight(QFont.Weight.Bold)
                    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
                    widget.setFont(f)

                root = QVBoxLayout(self)
                root.setContentsMargins(28, 24, 28, 24)
                root.setSpacing(0)

                header_row = QHBoxLayout()
                header_row.setSpacing(14)
                
                icon_lbl = QLabel()
                icon_lbl.setPixmap(QtGui.QIcon("app/gui/icons/play.png").pixmap(26, 26))
                header_row.addWidget(icon_lbl)
                
                title_col = QVBoxLayout()
                title_col.setSpacing(4)
                
                title_lbl = QLabel(self.translations.get("plot_wish_dialog_title", "CONTINUE PLOT").upper())
                _set_font(title_lbl, "Inter Tight SemiBold", 11, bold=True)
                title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); letter-spacing: 1.5px;")
                title_col.addWidget(title_lbl)
                
                sub_lbl = QLabel(self.translations.get("plot_wish_label", "What should happen next? (Optional hints for AI)"))
                _set_font(sub_lbl, "Inter Tight Medium", 10)
                sub_lbl.setStyleSheet("color: rgba(255,255,255,0.45);")
                title_col.addWidget(sub_lbl)
                
                header_row.addLayout(title_col, 1)
                root.addLayout(header_row)
                
                root.addSpacing(16)
                
                divider = QFrame()
                divider.setFrameShape(QFrame.Shape.HLine)
                divider.setFixedHeight(1)
                divider.setStyleSheet("background: rgba(255,255,255,0.05); border: none;")
                root.addWidget(divider)
                
                root.addSpacing(16)

                self.editor = QTextEdit()
                self.editor.setPlaceholderText(self.translations.get("plot_wish_placeholder", "e.g. An explosion happens outside, or someone knocks on the door..."))
                _set_font(self.editor, "Inter Tight Medium", 10)
                root.addWidget(self.editor, 1)
                
                root.addSpacing(20)

                btn_row = QHBoxLayout()
                btn_row.setSpacing(12)
                btn_row.addStretch()
                
                btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
                _set_font(btn_cancel, "Inter Tight Medium", 11)
                btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn_cancel.setFixedSize(110, 38)
                btn_cancel.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                        border-radius: 10px;
                        color: rgba(255, 255, 255, 0.5);
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                        border-color: rgba(255, 255, 255, 0.2);
                        color: rgba(255, 255, 255, 0.9);
                    }
                """)
                btn_cancel.clicked.connect(self.reject)
                btn_row.addWidget(btn_cancel)
                
                btn_ok = QPushButton(self.translations.get("plot_wish_continue_btn", "Continue Plot"))
                _set_font(btn_ok, "Inter Tight SemiBold", 11)
                btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_ok.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn_ok.setFixedSize(160, 38)
                btn_ok.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.08);
                        border: 1px solid rgba(255, 255, 255, 0.15);
                        border-radius: 10px;
                        color: rgba(255, 255, 255, 0.95);
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.15);
                        border-color: rgba(255, 255, 255, 0.3);
                        color: #ffffff;
                    }
                    QPushButton:pressed {
                        background: rgba(255, 255, 255, 0.05);
                    }
                """)
                btn_ok.clicked.connect(self.accept)
                btn_row.addWidget(btn_ok)
                
                root.addLayout(btn_row)
                self.wish = ""
                
            def accept(self):
                self.wish = self.editor.toPlainText().strip()
                super().accept()

        dlg = PlotWishDialog(self.main_window, self.translations)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
            
        wish = dlg.wish

        ws = self.soul_stage_session.orchestrator.world_state
        inv_str = (", ".join(ws.player_inventory)) if ws.player_inventory else "nothing notable"
        status_str = (", ".join(ws.player_status)) if ws.player_status else "normal"

        wish_str = f" Director's hints: '{wish}'" if wish else ""

        trigger_message = (
            f"[SYSTEM DIRECTIVE — PLOT ADVANCE]\n"
            f"Advance the plot. Introduce an interesting development, "
            f"unexpected event, or new complication that fits the current scene naturally.{wish_str}\n"
            f"Consider: location='{ws.location}', time='{ws.time_of_day}', "
            f"player carries: {inv_str}, player status: {status_str}.\n"
            f"Keep it grounded in the established world lore. DO NOT address the player directly."
        )

        await self._ss_run_plot_advance(trigger_message)

    async def _ss_run_plot_advance(self, trigger_message: str):
        if not self.soul_stage_session:
            return

        session   = self.soul_stage_session
        chat_view = self.ui.soul_stage_page.chat_view

        from app.gui.soul_stage_page import (
            SoulStageEventCard, SoulStageNPCBubble, _load_scenes, _save_scenes
        )
        scene_data = _load_scenes()["scenes"].get(self._soul_stage_scene_id, {})
        persona_key = scene_data.get("persona_key", "")
        personas = self.configuration_settings.get_user_data("personas") or {}
        user_name = "Player"
        user_desc = ""
        if persona_key and persona_key in personas:
            user_name = personas[persona_key].get("user_name", "Player")
            user_desc = personas[persona_key].get("user_description", "")

        chat_log = scene_data.get("chat_log", [])
        context_messages = []
        for m in chat_log[-30:]:
            r = m.get("role")
            c = m.get("content", "")
            actor = m.get("actor_name", "")
            if r == "player":   context_messages.append({"role": "user",      "content": f"[PLAYER ({actor})]: {c}"})
            elif r == "narrator": context_messages.append({"role": "assistant", "content": f"[NARRATOR]: {c}"})
            elif r == "char":   context_messages.append({"role": "assistant", "content": f"[{actor}]: {c}"})
            elif r == "npc":    context_messages.append({"role": "assistant", "content": f"[NPC {actor}]: {c}"})

        chat_view.btn_send.hide()
        chat_view.btn_stop.show()
        chat_view.btn_continue_plot.setEnabled(False)
        chat_view.text_input.setEnabled(False)

        turn_log = []
        _plot_event_type: list = ["none"]
        narrator_bubble = narrator_wrap = char_label = npc_bubble = None
        char_full_text = npc_full_text = ""

        async def on_narrator_chunk(chunk: str):
            nonlocal narrator_bubble, narrator_wrap
            if narrator_bubble is None:
                narrator_bubble = SoulStageEventCard(event_type=_plot_event_type[0])
                narrator_wrap = QWidget()
                narrator_wrap.setStyleSheet("background: transparent;")
                lyt = QVBoxLayout(narrator_wrap)
                lyt.setContentsMargins(0, 4, 0, 4)
                lyt.addWidget(narrator_bubble)
                chat_view.chat_container.addWidget(narrator_wrap)
            narrator_bubble.append_text(chunk)
            chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_narrator_done():
            nonlocal narrator_bubble, narrator_wrap
            if narrator_bubble:
                turn_log.append({
                    "role": "narrator",
                    "content": narrator_bubble.text_label.text(),
                    "actor_name": "NARRATOR"
                })
            narrator_bubble = narrator_wrap = None

        async def on_char_start(name: str, _avatar):
            nonlocal char_label, char_full_text
            char_full_text = ""
            char_label, _ = self._ss_add_custom_message(name, "", is_user=False)
            await asyncio.sleep(0)

        async def on_char_chunk(name: str, chunk: str):
            nonlocal char_label, char_full_text
            if char_label:
                char_full_text += chunk
                char_label.setText(self.markdown_to_html(char_full_text))
                chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_char_done(name: str, full_text: str):
            turn_log.append({"role": "char", "content": full_text, "actor_name": name})

        async def on_npc_start(npc, avatar_path: str):
            nonlocal npc_bubble, npc_full_text
            npc_full_text = ""
            npc_bubble = SoulStageNPCBubble(npc.name, npc.archetype, avatar_path)
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            lyt = QVBoxLayout(wrap)
            lyt.setContentsMargins(0, 4, 0, 4)
            lyt.addWidget(npc_bubble)
            chat_view.chat_container.addWidget(wrap)
            await asyncio.sleep(0)

        async def on_npc_chunk(name: str, chunk: str):
            nonlocal npc_bubble, npc_full_text
            if npc_bubble:
                npc_full_text += chunk
                npc_bubble.append_text(chunk)
                chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_npc_done(name: str, full_text: str):
            npc_obj = session.orchestrator.npc_registry.get(name)
            arch = npc_obj.archetype if npc_obj else "citizen"
            turn_log.append({"role": "npc", "content": full_text, "actor_name": name, "archetype": arch})

        async def on_turn_complete():
            chat_view.btn_stop.hide()
            chat_view.btn_send.show()
            chat_view.btn_continue_plot.setEnabled(True)
            chat_view.text_input.setEnabled(True)
            self._ss_apply_environment(
                session.orchestrator.world_state.bg_image,
                session.orchestrator.world_state.ambient_audio
            )
            inv = session.orchestrator.world_state.player_inventory
            chat_view.update_inventory_hud(inv)
        
        async def on_choices(choices: list, event_type: str):
            _plot_event_type[0] = event_type
            if choices:
                chat_view.show_choices(choices, event_type)

        async def on_error(msg: str):
            b = SoulStageEventCard(event_type="none")
            b.set_text(f"<b>⚠ ERROR</b> — {msg}")
            w = QWidget()
            QVBoxLayout(w).addWidget(b)
            chat_view.chat_container.addWidget(w)
            await on_turn_complete()

        def character_stream_fn(char_name, ctx_msgs, u_msg, u_name, u_desc):
            c_data   = self.configuration_characters.load_configuration()
            c_info   = c_data["character_list"].get(char_name, {})
            c_method = session.conversation_method
            
            clean_data = session.orchestrator._get_clean_character_data(char_name)

            async def stream_wrapper():
                provider = AIFactory.get_provider(c_method, c_info.get("model_override"))
                if not provider:
                    raise ValueError(f"Provider not found for method: {c_method}")

                original_load = self.prompt_engine.configuration_characters.load_configuration
                def fake_load():
                    data = original_load()
                    if "character_list" in data and char_name in data["character_list"]:
                        data["character_list"][char_name] = clean_data
                    return data

                self.prompt_engine.configuration_characters.load_configuration = fake_load

                try:
                    messages, _ = self.prompt_engine.build_system_prompt_blocks(
                        char_name, u_name, u_desc, ctx_msgs, u_msg
                    )
                finally:
                    self.prompt_engine.configuration_characters.load_configuration = original_load

                self.log_prompt_structure(messages)
                async for chunk in provider.generate_stream(messages):
                    yield chunk

            return stream_wrapper()
        
        await session.orchestrator.run_turn(
            player_message=trigger_message,
            party_names=session.party_names,
            conversation_method=session.conversation_method,
            context_messages=context_messages,
            user_name=user_name,
            user_description=user_desc,
            character_stream_fn=character_stream_fn,
            on_narrator_chunk=on_narrator_chunk, on_narrator_done=on_narrator_done,
            on_char_start=on_char_start, on_char_chunk=on_char_chunk, on_char_done=on_char_done,
            on_npc_start=on_npc_start, on_npc_chunk=on_npc_chunk, on_npc_done=on_npc_done,
            on_turn_complete=on_turn_complete, on_error=on_error, on_choices=on_choices,
        )

        if self._soul_stage_scene_id:
            d = _load_scenes()
            if self._soul_stage_scene_id in d["scenes"]:
                d["scenes"][self._soul_stage_scene_id].setdefault("chat_log", []).extend(turn_log)
                d["scenes"][self._soul_stage_scene_id]["chat_log"] = \
                    d["scenes"][self._soul_stage_scene_id]["chat_log"][-200:]
                ws = session.orchestrator.world_state
                d["scenes"][self._soul_stage_scene_id]["world_state"] = {
                    "location":         ws.location,
                    "time_of_day":      ws.time_of_day,
                    "atmosphere":       ws.atmosphere,
                    "bg_image":         ws.bg_image,
                    "ambient_audio":    ws.ambient_audio,
                    "key_facts":        ws.key_facts,
                    "player_inventory": ws.player_inventory,
                    "player_status":    ws.player_status,
                    "narrator_style":   ws.narrator_style,
                }
                active_npcs = []
                for npc in session.orchestrator.npc_registry.list_active():
                    active_npcs.append({
                        "name": npc.name, "archetype": npc.archetype,
                        "personality": npc.personality, "avatar_key": npc.avatar_key,
                        "turn_count": npc.turn_count
                    })
                d["scenes"][self._soul_stage_scene_id]["active_npcs"] = active_npcs
                _save_scenes(d)

        asyncio.create_task(
            session.orchestrator.sync_party_memory(
                session.conversation_method, session.party_names, turn_log, user_name
            )
        )

    def _ss_restore_chat(self, chat_log: list):
        from app.gui.soul_stage_page import SoulStageEventCard, SoulStageNPCBubble
        chat_view = self.ui.soul_stage_page.chat_view
        
        for entry in chat_log:
            role = entry.get("role", "")
            actor = entry.get("actor_name", "")
            content = entry.get("content", "")
            archetype = entry.get("archetype", "citizen")

            if role == "narrator":
                b = SoulStageEventCard(event_type="none"); b.set_text(self.markdown_to_html(content))
                w = QWidget(); w.setStyleSheet("background:transparent;"); QVBoxLayout(w).addWidget(b)
                chat_view.chat_container.addWidget(w)
            elif role == "npc":
                b = SoulStageNPCBubble(actor, archetype); b.append_text(self.markdown_to_html(content))
                w = QWidget(); w.setStyleSheet("background:transparent;"); QVBoxLayout(w).addWidget(b)
                chat_view.chat_container.addWidget(w)
            elif role == "player":
                self._ss_add_custom_message(actor, content, is_user=True)
            elif role == "char":
                lbl, _ = self._ss_add_custom_message(actor, content, is_user=False)

        chat_view.scroll_to_bottom()

    async def _ss_show_opening(self, opening_narration: str, first_message: str, party_names: list):
        from app.gui.soul_stage_page import SoulStageEventCard, append_to_scene_log
        chat_view = self.ui.soul_stage_page.chat_view
        log_entries =[]

        if opening_narration:
            bubble = SoulStageEventCard(event_type="none")
            bubble.set_text(self.markdown_to_html(opening_narration))
            wrap = QWidget(); lyt = QVBoxLayout(wrap); lyt.setContentsMargins(0, 6, 0, 6)
            lyt.addWidget(bubble); chat_view.chat_container.addWidget(wrap)
            chat_view.scroll_to_bottom()
            await asyncio.sleep(0.05)
            log_entries.append({"role": "narrator", "actor_name": "NARRATOR", "content": opening_narration, "timestamp": datetime.datetime.now().isoformat()})

        if first_message and party_names:
            char_name = party_names[0]
            lbl, _ = self._ss_add_custom_message(char_name, "", is_user=False)
            lbl.setText(self.markdown_to_html(first_message))
            chat_view.scroll_to_bottom()
            log_entries.append({"role": "char", "actor_name": char_name, "content": first_message, "timestamp": datetime.datetime.now().isoformat()})

        if log_entries and self._soul_stage_scene_id:
            append_to_scene_log(self._soul_stage_scene_id, log_entries)

    def _ss_add_custom_message(self, name: str, text: str, is_user: bool):
        from app.gui.soul_stage_page import _get_char_avatar_pixmap, _load_scenes

        html_text = self.markdown_to_html(text)
        
        message_container = QHBoxLayout()
        message_container.setSpacing(0)
        message_container.setContentsMargins(10, 5, 10, 5)

        s = self.get_chat_appearance()
        op = s["bubble_opacity"]
        
        def get_rgba(hex_col, alpha):
            h = hex_col.lstrip("#")
            return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha/100})"
            
        bg_color = get_rgba(s["user_bubble_color"] if is_user else s["char_bubble_color"], op)
        r = s["border_radius"]
        
        radius_css = (
            f"border-top-left-radius: {r}px; border-bottom-left-radius: {r}px; border-bottom-right-radius: 0px; border-top-right-radius: {r}px;" 
            if is_user else 
            f"border-top-right-radius: {r}px; border-bottom-right-radius: {r}px; border-top-left-radius: {r}px; border-bottom-left-radius: 0px;"
        )

        bubble_frame = QFrame()
        bubble_frame.setObjectName("bubble_frame")
        bubble_frame.setStyleSheet(f"""
            QFrame#bubble_frame {{
                background-color: {bg_color};
                {radius_css}
                margin: 5px;
            }}
        """)
        bubble_frame.setFixedWidth(s.get("max_width", 750))

        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(14, 12, 14, 12)
        bubble_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        if is_user:
            scene_data = _load_scenes()["scenes"].get(self._soul_stage_scene_id, {})
            persona_key = scene_data.get("persona", "None")
            personas = self.configuration_settings.get_user_data("personas")
            if persona_key != "None" and personas and persona_key in personas:
                av_path = personas[persona_key].get("user_avatar", "app/gui/icons/person.png")
            else:
                av_path = "app/gui/icons/person.png"
            raw_pixmap = QPixmap(av_path)
        else:
            raw_pixmap = _get_char_avatar_pixmap(name)

        if raw_pixmap.isNull():
            raw_pixmap = QPixmap("app/gui/icons/logotype.png")

        target_size = 64
        label_size  = 26

        scaled_pixmap = raw_pixmap.scaled(
            target_size, target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        crop_x = (scaled_pixmap.width()  - target_size) // 2
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

        name_label = QLabel(name)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {max(11, s["font_size"] - 2)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)

        header_layout.addWidget(avatar_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        bubble_layout.addLayout(header_layout)

        lbl = QLabel()
        lbl.setTextFormat(Qt.TextFormat.RichText)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl.setText(html_text)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl.setFont(font)

        lbl.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {s["font_size"]}px;
                background: transparent;
                border: none;
                line-height: 1.4;
            }}
        """)
        
        bubble_layout.addWidget(lbl)

        message_container.addStretch()
        message_container.addWidget(bubble_frame)
        message_container.addStretch()

        frame = SmoothMessageFrame(None)
        frame.setLayout(message_container)
        frame.setStyleSheet("""
            QMenu { background-color: #1E1E1E; color: #D4D4D4; border: 1px solid #383838; border-radius: 8px; }
            QMenu::item { padding: 6px 20px; background-color: transparent; }
            QMenu::item:selected { background-color: #2D2D2D; color: #FFFFFF; border-radius: 4px; }
        """)

        self.ui.soul_stage_page.chat_view.chat_container.addWidget(frame)
        return lbl, frame

    async def _ss_send_message(self):
        if not self.soul_stage_session: return

        from app.gui.soul_stage_page import (
            SoulStageEventCard,
            SoulStageNPCBubble, 
            _save_scenes, 
            _load_scenes
        )

        session = self.soul_stage_session
        chat_view = self.ui.soul_stage_page.chat_view
        user_text = chat_view.text_input.toPlainText().strip()
        chat_view.text_input.clear()
        chat_view.clear_choices()

        scene_data = _load_scenes()["scenes"].get(self._soul_stage_scene_id, {})
        persona_key = scene_data.get("persona", "None")
        personas = self.configuration_settings.get_user_data("personas")
        
        if persona_key in (None, "None") or persona_key not in personas:
            user_name, user_desc = "User", "The player."
        else:
            user_name = personas[persona_key].get("user_name", "User")
            user_desc = personas[persona_key].get("user_description", "")

        chat_log = scene_data.get("chat_log",[])
        context_messages =[]
        for m in chat_log[-30:]:
            r = m.get("role")
            c = m.get("content", "")
            actor = m.get("actor_name", "")
            if r == "player": context_messages.append({"role": "user", "content": f"[PLAYER ({actor})]: {c}"})
            elif r == "narrator": context_messages.append({"role": "assistant", "content": f"[NARRATOR]: {c}"})
            elif r == "char": context_messages.append({"role": "assistant", "content": f"[{actor}]: {c}"})
            elif r == "npc": context_messages.append({"role": "assistant", "content": f"[NPC {actor}]: {c}"})

        self._ss_add_custom_message(user_name, user_text or " ", is_user=True)
        chat_view.scroll_to_bottom()

        chat_view.btn_send.hide()
        chat_view.btn_stop.show()
        chat_view.text_input.setEnabled(False)

        turn_log =[{"role": "player", "content": user_text or " ", "actor_name": user_name}]
        
        narrator_bubble = narrator_wrap = char_label = npc_bubble = None
        char_full_text = npc_full_text = ""
        char_name_saved = None

        from app.gui.soul_stage_page import SoulStageEventCard, SoulStageNPCBubble, _save_scenes, _load_scenes

        async def on_narrator_chunk(chunk: str):
            nonlocal narrator_bubble, narrator_wrap
            if narrator_bubble is None:
                narrator_bubble = SoulStageEventCard(event_type="none")
                narrator_wrap = QWidget()
                narrator_wrap.setStyleSheet("background: transparent;")
                lyt = QVBoxLayout(narrator_wrap); lyt.setContentsMargins(0, 4, 0, 4)
                lyt.addWidget(narrator_bubble); chat_view.chat_container.addWidget(narrator_wrap)
            narrator_bubble.append_text(chunk)
            chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_narrator_done():
            nonlocal narrator_bubble, narrator_wrap
            if narrator_bubble:
                turn_log.append({"role": "narrator", "content": narrator_bubble.text_label.text(), "actor_name": "NARRATOR"})
            narrator_bubble = narrator_wrap = None

        async def on_char_start(name: str, _avatar):
            nonlocal char_label, char_name_saved, char_full_text
            char_full_text = ""; char_name_saved = name
            char_label, _ = self._ss_add_custom_message(name, "", is_user=False)
            await asyncio.sleep(0)

        async def on_char_chunk(name: str, chunk: str):
            nonlocal char_label, char_full_text
            if char_label:
                char_full_text += chunk
                char_label.setText(self.markdown_to_html(char_full_text))
                chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_char_done(name: str, full_text: str):
            turn_log.append({"role": "char", "content": full_text, "actor_name": name})

        async def on_npc_start(npc, avatar_path: str):
            nonlocal npc_bubble, npc_full_text
            npc_full_text = ""
            npc_bubble = SoulStageNPCBubble(npc.name, npc.archetype, avatar_path)
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            lyt = QVBoxLayout(wrap)
            lyt.setContentsMargins(0, 4, 0, 4)
            lyt.addWidget(npc_bubble)
            chat_view.chat_container.addWidget(wrap)
            await asyncio.sleep(0)

        async def on_npc_chunk(name: str, chunk: str):
            nonlocal npc_bubble, npc_full_text
            if npc_bubble:
                npc_full_text += chunk; npc_bubble.append_text(chunk); chat_view.scroll_to_bottom()
            await asyncio.sleep(0)

        async def on_npc_done(name: str, full_text: str):
            npc_obj = session.orchestrator.npc_registry.get(name)
            arch = npc_obj.archetype if npc_obj else "citizen"
            turn_log.append({"role": "npc", "content": full_text, "actor_name": name, "archetype": arch})

        async def on_turn_complete():
            chat_view.btn_stop.hide()
            chat_view.btn_send.show()
            chat_view.text_input.setEnabled(True)
            self._ss_apply_environment(
                session.orchestrator.world_state.bg_image,
                session.orchestrator.world_state.ambient_audio
            )
            inv = session.orchestrator.world_state.player_inventory
            chat_view.update_inventory_hud(inv)

        async def on_error(msg: str):
            b = SoulStageEventCard(event_type="none")
            b.set_text(f"<b>⚠ ERROR</b> — {msg}")
            w = QWidget(); QVBoxLayout(w).addWidget(b); chat_view.chat_container.addWidget(w)
            await on_turn_complete()

        def character_stream_fn(char_name, ctx_msgs, u_msg, u_name, u_desc):
            c_data   = self.configuration_characters.load_configuration()
            c_info   = c_data["character_list"].get(char_name, {})
            c_method = session.conversation_method
            
            clean_data = session.orchestrator._get_clean_character_data(char_name)

            async def stream_wrapper():
                provider = AIFactory.get_provider(c_method, c_info.get("model_override"))
                if not provider:
                    raise ValueError(f"Provider not found for method: {c_method}")

                original_load = self.prompt_engine.configuration_characters.load_configuration
                
                def fake_load():
                    data = original_load()
                    if "character_list" in data and char_name in data["character_list"]:
                        data["character_list"][char_name] = clean_data
                    return data

                self.prompt_engine.configuration_characters.load_configuration = fake_load

                try:
                    messages, _ = self.prompt_engine.build_system_prompt_blocks(
                        char_name, u_name, u_desc, ctx_msgs, u_msg
                    )
                finally:
                    self.prompt_engine.configuration_characters.load_configuration = original_load

                self.log_prompt_structure(messages)
                async for chunk in provider.generate_stream(messages):
                    yield chunk

            return stream_wrapper()
     
        async def on_choices(choices: list, event_type: str):
            if choices:
                chat_view.show_choices(choices, event_type)

        await session.orchestrator.run_turn(
            player_message=user_text, party_names=session.party_names, conversation_method=session.conversation_method,
            context_messages=context_messages, user_name=user_name, user_description=user_desc,
            character_stream_fn=character_stream_fn,
            on_narrator_chunk=on_narrator_chunk, on_narrator_done=on_narrator_done,
            on_char_start=on_char_start, on_char_chunk=on_char_chunk, on_char_done=on_char_done,
            on_npc_start=on_npc_start, on_npc_chunk=on_npc_chunk, on_npc_done=on_npc_done,
            on_turn_complete=on_turn_complete, on_error=on_error, on_choices=on_choices
        )

        if self._soul_stage_scene_id:
            d = _load_scenes()
            if self._soul_stage_scene_id in d["scenes"]:
                d["scenes"][self._soul_stage_scene_id].setdefault("chat_log",[]).extend(turn_log)
                d["scenes"][self._soul_stage_scene_id]["chat_log"] = d["scenes"][self._soul_stage_scene_id]["chat_log"][-200:]
                d["scenes"][self._soul_stage_scene_id]["world_state"] = {
                    "location":         session.orchestrator.world_state.location,
                    "time_of_day":      session.orchestrator.world_state.time_of_day,
                    "atmosphere":       session.orchestrator.world_state.atmosphere,
                    "bg_image":         session.orchestrator.world_state.bg_image,
                    "ambient_audio":    session.orchestrator.world_state.ambient_audio,
                    "key_facts":        session.orchestrator.world_state.key_facts,
                    "player_inventory": session.orchestrator.world_state.player_inventory,
                    "player_status":    session.orchestrator.world_state.player_status,
                    "narrator_style":   session.orchestrator.world_state.narrator_style,
                }
                active_npcs =[]
                for npc in session.orchestrator.npc_registry.list_active():
                    active_npcs.append({"name": npc.name, "archetype": npc.archetype, "personality": npc.personality, "avatar_key": npc.avatar_key, "turn_count": npc.turn_count})
                d["scenes"][self._soul_stage_scene_id]["active_npcs"] = active_npcs
                _save_scenes(d)

        asyncio.create_task(session.orchestrator.sync_party_memory(session.conversation_method, session.party_names, turn_log, user_name))

    def _soul_stage_interrupt(self):
        if self.soul_stage_session and self.soul_stage_session.orchestrator.is_running:
            self.soul_stage_session.orchestrator.cancel()

    async def close_chat(self):
        self.current_active_character = None
        self.ui.character_description_chat.setText("")

        if hasattr(self, 'playback_worker'):
            self.playback_worker.stop()
            self.playback_worker.deleteLater()

        if self.expression_widget is not None:
            self.expression_widget.setParent(None)
            self.expression_widget.deleteLater()
            self.expression_widget = None

        if self.stackedWidget_expressions is not None:
            self.stackedWidget_expressions.setCurrentIndex(-1)
            self.stackedWidget_expressions.setParent(None)
            self.stackedWidget_expressions.deleteLater()
            self.stackedWidget_expressions = None
    ### SETUP BUTTONS ==================================================================================

    ### SETUP MAIN TAB AND CREATE CHARACTER ============================================================
    async def set_main_tab(self):
        """
        Configures the main interface tab by uploading a list of characters and setting up a user profile.
        """
        if hasattr(self, '_folder_header_widget') and self._folder_header_widget:
            try:
                self.ui.gridLayout_9.removeWidget(self._folder_header_widget)
                self._folder_header_widget.deleteLater()
            except RuntimeError:
                pass
            self._folder_header_widget = None

            self.ui.gridLayout_9.removeWidget(self.ui.scrollArea_characters_list)
            self.ui.gridLayout_9.addWidget(self.ui.scrollArea_characters_list, 1, 0, 1, 1)

        character_data = self.configuration_characters.load_configuration()
        character_list_scrollArea = self.ui.scrollArea_characters_list

        self.cards.clear()

        if self.container:
            self.container.deleteLater()
            self.container = None

        self.container = QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(0, 20, 20, 20)
        character_list_scrollArea.setWidget(self.container)

        if character_data.get("character_list") and len(character_data["character_list"]) > 0:
            personas_data = self.configuration_settings.get_user_data("personas")
            current_persona = self.configuration_settings.get_user_data("default_persona")
            if current_persona == "None" or current_persona is None:
                user_name = "User"
                user_avatar = "app/gui/icons/person.png"
            else:
                try:
                    user_name = personas_data[current_persona].get("user_name", "User")
                    user_avatar = personas_data[current_persona].get("user_avatar", "app/gui/icons/person.png")
                except Exception as e:
                    user_name = "User"
                    user_avatar = "app/gui/icons/person.png"

            avatar_path = user_avatar if user_avatar else "app/gui/icons/person.png"
            original_pixmap = QPixmap(avatar_path)

            if original_pixmap.isNull():
                original_pixmap = QPixmap("app/gui/icons/person.png")

            canvas_size = 54
            avatar_size = 46 

            rounded_pixmap = QPixmap(canvas_size, canvas_size)
            rounded_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            shadow_gradient = QtGui.QRadialGradient(27, 29, 23)
            shadow_gradient.setColorAt(0.0, QtGui.QColor(0, 0, 0, 160))
            shadow_gradient.setColorAt(0.7, QtGui.QColor(0, 0, 0, 40))
            shadow_gradient.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))

            painter.setBrush(QtGui.QBrush(shadow_gradient))
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(4, 6, avatar_size, avatar_size)

            path = QtGui.QPainterPath()
            path.addEllipse(4, 4, avatar_size, avatar_size)
            painter.setClipPath(path)

            scaled_pixmap = original_pixmap.scaled(
                avatar_size, avatar_size,
                QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

            painter.drawPixmap(4, 4, scaled_pixmap)
            painter.end()

            self.ui.user_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.ui.user_avatar_label.setScaledContents(False)
            self.ui.user_avatar_label.setPixmap(rounded_pixmap)

            display_name = user_name if user_name else "User"
            greeting_text = self.get_dynamic_greeting(display_name)
            self.ui.welcome_label_2.setText(greeting_text)

            self.ui.stackedWidget.setCurrentWidget(self.ui.main_characters_page)
            QApplication.processEvents()

            characters = character_data.get('character_list', {})

            groups = self._get_groups()
            grouped_characters = self._get_grouped_characters()

            for group_name, members in groups.items():
                preview_avatars = []
                char_cfg = character_data.get("character_list", {})
                for ch in members[:4]:
                    avatar_path = char_cfg.get(ch, {}).get("character_avatar", "")
                    if avatar_path:
                        preview_avatars.append(avatar_path)

                folder_card = CharacterFolderCard(
                    group_name = group_name,
                    char_count = len(members),
                    preview_avatars = preview_avatars,
                    main_app = self,
                    parent = self.container
                )
                self.cards.append(folder_card)
                folder_card.setVisible(True)
                self.update_layout()
                QApplication.processEvents()

            for character_name, data in characters.items():
                conversation_method = data.get("conversation_method")
                character_avatar_replacement = "app/gui/icons/logotype.png"

                character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                character_avatar = character_avatar_url

                match conversation_method:
                    case "Mistral AI":
                        conversation_method_image = "app/gui/icons/mistralai.png"
                    case "Open AI":
                        conversation_method_image = "app/gui/icons/openai.png"
                    case "OpenRouter":
                        conversation_method_image = "app/gui/icons/openrouter.png"
                    case "Local LLM":
                        conversation_method_image = "app/gui/icons/local_llm.png"
                    case "Anthropic":
                        conversation_method_image = "app/gui/icons/anthropic.png"
                    case "Google Gemini":
                        conversation_method_image = "app/gui/icons/gemini.png"
                    case "DeepSeek":
                        conversation_method_image = "app/gui/icons/deepseek.png"
                    case "Grok":
                        conversation_method_image = "app/gui/icons/grok.png"
                    case "Qwen":
                        conversation_method_image = "app/gui/icons/qwen.png"
                    case "Z.AI":
                        conversation_method_image = "app/gui/icons/zai.png"
                    case _:
                        conversation_method_image = "app/gui/icons/local_llm.png"

                card_widget = CharacterCardList(character_name=character_name, 
                    image_path=character_avatar, 
                    icon_api_path=conversation_method_image, 
                    method=self.open_chat, 
                    parent=self.container
                )
                character_widget = self.create_character_card_widget(character_name, card_widget)
                self.cards.append(character_widget)

                character_widget.setVisible(character_name not in grouped_characters)

                self.update_layout() 
                QApplication.processEvents()

            QtCore.QTimer.singleShot(0, self.update_layout)
            self.ui.lineEdit_search_character_menu.textChanged.connect(self.filter_characters)
        else:
            self.ui.stackedWidget.setCurrentWidget(self.ui.main_no_characters_page)

    def get_dynamic_greeting(self, user_name):
        """
        Generates a thematic, time-of-day aware, and randomized greeting.
        """
        import random
        import time
        from datetime import datetime
        
        if not hasattr(self, '_last_greeting_text'):
            self._last_greeting_text = None
            self._last_greeting_user = None
            self._last_greeting_time_period = None
            self._last_greeting_timestamp = 0.0

        hour = datetime.now().hour
        current_time = time.time()
        
        if 5 <= hour < 12:
            time_period = "morning"
        elif 12 <= hour < 17:
            time_period = "afternoon"
        elif 17 <= hour < 22:
            time_period = "evening"
        else:
            time_period = "night"

        if (self._last_greeting_text is not None and 
            self._last_greeting_user == user_name and 
            self._last_greeting_time_period == time_period and 
            (current_time - self._last_greeting_timestamp) < 1800.0):
            
            return self._last_greeting_text
            
        default_templates = {
            "morning": [
                "The gateway is active. Good morning, {user}.",
                "Morning, {user}! Your companions are waiting for you.",
                "Rise and shine, {user}. Let's load up some memories and start the day.",
                "Morning, {user}! Ready to continue our digital journey?",
                "Good morning, {user}. The interface is ready, and the souls are awake."
            ],
            "afternoon": [
                "Good afternoon, {user}. The Soul of Waifu network is stable.",
                "Taking an afternoon break, {user}? Let's check in on your companions.",
                "Hello, {user}. Need to escape reality for a bit? Your waifus are here.",
                "Afternoon, {user}. The portal is open, ready for some communication.",
                "Welcome back, {user}. Let's write another chapter of our story."
            ],
            "evening": [
                "Good evening, {user}. Time to cozy up and chat with your favorite companion.",
                "Evening, {user}. Ready to dive back into the Soul Stage?",
                "Welcome back, {user}. The perfect hour for a slow, deep conversation.",
                "Cozy evening vibes, {user}. Your companions have a lot to share with you.",
                "Evening, {user}. Let's see what thoughts were logged in the diary today."
            ],
            "night": [
                "Burning the midnight oil, {user}? Don't worry, digital souls don't sleep.",
                "Late night session, {user}? We are here to keep you company in the quiet hours.",
                "Quiet night vibes... Ready for a late-night chat, {user}?",
                "The world is asleep, but the gateway is alive. Welcome, {user}.",
                "Late night, {user}. Let's have a deep, heartfelt conversation."
            ]
        }
        
        idx = random.randint(1, 5)
        trans_key = f"greeting_{time_period}_{idx}"
        
        translated_template = self.translations.get(trans_key, None)
        if translated_template:
            template = translated_template
        else:
            template = default_templates[time_period][idx - 1]
            
        generated_greeting = template.format(user=user_name)

        self._last_greeting_text = generated_greeting
        self._last_greeting_user = user_name
        self._last_greeting_time_period = time_period
        self._last_greeting_timestamp = current_time

        return generated_greeting
    
    def create_character_card_widget(self, character_name, card_widget):
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")

        base_col = QtGui.QColor(0, 0, 0, 100)
        hover_col = QtGui.QColor(0, 0, 0, 200)

        call_btn = AnimatedHoverButton("app/gui/icons/phone.png", "#2E7D32", self.translations.get("call_btn_text", "Call"))
        voice_btn = AnimatedHoverButton("app/gui/icons/voice.png", "#1976D2", self.translations.get("voice_btn_text", "Voice Settings"))
        expr_btn = AnimatedHoverButton("app/gui/icons/expressions.png", "#F57C00", self.translations.get("expressions_btn_text", "Expressions"))
        del_btn = AnimatedHoverButton("app/gui/icons/bin.png", "#D32F2F", self.translations.get("delete_btn_text", "Delete"))
        folder_btn = AnimatedHoverButton("app/gui/icons/folder.png", hover_col, self.translations.get("move_to_folder_btn", "Move to folder"), base_color=base_col)
        
        def _move_to_folder():
            groups = self._get_groups()
            if not groups:
                dialog = SowConfirmDialog(
                    parent=self.main_window,
                    title=self.translations.get("no_folders_title", "No folders"),
                    text=self.translations.get("no_folders_prompt", "No folders yet. Create one?"),
                    confirm_text="Create",
                    danger=False
                )
                
                if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    self._open_create_folder_dialog()
                return

            folder_menu = QMenu()
            folder_menu.setStyleSheet("""
                QMenu {
                    background: #1e1e22; border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 10px; padding: 5px; color: white; font-size: 12px;
                }
                QMenu::item { padding: 7px 16px; border-radius: 5px; }
                QMenu::item:selected { background: rgba(255,255,255,0.1); }
            """)

            current_group = None
            for g, members in groups.items():
                if character_name in members:
                    current_group = g
                    break

            if current_group:
                remove_action = QAction(
                    f"{self.translations.get('remove_from_folder', 'Remove from folder')}",
                    folder_menu
                )
                def _remove():
                    grps = self._get_groups()
                    if character_name in grps.get(current_group, []):
                        grps[current_group].remove(character_name)
                        self._save_groups(grps)
                        asyncio.create_task(self.set_main_tab())
                remove_action.triggered.connect(_remove)
                folder_menu.addAction(remove_action)
                folder_menu.addSeparator()

            for g, members in groups.items():
                action = QAction(f"📁  {g}", folder_menu)
                if character_name in members:
                    action.setEnabled(False)
                def _move(checked=False, gname=g):
                    grps = self._get_groups()
                    for og, om in grps.items():
                        if character_name in om:
                            om.remove(character_name)
                    grps.setdefault(gname, [])
                    if character_name not in grps[gname]:
                        grps[gname].append(character_name)
                    self._save_groups(grps)
                    asyncio.create_task(self.set_main_tab())
                action.triggered.connect(_move)
                folder_menu.addAction(action)

            global_pos = folder_btn.mapToGlobal(
                QtCore.QPoint(0, folder_btn.height())
            )
            folder_menu.exec(global_pos)

        voice_btn.clicked.connect(lambda: self.open_voice_menu(character_name))
        expr_btn.clicked.connect(lambda: self.open_expressions_menu(character_name))
        del_btn.clicked.connect(lambda: self.delete_character(card_widget, character_name))
        folder_btn.clicked.connect(_move_to_folder)

        if sow_system_status:
            call_btn.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
            card_widget.action_panel_layout.addWidget(call_btn)

        card_widget.action_panel_layout.addWidget(voice_btn)

        if sow_system_status:
            card_widget.action_panel_layout.addWidget(expr_btn)

        card_widget.action_panel_layout.addWidget(del_btn)

        more_button = AnimatedHoverButton(
            icon_path="app/gui/icons/more.png", 
            hover_color=hover_col, 
            tooltip_text=self.translations.get("more_btn_tooltip", "Settings"),
            base_color=base_col
        )
        
        more_button.clicked.connect(lambda: self.check_main_character_information(character_name))
        
        more_button.setParent(card_widget)
        more_button.setGeometry(card_widget.width() - 40, -40, 30, 30) 
        more_button.raise_()

        card_widget.more_button = more_button
        card_widget.more_btn_anim = QtCore.QPropertyAnimation(more_button, b"pos")
        card_widget.more_btn_anim.setDuration(350)
        card_widget.more_btn_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

        folder_btn.setParent(card_widget)
        folder_btn.setGeometry(10, -40, 30, 30)
        folder_btn.raise_()

        def sync_folder_btn_y(pos):
            folder_btn.move(10, pos.y())

        card_widget.more_btn_anim.valueChanged.connect(sync_folder_btn_y)

        return card_widget

    def filter_characters(self, search_text):
        """
        Filters the character list based on the search text entered by the user.
        """
        search_text = search_text.lower().strip()
        groups = self._get_groups()
        grouped = self._get_grouped_characters()

        for card in self.cards:
            if isinstance(card, CharacterFolderCard):
                if search_text:
                    members = groups.get(card.group_name, [])
                    folder_matches = any(search_text in m.lower() for m in members)
                    card.setVisible(folder_matches)
                else:
                    card.setVisible(True)
            elif isinstance(card, CharacterCardList):
                char_name = card.character_name
                if search_text:
                    card.setVisible(search_text in char_name.lower())
                else:
                    card.setVisible(char_name not in grouped)

        self.update_layout()

    def update_layout(self):
        """
        Updates the layout of visible character cards in the grid.
        """
        while True:
            item = self.grid_layout.takeAt(0)
            if not item:
                break
            widget = item.widget()
            if widget and widget not in self.cards:
                widget.deleteLater()

        visible_cards = [card for card in self.cards if card.isVisible()]

        for i in reversed(range(self.grid_layout.columnCount())):
            self.grid_layout.setColumnMinimumWidth(i, 0)
            self.grid_layout.setColumnStretch(i, 0)

        scroll_area = self.ui.scrollArea_characters_list
        viewport_width = scroll_area.viewport().width()
        current_margins = self.grid_layout.contentsMargins()
        spacing = 10
        card_height = 270

        self.grid_layout.setHorizontalSpacing(spacing)
        self.grid_layout.setVerticalSpacing(0)

        card_width = 210
        n_cols = max(1, (viewport_width + spacing) // (card_width + spacing))
        total_width = n_cols * card_width + (n_cols - 1) * spacing

        self.grid_layout.setContentsMargins(
            0,
            current_margins.top(),
            0,
            current_margins.bottom()
        )

        for col in range(n_cols):
            self.grid_layout.setColumnMinimumWidth(col, card_width)
            self.grid_layout.setColumnStretch(col, 0)

        row, col = 0, 0
        for card in visible_cards:
            try:
                if card.parent() != self.container:
                    card.setParent(self.container)
                card.setFixedSize(card_width, card_height)
                self.grid_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                col += 1
                if col >= n_cols:
                    col = 0
                    row += 1
            except RuntimeError:
                continue

        vertical_spacing = 10
        row_count = row + 1 if col > 0 else row
        total_height = (row_count * card_height) + (max(0, row_count - 1) * vertical_spacing)

        margins = self.grid_layout.contentsMargins()
        self.container.setFixedSize(
            total_width + margins.left() + margins.right(),
            total_height + margins.top() + margins.bottom()
        )
        self.container.updateGeometry()

    def handle_resize(self, event):
        self.update_layout()
    
    def handle_rp_editors_resize(self, event):
        if self.ui.stackedWidget.currentWidget() == self.ui.rp_editors_page:
            QtCore.QTimer.singleShot(50, self.ui.update_rp_layout)

    def delete_character(self, card_widget, character_name):
        """
        Removes a character from the list and wipes their data.
        """
        title = self.translations.get("delete_message_1", "Delete Character")
        prompt_base = self.translations.get("delete_message_2", "Are you sure you want to delete ")
        
        message = f"{prompt_base} '{character_name}'?"

        confirm_dialog = SowConfirmDialog(
            parent=self.main_window,
            title=title,
            text=message,
            confirm_text="Delete",
            danger=True
        )

        if confirm_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.configuration_characters.delete_character(character_name)

            safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in character_name).strip()
            char_memory_dir = Path(f".soul/{safe_name}")
            if char_memory_dir.exists() and char_memory_dir.is_dir():
                try:
                    shutil.rmtree(char_memory_dir)
                    logger.info(f"Memory folder for {character_name} completely wiped.")
                except Exception as e:
                    logger.error(f"Could not wipe memory folder: {e}")

            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget == card_widget:
                    self.grid_layout.removeWidget(widget)
                    widget.deleteLater()
                    break

            self.cards = [card for card in self.cards if card != card_widget]

            asyncio.create_task(self.set_main_tab())

            if not self.cards:
                self.ui.stackedWidget.setCurrentWidget(self.ui.main_no_characters_page)

    def check_main_character_information(self, character_name):
        """
        Vertical Dashboard Design for Character Information.
        """
        _BG       = "#070709"
        _SURF1    = "#0B0B0F"
        _SURF2    = "#121218"
        _SURF3    = "#161622"
        _CARD_BG  = "#0E0E14"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BORDER   = "rgba(255, 255, 255, 0.045)"
        _BORDER_M = "rgba(255, 255, 255, 0.08)"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        _DANGER   = "#C44040"  
        _DNG_MUT  = "rgba(196, 64, 64, 0.11)"
        _DNG_GLO  = "rgba(196, 64, 64, 0.25)"

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        conversation_method = character_information.get("conversation_method", "Local LLM")
        character_avatar = character_information.get("character_avatar", "")

        character_description = character_information.get("character_description", "")
        character_personality = character_information.get("character_personality", "")
        first_message = character_information.get("first_message", "")
        scenario = character_information.get("scenario", "")
        example_messages = character_information.get("example_messages", "")
        alternate_greetings = character_information.get("alternate_greetings", "")
        creator_notes = character_information.get("creator_notes", "")

        config_user = self.configuration_settings.load_configuration()
        user_data = config_user.get("user_data", {})

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(1020, 750)
        dialog.resize(1050, 750)

        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        f_title = mf(14, QFont.Weight.Bold)
        f_label = mf(8,  QFont.Weight.Bold)
        f_input = mf(10, QFont.Weight.Medium)
        f_btn   = mf(10, QFont.Weight.DemiBold)

        dialog.setFont(f_input)
        dialog.setStyleSheet(
            f"QDialog {{ background-color: {_BG}; }}"
            f"QLabel {{ border: none; background: transparent; color: {_TEXT}; }}"
        )

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_column = QFrame()
        left_column.setObjectName("IGSidebar")
        left_column.setFixedWidth(280)
        left_column.setStyleSheet(
            f"QFrame#IGSidebar {{"
            f"  background-color: {_SURF1};"
            f"  border: none;"
            f"  border-right: 1px solid {_BORDER};"
            f"}}"
            f"QFrame#IGSidebar QLabel {{ border: none; background: transparent; }}"
        )
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(20, 24, 20, 24)
        left_layout.setSpacing(16)

        avatar_size = 110
        avatar_label = QLabel()
        
        source_pixmap = QPixmap(character_avatar)
        if source_pixmap.isNull():
            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
        else:
            scaled_pixmap = source_pixmap.scaled(
                avatar_size, avatar_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            x = (scaled_pixmap.width() - avatar_size) // 2
            y = (scaled_pixmap.height() - avatar_size) // 2
            square_pixmap = scaled_pixmap.copy(x, y, avatar_size, avatar_size)

            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            brush = QtGui.QBrush(square_pixmap)
            painter.setBrush(brush)
            painter.setPen(Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, avatar_size, avatar_size)
            painter.end()

        avatar_label.setPixmap(final_pixmap)
        avatar_label.setFixedSize(avatar_size, avatar_size)
        avatar_label.setStyleSheet("border: none; background: transparent;")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        avatar_label.setGraphicsEffect(shadow)
        
        avatar_container = QHBoxLayout()
        avatar_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addLayout(avatar_container)

        name_lbl = QLabel(self.translations.get("character_settings_name_label", "CHARACTER NAME"))
        name_lbl.setFont(f_label)
        name_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px;")
        left_layout.addWidget(name_lbl)

        name_edit = QLineEdit(character_name)
        name_edit.setObjectName("IGNameInput")
        name_edit.setFont(f_title)
        name_edit.setStyleSheet(
            f"QLineEdit#IGNameInput {{"
            f"  background-color: {_SURF2};"
            f"  color: {_TEXT};"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 8px 12px;"
            f"  selection-background-color: {_BLUE_MUT};"
            f"}}"
            f"QLineEdit#IGNameInput:focus {{"
            f"  border-color: {_BORDER_M};"
            f"  background-color: {_SURF3};"
            f"}}"
        )
        name_edit.setFixedHeight(38)
        left_layout.addWidget(name_edit)

        nav_title = QLabel(self.translations.get("character_settings_nav_label", "CONFIGURATION"))
        nav_title.setFont(f_label)
        nav_title.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 6px;")
        left_layout.addWidget(nav_title)

        nav_list = QtWidgets.QListWidget()
        nav_list.setObjectName("IGNavList")
        nav_list.setFont(f_btn)
        nav_list.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        nav_list.setStyleSheet(
            f"QListWidget#IGNavList {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#IGNavList::item {{"
            f"  color: {_TEXT_S};"
            f"  background-color: transparent;"
            f"  border: 1px solid transparent;"
            f"  border-radius: 6px;"
            f"  padding: 10px 14px;"
            f"  margin-bottom: 4px;"
            f"}}"
            f"QListWidget#IGNavList::item:hover {{"
            f"  background-color: {_SURF2};"
            f"  color: {_TEXT};"
            f"}}"
            f"QListWidget#IGNavList::item:selected {{"
            f"  background-color: {_BLUE_MUT};"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )
        left_layout.addWidget(nav_list)

        btn_duplicate = QPushButton("⧉  " + self.translations.get("btn_duplicate_character", "Duplicate"))
        btn_duplicate.setFont(f_btn)
        btn_duplicate.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_duplicate.setFixedHeight(36)
        btn_duplicate.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: rgba(75, 184, 255, 0.08);"
            f"  color: {_BLUE_BRT};"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {_BLUE_MUT};"
            f"  border-color: {_BLUE_BRT};"
            f"}}"
        )

        def _duplicate_from_dialog():
                import copy, uuid, datetime
                
                character_configuration = self.configuration_characters.load_configuration()
                character_list = character_configuration["character_list"]

                base_name = character_name
                suffix = 2
                new_name = f"{base_name}_{suffix}"
                while new_name in character_list:
                    suffix += 1
                    new_name = f"{base_name}_{suffix}"

                new_data = copy.deepcopy(character_list[character_name])
                
                new_chat_id = str(uuid.uuid4())
                message_id = str(uuid.uuid4())
                
                first_message = new_data.get("first_message", "")
                alternate_greetings = new_data.get("alternate_greetings", [])
                
                variants = [
                    {"variant_id": "default", "text": first_message}
                ]

                if isinstance(alternate_greetings, list):
                    for i, greeting in enumerate(alternate_greetings):
                        if greeting.strip():
                            variants.append({
                                "variant_id": f"v{i+1}",
                                "text": greeting.strip()
                            })

                main_message = {
                    "message_id": message_id,
                    "sequence_number": 1,
                    "author_name": new_name,
                    "is_user": False,
                    "current_variant_id": "default",
                    "variants": variants
                }

                chat_history = []
                chat_history.append({
                    "user": "",
                    "character": first_message
                })

                default_chat_name = self.translations.get("default_chat_name", "Default Chat")
                new_chat = {
                    "name": default_chat_name,
                    "created_at": datetime.datetime.now().isoformat(),
                    "current_emotion": "neutral",
                    "chat_history": chat_history,
                    "chat_content": {message_id: main_message},
                }

                new_data["chats"] = {
                    new_chat_id: new_chat
                }
                new_data["current_chat"] = new_chat_id
                
                if "chat_id" in new_data:
                    del new_data["chat_id"]

                character_list[new_name] = new_data
                character_configuration["character_list"] = character_list
                self.configuration_characters.save_configuration_edit(character_configuration)

                success_msg = self.translations.get("duplicate_success", f"Character duplicated as '{new_name}'")
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("duplicate_title", "Character Duplicated"),
                    text=success_msg,
                    msg_type="success"
                )
                
                dialog.accept()
                asyncio.create_task(self.set_main_tab())

        btn_duplicate.clicked.connect(_duplicate_from_dialog)

        new_dialog_button = QPushButton(self.translations.get("character_edit_start_new_dialogue", "START NEW CHAT"), dialog)
        new_dialog_button.setFont(f_btn)
        new_dialog_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        new_dialog_button.setFixedHeight(36)
        new_dialog_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {_BLUE};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_BLUE_MUT};"
            f"  border-color: {_BLUE_BRT};"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )

        save_button = QPushButton(self.translations.get("character_edit_save_button", "SAVE CHANGES"), dialog)
        save_button.setFont(f_btn)
        save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_button.setFixedHeight(36)
        save_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: {_BLUE_MUT};"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {_BLUE};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: rgba(75, 184, 255, 0.25);"
            f"  border-color: rgba(75, 184, 255, 0.55);"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )

        ok_button = QPushButton(self.translations.get("personas_editor_close", "CLOSE"), dialog)
        ok_button.setFont(f_btn)
        ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_button.setFixedHeight(36)
        ok_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 6px;"
            f"  color: {_TEXT_S};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_SURF2};"
            f"  border-color: {_BORDER_M};"
            f"  color: {_TEXT};"
            f"}}"
        )
        ok_button.clicked.connect(dialog.close)

        left_layout.addWidget(btn_duplicate)
        left_layout.addWidget(new_dialog_button)
        left_layout.addWidget(save_button)
        left_layout.addWidget(ok_button)

        main_layout.addWidget(left_column)

        workspace = QFrame()
        workspace.setObjectName("IGWorkspace")
        workspace.setStyleSheet("QFrame#IGWorkspace { background: transparent; border: none; }")
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(28, 24, 28, 24)
        workspace_layout.setSpacing(12)

        stacked_widget = QStackedWidget()
        stacked_widget.setStyleSheet("QStackedWidget { background: transparent; border: none; }")
        workspace_layout.addWidget(stacked_widget)

        def create_page_card():
            card = QFrame()
            card.setObjectName("IGPageCard")
            card.setStyleSheet(
                f"QFrame#IGPageCard {{"
                f"  background-color: {_CARD_BG};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 12px;"
                f"}}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
                "QScrollBar:vertical { background: transparent; width: 8px; }"
                f"QScrollBar::handle:vertical {{ background: {_BORDER_M}; border-radius: 4px; }}"
                f"QScrollBar::handle:vertical:hover {{ background: {_TEXT_S}; }}"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }"
            )
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(8, 4, 8, 12)
            content_layout.setSpacing(12)
            
            scroll.setWidget(content_widget)
            card_layout.addWidget(scroll)
            return card, content_layout

        def add_glass_text_edit(layout, label_text, content, placeholder=""):
            lbl = QLabel(label_text)
            lbl.setFont(f_label)
            lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 8px; margin-bottom: 4px; border: none;")
            layout.addWidget(lbl)

            text_edit = QTextEdit()
            text_edit.setFont(f_input)
            text_edit.setPlainText(str(content) if content else "")
            if placeholder: 
                text_edit.setPlaceholderText(placeholder)
            
            text_edit.setStyleSheet(
                f"QTextEdit {{"
                f"  background-color: {_SURF2};"
                f"  color: {_TEXT};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 8px;"
                f"  padding: 12px 14px;"
                f"  selection-background-color: {_BLUE_MUT};"
                f"  line-height: 1.4;"
                f"}}"
                f"QTextEdit:focus {{"
                f"  border-color: {_BORDER_M};"
                f"  background-color: {_SURF3};"
                f"}}"
            )
            text_edit.setMinimumHeight(180)
            layout.addWidget(text_edit)
            return text_edit

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 8px; border-radius: 4px; }}
        """

        def create_combo_section(parent_layout, label_text, items, current_text, callback):
            lbl = QLabel(label_text)
            lbl.setFont(f_label)
            lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 8px; border: none;")
            parent_layout.addWidget(lbl)

            combo = QtWidgets.QComboBox()
            combo.setFont(f_input)
            combo.setStyleSheet(combo_style)
            combo.setFixedHeight(40)
            combo.addItems(items)
            combo.setCurrentText(current_text)
            combo.currentTextChanged.connect(callback)
            parent_layout.addWidget(combo)
            return combo

        # --- PAGE 0: General Settings ---
        page0, layout0 = create_page_card()
        
        def update_character_conversation_method(char_name, new_method):
            try:
                c_data = self.configuration_characters.load_configuration()
                c_data["character_list"][char_name]["conversation_method"] = new_method
                self.configuration_characters.save_configuration_edit(c_data)
                asyncio.create_task(self.set_main_tab())
            except Exception as e: print(e)

        def update_selected_persona(char_name, new_persona):
            try:
                c_data = self.configuration_characters.load_configuration()
                c_data["character_list"][char_name]["selected_persona"] = new_persona
                self.configuration_characters.save_configuration_edit(c_data)
            except Exception as e: print(e)

        def update_selected_system_prompt_preset(char_name, new_preset):
            try:
                c_data = self.configuration_characters.load_configuration()
                c_data["character_list"][char_name]["selected_system_prompt_preset"] = new_preset
                self.configuration_characters.save_configuration_edit(c_data)
            except Exception as e: print(e)

        def update_lorebooks(char_name, new_lorebooks_list):
            try:
                c_data = self.configuration_characters.load_configuration()
                c_data["character_list"][char_name]["selected_lorebooks"] = new_lorebooks_list

                if new_lorebooks_list:
                    c_data["character_list"][char_name]["selected_lorebook"] = new_lorebooks_list[0]
                else:
                    c_data["character_list"][char_name]["selected_lorebook"] = "None"
                self.configuration_characters.save_configuration_edit(c_data)
            except Exception as e: print(e)

        create_combo_section(
            layout0, 
            self.translations.get("character_edit_conv_method", "Conversation Method"), 
            ["Mistral AI", "OpenRouter", "Open AI", "Local LLM", "Anthropic", "Google Gemini", "DeepSeek", "Grok", "Qwen", "Z.AI"], conversation_method,
            lambda txt: update_character_conversation_method(character_name, txt)
        )
        
        personas = list(user_data.get("personas", {}).keys())
        create_combo_section(
            layout0, 
            self.translations.get("character_edit_persona", "Persona"), 
            ["None"] + personas, 
            character_information.get("selected_persona", "None"),
            lambda txt: update_selected_persona(character_name, txt)
        )

        presets = list(user_data.get("presets", {}).keys())
        create_combo_section(
            layout0, 
            self.translations.get("character_edit_prompt_preset", "System Prompt Preset"), 
            ["By default"] + presets,
            character_information.get("selected_system_prompt_preset", "By default"),
            lambda txt: update_selected_system_prompt_preset(character_name, txt)
        )

        lorebooks = sorted(list(user_data.get("lorebooks", {}).keys()))
        
        def create_multi_lorebook_section(parent_layout, label_text, all_lorebooks, character_name):
            lbl = QLabel(label_text)
            lbl.setFont(f_label)
            lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 8px; border: none;")
            parent_layout.addWidget(lbl)

            curr_selected = character_information.get("selected_lorebooks", [])
            if not curr_selected:
                old_lb = character_information.get("selected_lorebook", "None")
                if old_lb != "None": curr_selected = [old_lb]

            btn = QPushButton()
            btn.setFont(f_input)
            btn.setFixedHeight(40)
            
            def get_btn_text(sel):
                if not sel: 
                    return self.translations.get("character_settings_none", "None")
                if len(sel) == 1: 
                    return sel[0]
                return self.translations.get("character_settings_selected_count", "Selected: {count}").format(count=len(sel))
            
            btn.setText(get_btn_text(curr_selected))
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: {_SURF2}; color: {_TEXT};"
                f"  border: 1px solid {_BORDER}; border-radius: 8px; text-align: left; padding: 10px 15px;"
                f"}}"
                f"QPushButton:hover {{ border: 1px solid {_BORDER_M}; background-color: {_SURF3}; }}"
            )
            
            def open_sel():
                c_data = self.configuration_characters.load_configuration()
                c_info = c_data.get("character_list", {}).get(character_name, {})
                curr = c_info.get("selected_lorebooks", [])
                if not curr:
                    old = c_info.get("selected_lorebook", "None")
                    if old != "None": curr = [old]
                    
                sel_dialog = MultiSelectDialog(
                    self.translations.get("lorebook_selector_title", "Select Lorebooks"),
                    all_lorebooks,
                    curr,
                    self.translations,
                    dialog
                )
                if sel_dialog.exec():
                    new_sel = sel_dialog.get_selected_items()
                    update_lorebooks(character_name, new_sel)
                    btn.setText(get_btn_text(new_sel))
            
            btn.clicked.connect(open_sel)
            parent_layout.addWidget(btn)
            return btn

        create_multi_lorebook_section(
            layout0, 
            self.translations.get("character_edit_lorebooks", "Lorebooks"), 
            lorebooks, 
            character_name
        )
        layout0.addStretch()
        stacked_widget.addWidget(page0)

        # --- PAGE 1: Identity ---
        page1, layout1 = create_page_card()
        description_edit = add_glass_text_edit(
            layout1, 
            self.translations.get("character_edit_description", "Character Description"), 
            character_description, 
            self.translations.get("character_edit_description_placeholder_1", "Enter description")
        )
        personality_edit = add_glass_text_edit(
            layout1, 
            self.translations.get("character_edit_personality", "Personality"), 
            character_personality, 
            self.translations.get("character_edit_personality_placeholder", "Enter personality traits")
        )
        stacked_widget.addWidget(page1)

        # --- PAGE 2: Scenario ---
        page2, layout2 = create_page_card()
        first_message_edit = add_glass_text_edit(
            layout2, 
            self.translations.get("character_edit_first_message", "First Message"), 
            first_message, 
            self.translations.get("character_edit_first_message_placeholder", "Enter first message")
        )
        scenario_edit = add_glass_text_edit(
            layout2, 
            self.translations.get("scenario", "Scenario"), 
            scenario, 
            self.translations.get("placeholder_scenario", "Conversation scenario")
        )
        stacked_widget.addWidget(page2)

        # --- PAGE 3: Examples & Notes ---
        page3, layout3 = create_page_card()
        example_messages_edit = add_glass_text_edit(
            layout3, 
            self.translations.get("example_messages_title", "Example Messages"), 
            example_messages, 
            self.translations.get("placeholder_example_messages", "Use <START> macro")
        )
        alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
        alternate_greetings_edit = add_glass_text_edit(
            layout3, 
            self.translations.get("alternate_greetings_label", "Alternate Greetings"), 
            alt_greets_text, 
            self.translations.get("placeholder_alternate_greetings", "Use <GREETING> macro")
        )
        creator_notes_edit = add_glass_text_edit(
            layout3, 
            self.translations.get("creator_notes_label", "Creator Notes"), 
            creator_notes, 
            self.translations.get("placeholder_creator_notes", "Any additional notes")
        )
        stacked_widget.addWidget(page3)

        # --- PAGE 4: Chat Manager ---
        page4, layout4 = create_page_card()
        
        export_card_lbl = QLabel(self.translations.get("character_card_label", "Character Card"))
        export_card_lbl.setFont(f_label)
        export_card_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none;")
        layout4.addWidget(export_card_lbl)

        export_card_btn = QPushButton(self.translations.get("export_card_button", "Export character as PNG"))
        export_card_btn.setFont(f_btn)
        export_card_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        export_card_btn.setFixedHeight(40)
        export_card_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {_SURF2}; color: {_TEXT};"
            f"  border: 1px solid {_BORDER}; border-radius: 8px;"
            f"}}"
            f"QPushButton:hover {{ background-color: {_SURF3}; border-color: {_BORDER_M}; }}"
        )
        
        def export_character_card_information(character_name):
            try:
                config_data = self.configuration_characters.load_configuration()
                char_info = config_data.get("character_list", {}).get(character_name, {})
                
                sow_variables = char_info.get("sow_variables", [])
                card_version = char_info.get("character_version", "1.0.0")

                current_image_path = character_avatar
                current_persona = self.configuration_settings.get_user_data("default_persona")
                user_name = self.configuration_settings.get_user_data("personas").get(current_persona, {}).get("user_name", "User") if current_persona != "None" else "User"

                char_data = {
                    "spec": "chara_card_v2", "spec_version": "2.0",
                    "data": {
                        'name': name_edit.text().strip(), 
                        'description': description_edit.toPlainText().strip(),
                        'personality': personality_edit.toPlainText().strip(), 
                        'first_mes': first_message_edit.toPlainText().strip(),
                        'scenario': scenario_edit.toPlainText().strip(), 
                        'mes_example': example_messages_edit.toPlainText().strip(),
                        'creator_notes': creator_notes_edit.toPlainText().strip(), 
                        'character_version': card_version,
                        'creator': user_name, 
                        'tags': ["sow", "custom"], 
                        'extensions': {
                            "sow_variables": sow_variables
                        },
                        'alternate_greetings': self.parse_alternate_greetings(alternate_greetings_edit.toPlainText().strip()),
                        'system_prompt': "", 'post_history_instructions': ""
                    }
                }

                selected_lorebooks = char_info.get("selected_lorebooks", [])
                if not selected_lorebooks:
                    old_lorebook = char_info.get("selected_lorebook", "None")
                    if old_lorebook != "None":
                        selected_lorebooks = [old_lorebook]

                if selected_lorebooks:
                    all_lorebooks = config_data.get("user_data", {}).get("lorebooks", {})
                    books_to_export = []
                    for lb_name in selected_lorebooks:
                        if lb_name in all_lorebooks:
                            books_to_export.append(all_lorebooks[lb_name])
                        else:
                            logger.warning(f"Lorebook '{lb_name}' selected but not found in database.")
                            
                    if len(books_to_export) == 1:
                        char_data["data"]["character_book"] = books_to_export[0]
                    elif len(books_to_export) > 1:
                        char_data["data"]["character_book"] = books_to_export

                file_path, selected_filter = QFileDialog.getSaveFileName(
                    None, 
                    self.translations.get("export_card_dialog_title", "Export Character Card"), 
                    f"{character_name}", 
                    "PNG Images (*.png);;JSON Files (*.json)"
                )
                
                if not file_path:
                    return

                if file_path.lower().endswith('.json') or "JSON" in selected_filter:
                    if not file_path.lower().endswith('.json'):
                        file_path += ".json"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(char_data, f, ensure_ascii=False, indent=4)
                else:
                    if not file_path.lower().endswith('.png'):
                        file_path += ".png"

                    image = Image.open(current_image_path).convert("RGBA") if os.path.exists(current_image_path) else Image.open("app/gui/icons/export_card.png").convert("RGBA")

                    json_str = json.dumps(char_data, ensure_ascii=False)
                    b64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
                    
                    png_info = PngImagePlugin.PngInfo()
                    png_info.add_text("chara", b64_data)
                    image.save(file_path, format="PNG", pnginfo=png_info)
                
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("success_title", "Success"),
                    text=f"Character card exported to {os.path.basename(file_path)}",
                    msg_type="success"
                )
            
            except Exception as e:
                logger.error(f"Couldn't export character card: {e}", exc_info=True)
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("error_title", "Error"),
                    text=f"Couldn't export character card:\n{str(e)}",
                    msg_type="error"
                )

        export_card_btn.clicked.connect(lambda: export_character_card_information(character_name))
        layout4.addWidget(export_card_btn)

        separator_chat = QFrame()
        separator_chat.setFixedHeight(1)
        separator_chat.setStyleSheet(f"background-color: {_BORDER}; margin: 16px 0px; border: none;")
        layout4.addWidget(separator_chat)

        chat_manager_lbl = QLabel(self.translations.get("chat_manager_label", "Chat History Manager"))
        chat_manager_lbl.setFont(f_label)
        chat_manager_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none;")
        layout4.addWidget(chat_manager_lbl)

        chat_row = QHBoxLayout()
        chat_row.setSpacing(8)
        chat_combobox = QtWidgets.QComboBox()
        chat_combobox.setFont(f_input)
        chat_combobox.setStyleSheet(combo_style)
        chat_combobox.setFixedHeight(40)

        chats = character_information.get("chats", {})
        current_chat_id = character_information.get("current_chat", None)
        
        for chat_id, chat_data in chats.items():
            chat_name = chat_data.get("name", f"Chat {chat_id[:6]}")
            chat_combobox.addItem(chat_name, userData=chat_id)

        if current_chat_id and current_chat_id in chats:
            for index in range(chat_combobox.count()):
                if chat_combobox.itemData(index) == current_chat_id:
                    chat_combobox.setCurrentIndex(index)
                    break

        chat_row.addWidget(chat_combobox, stretch=1)

        icon_btn_style = f"""
            QPushButton {{
                background-color: {_SURF2};
                border: 1px solid {_BORDER};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {_SURF3};
                border-color: {_BORDER_M};
            }}
        """
        
        def create_icon_btn(icon_path):
            btn = QPushButton()
            btn.setFixedSize(40, 40)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(icon_btn_style)
            icon = QtGui.QIcon()
            icon.addPixmap(QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            btn.setIcon(icon)
            return btn

        rename_button = create_icon_btn("app/gui/icons/edit.png")
        
        delete_button = QPushButton()
        delete_button.setFixedSize(40, 40)
        delete_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        delete_button.setIcon(QtGui.QIcon("app/gui/icons/bin.png"))
        delete_button.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {_DNG_MUT};"
            f"  border: 1px solid {_DNG_GLO};"
            f"  border-radius: 8px;"
            f"  color: {_DANGER};"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: rgba(196, 64, 64, 0.22);"
            f"  border-color: rgba(196, 64, 64, 0.45);"
            f"}}"
        )
        
        import_button = create_icon_btn("app/gui/icons/import.png")
        export_button = create_icon_btn("app/gui/icons/export.png")

        chat_row.addWidget(rename_button)
        if len(chats) > 1: chat_row.addWidget(delete_button)
        chat_row.addWidget(import_button)
        chat_row.addWidget(export_button)

        layout4.addLayout(chat_row)

        def on_chat_selected(index):
            selected_chat_name = chat_combobox.currentText()
            config = self.configuration_characters.load_configuration()
            char_chats = config["character_list"][character_name].get("chats", {})
            for cid, cinfo in char_chats.items():
                if cinfo.get("name") == selected_chat_name:
                    config["character_list"][character_name]["current_chat"] = cid
                    self.configuration_characters.save_configuration_edit(config)
                    break

        def export_chat():
            config = self.configuration_characters.load_configuration()
            char_chats = config["character_list"][character_name].get("chats", {})
            selected_name = chat_combobox.currentText()
            selected_id = next((cid for cid, cinfo in char_chats.items() if cinfo.get("name") == selected_name), None)
            
            if not selected_id: return False
            
            export_data = {
                "exported_from": character_name,
                "exported_at": datetime.datetime.now().isoformat(),
                "chat_id": selected_id,
                "chat": char_chats[selected_id]
            }
            file_path, _ = QFileDialog.getSaveFileName(None, "Save chat", f"{character_name}_{char_chats[selected_id]['name']}.sowchat", "Chat Files (*.sowchat)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=4, ensure_ascii=False)
                return True
            return False

        def import_chat():
            file_path, _ = QFileDialog.getOpenFileName(None, "Import Chat", "", "Chat Files (*.sowchat)")
            if not file_path: return False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                chat_id = import_data.get("chat_id")
                imported_chat = import_data.get("chat", {})
                
                config = self.configuration_characters.load_configuration()
                existing_chats = config["character_list"][character_name].setdefault("chats", {})
                
                if chat_id in existing_chats:
                    conflict_dialog = SowConfirmDialog(
                        parent=self.main_window,
                        title=self.translations.get("conflict_title", "Conflict"),
                        text=f"Chat conflict detected. Overwrite existing chat '{existing_chats[chat_id].get('name', 'Unknown')}'?",
                        confirm_text="Overwrite",
                        danger=False 
                    )
                    
                    if conflict_dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                        chat_id = str(uuid.uuid4())
                        imported_chat["name"] += f" ({self.translations.get('imported_suffix', 'Imported')})"
                
                existing_chats[chat_id] = imported_chat
                self.configuration_characters.save_configuration_edit(config)
                
                chat_combobox.addItem(imported_chat["name"], userData=chat_id)
                chat_combobox.setCurrentIndex(chat_combobox.count() - 1)
                return True
            except Exception as e:
                print(f"Error importing chat: {e}")
                return False

        def rename_chat():
            index = chat_combobox.currentIndex()
            if index < 0: return
            old_name = chat_combobox.currentText()
            
            qdialog_font = QtGui.QFont()
            qdialog_font.setFamily("Inter Tight SemiBold")
            qdialog_font.setPointSize(10)
            qdialog_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            
            dialog = QInputDialog()
            dialog.setFont(qdialog_font)
            new_name, ok = dialog.getText(None, "Rename Chat", "Enter new chat name:", text=old_name)
            
            if ok and new_name.strip():
                config = self.configuration_characters.load_configuration()
                char_chats = config["character_list"][character_name]["chats"]
                found_id = next((cid for cid, cinfo in char_chats.items() if cinfo.get("name") == old_name), None)
                if found_id:
                    char_chats[found_id]["name"] = new_name
                    self.configuration_characters.save_configuration_edit(config)
                    chat_combobox.setItemText(index, new_name)

        def delete_chat():
            index = chat_combobox.currentIndex()
            if index < 0: return
            old_name = chat_combobox.currentText()

            dialog = SowConfirmDialog(
                parent=self.main_window,
                title="Delete chat",
                text="Are you sure you want to delete this chat?",
                confirm_text="Delete",
                danger=True
            )
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                config = self.configuration_characters.load_configuration()
                char_data = config["character_list"][character_name]
                found_id = next((cid for cid, cinfo in char_data["chats"].items() if cinfo.get("name") == old_name), None)
                
                if found_id:
                    del char_data["chats"][found_id]
                    
                    if not char_data["chats"]:
                        new_chat_id = str(uuid.uuid4())
                        first_message = char_data.get("first_message", "")
                        alternate_greetings = char_data.get("alternate_greetings", [])
                        
                        variants = [{"variant_id": "default", "text": first_message}]
                        if isinstance(alternate_greetings, list):
                            for i, greeting in enumerate(alternate_greetings):
                                if greeting.strip():
                                    variants.append({"variant_id": f"v{i+1}", "text": greeting.strip()})

                        message_id = str(uuid.uuid4())
                        main_message = {
                            "message_id": message_id,
                            "sequence_number": 1,
                            "author_name": character_name,
                            "is_user": False,
                            "current_variant_id": "default",
                            "variants": variants
                        }

                        chat_history = [{"user": "", "character": first_message}]

                        default_chat_name = self.translations.get("default_chat_name", "Default Chat")
                        new_chat = {
                            "name": default_chat_name,
                            "created_at": datetime.datetime.now().isoformat(),
                            "current_emotion": "neutral",
                            "chat_history": chat_history,
                            "chat_content": {message_id: main_message},
                        }

                        char_data["chats"][new_chat_id] = new_chat
                        char_data["current_chat"] = new_chat_id
                        
                        chat_combobox.setItemText(index, default_chat_name)
                        chat_combobox.setItemData(index, new_chat_id)
                    else:
                        if char_data.get("current_chat") == found_id:
                            char_data["current_chat"] = list(char_data["chats"].keys())[0] if char_data["chats"] else None
                        chat_combobox.removeItem(index)
                        
                    self.configuration_characters.save_configuration_edit(config)

        export_button.clicked.connect(export_chat)
        import_button.clicked.connect(import_chat)      
        rename_button.clicked.connect(rename_chat)
        if len(chats) > 1: delete_button.clicked.connect(delete_chat)
        chat_combobox.currentIndexChanged.connect(on_chat_selected)

        new_dialog_button.clicked.connect(lambda: asyncio.create_task(
            self.start_new_dialog_main(
                dialog, conversation_method, character_name,
                name_edit, description_edit, personality_edit,
                scenario_edit, first_message_edit, example_messages_edit,
                alternate_greetings_edit, creator_notes_edit
            )
        ))

        layout4.addStretch()
        stacked_widget.addWidget(page4)

        btn_settings_text = self.translations.get("btn_check_settings", "General Settings")
        btn_identity_text = self.translations.get("btn_check_identity", "Identity / Personality")
        btn_scenario_text = self.translations.get("btn_check_scenario", "Scenario / Greeting")
        btn_examples_text = self.translations.get("btn_check_examples", "Examples / Notes")
        btn_chats_text = self.translations.get("btn_check_chats", "Chat Manager / Export")

        nav_list.addItem(btn_settings_text)
        nav_list.addItem(btn_identity_text)
        nav_list.addItem(btn_scenario_text)
        nav_list.addItem(btn_examples_text)
        nav_list.addItem(btn_chats_text)

        nav_list.currentRowChanged.connect(stacked_widget.setCurrentIndex)
        nav_list.setCurrentRow(0)

        workspace_layout.addWidget(stacked_widget)
        main_layout.addWidget(workspace, 1)
        dialog.exec()

    def save_changes_main_menu(self, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Saves changes to the configuration file for the specified character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data["character_list"]

        if character_name in character_list:
            character_list[character_name]["character_title"] = creator_notes_edit.toPlainText()
            character_list[character_name]["character_description"] = description_edit.toPlainText()
            character_list[character_name]["character_personality"] = personality_edit.toPlainText()
            character_list[character_name]["scenario"] = scenario_edit.toPlainText()
            character_list[character_name]["first_message"] = first_message_edit.toPlainText()
            character_list[character_name]["example_messages"] = example_messages_edit.toPlainText()
            raw_text = alternate_greetings_edit.toPlainText().strip()
            if raw_text:
                greetings_list = [g.strip() for g in raw_text.split("<GREETING>") if g.strip()]
            else:
                greetings_list = []
            character_list[character_name]["alternate_greetings"] = greetings_list 
            
            new_name = name_edit.text()
            if new_name == character_name:
                pass
            else:
                character_data = character_list.pop(character_name)
                character_list[new_name] = character_data

            configuration_data["character_list"] = character_list
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("character_edit_title", "Character Settings"),
                text=self.translations.get("character_edit_saved_2", "The changes were saved successfully!"),
                msg_type="success"
            )
        else:
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("system_error_title", "System Error"),
                text=self.translations.get("character_edit_saved_error_2", "Character was not found in the configuration."),
                msg_type="error",
                duration=5000
            )
        
        asyncio.create_task(self.set_main_tab())
        
    async def start_new_dialog_main(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        title = self.translations.get("character_edit_start_new_dialogue", "Start new dialogue")
        message = self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue?")

        dialog = SowConfirmDialog(
            parent=self.main_window,
            title=title,
            text=message,
            confirm_text="Confirm",
            danger=False
        )
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        chat_name, ok = QInputDialog.getText(
            dialog,
            self.translations.get("new_chat_title", "New Chat"),
            self.translations.get("new_chat_prompt", "Enter chat name:")
        )

        if not ok or not chat_name.strip():
            chat_name = self.translations.get("default_chat_name", "Default Chat")

        new_name = name_edit.text()
        new_description = description_edit.toPlainText()
        new_personality = personality_edit.toPlainText()
        new_scenario = scenario_edit.toPlainText()
        new_first_message = first_message_edit.toPlainText()
        new_example_messages = example_messages_edit.toPlainText()
        raw_text = alternate_greetings_edit.toPlainText().strip()
        if raw_text:
            greetings_list = [g.strip() for g in raw_text.split("<GREETING>") if g.strip()]
        else:
            greetings_list = []
        new_alternate_greetings = greetings_list
        new_creator_notes = creator_notes_edit.toPlainText()

        self.configuration_characters.create_new_chat(
            character_name=character_name,
            conversation_method=conversation_method,
            new_name=new_name,
            new_description=new_description,
            new_personality=new_personality,
            new_scenario=new_scenario,
            new_first_message=new_first_message,
            new_example_messages=new_example_messages,
            new_alternate_greetings=new_alternate_greetings,
            new_creator_notes=new_creator_notes,
            chat_name=chat_name
        )

        self.messages.clear()
        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.ui.stackedWidget.setCurrentWidget(self.ui.main_characters_page)

        sow_toast(
            parent=self.main_window,
            title=self.translations.get("new_chat_title", "Chat System"),
            text=self.translations.get("character_edit_start_new_dialogue_success", "A new chat has been successfully started!"),
            msg_type="success"
        )
        
        dialog.close()
        asyncio.create_task(self.set_main_tab())
        self.main_window.updateGeometry()
        QtCore.QTimer.singleShot(0, self.update_layout)

    def _prepare_blank_character_and_open_editor(self):
        """
        Prepares a blank character editor sheet, populates options dropdowns, and switches UI.
        """
        self.ui.pushButton_rp_editors.click()
        self.prepare_new_character_editor()
        self.populate_editor_character_list()

        self.ui.comboBox_user_persona_building.clear()
        self.ui.comboBox_system_prompt_building.clear()
        self._selected_lorebooks_building = []
        
        if hasattr(self, '_update_lorebook_button_text'):
            self._update_lorebook_button_text()

        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})

        personas = user_data.get("personas", {})
        self.ui.comboBox_user_persona_building.addItem("None")
        for name in personas:
            self.ui.comboBox_user_persona_building.addItem(name)
        self.ui.comboBox_user_persona_building.setCurrentIndex(0)

        presets = user_data.get("presets", {})
        self.ui.comboBox_system_prompt_building.addItem("By default")
        for name in presets:
            self.ui.comboBox_system_prompt_building.addItem(name)
        self.ui.comboBox_system_prompt_building.setCurrentIndex(0)

        lorebooks = user_data.get("lorebooks", {})
        self.ui.comboBox_lorebook_building.addItem("None")
        for name in lorebooks:
            self.ui.comboBox_lorebook_building.addItem(name)
        self.ui.comboBox_lorebook_building.setCurrentIndex(0)

        self._editor_provider_value = None
        self.refresh_character_provider_options()

        QtCore.QTimer.singleShot(0, lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.create_character_page))

    def _on_provider_card_clicked(self, button):
        val = button.property("provider_value")
        self._editor_provider_value = val
        self.configuration_settings.update_main_setting("conversation_method", val)
        self.refresh_character_model_options()

    def refresh_character_provider_options(self, configured_provider=None):
        if not hasattr(self.ui, "provider_group"):
            return
        local_model = self.configuration_settings.get_main_setting("local_llm")
        available = []
        for button in self.ui.provider_group.buttons():
            provider = button.property("provider_value")
            enabled = bool(local_model and os.path.exists(local_model)) if provider == "Local LLM" else self._is_provider_verified(provider)
            button.setVisible(enabled)
            if enabled:
                available.append(provider)

        current = configured_provider or self._editor_provider_value
        if not configured_provider and current not in available:
            current = available[0] if available else None
        self._editor_provider_value = current
        for button in self.ui.provider_group.buttons():
            if button.property("provider_value") == current:
                button.setChecked(True)
                break

        if configured_provider and configured_provider not in available:
            status = f"Configured provider: {configured_provider} (not currently confirmed)"
        elif current:
            status = f"Configured provider: {current}"
        else:
            status = "No confirmed provider. Check a model in Configuration first."
        self.ui.label_character_provider_status.setText(status)
        self.refresh_character_model_options()

    def refresh_character_model_options(self, model_override=None):
        if not hasattr(self.ui, "comboBox_character_model_override"):
            return
        combo = self.ui.comboBox_character_model_override
        override = model_override if model_override is not None else combo.currentText()
        if override == "Use provider default":
            override = ""
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Use provider default", "")
        if self._editor_provider_value == "OpenRouter":
            for model in self.models:
                combo.addItem(model["name"], model["id"])
        index = combo.findData(override)
        if index >= 0:
            combo.setCurrentIndex(index)
        else:
            combo.setEditText(override)
        combo.blockSignals(False)

    def _editor_model_override(self):
        combo = self.ui.comboBox_character_model_override
        value = combo.currentData()
        if value is None:
            value = combo.currentText()
        value = value.strip()
        return "" if value == "Use provider default" else value
    
    def _get_groups(self) -> dict:
        cfg = self.configuration_settings.load_configuration()
        return cfg.get("character_groups", {})

    def _save_groups(self, groups: dict):
        cfg = self.configuration_settings.load_configuration()
        cfg["character_groups"] = groups
        self.configuration_settings.save_configuration_edit(cfg)

    def _get_grouped_characters(self) -> set:
        groups = self._get_groups()
        grouped = set()
        for members in groups.values():
            grouped.update(members)
        return grouped

    def _open_folder_view(self, group_name: str):
        groups = self._get_groups()
        members = groups.get(group_name,[])

        for widget in self.cards:
            char_name = getattr(widget, 'character_name', None)
            if isinstance(widget, CharacterFolderCard):
                widget.setVisible(False)
            elif isinstance(widget, CharacterCardList):
                widget.setVisible(char_name in members)

        self.update_layout()
        self._show_folder_header(group_name)

    def _show_folder_header(self, group_name: str):
        if hasattr(self, '_folder_header_widget') and self._folder_header_widget:
            try:
                self.ui.gridLayout_9.removeWidget(self._folder_header_widget)
                self._folder_header_widget.deleteLater()
            except RuntimeError:
                pass
            self._folder_header_widget = None

        def _aa_font(family="Inter Tight Medium", size=13, weight=QtGui.QFont.Weight.Normal, bold=False):
            font = QtGui.QFont(family, size, weight)
            font.setBold(bold)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
            return font

        header = QtWidgets.QWidget()
        header.setFixedHeight(45)

        outer = QtWidgets.QVBoxLayout(header)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(content)
        layout.setContentsMargins(24, 0, 20, 0)
        layout.setSpacing(12)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        back_btn = QtWidgets.QPushButton("←")
        back_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedHeight(30)
        back_btn.setFont(_aa_font("Inter Tight Medium", 11))
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.15); border-radius: 15px; padding: 0 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
        """)

        title_lbl = QtWidgets.QLabel(group_name)
        title_lbl.setFont(_aa_font("Inter Tight SemiBold", 15, bold=True))
        title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.95);")

        groups = self._get_groups()
        count_text = (
            f"{len(groups.get(group_name, []))} "
            + self.translations.get("folder_characters_label", "characters").lower()
        )
        count_lbl = QtWidgets.QLabel(count_text)
        count_lbl.setFont(_aa_font("Inter Tight Medium", 12))
        count_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.35); padding-bottom: 1px;")

        edit_btn = QtWidgets.QPushButton(self.translations.get("folder_edit_btn", "Edit"))
        edit_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedHeight(28)
        edit_btn.setFont(_aa_font("Inter Tight Medium", 12))
        edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 7px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.16);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.5);
            }
        """)

        back_btn.clicked.connect(self._close_folder_view)
        edit_btn.clicked.connect(lambda: self._open_folder_editor(group_name))

        layout.addWidget(back_btn)
        layout.addWidget(title_lbl)
        layout.addWidget(count_lbl)
        layout.addStretch()
        layout.addWidget(edit_btn)

        line = QtWidgets.QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.04); border: none;")

        outer.addWidget(content, stretch=1)
        outer.addWidget(line)

        self._folder_header_widget = header

        main_layout = self.ui.gridLayout_9
        main_layout.removeWidget(self.ui.scrollArea_characters_list)
        main_layout.addWidget(header, 1, 0, 1, 1)
        main_layout.addWidget(self.ui.scrollArea_characters_list, 2, 0, 1, 1)

    def _close_folder_view(self):
        if hasattr(self, '_folder_header_widget') and self._folder_header_widget:
            try:
                self.ui.gridLayout_9.removeWidget(self._folder_header_widget)
                self._folder_header_widget.deleteLater()
            except RuntimeError:
                pass
            self._folder_header_widget = None

            self.ui.gridLayout_9.removeWidget(self.ui.scrollArea_characters_list)
            self.ui.gridLayout_9.addWidget(self.ui.scrollArea_characters_list, 1, 0, 1, 1)

        grouped_characters = self._get_grouped_characters()

        for widget in self.cards:
            if isinstance(widget, CharacterFolderCard):
                widget.setVisible(True)
            elif isinstance(widget, CharacterCardList):
                char_name = getattr(widget, 'character_name', None)
                widget.setVisible(char_name not in grouped_characters)

        self.update_layout()
        
        search_text = self.ui.lineEdit_search_character_menu.text()
        if search_text:
            self.filter_characters(search_text)

    def _open_folder_editor(self, group_name: str):
        groups = self._get_groups()
        all_chars = list(self.configuration_characters.load_configuration().get("character_list", {}).keys())

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("folder_editor_title", "Edit Folder") + f" — {group_name}")
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setFixedSize(480, 580)

        def _aa_font(family="Inter Tight Medium", size=13, weight=QtGui.QFont.Weight.Normal, bold=False):
            font = QtGui.QFont(family, size, weight)
            font.setBold(bold)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
            return font

        dialog.setStyleSheet("""
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0c0c10, stop:0.5 #111118, stop:1 #16161d); 
            }
            QLabel { 
                color: rgba(255, 255, 255, 0.7); 
                font-size: 13px; 
                background: transparent;
            }
            QLabel#titleLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#subtitleLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 12px;
                margin-bottom: 4px;
            }
            QLabel#counterLabel {
                color: rgba(255, 255, 255, 0.35);
                font-size: 11px;
                padding-left: 4px;
            }
            QLabel#emptyLabel {
                color: rgba(255, 255, 255, 0.2);
                font-size: 13px;
                padding: 40px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 0.035); 
                color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.07); 
                border-radius: 10px; 
                padding: 14px 16px; 
                font-size: 14px;
                selection-background-color: rgba(255, 255, 255, 0.2);
            }
            QLineEdit:focus { 
                border: 1px solid rgba(255, 255, 255, 0.25); 
                background: rgba(255, 255, 255, 0.05); 
            }
            QLineEdit:hover {
                background: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QListWidget {
                background: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px; 
                color: rgba(255, 255, 255, 0.85); 
                font-size: 13px; 
                padding: 6px; 
                outline: none;
            }
            QListWidget::item { 
                padding: 0px; 
                border-radius: 8px; 
                margin-bottom: 3px; 
                border: 1px solid transparent;
                min-height: 44px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QListWidget::item:selected { 
                background: rgba(255, 255, 255, 0.08); 
                color: white; 
                border: 1px solid rgba(255, 255, 255, 0.12); 
            }
            QListWidget::item:selected:hover {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QScrollBar:vertical { 
                background: transparent; 
                width: 5px; 
                margin: 6px 4px 6px 0px;
            }
            QScrollBar::handle:vertical { 
                background: rgba(255, 255, 255, 0.1); 
                border-radius: 3px; 
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.18);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.14), stop:1 rgba(255, 255, 255, 0.1)); 
                color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.18); 
                border-radius: 10px;
                padding: 7px 14px;
                font-size: 13px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.22), stop:1 rgba(255, 255, 255, 0.16)); 
                border: 1px solid rgba(255, 255, 255, 0.28);
                color: white;
            }
            QPushButton:pressed { 
                background: rgba(255, 255, 255, 0.08); 
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
            QPushButton#dangerBtn {
                background: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
            QPushButton#dangerBtn:hover {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
            }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(32, 32, 32, 28)
        main_layout.setSpacing(16)

        title = QLabel(self.translations.get("folder_editor_title", "Edit Folder"))
        title.setObjectName("titleLabel")
        title.setFont(_aa_font("Inter Tight SemiBold", 20, bold=True))
        main_layout.addWidget(title)

        subtitle = QLabel(group_name)
        subtitle.setObjectName("subtitleLabel")
        subtitle.setFont(_aa_font("Inter Tight Medium", 12))
        main_layout.addWidget(subtitle)

        main_layout.addSpacing(8)

        name_lbl = QLabel(self.translations.get("folder_name_label", "Folder Name"))
        name_lbl.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))
        main_layout.addWidget(name_lbl)

        name_edit = QtWidgets.QLineEdit(group_name)
        name_edit.setFont(_aa_font("Inter Tight Medium", 14))
        main_layout.addWidget(name_edit)

        chars_header = QtWidgets.QHBoxLayout()
        members_lbl = QLabel(self.translations.get("folder_members_label", "Characters inside"))
        members_lbl.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))
        chars_header.addWidget(members_lbl)

        counter_label = QLabel("0")
        counter_label.setObjectName("counterLabel")
        counter_label.setFont(_aa_font("Inter Tight Medium", 11))
        chars_header.addStretch()
        chars_header.addWidget(counter_label)
        main_layout.addLayout(chars_header)

        members_list = QtWidgets.QListWidget()
        members_list.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.InternalMove)
        members_list.setFont(_aa_font("Inter Tight Medium", 13))
        members_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        members_list.verticalScrollBar().setSingleStep(24)
        members_list.setMinimumHeight(180)
        members_list.setSpacing(2)
        members_list.setToolTip(self.translations.get("folder_drag_tip", "Drag items to reorder"))
        main_layout.addWidget(members_list)

        empty_label = QLabel(self.translations.get("folder_empty", "No characters in this folder"))
        empty_label.setObjectName("emptyLabel")
        empty_label.setFont(_aa_font("Inter Tight Medium", 13))
        empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        empty_label.hide()
        main_layout.addWidget(empty_label)

        def update_counter():
            count = members_list.count()
            folder_characters_label = self.translations.get("folder_characters_label", "characters")
            counter_label.setText(f"{count} {folder_characters_label}")
            if count == 0:
                members_list.hide()
                empty_label.show()
            else:
                members_list.show()
                empty_label.hide()

        def _refresh_members():
            members_list.clear()
            for ch in groups.get(group_name, []):
                item = QtWidgets.QListWidgetItem(ch)
                item.setFont(_aa_font("Inter Tight Medium", 13))
                members_list.addItem(item)
            update_counter()

        _refresh_members()

        add_remove_row = QHBoxLayout()
        add_remove_row.setSpacing(10)

        btn_add = QPushButton("＋ " + self.translations.get("folder_add_char", "Add"))
        btn_add.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_add.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))

        btn_rem = QPushButton("− " + self.translations.get("folder_remove_char", "Remove"))
        btn_rem.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_rem.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))

        add_remove_row.addWidget(btn_add)
        add_remove_row.addWidget(btn_rem)
        add_remove_row.addStretch()
        main_layout.addLayout(add_remove_row)

        def _add_char():
            current_members = [members_list.item(i).text() for i in range(members_list.count())]
            available = [c for c in all_chars if c not in current_members]
            if not available:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_folder_title", "Folder Management"),
                    text=self.translations.get("folder_no_chars_available", "No more characters available"),
                    msg_type="info"
                )
                return
            
            char_name, ok = QInputDialog.getItem(
                dialog,
                self.translations.get("folder_add_char_title", "Add Character"),
                self.translations.get("folder_add_char_prompt", "Select character:"),
                available, 0, False
            )
            if ok and char_name:
                current_members.append(char_name)
                groups[group_name] = current_members
                _refresh_members()

        def _remove_char():
            item = members_list.currentItem()
            if item:
                char_name = item.text()
                members = groups.get(group_name, [])
                if char_name in members:
                    members.remove(char_name)
                    groups[group_name] = members
                _refresh_members()

        btn_add.clicked.connect(_add_char)
        btn_rem.clicked.connect(_remove_char)

        main_layout.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        btn_delete_folder = QPushButton(self.translations.get("folder_delete_btn", "Delete Folder"))
        btn_delete_folder.setObjectName("dangerBtn")
        btn_delete_folder.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_delete_folder.setFont(_aa_font("Inter Tight Medium", 13))

        btn_save = QPushButton(self.translations.get("folder_save_btn", "Save Changes"))
        btn_save.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_save.setFont(_aa_font("Inter Tight SemiBold", 14, bold=True))

        bottom_row.addWidget(btn_delete_folder)
        bottom_row.addStretch()
        bottom_row.addWidget(btn_save)
        main_layout.addLayout(bottom_row)

        def _save():
            new_name = name_edit.text().strip()
            if not new_name:
                return

            new_members = [members_list.item(i).text() for i in range(members_list.count())]
            groups[group_name] = new_members

            if new_name != group_name and new_name not in groups:
                groups[new_name] = groups.pop(group_name)

            self._save_groups(groups)
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_folder_title", "Folder Management"),
                text=self.translations.get("folder_saved", "Folder saved successfully"),
                msg_type="success"
            )
            dialog.accept()
            asyncio.create_task(self.set_main_tab())

        def _delete_folder():
            from app.gui.soul_stage_page import RPGConfirmDialog
            
            title = self.translations.get("folder_delete_confirm_title", "Delete Folder")
            message = self.translations.get("folder_delete_confirm_msg", "Delete this folder?")
            
            detail_base = self.translations.get("folder_delete_detail", "Characters will return to the main list.")
            detail = f"'{group_name}' · {detail_base}"
            
            confirm_btn = self.translations.get("delete", "Delete")

            confirmed = RPGConfirmDialog.ask(
                title=title,
                message=message,
                confirm_text=confirm_btn,
                detail=detail,
                parent=dialog 
            )

            if confirmed:
                groups.pop(group_name, None)
                self._save_groups(groups)
                dialog.accept()
                self._close_folder_view()
                asyncio.create_task(self.set_main_tab())

        btn_save.clicked.connect(_save)
        btn_delete_folder.clicked.connect(_delete_folder)
        dialog.exec()

    def _open_create_folder_dialog(self):
        all_chars = list(self.configuration_characters.load_configuration().get("character_list", {}).keys())
        groups = self._get_groups()

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("folder_create_title", "Create New Folder"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setFixedSize(480, 580)
        
        def _aa_font(family="Inter Tight Medium", size=13, weight=QtGui.QFont.Weight.Normal, bold=False):
            font = QtGui.QFont(family, size, weight)
            font.setBold(bold)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
            return font

        dialog.setStyleSheet("""
            QDialog { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 #0c0c10, stop:0.5 #111118, stop:1 #16161d); 
            }
            QLabel { 
                color: rgba(255, 255, 255, 0.7); 
                font-size: 13px; 
                background: transparent;
            }
            QLabel#titleLabel {
                color: rgba(255, 255, 255, 0.95);
                font-size: 20px;
                font-weight: bold;
            }
            QLabel#subtitleLabel {
                color: rgba(255, 255, 255, 0.4);
                font-size: 12px;
                margin-bottom: 4px;
            }
            QLabel#counterLabel {
                color: rgba(255, 255, 255, 0.35);
                font-size: 11px;
                padding-left: 4px;
            }
            QLineEdit {
                background: rgba(255, 255, 255, 0.035); 
                color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.07); 
                border-radius: 10px; 
                padding: 14px 16px; 
                font-size: 14px;
                selection-background-color: rgba(255, 255, 255, 0.2);
            }
            QLineEdit:focus { 
                border: 1px solid rgba(255, 255, 255, 0.25); 
                background: rgba(255, 255, 255, 0.05); 
            }
            QLineEdit:hover {
                background: rgba(255, 255, 255, 0.045);
                border: 1px solid rgba(255, 255, 255, 0.12);
            }
            QListWidget {
                background: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px; 
                color: rgba(255, 255, 255, 0.85); 
                font-size: 13px; 
                padding: 6px; 
                outline: none;
            }
            QListWidget::item { 
                padding: 0px; 
                border-radius: 8px; 
                margin-bottom: 3px; 
                border: 1px solid transparent;
                min-height: 44px;
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QListWidget::item:selected { 
                background: rgba(255, 255, 255, 0.08); 
                color: white; 
                border: 1px solid rgba(255, 255, 255, 0.12); 
            }
            QListWidget::item:selected:hover {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QScrollBar:vertical { 
                background: transparent; 
                width: 5px; 
                margin: 6px 4px 6px 0px;
            }
            QScrollBar::handle:vertical { 
                background: rgba(255, 255, 255, 0.1); 
                border-radius: 3px; 
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.18);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.14), stop:1 rgba(255, 255, 255, 0.1)); 
                color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.18); 
                border-radius: 10px;
                padding: 14px; 
                font-size: 14px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.22), stop:1 rgba(255, 255, 255, 0.16)); 
                border: 1px solid rgba(255, 255, 255, 0.28);
                color: white;
            }
            QPushButton:pressed { 
                background: rgba(255, 255, 255, 0.08); 
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.04);
                color: rgba(255, 255, 255, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(32, 32, 32, 28)
        layout.setSpacing(16)

        title = QLabel(self.translations.get("folder_create_title", "Create New Folder"))
        title.setObjectName("titleLabel")
        title.setFont(_aa_font("Inter Tight SemiBold", 20, bold=True))
        layout.addWidget(title)

        subtitle = QLabel(self.translations.get("folder_create_subtitle", "Organize your characters into a custom folder"))
        subtitle.setObjectName("subtitleLabel")
        subtitle.setFont(_aa_font("Inter Tight Medium", 12))
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        name_label = QLabel(self.translations.get("folder_name_label", "Folder Name"))
        name_label.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))
        layout.addWidget(name_label)

        name_edit = QtWidgets.QLineEdit()
        name_edit.setPlaceholderText(self.translations.get("folder_name_placeholder", "e.g. Fantasy RPG"))
        name_edit.setFont(_aa_font("Inter Tight Medium", 14))
        layout.addWidget(name_edit)

        chars_header = QtWidgets.QHBoxLayout()
        chars_label = QLabel(self.translations.get("folder_select_chars_label", "Select Characters"))
        chars_label.setFont(_aa_font("Inter Tight SemiBold", 13, bold=True))
        chars_header.addWidget(chars_label)
        
        selected_label = self.translations.get("selected_label", "selected")
        counter_label = QLabel(f"0 {selected_label}")
        counter_label.setObjectName("counterLabel")
        counter_label.setFont(_aa_font("Inter Tight Medium", 11))
        chars_header.addStretch()
        chars_header.addWidget(counter_label)
        layout.addLayout(chars_header)

        chars_list = QtWidgets.QListWidget()
        chars_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        chars_list.setFont(_aa_font("Inter Tight Medium", 13))
        chars_list.setMinimumHeight(200)
        chars_list.setSpacing(2)
        chars_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        chars_list.verticalScrollBar().setSingleStep(24)
        
        all_char_items = []
        
        for ch in all_chars:
            item = QtWidgets.QListWidgetItem()
            item.setText(ch)
            item.setFont(_aa_font("Inter Tight Medium", 13))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, ch)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter)
            chars_list.addItem(item)
            all_char_items.append(item)

        layout.addWidget(chars_list, stretch=1)

        hint_label = QLabel(self.translations.get("folder_select_hint", "Click to select or use checkboxes"))
        hint_label.setFont(_aa_font("Inter Tight Medium", 11))
        hint_label.setStyleSheet("color: rgba(255, 255, 255, 0.25); margin-top: 2px;")
        layout.addWidget(hint_label)

        layout.addSpacing(6)

        btn_create = QPushButton(self.translations.get("folder_create_btn", "Create Folder"))
        btn_create.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn_create.setFont(_aa_font("Inter Tight SemiBold", 14, bold=True))
        layout.addWidget(btn_create)

        def update_counter():
            count = sum(1 for item in all_char_items if item.checkState() == QtCore.Qt.CheckState.Checked)
            selected_label = self.translations.get("selected_label", "selected")
            counter_label.setText(f"{count} {selected_label}" if count != 1 else f"1 {selected_label}")
            if count > 0:
                folder_create_btn_with_count = self.translations.get("folder_create_btn_with_count", f"Create Folder ({count})")
                btn_create.setText(folder_create_btn_with_count.format(group_count=count))
            else:
                btn_create.setText(self.translations.get("folder_create_btn", "Create Folder"))

        def on_item_changed(item):
            update_counter()

        def on_item_clicked(item):
            if item.checkState() == QtCore.Qt.CheckState.Checked:
                item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            else:
                item.setCheckState(QtCore.Qt.CheckState.Checked)
            update_counter()

        chars_list.itemChanged.connect(on_item_changed)
        chars_list.itemClicked.connect(on_item_clicked)

        def _create():
            new_name = name_edit.text().strip()
            if not new_name:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_folder_error_title", "Folder Error"),
                    text=self.translations.get("folder_name_empty", "Folder name cannot be empty"),
                    msg_type="error"
                )
                return
            if new_name in groups:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_folder_error_title", "Folder Error"),
                    text=self.translations.get("folder_name_exists", "A folder with this name already exists"),
                    msg_type="error"
                )
                return

            selected_chars = [
                item.data(QtCore.Qt.ItemDataRole.UserRole) 
                for item in all_char_items 
                if item.checkState() == QtCore.Qt.CheckState.Checked and not item.isHidden()
            ]
            groups[new_name] = selected_chars
            self._save_groups(groups)
            dialog.accept()
            asyncio.create_task(self.set_main_tab())

        btn_create.clicked.connect(_create)
        name_edit.returnPressed.connect(_create)
        
        update_counter()
        dialog.exec()
    ### SETUP MAIN TAB AND CREATE CHARACTER ============================================================

    ### SETUP COMBOBOXES AND OTHER =======================================================================
    def on_comboBox_conversation_method_changed(self, text):
        self.configuration_settings.update_main_setting("conversation_method", text)
        self.update_local_llm_settings_visibility(text)
        self._reset_model_test_result()
        self.refresh_provider_verification_status()
        if text == "OpenRouter":
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write API value"))
            self.initialize_openrouter_models()
        elif text == "Open AI":
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_base_api", "Write API value (Optional)"))
        else:
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write API value"))

    _MODEL_SETTINGS = {
        "Open AI": "openai_model", "OpenRouter": "openrouter_model",
        "Mistral AI": "mistral_model_endpoint", "Anthropic": "anthropic_model",
        "Google Gemini": "gemini_model", "DeepSeek": "deepseek_model",
        "Grok": "grok_model", "Qwen": "qwen_model", "Z.AI": "zai_model",
    }

    def _provider_model(self, provider):
        setting = self._MODEL_SETTINGS.get(provider)
        return self.configuration_settings.get_main_setting(setting) if setting else None

    def _verified_providers(self):
        verified = self.configuration_settings.get_main_setting("verified_provider_models") or {}
        return verified if isinstance(verified, dict) else {}

    def _is_provider_verified(self, provider):
        verified = self._verified_providers()
        return provider in verified and verified[provider] == self._provider_model(provider)

    def _set_provider_verified(self, provider):
        verified = self._verified_providers()
        verified[provider] = self._provider_model(provider)
        self.configuration_settings.update_main_setting("verified_provider_models", verified)

    def _clear_provider_verification(self, provider):
        verified = self._verified_providers()
        if provider in verified:
            del verified[provider]
            self.configuration_settings.update_main_setting("verified_provider_models", verified)

    def _reset_model_test_result(self):
        self.ui.label_model_test_result.clear()
        self.ui.label_model_test_result.setStyleSheet("color: rgba(255, 255, 255, 0.45);")
        if self._model_test_task and not self._model_test_task.done():
            self._model_test_task.cancel()

    def refresh_provider_verification_status(self):
        if not hasattr(self.ui, "label_provider_verification"):
            return
        provider = self.ui.comboBox_conversation_method.currentText()
        if provider == "Local LLM":
            local_model = self.configuration_settings.get_main_setting("local_llm")
            verified = bool(local_model and os.path.exists(local_model))
            text = "Local model is available" if verified else "No local model is available."
        else:
            verified = self._is_provider_verified(provider)
            text = "✓ Confirmed by model check" if verified else "Not confirmed. Check the selected model to enable it for characters."
        self.ui.label_provider_verification.setStyleSheet(
            "color: #4ADE80;" if verified else "color: rgba(255, 255, 255, 0.45);"
        )
        self.ui.label_provider_verification.setText(text)
        self.update_conversation_provider_checks()

    def update_conversation_provider_checks(self):
        combo = self.ui.comboBox_conversation_method
        ready_icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
        )
        for index in range(combo.count()):
            provider = combo.itemText(index)
            if provider == "Local LLM":
                model_path = self.configuration_settings.get_main_setting("local_llm")
                ready = bool(model_path and os.path.exists(model_path))
            else:
                ready = self._is_provider_verified(provider)
            combo.setItemIcon(index, ready_icon if ready else QtGui.QIcon())

    def _save_model_setting(self, setting, value, provider):
        if self.configuration_settings.get_main_setting(setting) != value:
            self.configuration_settings.update_main_setting(setting, value)
            self._clear_provider_verification(provider)
            self._reset_model_test_result()
            self.refresh_provider_verification_status()

    def update_local_llm_settings_visibility(self, conversation_method):
        is_local = conversation_method == "Local LLM"
        self.ui.card_llm_hw.setVisible(is_local)
        self.ui.card_llm_adv.setVisible(is_local)
        self.ui.chat_template_label.setVisible(is_local)
        self.ui.comboBox_chat_template.setVisible(is_local)

    def load_audio_devices(self):
        input_device_index = self.configuration_settings.get_main_setting("input_device")
        output_device_index = self.configuration_settings.get_main_setting("output_device_combo_index")

        self.ui.comboBox_input_devices.clear()
        self.ui.comboBox_output_devices.clear()
        self.input_device_list = []
        self.output_device_list = []

        devices = sd.query_devices()
        host_apis = sd.query_hostapis()

        for dev in devices:
            if dev["max_input_channels"] > 0:
                host_api_name = host_apis[dev["hostapi"]]["name"]
                full_name = f"{dev['name']} ({host_api_name})"
                self.ui.comboBox_input_devices.addItem(full_name)
                self.input_device_list.append(dev["index"])

        self.set_combobox_to_device(self.ui.comboBox_input_devices, input_device_index)

        if input_device_index >= 0 and input_device_index < self.ui.comboBox_input_devices.count():
            real_input_index = self.input_device_list[input_device_index]
            self.configuration_settings.update_main_setting("input_device_real_index", real_input_index)
        elif self.input_device_list:
             self.configuration_settings.update_main_setting("input_device_real_index", self.input_device_list[0])

        for dev in devices:
            if dev["max_output_channels"] > 0:
                host_api_name = host_apis[dev["hostapi"]]["name"]
                full_name = f"{dev['name']} ({host_api_name})"
                self.ui.comboBox_output_devices.addItem(full_name)
                self.output_device_list.append(dev["index"])

        if output_device_index >= 0 and output_device_index < self.ui.comboBox_output_devices.count():
            self.ui.comboBox_output_devices.setCurrentIndex(output_device_index)
            real_index = self.output_device_list[output_device_index]
            self.configuration_settings.update_main_setting("output_device_real_index", real_index)
        else:
            self.ui.comboBox_output_devices.setCurrentIndex(0)
            real_index = self.output_device_list[0] if self.output_device_list else None
            self.configuration_settings.update_main_setting("output_device_real_index", real_index)
            self.configuration_settings.update_main_setting("output_device_combo_index", 0)

    def set_combobox_to_device(self, combobox, index):
        if index != -1 and index < combobox.count():
            combobox.setCurrentIndex(index)

    def on_comboBox_input_devices_changed(self, index):
        self.configuration_settings.update_main_setting("input_device", index)
        if index >= 0 and index < len(self.input_device_list):
            real_index = self.input_device_list[index]
            self.configuration_settings.update_main_setting("input_device_real_index", real_index)

    def on_comboBox_output_devices_changed(self, index):
        if index >= 0 and index < len(self.output_device_list):
            real_index = self.output_device_list[index]
            self.configuration_settings.update_main_setting("output_device_combo_index", index)
            self.configuration_settings.update_main_setting("output_device_real_index", real_index)
        else:
            if self.output_device_list:
                real_index = self.output_device_list[0]
                self.configuration_settings.update_main_setting("output_device_combo_index", 0)
                self.configuration_settings.update_main_setting("output_device_real_index", real_index)
            else:
                real_index = None
                self.configuration_settings.update_main_setting("output_device_real_index", None)

        if hasattr(self, 'ambient_player'):
            self.ambient_player.set_device(real_index)
    
    async def fetch_openrouter_api_models(self):
        def request_models():
            with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=15) as response:
                return json.load(response)

        data = await asyncio.to_thread(request_models)
        models = []
        for model in data.get("data", []):
            model_id = model.get("id")
            if model_id:
                models.append({
                    "id": model_id,
                    "name": model.get("name") or model_id,
                    "description": model.get("description") or ""
                })

        if not models:
            raise ValueError("OpenRouter returned an empty model list")

        return models
        
    def initialize_openrouter_models(self):
        if self._openrouter_models_task and not self._openrouter_models_task.done():
            return

        self._openrouter_models_task = asyncio.create_task(self._load_and_populate_open_models())

    async def _load_and_populate_open_models(self):
        combo = self.ui.comboBox_openrouter_models
        search = self.ui.lineEdit_search_openrouter_models
        refresh_button = self.ui.pushButton_reload_openrouter_models

        combo.setEnabled(False)
        search.setEnabled(False)
        refresh_button.setEnabled(False)
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self.translations.get("openrouter_models_loading", "Loading models..."))
        combo.blockSignals(False)

        try:
            self.models = await self.fetch_openrouter_api_models()
            self.refresh_character_model_options()
            self.filtered_models = [
                model for model in self.models
                if search.text().lower() in model["name"].lower()
            ]

            combo.blockSignals(True)
            self.load_openrouter_models()
            combo.blockSignals(False)

            current_active_index = self.ui.comboBox_openrouter_models.currentIndex()
            self.on_comboBox_openrouter_models_changed(max(0, current_active_index))
        except Exception:
            logger.exception("Failed to load OpenRouter models")
            self.filtered_models = [
                model for model in self.models
                if search.text().lower() in model["name"].lower()
            ]

            combo.blockSignals(True)
            self.load_openrouter_models()
            if not self.models:
                combo.addItem(self.translations.get(
                    "openrouter_models_load_error",
                    "Couldn't load models. Click Refresh to try again."
                ))
            combo.blockSignals(False)

            sow_toast(
                parent=self.main_window,
                title="OpenRouter",
                text=self.translations.get(
                    "openrouter_models_load_error",
                    "Couldn't load models. Click Refresh to try again."
                ),
                msg_type="error"
            )
        finally:
            combo.setEnabled(bool(self.models))
            search.setEnabled(bool(self.models))
            refresh_button.setEnabled(True)

    def filter_models(self, text):
        text = text.lower()
        self.filtered_models = [model for model in self.models if text in model["name"].lower()]
        self.load_openrouter_models()

    def load_openrouter_models(self):
        openrouter_model_id = self.configuration_settings.get_main_setting("openrouter_model")

        self.ui.comboBox_openrouter_models.clear()

        for model in self.filtered_models:
            self.ui.comboBox_openrouter_models.addItem(model["name"], userData=model["id"])
            index = self.ui.comboBox_openrouter_models.findText(model["name"])
            self.ui.comboBox_openrouter_models.setItemData(index, model["description"], Qt.ItemDataRole.ToolTipRole)

        self.set_combobox_to_model(self.ui.comboBox_openrouter_models, openrouter_model_id)

    def set_combobox_to_model(self, combobox, model_id):
        for i in range(combobox.count()):
            if combobox.itemData(i) == model_id:
                combobox.setCurrentIndex(i)
                break

    def on_comboBox_openrouter_models_changed(self, index):
        selected_model_id = self.ui.comboBox_openrouter_models.itemData(index)
        if selected_model_id:
            self._save_model_setting("openrouter_model", selected_model_id, "OpenRouter")

    def on_comboBox_translator_changed(self, index):
        self.configuration_settings.update_main_setting("translator", index)
        translator = self.configuration_settings.get_main_setting("translator")
        if translator == 0:
            self.ui.target_language_translator_label.hide()
            self.ui.comboBox_target_language_translator.hide()
        else:
            self.ui.target_language_translator_label.show()
            self.ui.comboBox_target_language_translator.show()

    def on_comboBox_target_language_translator_changed(self, index):
        self.configuration_settings.update_main_setting("target_language", index)

    def on_comboBox_live2d_mode_changed(self, index):
        self.configuration_settings.update_main_setting("live2d_mode", index)

    def on_comboBox_model_fps_changed(self, index):
        self.configuration_settings.update_main_setting("model_fps", index)

    def on_comboBox_llm_devices_changed(self, index):
        self.configuration_settings.update_main_setting("llm_device", index)
        llm_device = self.configuration_settings.get_main_setting("llm_device")
        if llm_device == 0:
            self.ui.checkBox_enable_flash_attention.hide()
            self.ui.comboBox_llm_gpu_devices.hide()
        else:
            self.ui.checkBox_enable_flash_attention.show()
            self.ui.comboBox_llm_gpu_devices.show()
    
    def on_comboBox_llm_gpu_devices_changed(self, index):
        self.configuration_settings.update_main_setting("llm_backend", index)

    def on_comboBox_chat_template_changed(self, text):
        self.configuration_settings.update_main_setting("chat_template", text)

    def save_stop_strings_in_real_time(self):
        self.configuration_settings.update_main_setting("stop_strings", self.ui.lineEdit_stop_strings.text())

    def on_checkBox_reasoning_mode_stateChanged(self):
        is_checked = self.ui.checkBox_reasoning_mode.isChecked()
        self.configuration_settings.update_main_setting("reasoning_mode", is_checked)

    def on_comboBox_model_background_changed(self, index):
        self.configuration_settings.update_main_setting("model_background_type", index)
        if index == 0:
            self.ui.pushButton_reload_bg_image.hide()
            self.ui.label_bg_color.show()
            self.ui.comboBox_model_bg_color.show()
            self.ui.label_bg_image.hide()
            self.ui.comboBox_model_bg_image.hide()
        elif index == 1:
            self.ui.pushButton_reload_bg_image.show()
            self.ui.label_bg_color.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.label_bg_image.show()
            self.ui.comboBox_model_bg_image.show()

    def on_comboBox_model_bg_color_changed(self, index):
        self.configuration_settings.update_main_setting("model_background_color", index)

    def on_comboBox_model_bg_image_changed(self, index):
        selected_image = self.ui.comboBox_model_bg_image.itemText(index)
        if selected_image == "None":
            image_path = None
        else:
            images_directory = "assets\\backgrounds"
            image_path = os.path.join(images_directory, selected_image)

        self.configuration_settings.update_main_setting("model_background_image", image_path)
    
    def load_background_images_to_comboBox(self):
        self.ui.comboBox_model_bg_image.clear()

        backgrounds_directory = "assets\\backgrounds"
        for filename in os.listdir(backgrounds_directory):
            if filename.endswith((".jpg", ".png", ".jpeg")):
                self.ui.comboBox_model_bg_image.addItem(filename)
        
        saved_background_path = self.configuration_settings.get_main_setting("model_background_image")
        if saved_background_path:
            index = self.ui.comboBox_model_bg_image.findText(os.path.basename(saved_background_path))
            if index >= 0:
                self.ui.comboBox_model_bg_image.setCurrentIndex(index)

        self.on_comboBox_model_bg_image_changed(self.ui.comboBox_model_bg_image.currentIndex())

    def on_comboBox_ambient_mode_changed(self, index):
        if index < 0:
            sound_path = None
        else:
            selected_file = self.ui.comboBox_ambient_mode.itemData(index)
            ambient_directory = "assets\\ambient"
            sound_path = os.path.join(ambient_directory, selected_file)

        self.configuration_settings.update_main_setting("ambient_sound", sound_path)
    
    def load_ambient_sound_to_comboBox(self):
        self.ui.comboBox_ambient_mode.clear()

        ambient_directory = "assets\\ambient"
        for filename in os.listdir(ambient_directory):
            if filename.endswith((".mp3", ".wav")):
                name_without_extension = os.path.splitext(filename)[0]
                self.ui.comboBox_ambient_mode.addItem(name_without_extension, userData=filename)
        
        saved_ambient_path = self.configuration_settings.get_main_setting("ambient_sound")

        if saved_ambient_path:
            saved_filename = os.path.basename(saved_ambient_path)
            for i in range(self.ui.comboBox_ambient_mode.count()):
                if self.ui.comboBox_ambient_mode.itemData(i) == saved_filename:
                    self.ui.comboBox_ambient_mode.setCurrentIndex(i)
                    break
            else:
                self.ui.comboBox_ambient_mode.setCurrentIndex(-1)
        else:
            self.ui.comboBox_ambient_mode.setCurrentIndex(-1)

        self.on_comboBox_ambient_mode_changed(self.ui.comboBox_ambient_mode.currentIndex())

    def on_comboBox_soul_memory_mode_changed(self, index):
        self.configuration_settings.update_main_setting("soul_memory_mode", index)

    def on_spinBox_soul_memory_batch_changed(self, value):
        self.configuration_settings.update_main_setting("soul_memory_batch", value)

    def _trigger_manual_memory(self):
        if not hasattr(self, 'current_active_character') or not self.current_active_character:
            sow_toast(
                parent=self.main_window,
                title="Soul Memory",
                text=self.translations.get("soul_memory_no_chat", "Please open a chat with a character first."),
                msg_type="error"
            )
            return
            
        character_name = self.current_active_character
        
        char_config = self.configuration_characters.load_configuration()
        if "character_list" not in char_config or character_name not in char_config["character_list"]:
            return

        char_data = char_config["character_list"][character_name]
        conversation_method = char_data.get("conversation_method", "Local LLM")
        
        current_chat_id = char_data.get("current_chat", "default")
        chat_content = char_data.get("chats", {}).get(current_chat_id, {}).get("chat_content", {})

        raw_messages = chat_content.values()
        sorted_messages = sorted(raw_messages, key=lambda x: x.get("sequence_number", 0))
        
        context_messages = []
        for msg in sorted_messages:
            current_var_id = msg.get("current_variant_id", "default")
            text_content = ""
            for variant in msg.get("variants", []):
                if isinstance(variant, dict) and variant.get("variant_id") == current_var_id:
                    text_content = variant.get("text", "")
                    break
            
            if not text_content.strip():
                continue
                
            role = "user" if msg.get("is_user") else "assistant"
            context_messages.append({"role": role, "content": text_content})
            
        if not context_messages:
            sow_toast(
                parent=self.main_window,
                title="Soul Memory",
                text=self.translations.get("soul_memory_empty", "Chat history is empty."),
                msg_type="error"
            )
            return
            
        config_user = self.configuration_settings.load_configuration()
        selected_persona = char_data.get("selected_persona", "None")
        user_name = config_user.get("user_data", {}).get("personas", {}).get(selected_persona, {}).get("user_name", "User")
        
        sow_toast(
            parent=self.main_window,
            title="Soul Memory",
            text=self.translations.get("soul_memory_manual_start", "Manual memory update started..."),
            msg_type="success"
        )
        
        try:
            provider = AIFactory.get_provider(conversation_method, char_data.get("model_override"))
            if not provider:
                logger.error(f"Cannot trigger manual memory: Provider '{conversation_method}' not found.")
                return

            asyncio.create_task(
                self.prompt_engine.update_memory_after_response(
                    provider=provider,
                    new_messages=context_messages, 
                    character_name=character_name, 
                    user_name=user_name,
                    force=True
                )
            )
        except Exception as e:
            logger.error(f"Manual memory trigger error: {e}", exc_info=True)

    def on_checkBox_enable_sow_system_stateChanged(self):
        if self.ui.checkBox_enable_sow_system.isChecked():
            model_background_type = self.configuration_settings.get_main_setting("model_background_type")
            ambient_enabled = self.configuration_settings.get_main_setting("ambient")
            self.configuration_settings.update_main_setting("sow_system_status", True)
            
            self.ui.label_live2d_mode.show()
            self.ui.comboBox_live2d_mode.show()
            self.ui.label_model_fps.show()
            self.ui.comboBox_model_fps.show()
            self.ui.label_model_background.show()
            self.ui.comboBox_model_background.show()
            self.ui.checkBox_enable_ambient.show()
            self.ui.checkBox_enable_soul_memory.show()
            self.ui.checkBox_enable_summary.show()
            self.ui.label_summary_interval.show()
            self.ui.spinBox_summary_interval.show()
            
            if self.ui.checkBox_enable_soul_memory.isChecked():
                self.ui.label_soul_memory_mode.show()
                self.ui.comboBox_soul_memory_mode.show()
                self.ui.label_soul_memory_batch.show()
                self.ui.spinBox_soul_memory_batch.show()
            else:
                self.ui.label_soul_memory_mode.hide()
                self.ui.comboBox_soul_memory_mode.hide()
                self.ui.label_soul_memory_batch.hide()
                self.ui.spinBox_soul_memory_batch.hide()

            if ambient_enabled == True:
                self.ui.comboBox_ambient_mode.show()
                self.ui.pushButton_reload_ambient.show()
            else:
                self.ui.comboBox_ambient_mode.hide()
                self.ui.pushButton_reload_ambient.hide()

            if model_background_type == 0:
                self.ui.pushButton_reload_bg_image.hide()
                self.ui.label_bg_color.show()
                self.ui.comboBox_model_bg_color.show()
                self.ui.label_bg_image.hide()
                self.ui.comboBox_model_bg_image.hide()
            elif model_background_type == 1:
                self.ui.pushButton_reload_bg_image.show()
                self.ui.label_bg_color.hide()
                self.ui.comboBox_model_bg_color.hide()
                self.ui.label_bg_image.show()
                self.ui.comboBox_model_bg_image.show()
        else:
            self.configuration_settings.update_main_setting("sow_system_status", False)
            
            self.ui.label_live2d_mode.hide()
            self.ui.comboBox_live2d_mode.hide()
            self.ui.label_model_fps.hide()
            self.ui.comboBox_model_fps.hide()
            self.ui.label_model_background.hide()
            self.ui.comboBox_model_background.hide()
            self.ui.label_bg_color.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.label_bg_image.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.pushButton_reload_bg_image.hide()
            self.ui.checkBox_enable_ambient.hide()
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()
            self.ui.checkBox_enable_soul_memory.hide()
            self.ui.checkBox_enable_summary.hide()
            self.ui.label_summary_interval.hide()
            self.ui.spinBox_summary_interval.hide()
            self.ui.label_soul_memory_mode.hide()
            self.ui.comboBox_soul_memory_mode.hide()
            self.ui.label_soul_memory_batch.hide()
            self.ui.spinBox_soul_memory_batch.hide()

    def on_checkBox_enable_mlock_stateChanged(self):
        if self.ui.checkBox_enable_mlock.isChecked():
            self.configuration_settings.update_main_setting("mlock_status", True)
        else:
            self.configuration_settings.update_main_setting("mlock_status", False)

    def on_checkBox_enable_tool_calling_stateChanged(self):
        if self.ui.checkBox_enable_tool_calling.isChecked():
            self.configuration_settings.update_main_setting("enable_tool_calling", True)
        else:
            self.configuration_settings.update_main_setting("enable_tool_calling", False)
    
    def on_checkBox_enable_mcp_stateChanged(self):
        if self.ui.checkBox_enable_mcp.isChecked():
            self.configuration_settings.update_main_setting("enable_mcp", True)
        else:
            self.configuration_settings.update_main_setting("enable_mcp", False)
    
    def on_checkBox_enable_flash_attention_stateChanged(self):
        if self.ui.checkBox_enable_flash_attention.isChecked():
            self.configuration_settings.update_main_setting("flash_attention_status", True)
        else:
            self.configuration_settings.update_main_setting("flash_attention_status", False)

    def on_checkBox_enable_nsfw_stateChanged(self):
        if self.ui.checkBox_enable_nsfw.isChecked():
            self.configuration_settings.update_main_setting("nsfw_query", True)
        else:
            self.configuration_settings.update_main_setting("nsfw_query", False)

    def on_checkBox_enable_ambient_stateChanged(self):
        if self.ui.checkBox_enable_ambient.isChecked():
            self.configuration_settings.update_main_setting("ambient", True)
            self.ui.comboBox_ambient_mode.show()
            self.ui.pushButton_reload_ambient.show()
        else:
            self.configuration_settings.update_main_setting("ambient", False)
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()
    
    def on_checkBox_enable_soul_memory_stateChanged(self):
        if self.ui.checkBox_enable_soul_memory.isChecked():
            self.configuration_settings.update_main_setting("soul_memory", True)
            self.ui.label_soul_memory_mode.show()
            self.ui.comboBox_soul_memory_mode.show()
            self.ui.label_soul_memory_batch.show()
            self.ui.spinBox_soul_memory_batch.show()
        else:
            self.configuration_settings.update_main_setting("soul_memory", False)
            self.ui.label_soul_memory_mode.hide()
            self.ui.comboBox_soul_memory_mode.hide()
            self.ui.label_soul_memory_batch.hide()
            self.ui.spinBox_soul_memory_batch.hide()
    
    def on_checkBox_enable_advanced_sampling_stateChanged(self):
        if self.ui.checkBox_enable_advanced_sampling.isChecked():
            self.configuration_settings.update_main_setting("adv_sampling", True)
        else:
            self.configuration_settings.update_main_setting("adv_sampling", False)
    
    def on_checkBox_enable_summary_stateChanged(self):
        if self.ui.checkBox_enable_summary.isChecked():
            self.configuration_settings.update_main_setting("auto_summary", True)
        else:
            self.configuration_settings.update_main_setting("auto_summary", False)

    def load_combobox(self):
        """
        Loads the settings to the Combobox's and Checkbox's of the interface from the configuration.
        """
        self.ui.comboBox_conversation_method.setCurrentText(self.configuration_settings.get_main_setting("conversation_method"))
        self.update_local_llm_settings_visibility(self.ui.comboBox_conversation_method.currentText())
        self.ui.comboBox_program_language.setCurrentIndex(self.configuration_settings.get_main_setting("program_language"))
        self.ui.comboBox_input_devices.setCurrentIndex(self.configuration_settings.get_main_setting("input_device"))
        self.ui.comboBox_output_devices.setCurrentIndex(self.configuration_settings.get_main_setting("output_device_combo_index"))
        self.ui.comboBox_translator.setCurrentIndex(self.configuration_settings.get_main_setting("translator"))
        self.ui.comboBox_target_language_translator.setCurrentIndex(self.configuration_settings.get_main_setting("target_language"))
        self.ui.comboBox_live2d_mode.setCurrentIndex(self.configuration_settings.get_main_setting("live2d_mode"))
        self.ui.comboBox_model_fps.setCurrentIndex(self.configuration_settings.get_main_setting("model_fps"))
        self.ui.comboBox_model_background.setCurrentIndex(self.configuration_settings.get_main_setting("model_background_type"))
        self.ui.comboBox_model_bg_color.setCurrentIndex(self.configuration_settings.get_main_setting("model_background_color"))
        self.ui.comboBox_model_bg_image.setCurrentText(self.configuration_settings.get_main_setting("model_background_image"))
        self.ui.comboBox_ambient_mode.setCurrentText(self.configuration_settings.get_main_setting("ambient_sound"))
        self.ui.comboBox_llm_devices.setCurrentIndex(self.configuration_settings.get_main_setting("llm_device"))
        self.ui.comboBox_llm_gpu_devices.setCurrentIndex(self.configuration_settings.get_main_setting("llm_backend"))
        chat_tpl = self.configuration_settings.get_main_setting("chat_template") or "Auto"
        self.ui.comboBox_chat_template.setCurrentText(chat_tpl)
        kv_cache = self.configuration_settings.get_main_setting("kv_cache_type") or "f16"
        kv_mapping = {"f16": 0, "q8_0": 1, "q4_1": 2, "q4_0": 3}
        self.ui.comboBox_kv_cache.setCurrentIndex(kv_mapping.get(kv_cache, 0))
        stop_str = self.configuration_settings.get_main_setting("stop_strings") or ""
        self.ui.lineEdit_stop_strings.setText(stop_str)
        reason_mode = self.configuration_settings.get_main_setting("reasoning_mode") or False
        self.ui.checkBox_reasoning_mode.setChecked(reason_mode)

        adv_sampling = self.configuration_settings.get_main_setting("adv_sampling")
        if adv_sampling == False:
            self.ui.checkBox_enable_advanced_sampling.setChecked(False)
        else:
            self.ui.checkBox_enable_advanced_sampling.setChecked(True)

        llm_device = self.configuration_settings.get_main_setting("llm_device")
        if llm_device == 0:
            self.ui.comboBox_llm_gpu_devices.hide()
        else:
            self.ui.comboBox_llm_gpu_devices.show()

        translator = self.configuration_settings.get_main_setting("translator")
        if translator == 0:
            self.ui.target_language_translator_label.hide()
            self.ui.comboBox_target_language_translator.hide()
        else:
            self.ui.target_language_translator_label.show()
            self.ui.comboBox_target_language_translator.show()

        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        if model_background_type == 0:
            self.ui.pushButton_reload_bg_image.hide()
        elif model_background_type == 1:
            self.ui.pushButton_reload_bg_image.show()

        sow_state = self.configuration_settings.get_main_setting("sow_system_status")
        if sow_state == False:
            self.ui.checkBox_enable_sow_system.setChecked(False)
            self.ui.label_live2d_mode.hide()
            self.ui.comboBox_live2d_mode.hide()
            self.ui.label_model_fps.hide()
            self.ui.comboBox_model_fps.hide()
            self.ui.label_model_background.hide()
            self.ui.comboBox_model_background.hide()
            self.ui.pushButton_reload_bg_image.hide()
            self.ui.checkBox_enable_ambient.hide()
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()
            self.ui.label_bg_color.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.label_bg_image.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.checkBox_enable_soul_memory.hide()
            self.ui.checkBox_enable_summary.hide()
            self.ui.label_summary_interval.hide()
            self.ui.spinBox_summary_interval.hide()
            self.ui.label_soul_memory_mode.hide()
            self.ui.comboBox_soul_memory_mode.hide()
            self.ui.label_soul_memory_batch.hide()
            self.ui.spinBox_soul_memory_batch.hide()
        else:
            self.ui.checkBox_enable_sow_system.setChecked(True)
            self.ui.label_live2d_mode.show()
            self.ui.comboBox_live2d_mode.show()
            self.ui.label_model_fps.show()
            self.ui.comboBox_model_fps.show()
            self.ui.label_model_background.show()
            self.ui.comboBox_model_background.show()
            self.ui.checkBox_enable_ambient.show()
            self.ui.comboBox_ambient_mode.show()
            self.ui.pushButton_reload_ambient.show()
            self.ui.checkBox_enable_soul_memory.show()
            self.ui.checkBox_enable_summary.show()
            self.ui.label_summary_interval.show()
            self.ui.spinBox_summary_interval.show()
            self.ui.label_soul_memory_mode.show()
            self.ui.comboBox_soul_memory_mode.show()
            self.ui.label_soul_memory_batch.show()
            self.ui.spinBox_soul_memory_batch.show()

            if model_background_type == 0:
                self.ui.pushButton_reload_bg_image.hide()
                self.ui.label_bg_color.show()
                self.ui.comboBox_model_bg_color.show()
                self.ui.label_bg_image.hide()
                self.ui.comboBox_model_bg_image.hide()
            elif model_background_type == 1:
                self.ui.pushButton_reload_bg_image.show()
                self.ui.label_bg_color.hide()
                self.ui.comboBox_model_bg_color.hide()
                self.ui.label_bg_image.show()
                self.ui.comboBox_model_bg_image.show()

        ambient_state = self.configuration_settings.get_main_setting("ambient")
        if ambient_state == False:
            self.ui.checkBox_enable_ambient.setChecked(False)
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()
        else:
            self.ui.checkBox_enable_ambient.setChecked(True)
            self.ui.comboBox_ambient_mode.show()
            self.ui.pushButton_reload_ambient.show()
        
        soul_memory_state = self.configuration_settings.get_main_setting("soul_memory")
        if soul_memory_state == False:
            self.ui.checkBox_enable_soul_memory.setChecked(False)
            self.ui.label_soul_memory_mode.hide()
            self.ui.comboBox_soul_memory_mode.hide()
            self.ui.label_soul_memory_batch.hide()
            self.ui.spinBox_soul_memory_batch.hide()
        else:
            self.ui.checkBox_enable_soul_memory.setChecked(True)
            self.ui.label_soul_memory_mode.show()
            self.ui.comboBox_soul_memory_mode.show()
            self.ui.label_soul_memory_batch.show()
            self.ui.spinBox_soul_memory_batch.show()

        soul_memory_mode = self.configuration_settings.get_main_setting("soul_memory_mode")
        if soul_memory_mode is not None and 0 <= soul_memory_mode <= 3:
            self.ui.comboBox_soul_memory_mode.setCurrentIndex(soul_memory_mode)
        else:
            self.ui.comboBox_soul_memory_mode.setCurrentIndex(0)

        soul_memory_batch = self.configuration_settings.get_main_setting("soul_memory_batch")
        if soul_memory_batch is not None:
            self.ui.spinBox_soul_memory_batch.setValue(soul_memory_batch)
        else:
            self.ui.spinBox_soul_memory_batch.setValue(4)

        self.ui.comboBox_soul_memory_mode.currentIndexChanged.connect(self.on_comboBox_soul_memory_mode_changed)
        self.ui.spinBox_soul_memory_batch.valueChanged.connect(self.on_spinBox_soul_memory_batch_changed)

        if hasattr(self.ui, 'pushButton_force_memory'):
            try:
                self.ui.pushButton_force_memory.clicked.disconnect()
            except TypeError:
                pass
            self.ui.pushButton_force_memory.clicked.connect(self._trigger_manual_memory)

        auto_summary_state = self.configuration_settings.get_main_setting("auto_summary")
        if auto_summary_state == False:
            self.ui.checkBox_enable_summary.setChecked(False)
        else:
            self.ui.checkBox_enable_summary.setChecked(True)

        mlock_state = self.configuration_settings.get_main_setting("mlock_status")
        if mlock_state == False:
            self.ui.checkBox_enable_mlock.setChecked(False)
        else:
            self.ui.checkBox_enable_mlock.setChecked(True)
        
        flash_attention_state = self.configuration_settings.get_main_setting("flash_attention_status")
        if flash_attention_state == False:
            self.ui.checkBox_enable_flash_attention.setChecked(False)
        else:
            self.ui.checkBox_enable_flash_attention.setChecked(True)

        tools_calling_enabled_state = self.configuration_settings.get_main_setting("enable_tool_calling")
        if tools_calling_enabled_state == False:
            self.ui.checkBox_enable_tool_calling.setChecked(False)
        else:
            self.ui.checkBox_enable_tool_calling.setChecked(True)

        mcp_enabled_state = self.configuration_settings.get_main_setting("enable_mcp")
        if mcp_enabled_state == False:
            self.ui.checkBox_enable_mcp.setChecked(False)
        else:
            self.ui.checkBox_enable_mcp.setChecked(True)

        nsfw_query = self.configuration_settings.get_main_setting("nsfw_query")
        if nsfw_query == False:
            self.ui.checkBox_enable_nsfw.setChecked(False)
        else:
            self.ui.checkBox_enable_nsfw.setChecked(True)

        self.ui.comboBox_user_persona_building.clear()
        self.ui.comboBox_system_prompt_building.clear()
        self.ui.comboBox_lorebook_building.clear()

        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})

        personas = user_data.get("personas", {})
        self.ui.comboBox_user_persona_building.addItem("None")
        for name in personas:
            self.ui.comboBox_user_persona_building.addItem(name)
        self.ui.comboBox_user_persona_building.setCurrentIndex(0)

        presets = user_data.get("presets", {})
        self.ui.comboBox_system_prompt_building.addItem("By default")
        for name in presets:
            self.ui.comboBox_system_prompt_building.addItem(name)
        self.ui.comboBox_system_prompt_building.setCurrentIndex(0)

        lorebooks = user_data.get("lorebooks", {})
        self.ui.comboBox_lorebook_building.addItem("None")
        for name in lorebooks:
            self.ui.comboBox_lorebook_building.addItem(name)
        self.ui.comboBox_lorebook_building.setCurrentIndex(0)
    ### SETUP GENERAL COMBOBOXES =======================================================================

    ### SETUP OPTIONS ==================================================================================
    def initialize_api_token_line_edit(self):
        """
        Entering an API token and active models for the selected option when launching the program.
        """
        selected_conversation_method = self.configuration_settings.get_main_setting("conversation_method")
        
        if selected_conversation_method == "Mistral AI":
            api_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Open AI":
            api_token = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
            current_base_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
            openai_model = self.configuration_settings.get_main_setting("openai_model") or ""
            self.ui.lineEdit_openai_model.setText(openai_model)
            self.ui.lineEdit_api_token_options.setText(api_token)
            self.ui.lineEdit_base_url_options.setText(current_base_url)
        elif selected_conversation_method == "OpenRouter":
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Anthropic":
            api_token = self.configuration_api.get_token("ANTHROPIC_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Google Gemini":
            api_token = self.configuration_api.get_token("GEMINI_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "DeepSeek":
            api_token = self.configuration_api.get_token("DEEPSEEK_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Grok":
            api_token = self.configuration_api.get_token("GROK_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Qwen":
            api_token = self.configuration_api.get_token("QWEN_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Z.AI":
            api_token = self.configuration_api.get_token("ZAI_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)

        self.ui.lineEdit_openai_model.setText(self.configuration_settings.get_main_setting("openai_model") or "")
        self.ui.lineEdit_mistral_model.setText(self.configuration_settings.get_main_setting("mistral_model_endpoint") or "")
        self.ui.lineEdit_anthropic_model.setText(self.configuration_settings.get_main_setting("anthropic_model") or "")
        self.ui.lineEdit_gemini_model.setText(self.configuration_settings.get_main_setting("gemini_model") or "")
        self.ui.lineEdit_deepseek_model.setText(self.configuration_settings.get_main_setting("deepseek_model") or "")
        self.ui.lineEdit_grok_model.setText(self.configuration_settings.get_main_setting("grok_model") or "")
        self.ui.lineEdit_qwen_model.setText(self.configuration_settings.get_main_setting("qwen_model") or "")
        self.ui.lineEdit_zai_model.setText(self.configuration_settings.get_main_setting("zai_model") or "")

    def update_api_token(self):
        """
        Changing the API token to the selected option and managing layout visibility dynamically.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()

        self.ui.label_base_url.hide()
        self.ui.lineEdit_base_url_options.hide()
        
        self.ui.label_openai_model.hide()
        self.ui.lineEdit_openai_model.hide()
        self.ui.label_mistral_model.hide()
        self.ui.lineEdit_mistral_model.hide()
        self.ui.label_anthropic_model.hide()
        self.ui.lineEdit_anthropic_model.hide()
        self.ui.label_gemini_model.hide()
        self.ui.lineEdit_gemini_model.hide()
        self.ui.label_deepseek_model.hide()
        self.ui.lineEdit_deepseek_model.hide()
        self.ui.label_grok_model.hide()
        self.ui.lineEdit_grok_model.hide()
        self.ui.label_qwen_model.hide()
        self.ui.lineEdit_qwen_model.hide()
        self.ui.label_zai_model.hide()
        self.ui.lineEdit_zai_model.hide()

        self.ui.openrouter_models_options_label.hide()
        self.ui.lineEdit_search_openrouter_models.hide()
        self.ui.comboBox_openrouter_models.hide()
        self.ui.pushButton_reload_openrouter_models.hide()

        self.ui.conversation_method_token_title_label.show()
        self.ui.lineEdit_api_token_options.show()

        if selected_conversation_method == "Mistral AI":
            self.ui.label_mistral_model.show()
            self.ui.lineEdit_mistral_model.show()
            api_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
            
        elif selected_conversation_method == "Open AI":
            self.ui.label_base_url.show()
            self.ui.lineEdit_base_url_options.show()
            self.ui.label_openai_model.show()
            self.ui.lineEdit_openai_model.show()
            api_token = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
            
        elif selected_conversation_method == "OpenRouter":
            self.ui.openrouter_models_options_label.show()
            self.ui.lineEdit_search_openrouter_models.show()
            self.ui.comboBox_openrouter_models.show()
            self.ui.pushButton_reload_openrouter_models.show()
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")

        elif selected_conversation_method == "Anthropic":
            self.ui.label_anthropic_model.show()
            self.ui.lineEdit_anthropic_model.show()
            api_token = self.configuration_api.get_token("ANTHROPIC_API_TOKEN")

        elif selected_conversation_method == "Google Gemini":
            self.ui.label_gemini_model.show()
            self.ui.lineEdit_gemini_model.show()
            api_token = self.configuration_api.get_token("GEMINI_API_TOKEN")

        elif selected_conversation_method == "DeepSeek":
            self.ui.label_deepseek_model.show()
            self.ui.lineEdit_deepseek_model.show()
            api_token = self.configuration_api.get_token("DEEPSEEK_API_TOKEN")

        elif selected_conversation_method == "Grok":
            self.ui.label_grok_model.show()
            self.ui.lineEdit_grok_model.show()
            api_token = self.configuration_api.get_token("GROK_API_TOKEN")

        elif selected_conversation_method == "Qwen":
            self.ui.label_qwen_model.show()
            self.ui.lineEdit_qwen_model.show()
            api_token = self.configuration_api.get_token("QWEN_API_TOKEN")

        elif selected_conversation_method == "Z.AI":
            self.ui.label_zai_model.show()
            self.ui.lineEdit_zai_model.show()
            api_token = self.configuration_api.get_token("ZAI_API_TOKEN")

        else:
            api_token = ""

        if api_token != self.ui.lineEdit_api_token_options.text():
            self.ui.lineEdit_api_token_options.setText(api_token)

    def save_api_token_in_real_time(self):
        """
        Saving the API token to a configuration file in real time.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()
        
        token_map = {
            "Mistral AI": "MISTRAL_AI_API_TOKEN",
            "Open AI": "OPEN_AI_API_TOKEN",
            "OpenRouter": "OPENROUTER_API_TOKEN",
            "Anthropic": "ANTHROPIC_API_TOKEN",
            "Google Gemini": "GEMINI_API_TOKEN",
            "DeepSeek": "DEEPSEEK_API_TOKEN",
            "Grok": "GROK_API_TOKEN",
            "Qwen": "QWEN_API_TOKEN",
            "Z.AI": "ZAI_API_TOKEN"
        }

        api_key_name = token_map.get(selected_conversation_method)
        if api_key_name:
            value = self.ui.lineEdit_api_token_options.text()
            if self.configuration_api.get_token(api_key_name) != value:
                self.configuration_api.save_api_token(api_key_name, value)
                self._clear_provider_verification(selected_conversation_method)
                self._reset_model_test_result()
                self.refresh_provider_verification_status()

    def on_pushButton_test_model_clicked(self):
        if self._model_test_task and not self._model_test_task.done():
            return
        self._model_test_task = asyncio.create_task(self.test_selected_model())

    async def test_selected_model(self):
        button = self.ui.pushButton_test_model
        result = self.ui.label_model_test_result
        button.setEnabled(False)
        result.setStyleSheet("color: #facc15;")
        result.setText("Checking model...")
        started = None
        first_response = None

        method = self.ui.comboBox_conversation_method.currentText()
        try:
            if method != "Local LLM" and not self.ui.lineEdit_api_token_options.text().strip():
                raise ValueError("missing API token")

            provider = AIFactory.get_provider(method)
            if not provider:
                raise ValueError("unsupported provider")

            started = time.perf_counter()
            async for chunk in provider.generate_stream(
                [{"role": "user", "content": "Reply with OK."}],
                max_tokens=1,
                temperature=0,
            ):
                if "API Error:" in chunk or chunk.lstrip().startswith("⚠️"):
                    raise RuntimeError("provider rejected the request")
                if first_response is None and chunk:
                    first_response = time.perf_counter() - started

            total = time.perf_counter() - started
            if first_response is None:
                raise RuntimeError("model returned no text")

            result.setStyleSheet("color: #4ADE80;")
            result.setText(f"Model is available. First response: {first_response:.2f}s. Total: {total:.2f}s.")
            self._set_provider_verified(method)
            self.refresh_provider_verification_status()
            self.refresh_character_provider_options()
        except Exception:
            self._clear_provider_verification(method)
            self.refresh_provider_verification_status()
            self.refresh_character_provider_options()
            result.setStyleSheet("color: #f87171;")
            if started is None:
                result.setText("Model check failed. Check the API token, model name, and connection.")
            else:
                total = time.perf_counter() - started
                result.setText(f"Model check failed. Total: {total:.2f}s. Check the API token, model name, and connection.")
        finally:
            button.setEnabled(True)

    def save_openai_model_in_real_time(self):
        self._save_model_setting("openai_model", self.ui.lineEdit_openai_model.text().strip(), "Open AI")

    def save_custom_url_in_real_time(self):
        value = self.ui.lineEdit_base_url_options.text()
        if self.configuration_api.get_token("CUSTOM_ENDPOINT_URL") != value:
            self.configuration_api.save_api_token("CUSTOM_ENDPOINT_URL", value)
            self._clear_provider_verification("Open AI")
            self._reset_model_test_result()
            self.refresh_provider_verification_status()

    def save_mistral_model_endpoint_in_real_time(self):
        self._save_model_setting("mistral_model_endpoint", self.ui.lineEdit_mistral_model.text(), "Mistral AI")

    def save_anthropic_model_in_real_time(self):
        self._save_model_setting("anthropic_model", self.ui.lineEdit_anthropic_model.text().strip(), "Anthropic")

    def save_gemini_model_in_real_time(self):
        self._save_model_setting("gemini_model", self.ui.lineEdit_gemini_model.text().strip(), "Google Gemini")

    def save_deepseek_model_in_real_time(self):
        self._save_model_setting("deepseek_model", self.ui.lineEdit_deepseek_model.text().strip(), "DeepSeek")

    def save_grok_model_in_real_time(self):
        self._save_model_setting("grok_model", self.ui.lineEdit_grok_model.text().strip(), "Grok")

    def save_qwen_model_in_real_time(self):
        self._save_model_setting("qwen_model", self.ui.lineEdit_qwen_model.text().strip(), "Qwen")

    def save_zai_model_in_real_time(self):
        self._save_model_setting("zai_model", self.ui.lineEdit_zai_model.text().strip(), "Z.AI")
    
    def initialize_lineEdit_customArgs(self):
        custom_args = self.configuration_settings.get_main_setting("custom_args")
        self.ui.lineEdit_customArgs.setText(custom_args)
    
    def save_lineEdit_customArgs_in_real_time(self):
        self.configuration_settings.update_main_setting("custom_args", self.ui.lineEdit_customArgs.text())

    def initialize_lineEdit_mcp_url(self):
        mcp_server = self.configuration_settings.get_main_setting("mcp_server")
        self.ui.lineEdit_mcp_url.setText(mcp_server)
    
    def save_lineEdit_mcp_url_in_real_time(self):
        self.configuration_settings.update_main_setting("mcp_server", self.ui.lineEdit_mcp_url.text())

    def initialize_cpu_moe_layers_horizontalSlider(self):
        cpu_moe_layers = self.configuration_settings.get_main_setting("cpu_moe_layers")
        self.ui.cpu_moe_layers_horizontalSlider.setValue(cpu_moe_layers)
        self.ui.lineEdit_cpuMoeLayers.setText(str(cpu_moe_layers))
    
    def save_cpu_moe_layers_in_real_time(self):
        cpu_moe_layers = self.ui.cpu_moe_layers_horizontalSlider.value()
        self.ui.lineEdit_cpuMoeLayers.setText(str(cpu_moe_layers))
        self.configuration_settings.update_main_setting("cpu_moe_layers", cpu_moe_layers)
    
    def update_cpu_moe_layers_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_cpuMoeLayers.text()
            cpu_moe_layers = int(text_value)

            min_value = self.ui.cpu_moe_layers_horizontalSlider.minimum()
            max_value = self.ui.cpu_moe_layers_horizontalSlider.maximum()
            cpu_moe_layers = max(min_value, min(max_value, cpu_moe_layers))

            self.ui.cpu_moe_layers_horizontalSlider.setValue(cpu_moe_layers)
            self.ui.lineEdit_cpuMoeLayers.setText(str(cpu_moe_layers))
            self.configuration_settings.update_main_setting("cpu_moe_layers", cpu_moe_layers)

        except ValueError:
            current_value = self.ui.cpu_moe_layers_horizontalSlider.value()
            self.ui.lineEdit_cpuMoeLayers.setText(str(current_value))

    def initialize_gpu_layers_horizontalSlider(self):
        n_gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")
        self.ui.gpu_layers_horizontalSlider.setValue(n_gpu_layers)
        self.ui.lineEdit_gpuLayers.setText(str(n_gpu_layers))

    def save_gpu_layers_in_real_time(self):
        n_gpu_layers = self.ui.gpu_layers_horizontalSlider.value()
        self.ui.lineEdit_gpuLayers.setText(str(n_gpu_layers))
        self.configuration_settings.update_main_setting("gpu_layers", n_gpu_layers)
    
    def update_gpu_layers_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_gpuLayers.text()
            n_gpu_layers = int(text_value)

            min_value = self.ui.gpu_layers_horizontalSlider.minimum()
            max_value = self.ui.gpu_layers_horizontalSlider.maximum()
            n_gpu_layers = max(min_value, min(max_value, n_gpu_layers))

            self.ui.gpu_layers_horizontalSlider.setValue(n_gpu_layers)
            self.ui.lineEdit_gpuLayers.setText(str(n_gpu_layers))
            self.configuration_settings.update_main_setting("gpu_layers", n_gpu_layers)

        except ValueError:
            current_value = self.ui.gpu_layers_horizontalSlider.value()
            self.ui.lineEdit_gpuLayers.setText(str(current_value))

    def initialize_context_size_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("context_size")
        if val is None:
            val = 8192
        
        try:
            idx = self.ui.CONTEXT_VALUES.index(val)
        except ValueError:
            idx = 4

        self.ui.context_size_horizontalSlider.setValue(idx)
        display_text = "Unlimited" if val == -1 else str(val)
        self.ui.lineEdit_contextSize.setText(display_text)

    def save_context_size_in_real_time(self):
        idx = self.ui.context_size_horizontalSlider.value()
        val = self.ui.CONTEXT_VALUES[idx]
        
        self.configuration_settings.update_main_setting("context_size", val)
        display_text = "Unlimited" if val == -1 else str(val)
        self.ui.lineEdit_contextSize.setText(display_text)
        
    def update_context_size_from_line_edit(self):
        text_val = self.ui.lineEdit_contextSize.text().strip()
        if text_val.lower() in ("unlimited", "inf", "-1", "none", "api"):
            val = -1
        else:
            try:
                val = int(text_val)
            except ValueError:
                val = 8192

        self.configuration_settings.update_main_setting("context_size", val)
        
        try:
            idx = self.ui.CONTEXT_VALUES.index(val)
            self.ui.context_size_horizontalSlider.setValue(idx)
        except ValueError:
            pass

        except ValueError:
            current_value = self.ui.context_size_horizontalSlider.value()
            self.ui.lineEdit_contextSize.setText(str(current_value))

    def initialize_temperature_horizontalSlider(self):
        temperature = self.configuration_settings.get_main_setting("temperature")
        temperature_int = int(round(temperature * 10))
        self.ui.temperature_horizontalSlider.setValue(temperature_int)
        self.ui.lineEdit_temperature.setText(f"{temperature:.1f}")

    def save_temperature_in_real_time(self):
        temperature = self.ui.temperature_horizontalSlider.value()
        scaled_value = temperature / 10.0
        self.configuration_settings.update_main_setting("temperature", scaled_value)
        self.ui.lineEdit_temperature.setText(f"{scaled_value:.1f}")
    
    def update_temperature_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_temperature.text()
            temperature = float(text_value)

            min_value = self.ui.temperature_horizontalSlider.minimum() / 10.0
            max_value = self.ui.temperature_horizontalSlider.maximum() / 10.0
            temperature = max(min_value, min(max_value, temperature))

            scaled_value_int = int(round(temperature * 10))
            self.ui.temperature_horizontalSlider.setValue(scaled_value_int)
            self.ui.lineEdit_temperature.setText(f"{temperature:.1f}")
            self.configuration_settings.update_main_setting("temperature", temperature)

        except ValueError:
            current_value = self.ui.temperature_horizontalSlider.value() / 10.0
            self.ui.lineEdit_temperature.setText(f"{current_value:.1f}")

    def initialize_top_p_horizontalSlider(self):
        top_p = self.configuration_settings.get_main_setting("top_p")
        top_p_int = int(round(top_p * 10))
        self.ui.top_p_horizontalSlider.setValue(top_p_int)
        self.ui.lineEdit_topP.setText(f"{top_p:.1f}")

    def save_top_p_in_real_time(self):
        top_p = self.ui.top_p_horizontalSlider.value()
        scaled_value = top_p / 10.0
        self.configuration_settings.update_main_setting("top_p", scaled_value)
        self.ui.lineEdit_topP.setText(f"{scaled_value:.1f}")
    
    def update_top_p_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_topP.text()
            top_p = float(text_value)

            min_value = self.ui.top_p_horizontalSlider.minimum() / 10.0
            max_value = self.ui.top_p_horizontalSlider.maximum() / 10.0
            top_p = max(min_value, min(max_value, top_p))

            scaled_value_int = int(round(top_p * 10))
            self.ui.top_p_horizontalSlider.setValue(scaled_value_int)
            self.ui.lineEdit_topP.setText(f"{top_p:.1f}")
            self.configuration_settings.update_main_setting("top_p", top_p)

        except ValueError:
            current_value = self.ui.top_p_horizontalSlider.value() / 10.0
            self.ui.lineEdit_topP.setText(f"{current_value:.1f}")

    def initialize_max_tokens_horizontalSlider(self):
        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        self.ui.max_tokens_horizontalSlider.setValue(max_tokens)
        self.ui.lineEdit_maxTokens.setText(str(max_tokens))

    def save_max_tokens_in_real_time(self):
        max_tokens = self.ui.max_tokens_horizontalSlider.value()
        self.configuration_settings.update_main_setting("max_tokens", max_tokens)
        self.ui.lineEdit_maxTokens.setText(str(max_tokens))

    def update_max_tokens_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_maxTokens.text()
            max_tokens = int(text_value)

            min_value = self.ui.max_tokens_horizontalSlider.minimum()
            max_tokens = max(min_value, max_tokens)
            
            max_value = self.ui.max_tokens_horizontalSlider.maximum()
            if max_tokens > max_value:
                self.ui.lineEdit_maxTokens.setText(str(max_tokens))
            else:
                self.ui.max_tokens_horizontalSlider.setValue(max_tokens)
                self.ui.lineEdit_maxTokens.setText(str(max_tokens))

            self.configuration_settings.update_main_setting("max_tokens", max_tokens)

        except ValueError:
            current_value = self.ui.max_tokens_horizontalSlider.value()
            self.ui.lineEdit_maxTokens.setText(str(current_value))
    
    def initialize_freq_penalty_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("frequency_penalty")
        val = val if val is not None else 0.0
        self.ui.freq_penalty_horizontalSlider.setValue(int(round(val * 10)))
        self.ui.lineEdit_freqPenalty.setText(f"{val:.1f}")

    def save_freq_penalty_in_real_time(self):
        val = self.ui.freq_penalty_horizontalSlider.value() / 10.0
        self.configuration_settings.update_main_setting("frequency_penalty", val)
        self.ui.lineEdit_freqPenalty.setText(f"{val:.1f}")

    def update_freq_penalty_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_freqPenalty.text())
            val = max(0.0, min(2.0, val))
            self.ui.freq_penalty_horizontalSlider.setValue(int(round(val * 10)))
            self.ui.lineEdit_freqPenalty.setText(f"{val:.1f}")
            self.configuration_settings.update_main_setting("frequency_penalty", val)
        except ValueError:
            self.ui.lineEdit_freqPenalty.setText(f"{self.ui.freq_penalty_horizontalSlider.value() / 10.0:.1f}")

    def initialize_pres_penalty_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("presence_penalty")
        val = val if val is not None else 0.0
        self.ui.pres_penalty_horizontalSlider.setValue(int(round(val * 10)))
        self.ui.lineEdit_presPenalty.setText(f"{val:.1f}")

    def save_pres_penalty_in_real_time(self):
        val = self.ui.pres_penalty_horizontalSlider.value() / 10.0
        self.configuration_settings.update_main_setting("presence_penalty", val)
        self.ui.lineEdit_presPenalty.setText(f"{val:.1f}")

    def update_pres_penalty_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_presPenalty.text())
            val = max(0.0, min(2.0, val))
            self.ui.pres_penalty_horizontalSlider.setValue(int(round(val * 10)))
            self.ui.lineEdit_presPenalty.setText(f"{val:.1f}")
            self.configuration_settings.update_main_setting("presence_penalty", val)
        except ValueError:
            self.ui.lineEdit_presPenalty.setText(f"{self.ui.pres_penalty_horizontalSlider.value() / 10.0:.1f}")

    def initialize_min_p_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("min_p")
        val = val if val is not None else 0.05
        self.ui.min_p_horizontalSlider.setValue(int(round(val * 100)))
        self.ui.lineEdit_minP.setText(f"{val:.2f}")

    def save_min_p_in_real_time(self):
        val = self.ui.min_p_horizontalSlider.value() / 100.0
        self.configuration_settings.update_main_setting("min_p", val)
        self.ui.lineEdit_minP.setText(f"{val:.2f}")

    def update_min_p_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_minP.text())
            val = max(0.0, min(1.0, val))
            self.ui.min_p_horizontalSlider.setValue(int(round(val * 100)))
            self.ui.lineEdit_minP.setText(f"{val:.2f}")
            self.configuration_settings.update_main_setting("min_p", val)
        except ValueError:
            self.ui.lineEdit_minP.setText(f"{self.ui.min_p_horizontalSlider.value() / 100.0:.2f}")

    def initialize_dyn_temp_min_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("dyn_temp_min")
        val = val if val is not None else 0.0
        self.ui.dyn_temp_min_horizontalSlider.setValue(int(round(val * 10)))
        self.ui.lineEdit_dynTempMin.setText(f"{val:.1f}")

    def save_dyn_temp_min_in_real_time(self):
        val = self.ui.dyn_temp_min_horizontalSlider.value() / 10.0
        self.configuration_settings.update_main_setting("dyn_temp_min", val)
        self.ui.lineEdit_dynTempMin.setText(f"{val:.1f}")

    def update_dyn_temp_min_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_dynTempMin.text())
            val = max(0.0, min(2.0, val))
            self.ui.dyn_temp_min_horizontalSlider.setValue(int(round(val * 10)))
            self.ui.lineEdit_dynTempMin.setText(f"{val:.1f}")
            self.configuration_settings.update_main_setting("dyn_temp_min", val)
        except ValueError:
            self.ui.lineEdit_dynTempMin.setText(f"{self.ui.dyn_temp_min_horizontalSlider.value() / 10.0:.1f}")

    def initialize_dyn_temp_max_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("dyn_temp_max")
        val = val if val is not None else 0.0
        self.ui.dyn_temp_max_horizontalSlider.setValue(int(round(val * 10)))
        self.ui.lineEdit_dynTempMax.setText(f"{val:.1f}")

    def save_dyn_temp_max_in_real_time(self):
        val = self.ui.dyn_temp_max_horizontalSlider.value() / 10.0
        self.configuration_settings.update_main_setting("dyn_temp_max", val)
        self.ui.lineEdit_dynTempMax.setText(f"{val:.1f}")

    def update_dyn_temp_max_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_dynTempMax.text())
            val = max(0.0, min(2.0, val))
            self.ui.dyn_temp_max_horizontalSlider.setValue(int(round(val * 10)))
            self.ui.lineEdit_dynTempMax.setText(f"{val:.1f}")
            self.configuration_settings.update_main_setting("dyn_temp_max", val)
        except ValueError:
            self.ui.lineEdit_dynTempMax.setText(f"{self.ui.dyn_temp_max_horizontalSlider.value() / 10.0:.1f}")

    def initialize_xtc_prob_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("xtc_probability")
        val = val if val is not None else 0.0
        self.ui.xtc_prob_horizontalSlider.setValue(int(round(val * 100)))
        self.ui.lineEdit_xtcProb.setText(f"{val:.2f}")

    def save_xtc_prob_in_real_time(self):
        val = self.ui.xtc_prob_horizontalSlider.value() / 100.0
        self.configuration_settings.update_main_setting("xtc_probability", val)
        self.ui.lineEdit_xtcProb.setText(f"{val:.2f}")

    def update_xtc_prob_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_xtcProb.text())
            val = max(0.0, min(1.0, val))
            self.ui.xtc_prob_horizontalSlider.setValue(int(round(val * 100)))
            self.ui.lineEdit_xtcProb.setText(f"{val:.2f}")
            self.configuration_settings.update_main_setting("xtc_probability", val)
        except ValueError:
            self.ui.lineEdit_xtcProb.setText(f"{self.ui.xtc_prob_horizontalSlider.value() / 100.0:.2f}")

    def initialize_xtc_threshold_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("xtc_threshold")
        val = val if val is not None else 0.10
        self.ui.xtc_threshold_horizontalSlider.setValue(int(round(val * 100)))
        self.ui.lineEdit_xtcThreshold.setText(f"{val:.2f}")

    def save_xtc_threshold_in_real_time(self):
        val = self.ui.xtc_threshold_horizontalSlider.value() / 100.0
        self.configuration_settings.update_main_setting("xtc_threshold", val)
        self.ui.lineEdit_xtcThreshold.setText(f"{val:.2f}")

    def update_xtc_threshold_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_xtcThreshold.text())
            val = max(0.0, min(1.0, val))
            self.ui.xtc_threshold_horizontalSlider.setValue(int(round(val * 100)))
            self.ui.lineEdit_xtcThreshold.setText(f"{val:.2f}")
            self.configuration_settings.update_main_setting("xtc_threshold", val)
        except ValueError:
            self.ui.lineEdit_xtcThreshold.setText(f"{self.ui.xtc_threshold_horizontalSlider.value() / 100.0:.2f}")

    def initialize_dry_multiplier_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("dry_multiplier")
        val = val if val is not None else 0.0
        self.ui.dry_multiplier_horizontalSlider.setValue(int(round(val * 100)))
        self.ui.lineEdit_dryMultiplier.setText(f"{val:.2f}")

    def save_dry_multiplier_in_real_time(self):
        val = self.ui.dry_multiplier_horizontalSlider.value() / 100.0
        self.configuration_settings.update_main_setting("dry_multiplier", val)
        self.ui.lineEdit_dryMultiplier.setText(f"{val:.2f}")

    def update_dry_multiplier_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_dryMultiplier.text())
            val = max(0.0, min(2.0, val))
            self.ui.dry_multiplier_horizontalSlider.setValue(int(round(val * 100)))
            self.ui.lineEdit_dryMultiplier.setText(f"{val:.2f}")
            self.configuration_settings.update_main_setting("dry_multiplier", val)
        except ValueError:
            self.ui.lineEdit_dryMultiplier.setText(f"{self.ui.dry_multiplier_horizontalSlider.value() / 100.0:.2f}")

    def initialize_dry_base_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("dry_base")
        val = val if val is not None else 1.75
        self.ui.dry_base_horizontalSlider.setValue(int(round(val * 100)))
        self.ui.lineEdit_dryBase.setText(f"{val:.2f}")

    def save_dry_base_in_real_time(self):
        val = self.ui.dry_base_horizontalSlider.value() / 100.0
        self.configuration_settings.update_main_setting("dry_base", val)
        self.ui.lineEdit_dryBase.setText(f"{val:.2f}")

    def update_dry_base_from_line_edit(self):
        try:
            val = float(self.ui.lineEdit_dryBase.text())
            val = max(0.0, min(2.0, val))
            self.ui.dry_base_horizontalSlider.setValue(int(round(val * 100)))
            self.ui.lineEdit_dryBase.setText(f"{val:.2f}")
            self.configuration_settings.update_main_setting("dry_base", val)
        except ValueError:
            self.ui.lineEdit_dryBase.setText(f"{self.ui.dry_base_horizontalSlider.value() / 100.0:.2f}")

    def initialize_dry_allowed_length_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("dry_allowed_length")
        val = val if val is not None else 2
        self.ui.dry_allowed_length_horizontalSlider.setValue(val)
        self.ui.lineEdit_dryAllowedLength.setText(str(val))

    def save_dry_allowed_length_in_real_time(self):
        val = self.ui.dry_allowed_length_horizontalSlider.value()
        self.configuration_settings.update_main_setting("dry_allowed_length", val)
        self.ui.lineEdit_dryAllowedLength.setText(str(val))

    def update_dry_allowed_length_from_line_edit(self):
        try:
            val = int(self.ui.lineEdit_dryAllowedLength.text())
            val = max(0, min(100, val))
            self.ui.dry_allowed_length_horizontalSlider.setValue(val)
            self.ui.lineEdit_dryAllowedLength.setText(str(val))
            self.configuration_settings.update_main_setting("dry_allowed_length", val)
        except ValueError:
            self.ui.lineEdit_dryAllowedLength.setText(str(self.ui.dry_allowed_length_horizontalSlider.value()))
    
    def initialize_interval_summary(self):
        interval = self.configuration_settings.get_main_setting("interval_summary")
        self.ui.spinBox_summary_interval.setValue(interval)
    
    def save_interval_summary_in_real_time(self):
        interval = self.ui.spinBox_summary_interval.value()
        self.configuration_settings.update_main_setting("interval_summary", interval)

    def on_comboBox_kv_cache_changed(self, index):
        mapping = {0: "f16", 1: "q8_0", 2: "q4_1", 3: "q4_0"}
        val = mapping.get(index, "f16")
        self.configuration_settings.update_main_setting("kv_cache_type", val)

    def initialize_batch_size_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("llm_batch_size")
        val = val if val is not None else 512
        self.ui.batch_size_horizontalSlider.setValue(val)
        self.ui.lineEdit_batchSize.setText(str(val))

    def save_batch_size_in_real_time(self):
        val = self.ui.batch_size_horizontalSlider.value()
        self.configuration_settings.update_main_setting("llm_batch_size", val)
        self.ui.lineEdit_batchSize.setText(str(val))

    def update_batch_size_from_line_edit(self):
        try:
            val = int(self.ui.lineEdit_batchSize.text())
            min_val = self.ui.batch_size_horizontalSlider.minimum()
            max_val = self.ui.batch_size_horizontalSlider.maximum()
            val = max(min_val, min(max_val, val))
            self.ui.batch_size_horizontalSlider.setValue(val)
            self.ui.lineEdit_batchSize.setText(str(val))
            self.configuration_settings.update_main_setting("llm_batch_size", val)
        except ValueError:
            self.ui.lineEdit_batchSize.setText(str(self.ui.batch_size_horizontalSlider.value()))

    def initialize_cpu_threads_horizontalSlider(self):
        val = self.configuration_settings.get_main_setting("cpu_threads")
        val = val if val is not None else 0
        self.ui.cpu_threads_horizontalSlider.setValue(val)
        self.ui.lineEdit_cpuThreads.setText(str(val))

    def save_cpu_threads_in_real_time(self):
        val = self.ui.cpu_threads_horizontalSlider.value()
        self.configuration_settings.update_main_setting("cpu_threads", val)
        self.ui.lineEdit_cpuThreads.setText(str(val))

    def update_cpu_threads_from_line_edit(self):
        try:
            val = int(self.ui.lineEdit_cpuThreads.text())
            min_val = self.ui.cpu_threads_horizontalSlider.minimum()
            max_val = self.ui.cpu_threads_horizontalSlider.maximum()
            val = max(min_val, min(max_val, val))
            self.ui.cpu_threads_horizontalSlider.setValue(val)
            self.ui.lineEdit_cpuThreads.setText(str(val))
            self.configuration_settings.update_main_setting("cpu_threads", val)
        except ValueError:
            self.ui.lineEdit_cpuThreads.setText(str(self.ui.cpu_threads_horizontalSlider.value()))

    def count_tokens(self, text):
        return len(self.tokenizer_character.encode(text))

    def update_token_count(self):
        texts = [
            self.ui.lineEdit_character_name_building.text(),
            self.ui.textEdit_character_description_building.toPlainText(),
            self.ui.textEdit_character_personality_building.toPlainText(),
            self.ui.textEdit_first_message_building.toPlainText(),
            self.ui.textEdit_scenario.toPlainText(),
            self.ui.textEdit_example_messages.toPlainText(),
            self.ui.textEdit_alternate_greetings.toPlainText()
        ]

        total_tokens = sum(self.count_tokens(text) for text in texts)

        if total_tokens < 2000:
            color = "#a0a0a0"
            weight_text = "Optimal"
        elif total_tokens < 4000:
            color = "#d4a373"
            weight_text = "Heavy"
        elif total_tokens < 6000:
            color = "#e27d60"
            weight_text = "Warning"
        else:
            color = "#c9184a"
            weight_text = "Critical"

        self.ui.total_tokens_building_label.setStyleSheet(
            f"font-family: 'Inter Tight SemiBold'; font-size: 15px; color: {color}; border: none; background: transparent;"
        )
        self.ui.total_tokens_building_label.setText(f"Total Tokens: {total_tokens} ({weight_text})")
    
    def open_updater_dialog(self):
        is_cpu = self.ui.comboBox_llm_devices.currentText() == "CPU"
        gpu_backend = self.ui.comboBox_llm_gpu_devices.currentText()
        
        if is_cpu:
            target = "cpu"
        elif "CUDA" in gpu_backend:
            target = "cuda"
        elif "HIP" in gpu_backend:
            target = "hip"
        elif "SYCL" in gpu_backend:
            target = "sycl"
        else:
            target = "vulkan"
            
        dialog = UpdaterDialog(backend_dir=Path("app/utils/ai_clients/backend"), backend_type=target, translations=self.translations, parent=self.main_window)
        dialog.exec()
    ### SETUP OPTIONS ==================================================================================

    ### SETUP CHARACTER INFORMATION ====================================================================
    def import_character_avatar(self):
        """
        Opens a dialog box for selecting a character's avatar image and updates the interface.
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "Choose character's image", "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                self._set_editor_avatar(file_path)
            else:
                logger.error("No file selected.")
                return None
        except Exception as e:
            logger.error(f"Error importing character image: {e}")
            return None
    
    def _set_editor_avatar(self, image_path=None):
        button = self.ui.pushButton_import_character_image
        size = 100
        radius = 12
        
        if not image_path or not os.path.exists(image_path):
            icon_import = QtGui.QIcon()
            icon_import.addPixmap(QtGui.QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            button.setIcon(icon_import)
            button.setIconSize(QtCore.QSize(32, 32))
            self.configuration_settings.update_user_data("current_character_image", None)
            return

        pixmap = QtGui.QPixmap(image_path)
        if pixmap.isNull():
            return

        scaled = pixmap.scaled(size, size, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding, QtCore.Qt.TransformationMode.SmoothTransformation)
        crop_x = (scaled.width() - size) // 2
        crop_y = (scaled.height() - size) // 2
        square = scaled.copy(crop_x, crop_y, size, size)
        
        final_px = QtGui.QPixmap(size, size)
        final_px.fill(QtCore.Qt.GlobalColor.transparent)
        
        painter = QtGui.QPainter(final_px)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(0, 0, size, size, radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, square)
        painter.end()
        
        button.setIcon(QtGui.QIcon(final_px))
        button.setIconSize(QtCore.QSize(size, size))
        self.configuration_settings.update_user_data("current_character_image", image_path)

    def import_character_card_from_menu(self):
        """
        Handles importing a character card directly from the main menu.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            None, 
            "Choose Character Card (PNG or JSON)", 
            "", 
            "Character Files (*.png *.json);;PNG Images (*.png);;JSON Files (*.json)"
        )
        
        if file_path:
            self.ui.pushButton_rp_editors.click()
            self.prepare_new_character_editor()
            self.import_character_card(file_path)
            QtCore.QTimer.singleShot(0, lambda: self.ui.stackedWidget.setCurrentWidget(self.ui.create_character_page))

    def import_character_card(self, file_path=None):
        try:
            if not file_path:
                file_path, _ = QFileDialog.getOpenFileName(
                    None, 
                    "Choose Character Card (PNG or JSON)", 
                    "", 
                    "Character Files (*.png *.json);;PNG Images (*.png);;JSON Files (*.json)"
                )
            if not file_path:
                return

            if file_path.lower().endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.character_data = json.load(f)
                self._set_editor_avatar(None)
            else:
                cached_image_path = self.save_image_to_cache(file_path)
                self._set_editor_avatar(cached_image_path)
                self.character_data = self.read_character_card(file_path)

            if self.character_data and "data" in self.character_data:
                data = self.character_data["data"]

                self.ui.lineEdit_character_name_building.setText(str(data.get("name", "")))
                self.ui.textEdit_character_description_building.setPlainText(str(data.get("description", "")))
                self.ui.textEdit_character_personality_building.setPlainText(str(data.get("personality", "")))
                self.ui.textEdit_first_message_building.setPlainText(str(data.get("first_mes", "")))
                self.ui.textEdit_example_messages.setPlainText(str(data.get("mes_example", "")))
                self.ui.textEdit_creator_notes.setPlainText(str(data.get("creator_notes", "")))
                self.ui.textEdit_character_version.setPlainText(str(data.get("character_version", "")))
                self.ui.textEdit_scenario.setPlainText(str(data.get("scenario", "")))

                alternate_greetings = data.get("alternate_greetings", [])
                self.ui.textEdit_alternate_greetings.setPlainText(self.format_alternate_greetings(alternate_greetings))

                extensions = data.get("extensions", {})
                sow_variables = extensions.get("sow_variables", [])
                if sow_variables and hasattr(self.ui, 'add_blank_variable_row'):
                    for var in sow_variables:
                        self.ui.add_blank_variable_row(var)

                character_book_data = data.get("character_book")
                if character_book_data:
                    books_to_import = []
                    if isinstance(character_book_data, dict):
                        books_to_import = [character_book_data]
                    elif isinstance(character_book_data, list):
                        books_to_import = character_book_data

                    for character_book in books_to_import:
                        book_name = character_book.get("name")
                        if not book_name or book_name.strip() == "":
                            book_name = f"Lore_{data.get('name', 'Unknown')}"
                            if len(books_to_import) > 1:
                                book_name += f"_{books_to_import.index(character_book) + 1}"

                        import_lorebook_text = self.translations.get("import_lorebook_text", f"This card contains an embedded lorebook '{book_name}'. Do you want to add it to your library?").format(book_name=book_name)
                        
                        confirm_dialog = SowConfirmDialog(
                            parent=self.main_window,
                            title=self.translations.get("lorebook_editor_import_lorebook", "Import Lorebook"),
                            text=import_lorebook_text,
                            confirm_text="Import",
                            danger=False
                        )

                        if confirm_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                            config = self.configuration_settings.load_configuration()
                            lorebooks = config.get("user_data", {}).get("lorebooks", {})

                            new_name = book_name
                            orig_name = new_name
                            counter = 1
                            while new_name in lorebooks:
                                new_name = f"{orig_name}_{counter}"
                                counter += 1

                            new_lorebook = {
                                "name": new_name,
                                "description": character_book.get("description", ""),
                                "n_depth": character_book.get("scan_depth", 3),
                                "entries": []
                            }

                            entries_data = character_book.get("entries", {})
                            if isinstance(entries_data, dict):
                                sorted_keys = sorted(entries_data.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                                items_to_parse = [entries_data[k] for k in sorted_keys]
                            else:
                                items_to_parse = entries_data

                            for e in items_to_parse:
                                ext = e.get("extensions", {})
                                keys = e.get("key", e.get("keys", []))
                                
                                new_entry = {
                                    "name": e.get("name", e.get("comment", "Unnamed Entry")),
                                    "content": e.get("content", ""),
                                    "key": keys if isinstance(keys, list) else [keys],
                                    "probability": e.get("probability", 100),
                                    
                                    "trigger_type": ext.get("sow_trigger_type", "keyword"),
                                    "min_msg": ext.get("sow_min_msg", 0),
                                    "max_msg": ext.get("sow_max_msg", 0),
                                    "exclude_key": ext.get("sow_exclude_key", []),
                                    "sticky": ext.get("sow_sticky", 0),
                                    "cooldown": ext.get("sow_cooldown", 0),
                                    "delay": ext.get("sow_delay", 0)
                                }
                                new_lorebook["entries"].append(new_entry)

                            self.configuration_settings.update_lorebook(new_name, new_lorebook)
                            
                            count_val = len(new_lorebook['entries'])
                            success_msg = self.translations.get("lorebook_editor_import_success_desc", "Lorebook '{new_name}' imported with {count} entries.").format(new_name=new_name, count=count_val)
                            sow_toast(
                                parent=self.main_window,
                                title=self.translations.get("lorebook_editor_import_success", "Import Success"),
                                text=success_msg,
                                msg_type="success"
                            )
                            
                            if new_name not in self._selected_lorebooks_building:
                                self._selected_lorebooks_building.append(new_name)
                    
                    self._update_lorebook_button_text()

        except Exception as e:
            logger.error(f"Error importing character card: {e}")
            error_str = str(e)
            
            err_title = self.translations.get("lorebook_editor_import_error", "Import Error")
            err_msg = self.translations.get("lorebook_editor_import_error_desc", f"Failed to parse lorebook: {error_str}").format(error=error_str)
            
            sow_toast(
                parent=self.main_window,
                title=err_title,
                text=err_msg,
                msg_type="error"
            )

    def save_image_to_cache(self, file_path):
        with open(file_path, "rb") as f:
            file_content = f.read()

        file_name_with_extension = file_path.split("/")[-1]
        cached_file_name = file_name_with_extension.split(".")[0]

        cached_file_path = os.path.join(CACHE_DIR, cached_file_name)
        if not os.path.exists(cached_file_path):
            with open(cached_file_path, "wb") as f:
                f.write(file_content)

        return cached_file_path
    
    def read_character_card(self, path):
        image = PngImagePlugin.PngImageFile(path)

        user_comment = image.text.get('chara', None)
        if user_comment is None:
            logger.error("No character data found in the image.")
            return None
        try:
            json_bytes = base64.b64decode(user_comment)
            json_str = json_bytes.decode('utf-8')
            data = json.loads(json_str)
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.error(f"Error decoding character data: {e}")
            return None
        return data
    
    def format_alternate_greetings(self, greetings_list):
        if not greetings_list:
            return ""

        formatted = "\n".join([f"<GREETING>\n{g.strip()}" for g in greetings_list if g.strip()])
        return formatted.strip()

    def parse_alternate_greetings(self, raw_text):
        if not raw_text or "<GREETING>" not in raw_text:
            return []

        parts = raw_text.split("<GREETING>")

        greetings = [part.strip() for part in parts if part.strip()]
        
        return greetings

    def export_character_card(self):
        try:
            character_name = self.ui.lineEdit_character_name_building.text().strip()
            if not character_name:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("error_title", "Error"),
                    text="Character name is required!",
                    msg_type="error"
                )
                return

            sow_variables = self.ui.get_variables_data() if hasattr(self.ui, 'get_variables_data') else []

            char_data = {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    'name': character_name,
                    'description': self.ui.textEdit_character_description_building.toPlainText().strip(),
                    'personality': self.ui.textEdit_character_personality_building.toPlainText().strip(),
                    'first_mes': self.ui.textEdit_first_message_building.toPlainText().strip(),
                    'scenario': self.ui.textEdit_scenario.toPlainText().strip(),
                    'mes_example': self.ui.textEdit_example_messages.toPlainText().strip(),
                    'creator_notes': self.ui.textEdit_creator_notes.toPlainText().strip(),
                    'character_version': self.ui.textEdit_character_version.toPlainText().strip() or "1.0.0",
                    'tags': ["sow", "custom"],
                    'extensions': {
                        "sow_variables": sow_variables
                    },
                    'alternate_greetings': self.parse_alternate_greetings(self.ui.textEdit_alternate_greetings.toPlainText()),
                    'system_prompt': "",
                    'post_history_instructions': ""
                }
            }

            selected_lorebooks = self._selected_lorebooks_building
            
            if selected_lorebooks:
                main_config = self.configuration_settings.load_configuration()
                all_lorebooks = main_config.get("user_data", {}).get("lorebooks", {})
                
                books_to_export = []
                for lb_name in selected_lorebooks:
                    if lb_name in all_lorebooks:
                        books_to_export.append(all_lorebooks[lb_name])
                    else:
                        logger.warning(f"Lorebook '{lb_name}' selected but not found in database.")
                        
                if len(books_to_export) == 1:
                    char_data["data"]["character_book"] = books_to_export[0]
                elif len(books_to_export) > 1:
                    char_data["data"]["character_book"] = books_to_export

            file_path, selected_filter = QFileDialog.getSaveFileName(
                None, 
                "Export Character", 
                f"{character_name}", 
                "PNG Images (*.png);;JSON Files (*.json)"
            )
            
            if not file_path:
                return

            if file_path.lower().endswith('.json') or "JSON" in selected_filter:
                if not file_path.lower().endswith('.json'):
                    file_path += ".json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(char_data, f, ensure_ascii=False, indent=4)
            else:
                if not file_path.lower().endswith('.png'):
                    file_path += ".png"

                json_str = json.dumps(char_data, ensure_ascii=False) 
                b64_data = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

                current_image_path = self.configuration_settings.get_user_data("current_character_image")
                if current_image_path and os.path.exists(current_image_path):
                    image = Image.open(current_image_path).convert("RGBA")
                else:
                    if os.path.exists("app/gui/icons/export_card.png"):
                        image = Image.open("app/gui/icons/export_card.png").convert("RGBA")
                    else:
                        image = Image.new("RGBA", (400, 600), (50, 50, 50))

                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("chara", b64_data)
                image.save(file_path, format="PNG", pnginfo=png_info)
            
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("success_title", "Success"),
                text=f"Character card exported to {os.path.basename(file_path)}",
                msg_type="success"
            )

        except Exception as e:
            logger.error(f"Error exporting character card: {e}")

            sow_toast(
                parent=self.main_window,
                title="Export Error",
                text=f"Failed: {str(e)}",
                msg_type="error"
            )
    
    def clean_character_card(self):
        self._set_editor_avatar(None)
        self.configuration_settings.update_user_data("current_character_image", "None")

        self.ui.lineEdit_character_name_building.clear(),
        self.ui.textEdit_character_description_building.clear(),
        self.ui.textEdit_character_personality_building.clear(),
        self.ui.textEdit_first_message_building.clear(),
        self.ui.textEdit_scenario.clear(),
        self.ui.textEdit_example_messages.clear(),
        self.ui.textEdit_alternate_greetings.clear(),
        self.ui.textEdit_creator_notes.clear(),
        self.ui.textEdit_character_version.clear()

        if hasattr(self.ui, 'clear_variables_layout'):
            self.ui.clear_variables_layout()
        
        self._selected_lorebooks_building = []
        self._update_lorebook_button_text()

        self.ui.comboBox_user_persona_building.clear()
        self.ui.comboBox_system_prompt_building.clear()
        self.ui.comboBox_lorebook_building.clear()

        config = self.configuration_settings.load_configuration()
        user_data = config.get("user_data", {})

        personas = user_data.get("personas", {})
        self.ui.comboBox_user_persona_building.addItem("None")
        for name in personas:
            self.ui.comboBox_user_persona_building.addItem(name)
        self.ui.comboBox_user_persona_building.setCurrentIndex(0)

        presets = user_data.get("presets", {})
        self.ui.comboBox_system_prompt_building.addItem("By default")
        for name in presets:
            self.ui.comboBox_system_prompt_building.addItem(name)
        self.ui.comboBox_system_prompt_building.setCurrentIndex(0)

        lorebooks = user_data.get("lorebooks", {})
        self.ui.comboBox_lorebook_building.addItem("None")
        for name in lorebooks:
            self.ui.comboBox_lorebook_building.addItem(name)
        self.ui.comboBox_lorebook_building.setCurrentIndex(0)

        self.ui.total_tokens_building_label.setText("Total tokens: ")

    def populate_editor_character_list(self):
        """Populates the character list in the editor with all available characters."""
        self.ui.editor_character_list.clear()
        
        config = self.configuration_characters.load_configuration()
        characters = config.get("character_list", {})
        
        for char_name, char_data in characters.items():
            avatar_path = char_data.get("character_avatar")
            
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(56, 56))
            item.setData(QtCore.Qt.ItemDataRole.UserRole, char_name)
            item.setToolTip(char_name)
            
            self.ui.editor_character_list.addItem(item)
            
            widget = EditorCharacterItemWidget(avatar_path)
            self.ui.editor_character_list.setItemWidget(item, widget)
            
    def load_character_into_editor(self, item):
        """Loads the selected character's data into the editor fields."""
        char_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
        config = self.configuration_characters.load_configuration()
        characters = config.get("character_list", {})
        
        if char_name not in characters:
            return
            
        char_data = characters[char_name]
        self._editing_character_name = char_name 
        
        self.clean_character_card()
        
        self.ui.lineEdit_character_name_building.setText(char_name)
        self.ui.textEdit_character_description_building.setPlainText(char_data.get("character_description", ""))
        self.ui.textEdit_character_personality_building.setPlainText(char_data.get("character_personality", ""))
        self.ui.textEdit_first_message_building.setPlainText(char_data.get("first_message", ""))
        self.ui.textEdit_scenario.setPlainText(char_data.get("scenario", ""))
        self.ui.textEdit_example_messages.setPlainText(char_data.get("example_messages", ""))
        
        alt_greetings = char_data.get("alternate_greetings", [])
        if isinstance(alt_greetings, list):
            alt_greetings_str = "\n\n".join([f"<GREETING>\n{g}" for g in alt_greetings if g.strip()])
        else:
            alt_greetings_str = alt_greetings
        self.ui.textEdit_alternate_greetings.setPlainText(alt_greetings_str)
        
        self.ui.textEdit_creator_notes.setPlainText(char_data.get("character_title", ""))
        self.ui.textEdit_character_version.setPlainText(char_data.get("character_version", "1.0.0"))
        self.refresh_character_provider_options(char_data.get("conversation_method", "Local LLM"))
        self.refresh_character_model_options(char_data.get("model_override") or "")

        sow_variables = char_data.get("sow_variables", [])
        if hasattr(self.ui, 'add_blank_variable_row'):
            for var in sow_variables:
                self.ui.add_blank_variable_row(var)

        for combo, key in [
            (self.ui.comboBox_user_persona_building, "selected_persona"),
            (self.ui.comboBox_system_prompt_building, "selected_system_prompt_preset"),
        ]:
            val = char_data.get(key, "None" if "persona" in key else "By default")
            idx = combo.findText(val)
            if idx >= 0: combo.setCurrentIndex(idx)
        
        self._selected_lorebooks_building = char_data.get("selected_lorebooks", [])
        if not self._selected_lorebooks_building:
            old_lb = char_data.get("selected_lorebook", "None")
            if old_lb != "None":
                self._selected_lorebooks_building = [old_lb]
        self._update_lorebook_button_text()
        
        avatar_path = char_data.get("character_avatar")
        self._set_editor_avatar(avatar_path)
            
        self.ui.pushButton_create_character_3.setText(self.translations.get("character_edit_save_button", "Save Character"))
        self.update_token_count()

    def prepare_new_character_editor(self):
        self._editing_character_name = None
        self.clean_character_card()
        self._editor_provider_value = None
        self.refresh_character_provider_options()
        self.ui.editor_character_list.clearSelection()
        self.ui.pushButton_create_character_3.setText(self.translations.get("create_character_button_3", "Create Character"))

    ### SETUP CHARACTER INFORMATION ====================================================================

    ### VOICE DIALOG ===================================================================================
    def open_voice_menu(self, character_name):
        """
        Opens the voice settings menu for the specified character.
        """
        current_conversation_method = self.configuration_characters.get_character_data(character_name, "conversation_method")
        dialog = self.create_voice_dialog(current_conversation_method, character_name)
        dialog.exec()

    def create_voice_dialog(self, conversation_method, character_name):
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"

        f_sidebar_title = QtGui.QFont("Inter Tight", 8, QtGui.QFont.Weight.Bold)
        f_sidebar_title.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 1.2)
        f_sidebar_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        current_text_to_speech = self.configuration_characters.get_character_data(character_name, "current_text_to_speech")
        
        voice_type = self.configuration_characters.get_character_data(character_name, "voice_type")
        rvc_enabled = self.configuration_characters.get_character_data(character_name, "rvc_enabled")
        rvc_file = self.configuration_characters.get_character_data(character_name, "rvc_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("tts_selector_title", 'Text-To-Speech Selector'))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setFixedSize(820, 600)

        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #0c0c10;
                color: {_TEXT};
            }}
        """)

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("SidebarFrame")
        sidebar_frame.setFixedWidth(220)
        sidebar_frame.setStyleSheet(f"""
            QFrame#SidebarFrame {{
                background-color: rgba(11, 11, 15, 0.4);
                border: none;
                border-right: 1px solid {_BORDER};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(10, 24, 10, 24)
        sidebar_layout.setSpacing(12)

        menu_title = QLabel(self.translations.get("tts_selector_title_2", "SPEECH ENGINES"))
        menu_title.setFont(f_sidebar_title)
        menu_title.setStyleSheet(f"color: {_TEXT_S}; background: transparent; border: none; padding-left: 14px;")
        sidebar_layout.addWidget(menu_title)

        sidebar_menu = QtWidgets.QListWidget()
        sidebar_menu.setObjectName("SidebarMenu")
        sidebar_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sidebar_menu.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        sidebar_menu.setIconSize(QtCore.QSize(16, 16))
        
        sidebar_menu.setStyleSheet(f"""
            QListWidget#SidebarMenu {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#SidebarMenu::item {{
                color: {_TEXT_S};
                font-family: 'Inter Tight SemiBold', 'Arial';
                font-size: 13px;
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 4px;
                border: 1px solid transparent;
            }}
            QListWidget#SidebarMenu::item:hover {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {_TEXT};
            }}
            QListWidget#SidebarMenu::item:selected {{
                background-color: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                color: #FFFFFF;
                font-weight: bold;
            }}
        """)

        provider_state = self.configuration_settings.get_main_setting("tts_providers") or {}
        cloud_tokens = {
            "ElevenLabs": "ELEVENLABS_API_TOKEN",
            "Inworld": "INWORLD_API_TOKEN",
        }

        def provider_is_ready(provider_name):
            saved_state = provider_state.get(provider_name, {})
            if provider_name in cloud_tokens:
                return bool(self.configuration_api.get_token(cloud_tokens[provider_name]))
            return True

        engines_data = [("None", "Nothing", "app/gui/icons/none.png")]
        for display_name, provider_name, icon_path in (
            ("ElevenLabs", "ElevenLabs", "app/gui/icons/tts_logo/elevenlabs.png"),
            ("XTTSv2", "XTTSv2", "app/gui/icons/tts_logo/xttsv2.png"),
            ("Edge TTS", "Edge TTS", "app/gui/icons/tts_logo/edgetts.png"),
            ("Kokoro", "Kokoro", "app/gui/icons/tts_logo/kokorotts.png"),
            ("Silero (RU)", "Silero", "app/gui/icons/tts_logo/silerotts.png"),
            ("Qwen-3 TTS", "Qwen-3 TTS", "app/gui/icons/tts_logo/qwentts.png"),
            ("Inworld", "Inworld", "app/gui/icons/tts_logo/elevenlabs.png"),
        ):
            if provider_is_ready(provider_name):
                engines_data.append((display_name, provider_name, icon_path))

        for name, _provider_name, icon_path in engines_data:
            item = QtWidgets.QListWidgetItem(name)
            item.setIcon(QtGui.QIcon(icon_path))
            sidebar_menu.addItem(item)

        sidebar_layout.addWidget(sidebar_menu)
        main_layout.addWidget(sidebar_frame)

        content_frame = QFrame()
        content_frame.setObjectName("ContentFrame")
        content_frame.setStyleSheet("QFrame#ContentFrame { background: transparent; border: none; }")
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 24, 30, 24)
        content_layout.setSpacing(0)

        stacked_widget = QStackedWidget(content_frame)
        stacked_widget.setStyleSheet("background: transparent; border: none;")
        
        widget_factories = {
            "Nothing": lambda: self.create_voice_nothing_widgets(character_name),
            "ElevenLabs": lambda: self.create_elevenlabs_widgets(character_name),
            "XTTSv2": lambda: self.create_xttsv2_widgets(character_name, voice_type, rvc_enabled, rvc_file),
            "Edge TTS": lambda: self.create_edge_tts_widgets(character_name, voice_type, rvc_enabled, rvc_file, stacked_widget),
            "Kokoro": lambda: self.create_kokoro_widgets(character_name, voice_type, rvc_enabled, rvc_file),
            "Silero": lambda: self.create_silero_widgets(character_name, voice_type, rvc_enabled, rvc_file),
            "Qwen-3 TTS": lambda: self.create_qwen3_widgets(character_name, voice_type, rvc_enabled, rvc_file),
            "Inworld": lambda: self.create_inworld_widgets(character_name),
        }
        for _display_name, provider_name, _icon_path in engines_data:
            stacked_widget.addWidget(widget_factories[provider_name]())
        
        content_layout.addWidget(stacked_widget)
        main_layout.addWidget(content_frame, 1)

        sidebar_menu.currentRowChanged.connect(stacked_widget.setCurrentIndex)

        self.set_initial_sidebar_selection(
            current_text_to_speech,
            sidebar_menu,
            {provider_name: index for index, (_display_name, provider_name, _icon_path) in enumerate(engines_data)},
        )

        dialog.setLayout(main_layout)
        return dialog

    def set_initial_sidebar_selection(self, current_text_to_speech, sidebar_menu, engine_map=None):
        row_idx = (engine_map or {}).get(current_text_to_speech, 0)
        sidebar_menu.setCurrentRow(row_idx)
    
    def _create_rvc_params_widget(self, character_name):
        f0up_key   = self.configuration_characters.get_character_data(character_name, "rvc_f0up_key")  or 0
        index_rate = self.configuration_characters.get_character_data(character_name, "rvc_index_rate") or 0.75
        protect    = self.configuration_characters.get_character_data(character_name, "rvc_protect")    or 0.5

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)

        title = QLabel("RVC Advanced Parameters")
        title.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px; font-weight: bold; margin-bottom: 4px;")
        layout.addWidget(title)

        slider_style = """
            QSlider::groove:horizontal {
                height: 4px; background: rgba(255,255,255,0.15); border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #ffffff; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px;
            }
            QSlider::sub-page:horizontal { background: rgba(255,255,255,0.6); border-radius: 2px; }
        """
        label_style = "color: rgba(255,255,255,0.85); font-size: 11px;"

        def _make_row(label_text, min_val, max_val, current_val, decimals=1, scale=1):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(label_style)
            lbl.setFixedWidth(110)
            row.addWidget(lbl)

            slider = QSlider(QtCore.Qt.Orientation.Horizontal)
            slider.setRange(int(min_val * scale), int(max_val * scale))
            slider.setValue(int(current_val * scale))
            slider.setStyleSheet(slider_style)
            row.addWidget(slider)

            val_label = QLabel(f"{current_val:.{decimals}f}")
            val_label.setStyleSheet("color: white; font-size: 11px; min-width: 38px;")
            val_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            row.addWidget(val_label)

            slider.valueChanged.connect(lambda v: val_label.setText(f"{v / scale:.{decimals}f}"))
            return row, slider

        # --- Pitch shift (f0up_key): -12 .. +12, step 1 ---
        row0, slider_f0 = _make_row("Pitch (f0up_key):", -12, 12, f0up_key, decimals=0, scale=1)
        slider_f0.setRange(-12, 12)
        slider_f0.setValue(int(f0up_key))
        layout.addLayout(row0)

        # --- Index Rate: 0.0 .. 1.0, step 0.01 ---
        row1, slider_idx = _make_row("Index Rate:", 0, 1, float(index_rate), decimals=2, scale=100)
        layout.addLayout(row1)

        # --- Protect: 0.0 .. 0.5, step 0.01 ---
        row2, slider_prt = _make_row("Protect:", 0, 0.5, float(protect), decimals=2, scale=100)
        slider_prt.setRange(0, 50)
        slider_prt.setValue(int(float(protect) * 100))
        layout.addLayout(row2)

        def get_values():
            return {
                "rvc_f0up_key":   slider_f0.value(),
                "rvc_index_rate": slider_idx.value() / 100,
                "rvc_protect":    slider_prt.value() / 100,
            }

        container.get_rvc_params = get_values
        return container

    def create_voice_nothing_widgets(self, character_name):
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        layout = QVBoxLayout()

        save_button = QPushButton(self.translations.get("tts_selector_save_button", 'Save Selection'))
        save_button.setFont(f_btn)
        save_button.setFixedHeight(40)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(save_button, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        def save_voice_mode_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_voice_settings_title", "Voice Settings"),
                text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"),
                msg_type="success"
            )

        save_button.clicked.connect(save_voice_mode_settings)

        widget = QWidget()
        widget.setLayout(layout)
        
        return widget

    def create_elevenlabs_widgets(self, character_name):
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        input_style = (
            f"QLineEdit {{"
            f"  background-color: {_SURF3};"
            f"  color: {_TEXT};"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 10px;"
            f"  selection-background-color: {_BLUE_MUT};"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {_BORDER_M};"
            f"  background-color: {_SURF2};"
            f"}}"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        elevenlabs_label = QLabel(self.translations.get("tts_selector_elevenlabs", "ElevenLabs Configuration"))
        elevenlabs_label.setFont(f_title)
        elevenlabs_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        elevenlabs_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(elevenlabs_label)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(10)

        lbl_voice_id = QLabel("VOICE ID")
        lbl_voice_id.setFont(f_label)
        lbl_voice_id.setStyleSheet(lbl_style)
        
        voice_id_input = QtWidgets.QLineEdit()
        voice_id_input.setFont(f_input)
        voice_id_input.setPlaceholderText(self.translations.get("tts_selector_elevenlabs_3", 'Enter Voice ID from ElevenLabs'))
        voice_id_input.setStyleSheet(input_style)

        elevenlabs_voice_id = self.configuration_characters.get_character_data(character_name, "elevenlabs_voice_id")
        if elevenlabs_voice_id:
            voice_id_input.setText(elevenlabs_voice_id)

        gen_layout.addWidget(lbl_voice_id)
        gen_layout.addWidget(voice_id_input)
        layout.addWidget(gen_card)

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        select_voice_button.clicked.connect(lambda: self.select_voice("ElevenLabs", character_name, voice_id_input.text()))

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    async def fetch_inworld_voices(self, api_key):
        if not api_key:
            return []
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.get("https://api.inworld.ai/voices/v1/voices", headers={"Authorization": f"Basic {api_key}"}) as response:
                    if response.status != 200:
                        logger.error("Inworld voices request failed with status %s", response.status)
                        return []
                    data = await response.json()
        except (aiohttp.ClientError, ValueError):
            logger.error("Inworld voices request failed")
            return []
        return [(voice.get("displayName") or voice_id, voice_id) for voice in data.get("voices", []) if (voice_id := voice.get("voiceId"))]

    async def preview_inworld_voice(self, api_key, voice_id, model_id, text=None):
        if not api_key or not voice_id or not model_id:
            return None
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                params = {"voice_id": voice_id, "model_id": model_id}
                if text:
                    params["text"] = text
                async with session.get("https://api.inworld.ai/tts/v1/voice:preview", params=params, headers={"Authorization": f"Basic {api_key}"}) as response:
                    if response.status != 200:
                        logger.error("Inworld preview request failed with status %s", response.status)
                        return None
                    audio_content = (await response.json()).get("audioContent")
            return base64.b64decode(audio_content, validate=True) if audio_content else None
        except (aiohttp.ClientError, ValueError):
            logger.error("Inworld preview request failed")
            return None

    def _global_inworld_api_key(self):
        token = self.ui.tts_provider_api_keys.get("Inworld")
        return token[1].text().strip() if token else None

    async def load_global_inworld_voices(self):
        api_key = self._global_inworld_api_key()
        if not api_key:
            return
        voices = await self.fetch_inworld_voices(api_key)
        if not voices:
            return
        combo = self.ui.comboBox_tts_inworld_voice
        selected = combo.currentData() or combo.currentText().strip()
        combo.clear()
        for display_name, voice_id in voices:
            combo.addItem(f"{display_name} ({voice_id})", voice_id)
        combo.setCurrentIndex(max(combo.findData(selected), 0))

    async def preview_global_inworld_voice(self):
        api_key = self._global_inworld_api_key()
        voice_combo = self.ui.comboBox_tts_inworld_voice
        voice_id = voice_combo.currentData() or voice_combo.currentText().strip()
        audio = await self.preview_inworld_voice(
            api_key,
            voice_id,
            self.ui.comboBox_tts_inworld_model.currentText().strip(),
            self.translations.get(
                "tts_inworld_preview_text_ru" if self.ui.comboBox_tts_inworld_preview_language.currentText() == "RU" else "tts_inworld_preview_text_en",
                "Привет! Это нейтральная проверка голоса." if self.ui.comboBox_tts_inworld_preview_language.currentText() == "RU" else "Hello! This is a neutral voice check.",
            ),
        )
        if not audio:
            return
        output_dir = "app/voices/inworld_audio"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"preview_{uuid.uuid4().hex}.mp3")
        with open(output_file, "wb") as preview_file:
            preview_file.write(audio)
        self.playback_worker.add_audio_file(output_file)

    def create_inworld_widgets(self, character_name):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel(self.translations.get("tts_selector_inworld", "Inworld TTS Configuration"))
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet("QFrame { background-color: rgba(255, 255, 255, 0.015); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; }")
        form = QFormLayout(card)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(10)

        character = self.configuration_characters.load_configuration()["character_list"].get(character_name, {})
        inworld_defaults = (self.configuration_settings.get_main_setting("tts_providers") or {}).get("Inworld", {})
        combo_style = "QComboBox { background-color: rgba(30, 30, 35, 0.5); color: #DEDAD2; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 8px 12px; } QComboBox:hover { border-color: rgba(255, 255, 255, 0.25); }"
        voice_combo = QtWidgets.QComboBox()
        voice_combo.setEditable(True)
        voice_combo.setStyleSheet(combo_style)
        voice_combo.setCurrentText(character.get("inworld_voice_id") or inworld_defaults.get("default_voice_id", "Dennis"))
        model_combo = QtWidgets.QComboBox()
        model_combo.setEditable(True)
        model_combo.setStyleSheet(combo_style)
        model_combo.addItems(["inworld-tts-1.5-mini", "inworld-tts-1.5-max", "inworld-tts-2"])
        model_combo.setCurrentText(character.get("inworld_model_id") or inworld_defaults.get("default_model_id", "inworld-tts-2"))

        form.addRow(self.translations.get("tts_selector_inworld_voice_label", "VOICE ID"), voice_combo)
        form.addRow(self.translations.get("tts_selector_inworld_model_label", "MODEL ID"), model_combo)
        load_voices_button = QPushButton(self.translations.get("tts_selector_inworld_load_voices", "Load voices"))
        load_voices_button.setFixedHeight(36)
        form.addRow("", load_voices_button)
        layout.addWidget(card)
        layout.addStretch(1)

        save_button = QPushButton(self.translations.get("tts_selector_save_button", "Save Selection"))
        save_button.setFixedHeight(40)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet("QPushButton { background: rgba(75, 184, 255, 0.12); border: 1px solid rgba(75, 184, 255, 0.25); border-radius: 8px; color: #4BB8FF; font-weight: bold; } QPushButton:hover { background: rgba(75, 184, 255, 0.25); }")
        preview_button = QPushButton(self.translations.get("tts_selector_inworld_preview", "Preview voice"))
        preview_button.setFixedHeight(40)
        preview_button.setCursor(Qt.CursorShape.PointingHandCursor)
        preview_button.setStyleSheet(save_button.styleSheet())
        layout.addWidget(preview_button)
        layout.addWidget(save_button)

        def current_api_key():
            return self.configuration_api.get_token("INWORLD_API_TOKEN")

        def selected_voice_id():
            return voice_combo.currentData() or voice_combo.currentText().strip()

        async def load_voices():
            key = current_api_key()
            if not key:
                sow_toast(parent=self.main_window, title="Inworld TTS", text=self.translations.get("tts_selector_inworld_provider_required", "Enable Inworld and add its API key in Voice Settings."), msg_type="error")
                return
            voices = await self.fetch_inworld_voices(key)
            if not voices:
                sow_toast(parent=self.main_window, title="Inworld TTS", text=self.translations.get("tts_selector_inworld_voices_failed", "Could not load voices. Check the API key."), msg_type="error")
                return
            selected = selected_voice_id()
            voice_combo.clear()
            for display_name, voice_id in voices:
                voice_combo.addItem(f"{display_name} ({voice_id})", voice_id)
            index = voice_combo.findData(selected)
            voice_combo.setCurrentIndex(index if index >= 0 else 0)

        async def preview_voice():
            audio = await self.preview_inworld_voice(current_api_key(), selected_voice_id(), model_combo.currentText().strip())
            if not audio:
                sow_toast(parent=self.main_window, title="Inworld TTS", text=self.translations.get("tts_selector_inworld_preview_failed", "Could not preview this voice."), msg_type="error")
                return
            output_dir = "app/voices/inworld_audio"
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"preview_{uuid.uuid4().hex}.mp3")
            with open(output_file, "wb") as preview_file:
                preview_file.write(audio)
            self.playback_worker.add_audio_file(output_file)

        load_voices_button.clicked.connect(lambda: asyncio.create_task(load_voices()))
        preview_button.clicked.connect(lambda: asyncio.create_task(preview_voice()))

        def save_inworld_settings():
            voice_id = selected_voice_id()
            model_id = model_combo.currentText().strip()
            api_key = current_api_key()
            if not voice_id or not model_id or not api_key:
                sow_toast(parent=self.main_window, title="Inworld TTS", text=self.translations.get("tts_selector_inworld_provider_required", "Enable Inworld and add its API key in Voice Settings."), msg_type="error")
                return

            config = self.configuration_characters.load_configuration()
            character = config["character_list"][character_name]
            character["current_text_to_speech"] = "Inworld"
            character["inworld_voice_id"] = voice_id
            character["inworld_model_id"] = model_id
            self.configuration_characters.save_configuration_edit(config)
            sow_toast(parent=self.main_window, title="Inworld TTS", text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"), msg_type="success")

        save_button.clicked.connect(save_inworld_settings)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_xttsv2_widgets(self, character_name, voice_type, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 8px 12px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        xtts_label = QLabel(self.translations.get("tts_selector_xttsv2", 'XTTSv2 Configuration'))
        xtts_label.setFont(f_title)
        xtts_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        xtts_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(xtts_label)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        lbl_voice = QLabel(self.translations.get("tts_selector_xttsv2_lbl_1", "SELECT SPEAKER MODEL"))
        lbl_voice.setFont(f_label)
        lbl_voice.setStyleSheet(lbl_style)
        
        voice_type_combo = QtWidgets.QComboBox()
        voice_type_combo.setFont(f_input)
        voice_type_combo.setStyleSheet(combo_style)
        voice_type_combo.addItems([
            self.translations.get("tts_selector_xttsv2_male", "Male"), 
            self.translations.get("tts_selector_xttsv2_female", "Female"), 
            self.translations.get("tts_selector_xttsv2_calm_female", "Female Calm")
        ])
        
        gen_layout.addWidget(lbl_voice)
        gen_layout.addWidget(voice_type_combo)
        layout.addWidget(gen_card)

        if voice_type:
            voice_type_combo.setCurrentText(voice_type)

        rvc_card = QFrame()
        rvc_card.setObjectName("RvcCard")
        rvc_card.setStyleSheet(f"QFrame#RvcCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        rvc_layout = QVBoxLayout(rvc_card)
        rvc_layout.setContentsMargins(12, 10, 12, 10)
        rvc_layout.setSpacing(10)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        rvc_checkbox.setFont(f_input)
        rvc_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rvc_layout.addWidget(rvc_checkbox)

        rvc_params_container = QWidget()
        rvc_params_container.setStyleSheet("background: transparent; border: none;")
        rvc_params_layout = QVBoxLayout(rvc_params_container)
        rvc_params_layout.setContentsMargins(0, 5, 0, 0)
        rvc_params_layout.setSpacing(10)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setFont(f_input)
        rvc_file_combo.setStyleSheet(combo_style)
        rvc_params_layout.addWidget(rvc_file_combo)

        rvc_params_widget = self._create_rvc_params_widget(character_name)
        rvc_params_layout.addWidget(rvc_params_widget)
        rvc_params_container.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_container)
        layout.addWidget(rvc_card)

        is_rvc_active = bool(rvc_enabled)
        rvc_checkbox.setChecked(is_rvc_active)
        rvc_params_container.setVisible(is_rvc_active)

        def toggle_rvc(checked):
            rvc_params_container.setVisible(checked)
            layout.invalidate()

        rvc_checkbox.toggled.connect(toggle_rvc)

        def populate_rvc_folders():
            rvc_file_combo.clear()
            selected_index = -1
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                if folders:
                    rvc_file_combo.addItems(folders)
                    if file_name:
                        try:
                            folder_name = os.path.basename(os.path.dirname(file_name))
                            selected_index = folders.index(folder_name)
                        except ValueError:
                            selected_index = -1
                else:
                    rvc_file_combo.addItem(self.translations.get("tts_selector_no_folders", "No folders found"))
            else:
                rvc_file_combo.addItem(self.translations.get("tts_selector_invalid_rvc", "Invalid RVC directory"))

            if selected_index >= 0:
                rvc_file_combo.setCurrentIndex(selected_index)
        
        populate_rvc_folders()

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        def save_xttsv2_settings():
            voice_type = voice_type_combo.currentText()
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = (
                os.path.join(RVC_DIR, rvc_file_combo.currentText())
                if rvc_enabled and rvc_file_combo.currentText() and rvc_file_combo.isEnabled()
                else None
            )

            if rvc_enabled and (not rvc_folder or "No folders found" in rvc_folder):
                sow_toast(
                    parent=self.main_window,
                    title="RVC System",
                    text=self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"),
                    msg_type="error"
                )
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    sow_toast(
                        parent=self.main_window,
                        title="RVC System",
                        text=self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder,
                        msg_type="error",
                        duration=6000
                    )
                    return
            
            rvc_params = {}
            if rvc_params_widget is not None:
                rvc_params = rvc_params_widget.get_rvc_params()

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "XTTSv2"

            configuration_data["character_list"][character_name]["rvc_f0up_key"]    = rvc_params.get("rvc_f0up_key",   0)
            configuration_data["character_list"][character_name]["rvc_index_rate"]  = rvc_params.get("rvc_index_rate", 0.75)
            configuration_data["character_list"][character_name]["rvc_protect"]     = rvc_params.get("rvc_protect",    0.5)

            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_voice_settings_title", "Voice Settings"),
                text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"),
                msg_type="success"
            )

        select_voice_button.clicked.connect(save_xttsv2_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    def extract_edge_tts_voice_name(self, full_voice_name):
        match = re.search(r"\((\w+-\w+),\s*(\w+)\)", full_voice_name)
        if match:
            locale, voice_name = match.groups()
            return f"{locale}-{voice_name}"
        return full_voice_name

    def create_edge_tts_widgets(self, character_name, voice_type, rvc_enabled, file_name, stacked_widget):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 8px 12px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        edge_tts_label = QLabel(self.translations.get("tts_selector_edge", 'Choose voice type for Edge TTS'))
        edge_tts_label.setFont(f_title)
        edge_tts_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        edge_tts_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(edge_tts_label)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QHBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 10, 12, 10)
        gen_layout.setSpacing(15)

        lang_layout = QVBoxLayout()
        lang_layout.setSpacing(4)
        lbl_lang = QLabel(self.translations.get("tts_selector_edge_tts_lbl_1", "LANGUAGE"))
        lbl_lang.setFont(f_label)
        lbl_lang.setStyleSheet(lbl_style)
        language_combo = QtWidgets.QComboBox()
        language_combo.setFont(f_input)
        language_combo.setStyleSheet(combo_style)
        language_combo.addItems(["English", "Russian"])
        lang_layout.addWidget(lbl_lang)
        lang_layout.addWidget(language_combo)

        voice_layout = QVBoxLayout()
        voice_layout.setSpacing(4)
        lbl_voice = QLabel(self.translations.get("tts_selector_edge_tts_lbl_2", "SPEAKER VOICE"))
        lbl_voice.setFont(f_label)
        lbl_voice.setStyleSheet(lbl_style)
        voice_combo = QtWidgets.QComboBox()
        voice_combo.setFont(f_input)
        voice_combo.setStyleSheet(combo_style)
        voice_layout.addWidget(lbl_voice)
        voice_layout.addWidget(voice_combo)

        gen_layout.addLayout(lang_layout, 1)
        gen_layout.addLayout(voice_layout, 2)
        layout.addWidget(gen_card)

        if voice_type:
            voice_combo.setCurrentText(voice_type)

        async def populate_voices():
            if voice_combo.isVisible():
                try:
                    selected_language = language_combo.currentText().lower()
                    voices_manager = edge_tts.VoicesManager()
                    voices = await voices_manager.create()

                    filtered_voices = [
                        self.extract_edge_tts_voice_name(voice["Name"])
                        for voice in voices.voices
                        if voice["Locale"].startswith(selected_language[:2])
                    ]
                    voice_combo.clear()
                    voice_combo.addItems(filtered_voices)
                except Exception as e:
                    logger.error(f"Error loading voices: {e}")

        def on_stacked_widget_changed(index):
            if index == 3:
                asyncio.create_task(populate_voices())

        stacked_widget.currentChanged.connect(on_stacked_widget_changed)
        language_combo.currentIndexChanged.connect(lambda: asyncio.create_task(populate_voices()))

        rvc_card = QFrame()
        rvc_card.setObjectName("RvcCard")
        rvc_card.setStyleSheet(f"QFrame#RvcCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        rvc_layout = QVBoxLayout(rvc_card)
        rvc_layout.setContentsMargins(12, 10, 12, 10)
        rvc_layout.setSpacing(10)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        rvc_checkbox.setFont(f_input)
        rvc_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rvc_layout.addWidget(rvc_checkbox)

        rvc_params_container = QWidget()
        rvc_params_container.setStyleSheet("background: transparent; border: none;")
        rvc_params_layout = QVBoxLayout(rvc_params_container)
        rvc_params_layout.setContentsMargins(0, 5, 0, 0)
        rvc_params_layout.setSpacing(10)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setFont(f_input)
        rvc_file_combo.setStyleSheet(combo_style)
        rvc_params_layout.addWidget(rvc_file_combo)

        rvc_params_widget = self._create_rvc_params_widget(character_name)
        rvc_params_layout.addWidget(rvc_params_widget)
        rvc_params_container.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_container)
        layout.addWidget(rvc_card)

        is_rvc_active = bool(rvc_enabled)
        rvc_checkbox.setChecked(is_rvc_active)
        rvc_params_container.setVisible(is_rvc_active)

        def toggle_rvc(checked):
            rvc_params_container.setVisible(checked)
            layout.invalidate()

        rvc_checkbox.toggled.connect(toggle_rvc)

        def populate_rvc_folders():
            rvc_file_combo.clear()
            selected_index = -1
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                if folders:
                    rvc_file_combo.addItems(folders)
                    if file_name:
                        try:
                            folder_name = os.path.basename(os.path.dirname(file_name))
                            selected_index = folders.index(folder_name)
                        except ValueError:
                            selected_index = -1
                else:
                    rvc_file_combo.addItem(self.translations.get("tts_selector_no_folders", "No folders found"))
            else:
                rvc_file_combo.addItem(self.translations.get("tts_selector_invalid_rvc", "Invalid RVC directory"))

            if selected_index >= 0:
                rvc_file_combo.setCurrentIndex(selected_index)
        
        populate_rvc_folders()

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        def save_edge_tts_settings():
            voice_type = voice_combo.currentText()
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = (
                os.path.join(RVC_DIR, rvc_file_combo.currentText())
                if rvc_enabled and rvc_file_combo.currentText() and rvc_file_combo.isEnabled()
                else None
            )

            if rvc_enabled and (not rvc_folder or "No folders found" in rvc_folder):
                sow_toast(
                    parent=self.main_window,
                    title="RVC System",
                    text=self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"),
                    msg_type="error"
                )
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    sow_toast(
                        parent=self.main_window,
                        title="RVC System",
                        text=self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder,
                        msg_type="error",
                        duration=6000
                    )
                    return

            rvc_params = {}
            if rvc_params_widget is not None:
                rvc_params = rvc_params_widget.get_rvc_params()

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Edge TTS"

            configuration_data["character_list"][character_name]["rvc_f0up_key"]    = rvc_params.get("rvc_f0up_key",   0)
            configuration_data["character_list"][character_name]["rvc_index_rate"]  = rvc_params.get("rvc_index_rate", 0.75)
            configuration_data["character_list"][character_name]["rvc_protect"]     = rvc_params.get("rvc_protect",    0.5)

            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_voice_settings_title", "Voice Settings"),
                text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"),
                msg_type="success"
            )

        select_voice_button.clicked.connect(save_edge_tts_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_kokoro_widgets(self, character_name, voice_name, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        _SURF1    = "rgba(0, 0, 0, 0.3)"
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 8px 12px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        kokoro_label = QLabel(self.translations.get("tts_selector_kokoro", "Choose voice for Kokoro"))
        kokoro_label.setFont(f_title)
        kokoro_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        kokoro_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(kokoro_label)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        lbl_voice = QLabel(self.translations.get("tts_selector_kokoro_lbl_1", "SELECT KOKORO SPEAKER"))
        lbl_voice.setFont(f_label)
        lbl_voice.setStyleSheet(lbl_style)
        
        voice_name_combo = QtWidgets.QComboBox()
        voice_name_combo.setFont(f_input)
        voice_name_combo.setStyleSheet(combo_style)
        voice_name_combo.addItems([
            "af_heart", "af_bella", "af_nicole", "af_aoede", 
            "af_kore", "af_sarah", "af_nova", "am_fenrir", 
            "am_michael", "am_puck", "bf_emma", "bf_isabella", 
            "bm_fable", "bm_george", "jf_alpha", "jf_gongitsune", 
            "jm_kumo", "zf_xiaobei", "zf_xiaoni", "zm_yunjian", "zm_yunxi"
        ])
        
        gen_layout.addWidget(lbl_voice)
        gen_layout.addWidget(voice_name_combo)
        layout.addWidget(gen_card)

        if voice_name:
            voice_name_combo.setCurrentText(voice_name)

        rvc_card = QFrame()
        rvc_card.setObjectName("RvcCard")
        rvc_card.setStyleSheet(f"QFrame#RvcCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        rvc_layout = QVBoxLayout(rvc_card)
        rvc_layout.setContentsMargins(12, 10, 12, 10)
        rvc_layout.setSpacing(10)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        rvc_checkbox.setFont(f_input)
        rvc_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rvc_layout.addWidget(rvc_checkbox)

        rvc_params_container = QWidget()
        rvc_params_container.setStyleSheet("background: transparent; border: none;")
        rvc_params_layout = QVBoxLayout(rvc_params_container)
        rvc_params_layout.setContentsMargins(0, 5, 0, 0)
        rvc_params_layout.setSpacing(10)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setFont(f_input)
        rvc_file_combo.setStyleSheet(combo_style)
        rvc_params_layout.addWidget(rvc_file_combo)

        rvc_params_widget = self._create_rvc_params_widget(character_name)
        rvc_params_layout.addWidget(rvc_params_widget)
        rvc_params_container.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_container)
        layout.addWidget(rvc_card)

        is_rvc_active = bool(rvc_enabled)
        rvc_checkbox.setChecked(is_rvc_active)
        rvc_params_container.setVisible(is_rvc_active)

        def toggle_rvc(checked):
            rvc_params_container.setVisible(checked)
            layout.invalidate()

        rvc_checkbox.toggled.connect(toggle_rvc)

        def populate_rvc():
            rvc_file_combo.clear()
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                rvc_file_combo.addItems(folders)
                if file_name:
                    try:
                        folder_name = os.path.basename(os.path.dirname(file_name))
                        if folder_name in folders:
                            rvc_file_combo.setCurrentText(folder_name)
                    except:
                        pass
        populate_rvc()

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        def save_kokoro_settings():
            voice_type = voice_name_combo.currentText()
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = (
                os.path.join(RVC_DIR, rvc_file_combo.currentText())
                if rvc_enabled and rvc_file_combo.currentText() and rvc_file_combo.isEnabled()
                else None
            )

            if rvc_enabled and (not rvc_folder or "No folders found" in rvc_folder):
                sow_toast(
                    parent=self.main_window,
                    title="RVC System",
                    text=self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"),
                    msg_type="error"
                )
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    sow_toast(
                        parent=self.main_window,
                        title="RVC System",
                        text=self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder,
                        msg_type="error",
                        duration=6000
                    )
                    return

            rvc_params = {}
            if rvc_params_widget is not None:
                rvc_params = rvc_params_widget.get_rvc_params()

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Kokoro"

            configuration_data["character_list"][character_name]["rvc_f0up_key"]    = rvc_params.get("rvc_f0up_key",   0)
            configuration_data["character_list"][character_name]["rvc_index_rate"]  = rvc_params.get("rvc_index_rate", 0.75)
            configuration_data["character_list"][character_name]["rvc_protect"]     = rvc_params.get("rvc_protect",    0.5)

            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_voice_settings_title", "Voice Settings"),
                text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"),
                msg_type="success"
            )

        select_voice_button.clicked.connect(save_kokoro_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_silero_widgets(self, character_name, voice_name, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")
        
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        silero_label = QLabel(self.translations.get("tts_selector_silero", "Choose voice for Silero"))
        silero_label.setFont(f_title)
        silero_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        silero_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(silero_label)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        lbl_voice = QLabel(self.translations.get("tts_selector_silero_lbl_1", "SELECT RUSSIAN SPEAKER"))
        lbl_voice.setFont(f_label)
        lbl_voice.setStyleSheet(lbl_style)
        
        voice_name_combo = QtWidgets.QComboBox()
        voice_name_combo.setFont(f_input)
        voice_name_combo.setStyleSheet(combo_style)
        voice_name_combo.addItems([
            "aidar", "baya", "kseniya", "xenia", "eugene"
        ])
        
        gen_layout.addWidget(lbl_voice)
        gen_layout.addWidget(voice_name_combo)
        layout.addWidget(gen_card)

        if voice_name and voice_name in ["aidar", "baya", "kseniya", "xenia", "eugene"]:
            voice_name_combo.setCurrentText(voice_name)
        else:
            voice_name_combo.setCurrentText("xenia")

        rvc_card = QFrame()
        rvc_card.setObjectName("RvcCard")
        rvc_card.setStyleSheet(f"QFrame#RvcCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        rvc_layout = QVBoxLayout(rvc_card)
        rvc_layout.setContentsMargins(12, 10, 12, 10)
        rvc_layout.setSpacing(10)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        rvc_checkbox.setFont(f_input)
        rvc_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rvc_layout.addWidget(rvc_checkbox)

        rvc_params_container = QWidget()
        rvc_params_container.setStyleSheet("background: transparent; border: none;")
        rvc_params_layout = QVBoxLayout(rvc_params_container)
        rvc_params_layout.setContentsMargins(0, 5, 0, 0)
        rvc_params_layout.setSpacing(10)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setFont(f_input)
        rvc_file_combo.setStyleSheet(combo_style)
        rvc_params_layout.addWidget(rvc_file_combo)

        rvc_params_widget = self._create_rvc_params_widget(character_name)
        rvc_params_layout.addWidget(rvc_params_widget)
        rvc_params_container.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_container)
        layout.addWidget(rvc_card)

        is_rvc_active = bool(rvc_enabled)
        rvc_checkbox.setChecked(is_rvc_active)
        rvc_params_container.setVisible(is_rvc_active)

        def toggle_rvc(checked):
            rvc_params_container.setVisible(checked)
            layout.invalidate()

        rvc_checkbox.toggled.connect(toggle_rvc)

        def populate_rvc():
            rvc_file_combo.clear()
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                rvc_file_combo.addItems(folders)
                if file_name:
                    try:
                        folder_name = os.path.basename(os.path.dirname(file_name))
                        if folder_name in folders:
                            rvc_file_combo.setCurrentText(folder_name)
                    except:
                        pass
        populate_rvc()

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        def save_silero_settings():
            voice_type = voice_name_combo.currentText()
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = os.path.join(RVC_DIR, rvc_file_combo.currentText()) if rvc_enabled and rvc_file_combo.currentText() else None
            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = os.path.join(rvc_folder, pth_files[0])

            rvc_params = rvc_params_widget.get_rvc_params() if rvc_params_widget else {}

            configuration_data = self.configuration_characters.load_configuration()
            char_cfg = configuration_data["character_list"][character_name]
            
            char_cfg["voice_type"] = voice_type
            char_cfg["rvc_enabled"] = rvc_enabled
            char_cfg["rvc_file"] = rvc_file
            char_cfg["current_text_to_speech"] = "Silero"

            char_cfg["rvc_f0up_key"]    = rvc_params.get("rvc_f0up_key",   0)
            char_cfg["rvc_index_rate"]  = rvc_params.get("rvc_index_rate", 0.75)
            char_cfg["rvc_protect"]     = rvc_params.get("rvc_protect",    0.5)

            self.configuration_characters.save_configuration_edit(configuration_data)
            sow_toast(parent=self.main_window, title="Voice Settings", text="Silero settings saved successfully!", msg_type="success")

        select_voice_button.clicked.connect(save_silero_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_qwen3_widgets(self, character_name, voice_name, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        # ==============================================================================
        _SURF1    = "rgba(0, 0, 0, 0.3)"
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        input_style = (
            f"QLineEdit {{"
            f"  background-color: {_SURF3};"
            f"  color: {_TEXT};"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 10px;"
            f"  selection-background-color: {_BLUE_MUT};"
            f"}}"
            f"QLineEdit:focus {{"
            f"  border-color: {_BORDER_M};"
            f"  background-color: {_SURF2};"
            f"}}"
        )

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 8px 12px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 4px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """
        # ==============================================================================

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        qwen_label = QLabel(self.translations.get("tts_selector_qwen3", "Qwen 3 TTS Configuration"))
        qwen_label.setFont(f_title)
        qwen_label.setStyleSheet("color: #ffffff; font-weight: bold; background: transparent; border: none;")
        qwen_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(qwen_label)

        sys_settings_card = QFrame()
        sys_settings_card.setObjectName("SysCard")
        sys_settings_card.setStyleSheet(f"QFrame#SysCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        sys_layout = QHBoxLayout(sys_settings_card)
        sys_layout.setContentsMargins(12, 10, 12, 10)
        sys_layout.setSpacing(15)

        size_layout = QVBoxLayout()
        size_layout.setSpacing(4)
        model_size_label = QLabel(self.translations.get("tts_selector_qwen3_lbl_1", "MODEL SIZE"))
        model_size_label.setFont(f_label)
        model_size_label.setStyleSheet(lbl_style)
        model_size_combo = QtWidgets.QComboBox()
        model_size_combo.setFont(f_input)
        model_size_combo.setStyleSheet(combo_style)
        model_size_combo.addItems(["0.6B (Fast)", "1.7B (High Quality)"])
        size_layout.addWidget(model_size_label)
        size_layout.addWidget(model_size_combo)

        lang_layout = QVBoxLayout()
        lang_layout.setSpacing(4)
        lang_label = QLabel(self.translations.get("tts_selector_qwen3_lbl_2", "LANGUAGE"))
        lang_label.setFont(f_label)
        lang_label.setStyleSheet(lbl_style)
        language_combo = QtWidgets.QComboBox()
        language_combo.setFont(f_input)
        language_combo.setStyleSheet(combo_style)
        language_combo.addItems(["English", "Russian", "Chinese", "Japanese", "Korean", "French", "German", "Spanish"])
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(language_combo)

        device_layout = QVBoxLayout()
        device_layout.setSpacing(4)
        device_label = QLabel(self.translations.get("tts_selector_qwen3_lbl_device", "COMPUTE DEVICE"))
        device_label.setFont(f_label)
        device_label.setStyleSheet(lbl_style)
        device_combo = QtWidgets.QComboBox()
        device_combo.setFont(f_input)
        device_combo.setStyleSheet(combo_style)
        device_combo.addItems(["CUDA (GPU)", "CPU"])
        device_layout.addWidget(device_label)
        device_layout.addWidget(device_combo)

        sys_layout.addLayout(size_layout, 1)
        sys_layout.addLayout(lang_layout, 1)
        sys_layout.addLayout(device_layout, 1)
        layout.addWidget(sys_settings_card)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(10)

        mode_label = QLabel(self.translations.get("tts_qwen_mode", "GENERATION MODE"))
        mode_label.setFont(f_label)
        mode_label.setStyleSheet(lbl_style)
        gen_layout.addWidget(mode_label)

        qwen_mode_combo = QtWidgets.QComboBox()
        qwen_mode_combo.setFont(f_input)
        qwen_mode_combo.setStyleSheet(combo_style)
        qwen_mode_combo.addItems([
            "Preset Voices (CustomVoice)",
            "Voice Design (Prompt)",
            "Voice Cloning (3-Sec Audio)"
        ])
        gen_layout.addWidget(qwen_mode_combo)

        qwen_stack = QtWidgets.QStackedWidget()
        qwen_stack.setStyleSheet("background: transparent; border: none;")
        gen_layout.addWidget(qwen_stack)

        page_presets = QWidget()
        layout_presets = QVBoxLayout(page_presets)
        layout_presets.setContentsMargins(0, 0, 0, 0)
        layout_presets.setSpacing(4)
        lbl_preset = QLabel(self.translations.get("tts_selector_qwen3_lbl_3", "CHOOSE PRESET VOICE"))
        lbl_preset.setFont(f_label)
        lbl_preset.setStyleSheet(lbl_style)
        qwen_preset_combo = QtWidgets.QComboBox()
        qwen_preset_combo.setFont(f_input)
        qwen_preset_combo.setStyleSheet(combo_style)
        qwen_preset_combo.addItems(["Serena", "Vivian", "Aiden", "Dylan", "Eric", "Ryan", "Sophia", "Emma", "Michael"])
        layout_presets.addWidget(lbl_preset)
        layout_presets.addWidget(qwen_preset_combo)
        style_label = QLabel("Style Instruction (optional)")
        style_label.setFont(f_label)
        style_label.setStyleSheet(lbl_style)
        qwen_style_input = QLineEdit()
        qwen_style_input.setPlaceholderText("speak sadly and slowly with deep emotion...")
        qwen_style_input.setStyleSheet(input_style)
        layout_presets.addWidget(style_label)
        layout_presets.addWidget(qwen_style_input)
        qwen_stack.addWidget(page_presets)

        page_prompt = QWidget()
        layout_prompt = QVBoxLayout(page_prompt)
        layout_prompt.setContentsMargins(0, 0, 0, 0)
        layout_prompt.setSpacing(4)
        lbl_prompt = QLabel(self.translations.get("tts_selector_qwen3_lbl_4", "DESCRIBE VOICE IN ENGLISH (PROMPT)"))
        lbl_prompt.setFont(f_label)
        lbl_prompt.setStyleSheet(lbl_style)
        qwen_prompt_input = QtWidgets.QLineEdit()
        qwen_prompt_input.setFont(f_input)
        qwen_prompt_input.setPlaceholderText("Cheerful English woman with a soft and melodic voice...")
        qwen_prompt_input.setStyleSheet(input_style)
        layout_prompt.addWidget(lbl_prompt)
        layout_prompt.addWidget(qwen_prompt_input)
        qwen_stack.addWidget(page_prompt)

        page_cloning = QWidget()
        layout_cloning = QVBoxLayout(page_cloning)
        layout_cloning.setContentsMargins(0, 0, 0, 0)
        layout_cloning.setSpacing(4)
        lbl_cloning = QLabel(self.translations.get("tts_selector_qwen3_lbl_5", "REFERENCE AUDIO FILE (.WAV)"))
        lbl_cloning.setFont(f_label)
        lbl_cloning.setStyleSheet(lbl_style)
        clone_file_row = QHBoxLayout()
        clone_file_row.setSpacing(10)
        qwen_ref_path_input = QtWidgets.QLineEdit()
        qwen_ref_path_input.setFont(f_input)
        qwen_ref_path_input.setReadOnly(True)
        qwen_ref_path_input.setPlaceholderText(self.translations.get("tts_selector_qwen3_lbl_6", "No reference audio selected"))
        qwen_ref_path_input.setStyleSheet(input_style.replace(f"background-color: {_SURF3}", f"background-color: {_SURF1}"))
        btn_browse_ref = QtWidgets.QPushButton()
        btn_browse_ref.setFixedSize(40, 40)
        btn_browse_ref.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_ref.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_browse_ref.setIcon(QtGui.QIcon("app/gui/icons/import.png"))
        btn_browse_ref.setIconSize(QtCore.QSize(18, 18))
        btn_browse_ref.setStyleSheet(f"QPushButton {{ background-color: {_SURF2}; border: 1px solid {_BORDER}; border-radius: 8px; }} QPushButton:hover {{ background-color: {_SURF3}; border-color: {_BORDER_M}; }}")
        
        def browse_ref_audio():
            file_path, _ = QFileDialog.getOpenFileName(None, "Select Reference Audio", "", "WAV Files (*.wav)")
            if file_path:
                qwen_ref_path_input.setText(file_path)

        btn_browse_ref.clicked.connect(browse_ref_audio)
        clone_file_row.addWidget(qwen_ref_path_input, 1)
        clone_file_row.addWidget(btn_browse_ref)
        layout_cloning.addWidget(lbl_cloning)
        layout_cloning.addLayout(clone_file_row)
        qwen_stack.addWidget(page_cloning)

        qwen_mode_combo.currentIndexChanged.connect(qwen_stack.setCurrentIndex)
        layout.addWidget(gen_card)

        rvc_card = QFrame()
        rvc_card.setObjectName("RvcCard")
        rvc_card.setStyleSheet(f"QFrame#RvcCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        rvc_layout = QVBoxLayout(rvc_card)
        rvc_layout.setContentsMargins(12, 10, 12, 10)
        rvc_layout.setSpacing(10)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        rvc_checkbox.setFont(f_input)
        rvc_checkbox.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        rvc_layout.addWidget(rvc_checkbox)

        rvc_params_container = QWidget()
        rvc_params_container.setStyleSheet("background: transparent; border: none;")
        rvc_params_layout = QVBoxLayout(rvc_params_container)
        rvc_params_layout.setContentsMargins(0, 5, 0, 0)
        rvc_params_layout.setSpacing(10)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setFont(f_input)
        rvc_file_combo.setStyleSheet(combo_style)
        rvc_params_layout.addWidget(rvc_file_combo)

        rvc_params_widget = self._create_rvc_params_widget(character_name)
        rvc_params_layout.addWidget(rvc_params_widget)
        rvc_params_container.setLayout(rvc_params_layout)
        rvc_layout.addWidget(rvc_params_container)
        layout.addWidget(rvc_card)

        is_rvc_active = bool(rvc_enabled)
        rvc_checkbox.setChecked(is_rvc_active)
        rvc_params_container.setVisible(is_rvc_active)

        def toggle_rvc(checked):
            rvc_params_container.setVisible(checked)
            layout.invalidate()

        rvc_checkbox.toggled.connect(toggle_rvc)

        def populate_rvc():
            rvc_file_combo.clear()
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                rvc_file_combo.addItems(folders)
                if file_name:
                    try:
                        folder_name = os.path.basename(os.path.dirname(file_name))
                        if folder_name in folders:
                            rvc_file_combo.setCurrentText(folder_name)
                    except:
                        pass
        populate_rvc()

        configuration_data = self.configuration_characters.load_configuration()
        char_config = configuration_data["character_list"].get(character_name, {})

        saved_mode = char_config.get("qwen_mode", "presets")
        saved_size = char_config.get("qwen_model_size", "1.7B")
        saved_prompt = char_config.get("qwen_prompt", "")
        saved_instruct = char_config.get("qwen_style_instruct", "")
        saved_ref = char_config.get("qwen_cloning_ref_path", "")
        saved_language = char_config.get("qwen_language", "English")
        saved_device = char_config.get("qwen_device", "cuda")

        model_size_combo.setCurrentIndex(1 if saved_size == "1.7B" else 0)
        language_combo.setCurrentText(saved_language)
        device_combo.setCurrentIndex(0 if saved_device == "cuda" else 1)

        if saved_mode == "presets":
            qwen_mode_combo.setCurrentIndex(0)
            if voice_name: 
                qwen_preset_combo.setCurrentText(voice_name)
                qwen_style_input.setText(saved_instruct)
        elif saved_mode == "prompt":
            qwen_mode_combo.setCurrentIndex(1)
            qwen_prompt_input.setText(saved_prompt)
        elif saved_mode == "cloning":
            qwen_mode_combo.setCurrentIndex(2)
            qwen_ref_path_input.setText(saved_ref)

        layout.addSpacing(5)
        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Save Qwen 3 Settings'))
        select_voice_button.setFont(f_btn)
        select_voice_button.setFixedHeight(40)
        select_voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(select_voice_button)

        def save_qwen_settings():
            mode_idx = qwen_mode_combo.currentIndex()
            mode_map = {0: "presets", 1: "prompt", 2: "cloning"}
            active_mode = mode_map[mode_idx]

            model_size = "1.7B" if model_size_combo.currentIndex() == 1 else "0.6B"
            selected_language = language_combo.currentText()
            selected_device = "cuda" if device_combo.currentIndex() == 0 else "cpu"

            voice_type = qwen_preset_combo.currentText() if active_mode == "presets" else ""
            prompt_text = qwen_prompt_input.text().strip() if active_mode == "prompt" else ""
            ref_path = qwen_ref_path_input.text().strip() if active_mode == "cloning" else ""

            if active_mode == "prompt" and not prompt_text:
                sow_toast(parent=self.main_window, title="Qwen 3 TTS", text="Voice design prompt cannot be empty!", msg_type="error")
                return
            if active_mode == "cloning" and (not ref_path or not os.path.exists(ref_path)):
                sow_toast(parent=self.main_window, title="Qwen 3 TTS", text="Please select a valid reference .wav file!", msg_type="error")
                return

            # RVC
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = os.path.join(RVC_DIR, rvc_file_combo.currentText()) if rvc_enabled and rvc_file_combo.currentText() else None
            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = os.path.join(rvc_folder, pth_files[0])

            rvc_params = rvc_params_widget.get_rvc_params() if rvc_params_widget else {}

            config = self.configuration_characters.load_configuration()
            char_cfg = config["character_list"][character_name]

            char_cfg["current_text_to_speech"] = "Qwen-3 TTS"
            char_cfg["qwen_model_size"] = model_size
            char_cfg["qwen_mode"] = active_mode
            char_cfg["qwen_language"] = selected_language
            char_cfg["qwen_device"] = selected_device
            char_cfg["voice_type"] = voice_type
            char_cfg["qwen_prompt"] = prompt_text
            char_cfg["qwen_cloning_ref_path"] = ref_path
            char_cfg["qwen_style_instruct"] = qwen_style_input.text().strip() if active_mode == "presets" else ""
            
            char_cfg["rvc_enabled"] = rvc_enabled
            char_cfg["rvc_file"] = rvc_file
            char_cfg["rvc_f0up_key"] = rvc_params.get("rvc_f0up_key", 0)
            char_cfg["rvc_index_rate"] = rvc_params.get("rvc_index_rate", 0.75)
            char_cfg["rvc_protect"] = rvc_params.get("rvc_protect", 0.5)

            self.configuration_characters.save_configuration_edit(config)
            sow_toast(parent=self.main_window, title="Qwen 3 TTS", text="Settings saved successfully!", msg_type="success")

        select_voice_button.clicked.connect(save_qwen_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def select_voice(self, tts_method, character_name, data):
        match tts_method:
            case "ElevenLabs":
                voice_id = data
                
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["elevenlabs_voice_id"] = voice_id
                configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                self.configuration_characters.save_configuration_edit(configuration_data)

                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_voice_settings_title", "Voice Settings"),
                    text=self.translations.get("tts_selector_save_information", "Voice successfully saved!"),
                    msg_type="success"
                )
    ### VOICE DIALOG ===================================================================================

    ### EXPRESSIONS DIALOG =============================================================================
    def open_expressions_menu(self, character_name):
        """
        Opens the expression settings menu for the specified character.
        """
        configuration_data = self.configuration_characters.load_configuration()

        if "current_sow_system_mode" not in configuration_data["character_list"][character_name]:
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

        dialog = self.create_expressions_dialog(character_name)
        dialog.exec()

    def create_expressions_dialog(self, character_name):
        """
        Creates a QDialog for selecting the expressions and visualization method.
        """
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"

        f_sidebar_title = QtGui.QFont("Inter Tight", 8, QtGui.QFont.Weight.Bold)
        f_sidebar_title.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 1.2)
        f_sidebar_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        current_sow_system_mode = self.configuration_characters.get_character_data(character_name, "current_sow_system_mode")
        expression_images_folder = self.configuration_characters.get_character_data(character_name, "expression_images_folder")
        live2d_model_folder = self.configuration_characters.get_character_data(character_name, "live2d_model_folder")
        vrm_model_file = self.configuration_characters.get_character_data(character_name, "vrm_model_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("expressions_selector_title", 'Expressions Selector'))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setFixedSize(820, 600)

        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: #0c0c10;
                color: {_TEXT};
            }}
        """)

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar_frame = QFrame()
        sidebar_frame.setObjectName("SidebarFrame")
        sidebar_frame.setFixedWidth(220)
        sidebar_frame.setStyleSheet(f"""
            QFrame#SidebarFrame {{
                background-color: rgba(11, 11, 15, 0.4);
                border: none;
                border-right: 1px solid {_BORDER};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar_frame)
        sidebar_layout.setContentsMargins(10, 24, 10, 24)
        sidebar_layout.setSpacing(12)

        menu_title = QLabel(self.translations.get("visual_engine_menu_title", "VISUALIZATION ENGINE"))
        menu_title.setFont(f_sidebar_title)
        menu_title.setStyleSheet(f"color: {_TEXT_S}; background: transparent; border: none; padding-left: 14px;")
        sidebar_layout.addWidget(menu_title)

        sidebar_menu = QtWidgets.QListWidget()
        sidebar_menu.setObjectName("SidebarMenu")
        sidebar_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sidebar_menu.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        sidebar_menu.setIconSize(QtCore.QSize(16, 16))
        
        sidebar_menu.setStyleSheet(f"""
            QListWidget#SidebarMenu {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#SidebarMenu::item {{
                color: {_TEXT_S};
                font-family: 'Inter Tight SemiBold', 'Arial';
                font-size: 13px;
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 4px;
                border: 1px solid transparent;
            }}
            QListWidget#SidebarMenu::item:hover {{
                background-color: rgba(255, 255, 255, 0.04);
                color: {_TEXT};
            }}
            QListWidget#SidebarMenu::item:selected {{
                background-color: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                color: #FFFFFF;
                font-weight: bold;
            }}
        """)

        visual_modes_data = [
            (self.translations.get("visual_engine_nothing", "Nothing"), "app/gui/icons/close.png"),
            (self.translations.get("visual_engine_images", "Expressions Images"), "app/gui/icons/background_icon.png"),
            (self.translations.get("visual_engine_live2d", "Live2D Model"), "app/gui/icons/2D_face.png"),
            (self.translations.get("visual_engine_vrm", "VRM 3D Model"), "app/gui/icons/3D_cube.png")
        ]

        for name, icon_path in visual_modes_data:
            item = QtWidgets.QListWidgetItem(name)
            item.setIcon(QtGui.QIcon(icon_path))
            sidebar_menu.addItem(item)

        sidebar_layout.addWidget(sidebar_menu)
        main_layout.addWidget(sidebar_frame)

        content_frame = QFrame()
        content_frame.setObjectName("ContentFrame")
        content_frame.setStyleSheet("QFrame#ContentFrame { background: transparent; border: none; }")
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 24, 30, 24)
        content_layout.setSpacing(0)

        stacked_widget = QStackedWidget(content_frame)
        stacked_widget.setStyleSheet("background: transparent; border: none;")
        
        stacked_widget.addWidget(self.create_nothing_widgets(character_name))
        stacked_widget.addWidget(self.create_expression_images_widgets(character_name, expression_images_folder))
        stacked_widget.addWidget(self.create_live2d_model_widgets(character_name, live2d_model_folder))
        stacked_widget.addWidget(self.create_vrm_model_widgets(character_name, vrm_model_file))
        
        content_layout.addWidget(stacked_widget)
        main_layout.addWidget(content_frame, 1)

        sidebar_menu.currentRowChanged.connect(stacked_widget.setCurrentIndex)

        mode_map = {
            "Nothing": 0,
            "Expressions Images": 1,
            "Live2D Model": 2,
            "VRM": 3
        }
        initial_row = mode_map.get(current_sow_system_mode, 0)
        sidebar_menu.setCurrentRow(initial_row)

        dialog.setLayout(main_layout)
        return dialog

    def set_initial_expressions_widget(self, current_sow_system_mode, combo_box, stacked_widget):
        if current_sow_system_mode == "Nothing":
            stacked_widget.setCurrentIndex(0)

        elif current_sow_system_mode == "Expressions Images":
            combo_box.setCurrentText('Expressions Images')
            stacked_widget.setCurrentIndex(1)

        elif current_sow_system_mode == "Live2D Model":
            combo_box.setCurrentText('Live2D Model')
            stacked_widget.setCurrentIndex(2)
        
        elif current_sow_system_mode == "VRM":
            combo_box.setCurrentText("VRM")
            stacked_widget.setCurrentIndex(3)

    def update_expressions_menu_ui(self, selected_method, stacked_widget):
        if selected_method == "Nothing":
            stacked_widget.setCurrentIndex(0)
        elif selected_method == "Expressions Images":
            stacked_widget.setCurrentIndex(1)
        elif selected_method == "Live2D Model":
            stacked_widget.setCurrentIndex(2)
        elif selected_method == "VRM":
            stacked_widget.setCurrentIndex(3)

    def create_nothing_widgets(self, character_name):
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_label = QtGui.QFont("Inter Tight Medium", 10)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        card = QFrame()
        card.setObjectName("NothingCard")
        card.setStyleSheet(f"QFrame#NothingCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)

        info_label = QLabel(self.translations.get("expressions_selector_nothing_desc", "Deactivate advanced visualization. Only the static character avatar card will be displayed."))
        info_label.setFont(f_label)
        info_label.setStyleSheet(f"color: {_TEXT_S}; background: transparent; border: none;")
        info_label.setWordWrap(True)
        info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(info_label)
        
        layout.addWidget(card)
        layout.addStretch(1)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFont(f_btn)
        save_button.setFixedHeight(40)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        layout.addWidget(save_button)

        def save_expression_images_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_visual_settings_title", "Visual Settings"),
                text=self.translations.get("expressions_selector_mode_saved_body", "Expression mode successfully saved!"),
                msg_type="success"
            )

        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_expression_images_widgets(self, character_name, expression_images_folder):
        EXP_DIR = os.path.join(os.getcwd(), "assets\\emotions\\images")
        
        _SURF1    = "rgba(0, 0, 0, 0.3)"
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        expressions_image_label = QLabel(self.translations.get("expressions_selector_select_folder", 'Select an emotion folder'))
        expressions_image_label.setFont(f_label)
        expressions_image_label.setStyleSheet(lbl_style)
        gen_layout.addWidget(expressions_image_label)

        expressions_folder_combo = QtWidgets.QComboBox()
        expressions_folder_combo.setFont(f_input)
        expressions_folder_combo.setStyleSheet(combo_style)
        gen_layout.addWidget(expressions_folder_combo)
        layout.addWidget(gen_card)
        
        layout.addStretch(1)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFont(f_btn)
        save_button.setFixedHeight(40)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        save_button.setEnabled(False)
        layout.addWidget(save_button)

        def populate_expressions_images_folders():
            expressions_folder_combo.clear()
            selected_index = -1
            save_button.setEnabled(False)

            if os.path.isdir(EXP_DIR):
                folder_list = [folder for folder in os.listdir(EXP_DIR) if os.path.isdir(os.path.join(EXP_DIR, folder))]
                if folder_list:
                    expressions_folder_combo.addItems(folder_list)
                    save_button.setEnabled(True)

                    if expression_images_folder:
                        try:
                            selected_index = folder_list.index(os.path.basename(expression_images_folder))
                        except ValueError:
                            selected_index = -1
                else:
                    expressions_folder_combo.addItem(self.translations.get("expressions_selector_no_folders", "No folders found"))
            else:
                expressions_folder_combo.addItem(self.translations.get("expressions_selector_invalid_directory", "Invalid expressions directory"))

            if selected_index >= 0:
                expressions_folder_combo.setCurrentIndex(selected_index)

        def save_expression_images_settings():
            selected_folder = (
                os.path.join(EXP_DIR, expressions_folder_combo.currentText())
                if expressions_folder_combo.currentText() and expressions_folder_combo.currentText() != "No folders found"
                else None
            )

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["expression_images_folder"] = selected_folder
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Expressions Images"
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_visual_settings_title", "Visual Settings"),
                text=self.translations.get("expressions_selector_foler_saved_body", "Expression folder successfully saved!"),
                msg_type="success"
            )

        populate_expressions_images_folders()
        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_live2d_model_widgets(self, character_name, live2d_model_folder):
        LIVE2D_DIR = os.path.join(os.getcwd(), "assets\\emotions\\live2d")
        
        _SURF1    = "rgba(0, 0, 0, 0.3)"
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        live2d_model_label = QLabel(self.translations.get("expressions_selector_select_folder_live2d", 'Select folder with Live2D model'))
        live2d_model_label.setFont(f_label)
        live2d_model_label.setStyleSheet(lbl_style)
        gen_layout.addWidget(live2d_model_label)

        live2d_model_folder_combo = QtWidgets.QComboBox()
        live2d_model_folder_combo.setFont(f_input)
        live2d_model_folder_combo.setStyleSheet(combo_style)
        gen_layout.addWidget(live2d_model_folder_combo)
        layout.addWidget(gen_card)

        btn_map_motions = QPushButton("🔗  " + self.translations.get("live2d_motion_mapper_btn", "Map Emotions to Motions"))
        btn_map_motions.setFont(f_btn)
        btn_map_motions.setFixedHeight(40)
        btn_map_motions.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_map_motions.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_map_motions.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
                font-family: 'Inter Tight SemiBold';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        
        def open_motion_mapper_dialog():
            selected_folder = (
                os.path.join(LIVE2D_DIR, live2d_model_folder_combo.currentText())
                if live2d_model_folder_combo.currentText() and live2d_model_folder_combo.currentText() != "No folders found"
                else None
            )
            if not selected_folder:
                sow_toast(None, "Error", "Please select a valid Live2D model folder first.", "error")
                return
            dlg = Live2DMotionLinkerDialog(character_name, selected_folder, self.translations, parent=self.main_window)
            dlg.exec()

        btn_map_motions.clicked.connect(open_motion_mapper_dialog)
        layout.addWidget(btn_map_motions)
        
        layout.addStretch(1)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFont(f_btn)
        save_button.setFixedHeight(40)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        save_button.setEnabled(False)
        layout.addWidget(save_button)

        def populate_live2d_model_folders():
            live2d_model_folder_combo.clear()
            selected_index = -1
            save_button.setEnabled(False)

            if os.path.isdir(LIVE2D_DIR):
                folder_list = [folder for folder in os.listdir(LIVE2D_DIR) if os.path.isdir(os.path.join(LIVE2D_DIR, folder))]
                if folder_list:
                    live2d_model_folder_combo.addItems(folder_list)
                    save_button.setEnabled(True)
                    if live2d_model_folder:
                        try:
                            selected_index = folder_list.index(os.path.basename(live2d_model_folder))
                        except ValueError:
                            selected_index = -1
                else:
                    live2d_model_folder_combo.addItem(self.translations.get("expressions_selector_no_folders", "No folders found"))
            else:
                live2d_model_folder_combo.addItem(self.translations.get("expressions_selector_invalid_directory", "Invalid live2d model directory"))

            if selected_index >= 0:
                live2d_model_folder_combo.setCurrentIndex(selected_index)

        def save_live2d_model_settings():
            selected_folder = (
                os.path.join(LIVE2D_DIR, live2d_model_folder_combo.currentText())
                if live2d_model_folder_combo.currentText() and live2d_model_folder_combo.currentText() != "No folders found"
                else None
            )

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["live2d_model_folder"] = selected_folder
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Live2D Model"
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_visual_settings_title", "Visual Settings"),
                text=self.translations.get("expressions_selector_live2d_folder_saved_body", "Live2D folder successfully saved!"),
                msg_type="success"
            )

        populate_live2d_model_folders()
        save_button.clicked.connect(save_live2d_model_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_vrm_model_widgets(self, character_name, vrm_model_file):
        VRM_DIR = os.path.join(os.getcwd(), "assets\\emotions\\vrm")
        
        _SURF1    = "rgba(0, 0, 0, 0.3)"
        _SURF2    = "rgba(22, 22, 26, 0.5)"
        _SURF3    = "rgba(30, 30, 35, 0.5)"
        _BORDER   = "rgba(255, 255, 255, 0.08)"
        _BORDER_M = "rgba(255, 255, 255, 0.25)"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        f_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        f_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_input = QtGui.QFont("Inter Tight Medium", 10)
        f_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        f_btn = QtGui.QFont("Inter Tight Medium", 10, QtGui.QFont.Weight.Bold)
        f_btn.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        lbl_style = f"color: {_TEXT_S}; letter-spacing: 0.8px; border: none; background: transparent; margin-bottom: 2px;"

        combo_style = f"""
            QComboBox {{
                background-color: {_SURF2}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {_BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {_TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {_SURF3}; color: {_TEXT}; border: 1px solid {_BORDER_M};
                border-radius: 8px; selection-background-color: {_SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 6px; border-radius: 4px; }}
        """

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        gen_card = QFrame()
        gen_card.setObjectName("GenCard")
        gen_card.setStyleSheet(f"QFrame#GenCard {{ background-color: rgba(255, 255, 255, 0.015); border: 1px solid {_BORDER}; border-radius: 10px; }}")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setContentsMargins(12, 12, 12, 12)
        gen_layout.setSpacing(6)

        vrm_model_label = QLabel(self.translations.get("expressions_selector_select_file_vrm", 'Select VRM model file'))
        vrm_model_label.setFont(f_label)
        vrm_model_label.setStyleSheet(lbl_style)
        gen_layout.addWidget(vrm_model_label)

        vrm_model_file_combo = QtWidgets.QComboBox()
        vrm_model_file_combo.setFont(f_input)
        vrm_model_file_combo.setStyleSheet(combo_style)
        gen_layout.addWidget(vrm_model_file_combo)
        layout.addWidget(gen_card)
        
        layout.addStretch(1)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFont(f_btn)
        save_button.setFixedHeight(40)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet(f"""
            QPushButton {{
                background: {_BLUE_MUT};
                border: 1px solid {_BLUE_GLO};
                border-radius: 8px;
                color: {_BLUE};
            }}
            QPushButton:hover {{
                background: rgba(75, 184, 255, 0.25);
                border-color: rgba(75, 184, 255, 0.55);
                color: {_BLUE_BRT};
            }}
        """)
        save_button.setEnabled(False)
        layout.addWidget(save_button)

        def populate_vrm_model_file():
            vrm_model_file_combo.clear()
            selected_index = -1
            save_button.setEnabled(False)

            if os.path.isdir(VRM_DIR):
                file_list = [
                    file for file in os.listdir(VRM_DIR)
                    if os.path.isfile(os.path.join(VRM_DIR, file)) and file.lower().endswith(".vrm")
                ]
                if file_list:
                    display_names = [os.path.splitext(file)[0] for file in file_list]
                    vrm_model_file_combo.addItems(display_names)
                    save_button.setEnabled(True)
                    if vrm_model_file:
                        try:
                            selected_index = file_list.index(os.path.basename(vrm_model_file))
                        except ValueError:
                            selected_index = -1
                else:
                    vrm_model_file_combo.addItem(self.translations.get("expressions_vrm_selector_no_files", "No VRM files found"))
            else:
                vrm_model_file_combo.addItem(self.translations.get("expressions_vrm_selector_invalid_directory", "Invalid VRM model directory"))

            if selected_index >= 0:
                vrm_model_file_combo.setCurrentIndex(selected_index)

        def save_vrm_model_settings():
            selected_file = (
                os.path.join(VRM_DIR, vrm_model_file_combo.currentText() + ".vrm")
                if vrm_model_file_combo.currentText() and vrm_model_file_combo.currentText() != "No VRM files found"
                else None
            )

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["vrm_model_file"] = selected_file
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "VRM"
            self.configuration_characters.save_configuration_edit(configuration_data)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_visual_settings_title", "Visual Settings"),
                text=self.translations.get("expressions_selector_vrm_file_saved_body", "VRM file successfully saved!"),
                msg_type="success"
            )

        populate_vrm_model_file()
        save_button.clicked.connect(save_vrm_model_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget
    ### EXPRESSIONS DIALOG =============================================================================

    ### CHARACTERS GATEWAY =============================================================================
    async def open_characters_gateway(self):
        """
        Opens Characters Gateway and adjusts the behavior depending on selected navigation item.
        """
        try:
            self.ui.gateway_nav_rail.currentRowChanged.disconnect()
        except (TypeError, RuntimeError):
            pass

        self.ui.gateway_nav_rail.currentRowChanged.connect(
            lambda index: self.on_gateway_tab_changed(index)
        )

        if self.ui.gateway_nav_rail.currentRow() == -1:
            self.ui.gateway_nav_rail.setCurrentRow(0)
        else:
            asyncio.ensure_future(self.handle_tab_change(self.ui.gateway_nav_rail.currentRow()))
    
    def on_gateway_tab_changed(self, index):
        if self.is_loading:
            self.abort_loading = True

        self.is_loading = True
        self.abort_loading = False
        asyncio.ensure_future(self.handle_tab_change(index))

    def clear_scroll_area(self, scroll_area):
        widget = scroll_area.widget()
        if widget:
            layout = widget.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                        item.widget().setParent(None)

    def save_to_cache_character_card(self, url, data):
        file_name = os.path.basename(url)
        file_name = url.split("/")[-2] + "_" + url.split("/")[-1]
        file_path = os.path.join(CACHE_DIR, file_name)

        os.makedirs(CACHE_DIR, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def get_from_cache_character_card(self, url):
        CACHE_DIR = "cache"
        if not url or not isinstance(url, str) or "/" not in url:
            return None

        try:
            parts = url.split("/")
            if len(parts) < 2:
                return None

            file_name = parts[-2] + "_" + parts[-1]
            file_path = os.path.join(CACHE_DIR, file_name)

            if os.path.exists(file_path):
                return file_path
            else:
                return None

        except Exception as e:
            logger.error(f"URL Error: {e}")
            return None
    
    async def download_image(self, url):
        if not url or not isinstance(url, str) or "/" not in url:
            logger.error(f"Incorrect URL: {url}")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Download error: {response.status}")
        except Exception as e:
            logger.error(f"Error when uploading an image: {e}")
            return None
    
    def process_image(self, data):
        from io import BytesIO

        with BytesIO(data) as bio:
            image = Image.open(bio)
            with BytesIO() as output:
                image.convert("RGBA").save(output, format="PNG")
                return output.getvalue()
            
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

    @asyncSlot()
    async def handle_tab_change(self, current_tab_index):
        self.abort_loading = False

        self.ui.gateway_stacked_widget.setCurrentIndex(current_tab_index)
    
        scroll_area_mapping = {
            "soul_gateway": self.ui.scrollArea_soul_gateway,
            "character_card_page": self.ui.scrollArea_character_card,
            "lorebooks": self.ui.scrollArea_lorebooks,
            "scenes": self.ui.scrollArea_scenes
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.soul_cards.clear()
        self.gate_cards.clear()
        self.lorebook_cards.clear()
        self.scene_cards.clear()

        self.ui.stackedWidget.setCurrentWidget(self.ui.charactersgateway_page)
        
        match current_tab_index:
            case 0:  # Soul Gateway
                self.ui.label_nsfw.hide()
                self.ui.checkBox_enable_nsfw.hide()
                
                if self.soul_gateway_container:
                    self.soul_gateway_container.deleteLater()
                
                self.soul_gateway_container = QWidget()
                self.soul_gateway_grid_layout = QtWidgets.QGridLayout(self.soul_gateway_container)
                self.soul_gateway_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.soul_gateway_grid_layout.setSpacing(10)
                self.ui.scrollArea_soul_gateway.setWidget(self.soul_gateway_container)

                REGISTRY_URL = "https://raw.githubusercontent.com/jofizcd/sow-data/main/soul_registry.json"

                try:
                    def fetch_registry():
                        context = ssl._create_unverified_context()
                        with urllib.request.urlopen(REGISTRY_URL, timeout=10, context=context) as response:
                            return json.loads(response.read().decode('utf-8'))

                    registry = await asyncio.to_thread(fetch_registry)
                    characters = registry.get("characters", [])

                    for i, char_info in enumerate(characters):
                        if self.abort_loading: break

                        char_url = char_info['download_url']
                        char_name = char_info['name']
                        char_card_author = char_info['author']
                        temp_path = os.path.join("app/utils/ai_clients/backend/_temp/gateway_cache", f"{char_name}.png")
                        
                        if not os.path.exists(temp_path):
                            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                            await asyncio.to_thread(urllib.request.urlretrieve, char_url, temp_path)

                        v2_data = await asyncio.to_thread(self.soul_gateway_client.read_v2_card, temp_path)
                        if not v2_data: continue
                        
                        data = v2_data.get("data", {})
                        character_name = data.get("name", "Unknown")
                        character_title = data.get("creator_notes", "")
                        character_personality = data.get("description", "")
                        first_message = data.get("first_mes", "")
                        character_tavern_personality = data.get("personality", "")
                        example_dialogs = data.get("mes_example", "")
                        character_scenario = data.get("scenario", "")
                        alternate_greetings = data.get("alternate_greetings", [])
                        character_book = data.get("character_book")

                        card_widget = CharacterCardCharactersGateway(
                            conversation_method="Local LLM", character_author=char_card_author, character_name=character_name, 
                            character_avatar=temp_path, character_title=character_title,
                            character_description=character_personality, character_personality=character_tavern_personality,
                            scenario=character_scenario, first_message=first_message, 
                            example_messages=example_dialogs, alternate_greetings=alternate_greetings, 
                            method=self.check_character_information
                        )
                        
                        character_widget = self.create_soul_gateway_character_card(
                            card_widget, character_name, character_title, temp_path,
                            character_personality, first_message, character_tavern_personality, 
                            example_dialogs, character_scenario, alternate_greetings, character_book
                        )

                        self.soul_cards.append(character_widget)
                        if i % 2 == 0:
                            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("soul_gateway"))
                            await asyncio.sleep(0.02)

                    self.update_gate_layout("soul_gateway")
                except Exception as e:
                    logger.error(f"Error loading Soul Gateway: {e}")

            case 1:  # Chub AI Public Database
                self.ui.checkBox_enable_nsfw.show()
                self.ui.label_nsfw.show()

                if self.gate_container:
                    self.gate_container.deleteLater()
                    self.gate_container = None
                
                self.gate_container = QWidget()
                self.gate_cards_grid_layout = QtWidgets.QGridLayout(self.gate_container)
                self.gate_cards_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.gate_cards_grid_layout.setSpacing(10)
                self.ui.scrollArea_character_card.setWidget(self.gate_container)
                
                trending_characters = await self.character_card_client.fetch_trending_character_data()
                nodes = trending_characters.get("data", {}).get("nodes", [])

                async def process_node(node):
                    if self.abort_loading: return
                    full_path = node.get('fullPath')
                    if full_path is None: return

                    (
                        character_name, character_title, character_avatar_url, downloads,
                        likes, total_tokens, character_personality, first_message,
                        character_tavern_personality, example_dialogs, character_scenario, alternate_greetings
                    ) = await self.character_card_client.get_character_information(full_path)
                        
                    avatar_path = None
                    if character_avatar_url:
                        try:
                            avatar_path = await self.load_image_character_card(character_avatar_url)
                        except Exception as e:
                            logger.error(f"Error loading avatar for {character_name}: {e}")

                    card_widget = CharacterCardCharactersGateway(
                        conversation_method="Not Character AI", character_author=None, character_name=character_name, 
                        character_avatar=avatar_path, character_title=character_title,
                        character_description=character_personality, character_personality=character_tavern_personality,
                        scenario=character_scenario, first_message=first_message, 
                        example_messages=example_dialogs, alternate_greetings=alternate_greetings, 
                        method=self.check_character_information
                    )
                    
                    character_widget = self.create_chub_character_card(
                        card_widget, character_name, character_title, avatar_path, 
                        downloads, likes, total_tokens,
                        character_personality, first_message, character_tavern_personality, 
                        example_dialogs, character_scenario, alternate_greetings
                    )

                    self.gate_cards.append(character_widget)
                    QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("chub_ai"))

                for i, node in enumerate(nodes[:50]):
                    if self.abort_loading: break
                    await process_node(node)
                    if i % 4 == 0:
                        self.update_gate_layout("chub_ai")
                        await asyncio.sleep(0.05)

                self.update_gate_layout("chub_ai")

            case 2:  # World Lorebooks
                self.ui.label_nsfw.hide()
                self.ui.checkBox_enable_nsfw.hide()
                await self.load_shared_lorebooks()

            case 3:  # Soul Stage Scenarios
                self.ui.label_nsfw.hide()
                self.ui.checkBox_enable_nsfw.hide()
                await self.load_shared_scenes()
        
        self.is_loading = False

    def update_gate_layout(self, tab):
        match tab:
            case "soul_gateway":
                cards_list = self.soul_cards
                cards_layout = self.soul_gateway_grid_layout
                cards_container = self.soul_gateway_container
                scroll_area = self.ui.scrollArea_soul_gateway
            case "chub_ai":
                cards_list = self.gate_cards
                cards_layout = self.gate_cards_grid_layout
                cards_container = self.gate_container
                scroll_area = self.ui.scrollArea_character_card
            case "lorebooks":
                cards_list = self.lorebook_cards
                cards_layout = self.lorebooks_grid_layout
                cards_container = self.lorebooks_container
                scroll_area = self.ui.scrollArea_lorebooks
            case "scenes":
                cards_list = self.scene_cards
                cards_layout = self.scenes_grid_layout
                cards_container = self.scenes_container
                scroll_area = self.ui.scrollArea_scenes
            case _:
                return

        while True:
            item = cards_layout.takeAt(0)
            if not item: break
            widget = item.widget()
            if widget and widget not in cards_list:
                widget.deleteLater()

        for i in reversed(range(cards_layout.columnCount())):
            cards_layout.setColumnMinimumWidth(i, 0)
            cards_layout.setColumnStretch(i, 0)

        viewport_width = scroll_area.viewport().width()
        current_margins = cards_layout.contentsMargins()
        spacing = 15
        vertical_spacing = 15
        card_width = 200
        card_height = 270

        cards_layout.setHorizontalSpacing(spacing)
        cards_layout.setVerticalSpacing(vertical_spacing)

        n_cols = max(1, (viewport_width + spacing) // (card_width + spacing))
        total_cards_width = n_cols * card_width + (n_cols - 1) * spacing

        left_right_margin = max(0, (viewport_width - total_cards_width) // 2)
        cards_layout.setContentsMargins(
            left_right_margin,
            current_margins.top(),
            left_right_margin,
            current_margins.bottom()
        )

        for col in range(n_cols):
            cards_layout.setColumnMinimumWidth(col, card_width)
            cards_layout.setColumnStretch(col, 0)

        row, col = 0, 0
        for card in cards_list:
            try:
                if card.parent() != cards_container:
                    card.setParent(cards_container)
                card.setFixedSize(card_width, card_height)
                cards_layout.addWidget(card, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
                col += 1
                if col >= n_cols:
                    col = 0
                    row += 1
            except RuntimeError:
                continue

        row_count = row + 1 if col > 0 else row
        total_height = (row_count * card_height) + (max(0, row_count - 1) * vertical_spacing)

        final_margins = cards_layout.contentsMargins()
        cards_container.setFixedSize(
            total_cards_width + final_margins.left() + final_margins.right(),
            total_height + final_margins.top() + final_margins.bottom()
        )
        cards_container.updateGeometry()

    def handle_gate_resize(self, event):
        if self.ui.scrollArea_soul_gateway.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("soul_gateway"))
        elif self.ui.scrollArea_character_card.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("chub_ai"))
        elif hasattr(self.ui, 'scrollArea_lorebooks') and self.ui.scrollArea_lorebooks.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("lorebooks"))
        elif hasattr(self.ui, 'scrollArea_scenes') and self.ui.scrollArea_scenes.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("scenes"))
        
    def create_soul_gateway_character_card(self, character_card, character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None):
        """
        Builds a Soul Gateway character card.
        """
        button = QtWidgets.QPushButton()
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        button.setFont(font)
        
        button.setFixedHeight(32)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button.setText(self.translations.get("gateway_add_to_list", "Add to List").strip())
        
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 16px;
                color: rgba(255, 255, 255, 0.7);
                font-family: 'Inter Tight SemiBold';
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        button.clicked.connect(
            lambda: self.open_gateway_provider_selection(
                character_name, character_title, avatar_path, character_personality, 
                first_message, character_tavern_personality, example_dialogs, 
                character_scenario, alternate_greetings, character_book
            )
        )
        
        character_card.action_panel_layout.addWidget(button)
        return character_card

    def create_chub_character_card(self, character_card, character_name, character_title, avatar_path, downloads, likes, total_tokens, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings):
        """
        Builds a Chub AI card.
        """
        character_card.downloads = downloads
        character_card.likes = likes
        character_card.total_tokens = total_tokens

        button = QtWidgets.QPushButton()
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        button.setFont(font)
        
        button.setFixedHeight(32)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button.setText(self.translations.get("gateway_add_to_list", "Add to List").strip())
        
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 16px;
                color: rgba(255, 255, 255, 0.7);
                font-family: 'Inter Tight SemiBold';
                font-size: 11px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        
        button.clicked.connect(
            lambda: self.open_gateway_provider_selection(
                character_name, character_title, avatar_path, character_personality, 
                first_message, character_tavern_personality, example_dialogs, 
                character_scenario, alternate_greetings, None
            )
        )
        
        character_card.action_panel_layout.addWidget(button)
        return character_card

    def open_gateway_provider_selection(self, character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None):
        """
        Displays a Grid Dialog with all active AI engines.
        """
        dialog = QtWidgets.QDialog(self.main_window)
        dialog.setWindowTitle(self.translations.get("choose_ai_provider_title", "Choose AI Provider"))
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        icon = QtGui.QIcon("app/gui/icons/logotype.ico")
        dialog.setWindowIcon(icon)
        
        dialog.setFixedSize(940, 680)

        container = QWidget()
        container.setObjectName("gateway_selector_container")
        container.setStyleSheet("""
            QWidget#gateway_selector_container {
                background-color: #121212; 
                border: 1px solid #2A2A2A;
            }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 25)

        title = QLabel(self.translations.get("choose_ai_provider_title", "Choose AI Provider"))
        title.setObjectName("gateway_selector_title")
        title.setStyleSheet("""
            QLabel#gateway_selector_title {
                font-size: 22px; 
                font-weight: bold; 
                color: white; 
                border: none; 
                background: transparent;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(self.translations.get("choose_ai_provider_subtitle", "Select the engine to bind with this character profile"))
        subtitle.setObjectName("gateway_selector_subtitle")
        subtitle.setStyleSheet("""
            QLabel#gateway_selector_subtitle {
                font-size: 13px; 
                color: rgba(255, 255, 255, 0.45); 
                margin-bottom: 25px; 
                border: none; 
                background: transparent;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(15)

        methods = [
            (
                self.translations.get("provider_name_local", "Local LLM"),
                self.translations.get("provider_desc_local", "Run models completely offline with maximum privacy and no censorship"),
                "app/gui/icons/local_llm.png"
            ),
            (
                self.translations.get("provider_name_openai", "Open AI"),
                self.translations.get("provider_desc_openai", "Industry-leading quality and reliability for roleplay"),
                "app/gui/icons/openai.png"
            ),
            (
                self.translations.get("provider_name_anthropic", "Anthropic"),
                self.translations.get("provider_desc_anthropic", "Best-in-class prose, character consistency, and emotional depth"),
                "app/gui/icons/anthropic.png"
            ),
            (
                self.translations.get("provider_name_gemini", "Google Gemini"),
                self.translations.get("provider_desc_gemini", "Massive context window (1M+ tokens) — perfect for long stories and sagas"),
                "app/gui/icons/gemini.png"
            ),
            (
                self.translations.get("provider_name_deepseek", "DeepSeek"),
                self.translations.get("provider_desc_deepseek", "Extremely capable and highly cost-efficient — best price-to-performance ratio"),
                "app/gui/icons/deepseek.png"
            ),
            (
                self.translations.get("provider_name_grok", "Grok"),
                self.translations.get("provider_desc_grok", "Less censored, witty, and creative — great for unrestricted adult roleplay"),
                "app/gui/icons/grok.png"
            ),
            (
                self.translations.get("provider_name_qwen", "Qwen"),
                self.translations.get("provider_desc_qwen", "Powerful multilingual reasoning and strong narrative capabilities"),
                "app/gui/icons/qwen.png"
            ),
            (
                self.translations.get("provider_name_zai", "Z.AI"),
                self.translations.get("provider_desc_zai", "Fast, coherent, and excellent at storytelling — strong Claude alternative"),
                "app/gui/icons/zai.png"
            ),
            (
                self.translations.get("provider_name_mistral", "Mistral AI"),
                self.translations.get("provider_desc_mistral", "High-performance open models with excellent speed and quality balance"),
                "app/gui/icons/mistralai.png"
            ),
            (
                self.translations.get("provider_name_openrouter", "OpenRouter"),
                self.translations.get("provider_desc_openrouter", "Access to hundreds of top models in one place — the ultimate aggregator"),
                "app/gui/icons/openrouter.png"
            )
        ]

        positions = [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2),
            (3, 0)
        ]

        for i, (name, desc, icon_path) in enumerate(methods):
            card = MethodCard(name, desc, icon_path)
            
            card.setObjectName(f"provider_card_{i}")
            card.setStyleSheet(f"""
                QWidget#provider_card_{i} {{
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    background-color: rgba(255, 255, 255, 0.01);
                }}
                QWidget#provider_card_{i}:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                    border-color: rgba(255, 255, 255, 0.15);
                }}
            """)
            
            def make_select_callback(method_name=name):
                return lambda: self.on_gateway_provider_selected(
                    method_name, dialog, character_name, character_title, 
                    avatar_path, character_personality, first_message, 
                    character_tavern_personality, example_dialogs, 
                    character_scenario, alternate_greetings, character_book
                )
            
            card.clicked.connect(make_select_callback())
            row, col = positions[i]
            grid.addWidget(card, row, col)

        layout.addLayout(grid)
        layout.addStretch()
        dialog.exec()

    def on_gateway_provider_selected(self, method_name, dialog, character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None):
        """
        Receives choice, closes modal and writes the gateway character with the designated engine.
        """
        dialog.accept()
        self.add_character_from_gateway(
            character_name, character_title, avatar_path, character_personality, 
            first_message, character_tavern_personality, example_dialogs, 
            character_scenario, alternate_greetings, character_book, 
            conversation_method=method_name
        )

    async def search_character(self):
        """
        Overridden search routing matching the navigation scheme.
        """
        character_name = self.ui.lineEdit_search_character.text().strip()
        self.ui.lineEdit_search_character.clear()

        current_tab_index = self.ui.gateway_nav_rail.currentRow()

        scroll_area_mapping = {
            "soul_gateway": self.ui.scrollArea_soul_gateway,
            "character_card_page": self.ui.scrollArea_character_card,
            "lorebooks": self.ui.scrollArea_lorebooks,
            "scenes": self.ui.scrollArea_scenes
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.soul_cards.clear()
        self.gate_cards.clear()
        self.lorebook_cards.clear()
        self.scene_cards.clear()

        match current_tab_index:
            case 0: # Soul Gateway search
                if self.soul_gateway_container:
                    self.soul_gateway_container.deleteLater()
                
                self.soul_gateway_container = QWidget()
                self.soul_gateway_grid_layout = QtWidgets.QGridLayout(self.soul_gateway_container)
                self.soul_gateway_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.soul_gateway_grid_layout.setSpacing(10)
                self.ui.scrollArea_soul_gateway.setWidget(self.soul_gateway_container)

                REGISTRY_URL = "https://raw.githubusercontent.com/jofizcd/sow-data/main/soul_registry.json"
                try:
                    def fetch_registry():
                        context = ssl._create_unverified_context()
                        with urllib.request.urlopen(REGISTRY_URL, timeout=10, context=context) as response:
                            return json.loads(response.read().decode('utf-8'))

                    registry = await asyncio.to_thread(fetch_registry)
                    all_characters = registry.get("characters", [])
                    filtered = [c for c in all_characters if character_name.lower() in c['name'].lower()]

                    for i, char_info in enumerate(filtered):
                        if self.abort_loading: break
                        char_url = char_info['download_url']
                        char_file_name = char_info['name']
                        char_card_author = char_info['author']
                        temp_path = os.path.join("app/utils/ai_clients/backend/_temp/gateway_cache", f"{char_file_name}.png")
                        
                        if not os.path.exists(temp_path):
                            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                            await asyncio.to_thread(urllib.request.urlretrieve, char_url, temp_path)

                        v2_data = await asyncio.to_thread(self.soul_gateway_client.read_v2_card, temp_path)
                        if not v2_data: continue
                        data = v2_data.get("data", {})

                        card_widget = CharacterCardCharactersGateway(
                            conversation_method="Local LLM", character_author=char_card_author,
                            character_name=data.get("name", "Unknown"), character_avatar=temp_path, 
                            character_title=data.get("creator_notes", ""),
                            character_description=data.get("description", ""), character_personality=data.get("personality", ""), 
                            scenario=data.get("scenario", ""), first_message=data.get("first_mes", ""), 
                            example_messages=data.get("mes_example", ""), alternate_greetings=data.get("alternate_greetings", []),
                            method=self.check_character_information
                        )

                        character_widget = self.create_soul_gateway_character_card(
                            card_widget, data.get("name", "Unknown"), data.get("creator_notes", ""), temp_path, 
                            data.get("description", ""), data.get("first_mes", ""), data.get("personality", ""), 
                            data.get("mes_example", ""), data.get("scenario", ""), data.get("alternate_greetings", []), 
                            data.get("character_book")
                        )
                        self.soul_cards.append(character_widget)
                        QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("soul_gateway"))
                        await asyncio.sleep(0.01)

                    self.update_gate_layout("soul_gateway")
                except Exception as e:
                    logger.error(f"Error searching Soul Gateway: {e}")

            case 1: # Chub AI search
                if self.gate_container:
                    self.gate_container.deleteLater()
                self.gate_container = QWidget()
                self.gate_cards_grid_layout = QtWidgets.QGridLayout(self.gate_container)
                self.gate_cards_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.gate_cards_grid_layout.setSpacing(10)
                self.ui.scrollArea_character_card.setWidget(self.gate_container)

                searched_characters = await self.character_card_client.search_character(character_name)
                nodes = searched_characters.get("data", {}).get("nodes", [])

                async def process_node(node):
                    full_path = node.get('fullPath')
                    if full_path is None: return
                    (
                        character_name, character_title, character_avatar_url, downloads,
                        likes, total_tokens, character_personality, first_message,
                        character_tavern_personality, example_dialogs, character_scenario, alternate_greetings
                    ) = await self.character_card_client.get_character_information(full_path)
                        
                    avatar_path = None
                    if character_avatar_url:
                        try:
                            avatar_path = await self.load_image_character_card(character_avatar_url)
                        except Exception as e:
                            logger.error(f"Error loading avatar: {e}")

                    card_widget = CharacterCardCharactersGateway(
                        conversation_method="Not Character AI", character_author=None, character_name=character_name, 
                        character_avatar=avatar_path, character_title=character_title,
                        character_description=character_personality, character_personality=character_tavern_personality,
                        scenario=character_scenario, first_message=first_message, 
                        example_messages=example_dialogs, alternate_greetings=alternate_greetings, 
                        method=self.check_character_information
                    )
                    character_widget = self.create_chub_character_card(
                        card_widget, character_name, character_title, avatar_path, 
                        downloads, likes, total_tokens,
                        character_personality, first_message, character_tavern_personality, 
                        example_dialogs, character_scenario, alternate_greetings
                    )
                    self.gate_cards.append(character_widget)
                    QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("chub_ai"))

                for i, node in enumerate(nodes[:50]):
                    await process_node(node)
                    if i % 4 == 0:
                        self.update_gate_layout("chub_ai")
                        await asyncio.sleep(0.05)
                self.update_gate_layout("chub_ai")

            case 2: # Filter Lorebooks
                await self.load_shared_lorebooks(filter_text=character_name)

            case 3: # Filter Scenes
                await self.load_shared_scenes(filter_text=character_name)

    def add_character_from_gateway(self, character_name, character_title, character_avatar_directory, character_personality, character_first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None, conversation_method=None):
        character_configuration = self.configuration_characters.load_configuration()
        character_list = character_configuration["character_list"]

        if character_name in character_list:
            suffix = 1
            while f"{character_name}_{suffix}" in character_list:
                suffix += 1
            suggested_name = f"{character_name}_{suffix}"

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("duplicate_character_error_title", "Duplicate Character"),
                text=self.translations.get("duplicate_character_error", "A character with this name already exists. A number will be added to the character's name."),
                msg_type="info"
            )

            character_name = suggested_name

        selected_lorebook_name = "None"
        
        if character_book:
            try:
                book_name = character_book.get("name")
                if not book_name or book_name.strip() == "":
                    book_name = f"Lore_{character_name}"

                import_lorebook_text = self.translations.get(
                    "import_lorebook_text", 
                    f"This card contains an embedded lorebook '{book_name}'. Do you want to add it to your library?"
                ).format(book_name=book_name)
                
                confirm_dialog = SowConfirmDialog(
                    parent=self.main_window,
                    title=self.translations.get("lorebook_editor_import_lorebook", "Import Lorebook"),
                    text=import_lorebook_text,
                    confirm_text="Import",
                    danger=False
                )

                if confirm_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                    config = self.configuration_settings.load_configuration()
                    lorebooks = config.get("user_data", {}).get("lorebooks", {})

                    new_name = book_name
                    orig_name = new_name
                    counter = 1
                    while new_name in lorebooks:
                        new_name = f"{orig_name}_{counter}"
                        counter += 1

                    new_lorebook = {
                        "name": new_name,
                        "description": character_book.get("description", ""),
                        "n_depth": character_book.get("scan_depth", 3),
                        "entries": []
                    }

                    entries_data = character_book.get("entries", {})
                    if isinstance(entries_data, dict):
                        sorted_keys = sorted(entries_data.keys(), key=lambda x: int(x) if x.isdigit() else 0)
                        items_to_parse = [entries_data[k] for k in sorted_keys]
                    else:
                        items_to_parse = entries_data

                    for e in items_to_parse:
                        ext = e.get("extensions", {})
                        keys = e.get("key", e.get("keys", []))
                        
                        new_entry = {
                            "name": e.get("name", e.get("comment", "Unnamed Entry")),
                            "content": e.get("content", ""),
                            "key": keys if isinstance(keys, list) else [keys],
                            "probability": e.get("probability", 100),
                            "trigger_type": ext.get("sow_trigger_type", "keyword"),
                            "min_msg": ext.get("sow_min_msg", 0),
                            "max_msg": ext.get("sow_max_msg", 0),
                            "exclude_key": ext.get("sow_exclude_key", []),
                            "sticky": ext.get("sow_sticky", 0),
                            "cooldown": ext.get("sow_cooldown", 0),
                            "delay": ext.get("sow_delay", 0)
                        }
                        new_lorebook["entries"].append(new_entry)

                    self.configuration_settings.update_lorebook(new_name, new_lorebook)
                    
                    count_val = len(new_lorebook['entries'])
                    success_msg = self.translations.get(
                        "lorebook_editor_import_success_desc", 
                        f"Lorebook '{new_name}' imported with {count_val} entries."
                    ).format(new_name=new_name, count=count_val)
                    
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("lorebook_editor_import_success", "Import Success"),
                        text=success_msg,
                        msg_type="success"
                    )
                    
                    selected_lorebook_name = new_name

            except Exception as e:
                logger.error(f"Error importing lorebook from gateway: {e}")
                error_str = str(e)
                err_msg = self.translations.get("lorebook_editor_import_error_desc", f"Failed to parse lorebook: {error_str}").format(error=error_str)
                
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("lorebook_editor_import_error", "Import Error"),
                    text=err_msg,
                    msg_type="error"
                )

        target_method = conversation_method if conversation_method in [
            "Mistral AI", "Open AI", "OpenRouter", "Local LLM", 
            "Anthropic", "Google Gemini", "DeepSeek", "Grok", "Qwen", "Z.AI"
        ] else "Local LLM"

        try:
            self.configuration_characters.save_character_card(
                character_name=character_name,
                character_title=character_title,
                character_avatar=character_avatar_directory,
                character_description=character_personality,
                character_personality=character_tavern_personality,
                first_message=character_first_message,
                scenario=character_scenario,
                example_messages=example_dialogs,
                alternate_greetings=alternate_greetings,
                selected_persona="None",
                selected_system_prompt_preset="By default",
                selected_lorebook=selected_lorebook_name,
                elevenlabs_voice_id=None,
                voice_type=None,
                rvc_enabled=False,
                rvc_file=None,
                expression_images_folder=None,
                live2d_model_folder=None,
                vrm_model_file=None,
                conversation_method=target_method
            )
            
            title = self.translations.get("add_character_title", "Character Information")
            first_text = self.translations.get("add_character_text_1", "was successfully added!")
            second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
            
            sow_toast(
                parent=self.main_window,
                title=title,
                text=f"{character_name} {first_text}\n{second_text}",
                msg_type="success"
            )
            return character_name

        except Exception as e:
            logger.error(f"Error adding character: {e}")
            sow_toast(
                parent=self.main_window,
                title="Error",
                text=f"Error adding character:\n{str(e)}",
                msg_type="error"
            )
            return None
   
    def check_character_information(self, conversation_method, character_name, character_avatar, character_title, character_description, character_personality, scenario, first_message, example_messages, alternate_greetings):
        _BG       = "#070709"
        _SURF1    = "#0B0B0F"
        _SURF2    = "#121218"
        _SURF3    = "#161622"
        _CARD_BG  = "#0E0E14"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BORDER   = "rgba(255, 255, 255, 0.045)"
        _BORDER_M = "rgba(255, 255, 255, 0.08)"
        
        _WHITE_MUT = "rgba(255, 255, 255, 0.08)"
        _WHITE_GLO = "rgba(255, 255, 255, 0.15)"

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(940, 680)
        dialog.resize(960, 700)

        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        f_title = mf(14, QFont.Weight.Bold)
        f_label = mf(8,  QFont.Weight.Bold)
        f_input = mf(10, QFont.Weight.Medium)
        f_btn   = mf(10, QFont.Weight.DemiBold)

        dialog.setFont(f_input)
        dialog.setStyleSheet(
            f"QDialog {{ background-color: {_BG}; }}"
            f"QLabel {{ border: none; background: transparent; color: {_TEXT}; }}"
        )

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("IGSidebar")
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet(
            f"QFrame#IGSidebar {{"
            f"  background-color: {_SURF1};"
            f"  border: none;"
            f"  border-right: 1px solid {_BORDER};"
            f"}}"
            f"QFrame#IGSidebar QLabel {{ border: none; background: transparent; }}"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 24)
        sidebar_layout.setSpacing(16)

        avatar_size = 110
        avatar_label = QLabel()
        
        source_pixmap = QPixmap(character_avatar)
        if source_pixmap.isNull():
            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
        else:
            scaled_pixmap = source_pixmap.scaled(
                avatar_size, avatar_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            x = (scaled_pixmap.width() - avatar_size) // 2
            y = (scaled_pixmap.height() - avatar_size) // 2
            square_pixmap = scaled_pixmap.copy(x, y, avatar_size, avatar_size)

            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            brush = QtGui.QBrush(square_pixmap)
            painter.setBrush(brush)
            painter.setPen(Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, avatar_size, avatar_size)
            painter.end()

        avatar_label.setPixmap(final_pixmap)
        avatar_label.setFixedSize(avatar_size, avatar_size)
        avatar_label.setStyleSheet("border: none; background: transparent;")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        avatar_label.setGraphicsEffect(shadow)
        
        avatar_container = QHBoxLayout()
        avatar_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addLayout(avatar_container)

        name_lbl = QLabel(self.translations.get("character_settings_name_label", "CHARACTER NAME"))
        name_lbl.setFont(f_label)
        name_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px;")
        sidebar_layout.addWidget(name_lbl)

        name_label_txt = QLabel(character_name)
        name_label_txt.setFont(f_title)
        name_label_txt.setStyleSheet(f"color: {_TEXT};")
        sidebar_layout.addWidget(name_label_txt)

        raw_title = str(character_title).strip() if character_title else ""
        max_subtitle_length = 70
        
        if raw_title:
            clean_title = " ".join(raw_title.splitlines())
            if len(clean_title) > max_subtitle_length:
                short_title = clean_title[:max_subtitle_length].strip() + "..."
            else:
                short_title = clean_title
        else:
            short_title = "No creator notes provided."

        subtitle_label = QLabel(short_title)
        subtitle_label.setFont(mf(9, QFont.Weight.Medium))
        subtitle_label.setStyleSheet(f"color: {_TEXT_S}; line-height: 1.3;")
        subtitle_label.setWordWrap(True)
        sidebar_layout.addWidget(subtitle_label)

        nav_title = QLabel(self.translations.get("character_settings_nav_label", "CONFIGURATION"))
        nav_title.setFont(f_label)
        nav_title.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 6px;")
        sidebar_layout.addWidget(nav_title)

        nav_list = QtWidgets.QListWidget()
        nav_list.setObjectName("IGNavList")
        nav_list.setFont(f_btn)
        nav_list.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        nav_list.setStyleSheet(
            f"QListWidget#IGNavList {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#IGNavList::item {{"
            f"  color: {_TEXT_S};"
            f"  background-color: transparent;"
            f"  border: 1px solid transparent;"
            f"  border-radius: 8px;"
            f"  padding: 10px 14px;"
            f"  margin-bottom: 4px;"
            f"}}"
            f"QListWidget#IGNavList::item:hover {{"
            f"  background-color: rgba(255, 255, 255, 0.04);"
            f"  color: {_TEXT};"
            f"}}"
            f"QListWidget#IGNavList::item:selected {{"
            f"  background-color: {_WHITE_MUT};"
            f"  border: 1px solid {_WHITE_GLO};"
            f"  color: #FFFFFF;"
            f"}}"
        )
        sidebar_layout.addWidget(nav_list)
        sidebar_layout.addStretch()

        ok_button = QPushButton(self.translations.get("personas_editor_close", "CLOSE"), dialog)
        ok_button.setFont(f_btn)
        ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_button.setFixedHeight(36)
        ok_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 6px;"
            f"  color: {_TEXT_S};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_SURF2};"
            f"  border-color: {_BORDER_M};"
            f"  color: {_TEXT};"
            f"}}"
        )
        ok_button.clicked.connect(dialog.close)
        sidebar_layout.addWidget(ok_button)

        main_layout.addWidget(sidebar)

        workspace = QFrame()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(28, 24, 28, 24)
        workspace_layout.setSpacing(12)

        workspace_stack = QStackedWidget()
        workspace_stack.setObjectName("IGWorkspaceStack")
        workspace_stack.setStyleSheet("QStackedWidget#IGWorkspaceStack { background: transparent; border: none; }")
        workspace_layout.addWidget(workspace_stack)

        def add_glass_section(layout, label_text, content):
            if not content: return 
            
            lbl = QLabel(label_text)
            lbl.setFont(f_label)
            lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 8px; margin-bottom: 4px; border: none;")
            layout.addWidget(lbl)

            text_edit = QTextEdit()
            text_edit.setFont(f_input)
            text_edit.setPlainText(str(content))
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet(
                f"QTextEdit {{"
                f"  background-color: {_SURF2};"
                f"  color: {_TEXT};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 8px;"
                f"  padding: 12px 14px;"
                f"  line-height: 1.5;"
                f"  selection-background-color: {_WHITE_MUT};"
                f"}}"
                f"QTextEdit:focus {{"
                f"  border-color: {_BORDER_M};"
                f"  background-color: {_SURF3};"
                f"}}"
            )
            text_edit.setMinimumHeight(150)
            layout.addWidget(text_edit)

        def create_page_card():
            card = QFrame()
            card.setObjectName("IGPageCard")
            card.setStyleSheet(
                f"QFrame#IGPageCard {{"
                f"  background-color: {_CARD_BG};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 12px;"
                f"}}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
                "QScrollBar:vertical { background: transparent; width: 8px; }"
                f"QScrollBar::handle:vertical {{ background: {_BORDER_M}; border-radius: 4px; }}"
                f"QScrollBar::handle:vertical:hover {{ background: {_TEXT_S}; }}"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }"
            )
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(8, 4, 8, 12)
            content_layout.setSpacing(12)
            
            scroll.setWidget(content_widget)
            card_layout.addWidget(scroll)
            return card, content_layout

        tab_general_info_text = self.translations.get("btn_general_info_text", "General Info")
        tab_identity_text = self.translations.get("btn_identity_text", "Identity")
        tab_scenario_text = self.translations.get("btn_scenario_text", "Scenario")
        tab_examples_text = self.translations.get("btn_examples_text", "Examples")
        tab_creator_notes_text = self.translations.get("btn_creator_notes_text", "Creator Notes")

        # Page 1: Identity
        page_id_card, layout_id = create_page_card()
        add_glass_section(layout_id, self.translations.get("character_edit_description", "Description"), character_description)
        add_glass_section(layout_id, self.translations.get("character_edit_personality", "Personality"), character_personality)
        workspace_stack.addWidget(page_id_card)
        
        item_id = QtWidgets.QListWidgetItem(tab_identity_text)
        nav_list.addItem(item_id)

        # Page 2: Scenario
        page_sc_card, layout_sc = create_page_card()
        add_glass_section(layout_sc, self.translations.get("character_edit_first_message", "First Message"), first_message)
        add_glass_section(layout_sc, self.translations.get("scenario", "Scenario"), scenario)
        workspace_stack.addWidget(page_sc_card)
        
        item_sc = QtWidgets.QListWidgetItem(tab_scenario_text)
        nav_list.addItem(item_sc)

        # Page 3: Examples
        page_ex_card, layout_ex = create_page_card()
        add_glass_section(layout_ex, self.translations.get("example_messages_title", "Example Messages"), example_messages)
        alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
        add_glass_section(layout_ex, self.translations.get("alternate_greetings_label", "Alternate Greetings"), alt_greets_text)
        workspace_stack.addWidget(page_ex_card)
        
        item_ex = QtWidgets.QListWidgetItem(tab_examples_text)
        nav_list.addItem(item_ex)

        # Page 4: Creator Notes
        if raw_title and len(raw_title) > max_subtitle_length:
            page_notes_card, layout_notes = create_page_card()
            add_glass_section(layout_notes, self.translations.get("creator_info_title", "Full Creator Notes"), character_title)
            workspace_stack.addWidget(page_notes_card)
            
            item_notes = QtWidgets.QListWidgetItem(tab_creator_notes_text)
            nav_list.addItem(item_notes)

        nav_list.currentRowChanged.connect(workspace_stack.setCurrentIndex)
        nav_list.setCurrentRow(0)

        main_layout.addWidget(workspace, 1)
        dialog.exec()
    
    async def load_shared_lorebooks(self, filter_text=""):
        self.clear_scroll_area(self.ui.scrollArea_lorebooks)
        self.lorebook_cards.clear()

        if hasattr(self, 'lorebooks_container') and self.lorebooks_container:
            try:
                self.lorebooks_container.deleteLater()
            except RuntimeError:
                pass
            self.lorebooks_container = None
        
        self.lorebooks_container = QWidget()
        self.lorebooks_grid_layout = QtWidgets.QGridLayout(self.lorebooks_container)
        self.lorebooks_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.lorebooks_grid_layout.setSpacing(15)
        self.ui.scrollArea_lorebooks.setWidget(self.lorebooks_container)

        REGISTRY_URL = "https://raw.githubusercontent.com/jofizcd/sow-data/main/lorebooks_registry.json"
        try:
            def fetch_registry():
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(REGISTRY_URL, timeout=10, context=context) as response:
                    return json.loads(response.read().decode('utf-8'))

            registry = await asyncio.to_thread(fetch_registry)
            lorebooks_list = registry.get("lorebooks", [])
        except Exception as e:
            logger.error(f"Error loading Lorebooks Registry: {e}")
            sow_toast(
                parent=self.main_window,
                title="Connection Error",
                text=f"Failed to fetch lorebooks registry:\n{str(e)}",
                msg_type="error"
            )
            return

        if filter_text:
            lorebooks_list = [lb for lb in lorebooks_list if filter_text.lower() in lb["name"].lower()]

        for i, info in enumerate(lorebooks_list):
            if self.abort_loading: break

            card_widget = LorebookGatewayCard(
                title=info["name"], author=info["author"], description=info["description"],
                entry_count=info["entry_count"], download_url=info["download_url"],
                import_method=self.import_lorebook_from_hub, translations=self.translations
            )
            self.lorebook_cards.append(card_widget)
            
            if i % 2 == 0:
                QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("lorebooks"))
                await asyncio.sleep(0.01)

        self.update_gate_layout("lorebooks")

    async def import_lorebook_from_hub(self, title, url):
        sow_toast(self.main_window, "Gateway Hub", f"Downloading lorebook '{title}'...", "info")
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch file: status {response.status}")
                    lore_data = await response.json(content_type=None)

            config = self.configuration_settings.load_configuration()
            lorebooks = config.setdefault("user_data", {}).setdefault("lorebooks", {})

            new_name = lore_data.get("name", title)
            orig_name = new_name
            counter = 1
            while new_name in lorebooks:
                new_name = f"{orig_name}_{counter}"
                counter += 1

            lore_data["name"] = new_name
            lorebooks[new_name] = lore_data
            self.configuration_settings.save_configuration_edit(config)

            sow_toast(
                parent=self.main_window,
                title="Import Complete",
                text=f"Lorebook '{new_name}' successfully added to your list!",
                msg_type="success"
            )
        except Exception as e:
            logger.error(f"Failed to download lorebook: {e}")
            sow_toast(self.main_window, "Download Error", f"Could not import: {e}", "error")

    async def load_shared_scenes(self, filter_text=""):
        self.clear_scroll_area(self.ui.scrollArea_scenes)
        self.scene_cards.clear()

        if hasattr(self, 'scenes_container') and self.scenes_container:
            try:
                self.scenes_container.deleteLater()
            except RuntimeError:
                pass
            self.scenes_container = None

        self.scenes_container = QWidget()
        self.scenes_grid_layout = QtWidgets.QGridLayout(self.scenes_container)
        self.scenes_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.scenes_grid_layout.setSpacing(15)
        self.ui.scrollArea_scenes.setWidget(self.scenes_container)

        REGISTRY_URL = "https://raw.githubusercontent.com/jofizcd/sow-data/main/stages_registry.json"
        try:
            def fetch_registry():
                context = ssl._create_unverified_context()
                with urllib.request.urlopen(REGISTRY_URL, timeout=10, context=context) as response:
                    return json.loads(response.read().decode('utf-8'))

            registry = await asyncio.to_thread(fetch_registry)
            scenes_list = registry.get("scenes", [])
        except Exception as e:
            logger.error(f"Error loading Stages Registry: {e}")

        if filter_text:
            scenes_list = [sc for sc in scenes_list if filter_text.lower() in sc["title"].lower()]

        for i, info in enumerate(scenes_list):
            if self.abort_loading: break

            card_widget = SceneGatewayCard(
                title=info["title"], author=info["author"], description=info["description"],
                starting_location=info["starting_location"],
                download_url=info["download_url"], import_method=self.import_scene_from_hub, translations=self.translations
            )
            self.scene_cards.append(card_widget)

            if i % 2 == 0:
                QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("scenes"))
                await asyncio.sleep(0.01)

        self.update_gate_layout("scenes")

    async def import_scene_from_hub(self, title, url):
        sow_toast(self.main_window, "Gateway Hub", f"Downloading scene '{title}'...", "info")
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        raise Exception(f"Server returned code {response.status}")
                    scene_data = await response.json(content_type=None)

            from app.gui.soul_stage_page import _load_scenes, _save_scenes
            d = _load_scenes()
            scene_id = str(uuid.uuid4())
            d["scenes"][scene_id] = scene_data
            _save_scenes(d)

            sow_toast(
                parent=self.main_window,
                title="Import Complete",
                text=f"Scene '{title}' was added successfully! Open Soul Stage page to play.",
                msg_type="success"
            )
            if hasattr(self.ui, 'soul_stage_page'):
                self.ui.soul_stage_page.on_page_shown()
        except Exception as e:
            logger.error(f"Failed to download scene: {e}")
            sow_toast(self.main_window, "Download Error", f"Could not import: {e}", "error")
    ### CHARACTER GATEWAY ==============================================================================

    ### MODELS HUB =====================================================================================
    def show_my_models(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
        self.stop_search_worker()
        if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
            self.model_information_widget.setParent(None)
            self.model_information_widget.deleteLater()
            self.model_information_widget = None
        self.ui.listWidget_models_hub.clear()
        self.ui.pushButton_models_hub_my_models.setChecked(True)

        self.ui.listWidget_models_hub.setSpacing(8)

        models_dir = self.configuration_settings.get_main_setting("models_directory") \
                     or "assets\\local_llm"
        models_dir = os.path.normpath(models_dir)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)

        header_widget = QWidget()
        header_widget.setFixedHeight(50) 
        header_widget.setStyleSheet("background: rgba(255, 255, 255, 0.03); border-bottom: 1px solid rgba(255,255,255,0.05);")
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 0, 15, 0) 
        header_layout.setSpacing(12)

        folder_icon_lbl = QLabel("📂")
        folder_icon_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        folder_icon_lbl.setFixedWidth(24)
        header_layout.addWidget(folder_icon_lbl)

        dir_label = QLabel(models_dir)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        dir_label.setFont(font)
        dir_label.setToolTip(models_dir)
        dir_label.setStyleSheet(
            "color: rgba(255,255,255,0.6); font-family: 'Inter Tight Medium';"
            " font-size: 11px; background: transparent; border: none;"
        )
        header_layout.addWidget(dir_label, 1)

        _btn_style = """
            QPushButton {
                background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.85);
                border: 1px solid rgba(255,255,255,0.15); border-radius: 8px;
                font-family: 'Inter Tight SemiBold'; font-size: 11px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.15); color: #fff;
                border-color: rgba(255,255,255,0.3);
            }
        """

        btn_open = QPushButton(self.translations.get("models_hub_open_folder_btn", "🗁  Open Folder"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        btn_open.setFont(font)
        btn_open.setFixedHeight(28)
        btn_open.setStyleSheet(_btn_style)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_open.setIcon(QtGui.QIcon("app/gui/icons/folder.png"))
        btn_open.setIconSize(QtCore.QSize(16, 16))
        btn_open.clicked.connect(lambda: self._open_models_folder())
        header_layout.addWidget(btn_open)

        btn_change = QPushButton(self.translations.get("models_hub_change_folder_btn", "⟳  Change Directory"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        btn_change.setFont(font)
        btn_change.setFixedHeight(28)
        btn_change.setStyleSheet(_btn_style)
        btn_change.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_change.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_change.setIcon(QtGui.QIcon("app/gui/icons/reload.png"))
        btn_change.setIconSize(QtCore.QSize(16, 16))
        btn_change.clicked.connect(lambda: self._change_models_directory())
        header_layout.addWidget(btn_change)

        header_item = QtWidgets.QListWidgetItem()
        header_item.setSizeHint(QtCore.QSize(0, 50)) 
        header_item.setFlags(Qt.ItemFlag.NoItemFlags)
        
        self.ui.listWidget_models_hub.addItem(header_item)
        self.ui.listWidget_models_hub.setItemWidget(header_item, header_widget)

        gguf_files = []
        for root, dirs, files in os.walk(models_dir):
            for file in files:
                if file.endswith(".gguf"):
                    full_path = os.path.join(root, file)
                    base_name = os.path.splitext(file)[0]
                    size_bytes = os.path.getsize(full_path)
                    gguf_files.append((base_name, full_path, size_bytes))
        
        current_default_path = self.configuration_settings.get_main_setting("local_llm")
        current_default_name = None

        if current_default_path and os.path.exists(current_default_path):
            filename_with_ext = os.path.basename(current_default_path)
            current_default_name = os.path.splitext(filename_with_ext)[0]

        if not current_default_path or not os.path.exists(current_default_path):
            if gguf_files:
                first_model_name, first_model_path, _ = gguf_files[0]
                self.configuration_settings.update_main_setting("local_llm", first_model_path)
                current_default_name = first_model_name
                current_default_path = first_model_path
            else:
                self.configuration_settings.update_main_setting("local_llm", None)
                item = QtWidgets.QListWidgetItem(self.translations.get("models_hub_no_models", "The directory with the local language models is empty"))
                font = QtGui.QFont()
                font.setFamily("Inter Tight Medium")
                font.setPointSize(11)
                font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
                item.setFont(font)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.ui.listWidget_models_hub.addItem(item)
                return

        sorted_files = []
        default_file = None

        for name, path, size in gguf_files:
            if name == current_default_name:
                default_file = (name, path, size)
            else:
                sorted_files.append((name, path, size))

        if default_file:
            sorted_files.insert(0, default_file)

        is_server_running = False
        if hasattr(self, 'local_server_manager') and self.local_server_manager is not None:
            is_server_running = getattr(self.local_server_manager, 'model_loaded', False)
        
        for name, path, size in sorted_files:
            widget = ModelListItemWidget(
                model_name=name,
                file_size_bytes=size,
                full_path=path,
                refresh_method=self.show_my_models,
                launch_server_method=self.on_pushButton_launch_server_clicked,
                
                stop_server_method=self.local_server_manager.on_shutdown_button_clicked if hasattr(self, 'local_server_manager') else None,
                
                ui=self.ui,
                parent=self.ui.listWidget_models_hub,
                is_server_running=is_server_running
            )
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(QtCore.QSize(0, 85)) 
            item.setSizeHint(widget.sizeHint())
            self.ui.listWidget_models_hub.addItem(item)
            self.ui.listWidget_models_hub.setItemWidget(item, widget)

    def _open_models_folder(self):
        models_dir = self.configuration_settings.get_main_setting("models_directory") \
                     or "assets\\local_llm"
        models_dir = os.path.normpath(models_dir)
        if not os.path.exists(models_dir):
            os.makedirs(models_dir, exist_ok=True)
        try:
            os.startfile(models_dir)
        except Exception as e:
            logger.warning(f"[ModelsHub] Cannot open folder: {e}")

    def _change_models_directory(self):
        current_dir = self.configuration_settings.get_main_setting("models_directory") \
                      or "assets\\local_llm"
        new_dir = QFileDialog.getExistingDirectory(
            self.main_window,
            "Select LLM Models Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if new_dir:
            new_dir = os.path.normpath(new_dir)
            self.configuration_settings.update_main_setting("models_directory", new_dir)
            logger.info(f"[ModelsHub] Models directory changed to: {new_dir}")
            self.show_my_models()

    def show_recommended_models(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
        self.stop_search_worker()
        if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
            self.model_information_widget.setParent(None)
            self.model_information_widget.deleteLater()
            self.model_information_widget = None
        self.ui.listWidget_models_hub.clear()
        self.ui.listWidget_models_hub.setSpacing(8)
        
        available_ram = self.configuration_settings.get_main_setting("available_memory")
        
        has_gpu = False
        gpu_vram_gb = 0
        
        try:
            if torch.cuda.is_available():
                has_gpu = True
                gpu_vram_bytes = torch.cuda.get_device_properties(0).total_memory
                gpu_vram_gb = gpu_vram_bytes / (1024**3)
        except:
            pass
        
        self.recommendations_worker = ModelRecommendations(
            available_ram_gb=available_ram,
            has_gpu=has_gpu,
            gpu_vram_gb=gpu_vram_gb
        )
        try:
            self.recommendations_worker.progress.disconnect()
            self.recommendations_worker.finished.disconnect()
            self.recommendations_worker.error.disconnect()
        except TypeError:
            pass

        self.recommendations_worker.progress.connect(self.add_recommended_model_to_list)
        self.recommendations_worker.finished.connect(self.on_worker_complete)
        self.recommendations_worker.error.connect(self.show_error)
        self.recommendations_worker.start()
    
    def stop_recommendation_worker(self):
        if self.recommendations_worker and self.recommendations_worker.isRunning():
            self.recommendations_worker.terminate()
            self.recommendations_worker.wait()
            self.recommendations_worker = None

    def show_popular_models(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
        self.stop_search_worker()
        if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
            self.model_information_widget.setParent(None)
            self.model_information_widget.deleteLater()
            self.model_information_widget = None
        self.ui.listWidget_models_hub.clear()
        self.ui.listWidget_models_hub.setSpacing(8)

        self.popular_worker= ModelPopular()
        try:
            self.popular_worker.progress.disconnect()
            self.popular_worker.finished.disconnect()
            self.popular_worker.error.disconnect()
        except TypeError:
            pass

        self.popular_worker.progress.connect(self.add_model_to_list)
        self.popular_worker.finished.connect(self.on_worker_complete)
        self.popular_worker.error.connect(self.show_error)
        self.popular_worker.start()
    
    def stop_popular_worker(self):
        if self.popular_worker and self.popular_worker.isRunning():
            self.popular_worker.terminate()
            self.popular_worker.wait()
            self.popular_worker = None
    
    def start_search(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
        self.stop_search_worker()
        if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
            self.model_information_widget.setParent(None)
            self.model_information_widget.deleteLater()
            self.model_information_widget = None
        
        query = self.ui.lineEdit_search_model.text().strip()
        self.ui.listWidget_models_hub.clear()
        self.ui.lineEdit_search_model.clear()
        self.ui.pushButton_models_hub_my_models.setChecked(False)
        self.ui.pushButton_models_hub_popular.setChecked(False)
        self.ui.pushButton_models_hub_recommendations.setChecked(False)
        self.ui.listWidget_models_hub.clear()
        self.ui.listWidget_models_hub.setSpacing(8)
        
        self.search_worker = ModelSearch(query)
        try:
            self.search_worker.progress.disconnect()
            self.search_worker.finished.disconnect()
            self.search_worker.error.disconnect()
        except TypeError:
            pass
        
        self.search_worker.progress.connect(self.add_model_to_list)
        self.search_worker.finished.connect(self.on_worker_complete)
        self.search_worker.error.connect(self.show_error)
        self.search_worker.start()
    
    def stop_search_worker(self):
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()
            self.search_worker = None

    def add_model_to_list(self, model_id, author, downloads):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, 85)) 
        widget = ModelItemWidget(model_id, author, downloads, self.show_model_info, 
                                 self.download_model, parent=self.ui.listWidget_models_hub, 
                                 download_button_translation=self.translations.get("button_download_model", " Download model"),
                                 author_label_translation=self.translations.get("models_hub_author", " Author - "),
                                 downloads_label_translation=self.translations.get("models_hub_downloads", " Downloads - "))
        item.setSizeHint(widget.sizeHint())
        self.ui.listWidget_models_hub.addItem(item)
        self.ui.listWidget_models_hub.setItemWidget(item, widget)

    def add_recommended_model_to_list(self, model_id, author, downloads, compatibility_text, is_compatible):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(0, 85)) 
        widget = RecommendedModelItemWidget(
            model_id, 
            author, 
            downloads, 
            compatibility_text, 
            is_compatible,
            self.show_model_info, 
            self.download_model, 
            parent=self.ui.listWidget_models_hub, 
            download_button_translation=self.translations.get("button_download_model", " Download model"),
            author_label_translation=self.translations.get("models_hub_author", " Author - "),
            downloads_label_translation=self.translations.get("models_hub_downloads", " Downloads - "),
            compatibility_label_translation=self.translations.get("models_hub_compatibility", " Compatibility: ")
        )
        item.setSizeHint(widget.sizeHint())
        self.ui.listWidget_models_hub.addItem(item)
        self.ui.listWidget_models_hub.setItemWidget(item, widget)

    def on_worker_complete(self):
        pass

    def show_model_info(self, model_id):
        self.selected_model = model_id

        if self.model_information_widget:
            self.model_information_widget.deleteLater()
            self.model_information_widget = None

        self.info_worker = ModelInformation(self.selected_model)
        self.info_worker.finished.connect(self.on_info_received)
        self.info_worker.error.connect(self.show_error)
        self.info_worker.start()
    
    def create_model_info_widget(self, model_data):
        widget = QWidget()
        widget.setObjectName("model_info_card")
        widget.setMinimumWidth(320)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(-5, 0)
        widget.setGraphicsEffect(shadow)

        widget.setStyleSheet("""
            QWidget#model_info_card {
                background-color: rgba(20, 20, 25, 0.85);
                border-left: 1px solid rgba(255, 255, 255, 0.1);
                border-top-right-radius: 24px;
                border-bottom-right-radius: 24px;
            }
        """)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(25, 25, 20, 25)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        header_layout.setSpacing(10)

        title_label = QLabel(model_data.get('id', 'Unknown Model'))
        font_title = QtGui.QFont("Inter Tight SemiBold", 14, QtGui.QFont.Weight.Bold)
        font_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        title_label.setFont(font_title)
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")
        title_label.setWordWrap(True)

        close_button = QPushButton("✕")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        close_button.setFont(font)
        close_button.setFixedSize(30, 30)
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        close_button.clicked.connect(lambda: self.close_model_info())
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                font-family: 'Inter Tight SemiBold';
                font-size: 14px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.2);
                color: #EF9A9A;
                border: 1px solid rgba(244, 67, 54, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.1);
            }
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)

        main_layout.addLayout(header_layout)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        badge_base_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Inter Tight Medium';
                font-size: 11px;
            }
        """

        author = model_data.get('author', '—')
        author_label = QLabel(f"👤 {author}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        author_label.setFont(font)
        author_label.setStyleSheet(badge_base_style)
        meta_layout.addWidget(author_label)

        downloads = model_data.get('downloads', 0)
        dl_label = QLabel(f"⬇️ {downloads:,}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dl_label.setFont(font)
        dl_label.setStyleSheet(badge_base_style)
        meta_layout.addWidget(dl_label)

        likes = model_data.get('likes', 0)
        like_label = QLabel(f"❤️ {likes:,}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        like_label.setFont(font)
        like_label.setStyleSheet("""
            QLabel {
                background-color: rgba(244, 67, 54, 0.1);
                color: #E57373;
                border: 1px solid rgba(244, 67, 54, 0.2);
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Inter Tight Medium';
                font-size: 11px;
            }
        """)
        meta_layout.addWidget(like_label)

        meta_layout.addStretch()
        main_layout.addLayout(meta_layout)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; max-height: 1px;")
        main_layout.addWidget(sep)

        tags = model_data.get("tags", "").strip()
        if tags:
            tags_list = [t.strip() for t in tags.split(",") if t.strip()][:6]
            tags_html = " ".join(
                f'<span style="background-color: #2a2a35; color: #a0a0c0; font-family: \'Inter Tight Medium\'; font-size: 11px;">&nbsp;{tag}&nbsp;</span>'
                for tag in tags_list
            )
            tags_label = QLabel(tags_html)
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            tags_label.setFont(font)
            tags_label.setTextFormat(Qt.TextFormat.RichText)
            tags_label.setWordWrap(True)
            main_layout.addWidget(tags_label)

        description = model_data.get("description", "No description available.").strip()

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setOpenExternalLinks(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextBrowserInteraction)
        
        font_desc = QtGui.QFont("Inter Tight Medium", 10)
        font_desc.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        desc_label.setFont(font_desc)
        
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.75);
                background: transparent;
                line-height: 1.4;
            }
            QLabel a {
                color: #64B5F6;
                text-decoration: none;
            }
            QLabel a:hover {
                text-decoration: underline;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(desc_label)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        main_layout.addWidget(scroll, stretch=1)

        return widget

    def on_info_received(self, data):
        if self.model_information_widget and self.model_information_widget.layout():
            while self.model_information_widget.layout().count():
                item = self.model_information_widget.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        elif not self.model_information_widget:
            curated_info = self.get_curated_model_info(data.get('id', ''))
            
            if curated_info:
                self.model_information_widget = self.create_curated_model_info_widget(curated_info)
            else:
                self.model_information_widget = self.create_model_info_widget(data)

            if self.ui.centralwidget.layout() is None:
                central_layout = QtWidgets.QHBoxLayout(self.ui.centralwidget)
            else:
                central_layout = self.ui.centralwidget.layout()
            central_layout.addWidget(self.model_information_widget)
        else:
            self.clear_layout(self.model_info_layout)

    def get_curated_model_info(self, model_id):
        try:
            cache_file = "app/utils/ai_clients/backend/_temp/recommended_models_cache.json"
            
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    models = data.get("models", [])
                    
                    for model in models:
                        if model.get("hf_id") == model_id:
                            return model
        except Exception as e:
            logger.warning(f"Couldn't load model information from cache: {e}")
        
        return None

    def create_curated_model_info_widget(self, model_data):
        widget = QWidget()
        widget.setObjectName("model_info_card")
        widget.setMinimumWidth(320)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(-5, 0)
        widget.setGraphicsEffect(shadow)

        widget.setStyleSheet("""
            QWidget#model_info_card {
                background-color: rgba(20, 20, 25, 0.85);
                border-left: 1px solid rgba(255, 255, 255, 0.1);
                border-top-right-radius: 24px;
                border-bottom-right-radius: 24px;
            }
        """)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(25, 25, 20, 25)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 5)
        header_layout.setSpacing(10)

        name_label = QLabel(model_data.get('name', 'Unknown Model'))
        name_label.setWordWrap(True)
        font_title = QtGui.QFont("Inter Tight SemiBold", 14, QtGui.QFont.Weight.Bold)
        font_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font_title)
        name_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")

        close_button = QPushButton("✕")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        close_button.setFont(font)
        close_button.setFixedSize(30, 30)
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        close_button.clicked.connect(lambda: self.close_model_info())
        close_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                font-family: 'Inter Tight SemiBold';
                font-size: 14px;
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 0.2);
                color: #EF9A9A;
                border: 1px solid rgba(244, 67, 54, 0.4);
            }
            QPushButton:pressed {
                background-color: rgba(244, 67, 54, 0.1);
            }
        """)

        header_layout.addWidget(name_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignTop)

        main_layout.addLayout(header_layout)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(8)

        badge_base_style = """
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Inter Tight Medium';
                font-size: 11px;
            }
        """

        author = model_data.get('author', '—')
        author_label = QLabel(f"👤 {author}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        author_label.setFont(font)
        author_label.setStyleSheet(badge_base_style)
        meta_layout.addWidget(author_label)

        downloads = model_data.get('downloads', 0)
        try:
            formatted_downloads = f"{int(downloads):,}"
        except (ValueError, TypeError):
            formatted_downloads = str(downloads)

        dl_label = QLabel(f"⬇️ {formatted_downloads}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dl_label.setFont(font)
        dl_label.setStyleSheet(badge_base_style)
        meta_layout.addWidget(dl_label)

        likes = model_data.get('likes', 0)
        try:
            formatted_likes = f"{int(likes):,}"
        except (ValueError, TypeError):
            formatted_likes = str(likes)

        like_label = QLabel(f"❤️ {formatted_likes}")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        like_label.setFont(font)
        like_label.setStyleSheet("""
            QLabel {
                background-color: rgba(244, 67, 54, 0.1);
                color: #E57373;
                border: 1px solid rgba(244, 67, 54, 0.2);
                border-radius: 6px;
                padding: 4px 8px;
                font-family: 'Inter Tight Medium';
                font-size: 11px;
            }
        """)
        meta_layout.addWidget(like_label)

        meta_layout.addStretch()
        main_layout.addLayout(meta_layout)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; max-height: 1px;")
        main_layout.addWidget(sep)

        match self.selected_language:
            case 0:
                description = model_data.get("description_en", "No description available.").strip()
            case 1:
                description = model_data.get("description_ru", "No description available.").strip()
            case _:
                description = model_data.get("description_en", "No description available.").strip()

        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setOpenExternalLinks(True)
        desc_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextBrowserInteraction)
        
        font_desc = QtGui.QFont("Inter Tight Medium", 10)
        font_desc.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        desc_label.setFont(font_desc)
        
        desc_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.75);
                background: transparent;
                line-height: 1.4;
            }
            QLabel a {
                color: #64B5F6;
                text-decoration: none;
            }
            QLabel a:hover {
                text-decoration: underline;
            }
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(desc_label)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(255, 255, 255, 0.15);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        main_layout.addWidget(scroll, stretch=1)

        if "optimal_quant" in model_data and model_data["optimal_quant"]:
            quant_row = QHBoxLayout()
            quant_row.setSpacing(12)
            quant_row.setContentsMargins(0, 8, 0, 4)

            quant_title = QLabel("Recommended quantization:")
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            quant_title.setFont(font)
            quant_title.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-family: 'Inter Tight Medium'; font-size: 12px;")

            quant_value = QLabel(model_data["optimal_quant"])
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            quant_value.setFont(font)
            quant_value.setStyleSheet("""
                QLabel {
                    background-color: rgba(76, 175, 80, 0.15);
                    color: #81C784;
                    border: 1px solid rgba(76, 175, 80, 0.3);
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-family: 'Inter Tight SemiBold';
                    font-size: 12px;
                }
            """)

            quant_row.addWidget(quant_title)
            quant_row.addWidget(quant_value)
            quant_row.addStretch()

            main_layout.addLayout(quant_row)

        if "author_notes" in model_data and model_data["author_notes"]:
            notes_title = QLabel("Developer's note:")
            notes_title.setStyleSheet("""
                color: rgba(255, 255, 255, 0.5);
                font-family: 'Inter Tight Medium';
                font-size: 12px;
                padding-top: 8px;
            """)
            main_layout.addWidget(notes_title)

            notes_text = QLabel(model_data["author_notes"])
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            notes_text.setFont(font)
            notes_text.setWordWrap(True)
            notes_text.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 193, 7, 0.1);
                    color: #FFE082;
                    border-left: 3px solid #FFCA28;
                    border-top-right-radius: 4px;
                    border-bottom-right-radius: 4px;
                    padding: 10px 14px;
                    font-family: 'Inter Tight Medium';
                    font-size: 13px;
                    line-height: 1.4;
                }
            """)
            main_layout.addWidget(notes_text)

        return widget
    
    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

    def close_model_info(self):
        if self.model_information_widget:
            self.model_information_widget.deleteLater()
            self.model_information_widget = None

    def download_model(self, model_id):
        self.selected_model = model_id

        if self.model_information_widget:
            self.model_information_widget.deleteLater()
            self.model_information_widget = None

        self.files_worker = ModelRepoFiles(self.selected_model)
        self.files_worker.finished.connect(lambda files: self.on_files_loaded(files, model_id=self.selected_model))
        self.files_worker.error.connect(self.show_error)
        self.files_worker.start()
        
    def on_files_loaded(self, files, model_id):
        if not files:
            parent = self.main_window if hasattr(self, "main_window") else None
            
            sow_toast(
                parent=parent,
                title=self.translations.get("no_files_title", "No files"),
                text=self.translations.get("no_files_desc", "There are no .gguf files in this repository."),
                msg_type="info"
            )
            return

        dialog = FileSelectorDialog(files, self.translations, model_id=model_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_file = dialog.selected_file
            self.start_download(selected_file)

    def start_download(self, filename):
        self.download_worker = FileDownloader(self.selected_model, filename, self.translations)
        self.download_worker.finished.connect(self.on_download_complete)
        self.download_worker.error.connect(self.show_error)
        self.download_worker.start()

    def on_download_complete(self, path):
        parent = self.main_window if hasattr(self, "main_window") else None
        
        short_path = f".../{Path(path).name}" if len(str(path)) > 50 else path
        
        sow_toast(
            parent=parent,
            title=self.translations.get("download_complete_title", "Download Complete"),
            text=self.translations.get("download_complete_desc", f"The model has been downloaded successfully.\nSaved to: {short_path}"),
            msg_type="success"
        )

    def show_error(self, message):
        parent = self.main_window if hasattr(self, "main_window") else None
        
        sow_toast(
            parent=parent,
            title=self.translations.get("error_title", "Error"),
            text=message,
            msg_type="error"
        )
    ### MODELS HUB =====================================================================================

    ### IMPLEMENTATION OF CHAT WITH CHARACTER =====================================================================
    async def open_chat(self, character_name: str) -> None:
        """
        Opens a chat tab with a selected character with certain settings based on the character's data.
        """
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_container.setSpacing(0)

        self.chat_messages_widget = QWidget()
        self.chat_messages_widget.setStyleSheet("background: transparent;")
        self.chat_messages_widget.setLayout(self.chat_container)
        self.chat_messages_widget.setMaximumWidth(850)

        self.chat_wrapper_layout = QHBoxLayout()
        self.chat_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_wrapper_layout.setSpacing(0)
        self.chat_wrapper_layout.addStretch()
        self.chat_wrapper_layout.addWidget(self.chat_messages_widget)
        self.chat_wrapper_layout.addStretch()

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: transparent;")
        self.chat_widget.setLayout(self.chat_wrapper_layout)

        self.ui.scrollArea_chat.setWidget(self.chat_widget)
        self.ui.scrollArea_chat.setWidgetResizable(True)

        # --- General settings ---
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        model_background_image = self.configuration_settings.get_main_setting("model_background_image")
        soul_memory = self.configuration_settings.get_main_setting("soul_memory")

        # --- Character configuration ---
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info.get("conversation_method", "Local LLM")

        self.current_active_character = character_name
        
        current_chat = character_info.get("current_chat")
        chats = character_info.get("chats", {})

        if not current_chat or current_chat not in chats:
            current_chat = str(uuid.uuid4())
            first_message = character_info.get("first_message", "")
            alternate_greetings = character_info.get("alternate_greetings", [])
            
            variants = [{"variant_id": "default", "text": first_message}]
            if isinstance(alternate_greetings, list):
                for i, greeting in enumerate(alternate_greetings):
                    if greeting.strip():
                        variants.append({"variant_id": f"v{i+1}", "text": greeting.strip()})

            message_id = str(uuid.uuid4())
            main_message = {
                "message_id": message_id,
                "sequence_number": 1,
                "author_name": character_name,
                "is_user": False,
                "current_variant_id": "default",
                "variants": variants
            }

            chat_history = [{"user": "", "character": first_message}]
            default_chat_name = self.translations.get("default_chat_name", "Default Chat")
            new_chat = {
                "name": default_chat_name,
                "created_at": datetime.datetime.now().isoformat(),
                "current_emotion": "neutral",
                "chat_history": chat_history,
                "chat_content": {message_id: main_message},
            }

            chats[current_chat] = new_chat
            configuration_data["character_list"][character_name]["chats"] = chats
            configuration_data["character_list"][character_name]["current_chat"] = current_chat
            self.configuration_characters.save_configuration_edit(configuration_data)

        current_emotion = chats[current_chat].get("current_emotion", "neutral")

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        self.messages = {}
        self.message_order = []

        self._chat_chunk_size = 30
        self._chat_loaded_count = 0
        self._chat_is_loading_history = False
        self._chat_all_messages = []
        
        scrollbar = self.ui.scrollArea_chat.verticalScrollBar()
        try:
            scrollbar.valueChanged.disconnect(self._on_chat_scroll)
        except TypeError:
            pass
        scrollbar.valueChanged.connect(self._on_chat_scroll)
        
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")

        self.ui.pushButton_author_notes.show()
        self.ui.pushButton_summary.show()
        if soul_memory:
            self.ui.pushButton_force_memory.show()
            self.ui.pushButton_soul_memory.show()
        else:
            self.ui.pushButton_force_memory.hide()
            self.ui.pushButton_soul_memory.hide()

        character_title = character_info.get("character_title")

        if hasattr(self, 'chat_tts_worker') and self.chat_tts_worker:
            try:
                self.chat_tts_worker.stop()
                self.chat_tts_worker.deleteLater()
            except Exception:
                pass
            self.chat_tts_worker = None

        current_text_to_speech = self.configuration_characters.get_character_data(
            character_name, "current_text_to_speech"
        )
        elevenlabs_voice_id = self.configuration_characters.get_character_data(
            character_name, "elevenlabs_voice_id"
        )

        if current_text_to_speech not in ("Nothing", None):
            from app.utils.text_to_speech import TTSWorker
            output_device = self.configuration_settings.get_main_setting("output_device_real_index")
            lang = "ru" if self.configuration_settings.get_main_setting("translator") != 0 else "en"
            self.chat_tts_worker = TTSWorker(
                current_text_to_speech, character_name, elevenlabs_voice_id, language=lang
            )
            self.chat_tts_worker.playback_worker.lipsync_signal.connect(self.update_lip_sync)
            self.chat_tts_worker.start()
            logger.info(f"Chat TTS Worker started: {current_text_to_speech}")
        else:
            self.chat_tts_worker = None
        
        if conversation_method == "Local LLM":
            local_llm = self.configuration_settings.get_main_setting("local_llm")
            if local_llm is None:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_llm_error_title", "Configuration Error"),
                    text=self.translations.get("llm_error_body", "Choose Local LLM in the options."),
                    msg_type="error",
                    duration=6000
                )
                return

        personas_data = self.configuration_settings.get_user_data("personas") or {}
        current_persona = character_info.get("selected_persona")
        if current_persona == "None" or current_persona is None or current_persona not in personas_data:
            user_name = "User"
            self.user_avatar = "app/gui/icons/person.png"
        else:
            try:
                user_name = personas_data[current_persona].get("user_name", "User")
                self.user_avatar = personas_data[current_persona].get("user_avatar", "app/gui/icons/person.png")
            except Exception as e:
                user_name = "User"
                self.user_avatar = "app/gui/icons/person.png"

        if user_name:
            self.ui.textEdit_write_user_message.setPlaceholderText(self.translations.get("user_message_textEdit", f"Write your message as {user_name}").format(user_name=user_name))
        else:
            self.ui.textEdit_write_user_message.setPlaceholderText(self.translations.get("user_message_textEdit_default", "Write your message as User"))

        self.ui.character_name_chat.setText(character_name)

        self.render_chat_hud(character_name)
        
        max_words = 10
        if character_title:
            words = character_title.split()
            if len(words) > max_words:
                cropped_description = " ".join(words[:max_words]) + "..."
                self.ui.character_description_chat.setText(cropped_description)
            else:
                cropped_description = character_title
                self.ui.character_description_chat.setText(cropped_description)

        if sow_system_status and current_sow_system_mode != "Nothing":
            if current_sow_system_mode in ["Live2D Model", "VRM"]:
                for i in reversed(range(self.ui.centralwidget.layout().count())):
                    item = self.ui.centralwidget.layout().itemAt(i)
                    widget = item.widget()
                    if widget and widget.objectName() == "expression_widget":
                        widget.deleteLater()
                        self.ui.centralwidget.layout().takeAt(i)
                        
            self.expression_widget = QtWidgets.QWidget(parent=self.ui.centralwidget)
            self.expression_widget.setObjectName("expression_widget")
            
            expression_layout = QtWidgets.QHBoxLayout(self.expression_widget)
            expression_layout.setContentsMargins(0, 0, 0, 0)
            expression_layout.setSpacing(0)

            self.avatar_resizer = QtWidgets.QFrame(self.expression_widget)
            self.avatar_resizer.setCursor(QtCore.Qt.CursorShape.SplitHCursor)
            self.avatar_resizer.setFixedWidth(3)
            self.avatar_resizer.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            
            self.avatar_resizer.setAttribute(QtCore.Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
            self.avatar_resizer.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, True)

            self.avatar_resizer.setStyleSheet("""
                background-color: #4a4a4a;
                border-left: 1px solid #666666;
                border-right: 1px solid #666666;
            """)
            self.avatar_resizer.enterEvent = lambda e: self.avatar_resizer.setStyleSheet("""
                background-color: #5a5a5a;
                border-left: 1px solid #888888;
                border-right: 1px solid #888888;
            """)
            self.avatar_resizer.leaveEvent = lambda e: self.avatar_resizer.setStyleSheet("""
                background-color: #4a4a4a;
                border-left: 1px solid #666666;
                border-right: 1px solid #666666;
            """)
            
            self.avatar_resizer.is_dragging = False
            self.avatar_resizer.start_x = 0
            self.avatar_resizer.start_width = 0
            
            def resizer_mouse_press(e):
                if e.button() == QtCore.Qt.MouseButton.LeftButton:
                    self.avatar_resizer.is_dragging = True
                    self.avatar_resizer.start_x = e.globalPosition().x()
                    self.avatar_resizer.start_width = self.expression_widget.width()
                    e.accept()
                    
            def resizer_mouse_move(e):
                if getattr(self.avatar_resizer, 'is_dragging', False):
                    delta = self.avatar_resizer.start_x - e.globalPosition().x()
                    new_width = max(200, min(800, self.avatar_resizer.start_width + delta))
                    self.expression_widget.setFixedWidth(int(new_width))
                    e.accept()
                    
            def resizer_mouse_release(e):
                if e.button() == QtCore.Qt.MouseButton.LeftButton:
                    self.avatar_resizer.is_dragging = False
                    e.accept()

            self.avatar_resizer.mousePressEvent = resizer_mouse_press
            self.avatar_resizer.mouseMoveEvent = resizer_mouse_move
            self.avatar_resizer.mouseReleaseEvent = resizer_mouse_release
            
            expression_layout.addWidget(self.avatar_resizer)

            self.stackedWidget_expressions = QtWidgets.QStackedWidget(parent=self.expression_widget)
            self.stackedWidget_expressions.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
            self.stackedWidget_expressions.setObjectName("stackedWidget_expressions")

            if current_sow_system_mode == "Live2D Model":
                self.expression_widget.setMinimumSize(QtCore.QSize(320, 0))
                if model_background_type == 0:
                    match model_background_color:
                        case 0: background_color = 0x000000
                        case 1: background_color = 0x1A202F
                        case 2: background_color = 0x2C1A22
                        case 3: background_color = 0x222B24
                        case 4: background_color = 0x2E2232
                        case 5: background_color = 0x292929
                    css_background = f"#{background_color:06X}"
                    self.expression_widget.setStyleSheet(f"background-color: {css_background}; border: 1px solid rgb(35, 35, 40);")
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")
                    self.expression_widget.setStyleSheet(f"background-color: rgb(27, 27, 27); border-image: url({model_background_image});")
            elif current_sow_system_mode == "Expressions Images":
                self.expression_widget.setMinimumSize(QtCore.QSize(320, 0))
                if model_background_type == 0:
                    match model_background_color:
                        case 0: background_color = 0x000000
                        case 1: background_color = 0x1A202F
                        case 2: background_color = 0x2C1A22
                        case 3: background_color = 0x222B24
                        case 4: background_color = 0x2E2232
                        case 5: background_color = 0x292929
                    css_background = f"#{background_color:06X}"
                    self.expression_widget.setStyleSheet(f"background-color: {css_background};")
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")
                    self.expression_widget.setStyleSheet(f"background-color: rgb(27, 27, 27); border-image: url({model_background_image});")
            elif current_sow_system_mode == "VRM":
                self.expression_widget.setMinimumSize(QtCore.QSize(320, 0))
                self.expression_widget.setStyleSheet("background-color: rgb(27, 27, 27);")

            if current_sow_system_mode == "Live2D Model":
                self.live2d_page = QtWidgets.QWidget()
                self.live2d_page.setObjectName("live2d_page")

                model_json_path = self.find_model_json(live2d_model_folder)
                self.update_model_json(model_json_path, self.emotion_resources)

                self.live2d_widget = Live2DWidget(model_path=model_json_path, character_name=character_name)
                self.live2d_widget.setStyleSheet("background: transparent;")
                self.live2d_widget.setObjectName("live2d_widget")
                
                live2d_layout = QtWidgets.QVBoxLayout(self.live2d_page)
                live2d_layout.setContentsMargins(0, 0, 0, 0)
                live2d_layout.addWidget(self.live2d_widget)
                
                self.stackedWidget_expressions.addWidget(self.live2d_page)
            elif current_sow_system_mode == "Expressions Images":
                self.expression_image_page = QtWidgets.QWidget()

                self.expression_image_label = ResponsiveEmotionLabel(parent=self.expression_image_page)
                self.expression_image_label.setObjectName("expression_image_label")

                expression_image_layout = QtWidgets.QVBoxLayout(self.expression_image_page)
                expression_image_layout.setContentsMargins(0, 0, 0, 0)
                expression_image_layout.addWidget(self.expression_image_label)
                
                self.stackedWidget_expressions.addWidget(self.expression_image_page)
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

                self.vrm_page = QtWidgets.QWidget()
                self.vrm_webview = QWebEngineView()
                self.vrm_webview.setPage(CustomWebEnginePage(self.vrm_webview))

                self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.WebGLEnabled, True)
                self.vrm_webview.settings().setAttribute(self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True)

                if not hasattr(self, 'server_thread') or not self.server_thread.is_alive():
                    self.server_thread = ServerThread(port=8001)
                    self.server_thread.start()

                html_url = f"http://localhost:8001/app/utils/emotions/vrm_module.html"
                
                if vrm_model_file:
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                    model_rel_path = os.path.relpath(vrm_model_file, project_root)
                    safe_path = model_rel_path.replace("\\", "/")
                    html_url += f"?model=/{safe_path}"
                
                def set_background_vrm(bg_type, color=None, image=None):
                    if bg_type == 0:
                        match color:
                            case 0: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x000000)")
                            case 1: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x1A202F)")
                            case 2: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x2C1A22)")
                            case 3: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x222B24)")
                            case 4: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x2E2232)")
                            case 5: self.vrm_webview.page().runJavaScript(f"setBackground('color', 0x292929)")
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
                        "admiration": "admiration.fbx", "amusement": "amusement.fbx", "anger": "anger.fbx",
                        "annoyance": "annoyance.fbx", "approval": "approval.fbx", "caring": "caring.fbx",
                        "confusion": "confusion.fbx", "curiosity": "curiosity.fbx", "desire": "desire.fbx",
                        "disappointment": "disappointment.fbx", "disapproval": "disapproval.fbx", "disgust": "disgust.fbx",
                        "embarrassment": "embarrassment.fbx", "excitement": "excitement.fbx", "fear": "fear.fbx",
                        "gratitude": "gratitude.fbx", "grief": "grief.fbx", "love": "love.fbx", "nervousness": "nervousness.fbx",
                        "neutral": "neutral.fbx", "optimism": "optimism.fbx", "pride": "pride.fbx", "realization": "realization.fbx",
                        "relief": "relief.fbx", "remorse": "remorse.fbx", "surprise": "surprise.fbx", "joy": "joy.fbx", "sadness": "sadness.fbx"
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
                        self.vrm_webview.page().runJavaScript("window.vrmLoaded", lambda is_loaded: on_vrm_loaded(is_loaded))
                    else:
                        logger.error("Error loading page")

                def on_vrm_loaded(is_loaded):
                    if is_loaded:
                        QtCore.QTimer.singleShot(500, lambda: set_background_vrm(model_background_type, model_background_color, model_background_image))
                        QtCore.QTimer.singleShot(500, lambda: set_expression_vrm(current_emotion))
                        QtCore.QTimer.singleShot(500, lambda: play_vrm_animation(current_emotion))
                    else:
                        QtCore.QTimer.singleShot(1000, lambda: self.vrm_webview.page().runJavaScript("window.vrmLoaded", lambda is_loaded: on_vrm_loaded(is_loaded)))

                self.vrm_webview.page().loadFinished.connect(on_load_finished)

                vrm_layout = QtWidgets.QVBoxLayout(self.vrm_page)
                vrm_layout.setContentsMargins(0, 0, 0, 0)
                vrm_layout.addWidget(self.vrm_webview)

                self.stackedWidget_expressions.addWidget(self.vrm_page)

            expression_layout.addWidget(self.stackedWidget_expressions)
            self.stackedWidget_expressions.setCurrentIndex(0)

            if current_sow_system_mode in ["Live2D Model", "VRM"]:
                if self.ui.centralwidget.layout() is None:
                    central_layout = QtWidgets.QHBoxLayout(self.ui.centralwidget)
                else:
                    central_layout = self.ui.centralwidget.layout()
                central_layout.addWidget(self.expression_widget)
            elif current_sow_system_mode == "Expressions Images":
                existing = self.ui.gridLayout_20.itemAtPosition(1, 2)
                if existing and existing.widget():
                    existing.widget().deleteLater()
                self.ui.gridLayout_20.addWidget(self.expression_widget, 1, 2, 1, 1)

            if current_sow_system_mode == "Expressions Images":
                self.show_emotion_image(expression_images_folder, character_name)
            elif current_sow_system_mode == "Live2D Model":
                model_json_path = self.find_model_json(live2d_model_folder)
                if model_json_path:
                    self.update_model_json(model_json_path, self.emotion_resources)
                    self.stackedWidget_expressions.setCurrentWidget(self.live2d_page)
                else:
                    logger.error("Live2D model file not found.")
            elif current_sow_system_mode == "VRM":
                self.stackedWidget_expressions.setCurrentWidget(self.vrm_page)
        
        await asyncio.sleep(0.05)
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

        ambient_status = self.configuration_settings.get_main_setting("ambient")
        if ambient_status == True:
            output_device = self.configuration_settings.get_main_setting("output_device_real_index")
            ambient_sound = self.configuration_settings.get_main_setting("ambient_sound")

            if hasattr(self, "ambient_thread") and self.ambient_thread.isRunning():
                self.ambient_thread.stop()
                self.ambient_thread.wait()
            
            self.ambient_thread = AmbientPlayer(ambient_sound, device_index=output_device)
            self.ambient_thread.start()

        try:
            self.ui.pushButton_more.clicked.disconnect()
            self.ui.pushButton_summary.clicked.disconnect()
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass
        
        chat_background = self.configuration_settings.get_main_setting("chat_background_image")
        scrollbar_style = """
            QScrollArea {
                background: transparent;
                border: none;
            }
            
            QScrollArea > QWidget, 
            QScrollArea #qt_scrollarea_viewport, 
            QScrollArea QWidget {
                background: transparent;
                background-color: transparent;
            }
            
            QScrollArea QScrollBar {
                background: transparent;
                background-color: transparent;
            }
            
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 2px;
                border: none;
            }
            
            QScrollBar::handle:vertical {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.15), 
                    stop:1 rgba(255, 255, 255, 0.08)
                );
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 4px;
                min-height: 40px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.25), 
                    stop:1 rgba(255, 255, 255, 0.16)
                );
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            
            QScrollBar::handle:vertical:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0, 
                    stop:0 rgba(255, 255, 255, 0.35), 
                    stop:1 rgba(255, 255, 255, 0.24)
                );
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
            
            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 2px 4px 2px 4px;
                border: none;
            }
            
            QScrollBar::handle:horizontal {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.15), 
                    stop:1 rgba(255, 255, 255, 0.08)
                );
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 4px;
                min-width: 40px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.25), 
                    stop:1 rgba(255, 255, 255, 0.16)
                );
                border: 1px solid rgba(255, 255, 255, 0.32);
            }
            
            QScrollBar::handle:horizontal:pressed {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1, 
                    stop:0 rgba(255, 255, 255, 0.35), 
                    stop:1 rgba(255, 255, 255, 0.24)
                );
                border: 1px solid rgba(255, 255, 255, 0.45);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: transparent;
                border: none;
                width: 0px;
                height: 0px;
            }
            
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
                border: none;
            }
        """

        if chat_background != "None":
            chat_background = chat_background.replace("\\", "/")
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    border-image: url({chat_background}) 0 0 0 0 stretch stretch;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(scrollbar_style)
        else:
            self.ui.scrollArea_chat.setStyleSheet(scrollbar_style)

        self.draw_circle_avatar(character_avatar)
        self.ui.stackedWidget.setCurrentWidget(self.ui.chat_page)

        self.ui.pushButton_more.clicked.connect(
            lambda: self.open_more_button(
                conversation_method, 
                character_name,
                character_avatar
            )
        )

        self.ui.pushButton_summary.clicked.connect(
            lambda: self.open_summary_editor(character_name, conversation_method)
        )

        if current_text_to_speech == "Nothing" and current_sow_system_mode == "Nothing":
            logger.info("Mode: Standart chat")
            self.clear_mode(character_name, conversation_method)
        elif current_text_to_speech != "Nothing" and current_sow_system_mode == "Nothing":
            logger.info("Mode: TTS Only")
            self.clear_text_to_speech_mode(character_name, conversation_method)
        elif current_text_to_speech == "Nothing" and current_sow_system_mode != "Nothing":
            logger.info("Mode: Expression Only")
            self.clear_expression_mode(character_name, conversation_method)
        elif current_text_to_speech != "Nothing" and current_sow_system_mode != "Nothing":
            logger.info("Mode: Full Mode")
            self.full_mode(character_name, conversation_method)

        await self.first_render_messages(character_name)
        
        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))
    
    def render_chat_hud(self, character_name):
        while self.ui.hud_layout.count():
            item = self.ui.hud_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.active_hud_widgets.clear()
        self.ui.hud_container_widget.hide()

        config_data = self.configuration_characters.load_configuration()
        char_info = config_data.get("character_list", {}).get(character_name)
        if not char_info:
            return

        sow_variables = char_info.get("sow_variables", [])
        if not sow_variables:
            return

        current_chat_id = char_info.get("current_chat", "default")
        chat_obj = char_info.get("chats", {}).get(current_chat_id, {})
        variables_state = chat_obj.get("variables_state", {})

        num_vars = len(sow_variables)

        for i in range(self.ui.hud_layout.columnCount()):
            self.ui.hud_layout.setColumnStretch(i, 0)

        if num_vars == 1:
            cols = 1
        elif num_vars <= 3:
            cols = num_vars
        elif num_vars == 4:
            cols = 2
        else:
            cols = 3

        for col_idx in range(cols):
            self.ui.hud_layout.setColumnStretch(col_idx, 1)

        self.ui.hud_container_widget.setFixedHeight(QtWidgets.QWIDGETSIZE_MAX)
        self.ui.hud_container_widget.setMinimumHeight(0)
        self.ui.hud_container_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Minimum
        )

        font_lbl = QtGui.QFont("Inter Tight SemiBold", 10, QtGui.QFont.Weight.Bold)
        font_lbl.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        for i, var in enumerate(sow_variables):
            var_id    = var["id"]
            var_name  = var["name"]
            var_type  = var["type"]
            var_icon  = var.get("icon", "none")
            current_value = variables_state.get(var_id, var["default"])

            stat_frame = QtWidgets.QFrame()
            stat_frame.setObjectName("StatPill")
            stat_frame.setStyleSheet("""
                QFrame#StatPill {
                    background-color: rgba(255, 255, 255, 0.015);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
                QLabel { border: none; background: transparent; }
            """)

            stat_frame.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed
            )
            stat_frame.setFixedHeight(36)

            stat_layout = QtWidgets.QHBoxLayout(stat_frame)
            stat_layout.setContentsMargins(12, 4, 12, 4)
            stat_layout.setSpacing(10)

            icon_lbl = QtWidgets.QLabel()
            icon_lbl.setFixedSize(16, 16)
            if var_icon != "none":
                pixmap = QtGui.QPixmap(f"app/gui/icons/custom_var/{var_icon}.png")
                if not pixmap.isNull():
                    icon_lbl.setPixmap(pixmap.scaled(
                        16, 16,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
            stat_layout.addWidget(icon_lbl)

            name_lbl = QtWidgets.QLabel(f"{var_name}:")
            name_lbl.setFont(font_lbl)
            name_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.4);")
            stat_layout.addWidget(name_lbl)

            if var_type == "int":
                min_v = var.get("min", 0)
                max_v = var.get("max", 100)

                COLORS = {
                    "heart":           ("#FF4B72", "#FF82A5"),
                    "coin":            ("#FFC107", "#FFE082"),
                    "star":            ("#FFC107", "#FFE082"),
                    "sword":           ("#90A4AE", "#CFD8DC"),
                    "shield":          ("#90A4AE", "#CFD8DC"),
                }
                c0, c1 = COLORS.get(var_icon, ("#4BB8FF", "#82CDFF"))

                progress_bar = QtWidgets.QProgressBar()
                progress_bar.setRange(min_v, max_v)
                progress_bar.setValue(int(current_value))
                progress_bar.setFixedSize(110, 8)
                progress_bar.setTextVisible(False)
                progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: 1px solid rgba(255,255,255,0.08);
                        border-radius: 4px;
                        background-color: rgba(0,0,0,0.35);
                    }}
                    QProgressBar::chunk {{
                        background-color: qlineargradient(
                            spread:pad, x1:0, y1:0, x2:1, y2:0,
                            stop:0 {c0}, stop:1 {c1}
                        );
                        border-radius: 3px;
                    }}
                """)
                stat_layout.addWidget(progress_bar)

                value_lbl = QtWidgets.QLabel(f"{current_value}/{max_v}")
                value_lbl.setFont(font_lbl)
                value_lbl.setStyleSheet("color: rgba(255,255,255,0.8);")
                stat_layout.addWidget(value_lbl)

                stat_layout.addStretch(1)

                self.active_hud_widgets[var_id] = {
                    "type": "int", "bar": progress_bar,
                    "label": value_lbl, "min": min_v, "max": max_v
                }

            elif var_type == "bool":
                status_text  = "YES" if current_value else "NO"
                status_color = "#81C784" if current_value else "#E57373"
                value_lbl = QtWidgets.QLabel(status_text)
                value_lbl.setFont(font_lbl)
                value_lbl.setStyleSheet(f"color: {status_color}; font-weight: bold;")
                stat_layout.addWidget(value_lbl)
                stat_layout.addStretch(1)
                self.active_hud_widgets[var_id] = {"type": "bool", "label": value_lbl}

            else:
                display_text = (
                    ", ".join(current_value) if isinstance(current_value, list)
                    else str(current_value) or "Empty"
                )
                value_lbl = QtWidgets.QLabel(display_text)
                value_lbl.setFont(font_lbl)
                value_lbl.setStyleSheet("color: rgba(255,255,255,0.8);")
                value_lbl.setMaximumWidth(200)
                value_lbl.setWordWrap(False)
                value_lbl.setTextFormat(Qt.TextFormat.PlainText)
                stat_layout.addWidget(value_lbl)
                stat_layout.addStretch(1)
                self.active_hud_widgets[var_id] = {"type": "str", "label": value_lbl}

            row_idx = i // cols
            col_idx = i % cols

            self.ui.hud_layout.addWidget(stat_frame, row_idx, col_idx)

        self.ui.hud_container_widget.show()

    def animate_hud_variable(self, var_id, new_value):
        if var_id not in self.active_hud_widgets:
            return

        widget_info = self.active_hud_widgets[var_id]
        var_type = widget_info["type"]

        if var_type == "int":
            bar = widget_info["bar"]
            lbl = widget_info["label"]
            max_v = widget_info["max"]

            if hasattr(widget_info, "_anim") and widget_info["_anim"].state() == QtCore.QAbstractAnimation.State.Running:
                widget_info["_anim"].stop()

            anim = QPropertyAnimation(bar, b"value")
            anim.setDuration(500)
            anim.setStartValue(bar.value())
            anim.setEndValue(int(new_value))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            anim.valueChanged.connect(lambda val: lbl.setText(f"{val}/{max_v}"))
            
            anim.start()
            widget_info["_anim"] = anim

        elif var_type == "bool":
            lbl = widget_info["label"]
            status_text = "YES" if new_value else "NO"
            status_color = "#81C784" if new_value else "#E57373"
            lbl.setText(status_text)
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {status_color};
                    background-color: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 6px;
                    padding: 2px 10px;
                }}
            """)

        else: # str / list
            lbl = widget_info["label"]
            display_text = ", ".join(new_value) if isinstance(new_value, list) else str(new_value)
            lbl.setText(display_text if display_text else "Empty")
    
    def modify_variable_value(self, character_name, var_id, delta_or_val, operation="add"):
        config = self.configuration_characters.load_configuration()
        char_data = config.get("character_list", {}).get(character_name)
        if not char_data:
            return None

        current_chat_id = char_data.get("current_chat", "default")
        chat_obj = char_data.get("chats", {}).get(current_chat_id, {})
        variables_state = chat_obj.setdefault("variables_state", {})

        sow_variables = char_data.get("sow_variables", [])
        var_schema = next((v for v in sow_variables if v["id"] == var_id), None)
        if not var_schema:
            logger.warning(f"Variable schema not found for '{var_id}' in '{character_name}'")
            return None

        var_type = var_schema.get("type", "int")
        current_val = variables_state.get(var_id, var_schema["default"])

        if var_type == "int":
            min_val = var_schema.get("min", 0)
            max_val = var_schema.get("max", 100)
            
            try:
                if operation == "add":
                    new_val = int(current_val) + int(delta_or_val)
                else: # set
                    new_val = int(delta_or_val)
            except (ValueError, TypeError):
                new_val = int(current_val)
                
            new_val = max(min_val, min(max_val, new_val))
            
        elif var_type == "bool":
            if isinstance(delta_or_val, str):
                new_val = delta_or_val.lower() in ("true", "1", "yes", "да", "True", "TRUE")
            else:
                new_val = bool(delta_or_val)
                
        elif var_type == "list":
            if not isinstance(current_val, list):
                current_val = []
            
            val_str = str(delta_or_val).strip()
            
            if val_str.startswith("+"):
                item_name = val_str[1:].strip()
                if item_name and item_name not in current_val:
                    current_val.append(item_name)
            elif val_str.startswith("-"):
                item_name = val_str[1:].strip()
                if item_name in current_val:
                    current_val.remove(item_name)
            else:
                if val_str and val_str not in current_val:
                    current_val.append(val_str)
                    
            new_val = current_val
            
        else: # str
            new_val = str(delta_or_val)

        variables_state[var_id] = new_val
        self.configuration_characters.save_configuration_edit(config)

        QtCore.QTimer.singleShot(0, lambda: self.animate_hud_variable(var_id, new_val))
        
        return new_val

    def draw_circle_avatar(self, avatar_path, current_sow_system_mode="Nothing"):
        target_size = 80
        label_size = 40

        source_pixmap = QPixmap(avatar_path)
        if source_pixmap.isNull():
            source_pixmap = QPixmap("app/gui/icons/logotype.png")

        scaled_pixmap = source_pixmap.scaled(
            target_size, target_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
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
        self.ui.character_avatar_label.setScaledContents(True)

        if current_sow_system_mode == "Nothing" and hasattr(self.ui, 'avatar_label'):
            self.ui.avatar_label.setPixmap(source_pixmap.scaled(
                200, 200, 
                QtCore.Qt.AspectRatioMode.KeepAspectRatio, 
                QtCore.Qt.TransformationMode.SmoothTransformation
            ))
            self.ui.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

    def open_soul_memory_viewer(self):
        if not hasattr(self, 'current_active_character') or not self.current_active_character:
            sow_toast(
                parent=self.main_window,
                title="Soul Memory",
                text=self.translations.get("soul_memory_no_chat", "Please open a chat with a character first."),
                msg_type="error"
            )
            return
            
        char_name = self.current_active_character
        
        current_mem_dir = self.get_current_memory_dir(char_name)
        
        dialog = SoulMemoryViewer(char_name, 
                                current_mem_dir, 
                                self.main_window, 
                                subtitle_tr=self.translations.get("soul_memory_subtitle"),
                                content_view_tr=self.translations.get("soul_memory_content_placeholder"),
                                title_text_tr=self.translations.get("soul_memory_title"),
                                tab_database_tr=self.translations.get("soul_memory_tab_db"),
                                tab_user_profile_tr=self.translations.get("soul_memory_tab_user"),
                                tab_diary_tr=self.translations.get("soul_memory_tab_diary"),
                                tab_logs_tr=self.translations.get("soul_memory_tab_logs"),
                                btn_save_tr=self.translations.get("soul_memory_btn_save"),
                                btn_delete_tr=self.translations.get("soul_memory_btn_delete"),
                                btn_refresh_tr=self.translations.get("soul_memory_btn_refresh"),
                                btn_open_folder_tr=self.translations.get("soul_memory_btn_open"),
                                msg_save_success_tr=self.translations.get("soul_memory_save_success"),
                                msg_save_error_tr=self.translations.get("soul_memory_save_error"),
                                msg_delete_confirm_title_tr=self.translations.get("soul_memory_del_title"),
                                msg_delete_confirm_text_tr=self.translations.get("soul_memory_del_text"),
                                msg_delete_success_tr=self.translations.get("soul_memory_del_success"),
                                msg_delete_error_tr=self.translations.get("soul_memory_del_error"),
                                msg_logs_empty_tr=self.translations.get("soul_memory_logs_empty"),
                                btn_edit_tr=self.translations.get("soul_memory_btn_edit"),
                                btn_preview_tr=self.translations.get("soul_memory_btn_preview")
                            )
        dialog.exec()

    def open_more_button(self, conversation_method, character_name, character_avatar):
        _BG       = "#070709"
        _SURF1    = "#0B0B0F"
        _SURF2    = "#121218"
        _SURF3    = "#161622"
        _CARD_BG  = "#0E0E14"
        _TEXT     = "#DEDAD2"
        _TEXT_S   = "#6F6B63"
        _BORDER   = "rgba(255, 255, 255, 0.045)"
        _BORDER_M = "rgba(255, 255, 255, 0.08)"
        
        _BLUE     = "#4BB8FF"  
        _BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        _BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        _BLUE_BRT = "#82CDFF"

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(940, 680) 
        dialog.resize(1100, 700)
        
        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        f_title = mf(14, QFont.Weight.Bold)
        f_label = mf(8,  QFont.Weight.Bold)
        f_input = mf(10, QFont.Weight.Medium)
        f_btn   = mf(10, QFont.Weight.DemiBold)

        dialog.setFont(f_input)
        dialog.setStyleSheet(
            f"QDialog {{ background-color: {_BG}; }}"
            f"QLabel {{ border: none; background: transparent; color: {_TEXT}; }}"
        )

        character_data = self.configuration_characters.load_configuration()
        if "character_list" not in character_data or character_name not in character_data["character_list"]:
            logger.error(f"Character '{character_name}' not found in the configuration.")
            return

        character_information = character_data["character_list"][character_name]
        character_description = character_information.get("character_description", "")
        character_personality = character_information.get("character_personality", "")
        first_message = character_information.get("first_message", "")
        scenario = character_information.get("scenario", "")
        example_messages = character_information.get("example_messages", "")
        alternate_greetings = character_information.get("alternate_greetings", "")
        creator_notes = character_information.get("creator_notes", "")

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("IGSidebar")
        sidebar.setFixedWidth(270)
        sidebar.setStyleSheet(
            f"QFrame#IGSidebar {{"
            f"  background-color: {_SURF1};"
            f"  border: none;"
            f"  border-right: 1px solid {_BORDER};"
            f"}}"
            f"QFrame#IGSidebar QLabel {{ border: none; background: transparent; }}"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 24)
        sidebar_layout.setSpacing(16)

        avatar_size = 110
        avatar_label = QLabel()
        
        source_pixmap = QPixmap(character_avatar)
        if source_pixmap.isNull():
            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
        else:
            scaled_pixmap = source_pixmap.scaled(
                avatar_size, avatar_size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            x = (scaled_pixmap.width() - avatar_size) // 2
            y = (scaled_pixmap.height() - avatar_size) // 2
            square_pixmap = scaled_pixmap.copy(x, y, avatar_size, avatar_size)

            final_pixmap = QPixmap(avatar_size, avatar_size)
            final_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            brush = QtGui.QBrush(square_pixmap)
            painter.setBrush(brush)
            painter.setPen(Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, avatar_size, avatar_size)
            painter.end()

        avatar_label.setPixmap(final_pixmap)
        avatar_label.setFixedSize(avatar_size, avatar_size)
        avatar_label.setStyleSheet("border: none; background: transparent;")
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 5)
        avatar_label.setGraphicsEffect(shadow)
        
        avatar_container = QHBoxLayout()
        avatar_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addLayout(avatar_container)

        name_lbl = QLabel(self.translations.get("character_settings_name_label", "CHARACTER NAME"))
        name_lbl.setFont(f_label)
        name_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px;")
        sidebar_layout.addWidget(name_lbl)

        name_edit = QLineEdit(character_name, dialog)
        name_edit.setObjectName("IGNameInput")
        name_edit.setFont(f_title)
        name_edit.setStyleSheet(
            f"QLineEdit#IGNameInput {{"
            f"  background-color: {_SURF2};"
            f"  color: {_TEXT};"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 8px 12px;"
            f"  selection-background-color: {_BLUE_MUT};"
            f"}}"
            f"QLineEdit#IGNameInput:focus {{"
            f"  border-color: {_BORDER_M};"
            f"  background-color: {_SURF3};"
            f"}}"
        )
        name_edit.setFixedHeight(38)
        sidebar_layout.addWidget(name_edit)

        nav_lbl = QLabel(self.translations.get("character_settings_nav_label", "CONFIGURATION"))
        nav_lbl.setFont(f_label)
        nav_lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 10px;")
        sidebar_layout.addWidget(nav_lbl)

        nav_list = QtWidgets.QListWidget()
        nav_list.setObjectName("IGNavList")
        nav_list.setFont(f_btn)
        nav_list.setStyleSheet(
            f"QListWidget#IGNavList {{"
            f"  background: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#IGNavList::item {{"
            f"  color: {_TEXT_S};"
            f"  background-color: transparent;"
            f"  border: 1px solid transparent;"
            f"  border-radius: 6px;"
            f"  padding: 10px 14px;"
            f"  margin-bottom: 4px;"
            f"}}"
            f"QListWidget#IGNavList::item:hover {{"
            f"  background-color: {_SURF2};"
            f"  color: {_TEXT};"
            f"}}"
            f"QListWidget#IGNavList::item:selected {{"
            f"  background-color: {_BLUE_MUT};"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )
        sidebar_layout.addWidget(nav_list)

        sidebar_layout.addStretch()

        new_dialog_button = QPushButton(self.translations.get("character_settings_new_chat_btn", "START NEW CHAT"), dialog)
        new_dialog_button.setFont(f_btn)
        new_dialog_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        new_dialog_button.setFixedHeight(36)
        new_dialog_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {_BLUE};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_BLUE_MUT};"
            f"  border-color: {_BLUE_BRT};"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )
        new_dialog_button.clicked.connect(
            lambda: asyncio.create_task(
                self.start_new_dialog(
                    dialog, conversation_method, character_name,
                    name_edit, description_edit, personality_edit,
                    scenario_edit, first_message_edit, example_messages_edit,
                    alternate_greetings_edit, creator_notes_edit
                )
            )
        )

        save_button = QPushButton(self.translations.get("character_settings_save_btn", "SAVE CHANGES"), dialog)
        save_button.setFont(f_btn)
        save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        save_button.setFixedHeight(36)
        save_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: {_BLUE_MUT};"
            f"  border: 1px solid {_BLUE_GLO};"
            f"  border-radius: 6px;"
            f"  color: {_BLUE};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: rgba(75, 184, 255, 0.25);"
            f"  border-color: rgba(75, 184, 255, 0.55);"
            f"  color: {_BLUE_BRT};"
            f"}}"
        )
        save_button.clicked.connect(lambda: self.save_changes(
            dialog, conversation_method, character_name, name_edit, 
            description_edit, personality_edit, scenario_edit, 
            first_message_edit, example_messages_edit, 
            alternate_greetings_edit, creator_notes_edit
        ))

        ok_button = QPushButton(self.translations.get("character_settings_close_btn", "CLOSE"), dialog)
        ok_button.setFont(f_btn)
        ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_button.setFixedHeight(36)
        ok_button.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent;"
            f"  border: 1px solid {_BORDER};"
            f"  border-radius: 6px;"
            f"  color: {_TEXT_S};"
            f"  letter-spacing: 0.5px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {_SURF2};"
            f"  border-color: {_BORDER_M};"
            f"  color: {_TEXT};"
            f"}}"
        )
        ok_button.clicked.connect(dialog.close)

        sidebar_layout.addWidget(new_dialog_button)
        sidebar_layout.addWidget(save_button)
        sidebar_layout.addWidget(ok_button)

        main_layout.addWidget(sidebar)

        workspace = QFrame()
        workspace_layout = QVBoxLayout(workspace)
        workspace_layout.setContentsMargins(28, 24, 28, 24)
        workspace_layout.setSpacing(12)

        workspace_stack = QStackedWidget()
        workspace_stack.setObjectName("IGWorkspaceStack")
        workspace_stack.setStyleSheet("QStackedWidget#IGWorkspaceStack { background: transparent; border: none; }")
        workspace_layout.addWidget(workspace_stack)

        def add_editable_field(layout, label_text, content, placeholder=""):
            lbl = QLabel(label_text)
            lbl.setFont(f_label)
            lbl.setStyleSheet(f"color: {_TEXT_S}; letter-spacing: 0.8px; margin-top: 8px; margin-bottom: 4px; border: none;")
            layout.addWidget(lbl)

            text_edit = QTextEdit()
            text_edit.setFont(f_input)
            text_edit.setPlainText(str(content) if content else "")
            if placeholder:
                text_edit.setPlaceholderText(placeholder)
            
            text_edit.setStyleSheet(
                f"QTextEdit {{"
                f"  background-color: {_SURF2};"
                f"  color: {_TEXT};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 8px;"
                f"  padding: 12px 14px;"
                f"  selection-background-color: {_BLUE_MUT};"
                f"  line-height: 1.4;"
                f"}}"
                f"QTextEdit:focus {{"
                f"  border-color: {_BORDER_M};"
                f"  background-color: {_SURF3};"
                f"}}"
            )
            text_edit.setMinimumHeight(180)
            layout.addWidget(text_edit)
            return text_edit

        def create_page_card():
            card = QFrame()
            card.setObjectName("IGPageCard")
            card.setStyleSheet(
                f"QFrame#IGPageCard {{"
                f"  background-color: {_CARD_BG};"
                f"  border: 1px solid {_BORDER};"
                f"  border-radius: 12px;"
                f"}}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)

            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(
                "QScrollArea { border: none; background: transparent; }"
                "QScrollBar:vertical { background: transparent; width: 8px; }"
                f"QScrollBar::handle:vertical {{ background: {_BORDER_M}; border-radius: 4px; }}"
                f"QScrollBar::handle:vertical:hover {{ background: {_TEXT_S}; }}"
                "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }"
            )
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(8, 4, 8, 12)
            content_layout.setSpacing(12)
            
            scroll.setWidget(content_widget)
            card_layout.addWidget(scroll)
            return card, content_layout

        tab_identity_text = self.translations.get("btn_identity_text", "Identity")
        tab_scenario_text = self.translations.get("btn_scenario_text", "Scenario")
        tab_examples_text = self.translations.get("btn_examples_text", "Examples")
        tab_creator_notes_text = self.translations.get("btn_creator_notes_text", "Creator Notes")

        page_id_card, layout_id = create_page_card()
        description_edit = add_editable_field(layout_id, self.translations.get("character_edit_description", "Description"), character_description, self.translations.get("character_edit_description_placeholder_1", "Enter description"))
        personality_edit = add_editable_field(layout_id, self.translations.get("character_edit_personality", "Personality"), character_personality, self.translations.get("character_edit_personality_placeholder", "Enter personality traits"))
        workspace_stack.addWidget(page_id_card)
        nav_list.addItem(tab_identity_text)

        page_sc_card, layout_sc = create_page_card()
        first_message_edit = add_editable_field(layout_sc, self.translations.get("character_edit_first_message", "First Message"), first_message, self.translations.get("character_edit_first_message_placeholder", "Enter first message"))
        scenario_edit = add_editable_field(layout_sc, self.translations.get("scenario", "Scenario"), scenario, self.translations.get("placeholder_scenario", "Conversation scenario:"))
        workspace_stack.addWidget(page_sc_card)
        nav_list.addItem(tab_scenario_text)

        page_ex_card, layout_ex = create_page_card()
        example_messages_edit = add_editable_field(layout_ex, self.translations.get("example_messages_title", "Example Messages"), example_messages, self.translations.get("placeholder_example_messages", "Use <START> macro"))
        alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
        alternate_greetings_edit = add_editable_field(layout_ex, self.translations.get("alternate_greetings_label", "Alternate Greetings"), alt_greets_text, self.translations.get("placeholder_alternate_greetings", "Use <GREETING> macro"))
        workspace_stack.addWidget(page_ex_card)
        nav_list.addItem(tab_examples_text)

        page_notes_card, layout_notes = create_page_card()
        creator_notes_edit = add_editable_field(layout_notes, self.translations.get("creator_notes_label", "Creator Notes"), creator_notes, self.translations.get("placeholder_creator_notes", "Any additional notes"))
        workspace_stack.addWidget(page_notes_card)
        nav_list.addItem(tab_creator_notes_text)

        nav_list.currentRowChanged.connect(workspace_stack.setCurrentIndex)
        nav_list.setCurrentRow(0)

        main_layout.addWidget(workspace, 1)
        dialog.exec()

    def clear_mode(self, character_name, conversation_method):
        """
        Mode without text-to-speech or emotions.
        """
        def handle_user_message_sync():
            asyncio.create_task(
                self.handle_user_message(
                    character_name,
                    conversation_method
                )
            )

        try:
            self.textEdit_write_user_message.handle_enter_key.disconnect()
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass

        self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)
        self.textEdit_write_user_message.handle_enter_key.connect(handle_user_message_sync)

    def clear_text_to_speech_mode(self, character_name, conversation_method):
        """
        Mode with text-to-speech but without calls and emotions.
        """
        def handle_user_message_sync():
            asyncio.create_task(
                self.handle_user_message(
                    character_name,
                    conversation_method
                )
            )

        try:
            self.textEdit_write_user_message.handle_enter_key.disconnect()
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass

        self.textEdit_write_user_message.handle_enter_key.connect(handle_user_message_sync)
        self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)

    def clear_expression_mode(self, character_name, conversation_method):
        """
        Mode without text-to-speech or calls but with emotions.
        """
        def handle_user_message_sync():
            asyncio.create_task(
                self.handle_user_message(
                    character_name,
                    conversation_method
                )
            )

        try:
            self.textEdit_write_user_message.handle_enter_key.disconnect()
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass

        self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)
        self.textEdit_write_user_message.handle_enter_key.connect(handle_user_message_sync)

    def full_mode(self, character_name, conversation_method):
        """
        Full mode with text-to-speech, calls, and emotions.
        """
        def handle_user_message_sync():
            asyncio.create_task(
                self.handle_user_message(
                    character_name,
                    conversation_method
                )
            )

        try:
            self.textEdit_write_user_message.handle_enter_key.disconnect()
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass

        self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)
        self.textEdit_write_user_message.handle_enter_key.connect(handle_user_message_sync)

    def apply_macros(self, text, character_name, user_name):
        if not text: return text
        return (text.replace("{{user}}", user_name)
                    .replace("{{char}}", character_name)
                    .replace("{{User}}", user_name)
                    .replace("{{Char}}", character_name)
                    .replace("{{пользователь}}", user_name)
                    .replace("{{Пользователь}}", user_name)
                    .replace("{{персонаж}}", character_name)
                    .replace("{{Персонаж}}", character_name))

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

    def stop_generation(self):
        self.abort_generation = True
        self.ui.pushButton_stop_generation.hide()
        self.ui.pushButton_send_message.show()
        logger.info("The user requested to stop the generation.")

    async def handle_user_message(self, character_name, conversation_method, external_text=None, discord_context=None):
        """
        Handles a user's message: sends it and retrieves a response from the character.
        """
        self.abort_generation = False

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        auto_summary_status = self.configuration_settings.get_main_setting("auto_summary")
        interval = self.configuration_settings.get_main_setting("interval_summary")

        conversation_method = character_info.get("conversation_method", "Local LLM")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")

        try:
            personas_data = self.configuration_settings.get_user_data("personas") or {}
            current_persona = character_info.get("selected_persona")
            if current_persona == "None" or current_persona is None or current_persona not in personas_data:
                user_name = "User"
                user_description = "Interacts with the character using the Soul of Waifu program, which allows the user to interact with large language models."
            else:
                user_name = personas_data[current_persona].get("user_name", "User")
                user_description = personas_data[current_persona].get("user_description", "")

            if external_text:
                user_text_original = external_text
            else:
                user_text_original = self.textEdit_write_user_message.toPlainText().strip()

            user_text = user_text_original
            user_text_markdown = self.markdown_to_html(user_text_original)

            user_message_container = await self.add_message(character_name, "", is_user=True, message_id=None)
            user_message_label = user_message_container["label"]
            user_message_label.setText(user_text_markdown or " ")

            await asyncio.sleep(0.05)
            if not external_text:
                self.textEdit_write_user_message.clear()
            
            if sow_system_status and current_sow_system_mode != "Nothing":
                indicator_margins = (10, 5, 10, 5)
            else:
                indicator_margins = (15, 5, 15, 5)

            s_app = self.get_chat_appearance()
            typing_widget = TypingIndicatorWidget(character_name, character_avatar, s_app, indicator_margins)
            self.chat_container.addWidget(typing_widget)

            await asyncio.sleep(0.05)
            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

            self.ui.pushButton_send_message.hide()
            self.ui.pushButton_stop_generation.show()

            full_text = ""
            first_chunk_received = False
            character_answer_container = None
            character_answer_label = None
            self.current_typewriter = None 

            current_chat = character_info.get("current_chat", "default")
            chats = character_info.get("chats", {})
            chat_history = chats.get(current_chat, {}).get("chat_history", [])
            
            context_messages = []
            for message in chat_history:
                u_msg = message.get("user", "")
                c_msg = message.get("character", "")
                if u_msg:
                    context_messages.append({"role": "user", "content": f"{u_msg.strip()}"})
                if c_msg:
                    context_messages.append({"role": "assistant", "content": f"{c_msg.strip()}"})

            messages, activated_lorebook_entries = self.prompt_engine.build_system_prompt_blocks(
                character_name, user_name, user_description, context_messages, user_text
            )

            provider = AIFactory.get_provider(conversation_method, character_info.get("model_override"))
            if not provider:
                raise ValueError(f"Unknown conversation method: {conversation_method}")

            self.log_prompt_structure(messages)
            generator = provider.generate_stream(messages)

            try:
                sentence_buffer_chat = ""
                _tts_active = current_text_to_speech not in ("Nothing", None) and not discord_context

                async for chunk in generator:
                    if self.abort_generation: 
                        break
                    if chunk:
                        delta = chunk
                        if full_text and chunk.startswith(full_text):
                            delta = chunk[len(full_text):]
                        
                        if not delta:
                            continue

                        if not first_chunk_received:
                            if typing_widget: 
                                try:
                                    typing_widget.deleteLater()
                                    self.chat_container.removeWidget(typing_widget)
                                except: 
                                    pass
                            
                            character_answer_container = await self.add_message(character_name, "", is_user=False, message_id=None)
                            character_answer_label = character_answer_container["label"]
                            self.current_typewriter = TypewriterEffect(
                                character_answer_label, 
                                character_answer_container["frame"],
                                self.ui.scrollArea_chat, 
                                self, 
                                character_name, 
                                user_name
                            )

                            first_chunk_received = True
                            if getattr(self, "web_bridge", None): 
                                asyncio.create_task(self.web_bridge.broadcast_message_start())

                        full_text += delta
                        self.current_typewriter.write(delta)
                        
                        if getattr(self, "web_bridge", None): 
                            asyncio.create_task(self.web_bridge.broadcast_chunk(delta))

                        if _tts_active:
                            sentence_buffer_chat += delta
                            while True:
                                match = re.search(r'([.!?\n]+)', sentence_buffer_chat)
                                if not match:
                                    break
                                
                                split_idx = match.end()
                                sentence = sentence_buffer_chat[:split_idx].strip()
                                clean_sentence = re.sub(r'[*_~`]', '', sentence)
                                
                                if len(clean_sentence) > 3:
                                    if hasattr(self, 'chat_tts_worker') and self.chat_tts_worker:
                                        self.chat_tts_worker.add_text(clean_sentence)
                                        
                                sentence_buffer_chat = sentence_buffer_chat[split_idx:]

                        await asyncio.sleep(0.016)

                if _tts_active and sentence_buffer_chat.strip():
                    clean_tail = re.sub(r'[*_~`]', '', sentence_buffer_chat.strip())
                    if len(clean_tail) > 3 and hasattr(self, 'chat_tts_worker') and self.chat_tts_worker:
                        self.chat_tts_worker.add_text(clean_tail)

                if full_text and first_chunk_received:
                    new_msgs_for_mem = context_messages + [
                        {"role": "user", "content": user_text},
                        {"role": "assistant", "content": full_text}
                    ]
                    asyncio.create_task(
                        self.prompt_engine.update_memory_after_response(
                            provider, new_msgs_for_mem, character_name, user_name, activated_lorebook_entries
                        )
                    )

            except Exception as e:
                if not first_chunk_received and 'typing_widget' in locals() and typing_widget:
                    try: typing_widget.deleteLater()
                    except: pass
                logger.error(f"Generation Engine Error: {e}")

            if self.current_typewriter:
                await self.current_typewriter.wait_until_finished()

            clean_full_text = full_text
            if full_text.startswith(f"{character_name}:"):
                clean_full_text = full_text[len(f"{character_name}:"):].lstrip()

            state_pattern = r"<(state[_\-\s]*update|update[_\-\s]*state)>(.*?)</\1>"
            state_match = re.search(state_pattern, clean_full_text, re.DOTALL | re.IGNORECASE)

            if state_match:
                json_data_str = state_match.group(2).strip()
                try:
                    sanitized_json = re.sub(r':\s*\+(\d+)', r': \1', json_data_str)
                    
                    updates = json.loads(sanitized_json)
                    for var_id, delta_or_val in updates.items():
                        self.modify_variable_value(character_name, var_id, delta_or_val, operation="add")
                except Exception as e:
                    logger.error(f"Failed to parse state update JSON from AI response: {e}")

                clean_full_text = re.sub(state_pattern, "", clean_full_text, flags=re.DOTALL | re.IGNORECASE).strip()

            if first_chunk_received:
                user_message_message_id = user_message_container["message_id"]
                character_answer_message_id = character_answer_container["message_id"]
                
                self.configuration_characters.add_message_to_config(
                    character_name, "User", True, user_text or " ", user_message_message_id
                )
                self.configuration_characters.add_message_to_config(
                    character_name, character_name, False, clean_full_text, character_answer_message_id
                )

            self.ui.pushButton_stop_generation.hide()
            self.ui.pushButton_send_message.show()

            if sow_system_status:
                if current_sow_system_mode in ["Expressions Images", "Live2D Model", "VRM"]:
                    if self.emotion_task and not self.emotion_task.done():
                        self.emotion_task.cancel()
                        logger.debug("Old emotion detection task has been cancelled.")

                    def start_emotion():
                        self.emotion_task = asyncio.create_task(
                            self.detect_emotion(character_name, full_text)
                        )

                    asyncio.get_event_loop().call_soon(start_emotion)

            if first_chunk_received:
                final_html = self.markdown_to_html(clean_full_text)
                final_html = self.apply_macros(final_html, character_name, user_name)
                character_answer_label.setText(final_html)
                character_answer_label.setProperty("original_text", final_html)
                character_answer_label.setProperty("is_translated", False)
            
            if getattr(self, 'abort_generation', False):
                current_text_to_speech = "Nothing"
                logger.info("Text-to-Speech was canceled because the generation was interrupted by the user.")

            await self.render_messages(character_name)
            
            if auto_summary_status and interval and int(interval) > 0:
                asyncio.create_task(
                    self.perform_auto_summary(character_name, user_name, interval, conversation_method)
                )
            
            if discord_context:
                from app.utils.discord_manager import split_message
                chunks = split_message(clean_full_text)
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await discord_context.reply(chunk)
                    else:
                        await discord_context.channel.send(chunk)
                        
            if getattr(self, "web_bridge", None):
                asyncio.create_task(self.web_bridge.broadcast_message_end())
                    
        except Exception:
            import traceback
            error_message = traceback.format_exc()
            logger.error(f"Error processing the message: {error_message}")
            if 'typing_widget' in locals() and typing_widget is not None:
                try:
                    typing_widget.deleteLater()
                except RuntimeError:
                    pass
            
            self.ui.pushButton_stop_generation.hide()
            self.ui.pushButton_send_message.show()

    async def regenerate_message(self, conversation_method, character_name, message_id):
        """
        Regenerate message from character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        conversation_method = character_info.get("conversation_method", "Local LLM")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        
        current_chat = character_info.get("current_chat", "default")
        chats = character_info.get("chats", {})
        chat_content = chats.get(current_chat, {}).get("chat_content", {})

        personas_data = self.configuration_settings.get_user_data("personas") or {}
        current_persona = character_info.get("selected_persona")
        user_name = "User"
        user_description = "Interacts with the character using the Soul of Waifu program."
        if current_persona and current_persona != "None" and current_persona in personas_data:
            try:
                user_name = personas_data[current_persona].get("user_name", "User")
                user_description = personas_data[current_persona].get("user_description", "")
            except Exception:
                pass

        if message_id not in chat_content:
            logger.error(f"Message {message_id} not found in chat_content.")
            return

        all_message_ids = list(chat_content.keys())
        selected_index = all_message_ids.index(message_id)
        ids_to_delete = all_message_ids[selected_index + 1:]
        
        for msg_id in ids_to_delete:
            if msg_id in self.messages:
                self.messages[msg_id]["frame"].deleteLater()
                del self.messages[msg_id]
            if msg_id in self.message_order:
                self.message_order.remove(msg_id)

        self.configuration_characters.delete_chat_messages(character_name, ids_to_delete)

        await asyncio.sleep(0.05)

        last_user_message = None
        idx = selected_index - 1
        while idx >= 0:
            prev_msg = chat_content.get(all_message_ids[idx])
            if prev_msg and prev_msg.get("is_user"):
                last_user_message = prev_msg
                break
            idx -= 1

        user_text_original = ""
        if last_user_message:
            current_variant_id = last_user_message.get("current_variant_id", "default")
            variant = next((v for v in last_user_message.get("variants", []) if v["variant_id"] == current_variant_id), None)
            if variant:
                user_text_original = variant.get("text", "")

        user_text = user_text_original

        if message_id in self.messages:
            character_answer_container = self.messages[message_id]
            character_answer_label = character_answer_container["label"]
            character_answer_frame = character_answer_container["frame"]
            
            character_answer_frame.hide()
        else:
            return

        if sow_system_status and current_sow_system_mode != "Nothing":
            indicator_margins = (10, 5, 10, 5)
        else:
            indicator_margins = (15, 5, 15, 5)

        s_app = self.get_chat_appearance()
        char_avatar_path = character_info.get("character_avatar")

        typing_widget = TypingIndicatorWidget(character_name, char_avatar_path, s_app, indicator_margins)
        self.chat_container.addWidget(typing_widget)

        await asyncio.sleep(0.05)
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

        full_text = ""
        first_chunk_received = False
        self.current_typewriter = None

        if user_text:
            chat_history_raw = chats.get(current_chat, {}).get("chat_history", [])
            context_messages = []

            for message in chat_history_raw[:-1]:
                u_msg = message.get("user", "")
                c_msg = message.get("character", "")
                if u_msg: context_messages.append({"role": "user", "content": f"{u_msg.strip()}"})
                if c_msg: context_messages.append({"role": "assistant", "content": f"{c_msg.strip()}"})

            messages, activated_lorebook_entries = self.prompt_engine.build_system_prompt_blocks(
                character_name, user_name, user_description, context_messages, user_text
            )

            provider = AIFactory.get_provider(conversation_method, character_info.get("model_override"))
            if provider:
                self.log_prompt_structure(messages)
                generator = provider.generate_stream(messages)

                async for chunk in generator:
                    if chunk:
                        if not first_chunk_received:
                            if typing_widget:
                                try:
                                    typing_widget.deleteLater()
                                    self.chat_container.removeWidget(typing_widget)
                                except: pass
                            
                            character_answer_frame.show()
                            character_answer_label.setText("")
                            self.current_typewriter = TypewriterEffect(
                                character_answer_label, 
                                character_answer_container["frame"],
                                self.ui.scrollArea_chat, 
                                self, 
                                character_name, 
                                user_name
                            )
                            first_chunk_received = True

                        full_text += chunk
                        self.current_typewriter.write(chunk)
                        await asyncio.sleep(0.01)

            if self.current_typewriter:
                await self.current_typewriter.wait_until_finished()

            if full_text.startswith(f"{character_name}:"):
                full_text = full_text[len(f"{character_name}:"):].lstrip()

            if sow_system_status:
                if current_sow_system_mode in ["Expressions Images", "Live2D Model", "VRM"]:
                    if self.emotion_task and not self.emotion_task.done():
                        self.emotion_task.cancel()
                        logger.debug("Old emotion detection has been cancelled.")

                    def start_emotion():
                        self.emotion_task = asyncio.create_task(
                            self.detect_emotion(character_name, full_text)
                        )

                    asyncio.get_event_loop().call_soon(start_emotion)

            final_html = self.markdown_to_html(full_text)
            final_html = self.apply_macros(final_html, character_name, user_name)
            character_answer_label.setText(final_html)
            character_answer_label.setProperty("original_text", final_html)
            character_answer_label.setProperty("is_translated", False)

            self.configuration_characters.regenerate_message_in_config(character_name, message_id, full_text)

        await self.render_messages(character_name)

        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))

    async def perform_auto_summary(self, character_name, user_name, interval, conversation_method):
        """
        Perform background summarization of the recent chat messages.
        """
        try:
            char_config = self.configuration_characters.load_configuration()
            char_data = char_config["character_list"].get(character_name)
            if not char_data: return

            current_chat_id = char_data.get("current_chat", "default")
            chat_data = char_data["chats"].get(current_chat_id, {})

            last_seq = chat_data.get("last_summarized_sequence", 0)
            
            raw_messages = chat_data.get("chat_content", {}).values()
            sorted_messages = sorted(raw_messages, key=lambda x: x.get("sequence_number", 0))

            if not sorted_messages: return
            highest_seq_total = sorted_messages[-1].get("sequence_number", 0)

            if (highest_seq_total - last_seq) < int(interval):
                return

            logger.info(f"Auto-summary triggered for {character_name}. New messages: {highest_seq_total - last_seq}")

            new_messages_chunk = []
            highest_seq_in_chunk = last_seq

            for msg in sorted_messages:
                seq = msg.get("sequence_number", 0)
                if seq > last_seq:
                    current_var_id = msg.get("current_variant_id", "default")
                    text_content = ""
                    for variant in msg.get("variants", []):
                        if isinstance(variant, dict) and variant.get("variant_id") == current_var_id:
                            text_content = variant.get("text", "")
                            break
                    
                    if not text_content.strip(): continue

                    role = "user" if msg.get("is_user") else "assistant"
                    new_messages_chunk.append({"role": role, "content": text_content})
                    highest_seq_in_chunk = seq
                    
                    if len(new_messages_chunk) >= int(interval):
                        break
            
            if not new_messages_chunk: return

            current_summary = chat_data.get("summary_text", "")
            full_new_summary = ""

            provider = AIFactory.get_provider(conversation_method, char_data.get("model_override"))
            if not provider:
                logger.error(f"Cannot perform auto-summary: Provider '{conversation_method}' not found.")
                return

            summary_messages = self.prompt_engine.build_summary_prompt_blocks(
                current_summary, new_messages_chunk, character_name, user_name
            )

            async for chunk in provider.generate_summary(summary_messages):
                full_new_summary += chunk

            if full_new_summary and len(full_new_summary) > 50:
                chat_data["summary_text"] = full_new_summary.strip()
                chat_data["last_summarized_sequence"] = highest_seq_in_chunk
                
                self.configuration_characters.save_configuration_edit(char_config)
                logger.info(f"Auto-summary completed. Updated sequence to {highest_seq_in_chunk}")

        except Exception as e:
            logger.error(f"Auto-summary background task failed: {e}")

    async def add_message(self, character_name, text, is_user, message_id, insert_at=None):
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
            try:
                user_name = personas_data[current_persona].get("user_name", "User")
            except Exception as e:
                logger.error(e)
                user_name = "User"

        html_text = re.sub(r'\s*!\[.*?\]\(.*?\)\s*', ' ', text)
        html_text = self.markdown_to_html(html_text)
        html_text = self.apply_macros(html_text, character_name, user_name)

        message_container = QHBoxLayout()
        message_container.setSpacing(0)
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        current_sow_system_mode = char_info.get("current_sow_system_mode", "Nothing")
        if sow_system_status and current_sow_system_mode != "Nothing":
            message_container.setContentsMargins(10, 5, 10, 5)
        else:
            message_container.setContentsMargins(10, 5, 10, 5)

        s = self.get_chat_appearance()
        op = s["bubble_opacity"]
        
        def get_rgba(hex_col, alpha):
            h = hex_col.lstrip("#")
            return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha/100})"
            
        bg_color = get_rgba(s["user_bubble_color"] if is_user else s["char_bubble_color"], op)
        r = s["border_radius"]
        
        radius_css = (
            f"border-top-left-radius: {r}px; border-bottom-left-radius: {r}px; border-bottom-right-radius: 0px; border-top-right-radius: {r}px;" 
            if is_user else 
            f"border-top-right-radius: {r}px; border-bottom-right-radius: {r}px; border-top-left-radius: {r}px; border-bottom-left-radius: 0px;"
        )

        bubble_frame = QFrame()
        bubble_frame.setObjectName("bubble_frame")
        bubble_frame.setStyleSheet(f"""
            QFrame#bubble_frame {{
                background-color: {bg_color};
                {radius_css}
                margin: 5px;
            }}
        """)
        bubble_frame.setFixedWidth(s.get("max_width", 750))

        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(14, 12, 14, 12)
        bubble_layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        if is_user:
            raw_pixmap = QPixmap(self.user_avatar)
        else:
            raw_pixmap = QPixmap(character_avatar)

        if raw_pixmap.isNull():
            raw_pixmap = QPixmap("app/gui/icons/logotype.png")

        target_size = 64
        label_size  = 26

        scaled_pixmap = raw_pixmap.scaled(
            target_size, target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        crop_x = (scaled_pixmap.width()  - target_size) // 2
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

        name_label = QLabel(user_name if is_user else character_name)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {max(11, s["font_size"] - 2)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)

        current_chat = char_info["current_chat"]
        chat_content = char_info.get("chats", {}).get(current_chat, {}).get("chat_content", {})

        last_char_index = self.get_last_character_message_index(chat_content)
        has_variants = False
        variants =[]
        if last_char_index is not None:
            msg_data = chat_content.get(last_char_index, {})
            variants = msg_data.get("variants",[])
            has_variants = len(variants) > 1

        is_last_char_message = (message_id == last_char_index)

        left_button  = QPushButton()
        right_button = QPushButton()
        for btn in (left_button, right_button):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedSize(QtCore.QSize(22, 22))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setVisible(has_variants and is_last_char_message)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: rgba(255,255,255,0.1);
                }
            """)

        left_button.setIcon(QtGui.QIcon("app/gui/icons/left_arrow.png"))
        right_button.setIcon(QtGui.QIcon("app/gui/icons/right_arrow.png"))

        if has_variants and last_char_index is not None:
            left_button.clicked.connect(lambda _, d=-1: self.change_variant(character_name, d))
            right_button.clicked.connect(lambda _, d=+1: self.change_variant(character_name, d))

        variant_counter_label = QLabel()
        variant_counter_label.setFixedSize(40, 20)
        variant_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        variant_counter_label.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.6); background-color: rgba(0,0,0,0.3);
                font-size: 10px; font-weight: bold; border-radius: 6px;
            }
        """)
        variant_counter_label.setVisible(has_variants and is_last_char_message)

        current_idx = self.get_current_variant_index(character_name)
        if current_idx != -1:
            variant_counter_label.setText(f"{current_idx + 1}/{len(variants)}")

        menu_button = QPushButton("•••")
        menu_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        menu_button.setFixedSize(26, 26)
        menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: rgba(255, 255, 255, 0.4);
                border-radius: 13px; font-weight: bold; font-size: 14px; padding-bottom: 3px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); color: white; }
        """)
        menu_button.clicked.connect(
            lambda _: self.show_message_menu(character_name, conversation_method, menu_button, is_user, message_id)
        )

        header_layout.addWidget(avatar_label)
        header_layout.addWidget(name_label)
        header_layout.addStretch()
        
        if not is_user:
            header_layout.addWidget(left_button)
            header_layout.addWidget(variant_counter_label)
            header_layout.addWidget(right_button)
        header_layout.addWidget(menu_button)

        bubble_layout.addLayout(header_layout)

        message_label = QLabel()
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_label.setText(html_text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        message_label.setFont(font)

        message_label.setStyleSheet(f"""
            QLabel {{
                color: {s["text_color"]};
                font-size: {s["font_size"]}px;
                background: transparent;
                border: none;
                line-height: 1.4;
            }}
        """)
        
        bubble_layout.addWidget(message_label)

        current_chat = char_info["current_chat"]
        chat_content = char_info.get("chats", {}).get(current_chat, {}).get("chat_content", {})

        msg_data = chat_content.get(message_id, {})
        image_rel_path = msg_data.get("image", None)

        if image_rel_path:
            img_full_path = os.path.join(os.getcwd(), "app", "data", ".soul", character_name, image_rel_path)
            if os.path.exists(img_full_path):
                img_pixmap = QPixmap(img_full_path)
                if not img_pixmap.isNull():
                    scaled_img = img_pixmap.scaled(350, 350, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                    img_label = QLabel()
                    img_label.setPixmap(scaled_img)
                    img_label.setStyleSheet("border-radius: 8px; margin-top: 5px;")
                    img_label.setCursor(Qt.CursorShape.PointingHandCursor)
                    
                    def show_full_image(evt, p=img_pixmap):
                        dlg = QDialog()
                        dlg.setWindowTitle("Image Preview")
                        dlg.setStyleSheet("background-color: #1E1E1E;")
                        l = QVBoxLayout(dlg)
                        l.setContentsMargins(0, 0, 0, 0)
                        lbl = QLabel()
                        
                        max_w = min(1200, p.width())
                        max_h = min(900, p.height())
                        full_scaled = p.scaled(max_w, max_h, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
                        
                        lbl.setPixmap(full_scaled)
                        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                        l.addWidget(lbl)
                        dlg.exec()
                        
                    img_label.mousePressEvent = show_full_image
                    bubble_layout.addWidget(img_label)

        message_container.addStretch()
        message_container.addWidget(bubble_frame)
        message_container.addStretch()

        message_frame = SmoothMessageFrame(None)
        message_frame.setLayout(message_container)
        message_frame.setStyleSheet("""
            QMenu { background-color: #1E1E1E; color: #D4D4D4; border: 1px solid #383838; border-radius: 8px; }
            QMenu::item { padding: 6px 20px; background-color: transparent; }
            QMenu::item:selected { background-color: #2D2D2D; color: #FFFFFF; border-radius: 4px; }
        """)

        if insert_at is not None:
            self.chat_container.insertWidget(insert_at, message_frame)
        else:
            self.chat_container.addWidget(message_frame)

        await asyncio.sleep(0.005)
        
        if insert_at is None:
            self.ui.scrollArea_chat.verticalScrollBar().setValue(
                self.ui.scrollArea_chat.verticalScrollBar().maximum()
            )

        self.messages[message_id] = {
            "message_id":           message_id,
            "text":                 text,
            "author_name":          user_name if is_user else character_name,
            "label":                message_label,
            "frame":                message_frame,
            "layout":               message_container,
            "is_user":              is_user,
            "variant_counter_label": variant_counter_label,
        }
        
        if insert_at is not None:
            self.message_order.insert(insert_at, message_id)
        else:
            self.message_order.append(message_id)

        return {
            "message_id":           message_id,
            "label":                message_label,
            "frame":                message_frame,
            "layout":               message_container,
            "left_button":          left_button,
            "right_button":         right_button,
            "variant_counter_label": variant_counter_label,
        }

    def show_message_menu(self, character_name, conversation_method, button, is_user, message_id):
        """
        Displays a context menu for a message (e.g., delete, edit, or continue from the message).
        """
        try:
            translator_idx = self.configuration_settings.get_main_setting("translator") or 0
            translator_enabled = translator_idx != 0

            menu = QMenu()
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setBold(True)
            font.setWeight(75)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            menu.setFont(font)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #1e1e1e;
                    color: #D8DEE9;
                    border-radius: 10px;
                    padding: 3px;
                    font-family: Inter Tight Medium;
                    font-size: 13px;
                    margin: 2px;
                }

                QMenu::item {
                    background-color: transparent;
                    padding: 6px 24px;
                    border-radius: 6px;
                }

                QMenu::item:selected {
                    background-color: #2D2D2D;
                    color: #FFFFFF;
                    border-radius: 6px;
                }

                QMenu::item:disabled {
                    color: #6E7A8A;
                    background-color: transparent;
                    border-radius: 6px;
                }

                QMenu::separator {
                    height: 1px;
                    background: #383838;
                    margin: 4px 0px;
                }

                QMenu::icon {
                    left: 5px;
                }
            """)

            if message_id not in self.messages:
                return

            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 130))   
            shadow.setOffset(0, 4)                  
            menu.setGraphicsEffect(shadow)

            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})

            msg_data = self.messages[message_id]
            text = msg_data["text"]
            msg_data_chat_content = chat_content.get(message_id)

            sequence_number = msg_data_chat_content.get("sequence_number", "N/A")

            edit_action = QAction(self.translations.get("chat_edit_message_2", "Edit"), None)
            delete_action = QAction(self.translations.get("chat_delete_message", "Delete"), None)
            continue_action = QAction(self.translations.get("chat_continue_message", "Continue from this message"), None)
            regenerate_action = QAction(self.translations.get("chat_regenerate_message", "Regenerate"), None)
            translate_action = QAction(self.translations.get("msg_action_translate", "Translate"), None)
            image_gen_action = QAction(self.translations.get("msg_action_generate_image", "Generate Image"), None)

            edit_icon = QtGui.QIcon("app/gui/icons/edit.png")
            delete_icon = QtGui.QIcon("app/gui/icons/delete.png")
            continue_icon = QtGui.QIcon("app/gui/icons/continue.png")
            regenerate_icon = QtGui.QIcon("app/gui/icons/regen.png")
            translate_icon = QtGui.QIcon("app/gui/icons/translator.png")
            image_gen_icon = QtGui.QIcon("app/gui/icons/background_icon.png")

            edit_action.setIcon(edit_icon)
            delete_action.setIcon(delete_icon)
            continue_action.setIcon(continue_icon)
            regenerate_action.setIcon(regenerate_icon)
            translate_action.setIcon(translate_icon)
            image_gen_action.setIcon(image_gen_icon)

            try:
                delete_action.triggered.disconnect()
                edit_action.triggered.disconnect()
                continue_action.triggered.disconnect()
                regenerate_action.triggered.disconnect()
                translate_action.triggered.disconnect()
                image_gen_action.triggered.disconnect()
            except TypeError:
                pass

            if is_user:
                continue_action.triggered.connect(lambda: asyncio.create_task(self.continue_dialog(conversation_method, message_id, character_name)))
                delete_action.triggered.connect(lambda: asyncio.create_task(self.delete_message(character_name, conversation_method, message_id)))
                edit_action.triggered.connect(lambda: asyncio.create_task(self.edit_message(character_name, conversation_method, message_id, text)))
                menu.addAction(continue_action)
                menu.addAction(edit_action)
                menu.addAction(delete_action)
            else:
                delete_action.triggered.connect(lambda: asyncio.create_task(self.delete_message(character_name, conversation_method, message_id)))
                edit_action.triggered.connect(lambda: asyncio.create_task(self.edit_message(character_name, conversation_method, message_id, text)))

                if self.configuration_settings.get_main_setting("image_gen_enabled"):
                    image_gen_action.triggered.connect(lambda _, c=character_name, m=message_id: asyncio.create_task(self.trigger_image_generation(c, m)))
                    menu.addAction(image_gen_action)

                if sequence_number == 1:
                    menu.addAction(edit_action)
                else:
                    regenerate_action.triggered.connect(lambda _: asyncio.create_task(
                        self.regenerate_message(conversation_method, character_name, message_id)
                    ))
                    menu.addAction(regenerate_action)
                    menu.addAction(edit_action)
                    menu.addAction(delete_action)

                    if translator_enabled:
                        translate_action.triggered.connect(
                            lambda: asyncio.create_task(
                                self._translate_single_message(message_id, character_name, conversation_method)
                            )
                        )
                        menu.addAction(translate_action)
            pos = button.mapToGlobal(QtCore.QPoint(button.width() - 30, button.height() + 2))
            def _start_fade():
                anim_timer = QtCore.QTimer(menu)
                anim_timer.setInterval(20)
                opacity = [0.0]
                def fadeIn():
                    opacity[0] = min(opacity[0] + 0.15, 1.0)
                    menu.setWindowOpacity(opacity[0])
                    if opacity[0] >= 1.0:
                        anim_timer.stop()
                anim_timer.timeout.connect(fadeIn)
                anim_timer.start()

            menu.setWindowOpacity(0.0)
            QtCore.QTimer.singleShot(0, _start_fade)
            menu.exec(pos)
        except Exception as e:
            logger.error(f"Unexpected error in show_message_menu: {e}")
            try:
                parent_window = None
                if hasattr(self, "parent_window"):
                    parent_window = self.parent_window
                elif hasattr(self, "main_window"):
                    parent_window = self.main_window
                elif hasattr(self, "parent"):
                    parent_window = self.parent()

                sow_toast(
                    parent=parent_window,
                    title="Menu Error",
                    text=f"Failed to show message menu:\n{str(e)}",
                    msg_type="error"
                )
            except:
                pass
    
    async def _translate_single_message(self, message_id: str, character_name: str, conversation_method: str):
        if message_id not in self.messages:
            return

        label = self.messages[message_id]["label"]

        current_html = label.text()
        if label.property("original_text") is None:
            label.setProperty("original_text", current_html)
            label.setProperty("is_translated", False)
            label.setProperty("cached_translation", None)

        is_translated = label.property("is_translated") or False

        if is_translated:
            label.setText(label.property("original_text"))
            label.setProperty("is_translated", False)
            return

        cached = label.property("cached_translation")
        if cached:
            label.setText(cached)
            label.setProperty("is_translated", True)
            return

        translator_idx  = self.configuration_settings.get_main_setting("translator")
        target_lang_idx = self.configuration_settings.get_main_setting("target_language")
        lang_map_short  = {0: "ru"}
        lang_map_full   = {0: "Russian"}
        target_lang_short = lang_map_short.get(target_lang_idx, "ru")
        target_lang_full  = lang_map_full.get(target_lang_idx, "Russian")

        if translator_idx == 3:
            label.setText("<i style='color:rgba(255,255,255,0.35);font-size:12px;'>AI translating...</i>")
        else:
            label.setText("<i style='color:rgba(255,255,255,0.35);font-size:12px;'>Translating...</i>")

        try:
            doc = QtGui.QTextDocument()
            doc.setHtml(label.property("original_text"))
            plain_text = doc.toPlainText().strip()

            if not plain_text:
                label.setText(label.property("original_text"))
                return

            translated = ""

            if translator_idx in (1, 2):
                # Google / Yandex
                engine = "google" if translator_idx == 1 else "yandex"
                translated = await asyncio.to_thread(
                    self.translator.translate, plain_text, engine, target_lang_short
                )

            elif translator_idx == 3:
                translated = await self._generate_llm_translation(
                    plain_text, target_lang_full, character_name, conversation_method
                )

            else:
                label.setText(label.property("original_text"))
                return

            if not translated:
                label.setText(label.property("original_text"))
                return

            config_data = self.configuration_characters.load_configuration()
            char_info   = config_data["character_list"].get(character_name, {})
            personas    = self.configuration_settings.get_user_data("personas")
            persona_key = char_info.get("selected_persona")
            if persona_key in (None, "None"):
                user_name = "User"
            else:
                try:
                    user_name = personas[persona_key].get("user_name", "User")
                except Exception:
                    user_name = "User"

            translated_html = self.markdown_to_html(translated)
            translated_html = self.apply_macros(translated_html, character_name, user_name)

            label.setProperty("cached_translation", translated_html)
            label.setProperty("is_translated", True)
            label.setText(translated_html)

        except Exception as e:
            logger.error(f"Single message translation error: {e}")
            label.setText(label.property("original_text") or current_html)
            label.setProperty("is_translated", False)
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_translate_error_title", "Translator Error"),
                text=self.translations.get("translate_error", "Translation failed"),
                msg_type="error"
            )
    
    async def trigger_image_generation(self, character_name, message_id):
        try:
            char_info = self.configuration_characters.load_configuration()["character_list"][character_name]
            conversation_method = char_info.get("conversation_method", "Local LLM")
            
            char_description = char_info.get("character_description", "")
            
            current_chat = char_info.get("current_chat", "default")
            chat_content = char_info.get("chats", {}).get(current_chat, {}).get("chat_content", {})

            msg_data = chat_content.get(message_id, {})
            
            if "variants" in msg_data:
                current_variant_id = msg_data.get("current_variant_id", "default")
                variants = msg_data.get("variants", [])
                text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
            else:
                text = msg_data.get("text", "")

            if not text:
                logger.warning(f"No text found for message_id {message_id}")
                return

            chat_history = []
            msg_keys = sorted(chat_content.keys())[-3:]
            for k in msg_keys:
                content = chat_content[k]
                if "variants" in content:
                    v_id = content.get("current_variant_id", "default")
                    txt = next((v["text"] for v in content.get("variants", []) if v["variant_id"] == v_id), "")
                else:
                    txt = content.get("text", "")
                speaker = "Character" if content.get("is_character", True) else "User"
                chat_history.append(f"{speaker}: {txt[:100]}")
            
            conversation_context = "\n".join(chat_history)

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_image_gen_title", "Image Generation"),
                text=self.translations.get("image_gen_started", "Generating image prompt..."),
                msg_type="success"
            )

            system_instruction = (
                "You are an expert prompt engineer for AI image generators (Stable Diffusion, DALL-E, Midjourney). "
                "Create a detailed, comma-separated prompt that will generate a high-quality image of the character "
                "in their current scene. Be specific about visual details."
            )

            user_prompt = f"""Character Information:
    Name: {character_name}
    Description: {char_description}

    Recent Conversation Context:
    {conversation_context}

    Current Message (this is the moment to illustrate):
    {text}

    ---
    INSTRUCTIONS:
    1. Describe the character's EXACT appearance based on Character Information (hair color/style, eye color, clothing, body type, distinctive features).
    2. Describe their CURRENT pose, facial expression, and body language based on the Current Message.
    3. Describe the environment/background based on the conversation context.
    4. Add lighting, mood, and camera angle.
    5. Include the specified Art Style.
    6. Output ONLY the image prompt as comma-separated tags. No explanations, no quotes, no markdown.

    Format: [subject], [appearance details], [pose/expression], [clothing], [environment], [lighting], [mood], [art style]

    Image prompt:"""

            messages = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ]
            
            provider = AIFactory.get_provider(conversation_method)
            if provider:
                img_prompt_text = await self.prompt_engine._memory_llm_call(provider, messages)
            else:
                img_prompt_text = text[:100]

            if not img_prompt_text:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_image_gen_title", "Image Generation"),
                    text=self.translations.get("toast_image_gen_prompt_error", "Failed to generate image prompt."),
                    msg_type="error"
                )
                return

            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_image_gen_title", "Image Generation"),
                text=self.translations.get("toast_image_gen_creating", "Generating image..."),
                msg_type="success"
            )
            
            from app.utils.image_generator import ImageGenerator
            img_gen = ImageGenerator()
            image_path = await img_gen.generate_image(img_prompt_text, character_name)
            
            if image_path:
                msg_data["image"] = image_path
                
                config_data = self.configuration_characters.load_configuration()
                config_data["character_list"][character_name]["chats"][current_chat]["chat_content"] = chat_content

                self.configuration_characters.save_configuration_edit(config_data)
                
                await self.first_render_messages(character_name)
            else:
                sow_toast(
                    parent=self.main_window,
                    title=self.translations.get("toast_image_gen_title", "Image Generation"),
                    text=self.translations.get("toast_image_gen_failed", "Image generation failed."),
                    msg_type="error",
                    duration=5000
                )

        except Exception as e:
            logger.error(f"Image generation error: {e}", exc_info=True)
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_image_gen_title", "Image Generation"),
                text=self.translations.get("toast_image_gen_failed", "Image generation failed."),
                msg_type="error",
                duration=5000
            )

    async def _generate_llm_translation(self, text_to_translate, target_lang, character_name, conversation_method) -> str:
        system_prompt = (
            f"You are a professional literary translator. Your task is to translate the following text into {target_lang}.\n\n"
            "STRICT RULES — follow every rule without exception:\n"
            "1. Output ONLY the translated text. No preamble, no explanations, no comments, no meta-text.\n"
            "2. Do NOT wrap the output in any quotes — not straight (\"), not curly (\u201c\u201d), not guillemets (\u00ab\u00bb).\n"
            "3. Preserve ALL Markdown formatting exactly as-is: *italics*, **bold**, ***bold-italic***, ~~strikethrough~~, `code`, > blockquote. Do not add, remove, or alter any Markdown symbols.\n"
            "4. Preserve ALL special tokens and macros exactly: {{user}}, {{char}}, {{Char}}, {{User}} — copy them verbatim, never translate or modify them.\n"
            "5. Use straight ASCII quotation marks (\") everywhere in the translation. Never use \u00ab\u00bb or \u201c\u201d.\n"
            "6. Preserve the narrative tone, emotional register, and the character's unique voice and personality.\n"
            "7. Preserve line breaks, paragraph structure, and spacing exactly as in the source text.\n"
            "8. Do NOT add any text that is not present in the source — no greetings, no sign-offs, no translator notes.\n"
            "9. If the source text is already in the target language, return it unchanged without any modifications.\n"
            "10. Translate dialogue and action beats naturally — action beats inside *asterisks* remain inside *asterisks* in the translation."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Text to translate:\n{text_to_translate}"}
        ]
        
        try:
            provider = AIFactory.get_provider(conversation_method)
            if not provider:
                logger.error(f"LLM Translation failed: Provider '{conversation_method}' not found.")
                return text_to_translate

            translated_result = await self.prompt_engine._memory_llm_call(provider, messages)

            if not translated_result:
                return text_to_translate

            for open_q, close_q in [('«', '»'), ('"', '"'), ('"', '"'), ('"', '"')]:
                if translated_result.startswith(open_q) and translated_result.endswith(close_q):
                    translated_result = translated_result[1:-1].strip()
                    break

            translated_result = (translated_result
                .replace('«', '"')
                .replace('»', '"')
                .replace('\u201c', '"')
                .replace('\u201d', '"')
                .replace('\u2018', "'")
                .replace('\u2019', "'")
            )

            translated_result = re.sub(
                r'^(Translation|Перевод|Translated text|Result)\s*:\s*',
                '',
                translated_result,
                flags=re.IGNORECASE
            ).strip()

            return translated_result if translated_result else text_to_translate

        except Exception as e:
            logger.error(f"LLM Translation failed for method {conversation_method}: {e}")
            return text_to_translate

    async def delete_message(self, character_name, conversation_method, message_id):
        """
        Deletes a message from the interface and the configuration file.
        """
        try:
            if message_id not in self.messages:
                return
            
            configuration_data = self.configuration_characters.load_configuration()
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})

            if message_id in chat_content:
                deleted_message_data = chat_content[message_id]

                configuration_data["character_list"][character_name]["chats"][current_chat]["chat_content"] = chat_content
                
                self.configuration_characters.save_configuration_edit(configuration_data)

                self.configuration_characters.delete_chat_message(
                    message_id, 
                    character_name
                )

                if message_id in self.messages:
                    self.messages[message_id]["frame"].deleteLater()
                    del self.messages[message_id]
                    self.message_order.remove(message_id)
            
            await self.first_render_messages(character_name)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    async def edit_message(self, character_name, conversation_method, message_id, original_text):
        if message_id not in self.messages:
            return

        msg_data = self.messages[message_id]
        label = msg_data["label"]
        frame = msg_data["frame"]
        
        if getattr(label, "is_editing", False):
            return
        label.is_editing = True

        bubble_layout = label.parentWidget().layout()
        label.hide()
        
        edit_container = QWidget()
        edit_layout = QVBoxLayout(edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(8)
        
        edit_box = QTextEdit()
        box_font = QtGui.QFont()
        box_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        edit_box.setFont(box_font)
        edit_box.setAcceptRichText(False)
        edit_box.setPlainText(original_text)
        
        approx_lines = max(2, len(original_text) // 50 + original_text.count('\n'))
        box_height = max(60, min(400, approx_lines * 22 + 20))
        edit_box.setFixedHeight(box_height)
        
        s = self.get_chat_appearance()
        edit_box.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(0, 0, 0, 0.25);
                color: {s['text_color']};
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Inter Tight Medium';
                font-size: {s['font_size']}px;
            }}
            QTextEdit:focus {{
                border: 1px solid rgba(255, 255, 255, 0.35);
                background-color: rgba(0, 0, 0, 0.4);
            }}
            QScrollBar:vertical {{
                background: transparent; width: 6px; margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,0.2); border-radius: 3px;
            }}
        """)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: 'Inter Tight SemiBold';
                font-size: 12px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.2); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.05); }
        """
        
        cancel_btn = QPushButton(self.translations.get("cancel", "Cancel"))
        btn_font = QtGui.QFont()
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        cancel_btn.setFont(btn_font)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(btn_style)
        
        save_btn = QPushButton(self.translations.get("chat_save_message", "Save"))
        btn_font = QtGui.QFont()
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        save_btn.setFont(btn_font)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(btn_style)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        edit_layout.addWidget(edit_box)
        edit_layout.addLayout(btn_layout)
        
        idx = bubble_layout.indexOf(label)
        bubble_layout.insertWidget(idx + 1, edit_container)
        
        if hasattr(frame, 'update_smooth_height'):
            QtCore.QTimer.singleShot(10, frame.update_smooth_height)

        def on_cancel():
            label.is_editing = False
            asyncio.create_task(self.first_render_messages(character_name))

        def on_save():
            new_text = edit_box.toPlainText().strip()
            if not new_text:
                return 
            
            label.is_editing = False
            asyncio.create_task(self._process_inline_edit(character_name, conversation_method, message_id, new_text))

        cancel_btn.clicked.connect(on_cancel)
        save_btn.clicked.connect(on_save)

    async def _process_inline_edit(self, character_name, conversation_method, message_id, new_text):
        if message_id not in self.messages:
            return

        try:
            self.configuration_characters.edit_chat_message(
                message_id=message_id,
                character_name=character_name,
                edited_text=new_text
            )
                
            self.configuration_characters.update_chat_history(character_name)
            
        except Exception as e:
            logger.error(f"Error saving inline edit: {e}")
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_message_editor_title", "Message Editor"),
                text=self.translations.get("edit_save_error", "Failed to save edited message!"),
                msg_type="error"
            )
            
        await self.first_render_messages(character_name)

    async def continue_dialog(self, conversation_method, message_id, character_name):
        """
        Deletes all messages that come after the specified message.
        """
        configuration_data = self.configuration_characters.load_configuration()
        char_data = configuration_data["character_list"].get(character_name)
        if not char_data:
            logger.error(f"Character '{character_name}' not found.")
            return

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        all_message_ids = list(chat_content.keys())
        try:
            selected_index = all_message_ids.index(message_id)
        except ValueError:
            logger.warning(f"Message ID {message_id} not found in chat_content.")
            return

        ids_to_delete = all_message_ids[selected_index + 1:]
        
        for msg_id in ids_to_delete:
            if msg_id in self.messages:
                self.messages[msg_id]["frame"].deleteLater()
                del self.messages[msg_id]
            if msg_id in self.message_order:
                self.message_order.remove(msg_id)

        self.configuration_characters.delete_chat_messages(character_name, ids_to_delete)

        await asyncio.sleep(0.05)
        await self.first_render_messages(character_name)

        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))

    def save_changes(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Saves changes to the configuration file for the specified character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data["character_list"]
        
        if character_name not in character_list:
            sow_toast(
                parent=self.main_window,
                title=self.translation.get("toast_character_editor_title", "Character Editor"),
                text=self.translations.get("character_edit_error_2", "Character was not found in the configuration."),
                msg_type="error"
            )
            dialog.close()
            return

        character_list[character_name]["character_title"] = creator_notes_edit.toPlainText()
        character_list[character_name]["character_description"] = description_edit.toPlainText()
        character_list[character_name]["character_personality"] = personality_edit.toPlainText()
        character_list[character_name]["scenario"] = scenario_edit.toPlainText()
        character_list[character_name]["first_message"] = first_message_edit.toPlainText()
        character_list[character_name]["example_messages"] = example_messages_edit.toPlainText()
        raw_text = alternate_greetings_edit.toPlainText().strip()
        if raw_text:
            greetings_list = [g.strip() for g in raw_text.split("<GREETING>") if g.strip()]
        else:
            greetings_list = []
        character_list[character_name]["alternate_greetings"] = greetings_list 
        
        new_name = name_edit.text()
        if new_name == character_name:
            pass
        else:
            character_data = character_list.pop(character_name)
            character_list[new_name] = character_data

        configuration_data["character_list"] = character_list
        self.configuration_characters.save_configuration_edit(configuration_data)

        sow_toast(
            parent=self.main_window,
            title=self.translations.get("toast_character_editor_title", "Settings"),
            text=self.translations.get("character_edit_saved_2", "The changes were saved successfully!"),
            msg_type="success"
        )
        asyncio.create_task(self.open_chat(new_name))
        dialog.close()

    async def start_new_dialog(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        title = self.translations.get("character_edit_start_new_dialogue", "Start new dialogue")
        message = self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue? The previous dialogue will be deleted.")

        dialog = SowConfirmDialog(
            parent=self.main_window,
            title=title,
            text=message,
            confirm_text="Confirm",
            danger=True
        )
        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return

        chat_name, ok = QInputDialog.getText(
            dialog,
            self.translations.get("new_chat_title", "New Chat"),
            self.translations.get("new_chat_prompt", "Enter chat name:")
        )

        if not ok or not chat_name.strip():
            chat_name = self.translations.get("default_chat_name", "Default Chat")

        new_name = name_edit.text()
        new_description = description_edit.toPlainText()
        new_personality = personality_edit.toPlainText()
        new_scenario = scenario_edit.toPlainText()
        new_first_message = first_message_edit.toPlainText()
        new_example_messages = example_messages_edit.toPlainText()
        raw_text = alternate_greetings_edit.toPlainText().strip()
        if raw_text:
            greetings_list = [g.strip() for g in raw_text.split("<GREETING>") if g.strip()]
        else:
            greetings_list = []
        new_alternate_greetings = greetings_list
        new_creator_notes = creator_notes_edit.toPlainText()
        
        self.configuration_characters.create_new_chat(character_name, conversation_method, new_name, new_description, new_personality, new_scenario, new_first_message, new_example_messages, new_alternate_greetings, new_creator_notes, chat_name)

        self.messages.clear()
        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.ui.stackedWidget.setCurrentWidget(self.ui.main_characters_page)

        sow_toast(
            parent=self.main_window,
            title=self.translations.get("new_chat_toast_title", "Chat System"),
            text=self.translations.get("character_edit_start_new_dialogue_success", "A new dialogue has been successfully started!"),
            msg_type="success"
        )
    
        dialog.close()
        await self.set_main_tab()
        await self.close_chat()
        self.main_window.updateGeometry()

    def markdown_to_html(self, text):
        s = self.get_chat_appearance()
        qc = s.get("quote_color", "#FFA500")
        ic = s.get("italic_color", "#a3a3a3")
        cbg = s.get("code_bg_color", "#1a1a1a")

        # 1. Text in double quotes ("text")
        text = re.sub(r'"(.*?)"', rf'<span style="color: {qc};">"\1"</span>', text)
        text = re.sub(r'“(.*?)”', rf'<span style="color: {qc};">"\1"</span>', text)

        # 2. Bold text (**text** or __text__)
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)

        # 3. Italics (*text* or _text_)
        text = re.sub(r'\*(.*?)\*', rf'<i><span style="color: {ic};">\1</span></i>', text)
        text = re.sub(r'_(.*?)_', rf'<i><span style="color: {ic};">\1</span></i>', text)

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
            rf'<pre style="background-color: {cbg}; color: #c7c7c7; border-radius: 6px; font-family: Inter Tight Light;">\1</pre>',
            text,
            flags=re.DOTALL
        )

        # 8. Inline code (`code`)
        text = re.sub(
            r'`([^`]+)`',
            rf'<code style="background-color: {cbg}; color: #c7c7c7; border-radius: 6px; font-family: Inter Tight Light;">\1</code>',
            text
        )

        # 9. Line break (\n)
        text = text.replace('\n', '<br>')

        return text

    def ensure_header_image_on_top(self):
        if not hasattr(self, '_header_image_added') or not self._header_image_added:
            return

        for i in range(self.chat_container.count()):
            item = self.chat_container.itemAt(i)
            if item.layout() is not None:
                widget_items = [item.layout().itemAt(j).widget() for j in range(item.layout().count())]
                if any(isinstance(w, QLabel) and w.pixmap() for w in widget_items):
                    layout = item.layout()
                    self.chat_container.removeItem(item)
                    self.chat_container.insertLayout(0, layout)
                    break
    
    @asyncSlot(str)
    async def add_header_image(self, text):
        image_matches = re.findall(r'!\[(.*?)\]\((.*?)\)', text)
        if not image_matches:
            return

        for i in reversed(range(self.chat_container.count())):
            item = self.chat_container.itemAt(i)

            if item.widget() and isinstance(item.widget(), QLabel) and item.widget().pixmap():
                widget = item.widget()
                logger.info(f"Removing header image widget at index {i}")
                widget.deleteLater()
                self.chat_container.removeItem(item)
                continue

            if item.layout():
                layout = item.layout()

                for j in reversed(range(layout.count())):
                    inner_item = layout.itemAt(j)
                    if inner_item.widget() and isinstance(inner_item.widget(), QLabel) and inner_item.widget().pixmap():
                        widget = inner_item.widget()
                        logger.info(f"Removing image from layout at position ({i}, {j})")
                        layout.removeItem(inner_item)
                        widget.deleteLater()

        has_existing_image = False
        first_item = self.chat_container.itemAt(0)
        if first_item and first_item.layout() and first_item.layout().count() > 0:
            widget = first_item.layout().itemAt(0).widget()
            if isinstance(widget, QLabel) and widget.pixmap():
                has_existing_image = True

        if hasattr(self, '_header_image_added') and self._header_image_added and has_existing_image:
            return

        image_container = QHBoxLayout()
        image_container.setSpacing(5)
        image_container.setContentsMargins(0, 10, 0, 10)

        for alt_text, image_url in image_matches:
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            file_extension = os.path.splitext(image_url)[-1]
            cache_file_path = os.path.join(CACHE_DIR, f"{url_hash}{file_extension}")

            image_label = QLabel("Loading image...")
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            try:
                if os.path.exists(cache_file_path):
                    pixmap = QPixmap(cache_file_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(
                            400, 300,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        image_label.setPixmap(pixmap)
                    else:
                        image_label.setText("")
                else:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image_url, headers=headers) as response:
                            if response.status == 200:
                                image_data = await response.read()
                                pixmap = QPixmap()
                                pixmap.loadFromData(image_data)
                                if not pixmap.isNull():
                                    with open(cache_file_path, "wb") as cache_file:
                                        cache_file.write(image_data)
                                    pixmap = pixmap.scaled(
                                        400, 300,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation
                                    )
                                    image_label.setPixmap(pixmap)
                                else:
                                    image_label.setText("")
            except Exception as e:
                logger.error(f"Error loading header image {image_url}: {e}")

            image_container.addWidget(image_label)

        self.chat_container.insertLayout(0, image_container)
        self._header_image_added = True

    def change_variant(self, character_name, direction):
        """
        Switches to the previous or next variant of the last character message.
        """
        config = self.configuration_characters.load_configuration()
        char_data = config["character_list"].get(character_name)
        if not char_data:
            return

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)

        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        variants = self.get_available_variants(character_name)

        if len(variants) <= 1:
            return

        current_idx = self.get_current_variant_index(character_name)
        if current_idx == -1:
            return

        new_idx = (current_idx + direction) % len(variants)
        new_variant = variants[new_idx]

        last_key = self.get_last_character_message_index(chat_content)
        if not last_key:
            return

        chat_content[last_key]["current_variant_id"] = new_variant["variant_id"]
        chats[current_chat]["chat_content"] = chat_content
        
        config["character_list"][character_name] = character_information
        self.configuration_characters.save_configuration_edit(config)

        message_id = last_key
        if message_id not in self.messages:
            return

        message_entry = self.messages[message_id]
        label = message_entry.get("label")
        counter_label = message_entry.get("variant_counter_label")

        if label:
            label.setText(new_variant["text"])
            label.adjustSize()

        last_char_msg_id = self.get_last_character_message_index(chat_content)
        if not last_char_msg_id:
            return

        msg_data = chat_content[last_char_msg_id]
        variants = msg_data.get("variants", [])
        current_idx = self.get_current_variant_index(character_name)
        total = len(variants)

        if last_char_msg_id in self.messages:
            message_entry = self.messages[last_char_msg_id]
            counter_label = message_entry.get("variant_counter_label")
            if counter_label:
                counter_label.setText(f"{current_idx + 1}/{total}" if current_idx != -1 else f"1/{total}")
                counter_label.setVisible(len(variants) > 1)

        asyncio.create_task(self.first_render_messages(character_name))
        self.configuration_characters.update_chat_history(character_name)

    def get_available_variants(self, character_name):
        """
        Returns list of available variants of the last character message.
        """
        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        conversation_method = character_information["conversation_method"]

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})
        
        last_char_index = self.get_last_character_message_index(chat_content)
        if last_char_index is None:
            return []

        msg = chat_content.get(last_char_index, {})
        return msg.get("variants", [])

    def get_current_variant_index(self, character_name):
        """
        Returns index of current variant in the last character message.
        """
        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        last_char_index = self.get_last_character_message_index(chat_content)
        if last_char_index is None:
            return -1

        msg_data = chat_content[last_char_index]
        variants = msg_data.get("variants", [])
        current_id = msg_data.get("current_variant_id", "default")

        for idx, variant in enumerate(variants):
            if variant.get("variant_id") == current_id:
                return idx

        return -1

    def get_last_character_message_index(self, chat_content):
        for key, msg in reversed(chat_content.items()):
            if not msg.get("is_user", True):
                return key
        return None

    async def _maybe_translate(self, text, is_user, character_name, conversation_method, is_history_load = False) -> str:
        if is_history_load:
            return text

        translator_idx = self.configuration_settings.get_main_setting("translator")
        target_language_idx = self.configuration_settings.get_main_setting("target_language")

        if translator_idx == 0:
            return text
            
        if target_language_idx != 0:
            return text

        if translator_idx in (1, 2):
            # 1 - Google, 2 - Yandex
            service = "google" if translator_idx == 1 else "yandex"
            return await self.translator.translate_async(text, service, "ru")
            
        elif translator_idx == 3:
            # 3 - LLM
            return await self._generate_llm_translation(text, target_lang="Russian", character_name=character_name, conversation_method=conversation_method)

        return text

    def _on_chat_scroll(self, value):
        if getattr(self, '_chat_is_loading_history', False) or getattr(self, '_is_chat_rendering', False):
            return

        if value <= 50:
            if hasattr(self, '_chat_loaded_count') and hasattr(self, '_chat_all_messages'):
                if self._chat_loaded_count < len(self._chat_all_messages):
                    asyncio.create_task(self._load_older_messages())

    async def _load_older_messages(self):
        self._chat_is_loading_history = True
        
        scrollbar = self.ui.scrollArea_chat.verticalScrollBar()
        old_max = scrollbar.maximum()
        old_val = scrollbar.value()
        
        self.chat_widget.setUpdatesEnabled(False)
        
        total_msgs = len(self._chat_all_messages)
        end_idx = total_msgs - self._chat_loaded_count
        start_idx = max(0, end_idx - self._chat_chunk_size)
        
        chunk = self._chat_all_messages[start_idx:end_idx]
        
        character_name = self.current_active_character
        
        insert_index = 0
        
        for message_id, msg_data in chunk:
            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants",[])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
            
            await self.add_header_image(text)
            await self.add_message(
                character_name=character_name, 
                text=text, 
                is_user=is_user, 
                message_id=message_id, 
                insert_at=insert_index
            )
            insert_index += 1
            
        self._chat_loaded_count += len(chunk)
        self.ensure_header_image_on_top()
        
        self.chat_widget.setUpdatesEnabled(True)
        QApplication.processEvents() 
        
        new_max = scrollbar.maximum()
        height_diff = new_max - old_max
        scrollbar.setValue(old_val + height_diff)
        
        await asyncio.sleep(0.1)
        self._chat_is_loading_history = False

    async def first_render_messages(self, character_name):
        self._is_chat_rendering = True
        try:
            self.chat_widget.setUpdatesEnabled(False)
            self.ui.scrollArea_chat.setUpdatesEnabled(False)
            self.ui.scrollArea_chat.viewport().setUpdatesEnabled(False)

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
            character_information = character_data.get("character_list", {}).get(character_name)

            if not character_information:
                logger.warning(f"Character {character_name} not found in config.")
                self.chat_widget.setUpdatesEnabled(True)
                self.ui.scrollArea_chat.viewport().setUpdatesEnabled(True)
                self.ui.scrollArea_chat.setUpdatesEnabled(True)
                return
            
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})
            chat_content = chats[current_chat].get("chat_content", {})

            sorted_messages = sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf')))
            
            self._chat_all_messages = sorted_messages
            
            chunk = self._chat_all_messages[-self._chat_chunk_size:]
            self._chat_loaded_count = len(chunk)

            for message_id, msg_data in chunk:
                is_user = msg_data.get("is_user", False)
                current_variant_id = msg_data.get("current_variant_id", "default")
                variants = msg_data.get("variants", [])
                text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
                
                await self.add_header_image(text)
                await self.add_message(character_name=character_name, text=text, is_user=is_user, message_id=message_id)

            self.ensure_header_image_on_top()
            
            self.ui.scrollArea_chat.viewport().setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setUpdatesEnabled(True)
            self.chat_widget.setUpdatesEnabled(True)
            
            await asyncio.sleep(0) 
            
            scrollbar = self.ui.scrollArea_chat.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        finally:
            self._is_chat_rendering = False
    
    async def render_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.viewport().setUpdatesEnabled(False)

        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)
        conversation_method = character_information.get("conversation_method", "Local LLM")

        if not character_information:
            self.chat_widget.setUpdatesEnabled(True)
            self.ui.scrollArea_chat.viewport().setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setUpdatesEnabled(True)
            return
        
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})
        chat_content = chats[current_chat].get("chat_content", {})
        
        sorted_chat_content = sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf')))
        if len(sorted_chat_content) > 100:
            sorted_chat_content = sorted_chat_content[-100:]
        limited_chat_content = dict(sorted_chat_content)

        new_message_ids = list(limited_chat_content.keys())
        existing_ids = set(self.messages.keys())

        for msg_id in list(existing_ids - set(new_message_ids)):
            widget = self.messages[msg_id].get("frame")
            if widget:
                widget.deleteLater()
            del self.messages[msg_id]
            if msg_id in self.message_order:
                self.message_order.remove(msg_id)

        current_persona = character_information.get("selected_persona")
        personas_data = self.configuration_settings.get_user_data("personas")
        user_name = "User"
        if current_persona and current_persona != "None":
            user_name = personas_data.get(current_persona, {}).get("user_name", "User")

        for message_id, msg_data in limited_chat_content.items():
            if not message_id:
                continue

            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants",[])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
            author_name = msg_data.get("author_name", character_name if not is_user else "User")

            if message_id in self.messages:
                message_entry = self.messages[message_id]
                message_label = message_entry.get("label")
                
                html_text = re.sub(r'\s*!\[.*?\]\(.*?\)\s*', ' ', text)
                html_text = self.markdown_to_html(html_text)
                text_for_display = self.apply_macros(html_text, character_name, user_name)

                if message_label:
                    message_label.setText(text_for_display)
                    
                message_entry.update({"text": text, "author_name": author_name, "is_user": is_user})
                
            else:
                await self.add_header_image(text)
                await self.add_message(character_name=character_name, text=text, is_user=is_user, message_id=message_id)

        self.message_order =[msg_id for msg_id in new_message_ids if msg_id in self.messages]

        for idx, msg_id in enumerate(self.message_order):
            if msg_id in self.messages:
                widget = self.messages[msg_id]["frame"]
                if self.chat_container.indexOf(widget) != idx:
                    self.chat_container.insertWidget(idx, widget)

        self.ensure_header_image_on_top()
        
        self.ui.scrollArea_chat.viewport().setUpdatesEnabled(True)
        self.ui.scrollArea_chat.setUpdatesEnabled(True)
        self.chat_widget.setUpdatesEnabled(True)
        
        QApplication.processEvents()
        
        scrollbar = self.ui.scrollArea_chat.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    async def detect_emotion(self, character_name, text):
        """
        Detects emotion and updates the character's expression (image, Live2D model or VRM) along with motions.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]

        expression_images_folder = character_information["expression_images_folder"]
        live2d_model_folder = character_information["live2d_model_folder"]
        current_sow_system_mode = character_information["current_sow_system_mode"]

        if current_sow_system_mode == "Nothing":
            return

        if self.tokenizer is None or self.model is None:
            def _load_model():
                tokenizer_path = os.path.join("app", "utils", "emotions", "detector")
                tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
                model = AutoModelForSequenceClassification.from_pretrained(tokenizer_path)
                return tokenizer, model
            self.tokenizer, self.model = await asyncio.to_thread(_load_model)

        def _run_inference():
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
            return torch.argmax(outputs.logits, dim=1).item()

        predicted_class_id = await asyncio.to_thread(_run_inference)

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
                if self.stackedWidget_expressions is not None:
                    self.stackedWidget_expressions.setCurrentWidget(self.live2d_page)
                else:
                    logger.error("Live2D model file not found.")
                
                if hasattr(self, "live2d_widget") and self.live2d_widget:
                    motion_map = character_info.get("emotion_motions", {})
                    target_motion = motion_map.get(emotion)
                    
                    if target_motion == "none":
                        logger.debug(f"[Live2D Motion] Emotion '{emotion}' is mapped to silent/none.")
                    else:
                        if not target_motion:
                            target_motion = DEFAULT_EMOTION_MOTIONS.get(emotion, "Idle")
                        
                        logger.info(f"[Live2D Motion] Playing group '{target_motion}' for detected emotion '{emotion}'")
                        self.live2d_widget.play_motion_safely(target_motion)

        elif current_sow_system_mode == "VRM":
            self.show_emotion_animation(character_name)

        if hasattr(self, 'web_bridge') and self.web_bridge:
            asyncio.create_task(self.web_bridge.manager.broadcast({
                "type": "emotion_changed",
                "emotion": emotion
            }))
        
        return emotion

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

        with open(model_json_path, "w", encoding="utf-8") as file:
            json.dump(model_data, file, indent=4, ensure_ascii=False)

    def show_emotion_image(self, expression_images_folder, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        current_chat = character_info["current_chat"]
        chats = character_info.get("chats", {})
        current_emotion = chats[current_chat].get("current_emotion", "neutral")

        image_name = self.emotion_resources[current_emotion]["image"]
        
        if hasattr(self, 'expression_image_label') and self.expression_image_label is not None:
            gif_path = os.path.join(expression_images_folder, f"{image_name}.gif")
            png_path = os.path.join(expression_images_folder, f"{image_name}.png")
            neutral_gif_path = os.path.join(expression_images_folder, "neutral.gif")
            neutral_png_path = os.path.join(expression_images_folder, "neutral.png")

            if os.path.exists(gif_path):
                movie = QtGui.QMovie(gif_path)
                self.expression_image_label.set_emotion_movie(movie)
            elif os.path.exists(neutral_gif_path):
                movie = QtGui.QMovie(neutral_gif_path)
                self.expression_image_label.set_emotion_movie(movie)
            elif os.path.exists(png_path):
                pixmap = QtGui.QPixmap(png_path)
                self.expression_image_label.set_emotion_pixmap(pixmap)
            elif os.path.exists(neutral_png_path):
                pixmap = QtGui.QPixmap(neutral_png_path)
                self.expression_image_label.set_emotion_pixmap(pixmap)
            else:
                logger.error(f"Files for emotion {image_name} and neutral not found.")

            if self.stackedWidget_expressions is not None:
                self.stackedWidget_expressions.setCurrentWidget(self.expression_image_page)

    def show_emotion_animation(self, character_name):
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]

        current_chat = character_info["current_chat"]
        chats = character_info.get("chats", {})
        current_emotion = chats[current_chat]["current_emotion"]

        self.set_expression_vrm(current_emotion)
        self.play_vrm_animation(current_emotion)
        
    async def open_sow_system(self, character_name):
        """
        Opens the Soul of Waifu System for the specified character.
        """
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][character_name]

        current_text_to_speech = character_information["current_text_to_speech"]
        current_sow_system_mode = character_information["current_sow_system_mode"]
        gui_mode = self.configuration_settings.get_main_setting("live2d_mode")

        app = QtWidgets.QApplication.instance()
        app.main_window = self.main_window
        
        if current_text_to_speech in ("Nothing", None):
            sow_toast(
                parent=self.main_window,
                title=self.translations.get("toast_call_system_title", "Call System"),
                text=self.translations.get("voice_error_body", "Assign a character's voice before you go on to the call."),
                msg_type="error",
                duration=6000
            )
        else:
            personas_data = self.configuration_settings.get_user_data("personas")
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][character_name]
            current_persona = character_info.get("selected_persona")

            if current_persona == "None" or current_persona is None:
                self.user_avatar = "app/gui/icons/person.png"
            else:
                if current_persona not in personas_data:
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("toast_profile_error_title", "Profile Error"),
                        text=self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."),
                        msg_type="error",
                        duration=6000
                    )
                    return
                else:
                    self.user_avatar = personas_data[current_persona].get("user_avatar", "")
                    
                    if not self.user_avatar or not os.path.exists(self.user_avatar):
                        self.user_avatar = "app/gui/icons/person.png"
            
            if gui_mode == 1:
                if current_sow_system_mode in ("Nothing", "Expressions Images"):
                    sow_toast(
                        parent=self.main_window,
                        title=self.translations.get("toast_companion_error_title", "Companion Error"),
                        text=self.translations.get("no_gui_error_body", "Select Live2D or VRM to use the non-interface mode."),
                        msg_type="error",
                        duration=6000
                    )
                    return
                else:
                    self.sow_system = Soul_Of_Waifu_System(self.main_window, character_name)
                    asyncio.create_task(self.sow_system.initialize_sow_system(character_name))
            else:
                self.sow_system = Soul_Of_Waifu_System(self.main_window, character_name)
                asyncio.create_task(self.sow_system.initialize_sow_system(character_name))

    def open_image_gen_settings(self):
        """
        Opens a dialog for configuring AI Image Generation settings.
        """
        dialog = ImageGenSettingsDialog(self.translations, self.configuration_settings, self.configuration_api, self.main_window, parent=self.main_window)
        dialog.exec()
