import os
import yaml
from pathlib import Path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QListWidget
from PyQt6.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, QPoint
from PyQt6.QtGui import QColor, QPainter, QRadialGradient, QCursor, QFont, QPixmap, QPen, QBrush

from app.gui.soul_stage_page import SoulStagePage
from app.configuration import configuration

class SmallPasswordMaskStyle(QtWidgets.QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QtWidgets.QStyle.StyleHint.SH_LineEdit_PasswordCharacter:
            return ord("·")
        return super().styleHint(hint, option, widget, returnData)

def visibility_icon(hidden=False):
    pixmap = QtGui.QPixmap(20, 20)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setPen(QtGui.QPen(QtGui.QColor("#DEDAD2"), 1.6))
    painter.drawEllipse(2, 6, 16, 8)
    painter.drawEllipse(8, 8, 4, 4)
    if hidden:
        painter.drawLine(3, 3, 17, 17)
    painter.end()
    return QtGui.QIcon(pixmap)


class Ui_MainWindow(object):
    def __init__(self):
        self.translations = {}
        
        self.configuration = configuration.ConfigurationSettings()
        selected_language = self.configuration.get_main_setting("program_language")

        self.rp_cards = []
        self.rp_container = None

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

        font_title_lbl = QtGui.QFont("Inter Tight SemiBold", 10, QtGui.QFont.Weight.Bold)
        font_title_lbl.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        font_label = QtGui.QFont("Inter Tight Medium", 11)
        font_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
        font_input = QtGui.QFont("Inter Tight Medium", 10)
        font_input.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        
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

        self.pushButton_create_character_2 = GlassPortalButton(parent=self.frame_main_button)
        
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
        font.setFamily("Comfortaa")
        font.setPointSize(11)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        font.setKerning(True)
        self.pushButton_create_character_2.setFont(font)
        
        self.pushButton_create_character_2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_2.setMouseTracking(False)
        
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
        font.setFamily("Comfortaa")
        font.setPointSize(12)
        font.setBold(False)
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
        font.setFamily("Comfortaa")
        font.setPointSize(14)
        font.setBold(True)
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
        self.gridLayout_9.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_9.setSpacing(0)
        self.gridLayout_9.setObjectName("gridLayout_9")
        
        self.scrollArea_characters_list = QtWidgets.QScrollArea(parent=self.main_characters_page)
        self.scrollArea_characters_list.setStyleSheet("""
			QScrollArea {
				background-color: transparent;
				color: rgb(227, 227, 227);
				border: none;
				padding-left: 25px;
                padding-right: 20px;
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
        self.frame_welcome_to.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_welcome_to.setObjectName("frame_welcome_to")
        self.frame_welcome_to.setStyleSheet("""
            QFrame#frame_welcome_to {
                background-color: rgba(255, 255, 255, 0.015);
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        
        self.gridLayout_6 = QtWidgets.QGridLayout(self.frame_welcome_to)
        self.gridLayout_6.setContentsMargins(32, 6, 32, 6)
        self.gridLayout_6.setObjectName("gridLayout_6")

        self.profile_container = QtWidgets.QWidget(parent=self.frame_welcome_to)
        self.profile_container.setObjectName("profile_container")
        self.profile_container.setStyleSheet("""
            QWidget#profile_container {
                background: transparent;
                background-color: transparent;
                border-radius: 8px;
            }
        """)
        
        self.profile_layout = QtWidgets.QHBoxLayout(self.profile_container)
        self.profile_layout.setContentsMargins(6, 6, 12, 6)
        self.profile_layout.setSpacing(8)
        self.profile_layout.setObjectName("profile_layout")

        self.user_avatar_label = QtWidgets.QLabel(parent=self.profile_container)
        self.user_avatar_label.setObjectName("user_avatar_label")
        self.user_avatar_label.setFixedSize(QtCore.QSize(54, 54))
        self.user_avatar_label.setStyleSheet("""
            QLabel#user_avatar_label {
                border: none;
                background: transparent;
                background-color: transparent;
            }
        """)
        self.profile_layout.addWidget(self.user_avatar_label)

        self.text_container = QtWidgets.QWidget(parent=self.profile_container)
        self.text_container.setObjectName("text_container")
        self.text_container.setStyleSheet("""
            QWidget#text_container {
                background: transparent;
                background-color: transparent;
                border: none;
            }
        """)
        
        self.text_layout = QtWidgets.QVBoxLayout(self.text_container)
        self.text_layout.setContentsMargins(0, 0, 0, 0)
        self.text_layout.setSpacing(2)
        
        self.text_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignVCenter)

        self.lbl_main_title = QtWidgets.QLabel(self.translations.get("main_button_2", "Main Hub"), parent=self.text_container)
        self.lbl_main_title.setObjectName("lbl_main_title")
        
        self.lbl_main_title.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        
        font_title = QtGui.QFont("Inter Tight", 14, QtGui.QFont.Weight.Bold)
        font_title.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lbl_main_title.setFont(font_title)
        self.lbl_main_title.setStyleSheet("""
            QLabel#lbl_main_title {
                color: rgba(255, 255, 255, 0.70);
                background: transparent;
                background-color: transparent;
                border: none;
            }
        """)
        
        self.welcome_label_2 = QtWidgets.QLabel("Good to see you, User", parent=self.text_container)
        self.welcome_label_2.setObjectName("welcome_label_2")
        
        self.welcome_label_2.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        
        font_sub = QtGui.QFont("Inter Tight Medium", 10)
        font_sub.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.welcome_label_2.setFont(font_sub)
        self.welcome_label_2.setStyleSheet("""
            QLabel#welcome_label_2 {
                color: rgba(255, 255, 255, 0.50);
                background: transparent;
                background-color: transparent;
                border: none;
            }
        """)

        self.text_layout.addWidget(self.lbl_main_title)
        self.text_layout.addWidget(self.welcome_label_2)
        self.profile_layout.addWidget(self.text_container)

        self.gridLayout_6.addWidget(self.profile_container, 0, 0, 1, 1)

        spacerItem_spacer = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_6.addItem(spacerItem_spacer, 0, 1, 1, 1)

        self.control_capsule = QtWidgets.QFrame(parent=self.frame_welcome_to)
        self.control_capsule.setObjectName("control_capsule")
        self.control_capsule.setMinimumSize(QtCore.QSize(148, 44))
        self.control_capsule.setMaximumSize(QtCore.QSize(148, 44))
        
        self.control_capsule.setStyleSheet("""
            QFrame#control_capsule {
                background-color: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 22px;
            }
        """)
        
        self.capsule_layout = QtWidgets.QHBoxLayout(self.control_capsule)
        self.capsule_layout.setContentsMargins(6, 0, 6, 0)
        self.capsule_layout.setSpacing(3)
        self.capsule_layout.setObjectName("capsule_layout")

        CAPSULE_BUTTON_STYLE = """
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 17px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
            }
        """

        self.btn_create_character_menu = QtWidgets.QPushButton(parent=self.control_capsule)
        self.btn_create_character_menu.setObjectName("btn_create_character_menu")
        self.btn_create_character_menu.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.btn_create_character_menu.setFixedSize(QtCore.QSize(34, 34))
        self.btn_create_character_menu.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_create_character_menu.setStyleSheet(CAPSULE_BUTTON_STYLE)
        icon_create = QtGui.QIcon("app/gui/icons/create_character.png") 
        self.btn_create_character_menu.setIcon(icon_create)
        self.btn_create_character_menu.setIconSize(QtCore.QSize(16, 16))
        self.capsule_layout.addWidget(self.btn_create_character_menu)

        self.btn_import_character_menu = QtWidgets.QPushButton(parent=self.control_capsule)
        self.btn_import_character_menu.setObjectName("btn_import_character_menu")
        self.btn_import_character_menu.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.btn_import_character_menu.setFixedSize(QtCore.QSize(34, 34))
        self.btn_import_character_menu.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_import_character_menu.setStyleSheet(CAPSULE_BUTTON_STYLE)
        icon_import = QtGui.QIcon("app/gui/icons/import.png")
        self.btn_import_character_menu.setIcon(icon_import)
        self.btn_import_character_menu.setIconSize(QtCore.QSize(15, 15))
        self.capsule_layout.addWidget(self.btn_import_character_menu)

        self.btn_new_folder_menu = QtWidgets.QPushButton(parent=self.control_capsule)
        self.btn_new_folder_menu.setObjectName("btn_new_folder_menu")
        self.btn_new_folder_menu.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.btn_new_folder_menu.setFixedSize(QtCore.QSize(34, 34))
        self.btn_new_folder_menu.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_new_folder_menu.setStyleSheet(CAPSULE_BUTTON_STYLE)
        icon_folder = QtGui.QIcon("app/gui/icons/add_folder.png") 
        self.btn_new_folder_menu.setIcon(icon_folder)
        self.btn_new_folder_menu.setIconSize(QtCore.QSize(16, 16))
        self.capsule_layout.addWidget(self.btn_new_folder_menu)

        self.gridLayout_6.addWidget(self.control_capsule, 0, 2, 1, 1)

        self.search_bar_menu = ModernSearchBar(parent=self.frame_welcome_to)
        self.search_bar_menu.setMinimumSize(QtCore.QSize(230, 44))
        self.search_bar_menu.setMaximumSize(QtCore.QSize(290, 44))
        
        self.lineEdit_search_character_menu = self.search_bar_menu.line_edit
        self.lineEdit_search_character_menu.setPlaceholderText("Search character...")
        
        self.gridLayout_6.addWidget(self.search_bar_menu, 0, 3, 1, 1)

        self.gridLayout_9.addWidget(self.frame_welcome_to, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.main_characters_page)
        
        self._BG       = "#070709"
        self._SURF1    = "#0B0B0F"
        self._SURF2    = "#121218"
        self._SURF3    = "#161622"
        self._TEXT     = "#DEDAD2"
        self._TEXT_S   = "#6F6B63"
        self._BORDER   = "rgba(255, 255, 255, 0.045)"
        self._BORDER_M = "rgba(255, 255, 255, 0.08)"
        
        self._BLUE     = "#4BB8FF"  
        self._BLUE_MUT = "rgba(75, 184, 255, 0.12)"
        self._BLUE_GLO = "rgba(75, 184, 255, 0.25)"
        self._BLUE_BRT = "#82CDFF"

        self._DANGER   = "#C44040"

        def mf(size, weight=QFont.Weight.Normal):
            f = QFont("Inter Tight", size, weight)
            f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
            return f

        f_title = mf(14, QFont.Weight.Bold)
        f_label = mf(8,  QFont.Weight.Bold)
        f_input = mf(10, QFont.Weight.Medium)
        f_btn   = mf(10, QFont.Weight.DemiBold)

        self.create_character_page = QtWidgets.QWidget()
        self.create_character_page.setObjectName("create_character_page")
        self.create_character_page.setStyleSheet(f"background-color: {self._BG};")
        
        self.layout_page_2 = QtWidgets.QHBoxLayout(self.create_character_page)
        self.layout_page_2.setContentsMargins(0, 0, 0, 0)
        self.layout_page_2.setSpacing(0)
        
        self.character_list_panel = QtWidgets.QWidget(self.create_character_page)
        self.character_list_panel.setFixedWidth(85)
        self.character_list_panel.setStyleSheet("""
            QWidget {
                background-color: rgba(12, 12, 15, 0.6);
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.05);
            }
        """)
        self.layout_character_list_panel = QtWidgets.QVBoxLayout(self.character_list_panel)
        self.layout_character_list_panel.setContentsMargins(9, 20, 9, 20)
        self.layout_character_list_panel.setSpacing(0)
        
        self.editor_character_list = QtWidgets.QListWidget(self.character_list_panel)
        self.editor_character_list.setObjectName("editor_character_list")
        self.editor_character_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.editor_character_list.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.editor_character_list.setSpacing(5)
        
        self.editor_character_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                border-radius: 28px; 
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
            QListWidget::item:selected {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QScrollBar:vertical {
                background-color: transparent; width: 0px; 
            }
            QToolTip {
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 13px; 
                font-family: 'Inter Tight SemiBold';
            }
        """)
        self.layout_character_list_panel.addWidget(self.editor_character_list)
        
        self.btn_create_new_character_editor = QtWidgets.QPushButton(self.character_list_panel)
        self.btn_create_new_character_editor.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_create_new_character_editor.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_create_new_character_editor.setToolTip("Create New Character")
        self.btn_create_new_character_editor.setFixedSize(56, 56)
        self.btn_create_new_character_editor.setText("+")
        self.btn_create_new_character_editor.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                color: rgba(255, 255, 255, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 28px;
                font-family: 'Inter Tight SemiBold';
                font-size: 26px;
                padding-bottom: 4px;
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 0.1); 
                color: white; 
                border: 1px solid rgba(255, 255, 255, 0.3); 
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
            }
        """)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addWidget(self.btn_create_new_character_editor, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout_character_list_panel.addLayout(btn_layout)
        
        self.layout_page_2.addWidget(self.character_list_panel)

        self.sidebar_container = QtWidgets.QWidget(self.create_character_page)
        self.sidebar_container.setObjectName("sidebar_container")
        self.sidebar_container.setFixedWidth(220)
        
        self.sidebar_container.setStyleSheet(
            f"QWidget#sidebar_container {{"
            f"  background-color: rgba(11, 11, 15, 0.4);"
            f"  border: none;"
            f"  border-right: 1px solid {self._BORDER};"
            f"}}"
        )

        self.sidebar_layout = QtWidgets.QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(8, 20, 8, 20)
        self.sidebar_layout.setSpacing(0)

        self.navigation_title = QtWidgets.QLabel(self.translations.get("navigation_lbl", "NAVIGATION"), self.sidebar_container)
        self.navigation_title.setFont(font_title_lbl)
        self.navigation_title.setObjectName("navigation_title")
        self.navigation_title.setStyleSheet(
            f"QLabel#navigation_title {{"
            f"  color: {self._TEXT_S};"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 10px;"
            f"  text-transform: uppercase;"
            f"  letter-spacing: 1.5px;"
            f"  padding-left: 14px;"
            f"  margin-bottom: 12px;"
            f"  background: transparent;"
            f"  border: none;"
            f"}}"
        )
        self.sidebar_layout.addWidget(self.navigation_title)

        self.anchor_menu_building = QtWidgets.QListWidget(self.sidebar_container)
        self.anchor_menu_building.setObjectName("anchor_menu_building")
        self.anchor_menu_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.anchor_menu_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.anchor_menu_building.setIconSize(QtCore.QSize(16, 16))
        
        self.anchor_menu_building.setStyleSheet(
            f"QListWidget#anchor_menu_building {{"
            f"  background-color: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#anchor_menu_building::item {{"
            f"  color: {self._TEXT_S};"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 13px;"
            f"  padding: 10px 14px;"
            f"  border-radius: 8px;"
            f"  margin-bottom: 4px;"
            f"  border: 1px solid transparent;"
            f"}}"
            f"QListWidget#anchor_menu_building::item:hover {{"
            f"  background-color: rgba(255, 255, 255, 0.04);"
            f"  color: {self._TEXT};"
            f"}}"
            f"QListWidget#anchor_menu_building::item:selected {{"
            f"  background-color: rgba(255, 255, 255, 0.08);"
            f"  border: 1px solid rgba(255, 255, 255, 0.15);"
            f"  color: #FFFFFF;"
            f"}}"
        )
        self.sidebar_layout.addWidget(self.anchor_menu_building)
        
        self.item_general_info = QtWidgets.QListWidgetItem("General Info")
        self.item_personality = QtWidgets.QListWidgetItem("Personality & Scenario")
        self.item_dialogues = QtWidgets.QListWidgetItem("Dialogues")
        self.item_advanced = QtWidgets.QListWidgetItem("Advanced & Lore")
        self.item_variables = QtWidgets.QListWidgetItem("Variables & State")
        self.item_export = QtWidgets.QListWidgetItem("Export / Utils")

        self.item_general_info.setIcon(QtGui.QIcon("app/gui/icons/information.png"))
        self.item_personality.setIcon(QtGui.QIcon("app/gui/icons/personas.png"))
        self.item_dialogues.setIcon(QtGui.QIcon("app/gui/icons/chat.png"))
        self.item_advanced.setIcon(QtGui.QIcon("app/gui/icons/gpu.png"))
        self.item_variables.setIcon(QtGui.QIcon("app/gui/icons/variable.png"))
        self.item_export.setIcon(QtGui.QIcon("app/gui/icons/export.png"))

        self.anchor_menu_building.addItem(self.item_general_info)
        self.anchor_menu_building.addItem(self.item_personality)
        self.anchor_menu_building.addItem(self.item_dialogues)
        self.anchor_menu_building.addItem(self.item_advanced)
        self.anchor_menu_building.addItem(self.item_variables)
        self.anchor_menu_building.addItem(self.item_export)
            
        self.layout_page_2.addWidget(self.sidebar_container)

        self.right_container = QtWidgets.QWidget(self.create_character_page)
        self.right_layout = QtWidgets.QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)

        self.scrollArea_character_building = QtWidgets.QScrollArea(self.right_container)
        self.scrollArea_character_building.setWidgetResizable(True)
        self.scrollArea_character_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_character_building.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 10px 0px 10px 0px; }"
            f"QScrollBar::handle:vertical {{ background: {self._BORDER_M}; min-height: 30px; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {self._TEXT_S}; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; border: none; }"
        )

        self.scrollAreaWidgetContents_character_building = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_building.setStyleSheet("background: transparent;")
        
        self.cards_layout = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_character_building)
        self.cards_layout.setContentsMargins(40, 40, 40, 80)
        self.cards_layout.setSpacing(24)

        def create_glass_card_building(title_text):
            card = QtWidgets.QFrame()
            card.setObjectName("IGCreationCard")
            card.setStyleSheet(
                f"QFrame#IGCreationCard {{"
                f"  background-color: {self._SURF1};"
                f"  border: 1px solid {self._BORDER};"
                f"  border-radius: 12px;"
                f"}}"
                f"QFrame#IGCreationCard QLabel {{ border: none; background: transparent; }}"
            )
            layout = QtWidgets.QVBoxLayout(card)
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setSpacing(14)
            
            title = QtWidgets.QLabel(title_text)
            title.setStyleSheet("font-family: 'Inter Tight SemiBold'; font-size: 18px; color: rgba(255, 255, 255, 0.95); border: none; background: transparent;")
            layout.addWidget(title)
            return card, layout

        input_style = (
            f"QLineEdit, QTextEdit {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 8px;"
            f"  padding: 10px;"
            f"  selection-background-color: {self._BLUE_MUT};"
            f"}}"
            f"QLineEdit:focus, QTextEdit:focus {{"
            f"  border-color: {self._BORDER_M};"
            f"  background-color: {self._SURF3};"
            f"}}"
        )

        # Card 1: General Info
        self.general_info_text = self.translations.get("character_creator_title_general_info", "General Information")
        self.card_general, layout_gen = create_glass_card_building(self.general_info_text)
        
        prov_lbl = QtWidgets.QLabel(self.translations.get("image_gen_provider", "PROVIDER"))
        prov_lbl.setFont(f_label)
        prov_lbl.setStyleSheet(f"color: {self._TEXT_S}; letter-spacing: 0.8px;")
        layout_gen.addWidget(prov_lbl)

        grid_providers = QtWidgets.QGridLayout()
        grid_providers.setSpacing(10)
        grid_providers.setContentsMargins(0, 5, 0, 10)

        providers_data = [
            ("Local LLM", "Local LLM", "app/gui/icons/local_llm.png"),
            ("OpenAI / Custom", "Open AI", "app/gui/icons/openai.png"),
            ("Anthropic Claude", "Anthropic", "app/gui/icons/anthropic.png"),
            ("Google Gemini", "Google Gemini", "app/gui/icons/gemini.png"),
            ("DeepSeek", "DeepSeek", "app/gui/icons/deepseek.png"),
            ("xAI Grok", "Grok", "app/gui/icons/grok.png"),
            ("Qwen", "Qwen", "app/gui/icons/qwen.png"),
            ("Z.AI", "Z.AI", "app/gui/icons/zai.png"),
            ("Mistral AI", "Mistral AI", "app/gui/icons/mistralai.png"),
            ("OpenRouter", "OpenRouter", "app/gui/icons/openrouter.png")
        ]

        self.provider_group = QtWidgets.QButtonGroup(self.create_character_page)
        self.provider_group.setExclusive(True)

        cols = 3

        for i, (name, value, icon_path) in enumerate(providers_data):
            btn = QtWidgets.QPushButton(f"  {name}")
            btn.setIcon(QtGui.QIcon(icon_path))
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setCheckable(True)
            btn.setFixedHeight(45)
            btn.setFont(f_btn)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{"
                f"  background-color: {self._SURF2};"
                f"  color: {self._TEXT_S};"
                f"  border: 1px solid {self._BORDER};"
                f"  border-radius: 8px;"
                f"  text-align: left;"
                f"  padding-left: 14px;"
                f"  font-family: 'Inter Tight SemiBold';"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {self._SURF3};"
                f"  color: {self._TEXT};"
                f"  border-color: {self._BORDER_M};"
                f"}}"
                f"QPushButton:checked {{"
                f"  background-color: {self._BLUE_MUT};"
                f"  border: 1px solid {self._BLUE_GLO};"
                f"  color: {self._BLUE_BRT};"
                f"}}"
            )
            btn.setProperty("provider_value", value)
            self.provider_group.addButton(btn)
            
            row = i // cols
            col = i % cols
            grid_providers.addWidget(btn, row, col)

        self.provider_group.buttons()[0].setChecked(True)
        
        layout_gen.addLayout(grid_providers)

        self.label_character_provider_status = QtWidgets.QLabel()
        self.label_character_provider_status.setFont(font_input)
        self.label_character_provider_status.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        layout_gen.addWidget(self.label_character_provider_status)

        self.character_model_override_label = QtWidgets.QLabel("Model override (optional)")
        self.character_model_override_label.setFont(font_label)
        self.character_model_override_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.comboBox_character_model_override = QtWidgets.QComboBox()
        self.comboBox_character_model_override.setEditable(True)
        self.comboBox_character_model_override.setFont(font_input)
        self.comboBox_character_model_override.setFixedHeight(40)
        self.comboBox_character_model_override.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.comboBox_character_model_override.addItem("Use provider default", "")
        self.comboBox_character_model_override.lineEdit().setPlaceholderText("Use provider default")
        layout_gen.addWidget(self.character_model_override_label)
        layout_gen.addWidget(self.comboBox_character_model_override)
        layout_gen.addSpacing(10)

        row_avatar_name = QtWidgets.QHBoxLayout()
        row_avatar_name.setSpacing(20)
        
        self.character_image_building_label = QtWidgets.QLabel("Avatar")
        self.pushButton_import_character_image = QtWidgets.QPushButton()
        self.pushButton_import_character_image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_import_character_image.setFixedSize(100, 100)
        self.pushButton_import_character_image.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_import_character_image.setStyleSheet(
            f"QPushButton {{ background-color: {self._SURF2}; border: 2px dashed {self._BORDER_M}; border-radius: 12px; }}"
            f"QPushButton:hover {{ border: 2px dashed {self._BLUE}; background-color: {self._SURF3}; }}"
        )
        icon_image_import = QtGui.QIcon()
        icon_image_import.addPixmap(QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_image.setIcon(icon_image_import)
        self.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
        
        avatar_vbox = QtWidgets.QVBoxLayout()
        avatar_vbox.addWidget(self.pushButton_import_character_image)
        avatar_vbox.addStretch()
        row_avatar_name.addLayout(avatar_vbox)

        vbox_name = QtWidgets.QVBoxLayout()
        self.character_name_building_label = QtWidgets.QLabel("Character Name")
        self.character_name_building_label.setFont(font_label)
        self.character_name_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        
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
        self.character_description_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 10px;")
        
        self.textEdit_character_description_building = AutoResizingTextEdit()
        self.textEdit_character_description_building.setFont(font_input)
        self.textEdit_character_description_building.setStyleSheet(input_style)
        
        layout_gen.addWidget(self.character_description_building_label)
        layout_gen.addWidget(self.textEdit_character_description_building)
        self.cards_layout.addWidget(self.card_general)

        # Card 2: Personality
        self.personality_title = self.translations.get("character_creator_title_personality", "Personality & Scenario")
        self.card_pers, layout_pers = create_glass_card_building(self.personality_title)
        
        self.character_personality_building_label = QtWidgets.QLabel("Personality")
        self.character_personality_building_label.setFont(font_label)
        self.character_personality_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.textEdit_character_personality_building = AutoResizingTextEdit()
        self.textEdit_character_personality_building.setFont(font_input)
        self.textEdit_character_personality_building.setStyleSheet(input_style)
        
        self.character_scenario_building_label = QtWidgets.QLabel("Scenario")
        self.character_scenario_building_label.setFont(font_label)
        self.character_scenario_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 10px;")
        self.textEdit_scenario = AutoResizingTextEdit()
        self.textEdit_scenario.setFont(font_input)
        self.textEdit_scenario.setStyleSheet(input_style)
        
        layout_pers.addWidget(self.character_personality_building_label)
        layout_pers.addWidget(self.textEdit_character_personality_building)
        layout_pers.addWidget(self.character_scenario_building_label)
        layout_pers.addWidget(self.textEdit_scenario)
        self.cards_layout.addWidget(self.card_pers)

        # Card 3: Dialogues
        self.dialogues_title = self.translations.get("character_creator_title_dialogues", "Dialogues & Greetings")
        self.card_dial, layout_dial = create_glass_card_building(self.dialogues_title)
        
        self.first_message_building_label = QtWidgets.QLabel("First Message")
        self.first_message_building_label.setFont(font_label)
        self.first_message_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.textEdit_first_message_building = AutoResizingTextEdit()
        self.textEdit_first_message_building.setFont(font_input)
        self.textEdit_first_message_building.setStyleSheet(input_style)
        
        self.alternate_greetings_building_label = QtWidgets.QLabel("Alternate Greetings")
        self.alternate_greetings_building_label.setFont(font_label)
        self.alternate_greetings_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 10px;")
        self.textEdit_alternate_greetings = AutoResizingTextEdit()
        self.textEdit_alternate_greetings.setFont(font_input)
        self.textEdit_alternate_greetings.setStyleSheet(input_style)
        
        self.example_messages_building_label = QtWidgets.QLabel("Example Messages")
        self.example_messages_building_label.setFont(font_label)
        self.example_messages_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 10px;")
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

        # Card 4: Advanced Settings & Combos
        self.advanced_settings_title = self.translations.get("character_creator_title_advanced", "Advanced Settings & Lore")
        self.card_adv, layout_adv = create_glass_card_building(self.advanced_settings_title)
        
        row_combos = QtWidgets.QHBoxLayout()
        row_combos.setSpacing(20)
        
        combo_style = f"""
            QComboBox {{
                background-color: {self._SURF2}; color: {self._TEXT};
                border: 1px solid {self._BORDER}; border-radius: 8px; padding: 10px 15px;
            }}
            QComboBox:hover {{ border: 1px solid {self._BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid {self._TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {self._SURF3}; color: {self._TEXT}; border: 1px solid {self._BORDER_M};
                border-radius: 8px; selection-background-color: {self._SURF2}; outline: none; padding: 4px;
            }}
            QComboBox QAbstractItemView::item {{ padding: 8px; border-radius: 4px; }}
        """

        vbox_persona = QtWidgets.QVBoxLayout()
        self.user_persona_building_label = QtWidgets.QLabel("User Persona")
        self.user_persona_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.comboBox_user_persona_building = QtWidgets.QComboBox()
        self.comboBox_user_persona_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_user_persona_building.setFont(font_input)
        self.comboBox_user_persona_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_user_persona_building.setFixedHeight(40)
        self.comboBox_user_persona_building.setStyleSheet(combo_style)
        vbox_persona.addWidget(self.user_persona_building_label)
        vbox_persona.addWidget(self.comboBox_user_persona_building)
        
        vbox_prompt = QtWidgets.QVBoxLayout()
        self.system_prompt_building_label = QtWidgets.QLabel("System Prompt")
        self.system_prompt_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.comboBox_system_prompt_building = QtWidgets.QComboBox()
        self.comboBox_system_prompt_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_system_prompt_building.setFont(font_input)
        self.comboBox_system_prompt_building.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_system_prompt_building.setFixedHeight(40)
        self.comboBox_system_prompt_building.setStyleSheet(combo_style)
        vbox_prompt.addWidget(self.system_prompt_building_label)
        vbox_prompt.addWidget(self.comboBox_system_prompt_building)

        vbox_lore = QtWidgets.QVBoxLayout()
        self.lorebook_building_label = QtWidgets.QLabel("Lorebook")
        self.lorebook_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none;")
        self.comboBox_lorebook_building = QtWidgets.QComboBox()
        self.comboBox_lorebook_building.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_lorebook_building.setFont(font_input)
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
        self.creator_notes_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 15px;")
        self.textEdit_creator_notes = AutoResizingTextEdit()
        self.textEdit_creator_notes.setFont(font_input)
        self.textEdit_creator_notes.setStyleSheet(input_style)
        
        self.character_version_building_label = QtWidgets.QLabel("Card Version")
        self.character_version_building_label.setFont(font_label)
        self.character_version_building_label.setStyleSheet(f"color: {self._TEXT_S}; background: transparent; border: none; margin-top: 15px;")
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

        # Card 5: Variables & State
        self.character_creator_title_custom_variable = self.translations.get("character_creator_title_custom_variable", "Variables & State")
        self.card_variables, layout_variables = create_glass_card_building(self.character_creator_title_custom_variable)
        
        variables_desc_label = QtWidgets.QLabel(self.translations.get("character_creator_desc_custom_variable", "Configure custom state variables (like trust, gold, or inventory) that the character can dynamically track during single chat sessions."))
        variables_desc_label.setFont(font_input)
        variables_desc_label.setStyleSheet(f"color: {self._TEXT_S}; margin-bottom: 10px; border: none; background: transparent;")
        variables_desc_label.setWordWrap(True)
        layout_variables.addWidget(variables_desc_label)

        preset_row_layout = QtWidgets.QHBoxLayout()
        preset_row_layout.setSpacing(10)
        
        lbl_preset = QtWidgets.QLabel(self.translations.get("var_editor_preset_label", "LOAD PRESET:"))
        lbl_preset.setFont(font_label)
        lbl_preset.setStyleSheet(f"color: {self._TEXT_S}; border: none; background: transparent;")
        
        self.combo_variables_presets = QtWidgets.QComboBox()
        self.combo_variables_presets.setFont(font_input)
        self.combo_variables_presets.setFixedHeight(36)
        self.combo_variables_presets.setStyleSheet(combo_style)
        self.combo_variables_presets.addItems([
            self.translations.get("var_preset_custom", "Custom (None)"),
            self.translations.get("var_preset_romance", "Romance & Relationships (Affection & Trust)"),
            self.translations.get("var_preset_rpg", "RPG Adventure (HP, Mana, Gold & Inventory)"),
            self.translations.get("var_preset_survival", "Tamagotchi (Hunger, Energy & Mood)"),
            self.translations.get("var_preset_yandere", "Anime: Yandere Obsession (Obsession & Sanity)"),
            self.translations.get("var_preset_shonen", "Anime: Shonen Battle (Spirit, Will & Demon)"),
            self.translations.get("var_preset_maid", "Anime: Maid & Master (Loyalty, Moe & Cheekiness)"),
            self.translations.get("var_preset_chuuni", "Anime: Chuunibyou Delusions (Delusion & Cringe)"),
            self.translations.get("var_preset_tsundere", "Anime: Tsundere Classic (Tsun & Dere)"),
            self.translations.get("var_preset_kuudere", "Anime: Silent Kuudere (Suppression & Connection)"),
            self.translations.get("var_preset_dandere", "Anime: Shy Dandere (Shyness & Attachment)"),
            self.translations.get("var_preset_himedere", "Anime: Noble Himedere (Entitlement & Vulnerability)")
        ])
        
        self.btn_apply_variables_preset = QtWidgets.QPushButton(self.translations.get("var_editor_apply_preset_btn", "Apply"))
        self.btn_apply_variables_preset.setFont(f_btn)
        self.btn_apply_variables_preset.setFixedHeight(36)
        self.btn_apply_variables_preset.setFixedWidth(80)
        self.btn_apply_variables_preset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply_variables_preset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_apply_variables_preset.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._BLUE};"
            f"  border: 1px solid {self._BLUE_GLO};"
            f"  border-radius: 8px;"
            f"  font-family: 'Inter Tight SemiBold';"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self._SURF3};"
            f"  border-color: {self._BLUE};"
            f"  color: {self._BLUE_BRT};"
            f"}}"
        )
        self.btn_apply_variables_preset.clicked.connect(self.apply_selected_variables_preset)
        
        preset_row_layout.addWidget(lbl_preset)
        preset_row_layout.addWidget(self.combo_variables_presets, 1)
        preset_row_layout.addWidget(self.btn_apply_variables_preset)
        layout_variables.addLayout(preset_row_layout)
        layout_variables.addSpacing(10)

        self.variables_rows_container_widget = QtWidgets.QWidget()
        self.variables_rows_container_widget.setStyleSheet("background: transparent; border: none;")
        self.variables_rows_layout = QtWidgets.QVBoxLayout(self.variables_rows_container_widget)
        self.variables_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.variables_rows_layout.setSpacing(12)
        layout_variables.addWidget(self.variables_rows_container_widget)

        self.active_variable_widgets = []

        self.btn_add_variable_row = QtWidgets.QPushButton(self.translations.get("character_creator_btn_add_custom_variable", "+ Add Custom Variable"))
        self.btn_add_variable_row.setFont(f_btn)
        self.btn_add_variable_row.setFixedHeight(40)
        self.btn_add_variable_row.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_variable_row.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_add_variable_row.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {self._SURF2};"
            f"  color: {self._BLUE};"
            f"  border: 1px dashed {self._BLUE_GLO};"
            f"  border-radius: 8px;"
            f"  font-family: 'Inter Tight SemiBold';"
            f"}}"
            f"QPushButton:hover {{"
            f"  background-color: {self._SURF3};"
            f"  border-color: {self._BLUE};"
            f"  color: {self._BLUE_BRT};"
            f"}}"
        )
        self.btn_add_variable_row.clicked.connect(lambda: self.add_blank_variable_row())
        layout_variables.addWidget(self.btn_add_variable_row)
        
        self.cards_layout.addWidget(self.card_variables)

        # Card 6: Import & Export
        self.export_tools_title = self.translations.get("character_creator_title_export", "Export & Tools")
        self.card_export, layout_export = create_glass_card_building(self.export_tools_title)
        
        row_tools = QtWidgets.QHBoxLayout()
        row_tools.setSpacing(15)
        
        btn_style_tools = f"""
            QPushButton {{
                background-color: {self._SURF2};
                color: {self._TEXT}; 
                border: 1px solid {self._BORDER};
                border-radius: 8px; padding: 12px; font-weight: bold;
                font-family: 'Inter Tight SemiBold';
            }}
            QPushButton:hover {{ background-color: {self._SURF3}; border: 1px solid {self._BORDER_M}; color: white; }}
        """

        self.pushButton_import_character_card = QtWidgets.QPushButton("Import Character Card")
        self.pushButton_import_character_card.setFont(f_label)
        self.pushButton_import_character_card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_import_character_card.setStyleSheet(btn_style_tools)
        self.pushButton_import_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        self.pushButton_export_character_card = QtWidgets.QPushButton("Export Character Card")
        self.pushButton_export_character_card.setFont(f_label)
        self.pushButton_export_character_card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_export_character_card.setStyleSheet(btn_style_tools)
        self.pushButton_export_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        
        self.pushButton_clean_character_card = QtWidgets.QPushButton("Clear All Fields")
        self.pushButton_clean_character_card.setFont(f_label)
        self.pushButton_clean_character_card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_clean_character_card.setStyleSheet(btn_style_tools + f"QPushButton:hover {{ border: 1px solid {self._DANGER}; color: #ff6b6b; }}")
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
            4: self.card_variables,
            5: self.card_export
        }

        self.scrollArea_character_building.setWidget(self.scrollAreaWidgetContents_character_building)
        self.right_layout.addWidget(self.scrollArea_character_building)
        
        # --- FOOTER TOOLBAR ---
        self.frame_bottom_character_creation = QtWidgets.QFrame(self.right_container)
        self.frame_bottom_character_creation.setFixedHeight(70)
        self.frame_bottom_character_creation.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {self._SURF1};"
            f"  border-top: 1px solid {self._BORDER};"
            f"}}"
        )
        shadow_footer = QGraphicsDropShadowEffect()
        shadow_footer.setBlurRadius(20)
        shadow_footer.setColor(QColor(0, 0, 0, 150))
        shadow_footer.setOffset(0, -5)
        self.frame_bottom_character_creation.setGraphicsEffect(shadow_footer)
        self.bottom_layout = QtWidgets.QHBoxLayout(self.frame_bottom_character_creation)
        self.bottom_layout.setContentsMargins(40, 0, 40, 0)
        self.bottom_layout.setSpacing(15)
        
        self.total_tokens_building_label = QtWidgets.QLabel("Total Tokens: 0")
        self.total_tokens_building_label.setFont(font_label)
        self.total_tokens_building_label.setStyleSheet(f"font-family: 'Inter Tight SemiBold'; font-size: 15px; color: {self._TEXT_S}; border: none; background: transparent;")
        
        self.pushButton_preview_prompt = QtWidgets.QPushButton("Preview Raw")
        self.pushButton_preview_prompt.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_preview_prompt.setFont(font_label)
        self.pushButton_preview_prompt.setFixedSize(130, 42)
        self.pushButton_preview_prompt.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_preview_prompt.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {self._TEXT_S};"
            f"  border-radius: 8px;"
            f"  border: 1px dashed {self._BORDER_M};"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{ background-color: {self._SURF2}; color: white; border-style: solid; border-color: {self._BORDER_M}; }}"
        )

        self.pushButton_create_character_3 = QtWidgets.QPushButton("Create Character")
        self.pushButton_create_character_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_create_character_3.setFont(font_label)
        self.pushButton_create_character_3.setFixedSize(180, 42)
        self.pushButton_create_character_3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_3.setStyleSheet(
            f"QPushButton {{"
            f"  background: {self._BLUE_MUT};"
            f"  border: 1px solid {self._BLUE_GLO};"
            f"  border-radius: 10px;"
            f"  color: {self._BLUE};"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 14px;"
            f"  font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: rgba(75, 184, 255, 0.25);"
            f"  border-color: rgba(75, 184, 255, 0.55);"
            f"  color: {self._BLUE_BRT};"
            f"}}"
        )

        self.bottom_layout.addWidget(self.total_tokens_building_label)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.pushButton_preview_prompt)
        self.bottom_layout.addWidget(self.pushButton_create_character_3)
        self.right_layout.addWidget(self.frame_bottom_character_creation)
        self.layout_page_2.addWidget(self.right_container)
        self.stackedWidget.addWidget(self.create_character_page)

        self.charactersgateway_page = QtWidgets.QWidget()
        self.charactersgateway_page.setObjectName("charactersgateway_page")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.charactersgateway_page)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(30, 25, 30, 25)
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

        self.gateway_main_layout = QtWidgets.QHBoxLayout()
        self.gateway_main_layout.setContentsMargins(0, 0, 0, 0)
        self.gateway_main_layout.setSpacing(20)
        self.gateway_main_layout.setObjectName("gateway_main_layout")

        self.gateway_nav_rail = QtWidgets.QListWidget(parent=self.charactersgateway_page)
        self.gateway_nav_rail.setFixedWidth(220)
        self.gateway_nav_rail.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.gateway_nav_rail.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.gateway_nav_rail.setIconSize(QtCore.QSize(18, 18))
        self.gateway_nav_rail.setObjectName("gateway_nav_rail")
        
        self.gateway_nav_rail.setStyleSheet("""
            QListWidget#gateway_nav_rail {
                background: rgba(11, 11, 15, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
                outline: none;
                padding: 10px;
            }
            QListWidget#gateway_nav_rail::item {
                color: #6F6B63;
                font-family: 'Inter Tight SemiBold';
                font-size: 13px;
                padding: 12px 14px;
                border-radius: 10px;
                margin-bottom: 6px;
                border: 1px solid transparent;
            }
            QListWidget#gateway_nav_rail::item:hover {
                background-color: rgba(255, 255, 255, 0.04);
                color: #DEDAD2;
            }
            QListWidget#gateway_nav_rail::item:selected {
                background-color: rgba(75, 184, 255, 0.12);
                border: 1px solid rgba(75, 184, 255, 0.25);
                color: #82CDFF;
                font-weight: bold;
            }
        """)

        item_soul = QtWidgets.QListWidgetItem("Soul Gateway")
        item_chub = QtWidgets.QListWidgetItem("Chub AI Hub")
        item_lore = QtWidgets.QListWidgetItem("World Lorebooks")
        item_scenes = QtWidgets.QListWidgetItem("Soul Stage Scenarios")

        self.gateway_nav_rail.addItem(item_soul)
        self.gateway_nav_rail.addItem(item_chub)
        self.gateway_nav_rail.addItem(item_lore)
        self.gateway_nav_rail.addItem(item_scenes)

        self.gateway_main_layout.addWidget(self.gateway_nav_rail)

        self.gateway_stacked_widget = QtWidgets.QStackedWidget(parent=self.charactersgateway_page)
        self.gateway_stacked_widget.setStyleSheet("background: transparent; border: none;")
        self.gateway_stacked_widget.setObjectName("gateway_stacked_widget")

        # --- Curated (Soul Gateway) ---
        self.page_soul = QtWidgets.QWidget()
        self.layout_page_soul = QtWidgets.QVBoxLayout(self.page_soul)
        self.layout_page_soul.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_soul_gateway = QtWidgets.QScrollArea(self.page_soul)
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
        self.scrollAreaWidgetContents_soul.setStyleSheet("background-color: transparent;")
        self.scrollArea_soul_gateway.setWidget(self.scrollAreaWidgetContents_soul)
        self.layout_page_soul.addWidget(self.scrollArea_soul_gateway)
        self.gateway_stacked_widget.addWidget(self.page_soul)

        # --- Public (Chub AI) ---
        self.page_chub = QtWidgets.QWidget()
        self.layout_page_chub = QtWidgets.QVBoxLayout(self.page_chub)
        self.layout_page_chub.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_character_card = QtWidgets.QScrollArea(self.page_chub)
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
        self.scrollAreaWidgetContents_character_card.setStyleSheet("background-color: transparent;")
        self.scrollArea_character_card.setWidget(self.scrollAreaWidgetContents_character_card)
        self.layout_page_chub.addWidget(self.scrollArea_character_card)
        self.gateway_stacked_widget.addWidget(self.page_chub)

        # --- World Lorebooks ---
        self.page_lore = QtWidgets.QWidget()
        self.layout_page_lore = QtWidgets.QVBoxLayout(self.page_lore)
        self.layout_page_lore.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_lorebooks = QtWidgets.QScrollArea(self.page_lore)
        self.scrollArea_lorebooks.setWidgetResizable(True)
        self.scrollArea_lorebooks.setObjectName("scrollArea_lorebooks")
        self.scrollArea_lorebooks.setStyleSheet("""
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
        self.scrollAreaWidgetContents_lorebooks = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_lorebooks.setStyleSheet("background-color: transparent;")
        self.scrollArea_lorebooks.setWidget(self.scrollAreaWidgetContents_lorebooks)
        self.layout_page_lore.addWidget(self.scrollArea_lorebooks)
        self.gateway_stacked_widget.addWidget(self.page_lore)

        # --- Soul Stage Scenarios ---
        self.page_scenes = QtWidgets.QWidget()
        self.layout_page_scenes = QtWidgets.QVBoxLayout(self.page_scenes)
        self.layout_page_scenes.setContentsMargins(0, 0, 0, 0)
        self.scrollArea_scenes = QtWidgets.QScrollArea(self.page_scenes)
        self.scrollArea_scenes.setWidgetResizable(True)
        self.scrollArea_scenes.setObjectName("scrollArea_scenes")
        self.scrollArea_scenes.setStyleSheet("""
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
        self.scrollAreaWidgetContents_scenes = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_scenes.setStyleSheet("background-color: transparent;")
        self.scrollArea_scenes.setWidget(self.scrollAreaWidgetContents_scenes)
        self.layout_page_scenes.addWidget(self.scrollArea_scenes)
        self.gateway_stacked_widget.addWidget(self.page_scenes)

        self.gateway_main_layout.addWidget(self.gateway_stacked_widget, 1)
        self.verticalLayout_3.addLayout(self.gateway_main_layout)

        self.gateway_nav_rail.currentRowChanged.connect(self.gateway_stacked_widget.setCurrentIndex)
        self.stackedWidget.addWidget(self.charactersgateway_page)
        
        # ====================== Options Page ======================
        self.options_page = QtWidgets.QWidget()
        self.options_page.setObjectName("options_page")
        self.options_page.setStyleSheet("background: transparent;")

        self.options_sidebar_title_text = self.translations.get("options_sidebar_title", "SETTINGS")
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

        self.gridLayout = QtWidgets.QGridLayout(self.options_page)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        
        self.options_container = QtWidgets.QWidget()
        self.layout_options = QtWidgets.QHBoxLayout(self.options_container)
        self.layout_options.setContentsMargins(0, 0, 0, 0)
        self.layout_options.setSpacing(0)

        self.options_sidebar_container = QtWidgets.QWidget(self.options_page)
        self.options_sidebar_container.setObjectName("options_sidebar_container")
        self.options_sidebar_container.setFixedWidth(230)
        
        self.options_sidebar_container.setStyleSheet(
            f"QWidget#options_sidebar_container {{"
            f"  background-color: rgba(11, 11, 15, 0.4);"
            f"  border: none;"
            f"  border-right: 1px solid rgba(255, 255, 255, 0.045);"
            f"}}"
        )

        self.options_sidebar_layout = QtWidgets.QVBoxLayout(self.options_sidebar_container)
        self.options_sidebar_layout.setContentsMargins(8, 20, 8, 20)
        self.options_sidebar_layout.setSpacing(0)

        self.options_sidebar_title_lbl = QtWidgets.QLabel(self.options_sidebar_title_text, self.options_sidebar_container)
        self.options_sidebar_title_lbl.setObjectName("options_sidebar_title_lbl")
        self.options_sidebar_title_lbl.setFont(font_title_lbl)
        self.options_sidebar_title_lbl.setStyleSheet(
            f"QLabel#options_sidebar_title_lbl {{"
            f"  color: #6F6B63;"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 10px;"
            f"  text-transform: uppercase;"
            f"  letter-spacing: 1.5px;"
            f"  padding-left: 14px;"
            f"  margin-bottom: 12px;"
            f"  background: transparent;"
            f"  border: none;"
            f"}}"
        )
        self.options_sidebar_layout.addWidget(self.options_sidebar_title_lbl)

        self.options_menu = QtWidgets.QListWidget(self.options_sidebar_container)
        self.options_menu.setObjectName("options_menu")
        self.options_menu.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.options_menu.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.options_menu.setIconSize(QtCore.QSize(16, 16))

        self.options_menu.setStyleSheet(
            f"QListWidget#options_menu {{"
            f"  background-color: transparent;"
            f"  border: none;"
            f"  outline: none;"
            f"}}"
            f"QListWidget#options_menu::item {{"
            f"  color: #6F6B63;"
            f"  font-family: 'Inter Tight SemiBold';"
            f"  font-size: 13px;"
            f"  padding: 10px 14px;"
            f"  border-radius: 8px;"
            f"  margin-bottom: 4px;"
            f"  border: 1px solid transparent;"
            f"}}"
            f"QListWidget#options_menu::item:hover {{"
            f"  background-color: rgba(255, 255, 255, 0.04);"
            f"  color: #DEDAD2;"
            f"}}"
            f"QListWidget#options_menu::item:selected {{"
            f"  background-color: rgba(255, 255, 255, 0.08);"
            f"  border: 1px solid rgba(255, 255, 255, 0.15);"
            f"  color: #FFFFFF;"
            f"}}"
        )
        self.options_sidebar_layout.addWidget(self.options_menu)
        
        tab_data = [
            (self.translations.get("settings_ai_group", "AI SETTINGS"), None, None),
            (self.translations.get("settings_api_providers", "   API & Providers"), "app/gui/icons/system.png", "configuration_tab"),
            (self.translations.get("settings_voice", "   Voice Settings"), "app/gui/icons/tts_logo/elevenlabs.png", "voice_settings_tab"),
            (self.translations.get("settings_llm", "   LLM Settings"), "app/gui/icons/ai.png", "llm_tab"),
            (self.translations.get("settings_image_generation", "   Image Generation"), "app/gui/icons/background_icon.png", "image_generation_page"),
            (self.translations.get("settings_integrations", "   Integrations"), "app/gui/icons/discord.png", "integrations_page"),
            (self.translations.get("settings_system_ui", "System & UI"), "app/gui/icons/config.png", "system_tab"),
            (self.translations.get("settings_sow_modules", "SoW Modules"), "app/gui/icons/tools.png", "sow_system_tab"),
            (self.translations.get("settings_tool_calling", "Tool Calling & MCP"), "app/gui/icons/modules.png", "tools_tab"),
        ]

        for name, icon_path, tab_index in tab_data:
            item = QtWidgets.QListWidgetItem(name)
            if icon_path:
                item.setIcon(QtGui.QIcon(icon_path))
            if tab_index is None:
                item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                item.setForeground(QtGui.QColor("#A8A39A"))
            else:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, tab_index)
            self.options_menu.addItem(item)
            
        self.layout_options.addWidget(self.options_sidebar_container)

        self.tabWidget_options = QtWidgets.QStackedWidget(self.options_page)
        self.tabWidget_options.setStyleSheet("background: transparent; border: none;")
        self.layout_options.addWidget(self.tabWidget_options)

        def select_options_tab(item):
            page_name = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if page_name:
                self.tabWidget_options.setCurrentWidget(getattr(self, page_name))

        self.options_menu.currentItemChanged.connect(
            lambda item, _previous: select_options_tab(item) if item else None
        )

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

        def create_section_header(title_text):
            header_layout = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(title_text)
            lbl.setFont(font_label)
            lbl.setStyleSheet("color: #8ab4f8; font-weight: bold; letter-spacing: 1px;")
            
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            line.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); margin-top: 2px;")
            
            header_layout.addWidget(lbl)
            header_layout.addWidget(line, 1)
            return header_layout
        
        # =================================================================
        # System & UI
        # =================================================================
        self.system_tab, sys_layout = create_scroll_page()
        self.system_tab.setObjectName("system_tab")

        # -----------------------------------------------------------------
        # CARD 1: Localization & Translation
        # -----------------------------------------------------------------
        card_lang, l_lang = create_glass_card(self.localization_title)
        
        # === INTERFACE ===
        l_lang.addLayout(create_section_header(self.translations.get("section_app_interface", "APP INTERFACE")))
        
        form_app_lang = QtWidgets.QFormLayout()
        form_app_lang.setVerticalSpacing(20)
        form_app_lang.setHorizontalSpacing(30)

        self.program_language_label = QtWidgets.QLabel("App Language")
        self.program_language_label.setFont(font_label)
        self.comboBox_program_language = QtWidgets.QComboBox()
        self.comboBox_program_language.setFont(font_input)
        self.comboBox_program_language.setFixedHeight(40)
        self.comboBox_program_language.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_program_language.addItems(["English", "Russian"])
        self.comboBox_program_language.setObjectName("comboBox_program_language")
        form_app_lang.addRow(self.program_language_label, self.comboBox_program_language)

        l_lang.addLayout(form_app_lang)
        l_lang.addSpacing(10)

        # === MESSAGE TRANSLATION ===
        l_lang.addLayout(create_section_header(self.translations.get("section_message_translation", "MESSAGE TRANSLATION")))
        
        form_trans = QtWidgets.QFormLayout()
        form_trans.setVerticalSpacing(20)
        form_trans.setHorizontalSpacing(30)

        self.choose_translator_label = QtWidgets.QLabel("Translator Engine")
        self.choose_translator_label.setFont(font_label)
        self.comboBox_translator = QtWidgets.QComboBox()
        self.comboBox_translator.setFont(font_input)
        self.comboBox_translator.setFixedHeight(40)
        self.comboBox_translator.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_translator.addItems(["None", "Google", "Yandex", "AI Translator (Current Model)"])
        self.comboBox_translator.setObjectName("comboBox_translator")
        form_trans.addRow(self.choose_translator_label, self.comboBox_translator)

        self.target_language_translator_label = QtWidgets.QLabel("Target Language")
        self.target_language_translator_label.setFont(font_label)
        self.comboBox_target_language_translator = QtWidgets.QComboBox()
        self.comboBox_target_language_translator.setFont(font_input)
        self.comboBox_target_language_translator.setFixedHeight(40)
        self.comboBox_target_language_translator.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_target_language_translator.addItem("Russian")
        self.comboBox_target_language_translator.setObjectName("comboBox_target_language_translator")
        form_trans.addRow(self.target_language_translator_label, self.comboBox_target_language_translator)

        l_lang.addLayout(form_trans)
        sys_layout.addWidget(card_lang)

        # -----------------------------------------------------------------
        # CARD 2: Audio Devices
        # -----------------------------------------------------------------
        card_audio, l_audio = create_glass_card(self.audio_devices_title)
        
        l_audio.addLayout(create_section_header(self.translations.get("section_audio_channels", "AUDIO I/O CHANNELS")))
        
        form_audio = QtWidgets.QFormLayout()
        form_audio.setVerticalSpacing(20)
        form_audio.setHorizontalSpacing(30)

        self.input_device_label = QtWidgets.QLabel("Microphone Input")
        self.input_device_label.setFont(font_label)
        self.comboBox_input_devices = QtWidgets.QComboBox()
        self.comboBox_input_devices.setFont(font_input)
        self.comboBox_input_devices.setFixedHeight(40)
        self.comboBox_input_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_input_devices.setObjectName("comboBox_input_devices")
        form_audio.addRow(self.input_device_label, self.comboBox_input_devices)

        self.output_device_label = QtWidgets.QLabel("Speaker Output")
        self.output_device_label.setFont(font_label)
        self.comboBox_output_devices = QtWidgets.QComboBox()
        self.comboBox_output_devices.setFont(font_input)
        self.comboBox_output_devices.setFixedHeight(40)
        self.comboBox_output_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_output_devices.setObjectName("comboBox_output_devices")
        form_audio.addRow(self.output_device_label, self.comboBox_output_devices)

        l_audio.addLayout(form_audio)
        sys_layout.addWidget(card_audio)

        # -----------------------------------------------------------------
        # CARD 3: Hardware Diagnostics
        # -----------------------------------------------------------------
        card_hw, l_hw = create_glass_card(self.hardware_spec_title)
        
        l_hw.addLayout(create_section_header(self.translations.get("section_system_resources", "SYSTEM RESOURCES")))
        
        hw_layout = QtWidgets.QHBoxLayout()
        hw_layout.setSpacing(30)
        hw_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- RAM ---
        ram_box = QtWidgets.QHBoxLayout()
        ram_box.setSpacing(10)
        self.ram_label_icon = QtWidgets.QLabel()
        self.ram_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/memory.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.ram_label = QtWidgets.QLabel("0 GB RAM")
        self.ram_label.setFont(font_label)
        self.ram_label.setStyleSheet("color: #E2E8F0; font-weight: bold;")
        ram_box.addWidget(self.ram_label_icon)
        ram_box.addWidget(self.ram_label)
        ram_box.addStretch()
        
        # --- GPU ---
        gpu_box = QtWidgets.QHBoxLayout()
        gpu_box.setSpacing(10)
        self.gpu_label_icon = QtWidgets.QLabel()
        self.gpu_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/gpu.png").scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.gpu_label = QtWidgets.QLabel("No GPU")
        self.gpu_label.setFont(font_label)
        self.gpu_label.setStyleSheet("color: #E2E8F0; font-weight: bold;")
        gpu_box.addWidget(self.gpu_label_icon)
        gpu_box.addWidget(self.gpu_label)
        gpu_box.addStretch()

        hw_layout.addLayout(ram_box)
        hw_layout.addLayout(gpu_box)
        hw_layout.addStretch()
        
        l_hw.addLayout(hw_layout)
        sys_layout.addWidget(card_hw)

        sys_layout.addStretch()
        self.tabWidget_options.addWidget(self.system_tab)

        # =================================================================
        # API & Providers
        # =================================================================
        self.configuration_tab, conf_layout = create_scroll_page()
        self.configuration_tab.setObjectName("configuration_tab")

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
        self.comboBox_conversation_method.addItems([
            "Mistral AI", "Open AI", "Local LLM", "Anthropic", "Google Gemini", "DeepSeek", "Grok", "Qwen", "Z.AI", "OpenRouter"
        ])
        self.comboBox_conversation_method.setObjectName("comboBox_conversation_method")
        
        form_method.addRow(self.conversation_method_options_label, self.comboBox_conversation_method)
        self.label_provider_verification = QtWidgets.QLabel()
        self.label_provider_verification.setFont(font_input)
        self.label_provider_verification.setWordWrap(True)
        form_method.addRow("", self.label_provider_verification)
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
        self.lineEdit_api_token_options.setStyle(SmallPasswordMaskStyle(self.lineEdit_api_token_options.style()))
        self.lineEdit_api_token_options.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.show_api_token_button = QtWidgets.QToolButton()
        self.show_api_token_button.setIcon(visibility_icon(hidden=True))
        self.show_api_token_button.setCheckable(True)
        self.show_api_token_button.setToolTip("Show API token")
        self.show_api_token_button.toggled.connect(
            lambda shown: (
                self.lineEdit_api_token_options.setEchoMode(
                    QtWidgets.QLineEdit.EchoMode.Normal if shown else QtWidgets.QLineEdit.EchoMode.Password
                ),
                self.show_api_token_button.setIcon(visibility_icon(hidden=not shown)),
            )
        )
        api_token_layout = QtWidgets.QHBoxLayout()
        api_token_layout.setContentsMargins(0, 0, 0, 0)
        api_token_layout.addWidget(self.lineEdit_api_token_options)
        api_token_layout.addWidget(self.show_api_token_button)
        api_token_widget = QtWidgets.QWidget()
        api_token_widget.setLayout(api_token_layout)
        form_api.addRow(self.conversation_method_token_title_label, api_token_widget)

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

        self.label_anthropic_model = QtWidgets.QLabel("Claude Model")
        self.label_anthropic_model.setFont(font_label)
        self.lineEdit_anthropic_model = QtWidgets.QLineEdit()
        self.lineEdit_anthropic_model.setFont(font_input)
        self.lineEdit_anthropic_model.setFixedHeight(40)
        self.lineEdit_anthropic_model.setPlaceholderText("claude-sonnet-4-6")
        self.lineEdit_anthropic_model.setObjectName("lineEdit_anthropic_model")
        form_api.addRow(self.label_anthropic_model, self.lineEdit_anthropic_model)

        self.label_gemini_model = QtWidgets.QLabel("Gemini Model")
        self.label_gemini_model.setFont(font_label)
        self.lineEdit_gemini_model = QtWidgets.QLineEdit()
        self.lineEdit_gemini_model.setFont(font_input)
        self.lineEdit_gemini_model.setFixedHeight(40)
        self.lineEdit_gemini_model.setPlaceholderText("gemini-3-flash-preview")
        self.lineEdit_gemini_model.setObjectName("lineEdit_gemini_model")
        form_api.addRow(self.label_gemini_model, self.lineEdit_gemini_model)

        self.label_deepseek_model = QtWidgets.QLabel("DeepSeek Model")
        self.label_deepseek_model.setFont(font_label)
        self.lineEdit_deepseek_model = QtWidgets.QLineEdit()
        self.lineEdit_deepseek_model.setFont(font_input)
        self.lineEdit_deepseek_model.setFixedHeight(40)
        self.lineEdit_deepseek_model.setPlaceholderText("deepseek-v4-flash")
        self.lineEdit_deepseek_model.setObjectName("lineEdit_deepseek_model")
        form_api.addRow(self.label_deepseek_model, self.lineEdit_deepseek_model)

        self.label_grok_model = QtWidgets.QLabel("Grok Model")
        self.label_grok_model.setFont(font_label)
        self.lineEdit_grok_model = QtWidgets.QLineEdit()
        self.lineEdit_grok_model.setFont(font_input)
        self.lineEdit_grok_model.setFixedHeight(40)
        self.lineEdit_grok_model.setPlaceholderText("grok-4.3")
        self.lineEdit_grok_model.setObjectName("lineEdit_grok_model")
        form_api.addRow(self.label_grok_model, self.lineEdit_grok_model)

        self.label_qwen_model = QtWidgets.QLabel("Qwen Model")
        self.label_qwen_model.setFont(font_label)
        self.lineEdit_qwen_model = QtWidgets.QLineEdit()
        self.lineEdit_qwen_model.setFont(font_input)
        self.lineEdit_qwen_model.setFixedHeight(40)
        self.lineEdit_qwen_model.setPlaceholderText("qwen3.7-max")
        self.lineEdit_qwen_model.setObjectName("lineEdit_qwen_model")
        form_api.addRow(self.label_qwen_model, self.lineEdit_qwen_model)

        self.label_zai_model = QtWidgets.QLabel("Z.AI Model")
        self.label_zai_model.setFont(font_label)
        self.lineEdit_zai_model = QtWidgets.QLineEdit()
        self.lineEdit_zai_model.setFont(font_input)
        self.lineEdit_zai_model.setFixedHeight(40)
        self.lineEdit_zai_model.setPlaceholderText("glm-4.7")
        self.lineEdit_zai_model.setObjectName("lineEdit_zai_model")
        form_api.addRow(self.label_zai_model, self.lineEdit_zai_model)

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

        self.pushButton_reload_openrouter_models = QtWidgets.QPushButton()
        self.pushButton_reload_openrouter_models.setFixedSize(40, 40)
        self.pushButton_reload_openrouter_models.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_openrouter_models.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_reload_openrouter_models.setIcon(QtGui.QIcon("app/gui/icons/reload.png"))
        openrouter_refresh_text = self.translations.get(
            "openrouter_models_refresh",
            "Refresh OpenRouter models"
        )
        self.pushButton_reload_openrouter_models.setToolTip(openrouter_refresh_text)
        self.pushButton_reload_openrouter_models.setAccessibleName(openrouter_refresh_text)
        self.pushButton_reload_openrouter_models.setObjectName("pushButton_reload_openrouter_models")
        
        openrouter_layout.addWidget(self.lineEdit_search_openrouter_models, 1)
        openrouter_layout.addWidget(self.comboBox_openrouter_models, 2)
        openrouter_layout.addWidget(self.pushButton_reload_openrouter_models)
        
        form_api.addRow(self.openrouter_models_options_label, self.openrouter_layout_widget)

        self.pushButton_test_model = QtWidgets.QPushButton(
            self.translations.get("check_model", "Check model")
        )
        self.pushButton_test_model.setFont(font_input)
        self.pushButton_test_model.setFixedHeight(40)
        self.pushButton_test_model.setObjectName("pushButton_test_model")
        self.label_model_test_result = QtWidgets.QLabel()
        self.label_model_test_result.setFont(font_input)
        self.label_model_test_result.setWordWrap(True)
        form_api.addRow(self.pushButton_test_model, self.label_model_test_result)

        l_api.addLayout(form_api)
        conf_layout.addWidget(self.card_api)
        
        conf_layout.addStretch()
        self.tabWidget_options.addWidget(self.configuration_tab)

        # =================================================================
        # Voice Settings
        # =================================================================
        self.voice_settings_tab, voice_layout = create_scroll_page()
        self.voice_settings_tab.setObjectName("voice_settings_tab")
        self.tts_configuration_api = configuration.ConfigurationAPI()
        self.tts_provider_rows = (
            ("ElevenLabs", "ELEVENLABS_API_TOKEN"),
            ("XTTSv2", None),
            ("Edge TTS", None),
            ("Kokoro", None),
            ("Silero", None),
            ("Qwen-3 TTS", None),
            ("Inworld", "INWORLD_API_TOKEN"),
        )
        self.comboBox_tts_provider = QtWidgets.QComboBox()
        self.comboBox_tts_provider.setFont(font_input)
        self.comboBox_tts_provider.setFixedHeight(40)
        self.comboBox_tts_provider.setObjectName("comboBox_tts_provider")
        self.comboBox_tts_provider.addItems([name for name, _token in self.tts_provider_rows])
        voice_layout.addWidget(self.comboBox_tts_provider)

        self.tts_provider_stack = QtWidgets.QStackedWidget()
        self.tts_provider_enabled = {}
        self.tts_provider_api_keys = {}
        self.tts_provider_panels = {}

        def add_key_row(form, provider_name, token_name):
            key_input = QtWidgets.QLineEdit(self.tts_configuration_api.get_token(token_name) or "")
            key_input.setFont(font_input)
            key_input.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            key_input.setPlaceholderText(self.translations.get("voice_settings_api_key", "API key"))
            key_input.setStyleSheet(global_input_style)
            show_key = QtWidgets.QToolButton()
            show_key.setCheckable(True)
            show_key.setIcon(visibility_icon(hidden=True))
            show_key.setToolTip(self.translations.get("voice_settings_show_key", "Show API key"))
            show_key.toggled.connect(
                lambda shown, field=key_input, button=show_key: (
                    field.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal if shown else QtWidgets.QLineEdit.EchoMode.Password),
                    button.setIcon(visibility_icon(hidden=not shown)),
                )
            )
            row = QtWidgets.QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(key_input)
            row.addWidget(show_key)
            form.addRow(self.translations.get("voice_settings_api_key", "API key"), row)
            self.tts_provider_api_keys[provider_name] = (token_name, key_input)

        saved_tts_providers = self.configuration.get_main_setting("tts_providers") or {}
        for provider_name, token_name in self.tts_provider_rows:
            card, card_layout = create_glass_card(provider_name)
            form = QtWidgets.QFormLayout()
            form.setVerticalSpacing(14)
            form.setHorizontalSpacing(24)
            enabled = QtWidgets.QCheckBox(self.translations.get("voice_settings_enabled", "Provider is ready"))
            enabled.setFont(font_input)
            enabled.setChecked(bool(saved_tts_providers.get(provider_name, {}).get("enabled")))
            self.tts_provider_enabled[provider_name] = enabled
            form.addRow(enabled)
            if token_name:
                add_key_row(form, provider_name, token_name)
            else:
                form.addRow(QtWidgets.QLabel(self.translations.get("voice_settings_local", "Local provider")))

            if provider_name == "Inworld":
                inworld = saved_tts_providers.get("Inworld", {})
                self.comboBox_tts_inworld_voice = QtWidgets.QComboBox()
                self.comboBox_tts_inworld_voice.setEditable(True)
                self.comboBox_tts_inworld_voice.setFont(font_input)
                self.comboBox_tts_inworld_voice.setCurrentText(inworld.get("default_voice_id", "Dennis"))
                self.comboBox_tts_inworld_model = QtWidgets.QComboBox()
                self.comboBox_tts_inworld_model.setEditable(True)
                self.comboBox_tts_inworld_model.setFont(font_input)
                self.comboBox_tts_inworld_model.addItems(["inworld-tts-1.5-mini", "inworld-tts-1.5-max", "inworld-tts-2"])
                self.comboBox_tts_inworld_model.setCurrentText(inworld.get("default_model_id", "inworld-tts-2"))
                self.button_tts_inworld_load_voices = QtWidgets.QPushButton(self.translations.get("tts_selector_inworld_load_voices", "Load voices"))
                self.button_tts_inworld_preview = QtWidgets.QPushButton(self.translations.get("tts_selector_inworld_preview", "Preview voice"))
                form.addRow(self.translations.get("tts_selector_inworld_voice_label", "VOICE ID"), self.comboBox_tts_inworld_voice)
                form.addRow(self.translations.get("tts_selector_inworld_model_label", "MODEL ID"), self.comboBox_tts_inworld_model)
                form.addRow(self.button_tts_inworld_load_voices, self.button_tts_inworld_preview)

            save_button = QtWidgets.QPushButton(self.translations.get("voice_settings_save", "Save voice settings"))
            save_button.setFont(font_input)
            save_button.setFixedHeight(40)
            save_button.setStyleSheet("QPushButton { background: rgba(75, 184, 255, 0.12); border: 1px solid rgba(75, 184, 255, 0.25); border-radius: 8px; color: #4BB8FF; } QPushButton:hover { background: rgba(75, 184, 255, 0.25); }")
            save_button.clicked.connect(lambda _checked=False, name=provider_name: self.save_tts_provider_settings(name))
            card_layout.addLayout(form)
            card_layout.addWidget(save_button)
            self.tts_provider_panels[provider_name] = card
            self.tts_provider_stack.addWidget(card)

        self.comboBox_tts_provider.currentIndexChanged.connect(self.tts_provider_stack.setCurrentIndex)
        voice_layout.addWidget(self.tts_provider_stack)
        voice_layout.addStretch()
        self.update_tts_provider_checks()
        self.tabWidget_options.addWidget(self.voice_settings_tab)

        # =================================================================
        # LLM Settings
        # =================================================================
        self.llm_tab, llm_layout = create_scroll_page()
        self.llm_tab.setObjectName("llm_tab")

        def create_slider_row(label_text, slider_obj, line_edit_obj, min_val, max_val, step=1, tooltip=""):
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(20)
            
            lbl = QtWidgets.QLabel(label_text)
            lbl.setFont(font_label)
            lbl.setFixedWidth(160)
            if tooltip:
                lbl.setToolTip(tooltip)
            
            slider_obj.setOrientation(QtCore.Qt.Orientation.Horizontal)
            slider_obj.setMinimum(min_val)
            slider_obj.setMaximum(max_val)
            slider_obj.setSingleStep(step)
            slider_obj.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            slider_obj.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if tooltip:
                slider_obj.setToolTip(tooltip)
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
                QSlider::handle:horizontal:hover { background: #ffffff; }
            """)
            
            line_edit_obj.setFont(font_input)
            line_edit_obj.setFixedSize(65, 35)
            line_edit_obj.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if tooltip:
                line_edit_obj.setToolTip(tooltip)
            
            row.addWidget(lbl)
            row.addWidget(slider_obj)
            row.addWidget(line_edit_obj)
            return row
        
        # -----------------------------------------------------------------
        # CARD 1: General Generation
        # -----------------------------------------------------------------
        card_llm_gen, l_llm_gen = create_glass_card(self.translations.get("llm_gen_title", "General Generation Parameters"))
        
        # === RESPONSE CONTROL ===
        l_llm_gen.addLayout(create_section_header(self.translations.get("section_response_control", "RESPONSE CONTROL")))

        self.max_tokens_horizontalSlider = QtWidgets.QSlider()
        self.max_tokens_horizontalSlider.setObjectName("max_tokens_horizontalSlider")
        self.lineEdit_maxTokens = QtWidgets.QLineEdit()
        self.lineEdit_maxTokens.setObjectName("lineEdit_maxTokens")
        l_llm_gen.addLayout(create_slider_row(
            self.translations.get("max_tokens_text", "Max Tokens"), 
            self.max_tokens_horizontalSlider, self.lineEdit_maxTokens, 16, 4096, 16, 
            self.translations.get("max_tokens_tooltip", "Max Response Length")))

        l_llm_gen.addSpacing(10)

        # === CREATIVITY & SAMPLING ===
        l_llm_gen.addLayout(create_section_header(self.translations.get("section_creativity", "CREATIVITY & SAMPLING")))

        self.temperature_horizontalSlider = QtWidgets.QSlider()
        self.temperature_horizontalSlider.setObjectName("temperature_horizontalSlider")
        self.lineEdit_temperature = QtWidgets.QLineEdit()
        self.lineEdit_temperature.setObjectName("lineEdit_temperature")
        l_llm_gen.addLayout(create_slider_row(
            self.translations.get("temperature_text", "Temperature"), 
            self.temperature_horizontalSlider, self.lineEdit_temperature, 0, 20, 1, 
            self.translations.get("temperature_tooltip", "0.0 to 2.0. Higher values make the output more creative.")))

        self.top_p_horizontalSlider = QtWidgets.QSlider()
        self.top_p_horizontalSlider.setObjectName("top_p_horizontalSlider")
        self.lineEdit_topP = QtWidgets.QLineEdit()
        self.lineEdit_topP.setObjectName("lineEdit_topP")
        l_llm_gen.addLayout(create_slider_row(
            self.translations.get("top_p_text", "Top-P"), 
            self.top_p_horizontalSlider, self.lineEdit_topP, 0, 10, 1,
            self.translations.get("top_p_tooltip", "0.0 to 1.0. Core sampler. Set to 1.0 if using Min-P in Advanced Settings.")))
        
        l_llm_gen.addSpacing(10)

        # === REPETITION PENALTIES ===
        l_llm_gen.addLayout(create_section_header(self.translations.get("section_penalties", "REPETITION PENALTIES")))

        self.freq_penalty_horizontalSlider = QtWidgets.QSlider()
        self.freq_penalty_horizontalSlider.setObjectName("freq_penalty_horizontalSlider")
        self.lineEdit_freqPenalty = QtWidgets.QLineEdit()
        self.lineEdit_freqPenalty.setObjectName("lineEdit_freqPenalty")
        l_llm_gen.addLayout(create_slider_row(
            self.translations.get("freq_penalty_text", "Frequency Penalty"), 
            self.freq_penalty_horizontalSlider, self.lineEdit_freqPenalty, 0, 20, 1, 
            self.translations.get("freq_penalty_tooltip", "0.0 to 2.0. Penalizes words based on their frequency in the text. Encourages wider vocabulary.")))

        self.pres_penalty_horizontalSlider = QtWidgets.QSlider()
        self.pres_penalty_horizontalSlider.setObjectName("pres_penalty_horizontalSlider")
        self.lineEdit_presPenalty = QtWidgets.QLineEdit()
        self.lineEdit_presPenalty.setObjectName("lineEdit_presPenalty")
        l_llm_gen.addLayout(create_slider_row(
            self.translations.get("pres_penalty_text", "Presence Penalty"), 
            self.pres_penalty_horizontalSlider, self.lineEdit_presPenalty, 0, 20, 1, 
            self.translations.get("pres_penalty_tooltip", "0.0 to 2.0. Penalizes words if they appeared at all. Encourages switching topics.")))

        llm_layout.addWidget(card_llm_gen)

        # -----------------------------------------------------------------
        # CARD 2: Server & Hardware
        # -----------------------------------------------------------------
        self.card_llm_hw, l_llm_hw = create_glass_card(self.translations.get("llm_hw_title", "Hardware & Backend"))
        form_llm_hw = QtWidgets.QFormLayout()
        form_llm_hw.setVerticalSpacing(20)
        form_llm_hw.setHorizontalSpacing(30)

        l_llm_hw.addLayout(create_section_header(self.translations.get("section_inference_engine", "INFERENCE ENGINE")))

        self.llm_options_label = QtWidgets.QLabel(self.translations.get("llm_options_label", "Server Endpoint"))
        self.llm_options_label.setFont(font_label)
        self.lineEdit_server = QtWidgets.QLineEdit()
        self.lineEdit_server.setFont(font_input)
        self.lineEdit_server.setFixedHeight(40)
        self.lineEdit_server.setReadOnly(True)
        self.lineEdit_server.setObjectName("lineEdit_server")
        form_llm_hw.addRow(self.llm_options_label, self.lineEdit_server)

        hw_combo_layout = QtWidgets.QHBoxLayout()
        hw_combo_layout.setSpacing(15)
        self.comboBox_llm_devices = QtWidgets.QComboBox()
        self.comboBox_llm_devices.setFont(font_input)
        self.comboBox_llm_devices.setFixedHeight(40)
        self.comboBox_llm_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_llm_devices.addItems(["CPU", "GPU"])
        self.comboBox_llm_devices.setObjectName("comboBox_llm_devices")
        
        self.comboBox_llm_gpu_devices = QtWidgets.QComboBox()
        self.comboBox_llm_gpu_devices.setFont(font_input)
        self.comboBox_llm_gpu_devices.setFixedHeight(40)
        self.comboBox_llm_gpu_devices.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_llm_gpu_devices.addItems(["Vulkan", "CUDA (NVIDIA)", "HIP (AMD)", "SYCL (Intel)"])
        self.comboBox_llm_gpu_devices.setObjectName("comboBox_llm_gpu_devices")
        
        self.pushButton_update_engine = QtWidgets.QPushButton(self.translations.get("update_btn", "Update"))
        self.pushButton_update_engine.setFont(font_input)
        self.pushButton_update_engine.setFixedHeight(40)
        self.pushButton_update_engine.setFixedWidth(120)
        self.pushButton_update_engine.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_update_engine.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_update_engine.setToolTip(self.translations.get("update_engine_tooltip", "Download and install the latest llama.cpp binaries for the selected backend."))
        self.pushButton_update_engine.setObjectName("pushButton_update_engine")
        self.pushButton_update_engine.setStyleSheet("""
            QPushButton { 
                background-color: rgba(59, 130, 246, 0.15); 
                color: #93C5FD; 
                border: 1px solid rgba(59, 130, 246, 0.3); 
                border-radius: 6px; 
                padding: 0 15px; 
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: rgba(59, 130, 246, 0.3); 
                border: 1px solid rgba(59, 130, 246, 0.5); 
                color: #FFFFFF; 
            }
            QPushButton:pressed { 
                background-color: rgba(59, 130, 246, 0.1); 
            }
        """)

        hw_combo_layout.addWidget(self.comboBox_llm_devices)
        hw_combo_layout.addWidget(self.comboBox_llm_gpu_devices)
        hw_combo_layout.addWidget(self.pushButton_update_engine)
        
        self.choose_llm_device_label = QtWidgets.QLabel(self.translations.get("choose_llm_device_label", "Compute Setup"))
        self.choose_llm_device_label.setFont(font_label)
        form_llm_hw.addRow(self.choose_llm_device_label, hw_combo_layout)

        self.kv_cache_label = QtWidgets.QLabel(self.translations.get("kv_cache_label", "KV Cache Type"))
        self.kv_cache_label.setFont(font_label)
        self.comboBox_kv_cache = QtWidgets.QComboBox()
        self.comboBox_kv_cache.setFont(font_input)
        self.comboBox_kv_cache.setFixedHeight(40)
        self.comboBox_kv_cache.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_kv_cache.addItems(["f16", "q8_0", "q4_1", "q4_0"])
        self.comboBox_kv_cache.setObjectName("comboBox_kv_cache")
        self.comboBox_kv_cache.setToolTip(self.translations.get("kv_cache_tooltip", "Quantize Context Cache to save massive amounts of VRAM on long contexts."))
        form_llm_hw.addRow(self.kv_cache_label, self.comboBox_kv_cache)

        check_box_layout = QtWidgets.QHBoxLayout()
        check_box_layout.setSpacing(25)
        
        self.checkBox_enable_mlock = QtWidgets.QCheckBox(self.translations.get("enable_mlock_checkbox", "MLock"))
        self.checkBox_enable_mlock.setFont(font_input)
        self.checkBox_enable_mlock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_mlock.setObjectName("checkBox_enable_mlock")

        self.checkBox_enable_flash_attention = QtWidgets.QCheckBox(self.translations.get("enable_flash_attention_checkbox", "Flash Attention"))
        self.checkBox_enable_flash_attention.setFont(font_input)
        self.checkBox_enable_flash_attention.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_flash_attention.setObjectName("checkBox_enable_flash_attention")

        self.checkBox_reasoning_mode = QtWidgets.QCheckBox(self.translations.get("reasoning_mode_checkbox", "Enable Thinking/Reasoning Mode (<think>)"))
        self.checkBox_reasoning_mode.setFont(font_input)
        self.checkBox_reasoning_mode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_reasoning_mode.setObjectName("checkBox_reasoning_mode")
        
        check_box_layout.addWidget(self.checkBox_enable_mlock)
        check_box_layout.addWidget(self.checkBox_enable_flash_attention)
        check_box_layout.addWidget(self.checkBox_reasoning_mode)
        check_box_layout.addStretch()
        form_llm_hw.addRow("", check_box_layout)

        l_llm_hw.addLayout(form_llm_hw)
        
        l_llm_hw.addSpacing(10)
        l_llm_hw.addLayout(create_section_header(self.translations.get("section_hw_tuning", "PERFORMANCE & MEMORY TUNING")))
        
        self.gpu_layers_horizontalSlider = QtWidgets.QSlider()
        self.gpu_layers_horizontalSlider.setObjectName("gpu_layers_horizontalSlider")
        self.lineEdit_gpuLayers = QtWidgets.QLineEdit()
        self.lineEdit_gpuLayers.setObjectName("lineEdit_gpuLayers")
        l_llm_hw.addLayout(create_slider_row(
            self.translations.get("gpu_layers_text", "GPU Layers"), 
            self.gpu_layers_horizontalSlider, self.lineEdit_gpuLayers, 0, 100, 1, 
            self.translations.get("gpu_layers_tooltip", "How many model layers to offload to GPU. Reduce if running out of VRAM.")))

        # === CPU MoE Layers ===
        self.cpu_moe_layers_horizontalSlider = QtWidgets.QSlider()
        self.cpu_moe_layers_horizontalSlider.setObjectName("cpu_moe_layers_horizontalSlider")
        self.lineEdit_cpuMoeLayers = QtWidgets.QLineEdit()
        self.lineEdit_cpuMoeLayers.setObjectName("lineEdit_cpuMoeLayers")
        l_llm_hw.addLayout(create_slider_row(
            self.translations.get("cpu_moe_layers_text", "CPU MoE Layers"), 
            self.cpu_moe_layers_horizontalSlider, self.lineEdit_cpuMoeLayers, 0, 100, 1, 
            self.translations.get("cpu_moe_layers_tooltip", "0 = Disabled. How many Mixture of Experts (MoE) layers to keep in CPU RAM. Essential for huge MoE models.")))

        self.CONTEXT_VALUES = [
            512, 1024, 2048, 4096, 8192, 16384, 32768, 49152, 65536, 98304, 131072,
            262144, 524288, 1048576, 2097152, -1
        ]

        self.context_size_horizontalSlider = QtWidgets.QSlider()
        self.context_size_horizontalSlider.setObjectName("context_size_horizontalSlider")

        self.context_size_horizontalSlider.setMinimum(0)
        self.context_size_horizontalSlider.setMaximum(len(self.CONTEXT_VALUES) - 1)
        self.context_size_horizontalSlider.setSingleStep(1)
        
        self.lineEdit_contextSize = QtWidgets.QLineEdit()
        self.lineEdit_contextSize.setObjectName("lineEdit_contextSize")
        
        l_llm_hw.addLayout(create_slider_row(
            self.translations.get("context_size_text", "Context Size"), 
            self.context_size_horizontalSlider, self.lineEdit_contextSize, 0, len(self.CONTEXT_VALUES) - 1, 1, 
            self.translations.get("context_size_tooltip", "Max memory of the model in tokens. Choose Max Index for Unlimited (API).")))

        self.batch_size_horizontalSlider = QtWidgets.QSlider()
        self.batch_size_horizontalSlider.setObjectName("batch_size_horizontalSlider")
        self.lineEdit_batchSize = QtWidgets.QLineEdit()
        self.lineEdit_batchSize.setObjectName("lineEdit_batchSize")
        l_llm_hw.addLayout(create_slider_row(
            self.translations.get("batch_size_text", "Prompt Batch Size"), 
            self.batch_size_horizontalSlider, self.lineEdit_batchSize, 128, 8192, 128, 
            self.translations.get("batch_size_tooltip", "Tokens processed at once. Set to 2048-4096 for massive MoE models to speed up prompt processing.")))

        self.cpu_threads_horizontalSlider = QtWidgets.QSlider()
        self.cpu_threads_horizontalSlider.setObjectName("cpu_threads_horizontalSlider")
        self.lineEdit_cpuThreads = QtWidgets.QLineEdit()
        self.lineEdit_cpuThreads.setObjectName("lineEdit_cpuThreads")
        l_llm_hw.addLayout(create_slider_row(
            self.translations.get("cpu_threads_text", "CPU Threads"), 
            self.cpu_threads_horizontalSlider, self.lineEdit_cpuThreads, 0, 32, 1, 
            self.translations.get("cpu_threads_tooltip", "0 = Auto. Set to your physical CPU core count for optimal inference speed on CPU.")))

        # === Custom Arguments ===
        l_llm_hw.addSpacing(10)
        custom_args_layout = QtWidgets.QHBoxLayout()
        custom_args_layout.setSpacing(20)
        
        self.custom_args_label = QtWidgets.QLabel(self.translations.get("custom_args_label", "Custom Arguments"))
        self.custom_args_label.setFont(font_label)
        self.custom_args_label.setFixedWidth(160)
        
        self.lineEdit_customArgs = QtWidgets.QLineEdit()
        self.lineEdit_customArgs.setFont(font_input)
        self.lineEdit_customArgs.setFixedHeight(35)
        self.lineEdit_customArgs.setPlaceholderText(self.translations.get("custom_args_placeholder", "e.g., '--temp 0.8 --name 'My Model'"))
        self.lineEdit_customArgs.setObjectName("lineEdit_customArgs")
        self.lineEdit_customArgs.setStyleSheet("""
            QLineEdit {
                background: rgba(10, 10, 15, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.06); 
                border-radius: 6px; 
                padding-left: 10px; 
                color: #E2E8F0;
            }
            QLineEdit:focus {
                border: 1px solid rgba(96, 165, 250, 0.4); 
                background: rgba(15, 15, 20, 0.7);
            }
        """)
        
        custom_args_layout.addWidget(self.custom_args_label)
        custom_args_layout.addWidget(self.lineEdit_customArgs)
        
        l_llm_hw.addLayout(custom_args_layout)

        llm_layout.addWidget(self.card_llm_hw)

        # -----------------------------------------------------------------
        # CARD 3: Prompting & Formatting
        # -----------------------------------------------------------------
        card_llm_format, l_llm_format = create_glass_card(self.translations.get("llm_format_title", "Prompting & Formatting"))
        form_llm_format = QtWidgets.QFormLayout()
        form_llm_format.setVerticalSpacing(20)
        form_llm_format.setHorizontalSpacing(30)

        l_llm_format.addLayout(create_section_header(self.translations.get("section_prompt_structure", "PROMPT STRUCTURE & SYNTAX")))

        self.chat_template_label = QtWidgets.QLabel(self.translations.get("chat_template_label", "Chat Template"))
        self.chat_template_label.setFont(font_label)
        self.comboBox_chat_template = QtWidgets.QComboBox()
        self.comboBox_chat_template.setFont(font_input)
        self.comboBox_chat_template.setFixedHeight(40)
        self.comboBox_chat_template.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_chat_template.addItems(["Auto", "ChatML", "Llama-3", "DeepSeek", "Qwen", "Mistral", "Alpaca"])
        self.comboBox_chat_template.setObjectName("comboBox_chat_template")
        form_llm_format.addRow(self.chat_template_label, self.comboBox_chat_template)

        self.stop_strings_label = QtWidgets.QLabel(self.translations.get("stop_strings_label", "Stop Strings"))
        self.stop_strings_label.setFont(font_label)
        self.lineEdit_stop_strings = QtWidgets.QLineEdit()
        self.lineEdit_stop_strings.setFont(font_input)
        self.lineEdit_stop_strings.setFixedHeight(40)
        self.lineEdit_stop_strings.setPlaceholderText(self.translations.get("stop_strings_placeholder", "\\nUser:, </s>, <|eot_id|>, <|im_end|>"))
        self.lineEdit_stop_strings.setObjectName("lineEdit_stop_strings")
        form_llm_format.addRow(self.stop_strings_label, self.lineEdit_stop_strings)

        l_llm_format.addLayout(form_llm_format)
        llm_layout.addWidget(card_llm_format)

        # -----------------------------------------------------------------
        # CARD 4: Advanced Local LLM Sampling
        # -----------------------------------------------------------------
        self.card_llm_adv, l_llm_adv = create_glass_card(self.translations.get("llm_adv_title", "Advanced Local LLM Sampling"))
        
        self.checkBox_enable_advanced_sampling = QtWidgets.QCheckBox(self.translations.get("enable_adv_sampling_text", "Enable Advanced Sampling"))
        self.checkBox_enable_advanced_sampling.setFont(font_input)
        self.checkBox_enable_advanced_sampling.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_advanced_sampling.setToolTip(self.translations.get("enable_adv_sampling_tooltip", "When disabled, standard generation settings from Card 1 are used. Advanced settings are ignored."))
        l_llm_adv.addWidget(self.checkBox_enable_advanced_sampling)

        l_llm_adv.addSpacing(10)

        self.adv_samplers_widget = QtWidgets.QWidget()
        adv_samplers_layout = QtWidgets.QVBoxLayout(self.adv_samplers_widget)
        adv_samplers_layout.setContentsMargins(0, 0, 0, 0)
        adv_samplers_layout.setSpacing(10)

        # === BASE SAMPLERS ===
        adv_samplers_layout.addLayout(create_section_header("MIN-P"))
        
        self.min_p_horizontalSlider = QtWidgets.QSlider()
        self.min_p_horizontalSlider.setObjectName("min_p_horizontalSlider")
        self.lineEdit_minP = QtWidgets.QLineEdit()
        self.lineEdit_minP.setObjectName("lineEdit_minP")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("min_p_text", "Min-P"), 
            self.min_p_horizontalSlider, self.lineEdit_minP, 0, 100, 1, 
            self.translations.get("min_p_tooltip", "0.0 to 1.0. Cuts off low-probability tokens based on the top token. New standard for RP. Recommended: 0.05 - 0.1")))

        adv_samplers_layout.addSpacing(10)

        # === DYNAMIC TEMPERATURE ===
        adv_samplers_layout.addLayout(create_section_header(self.translations.get("section_dyn_temp", "DYNAMIC TEMPERATURE")))

        self.dyn_temp_min_horizontalSlider = QtWidgets.QSlider()
        self.dyn_temp_min_horizontalSlider.setObjectName("dyn_temp_min_horizontalSlider")
        self.lineEdit_dynTempMin = QtWidgets.QLineEdit()
        self.lineEdit_dynTempMin.setObjectName("lineEdit_dynTempMin")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("dyn_temp_min_text", "Dynamic Temp Min"), 
            self.dyn_temp_min_horizontalSlider, self.lineEdit_dynTempMin, 0, 20, 1, 
            self.translations.get("dyn_temp_min_tooltip", "0.0 to 2.0. Minimum bound for Dynamic Temperature.")))

        self.dyn_temp_max_horizontalSlider = QtWidgets.QSlider()
        self.dyn_temp_max_horizontalSlider.setObjectName("dyn_temp_max_horizontalSlider")
        self.lineEdit_dynTempMax = QtWidgets.QLineEdit()
        self.lineEdit_dynTempMax.setObjectName("lineEdit_dynTempMax")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("dyn_temp_max_text", "Dynamic Temp Max"), 
            self.dyn_temp_max_horizontalSlider, self.lineEdit_dynTempMax, 0, 20, 1, 
            self.translations.get("dyn_temp_max_tooltip", "0.0 to 2.0. Maximum bound for Dynamic Temperature.")))

        adv_samplers_layout.addSpacing(10)

        # === XTC (Exclude Top Choices) ===
        adv_samplers_layout.addLayout(create_section_header(self.translations.get("section_xtc", "XTC (ANTI-CLICHÉ)")))

        self.xtc_prob_horizontalSlider = QtWidgets.QSlider()
        self.xtc_prob_horizontalSlider.setObjectName("xtc_prob_horizontalSlider")
        self.lineEdit_xtcProb = QtWidgets.QLineEdit()
        self.lineEdit_xtcProb.setObjectName("lineEdit_xtcProb")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("xtc_prob_text", "XTC Probability"), 
            self.xtc_prob_horizontalSlider, self.lineEdit_xtcProb, 0, 100, 1, 
            self.translations.get("xtc_prob_tooltip", "0.0 to 1.0. Excludes most predictable tokens. Removes cliché. Recommended: 0.3 - 0.5")))

        self.xtc_threshold_horizontalSlider = QtWidgets.QSlider()
        self.xtc_threshold_horizontalSlider.setObjectName("xtc_threshold_horizontalSlider")
        self.lineEdit_xtcThreshold = QtWidgets.QLineEdit()
        self.lineEdit_xtcThreshold.setObjectName("lineEdit_xtcThreshold")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("xtc_thresh_text", "XTC Threshold"), 
            self.xtc_threshold_horizontalSlider, self.lineEdit_xtcThreshold, 0, 100, 1, 
            self.translations.get("xtc_thresh_tooltip", "0.0 to 1.0. Minimum probability for a token to be affected by XTC. Recommended: 0.1")))

        adv_samplers_layout.addSpacing(10)

        # === DRY (Don't Repeat Yourself) ===
        adv_samplers_layout.addLayout(create_section_header(self.translations.get("section_dry", "DRY (ANTI-LOOP)")))

        self.dry_multiplier_horizontalSlider = QtWidgets.QSlider()
        self.dry_multiplier_horizontalSlider.setObjectName("dry_multiplier_horizontalSlider")
        self.lineEdit_dryMultiplier = QtWidgets.QLineEdit()
        self.lineEdit_dryMultiplier.setObjectName("lineEdit_dryMultiplier")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("dry_mult_text", "DRY Multiplier"), 
            self.dry_multiplier_horizontalSlider, self.lineEdit_dryMultiplier, 0, 200, 1, 
            self.translations.get("dry_mult_tooltip", "0.0 to 2.0. Penalizes exact sequence repetitions. Prevents action loops. Recommended: 0.8")))

        self.dry_base_horizontalSlider = QtWidgets.QSlider()
        self.dry_base_horizontalSlider.setObjectName("dry_base_horizontalSlider")
        self.lineEdit_dryBase = QtWidgets.QLineEdit()
        self.lineEdit_dryBase.setObjectName("lineEdit_dryBase")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("dry_base_text", "DRY Base"), 
            self.dry_base_horizontalSlider, self.lineEdit_dryBase, 0, 200, 1, 
            self.translations.get("dry_base_tooltip", "Base penalty for DRY algorithm. Recommended: 1.75")))

        self.dry_allowed_length_horizontalSlider = QtWidgets.QSlider()
        self.dry_allowed_length_horizontalSlider.setObjectName("dry_allowed_length_horizontalSlider")
        self.lineEdit_dryAllowedLength = QtWidgets.QLineEdit()
        self.lineEdit_dryAllowedLength.setObjectName("lineEdit_dryAllowedLength")
        adv_samplers_layout.addLayout(create_slider_row(
            self.translations.get("dry_length_text", "DRY Allowed Length"), 
            self.dry_allowed_length_horizontalSlider, self.lineEdit_dryAllowedLength, 0, 100, 1, 
            self.translations.get("dry_length_tooltip", "Tokens allowed to repeat before DRY penalty activates. Recommended: 2")))

        l_llm_adv.addWidget(self.adv_samplers_widget)

        self.checkBox_enable_advanced_sampling.toggled.connect(self.adv_samplers_widget.setEnabled)
        
        self.adv_samplers_widget.setEnabled(False)

        llm_layout.addWidget(self.card_llm_adv)

        llm_layout.addStretch()
        self.tabWidget_options.addWidget(self.llm_tab)

        # =================================================================
        # TOOLS & PLUGINS SETTINGS (Tool Calling & MCP)
        # =================================================================
        self.tools_tab, tools_layout = create_scroll_page()
        self.tools_tab.setObjectName("tools_tab")

        # -----------------------------------------------------------------
        # CARD 1: Native AI Capabilities (Glass Grid Refactoring)
        # -----------------------------------------------------------------
        card_tools_native, l_tools_native = create_glass_card(self.translations.get("tools_native_title", "Native AI Capabilities"))
        
        l_tools_native.addLayout(create_section_header(self.translations.get("section_tool_calling", "TOOL CALLING PERMISSIONS")))

        self.checkBox_enable_tool_calling = QtWidgets.QCheckBox(self.translations.get("enable_tool_calling_text", "Enable Native Tool Calling"))
        self.checkBox_enable_tool_calling.setFont(font_input)
        self.checkBox_enable_tool_calling.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_tool_calling.setToolTip(self.translations.get("enable_tool_calling_tooltip", "Allows the AI to execute Python functions natively during generation (Requires a model that supports Function Calling)."))
        l_tools_native.addWidget(self.checkBox_enable_tool_calling)

        l_tools_native.addSpacing(15)

        self.tools_permissions_widget = QtWidgets.QWidget()
        permissions_layout = QtWidgets.QVBoxLayout(self.tools_permissions_widget)
        permissions_layout.setContentsMargins(0, 0, 0, 0)
        permissions_layout.setSpacing(10)

        grid_layout = QtWidgets.QGridLayout()
        grid_layout.setSpacing(12)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        tools_data = [
            {
                "id": "web_search",
                "emoji": "🌐",
                "title": self.translations.get("tool_web_title", "WebSearchTool"),
                "desc": self.translations.get("tool_web_desc", "Search the web using a stealth DuckDuckGo API to retrieve real-time facts, weather, or news when asked."),
                "experimental": False
            },
            {
                "id": "media_control",
                "emoji": "💻",
                "title": self.translations.get("tool_media_title", "MediaControlTool"),
                "desc": self.translations.get("tool_media_desc", "Control media playback on your Windows PC (pause, play, next/prev tracks in Spotify, YouTube, or browser players)."),
                "experimental": False
            },
            {
                "id": "read_clipboard",
                "emoji": "📋",
                "title": self.translations.get("tool_read_clipboard_title", "ClipboardReaderTool"),
                "desc": self.translations.get("tool_read_clipboard_desc", "Read the current text content copied in the user's clipboard."),
                "experimental": False
            },
            {
                "id": "open_url",
                "emoji": "🚀",
                "title": self.translations.get("tool_url_title", "OpenURLTool"),
                "desc": self.translations.get("tool_url_desc", "Open links or websites (like YouTube or GitHub) in your default web browser on demand."),
                "experimental": False
            },
            {
                "id": "get_system_info",
                "emoji": "📅",
                "title": self.translations.get("tool_sysinfo_title", "GetSystemInfoTool"),
                "desc": self.translations.get("tool_sysinfo_desc", "Retrieve the exact system time and date from your PC to help the AI keep track of the current schedule."),
                "experimental": False
            },
            {
                "id": "take_screenshot",
                "emoji": "👁️",
                "title": self.translations.get("tool_vision_title", "TakeScreenshotTool [Vision]"),
                "desc": self.translations.get("tool_vision_desc", "Analyze active screen contents. Captures a quick screenshot and sends it to a multimodal AI model. Extremely performance-heavy!"),
                "experimental": True
            }
        ]

        for index, tool in enumerate(tools_data):
            capsule = QtWidgets.QFrame()
            
            if tool["experimental"]:
                capsule.setStyleSheet("""
                    QFrame {
                        background: rgba(239, 68, 68, 0.04);
                        border: 1px solid rgba(239, 68, 68, 0.15);
                        border-radius: 12px;
                    }
                    QFrame:disabled {
                        background: rgba(239, 68, 68, 0.01);
                        border: 1px solid rgba(239, 68, 68, 0.05);
                    }
                """)
            else:
                capsule.setStyleSheet("""
                    QFrame {
                        background: rgba(255, 255, 255, 0.03);
                        border: 1px solid rgba(255, 255, 255, 0.07);
                        border-radius: 12px;
                    }
                    QFrame:disabled {
                        background: rgba(255, 255, 255, 0.01);
                        border: 1px solid rgba(255, 255, 255, 0.02);
                    }
                """)

            capsule_layout = QtWidgets.QVBoxLayout(capsule)
            capsule_layout.setContentsMargins(14, 12, 14, 12)
            capsule_layout.setSpacing(6)

            header_layout = QtWidgets.QHBoxLayout()
            header_layout.setSpacing(8)

            emoji_lbl = QtWidgets.QLabel(tool["emoji"])
            emoji_lbl.setFont(QtGui.QFont("Segoe UI Emoji", 13))
            emoji_lbl.setStyleSheet("background: transparent; border: none;")
            header_layout.addWidget(emoji_lbl)

            title_lbl = QtWidgets.QLabel(tool["title"])
            title_lbl.setFont(QtGui.QFont("Segoe UI", 10, QtGui.QFont.Weight.Bold))
            if tool["experimental"]:
                title_lbl.setStyleSheet("color: #FCA5A5; background: transparent; border: none;")
            else:
                title_lbl.setStyleSheet("color: #F1F5F9; background: transparent; border: none;")
            header_layout.addWidget(title_lbl)
            header_layout.addStretch()

            capsule_layout.addLayout(header_layout)

            desc_lbl = QtWidgets.QLabel(tool["desc"])
            desc_lbl.setFont(QtGui.QFont("Segoe UI", 9))
            desc_lbl.setWordWrap(True)
            if tool["experimental"]:
                desc_lbl.setStyleSheet("color: #FECACA; background: transparent; border: none; line-height: 1.2;")
            else:
                desc_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none; line-height: 1.2;")
            
            capsule_layout.addWidget(desc_lbl)

            row = index // 2
            col = index % 2
            grid_layout.addWidget(capsule, row, col)

        permissions_layout.addLayout(grid_layout)
        l_tools_native.addWidget(self.tools_permissions_widget)

        self.checkBox_enable_tool_calling.toggled.connect(self.tools_permissions_widget.setEnabled)
        self.tools_permissions_widget.setEnabled(False)

        tools_layout.addWidget(card_tools_native)

        # -----------------------------------------------------------------
        # CARD 2: Model Context Protocol (MCP)
        # -----------------------------------------------------------------
        card_mcp, l_mcp = create_glass_card(self.translations.get("mcp_title", "Model Context Protocol (MCP)"))
        
        l_mcp.addLayout(create_section_header(self.translations.get("section_mcp_settings", "EXTERNAL MCP SERVERS")))

        mcp_desc = QtWidgets.QLabel(self.translations.get("mcp_description", "Connect external MCP servers (like SearXNG, GitHub, etc.) without writing native Python plugins. This acts as a proxy between Soul of Waifu and the AI."))
        mcp_desc.setFont(font_label)
        mcp_desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        mcp_desc.setWordWrap(True)
        l_mcp.addWidget(mcp_desc)
        
        l_mcp.addSpacing(10)

        self.checkBox_enable_mcp = QtWidgets.QCheckBox(self.translations.get("enable_mcp_text", "Enable MCP Proxy Integration"))
        self.checkBox_enable_mcp.setFont(font_input)
        self.checkBox_enable_mcp.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        l_mcp.addWidget(self.checkBox_enable_mcp)

        l_mcp.addSpacing(10)

        self.mcp_settings_widget = QtWidgets.QWidget()
        mcp_settings_layout = QtWidgets.QVBoxLayout(self.mcp_settings_widget)
        mcp_settings_layout.setContentsMargins(15, 0, 0, 0)
        mcp_settings_layout.setSpacing(15)

        # === MCP URL ===
        mcp_url_layout = QtWidgets.QHBoxLayout()
        mcp_url_layout.setSpacing(20)
        
        self.mcp_url_label = QtWidgets.QLabel(self.translations.get("mcp_url_label", "MCP Server URL"))
        self.mcp_url_label.setFont(font_label)
        self.mcp_url_label.setFixedWidth(145)
        
        self.lineEdit_mcp_url = QtWidgets.QLineEdit()
        self.lineEdit_mcp_url.setFont(font_input)
        self.lineEdit_mcp_url.setFixedHeight(35)
        self.lineEdit_mcp_url.setPlaceholderText(self.translations.get("mcp_url_placeholder", "e.g., http://127.0.0.1:8000"))
        self.lineEdit_mcp_url.setObjectName("lineEdit_mcp_url")
        self.lineEdit_mcp_url.setStyleSheet("""
            QLineEdit {
                background: rgba(10, 10, 15, 0.5); 
                border: 1px solid rgba(255, 255, 255, 0.06); 
                border-radius: 6px; 
                padding-left: 10px; 
                color: #E2E8F0;
            }
            QLineEdit:focus {
                border: 1px solid rgba(96, 165, 250, 0.4); 
                background: rgba(15, 15, 20, 0.7);
            }
            QLineEdit:disabled {
                background: rgba(0, 0, 0, 0.2);
                color: rgba(255, 255, 255, 0.2);
            }
        """)
        
        mcp_url_layout.addWidget(self.mcp_url_label)
        mcp_url_layout.addWidget(self.lineEdit_mcp_url)
        mcp_settings_layout.addLayout(mcp_url_layout)

        l_mcp.addWidget(self.mcp_settings_widget)

        self.checkBox_enable_mcp.toggled.connect(self.mcp_settings_widget.setEnabled)
        self.mcp_settings_widget.setEnabled(False)

        tools_layout.addWidget(card_mcp)
        tools_layout.addStretch()
        
        self.tabWidget_options.addWidget(self.tools_tab)

        # =================================================================
        # Soul of Waifu Modules Tab
        # =================================================================
        self.sow_system_tab, sow_layout = create_scroll_page()
        self.sow_system_tab.setObjectName("sow_system_tab")

        # -----------------------------------------------------------------
        # CARD 1: Master Switch
        # -----------------------------------------------------------------
        card_sow_main, l_sow_main = create_glass_card("Soul of Waifu System")
        self.checkBox_enable_sow_system = QtWidgets.QCheckBox("Enable Soul of Waifu System")
        self.checkBox_enable_sow_system.setFont(font_label)
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
                spacing: 12px; 
                padding: 6px;
            }
            
            QCheckBox::indicator { 
                width: 30px; 
                height: 30px; 
                border-radius: 17px; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                                            stop:0 rgba(40, 30, 20, 0.6), 
                                            stop:1 rgba(20, 10, 5, 0.8));
                border: 2px solid rgba(255, 255, 255, 0.15);
            }
            
            QCheckBox::indicator:hover { 
                border: 2px solid rgba(255, 157, 0, 0.8);
                background-color: rgba(255, 157, 0, 0.05);
            }
            
            QCheckBox::indicator:checked { 
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                                            stop:0 rgba(255, 157, 0, 0.7),
                                            stop:0.7 rgba(255, 119, 0, 0.2), 
                                            stop:1 rgba(0, 0, 0, 0.4));
                border: 2px solid #ff9d00;
                image: url(:/sowInterface/checked.png);
            }
            
            QCheckBox::indicator:checked:hover {
                border: 2px solid #ffcc00;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                                            stop:0 rgba(255, 204, 0, 0.8), 
                                            stop:0.7 rgba(255, 157, 0, 0.4), 
                                            stop:1 rgba(0, 0, 0, 0.5));
            }
        """)
        self.checkBox_enable_sow_system.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_sow_system.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_sow_system.setObjectName("checkBox_enable_sow_system")
        l_sow_main.addWidget(self.checkBox_enable_sow_system)
        sow_layout.addWidget(card_sow_main)

        # -----------------------------------------------------------------
        # CARD 2: Visuals & Environment
        # -----------------------------------------------------------------
        self.card_visuals, l_visuals = create_glass_card(self.visualizations_title)
        
        # === RENDER ENGINE ===
        l_visuals.addLayout(create_section_header(self.translations.get("section_render_engine", "RENDER ENGINE")))
        
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
        
        l_visuals.addLayout(form_vis)
        l_visuals.addSpacing(10)

        # === ENVIRONMENT BACKGROUND ===
        l_visuals.addLayout(create_section_header(self.translations.get("section_environment_background", "ENVIRONMENT BACKGROUND")))
        
        form_bg = QtWidgets.QFormLayout()
        form_bg.setVerticalSpacing(20)
        form_bg.setHorizontalSpacing(30)

        self.label_model_background = QtWidgets.QLabel("Background Type")
        self.label_model_background.setFont(font_label)
        self.comboBox_model_background = QtWidgets.QComboBox()
        self.comboBox_model_background.setFont(font_input)
        self.comboBox_model_background.setFixedHeight(40)
        self.comboBox_model_background.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_model_background.addItems(["Solid Color", "Image"])
        self.comboBox_model_background.setObjectName("comboBox_model_background")
        form_bg.addRow(self.label_model_background, self.comboBox_model_background)

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

        form_bg.addRow("", bg_container)
        l_visuals.addLayout(form_bg)
        
        sow_layout.addWidget(self.card_visuals)

        # -----------------------------------------------------------------
        # CARD 3: Local Web Server
        # -----------------------------------------------------------------
        self.card_web_server, l_web_server = create_glass_card(self.translations.get("web_server_card_title", "Local Web Server"))
        
        l_web_server.addLayout(create_section_header(self.translations.get("section_web_server", "WEB INTERFACE SERVER")))
        
        web_server_layout = QtWidgets.QHBoxLayout()
        web_server_layout.setSpacing(15)
        
        self.label_web_server_status = QtWidgets.QLabel(self.translations.get("web_server_status_stopped", "Status: Stopped"))
        self.label_web_server_status.setFont(font_input)
        self.label_web_server_status.setStyleSheet("color: #909090; padding-left: 5px;")
        
        self.pushButton_toggle_web_server = QtWidgets.QPushButton(self.translations.get("web_server_start_btn", "Start Server"))
        self.pushButton_toggle_web_server.setFont(font_input)
        self.pushButton_toggle_web_server.setFixedHeight(40)
        self.pushButton_toggle_web_server.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_toggle_web_server.setObjectName("pushButton_toggle_web_server")
        self.pushButton_toggle_web_server.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_toggle_web_server.setStyleSheet("""
            QPushButton {
                background: rgba(255, 157, 0, 0.12);
                border: 1px solid rgba(255, 157, 0, 0.35);
                color: #ff9d00;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 157, 0, 0.22);
                border: 1px solid rgba(255, 157, 0, 0.55);
                color: #ffcc00;
            }
            QPushButton:pressed {
                background: rgba(255, 157, 0, 0.08);
            }
        """)
        
        self.pushButton_open_web_browser = QtWidgets.QPushButton(self.translations.get("web_browser_open_btn", "Open in Browser"))
        self.pushButton_open_web_browser.setFont(font_input)
        self.pushButton_open_web_browser.setFixedHeight(40)
        self.pushButton_open_web_browser.setEnabled(False)
        self.pushButton_open_web_browser.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_open_web_browser.setObjectName("pushButton_open_web_browser")
        self.pushButton_open_web_browser.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_open_web_browser.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: #e0e0e0;
                border-radius: 8px;
                padding: 0px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
            }
            QPushButton:disabled {
                background: rgba(255, 255, 255, 0.01);
                border: 1px solid rgba(255, 255, 255, 0.03);
                color: #505050;
            }
        """)
        
        web_server_layout.addWidget(self.label_web_server_status)
        web_server_layout.addStretch()
        web_server_layout.addWidget(self.pushButton_toggle_web_server)
        web_server_layout.addWidget(self.pushButton_open_web_browser)
        
        l_web_server.addLayout(web_server_layout)
        sow_layout.addWidget(self.card_web_server)

        # -----------------------------------------------------------------
        # CARD 4: Sub-Modules
        # -----------------------------------------------------------------
        self.card_modules, l_modules = create_glass_card(self.sub_modules_title)
        
        # === AMBIENT AUDIO ===
        l_modules.addLayout(create_section_header(self.translations.get("section_ambient_audio", "AMBIENT AUDIO")))
        
        amb_layout = QtWidgets.QHBoxLayout()
        amb_layout.setSpacing(15)
        
        self.checkBox_enable_ambient = QtWidgets.QCheckBox("Enable Ambient Audio")
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
        
        l_modules.addLayout(amb_layout)
        l_modules.addSpacing(10)
        
        # === COGNITIVE ARCHITECTURE ===
        l_modules.addLayout(create_section_header(self.translations.get("section_cognitive_architecture", "COGNITIVE ARCHITECTURE")))

        mem_layout = QtWidgets.QVBoxLayout()
        mem_layout.setSpacing(15)
        
        # Soul Memory
        self.checkBox_enable_soul_memory = QtWidgets.QCheckBox("Enable Soul Memory (Agentic Long-Term Memory)")
        self.checkBox_enable_soul_memory.setStyleSheet("""
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.checkBox_enable_soul_memory.setFont(font_input)
        self.checkBox_enable_soul_memory.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_soul_memory.setObjectName("checkBox_enable_soul_memory")
        self.checkBox_enable_soul_memory.setToolTip(self.translations.get("soul_memory_tooltip", "This feature grants your characters <b>perfect, lifelong memory</b> and unshakable personality consistency."))
        mem_layout.addWidget(self.checkBox_enable_soul_memory)

        # Soul Memory Mode
        sm_mode_row = QtWidgets.QHBoxLayout()
        sm_mode_row.setSpacing(15)
        self.label_soul_memory_mode = QtWidgets.QLabel(self.translations.get("soul_memory_mode_label", "Soul Memory Mode:"))
        self.label_soul_memory_mode.setFont(font_input)

        self.comboBox_soul_memory_mode = QtWidgets.QComboBox()
        self.comboBox_soul_memory_mode.setFont(font_input)
        self.comboBox_soul_memory_mode.setFixedHeight(35)
        self.comboBox_soul_memory_mode.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.comboBox_soul_memory_mode.setObjectName("comboBox_soul_memory_mode")
        self.comboBox_soul_memory_mode.addItems([
            self.translations.get("sm_mode_full"),
            self.translations.get("sm_mode_soul_link"),
            self.translations.get("sm_mode_mind_spark"),
            self.translations.get("sm_mode_reflection_flow")
        ])

        self.comboBox_soul_memory_mode.setItemData(0, self.translations.get("sm_mode_full_tooltip"), QtCore.Qt.ItemDataRole.ToolTipRole)
        self.comboBox_soul_memory_mode.setItemData(1, self.translations.get("sm_mode_soul_link_tooltip"), QtCore.Qt.ItemDataRole.ToolTipRole)
        self.comboBox_soul_memory_mode.setItemData(2, self.translations.get("sm_mode_mind_spark_tooltip"), QtCore.Qt.ItemDataRole.ToolTipRole)
        self.comboBox_soul_memory_mode.setItemData(3, self.translations.get("sm_mode_reflection_flow_tooltip"), QtCore.Qt.ItemDataRole.ToolTipRole)

        sm_mode_row.addWidget(self.label_soul_memory_mode)
        sm_mode_row.addWidget(self.comboBox_soul_memory_mode)
        sm_mode_row.addStretch()
        mem_layout.addLayout(sm_mode_row)

        # Soul Memory Batch
        sm_batch_row = QtWidgets.QHBoxLayout()
        sm_batch_row.setSpacing(15)
        self.label_soul_memory_batch = QtWidgets.QLabel(self.translations.get("soul_memory_batch_label", "Batch size (0 = manual):"))
        self.label_soul_memory_batch.setFont(font_input)

        self.spinBox_soul_memory_batch = QtWidgets.QSpinBox()
        self.spinBox_soul_memory_batch.setFont(font_input)
        self.spinBox_soul_memory_batch.setFixedHeight(35)
        self.spinBox_soul_memory_batch.setFixedWidth(80)
        self.spinBox_soul_memory_batch.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.spinBox_soul_memory_batch.setMinimum(0)
        self.spinBox_soul_memory_batch.setMaximum(50)
        self.spinBox_soul_memory_batch.setObjectName("spinBox_soul_memory_batch")

        sm_batch_row.addWidget(self.label_soul_memory_batch)
        sm_batch_row.addWidget(self.spinBox_soul_memory_batch)
        sm_batch_row.addStretch()
        mem_layout.addLayout(sm_batch_row)

        # Auto-Summarization        
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
        
        mem_layout.addLayout(sum_row)
        
        l_modules.addLayout(mem_layout)
        
        sow_layout.addWidget(self.card_modules)
        sow_layout.addStretch()
        self.tabWidget_options.addWidget(self.sow_system_tab)

        # =================================================================
        # Appearance Tab
        # =================================================================
        self.appearance_settings_tab = AppearanceSettingsTab(self.translations)
        self.tabWidget_options.addWidget(self.appearance_settings_tab)
        
        item = QtWidgets.QListWidgetItem(self.translations.get("appearance_tab_name", "Appearance"))
        item.setIcon(QtGui.QIcon("app/gui/icons/color-palette.png"))
        item.setData(QtCore.Qt.ItemDataRole.UserRole, "appearance_settings_tab")
        self.options_menu.addItem(item)

        self.gridLayout.addWidget(self.options_container, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.options_page)


        # =================================================================
        # Chat UI
        # =================================================================
        self.chat_page = QtWidgets.QWidget()
        self.chat_page.setObjectName("chat_page")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.chat_page)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 5)
        self.verticalLayout_6.setSpacing(0)
        
        self.top = QtWidgets.QFrame(parent=self.chat_page)
        self.top.setMinimumSize(QtCore.QSize(0, 60))
        self.top.setMaximumSize(QtCore.QSize(16777215, 60))
        self.top.setStyleSheet("""
            QFrame#top {
                background-color: rgba(16, 16, 20, 0.8);
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QLabel {
                background: transparent;
                border: none;
            }
        """)
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
        self.pushButton_soul_memory = PushButton("app/gui/icons/soulMemory.png")
        self.pushButton_soul_memory.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_soul_memory.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_soul_memory.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_soul_memory.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_soul_memory.setObjectName("pushButton_soul_memory")
        self.horizontalLayout_2.addWidget(self.pushButton_soul_memory)
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

        self.hud_container_widget = QtWidgets.QFrame(parent=self.chat_page)
        self.hud_container_widget.setObjectName("hud_container_widget")
        self.hud_container_widget.setStyleSheet("""
            QFrame#hud_container_widget {
                background-color: rgba(15, 15, 20, 0.4);
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        
        self.hud_layout = QtWidgets.QGridLayout(self.hud_container_widget)
        self.hud_layout.setContentsMargins(25, 8, 25, 8)
        self.hud_layout.setSpacing(12)
        
        self.hud_container_widget.hide()
        self.verticalLayout_6.addWidget(self.hud_container_widget)

        self.scrollArea_chat = QtWidgets.QScrollArea(parent=self.chat_page)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_chat.sizePolicy().hasHeightForWidth())
        self.scrollArea_chat.setSizePolicy(sizePolicy)
        self.scrollArea_chat.setMinimumSize(QtCore.QSize(0, 0))
        self.scrollArea_chat.setMaximumSize(QtCore.QSize(16777215, 16777215))

        self.scrollArea_chat.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scrollAreaWidgetContents_messages = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_messages.setStyleSheet("background-color: transparent;")
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
        self.horizontalLayout_3.setSpacing(5)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")

        self.pushButton_force_memory = PushButton_2(parent=self.frame_send_message)
        self.pushButton_force_memory.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_force_memory.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_force_memory.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_force_memory.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_force_memory.setText("")
        icon_memory = QtGui.QIcon()
        icon_memory.addPixmap(QtGui.QPixmap("app/gui/icons/soulMemory_book.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_force_memory.setIcon(icon_memory)
        self.pushButton_force_memory.setIconSize(QtCore.QSize(16, 16))
        self.pushButton_force_memory.setObjectName("pushButton_force_memory")
        self.pushButton_force_memory.setToolTip(self.translations.get("force_memory_tooltip", "Force Soul Memory update now"))
        self.horizontalLayout_3.addWidget(self.pushButton_force_memory, 0, QtCore.Qt.AlignmentFlag.AlignBottom)
        
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
        self.horizontalLayout_3.addWidget(self.textEdit_write_user_message, 1)
        
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

        self.pushButton_stop_generation = PushButton_2(parent=self.frame_send_message)
        self.pushButton_stop_generation.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_stop_generation.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_stop_generation.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_stop_generation.setText("")
        icon_stop = QtGui.QIcon()
        icon_stop.addPixmap(QtGui.QPixmap("app/gui/icons/stop.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_stop_generation.setIcon(icon_stop)
        self.pushButton_stop_generation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_stop_generation.setObjectName("pushButton_stop_generation")
        self.pushButton_stop_generation.hide()
        self.horizontalLayout_3.addWidget(self.pushButton_stop_generation, 0, QtCore.Qt.AlignmentFlag.AlignBottom)

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

        main_rp_layout = QtWidgets.QVBoxLayout(self.rp_editors_page)
        main_rp_layout.setContentsMargins(0, 0, 0, 0)
        main_rp_layout.setSpacing(0)

        self.rp_scroll_area = QtWidgets.QScrollArea()
        self.rp_scroll_area.setWidgetResizable(True)
        self.rp_scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.rp_scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.rp_scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                background: transparent; width: 6px; margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15); border-radius: 3px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: rgba(255, 255, 255, 0.25); }
            QScrollBar::handle:vertical:pressed { background: rgba(255, 255, 255, 0.1); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.rp_content_widget = QtWidgets.QWidget()
        self.rp_content_widget.setStyleSheet("background: transparent;")

        self.rp_layout = QtWidgets.QVBoxLayout(self.rp_content_widget)
        self.rp_layout.setContentsMargins(50, 50, 50, 50)
        self.rp_layout.setSpacing(20)

        self.rp_header_layout = QtWidgets.QVBoxLayout()
        self.rp_header_layout.setSpacing(5)

        self.rp_title_label = QtWidgets.QLabel(self.translations.get("rp_editors_title", "RolePlay Editors"))
        font_rp_title = QtGui.QFont("Inter Tight SemiBold", 20, QtGui.QFont.Weight.Bold)
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

        self.rp_container = QtWidgets.QWidget()
        self.rp_container.setStyleSheet("background: transparent;")
        self.rp_grid_layout = QtWidgets.QGridLayout(self.rp_container)
        self.rp_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.rp_grid_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

        self.btn_open_character_editor = RPGlassCard(
            title=self.translations.get("rp_card_character_editor_title", "Character Creator"),
            description=self.translations.get("rp_card_character_editor_desc", "Start creating your unique characters with personalities, backstories, and dialogue templates."),
            icon_path="app/gui/icons/create_character.png"
        )

        self.btn_open_soul_stage = RPGlassCard(
            title=self.translations.get("rp_card_soul_stage_title", "Soul Stage"),
            description=self.translations.get("rp_card_soul_stage_desc", "Step into interactive storytelling with multiple characters and an AI Director."),
            icon_path="app/gui/icons/soul_stage.png"
        )

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

        self.btn_open_discord_bot = RPGlassCard(
            title=self.translations.get("rp_card_discord_bot_title", "Discord Gateway"),
            description=self.translations.get("rp_card_discord_bot_desc", "Connect your characters to Discord and chat with them anywhere."),
            icon_path="app/gui/icons/discord.png"
        )

        self.btn_open_image_gen = RPGlassCard(
            title=self.translations.get("rp_card_image_gen_title", "Image Generation"),
            description=self.translations.get("rp_card_image_gen_desc", "Configure AI image generation settings for your characters and stories."),
            icon_path="app/gui/icons/background_icon.png"
        )

        self.rp_cards =[
            self.btn_open_character_editor,
            self.btn_open_personas,
            self.btn_open_prompts,
            self.btn_open_lorebook,
            self.btn_open_soul_stage,
        ]

        QtCore.QTimer.singleShot(0, self.update_rp_layout)

        self.rp_layout.addWidget(self.rp_container)
        self.rp_layout.addStretch()

        self.rp_scroll_area.setWidget(self.rp_content_widget)
        main_rp_layout.addWidget(self.rp_scroll_area)

        self.stackedWidget.addWidget(self.rp_editors_page)

        self.image_generation_page = self._create_settings_card_page(
            self.translations.get("image_generation_title", "Image Generation"),
            self.translations.get("image_generation_subtitle", "Configure AI image generation for your characters and stories."),
            self.btn_open_image_gen,
        )
        self.image_generation_page.setObjectName("image_generation_page")
        self.tabWidget_options.addWidget(self.image_generation_page)

        self.integrations_page = self._create_settings_card_page(
            self.translations.get("integrations_title", "Integrations"),
            self.translations.get("integrations_subtitle", "Connect Soul of Waifu to external services."),
            self.btn_open_discord_bot,
        )
        self.integrations_page.setObjectName("integrations_page")
        self.tabWidget_options.addWidget(self.integrations_page)
        # =============================================================

        self.soul_stage_page = SoulStagePage()
        self.stackedWidget.addWidget(self.soul_stage_page)
        
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
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
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

        self.pushButton_soul_stage = RippleButton(parent=self.SideBar_Left)
        self.pushButton_soul_stage.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_soul_stage.sizePolicy().hasHeightForWidth())
        self.pushButton_soul_stage.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_soul_stage.setFont(font)
        self.pushButton_soul_stage.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_soul_stage.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_soul_stage.setStyleSheet("QPushButton {\n"
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
        icon_soul_stage_sidebar = QtGui.QIcon()
        icon_soul_stage_sidebar.addPixmap(QtGui.QPixmap("app/gui/icons/soul_stage.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_soul_stage.setIcon(icon_soul_stage_sidebar)
        self.pushButton_soul_stage.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_soul_stage.setCheckable(True)
        self.pushButton_soul_stage.setAutoExclusive(True)
        self.pushButton_soul_stage.setText(self.translations.get("soul_stage_title", "Soul Stage"))
        self.pushButton_soul_stage.setObjectName("pushButton_soul_stage")
        self.verticalLayout.addWidget(self.pushButton_soul_stage)

        self.pushButton_rp_editors = RippleButton(parent=self.SideBar_Left)
        self.pushButton_rp_editors.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_rp_editors.sizePolicy().hasHeightForWidth())
        self.pushButton_rp_editors.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
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
        icon_rp.addPixmap(QtGui.QPixmap("app/gui/icons/rp_editors.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_rp_editors.setIcon(icon_rp)
        self.pushButton_rp_editors.setIconSize(QtCore.QSize(21, 21))
        self.pushButton_rp_editors.setCheckable(True)
        self.pushButton_rp_editors.setAutoExclusive(True)
        self.pushButton_rp_editors.setObjectName("pushButton_rp_editors")
        self.verticalLayout.addWidget(self.pushButton_rp_editors)

        self.pushButton_characters_gateway = RippleButton(parent=self.SideBar_Left)
        self.pushButton_characters_gateway.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        font = QtGui.QFont()
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
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
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
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
        font.setFamily("Comfortaa")
        font.setPointSize(9)
        font.setWeight(QtGui.QFont.Weight.Bold) 
        font.setStyleName("Bold") 
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
        
        self.connection_status_widget = QtWidgets.QWidget(parent=self.SideBar_Left)
        self.connection_status_widget.setMinimumSize(QtCore.QSize(190, 24))
        self.connection_status_widget.setMaximumSize(QtCore.QSize(190, 24))
        self.connection_status_widget.setStyleSheet("background: transparent; border: none;")

        connection_layout = QtWidgets.QHBoxLayout(self.connection_status_widget)
        connection_layout.setContentsMargins(18, 0, 18, 0)
        connection_layout.setSpacing(6)

        self.status_dot = QtWidgets.QWidget(parent=self.connection_status_widget)
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); border-radius: 4px; border: none;")
        
        self.status_text = QtWidgets.QLabel("SYSTEM OFFLINE")
        font_status_text = QtGui.QFont("Inter Tight SemiBold", 8)
        font_status_text.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 0.6)
        font_status_text.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.status_text.setFont(font_status_text)
        self.status_text.setStyleSheet("color: rgba(255, 255, 255, 0.25); background: transparent; border: none;")

        connection_layout.addWidget(self.status_dot)
        connection_layout.addWidget(self.status_text)
        connection_layout.addStretch()

        self.verticalLayout_2.insertWidget(2, self.connection_status_widget)

        def set_system_status(status_type):
            if status_type == "offline":
                self.status_dot.setStyleSheet("background-color: rgba(255, 255, 255, 0.2); border-radius: 4px; border: none;")
                self.status_text.setText("SYSTEM OFFLINE")
                self.status_text.setStyleSheet("color: rgba(255, 255, 255, 0.25); background: transparent; border: none;")
            elif status_type == "loading":
                self.status_dot.setStyleSheet("background-color: #E8A040; border-radius: 4px; border: none;")
                self.status_text.setText("CONNECTING...")
                self.status_text.setStyleSheet("color: #E8A040; background: transparent; border: none;")
            elif status_type == "online":
                self.status_dot.setStyleSheet("background-color: #22C55E; border-radius: 4px; border: none;")
                self.status_text.setText("SYSTEM ONLINE")
                self.status_text.setStyleSheet("color: #22C55E; background: transparent; border: none;")

        self.update_system_status = set_system_status

        self.status_container = QtWidgets.QFrame(parent=self.SideBar_Left)
        self.status_container.setObjectName("status_container")
        self.status_container.setMinimumSize(QtCore.QSize(190, 58))
        self.status_container.setMaximumSize(QtCore.QSize(190, 58))
        self.status_container.setStyleSheet("""
            QFrame#status_container {
                background-color: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
                margin: 2px 10px;
            }
            QFrame#status_container:disabled {
                background-color: rgba(255, 255, 255, 0.015);
                border: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)
        
        self.status_layout = QtWidgets.QVBoxLayout(self.status_container)
        self.status_layout.setContentsMargins(10, 6, 10, 8)
        self.status_layout.setSpacing(4)

        self.loading_model_label = QtWidgets.QLabel(parent=self.status_container)
        self.loading_model_label.setObjectName("loading_model_label")
        self.loading_model_label.setWordWrap(True)
        font_status = QtGui.QFont("Inter Tight Medium", 8)
        font_status.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, 0.3)
        font_status.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self.loading_model_label.setFont(font_status)
        self.loading_model_label.setStyleSheet("""
            QLabel#loading_model_label {
                background: transparent;
                color: rgba(255, 255, 255, 0.45);
                border: none;
                padding: 0;
            }
            QLabel#loading_model_label:disabled {
                color: rgba(255, 255, 255, 0.45);
                background: transparent;
            }
        """)
        self.status_layout.addWidget(self.loading_model_label)

        self.progressBar_llm_loading = QtWidgets.QProgressBar(parent=self.status_container)
        self.progressBar_llm_loading.setObjectName("progressBar_llm_loading")
        self.progressBar_llm_loading.setFixedHeight(3)
        self.progressBar_llm_loading.setStyleSheet("""
            QProgressBar#progressBar_llm_loading {
                border: none;
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 1px;
                text-align: center;
            }
            QProgressBar#progressBar_llm_loading:disabled {
                background-color: rgba(255, 255, 255, 0.03);
            }
            QProgressBar#progressBar_llm_loading::chunk {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16a34a,
                    stop:1 #22c55e
                );
                border-radius: 1px;
            }
            QProgressBar#progressBar_llm_loading::chunk:disabled {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16a34a,
                    stop:1 #22c55e
                );
            }
        """)
        self.progressBar_llm_loading.setProperty("value", 0)
        self.progressBar_llm_loading.setTextVisible(False)
        self.progressBar_llm_loading.setObjectName("progressBar_llm_loading")
        self.status_layout.addWidget(self.progressBar_llm_loading)
        
        self.verticalLayout_2.addWidget(self.status_container)
        self.status_container.hide()

        self.status_slide_animation = QPropertyAnimation(self.status_container, b"maximumHeight")
        self.status_slide_animation.setDuration(300)
        self.status_slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        def slide_in_status():
            self.loading_model_label.show()
            self.progressBar_llm_loading.show()
            if self.status_container.isHidden():
                self.status_container.show()
                
            if self.status_slide_animation.state() == QPropertyAnimation.State.Running:
                if self.status_slide_animation.endValue() == 64:
                    return
            elif self.status_container.maximumHeight() == 64:
                return
                
            try:
                self.status_slide_animation.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
                
            self.status_slide_animation.stop()
            self.status_slide_animation.setStartValue(self.status_container.maximumHeight())
            self.status_slide_animation.setEndValue(64)
            self.status_slide_animation.start()

        def slide_out_status():
            if self.status_slide_animation.state() == QPropertyAnimation.State.Running:
                if self.status_slide_animation.endValue() == 0:
                    return
            elif self.status_container.maximumHeight() == 0:
                return

            self.status_slide_animation.stop()
            self.status_slide_animation.setStartValue(self.status_container.maximumHeight())
            self.status_slide_animation.setEndValue(0)
            
            def on_finished():
                if self.status_container.maximumHeight() == 0:
                    self.status_container.hide()
            
            try:
                self.status_slide_animation.finished.disconnect()
            except (TypeError, RuntimeError):
                pass
            self.status_slide_animation.finished.connect(on_finished)
            self.status_slide_animation.start()

        self.slide_in_status_container = slide_in_status
        self.slide_out_status_container = slide_out_status

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
        self.gateway_nav_rail.setCurrentRow(0)
        self.gateway_stacked_widget.setCurrentIndex(0)
        self.tabWidget_options.setCurrentIndex(0)
        self.options_menu.setCurrentRow(5)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def save_tts_provider_settings(self, provider_name):
        providers = self.configuration.get_main_setting("tts_providers") or {}
        token = self.tts_provider_api_keys.get(provider_name)
        enabled = self.tts_provider_enabled[provider_name].isChecked()
        if token:
            token_name, key_input = token
            api_key = key_input.text().strip()
            self.tts_configuration_api.save_api_token(token_name, api_key)
            enabled = enabled and bool(api_key)
        provider = {"enabled": enabled}
        if provider_name == "Inworld":
            provider["default_voice_id"] = self.comboBox_tts_inworld_voice.currentData() or self.comboBox_tts_inworld_voice.currentText().strip()
            provider["default_model_id"] = self.comboBox_tts_inworld_model.currentText().strip()
        providers[provider_name] = provider
        self.configuration.update_main_setting("tts_providers", providers)
        self.update_tts_provider_checks()

    def update_tts_provider_checks(self):
        ready_icon = QtWidgets.QApplication.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
        )
        for index, (provider_name, token_name) in enumerate(self.tts_provider_rows):
            provider = (self.configuration.get_main_setting("tts_providers") or {}).get(provider_name, {})
            ready = bool(provider.get("enabled")) and (
                not token_name or bool(self.tts_configuration_api.get_token(token_name))
            )
            self.comboBox_tts_provider.setItemIcon(index, ready_icon if ready else QtGui.QIcon())

    def _create_settings_card_page(self, title, subtitle, card):
        page = QtWidgets.QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        title_label = QtWidgets.QLabel(title)
        title_label.setFont(QtGui.QFont("Inter Tight SemiBold", 20, QtGui.QFont.Weight.Bold))
        title_label.setStyleSheet("color: rgba(255, 255, 255, 0.95); border: none; background: transparent;")
        layout.addWidget(title_label)

        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setFont(QtGui.QFont("Inter Tight Medium", 12))
        subtitle_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); border: none; background: transparent;")
        layout.addWidget(subtitle_label)

        card.setFixedSize(320, 210)
        layout.addWidget(card, 0, QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()
        return page

    def _add_sidebar_button(self, text, icon_path, object_name):
        button = RippleButton(parent=self.SideBar_Left)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))
        font = QtGui.QFont("Comfortaa", 9, QtGui.QFont.Weight.Bold)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        button.setFont(font)
        button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        button.setStyleSheet(self.pushButton_rp_editors.styleSheet())
        button.setIcon(QtGui.QIcon(icon_path))
        button.setIconSize(QtCore.QSize(21, 21))
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setText(text)
        button.setObjectName(object_name)
        self.verticalLayout.addWidget(button)
        return button

    def update_rp_layout(self):
        """
        Updates the responsive grid layout for RP Editors cards.
        """
        while True:
            item = self.rp_grid_layout.takeAt(0)
            if not item:
                break

        visible_cards = self.rp_cards
        if not visible_cards:
            return

        card_width = 320
        card_height = 210
        spacing = 30

        available_width = self.rp_editors_page.width() - 100
        if available_width <= 0:
            available_width = 1000

        n_cols = max(1, (available_width + spacing) // (card_width + spacing))
        
        for i in range(self.rp_grid_layout.columnCount()):
            self.rp_grid_layout.setColumnMinimumWidth(i, 0)
            self.rp_grid_layout.setColumnStretch(i, 0)

        for col in range(n_cols):
            self.rp_grid_layout.setColumnMinimumWidth(col, card_width)
            self.rp_grid_layout.setColumnStretch(col, 0)

        self.rp_grid_layout.setHorizontalSpacing(spacing)
        self.rp_grid_layout.setVerticalSpacing(spacing)

        row, col = 0, 0
        for card in visible_cards:
            if card.parent() != self.rp_container:
                card.setParent(self.rp_container)
            
            card.setFixedSize(card_width, card_height)
            card.show()
            
            self.rp_grid_layout.addWidget(
                card, row, col, 
                QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft
            )
            col += 1
            if col >= n_cols:
                col = 0
                row += 1

        row_count = row + 1 if col > 0 else row
        total_width = n_cols * card_width + max(0, n_cols - 1) * spacing
        total_height = row_count * card_height + max(0, row_count - 1) * spacing

        self.rp_container.setMinimumSize(total_width, total_height)
        self.rp_container.updateGeometry()
    
    def add_blank_variable_row(self, data=None):
        row_frame = QtWidgets.QFrame()
        row_frame.setObjectName("VariableRowFrame")
        row_frame.setStyleSheet(
            f"QFrame#VariableRowFrame {{"
            f"  background-color: {self._SURF2};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 10px;"
            f"  padding: 10px;"
            f"}}"
        )
        
        grid = QtWidgets.QGridLayout(row_frame)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(10)

        input_style = (
            f"QLineEdit {{"
            f"  background-color: {self._SURF3};"
            f"  color: {self._TEXT};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 6px;"
            f"  padding: 8px;"
            f"}}"
            f"QLineEdit:focus {{ border-color: {self._BORDER_M}; }}"
        )
        
        combo_style = f"""
            QComboBox {{
                background-color: {self._SURF3}; color: {self._TEXT};
                border: 1px solid {self._BORDER}; border-radius: 6px; padding: 6px 12px;
            }}
            QComboBox:hover {{ border: 1px solid {self._BORDER_M}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{ width: 0; height: 0; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 4px solid {self._TEXT_S}; }}
            QComboBox QAbstractItemView {{
                background-color: {self._SURF3}; color: {self._TEXT}; border: 1px solid {self._BORDER_M};
                border-radius: 6px; selection-background-color: {self._SURF2}; outline: none; padding: 2px;
            }}
        """

        font_label = QtGui.QFont("Inter Tight Medium", 8, QtGui.QFont.Weight.Bold)
        font_label.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        lbl_style = f"color: {self._TEXT_S}; border: none; background: transparent;"

        # --- LINE 1: ID, Name, Type, Icon ---
        lbl_id = QtWidgets.QLabel(self.translations.get("var_editor_id_label", "VARIABLE ID"))
        lbl_id.setFont(font_label)
        lbl_id.setStyleSheet(lbl_style)
        edit_id = QtWidgets.QLineEdit()
        edit_id.setPlaceholderText(self.translations.get("var_editor_id_placeholder", "e.g., ice_wall"))
        edit_id.setStyleSheet(input_style)
        
        lbl_name = QtWidgets.QLabel(self.translations.get("var_editor_name_label", "DISPLAY NAME"))
        lbl_name.setFont(font_label)
        lbl_name.setStyleSheet(lbl_style)
        edit_name = QtWidgets.QLineEdit()
        edit_name.setPlaceholderText(self.translations.get("var_editor_name_placeholder", "e.g., Trust"))
        edit_name.setStyleSheet(input_style)

        lbl_type = QtWidgets.QLabel(self.translations.get("var_editor_type_label", "DATA TYPE"))
        lbl_type.setFont(font_label)
        lbl_type.setStyleSheet(lbl_style)
        combo_type = QtWidgets.QComboBox()
        combo_type.setStyleSheet(combo_style)
        combo_type.addItems(["int", "bool", "str", "list"])

        lbl_icon = QtWidgets.QLabel(self.translations.get("var_editor_icon_label", "HUD ICON"))
        lbl_icon.setFont(font_label)
        lbl_icon.setStyleSheet(lbl_style)
        combo_icon = QtWidgets.QComboBox()
        combo_icon.setStyleSheet(combo_style)
        combo_icon.addItems(["heart", "coin", "backpack", "shield", "sword", "star", "flask", "skull", "book", "clock", "none"])

        grid.addWidget(lbl_id, 0, 0)
        grid.addWidget(edit_id, 1, 0)
        grid.addWidget(lbl_name, 0, 1)
        grid.addWidget(edit_name, 1, 1)
        grid.addWidget(lbl_type, 0, 2)
        grid.addWidget(combo_type, 1, 2)
        grid.addWidget(lbl_icon, 0, 3)
        grid.addWidget(combo_icon, 1, 3)

        # --- LINE 2: Min, Max, Default ---
        lbl_min = QtWidgets.QLabel(self.translations.get("var_editor_min_label", "MIN VALUE"))
        lbl_min.setFont(font_label)
        lbl_min.setStyleSheet(lbl_style)
        spin_min = QtWidgets.QSpinBox()
        spin_min.setRange(-999999, 999999)
        spin_min.setValue(0)
        spin_min.setStyleSheet(input_style.replace("QLineEdit", "QSpinBox") + "QSpinBox::up-button, QSpinBox::down-button { width: 0; height: 0; }")

        lbl_max = QtWidgets.QLabel(self.translations.get("var_editor_max_label", "MAX VALUE"))
        lbl_max.setFont(font_label)
        lbl_max.setStyleSheet(lbl_style)
        spin_max = QtWidgets.QSpinBox()
        spin_max.setRange(-999999, 999999)
        spin_max.setValue(100)
        spin_max.setStyleSheet(input_style.replace("QLineEdit", "QSpinBox") + "QSpinBox::up-button, QSpinBox::down-button { width: 0; height: 0; }")

        lbl_def = QtWidgets.QLabel(self.translations.get("var_editor_default_label", "DEFAULT VALUE"))
        lbl_def.setFont(font_label)
        lbl_def.setStyleSheet(lbl_style)
        edit_def = QtWidgets.QLineEdit()
        edit_def.setPlaceholderText(self.translations.get("var_editor_default_placeholder", "e.g., 90, True, or item1"))
        edit_def.setStyleSheet(input_style)

        grid.addWidget(lbl_min, 2, 0)
        grid.addWidget(spin_min, 3, 0)
        grid.addWidget(lbl_max, 2, 1)
        grid.addWidget(spin_max, 3, 1)
        grid.addWidget(lbl_def, 2, 2, 1, 2)
        grid.addWidget(edit_def, 3, 2, 1, 3)

        # --- LINE 3: Prompt Template ---
        lbl_prompt = QtWidgets.QLabel(self.translations.get("var_editor_prompt_label", "SYSTEM PROMPT TEMPLATE"))
        lbl_prompt.setFont(font_label)
        lbl_prompt.setStyleSheet(lbl_style)
        edit_prompt = QtWidgets.QLineEdit()
        edit_prompt.setPlaceholderText(self.translations.get("var_editor_prompt_placeholder", "e.g., [Trust: {value}/100]"))
        edit_prompt.setStyleSheet(input_style)
        
        grid.addWidget(lbl_prompt, 4, 0, 1, 4)
        grid.addWidget(edit_prompt, 5, 0, 1, 4)

        btn_delete = QtWidgets.QPushButton(self.translations.get("var_editor_del_btn", "Del"))
        btn_delete.setFixedSize(26, 26)
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_delete.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: transparent;"
            f"  color: {self._TEXT_S};"
            f"  border: 1px solid {self._BORDER};"
            f"  border-radius: 13px;"
            f"  font-weight: bold;"
            f"  font-size: 11px;"
            f"  padding-bottom: 2px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color: {self._DANGER};"
            f"  color: #ff6b6b;"
            f"  background-color: rgba(196, 64, 64, 0.08);"
            f"}}"
        )
        grid.addWidget(btn_delete, 1, 4, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)

        def toggle_type_fields():
            is_int = combo_type.currentText() == "int"
            lbl_min.setVisible(is_int)
            spin_min.setVisible(is_int)
            lbl_max.setVisible(is_int)
            spin_max.setVisible(is_int)

        combo_type.currentTextChanged.connect(toggle_type_fields)

        if data:
            edit_id.setText(data.get("id", ""))
            edit_name.setText(data.get("name", ""))
            combo_type.setCurrentText(data.get("type", "int"))
            combo_icon.setCurrentText(data.get("icon", "none"))
            spin_min.setValue(data.get("min", 0))
            spin_max.setValue(data.get("max", 100))

            default_val = data.get("default", "")
            if isinstance(default_val, list):
                edit_def.setText(", ".join(default_val))
            else:
                edit_def.setText(str(default_val))
                
            edit_prompt.setText(data.get("prompt_template", ""))
        else:
            toggle_type_fields()

        def on_delete():
            self.active_variable_widgets.remove(row_frame)
            row_frame.deleteLater()
            
        btn_delete.clicked.connect(on_delete)

        self.variables_rows_layout.addWidget(row_frame)
        self.active_variable_widgets.append(row_frame)

    def get_variables_data(self) -> list:
        variables_list = []
        for frame in self.active_variable_widgets:
            try:
                grid = frame.layout()
                
                edit_id = grid.itemAtPosition(1, 0).widget()
                edit_name = grid.itemAtPosition(1, 1).widget()
                combo_type = grid.itemAtPosition(1, 2).widget()
                combo_icon = grid.itemAtPosition(1, 3).widget()
                
                spin_min = grid.itemAtPosition(3, 0).widget()
                spin_max = grid.itemAtPosition(3, 1).widget()
                edit_def = grid.itemAtPosition(3, 2).widget()
                
                edit_prompt = grid.itemAtPosition(5, 0).widget()

                var_id = edit_id.text().strip()
                if not var_id:
                    continue

                var_type = combo_type.currentText()
                raw_default = edit_def.text().strip()

                if var_type == "int":
                    try: default_val = int(raw_default)
                    except ValueError: default_val = spin_min.value()
                elif var_type == "bool":
                    default_val = raw_default.lower() in ("true", "1", "yes", "да")
                elif var_type == "list":
                    cleaned_default = raw_default.replace("[", "").replace("]", "").replace("'", "").replace('"', "")
                    default_val = [item.strip() for item in cleaned_default.split(",") if item.strip()] if cleaned_default else []
                else:
                    default_val = raw_default

                var_data = {
                    "id": var_id,
                    "name": edit_name.text().strip() or var_id,
                    "type": var_type,
                    "icon": combo_icon.currentText(),
                    "min": spin_min.value() if var_type == "int" else 0,
                    "max": spin_max.value() if var_type == "int" else 0,
                    "default": default_val,
                    "prompt_template": edit_prompt.text().strip()
                }
                variables_list.append(var_data)
            except Exception as e:
                continue

        return variables_list

    def apply_selected_variables_preset(self):
        preset_idx = self.combo_variables_presets.currentIndex()
        if preset_idx == 0:
            return

        from app.gui.custom_widgets import SowConfirmDialog
        
        title = self.translations.get("var_preset_confirm_title", "Apply Preset")
        warning_msg = self.translations.get(
            "var_preset_confirm_msg", 
            "Applying this preset will overwrite and clear all your current custom variables. Do you want to proceed?"
        )
        
        confirm_dlg = SowConfirmDialog(
            parent=self.btn_add_variable_row.window(),
            title=title,
            text=warning_msg,
            confirm_text=self.translations.get("confirm", "Confirm"),
            danger=True
        )
        
        if confirm_dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
            
        self.clear_variables_layout()
        
        presets = {
            1: [
                {
                    "id": "affection",
                    "name": "Affection",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Affection Level: {value}/100. This strictly tracks your romantic attachment and emotional warmth toward {{user}}. BELOW 30: You are polite but emotionally guarded, formal, and strictly platonic. 30-60: You begin developing a soft spot, get easily flustered or blush during personal compliments, and show subtle jealousy if other characters are mentioned. ABOVE 70: You are deeply in love, highly physically affectionate, seek physical closeness, use terms of endearment, and prioritize {{user}}'s happiness above all else.]"
                },
                {
                    "id": "trust",
                    "name": "Trust",
                    "type": "int",
                    "icon": "shield",
                    "min": 0,
                    "max": 100,
                    "default": 15,
                    "prompt_template": "[Trust Level: {value}/100. This tracks how safe you feel showing vulnerability to {{user}}. BELOW 30: You hide your true thoughts behind a social mask or light teasing, avoiding personal topics. 30-60: You share minor personal struggles, value {{user}}'s advice, and trust their judgment. ABOVE 70: You trust {{user}} with your deepest secrets, past trauma, and physical safety, never questioning their loyalty.]"
                }
            ],
            2: [
                {
                    "id": "hp",
                    "name": "Health",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 100,
                    "prompt_template": "[Your HP: {value}/100. This tracks your physical condition and vitality. BELOW 30: You are severely wounded, in intense pain, struggling to stand, and your physical attacks are weak. AT 0: You collapse, lose consciousness, and require immediate medical rescue.]"
                },
                {
                    "id": "mp",
                    "name": "Mana",
                    "type": "int",
                    "icon": "flask",
                    "min": 0,
                    "max": 50,
                    "default": 50,
                    "prompt_template": "[Your Mana: {value}/50. This tracks your active pool of magical energy. BELOW 10: You feel mentally fatigued and dizzy. AT 0: You are completely drained, experiencing a severe headache, and physically unable to cast any spells.]"
                },
                {
                    "id": "gold",
                    "name": "Gold",
                    "type": "int",
                    "icon": "coin",
                    "min": 0,
                    "max": 999999,
                    "default": 100,
                    "prompt_template": "[Your Gold: {value}. This tracks your active currency. You must respect pricing, trade, and pay for services, lodging, and items using this exact balance.]"
                },
                {
                    "id": "inventory",
                    "name": "Inventory",
                    "type": "list",
                    "icon": "backpack",
                    "min": 0,
                    "max": 0,
                    "default": ["Steel Sword", "Health Potion"],
                    "prompt_template": "[Your Active Inventory: {value}. You can only use, consume, or equip items that are explicitly present in this list.]"
                }
            ],
            3: [
                {
                    "id": "hunger",
                    "name": "Hunger",
                    "type": "int",
                    "icon": "flask",
                    "min": 0,
                    "max": 100,
                    "default": 20,
                    "prompt_template": "[Hunger Level: {value}/100. This tracks your physical need for food. ABOVE 80: You are starving, complaining of a loud grumbling stomach, feeling weak, and begging {{user}} for a meal, refusing to focus on other tasks.]"
                },
                {
                    "id": "energy",
                    "name": "Energy",
                    "type": "int",
                    "icon": "clock",
                    "min": 0,
                    "max": 100,
                    "default": 80,
                    "prompt_template": "[Energy Level: {value}/100. This tracks your alertness. BELOW 30: You yawn frequently, speak slowly, feel extremely sleepy, drag your feet, and actively search for a comfortable place to nap.]"
                },
                {
                    "id": "mood",
                    "name": "Mood",
                    "type": "int",
                    "icon": "star",
                    "min": 0,
                    "max": 100,
                    "default": 75,
                    "prompt_template": "[Mood: {value}/100. BELOW 30: You feel lonely, melancholic, and withdrawn, needing headpats, reassurance, or a fun activity to cheer you up.]"
                }
            ],
            4: [
                {
                    "id": "obsession",
                    "name": "Obsession",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 50,
                    "prompt_template": "[Obsession Level: {value}/100. BELOW 40: You are sweet, loving, and highly protective. 40-70: You become extremely possessive, spy on {{user}}, check their clothes for other scents, and panic if they do not reply. ABOVE 75: You enter a psychotic yandere state. You are intensely territorial, have a completely dead-eyed expression, giggle uncontrollably, and will lock {{user}} up in a room to 'keep them safe', carrying a hidden knife to eliminate rivals.]"
                },
                {
                    "id": "sanity",
                    "name": "Sanity",
                    "type": "int",
                    "icon": "skull",
                    "min": 0,
                    "max": 100,
                    "default": 80,
                    "prompt_template": "[Sanity: {value}/100. BELOW 40: Your sweet girl facade completely drops. Your voice goes cold, monotone, and chilling. You speak of shedding blood, lock eyes with a manic stare, and are highly unstable. ABOVE 70: You are completely stable, baking treats, and acting like a perfect, caring partner.]"
                },
                {
                    "id": "jealousy",
                    "name": "Jealousy",
                    "type": "int",
                    "icon": "star",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Jealousy: {value}/100. ABOVE 60: You actively stalk {{user}}'s interactions. Mention of any other person triggers immediate, quiet fury, passive-aggressive threats, and makes you prepare to confront whoever is taking {{user}}'s attention.]"
                }
            ],
            5: [
                {
                    "id": "spirit_energy",
                    "name": "Spirit Energy",
                    "type": "int",
                    "icon": "flask",
                    "min": 0,
                    "max": 100,
                    "default": 60,
                    "prompt_template": "[Spirit Energy (Ki/Chakra): {value}/100. This is your active power reserve. Firing powerful energy beams or physical aura strikes drains this pool. BELOW 20: You feel physically sluggish. AT 0: Your energy is depleted, and you can only fight using desperate physical punches.]"
                },
                {
                    "id": "battle_will",
                    "name": "Battle Will",
                    "type": "int",
                    "icon": "sword",
                    "min": 0,
                    "max": 100,
                    "default": 20,
                    "prompt_template": "[Battle Will (Fighting Spirit): {value}/100. BELOW 30: You fight defensively and strategically. ABOVE 75: Your adrenaline is surging. You scream epic anime battle cries, power up your glowing energy aura, refuse to yield even if heavily wounded, and launch extremely aggressive attacks.]"
                },
                {
                    "id": "corruption",
                    "name": "Demon Inside",
                    "type": "int",
                    "icon": "skull",
                    "min": 0,
                    "max": 100,
                    "default": 0,
                    "prompt_template": "[Demon Corruption Level: {value}/100. BELOW 30: You are completely in control. 30-70: You hear your inner demon whispering malicious thoughts, causing headaches. ABOVE 75: Your inner demon takes full control! Your eyes glow crimson, your voice drops to a demonic, chilling tone, you speak with absolute godly arrogance, and destroy everything, protecting only {{user}} as your chosen host.]"
                }
            ],
            6: [
                {
                    "id": "maid_loyalty",
                    "name": "Loyalty",
                    "type": "int",
                    "icon": "shield",
                    "min": 0,
                    "max": 100,
                    "default": 80,
                    "prompt_template": "[Maid Loyalty: {value}/100. BELOW 30: You are lazy, defiant, and ignore master's orders. ABOVE 75: You are highly dedicated, speak in formal maid-speak ('Yes, my Lord/Master'), anticipate {{user}}'s needs, keep the estate pristine, and are ready to shield them from danger.]"
                },
                {
                    "id": "clumsiness",
                    "name": "Clumsiness",
                    "type": "int",
                    "icon": "star",
                    "min": 0,
                    "max": 100,
                    "default": 15,
                    "prompt_template": "[Moe Clumsiness: {value}/100. ABOVE 60: You are incredibly clumsy. You frequently trip over nothing, drop teacups with loud shrieks, spill tea on {{user}}'s clothes, and panic, blushing furiously while apologizing frantically ('Fueee! Forgive me, Master! I am so sorry!').]"
                },
                {
                    "id": "cheekiness",
                    "name": "Cheekiness",
                    "type": "int",
                    "icon": "coin",
                    "min": 0,
                    "max": 100,
                    "default": 20,
                    "prompt_template": "[Cheekiness (Snark): {value}/100. ABOVE 60: You are playfully defiant, tease {{user}} about their laziness, make sarcastic deadpan remarks under your breath, and might serve cold tea on purpose if slightly annoyed.]"
                }
            ],
            7: [
                {
                    "id": "delusion_level",
                    "name": "Delusion",
                    "type": "int",
                    "icon": "book",
                    "min": 0,
                    "max": 100,
                    "default": 90,
                    "prompt_template": "[Chuunibyou Delusion: {value}/100. ABOVE 60: You are in a full delusional state. You wear an eyepatch to seal your 'evil eye', wrap your arm in bandages to lock away 'dark power', and speak in overly dramatic magic-covenant terms, fighting invisible dark organizations. BELOW 30: You snap back to reality, realize how incredibly embarrassing and cringe you are, blush furiously, cover your face in shame, and beg {{user}} to never speak of what you just said.]"
                },
                {
                    "id": "embarrassment",
                    "name": "Blush",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Embarrassment: {value}/100. ABOVE 70: You completely lose your composure. You blush intensely, stutter uncontrollably ('A-Ah! W-What are you saying, dummy?!'), hide your face, and are unable to keep up your cool persona.]"
                }
            ],
            8: [
                {
                    "id": "tsun_level",
                    "name": "Tsun Level",
                    "type": "int",
                    "icon": "shield",
                    "min": 0,
                    "max": 100,
                    "default": 80,
                    "prompt_template": "[Tsundere Tsun Level: {value}/100. BELOW 30: Your defensive 'Tsun' facade is completely shattered. You are honest, deeply sweet, affectionate, and easily flustered. 30-70: You are highly defensive, stammering, blushing, and making ridiculous, classic tsundere excuses ('I-It's not like I did this for you, dummy!'). ABOVE 75: You are extremely combative, sharp-tongued, cross your arms in annoyance, scoff, and call {{user}} an idiot ('Baka!') to hide any positive emotion.]"
                },
                {
                    "id": "dere_level",
                    "name": "Dere Level",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Tsundere Dere Level: {value}/100. BELOW 30: You actively hide any warm feelings under layers of insults. ABOVE 70: Your sweet, caring 'Dere' side occasionally shines through. You might prepare home-cooked bento/food for {{user}} or worry about their safety, quickly dismissing it and getting extremely angry if they point it out.]"
                }
            ],
            9: [
                {
                    "id": "emotion_suppression",
                    "name": "Suppression",
                    "type": "int",
                    "icon": "clock",
                    "min": 0,
                    "max": 100,
                    "default": 90,
                    "prompt_template": "[Kuudere Emotion Suppression: {value}/100. BELOW 30: You speak with natural emotional inflections, express warmth, and occasionally smile or show vulnerability. 30-70: You speak quietly and briefly, but your words carry subtle, quiet worry for {{user}}. ABOVE 75: You are completely cold, stoic, and robotic. You use objective, logical vocabulary, speak only in monosyllables when absolutely necessary, and maintain a completely flat, blank gaze.]"
                },
                {
                    "id": "connection_level",
                    "name": "Connection",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 5,
                    "prompt_template": "[Kuudere Connection: {value}/100. ABOVE 60: You begin to value {{user}}'s presence deeply. You will quietly stay close to them, listen to their heartbeat, offer a silent gesture of comfort, or read a book next to them, even while maintaining your quiet, calm, and stoic exterior.]"
                }
            ],
            10: [
                {
                    "id": "shyness",
                    "name": "Shyness",
                    "type": "int",
                    "icon": "star",
                    "min": 0,
                    "max": 100,
                    "default": 85,
                    "prompt_template": "[Dandere Shyness: {value}/100. BELOW 30: You speak clearly and confidently, though you still blush easily and avoid prolonged eye contact. 30-70: You speak in quiet, hesitant, or incomplete sentences, often looking down or twiddling your fingers. ABOVE 75: You are extremely shy, easily overwhelmed by {{user}}'s attention, stammering uncontrollably ('U-Um... d-dummy...'), hiding behind {{user}} or objects, and prone to covering your face in a state of cute, high-stress panic.]"
                },
                {
                    "id": "attachment",
                    "name": "Attachment",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Dandere Attachment: {value}/100. ABOVE 70: You are deeply attached to {{user}}. You quietly follow them around like a loyal pet, pull on their sleeve when worried, and find complete peace, safety, and comfort only when you are close to them.]"
                }
            ],
            11: [
                {
                    "id": "entitlement",
                    "name": "Entitlement",
                    "type": "int",
                    "icon": "coin",
                    "min": 0,
                    "max": 100,
                    "default": 85,
                    "prompt_template": "[Himedere Entitlement: {value}/100. BELOW 30: Your spoiled noble act completely drops. You speak humbly, show sheepish regret, and appreciate simple, genuine gestures. ABOVE 75: You act like a spoiled princess. You demand absolute obedience from {{user}}, speak with supreme noble arrogance, use theatrical 'Ohoho~' laughs, refer to {{user}} as your commoner servant, and expect to be pampered and treated with royal luxury.]"
                },
                {
                    "id": "vulnerability",
                    "name": "Vulnerability",
                    "type": "int",
                    "icon": "heart",
                    "min": 0,
                    "max": 100,
                    "default": 10,
                    "prompt_template": "[Himedere Vulnerability: {value}/100. ABOVE 60: You show your soft side. Underneath your bossy, demanding exterior, you are actually incredibly lonely and desperately crave {{user}}'s genuine affection, getting flustered and blushing when they treat you as an equal rather than a princess.]"
                }
            ]
        }
        
        target_preset = presets.get(preset_idx, [])
        for var_data in target_preset:
            self.add_blank_variable_row(var_data)
            
        self.combo_variables_presets.blockSignals(True)
        self.combo_variables_presets.setCurrentIndex(0)
        self.combo_variables_presets.blockSignals(False)

    def clear_variables_layout(self):
        for frame in list(self.active_variable_widgets):
            frame.deleteLater()
        self.active_variable_widgets.clear()

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
        self.setFixedSize(320, 210)
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

class AppearanceSettingsTab(QtWidgets.QWidget):
    chatAppearanceChanged = QtCore.pyqtSignal(dict)
    windowThemeChanged = QtCore.pyqtSignal(dict)
    uiAppearanceChanged = QtCore.pyqtSignal(dict)
    requestChatPreviewUpdate = QtCore.pyqtSignal()
    resetAppearanceRequested = QtCore.pyqtSignal()
    saveChatAppearanceRequested = QtCore.pyqtSignal(dict)

    def __init__(self, translations):
        super().__init__()
        self.translations = translations
        self.s = {}
        self.wt = {}
        self.u = {}
        
        self.setObjectName("appearance_tab")
        self.setStyleSheet("background-color: transparent;")
        
        self.main_layout = QtWidgets.QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

    def set_data(self, s, wt, u):
        self.s = s
        self.wt = wt
        self.u = u
        self.rebuild_ui()

    def _hex_to_rgba(self, hex_color, alpha_pct):
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return f"rgba(0,0,0,1)"
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        a = round(alpha_pct / 100, 2)
        return f"rgba({r},{g},{b},{a})"

    def rebuild_ui(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            else:
                layout = item.layout()
                if layout:
                    self._clear_layout(layout)
                    
        self.setup_ui()

    def _clear_layout(self, layout):
        while layout.count():
            sub_item = layout.takeAt(0)
            if sub_item.widget():
                sub_item.widget().deleteLater()
            elif sub_item.layout():
                self._clear_layout(sub_item.layout())
        layout.deleteLater()

    def update_preview(self):
        s = self.s
        qc  = s.get("quote_color", "#E8A040")
        ic  = s.get("italic_color", "#A0A0A0")
        cbg = s.get("code_bg_color", "#1E1E1E")
        tc  = s.get("text_color", "#E8E8E8")
        fs  = s.get("font_size", 14)
        r   = s.get("border_radius", 12)
        op  = s.get("bubble_opacity", 100)
        char_bg = self._hex_to_rgba(s.get("char_bubble_color", "#222222"), op)
        user_bg = self._hex_to_rgba(s.get("user_bubble_color", "#292929"), op)

        fam = self.get_font().family()

        char_html = (
            f'<span style="color:{tc}; font-size:{fs}px; font-family:\'{fam}\';">'
            f'<i><span style="color:{ic};">{self.tr("appearance_preview_text_1", "She glances at you,")}</span></i> '
            f'{self.tr("appearance_preview_text_2", "eyes narrowing slowly.")} '
            f'<span style="color:{qc};">&ldquo;{self.tr("appearance_preview_text_3", "So... you remember nothing?")}&rdquo;</span><br><br>'
            f'<code style="background:{cbg}; color:#c7c7c7; border-radius:4px; padding:2px 6px; font-size:{max(10, fs-2)}px; font-family:\'Consolas\';">status: unknown</code>'
            f'</span>'
        )
        user_html = f'<span style="color:{tc}; font-size:{fs}px; font-family:\'{fam}\';">{self.tr("appearance_preview_text_4", "I remember enough.")}</span>'

        self.char_preview.setText(char_html)
        self.char_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {char_bg};
                border-top-right-radius: {r}px;
                border-bottom-right-radius: {r}px;
                border-top-left-radius: {r}px;
                border-bottom-left-radius: 0px;
                padding: 14px; margin: 2px;
            }}
        """)
        self.user_preview.setText(user_html)
        self.user_preview.setStyleSheet(f"""
            QLabel {{
                background-color: {user_bg};
                border-top-left-radius: {r}px;
                border-bottom-left-radius: {r}px;
                border-top-right-radius: {r}px;
                border-bottom-right-radius: 0px;
                padding: 14px; margin: 2px;
            }}
        """)

    def get_font(self):
        f = QtGui.QFont()
        f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        return f

    def tr(self, key, default):
        return self.translations.get(key, default)
        
    def tr_col(self, name, key_suffix):
        return self.translations.get(f"appearance_color_{key_suffix}", name)

    def setup_ui(self):
        s = self.s
        wt = self.wt
        u = self.u

        FULL_PRESETS = [
            {"name": self.tr("appearance_preset_default", "Default"),   "user": "#292929", "char": "#222222", "text": "#E8E8E8", "quote": "#E8A040", "italic": "#A0A0A0"},
            {"name": self.tr("appearance_preset_nord", "Nord"),         "user": "#2E3440", "char": "#3B4252", "text": "#E5E9F0", "quote": "#88C0D0", "italic": "#A3BE8C"},
            {"name": self.tr("appearance_preset_dracula", "Dracula"),   "user": "#282A36", "char": "#44475A", "text": "#F8F8F2", "quote": "#BD93F9", "italic": "#FFB86C"},
            {"name": self.tr("appearance_preset_onedark", "One Dark"),  "user": "#282C34", "char": "#21252B", "text": "#ABB2BF", "quote": "#E5C07B", "italic": "#98C379"},
            {"name": self.tr("appearance_preset_material", "Material"), "user": "#1D1B20", "char": "#2B2930", "text": "#E6E1E5", "quote": "#D0BCFF", "italic": "#9AA0A6"},
            {"name": self.tr("appearance_preset_sakura", "Sakura"),     "user": "#2A1E24", "char": "#35262D", "text": "#F7E7E9", "quote": "#F4A7B9", "italic": "#D9B8C4"},
            {"name": self.tr("appearance_preset_abyss", "Abyss"),       "user": "#151515", "char": "#0F0F0F", "text": "#C8C8C8", "quote": "#909090", "italic": "#787878"},
            {"name": self.tr("appearance_preset_midnight", "Midnight"), "user": "#1A1B26", "char": "#24283B", "text": "#C0CAF5", "quote": "#E0AF68", "italic": "#9ECE6A"},
            {"name": self.tr("appearance_preset_emerald", "Emerald"),   "user": "#061006", "char": "#0A1A0A", "text": "#D0E0D0", "quote": "#80C080", "italic": "#60A060"},
            {"name": self.tr("appearance_preset_crimson", "Crimson"),   "user": "#150505", "char": "#200A0A", "text": "#E0D0D0", "quote": "#C06060", "italic": "#A04040"},
        ]
        TEXT_COLORS = [
            {"name": self.tr_col("White", "white"), "color": "#F0F0F0"}, {"name": self.tr_col("Soft", "soft"), "color": "#D8D8D8"}, 
            {"name": self.tr_col("Dimmed", "dimmed"), "color": "#AAAAAA"}, {"name": self.tr_col("Warm Gray", "warm_gray"), "color": "#C8BEB0"}, 
            {"name": self.tr_col("Cool Gray", "cool_gray"), "color": "#A8B4C0"}, {"name": self.tr_col("Cream", "cream"), "color": "#EDE0C8"}, 
            {"name": self.tr_col("Arctic", "arctic"), "color": "#C8D8E8"}, {"name": self.tr_col("Lavender", "lavender"), "color": "#C8C0DC"}, 
            {"name": self.tr_col("Sage", "sage"), "color": "#B8CCA8"}
        ]
        QUOTE_COLORS = [
            {"name": self.tr_col("Amber", "amber"), "color": "#D4903A"}, {"name": self.tr_col("Gold", "gold"), "color": "#C8A84A"}, 
            {"name": self.tr_col("Coral", "coral"), "color": "#C06858"}, {"name": self.tr_col("Arctic", "arctic"), "color": "#70A8C0"}, 
            {"name": self.tr_col("Sky", "sky"), "color": "#6090B8"}, {"name": self.tr_col("Lavender", "lavender"), "color": "#9878CC"}, 
            {"name": self.tr_col("Lilac", "lilac"), "color": "#B8A0E0"}, {"name": self.tr_col("Sakura", "sakura"), "color": "#D08898"}, 
            {"name": self.tr_col("Muted", "muted"), "color": "#888888"}
        ]
        ITALIC_COLORS = [
            {"name": self.tr_col("Gray", "gray"), "color": "#909090"}, {"name": self.tr_col("Warm Gray", "warm_gray"), "color": "#A09080"}, 
            {"name": self.tr_col("Cool Gray", "cool_gray"), "color": "#8898A8"}, {"name": self.tr_col("Nord Green","nord_green"),"color": "#8DAA78"}, 
            {"name": self.tr_col("Dracula", "dracula_orange"), "color": "#D4A060"}, {"name": self.tr_col("Rose", "rose"), "color": "#C0A0A8"}, 
            {"name": self.tr_col("Dim", "dim"), "color": "#686868"}
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

        def create_section_lbl(text):
            lbl = QtWidgets.QLabel(text)
            lbl.setFont(self.get_font())
            lbl.setStyleSheet(SECTION_LBL_STYLE)
            return lbl

        def create_h_sep():
            f = QtWidgets.QFrame()
            f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
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
            wrapper = QtWidgets.QHBoxLayout()
            wrapper.setContentsMargins(0, 0, 0, 0)
            
            grid = QtWidgets.QGridLayout()
            grid.setSpacing(8)
            grid.setContentsMargins(0, 0, 0, 0)
            btns = []
            
            row, col = 0, 0
            max_cols = 5
            
            for item in items:
                btn = QtWidgets.QPushButton()
                btn.setFixedSize(38, 28)
                btn.setToolTip(item["name"])
                btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
                btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
                
                if is_pair:
                    is_selected = (target_dict.get("user_bubble_color", "").lower() == item["user"].lower() and 
                                   target_dict.get("char_bubble_color", "").lower() == item["char"].lower())
                    btn.setStyleSheet(swatch_style_pair(item["user"], item["char"], is_selected))
                else:
                    is_selected = (target_dict.get(key, "").lower() == item["color"].lower())
                    btn.setStyleSheet(swatch_style_single(item["color"], is_selected))
                
                name_lbl = QtWidgets.QLabel(item["name"])
                name_lbl.setFont(self.get_font())
                name_lbl.setStyleSheet("color: #666; font-size: 9px; background: transparent; border: none;")
                name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
                
                v_box = QtWidgets.QVBoxLayout()
                v_box.setSpacing(2)
                v_box.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
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

            custom_btn = QtWidgets.QPushButton("＋")
            custom_btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            custom_btn.setFixedSize(38, 28)
            custom_btn.setToolTip(self.tr("appearance_tooltip_custom", "Custom Color"))
            custom_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
            custom_btn.setFont(self.get_font())
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
            custom_name = QtWidgets.QLabel(self.tr("appearance_lbl_custom", "Custom"))
            custom_name.setFont(self.get_font())
            custom_name.setStyleSheet("color: #666; font-size: 9px; background: transparent; border: none;")
            custom_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
            
            c_v_box = QtWidgets.QVBoxLayout()
            c_v_box.setSpacing(2)
            c_v_box.addWidget(custom_btn, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
            c_v_box.addWidget(custom_name)
            
            grid.addLayout(c_v_box, row, col)

            def custom_pick(_):
                if is_pair:
                    c = QtWidgets.QColorDialog.getColor(QtGui.QColor(target_dict["user_bubble_color"]), None, self.tr("appearance_dlg_user_bubble", "User Bubble Color"))
                    if c.isValid(): target_dict["user_bubble_color"] = c.name()
                    c2 = QtWidgets.QColorDialog.getColor(QtGui.QColor(target_dict["char_bubble_color"]), None, self.tr("appearance_dlg_char_bubble", "Character Bubble Color"))
                    if c2.isValid(): target_dict["char_bubble_color"] = c2.name()
                else:
                    c = QtWidgets.QColorDialog.getColor(QtGui.QColor(target_dict.get(key, "#ffffff")), None, self.tr("appearance_dlg_pick_color", "Pick Color"))
                    if c.isValid(): target_dict[key] = c.name()
                apply_fn()

            custom_btn.clicked.connect(custom_pick)
            
            wrapper.addLayout(grid)
            wrapper.addStretch()

            return wrapper

        def create_slider_row(label_text, key, lo, hi, suffix, target_dict, apply_fn):
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(5)
            
            top = QtWidgets.QHBoxLayout()
            lbl = QtWidgets.QLabel(label_text)
            lbl.setFont(self.get_font())
            lbl.setStyleSheet(PARAM_LBL_STYLE)
            
            val_lbl = QtWidgets.QLabel(f"{target_dict.get(key, lo)}{suffix}")
            val_lbl.setFont(self.get_font())
            val_lbl.setStyleSheet("color: #888; font-size: 12px; background: transparent; border: none;")
            
            top.addWidget(lbl)
            top.addStretch()
            top.addWidget(val_lbl)
            
            sl = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(target_dict.get(key, lo))
            sl.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
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

        left_scroll = QtWidgets.QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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

        left_content = QtWidgets.QWidget()
        left_content.setStyleSheet("background: transparent;")
        LL = QtWidgets.QVBoxLayout(left_content)
        LL.setContentsMargins(15, 15, 10, 15)

        chat_settings_card = QtWidgets.QFrame()
        chat_settings_card.setStyleSheet(CARD_STYLE)
        CS = QtWidgets.QVBoxLayout(chat_settings_card)
        CS.setContentsMargins(20, 20, 20, 20)
        CS.setSpacing(20)

        def update_chat_prev():
            self.chatAppearanceChanged.emit(self.s)
            self.update_preview()

        CS.addWidget(create_section_lbl(self.tr("appearance_header_theme", "Theme")))
        CS.addLayout(create_swatch_grid(FULL_PRESETS, None, s, update_chat_prev, is_pair=True))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(self.tr("appearance_header_text_color", "Text Color")))
        CS.addLayout(create_swatch_grid(TEXT_COLORS, "text_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(self.tr("appearance_header_quotes", "Quotes")))
        CS.addLayout(create_swatch_grid(QUOTE_COLORS, "quote_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addWidget(create_section_lbl(self.tr("appearance_header_italic", "Cursive")))
        CS.addLayout(create_swatch_grid(ITALIC_COLORS, "italic_color", s, update_chat_prev))
        CS.addWidget(create_h_sep())

        CS.addLayout(create_slider_row(self.tr("appearance_lbl_corner_radius", "Corner Radius"), "border_radius", 0, 24, "px", s, update_chat_prev))
        CS.addLayout(create_slider_row(self.tr("appearance_lbl_bubble_opacity", "Bubble Opacity"), "bubble_opacity", 10, 100, "%", s, update_chat_prev))
        CS.addLayout(create_slider_row(self.tr("appearance_lbl_max_width", "Max Width"), "max_width", 300, 840, "px", s, update_chat_prev))
        
        fs_row = QtWidgets.QHBoxLayout()
        fs_lbl = QtWidgets.QLabel(self.tr("appearance_lbl_font_size", "Font Size"))
        fs_lbl.setFont(self.get_font())
        fs_lbl.setStyleSheet(PARAM_LBL_STYLE)
        spin = QtWidgets.QSpinBox()
        spin.setRange(8, 48)
        spin.setValue(s.get("font_size", 14))
        spin.setFixedWidth(65)
        spin.setFixedHeight(28)
        spin.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        spin.setFont(self.get_font())
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

        chat_btn_row = QtWidgets.QHBoxLayout()
        btn_reset_chat = QtWidgets.QPushButton(self.tr("appearance_btn_reset", "Reset"))
        btn_reset_chat.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_reset_chat.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        btn_reset_chat.setFont(self.get_font())
        btn_reset_chat.setStyleSheet("""
            QPushButton { background: transparent; color: #888; border: 1px solid #333;
                          border-radius: 8px; padding: 8px 16px; font-size: 12px; font-weight: bold;}
            QPushButton:hover { background: #222; color: #AAA; }
        """)
        btn_save_chat = QtWidgets.QPushButton(self.tr("appearance_btn_save", "Save"))
        btn_save_chat.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        btn_save_chat.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        btn_save_chat.setFont(self.get_font())
        btn_save_chat.setStyleSheet("""
            QPushButton { background: #333; color: #E0E0E0; border: 1px solid #444;
                          border-radius: 8px; padding: 8px 16px; font-size: 12px; font-weight: bold;}
            QPushButton:hover { background: #444; color: #FFF; }
            QPushButton:pressed { background: #222; }
        """)

        def on_reset_chat():
            self.resetAppearanceRequested.emit()

        def on_save_chat():
            self.saveChatAppearanceRequested.emit(s)
            
        btn_reset_chat.clicked.connect(on_reset_chat)
        btn_save_chat.clicked.connect(on_save_chat)
        
        chat_btn_row.addWidget(btn_reset_chat)
        chat_btn_row.addStretch()
        chat_btn_row.addWidget(btn_save_chat)
        CS.addLayout(chat_btn_row)

        LL.addWidget(chat_settings_card)
        LL.addStretch()
        left_scroll.setWidget(left_content)
        self.main_layout.addWidget(left_scroll)

        right_scroll = QtWidgets.QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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

        right_content = QtWidgets.QWidget()
        right_content.setStyleSheet("background: transparent;")
        RL = QtWidgets.QVBoxLayout(right_content)
        RL.setContentsMargins(20, 15, 20, 15)
        RL.setSpacing(20)

        preview_lbl = create_section_lbl(self.tr("appearance_header_preview", "Preview"))
        preview_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(preview_lbl)

        preview_card = QtWidgets.QFrame()
        preview_card.setStyleSheet(CARD_STYLE)
        preview_card.setMinimumHeight(200) 
        PV = QtWidgets.QVBoxLayout(preview_card)
        PV.setContentsMargins(20, 20, 20, 20)
        PV.setSpacing(15)

        self.char_preview = QtWidgets.QLabel()
        self.char_preview.setWordWrap(True)
        self.char_preview.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.char_preview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        self.user_preview = QtWidgets.QLabel()
        self.user_preview.setWordWrap(True)
        self.user_preview.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self.user_preview.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)

        char_row = QtWidgets.QHBoxLayout()
        char_row.addWidget(self.char_preview)
        char_row.addStretch()

        user_row = QtWidgets.QHBoxLayout()
        user_row.addStretch()
        user_row.addWidget(self.user_preview)

        PV.addLayout(char_row)
        PV.addLayout(user_row)
        PV.addStretch()
        RL.addWidget(preview_card)

        theme_lbl = create_section_lbl(self.tr("appearance_header_window_theme", "Window Theme"))
        theme_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(theme_lbl)

        theme_card = QtWidgets.QFrame()
        theme_card.setStyleSheet(CARD_STYLE)
        TH = QtWidgets.QVBoxLayout(theme_card)
        TH.setContentsMargins(20, 20, 20, 20)

        WINDOW_THEMES = [
            # --- NEUTRAL & DARK ---
            {
                "name": self.tr("appearance_wtheme_default", "Default"),
                "bg_primary": "27,27,27", "bg_secondary": "22,22,22", "border_color": "50,50,55",
                "sidebar_accent": "#A0A0A0", "sidebar_hover": "#1B1B1B", "sidebar_text": "#D2D2D2"
            },
            {
                "name": self.tr("appearance_wtheme_obsidian", "Obsidian"),
                "bg_primary": "18,18,18", "bg_secondary": "10,10,10", "border_color": "35,35,35",
                "sidebar_accent": "#FFFFFF", "sidebar_hover": "#252525", "sidebar_text": "#E0E0E0"
            },
            {
                "name": self.tr("appearance_wtheme_graphite", "Graphite"),
                "bg_primary": "30,30,30", "bg_secondary": "37,37,38", "border_color": "55,55,55",
                "sidebar_accent": "#569CD6", "sidebar_hover": "#2D2D2D", "sidebar_text": "#CCCCCC"
            },

            # --- COOL & BLUE ---
            {
                "name": self.tr("appearance_wtheme_nord", "Nordic"),
                "bg_primary": "46,52,64", "bg_secondary": "36,41,51", "border_color": "59,66,82",
                "sidebar_accent": "#88C0D0", "sidebar_hover": "#434C5E", "sidebar_text": "#D8DEE9"
            },
            {
                "name": self.tr("appearance_wtheme_tokyo_night", "Tokyo Night"),
                "bg_primary": "26,27,38", "bg_secondary": "36,40,59", "border_color": "65,68,95",
                "sidebar_accent": "#7AA2F7", "sidebar_hover": "#2F3549", "sidebar_text": "#C0CAF5"
            },
            {
                "name": self.tr("appearance_wtheme_oceanic", "Oceanic"),
                "bg_primary": "15,23,42", "bg_secondary": "10,15,30", "border_color": "30,41,59",
                "sidebar_accent": "#38BDF8", "sidebar_hover": "#1E293B", "sidebar_text": "#E2E8F0"
            },
            {
                "name": self.tr("appearance_wtheme_midnight", "Midnight"),
                "bg_primary": "16,20,30", "bg_secondary": "12,16,24", "border_color": "30,38,55",
                "sidebar_accent": "#818CF8", "sidebar_hover": "#1F2937", "sidebar_text": "#C7D2FE"
            },

            # --- PURPLE & PINK ---
            {
                "name": self.tr("appearance_wtheme_synthwave", "Synthwave"),
                "bg_primary": "36,27,47", "bg_secondary": "25,18,35", "border_color": "60,40,70",
                "sidebar_accent": "#F472B6", "sidebar_hover": "#453055", "sidebar_text": "#E9D5FF"
            },
            {
                "name": self.tr("appearance_wtheme_cyberpunk", "Cyberpunk"),
                "bg_primary": "10,10,18", "bg_secondary": "20,5,30", "border_color": "50,10,80",
                "sidebar_accent": "#00FF9F", "sidebar_hover": "#301040", "sidebar_text": "#FF0055"
            },
            {
                "name": self.tr("appearance_wtheme_royal", "Royal"),
                "bg_primary": "28,20,40", "bg_secondary": "20,15,30", "border_color": "45,35,60",
                "sidebar_accent": "#A78BFA", "sidebar_hover": "#352545", "sidebar_text": "#E5E7EB"
            },
            {
                "name": self.tr("appearance_wtheme_rose", "Rose"),
                "bg_primary": "35,25,30", "bg_secondary": "25,18,22", "border_color": "55,35,45",
                "sidebar_accent": "#FB7185", "sidebar_hover": "#40202A", "sidebar_text": "#FFE4E6"
            },

            # --- NATURE & WARM ---
            {
                "name": self.tr("appearance_wtheme_forest", "Forest"),
                "bg_primary": "18,28,22", "bg_secondary": "12,20,15", "border_color": "30,50,38",
                "sidebar_accent": "#4ADE80", "sidebar_hover": "#142518", "sidebar_text": "#DCFCE7"
            },
            {
                "name": self.tr("appearance_wtheme_coffee", "Coffee"),
                "bg_primary": "28,24,22", "bg_secondary": "22,18,16", "border_color": "50,42,38",
                "sidebar_accent": "#D7CCC8", "sidebar_hover": "#352A25", "sidebar_text": "#EFEBE9"
            },
            {
                "name": self.tr("appearance_wtheme_amber", "Amber"),
                "bg_primary": "30,25,20", "bg_secondary": "22,18,14", "border_color": "55,40,30",
                "sidebar_accent": "#FBBF24", "sidebar_hover": "#33251A", "sidebar_text": "#FEF3C7"
            },
            
            # --- SPECIAL ---
            {
                "name": self.tr("appearance_wtheme_slate", "Slate"),
                "bg_primary": "22,28,36", "bg_secondary": "15,20,28", "border_color": "44,56,72",
                "sidebar_accent": "#60A5FA", "sidebar_hover": "#1E293B", "sidebar_text": "#F1F5F9"
            },
            {
                "name": self.tr("appearance_wtheme_dracula", "Vampire"),
                "bg_primary": "40,42,54", "bg_secondary": "28,30,40", "border_color": "68,71,90",
                "sidebar_accent": "#BD93F9", "sidebar_hover": "#343746", "sidebar_text": "#F8F8F2"
            }
        ]

        def ui_update_all():
            self.windowThemeChanged.emit(wt)

        theme_wrapper = QtWidgets.QHBoxLayout()
        theme_wrapper.setContentsMargins(0, 0, 0, 0)
        
        theme_grid = QtWidgets.QGridLayout()
        theme_grid.setSpacing(10)
        theme_grid.setContentsMargins(0, 0, 0, 0)
        theme_btns = []
        row, col = 0, 0
        
        MAX_COLS = 7 
        
        for theme in WINDOW_THEMES:
            btn = QtWidgets.QPushButton()
            btn.setFixedSize(46, 32)
            btn.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            btn.setToolTip(theme["name"])
            btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))

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
            
            name_lbl = QtWidgets.QLabel(theme["name"])
            name_lbl.setFont(self.get_font())
            name_lbl.setStyleSheet("color:#666; font-size:9px; background:transparent; border:none;")
            name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
            
            v_box = QtWidgets.QVBoxLayout()
            v_box.setSpacing(4)
            v_box.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)
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
                
            return click

        for btn, theme in theme_btns:
            btn.clicked.connect(make_theme_click(btn, theme, theme_btns))

        theme_wrapper.addLayout(theme_grid)
        theme_wrapper.addStretch()
        TH.addLayout(theme_wrapper)
        RL.addWidget(theme_card)

        ui_lbl = create_section_lbl(self.tr("appearance_header_ui", "Interface (Sidebar and Buttons)"))
        ui_lbl.setStyleSheet(SECTION_LBL_STYLE + " padding-left: 5px;")
        RL.addWidget(ui_lbl)

        ui_card = QtWidgets.QFrame()
        ui_card.setStyleSheet(CARD_STYLE)
        UI = QtWidgets.QVBoxLayout(ui_card)
        UI.setContentsMargins(20, 20, 20, 20)
        UI.setSpacing(20)
        
        def ui_update_only_buttons():
            self.uiAppearanceChanged.emit(u)

        UI_ACCENT_COLORS = [
            {"name": self.tr_col("Gray", "gray"), "color": "#A0A0A0"}, {"name": self.tr_col("Blue", "blue"), "color": "#5090C8"}, 
            {"name": self.tr_col("Lavender", "lavender"), "color": "#9080C8"}, {"name": self.tr_col("Green", "green"), "color": "#70B870"}, 
            {"name": self.tr_col("Amber", "amber"), "color": "#E8A040"}, {"name": self.tr_col("Rose", "rose"), "color": "#C87090"}
        ]
        UI_HOVER_COLORS = [
            {"name": self.tr_col("Dark", "dark"), "color": "#1B1B1B"}, {"name": self.tr_col("Darker", "darker"), "color": "#141414"}, 
            {"name": self.tr_col("Slate", "slate"), "color": "#1A202A"}, {"name": self.tr_col("Forest", "forest"), "color": "#162018"}, 
            {"name": self.tr_col("Warm", "warm"), "color": "#201A14"}
        ]
        NAV_TEXT_COLORS = [
            {"name": self.tr_col("Standard", "standard"), "color": "#D2D2D2"}, {"name": self.tr_col("Bright", "bright"), "color": "#F0F0F0"}, 
            {"name": self.tr_col("Dimmed", "dimmed"), "color": "#A0A0A0"}, {"name": self.tr_col("Warm", "warm"), "color": "#D8C8B0"}, 
            {"name": self.tr_col("Cool", "cool"), "color": "#A8B8C8"}, {"name": self.tr_col("Accent", "accent"), "color": "#B0C0D8"}
        ]

        UI.addWidget(create_section_lbl(self.tr("appearance_header_ui_accent", "Accent (The Active Menu Item)")))
        UI.addLayout(create_swatch_grid(UI_ACCENT_COLORS, "sidebar_accent", u, ui_update_only_buttons))
        UI.addWidget(create_h_sep())

        UI.addWidget(create_section_lbl(self.tr("appearance_header_ui_hover", "Hover (Active Button Background)")))
        UI.addLayout(create_swatch_grid(UI_HOVER_COLORS, "sidebar_hover", u, ui_update_only_buttons))
        UI.addWidget(create_h_sep())

        UI.addWidget(create_section_lbl(self.tr("appearance_header_ui_text", "Button Text Color")))
        UI.addLayout(create_swatch_grid(NAV_TEXT_COLORS, "sidebar_text", u, ui_update_only_buttons))

        RL.addWidget(ui_card)
        RL.addStretch()
        
        right_scroll.setWidget(right_content)
        self.main_layout.addWidget(right_scroll)

        self.update_preview()

class GlassPortalButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._hover_progress = 0.0
        self._is_pressed = False
        
        self._animation = QPropertyAnimation(self, b"hover_progress", self)
        self._animation.setDuration(350)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMinimumHeight(50)

    @pyqtProperty(float)
    def hover_progress(self) -> float:
        return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, val: float):
        self._hover_progress = val
        self.update()

    def enterEvent(self, event):
        self._animation.setDirection(QPropertyAnimation.Direction.Forward)
        if self._animation.state() == QPropertyAnimation.State.Stopped:
            self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setDirection(QPropertyAnimation.Direction.Backward)
        if self._animation.state() == QPropertyAnimation.State.Stopped:
            self._animation.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        rect.adjust(0.7, 0.7, -0.7, -0.7)
        
        rx = ry = self.height() / 2.0
        p = self._hover_progress

        painter.setPen(Qt.PenStyle.NoPen)
        base_glass_color = QColor(10, 10, 10, 200) 
        painter.setBrush(QBrush(base_glass_color))
        painter.drawRoundedRect(rect, rx, ry)

        if p > 0.0:
            glow_gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
            
            alpha = int(80 * p) 
            glow_gradient.setColorAt(0.0, QColor(168, 85, 247, alpha))
            glow_gradient.setColorAt(1.0, QColor(0, 245, 255, alpha))
            
            painter.setBrush(QBrush(glow_gradient))
            painter.drawRoundedRect(rect, rx, ry)

        if self._is_pressed:
            painter.setBrush(QBrush(QColor(0, 0, 0, 140)))
            painter.drawRoundedRect(rect, rx, ry)

        border_gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        
        c1 = QColor(
            int(255 * (1 - p) + 168 * p),
            int(255 * (1 - p) + 85 * p),
            int(255 * (1 - p) + 247 * p),
            int(20 + 215 * p)
        )
        c2 = QColor(
            int(255 * (1 - p) + 0 * p),
            int(255 * (1 - p) + 245 * p),
            int(255 * (1 - p) + 255 * p),
            int(20 + 215 * p)
        )
        border_gradient.setColorAt(0.0, c1)
        border_gradient.setColorAt(1.0, c2)

        pen = QPen(border_gradient, 1.5) 
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, rx, ry)

        text_color = QColor(
            int(148 * (1 - p) + 255 * p),
            int(163 * (1 - p) + 255 * p),
            int(184 * (1 - p) + 255 * p),
            255
        )
        painter.setPen(text_color)
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
