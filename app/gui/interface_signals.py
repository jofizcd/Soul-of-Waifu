import os
import re
import ssl
import uuid
import json
import base64
import hashlib
import logging
import threading
import traceback
import datetime
import urllib.request
from pathlib import Path
from multiprocessing import freeze_support

import yaml
import torch
import aiohttp
import asyncio
import tiktoken
import edge_tts
import sounddevice as sd
import OpenGL.GL as gl
from socketserver import TCPServer
import live2d.v3 as live2d
from live2d.utils.image import Image
from PIL import Image, PngImagePlugin
from qasync import asyncSlot
from http.server import SimpleHTTPRequestHandler
from collections import deque
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QUrl, Qt, QTimerEvent, QPropertyAnimation, QEasingCurve, QPointF
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QPainter, QAction, QColor, QCursor
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QMessageBox, QPushButton,
    QWidget, QHBoxLayout, QDialog, QVBoxLayout, QStackedWidget, QFileDialog,
    QGraphicsDropShadowEffect, QFrame, QMenu, QTextEdit, QLineEdit, QColorDialog, QSlider, QSpinBox,
    QScrollArea, QSizePolicy, QGridLayout
)

from app.utils.ai_clients.local_ai_client import LocalAI
from app.utils.ai_clients.mistral_ai_client import MistralAI
from app.utils.ai_clients.openai_client import OpenAI
from app.utils.ai_clients.character_ai_client import CharacterAI
from app.utils.translator import Translator
from app.utils.character_cards import CharactersCard, SoulGateway
from app.utils.text_to_speech import ElevenLabs, XTTSv2_SOW_System, EdgeTTS, KokoroTTS_SOW_System, SileroTTS_SOW_System, AudioPlaybackWorker
from app.utils.ambient_client import AmbientPlayer
from app.utils.models_hub import ModelSearch, ModelRecommendations, ModelPopular, ModelInformation, ModelRepoFiles, FileSelectorDialog, FileDownloader, ModelItemWidget, RecommendedModelItemWidget
from app.gui.sow_system_signals import Soul_Of_Waifu_System
from app.configuration import configuration

logger = logging.getLogger("Interface Signals")

CACHE_DIR = os.path.join(os.getcwd(), "app/cache")

tiktoken_dir = Path(__file__).parent.parent.parent / "app" / "utils" / "ai_clients"
assert (tiktoken_dir / "9b5ad71b2ce5302211f9c61530b329a4922fc6a4").exists(), "File not found!"
os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_dir)

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
        self.session = None
        self.tokenizer = None

        # --- Card Management ---
        self.cards = []
        self.soul_cards = []
        self.cai_cards = []
        self.gate_cards = []

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

        self.cai_grid_layout = QtWidgets.QGridLayout()
        self.cai_grid_layout.setSpacing(10)
        self.cai_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.cai_container = QWidget()
        self.cai_container.setLayout(self.cai_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_character_ai_page, self.cai_container)

        self.gate_cards_grid_layout = QtWidgets.QGridLayout()
        self.gate_cards_grid_layout.setSpacing(10)
        self.gate_cards_grid_layout.setContentsMargins(0, 20, 20, 20)
        self.gate_container = QWidget()
        self.gate_container.setLayout(self.gate_cards_grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_character_card, self.gate_container)

        # --- Chat Input Setup ---
        self.textEdit_write_user_message = self._replace_text_edit()
        self.current_max_height = 40

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

        self._is_switching_tab = False

        # --- Configuration Initialization ---
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.configuration_settings.update_main_setting("conversation_method", "Character AI")

        # --- AI Client Initialization ---
        self.character_ai_client = CharacterAI()
        self.mistral_ai_client = MistralAI(self.ui)
        self.open_ai_client = OpenAI(self.ui)
        self.local_ai_client = LocalAI(self.ui)
        
        # --- TTS Client Initialization ---
        self.eleven_labs_client = ElevenLabs()
        self.edge_tts_client = EdgeTTS()
        self.xttsv2_client = XTTSv2_SOW_System()
        self.kokoro_client = KokoroTTS_SOW_System()
        self.silero_client = SileroTTS_SOW_System()

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
        self.setup_appearance_tab()
        QtCore.QTimer.singleShot(100, lambda: self.apply_gui_theme(self.get_gui_theme()))
        self.apply_window_theme()

        freeze_support()

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
    
    def setup_appearance_tab(self):
        def get_font():
            f = QFont()
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        s = self.get_chat_appearance()

        def tr(key, default):
            return self.translations.get(key, default)
            
        def tr_col(name, key_suffix):
            return self.translations.get(f"appearance_color_{key_suffix}", name)

        FULL_PRESETS = [
            {"name": tr("appearance_preset_default", "Default"),   "user": "#292929", "char": "#222222", "text": "#E8E8E8", "quote": "#E8A040", "italic": "#A0A0A0"},
            {"name": tr("appearance_preset_nord", "Nord"),         "user": "#2E3440", "char": "#3B4252", "text": "#E5E9F0", "quote": "#88C0D0", "italic": "#A3BE8C"},
            {"name": tr("appearance_preset_dracula", "Dracula"),   "user": "#282A36", "char": "#44475A", "text": "#F8F8F2", "quote": "#BD93F9", "italic": "#FFB86C"},
            {"name": tr("appearance_preset_onedark", "One Dark"),  "user": "#282C34", "char": "#21252B", "text": "#ABB2BF", "quote": "#E5C07B", "italic": "#98C379"},
            {"name": tr("appearance_preset_material", "Material"), "user": "#1D1B20", "char": "#2B2930", "text": "#E6E1E5", "quote": "#D0BCFF", "italic": "#9AA0A6"},
            {"name": tr("appearance_preset_sakura", "Sakura"),     "user": "#2A1E24", "char": "#35262D", "text": "#F7E7E9", "quote": "#F4A7B9", "italic": "#D9B8C4"},
            {"name": tr("appearance_preset_abyss", "Abyss"),       "user": "#151515", "char": "#0F0F0F", "text": "#C8C8C8", "quote": "#909090", "italic": "#787878"},
        ]
        TEXT_COLORS = [
            {"name": tr_col("White", "white"), "color": "#F0F0F0"}, {"name": tr_col("Soft", "soft"), "color": "#D8D8D8"}, 
            {"name": tr_col("Dimmed", "dimmed"), "color": "#AAAAAA"}, {"name": tr_col("Warm Gray", "warm_gray"), "color": "#C8BEB0"}, 
            {"name": tr_col("Cool Gray", "cool_gray"), "color": "#A8B4C0"}, {"name": tr_col("Cream", "cream"), "color": "#EDE0C8"}, 
            {"name": tr_col("Arctic", "arctic"), "color": "#C8D8E8"}, {"name": tr_col("Lavender", "lavender"), "color": "#C8C0DC"}, 
            {"name": tr_col("Sage", "sage"), "color": "#B8CCA8"}
        ]
        QUOTE_COLORS = [
            {"name": tr_col("Amber", "amber"), "color": "#D4903A"}, {"name": tr_col("Gold", "gold"), "color": "#C8A84A"}, 
            {"name": tr_col("Coral", "coral"), "color": "#C06858"}, {"name": tr_col("Arctic", "arctic"), "color": "#70A8C0"}, 
            {"name": tr_col("Sky", "sky"), "color": "#6090B8"}, {"name": tr_col("Lavender", "lavender"), "color": "#9878CC"}, 
            {"name": tr_col("Lilac", "lilac"), "color": "#B8A0E0"}, {"name": tr_col("Sakura", "sakura"), "color": "#D08898"}, 
            {"name": tr_col("Muted", "muted"), "color": "#888888"}
        ]
        ITALIC_COLORS = [
            {"name": tr_col("Gray", "gray"), "color": "#909090"}, {"name": tr_col("Warm Gray", "warm_gray"), "color": "#A09080"}, 
            {"name": tr_col("Cool Gray", "cool_gray"), "color": "#8898A8"}, {"name": tr_col("Nord Green","nord_green"),"color": "#8DAA78"}, 
            {"name": tr_col("Dracula", "dracula_orange"), "color": "#D4A060"}, {"name": tr_col("Rose", "rose"), "color": "#C0A0A8"}, 
            {"name": tr_col("Dim", "dim"), "color": "#686868"}
        ]
        CARD_STYLE = """
            QFrame {
                background-color: rgba(0, 0, 0, 70); 
                border-radius: 12px;
                border: 1px solid #2A2A2A;
            }
        """
        SECTION_LBL_STYLE = """
            QLabel {
                color: #6E6E6E;
                font-family: 'Inter Tight SemiBold', 'Arial';
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }
        """
        PARAM_LBL_STYLE = """
            QLabel {
                color: #D4D4D4;
                font-family: 'Inter Tight Medium';
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """
        H_SEP_STYLE = "QFrame { background-color: #2A2A2A; border: none; max-height: 1px; }"

        tab = QWidget()
        tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tab.setObjectName("appearance_tab")
        tab.setStyleSheet("background-color: transparent;")

        main_layout = QHBoxLayout(tab)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        def create_section_lbl(text):
            lbl = QLabel(text)
            lbl.setFont(get_font())
            lbl.setStyleSheet(SECTION_LBL_STYLE)
            return lbl

        def create_h_sep():
            f = QFrame()
            f.setFrameShape(QFrame.Shape.HLine)
            f.setStyleSheet(H_SEP_STYLE)
            return f

        def swatch_style_pair(user_clr, char_clr, selected=False):
            border = "#666666" if selected else "transparent"
            bg = f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {user_clr},stop:0.499 {user_clr}, stop:0.5 {char_clr},stop:1 {char_clr})"
            return f"QPushButton {{ background: {bg}; border-radius: 8px; border: 2px solid {border}; }} QPushButton:hover {{ border: 2px solid #888888; }} QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 500; }}"

        def swatch_style_single(clr, selected=False):
            border = "#666666" if selected else "transparent"
            return f"QPushButton {{ background: {clr}; border-radius: 8px; border: 2px solid {border}; }} QPushButton:hover {{ border: 2px solid #888888; }} QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 500; }}"

        def create_swatch_grid(items, key, target_dict, apply_fn, is_pair=False):
            wrapper = QHBoxLayout()
            wrapper.setContentsMargins(0, 0, 0, 0)
            
            grid = QGridLayout()
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0)
            btns = []
            
            row, col = 0, 0
            max_cols = 5
            
            for item in items:
                btn = QPushButton()
                btn.setFixedSize(38, 28)
                btn.setToolTip(item["name"])
                btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                
                if is_pair:
                    is_selected = (target_dict.get("user_bubble_color", "").lower() == item["user"].lower() and 
                                   target_dict.get("char_bubble_color", "").lower() == item["char"].lower())
                    btn.setStyleSheet(swatch_style_pair(item["user"], item["char"], is_selected))
                else:
                    is_selected = (target_dict.get(key, "").lower() == item["color"].lower())
                    btn.setStyleSheet(swatch_style_single(item["color"], is_selected))
                
                name_lbl = QLabel(item["name"])
                name_lbl.setFont(get_font())
                name_lbl.setStyleSheet("color: #666; font-size: 9px; background: transparent; border: none;")
                name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                
                v_box = QVBoxLayout()
                v_box.setSpacing(2)
                v_box.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
                v_box.addWidget(name_lbl)
                
                grid.addLayout(v_box, row, col)
                btns.append((btn, item))
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            def make_click(b, it, all_btns):
                def click(_):
                    for ob, oi in all_btns:
                        if is_pair:
                            ob.setStyleSheet(swatch_style_pair(oi["user"], oi["char"], selected=(ob is b)))
                        else:
                            ob.setStyleSheet(swatch_style_single(oi["color"], selected=(ob is b)))
                    
                    if is_pair:
                        target_dict["user_bubble_color"] = it["user"]
                        target_dict["char_bubble_color"] = it["char"]
                        target_dict["text_color"] = it["text"]
                        target_dict["quote_color"] = it["quote"]
                        target_dict["italic_color"] = it["italic"]
                    else:
                        target_dict[key] = it["color"]
                    apply_fn()
                return click

            for btn, item in btns:
                btn.clicked.connect(make_click(btn, item, btns))

            custom_btn = QPushButton("＋")
            custom_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            custom_btn.setFixedSize(38, 28)
            custom_btn.setToolTip(tr("appearance_tooltip_custom", "Custom Color"))
            custom_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            custom_btn.setFont(get_font())
            custom_btn.setStyleSheet("""
                QToolTip {
                    background-color: rgba(25, 25, 30, 0.95);
                    color: #E0E0E0;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: 500;
                }
                QPushButton { background: #232323; color: #777; border-radius: 8px; border: 1px dashed #444; font-size: 16px; }
                QPushButton:hover { background: #2c2c2c; color: #aaa; border: 1px dashed #666; }
            """)
            custom_name = QLabel(tr("appearance_lbl_custom", "Custom"))
            custom_name.setFont(get_font())
            custom_name.setStyleSheet("color: #666; font-size: 9px; background: transparent; border: none;")
            custom_name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            
            c_v_box = QVBoxLayout()
            c_v_box.setSpacing(2)
            c_v_box.addWidget(custom_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            c_v_box.addWidget(custom_name)
            
            grid.addLayout(c_v_box, row, col)

            def custom_pick(_):
                if is_pair:
                    c = QColorDialog.getColor(QColor(target_dict["user_bubble_color"]), None, tr("appearance_dlg_user_bubble", "User Bubble Color"))
                    if c.isValid(): target_dict["user_bubble_color"] = c.name()
                    c2 = QColorDialog.getColor(QColor(target_dict["char_bubble_color"]), None, tr("appearance_dlg_char_bubble", "Character Bubble Color"))
                    if c2.isValid(): target_dict["char_bubble_color"] = c2.name()
                else:
                    c = QColorDialog.getColor(QColor(target_dict.get(key, "#ffffff")), None, tr("appearance_dlg_pick_color", "Pick Color"))
                    if c.isValid(): target_dict[key] = c.name()
                apply_fn()

            custom_btn.clicked.connect(custom_pick)
            
            wrapper.addLayout(grid)
            wrapper.addStretch()

            return wrapper

        def create_slider_row(label_text, key, lo, hi, suffix, target_dict, apply_fn):
            col = QVBoxLayout()
            col.setSpacing(5)
            
            top = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFont(get_font())
            lbl.setStyleSheet(PARAM_LBL_STYLE)
            
            val_lbl = QLabel(f"{target_dict.get(key, lo)}{suffix}")
            val_lbl.setFont(get_font())
            val_lbl.setStyleSheet("color: #888; font-size: 12px; background: transparent; border: none;")
            
            top.addWidget(lbl)
            top.addStretch()
            top.addWidget(val_lbl)
            
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(target_dict.get(key, lo))
            sl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            sl.setStyleSheet("""
                QSlider::groove:horizontal { height: 4px; background: #333; border-radius: 2px; }
                QSlider::handle:horizontal { background: #E0E0E0; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
                QSlider::handle:horizontal:hover { background: #FFFFFF; }
                QSlider::sub-page:horizontal { background: #666; border-radius: 2px; }
            """)
            
            def on_ch(v, k=key, vl=val_lbl, sf=suffix):
                target_dict[k] = v
                vl.setText(f"{v}{sf}")
                apply_fn()
                
            sl.valueChanged.connect(on_ch)
            col.addLayout(top)
            col.addWidget(sl)
            return col

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setStyleSheet("""
            QScrollArea { background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                padding-top: 18px;
                padding-bottom: 18px;
                margin: 0px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 30px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {
                background: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        left_scroll.setFixedWidth(360)

        left_content = QWidget()
        left_content.setStyleSheet("background: transparent;")
        LL = QVBoxLayout(left_content)
        LL.setContentsMargins(15, 15, 10, 15)

        chat_settings_card = QFrame()
        chat_settings_card.setStyleSheet(CARD_STYLE)
        CS = QVBoxLayout(chat_settings_card)
        CS.setContentsMargins(20, 20, 20, 20)
        CS.setSpacing(20)

        def update_chat_prev():
            self.apply_chat_appearance_to_all(s)
            update_preview()

        CS.addWidget(create_section_lbl(tr("appearance_header_theme", "Theme")))
        CS.addLayout(create_swatch_grid(FULL_PRESETS, None, s, update_chat_prev, is_pair=True))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(tr("appearance_header_text_color", "Text Color")))
        CS.addLayout(create_swatch_grid(TEXT_COLORS, "text_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(tr("appearance_header_quotes", "Quotes")))
        CS.addLayout(create_swatch_grid(QUOTE_COLORS, "quote_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(tr("appearance_header_italic", "Cursive")))
        CS.addLayout(create_swatch_grid(ITALIC_COLORS, "italic_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addLayout(create_slider_row(tr("appearance_lbl_corner_radius", "Corner Radius"), "border_radius", 0, 24, "px", s, update_chat_prev))
        CS.addLayout(create_slider_row(tr("appearance_lbl_bubble_opacity", "Bubble Opacity"), "bubble_opacity", 10, 100, "%", s, update_chat_prev))
        
        fs_row = QHBoxLayout()
        fs_lbl = QLabel(tr("appearance_lbl_font_size", "Font Size"))
        fs_lbl.setFont(get_font())
        fs_lbl.setStyleSheet(PARAM_LBL_STYLE)
        spin = QSpinBox()
        spin.setRange(8, 48)
        spin.setValue(s["font_size"])
        spin.setFixedWidth(65)
        spin.setFixedHeight(28)
        spin.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        spin.setFont(get_font())
        spin.setStyleSheet("""
            QSpinBox { background: #2A2A2A; color: #E0E0E0; border: 1px solid #3A3A3A;
                        border-radius: 6px; padding: 0px 8px; font-size: 13px; font-weight: bold;}
            QSpinBox::up-button, QSpinBox::down-button { width: 0px; }
        """)
        def on_fs(v):
            s["font_size"] = v
            update_chat_prev()
        spin.valueChanged.connect(on_fs)
        fs_row.addWidget(fs_lbl)
        fs_row.addStretch()
        fs_row.addWidget(spin)
        CS.addLayout(fs_row)

        CS.addWidget(create_h_sep())

        chat_btn_row = QHBoxLayout()
        btn_reset_chat = QPushButton(tr("appearance_btn_reset", "Reset"))
        btn_reset_chat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_reset_chat.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_reset_chat.setFont(get_font())
        btn_reset_chat.setStyleSheet("""
            QPushButton { background: transparent; color: #888; border: 1px solid #333;
                          border-radius: 8px; padding: 8px 16px; font-size: 12px; font-weight: bold;}
            QPushButton:hover { background: #222; color: #AAA; }
        """)
        btn_save_chat = QPushButton(tr("appearance_btn_save", "Save"))
        btn_save_chat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn_save_chat.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_save_chat.setFont(get_font())
        btn_save_chat.setStyleSheet("""
            QPushButton { background: #333; color: #E0E0E0; border: 1px solid #444;
                          border-radius: 8px; padding: 8px 16px; font-size: 12px; font-weight: bold;}
            QPushButton:hover { background: #444; color: #FFF; }
            QPushButton:pressed { background: #222; }
        """)

        def on_reset_chat():
            self.configuration_settings.update_main_setting("chat_appearance", {})
            
            idx = self.ui.tabWidget_options.indexOf(tab)
            self.ui.tabWidget_options.removeWidget(tab)
            
            menu_item = self.ui.options_menu.takeItem(idx)
            del menu_item

            self.setup_appearance_tab()
            
            self.ui.options_menu.setCurrentRow(idx)

        def on_save_chat():
            self.configuration_settings.update_main_setting("chat_appearance", dict(s))
            
        btn_reset_chat.clicked.connect(on_reset_chat)
        btn_save_chat.clicked.connect(on_save_chat)
        
        chat_btn_row.addWidget(btn_reset_chat)
        chat_btn_row.addStretch()
        chat_btn_row.addWidget(btn_save_chat)
        CS.addLayout(chat_btn_row)

        LL.addWidget(chat_settings_card)
        LL.addStretch()
        left_scroll.setWidget(left_content)
        main_layout.addWidget(left_scroll)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("""
            QScrollArea { background: transparent; padding-right: 5px; }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                padding-top: 18px;
                padding-bottom: 18px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 30px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover,
            QScrollBar::handle:vertical:pressed {
                background: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        right_content = QWidget()
        right_content.setStyleSheet("background: transparent;")
        RL = QVBoxLayout(right_content)
        RL.setContentsMargins(20, 15, 20, 15)
        RL.setSpacing(20)

        preview_lbl = create_section_lbl(tr("appearance_header_preview", "Preview"))
        preview_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(preview_lbl)

        preview_card = QFrame()
        preview_card.setStyleSheet(CARD_STYLE)
        preview_card.setMinimumHeight(200) 
        PV = QVBoxLayout(preview_card)
        PV.setContentsMargins(20, 20, 20, 20)
        PV.setSpacing(15)

        char_preview = QLabel()
        char_preview.setWordWrap(True)
        char_preview.setTextFormat(Qt.TextFormat.RichText)
        char_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        user_preview = QLabel()
        user_preview.setWordWrap(True)
        user_preview.setTextFormat(Qt.TextFormat.RichText)
        user_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        char_row = QHBoxLayout()
        char_row.addWidget(char_preview)
        char_row.addStretch()

        user_row = QHBoxLayout()
        user_row.addStretch()
        user_row.addWidget(user_preview)

        PV.addLayout(char_row)
        PV.addLayout(user_row)
        PV.addStretch()
        RL.addWidget(preview_card)

        def update_preview():
            qc  = s["quote_color"]
            ic  = s["italic_color"]
            cbg = s["code_bg_color"]
            tc  = s["text_color"]
            fs  = s["font_size"]
            r   = s["border_radius"]
            op  = s["bubble_opacity"]
            char_bg = self._hex_to_rgba(s["char_bubble_color"], op)
            user_bg = self._hex_to_rgba(s["user_bubble_color"], op)

            fam = get_font().family()

            char_html = (
                f'<span style="color:{tc}; font-size:{fs}px; font-family:\'{fam}\';">'
                f'<i><span style="color:{ic};">{tr("appearance_preview_text_1", "She glances at you,")}</span></i> '
                f'{tr("appearance_preview_text_2", "eyes narrowing slowly.")} '
                f'<span style="color:{qc};">&ldquo;{tr("appearance_preview_text_3", "So... you remember nothing?")}&rdquo;</span><br><br>'
                f'<code style="background:{cbg}; color:#c7c7c7; border-radius:4px; padding:2px 6px; font-size:{max(10, fs-2)}px; font-family:\'Consolas\';">status: unknown</code>'
                f'</span>'
            )
            user_html = f'<span style="color:{tc}; font-size:{fs}px; font-family:\'{fam}\';">{tr("appearance_preview_text_4", "I remember enough.")}</span>'

            char_preview.setText(char_html)
            char_preview.setStyleSheet(f"""
                QLabel {{
                    background-color: {char_bg};
                    border-top-right-radius: {r}px;
                    border-bottom-right-radius: {r}px;
                    border-top-left-radius: {r}px;
                    border-bottom-left-radius: 0px;
                    padding: 14px; margin: 2px;
                }}
            """)
            user_preview.setText(user_html)
            user_preview.setStyleSheet(f"""
                QLabel {{
                    background-color: {user_bg};
                    border-top-left-radius: {r}px;
                    border-bottom-left-radius: {r}px;
                    border-top-right-radius: {r}px;
                    border-bottom-right-radius: 0px;
                    padding: 14px; margin: 2px;
                }}
            """)

        theme_lbl = create_section_lbl(tr("appearance_header_window_theme", "Window Theme"))
        theme_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(theme_lbl)

        theme_card = QFrame()
        theme_card.setStyleSheet(CARD_STYLE)
        TH = QVBoxLayout(theme_card)
        TH.setContentsMargins(20, 20, 20, 20)

        u = self.get_ui_appearance()
        wt = self.get_window_theme()

        WINDOW_THEMES = [
            # --- NEUTRAL & DARK ---
            {
                "name": tr("appearance_wtheme_default", "Default"),
                "bg_primary": "27,27,27", "bg_secondary": "22,22,22", "border_color": "50,50,55",
                "sidebar_accent": "#A0A0A0", "sidebar_hover": "#1B1B1B", "sidebar_text": "#D2D2D2"
            },
            {
                "name": tr("appearance_wtheme_obsidian", "Obsidian"),
                "bg_primary": "18,18,18", "bg_secondary": "10,10,10", "border_color": "35,35,35",
                "sidebar_accent": "#FFFFFF", "sidebar_hover": "#252525", "sidebar_text": "#E0E0E0"
            },
            {
                "name": tr("appearance_wtheme_graphite", "Graphite"),
                "bg_primary": "30,30,30", "bg_secondary": "37,37,38", "border_color": "55,55,55",
                "sidebar_accent": "#569CD6", "sidebar_hover": "#2D2D2D", "sidebar_text": "#CCCCCC"
            },

            # --- COOL & BLUE ---
            {
                "name": tr("appearance_wtheme_nord", "Nordic"),
                "bg_primary": "46,52,64", "bg_secondary": "36,41,51", "border_color": "59,66,82",
                "sidebar_accent": "#88C0D0", "sidebar_hover": "#434C5E", "sidebar_text": "#D8DEE9"
            },
            {
                "name": tr("appearance_wtheme_oceanic", "Oceanic"),
                "bg_primary": "15,23,42", "bg_secondary": "10,15,30", "border_color": "30,41,59",
                "sidebar_accent": "#38BDF8", "sidebar_hover": "#1E293B", "sidebar_text": "#E2E8F0"
            },
            {
                "name": tr("appearance_wtheme_midnight", "Midnight"),
                "bg_primary": "16,20,30", "bg_secondary": "12,16,24", "border_color": "30,38,55",
                "sidebar_accent": "#818CF8", "sidebar_hover": "#1F2937", "sidebar_text": "#C7D2FE"
            },

            # --- PURPLE & PINK ---
            {
                "name": tr("appearance_wtheme_synthwave", "Synthwave"),
                "bg_primary": "36,27,47", "bg_secondary": "25,18,35", "border_color": "60,40,70",
                "sidebar_accent": "#F472B6", "sidebar_hover": "#453055", "sidebar_text": "#E9D5FF"
            },
            {
                "name": tr("appearance_wtheme_royal", "Royal"),
                "bg_primary": "28,20,40", "bg_secondary": "20,15,30", "border_color": "45,35,60",
                "sidebar_accent": "#A78BFA", "sidebar_hover": "#352545", "sidebar_text": "#E5E7EB"
            },
            {
                "name": tr("appearance_wtheme_rose", "Rose"),
                "bg_primary": "35,25,30", "bg_secondary": "25,18,22", "border_color": "55,35,45",
                "sidebar_accent": "#FB7185", "sidebar_hover": "#40202A", "sidebar_text": "#FFE4E6"
            },

            # --- NATURE & WARM ---
            {
                "name": tr("appearance_wtheme_forest", "Forest"),
                "bg_primary": "18,28,22", "bg_secondary": "12,20,15", "border_color": "30,50,38",
                "sidebar_accent": "#4ADE80", "sidebar_hover": "#142518", "sidebar_text": "#DCFCE7"
            },
            {
                "name": tr("appearance_wtheme_coffee", "Coffee"),
                "bg_primary": "28,24,22", "bg_secondary": "22,18,16", "border_color": "50,42,38",
                "sidebar_accent": "#D7CCC8", "sidebar_hover": "#352A25", "sidebar_text": "#EFEBE9"
            },
            {
                "name": tr("appearance_wtheme_amber", "Amber"),
                "bg_primary": "30,25,20", "bg_secondary": "22,18,14", "border_color": "55,40,30",
                "sidebar_accent": "#FBBF24", "sidebar_hover": "#33251A", "sidebar_text": "#FEF3C7"
            },
            
            # --- SPECIAL ---
            {
                "name": tr("appearance_wtheme_slate", "Slate"),
                "bg_primary": "22,28,36", "bg_secondary": "15,20,28", "border_color": "44,56,72",
                "sidebar_accent": "#60A5FA", "sidebar_hover": "#1E293B", "sidebar_text": "#F1F5F9"
            },
            {
                "name": tr("appearance_wtheme_dracula", "Vampire"),
                "bg_primary": "40,42,54", "bg_secondary": "28,30,40", "border_color": "68,71,90",
                "sidebar_accent": "#BD93F9", "sidebar_hover": "#343746", "sidebar_text": "#F8F8F2"
            }
        ]

        def ui_update_all():
            self.apply_window_theme(wt)
            self.apply_gui_theme(wt["theme_name"])
            self.apply_sidebar_styles(u, wt)

        theme_wrapper = QHBoxLayout()
        theme_wrapper.setContentsMargins(0, 0, 0, 0)
        
        theme_grid = QGridLayout()
        theme_grid.setSpacing(10)
        theme_grid.setContentsMargins(0, 0, 0, 0)
        theme_btns = []
        row, col = 0, 0
        
        MAX_COLS = 7 
        
        for theme in WINDOW_THEMES:
            btn = QPushButton()
            btn.setFixedSize(46, 32)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setToolTip(theme["name"])
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            bp = theme["bg_primary"]
            bs = theme["bg_secondary"]
            r1, g1, b1 = [int(x) for x in bp.split(",")]
            r2, g2, b2 = [int(x) for x in bs.split(",")]
            
            is_sel = (wt.get("theme_name", "default") == theme["name"].lower().replace(" ", "_"))
            border = "#FFFFFF" if is_sel else "transparent"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgb({r1},{g1},{b1}), stop:1 rgb({r2},{g2},{b2}));
                    border-radius: 6px; border: 2px solid {border};
                }}
                QPushButton:hover {{ border: 2px solid #999; }}
                QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 12px; font-weight: 500; }}
            """)
            
            name_lbl = QLabel(theme["name"])
            name_lbl.setFont(get_font())
            name_lbl.setStyleSheet("color:#666; font-size:9px; background:transparent; border:none;")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            
            v_box = QVBoxLayout()
            v_box.setSpacing(4)
            v_box.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            v_box.addWidget(name_lbl)
            
            theme_grid.addLayout(v_box, row, col)
            theme_btns.append((btn, theme))
            
            col += 1
            if col >= MAX_COLS:
                col = 0
                row += 1

        def make_theme_click(b, th, all_btns):
            def click(_):
                for ob, ot in all_btns:
                    bp2 = ot["bg_primary"]; bs2 = ot["bg_secondary"]
                    r1,g1,b1 = [int(x) for x in bp2.split(",")]
                    r2,g2,b2 = [int(x) for x in bs2.split(",")]
                    sel = ob is b
                    brd = "#888" if sel else "transparent"
                    ob.setStyleSheet(f"""
                        QPushButton {{
                            background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgb({r1},{g1},{b1}), stop:1 rgb({r2},{g2},{b2}));
                            border-radius: 8px; border: 2px solid {brd};
                        }}
                        QPushButton:hover {{ border: 2px solid #555; }}
                    """)
                
                wt.update(th)
                wt["theme_name"] = th["name"].lower().replace(" ", "_")

                u["sidebar_accent"] = th.get("sidebar_accent", "#A0A0A0")
                u["sidebar_hover"]  = th.get("sidebar_hover", "#1B1B1B")
                u["sidebar_text"]   = th.get("sidebar_text", "#D2D2D2")

                ui_update_all()

                self.configuration_settings.update_main_setting("window_theme", dict(wt))
                self.configuration_settings.update_main_setting("ui_appearance", dict(u))
                
            return click

        for btn, theme in theme_btns:
            btn.clicked.connect(make_theme_click(btn, theme, theme_btns))

        theme_wrapper.addLayout(theme_grid)
        theme_wrapper.addStretch()
        TH.addLayout(theme_wrapper)
        RL.addWidget(theme_card)

        ui_lbl = create_section_lbl(tr("appearance_header_ui", "Interface (Sidebar and Buttons)"))
        ui_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(ui_lbl)

        ui_card = QFrame()
        ui_card.setStyleSheet(CARD_STYLE)
        UI = QVBoxLayout(ui_card)
        UI.setContentsMargins(20, 20, 20, 20)
        UI.setSpacing(20)
        
        def ui_update_only_buttons():
            self.apply_sidebar_styles(u, wt)
            self.configuration_settings.update_main_setting("ui_appearance", dict(u))

        UI_ACCENT_COLORS = [
            {"name": tr_col("Gray", "gray"), "color": "#A0A0A0"}, {"name": tr_col("Blue", "blue"), "color": "#5090C8"}, 
            {"name": tr_col("Lavender", "lavender"), "color": "#9080C8"}, {"name": tr_col("Green", "green"), "color": "#70B870"}, 
            {"name": tr_col("Amber", "amber"), "color": "#E8A040"}, {"name": tr_col("Rose", "rose"), "color": "#C87090"}
        ]
        UI_HOVER_COLORS = [
            {"name": tr_col("Dark", "dark"), "color": "#1B1B1B"}, {"name": tr_col("Darker", "darker"), "color": "#141414"}, 
            {"name": tr_col("Slate", "slate"), "color": "#1A202A"}, {"name": tr_col("Forest", "forest"), "color": "#162018"}, 
            {"name": tr_col("Warm", "warm"), "color": "#201A14"}
        ]
        NAV_TEXT_COLORS = [
            {"name": tr_col("Standard", "standard"), "color": "#D2D2D2"}, {"name": tr_col("Bright", "bright"), "color": "#F0F0F0"}, 
            {"name": tr_col("Dimmed", "dimmed"), "color": "#A0A0A0"}, {"name": tr_col("Warm", "warm"), "color": "#D8C8B0"}, 
            {"name": tr_col("Cool", "cool"), "color": "#A8B8C8"}, {"name": tr_col("Accent", "accent"), "color": "#B0C0D8"}
        ]

        UI.addWidget(create_section_lbl(tr("appearance_header_ui_accent", "Accent (The Active Menu Item)")))
        UI.addLayout(create_swatch_grid(UI_ACCENT_COLORS, "sidebar_accent", u, ui_update_only_buttons))
        UI.addWidget(create_h_sep())

        UI.addWidget(create_section_lbl(tr("appearance_header_ui_hover", "Hover (Active Button Background)")))
        UI.addLayout(create_swatch_grid(UI_HOVER_COLORS, "sidebar_hover", u, ui_update_only_buttons))
        UI.addWidget(create_h_sep())

        UI.addWidget(create_section_lbl(tr("appearance_header_ui_text", "Button Text Color")))
        UI.addLayout(create_swatch_grid(NAV_TEXT_COLORS, "sidebar_text", u, ui_update_only_buttons))

        RL.addWidget(ui_card)
        RL.addStretch()
        
        right_scroll.setWidget(right_content)
        main_layout.addWidget(right_scroll)

        update_preview()

        self.ui.tabWidget_options.addWidget(tab)

        item = QtWidgets.QListWidgetItem(tr("appearance_tab_name", "Appearance"))
        self.ui.options_menu.addItem(item)

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
            "create_character_page_2", "charactersgateway_page",
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

            QScrollArea#scrollArea_chat {{
                background-color: rgb({bg});
                border: none;
                padding-left: 5px;
                padding-right: 5px;
                padding-bottom: 5px;
                margin-top: 5px;
                border-radius: 10px;
            }}

            QScrollBar:vertical {{
                background-color: rgb({bg});
                width: 12px;
                margin: 15px 0px 15px 0px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgb({bg2});
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
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}

            QScrollArea#scrollArea_characters_list QScrollBar:vertical,
            QScrollArea#scrollArea_characters_list QScrollBar:horizontal,
            QScrollArea#scrollArea_chat QScrollBar:vertical {{
                width: 0px;
                height: 0px;
                background: transparent;
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
            self.ui.pushButton_rp_editors,
            self.ui.pushButton_create_character,
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

    def show_confirmation_dialog(self, title, message):
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        msg_box.setWindowTitle(title)
        
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                font-family: "Inter Tight Medium";
                font-size: 14px;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px 16px;
                min-width: 80px;
                font-family: "Inter Tight SemiBold";
            }
            QPushButton:hover {
                background-color: #383838;
                border: 1px solid #555555;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        font = QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        msg_box.setFont(font)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        return msg_box.exec() == QMessageBox.StandardButton.Yes
    
    def show_toast(self, message, toast_type="success", duration=3000):
        if hasattr(self, "current_toast") and self.current_toast:
            try:
                self.current_toast.hide_toast()
            except RuntimeError:
                pass
            
        self.current_toast = ToastNotification(self.main_window, message, toast_type, duration)
        self.current_toast.show_toast()

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

    def update_lip_sync(self, value):
        if not self.current_active_character:
            return

        if not hasattr(self, 'expression_widget') or not self.expression_widget or not self.expression_widget.isVisible():
            return
            
        config = self.configuration_characters.load_configuration()
        if self.current_active_character not in config["character_list"]:
            return
            
        mode = config["character_list"][self.current_active_character]["current_sow_system_mode"]

        # --- LIVE2D ---
        if mode == "Live2D Model":
            if hasattr(self, 'live2d_widget') and self.live2d_widget and self.live2d_widget.isVisible():
                if self.live2d_widget.live2d_model:
                    self.live2d_widget.live2d_model.SetParameterValue("ParamMouthOpenY", value)
                    
        # --- VRM ---
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
        self.ui.textEdit_write_user_message.setMinimumSize(QtCore.QSize(0, 40))
        self.ui.textEdit_write_user_message.setMaximumSize(QtCore.QSize(610, 16777215))
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
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle(self.translations.get("about_program_title", "About Soul of Waifu"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        dialog.resize(900, 600)

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dialog.setFont(font)

        dialog.setStyleSheet("""
            QFrame#MainFrame {
                background-color: rgba(22, 22, 24, 240);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
            }
            QLabel {
                color: rgba(255, 255, 255, 0.85);
                border: none;
                background: transparent;
                font-size: 11pt;
            }
            QLabel#title_label {
                font-family: 'Inter Tight ExtraBold';
                font-size: 28pt;
                color: #ffffff;
                padding-bottom: 5px;
            }
            QLabel#version_label {
                font-size: 10pt;
                color: rgba(255, 255, 255, 0.9);
                font-weight: bold;
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 4px 12px;
                border-radius: 12px;
            }
            a {
                color: #4da6ff;
                text-decoration: none;
                font-weight: bold;
            }
            a:hover {
                color: #80bfff;
                text-decoration: underline;
            }
            
            QScrollArea { background: transparent; border: none; }
            QWidget { background: transparent; }
            
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,0.1);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2); 
                min-height: 30px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 10px 24px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.15);
                transform: scale(0.98);
            }

            QPushButton#donate_btn {
                background-color: rgba(255, 107, 107, 0.15);
                color: #ff6b6b;
                border: 1px solid rgba(255, 107, 107, 0.4);
            }
            QPushButton#donate_btn:hover {
                background-color: rgba(255, 107, 107, 0.25);
                border: 1px solid rgba(255, 107, 107, 0.6);
                color: #ff8585;
            }
            QPushButton#donate_btn:pressed {
                background-color: rgba(255, 107, 107, 0.35);
            }
            
            QLabel#footer_text {
                font-size: 10pt;
                color: rgba(255, 255, 255, 0.4);
            }
            QLabel#footer_text a { color: rgba(255, 255, 255, 0.6); }
            QLabel#footer_text a:hover { color: #ffffff; }
        """)

        layout_dialog = QtWidgets.QVBoxLayout(dialog)
        layout_dialog.setContentsMargins(15, 15, 15, 15)

        main_frame = QtWidgets.QFrame()
        main_frame.setObjectName("MainFrame")
        
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        main_frame.setGraphicsEffect(shadow)

        layout_frame = QtWidgets.QHBoxLayout(main_frame)
        layout_frame.setContentsMargins(40, 50, 40, 40)
        layout_frame.setSpacing(40)

        left_layout = QtWidgets.QVBoxLayout()
        
        logo_label = QtWidgets.QLabel()
        logo_pixmap = QtGui.QPixmap("app/gui/icons/logotype.ico")
        
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            
            logo_shadow = QtWidgets.QGraphicsDropShadowEffect()
            logo_shadow.setBlurRadius(30)
            logo_shadow.setColor(QtGui.QColor(0, 0, 0, 120))
            logo_shadow.setOffset(0, 5)
            logo_label.setGraphicsEffect(logo_shadow)
        else:
            logo_label.setText("SoW") 
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet("font-size: 40pt; color: rgba(255,255,255,0.2); border: 2px dashed rgba(255,255,255,0.1); border-radius: 30px;")
            logo_label.setFixedSize(200, 200)
            
        logo_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        left_layout.addWidget(logo_label)
        left_layout.addStretch()
        
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setSpacing(20)

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(15)
        
        title_label = QtWidgets.QLabel("Soul of Waifu")
        title_label.setObjectName("title_label")
        
        raw_ver = "v2.3.1"
        version_badge = QtWidgets.QLabel(raw_ver)
        version_badge.setObjectName("version_label")
        version_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_badge.setFixedHeight(28)

        header_layout.addWidget(title_label)
        header_layout.addWidget(version_badge)
        header_layout.addStretch()
        
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 10, 20, 10)
        content_layout.setSpacing(25)

        desc_text = self.translations.get(
            "about_program_description",
            "<p style='line-height: 1.6; font-size: 16px;'>"
            "<b>Soul of Waifu</b> is your ultimate tool for bringing AI-driven characters to life. "
            "With support for advanced APIs from leading AI platforms and local LLMs, you can customize "
            "every aspect of your character.</p>"
            "<p style='line-height: 1.6; font-size: 16px;'>"
            "Connect a Live2D model, use high-quality TTS/STT, and enjoy Speech-To-Speech mode "
            "to truly talk to your character as if they were right there with you.</p>"
        )
        
        sub_desc_text = self.translations.get(
            "about_program_sub_description",
            "<p style='line-height: 1.6; font-size: 15px; color: rgba(255,255,255,0.6);'>"
            "Join our vibrant community on <a href='https://discord.gg/6vFtQGVfxM' style='color: #7289da;'>Discord</a> to share ideas "
            "and shape the future of Soul of Waifu.</p>"
        )

        full_desc = f"{desc_text}<br>{sub_desc_text}"
        
        description_label = QtWidgets.QLabel(full_desc)
        description_label.setObjectName("desc_label")
        description_label.setWordWrap(True)
        description_label.setTextFormat(Qt.TextFormat.RichText)
        description_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        description_label.setOpenExternalLinks(True)

        content_layout.addWidget(description_label)
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setSpacing(15)
        
        developed_by = self.translations.get("creator_label", "Developed by")
        author_label = QtWidgets.QLabel(f"{developed_by} <a href='https://github.com/jofizcd'>jofizcd</a>")
        author_label.setObjectName("footer_text")
        author_label.setOpenExternalLinks(True)

        donate_btn = QtWidgets.QPushButton(self.translations.get("support_btn", "❤ Support"))
        donate_btn.setObjectName("donate_btn")
        donate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        donate_btn.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl("https://boosty.to/jofizcd/")))
        
        close_btn = QtWidgets.QPushButton(self.translations.get("update_available_close", "Close"))
        close_btn.setObjectName("close_btn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(dialog.accept)

        footer_layout.addWidget(author_label)
        footer_layout.addStretch()
        footer_layout.addWidget(donate_btn)
        footer_layout.addWidget(close_btn)

        right_layout.addLayout(header_layout)
        right_layout.addWidget(scroll_area)
        right_layout.addLayout(footer_layout)

        layout_frame.addLayout(left_layout, 1)
        layout_frame.addLayout(right_layout, 2)

        layout_dialog.addWidget(main_frame)

        dialog.exec()

    def on_pushButton_main_clicked(self):
        asyncio.create_task(self.set_main_tab())

    def on_pushButton_options_clicked(self):
        self.ui.pushButton_options.setChecked(True)
        self.ui.stackedWidget.setCurrentIndex(5)

    def on_pushButton_models_hub_clicked(self):
        self.ui.pushButton_models_hub.setChecked(True)
        self.ui.stackedWidget.setCurrentIndex(7)
        QApplication.processEvents()
        self.show_my_models()

    def on_pushButton_launch_server_clicked(self):
        asyncio.create_task(self.local_ai_client.ensure_server_running())

    def on_youtube(self):
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/@jofizcd"))

    def on_discord(self):
        QDesktopServices.openUrl(QUrl("https://discord.gg/6vFtQGVfxM"))

    def on_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/jofizcd/Soul-of-Waifu"))

    def open_personas_editor(self):
        """
        Opens a dialog for creating, editing, and managing user personas.
        """
        personas_data = self.configuration_settings.get_user_data("personas")
        current_default_persona = self.configuration_settings.get_user_data("default_persona")
        
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("personas_editor_title", "Personas Editor"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(850, 550)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E; 
            }
            QListWidget {
                background-color: #252525;
                border: none;
                border-right: 1px solid #333;
                outline: none;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #2e2e2e;
            }
            QListWidget::item:selected {
                background-color: #303030;
                border-left: 3px solid rgb(160, 160, 160);
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }

            QLabel {
                color: #cfcfcf;
                font-family: "Inter Tight";
                font-size: 14px;
            }
            QLabel#header_label {
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
            }
            QLineEdit, QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 8px;
                font-family: "Inter Tight";
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #444;
                background-color: #303030;
            }

            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-family: "Inter Tight Medium";
            }
            QPushButton#primary_btn {
                background-color: #2D2D2D;
                color: white;
                border: 1px solid #3e3e3e;
            }
            QPushButton#primary_btn:hover {
                background-color: #333333;
            }
            QPushButton#secondary_btn {
                background-color: transparent;
                color: #aaaaaa;
                border: 1px solid #3e3e3e;
            }
            QPushButton#secondary_btn:hover {
                background-color: #333333;
                color: white;
            }
            QPushButton#delete_btn {
                background-color: transparent;
                color: #ff6b6b;
                border: 1px solid #5a3e3e;
            }
            QPushButton#delete_btn:hover {
                background-color: #4a2525;
                border: 1px solid #ff6b6b;
                color: white;
            }
            QPushButton#upload_btn {
                background-color: #333;
                color: white;
                border: 1px dashed #555;
                font-size: 11px;
            }
            QPushButton#upload_btn:hover {
                background-color: #444;
                border: 1px dashed #777;
            }
        """)

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        list_container = QWidget()
        list_container.setFixedWidth(260)
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        list_widget = QtWidgets.QListWidget()
        list_widget.setObjectName("listWidget_personas")
        list_layout.addWidget(list_widget)
        
        add_new_btn_list = QPushButton("+ " + self.translations.get("personas_editor_create_new", "Create New Persona"))
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        add_new_btn_list.setFont(font)
        add_new_btn_list.setStyleSheet("""
            QPushButton {
                background-color: #252525;
                color: #888;
                border: none;
                border-top: 1px solid #333;
                text-align: left;
                padding: 15px;
            }
            QPushButton:hover { background-color: #2a2a2a; color: white; }
        """)
        add_new_btn_list.setCursor(Qt.CursorShape.PointingHandCursor)
        list_layout.addWidget(add_new_btn_list)

        main_layout.addWidget(list_container)

        editor_area = QWidget()
        editor_area.setObjectName("editor_area")
        
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(30, 30, 30, 30)
        editor_layout.setSpacing(15)
        editor_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        header_layout = QHBoxLayout()
        header_label = QLabel(self.translations.get("personas_editor_title", "Personas Editor"))
        header_label.setObjectName("header_label")
        
        default_status_label = QLabel(self.translations.get("personas_editor_default_persona", "(Default Persona)"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        default_status_label.setFont(font)
        default_status_label.setStyleSheet("color: #4CAF50; font-size: 12px; font-weight: bold;")
        default_status_label.setVisible(False)

        header_layout.addWidget(header_label)
        header_layout.addWidget(default_status_label)
        header_layout.addStretch()
        editor_layout.addLayout(header_layout)

        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(20)
        
        avatar_label = QLabel()
        avatar_label.setFixedSize(100, 100)
        avatar_label.setStyleSheet("""
            border-radius: 50px; 
            border: 2px solid #3d3d3d; 
            background-color: #252525;
        """)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        upload_btn = QPushButton(self.translations.get("personas_editor_choose_avatar", "Choose Image"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(7)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        upload_btn.setFont(font)
        upload_btn.setObjectName("upload_btn")
        upload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        upload_btn.setFixedSize(160, 30)

        avatar_info_layout = QVBoxLayout()
        avatar_info_layout.addWidget(upload_btn)
        avatar_info_layout.addStretch()

        avatar_row.addWidget(avatar_label)
        avatar_row.addLayout(avatar_info_layout)
        avatar_row.addStretch()
        
        editor_layout.addLayout(avatar_row)

        name_label = QLabel(self.translations.get("personas_editor_name", "Name"))
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_line_edit = QLineEdit()
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        name_line_edit.setFont(font)
        name_line_edit.setPlaceholderText(self.translations.get("personas_editor_name_placeholder", "E.g. Dark Knight"))

        desc_label = QLabel(self.translations.get("personas_editor_description", "Description"))
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        desc_label.setFont(font)
        description_text_edit = QTextEdit()
        description_text_edit.setPlaceholderText(self.translations.get("personas_editor_description_placeholder", "Describe the persona's role, tone, and backstory..."))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        description_text_edit.setFont(font)
        description_text_edit.setMinimumHeight(120)

        editor_layout.addWidget(name_label)
        editor_layout.addWidget(name_line_edit)
        editor_layout.addWidget(desc_label)
        editor_layout.addWidget(description_text_edit)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        delete_btn = QPushButton(self.translations.get("personas_editor_delete_btn", "Delete"))
        delete_btn.setObjectName("delete_btn")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        delete_btn.setFont(font)
        
        buttons_layout.addWidget(delete_btn)
        
        set_default_btn = QPushButton(self.translations.get("personas_editor_default_btn", "Set as Default"))
        set_default_btn.setObjectName("secondary_btn")
        set_default_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        set_default_btn.setFont(font)

        cancel_btn = QPushButton(self.translations.get("personas_editor_close", "Close"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        cancel_btn.setFont(font)
        cancel_btn.setObjectName("secondary_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        save_btn = QPushButton(self.translations.get("personas_editor_save", "Save Changes"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        save_btn.setFont(font)
        save_btn.setObjectName("primary_btn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons_layout.addWidget(set_default_btn)
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        
        editor_layout.addStretch()
        editor_layout.addLayout(buttons_layout)

        main_layout.addWidget(editor_area)

        editor_widgets = {
            "current_state": {"current_avatar_path": None, "mode": "add", "original_name": None},
            "name_edit": name_line_edit,
            "desc_edit": description_text_edit,
            "avatar_lbl": avatar_label
        }

        def choose_avatar():
            file_dialog = QFileDialog()
            path, _ = file_dialog.getOpenFileName(dialog, "Choose Avatar", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                pixmap = QPixmap(path)
                avatar_label.setPixmap(pixmap.scaled(70, 70, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
                mask = QPixmap(pixmap.size())
                mask.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QPainter(mask)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QtCore.Qt.GlobalColor.black)
                painter.setPen(QtCore.Qt.GlobalColor.transparent)
                painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
                painter.end()
                pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
                avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
                avatar_label.setScaledContents(True)
                avatar_label.setPixmap(pixmap)
                editor_widgets["current_state"]["current_avatar_path"] = path

        upload_btn.clicked.connect(choose_avatar)

        def refresh_personas_list():
            list_widget.clear()
            nonlocal current_default_persona
            current_default_persona = self.configuration_settings.get_user_data("default_persona")

            if personas_data:
                for name, data in personas_data.items():
                    item = QtWidgets.QListWidgetItem()

                    display_name = data.get("user_name", name)
                    if name == current_default_persona:
                        display_name += " (Default)"

                    item.setText(data.get("user_name", name))
                    item.setData(Qt.ItemDataRole.UserRole, name)
                    item.setSizeHint(QtCore.QSize(0, 50))
                    
                    av_path = data.get("user_avatar")
                    if av_path and os.path.exists(av_path):
                         icon = QtGui.QIcon(av_path)
                         item.setIcon(icon)
                    else:
                         item.setIcon(QtGui.QIcon("app/gui/icons/person.png"))
                        
                    if name == current_default_persona:
                        item.setForeground(QtGui.QBrush(QtGui.QColor("#4CAF50")))
                    
                    list_widget.addItem(item)
            
        def on_item_clicked(item):
            original_name = item.data(Qt.ItemDataRole.UserRole)
            data = personas_data.get(original_name)
            
            editor_widgets["current_state"]["mode"] = "edit"
            editor_widgets["current_state"]["original_name"] = original_name
            editor_widgets["current_state"]["current_avatar_path"] = data.get("user_avatar")
            
            header_label.setText(self.translations.get("personas_editor_title", "Edit Persona"))
            save_btn.setText(self.translations.get("personas_editor_save", "Save Changes"))
            
            name_line_edit.setText(data.get("user_name", ""))
            description_text_edit.setPlainText(data.get("user_description", ""))

            delete_btn.setVisible(True)

            nonlocal current_default_persona
            if original_name == current_default_persona:
                default_status_label.setVisible(True)
                set_default_btn.setVisible(False)
            else:
                default_status_label.setVisible(False)
                set_default_btn.setVisible(True)
            
            path = data.get("user_avatar")
            if path and os.path.exists(path):
                pixmap = QPixmap(path)
                avatar_label.setPixmap(pixmap.scaled(70, 70, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
                mask = QPixmap(pixmap.size())
                mask.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QPainter(mask)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QtCore.Qt.GlobalColor.black)
                painter.setPen(QtCore.Qt.GlobalColor.transparent)
                painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
                painter.end()
                pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
                avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
                avatar_label.setScaledContents(True)
                avatar_label.setPixmap(pixmap)
            else:
                avatar_label.clear()
                avatar_label.setText("No Img")

            editor_area.setVisible(True)

        def on_add_new_clicked():
            list_widget.clearSelection()
            editor_widgets["current_state"]["mode"] = "add"
            editor_widgets["current_state"]["original_name"] = None
            editor_widgets["current_state"]["current_avatar_path"] = None
            
            header_label.setText(self.translations.get("personas_editor_create_new", "Create New Persona"))
            save_btn.setText(self.translations.get("personas_editor_create_btn", "Create Persona"))

            delete_btn.setVisible(False)
            set_default_btn.setVisible(False)
            default_status_label.setVisible(False)
            
            name_line_edit.clear()
            description_text_edit.clear()
            avatar_label.clear()
            avatar_label.setText("No Img")
            
            editor_area.setVisible(True)
            name_line_edit.setFocus()
        
        def set_default_action():
            name = editor_widgets["current_state"]["original_name"]
            if name:
                self.configuration_settings.update_user_data("default_persona", name)
                
                nonlocal current_default_persona
                current_default_persona = name
                
                refresh_personas_list()
                
                for i in range(list_widget.count()):
                    item = list_widget.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == name:
                        list_widget.setCurrentItem(item)
                        on_item_clicked(item)
                        break
        
        def delete_action():
            name = editor_widgets["current_state"]["original_name"]
            if not name: return

            title = self.translations.get("personas_editor_confirm_delete", "Confirm Delete")
            message = self.translations.get("personas_editor_confirm_delete_text", f"Are you sure you want to delete persona '{name}'?")

            if self.show_confirmation_dialog(title, message):
                del personas_data[name]
                
                nonlocal current_default_persona
                if current_default_persona == name:
                    self.configuration_settings.update_user_data("default_persona", "None")
                    current_default_persona = "None"
                
                self.configuration_settings.update_user_data("personas", personas_data)
                
                refresh_personas_list()
                
                if list_widget.count() > 0:
                    list_widget.setCurrentRow(0)
                    on_item_clicked(list_widget.item(0))
                else:
                    on_add_new_clicked()

        def save_action():
            name = name_line_edit.text().strip()
            description = description_text_edit.toPlainText().strip()
            path = editor_widgets["current_state"]["current_avatar_path"]
            
            if not name:
                QMessageBox.warning(dialog, "Error", "Name is required")
                return

            mode = editor_widgets["current_state"]["mode"]
            
            if mode == "edit":
                orig_name = editor_widgets["current_state"]["original_name"]
                if orig_name != name:
                    if name in personas_data:
                         QMessageBox.warning(dialog, "Error", "Persona with this name already exists")
                         return
                    del personas_data[orig_name]
                    if current_default_persona == orig_name:
                        self.configuration_settings.update_user_data("default_persona", name)
                
                personas_data[name] = {
                    "user_name": name,
                    "user_description": description,
                    "user_avatar": path
                }
            else:
                if name in personas_data:
                     QMessageBox.warning(dialog, "Error", "Persona with this name already exists")
                     return
                personas_data[name] = {
                    "user_name": name,
                    "user_description": description,
                    "user_avatar": path
                }

            self.configuration_settings.update_user_data("personas", personas_data)
            refresh_personas_list()
            
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == name:
                    list_widget.setCurrentItem(item)
                    on_item_clicked(item)
                    break
            
            QMessageBox.information(dialog, "Success", "Saved successfully")

        list_widget.itemClicked.connect(on_item_clicked)
        add_new_btn_list.clicked.connect(on_add_new_clicked)
        save_btn.clicked.connect(save_action)
        cancel_btn.clicked.connect(dialog.close)
        delete_btn.clicked.connect(delete_action)
        set_default_btn.clicked.connect(set_default_action)

        refresh_personas_list()
        
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)
            on_item_clicked(list_widget.item(0))
        else:
            on_add_new_clicked()

        main_layout.addWidget(editor_area)
        dialog.exec()

    def open_system_prompt_editor(self):
        """
        Opens a dialog for creating, editing, and managing system prompts, 
        component order, and preset configurations for characters in Soul of Waifu.
        """        
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("system_prompt_editor_title", "System Prompt Editor"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(900, 745)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit, QTextEdit {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 12px;
                selection-color: #ffffff;
                selection-background-color: #3d5afe;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #555555;
                background-color: #323232;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)

        prompt_label = QLabel(self.translations.get("system_prompt_editor_system_prompt", "System prompt"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        prompt_label.setFont(font)
        main_layout.addWidget(prompt_label)

        system_prompt_edit = QTextEdit()
        system_prompt_edit.setFont(font)
        system_prompt_edit.setFixedHeight(220)
        system_prompt_edit.setAcceptRichText(False)
        system_prompt_edit.setPlaceholderText(self.translations.get("system_prompt_editor_system_prompt_edit", "Write the system prompt here"))
        main_layout.addWidget(system_prompt_edit)
        
        reorder_label = QLabel(self.translations.get("system_prompt_editor_order", "Prompt Component Order (Drag to reorder)"))
        reorder_label.setFont(font)
        reorder_label.setStyleSheet("color: #aaaaaa; margin-top: 5px;") 
        main_layout.addWidget(reorder_label)

        list_widget = QtWidgets.QListWidget()
        list_widget.setDragDropMode(QtWidgets.QListWidget.DragDropMode.InternalMove)
        list_widget.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
                padding: 8px;
                outline: none;
            }
            QListWidget::item {
                background-color: #333333;
                border: 1px solid #3f3f3f;
                border-radius: 6px;
                margin: 3px 4px;
                padding: 8px 12px;
                color: #dcdcdc;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QListWidget::item:selected {
                background-color: #454545;
                color: #ffffff;
                border: 1px solid #666666;
            }
        """)
        main_layout.addWidget(list_widget)

        main_layout.addSpacing(10)

        control_panel = QtWidgets.QFrame()
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 10px;
                border: 1px solid #333333;
            }
        """)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(10)

        preset_layout = QVBoxLayout()
        preset_layout.setSpacing(5)
        
        preset_label = QLabel(self.translations.get("system_prompt_editor_presets", "Presets"))
        preset_label.setFont(font)
        preset_label.setStyleSheet("border: none; background: transparent;")
        preset_layout.addWidget(preset_label)

        preset_combo = QtWidgets.QComboBox()
        preset_combo.setFixedHeight(40)
        preset_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        preset_layout.addWidget(preset_combo)
        
        control_layout.addLayout(preset_layout, stretch=1)

        buttons_style = """
            QPushButton {
                background-color: transparent;
                color: #aaaaaa;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: "Inter Tight Medium";
            }
            QPushButton:hover {
                background-color: #333333;
                color: white;
                border: 1px solid #666666;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """

        actions_layout = QHBoxLayout()
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignBottom) 
        
        new_preset_btn = QPushButton(self.translations.get("system_prompt_editor_new_preset", "New"))
        save_preset_button = QPushButton(self.translations.get("system_prompt_editor_save_preset", "Save"))
        delete_preset_btn = QPushButton(self.translations.get("system_prompt_editor_delete_preset", "Delete"))
        
        reset_button = QPushButton(self.translations.get("system_prompt_editor_default_btn", "Reset Default"))
        
        buttons = [new_preset_btn, save_preset_button, reset_button]
        for btn in buttons:
            btn.setFixedHeight(40)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            btn.setFont(font)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(buttons_style)
        
        delete_preset_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ff6b6b;
                border: 1px solid #5a3e3e;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: "Inter Tight Medium";
            }
            QPushButton:hover {
                background-color: #4a2525;
                border: 1px solid #ff6b6b;
                color: white;
            }                          
        """)
        delete_preset_btn.setFixedHeight(40)
        delete_preset_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        delete_preset_btn.setFont(font)
        delete_preset_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        actions_layout.addWidget(new_preset_btn)
        actions_layout.addWidget(save_preset_button)
        actions_layout.addWidget(delete_preset_btn)
        
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        line.setStyleSheet("border: 1px solid #3a3a3a; background: transparent;")
        actions_layout.addWidget(line)
        
        actions_layout.addWidget(reset_button)

        control_layout.addLayout(actions_layout)

        main_layout.addWidget(control_panel)

        def load_presets():
            saved_presets = self.configuration_settings.get_all_presets()
            return saved_presets

        def update_preset_combo():
            presets = self.configuration_settings.get_user_data("presets")
            preset_combo.clear()
            for name in presets:
                preset_combo.addItem(name)

        def apply_current_preset():
            presets = self.configuration_settings.get_user_data("presets")
            name = preset_combo.currentText()
            if name in presets:
                data = presets[name]
                system_prompt_edit.setPlainText(data["prompt"])
                list_widget.clear()
                list_widget.addItems(data["order"])

        def save_current_preset():
            presets = self.configuration_settings.get_user_data("presets")
            name = preset_combo.currentText()
            if name in presets:
                presets[name] = {
                    "prompt": system_prompt_edit.toPlainText(),
                    "order": [list_widget.item(i).text() for i in range(list_widget.count())]
                }
                self.configuration_settings.update_preset(name, presets[name])

        def reset_to_default():
            system_prompt_edit.setPlainText("You are a {{char}}, you must answer as {{char}}.")
            list_widget.clear()
            list_widget.addItems([
                "System prompt",
                "Character's information",
                "Persona information",
                "Lorebook",
                "Story Summary",
                "Author's notes"
            ])
            
        def create_new_preset():
            preset_name_text = self.translations.get("system_prompt_editor_preset_name", "Enter the preset name:")
            name, ok = QInputDialog.getText(dialog, "New preset", preset_name_text)
            if ok and name:
                preset_data = {
                    "prompt": "You are {{char}}, you must answer as {{char}}.",
                    "order": [
                        "System prompt",
                        "Character's information",
                        "Persona information",
                        "Lorebook",
                        "Story Summary",
                        "Author's notes"
                    ]
                }
                self.configuration_settings.update_preset(name, preset_data)
                update_preset_combo()
                preset_combo.setCurrentText(name)

        def delete_current_preset():
            presets = self.configuration_settings.get_user_data("presets")
            name = preset_combo.currentText()
            if name in presets:
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                msg_box.setWindowTitle(self.translations.get("system_prompt_editor_delete_preset_title", "Delete Preset"))
                msg_box.setStyleSheet("""
                    QMessageBox { background-color: #1e1e1e; color: #e0e0e0; }
                    QLabel { color: #e0e0e0; }
                    QPushButton {
                        background-color: #383838; color: #e0e0e0;
                        border: 1px solid #4a4a4a; border-radius: 4px; padding: 6px 12px;
                    }
                    QPushButton:hover { background-color: #454545; }
                """)

                first_text = self.translations.get("system_prompt_editor_delete_preset_first", "Do you really want to remove the preset:")
                second_text = self.translations.get("system_prompt_editor_delete_preset_second", "This action cannot be canceled.")

                message_text = f"""
                    <html><head><style>
                    body {{ font-family: sans-serif; font-size: 14px; color: #e0e0e0; }}
                    .preset-name {{ color: #ff6b6b; font-weight: bold; }}
                    </style></head><body>
                    <p>{first_text} <span class="preset-name">"{name}"</span>?</p>
                    <p style='color: #888;'>{second_text}</p>
                    </body></html>
                """

                msg_box.setText(message_text)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)

                reply = msg_box.exec()

                if reply == QMessageBox.StandardButton.Yes:
                    self.configuration_settings.delete_preset(name)
                    update_preset_combo()

        reset_button.clicked.connect(reset_to_default)
        save_preset_button.clicked.connect(save_current_preset)
        new_preset_btn.clicked.connect(create_new_preset)
        delete_preset_btn.clicked.connect(delete_current_preset)
        preset_combo.currentTextChanged.connect(apply_current_preset)

        load_presets()
        update_preset_combo()
        apply_current_preset()

        dialog.setLayout(main_layout)
        dialog.exec()

    def open_lorebook_editor(self):
        """
        Opens a dialog for managing lorebooks and their entries.
        Allows users to create, edit, delete, import/export lorebooks,
        and manage individual entries with trigger keywords and content.
        """
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("lorebook_editor_title", "Lorebook Editor"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(1000, 700)

        dialog.setStyleSheet("""
            QDialog { background-color: #1E1E1E; }
            
            QWidget#sidebar { background-color: #252525; border-right: 1px solid #333; }
            
            QListWidget {
                background-color: #252525;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #2e2e2e;
                color: #bbbbbb;
            }
            QListWidget::item:selected {
                background-color: #303030;
                border-left: 3px solid rgb(160, 160, 160);
                color: white;
            }
            QListWidget::item:hover { background-color: #2a2a2a; }

            QLabel { color: #cfcfcf; font-family: "Inter Tight"; font-size: 14px; }
            QLabel#header { font-size: 18px; font-weight: bold; color: white; }
            QLabel#hint { color: #666; font-size: 11px; }
            
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background-color: #2b2b2b; color: #e0e0e0;
                border: 1px solid #3e3e3e; border-radius: 6px;
                padding: 8px; font-family: "Inter Tight";
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border: 1px solid #444; background-color: #303030;
            }

            QSpinBox::up-button, QSpinBox::down-button { width: 0px; }

            QPushButton {
                background-color: #2D2D2D;
                color: #cccccc;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                padding: 6px 12px;
                font-family: "Inter Tight Medium";
            }
            QPushButton:hover { background-color: #383838; color: white; }
            QPushButton:pressed { background-color: #222; }
            
            QPushButton#primary_btn { background-color: #2D2D2D; color: white; border: 1px solid #3e3e3e; }
            QPushButton#primary_btn:hover { background-color: #333333; }
            
            QPushButton#delete_btn { color: #ff6b6b; border-color: #5a3e3e; background-color: transparent; }
            QPushButton#delete_btn:hover { background-color: #4a2525; border-color: #ff4d4d; color: white; }

            QGroupBox {
                border: 1px solid #3e3e3e; border-radius: 6px;
                margin-top: 20px; font-weight: bold; color: #888;
            }
            QGroupBox::title { subcontrol-origin: margin; padding: 0 5px; }

            QToolTip {
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)

        font_semibold = QtGui.QFont()
        font_semibold.setFamily("Inter Tight SemiBold")
        font_semibold.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        main_layout = QHBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        sb_header = QWidget()
        sb_header_layout = QVBoxLayout(sb_header)
        sb_header_layout.setContentsMargins(15, 15, 15, 10)
        
        lbl_select = QLabel(self.translations.get("lorebook_editor_select", "Current Lorebook:"))
        lbl_select.setFont(font_semibold)
        lbl_select.setStyleSheet("font-size: 12px; color: #888;")
        
        lorebook_combo = QtWidgets.QComboBox()
        lorebook_combo.setFont(font_semibold)
        lorebook_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        lorebook_combo.setFixedHeight(30)
        
        lb_actions_layout = QHBoxLayout()
        lb_actions_layout.setSpacing(5)
        
        btn_create_lb = QPushButton("+")
        btn_create_lb.setFont(font_semibold)
        btn_create_lb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_create_lb.setToolTip(self.translations.get("lorebook_editor_btn_create", "Create New Lorebook"))
        btn_create_lb.setFixedWidth(35)
        
        btn_menu_lb = QPushButton("...")
        btn_menu_lb.setFont(font_semibold)
        btn_menu_lb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_menu_lb.setToolTip(self.translations.get("lorebook_editor_options", "Lorebook Options (Import/Export/Delete)"))
        btn_menu_lb.setFixedWidth(45)
        
        lb_menu = QtWidgets.QMenu(dialog)
        action_edit_meta = QtGui.QAction(self.translations.get("lorebook_editor_edit_description", "Edit Description"), dialog)
        action_import = QtGui.QAction(self.translations.get("lorebook_editor_import_lorebook", "Import JSON"), dialog)
        action_export = QtGui.QAction(self.translations.get("lorebook_editor_export_lorebook", "Export JSON"), dialog)
        action_delete_lb = QtGui.QAction(self.translations.get("lorebook_editor_delete_lorebook", "Delete Lorebook"), dialog)
        
        lb_menu.addAction(action_edit_meta)
        lb_menu.addSeparator()
        lb_menu.addAction(action_import)
        lb_menu.addAction(action_export)
        lb_menu.addSeparator()
        lb_menu.addAction(action_delete_lb)
        
        btn_menu_lb.setMenu(lb_menu)

        lb_actions_layout.addWidget(lorebook_combo)
        lb_actions_layout.addWidget(btn_create_lb)
        lb_actions_layout.addWidget(btn_menu_lb)

        sb_header_layout.addWidget(lbl_select)
        sb_header_layout.addLayout(lb_actions_layout)

        search_bar = QLineEdit()
        search_bar.setPlaceholderText(self.translations.get("lorebook_editor_search", "Search entries..."))
        search_bar.setFont(font_semibold)
        search_bar.setStyleSheet("border-radius: 15px; padding-left: 10px; margin: 10px 15px;")
        
        entry_list = QtWidgets.QListWidget()
        entry_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        btn_add_entry = QPushButton(self.translations.get("lorebook_editor_add_entry", "+ Add New Entry"))
        btn_add_entry.setFont(font_semibold)
        btn_add_entry.setStyleSheet("""
            QPushButton {
                border: none; border-top: 1px solid #333;
                background-color: transparent; color: #888;
                text-align: left; padding: 15px;
            }
            QPushButton:hover { background-color: #2a2a2a; color: white; }
        """)
        btn_add_entry.setCursor(Qt.CursorShape.PointingHandCursor)

        sidebar_layout.addWidget(sb_header)
        sidebar_layout.addWidget(search_bar)
        sidebar_layout.addWidget(entry_list)
        sidebar_layout.addWidget(btn_add_entry)

        main_layout.addWidget(sidebar)

        editor_area = QWidget()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(30, 30, 30, 30)
        editor_layout.setSpacing(15)
        editor_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_settings_layout = QHBoxLayout()
        
        depth_label = QLabel(self.translations.get("lorebook_editor_scan_depth", "Scan Depth:"))
        depth_label.setFont(font_semibold)
        depth_combo = QtWidgets.QComboBox()
        depth_combo.setFont(font_semibold)
        depth_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        depth_combo.addItems([str(i) for i in range(1, 100)])
        depth_combo.setFixedWidth(60)
        
        top_settings_layout.addWidget(depth_label)
        top_settings_layout.addWidget(depth_combo)
        top_settings_layout.addStretch()

        editor_layout.addLayout(top_settings_layout)
        
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        line.setStyleSheet("color: #333;")
        editor_layout.addWidget(line)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0,0,0,0)
        form_layout.setSpacing(10)

        row_name_type = QHBoxLayout()

        vbox_name = QVBoxLayout()
        lbl_name = QLabel(self.translations.get("lorebook_editor_entry_name", "Entry Name"))
        lbl_name.setFont(font_semibold)
        input_name = QLineEdit()
        input_name.setPlaceholderText(self.translations.get("lorebook_editor_entry_description", "e.g. Character Name, Location, Event"))
        input_name.setFont(font_semibold)
        input_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        vbox_name.addWidget(lbl_name)
        vbox_name.addWidget(input_name)
        
        vbox_type = QVBoxLayout()
        lbl_type = QLabel(self.translations.get("lorebook_editor_trigger", "Trigger Method"))
        lbl_type.setFont(font_semibold)
        combo_type = QtWidgets.QComboBox()
        combo_type.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        combo_type.setFont(font_semibold)
        combo_type.addItems(["Keywords (Standard)", "Story Event (Scenario)"])
        vbox_type.addWidget(lbl_type)
        vbox_type.addWidget(combo_type)
        
        row_name_type.addLayout(vbox_name, 7)
        row_name_type.addLayout(vbox_type, 3)
        form_layout.addLayout(row_name_type)

        stack_triggers = QtWidgets.QStackedWidget()
        
        pg_keywords = QWidget()
        layout_keywords = QVBoxLayout(pg_keywords)
        layout_keywords.setContentsMargins(0,0,0,0)
        
        lbl_keys = QLabel(self.translations.get("lorebook_editor_keywords", "Trigger Keywords"))
        lbl_keys.setFont(font_semibold)
        input_keys = QLineEdit()
        input_keys.setPlaceholderText(self.translations.get("lorebook_editor_keywords_example", "wizard, magic, spell"))
        input_keys.setFont(font_semibold)
        
        lbl_exclude = QLabel(self.translations.get("lorebook_editor_exclude_keywords", "Exclude Keywords"))
        lbl_exclude.setFont(font_semibold)
        input_exclude = QLineEdit()
        input_exclude.setPlaceholderText(self.translations.get("lorebook_editor_exclude_keywords_example", "human, physics (Prevents activation if present)"))
        input_exclude.setFont(font_semibold)
        
        layout_keywords.addWidget(lbl_keys)
        layout_keywords.addWidget(input_keys)
        layout_keywords.addWidget(lbl_exclude)
        layout_keywords.addWidget(input_exclude)
        
        vbox_min = QVBoxLayout()
        lbl_min = QLabel(self.translations.get("lorebook_editor_start_msg", "Start Message"))
        lbl_min.setFont(font_semibold)
        spin_min = QtWidgets.QSpinBox()
        spin_min.setRange(0, 99999)
        spin_min.setFont(font_semibold)
        vbox_min.addWidget(lbl_min)
        vbox_min.addWidget(spin_min)

        vbox_max = QVBoxLayout()
        lbl_max = QLabel(self.translations.get("lorebook_editor_end_msg", "End Message"))
        lbl_max.setFont(font_semibold)
        spin_max = QtWidgets.QSpinBox()
        spin_max.setRange(0, 99999)
        spin_max.setValue(10)
        spin_max.setFont(font_semibold)
        vbox_max.addWidget(lbl_max)
        vbox_max.addWidget(spin_max)
        
        scenario_container = QWidget()
        scenario_layout = QVBoxLayout(scenario_container)
        scenario_layout.setContentsMargins(0, 20, 0, 0)

        lbl_scenario_hint = QLabel(self.translations.get("lorebook_editor_hint", "Activates strictly between these message numbers."))
        lbl_scenario_hint.setStyleSheet("color: #4CAF50; font-style: italic; font-size: 13px;")
        lbl_scenario_hint.setWordWrap(True)
        scenario_layout.addWidget(lbl_scenario_hint)

        input_row = QHBoxLayout()
        input_row.addLayout(vbox_min)
        input_row.addSpacing(15)
        input_row.addLayout(vbox_max)
        input_row.addStretch()

        scenario_layout.addLayout(input_row)
        scenario_layout.addStretch()

        stack_triggers.addWidget(pg_keywords)
        stack_triggers.addWidget(scenario_container)
        form_layout.addWidget(stack_triggers)

        lbl_content = QLabel(self.translations.get("lorebook_editor_content_title", "Lore Content / Instruction"))
        lbl_content.setFont(font_semibold)
        input_content = QTextEdit()
        input_content.setFont(font_semibold)
        input_content.setPlaceholderText(self.translations.get("lorebook_editor_content_hint", "Text inserted into prompt when triggered..."))
        input_content.setMinimumHeight(150)
        form_layout.addWidget(lbl_content)
        form_layout.addWidget(input_content)

        group_advanced = QtWidgets.QGroupBox(self.translations.get("lorebook_editor_timed_title", "Advanced and Timed Effects"))
        group_advanced.setFont(font_semibold)
        layout_adv = QtWidgets.QGridLayout(group_advanced)
        
        lbl_sticky = QLabel(self.translations.get("lorebook_editor_sticky", "Duration"))
        lbl_sticky.setToolTip(self.translations.get("lorebook_editor_sticky_hint", "Stays active for N messages after trigger."))
        spin_sticky = QtWidgets.QSpinBox()
        spin_sticky.setRange(0, 999)
        spin_sticky.setSuffix(self.translations.get("lorebook_editor_suffix", " msgs"))
        spin_sticky.setFont(font_semibold)
        
        lbl_cd = QLabel(self.translations.get("lorebook_editor_cooldown", "Cooldown"))
        lbl_cd.setToolTip(self.translations.get("lorebook_editor_cooldown_hint", "Cannot trigger again for N messages."))
        spin_cd = QtWidgets.QSpinBox()
        spin_cd.setRange(0, 999)
        spin_cd.setSuffix(self.translations.get("lorebook_editor_suffix", " msgs"))
        spin_cd.setFont(font_semibold)

        lbl_delay = QLabel(self.translations.get("lorebook_editor_delay", "Delay"))
        lbl_delay.setToolTip(self.translations.get("lorebook_editor_delay_hint", "Cannot trigger until chat has N messages."))
        spin_delay = QtWidgets.QSpinBox()
        spin_delay.setRange(0, 999)
        spin_delay.setSuffix(self.translations.get("lorebook_editor_suffix", " msgs"))
        spin_delay.setFont(font_semibold)
        
        lbl_prob = QLabel(self.translations.get("lorebook_editor_probability", "Probability"))
        lbl_prob.setToolTip(self.translations.get("lorebook_editor_probability_hint", "Chance to trigger when conditions are met."))
        spin_prob = QtWidgets.QSpinBox()
        spin_prob.setRange(0, 100)
        spin_prob.setSuffix("%")
        spin_prob.setValue(100)
        spin_prob.setFont(font_semibold)

        layout_adv.addWidget(lbl_sticky, 0, 0)
        layout_adv.addWidget(spin_sticky, 1, 0)
        layout_adv.addWidget(lbl_cd, 0, 1)
        layout_adv.addWidget(spin_cd, 1, 1)
        layout_adv.addWidget(lbl_delay, 0, 2)
        layout_adv.addWidget(spin_delay, 1, 2)
        layout_adv.addWidget(lbl_prob, 0, 3)
        layout_adv.addWidget(spin_prob, 1, 3)
        
        form_layout.addWidget(group_advanced)

        row_btns = QHBoxLayout()
        btn_del_entry = QPushButton(self.translations.get("lorebook_editor_delete_entry", "Delete Entry"))
        btn_del_entry.setObjectName("delete_btn")
        btn_del_entry.setFont(font_semibold)
        btn_del_entry.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_save_all = QPushButton(self.translations.get("lorebook_editor_save", "Save All Changes"))
        btn_save_all.setObjectName("primary_btn")
        btn_save_all.setFont(font_semibold)
        btn_save_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_all.setFixedWidth(170)
        
        row_btns.addWidget(btn_del_entry)
        row_btns.addStretch()
        row_btns.addWidget(btn_save_all)
        form_layout.addLayout(row_btns)

        form_widget.setVisible(False)
        editor_layout.addWidget(form_widget)

        lbl_empty = QLabel(self.translations.get("lorebook_editor_main_hint", "Select an entry to edit or create a new one."))
        lbl_empty.setFont(font_semibold)
        lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_empty.setStyleSheet("color: #555; font-size: 16px; margin-top: 50px;")
        editor_layout.addWidget(lbl_empty)

        main_layout.addWidget(editor_area)

        lorebooks = {}
        current_lorebook_name = None
        current_entry_index = -1
        is_programmatic_change = False

        def load_lorebooks():
            nonlocal lorebooks
            lorebooks = self.configuration_settings.load_configuration().get("user_data", {}).get("lorebooks", {})

        def update_lorebook_combo():
            lorebook_combo.clear()
            for name in lorebooks:
                lorebook_combo.addItem(name)

        def populate_entry_list():
            entry_list.clear()
            if not current_lorebook_name or current_lorebook_name not in lorebooks:
                return

            entries = lorebooks[current_lorebook_name].get("entries", [])
            filter_text = search_bar.text().lower()

            for idx, entry in enumerate(entries):
                name = entry.get("name", "Unnamed Entry")
                keys = ", ".join(entry.get("key", []))
                if entry.get("trigger_type") == "range":
                    name = f"📅 {name} [{entry.get('min_msg',0)}-{entry.get('max_msg',0)}]"
                
                if filter_text and (filter_text not in name.lower() and filter_text not in keys.lower()):
                    continue

                item = QtWidgets.QListWidgetItem()
                item.setText(name)
                item.setData(Qt.ItemDataRole.UserRole, idx)
                entry_list.addItem(item)

        def apply_current_lorebook():
            nonlocal current_lorebook_name
            name = lorebook_combo.currentText()
            if name in lorebooks:
                current_lorebook_name = name
                data = lorebooks[name]
                depth_combo.setCurrentIndex(data.get("n_depth", 3) - 1)
                form_widget.setVisible(False)
                lbl_empty.setVisible(True)
                populate_entry_list()

        def on_type_changed(idx):
            stack_triggers.setCurrentIndex(idx)
            save_current_entry_changes()

        def select_entry(item):
            nonlocal current_entry_index, is_programmatic_change
            if not item: return
            
            idx = item.data(Qt.ItemDataRole.UserRole)

            if current_lorebook_name not in lorebooks:
                logger.warning(f"Lorebook '{current_lorebook_name}' not found in memory. Refreshing UI.")
                form_widget.setVisible(False)
                lbl_empty.setVisible(True)
                lbl_empty.setText(f"Lorebook '{current_lorebook_name}' not found.")
                load_lorebooks()
                update_lorebook_combo()
                if lorebook_combo.count() > 0:
                    apply_current_lorebook()
                return
    
            current_entry_index = idx
            entry = lorebooks[current_lorebook_name]["entries"][idx]
            
            is_programmatic_change = True
            
            input_name.setText(entry.get("name", "Unnamed"))
            input_content.setPlainText(entry.get("content", ""))
            
            t_type = entry.get("trigger_type", "keyword")
            if t_type == "range":
                combo_type.setCurrentIndex(1)
                spin_min.setValue(entry.get("min_msg", 0))
                spin_max.setValue(entry.get("max_msg", 10))
            else:
                combo_type.setCurrentIndex(0)
                input_keys.setText(", ".join(entry.get("key", [])))
                input_exclude.setText(", ".join(entry.get("exclude_key", [])))

            spin_sticky.setValue(entry.get("sticky", 0))
            spin_cd.setValue(entry.get("cooldown", 0))
            spin_delay.setValue(entry.get("delay", 0))
            spin_prob.setValue(entry.get("probability", 100))

            is_programmatic_change = False
            
            form_widget.setVisible(True)
            lbl_empty.setVisible(False)

        def save_current_entry_changes():
            if is_programmatic_change or current_entry_index < 0: return
            
            data = lorebooks[current_lorebook_name]["entries"][current_entry_index]
            data["name"] = input_name.text().strip() or "Unnamed"
            data["content"] = input_content.toPlainText()
            
            if combo_type.currentIndex() == 0:
                data["trigger_type"] = "keyword"
                data["key"] = [k.strip() for k in input_keys.text().split(",") if k.strip()]
                data["exclude_key"] = [k.strip() for k in input_exclude.text().split(",") if k.strip()]
            else:
                data["trigger_type"] = "range"
                data["min_msg"] = spin_min.value()
                data["max_msg"] = spin_max.value()
                data["key"] = [] 

            data["sticky"] = spin_sticky.value()
            data["cooldown"] = spin_cd.value()
            data["delay"] = spin_delay.value()
            data["probability"] = spin_prob.value()

            item = entry_list.currentItem()
            if item:
                display_name = data["name"]
                if data["trigger_type"] == "range":
                     display_name = f"📅 {display_name} [{data['min_msg']}-{data['max_msg']}]"
                item.setText(display_name)

        def add_entry():
            if not current_lorebook_name: return
            new_entry = { "name": "New Entry", "key": [], "content": "", "probability": 100 }
            lorebooks[current_lorebook_name]["entries"].append(new_entry)
            populate_entry_list()
            entry_list.setCurrentRow(entry_list.count() - 1)
            input_name.setFocus()
            input_name.selectAll()

        def delete_entry():
            if current_entry_index < 0: return
            confirm = QMessageBox.question(dialog, self.translations.get("lorebook_editor_delete", "Delete"), self.translations.get("lorebook_editor_delete_question", "Delete entry?"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                del lorebooks[current_lorebook_name]["entries"][current_entry_index]
                form_widget.setVisible(False)
                lbl_empty.setVisible(True)
                populate_entry_list()

        def create_lorebook():
            name, ok = QInputDialog.getText(dialog, self.translations.get("lorebook_editor_new_lorebook", "New Lorebook"), self.translations.get("lorebook_editor_lorebook_name", "Name:"))
            if ok and name and name not in lorebooks:
                lorebooks[name] = {"name": name, "n_depth": 3, "entries": []}
                self.configuration_settings.update_lorebook(name, lorebooks[name])
                load_lorebooks()
                update_lorebook_combo()
                lorebook_combo.setCurrentText(name)
        
        def edit_lorebook_description():
            name = lorebook_combo.currentText()
            if not name or name not in lorebooks:
                return

            current_desc = lorebooks[name].get("description", "")

            edit_lorebook_translation = self.translations.get("lorebook_editor_edit_description_label", f"Description for '{name}':").format(name=name)
            edit_lorebook_translation_desc = self.translations.get("lorebook_editor_edit_description_updated", f"Description for lorebook '{name}' updated.").format(name=name)
            
            new_desc, ok = QInputDialog.getMultiLineText(
                dialog, 
                self.translations.get("lorebook_editor_edit_description_title", "Edit Lorebook Description"),
                edit_lorebook_translation,
                current_desc
            )

            if ok:
                lorebooks[name]["description"] = new_desc
                self.configuration_settings.update_lorebook(name, lorebooks[name])
                logger.info(edit_lorebook_translation_desc)

        def delete_lorebook_action():
            name = lorebook_combo.currentText()
            lorebook_editor_delete_translation = self.translations.get("lorebook_editor_delete_lorebook", f"Delete '{name}'?").format(name=name)

            if not name: return
            res = QMessageBox.warning(dialog, self.translations.get("lorebook_editor_delete", "Delete"), lorebook_editor_delete_translation, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.Yes:
                del lorebooks[name]
                self.configuration_settings.delete_lorebook(name)
                load_lorebooks()
                update_lorebook_combo()
                apply_current_lorebook()

        def export_lorebook_action():
            name = lorebook_combo.currentText()
            if not name or name not in lorebooks:
                return

            source = lorebooks[name]
            file_path, _ = QFileDialog.getSaveFileName(
                dialog, "Export Lorebook", f"{name}.json", "JSON Files (*.json)"
            )
            if not file_path:
                return

            export_data = {
                "name": name,
                "description": source.get("description", ""),
                "is_creation": False,
                "scan_depth": source.get("n_depth", 3),
                "token_budget": 500,
                "recursive_scanning": False,
                "extensions": {
                    "sow_engine": "Soul of Waifu Scenario Engine"
                },
                "entries": {}
            }

            for idx, entry in enumerate(source.get("entries", [])):
                uid = idx + 1
                export_data["entries"][str(uid)] = {
                    "uid": uid,
                    "name": entry.get("name", f"Entry {uid}"),
                    "key": entry.get("key", []),
                    "comment": entry.get("name", ""),
                    "content": entry.get("content", ""),
                    "constant": False,
                    "probability": entry.get("probability", 100),
                    "enabled": True,
                    "keys": entry.get("key", []),
                    "extensions": {
                        "sow_trigger_type": entry.get("trigger_type", "keyword"),
                        "sow_min_msg": entry.get("min_msg", 0),
                        "sow_max_msg": entry.get("max_msg", 0),
                        "sow_exclude_key": entry.get("exclude_key", []),
                        "sow_sticky": entry.get("sticky", 0),
                        "sow_cooldown": entry.get("cooldown", 0),
                        "sow_delay": entry.get("delay", 0)
                    }
                }

            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(dialog, self.translations.get("lorebook_editor_export_success", "Export Success"), self.translations.get("lorebook_editor_export_success_desc", "Lorebook saved successfully."))
            except Exception as e:
                logger.error(f"Export error: {e}")
                QMessageBox.critical(dialog, self.translations.get("lorebook_editor_export_error", "Export Error"), str(e))

        def import_lorebook_action():
            file_path, _ = QFileDialog.getOpenFileName(
                dialog, "Import Lorebook", "", "JSON Files (*.json)"
            )
            if not file_path:
                return

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                new_name = data.get("name")
                if not new_name or new_name.strip() == "":
                    new_name = os.path.splitext(os.path.basename(file_path))[0]
                
                orig_name = new_name
                counter = 1
                while new_name in lorebooks:
                    new_name = f"{orig_name}_{counter}"
                    counter += 1

                new_lorebook = {
                    "name": new_name,
                    "description": data.get("description", ""),
                    "n_depth": data.get("scan_depth", 3),
                    "entries": []
                }

                entries_data = data.get("entries", {})
                
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

                lorebooks[new_name] = new_lorebook
                self.configuration_settings.update_lorebook(new_name, new_lorebook)
                
                load_lorebooks()
                update_lorebook_combo()
                lorebook_combo.setCurrentText(new_name)
                apply_current_lorebook()
                
                count = {len(new_lorebook['entries'])}
                lorebook_editor_import_translation = self.translations.get("lorebook_editor_import_success_desc", f"Lorebook '{new_name}' imported with {count} entries.").format(new_name=new_name, count=count)
                QMessageBox.information(dialog, self.translations.get("lorebook_editor_import_success", "Import Success"), lorebook_editor_import_translation)

            except Exception as e:
                logger.error(f"Import error: {e}")
                error = {str(e)}
                lorebook_editor_import_error_translation = self.translations.get("lorebook_editor_import_error_desc", f"Failed to parse lorebook: {error}").format(error=error)
                QMessageBox.critical(dialog, self.translations.get("lorebook_editor_import_error", "Import Error"), lorebook_editor_import_error_translation)

        def global_save():
            if current_lorebook_name:
                lorebooks[current_lorebook_name]["n_depth"] = int(depth_combo.currentText())
            self.configuration_settings.save_lorebooks(lorebooks)
            QMessageBox.information(dialog, self.translations.get("lorebook_editor_saved", "Saved"), self.translations.get("lorebook_editor_saved_desc", "Lorebooks saved successfully."))

        lorebook_combo.currentTextChanged.connect(apply_current_lorebook)
        entry_list.itemClicked.connect(select_entry)
        
        btn_add_entry.clicked.connect(add_entry)
        btn_del_entry.clicked.connect(delete_entry)
        btn_save_all.clicked.connect(global_save)
        
        btn_create_lb.clicked.connect(create_lorebook)

        action_import.triggered.connect(import_lorebook_action)
        action_export.triggered.connect(export_lorebook_action)
        action_edit_meta.triggered.connect(edit_lorebook_description)
        action_delete_lb.triggered.connect(delete_lorebook_action)
        
        input_name.textChanged.connect(save_current_entry_changes)
        input_content.textChanged.connect(save_current_entry_changes)
        
        combo_type.currentIndexChanged.connect(on_type_changed)
        
        input_keys.textChanged.connect(save_current_entry_changes)
        input_exclude.textChanged.connect(save_current_entry_changes)
        
        spin_min.valueChanged.connect(save_current_entry_changes)
        spin_max.valueChanged.connect(save_current_entry_changes)
        
        spin_sticky.valueChanged.connect(save_current_entry_changes)
        spin_cd.valueChanged.connect(save_current_entry_changes)
        spin_delay.valueChanged.connect(save_current_entry_changes)
        spin_prob.valueChanged.connect(save_current_entry_changes)
        
        search_bar.textChanged.connect(populate_entry_list)

        load_lorebooks()
        update_lorebook_combo()
        if lorebook_combo.count() > 0:
            apply_current_lorebook()

        dialog.exec()

    def open_author_notes_editor(self):
        """
        Opens a simple editor for modifying the Author's Notes.
        The user can edit and save notes that will be inserted into prompts dynamically.
        """
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("author_notes_editor_title", "Author Notes Editor"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(700, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(30, 30, 30);
                border-radius: 10px;
            }
            QLabel {
                color: rgb(200, 200, 200);
            }
            QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton {
                background-color: rgb(60, 60, 60);
                color: rgb(227, 227, 227);
                border: none;
                border-radius: 5px;
                padding: 10px;
                font: 10pt "Inter Tight Medium";
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: rgb(80, 80, 80);
            }
            QPushButton:pressed {
                background-color: rgb(40, 40, 40);
            }
        """)

        layout = QVBoxLayout()

        title_label = QLabel(self.translations.get("author_notes_editor_description", "Editing author's notes"))
        font = QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        title_label.setFont(font)
        layout.addWidget(title_label)

        notes_edit = QTextEdit()
        notes_edit.setAcceptRichText(False)
        notes_edit.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        notes_edit.setPlaceholderText(
            self.translations.get("author_notes_editor_placeholder", "Enter your instructions or hints for the character...")
        )

        current_notes = self.configuration_settings.get_user_data("author_notes") or ""
        notes_edit.setPlainText(current_notes)
        layout.addWidget(notes_edit)

        button_layout = QHBoxLayout()
        save_button = QPushButton(self.translations.get("author_notes_editor_save", "Save"))
        save_button.setFixedHeight(40)
        font = QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        save_button.setFont(font)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 6px;
                border: 1px solid #383838;
                padding: 0 16px;
                height: 38px;
                font-family: "Inter Tight Medium";
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

        def save_notes():
            new_notes = notes_edit.toPlainText().strip()
            self.configuration_settings.update_user_data("author_notes", new_notes)

            self.show_toast(self.translations.get("author_notes_saved_body", "The author's notes were saved successfully."), "success")
            dialog.accept()

        save_button.clicked.connect(save_notes)

        dialog.setLayout(layout)
        dialog.exec()

    def open_summary_editor(self, character_name, conversation_method):
        char_config = self.configuration_characters.load_configuration()
        
        if not character_name or character_name not in char_config["character_list"]:
            return

        char_data = char_config["character_list"][character_name]
        current_chat_id = char_data.get("current_chat", "default")
        chat_data = char_data["chats"].get(current_chat_id, {})

        current_summary_text = chat_data.get("summary_text", "")
        last_seq = chat_data.get("last_summarized_sequence", 0)

        current_prompt = self.configuration_settings.get_main_setting("prompt_summary")
        if not current_prompt:
            current_prompt = ("""
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

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("summary_editor_title", "Story Memory Editor"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(800, 700)
        
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                border-radius: 12px;
            }
            QLabel {
                color: #e0e0e0;
                font-family: "Inter Tight Medium";
            }
            QTextEdit, QPlainTextEdit {
                background-color: #252525;
                color: #e0e0e0;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 12px;
                font-family: "Inter Tight Medium";
                font-size: 14px;
                selection-background-color: #3d5afe;
                line-height: 1.4;
            }
            QTextEdit:focus, QPlainTextEdit:focus {
                border: 1px solid #555;
                background-color: #2a2a2a;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        
        title_label = QLabel(self.translations.get("summary_editor_heading", "Story Memory"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        title_label.setFont(font)
        
        status_msg = self.translations.get("summary_editor_covered_history", f"Covered History: Messages 1-{last_seq}").format(last_seq=last_seq)
        status_label = QLabel(status_msg)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        status_label.setFont(font)
        status_label.setStyleSheet("color: #888; font-size: 12px; background: #252525; padding: 4px 8px; border-radius: 4px;")
        status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        layout.addLayout(header_layout)

        lbl_memory = QLabel(self.translations.get("summary_editor_current_memory_text", "Current Memory Text (The result injected into context)"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_memory.setFont(font)
        lbl_memory.setStyleSheet("color: #aaaaaa; font-weight: bold; margin-top: 5px;")
        layout.addWidget(lbl_memory)

        summary_edit = QTextEdit()
        summary_edit.setAcceptRichText(False)
        summary_edit.setPlaceholderText(self.translations.get("summary_editor_memory_empty", "The memory is empty..."))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        summary_edit.setFont(font)
        summary_edit.setPlainText(current_summary_text)
        layout.addWidget(summary_edit, stretch=2)

        lbl_prompt = QLabel(self.translations.get("summary_editor_sum_instructions", "Summarization Instructions (How the AI should compress the story)"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        lbl_prompt.setFont(font)
        lbl_prompt.setStyleSheet("color: #aaaaaa; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_prompt)

        prompt_edit = QtWidgets.QPlainTextEdit()
        prompt_edit.setPlaceholderText(self.translations.get("summary_editor_instruction_placeholder", "Enter instructions for the AI..."))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        prompt_edit.setFont(font)
        prompt_edit.setPlainText(current_prompt)
        prompt_edit.setFixedHeight(100)
        layout.addWidget(prompt_edit)

        button_layout = QHBoxLayout()
        
        btn_style = """
            QToolTip {
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 0 16px;
                height: 38px;
                font-family: "Inter Tight Medium";
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #383838;
                border: 1px solid #555;
                color: #ffffff;
            }
            QPushButton:pressed { background-color: #222; }
        """
        
        clear_btn = QPushButton(self.translations.get("summary_editor_clear", "Clear Memory"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        clear_btn.setFont(font)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(btn_style + "QPushButton:hover { background-color: #4a2b2b; border-color: #6e3838; }")
        
        generate_btn = QPushButton(self.translations.get("summary_editor_generate", "Generate Summary"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        generate_btn.setFont(font)
        generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        generate_btn.setStyleSheet(btn_style)
        generate_btn.setToolTip(self.translations.get("summary_editor_tooltip", "Uses the 'Instructions' below to summarize recent messages immediately."))

        save_btn = QPushButton(self.translations.get("summary_editor_save", "Save Changes"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        save_btn.setFont(font)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 6px;
                border: 1px solid #383838;
                padding: 0 16px;
                height: 38px;
                font-family: "Inter Tight Medium";
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }
            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)

        button_layout.addWidget(clear_btn)
        button_layout.addWidget(generate_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)

        def save_all():
            new_text = summary_edit.toPlainText().strip()
            chat_data["summary_text"] = new_text
            self.configuration_characters.save_configuration_edit(char_config)

            new_prompt_text = prompt_edit.toPlainText().strip()
            self.configuration_settings.update_main_setting("prompt_summary", new_prompt_text)

        def clear_summary():
            title = self.translations.get("summary_editor_clear_title", "Clear Memory?")
            message = self.translations.get("summary_editor_clear_text", "Are you sure you want to delete the story memory?")

            if self.show_confirmation_dialog(title, message):
                summary_edit.clear()
                nonlocal last_seq
                last_seq = 0
                status_msg = self.translations.get("summary_editor_covered_history", "Covered History: Messages 1-{last_seq}").format(last_seq=0)
                status_label.setText(status_msg)

                chat_data["last_summarized_sequence"] = last_seq
                self.configuration_characters.save_configuration_edit(char_config)

        def force_update():
            new_prompt_text = prompt_edit.toPlainText().strip()
            self.configuration_settings.update_main_setting("prompt_summary", new_prompt_text)
            
            interval = int(self.configuration_settings.get_main_setting("interval_summary") or 20)
            
            raw_messages = chat_data.get("chat_content", {}).values()
            sorted_messages = sorted(raw_messages, key=lambda x: x.get("sequence_number", 0))
            
            new_messages_chunk =[]
            highest_seq_in_chunk = last_seq
            
            for msg in sorted_messages:
                seq = msg.get("sequence_number", 0)
                
                if seq > last_seq:
                    current_var_id = msg.get("current_variant_id", "default")
                    text_content = ""
                    
                    for variant in msg.get("variants",[]):
                        if variant.get("variant_id") == current_var_id:
                            text_content = variant.get("text", "")
                            break
                    
                    if not text_content.strip():
                        continue
                    
                    role = "user" if msg.get("is_user") else "assistant"
                    new_messages_chunk.append({"role": role, "content": text_content})
                    highest_seq_in_chunk = seq
                    
                    if len(new_messages_chunk) >= interval:
                        break
            
            if not new_messages_chunk:
                QMessageBox.information(dialog, "Info", self.translations.get("summary_editor_no_new_msg", "No new messages to summarize."))
                return

            config_user = self.configuration_settings.load_configuration()
            selected_persona = char_data.get("selected_persona", "None")
            user_name = config_user.get("user_data", {}).get("personas", {}).get(selected_persona, {}).get("user_name", "User")

            async def run_generation():
                nonlocal last_seq

                generate_btn.setEnabled(False)
                save_btn.setEnabled(False)
                clear_btn.setEnabled(False)
                generate_btn.setText(self.translations.get("summary_editor_generating", "Generating..."))

                old_text = summary_edit.toPlainText().strip()
                summary_edit.clear()

                generation_successful = False

                try:
                    match conversation_method:
                        case "Mistral AI":
                            generator = self.mistral_ai_client.generate_summary(
                                current_summary=old_text,
                                new_messages=new_messages_chunk,
                                character_name=character_name,
                                user_name=user_name
                            )
                        case "Open AI" | "OpenRouter":
                            generator = self.open_ai_client.generate_summary(
                                conversation_method=conversation_method,
                                current_summary=old_text,
                                new_messages=new_messages_chunk,
                                character_name=character_name,
                                user_name=user_name
                            )
                        case "Local LLM" | _:
                            generator = self.local_ai_client.generate_summary(
                                current_summary=old_text,
                                new_messages=new_messages_chunk,
                                character_name=character_name,
                                user_name=user_name
                            )

                    async for chunk in generator:
                        summary_edit.insertPlainText(chunk)
                        scrollbar = summary_edit.verticalScrollBar()
                        scrollbar.setValue(scrollbar.maximum())

                    generation_successful = True

                except Exception as e:
                    QMessageBox.critical(dialog, "Error", f"Summarization failed:\n{str(e)}")
                    summary_edit.setPlainText(old_text)

                finally:
                    generate_btn.setEnabled(True)
                    save_btn.setEnabled(True)
                    clear_btn.setEnabled(True)
                    generate_btn.setText(self.translations.get("summary_editor_generate", "Generate Summary"))

                    if generation_successful:
                        status_msg = self.translations.get("summary_editor_covered_history", "Covered History: Messages 1-{last_seq}").format(last_seq=highest_seq_in_chunk)
                        status_label.setText(status_msg)
                        chat_data["last_summarized_sequence"] = highest_seq_in_chunk
                        self.configuration_characters.save_configuration_edit(char_config)
                        save_all()

            asyncio.create_task(run_generation())

        save_btn.clicked.connect(save_all)
        clear_btn.clicked.connect(clear_summary)
        generate_btn.clicked.connect(force_update)

        dialog.setLayout(layout)
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
        Displays a success or error message based on the task result.
        """
        result = task.result()

        def show_message_box(title, message_text, is_success=True):
            message_box = QMessageBox()
            message_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box.setWindowTitle(title)
            message_box.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: rgb(227, 227, 227);
                }
                QLabel {
                    color: rgb(227, 227, 227);
                }
            """)
            message_box.setText(message_text)
            message_box.exec()

        if result:
            character_name = result
            first_text = self.translations.get(
                "add_character_text_1", 
                "was successfully added!"
            )
            second_text = self.translations.get(
                "add_character_text_2", 
                "You can now interact with the character in your character list."
            )

            success_message = f"""
                <html>
                    <head>
                        <style>
                            body {{
                                background-color: #2b2b2b;
                            }}
                            h1 {{
                                background-color: rgb(27, 27, 27);
                                color: #4CAF50;
                                font-family: "Segoe UI", Arial, sans-serif;
                                font-size: 20px;
                            }}
                            p {{
                                background-color: rgb(27, 27, 27);
                                color: rgb(227, 227, 227);
                                font-family: "Segoe UI", Arial, sans-serif;
                                font-size: 14px;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                        <p>{second_text}</p>
                    </body>
                </html>
            """
            show_message_box(self.translations.get("add_character_title", "Character Information"), success_message, is_success=True)
        else:
            first_text = self.translations.get(
                "add_character_text_3", 
                "There was an error while adding the character."
            )
            second_text = self.translations.get(
                "add_character_text_4", 
                "Please try again."
            )

            error_message = f"""
                <html>
                    <head>
                        <style>
                            body {{
                                background-color: #2b2b2b;
                            }}
                            h1 {{
                                color: #FF6347;
                                font-family: "Segoe UI", Arial, sans-serif;
                                font-size: 20px;
                            }}
                            p {{
                                color: rgb(227, 227, 227);
                                font-family: "Segoe UI", Arial, sans-serif;
                                font-size: 14px;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>{first_text}</h1>
                        <p>{second_text}</p>
                    </body>
                </html>
            """
            show_message_box("Error", error_message, is_success=False)

    async def add_character(self):
        """
        Adds a character to the list based on the currently selected conversation method.
        """
        character_configuration = self.configuration_characters.load_configuration()
        character_list = character_configuration["character_list"]
        conversation_method = self.configuration_settings.get_main_setting("conversation_method")
        character_id = self.ui.character_id_lineEdit.text()
        
        async def handle_character_ai():
            """
            Handles adding a character using the Character AI method.
            """
            try:
                character_name = await self.character_ai_client.create_character(character_id)
                self.ui.character_id_lineEdit.clear()

                return character_name
            except Exception as e:
                logger.error(f"Error adding character: {e}")
                return None

        def handle_generic_ai(method_name):
            """
            Handles adding a character for generic AI methods.
            """
            try:
                character_name = self.ui.lineEdit_character_name_building.text()
                character_avatar_directory = self.configuration_settings.get_user_data("current_character_image")
                if character_avatar_directory == "None" or character_avatar_directory == None:
                    character_avatar_directory = "app/gui/icons/logotype.png"
                character_description = self.ui.textEdit_character_description_building.toPlainText()
                character_personality = self.ui.textEdit_character_personality_building.toPlainText()
                character_first_message = self.ui.textEdit_first_message_building.toPlainText()

                if not character_name or not character_first_message:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowTitle(self.translations.get("add_character_error_title", "Error adding a character"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #FF6347;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1>{self.translations.get("add_character_error", "Set a name and the first message for your character.")}</h1>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return
                
                scenario = self.ui.textEdit_scenario.toPlainText()
                example_messages = self.ui.textEdit_example_messages.toPlainText()
                alternate_greetings = self.ui.textEdit_alternate_greetings.toPlainText()
                creator_notes = self.ui.textEdit_creator_notes.toPlainText()

                parts = alternate_greetings.split("<GREETING>")
                greetings = []
                for part in parts:
                    stripped = part.strip()
                    if stripped:
                        greetings.append(stripped)

                selected_persona = self.ui.comboBox_user_persona_building.currentText()
                selected_system_prompt_preset = self.ui.comboBox_system_prompt_building.currentText()
                selected_lorebook = self.ui.comboBox_lorebook_building.currentText()
                
                if character_name in character_list:
                    suffix = 1
                    while f"{character_name}_{suffix}" in character_list:
                        suffix += 1
                    suggested_name = f"{character_name}_{suffix}"

                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowTitle(self.translations.get("duplicate_character_error_title", "Duplicate Character"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1>{self.translations.get("duplicate_character_error", "A character with this name already exists. A number will be added to the character's name.")}</h1>
                                <p>{suggested_name}</p>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()

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
                    conversation_method=method_name
                )

                clear_input_fields()
                reset_image_button_icon()

                return character_name
            except Exception as e:
                logger.error(f"Error adding character ({method_name}): {e}")
                return None

        def clear_input_fields():
            """
            Clears all input fields related to character creation.
            """
            self.ui.lineEdit_character_name_building.clear(),
            self.ui.textEdit_character_description_building.clear(),
            self.ui.textEdit_character_personality_building.clear(),
            self.ui.textEdit_first_message_building.clear(),
            self.ui.textEdit_scenario.clear(),
            self.ui.textEdit_example_messages.clear(),
            self.ui.textEdit_alternate_greetings.clear(),
            self.ui.textEdit_creator_notes.clear(),
            self.ui.textEdit_character_version.clear()

        def reset_image_button_icon():
            """
            Resets the image button icon to its default state.
            """
            icon_import = QtGui.QIcon()
            icon_import.addPixmap(QtGui.QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            self.ui.pushButton_import_character_image.setIcon(icon_import)
            self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
            self.configuration_settings.update_user_data("current_character_image", None)

        match conversation_method:
            case "Character AI":
                return await handle_character_ai()
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
                return handle_generic_ai(conversation_method)
            case _:
                logger.error(f"Unsupported conversation method: {conversation_method}")
                return None

    def on_stacked_widget_changed(self, index):
        """
        The slot that is called when the current widget is changed in QStackedWidget.
        """
        if not hasattr(self, '_previous_index'):
            self._previous_index = 0

        CHAT_WIDGET_INDEX = 6

        if self._previous_index == CHAT_WIDGET_INDEX and index != CHAT_WIDGET_INDEX:
            self.ui.character_description_chat.setText("")

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

            self.center()

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
        
        self._previous_index = index

    async def close_chat(self):
        self.center()

        self.current_active_character = None
        self.ui.character_description_chat.setText("")

        if hasattr(self.ui_signals, 'playback_worker'):
            self.ui_signals.playback_worker.stop()
            self.ui_signals.playback_worker.deleteLater()

        if self.expression_widget is not None:
            self.expression_widget.setParent(None)
            self.expression_widget.deleteLater()
            self.expression_widget = None

        if self.stackedWidget_expressions is not None:
            self.stackedWidget_expressions.setCurrentIndex(-1)
            self.stackedWidget_expressions.setParent(None)
            self.stackedWidget_expressions.deleteLater()
            self.stackedWidget_expressions = None
    
    def center(self):
        """
        Places the program window in the center of the screen.
        """
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        center_point = screen_geometry.center()
        frame_geometry = self.main_window.frameGeometry()
        frame_geometry.moveCenter(center_point)
        self.main_window.move(frame_geometry.topLeft())
    ### SETUP BUTTONS ==================================================================================

    ### SETUP MAIN TAB AND CREATE CHARACTER ============================================================
    async def set_main_tab(self):
        """
        Configures the main interface tab by uploading a list of characters and setting up a user profile.
        """
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

            if user_avatar:
                pixmap = QPixmap(user_avatar)
                self.ui.user_avatar_label.setPixmap(pixmap.scaled(70, 70, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
                mask = QPixmap(pixmap.size())
                mask.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QPainter(mask)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QtCore.Qt.GlobalColor.black)
                painter.setPen(QtCore.Qt.GlobalColor.transparent)
                painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
                painter.end()
                pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
                self.ui.user_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.ui.user_avatar_label.setScaledContents(True)
                self.ui.user_avatar_label.setPixmap(pixmap)
            else:
                pixmap = QPixmap("app/gui/icons/person.png")
                self.ui.user_avatar_label.setPixmap(pixmap.scaled(70, 70, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
                mask = QPixmap(pixmap.size())
                mask.fill(QtCore.Qt.GlobalColor.transparent)
                painter = QPainter(mask)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setBrush(QtCore.Qt.GlobalColor.black)
                painter.setPen(QtCore.Qt.GlobalColor.transparent)
                painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
                painter.end()
                pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
                self.ui.user_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.ui.user_avatar_label.setScaledContents(True)
                self.ui.user_avatar_label.setPixmap(pixmap)

            welcome_message = self.translations.get("welcome_message", "Welcome to Soul of Waifu, ")
            if user_name:
                self.ui.welcome_label_2.setText(f"{welcome_message}{user_name}")
            else:
                self.ui.welcome_label_2.setText(f"{welcome_message}User")

            self.ui.stackedWidget.setCurrentIndex(1)
            QApplication.processEvents()

            characters = character_data.get('character_list', {})

            for character_name, data in characters.items():
                conversation_method = data.get("conversation_method")
                character_avatar_replacement = "app/gui/icons/logotype.png"
                match conversation_method:
                    case "Character AI":
                        conversation_method_image = "app/gui/icons/characterai.png"
                        character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                        character_avatar = await self.character_ai_client.load_image(character_avatar_url)
                    case "Mistral AI":
                        conversation_method_image = "app/gui/icons/mistralai.png"
                        character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                        character_avatar = character_avatar_url
                    case "Open AI":
                        conversation_method_image = "app/gui/icons/openai.png"
                        character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                        character_avatar = character_avatar_url
                    case "OpenRouter":
                        conversation_method_image = "app/gui/icons/openrouter.png"
                        character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                        character_avatar = character_avatar_url
                    case "Local LLM":
                        conversation_method_image = "app/gui/icons/local_llm.png"
                        character_avatar_url = data.get("character_avatar", character_avatar_replacement)
                        character_avatar = character_avatar_url

                card_widget = CharacterCardList(character_name=character_name, 
                    image_path=character_avatar, 
                    icon_api_path=conversation_method_image, 
                    method=self.open_chat, 
                    parent=self.container
                )
                character_widget = self.create_character_card_widget(character_name, card_widget)
                self.cards.append(character_widget)
                character_widget.setVisible(True)

                self.update_layout() 
                QApplication.processEvents()

            QtCore.QTimer.singleShot(0, self.update_layout)
            self.ui.lineEdit_search_character_menu.textChanged.connect(self.filter_characters)
        else:
            self.ui.stackedWidget.setCurrentIndex(0)

    def create_character_card_widget(self, character_name, card_widget):
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")

        call_btn = AnimatedHoverButton("app/gui/icons/phone.png", "#2E7D32", self.translations.get("call_btn_text", "Call"))
        voice_btn = AnimatedHoverButton("app/gui/icons/voice.png", "#1976D2", self.translations.get("voice_btn_text", "Voice Settings"))
        expr_btn = AnimatedHoverButton("app/gui/icons/expressions.png", "#F57C00", self.translations.get("expressions_btn_text", "Expressions"))
        del_btn = AnimatedHoverButton("app/gui/icons/bin.png", "#D32F2F", self.translations.get("delete_btn_text", "Delete"))

        voice_btn.clicked.connect(lambda: self.open_voice_menu(character_name))
        expr_btn.clicked.connect(lambda: self.open_expressions_menu(character_name))
        del_btn.clicked.connect(lambda: self.delete_character(card_widget, character_name))

        if sow_system_status:
            call_btn.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
            card_widget.action_panel_layout.addWidget(call_btn)

        card_widget.action_panel_layout.addWidget(voice_btn)

        if sow_system_status:
            card_widget.action_panel_layout.addWidget(expr_btn)

        card_widget.action_panel_layout.addWidget(del_btn)

        base_col = QtGui.QColor(0, 0, 0, 100)
        hover_col = QtGui.QColor(0, 0, 0, 200)

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

        return card_widget

    def filter_characters(self, search_text):
        """
        Filters the character list based on the search text entered by the user.
        """
        search_text = search_text.lower()

        for card in self.cards:
            character_name = card.character_name.lower()
            if not search_text or search_text in character_name:
                card.setVisible(True)
            else:
                card.setVisible(False)

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

    def delete_character(self, card_widget, character_name):
        """
        Removes a character from the list.
        """
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        msg_box.setWindowTitle(self.translations.get("delete_message_1", "Delete Character"))
        msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: rgb(227, 227, 227);
                }
                QLabel {
                    color: rgb(227, 227, 227);
                }
            """)
        first_text = self.translations.get("delete_message_2", "Are you sure you want to delete ")
        message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: rgb(227, 227, 227);
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1>{first_text}<span style="color: #FF6347;">{character_name}</span>?</h1>
                            </body>
                        </html>
                    """
        msg_box.setText(message_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self.configuration_characters.delete_character(character_name)

            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget == card_widget:
                    self.grid_layout.removeWidget(widget)
                    widget.deleteLater()
                    break

            self.cards = [card for card in self.cards if card != card_widget]

            asyncio.create_task(self.set_main_tab())

            if not self.cards:
                self.ui.stackedWidget.setCurrentIndex(0)

    def check_main_character_information(self, character_name):
        """
        Vertical Dashboard Design for Character Information.
        """
        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list", {})
        character_information = character_list.get(character_name, {})

        conversation_method = character_information.get("conversation_method", "Local LLM")
        character_avatar = character_information.get("character_avatar", "")
        if conversation_method == "Character AI":
            character_avatar = self.character_ai_client.get_from_cache(character_avatar)

        character_title = character_information.get("character_title", "")
        character_description = character_information.get("character_description", "")
        character_personality = character_information.get("character_personality", "")
        first_message = character_information.get("first_message", "")
        scenario = character_information.get("scenario", "")
        example_messages = character_information.get("example_messages", "")
        alternate_greetings = character_information.get("alternate_greetings", "")
        creator_notes = character_information.get("character_title", "")

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(1050, 750)

        base_font = QtGui.QFont()
        base_font.setFamily("Inter Tight SemiBold")
        base_font.setPointSize(10)
        base_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dialog.setFont(base_font)

        dialog.setStyleSheet("""
            QDialog { background-color: #161618; }
            QScrollBar:vertical { background-color: transparent; width: 12px; margin: 0px; }
            QScrollBar::handle:vertical { background-color: rgba(255, 255, 255, 0.15); border-radius: 6px; min-height: 40px; }
            QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(25, 25, 25, 20)
        main_layout.setSpacing(20)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(25)

        left_column = QWidget()
        left_column.setFixedWidth(280)
        left_column.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 15px;
            }
        """)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(15, 25, 15, 25)
        left_layout.setSpacing(15)

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

        name_font = QtGui.QFont()
        name_font.setFamily("Inter Tight SemiBold")
        name_font.setPointSize(16)
        name_font.setBold(True)
        name_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        name_edit = None
        if conversation_method != "Character AI":
            name_edit = QLineEdit(character_name)
            name_edit.setFont(name_font)
            name_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_edit.setStyleSheet("""
                QLineEdit { background: transparent; color: white; border: none; border-bottom: 2px solid rgba(255,255,255,0.1); padding: 5px; }
                QLineEdit:focus { border-bottom: 2px solid rgba(255,255,255,0.6); }
            """)
            left_layout.addWidget(name_edit)
        else:
            name_label = QLabel(character_name)
            name_label.setFont(name_font)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet("color: white; border: none; background: transparent;")
            left_layout.addWidget(name_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none; min-height: 1px; max-height: 1px; margin: 10px 0px;")
        left_layout.addWidget(separator)

        nav_buttons_group = []
        stacked_widget = QStackedWidget()
        stacked_widget.setStyleSheet("QWidget { background: transparent; border: none; }")

        def switch_page(index, btn):
            stacked_widget.setCurrentIndex(index)
            for b in nav_buttons_group:
                b.setStyleSheet(b.property("default_style"))
            btn.setStyleSheet(btn.property("active_style"))

        def create_nav_button(text, index):
            btn = QPushButton(text)
            btn.setFont(base_font)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setFixedHeight(45)
            
            default_style = """
                QPushButton { background-color: transparent; color: rgba(255,255,255,0.6); border: none; border-radius: 8px; text-align: left; padding-left: 15px; }
                QPushButton:hover { background-color: rgba(255,255,255,0.05); color: white; }
            """
            active_style = """
                QPushButton { background-color: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; text-align: left; padding-left: 15px; }
            """
            btn.setProperty("default_style", default_style)
            btn.setProperty("active_style", active_style)
            btn.setStyleSheet(default_style)
            btn.clicked.connect(lambda _, i=index, b=btn: switch_page(i, b))
            
            nav_buttons_group.append(btn)
            left_layout.addWidget(btn)
            return btn

        btn_settings_text = self.translations.get("btn_check_settings", "General Settings")
        btn_identity_text = self.translations.get("btn_check_identity", "Identity / Personality")
        btn_scenario_text = self.translations.get("btn_check_scenario", "Scenario / Greeting")
        btn_examples_text = self.translations.get("btn_check_examples", "Examples / Notes")
        btn_chats_text = self.translations.get("btn_check_chats", "Chat Manager / Export")

        btn_settings = create_nav_button(btn_settings_text, 0)
        btn_identity = create_nav_button(btn_identity_text, 1)
        btn_scenario = create_nav_button(btn_scenario_text, 2)
        btn_examples = create_nav_button(btn_examples_text, 3)
        btn_chats = create_nav_button(btn_chats_text, 4)

        btn_settings.setStyleSheet(btn_settings.property("active_style"))
        left_layout.addStretch()
        content_layout.addWidget(left_column)

        def create_page():
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(10, 0, 15, 10)
            content_layout.setSpacing(15)
            
            scroll.setWidget(content_widget)
            layout.addWidget(scroll)
            return page, content_layout

        def add_glass_text_edit(layout, label_text, content, placeholder=""):
            lbl_font = QtGui.QFont()
            lbl_font.setFamily("Inter Tight SemiBold")
            lbl_font.setPointSize(12)
            lbl_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

            lbl = QLabel(label_text)
            lbl.setFont(lbl_font)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); margin-bottom: 2px;")
            layout.addWidget(lbl)

            text_font = QtGui.QFont()
            text_font.setFamily("Inter Tight Medium")
            text_font.setPointSize(11)
            text_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

            text_edit = QTextEdit()
            text_edit.setFont(text_font)
            text_edit.setPlainText(str(content) if content else "")
            if placeholder: text_edit.setPlaceholderText(placeholder)
            if conversation_method == "Character AI": text_edit.setReadOnly(True)
            
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3); color: rgba(240, 240, 240, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 15px;
                }
                QTextEdit:focus { border: 1px solid rgba(255, 255, 255, 0.3); background-color: rgba(0, 0, 0, 0.4); }
            """)
            text_edit.setMinimumHeight(180)
            layout.addWidget(text_edit)
            return text_edit

        description_edit = None
        personality_edit = None
        first_message_edit = None
        scenario_edit = None
        example_messages_edit = None
        alternate_greetings_edit = None
        creator_notes_edit = None

        config_user = self.configuration_settings.load_configuration()
        user_data = config_user.get("user_data", {})

        page0, layout0 = create_page()
        
        combo_style = """
            QComboBox {
                background-color: rgba(0, 0, 0, 0.3); color: white;
                border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 10px 15px;
            }
            QComboBox:hover { border: 1px solid rgba(255, 255, 255, 0.3); }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: url(:/sowInterface/arrowDown.png); width: 12px; height: 12px; }
            QComboBox QAbstractItemView {
                background-color: #1e1e1e; color: white; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 8px; selection-background-color: rgba(255,255,255,0.1); outline: none;
            }
            QComboBox QAbstractItemView::item { padding: 10px; min-height: 25px; }
        """

        def create_combo_section(parent_layout, label_text, items, current_text, callback):
            lbl = QLabel(label_text)
            lbl.setFont(base_font)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); margin-top: 10px;")
            parent_layout.addWidget(lbl)

            combo = QtWidgets.QComboBox()
            combo.setFont(base_font)
            combo.setStyleSheet(combo_style)
            combo.setFixedHeight(45)
            combo.addItems(items)
            combo.setCurrentText(current_text)
            combo.currentTextChanged.connect(callback)
            parent_layout.addWidget(combo)
            return combo

        if conversation_method != "Character AI":
            create_combo_section(
                layout0, "Conversation Method", 
                ["Mistral AI", "OpenRouter", "Open AI", "Local LLM"], conversation_method,
                lambda txt: update_character_conversation_method(character_name, txt)
            )
            
            personas = list(user_data.get("personas", {}).keys())
            create_combo_section(
                layout0, "Persona", ["None"] + personas, 
                character_information.get("selected_persona", "None"),
                lambda txt: update_selected_persona(character_name, txt)
            )

            presets = list(user_data.get("presets", {}).keys())
            create_combo_section(
                layout0, "System Prompt Preset", ["By default"] + presets,
                character_information.get("selected_system_prompt_preset", "By default"),
                lambda txt: update_selected_system_prompt_preset(character_name, txt)
            )

            lorebooks = list(user_data.get("lorebooks", {}).keys())
            create_combo_section(
                layout0, "Lorebook", ["None"] + lorebooks,
                character_information.get("selected_lorebook", "None"),
                lambda txt: update_lorebook(character_name, txt)
            )
        else:
            lbl = QLabel("No advanced settings available for Character AI.")
            lbl.setFont(base_font)
            lbl.setStyleSheet("color: rgba(255,255,255,0.5);")
            layout0.addWidget(lbl)

        layout0.addStretch()
        stacked_widget.addWidget(page0)

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

        def update_lorebook(char_name, new_lorebook):
            try:
                c_data = self.configuration_characters.load_configuration()
                c_data["character_list"][char_name]["selected_lorebook"] = new_lorebook
                self.configuration_characters.save_configuration_edit(c_data)
            except Exception as e: print(e)

        page1, layout1 = create_page()
        description_edit = add_glass_text_edit(layout1, "Character Description", character_description, "Enter description")
        personality_edit = add_glass_text_edit(layout1, "Personality", character_personality, "Enter personality traits")
        stacked_widget.addWidget(page1)

        page2, layout2 = create_page()
        first_message_edit = add_glass_text_edit(layout2, "First Message", first_message, "Enter first message")
        scenario_edit = add_glass_text_edit(layout2, "Scenario", scenario, "Conversation scenario")
        stacked_widget.addWidget(page2)

        page3, layout3 = create_page()
        example_messages_edit = add_glass_text_edit(layout3, "Example Messages", example_messages, "Use <START> macro")
        alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
        alternate_greetings_edit = add_glass_text_edit(layout3, "Alternate Greetings", alt_greets_text, "Use <GREETING> macro")
        creator_notes_edit = add_glass_text_edit(layout3, "Creator Notes", creator_notes, "Any additional notes")
        stacked_widget.addWidget(page3)

        page4, layout4 = create_page()
        
        if conversation_method != "Character AI":
            export_card_lbl = QLabel("Character Card")
            export_card_lbl.setFont(base_font)
            export_card_lbl.setStyleSheet("color: rgba(255,255,255,0.85);")
            layout4.addWidget(export_card_lbl)

            export_card_btn = QPushButton(self.translations.get("export_card_button", "Export character as PNG"))
            export_card_btn.setFont(base_font)
            export_card_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            export_card_btn.setFixedHeight(45)
            export_card_btn.setStyleSheet("""
                QPushButton { background-color: rgba(255,255,255,0.05); color: white; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; }
                QPushButton:hover { background-color: rgba(255,255,255,0.1); }
            """)
            export_card_btn.clicked.connect(lambda: export_character_card_information(character_name))
            layout4.addWidget(export_card_btn)

            separator_chat = QFrame()
            separator_chat.setFrameShape(QFrame.Shape.HLine)
            separator_chat.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none; height: 1px; margin: 20px 0px;")
            layout4.addWidget(separator_chat)

            chat_manager_lbl = QLabel("Chat History Manager")
            chat_manager_lbl.setFont(base_font)
            chat_manager_lbl.setStyleSheet("color: rgba(255,255,255,0.85);")
            layout4.addWidget(chat_manager_lbl)

            chat_row = QHBoxLayout()
            chat_combobox = QtWidgets.QComboBox()
            chat_combobox.setFont(base_font)
            chat_combobox.setStyleSheet(combo_style)
            chat_combobox.setFixedHeight(45)

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

            icon_btn_style = """
                QPushButton { background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; }
                QPushButton:hover { background-color: rgba(255,255,255,0.1); }
            """
            
            def create_icon_btn(icon_path):
                btn = QPushButton()
                btn.setFixedSize(45, 45)
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                btn.setStyleSheet(icon_btn_style)
                icon = QtGui.QIcon()
                icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
                btn.setIcon(icon)
                return btn

            rename_button = create_icon_btn("app/gui/icons/edit.png")
            delete_button = create_icon_btn("app/gui/icons/bin.png")
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
                        reply = QMessageBox.question(None, "Conflict", "Overwrite existing chat?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if reply == QMessageBox.StandardButton.No:
                            chat_id = str(uuid.uuid4())
                            imported_chat["name"] += " (Imported)"
                    
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
                
                if self.show_confirmation_dialog("Delete chat", "Are you sure you want to delete this chat?"):
                    config = self.configuration_characters.load_configuration()
                    char_data = config["character_list"][character_name]
                    found_id = next((cid for cid, cinfo in char_data["chats"].items() if cinfo.get("name") == old_name), None)
                    
                    if found_id:
                        del char_data["chats"][found_id]
                        if char_data.get("current_chat") == found_id:
                            char_data["current_chat"] = list(char_data["chats"].keys())[0] if char_data["chats"] else None
                        self.configuration_characters.save_configuration_edit(config)
                        chat_combobox.removeItem(index)

            export_button.clicked.connect(export_chat)
            import_button.clicked.connect(import_chat)      
            rename_button.clicked.connect(rename_chat)
            if len(chats) > 1: delete_button.clicked.connect(delete_chat)
            chat_combobox.currentIndexChanged.connect(on_chat_selected)

            def export_character_card_information(character_name):
                try:
                    current_image_path = character_avatar
                    image = Image.open(current_image_path).convert("RGBA") if os.path.exists(current_image_path) else Image.open("app/gui/icons/export_card.png").convert("RGBA")

                    current_persona = self.configuration_settings.get_user_data("default_persona")
                    user_name = self.configuration_settings.get_user_data("personas").get(current_persona, {}).get("user_name", "User") if current_persona != "None" else "User"

                    char_data = {
                        "spec": "chara_card_v2", "spec_version": "2.0",
                        "data": {
                            'name': name_edit.text(), 'description': description_edit.toPlainText(),
                            'personality': personality_edit.toPlainText(), 'first_mes': first_message_edit.toPlainText(),
                            'scenario': scenario_edit.toPlainText(), 'mes_example': example_messages_edit.toPlainText(),
                            'creator_notes': creator_notes_edit.toPlainText(), 'character_version': "1.0.0",
                            'creator': user_name, 'tags': ["sow", "custom"], 'extensions': {},
                            'alternate_greetings': self.parse_alternate_greetings(alternate_greetings_edit.toPlainText().strip()),
                            'system_prompt': "", 'post_history_instructions': ""
                        }
                    }

                    b64_data = base64.b64encode(json.dumps(char_data, ensure_ascii=False).encode('utf-8')).decode('utf-8')
                    png_info = PngImagePlugin.PngInfo()
                    png_info.add_text("chara", b64_data.encode('utf-8'))

                    file_path, _ = QFileDialog.getSaveFileName(None, "Export Character Card", "", "PNG Images (*.png)")
                    if file_path: image.save(file_path, format="PNG", pnginfo=png_info)
                except Exception as e:
                    QMessageBox.critical(None, "Error", f"Couldn't export character card:\n{str(e)}")

        else:
            lbl = QLabel("Export and Chat Management is not available for Character AI.")
            lbl.setFont(base_font)
            lbl.setStyleSheet("color: rgba(255,255,255,0.5);")
            layout4.addWidget(lbl)

        layout4.addStretch()
        stacked_widget.addWidget(page4)

        content_layout.addWidget(stacked_widget)
        main_layout.addLayout(content_layout)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        button_layout.setSpacing(15)

        pill_button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05); color: white;
                border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.15); padding: 10px 30px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.12); border: 1px solid rgba(255, 255, 255, 0.3); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.02); color: rgba(255, 255, 255, 0.5); }
        """
        
        btn_font = QtGui.QFont()
        btn_font.setFamily("Inter Tight SemiBold")
        btn_font.setPointSize(11)
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        ok_button = QPushButton(self.translations.get("personas_editor_close", "Close"))
        ok_button.setFont(btn_font)
        ok_button.setStyleSheet(pill_button_style)
        ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_button.clicked.connect(dialog.close)
        button_layout.addWidget(ok_button)

        if conversation_method != "Character AI":
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"))
            save_button.setFont(btn_font)
            save_button.setStyleSheet(pill_button_style)
            save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            save_button.clicked.connect(lambda: self.save_changes_main_menu(
                conversation_method, character_name, name_edit, description_edit, 
                personality_edit, scenario_edit, first_message_edit, 
                example_messages_edit, alternate_greetings_edit, creator_notes_edit
            ))
            button_layout.addWidget(save_button)

        new_dialog_button = QPushButton(self.translations.get("character_edit_start_new_dialogue", "Start new dialogue"))
        new_dialog_button.setFont(btn_font)
        new_dialog_button.setStyleSheet(pill_button_style)
        new_dialog_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        new_dialog_button.clicked.connect(lambda: asyncio.create_task(
            self.start_new_dialog_main(
                dialog, conversation_method, character_name,
                name_edit if conversation_method != "Character AI" else character_name,
                description_edit if conversation_method != "Character AI" else None,
                personality_edit if conversation_method != "Character AI" else None,
                scenario_edit if conversation_method != "Character AI" else None,
                first_message_edit if conversation_method != "Character AI" else None,
                example_messages_edit if conversation_method != "Character AI" else None,
                alternate_greetings_edit if conversation_method != "Character AI" else None,
                creator_notes_edit if conversation_method != "Character AI" else None
            )
        ))
        button_layout.addWidget(new_dialog_button)

        main_layout.addLayout(button_layout)
        dialog.exec()

    def save_changes_main_menu(self, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Saves changes to the configuration file for the specified character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data["character_list"]

        if character_name in character_list:
            if conversation_method != "Character AI":
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
            else:
                pass

            configuration_data["character_list"] = character_list
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("character_edit_saved_2", "The changes were saved successfully!"), "success")
        else:
            self.show_toast(self.translations.get("character_edit_saved_error_2", "Character was not found in the configuration."), "error")
        
        asyncio.create_task(self.set_main_tab())
        
    async def start_new_dialog_main(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        title = self.translations.get("character_edit_start_new_dialogue", "Start new dialogue")
        message = self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue?")

        if not self.show_confirmation_dialog(title, message):
            return

        if conversation_method != "Character AI":
            chat_name, ok = QInputDialog.getText(
                dialog,
                self.translations.get("new_chat_title", "New Chat"),
                self.translations.get("new_chat_prompt", "Enter chat name:")
            )

            if not ok or not chat_name.strip():
                chat_name = self.translations.get("default_chat_name", "Default Chat")

        match conversation_method:
            case "Character AI":
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list", {})
                character_id = character_list[character_name]["character_id"]
                await self.character_ai_client.create_new_chat(character_id)

            case "Mistral AI" | "Local LLM" | "Open AI" | "OpenRouter":
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

        self.ui.stackedWidget.setCurrentIndex(1)

        self.show_toast(self.translations.get("character_edit_start_new_dialogue_success", "A new chat has been successfully started!"), "success")
        
        dialog.close()
        asyncio.create_task(self.set_main_tab())
        self.main_window.updateGeometry()
        QtCore.QTimer.singleShot(0, self.update_layout)

    def set_conversation_method_dialog(self):
        """
        Loads a dialog for selecting the conversation method.
        """
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle(self.translations.get("create_character_title", "Character Creation Selector"))
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        dialog.setWindowIcon(icon)

        dialog.setFixedSize(600, 450)

        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: #121212; 
                border: 1px solid #2A2A2A;
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QtGui.QColor(0, 0, 0, 150))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(25, 25, 25, 25)

        title = QLabel(self.translations.get("choose_ai_provider_title", "Choose AI Provider"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; border:none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel(self.translations.get("choose_ai_provider_subtitle", "Select the engine for generating responses"))
        subtitle.setStyleSheet("font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 15px; border:none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(12)

        methods = [
            ("OpenAI / Custom", self.translations.get("choose_ai_provider_openai", "Industry standard, requires API Key"), "app/gui/icons/openai.png", "CUSTOM"),
            ("Local LLM", self.translations.get("choose_ai_provider_local_llm", "Run models offline on your GPU"), "app/gui/icons/local_llm.png", "FREE"),
            ("Mistral AI", self.translations.get("choose_ai_provider_mistralai", "Fast and open source models via API"), "app/gui/icons/mistralai.png", "CLOUD"),
            ("Character AI", self.translations.get("choose_ai_provider_characterai", "Roleplay and entertainment focused AI"), "app/gui/icons/characterai.png", None),
            ("OpenRouter", self.translations.get("choose_ai_provider_openrouter", "Unified API for many providers"), "app/gui/icons/openrouter.png", "AGGREGATOR"),
        ]

        positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)]
        
        for i, (name, desc, icon, badge) in enumerate(methods):
            card = MethodCard(name, desc, icon, badge)
            card.clicked.connect(lambda n=name: self.on_method_selected(n, dialog))
            
            row, col = positions[i]
            grid.addWidget(card, row, col)

        layout.addLayout(grid)
        layout.addStretch()
        
        dialog.exec()

    def on_method_selected(self, method_name, dialog):
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

        if method_name:
            if method_name == "Character AI":
                self.ui.stackedWidget.setCurrentIndex(2)
                self.configuration_settings.update_main_setting("conversation_method", "Character AI")
            elif method_name == "Mistral AI":
                self.ui.stackedWidget.setCurrentIndex(3)
                self.configuration_settings.update_main_setting("conversation_method", "Mistral AI")
            elif method_name == "OpenAI / Custom":
                self.ui.stackedWidget.setCurrentIndex(3)
                self.configuration_settings.update_main_setting("conversation_method", "Open AI")
            elif method_name == "OpenRouter":
                self.ui.stackedWidget.setCurrentIndex(3)
                self.configuration_settings.update_main_setting("conversation_method", "OpenRouter")
            elif method_name == "Local LLM":
                self.ui.stackedWidget.setCurrentIndex(3)
                self.configuration_settings.update_main_setting("conversation_method", "Local LLM")

            dialog.accept()

    def get_add_character_dialog_stylesheet(self):
        return """
            QDialog {
                background-color: rgb(27,27,27);
                color: white;
                font-family: 'Inter Tight Medium';
            }
            QPushButton {
                background-color: #2c2f33;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton:pressed {
                background-color: #4a4a4a;
            }
            """
    ### SETUP MAIN TAB AND CREATE CHARACTER ============================================================

    ### SETUP COMBOBOXES AND OTHER=======================================================================
    def on_comboBox_conversation_method_changed(self, text):
        self.configuration_settings.update_main_setting("conversation_method", text)
        if text == "Character AI":
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write API value"))
        elif text == "OpenRouter":
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write API value"))
            self.initialize_openrouter_models()
        elif text == "Open AI":
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_base_api", "Write API value (Optional)"))
        else:
            self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write API value"))

    def load_audio_devices(self):
        input_device_index = self.configuration_settings.get_main_setting("input_device")
        output_device_index = self.configuration_settings.get_main_setting("output_device_combo_index")

        self.ui.comboBox_input_devices.clear()
        self.ui.comboBox_output_devices.clear()
        self.output_device_list = []

        # Input devices
        input_devices = QMediaDevices.audioInputs()
        for idx, device in enumerate(input_devices):
            self.ui.comboBox_input_devices.addItem(device.description(), userData=device)

        self.set_combobox_to_device(self.ui.comboBox_input_devices, input_device_index)

        # Output devices
        devices = sd.query_devices()
        host_apis = sd.query_hostapis()

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
    
    def initialize_openrouter_models(self):
        self.models = self.open_ai_client.load_openrouter_models()
        self.filtered_models = self.models[:]

        self.ui.lineEdit_search_openrouter_models.textChanged.connect(self.filter_models)
        self.ui.comboBox_openrouter_models.currentIndexChanged.connect(self.on_comboBox_openrouter_models_changed)

        self.load_openrouter_models()

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
            self.configuration_settings.update_main_setting("openrouter_model", selected_model_id)
    
    def on_comboBox_mode_translator_changed(self, index):
        self.configuration_settings.update_main_setting("translator_mode", index)

    def on_comboBox_translator_changed(self, index):
        self.configuration_settings.update_main_setting("translator", index)
        translator = self.configuration_settings.get_main_setting("translator")
        if translator == 0:
            self.ui.target_language_translator_label.hide()
            self.ui.comboBox_target_language_translator.hide()
            self.ui.mode_translator_label.hide()
            self.ui.comboBox_mode_translator.hide()
        else:
            self.ui.target_language_translator_label.show()
            self.ui.comboBox_target_language_translator.show()
            self.ui.mode_translator_label.show()
            self.ui.comboBox_mode_translator.show()

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
            self.ui.choose_llm_gpu_device_label.hide()
            self.ui.checkBox_enable_flash_attention.hide()
            self.ui.comboBox_llm_gpu_devices.hide()
        else:
            self.ui.choose_llm_gpu_device_label.show()
            self.ui.checkBox_enable_flash_attention.show()
            self.ui.comboBox_llm_gpu_devices.show()
    
    def on_comboBox_llm_gpu_devices_changed(self, index):
        self.configuration_settings.update_main_setting("llm_backend", index)

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

    def on_checkBox_enable_mlock_stateChanged(self):
        if self.ui.checkBox_enable_mlock.isChecked():
            self.configuration_settings.update_main_setting("mlock_status", True)
        else:
            self.configuration_settings.update_main_setting("mlock_status", False)
    
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
    
    def on_checkBox_enable_memory_stateChanged(self):
        if self.ui.checkBox_enable_memory.isChecked():
            self.configuration_settings.update_main_setting("smart_memory", True)
        else:
            self.configuration_settings.update_main_setting("smart_memory", False)
    
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
        self.ui.comboBox_mode_translator.setCurrentIndex(self.configuration_settings.get_main_setting("translator_mode"))

        llm_device = self.configuration_settings.get_main_setting("llm_device")
        if llm_device == 0:
            self.ui.choose_llm_gpu_device_label.hide()
            self.ui.comboBox_llm_gpu_devices.hide()
        else:
            self.ui.choose_llm_gpu_device_label.show()
            self.ui.comboBox_llm_gpu_devices.show()

        translator = self.configuration_settings.get_main_setting("translator")
        if translator == 0:
            self.ui.target_language_translator_label.hide()
            self.ui.comboBox_target_language_translator.hide()
            self.ui.mode_translator_label.hide()
            self.ui.comboBox_mode_translator.hide()
        else:
            self.ui.target_language_translator_label.show()
            self.ui.comboBox_target_language_translator.show()
            self.ui.mode_translator_label.show()
            self.ui.comboBox_mode_translator.show()

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
        
        smart_memory_state = self.configuration_settings.get_main_setting("smart_memory")
        if smart_memory_state == False:
            self.ui.checkBox_enable_memory.setChecked(False)
        else:
            self.ui.checkBox_enable_memory.setChecked(True)

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
        Entering an API token for the selected option when launching the program.
        """
        selected_conversation_method = self.configuration_settings.get_main_setting("conversation_method")
        if selected_conversation_method == "Character AI":
            api_token = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
            self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Mistral AI":
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

    def update_api_token(self):
        """
        Changing the API token to the selected option.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()
        if selected_conversation_method == "Character AI":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            self.ui.lineEdit_base_url_options.hide()
            self.ui.label_base_url.hide()
            self.ui.label_openai_model.hide()
            self.ui.lineEdit_openai_model.hide()
            self.ui.label_mistral_model.hide()
            self.ui.lineEdit_mistral_model.hide()
            self.ui.openrouter_models_options_label.hide()
            self.ui.lineEdit_search_openrouter_models.hide()
            self.ui.comboBox_openrouter_models.hide()
            api_token = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Mistral AI":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            self.ui.label_base_url.hide()
            self.ui.label_mistral_model.show()
            self.ui.lineEdit_mistral_model.show()
            self.ui.lineEdit_base_url_options.hide()
            self.ui.label_openai_model.hide()
            self.ui.lineEdit_openai_model.hide()
            self.ui.openrouter_models_options_label.hide()
            self.ui.lineEdit_search_openrouter_models.hide()
            self.ui.comboBox_openrouter_models.hide()
            api_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
            mistral_model_endpoint = self.configuration_settings.get_main_setting("mistral_model_endpoint")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
            if mistral_model_endpoint != self.ui.lineEdit_mistral_model.text():
                self.ui.lineEdit_mistral_model.setText(mistral_model_endpoint)
        elif selected_conversation_method == "Open AI":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            self.ui.label_base_url.show()
            self.ui.label_mistral_model.hide()
            self.ui.lineEdit_mistral_model.hide()
            self.ui.label_openai_model.show()
            self.ui.lineEdit_openai_model.show()
            self.ui.lineEdit_base_url_options.show()
            self.ui.openrouter_models_options_label.hide()
            self.ui.lineEdit_search_openrouter_models.hide()
            self.ui.comboBox_openrouter_models.hide()
            api_token = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
            custom_endpoint_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
            openai_model = self.configuration_settings.get_main_setting("openai_model") or ""
            if openai_model != self.ui.lineEdit_openai_model.text():
                self.ui.lineEdit_openai_model.setText(openai_model)
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
            if custom_endpoint_url != self.ui.lineEdit_base_url_options.text():
                self.ui.lineEdit_base_url_options.setText(custom_endpoint_url)
        elif selected_conversation_method == "OpenRouter":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            self.ui.label_base_url.hide()
            self.ui.label_mistral_model.hide()
            self.ui.lineEdit_mistral_model.hide()
            self.ui.label_openai_model.hide()
            self.ui.lineEdit_openai_model.hide()
            self.ui.lineEdit_base_url_options.hide()
            self.ui.openrouter_models_options_label.show()
            self.ui.lineEdit_search_openrouter_models.show()
            self.ui.comboBox_openrouter_models.show()
            api_token = self.configuration_api.get_token("OPENROUTER_API_TOKEN")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)

    def save_api_token_in_real_time(self):
        """
        Saving the API token to a configuration file in real time.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()
        if selected_conversation_method == "Character AI":
            method = "CHARACTER_AI_API_TOKEN"
        elif selected_conversation_method == "Mistral AI":
            method = "MISTRAL_AI_API_TOKEN"
        elif selected_conversation_method == "Open AI":
            method = "OPEN_AI_API_TOKEN"
        elif selected_conversation_method == "OpenRouter":
            method = "OPENROUTER_API_TOKEN"

        self.configuration_api.save_api_token(method, self.ui.lineEdit_api_token_options.text())

    def save_openai_model_in_real_time(self):
        self.configuration_settings.update_main_setting("openai_model", self.ui.lineEdit_openai_model.text().strip())

    def save_custom_url_in_real_time(self):
        self.configuration_api.save_api_token("CUSTOM_ENDPOINT_URL", self.ui.lineEdit_base_url_options.text())

    def save_mistral_model_endpoint_in_real_time(self):
        self.configuration_settings.update_main_setting("mistral_model_endpoint", self.ui.lineEdit_mistral_model.text())

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
        context_size = self.configuration_settings.get_main_setting("context_size")
        self.ui.context_size_horizontalSlider.setValue(context_size)
        self.ui.lineEdit_contextSize.setText(str(context_size))

    def save_context_size_in_real_time(self):
        context_size = self.ui.context_size_horizontalSlider.value()
        self.ui.lineEdit_contextSize.setText(str(context_size))
        self.configuration_settings.update_main_setting("context_size", context_size)
        
    def update_context_size_from_line_edit(self):
        try:
            text_value = self.ui.lineEdit_contextSize.text()
            context_size = int(text_value)

            min_value = self.ui.context_size_horizontalSlider.minimum()
            context_size = max(min_value, context_size)

            max_value = self.ui.context_size_horizontalSlider.maximum()
            if context_size > max_value:
                self.ui.lineEdit_contextSize.setText(str(context_size))
            else:
                self.ui.context_size_horizontalSlider.setValue(context_size)
                self.ui.lineEdit_contextSize.setText(str(context_size))
            
            self.configuration_settings.update_main_setting("context_size", context_size)

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

    def initialize_repeat_penalty_horizontalSlider(self):
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")
        repeat_penalty_int = int(round(repeat_penalty * 10))
        self.ui.repeat_penalty_horizontalSlider.setValue(repeat_penalty_int)
        self.ui.lineEdit_repeatPenalty.setText(f"{repeat_penalty:.1f}")

    def save_repeat_penalty_in_real_time(self):
        repeat_penalty = self.ui.repeat_penalty_horizontalSlider.value()
        scaled_value = repeat_penalty / 10.0
        self.configuration_settings.update_main_setting("repeat_penalty", scaled_value)
        self.ui.lineEdit_repeatPenalty.setText(f"{scaled_value:.1f}")
    
    def update_repeat_penalty_from_line_edit(self): 
        try:
            text_value = self.ui.lineEdit_repeatPenalty.text()
            repeat_penalty = float(text_value)

            min_value = self.ui.repeat_penalty_horizontalSlider.minimum() / 10.0
            max_value = self.ui.repeat_penalty_horizontalSlider.maximum() / 10.0
            repeat_penalty = max(min_value, min(max_value, repeat_penalty))
            
            scaled_value_int = int(round(repeat_penalty * 10))
            self.ui.repeat_penalty_horizontalSlider.setValue(scaled_value_int)
            self.ui.lineEdit_repeatPenalty.setText(f"{repeat_penalty:.1f}")
            self.configuration_settings.update_main_setting("repeat_penalty", repeat_penalty)

        except ValueError:
            current_value = self.ui.repeat_penalty_horizontalSlider.value() / 10.0
            self.ui.lineEdit_repeatPenalty.setText(f"{current_value:.1f}")

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
    
    def initialize_interval_summary(self):
        interval = self.configuration_settings.get_main_setting("interval_summary")
        self.ui.spinBox_summary_interval.setValue(interval)
    
    def save_interval_summary_in_real_time(self):
        interval = self.ui.spinBox_summary_interval.value()
        self.configuration_settings.update_main_setting("interval_summary", interval)

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
    ### SETUP OPTIONS ==================================================================================

    ### SETUP CHARACTER INFORMATION ====================================================================
    def import_character_avatar(self):
        """
        Opens a dialog box for selecting a character's avatar image and updates the interface.
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "Choose character's image", "", "Images (*.png *.jpg *.jpeg)")
            if file_path:
                icon = QtGui.QIcon(file_path)
                self.ui.pushButton_import_character_image.setIcon(icon)
                self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(64, 64))
                self.configuration_settings.update_user_data("current_character_image", file_path)
            else:
                logger.error("No file selected.")
                return None
        except Exception as e:
            logger.error(f"Error importing character image: {e}")
            return None

    def import_character_card(self):
        try:
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
                default_icon = QtGui.QPixmap("app/gui/icons/export_card.png").scaled(
                    self.ui.pushButton_import_character_image.size() - QtCore.QSize(8, 8),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                self.ui.pushButton_import_character_image.setIcon(QtGui.QIcon(default_icon))
            else:
                cached_image_path = self.save_image_to_cache(file_path)

                pixmap = QtGui.QPixmap(cached_image_path)
                scaled_pixmap = pixmap.scaled(
                    self.ui.pushButton_import_character_image.size() - QtCore.QSize(8, 8),
                    QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    QtCore.Qt.TransformationMode.SmoothTransformation
                )
                icon = QtGui.QIcon(scaled_pixmap)
                self.ui.pushButton_import_character_image.setIcon(icon)
                self.ui.pushButton_import_character_image.setIconSize(
                    self.ui.pushButton_import_character_image.size() - QtCore.QSize(8, 8)
                )

                self.configuration_settings.update_user_data("current_character_image", cached_image_path)
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

                character_book = data.get("character_book")
                if character_book:
                    book_name = character_book.get("name")
                    if not book_name or book_name.strip() == "":
                        book_name = f"Lore_{data.get('name', 'Unknown')}"

                    import_lorebook_text = self.translations.get("import_lorebook_text", f"This card contains an embedded lorebook '{book_name}'. Do you want to add it to your library?").format(book_name=book_name)
                    reply = QMessageBox.question(
                        None,
                        self.translations.get("lorebook_editor_import_lorebook", "Import Lorebook"),
                        import_lorebook_text,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )

                    if reply == QMessageBox.StandardButton.Yes:
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
                        QMessageBox.information(None, self.translations.get("lorebook_editor_import_success", "Import Success"), success_msg)
                        
                        self.ui.comboBox_lorebook_building.addItem(new_name)
                        self.ui.comboBox_lorebook_building.setCurrentText(new_name)

        except Exception as e:
            logger.error(f"Error importing character card: {e}")
            error_str = str(e)
            err_msg = self.translations.get("lorebook_editor_import_error_desc", "Failed to parse lorebook: {error}").format(error=error_str)
            QMessageBox.critical(None, self.translations.get("lorebook_editor_import_error", "Import Error"), err_msg)

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
                QMessageBox.warning(None, "Error", "Character name is required!")
                return

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
                    'extensions': {},
                    'alternate_greetings': self.parse_alternate_greetings(self.ui.textEdit_alternate_greetings.toPlainText()),
                    'system_prompt': "",
                    'post_history_instructions': ""
                }
            }

            selected_lorebook_name = self.ui.comboBox_lorebook_building.currentText()
            
            if selected_lorebook_name and selected_lorebook_name != "None":
                main_config = self.configuration_settings.load_configuration()
                all_lorebooks = main_config.get("user_data", {}).get("lorebooks", {})
                
                if selected_lorebook_name in all_lorebooks:
                    book_data = all_lorebooks[selected_lorebook_name]
                    char_data["data"]["character_book"] = book_data
                else:
                    logger.warning(f"Lorebook '{selected_lorebook_name}' selected but not found in database.")

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
            
            QMessageBox.information(None, "Success", f"Character card exported to {file_path}")

        except Exception as e:
            logger.error(f"Error exporting character card: {e}")
            QMessageBox.critical(None, "Export Error", f"Failed: {str(e)}")
    
    def clean_character_card(self):
        icon_import = QtGui.QIcon()
        icon_import.addPixmap(QtGui.QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.ui.pushButton_import_character_image.setIcon(icon_import)
        self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
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
        """
        Creates a dialog box for selecting the Text-To-Speech (TTS) method for the character.
        """
        current_text_to_speech = self.configuration_characters.get_character_data(character_name, "current_text_to_speech")
        
        character_ai_voice_name = self.configuration_characters.get_character_data(character_name, "voice_name")
        voice_type = self.configuration_characters.get_character_data(character_name, "voice_type")
        rvc_enabled = self.configuration_characters.get_character_data(character_name, "rvc_enabled")
        rvc_file = self.configuration_characters.get_character_data(character_name, "rvc_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("tts_selector_title", 'Text-To-Speech Selector'))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(500, 440)
        dialog.setMaximumSize(500, 440)

        dialog.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }

            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #cccccc;
                margin-bottom: 15px;
            }

            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                border: 2px solid #444444;
                border-radius: 8px;
                padding: 8px 10px;
            }

            QLineEdit:focus {
                border: 2px solid #555555;
            }

            QRadioButton {
                font-size: 14px;
                color: #ffffff;
                padding: 5px;
            }

            QRadioButton::indicator {
                border: 2px solid #444444;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                background-color: #333333;
            }

            QRadioButton::indicator:checked {
                background-color: #555555;
                border: 2px solid #555555;
            }
        """)

        main_layout = QVBoxLayout()

        title_label = QLabel(self.translations.get("tts_selector_title_label", 'Choose Text-To-Speech Method'))
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        combo_box = QtWidgets.QComboBox(dialog)
        combo_box.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.add_items_to_combo_box(conversation_method, combo_box)
        combo_box.currentTextChanged.connect(lambda: self.update_ui(combo_box.currentText(), stacked_widget))
        main_layout.addWidget(combo_box)

        stacked_widget = QStackedWidget(dialog)
        stacked_widget.addWidget(self.create_voice_nothing_widgets(character_name))
        stacked_widget.addWidget(self.create_character_ai_widgets(character_name, character_ai_voice_name))
        stacked_widget.addWidget(self.create_elevenlabs_widgets(character_name))
        stacked_widget.addWidget(self.create_xttsv2_widgets(character_name, voice_type, rvc_enabled, rvc_file))
        stacked_widget.addWidget(self.create_edge_tts_widgets(character_name, voice_type, rvc_enabled, rvc_file, stacked_widget))
        stacked_widget.addWidget(self.create_kokoro_widgets(character_name, voice_type, rvc_enabled, rvc_file))
        stacked_widget.addWidget(self.create_silero_widgets(character_name, voice_type, rvc_enabled, rvc_file))
        main_layout.addWidget(stacked_widget)

        self.set_initial_widget(current_text_to_speech, conversation_method, combo_box, stacked_widget)

        dialog.setLayout(main_layout)

        return dialog

    def add_items_to_combo_box(self, conversation_method, combo_box):
        if conversation_method == "Character AI":
            combo_box.addItem('Nothing')
            combo_box.addItem('Character AI')
            combo_box.addItem('ElevenLabs')
            combo_box.addItem('XTTSv2')
            combo_box.addItem('Edge TTS')
            combo_box.addItem('Kokoro')
            combo_box.addItem('Silero')
        elif conversation_method in ["Mistral AI", "Open AI", "OpenRouter", "Local LLM"]:
            combo_box.addItem('Nothing')
            combo_box.addItem('ElevenLabs')
            combo_box.addItem('XTTSv2')
            combo_box.addItem('Edge TTS')
            combo_box.addItem('Kokoro')
            combo_box.addItem('Silero')

    def set_initial_widget(self, current_text_to_speech, conversation_method, combo_box, stacked_widget):
        if conversation_method == "Character AI":
            stacked_widget.setCurrentIndex(0)
            combo_box.setCurrentText('Character AI')
            match current_text_to_speech:
                case "Nothing":
                    combo_box.setCurrentText("Nothing")
                case "Character AI":
                    combo_box.setCurrentText("Character AI")
                case "ElevenLabs":
                    combo_box.setCurrentText("ElevenLabs")
                case "XTTSv2":
                    combo_box.setCurrentText("XTTSv2")
                case "Edge TTS":
                    combo_box.setCurrentText("Edge TTS")
                case "Kokoro":
                    combo_box.setCurrentText("Kokoro")
                case "Silero":
                    combo_box.setCurrentText("Silero")
        elif conversation_method in ["Mistral AI", "Local LLM"]:
            stacked_widget.setCurrentIndex(1)
            combo_box.setCurrentText("ElevenLabs")
            match current_text_to_speech:
                case "Nothing":
                    combo_box.setCurrentText("Nothing")
                case "ElevenLabs":
                    combo_box.setCurrentText("ElevenLabs")
                case "XTTSv2":
                    combo_box.setCurrentText("XTTSv2")
                case "Edge TTS":
                    combo_box.setCurrentText("Edge TTS")
                case "Kokoro":
                    combo_box.setCurrentText("Kokoro")
                case "Silero":
                    combo_box.setCurrentText("Silero")

    def update_ui(self, selected_method, stacked_widget):
        if selected_method == "Nothing":
            stacked_widget.setCurrentIndex(0)
        elif selected_method == "Character AI":
            stacked_widget.setCurrentIndex(1)
        elif selected_method == "ElevenLabs":
            stacked_widget.setCurrentIndex(2)
        elif selected_method == "XTTSv2":
            stacked_widget.setCurrentIndex(3)
        elif selected_method == "Edge TTS":
            stacked_widget.setCurrentIndex(4)
        elif selected_method == "Kokoro":
            stacked_widget.setCurrentIndex(5)
        elif selected_method == "Silero":
            stacked_widget.setCurrentIndex(6)

    def create_voice_nothing_widgets(self, character_name):
        layout = QVBoxLayout()

        save_button = QPushButton(self.translations.get("tts_selector_save_button", 'Save Selection'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(save_button, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        def save_voice_mode_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

        save_button.clicked.connect(save_voice_mode_settings)

        widget = QWidget()
        widget.setLayout(layout)
        
        return widget

    def create_character_ai_widgets(self, character_name, character_ai_voice_name):
        layout = QVBoxLayout()

        if character_ai_voice_name:
            character_ai_label = QLabel(self.translations.get("tts_selector_character_ai", "Your character voice name is ") + character_ai_voice_name)
        else:
            character_ai_label = QLabel(self.translations.get("tts_selector_character_ai_2", 'Choose voice for your character'))
        
        character_ai_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        character_ai_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        character_ai_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(character_ai_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        voice_input = QtWidgets.QLineEdit()
        voice_input.setPlaceholderText(self.translations.get("tts_selector_character_ai_3", "Enter a voice name for the character"))
        layout.addWidget(voice_input)

        search_layout = QHBoxLayout()

        voice_combo = QtWidgets.QComboBox()
        voice_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        search_layout.addWidget(voice_combo)

        search_button = QPushButton(self.translations.get("tts_selector_character_ai_search", 'Search'))
        search_button.setFixedHeight(30)
        search_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        search_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        search_button.setFixedWidth(100)
        search_button.clicked.connect(lambda: self.search_character_voice(voice_combo, voice_input, character_name))
        search_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        listen_button = QPushButton(self.translations.get("tts_selector_character_ai_listen", 'Listen'))
        listen_button.setFixedHeight(35)
        listen_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        listen_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        listen_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        listen_button.clicked.connect(lambda: self.play_preview_voice(character_name))
        select_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select voice'))
        select_button.setFixedHeight(35)
        select_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_button.clicked.connect(lambda: self.select_voice("Character AI", character_name, voice_combo, None, mode="Choice"))

        save_button = QPushButton(self.translations.get("chat_save_message", 'Save'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.clicked.connect(lambda: self.select_voice("Character AI", character_name, voice_combo, None, mode="Save"))

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(listen_button)
        buttons_layout.addWidget(select_button)
        buttons_layout.addWidget(save_button)
        layout.addLayout(buttons_layout)

        widget = QWidget()
        widget.setLayout(layout)
        
        return widget

    def create_elevenlabs_widgets(self, character_name):
        layout = QVBoxLayout()

        elevenlabs_label = QLabel(self.translations.get("tts_selector_elevenlabs", 'Write your API Token from ElevenLabs'))
        elevenlabs_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        elevenlabs_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(elevenlabs_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        token_input = QtWidgets.QLineEdit()
        token_input.setPlaceholderText(self.translations.get("tts_selector_elevenlabs_2", 'Enter your ElevenLabs API token...'))
        layout.addWidget(token_input)

        elevenlabs_api = self.configuration_api.get_token("ELEVENLABS_API_TOKEN")
        if elevenlabs_api:
            token_input.setText(elevenlabs_api)

        voice_id_input = QtWidgets.QLineEdit()
        voice_id_input.setPlaceholderText(self.translations.get("tts_selector_elevenlabs_3", 'Enter Voice ID from ElevenLabs'))
        layout.addWidget(voice_id_input)

        elevenlabs_voice_id = self.configuration_characters.get_character_data(character_name, "elevenlabs_voice_id")
        if elevenlabs_voice_id:
            voice_id_input.setText(elevenlabs_voice_id)

        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select voice'))
        select_voice_button.setFixedHeight(35)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_voice_button.clicked.connect(lambda: self.select_voice("ElevenLabs", character_name, voice_id_input.text(), token_input.text()))
        layout.addWidget(select_voice_button)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_xttsv2_widgets(self, character_name, voice_type, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        layout = QVBoxLayout()

        xtts_label = QLabel(self.translations.get("tts_selector_xttsv2", 'Choose voice type for XTTSv2'))
        xtts_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        xtts_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(xtts_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        voice_type_combo = QtWidgets.QComboBox()
        voice_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        voice_type_combo.addItems([self.translations.get("tts_selector_xttsv2_male", "Male"), self.translations.get("tts_selector_xttsv2_female", "Female"), self.translations.get("tts_selector_xttsv2_calm_female", "Female Calm")])
        layout.addWidget(voice_type_combo)

        if voice_type:
            voice_type_combo.setCurrentText(voice_type)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        layout.addWidget(rvc_checkbox)

        if rvc_enabled:
            rvc_checkbox.setCheckable(rvc_enabled)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        rvc_file_combo.setEnabled(False)
        layout.addWidget(rvc_file_combo)

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

        def toggle_rvc_file_combo(checked):
            rvc_file_combo.setEnabled(checked)

        rvc_checkbox.stateChanged.connect(toggle_rvc_file_combo)

        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFixedHeight(35)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
                self.show_toast(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"), "error")
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    self.show_toast(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder, "error")
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "XTTSv2"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

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

        layout = QVBoxLayout()

        edge_tts_label = QLabel(self.translations.get("tts_selector_edge", 'Choose voice type for Edge TTS'))
        edge_tts_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        edge_tts_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(edge_tts_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        language_combo = QtWidgets.QComboBox()
        language_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        language_combo.addItems(["English", "Russian"])
        layout.addWidget(language_combo)

        voice_combo = QtWidgets.QComboBox()
        voice_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(voice_combo)

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
            if index == 4:
                asyncio.create_task(populate_voices())

        stacked_widget.currentChanged.connect(on_stacked_widget_changed)

        language_combo.currentIndexChanged.connect(lambda: asyncio.create_task(populate_voices()))

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        layout.addWidget(rvc_checkbox)

        if rvc_enabled:
            rvc_checkbox.setCheckable(rvc_enabled)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        rvc_file_combo.setEnabled(False)
        layout.addWidget(rvc_file_combo)

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

        def toggle_rvc_file_combo(checked):
            rvc_file_combo.setEnabled(checked)

        rvc_checkbox.stateChanged.connect(toggle_rvc_file_combo)

        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select voice'))
        select_voice_button.setFixedHeight(35)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
                self.show_toast(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"), "error")
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    self.show_toast(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder, "error")
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Edge TTS"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

        select_voice_button.clicked.connect(save_edge_tts_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_kokoro_widgets(self, character_name, voice_name, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        layout = QVBoxLayout()

        kokoro_label = QLabel(self.translations.get("tts_selector_kokoro", "Choose voice for Kokoro"))
        kokoro_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        kokoro_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(kokoro_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        voice_name_combo = QtWidgets.QComboBox()
        voice_name_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        voice_name_combo.addItems([
            "af_heart", "af_bella", "af_nicole", "af_aoede", 
            "af_kore", "af_sarah", "af_nova", "am_fenrir", 
            "am_michael", "am_puck", "bf_emma", "bf_isabella", 
            "bm_fable", "bm_george", "jf_alpha", "jf_gongitsune", 
            "jm_kumo", "zf_xiaobei", "zf_xiaoni", "zm_yunjian", "zm_yunxi"
        ])
        layout.addWidget(voice_name_combo)

        if voice_name:
            voice_name_combo.setCurrentText(voice_name)

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        layout.addWidget(rvc_checkbox)

        if rvc_enabled:
            rvc_checkbox.setCheckable(rvc_enabled)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        rvc_file_combo.setEnabled(False)
        layout.addWidget(rvc_file_combo)

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

        def toggle_rvc_file_combo(checked):
            rvc_file_combo.setEnabled(checked)

        rvc_checkbox.stateChanged.connect(toggle_rvc_file_combo)

        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFixedHeight(35)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
                self.show_toast(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"), "error")
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    self.show_toast(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder, "error")
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Kokoro"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

        select_voice_button.clicked.connect(save_kokoro_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_silero_widgets(self, character_name, voice_name, rvc_enabled, file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        layout = QVBoxLayout()

        silero_label = QLabel(self.translations.get("tts_selector_silero", "Choose voice for Silero"))
        silero_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        silero_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(silero_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        voice_name_combo = QtWidgets.QComboBox()
        voice_name_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        voice_name_combo.addItems([
            "aidar", "baya", "kseniya", "xenia", "eugene"
        ])
        layout.addWidget(voice_name_combo)

        if voice_name and voice_name in ["aidar", "baya", "kseniya", "xenia", "eugene"]:
            voice_name_combo.setCurrentText(voice_name)
        else:
            voice_name_combo.setCurrentText("xenia")

        rvc_checkbox = QtWidgets.QCheckBox(self.translations.get("tts_selector_enable_rvc", "Enable RVC"))
        layout.addWidget(rvc_checkbox)

        if rvc_enabled:
            rvc_checkbox.setChecked(rvc_enabled)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        rvc_file_combo.setEnabled(False)
        layout.addWidget(rvc_file_combo)

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

        def toggle_rvc_file_combo(checked):
            rvc_file_combo.setEnabled(checked)

        rvc_checkbox.stateChanged.connect(toggle_rvc_file_combo)

        select_voice_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select Voice'))
        select_voice_button.setFixedHeight(35)
        select_voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_voice_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(select_voice_button)

        def save_silero_settings():
            voice_type = voice_name_combo.currentText()
            rvc_enabled = rvc_checkbox.isChecked()
            rvc_folder = (
                os.path.join(RVC_DIR, rvc_file_combo.currentText())
                if rvc_enabled and rvc_file_combo.currentText() and rvc_file_combo.isEnabled()
                else None
            )

            if rvc_enabled and (not rvc_folder or "No folders found" in str(rvc_folder)):
                self.show_toast(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"), "error")
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = os.path.join(rvc_folder, pth_files[0])
                else:
                    self.show_toast(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder, "error")
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Silero"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

        select_voice_button.clicked.connect(save_silero_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def select_voice(self, tts_method, character_name, data, elevenlabs_api, mode=None):
        match tts_method:
            case "Character AI":
                voice_name = data.currentText()
                voice_id = data.currentData()
                configuration_data = self.configuration_characters.load_configuration()

                if mode == "Save":
                    voice_name = configuration_data["character_list"][character_name]["voice_name"]
                    if voice_name:
                        configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                        self.configuration_characters.save_configuration_edit(configuration_data)

                        self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")
                    else:
                        self.show_toast(self.translations.get("tts_selector_save_information_error", "Choose a voice for the character!"), "error")

                elif mode == "Choice":
                    if voice_id:
                        configuration_data["character_list"][character_name]["voice_name"] = voice_name
                        configuration_data["character_list"][character_name]["character_ai_voice_id"] = voice_id
                        configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                        self.configuration_characters.save_configuration_edit(configuration_data)

                        self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

            case "ElevenLabs":
                voice_id = data
                
                self.configuration_api.save_api_token("ELEVENLABS_API_TOKEN", elevenlabs_api)
                
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["elevenlabs_voice_id"] = voice_id
                configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                self.configuration_characters.save_configuration_edit(configuration_data)

                self.show_toast(self.translations.get("tts_selector_save_information", "Voice successfully saved!"), "success")

    def search_character_voice(self, combobox, voice_input, character_name):
        combobox.clear()
        voice_name = voice_input.text().strip()

        if not voice_name:
            self.show_toast(self.translations.get("tts_selector_error_2", "Please enter a valid voice name."), "error")
            return

        async def fetch_voices():
            try:
                voices = await self.character_ai_client.search_voices(voice_name)
                if voices:
                    for voice in voices:
                        combobox.addItem(voice.name, voice.voice_id)
                else:
                    self.show_toast(self.translations.get("tts_selector_error_4", "No voices found for the given name."), "error")
            except Exception as e:
                self.show_toast(self.translations.get("tts_selector_error_6", "Failed to fetch voices: ") + str(e), "error")

        asyncio.ensure_future(fetch_voices())

        def on_combobox_change():
            voice_id = combobox.currentData()
            if voice_id:
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["character_ai_preview_voice"] = voice_id
                self.configuration_characters.save_configuration_edit(configuration_data)

        combobox.currentIndexChanged.connect(on_combobox_change)

    def play_preview_voice(self, character_name):
        voice_preview_id = self.configuration_characters.get_character_data(character_name, "character_ai_preview_voice")

        async def play_voice():
            await self.character_ai_client.play_preview_voice(voice_preview_id)

        asyncio.ensure_future(play_voice())
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
        Creates a dialog box for selecting the Expressions method for the character.
        """
        current_sow_system_mode = self.configuration_characters.get_character_data(character_name, "current_sow_system_mode")
        expression_images_folder = self.configuration_characters.get_character_data(character_name, "expression_images_folder")
        live2d_model_folder = self.configuration_characters.get_character_data(character_name, "live2d_model_folder")
        vrm_model_file = self.configuration_characters.get_character_data(character_name, "vrm_model_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("expressions_selector_title", 'Expressions Selector'))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(500, 400)
        dialog.setMaximumSize(500, 400)

        dialog.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }

            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #cccccc;
                margin-bottom: 15px;
            }

            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                border: 2px solid #444444;
                border-radius: 8px;
                padding: 8px 10px;
            }

            QLineEdit:focus {
                border: 2px solid #555555;
            }

            QRadioButton {
                font-size: 14px;
                color: #ffffff;
                padding: 5px;
            }

            QRadioButton::indicator {
                border: 2px solid #444444;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                background-color: #333333;
            }

            QRadioButton::indicator:checked {
                background-color: #555555;
                border: 2px solid #555555;
            }
        """)

        main_layout = QVBoxLayout()

        title_label = QLabel(self.translations.get("expressions_selector_choose_method", 'Choose Expression Method'))
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        combo_box = QtWidgets.QComboBox(dialog)
        combo_box.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        combo_box.addItems(["Nothing", "Expressions Images", "Live2D Model", "VRM"])
        combo_box.currentTextChanged.connect(lambda: self.update_expressions_menu_ui(combo_box.currentText(), stacked_widget))
        main_layout.addWidget(combo_box)

        stacked_widget = QStackedWidget(dialog)
        stacked_widget.addWidget(self.create_nothing_widgets(character_name))
        stacked_widget.addWidget(self.create_expression_images_widgets(character_name, expression_images_folder))
        stacked_widget.addWidget(self.create_live2d_model_widgets(character_name, live2d_model_folder))
        stacked_widget.addWidget(self.create_vrm_model_widgets(character_name, vrm_model_file))

        main_layout.addWidget(stacked_widget)

        self.set_initial_expressions_widget(current_sow_system_mode, combo_box, stacked_widget)

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
        layout = QVBoxLayout()

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
        """)
        layout.addWidget(save_button, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        def save_expression_images_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            self.show_toast(self.translations.get("expressions_selector_mode_saved_body", "Expression mode successfully saved!"), "success")

        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_expression_images_widgets(self, character_name, expression_images_folder):
        EXP_DIR = os.path.join(os.getcwd(), "assets\\emotions\\images")
        
        layout = QVBoxLayout()

        expressions_image_label = QLabel(self.translations.get("expressions_selector_select_folder", 'Select an emotion folder'))
        expressions_image_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        expressions_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(expressions_image_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        expressions_folder_combo = QtWidgets.QComboBox()
        expressions_folder_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(expressions_folder_combo)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
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

            self.show_toast(self.translations.get("expressions_selector_foler_saved_body", "Expression folder successfully saved!"), "success")

        populate_expressions_images_folders()
        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_live2d_model_widgets(self, character_name, live2d_model_folder):
        LIVE2D_DIR = os.path.join(os.getcwd(), "assets\\emotions\\live2d")
        
        layout = QVBoxLayout()

        live2d_model_label = QLabel(self.translations.get("expressions_selector_select_folder_live2d", 'Select folder with Live2D model'))
        live2d_model_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        live2d_model_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(live2d_model_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        live2d_model_folder_combo = QtWidgets.QComboBox()
        live2d_model_folder_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(live2d_model_folder_combo)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
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

            self.show_toast(self.translations.get("expressions_selector_live2d_folder_saved_body", "Live2D folder successfully saved!"), "success")

        populate_live2d_model_folders()
        save_button.clicked.connect(save_live2d_model_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_vrm_model_widgets(self, character_name, vrm_model_file):
        VRM_DIR = os.path.join(os.getcwd(), "assets\\emotions\\vrm")
        
        layout = QVBoxLayout()

        vrm_model_label = QLabel(self.translations.get("expressions_selector_select_file_vrm", 'Select VRM model file'))
        vrm_model_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        vrm_model_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(vrm_model_label, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        vrm_model_file_combo = QtWidgets.QComboBox()
        vrm_model_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 2px solid #333;
                border-radius: 5px;
                padding: 5px;
                padding-left: 10px;
                selection-color: #ffffff;
                selection-background-color: #454545;
            }

            QComboBox:hover {
                border: 2px solid #444;
            }

            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #333;
                background-color: #2b2b2b;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }

            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                image: url(:/sowInterface/arrowDown.png);
            }

            QComboBox::down-arrow:hover {
                width: 12px;
                height: 12px;
            }

            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #e0e0e0;
                border: 1px solid rgb(70, 70, 70);
                border-radius: 6px;
                padding: 5px;
                outline: 0px;
                selection-color: #ffffff;
                selection-background-color: #8f8f8f;
            }

            QComboBox QAbstractItemView::item {
                border: none;
                height: 20px;
                padding: 4px 8px;
                border-radius: 4px;
            }

            QComboBox QAbstractItemView::item:hover {
                background-color: #5a5a5a;
                color: white;
            }

            QComboBox QAbstractItemView::item:selected {
                background-color: #454545;
                color: white;
                border-radius: 4px;
            }

            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #454545;
            }

            QScrollBar::handle:vertical:pressed {
                background-color: #424242;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(vrm_model_file_combo)

        save_button = QPushButton(self.translations.get("expressions_selector_save_button", 'Save Selection'))
        
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        save_button.setFixedHeight(35)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 10px;
                border: 1px solid #383838;
                padding: 0;
            }

            QPushButton:hover {
                background-color: #333333;
                border: 1px solid #404040;
            }

            QPushButton:pressed {
                background-color: #202020;
                color: #999999;
            }
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

            self.show_toast(self.translations.get("expressions_selector_vrm_file_saved_body", "VRM file successfully saved!"), "success")

        populate_vrm_model_file()
        save_button.clicked.connect(save_vrm_model_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget
    ### EXPRESSIONS DIALOG =============================================================================

    ### CHARACTERS GATEWAY =============================================================================
    async def open_characters_gateway(self):
        """
        Opens Characters Gateway and adjusts the behavior depending on the availability of an API token.
        """
        character_ai_api = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
        self.ui.stackedWidget_soul_gateway.setCurrentIndex(0)
        self.ui.stackedWidget_character_ai.setCurrentIndex(0)
        self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)

        available_api = bool(character_ai_api)

        try:
            self.ui.tabWidget_characters_gateway.currentChanged.disconnect()
        except TypeError:
            pass

        self.ui.tabWidget_characters_gateway.currentChanged.connect(
            lambda index: self.on_tab_changed(index, available_api)
        )

        asyncio.ensure_future(self.handle_tab_change(self.ui.tabWidget_characters_gateway.currentIndex(), available_api))
    
    def on_tab_changed(self, index, available_api):
        if self.is_loading:
            self.abort_loading = True

        self.is_loading = True
        self.abort_loading = False
        asyncio.ensure_future(self.handle_tab_change(index, available_api))

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

    @asyncSlot()
    async def handle_tab_change(self, current_tab_index, available_api):
        """
        Handles changing tabs in Characters Gateway.
        """
        self.abort_loading = False
    
        scroll_area_mapping = {
            "soul_gateway": self.ui.scrollArea_soul_gateway,
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_card_page": self.ui.scrollArea_character_card
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.soul_cards.clear()
        self.cai_cards.clear()
        self.gate_cards.clear()

        self.ui.stackedWidget.setCurrentIndex(4)
        
        match current_tab_index:
            case 0:  # Soul Gateway
                self.ui.stackedWidget_soul_gateway.setCurrentIndex(0)
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
                            await asyncio.sleep(0.05)

                    self.update_gate_layout("soul_gateway")

                except Exception as e:
                    logger.error(f"Error loading Soul Gateway: {e}")
            case 1:  # Character AI
                self.ui.stackedWidget_character_ai.setCurrentIndex(0)
                self.ui.label_nsfw.hide()
                self.ui.checkBox_enable_nsfw.hide()

                if self.cai_container:
                    self.cai_container.deleteLater()
                    self.cai_container = None
                
                self.cai_container = QWidget()
                self.cai_grid_layout = QtWidgets.QGridLayout(self.cai_container)
                self.cai_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.cai_grid_layout.setSpacing(10)

                self.ui.scrollArea_character_ai_page.setWidget(self.cai_container)

                if available_api:
                    recommended_data = await self.character_ai_client.fetch_recommended()
                    
                    async def process_character(character_information):
                        if self.abort_loading:
                            return
                
                        character_name = character_information.name
                        character_title = character_information.title
                        character_avatar = character_information.avatar
                        character_id = character_information.character_id
                        downloads = character_information.num_interactions
                        likes = None
                        
                        character_avatar_url = None
                        if character_avatar is not None:
                            try:
                                character_avatar_url = character_avatar.get_url()
                            except AttributeError:
                                logger.error(f"Avatar for {character_name} does not have a valid URL.")

                        avatar_path = None
                        if character_avatar_url:
                            try:
                                avatar_path = await self.character_ai_client.load_image(character_avatar_url)
                            except Exception as e:
                                logger.error(f"Error loading avatar for {character_name}: {e}")
                        else:
                            logger.error(f"No avatar found for {character_name}")

                        card_widget = CharacterCardCharactersGateway(
                            conversation_method="Character AI", character_author=None, character_name=character_name, 
                            character_avatar=avatar_path, character_title=character_title,
                            character_description=None, character_personality=None, scenario=None,
                            first_message=None, example_messages=None, alternate_greetings=None,
                            method=self.check_character_information
                        )
                        
                        character_widget = self.create_cai_character_card(
                            card_widget, character_name, character_title, avatar_path, 
                            downloads, likes, character_id
                        )

                        self.cai_cards.append(character_widget)
                        QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("character_ai"))
                    
                    BATCH_SIZE = 1
                    for i, character_info in enumerate(recommended_data):
                        if self.abort_loading:
                            break

                        await process_character(character_info)

                        if i % BATCH_SIZE == 0:
                            self.update_gate_layout("character_ai")
                            await asyncio.sleep(0.1)

                        await asyncio.sleep(0.01)

                    self.update_gate_layout("character_ai")
                else:
                    if not self.cai_container:
                        self.cai_container = QWidget()
                        self.cai_grid_layout = QtWidgets.QGridLayout(self.cai_container)
                        self.cai_grid_layout.setContentsMargins(0, 20, 20, 20)
                        self.cai_grid_layout.setSpacing(10)
                        self.ui.scrollArea_character_ai_page.setWidget(self.cai_container)

                    for i in reversed(range(self.cai_grid_layout.count())): 
                        self.cai_grid_layout.itemAt(i).widget().setParent(None)
                    
                    warning_label = QLabel(self.translations.get("characters_gateway_character_ai_error", "You don't have a token from Character AI"))
                    warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    font = QtGui.QFont()
                    font.setFamily("Inter Tight Medium")
                    font.setPointSize(14)
                    font.setBold(True)
                    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
                    warning_label.setFont(font)
                    warning_label.setWordWrap(True)

                    self.cai_grid_layout.addWidget(warning_label, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
            case 2:  # Chub AI
                self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
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
                    if self.abort_loading:
                        return
                
                    full_path = node.get('fullPath')
                    if full_path is None:
                        logger.debug(f"'fullPath' not found for character: {node['name']}")
                        return

                    (
                        character_name, character_title, character_avatar_url, downloads,
                        likes, total_tokens, character_personality, first_message,
                        character_tavern_personality, example_dialogs, character_scenario, alternate_greetings
                    ) = await self.character_card_client.get_character_information(full_path)
                        
                    avatar_path = None
                    if character_avatar_url:
                        try:
                            avatar_path = await self.character_ai_client.load_image_character_card(character_avatar_url)
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

                BATCH_SIZE = 1
                for i, node in enumerate(nodes[:50]):
                    if self.abort_loading:
                        break

                    await process_node(node)
                    
                    if i % BATCH_SIZE == 0:
                        self.update_gate_layout("chub_ai")
                        await asyncio.sleep(0.1)
                    
                    await asyncio.sleep(0.01)

                self.update_gate_layout("chub_ai")
        
        self.is_loading = False

    def create_cai_character_card(self, character_card, character_name, character_title, avatar_path, downloads, likes, character_id):
        character_card.downloads = downloads
        character_card.likes = likes

        add_to_cai_button = QtWidgets.QPushButton(self.translations.get("characters_gateway_cai_add", "Add to the list"))
        add_to_cai_button.setFixedHeight(20)
        add_to_cai_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_to_cai_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        add_to_cai_button.setFont(font)
        add_to_cai_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 6px;
                font-family: 'Inter Tight SemiBold';
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)
        add_to_cai_button.clicked.connect(lambda: self.add_character_from_cai_gateway_sync(character_id))
        
        character_card.action_panel_layout.addWidget(add_to_cai_button)

        return character_card

    def update_gate_layout(self, tab):
        """
        Updates the layout of character cards in the specified tab with adaptive margins.
        """
        match tab:
            case "soul_gateway":
                cards_list = self.soul_cards
                cards_layout = self.soul_gateway_grid_layout
                cards_container = self.soul_gateway_container
                scroll_area = self.ui.scrollArea_soul_gateway
            case "character_ai":
                cards_list = self.cai_cards
                cards_layout = self.cai_grid_layout
                cards_container = self.cai_container
                scroll_area = self.ui.scrollArea_character_ai_page
            case "chub_ai":
                cards_list = self.gate_cards
                cards_layout = self.gate_cards_grid_layout
                cards_container = self.gate_container
                scroll_area = self.ui.scrollArea_character_card

        while True:
            item = cards_layout.takeAt(0)
            if not item:
                break
            widget = item.widget()
            if widget and widget not in cards_list:
                widget.deleteLater()

        for i in reversed(range(cards_layout.columnCount())):
            cards_layout.setColumnMinimumWidth(i, 0)
            cards_layout.setColumnStretch(i, 0)

        viewport_width = scroll_area.viewport().width()
        current_margins = cards_layout.contentsMargins()
        spacing = 10
        vertical_spacing = 10
        card_width = 200
        card_height = 270

        cards_layout.setHorizontalSpacing(spacing)
        cards_layout.setVerticalSpacing(0)

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
        elif self.ui.scrollArea_character_ai_page.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("character_ai"))
        elif self.ui.scrollArea_character_card.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("chub_ai"))
        
    def create_soul_gateway_character_card(self, character_card, character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None):
        
        buttons_data = [
            ("app/gui/icons/mistralai.png", "Add to Mistral AI", "Mistral AI"),
            ("app/gui/icons/openai.png", "Add to Open AI", "Open AI"),
            ("app/gui/icons/openrouter.png", "Add to OpenRouter", "OpenRouter"),
            ("app/gui/icons/local_llm.png", "Add to Local LLM", "Local LLM"),
        ]

        character_card.action_panel_layout.addStretch()

        for icon_path, button_text, conversation_method in buttons_data:
            button = QtWidgets.QPushButton()
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            button.setFont(font)
            button.setFixedSize(32, 32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setToolTip(button_text)
            
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            button.setIconSize(QtCore.QSize(18, 18))
            button.setIcon(icon)
            
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 16px; 
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QToolTip {
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }
            """)
            button.clicked.connect(
                lambda _, cm=conversation_method: self.add_character_from_gateway(character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=character_book, conversation_method=cm)
            )
            character_card.action_panel_layout.addWidget(button)

        character_card.action_panel_layout.addStretch()

        return character_card

    def create_chub_character_card(self, character_card, character_name, character_title, avatar_path, downloads, likes, total_tokens, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings):
        
        character_card.downloads = downloads
        character_card.likes = likes
        character_card.total_tokens = total_tokens

        buttons_data = [
            ("app/gui/icons/mistralai.png", "Add to Mistral AI", "Mistral AI"),
            ("app/gui/icons/openai.png", "Add to Open AI", "Open AI"),
            ("app/gui/icons/openrouter.png", "Add to OpenRouter", "OpenRouter"),
            ("app/gui/icons/local_llm.png", "Add to Local LLM", "Local LLM"),
        ]

        character_card.action_panel_layout.addStretch()

        for icon_path, button_text, conversation_method in buttons_data:
            button = QtWidgets.QPushButton()
            font = QtGui.QFont()
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            button.setFont(font)
            button.setFixedSize(32, 32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setToolTip(button_text)
            
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            button.setIconSize(QtCore.QSize(18, 18))
            button.setIcon(icon)
            
            button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 16px; 
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.05);
                }
                QToolTip {
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }
            """)
            button.clicked.connect(
                lambda _, cm=conversation_method: self.add_character_from_gateway(
                    character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None, conversation_method=cm
                )
            )
            character_card.action_panel_layout.addWidget(button)

        character_card.action_panel_layout.addStretch()

        return character_card

    async def search_character(self):
        """
        Searches for characters based on the current tab.
        """
        character_name = self.ui.lineEdit_search_character.text()
        self.ui.lineEdit_search_character.clear()
        character_ai_api = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
        if character_ai_api:
            available_api = True
        else:
            available_api = False

        current_tab_index = self.ui.tabWidget_characters_gateway.currentIndex()

        scroll_area_mapping = {
            "soul_gateway_page": self.ui.scrollArea_soul_gateway,
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_card_page": self.ui.scrollArea_character_card
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.soul_cards.clear()
        self.cai_cards.clear()
        self.gate_cards.clear()

        match current_tab_index:
            case 0:  # Soul Gateway
                self.ui.stackedWidget_soul_gateway.setCurrentIndex(0)
                
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

                    filtered_characters = [
                        char for char in all_characters 
                        if character_name.lower() in char['name'].lower()
                    ]

                    for i, char_info in enumerate(filtered_characters):
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
                            conversation_method="Local LLM", 
                            character_author=char_card_author,
                            character_name=data.get("name", "Unknown"), 
                            character_avatar=temp_path, 
                            character_title=data.get("creator_notes", char_info.get("author", "Soul Artist")),
                            character_description=data.get("description", ""), 
                            character_personality=data.get("personality", ""), 
                            scenario=data.get("scenario", ""), 
                            first_message=data.get("first_mes", ""), 
                            example_messages=data.get("mes_example", ""), 
                            alternate_greetings=data.get("alternate_greetings", []),
                            method=self.check_character_information
                        )

                        character_widget = self.create_soul_gateway_character_card(
                            card_widget, data.get("name", "Unknown"), data.get("creator_notes", ""), temp_path, 
                            data.get("description", ""), data.get("first_mes", ""), data.get("personality", ""), 
                            data.get("mes_example", ""), data.get("scenario", ""), data.get("alternate_greetings", []), 
                            data.get("character_book")
                        )

                        self.soul_cards.append(character_widget)
                        
                        if i % 1 == 0:
                            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("soul_gateway"))
                            await asyncio.sleep(0.01)

                    self.update_gate_layout("soul_gateway")

                except Exception as e:
                    logger.error(f"Error searching Soul Gateway: {e}")
            case 1: # Character AI
                self.ui.stackedWidget_character_ai.setCurrentIndex(0)
                self.ui.label_nsfw.hide()
                self.ui.checkBox_enable_nsfw.hide()

                if self.cai_container:
                    self.cai_container.deleteLater()
                    self.cai_container = None
                
                self.cai_container = QWidget()
                self.cai_grid_layout = QtWidgets.QGridLayout(self.cai_container)
                self.cai_grid_layout.setContentsMargins(0, 20, 20, 20)
                self.cai_grid_layout.setSpacing(10)

                self.ui.scrollArea_character_ai_page.setWidget(self.cai_container)

                if available_api:
                    searched_characters = await self.character_ai_client.search_character(character_name)
                    
                    async def process_character(character_information):
                        character_name = character_information.name
                        character_title = character_information.title
                        character_avatar = character_information.avatar
                        character_id = character_information.character_id
                        downloads = character_information.num_interactions
                        likes = None
                        
                        character_avatar_url = None
                        if character_avatar is not None:
                            try:
                                character_avatar_url = character_avatar.get_url()
                            except AttributeError:
                                logger.error(f"Avatar for {character_name} does not have a valid URL.")

                        avatar_path = None
                        if character_avatar_url:
                            try:
                                avatar_path = await self.character_ai_client.load_image(character_avatar_url)
                            except Exception as e:
                                logger.error(f"Error loading avatar for {character_name}: {e}")
                        else:
                            logger.error(f"No avatar found for {character_name}")

                        card_widget = CharacterCardCharactersGateway(
                            conversation_method="Character AI", character_author=None, character_name=character_name, 
                            character_avatar=avatar_path, character_title=character_title,
                            character_description=None, character_personality=None, scenario=None,
                            first_message=None, example_messages=None, alternate_greetings=None,
                            method=self.check_character_information
                        )

                        character_widget = self.create_cai_character_card(
                            card_widget, character_name, character_title, avatar_path, 
                            downloads, likes, character_id
                        )

                        self.cai_cards.append(character_widget)
                        QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("character_ai"))

                    BATCH_SIZE = 1
                    for i, character_info in enumerate(searched_characters):
                        await process_character(character_info)

                        if i % BATCH_SIZE == 0:
                            self.update_gate_layout("character_ai")
                            await asyncio.sleep(0.1)

                        await asyncio.sleep(0.01)
                    
                    self.update_gate_layout("character_ai")
                else:
                    warning_label = QLabel(parent=self.ui.scrollAreaWidgetContents_character_ai)
                    warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    font = QtGui.QFont()
                    font.setFamily("Inter Tight Medium")
                    font.setPointSize(14)
                    font.setBold(True)
                    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
                    warning_label.setFont(font)
                    warning_label.setGeometry(QtCore.QRect(10, 220, 1020, 60))
                    warning_label.setText(self.translations.get("characters_gateway_character_ai_error", "You don't have a token from Character AI"))
            case 2: # Chub AI
                self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
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

                searched_characters = await self.character_card_client.search_character(character_name)
                nodes = searched_characters.get("data", {}).get("nodes", [])
                
                async def process_node(node):
                    full_path = node.get('fullPath')
                    if full_path is None:
                        logger.debug(f"'fullPath' not found for character: {node['name']}")
                        return

                    (
                        character_name, character_title, character_avatar_url, downloads,
                        likes, total_tokens, character_personality, first_message,
                        character_tavern_personality, example_dialogs, character_scenario, alternate_greetings
                    ) = await self.character_card_client.get_character_information(full_path)
                        
                    avatar_path = None
                    if character_avatar_url:
                        try:
                            avatar_path = await self.character_ai_client.load_image_character_card(character_avatar_url)
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

                BATCH_SIZE = 5
                for i, node in enumerate(nodes[:50]):
                    await process_node(node)
                    
                    if i % BATCH_SIZE == 0:
                        self.update_gate_layout("chub_ai")
                        await asyncio.sleep(0.1)
                    
                    await asyncio.sleep(0.01)

                self.update_gate_layout("chub_ai")

    def add_character_from_cai_gateway_sync(self, character_id):
        task = asyncio.create_task(self.add_character_from_cai_gateway(character_id))
        task.add_done_callback(self.on_add_character_from_cai_gateway_done)

    def on_add_character_from_cai_gateway_done(self, task):
        result = task.result()

        if result:
            character_name = result
            first_text = self.translations.get("add_character_text_1", "was successfully added!")
            second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
            message_box_information = QMessageBox()
            message_box_information.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: rgb(227, 227, 227);
                }
                QLabel {
                    color: rgb(227, 227, 227);
                }
            """)
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("add_character_title", "Character Information"))

            message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
            message_box_information.setText(message_text)
            message_box_information.exec()
        else:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: #e0e0e0;
                }
            """)
            message_box_information.setWindowTitle("Error")

            first_text = self.translations.get("add_character_text_3", "There was an error while adding the character.")
            second_text = self.translations.get("add_character_text_4", "Please try again.")
            message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #FF6347;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1>{first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
            message_box_information.setText(message_text)
            message_box_information.exec() 

    async def add_character_from_cai_gateway(self, character_id):
        try:
            character_name = await self.character_ai_client.create_character(character_id)
            return character_name
        except Exception as e:
            logger.error(f"Error adding character: {e}")
            return None

    def add_character_from_gateway(self, character_name, character_title, character_avatar_directory, character_personality, character_first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, character_book=None, conversation_method=None):
        character_configuration = self.configuration_characters.load_configuration()
        character_list = character_configuration["character_list"]

        if character_name in character_list:
            suffix = 1
            while f"{character_name}_{suffix}" in character_list:
                suffix += 1
            suggested_name = f"{character_name}_{suffix}"

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: rgb(227, 227, 227);
                }
                QLabel {
                    color: rgb(227, 227, 227);
                }
            """)
            message_box_information.setWindowTitle(self.translations.get("duplicate_character_error_title", "Duplicate Character"))

            message_text = f"""
                <html>
                    <head>
                        <style>
                            body {{
                                background-color: #2b2b2b;
                            }}
                            h1 {{
                                color: rgb(227, 227, 227);
                                font-family: "Segoe UI", Arial, sans-serif;
                                font-size: 20px;
                            }}
                            p {{
                                color: rgb(227, 227, 227);
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                font-size: 14px;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>{self.translations.get("duplicate_character_error", "A character with this name already exists. A number will be added to the character's name.")}</h1>
                    </body>
                </html>
            """
            message_box_information.setText(message_text)
            message_box_information.exec()

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
                
                reply = QMessageBox.question(
                    None,
                    self.translations.get("lorebook_editor_import_lorebook", "Import Lorebook"),
                    import_lorebook_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
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
                        "Lorebook '{new_name}' imported with {count} entries."
                    ).format(new_name=new_name, count=count_val)
                    QMessageBox.information(None, self.translations.get("lorebook_editor_import_success", "Import Success"), success_msg)
                    
                    selected_lorebook_name = new_name

            except Exception as e:
                logger.error(f"Error importing lorebook from gateway: {e}")
                error_str = str(e)
                err_msg = self.translations.get("lorebook_editor_import_error_desc", "Failed to parse lorebook: {error}").format(error=error_str)
                QMessageBox.critical(None, self.translations.get("lorebook_editor_import_error", "Import Error"), err_msg)

        match conversation_method:
            case "Mistral AI":
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
                        conversation_method="Mistral AI"
                    )
                    first_text = self.translations.get("add_character_text_1", "was successfully added!")
                    second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowTitle(self.translations.get("add_character_title", "Character Information"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    logger.error(f"Error adding character: {e}")
                    return None
            case "Open AI":
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
                        conversation_method="Open AI"
                    )
                    first_text = self.translations.get("add_character_text_1", "was successfully added!")
                    second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowTitle(self.translations.get("add_character_title", "Character Information"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    logger.error(f"Error adding character: {e}")
                    return None
            case "OpenRouter":
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
                        conversation_method="OpenRouter"
                    )
                    first_text = self.translations.get("add_character_text_1", "was successfully added!")
                    second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("add_character_title", "Character Information"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    logger.error(f"Error adding character: {e}")
                    return None
            case "Local LLM":
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
                        conversation_method="Local LLM"
                    )
                    first_text = self.translations.get("add_character_text_1", "was successfully added!")
                    second_text = self.translations.get("add_character_text_2", "You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                        }
                    """)
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("add_character_title", "Character Information"))

                    message_text = f"""
                        <html>
                            <head>
                                <style>
                                    body {{
                                        background-color: #2b2b2b;
                                    }}
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: "Segoe UI", Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: rgb(227, 227, 227);
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color: rgb(227, 227, 227);">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    logger.error(f"Error adding character: {e}")
                    return None
   
    def check_character_information(self, conversation_method, character_name, character_avatar, character_title, character_description, character_personality, scenario, first_message, example_messages, alternate_greetings):
        """
        Opens a dialog to view character information.
        """
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(800, 650)

        font = QtGui.QFont()
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    
        dialog.setStyleSheet("""
            QDialog {
                background-color: #161618;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: rgba(255, 255, 255, 0.02);
                border-radius: 12px;
            }
            QTabBar::tab {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.5);
                padding: 10px 20px;
                margin-right: 4px;
                margin-bottom: 8px;
                border-radius: 8px;
                font-family: "Inter Tight SemiBold";
                font-size: 14px;
            }
            QTabBar::tab:hover {
                background: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.9);
            }
            QTabBar::tab:selected {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.15);
                min-height: 40px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(25, 25, 25, 20)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.setSpacing(20)

        avatar_size = 90
        avatar_label = QLabel(dialog)
        
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
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        avatar_label.setGraphicsEffect(shadow)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        name_label = QLabel(character_name, dialog)
        name_label.setFont(font)
        name_label.setStyleSheet("color: #FFFFFF; font-family: 'Inter Tight SemiBold'; font-size: 26px; font-weight: bold; background: transparent;")
        
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

        subtitle_label = QLabel(short_title, dialog)
        subtitle_label.setFont(font)
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-family: 'Inter Tight Medium'; font-size: 14px; background: transparent;")

        info_layout.addWidget(name_label)
        info_layout.addWidget(subtitle_label)

        header_layout.addWidget(avatar_label)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        def add_glass_section(layout, title, content):
            if not content: return 
            
            lbl = QLabel(title)
            lbl.setFont(font)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); font-family: 'Inter Tight SemiBold'; font-size: 15px; margin-top: 12px; margin-bottom: 2px;")
            layout.addWidget(lbl)

            text_edit = QTextEdit()
            text_edit.setFont(font)
            text_edit.setPlainText(str(content))
            text_edit.setReadOnly(True)
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.25);
                    color: rgba(240, 240, 240, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                    padding: 14px;
                    font-family: 'Inter Tight Medium';
                    font-size: 14px;
                    line-height: 1.6;
                }
                QTextEdit:focus {
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    background-color: rgba(0, 0, 0, 0.35);
                }
            """)
            
            text_edit.setMinimumHeight(120)
            layout.addWidget(text_edit)

        def create_scrollable_tab():
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(0, 0, 0, 0)
            
            scroll = QScrollArea()
            scroll.setFont(font)
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(15, 5, 15, 20)
            content_layout.setSpacing(8)
            
            scroll.setWidget(content_widget)
            layout.addWidget(scroll)
            return tab, content_layout

        tabs = QtWidgets.QTabWidget(dialog)
        tabs.setFont(font)
        main_layout.addWidget(tabs)

        tab_general_info_text = self.translations.get("btn_general_info_text", "General Info")
        tab_identity_text = self.translations.get("btn_identity_text", "Identity")
        tab_scenario_text = self.translations.get("btn_scenario_text", "Scenario")
        tab_examples_text = self.translations.get("btn_examples_text", "Examples")
        tab_creator_notes_text = self.translations.get("btn_creator_notes_text", "Creator Notes")

        if conversation_method == "Character AI":
            tab_cai, layout_cai = create_scrollable_tab()
            add_glass_section(layout_cai, self.translations.get("creator_notes_label", "Full Notes"), character_title)
            tabs.addTab(tab_cai, tab_general_info_text)
        else:
            # Identity
            tab_identity, layout_id = create_scrollable_tab()
            add_glass_section(layout_id, self.translations.get("character_edit_description", "Description"), character_description)
            add_glass_section(layout_id, self.translations.get("character_edit_personality", "Personality"), character_personality)
            tabs.addTab(tab_identity, tab_identity_text)

            # Scenario
            tab_scenario, layout_sc = create_scrollable_tab()
            add_glass_section(layout_sc, self.translations.get("character_edit_first_message", "First Message"), first_message)
            add_glass_section(layout_sc, self.translations.get("scenario", "Scenario"), scenario)
            tabs.addTab(tab_scenario, tab_scenario_text)

            # Examples
            tab_examples, layout_ex = create_scrollable_tab()
            add_glass_section(layout_ex, self.translations.get("example_messages_title", "Example Messages"), example_messages)
            alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
            add_glass_section(layout_ex, self.translations.get("alternate_greetings_label", "Alternate Greetings"), alt_greets_text)
            tabs.addTab(tab_examples, tab_examples_text)

            # Creator Notes
            if raw_title and len(raw_title) > max_subtitle_length:
                tab_notes, layout_notes = create_scrollable_tab()
                add_glass_section(layout_notes, self.translations.get("creator_info_title", "Full Creator Notes"), character_title)
                tabs.addTab(tab_notes, tab_creator_notes_text)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(button_layout)

        dialog.exec()
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

        models_dir = "assets\\local_llm"
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

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
        if hasattr(self, 'local_ai_client') and self.local_ai_client is not None:
            is_server_running = getattr(self.local_ai_client, 'model_loaded', False)
        
        for name, path, size in sorted_files:
            widget = ModelListItemWidget(
                model_name=name,
                file_size_bytes=size,
                full_path=path,
                refresh_method=self.show_my_models,
                launch_server_method=self.on_pushButton_launch_server_clicked,
                stop_server_method=self.local_ai_client.on_shutdown_button_clicked,
                ui=self.ui,
                parent=self.ui.listWidget_models_hub,
                is_server_running=is_server_running
            )
            item = QtWidgets.QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.ui.listWidget_models_hub.addItem(item)
            self.ui.listWidget_models_hub.setItemWidget(item, widget)

    def show_recommended_models(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
        self.stop_search_worker()
        if hasattr(self, 'model_information_widget') and self.model_information_widget is not None:
            self.model_information_widget.setParent(None)
            self.model_information_widget.deleteLater()
            self.model_information_widget = None
        self.ui.listWidget_models_hub.clear()
        
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
        shadow.setBlurRadius(40)
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
        shadow.setBlurRadius(40)
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
            QMessageBox.information(parent, "No files", "There are no .gguf files in this repository.")
            return

        dialog = FileSelectorDialog(files, download_button_translation=self.translations.get("button_download_model", " Download model"), model_id=model_id)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_file = dialog.selected_file
            self.start_download(selected_file)

    def start_download(self, filename):
        self.download_worker = FileDownloader(self.selected_model, filename)
        self.download_worker.finished.connect(self.on_download_complete)
        self.download_worker.error.connect(self.show_error)
        self.download_worker.start()

    def on_download_complete(self, path):
        parent = self.main_window if hasattr(self, "main_window") else None
        QMessageBox.information(parent, "The model has been downloaded.", f"Path:\n{path}")

    def show_error(self, message):
        parent = self.main_window if hasattr(self, "main_window") else None
        QMessageBox.critical(parent, "Error", message)
    ### MODELS HUB =====================================================================================

    ### IMPLEMENTATION OF CHAT WITH CHARACTER =====================================================================
    async def open_chat(self, character_name: str) -> None:
        """
        Opens a chat tab with a selected character with certain settings based on the character's data.
        """
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setContentsMargins(0, 0, 0, 0)
        self.chat_container.setSpacing(5)
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background: transparent;")
        self.chat_widget.setLayout(self.chat_container)
        self.ui.scrollArea_chat.setWidget(self.chat_widget)
        self.ui.scrollArea_chat.setWidgetResizable(True)

        # --- General settings ---
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        model_background_type = self.configuration_settings.get_main_setting("model_background_type")
        model_background_color = self.configuration_settings.get_main_setting("model_background_color")
        model_background_image = self.configuration_settings.get_main_setting("model_background_image")

        # --- Character configuration ---
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info.get("conversation_method")

        self.current_active_character = character_name
        
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
        
        self.messages = {}
        self.message_order = []
        
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")
        if conversation_method != "Character AI":
            self.ui.pushButton_author_notes.show()
            self.ui.pushButton_summary.show()
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            self.ui.pushButton_author_notes.hide()
            self.ui.pushButton_summary.hide()
            current_emotion = character_info["current_emotion"]

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        if conversation_method == "Character AI":
            character_id = character_info.get("character_id")
            chat_id = character_info.get("chat_id")
            character_avatar_url = character_info.get("character_avatar")

            voice_name = character_info.get("voice_name")
            character_ai_voice_id = character_info.get("character_ai_voice_id")
            
        elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
        voice_type = character_info.get("voice_type")
        rvc_enabled = character_info.get("rvc_enabled")
        rvc_file = character_info.get("rvc_file")
        
        if conversation_method == "Local LLM":
            local_llm = self.configuration_settings.get_main_setting("local_llm")
            if local_llm is None:
                self.show_toast(self.translations.get("llm_error_body", "Choose Local LLM in the options."), "error")
                return

        personas_data = self.configuration_settings.get_user_data("personas")
        current_persona = character_info.get("selected_persona")
        if current_persona == "None" or current_persona is None:
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
        if conversation_method == "Character AI":
            self.ui.character_description_chat.setText(character_title)
        else:
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

                    self.expression_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                        border: 1px solid rgb(35, 35, 40);
                        
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.expression_widget.setStyleSheet(f"""
                        background-color: rgb(27, 27, 27);
                        border-image: url({model_background_image}); 
                    """)
            elif current_sow_system_mode == "Expressions Images":
                self.expression_widget.setMinimumSize(QtCore.QSize(320, 0))
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

                    self.expression_widget.setStyleSheet(f"""
                        background-color: {css_background}; 
                    """)
                elif model_background_type == 1:
                    model_background_image = model_background_image.replace("\\", "/")

                    self.expression_widget.setStyleSheet(f"""
                        background-color: rgb(27, 27, 27);
                        border-image: url({model_background_image}); 
                    """)
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
                self.expression_image_label = QtWidgets.QLabel(parent=self.expression_image_page)
                self.expression_image_label.setText("")
                self.expression_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.expression_image_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
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

                self.vrm_webview.settings().setAttribute(
                    self.vrm_webview.settings().WebAttribute.WebGLEnabled, True
                )
                self.vrm_webview.settings().setAttribute(
                    self.vrm_webview.settings().WebAttribute.Accelerated2dCanvasEnabled, True
                )

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
                        logger.error("Error loading page")

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

        if chat_background != "None":
            chat_background = chat_background.replace("\\", "/")
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    border-image: url({chat_background}) 0 0 0 0 stretch stretch;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                    border-top-right-radius: 10px;
                    border-top-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                    border-bottom-left-radius: 10px;
                }}
                QScrollBar:vertical {{
                    width: 0px;
                    background: transparent;
                }}
                QScrollBar::handle:vertical {{
                    background: transparent;
                }}
                QScrollBar::sub-page:vertical {{
                    background: none;
                    border: none;
                }}
                QScrollBar:horizontal {{
                    background-color: #2b2b2b;
                    height: 10px;
                    border-radius: 5px;
                }}
                QScrollBar::handle:horizontal {{
                    background-color: #383838;
                    width: 10px;
                    border-radius: 3px;
                    margin: 2px;
                }}
                QScrollBar::handle:horizontal:hover {{
                    background-color: #454545;
                }}
                QScrollBar::handle:horizontal:pressed {{
                    background-color: #424242;
                }}
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                    border: none;
                    background: none;
                }}
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                    background: none;
                }}
            """)
        else:
            self.ui.scrollArea_chat.setStyleSheet("""
                QScrollArea {
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                    border-top-right-radius: 10px;
                    border-top-left-radius: 10px;
                    border-bottom-right-radius: 10px;
                    border-bottom-left-radius: 10px;
                }
                QScrollBar:vertical {
                    width: 0px;
                    background: transparent;
                }
                QScrollBar::handle:vertical {
                    background: transparent;
                }
                QScrollBar::sub-page:vertical {
                    background: none;
                    border: none;
                }
                QScrollBar:horizontal {
                    background-color: #2b2b2b;
                    height: 10px;
                    border-radius: 5px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #383838;
                    width: 10px;
                    border-radius: 3px;
                    margin: 2px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #454545;
                }
                QScrollBar::handle:horizontal:pressed {
                    background-color: #424242;
                }
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    border: none;
                    background: none;
                }
                QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                    background: none;
                }
            """)

        match conversation_method:
            case "Character AI":
                """
                Handles the setup for a Character AI-based conversation.
                """
                await self.character_ai_client.fetch_chat(
                            chat_id, character_name, character_id, character_avatar_url, character_title,
                            character_description, character_personality, first_message, current_text_to_speech,
                            voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                            rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                            vrm_model_file, conversation_method, current_emotion
                )

                character_avatar = self.character_ai_client.get_from_cache(character_avatar_url)
                self.draw_circle_avatar(character_avatar)

                self.ui.stackedWidget.setCurrentIndex(6)

                self.ui.pushButton_more.clicked.connect(
                    lambda: self.open_more_button(
                        conversation_method, 
                        character_name, 
                        character_avatar
                    )
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

            case "Mistral AI" | "Open AI" | "OpenRouter":
                """
                Handles the setup for a Mistral AI-based, OpenAI, OpenRouter conversation.
                """
                self.draw_circle_avatar(character_avatar)

                self.ui.stackedWidget.setCurrentIndex(6)

                self.ui.pushButton_more.clicked.connect(
                    lambda: self.open_more_button(
                        conversation_method, 
                        character_name,
                        character_avatar
                    )
                )

                self.ui.pushButton_summary.clicked.connect(lambda: self.open_summary_editor(character_name, conversation_method))

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

            case "Local LLM":
                """
                Handles the setup for a Local LLM-based conversation.
                """     
                self.draw_circle_avatar(character_avatar)

                self.ui.stackedWidget.setCurrentIndex(6)

                self.ui.pushButton_more.clicked.connect(
                    lambda: self.open_more_button(
                        conversation_method, 
                        character_name,
                        character_avatar
                    )
                )

                self.ui.pushButton_summary.clicked.connect(lambda: self.open_summary_editor(character_name, conversation_method))

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

        if conversation_method == "Character AI":
            await self.first_render_cai_messages(character_name)
        else:
            await self.first_render_messages(character_name)
        
        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))
        
    def draw_circle_avatar(self, avatar_path, current_sow_system_mode="Nothing"):
        """
        Draws a character's avatar as a perfect circle without distortion.
        """
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

    def open_more_button(self, conversation_method, character_name, character_avatar):
        """
        Opens a dialog for editing character information
        """
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(850, 700) 
        
        base_font = QtGui.QFont()
        base_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dialog.setFont(base_font)

        dialog.setStyleSheet("""
            QDialog {
                background-color: #161618;
            }
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: rgba(255, 255, 255, 0.02);
                border-radius: 12px;
            }
            QTabBar::tab {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.5);
                padding: 10px 20px;
                margin-right: 4px;
                margin-bottom: 8px;
                border-radius: 8px;
                font-family: "Inter Tight SemiBold";
                font-size: 14px;
            }
            QTabBar::tab:hover {
                background: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.9);
            }
            QTabBar::tab:selected {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.15);
                min-height: 40px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        character_data = self.configuration_characters.load_configuration()
        if "character_list" not in character_data or character_name not in character_data["character_list"]:
            print(f"Character '{character_name}' not found in the configuration.")
            return

        character_information = character_data["character_list"][character_name]
        character_title = character_information.get("character_title", "")
        character_description = character_information.get("character_description", "")
        character_personality = character_information.get("character_personality", "")
        first_message = character_information.get("first_message", "")
        scenario = character_information.get("scenario", "")
        example_messages = character_information.get("example_messages", "")
        alternate_greetings = character_information.get("alternate_greetings", "")
        creator_notes = character_information.get("character_title", "")

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(25, 25, 25, 20)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.setSpacing(20)

        avatar_size = 90
        avatar_label = QLabel(dialog)
        
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
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        avatar_label.setGraphicsEffect(shadow)
        header_layout.addWidget(avatar_label)

        title_font = QtGui.QFont()
        title_font.setFamily("Inter Tight SemiBold")
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        name_edit = None
        if conversation_method != "Character AI":
            name_edit = QLineEdit(character_name, dialog)
            name_edit.setFont(title_font)
            name_edit.setStyleSheet("""
                QLineEdit {
                    background-color: transparent;
                    color: #FFFFFF;
                    border: 1px solid transparent;
                    border-bottom: 2px solid rgba(255, 255, 255, 0.2);
                    padding: 4px;
                }
                QLineEdit:focus {
                    background-color: rgba(0, 0, 0, 0.2);
                    border-bottom: 2px solid rgba(255, 255, 255, 0.8);
                    border-radius: 4px;
                }
            """)
            name_edit.setFixedHeight(45)
            header_layout.addWidget(name_edit)
        else:
            name_label = QLabel(character_name, dialog)
            name_label.setFont(title_font)
            name_label.setStyleSheet("color: #FFFFFF; background: transparent;")
            header_layout.addWidget(name_label)

        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        def add_editable_field(layout, label_text, content, placeholder=""):
            lbl_font = QtGui.QFont()
            lbl_font.setFamily("Inter Tight SemiBold")
            lbl_font.setPointSize(10)
            lbl_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            
            lbl = QLabel(label_text)
            lbl.setFont(lbl_font)
            lbl.setStyleSheet("color: rgba(255, 255, 255, 0.85); margin-top: 10px; margin-bottom: 2px;")
            layout.addWidget(lbl)

            text_font = QtGui.QFont()
            text_font.setFamily("Inter Tight Medium")
            text_font.setPointSize(10)
            text_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

            text_edit = QTextEdit()
            text_edit.setFont(text_font)
            text_edit.setPlainText(str(content) if content else "")
            if placeholder:
                text_edit.setPlaceholderText(placeholder)
            
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(240, 240, 240, 0.95);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 14px;
                }
                QTextEdit:focus {
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    background-color: rgba(0, 0, 0, 0.4);
                }
            """)
            text_edit.setMinimumHeight(180)
            layout.addWidget(text_edit)
            return text_edit

        def create_tab():
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(0, 0, 0, 0)
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setContentsMargins(15, 5, 15, 20)
            content_layout.setSpacing(10)
            
            scroll.setWidget(content_widget)
            layout.addWidget(scroll)
            return tab, content_layout

        description_edit = None
        personality_edit = None
        first_message_edit = None
        scenario_edit = None
        example_messages_edit = None
        alternate_greetings_edit = None
        creator_notes_edit = None

        tabs = QtWidgets.QTabWidget(dialog)
        tabs.setFont(base_font)
        main_layout.addWidget(tabs)

        tab_general_info_text = self.translations.get("btn_general_info_text", "General Info")
        tab_identity_text = self.translations.get("btn_identity_text", "Identity")
        tab_scenario_text = self.translations.get("btn_scenario_text", "Scenario")
        tab_examples_text = self.translations.get("btn_examples_text", "Examples")
        tab_creator_notes_text = self.translations.get("btn_creator_notes_text", "Creator Notes")

        if conversation_method == "Character AI":
            tab_cai, layout_cai = create_tab()
            add_editable_field(layout_cai, self.translations.get("creator_notes_label", "Creator Notes"), character_title).setReadOnly(True)
            tabs.addTab(tab_cai, tab_general_info_text)
        else:
            tab_identity, layout_id = create_tab()
            description_edit = add_editable_field(layout_id, self.translations.get("character_edit_description", "Description"), character_description, self.translations.get("character_edit_description_placeholder_1", "Enter description"))
            personality_edit = add_editable_field(layout_id, self.translations.get("character_edit_personality", "Personality"), character_personality, self.translations.get("character_edit_personality_placeholder", "Enter personality traits"))
            tabs.addTab(tab_identity, tab_identity_text)

            tab_scenario, layout_sc = create_tab()
            first_message_edit = add_editable_field(layout_sc, self.translations.get("character_edit_first_message", "First Message"), first_message, self.translations.get("character_edit_first_message_placeholder", "Enter first message"))
            scenario_edit = add_editable_field(layout_sc, self.translations.get("scenario", "Scenario"), scenario, self.translations.get("placeholder_scenario", "Conversation scenario:"))
            tabs.addTab(tab_scenario, tab_scenario_text)

            tab_examples, layout_ex = create_tab()
            example_messages_edit = add_editable_field(layout_ex, self.translations.get("example_messages_title", "Example Messages"), example_messages, self.translations.get("placeholder_example_messages", "Use <START> macro"))
            alt_greets_text = "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings
            alternate_greetings_edit = add_editable_field(layout_ex, self.translations.get("alternate_greetings_label", "Alternate Greetings"), alt_greets_text, self.translations.get("placeholder_alternate_greetings", "Use <GREETING> macro"))
            tabs.addTab(tab_examples, tab_examples_text)

            tab_notes, layout_notes = create_tab()
            creator_notes_edit = add_editable_field(layout_notes, self.translations.get("creator_notes_label", "Creator Notes"), creator_notes, self.translations.get("placeholder_creator_notes", "Any additional notes"))
            tabs.addTab(tab_notes, tab_creator_notes_text)

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        button_layout.setSpacing(15)

        btn_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.95);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
                color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.05);
            }
        """

        btn_font = QtGui.QFont()
        btn_font.setFamily("Inter Tight SemiBold")
        btn_font.setPointSize(10)
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        ok_button = QPushButton(self.translations.get("update_available_close", "Close"), dialog)
        ok_button.setFont(btn_font)
        ok_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        ok_button.setStyleSheet(btn_style)
        ok_button.clicked.connect(dialog.close)
        button_layout.addWidget(ok_button)

        if conversation_method != "Character AI":
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"), dialog)
            save_button.setFont(btn_font)
            save_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            save_button.setStyleSheet(btn_style)
            save_button.clicked.connect(lambda: self.save_changes(
                dialog, conversation_method, character_name, name_edit, 
                description_edit, personality_edit, scenario_edit, 
                first_message_edit, example_messages_edit, 
                alternate_greetings_edit, creator_notes_edit
            ))
            button_layout.addWidget(save_button)

        new_dialog_button = QPushButton(self.translations.get("character_edit_start_new_dialogue", "Start new chat"), dialog)
        new_dialog_button.setFont(btn_font)
        new_dialog_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        new_dialog_button.setStyleSheet(btn_style)
        
        new_dialog_button.clicked.connect(
            lambda: asyncio.create_task(
                self.start_new_dialog(
                    dialog, conversation_method, character_name,
                    name_edit if conversation_method != "Character AI" else character_name,
                    description_edit if conversation_method != "Character AI" else None,
                    personality_edit if conversation_method != "Character AI" else None,
                    scenario_edit if conversation_method != "Character AI" else None,
                    first_message_edit if conversation_method != "Character AI" else None,
                    example_messages_edit if conversation_method != "Character AI" else None,
                    alternate_greetings_edit if conversation_method != "Character AI" else None,
                    creator_notes_edit if conversation_method != "Character AI" else None
                )
            )
        )
        button_layout.addWidget(new_dialog_button)

        main_layout.addLayout(button_layout)

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

        self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
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
            self.ui.pushButton_call.clicked.disconnect()
        except TypeError:
            pass

        self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.ui.pushButton_call.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
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

        self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
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
            self.ui.pushButton_call.clicked.disconnect()
        except TypeError:
            pass

        self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.ui.pushButton_call.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
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

    def translate_text_if_needed(self, text, is_user=False, to_language="ru"):
        if not text: return text

        translator = self.configuration_settings.get_main_setting("translator")
        if translator == 0:
            return text

        target_lang_setting = self.configuration_settings.get_main_setting("target_language")
        if target_lang_setting != 0:
            return text

        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        # translator_mode: 0 - Both, 1 - User Message, 2 - Character Message
        
        if (is_user and translator_mode == 2) or (not is_user and translator_mode == 1):
            return text

        service = "google" if translator == 1 else "yandex"
        
        try:
            return self.translator.translate(text, service, to_language)
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    async def handle_user_message(self, character_name, conversation_method):
        """
        Handles a user's message: sends it and retrieves a response from the character.

        Args:
            character_name: Character Name
            conversation_method (str): The method used for the conversation.

        This function processes the user's input, translates it if necessary, and interacts with the selected AI model.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        # General Settings
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        auto_summary_status = self.configuration_settings.get_main_setting("auto_summary")
        interval = self.configuration_settings.get_main_setting("interval_summary")
        
        # Character Specifics
        translator = self.configuration_settings.get_main_setting("translator")
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        conversation_method = character_info["conversation_method"]
        
        # Emotions & IDs
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
        
        # TTS Settings
        elevenlabs_voice_id = character_info["elevenlabs_voice_id"]
        voice_type = character_info["voice_type"]
        rvc_enabled = character_info["rvc_enabled"]
        rvc_file = character_info["rvc_file"]

        if conversation_method == "Character AI":
            character_id = character_info.get("character_id")
            chat_id = character_info.get("chat_id")
            character_avatar_url = character_info.get("character_avatar")
            character_avatar = self.character_ai_client.get_from_cache(character_avatar_url)
            voice_name = character_info.get("voice_name")
            character_ai_voice_id = character_info.get("character_ai_voice_id")
        else:
            character_avatar = character_info.get("character_avatar")

        try:
            # User Persona
            personas_data = self.configuration_settings.get_user_data("personas")
            current_persona = character_info.get("selected_persona")
            if current_persona == "None" or current_persona is None:
                user_name = "User"
                user_description = "Interacts with the character using the Soul of Waifu program, which allows the user to interact with large language models."
            else:
                try:
                    user_name = personas_data[current_persona].get("user_name", "User")
                    user_description = personas_data[current_persona].get("user_description", "")
                except Exception as e:
                    user_name = "User"
                    user_description = "Interacts with the character using the Soul of Waifu program, which allows the user to interact with large language models."
            
            user_text_original = self.textEdit_write_user_message.toPlainText().strip()
            user_text = self.translate_text_if_needed(user_text_original, is_user=True, to_language="en")
            user_text_markdown = self.markdown_to_html(user_text_original)
            
            if user_text:
                user_message_container = await self.add_message(character_name, "", is_user=True, message_id=None)
                user_message_label = user_message_container["label"]
                user_message_label.setText(user_text_markdown)

                await asyncio.sleep(0.05)
                self.textEdit_write_user_message.clear()

                if sow_system_status and current_sow_system_mode != "Nothing":
                    indicator_margins = (10, 5, 10, 5)
                else:
                    indicator_margins = (185, 5, 185, 5)

                s_app = self.get_chat_appearance()
                typing_widget = TypingIndicatorWidget(character_name, character_avatar, s_app, indicator_margins)
                self.chat_container.addWidget(typing_widget)

                await asyncio.sleep(0.05)
                self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                full_text = ""
                first_chunk_received = False
                turn_id = ""
                candidate_id = ""
                
                self.current_typewriter = None 

                match conversation_method:
                    case "Character AI":
                        try:
                            async for message in self.character_ai_client.send_message(character_id, chat_id, user_text):
                                text = message.get_primary_candidate().text
                                turn_id = message.turn_id
                                candidate_id = message.get_primary_candidate().candidate_id
                                
                                new_content = text[len(full_text):]
                                
                                if new_content:
                                    if not first_chunk_received:
                                        typing_widget.deleteLater()
                                        self.chat_container.removeWidget(typing_widget)
                                        typing_widget = None
                                        
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

                                    full_text = text
                                    self.current_typewriter.write(new_content)
                                    await asyncio.sleep(0.01) 
                                    
                        except Exception as e:
                            if not first_chunk_received:
                                typing_widget.deleteLater()
                            logger.error(f"C.AI Error: {e}")

                    case "Mistral AI" | "Local LLM" | "Open AI" | "OpenRouter":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list")
                        character_info = character_list.get(character_name)
                        current_chat = character_info["current_chat"]
                        chats = character_info.get("chats", {})
                        chat_history = chats[current_chat]["chat_history"]

                        context_messages = []
                        for message in chat_history:
                            u_msg = message.get("user", "")
                            c_msg = message.get("character", "")
                            if u_msg:
                                context_messages.append({"role": "user", "content": f"{u_msg.strip()}"})
                            if c_msg:
                                context_messages.append({"role": "assistant", "content": f"{c_msg.strip()}"})

                        try:
                            generator = None
                            if conversation_method == "Mistral AI":
                                generator = self.mistral_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description)
                            elif conversation_method == "Local LLM":
                                generator = self.local_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description)
                            elif conversation_method in ["Open AI", "OpenRouter"]:
                                generator = self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description)

                            async for chunk in generator:
                                if chunk:
                                    if not first_chunk_received:
                                        typing_widget.deleteLater()
                                        self.chat_container.removeWidget(typing_widget)
                                        typing_widget = None
                                        
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

                                    full_text += chunk
                                    self.current_typewriter.write(chunk)
                                    
                                    await asyncio.sleep(0.01)

                        except Exception as e:
                            if not first_chunk_received:
                                typing_widget.deleteLater()
                            logger.error(f"Gen Error: {e}")

                if self.current_typewriter:
                    await self.current_typewriter.wait_until_finished()

                clean_full_text = full_text
                if full_text.startswith(f"{character_name}:"):
                    clean_full_text = full_text[len(f"{character_name}:"):].lstrip()

                if first_chunk_received:
                    user_message_message_id = user_message_container["message_id"]
                    character_answer_message_id = character_answer_container["message_id"]
                    
                    if conversation_method != "Character AI":
                        self.configuration_characters.add_message_to_config(character_name, "User", True, user_text, user_message_message_id)
                        self.configuration_characters.add_message_to_config(character_name, character_name, False, clean_full_text, character_answer_message_id)

                if sow_system_status:
                    if current_sow_system_mode in ["Expressions Images", "Live2D Model", "VRM"]:
                        asyncio.create_task(self.detect_emotion(character_name, full_text))

                final_translated_text = self.translate_text_if_needed(clean_full_text, is_user=False, to_language="ru")
                
                translator_setting = self.configuration_settings.get_main_setting("translator")
                if translator_setting != 0 and first_chunk_received:
                     await asyncio.sleep(0.5)
                     final_html = self.markdown_to_html(final_translated_text)
                     final_html = self.apply_macros(final_html, character_name, user_name)
                     character_answer_label.setText(final_html)

                full_text_tts = self.clean_text_for_tts(clean_full_text)
                output_file = None

                try:
                    match current_text_to_speech:
                        case "Nothing" | None:
                            pass
                        
                        case "Character AI":
                            await asyncio.sleep(0.05)
                            output_file = await self.character_ai_client.generate_speech(chat_id, turn_id, candidate_id, character_ai_voice_id)
                        
                        case "ElevenLabs":
                            output_file = await self.eleven_labs_client.generate_speech_with_elevenlabs_sow_system(full_text_tts, elevenlabs_voice_id)
                        
                        case "XTTSv2":
                            lang = "ru" if self.configuration_settings.get_main_setting("translator") != 0 else "en"
                            output_file = await self.xttsv2_client.generate_speech_with_xttsv2_sow_system(full_text_tts, lang, character_name)
                        
                        case "Edge TTS":
                            output_file = await self.edge_tts_client.generate_speech_with_edge_tts_sow_system(full_text_tts, character_name)
                        
                        case "Kokoro":
                            output_file = await self.kokoro_client.generate_speech_with_kokoro(full_text_tts, character_name)
                        
                        case "Silero":
                            output_file = await self.silero_client.generate_speech_with_silero(full_text_tts, character_name)

                    if output_file:
                        # self.playback_worker.clear_queue() 
                        
                        logger.info(f"Adding audio to playback queue: {output_file}")
                        self.playback_worker.add_audio_file(output_file)

                except Exception as e:
                    logger.error(f"TTS Generation Error in Chat: {e}")

                if conversation_method == "Character AI":
                    await self.character_ai_client.fetch_chat(
                        chat_id, character_name, character_id, character_avatar_url, character_title,
                        character_description, character_personality, first_message, current_text_to_speech,
                        voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                        rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                        vrm_model_file, conversation_method, current_emotion
                    )
                    await self.render_cai_messages(character_name)
                else:
                    await self.render_messages(character_name)
                
                if conversation_method != "Character AI":
                    if auto_summary_status and interval and int(interval) > 0:
                        asyncio.create_task(
                            self.perform_auto_summary(character_name, user_name, interval, conversation_method)
                        )
        except Exception:
            error_message = traceback.format_exc()
            logger.error(f"Error processing the message: {error_message}")
            if 'typing_widget' in locals() and typing_widget is not None:
                try:
                    typing_widget.deleteLater()
                except RuntimeError:
                    pass

    async def regenerate_message(self, conversation_method, character_name, message_id):
        """
        Regenerate message from character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
            chat_content = chats[current_chat].get("chat_content", {})
        else:
            current_emotion = character_info["current_emotion"]
            chat_content = character_info.get("chat_content", {})

        character_title = character_info.get("character_title")
        character_description = character_info.get("character_description")
        character_personality = character_info.get("character_personality")
        first_message = character_info.get("first_message")

        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
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

        personas_data = self.configuration_settings.get_user_data("personas")
        current_persona = character_info.get("selected_persona")
        user_name = "User"
        user_description = "Interacts with the character using the Soul of Waifu program."
        if current_persona and current_persona != "None":
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

        match conversation_method:
            case "Character AI":
                turn_ids_to_delete = [chat_content[m].get("turn_id") for m in ids_to_delete if "turn_id" in chat_content[m]]
                await self.character_ai_client.delete_messages(character_name, ids_to_delete, chat_id, turn_ids_to_delete)
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
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

        user_text = self.translate_text_if_needed(user_text_original, is_user=True, to_language="en")

        if message_id in self.messages:
            character_answer_container = self.messages[message_id]
            character_answer_label = character_answer_container["label"]
            character_answer_label.setText("<span style='color: #888;'><i>typing...</i></span>")
        else:
            return

        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

        full_text = ""
        first_chunk_received = False
        self.current_typewriter = None

        if user_text:
            match conversation_method:
                case "Character AI": 
                    turn_id = chat_content[message_id]["turn_id"]

                    try:
                        async for message in self.character_ai_client.regenerate_message(character_id, chat_id, turn_id):
                            text = message.get_primary_candidate().text
                            new_content = text[len(full_text):]
                            
                            if new_content:
                                if not first_chunk_received:
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

                                full_text = text
                                self.current_typewriter.write(new_content)
                                await asyncio.sleep(0.01)
                    except Exception as e:
                        logger.error(f"C.AI Regen Error: {e}")

                case "Mistral AI" | "Local LLM" | "Open AI" | "OpenRouter":
                    chat_history = chats[current_chat]["chat_history"]
                    context_messages = []
                    for message in chat_history[:-1]:
                        u_msg = message.get("user", "")
                        c_msg = message.get("character", "")
                        if u_msg: context_messages.append({"role": "user", "content": f"{u_msg.strip()}"})
                        if c_msg: context_messages.append({"role": "assistant", "content": f"{c_msg.strip()}"})

                    try:
                        generator = None
                        if conversation_method == "Mistral AI":
                            generator = self.mistral_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description)
                        elif conversation_method == "Local LLM":
                            generator = self.local_ai_client.send_message(context_messages, user_text, character_name, user_name, user_description)
                        elif conversation_method in ["Open AI", "OpenRouter"]:
                            generator = self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description)

                        async for chunk in generator:
                            if chunk:
                                if not first_chunk_received:
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
                    except Exception as e:
                        logger.error(f"Gen Regen Error: {e}")

            if self.current_typewriter:
                await self.current_typewriter.wait_until_finished()

            if full_text.startswith(f"{character_name}:"):
                full_text = full_text[len(f"{character_name}:"):].lstrip()

            if sow_system_status and current_sow_system_mode in ["Expressions Images", "Live2D Model", "VRM"]:
                asyncio.create_task(self.detect_emotion(character_name, full_text))

            final_html = self.markdown_to_html(full_text)
            final_html = self.apply_macros(final_html, character_name, user_name)
            final_translated_html = self.translate_text_if_needed(final_html, is_user=False, to_language="ru")
            
            character_answer_label.setText(final_translated_html)

            if conversation_method != "Character AI":
                self.configuration_characters.regenerate_message_in_config(character_name, message_id, full_text)
            else:
                await self.character_ai_client.fetch_chat(
                    chat_id, character_name, character_id, character_avatar_url, character_title,
                    character_description, character_personality, first_message, current_text_to_speech,
                    voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                    rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                    vrm_model_file, conversation_method, current_emotion
                )

        if conversation_method == "Character AI":
            await self.render_cai_messages(character_name)
        else:
            await self.first_render_messages(character_name)

        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))

    async def perform_auto_summary(self, character_name, user_name, interval, conversation_method):
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

            match conversation_method:
                case "Mistral AI":
                    async for chunk in self.mistral_ai_client.generate_summary(
                            current_summary=current_summary,
                            new_messages=new_messages_chunk,
                            character_name=character_name,
                            user_name=user_name
                        ):
                            full_new_summary += chunk
                case "Open AI":
                    async for chunk in self.open_ai_client.generate_summary(
                        conversation_method=conversation_method,
                        current_summary=current_summary,
                        new_messages=new_messages_chunk,
                        character_name=character_name,
                        user_name=user_name
                    ):
                        full_new_summary += chunk
                case "OpenRouter":
                    async for chunk in self.open_ai_client.generate_summary(
                        conversation_method=conversation_method,
                        current_summary=current_summary,
                        new_messages=new_messages_chunk,
                        character_name=character_name,
                        user_name=user_name
                    ):
                        full_new_summary += chunk
                case "Local LLM":
                    async for chunk in self.local_ai_client.generate_summary(
                        current_summary=current_summary,
                        new_messages=new_messages_chunk,
                        character_name=character_name,
                        user_name=user_name
                    ):
                        full_new_summary += chunk

            if full_new_summary and len(full_new_summary) > 50:
                chat_data["summary_text"] = full_new_summary
                chat_data["last_summarized_sequence"] = highest_seq_in_chunk
                
                self.configuration_characters.save_configuration_edit(char_config)
                logger.info(f"Auto-summary completed. Updated sequence to {highest_seq_in_chunk}")

        except Exception as e:
            logger.error(f"Auto-summary background task failed: {e}")

    async def add_message(self, character_name, text, is_user, message_id):
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
            try:
                user_name = personas_data[current_persona].get("user_name", "User")
            except Exception as e:
                logger.error(e)
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
                    )
        
        message_container = QHBoxLayout()
        message_container.setSpacing(5)

        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        current_sow_system_mode = char_info.get("current_sow_system_mode", "Nothing")
        if sow_system_status and current_sow_system_mode != "Nothing":
            message_container.setContentsMargins(10, 5, 10, 5)
        else:
            message_container.setContentsMargins(185, 5, 185, 5)

        message_label = QLabel()
        message_label.setTextFormat(Qt.TextFormat.RichText)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_label.setText(html_text)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        message_label.setFont(font)

        message_frame = SmoothMessageFrame(None)
        message_frame.setLayout(message_container)
        message_frame.setStyleSheet("""
            QMenu {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #383838;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 6px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border-radius: 4px;
            }
        """)

        s = self.get_chat_appearance()
        message_label.setStyleSheet(self._bubble_stylesheet(s, is_user))

        if is_user:
            raw_pixmap = QPixmap(self.user_avatar)
        else:
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
        # ==========================================

        if conversation_method != "Character AI":
            current_chat = char_info["current_chat"]
            chats = char_info.get("chats", {})
            chat_content = chats[current_chat].get("chat_content", {})
        else:
            chat_content = char_info.get("chat_content", {})

        last_char_index = self.get_last_character_message_index(chat_content)
        if last_char_index is None:
            has_variants = False
        else:
            msg_data = chat_content[last_char_index]
            variants = msg_data.get("variants", [])
            has_variants = len(variants) > 1

        left_button = QPushButton()
        right_button = QPushButton()

        left_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        right_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        left_icon = QtGui.QIcon(QtGui.QPixmap("app/gui/icons/left_arrow.png"))
        left_button.setIcon(left_icon)
        right_icon = QtGui.QIcon(QtGui.QPixmap("app/gui/icons/right_arrow.png"))
        right_button.setIcon(right_icon)
        button_size = QtCore.QSize(20, 20)

        left_button.setFixedSize(button_size)
        right_button.setFixedSize(button_size)
        left_button.setStyleSheet("background-color: transparent; border: none;")
        right_button.setStyleSheet("background-color: transparent; border: none;")
        left_button.setCursor(Qt.CursorShape.PointingHandCursor)
        right_button.setCursor(Qt.CursorShape.PointingHandCursor)

        is_last_char_message = False
        if message_id == self.get_last_character_message_index(chat_content):
            is_last_char_message = True

        left_button.setVisible(has_variants and is_last_char_message)
        right_button.setVisible(has_variants and is_last_char_message)
        
        if has_variants and last_char_index is not None:
            try:
                left_button.clicked.disconnect()
                right_button.clicked.disconnect()
            except TypeError:
                pass
            left_button.clicked.connect(lambda _, dir=-1: self.change_variant(character_name, dir))
            right_button.clicked.connect(lambda _, dir=+1: self.change_variant(character_name, dir))
        
        variant_counter_label = QLabel()
        variant_counter_label.setFixedSize(45, 20)
        variant_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font_variant = QtGui.QFont()
        font_variant.setFamily("Inter Tight Medium")
        font_variant.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        variant_counter_label.setFont(font_variant)
        variant_counter_label.setStyleSheet("""
            QLabel {
                color: #D8DEE9;
                background-color: rgba(45, 45, 45, 0.8);
                font-size: 10px;
                border-radius: 10px;
                padding: 2px 5px;
                margin-left: 5px;
                margin-right: 5px;
            }
        """)
        variant_counter_label.setVisible(has_variants and is_last_char_message)

        current_idx = self.get_current_variant_index(character_name)
        if current_idx != -1:
            variant_counter_label.setText(f"{current_idx + 1}/{len(variants)}")
        variant_counter_label.raise_()

        menu_button = QPushButton("•••")
        menu_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        menu_button.setFixedSize(30, 30)
        
        font_menu = QtGui.QFont("Arial", 11, QtGui.QFont.Weight.Bold)
        font_menu.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        menu_button.setFont(font_menu)
        menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        
        menu_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 15px;
                padding-bottom: 2px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.08);
            }
        """)

        try:
            menu_button.clicked.disconnect()
        except TypeError:
            pass
        
        menu_button.clicked.connect(lambda _: self.show_message_menu(character_name, conversation_method, menu_button, is_user, message_id))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        message_label.setGraphicsEffect(shadow)

        if is_user:
            message_container.addStretch()
            message_container.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignVCenter)
            message_container.addWidget(message_label)
            message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
        else:
            message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(left_button, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(message_label)
            message_container.addWidget(right_button, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(variant_counter_label, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(menu_button, alignment=Qt.AlignmentFlag.AlignVCenter)
            message_container.addStretch()

        left_button.raise_()
        right_button.raise_()

        self.chat_container.addWidget(message_frame)
        await asyncio.sleep(0.005)
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
        
        self.messages[message_id] = {
            "message_id": message_id,
            "text": text,
            "author_name": user_name if is_user else character_name,
            "label": message_label,
            "frame": message_frame,
            "layout": message_container,
            "is_user": is_user,
            "variant_counter_label": variant_counter_label
        }

        self.message_order.append(message_id)

        return {
            "message_id": message_id,
            "label": message_label,
            "frame": message_frame,
            "layout": message_container,
            "left_button": left_button,
            "right_button": right_button,
            "variant_counter_label": variant_counter_label
        }

    def show_message_menu(self, character_name, conversation_method, button, is_user, message_id):
        """
        Displays a context menu for a message (e.g., delete, edit, or continue from the message).
        """
        try:
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

            if conversation_method != "Character AI":
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)
                current_chat = character_information["current_chat"]
                chats = character_information.get("chats", {})

                chat_content = chats[current_chat].get("chat_content", {})
            else:
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)

                chat_content = character_information.get("chat_content", {})

            msg_data = self.messages[message_id]
            text = msg_data["text"]
            msg_data_chat_content = chat_content.get(message_id)

            sequence_number = msg_data_chat_content.get("sequence_number", "N/A")

            edit_action = QAction(self.translations.get("chat_edit_message_2", "Edit"), None)
            delete_action = QAction(self.translations.get("chat_delete_message", "Delete"), None)
            continue_action = QAction(self.translations.get("chat_continue_message", "Continue from this message"), None)
            regenerate_action = QAction(self.translations.get("chat_regenerate_message", "Regenerate"), None)

            edit_icon = QtGui.QIcon("app/gui/icons/edit.png")
            delete_icon = QtGui.QIcon("app/gui/icons/delete.png")
            continue_icon = QtGui.QIcon("app/gui/icons/continue.png")
            regenerate_icon = QtGui.QIcon("app/gui/icons/regen.png")

            edit_action.setIcon(edit_icon)
            delete_action.setIcon(delete_icon)
            continue_action.setIcon(continue_icon)
            regenerate_action.setIcon(regenerate_icon)

            try:
                delete_action.triggered.disconnect()
                edit_action.triggered.disconnect()
                continue_action.triggered.disconnect()
                regenerate_action.triggered.disconnect()
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
                if sequence_number == 1:
                    menu.addAction(edit_action)
                else:
                    if conversation_method != "Character AI":
                        regenerate_action.triggered.connect(lambda _: asyncio.create_task(
                            self.regenerate_message(conversation_method, character_name, message_id)
                        ))
                        menu.addAction(regenerate_action)
                    menu.addAction(edit_action)
                    menu.addAction(delete_action)

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
                QMessageBox.warning(
                    None, 
                    "Error with message menu", 
                    f"Failed to show message menu: {str(e)}"
                )
            except:
                pass

    async def delete_message(self, character_name, conversation_method, message_id):
        """
        Deletes a message from the interface and the configuration file.
        """
        try:
            if message_id not in self.messages:
                return
            
            configuration_data = self.configuration_characters.load_configuration()
            if conversation_method != "Character AI":
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)
                current_chat = character_information["current_chat"]
                chats = character_information.get("chats", {})

                chat_content = chats[current_chat].get("chat_content", {})
            else:
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list")
                character_information = character_list.get(character_name)

                chat_content = character_information.get("chat_content", {})

            if message_id in chat_content:
                deleted_message_data = chat_content[message_id]

                if conversation_method != "Character AI":
                    configuration_data["character_list"][character_name]["chats"][current_chat]["chat_content"] = chat_content
                else:
                    configuration_data["character_list"][character_name]["chat_content"] = chat_content
                
                
                self.configuration_characters.save_configuration_edit(configuration_data)

                self.configuration_characters.delete_chat_message(
                    message_id, 
                    character_name
                )

                if message_id in self.messages:
                    self.messages[message_id]["frame"].deleteLater()
                    del self.messages[message_id]
                    self.message_order.remove(message_id)

                if conversation_method == "Character AI":
                    chat_id = configuration_data["character_list"][character_name]["chat_id"]
                    turn_id = deleted_message_data["turn_id"]
                    await self.character_ai_client.delete_message(
                        character_name, 
                        message_id, 
                        chat_id, 
                        turn_id
                    )
            
            if conversation_method == "Character AI":
                await self.first_render_cai_messages(character_name)
            else:
                await self.first_render_messages(character_name)
        except Exception as e:
            logger.error(f"Error deleting message: {e}")

    async def edit_message(self, character_name, conversation_method, message_id, original_text):
        """
        Edits a message in both the interface and the configuration file.
        """
        if message_id not in self.messages:
            return

        new_text = await self.edit_message_dialog(conversation_method, message_id, character_name, original_text)
        if new_text is not None:
            processed_text = self.markdown_to_html(new_text)
        else:
            return
        
        user_name = self.configuration_settings.get_user_data("user_name") or "User"
        processed_text = (processed_text.replace("{{user}}", user_name)
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

        self.messages[message_id]["label"].setText(processed_text)
        self.messages[message_id]["text"] = new_text

        self.configuration_characters.update_chat_history(character_name)
        
        if conversation_method == "Character AI":
            await self.first_render_cai_messages(character_name)
        else:
            await self.first_render_messages(character_name)
    
    async def edit_message_dialog(self, conversation_method, message_id, character_name, original_text, parent=None):
        """
        Opens a dialog window to edit a message based on the conversation method.
        """
        try:
            dialog = QDialog(parent)
            dialog.setWindowTitle(self.translations.get("chat_edit_message", "Edit Message"))
            dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            dialog.setMinimumSize(400, 400)
            dialog.setMaximumSize(400, 400)
            
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgb(30, 30, 30);
                    border-radius: 10px;
                }
                QTextEdit {
                    background-color: rgb(40, 40, 40);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(60, 60, 60);
                    border-radius: 5px;
                    padding: 10px;
                    font: 10pt "Segoe UI";
                    selection-color: rgb(255, 255, 255);
                    selection-background-color: rgb(39, 62, 135);
                }
                QPushButton {
                    background-color: rgb(60, 60, 60);
                    color: rgb(255, 255, 255);
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    font: 10pt "Segoe UI";
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: rgb(80, 80, 80);
                }
                QPushButton:pressed {
                    background-color: rgb(40, 40, 40);
                }
            """)
            
            configuration_data = self.configuration_characters.load_configuration()

            layout = QVBoxLayout(dialog)
            edit_field = QtWidgets.QTextEdit(dialog)
            edit_field.setText(original_text)

            edit_field.setAcceptRichText(False)
            layout.addWidget(edit_field)

            save_button = QPushButton(self.translations.get("chat_save_message", "Save"), dialog)
            save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            layout.addWidget(save_button)

            try:
                save_button.clicked.disconnect()
            except TypeError:
                pass

            save_button.clicked.connect(dialog.accept)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                edited_text = edit_field.toPlainText()

                if conversation_method == "Character AI":
                    configuration_data = self.configuration_characters.load_configuration()
                    char_data = configuration_data["character_list"][character_name]

                    if "chat_id" not in char_data or message_id not in char_data["chat_content"]:
                        raise ValueError("Missing required chat data")

                    await self.character_ai_client.edit_message(
                        character_name=character_name,
                        message_id=message_id,
                        chat_id=char_data["chat_id"],
                        turn_id=char_data["chat_content"][message_id]["turn_id"],
                        candidate_id=char_data["chat_content"][message_id]["candidate_id"],
                        text=edited_text
                    )
                else:
                    self.configuration_characters.edit_chat_message(
                        message_id=message_id,
                        character_name=character_name,
                        edited_text=edited_text
                    )

                return edited_text
            
            return None
        except Exception as e:
            logger.error(f"Error editing message: {str(e)}")
            return None

    async def continue_dialog(self, conversation_method, message_id, character_name):
        """
        Deletes all messages that come after the specified message.
        """
        configuration_data = self.configuration_characters.load_configuration()
        char_data = configuration_data["character_list"].get(character_name)
        if not char_data:
            logger.error(f"Character '{character_name}' not found.")
            return

        if conversation_method != "Character AI":
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})
        else:
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            chat_content = character_information.get("chat_content", {})

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

        match conversation_method:
            case "Character AI":
                chat_id = char_data.get("chat_id")
                turn_ids_to_delete = []
                for msg_id, msg_data in chat_content.items():
                    if msg_data and "turn_id" in msg_data:
                        turn_ids_to_delete.append(msg_data["turn_id"])
                await self.character_ai_client.delete_messages(
                    character_name, ids_to_delete, chat_id, turn_ids_to_delete
                )
            case "Mistral AI" | "Open AI" | "OpenRouter" | "Local LLM":
                self.configuration_characters.delete_chat_messages(character_name, ids_to_delete)

        await asyncio.sleep(0.05)
        if conversation_method == "Character AI":
            await self.first_render_cai_messages(character_name)
        else:
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
            self.show_toast(self.translations.get("character_edit_error_2", "Character was not found in the configuration."), "error")
            dialog.close()
            return

        if conversation_method != "Character AI":
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

        self.show_toast(self.translations.get("character_edit_saved_2", "The changes were saved successfully!"), "success")
        asyncio.create_task(self.open_chat(new_name))
        dialog.close()

    async def start_new_dialog(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        title = self.translations.get("character_edit_start_new_dialogue", "Start new dialogue")
        message = self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue? The previous dialogue will be deleted.")

        if not self.show_confirmation_dialog(title, message):
            return

        if conversation_method != "Character AI":
            chat_name, ok = QInputDialog.getText(
                dialog,
                self.translations.get("new_chat_title", "New Chat"),
                self.translations.get("new_chat_prompt", "Enter chat name:")
            )

            if not ok or not chat_name.strip():
                chat_name = self.translations.get("default_chat_name", "Default Chat")

        match conversation_method:
            case "Character AI":
                character_data = self.configuration_characters.load_configuration()
                character_list = character_data.get("character_list", {})
                character_id = character_list[character_name]["character_id"]
                await self.character_ai_client.create_new_chat(character_id)

            case "Mistral AI" | "Local LLM" | "Open AI" | "OpenRouter":
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

        self.ui.stackedWidget.setCurrentIndex(1)

        self.show_toast(self.translations.get("character_edit_start_new_dialogue_success", "A new dialogue has been successfully started!"), "success")
    
        dialog.close()
        await self.set_main_tab()
        await self.close_chat()
        self.main_window.updateGeometry()

    def clean_text_for_tts(self, full_text):
        cleaned_text = re.sub(r"[^a-zA-Zа-яА-Я0-9\s.,!?]", "", full_text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text

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
        conversation_method = character_information["conversation_method"]

        if conversation_method != "Character AI":
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})
        else:
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            chat_content = character_information.get("chat_content", {})

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

        if conversation_method != "Character AI":
            chats[current_chat]["chat_content"] = chat_content
        else:
            character_information["chat_content"] = chat_content
        
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

        if conversation_method != "Character AI":
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})
        else:
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            chat_content = character_information.get("chat_content", {})
        
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
        conversation_method = character_information["conversation_method"]

        if conversation_method != "Character AI":
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)
            current_chat = character_information["current_chat"]
            chats = character_information.get("chats", {})

            chat_content = chats[current_chat].get("chat_content", {})
        else:
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            chat_content = character_information.get("chat_content", {})

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

    async def _maybe_translate(self, text: str, is_user: bool) -> str:
        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")

        if translator == 0:
            return text
        if target_language != 0:
            return text
        if translator_mode not in (0, 2):
            return text
        if is_user and translator_mode != 0:
            return text

        service = "google" if translator == 1 else "yandex" if translator == 2 else None
        if not service:
            return text

        return await self.translator.translate_async(text, service, "ru")

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

        if not character_information:
            logger.warning(f"Character {character_name} not found in config (possible race condition).")
            self.chat_widget.setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setVisible(True)
            return
        
        current_chat = character_information["current_chat"]
        chats = character_information.get("chats", {})

        chat_content = chats[current_chat].get("chat_content", {})

        for message_id, msg_data in sorted(chat_content.items(), key=lambda x: x[1].get("sequence_number", float('inf'))):
            is_user = msg_data.get("is_user", False)
            current_variant_id = msg_data.get("current_variant_id", "default")
            variants = msg_data.get("variants", [])
            text = next((v["text"] for v in variants if v["variant_id"] == current_variant_id), "")
                
            text = await self._maybe_translate(text, is_user)
            
            await self.add_header_image(text)

            await self.add_message(
                character_name=character_name,
                text=text,
                is_user=is_user,
                message_id=message_id
            )

        self.ensure_header_image_on_top()
        self.chat_widget.setUpdatesEnabled(True)
        self.chat_container.update()
        self.ui.scrollArea_chat.setVisible(True)
        self.ui.scrollArea_chat.update()
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
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

        if not character_information:
            logger.warning(f"Character {character_name} not found in config (possible race condition).")
            self.chat_widget.setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setVisible(True)
            return
        
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
            
            await self.add_header_image(text)

            text = await self._maybe_translate(text, is_user)
            
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
                        logger.error(e)
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

        self.ensure_header_image_on_top()
        self.chat_widget.setUpdatesEnabled(True)
        self.chat_container.update()
        self.ui.scrollArea_chat.setVisible(True)
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
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

        if not character_information:
            logger.warning(f"Character {character_name} not found in config (possible race condition).")
            self.chat_widget.setUpdatesEnabled(True)
            self.ui.scrollArea_chat.setVisible(True)
            return

        chat_content = character_information.get("chat_content", {})

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

                text = await self._maybe_translate(text, is_user)

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
        self.chat_container.update()
        self.ui.scrollArea_chat.update()
        QApplication.processEvents()
    
    async def render_cai_messages(self, character_name):
        self.chat_widget.setUpdatesEnabled(False)
        self.ui.scrollArea_chat.setVisible(False)
        
        try:
            character_data = self.configuration_characters.load_configuration()
            character_list = character_data.get("character_list")
            character_information = character_list.get(character_name)

            if not character_information:
                logger.warning(f"Character {character_name} not found in config (possible race condition).")
                self.chat_widget.setUpdatesEnabled(True)
                self.ui.scrollArea_chat.setVisible(True)
                return

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

                    text = await self._maybe_translate(text, is_user)

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
            self.ensure_header_image_on_top()

    async def detect_emotion(self, character_name, text):
        """
        Detects emotion and updates the character's expression (image, Live2D model or VRM).
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

        conversation_method = character_info["conversation_method"]
            
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
                if self.stackedWidget_expressions is not None:
                    self.stackedWidget_expressions.setCurrentWidget(self.live2d_page)
                else:
                    logger.error("Live2D model file not found.")
        elif current_sow_system_mode == "VRM":
            self.show_emotion_animation(character_name)
        
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
        
        # FOR 2.4
        # if "Motions" in file_references:
        #     del file_references["Motions"]
        # model_data["FileReferences"] = file_references

        with open(model_json_path, "w", encoding="utf-8") as file:
            json.dump(model_data, file, indent=4, ensure_ascii=False)

    def show_emotion_image(self, expression_images_folder, character_name):
        """
        Displays an image or GIF representing the character's current emotion.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_information["conversation_method"]
        
        if conversation_method != "Character AI":
            current_chat = character_info["current_chat"]
            chats = character_info.get("chats", {})
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            current_emotion = character_info["current_emotion"]

        image_name = self.emotion_resources[current_emotion]["image"]
        
        if self.expression_image_label is not None:
            gif_path = os.path.join(expression_images_folder, f"{image_name}.gif")
            png_path = os.path.join(expression_images_folder, f"{image_name}.png")
            neutral_gif_path = os.path.join(expression_images_folder, "neutral.gif")
            neutral_png_path = os.path.join(expression_images_folder, "neutral.png")

            if os.path.exists(gif_path):
                movie = QtGui.QMovie(gif_path)
                movie.setScaledSize(QtCore.QSize(320, 500))
                self.expression_image_label.setMovie(movie)
                self.expression_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                movie.start()
            elif os.path.exists(neutral_gif_path):
                movie = QtGui.QMovie(neutral_gif_path)
                movie.setScaledSize(QtCore.QSize(320, 500))
                self.expression_image_label.setMovie(movie)
                self.expression_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                movie.setParent(self.expression_image_label)
                movie.start()
            elif os.path.exists(png_path):
                pixmap = QPixmap(png_path)
                scaled_pixmap = pixmap.scaled(
                    self.expression_image_label.width(),
                    self.expression_image_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.expression_image_label.setPixmap(scaled_pixmap)
            elif os.path.exists(neutral_png_path):
                pixmap = QPixmap(neutral_png_path)
                scaled_pixmap = pixmap.scaled(
                    self.expression_image_label.width(),
                    self.expression_image_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.expression_image_label.setPixmap(scaled_pixmap)
            else:
                logger.error(f"Files for emotion {image_name} and neutral not found.")

            if self.stackedWidget_expressions is not None:
                self.stackedWidget_expressions.setCurrentWidget(self.expression_image_page)

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
            self.show_toast(self.translations.get("voice_error_body", "Assign a character's voice before you go on to the call."), "error")
        else:
            personas_data = self.configuration_settings.get_user_data("personas")
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][character_name]
            current_persona = character_info.get("selected_persona")

            if current_persona == "None" or current_persona is None:
                self.user_avatar = "app/gui/icons/person.png"
            else:
                if current_persona not in personas_data:
                    self.show_toast(self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."), "error")
                    return
                else:
                    self.user_avatar = personas_data[current_persona].get("user_avatar", "")
                    
                    if not self.user_avatar or not os.path.exists(self.user_avatar):
                        self.user_avatar = "app/gui/icons/person.png"
            
            if gui_mode == 1:
                if current_sow_system_mode in ("Nothing", "Expressions Images"):
                    self.show_toast(self.translations.get("no_gui_error_body", "Select Live2D or VRM to use the non-interface mode."), "error")
                    return
                else:
                    self.sow_system = Soul_Of_Waifu_System(self.main_window, character_name)
                    asyncio.create_task(self.sow_system.initialize_sow_system(character_name))
            else:
                self.sow_system = Soul_Of_Waifu_System(self.main_window, character_name)
                asyncio.create_task(self.sow_system.initialize_sow_system(character_name))

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
        gl.glClearDepth(1.0)
        
        if self.live2d_model:
            self.live2d_model.Resize(self.width(), self.height())
            
            self.live2d_model.Update()
            self.live2d_model.Draw()

    def timerEvent(self, a0: QTimerEvent | None) -> None:
        """
        Updates the Live2D model and triggers a repaint.
        """
        self.update_live2d_emotion()
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

class PushButton(QtWidgets.QPushButton):
    def __init__(self, start_color, end_color, type_button, text_block_content, parent=None):
        super().__init__(parent)
        self._start_color = QtGui.QColor(start_color)
        self._end_color = QtGui.QColor(end_color)
        self.type_button = type_button
        self.text_block_content = text_block_content
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.setToolTip(self.text_block_content)
        self._animation = QtCore.QVariantAnimation(
            startValue=self._start_color,
            endValue=self._end_color,
            valueChanged=self._on_value_changed,
            duration=300
        )

    def _on_value_changed(self, color):
        self._update_stylesheet(color)

    def _update_stylesheet(self, color):
        if self.type_button == "menu_card":
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: white;
                    border: 2px solid transparent;
                    border-radius: 17px;
                    width: 30px;
                    height: 30px;
                    font-size: 14px;
                    padding: 0;
                    margin: 5px;
                }}

                QToolTip {{
                    background-color: #2a2a2a;
                    color: #ffffff;
                    border: 1px solid #444444;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 14px;
                    max-width: 300px;
                    opacity: 220;
                }}
                """
            )
        elif self.type_button == "menu_more_button":
            self.setStyleSheet(
            f"""
                QPushButton {{
                    background-color: {color.name()};
                    border: none;
                    border-radius: 15px;
                    padding: 0;
                    margin: 0;
                }}

                QToolTip {{
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }}
                """
            )
        elif self.type_button == "character_card":
            self.setStyleSheet(
                f"""
                QPushButton {{
                    border: none;
                    border-radius: 15px;
                    padding: 8px 16px;
                    font-size: 10px;
                    background-color: {color.name()};
                    color: #ffffff;
                }}

                QToolTip {{
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }}
                """
            )
        elif self.type_button == "character_card_2":
            self.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color.name()};
                    color: white;
                    border: 2px solid transparent;
                    border-radius: 15px;
                    padding: 0;
                    margin: 5px;
                    width: 30px;
                    height: 30px;
                }}

                QToolTip {{
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }}
                """
            )

    def enterEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Forward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Backward)
        self._animation.start()
        super().leaveEvent(event)

class TextEditUserMessage(QtWidgets.QTextEdit):
    handle_enter_key = QtCore.pyqtSignal()
    
    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
            if event.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.handle_enter_key.emit()
                event.accept()
        else:
            super().keyPressEvent(event)

class CharacterCardCharactersGateway(QtWidgets.QFrame):
    def __init__(self, conversation_method, character_author, character_name, character_avatar, character_title, character_description, character_personality, scenario, first_message, example_messages, alternate_greetings, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.conversation_method = conversation_method
        self.character_name = character_name
        self.character_avatar = character_avatar
        self.character_title = character_title
        self.character_description = character_description
        self.character_personality = character_personality
        self.character_scenario = scenario
        self.first_message = first_message
        self.example_messages = example_messages
        self.alternate_greetings = alternate_greetings

        self.check_character_information = method

        self.downloads = None
        self.likes = None
        self.total_tokens = None
        self.character_author = character_author

        self.pixmap = QtGui.QPixmap(character_avatar)
        if self.pixmap.isNull():
            self.pixmap = QtGui.QPixmap("app/gui/icons/logotype.png")

        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(350)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(350)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(300)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        
        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(20, 20, 22, 0.9); border-radius: 20px;")
        self.action_panel.setGeometry(10, 280, 180, 40)
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(4, 4, 4, 4)
        self.action_panel_layout.setSpacing(4)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self):
        return self._darkness_alpha

    @darkness_alpha.setter
    def darkness_alpha(self, value):
        self._darkness_alpha = value
        self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self):
        return self._info_alpha

    @info_alpha.setter
    def info_alpha(self, value):
        self._info_alpha = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 220))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()
        
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()
        
        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(15)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(220, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            
            text_rect = QtCore.QRect(15, rect.height() - 85, rect.width() - 30, 45)
            painter.drawText(
                text_rect, 
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.TextFlag.TextWordWrap, 
                self.character_name
            )

            stats_y = rect.height() - 20
            stats_x = 15
            painter.setFont(QtGui.QFont("Inter Tight SemiBold", 9))
            
            if hasattr(self, 'likes') and self.likes is not None:
                painter.setPen(QtGui.QColor(230, 41, 41, int(self._info_alpha)))
                lk_text = f"\u2764 {self.likes}"
                painter.drawText(stats_x, stats_y, lk_text)
                stats_x += painter.fontMetrics().horizontalAdvance(lk_text) + 10

            if hasattr(self, 'downloads') and self.downloads is not None:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                dl_text = f"\ud83d\udcbe {self.downloads}"
                painter.drawText(stats_x, stats_y, dl_text)
                stats_x += painter.fontMetrics().horizontalAdvance(dl_text) + 10

            if hasattr(self, 'total_tokens') and self.total_tokens is not None:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                tk_text = f"\u2699 {self.total_tokens}"
                painter.drawText(stats_x, stats_y, tk_text)
            
            if self.character_author:
                painter.setPen(QtGui.QColor(104, 128, 186, int(self._info_alpha)))
                dl_text = f"✒️ {self.character_author}"
                painter.drawText(stats_x, stats_y, dl_text)
                stats_x += painter.fontMetrics().horizontalAdvance(dl_text) + 10

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.check_character_information(
                self.conversation_method, self.character_name, 
                self.character_avatar, self.character_title, 
                self.character_description, self.character_personality, 
                self.character_scenario, self.first_message, self.example_messages,
                self.alternate_greetings
            )
        super().mousePressEvent(event)

class ModelListItemWidget(QWidget):
    def __init__(self, model_name, file_size_bytes, full_path, refresh_method, launch_server_method, stop_server_method, ui, parent=None, is_server_running=False):
        super().__init__(parent)
        self.configuration_settings = configuration.ConfigurationSettings()
        
        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")
            case _:
                self.load_translation("en")

        self.model_name = model_name or "unknown_model"
        self.full_path = full_path or ""
        self.refresh_method = refresh_method
        self.launch_server_method = launch_server_method
        self.stop_server_method = stop_server_method
        self.ui = ui
        self.parent_widget = parent
        self.is_server_running = is_server_running

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        
        self.glass_card = QFrame(self)
        self.glass_style_normal = """
            QFrame {
                background-color: rgba(25, 25, 30, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """
        self.glass_style_hover = """
            QFrame {
                background-color: rgba(35, 35, 45, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 16px;
            }
        """
        self.glass_card.setStyleSheet(self.glass_style_normal)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.glass_card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(self.glass_card)
        card_layout.setContentsMargins(20, 15, 20, 15)
        card_layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(6)

        name_row_layout = QHBoxLayout()
        name_row_layout.setSpacing(8)
        
        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setFixedSize(18, 18)
        self.icon_label.setScaledContents(True)
        name_row_layout.addWidget(self.icon_label)

        self.name_label = QLabel(model_name)
        font_name = QtGui.QFont("Inter Tight SemiBold", 11, QtGui.QFont.Weight.Bold)
        font_name.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font_name)
        self.name_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")
        name_row_layout.addWidget(self.name_label)
        name_row_layout.addStretch()

        info_layout.addLayout(name_row_layout)

        meta_row_layout = QHBoxLayout()
        meta_row_layout.setSpacing(8)

        size_str = self.human_readable_size(file_size_bytes)
        self.size_badge = QLabel(f"💾 {size_str}")
        self.size_badge.setFixedHeight(20)
        self.size_badge.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 10px;
                font-family: 'Inter Tight Medium';
            }
        """)
        meta_row_layout.addWidget(self.size_badge)

        self.status_badge = QLabel()
        self.status_badge.setFixedHeight(20)
        meta_row_layout.addWidget(self.status_badge)
        meta_row_layout.addStretch()
        self.status_badge.hide()

        info_layout.addLayout(meta_row_layout)
        card_layout.addLayout(info_layout, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_set_default = QPushButton(self.translations.get("button_set_default", "Set as Default"))
        icon_launch = QtGui.QIcon()
        icon_launch.addPixmap(QtGui.QPixmap("app/gui/icons/default_model.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_set_default.setIcon(icon_launch)
        self.btn_set_default.setIconSize(QtCore.QSize(14, 14))

        current_default_path = self.configuration_settings.get_main_setting("local_llm")
        current_default_name = None
        if current_default_path and os.path.exists(current_default_path):
            current_default_name = os.path.splitext(os.path.basename(current_default_path))[0]

        if current_default_name == model_name and is_server_running:
            self.btn_launch_server = QPushButton(self.translations.get("button_disable_server", "Unload Model"))
            self.server_loaded = True
        else:
            self.btn_launch_server = QPushButton(self.translations.get("button_launch_server", "Load Model"))
            self.server_loaded = False
            
        self.btn_delete = QPushButton()
        self.btn_delete.setToolTip(self.translations.get("button_delete_model", "Delete model"))
        icon_delete = QtGui.QIcon()
        icon_delete.addPixmap(QtGui.QPixmap("app/gui/icons/bin.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_delete.setIcon(icon_delete)
        self.btn_delete.setIconSize(QtCore.QSize(16, 16))

        btn_font = QtGui.QFont("Inter Tight SemiBold", 9)
        btn_font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        for btn in [self.btn_set_default, self.btn_launch_server, self.btn_delete]:
            btn.setFont(btn_font)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self.btn_set_default.setFixedHeight(34)
        self.btn_launch_server.setFixedHeight(34)
        self.btn_delete.setFixedSize(34, 34)

        self.btn_set_default.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.8);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.1);
                padding: 0px 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: #ffffff;
            }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.08); }
        """)

        if self.server_loaded:
            self.btn_launch_server.setStyleSheet("""
                QPushButton {
                    background-color: rgba(230, 81, 0, 0.2);
                    color: #FFCC80;
                    border-radius: 8px;
                    border: 1px solid rgba(255, 152, 0, 0.3);
                    padding: 0px 15px;
                }
                QPushButton:hover {
                    background-color: rgba(230, 81, 0, 0.4);
                    border: 1px solid rgba(255, 152, 0, 0.6);
                    color: #ffffff;
                }
                QPushButton:pressed { background-color: rgba(230, 81, 0, 0.1); }
            """)
        else:
            self.btn_launch_server.setStyleSheet("""
                QPushButton {
                    background-color: rgba(46, 125, 50, 0.2);
                    color: #A5D6A7;
                    border-radius: 8px;
                    border: 1px solid rgba(76, 175, 80, 0.3);
                    padding: 0px 15px;
                }
                QPushButton:hover {
                    background-color: rgba(46, 125, 50, 0.4);
                    border: 1px solid rgba(76, 175, 80, 0.6);
                    color: #ffffff;
                }
                QPushButton:pressed { background-color: rgba(46, 125, 50, 0.1); }
            """)

        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: rgba(211, 47, 47, 0.1);
                border-radius: 8px;
                border: 1px solid rgba(244, 67, 54, 0.2);
            }
            QPushButton:hover {
                background-color: rgba(211, 47, 47, 0.3);
                border: 1px solid rgba(244, 67, 54, 0.5);
            }
            QPushButton:pressed { background-color: rgba(211, 47, 47, 0.05); }
        """)

        if current_default_name == model_name:
            pixmap = QPixmap("app/gui/icons/star.png")
            self.icon_label.setPixmap(pixmap)
            self.name_label.setStyleSheet("color: #FFD700; font-weight: bold; background: transparent; border: none;")
            
            self.status_badge.show()
            if is_server_running:
                self.status_badge.setText("🟢 Active")
                self.status_badge.setStyleSheet("""
                    QLabel { background-color: rgba(76, 175, 80, 0.15); color: #81C784; border: 1px solid rgba(76, 175, 80, 0.3);
                    border-radius: 6px; padding: 3px 8px; font-size: 10px; font-weight: bold; }
                """)
            else:
                self.status_badge.setText("⚪ Standby")
                self.status_badge.setStyleSheet("""
                    QLabel { background-color: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.5); border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 6px; padding: 3px 8px; font-size: 10px; font-weight: bold; }
                """)
                
            actions_layout.addWidget(self.btn_launch_server)
        else:
            self.icon_label.hide()
            actions_layout.addWidget(self.btn_set_default)

        actions_layout.addWidget(self.btn_delete)
        card_layout.addLayout(actions_layout)

        self.btn_set_default.clicked.connect(self.on_set_default_clicked)
        self.btn_delete.clicked.connect(self.on_delete_clicked)
        
        if self.server_loaded:
            self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
        else:
            self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)
            
        main_layout.addWidget(self.glass_card)
        self.setLayout(main_layout)
    
    def load_translation(self, language):
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

    def human_readable_size(self, size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"

    def on_set_default_clicked(self):
        self.configuration_settings.update_main_setting("local_llm", self.full_path)
        self.refresh_method()
    
    def on_launch_server_clicked(self):
        self.btn_launch_server.setText(self.translations.get("button_disable_server", "Unload model"))
        QApplication.processEvents()
        self.server_loaded = True
        
        try:
            self.btn_launch_server.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        
        self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
        self.launch_server_method()
    
    def on_unload_model_clicked(self):
        self.btn_launch_server.setText(self.translations.get("button_launch_server", "Load model"))
        QApplication.processEvents()
        self.server_loaded = False
        
        try:
            self.btn_launch_server.clicked.disconnect()
        except (TypeError, RuntimeError):
            pass
        
        self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)
        self.stop_server_method()

    def on_delete_clicked(self):
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        msg_box.setWindowTitle(self.translations.get("delete_model", "Delete LLM"))
        
        msg_box.setStyleSheet("""
            QMessageBox { background-color: #1e1e24; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QPushButton { background-color: rgba(255, 255, 255, 0.05); color: white; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 5px 15px; min-width: 60px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3); }
        """)
        
        model_name = self.name_label.text()
        first_text = self.translations.get("model_widget_delete", "Do you want to delete the model:")
        second_text = self.translations.get("model_widget_delete_2", "This action cannot be canceled.")
        message_text = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: "Inter Tight", Arial, sans-serif; font-size: 14px; color: #e0e0e0; }}
                        h1 {{ font-size: 16px; margin-bottom: 10px; font-weight: normal; }}
                        .model-name {{ color: #EF9A9A; font-weight: bold; }}
                        p {{ color: #a0a0a0; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <h1>{first_text}<span class="model-name"> {model_name}?</span></h1>
                    <p>{second_text}</p>
                </body>
            </html>
        """
        msg_box.setText(message_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        
        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(self.full_path)
                self.refresh_method()
            except Exception as e:
                error_box = QMessageBox()
                error_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                error_box.setWindowTitle("Delete Error")
                error_box.setText(f"Couldn't delete the model:\n{str(e)}")
                error_box.setStyleSheet("QMessageBox { background-color: #1e1e24; color: #e0e0e0; } QLabel { color: #e0e0e0; }")
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.exec()
        
    def enterEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.glass_card.setStyleSheet(self.glass_style_normal)
        super().leaveEvent(event)

class PersonaItemWidget(QWidget):
    def __init__(self, name="", main_name="", description="", avatar_path=None, 
                 is_plus_item=False, open_editor_method=None, open_editor_by_name_method=None, 
                 refresh_method=None, parent=None, default_btn_translation="Set as default", delete_btn_translation="Delete"):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.configuration_settings = configuration.ConfigurationSettings()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        self.name = name
        self.main_name = main_name
        self.open_editor_method = open_editor_method
        self.open_editor_by_name_method = open_editor_by_name_method
        self.refresh_method = refresh_method

        self.name_label = QLabel(name)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12pt;")

        if not is_plus_item:
            self.avatar_label = QLabel()
            if avatar_path and os.path.exists(avatar_path):
                pixmap = QtGui.QPixmap(avatar_path).scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            else:
                pixmap = QtGui.QPixmap("app/gui/icons/person.png").scaled(
                    60, 60, Qt.AspectRatioMode.KeepAspectRatio
                )
            mask = QPixmap(pixmap.size())
            mask.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QtCore.Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
            painter.end()

            pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
            self.avatar_label.setPixmap(pixmap.scaled(60, 60, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
            self.avatar_label.setFixedSize(60, 60)
            self.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.avatar_label.setScaledContents(True)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)
            info_layout.setContentsMargins(0, 15, 0, 15)

            self.desc_label = QLabel(description)
            self.desc_label.setStyleSheet("font-size: 10pt; color: gray;")

            info_layout.addWidget(self.name_label)
            info_layout.addWidget(self.desc_label)

            self.button_layout = QHBoxLayout()

            current_default_persona = self.configuration_settings.get_user_data("default_persona")
            if not current_default_persona:
                self.configuration_settings.update_user_data("default_persona", "None")
            else:
                if main_name != current_default_persona:
                    self.set_default_button = QPushButton(default_btn_translation)
                    self.set_default_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                    self.set_default_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    self.set_default_button.setStyleSheet("""
                        QPushButton {
                            background-color: #2D2D2D;
                            color: #BBBBBB;
                            border-radius: 10px;
                            border: 1px solid #383838;
                            padding: 0;
                        }

                        QPushButton:hover {
                            background-color: #333333;
                            border: 1px solid #404040;
                        }

                        QPushButton:pressed {
                            background-color: #202020;
                            color: #999999;
                        }
                    """)
                    self.set_default_button.setFixedSize(150, 35)
                    self.set_default_button.setObjectName("setdefaultButton")
                    font = QtGui.QFont()
                    font.setFamily("Inter Tight SemiBold")
                    font.setPointSize(7)
                    font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
                    self.set_default_button.setFont(font)
                    try:
                        self.set_default_button.clicked.disconnect()
                    except Exception as e:
                        pass
                    self.set_default_button.clicked.connect(lambda _, n=main_name: self.set_default_persona(n))
                    self.button_layout.addWidget(self.set_default_button)

            self.delete_button = QPushButton(delete_btn_translation)
            self.delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(7)
            font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            self.delete_button.setFont(font)

            self.delete_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            self.delete_button.setFixedSize(130, 35)
            self.delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #D32F2F;
                    color: rgb(227, 227, 227);
                    font-size: 12px;
                    border-radius: 6px;
                    border: 1px solid #9A0007;
                    padding: 5px;
                }

                QPushButton:hover {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                    stop: 0 #E53935, stop: 1 #C62828);
                    border: 1px solid #B71C1C;
                }

                QPushButton:pressed {
                    background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                    stop: 0 #B71C1C, stop: 1 #E53935);
                    border: 1px solid #7A0000;
                }

                QPushButton:disabled {
                    background-color: #EF9A9A;
                    color: #A8A8A8;
                    border: 1px solid #BDBDBD;
                }
            """)
            self.delete_button.setObjectName("deleteButton")
            self.button_layout.addWidget(self.delete_button)

            self.mousePressEvent = self.on_click_persona

            layout.addWidget(self.avatar_label)
            layout.addLayout(info_layout)
            layout.addLayout(self.button_layout)
        else:
            self.name_label.setText("+")
            self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_label.setStyleSheet("font-size: 20pt; font-weight: bold; color: white;")

            self.mousePressEvent = self.on_click

            layout.addWidget(self.name_label)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def on_click(self, event):
        self.open_editor_method()
    
    def on_click_persona(self, event):
        self.open_editor_by_name_method(self.main_name)

    def set_default_persona(self, name):
        self.configuration_settings.update_user_data("default_persona", name)
        self.refresh_method()

class BackgroundCard(QtWidgets.QFrame):
    def __init__(self, name, image_path, is_selected, click_callback, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 150)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.name = name
        self.image_path = image_path
        self.is_selected = is_selected
        self.click_callback = click_callback

        if image_path == "Default":
            self.pixmap = QPixmap(200, 150)
            self.pixmap.fill(QColor(15, 15, 18))
        else:
            original_pixmap = QPixmap(image_path)
            self.pixmap = original_pixmap.scaled(
                200, 150, 
                Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                Qt.TransformationMode.SmoothTransformation
            )

        self._hover_scale = 1.0
        self.anim_scale = QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(200)
        self.anim_scale.setEasingCurve(QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_scale.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_scale.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()

        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 12, 12)
        painter.setClipPath(path)

        painter.save()
        painter.translate(rect.center())
        painter.scale(self._hover_scale, self._hover_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        gradient = QtGui.QLinearGradient(0, rect.height() * 0.5, 0, rect.height())
        gradient.setColorAt(0, QColor(0, 0, 0, 0))
        gradient.setColorAt(1, QColor(0, 0, 0, 200))
        painter.fillRect(rect, QtGui.QBrush(gradient))

        if self.is_selected:
            painter.setPen(QtGui.QPen(QColor(76, 175, 80), 4))
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 10, 10)
        else:
            painter.setPen(QtGui.QPen(QColor(255, 255, 255, 30), 2))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 11, 11)

        painter.setPen(QColor(255, 255, 255, 240))
        font = QFont("Inter Tight SemiBold", 11, QFont.Weight.Bold)
        painter.setFont(font)
        
        display_name = os.path.splitext(self.name)[0] if self.name != "Default" else self.translations.get("background_changer_default_btn", "Default Theme")
        
        text_rect = QtCore.QRect(10, rect.height() - 35, rect.width() - 20, 30)
        painter.drawText(
            text_rect, 
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, 
            display_name
        )

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_callback(self.image_path)
        super().mousePressEvent(event)

class BackgroundChangerWindow(QDialog):
    def __init__(self, ui=None, translation=None, parent=None):
        super().__init__(parent)
        self.translations = translation if translation else {}
        self.ui = ui

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(940, 540)

        self.configuration_settings = configuration.ConfigurationSettings()
        
        self.current_bg = self.configuration_settings.get_main_setting("chat_background_image")

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        self.main_frame = QtWidgets.QFrame()
        self.main_frame.setStyleSheet("""
            QFrame#MainFrame {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 15px;
            }
        """)
        self.main_frame.setObjectName("MainFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.main_frame.setGraphicsEffect(shadow)

        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        
        title = QLabel(self.translations.get("background_changer_label_1", "Choose a background for the chat"))
        title.setStyleSheet("font-family: 'Inter Tight SemiBold'; font-size: 18px; color: white;")
        
        close_btn = QPushButton("×")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        close_btn.setFont(font)
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                font-size: 20px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #ff6b6b;
            }
        """)
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        frame_layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: transparent;
                min-height: 0px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(container)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        is_default_selected = (self.current_bg == "None" or not self.current_bg)
        default_card = BackgroundCard("Default", "Default", is_default_selected, self.select_background)
        default_card.translations = self.translations
        grid_layout.addWidget(default_card, 0, 0)

        images_directory = "assets/backgrounds"
        if os.path.exists(images_directory):
            image_files = [f for f in os.listdir(images_directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            row = 0
            col = 1
            max_cols = 4

            for img_file in image_files:
                path = os.path.join(images_directory, img_file).replace("\\", "/")
                
                is_selected = (self.current_bg == path)
                
                card = BackgroundCard(img_file, path, is_selected, self.select_background)
                grid_layout.addWidget(card, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

        scroll_area.setWidget(container)
        frame_layout.addWidget(scroll_area)

        main_layout.addWidget(self.main_frame)

    def get_scroll_area_base_style(self):
        return """
            QScrollBar:vertical { width: 0px; background: transparent; }
            QScrollBar::handle:vertical { background: transparent; }
            QScrollBar::sub-page:vertical { background: none; border: none; }
            QScrollBar:horizontal { background-color: #2b2b2b; height: 10px; border-radius: 5px; }
            QScrollBar::handle:horizontal { background-color: #383838; width: 10px; border-radius: 3px; margin: 2px; }
            QScrollBar::handle:horizontal:hover { background-color: #454545; }
            QScrollBar::handle:horizontal:pressed { background-color: #424242; }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { border: none; background: none; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """

    def select_background(self, image_path):
        base_style = self.get_scroll_area_base_style()

        if image_path and image_path != "Default":
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    border-image: url({image_path}) 0 0 0 0 stretch stretch;
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                    border-radius: 10px;
                }}
                {base_style}
            """)
            self.configuration_settings.update_main_setting("chat_background_image", image_path)
        else:
            self.ui.chat_page.setStyleSheet(f"""
                QWidget#chat_page {{
                    background-position: center;
                    background-repeat: no-repeat;
                }}
            """)
            self.ui.scrollArea_chat.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                    border-radius: 10px;
                }}
                {base_style}
            """)
            self.configuration_settings.update_main_setting("chat_background_image", "None")

        self.close()

class CharacterCardList(QtWidgets.QFrame):
    def __init__(self, character_name, image_path, icon_api_path, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 270)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.character_name = character_name
        self.open_chat = method
        
        self.pixmap = QtGui.QPixmap(image_path)
        if self.pixmap.isNull():
            self.pixmap = QtGui.QPixmap("app/gui/icons/logotype.png")
            
        self.icon_api_pixmap = QtGui.QPixmap(icon_api_path).scaled(
            20, 20, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation
        )
        
        self.shadow_effect = QtWidgets.QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow_effect)

        self._hover_scale = 1.0
        self.anim_scale = QtCore.QPropertyAnimation(self, b"hover_scale")
        self.anim_scale.setDuration(350)
        self.anim_scale.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._darkness_alpha = 100.0
        self.anim_dark = QtCore.QPropertyAnimation(self, b"darkness_alpha")
        self.anim_dark.setDuration(350)
        self.anim_dark.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)

        self._info_alpha = 255.0
        self.anim_info = QtCore.QPropertyAnimation(self, b"info_alpha")
        self.anim_info.setDuration(300)
        self.anim_info.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        
        self.action_panel = QtWidgets.QFrame(self)
        self.action_panel.setStyleSheet("background-color: rgba(15, 15, 15, 0.9); border-radius: 15px;")
        self.action_panel.setGeometry(10, 280, 190, 45) 
        self.action_panel_layout = QtWidgets.QHBoxLayout(self.action_panel)
        self.action_panel_layout.setContentsMargins(5, 0, 5, 0)
        self.action_panel_layout.setSpacing(5)
        
        self.panel_anim = QtCore.QPropertyAnimation(self.action_panel, b"pos")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)

    @QtCore.pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale

    @hover_scale.setter
    def hover_scale(self, value):
        self._hover_scale = value
        self.update()

    @QtCore.pyqtProperty(float)
    def darkness_alpha(self):
        return self._darkness_alpha

    @darkness_alpha.setter
    def darkness_alpha(self, value):
        self._darkness_alpha = value
        self.update()

    @QtCore.pyqtProperty(float)
    def info_alpha(self):
        return self._info_alpha

    @info_alpha.setter
    def info_alpha(self, value):
        self._info_alpha = value
        self.update()

    def enterEvent(self, event):
        self.anim_scale.setEndValue(1.05)
        self.anim_dark.setEndValue(0.0)
        self.anim_info.setEndValue(0.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 215))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        if hasattr(self, 'more_btn_anim'):
            self.more_btn_anim.setEndValue(QtCore.QPoint(self.width() - 40, 10))
            self.more_btn_anim.start()
        
        self.shadow_effect.setOffset(0, 8)
        self.shadow_effect.setBlurRadius(25)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_scale.setEndValue(1.0)
        self.anim_dark.setEndValue(100.0)
        self.anim_info.setEndValue(255.0)
        self.panel_anim.setEndValue(QtCore.QPoint(10, 280))
        
        self.anim_scale.start()
        self.anim_dark.start()
        self.anim_info.start()
        self.panel_anim.start()

        if hasattr(self, 'more_btn_anim'):
            self.more_btn_anim.setEndValue(QtCore.QPoint(self.width() - 40, -40))
            self.more_btn_anim.start()
        
        self.shadow_effect.setOffset(0, 5)
        self.shadow_effect.setBlurRadius(15)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), 15, 15)
        painter.setClipPath(path)

        painter.save()
        scale_factor = max(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
        final_scale = scale_factor * self._hover_scale
        painter.translate(rect.center())
        painter.scale(final_scale, final_scale)
        painter.drawPixmap(-self.pixmap.width() // 2, -self.pixmap.height() // 2, self.pixmap)
        painter.restore()

        if self._darkness_alpha > 0:
            painter.fillRect(rect, QtGui.QColor(0, 0, 0, int(self._darkness_alpha)))

        if self._info_alpha > 0:
            gradient = QtGui.QLinearGradient(0, rect.height() * 0.4, 0, rect.height())
            gradient.setColorAt(0, QtGui.QColor(0, 0, 0, 0))
            gradient.setColorAt(1, QtGui.QColor(0, 0, 0, int(min(220, self._info_alpha))))
            painter.fillRect(rect, QtGui.QBrush(gradient))

            painter.setPen(QtGui.QColor(255, 255, 255, int(self._info_alpha)))
            font = QtGui.QFont("Inter Tight SemiBold", 13, QtGui.QFont.Weight.Bold)
            painter.setFont(font)
            
            text_rect = QtCore.QRect(15, rect.height() - 75, rect.width() - 45, 65)
            painter.drawText(
                text_rect, 
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.TextFlag.TextWordWrap, 
                self.character_name
            )

            if hasattr(self, 'icon_api_pixmap') and not self.icon_api_pixmap.isNull():
                painter.setOpacity(self._info_alpha / 255.0)
                icon_rect = QtCore.QRect(rect.width() - 30, rect.height() - 30, 20, 20)
                painter.drawPixmap(icon_rect, self.icon_api_pixmap)
                painter.setOpacity(1.0)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            import asyncio
            asyncio.create_task(self.open_chat(self.character_name)) 
        super().mousePressEvent(event)

class AnimatedHoverButton(QtWidgets.QPushButton):
    def __init__(self, icon_path, hover_color, tooltip_text, parent=None, base_color=None):
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.setToolTip(tooltip_text)
        
        self.setIcon(QtGui.QIcon(icon_path))
        self.setIconSize(QtCore.QSize(18, 18))

        if base_color:
            self._base_color = QtGui.QColor(base_color) if isinstance(base_color, (str, int)) else base_color
        else:
            self._base_color = QtGui.QColor(0, 0, 0, 0)
            
        self._hover_color = QtGui.QColor(hover_color) if isinstance(hover_color, (str, int)) else hover_color
        
        self._current_color = QtGui.QColor(self._base_color)

        self.anim = QtCore.QVariantAnimation(self)
        self.anim.setDuration(200)
        self.anim.valueChanged.connect(self._update_color)

        self.setStyleSheet("""
            background-color: transparent; 
            border: none;
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)

    def _update_color(self, color):
        self._current_color = color
        self.update()

    def enterEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_color)
        self.anim.setEndValue(self._hover_color)
        self.anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self._current_color)
        self.anim.setEndValue(self._base_color)
        self.anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        painter.setBrush(self._current_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(self.rect())
        
        painter.end()
        super().paintEvent(event)

class ToastNotification(QWidget):
    def __init__(self, parent, message, toast_type="success", duration=3000):
        super().__init__(parent)
        self.parent_widget = parent
        
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        if toast_type == "success":
            bg_color = "#27682A"
            icon_text = "✓"
        elif toast_type == "error":
            bg_color = "#8A2222"
            icon_text = "❌"
        else:
            bg_color = "#125292"
            icon_text = "ℹ️"

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.frame = QtWidgets.QFrame(self)
        self.frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.frame.setGraphicsEffect(shadow)

        frame_layout = QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(15, 10, 15, 10)
        frame_layout.setSpacing(10)

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("color: white; font-size: 14px; background: transparent; border: none;")
        
        text_label = QLabel(message)
        font = QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        text_label.setFont(font)
        text_label.setStyleSheet("""
            color: white; 
            font-family: 'Inter Tight SemiBold'; 
            font-size: 13px; 
            background: transparent; 
            border: none;
        """)
        
        frame_layout.addWidget(icon_label)
        frame_layout.addWidget(text_label)
        self.layout.addWidget(self.frame)

        self.opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.hide_toast)
        self.duration = duration

        self.adjustSize()
        self.update_position()

    def update_position(self):
        if self.parent_widget:
            parent_rect = self.parent_widget.rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 50
            self.move(x, y)

    def show_toast(self):
        self.show()
        self.raise_()
        
        self.anim_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_in.setDuration(300)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim_in.start()

        self.timer.start(self.duration)

    def hide_toast(self):
        try:
            self.timer.stop()
            
            if hasattr(self, "anim_out") and self.anim_out.state() == QPropertyAnimation.State.Running:
                return
                
            self.anim_out = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.anim_out.setDuration(300)
            self.anim_out.setStartValue(self.opacity_effect.opacity())
            self.anim_out.setEndValue(0.0)
            self.anim_out.setEasingCurve(QEasingCurve.Type.InQuad)
            self.anim_out.finished.connect(self.deleteLater)
            self.anim_out.start()
        except RuntimeError:
            pass

class TypingIndicatorWidget(QWidget):
    def __init__(self, character_name, avatar_path, s_appearance, margins, parent=None):
        super().__init__(parent)
        self.configuration_settings = configuration.ConfigurationSettings()

        self.translations = {}
        self.selected_language = self.configuration_settings.get_main_setting("program_language")
        match self.selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(*margins)
        self.layout.setSpacing(5)

        self.character_name = character_name


        raw_pixmap = QPixmap(avatar_path)
            
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

        self.avatar_label = QLabel()
        self.avatar_label.setPixmap(final_avatar_pixmap)
        self.avatar_label.setFixedSize(label_size, label_size)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")

        self.bubble_label = QLabel()
        self.bubble_label.setTextFormat(Qt.TextFormat.RichText)
        
        r = s_appearance["border_radius"]
        fs = s_appearance["font_size"]
        tc = s_appearance["text_color"]
        h = s_appearance["char_bubble_color"].lstrip("#")
        bg_rgb = f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"
        
        self.bubble_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({bg_rgb}, 0.8);
                color: {tc};
                border-top-right-radius: {r}px;
                border-bottom-right-radius: {r}px;
                border-top-left-radius: {r}px;
                border-bottom-left-radius: 0px;
                padding: 12px;
                font-size: {fs}px;
                margin: 5px;
            }}
        """)

        self.dot_count = 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.animate_dots)
        self.timer.start(400)

        self.layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
        self.layout.addWidget(self.bubble_label)
        self.layout.addStretch()

        self.animate_dots()
    
    def load_translation(self, language):
        """
        Loads translation strings from a YAML file based on the program language.
        """
        file_path = f".../.../app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

    def animate_dots(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "• " * self.dot_count
        character_name = self.character_name
        typingIndicator_text = self.translations.get("typingIndicator_text", f"{character_name} <span style='color: #888;'>typing {dots}</span>").format(character_name=self.character_name, dots=dots)
        self.bubble_label.setText(typingIndicator_text)

class SmoothMessageFrame(QtWidgets.QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_height = -1
        
        self.height_anim = QtCore.QVariantAnimation(self)
        self.height_anim.setDuration(150)
        self.height_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutCubic)
        self.height_anim.valueChanged.connect(self._on_height_changed)
        
        self.scroll_callback = None

    def _on_height_changed(self, new_height):
        self.setFixedHeight(new_height)
        if self.scroll_callback:
            self.scroll_callback()

    def update_smooth_height(self):
        if not self.layout(): return
        
        self.layout().activate()
        new_target = self.layout().sizeHint().height()

        current_height = self.height()

        if new_target != self._target_height and new_target > current_height:
            self._target_height = new_target
            
            self.height_anim.stop()
            self.height_anim.setStartValue(current_height)
            self.height_anim.setEndValue(new_target)
            self.height_anim.start()

    def finalize_size(self):
        self.height_anim.stop()
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)

class TypewriterEffect(QtCore.QObject):
    def __init__(self, label, frame, scroll_area, interface, char_name, user_name, interval=30):
        super().__init__()
        self.label = label
        self.frame = frame          
        self.scroll_area = scroll_area
        self.interface = interface
        self.char_name = char_name
        self.user_name = user_name
        
        self.raw_text_buffer = ""
        self.queue = deque()
        
        self.finished_event = asyncio.Event()
        self.finished_event.set()
        
        self.timer = QtCore.QTimer()
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self._on_timeout)
        
        if hasattr(self.frame, 'scroll_callback'):
            self.frame.scroll_callback = self._force_scroll_down

    def _force_scroll_down(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def write(self, text_chunk):
        if not text_chunk: return
        self.finished_event.clear()
        
        for char in text_chunk:
            self.queue.append(char)
        
        if not self.timer.isActive():
            self.timer.start()

    def _on_timeout(self):
        if not self.queue:
            self.timer.stop()
            try:
                if hasattr(self.frame, 'finalize_size'):
                    self.frame.finalize_size()
            except RuntimeError:
                pass
            self.finished_event.set()
            return

        chunk_size = 1
        q_len = len(self.queue)
        if q_len > 50: chunk_size = 3
        if q_len > 200: chunk_size = 10

        for _ in range(chunk_size):
            if self.queue:
                self.raw_text_buffer += self.queue.popleft()
            else:
                break
        
        self._update_display()

    def _update_display(self):
        try:
            processed_html = self.interface.markdown_to_html(self.raw_text_buffer)
            processed_html = self.interface.apply_macros(processed_html, self.char_name, self.user_name)
            self.label.setText(processed_html)
            
            if hasattr(self.frame, 'update_smooth_height'):
                self.frame.update_smooth_height()
            
            scrollbar = self.scroll_area.verticalScrollBar()
            if scrollbar.value() >= scrollbar.maximum() - 50:
                self._force_scroll_down()
                
        except RuntimeError:
            self.stop()
            return

    async def wait_until_finished(self):
        if self.queue or self.timer.isActive():
            await self.finished_event.wait()

    def stop_and_flush(self):
        self.timer.stop()
        while self.queue:
            self.raw_text_buffer += self.queue.popleft()
            
        try:
            self._update_display()
            if hasattr(self.frame, 'finalize_size'):
                self.frame.finalize_size()
        except RuntimeError:
            pass
            
        self.finished_event.set()
        return self.raw_text_buffer

    def stop(self):
        self.timer.stop()
        self.queue.clear()
        self.finished_event.set()
        try:
            if hasattr(self.frame, 'finalize_size'):
                self.frame.finalize_size()
        except RuntimeError:
            pass

class MethodCard(QFrame):
    clicked = QtCore.pyqtSignal()
    
    def __init__(self, title, description, icon_path, badge_text=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(95)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.setStyleSheet("""
            MethodCard {
                background-color: #2B2B2B;
                border: 1px solid #3A3A3A;
                border-radius: 12px;
            }
            MethodCard:hover {
                background-color: #363636; 
                border: 1px solid #555555;
            }
            QLabel { border: none; background: transparent; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(20)

        icon_label = QLabel()
        pixmap = QtGui.QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(36, 36)
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #E0E0E0; font-size: 15px; font-weight: bold;")
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #A0A0A0; font-size: 11px;")
        desc_lbl.setWordWrap(True)
        
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(desc_lbl)
        layout.addLayout(text_layout, 1)

        if badge_text:
            badge = QLabel(badge_text)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet("""
                background-color: rgba(100, 180, 255, 0.15);
                color: #64B4FF;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: bold;
            """)
            layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
