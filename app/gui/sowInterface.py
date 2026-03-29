import os
import yaml

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QListWidget
from PyQt6.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPoint
from PyQt6.QtGui import QColor, QPainter, QRadialGradient, QCursor, QFont, QPixmap, QPen, QBrush

from app.configuration import configuration

class Ui_MainWindow(object):
    def __init__(self):
        self.translations = {}
        
        self.configuration = configuration.ConfigurationSettings()
        selected_language = self.configuration.get_main_setting("program_language")

        match selected_language:
            case 0:
                self.load_translation("en")
            case 1:
                self.load_translation("ru")
    
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

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1350, 734)
        MainWindow.setMinimumSize(QtCore.QSize(1350, 734))

        MainWindow.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        MainWindow.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet("border: none;\n"
"background: transparent;")
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setStyleSheet("""
            background: transparent;
        """)
        self.centralwidget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for child in self.centralwidget.findChildren(QtWidgets.QWidget):
            child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.horizontalLayout_main_widget = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_main_widget.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_main_widget.setSpacing(0)
        self.horizontalLayout_main_widget.setObjectName("horizontalLayout_main_widget")
        self.centralwidget.setObjectName("centralwidget")

        self.main_widget = QtWidgets.QFrame(parent=self.centralwidget)
        self.main_widget.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.main_widget.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.main_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for child in self.main_widget.findChildren(QtWidgets.QWidget):
            child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.main_widget.setLineWidth(1)
        self.main_widget.setStyleSheet("""
            #main_widget {
                    border: 1px solid rgb(50, 50, 55);
                }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.main_widget.setGraphicsEffect(shadow)
        self.main_widget.setObjectName("main_widget")

        self.gridLayout_20 = QtWidgets.QGridLayout(self.main_widget)
        self.gridLayout_20.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_20.setSpacing(0)
        self.gridLayout_20.setObjectName("gridLayout_20")
        
        self.menu_bar = QtWidgets.QFrame(parent=self.main_widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.menu_bar.sizePolicy().hasHeightForWidth())
        self.menu_bar.setSizePolicy(sizePolicy)
        self.menu_bar.setMinimumSize(QtCore.QSize(0, 25))
        self.menu_bar.setMaximumSize(QtCore.QSize(16777215, 25))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.menu_bar.setFont(font)
        self.menu_bar.setStyleSheet("#menu_bar {\n"
"    background-color: rgb(27,27,27);\n"
"}")
        self.menu_bar.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.menu_bar.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.menu_bar.setObjectName("menu_bar")
        
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.menu_bar)
        self.horizontalLayout_7.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")

        self.toggle_sidebar_btn = QtWidgets.QPushButton(parent=self.menu_bar)
        self.toggle_sidebar_btn.setMinimumSize(QtCore.QSize(40, 25))
        self.toggle_sidebar_btn.setMaximumSize(QtCore.QSize(40, 25))
        self.toggle_sidebar_btn.setText("≡")
        font_toggle = QtGui.QFont()
        font_toggle.setPointSize(14)
        self.toggle_sidebar_btn.setFont(font_toggle)
        self.toggle_sidebar_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.toggle_sidebar_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.toggle_sidebar_btn.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                color: rgb(190, 190, 190);
                border: none; 
            }
            QPushButton:hover { background-color: rgb(50, 50, 50); color: white; }
            QPushButton:pressed { background-color: rgb(30, 30, 30); }
        """)
        self.horizontalLayout_7.addWidget(self.toggle_sidebar_btn)
        
        self.frame_version = QtWidgets.QFrame(parent=self.menu_bar)
        self.frame_version.setMinimumSize(QtCore.QSize(1000, 0))
        self.frame_version.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_version.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_version.setObjectName("frame_version")
        
        self.version_label = QtWidgets.QLabel(parent=self.frame_version)
        self.version_label.setGeometry(QtCore.QRect(0, 0, 143, 29))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.version_label.sizePolicy().hasHeightForWidth())
        self.version_label.setSizePolicy(sizePolicy)
        self.version_label.setMinimumSize(QtCore.QSize(100, 0))
        
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.version_label.setFont(font)
        self.version_label.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_label.setIndent(10)
        self.version_label.setObjectName("version_label")
        self.horizontalLayout_7.addWidget(self.frame_version)
        
        self.right_buttons = QtWidgets.QFrame(parent=self.menu_bar)
        self.right_buttons.setMinimumSize(QtCore.QSize(0, 0))
        self.right_buttons.setMaximumSize(QtCore.QSize(150, 16777215))
        self.right_buttons.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.right_buttons.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.right_buttons.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.right_buttons.setObjectName("right_buttons")
        
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.right_buttons)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        
        self.minimize_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.minimize_btn.setMinimumSize(QtCore.QSize(35, 25))
        self.minimize_btn.setMaximumSize(QtCore.QSize(35, 25))
        self.minimize_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.minimize_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.minimize_btn.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    border: none; \n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(50, 50, 50); \n"
"    border-style: solid;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(23, 23, 23); \n"
"    border-style: solid; \n"
"}")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("app/gui/icons/minimize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.minimize_btn.setIcon(icon3)
        self.minimize_btn.setIconSize(QtCore.QSize(12, 12))
        self.minimize_btn.setObjectName("minimize_btn")
        self.horizontalLayout_6.addWidget(self.minimize_btn)
        self.maximize_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.maximize_btn.setMinimumSize(QtCore.QSize(35, 25))
        self.maximize_btn.setMaximumSize(QtCore.QSize(35, 25))
        self.maximize_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.maximize_btn.setFont(font)
        self.maximize_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.maximize_btn.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    border: none; \n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(50, 50, 50); \n"
"    border-style: solid;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(23, 23, 23); \n"
"    border-style: solid; \n"
"}")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("app/gui/icons/maximize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.maximize_btn.setIcon(icon4)
        self.maximize_btn.setIconSize(QtCore.QSize(11, 11))
        self.maximize_btn.setObjectName("maximize_btn")
        self.horizontalLayout_6.addWidget(self.maximize_btn)
        self.close_app_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.close_app_btn.setMinimumSize(QtCore.QSize(35, 25))
        self.close_app_btn.setMaximumSize(QtCore.QSize(35, 25))
        self.close_app_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_app_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.close_app_btn.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    border: none; \n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    \n"
"    background-color: rgb(207, 0, 3);\n"
"    border-style: solid;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(218, 0, 0); \n"
"    border-style: solid; \n"
"}")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap("app/gui/icons/close.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.close_app_btn.setIcon(icon5)
        self.close_app_btn.setIconSize(QtCore.QSize(11, 11))
        self.close_app_btn.setObjectName("close_app_btn")
        self.horizontalLayout_6.addWidget(self.close_app_btn)
        self.horizontalLayout_7.addWidget(self.right_buttons, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        self.gridLayout_20.addWidget(self.menu_bar, 0, 0, 1, 3)
        self.SideBar_Right = QtWidgets.QWidget(parent=self.main_widget)
        self.SideBar_Right.setMinimumSize(QtCore.QSize(800, 648))
        self.SideBar_Right.setStyleSheet("#SideBar_Right {\n"
"    background-color: rgb(27,27,27);\n"
"    color: rgb(227, 227, 227);\n"
"}")
        self.SideBar_Right.setObjectName("SideBar_Right")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.SideBar_Right)
        self.gridLayout_3.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.stackedWidget = QtWidgets.QStackedWidget(parent=self.SideBar_Right)
        self.stackedWidget.setStyleSheet("background-color: rgb(27,27,27);")
        self.stackedWidget.setObjectName("stackedWidget")
        self.main_no_characters_page = QtWidgets.QWidget()
        self.main_no_characters_page.setStyleSheet("background-color: rgb(27,27,27);")
        self.main_no_characters_page.setObjectName("main_no_characters_page")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.main_no_characters_page)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.frame_main_button = QtWidgets.QFrame(parent=self.main_no_characters_page)
        self.frame_main_button.setMinimumSize(QtCore.QSize(500, 65))
        self.frame_main_button.setStyleSheet("background-color: transparent;\n"
"color: rgb(227, 227, 227);\n"
"border: none;")
        self.frame_main_button.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_main_button.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_main_button.setObjectName("frame_main_button")
        self.gridLayout_8 = QtWidgets.QGridLayout(self.frame_main_button)
        self.gridLayout_8.setObjectName("gridLayout_8")
        spacerItem1 = QtWidgets.QSpacerItem(388, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_8.addItem(spacerItem1, 0, 0, 1, 1)
        self.pushButton_create_character_2 = QtWidgets.QPushButton(parent=self.frame_main_button)
        self.pushButton_create_character_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_create_character_2.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_create_character_2.sizePolicy().hasHeightForWidth())
        self.pushButton_create_character_2.setSizePolicy(sizePolicy)
        self.pushButton_create_character_2.setMinimumSize(QtCore.QSize(200, 50))
        self.pushButton_create_character_2.setMaximumSize(QtCore.QSize(200, 100))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setKerning(True)
        self.pushButton_create_character_2.setFont(font)
        self.pushButton_create_character_2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_2.setMouseTracking(False)
        self.pushButton_create_character_2.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 25px;
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
        self.pushButton_create_character_2.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_create_character_2.setCheckable(False)
        self.pushButton_create_character_2.setChecked(False)
        self.pushButton_create_character_2.setAutoExclusive(True)
        self.pushButton_create_character_2.setObjectName("pushButton_create_character_2")
        self.gridLayout_8.addWidget(self.pushButton_create_character_2, 0, 1, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(399, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_8.addItem(spacerItem2, 0, 2, 1, 1)
        self.gridLayout_7.addWidget(self.frame_main_button, 4, 0, 2, 1, QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.main_no_characters_description_label = QtWidgets.QLabel(parent=self.main_no_characters_page)
        self.main_no_characters_description_label.setMinimumSize(QtCore.QSize(500, 51))
        self.main_no_characters_description_label.setMaximumSize(QtCore.QSize(16777215, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Light")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        font.setKerning(True)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.main_no_characters_description_label.setFont(font)
        self.main_no_characters_description_label.setAcceptDrops(False)
        self.main_no_characters_description_label.setStyleSheet("background-color: transparent;\n"
"color: rgb(227, 227, 227);\n"
"border: none;")
        self.main_no_characters_description_label.setScaledContents(False)
        self.main_no_characters_description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_no_characters_description_label.setWordWrap(True)
        self.main_no_characters_description_label.setObjectName("main_no_characters_description_label")
        self.gridLayout_7.addWidget(self.main_no_characters_description_label, 0, 0, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(20, 385, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout_7.addItem(spacerItem3, 6, 0, 1, 1)
        self.main_no_characters_advice_label = QtWidgets.QLabel(parent=self.main_no_characters_page)
        self.main_no_characters_advice_label.setMinimumSize(QtCore.QSize(500, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.main_no_characters_advice_label.setFont(font)
        self.main_no_characters_advice_label.setStyleSheet("background-color: transparent;\n"
"color: rgb(227, 227, 227);\n"
"border: none;")
        self.main_no_characters_advice_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_no_characters_advice_label.setObjectName("main_no_characters_advice_label")
        self.gridLayout_7.addWidget(self.main_no_characters_advice_label, 2, 0, 1, 1)
        spacerItem4 = QtWidgets.QSpacerItem(16, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout_7.addItem(spacerItem4, 3, 0, 1, 1)
        spacerItem5 = QtWidgets.QSpacerItem(20, 200, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout_7.addItem(spacerItem5, 1, 0, 1, 1)
        self.stackedWidget.addWidget(self.main_no_characters_page)
        self.main_characters_page = QtWidgets.QWidget()
        self.main_characters_page.setStyleSheet("background-color: rgb(27,27,27);")
        self.main_characters_page.setObjectName("main_characters_page")
        self.gridLayout_9 = QtWidgets.QGridLayout(self.main_characters_page)
        self.gridLayout_9.setContentsMargins(0, 0, 20, 0)
        self.gridLayout_9.setSpacing(0)
        self.gridLayout_9.setObjectName("gridLayout_9")
        
        self.scrollArea_characters_list = QtWidgets.QScrollArea(parent=self.main_characters_page)
        self.scrollArea_characters_list.setStyleSheet("""
			QScrollArea {
				background-color: transparent;
				color: rgb(227, 227, 227);
				border: none;
				padding-left: 25px;
			}
			QScrollBar:vertical,
			QScrollBar:horizontal {
				width: 0px;
				height: 0px;
				background: transparent;
			}
        """)
        self.scrollArea_characters_list.setWidgetResizable(True)
        self.scrollArea_characters_list.setObjectName("scrollArea_characters_list")
        self.scrollAreaWidgetContents_characters_list = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_characters_list.setGeometry(QtCore.QRect(0, 0, 1057, 553))
        self.scrollAreaWidgetContents_characters_list.setObjectName("scrollAreaWidgetContents_characters_list")
        self.scrollAreaWidgetContents_characters_list.setContentsMargins(0, 0, 0, 0)
        
        self.scrollArea_characters_list.setWidget(self.scrollAreaWidgetContents_characters_list)
        self.gridLayout_9.addWidget(self.scrollArea_characters_list, 1, 0, 1, 1)

        self.frame_welcome_to = QtWidgets.QFrame(parent=self.main_characters_page)
        self.frame_welcome_to.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_welcome_to.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_welcome_to.setObjectName("frame_welcome_to")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.frame_welcome_to)
        self.gridLayout_6.setContentsMargins(32, 10, 10, 10)
        self.gridLayout_6.setObjectName("gridLayout_6")
        spacerItem6 = QtWidgets.QSpacerItem(651, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_6.addItem(spacerItem6, 0, 3, 1, 1)
        self.user_avatar_label = QtWidgets.QLabel(parent=self.frame_welcome_to)
        self.user_avatar_label.setMinimumSize(QtCore.QSize(51, 51))
        self.user_avatar_label.setMaximumSize(QtCore.QSize(51, 51))
        self.user_avatar_label.setStyleSheet("")
        self.user_avatar_label.setText("")
        self.user_avatar_label.setPixmap(QtGui.QPixmap("app/gui/icons/person.png"))
        self.user_avatar_label.setScaledContents(True)
        self.user_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.user_avatar_label.setObjectName("user_avatar_label")
        self.gridLayout_6.addWidget(self.user_avatar_label, 0, 0, 1, 1)
        self.welcome_label_2 = QtWidgets.QLabel(parent=self.frame_welcome_to)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.welcome_label_2.setFont(font)
        self.welcome_label_2.setStyleSheet("color: rgb(227, 227, 227);")
        self.welcome_label_2.setObjectName("welcome_label_2")
        self.gridLayout_6.addWidget(self.welcome_label_2, 0, 2, 1, 1)
        spacerItem7 = QtWidgets.QSpacerItem(5, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_6.addItem(spacerItem7, 0, 1, 1, 1)

        self.search_bar_menu = ModernSearchBar(parent=self.frame_welcome_to)
        self.search_bar_menu.setMinimumSize(QtCore.QSize(250, 45))
        self.search_bar_menu.setMaximumSize(QtCore.QSize(300, 45))
        
        self.lineEdit_search_character_menu = self.search_bar_menu.line_edit
        self.lineEdit_search_character_menu.setPlaceholderText("Search character...")
        
        self.gridLayout_6.addWidget(self.search_bar_menu, 0, 4, 1, 1)
        self.gridLayout_9.addWidget(self.frame_welcome_to, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.main_characters_page)
        self.create_character_page = QtWidgets.QWidget()
        self.create_character_page.setObjectName("create_character_page")
        self.gridLayout_10 = QtWidgets.QGridLayout(self.create_character_page)
        self.gridLayout_10.setObjectName("gridLayout_10")
        spacerItem8 = QtWidgets.QSpacerItem(20, 193, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout_10.addItem(spacerItem8, 0, 0, 1, 1)
        self.add_character_title_label = QtWidgets.QLabel(parent=self.create_character_page)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.add_character_title_label.setFont(font)
        self.add_character_title_label.setStyleSheet("color: rgb(227, 227, 227);\n"
"")
        self.add_character_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.add_character_title_label.setObjectName("add_character_title_label")
        self.gridLayout_10.addWidget(self.add_character_title_label, 1, 0, 1, 1)
        self.frame_create_character = QtWidgets.QFrame(parent=self.create_character_page)
        self.frame_create_character.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_create_character.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_create_character.setObjectName("frame_create_character")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.frame_create_character)
        self.gridLayout_5.setObjectName("gridLayout_5")
        spacerItem9 = QtWidgets.QSpacerItem(94, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_5.addItem(spacerItem9, 1, 0, 1, 1)
        self.add_character_id_label = QtWidgets.QLabel(parent=self.frame_create_character)
        self.add_character_id_label.setMinimumSize(QtCore.QSize(90, 35))
        self.add_character_id_label.setMaximumSize(QtCore.QSize(90, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.add_character_id_label.setFont(font)
        self.add_character_id_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.add_character_id_label.setMidLineWidth(0)
        self.add_character_id_label.setObjectName("add_character_id_label")
        self.gridLayout_5.addWidget(self.add_character_id_label, 1, 1, 1, 1)
        self.pushButton_add_character = QtWidgets.QPushButton(parent=self.frame_create_character)
        self.pushButton_add_character.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_add_character.setMinimumSize(QtCore.QSize(80, 31))
        self.pushButton_add_character.setMaximumSize(QtCore.QSize(80, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_add_character.setFont(font)
        self.pushButton_add_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_add_character.setStyleSheet("""
            QPushButton {
                background-color: #2D2D2D;
                color: #BBBBBB;
                border-radius: 15px;
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
        self.pushButton_add_character.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_add_character.setAutoExclusive(True)
        self.pushButton_add_character.setObjectName("pushButton_add_character")
        self.gridLayout_5.addWidget(self.pushButton_add_character, 2, 3, 1, 1)
        self.character_id_lineEdit = QtWidgets.QLineEdit(parent=self.frame_create_character)
        self.character_id_lineEdit.setMinimumSize(QtCore.QSize(651, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_id_lineEdit.setFont(font)
        self.character_id_lineEdit.setStyleSheet("QLineEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QLineEdit::placeholder {\n"
"    color: #888888;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid #444;\n"
"}")
        self.character_id_lineEdit.setObjectName("character_id_lineEdit")
        self.gridLayout_5.addWidget(self.character_id_lineEdit, 1, 2, 1, 2)
        spacerItem10 = QtWidgets.QSpacerItem(135, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_5.addItem(spacerItem10, 1, 4, 1, 1)
        spacerItem11 = QtWidgets.QSpacerItem(771, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_5.addItem(spacerItem11, 2, 0, 1, 3)
        spacerItem12 = QtWidgets.QSpacerItem(135, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_5.addItem(spacerItem12, 2, 4, 1, 1)
        spacerItem13 = QtWidgets.QSpacerItem(20, 95, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout_5.addItem(spacerItem13, 3, 3, 1, 1)
        spacerItem14 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout_5.addItem(spacerItem14, 0, 2, 1, 1)
        self.gridLayout_10.addWidget(self.frame_create_character, 2, 0, 1, 1)
        spacerItem15 = QtWidgets.QSpacerItem(20, 238, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout_10.addItem(spacerItem15, 3, 0, 1, 1)
        self.frame_create_character.raise_()
        self.add_character_title_label.raise_()
        self.stackedWidget.addWidget(self.create_character_page)
        

        self.create_character_page_2 = QtWidgets.QWidget()
        self.create_character_page_2.setObjectName("create_character_page_2")
        self.create_character_page_2.setStyleSheet("background: transparent;")
        self.layout_page_2 = QtWidgets.QHBoxLayout(self.create_character_page_2)
        self.layout_page_2.setContentsMargins(0, 0, 0, 0)
        self.layout_page_2.setSpacing(0)
        self.anchor_menu_building = QtWidgets.QListWidget(self.create_character_page_2)
        self.anchor_menu_building.setObjectName("anchor_menu_building")
        self.anchor_menu_building.setFixedWidth(220)
        self.anchor_menu_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.anchor_menu_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.anchor_menu_building.setStyleSheet("""
            QListWidget {
                background-color: rgba(15, 15, 18, 0.4);
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                padding-top: 20px;
                outline: none;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.5);
                font-family: 'Inter Tight SemiBold';
                font-size: 13px;
                padding: 12px 20px;
                border-radius: 8px;
                margin: 4px 12px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.9);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border-left: 3px solid #d4d4d4;
                font-weight: bold;
            }
        """)
        
        self.item_general_info = QtWidgets.QListWidgetItem("General Info")
        self.item_personality = QtWidgets.QListWidgetItem("Personality & Scenario")
        self.item_dialogues = QtWidgets.QListWidgetItem("Dialogues")
        self.item_advanced = QtWidgets.QListWidgetItem("Advanced & Lore")
        self.item_export = QtWidgets.QListWidgetItem("Export / Utils")

        self.anchor_menu_building.addItem(self.item_general_info)
        self.anchor_menu_building.addItem(self.item_personality)
        self.anchor_menu_building.addItem(self.item_dialogues)
        self.anchor_menu_building.addItem(self.item_advanced)
        self.anchor_menu_building.addItem(self.item_export)
            
        self.layout_page_2.addWidget(self.anchor_menu_building)

        self.right_container = QtWidgets.QWidget(self.create_character_page_2)
        self.right_layout = QtWidgets.QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.scrollArea_character_building = QtWidgets.QScrollArea(self.right_container)
        self.scrollArea_character_building.setWidgetResizable(True)
        self.scrollArea_character_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_character_building.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background-color: transparent; width: 8px; margin: 10px 0px 10px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.1); min-height: 30px; border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.2); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }
        """)

        self.scrollAreaWidgetContents_character_building = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_building.setStyleSheet("background: transparent;")
        
        self.cards_layout = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_character_building)
        self.cards_layout.setContentsMargins(40, 40, 40, 80)
        self.cards_layout.setSpacing(25)

        def create_glass_card_building(title_text):
            card = QtWidgets.QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: rgba(25, 25, 30, 0.4);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                }
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(25)
            shadow.setColor(QColor(0, 0, 0, 80))
            shadow.setOffset(0, 5)
            card.setGraphicsEffect(shadow)
            
            layout = QtWidgets.QVBoxLayout(card)
            layout.setContentsMargins(25, 25, 25, 25)
            layout.setSpacing(15)
            
            title = QtWidgets.QLabel(title_text)
            title.setStyleSheet("font-family: 'Inter Tight SemiBold'; font-size: 18px; color: rgba(255, 255, 255, 0.9); border: none; background: transparent;")
            layout.addWidget(title)
            
            return card, layout

        font_label = QtGui.QFont("Inter Tight Medium", 11)
        font_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        font_input = QtGui.QFont("Inter Tight Medium", 10)
        font_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        input_style = """
            QLineEdit, QTextEdit {
                background-color: rgba(15, 15, 18, 0.6);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 10px;
                selection-background-color: rgba(255, 255, 255, 0.2);
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.3);
                background-color: rgba(25, 25, 30, 0.8);
            }
        """
        self.general_info_text = self.translations.get("character_creator_title_general_info", "General Information")
        self.card_general, layout_gen = create_glass_card_building(self.general_info_text)
        
        row_avatar_name = QtWidgets.QHBoxLayout()
        row_avatar_name.setSpacing(20)
        
        self.character_image_building_label = QtWidgets.QLabel("Avatar")
        self.pushButton_import_character_image = QtWidgets.QPushButton()
        self.pushButton_import_character_image.setFixedSize(100, 100)
        self.pushButton_import_character_image.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_import_character_image.setStyleSheet("""
            QPushButton { background-color: rgba(0,0,0,0.4); border: 2px dashed rgba(255,255,255,0.15); border-radius: 12px; }
            QPushButton:hover { border: 2px dashed rgba(255, 255, 255, 0.5); background-color: rgba(255, 255, 255, 0.05); }
        """)
        icon_image_import = QtGui.QIcon()
        icon_image_import.addPixmap(QtGui.QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_image.setIcon(icon_image_import)
        self.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
        
        avatar_vbox = QtWidgets.QVBoxLayout()
        avatar_vbox.addWidget(self.pushButton_import_character_image)
        avatar_vbox.addStretch()
        row_avatar_name.addLayout(avatar_vbox)

        vbox_name = QtWidgets.QVBoxLayout()
        self.character_name_building_label = QtWidgets.QLabel("Character Name")
        self.character_name_building_label.setFont(font_label)
        self.character_name_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        
        self.lineEdit_character_name_building = QtWidgets.QLineEdit()
        self.lineEdit_character_name_building.setFont(font_input)
        self.lineEdit_character_name_building.setFixedHeight(45)
        self.lineEdit_character_name_building.setStyleSheet(input_style)
        
        vbox_name.addWidget(self.character_name_building_label)
        vbox_name.addWidget(self.lineEdit_character_name_building)
        vbox_name.addStretch()
        row_avatar_name.addLayout(vbox_name)
        
        layout_gen.addLayout(row_avatar_name)
        
        self.character_description_building_label = QtWidgets.QLabel("Description")
        self.character_description_building_label.setFont(font_label)
        self.character_description_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 10px;")
        
        self.textEdit_character_description_building = AutoResizingTextEdit()
        self.textEdit_character_description_building.setFont(font_input)
        self.textEdit_character_description_building.setStyleSheet(input_style)
        
        layout_gen.addWidget(self.character_description_building_label)
        layout_gen.addWidget(self.textEdit_character_description_building)
        self.cards_layout.addWidget(self.card_general)

        self.personality_title = self.translations.get("character_creator_title_personality", "Personality & Scenario")
        self.card_pers, layout_pers = create_glass_card_building(self.personality_title)
        
        self.character_personality_building_label = QtWidgets.QLabel("Personality")
        self.character_personality_building_label.setFont(font_label)
        self.character_personality_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        self.textEdit_character_personality_building = AutoResizingTextEdit()
        self.textEdit_character_personality_building.setFont(font_input)
        self.textEdit_character_personality_building.setStyleSheet(input_style)
        
        self.character_scenario_building_label = QtWidgets.QLabel("Scenario")
        self.character_scenario_building_label.setFont(font_label)
        self.character_scenario_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 10px;")
        self.textEdit_scenario = AutoResizingTextEdit()
        self.textEdit_scenario.setFont(font_input)
        self.textEdit_scenario.setStyleSheet(input_style)
        
        layout_pers.addWidget(self.character_personality_building_label)
        layout_pers.addWidget(self.textEdit_character_personality_building)
        layout_pers.addWidget(self.character_scenario_building_label)
        layout_pers.addWidget(self.textEdit_scenario)
        self.cards_layout.addWidget(self.card_pers)

        self.dialogues_title = self.translations.get("character_creator_title_dialogues", "Dialogues & Greetings")
        self.card_dial, layout_dial = create_glass_card_building(self.dialogues_title)
        
        self.first_message_building_label = QtWidgets.QLabel("First Message")
        self.first_message_building_label.setFont(font_label)
        self.first_message_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        self.textEdit_first_message_building = AutoResizingTextEdit()
        self.textEdit_first_message_building.setFont(font_input)
        self.textEdit_first_message_building.setStyleSheet(input_style)
        
        self.alternate_greetings_building_label = QtWidgets.QLabel("Alternate Greetings")
        self.alternate_greetings_building_label.setFont(font_label)
        self.alternate_greetings_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 10px;")
        self.textEdit_alternate_greetings = AutoResizingTextEdit()
        self.textEdit_alternate_greetings.setFont(font_input)
        self.textEdit_alternate_greetings.setStyleSheet(input_style)
        
        self.example_messages_building_label = QtWidgets.QLabel("Example Messages")
        self.example_messages_building_label.setFont(font_label)
        self.example_messages_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 10px;")
        self.textEdit_example_messages = AutoResizingTextEdit()
        self.textEdit_example_messages.setFont(font_input)
        self.textEdit_example_messages.setStyleSheet(input_style)
        
        layout_dial.addWidget(self.first_message_building_label)
        layout_dial.addWidget(self.textEdit_first_message_building)
        layout_dial.addWidget(self.alternate_greetings_building_label)
        layout_dial.addWidget(self.textEdit_alternate_greetings)
        layout_dial.addWidget(self.example_messages_building_label)
        layout_dial.addWidget(self.textEdit_example_messages)
        self.cards_layout.addWidget(self.card_dial)

        self.advanced_settings_title = self.translations.get("character_creator_title_advanced", "Advanced Settings & Lore")
        self.card_adv, layout_adv = create_glass_card_building(self.advanced_settings_title)
        
        row_combos = QtWidgets.QHBoxLayout()
        row_combos.setSpacing(20)
        
        combo_style = """
            QComboBox {
                background-color: rgba(15, 15, 18, 0.4);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 8px 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.05),
                                            stop:1 rgba(0, 0, 0, 0.05));
            }
            QComboBox:hover {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.08),
                                            stop:1 rgba(0, 0, 0, 0.08));
            }
            QComboBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.6);
                outline: none;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                image: url(:/sowInterface/arrowDown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 30, 35, 0.8);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                selection-background-color: rgba(255, 255, 255, 0.15);
                selection-color: #ffffff;
                padding: 5px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                background: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.1),
                                            stop:1 rgba(255, 255, 255, 0.05));
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.15),
                                            stop:1 rgba(255, 255, 255, 0.05));
                color: #ffffff;
            }
            QScrollBar:vertical {
                background-color: rgba(30, 30, 35, 0.8);
                width: 12px;
                margin: 0px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 0.2);
                min-height: 30px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
            QScrollBar::handle:vertical:pressed {
                background-color: rgba(255, 255, 255, 0.25);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """

        vbox_persona = QtWidgets.QVBoxLayout()
        self.user_persona_building_label = QtWidgets.QLabel("User Persona")
        self.user_persona_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        self.comboBox_user_persona_building = QtWidgets.QComboBox()
        self.comboBox_user_persona_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_user_persona_building.setFont(font)
        self.comboBox_user_persona_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_user_persona_building.setFixedHeight(40)
        self.comboBox_user_persona_building.setStyleSheet(combo_style)
        vbox_persona.addWidget(self.user_persona_building_label)
        vbox_persona.addWidget(self.comboBox_user_persona_building)
        
        vbox_prompt = QtWidgets.QVBoxLayout()
        self.system_prompt_building_label = QtWidgets.QLabel("System Prompt")
        self.system_prompt_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        self.comboBox_system_prompt_building = QtWidgets.QComboBox()
        self.comboBox_system_prompt_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_system_prompt_building.setFont(font)
        self.comboBox_system_prompt_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_system_prompt_building.setFixedHeight(40)
        self.comboBox_system_prompt_building.setStyleSheet(combo_style)
        vbox_prompt.addWidget(self.system_prompt_building_label)
        vbox_prompt.addWidget(self.comboBox_system_prompt_building)

        vbox_lore = QtWidgets.QVBoxLayout()
        self.lorebook_building_label = QtWidgets.QLabel("Lorebook")
        self.lorebook_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none;")
        self.comboBox_lorebook_building = QtWidgets.QComboBox()
        self.comboBox_lorebook_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_lorebook_building.setFont(font)
        self.comboBox_lorebook_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_lorebook_building.setFixedHeight(40)
        self.comboBox_lorebook_building.setStyleSheet(combo_style)
        vbox_lore.addWidget(self.lorebook_building_label)
        vbox_lore.addWidget(self.comboBox_lorebook_building)
        
        row_combos.addLayout(vbox_persona)
        row_combos.addLayout(vbox_prompt)
        row_combos.addLayout(vbox_lore)
        
        self.creator_notes_building_label = QtWidgets.QLabel("Creator Notes (Metadata)")
        self.creator_notes_building_label.setFont(font_label)
        self.creator_notes_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 15px;")
        self.textEdit_creator_notes = AutoResizingTextEdit()
        self.textEdit_creator_notes.setFont(font_input)
        self.textEdit_creator_notes.setStyleSheet(input_style)
        
        self.character_version_building_label = QtWidgets.QLabel("Card Version")
        self.character_version_building_label.setFont(font_label)
        self.character_version_building_label.setStyleSheet("color: #aaaaaa; background: transparent; border: none; margin-top: 15px;")
        self.textEdit_character_version = QtWidgets.QTextEdit()
        self.textEdit_character_version.setFixedHeight(45)
        self.textEdit_character_version.setFont(font_input)
        self.textEdit_character_version.setStyleSheet(input_style)

        layout_adv.addLayout(row_combos)
        layout_adv.addWidget(self.creator_notes_building_label)
        layout_adv.addWidget(self.textEdit_creator_notes)
        layout_adv.addWidget(self.character_version_building_label)
        layout_adv.addWidget(self.textEdit_character_version)
        self.cards_layout.addWidget(self.card_adv)

        self.export_tools_title = self.translations.get("character_creator_title_export", "Export & Tools")
        self.card_export, layout_export = create_glass_card_building(self.export_tools_title)
        
        row_tools = QtWidgets.QHBoxLayout()
        row_tools.setSpacing(15)
        
        btn_style_tools = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.8); 
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px; padding: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); color: white;}
            QPushButton:pressed { background-color: rgba(0, 0, 0, 0.3); }
        """
        
        self.pushButton_import_character_card = QtWidgets.QPushButton("Import Character Card")
        self.pushButton_import_character_card.setStyleSheet(btn_style_tools)
        self.pushButton_import_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        self.pushButton_export_character_card = QtWidgets.QPushButton("Export Character Card")
        self.pushButton_export_character_card.setStyleSheet(btn_style_tools)
        self.pushButton_export_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        self.pushButton_clean_character_card = QtWidgets.QPushButton("Clear All Fields")
        self.pushButton_clean_character_card.setStyleSheet(btn_style_tools + "QPushButton:hover { border: 1px solid #d32f2f; color: #ff6b6b; }")
        self.pushButton_clean_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        row_tools.addWidget(self.pushButton_import_character_card)
        row_tools.addWidget(self.pushButton_export_character_card)
        row_tools.addWidget(self.pushButton_clean_character_card)
        
        layout_export.addLayout(row_tools)
        self.cards_layout.addWidget(self.card_export)

        self.cards_layout.addStretch()
        
        self.creation_cards_mapping = {
            0: self.card_general,
            1: self.card_pers,
            2: self.card_dial,
            3: self.card_adv,
            4: self.card_export
        }

        self.scrollArea_character_building.setWidget(self.scrollAreaWidgetContents_character_building)
        self.right_layout.addWidget(self.scrollArea_character_building)
        self.frame_bottom_character_creation = QtWidgets.QFrame(self.right_container)
        self.frame_bottom_character_creation.setFixedHeight(70)
        self.frame_bottom_character_creation.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 15, 18, 0.85);
                border-top: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        shadow_footer = QGraphicsDropShadowEffect()
        shadow_footer.setBlurRadius(20)
        shadow_footer.setColor(QColor(0, 0, 0, 150))
        shadow_footer.setOffset(0, -5)
        self.frame_bottom_character_creation.setGraphicsEffect(shadow_footer)
        self.bottom_layout = QtWidgets.QHBoxLayout(self.frame_bottom_character_creation)
        self.bottom_layout.setContentsMargins(40, 0, 40, 0)
        self.bottom_layout.setSpacing(15)
        self.total_tokens_building_label = QtWidgets.QLabel("Total Tokens: 0")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.total_tokens_building_label.setFont(font)
        self.total_tokens_building_label.setStyleSheet("font-family: 'Inter Tight SemiBold'; font-size: 15px; color: rgba(255,255,255,0.6); border: none; background: transparent;")
        self.pushButton_preview_prompt = QtWidgets.QPushButton("Preview Raw")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_preview_prompt.setFont(font)
        self.pushButton_preview_prompt.setFixedSize(130, 42)
        self.pushButton_preview_prompt.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_preview_prompt.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 0.7);
                border-radius: 8px;
                border: 1px dashed rgba(255, 255, 255, 0.2);
                font-family: 'Inter Tight SemiBold';
                font-size: 13px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.05); color: white; border-style: solid; }
        """)

        self.pushButton_create_character_3 = QtWidgets.QPushButton("Create Character")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_create_character_3.setFont(font)
        self.pushButton_create_character_3.setFixedSize(180, 42)
        self.pushButton_create_character_3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_3.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 15, 18, 0.4);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 8px 12px;
                font-family: 'Inter Tight SemiBold';
                font-size: 14px;
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.05),
                                            stop:1 rgba(0, 0, 0, 0.05));
            }
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.08),
                                            stop:1 rgba(0, 0, 0, 0.08));
            }
            QPushButton:pressed {
                border: 1px solid rgba(255, 255, 255, 0.3);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(0, 0, 0, 0.05),
                                            stop:1 rgba(255, 255, 255, 0.05));
            }
            QPushButton:focus {
                border: 1px solid rgba(255, 255, 255, 0.6);
                outline: none;
            }
        """)

        self.bottom_layout.addWidget(self.total_tokens_building_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.pushButton_preview_prompt)
        self.bottom_layout.addWidget(self.pushButton_create_character_3)
        self.right_layout.addWidget(self.frame_bottom_character_creation)
        self.layout_page_2.addWidget(self.right_container)
        self.stackedWidget.addWidget(self.create_character_page_2)

        self.charactersgateway_page = QtWidgets.QWidget()
        self.charactersgateway_page.setObjectName("charactersgateway_page")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.charactersgateway_page)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(30, 25, 30, 0)
        self.verticalLayout_3.setSpacing(20)
        self.header_layout = QtWidgets.QHBoxLayout()
        self.header_layout.setSpacing(20)
        self.header_layout.setObjectName("header_layout")
        self.search_bar_widget = ModernSearchBar(parent=self.charactersgateway_page)
        self.search_bar_widget.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.search_bar_widget.line_edit.setObjectName("lineEdit_search_character")
        self.search_bar_widget.search_btn.setObjectName("pushButton_search_character")
        self.lineEdit_search_character = self.search_bar_widget.line_edit
        self.pushButton_search_character = self.search_bar_widget.search_btn
        self.nsfw_layout = QtWidgets.QHBoxLayout()
        self.nsfw_layout.setSpacing(10)
        self.label_nsfw = QtWidgets.QLabel("NSFW")
        font_nsfw = QtGui.QFont()
        font_nsfw.setFamily("Inter Tight SemiBold")
        font_nsfw.setPointSize(10)
        font_nsfw.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.label_nsfw.setFont(font_nsfw)
        self.label_nsfw.setStyleSheet("color: #808080;")
        
        self.checkBox_enable_nsfw = AnimatedToggle(parent=self.charactersgateway_page)
        self.checkBox_enable_nsfw.setObjectName("checkBox_enable_nsfw")
        
        self.nsfw_layout.addWidget(self.label_nsfw)
        self.nsfw_layout.addWidget(self.checkBox_enable_nsfw)

        self.header_layout.addWidget(self.search_bar_widget)
        self.header_layout.addLayout(self.nsfw_layout)
        self.verticalLayout_3.addLayout(self.header_layout)

        self.tabWidget_characters_gateway = QtWidgets.QTabWidget(parent=self.charactersgateway_page)
        font_tabs = QtGui.QFont()
        font_tabs.setFamily("Inter Tight SemiBold")
        font_tabs.setPointSize(10)
        font_tabs.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.tabWidget_characters_gateway.setFont(font_tabs)

        self.tabWidget_characters_gateway.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: transparent;
                margin-top: 15px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: transparent;
                color: #757575;
                min-width: 120px;
                padding: 10px 0px;
                margin-right: 15px;
                border-bottom: 3px solid transparent;
                font-weight: 500;
            }
            QTabBar::tab:hover {
                color: #b0b0b0;
            }
            QTabBar::tab:selected {
                color: #ffffff;
                border-bottom: 3px solid #7a7a7a;
                font-weight: bold;
            }
        """)
        self.tabWidget_characters_gateway.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabWidget_characters_gateway.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.tabWidget_characters_gateway.setObjectName("tabWidget_characters_gateway")

        # --- 1. TAB SOUL GATEWAY
        self.tab_soul_gateway = QtWidgets.QWidget()
        self.tab_soul_gateway.setObjectName("tab_soul_gateway")
        self.layout_tab_soul = QtWidgets.QVBoxLayout(self.tab_soul_gateway)
        self.layout_tab_soul.setContentsMargins(0, 15, 0, 0)
        
        self.stackedWidget_soul_gateway = QtWidgets.QStackedWidget(parent=self.tab_soul_gateway)
        self.stackedWidget_soul_gateway.setObjectName("stackedWidget_soul_gateway")
        
        self.soul_gateway_page = QtWidgets.QWidget()
        self.soul_gateway_page.setObjectName("soul_gateway_page")
        self.layout_soul_page = QtWidgets.QVBoxLayout(self.soul_gateway_page)
        self.layout_soul_page.setContentsMargins(0, 0, 0, 0)
        
        self.scrollArea_soul_gateway = QtWidgets.QScrollArea(self.soul_gateway_page)
        self.scrollArea_soul_gateway.setWidgetResizable(True)
        self.scrollArea_soul_gateway.setObjectName("scrollArea_soul_gateway")
        self.scrollArea_soul_gateway.setStyleSheet("""
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
        
        self.scrollAreaWidgetContents_soul = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_soul.setGeometry(QtCore.QRect(0, 0, 1019, 495))
        self.scrollAreaWidgetContents_soul.setStyleSheet("background-color: transparent;")
        self.scrollAreaWidgetContents_soul.setObjectName("scrollAreaWidgetContents_soul")
        
        self.scrollArea_soul_gateway.setWidget(self.scrollAreaWidgetContents_soul)
        self.layout_soul_page.addWidget(self.scrollArea_soul_gateway)
        
        self.stackedWidget_soul_gateway.addWidget(self.soul_gateway_page)
        self.layout_tab_soul.addWidget(self.stackedWidget_soul_gateway)
        
        self.tabWidget_characters_gateway.addTab(self.tab_soul_gateway, "Soul Gateway")

        # --- 2. TAB CHARACTER AI
        self.tab_character_ai = QtWidgets.QWidget()
        self.tab_character_ai.setObjectName("tab_character_ai")
        self.layout_tab_cai = QtWidgets.QVBoxLayout(self.tab_character_ai)
        self.layout_tab_cai.setContentsMargins(0, 15, 0, 0)
        
        self.stackedWidget_character_ai = QtWidgets.QStackedWidget(parent=self.tab_character_ai)
        self.stackedWidget_character_ai.setObjectName("stackedWidget_character_ai")
        
        self.character_ai_page = QtWidgets.QWidget()
        self.character_ai_page.setObjectName("character_ai_page")
        self.layout_cai_page = QtWidgets.QVBoxLayout(self.character_ai_page)
        self.layout_cai_page.setContentsMargins(0, 0, 0, 0)
        
        self.scrollArea_character_ai_page = QtWidgets.QScrollArea(self.character_ai_page)
        self.scrollArea_character_ai_page.setWidgetResizable(True)
        self.scrollArea_character_ai_page.setObjectName("scrollArea_character_ai_page")
        self.scrollArea_character_ai_page.setStyleSheet("""
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
        
        self.scrollAreaWidgetContents_character_ai = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_ai.setGeometry(QtCore.QRect(0, 0, 1019, 495))
        self.scrollAreaWidgetContents_character_ai.setStyleSheet("background-color: transparent;")
        self.scrollAreaWidgetContents_character_ai.setObjectName("scrollAreaWidgetContents_character_ai")
        
        self.scrollArea_character_ai_page.setWidget(self.scrollAreaWidgetContents_character_ai)
        self.layout_cai_page.addWidget(self.scrollArea_character_ai_page)
        
        self.stackedWidget_character_ai.addWidget(self.character_ai_page)
        self.layout_tab_cai.addWidget(self.stackedWidget_character_ai)
        self.tabWidget_characters_gateway.addTab(self.tab_character_ai, "Character AI")

        # --- 3. TAB CHUB AI
        self.tab_character_cards = QtWidgets.QWidget()
        self.tab_character_cards.setObjectName("tab_character_cards")
        self.layout_tab_cards = QtWidgets.QVBoxLayout(self.tab_character_cards)
        self.layout_tab_cards.setContentsMargins(0, 15, 0, 0)
        
        self.stackedWidget_character_card_gateway = QtWidgets.QStackedWidget(parent=self.tab_character_cards)
        self.stackedWidget_character_card_gateway.setObjectName("stackedWidget_character_card_gateway")
        
        self.character_card_page = QtWidgets.QWidget()
        self.character_card_page.setObjectName("character_card_page")
        self.layout_card_page = QtWidgets.QVBoxLayout(self.character_card_page)
        self.layout_card_page.setContentsMargins(0, 0, 0, 0)
        
        self.scrollArea_character_card = QtWidgets.QScrollArea(self.character_card_page)
        self.scrollArea_character_card.setWidgetResizable(True)
        self.scrollArea_character_card.setObjectName("scrollArea_character_card")
        self.scrollArea_character_card.setStyleSheet("""
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
        
        self.scrollAreaWidgetContents_character_card = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_card.setGeometry(QtCore.QRect(0, 0, 1021, 497))
        self.scrollAreaWidgetContents_character_card.setStyleSheet("background-color: transparent;")
        self.scrollAreaWidgetContents_character_card.setObjectName("scrollAreaWidgetContents_character_card")
        
        self.scrollArea_character_card.setWidget(self.scrollAreaWidgetContents_character_card)
        self.layout_card_page.addWidget(self.scrollArea_character_card)
        
        self.stackedWidget_character_card_gateway.addWidget(self.character_card_page)
        self.layout_tab_cards.addWidget(self.stackedWidget_character_card_gateway)
        self.tabWidget_characters_gateway.addTab(self.tab_character_cards, "Chub AI / Cards")

        self.verticalLayout_3.addWidget(self.tabWidget_characters_gateway)
        self.stackedWidget.addWidget(self.charactersgateway_page)
        
        # ====================== Options Page ======================
        self.options_page = QtWidgets.QWidget()
        self.options_page.setObjectName("options_page")
        self.options_page.setStyleSheet("background: transparent;")

        self.gridLayout = QtWidgets.QGridLayout(self.options_page)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        
        self.options_container = QtWidgets.QWidget()
        self.layout_options = QtWidgets.QHBoxLayout(self.options_container)
        self.layout_options.setContentsMargins(0, 0, 0, 0)
        self.layout_options.setSpacing(0)

        self.options_menu = QtWidgets.QListWidget(self.options_page)
        self.options_menu.setObjectName("options_menu")
        self.options_menu.setFixedWidth(230)
        self.options_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.options_menu.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.options_menu.setStyleSheet("""
            QListWidget {
                background-color: rgba(15, 15, 18, 0.45);
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                padding-top: 25px;
                outline: none;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.5);
                font-family: 'Inter Tight SemiBold';
                font-size: 14px;
                padding: 14px 20px;
                border-radius: 8px;
                margin: 4px 15px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.15);
                color: #ffffff;
                border-left: 3px solid #ffffff;
                font-weight: bold;
            }
        """)
        
        tab_names = ["API & Providers", "System & UI", "Local LLM", "SoW Modules"]
        for name in tab_names:
            self.options_menu.addItem(QtWidgets.QListWidgetItem(name))
            
        self.layout_options.addWidget(self.options_menu)

        self.tabWidget_options = QtWidgets.QStackedWidget(self.options_page)
        self.tabWidget_options.setStyleSheet("background: transparent; border: none;")
        self.layout_options.addWidget(self.tabWidget_options)

        self.options_menu.currentRowChanged.connect(self.tabWidget_options.setCurrentIndex)

        font_title = QtGui.QFont("Inter Tight SemiBold", 15, QtGui.QFont.Weight.Bold)
        font_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        font_label = QtGui.QFont("Inter Tight Medium", 11)
        font_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        font_input = QtGui.QFont("Inter Tight Medium", 10)
        font_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)

        global_input_style = """
            QComboBox {
                background-color: rgba(15, 15, 18, 0.4);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 8px 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.05),
                                            stop:1 rgba(0, 0, 0, 0.05));
            }
            QComboBox:hover {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.08),
                                            stop:1 rgba(0, 0, 0, 0.08));
            }
            QComboBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.6);
                outline: none;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                image: url(:/sowInterface/arrowDown.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(30, 30, 35, 0.8);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                selection-background-color: rgba(255, 255, 255, 0.15);
                selection-color: #ffffff;
                padding: 5px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border: none;
                border-radius: 6px;
                background: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.1),
                                            stop:1 rgba(255, 255, 255, 0.05));
                color: #ffffff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 rgba(255, 255, 255, 0.15),
                                            stop:1 rgba(255, 255, 255, 0.05));
                color: #ffffff;
            }
            QLineEdit, QSpinBox {
                background-color: rgba(30, 30, 35, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 5px 15px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background-color: rgba(40, 40, 45, 0.6);
            }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 0px;
                height: 0px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                color: white;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QCheckBox {
                color: rgba(255, 255, 255, 0.9);
                spacing: 10px;
                font-size: 14px;
            }

            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }

            QCheckBox::indicator:hover {
                border: 1px solid rgba(255, 255, 255, 0.5);
                background-color: rgba(255, 255, 255, 0.05);
            }

            QCheckBox::indicator:checked {
                background-color: rgba(25, 25, 35, 0.9); 
                border: 1px solid rgba(180, 180, 180, 0.6);
                image: url(:/sowInterface/checked.png);
            }
        """

        def create_glass_card(title_text):
            card = QtWidgets.QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(22, 22, 26, 0.5);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                }}
                QLabel {{ color: rgba(255, 255, 255, 0.85); border: none; background: transparent; }}
                {global_input_style}
            """)
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(35)
            shadow.setColor(QColor(0, 0, 0, 100))
            shadow.setOffset(0, 8)
            card.setGraphicsEffect(shadow)
            
            layout = QtWidgets.QVBoxLayout(card)
            layout.setContentsMargins(30, 30, 30, 30)
            layout.setSpacing(20)
            
            title = QtWidgets.QLabel(title_text)
            title.setFont(font_title)
            title.setStyleSheet("color: #ffffff; font-weight: bold; padding-bottom: 5px;")
            title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            title.setContentsMargins(0, 0, 0, 0)
            title.setMinimumWidth(0)

            layout.addWidget(title)
            
            return card, layout

        def create_scroll_page():
            page = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            
            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("""
                QScrollArea { background: transparent; border: none; }
                QScrollBar:vertical { background-color: transparent; width: 6px; margin: 10px 0px; }
                QScrollBar::handle:vertical { background-color: rgba(255, 255, 255, 0.15); border-radius: 3px; min-height: 30px; }
                QScrollBar::handle:vertical:hover { background-color: rgba(255, 255, 255, 0.3); }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }
            """)
            
            content = QtWidgets.QWidget()
            content.setStyleSheet("background: transparent;")
            content_layout = QtWidgets.QVBoxLayout(content)
            content_layout.setContentsMargins(50, 40, 50, 50)
            content_layout.setSpacing(30)
            
            scroll.setWidget(content)
            layout.addWidget(scroll)
            return page, content_layout

        # =================================================================
        # API & Providers
        # =================================================================
        self.configuration_tab, conf_layout = create_scroll_page()
        self.configuration_tab.setObjectName("configuration_tab")

        self.conversation_provider_title = self.translations.get("conversation_provider_title", "Conversation Provider")
        self.api_configuration_title = self.translations.get("api_configuration_title", "API Configuration")
        self.user_profile_title = self.translations.get("user_profile_title", "User Profile")
        self.localization_title = self.translations.get("localization_title", "Localization & Translation")
        self.audio_devices_title = self.translations.get("audio_devices_title", "Audio Devices")
        self.hardware_spec_title = self.translations.get("hardware_spec_title", "Hardware Specifications")
        self.llm_settings_title = self.translations.get("llm_settings_title", "LLM Settings")
        self.memory_and_offloading_title = self.translations.get("memory_and_offloading_title", "Memory & Offloading")
        self.generation_params_title = self.translations.get("generation_params_title", "Generation Parameters")
        self.global_editors_title = self.translations.get("global_editors_title", "Global Editors")
        self.visualizations_title = self.translations.get("visualizations_title", "Visualizations (Live2D / VRM)")
        self.sub_modules_title = self.translations.get("sub_modules_title", "Sub-Modules")
        
        self.gpu_layers_text = self.translations.get("gpu_layers_text", "GPU Layers")
        self.context_size_text = self.translations.get("context_size_text", "Context Size")
        self.temperature_text = self.translations.get("temperature_label", "Temperature")
        self.top_p_text = self.translations.get("top_p_label", "Top P")
        self.rep_penalty_text = self.translations.get("repeat_penalty_label", "Repeat Penalty")
        self.max_tokens_text = self.translations.get("max_tokens_label", "Max Tokens")

        card_method, l_method = create_glass_card(self.conversation_provider_title)
        form_method = QtWidgets.QFormLayout()
        form_method.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_method.setVerticalSpacing(20)
        form_method.setHorizontalSpacing(30)
        
        self.conversation_method_options_label = QtWidgets.QLabel("Conversation Method")
        self.conversation_method_options_label.setFont(font_label)
        self.comboBox_conversation_method = QtWidgets.QComboBox()
        self.comboBox_conversation_method.setFont(font_input)
        self.comboBox_conversation_method.setFixedHeight(40)
        self.comboBox_conversation_method.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_conversation_method.addItems(["Character AI", "Mistral AI", "Open AI", "OpenRouter"])
        self.comboBox_conversation_method.setObjectName("comboBox_conversation_method")
        
        form_method.addRow(self.conversation_method_options_label, self.comboBox_conversation_method)
        l_method.addLayout(form_method)
        conf_layout.addWidget(card_method)

        self.card_api, l_api = create_glass_card(self.api_configuration_title)
        form_api = QtWidgets.QFormLayout()
        form_api.setVerticalSpacing(20)
        form_api.setHorizontalSpacing(30)
        
        self.conversation_method_token_title_label = QtWidgets.QLabel("API Token")
        self.conversation_method_token_title_label.setFont(font_label)
        self.lineEdit_api_token_options = QtWidgets.QLineEdit()
        self.lineEdit_api_token_options.setFont(font_input)
        self.lineEdit_api_token_options.setFixedHeight(40)
        self.lineEdit_api_token_options.setObjectName("lineEdit_api_token_options")
        form_api.addRow(self.conversation_method_token_title_label, self.lineEdit_api_token_options)

        self.label_base_url = QtWidgets.QLabel("Base URL")
        self.label_base_url.setFont(font_label)
        self.lineEdit_base_url_options = QtWidgets.QLineEdit()
        self.lineEdit_base_url_options.setFont(font_input)
        self.lineEdit_base_url_options.setFixedHeight(40)
        self.lineEdit_base_url_options.setPlaceholderText("Custom Endpoint URL (Optional)")
        self.lineEdit_base_url_options.setObjectName("lineEdit_base_url_options")
        form_api.addRow(self.label_base_url, self.lineEdit_base_url_options)

        self.label_openai_model = QtWidgets.QLabel("OpenAI Model")
        self.label_openai_model.setFont(font_label)
        
        self.lineEdit_openai_model = QtWidgets.QLineEdit()
        self.lineEdit_openai_model.setFont(font_input)
        self.lineEdit_openai_model.setFixedHeight(40)
        self.lineEdit_openai_model.setPlaceholderText("gpt-5.4 or something else")
        self.lineEdit_openai_model.setObjectName("lineEdit_openai_model")
        form_api.addRow(self.label_openai_model, self.lineEdit_openai_model)

        self.label_mistral_model = QtWidgets.QLabel("Mistral Model")
        self.label_mistral_model.setFont(font_label)
        self.lineEdit_mistral_model = QtWidgets.QLineEdit()
        self.lineEdit_mistral_model.setFont(font_input)
        self.lineEdit_mistral_model.setFixedHeight(40)
        self.lineEdit_mistral_model.setObjectName("lineEdit_mistral_model")
        form_api.addRow(self.label_mistral_model, self.lineEdit_mistral_model)

        self.openrouter_models_options_label = QtWidgets.QLabel("Model")
        self.openrouter_models_options_label.setFont(font_label)
        
        self.openrouter_layout_widget = QtWidgets.QWidget()
        openrouter_layout = QtWidgets.QHBoxLayout(self.openrouter_layout_widget)
        openrouter_layout.setContentsMargins(0,0,0,0)
        openrouter_layout.setSpacing(15)
        
        self.lineEdit_search_openrouter_models = QtWidgets.QLineEdit()
        self.lineEdit_search_openrouter_models.setFont(font_input)
        self.lineEdit_search_openrouter_models.setFixedHeight(40)
        self.lineEdit_search_openrouter_models.setPlaceholderText("Search models...")
        self.lineEdit_search_openrouter_models.setObjectName("lineEdit_search_openrouter_models")
        
        self.comboBox_openrouter_models = QtWidgets.QComboBox()
        self.comboBox_openrouter_models.setFont(font_input)
        self.comboBox_openrouter_models.setFixedHeight(40)
        self.comboBox_openrouter_models.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_openrouter_models.setObjectName("comboBox_openrouter_models")
        
        openrouter_layout.addWidget(self.lineEdit_search_openrouter_models, 1)
        openrouter_layout.addWidget(self.comboBox_openrouter_models, 2)
        
        form_api.addRow(self.openrouter_models_options_label, self.openrouter_layout_widget)
        l_api.addLayout(form_api)
        conf_layout.addWidget(self.card_api)
        
        conf_layout.addStretch()
        self.tabWidget_options.addWidget(self.configuration_tab)

        # =================================================================
        # System & UI
        # =================================================================
        self.system_tab, sys_layout = create_scroll_page()
        self.system_tab.setObjectName("system_tab")

        card_lang, l_lang = create_glass_card(self.localization_title)
        form_lang = QtWidgets.QFormLayout()
        form_lang.setVerticalSpacing(20)
        form_lang.setHorizontalSpacing(30)

        self.program_language_label = QtWidgets.QLabel("App Language")
        self.program_language_label.setFont(font_label)
        self.comboBox_program_language = QtWidgets.QComboBox()
        self.comboBox_program_language.setFont(font_input)
        self.comboBox_program_language.setFixedHeight(40)
        self.comboBox_program_language.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_program_language.addItems(["English", "Russian"])
        self.comboBox_program_language.setObjectName("comboBox_program_language")
        form_lang.addRow(self.program_language_label, self.comboBox_program_language)

        self.choose_translator_label = QtWidgets.QLabel("Translator")
        self.choose_translator_label.setFont(font_label)
        self.comboBox_translator = QtWidgets.QComboBox()
        self.comboBox_translator.setFont(font_input)
        self.comboBox_translator.setFixedHeight(40)
        self.comboBox_translator.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_translator.addItems(["None", "Google", "Yandex"])
        self.comboBox_translator.setObjectName("comboBox_translator")
        form_lang.addRow(self.choose_translator_label, self.comboBox_translator)

        self.mode_translator_label = QtWidgets.QLabel("Translation Mode")
        self.mode_translator_label.setFont(font_label)
        self.comboBox_mode_translator = QtWidgets.QComboBox()
        self.comboBox_mode_translator.setFont(font_input)
        self.comboBox_mode_translator.setFixedHeight(40)
        self.comboBox_mode_translator.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_mode_translator.addItems(["Both", "User Only", "Character Only"])
        self.comboBox_mode_translator.setObjectName("comboBox_mode_translator")
        form_lang.addRow(self.mode_translator_label, self.comboBox_mode_translator)

        self.target_language_translator_label = QtWidgets.QLabel("Target Language:")
        self.target_language_translator_label.setFont(font_label)
        self.comboBox_target_language_translator = QtWidgets.QComboBox()
        self.comboBox_target_language_translator.setFont(font_input)
        self.comboBox_target_language_translator.setFixedHeight(40)
        self.comboBox_target_language_translator.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_target_language_translator.addItem("Russian")
        self.comboBox_target_language_translator.setObjectName("comboBox_target_language_translator")
        form_lang.addRow(self.target_language_translator_label, self.comboBox_target_language_translator)

        l_lang.addLayout(form_lang)
        sys_layout.addWidget(card_lang)

        card_audio, l_audio = create_glass_card(self.audio_devices_title)
        form_audio = QtWidgets.QFormLayout()
        form_audio.setVerticalSpacing(20)
        form_audio.setHorizontalSpacing(30)

        self.input_device_label = QtWidgets.QLabel("Microphone")
        self.input_device_label.setFont(font_label)
        self.comboBox_input_devices = QtWidgets.QComboBox()
        self.comboBox_input_devices.setFont(font_input)
        self.comboBox_input_devices.setFixedHeight(40)
        self.comboBox_input_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_input_devices.setObjectName("comboBox_input_devices")
        form_audio.addRow(self.input_device_label, self.comboBox_input_devices)

        self.output_device_label = QtWidgets.QLabel("Speakers")
        self.output_device_label.setFont(font_label)
        self.comboBox_output_devices = QtWidgets.QComboBox()
        self.comboBox_output_devices.setFont(font_input)
        self.comboBox_output_devices.setFixedHeight(40)
        self.comboBox_output_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_output_devices.setObjectName("comboBox_output_devices")
        form_audio.addRow(self.output_device_label, self.comboBox_output_devices)

        l_audio.addLayout(form_audio)
        sys_layout.addWidget(card_audio)

        card_hw, l_hw = create_glass_card(self.hardware_spec_title)
        hw_layout = QtWidgets.QHBoxLayout()
        
        ram_box = QtWidgets.QHBoxLayout()
        self.ram_label_icon = QtWidgets.QLabel()
        self.ram_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/memory.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.ram_label = QtWidgets.QLabel("0 GB RAM")
        self.ram_label.setFont(font_label)
        ram_box.addWidget(self.ram_label_icon)
        ram_box.addWidget(self.ram_label)
        ram_box.addStretch()
        
        gpu_box = QtWidgets.QHBoxLayout()
        self.gpu_label_icon = QtWidgets.QLabel()
        self.gpu_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/gpu.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.gpu_label = QtWidgets.QLabel("No GPU")
        self.gpu_label.setFont(font_label)
        gpu_box.addWidget(self.gpu_label_icon)
        gpu_box.addWidget(self.gpu_label)
        gpu_box.addStretch()

        hw_layout.addLayout(ram_box)
        hw_layout.addLayout(gpu_box)
        l_hw.addLayout(hw_layout)
        sys_layout.addWidget(card_hw)

        sys_layout.addStretch()
        self.tabWidget_options.addWidget(self.system_tab)

        # =================================================================
        # LLM Settings
        # =================================================================
        self.llm_tab, llm_layout = create_scroll_page()
        self.llm_tab.setObjectName("llm_tab")

        card_llm_base, l_llm_base = create_glass_card(self.llm_settings_title)
        form_llm_base = QtWidgets.QFormLayout()
        form_llm_base.setVerticalSpacing(20)
        form_llm_base.setHorizontalSpacing(30)

        self.llm_options_label = QtWidgets.QLabel("Server Endpoint")
        self.llm_options_label.setFont(font_label)
        self.lineEdit_server = QtWidgets.QLineEdit()
        self.lineEdit_server.setFont(font_input)
        self.lineEdit_server.setFixedHeight(40)
        self.lineEdit_server.setReadOnly(True)
        self.lineEdit_server.setObjectName("lineEdit_server")
        form_llm_base.addRow(self.llm_options_label, self.lineEdit_server)

        self.choose_llm_device_label = QtWidgets.QLabel("Compute Device")
        self.choose_llm_device_label.setFont(font_label)
        self.comboBox_llm_devices = QtWidgets.QComboBox()
        self.comboBox_llm_devices.setFont(font_input)
        self.comboBox_llm_devices.setFixedHeight(40)
        self.comboBox_llm_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_llm_devices.addItems(["CPU", "GPU"])
        self.comboBox_llm_devices.setObjectName("comboBox_llm_devices")
        form_llm_base.addRow(self.choose_llm_device_label, self.comboBox_llm_devices)

        self.choose_llm_gpu_device_label = QtWidgets.QLabel("GPU Backend")
        self.choose_llm_gpu_device_label.setFont(font_label)
        self.comboBox_llm_gpu_devices = QtWidgets.QComboBox()
        self.comboBox_llm_gpu_devices.setFont(font_input)
        self.comboBox_llm_gpu_devices.setFixedHeight(40)
        self.comboBox_llm_gpu_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_llm_gpu_devices.addItems(["Vulkan", "CUDA"])
        self.comboBox_llm_gpu_devices.setObjectName("comboBox_llm_gpu_devices")
        form_llm_base.addRow(self.choose_llm_gpu_device_label, self.comboBox_llm_gpu_devices)

        check_box_layout = QtWidgets.QHBoxLayout()
        check_box_layout.setSpacing(25)
        self.checkBox_enable_mlock = QtWidgets.QCheckBox("MLock")
        self.checkBox_enable_mlock.setFont(font_input)
        self.checkBox_enable_mlock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_mlock.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_mlock.setObjectName("checkBox_enable_mlock")

        self.checkBox_enable_flash_attention = QtWidgets.QCheckBox("Flash Attention")
        self.checkBox_enable_flash_attention.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_flash_attention.setFont(font_input)
        self.checkBox_enable_flash_attention.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_flash_attention.setObjectName("checkBox_enable_flash_attention")
        
        check_box_layout.addWidget(self.checkBox_enable_mlock)
        check_box_layout.addWidget(self.checkBox_enable_flash_attention)
        check_box_layout.addStretch()
        form_llm_base.addRow("", check_box_layout)

        l_llm_base.addLayout(form_llm_base)
        llm_layout.addWidget(card_llm_base)

        def create_slider_row(label_text, slider_obj, line_edit_obj, min_val, max_val, step=1):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(20)
            
            lbl = QtWidgets.QLabel(label_text)
            lbl.setFont(font_label)
            lbl.setFixedWidth(120)
            
            slider_obj.setOrientation(QtCore.Qt.Orientation.Horizontal)
            slider_obj.setMinimum(min_val)
            slider_obj.setMaximum(max_val)
            slider_obj.setSingleStep(step)
            slider_obj.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            slider_obj.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            slider_obj.setStyleSheet("""
                QToolTip { 
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }
                QSlider::groove:horizontal { background: rgba(0,0,0,0.5); height: 6px; border-radius: 3px; }
                QSlider::sub-page:horizontal { background: rgba(255, 255, 255, 0.6); border-radius: 3px; }
                QSlider::handle:horizontal { background: white; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; border: 1px solid rgba(0,0,0,0.2); }
                QSlider::handle:horizontal:hover { background: #ffffff; transform: scale(1.1); box-shadow: 0 0 10px rgba(255,255,255,0.5); }
            """)
            
            line_edit_obj.setFont(font_input)
            line_edit_obj.setFixedSize(65, 35)
            line_edit_obj.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            row.addWidget(lbl)
            row.addWidget(slider_obj)
            row.addWidget(line_edit_obj)
            return row

        card_llm_mem, l_llm_mem = create_glass_card(self.memory_and_offloading_title)
        self.gpu_layers_horizontalSlider = QtWidgets.QSlider()
        self.gpu_layers_horizontalSlider.setObjectName("gpu_layers_horizontalSlider")
        self.lineEdit_gpuLayers = QtWidgets.QLineEdit()
        self.lineEdit_gpuLayers.setObjectName("lineEdit_gpuLayers")
        l_llm_mem.addLayout(create_slider_row(self.gpu_layers_text, self.gpu_layers_horizontalSlider, self.lineEdit_gpuLayers, 0, 100))

        self.context_size_horizontalSlider = QtWidgets.QSlider()
        self.context_size_horizontalSlider.setObjectName("context_size_horizontalSlider")
        self.lineEdit_contextSize = QtWidgets.QLineEdit()
        self.lineEdit_contextSize.setObjectName("lineEdit_contextSize")
        l_llm_mem.addLayout(create_slider_row(self.context_size_text, self.context_size_horizontalSlider, self.lineEdit_contextSize, 512, 32768, 512))
        llm_layout.addWidget(card_llm_mem)

        card_llm_gen, l_llm_gen = create_glass_card(self.generation_params_title)
        self.temperature_horizontalSlider = QtWidgets.QSlider()
        self.temperature_horizontalSlider.setObjectName("temperature_horizontalSlider")
        self.lineEdit_temperature = QtWidgets.QLineEdit()
        self.lineEdit_temperature.setObjectName("lineEdit_temperature")
        l_llm_gen.addLayout(create_slider_row(self.temperature_text, self.temperature_horizontalSlider, self.lineEdit_temperature, 0, 20))

        self.top_p_horizontalSlider = QtWidgets.QSlider()
        self.top_p_horizontalSlider.setObjectName("top_p_horizontalSlider")
        self.lineEdit_topP = QtWidgets.QLineEdit()
        self.lineEdit_topP.setObjectName("lineEdit_topP")
        l_llm_gen.addLayout(create_slider_row(self.top_p_text, self.top_p_horizontalSlider, self.lineEdit_topP, 0, 10))

        self.repeat_penalty_horizontalSlider = QtWidgets.QSlider()
        self.repeat_penalty_horizontalSlider.setObjectName("repeat_penalty_horizontalSlider")
        self.lineEdit_repeatPenalty = QtWidgets.QLineEdit()
        self.lineEdit_repeatPenalty.setObjectName("lineEdit_repeatPenalty")
        l_llm_gen.addLayout(create_slider_row(self.rep_penalty_text, self.repeat_penalty_horizontalSlider, self.lineEdit_repeatPenalty, 10, 20))

        self.max_tokens_horizontalSlider = QtWidgets.QSlider()
        self.max_tokens_horizontalSlider.setObjectName("max_tokens_horizontalSlider")
        self.lineEdit_maxTokens = QtWidgets.QLineEdit()
        self.lineEdit_maxTokens.setObjectName("lineEdit_maxTokens")
        l_llm_gen.addLayout(create_slider_row(self.max_tokens_text, self.max_tokens_horizontalSlider, self.lineEdit_maxTokens, 16, 4096, 16))
        llm_layout.addWidget(card_llm_gen)

        llm_layout.addStretch()
        self.tabWidget_options.addWidget(self.llm_tab)

        # =================================================================
        # SoW Modules
        # =================================================================
        self.sow_system_tab, sow_layout = create_scroll_page()
        self.sow_system_tab.setObjectName("sow_system_tab")

        card_sow_main, l_sow_main = create_glass_card("Soul of Waifu System")
        self.checkBox_enable_sow_system = QtWidgets.QCheckBox("Enable Soul of Waifu System")
        f = QtGui.QFont("Inter Tight SemiBold", 12, QtGui.QFont.Weight.Bold)
        self.checkBox_enable_sow_system.setFont(f)
        self.checkBox_enable_sow_system.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
            QCheckBox { 
                color: #ffffff; 
                spacing: 10px;
            }
            QCheckBox::indicator { 
                width: 26px; 
                height: 26px; 
                border-radius: 13px; 
                background-color: rgba(0, 0, 0, 0.5); 
                border: 2px solid rgba(255, 255, 255, 0.4); 
            }
            QCheckBox::indicator:hover { 
                border: 2px solid rgba(255, 255, 255, 0.8); 
                background-color: rgba(255, 255, 255, 0.1); 
            }
            QCheckBox::indicator:checked { 
                background-color: rgba(20, 20, 30, 0.95); 
                border: 2px solid rgba(180, 180, 180, 0.8); 
                image: url(:/sowInterface/checked.png); 
            }
        """)
        self.checkBox_enable_sow_system.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_sow_system.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_sow_system.setObjectName("checkBox_enable_sow_system")
        l_sow_main.addWidget(self.checkBox_enable_sow_system)
        sow_layout.addWidget(card_sow_main)

        self.card_visuals, l_visuals = create_glass_card(self.visualizations_title)
        form_vis = QtWidgets.QFormLayout()
        form_vis.setVerticalSpacing(20)
        form_vis.setHorizontalSpacing(30)

        self.label_live2d_mode = QtWidgets.QLabel("Render Mode")
        self.label_live2d_mode.setFont(font_label)
        self.comboBox_live2d_mode = QtWidgets.QComboBox()
        self.comboBox_live2d_mode.setFont(font_input)
        self.comboBox_live2d_mode.setFixedHeight(40)
        self.comboBox_live2d_mode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_live2d_mode.addItems(["With GUI", "Without GUI"])
        self.comboBox_live2d_mode.setObjectName("comboBox_live2d_mode")
        form_vis.addRow(self.label_live2d_mode, self.comboBox_live2d_mode)

        self.label_model_fps = QtWidgets.QLabel("Target FPS")
        self.label_model_fps.setFont(font_label)
        self.comboBox_model_fps = QtWidgets.QComboBox()
        self.comboBox_model_fps.setFont(font_input)
        self.comboBox_model_fps.setFixedHeight(40)
        self.comboBox_model_fps.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_model_fps.addItems(["30 FPS", "60 FPS", "120 FPS"])
        self.comboBox_model_fps.setObjectName("comboBox_model_fps")
        form_vis.addRow(self.label_model_fps, self.comboBox_model_fps)

        self.label_model_background = QtWidgets.QLabel("Background Type")
        self.label_model_background.setFont(font_label)
        self.comboBox_model_background = QtWidgets.QComboBox()
        self.comboBox_model_background.setFont(font_input)
        self.comboBox_model_background.setFixedHeight(40)
        self.comboBox_model_background.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_model_background.addItems(["Solid Color", "Image"])
        self.comboBox_model_background.setObjectName("comboBox_model_background")
        form_vis.addRow(self.label_model_background, self.comboBox_model_background)

        bg_container = QtWidgets.QWidget()
        bg_dyn_layout = QtWidgets.QGridLayout(bg_container)
        bg_dyn_layout.setContentsMargins(0, 0, 0, 0)
        bg_dyn_layout.setSpacing(10)
        
        self.label_bg_color = QtWidgets.QLabel("Color")
        self.label_bg_color.setFont(font_label)
        
        self.comboBox_model_bg_color = QtWidgets.QComboBox()
        self.comboBox_model_bg_color.setFont(font_input)
        self.comboBox_model_bg_color.setFixedHeight(40)
        self.comboBox_model_bg_color.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_model_bg_color.addItems(["Black", "Deep Blue", "Vinous", "Dark Green", "Soft Purple", "Warm Coal Grey"])
        self.comboBox_model_bg_color.setObjectName("comboBox_model_bg_color")
        
        self.label_bg_image = QtWidgets.QLabel("Image")
        self.label_bg_image.setFont(font_label)
        
        self.comboBox_model_bg_image = QtWidgets.QComboBox()
        self.comboBox_model_bg_image.setFont(font_input)
        self.comboBox_model_bg_image.setFixedHeight(40)
        self.comboBox_model_bg_image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_model_bg_image.setObjectName("comboBox_model_bg_image")
        
        self.pushButton_reload_bg_image = QtWidgets.QPushButton()
        self.pushButton_reload_bg_image.setFixedSize(40, 40)
        self.pushButton_reload_bg_image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_bg_image.setIcon(QtGui.QIcon("app/gui/icons/reload.png"))
        self.pushButton_reload_bg_image.setObjectName("pushButton_reload_bg_image")
        
        bg_dyn_layout.addWidget(self.label_bg_color, 0, 0)
        bg_dyn_layout.addWidget(self.comboBox_model_bg_color, 0, 1)
        bg_dyn_layout.addWidget(self.label_bg_image, 0, 2)
        bg_dyn_layout.addWidget(self.comboBox_model_bg_image, 0, 3)
        bg_dyn_layout.addWidget(self.pushButton_reload_bg_image, 0, 4)
        
        bg_dyn_layout.setColumnStretch(1, 1)
        bg_dyn_layout.setColumnStretch(3, 1)

        form_vis.addRow("", bg_container)
        l_visuals.addLayout(form_vis)
        sow_layout.addWidget(self.card_visuals)

        self.card_modules, l_modules = create_glass_card(self.sub_modules_title)
        
        layout_modules_main = QtWidgets.QVBoxLayout()
        layout_modules_main.setSpacing(20)

        amb_layout = QtWidgets.QHBoxLayout()
        amb_layout.setSpacing(15)
        
        self.checkBox_enable_ambient = QtWidgets.QCheckBox("Ambient Audio")
        self.checkBox_enable_ambient.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_ambient.setFont(font_input)
        self.checkBox_enable_ambient.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_ambient.setObjectName("checkBox_enable_ambient")
        
        self.comboBox_ambient_mode = QtWidgets.QComboBox()
        self.comboBox_ambient_mode.setFont(font_input)
        self.comboBox_ambient_mode.setFixedHeight(40)
        self.comboBox_ambient_mode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_ambient_mode.setObjectName("comboBox_ambient_mode")
        
        self.pushButton_reload_ambient = QtWidgets.QPushButton()
        self.pushButton_reload_ambient.setFixedSize(40, 40)
        self.pushButton_reload_ambient.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_ambient.setIcon(QtGui.QIcon("app/gui/icons/reload.png"))
        self.pushButton_reload_ambient.setObjectName("pushButton_reload_ambient")
        
        amb_layout.addWidget(self.checkBox_enable_ambient)
        amb_layout.addWidget(self.comboBox_ambient_mode, 1)
        amb_layout.addWidget(self.pushButton_reload_ambient)
        layout_modules_main.addLayout(amb_layout)

        mem_layout = QtWidgets.QVBoxLayout()
        mem_layout.setSpacing(15)
        
        self.checkBox_enable_memory = QtWidgets.QCheckBox("Smart Memory (Vector DB)")
        self.checkBox_enable_memory.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_memory.setFont(font_input)
        self.checkBox_enable_memory.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_memory.setObjectName("checkBox_enable_memory")
        
        sum_row = QtWidgets.QHBoxLayout()
        sum_row.setSpacing(15)      
        self.checkBox_enable_summary = QtWidgets.QCheckBox("Auto-Summarization")
        self.checkBox_enable_summary.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_summary.setFont(font_input)
        self.checkBox_enable_summary.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_summary.setObjectName("checkBox_enable_summary")        
        self.label_summary_interval = QtWidgets.QLabel("Interval:")
        self.label_summary_interval.setFont(font_input)        
        self.spinBox_summary_interval = QtWidgets.QSpinBox()
        self.spinBox_summary_interval.setFont(font_input)
        self.spinBox_summary_interval.setFixedHeight(35)
        self.spinBox_summary_interval.setFixedWidth(80)
        self.spinBox_summary_interval.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.spinBox_summary_interval.setMinimum(5)
        self.spinBox_summary_interval.setObjectName("spinBox_summary_interval")        
        sum_row.addWidget(self.checkBox_enable_summary)
        sum_row.addWidget(self.label_summary_interval)
        sum_row.addWidget(self.spinBox_summary_interval)
        sum_row.addStretch()
        mem_layout.addWidget(self.checkBox_enable_memory)
        mem_layout.addLayout(sum_row)
        layout_modules_main.addLayout(mem_layout)
        l_modules.addLayout(layout_modules_main)
        sow_layout.addWidget(self.card_modules)
        sow_layout.addStretch()
        self.tabWidget_options.addWidget(self.sow_system_tab)
        self.options_menu.setCurrentRow(0)
        self.gridLayout.addWidget(self.options_container, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.options_page)

        self.chat_page = QtWidgets.QWidget()
        self.chat_page.setObjectName("chat_page")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.chat_page)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 5)
        self.verticalLayout_6.setSpacing(0)
        self.top = QtWidgets.QFrame(parent=self.chat_page)
        self.top.setMinimumSize(QtCore.QSize(0, 60))
        self.top.setMaximumSize(QtCore.QSize(16777215, 60))
        self.top.setStyleSheet("#top {\n"
"    background-color: rgba(20, 20, 20, 180);\n"
"}\n"
"\n"
"#user_name { \n"
"    color: rgb(220, 220, 220);\n"
"    font: 600 12pt \"Segoe UI\";\n"
"    background: transparent;\n"
"}\n"
"\n"
"#user_image {\n"
"    border: 1px solid rgba(255, 255, 255, 80);\n"
"    background-color: rgba(255, 255, 255, 40);\n"
"    border-radius: 20px;\n"
"}")
        self.top.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.top.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.top.setObjectName("top")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.top)
        self.horizontalLayout_2.setContentsMargins(20, 9, 20, 9)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.character_avatar_label = QtWidgets.QLabel(parent=self.top)
        self.character_avatar_label.setMinimumSize(QtCore.QSize(40, 40))
        self.character_avatar_label.setMaximumSize(QtCore.QSize(40, 40))
        self.character_avatar_label.setStyleSheet("background: transparent;\n"
"border-radius: 30px;")
        self.character_avatar_label.setText("")
        self.character_avatar_label.setScaledContents(True)
        self.character_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.character_avatar_label.setObjectName("character_avatar_label")
        self.horizontalLayout_2.addWidget(self.character_avatar_label)
        self.user_information_frame = QtWidgets.QFrame(parent=self.top)
        self.user_information_frame.setMinimumSize(QtCore.QSize(0, 45))
        self.user_information_frame.setStyleSheet("background-color: transparent;")
        self.user_information_frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.user_information_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.user_information_frame.setObjectName("user_information_frame")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.user_information_frame)
        self.verticalLayout_4.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout_4.setSpacing(3)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.character_name_chat = QtWidgets.QLabel(parent=self.user_information_frame)
        self.character_name_chat.setMinimumSize(QtCore.QSize(0, 22))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_name_chat.setFont(font)
        self.character_name_chat.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_name_chat.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.character_name_chat.setObjectName("character_name_chat")
        self.verticalLayout_4.addWidget(self.character_name_chat)
        self.character_description_chat = QtWidgets.QLabel(parent=self.user_information_frame)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_description_chat.setFont(font)
        self.character_description_chat.setStyleSheet("background: transparent;\n"
"color: rgb(216, 216, 216)")
        self.character_description_chat.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.character_description_chat.setObjectName("character_description_chat")
        self.verticalLayout_4.addWidget(self.character_description_chat)
        self.horizontalLayout_2.addWidget(self.user_information_frame)
        spacerItem24 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem24)
        
        self.pushButton_change_chat_background = PushButton("app/gui/icons/background_icon.png")
        self.pushButton_change_chat_background.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_change_chat_background.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_change_chat_background.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_change_chat_background.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_change_chat_background.setStyleSheet("QPushButton {\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #2C2C2C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #424242;\n"
"}")
        self.pushButton_change_chat_background.setText("")
        icon_chat_background = QtGui.QIcon()
        icon_chat_background.addPixmap(QtGui.QPixmap("app/gui/icons/background_icon.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_change_chat_background.setIcon(icon_chat_background)
        self.pushButton_change_chat_background.setIconSize(QtCore.QSize(18, 18))
        self.pushButton_change_chat_background.setObjectName("pushButton_change_chat_background")
        self.horizontalLayout_2.addWidget(self.pushButton_change_chat_background)
        self.pushButton_author_notes = PushButton("app/gui/icons/author_notes.png")
        self.pushButton_author_notes.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_author_notes.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_author_notes.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_author_notes.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_author_notes.setStyleSheet("QPushButton {\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #2C2C2C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #424242;\n"
"}")
        self.pushButton_author_notes.setText("")
        icon_author_notes = QtGui.QIcon()
        icon_author_notes.addPixmap(QtGui.QPixmap("app/gui/icons/author_notes.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_author_notes.setIcon(icon_author_notes)
        self.pushButton_author_notes.setIconSize(QtCore.QSize(18, 18))
        self.pushButton_author_notes.setObjectName("pushButton_author_notes")
        self.pushButton_author_notes.hide()
        self.horizontalLayout_2.addWidget(self.pushButton_author_notes)
        self.pushButton_summary = PushButton("app/gui/icons/summary.png")
        self.pushButton_summary.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_summary.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_summary.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_summary.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_summary.setStyleSheet("QPushButton {\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #2C2C2C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #424242;\n"
"}")
        self.pushButton_summary.setText("")
        icon_summary = QtGui.QIcon()
        icon_summary.addPixmap(QtGui.QPixmap("app/gui/icons/summary.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_summary.setIcon(icon_summary)
        self.pushButton_summary.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_summary.setObjectName("pushButton_summary")
        self.pushButton_summary.hide()
        self.horizontalLayout_2.addWidget(self.pushButton_summary)
        self.pushButton_more = PushButton("app/gui/icons/more.png")
        self.pushButton_more.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_more.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_more.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_more.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_more.setStyleSheet("QPushButton {\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: #2C2C2C;\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: #424242;\n"
"}")
        self.pushButton_more.setText("")
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap("app/gui/icons/more.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_more.setIcon(icon9)
        self.pushButton_more.setObjectName("pushButton_more")
        self.horizontalLayout_2.addWidget(self.pushButton_more)
        self.verticalLayout_6.addWidget(self.top)
        self.frame_separator_chat = QtWidgets.QFrame(parent=self.chat_page)
        self.frame_separator_chat.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_separator_chat.setStyleSheet("background-color: transparent;")
        self.frame_separator_chat.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_separator_chat.setObjectName("frame_separator_chat")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.frame_separator_chat)
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.separator_chat = QtWidgets.QFrame(parent=self.frame_separator_chat)
        self.separator_chat.setMaximumSize(QtCore.QSize(1077, 1))
        self.separator_chat.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
            }
        """)
        self.separator_chat.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_chat.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_chat.setObjectName("separator_chat")
        self.horizontalLayout_10.addWidget(self.separator_chat)
        self.verticalLayout_6.addWidget(self.frame_separator_chat)
        self.scrollArea_chat = QtWidgets.QScrollArea(parent=self.chat_page)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_chat.sizePolicy().hasHeightForWidth())
        self.scrollArea_chat.setSizePolicy(sizePolicy)
        self.scrollArea_chat.setMinimumSize(QtCore.QSize(0, 0))
        self.scrollArea_chat.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.scrollArea_chat.setStyleSheet("""
                QScrollArea {
                    background-color: rgb(27,27,27);
                    border: none;
                    padding-left: 5px;
                    padding-right: 5px;
                    padding-bottom: 5px;
                    margin-top: 5px;
                    border-radius: 10px;
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
        self.scrollArea_chat.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scrollAreaWidgetContents_messages = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_messages.setGeometry(QtCore.QRect(0, 0, 1057, 591))
        self.scrollAreaWidgetContents_messages.setObjectName("scrollAreaWidgetContents_messages")
        self.scrollArea_chat.setWidget(self.scrollAreaWidgetContents_messages)
        self.verticalLayout_6.addWidget(self.scrollArea_chat)
        
        self.frame_send_message_full = QtWidgets.QFrame(parent=self.chat_page)
        self.frame_send_message_full.setMinimumSize(QtCore.QSize(0, 40))
        self.frame_send_message_full.setMaximumSize(QtCore.QSize(16777215, 40))
        self.frame_send_message_full.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_send_message_full.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_send_message_full.setStyleSheet("background-color: transparent; border: none;")
        self.frame_send_message_full.setObjectName("frame_send_message_full")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.frame_send_message_full)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 5)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        spacerItem27 = QtWidgets.QSpacerItem(200, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem27)
        self.frame_send_message = QtWidgets.QFrame(parent=self.frame_send_message_full)
        self.frame_send_message.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_send_message.sizePolicy().hasHeightForWidth())
        self.frame_send_message.setSizePolicy(sizePolicy)
        self.frame_send_message.setMinimumSize(QtCore.QSize(0, 40))
        self.frame_send_message.setMaximumSize(QtCore.QSize(681, 40))
        self.frame_send_message.setBaseSize(QtCore.QSize(0, 0))
        
        self.frame_send_message.setStyleSheet("""
            QFrame#frame_send_message { 
                background-color: rgba(20, 20, 22, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 19px;
            }
            QTextEdit {
                background-color: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.9);
                padding-top: 6px;
                padding-left: 10px;
                padding-right: 10px;
                selection-background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.frame_send_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_send_message.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_send_message.setObjectName("frame_send_message")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.frame_send_message)
        self.horizontalLayout_3.setContentsMargins(5, 0, 5, 5)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        
        self.pushButton_call = PushButton_2(parent=self.frame_send_message)
        self.pushButton_call.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_call.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_call.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_call.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_call.setText("")
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap("app/gui/icons/sowsystem.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_call.setIcon(icon10)
        self.pushButton_call.setIconSize(QtCore.QSize(16, 16))
        self.pushButton_call.setObjectName("pushButton_call")
        self.horizontalLayout_3.addWidget(self.pushButton_call, 0, QtCore.Qt.AlignmentFlag.AlignBottom)
        
        self.textEdit_write_user_message = QtWidgets.QTextEdit(parent=self.frame_send_message)
        self.textEdit_write_user_message.setMinimumSize(QtCore.QSize(0, 40))
        self.textEdit_write_user_message.setMaximumSize(QtCore.QSize(0, 16777215))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_write_user_message.setFont(font)
        self.textEdit_write_user_message.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.textEdit_write_user_message.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhMultiLine)
        self.textEdit_write_user_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.textEdit_write_user_message.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.textEdit_write_user_message.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.textEdit_write_user_message.setAutoFormatting(QtWidgets.QTextEdit.AutoFormattingFlag.AutoNone)
        self.textEdit_write_user_message.setAcceptRichText(False)
        self.textEdit_write_user_message.setObjectName("textEdit_write_user_message")
        self.horizontalLayout_3.addWidget(self.textEdit_write_user_message)
        
        self.pushButton_send_message = PushButton_2(parent=self.frame_send_message)
        self.pushButton_send_message.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_send_message.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_send_message.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_send_message.setText("")
        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap("app/gui/icons/send.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_send_message.setIcon(icon11)
        self.pushButton_send_message.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_send_message.setObjectName("pushButton_send_message")
        self.horizontalLayout_3.addWidget(self.pushButton_send_message, 0, QtCore.Qt.AlignmentFlag.AlignBottom)
        self.horizontalLayout_5.addWidget(self.frame_send_message)
        spacerItem28 = QtWidgets.QSpacerItem(200, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem28)
        self.verticalLayout_6.addWidget(self.frame_send_message_full)

        self.top.raise_()
        self.scrollArea_chat.raise_()
        self.frame_send_message_full.raise_()
        self.stackedWidget.addWidget(self.chat_page)

        # ======= Models Hub Page ========
        self.modelshub_page = QtWidgets.QWidget()
        self.modelshub_page.setObjectName("modelshub_page")
        self.verticalLayout_models_hub = QtWidgets.QVBoxLayout(self.modelshub_page)
        self.verticalLayout_models_hub.setContentsMargins(0, 0, 0, 5)
        self.verticalLayout_models_hub.setSpacing(0)
        self.verticalLayout_models_hub.setObjectName("verticalLayout_models_hub")
        
        self.frame_models_hub_search = QtWidgets.QFrame(parent=self.modelshub_page)
        self.frame_models_hub_search.setMinimumSize(QtCore.QSize(0, 50))
        self.frame_models_hub_search.setMaximumSize(QtCore.QSize(16777215, 50))
        self.frame_models_hub_search.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_models_hub_search.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_models_hub_search.setObjectName("frame_models_hub_search")
        self.frame_models_hub_search.setStyleSheet("""
            QFrame#frame_models_hub_search {
                background-color: transparent;
            }
        """)
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.frame_models_hub_search)
        self.horizontalLayout_8.setContentsMargins(30, 0, 30, 0)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")

        glass_toggle_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 0.03);
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                padding: 5px 15px;
                font-family: 'Inter Tight SemiBold';
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:checked {
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """

        self.pushButton_models_hub_recommendations = QtWidgets.QPushButton(parent=self.frame_models_hub_search)
        self.pushButton_models_hub_recommendations.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_models_hub_recommendations.setMinimumSize(QtCore.QSize(190, 33))
        self.pushButton_models_hub_recommendations.setMaximumSize(QtCore.QSize(190, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_models_hub_recommendations.setFont(font)
        self.pushButton_models_hub_recommendations.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        icon_recommendations = QtGui.QIcon()
        icon_recommendations.addPixmap(QtGui.QPixmap("app/gui/icons/recommendations.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_models_hub_recommendations.setIcon(icon_recommendations)
        self.pushButton_models_hub_recommendations.setIconSize(QtCore.QSize(32, 35))
        self.pushButton_models_hub_recommendations.setCheckable(True)
        self.pushButton_models_hub_recommendations.setAutoExclusive(True)
        self.pushButton_models_hub_recommendations.setObjectName("pushButton_models_hub_recommendations")
        self.horizontalLayout_8.addWidget(self.pushButton_models_hub_recommendations)
        self.pushButton_models_hub_popular = QtWidgets.QPushButton(parent=self.frame_models_hub_search)
        self.pushButton_models_hub_popular.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_models_hub_popular.setMinimumSize(QtCore.QSize(150, 33))
        self.pushButton_models_hub_popular.setMaximumSize(QtCore.QSize(150, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_models_hub_popular.setFont(font)
        self.pushButton_models_hub_popular.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        icon_popular = QtGui.QIcon()
        icon_popular.addPixmap(QtGui.QPixmap("app/gui/icons/popular.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_models_hub_popular.setIcon(icon_popular)
        self.pushButton_models_hub_popular.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_models_hub_popular.setCheckable(True)
        self.pushButton_models_hub_popular.setAutoExclusive(True)
        self.pushButton_models_hub_popular.setObjectName("pushButton_models_hub_popular")
        self.horizontalLayout_8.addWidget(self.pushButton_models_hub_popular)
        self.pushButton_models_hub_my_models = QtWidgets.QPushButton(parent=self.frame_models_hub_search)
        self.pushButton_models_hub_my_models.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_models_hub_my_models.setMinimumSize(QtCore.QSize(150, 33))
        self.pushButton_models_hub_my_models.setMaximumSize(QtCore.QSize(150, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_models_hub_my_models.setFont(font)
        self.pushButton_models_hub_my_models.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        icon_my_models = QtGui.QIcon()
        icon_my_models.addPixmap(QtGui.QPixmap("app/gui/icons/models.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_models_hub_my_models.setIcon(icon_my_models)
        self.pushButton_models_hub_my_models.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_models_hub_my_models.setCheckable(True)
        self.pushButton_models_hub_my_models.setChecked(True)
        self.pushButton_models_hub_my_models.setAutoExclusive(True)
        self.pushButton_models_hub_my_models.setObjectName("pushButton_models_hub_my_models")
        self.horizontalLayout_8.addWidget(self.pushButton_models_hub_my_models)

        self.pushButton_models_hub_recommendations.setStyleSheet(glass_toggle_style)
        self.pushButton_models_hub_popular.setStyleSheet(glass_toggle_style)
        self.pushButton_models_hub_my_models.setStyleSheet(glass_toggle_style)

        self.pushButton_reload_models = QtWidgets.QPushButton(parent=self.frame_models_hub_search)
        self.pushButton_reload_models.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_models.setMinimumSize(QtCore.QSize(33, 33))
        self.pushButton_reload_models.setMaximumSize(QtCore.QSize(33, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_reload_models.setFont(font)
        self.pushButton_reload_models.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_reload_models.setStyleSheet(glass_toggle_style)
        self.pushButton_reload_models.setText("")
        icon_reload_models = QtGui.QIcon()
        icon_reload_models.addPixmap(QtGui.QPixmap("app/gui/icons/reload.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_reload_models.setIcon(icon_reload_models)
        self.pushButton_reload_models.setObjectName("pushButton_reload_models")
        self.horizontalLayout_8.addWidget(self.pushButton_reload_models)
        spacerItem31 = QtWidgets.QSpacerItem(612, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem31)
        
        self.search_bar_models = ModernSearchBar(parent=self.frame_models_hub_search)
        self.search_bar_models.setMinimumSize(QtCore.QSize(300, 45))
        self.search_bar_models.setMaximumSize(QtCore.QSize(400, 45))
        self.search_bar_models.line_edit.setPlaceholderText("Search models...")
        self.lineEdit_search_model = self.search_bar_models.line_edit
        self.pushButton_search_model = self.search_bar_models.search_btn
        
        self.horizontalLayout_8.addWidget(self.search_bar_models)

        self.verticalLayout_models_hub.addWidget(self.frame_models_hub_search)
        self.listWidget_models_hub = QtWidgets.QListWidget(parent=self.modelshub_page)
        self.listWidget_models_hub.setMinimumSize(QtCore.QSize(0, 0))
        self.listWidget_models_hub.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.listWidget_models_hub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.listWidget_models_hub.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.listWidget_models_hub.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.listWidget_models_hub.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.listWidget_models_hub.verticalScrollBar().setSingleStep(15)
        self.listWidget_models_hub.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                border: none;
                padding: 5px 15px;
            }
            QListWidget::item:selected { background: transparent; border: none; }
            QListWidget::item:hover { background: transparent; }
                                                 
            QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin-top: 13px;
                border-radius: 5px;
                margin-left: 10px;
                margin-bottom: 13px;
            }

            QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
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
        self.listWidget_models_hub.setObjectName("listWidget_models_hub")
        self.verticalLayout_models_hub.addWidget(self.listWidget_models_hub)
        self.stackedWidget.addWidget(self.modelshub_page)

        # ====================== RP Editors Page ======================
        self.rp_editors_page = QtWidgets.QWidget()
        self.rp_editors_page.setObjectName("rp_editors_page")
        self.rp_editors_page.setStyleSheet("background: transparent;")

        self.rp_layout = QtWidgets.QVBoxLayout(self.rp_editors_page)
        self.rp_layout.setContentsMargins(50, 50, 50, 50)
        self.rp_layout.setSpacing(20)

        self.rp_header_layout = QtWidgets.QVBoxLayout()
        self.rp_header_layout.setSpacing(5)

        self.rp_title_label = QtWidgets.QLabel(self.translations.get("rp_editors_title", "RolePlay Editors"))
        font_rp_title = QtGui.QFont("Inter Tight SemiBold", 26, QtGui.QFont.Weight.Bold)
        font_rp_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.rp_title_label.setFont(font_rp_title)
        self.rp_title_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); border: none; background: transparent;")

        self.rp_subtitle_label = QtWidgets.QLabel(self.translations.get("rp_editors_subtitle", "Manage your personas, world lore, and system prompts"))
        font_rp_sub = QtGui.QFont("Inter Tight Medium", 12)
        font_rp_sub.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.rp_subtitle_label.setFont(font_rp_sub)
        self.rp_subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); border: none; background: transparent;")

        self.rp_header_layout.addWidget(self.rp_title_label)
        self.rp_header_layout.addWidget(self.rp_subtitle_label)
        self.rp_layout.addLayout(self.rp_header_layout)

        self.rp_separator = QtWidgets.QFrame()
        self.rp_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.rp_separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border: none; max-height: 1px; margin-top: 15px; margin-bottom: 25px;")
        self.rp_layout.addWidget(self.rp_separator)

        self.rp_grid_layout = QtWidgets.QGridLayout()
        self.rp_grid_layout.setSpacing(30)
        self.rp_grid_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

        self.btn_open_lorebook = RPGlassCard(
            title=self.translations.get("rp_card_lorebook_title", "Lorebooks"),
            description=self.translations.get("rp_card_lorebook_desc", "Create rules, places, and world events for your scenarios."),
            icon_path="app/gui/icons/lorebook.png"
        )
        
        self.btn_open_personas = RPGlassCard(
            title=self.translations.get("rp_card_personas_title", "Personas"),
            description=self.translations.get("rp_card_personas_desc", "Manage your user profiles, avatars, and identity descriptions."),
            icon_path="app/gui/icons/personas.png"
        )

        self.btn_open_prompts = RPGlassCard(
            title=self.translations.get("rp_card_prompts_title", "System Prompts"),
            description=self.translations.get("rp_card_prompts_desc", "Configure instructions and format how the AI receives character data."),
            icon_path="app/gui/icons/system_prompt.png"
        )

        self.rp_grid_layout.addWidget(self.btn_open_lorebook, 0, 0)
        self.rp_grid_layout.addWidget(self.btn_open_personas, 0, 1)
        self.rp_grid_layout.addWidget(self.btn_open_prompts, 0, 2)

        self.rp_layout.addLayout(self.rp_grid_layout)
        self.rp_layout.addStretch()

        self.stackedWidget.addWidget(self.rp_editors_page)
        # =============================================================
        
        self.gridLayout_3.addWidget(self.stackedWidget, 0, 0, 1, 1)
        self.gridLayout_20.addWidget(self.SideBar_Right, 1, 1, 1, 1)
        
        self.SideBar_Left = QtWidgets.QWidget(parent=self.main_widget)
        self.SideBar_Left.setMinimumSize(QtCore.QSize(190, 648))
        self.SideBar_Left.setMaximumSize(QtCore.QSize(190, 16777215))
        self.SideBar_Left.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)

        shadow_sidebar = QtWidgets.QGraphicsDropShadowEffect()
        shadow_sidebar.setBlurRadius(20)
        shadow_sidebar.setXOffset(0)
        shadow_sidebar.setYOffset(0)
        shadow_sidebar.setColor(QColor(0, 0, 0, 80))
        self.SideBar_Left.setGraphicsEffect(shadow_sidebar)

        shadow_button = QtWidgets.QGraphicsDropShadowEffect()
        shadow_button.setBlurRadius(15)
        shadow_button.setXOffset(3)
        shadow_button.setYOffset(3)
        shadow_button.setColor(QColor(0, 0, 0, 50))

        shadow_logo = QtWidgets.QGraphicsDropShadowEffect()
        shadow_logo.setBlurRadius(10)
        shadow_logo.setXOffset(2)
        shadow_logo.setYOffset(2)
        shadow_logo.setColor(QColor(0, 0, 0, 100))

        self.SideBar_Left.setStyleSheet("#SideBar_Left {\n"
"    background: qlineargradient(spread: pad, x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 rgba(27, 27, 27, 255), stop: 0.25 rgba(38, 38, 38, 255), stop: 0.5 rgba(42, 42, 42, 255), stop: 0.75 rgba(46, 46, 46, 255), stop: 1 rgba(50, 50, 50, 255));\n"
"}")
        self.SideBar_Left.setObjectName("SideBar_Left")
        
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.SideBar_Left)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_logotype = QtWidgets.QLabel(parent=self.SideBar_Left)
        self.label_logotype.setMinimumSize(QtCore.QSize(185, 0))
        self.label_logotype.setMaximumSize(QtCore.QSize(185, 85))
        self.label_logotype.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.label_logotype.setStyleSheet("padding: 10px;")
        self.label_logotype.setText("")
        self.label_logotype.setPixmap(QtGui.QPixmap("app/gui/icons/logotitle.png"))
        self.label_logotype.setScaledContents(True)
        self.label_logotype.setGraphicsEffect(shadow_logo)
        self.label_logotype.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_logotype.setIndent(3)
        self.label_logotype.setObjectName("label_logotype")
        self.verticalLayout_2.addWidget(self.label_logotype)
        self.separator_left_bar_2 = QtWidgets.QFrame(parent=self.SideBar_Left)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.separator_left_bar_2.sizePolicy().hasHeightForWidth())
        self.separator_left_bar_2.setSizePolicy(sizePolicy)
        self.separator_left_bar_2.setMinimumSize(QtCore.QSize(150, 2))
        self.separator_left_bar_2.setMaximumSize(QtCore.QSize(150, 2))
        self.separator_left_bar_2.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 40);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_left_bar_2.setMidLineWidth(0)
        self.separator_left_bar_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_left_bar_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_left_bar_2.setObjectName("separator_left_bar_2")
        self.verticalLayout_2.addWidget(self.separator_left_bar_2, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setContentsMargins(-1, 0, 0, 0)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        spacerItem29 = QtWidgets.QSpacerItem(20, 10, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.verticalLayout.addItem(spacerItem29)
        
        self.pushButton_main = RippleButton(parent=self.SideBar_Left)
        self.pushButton_main.setEnabled(True)
        self.pushButton_main.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_main.sizePolicy().hasHeightForWidth())
        self.pushButton_main.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_main.setFont(font)
        self.pushButton_main.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_main.setMouseTracking(False)
        self.pushButton_main.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.pushButton_main.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_main.setAutoFillBackground(False)
        self.pushButton_main.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap("app/gui/icons/main.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_main.setIcon(icon12)
        self.pushButton_main.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_main.setCheckable(True)
        self.pushButton_main.setChecked(True)
        self.pushButton_main.setAutoExclusive(True)
        self.pushButton_main.setAutoDefault(False)
        self.pushButton_main.setDefault(False)
        self.pushButton_main.setFlat(False)
        self.pushButton_main.setObjectName("pushButton_main")
        self.verticalLayout.addWidget(self.pushButton_main)

        self.pushButton_rp_editors = RippleButton(parent=self.SideBar_Left)
        self.pushButton_rp_editors.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_rp_editors.sizePolicy().hasHeightForWidth())
        self.pushButton_rp_editors.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.pushButton_rp_editors.setFont(font)
        self.pushButton_rp_editors.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_rp_editors.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_rp_editors.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon_rp = QtGui.QIcon()
        icon_rp.addPixmap(QtGui.QPixmap("app/gui/icons/lorebook.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_rp_editors.setIcon(icon_rp)
        self.pushButton_rp_editors.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_rp_editors.setCheckable(True)
        self.pushButton_rp_editors.setAutoExclusive(True)
        self.pushButton_rp_editors.setObjectName("pushButton_rp_editors")
        self.verticalLayout.addWidget(self.pushButton_rp_editors)
        
        self.pushButton_create_character = RippleButton(parent=self.SideBar_Left)
        self.pushButton_create_character.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_create_character.sizePolicy().hasHeightForWidth())
        self.pushButton_create_character.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_create_character.setFont(font)
        self.pushButton_create_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon_add_user = QtGui.QIcon()
        icon_add_user.addPixmap(QtGui.QPixmap("app/gui/icons/add_user.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_create_character.setIcon(icon_add_user)
        self.pushButton_create_character.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_create_character.setCheckable(True)
        self.pushButton_create_character.setChecked(False)
        self.pushButton_create_character.setAutoExclusive(True)
        self.pushButton_create_character.setObjectName("pushButton_create_character")
        self.verticalLayout.addWidget(self.pushButton_create_character)
        
        self.pushButton_characters_gateway = RippleButton(parent=self.SideBar_Left)
        self.pushButton_characters_gateway.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_characters_gateway.setFont(font)
        self.pushButton_characters_gateway.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_characters_gateway.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_characters_gateway.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon14 = QtGui.QIcon()
        icon14.addPixmap(QtGui.QPixmap("app/gui/icons/gateway.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_characters_gateway.setIcon(icon14)
        self.pushButton_characters_gateway.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_characters_gateway.setCheckable(True)
        self.pushButton_characters_gateway.setChecked(False)
        self.pushButton_characters_gateway.setAutoExclusive(True)
        self.pushButton_characters_gateway.setObjectName("pushButton_characters_gateway")
        self.verticalLayout.addWidget(self.pushButton_characters_gateway)

        self.pushButton_models_hub = RippleButton(parent=self.SideBar_Left)
        self.pushButton_models_hub.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_models_hub.sizePolicy().hasHeightForWidth())
        self.pushButton_models_hub.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_models_hub.setFont(font)
        self.pushButton_models_hub.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_models_hub.setMouseTracking(False)
        self.pushButton_models_hub.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.pushButton_models_hub.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_models_hub.setAutoFillBackground(False)
        self.pushButton_models_hub.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon_models_hub = QtGui.QIcon()
        icon_models_hub.addPixmap(QtGui.QPixmap("app/gui/icons/modelshub.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_models_hub.setIcon(icon_models_hub)
        self.pushButton_models_hub.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_models_hub.setCheckable(True)
        self.pushButton_models_hub.setChecked(False)
        self.pushButton_models_hub.setAutoExclusive(True)
        self.pushButton_models_hub.setAutoDefault(False)
        self.pushButton_models_hub.setDefault(False)
        self.pushButton_models_hub.setFlat(False)
        self.pushButton_models_hub.setObjectName("pushButton_models_hub")
        self.verticalLayout.addWidget(self.pushButton_models_hub)
        
        self.pushButton_options = RippleButton(parent=self.SideBar_Left)
        self.pushButton_options.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_options.setFont(font)
        self.pushButton_options.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_options.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_options.setStyleSheet("QPushButton {\n"
"    color: rgb(210, 210, 210);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"    height: 50px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:pressed {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"}\n"
"        \n"
"QPushButton:checked {\n"
"    background-color:  rgb(27,27,27);\n"
"    color: rgb(210, 210, 210);\n"
"    border-left: 3px solid rgb(160, 160, 160);\n"
"}")
        icon15 = QtGui.QIcon()
        icon15.addPixmap(QtGui.QPixmap("app/gui/icons/options.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_options.setIcon(icon15)
        self.pushButton_options.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_options.setCheckable(True)
        self.pushButton_options.setAutoExclusive(True)
        self.pushButton_options.setObjectName("pushButton_options")
        self.verticalLayout.addWidget(self.pushButton_options)
        self.verticalLayout_2.addLayout(self.verticalLayout)
        spacerItem30 = QtWidgets.QSpacerItem(40, 326, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_2.addItem(spacerItem30)
        self.progressBar_llm_loading = QtWidgets.QProgressBar(parent=self.SideBar_Left)
        self.progressBar_llm_loading.setMinimumSize(QtCore.QSize(188, 40))
        self.progressBar_llm_loading.setMaximumSize(QtCore.QSize(188, 40))
        self.progressBar_llm_loading.setStyleSheet("QProgressBar {\n"
"                margin: 10px 10px 10px;\n"
"                border: 1px solid #3A3A3A;\n"
"                border-radius: 5px;\n"
"                background-color: #2A2A2A;\n"
"                text-align: center;\n"
"                color: #FFFFFF;\n"
"                font-weight: bold;\n"
"                min-height: 16px;\n"
"            }\n"
"            \n"
"            QProgressBar::chunk {\n"
"                background-color: qlineargradient(\n"
"                    spread:pad, x1:0, y1:0.5, x2:1, y2:0.5,\n"
"                    stop:0 #27ae2b, stop:1 #2cc944\n"
"                );\n"
"                border-radius: 3px;\n"
"                margin: 1px;\n"
"            }")
        self.progressBar_llm_loading.setProperty("value", 0)
        self.progressBar_llm_loading.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.progressBar_llm_loading.setTextVisible(False)
        self.progressBar_llm_loading.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.progressBar_llm_loading.setInvertedAppearance(False)
        self.progressBar_llm_loading.setTextDirection(QtWidgets.QProgressBar.Direction.TopToBottom)
        self.progressBar_llm_loading.setObjectName("progressBar_llm_loading")
        self.verticalLayout_2.addWidget(self.progressBar_llm_loading)
        self.progressBar_llm_loading.hide()

        self.loading_model_label = QtWidgets.QLabel(parent=self.SideBar_Left)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setItalic(False)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.loading_model_label.setFont(font)
        self.loading_model_label.setStyleSheet("background: transparent;\n"
            "color: rgb(216, 216, 216);\n"
            "padding-left: 10px;\n"
            "margin-bottom: 5px;"
        )
        self.loading_model_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.loading_model_label.setObjectName("loading_model_label")
        self.verticalLayout_2.addWidget(self.loading_model_label)
        self.loading_model_label.hide()

        self.separator_left_bar_3 = QtWidgets.QFrame(parent=self.SideBar_Left)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.separator_left_bar_3.sizePolicy().hasHeightForWidth())
        self.separator_left_bar_3.setMinimumSize(QtCore.QSize(165, 2))
        self.separator_left_bar_3.setMaximumSize(QtCore.QSize(165, 2))
        self.separator_left_bar_3.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 40);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_left_bar_3.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.separator_left_bar_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_left_bar_3.setObjectName("separator_left_bar_3")
        self.verticalLayout_2.addWidget(self.separator_left_bar_3, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.footer_container = QtWidgets.QWidget(self.SideBar_Left)
        footer_layout = QtWidgets.QHBoxLayout(self.footer_container)
        footer_layout.setContentsMargins(5, 10, 5, 10) 
        footer_layout.setSpacing(5)
        footer_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.glass_capsule = QtWidgets.QFrame()
        self.glass_capsule.setMinimumHeight(46)
        self.glass_capsule.setFixedWidth(170)
        self.glass_capsule.setStyleSheet("""
            QFrame {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 23px;
            }
        """)
        
        capsule_shadow = QtWidgets.QGraphicsDropShadowEffect()
        capsule_shadow.setBlurRadius(20)
        capsule_shadow.setColor(QColor(0, 0, 0, 100))
        capsule_shadow.setOffset(0, 5)
        self.glass_capsule.setGraphicsEffect(capsule_shadow)

        capsule_layout = QtWidgets.QHBoxLayout(self.glass_capsule)
        capsule_layout.setContentsMargins(0, 0, 0, 0)
        capsule_layout.setSpacing(5)
        capsule_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.pushButton_github = LiquidButton("app/gui/icons/github.png", "#FFFFFF", self.glass_capsule)
        self.pushButton_github.setObjectName("pushButton_github")
        capsule_layout.addWidget(self.pushButton_github)

        self.pushButton_discord = LiquidButton("app/gui/icons/discord.png", "#5865F2", self.glass_capsule)
        self.pushButton_discord.setObjectName("pushButton_discord")
        capsule_layout.addWidget(self.pushButton_discord)

        self.pushButton_youtube = LiquidButton("app/gui/icons/youtube.png", "#FF0000", self.glass_capsule)
        self.pushButton_youtube.setObjectName("pushButton_youtube")
        capsule_layout.addWidget(self.pushButton_youtube)

        self.about_btn = LiquidButton("app/gui/icons/information.png", "#00BFFF", self.glass_capsule)
        self.about_btn.setObjectName("about_btn")
        capsule_layout.addWidget(self.about_btn)

        footer_layout.addWidget(self.glass_capsule)
        self.verticalLayout_2.addWidget(self.footer_container)
        self.gridLayout_20.addWidget(self.SideBar_Left, 1, 0, 1, 1)

        self.SideBar_Right.raise_()
        self.SideBar_Left.raise_()
        self.menu_bar.raise_()
        self.horizontalLayout_main_widget.addWidget(self.main_widget)
        MainWindow.setCentralWidget(self.centralwidget)

        self.stackedWidget.setCurrentIndex(0)
        self.tabWidget_characters_gateway.setCurrentIndex(0)
        self.stackedWidget_character_ai.setCurrentIndex(0)
        self.stackedWidget_character_card_gateway.setCurrentIndex(0)
        self.tabWidget_options.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

class RippleButton(QPushButton):
    def __init__(self, *args, ripple_color=QColor(50, 50, 50, 100), **kwargs):
        super().__init__(*args, **kwargs)
        self._ripple_radius = 0
        self._ripple_pos = None
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self.update_ripple)
        self._max_radius = 0
        self._ripple_color = ripple_color
        self._opacity = 1.0
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, event):
        if not self.isChecked():
            self._ripple_pos = event.pos()
            self._ripple_radius = 0
            self._opacity = 1.0
            self._max_radius = max(self.width(), self.height())
            self._animation_timer.start(10)
        super().mousePressEvent(event)

    def update_ripple(self):
        if self._ripple_radius < self._max_radius:
            self._ripple_radius += 7
        else:
            self._opacity -= 0.07
            if self._opacity <= 0:
                self._animation_timer.stop()
                self._ripple_pos = None
                self._ripple_radius = 0
                self._opacity = 1.0
                return

        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._ripple_pos and self._ripple_radius > 0:
            painter = QPainter(self)
            gradient = QRadialGradient(
                QPointF(self._ripple_pos),
                self._ripple_radius
            )
            gradient.setColorAt(0, QColor(self._ripple_color.red(), self._ripple_color.green(), self._ripple_color.blue(), int(255 * self._opacity)))
            gradient.setColorAt(1, QColor(self._ripple_color.red(), self._ripple_color.green(), self._ripple_color.blue(), 0))
            painter.setBrush(gradient)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self._ripple_pos, self._ripple_radius, self._ripple_radius)

    def isChecked(self):
        return self.property("checked") or False

    def setChecked(self, checked):
        self.setProperty("checked", checked)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

class PushButton(QtWidgets.QPushButton):
    def __init__(self, icon_path, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self.icon_pixmap = QtGui.QPixmap(icon_path)
        
        self._color_normal = QColor(255, 255, 255, 10)
        self._color_hover = QColor(255, 255, 255, 40)
        self._color_pressed = QColor(255, 255, 255, 60)

        self._current_bg_color = self._color_normal
        
        self._animation = QtCore.QVariantAnimation(self)
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._animation.valueChanged.connect(self._update_bg_color)

    def _update_bg_color(self, color):
        self._current_bg_color = color
        self.update()

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_hover)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_normal)
        self._animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._animation.stop()
        self._current_bg_color = self._color_pressed
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_hover)
        self._animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        draw_rect = QRectF(rect).adjusted(1, 1, -1, -1)
        radius = 20

        painter.setBrush(QBrush(self._current_bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1)) 
        painter.drawRoundedRect(draw_rect, radius, radius)

        if not self.icon_pixmap.isNull():
            icon_size = 20
            x = (self.width() - icon_size) // 2
            y = (self.height() - icon_size) // 2
            painter.drawPixmap(x, y, icon_size, icon_size, 
                               self.icon_pixmap.scaled(
                                   icon_size, icon_size, 
                                   Qt.AspectRatioMode.KeepAspectRatio, 
                                   Qt.TransformationMode.SmoothTransformation
                               ))

class PushButton_2(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

        self._color_normal = QColor(67, 68, 70, 180) 
        self._color_hover = QColor(90, 93, 96, 220)
        self._color_pressed = QColor(120, 123, 126, 240)

        self._current_bg_color = self._color_normal

        self._animation = QtCore.QVariantAnimation(self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self._animation.valueChanged.connect(self._update_bg_color)

    def _update_bg_color(self, color):
        self._current_bg_color = color
        self.update()

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_hover)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_normal)
        self._animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._animation.stop()
        self._current_bg_color = self._color_pressed
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._animation.setStartValue(self._current_bg_color)
        self._animation.setEndValue(self._color_hover)
        self._animation.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()
        draw_rect = QRectF(rect).adjusted(1, 1, -1, -1)
        radius = 15

        painter.setBrush(QBrush(self._current_bg_color))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1)) 
        painter.drawRoundedRect(draw_rect, radius, radius)

        if not self.icon().isNull():
            icon_size = 16
            x = int((self.width() - icon_size) / 2)
            y = int((self.height() - icon_size) / 2)
            
            self.icon().paint(painter, x, y, icon_size, icon_size)

class AnimatedToggle(QtWidgets.QCheckBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("")
        
        self._bg_off = QColor("#3a3a3a")
        self._bg_on = QColor("#d32f2f")
        self._circle_color = QColor("#dddddd")
        self._circle_color_hover = QColor("#ffffff")
        
        self._circle_position = 3
        
        self._animation = QPropertyAnimation(self, b"circle_position", self)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._animation.setDuration(250)
        
        self.stateChanged.connect(self.start_transition)

    @pyqtProperty(float)
    def circle_position(self):
        return self._circle_position

    @circle_position.setter
    def circle_position(self, pos):
        self._circle_position = pos
        self.update()

    def start_transition(self, state):
        self._animation.stop()
        
        if self.isChecked():
            end_val = self.width() - 25
        else:
            end_val = 3
            
        self._animation.setStartValue(self._circle_position)
        self._animation.setEndValue(end_val)
        self._animation.start()

    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        track_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height())
        
        if self.isChecked():
            bg_color = self._bg_on
        else:
            bg_color = self._bg_off
            
        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(track_rect, 14, 14)
        
        circle_rect = QRectF(self._circle_position, 3, 22, 22)
        
        p.setBrush(QBrush(self._circle_color))
        p.drawEllipse(circle_rect)
        p.end()

class ModernSearchBar(QtWidgets.QFrame):
    textChanged = QtCore.pyqtSignal(str)
    returnPressed = QtCore.pyqtSignal()
    searchClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 45)
        self.setMaximumHeight(45)
        self.setObjectName("ModernSearchBar")
        
        self._border_color = QtGui.QColor(255, 255, 255, 40)
        self.animation = QtCore.QPropertyAnimation(self, b"border_color")
        self.animation.setDuration(250)
        
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(18, 0, 5, 0)
        self.layout.setSpacing(10)
        
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setPlaceholderText("Search characters...")
        font = QtGui.QFont()
        font.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.line_edit.setFont(font)

        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: transparent; 
                border: none; 
                color: #ffffff; 
                font-size: 14px;
                font-family: 'Inter Tight', 'Segoe UI';
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.line_edit.textChanged.connect(self._handle_text_change)
        self.line_edit.returnPressed.connect(self.returnPressed)
        self.line_edit.installEventFilter(self)
        
        self.clear_btn = QtWidgets.QPushButton("✕")
        self.clear_btn.setFont(font)
        self.clear_btn.setFixedSize(22, 22)
        self.clear_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.clear_btn.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                color: rgba(255, 255, 255, 80); 
                border-radius: 11px; 
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background: rgba(255, 255, 255, 30); 
                color: #fff; 
            }
        """)
        self.clear_btn.clicked.connect(self.line_edit.clear)
        self.clear_btn.hide()

        self.search_btn = QtWidgets.QPushButton()
        self.search_btn.setFixedSize(34, 34)
        self.search_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.search_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.search_btn.setIcon(QtGui.QIcon("app/gui/icons/search.png"))
        self.search_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 17px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
                border: 1px solid rgba(255, 255, 255, 40);
            }
        """)
        self.search_btn.clicked.connect(lambda: self.searchClicked.emit(self.line_edit.text()))

        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.clear_btn)
        self.layout.addWidget(self.search_btn)

    def _handle_text_change(self, text):
        self.textChanged.emit(text)
        self.clear_btn.setVisible(len(text) > 0)

    @QtCore.pyqtProperty(QtGui.QColor)
    def border_color(self):
        return self._border_color

    @border_color.setter
    def border_color(self, color):
        self._border_color = color
        self.update()

    def eventFilter(self, obj, event):
        if obj == self.line_edit:
            if event.type() == QtCore.QEvent.Type.FocusIn:
                self.animate_focus(True)
            elif event.type() == QtCore.QEvent.Type.FocusOut:
                self.animate_focus(False)
        return super().eventFilter(obj, event)

    def animate_focus(self, focused):
        self.animation.stop()
        self.animation.setStartValue(self._border_color)
        end_color = QtGui.QColor(255, 255, 255, 120) if focused else QtGui.QColor(255, 255, 255, 40)
        self.animation.setEndValue(end_color)
        self.animation.start()

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(rect), radius, radius)
        p.fillPath(path, QtGui.QColor(0, 0, 0, 65)) 
        
        pen = QtGui.QPen(self._border_color, 1.2)
        p.setPen(pen)
        p.drawPath(path)

    def text(self): 
        return self.line_edit.text()
    
    def setText(self, text): 
        self.line_edit.setText(text)

class AutoResizingTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.textChanged.connect(self.adjust_height)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def adjust_height(self):
        doc_height = int(self.document().size().height())
        margins = self.contentsMargins()
        new_height = doc_height + margins.top() + margins.bottom() + 15
        self.setMinimumHeight(max(100, new_height))

class LiquidButton(QtWidgets.QPushButton):
    def __init__(self, icon_path, hover_color_hex, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        original_pixmap = QtGui.QPixmap(icon_path)
        
        self.icon_pixmap = original_pixmap.scaled(
            24, 24,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        
        self._base_color = QColor(0, 0, 0, 0)
        self._hover_color = QColor(hover_color_hex)
        self._hover_color.setAlpha(80)
        self._current_color = self._base_color

        self._animation = QtCore.QVariantAnimation(self)
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QtCore.QEasingCurve.Type.OutQuad)
        self._animation.valueChanged.connect(self._update_color)

    def _update_color(self, color):
        self._current_color = color
        self.update()

    def enterEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_color)
        self._animation.setEndValue(self._hover_color)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.stop()
        self._animation.setStartValue(self._current_color)
        self._animation.setEndValue(self._base_color)
        self._animation.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        path = QtGui.QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        painter.fillPath(path, self._current_color)

        icon_size = 26
        
        x = round((self.width() - icon_size) / 2)
        y = round((self.height() - icon_size) / 2)

        is_hovered = self._current_color.alpha() > 10
    
        if is_hovered:
            painter.setOpacity(1.0)
        else:
            painter.setOpacity(0.6)
        
        painter.drawPixmap(x, y, icon_size, icon_size, self.icon_pixmap)

class RPGlassCard(QtWidgets.QFrame):
    clicked = QtCore.pyqtSignal()

    def __init__(self, title, description, icon_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 180)
        self.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.setObjectName("rp_card")

        self.style_normal = """
            QFrame#rp_card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(35, 35, 45, 0.4), stop:1 rgba(15, 15, 20, 0.6));
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
            }
        """
        self.style_hover = """
            QFrame#rp_card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(50, 50, 65, 0.6), stop:1 rgba(25, 25, 35, 0.8));
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
            }
        """
        self.setStyleSheet(self.style_normal)

        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35)
        shadow.setColor(QtGui.QColor(0, 0, 0, 120))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        icon_lbl = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(icon_path).scaled(42, 42, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        icon_lbl.setPixmap(pixmap)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        
        title_lbl = QtWidgets.QLabel(title)
        f_title = QtGui.QFont("Inter Tight SemiBold", 16, QtGui.QFont.Weight.Bold)
        f_title.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        title_lbl.setFont(f_title)
        title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.95); background: transparent; border: none;")

        desc_lbl = QtWidgets.QLabel(description)
        f_desc = QtGui.QFont("Inter Tight Medium", 11)
        f_desc.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        desc_lbl.setFont(f_desc)
        desc_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.55); background: transparent; border: none; line-height: 1.4;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(icon_lbl)
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        layout.addStretch()

    def enterEvent(self, event):
        self.setStyleSheet(self.style_hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self.style_normal)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setStyleSheet("""
                QFrame#rp_card {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(20, 20, 25, 0.8), stop:1 rgba(10, 10, 15, 0.9));
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    border-radius: 20px;
                }
            """)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.setStyleSheet(self.style_hover)
            self.clicked.emit()
        super().mouseReleaseEvent(event)
