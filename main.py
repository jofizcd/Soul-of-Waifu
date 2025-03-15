import sys
import ctypes
import asyncio
import requests
from qasync import QEventLoop
from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QTranslator
from configuration import configuration
from resources.icons import resources
from resources.data import interface_signals
from resources.data.sowInterface import Ui_MainWindow

class MainWindow(QMainWindow):
    """
    The main window class for managing the Soul of Waifu GUI and its modules.
    """
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # Initialize interface signals and configurations
        self.interface_signals = interface_signals.InterfaceSignals(self.ui, self)
        self.interface_signals.load_llms_to_comboBox()
        self.interface_signals.load_last_selected_model()
        self.setup_interface_signals()
        self.interface_signals.load_audio_devices()
        self.interface_signals.load_combobox()
        
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

    def setup_interface_signals(self):
        """
        Connects signals for all UI elements to their respective handlers.
        """
        # Menu Actions
        self.ui.action_about_program.triggered.connect(self.interface_signals.set_about_program_button)
        self.ui.action_create_new_character.triggered.connect(self.interface_signals.show_selection_dialog)
        self.ui.action_get_token_from_character_ai.triggered.connect(self.interface_signals.set_get_token_from_character_ai_button)
        self.ui.action_options.triggered.connect(self.interface_signals.on_pushButton_options_clicked)
        self.ui.action_discord.triggered.connect(self.interface_signals.on_discord)
        self.ui.action_github.triggered.connect(self.interface_signals.on_github)
        self.ui.action_faq.triggered.connect(self.interface_signals.set_faq_button)
        
        # Push Buttons
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
        self.ui.pushButton_choose_user_avatar.clicked.connect(self.interface_signals.choose_avatar)

        # Combo Boxes
        self.ui.comboBox_conversation_method.currentTextChanged.connect(self.interface_signals.on_comboBox_conversation_method_changed)
        self.ui.comboBox_speech_to_text_method.currentIndexChanged.connect(self.interface_signals.on_comboBox_speech_to_text_method_changed)
        self.ui.comboBox_program_language.currentIndexChanged.connect(self.interface_signals.on_comboBox_program_language_changed)
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

        # Line Edits
        self.ui.lineEdit_api_token_options.textChanged.connect(self.interface_signals.save_api_token_in_real_time)
        self.ui.lineEdit_user_name_options.textChanged.connect(self.interface_signals.save_username_in_real_time)
        self.ui.lineEdit_user_description_options.textChanged.connect(self.interface_signals.save_userpersonality_in_real_time)
        
        # Sliders
        self.ui.gpu_layers_horizontalSlider.valueChanged.connect(self.interface_signals.save_gpu_layers_in_real_time)
        self.ui.context_size_horizontalSlider.valueChanged.connect(self.interface_signals.save_context_size_in_real_time)
        self.ui.temperature_horizontalSlider.valueChanged.connect(self.interface_signals.save_temperature_in_real_time)
        self.ui.top_p_horizontalSlider.valueChanged.connect(self.interface_signals.save_top_p_in_real_time)
        self.ui.repeat_penalty_horizontalSlider.valueChanged.connect(self.interface_signals.save_repeat_penalty_in_real_time)
        self.ui.max_tokens_horizontalSlider.valueChanged.connect(self.interface_signals.save_max_tokens_in_real_time)
        
        # Check Box
        self.ui.checkBox_enable_mlock.stateChanged.connect(self.interface_signals.on_checkBox_enable_mlock_stateChanged)

        self.ui.stackedWidget.currentChanged.connect(self.interface_signals.on_stacked_widget_changed)

        # Translate
        self.setWindowTitle("Soul of Waifu")
        self.ui.pushButton_main.setText(self.tr(" Main"))
        self.ui.pushButton_create_character.setText(self.tr(" Create Character"))
        self.ui.pushButton_characters_gateway.setText(self.tr(" Characters Gateway"))
        self.ui.pushButton_options.setText(self.tr(" Options"))
        self.ui.pushButton_youtube.setText(self.tr(" YouTube"))
        self.ui.pushButton_discord.setText(self.tr(" Discord"))
        self.ui.pushButton_github.setText(self.tr(" Github"))
        self.ui.main_no_characters_advice_label.setText(self.tr("You haven\'t added any characters. Click on the button and create it"))
        self.ui.pushButton_create_character_2.setText(self.tr(" Create Character"))
        self.ui.main_no_characters_description_label.setText(self.tr("To start, click on \"Create a Character\" and create one."))
        self.ui.welcome_label.setText(self.tr("Welcome to Soul of Waifu"))
        self.ui.main_navigation_label.setText(self.tr("MAIN NAVIGATION"))
        self.ui.main_navigation_label_2.setText(self.tr("MAIN NAVIGATION"))
        self.ui.welcome_label_2.setText(self.tr("Welcome to Soul of Waifu, User"))
        self.ui.add_character_title_label.setText(self.tr("<html><head/><body><p>Enter the character ID to add it to the list</p></body></html>"))
        self.ui.add_character_id_label.setText(self.tr("Character ID:"))
        self.ui.character_id_lineEdit.setPlaceholderText(self.tr("Write Character ID"))
        self.ui.pushButton_add_character.setText(self.tr(" ADD"))
        self.ui.create_character_label.setText(self.tr("CREATE CHARACTER"))
        self.ui.create_character_label_2.setText(self.tr("CREATE CHARACTER"))
        self.ui.addcharacter_title_Label_2.setText(self.tr("<html><head/><body><p>Character building</p></body></html>"))
        self.ui.addcharacter_title_Label_3.setText(self.tr("<html><head/><body><p>Character\'s Image:</p></body></html>"))
        self.ui.addcharacter_title_Label_4.setText(self.tr("<html><head/><body><p>Character\'s Name:</p></body></html>"))
        self.ui.addcharacter_title_Label_5.setText(self.tr("<html><head/><body><p>Character\'s Name:</p></body></html>"))
        self.ui.pushButton_import_character_card.setText(self.tr("Import Character Card"))
        self.ui.character_building_label.setText(self.tr("Character\'s Building"))
        self.ui.character_image_building_label.setText(self.tr("Character\'s Image"))
        self.ui.character_name_building_label.setText(self.tr("Character\'s Name"))
        self.ui.lineEdit_character_name_building.setPlaceholderText(self.tr("Write your character\'s name here"))
        self.ui.character_description_building_label.setText(self.tr("Character\'s Description"))
        self.ui.textEdit_character_description_building.setHtml(self.tr("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p></body></html>"))
        self.ui.textEdit_character_description_building.setPlaceholderText(self.tr("Write your character\'s description here"))
        self.ui.character_personality_building_label.setText(self.tr("Character\'s Personality"))
        self.ui.textEdit_character_personality_building.setHtml(self.tr("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400;\"><br /></p></body></html>"))
        self.ui.textEdit_character_personality_building.setPlaceholderText(self.tr("Write your character\'s personality here"))
        self.ui.first_message_building_label.setText(self.tr("First Message"))
        self.ui.textEdit_first_message_building.setHtml(self.tr("<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'Muli SemiBold\'; font-size:10pt; font-weight:600; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400;\"><br /></p></body></html>"))
        self.ui.textEdit_first_message_building.setPlaceholderText(self.tr("Write your character\'s first message here"))
        self.ui.pushButton_create_character_3.setText(self.tr("Create Character"))
        self.ui.characters_gateway_label.setText(self.tr("CHARACTERS GATEWAY"))
        self.ui.lineEdit_search_character.setPlaceholderText(self.tr("Search"))
        self.ui.options_label.setText(self.tr("OPTIONS"))
        self.ui.conversation_method_title_label.setText(self.tr("Conversation Method"))
        self.ui.conversation_method_token_title_label.setText(self.tr("Write your token:"))
        self.ui.lineEdit_api_token_options.setPlaceholderText(self.tr("Write your API token here"))
        self.ui.sow_system_title_label.setText(self.tr("Soul of Waifu System"))
        self.ui.checkBox_enable_sow_system.setText(self.tr("Enable Soul of Waifu System"))
        self.ui.conversation_method_options_label.setText(self.tr("Conversation method:"))
        self.ui.comboBox_conversation_method.setItemText(0, self.tr("Character AI"))
        self.ui.comboBox_conversation_method.setItemText(1, self.tr("Mistral AI"))
        self.ui.comboBox_conversation_method.setItemText(2, self.tr("Local LLM"))
        self.ui.choose_your_avatar_label.setText(self.tr("Choose your avatar:"))
        self.ui.speech_to_text_title_label.setText(self.tr("Speech-To-Text"))
        self.ui.speech_to_text_method_label.setText(self.tr("Speech-To-Text method:"))
        self.ui.comboBox_speech_to_text_method.setItemText(0, self.tr("Google STT English"))
        self.ui.comboBox_speech_to_text_method.setItemText(1, self.tr("Google STT Russian"))
        self.ui.comboBox_speech_to_text_method.setItemText(2, self.tr("Vosk English"))
        self.ui.comboBox_speech_to_text_method.setItemText(3, self.tr("Vosk Russian"))
        self.ui.comboBox_speech_to_text_method.setItemText(4, self.tr("Local Whisper"))
        self.ui.choose_your_name_label.setText(self.tr("Write your name:"))
        self.ui.choose_your_description_label.setText(self.tr("Write your description:"))
        self.ui.user_building_title_label.setText(self.tr("User Building"))
        self.ui.lineEdit_user_name_options.setPlaceholderText(self.tr("Your name"))
        self.ui.lineEdit_user_description_options.setPlaceholderText(self.tr("Your description"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.configuration_tab), self.tr("Configuration"))
        self.ui.tabWidget_characters_gateway.setTabText(self.ui.tabWidget_characters_gateway.indexOf(self.ui.tab_character_ai), "Character AI")
        self.ui.tabWidget_characters_gateway.setTabText(self.ui.tabWidget_characters_gateway.indexOf(self.ui.tab_character_cards), "Character Card")
        self.ui.language_title_label.setText(self.tr("Language"))
        self.ui.comboBox_program_language.setItemText(0, self.tr("English"))
        self.ui.comboBox_program_language.setItemText(1, self.tr("Russian"))
        self.ui.devices_title_label.setText(self.tr("Devices"))
        self.ui.input_device_label.setText(self.tr("Input device:"))
        self.ui.output_device_label.setText(self.tr("Output device:"))
        self.ui.program_language_label.setText(self.tr("Program language:"))
        self.ui.translator_title_label.setText(self.tr("Translator"))
        self.ui.choose_translator_label.setText(self.tr("Choose translator:"))
        self.ui.comboBox_translator.setItemText(0, self.tr("None"))
        self.ui.comboBox_translator.setItemText(1, self.tr("Google"))
        self.ui.comboBox_translator.setItemText(2, self.tr("Yandex"))
        self.ui.comboBox_translator.setItemText(3, self.tr("Local Translator"))
        self.ui.target_language_translator_label.setText(self.tr("Target Language:"))
        self.ui.comboBox_target_language_translator.setItemText(0, self.tr("Russian"))
        self.ui.comboBox_mode_translator.setItemText(0, self.tr("Both"))
        self.ui.comboBox_mode_translator.setItemText(1, self.tr("User Message"))
        self.ui.comboBox_mode_translator.setItemText(2, self.tr("Character Message"))
        self.ui.mode_translator_label.setText(self.tr("Mode:"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.system_tab), self.tr("System"))
        self.ui.tabWidget_options.setTabText(self.ui.tabWidget_options.indexOf(self.ui.llm_tab), self.tr("Local LLM"))
        self.ui.character_name_chat.setText(self.tr("Character name"))
        self.ui.character_description_chat.setText(self.tr(""))
        self.ui.textEdit_write_user_message.setPlaceholderText(self.tr("Write your message to character..."))
        self.ui.creator_label.setText(self.tr("Created by Jofi"))
        self.ui.version_label.setText(self.tr("v2.0.0"))
        self.ui.menu_sow.setTitle(self.tr("Soul of Waifu"))
        self.ui.menu_help.setTitle(self.tr("Help"))
        self.ui.action_about_program.setText(self.tr("About Soul of Waifu"))
        self.ui.action_get_token_from_character_ai.setText(self.tr("Get Token from Character AI"))
        self.ui.action_create_new_character.setText(self.tr("Create new character"))
        self.ui.action_options.setText(self.tr("Options"))
        self.ui.action_discord.setText(self.tr("Get support from Discord"))
        self.ui.action_github.setText(self.tr("Get support from GitHub"))
        self.ui.action_faq.setText(self.tr("FAQ"))
        self.ui.choose_live2d_mode_label.setText(self.tr("Choose mode for Live2d model:"))
        self.ui.comboBox_live2d_mode.setItemText(0, self.tr("With GUI"))
        self.ui.comboBox_live2d_mode.setItemText(1, self.tr("Without GUI"))
        self.ui.comboBox_llms.setWhatsThis(self.tr("<html><head/><body><p>Choose your Local LLM from the list.</p></body></html>"))
        self.ui.llm_options_label.setText(self.tr("Local Model:"))
        self.ui.llm_title_label.setText(self.tr("Local LLM Settings"))
        self.ui.choose_llm_device_label.setText(self.tr("Choose device:"))
        self.ui.comboBox_llm_devices.setWhatsThis(self.tr("<html><head/><body><p>Select the device to which the LLM will be loaded.</p></body></html>"))
        self.ui.comboBox_llm_devices.setItemText(0, self.tr("CPU"))
        self.ui.comboBox_llm_devices.setItemText(1, self.tr("GPU"))
        self.ui.gpu_layers_label.setText(self.tr("GPU Layers:"))
        self.ui.checkBox_enable_mlock.setWhatsThis(self.tr("<html><head/><body><p>MLOCK is used to force the model to be held in RAM to improve LLM performance.</p></body></html>"))
        self.ui.checkBox_enable_mlock.setText(self.tr("Enable MLock"))
        self.ui.context_size_label.setText(self.tr("Context Size:"))
        self.ui.llm_title_label_2.setText(self.tr("Local LLM Conversation Settings:"))
        self.ui.reapet_penalty_label.setText(self.tr("Repeat Penalty:"))
        self.ui.temperature_label.setText(self.tr("Temperature:"))
        self.ui.temperature_value_label.setText(self.tr("Value: "))
        self.ui.top_p_label.setText(self.tr("Top P:"))
        self.ui.top_p_value_label.setText(self.tr("Value: "))
        self.ui.max_tokens_label.setText(self.tr("Max Tokens:"))
        self.ui.repeat_penalty_value_label.setText(self.tr("Value: "))
        self.ui.max_tokens_value_label.setText(self.tr("Value: "))
        self.ui.context_size_value_label.setText(self.tr("Value: "))
        self.ui.gpu_layers_value_label.setText(self.tr("Value: "))

    def check_for_updates(self, current_version):
        try:
            repo_url = "https://api.github.com/repos/jofizcd/Soul-of-Waifu/releases/latest"
            response = requests.get(repo_url)
            latest_release = response.json()
            latest_version = latest_release["tag_name"]

            print(latest_version)
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
        msg_box.setWindowTitle(self.tr("Update Available"))

        msg_box.setText(self.tr("A new version is available: ") + f"{latest_version}")
        msg_box.setInformativeText(self.tr("Would you like to update the program?"))

        close_button = msg_box.addButton(self.tr("Close"), QMessageBox.ButtonRole.RejectRole)
        github_button = msg_box.addButton(self.tr("Go to GitHub"), QMessageBox.ButtonRole.ActionRole)

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

        msg_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        msg_box.setDefaultButton(github_button)

        msg_box.exec()

        if msg_box.clickedButton() == github_button:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(github_url))

if __name__ == "__main__":
    if sys.platform == 'win32':
        app_id = "com.jofizcd.soul_of_waifu.v2"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    app = QApplication(sys.argv)

    # configuration = configuration.ConfigurationSettings()
    # selected_language = configuration.get_main_setting("program_language")

    # translator = QTranslator()

    # match selected_language:
    #     case 0:
    #         translator.load("resources\\translations\\sow_en.qm")
    #     case 1:
    #         translator.load("resources\\translations\\sow_ru.qm")

    # app.installTranslator(translator)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    main_window = MainWindow()
    main_window.setWindowIcon(QtGui.QIcon("resources\\icons\\logotype.ico"))
    main_window.show()    
    
    current_version = "v2.0.0"
    latest_version, github_url = main_window.check_for_updates(current_version)
    if latest_version:
        main_window.show_update_dialog(latest_version, github_url)     

    loop.run_forever()
