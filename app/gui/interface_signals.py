import os
import re
import uuid
import json
import base64
import hashlib
import logging
import threading
import traceback
import datetime
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
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QUrl, Qt, QTimerEvent, QPropertyAnimation, QEasingCurve, QPointF
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QPainter, QAction, QColor
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QMessageBox, QPushButton,
    QWidget, QHBoxLayout, QDialog, QVBoxLayout, QStackedWidget, QFileDialog,
    QGraphicsDropShadowEffect, QFrame, QMenu, QTextEdit, QLineEdit
)

from app.utils.ai_clients.local_ai_client import LocalAI
from app.utils.ai_clients.mistral_ai_client import MistralAI
from app.utils.ai_clients.openai_client import OpenAI
from app.utils.ai_clients.character_ai_client import CharacterAI
from app.utils.translator import Translator
from app.utils.character_cards import CharactersCard
from app.utils.text_to_speech import ElevenLabs, XTTSv2, EdgeTTS, KokoroTTS
from app.utils.ambient_client import AmbientPlayer
from app.utils.models_hub import ModelSearch, ModelRecommendations, ModelPopular, ModelInformation, ModelRepoFiles, FileSelectorDialog, FileDownloader, ModelItemWidget
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
        self.cai_cards = []
        self.gate_cards = []

        # --- Scroll Area Setup ---
        self.grid_layout = QtWidgets.QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(0, 20, 20, 20)
        self.container = QWidget()
        self.container.setLayout(self.grid_layout)
        self._setup_scroll_area(self.ui.scrollArea_characters_list, self.container)

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

        # --- Configuration Initialization ---
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.configuration_settings.update_main_setting("conversation_method", "Character AI")

        # --- AI Client Initialization ---
        self.character_ai_client = CharacterAI()
        self.mistral_ai_client = MistralAI()
        self.open_ai_client = OpenAI()
        self.local_ai_client = LocalAI(self.ui)
        
        # --- TTS Client Initialization ---
        self.eleven_labs_client = ElevenLabs()
        self.edge_tts_client = EdgeTTS()

        # --- Utility Modules ---
        self.translator = Translator()
        self.character_card_client = CharactersCard()

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

        layout.insertWidget(1, self.ui.textEdit_write_user_message)

        self.ui.frame_send_message.setMinimumHeight(40)
        self.ui.frame_send_message.setMaximumHeight(40)

        self.ui.frame_send_message_full.setMinimumHeight(40)
        self.ui.frame_send_message_full.setMaximumHeight(40)

        self.ui.textEdit_write_user_message.textChanged.connect(self._adjust_frame_height)

        return self.ui.textEdit_write_user_message
    
    def _adjust_frame_height(self):
        """
        Dynamically adjusts the height of the message input frame based on the content size.
        Ensures the frame does not exceed a maximum height of 400 pixels.
        """
        text_edit_height = self.ui.textEdit_write_user_message.calculate_content_height()

        if text_edit_height > self.current_max_height:
            self.current_max_height = min(text_edit_height, 400)

        new_height = max(40, min(text_edit_height, self.current_max_height))
        self.ui.frame_send_message.setFixedHeight(new_height)
        self.ui.frame_send_message_full.setFixedHeight(new_height)

        self.ui.scrollArea_chat.updateGeometry()
        self.ui.verticalLayout_6.invalidate()
        self.ui.verticalLayout_6.activate()

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
        dialog.setFixedSize(900, 500)

        dialog.setStyleSheet("""
            QDialog {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #1e1e1e, stop:1 #121212);
                border-radius: 16px;
            }
            QLabel#title_label {
                font-size: 20pt;
                font-weight: bold;
                color: #ffa726;
                text-align: center;
                margin-bottom: 10px;
            }
            QLabel#version_label {
                font-size: 10pt;
                color: #888888;
                text-align: right;
            }
            QLabel#description_label {
                font-size: 12pt;
                color: #d0d0d0;
                line-height: 1.5;
            }
            QLabel#sub_label {
                font-size: 12pt;
                color: #d0d0d0;
                line-height: 1.5;
            }
            a {
                color: #ffa726;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            QPushButton {
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                background-color: #4a4a4a;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
            }
            .footer {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 15px;
            }
        """)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dialog.setFont(font)
        main_layout = QtWidgets.QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Soul of Waifu v2.2.0")
        title.setObjectName("title_label")

        title_layout.addStretch()
        title_layout.addWidget(title)
        title_layout.addStretch()

        description = self.translations.get(
            "about_program_description",
            "<b>Soul of Waifu</b> is your ultimate tool for bringing AI-driven characters to life. "
            "With support for advanced APIs from leading AI platforms and local LLMs, you can customize "
            "every aspect of your character. With advanced features like high-quality Text-To-Speech and "
            "Speech-To-Text, you can have natural conversations with your characters. Take it a step further "
            "with Speech-To-Speech mode, which lets you truly talk to your character as if they were right there "
            "with you. <br><br>Want to add personality and emotion? Connect a Live2D model that brings your "
            "character to life with dynamic expressions, or use avatar images to give them a unique visual identity. "
            "Soul of Waifu supports customization at every level—create a character from scratch, import pre-made "
            "character cards, or tweak settings to match your preferences."
        )

        description_label = QtWidgets.QLabel(description)
        description_label.setObjectName("description_label")
        description_label.setWordWrap(True)
        description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)

        sub_description = self.translations.get(
            "about_program_sub_description",
            "Encounter bugs, have suggestions, or just want to share your ideas? Join the vibrant community on our "
            "official <a href='https://discord.gg/6vFtQGVfxM'>Discord server</a>. Your feedback shapes the future "
            "of Soul of Waifu. Together we make a place where dreams become reality!"
        )

        sub_label = QtWidgets.QLabel(sub_description)
        sub_label.setObjectName("sub_label")
        sub_label.setWordWrap(True)
        sub_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)

        developed = self.translations.get("creator_label", "Developed by")
        version = self.translations.get("simple_version_label", "Version")
        version_label = QtWidgets.QLabel(f"{version} 2.2.0 • {developed} <a href='https://github.com/jofizcd'>jofizcd</a>")
        version_label.setObjectName("version_label")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.addWidget(version_label)
        footer_layout.setAlignment(version_label, QtCore.Qt.AlignmentFlag.AlignRight) 

        close_button = QtWidgets.QPushButton(self.translations.get("update_available_close", "Close"))
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.clicked.connect(dialog.accept)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        main_layout.addLayout(title_layout)
        main_layout.addWidget(description_label)
        main_layout.addWidget(sub_label)
        main_layout.addLayout(footer_layout)
        main_layout.addLayout(button_layout)

        dialog.exec()

    def on_pushButton_main_clicked(self):
        asyncio.create_task(self.set_main_tab())

    def on_pushButton_options_clicked(self):
        self.ui.pushButton_options.setChecked(True)
        self.ui.stackedWidget.setCurrentIndex(5)

    def on_pushButton_models_hub_clicked(self):
        self.ui.pushButton_models_hub.setChecked(True)
        self.ui.stackedWidget.setCurrentIndex(7)
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
        
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("personas_editor_title", "Personas Editor"))
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
            QLineEdit, QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
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
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        list_widget = QtWidgets.QListWidget()
        list_widget.setObjectName("listWidget_personas")
        list_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

        editor_area = QWidget()
        editor_area.setObjectName("editor_area")
        editor_area.setVisible(False)
        
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        avatar_label = QLabel()
        avatar_label.setFixedSize(80, 80)
        avatar_label.setStyleSheet("border: 1px solid #555; border-radius: 5px;")

        def choose_avatar():
            file_dialog = QFileDialog()
            path, _ = file_dialog.getOpenFileName(dialog, "Choose Avatar", "", "Images (*.png *.jpg *.jpeg)")
            if path:
                pixmap = QtGui.QPixmap(path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
                avatar_label.setPixmap(pixmap)

                editor_widgets["current_state"]["current_avatar_path"] = path

        avatar_button = QPushButton(self.translations.get("personas_editor_choose_avatar", "Choose avatar"))
        avatar_button.setFixedHeight(40)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(7)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        avatar_button.setFont(font)
        avatar_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        avatar_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 1 #1e1e1e
                );
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 1 #222222
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
        """)
        avatar_button.clicked.connect(choose_avatar)

        name_line_edit = QLineEdit()
        name_line_edit.setPlaceholderText(self.translations.get("personas_editor_name", "Persona's name"))

        description_text_edit = QTextEdit()
        description_text_edit.setPlaceholderText(self.translations.get("personas_editor_description", "Persona's description"))

        close_button = QPushButton(self.translations.get("personas_editor_close", "Close editor"))
        close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        close_button.setFixedHeight(40)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 1 #1e1e1e
                );
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 1 #222222
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
        """)
        add_button = QPushButton(self.translations.get("personas_editor_add", "Add persona"))
        add_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        add_button.setFixedHeight(40)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 1 #1e1e1e
                );
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 1 #222222
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
        """)

        close_button.setFont(font)
        add_button.setFont(font)

        editor_widgets = {
            "avatar_label": avatar_label,
            "name_line_edit": name_line_edit,
            "description_text_edit": description_text_edit,
            "add_button": add_button,
            "current_state": {
                "current_avatar_path": None,
                "current_item_name": ""
            }
        }

        def refresh_personas_list():
            list_widget.clear()

            if not personas_data:
                self.configuration_settings.update_user_data("default_persona", "None")
            else:
                for name in personas_data:
                    data = personas_data[name]
                    item = QtWidgets.QListWidgetItem()
                    item.setSizeHint(QtCore.QSize(0, 80))

                    widget = PersonaItemWidget(
                        name=data["user_name"],
                        main_name=name,
                        description=data.get("user_description", ""),
                        avatar_path=data.get("user_avatar"),
                        is_plus_item=False,
                        open_editor_by_name_method=show_persona_editor_by_name,
                        refresh_method=refresh_personas_list,
                        default_btn_translation=self.translations.get("personas_editor_default_btn", "Set as default"),
                        delete_btn_translation=self.translations.get("personas_editor_delete_btn", "Delete")
                    )

                    try:
                        widget.delete_button.clicked.disconnect()
                    except Exception as e:
                        pass
            
                    widget.delete_button.clicked.connect(lambda _, n=name: delete_persona(n))

                    list_widget.addItem(item)
                    list_widget.setItemWidget(item, widget)

            plus_item = QtWidgets.QListWidgetItem()
            plus_item.setSizeHint(QtCore.QSize(0, 80))

            widget = PersonaItemWidget(is_plus_item=True, open_editor_method=show_persona_editor)
            list_widget.addItem(plus_item)
            list_widget.setItemWidget(plus_item, widget)

        def show_persona_editor():
            reset_editor()

            try:
                add_button.clicked.disconnect()
            except Exception as e:
                pass

            add_button.clicked.connect(add_persona)

            editor_widgets["current_state"]["current_avatar_path"] = None
            editor_widgets["current_state"]["current_item_name"] = ""
            editor_widgets["avatar_label"].clear()
            
            editor_area.setVisible(True)

        def show_persona_editor_by_name(name):
            editor_area.setVisible(True)

            add_button.setText(self.translations.get("personas_editor_save", "Save changes"))

            try:
                add_button.clicked.disconnect()
            except Exception as e:
                pass

            add_button.clicked.connect(lambda: save_persona(name))
            
            data = personas_data.get(name, {})
            fill_editor(data)

        def fill_editor(data):
            avatar_path = data.get("user_avatar")
            editor_widgets["current_state"]["current_avatar_path"] = avatar_path

            if avatar_path and os.path.exists(avatar_path):
                pixmap = QtGui.QPixmap(avatar_path).scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
            else:
                pixmap = QtGui.QPixmap("app/gui/icons/person.png").scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio)
            editor_widgets["avatar_label"].setPixmap(pixmap)
            editor_widgets["avatar_label"].setScaledContents(True)

            editor_widgets["name_line_edit"].setText(data.get("user_name", ""))
            editor_widgets["description_text_edit"].setPlainText(data.get("user_description", ""))

        def delete_persona(name):
            del personas_data[name]
            self.configuration_settings.update_user_data("personas", personas_data)
            refresh_personas_list()
            editor_area.setVisible(False)
        
        def reset_editor():
            name_line_edit.clear()
            description_text_edit.clear()
            add_button.setText(self.translations.get("personas_editor_add", "Add persona"))

        def close_editor():
            editor_area.setVisible(False)     

        def save_persona(name_original):
            name = editor_widgets["name_line_edit"].text().strip()
            description = editor_widgets["description_text_edit"].toPlainText().strip()
            avatar_path = editor_widgets["current_state"]["current_avatar_path"]

            if not name:
                error_message = self.translations.get("personas_editor_error", "Persona`s name cannot be empty.")
                QMessageBox.warning(dialog, "Error", error_message)
                return
            
            personas_data[name_original] = {
                "user_name": name,
                "user_description": description,
                "user_avatar": avatar_path
            }

            self.configuration_settings.update_user_data("personas", personas_data)
            refresh_personas_list()
            reset_editor()
            editor_area.setVisible(False)

        def add_persona():
            name = editor_widgets["name_line_edit"].text().strip()
            description = editor_widgets["description_text_edit"].toPlainText().strip()
            avatar_path = editor_widgets["current_state"]["current_avatar_path"]

            if not name:
                error_message = self.translations.get("personas_editor_error", "Persona`s name cannot be empty.")
                QMessageBox.warning(dialog, "Error", error_message)
                return

            personas_data[name] = {
                "user_name": name,
                "user_description": description,
                "user_avatar": avatar_path
            }

            self.configuration_settings.update_user_data("personas", personas_data)
            refresh_personas_list()
            reset_editor()
            editor_area.setVisible(False)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(close_button)

        editor_layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        editor_layout.addWidget(avatar_button, alignment=Qt.AlignmentFlag.AlignCenter)
        editor_layout.addWidget(QLabel(self.translations.get("personas_editor_name", "Name:")))
        editor_layout.addWidget(name_line_edit)
        editor_layout.addWidget(QLabel(self.translations.get("personas_editor_description", "Description:")))
        editor_layout.addWidget(description_text_edit)
        editor_layout.addLayout(buttons_layout)

        try:
            close_button.clicked.disconnect()
        except Exception as e:
            pass
        
        close_button.clicked.connect(close_editor)
        
        refresh_personas_list()

        main_layout.addWidget(list_widget)
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
        dialog.setMinimumSize(900, 690)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(30, 30, 30);
                border-radius: 10px;
            }
            QLabel {
                color: rgb(200, 200, 200);
            }
            QLineEdit, QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
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
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
        """)

        layout = QVBoxLayout()

        system_prompt_label = QLabel(self.translations.get("system_prompt_editor_system_prompt", "System prompt"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        system_prompt_label.setFont(font)
        layout.addWidget(system_prompt_label)

        system_prompt_edit = QTextEdit()
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        system_prompt_edit.setFont(font)
        system_prompt_edit.setFixedHeight(240)
        system_prompt_edit.setAcceptRichText(False)
        system_prompt_edit.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextEditable |
            Qt.TextInteractionFlag.TextEditorInteraction
        )
        system_prompt_edit.setPlaceholderText(self.translations.get("system_prompt_editor_system_prompt_edit", "Write the system prompt here"))
        layout.addWidget(system_prompt_edit)

        reorder_label = QLabel(self.translations.get("system_prompt_editor_order", "Prompt Component Order"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        reorder_label.setFont(font)
        layout.addWidget(reorder_label)

        list_widget = QtWidgets.QListWidget()
        list_widget.setDragDropMode(QtWidgets.QListWidget.DragDropMode.InternalMove)
        list_widget.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: #2e2e2e;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 5px;
                outline: 0px;
            }

            QListWidget::item {
                background-color: #3a3a3a;
                border-radius: 6px;
                margin: 2px 0;
                padding: 10px;
                color: #dcdcdc;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }

            QListWidget::item:hover {
                background-color: #4a4a4a;
            }

            QListWidget::item:selected {
                background-color: #5a5a5a;
                color: #ffffff;
                font-weight: bold;
                border-left: 2px solid #7a7a7a;
            }
        """)

        layout.addWidget(list_widget)

        button_layout = QHBoxLayout()
        reset_button = QPushButton(self.translations.get("system_prompt_editor_default_btn", "By default"))
        reset_button.setFixedHeight(40)
        reset_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        reset_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(7)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        reset_button.setFont(font)
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 1 #1e1e1e
                );
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 1 #222222
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
        """)
        button_layout.addWidget(reset_button)
        layout.addLayout(button_layout)

        preset_label = QLabel(self.translations.get("system_prompt_editor_presets", "Presets"))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        preset_label.setFont(font)
        layout.addWidget(preset_label)

        preset_combo = QtWidgets.QComboBox()
        preset_combo.setFixedHeight(45)
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
        layout.addWidget(preset_combo)

        preset_actions_layout = QHBoxLayout()
        new_preset_btn = QPushButton(self.translations.get("system_prompt_editor_new_preset", "New preset"))
        save_preset_button = QPushButton(self.translations.get("system_prompt_editor_save_preset", "Save preset"))
        delete_preset_btn = QPushButton(self.translations.get("system_prompt_editor_delete_preset", "Delete preset"))

        buttons = [new_preset_btn, save_preset_button, delete_preset_btn]
        for button in buttons:
            button.setFixedHeight(30)
            button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            button.setFont(font)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 1 #1e1e1e
                );
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 1 #222222
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
        """)
        
        preset_actions_layout.addWidget(new_preset_btn)
        preset_actions_layout.addWidget(save_preset_button)
        preset_actions_layout.addWidget(delete_preset_btn)
        layout.addLayout(preset_actions_layout)

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
                    QMessageBox {
                        background-color: rgb(27, 27, 27);
                        color: rgb(227, 227, 227);
                    }
                    QLabel {
                        color: rgb(227, 227, 227);
                    }
                """)

                first_text = self.translations.get("system_prompt_editor_delete_preset_first", "Do you really want to remove the preset:")
                second_text = self.translations.get("system_prompt_editor_delete_preset_second", "This action cannot be canceled.")

                message_text = f"""
                    <html>
                        <head>
                            <style>
                                body {{
                                    background-color: #2b2b2b;
                                    font-family: "Segoe UI", Arial, sans-serif;
                                    font-size: 14px;
                                    color: rgb(227, 227, 227);
                                }}
                                h1 {{
                                    font-size: 16px;
                                    margin-bottom: 10px;
                                }}
                                .preset-name {{
                                    color: #FF6347;
                                    font-weight: bold;
                                }}
                            </style>
                        </head>
                        <body>
                            <h1><span class="preset-name">{first_text} "{name}"?</span></h1>
                            <p>{second_text}</p>
                        </body>
                    </html>
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

        dialog.setLayout(layout)
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
        dialog.setMinimumSize(900, 710)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(30, 30, 30);
                border-radius: 10px;
            }
            QLabel {
                color: rgb(200, 200, 200);
            }
            QLineEdit, QTextEdit {
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
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
            QListWidget::item:selected {
                background-color: #5a5a5a;
                color: white;
                font-weight: bold;
            }
        """)

        layout = QVBoxLayout()

        lorebook_label = QLabel(self.translations.get("lorebook_editor_select", "Select Lorebook"))
        layout.addWidget(lorebook_label)

        lorebook_combo = QtWidgets.QComboBox()
        lorebook_combo.setFixedHeight(30)
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
        layout.addWidget(lorebook_combo)

        button_layout = QHBoxLayout()
        create_button = QPushButton(self.translations.get("lorebook_editor_create", "Create"))
        edit_button = QPushButton(self.translations.get("lorebook_editor_edit", "Edit"))
        delete_button = QPushButton(self.translations.get("lorebook_editor_delete", "Delete"))
        import_button = QPushButton(self.translations.get("lorebook_editor_import", "Import"))
        export_button = QPushButton(self.translations.get("lorebook_editor_export", "Export"))
        save_button = QPushButton(self.translations.get("lorebook_editor_save", "Save All"))

        buttons = [create_button, edit_button, delete_button, import_button, export_button, save_button]
        for btn in buttons:
            btn.setFixedHeight(40)
            font = QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            btn.setFont(font)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #2f2f2f, stop:1 #1e1e1e);
                    color: rgb(227, 227, 227);
                    border: 2px solid #3A3A3A;
                    border-radius: 5px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #343434, stop:1 #222222);
                    border: 2px solid #666666;
                }
                QPushButton:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #4a4a4a, stop:1 #3a3a3a);
                    border: 2px solid #888888;
                }
            """)
        button_layout.addWidget(create_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(import_button)
        button_layout.addWidget(export_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

        entry_list_label = QLabel(self.translations.get("lorebook_editor_entries", "Lorebook Entries"))
        layout.addWidget(entry_list_label)

        entry_list = QtWidgets.QListWidget()
        entry_list.setSelectionMode(QtWidgets.QListWidget.SelectionMode.SingleSelection)
        entry_list.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        entry_list.verticalScrollBar().setSingleStep(15)
        entry_list.setStyleSheet("""
            QListWidget {
                background-color: #2e2e2e;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 5px;
                outline: 0px;
            }

            QListWidget::item {
                background-color: #3a3a3a;
                border-radius: 6px;
                margin: 2px 0;
                padding: 10px;
                color: #dcdcdc;
                font-family: "Segoe UI", sans-serif;
                font-size: 14px;
            }

            QListWidget::item:hover {
                background-color: #4a4a4a;
            }

            QListWidget::item:selected {
                background-color: #5a5a5a;
                color: #ffffff;
                font-weight: bold;
                border-left: 2px solid #7a7a7a;
            }
        """)
        layout.addWidget(entry_list)

        key_input = QLineEdit()
        key_input.setPlaceholderText(self.translations.get("lorebook_editor_key_placeholder", "Trigger Keywords (comma-separated)"))
        layout.addWidget(key_input)

        content_input = QTextEdit()
        content_input.setFixedHeight(150)
        content_input.setPlaceholderText(self.translations.get("lorebook_editor_content_placeholder", "Entry Content"))
        layout.addWidget(content_input)

        entry_buttons_layout = QHBoxLayout()
        add_entry_btn = QPushButton(self.translations.get("lorebook_editor_add_entry", "Add Entry"))
        save_entry_btn = QPushButton(self.translations.get("lorebook_editor_save_entry", "Save Entry"))
        delete_entry_btn = QPushButton(self.translations.get("lorebook_editor_delete_entry", "Delete Entry"))

        for btn in [add_entry_btn, save_entry_btn, delete_entry_btn]:
            btn.setFixedHeight(30)
            font = QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(9)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            btn.setFont(font)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #2f2f2f, stop:1 #1e1e1e);
                    color: rgb(227, 227, 227);
                    border: 2px solid #3A3A3A;
                    border-radius: 5px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #343434, stop:1 #222222);
                    border: 2px solid #666666;
                }
                QPushButton:pressed {
                    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #4a4a4a, stop:1 #3a3a3a);
                    border: 2px solid #888888;
                }
            """)
        entry_buttons_layout.addWidget(add_entry_btn)
        entry_buttons_layout.addWidget(save_entry_btn)
        entry_buttons_layout.addWidget(delete_entry_btn)
        layout.addLayout(entry_buttons_layout)

        depth_label = QLabel(self.translations.get("lorebook_editor_depth", "Scan Depth (messages):"))
        layout.addWidget(depth_label)

        depth_combo = QtWidgets.QComboBox()
        depth_combo.addItems([str(i) for i in range(1, 32)])
        depth_combo.setFixedHeight(30)
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
        layout.addWidget(depth_combo)

        lorebooks = {}
        current_lorebook_name = None

        def load_lorebooks():
            nonlocal lorebooks
            lorebooks = self.configuration_settings.load_configuration().get("user_data", {}).get("lorebooks", {})

        def update_lorebook_combo():
            lorebook_combo.clear()
            for name in lorebooks:
                lorebook_combo.addItem(name)

        def apply_current_lorebook():
            nonlocal current_lorebook_name
            name = lorebook_combo.currentText()
            if name in lorebooks:
                current_lorebook_name = name
                data = lorebooks[name]

                entry_list.clear()
                for idx, entry in enumerate(data.get("entries", [])):
                    if entry.get("key"):
                        item_text = ", ".join(entry["key"])
                        entry_list.addItem(item_text)

                depth_combo.setCurrentIndex(data.get("n_depth", 3) - 1)

        def create_new_lorebook():
            lorebook_input_dialog_text = self.translations.get("lorebook_input_dialog", "Enter the name of the new lorebook:")
            lorebook_input_dialog_text_2 = self.translations.get("lorebook_input_dialog_2", "Enter description:")
            name, ok = QInputDialog.getText(dialog, "New Lorebook", lorebook_input_dialog_text)
            if ok and name:
                desc, ok2 = QInputDialog.getText(dialog, "Description", lorebook_input_dialog_text_2)
                if ok2:
                    new_data = {
                        "name": name,
                        "description": desc,
                        "n_depth": 3,
                        "entries": []
                    }
                    lorebooks[name] = new_data
                    self.configuration_settings.update_lorebook(name, new_data)
                    load_lorebooks()
                    update_lorebook_combo()
                    apply_current_lorebook()
                    lorebook_combo.setCurrentText(name)

        def edit_lorebook():
            old_name = lorebook_combo.currentText()
            lorebook_input_dialog_edit_text = self.translations.get("lorebook_input_dialog_edit_text", "Edit lorebook name:")
            lorebook_input_dialog_edit_text_2 = self.translations.get("lorebook_input_dialog_edit_text_2", "Edit description:")
            if old_name in lorebooks:
                new_name, ok = QInputDialog.getText(dialog, "Edit Lorebook", lorebook_input_dialog_edit_text, text=old_name)
                if ok and new_name:
                    desc = QInputDialog.getText(dialog, "Edit Description", lorebook_input_dialog_edit_text_2, text=lorebooks[old_name]["description"])[0]
                    lorebooks[new_name] = lorebooks.pop(old_name)
                    lorebooks[new_name]["name"] = new_name
                    lorebooks[new_name]["description"] = desc
                    self.configuration_settings.delete_lorebook(old_name)
                    self.configuration_settings.update_lorebook(new_name, lorebooks[new_name])
                    load_lorebooks()
                    update_lorebook_combo()
                    apply_current_lorebook()
                    lorebook_combo.setCurrentText(new_name)

        def delete_lorebook():
            lorebook_input_dialog_delete_text = self.translations.get("lorebook_input_dialog_delete_text", "Do you really want to remove the lorebook ")
            lorebook_input_dialog_delete_text_2 = self.translations.get("lorebook_input_dialog_delete_text_2", "This action cannot be undone.")
            name = lorebook_combo.currentText()
            if name in lorebooks:
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                msg_box.setWindowTitle("Delete Lorebook")
                msg_box.setText(f"<h1>{lorebook_input_dialog_delete_text}<span style='color:#FF6347;font-weight:bold;'>{name}</span>?</h1>")
                msg_box.setInformativeText(lorebook_input_dialog_delete_text_2)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: rgb(27, 27, 27);
                        color: rgb(227, 227, 227);
                    }
                    QLabel {
                        color: rgb(227, 227, 227);
                    }
                """)
                reply = msg_box.exec()
                if reply == QMessageBox.StandardButton.Yes:
                    del lorebooks[name]
                    self.configuration_settings.delete_lorebook(name)
                    load_lorebooks()
                    update_lorebook_combo()
                    entry_list.clear()
                    content_input.clear()
                    depth_combo.setCurrentIndex(0)
                    apply_current_lorebook()

        def import_lorebook():
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Select Lorebook File to Import",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            if not file_path:
                return False

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_data = json.load(f)

                new_lorebook = {
                    "name": imported_data.get("name", "unnamed_lorebook"),
                    "description": imported_data.get("description", ""),
                    "n_depth": imported_data.get("scan_depth", 3),
                    "entries": []
                }

                entries = imported_data.get("entries", {})
                for entry_id, entry in entries.items():
                    new_entry = {
                        "key": entry.get("key", []),
                        "content": entry.get("content", "")
                    }
                    new_lorebook["entries"].append(new_entry)

                self.configuration_settings.update_lorebook(imported_data.get("name"), new_lorebook)
                load_lorebooks()
                update_lorebook_combo()
                apply_current_lorebook()
                return True

            except Exception as e:
                logger.error(f"Error when exporting a lorebook: {e}")
                return False

        def export_lorebook(lorebook_name):
            default_file_name = f"{lorebook_name}.json"
            save_path, _ = QFileDialog.getSaveFileName(
                None,
                "Save Lorebook As",
                default_file_name,
                "JSON Files (*.json);;All Files (*)"
            )
            if not save_path:
                return False

            config = self.configuration_settings.load_configuration()
            lorebooks = config.get("user_data", {}).get("lorebooks", {})

            if lorebook_name not in lorebooks:
                logger.error(f"Lorebook '{lorebook_name}' not found.")
                return False

            source = lorebooks[lorebook_name]

            exported_data = {
                "name": source.get("name", lorebook_name),
                "description": source.get("description", ""),
                "is_creation": False,
                "scan_depth": source.get("n_depth", 3),
                "token_budget": 512,
                "recursive_scanning": False,
                "extensions": {
                    "chub": {
                        "expressions": None,
                        "alt_expressions": None,
                        "id": None,
                        "full_path": f"lorebooks/{source.get('name', lorebook_name)}",
                        "related_lorebooks": [],
                        "background_image": "",
                        "preset": None,
                        "extensions": []
                    }
                },
                "entries": {}
            }

            entries = source.get("entries", [])
            for idx, entry in enumerate(entries, start=1):
                exported_data["entries"][str(idx)] = {
                    "uid": idx,
                    "key": entry.get("key", []),
                    "keysecondary": ["False"],
                    "comment": "",
                    "content": entry.get("content", ""),
                    "constant": False,
                    "selective": False,
                    "selectiveLogic": 0,
                    "order": 10,
                    "position": 1,
                    "disable": False,
                    "addMemo": True,
                    "excludeRecursion": True,
                    "probability": 100,
                    "displayIndex": 1,
                    "useProbability": True,
                    "secondary_keys": ["False"],
                    "keys": entry.get("key", []),
                    "id": idx,
                    "priority": 10,
                    "insertion_order": 10,
                    "enabled": True,
                    "name": f"Entry {idx}",
                    "extensions": {
                        "depth": 4,
                        "weight": 10,
                        "addMemo": True,
                        "probability": 100,
                        "displayIndex": 1,
                        "selectiveLogic": 0,
                        "useProbability": True,
                        "characterFilter": None,
                        "excludeRecursion": True
                    },
                    "case_sensitive": False,
                    "depth": 4,
                    "characterFilter": None
                }

            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(exported_data, f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                logger.error(f"Error when exporting a lorebook: {e}")
                return False

        def select_entry():
            selected = entry_list.currentRow()
            if selected >= 0:
                name = lorebook_combo.currentText()
                if name in lorebooks:
                    try:
                        entry = lorebooks[name]["entries"][selected]
                        key_input.setText(", ".join(entry.get("key", [])))
                        content_input.setPlainText(entry.get("content", ""))
                    except IndexError:
                        if lorebooks[name]["entries"]:
                            selected = 0
                            entry = lorebooks[name]["entries"][selected]
                            logger.info(f"The index is out of range. The first entry in '{name}' lorebook has been selected.")
                            key_input.setText(", ".join(entry.get("key", [])))
                            content_input.setPlainText(entry.get("content", ""))
                        else:
                            logger.info(f"Lorebook '{name}' it does not contain entries.")
                            key_input.clear()
                            content_input.clear()
                            entry_list.clearSelection()

        def add_entry():
            name = lorebook_combo.currentText()
            if name in lorebooks:
                key_text = key_input.text().strip()
                content_text = content_input.toPlainText().strip()
                if key_text:
                    keys = [k.strip() for k in key_text.split(",") if k.strip()]
                    lorebooks[name]["entries"].append({
                        "key": keys,
                        "content": content_text
                    })
                    entry_list.addItem(", ".join(keys))
                    key_input.clear()
                    content_input.clear()

        def save_entry():
            name = lorebook_combo.currentText()
            selected = entry_list.currentRow()
            if name in lorebooks and selected >= 0:
                key_text = key_input.text().strip()
                content_text = content_input.toPlainText().strip()

                if key_text:
                    keys = [k.strip() for k in key_text.split(",") if k.strip()]
                    lorebooks[name]["entries"][selected] = {
                        "key": keys,
                        "content": content_text
                    }
                    entry_list.item(selected).setText(", ".join(keys))
                    self.configuration_settings.update_lorebook(name, lorebooks[name])

        def delete_entry():
            lorebook_delete_entry = self.translations.get("lorebook_delete_entry", "Are you sure you want to delete this entry?")
            name = lorebook_combo.currentText()
            selected = entry_list.currentRow()
            if name in lorebooks and selected >= 0:
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                msg_box.setWindowTitle("Delete Entry")
                msg_box.setText(lorebook_delete_entry)
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.No)
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: rgb(27, 27, 27);
                        color: rgb(227, 227, 227);
                    }
                    QLabel {
                        color: rgb(227, 227, 227);
                    }
                """)
                reply = msg_box.exec()
                if reply == QMessageBox.StandardButton.Yes:
                    del lorebooks[name]["entries"][selected]
                    entry_list.takeItem(selected)
                    content_input.clear()
                    key_input.clear()

        entry_list.currentRowChanged.connect(select_entry)
        lorebook_combo.currentTextChanged.connect(apply_current_lorebook)
        create_button.clicked.connect(create_new_lorebook)
        edit_button.clicked.connect(edit_lorebook)
        delete_button.clicked.connect(delete_lorebook)
        import_button.clicked.connect(import_lorebook)
        export_button.clicked.connect(lambda: export_lorebook(lorebook_combo.currentText()))

        add_entry_btn.clicked.connect(add_entry)
        save_entry_btn.clicked.connect(save_entry)
        delete_entry_btn.clicked.connect(delete_entry)
        save_button.clicked.connect(lambda: self.configuration_settings.save_lorebooks(lorebooks))

        load_lorebooks()
        update_lorebook_combo()
        apply_current_lorebook()

        dialog.setLayout(layout)
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
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #2f2f2f, stop:1 #1e1e1e);
                color: rgb(227, 227, 227);
                border: 2px solid #3A3A3A;
                border-radius: 5px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #343434, stop:1 #222222);
                border: 2px solid #666666;
            }
            QPushButton:pressed {
                background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:0, y2:1, stop:0 #4a4a4a, stop:1 #3a3a3a);
                border: 2px solid #888888;
            }
        """)
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)

        def save_notes():
            new_notes = notes_edit.toPlainText().strip()
            self.configuration_settings.update_user_data("author_notes", new_notes)

            msg_box = QMessageBox()
            msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            msg_box.setWindowTitle(self.translations.get("author_notes_saved", "Saved"))
            msg_box.setText(self.translations.get("author_notes_saved_body", "The author's notes were saved successfully."))
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: rgb(27, 27, 27);
                    color: rgb(227, 227, 227);
                }
                QLabel {
                    color: rgb(227, 227, 227);
                }
            """)
            msg_box.exec()
            dialog.accept()

        save_button.clicked.connect(save_notes)

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
                if character_avatar_directory == "None":
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
            
            xttsv2_thread = XTTSv2(text=None, language=None, character_name=None, ui=self.ui)
            xttsv2_thread.stop_audio()

            kokoro_thread = KokoroTTS(text=None, character_name=None, ui=self.ui)
            kokoro_thread.stop_audio()

            self.center()

        if self._previous_index == 3 and index != 3:
            asyncio.create_task(self.close_character_building())

        if self._previous_index == 2 and index != 2:
            asyncio.create_task(self.close_character_building_cai())

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

        self.ui.character_description_chat.setText("")

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
    
    async def close_character_building_cai(self):
        self.ui.character_id_lineEdit.setText("")

    async def close_character_building(self):
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

            characters = character_data.get('character_list', {})
            for character_name, data in characters.items():
                conversation_method = data.get("conversation_method")
                match conversation_method:
                    case "Character AI":
                        conversation_method_image = "app/gui/icons/characterai.png"
                        character_avatar_url = data.get("character_avatar", None)
                        character_avatar = await self.character_ai_client.load_image(character_avatar_url)
                    case "Mistral AI":
                        conversation_method_image = "app/gui/icons/mistralai.png"
                        character_avatar_url = data.get("character_avatar", None)
                        character_avatar = character_avatar_url
                    case "Open AI":
                        conversation_method_image = "app/gui/icons/openai.png"
                        character_avatar_url = data.get("character_avatar", None)
                        character_avatar = character_avatar_url
                    case "OpenRouter":
                        conversation_method_image = "app/gui/icons/openrouter.png"
                        character_avatar_url = data.get("character_avatar", None)
                        character_avatar = character_avatar_url
                    case "Local LLM":
                        conversation_method_image = "app/gui/icons/local_llm.png"
                        character_avatar_url = data.get("character_avatar", None)
                        character_avatar = character_avatar_url

                card_widget = CharacterCardList(character_name, method=self.open_chat, parent=self.container)
                character_widget = self.create_character_card_widget(character_avatar, character_name, conversation_method_image, card_widget)
                character_widget.setVisible(True)
                self.cards.append(character_widget)
            QtCore.QTimer.singleShot(0, self.update_layout)

            self.ui.lineEdit_search_character_menu.textChanged.connect(self.filter_characters)

            self.ui.stackedWidget.setCurrentIndex(1)
        else:
            self.ui.stackedWidget.setCurrentIndex(0)

    def create_character_card_widget(self, character_image, character_name, communication_icon, card_widget):
        """
        Creates a character card widget with hover animations and a unified dark theme.
        """
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")

        self.ui.scrollArea_characters_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.scrollArea_characters_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.ui.scrollArea_characters_list.setViewportMargins(0, 0, 0, 0)
        self.ui.scrollArea_characters_list.verticalScrollBar().setStyleSheet("width: 0px;")
        self.ui.scrollArea_characters_list.horizontalScrollBar().setStyleSheet("height: 0px;")

        vertical_layout = QtWidgets.QVBoxLayout(card_widget)
        vertical_layout.setContentsMargins(0, 15, 0, 15)
        vertical_layout.setSpacing(0)

        frame_image = QtWidgets.QFrame()
        frame_image.setMinimumSize(QtCore.QSize(210, 0))
        frame_image.setMaximumSize(QtCore.QSize(210, 100))
        frame_image.setStyleSheet("background: transparent;")
        
        grid_layout = QtWidgets.QGridLayout(frame_image)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0)

        grid_layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum), 0, 0)

        avatar_label = QtWidgets.QLabel()
        avatar_label.setMinimumSize(QtCore.QSize(100, 100))
        avatar_label.setMaximumSize(QtCore.QSize(100, 100))
        avatar_label.setScaledContents(True)
        avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        pixmap = QPixmap(character_image)
        avatar_label.setPixmap(pixmap.scaled(
            100, 100,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
        mask = QPixmap(pixmap.size())
        mask.fill(Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()
        pixmap.setMask(mask.createMaskFromColor(Qt.GlobalColor.transparent))
        avatar_label.setPixmap(pixmap)
        grid_layout.addWidget(avatar_label, 0, 1)
        grid_layout.addItem(QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum), 0, 2)
        
        vertical_layout.addWidget(frame_image)

        name_label = QtWidgets.QLabel(character_name)
        name_label.setMinimumSize(QtCore.QSize(210, 0))
        name_label.setMaximumSize(QtCore.QSize(210, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("text-align: center; background: transparent; color: rgb(227, 227, 227);")
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        vertical_layout.addWidget(name_label)

        frame_comm = QtWidgets.QFrame()
        frame_comm.setMinimumSize(QtCore.QSize(210, 40))
        frame_comm.setMaximumSize(QtCore.QSize(210, 40))
        frame_comm.setStyleSheet("background: transparent;")
        
        grid_layout_comm = QtWidgets.QGridLayout(frame_comm)
        grid_layout_comm.setContentsMargins(0, 0, 0, 0)
        
        comm_icon_label = QtWidgets.QLabel()
        comm_icon_label.setMaximumSize(QtCore.QSize(30, 30))
        comm_icon_label.setStyleSheet("background: transparent; border-radius: 15px;")
        comm_pixmap = QPixmap(communication_icon).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        comm_icon_label.setPixmap(comm_pixmap)
        comm_icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        grid_layout_comm.addWidget(comm_icon_label, 0, 0)
        vertical_layout.addWidget(frame_comm)

        frame_buttons = QtWidgets.QFrame()
        frame_buttons.setStyleSheet("background: transparent;")
        buttons_layout = QtWidgets.QHBoxLayout(frame_buttons)
        buttons_layout.setContentsMargins(5, 0, 5, 0)

        call_button_text = self.translations.get("call_btn_text", "Open the Soul of Waifu System")
        voice_button_text = self.translations.get("voice_btn_text", "Open Text-To-Speech options")
        expressions_button_text = self.translations.get("expressions_btn_text", "Open expressions options")
        delete_button_text = self.translations.get("delete_btn_text", "Delete character")

        call_button = PushButton("#333333", "#444444", "menu_card", call_button_text)
        call_button.setObjectName("callButton")
        call_button.setCursor(Qt.CursorShape.PointingHandCursor)
        call_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        voice_button = PushButton("#333333", "#444444", "menu_card", voice_button_text)
        voice_button.setObjectName("voiceButton")
        voice_button.setCursor(Qt.CursorShape.PointingHandCursor)
        voice_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        expressions_button = PushButton("#333333", "#444444", "menu_card", expressions_button_text)
        expressions_button.setObjectName("expressionsButton")
        expressions_button.setCursor(Qt.CursorShape.PointingHandCursor)
        expressions_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        delete_button = PushButton("#333333", "#444444", "menu_card", delete_button_text)
        delete_button.setObjectName("deleteButton")
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        buttons = [call_button, voice_button, expressions_button, delete_button]
        for button in buttons:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    color: white;
                    border: 2px solid transparent;
                    border-radius: 17px;
                    width: 30px;
                    height: 30px;
                    font-size: 14px;
                    font-family: 'Inter Tight ExtraBold';
                    padding: 0;
                    margin: 5px;
                }
            """)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        icons = {
            call_button: "app/gui/icons/phone.png",
            voice_button: "app/gui/icons/voice.png",
            expressions_button: "app/gui/icons/expressions.png",
            delete_button: "app/gui/icons/bin.png"
        }
        for button, icon_path in icons.items():
            icon = QtGui.QIcon(icon_path)
            button.setIcon(icon)
            button.setIconSize(QtCore.QSize(20, 20))

        voice_button.clicked.connect(lambda: self.open_voice_menu(character_name))
        expressions_button.clicked.connect(lambda: self.open_expressions_menu(character_name))
        delete_button.clicked.connect(lambda: self.delete_character(self, character_name))

        if sow_system_status:
            buttons_layout.addWidget(call_button)
            call_button.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
        buttons_layout.addWidget(voice_button)
        if sow_system_status:
            buttons_layout.addWidget(expressions_button)
        buttons_layout.addWidget(delete_button)

        vertical_layout.addWidget(frame_buttons)

        more_btn_tooltip_text = self.translations.get("more_btn_tooltip", "Character Information")
        more_button = PushButton("#232323", "#444444", "menu_more_button", more_btn_tooltip_text)
        more_button.setObjectName("moreButton")
        more_button.setCursor(Qt.CursorShape.PointingHandCursor)
        more_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        more_button.setIcon(QtGui.QIcon("app/gui/icons/more.png"))
        more_button.setIconSize(QtCore.QSize(20, 20))
        more_button.setFixedSize(30, 30)
        more_button.clicked.connect(lambda: self.check_main_character_information(character_name))

        more_button.setStyleSheet("""
            QPushButton {
                background-color: #232323;
                border: none;
                border-radius: 15px;
                padding: 0;
                margin: 0;
            }
        """)

        more_button.setParent(card_widget)
        more_button.setGeometry(210 - 40, 10, 30, 30)
        more_button.raise_()
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
        Opens a dialog with additional settings for the character.
        """
        character_data = self.configuration_characters.load_configuration()
        character_list = character_data.get("character_list")
        character_information = character_list.get(character_name)

        conversation_method = character_information.get("conversation_method")
        character_avatar = character_information.get("character_avatar")
        if conversation_method == "Character AI":
            character_avatar = self.character_ai_client.get_from_cache(character_avatar)

        character_title = character_information.get("character_title")
        character_description = character_information.get("character_description")
        character_personality = character_information.get("character_personality")
        first_message = character_information.get("first_message")
        scenario = character_information.get("scenario")
        example_messages = character_information.get("example_messages")
        alternate_greetings = character_information.get("alternate_greetings")
        creator_notes = character_information.get("character_title")
        
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
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
            QLineEdit, QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
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
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        avatar_label = QLabel(dialog)
        pixmap = QPixmap(character_avatar)
        mask = QPixmap(pixmap.size())
        mask.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtCore.Qt.GlobalColor.black)
        painter.setPen(QtCore.Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()

        pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
        avatar_label.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        avatar_label.setFixedSize(100, 100)
        avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        avatar_label.setScaledContents(True)

        if conversation_method != "Character AI":
            name_edit = QLineEdit(character_name, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(15)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            name_edit.setFont(font)
            name_edit.setReadOnly(False)
            name_edit.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.3);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
            """)
            name_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            name_edit.setFixedHeight(45)
            name_edit.setCursorPosition(0)
            
            header_layout.addWidget(avatar_label)
            main_layout.addLayout(header_layout)
            main_layout.addWidget(name_edit)
        else:
            name_label = QLabel(character_name, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(16)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            name_label.setFont(font)
            name_label.setStyleSheet("text-align: center; background: transparent; color: rgb(227, 227, 227);")
            name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            header_layout.addWidget(avatar_label)
            main_layout.addLayout(header_layout)
            main_layout.addWidget(name_label)

        button_combo_container = QWidget()
        button_combo_layout = QHBoxLayout(button_combo_container)
        button_combo_layout.setContentsMargins(0, 0, 0, 0)
        button_combo_layout.setSpacing(10)

        creator_info_button = QPushButton(self.translations.get("creator_info_button", "Creator Notes"), dialog)
        creator_info_button.setStyleSheet("QPushButton {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #2f2f2f,\n"
                        "        stop: 1 #1e1e1e\n"
                        "    );\n"
                        "    color: rgb(227, 227, 227);\n"
                        "    border: 2px solid #3A3A3A;\n"
                        "    border-radius: 5px;\n"
                        "    padding: 2px;\n"
                        "}\n"
                        "\n"
                        "QPushButton:hover {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #343434,\n"
                        "        stop: 1 #222222\n"
                        "    );\n"
                        "    border: 2px solid #666666;\n"
                        "    border-top: 2px solid #777777;\n"
                        "    border-bottom: 2px solid #555555;\n"
                        "}\n"
                        "\n"
                        "QPushButton:pressed {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #4a4a4a,\n"
                        "        stop: 1 #3a3a3a\n"
                        "    );\n"
                        "    border: 2px solid #888888;\n"
                        "}")
        creator_info_button.setFixedHeight(35)
        creator_info_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        creator_info_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        creator_info_button.setFont(font)
        creator_info_button.clicked.connect(lambda: show_creator_info(character_title))
        main_layout.addWidget(creator_info_button)

        if conversation_method != "Character AI":
            export_button = QPushButton(self.translations.get("export_card_button", "Export character"), dialog)
            export_button.setStyleSheet("QPushButton {\n"
                            "    background-color: qlineargradient(\n"
                            "        spread: pad,\n"
                            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                            "        stop: 0 #2f2f2f,\n"
                            "        stop: 1 #1e1e1e\n"
                            "    );\n"
                            "    color: rgb(227, 227, 227);\n"
                            "    border: 2px solid #3A3A3A;\n"
                            "    border-radius: 5px;\n"
                            "    padding: 2px;\n"
                            "}\n"
                            "\n"
                            "QPushButton:hover {\n"
                            "    background-color: qlineargradient(\n"
                            "        spread: pad,\n"
                            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                            "        stop: 0 #343434,\n"
                            "        stop: 1 #222222\n"
                            "    );\n"
                            "    border: 2px solid #666666;\n"
                            "    border-top: 2px solid #777777;\n"
                            "    border-bottom: 2px solid #555555;\n"
                            "}\n"
                            "\n"
                            "QPushButton:pressed {\n"
                            "    background-color: qlineargradient(\n"
                            "        spread: pad,\n"
                            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                            "        stop: 0 #4a4a4a,\n"
                            "        stop: 1 #3a3a3a\n"
                            "    );\n"
                            "    border: 2px solid #888888;\n"
                            "}")
            export_button.setFixedHeight(35)
            export_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            export_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            export_button.setFont(font)
            export_button.clicked.connect(lambda: export_character_card_information(character_name))
            main_layout.addWidget(export_button)

        if conversation_method != "Character AI":
            conversation_method_layout = QVBoxLayout()
            conversation_method_label = QLabel("Conversation Method")
            conversation_method_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            conversation_method_layout.addWidget(conversation_method_label)
            conversation_method_combobox = QtWidgets.QComboBox(dialog)
            conversation_method_combobox.setFixedHeight(35)
            conversation_method_combobox.setStyleSheet("""
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
            conversation_method_combobox.setObjectName("conversation_method_combobox")
            conversation_method_combobox.addItems(["Mistral AI", "OpenRouter", "Open AI", "Local LLM"])
            conversation_method_combobox.setCurrentText(conversation_method)
            conversation_method_combobox.currentTextChanged.connect(
                lambda new_method: update_character_conversation_method(
                    character_name=character_name,
                    new_conversation_method=new_method
                )
            )
            conversation_method_layout.addWidget(conversation_method_combobox)
            button_combo_layout.addLayout(conversation_method_layout)

            config = self.configuration_settings.load_configuration()
            user_data = config.get("user_data", {})
            
            persona_layout = QVBoxLayout()
            persona_label = QLabel("Persona")
            persona_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            persona_layout.addWidget(persona_label)
            selected_persona = character_information.get("selected_persona", "None")
            persona_combobox = QtWidgets.QComboBox(dialog)
            persona_combobox.setFixedHeight(35)
            persona_combobox.setStyleSheet("""
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
            persona_combobox.setObjectName("persona_combobox")
            persona_combobox.addItem("None")
            personas = user_data.get("personas", {})
            for name in personas:
                persona_combobox.addItem(name)
            persona_combobox.setCurrentText(selected_persona)
            persona_combobox.currentTextChanged.connect(
                lambda new_persona: update_selected_persona(
                    character_name=character_name,
                    new_persona=new_persona
                )
            )
            persona_layout.addWidget(persona_combobox)
            button_combo_layout.addLayout(persona_layout)

            system_prompt_layout = QVBoxLayout()
            system_prompt_label = QLabel("System Prompt Preset")
            system_prompt_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            system_prompt_layout.addWidget(system_prompt_label)
            selected_system_prompt_preset = character_information.get("selected_system_prompt_preset", "By default")
            system_prompt_preset_combobox = QtWidgets.QComboBox(dialog)
            system_prompt_preset_combobox.setFixedHeight(35)
            system_prompt_preset_combobox.setStyleSheet("""
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
            system_prompt_preset_combobox.setObjectName("system_prompt_preset_combobox")
            system_prompt_preset_combobox.addItem("By default")
            presets = user_data.get("presets", {})
            for name in presets:
                system_prompt_preset_combobox.addItem(name)
            system_prompt_preset_combobox.setCurrentText(selected_system_prompt_preset)
            system_prompt_preset_combobox.currentTextChanged.connect(
                lambda new_preset: update_selected_system_prompt_preset(
                    character_name=character_name,
                    new_preset=new_preset
                )
            )
            system_prompt_layout.addWidget(system_prompt_preset_combobox)
            button_combo_layout.addLayout(system_prompt_layout)

            lorebook_layout = QVBoxLayout()
            lorebook_label = QLabel("Lorebook")
            lorebook_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
            lorebook_layout.addWidget(lorebook_label)
            selected_lorebook = character_information.get("selected_lorebook", "None")
            lorebook_combobox = QtWidgets.QComboBox(dialog)
            lorebook_combobox.setFixedHeight(35)
            lorebook_combobox.setStyleSheet("""
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
            lorebook_combobox.setObjectName("lorebook_combobox")
            lorebook_combobox.addItem("None")
            lorebooks = user_data.get("lorebooks", {})
            for name in lorebooks:
                lorebook_combobox.addItem(name)
            lorebook_combobox.setCurrentText(selected_lorebook)
            lorebook_combobox.currentTextChanged.connect(
                lambda new_lorebook: update_lorebook(
                    character_name=character_name,
                    new_lorebook=new_lorebook
                )
            )
            lorebook_layout.addWidget(lorebook_combobox)
            button_combo_layout.addLayout(lorebook_layout)
            
            def update_character_conversation_method(character_name, new_conversation_method):
                try:
                    character_data = self.configuration_characters.load_configuration()
                    character_list = character_data.get("character_list", {})

                    if character_name not in character_list:
                        logger.warning(f"Character '{character_name}' not found in configuration.")
                        return

                    character_information = character_list[character_name]
                    character_information["conversation_method"] = new_conversation_method

                    self.configuration_characters.save_configuration_edit(character_data)

                    asyncio.create_task(self.set_main_tab())
                except Exception as e:
                    logger.error(f"Failed to update conversation method for '{character_name}': {e}")
            
            def update_selected_persona(character_name, new_persona):
                try:
                    character_data = self.configuration_characters.load_configuration()
                    character_list = character_data.get("character_list", {})

                    if character_name not in character_list:
                        logger.warning(f"Character '{character_name}' not found in configuration.")
                        return

                    character_information = character_list[character_name]
                    character_information["selected_persona"] = new_persona
                    self.configuration_characters.save_configuration_edit(character_data)
                except Exception as e:
                    logger.error(f"Failed to update user persona for '{character_name}': {e}")
            
            def update_selected_system_prompt_preset(character_name, new_preset):
                try:
                    character_data = self.configuration_characters.load_configuration()
                    character_list = character_data.get("character_list", {})

                    if character_name not in character_list:
                        logger.warning(f"Character '{character_name}' not found in configuration.")
                        return

                    character_information = character_list[character_name]
                    character_information["selected_system_prompt_preset"] = new_preset

                    self.configuration_characters.save_configuration_edit(character_data)
                except Exception as e:
                    logger.error(f"Failed to update system prompt preset for '{character_name}': {e}")
            
            def update_lorebook(character_name, new_lorebook):
                try:
                    character_data = self.configuration_characters.load_configuration()
                    character_list = character_data.get("character_list", {})

                    if character_name not in character_list:
                        logger.warning(f"Character '{character_name}' not found in configuration.")
                        return

                    character_information = character_list[character_name]
                    character_information["selected_lorebook"] = new_lorebook

                    self.configuration_characters.save_configuration_edit(character_data)
                except Exception as e:
                    logger.error(f"Failed to update lorebook for '{character_name}': {e}")

        main_layout.addWidget(button_combo_container)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

        scroll_area = QtWidgets.QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        def show_creator_info(character_title):
            info_dialog = QDialog(dialog)
            info_dialog.setWindowTitle(self.translations.get("creator_info_window_title", "Creator Notes"))
            info_dialog.setMinimumSize(400, 300)
            info_dialog.setStyleSheet("""
                QDialog {
                    background-color: rgb(30, 30, 30);
                    border-radius: 10px;
                }
                QLabel {
                    color: rgb(200, 200, 200);
                }
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(60, 60, 60);
                    border-radius: 5px;
                    padding: 10px;
                    selection-color: rgb(255, 255, 255);
                    selection-background-color: rgb(39, 62, 135);
                }
                QPushButton {
                    background-color: rgb(60, 60, 60);
                    color: rgb(255, 255, 255);
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

            layout = QVBoxLayout(info_dialog)

            title_label = QLabel(self.translations.get("creator_info_title", "Title from Creator:"), info_dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_label.setFont(font)
            layout.addWidget(title_label)

            title_text_edit = QTextEdit(info_dialog)
            title_text_edit.setPlainText(character_title)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_text_edit.setFont(font)
            title_text_edit.setReadOnly(True)
            title_text_edit.setMinimumHeight(100)
            layout.addWidget(title_text_edit)

            close_button = QPushButton(self.translations.get("update_available_close", "Close"), info_dialog)
            close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            close_button.setFixedHeight(35)
            close_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            close_button.setFont(font)
            close_button.clicked.connect(info_dialog.close)
            layout.addWidget(close_button)

            info_dialog.exec()

        def create_editable_text_edit(label_text, content, placeholder="", is_read_only=False):
            label = QLabel(label_text, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            label.setFont(font)
            scroll_layout.addWidget(label)

            text_edit = QTextEdit(dialog)
            text_edit.setPlainText(content)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            text_edit.setFont(font)
            text_edit.setReadOnly(is_read_only)
            
            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(220, 220, 210, 1);
                    padding: 10px;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 15px 0px 15px 0px;
                    border-radius: 5px;
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

            if placeholder and conversation_method != "Character AI":
                text_edit.setPlaceholderText(placeholder)
            text_edit.setMinimumHeight(200)
            scroll_layout.addWidget(text_edit)

            edit_button = QPushButton(self.translations.get("chat_edit_message_2", "Edit"), dialog)
            edit_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            edit_button.setFixedHeight(35)
            edit_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            edit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            edit_button.setFont(font)
            edit_button.clicked.connect(lambda: open_edit_dialog(text_edit))
            scroll_layout.addWidget(edit_button)

            return text_edit

        def open_edit_dialog(text_edit):
            edit_dialog = QDialog(dialog)
            edit_dialog.setWindowTitle(self.translations.get("character_edit_edit_title", "Edit text"))
            edit_dialog.setMinimumSize(400, 300)

            layout = QVBoxLayout(edit_dialog)

            edit_text_edit = QTextEdit(edit_dialog)
            edit_text_edit.setPlainText(text_edit.toPlainText())
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(11)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            edit_text_edit.setFont(font)
            edit_text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(220, 220, 210, 1);
                    padding: 10px;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 15px 0px 15px 0px;
                    border-radius: 5px;
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
            layout.addWidget(edit_text_edit)

            button_layout = QHBoxLayout()
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"), edit_dialog)
            save_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            save_button.setFixedHeight(35)
            save_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cancel_button = QPushButton(self.translations.get("character_edit_cancel", "Cancel"), edit_dialog)
            cancel_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            cancel_button.setFixedHeight(35)
            cancel_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            save_button.setFont(font)
            cancel_button.setFont(font)

            save_button.clicked.connect(lambda: save_edit_changes(edit_text_edit, text_edit))
            cancel_button.clicked.connect(edit_dialog.close)

            button_layout.addWidget(save_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            edit_dialog.exec()

        def save_edit_changes(edit_text_edit, original_text_edit):
            new_text = edit_text_edit.toPlainText()
            original_text_edit.setPlainText(new_text)

        if conversation_method == "Character AI":
            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(6)
            form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignVCenter)
            form_layout.setHorizontalSpacing(10)

            title_edit = QLineEdit(character_title, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_edit.setFont(font)
            title_edit.setReadOnly(True)
            title_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            title_edit.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); color: rgba(220, 220, 210, 1);")
            title_edit.setMaximumHeight(50)

            form_layout.addRow(title_edit)

            group_box = QtWidgets.QGroupBox()
            group_box.setLayout(form_layout)
            group_box.setStyleSheet("QGroupBox { border: none; padding: 0px; margin-top: 5px; }")

            scroll_layout.addWidget(group_box)
        else:
            description_edit = create_editable_text_edit(
                self.translations.get("character_edit_description", "Character Description:"),
                character_description,
                placeholder=self.translations.get("character_edit_description_placeholder_1", "Enter the character's description"),
                is_read_only=False
            )

            personality_edit = create_editable_text_edit(
                self.translations.get("character_edit_personality", "Character Personality:"),
                character_personality,
                placeholder=self.translations.get("character_edit_personality_placeholder", "Enter the character's personality traits"),
                is_read_only=False
            )

            scenario_edit = create_editable_text_edit(
                self.translations.get("scenario", "Scenario:"),
                scenario,
                placeholder=self.translations.get("placeholder_scenario", "Conversation scenario:"),
                is_read_only=False
            )

            first_message_edit = create_editable_text_edit(
                self.translations.get("character_edit_first_message", "Character First Message:"),
                first_message,
                placeholder=self.translations.get("character_edit_first_message_placeholder", "Enter the character's first message"),
                is_read_only=False
            )

            example_messages_edit = create_editable_text_edit(
                self.translations.get("example_messages_title", "Example Messages:"),
                example_messages,
                placeholder=self.translations.get("placeholder_example_messages", "Describes how the character speaks. Before each example, you must insert the <START> macro"),
                is_read_only=False
            )

            alternate_greetings_edit = create_editable_text_edit(
                self.translations.get("alternate_greetings_label", "Alternate Greetings:"),
                "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings or "",
                placeholder=self.translations.get("placeholder_alternate_greetings", "You can include as many alternative greetings as you like. Before each alternate greeting, you must insert the <GREETING> macro"),
                is_read_only=False
            )

            creator_notes_edit = create_editable_text_edit(
                self.translations.get("creator_notes_label", "Creator Notes:"),
                creator_notes,
                placeholder=self.translations.get("placeholder_creator_notes", "Any additional notes about the character card"),
                is_read_only=False
            )

        scroll_area.setWidget(scroll_content)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_button = QPushButton("OK", dialog)
        ok_button.setFixedHeight(35)
        ok_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        ok_button.setFont(font)
        try:
            ok_button.clicked.disconnect()
        except TypeError:
            pass
        ok_button.clicked.connect(dialog.close)
        button_layout.addWidget(ok_button)

        def export_character_card_information(character_name):
            try:
                if not character_name:
                    QMessageBox.warning(None, "Error", "Not enough information about the character")
                    return

                current_image_path = character_avatar

                if current_image_path and os.path.exists(current_image_path):
                    image = Image.open(current_image_path).convert("RGBA")
                else:
                    default_image_path = "app/gui/icons/export_card.png"
                    image = Image.open(default_image_path).convert("RGBA")

                personas_data = self.configuration_settings.get_user_data("personas")
                current_persona = self.configuration_settings.get_user_data("default_persona")
                if current_persona == "None" or current_persona is None:
                    user_name = "User"
                else:
                    try:
                        user_name = personas_data[current_persona].get("user_name", "User")
                    except Exception as e:
                        user_name = "User"

                char_data = {
                    "spec": "chara_card_v2",
                    "spec_version": "2.0",
                    "data": {
                        'name': name_edit.text(),
                        'description': description_edit.toPlainText(),
                        'personality': personality_edit.toPlainText(),
                        'first_mes': first_message_edit.toPlainText(),
                        'scenario': scenario_edit.toPlainText(),
                        'mes_example': example_messages_edit.toPlainText(),
                        'creator_notes': creator_notes_edit.toPlainText(),
                        'character_version': "1.0.0",
                        'creator': user_name,
                        'tags': ["sow", "custom"],
                        'extensions': {},
                    }
                }

                raw_greetings = alternate_greetings_edit.toPlainText().strip()
                greetings_list = self.parse_alternate_greetings(raw_greetings)
                char_data["data"]["alternate_greetings"] = greetings_list

                if not char_data["data"]["character_version"]:
                    char_data["data"]["character_version"] = "1.0.0"

                char_data["data"]["system_prompt"] = ""
                char_data["data"]["post_history_instructions"] = ""

                json_str = json.dumps(char_data, ensure_ascii=False, indent=2)
                json_bytes = json_str.encode('utf-8')
                b64_data = base64.b64encode(json_bytes).decode('utf-8')

                png_info = PngImagePlugin.PngInfo()
                png_info.add_text("chara", b64_data.encode('utf-8'))

                file_path, _ = QFileDialog.getSaveFileName(
                    None,
                    "Export Character Card",
                    "",
                    "PNG Images (*.png)"
                )
                if file_path:
                    image.save(file_path, format="PNG", pnginfo=png_info)

            except Exception as e:
                logger.error(f"Error exporting character card: {e}")
                QMessageBox.critical(None, "Error", f"Couldn't export character card:\n{str(e)}")

        if conversation_method != "Character AI":
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"), dialog)
            save_button.setFixedHeight(35)
            save_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            save_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            save_button.setFont(font)
            try:
                save_button.clicked.disconnect()
            except TypeError:
                pass
            save_button.clicked.connect(lambda: self.save_changes_main_menu(conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit))
            button_layout.addWidget(save_button)

            chats = character_information["chats"]
            if conversation_method != "Character AI":
                chat_selector_widget = QWidget()
                chat_selector_layout = QHBoxLayout(chat_selector_widget)
                chat_combobox = QtWidgets.QComboBox(dialog)
                chat_combobox.setFixedHeight(33)
                chat_combobox.setStyleSheet("""
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
                chat_combobox.setObjectName("chat_combobox")

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

                rename_button = QPushButton(self.translations.get("rename_chat_button", "Rename chat"))
                delete_button = QPushButton(self.translations.get("delete_chat_button", "Delete chat"))
                export_button = QPushButton(self.translations.get("export_chat_button", "Export chat"))
                import_button = QPushButton(self.translations.get("import_chat_button", "Import chat"))

                font = QtGui.QFont()
                font.setFamily("Inter Tight SemiBold")
                font.setPointSize(8)
                font.setBold(False)
                font.setWeight(50)
                font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

                buttons = [rename_button, delete_button, export_button, import_button]
                for button in buttons:
                    button.setFixedHeight(33)
                    button.setFont(font)
                    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                    button.setStyleSheet("QPushButton {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #2f2f2f,\n"
                        "        stop: 1 #1e1e1e\n"
                        "    );\n"
                        "    color: rgb(227, 227, 227);\n"
                        "    border: 2px solid #3A3A3A;\n"
                        "    border-radius: 5px;\n"
                        "    padding: 2px;\n"
                        "}\n"
                        "\n"
                        "QPushButton:hover {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #343434,\n"
                        "        stop: 1 #222222\n"
                        "    );\n"
                        "    border: 2px solid #666666;\n"
                        "    border-top: 2px solid #777777;\n"
                        "    border-bottom: 2px solid #555555;\n"
                        "}\n"
                        "\n"
                        "QPushButton:pressed {\n"
                        "    background-color: qlineargradient(\n"
                        "        spread: pad,\n"
                        "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
                        "        stop: 0 #4a4a4a,\n"
                        "        stop: 1 #3a3a3a\n"
                        "    );\n"
                        "    border: 2px solid #888888;\n"
                        "}")
                
                icon_delete = QtGui.QIcon()
                icon_delete.addPixmap(QtGui.QPixmap("app/gui/icons/bin.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
                icon_import = QtGui.QIcon()
                icon_import.addPixmap(QtGui.QPixmap("app/gui/icons/import.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
                icon_export = QtGui.QIcon()
                icon_export.addPixmap(QtGui.QPixmap("app/gui/icons/export.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)

                rename_button.setFont(font)
                delete_button.setFont(font)
                import_button.setFont(font)
                export_button.setFont(font)
                
                rename_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                delete_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                delete_button.setIcon(icon_delete)
                import_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                import_button.setIcon(icon_import)
                export_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                export_button.setIcon(icon_export)

                def on_chat_selected(index):
                    character_data = self.configuration_characters.load_configuration()
                    character_list = character_data.get("character_list")
                    character_information = character_list.get(character_name)
                    chats = character_information.get("chats", {})

                    selected_chat_name = chat_combobox.currentText()

                    chat_id_to_set = None
                    for chat_id, chat_info in chats.items():
                        if chat_info.get("name") == selected_chat_name:
                            chat_id_to_set = chat_id
                            break

                    set_current_chat(character_name, chat_id_to_set)

                    chat_combobox.setItemText(index, selected_chat_name)

                def set_current_chat(character_name, chat_id):
                    config = self.configuration_characters.load_configuration()
                    char_data = config["character_list"].get(character_name)
                    if not char_data:
                        return

                    char_data["current_chat"] = chat_id
                    config["character_list"][character_name] = char_data

                    self.configuration_characters.save_configuration_edit(config)

                def export_chat():
                    """
                    Exports the currently selected chat of a character to a .sowchat file.
                    """
                    configuration_data = self.configuration_characters.load_configuration()
                    character_list = configuration_data.get("character_list", {})
                    
                    if character_name not in character_list:
                        logger.error(f"Character '{character_name}' not found.")
                        return False

                    char_data = character_list[character_name]
                    chats = char_data.get("chats", {})

                    index = chat_combobox.currentIndex()
                    if index < 0:
                        logger.warning("No chat selected for export.")
                        return False

                    selected_chat_name = chat_combobox.currentText()

                    selected_chat_id = None
                    for chat_id, chat_info in chats.items():
                        if chat_info.get("name") == selected_chat_name:
                            selected_chat_id = chat_id
                            break

                    if selected_chat_id not in chats:
                        logger.warning(f"Selected chat ID '{selected_chat_id}' not found in character's chats.")
                        return False

                    selected_chat_data = chats[selected_chat_id]

                    export_data = {
                        "exported_from": character_name,
                        "exported_at": datetime.datetime.now().isoformat(),
                        "chat_id": selected_chat_id,
                        "chat": selected_chat_data
                    }

                    default_file_name = f"{character_name}_{selected_chat_data['name']}.sowchat"
                    file_path, _ = QFileDialog.getSaveFileName(
                        None,
                        "Save chat",
                        default_file_name,
                        "Chat Files (*.sowchat)"
                    )

                    if not file_path:
                        return False

                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(export_data, f, indent=4, ensure_ascii=False)
                        return True
                    except Exception as e:
                        logger.error(f"Error exporting chat: {e}")
                        return False

                def import_chat():
                    """
                    Imports a chat from a .sowchat file into the current character.
                    Allows the user to either replace the current chat or create a new one.
                    """
                    file_path, _ = QFileDialog.getOpenFileName(
                        None,
                        "Import Chat",
                        "",
                        "Chat Files (*.sowchat)"
                    )

                    if not file_path:
                        return False

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            import_data = json.load(f)

                        exported_from = import_data.get("exported_from")
                        exported_at = import_data.get("exported_at")
                        chat_id = import_data.get("chat_id")
                        imported_chat = import_data.get("chat", {})

                        if not all([exported_from, exported_at, chat_id, imported_chat]):
                            logger.error("Invalid .sowchat file format.")
                            QMessageBox.critical(None, "Error", self.translations.get("invalid_sowchat_file", "This file is not a valid .sowchat file."))
                            return False

                        configuration_data = self.configuration_characters.load_configuration()
                        character_list = configuration_data.get("character_list", {})
                        
                        if character_name != exported_from:
                            msg = self.translations.get(
                                "import_chat_mismatch",
                                "This chat was created for '{exported_from}', but you're trying to import it into '{character_name}'. Would you like to proceed anyway?"
                            ).format(exported_from=exported_from, character_name=character_name)
                            reply = QMessageBox.question(
                                None,
                                self.translations.get("import_chat_mismatch_title", "Character Mismatch"),
                                msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                            )
                            if reply == QMessageBox.StandardButton.No:
                                return False

                        char_data = character_list.get(character_name)
                        if not char_data:
                            logger.error(f"Character '{character_name}' not found in config.")
                            return False

                        if "chats" not in char_data:
                            char_data["chats"] = {}

                        existing_chats = char_data["chats"]

                        if chat_id in existing_chats:
                            msg = (
                                self.translations.get("import_chat_conflict", "A chat with ID '{chat_id}' already exists. Would you like to overwrite it or add this as a new chat?").format(chat_id=chat_id)
                            )
                            reply = QMessageBox.question(
                                None,
                                self.translations.get("import_chat_conflict_title", "Conflict Detected"),
                                msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.No
                            )

                            if reply == QMessageBox.StandardButton.Yes:
                                existing_chats[chat_id] = imported_chat
                            else:
                                new_chat_id = str(uuid.uuid4())
                                imported_chat["name"] += " (Imported)"
                                existing_chats[new_chat_id] = imported_chat
                        else:
                            existing_chats[chat_id] = imported_chat

                        char_data["chats"] = existing_chats
                        character_list[character_name] = char_data
                        configuration_data["character_list"] = character_list
                        self.configuration_characters.save_configuration_edit(configuration_data)

                        chat_combobox.clear()

                        chats = char_data.get("chats", {})
                        current_chat_id = char_data.get("current_chat")

                        for chat_id_iter, chat_info in chats.items():
                            chat_name = chat_info.get("name", f"Chat {chat_id_iter[:6]}")
                            chat_combobox.addItem(chat_name, userData=chat_id_iter)

                        if current_chat_id and current_chat_id in chats:
                            for index in range(chat_combobox.count()):
                                if chat_combobox.itemData(index) == current_chat_id:
                                    chat_combobox.setCurrentIndex(index)
                                    break

                        return True

                    except Exception as e:
                        logger.error(f"Error importing chat: {e}")
                        traceback.print_exc()
                        QMessageBox.critical(None, "Import Error", f"Failed to import chat:\n{str(e)}")
                        return False
                
                def rename_chat():
                    index = chat_combobox.currentIndex()
                    if index < 0:
                        return
                    
                    old_name = chat_combobox.currentText()
                    found_chat_id = None

                    for chat_id, chat_info in chats.items():
                        if chat_info.get("name") == old_name:
                            found_chat_id = chat_id
                            break
                    
                    new_name, ok = QInputDialog.getText(
                        dialog,
                        "Rename Chat",
                        "Enter new chat name:",
                        text=old_name
                    )

                    if not ok or not new_name.strip():
                        return
                    
                    config = self.configuration_characters.load_configuration()
                    char_data = config["character_list"][character_name]
                    chat_data = char_data["chats"][found_chat_id]
                    chat_data["name"] = new_name
                    char_data["chats"][chat_id] = chat_data
                    config["character_list"][character_name] = char_data
                    
                    self.configuration_characters.save_configuration_edit(config)

                    chat_combobox.setItemText(index, new_name)
                
                def delete_chat():
                    index = chat_combobox.currentIndex()
                    if index < 0:
                        return

                    selected_chat_name = chat_combobox.currentText()
                    chat_id_to_delete = None
                    for chat_id, chat_info in chats.items():
                        if chat_info.get("name") == selected_chat_name:
                            chat_id_to_delete = chat_id
                            break
                    
                    msg_box = QMessageBox()
                    msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    msg_box.setWindowTitle(self.translations.get("delete_chat", "Delete chat"))
                    msg_box.setStyleSheet("""
                        QMessageBox {
                            background-color: rgb(27, 27, 27);
                            color: rgb(227, 227, 227);
                        }
                        QLabel {
                            color: rgb(227, 227, 227);
                            font-family: "Segoe UI", Arial, sans-serif;
                            font-size: 14px;
                        }
                    """)

                    msg_box.setText(self.translations.get("delete_chat", "Are you sure you want to delete this chat?"))
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    
                    reply = msg_box.exec()

                    if reply != QMessageBox.StandardButton.Yes:
                        return

                    try:
                        config = self.configuration_characters.load_configuration()
                        char_data = config["character_list"][character_name]
                        del char_data["chats"][chat_id_to_delete]
                    except KeyError as e:
                        return

                    if char_data["current_chat"] == chat_id_to_delete:
                        remaining_chats = list(char_data["chats"].keys())
                        if remaining_chats:
                            char_data["current_chat"] = remaining_chats[0]
                        else:
                            try:
                                self.configuration_characters.create_new_chat(
                                    character_name, conversation_method, name_edit, 
                                    description_edit, personality_edit, scenario_edit, 
                                    first_message_edit, example_messages_edit, 
                                    alternate_greetings_edit, creator_notes_edit
                                )
                            except TypeError as e:
                                return

                    config["character_list"][character_name] = char_data
                    self.configuration_characters.save_configuration_edit(config)

                    chat_combobox.removeItem(index)
                    if chat_combobox.count() == 0:
                        chat_selector_widget.setVisible(False)

                try:
                    rename_button.clicked.disconnect()
                    delete_button.clicked.disconnect()
                    export_button.clicked.disconnect()
                    import_button.clicked.disconnect()
                except TypeError:
                    pass

                export_button.clicked.connect(export_chat)
                import_button.clicked.connect(import_chat)      
                rename_button.clicked.connect(rename_chat)
                if len(chats) > 1:
                    delete_button.clicked.connect(delete_chat)
                chat_combobox.currentIndexChanged.connect(on_chat_selected)

                chat_selector_layout.addWidget(chat_combobox)
                chat_selector_layout.addWidget(rename_button)
                if len(chats) > 1:
                    chat_selector_layout.addWidget(delete_button)
                chat_selector_layout.addWidget(import_button)
                chat_selector_layout.addWidget(export_button)

                main_layout.addWidget(chat_selector_widget)

        new_dialog_button = QPushButton(self.translations.get("character_edit_start_new_dialogue", "Start new dialogue"), dialog)
        new_dialog_button.setFixedHeight(35)
        new_dialog_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        new_dialog_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        new_dialog_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        new_dialog_button.setFont(font)
        try:
            new_dialog_button.clicked.disconnect()
        except TypeError:
            pass
        new_dialog_button.clicked.connect(
            lambda: asyncio.create_task(
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
            )
        )
        button_layout.addWidget(new_dialog_button)

        main_layout.addWidget(scroll_area)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

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

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("character_edit_saved", "Saved"))
            message_box_information.setText(self.translations.get("character_edit_saved_2", "The changes were saved successfully!"))
            message_box_information.exec()
        else:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("character_edit_saved_error", "Saving Error"))
            message_box_information.setText(self.translations.get("character_edit_saved_error_2", "Character was not found in the configuration."))
            message_box_information.exec()
        
        asyncio.create_task(self.set_main_tab())
        
    async def start_new_dialog_main(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        reply = QMessageBox.question(
            dialog, 
            self.translations.get("character_edit_start_new_dialogue", "Start new dialogue"), 
            self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue?"), 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
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

        message_box_information = QMessageBox()
        message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        message_box_information.setWindowTitle("New Chat")
        message_box_information.setText(self.translations.get("character_edit_start_new_dialogue_success", "A new chat has been successfully started!"))
        message_box_information.exec()
        
        dialog.close()
        asyncio.create_task(self.set_main_tab())
        self.main_window.updateGeometry()
        QtCore.QTimer.singleShot(0, self.update_layout)

    def set_conversation_method_dialog(self):
        """
        Loads the dialog window for selecting the conversation method.
        """
        dialog = QtWidgets.QDialog()
        dialog.setStyleSheet(self.get_add_character_dialog_stylesheet())
        dialog.setWindowTitle(self.translations.get("create_character_title", "Character Creation Selector"))

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        dialog.setWindowIcon(icon)

        dialog.setFixedSize(QtCore.QSize(400, 350))

        btn_char_ai = QPushButton(self.translations.get("radio_character_ai", " Character AI"))
        icon_cai = QtGui.QIcon()
        icon_cai.addPixmap(QtGui.QPixmap("app/gui/icons/characterai.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn_char_ai.setIcon(icon_cai)

        btn_mistral_ai = QPushButton(self.translations.get("radio_mistral_ai", " Mistral AI"))
        icon_mistral_ai = QtGui.QIcon()
        icon_mistral_ai.addPixmap(QtGui.QPixmap("app/gui/icons/mistralai.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn_mistral_ai.setIcon(icon_mistral_ai)

        btn_open_ai = QPushButton(self.translations.get("radio_open_ai", " Open AI or Custom"))
        icon_open_ai = QtGui.QIcon()
        icon_open_ai.addPixmap(QtGui.QPixmap("app/gui/icons/openai.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn_open_ai.setIcon(icon_open_ai)

        btn_openrouter = QPushButton(self.translations.get("radio_openrouter", " OpenRouter"))
        icon_openrouter = QtGui.QIcon()
        icon_openrouter.addPixmap(QtGui.QPixmap("app/gui/icons/openrouter.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn_openrouter.setIcon(icon_openrouter)

        btn_local_llm = QPushButton(self.translations.get("radio_local_llm", " Local LLM"))
        icon_local_llm = QtGui.QIcon()
        icon_local_llm.addPixmap(QtGui.QPixmap("app/gui/icons/local_llm.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        btn_local_llm.setIcon(icon_local_llm)

        self.buttons = [btn_char_ai, btn_mistral_ai, btn_open_ai, btn_openrouter, btn_local_llm]
        
        for btn in self.buttons:
            btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setCheckable(True)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(12)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            btn.setFont(font)
            btn.clicked.connect(lambda checked, b=btn: self.on_button_clicked(b, dialog))

        btn_char_ai.setChecked(True)
        btn_char_ai.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel(self.translations.get("create_character_title_2", "Choose Character Creation Method"))
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: rgb(200, 200, 200);
        """)
        layout.addWidget(title_label)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)

        for btn in self.buttons:
            btn.setStyleSheet("QPushButton {\n"
            "    background-color: qlineargradient(\n"
            "        spread: pad,\n"
            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
            "        stop: 0 #2f2f2f,\n"
            "        stop: 1 #1e1e1e\n"
            "    );\n"
            "    color: rgb(227, 227, 227);\n"
            "    border: 2px solid #3A3A3A;\n"
            "    border-radius: 5px;\n"
            "    padding: 2px;\n"
            "}\n"
            "\n"
            "QPushButton:hover {\n"
            "    background-color: qlineargradient(\n"
            "        spread: pad,\n"
            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
            "        stop: 0 #343434,\n"
            "        stop: 1 #222222\n"
            "    );\n"
            "    border: 2px solid #666666;\n"
            "    border-top: 2px solid #777777;\n"
            "    border-bottom: 2px solid #555555;\n"
            "}\n"
            "\n"
            "QPushButton:pressed {\n"
            "    background-color: qlineargradient(\n"
            "        spread: pad,\n"
            "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
            "        stop: 0 #4a4a4a,\n"
            "        stop: 1 #3a3a3a\n"
            "    );\n"
            "    border: 2px solid #888888;\n"
            "}")
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        dialog.btn_char_ai = btn_char_ai
        dialog.btn_mistral_ai = btn_mistral_ai
        dialog.btn_open_ai = btn_open_ai
        dialog.btn_openrouter = btn_openrouter
        dialog.btn_local_llm = btn_local_llm

        dialog.exec()

    def on_button_clicked(self, clicked_button, dialog):
        for btn in self.buttons:
            btn.setChecked(btn == clicked_button)

        selection_map = {
            dialog.btn_char_ai: "Character AI",
            dialog.btn_mistral_ai: "Mistral AI",
            dialog.btn_open_ai: "Open AI",
            dialog.btn_openrouter: "OpenRouter",
            dialog.btn_local_llm: "Local LLM"
        }

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
        
        selection = selection_map.get(clicked_button)
        if selection:
            match selection:
                case "Character AI":
                    self.ui.stackedWidget.setCurrentIndex(2)
                    self.configuration_settings.update_main_setting("conversation_method", "Character AI")
                case "Mistral AI":
                    self.ui.stackedWidget.setCurrentIndex(3)
                    self.configuration_settings.update_main_setting("conversation_method", "Mistral AI")
                case "Open AI":
                    self.ui.stackedWidget.setCurrentIndex(3)
                    self.configuration_settings.update_main_setting("conversation_method", "Open AI")
                case "OpenRouter":
                    self.ui.stackedWidget.setCurrentIndex(3)
                    self.configuration_settings.update_main_setting("conversation_method", "OpenRouter")
                case "Local LLM":
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

    def on_comboBox_speech_to_text_method_changed(self, index):
        self.configuration_settings.update_main_setting("stt_method", index)

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
            self.ui.choose_model_bg_color.show()
            self.ui.comboBox_model_bg_color.show()
            self.ui.choose_model_bg_image.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.pushButton_reload_bg_image.hide()
        elif index == 1:
            self.ui.choose_model_bg_color.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.choose_model_bg_image.show()
            self.ui.comboBox_model_bg_image.show()
            self.ui.pushButton_reload_bg_image.show()

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
            self.ui.choose_live2d_mode_label.show()
            self.ui.comboBox_live2d_mode.show()
            self.ui.choose_model_fps.show()
            self.ui.comboBox_model_fps.show()
            self.ui.choose_model_background.show()
            self.ui.comboBox_model_background.show()
            self.ui.checkBox_enable_ambient.show()
            if ambient_enabled == True:
                self.ui.comboBox_ambient_mode.show()
                self.ui.pushButton_reload_ambient.show()
            else:
                self.ui.comboBox_ambient_mode.hide()
                self.ui.pushButton_reload_ambient.hide()
            if model_background_type == 0:
                self.ui.choose_model_bg_color.show()
                self.ui.comboBox_model_bg_color.show()
                self.ui.choose_model_bg_image.hide()
                self.ui.comboBox_model_bg_image.hide()
                self.ui.pushButton_reload_bg_image.hide()
            elif model_background_type == 1:
                self.ui.choose_model_bg_color.hide()
                self.ui.comboBox_model_bg_color.hide()
                self.ui.choose_model_bg_image.show()
                self.ui.comboBox_model_bg_image.show()
                self.ui.pushButton_reload_bg_image.show()
            
            self.ui.separator_options.setGeometry(QtCore.QRect(10, 290, 1060, 2))
            self.ui.sow_system_modules_title_label.setGeometry(QtCore.QRect(10, 310, 171, 31))
            self.ui.speech_to_text_method_label.setGeometry(QtCore.QRect(20, 360, 151, 16))
            self.ui.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(20, 380, 181, 31))
            self.ui.checkBox_enable_memory.setGeometry(QtCore.QRect(20, 440, 221, 22))
        else:
            self.configuration_settings.update_main_setting("sow_system_status", False)
            self.ui.choose_live2d_mode_label.hide()
            self.ui.comboBox_live2d_mode.hide()
            self.ui.choose_model_fps.hide()
            self.ui.comboBox_model_fps.hide()
            self.ui.choose_model_background.hide()
            self.ui.comboBox_model_background.hide()
            self.ui.choose_model_bg_color.hide()
            self.ui.choose_model_bg_image.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.pushButton_reload_bg_image.hide()
            self.ui.checkBox_enable_ambient.hide()
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()

            self.ui.separator_options.setGeometry(QtCore.QRect(10, 100, 1060, 2))
            self.ui.sow_system_modules_title_label.setGeometry(QtCore.QRect(10, 120, 171, 31))
            self.ui.speech_to_text_method_label.setGeometry(QtCore.QRect(20, 170, 151, 16))
            self.ui.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(20, 190, 181, 31))
            self.ui.checkBox_enable_memory.setGeometry(QtCore.QRect(20, 250, 221, 22))

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

    def load_combobox(self):
        """
        Loads the settings to the Combobox's and Checkbox's of the interface from the configuration.
        """
        self.ui.comboBox_conversation_method.setCurrentText(self.configuration_settings.get_main_setting("conversation_method"))
        self.ui.comboBox_speech_to_text_method.setCurrentIndex(self.configuration_settings.get_main_setting("stt_method"))
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
            self.ui.choose_model_bg_color.show()
            self.ui.comboBox_model_bg_color.show()
            self.ui.choose_model_bg_image.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.pushButton_reload_bg_image.hide()
        elif model_background_type == 1:
            self.ui.choose_model_bg_color.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.choose_model_bg_image.show()
            self.ui.comboBox_model_bg_image.show()
            self.ui.pushButton_reload_bg_image.show()

        sow_state = self.configuration_settings.get_main_setting("sow_system_status")
        if sow_state == False:
            self.ui.checkBox_enable_sow_system.setChecked(False)
            self.ui.choose_live2d_mode_label.hide()
            self.ui.comboBox_live2d_mode.hide()
            self.ui.choose_model_fps.hide()
            self.ui.comboBox_model_fps.hide()
            self.ui.choose_model_background.hide()
            self.ui.comboBox_model_background.hide()
            self.ui.choose_model_bg_color.hide()
            self.ui.choose_model_bg_image.hide()
            self.ui.comboBox_model_bg_color.hide()
            self.ui.comboBox_model_bg_image.hide()
            self.ui.pushButton_reload_bg_image.hide()
            self.ui.checkBox_enable_ambient.hide()
            self.ui.comboBox_ambient_mode.hide()
            self.ui.pushButton_reload_ambient.hide()

            self.ui.separator_options.setGeometry(QtCore.QRect(10, 100, 1060, 2))
            self.ui.sow_system_modules_title_label.setGeometry(QtCore.QRect(10, 120, 171, 31))
            self.ui.speech_to_text_method_label.setGeometry(QtCore.QRect(20, 170, 151, 16))
            self.ui.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(20, 190, 181, 31))
            self.ui.checkBox_enable_memory.setGeometry(QtCore.QRect(20, 250, 221, 22))
        else:
            self.ui.checkBox_enable_sow_system.setChecked(True)
            self.ui.choose_live2d_mode_label.show()
            self.ui.comboBox_live2d_mode.show()
            self.ui.choose_model_fps.show()
            self.ui.comboBox_model_fps.show()
            self.ui.choose_model_background.show()
            self.ui.comboBox_model_background.show()
            self.ui.checkBox_enable_ambient.show()
            self.ui.comboBox_ambient_mode.show()
            self.ui.pushButton_reload_ambient.show()
            if model_background_type == 0:
                self.ui.choose_model_bg_color.show()
                self.ui.comboBox_model_bg_color.show()
                self.ui.choose_model_bg_image.hide()
                self.ui.comboBox_model_bg_image.hide()
                self.ui.pushButton_reload_bg_image.hide()
            elif model_background_type == 1:
                self.ui.choose_model_bg_color.hide()
                self.ui.comboBox_model_bg_color.hide()
                self.ui.choose_model_bg_image.show()
                self.ui.comboBox_model_bg_image.show()
                self.ui.pushButton_reload_bg_image.show()
            
            self.ui.separator_options.setGeometry(QtCore.QRect(10, 290, 1060, 2))
            self.ui.sow_system_modules_title_label.setGeometry(QtCore.QRect(10, 310, 171, 31))
            self.ui.speech_to_text_method_label.setGeometry(QtCore.QRect(20, 360, 151, 16))
            self.ui.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(20, 380, 181, 31))
            self.ui.checkBox_enable_memory.setGeometry(QtCore.QRect(20, 440, 221, 22))
        
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
            self.ui.lineEdit_mistral_model.show()
            self.ui.lineEdit_base_url_options.hide()
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
            self.ui.lineEdit_mistral_model.hide()
            self.ui.lineEdit_base_url_options.show()
            self.ui.openrouter_models_options_label.hide()
            self.ui.lineEdit_search_openrouter_models.hide()
            self.ui.comboBox_openrouter_models.hide()
            api_token = self.configuration_api.get_token("OPEN_AI_API_TOKEN")
            custom_endpoint_url = self.configuration_api.get_token("CUSTOM_ENDPOINT_URL")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
            if custom_endpoint_url != self.ui.lineEdit_base_url_options.text():
                self.ui.lineEdit_base_url_options.setText(custom_endpoint_url)
        elif selected_conversation_method == "OpenRouter":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            self.ui.lineEdit_mistral_model.hide()
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

    def save_custom_url_in_real_time(self):
        self.configuration_api.save_api_token("CUSTOM_ENDPOINT_URL", self.ui.lineEdit_base_url_options.text())

    def save_mistral_model_endpoint_in_real_time(self):
        self.configuration_settings.update_main_setting("mistral_model_endpoint", self.ui.lineEdit_mistral_model.text())

    def initialize_gpu_layers_horizontalSlider(self):
        n_gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")
        self.ui.gpu_layers_horizontalSlider.setValue(n_gpu_layers)
        self.ui.gpu_layers_value_label.setText(self.translations.get("value", "Value: "))
        self.ui.lineEdit_gpuLayers.setText(str(n_gpu_layers))

    def save_gpu_layers_in_real_time(self):
        n_gpu_layers = self.ui.gpu_layers_horizontalSlider.value()
        self.ui.gpu_layers_value_label.setText(self.translations.get("value", "Value: "))
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
            self.ui.gpu_layers_value_label.setText(self.translations.get("value", "Value: "))
            self.ui.lineEdit_gpuLayers.setText(str(n_gpu_layers))
            self.configuration_settings.update_main_setting("gpu_layers", n_gpu_layers)

        except ValueError:
            current_value = self.ui.gpu_layers_horizontalSlider.value()
            self.ui.lineEdit_gpuLayers.setText(str(current_value))

    def initialize_context_size_horizontalSlider(self):
        context_size = self.configuration_settings.get_main_setting("context_size")
        self.ui.context_size_horizontalSlider.setValue(context_size)
        self.ui.context_size_value_label.setText(self.translations.get("value", "Value: "))
        self.ui.lineEdit_contextSize.setText(str(context_size))

    def save_context_size_in_real_time(self):
        context_size = self.ui.context_size_horizontalSlider.value()
        self.ui.lineEdit_contextSize.setText(str(context_size))
        self.ui.context_size_value_label.setText(self.translations.get("value", "Value: "))
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
                self.ui.context_size_value_label.setText(self.translations.get("value", "Value: "))
            else:
                self.ui.context_size_horizontalSlider.setValue(context_size)
                self.ui.context_size_value_label.setText(self.translations.get("value", "Value: "))
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
        self.ui.temperature_value_label.setText(self.translations.get("value", "Value: "))

    def save_temperature_in_real_time(self):
        temperature = self.ui.temperature_horizontalSlider.value()
        scaled_value = temperature / 10.0
        self.configuration_settings.update_main_setting("temperature", scaled_value)
        self.ui.temperature_value_label.setText(self.translations.get("value", "Value: "))
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
            self.ui.temperature_value_label.setText(self.translations.get("value", "Value: "))
            self.ui.lineEdit_temperature.setText(f"{temperature:.1f}")
            self.configuration_settings.update_main_setting("temperature", temperature)

        except ValueError:
            current_value = self.ui.temperature_horizontalSlider.value() / 10.0
            self.ui.lineEdit_temperature.setText(f"{current_value:.1f}")

    def initialize_top_p_horizontalSlider(self):
        top_p = self.configuration_settings.get_main_setting("top_p")
        top_p_int = int(round(top_p * 10))
        self.ui.top_p_horizontalSlider.setValue(top_p_int)
        self.ui.top_p_value_label.setText(self.translations.get("value", "Value: "))
        self.ui.lineEdit_topP.setText(f"{top_p:.1f}")

    def save_top_p_in_real_time(self):
        top_p = self.ui.top_p_horizontalSlider.value()
        scaled_value = top_p / 10.0
        self.configuration_settings.update_main_setting("top_p", scaled_value)
        self.ui.top_p_value_label.setText(self.translations.get("value", "Value: "))
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
            self.ui.top_p_value_label.setText(self.translations.get("value", "Value: "))
            self.ui.lineEdit_topP.setText(f"{top_p:.1f}")
            self.configuration_settings.update_main_setting("top_p", top_p)

        except ValueError:
            current_value = self.ui.top_p_horizontalSlider.value() / 10.0
            self.ui.lineEdit_topP.setText(f"{current_value:.1f}")

    def initialize_repeat_penalty_horizontalSlider(self):
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")
        repeat_penalty_int = int(round(repeat_penalty * 10))
        self.ui.repeat_penalty_horizontalSlider.setValue(repeat_penalty_int)
        self.ui.repeat_penalty_value_label.setText(self.translations.get("value", "Value: "))
        self.ui.lineEdit_repeatPenalty.setText(f"{repeat_penalty:.1f}")

    def save_repeat_penalty_in_real_time(self):
        repeat_penalty = self.ui.repeat_penalty_horizontalSlider.value()
        scaled_value = repeat_penalty / 10.0
        self.configuration_settings.update_main_setting("repeat_penalty", scaled_value)
        self.ui.repeat_penalty_value_label.setText(self.translations.get("value", "Value: "))
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
            self.ui.repeat_penalty_value_label.setText(self.translations.get("value", "Value: "))
            self.ui.lineEdit_repeatPenalty.setText(f"{repeat_penalty:.1f}")
            self.configuration_settings.update_main_setting("repeat_penalty", repeat_penalty)

        except ValueError:
            current_value = self.ui.repeat_penalty_horizontalSlider.value() / 10.0
            self.ui.lineEdit_repeatPenalty.setText(f"{current_value:.1f}")

    def initialize_max_tokens_horizontalSlider(self):
        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        self.ui.max_tokens_horizontalSlider.setValue(max_tokens)
        self.ui.max_tokens_value_label.setText(self.translations.get("value", "Value: "))
        self.ui.lineEdit_maxTokens.setText(str(max_tokens))

    def save_max_tokens_in_real_time(self):
        max_tokens = self.ui.max_tokens_horizontalSlider.value()
        self.configuration_settings.update_main_setting("max_tokens", max_tokens)
        self.ui.max_tokens_value_label.setText(self.translations.get("value", "Value: "))
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
                self.ui.max_tokens_value_label.setText(self.translations.get("value", "Value: "))
            else:
                self.ui.max_tokens_horizontalSlider.setValue(max_tokens)
                self.ui.max_tokens_value_label.setText(self.translations.get("value", "Value: "))
                self.ui.lineEdit_maxTokens.setText(str(max_tokens))

            self.configuration_settings.update_main_setting("max_tokens", max_tokens)

        except ValueError:
            current_value = self.ui.max_tokens_horizontalSlider.value()
            self.ui.lineEdit_maxTokens.setText(str(current_value))
    
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

        self.ui.total_tokens_building_label.setText(f"Total Tokens: {total_tokens}")
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
            file_path, _ = QFileDialog.getOpenFileName(None, "Choose PNG character's card", "", "Images (*.png)")
            if file_path:
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

                    def safe_get(key):
                        val = data.get(key)
                        if isinstance(val, list):
                            return "\n".join(str(x) for x in val)
                        return str(val) if val is not None else ""
                    
                    self.ui.lineEdit_character_name_building.setText(safe_get("name"))

                    self.ui.textEdit_character_description_building.setPlainText(safe_get("description"))
                    self.ui.textEdit_character_personality_building.setPlainText(safe_get("personality"))
                    self.ui.textEdit_first_message_building.setPlainText(safe_get("first_mes"))
                    self.ui.textEdit_example_messages.setPlainText(safe_get("mes_example"))
                    self.ui.textEdit_creator_notes.setPlainText(safe_get("creator_notes"))
                    self.ui.textEdit_character_version.setPlainText(safe_get("character_version"))
                    self.ui.textEdit_scenario.setPlainText(safe_get("scenario"))

                    alternate_greetings = data.get("alternate_greetings", [])
                    formatted_greetings = self.format_alternate_greetings(alternate_greetings)
                    self.ui.textEdit_alternate_greetings.setPlainText(formatted_greetings)
        except Exception as e:
            logger.error(f"Error importing character card: {e}")

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
                QMessageBox.warning(None, "Error", "Not enough information about the character")
                return

            current_image_path = self.configuration_settings.get_user_data("current_character_image")

            if current_image_path and os.path.exists(current_image_path):
                image = Image.open(current_image_path).convert("RGBA")
            else:
                default_image_path = "app/gui/icons/export_card.png"
                image = Image.open(default_image_path).convert("RGBA")

            personas_data = self.configuration_settings.get_user_data("personas")
            current_persona = self.configuration_settings.get_user_data("default_persona")
            if current_persona == "None" or current_persona is None:
                user_name = "User"
            else:
                try:
                    user_name = personas_data[current_persona].get("user_name", "User")
                except Exception as e:
                    user_name = "User"

            char_data = {
                "spec": "chara_card_v2",
                "spec_version": "2.0",
                "data": {
                    'name': self.ui.lineEdit_character_name_building.text().strip(),
                    'description': self.ui.textEdit_character_description_building.toPlainText().strip(),
                    'personality': self.ui.textEdit_character_personality_building.toPlainText().strip(),
                    'first_mes': self.ui.textEdit_first_message_building.toPlainText().strip(),
                    'scenario': self.ui.textEdit_scenario.toPlainText().strip(),
                    'mes_example': self.ui.textEdit_example_messages.toPlainText().strip(),
                    'creator_notes': self.ui.textEdit_creator_notes.toPlainText().strip(),
                    'character_version': self.ui.textEdit_character_version.toPlainText().strip() or "1.0.0",
                    'creator': user_name,
                    'tags': ["sow", "custom"],
                    'extensions': {},
                }
            }

            raw_greetings = self.ui.textEdit_alternate_greetings.toPlainText()
            greetings_list = self.parse_alternate_greetings(raw_greetings)
            char_data["data"]["alternate_greetings"] = greetings_list

            if not char_data["data"]["character_version"]:
                char_data["data"]["character_version"] = "1.0.0"

            char_data["data"]["system_prompt"] = ""
            char_data["data"]["post_history_instructions"] = ""

            json_str = json.dumps(char_data, ensure_ascii=False, indent=2)
            json_bytes = json_str.encode('utf-8')
            b64_data = base64.b64encode(json_bytes).decode('utf-8')

            png_info = PngImagePlugin.PngInfo()
            png_info.add_text("chara", b64_data.encode('utf-8'))

            file_path, _ = QFileDialog.getSaveFileName(
                None,
                "Export Character Card",
                "",
                "PNG Images (*.png)"
            )
            if file_path:
                image.save(file_path, format="PNG", pnginfo=png_info)

        except Exception as e:
            logger.error(f"Error exporting character card: {e}")
            QMessageBox.critical(None, "Error", f"Couldn't export character card:\n{str(e)}")
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
        elif conversation_method in ["Mistral AI", "Open AI", "OpenRouter", "Local LLM"]:
            combo_box.addItem('Nothing')
            combo_box.addItem('ElevenLabs')
            combo_box.addItem('XTTSv2')
            combo_box.addItem('Edge TTS')
            combo_box.addItem('Kokoro')

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

    def create_voice_nothing_widgets(self, character_name):
        layout = QVBoxLayout()

        save_button = QPushButton(self.translations.get("tts_selector_save_button", 'Save Selection'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(save_button, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        def save_voice_mode_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
            message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
            message_box_information.exec()

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
        search_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        search_button.setFixedWidth(100)
        search_button.clicked.connect(lambda: self.search_character_voice(voice_combo, voice_input, character_name))
        search_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        listen_button = QPushButton(self.translations.get("tts_selector_character_ai_listen", 'Listen'))
        listen_button.setFixedHeight(35)
        listen_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        listen_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        listen_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        listen_button.clicked.connect(lambda: self.play_preview_voice(character_name))
        select_button = QPushButton(self.translations.get("tts_selector_select_button", 'Select voice'))
        select_button.setFixedHeight(35)
        select_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        select_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        select_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_button.clicked.connect(lambda: self.select_voice("Character AI", character_name, voice_combo, None, mode="Choice"))

        save_button = QPushButton(self.translations.get("chat_save_message", 'Save'))
        save_button.setFixedHeight(35)
        save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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
        select_voice_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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
        select_voice_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("tts_selector_no_folder", "No Folder"))
                message_box_information.setText(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"))
                message_box_information.exec()
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("tts_selector_no_pth", "No PTH File"))
                    message_box_information.setText(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder)
                    message_box_information.exec()
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "XTTSv2"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
            message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
            message_box_information.exec()

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
        select_voice_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("tts_selector_no_folder", "No Folder"))
                message_box_information.setText(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"))
                message_box_information.exec()
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("tts_selector_no_pth", "No PTH File"))
                    message_box_information.setText(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder)
                    message_box_information.exec()
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Edge TTS"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
            message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
            message_box_information.exec()

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
        select_voice_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("tts_selector_no_folder", "No Folder"))
                message_box_information.setText(self.translations.get("tts_selector_rvc_no_folder", "RVC is enabled, but no folder selected!"))
                message_box_information.exec()
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("tts_selector_no_pth", "No PTH File"))
                    message_box_information.setText(self.translations.get("tts_selector_no_pth_in_folder", "No .pth file found in folder: ") + rvc_folder)
                    message_box_information.exec()
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["voice_type"] = voice_type
            configuration_data["character_list"][character_name]["rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Kokoro"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
            message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
            message_box_information.exec()

        select_voice_button.clicked.connect(save_kokoro_settings)

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

                        message_box_information = QMessageBox()
                        message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                        message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
                        message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
                        message_box_information.exec()
                    else:
                        message_box_information = QMessageBox()
                        message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                        message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
                        message_box_information.setText(self.translations.get("tts_selector_save_information_error", "Choose a voice for the character!"))
                        message_box_information.exec()

                elif mode == "Choice":
                    if voice_id:
                        configuration_data["character_list"][character_name]["voice_name"] = voice_name
                        configuration_data["character_list"][character_name]["character_ai_voice_id"] = voice_id
                        configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                        self.configuration_characters.save_configuration_edit(configuration_data)

                        message_box_information = QMessageBox()
                        message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                        message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
                        message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
                        message_box_information.exec()

            case "ElevenLabs":
                voice_id = data
                
                self.configuration_api.save_api_token("ELEVENLABS_API_TOKEN", elevenlabs_api)
                
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["elevenlabs_voice_id"] = voice_id
                configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                self.configuration_characters.save_configuration_edit(configuration_data)

                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("tts_selector_title_2", "Character Voice"))
                message_box_information.setText(self.translations.get("tts_selector_save_information", "Voice successfully saved!"))
                message_box_information.exec()

    def search_character_voice(self, combobox, voice_input, character_name):
        combobox.clear()
        voice_name = voice_input.text().strip()

        if not voice_name:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("tts_selector_error", "Input Error"))
            message_box_information.setText(self.translations.get("tts_selector_error_2", "Please enter a valid voice name."))
            message_box_information.exec()
            return

        async def fetch_voices():
            try:
                voices = await self.character_ai_client.search_voices(voice_name)
                if voices:
                    for voice in voices:
                        combobox.addItem(voice.name, voice.voice_id)
                else:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("tts_selector_error_3", "No Voices"))
                    message_box_information.setText(self.translations.get("tts_selector_error_4", "No voices found for the given name."))
                    message_box_information.exec()
            except Exception as e:
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("tts_selector_error_5", "Fetch Error"))
                message_box_information.setText(self.translations.get("tts_selector_error_6", "Failed to fetch voices: ") + str(e))
                message_box_information.exec()

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
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        layout.addWidget(save_button, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)

        def save_expression_images_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("expressions_selector_mode_saved", "Expression Mode Saved"))
            message_box_information.setText(self.translations.get("expressions_selector_mode_saved_body", "Expression mode successfully saved!"))
            message_box_information.exec()

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
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("expressions_selector_folder_saved_title", "Expression Folder Saved"))
            message_box_information.setText(self.translations.get("expressions_selector_foler_saved_body", "Expression folder successfully saved!"))
            message_box_information.exec()

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
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("expressions_selector_live2d_folder_saved_title", "Live2D Folder Saved"))
            message_box_information.setText(self.translations.get("expressions_selector_live2d_folder_saved_body", "Live2D folder successfully saved!"))
            message_box_information.exec()

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
        save_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
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

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("expressions_selector_vrm_file_saved_title", "VRM File Saved"))
            message_box_information.setText(self.translations.get("expressions_selector_vrm_file_saved_body", "VRM file successfully saved!"))
            message_box_information.exec()

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
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_card_page": self.ui.scrollArea_character_card
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.cai_cards.clear()
        self.gate_cards.clear()

        self.ui.stackedWidget.setCurrentIndex(4)
        
        match current_tab_index:
            case 0:  # Character AI
                self.ui.stackedWidget_character_ai.setCurrentIndex(0)
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
                            conversation_method="Character AI", character_name=character_name, 
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
            case 1:  # Chub AI
                self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
                self.ui.checkBox_enable_nsfw.show()

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
                        conversation_method="Not Character AI", character_name=character_name, 
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
        """
        Character cards design from CAI section
        """
        self.ui.scrollArea_character_ai_page.setViewportMargins(0, 0, 0, 0)
        self.ui.scrollArea_character_ai_page.verticalScrollBar().setStyleSheet("width: 0px;")
        self.ui.scrollArea_character_ai_page.horizontalScrollBar().setStyleSheet("height: 0px;")
        
        vertical_layout = QVBoxLayout(character_card)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(0)

        avatar_frame = QFrame()
        avatar_frame.setMinimumSize(200, 0)
        avatar_frame.setMaximumSize(200, 90)
        avatar_frame.setStyleSheet("background: transparent;")

        grid_layout = QtWidgets.QGridLayout(avatar_frame)
        grid_layout.setContentsMargins(0, 10, 0, 0)
        grid_layout.setSpacing(0)

        avatar_label = QLabel()
        avatar_label.setMinimumSize(QtCore.QSize(80, 80))
        avatar_label.setMaximumSize(QtCore.QSize(80, 80))
        avatar_label.setScaledContents(True)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if avatar_path:
            pixmap = QPixmap(avatar_path)
            mask = QPixmap(pixmap.size())
            mask.fill(Qt.GlobalColor.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
            painter.end()
            pixmap.setMask(mask.createMaskFromColor(Qt.GlobalColor.transparent))
            avatar_label.setPixmap(pixmap.scaled(
                80, 80, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            avatar_label.setStyleSheet("background-color: #23272a;")
            avatar_label.setText("[Avatar]")

        grid_layout.addWidget(avatar_label, 0, 0, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        
        vertical_layout.addWidget(avatar_frame)

        name_label = QLabel(character_name)
        name_label.setMinimumSize(QtCore.QSize(200, 0))
        name_label.setMaximumSize(QtCore.QSize(200, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("text-align: center; background: transparent; color: white;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        vertical_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        info_layout = QtWidgets.QGridLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)

        description_label = QLabel(character_title)
        description_label.setMinimumSize(QtCore.QSize(200, 0))
        description_label.setMaximumSize(QtCore.QSize(200, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        description_label.setFont(font)
        description_label.setStyleSheet("text-align: center; background: transparent; color: #b9bbbe;")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        info_layout.addWidget(description_label, 0, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        stats_layout = QHBoxLayout()
        stats_layout.addStretch()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if likes is not None:
            likes_label = QLabel(f"\u2764 {likes}")
            likes_label.setStyleSheet("text-align: center; background: transparent; font-size: 11px; color: #e62929;")
            stats_layout.addWidget(likes_label)
        
        downloads_label = QLabel(f"\ud83d\udcbe {downloads}")
        downloads_label.setStyleSheet("text-align: center; background: transparent; font-size: 11px; color: #6880ba;")
        stats_layout.addWidget(downloads_label)
        stats_layout.addStretch()
        
        info_layout.addLayout(
            stats_layout, 
            1, 0, 
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
        )
        vertical_layout.addLayout(info_layout)

        button_frame = QFrame()
        button_frame.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(5, 0, 5, 0)

        add_to_cai_button = PushButton("#333333", "#444444", "character_card", "")
        add_to_cai_button.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 15px;
                padding: 8px 16px;
                font-size: 10px;
                background-color: #333333;
                color: #ffffff;
            }
        """)
        add_to_cai_button.setObjectName("AddToCharacterAI")
        add_to_cai_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        add_to_cai_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_to_cai_button.clicked.connect(lambda: self.add_character_from_cai_gateway_sync(character_id))
        add_to_cai_button.setText(self.translations.get("characters_gateway_cai_add", "Add to the list"))

        button_layout.addWidget(add_to_cai_button)
        vertical_layout.addWidget(button_frame)

        return character_card

    def update_gate_layout(self, tab):
        """
        Updates the layout of character cards in the specified tab with adaptive margins.
        """
        match tab:
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
        if self.ui.scrollArea_character_ai_page.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("character_ai"))
        elif self.ui.scrollArea_character_card.isVisible():
            QtCore.QTimer.singleShot(0, lambda: self.update_gate_layout("chub_ai"))

    def create_chub_character_card(self, character_card, character_name, character_title, avatar_path, downloads, likes, total_tokens, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings):
        """
        Character cards design from Chub AI section
        """
        self.ui.scrollArea_character_card.setViewportMargins(0, 0, 0, 0)
        self.ui.scrollArea_character_card.verticalScrollBar().setStyleSheet("width: 0px;")
        self.ui.scrollArea_character_card.horizontalScrollBar().setStyleSheet("height: 0px;")

        alternate_greetings = alternate_greetings if not None else None
        vertical_layout = QVBoxLayout(character_card)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(5)

        avatar_frame = QFrame()
        avatar_frame.setMinimumSize(200, 0)
        avatar_frame.setMaximumSize(200, 90)
        avatar_frame.setStyleSheet("background: transparent;")

        grid_layout = QtWidgets.QGridLayout(avatar_frame)
        grid_layout.setContentsMargins(0, 10, 0, 0)
        grid_layout.setSpacing(0)

        avatar_label = QLabel()
        avatar_label.setMinimumSize(QtCore.QSize(80, 80))
        avatar_label.setMaximumSize(QtCore.QSize(80, 80))
        avatar_label.setScaledContents(True)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if avatar_path:
            pixmap = QPixmap(avatar_path)
            mask = QPixmap(pixmap.size())
            mask.fill(Qt.GlobalColor.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(Qt.GlobalColor.black)
            painter.setPen(QtCore.Qt.GlobalColor.transparent)
            painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
            painter.end()
            pixmap.setMask(mask.createMaskFromColor(Qt.GlobalColor.transparent))
            avatar_label.setPixmap(pixmap.scaled(
                80, 80, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            avatar_label.setStyleSheet("background-color: #23272a;")
            avatar_label.setText("[Avatar]")

        grid_layout.addWidget(avatar_label, 0, 0, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        vertical_layout.addWidget(avatar_frame, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_label = QLabel(character_name)
        name_label.setMinimumSize(QtCore.QSize(200, 0))
        name_label.setMaximumSize(QtCore.QSize(200, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("text-align: center; background: transparent; color: white;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        vertical_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        def truncate_text(text, max_words):
            words = text.split()
            if len(words) > max_words:
                return " ".join(words[:max_words]) + "..."
            return text

        max_words = 6
        cropped_description = truncate_text(character_title, max_words)

        description_label = QLabel(cropped_description)
        description_label.setMinimumSize(QtCore.QSize(200, 0))
        description_label.setMaximumSize(QtCore.QSize(200, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        description_label.setFont(font)
        description_label.setStyleSheet("text-align: center; background: transparent; color: #b9bbbe;")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)
        vertical_layout.addWidget(description_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(10)
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if likes is not None:
            likes_label = QLabel(f"\u2764 {likes}")
            likes_label.setStyleSheet("text-align: center; background: transparent; font-size: 11px; color: #e62929;")
            stats_layout.addWidget(likes_label)

        downloads_label = QLabel(f"\ud83d\udcbe {downloads}")
        downloads_label.setStyleSheet("text-align: center; background: transparent; font-size: 11px; color: #6880ba;")
        stats_layout.addWidget(downloads_label)

        vertical_layout.addLayout(stats_layout)

        tokens_label = QLabel(f"\u2699 Total tokens: {total_tokens}")
        tokens_label.setStyleSheet("text-align: center; background: transparent; font-size: 11px; color: #6880ba;")
        tokens_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vertical_layout.addWidget(tokens_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        button_frame = QFrame()
        
        button_frame.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                border: 2px solid transparent;
                border-radius: 15px;
                width: 30px;
                height: 30px;
                padding: 0;
                margin: 5px;
            }
        """)

        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(5, 0, 5, 0)
        button_layout.setSpacing(0)

        buttons_data = [
            ("app/gui/icons/mistralai.png", "Add to Mistral AI", "Mistral AI"),
            ("app/gui/icons/openai.png", "Add to Open AI", "Open AI"),
            ("app/gui/icons/openrouter.png", "Add to OpenRouter", "OpenRouter"),
            ("app/gui/icons/local_llm.png", "Add to Local LLM", "Local LLM"),
        ]

        for icon_path, button_text, conversation_method in buttons_data:
            button = PushButton("#333333", "#444444", "character_card_2", button_text)
            button.setObjectName(button_text.replace(" ", ""))
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            button.setIconSize(QtCore.QSize(18, 18))
            button.setIcon(icon)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(
                lambda _, cm=conversation_method: self.add_character_from_gateway(
                    character_name, character_title, avatar_path, character_personality, first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, conversation_method=cm
                )
            )
            button_layout.addWidget(button)

        vertical_layout.addWidget(button_frame, alignment=Qt.AlignmentFlag.AlignHCenter)

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
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_card_page": self.ui.scrollArea_character_card
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        self.cai_cards.clear()
        self.gate_cards.clear()

        match current_tab_index:
            case 0: # Character AI
                self.ui.stackedWidget_character_ai.setCurrentIndex(0)
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
                            conversation_method="Character AI", character_name=character_name, 
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
            case 1: # Chub AI
                self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
                self.ui.checkBox_enable_nsfw.show()

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
                        conversation_method="Not Character AI", character_name=character_name, 
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

    def add_character_from_gateway(self, character_name, character_title, character_avatar_directory, character_personality, character_first_message, character_tavern_personality, example_dialogs, character_scenario, alternate_greetings, conversation_method):
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
                        selected_lorebook="None",
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
                        selected_lorebook="None",
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
                        selected_lorebook="None",
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
                        selected_lorebook="None",
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
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(30, 30, 30);
                border-radius: 10px;
            }
            QLabel {
                color: rgb(200, 200, 200);
            }
            QLineEdit, QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
            }
            QFrame#separator {
                background-color: rgb(60, 60, 60);
                border: none;
                height: 1px;
            }
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
        """)

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        avatar_label = QLabel(dialog)
        pixmap = QPixmap(character_avatar)
        mask = QPixmap(pixmap.size())
        mask.fill(Qt.GlobalColor.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()

        pixmap.setMask(mask.createMaskFromColor(Qt.GlobalColor.transparent))
        avatar_label.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        avatar_label.setFixedSize(100, 100)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setScaledContents(True)

        name_label = QLabel(character_name, dialog)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        name_label.setFont(font)
        name_label.setStyleSheet("text-align: center; background: transparent; color: rgb(227, 227, 227);")
        name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(avatar_label)
        main_layout.addLayout(header_layout)
        main_layout.addWidget(name_label)

        creator_info_button = QPushButton(self.translations.get("creator_info_button", "Creator Notes"), dialog)
        creator_info_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        creator_info_button.setFixedHeight(35)
        creator_info_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        creator_info_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        creator_info_button.clicked.connect(lambda: show_creator_info(character_title))
        main_layout.addWidget(creator_info_button)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

        scroll_area = QtWidgets.QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        def show_creator_info(character_title):
            info_dialog = QDialog(dialog)
            info_dialog.setWindowTitle(self.translations.get("creator_info_window_title", "Creator Notes"))
            info_dialog.setMinimumSize(400, 300)
            info_dialog.setStyleSheet("""
                QDialog {
                    background-color: rgb(30, 30, 30);
                    border-radius: 10px;
                }
                QLabel {
                    color: rgb(200, 200, 200);
                }
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(60, 60, 60);
                    border-radius: 5px;
                    padding: 10px;
                    selection-color: rgb(255, 255, 255);
                    selection-background-color: rgb(39, 62, 135);
                }
                QPushButton {
                    background-color: rgb(60, 60, 60);
                    color: rgb(255, 255, 255);
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

            layout = QVBoxLayout(info_dialog)

            title_label = QLabel(self.translations.get("creator_info_title", "Title from Creator:"), info_dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_label.setFont(font)
            layout.addWidget(title_label)

            title_text_edit = QTextEdit(info_dialog)
            title_text_edit.setPlainText(character_title)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_text_edit.setFont(font)
            title_text_edit.setReadOnly(True)
            title_text_edit.setMinimumHeight(100)
            layout.addWidget(title_text_edit)

            close_button = QPushButton(self.translations.get("creator_info_close_button", "Close"), info_dialog)
            close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            close_button.setFixedHeight(35)
            close_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            close_button.clicked.connect(info_dialog.close)
            layout.addWidget(close_button)

            info_dialog.exec()

        def create_readonly_text_edit(label_text, content):
            label = QLabel(label_text, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            label.setFont(font)
            scroll_layout.addWidget(label)

            text_edit = QTextEdit(dialog)
            text_edit.setPlainText(content)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            text_edit.setFont(font)
            text_edit.setReadOnly(True)
            text_edit.setMinimumHeight(200)

            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(220, 220, 210, 1);
                    padding: 10px;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 15px 0px 15px 0px;
                    border-radius: 5px;
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
            
            scroll_layout.addWidget(text_edit)

            return text_edit

        if conversation_method == "Character AI":
            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(6)
            form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignVCenter)
            form_layout.setHorizontalSpacing(10)

            title_edit = QLineEdit(character_title, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_edit.setFont(font)
            title_edit.setReadOnly(True)
            title_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            title_edit.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); color: rgba(220, 220, 210, 1);")
            title_edit.setMaximumHeight(50)

            form_layout.addRow(title_edit)

            group_box = QtWidgets.QGroupBox()
            group_box.setLayout(form_layout)
            group_box.setStyleSheet("QGroupBox { border: none; padding: 0px; margin-top: 5px; }")

            scroll_layout.addWidget(group_box)
        else:
            create_readonly_text_edit(
                self.translations.get("character_edit_description", "Character Description:"),
                character_description
            )

            create_readonly_text_edit(
                self.translations.get("character_edit_personality", "Character Personality:"),
                character_personality
            )

            create_readonly_text_edit(
                self.translations.get("scenario", "Scenario:"),
                scenario
            )

            create_readonly_text_edit(
                self.translations.get("character_edit_first_message", "Character First Message:"),
                first_message
            )

            create_readonly_text_edit(
                self.translations.get("example_messages_title", "Example Messages:"),
                example_messages
            )

            create_readonly_text_edit(
                self.translations.get("alternate_greetings_label", "Alternate Greetings:"),
                "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings or ""
            )

            create_readonly_text_edit(
                self.translations.get("creator_notes_label", "Creator Notes:"),
                character_title
            )

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_button = QPushButton("OK", dialog)
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        ok_button.setFixedHeight(35)
        ok_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.clicked.connect(dialog.close)
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

        dialog.exec()
    ### CHARACTER GATEWAY ==============================================================================

    ### MODELS HUB =====================================================================================
    def show_my_models(self):
        self.stop_recommendation_worker()
        self.stop_popular_worker()
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
        
        for name, path, size in sorted_files:
            widget = ModelListItemWidget(
                model_name=name,
                file_size_bytes=size,
                full_path=path,
                refresh_method=self.show_my_models,
                launch_server_method=self.on_pushButton_launch_server_clicked,
                stop_server_method=self.local_ai_client.on_shutdown_button_clicked,
                ui=self.ui,
                parent=self.ui.listWidget_models_hub
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

        self.recommendations_worker = ModelRecommendations(
            available_ram_gb=available_ram
        )
        try:
            self.recommendations_worker.progress.disconnect()
            self.recommendations_worker.finished.disconnect()
            self.recommendations_worker.error.disconnect()
        except TypeError:
            pass

        self.recommendations_worker.progress.connect(self.add_model_to_list)
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
        widget.setMinimumWidth(300)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        name_label = QLabel(f"<b>Model:</b> {model_data.get('id', 'Unknown')}")
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-size: 14px; color: #ffffff;")
        layout.addWidget(name_label)

        author_label = QLabel(f"<b>Author:</b> {model_data.get('author', 'Unknown')}")
        author_label.setWordWrap(True)
        author_label.setStyleSheet("font-size: 13px; color: #cccccc;")
        layout.addWidget(author_label)

        tags = model_data.get("tags", "").split(", ")
        tags_str = ", ".join(tags[:5]) + ("..." if len(tags) > 5 else "")
        tags_label = QLabel(f"<b>Tags:</b> {tags_str}")
        tags_label.setWordWrap(True)
        tags_label.setStyleSheet("font-size: 12px; color: #888888;")
        layout.addWidget(tags_label)

        description = model_data.get("description", "No description")
        description_widget = QWidget()
        description_layout = QVBoxLayout(description_widget)
        description_label = QLabel(f"<b>Description:</b><br>{description}")
        description_label.setWordWrap(True)
        description_label.setOpenExternalLinks(True)
        description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        description_label.setStyleSheet("font-size: 12px; color: #bbbbbb;")
        description_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        description_layout.addWidget(description_label)
        description_layout.setContentsMargins(0, 0, 0, 0)
        description_layout.setSpacing(0)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(description_widget)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }              
            QScrollBar:horizontal {
                background: #2a2a2a;
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4a4a4a;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        layout.addWidget(scroll_area)

        downloads_label = QLabel(f"<b>Downloads: </b> {model_data.get('downloads', 0)}")
        downloads_label.setStyleSheet("font-size: 14px; color: #aaaaaa;")
        layout.addWidget(downloads_label)

        likes_label = QLabel(f"<b>❤️ Likes: </b> {model_data.get('likes', 0)}")
        likes_label.setStyleSheet("font-size: 14px; color: #777777;")
        layout.addWidget(likes_label)

        close_button = QPushButton("✕")
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.setFixedSize(25, 25)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999999;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        close_button.clicked.connect(lambda: self.close_model_info())

        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        widget.setStyleSheet("""
            QWidget#model_info_card {
                background-color: #2a2a2a;
                border: 1px solid #3a3a3a;
            }
        """)

        return widget

    def on_info_received(self, data):
        if self.model_information_widget and self.model_information_widget.layout():
            while self.model_information_widget.layout().count():
                item = self.model_information_widget.layout().takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        elif not self.model_information_widget:
            self.model_information_widget = self.create_model_info_widget(data)

            if self.ui.centralwidget.layout() is None:
                central_layout = QtWidgets.QHBoxLayout(self.ui.centralwidget)
            else:
                central_layout = self.ui.centralwidget.layout()
            central_layout.addWidget(self.model_information_widget)
        else:
            self.clear_layout(self.model_info_layout)
    
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
            QMessageBox.information(self, "No files", "There are no .gguf files in this repository.")
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
        QMessageBox.information(self, "The model has been downloaded.", f"Path:\n{path}")

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
            current_emotion = chats[current_chat]["current_emotion"]
        else:
            self.ui.pushButton_author_notes.hide()
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
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                message_box_information.setWindowTitle(self.translations.get("llm_error_title", "No Local LLM"))
                message_box_information.setText(self.translations.get("llm_error_body", "Choose Local LLM in the options."))
                message_box_information.exec()
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
            expression_layout = QtWidgets.QVBoxLayout(self.expression_widget)
            expression_layout.setContentsMargins(0, 0, 0, 0)
            expression_layout.setSpacing(0)

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
            self.ui.pushButton_send_message.clicked.disconnect()
        except TypeError:
            pass
        
        chat_background = self.configuration_settings.get_main_setting("chat_background_image")

        if chat_background != "None":
            chat_background = chat_background.replace("\\", "/")
            self.ui.scrollArea_chat.setStyleSheet(f"""
                QScrollArea {{
                    background-color: rgb(27, 27, 27);
                    border: none;
                    padding: 5px;
                    margin: 5px;
                    border-image: url({chat_background});
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
                    background-color: rgb(27,27,27);
                    border: none;
                    padding: 5px;
                    margin-top: 5px;
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
        
    def draw_circle_avatar(self, avatar_path):
        """
        Draws a character's avatar
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
        self.ui.character_avatar_label.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        self.ui.character_avatar_label.setFixedSize(40, 40)
        self.ui.character_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.ui.character_avatar_label.setScaledContents(True)

    def open_more_button(self, conversation_method, character_name, character_avatar):
        """
        Opens a dialog with additional settings for the character.
        """
        dialog = QDialog()
        dialog.setWindowTitle(self.translations.get("character_edit_settings", "Character Settings: ") + character_name)
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setMinimumSize(600, 500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(30, 30, 30);
                border-radius: 10px;
            }
            QLabel {
                color: rgb(200, 200, 200);
            }
            QLineEdit, QTextEdit {
                background-color: rgb(40, 40, 40);
                color: rgb(227, 227, 227);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                padding: 10px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
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
            QFrame#separator {
                background-color: rgb(60, 60, 60);
                border: none;
                height: 1px;
            }
            QScrollArea {
                background-color: rgb(30, 30, 30);
                border: none;
            }
        """)

        character_data = self.configuration_characters.load_configuration()
        if "character_list" not in character_data or character_name not in character_data["character_list"]:
            logger.error(f"Character '{character_name}' not found in the configuration.")
            return

        character_information = character_data["character_list"][character_name]
        character_title = character_information.get("character_title")
        character_description = character_information.get("character_description")
        character_personality = character_information.get("character_personality")
        first_message = character_information.get("first_message")
        scenario = character_information.get("scenario")
        example_messages = character_information.get("example_messages")
        alternate_greetings = character_information.get("alternate_greetings")
        creator_notes = character_information.get("character_title")

        main_layout = QVBoxLayout(dialog)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        header_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        avatar_label = QLabel(dialog)
        pixmap = QPixmap(character_avatar)
        mask = QPixmap(pixmap.size())
        mask.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtCore.Qt.GlobalColor.black)
        painter.setPen(QtCore.Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()

        pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
        avatar_label.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        avatar_label.setFixedSize(100, 100)
        avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        avatar_label.setScaledContents(True)

        if conversation_method != "Character AI":
            name_edit = QLineEdit(character_name, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(15)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            name_edit.setFont(font)
            name_edit.setReadOnly(False)
            name_edit.setStyleSheet("""
                background-color: rgba(0, 0, 0, 0.3);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(60, 60, 60);
                border-radius: 5px;
                selection-color: rgb(255, 255, 255);
                selection-background-color: rgb(39, 62, 135);
            """)
            name_edit.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            name_edit.setFixedHeight(45)
            name_edit.setCursorPosition(0)
            
            header_layout.addWidget(avatar_label)
            main_layout.addLayout(header_layout)
            main_layout.addWidget(name_edit)
        else:
            name_label = QLabel(character_name, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(16)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            name_label.setFont(font)
            name_label.setStyleSheet("text-align: center; background: transparent; color: rgb(227, 227, 227);")
            name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            header_layout.addWidget(avatar_label)
            main_layout.addLayout(header_layout)
            main_layout.addWidget(name_label)

        creator_info_button = QPushButton(self.translations.get("creator_info_button", "Creator Info"), dialog)
        creator_info_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        creator_info_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        creator_info_button.setFixedHeight(35)
        creator_info_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        creator_info_button.setFont(font)
        creator_info_button.clicked.connect(lambda: show_creator_info(character_title))
        main_layout.addWidget(creator_info_button)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

        scroll_area = QtWidgets.QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        def show_creator_info(character_title):
            info_dialog = QDialog(dialog)
            info_dialog.setWindowTitle(self.translations.get("creator_info_window_title", "Creator Information"))
            info_dialog.setMinimumSize(400, 300)
            info_dialog.setStyleSheet("""
                QDialog {
                    background-color: rgb(30, 30, 30);
                    border-radius: 10px;
                }
                QLabel {
                    color: rgb(200, 200, 200);
                }
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgb(255, 255, 255);
                    border: 1px solid rgb(60, 60, 60);
                    border-radius: 5px;
                    padding: 10px;
                    selection-color: rgb(255, 255, 255);
                    selection-background-color: rgb(39, 62, 135);
                }
                QPushButton {
                    background-color: rgb(60, 60, 60);
                    color: rgb(255, 255, 255);
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

            layout = QVBoxLayout(info_dialog)

            title_label = QLabel(self.translations.get("creator_info_title", "Title from Creator:"), info_dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_label.setFont(font)
            layout.addWidget(title_label)

            title_text_edit = QTextEdit(info_dialog)
            title_text_edit.setPlainText(character_title)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_text_edit.setFont(font)
            title_text_edit.setReadOnly(True)
            title_text_edit.setMinimumHeight(100)
            layout.addWidget(title_text_edit)

            close_button = QPushButton(self.translations.get("creator_info_close_button", "Close"), info_dialog)
            close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            close_button.setFixedHeight(35)
            close_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            close_button.setFont(font)
            close_button.clicked.connect(info_dialog.close)
            layout.addWidget(close_button)

            info_dialog.exec()

        def create_editable_text_edit(label_text, content, placeholder="", is_read_only=False):
            label = QLabel(label_text, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            label.setFont(font)
            scroll_layout.addWidget(label)

            text_edit = QTextEdit(dialog)
            text_edit.setPlainText(content)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            text_edit.setFont(font)
            text_edit.setReadOnly(is_read_only)

            text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(220, 220, 210, 1);
                    padding: 10px;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 15px 0px 15px 0px;
                    border-radius: 5px;
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

            if placeholder and conversation_method != "Character AI":
                text_edit.setPlaceholderText(placeholder)
            text_edit.setMinimumHeight(200)
            scroll_layout.addWidget(text_edit)

            edit_button = QPushButton(self.translations.get("chat_edit_message_2", "Edit"), dialog)
            edit_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            edit_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            edit_button.setFixedHeight(35)
            edit_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            edit_button.setFont(font)
            edit_button.clicked.connect(lambda: open_edit_dialog(text_edit))
            scroll_layout.addWidget(edit_button)

            return text_edit

        def open_edit_dialog(text_edit):
            edit_dialog = QDialog(dialog)
            edit_dialog.setWindowTitle(self.translations.get("character_edit_edit_title", "Edit text"))
            edit_dialog.setMinimumSize(400, 300)

            layout = QVBoxLayout(edit_dialog)

            edit_text_edit = QTextEdit(edit_dialog)
            edit_text_edit.setPlainText(text_edit.toPlainText())
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(11)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            edit_text_edit.setFont(font)
            edit_text_edit.setStyleSheet("""
                QTextEdit {
                    background-color: rgba(0, 0, 0, 0.3);
                    color: rgba(220, 220, 210, 1);
                    padding: 10px;
                    border: 1px solid #444;
                    border-radius: 5px;
                }
                
                QScrollBar:vertical {
                    background-color: #2b2b2b;
                    width: 12px;
                    margin: 15px 0px 15px 0px;
                    border-radius: 5px;
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
            layout.addWidget(edit_text_edit)

            button_layout = QHBoxLayout()
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"), edit_dialog)
            save_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            save_button.setFixedHeight(35)
            save_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cancel_button = QPushButton(self.translations.get("character_edit_cancel", "Cancel"), edit_dialog)
            cancel_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            cancel_button.setFixedHeight(35)
            cancel_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            cancel_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            save_button.setFont(font)
            cancel_button.setFont(font)

            save_button.clicked.connect(lambda: save_edit_changes(edit_text_edit, text_edit))
            cancel_button.clicked.connect(edit_dialog.close)

            button_layout.addWidget(save_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            edit_dialog.exec()

        def save_edit_changes(edit_text_edit, original_text_edit):
            new_text = edit_text_edit.toPlainText()
            original_text_edit.setPlainText(new_text)

        if conversation_method == "Character AI":
            form_layout = QtWidgets.QFormLayout()
            form_layout.setVerticalSpacing(6)
            form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
            form_layout.setHorizontalSpacing(10)

            title_edit = QLineEdit(character_title, dialog)
            font = QtGui.QFont()
            font.setFamily("Inter Tight Medium")
            font.setPointSize(10)
            font.setBold(True)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            title_edit.setFont(font)
            title_edit.setReadOnly(True)
            title_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            title_edit.setStyleSheet("background-color: rgba(0, 0, 0, 0.3); color: rgba(220, 220, 210, 1);")
            title_edit.setMaximumHeight(50)

            form_layout.addRow(title_edit)

            group_box = QtWidgets.QGroupBox()
            group_box.setLayout(form_layout)
            group_box.setStyleSheet("QGroupBox { border: none; padding: 0px; margin-top: 5px; }")

            scroll_layout.addWidget(group_box)
        else:
            description_edit = create_editable_text_edit(
                self.translations.get("character_edit_description", "Character Description:"),
                character_description,
                placeholder=self.translations.get("character_edit_description_placeholder_1", "Enter the character's description"),
                is_read_only=False
            )

            personality_edit = create_editable_text_edit(
                self.translations.get("character_edit_personality", "Character Personality:"),
                character_personality,
                placeholder=self.translations.get("character_edit_personality_placeholder", "Enter the character's personality traits"),
                is_read_only=False
            )

            scenario_edit = create_editable_text_edit(
                self.translations.get("scenario", "Scenario:"),
                scenario,
                placeholder=self.translations.get("placeholder_scenario", "Conversation scenario:"),
                is_read_only=False
            )

            first_message_edit = create_editable_text_edit(
                self.translations.get("character_edit_first_message", "Character First Message:"),
                first_message,
                placeholder=self.translations.get("character_edit_first_message_placeholder", "Enter the character's first message"),
                is_read_only=False
            )

            example_messages_edit = create_editable_text_edit(
                self.translations.get("example_messages_title", "Example Messages:"),
                example_messages,
                placeholder=self.translations.get("placeholder_example_messages", "Describes how the character speaks. Before each example, you must insert the <START> macro"),
                is_read_only=False
            )

            alternate_greetings_edit = create_editable_text_edit(
                self.translations.get("alternate_greetings_label", "Alternate Greetings:"),
                "\n\n".join([f"<GREETING>\n{g.strip()}" for g in alternate_greetings if g.strip()]) if isinstance(alternate_greetings, list) else alternate_greetings or "",
                placeholder=self.translations.get("placeholder_alternate_greetings", "You can include as many alternative greetings as you like. Before each alternate greeting, you must insert the <GREETING> macro"),
                is_read_only=False
            )

            creator_notes_edit = create_editable_text_edit(
                self.translations.get("creator_notes_label", "Creator Notes:"),
                creator_notes,
                placeholder=self.translations.get("placeholder_creator_notes", "Any additional notes about the character card"),
                is_read_only=False
            )

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        separator = QFrame(dialog)
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        separator.setStyleSheet("""
            #separator {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #333333, stop:0.5 #444444, stop:1 #333333);
                min-height: 2px;
                margin: 12px 0px;
                border: none;
            }
        """)
        main_layout.addWidget(separator)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        ok_button = QPushButton("OK", dialog)
        ok_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        ok_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        ok_button.setFixedHeight(35)
        ok_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        ok_button.setFont(font)
        ok_button.clicked.connect(dialog.close)
        button_layout.addWidget(ok_button)

        if conversation_method != "Character AI":
            save_button = QPushButton(self.translations.get("character_edit_save_button", "Save"), dialog)
            save_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            save_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            save_button.setFixedHeight(35)
            save_button.setStyleSheet("QPushButton {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #2f2f2f,\n"
    "        stop: 1 #1e1e1e\n"
    "    );\n"
    "    color: rgb(227, 227, 227);\n"
    "    border: 2px solid #3A3A3A;\n"
    "    border-radius: 5px;\n"
    "    padding: 2px;\n"
    "}\n"
    "\n"
    "QPushButton:hover {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #343434,\n"
    "        stop: 1 #222222\n"
    "    );\n"
    "    border: 2px solid #666666;\n"
    "    border-top: 2px solid #777777;\n"
    "    border-bottom: 2px solid #555555;\n"
    "}\n"
    "\n"
    "QPushButton:pressed {\n"
    "    background-color: qlineargradient(\n"
    "        spread: pad,\n"
    "        x1: 0, y1: 0, x2: 0, y2: 1,\n"
    "        stop: 0 #4a4a4a,\n"
    "        stop: 1 #3a3a3a\n"
    "    );\n"
    "    border: 2px solid #888888;\n"
    "}")
            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(8)
            font.setBold(False)
            font.setWeight(50)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            save_button.setFont(font)
            save_button.clicked.connect(lambda: self.save_changes(dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit))
            button_layout.addWidget(save_button)

        new_dialog_button = QPushButton(self.translations.get("character_edit_start_new_dialogue", "Start new chat"), dialog)
        new_dialog_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        new_dialog_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        new_dialog_button.setFixedHeight(35)
        new_dialog_button.setStyleSheet("QPushButton {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #2f2f2f,\n"
"        stop: 1 #1e1e1e\n"
"    );\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 5px;\n"
"    padding: 2px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #343434,\n"
"        stop: 1 #222222\n"
"    );\n"
"    border: 2px solid #666666;\n"
"    border-top: 2px solid #777777;\n"
"    border-bottom: 2px solid #555555;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #888888;\n"
"}")
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        new_dialog_button.setFont(font)
        try:
            new_dialog_button.clicked.disconnect()
        except TypeError:
            pass
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
        
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
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
                user_description = "Interacts with the character using the Soul of Waifu program, which allows the user to interact with large language models."
            else:
                try:
                    user_name = personas_data[current_persona].get("user_name", "User")
                    user_description = personas_data[current_persona].get("user_description", "")
                except Exception as e:
                    user_name = "User"
                    user_description = "Interacts with the character using the Soul of Waifu program, which allows the user to interact with large language models."
            
                

            user_text_original = self.textEdit_write_user_message.toPlainText().strip()
            user_text = user_text_original

            match translator:
                case 0:
                    # No translation needed
                    pass
                case 1:
                    # Google Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(user_text_original, "google", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 2:
                    # Yandex Translate
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", 'en')
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate(user_text_original, "yandex", "en")
                            else:
                                pass
                        case 2:
                            pass
                case 3:
                    # Local translation
                    match translator_mode:
                        case 0:
                            if target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 1:
                            if target_language == 0:
                                user_text = self.translator.translate_local(user_text_original, "ru", "en")
                            else:
                                pass
                        case 2:
                            pass

            user_text_markdown = self.markdown_to_html(user_text_original)
            
            if user_text:
                user_message_container = await self.add_message(character_name, "", is_user=True, message_id=None)
                user_message_label = user_message_container["label"]

                user_message_label.setText(user_text_markdown)
                await asyncio.sleep(0.05)
                self.textEdit_write_user_message.clear()
                
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
                                self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                        
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

                        match sow_system_status:
                            case False:
                                pass
                            case True:
                                match current_sow_system_mode:
                                    case "Nothing":
                                        pass
                                    case "Expressions Images" | "Live2D Model" | "VRM":
                                        current_emotion = await self.detect_emotion(character_name, original_text)

                        match translator:
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
                                # Local translation
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
                                if translator != 0:
                                    self.worker = XTTSv2(text=full_text_tts, language="ru", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                                else:
                                    self.worker = XTTSv2(text=full_text_tts, language="en", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                self.worker = KokoroTTS(text=full_text_tts, character_name=character_name, ui=self.ui)
                                self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                self.worker.start()

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
                        

                        match sow_system_status:
                            case False:
                                pass
                            case True:
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

                        match translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 3:
                                # Local translation
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
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
                                if translator != 0:
                                    self.worker = XTTSv2(text=full_text_tts, language="ru", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                                else:
                                    self.worker = XTTSv2(text=full_text_tts, language="en", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                self.worker = KokoroTTS(text=full_text_tts, character_name=character_name, ui=self.ui)
                                self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                self.worker.start()
                    
                    case "Local LLM" | "Open AI" | "OpenRouter":
                        character_data = configuration_data["character_list"].get(character_name)
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
                                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                        elif conversation_method in ["Open AI", "OpenRouter"]:
                            async for chunk in self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description):
                                if chunk:
                                    if conversation_method == "OpenRouter":
                                        corrected_chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk
                                        full_text += corrected_chunk
                                    else:
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

                        match sow_system_status:
                            case False:
                                pass
                            case True:
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

                        match translator:
                            case 0:
                                pass
                            case 1:
                                # Google Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "google", 'ru')
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 2:
                                # Yandex Translate
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate(full_text_html, "yandex", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                            case 3:
                                # Local translation
                                match translator_mode:
                                    case 0:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
                                        else:
                                            pass
                                    case 1:
                                        pass
                                    case 2:
                                        if target_language == 0:
                                            full_text = self.translator.translate_local(full_text_html, "en", "ru")
                                            character_answer_label.setText(full_text)
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
                                if translator != 0:
                                    self.worker = XTTSv2(text=full_text_tts, language="ru", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                                else:
                                    self.worker = XTTSv2(text=full_text_tts, language="en", character_name=character_name, ui=self.ui)
                                    self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                    self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                    self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                    self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                    self.worker.start()
                            case "Edge TTS":
                                await self.edge_tts_client.generate_speech_with_edge_tts(full_text_tts, character_name=character_name)
                            case "Kokoro":
                                self.worker = KokoroTTS(text=full_text_tts, character_name=character_name, ui=self.ui)
                                self.worker.started.connect(lambda: logger.info("Starting speech generation..."))
                                self.worker.finished.connect(lambda: logger.info("The generation is completed!"))
                                self.worker.error_occurred.connect(lambda msg: QMessageBox.critical(None, "Error", msg))
                                self.worker.audio_played.connect(lambda: logger.info("Audio has been played"))

                                self.worker.start()

            if conversation_method == "Character AI":
                await self.render_cai_messages(character_name)
            else:
                await self.render_messages(character_name)
        except Exception:
            error_message = traceback.format_exc()
            logger.error(f"Error processing the message: {error_message}")

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
        
        message_container = QHBoxLayout()
        message_container.setSpacing(5)

        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        if sow_system_status and current_sow_system_mode != "Nothing":
            message_container.setContentsMargins(10, 5, 10, 5)
        else:
            message_container.setContentsMargins(185, 5, 185, 5)

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
        message_frame.setLayout(message_container)
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

        if is_user:
            # User message styling
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #292929;
                    color: rgb(220, 220, 220);
                    border-top-left-radius: 15px;
                    border-bottom-left-radius: 15px;
                    border-bottom-right-radius: 0px;
                    border-top-right-radius: 15px;
                    padding: 12px;
                    font-size: 14px;
                    margin: 5px;
                    letter-spacing: 0.5px;
                }
            """)
            avatar_pixmap = QPixmap(self.user_avatar)
        else:
            # Character message styling
            message_label.setStyleSheet("""
                QLabel {
                    background-color: #222222;
                    color: rgb(220, 220, 220);
                    border-top-right-radius: 15px;
                    border-bottom-right-radius: 15px;
                    border-top-left-radius: 15px;
                    border-bottom-left-radius: 0px;
                    padding: 12px;
                    font-size: 14px;
                    margin: 5px;
                    letter-spacing: 0.5px;
                    text-align: justify;
                    white-space: pre-line;
                }
            """)
            avatar_pixmap = QPixmap(character_avatar)

        avatar_label = QLabel()
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
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        variant_counter_label.setFont(font)
        variant_counter_label.setStyleSheet("""
            QLabel {
                color: #D8DEE9;
                background-color: #2D2D2D;
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

        menu_button = QPushButton("···")
        menu_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #D8DEE9;
                border-radius: 15px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #383838;
                color: #ECEFF4;
                border-radius: 15px;
            }
        """)
        menu_button.setFixedSize(30, 30)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        menu_button.setFont(font)

        try:
            menu_button.clicked.disconnect()
        except TypeError:
            pass
        
        menu_button.clicked.connect(lambda _: self.show_message_menu(character_name, conversation_method, menu_button, is_user, message_id))
        menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        message_label.setGraphicsEffect(shadow)

        if is_user:
            message_container.addStretch()
            message_container.addWidget(message_label)
            message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(menu_button)
        else:
            message_container.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(left_button, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(message_label)
            message_container.addWidget(right_button, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(variant_counter_label, alignment=Qt.AlignmentFlag.AlignBottom)
            message_container.addWidget(menu_button)
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
            menu.setWindowOpacity(0.0)
            menu.exec(pos)

            anim_timer = QtCore.QTimer(menu)
            anim_timer.setInterval(20)
            opacity = 0.0
            def fadeIn():
                nonlocal opacity
                opacity += 0.05
                if opacity >= 1.0:
                    menu.setWindowOpacity(1.0)
                    anim_timer.stop()
                else:
                    menu.setWindowOpacity(opacity)

            anim_timer.timeout.connect(fadeIn)
            anim_timer.start()
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

    async def regenerate_message(self, conversation_method, character_name, message_id):
        """
        Regenerate message from character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        vrm_model_file = character_info.get("vrm_model_file", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")

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
            character_avatar_url = character_info.get("character_avatar")
            voice_name = character_info.get("voice_name")
            character_ai_voice_id = character_info.get("character_ai_voice_id")
        
        if message_id in self.messages:
            self.messages[message_id]["label"].setText("")
            self.messages[message_id]["text"] = ""

        configuration_data = self.configuration_characters.load_configuration()
        char_data = configuration_data["character_list"].get(character_name)
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

        personas_data = self.configuration_settings.get_user_data("personas")
        current_persona = char_data.get("selected_persona")
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
            await self.render_cai_messages(character_name)
        else:
            await self.first_render_messages(character_name)

        QtCore.QTimer.singleShot(0, lambda: self.ui.scrollArea_chat.verticalScrollBar().setValue(
            self.ui.scrollArea_chat.verticalScrollBar().maximum()
        ))
        
        configuration_data = self.configuration_characters.load_configuration()
        char_data = configuration_data["character_list"].get(character_name)
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
        
        msg_to_regenerate = chat_content.get(message_id)
        if not msg_to_regenerate:
            logger.error(f"Message {message_id} not found in chat_content.")
            return

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
            variants = last_user_message.get("variants", [])
            variant = next((v for v in variants if v["variant_id"] == current_variant_id), None)
            if variant:
                user_text_original = variant.get("text", "")

        user_text = user_text_original

        match translator:
            case 0:
                pass
            case 1:
                # Google Translate
                match translator_mode:
                    case 0:
                        if target_language == 0:
                            user_text = self.translator.translate(user_text_original, "google", 'en')
                        else:
                            pass
                    case 1:
                        if target_language == 0:
                            user_text = self.translator.translate(user_text_original, "google", "en")
                        else:
                            pass
                    case 2:
                        pass
            case 2:
                # Yandex Translate
                match translator_mode:
                    case 0:
                        if target_language == 0:
                            user_text = self.translator.translate(user_text_original, "yandex", 'en')
                        else:
                            pass
                    case 1:
                        if target_language == 0:
                            user_text = self.translator.translate(user_text_original, "yandex", "en")
                        else:
                            pass
                    case 2:
                        pass
            case 3:
                # Local translation
                match translator_mode:
                    case 0:
                        if target_language == 0:
                            user_text = self.translator.translate_local(user_text_original, "ru", "en")
                        else:
                            pass
                    case 1:
                        if target_language == 0:
                            user_text = self.translator.translate_local(user_text_original, "ru", "en")
                        else:
                            pass
                    case 2:
                        pass

        if user_text:
            match conversation_method:
                case "Character AI": 
                    if message_id in self.messages:
                        character_answer_container = self.messages[message_id]
                        character_answer_label = character_answer_container["label"]
                        character_answer_label.setText("")

                    full_text = ""
                    turn_id = chat_content[message_id]["turn_id"]

                    async for message in self.character_ai_client.regenerate_message(character_id, chat_id, turn_id):
                        text = message.get_primary_candidate().text
                        
                        if text != full_text:
                            full_text = text
                            original_text = text
                            full_text_html = self.markdown_to_html(full_text)
                            character_answer_label.setText(full_text_html)
                            await asyncio.sleep(0.05)
                            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                    match sow_system_status:
                        case False:
                            pass
                        case True:
                            match current_sow_system_mode:
                                case "Nothing":
                                    pass
                                case "Expressions Images" | "Live2D Model" | "VRM":
                                    current_emotion = await self.detect_emotion(character_name, original_text)

                    match translator:
                        case 0:
                            pass
                        case 1:
                            # Google Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 2:
                            # Yandex Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 3:
                            # Local translation
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                    
                    await self.character_ai_client.fetch_chat(
                        chat_id, character_name, character_id, character_avatar_url, character_title,
                        character_description, character_personality, first_message, current_text_to_speech,
                        voice_name, character_ai_voice_id, elevenlabs_voice_id, voice_type, rvc_enabled,
                        rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                        vrm_model_file, conversation_method, current_emotion
                    )

                case "Mistral AI":
                    configuration_data = self.configuration_characters.load_configuration()
                    character_data = configuration_data["character_list"].get(character_name)
                    character_information = character_data["character_information"]
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

                    if message_id in self.messages:
                        character_answer_container = self.messages[message_id]
                        character_answer_label = character_answer_container["label"]
                        character_answer_label.setText("")

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

                    match sow_system_status:
                        case False:
                            pass
                        case True:
                            match current_sow_system_mode:
                                case "Nothing":
                                    pass
                                case "Expressions Images" | "Live2D Model" | "VRM":
                                    asyncio.create_task(self.detect_emotion(character_name, full_text))

                    self.configuration_characters.regenerate_message_in_config(character_name, message_id, full_text)
                    await asyncio.sleep(0.5)

                    match translator:
                        case 0:
                            pass
                        case 1:
                            # Google Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 2:
                            # Yandex Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 3:
                            # Local translation
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                
                case "Local LLM" | "Open AI" | "OpenRouter":
                    configuration_data = self.configuration_characters.load_configuration()
                    character_data = configuration_data["character_list"].get(character_name)
                    character_information = character_data["character_information"]
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

                    if message_id in self.messages:
                        character_answer_container = self.messages[message_id]
                        character_answer_label = character_answer_container["label"]
                        character_answer_label.setText("")

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
                                self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())
                    elif conversation_method in ["Open AI", "OpenRouter"]:
                        async for chunk in self.open_ai_client.send_message(conversation_method, context_messages, user_text, character_name, user_name, user_description):
                            if chunk:
                                if conversation_method == "OpenRouter":
                                    corrected_chunk = chunk.encode('latin1').decode('utf-8') if isinstance(chunk, str) else chunk
                                    full_text += corrected_chunk
                                else:
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

                    match sow_system_status:
                        case False:
                            pass
                        case True:
                            match current_sow_system_mode:
                                case "Nothing":
                                    pass
                                case "Expressions Images" | "Live2D Model" | "VRM":
                                    asyncio.create_task(self.detect_emotion(character_name, full_text)) # Detect and display the character's emotion

                    self.configuration_characters.regenerate_message_in_config(character_name, message_id, full_text)
                    await asyncio.sleep(0.5)

                    match translator:
                        case 0:
                            pass
                        case 1:
                            # Google Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "google", 'ru')
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 2:
                            # Yandex Translate
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate(full_text_html, "yandex", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                        case 3:
                            # Local translation
                            match translator_mode:
                                case 0:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass
                                case 1:
                                    pass
                                case 2:
                                    if target_language == 0:
                                        full_text = self.translator.translate_local(full_text_html, "en", "ru")
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
                                        character_answer_label.setText(full_text)
                                    else:
                                        pass

            if conversation_method == "Character AI":
                await self.first_render_cai_messages(character_name)
            else:
                await self.first_render_messages(character_name)

    def save_changes(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Saves changes to the configuration file for the specified character.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_list = configuration_data["character_list"]
        
        if character_name not in character_list:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("character_edit_saved_error", "Saving Error"))
            message_box_information.setText(self.translations.get("character_edit_saved_error_2", "Character was not found in the configuration."))
            message_box_information.exec()
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

        message_box_information = QMessageBox()
        message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        message_box_information.setWindowTitle(self.translations.get("character_edit_saved", "Saved"))
        message_box_information.setText(self.translations.get("character_edit_saved_2", "The changes were saved successfully!"))
        message_box_information.exec()
        asyncio.create_task(self.open_chat(new_name))
        dialog.close()

    async def start_new_dialog(self, dialog, conversation_method, character_name, name_edit, description_edit, personality_edit, scenario_edit, first_message_edit, example_messages_edit, alternate_greetings_edit, creator_notes_edit):
        """
        Starts a new dialogue with the character.
        """
        reply = QMessageBox.question(
            dialog, 
            self.translations.get("character_edit_start_new_dialogue", "Start new dialogue"), 
            self.translations.get("character_edit_start_new_dialogue_sure", "Are you sure you want to start a new dialogue? The previous dialogue will be deleted."), 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return

        if conversation_method != "Character AI":
            chat_name, ok = QInputDialog.getText(
                dialog,
                self.translations.get("new_chat_title", "New Chat"),
                self.translations.get("new_chat_prompt", "Enter chat name:")
            )

            if not ok or not chat_name.strip():
                chat_name = self.translations.get("default_chat_name", "Default Chat")

        if reply == QMessageBox.StandardButton.Yes:
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

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle("New Chat")
            message_box_information.setText(self.translations.get("character_edit_start_new_dialogue_success", "A new dialogue has been successfully started!"))
            message_box_information.exec()
        
            dialog.close()
            await self.set_main_tab()
            await self.close_chat()
            self.main_window.updateGeometry()
        else:
            dialog.close()

    def clean_text_for_tts(self, full_text):
        cleaned_text = re.sub(r"[^a-zA-Zа-яА-Я0-9\s.,!?]", "", full_text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text

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
                if translator == 1:
                    if translator_mode in (0, 2):
                        if target_language == 0:
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate(text, "google", "ru")
                elif translator == 2:  # Yandex Translate
                    if translator_mode in (0, 2):  # Translate all messages or only model messages
                        if target_language == 0:  # Target language is Russian
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate(text, "yandex", "ru")
                elif translator == 3:  # MarianMT (local translator)
                    if translator_mode in (0, 2):  # Translate all messages or only model messages
                        if target_language == 0:  # Target language is Russian
                            if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                text = self.translator.translate_local(text, "en", "ru")
            
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
            
            await self.add_header_image(text)

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
                user_name = self.configuration_settings.get_user_data("user_name") or "User"

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
                    if translator == 1:  # Google Translate
                        if translator_mode in (0, 2):  # Translate all messages or only model messages
                            if target_language == 0:  # Target language is Russian
                                if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                    text = self.translator.translate(text, "google", "ru")
                    elif translator == 2:  # Yandex Translate
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
        self.chat_container.update()
        self.ui.scrollArea_chat.update()
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
                        if translator == 1:  # Google Translate
                            if translator_mode in (0, 2):  # Translate all messages or only model messages
                                if target_language == 0:  # Target language is Russian
                                    if not is_user or translator_mode == 0:  # Translate user messages or all messages
                                        text = self.translator.translate(text, "google", "ru")
                        elif translator == 2:  # Yandex Translate
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
        
        # FOR 2.3
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
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
            message_box_information.setWindowTitle(self.translations.get("voice_error_title", "Voice Error"))
            message_box_information.setText(self.translations.get("voice_error_body", "Assign a character's voice before you go on to the call."))
            message_box_information.exec()
        else:
            personas_data = self.configuration_settings.get_user_data("personas")
            configuration_data = self.configuration_characters.load_configuration()
            character_info = configuration_data["character_list"][character_name]
            current_persona = character_info.get("selected_persona")

            if current_persona == "None" or current_persona is None:
                self.user_avatar = "app/gui/icons/person.png"
            else:
                if current_persona not in personas_data:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("persona_error_title", "Change persona"))
                    message_box_information.setText(self.translations.get("persona_error_body", "A non-existent persona has been selected, please change it."))
                    message_box_information.exec()
                    return
                else:
                    self.user_avatar = personas_data[current_persona].get("user_avatar", "")
                    
                    if not self.user_avatar or not os.path.exists(self.user_avatar):
                        self.user_avatar = "app/gui/icons/person.png"
            
            if gui_mode == 1:
                if current_sow_system_mode in ("Nothing", "Expressions Images"):
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
                    message_box_information.setWindowTitle(self.translations.get("no_gui_error_title", "Incorrect type of expression"))
                    message_box_information.setText(self.translations.get("no_gui_error_body", "Select Live2D or VRM to use the non-interface mode."))
                    message_box_information.exec()
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

        # Load output device settings
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
    
    def calculate_content_height(self):
        doc = self.document().clone()
        doc.setTextWidth(self.viewport().width())
        height = doc.size().height()

        padding_vertical = 7 + 6
        return int(height + padding_vertical)

class CharacterCardList(QtWidgets.QFrame):
    def __init__(self, character_name, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(210, 270)

        self.character_name = character_name
        self.open_chat = method
        self._background_color = QColor(35, 35, 35)

        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow_effect)

        self.animation = QPropertyAnimation(self.shadow_effect, b"offset")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.color_animation = QtCore.QVariantAnimation(self)
        self.color_animation.setDuration(250)
        self.color_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.color_animation.valueChanged.connect(self.update_background_color)

        self.setStyleSheet("""
            QFrame {
                background-color: rgb(35, 35, 35);
                border: none;
                border-radius: 15px; 
            }
        """)

        self.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))

    def enterEvent(self, event):
        self.animation.setStartValue(QPointF(0, 0))
        self.animation.setEndValue(QPointF(5, 5))
        self.animation.start()
        
        self.color_animation.setStartValue(self._background_color)
        self.color_animation.setEndValue(QColor(30, 30, 30)) # Second color
        self.color_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setStartValue(QPointF(5, 5))
        self.animation.setEndValue(QPointF(0, 0))
        self.animation.start()
        
        self.color_animation.setStartValue(self._background_color)
        self.color_animation.setEndValue(QColor(35, 35, 35)) # First color
        self.color_animation.start()
        super().leaveEvent(event)
    
    def update_background_color(self, color):
        self._background_color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color.name()};
                border: none;
                border-radius: 15px;
            }}
        """)
    
    def get_background_color(self):
        return self._background_color

    def set_background_color(self, color):
        self._background_color = color

    background_color = QtCore.pyqtProperty(QColor, get_background_color, set_background_color)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            asyncio.create_task(self.open_chat(self.character_name)) 
        super().mousePressEvent(event)

class CharacterCardCharactersGateway(QtWidgets.QFrame):
    def __init__(self, conversation_method, character_name, character_avatar, character_title, character_description, character_personality, scenario, first_message, example_messages, alternate_greetings, method, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 270)

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

        self._background_color = QColor(35, 35, 35)

        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow_effect)

        self.animation = QPropertyAnimation(self.shadow_effect, b"offset")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.color_animation = QtCore.QVariantAnimation(self)
        self.color_animation.setDuration(250)
        self.color_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.color_animation.valueChanged.connect(self.update_background_color)

        self.setStyleSheet("""
            QFrame {
                background-color: rgb(35, 35, 35);
                border: none;
                border-radius: 15px; 
            }
        """)

        self.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))

    def enterEvent(self, event):
        self.animation.setStartValue(QPointF(0, 0))
        self.animation.setEndValue(QPointF(5, 5))
        self.animation.start()
        
        self.color_animation.setStartValue(self._background_color)
        self.color_animation.setEndValue(QColor(30, 30, 30)) # Second color
        self.color_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setStartValue(QPointF(5, 5))
        self.animation.setEndValue(QPointF(0, 0))
        self.animation.start()
        
        self.color_animation.setStartValue(self._background_color)
        self.color_animation.setEndValue(QColor(35, 35, 35)) # First color
        self.color_animation.start()
        super().leaveEvent(event)
    
    def update_background_color(self, color):
        self._background_color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color.name()};
                border: none;
                border-radius: 15px;
            }}
        """)
    
    def get_background_color(self):
        return self._background_color

    def set_background_color(self, color):
        self._background_color = color

    background_color = QtCore.pyqtProperty(QColor, get_background_color, set_background_color)

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
    def __init__(self, model_name, file_size_bytes, full_path, refresh_method, launch_server_method, stop_server_method, ui, parent=None):
        super().__init__(parent)
        self.configuration_settings = configuration.ConfigurationSettings()
        
        self.translations = {}
        selected_language = self.configuration_settings.get_main_setting("program_language")
        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")

        self.model_name = model_name or "unknown_model"
        self.full_path = full_path or ""
        self.refresh_method = refresh_method
        self.launch_server_method = launch_server_method
        self.stop_server_method = stop_server_method
        self.ui = ui
        self.parent_widget = parent

        self.setStyleSheet("border: 1px solid rgb(50, 50, 55);")
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background: transparent; border: none;")
        self.icon_label.setFixedWidth(20)
        
        layout.addWidget(self.icon_label)

        self.name_label = QLabel(model_name)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.name_label.setFont(font)
        self.name_label.setStyleSheet("color: rgb(227, 227, 227); font-weight: bold; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(self.name_label)

        size_str = self.human_readable_size(file_size_bytes)
        self.size_label = QLabel(f"({size_str})")
        self.size_label.setStyleSheet("color: #999999; font-size: 11px; background: transparent; border: none;")
        layout.addWidget(self.size_label, stretch=1)

        self.btn_set_default = QPushButton(self.translations.get("button_set_default", " Set as default"))
        self.btn_set_default.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_set_default.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        if self.ui.pushButton_turn_off_llm.isVisible():
            self.btn_launch_server = QPushButton(self.translations.get("button_disable_server", "Unload model"))
        else:
            self.btn_launch_server = QPushButton(self.translations.get("button_launch_server", "Load model"))
        self.btn_launch_server.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_launch_server.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_delete = QPushButton(self.translations.get("button_delete_model", "Delete model"))
        self.btn_delete.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_delete.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(7)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.btn_set_default.setFont(font)
        self.btn_launch_server.setFont(font)
        self.btn_delete.setFont(font)

        self.btn_set_default.setFixedSize(160, 30)
        self.btn_launch_server.setFixedSize(160, 30)
        self.btn_delete.setFixedSize(90, 30)

        self.btn_set_default.setObjectName("btn_set_default")
        self.btn_launch_server.setObjectName("btn_launch_server")
        self.btn_delete.setObjectName("btn_delete")

        icon_launch = QtGui.QIcon()
        icon_launch.addPixmap(QtGui.QPixmap("app/gui/icons/default_model.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_set_default.setIconSize(QtCore.QSize(15, 15))
        self.btn_set_default.setIcon(icon_launch)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 3)
        self.btn_set_default.setGraphicsEffect(shadow)
        self.btn_launch_server.setGraphicsEffect(shadow)
        self.btn_delete.setGraphicsEffect(shadow)

        self.btn_set_default.setStyleSheet("""
            QPushButton {
                background-color: #2E2E2E;
                color: rgb(227, 227, 227);
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid #444444;
            }

            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #3A3A3A, stop: 1 #2F2F2F);
                border: 1px solid #666666;
            }

            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #2A2A2A, stop: 1 #444444);
                border: 1px solid #888888;
            }

            QPushButton:disabled {
                background-color: #222222;
                color: #777777;
                border: 1px solid #333333;
            }
        """)

        self.btn_launch_server.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: rgb(227, 227, 227);
                border-radius: 6px;
                font-size: 12px;
                border: 1px solid #1B5E20;
            }

            QPushButton:hover {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #43A047, stop: 1 #2E7D32);
                border: 1px solid #4CAF50;
            }

            QPushButton:pressed {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                                stop: 0 #1B5E20, stop: 1 #66BB6A);
                border: 1px solid #81C784;
            }

            QPushButton:disabled {
                background-color: #A5D6A7;
                color: #888888;
                border: 1px solid #90A4AE;
            }
        """)

        self.btn_delete.setStyleSheet("""
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

        current_default_model = self.configuration_settings.get_main_setting("local_llm")
        filename_with_ext = os.path.basename(current_default_model)
        current_default_model = os.path.splitext(filename_with_ext)[0]
        if current_default_model == model_name:
            icon_path = "app/gui/icons/star.png"
            pixmap = QPixmap(icon_path).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pixmap)
            self.name_label.setText(f"{model_name}")
            self.name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #FFD700; background: transparent; border: none;")
            layout.addWidget(self.btn_launch_server, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        else:
            layout.addWidget(self.btn_set_default, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.btn_delete, alignment=QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)

        try:
            self.btn_set_default.clicked.disconnect()
            self.btn_delete.clicked.disconnect()
            self.btn_launch_server.disconnect()
        except TypeError:
            pass

        self.btn_set_default.clicked.connect(self.on_set_default_clicked)
        if self.ui.pushButton_turn_off_llm.isVisible():
            self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
        else:
            self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)
        self.btn_delete.clicked.connect(self.on_delete_clicked)

        self.setLayout(layout)
    
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
        self.launch_server_method()

        try:
            self.btn_launch_server.disconnect()
        except TypeError:
            pass

        self.btn_launch_server.clicked.connect(self.on_unload_model_clicked)
    
    def on_unload_model_clicked(self):
        self.btn_launch_server.setText(self.translations.get("button_launch_server", "Load model"))
        self.stop_server_method()

        try:
            self.btn_launch_server.disconnect()
        except TypeError:
            pass

        self.btn_launch_server.clicked.connect(self.on_launch_server_clicked)

    def on_delete_clicked(self):
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        msg_box.setWindowTitle(self.translations.get("delete_model", "Delete LLM"))
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: rgb(27, 27, 27);
                color: rgb(227, 227, 227);
            }
            QLabel {
                color: rgb(227, 227, 227);
            }
        """)
        
        model_name = self.name_label.text()
        first_text = self.translations.get("model_widget_delete", "Do you want to delete the model:")
        second_text = self.translations.get("model_widget_delete_2", "This action cannot be canceled.")
        message_text = f"""
            <html>
                <head>
                    <style>
                        body {{
                            background-color: #2b2b2b;
                            font-family: "Segoe UI", Arial, sans-serif;
                            font-size: 14px;
                            color: rgb(227, 227, 227);
                        }}
                        h1 {{
                            font-size: 16px;
                            margin-bottom: 10px;
                        }}
                        .model-name {{
                            color: #FF6347;
                            font-weight: bold;
                        }}
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
                error_box.setStyleSheet("""
                    QMessageBox {
                        background-color: rgb(27, 27, 27);
                        color: rgb(227, 227, 227);
                    }
                    QLabel {
                        color: rgb(227, 227, 227);
                    }
                """)
                error_box.setIcon(QMessageBox.Icon.Critical)
                error_box.exec()
        
    def enterEvent(self, event):
        self.setStyleSheet("""
            background-color: #121212;
            border: 1px solid rgb(60, 60, 65);
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("""
            background: transparent;
            border: 1px solid rgb(50, 50, 55);
        """)
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
                            background-color: qlineargradient(
                                spread: pad,
                                x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #2f2f2f,
                                stop: 1 #1e1e1e
                            );
                            color: rgb(227, 227, 227);
                            border: 2px solid #3A3A3A;
                            border-radius: 5px;
                            padding: 2px;
                        }

                        QPushButton:hover {
                            background-color: qlineargradient(
                                spread: pad,
                                x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #343434,
                                stop: 1 #222222
                            );
                            border: 2px solid #666666;
                            border-top: 2px solid #777777;
                            border-bottom: 2px solid #555555;
                        }

                        QPushButton:pressed {
                            background-color: qlineargradient(
                                spread: pad,
                                x1: 0, y1: 0, x2: 0, y2: 1,
                                stop: 0 #4a4a4a,
                                stop: 1 #3a3a3a
                            );
                            border: 2px solid #888888;
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

class BackgroundChangerWindow(QDialog):
    def __init__(self, ui=None, translation=None, parent=None):
        super().__init__(parent)
        self.translations = translation

        self.setWindowTitle(self.translations.get("background_changer_title", "Chat Background"))
        self.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        self.setFixedSize(900, 500)

        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()

        self.parent = parent
        self.ui = ui

        layout = QVBoxLayout(self)

        title = QLabel(self.translations.get("background_changer_label_1", "Choose a background for the chat"))
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea {\n"
"                border: none;\n"
"                background-color: rgb(27,27,27);\n"
"}\n"
"\n"
"QScrollBar:vertical {\n"
"                background-color: #2b2b2b;\n"
"                width: 12px;\n"
"                margin: 15px 0px 15px 0px;\n"
"                border-radius: 5px;\n"
"}\n"
"\n"
"        QScrollBar::handle:vertical {\n"
"                background-color: #383838;\n"
"                min-height: 30px;\n"
"                border-radius: 3px;\n"
"                margin: 2px;\n"
"        }\n"
"\n"
"        QScrollBar::handle:vertical:hover {\n"
"                background-color: #454545;\n"
"        }\n"
"\n"
"        QScrollBar::handle:vertical:pressed {\n"
"                background-color: #424242;\n"
"        }\n"
"\n"
"        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"                border: none;\n"
"                background: none;\n"
"        }\n"
"\n"
"        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"                background: none;\n"
"        }")

        container = QtWidgets.QWidget()
        grid_layout = QtWidgets.QGridLayout(container)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(10, 10, 10, 10)

        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)

        images_directory = "assets/backgrounds"
        if not os.path.exists(images_directory):
            QMessageBox.critical(self, "Error", f"Folder '{images_directory}' not found.")
            return

        image_files = [f for f in os.listdir(images_directory) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

        black_button = QPushButton(self.translations.get("background_changer_default_btn", "Default"))
        black_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        black_button.setFixedSize(200, 150)
        black_button.setStyleSheet("""
            QPushButton {
                background-color: black;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                border: 2px solid white;
            }
        """)
        black_button.clicked.connect(lambda: self.select_background("Default"))
        grid_layout.addWidget(black_button, 0, 0)

        row, col = 0, 1
        max_cols = 4
        for i, img_file in enumerate(image_files):
            path = os.path.join(images_directory, img_file)
            path = path.replace("\\", "/")
            button = QPushButton()
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setFixedSize(200, 150)
            button.setStyleSheet(f"""
                QPushButton {{
                    border-image: url({path});
                    border-radius: 10px;
                    text-align: bottom;
                    padding-bottom: 10px;
                    font-size: 12px;
                    color: white;
                    background-color: rgba(0, 0, 0, 100);
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
            """)

            font = QtGui.QFont()
            font.setFamily("Inter Tight SemiBold")
            font.setPointSize(12)
            font.setBold(True)
            font.setItalic(False)
            font.setWeight(75)
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            button.setFont(font)
            button.setText(img_file)
            button.clicked.connect(lambda _, p=path: self.select_background(p))

            grid_layout.addWidget(button, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def select_background(self, image_path):
        if image_path:
            self.ui.scrollArea_chat.setStyleSheet(f"""
                QScrollArea {{
                    background-color: rgb(27, 27, 27);
                    border: none;
                    padding: 5px;
                    margin: 5px;
                    border-image: url({image_path});
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
                    background-color: rgb(27,27,27);
                    border: none;
                    padding: 5px;
                    margin-top: 5px;
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

        self.configuration_settings.update_main_setting("chat_background_image", image_path)

        self.close()
