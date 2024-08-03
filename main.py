import os
import sys
import json
import torch
import pygame
import asyncio
import aiohttp
import aiofiles
import translators as ts
import speech_recognition as sr

from functools import partial
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from qasync import QEventLoop, asyncSlot
from silero_tts.silero_tts import SileroTTS
from characterai import aiocai, authUser, sendCode

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QTranslator, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtMultimedia import QMediaDevices
from PyQt6.QtWidgets import (QApplication, QInputDialog, QLabel, QMainWindow, 
                             QMessageBox, QPushButton, QWidget, QHBoxLayout, 
                             QListWidgetItem)

from resources.call_interface import Call_MainWindow
from resources.main_interface import Ui_MainWindow

class MainWindow(QMainWindow):
    """Этот класс отвечает за работу графического интерфейса программы"""
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Soul of Waifu")
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._translate = QtCore.QCoreApplication.translate
        
        self.configuration = Configuration()
        self.conversation = Conversation()

        self.get_home_page()
        self.first_message_sent = {}
        self.character_chats = {}

        self.setup_side_menu_actions()
        self.setup_social_media_actions()
        self.setup_top_menu_actions()
        self.setup_settings_tab()
        self.load_characters_to_list()
        self.inoutput_devices()
        self.retranslateUi()

    def setup_side_menu_actions(self):
        """Подключение действий для кнопок бокового меню"""
        self.ui.pushButton_CreateCharacter.clicked.connect(self.on_pushButton_CreateCharacter_clicked)
        self.ui.pushButton_ListOfCharacters.clicked.connect(self.on_pushButton_ListOfCharacters_clicked)
        self.ui.pushButton_Options.clicked.connect(self.on_pushButton_Options_clicked)
        self.ui.pushButton_CreateCharacter2.clicked.connect(self.on_pushButton_CreateCharacter_clicked)
        self.ui.pushButton_AddCharacter.clicked.connect(self.add_character)
    
    def setup_social_media_actions(self):
        """Подключение действий для кнопок социальных сетей"""
        self.ui.pushButton_Youtube.clicked.connect(self.open_youtube)
        self.ui.pushButton_Discord.clicked.connect(self.open_discord)
        self.ui.pushButton_Github.clicked.connect(self.open_github)
    
    def setup_top_menu_actions(self):
        """Подключение действий для кнопок верхнего меню"""
        self.ui.actionAbout_program.triggered.connect(self.about_program)
        self.ui.actionGet_Token_from_Character_AI.triggered.connect(self.get_token_from_character_ai)
        self.ui.actionCreate_new_character.triggered.connect(self.on_pushButton_CreateCharacter_clicked)
        self.ui.actionSettings.triggered.connect(self.on_pushButton_Options_clicked)
        self.ui.actionGet_support_from_GitHub.triggered.connect(self.open_github)
        self.ui.actionGet_support_from_Discord.triggered.connect(self.open_discord)
    
    def setup_settings_tab(self):
        """Настройка настроек"""
        self.setup_api_token()
        self.setup_elevenlabs_settings()
        self.setup_combobox_connections()
    
    def setup_api_token(self):
        """Настройка API токена"""
        api_token = self.configuration.get_value("api_token")
        if api_token:
            self.ui.lineEdit_apiToken.setText(api_token)
        self.ui.lineEdit_apiToken.textChanged.connect(self.load_token)
    
    def setup_elevenlabs_settings(self):
        """Настройка токена и голосового ID Eleven Labs"""
        eleven_token = self.configuration.get_value("eleven_api_token")
        if eleven_token:
            self.ui.lineEdit_ElevenToken.setText(eleven_token)
        self.ui.lineEdit_ElevenToken.textChanged.connect(self.load_eleven_token)

        eleven_voice_id = self.configuration.get_value("eleven_voice_id")
        if eleven_voice_id:
            self.ui.lineEdit_ElevenToken_voiceID.setText(eleven_voice_id)
        self.ui.lineEdit_ElevenToken_voiceID.textChanged.connect(self.load_eleven_voice_id)

    def setup_combobox_connections(self):
        """Подключение сигналов для комбобоксов"""
        self.load_selected_tts()
        self.ui.comboBox_TTS.currentIndexChanged.connect(self.on_comboBox_TTS_changed)
        self.ui.comboBox_TTS_Lang.currentIndexChanged.connect(self.on_comboBox_TTS_Lang_changed)
        self.ui.comboBox_TTS_Voice.currentIndexChanged.connect(self.on_comboBox_TTS_Voice_changed)
        self.ui.comboBox_TTS_Device.currentIndexChanged.connect(self.on_comboBox_TTS_Device_changed)
        self.ui.comboBox_Language.currentIndexChanged.connect(self.on_comboBox_Language_changed)
        self.ui.comboBox_SpeechToText.currentIndexChanged.connect(self.on_comboBox_SpeechToText_changed)

    def reset_button_styles(self):
        """Сброс стилей кнопок бокового меню на значения по умолчанию"""
        buttons = [
            self.ui.pushButton_Home,
            self.ui.pushButton_CreateCharacter,
            self.ui.pushButton_ListOfCharacters,
            self.ui.pushButton_Options
        ]
        default_style = "QPushButton {background-color: none; color: rgb(255, 255, 255);}"
        for btn in buttons:
            btn.setStyleSheet(default_style)
            btn.setChecked(False)
    
    def set_active_button_style(self, button):
        """Установка активного стиля для кнопки"""
        active_style = "QPushButton {background-color: rgb(63, 92, 186); color: black; border-radius: 10px;}"
        button.setStyleSheet(active_style)
        button.setChecked(True)

    def on_pushButton_Home_clicked(self):
        """Обработка клика по кнопке Home"""
        self.reset_button_styles()
        self.set_active_button_style(self.ui.pushButton_Home)
        character_list = self.configuration.configuration_data.get("character_list")
        self.ui.stackedWidget.setCurrentIndex(1 if character_list else 0)

    def on_pushButton_CreateCharacter_clicked(self):
        """Обработка клика по кнопке Create Character"""
        self.reset_button_styles()
        self.set_active_button_style(self.ui.pushButton_CreateCharacter)
        self.ui.stackedWidget.setCurrentIndex(2)

    def on_pushButton_ListOfCharacters_clicked(self):
        """Обработка клика по кнопке List of Characters"""
        self.reset_button_styles() 
        self.set_active_button_style(self.ui.pushButton_ListOfCharacters)
        self.ui.stackedWidget.setCurrentIndex(3)

    def on_pushButton_Options_clicked(self):
        """Обработка клика по кнопке Options"""
        self.reset_button_styles()
        self.set_active_button_style(self.ui.pushButton_Options)
        self.ui.stackedWidget.setCurrentIndex(4)

    def open_youtube(self):
        """Открытие YouTube канала"""
        QDesktopServices.openUrl(QUrl("https://www.youtube.com/@jofizcd"))

    def open_discord(self):
        """Открытие Discord-сервера"""
        QDesktopServices.openUrl(QUrl("https://discord.com/invite/HC89b3CvZH"))

    def open_github(self):
        """Открытие GitHub репозитория"""
        QDesktopServices.openUrl(QUrl("https://github.com/jofizcd/Soul-of-Waifu"))        

    def about_program(self):
        """Показать окно О программе"""
        description = self.tr("Soul of Waifu is a program that will allow you to interact with your waifu. The program uses the API from the Character AI website, so you will be able to bring your characters from there. The main feature of Soul of Waifu is the ability to have a voice conversation with your character. In the future, I will add the ability to upload your LLMs. This way, you will be able to switch between a character with Character AI and a local character.")
        sub_description = self.tr("If you have any suggestions and ideas for the development of Soul of Waifu or if you have any problems with the program, I am waiting for you in my Discord server.")
        github_site = "https://github.com/jofizcd"
        align = "justify"
    
        mbox_about = QMessageBox()
        mbox_about.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        mbox_about.setWindowTitle(self.tr("Soul of Waifu - About"))
        mbox_about.setText(f"<p><b>Soul of Waifu v1.0.0</b></p>"
                        f"<p align={align}>{description}</p>"
                        f"<p align={align}>{sub_description}</p>"
                        f"<p><i>Developed by <a href={github_site}>jofizcd</a></i></p>")
        mbox_about.exec()
    
    def get_token_from_character_ai(self):
        """Получение токена от Character AI"""
        email_address, agreement = QInputDialog.getText(self, self.tr('Get Token'), self.tr('Enter your email:'))
        if agreement and email_address:
            sendCode(email_address)
            link, agreement_link = QInputDialog.getText(self, self.tr('Get Token'), self.tr('Enter the link from the email:'))
            if agreement_link and link:
                user_token = authUser(link, email_address)
                email_message = self.tr(f"Thank you! Your email is: {email_address}")
                api_token_message = self.tr(f"Your API token: {user_token}")
                combined_message = f"{email_message}<br>{api_token_message}"
                configuration.configuration_process("api_token", user_token)
                self.show_message_box("Soul of Waifu - Get API Token", combined_message)

    def show_message_box(self, title, text):
        """Показать сообщение"""
        mbox = QMessageBox()
        mbox.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        mbox.setWindowTitle(self.tr(title))
        mbox.setText(text)
        mbox.exec()

    def inoutput_devices(self):
        """Загрузка доступных устройств ввода и вывода аудио"""
        self.populate_devices(QMediaDevices.audioInputs(), self.ui.comboBox_InputDevice)
        self.populate_devices(QMediaDevices.audioOutputs(), self.ui.comboBox_OutputDevice)

    def populate_devices(self, devices, combobox):
        """Заполнение выпадающего списка устройствами"""
        combobox.clear()
        for device in devices:
            combobox.addItem(device.description(), device)

    def load_token(self):
        """Загрузка и сохранение API токена"""
        self.configuration.configuration_process("api_token", self.ui.lineEdit_apiToken.text())

    def load_eleven_token(self):
        """Загрузка и сохранение токена ElevenLabs"""
        self.configuration.configuration_process("eleven_api_token", self.ui.lineEdit_ElevenToken.text())

    def load_eleven_voice_id(self):
        """Загрузка и сохранение ID голоса ElevenLabs"""
        self.configuration.configuration_process("eleven_voice_id", self.ui.lineEdit_ElevenToken_voiceID.text())

    def load_selected_tts(self):
        """Загрузка выбранных настроек Text-to-Speech"""
        self.load_combobox_value("selected_tts", self.ui.comboBox_TTS, self.selector_tts)
        self.load_combobox_value("selected_tts_language", self.ui.comboBox_TTS_Lang, self.selector_tts_language)
        self.load_combobox_value("selected_tts_voice", self.ui.comboBox_TTS_Voice)
        self.load_combobox_value("selected_tts_device", self.ui.comboBox_TTS_Device)

    def load_combobox_value(self, key, combobox, selector=None):
        """Загрузка значения для выпадающего списка"""
        value = self.configuration.get_value(key)
        if value is not None:
            combobox.setCurrentIndex(value)
            if selector:
                selector(value)
        else:
            self.configuration.configuration_process(key, 0)

    def on_comboBox_TTS_changed(self, index):
        """Обработка изменения выбора Text-To-Speech"""
        self.configuration.configuration_process("selected_tts", index)
        self.selector_tts(index)

    def selector_tts(self, selected_tts):
        """Настройка видимости элементов интерфейса в зависимости от выбранного Text-To-Speech"""
        components = [
            self.ui.comboBox_TTS_Lang,
            self.ui.comboBox_TTS_Voice,
            self.ui.comboBox_TTS_Device,
            self.ui.lineEdit_ElevenToken,
            self.ui.lineEdit_ElevenToken_voiceID,
            self.ui.label_12,  # Choose language
            self.ui.label_13,  # Choose device
            self.ui.label_14,  # Write your token
            self.ui.label_15,  # Choose voice
            self.ui.label_elevenlabs_voice_id
        ]
    
        for component in components:
            component.hide()
    
        if selected_tts == 2:
            component.hide()
            self.ui.comboBox_TTS_Lang.show()
            self.ui.comboBox_TTS_Voice.show()
            self.ui.comboBox_TTS_Device.show()
            self.ui.label_12.show()
            self.ui.label_13.show()
            self.ui.label_15.show()
        elif selected_tts == 3:
            component.hide()
            self.ui.lineEdit_ElevenToken.show()
            self.ui.label_14.show()
            if self.configuration.get_value("eleven_api_token"):
                self.ui.lineEdit_ElevenToken_voiceID.show()
                self.ui.label_elevenlabs_voice_id.show()

    def show_components(self, components):
        """Показать компоненты"""
        for component in components:
            component.show()

    def on_comboBox_TTS_Lang_changed(self, index):
        """Обработка изменения выбора языка Text-To-Speech"""
        self.configuration.configuration_process("selected_tts_language", index)
        self.selector_tts_language(index)

    def selector_tts_language(self, selected_tts_language):
        """Настройка доступных голосов в зависимости от выбранного языка Text-To-Speech"""
        self.ui.comboBox_TTS_Voice.clear()
        voices = {
            0: ["en_0", "en_1", "en_2", "en_3", "en_4", "en_5", "en_6", "en_7", "en_8", "en_9", "en_10", "en_11", "en_12"],
            1: ["aidar", "xenia", "kseniya", "baya", "eugene"]
        }
        self.ui.comboBox_TTS_Voice.addItems(voices.get(selected_tts_language, []))

    def on_comboBox_TTS_Voice_changed(self, index):
        """Обработка изменения выбора голоса Text-To-Speech"""
        self.configuration.configuration_process("selected_tts_voice", index)

    def on_comboBox_TTS_Device_changed(self, index):
        """Обработка изменения выбора устройства Text-To-Speech"""
        self.configuration.configuration_process("selected_tts_device", index)

    def on_comboBox_Language_changed(self, index):
        """Обработка изменения выбора языка интерфейса"""
        self.configuration.configuration_process("selected_language", index)

    def on_comboBox_SpeechToText_changed(self, index):
        """Обработка изменения выбора технологии Speech-To-Text"""
        self.configuration.configuration_process("selected_stt", index)

    @asyncSlot()
    async def add_character(self):
        """Добавляет нового персонажа в список"""
        character_id = self.ui.character_id_lineEdit.text()
        conversation = await Conversation().init_async()
    
        character_name, character_title, character_first_message = await conversation.get_character(character_id)
        character_avatar = await conversation.get_character_avatar(character_id)
    
        if await self.is_character_already_added(character_id, character_name):
            return

        self.configuration.configuration_character_list_process(
            character_name, character_id, character_avatar, character_title, character_first_message)
        self.ui.character_id_lineEdit.clear()

        if character_name is None or character_avatar is None:
            raise ValueError("Character name or avatar cannot be None")

        await self.add_character_to_characters_list(character_name, character_avatar)
        self.show_message_box("Soul of Waifu - Information", 
                            self.tr(f"Character {character_name} has been added to the character list."))

    async def is_character_already_added(self, character_id, character_name):
        """Проверка, добавлен ли персонаж ранее"""
        character_data = self.configuration.load_configuration()
    
        if 'character_list' in character_data:
            for character in character_data['character_list'].values():
                if character['character_id'] == character_id:
                    self.show_message_box("Soul of Waifu - Character Error", 
                                      self.tr(f"Character {character_name} has already been added previously."))
                    return True
        return False

    def show_message_box(self, title, message):
        """Показ сообщения"""
        QtWidgets.QMessageBox.information(self, self.tr(title), message)

    @asyncSlot()
    async def add_character_to_characters_list(self, character_name, character_avatar):
        """Добавляет персонажа в виджет списка персонажей"""
        item = QListWidgetItem()
        item_widget = QWidget()
        item_layout = QHBoxLayout()

        name_label = QLabel(character_name)
        avatar_label = QLabel()

        avatar_pixmap = self.load_avatar_pixmap(character_avatar)
        avatar_label.setPixmap(avatar_pixmap)
        avatar_label.setFixedSize(70, 70)
        
        delete_button = QPushButton(self.tr("Delete"))
        delete_button.clicked.connect(lambda: self.delete_character(character_name, item))

        configuration_data = self.configuration.load_configuration()
        character_data = configuration_data['character_list']
        character_description = character_data[character_name]['character_description']
        character_first_message = character_data[character_name]['character_first_message']
        
        chat_button = QPushButton(self.tr("Chat"))
        chat_button.clicked.connect(lambda: self.start_chat(character_name, character_avatar, character_description, character_first_message))
        
        set_voice_button = QPushButton(self.tr("Set voice"))
        self.setup_voice_button(set_voice_button, character_name)

        item_layout.addWidget(avatar_label)
        item_layout.addWidget(name_label)
        item_layout.addWidget(chat_button)
        item_layout.addWidget(delete_button)
        item_layout.addWidget(set_voice_button)
        
        item_widget.setLayout(item_layout)
        item.setSizeHint(item_widget.sizeHint())
        self.ui.characterlistWidget.addItem(item)
        self.ui.characterlistWidget.setItemWidget(item, item_widget)
        self.ui.characterlistWidget.setCurrentItem(item)

        self.style_widgets_character_list(name_label, avatar_label, delete_button, set_voice_button, chat_button)

    def style_widgets_character_list(self, name_label, avatar_label, delete_button, set_voice_button, chat_button):
        """Стилизация виджетов"""
        self.ui.characterlistWidget.setStyleSheet("""
            QListWidget {
                background-color: rgb(44, 44, 44);
                border: 1px solid rgb(40, 40, 40);
                padding: 10px;
                border-radius: 1px;
            }
            QListWidget::item {
                border-bottom: 1px solid rgb(37, 37, 37);
            }
            QListWidget::item:hover {
                background-color: rgb(33, 33, 33);
            }
        """)

        name_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: white;
                padding: 10px;
                font-family: 'Muli SemiBold', sans-serif;
            }
        """)

        avatar_label.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 35px;
                padding: 2px;
            }
        """)

        delete_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: #ff4d4d;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-family: 'Muli', sans-serif;
            }
            QPushButton:hover {
                background-color: #ff3333;
            }
        """)
        delete_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

        chat_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                background-color: rgb(36, 64, 94);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 10px;
                font-family: 'Muli', sans-serif;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        chat_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

        set_voice_button.setStyleSheet("""
        QPushButton {
            font-size: 16px;
            background-color: rgb(85, 85, 85);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px 10px;
            font-family: 'Muli', sans-serif;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        """)
        set_voice_button.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)

    def load_avatar_pixmap(self, avatar_filename):
        """Загружает и обрабатывает изображение аватара"""
        pixmap = QtGui.QPixmap(f"./resources/avatars/{avatar_filename}")
        pixmap = pixmap.scaled(70, 70, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        
        mask = QtGui.QPixmap(63, 63)
        mask.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(mask)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.black))
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        painter.drawEllipse(0, 0, 63, 63)
        painter.end()

        painter.begin(mask)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return mask

    def setup_voice_button(self, button, character_name):
        """Настраивает кнопку установки голоса для персонажа"""
        configuration = self.configuration.load_configuration()
        selected_tts = configuration.get("selected_tts", 0)

        if selected_tts == 1:
            button.clicked.connect(lambda: self.open_voice_window(character_name))
            button.setVisible(True)
        else:
            button.clicked.connect(lambda: None)
            button.setVisible(False)

    def open_voice_window(self, character_name):
        """Открывает окно настройки голоса для выбранного персонажа"""
        self.current_character_name = character_name
        self.voice_window = VoiceWindow(character_name)
        self.voice_window.show()    

    @asyncSlot()
    async def load_characters_to_list(self):
        """Загружает персонажей из конфигурационного файла в интерфейс"""
        character_list = self.configuration.load_configuration()
        characters = character_list.get('character_list', {})

        for character_name, data in characters.items():
            character_avatar = data.get('character_avatar')
            await self.add_character_to_characters_list(character_name, character_avatar)

    def delete_character(self, character_name, item):
        """Удаляет персонажа из списка и конфигурации"""
        reply = QMessageBox.question(
            self,
            self.tr("Soul of Waifu - Вопрос"),
            self.tr("Вы уверены, что хотите удалить персонажа?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._remove_character_from_list(character_name, item)    

    def _remove_character_from_list(self, character_name, item):
        """Удаляет персонажа из конфигурации и списка в UI"""
        character_list = self.configuration.configuration_data.get("character_list", {})
        if character_name in character_list:
            del character_list[character_name]
            self.ui.characterlistWidget.takeItem(self.ui.characterlistWidget.row(item))
            self.configuration.save_configuration()

    @asyncSlot()
    async def get_home_page(self):
        """Загружает домашнюю страницу с данными пользователя"""
        user_data = self.configuration.load_configuration()
        
        if 'user_data' not in user_data or not user_data['user_data']:
            conversation = await Conversation().init_async()
            user_name, user_avatar = await conversation.get_user()
            self.configuration.configuration_user_process(user_name, user_avatar)
            user_data = self.configuration.load_configuration()

        user_name = list(user_data['user_data'].keys())[0]
        user_avatar = user_data['user_data'][user_name]['user_avatar']
        
        character_list = self.configuration.configuration_data.get("character_list")
        
        if character_list:
            self.ui.stackedWidget.setCurrentIndex(1)
            self.ui.pushButton_Home.setChecked(True)
            welcome_message = self.tr("Nice to see you again, ")
            self.ui.HomeUser_Label.setText(welcome_message + user_name)
            user_pixmap = QtGui.QPixmap(f"./resources/avatars/{user_avatar}")
            user_pixmap = user_pixmap.scaled(100, 100)
            self.ui.user_avatar_label.setPixmap(user_pixmap)
        else:
            self.ui.stackedWidget.setCurrentIndex(0)
            self.ui.pushButton_Home.setChecked(True)

    async def chat_with_character(self, character_name, character_avatar, character_description, character_first_message):
        """Инициализирует чат с выбранным персонажем"""
        if character_name not in self.character_chats:
            self.character_chats[character_name] = []
        
        selected_tts = self.configuration.load_configuration()["selected_tts"]

        self.ui.stackedWidget.setCurrentIndex(5)
        self.ui.character_image.setPixmap(QtGui.QPixmap(f"./resources/avatars/{character_avatar}").scaled(45, 45, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        self.ui.character_name.setText(character_name)
        self.ui.character_description.setText(character_description)
        self.set_cursor(selected_tts)
        self.display_chat(character_name)

        if not self.first_message_sent.get(character_name, False):
            self.add_message(character_first_message, character_name, character_name)
            self.first_message_sent[character_name] = True
    
        self.disconnect_signals()
        self.connect_signals(selected_tts, character_name, character_avatar)

    def set_cursor(self, selected_tts):
        """Устанавливает курсор в зависимости от выбранного TTS"""
        if selected_tts == 0:
            self.ui.btn_call.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ForbiddenCursor))
        else:
            self.ui.btn_call.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

    def disconnect_signals(self):
        """Отключает сигналы, если они уже подключены"""
        try:
            self.ui.line_edit_message.returnPressed.disconnect()
            self.ui.btn_send_message.clicked.disconnect()
            self.ui.btn_call.clicked.disconnect()
        except TypeError:
            pass

    def connect_signals(self, selected_tts, character_name, character_avatar):
        """Подключает сигналы в зависимости от выбранного TTS"""
        match selected_tts:
            case 0:  # None
                self.ui.line_edit_message.returnPressed.connect(lambda: asyncio.create_task(self.send_message_None(character_name)))
                self.ui.btn_send_message.clicked.connect(lambda: asyncio.create_task(self.send_message_None(character_name)))
            case 1:  # Character AI
                self.ui.line_edit_message.returnPressed.connect(lambda: asyncio.create_task(self.send_message_Character_AI_TTS_text(character_name)))
                self.ui.btn_send_message.clicked.connect(lambda: asyncio.create_task(self.send_message_Character_AI_TTS_text(character_name)))
                self.ui.btn_call.clicked.connect(lambda: self.open_call_window(selected_tts, character_avatar, character_name))
            case 2:  # Silero TTS
                self.ui.line_edit_message.returnPressed.connect(lambda: asyncio.create_task(self.send_message_SileroTTS_text(character_name)))
                self.ui.btn_send_message.clicked.connect(lambda: asyncio.create_task(self.send_message_SileroTTS_text(character_name)))
                self.ui.btn_call.clicked.connect(lambda: self.open_call_window(selected_tts, character_avatar, character_name))
            case 3:  # Eleven Labs
                self.ui.line_edit_message.returnPressed.connect(lambda: asyncio.create_task(self.send_message_ElevenLabs_text(character_name)))
                self.ui.btn_send_message.clicked.connect(lambda: asyncio.create_task(self.send_message_ElevenLabs_text(character_name)))
                self.ui.btn_call.clicked.connect(lambda: self.open_call_window(selected_tts, character_avatar, character_name))

    def start_chat(self, character_name, character_avatar, character_description, character_first_message):
        """Запускает чат с персонажем"""
        asyncio.create_task(self.chat_with_character(character_name, character_avatar, character_description, character_first_message))

    def save_user_message(self):
        """Сохраняет сообщение пользователя и очищает поле ввода"""
        user_message = self.ui.line_edit_message.text()
        self.ui.line_edit_message.clear()
        return user_message

    def display_chat(self, character_name):
        """Отображает чат с выбранным персонажем"""
        self.clear_chat()
        self.load_chat_messages(character_name)

    def clear_chat(self):
        """Очищает виджет чата"""
        for i in reversed(range(self.ui.scroll_layout.count())):
            widget = self.ui.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

    def load_chat_messages(self, character_name):
        """Загружает сообщения чата для выбранного персонажа"""
        for message, sender in self.character_chats[character_name]:
            self.create_message_widget(message, sender)

    def create_message_widget(self, message, sender):
        """Создает виджет сообщения и добавляет его в чат"""
        message_widget = QWidget()
        message_layout = QHBoxLayout()
        message_widget.setLayout(message_layout)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(self.get_message_style(sender))

        if sender == "user":
            message_layout.addStretch()
            message_layout.addWidget(message_label)
        else:
            message_layout.addWidget(message_label)
            message_layout.addStretch()
            
        self.ui.scroll_layout.addWidget(message_widget)
        asyncio.create_task(self.scroll_to_bottom())

    async def scroll_to_bottom(self):
        """Асинхронно прокручивает scrollArea вниз"""
        await asyncio.sleep(0.05)
        self.ui.scrollArea_chat.verticalScrollBar().setValue(self.ui.scrollArea_chat.verticalScrollBar().maximum())

    def add_message(self, message, sender, character_name):
        """Добавляет сообщение в историю чата и отображает его, если нужный персонаж активен"""
        self.character_chats.setdefault(character_name, []).append((message, sender))
        if self.ui.character_name.text() == character_name:
            self.display_chat(character_name)

    def get_message_style(self, sender):
        """Возвращает стиль для сообщения в зависимости от отправителя"""
        if sender == "user":
            return """
                QLabel {
                    color: #E1E1E1;
                    background-color: #2E2E2E;
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px;
                    font-size: 14px;
                }
            """
        else:
            return """
                QLabel {
                    color: #E1E1E1;
                    background-color: #3E3E3E;
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px;
                    font-size: 14px;
                }
            """  

    def open_call_window(self, selected_tts, character_avatar, character_name):
        """Открывает окно вызова для выбранного персонажа"""
        self.call_window = CallWindow(selected_tts, character_avatar, character_name)
        self.call_window.show()

    async def send_message(self, character_name, tts_method, user_message=None,
    selected_language=None, selected_tts_language=None, selected_tts_voice=None,
    selected_tts_device=None, eleven_labs_token=None, eleven_labs_voice_id=None,
    candidate_id=None, chat_id=None, turn_id=None):
        """Отправляет сообщение, используя указанный метод TTS"""
        if user_message is None:
            user_message = self.save_user_message()
        if not user_message:
            return

        self.add_message(user_message, "user", character_name)
        conversation = await Conversation().init_async()
        configuration_data = self.configuration.load_configuration()
        character_data = configuration_data['character_list']
        character_id = character_data[character_name]['character_id']
        selected_language = configuration_data['selected_language']
        selected_tts_language = configuration_data['selected_tts_language']
        selected_tts_voice = configuration_data['selected_tts_voice']
        selected_tts_device = configuration_data['selected_tts_device']
        eleven_labs_token = configuration_data['eleven_api_token']
        eleven_labs_voice_id = configuration_data['eleven_voice_id']
    
        if tts_method == "None":
            character_message = await conversation.character_conversation_send_message_None(character_id, user_message)
            self.handle_response_language(character_message, character_name, selected_language)
        else:
            if 'voice_id' not in character_data[character_name]:
                reply = QMessageBox.information(
                    self,
                    self.tr("Soul of Waifu - Voice Error"),
                    self.tr("You have not assigned a voice to your character"),
                    QMessageBox.StandardButton.Ok
                )
                if reply == QMessageBox.StandardButton.Ok:
                    self.open_voice_window(character_name)
                return
        
            voice_id = character_data[character_name]['voice_id']
            if tts_method in ["CharacterAI_TTS_text", "CharacterAI_TTS_call"]:
                character_message, turn_id, candidate_id, chat_id = await conversation.character_conversation_send_message_CharacterAI_TTS(character_id, user_message)
            elif tts_method in ["SileroTTS_text", "SileroTTS_call"]:                
                character_message = await conversation.character_conversation_send_message_SileroTTS(character_id, user_message)
            elif tts_method in ["ElevenLabs_text", "ElevenLabs_call"]:
                character_message = await conversation.character_conversation_send_message_ElevenLabs(character_id, user_message)
        
            await self.handle_tts_response(character_message, character_name, selected_language, tts_method, voice_id, candidate_id, chat_id, turn_id, selected_tts_language, selected_tts_voice, selected_tts_device, eleven_labs_token, eleven_labs_voice_id)    

    def handle_response_language(self, character_message, character_name, selected_language):
        """Обрабатывает сообщение персонажа в зависимости от выбранного языка"""
        if selected_language == 0: # English
            self.add_message(character_message, character_name, character_name)
        elif selected_language == 1: # Русский
            character_message_translated = ts.translate_text(character_message, "yandex", "en", "ru")
            self.add_message(character_message_translated, character_name, character_name)

    async def handle_tts_response(self, character_message, character_name, selected_language, tts_method, voice_id, candidate_id, chat_id, turn_id, selected_tts_language, selected_tts_voice, selected_tts_device, eleven_labs_token, eleven_labs_voice_id):
        """Обрабатывает ответ персонажа с использованием TTS"""
        conversation = await Conversation().init_async()
        if tts_method in ["CharacterAI_TTS_text", "CharacterAI_TTS_call"]:
            self.handle_response_language(character_message, character_name, selected_language)
            await conversation.character_conversation_reply_CharacterAI_TTS(candidate_id, chat_id, turn_id, voice_id)
        elif tts_method in ["SileroTTS_text", "SileroTTS_call"]:
            self.handle_response_language(character_message, character_name, selected_language)
            character_message = character_message.replace("*", "")
            await asyncio.sleep(0.5)
            await conversation.character_conversation_reply_SileroTTS(selected_tts_language, selected_tts_voice, selected_tts_device, character_message)
        elif tts_method in ["ElevenLabs_text", "ElevenLabs_call"]:
            self.handle_response_language(character_message, character_name, selected_language)
            character_message = character_message.replace("*", "")
            await asyncio.sleep(0.5)
            await conversation.character_conversation_reply_ElevenLabs(character_message, eleven_labs_token, eleven_labs_voice_id)

    async def send_message_None(self, character_name):
        await self.send_message(character_name, "None")

    async def send_message_Character_AI_TTS_text(self, character_name):
        await self.send_message(character_name, "CharacterAI_TTS_text")

    async def send_message_Character_AI_TTS_call(self, character_name, user_message):
        await self.send_message(character_name, "CharacterAI_TTS_call", user_message)

    async def send_message_SileroTTS_text(self, character_name):
        await self.send_message(character_name, "SileroTTS_text")

    async def send_message_SileroTTS_call(self, character_name, user_message):
        await self.send_message(character_name, "SileroTTS_call", user_message)

    async def send_message_ElevenLabs_text(self, character_name):
        await self.send_message(character_name, "ElevenLabs_text")

    async def send_message_ElevenLabs_call(self, character_name, user_message):
        await self.send_message(character_name, "ElevenLabs_call", user_message)

    def retranslateUi(self):
        self.ui.pushButton_Home.setText(self.tr(" Main Navigation"))
        self.ui.pushButton_CreateCharacter.setText(self.tr(" Create Character"))
        self.ui.pushButton_ListOfCharacters.setText(self.tr(" List of Characters"))
        self.ui.pushButton_Options.setText(self.tr(" Options"))
        self.ui.pushButton_Youtube.setText(self.tr(" YouTube"))
        self.ui.pushButton_Discord.setText(self.tr(" Discord"))
        self.ui.pushButton_Github.setText(self.tr(" GitHub"))
        self.ui.creditsLabel.setText(self.tr("Created by Jofi"))
        self.ui.version.setText(self.tr("v1.0.0"))
        self.ui.NoneCharacter_Label.setText(self.tr("You do not have any characters added. Click the button to add more characters."))
        self.ui.pushButton_CreateCharacter2.setText(self.tr(" Create Character"))
        self.ui.MainNavigation_Label.setText(self.tr("MAIN NAVIGATION"))
        self.ui.creditsLabel_2.setText(self.tr("Created by Jofi"))
        self.ui.version_2.setText(self.tr("v1.0.0"))
        self.ui.MainNavigation2_Label.setText(self.tr("MAIN NAVIGATION"))
        self.ui.HomeUser_Label.setText(self.tr("Nice to see you again,"))
        self.ui.user_avatar_label.setText(self.tr(""))
        self.ui.creditsLabel_5.setText(self.tr("Created by Jofi"))
        self.ui.version_5.setText(self.tr("v1.0.0"))
        self.ui.label_4.setText(self.tr("Write your character\'s ID"))
        self.ui.label_7.setText(self.tr("Character ID:"))
        self.ui.pushButton_AddCharacter.setText(self.tr("Add"))
        self.ui.MainNavigation2_Label_2.setText(self.tr("CREATE CHARACTER"))
        self.ui.creditsLabel_6.setText(self.tr("Created by Jofi"))
        self.ui.version_6.setText(self.tr("v1.0.0"))
        self.ui.ListOfCharacters_Label.setText(self.tr("LIST OF CHARACTERS"))
        self.ui.creditsLabel_7.setText(self.tr("Created by Jofi"))
        self.ui.version_7.setText(self.tr("v1.0.0"))
        self.ui.Options_Label.setText(self.tr("OPTIONS"))
        self.ui.label_8.setText(self.tr("Character Ai API Token"))
        self.ui.label_9.setText(self.tr("Write your token:"))
        self.ui.label_10.setText(self.tr("Generating a character\'s voice"))
        self.ui.label_11.setText(self.tr("Choose TTS:"))
        self.ui.comboBox_TTS.setItemText(1, self.tr("Character AI"))
        self.ui.comboBox_TTS.setItemText(2, self.tr("Silero TTS"))
        self.ui.comboBox_TTS.setItemText(3, self.tr("Eleven Labs"))
        self.ui.label_12.setText(self.tr("Choose language:"))
        self.ui.comboBox_TTS_Lang.setItemText(0, self.tr("English"))
        self.ui.comboBox_TTS_Lang.setItemText(1, self.tr("Russian"))
        self.ui.label_13.setText(self.tr("Choose device:"))
        self.ui.comboBox_TTS_Device.setItemText(0, self.tr("CPU"))
        self.ui.comboBox_TTS_Device.setItemText(1, self.tr("GPU"))
        self.ui.label_14.setText(self.tr("Write your token:"))
        self.ui.label_15.setText(self.tr("Choose voice:"))
        self.ui.tabWidget.setTabText(self.ui.tabWidget.indexOf(self.ui.config_tab), self.tr("Configuration"))
        self.ui.label_16.setText(self.tr("Language"))
        self.ui.comboBox_Language.setItemText(0, self.tr("English"))
        self.ui.comboBox_Language.setItemText(1, self.tr("Русский"))
        self.ui.label_17.setText(self.tr("Devices"))
        self.ui.label_18.setText(self.tr("Input device:"))
        self.ui.label_19.setText(self.tr("Output device:"))
        self.ui.tabWidget.setTabText(self.ui.tabWidget.indexOf(self.ui.system_tab), self.tr("System"))
        self.ui.line_edit_message.setPlaceholderText(self.tr("Write your message to character"))
        self.ui.character_name.setText(self.tr("Character name"))
        self.ui.character_description.setText(self.tr("Character description"))
        self.ui.label_mainWords.setText(self.tr("Soul of Waifu is the place where your dream becomes real"))
        self.ui.menuSoW.setTitle(self.tr("Soul of Waifu"))
        self.ui.menuHelp.setTitle(self.tr("Help"))
        self.ui.actionAbout_program.setText(self.tr("About Soul of Waifu"))
        self.ui.actionGet_Token_from_Character_AI.setText(self.tr("Get Token from Character AI"))
        self.ui.actionCreate_new_character.setText(self.tr("Create new character"))
        self.ui.actionSettings.setText(self.tr("Settings"))
        self.ui.actionGet_support_from_Discord.setText(self.tr("Get support from Discord"))
        self.ui.actionGet_support_from_GitHub.setText(self.tr("Get support from GitHub"))
        self.ui.label_elevenlabs_voice_id.setText(self.tr("Write Voice ID: "))

class Conversation:
    """В этом классе прописывается возможность взаимодействия пользователя и больших языковых моделей для общения в программе"""
    def __init__(self):
        self.configuration = Configuration()
    
    async def init_async(self):
        self.characterAI_token = self.configuration.get_value("api_token")
        self.client = aiocai.Client(self.characterAI_token)
        return self

    async def get_characterai_tts_audio(self, candidateID, roomID, turnID, voiceID):
        """Получаем содержимое всего json-файла с ссылки Character AI TTS"""
        url = "https://neo.character.ai/multimodal/api/v1/memo/replay"
        headers = {
            "Content-Type": "application/json",
            'Authorization': f'Token {self.characterAI_token}'
        }
        data = {
            "candidateId": candidateID,
            "roomId": roomID,
            "turnId": turnID,
            "voiceId": voiceID
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Ошибка запроса: {response.status}, {await response.text()}")

    async def get_character(self, character_id):
        """Функция для получения информации о персонаже"""
        if len(character_id) == 43: 
            get_character = await self.client.get_char(character_id)
            return get_character.name, get_character.title, get_character.greeting
        else:
            self.show_error_message(
                "Soul of Waifu - Character Error", 
                "Your text is not character ID", 
                "Enter your ID correctly"
            )
            return None, None, None

    async def get_character_avatar(self, character_id):
        """Функция для получения файла с изображением персонажа"""
        get_character = await self.client.get_char(character_id)
        avatar_file_name = get_character.avatar_file_name.split("/")[-1]
        await get_character.avatar.download(f"./resources/avatars/{avatar_file_name}")
        return avatar_file_name

    async def get_user(self):
        """Функция для получения информации о пользователе"""
        get_user = await self.client.get_me()
        avatar_file_name = get_user.avatar_file_name.split("/")[-1]
        await get_user.avatar.download(f"./resources/avatars/{avatar_file_name}")
        return get_user.name, avatar_file_name

    def show_error_message(self, title, text_1, text_2):
        """Функция для отображения сообщения об ошибке"""
        mbox_problem = QMessageBox()
        mbox_problem.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        mbox_problem.setWindowTitle(title)
        align = "justify"
        mbox_problem.setText(f"<p><b>Error</b></p><p align={align}>{text_1}</p><p align={align}>{text_2}</p>")
        mbox_problem.exec()

    async def send_message(self, character_id, user_message):
        """Общий метод для отправки сообщения персонажу и получения содержимого ответа"""
        if self.client is None:
            await self.init_async()
            
        get_chat = await self.client.get_chat(character_id)
        chat_id = get_chat.chat_id

        async with await self.client.connect() as chat:
            message = await chat.send_message(character_id, chat_id, user_message)
        return message

    async def character_conversation_send_message_None(self, character_id, user_message):
        """Метод для отправки персонажу сообщения и получения содержимого ответа. Mode: None"""
        message = await self.send_message(character_id, user_message)
        return message.text

    async def character_conversation_send_message_CharacterAI_TTS(self, character_id, user_message):
        """Метод для отправки персонажу сообщения и получения содержимого ответа. Mode: Character AI TTS"""
        message = await self.send_message(character_id, user_message)
        return message.text, message.turn_key.turn_id, message.primary_candidate_id, message.turn_key.chat_id

    async def character_conversation_send_message_SileroTTS(self, character_id, user_message):
        """Метод для отправки персонажу сообщения и получения содержимого ответа. Mode: Silero TTS"""
        message = await self.send_message(character_id, user_message)
        return message.text

    async def character_conversation_send_message_ElevenLabs(self, character_id, user_message):
        """Метод для отправки персонажу сообщения и получения содержимого ответа. Mode: Eleven Labs"""
        message = await self.send_message(character_id, user_message)
        return message.text

    async def _fetch_audio(self, url, filename):
        """Скачивание аудио с url-ссылки и его воспроизведение"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        async for chunk in response.content.iter_any():
                            if chunk:
                                await f.write(chunk)
                else:
                    print(f"Failed to download file. Status code: {response.status}")

    def _play_and_remove_file(self, filename):
        """Проигрывает аудио с файла и удаляет его"""
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                pygame.init()
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)

                pygame.quit()
            except Exception as e:
                print(f"Error playing audio: {e}")
            finally:
                os.remove(filename)
        else:
            print("Failed to download the audio file or the file is empty.")

    async def character_conversation_reply_CharacterAI_TTS(self, candidate_id, chat_id, turn_id, voice_id):
        """Метод для получения голосового ответа от персонажа CharacterAI"""
        character_reply_data = await self.get_characterai_tts_audio(candidate_id, chat_id, turn_id, voice_id)
        voice_mp3 = character_reply_data.get("replayUrl")
        filename = "character_answer.mp3"
        await self._fetch_audio(voice_mp3, filename)
        self._play_and_remove_file(filename)

    async def character_conversation_reply_SileroTTS(self, selected_tts_language, selected_tts_voice, selected_tts_device, character_message):
        """Метод для получения голосового ответа от персонажа SileroTTS"""
        device = 'cpu' if selected_tts_device == 0 else 'cuda'
        language = 'en' if selected_tts_language == 0 else 'ru'
        if language == "en":
            match selected_tts_voice:
                case 0:
                    voice_id = "en_0"
                case 1:
                    voice_id = "en_1"
                case 2:
                    voice_id = "en_2"
                case 3:
                    voice_id = "en_3"
                case 4:
                    voice_id = "en_4"
                case 5:
                    voice_id = "en_5"
                case 6:
                    voice_id = "en_6"
                case 7:
                    voice_id = "en_7"
                case 8:
                    voice_id = "en_8"
                case 9:
                    voice_id = "en_9"
                case 10:
                    voice_id = "en_10"
                case 11:
                    voice_id = "en_11"
                case 12:
                    voice_id = "en_12"
        else:
            match selected_tts_voice:
                case 0:
                    voice_id = "aidar"
                case 1:
                    voice_id = "xenia"
                case 2:
                    voice_id = "kseniya"
                case 3:
                    voice_id = "baya"
                case 4:
                    voice_id = "eugene"
        
        reply = SileroTTS(
            model_id='v3_en' if language == 'en' else 'v4_ru',
            language=language,
            speaker=voice_id,
            sample_rate=48000,
            device=device
        )
        if selected_language == 0:
            reply.tts(character_message, 'character_reply.wav')
            self._play_and_remove_file("character_reply.wav")
        else:
            character_message = ts.translate_text(character_message, 'yandex', to_language="ru")
            reply.tts(character_message, 'character_reply.wav')
            self._play_and_remove_file("character_reply.wav")

    async def character_conversation_reply_ElevenLabs(self, character_message, eleven_labs_token, eleven_labs_voice_id):
        """Метод для получения голосового ответа от персонажа ElevenLabs"""
        client = ElevenLabs(api_key=eleven_labs_token)
        model_id = "eleven_multilingual_v2"
        filepath = "character_answer.mp3"
        if selected_language == 0:
            character_message = character_message
        else:
            character_message = ts.translate_text(character_message, "yandex", to_language="ru")
        
        response = client.text_to_speech.convert(
            voice_id=eleven_labs_voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=character_message,
            model_id=model_id,
            voice_settings=VoiceSettings(
                stability=0.2,
                similarity_boost=0.8,
                style=0.4,
                use_speaker_boost=True,
            )
        )

        with open(filepath, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
        
        self._play_and_remove_file(filepath)

class CallWindow(QtWidgets.QMainWindow):
    """Этот класс открывает разговорное окно с персонажем"""
    def __init__(self, selected_tts, character_avatar, character_name):
        super().__init__()
        self.character_name = character_name
        self.selected_tts = selected_tts
        self.setup_ui(character_avatar)
        self.setup_audio()
        self.setup_worker()
        self.setup_connections()

    def setup_ui(self, character_avatar):
        """Настраивает пользовательский интерфейс"""
        mw = MainWindow()
        self.setWindowTitle(mw.tr(f"Soul of Waifu - Call with {self.character_name}"))
        self.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        self.ui = Call_MainWindow()
        self.ui.setupUi(self)

        pixmap = QtGui.QPixmap(f"./resources/avatars/{character_avatar}")
        rounded = QtGui.QPixmap(self.ui.label.size())
        rounded.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, self.ui.label.size().width(), self.ui.label.size().height())
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap.scaled(self.ui.label.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
        painter.end()

        self.ui.label.setPixmap(rounded)
        self.ui.label_2.setText(self.character_name)
        self.calling_text = mw.tr("Calling")

    def setup_audio(self):
        """Настраивает аудио поток с pygame"""
        self.sound_toggle = False
        self.is_muted = False
        self.is_hang_up_pressed = False

    def setup_worker(self):
        """Настраивает рабочий поток в зависимости от выбранного TTS"""
        self.worker = CallWorker(self.character_name, self.get_microphone_index(), self.selected_tts, self)
        asyncio.ensure_future(self.worker.run())

    def setup_connections(self):
        """Настраивает соединения сигналов и слотов"""
        self.ui.pushButton_HangUp.clicked.connect(self.hang_up)
        self.ui.pushButton_Mute.clicked.connect(self.toggle_mute)

    def text_speaker_animation(self, action_text):
        """Анимация текста с точками"""
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(partial(self.update_dots_slot, action_text))
        self.timer.start(500)

    def update_dots_slot(self, action_text):
        """Обновляет текст с точками"""
        dot_count = (self.timer.interval() // 500) % 4
        dots = '. ' * dot_count
        self.ui.label_speaker.setText(f"{action_text}{dots}")
    
    def hang_up(self):
        """Завершение звонка"""
        self.is_hang_up_pressed = True
        self.worker.stop()
        pygame.mixer.quit()
        pygame.quit()
        self.close()

    def play_sound(self, filename):
        """Проигрывание звука из файла с pygame"""
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./resources/sounds", filename)
        if not os.path.exists(filepath):
            print(f"File does not exist: {filepath}")
            return
        try:
            pygame.init()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except Exception as e:
            print(f"Error playing audio: {e}")

    def get_microphone_index(self):
        """Получение индекса выбранного микрофона"""
        selected_microphone_device = MainWindow().ui.comboBox_InputDevice.currentData()
        available_devices = QMediaDevices.audioInputs()
        
        for index, device in enumerate(available_devices):
            if device == selected_microphone_device:
                return index
        
        print("Selected device not found.")
        return None

    def toggle_mute(self):
        """Включение/выключение микрофона"""
        self.is_muted = not self.is_muted
        self.ui.pushButton_Mute.setText("Unmute" if self.is_muted else "Mute")
        sound_file = 'mute_01.mp3' if self.is_muted else 'unmute_02.mp3'
        self.play_sound(sound_file)

    async def send_message(self, tts_function, character_name, user_message):
        """Асинхронная отправка сообщения в AI TTS вызов"""
        await tts_function(character_name, user_message)

    async def threaded_send_message(self, character_name, user_message):
        """Асинхронная отправка сообщения"""
        tts_functions = {
            1: MainWindow().send_message_Character_AI_TTS_call,
            2: MainWindow().send_message_SileroTTS_call,
            3: MainWindow().send_message_ElevenLabs_call
        }
        tts_function = tts_functions.get(self.selected_tts)
        if tts_function:
            await self.send_message(tts_function, character_name, user_message)
        else:
            print("Invalid TTS selection")

class CallWorker:
    """Универсальный класс для выполнения фоновых задач вызова TTS"""
    def __init__(self, character_name, selected_microphone_index, tts_type, parent):
        self.character_name = character_name
        self.selected_microphone_index = selected_microphone_index
        self.tts_type = tts_type
        self.parent = parent
        self.is_hang_up_pressed = False
        self.r = sr.Recognizer()
        self.selected_stt = configuration.get_value("selected_stt")

    async def run(self):
        """Основной метод, выполняющий работу асинхронно"""
        while not self.is_hang_up_pressed:
            if not self.parent.is_muted:
                if self.selected_stt == 0:
                    with sr.Microphone() as source:
                        self.parent.play_sound("return_04.mp3")
                        user_message = self.r.listen(source)
                    self.parent.play_sound("turn_03.mp3")
                    if selected_language == 0: # Говорить только на английском
                        user_message = self.r.recognize_google(user_message)
                        print(user_message)
                        await self.parent.threaded_send_message(self.character_name, user_message)
                    else:
                        user_message = self.r.recognize_google(user_message, language="ru-RU")
                        print(user_message)
                        user_message = ts.translate_text(user_message, "yandex", to_language="en")
                        await self.parent.threaded_send_message(self.character_name, user_message)
                else:
                    self.parent.play_sound("return_04.mp3")
                    user_message = await asyncio.to_thread(self.mic.listen)
                    print(user_message)
                    self.parent.play_sound("turn_03.mp3")
                    if selected_language == 0:
                        await self.parent.threaded_send_message(self.character_name, user_message)
                    else:
                        user_message = ts.translate_text(user_message, "yandex", to_language="en")
                        await self.parent.threaded_send_message(self.character_name, user_message)
            else:
                await asyncio.sleep(0.5)

    def stop(self):
        self.is_hang_up_pressed = True

class VoiceWindow(QtWidgets.QMainWindow):
    """Создает окно с выбором голоса персонажа для TTS Character AI"""

    def __init__(self, character_name):
        super().__init__()

        self.character_name = character_name
        self.characterAI_token = Configuration().get_value("api_token")

        self.init_ui()
        self.connect_signals()
        self.apply_dark_theme()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        mw = MainWindow()
        self.setWindowTitle(mw.tr(f"Soul of Waifu - Voice Selector for {self.character_name}"))
        self.setGeometry(100, 100, 400, 200)
        self.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))

        self.label_voice = QtWidgets.QLabel(self.tr("Enter a voice name:"))
        self.textbox_voice = QtWidgets.QLineEdit(self)
        self.combo_voice = QtWidgets.QComboBox(self)

        self.play_button = QtWidgets.QPushButton(self.tr("Play preview audio"))
        self.select_button = QtWidgets.QPushButton(self.tr("Select voice"))

        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addWidget(self.play_button)
        self.button_layout.addWidget(self.select_button)

        self.layout = QtWidgets.QVBoxLayout()
        self.add_current_voice_label()
        self.layout.addWidget(self.label_voice)
        self.layout.addWidget(self.textbox_voice)
        self.layout.addWidget(self.combo_voice)
        self.layout.addLayout(self.button_layout)

        self.central_widget = QtWidgets.QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

    def add_current_voice_label(self):
        """Добавляет метку текущего голоса, если он установлен"""
        character_data = Configuration().load_configuration().get('character_list', {}).get(self.character_name, {})
        voice_name = character_data.get('voice_name')
        if voice_name:
            self.label_current_voice = QtWidgets.QLabel(self.tr(f"Current voice: {voice_name}"))
            self.layout.addWidget(self.label_current_voice)

    def connect_signals(self):
        """Соединяет сигналы с методами"""
        self.textbox_voice.returnPressed.connect(self.search_voices)
        self.play_button.clicked.connect(self.play_selected_voice)
        self.select_button.clicked.connect(self.select_voice)

    async def get_character_voice(self):
        """Получает данные о голосах персонажа"""
        query = self.textbox_voice.text().strip()
        if not query:
            return None

        url = f"https://neo.character.ai/multimodal/api/v1/voices/search?query={query}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.characterAI_token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()

    @asyncSlot()
    async def search_voices(self):
        """Ищет голоса и обновляет комбинированный список"""
        self.combo_voice.clear()
        try:
            data = await self.get_character_voice()
            if data:
                for voice in data.get('voices', []):
                    self.combo_voice.addItem(voice['name'], userData=voice)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Fetch voices error", f"Failed to fetch voices: {str(e)}")

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
    
    async def play_audio_file(self, filename):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        except pygame.error as e:
            print(f"Error playing audio: {e}")
        finally:
            pygame.mixer.quit()
    
    async def play_voice_preview(self, voice):
        """Проигрывает предварительный просмотр голоса"""
        if 'previewAudioURI' in voice:
            preview_audio_uri = voice['previewAudioURI']
            filename = "character_answer.wav"

            if await self.download_file(preview_audio_uri, filename):
                if os.path.exists(filename) and os.path.getsize(filename) > 0:
                    await self.play_audio_file(filename)
                else:
                    print("Downloaded file is empty or corrupt.")
                os.remove(filename)
            else:
                print("Failed to download the audio file.")

    @asyncSlot()
    async def play_selected_voice(self):
        """Проигрывает выбранный голос"""
        voice = self.combo_voice.currentData(QtCore.Qt.ItemDataRole.UserRole)
        if voice:
            await self.play_voice_preview(voice)

    def select_voice(self):
        """Выбирает голос и сохраняет его в конфигурацию"""
        voice = self.combo_voice.currentData(QtCore.Qt.ItemDataRole.UserRole)
        if voice:
            config = Configuration()
            character_list = config.configuration_data.get("character_list", {})
            if self.character_name in character_list:
                character_data = character_list[self.character_name]
                character_data['voice_id'] = voice['id']
                character_data['voice_name'] = voice['name']
                config.save_configuration()
                QtWidgets.QMessageBox.information(self, self.tr("Voice Selected"),
                                                  self.tr(f"Selected voice ID: {voice['id']} for character: {self.character_name}"))
                self.close()
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QLabel, QLineEdit, QComboBox, QPushButton {
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                font-size: 14px;
            }
            QLabel {
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #2e2e2e;
                color: #f5f5f5;
            }
            QPushButton {
                background-color: #3e3e3e;
                color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #2c2c2c;
            }
            QComboBox {
                padding-left: 5px;
            }
            QVBoxLayout, QHBoxLayout {
                spacing: 10px;
            }
        """)

class Configuration():
    """В этом классе прописывается работа конфигурационного файла, в котором будут все необходимые данные пользователя и его программные настройки"""
    def __init__(self):
        self.configuration_path = os.path.join(os.getcwd(), 'configuration.json')
        self.configuration_data = self.load_configuration()
    
    def load_configuration(self):
        """Загрузка данных конфигурации из файла"""
        if not os.path.exists(self.configuration_path):
            return {}
        with open(self.configuration_path, 'r', encoding='utf-8') as file:
            return json.load(file)

    def save_configuration(self):
        """Сохранение текущих данных конфигурации в файл"""
        with open(self.configuration_path, 'w', encoding="utf-8") as file:
            json.dump(self.configuration_data, file, ensure_ascii=False, indent=4)
    
    def configuration_process(self, variable, variable_value):
        """
        Обработка переменной конфигурационного файла.
        
        Args:
            variable (str): Название переменной.
            variable_value (any): Значение переменной.
        """
        self.configuration_data[variable] = variable_value
        self.save_configuration()

    def configuration_character_list_process(self, character_name, character_id, character_avatar, character_description, character_first_message):
        """
        Обработка списка персонажей.
        
        Args:
            character_id (str): Идентификатор персонажа.
            character_avatar (str): Имя файла аватара персонажа.
            character_description (str): Краткое описание персонажа.
            character_first_message (str): Приветственное сообщение персонажа.
        """

        if 'character_list' not in self.configuration_data:
            self.configuration_data['character_list'] = {}

        self.configuration_data['character_list'][character_name] = {
            "character_id": character_id, 
            "character_avatar": character_avatar, 
            "character_description": character_description, 
            "character_first_message": character_first_message
            }
        
        self.save_configuration()

    def configuration_user_process(self, user_name, user_avatar):
        """
        Добавление пользователя в конфигурационный файл
        
        Args:
            user_name (str): Имя пользователя.
            user_avatar (str): Имя файла аватара пользователя.
        """

        if 'user_list' not in self.configuration_data:
            self.configuration_data['user_data'] = {}
        
        self.configuration_data['user_data'][user_name] = {
            "user_avatar": user_avatar
            }
        
        self.save_configuration()
    
    def get_value(self, variable):

        """
        Получение значения из конфигурационного файла по входным данным.
        
        Args:
            variable (str): Название необходимой переменной для получения значения.
        
        Returns:
            any: Значение из конфигурационного файла по указанному названию.
        """
        return self.configuration_data.get(variable)
    
'''Основные переменные'''
current_direction = os.getcwd()

if torch.cuda.is_available():
    selected_device = 'cuda'
    configuration = Configuration()
    configuration.configuration_process("selected_device", selected_device)
else:
    selected_device = 'cpu'
    configuration = Configuration()
    configuration.configuration_process("selected_device", selected_device)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('fusion')

    configuration = Configuration()
    selected_language = configuration.get_value('selected_language')

    translator = QTranslator()
    match selected_language:
        case 0:
            translator.load('./resources/locales/en.qm')
        case 1:
            translator.load('./resources/locales/ru.qm')

    app.installTranslator(translator)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window_app = MainWindow()
    window_app.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
    window_app.show()

    with loop:
        loop.run_forever()