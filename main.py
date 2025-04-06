import os
import yaml
import sys
import ctypes
import asyncio
import requests
from qasync import QEventLoop
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtGui import QFontDatabase
from configuration import configuration
from resources.icons import resources
from resources.data import interface_signals
from api_clients import local_ai_client
from resources.data.sowInterface import Ui_MainWindow

class MainWindow(QMainWindow):
    """
    The main window class for managing the Soul of Waifu GUI and its modules.
    """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.translations = {}
        
        self.configuration = configuration.ConfigurationSettings()
        selected_language = self.configuration.get_main_setting("program_language")
    
        match selected_language:
            case 0:
                self.load_translation("en")
                self.apply_translations()
            case 1:
                self.load_translation("ru")
                self.apply_translations()

        # Initialize interface signals and configurations
        self.interface_signals = interface_signals.InterfaceSignals(self.ui, self)
        self.local_ai_client = local_ai_client.LocalAI(self.ui)

        self.interface_signals.load_llms_to_comboBox()
        self.interface_signals.load_last_selected_model()
        self.interface_signals.load_combobox()
        self.setup_interface_signals()
        self.interface_signals.load_audio_devices()
        self.interface_signals.update_api_token()
        
        # Initialize user settings and sliders
        self.interface_signals.initialize_api_token_line_edit()
        self.interface_signals.initialize_username_line_edit()
        self.interface_signals.initialize_userpersonality_line_edit()
        self.interface_signals.initialize_gpu_layers_horizontalSlider()
        self.interface_signals.initialize_context_size_horizontalSlider()
        self.interface_signals.initialize_temperature_horizontalSlider()
        self.interface_signals.initialize_top_p_horizontalSlider()
        self.interface_signals.initialize_repeat_penalty_horizontalSlider()
        self.interface_signals.initialize_max_tokens_horizontalSlider()
        
        # Create layouts for character management
        self.interface_signals.create_characterai_layout()
        self.interface_signals.create_characterai_search_layout()
        self.interface_signals.create_character_card_layout()
        self.interface_signals.create_character_card_search_layout()

        asyncio.ensure_future(self.interface_signals.set_main_tab())

    def load_translation(self, language):
        file_path = f"resources/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}

    def setup_interface_signals(self):
        """
        Connects signals for all UI elements to their respective handlers.
        """
        # MenuActions
        self.ui.action_about_program.triggered.connect(self.interface_signals.set_about_program_button)
        self.ui.action_create_new_character.triggered.connect(self.interface_signals.show_selection_dialog)
        self.ui.action_get_token_from_character_ai.triggered.connect(self.interface_signals.set_get_token_from_character_ai_button)
        self.ui.action_options.triggered.connect(self.interface_signals.on_pushButton_options_clicked)
        self.ui.action_discord.triggered.connect(self.interface_signals.on_discord)
        self.ui.action_github.triggered.connect(self.interface_signals.on_github)
        self.ui.action_faq.triggered.connect(self.interface_signals.set_faq_button)
        
        # PushButtons
        self.ui.pushButton_main.clicked.connect(self.interface_signals.on_pushButton_main_clicked)
        self.ui.pushButton_create_character.clicked.connect(self.interface_signals.show_selection_dialog)
        self.ui.pushButton_create_character_2.clicked.connect(self.interface_signals.show_selection_dialog)
        self.ui.pushButton_create_character_3.clicked.connect(self.interface_signals.add_character_sync)
        self.ui.pushButton_characters_gateway.clicked.connect(self.interface_signals.open_characters_gateway)
        self.ui.pushButton_options.clicked.connect(self.interface_signals.on_pushButton_options_clicked)
        self.ui.pushButton_youtube.clicked.connect(self.interface_signals.on_youtube)
        self.ui.pushButton_discord.clicked.connect(self.interface_signals.on_discord)
        self.ui.pushButton_github.clicked.connect(self.interface_signals.on_github)
        self.ui.pushButton_add_character.clicked.connect(self.interface_signals.add_character_sync)
        self.ui.pushButton_import_character_card.clicked.connect(self.interface_signals.import_character_card)
        self.ui.pushButton_import_character_image.clicked.connect(self.interface_signals.import_character_avatar)
        self.ui.pushButton_search_character.clicked.connect(self.interface_signals.search_character)
        self.ui.lineEdit_search_character.returnPressed.connect(self.interface_signals.search_character)
        self.ui.pushButton_choose_user_avatar.clicked.connect(self.interface_signals.choose_avatar)
        self.ui.pushButton_turn_off_llm.hide()

        # ComboBoxes
        self.ui.comboBox_conversation_method.currentTextChanged.connect(self.interface_signals.on_comboBox_conversation_method_changed)
        self.ui.comboBox_speech_to_text_method.currentIndexChanged.connect(self.interface_signals.on_comboBox_speech_to_text_method_changed)
        self.ui.comboBox_program_language.currentIndexChanged.connect(self.on_comboBox_program_language_changed)
        self.ui.comboBox_input_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_input_devices_changed)
        self.ui.comboBox_output_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_output_devices_changed)
        self.ui.comboBox_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_translator_changed)
        self.ui.comboBox_target_language_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_target_language_translator_changed)
        self.ui.checkBox_enable_sow_system.stateChanged.connect(self.interface_signals.on_checkBox_enable_sow_system_stateChanged)
        self.ui.comboBox_conversation_method.currentIndexChanged.connect(self.interface_signals.update_api_token)
        self.ui.comboBox_llms.currentIndexChanged.connect(self.interface_signals.on_comboBox_llms_changed)
        self.ui.comboBox_live2d_mode.currentIndexChanged.connect(self.interface_signals.on_comboBox_live2d_mode_changed)
        self.ui.comboBox_llm_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_llm_devices_changed)
        self.ui.comboBox_mode_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_mode_translator_changed)

        # LineEdits
        self.ui.lineEdit_api_token_options.textChanged.connect(self.interface_signals.save_api_token_in_real_time)
        self.ui.lineEdit_base_url_options.textChanged.connect(self.interface_signals.save_custom_url_in_real_time)
        self.ui.lineEdit_user_name_options.textChanged.connect(self.interface_signals.save_username_in_real_time)
        self.ui.lineEdit_user_description_options.textChanged.connect(self.interface_signals.save_userpersonality_in_real_time)
        self.ui.lineEdit_character_name_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_character_description_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_character_personality_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_first_message_building.textChanged.connect(self.interface_signals.update_token_count)
        
        # Sliders
        self.ui.gpu_layers_horizontalSlider.valueChanged.connect(self.interface_signals.save_gpu_layers_in_real_time)
        self.ui.context_size_horizontalSlider.valueChanged.connect(self.interface_signals.save_context_size_in_real_time)
        self.ui.temperature_horizontalSlider.valueChanged.connect(self.interface_signals.save_temperature_in_real_time)
        self.ui.top_p_horizontalSlider.valueChanged.connect(self.interface_signals.save_top_p_in_real_time)
        self.ui.repeat_penalty_horizontalSlider.valueChanged.connect(self.interface_signals.save_repeat_penalty_in_real_time)
        self.ui.max_tokens_horizontalSlider.valueChanged.connect(self.interface_signals.save_max_tokens_in_real_time)
        
        # CheckBox
        self.ui.checkBox_enable_mlock.stateChanged.connect(self.interface_signals.on_checkBox_enable_mlock_stateChanged)
        self.ui.stackedWidget.currentChanged.connect(self.interface_signals.on_stacked_widget_changed)
        self.ui.checkBox_enable_nsfw.stateChanged.connect(self.interface_signals.on_checkBox_enable_nsfw_stateChanged)

    def on_comboBox_program_language_changed(self, index):
        self.configuration.update_main_setting("program_language", index)

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(self.translations.get("language_changed_title", "Restart Required"))
        msg_box.setText(self.translations.get("language_changed_body", "The program needs to be restarted for the changes to take effect."))
        msg_box.setInformativeText(self.translations.get("language_changed_question", "Would you like to restart the program now?"))

        restart_button = msg_box.addButton(self.translations.get("language_changed_yes", "Yes"), QMessageBox.ButtonRole.YesRole)
        cancel_button = msg_box.addButton(self.translations.get("language_changed_no", "No"), QMessageBox.ButtonRole.NoRole)

        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #ffffff;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                padding: 5px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        msg_box.exec()

        if msg_box.clickedButton() == restart_button:
            QApplication.quit()

    def apply_translations(self):
        self.setWindowTitle(self.translations.get("program_title", "Soul of Waifu"))
        self.ui.pushButton_main.setText(self.translations.get("main_button", " Main"))
        self.ui.pushButton_create_character.setText(self.translations.get("create_character_button", " Create Character"))
        self.ui.pushButton_characters_gateway.setText(self.translations.get("characters_gateway_button", " Characters Gateway"))
        self.ui.pushButton_options.setText(self.translations.get("options_button", " Options"))
        self.ui.main_no_characters_advice_label.setText(self.translations.get("no_characters_advice", "You haven\'t added any characters. Click on the button and create it"))
        self.ui.pushButton_create_character_2.setText(self.translations.get("create_character_button_2", " Create Character"))
        self.ui.main_no_characters_description_label.setText(self.translations.get("no_characters_description", "Before you begin a chat with a character, take a moment to customize the program to suit your preferences. \n"
"Once you\'re ready, create your unique character and start the conversation!"))
        self.ui.welcome_label_2.setText(self.translations.get("welcome_label", "Welcome to Soul of Waifu, User"))
        self.ui.add_character_title_label.setText(self.translations.get("add_character_title", "<html><head/><body><p>Enter the character ID to add it to the list</p></body></html>"))
        self.ui.add_character_id_label.setText(self.translations.get("character_id_label", "Character ID:"))
        self.ui.character_id_lineEdit.setPlaceholderText(self.translations.get("placeholder_character_id", "Write Character ID"))
        self.ui.pushButton_add_character.setText(self.translations.get("add_character_button", " ADD"))
        self.ui.pushButton_import_character_card.setText(self.translations.get("import_character_card_button", "Import Character Card"))
        self.ui.character_building_label.setText(self.translations.get("character_building_label", "Character\'s Building"))
        self.ui.character_image_building_label.setText(self.translations.get("character_image_building_label", "Character\'s Image"))
        self.ui.character_name_building_label.setText(self.translations.get("character_name_building_label", "Character\'s Name"))
        self.ui.lineEdit_character_name_building.setPlaceholderText(self.translations.get("placeholder_character_name", "Write your character\'s name here"))
        self.ui.character_description_building_label.setText(self.translations.get("character_description_building_label", "Character\'s Description"))
        self.ui.textEdit_character_description_building.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>")
        self.ui.textEdit_character_description_building.setPlaceholderText(self.translations.get("placeholder_character_description", "Write your character\'s description here"))
        self.ui.character_personality_building_label.setText(self.translations.get("character_personality_building_label", "Character\'s Personality"))
        self.ui.textEdit_character_personality_building.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400;\"><br /></p></body></html>")
        self.ui.textEdit_character_personality_building.setPlaceholderText(self.translations.get("placeholder_character_personality", "Write your character\'s personality here"))
        self.ui.first_message_building_label.setText(self.translations.get("first_message_building_label", "First Message"))
        self.ui.textEdit_first_message_building.setHtml("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400;\"><br /></p></body></html>")
        self.ui.textEdit_first_message_building.setPlaceholderText(self.translations.get("placeholder_first_message", "Write your character\'s first message here"))
        self.ui.pushButton_create_character_3.setText(self.translations.get("create_character_button_3", "Create Character"))
        self.ui.total_tokens_building_label.setText(self.translations.get("total_tokens_label", "Total Tokens: 0"))
        self.ui.lineEdit_search_character.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.conversation_method_title_label.setText(self.translations.get("conversation_method_title", "Conversation Method"))
        self.ui.conversation_method_token_title_label.setText(self.translations.get("api_label", "API:"))
        self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write your API value here"))
        self.ui.sow_system_title_label.setText(self.translations.get("sow_system_title", "Soul of Waifu System"))
        self.ui.checkBox_enable_sow_system.setText(self.translations.get("enable_sow_system_checkbox", "Enable Soul of Waifu System"))
        self.ui.conversation_method_options_label.setText(self.translations.get("conversation_method_label", "Conversation method:"))
        self.ui.comboBox_conversation_method.setItemText(0, self.translations.get("conversation_method_item_cai", "Character AI"))
        self.ui.comboBox_conversation_method.setItemText(1, self.translations.get("conversation_method_item_mistralai", "Mistral AI"))
        self.ui.comboBox_conversation_method.setItemText(2, self.translations.get("conversation_method_item_openai", "Open AI"))
        self.ui.comboBox_conversation_method.setItemText(3, self.translations.get("conversation_method_item_openrouter", "OpenRouter"))
        self.ui.choose_your_avatar_label.setText(self.translations.get("choose_your_avatar_label", "Choose your avatar:"))
        self.ui.speech_to_text_title_label.setText(self.translations.get("speech_to_text_title", "Speech-To-Text"))
        self.ui.speech_to_text_method_label.setText(self.translations.get("speech_to_text_method_label", "Speech-To-Text method:"))
        self.ui.comboBox_speech_to_text_method.setItemText(0, self.translations.get("speech_to_text_method_google_en", "Google STT English"))
        self.ui.comboBox_speech_to_text_method.setItemText(1, self.translations.get("speech_to_text_method_google_ru", "Google STT Russian"))
        self.ui.comboBox_speech_to_text_method.setItemText(2, self.translations.get("speech_to_text_method_vosk_en", "Vosk English"))
        self.ui.comboBox_speech_to_text_method.setItemText(3, self.translations.get("speech_to_text_method_vosk_ru", "Vosk Russian"))
        self.ui.comboBox_speech_to_text_method.setItemText(4, self.translations.get("speech_to_text_method_whisper", "Local Whisper"))
        self.ui.choose_your_name_label.setText(self.translations.get("choose_your_name_label", "Write your name:"))
        self.ui.choose_your_description_label.setText(self.translations.get("choose_your_description_label", "Write your description:"))
        self.ui.user_building_title_label.setText(self.translations.get("user_building_title", "User Building"))
        self.ui.lineEdit_user_name_options.setPlaceholderText(self.translations.get("placeholder_user_name", "Your name"))
        self.ui.lineEdit_user_description_options.setPlaceholderText(self.translations.get("placeholder_user_description", "Your description"))
        self.ui.openrouter_models_options_label.setText(self.translations.get("openrouter_models_label", "Model:"))
        self.ui.lineEdit_search_openrouter_models.setPlaceholderText(self.translations.get("placeholder_search_openrouter_models", "Search"))
        self.ui.lineEdit_base_url_options.setPlaceholderText(self.translations.get("placeholder_base_url", "Write your custom endpoint url here (Optional)"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.configuration_tab), self.translations.get("configuration_tab", "Configuration"))
        self.ui.tabWidget_characters_gateway.setTabText(self.ui.tabWidget_characters_gateway.indexOf(self.ui.tab_character_ai), "Character AI")
        self.ui.tabWidget_characters_gateway.setTabText(self.ui.tabWidget_characters_gateway.indexOf(self.ui.tab_character_cards), "Character Card")
        self.ui.language_title_label.setText(self.translations.get("language_title", "Language"))
        self.ui.comboBox_program_language.setItemText(0, self.translations.get("program_language_item_en", "English"))
        self.ui.comboBox_program_language.setItemText(1, self.translations.get("program_language_item_ru", "Russian"))
        self.ui.devices_title_label.setText(self.translations.get("devices_title", "Devices"))
        self.ui.input_device_label.setText(self.translations.get("input_device_label", "Input device:"))
        self.ui.output_device_label.setText(self.translations.get("output_device_label", "Output device:"))
        self.ui.program_language_label.setText(self.translations.get("program_language_label", "Program language:"))
        self.ui.translator_title_label.setText(self.translations.get("translator_title", "Translator"))
        self.ui.choose_translator_label.setText(self.translations.get("choose_translator_label", "Choose translator:"))
        self.ui.comboBox_translator.setItemText(0, self.translations.get("translator_item_none", "None"))
        self.ui.comboBox_translator.setItemText(1, self.translations.get("translator_item_google", "Google"))
        self.ui.comboBox_translator.setItemText(2, self.translations.get("translator_item_yandex", "Yandex"))
        self.ui.comboBox_translator.setItemText(3, self.translations.get("translator_item_local", "Local Translator"))
        self.ui.target_language_translator_label.setText(self.translations.get("target_language_label", "Target Language:"))
        self.ui.comboBox_target_language_translator.setItemText(0, self.translations.get("target_language_item_ru", "Russian"))
        self.ui.comboBox_mode_translator.setItemText(0, self.translations.get("translator_mode_item_both", "Both"))
        self.ui.comboBox_mode_translator.setItemText(1, self.translations.get("translator_mode_item_user", "User Message"))
        self.ui.comboBox_mode_translator.setItemText(2, self.translations.get("translator_mode_item_character", "Character Message"))
        self.ui.mode_translator_label.setText(self.translations.get("mode_translator_label", "Mode:"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.system_tab), self.translations.get("system_tab", "System"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.llm_tab), self.translations.get("local_llm_tab", "Local LLM"))
        self.ui.character_name_chat.setText(self.translations.get("character_name_chat", "Character name"))
        self.ui.textEdit_write_user_message.setPlaceholderText(self.translations.get("write_user_message_placeholder", "Write your message to character..."))
        self.ui.creator_label.setText(self.translations.get("creator_label", "Created by Jofi"))
        self.ui.version_label.setText(self.translations.get("version_label", "v2.1.0"))
        self.ui.menu_sow.setTitle(self.translations.get("menu_sow", "Soul of Waifu"))
        self.ui.menu_help.setTitle(self.translations.get("menu_help", "Help"))
        self.ui.action_about_program.setText(self.translations.get("about_program", "About Soul of Waifu"))
        self.ui.action_get_token_from_character_ai.setText(self.translations.get("get_token_from_character_ai", "Get Token from Character AI"))
        self.ui.action_create_new_character.setText(self.translations.get("create_new_character", "Create new character"))
        self.ui.action_options.setText(self.translations.get("options_menu", "Options"))
        self.ui.action_discord.setText(self.translations.get("discord_support", "Get support from Discord"))
        self.ui.action_github.setText(self.translations.get("github_support", "Get support from GitHub"))
        self.ui.action_faq.setText(self.translations.get("faq", "FAQ"))
        self.ui.choose_live2d_mode_label.setText(self.translations.get("live2d_mode_label", "Choose mode for Live2d model:"))
        self.ui.comboBox_live2d_mode.setItemText(0, self.translations.get("live2d_mode_with_gui", "With GUI"))
        self.ui.comboBox_live2d_mode.setItemText(1, self.translations.get("live2d_mode_without_gui", "Without GUI"))
        self.ui.comboBox_llms.setWhatsThis(self.translations.get("comboBox_llm_what_is_it", "<html><head/><body><p>Choose your Local LLM from the list.</p></body></html>"))
        self.ui.llm_options_label.setText(self.translations.get("llm_options_label", "Local Model:"))
        self.ui.llm_title_label.setText(self.translations.get("llm_title", "Local LLM Settings"))
        self.ui.choose_llm_device_label.setText(self.translations.get("choose_llm_device_label", "Choose device:"))
        self.ui.comboBox_llm_devices.setItemText(0, "CPU")
        self.ui.comboBox_llm_devices.setItemText(1, "GPU")
        self.ui.gpu_layers_label.setText(self.translations.get("gpu_layers_label", "GPU Layers:"))
        self.ui.checkBox_enable_mlock.setText(self.translations.get("enable_mlock_checkbox", "Enable MLock"))
        self.ui.context_size_label.setText(self.translations.get("context_size_label", "Context Size:"))
        self.ui.llm_title_label_2.setText(self.translations.get("llm_title_label_settings", "Local LLM Conversation Settings:"))
        self.ui.reapet_penalty_label.setText(self.translations.get("repeat_penalty_label", "Repeat Penalty:"))
        self.ui.temperature_label.setText(self.translations.get("temperature_label", "Temperature:"))
        self.ui.temperature_value_label.setText(self.translations.get("temperature_value", "Value: "))
        self.ui.top_p_label.setText(self.translations.get("top_p_label", "Top P:"))
        self.ui.top_p_value_label.setText(self.translations.get("top_p_value", "Value: "))
        self.ui.max_tokens_label.setText(self.translations.get("max_tokens_label", "Max Tokens:"))
        self.ui.repeat_penalty_value_label.setText(self.translations.get("repeat_penalty_value", "Value: "))
        self.ui.max_tokens_value_label.setText(self.translations.get("max_tokens_value", "Value: "))
        self.ui.context_size_value_label.setText(self.translations.get("context_size_value", "Value: "))
        self.ui.gpu_layers_value_label.setText(self.translations.get("gpu_layers_value", "Value: "))
        self.ui.checkBox_enable_nsfw.setText(self.translations.get("nsfw_checkbox", "NSFW"))
        self.ui.pushButton_turn_off_llm.setText(self.translations.get("turn_off_llm", "Turn off the LLM"))

    def check_for_updates(self, current_version):
        try:
            repo_url = "https://api.github.com/repos/jofizcd/Soul-of-Waifu/releases/latest"
            response = requests.get(repo_url)
            latest_release = response.json()
            latest_version = latest_release["tag_name"]

            if latest_version != current_version:
                return latest_version, latest_release["html_url"]
            else:
                return None, None
        except Exception as e:
            print(f"Failed to check for updates: {e}")
            return None, None

    def show_update_dialog(self, latest_version, github_url):
        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        msg_box.setWindowTitle(self.translations.get("update_available_title", "Update Available"))

        msg_box.setText(self.translations.get("update_available_body", "A new version is available: ") + latest_version)
        msg_box.setInformativeText(self.translations.get("update_available_info", "Would you like to update the program?"))

        close_button = msg_box.addButton(self.translations.get("update_available_close", "Close"), QMessageBox.ButtonRole.RejectRole)
        github_button = msg_box.addButton(self.translations.get("update_available_link", "Go to GitHub"), QMessageBox.ButtonRole.ActionRole)

        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                border: 1px solid #3b3b3b;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                min-width: 100px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #6a6a6a;
            }
        """)

        msg_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg_box.setDefaultButton(github_button)

        msg_box.exec()

        if msg_box.clickedButton() == github_button:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(github_url))

    def load_fonts_from_folder(self, folder_path):
        for font_file in os.listdir(folder_path):
            font_path = os.path.join(folder_path, font_file)
            if font_path.endswith(('.ttf')):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id == -1:
                    print(f"Error during load a font: {font_file}")
                else:
                    pass

if __name__ == "__main__":
    if sys.platform == 'win32':
        app_id = "com.jofizcd.soul_of_waifu.v2"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    main_window = MainWindow()
    main_window.setWindowIcon(QtGui.QIcon("resources\\icons\\logotype.ico"))
    fonts_folder = "resources/data/font"
    main_window.load_fonts_from_folder(fonts_folder)

    main_window.show()    

    current_version = "v2.1.0"
    latest_version, github_url = main_window.check_for_updates(current_version)
    if latest_version:
        main_window.show_update_dialog(latest_version, github_url)     

    loop.run_forever()
