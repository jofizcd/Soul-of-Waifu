import asyncio
import ctypes
import logging
import os
import sys
from datetime import datetime

import GPUtil
import psutil
import requests
import torch
import yaml
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from qasync import QEventLoop, asyncSlot

from app.configuration import configuration
from app.gui import interface_signals
from app.gui.custom_widgets import SowConfirmDialog
from app.gui.sowInterface import Ui_MainWindow
from app.utils.ai_clients.local_server_manager import LocalServerManager

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

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("Unhandled exception captured:", exc_info=(exc_type, exc_value, exc_traceback))
    
    if QApplication.instance():
        try:
            QMessageBox.critical(
                None, 
                "Critical Error", 
                f"An unexpected error occurred:\n{exc_value}\n\nPlease check the logs for details."
            )
        except Exception:
            pass

sys.excepthook = global_exception_handler

from app.utils.discord_manager import DiscordBotManager

RESIZE_GRIP_SIZE = 8

class _EdgeResizeGrip(QtWidgets.QWidget):
    def __init__(self, window: QtWidgets.QMainWindow, edges: QtCore.Qt.Edge,
                 cursor: QtCore.Qt.CursorShape, parent=None):
        super().__init__(parent)
        self._window = window
        self._edges = edges
        self.setCursor(cursor)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if (event.button() == QtCore.Qt.MouseButton.LeftButton
                and not self._window.isMaximized()
                and not self._window.isFullScreen()):
            handle = self._window.windowHandle()
            if handle is not None and handle.startSystemResize(self._edges):
                event.accept()
                return
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """
    Main application window for 'Soul of Waifu'.
    """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setAcceptDrops(True)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.discord_manager = DiscordBotManager(self)

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
        self.local_server_manager = LocalServerManager(self.ui)

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
        self.interface_signals.initialize_lineEdit_customArgs()
        self.interface_signals.initialize_lineEdit_mcp_url()
        self.interface_signals.initialize_gpu_layers_horizontalSlider()
        self.interface_signals.initialize_context_size_horizontalSlider()
        self.interface_signals.initialize_temperature_horizontalSlider()
        self.interface_signals.initialize_top_p_horizontalSlider()
        self.interface_signals.initialize_max_tokens_horizontalSlider()
        self.interface_signals.initialize_interval_summary()
        self.interface_signals.initialize_freq_penalty_horizontalSlider()
        self.interface_signals.initialize_pres_penalty_horizontalSlider()
        self.interface_signals.initialize_min_p_horizontalSlider()
        self.interface_signals.initialize_dyn_temp_min_horizontalSlider()
        self.interface_signals.initialize_dyn_temp_max_horizontalSlider()
        self.interface_signals.initialize_xtc_prob_horizontalSlider()
        self.interface_signals.initialize_xtc_threshold_horizontalSlider()
        self.interface_signals.initialize_dry_multiplier_horizontalSlider()
        self.interface_signals.initialize_dry_base_horizontalSlider()
        self.interface_signals.initialize_dry_allowed_length_horizontalSlider()
        self.interface_signals.initialize_batch_size_horizontalSlider()
        self.interface_signals.initialize_cpu_threads_horizontalSlider()
        self.interface_signals.initialize_cpu_moe_layers_horizontalSlider()

        self.drop_overlay = QtWidgets.QLabel(self)
        self.drop_overlay.setText(self.translations.get("drag_and_drop_overlay", "Drag and drop a .png or .json card directly here\nto import it into Soul of Waifu"))
        self.drop_overlay.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.drop_overlay.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                color: white;
                font-size: 24px;
                font-family: 'Inter Tight Medium';
            }
        """)
        self.drop_overlay.hide()

    async def startup_sequence(self):
        await self.interface_signals.set_main_tab()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(('.png', '.json')):
                    self.drop_overlay.resize(self.size())
                    self.drop_overlay.show()
                    self.drop_overlay.raise_()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.drop_overlay.hide()
        if not event.mimeData().hasUrls():
            return
            
        for url in event.mimeData().urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(('.png', '.json')):
                file_path = url.toLocalFile()
                
                if hasattr(self, 'interface_signals'):
                    self.interface_signals.populate_editor_character_list()
                    self.interface_signals.prepare_new_character_editor()
                    self.interface_signals.import_character_card(file_path)
                    self.ui.stackedWidget.setCurrentWidget(self.ui.create_character_page)
                event.acceptProposedAction()
                return

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
        self.ui.pushButton_characters_gateway.setText(self.translations.get("characters_gateway_button", " Characters Gateway"))
        self.ui.pushButton_models_hub.setText(self.translations.get("models_hub_button", " Models Hub"))
        self.ui.pushButton_rp_editors.setText(self.translations.get("rp_editors_button", " RP Editors"))
        self.ui.pushButton_soul_stage.setText(self.translations.get("soul_stage_button", " Soul Stage"))
        self.ui.pushButton_options.setText(self.translations.get("options_button", " Options"))
        self.ui.version_label.setText(self.translations.get("version_label", "v2.4.5"))
        
        # Main Tab Without Characters
        self.ui.main_no_characters_advice_label.setText(self.translations.get("no_characters_advice", "You haven\'t added any characters. Click on the button and create it"))
        self.ui.pushButton_create_character_2.setText(self.translations.get("create_character_button_2", " Create Character"))
        self.ui.main_no_characters_description_label.setText(self.translations.get("no_characters_description", "Before you begin a chat with a character, take a moment to customize the program to suit your preferences. \n"
"Once you\'re ready, create your unique character and start the conversation!"))
        
        # Main Tab With Characters
        self.ui.welcome_label_2.setText(self.translations.get("welcome_label", "Welcome to Soul of Waifu, User"))
        self.ui.lineEdit_search_character_menu.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        
        # Character Creation
        self.ui.pushButton_import_character_card.setText(self.translations.get("import_character_card_button", " Import Character Card"))
        self.ui.pushButton_export_character_card.setText(self.translations.get("export_character_card_button", " Export Character Card"))
        self.ui.pushButton_clean_character_card.setText(self.translations.get("clean_character_card_button", " Clear All Fields"))
        self.ui.pushButton_preview_prompt.setText(self.translations.get("preview_prompt_button", "Preview Raw"))
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
        self.ui.item_general_info.setText(self.translations.get("character_creator_item_general_info", "General Information"))
        self.ui.item_personality.setText(self.translations.get("character_creator_item_personality", "Personality & Scenario"))
        self.ui.item_dialogues.setText(self.translations.get("character_creator_item_dialogues", "Dialogues"))
        self.ui.item_advanced.setText(self.translations.get("character_creator_item_advanced", "Advanced & Lore"))
        self.ui.item_variables.setText(self.translations.get("character_creator_title_custom_variable", "Variables & State"))
        self.ui.item_export.setText(self.translations.get("character_creator_item_export", "Export / Utils"))
        
        # Models Hub
        self.ui.lineEdit_search_model.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.pushButton_models_hub_my_models.setText(self.translations.get("models_hub_my_models", " My models"))
        self.ui.pushButton_models_hub_popular.setText(self.translations.get("models_hub_popular", " Popular"))
        self.ui.pushButton_models_hub_recommendations.setText(self.translations.get("models_hub_recommendations", "Recommendations"))

        # Options
        self.ui.label_base_url.setText(self.translations.get("label_base_url", "Base URL"))
        self.ui.label_mistral_model.setText(self.translations.get("label_mistral_model", "Mistral Model"))
        self.ui.label_bg_color.setText(self.translations.get("model_background_1", "Color"))
        self.ui.label_bg_image.setText(self.translations.get("model_background_2", "Image"))
        self.ui.lineEdit_search_character.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.conversation_method_token_title_label.setText(self.translations.get("api_label", "API"))
        self.ui.lineEdit_api_token_options.setPlaceholderText(self.translations.get("placeholder_api_value", "Write your API value here"))
        self.ui.lineEdit_mistral_model.setPlaceholderText(self.translations.get("placeholder_mistral_model_endpoint", "Enter the API endpoint of the mistral model here"))
        self.ui.checkBox_enable_sow_system.setText(self.translations.get("enable_sow_system_checkbox", "Enable Soul of Waifu System"))
        self.ui.label_model_fps.setText(self.translations.get("choose_model_fps", "Model FPS"))
        self.ui.comboBox_model_fps.setItemText(0, self.translations.get("model_fps_30", "30 FPS"))
        self.ui.comboBox_model_fps.setItemText(1, self.translations.get("model_fps_60", "60 FPS"))
        self.ui.comboBox_model_fps.setItemText(2, self.translations.get("model_fps_120", "120 FPS"))
        self.ui.label_model_background.setText(self.translations.get("choose_model_background", "Model background"))
        self.ui.comboBox_model_background.setItemText(0, self.translations.get("model_background_1", "Color"))
        self.ui.comboBox_model_background.setItemText(1, self.translations.get("model_background_2", "Custom Image"))
        self.ui.checkBox_enable_ambient.setText(self.translations.get("enable_ambient_checkbox", "Ambient Sound"))
        self.ui.checkBox_enable_soul_memory.setText(self.translations.get("enable_soul_memory", "Soul Memory"))
        self.ui.checkBox_enable_summary.setText(self.translations.get("enable_summary_checkbox", "Auto-Summarization"))
        self.ui.label_summary_interval.setText(self.translations.get("settings_summary_interval", "Interval (messages):"))
        self.ui.conversation_method_options_label.setText(self.translations.get("conversation_method_label", "Conversation method"))
        self.ui.comboBox_conversation_method.setItemText(0, self.translations.get("conversation_method_item_mistralai", "Mistral AI"))
        self.ui.comboBox_conversation_method.setItemText(1, self.translations.get("conversation_method_item_openai", "Open AI"))
        self.ui.comboBox_conversation_method.setItemText(2, self.translations.get("conversation_method_item_openrouter", "OpenRouter"))
        self.ui.openrouter_models_options_label.setText(self.translations.get("openrouter_models_label", "Model"))
        self.ui.lineEdit_search_openrouter_models.setPlaceholderText(self.translations.get("search_placeholder", "Search"))
        self.ui.lineEdit_base_url_options.setPlaceholderText(self.translations.get("placeholder_base_url", "Write your custom endpoint url here (Optional)"))
        self.ui.comboBox_program_language.setItemText(0, self.translations.get("program_language_item_en", "English"))
        self.ui.comboBox_program_language.setItemText(1, self.translations.get("program_language_item_ru", "Russian"))
        self.ui.input_device_label.setText(self.translations.get("input_device_label", "Input device"))
        self.ui.output_device_label.setText(self.translations.get("output_device_label", "Output device"))
        self.ui.program_language_label.setText(self.translations.get("program_language_label", "App Language"))
        self.ui.choose_translator_label.setText(self.translations.get("choose_translator_label", "Translator"))
        self.ui.comboBox_translator.setItemText(0, self.translations.get("translator_item_none", "None"))
        self.ui.comboBox_translator.setItemText(1, self.translations.get("translator_item_google", "Google"))
        self.ui.comboBox_translator.setItemText(2, self.translations.get("translator_item_yandex", "Yandex"))
        self.ui.target_language_translator_label.setText(self.translations.get("target_language_label", "Target Language"))
        self.ui.comboBox_target_language_translator.setItemText(0, self.translations.get("target_language_item_ru", "Russian"))

        if hasattr(self.ui, 'options_menu'):
            item0 = self.ui.options_menu.item(0)
            if item0: item0.setText(self.translations.get("system_tab", "System & UI"))
            
            item1 = self.ui.options_menu.item(1)
            if item1: item1.setText(self.translations.get("configuration_tab", "API & Providers"))
            
            item2 = self.ui.options_menu.item(2)
            if item2: item2.setText(self.translations.get("local_llm_tab", "Local LLM"))
            
            item3 = self.ui.options_menu.item(3)
            if item3: item3.setText(self.translations.get("tools_tab", "Tool Calling & MCP"))

            item4 = self.ui.options_menu.item(4)
            if item4: item4.setText(self.translations.get("sow_system_tab", "SoW Modules"))
        
        # Chat
        self.ui.character_name_chat.setText(self.translations.get("character_name_chat", "Character name"))
        self.ui.textEdit_write_user_message.setPlaceholderText(self.translations.get("write_user_message_placeholder", "Write your message to character..."))
        
        # LLM Options
        self.ui.label_live2d_mode.setText(self.translations.get("live2d_mode_label", "Mode:"))
        self.ui.comboBox_live2d_mode.setItemText(0, self.translations.get("live2d_mode_with_gui", "With GUI"))
        self.ui.comboBox_live2d_mode.setItemText(1, self.translations.get("live2d_mode_without_gui", "Without GUI"))
        self.ui.checkBox_enable_nsfw.setText(self.translations.get("nsfw_checkbox", "NSFW"))
        self.ui.lineEdit_server.setText("http://localhost:48596/v1")

        # Tooltips
        self.ui.checkBox_enable_mlock.setToolTip(self.translations.get("mlock_tooltip", ""))
        self.ui.checkBox_enable_no_mmap.setToolTip(self.translations.get("no_mmap_tooltip", ""))
        self.ui.checkBox_reasoning_mode.setToolTip(self.translations.get("reasoning_mode_tooltip", ""))
        self.ui.checkBox_enable_flash_attention.setToolTip(self.translations.get("flashattention_tooltip", ""))
        self.ui.checkBox_enable_ambient.setToolTip(self.translations.get("ambient_sound_tooltip", "Enable Ambient Sound Module"))
        self.ui.checkBox_enable_soul_memory.setToolTip(self.translations.get("soul_memory_tooltip", "Enable Soul Memory Module"))
        self.ui.checkBox_enable_sow_system.setToolTip(self.translations.get("sow_system_tooltip", "Enable Soul of Waifu System Module"))
        self.ui.chat_template_label.setToolTip(self.translations.get("chat_template_tooltip", ""))
        self.ui.lineEdit_stop_strings.setToolTip(self.translations.get("stop_strings_tooltip", ""))

    def on_comboBox_program_language_changed(self, index):
        self.configuration.update_main_setting("program_language", index)

        title = self.translations.get("language_changed_title", "Restart Required")
        first_text = self.translations.get("language_changed_body", "The program needs to be restarted for the changes to take effect.")
        second_text = self.translations.get("language_changed_question", "Would you like to restart the program now?")

        message_text = f"{first_text}\n\n{second_text}"

        parent_win = self.main_window if hasattr(self, "main_window") else self

        dialog = SowConfirmDialog(
            parent=parent_win,
            title=title,
            text=message_text,
            confirm_text="Restart",
            danger=False
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            QtCore.QProcess.startDetached(sys.executable, sys.argv)
            QtCore.QCoreApplication.quit()

    def setup_interface_signals(self):
        """
        Connects signals for all UI elements to their respective handlers.
        """
        # PushButtons
        self.ui.pushButton_main.clicked.connect(self.interface_signals.on_pushButton_main_clicked)
        self.ui.pushButton_create_character_2.clicked.connect(self.interface_signals._prepare_blank_character_and_open_editor)
        self.ui.pushButton_create_character_3.clicked.connect(self.interface_signals.add_character_sync)
        self.ui.pushButton_characters_gateway.clicked.connect(self._on_characters_gateway_clicked)
        self.ui.pushButton_models_hub.clicked.connect(self.interface_signals.on_pushButton_models_hub_clicked)
        self.ui.pushButton_options.clicked.connect(self.interface_signals.on_pushButton_options_clicked)
        self.ui.pushButton_rp_editors.clicked.connect(self.on_rp_editors_clicked)
        self.ui.pushButton_soul_stage.clicked.connect(self.interface_signals._open_soul_stage_page)
        self.ui.about_btn.clicked.connect(self.interface_signals.set_about_program_button)
        self.ui.pushButton_youtube.clicked.connect(self.interface_signals.on_youtube)
        self.ui.pushButton_discord.clicked.connect(self.interface_signals.on_discord)
        self.ui.pushButton_github.clicked.connect(self.interface_signals.on_github)
        self.ui.btn_new_folder_menu.clicked.connect(self.interface_signals._open_create_folder_dialog)
        self.ui.btn_import_character_menu.clicked.connect(self.interface_signals.import_character_card_from_menu)
        self.ui.pushButton_stop_generation.clicked.connect(self.interface_signals.stop_generation)
        self.ui.pushButton_import_character_card.clicked.connect(self.interface_signals.import_character_card)
        self.ui.pushButton_export_character_card.clicked.connect(self.interface_signals.export_character_card)
        self.ui.pushButton_clean_character_card.clicked.connect(self.interface_signals.clean_character_card)
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
        self.ui.pushButton_author_notes.clicked.connect(self.interface_signals.open_author_notes_editor)
        self.ui.pushButton_change_chat_background.clicked.connect(self.interface_signals.open_chat_background_changer)
        self.ui.btn_open_character_editor.clicked.connect(self.interface_signals._prepare_blank_character_and_open_editor)
        self.ui.editor_character_list.itemClicked.connect(self.interface_signals.load_character_into_editor)
        self.ui.btn_create_new_character_editor.clicked.connect(self.interface_signals.prepare_new_character_editor)
        self.ui.btn_open_soul_stage.clicked.connect(self.interface_signals._open_soul_stage_page)
        self.ui.btn_open_personas.clicked.connect(self.interface_signals.open_personas_editor)
        self.ui.btn_open_lorebook.clicked.connect(self.interface_signals.open_lorebook_editor)
        self.ui.btn_open_discord_bot.clicked.connect(self.interface_signals.open_discord_gateway)
        self.ui.btn_open_prompts.clicked.connect(self.interface_signals.open_system_prompt_editor)
        self.ui.btn_open_image_gen.clicked.connect(self.interface_signals.open_image_gen_settings)
        self.ui.pushButton_soul_memory.clicked.connect(self.interface_signals.open_soul_memory_viewer)
        self.ui.pushButton_update_engine.clicked.connect(self.interface_signals.open_updater_dialog)
        self.ui.provider_group.buttonClicked.connect(self.interface_signals._on_provider_card_clicked)
        self.ui.btn_create_character_menu.clicked.connect(self.interface_signals._prepare_blank_character_and_open_editor)
        self.ui.pushButton_toggle_web_server.clicked.connect(self.interface_signals.on_toggle_web_server)
        self.ui.pushButton_copy_mobile_link.clicked.connect(self.interface_signals.on_copy_mobile_link)
        self.ui.pushButton_open_web_browser.clicked.connect(self.interface_signals.on_open_web_browser)
        self.ui.pushButton_ai_assistant.clicked.connect(self.interface_signals.open_ai_character_assistant)

        # ComboBoxes
        self.ui.comboBox_conversation_method.currentTextChanged.connect(self.interface_signals.on_comboBox_conversation_method_changed)
        self.ui.comboBox_program_language.currentIndexChanged.connect(self.on_comboBox_program_language_changed)
        self.ui.comboBox_input_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_input_devices_changed)
        self.ui.comboBox_output_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_output_devices_changed)
        self.ui.comboBox_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_translator_changed)
        self.ui.comboBox_target_language_translator.currentIndexChanged.connect(self.interface_signals.on_comboBox_target_language_translator_changed)
        self.ui.comboBox_conversation_method.currentIndexChanged.connect(self.interface_signals.update_api_token)
        self.ui.comboBox_live2d_mode.currentIndexChanged.connect(self.interface_signals.on_comboBox_live2d_mode_changed)
        self.ui.comboBox_model_fps.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_fps_changed)
        self.ui.comboBox_model_background.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_background_changed)
        self.ui.comboBox_model_bg_color.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_bg_color_changed)
        self.ui.comboBox_model_bg_image.currentIndexChanged.connect(self.interface_signals.on_comboBox_model_bg_image_changed)
        self.ui.comboBox_ambient_mode.currentIndexChanged.connect(self.interface_signals.on_comboBox_ambient_mode_changed)
        self.ui.comboBox_llm_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_llm_devices_changed)
        self.ui.comboBox_llm_gpu_devices.currentIndexChanged.connect(self.interface_signals.on_comboBox_llm_gpu_devices_changed)
        self.ui.comboBox_chat_template.currentTextChanged.connect(self.interface_signals.on_comboBox_chat_template_changed)
        self.ui.comboBox_kv_cache.currentIndexChanged.connect(self.interface_signals.on_comboBox_kv_cache_changed)

        # LineEdits
        self.ui.lineEdit_api_token_options.textChanged.connect(self.interface_signals.save_api_token_in_real_time)
        self.ui.lineEdit_base_url_options.textChanged.connect(self.interface_signals.save_custom_url_in_real_time)
        self.ui.lineEdit_openai_model.textChanged.connect(self.interface_signals.save_openai_model_in_real_time)
        self.ui.lineEdit_mistral_model.textChanged.connect(self.interface_signals.save_mistral_model_endpoint_in_real_time)
        self.ui.lineEdit_anthropic_model.textChanged.connect(self.interface_signals.save_anthropic_model_in_real_time)
        self.ui.lineEdit_gemini_model.textChanged.connect(self.interface_signals.save_gemini_model_in_real_time)
        self.ui.lineEdit_deepseek_model.textChanged.connect(self.interface_signals.save_deepseek_model_in_real_time)
        self.ui.lineEdit_grok_model.textChanged.connect(self.interface_signals.save_grok_model_in_real_time)
        self.ui.lineEdit_qwen_model.textChanged.connect(self.interface_signals.save_qwen_model_in_real_time)
        self.ui.lineEdit_zai_model.textChanged.connect(self.interface_signals.save_zai_model_in_real_time)
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
        self.ui.lineEdit_maxTokens.editingFinished.connect(self.interface_signals.update_max_tokens_from_line_edit)
        self.ui.lineEdit_stop_strings.textChanged.connect(self.interface_signals.save_stop_strings_in_real_time)
        self.ui.lineEdit_freqPenalty.editingFinished.connect(self.interface_signals.update_freq_penalty_from_line_edit)
        self.ui.lineEdit_presPenalty.editingFinished.connect(self.interface_signals.update_pres_penalty_from_line_edit)
        self.ui.lineEdit_minP.editingFinished.connect(self.interface_signals.update_min_p_from_line_edit)
        self.ui.lineEdit_dynTempMin.editingFinished.connect(self.interface_signals.update_dyn_temp_min_from_line_edit)
        self.ui.lineEdit_dynTempMax.editingFinished.connect(self.interface_signals.update_dyn_temp_max_from_line_edit)
        self.ui.lineEdit_xtcProb.editingFinished.connect(self.interface_signals.update_xtc_prob_from_line_edit)
        self.ui.lineEdit_xtcThreshold.editingFinished.connect(self.interface_signals.update_xtc_threshold_from_line_edit)
        self.ui.lineEdit_dryMultiplier.editingFinished.connect(self.interface_signals.update_dry_multiplier_from_line_edit)
        self.ui.lineEdit_dryBase.editingFinished.connect(self.interface_signals.update_dry_base_from_line_edit)
        self.ui.lineEdit_dryAllowedLength.editingFinished.connect(self.interface_signals.update_dry_allowed_length_from_line_edit)
        self.ui.lineEdit_batchSize.editingFinished.connect(self.interface_signals.update_batch_size_from_line_edit)
        self.ui.lineEdit_cpuThreads.editingFinished.connect(self.interface_signals.update_cpu_threads_from_line_edit)
        self.ui.lineEdit_cpuMoeLayers.editingFinished.connect(self.interface_signals.update_cpu_moe_layers_from_line_edit)
        self.ui.lineEdit_customArgs.textChanged.connect(self.interface_signals.save_lineEdit_customArgs_in_real_time)
        self.ui.lineEdit_mcp_url.textChanged.connect(self.interface_signals.save_lineEdit_mcp_url_in_real_time)
        
        # Sliders
        self.ui.gpu_layers_horizontalSlider.valueChanged.connect(self.interface_signals.save_gpu_layers_in_real_time)
        self.ui.context_size_horizontalSlider.valueChanged.connect(self.interface_signals.save_context_size_in_real_time)
        self.ui.temperature_horizontalSlider.valueChanged.connect(self.interface_signals.save_temperature_in_real_time)
        self.ui.top_p_horizontalSlider.valueChanged.connect(self.interface_signals.save_top_p_in_real_time)
        self.ui.max_tokens_horizontalSlider.valueChanged.connect(self.interface_signals.save_max_tokens_in_real_time)
        self.ui.spinBox_summary_interval.valueChanged.connect(self.interface_signals.save_interval_summary_in_real_time)
        self.ui.freq_penalty_horizontalSlider.valueChanged.connect(self.interface_signals.save_freq_penalty_in_real_time)
        self.ui.pres_penalty_horizontalSlider.valueChanged.connect(self.interface_signals.save_pres_penalty_in_real_time)
        self.ui.min_p_horizontalSlider.valueChanged.connect(self.interface_signals.save_min_p_in_real_time)
        self.ui.dyn_temp_min_horizontalSlider.valueChanged.connect(self.interface_signals.save_dyn_temp_min_in_real_time)
        self.ui.dyn_temp_max_horizontalSlider.valueChanged.connect(self.interface_signals.save_dyn_temp_max_in_real_time)
        self.ui.xtc_prob_horizontalSlider.valueChanged.connect(self.interface_signals.save_xtc_prob_in_real_time)
        self.ui.xtc_threshold_horizontalSlider.valueChanged.connect(self.interface_signals.save_xtc_threshold_in_real_time)
        self.ui.dry_multiplier_horizontalSlider.valueChanged.connect(self.interface_signals.save_dry_multiplier_in_real_time)
        self.ui.dry_base_horizontalSlider.valueChanged.connect(self.interface_signals.save_dry_base_in_real_time)
        self.ui.dry_allowed_length_horizontalSlider.valueChanged.connect(self.interface_signals.save_dry_allowed_length_in_real_time)
        self.ui.batch_size_horizontalSlider.valueChanged.connect(self.interface_signals.save_batch_size_in_real_time)
        self.ui.cpu_threads_horizontalSlider.valueChanged.connect(self.interface_signals.save_cpu_threads_in_real_time)
        self.ui.cpu_moe_layers_horizontalSlider.valueChanged.connect(self.interface_signals.save_cpu_moe_layers_in_real_time)
        
        # CheckBox
        self.ui.checkBox_enable_mlock.stateChanged.connect(self.interface_signals.on_checkBox_enable_mlock_stateChanged)
        self.ui.checkBox_enable_flash_attention.stateChanged.connect(self.interface_signals.on_checkBox_enable_flash_attention_stateChanged)
        self.ui.checkBox_enable_no_mmap.stateChanged.connect(self.interface_signals.on_checkBox_enable_no_mmap_stateChanged)
        self.ui.checkBox_enable_advanced_sampling.stateChanged.connect(self.interface_signals.on_checkBox_enable_advanced_sampling_stateChanged)
        self.ui.stackedWidget.currentChanged.connect(self.interface_signals.on_stacked_widget_changed)
        self.ui.checkBox_enable_nsfw.stateChanged.connect(self.interface_signals.on_checkBox_enable_nsfw_stateChanged)
        self.ui.checkBox_enable_ambient.stateChanged.connect(self.interface_signals.on_checkBox_enable_ambient_stateChanged)
        self.ui.checkBox_enable_sow_system.stateChanged.connect(self.interface_signals.on_checkBox_enable_sow_system_stateChanged)
        self.ui.checkBox_enable_soul_memory.stateChanged.connect(self.interface_signals.on_checkBox_enable_soul_memory_stateChanged)
        self.ui.checkBox_enable_summary.stateChanged.connect(self.interface_signals.on_checkBox_enable_summary_stateChanged)
        self.ui.checkBox_reasoning_mode.stateChanged.connect(self.interface_signals.on_checkBox_reasoning_mode_stateChanged)
        self.ui.checkBox_enable_tool_calling.stateChanged.connect(self.interface_signals.on_checkBox_enable_tool_calling_stateChanged)
        self.ui.checkBox_enable_mcp.stateChanged.connect(self.interface_signals.on_checkBox_enable_mcp_stateChanged)

        self.ui.anchor_menu_building.currentRowChanged.connect(self.interface_signals._scroll_character_creation)
        self.ui.scrollArea_character_building.verticalScrollBar().valueChanged.connect(self.interface_signals._update_anchor_menu_from_scroll)
        if hasattr(self.ui, 'pushButton_preview_prompt'):
            self.ui.pushButton_preview_prompt.clicked.connect(self.interface_signals._show_raw_prompt_preview)

    @asyncSlot()
    async def on_rp_editors_clicked(self):
        self.ui.pushButton_rp_editors.setChecked(True)
        index = self.ui.stackedWidget.indexOf(self.ui.rp_editors_page)
        self.ui.stackedWidget.setCurrentIndex(index)

    @asyncSlot()
    async def _on_characters_gateway_clicked(self):
        await self.interface_signals.open_characters_gateway()

    @asyncSlot()
    async def _on_search_characters_gateway_clicked(self):
        await self.interface_signals.search_character()

    def check_pc_specs(self):
        """
        Detects and displays basic PC specifications such as RAM and GPU info.
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
            response = requests.get(repo_url, timeout=10)
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
        dialog.setFixedSize(400, 450)

        dialog.setStyleSheet("""
            QDialog {
                background-color: rgb(27,27,27);
                border-radius: 20px;
            }
            QLabel#titleLabel {
                font-size: 22px;
                font-weight: 800;
                color: #ffffff;
                margin-top: 10px;
            }
            QLabel#infoLabel {
                font-size: 14px;
                color: #9CA3AF;
                line-height: 1.5;
            }
            QLabel#version_label {
                font-size: 12px;
                font-weight: bold;
                color: #6B7280;
                background-color: #1F1F23;
                padding: 4px 12px;
                border-radius: 10px;
            }
            QPushButton {
                padding: 12px 24px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 12px;
            }
            QPushButton#github_button {
                background-color: #777778;
                color: white;
                border: none;
            }
            QPushButton#github_button:hover {
                background-color: #828282;
            }
            QPushButton#github_button:pressed {
                background-color: #909091;
            }
            QPushButton#close_button {
                background-color: transparent;
                color: #9CA3AF;
                border: 1px solid #374151;
            }
            QPushButton#close_button:hover {
                background-color: #1F1F23;
                color: white;
            }
        """)

        font = QtGui.QFont("Inter Tight Medium", 10)
        dialog.setFont(font)

        main_layout = QtWidgets.QVBoxLayout(dialog)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(10)

        icon_label = QtWidgets.QLabel()
        icon_pixmap = QtGui.QPixmap("app/gui/icons/reload.png").scaled(
            100, 100, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        title_label = QtWidgets.QLabel(
            self.translations.get("update_available_body", "New Update!")
        )
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        version_box = QtWidgets.QHBoxLayout()
        v_text = f"{current_version}  →  {latest_version}"
        version_label = QtWidgets.QLabel(v_text)
        version_label.setObjectName("version_label")
        version_box.addStretch()
        version_box.addWidget(version_label)
        version_box.addStretch()

        info_label = QtWidgets.QLabel(
            self.translations.get("update_available_info", 
            "A newer version of Soul of Waifu is ready. Update now to get the latest features and fixes.")
        )
        info_label.setObjectName("infoLabel")
        info_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)

        button_layout = QtWidgets.QVBoxLayout()
        button_layout.setSpacing(10)
        button_layout.setContentsMargins(0, 20, 0, 0)

        github_button = QtWidgets.QPushButton(
            self.translations.get("update_available_link", "Update Now")
        )
        github_button.setObjectName("github_button")
        github_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        github_button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(github_url)))

        close_button = QtWidgets.QPushButton(
            self.translations.get("update_available_close", "Later")
        )
        close_button.setObjectName("close_button")
        close_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        close_button.clicked.connect(dialog.reject)

        button_layout.addWidget(github_button)
        button_layout.addWidget(close_button)

        main_layout.addWidget(icon_label)
        main_layout.addWidget(title_label)
        main_layout.addLayout(version_box)
        main_layout.addSpacing(5)
        main_layout.addWidget(info_label)
        main_layout.addStretch()
        main_layout.addLayout(button_layout)

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
        Edge = QtCore.Qt.Edge
        Cursor = QtCore.Qt.CursorShape

        def make(edges, cursor):
            grip = _EdgeResizeGrip(self, edges, cursor, parent=mw)
            grip.show()
            grip.raise_()
            return grip

        self.top_left_grip = make(Edge.TopEdge | Edge.LeftEdge, Cursor.SizeFDiagCursor)
        self.top_right_grip = make(Edge.TopEdge | Edge.RightEdge, Cursor.SizeBDiagCursor)
        self.bottom_left_grip = make(Edge.BottomEdge | Edge.LeftEdge, Cursor.SizeBDiagCursor)
        self.bottom_right_grip = make(Edge.BottomEdge | Edge.RightEdge, Cursor.SizeFDiagCursor)

        self.top_edge_grip = make(Edge.TopEdge, Cursor.SizeVerCursor)
        self.bottom_edge_grip = make(Edge.BottomEdge, Cursor.SizeVerCursor)
        self.left_edge_grip = make(Edge.LeftEdge, Cursor.SizeHorCursor)
        self.right_edge_grip = make(Edge.RightEdge, Cursor.SizeHorCursor)

        self._all_grips = [
            self.top_left_grip, self.top_right_grip,
            self.bottom_left_grip, self.bottom_right_grip,
            self.top_edge_grip, self.bottom_edge_grip,
            self.left_edge_grip, self.right_edge_grip,
        ]

    def update_size_grip_positions(self):
        mw = self.ui.main_widget
        w, h = mw.width(), mw.height()
        g = RESIZE_GRIP_SIZE

        self.top_left_grip.setGeometry(0, 0, g, g)
        self.top_right_grip.setGeometry(w - g, 0, g, g)
        self.bottom_left_grip.setGeometry(0, h - g, g, g)
        self.bottom_right_grip.setGeometry(w - g, h - g, g, g)

        self.top_edge_grip.setGeometry(g, 0, max(0, w - 2 * g), g)
        self.bottom_edge_grip.setGeometry(g, h - g, max(0, w - 2 * g), g)
        self.left_edge_grip.setGeometry(0, g, g, max(0, h - 2 * g))
        self.right_edge_grip.setGeometry(w - g, g, g, max(0, h - 2 * g))

        self._update_grips_visibility()

    def _update_grips_visibility(self):
        visible = not (self.isMaximized() or self.isFullScreen())
        for grip in getattr(self, "_all_grips", []):
            grip.setVisible(visible)

    def resizeEvent(self, event):
        current_widget = self.ui.stackedWidget.currentWidget()

        if current_widget == self.ui.main_characters_page:
            self.interface_signals.handle_resize(event)
        elif current_widget == self.ui.rp_editors_page:
            self.interface_signals.handle_rp_editors_resize(event)
        elif current_widget == self.ui.charactersgateway_page:
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

    current_version = "v2.4.5"

    def deferred_update_check():
        latest_version, github_url = main_window.check_for_updates(current_version)
        if latest_version:
            main_window.show_update_dialog(latest_version, github_url)

    QtCore.QTimer.singleShot(0, deferred_update_check)
    
    asyncio.ensure_future(main_window.startup_sequence())

    loop.run_forever()
