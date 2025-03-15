import re
import os
import json
import base64
import asyncio
import traceback
import numpy as np
import OpenGL.GL as gl
import onnxruntime as ort
import live2d.v3 as live2d

from PIL import Image, PngImagePlugin
from transformers import AutoTokenizer
from multiprocessing import freeze_support
from characterai import authUser, sendCode

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QUrl, Qt, QTimerEvent, QTranslator
from PyQt6.QtGui import QDesktopServices, QPixmap, QFont, QPainter, QAction
from PyQt6.QtWidgets import (
    QApplication, QInputDialog, QLabel, QMessageBox, QPushButton,
    QWidget, QHBoxLayout, QListWidgetItem, QDialog, QVBoxLayout,
    QRadioButton, QButtonGroup, QStackedWidget, QFileDialog,
    QScroller, QAbstractItemView, QScrollerProperties, QGraphicsDropShadowEffect,
    QFrame, QMenu, QTextEdit, QLineEdit
)

from api_clients.local_ai_client import LocalAI
from api_clients.mistral_ai_client import MistralAI
from api_clients.character_ai_client import CharacterAI
from utils.translator import Translator
from utils.character_cards import CharactersCard
from utils.text_to_speech import ElevenLabs, XTTSv2
from utils.sow_system_interface_signals import Soul_Of_Waifu_System
from configuration import configuration
from resources.data.sowSystem import sow_System

class InterfaceSignals():
    """
    A class that contains the code for all interface elements to work.
    """
    def __init__(self, ui, main_window):
        super(InterfaceSignals, self).__init__()
        self.ui = ui
        self.messages = {}
        self.main_window = main_window
        self.model = None
        self.session = None
        self.tokenizer = None
        
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

        self.live2d_widget = None
        self.expression_widget = None
        self.stackedWidget_expressions = None
        self.original_window_size = QtCore.QSize(1296, 807)
        self.original_bottom_bar_geometry = QtCore.QRect(5, 756, 1280, 16)
        
        self.translator = Translator()
        self.tr = QtCore.QCoreApplication.tr
        
        self.configuration_api = configuration.ConfigurationAPI()
        self.configuration_settings = configuration.ConfigurationSettings()
        self.configuration_characters = configuration.ConfigurationCharacters()
        
        self.local_ai_client = LocalAI()
        self.mistral_ai_client = MistralAI()
        self.character_ai_client = CharacterAI()
        
        self.xttsv2_client = XTTSv2()
        self.eleven_labs_client = ElevenLabs()

        self.character_card_client = CharactersCard()
        freeze_support()

    ### SETUP BUTTONS ==================================================================================
    def set_about_program_button(self):
        """
        Shows a message with information about the Soul of Waifu program.
        """
        description = self.tr(
            "Soul of Waifu is an advanced application designed to bring your AI-driven character experiences to life. By integrating various APIs from platforms providing artificial intelligence-based character communication and local LLMs, Soul of Waifu enables you to interact with your favorite characters like never before. Immerse yourself in a world where characters come alive with stunning visuals, Live2D models, and dynamic Text-To-Speech capabilities."
        )
        sub_description = self.tr(
            "Encounter bugs, have suggestions, or just want to share your ideas? Join the vibrant community on our official <a href='https://discord.gg/6vFtQGVfxM'>Discord server</a>. Your feedback shapes the future of Soul of Waifu. Together we make a place where dreams become reality!"
        )
        github_site = "https://github.com/jofizcd"

        mbox_about = QMessageBox()
        mbox_about.setWindowTitle(self.tr("About Soul of Waifu"))
        mbox_about.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        
        mbox_about.setText(
        f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: "Segoe UI", Arial, sans-serif;
                        font-size: 12pt;
                        color: #e0e0e0;
                        background-color: #2b2b2b;
                    }}
                    p {{
                        margin: 5px 0;
                        text-align: justify;
                        line-height: 1.3;
                    }}
                    a {{
                        color: #ffa726;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    .title {{
                        font-size: 16pt;
                        font-weight: bold;
                        color: #ffa726;
                        text-align: justify;
                        margin-bottom: 5px;
                    }}
                    .subtitle {{
                        margin-bottom: 5px;
                        margin-top: 20px;
                        text-align: justify;
                    }}
                    .footer {{
                        display: flex;
                        text-align: right;
                        justify-content: space-between;
                        font-size: 10pt;
                        color: #cccccc;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <p class="title">Soul of Waifu v2.0.0</p>
                <p align="justify">{description}</p>
                <p>
                <p class="subtitle" align="justify">{sub_description}</p>
                <div class="footer">
                    <div style="float: right; text-align: right"><i>Version 2.0.0</i></div>
                    <i>Developed by <a href="{github_site}">jofizcd</a></i>
                </div>
            </body>
        </html>
        """
        )
        
        mbox_about.exec()

    def on_pushButton_main_clicked(self):
        asyncio.create_task(self.set_main_tab())

    def set_get_token_from_character_ai_button(self):
        """
        Receives the API token from Character AI by email.
        Handles user input, validation, and API interactions.
        """
        email_regex = r"^[^@]+@[^@]+\.[^@]+$"

        def show_message_box(title, text):
            mbox = QMessageBox()
            mbox.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            mbox.setWindowTitle(self.tr(title))
            mbox.setText(text)
            mbox.exec()

        email_address, ok_pressed = QInputDialog.getText(
            None,
            self.tr("Get Token from Character AI"),
            self.tr("Enter your email address:")
        )
        if not ok_pressed or not email_address.strip():
            return

        email_address = email_address.strip()
        if not re.match(email_regex, email_address):
            show_message_box('Error', self.tr("Invalid email format. Please enter a valid email address."))
            return

        try:
            sendCode(email_address)
        except Exception as e:
            show_message_box(
                'Error', self.tr("Failed to send verification code.")
                )
            return

        link, ok_pressed = QInputDialog.getText(
            None,
            self.tr('Soul of Waifu - Get Token'),
            self.tr('Enter the verification link from the email:')
        )

        if not ok_pressed or not link.strip():
            show_message_box('Error', self.tr('Verification link is required.'))
            return

        try:
            user_token = authUser(link.strip(), email_address)
        except Exception as e:
            show_message_box('Error', self.tr(f"Failed to authenticate user."))
            return

        try:
            api_token_data = self.configuration_api.load_configuration()
            api_token_data["CHARACTER_AI_API_TOKEN"] = user_token
            self.configuration_api.save_configuration_edit(api_token_data)

            combined_message = (
                self.tr("Your API token: ") + user_token
            )
            show_message_box(self.tr('Soul of Waifu - Get API Token'), combined_message)
        except Exception as e:
            show_message_box('Error', self.tr("Failed to save API token."))

    def on_pushButton_options_clicked(self):
        self.ui.pushButton_options.setChecked(True)
        self.ui.stackedWidget.setCurrentIndex(5)

    def on_youtube(self):
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/@jofizcd"))

    def on_discord(self):
        QDesktopServices.openUrl(QUrl("https://discord.gg/6vFtQGVfxM"))

    def on_github(self):
        QDesktopServices.openUrl(QUrl("https://github.com/jofizcd/Soul-of-Waifu"))

    def set_faq_button(self):
        """
        Shows the FAQ of the program.
        """
        faq_title = self.tr("Frequently Asked Questions")
        faq_content = [
            self.tr(
                "<b>Q: What is Soul of Waifu?</b><br>"
                "A: This program gives you the opportunity to communicate with your character, bringing him to life with the help of large language models. Settings for every taste are available here, have fun!"
            ),
            self.tr(
                "<b>Q: How can I add new characters?</b><br>"
                "A: You can add a character simply by clicking on the “Create Character” button and selecting the desired option. When using Mistral AI and Local LLM, you can either fully customize your character's information or import a character card. You can also go to the “Characters Gateway” and add a character there without leaving the program."
            ),
            self.tr(
                "<b>Q: Where can I report issues?</b><br>"
                "A: If you notice any bug, you can tell us about it on our discord server, which hosts people who also use the program. You can also suggest your ideas for improving the program."
            ),
        ]

        mbox_faq = QMessageBox()
        mbox_faq.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        mbox_faq.setWindowTitle(faq_title)

        faq_text = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: "Segoe UI", Arial, sans-serif;
                        font-size: 14px;
                        color: #ffa726;
                        text-align: justify;
                        margin-bottom: 5px;
                    }}
                    p {{
                        text-align: justify;
                        line-height: 1.6;
                    }}
                    b {{
                        color: #2c7ef8;
                    }}
                    a {{
                        color: #2c7ef8;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    i {{
                        color: #666666;
                    }}
                </style>
            </head>
            <body>
                <h2>{faq_title}</h2>
        """
        for item in faq_content:
            faq_text += f"<p>{item}</p>"

        faq_text += f"""
                <p><i>More details on <a href='https://github.com/jofizcd' target='_blank'>GitHub</a></i></p>
            </body>
        </html>
        """

        mbox_faq.setTextFormat(QtCore.Qt.TextFormat.RichText)
        mbox_faq.setText(faq_text)
        mbox_faq.exec()

    def add_character_sync(self):
        task = asyncio.create_task(self.add_character())
        task.add_done_callback(self.on_add_character_done)

    def on_add_character_done(self, task):
        """
        Handles the result of adding a character to the system.
        """
        result = task.result()

        def show_message_box(title, message_text, is_success=True):
            message_box = QMessageBox()
            message_box.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box.setWindowTitle(title)
            message_box.setText(message_text)
            message_box.exec()

        if result:
            character_name = result
            first_text = self.tr("was successfully added!")
            second_text = self.tr("You can now interact with the character in your character list.")
            success_message = f"""
                <html>
                    <head>
                        <style>
                            h1 {{
                                color: #4CAF50;
                                font-family: Arial, sans-serif;
                                font-size: 20px;
                            }}
                            p {{
                                color: #555;
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                font-size: 14px;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1><span style="color:#1E90FF;">{character_name}</span> {first_text}</h1>
                        <p>{second_text}</p>
                    </body>
                </html>
            """
            show_message_box(self.tr("Character Information"), success_message, is_success=True)
        else:
            first_text = self.tr("There was an error while adding the character.")
            second_text = self.tr("Please try again.")
            error_message = f"""
                <html>
                    <head>
                        <style>
                            h1 {{
                                color: #FF6347;
                                font-family: Arial, sans-serif;
                                font-size: 20px;
                            }}
                            p {{
                                color: #555;
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
        Adds a character to the list of characters based on the selected conversation method.
        """
        conversation_method = self.configuration_settings.get_main_setting("conversation_method")
        character_id = self.ui.character_id_lineEdit.text()
        
        async def handle_character_ai():
            try:
                character_name = await self.character_ai_client.create_character(character_id)
                self.ui.character_id_lineEdit.clear()
                return character_name
            except Exception as e:
                print(f"Error occurred while adding character: {e}")
                return None

        def handle_generic_ai(method_name):
            try:
                character_name = self.ui.lineEdit_character_name_building.text()
                character_avatar_directory = self.configuration_settings.get_user_data("current_character_image")
                character_description = self.ui.textEdit_character_description_building.toPlainText()
                character_personality = self.ui.textEdit_character_personality_building.toPlainText()
                character_first_message = self.ui.textEdit_first_message_building.toPlainText()

                self.configuration_characters.save_character_card(
                    character_name=character_name,
                    character_title=None,
                    character_avatar=character_avatar_directory,
                    character_description=character_description,
                    character_personality=character_personality,
                    first_message=character_first_message,
                    elevenlabs_voice_id=None,
                    xttsv2_voice_type=None,
                    xttsv2_rvc_enabled=False,
                    xttsv2_rvc_file=None,
                    expression_images_folder=None,
                    live2d_model_folder=None,
                    conversation_method=method_name
                )

                clear_input_fields()
                reset_image_button_icon()

                return character_name
            except Exception as e:
                print(f"Error occurred while adding character ({method_name}): {e}")
                return None

        def clear_input_fields():
            self.ui.lineEdit_character_name_building.clear()
            self.ui.textEdit_character_description_building.clear()
            self.ui.textEdit_character_personality_building.clear()
            self.ui.textEdit_first_message_building.clear()
            self.configuration_settings.update_user_data("current_character_image", None)

        def reset_image_button_icon():
            icon_import = QtGui.QIcon()
            icon_import.addPixmap(QtGui.QPixmap(":/sowInterface/addImage.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            self.ui.pushButton_import_character_image.setIcon(icon_import)
            self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))

        match conversation_method:
            case "Character AI":
                return await handle_character_ai()
            case "Mistral AI":
                return handle_generic_ai("Mistral AI")
            case "Local LLM":
                return handle_generic_ai("Local LLM")

    def on_stacked_widget_changed(self, index):
        """
        The slot that is called when the current widget is changed in QStackedWidget.
        """
        if self.original_window_size is not None:
            current_size = self.main_window.size()
            if current_size.width() > self.original_window_size.width() or current_size.height() > self.original_window_size.height():
                if index != 6:
                    asyncio.create_task(self.close_chat())
                    self.main_window.updateGeometry()

    async def close_chat(self):
        """
        Closes the current chat and resets the interface to its original state.
        """
        if self.original_window_size is not None:
            self.main_window.setFixedSize(self.original_window_size)
            self.main_window.adjustSize()
            self.center()

        if self.original_bottom_bar_geometry is not None:
            self.ui.bottom_bar.setGeometry(self.original_bottom_bar_geometry)

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
        character_list = self.ui.ListWidget_character_list
        character_list.clear()

        if character_data.get("character_list") and len(character_data["character_list"]) > 0:
            user_name = self.configuration_settings.get_user_data("user_name")
            user_avatar = self.configuration_settings.get_user_data("user_avatar")

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
                pixmap = QPixmap(":/sowInterface/person.png")
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

            welcome_message = self.tr("Welcome to Soul of Waifu, ")
            if user_name:
                self.ui.welcome_label_2.setText(f"{welcome_message}{user_name}")
            else:
                self.ui.welcome_label_2.setText(f"{welcome_message}User")

            characters = character_data.get('character_list', {})
            for character_name, data in characters.items():
                conversation_method = data.get("conversation_method")
                match conversation_method:
                    case "Character AI":
                        conversation_method_image = os.path.abspath(os.path.join(os.path.dirname(__file__), "../icons/characterai.png"))
                        character_avatar_url = data.get("character_avatar", None)
                        character_title = data.get("character_title")
                        character_avatar = await self.character_ai_client.load_image(character_avatar_url)
                    case "Mistral AI":
                        conversation_method_image = os.path.abspath(os.path.join(os.path.dirname(__file__), "../icons/mistralai.png"))
                        character_avatar_url = data.get("character_avatar", None)
                        character_title = data.get("character_title", None)
                        max_words = 10
                        if character_title:
                            words = character_title.split()
                            if len(words) > max_words:
                                character_title = " ".join(words[:max_words]) + "..."
                            else:
                                pass
                        character_avatar = character_avatar_url
                    case "Local LLM":
                        conversation_method_image = os.path.abspath(os.path.join(os.path.dirname(__file__), "../icons/local_llm.png"))
                        character_avatar_url = data.get("character_avatar", None)
                        character_title = data.get("character_title", None)
                        max_words = 10
                        if character_title:
                            words = character_title.split()
                            if len(words) > max_words:
                                character_title = " ".join(words[:max_words]) + "..."
                            else:
                                pass
                        character_avatar = character_avatar_url

                self.add_character_to_list(character_list, character_avatar, character_name, character_title, conversation_method_image, )

            self.ui.stackedWidget.setCurrentIndex(1)
        else:
            self.ui.stackedWidget.setCurrentIndex(0)

    def create_character_card_widget(self, character_image, character_name, character_title, communication_icon):
        """
        Creates a character card widget with element alignment.
        """
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")

        card_widget = QWidget()
        card_widget.setStyleSheet("""
            QWidget {
                background-color: #222831;
                border-radius: 10px;
                padding: 5px;
                margin: 5px;
            }
            QLabel {
                color: #ffffff;
                font-family: 'Muli ExtraBold';
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                font-size: 15px;
                font-family: 'Muli ExtraBold';
                padding: 5px 10px;
            }
            QPushButton#callButton {
                background-color: rgb(51, 115, 87);
                color: white;
            }
            QPushButton#callButton:hover {
                background-color: #4b7777;
            }
            QPushButton#chatButton {
                background-color: #074173;
                color: white;
            }
            QPushButton#chatButton:hover {
                background-color: #2f577c;
            }
            QPushButton#voiceButton {
                background-color: rgb(32, 32, 64);
                color: white;
            }
            QPushButton#voiceButton:hover {
                background-color: rgb(39, 39, 70);
            }
            QPushButton#expressionsButton {
                background-color: rgb(173, 95, 17);
                color: white;
            }
            QPushButton#expressionsButton:hover {
                background-color: rgb(189, 104, 19);
            }
            QPushButton#deleteButton {
                background-color: #a94040;
                color: white;
            }
            QPushButton#deleteButton:hover {
                background-color: #8a3030;
            }
        """)
        card_widget.setMinimumWidth(1020)
        card_widget.setMaximumWidth(1020)

        shadow_effect = QGraphicsDropShadowEffect()
        shadow_effect.setBlurRadius(10)
        shadow_effect.setOffset(0, 4)
        shadow_effect.setColor(QtGui.QColor(0, 0, 0, 160))
        card_widget.setGraphicsEffect(shadow_effect)

        self.ui.ListWidget_character_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.ListWidget_character_list.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui.ListWidget_character_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        scroller = QScroller.scroller(self.ui.ListWidget_character_list.viewport())
        scroller.grabGesture(self.ui.ListWidget_character_list.viewport())
        properties = scroller.scrollerProperties()
        properties.setScrollMetric(QScrollerProperties.ScrollMetric.DecelerationFactor, 0.4)
        scroller.setScrollerProperties(properties)

        character_image_label = QLabel()
        pixmap = QPixmap(character_image)
        character_image_label.setPixmap(pixmap.scaled(100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        mask = QPixmap(pixmap.size())
        mask.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtCore.Qt.GlobalColor.black)
        painter.setPen(QtCore.Qt.GlobalColor.transparent)
        painter.drawEllipse(0, 0, pixmap.width(), pixmap.height())
        painter.end()
        pixmap.setMask(mask.createMaskFromColor(QtCore.Qt.GlobalColor.transparent))
        character_image_label.setPixmap(pixmap)
        character_image_label.setFixedSize(100, 100)
        character_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        character_image_label.setScaledContents(True)
        character_image_label.setStyleSheet("""border-radius: 45px;""")

        character_name_label = QLabel(character_name)
        character_name_label.setMinimumWidth(400)
        character_name_label.setMaximumWidth(400)
        character_name_label.setWordWrap(True)
        character_name_label.setFont(QFont("Muli ExtraBold", 14, QFont.Weight.Bold))

        if character_title:
            character_title_label = QLabel(character_title)
            character_title_label.setFont(QFont("Muli", 9, QFont.Weight.Bold))
            character_title_label.setStyleSheet("color: #aaaaaa;")

        communication_icon_label = QLabel()
        comm_pixmap = QPixmap(communication_icon)
        communication_icon_label.setPixmap(comm_pixmap.scaled(15, 15, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        communication_icon_label.setFixedSize(50, 50)

        call_button = QPushButton(self.tr("CALL"))
        call_button.setObjectName("callButton")
        call_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        chat_button = QPushButton(self.tr("CHAT"))
        chat_button.setObjectName("chatButton")
        chat_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        voice_button = QPushButton(self.tr("VOICE"))
        voice_button.setObjectName("voiceButton")
        voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        expressions_button = QPushButton(self.tr("EXPRESSIONS"))
        expressions_button.setObjectName("expressionsButton")
        expressions_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        delete_button = QPushButton(self.tr("DELETE"))
        delete_button.setObjectName("deleteButton")
        delete_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        chat_button.clicked.connect(lambda: asyncio.create_task(self.open_chat(character_name)))
        voice_button.clicked.connect(lambda: self.open_voice_menu(character_name))
        expressions_button.clicked.connect(lambda: self.open_expressions_menu(character_name))
        delete_button.clicked.connect(lambda: self.delete_character(card_widget, character_name))

        if sow_system_status == True:
            call_button.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))

        info_layout = QVBoxLayout()
        info_layout.addWidget(character_name_label)
        if character_title:
            info_layout.addWidget(character_title_label)
        info_layout.addWidget(communication_icon_label)
        info_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        button_layout = QHBoxLayout()
        if sow_system_status == True:
            button_layout.addWidget(call_button)
        button_layout.addWidget(chat_button)
        button_layout.addWidget(voice_button)
        if sow_system_status == True:
            button_layout.addWidget(expressions_button)
        button_layout.addWidget(delete_button)
        button_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        main_layout = QHBoxLayout(card_widget)
        main_layout.addWidget(character_image_label)
        main_layout.addLayout(info_layout)
        main_layout.addLayout(button_layout)
        main_layout.setContentsMargins(10, 5, 10, 5)

        return card_widget

    def add_character_to_list(self, character_list, character_image, character_name, character_title, communication_icon):
        """
        Add a character card to the list.
        """
        item = QListWidgetItem(character_list)
        character_widget = self.create_character_card_widget(character_image, character_name, character_title, communication_icon)
        item.setSizeHint(character_widget.sizeHint())
        character_list.addItem(item)
        character_list.setItemWidget(item, character_widget)

    def delete_character(self, card_widget, character_name):
        """
        Removes a character from the list after confirmation.
        """
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        msg_box.setWindowTitle(self.tr("Delete Character"))
        first_text = self.tr("Are you sure you want to delete ")
        message_text = f"""
                        <html>
                            <head>
                                <style>
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: #555;
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1>{first_text}<span style="color:#1E90FF;">{character_name}</span>?</h1>
                            </body>
                        </html>
                    """
        msg_box.setText(message_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        reply = msg_box.exec()
        if reply == QMessageBox.StandardButton.Yes:
            for index in range(self.ui.ListWidget_character_list.count()):
                item = self.ui.ListWidget_character_list.item(index)
                widget = self.ui.ListWidget_character_list.itemWidget(item)
                if widget == card_widget:
                    self.ui.ListWidget_character_list.takeItem(index)
                    break

            self.configuration_characters.delete_character(character_name)

    def choose_avatar(self):
        """
        Opens the file selection window and updates the avatar.
        """
        file_path, _ = QFileDialog.getOpenFileName(None, "Select an avatar file", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.configuration_settings.update_user_data("user_avatar", file_path)

    def set_dialog(self, dialog):
        """
        Loads the dialog window.
        """
        dialog.setStyleSheet(self.get_add_character_dialog_stylesheet())
        dialog.setWindowTitle(self.tr("Character Creation Selector"))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/sowInterface/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        dialog.setWindowIcon(icon)
        dialog.setMinimumSize(QtCore.QSize(300, 200))
        dialog.setMaximumSize(QtCore.QSize(300, 200))
        dialog.setBaseSize(QtCore.QSize(300, 200))

        # Radio buttons
        radio_char_ai = QRadioButton("Character AI")
        radio_mistral_ai = QRadioButton("Mistral AI")
        radio_local_llm = QRadioButton("Local LLM")

        # Group buttons
        button_group = QButtonGroup()
        button_group.addButton(radio_char_ai)
        button_group.addButton(radio_mistral_ai)
        button_group.addButton(radio_local_llm)

        # Default selection
        radio_char_ai.setChecked(True)

        # Select button
        select_button = QPushButton(self.tr("Select"))
        select_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_button.clicked.connect(dialog.accept)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(radio_char_ai)
        layout.addWidget(radio_mistral_ai)
        layout.addWidget(radio_local_llm)
        layout.addWidget(select_button)

        dialog.setLayout(layout)

        dialog.radio_char_ai = radio_char_ai
        dialog.radio_mistral_ai = radio_mistral_ai
        dialog.radio_local_llm = radio_local_llm
        dialog.select_button = select_button

    def get_selection(self, dialog):
        if dialog.radio_char_ai.isChecked():
            return "Character AI"
        elif dialog.radio_mistral_ai.isChecked():
            return "Mistral AI"
        elif dialog.radio_local_llm.isChecked():
            return "Local LLM"

    def get_add_character_dialog_stylesheet(self):
        return """
        QDialog {
            background-color: rgb(27,27,27);
            color: white;
            font-family: 'Muli Medium';
        }
        QRadioButton {
            font-size: 14px;
            padding: 5px;
        }
        QRadioButton::indicator {
            border: 3px solid rgb(52, 59, 72);
            width: 15px;
            height: 15px;
            border-radius: 10px;
            background-color: #333;
        }
        QRadioButton::indicator:checked {
            border: 3px solid rgb(52, 59, 72);
            background: rgb(28, 56, 85);
        }
        QPushButton {
            background: transparent;
            border-radius: 10px;
            border-color: rgb(255, 255, 255);
            border: 2px solid rgb(39, 44, 54);
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: rgb(54, 54, 54);
            border: 1px solid rgb(28, 56, 85);
        }
        QPushButton:pressed {
            background-color: rgb(39, 44, 54);
            border: 1px solid rgb(28, 56, 85);
        }
        """

    def show_selection_dialog(self):
        """
        Displays a dialog for selecting a conversation method and updates the UI accordingly.
        """
        dialog = QDialog()
        self.set_dialog(dialog)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selection = self.get_selection(dialog)

            match selection:
                case "Character AI":
                    self.ui.stackedWidget.setCurrentIndex(2)
                    self.ui.comboBox_conversation_method.setCurrentIndex(0)
                case "Mistral AI":
                    self.ui.stackedWidget.setCurrentIndex(3)
                    self.ui.comboBox_conversation_method.setCurrentIndex(1)
                case "Local LLM":
                    self.ui.stackedWidget.setCurrentIndex(3)
                    self.ui.comboBox_conversation_method.setCurrentIndex(2)
    ### SETUP MAIN TAB AND CREATE CHARACTER ============================================================

    ### SETUP GENERAL COMBOBOXES =======================================================================
    def on_comboBox_conversation_method_changed(self, text):
        self.configuration_settings.update_main_setting("conversation_method", text)

    def on_comboBox_speech_to_text_method_changed(self, index):
        self.configuration_settings.update_main_setting("stt_method", index)

    def on_comboBox_program_language_changed(self, index):
        self.configuration_settings.update_main_setting("program_language", index)

        #     message_box = QMessageBox()
        #     message_box.setIcon(QMessageBox.Icon.Information)
        #     message_box.setWindowTitle("Language Change")
        #     message_box.setText("The language has been changed. Please restart the application for the changes to take effect.")
        #     message_box.setInformativeText("Do you want to close the application now?")
        #     message_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        #     message_box.setDefaultButton(QMessageBox.StandardButton.Yes)

        #     response = message_box.exec()

        #     if response == QMessageBox.StandardButton.Yes:
        #         QApplication.quit()
        #     else:
        #         pass   

    def load_audio_devices(self):
        """
        Loads the input and output devices into the ComboBox.
        """
        input_device_index = self.configuration_settings.get_main_setting("input_device")
        output_device_index = self.configuration_settings.get_main_setting("output_device")

        self.ui.comboBox_input_devices.clear()
        self.ui.comboBox_output_devices.clear()

        input_devices = QMediaDevices.audioInputs()
        for device in input_devices:
            self.ui.comboBox_input_devices.addItem(device.description(), device)

        output_devices = QMediaDevices.audioOutputs()
        for device in output_devices:
            self.ui.comboBox_output_devices.addItem(device.description(), device)

        self.set_combobox_to_device(self.ui.comboBox_input_devices, input_device_index)
        self.set_combobox_to_device(self.ui.comboBox_output_devices, output_device_index)

    def set_combobox_to_device(self, combobox, index):
        if index != -1:
            combobox.setCurrentIndex(index)

    def on_comboBox_input_devices_changed(self, index):
        self.configuration_settings.update_main_setting("input_device", index)

    def on_comboBox_output_devices_changed(self, index):
        self.configuration_settings.update_main_setting("output_device", index)

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

    def on_comboBox_llm_devices_changed(self, index):
        self.configuration_settings.update_main_setting("llm_device", index)

    def load_llms_to_comboBox(self):
        """
        Loads all models with the extension .gguf in ComboBox.
        """
        self.ui.comboBox_llms.clear()
        self.ui.comboBox_llms.addItem("None")

        models_directory = "assets\\models"
        for filename in os.listdir(models_directory):
            if filename.endswith(".gguf"):
                self.ui.comboBox_llms.addItem(filename)

    def on_comboBox_llms_changed(self, index):
        """
        Processes the model selection in the ComboBox.
        """
        selected_model = self.ui.comboBox_llms.itemText(index)
        if selected_model == "None":
            model_path = None
        else:
            models_directory = "assets\\models"
            model_path = os.path.join(models_directory, selected_model)

        self.configuration_settings.update_main_setting("local_llm", model_path)

    def load_last_selected_model(self):
        """
        Loads the last selected model from the configuration file.
        """
        selected_model = self.configuration_settings.get_main_setting("local_llm")
        if selected_model:
            model_name = os.path.basename(selected_model)
            
            index = self.ui.comboBox_llms.findText(model_name)
            if index >= 0:
                self.ui.comboBox_llms.setCurrentIndex(index)
            else:
                print(f"The {model_name} model was not found in the ComboBox.")
                self.ui.comboBox_llms.setCurrentIndex(0)
        else:
            self.ui.comboBox_llms.setCurrentIndex(0)

    def on_checkBox_enable_sow_system_stateChanged(self):
        if self.ui.checkBox_enable_sow_system.isChecked():
            self.configuration_settings.update_main_setting("sow_system_status", True)
            self.ui.choose_live2d_mode_label.show()
            self.ui.comboBox_live2d_mode.show()
        else:
            self.configuration_settings.update_main_setting("sow_system_status", False)
            self.ui.choose_live2d_mode_label.hide()
            self.ui.comboBox_live2d_mode.hide()

    def on_checkBox_enable_mlock_stateChanged(self):
        if self.ui.checkBox_enable_mlock.isChecked():
            self.configuration_settings.update_main_setting("mlock_status", True)
        else:
            self.configuration_settings.update_main_setting("mlock_status", False)

    def on_comboBox_mode_translator_changed(self, index):
        self.configuration_settings.update_main_setting("translator_mode", index)

    def load_combobox(self):
        """
        Loads the settings to the Combobox's and Checkbox's of the interface from the configuration.
        """
        self.ui.comboBox_conversation_method.setCurrentText(self.configuration_settings.get_main_setting("conversation_method"))
        self.ui.comboBox_speech_to_text_method.setCurrentIndex(self.configuration_settings.get_main_setting("stt_method"))
        self.ui.comboBox_program_language.setCurrentIndex(self.configuration_settings.get_main_setting("program_language"))
        self.ui.comboBox_input_devices.setCurrentIndex(self.configuration_settings.get_main_setting("input_device"))
        self.ui.comboBox_output_devices.setCurrentIndex(self.configuration_settings.get_main_setting("output_device"))
        self.ui.comboBox_translator.setCurrentIndex(self.configuration_settings.get_main_setting("translator"))
        self.ui.comboBox_target_language_translator.setCurrentIndex(self.configuration_settings.get_main_setting("target_language"))
        self.ui.comboBox_live2d_mode.setCurrentIndex(self.configuration_settings.get_main_setting("live2d_mode"))
        self.ui.comboBox_llm_devices.setCurrentIndex(self.configuration_settings.get_main_setting("llm_device"))
        self.ui.comboBox_mode_translator.setCurrentIndex(self.configuration_settings.get_main_setting("translator_mode"))

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

        sow_state = self.configuration_settings.get_main_setting("sow_system_status")
        if sow_state == False:
            self.ui.checkBox_enable_sow_system.setChecked(False)
            self.ui.choose_live2d_mode_label.hide()
            self.ui.comboBox_live2d_mode.hide()
        else:
            self.ui.checkBox_enable_sow_system.setChecked(True)
            self.ui.choose_live2d_mode_label.show()
            self.ui.comboBox_live2d_mode.show()

        mlock_state = self.configuration_settings.get_main_setting("mlock_status")
        if mlock_state == False:
            self.ui.checkBox_enable_mlock.setChecked(False)
        else:
            self.ui.checkBox_enable_mlock.setChecked(True)
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
        elif selected_conversation_method == "Local LLM":
            self.ui.conversation_method_token_title_label.hide()
            self.ui.lineEdit_api_token_options.hide()

    def update_api_token(self):
        """
        Changing the API token to the selected option.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()
        if selected_conversation_method == "Character AI":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            api_token = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Mistral AI":
            self.ui.conversation_method_token_title_label.show()
            self.ui.lineEdit_api_token_options.show()
            api_token = self.configuration_api.get_token("MISTRAL_AI_API_TOKEN")
            if api_token != self.ui.lineEdit_api_token_options.text():
                self.ui.lineEdit_api_token_options.setText(api_token)
        elif selected_conversation_method == "Local LLM":
            self.ui.conversation_method_token_title_label.hide()
            self.ui.lineEdit_api_token_options.hide()

    def save_api_token_in_real_time(self):
        """
        Saving the API token to a configuration file in real time.
        """
        selected_conversation_method = self.ui.comboBox_conversation_method.currentText()
        if selected_conversation_method == "Character AI":
            method = "CHARACTER_AI_API_TOKEN"
        elif selected_conversation_method == "Mistral AI":
            method = "MISTRAL_AI_API_TOKEN"

        self.configuration_api.save_api_token(method, self.ui.lineEdit_api_token_options.text())

    def initialize_username_line_edit(self):
        username = self.configuration_settings.get_user_data("user_name")
        self.ui.lineEdit_user_name_options.setText(username)

    def save_username_in_real_time(self):
        username = self.ui.lineEdit_user_name_options.text()
        self.configuration_settings.update_user_data("user_name", username)

    def initialize_userpersonality_line_edit(self):
        userpersonality = self.configuration_settings.get_user_data("user_description")
        self.ui.lineEdit_user_description_options.setText(userpersonality)

    def save_userpersonality_in_real_time(self):
        userpersonality = self.ui.lineEdit_user_description_options.text()
        self.configuration_settings.update_user_data("user_description", userpersonality)

    def initialize_gpu_layers_horizontalSlider(self):
        n_gpu_layers = self.configuration_settings.get_main_setting("gpu_layers")
        self.ui.gpu_layers_horizontalSlider.setValue(n_gpu_layers)
        self.ui.gpu_layers_value_label.setText(self.tr("Value: ") + f"{n_gpu_layers}")

    def save_gpu_layers_in_real_time(self):
        n_gpu_layers = self.ui.gpu_layers_horizontalSlider.value()
        self.configuration_settings.update_main_setting("gpu_layers", n_gpu_layers)
        self.ui.gpu_layers_value_label.setText(self.tr("Value: ") + f"{n_gpu_layers}")

    def initialize_context_size_horizontalSlider(self):
        context_size = self.configuration_settings.get_main_setting("context_size")
        self.ui.context_size_horizontalSlider.setValue(context_size)
        self.ui.context_size_value_label.setText(self.tr("Value: ") + f"{context_size}")

    def save_context_size_in_real_time(self):
        context_size = self.ui.context_size_horizontalSlider.value()
        self.configuration_settings.update_main_setting("context_size", context_size)
        self.ui.context_size_value_label.setText(self.tr("Value: ") + f"{context_size}")

    def initialize_temperature_horizontalSlider(self):
        temperature = self.configuration_settings.get_main_setting("temperature")
        temperature_int = int(round(temperature * 10))
        self.ui.temperature_horizontalSlider.setValue(temperature_int)
        self.ui.temperature_value_label.setText(self.tr("Value: ") + f"{temperature:.1f}")

    def save_temperature_in_real_time(self):
        temperature = self.ui.temperature_horizontalSlider.value()
        scaled_value = temperature / 10.0
        self.configuration_settings.update_main_setting("temperature", scaled_value)
        self.ui.temperature_value_label.setText(self.tr("Value: ") + f"{scaled_value:.1f}")

    def initialize_top_p_horizontalSlider(self):
        top_p = self.configuration_settings.get_main_setting("top_p")
        top_p_int = int(round(top_p * 10))
        self.ui.top_p_horizontalSlider.setValue(top_p_int)
        self.ui.top_p_value_label.setText(self.tr("Value: ") + f"{top_p:.1f}")

    def save_top_p_in_real_time(self):
        top_p = self.ui.top_p_horizontalSlider.value()
        scaled_value = top_p / 10.0
        self.configuration_settings.update_main_setting("top_p", scaled_value)
        self.ui.top_p_value_label.setText(self.tr("Value: ") + f"{scaled_value:.1f}")

    def initialize_repeat_penalty_horizontalSlider(self):
        repeat_penalty = self.configuration_settings.get_main_setting("repeat_penalty")
        repeat_penalty_int = int(round(repeat_penalty * 10))
        self.ui.repeat_penalty_horizontalSlider.setValue(repeat_penalty_int)
        self.ui.repeat_penalty_value_label.setText(self.tr("Value: ") + f"{repeat_penalty:.1f}")

    def save_repeat_penalty_in_real_time(self):
        repeat_penalty = self.ui.repeat_penalty_horizontalSlider.value()
        scaled_value = repeat_penalty / 10.0
        self.configuration_settings.update_main_setting("repeat_penalty", scaled_value)
        self.ui.repeat_penalty_value_label.setText(self.tr("Value: ") + f"{scaled_value}")

    def initialize_max_tokens_horizontalSlider(self):
        max_tokens = self.configuration_settings.get_main_setting("max_tokens")
        self.ui.max_tokens_horizontalSlider.setValue(max_tokens)
        self.ui.max_tokens_value_label.setText(self.tr("Value: ") + f"{max_tokens}")

    def save_max_tokens_in_real_time(self):
        max_tokens = self.ui.max_tokens_horizontalSlider.value()
        self.configuration_settings.update_main_setting("max_tokens", max_tokens)
        self.ui.max_tokens_value_label.setText(self.tr("Value: ") + f"{max_tokens}")
    ### SETUP OPTIONS ==================================================================================

    ### SETUP CHARACTER INFORMATION ====================================================================
    def import_character_avatar(self):
        """
        Opens a dialog box for selecting a character's avatar image and updates the interface.
        """
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "Choose character's image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
            if file_path:
                icon = QtGui.QIcon(file_path)
                self.ui.pushButton_import_character_image.setIcon(icon)
                self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(64, 64))
                self.configuration_settings.update_user_data("current_character_image", file_path)
            else:
                print("No file selected.")
                return None
        except Exception as e:
            print(f"Error occurred while importing character image: {e}")
            return None

    def import_character_card(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(None, "Choose PNG character's card", "", "Images (*.png)")
            if file_path:
                icon = QtGui.QIcon(file_path)
                self.ui.pushButton_import_character_image.setIcon(icon)
                self.ui.pushButton_import_character_image.setIconSize(QtCore.QSize(64, 64))
                self.configuration_settings.update_user_data("current_character_image", file_path)

                self.character_data = self.read_character_card(file_path)
                if self.character_data and "data" in self.character_data:
                    data = self.character_data["data"]
                    self.ui.lineEdit_character_name_building.setText(f"{data.get('name', 'None')}")
                    self.ui.textEdit_character_description_building.setText(f"{data.get('description', 'None')}\n\n{data.get('scenario', 'None')}")
                    self.ui.textEdit_character_personality_building.setText(f"{data.get('personality', 'None')}")
                    self.ui.textEdit_first_message_building.setText(f"{data.get('first_mes', 'None')}")
        except Exception as e:
            print(f"Error occured while importing character card: {e}")

    def read_character_card(self, path):
        image = PngImagePlugin.PngImageFile(path)
        user_comment = image.text.get('chara', None)
        if user_comment is None:
            print("No character data found in the image.")
            return None
        try:
            json_bytes = base64.b64decode(user_comment)
            json_str = json_bytes.decode('utf-8')
            data = json.loads(json_str)
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            print(f"Error decoding character data: {e}")
            return None
        return data
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
        xttsv2_voice_type = self.configuration_characters.get_character_data(character_name, "xttsv2_voice_type")
        xttsv2_rvc_enabled = self.configuration_characters.get_character_data(character_name, "xttsv2_rvc_enabled")
        xttsv2_rvc_file = self.configuration_characters.get_character_data(character_name, "xttsv2_rvc_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.tr('Text-To-Speech Selector'))
        dialog.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        dialog.setMinimumSize(450, 300)
        dialog.setMaximumSize(450, 300)
        dialog.setStyleSheet("""
            QWidget {
                background-color: rgb(27,27,27);
                color: #e0e0e0;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                font-weight: bold;
                margin-bottom: 10px;
                color: #ffa726;
            }
            QLineEdit {
                color: rgb(255, 255, 255);
                padding-left: 5px;
                border-radius: 5px;
                border: 2px solid rgb(39, 44, 54);
                background-color: rgb(51,51,51);
            }

            QLineEdit:focus {
                border: 1px solid rgb(28, 56, 85);
            }
            QRadioButton {
            font-size: 14px;
            padding: 5px;
            }
            QRadioButton::indicator {
                border: 3px solid rgb(52, 59, 72);
                width: 15px;
                height: 15px;
                border-radius: 8px;
                background-color: #333;
            }
            QRadioButton::indicator:checked {
                border: 3px solid rgb(52, 59, 72);
                background: rgb(28, 56, 85);
            }
            QPushButton {
                background: transparent;
                border-radius: 10px;
                border-color: rgb(255, 255, 255);
                border: 2px solid rgb(39, 44, 54);
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgb(54, 54, 54);
                border: 1px solid rgb(28, 56, 85);
            }
            QPushButton:pressed {
                background-color: rgb(39, 44, 54);
                border: 1px solid rgb(28, 56, 85);
            }
            QComboBox {
                background-color: #353535;
                color: #ffffff;
                border-radius: 5px;
                border: 2px solid rgb(33, 37, 43);
                padding: 5px;
                padding-left: 10px;
            }
            QComboBox:hover {
                border: 2px solid rgb(64, 71, 88);
            }
            QComboBox QAbstractItemView {
                color: #ffffff;
                background-color: rgb(33, 37, 43);
                padding: 10px;
                selection-background-color: rgb(39, 44, 54);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid rgb(39, 44, 54);
                background-color: rgb(39, 44, 54);
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
                image: url(:/sowInterface/arrowDown.png);
            }
        """)

        main_layout = QVBoxLayout()
        
        title_label = QLabel(self.tr('Choose Text-To-Speech method'))
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        combo_box = QtWidgets.QComboBox(dialog)
        self.add_items_to_combo_box(conversation_method, combo_box)
        combo_box.currentTextChanged.connect(lambda: self.update_ui(combo_box.currentText(), stacked_widget))
        main_layout.addWidget(combo_box)

        stacked_widget = QStackedWidget(dialog)
        stacked_widget.addWidget(self.create_voice_nothing_widgets(character_name))
        stacked_widget.addWidget(self.create_character_ai_widgets(character_name, character_ai_voice_name))
        stacked_widget.addWidget(self.create_elevenlabs_widgets(character_name))
        stacked_widget.addWidget(self.create_xttsv2_widgets(character_name, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file))
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
        elif conversation_method in ["Mistral AI", "Local LLM"]:
            combo_box.addItem('Nothing')
            combo_box.addItem('ElevenLabs')
            combo_box.addItem('XTTSv2')

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

    def update_ui(self, selected_method, stacked_widget):
        if selected_method == "Nothing":
            stacked_widget.setCurrentIndex(0)
        elif selected_method == "Character AI":
            stacked_widget.setCurrentIndex(1)
        elif selected_method == "ElevenLabs":
            stacked_widget.setCurrentIndex(2)
        elif selected_method == "XTTSv2":
            stacked_widget.setCurrentIndex(3)

    def create_voice_nothing_widgets(self, character_name):
        layout = QVBoxLayout()

        placeholder_label = QLabel(self.tr("Nothing to display here yet."))
        placeholder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        placeholder_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        layout.addWidget(placeholder_label)

        save_button = QPushButton(self.tr('Save Selection'))
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(save_button)

        def save_voice_mode_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Character Voice"))
            message_box_information.setText(self.tr("Voice successfully saved!"))
            message_box_information.exec()

        save_button.clicked.connect(save_voice_mode_settings)

        widget = QWidget()
        widget.setLayout(layout)
        
        return widget

    def create_character_ai_widgets(self, character_name, character_ai_voice_name):
        layout = QVBoxLayout()

        if character_ai_voice_name:
            character_ai_label = QLabel(self.tr("Your character voice name is ") + character_ai_voice_name)
        else:
            character_ai_label = QLabel(self.tr('Choose voice for your character'))
        
        character_ai_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        character_ai_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        character_ai_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(character_ai_label)

        voice_input = QtWidgets.QLineEdit()
        voice_input.setPlaceholderText(self.tr("Enter a voice name for the character"))
        layout.addWidget(voice_input)

        search_layout = QHBoxLayout()

        voice_combo = QtWidgets.QComboBox()
        search_layout.addWidget(voice_combo)

        search_button = QPushButton(self.tr('Search'))
        search_button.setFixedWidth(100)
        search_button.clicked.connect(lambda: self.search_character_voice(voice_combo, voice_input, character_name))
        search_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        listen_button = QPushButton(self.tr('Listen'))
        listen_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        listen_button.clicked.connect(lambda: self.play_preview_voice(character_name))
        select_button = QPushButton(self.tr('Select voice'))
        select_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_button.clicked.connect(lambda: self.select_voice("Character AI", character_name, voice_combo, None))

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(listen_button)
        buttons_layout.addWidget(select_button)
        layout.addLayout(buttons_layout)

        widget = QWidget()
        widget.setLayout(layout)
        
        return widget

    def create_elevenlabs_widgets(self, character_name):
        layout = QVBoxLayout()

        elevenlabs_label = QLabel(self.tr('Write your API Token from ElevenLabs'))
        elevenlabs_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        elevenlabs_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(elevenlabs_label)

        token_input = QtWidgets.QLineEdit()
        token_input.setPlaceholderText(self.tr('Enter your ElevenLabs API token...'))
        layout.addWidget(token_input)

        elevenlabs_api = self.configuration_api.get_token("ELEVENLABS_API_TOKEN")
        if elevenlabs_api:
            token_input.setText(elevenlabs_api)

        voice_id_input = QtWidgets.QLineEdit()
        voice_id_input.setPlaceholderText(self.tr('Enter Voice ID from ElevenLabs'))
        layout.addWidget(voice_id_input)

        elevenlabs_voice_id = self.configuration_characters.get_character_data(character_name, "elevenlabs_voice_id")
        if elevenlabs_voice_id:
            voice_id_input.setText(elevenlabs_voice_id)

        select_voice_button = QPushButton(self.tr('Select Voice'))
        select_voice_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        select_voice_button.clicked.connect(lambda: self.select_voice("ElevenLabs", character_name, voice_id_input.text(), token_input.text()))
        layout.addWidget(select_voice_button)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_xttsv2_widgets(self, character_name, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_file_name):
        RVC_DIR = os.path.join(os.getcwd(), "assets\\rvc_models")

        layout = QVBoxLayout()

        xtts_label = QLabel(self.tr('Choose voice type for XTTSv2'))
        xtts_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        xtts_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(xtts_label)

        voice_type_combo = QtWidgets.QComboBox()
        voice_type_combo.addItems([self.tr("Male"), self.tr("Female"), self.tr("Female Calm")])
        layout.addWidget(voice_type_combo)

        if xttsv2_voice_type:
            voice_type_combo.setCurrentText(xttsv2_voice_type)

        rvc_checkbox = QtWidgets.QCheckBox(self.tr("Enable RVC"))
        layout.addWidget(rvc_checkbox)

        if xttsv2_rvc_enabled:
            rvc_checkbox.setCheckable(xttsv2_rvc_enabled)

        rvc_file_combo = QtWidgets.QComboBox()
        rvc_file_combo.setEnabled(False)
        layout.addWidget(rvc_file_combo)

        def populate_rvc_folders():
            rvc_file_combo.clear()
            selected_index = -1
            if os.path.isdir(RVC_DIR):
                folders = [f for f in os.listdir(RVC_DIR) if os.path.isdir(os.path.join(RVC_DIR, f))]
                if folders:
                    rvc_file_combo.addItems(folders)
                    if xttsv2_file_name:
                        try:
                            folder_name = os.path.basename(os.path.dirname(xttsv2_file_name))
                            selected_index = folders.index(folder_name)
                        except ValueError:
                            selected_index = -1
                else:
                    rvc_file_combo.addItem("No folders found")
            else:
                rvc_file_combo.addItem(self.tr("Invalid RVC directory"))

            if selected_index >= 0:
                rvc_file_combo.setCurrentIndex(selected_index)
        
        populate_rvc_folders()

        def toggle_rvc_file_combo(checked):
            rvc_file_combo.setEnabled(checked)

        rvc_checkbox.stateChanged.connect(toggle_rvc_file_combo)

        select_voice_button = QPushButton(self.tr('Select Voice'))
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
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("No Folder"))
                message_box_information.setText(self.tr("RVC is enabled, but no folder selected!"))
                message_box_information.exec()
                return

            rvc_file = None
            if rvc_folder:
                pth_files = [f for f in os.listdir(rvc_folder) if f.endswith(".pth")]
                if pth_files:
                    rvc_file = pth_files[0]
                else:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                    message_box_information.setWindowTitle(self.tr("No PTH File"))
                    message_box_information.setText(self.tr("No .pth file found in folder: ") + rvc_folder)
                    message_box_information.exec()
                    return

            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["xttsv2_voice_type"] = voice_type
            configuration_data["character_list"][character_name]["xttsv2_rvc_enabled"] = rvc_enabled
            configuration_data["character_list"][character_name]["xttsv2_rvc_file"] = rvc_file
            configuration_data["character_list"][character_name]["current_text_to_speech"] = "XTTSv2"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Character Voice"))
            message_box_information.setText(self.tr("Voice successfully added!"))
            message_box_information.exec()

        select_voice_button.clicked.connect(save_xttsv2_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def select_voice(self, tts_method, character_name, data, elevenlabs_api):
        match tts_method:
            case "Character AI":
                voice_name = data.currentText()
                voice_id = data.currentData()

                if voice_id:
                    configuration_data = self.configuration_characters.load_configuration()
                    configuration_data["character_list"][character_name]["voice_name"] = voice_name
                    configuration_data["character_list"][character_name]["character_ai_voice_id"] = voice_id
                    configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                    self.configuration_characters.save_configuration_edit(configuration_data)

                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("Character Voice"))
                message_box_information.setText(self.tr("Voice successfully added!"))
                message_box_information.exec()
            case "ElevenLabs":
                voice_id = data
                
                self.configuration_api.save_api_token("ELEVENLABS_API_TOKEN", elevenlabs_api)
                
                configuration_data = self.configuration_characters.load_configuration()
                configuration_data["character_list"][character_name]["elevenlabs_voice_id"] = voice_id
                configuration_data["character_list"][character_name]["current_text_to_speech"] = tts_method
                self.configuration_characters.save_configuration_edit(configuration_data)

                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("Character Voice"))
                message_box_information.setText(self.tr("Voice successfully added!"))
                message_box_information.exec()

    def search_character_voice(self, combobox, voice_input, character_name):
        combobox.clear()
        voice_name = voice_input.text().strip()

        if not voice_name:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Input Error"))
            message_box_information.setText(self.tr("Please enter a valid voice name."))
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
                    message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                    message_box_information.setWindowTitle(self.tr("No Voices"))
                    message_box_information.setText(self.tr("No voices found for the given name."))
                    message_box_information.exec()
            except Exception as e:
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("Fetch Error"))
                message_box_information.setText(self.tr("Failed to fetch voices: ") + str(e))
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
        current_sow_system_mode = self.configuration_characters.get_character_data(character_name, "current_sow_system_mode")
        expression_images_file = self.configuration_characters.get_character_data(character_name, "expression_images_file")
        live2d_model_file = self.configuration_characters.get_character_data(character_name, "live2d_model_file")

        dialog = QDialog()
        dialog.setWindowTitle(self.tr('Expressions Selector'))
        dialog.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        dialog.setMinimumSize(450, 300)
        dialog.setMaximumSize(450, 300)
        dialog.setStyleSheet("""
            QWidget {
                background-color: rgb(27,27,27);
                color: #e0e0e0;
                font-size: 14px;
                font-family: "Segoe UI", Arial, sans-serif;
            }
            QLabel {
                font-weight: bold;
                margin-bottom: 10px;
                color: #ffa726;
            }
            QLineEdit {
                color: rgb(255, 255, 255);
                padding-left: 5px;
                border-radius: 5px;
                border: 2px solid rgb(39, 44, 54);
                background-color: rgb(51,51,51);
            }

            QLineEdit:focus {
                border: 1px solid rgb(28, 56, 85);
            }
            QRadioButton {
            font-size: 14px;
            padding: 5px;
            }
            QRadioButton::indicator {
                border: 3px solid rgb(52, 59, 72);
                width: 15px;
                height: 15px;
                border-radius: 8px;
                background-color: #333;
            }
            QRadioButton::indicator:checked {
                border: 3px solid rgb(52, 59, 72);
                background: rgb(28, 56, 85);
            }
            QPushButton {
                background: transparent;
                border-radius: 10px;
                border-color: rgb(255, 255, 255);
                border: 2px solid rgb(39, 44, 54);
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgb(54, 54, 54);
                border: 1px solid rgb(28, 56, 85);
            }
            QPushButton:pressed {
                background-color: rgb(39, 44, 54);
                border: 1px solid rgb(28, 56, 85);
            }
            QComboBox {
                background-color: #353535;
                color: #ffffff;
                border-radius: 5px;
                border: 2px solid rgb(33, 37, 43);
                padding: 5px;
                padding-left: 10px;
            }
            QComboBox:hover {
                border: 2px solid rgb(64, 71, 88);
            }
            QComboBox QAbstractItemView {
                color: #ffffff;
                background-color: rgb(33, 37, 43);
                padding: 10px;
                selection-background-color: rgb(39, 44, 54);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid rgb(39, 44, 54);
                background-color: rgb(39, 44, 54);
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
                image: url(:/sowInterface/arrowDown.png);
            }
        """)

        main_layout = QVBoxLayout()

        title_label = QLabel(self.tr('Choose Expression Method'))
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        combo_box = QtWidgets.QComboBox(dialog)
        combo_box.addItems(["Nothing", "Expressions Images", "Live2D Model"])
        combo_box.currentTextChanged.connect(lambda: self.update_expressions_menu_ui(combo_box.currentText(), stacked_widget))

        main_layout.addWidget(combo_box)

        stacked_widget = QStackedWidget(dialog)
        stacked_widget.addWidget(self.create_nothing_widgets(character_name))
        stacked_widget.addWidget(self.create_expression_images_widgets(character_name, expression_images_file))
        stacked_widget.addWidget(self.create_live2d_model_widgets(character_name, live2d_model_file))

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

    def update_expressions_menu_ui(self, selected_method, stacked_widget):
        if selected_method == "Nothing":
            stacked_widget.setCurrentIndex(0)
        elif selected_method == "Expressions Images":
            stacked_widget.setCurrentIndex(1)
        elif selected_method == "Live2D Model":
            stacked_widget.setCurrentIndex(2)

    def create_nothing_widgets(self, character_name):
        layout = QVBoxLayout()

        placeholder_label = QLabel(self.tr("Nothing to display here yet."))
        placeholder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        placeholder_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        layout.addWidget(placeholder_label)

        save_button = QPushButton(self.tr('Save Selection'))
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(save_button)

        def save_expression_images_settings():
            configuration_data = self.configuration_characters.load_configuration()
            configuration_data["character_list"][character_name]["current_sow_system_mode"] = "Nothing"
            self.configuration_characters.save_configuration_edit(configuration_data)

            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Expression Mode Saved"))
            message_box_information.setText(self.tr("Expression mode successfully saved!"))
            message_box_information.exec()

        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_expression_images_widgets(self, character_name, expression_images_folder):
        EXP_DIR = os.path.join(os.getcwd(), "assets\\emotions\\images")
        
        layout = QVBoxLayout()

        expressions_image_label = QLabel(self.tr('Select an emotion folder'))
        expressions_image_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        expressions_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(expressions_image_label)

        expressions_folder_combo = QtWidgets.QComboBox()
        layout.addWidget(expressions_folder_combo)

        save_button = QPushButton(self.tr('Save Selection'))
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
                    expressions_folder_combo.addItem("No folders found")
            else:
                expressions_folder_combo.addItem(self.tr("Invalid expressions directory"))

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
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Expression Folder Saved"))
            message_box_information.setText(self.tr("Expression folder successfully saved!"))
            message_box_information.exec()

        populate_expressions_images_folders()
        save_button.clicked.connect(save_expression_images_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_live2d_model_widgets(self, character_name, live2d_model_folder):
        LIVE2D_DIR = os.path.join(os.getcwd(), "assets\\emotions\\live2d")
        
        layout = QVBoxLayout()

        live2d_model_label = QLabel(self.tr('Select folder with Live2D Model'))
        live2d_model_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #ffffff;
            font-family: Arial, sans-serif;
        """)
        live2d_model_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(live2d_model_label)

        live2d_model_folder_combo = QtWidgets.QComboBox()
        layout.addWidget(live2d_model_folder_combo)

        save_button = QPushButton(self.tr('Save Selection'))
        save_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
                    live2d_model_folder_combo.addItem("No folders found")
            else:
                live2d_model_folder_combo.addItem(self.tr("Invalid live2d model directory"))

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
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Live2D Folder Saved"))
            message_box_information.setText(self.tr("Live2D folder successfully saved!"))
            message_box_information.exec()

        populate_live2d_model_folders()
        save_button.clicked.connect(save_live2d_model_settings)

        widget = QWidget()
        widget.setLayout(layout)
        return widget
    ### EXPRESSIONS DIALOG =============================================================================

    ### CHARACTER GATEWAY ==============================================================================
    def open_characters_gateway(self):
        """
        Opens the gateway of characters and adjusts the behavior depending on the availability of an API token.
        """
        character_ai_api = self.configuration_api.get_token("CHARACTER_AI_API_TOKEN")
        self.ui.stackedWidget_character_ai.setCurrentIndex(0)
        self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
        if character_ai_api:
            available_api = True
            self.ui.tabWidget_characters_gateway.currentChanged.connect(lambda: self.handle_tab_change(self.ui.tabWidget_characters_gateway.currentIndex(), available_api))
            self.handle_tab_change(self.ui.tabWidget_characters_gateway.currentIndex(), available_api)
        else:
            available_api = False
            self.ui.tabWidget_characters_gateway.currentChanged.connect(lambda: self.handle_tab_change(self.ui.tabWidget_characters_gateway.currentIndex(), available_api))
            self.handle_tab_change(self.ui.tabWidget_characters_gateway.currentIndex(), available_api)

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

    def create_characterai_layout(self):
        if not hasattr(self, 'character_layout'):
            self.characterai_layout = QtWidgets.QVBoxLayout(self.ui.scrollAreaWidgetContents_character_ai)
            self.characterai_layout.setContentsMargins(0, 0, 0, 0)
            self.characterai_layout.setSpacing(10)

    def create_characterai_search_layout(self):
        if not hasattr(self, 'character_layout'):
            self.characterai_search_layout = QtWidgets.QVBoxLayout(self.ui.scrollAreaWidgetContents_character_ai_search)
            self.characterai_search_layout.setContentsMargins(0, 0, 0, 0)
            self.characterai_search_layout.setSpacing(10)

    def create_character_card_layout(self):
        if not hasattr(self, 'character_layout'):
            self.character_card_layout = QtWidgets.QVBoxLayout(self.ui.scrollAreaWidgetContents_character_card)
            self.character_card_layout.setContentsMargins(0, 0, 0, 0)
            self.character_card_layout.setSpacing(10)

    def create_character_card_search_layout(self):
        if not hasattr(self, 'character_layout'):
            self.character_card_search_layout = QtWidgets.QVBoxLayout(self.ui.scrollAreaWidgetContents_character_card_search)
            self.character_card_search_layout.setContentsMargins(0, 0, 0, 0)
            self.character_card_search_layout.setSpacing(10)

    def add_character_from_cai_gateway_sync(self, character_id):
        task = asyncio.create_task(self.add_character_from_cai_gateway(character_id))
        task.add_done_callback(self.on_add_character_from_cai_gateway_done)

    def on_add_character_from_cai_gateway_done(self, task):
        result = task.result()

        if result:
            character_name = result
            first_text = self.tr("was successfully added!")
            second_text = self.tr("You can now interact with the character in your character list.")
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Character Information"))

            message_text = f"""
                        <html>
                            <head>
                                <style>
                                    h1 {{
                                        color: #4CAF50;
                                        font-family: Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: #555;
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                        font-size: 14px;
                                    }}
                                </style>
                            </head>
                            <body>
                                <h1><span style="color:#1E90FF;">{character_name}</span> {first_text}</h1>
                                <p>{second_text}</p>
                            </body>
                        </html>
                    """
            message_box_information.setText(message_text)
            message_box_information.exec()
        else:
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Error"))

            first_text = self.tr("There was an error while adding the character.")
            second_text = self.tr("Please try again.")
            message_text = f"""
                        <html>
                            <head>
                                <style>
                                    h1 {{
                                        color: #FF6347;
                                        font-family: Arial, sans-serif;
                                        font-size: 20px;
                                    }}
                                    p {{
                                        color: #555;
                                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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
            print(f"Error occurred while adding character: {e}")
            return None

    def add_character_from_gateway(self, character_name, character_title, character_avatar_directory, character_description, character_personality, character_first_message, conversation_method):
        match conversation_method:
            case "Mistral AI":
                try:
                    character_description = None
                    self.configuration_characters.save_character_card(character_name, character_title, character_avatar_directory, character_description, character_personality, character_first_message, elevenlabs_voice_id=None, xttsv2_voice_type=None, xttsv2_rvc_enabled=False, xttsv2_rvc_file=None, expression_images_folder=None, live2d_model_folder=None, conversation_method="Mistral AI")
                    first_text = self.tr("was successfully added!")
                    second_text = self.tr("You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                    message_box_information.setWindowTitle(self.tr("Character Information"))

                    message_text = f"""
                                <html>
                                    <head>
                                        <style>
                                            h1 {{
                                                color: #4CAF50;
                                                font-family: Arial, sans-serif;
                                                font-size: 20px;
                                            }}
                                            p {{
                                                color: #555;
                                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                font-size: 14px;
                                            }}
                                        </style>
                                    </head>
                                    <body>
                                        <h1><span style="color:#1E90FF;">{character_name}</span> {first_text}</h1>
                                        <p>{second_text}</p>
                                    </body>
                                </html>
                            """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    print(f"Error occurred while adding character: {e}")
                    return None
            case "Local LLM":
                try:
                    character_description = None
                    self.configuration_characters.save_character_card(character_name, character_title, character_avatar_directory, character_description, character_personality, character_first_message, elevenlabs_voice_id=None, xttsv2_voice_type=None, xttsv2_rvc_enabled=False, xttsv2_rvc_file=None, expression_images_folder=None, live2d_model_folder=None, conversation_method="Local LLM")
                    first_text = self.tr("was successfully added!")
                    second_text = self.tr("You can now interact with the character in your character list.")
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                    message_box_information.setWindowTitle(self.tr("Character Information"))

                    message_text = f"""
                                <html>
                                    <head>
                                        <style>
                                            h1 {{
                                                color: #4CAF50;
                                                font-family: Arial, sans-serif;
                                                font-size: 20px;
                                            }}
                                            p {{
                                                color: #555;
                                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                font-size: 14px;
                                            }}
                                        </style>
                                    </head>
                                    <body>
                                        <h1><span style="color:#1E90FF;">{character_name}</span> {first_text}</h1>
                                        <p>{second_text}</p>
                                    </body>
                                </html>
                            """
                    message_box_information.setText(message_text)
                    message_box_information.exec()
                    return character_name
                except Exception as e:
                    print(f"Error occurred while adding character: {e}")
                    return None

    def handle_tab_change(self, current_tab_index, available_api):
        """
        Handles changing tabs in the character gateway.
        """
        scroll_area_mapping = {
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_ai_search_page": self.ui.scrollArea_character_ai_search_page,
            "character_card_page": self.ui.scrollArea_character_card,
            "character_card_search_page": self.ui.scrollArea_character_card_search
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        async def load_characters(fetch_function, create_widget_function, scroll_area_contents):
            data = await fetch_function()
            main_widget = create_widget_function(data)
            
            layout = scroll_area_contents.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(main_widget)

        match current_tab_index:
            case 0:  # Character AI
                self.ui.stackedWidget_character_ai.setCurrentIndex(0)
                if available_api:
                    async def fetch_feature_and_recommend_character_ai():
                        feature_data = await self.character_ai_client.fetch_feature()
                        recommended_data = await self.character_ai_client.fetch_recommended()
                        return feature_data, recommended_data

                    asyncio.create_task(
                        load_characters(
                            fetch_feature_and_recommend_character_ai,
                            lambda data: self.create_main_widget(*data),
                            self.ui.scrollAreaWidgetContents_character_ai
                        )
                    )
                else:
                    warning_label = QLabel(parent=self.ui.scrollAreaWidgetContents_character_ai)
                    warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    warning_label.setFont(QFont("Muli", 14, QFont.Weight.Bold))
                    warning_label.setGeometry(QtCore.QRect(10, 220, 1020, 60))
                    warning_label.setText(self.tr("You don't have a token from Character AI"))
            case 1:  # Character Card
                self.ui.stackedWidget_character_card_gateway.setCurrentIndex(0)
                async def fetch_trending_characters():
                    return await self.character_card_client.fetch_trending_character_data()

                asyncio.create_task(
                    load_characters(
                        fetch_trending_characters,
                        self.create_main_widget_for_character_card,
                        self.ui.scrollAreaWidgetContents_character_card
                    )
                )

        self.ui.stackedWidget.setCurrentIndex(4)

    def search_character(self):
        """
        Searches for characters based on the current tab.
        """
        character_name = self.ui.lineEdit_search_character.text()
        self.ui.lineEdit_search_character.clear()

        current_tab_index = self.ui.tabWidget_characters_gateway.currentIndex()

        scroll_area_mapping = {
            "character_ai_page": self.ui.scrollArea_character_ai_page,
            "character_ai_search_page": self.ui.scrollArea_character_ai_search_page,
            "character_card_page": self.ui.scrollArea_character_card,
            "character_card_search_page": self.ui.scrollArea_character_card_search
        }
        for area in scroll_area_mapping.values():
            self.clear_scroll_area(area)

        match current_tab_index:
            case 0:
                async def fetch_searched_character_ai():
                    searched_characters = await self.character_ai_client.search_character(character_name)
                    return searched_characters

                async def load_characters():
                    searched_characters = await fetch_searched_character_ai()
                    main_widget = self.create_main_widget_search(searched_characters)
                    
                    self.ui.stackedWidget_character_ai.setCurrentIndex(1)
                    self.ui.scrollAreaWidgetContents_character_ai_search.layout().addWidget(main_widget)
                asyncio.create_task(load_characters())
            case 1:
                async def fetch_searched_character_card():
                    searched_characters = await self.character_card_client.search_character(character_name)
                    return searched_characters

                async def load_characters():
                    searched_characters = await fetch_searched_character_card()
                    main_widget = self.create_main_widget_for_character_card(searched_characters)
                    
                    layout = self.ui.scrollAreaWidgetContents_character_card_search.layout()
                    while layout.count():
                        item = layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()

                    self.ui.stackedWidget_character_card_gateway.setCurrentIndex(1)
                    self.ui.scrollAreaWidgetContents_character_card_search.layout().addWidget(main_widget)
                asyncio.create_task(load_characters())

    def create_character_card(self, character_name, character_title, avatar_path, downloads, likes, character_id, character_description, character_personality, character_first_message):
        widget = QFrame()
        widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        widget.setStyleSheet("""
            QFrame {
                background-color: #2c2f33;
                border-radius: 10px;
                padding: 5px;
                margin: 5px;
                width: 300px;
                height: 120px;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 14px;
            }
            QPushButton#AddToCharacterAI {
                background-color: #253b6e;
                color: #dcdfe3;
            }
            QPushButton#AddToCharacterAI:hover {
                background-color: #284b82;
            }
            QPushButton#AddToCharacterAI:pressed {
	            background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToMistralAI {
                background-color: #663007;
                color: #dcdfe3;
            }
            QPushButton#AddToMistralAI:hover {
                background-color: #663d1e;
            }
            QPushButton#AddToMistralAI:pressed {
	            background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToLocalLLM {
                background-color: #134f02;
                color: #dcdfe3;
            }
            QPushButton#AddToLocalLLM:hover {
                background-color: #264d1c;
            }
            QPushButton#AddToLocalLLM:pressed {
	            background-color: rgb(39, 44, 54);
            }
        """)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        avatar_label = QLabel()
        avatar_label.setFixedSize(130, 160)
        avatar_label.setStyleSheet("border-radius: 10px;")
        if avatar_path:
            pixmap = QPixmap(avatar_path).scaled(130, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_label.setPixmap(pixmap)
        else:
            avatar_label.setStyleSheet("background-color: #23272a;")
            avatar_label.setText("[Avatar]")
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar_label)

        right_layout = QVBoxLayout()
        name_label = QLabel(character_name)
        name_label.setStyleSheet("font-weight: bold; font-size: 17px;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        right_layout.addWidget(name_label)

        description_label = QLabel(character_title)
        description_label.setWordWrap(True)
        description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        description_label.setStyleSheet("font-size: 12px; color: #b9bbbe;")
        right_layout.addWidget(description_label)

        stats_layout = QHBoxLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        if likes is not None:
            likes_label = QLabel(f"\u2764 {likes}")
            likes_label.setStyleSheet("font-size: 12px; color: #e62929;")
            stats_layout.addWidget(likes_label)

        downloads_label = QLabel(f"\ud83d\udcbe {downloads}")
        downloads_label.setStyleSheet("font-size: 12px; color: #6880ba;")
        stats_layout.addWidget(downloads_label)

        right_layout.addLayout(stats_layout)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(3)

        add_to_cai_button = QPushButton(self.tr("Add to Character AI"))
        add_to_cai_button.setObjectName("AddToCharacterAI")
        add_to_cai_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_cai_button.clicked.connect(lambda: self.add_character_from_cai_gateway_sync(character_id))
        button_layout.addWidget(add_to_cai_button)

        add_to_mistral_button = QPushButton(self.tr("Add to Mistral AI"))
        add_to_mistral_button.setObjectName("AddToMistralAI")
        add_to_mistral_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        async def fetch_information_mistral():
            character_name, character_title, greeting_message, character_avatar = await self.character_ai_client.fetch_character_information(character_id)
            self.add_character_from_gateway(character_name, character_title=character_title, character_avatar_directory=character_avatar, character_description=character_title, character_personality=None, character_first_message=greeting_message, conversation_method="Mistral AI")

        add_to_mistral_button.clicked.connect(lambda: asyncio.create_task(fetch_information_mistral()))
        button_layout.addWidget(add_to_mistral_button)

        add_to_local_button = QPushButton(self.tr("Add to Local LLM"))
        add_to_local_button.setObjectName("AddToLocalLLM")
        add_to_local_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        async def fetch_information_local_llm():
            character_name, character_title, greeting_message, character_avatar = await self.character_ai_client.fetch_character_information(character_id)
            self.add_character_from_gateway(character_name, character_title=character_title, character_avatar_directory=character_avatar, character_description=character_title, character_personality=None, character_first_message=greeting_message, conversation_method="Local LLM")

        add_to_local_button.clicked.connect(lambda: asyncio.create_task(fetch_information_local_llm()))
        button_layout.addWidget(add_to_local_button)

        right_layout.addLayout(button_layout)
        layout.addLayout(right_layout)
        widget.setLayout(layout)
        return widget

    def create_horizontal_scroll_area(self, character_data):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:horizontal {
                background-color: rgb(39, 44, 54);
                height: 10px;
                margin: 0px 20px 0px 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: rgb(50, 55, 65);
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: rgb(50, 55, 65);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)

        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        async def load_characters():
            for character in character_data:
                character_name = character.get("character_name", "No name")
                character_title = character.get("character_title", "No title")
                character_avatar = character.get("character_avatar", "No avatar")
                character_description = character.get("character_description", "No description")
                character_personality = character.get("character_definition", "No personality")
                character_first_message = character.get("character_first_message", "No first message")

                character_avatar_url = None
                if character_avatar is not None:
                    try:
                        character_avatar_url = character_avatar.get_url()
                    except AttributeError:
                        print(f"Avatar for {character_name} does not have a valid URL.")

                downloads = character.get("downloads", "0")
                likes = character.get("likes", "0")
                character_id = character.get("character_id")
                avatar_path = None
                if character_avatar_url:
                    try:
                        avatar_path = await self.character_ai_client.load_image(character_avatar_url)
                    except Exception as e:
                        print(f"Error loading avatar for {character_name}: {e}")
                else:
                    print(f"No avatar found for {character_name}")

                card = self.create_character_card(
                    character_name, character_title, avatar_path, downloads, likes, character_id, character_description, character_personality, character_first_message
                )
                layout.addWidget(card)

            spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
            layout.addSpacerItem(spacer)

            container.setLayout(layout)
            scroll_area.setWidget(container)

        asyncio.ensure_future(load_characters())

        return scroll_area

    def create_main_widget(self, character_data, character_data_2):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 5, 15, 5)
        main_layout.setSpacing(10)
        main_widget.setStyleSheet("background-color: rgb(27,27,27);")

        recommendations_label = QLabel(self.tr("Featured"))
        recommendations_label.setStyleSheet("font-weight: bold; font-size: 18px; color: white;")
        main_layout.addWidget(recommendations_label)

        recommended_characters = []

        for character_information in character_data:
            recommended_characters.append({
                'character_name': character_information.name,
                'character_title': character_information.title,
                'character_first_message': character_information.greeting,
                'character_description': character_information.description,
                'character_definition': character_information.definition,
                'character_avatar': character_information.avatar,
                'character_id': character_information.character_id,
                'downloads': character_information.num_interactions,
                'likes': None
            })

        recommendations_scroll = self.create_horizontal_scroll_area(recommended_characters)
        main_layout.addWidget(recommendations_scroll)

        trending_label = QLabel(self.tr("Trending"))
        trending_label.setStyleSheet("font-weight: bold; font-size: 18px; color: white;")
        main_layout.addWidget(trending_label)

        trending_characters = []

        for character_information in character_data_2:
            trending_characters.append({
                'character_name': character_information.name,
                'character_title': character_information.title,
                'character_first_message': character_information.greeting,
                'character_description': character_information.description,
                'character_definition': character_information.definition,
                'character_avatar': character_information.avatar,
                'character_id': character_information.character_id,
                'downloads': character_information.num_interactions,
                'likes': None
            })

        trending_scroll = self.create_horizontal_scroll_area(trending_characters)
        main_layout.addWidget(trending_scroll)

        main_widget.setLayout(main_layout)
        return main_widget

    def create_searched_character_card(self, character_name, character_title, avatar_path, downloads, likes, character_id, character_description, character_personality, character_first_message):
        widget = QFrame()
        widget.setFixedSize(305, 350)
        widget.setStyleSheet("""
            QFrame {
                background-color: #2c2f33;
                border-radius: 10px;
                padding: 2px;
                margin: 2px;
                width: 200px;
                height: 300px;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 14px;
            }
            QPushButton#AddToCharacterAI {
                background-color: #253b6e;
                color: #dcdfe3;
            }
            QPushButton#AddToCharacterAI:hover {
                background-color: #284b82;
            }
            QPushButton#AddToCharacterAI:pressed {
                background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToMistralAI {
                background-color: #663007;
                color: #dcdfe3;
            }
            QPushButton#AddToMistralAI:hover {
                background-color: #663d1e;
            }
            QPushButton#AddToMistralAI:pressed {
                background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToLocalLLM {
                background-color: #134f02;
                color: #dcdfe3;
            }
            QPushButton#AddToLocalLLM:hover {
                background-color: #264d1c;
            }
            QPushButton#AddToLocalLLM:pressed {
                background-color: rgb(39, 44, 54);
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        avatar_container = QWidget()
        avatar_container.setFixedSize(287, 150)
        avatar_container.setStyleSheet("""
            background-color: rgb(27,27,27);
            border-radius: 10px;
        """)
        avatar_layout = QVBoxLayout()
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        avatar_label = QLabel()
        avatar_label.setFixedSize(120, 120)
        avatar_label.setStyleSheet("border-radius: 10px;")
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if avatar_path:
            pixmap = QPixmap(avatar_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            avatar_label.setPixmap(pixmap)
        else:
            avatar_label.setStyleSheet("background-color: #23272a;")
            avatar_label.setText("[Avatar]")

        avatar_layout.addWidget(avatar_label)
        avatar_container.setLayout(avatar_layout)
        layout.addWidget(avatar_container)

        right_layout = QVBoxLayout()

        name_label = QLabel(character_name)
        name_label.setStyleSheet("font-weight: bold; font-size: 17px;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(name_label)

        description_label = QLabel(character_title)
        description_label.setWordWrap(True)
        description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        description_label.setStyleSheet("font-size: 12px; color: #b9bbbe;")
        right_layout.addWidget(description_label)

        stats_layout = QHBoxLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if likes is not None:
            likes_label = QLabel(f"\u2764 {likes}")
            likes_label.setStyleSheet("font-size: 12px; color: #e62929;")
            stats_layout.addWidget(likes_label)

        downloads_label = QLabel(f"\ud83d\udcbe {downloads}")
        downloads_label.setStyleSheet("font-size: 12px; color: #6880ba;")
        stats_layout.addWidget(downloads_label)

        right_layout.addLayout(stats_layout)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)

        add_to_cai_button = QPushButton(self.tr("Add to Character AI"))
        add_to_cai_button.setObjectName("AddToCharacterAI")
        add_to_cai_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_cai_button.clicked.connect(lambda: self.add_character_from_cai_gateway_sync(character_id))
        button_layout.addWidget(add_to_cai_button)

        add_to_mistral_button = QPushButton(self.tr("Add to Mistral AI"))
        add_to_mistral_button.setObjectName("AddToMistralAI")
        add_to_mistral_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_mistral_button.clicked.connect(lambda: self.add_character_from_gateway(character_name, avatar_path, character_description, character_personality, character_first_message, conversation_method="Mistral AI"))
        button_layout.addWidget(add_to_mistral_button)

        add_to_local_button = QPushButton(self.tr("Add to Local LLM"))
        add_to_local_button.setObjectName("AddToLocalLLM")
        add_to_local_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_local_button.clicked.connect(lambda: self.add_character_from_gateway(character_name, avatar_path, character_description, character_personality, character_first_message, conversation_method="Local LLM"))
        button_layout.addWidget(add_to_local_button)

        right_layout.addLayout(button_layout)
        layout.addLayout(right_layout)

        widget.setLayout(layout)
        return widget

    def create_vertical_search_scroll_area(self, character_data):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgb(39, 44, 54);
                width: 10px;
                margin: 20px 0px 20px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: rgb(50, 55, 65);
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgb(50, 55, 65);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        container = QWidget()
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(10)
        container.setLayout(grid_layout)
        scroll_area.setWidget(container)

        batch_size = 9
        current_index = 0

        async def load_next_batch():
            nonlocal current_index
            next_index = min(current_index + batch_size, len(character_data))

            for index in range(current_index, next_index):
                character = character_data[index]
                character_name = character.get("character_name", "No name")
                character_title = character.get("character_title", "No title")
                character_avatar = character.get("character_avatar", "No avatar")
                character_description = character.get("character_description", "No description")
                character_personality = character.get("character_definition", "No personality")
                character_first_message = character.get("character_first_message", "No first message")

                character_avatar_url = None
                if character_avatar is not None:
                    try:
                        character_avatar_url = character_avatar.get_url()
                    except AttributeError:
                        print(f"Avatar for {character_name} does not have a valid URL.")

                downloads = int(float(character.get("downloads", "0")))
                likes = character.get("likes", "0")
                character_id = character.get("character_id")
                avatar_path = None
                if character_avatar_url:
                    try:
                        avatar_path = await self.character_ai_client.load_image(character_avatar_url)
                    except Exception as e:
                        print(f"Error loading avatar for {character_name}: {e}")
                else:
                    print(f"No avatar found for {character_name}")

                card = self.create_searched_character_card(
                    character_name, character_title, avatar_path, downloads, likes, character_id, character_description, character_personality, character_first_message
                )

                row = index // 3
                col = index % 3
                grid_layout.addWidget(card, row, col)

                QtWidgets.QApplication.processEvents()

            current_index = next_index

        async def handle_scroll():
            if scroll_area.verticalScrollBar().value() == scroll_area.verticalScrollBar().maximum():
                await load_next_batch()

        asyncio.create_task(load_next_batch())

        scroll_area.verticalScrollBar().valueChanged.connect(lambda: asyncio.create_task(handle_scroll()))
        return scroll_area

    def create_main_widget_search(self, character_data):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        main_widget.setStyleSheet("background-color: rgb(27,27,27);")

        search_label = QLabel(self.tr("Characters by request"))
        search_label.setStyleSheet("font-weight: bold; font-size: 18px; color: white;")
        main_layout.addWidget(search_label)

        searched_characters = []

        for character_information in character_data:
            searched_characters.append({
                'character_name': character_information.name,
                'character_title': character_information.title,
                'character_first_message': character_information.greeting,
                'character_description': character_information.description,
                'character_definition': character_information.definition,
                'character_avatar': character_information.avatar,
                'character_id': character_information.character_id,
                'downloads': character_information.num_interactions,
                'likes': None
            })

        search_scroll = self.create_vertical_search_scroll_area(searched_characters)
        main_layout.addWidget(search_scroll)

        main_widget.setLayout(main_layout)
        return main_widget

    def create_character_card_for_character_card(self, character_name, character_title, avatar_path, downloads, likes, total_tokens, character_description, character_personality, first_message):
        widget = QFrame()
        widget.setFixedSize(305, 350)
        widget.setStyleSheet("""
            QFrame {
                background-color: #2c2f33;
                border-radius: 10px;
                padding: 2px;
                margin: 2px;
                width: 200px;
                height: 300px;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                padding: 3px 8px;
                font-size: 14px;
            }
            QPushButton#AddToCharacterAI {
                background-color: #253b6e;
                color: #dcdfe3;
            }
            QPushButton#AddToCharacterAI:hover {
                background-color: #284b82;
            }
            QPushButton#AddToCharacterAI:pressed {
                background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToMistralAI {
                background-color: #663007;
                color: #dcdfe3;
            }
            QPushButton#AddToMistralAI:hover {
                background-color: #663d1e;
            }
            QPushButton#AddToMistralAI:pressed {
                background-color: rgb(39, 44, 54);
            }
            QPushButton#AddToLocalLLM {
                background-color: #134f02;
                color: #dcdfe3;
            }
            QPushButton#AddToLocalLLM:hover {
                background-color: #264d1c;
            }
            QPushButton#AddToLocalLLM:pressed {
                background-color: rgb(39, 44, 54);
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        avatar_container = QWidget()
        avatar_container.setFixedSize(287, 150)
        avatar_container.setStyleSheet("""
            background-color: rgb(27,27,27);
            border-radius: 10px;
        """)
        avatar_layout = QVBoxLayout()
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        avatar_label = QLabel()
        avatar_label.setFixedSize(120, 120)
        avatar_label.setStyleSheet("border-radius: 10px;")
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if avatar_path:
            pixmap = QPixmap(avatar_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            avatar_label.setPixmap(pixmap)
        else:
            avatar_label.setStyleSheet("background-color: #23272a;")
            avatar_label.setText("[Avatar]")

        avatar_layout.addWidget(avatar_label)
        avatar_container.setLayout(avatar_layout)
        layout.addWidget(avatar_container)

        right_layout = QVBoxLayout()

        name_label = QLabel(character_name)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("font-weight: bold; font-size: 17px;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(name_label)

        def truncate_text(text, max_words):
            words = text.split()
            if len(words) > max_words:
                return " ".join(words[:max_words]) + "..."
            return text

        max_words = 10
        cropped_description = truncate_text(character_title, max_words)

        description_label = QLabel(cropped_description)
        description_label.setWordWrap(True)
        description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        description_label.setStyleSheet("font-size: 12px; color: #b9bbbe;")
        right_layout.addWidget(description_label)

        stats_layout = QHBoxLayout()
        stats_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if likes is not None:
            likes_label = QLabel(f"\u2764 {likes}")
            likes_label.setStyleSheet("font-size: 12px; color: #e62929;")
            stats_layout.addWidget(likes_label)

        downloads_label = QLabel(f"\ud83d\udcbe {downloads}")
        downloads_label.setStyleSheet("font-size: 12px; color: #6880ba;")
        stats_layout.addWidget(downloads_label)

        tokens_label = QLabel(f"\u2699 Total tokens: {total_tokens}")
        tokens_label.setStyleSheet("font-size: 12px;")
        stats_layout.addWidget(tokens_label)

        right_layout.addLayout(stats_layout)

        button_layout = QVBoxLayout()
        button_layout.setSpacing(5)

        add_to_mistral_button = QPushButton(self.tr("Add to Mistral AI"))
        add_to_mistral_button.setObjectName("AddToMistralAI")
        add_to_mistral_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_mistral_button.clicked.connect(lambda: self.add_character_from_gateway(character_name, character_title, avatar_path, character_description, character_personality, first_message, conversation_method="Mistral AI"))
        button_layout.addWidget(add_to_mistral_button)

        add_to_local_button = QPushButton(self.tr("Add to Local LLM"))
        add_to_local_button.setObjectName("AddToLocalLLM")
        add_to_local_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        add_to_local_button.clicked.connect(lambda: self.add_character_from_gateway(character_name, character_title, avatar_path, character_description, character_personality, first_message, conversation_method="Local LLM"))
        button_layout.addWidget(add_to_local_button)

        right_layout.addLayout(button_layout)
        layout.addLayout(right_layout)

        widget.setLayout(layout)
        return widget

    def create_vertical_characters_card_scroll_area(self, character_data):
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background-color: rgb(39, 44, 54);
                width: 10px;
                margin: 20px 0px 20px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: rgb(50, 55, 65);
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgb(50, 55, 65);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        container = QWidget()
        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(10)

        container.setLayout(grid_layout)
        scroll_area.setWidget(container)

        batch_size = 9
        current_index = 0

        async def load_next_batch():
            nonlocal current_index
            next_index = min(current_index + batch_size, len(character_data))

            for index in range(current_index, next_index):
                character = character_data[index]
                character_full_path = character.get("fullPath")
                character_name, character_title, character_avatar_url, downloads, likes, total_tokens, character_description, character_personality, first_message = await self.character_card_client.get_character_information(character_full_path)

                avatar_path = await self.character_ai_client.load_image_character_card(character_avatar_url)

                card = self.create_character_card_for_character_card(
                    character_name, character_title, avatar_path, downloads, likes, total_tokens, character_description, character_personality, first_message
                )

                row = index // 3
                col = index % 3
                grid_layout.addWidget(card, row, col)

                QtWidgets.QApplication.processEvents()

            current_index = next_index

        async def handle_scroll():
            if scroll_area.verticalScrollBar().value() == scroll_area.verticalScrollBar().maximum():
                await load_next_batch()

        asyncio.create_task(load_next_batch())

        scroll_area.verticalScrollBar().valueChanged.connect(
            lambda: asyncio.create_task(handle_scroll())
        )
        return scroll_area

    def create_main_widget_for_character_card(self, character_data):
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        main_widget.setStyleSheet("background-color: rgb(27,27,27);")

        cards_label = QLabel(self.tr("Characters by request"))
        cards_label.setStyleSheet("font-weight: bold; font-size: 18px; color: white;")
        main_layout.addWidget(cards_label)

        nodes = character_data.get("data", {}).get("nodes", [])
        information_characters = []
        
        for node in nodes[:50]:
            full_path = node.get('fullPath')

            if full_path is not None:
                information_characters.append({
                    'fullPath': full_path
                })
            else:
                print(f"Warning: 'fullPath' not found for character: {node['name']}")

        characters_card_scroll = self.create_vertical_characters_card_scroll_area(information_characters)
        main_layout.addWidget(characters_card_scroll)

        main_widget.setLayout(main_layout)
        return main_widget
    ### CHARACTER GATEWAY ==============================================================================

    ### INTERACTION WITH CHARACTER =====================================================================
    async def open_chat(self, character_name):
        """
        Opens a chat interface for the selected character, configuring the UI and settings based on the character's data.
        """
        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setSpacing(5)
        chat_widget = QWidget()
        chat_widget.setStyleSheet("background-color: transparent;")
        chat_widget.setLayout(self.chat_container)
        self.ui.scrollArea_chat.setWidget(chat_widget)

        # General settings
        sow_system_status = self.configuration_settings.get_main_setting("sow_system_status")
        translator = self.configuration_settings.get_main_setting("translator")
        target_language = self.configuration_settings.get_main_setting("target_language")
        translator_mode = self.configuration_settings.get_main_setting("translator_mode")
        
        # Load character-specific configuration
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        
        # Ensure the character has a default emotion set
        current_emotion = character_info.get("current_emotion")
        if not current_emotion:
            configuration_data["character_list"][character_name]["current_emotion"] = "neutral"
            self.configuration_characters.save_configuration_edit(configuration_data)
        
        # Load character-specific configuration again
        configuration_data = self.configuration_characters.load_configuration()
        character_info = configuration_data["character_list"][character_name]
        conversation_method = character_info.get("conversation_method")
        current_sow_system_mode = character_info.get("current_sow_system_mode", "Nothing")
        expression_images_folder = character_info.get("expression_images_folder", None)
        live2d_model_folder = character_info.get("live2d_model_folder", None)
        current_text_to_speech = character_info.get("current_text_to_speech", "Nothing")
        character_avatar = character_info.get("character_avatar")
        current_emotion = character_info.get("current_emotion")

        # If using Character AI, fetch the cached avatar
        if conversation_method == "Character AI":
            character_avatar = self.character_ai_client.get_from_cache(character_avatar)
        
        self.user_avatar = self.configuration_settings.get_user_data("user_avatar")
        if not self.user_avatar:
            self.user_avatar = ":/sowInterface/person.png"

        # Configure the main window layout based on the SOW system status and current SOW system mode
        if sow_system_status and current_sow_system_mode != "Nothing":
            self.main_window.setFixedSize(1730, 807)
            self.center()
            await asyncio.sleep(0.5)

            # Create a new widget for displaying emotions (Live2D or Images)
            self.expression_widget = QtWidgets.QWidget(parent=self.ui.centralwidget)
            self.expression_widget.setObjectName("expression_widget")
            self.expression_widget.setFixedSize(420, 750)
            self.expression_widget.setStyleSheet("background-color: #252525; border-radius: 10px;")

            # Set layout for expression_widget
            expression_layout = QtWidgets.QVBoxLayout(self.expression_widget)
            if current_sow_system_mode == "Live2D Model":
                expression_layout.setContentsMargins(0, 5, 0, 100)
            elif current_sow_system_mode == "Expressions Images":
                expression_layout.setContentsMargins(0, 0, 0, 0)
            expression_layout.setSpacing(0)

            # Create a QStackedWidget to switch between Live2D and emotion images
            self.stackedWidget_expressions = QtWidgets.QStackedWidget(parent=self.expression_widget)
            self.stackedWidget_expressions.setObjectName("stackedWidget_expressions")
            self.stackedWidget_expressions.setFixedSize(421, 710)

            if current_sow_system_mode == "Live2D Model":
                self.live2d_page = QtWidgets.QWidget()
                self.live2d_page.setObjectName("live2d_page")
                
                model_json_path = self.find_model_json(live2d_model_folder)
                self.update_model_json(model_json_path, self.emotion_resources)

                self.live2d_widget = Live2DWidget(model_path=model_json_path, character_name=character_name)
                self.live2d_widget.setFixedSize(411, 730)
                self.live2d_widget.setStyleSheet("background-color: transparent;")
                self.live2d_widget.setObjectName("live2d_widget")

                live2d_layout = QtWidgets.QVBoxLayout(self.live2d_page)
                live2d_layout.setContentsMargins(0, 0, 0, 20) # I need this! (Hi my dear reader)
                live2d_layout.addWidget(self.live2d_widget, alignment=Qt.AlignmentFlag.AlignCenter)
                self.stackedWidget_expressions.addWidget(self.live2d_page)
            elif current_sow_system_mode == "Expressions Images":
                self.expression_image_page = QtWidgets.QWidget()
                self.expression_image_page.setObjectName("expression_image_page")
                self.expression_image_label = QtWidgets.QLabel(parent=self.expression_image_page)
                self.expression_image_label.setText("")
                self.expression_image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                self.expression_image_label.setFixedSize(421, 711)
                self.expression_image_label.setObjectName("expression_image_label")

                expression_image_layout = QtWidgets.QVBoxLayout(self.expression_image_page)
                expression_image_layout.setContentsMargins(0, 5, 0, 20) # I need this! (Hi my dear reader)
                expression_image_layout.addWidget(self.expression_image_label)
                self.stackedWidget_expressions.addWidget(self.expression_image_page)

            expression_layout.addWidget(self.stackedWidget_expressions)
            self.stackedWidget_expressions.setCurrentIndex(0)

            if current_sow_system_mode == "Live2D Model":
                if self.ui.centralwidget.layout() is None:
                    central_layout = QtWidgets.QHBoxLayout(self.ui.centralwidget)
                    central_layout.setContentsMargins(0, 4, 10, 100)
                else:
                    central_layout = self.ui.centralwidget.layout()
                    central_layout.setContentsMargins(0, 4, 10, 100)
            elif current_sow_system_mode == "Expressions Images":
                if self.ui.centralwidget.layout() is None:
                    central_layout = QtWidgets.QHBoxLayout(self.ui.centralwidget)
                    central_layout.setContentsMargins(0, 4, 10, 100)
                else:
                    central_layout = self.ui.centralwidget.layout()
                    central_layout.setContentsMargins(0, 4, 10, 100)

            central_layout.addStretch(1)
            central_layout.addWidget(self.expression_widget)

            if current_sow_system_mode == "Expressions Images":
                self.show_emotion_image(expression_images_folder, character_name)
            elif current_sow_system_mode == "Live2D Model":
                model_json_path = self.find_model_json(live2d_model_folder)
                if model_json_path:
                    print(f"[detect_emotion] Model file found: {model_json_path}")
                    self.update_model_json(model_json_path, self.emotion_resources)
                    # Устанавливаем текущую страницу в stackedWidget_expressions на live2d_page
                    if self.stackedWidget_expressions is not None:
                        print("[detect_emotion] Switching to Live2D page...")
                        self.stackedWidget_expressions.setCurrentWidget(self.live2d_page)
                else:
                    print("[detect_emotion] Model file not found.")

            self.ui.bottom_bar.setMinimumSize(QtCore.QSize(1280, 16))
            self.ui.bottom_bar.setMaximumSize(QtCore.QSize(10000, 26))
            self.ui.bottom_bar.setGeometry(QtCore.QRect(5, 755, 1711, 16))

        def draw_circle_avatar(avatar_path):
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

        async def edit_message_dialog(conversation_method, message_id, character_name, original_text, parent=None):
            """
            Opens a dialog window to edit a message based on the conversation method.
            """
            dialog = QDialog(parent)
            dialog.setWindowTitle(self.tr("Edit Message"))
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

            layout = QVBoxLayout(dialog)
            edit_field = QtWidgets.QTextEdit(dialog)
            edit_field.setText(original_text)
            edit_field.setAcceptRichText(False)
            layout.addWidget(edit_field)

            save_button = QPushButton(self.tr("Save"), dialog)
            layout.addWidget(save_button)

            # Disconnect any existing connections to avoid multiple bindings
            try:
                save_button.clicked.disconnect()
            except TypeError:
                pass
            
            save_button.clicked.connect(dialog.accept)

            # Handle the dialog result based on the conversation method
            match conversation_method:
                case "Character AI":
                    message_id_str = str(message_id)
                    configuration_data = self.configuration_characters.load_configuration()
                    chat_id = configuration_data["character_list"][character_name]["chat_id"]
                    chat_content = configuration_data["character_list"][character_name]["chat_content"]
                    turn_id = chat_content[message_id_str]["turn_id"]
                    candidate_id = chat_content[message_id_str]["candidate_id"]

                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        edited_text = edit_field.toPlainText()
                        await self.character_ai_client.edit_message(character_name, message_id_str, chat_id, turn_id, candidate_id, edited_text)
                        return edited_text
                    else:
                        return None

                case "Mistral AI" | "Local LLM":
                    message_id_str = str(message_id)
                    configuration_data = self.configuration_characters.load_configuration()
                    chat_content = configuration_data["character_list"][character_name]["chat_content"]

                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        edited_text = edit_field.toPlainText()
                        self.configuration_characters.edit_chat_message(
                            message_id_str, character_name, edited_text, original_text
                        )
                        return edited_text
                    else:
                        return None

        async def handle_user_message(conversation_method, character_id, chat_id, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file):
            """
            Handles a user's message: sends it and retrieves a response from the character.

            Args:
                conversation_method (str): The method used for the conversation (e.g., "Character AI", "Mistral AI", "Local LLM").
                character_id (str): The ID of the character.
                chat_id (str): The ID of the chat session.
                character_ai_voice_id (str): The voice ID for Character AI.
                elevenlabs_voice_id (str): The voice ID for ElevenLabs.
                xttsv2_voice_type (str): The voice type for XTTSv2.
                xttsv2_rvc_enabled (bool): Whether RVC is enabled for XTTSv2.
                xttsv2_rvc_file (str): The RVC file path for XTTSv2.

            This function processes the user's input, translates it if necessary, and interacts with the selected AI model.
            """
            self.ui.textEdit_write_user_message.setDisabled(True)
            self.ui.pushButton_send_message.setDisabled(True)

            try:
                # Load user data (name and description) from settings
                user_name = self.configuration_settings.get_user_data("user_name")
                user_description = self.configuration_settings.get_user_data("user_description")

                # Get the user's original message and strip whitespace
                user_text_original = self.ui.textEdit_write_user_message.toPlainText().strip()
                user_text = user_text_original

                # Translate the user's message based on the selected translator and translator mode
                match translator:
                    case 0:
                        # No translation needed
                        pass
                    case 1:
                        # Use Google Translate
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
                        # Use Yandex Translate
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
                        # Use local translation
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
                
                # Convert the user's text to Markdown HTML format
                user_text_markdown = markdown_to_html(user_text_original)
                
                if user_text:
                    await add_message(user_text_markdown, is_user=True)
                    await asyncio.sleep(0.05)
                    self.ui.textEdit_write_user_message.clear()
                    
                    match conversation_method:
                        case "Character AI": # Process the message using Character AI
                            # Add an empty message container for the character's response
                            character_answer_container = await add_message("", is_user=False)
                            character_answer_label = character_answer_container["label"]

                            # Initialize variables to store the full response and metadata
                            full_text = ""
                            turn_id = ""
                            candidate_id = ""

                            # Send the user's message to Character AI and process the response
                            async for message in self.character_ai_client.send_message(character_id, chat_id, user_text):
                                text = message.get_primary_candidate().text
                                turn_id = message.turn_id
                                candidate_id = message.get_primary_candidate().candidate_id
                                
                                
                                if text != full_text:
                                    full_text = text
                                    original_text = text
                                    full_text = markdown_to_html(full_text)
                                    character_answer_label.setText(full_text)
                                    await asyncio.sleep(0.05)
                                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                            # Handle emotion detection based on SOW system status
                            match sow_system_status:
                                case False:
                                    pass # No emotion detection
                                case True:
                                    match current_sow_system_mode:
                                        case "Nothing":
                                            pass
                                        case "Expressions Images" | "Live2D Model":
                                            asyncio.create_task(self.detect_emotion(character_name, original_text)) # Detect and display the character's emotion

                            match translator:
                                case 0:
                                    pass
                                case 1:
                                    # Google Translate
                                    match translator_mode:
                                        case 0:
                                            if target_language == 0:
                                                full_text = self.translator.translate(full_text, "google", 'ru')
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                                        case 1:
                                            pass
                                        case 2:
                                            if target_language == 0:
                                                full_text = self.translator.translate(full_text, "google", 'ru')
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                                case 2:
                                    # Yandex Translate
                                    match translator_mode:
                                        case 0:
                                            if target_language == 0:
                                                full_text = self.translator.translate(full_text, "yandex", "ru")
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                                        case 1:
                                            pass
                                        case 2:
                                            if target_language == 0:
                                                full_text = self.translator.translate(full_text, "yandex", "ru")
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                                case 3:
                                    # Local translation
                                    match translator_mode:
                                        case 0:
                                            if target_language == 0:
                                                full_text = self.translator.translate_local(full_text, "en", "ru")
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                                        case 1:
                                            pass
                                        case 2:
                                            if target_language == 0:
                                                full_text = self.translator.translate_local(full_text, "en", "ru")
                                                character_answer_label.setText(full_text)
                                            else:
                                                pass
                            
                            # Handle text-to-speech generation
                            match current_text_to_speech:
                                case "Nothing" | None:
                                    pass # No text-to-speech generation
                                case "Character AI":
                                    await asyncio.sleep(0.05)
                                    await self.character_ai_client.generate_speech(chat_id, turn_id, candidate_id, character_ai_voice_id)
                                case "ElevenLabs":
                                    await asyncio.sleep(0.05)
                                    await self.eleven_labs_client.generate_speech_with_elevenlabs(text, elevenlabs_voice_id)
                                case "XTTSv2":
                                    if translator != 0:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=character_name)
                                    else:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=character_name)

                            # Fetch and update the chat history for the character
                            await self.character_ai_client.fetch_chat(
                                    chat_id, character_name, character_id, character_avatar_url, character_title,
                                    character_description, character_personality, first_message, current_text_to_speech,
                                    voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled,
                                    xttsv2_rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                                    conversation_method, current_emotion
                                    )

                        case "Mistral AI": # Process the message using Mistral AI
                            configuration_data = self.configuration_characters.load_configuration()
                            character_data = configuration_data["character_list"].get(character_name)
                            system_prompt = character_data["system_prompt"]
                            chat_history = character_data.get("chat_history", [])

                            # Build the context from the chat history (last 10 messages)
                            context_messages = []
                            for message in chat_history:
                                user_message = message.get("user", "")
                                character_message = message.get("character", "")
                                if user_message:
                                    context_messages.append(f"{user_name}: {user_message}")
                                if character_message:
                                    context_messages.append(f"{character_name}: {character_message}")
                            context_messages = context_messages[-10:]
                            context = "\n".join(context_messages)

                            # Construct the final system prompt and user message
                            final_system_prompt = (
                                f"[INST] {system_prompt} [/INST]\n\n"
                                f"Context of dialogue:\n{context}\n\n"
                                f"Information about User:\nName: {user_name},\nDescription: {user_description}\n\n"
                            )
                            final_user_message = f"Current message:\nUser: {user_text}"

                            answer_generator = self.mistral_ai_client.send_message(final_user_message, final_system_prompt, character_name, user_name)

                            character_answer_container = await add_message("", is_user=False)
                            character_answer_label = character_answer_container["label"]

                            full_text = ""
                            async for message in answer_generator:
                                if message:
                                    full_text += message
                                    full_text_html = markdown_to_html(full_text)
                                    character_answer_label.setText(full_text_html)
                                    await asyncio.sleep(0.05)
                                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                            if full_text_html.startswith(f"{character_name}:"):
                                full_text_html = full_text_html[len(f"{character_name}:"):].lstrip()

                            full_text_html = (
                                full_text_html.replace("{{user}}", user_name)
                                .replace("{{char}}", character_name)
                                .replace("{{User}}", user_name)
                                .replace("{{Char}}", character_name)
                                .replace("{{пользователь}}", user_name)
                                .replace("{{персонаж}}", character_name)
                                .replace("{{шар}}", character_name)
                                .replace("{{символ}}", character_name)
                            )
                            character_answer_label.setText(full_text_html)

                            # Handle emotion detection based on SOW system status
                            match sow_system_status:
                                case False:
                                    pass # No emotion detection
                                case True:
                                    match current_sow_system_mode:
                                        case "Nothing":
                                            pass
                                        case "Expressions Images" | "Live2D Model":
                                            asyncio.create_task(self.detect_emotion(character_name, full_text)) # Detect and display the character's emotion

                            self.configuration_characters.add_message_to_chat_content(character_name, "User", True, user_text)
                            self.configuration_characters.add_message_to_chat_content(character_name, character_name, False, full_text)
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
                            
                            # Handle text-to-speech generation
                            match current_text_to_speech:
                                case "Nothing" | None:
                                    pass
                                case "ElevenLabs":
                                    await asyncio.sleep(0.05)
                                    await self.eleven_labs_client.generate_speech_with_elevenlabs(text, elevenlabs_voice_id)
                                case "XTTSv2":
                                    if translator != 0:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=character_name)
                                    else:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=character_name)

                        case "Local LLM": # Process the message using Local LLM
                            configuration_data = self.configuration_characters.load_configuration()
                            character_data = configuration_data["character_list"].get(character_name)
                            system_prompt = character_data["system_prompt"]
                            chat_history = character_data.get("chat_history", [])

                            # Build the context from the chat history (last 20 messages)
                            context_messages = []
                            for message in chat_history:
                                user_message = message.get("user", "")
                                character_message = message.get("character", "")
                                if user_message:
                                    context_messages.append(f"<start_of_turn>user\n{user_name}: {user_message}</start_of_turn>")
                                if character_message:
                                    context_messages.append(f"<start_of_turn>model\n{character_name}: {character_message}</start_of_turn>")
                            context_messages = context_messages[-20:]
                            context = "\n".join(context_messages)

                            character_answer_container = await add_message("", is_user=False)
                            character_answer_label = character_answer_container["label"]

                            full_text = ""
                            full_text_html = ""
                            async for chunk in self.local_ai_client.send_message(system_prompt, context, user_text, character_name, user_name):
                                if chunk:
                                    full_text += chunk
                                    full_text_html = markdown_to_html(full_text)
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
                                              .replace("{{персонаж}}", character_name)
                                              .replace("{{шар}}", character_name)
                                              .replace("{{символ}}", character_name)
                            )
                            character_answer_label.setText(full_text_html)

                            # Handle emotion detection based on SOW system status
                            match sow_system_status:
                                case False:
                                    pass # No emotion detection
                                case True:
                                    match current_sow_system_mode:
                                        case "Nothing":
                                            pass
                                        case "Expressions Images" | "Live2D Model":
                                            asyncio.create_task(self.detect_emotion(character_name, full_text)) # Detect and display the character's emotion

                            self.configuration_characters.add_message_to_chat_content(character_name, "User", True, user_text)
                            self.configuration_characters.add_message_to_chat_content(character_name, character_name, False, full_text)
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

                            match current_text_to_speech:
                                case "Nothing" | None:
                                    pass
                                case "ElevenLabs":
                                    await asyncio.sleep(0.05)
                                    await self.eleven_labs_client.generate_speech_with_elevenlabs(text, elevenlabs_voice_id)
                                case "XTTSv2":
                                    if translator != 0:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="ru", character_name=character_name)
                                    else:
                                        await self.xttsv2_client.generate_speech_with_xttsv2(full_text, language="en", character_name=character_name)
            except Exception as e:
                error_message = traceback.format_exc()
                print(f"Error processing the message: {e}")
                print(f"Full error message: {error_message}")
            finally:
                self.ui.textEdit_write_user_message.setDisabled(False)
                self.ui.pushButton_send_message.setDisabled(False)

        def markdown_to_html(text):
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.*?)\*', r'<i><span style="color: #a3a3a3;">\1</span></i>', text)
            text = re.sub(r'__(.*?)__', r'<b>\1</b>', text)
            return text

        async def add_message(text, is_user, message_id=None):
            """
            Adds a message to the chat interface.
            """
            if message_id is None:
                message_id = len(self.messages) + 1

            # Load user data and convert the message text to Markdown formatting
            user_name = self.configuration_settings.get_user_data("user_name")
            if not user_name:
                user_name = "User"
            html_text = markdown_to_html(text)
            html_text = html_text.replace("{{user}}", user_name).replace("{{char}}", character_name)

            message_container = QHBoxLayout()
            message_container.setSpacing(5)
            message_container.setContentsMargins(10, 5, 10, 5)

            avatar_label = QLabel()

            # Create the message label with rich text formatting
            message_label = QLabel()
            message_label.setTextFormat(Qt.TextFormat.RichText)
            message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            message_label.setTextFormat(Qt.TextFormat.RichText)
            message_label.setText(html_text)
            message_label.setWordWrap(True)
            message_label.setFont(QFont("Arial", 20))

            small_name_label = QLabel()
            small_name_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
            small_name_label.setStyleSheet("font-size: 10px; color: gray;")

            message_frame = QFrame(None)
            message_frame.setStyleSheet("background-color: transparent; border-radius: 15px; padding: 0px;")
            message_frame.setLayout(message_container)

            # Configure the message appearance based on whether it's from the user or the character
            if is_user:
                # User message styling
                message_label.setStyleSheet(
                    "background-color: #384a69; color: white; border-radius: 15px; padding: 12px; font-size: 14px; margin: 5px; line-height: 2.4;"
                )
                avatar_pixmap = QPixmap(self.user_avatar)
            else:
                # Character message styling
                message_label.setStyleSheet(
                    "background-color: #222d40; color: white; border-radius: 15px; padding: 12px; font-size: 14px; margin: 5px; line-height: 2.4;"
                )
                avatar_pixmap = QPixmap(character_avatar)

            avatar_pixmap = avatar_pixmap.scaled(
                45, 45, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation
            )
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

            first_word = user_name.split()[0] if is_user else character_name.split()[0]
            small_name_label.setText(first_word)

            menu_button = QPushButton("···")
            menu_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border-radius: 15px;
                    padding: 8px;
                    font-size: 13px;
                    border: 2px solid transparent;
                }
                QPushButton:hover {
                    background-color: grey;
                    border-radius: 15px;
                }
            """)
            menu_button.setFixedSize(30, 30)
            menu_button.setFont(QFont("Arial", 12))
           
           # Disconnect any existing connections to avoid multiple bindings
            try:
                menu_button.clicked.disconnect()
            except TypeError:
                pass
            
            menu_button.clicked.connect(lambda: show_message_menu(menu_button, text, is_user, message_id))
            menu_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

            if is_user:
                message_container.addStretch()
                message_container.addWidget(avatar_label)
                message_container.addWidget(message_label)
                message_container.addWidget(small_name_label)
                message_container.addWidget(menu_button)
            else:
                message_container.addWidget(avatar_label)
                message_container.addWidget(message_label)
                message_container.addWidget(small_name_label)
                message_container.addWidget(menu_button)
                message_container.addStretch()

            self.chat_container.addWidget(message_frame)
            await asyncio.sleep(0.05)
            self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

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

        def show_message_menu(button, text, is_user, message_id):
            """
            Displays a context menu for a message (e.g., delete, edit, or continue from the message).
            """
            menu = QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2E3440;
                    color: #D8DEE9;
                    padding: 5px;
                }
                QMenu::item {
                    padding: 5px;
                    border-radius: 10px;
                    background-color: transparent;
                }
                QMenu::item:selected {
                    background-color: #4C566A;
                    border-radius: 10px;
                }
                QMenu::item:disabled {
                    border-radius: 10px;
                    color: #6E7A8A;
                }
            """)

            delete_action = QAction(self.tr("Delete"), None)
            edit_action = QAction(self.tr("Edit"), None)
            continue_action = QAction(self.tr("Continue from this message"), None)

            try:
                delete_action.triggered.disconnect()
                edit_action.triggered.disconnect()
                continue_action.triggered.disconnect()
            except TypeError:
                pass

            if is_user:
                delete_action.triggered.connect(lambda: asyncio.create_task(delete_message(conversation_method, message_id)))
                edit_action.triggered.connect(lambda: asyncio.create_task(edit_message(conversation_method, message_id, text)))
                continue_action.triggered.connect(lambda: asyncio.create_task(continue_dialog(conversation_method, message_id, character_name)))
                menu.addAction(delete_action)
                menu.addAction(edit_action)
                menu.addAction(continue_action)
            else:
                delete_action.triggered.connect(lambda: asyncio.create_task(delete_message(conversation_method, message_id)))
                edit_action.triggered.connect(lambda: asyncio.create_task(edit_message(conversation_method, message_id, text)))
                menu.addAction(delete_action)
                menu.addAction(edit_action)

            menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

        async def delete_message(conversation_method, message_id):
            """
            Deletes a message from the interface and the configuration file.
            """
            try:
                configuration_data = self.configuration_characters.load_configuration()

                if "character_list" not in configuration_data or character_name not in configuration_data["character_list"]:
                    print(f"Character '{character_name}' not found in the configuration.")
                    return

                chat_content = configuration_data["character_list"][character_name].get("chat_content", {})
                message_id_str = str(message_id)

                # Check if the message exists in the chat content
                if message_id_str not in chat_content:
                    print(f"Message with ID {message_id} not found in chat_content.")
                    return
                
                # Remove the message from the UI if it exists
                if message_id in self.messages:
                    self.messages[message_id]["frame"].deleteLater()
                    del self.messages[message_id]
                else:
                    print(f"Message with ID {message_id} not found in the interface.")
                    return

                match conversation_method:
                    case "Character AI":
                        turn_id = chat_content[message_id_str]["turn_id"]
                        chat_id = configuration_data["character_list"][character_name]["chat_id"]
                        await self.character_ai_client.delete_message(character_name, message_id_str, chat_id, turn_id)
                    case "Mistral AI" | "Local LLM":
                        self.configuration_characters.delete_chat_message(message_id_str, character_name)

            except Exception as e:
                print(f"Error deleting message: {e}")

        async def edit_message(conversation_method, message_id, original_text):
            """
            Edits a message in both the interface and the configuration file.
            """
            configuration_data = self.configuration_characters.load_configuration()

            if "character_list" not in configuration_data or character_name not in configuration_data["character_list"]:
                print(f"Character '{character_name}' not found in the configuration.")
                return

            chat_content = configuration_data["character_list"][character_name].get("chat_content", {})
            message_id_str = str(message_id)

            if message_id_str not in chat_content:
                print(f"Message with ID {message_id} not found in chat_content.")
                return

            new_text = await edit_message_dialog(conversation_method, message_id, character_name, original_text)
            if new_text is not None:
                if message_id in self.messages:
                    self.messages[message_id]["label"].setText(new_text)
                    self.messages[message_id]["text"] = new_text
                else:
                    print(f"Message with ID {message_id} not found in self.messages.")

        async def continue_dialog(conversation_method, message_id, character_name):
            """
            Deletes all messages that come after the specified message.
            """
            configuration_data = self.configuration_characters.load_configuration()
            character_list = configuration_data["character_list"]

            if character_name not in character_list:
                print(f"Character '{character_name}' not found in the configuration.")
                return

            chat_content = character_list[character_name]["chat_content"]

            match conversation_method:
                case "Character AI":
                    chat_id = configuration_data["character_list"][character_name]["chat_id"]

                    message_ids = []
                    turn_ids = []
                    for msg_id, msg_data in chat_content.items():
                        if int(msg_id) > message_id:
                            message_ids.append(str(msg_id))
                            turn_ids.append(msg_data["turn_id"])

                    for msg_id in list(self.messages.keys()):
                        if int(msg_id) > message_id:
                            self.messages[msg_id]["frame"].deleteLater()
                            del self.messages[msg_id]

                    await self.character_ai_client.delete_messages(character_name, message_ids, chat_id, turn_ids)

                    print(f"Dialog continued from: {self.messages[message_id]['text']}")
                    await asyncio.sleep(0.05)
                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

                case "Mistral AI" | "Local LLM":
                    message_ids = []
                    for msg_id, msg_data in chat_content.items():
                        if int(msg_id) > message_id:
                            message_ids.append(str(msg_id))

                    for msg_id in list(self.messages.keys()):
                        if int(msg_id) > message_id:
                            self.messages[msg_id]["frame"].deleteLater()
                            del self.messages[msg_id]

                    self.configuration_characters.delete_chat_messages(message_ids, character_name)

                    print(f"Dialog continued from: {self.messages[message_id]['text']}")
                    await asyncio.sleep(0.05)
                    self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

        def open_more_button(conversation_method, character_name, character_avatar, character_title, character_description, character_personality, first_message):
            """
            Opens a dialog with additional settings for the character.
            """
            # Create the dialog window
            dialog = QDialog()
            dialog.setWindowTitle(self.tr("Character Settings: ") + character_name)
            dialog.setMinimumSize(600, 650)
            dialog.setMaximumSize(600, 650)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: rgb(30, 30, 30);
                    border-radius: 10px;
                }
                QLineEdit, QTextEdit {
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
            """)

            layout = QVBoxLayout(dialog)

            # Add the character's avatar
            avatar_label = QLabel(dialog)
            avatar_pixmap = QPixmap(character_avatar).scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio)
            avatar_label.setPixmap(avatar_pixmap)
            avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(avatar_label)

            # Add the character's name
            name_label = QLabel(self.tr("Character Name: ") + character_name, dialog)
            name_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            name_label.setStyleSheet("""font: 14px "Muli Medium";""")
            layout.addWidget(name_label)

            separator = QFrame(dialog)
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setObjectName("separator")
            layout.addWidget(separator)

            # Display different fields based on the conversation method
            if conversation_method == "Character AI": # For Character AI: Display the character's title as read-only
                title_label = QLabel(self.tr("Character's Title:"), dialog)
                title_label.setStyleSheet("""font: 14px "Muli Medium";""")
                title_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
                layout.addWidget(title_label)

                title_edit = QLineEdit(character_title, dialog)
                title_edit.setReadOnly(True)
                title_edit.setAlignment(Qt.AlignmentFlag.AlignVCenter)
                title_edit.setStyleSheet("""background-color: rgb(50, 50, 50); font: 14px "Muli Medium";""")
                layout.addWidget(title_edit)
            else: # For Mistral AI and Local LLM: Display editable fields for description, personality, and first message
                description_label = QLabel(self.tr("Character Description:"), dialog)
                layout.addWidget(description_label)

                description_edit = QTextEdit(character_description, dialog)
                description_edit.setPlaceholderText(self.tr("Enter the character's description"))
                layout.addWidget(description_edit)

                personality_label = QLabel(self.tr("Character Personality:"), dialog)
                layout.addWidget(personality_label)

                personality_edit = QTextEdit(character_personality, dialog)
                personality_edit.setPlaceholderText(self.tr("Enter the character's personality traits"))
                layout.addWidget(personality_edit)

                first_message_label = QLabel(self.tr("Character First Message:"), dialog)
                layout.addWidget(first_message_label)

                first_message_edit = QTextEdit(first_message, dialog)
                first_message_edit.setPlaceholderText(self.tr("Enter the character's first message"))
                layout.addWidget(first_message_edit)

            separator = QFrame(dialog)
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setObjectName("separator")
            layout.addWidget(separator)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK", dialog)
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                ok_button.clicked.disconnect()
            except TypeError:
                pass
            
            ok_button.clicked.connect(dialog.close)
            button_layout.addWidget(ok_button)

            if conversation_method != "Character AI":
                save_button = QPushButton(self.tr("Save"), dialog)
                
                # Disconnect any existing connections to avoid multiple bindings
                try:
                    save_button.clicked.disconnect()
                except TypeError:
                    pass
                
                save_button.clicked.connect(lambda: save_changes(dialog, conversation_method, character_name, description_edit, personality_edit, first_message_edit))
                button_layout.addWidget(save_button)
            
            new_dialog_button = QPushButton(self.tr("Start New Dialogue with Character"), dialog)
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                new_dialog_button.clicked.disconnect()
            except TypeError:
                pass
            
            new_dialog_button.clicked.connect(
                lambda: asyncio.create_task(
                    start_new_dialog(
                        dialog, conversation_method, character_name,
                        description_edit if conversation_method != "Character AI" else None,
                        personality_edit if conversation_method != "Character AI" else None,
                        first_message_edit if conversation_method != "Character AI" else None
                    )
                )
            )
            button_layout.addWidget(new_dialog_button)
            layout.addLayout(button_layout)
            dialog.exec()

        def save_changes(dialog, conversation_method, character_name, description_edit, personality_edit, first_message_edit):
            """
            Saves changes to the configuration file for the specified character.
            """
            configuration_data = self.configuration_characters.load_configuration()
            character_list = configuration_data["character_list"]

            if character_name in character_list:
                if conversation_method != "Character AI":
                    character_list[character_name]["character_description"] = description_edit.toPlainText()
                    character_list[character_name]["character_personality"] = personality_edit.toPlainText()
                    character_list[character_name]["first_message"] = first_message_edit.toPlainText()
                else:
                    pass

                configuration_data["character_list"] = character_list
                self.configuration_characters.save_configuration_edit(configuration_data)

                # Show a success message
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("Saved"))
                message_box_information.setText(self.tr("The changes were saved successfully!"))
                message_box_information.exec()
            else:
                # Show an error message if the character is not found
                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle(self.tr("Saving Error"))
                message_box_information.setText(self.tr("Character was not found in the configuration."))
                message_box_information.exec()

            dialog.close()

        async def start_new_dialog(dialog, conversation_method, character_name, description_edit, personality_edit, first_message_edit):
            """
            Starts a new dialogue with the character by clearing the previous chat history.
            """
            reply = QMessageBox.question(
                dialog, 
                self.tr("Start New Dialogue"), 
                self.tr("Are you sure you want to start a new dialogue? The previous dialogue will be deleted."), 
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Handle the creation of a new dialogue based on the conversation method
                match conversation_method:
                    case "Character AI":
                        character_data = self.configuration_characters.load_configuration()
                        character_list = character_data.get("character_list", {})
                        character_id = character_list[character_name]["character_id"]
                        await self.character_ai_client.create_new_chat(character_id)

                    case "Mistral AI" | "Local LLM":
                        new_description = description_edit.toPlainText()
                        new_personality = personality_edit.toPlainText()
                        new_first_message = first_message_edit.toPlainText()
                        self.configuration_characters.create_new_chat(character_name, conversation_method, new_description, new_personality, new_first_message)

                self.messages.clear()
                while self.chat_container.count():
                    item = self.chat_container.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

                self.ui.stackedWidget.setCurrentIndex(1)

                message_box_information = QMessageBox()
                message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                message_box_information.setWindowTitle("New Chat")
                message_box_information.setText(self.tr("A new dialogue has been successfully started!"))
                message_box_information.exec()
            
            dialog.close()
            await self.close_chat()
            self.main_window.updateGeometry()

        def clear_mode(conversation_method, character_id, chat_id):
            """
            Mode without text-to-speech or emotions.
            """
            def handle_user_message_sync():
                asyncio.create_task(
                    handle_user_message(
                        conversation_method, 
                        character_id, 
                        chat_id, 
                        character_ai_voice_id=None, 
                        elevenlabs_voice_id=None, 
                        xttsv2_voice_type=None, 
                        xttsv2_rvc_enabled=None, 
                        xttsv2_rvc_file=None
                    )
                )
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                self.ui.pushButton_send_message.clicked.disconnect()
            except TypeError:
                pass

            self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
            self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)

        def clear_text_to_speech_mode(conversation_method, character_id, chat_id, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file):
            """
            Mode with text-to-speech but without calls and emotions.
            """
            def handle_user_message_sync():
                asyncio.create_task(
                    handle_user_message(
                        conversation_method,
                        character_id,
                        chat_id,
                        character_ai_voice_id,
                        elevenlabs_voice_id,
                        xttsv2_voice_type,
                        xttsv2_rvc_enabled,
                        xttsv2_rvc_file
                    )
                )
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                self.ui.pushButton_send_message.clicked.disconnect()
                self.ui.pushButton_call.clicked.disconnect()
            except TypeError:
                pass

            self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.ui.pushButton_call.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
            self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)

        def clear_expression_mode(conversation_method, character_id, chat_id, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file):
            """
            Mode without text-to-speech or calls but with emotions.
            """
            def handle_user_message_sync():
                asyncio.create_task(
                    handle_user_message(
                        conversation_method,
                        character_id,
                        chat_id,
                        character_ai_voice_id,
                        elevenlabs_voice_id,
                        xttsv2_voice_type,
                        xttsv2_rvc_enabled,
                        xttsv2_rvc_file
                    )
                )
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                self.ui.pushButton_send_message.clicked.disconnect()
            except TypeError:
                pass

            self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.ForbiddenCursor)
            self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)

        def full_mode(conversation_method, character_id, chat_id, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file):
            """
            Full mode with text-to-speech, calls, and emotions.
            """
            def handle_user_message_sync():
                asyncio.create_task(
                    handle_user_message(
                        conversation_method,
                        character_id,
                        chat_id,
                        character_ai_voice_id,
                        elevenlabs_voice_id,
                        xttsv2_voice_type,
                        xttsv2_rvc_enabled,
                        xttsv2_rvc_file
                    )
                )
            
            # Disconnect any existing connections to avoid multiple bindings
            try:
                self.ui.pushButton_send_message.clicked.disconnect()
                self.ui.pushButton_call.clicked.disconnect()
            except TypeError:
                pass

            self.ui.pushButton_call.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            self.ui.pushButton_call.clicked.connect(lambda: asyncio.create_task(self.open_sow_system(character_name)))
            self.ui.pushButton_send_message.clicked.connect(handle_user_message_sync)

        match conversation_method:
            case "Character AI":
                """
                Handles the setup for a Character AI-based conversation.
                """
                character_data = self.configuration_characters.load_configuration()
                if "character_list" not in character_data or character_name not in character_data["character_list"]:
                    print(f"Character '{character_name}' not found in the configuration.")
                    return

                # Extract character-specific information
                character_info = character_data["character_list"][character_name]
                character_id = character_info.get("character_id")
                chat_id = character_info.get("chat_id")
                character_avatar_url = character_info.get("character_avatar")
                character_title = character_info.get("character_title")
                character_description = character_info.get("character_description")
                character_personality = character_info.get("character_personality")
                first_message = character_info.get("first_message")
                chat_content = character_info.get("chat_content", {})

                # Retrieve voice-related data for the character
                voice_name = character_info.get("voice_name")
                character_ai_voice_id = character_info.get("character_ai_voice_id")
                elevenlabs_voice_id = character_info.get("elevenlabs_voice_id")
                xttsv2_voice_type = character_info.get("xttsv2_voice_type")
                xttsv2_rvc_enabled = character_info.get("xttsv2_rvc_enabled")
                xttsv2_rvc_file = character_info.get("xttsv2_rvc_file")
                
                # Fetch the chat history from the Character AI client
                await self.character_ai_client.fetch_chat(
                            chat_id, character_name, character_id, character_avatar_url, character_title,
                            character_description, character_personality, first_message, current_text_to_speech,
                            voice_name, character_ai_voice_id, elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled,
                            xttsv2_rvc_file, current_sow_system_mode, expression_images_folder, live2d_model_folder,
                            conversation_method, current_emotion
                )

                # Update chat content after fetching the chat
                character_data = self.configuration_characters.load_configuration()
                chat_content = character_data["character_list"][character_name].get("chat_content", {})
                await asyncio.sleep(0.05)

                # Load and display the character's avatar
                character_avatar = self.character_ai_client.get_from_cache(character_avatar_url)
                draw_circle_avatar(character_avatar)

                # Set the character's name and description in the UI
                self.ui.character_name_chat.setText(character_name)
                self.ui.character_description_chat.setText(character_title)

                self.ui.stackedWidget.setCurrentIndex(6)

                # Disconnect any existing connections to avoid multiple bindings
                try:
                    self.ui.pushButton_more.clicked.disconnect()
                except TypeError:
                    pass

                self.ui.pushButton_more.clicked.connect(
                    lambda: open_more_button(
                        conversation_method, 
                        character_name, 
                        character_avatar, 
                        character_title,
                        character_description, 
                        character_personality, 
                        first_message
                    )
                )

                # Configure interaction modes based on text-to-speech and expression settings
                if current_text_to_speech == "Nothing" and current_sow_system_mode == "Nothing":
                    print("Condition 1 met")
                    clear_mode(conversation_method, character_id, chat_id)
                elif current_text_to_speech != "Nothing" and current_sow_system_mode == "Nothing":
                    print("Condition 2 met")
                    clear_text_to_speech_mode(
                        conversation_method, character_id, chat_id, character_ai_voice_id,
                        elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file
                    )
                elif current_text_to_speech == "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 3 met")
                    clear_expression_mode(
                        conversation_method, character_id, chat_id, character_ai_voice_id,
                        elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file
                    )
                elif current_text_to_speech != "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 4 met")
                    full_mode(
                        conversation_method, character_id, chat_id, character_ai_voice_id,
                        elevenlabs_voice_id, xttsv2_voice_type, xttsv2_rvc_enabled, xttsv2_rvc_file
                    )

                for message_id, message_data in chat_content.items():
                    text = message_data["text"]
                    is_user = message_data["is_user"]

                    if translator != 0:  # If translation is enabled
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

                    asyncio.create_task(add_message(text, is_user, int(message_id)))

            case "Mistral AI":
                """
                Handles the setup for a Mistral AI-based conversation.
                """
                character_data = self.configuration_characters.load_configuration()
                if "character_list" not in character_data or character_name not in character_data["character_list"]:
                    print(f"Character '{character_name}' not found in the configuration.")
                    return

                character_info = character_data["character_list"][character_name]

                # Character Data
                character_avatar = character_info["character_avatar"]
                character_title = character_info["character_title"]
                character_description = character_info["character_description"]
                character_personality = character_info["character_personality"]
                first_message = character_info["first_message"]
                chat_content = character_info["chat_content"]

                # Character Voice Data
                elevenlabs_voice_id = character_info["elevenlabs_voice_id"]
                xttsv2_voice_type = character_info["xttsv2_voice_type"]
                xttsv2_rvc_enabled = character_info["xttsv2_rvc_enabled"]
                xttsv2_rvc_file = character_info["xttsv2_rvc_file"]

                draw_circle_avatar(character_avatar)

                max_words = 10
                if character_title:
                    words = character_title.split()
                    if len(words) > max_words:
                        cropped_description = " ".join(words[:max_words]) + "..."
                        self.ui.character_description_chat.setText(cropped_description)
                    else:
                        cropped_description = character_title
                        self.ui.character_description_chat.setText(cropped_description)

                self.ui.character_name_chat.setText(character_name)

                self.ui.stackedWidget.setCurrentIndex(6)

                # Disconnect any existing connections to avoid multiple bindings
                try:
                    self.ui.pushButton_more.clicked.disconnect()
                except TypeError:
                    pass

                self.ui.pushButton_more.clicked.connect(
                    lambda: open_more_button(
                        conversation_method=conversation_method, 
                        character_name=character_name,
                        character_avatar=character_avatar, 
                        character_title=None,
                        character_description=character_description, 
                        character_personality=character_personality,
                        first_message=first_message
                    )
                )

                if current_text_to_speech and current_sow_system_mode == "Nothing":
                    print("Condition 1 met")
                    clear_mode(conversation_method, character_id=None, chat_id=None)
                elif current_text_to_speech != "Nothing" and current_sow_system_mode == "Nothing":
                    print("Condition 2 met")
                    clear_text_to_speech_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )
                elif current_text_to_speech == "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 3 met")
                    clear_expression_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )
                elif current_text_to_speech != "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 4 met")
                    full_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )

                for message_id, message_data in chat_content.items():
                    text = message_data["text"]
                    is_user = message_data["is_user"]

                    if translator != 0:  # If translation is enabled
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

                    asyncio.create_task(add_message(text, is_user, int(message_id)))

            case "Local LLM":
                """
                Handles the setup for a Local LLM-based conversation.
                """
                local_llm = self.configuration_settings.get_main_setting("local_llm")
                if local_llm is None:
                    message_box_information = QMessageBox()
                    message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
                    message_box_information.setWindowTitle(self.tr("No Local LLM"))
                    message_box_information.setText(self.tr("Choose Local LLM in the options."))
                    message_box_information.exec()
                    return

                character_data = self.configuration_characters.load_configuration()
                if "character_list" not in character_data or character_name not in character_data["character_list"]:
                    print(f"Character '{character_name}' not found in the configuration.")
                    return

                character_info = character_data["character_list"][character_name]

                # Character Data
                character_avatar = character_info["character_avatar"]
                character_title = character_info["character_title"]
                character_description = character_info["character_description"]
                character_personality = character_info["character_personality"]
                first_message = character_info["first_message"]
                chat_content = character_info["chat_content"]

                # Character Voice Data
                elevenlabs_voice_id = character_info["elevenlabs_voice_id"]
                xttsv2_voice_type = character_info["xttsv2_voice_type"]
                xttsv2_rvc_enabled = character_info["xttsv2_rvc_enabled"]
                xttsv2_rvc_file = character_info["xttsv2_rvc_file"]

                draw_circle_avatar(character_avatar)

                max_words = 10
                if character_title:
                    words = character_title.split()
                    if len(words) > max_words:
                        cropped_description = " ".join(words[:max_words]) + "..."
                        self.ui.character_description_chat.setText(cropped_description)
                    else:
                        cropped_description = character_title
                        self.ui.character_description_chat.setText(cropped_description)

                self.ui.character_name_chat.setText(character_name)

                self.ui.stackedWidget.setCurrentIndex(6)

                # Disconnect any existing connections to avoid multiple bindings
                try:
                    self.ui.pushButton_more.clicked.disconnect()
                except TypeError:
                    pass

                self.ui.pushButton_more.clicked.connect(
                    lambda: open_more_button(
                        conversation_method=conversation_method, 
                        character_name=character_name,
                        character_avatar=character_avatar, 
                        character_title=None,
                        character_description=character_description, 
                        character_personality=character_personality,
                        first_message=first_message
                    )
                )

                if current_text_to_speech and current_sow_system_mode == "Nothing":
                    print("Condition 1 met")
                    clear_mode(conversation_method, character_id=None, chat_id=None)
                elif current_text_to_speech != "Nothing" and current_sow_system_mode == "Nothing":
                    print("Condition 2 met")
                    clear_text_to_speech_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )
                elif current_text_to_speech == "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 3 met")
                    clear_expression_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )
                elif current_text_to_speech != "Nothing" and current_sow_system_mode != "Nothing":
                    print("Condition 4 met")
                    full_mode(
                        conversation_method,
                        character_id=None,
                        chat_id=None,
                        character_ai_voice_id=None,
                        elevenlabs_voice_id=elevenlabs_voice_id,
                        xttsv2_voice_type=xttsv2_voice_type,
                        xttsv2_rvc_enabled=xttsv2_rvc_enabled,
                        xttsv2_rvc_file=xttsv2_rvc_file,
                    )

                for message_id, message_data in chat_content.items():
                    text = message_data["text"]
                    is_user = message_data["is_user"]

                    if translator != 0:  # If translation is enabled
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

                    asyncio.create_task(add_message(text, is_user, int(message_id)))

    async def detect_emotion(self, character_name, text):
        """
        Detects emotion and updates the character's expression (image or Live2D model).
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]

        # Extract relevant settings for emotion detection
        expression_images_folder = character_information["expression_images_folder"]
        live2d_model_folder = character_information["live2d_model_folder"]
        current_sow_system_mode = character_information["current_sow_system_mode"]

        if current_sow_system_mode == "Nothing":
            return

        if self.tokenizer is None or self.session is None:
            self.tokenizer = AutoTokenizer.from_pretrained("Cohee/distilbert-base-uncased-go-emotions-onnx")
            model_path = os.path.join("resources", "data", "emotions", "detector.onnx")
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
                    print("Model file not found.")

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
        emotions_path = "../../../../resources/data/emotions"
        
        # Load the existing JSON data from the model file
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

        # Update the FileReferences and save the modified JSON back to the file
        with open(model_json_path, "w", encoding="utf-8") as file:
            json.dump(model_data, file, indent=4, ensure_ascii=False)

    def show_emotion_image(self, expression_images_folder, character_name):
        """
        Displays an image or GIF representing the character's current emotion.
        """
        configuration_data = self.configuration_characters.load_configuration()
        character_information = configuration_data["character_list"][character_name]
        current_emotion = character_information.get("current_emotion")
        image_name = self.emotion_resources[current_emotion]["image"]
        print(image_name)
        
        if self.expression_image_label is not None:
            # Define possible paths for the emotion image
            gif_path = os.path.join(expression_images_folder, f"{image_name}.gif")
            png_path = os.path.join(expression_images_folder, f"{image_name}.png")
            neutral_gif_path = os.path.join(expression_images_folder, "neutral.gif")
            neutral_png_path = os.path.join(expression_images_folder, "neutral.png")

            # Display the appropriate image or GIF based on availability
            if os.path.exists(gif_path):
                # Use QMovie for animated GIFs
                movie = QtGui.QMovie(gif_path)
                self.expression_image_label.setMovie(movie)
                movie.setScaledSize(self.expression_image_label.size())
                movie.start()
            elif os.path.exists(png_path):
                # Use QPixmap for static PNGs
                pixmap = QPixmap(png_path)
                scaled_pixmap = pixmap.scaled(
                    self.expression_image_label.width(),
                    self.expression_image_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.expression_image_label.setPixmap(scaled_pixmap)
            elif os.path.exists(neutral_gif_path):
                # Fallback to neutral GIF if the specific emotion file is missing
                movie = QtGui.QMovie(neutral_gif_path)
                self.expression_image_label.setMovie(movie)
                movie.setScaledSize(self.expression_image_label.size())
                movie.start()
            elif os.path.exists(neutral_png_path):
                # Fallback to neutral PNG if no other files are available
                pixmap = QPixmap(neutral_png_path)
                scaled_pixmap = pixmap.scaled(
                    self.expression_image_label.width(),
                    self.expression_image_label.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.expression_image_label.setPixmap(scaled_pixmap)
            else:
                print(f"Files for emotion {image_name} and neutral not found.")

            if self.stackedWidget_expressions is not None:
                self.stackedWidget_expressions.setCurrentWidget(self.expression_image_page)

    async def open_sow_system(self, character_name):
        """
        Opens the Soul of Waifu System (SOW) for the specified character.
        """
        character_data = self.configuration_characters.load_configuration()
        character_information = character_data["character_list"][character_name]

        current_text_to_speech = character_information["current_text_to_speech"]
        
        if current_text_to_speech in ("Nothing", None):
            message_box_information = QMessageBox()
            message_box_information.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
            message_box_information.setWindowTitle(self.tr("Voice Error"))
            message_box_information.setText(self.tr("Assign a character's voice before you go on to the call."))
            message_box_information.exec()
        else:
            self.sow_system = Soul_Of_Waifu_System(self.main_window, character_name)
            asyncio.ensure_future(self.sow_system.open_soul_of_waifu_system())

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

        # Load output device settings (In development...)
        self.output_device = self.configuration_settings.get_main_setting("output_device")
        self.output_device = self.output_device + 1

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
            print("[Live2DWidget] Current OpenGL context activated.")
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
        
        print("[Live2DWidget] OpenGL initialized.")
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
            self.savePng('cache\\screenshot_chat.png')
            self.read = True

    def savePng(self, fName):
        """
        Saves the current frame as a PNG image.

        Args:
            fName (str): File name to save the screenshot as.
        """
        if self.width() <= 0 or self.height() <= 0:
            print(f"[Live2DWidget] Error: Invalid widget dimensions: {self.width()}x{self.height()}")
            return
        
        print(f"Saving frame to {fName}...")
        data = gl.glReadPixels(0, 0, self.width(), self.height(), gl.GL_RGBA, gl.GL_UNSIGNED_BYTE)
        data = np.frombuffer(data, dtype=np.uint8).reshape(self.height(), self.width(), 4)
        data = np.flipud(data)
        
        # Process pixel data to highlight edges
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
        """
        Handles the hide event by stopping the timer and cleaning up resources.
        """
        print("[Live2DWidget] Widget hidden, stopping timer and releasing resources.")
        if self.timerId is not None:
            self.killTimer(self.timerId)
            self.timerId = None
        self.cleanup()
        super().hideEvent(event)

    def closeEvent(self, event):
        """
        Handles the close event by cleaning up resources.
        """
        print("[Live2DWidget] Closing widget...")
        self.cleanup()
        super().closeEvent(event)
