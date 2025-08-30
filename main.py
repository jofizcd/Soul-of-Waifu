import os
import sys
import yaml
import torch
import ctypes
import psutil
import GPUtil
import asyncio
import logging
import requests
from datetime import datetime
from qasync import QEventLoop, asyncSlot

from PyQt6.QtGui import QFontDatabase
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from app.configuration import configuration
from app.gui.icons import resources
from app.gui import interface_signals
from app.utils.ai_clients import local_ai_client
from app.gui.sowInterface import Ui_MainWindow

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file = os.path.join(LOG_DIR, f"sow_{timestamp}.log")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(name)s: %(message)s')

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logging.root = logger
logging.root.setLevel(logging.INFO)

logger.propagate = False

logger.info("========================================")
logger.info(f"Logging started. Output will be written to: {log_file}")
logger.info(f"All logs will be saved in 'logs' folder")
logger.info("========================================")

class MainWindow(QMainWindow):
    """
    Main application window for 'Soul of Waifu'.
    """
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.translations = {}

        self.draggable = False
        self.offset = None

        self.ui.minimize_btn.clicked.connect(self.showMinimized)
        self.ui.maximize_btn.clicked.connect(self.toggle_maximize)
        self.ui.close_app_btn.clicked.connect(self.close)

        self.configuration = configuration.ConfigurationSettings()
        selected_language = self.configuration.get_main_setting("program_language")
    
        match selected_language:
            case 0:
                self.load_translation("en")
                self.apply_translations()
            case 1:
                self.load_translation("ru")
                self.apply_translations()

        self.interface_signals = interface_signals.InterfaceSignals(self.ui, self)
        self.local_ai_client = local_ai_client.LocalAI(self.ui)

        self.create_size_grips()
        QtCore.QTimer.singleShot(0, self.update_size_grip_positions)

        self.interface_signals.load_background_images_to_comboBox()
        self.interface_signals.load_ambient_sound_to_comboBox()
        self.interface_signals.load_combobox()
        self.setup_interface_signals()
        self.interface_signals.load_audio_devices()
        self.interface_signals.update_api_token()
        self.check_pc_specs()

        self.interface_signals.initialize_api_token_line_edit()
        self.interface_signals.initialize_gpu_layers_horizontalSlider()
        self.interface_signals.initialize_context_size_horizontalSlider()
        self.interface_signals.initialize_temperature_horizontalSlider()
        self.interface_signals.initialize_top_p_horizontalSlider()
        self.interface_signals.initialize_repeat_penalty_horizontalSlider()
        self.interface_signals.initialize_max_tokens_horizontalSlider()

        asyncio.ensure_future(self.interface_signals.set_main_tab())

    def load_translation(self, language):
        """
        Loads translation strings from a YAML file based on the program language.
        """
        file_path = f"app/translations/{language}.yaml"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                self.translations = yaml.safe_load(file)
        else:
            self.translations = {}
    
    def apply_translations(self):
        """
        Applies loaded translations to static UI elements.
        """
        self.setWindowTitle(self.translations.get("program_title", "Soul of Waifu"))
        
        # Left Menu
        self.ui.pushButton_main.setText(self.translations.get("main_button", " Main"))
        self.ui.pushButton_create_character.setText(self.translations.get("create_character_button", " Create Character"))
        self.ui.pushButton_characters_gateway.setText(self.translations.get("characters_gateway_button", " Characters Gateway"))
        self.ui.pushButton_models_hub.setText(self.translations.get("models_hub_button", " Models Hub"))
        self.ui.pushButton_options.setText(self.translations.get("options_button", " Options"))
        self.ui.version_label.setText(self.translations.get("version_label", "v2.2.0"))
        
        # Main Tab Without Characters
        self.ui.main_no_characters_advice_label.setText(self.translations.get("no_characters_advice", "You haven\'t added any characters. Click on the button and create it"))
        self.ui.pushButton_create_character_2.setText(self.translations.get("create_character_button_2", " Create Character"))
        self.ui.main_no_characters_description_label.setText(self.translations.get("no_characters_description", "Before you begin a chat with a character, take a moment to customize the program to suit your preferences. \n"
"Once you\'re ready, create your unique character and start the conversation!"))
        
        # Main Tab With Characters
        self.ui.welcome_label_2.setText(self.translations.get("welcome_label", "Welcome to Soul of Waifu, User"))
        self.ui.lineEdit_search_character_menu.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        
        # Character AI Creation
        self.ui.add_character_title_label.setText(self.translations.get("add_character_title", "<html><head/><body><p>Enter the character ID to add it to the list</p></body></html>"))
        self.ui.add_character_id_label.setText(self.translations.get("character_id_label", "Character ID:"))
        self.ui.character_id_lineEdit.setPlaceholderText(self.translations.get("placeholder_character_id", "Write Character ID"))
        self.ui.pushButton_add_character.setText(self.translations.get("add_character_button", " ADD"))
        
        # Character Creation
        self.ui.pushButton_import_character_card.setText(self.translations.get("import_character_card_button", " Import Character Card"))
        self.ui.character_building_label.setText(self.translations.get("character_building_label", "Character Creation"))
        self.ui.character_image_building_label.setText(self.translations.get("character_image_building_label", "Character\'s Image"))
        self.ui.character_name_building_label.setText(self.translations.get("character_name_building_label", "Character\'s Name"))
        self.ui.lineEdit_character_name_building.setPlaceholderText(self.translations.get("placeholder_character_name", "The name of your character"))
        self.ui.character_description_building_label.setText(self.translations.get("character_description_building_label", "Character\'s Description"))
        self.ui.textEdit_character_description_building.setPlaceholderText(self.translations.get("placeholder_character_description", "Used to provide the character description and other essential information the AI should know. It should contain all important facts"))
        self.ui.character_personality_building_label.setText(self.translations.get("character_personality_building_label", "Character\'s Personality"))
        self.ui.textEdit_character_personality_building.setPlaceholderText(self.translations.get("placeholder_character_personality", "A summary of the character’s personality"))
        self.ui.character_scenario_building_label.setText(self.translations.get("scenario", "Scenario"))
        self.ui.textEdit_scenario.setPlaceholderText(self.translations.get("placeholder_scenario", "Conversation scenario"))
        self.ui.first_message_building_label.setText(self.translations.get("first_message_building_label", "First Message"))
        self.ui.textEdit_first_message_building.setPlaceholderText(self.translations.get("placeholder_first_message", "The First Message is crucial as it sets the tone, style, and manner in which the character will communicate"))
        self.ui.example_messages_building_label.setText(self.translations.get("example_messages_title", "Example Messages"))
        self.ui.textEdit_example_messages.setPlaceholderText(self.translations.get("placeholder_example_messages", "Describes how the character speaks. Before each example, you must insert the <START> macro"))
        self.ui.alternate_greetings_building_label.setText(self.translations.get("alternate_greetings_label", "Alternate Greetings"))
        self.ui.textEdit_alternate_greetings.setPlaceholderText(self.translations.get("placeholder_alternate_greetings", "You can include as many alternative greetings as you like. Before each alternate greeting, you must insert the <GREETING> macro"))
        self.ui.creator_notes_building_label.setText(self.translations.get("creator_notes_label", "Creator Notes"))
        self.ui.textEdit_creator_notes.setPlaceholderText(self.translations.get("placeholder_creator_notes", "Any additional notes about the character card"))
        self.ui.character_version_building_label.setText(self.translations.get("card_version_label", "Character Card Version"))
        self.ui.textEdit_character_version.setPlaceholderText(self.translations.get("placeholder_card_version", "The version of the character card"))
        self.ui.user_persona_building_label.setText(self.translations.get("user_persona_building_label", "User Persona"))
        self.ui.system_prompt_building_label.setText(self.translations.get("system_prompt_building_label", "System Prompt Preset"))
        self.ui.lorebook_building_label.setText(self.translations.get("lorebook_building_label", "Lorebook"))
        self.ui.pushButton_create_character_3.setText(self.translations.get("create_character_button_3", "Create Character"))
        self.ui.total_tokens_building_label.setText(self.translations.get("total_tokens_label", "Total Tokens: 0"))
        
        # Models Hub
        self.ui.lineEdit_search_model.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.pushButton_models_hub_my_models.setText(self.translations.get("models_hub_my_models", " My models"))
        self.ui.pushButton_models_hub_popular.setText(self.translations.get("models_hub_popular", " Popular"))
        self.ui.pushButton_models_hub_recommendations.setText(self.translations.get("models_hub_recommendations", "Recommendations"))

        # Options
        self.ui.lineEdit_search_character.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.conversation_method_title_label.setText(self.translations.get("conversation_method_title", "Conversation Method"))
        self.ui.conversation_method_token_title_label.setText(self.translations.get("api_label", "API:"))
        self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write your API value here"))
        self.ui.lineEdit_mistral_model.setPlaceholderText(self.translations.get("placeholder_mistral_model_endpoint", "Enter the API endpoint of the mistral model here"))
        self.ui.sow_system_title_label.setText(self.translations.get("sow_system_title", "Soul of Waifu System"))
        self.ui.checkBox_enable_sow_system.setText(self.translations.get("enable_sow_system_checkbox", "Enable Soul of Waifu System"))
        self.ui.choose_model_fps.setText(self.translations.get("choose_model_fps", "Choose model FPS"))
        self.ui.comboBox_model_fps.setItemText(0, self.translations.get("model_fps_30", "30 FPS"))
        self.ui.comboBox_model_fps.setItemText(1, self.translations.get("model_fps_60", "60 FPS"))
        self.ui.comboBox_model_fps.setItemText(2, self.translations.get("model_fps_120", "120 FPS"))
        self.ui.choose_model_background.setText(self.translations.get("choose_model_background", "Choose model background"))
        self.ui.comboBox_model_background.setItemText(0, self.translations.get("model_background_1", "Color"))
        self.ui.comboBox_model_background.setItemText(1, self.translations.get("model_background_2", "Custom Image"))
        self.ui.choose_model_bg_color.setText(self.translations.get("choose_model_background_color", "Choose background color"))
        self.ui.comboBox_model_bg_color.setItemText(0, self.translations.get("model_background_color_1", "Black"))
        self.ui.comboBox_model_bg_color.setItemText(1, self.translations.get("model_background_color_2", "Deep Blue"))
        self.ui.comboBox_model_bg_color.setItemText(2, self.translations.get("model_background_color_3", "Vinous"))
        self.ui.comboBox_model_bg_color.setItemText(3, self.translations.get("model_background_color_4", "Dark Green"))
        self.ui.comboBox_model_bg_color.setItemText(4, self.translations.get("model_background_color_5", "Soft Purple"))
        self.ui.comboBox_model_bg_color.setItemText(5, self.translations.get("model_background_color_6", "Warm Coal Grey"))
        self.ui.choose_model_bg_image.setText(self.translations.get("choose_model_background_image", "Choose background image"))
        self.ui.checkBox_enable_ambient.setText(self.translations.get("enable_ambient_checkbox", "Enable Ambient Sound"))
        self.ui.checkBox_enable_memory.setText(self.translations.get("enable_enhanced_memory", "Enable Smart Memory"))
        self.ui.sow_system_modules_title_label.setText(self.translations.get("sow_system_modules_title", "Modules"))
        self.ui.conversation_method_options_label.setText(self.translations.get("conversation_method_label", "Conversation method:"))
        self.ui.comboBox_conversation_method.setItemText(0, self.translations.get("conversation_method_item_cai", "Character AI"))
        self.ui.comboBox_conversation_method.setItemText(1, self.translations.get("conversation_method_item_mistralai", "Mistral AI"))
        self.ui.comboBox_conversation_method.setItemText(2, self.translations.get("conversation_method_item_openai", "Open AI"))
        self.ui.comboBox_conversation_method.setItemText(3, self.translations.get("conversation_method_item_openrouter", "OpenRouter"))
        self.ui.speech_to_text_method_label.setText(self.translations.get("speech_to_text_method_label", "Speech-To-Text method:"))
        self.ui.comboBox_speech_to_text_method.setItemText(0, self.translations.get("speech_to_text_method_vosk_en", "Vosk English"))
        self.ui.comboBox_speech_to_text_method.setItemText(1, self.translations.get("speech_to_text_method_vosk_ru", "Vosk Russian"))
        self.ui.comboBox_speech_to_text_method.setItemText(2, self.translations.get("speech_to_text_method_whisper", "Local Whisper"))
        self.ui.user_building_title_label.setText(self.translations.get("user_building_title", "User Persona"))
        self.ui.personas_button.setText(self.translations.get("personas_button", " Open Personas Editor"))
        self.ui.openrouter_models_options_label.setText(self.translations.get("openrouter_models_label", "Model:"))
        self.ui.lineEdit_search_openrouter_models.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
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
        self.ui.computer_specs_title_label.setText(self.translations.get("computer_specs_title", "Computer Specs"))
        self.ui.mode_translator_label.setText(self.translations.get("mode_translator_label", "Mode:"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.system_tab), self.translations.get("system_tab", "System"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.llm_tab), self.translations.get("local_llm_tab", "LLM Settings"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.sow_system_tab), self.translations.get("sow_system_tab", "Soul of Waifu Modules"))
        
        # Chat
        self.ui.character_name_chat.setText(self.translations.get("character_name_chat", "Character name"))
        self.ui.textEdit_write_user_message.setPlaceholderText(self.translations.get("write_user_message_placeholder", "Write your message to character..."))
        
        # LLM Options
        self.ui.choose_live2d_mode_label.setText(self.translations.get("live2d_mode_label", "Choose mode:"))
        self.ui.comboBox_live2d_mode.setItemText(0, self.translations.get("live2d_mode_with_gui", "With GUI"))
        self.ui.comboBox_live2d_mode.setItemText(1, self.translations.get("live2d_mode_without_gui", "Without GUI"))
        self.ui.llm_options_label.setText(self.translations.get("llm_options_label", "Local Model:"))
        self.ui.llm_title_label.setText(self.translations.get("llm_title", "Local LLM Settings"))
        self.ui.choose_llm_device_label.setText(self.translations.get("choose_llm_device_label", "Choose device:"))
        self.ui.choose_llm_gpu_device_label.setText(self.translations.get("choose_llm_gpu_device_label", "Choose backend:"))
        self.ui.comboBox_llm_devices.setItemText(0, "CPU")
        self.ui.comboBox_llm_devices.setItemText(1, "GPU")
        self.ui.comboBox_llm_gpu_devices.setItemText(0, "Vulkan")
        self.ui.comboBox_llm_gpu_devices.setItemText(1, "CUDA")
        self.ui.gpu_layers_label.setText(self.translations.get("gpu_layers_label", "GPU Layers:"))
        self.ui.checkBox_enable_mlock.setText(self.translations.get("enable_mlock_checkbox", "Enable MLock"))
        self.ui.checkBox_enable_flash_attention.setText(self.translations.get("enable_flash_attention_checkbox", "Enable Flash Attention"))
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
        self.ui.system_prompt_button.setText(self.translations.get("system_prompt_button", " System Prompt Editor"))
        self.ui.lorebook_editor_button.setText(self.translations.get("lorebook_editor_button", " Lorebook Editor"))
        self.ui.checkBox_enable_nsfw.setText(self.translations.get("nsfw_checkbox", "NSFW"))
        self.ui.pushButton_turn_off_llm.setText(self.translations.get("turn_off_llm", "Shutdown Model"))
        self.ui.lineEdit_server.setText("http://localhost:8080/v1")

        # Tooltips
        self.ui.checkBox_enable_mlock.setToolTip(self.translations.get("mlock_tooltip", "Enable MLock"))
        self.ui.checkBox_enable_flash_attention.setToolTip(self.translations.get("flashattention_tooltip", "Enable Flash Attention"))
        self.ui.checkBox_enable_ambient.setToolTip(self.translations.get("ambient_sound_tooltip", "Enable Ambient Sound Module"))
        self.ui.checkBox_enable_memory.setToolTip(self.translations.get("smart_memory_tooltip", "Enable Smart Memory Module"))
        self.ui.checkBox_enable_sow_system.setToolTip(self.translations.get("sow_system_tooltip", "Enable Soul of Waifu System Module"))
        self.ui.gpu_layers_horizontalSlider.setToolTip(self.translations.get("gpu_layers_tooltip", "GPU Layer Offloading"))
        self.ui.context_size_horizontalSlider.setToolTip(self.translations.get("context_size_tooltip", "Adjusting context window"))
        self.ui.temperature_horizontalSlider.setToolTip(self.translations.get("temperature_tooltip", "Temperature"))
        self.ui.top_p_horizontalSlider.setToolTip(self.translations.get("top_p_tooltip", "Top P"))
        self.ui.repeat_penalty_horizontalSlider.setToolTip(self.translations.get("repeat_penalty_tooltip", "Repeat Penalty"))
        self.ui.max_tokens_horizontalSlider.setToolTip(self.translations.get("max_tokens_tooltip", "Max Tokens"))
        self.ui.personas_button.setToolTip(self.translations.get("personas_button_tooltip", "Open personas editor"))
        self.ui.system_prompt_button.setToolTip(self.translations.get("system_prompt_button_tooltip", "Open system prompt editor"))
        self.ui.lorebook_editor_button.setToolTip(self.translations.get("lorebook_editor_button_tooltip", "Open lorebooks editor"))

    def on_comboBox_program_language_changed(self, index):
        """
        Handles the event when the program language selection is changed.

        Updates the configuration and prompts the user to restart the application
        for the changes to take effect.
        """
        self.configuration.update_main_setting("program_language", index)

        msg_box = QMessageBox()
        msg_box.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        msg_box.setWindowTitle(self.translations.get("language_changed_title", "Restart Required"))
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: rgb(27, 27, 27);
                color: rgb(227, 227, 227);
            }
            QLabel {
                color: rgb(227, 227, 227);
            }
        """)

        first_text = self.translations.get("language_changed_body", "The program needs to be restarted for the changes to take effect.")
        second_text = self.translations.get("language_changed_question", "Would you like to restart the program now?")

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
                    </style>
                </head>
                <body>
                    <h1>{first_text}</h1>
                    <p>{second_text}</p>
                </body>
            </html>
        """

        msg_box.setText(message_text)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        reply = msg_box.exec()

        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    def setup_interface_signals(self):
        """
        Connects signals for all UI elements to their respective handlers.
        """
        # PushButtons
        self.ui.pushButton_main.clicked.connect(self.interface_signals.on_pushButton_main_clicked)
        self.ui.pushButton_create_character.clicked.connect(self.interface_signals.set_conversation_method_dialog)
        self.ui.pushButton_create_character_2.clicked.connect(self.interface_signals.set_conversation_method_dialog)
        self.ui.pushButton_create_character_3.clicked.connect(self.interface_signals.add_character_sync)
        self.ui.pushButton_characters_gateway.clicked.connect(self._on_characters_gateway_clicked)
        self.ui.pushButton_models_hub.clicked.connect(self.interface_signals.on_pushButton_models_hub_clicked)
        self.ui.pushButton_options.clicked.connect(self.interface_signals.on_pushButton_options_clicked)
        self.ui.about_btn.clicked.connect(self.interface_signals.set_about_program_button)
        self.ui.pushButton_youtube.clicked.connect(self.interface_signals.on_youtube)
        self.ui.pushButton_discord.clicked.connect(self.interface_signals.on_discord)
        self.ui.pushButton_github.clicked.connect(self.interface_signals.on_github)
        self.ui.pushButton_add_character.clicked.connect(self.interface_signals.add_character_sync)
        self.ui.pushButton_import_character_card.clicked.connect(self.interface_signals.import_character_card)
        self.ui.pushButton_export_character_card.clicked.connect(self.interface_signals.export_character_card)
        self.ui.pushButton_import_character_image.clicked.connect(self.interface_signals.import_character_avatar)
        self.ui.pushButton_search_character.clicked.connect(self._on_search_characters_gateway_clicked)
        self.ui.pushButton_search_model.clicked.connect(self.interface_signals.start_search)
        self.ui.pushButton_models_hub_recommendations.clicked.connect(self.interface_signals.show_recommended_models)
        self.ui.pushButton_models_hub_popular.clicked.connect(self.interface_signals.show_popular_models)
        self.ui.pushButton_models_hub_my_models.clicked.connect(self.interface_signals.show_my_models)
        self.ui.pushButton_reload_models.clicked.connect(self.interface_signals.show_my_models)
        self.ui.pushButton_reload_bg_image.clicked.connect(self.interface_signals.load_background_images_to_comboBox)
        self.ui.pushButton_reload_ambient.clicked.connect(self.interface_signals.load_ambient_sound_to_comboBox)
        self.ui.lineEdit_search_character.returnPressed.connect(self._on_search_characters_gateway_clicked)
        self.ui.lineEdit_search_model.returnPressed.connect(self.interface_signals.start_search)
        self.ui.personas_button.clicked.connect(self.interface_signals.open_personas_editor)
        self.ui.system_prompt_button.clicked.connect(self.interface_signals.open_system_prompt_editor)
        self.ui.lorebook_editor_button.clicked.connect(self.interface_signals.open_lorebook_editor)
        self.ui.pushButton_author_notes.clicked.connect(self.interface_signals.open_author_notes_editor)
        self.ui.pushButton_change_chat_background.clicked.connect(self.interface_signals.open_chat_background_changer)
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
        self.ui.checkBox_enable_memory.stateChanged.connect(self.interface_signals.on_checkBox_enable_memory_stateChanged)
        self.ui.comboBox_conversation_method.currentIndexChanged.connect(self.interface_signals.update_api_token)
        self.ui.comboBox_live2d_mode.currentIndexChanged.connect(self.interface_signals.on_comboBox_live2d_mode_changed)
        self.ui.comboBox_model_fps.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_fps_changed)
        self.ui.comboBox_model_background.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_background_changed)
        self.ui.comboBox_model_bg_color.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_bg_color_changed)
        self.ui.comboBox_model_bg_image.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_bg_image_changed)
        self.ui.comboBox_ambient_mode.currentIndexChanged.connect(self.interface_signals.on_comboBox_ambient_mode_changed)
        self.ui.comboBox_llm_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_llm_devices_changed)
        self.ui.comboBox_llm_gpu_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_llm_gpu_devices_changed)
        self.ui.comboBox_mode_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_mode_translator_changed)

        # LineEdits
        self.ui.lineEdit_api_token_options.textChanged.connect(self.interface_signals.save_api_token_in_real_time)
        self.ui.lineEdit_base_url_options.textChanged.connect(self.interface_signals.save_custom_url_in_real_time)
        self.ui.lineEdit_mistral_model.textChanged.connect(self.interface_signals.save_mistral_model_endpoint_in_real_time)
        self.ui.lineEdit_character_name_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_character_description_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_character_personality_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_first_message_building.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_scenario.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_example_messages.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.textEdit_alternate_greetings.textChanged.connect(self.interface_signals.update_token_count)
        self.ui.lineEdit_gpuLayers.editingFinished.connect(self.interface_signals.update_gpu_layers_from_line_edit)
        self.ui.lineEdit_contextSize.editingFinished.connect(self.interface_signals.update_context_size_from_line_edit)
        self.ui.lineEdit_temperature.editingFinished.connect(self.interface_signals.update_temperature_from_line_edit)
        self.ui.lineEdit_topP.editingFinished.connect(self.interface_signals.update_top_p_from_line_edit)
        self.ui.lineEdit_repeatPenalty.editingFinished.connect(self.interface_signals.update_repeat_penalty_from_line_edit)
        self.ui.lineEdit_maxTokens.editingFinished.connect(self.interface_signals.update_max_tokens_from_line_edit)
        
        # Sliders
        self.ui.gpu_layers_horizontalSlider.valueChanged.connect(self.interface_signals.save_gpu_layers_in_real_time)
        self.ui.context_size_horizontalSlider.valueChanged.connect(self.interface_signals.save_context_size_in_real_time)
        self.ui.temperature_horizontalSlider.valueChanged.connect(self.interface_signals.save_temperature_in_real_time)
        self.ui.top_p_horizontalSlider.valueChanged.connect(self.interface_signals.save_top_p_in_real_time)
        self.ui.repeat_penalty_horizontalSlider.valueChanged.connect(self.interface_signals.save_repeat_penalty_in_real_time)
        self.ui.max_tokens_horizontalSlider.valueChanged.connect(self.interface_signals.save_max_tokens_in_real_time)
        
        # CheckBox
        self.ui.checkBox_enable_mlock.stateChanged.connect(self.interface_signals.on_checkBox_enable_mlock_stateChanged)
        self.ui.checkBox_enable_flash_attention.stateChanged.connect(self.interface_signals.on_checkBox_enable_flash_attention_stateChanged)
        self.ui.stackedWidget.currentChanged.connect(self.interface_signals.on_stacked_widget_changed)
        self.ui.checkBox_enable_nsfw.stateChanged.connect(self.interface_signals.on_checkBox_enable_nsfw_stateChanged)
        self.ui.checkBox_enable_ambient.stateChanged.connect(self.interface_signals.on_checkBox_enable_ambient_stateChanged)

    @asyncSlot()
    async def _on_characters_gateway_clicked(self):
        await self.interface_signals.open_characters_gateway()

    @asyncSlot()
    async def _on_search_characters_gateway_clicked(self):
        await self.interface_signals.search_character()

    def check_pc_specs(self):
        """
        Detects and displays basic PC specifications such as RAM and GPU info.
        
        Updates:
            - RAM label in the UI
            - GPU label in the UI
            - Configuration with available system memory (in GB)
        """
        memory_info = psutil.virtual_memory()
        available_memory = round(memory_info.total / 1024 ** 3, 2)
        self.ui.ram_label.setText(f"{available_memory} GB RAM")

        gpu_info = self.translations.get("no_gpu", "No GPU")
        
        if torch.cuda.is_available():
            try:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_properties = torch.cuda.get_device_properties(0)

                total_vram_gb = round(gpu_properties.total_memory / (1024 ** 3), 2) 
                
                gpu_info = f"{gpu_name} - {total_vram_gb} GB VRAM"
                
            except Exception as e:
                gpu_info = f"GPU detected, but info error: {str(e)}"
        else:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_name = gpu.name
                    gpu_vram_gb = round(gpu.memoryTotal / 1024, 2) 
                    gpu_info = f"{gpu_name} - {gpu_vram_gb} GB VRAM"
            except ImportError:
                pass
            except Exception as e:
                print(f"GPUtil detection failed: {e}")

        self.ui.gpu_label.setText(gpu_info)

        available_memory_round = memory_info.total // (1024 ** 3)
        self.configuration.update_main_setting("available_memory", available_memory_round)
        
    def check_for_updates(self, current_version):
        try:
            repo_url = "https://api.github.com/repos/jofizcd/Soul-of-Waifu/releases/latest"
            response = requests.get(repo_url)
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release["tag_name"]

            if latest_version != current_version:
                logger.info(f"A new version has been released, update the program! {latest_version}")
                return latest_version, latest_release["html_url"]
            else:
                return None, None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Couldn't check for updates: {e}")
            return None, None

        except Exception as e:
            logger.error(f"Error checking for updates: {e}", exc_info=True)
            return None, None

    def show_update_dialog(self, latest_version, github_url):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(self.translations.get("update_available_title", "Update Available"))
        dialog.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
        dialog.setFixedSize(450, 420)

        dialog.setStyleSheet("""
            QDialog {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                stop:0 #2e2e2e, stop:1 #1e1e1e);
                border-radius: 16px;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #ffffff;
            }
            QLabel#infoLabel {
                font-size: 14px;
                color: #d0d0d0;
            }
            QLabel#version_label {
                font-size: 14px;
                color: #aaaaaa;
            }
            QLabel#logo_text {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;
            }
            QPushButton {
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                min-width: 110px;
            }
            QPushButton#github_button {
                background-color: #28a745;
                color: white;
                border: none;
            }
            QPushButton#github_button:hover {
                background-color: #218c3e;
            }
            QPushButton#close_button {
                background-color: #4a4a4a;
                color: white;
                border: none;
            }
            QPushButton#close_button:hover {
                background-color: #5a5a5a;
            }
            QPushButton:focus {
                outline: none;
                border: 2px solid #6a6a6a;
            }
        """)

        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        dialog.setFont(font)

        main_layout = QtWidgets.QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 0, 20, 20)
        main_layout.setSpacing(15)

        icon_label = QtWidgets.QLabel()
        icon_pixmap = QtGui.QPixmap("app/gui/icons/reload.png").scaled(
            120, 120, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("border-radius: 40px; background: transparent; padding: 10px;")

        title_label = QtWidgets.QLabel(
            self.translations.get("update_available_body", "A new version is available: ") + latest_version
        )
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        info_label = QtWidgets.QLabel(
            self.translations.get("update_available_info", "Would you like to update the program?")
        )
        info_label.setObjectName("infoLabel")
        info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)

        version_label = QtWidgets.QLabel(
            self.translations.get("update_current_version", "Current version: v2.2.0")
        )
        version_label.setObjectName("version_label")
        version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.setSpacing(20)

        close_button = QtWidgets.QPushButton(
            self.translations.get("update_available_close", "Close")
        )
        close_button.setObjectName("close_button")
        close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        close_button.clicked.connect(dialog.reject)

        github_button = QtWidgets.QPushButton(
            self.translations.get("update_available_link", "Go to GitHub")
        )
        github_button.setObjectName("github_button")
        github_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        github_button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(github_url)))

        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addWidget(github_button)
        button_layout.addStretch()

        main_layout.addStretch(1)
        main_layout.addWidget(icon_label, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacing(10)
        main_layout.addWidget(title_label)
        main_layout.addWidget(info_label)
        main_layout.addWidget(version_label)
        main_layout.addStretch(1)
        main_layout.addLayout(button_layout)
        main_layout.addSpacing(10)

        dialog.exec()

    def load_fonts_from_folder(self, folder_path):
        for font_file in os.listdir(folder_path):
            font_path = os.path.join(folder_path, font_file)
            if font_path.endswith(('.ttf', '.otf')):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id == -1:
                    logger.error(f"Error loading font: {font_file}")
                else:
                    QFontDatabase.applicationFontFamilies(font_id)
    
    def create_size_grips(self):
        mw = self.ui.main_widget

        self.top_left_grip = QtWidgets.QSizeGrip(mw)
        self.top_right_grip = QtWidgets.QSizeGrip(mw)
        self.bottom_left_grip = QtWidgets.QSizeGrip(mw)
        self.bottom_right_grip = QtWidgets.QSizeGrip(mw)

        self.top_edge_grip = QtWidgets.QSizeGrip(mw)
        self.bottom_edge_grip = QtWidgets.QSizeGrip(mw)
        self.left_edge_grip = QtWidgets.QSizeGrip(mw)
        self.right_edge_grip = QtWidgets.QSizeGrip(mw)

        grips = [
            self.top_left_grip, self.top_right_grip,
            self.bottom_left_grip, self.bottom_right_grip,
            self.top_edge_grip, self.bottom_edge_grip,
            self.left_edge_grip, self.right_edge_grip
        ]

        for grip in grips:
            grip.resize(8, 8)
            grip.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
            grip.show()
            grip.raise_()

        self.top_left_grip.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)
        self.top_right_grip.setCursor(QtCore.Qt.CursorShape.SizeBDiagCursor)
        self.bottom_left_grip.setCursor(QtCore.Qt.CursorShape.SizeBDiagCursor)
        self.bottom_right_grip.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)

        self.top_edge_grip.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
        self.bottom_edge_grip.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
        self.left_edge_grip.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self.right_edge_grip.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)

    def update_size_grip_positions(self):
        mw = self.ui.main_widget
        w, h = mw.width(), mw.height()
        size = 8

        self.top_left_grip.move(0, 0)
        self.bottom_left_grip.move(0, h - size)
        self.top_right_grip.move(w - size, 0)
        self.bottom_right_grip.move(w - size, h - size)

        self.top_edge_grip.move(w // 2 - size // 2, 0)
        self.bottom_edge_grip.move(w // 2 - size // 2, h - size)
        self.left_edge_grip.move(0, h // 2 - size // 2)
        self.right_edge_grip.move(w - size, h // 2 - size // 2)

    def resizeEvent(self, event):
        current_index = self.ui.stackedWidget.currentIndex()
        if current_index == 1:
            self.interface_signals.handle_resize(event)
        elif current_index == 4:
            self.interface_signals.handle_gate_resize(event)
        
        super().resizeEvent(event)

        self.update_size_grip_positions()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if event.pos().y() <= self.ui.frame_version.height():
                self.draggable = True
                self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.draggable:
            self.move(self.pos() + event.pos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.draggable = False

    def toggle_maximize(self):
        if self.isMaximized():
            icon_maximize = QtGui.QIcon()
            icon_maximize.addPixmap(QtGui.QPixmap("app/gui/icons/maximize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            self.ui.horizontalLayout_main_widget.setContentsMargins(0, 0, 0, 0)
            self.ui.maximize_btn.setIcon(icon_maximize)
            self.showNormal()
        else:
            self.ui.horizontalLayout_main_widget.setContentsMargins(0, 0, 0, 0)
            icon_maximize = QtGui.QIcon()
            icon_maximize.addPixmap(QtGui.QPixmap("app/gui/icons/maximize_minimize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            self.ui.maximize_btn.setIcon(icon_maximize)
            self.showMaximized()

if __name__ == "__main__":
    if sys.platform == 'win32':
        app_id = "com.jofizcd.soul_of_waifu.v2"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    main_window = MainWindow()
    main_window.setWindowIcon(QtGui.QIcon("app/gui/icons/logotype.ico"))
    fonts_folder = "app/font"
    main_window.load_fonts_from_folder(fonts_folder)

    main_window.show()    

    current_version = "v2.2.0"
    latest_version, github_url = main_window.check_for_updates(current_version)
    if latest_version:
        main_window.show_update_dialog(latest_version, github_url)     

    loop.run_forever()