from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QListWidget
from PyQt6.QtCore import Qt, QPointF, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QPainter, QRadialGradient, QCursor, QFont, QPixmap

class Ui_MainWindow(object):
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
        self.frame_main_button.setStyleSheet("background-color: rgb(27, 27, 27);\n"
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
        self.pushButton_create_character_2.setStyleSheet("QPushButton {\n"
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
        self.main_no_characters_description_label.setStyleSheet("background-color: rgb(27, 27, 27);\n"
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
        self.main_no_characters_advice_label.setStyleSheet("background-color: rgb(27, 27, 27);\n"
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
				background-color: rgb(27,27,27);
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
        self.lineEdit_search_character_menu = QtWidgets.QLineEdit(parent=self.frame_welcome_to)
        self.lineEdit_search_character_menu.setMinimumSize(QtCore.QSize(250, 33))
        self.lineEdit_search_character_menu.setMaximumSize(QtCore.QSize(250, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_search_character_menu.setFont(font)
        self.lineEdit_search_character_menu.setStyleSheet("QLineEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"\n"
"QLineEdit::placeholder {\n"
"    color: #888888;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid #444;\n"
"}")
        self.lineEdit_search_character_menu.setObjectName("lineEdit_search_character_menu")
        self.gridLayout_6.addWidget(self.lineEdit_search_character_menu, 0, 4, 1, 1)
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
        self.pushButton_add_character.setStyleSheet("QPushButton {\n"
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
        self.create_character_page_2.setStyleSheet("")
        self.create_character_page_2.setObjectName("create_character_page_2")
        self.gridLayout_17 = QtWidgets.QGridLayout(self.create_character_page_2)
        self.gridLayout_17.setContentsMargins(0, 0, 5, 0)
        self.gridLayout_17.setSpacing(0)
        self.gridLayout_17.setObjectName("gridLayout_17")
        self.scrollArea_character_building = QtWidgets.QScrollArea(parent=self.create_character_page_2)
        self.scrollArea_character_building.setStyleSheet("QScrollArea {\n"
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
        self.scrollArea_character_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scrollArea_character_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_character_building.setWidgetResizable(True)
        self.scrollArea_character_building.setObjectName("scrollArea_character_building")
        self.scrollAreaWidgetContents_character_building = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_building.setGeometry(QtCore.QRect(0, 0, 1102, 2618))
        self.scrollAreaWidgetContents_character_building.setStyleSheet("background-color: rgb(27,27,27);\n"
"")
        self.scrollAreaWidgetContents_character_building.setObjectName("scrollAreaWidgetContents_character_building")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_character_building)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.frame_character_building = QtWidgets.QFrame(parent=self.scrollAreaWidgetContents_character_building)
        self.frame_character_building.setMinimumSize(QtCore.QSize(0, 3000))
        self.frame_character_building.setStyleSheet("background-color: rgb(27,27,27);")
        self.frame_character_building.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building.setObjectName("frame_character_building")
        self.verticalLayout_7 = QtWidgets.QVBoxLayout(self.frame_character_building)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.frame_character_building_title = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_title.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_title.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_title.setStyleSheet("border: none;")
        self.frame_character_building_title.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_title.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_title.setObjectName("frame_character_building_title")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.frame_character_building_title)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.character_building_label = QtWidgets.QLabel(parent=self.frame_character_building_title)
        self.character_building_label.setMinimumSize(QtCore.QSize(211, 31))
        self.character_building_label.setMaximumSize(QtCore.QSize(211, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_building_label.setFont(font)
        self.character_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_building_label.setObjectName("character_building_label")
        self.gridLayout_4.addWidget(self.character_building_label, 0, 0, 1, 1)
        spacerItem15 = QtWidgets.QSpacerItem(572, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_4.addItem(spacerItem15, 0, 1, 1, 1)
        self.pushButton_import_character_card = QtWidgets.QPushButton(parent=self.frame_character_building_title)
        self.pushButton_import_character_card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_import_character_card.setMinimumSize(QtCore.QSize(161, 35))
        self.pushButton_import_character_card.setMaximumSize(QtCore.QSize(161, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_import_character_card.setFont(font)
        self.pushButton_import_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_import_character_card.setStyleSheet("QPushButton {\n"
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
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap(":/sowInterface/import.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_card.setIcon(icon6)
        self.pushButton_import_character_card.setObjectName("pushButton_import_character_card")
        self.gridLayout_4.addWidget(self.pushButton_import_character_card, 0, 2, 1, 1)
        self.pushButton_export_character_card = QtWidgets.QPushButton(parent=self.frame_character_building_title)
        self.pushButton_export_character_card.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_export_character_card.setMinimumSize(QtCore.QSize(35, 35))
        self.pushButton_export_character_card.setMaximumSize(QtCore.QSize(35, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_export_character_card.setFont(font)
        self.pushButton_export_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_export_character_card.setStyleSheet("QPushButton {\n"
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
        self.pushButton_export_character_card.setText("")
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap("../../../../Soul-of-Waifu-v2.2.0/app/gui/icons/export.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_export_character_card.setIcon(icon7)
        self.pushButton_export_character_card.setObjectName("pushButton_export_character_card")
        self.gridLayout_4.addWidget(self.pushButton_export_character_card, 0, 3, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_character_building_title)
        self.frame_character_building_imahe = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_imahe.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_imahe.setMaximumSize(QtCore.QSize(16777215, 100))
        self.frame_character_building_imahe.setStyleSheet("border: none;")
        self.frame_character_building_imahe.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_imahe.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_imahe.setObjectName("frame_character_building_imahe")
        self.gridLayout_11 = QtWidgets.QGridLayout(self.frame_character_building_imahe)
        self.gridLayout_11.setObjectName("gridLayout_11")
        self.character_image_building_label = QtWidgets.QLabel(parent=self.frame_character_building_imahe)
        self.character_image_building_label.setMinimumSize(QtCore.QSize(151, 51))
        self.character_image_building_label.setMaximumSize(QtCore.QSize(151, 51))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_image_building_label.setFont(font)
        self.character_image_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_image_building_label.setObjectName("character_image_building_label")
        self.gridLayout_11.addWidget(self.character_image_building_label, 0, 0, 1, 1)
        self.pushButton_import_character_image = QtWidgets.QPushButton(parent=self.frame_character_building_imahe)
        self.pushButton_import_character_image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_import_character_image.setMinimumSize(QtCore.QSize(81, 81))
        self.pushButton_import_character_image.setMaximumSize(QtCore.QSize(81, 81))
        font = QtGui.QFont()
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_import_character_image.setFont(font)
        self.pushButton_import_character_image.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_import_character_image.setStyleSheet("QPushButton {\n"
"    background-color: #1E1E1E;\n"
"    color: rgb(227, 227, 227);\n"
"    border: 2px solid #3A3A3A;\n"
"    border-radius: 10px;\n"
"}\n"
"QPushButton:hover {\n"
"    background-color: #2C2C2C;\n"
"    border: 2px solid #505050;\n"
"}\n"
"QPushButton:pressed {\n"
"    background-color: #424242;\n"
"    border: 2px solid #707070;\n"
"}")
        self.pushButton_import_character_image.setText("")
        icon_image_import = QtGui.QIcon()
        icon_image_import.addPixmap(QtGui.QPixmap("app/gui/icons/import_image.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_image.setIcon(icon_image_import)
        self.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
        self.pushButton_import_character_image.setObjectName("pushButton_import_character_image")
        self.gridLayout_11.addWidget(self.pushButton_import_character_image, 0, 1, 1, 1)
        spacerItem16 = QtWidgets.QSpacerItem(712, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_11.addItem(spacerItem16, 0, 2, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_character_building_imahe)
        self.frame_character_building_name_description = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_name_description.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_name_description.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_name_description.setStyleSheet("border: none;")
        self.frame_character_building_name_description.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_name_description.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_name_description.setObjectName("frame_character_building_name_description")
        self.gridLayout_12 = QtWidgets.QGridLayout(self.frame_character_building_name_description)
        self.gridLayout_12.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout_12.setObjectName("gridLayout_12")
        self.character_name_building_label = QtWidgets.QLabel(parent=self.frame_character_building_name_description)
        self.character_name_building_label.setMinimumSize(QtCore.QSize(151, 51))
        self.character_name_building_label.setMaximumSize(QtCore.QSize(151, 51))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_name_building_label.setFont(font)
        self.character_name_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_name_building_label.setObjectName("character_name_building_label")
        self.gridLayout_12.addWidget(self.character_name_building_label, 0, 0, 1, 1)
        self.lineEdit_character_name_building = QtWidgets.QLineEdit(parent=self.frame_character_building_name_description)
        self.lineEdit_character_name_building.setMinimumSize(QtCore.QSize(291, 31))
        self.lineEdit_character_name_building.setMaximumSize(QtCore.QSize(291, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_character_name_building.setFont(font)
        self.lineEdit_character_name_building.setStyleSheet("QLineEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"\n"
"QLineEdit::placeholder {\n"
"    color: #888888;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid #444;\n"
"}")
        self.lineEdit_character_name_building.setInputMask("")
        self.lineEdit_character_name_building.setText("")
        self.lineEdit_character_name_building.setObjectName("lineEdit_character_name_building")
        self.gridLayout_12.addWidget(self.lineEdit_character_name_building, 0, 1, 1, 1)
        spacerItem17 = QtWidgets.QSpacerItem(502, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_12.addItem(spacerItem17, 0, 2, 1, 1)
        spacerItem18 = QtWidgets.QSpacerItem(956, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_12.addItem(spacerItem18, 1, 0, 1, 3)
        self.character_description_building_label = QtWidgets.QLabel(parent=self.frame_character_building_name_description)
        self.character_description_building_label.setMinimumSize(QtCore.QSize(181, 40))
        self.character_description_building_label.setMaximumSize(QtCore.QSize(181, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_description_building_label.setFont(font)
        self.character_description_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_description_building_label.setObjectName("character_description_building_label")
        self.gridLayout_12.addWidget(self.character_description_building_label, 2, 0, 1, 2)
        self.textEdit_character_description_building = QtWidgets.QTextEdit(parent=self.frame_character_building_name_description)
        self.textEdit_character_description_building.setMinimumSize(QtCore.QSize(700, 300))
        self.textEdit_character_description_building.setMaximumSize(QtCore.QSize(16777215, 300))
        self.textEdit_character_description_building.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_character_description_building.setFont(font)
        self.textEdit_character_description_building.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
"\n"
"QLineEdit {\n"
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
"}\n"
"\n"
"")
        self.textEdit_character_description_building.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.textEdit_character_description_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_description_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_description_building.setObjectName("textEdit_character_description_building")
        self.gridLayout_12.addWidget(self.textEdit_character_description_building, 3, 0, 1, 3)
        self.verticalLayout_7.addWidget(self.frame_character_building_name_description)
        self.frame_character_building_personality = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_personality.setMinimumSize(QtCore.QSize(0, 300))
        self.frame_character_building_personality.setMaximumSize(QtCore.QSize(16777215, 300))
        self.frame_character_building_personality.setStyleSheet("border: none;")
        self.frame_character_building_personality.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_personality.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_personality.setObjectName("frame_character_building_personality")
        self.gridLayout_13 = QtWidgets.QGridLayout(self.frame_character_building_personality)
        self.gridLayout_13.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout_13.setObjectName("gridLayout_13")
        self.character_personality_building_label = QtWidgets.QLabel(parent=self.frame_character_building_personality)
        self.character_personality_building_label.setMinimumSize(QtCore.QSize(181, 40))
        self.character_personality_building_label.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_personality_building_label.setFont(font)
        self.character_personality_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_personality_building_label.setObjectName("character_personality_building_label")
        self.gridLayout_13.addWidget(self.character_personality_building_label, 0, 0, 1, 1)
        spacerItem19 = QtWidgets.QSpacerItem(767, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_13.addItem(spacerItem19, 0, 1, 1, 1)
        self.textEdit_character_personality_building = QtWidgets.QTextEdit(parent=self.frame_character_building_personality)
        self.textEdit_character_personality_building.setMinimumSize(QtCore.QSize(951, 250))
        self.textEdit_character_personality_building.setMaximumSize(QtCore.QSize(16777215, 250))
        self.textEdit_character_personality_building.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_character_personality_building.setFont(font)
        self.textEdit_character_personality_building.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_character_personality_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_personality_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_personality_building.setObjectName("textEdit_character_personality_building")
        self.gridLayout_13.addWidget(self.textEdit_character_personality_building, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_personality)
        self.frame_character_building_scenario = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_scenario.setMinimumSize(QtCore.QSize(0, 150))
        self.frame_character_building_scenario.setMaximumSize(QtCore.QSize(16777215, 150))
        self.frame_character_building_scenario.setStyleSheet("border: none;")
        self.frame_character_building_scenario.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_scenario.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_scenario.setObjectName("frame_character_building_scenario")
        self.gridLayout_26 = QtWidgets.QGridLayout(self.frame_character_building_scenario)
        self.gridLayout_26.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout_26.setObjectName("gridLayout_26")
        self.character_scenario_building_label = QtWidgets.QLabel(parent=self.frame_character_building_scenario)
        self.character_scenario_building_label.setMinimumSize(QtCore.QSize(181, 40))
        self.character_scenario_building_label.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_scenario_building_label.setFont(font)
        self.character_scenario_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_scenario_building_label.setObjectName("character_scenario_building_label")
        self.gridLayout_26.addWidget(self.character_scenario_building_label, 0, 0, 1, 1)
        spacerItem20 = QtWidgets.QSpacerItem(767, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_26.addItem(spacerItem20, 0, 1, 1, 1)
        self.textEdit_scenario = QtWidgets.QTextEdit(parent=self.frame_character_building_scenario)
        self.textEdit_scenario.setMinimumSize(QtCore.QSize(951, 100))
        self.textEdit_scenario.setMaximumSize(QtCore.QSize(16777215, 100))
        self.textEdit_scenario.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_scenario.setFont(font)
        self.textEdit_scenario.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_scenario.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_scenario.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_scenario.setObjectName("textEdit_scenario")
        self.gridLayout_26.addWidget(self.textEdit_scenario, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_scenario)
        self.frame_character_building_first_message = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_first_message.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_first_message.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_first_message.setStyleSheet("border: none;")
        self.frame_character_building_first_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_first_message.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_first_message.setObjectName("frame_character_building_first_message")
        self.gridLayout_14 = QtWidgets.QGridLayout(self.frame_character_building_first_message)
        self.gridLayout_14.setObjectName("gridLayout_14")
        self.first_message_building_label = QtWidgets.QLabel(parent=self.frame_character_building_first_message)
        self.first_message_building_label.setMinimumSize(QtCore.QSize(170, 40))
        self.first_message_building_label.setMaximumSize(QtCore.QSize(170, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.first_message_building_label.setFont(font)
        self.first_message_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.first_message_building_label.setObjectName("first_message_building_label")
        self.gridLayout_14.addWidget(self.first_message_building_label, 0, 0, 1, 1)
        spacerItem21 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_14.addItem(spacerItem21, 0, 1, 1, 1)
        self.textEdit_first_message_building = QtWidgets.QTextEdit(parent=self.frame_character_building_first_message)
        self.textEdit_first_message_building.setMinimumSize(QtCore.QSize(951, 300))
        self.textEdit_first_message_building.setMaximumSize(QtCore.QSize(16777215, 300))
        self.textEdit_first_message_building.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_first_message_building.setFont(font)
        self.textEdit_first_message_building.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_first_message_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_first_message_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_first_message_building.setObjectName("textEdit_first_message_building")
        self.gridLayout_14.addWidget(self.textEdit_first_message_building, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_first_message)
        self.frame_character_building_example_messages = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_example_messages.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_example_messages.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_example_messages.setStyleSheet("border: none;")
        self.frame_character_building_example_messages.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_example_messages.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_example_messages.setObjectName("frame_character_building_example_messages")
        self.gridLayout_16 = QtWidgets.QGridLayout(self.frame_character_building_example_messages)
        self.gridLayout_16.setObjectName("gridLayout_16")
        self.example_messages_building_label = QtWidgets.QLabel(parent=self.frame_character_building_example_messages)
        self.example_messages_building_label.setMinimumSize(QtCore.QSize(200, 40))
        self.example_messages_building_label.setMaximumSize(QtCore.QSize(200, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.example_messages_building_label.setFont(font)
        self.example_messages_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.example_messages_building_label.setObjectName("example_messages_building_label")
        self.gridLayout_16.addWidget(self.example_messages_building_label, 0, 0, 1, 1)
        spacerItem22 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_16.addItem(spacerItem22, 0, 1, 1, 1)
        self.textEdit_example_messages = QtWidgets.QTextEdit(parent=self.frame_character_building_example_messages)
        self.textEdit_example_messages.setMinimumSize(QtCore.QSize(951, 300))
        self.textEdit_example_messages.setMaximumSize(QtCore.QSize(16777215, 300))
        self.textEdit_example_messages.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_example_messages.setFont(font)
        self.textEdit_example_messages.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_example_messages.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_example_messages.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_example_messages.setObjectName("textEdit_example_messages")
        self.gridLayout_16.addWidget(self.textEdit_example_messages, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_example_messages)
        self.frame_character_building_alternate_greetings = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_alternate_greetings.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_alternate_greetings.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_alternate_greetings.setStyleSheet("border: none;")
        self.frame_character_building_alternate_greetings.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_alternate_greetings.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_alternate_greetings.setObjectName("frame_character_building_alternate_greetings")
        self.gridLayout_27 = QtWidgets.QGridLayout(self.frame_character_building_alternate_greetings)
        self.gridLayout_27.setObjectName("gridLayout_27")
        self.alternate_greetings_building_label = QtWidgets.QLabel(parent=self.frame_character_building_alternate_greetings)
        self.alternate_greetings_building_label.setMinimumSize(QtCore.QSize(220, 40))
        self.alternate_greetings_building_label.setMaximumSize(QtCore.QSize(220, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.alternate_greetings_building_label.setFont(font)
        self.alternate_greetings_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.alternate_greetings_building_label.setObjectName("alternate_greetings_building_label")
        self.gridLayout_27.addWidget(self.alternate_greetings_building_label, 0, 0, 1, 1)
        spacerItem23 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_27.addItem(spacerItem23, 0, 1, 1, 1)
        self.textEdit_alternate_greetings = QtWidgets.QTextEdit(parent=self.frame_character_building_alternate_greetings)
        self.textEdit_alternate_greetings.setMinimumSize(QtCore.QSize(951, 300))
        self.textEdit_alternate_greetings.setMaximumSize(QtCore.QSize(16777215, 300))
        self.textEdit_alternate_greetings.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_alternate_greetings.setFont(font)
        self.textEdit_alternate_greetings.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_alternate_greetings.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_alternate_greetings.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_alternate_greetings.setObjectName("textEdit_alternate_greetings")
        self.gridLayout_27.addWidget(self.textEdit_alternate_greetings, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_alternate_greetings)
        self.frame_character_building_creator_notes = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_creator_notes.setMinimumSize(QtCore.QSize(0, 200))
        self.frame_character_building_creator_notes.setMaximumSize(QtCore.QSize(16777215, 200))
        self.frame_character_building_creator_notes.setStyleSheet("border: none;")
        self.frame_character_building_creator_notes.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_creator_notes.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_creator_notes.setObjectName("frame_character_building_creator_notes")
        self.gridLayout_28 = QtWidgets.QGridLayout(self.frame_character_building_creator_notes)
        self.gridLayout_28.setObjectName("gridLayout_28")
        self.creator_notes_building_label = QtWidgets.QLabel(parent=self.frame_character_building_creator_notes)
        self.creator_notes_building_label.setMinimumSize(QtCore.QSize(200, 40))
        self.creator_notes_building_label.setMaximumSize(QtCore.QSize(200, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.creator_notes_building_label.setFont(font)
        self.creator_notes_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.creator_notes_building_label.setObjectName("creator_notes_building_label")
        self.gridLayout_28.addWidget(self.creator_notes_building_label, 0, 0, 1, 1)
        spacerItem24 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_28.addItem(spacerItem24, 0, 1, 1, 1)
        self.textEdit_creator_notes = QtWidgets.QTextEdit(parent=self.frame_character_building_creator_notes)
        self.textEdit_creator_notes.setMinimumSize(QtCore.QSize(951, 150))
        self.textEdit_creator_notes.setMaximumSize(QtCore.QSize(16777215, 150))
        self.textEdit_creator_notes.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_creator_notes.setFont(font)
        self.textEdit_creator_notes.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
"\n"
)
        self.textEdit_creator_notes.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_creator_notes.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_creator_notes.setObjectName("textEdit_creator_notes")
        self.gridLayout_28.addWidget(self.textEdit_creator_notes, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_creator_notes)
        self.frame_character_building_character_version = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_character_version.setMinimumSize(QtCore.QSize(0, 112))
        self.frame_character_building_character_version.setMaximumSize(QtCore.QSize(16777215, 112))
        self.frame_character_building_character_version.setStyleSheet("border: none;")
        self.frame_character_building_character_version.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_character_version.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_character_version.setObjectName("frame_character_building_character_version")
        self.gridLayout_30 = QtWidgets.QGridLayout(self.frame_character_building_character_version)
        self.gridLayout_30.setObjectName("gridLayout_30")
        self.character_version_building_label = QtWidgets.QLabel(parent=self.frame_character_building_character_version)
        self.character_version_building_label.setMinimumSize(QtCore.QSize(220, 40))
        self.character_version_building_label.setMaximumSize(QtCore.QSize(220, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_version_building_label.setFont(font)
        self.character_version_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.character_version_building_label.setObjectName("character_version_building_label")
        self.gridLayout_30.addWidget(self.character_version_building_label, 0, 0, 1, 1)
        spacerItem25 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_30.addItem(spacerItem25, 0, 1, 1, 1)
        self.textEdit_character_version = QtWidgets.QTextEdit(parent=self.frame_character_building_character_version)
        self.textEdit_character_version.setMinimumSize(QtCore.QSize(250, 70))
        self.textEdit_character_version.setMaximumSize(QtCore.QSize(250, 70))
        self.textEdit_character_version.setAcceptRichText(False)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.textEdit_character_version.setFont(font)
        self.textEdit_character_version.setStyleSheet("QTextEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:hover {\n"
"    border: 2px solid #444;\n"
"}\n"
)
        self.textEdit_character_version.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_version.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_version.setObjectName("textEdit_character_version")
        self.gridLayout_30.addWidget(self.textEdit_character_version, 1, 0, 1, 2)
        self.verticalLayout_7.addWidget(self.frame_character_building_character_version)
        self.frame_character_building_user_persona = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_user_persona.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_user_persona.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_user_persona.setStyleSheet("border: none;")
        self.frame_character_building_user_persona.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_user_persona.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_user_persona.setObjectName("frame_character_building_user_persona")
        self.gridLayout_31 = QtWidgets.QGridLayout(self.frame_character_building_user_persona)
        self.gridLayout_31.setObjectName("gridLayout_31")
        spacerItem26 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_31.addItem(spacerItem26, 0, 1, 1, 1)
        self.user_persona_building_label = QtWidgets.QLabel(parent=self.frame_character_building_user_persona)
        self.user_persona_building_label.setMinimumSize(QtCore.QSize(220, 40))
        self.user_persona_building_label.setMaximumSize(QtCore.QSize(220, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.user_persona_building_label.setFont(font)
        self.user_persona_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.user_persona_building_label.setObjectName("user_persona_building_label")
        self.gridLayout_31.addWidget(self.user_persona_building_label, 0, 0, 1, 1)
        self.comboBox_user_persona_building = QtWidgets.QComboBox(parent=self.frame_character_building_user_persona)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_user_persona_building.setFont(font)
        self.comboBox_user_persona_building.setStyleSheet("QComboBox {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 2px solid #333;\n"
"                border-radius: 5px;\n"
"                padding: 5px;\n"
"                padding-left: 10px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #454545;\n"
"            }\n"
"\n"
"            QComboBox:hover {\n"
"                border: 2px solid #444;\n"
"            }\n"
"\n"
"            QComboBox::drop-down {\n"
"                subcontrol-origin: padding;\n"
"                subcontrol-position: top right;\n"
"                width: 18px;\n"
"                border-left: 1px solid #333;\n"
"                background-color: #2b2b2b;\n"
"                border-top-right-radius: 5px;\n"
"                border-bottom-right-radius: 5px;\n"
"            }\n"
"\n"
"            QComboBox::down-arrow {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"                image: url(:/sowInterface/arrowDown.png);\n"
"            }\n"
"\n"
"            QComboBox::down-arrow:hover {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 1px solid rgb(70, 70, 70);\n"
"                border-radius: 6px;\n"
"                padding: 5px;\n"
"                outline: 0px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #8f8f8f;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item {\n"
"                border: none;\n"
"                height: 20px;\n"
"                padding: 4px 8px;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:hover {\n"
"                background-color: #5a5a5a;\n"
"                color: white;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:selected {\n"
"                background-color: #454545;\n"
"                color: white;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QScrollBar:vertical {\n"
"                background-color: #2b2b2b;\n"
"                width: 12px;\n"
"                margin: 0px;\n"
"                border: none;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical {\n"
"                background-color: #383838;\n"
"                min-height: 30px;\n"
"                border-radius: 3px;\n"
"                margin: 2px;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:hover {\n"
"                background-color: #454545;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:pressed {\n"
"                background-color: #424242;\n"
"            }\n"
"\n"
"            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"                border: none;\n"
"                background: none;\n"
"            }\n"
"\n"
"            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"                background: none;\n"
"            }")
        self.comboBox_user_persona_building.setObjectName("comboBox_user_persona_building")
        self.comboBox_user_persona_building.addItem("None")
        self.gridLayout_31.addWidget(self.comboBox_user_persona_building, 1, 0, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_character_building_user_persona)
        self.frame_character_building_system_prompt = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_system_prompt.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_system_prompt.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_system_prompt.setStyleSheet("border: none;")
        self.frame_character_building_system_prompt.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_system_prompt.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_system_prompt.setObjectName("frame_character_building_system_prompt")
        self.gridLayout_32 = QtWidgets.QGridLayout(self.frame_character_building_system_prompt)
        self.gridLayout_32.setObjectName("gridLayout_32")
        spacerItem27 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_32.addItem(spacerItem27, 0, 1, 1, 1)
        self.system_prompt_building_label = QtWidgets.QLabel(parent=self.frame_character_building_system_prompt)
        self.system_prompt_building_label.setMinimumSize(QtCore.QSize(220, 40))
        self.system_prompt_building_label.setMaximumSize(QtCore.QSize(220, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.system_prompt_building_label.setFont(font)
        self.system_prompt_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.system_prompt_building_label.setObjectName("system_prompt_building_label")
        self.gridLayout_32.addWidget(self.system_prompt_building_label, 0, 0, 1, 1)
        self.comboBox_system_prompt_building = QtWidgets.QComboBox(parent=self.frame_character_building_system_prompt)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_system_prompt_building.setFont(font)
        self.comboBox_system_prompt_building.setStyleSheet("QComboBox {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 2px solid #333;\n"
"                border-radius: 5px;\n"
"                padding: 5px;\n"
"                padding-left: 10px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #454545;\n"
"            }\n"
"\n"
"            QComboBox:hover {\n"
"                border: 2px solid #444;\n"
"            }\n"
"\n"
"            QComboBox::drop-down {\n"
"                subcontrol-origin: padding;\n"
"                subcontrol-position: top right;\n"
"                width: 18px;\n"
"                border-left: 1px solid #333;\n"
"                background-color: #2b2b2b;\n"
"                border-top-right-radius: 5px;\n"
"                border-bottom-right-radius: 5px;\n"
"            }\n"
"\n"
"            QComboBox::down-arrow {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"                image: url(:/sowInterface/arrowDown.png);\n"
"            }\n"
"\n"
"            QComboBox::down-arrow:hover {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 1px solid rgb(70, 70, 70);\n"
"                border-radius: 6px;\n"
"                padding: 5px;\n"
"                outline: 0px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #8f8f8f;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item {\n"
"                border: none;\n"
"                height: 20px;\n"
"                padding: 4px 8px;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:hover {\n"
"                background-color: #5a5a5a;\n"
"                color: white;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:selected {\n"
"                background-color: #454545;\n"
"                color: white;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QScrollBar:vertical {\n"
"                background-color: #2b2b2b;\n"
"                width: 12px;\n"
"                margin: 0px;\n"
"                border: none;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical {\n"
"                background-color: #383838;\n"
"                min-height: 30px;\n"
"                border-radius: 3px;\n"
"                margin: 2px;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:hover {\n"
"                background-color: #454545;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:pressed {\n"
"                background-color: #424242;\n"
"            }\n"
"\n"
"            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"                border: none;\n"
"                background: none;\n"
"            }\n"
"\n"
"            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"                background: none;\n"
"            }")
        self.comboBox_system_prompt_building.setObjectName("comboBox_system_prompt_building")
        self.comboBox_system_prompt_building.addItem("By default")
        self.gridLayout_32.addWidget(self.comboBox_system_prompt_building, 1, 0, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_character_building_system_prompt)
        self.frame_character_building_lorebook = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_character_building_lorebook.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_character_building_lorebook.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_character_building_lorebook.setStyleSheet("border: none;")
        self.frame_character_building_lorebook.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building_lorebook.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building_lorebook.setObjectName("frame_character_building_lorebook")
        self.gridLayout_33 = QtWidgets.QGridLayout(self.frame_character_building_lorebook)
        self.gridLayout_33.setObjectName("gridLayout_33")
        spacerItem28 = QtWidgets.QSpacerItem(817, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_33.addItem(spacerItem28, 0, 1, 1, 1)
        self.lorebook_building_label = QtWidgets.QLabel(parent=self.frame_character_building_lorebook)
        self.lorebook_building_label.setMinimumSize(QtCore.QSize(220, 40))
        self.lorebook_building_label.setMaximumSize(QtCore.QSize(220, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lorebook_building_label.setFont(font)
        self.lorebook_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.lorebook_building_label.setObjectName("lorebook_building_label")
        self.gridLayout_33.addWidget(self.lorebook_building_label, 0, 0, 1, 1)
        self.comboBox_lorebook_building = QtWidgets.QComboBox(parent=self.frame_character_building_lorebook)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_lorebook_building.setFont(font)
        self.comboBox_lorebook_building.setStyleSheet("QComboBox {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 2px solid #333;\n"
"                border-radius: 5px;\n"
"                padding: 5px;\n"
"                padding-left: 10px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #454545;\n"
"            }\n"
"\n"
"            QComboBox:hover {\n"
"                border: 2px solid #444;\n"
"            }\n"
"\n"
"            QComboBox::drop-down {\n"
"                subcontrol-origin: padding;\n"
"                subcontrol-position: top right;\n"
"                width: 18px;\n"
"                border-left: 1px solid #333;\n"
"                background-color: #2b2b2b;\n"
"                border-top-right-radius: 5px;\n"
"                border-bottom-right-radius: 5px;\n"
"            }\n"
"\n"
"            QComboBox::down-arrow {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"                image: url(:/sowInterface/arrowDown.png);\n"
"            }\n"
"\n"
"            QComboBox::down-arrow:hover {\n"
"                width: 12px;\n"
"                height: 12px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView {\n"
"                background-color: #2b2b2b;\n"
"                color: #e0e0e0;\n"
"                border: 1px solid rgb(70, 70, 70);\n"
"                border-radius: 6px;\n"
"                padding: 5px;\n"
"                outline: 0px;\n"
"                selection-color: #ffffff;\n"
"                selection-background-color: #8f8f8f;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item {\n"
"                border: none;\n"
"                height: 20px;\n"
"                padding: 4px 8px;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:hover {\n"
"                background-color: #5a5a5a;\n"
"                color: white;\n"
"            }\n"
"\n"
"            QComboBox QAbstractItemView::item:selected {\n"
"                background-color: #454545;\n"
"                color: white;\n"
"                border-radius: 4px;\n"
"            }\n"
"\n"
"            QScrollBar:vertical {\n"
"                background-color: #2b2b2b;\n"
"                width: 12px;\n"
"                margin: 0px;\n"
"                border: none;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical {\n"
"                background-color: #383838;\n"
"                min-height: 30px;\n"
"                border-radius: 3px;\n"
"                margin: 2px;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:hover {\n"
"                background-color: #454545;\n"
"            }\n"
"\n"
"            QScrollBar::handle:vertical:pressed {\n"
"                background-color: #424242;\n"
"            }\n"
"\n"
"            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"                border: none;\n"
"                background: none;\n"
"            }\n"
"\n"
"            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"                background: none;\n"
"            }")
        self.comboBox_lorebook_building.setObjectName("comboBox_lorebook_building")
        self.comboBox_lorebook_building.addItem("None")
        self.gridLayout_33.addWidget(self.comboBox_lorebook_building, 1, 0, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_character_building_lorebook)
        self.frame_bottom_character_creation = QtWidgets.QFrame(parent=self.frame_character_building)
        self.frame_bottom_character_creation.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.frame_bottom_character_creation.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_bottom_character_creation.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_bottom_character_creation.setObjectName("frame_bottom_character_creation")
        self.gridLayout_15 = QtWidgets.QGridLayout(self.frame_bottom_character_creation)
        self.gridLayout_15.setObjectName("gridLayout_15")
        spacerItem26 = QtWidgets.QSpacerItem(550, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_15.addItem(spacerItem26, 0, 1, 1, 1)
        self.pushButton_create_character_3 = QtWidgets.QPushButton(parent=self.frame_bottom_character_creation)
        self.pushButton_create_character_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_create_character_3.setMinimumSize(QtCore.QSize(191, 41))
        self.pushButton_create_character_3.setMaximumSize(QtCore.QSize(16777215, 41))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(11)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_create_character_3.setFont(font)
        self.pushButton_create_character_3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_3.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_create_character_3.setAutoFillBackground(False)
        self.pushButton_create_character_3.setStyleSheet("QPushButton {\n"
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
        self.pushButton_create_character_3.setIconSize(QtCore.QSize(19, 19))
        self.pushButton_create_character_3.setObjectName("pushButton_create_character_3")
        self.gridLayout_15.addWidget(self.pushButton_create_character_3, 0, 2, 1, 1)
        self.total_tokens_building_label = QtWidgets.QLabel(parent=self.frame_bottom_character_creation)
        self.total_tokens_building_label.setMinimumSize(QtCore.QSize(201, 51))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.total_tokens_building_label.setFont(font)
        self.total_tokens_building_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.total_tokens_building_label.setObjectName("total_tokens_building_label")
        self.gridLayout_15.addWidget(self.total_tokens_building_label, 0, 0, 1, 1)
        self.verticalLayout_7.addWidget(self.frame_bottom_character_creation)
        self.frame_bottom_character_creation.raise_()
        self.frame_character_building_first_message.raise_()
        self.frame_character_building_name_description.raise_()
        self.frame_character_building_imahe.raise_()
        self.frame_character_building_title.raise_()
        self.frame_character_building_personality.raise_()
        self.frame_character_building_scenario.raise_()
        self.frame_character_building_example_messages.raise_()
        self.frame_character_building_alternate_greetings.raise_()
        self.frame_character_building_creator_notes.raise_()
        self.frame_character_building_character_version.raise_()
        self.verticalLayout_5.addWidget(self.frame_character_building)
        self.scrollArea_character_building.setWidget(self.scrollAreaWidgetContents_character_building)
        self.gridLayout_17.addWidget(self.scrollArea_character_building, 0, 0, 1, 1)
        self.stackedWidget.addWidget(self.create_character_page_2)
        
        self.charactersgateway_page = QtWidgets.QWidget()
        self.charactersgateway_page.setObjectName("charactersgateway_page")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.charactersgateway_page)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.frame_gateway_search = QtWidgets.QFrame(parent=self.charactersgateway_page)
        self.frame_gateway_search.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_gateway_search.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_gateway_search.setObjectName("frame_gateway_search")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.frame_gateway_search)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem23 = QtWidgets.QSpacerItem(612, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem23)
        self.checkBox_enable_nsfw = QtWidgets.QCheckBox(parent=self.frame_gateway_search)
        self.checkBox_enable_nsfw.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_nsfw.setMinimumSize(QtCore.QSize(91, 31))
        self.checkBox_enable_nsfw.setMaximumSize(QtCore.QSize(91, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight")
        font.setPointSize(11)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_nsfw.setFont(font)
        self.checkBox_enable_nsfw.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_nsfw.setLayoutDirection(QtCore.Qt.LayoutDirection.RightToLeft)
        self.checkBox_enable_nsfw.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_nsfw.setObjectName("checkBox_enable_nsfw")
        self.horizontalLayout_4.addWidget(self.checkBox_enable_nsfw)
        self.lineEdit_search_character = QtWidgets.QLineEdit(parent=self.frame_gateway_search)
        self.lineEdit_search_character.setMinimumSize(QtCore.QSize(250, 33))
        self.lineEdit_search_character.setMaximumSize(QtCore.QSize(250, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_search_character.setFont(font)
        self.lineEdit_search_character.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_search_character.setObjectName("lineEdit_search_character")
        self.horizontalLayout_4.addWidget(self.lineEdit_search_character)
        self.pushButton_search_character = QtWidgets.QPushButton(parent=self.frame_gateway_search)
        self.pushButton_search_character.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_search_character.setMinimumSize(QtCore.QSize(27, 27))
        self.pushButton_search_character.setMaximumSize(QtCore.QSize(27, 27))
        self.pushButton_search_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_search_character.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0); border: none;  border-radius: 13px; }\n"
"QPushButton:hover { background-color: rgb(50, 50, 50); border-style: solid; border-radius: 13px; }\n"
"QPushButton:pressed { background-color: rgb(23, 23, 23); border-style: solid; border-radius: 13px; }\n"
"")
        self.pushButton_search_character.setText("")
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap("app/gui/icons/search.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_search_character.setIcon(icon8)
        self.pushButton_search_character.setIconSize(QtCore.QSize(16, 16))
        self.pushButton_search_character.setFlat(True)
        self.pushButton_search_character.setObjectName("pushButton_search_character")
        self.horizontalLayout_4.addWidget(self.pushButton_search_character)
        self.verticalLayout_3.addWidget(self.frame_gateway_search)
        
        self.tabWidget_characters_gateway = QtWidgets.QTabWidget(parent=self.charactersgateway_page)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.tabWidget_characters_gateway.setFont(font)
        self.tabWidget_characters_gateway.setStyleSheet("QTabWidget::pane {\n"
"    border: none;\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 3px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QTabWidget::tab-bar {\n"
"    alignment: center;\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: rgba(43, 43, 43, 0.8);\n"
"    color: rgb(180, 180, 180);\n"
"    padding: 8px 20px;\n"
"    margin: 1px;\n"
"    border: none;\n"
"    font-size: 12px;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: rgba(60, 60, 60, 0.9);\n"
"    color: rgb(227, 227, 227);\n"
"    font-weight: bold;\n"
"    border-bottom: 2px solid rgba(255, 255, 255, 0.1);\n"
"}\n"
"\n"
"QTabBar::tab:hover {\n"
"    background-color: rgba(50, 50, 50, 0.9);\n"
"    color: rgb(227, 227, 227);\n"
"}\n"
"\n"
"QTabBar::tab:disabled {\n"
"    background-color: rgba(30, 30, 30, 0.6);\n"
"    color: rgb(100, 100, 100);\n"
"}\n"
"\n"
"QTabBar::tab:!selected {\n"
"    margin-top: 3px;\n"
"}")
        self.tabWidget_characters_gateway.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.tabWidget_characters_gateway.setTabShape(QtWidgets.QTabWidget.TabShape.Rounded)
        self.tabWidget_characters_gateway.setObjectName("tabWidget_characters_gateway")
        
        self.tab_character_ai = QtWidgets.QWidget()
        self.tab_character_ai.setObjectName("tab_character_ai")
        self.tab_character_ai.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.gridLayout_18 = QtWidgets.QGridLayout(self.tab_character_ai)
        self.gridLayout_18.setObjectName("gridLayout_18")
        self.stackedWidget_character_ai = QtWidgets.QStackedWidget(parent=self.tab_character_ai)
        self.stackedWidget_character_ai.setObjectName("stackedWidget_character_ai")
        
        # ====================== Character AI Page ======================
        self.character_ai_page = QtWidgets.QWidget()
        self.character_ai_page.setObjectName("character_ai_page")
        
        self.gridLayout_21 = QtWidgets.QGridLayout(self.character_ai_page)
        self.gridLayout_21.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_21.setSpacing(0)
        self.gridLayout_21.setObjectName("gridLayout_21")
        
        self.scrollArea_character_ai_page = QtWidgets.QScrollArea(parent=self.character_ai_page)
        self.scrollArea_character_ai_page.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgb(27,27,27);
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
        self.scrollArea_character_ai_page.setWidgetResizable(True)
        self.scrollArea_character_ai_page.setObjectName("scrollArea_character_ai_page")
        self.scrollAreaWidgetContents_character_ai = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_ai.setGeometry(QtCore.QRect(0, 0, 1019, 495))
        self.scrollAreaWidgetContents_character_ai.setObjectName("scrollAreaWidgetContents_character_ai")
        self.scrollArea_character_ai_page.setWidget(self.scrollAreaWidgetContents_character_ai)
        self.gridLayout_21.addWidget(self.scrollArea_character_ai_page, 0, 0, 1, 1)
        self.stackedWidget_character_ai.addWidget(self.character_ai_page)
        
        # ====================== Character AI Search Page ======================
        
        self.gridLayout_18.addWidget(self.stackedWidget_character_ai, 0, 0, 1, 1)
        self.tabWidget_characters_gateway.addTab(self.tab_character_ai, "")

        self.tab_character_cards = QtWidgets.QWidget()
        self.tab_character_cards.setObjectName("tab_character_cards")
        self.tab_character_cards.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.gridLayout_19 = QtWidgets.QGridLayout(self.tab_character_cards)
        self.gridLayout_19.setObjectName("gridLayout_19")
        self.stackedWidget_character_card_gateway = QtWidgets.QStackedWidget(parent=self.tab_character_cards)
        self.stackedWidget_character_card_gateway.setObjectName("stackedWidget_character_card_gateway")
        
        # ====================== Character Card Page ======================
        self.character_card_page = QtWidgets.QWidget()
        self.character_card_page.setObjectName("character_card_page")
        self.gridLayout_22 = QtWidgets.QGridLayout(self.character_card_page)
        self.gridLayout_22.setContentsMargins(0, 0, 0, 0)
        self.gridLayout_22.setSpacing(0)
        self.gridLayout_22.setObjectName("gridLayout_22")


        self.scrollArea_character_card = QtWidgets.QScrollArea(parent=self.character_card_page)
        self.scrollArea_character_card.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: rgb(27,27,27);
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
        self.scrollArea_character_card.setWidgetResizable(True)
        self.scrollArea_character_card.setObjectName("scrollArea_character_card")
        self.scrollAreaWidgetContents_character_card = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_card.setGeometry(QtCore.QRect(0, 0, 1021, 497))
        self.scrollAreaWidgetContents_character_card.setObjectName("scrollAreaWidgetContents_character_card")
        self.scrollArea_character_card.setWidget(self.scrollAreaWidgetContents_character_card)
        self.gridLayout_22.addWidget(self.scrollArea_character_card, 0, 0, 1, 1)
        self.stackedWidget_character_card_gateway.addWidget(self.character_card_page)
        
        # ====================== Character Card Search Page ======================
        self.gridLayout_19.addWidget(self.stackedWidget_character_card_gateway, 0, 0, 1, 1)
        self.tabWidget_characters_gateway.addTab(self.tab_character_cards, "")
        self.verticalLayout_3.addWidget(self.tabWidget_characters_gateway)
        self.tabWidget_characters_gateway.raise_()
        self.frame_gateway_search.raise_()
        self.stackedWidget.addWidget(self.charactersgateway_page)
        
        # ====================== Options Page ======================
        self.options_page = QtWidgets.QWidget()
        self.options_page.setObjectName("options_page")
        self.gridLayout = QtWidgets.QGridLayout(self.options_page)
        self.gridLayout.setObjectName("gridLayout")
        self.tabWidget_options = QtWidgets.QTabWidget(parent=self.options_page)
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.tabWidget_options.setFont(font)
        self.tabWidget_options.setStyleSheet("QTabWidget::pane {\n"
"    border: none;\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 3px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QTabWidget::tab-bar {\n"
"    alignment: center;\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: rgba(43, 43, 43, 0.8);\n"
"    color: rgb(180, 180, 180);\n"
"    padding: 8px 20px;\n"
"    margin: 1px;\n"
"    border: none;\n"
"    font-size: 12px;\n"
"    border-radius: 3px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: rgba(60, 60, 60, 0.9);\n"
"    color: rgb(227, 227, 227);\n"
"    font-weight: bold;\n"
"    border-bottom: 2px solid rgba(255, 255, 255, 0.1);\n"
"}\n"
"\n"
"QTabBar::tab:hover {\n"
"    background-color: rgba(50, 50, 50, 0.9);\n"
"    color: rgb(227, 227, 227);\n"
"}\n"
"\n"
"QTabBar::tab:disabled {\n"
"    background-color: rgba(30, 30, 30, 0.6);\n"
"    color: rgb(100, 100, 100);\n"
"}\n"
"\n"
"QTabBar::tab:!selected {\n"
"    margin-top: 3px;\n"
"}")
        self.tabWidget_options.setObjectName("tabWidget_options")
        self.configuration_tab = QtWidgets.QWidget()
        self.configuration_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.configuration_tab.setStyleSheet("")
        self.configuration_tab.setObjectName("configuration_tab")
        self.configuration_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.conversation_method_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_title_label.setGeometry(QtCore.QRect(10, 10, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.conversation_method_title_label.setFont(font)
        self.conversation_method_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.conversation_method_title_label.setObjectName("conversation_method_title_label")
        self.conversation_method_token_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_token_title_label.setGeometry(QtCore.QRect(21, 126, 141, 20))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.conversation_method_token_title_label.setFont(font)
        self.conversation_method_token_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.conversation_method_token_title_label.setObjectName("conversation_method_token_title_label")
        self.lineEdit_api_token_options = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_api_token_options.setGeometry(QtCore.QRect(20, 150, 291, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_api_token_options.setFont(font)
        self.lineEdit_api_token_options.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_api_token_options.setObjectName("lineEdit_api_token_options")
        self.conversation_method_options_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_options_label.setGeometry(QtCore.QRect(21, 60, 221, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.conversation_method_options_label.setFont(font)
        self.conversation_method_options_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.conversation_method_options_label.setObjectName("conversation_method_options_label")
        self.comboBox_conversation_method = QtWidgets.QComboBox(parent=self.configuration_tab)
        self.comboBox_conversation_method.setGeometry(QtCore.QRect(20, 80, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_conversation_method.setFont(font)
        self.comboBox_conversation_method.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_conversation_method.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_conversation_method.setGraphicsEffect(shadow)
        self.comboBox_conversation_method.setObjectName("comboBox_conversation_method")
        self.comboBox_conversation_method.addItem("")
        self.comboBox_conversation_method.addItem("")
        self.comboBox_conversation_method.addItem("")
        self.comboBox_conversation_method.addItem("")
        self.separator_options_4 = QtWidgets.QFrame(parent=self.configuration_tab)
        self.separator_options_4.setGeometry(QtCore.QRect(20, 240, 1070, 3))
        self.separator_options_4.setMaximumSize(QtCore.QSize(16777215, 3))
        self.separator_options_4.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_options_4.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_4.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_4.setObjectName("separator_options_4")
        self.choose_your_name_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.choose_your_name_label.setGeometry(QtCore.QRect(20, 348, 161, 20))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_your_name_label.setFont(font)
        self.choose_your_name_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_your_name_label.setObjectName("choose_your_name_label")
        self.user_building_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.user_building_title_label.setGeometry(QtCore.QRect(10, 251, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.user_building_title_label.setFont(font)
        self.user_building_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.user_building_title_label.setObjectName("user_building_title_label")
        
        self.openrouter_models_options_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.openrouter_models_options_label.setEnabled(True)
        self.openrouter_models_options_label.setGeometry(QtCore.QRect(330, 130, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.openrouter_models_options_label.setFont(font)
        self.openrouter_models_options_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.openrouter_models_options_label.setObjectName("openrouter_models_options_label")
        self.comboBox_openrouter_models = QtWidgets.QComboBox(parent=self.configuration_tab)
        self.comboBox_openrouter_models.setGeometry(QtCore.QRect(330, 190, 311, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_openrouter_models.setFont(font)
        self.comboBox_openrouter_models.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_openrouter_models.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_openrouter_models.setGraphicsEffect(shadow)
        self.comboBox_openrouter_models.setObjectName("comboBox_openrouter_models")
        self.lineEdit_search_openrouter_models = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_search_openrouter_models.setGeometry(QtCore.QRect(330, 150, 251, 33))
        self.lineEdit_search_openrouter_models.setMinimumSize(QtCore.QSize(200, 33))
        self.lineEdit_search_openrouter_models.setMaximumSize(QtCore.QSize(260, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_search_openrouter_models.setFont(font)
        self.lineEdit_search_openrouter_models.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_search_openrouter_models.setObjectName("lineEdit_search_openrouter_models")
        self.lineEdit_base_url_options = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_base_url_options.setGeometry(QtCore.QRect(20, 190, 291, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_base_url_options.setFont(font)
        self.lineEdit_base_url_options.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_base_url_options.setObjectName("lineEdit_base_url_options")
        
        self.lineEdit_mistral_model = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_mistral_model.setGeometry(QtCore.QRect(20, 190, 291, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_mistral_model.setFont(font)
        self.lineEdit_mistral_model.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_mistral_model.setObjectName("lineEdit_mistral_model")

        self.personas_button = QtWidgets.QPushButton(parent=self.configuration_tab)
        self.personas_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.personas_button.setGeometry(QtCore.QRect(20, 300, 190, 35))
        self.personas_button.setMinimumSize(QtCore.QSize(25, 25))
        self.personas_button.setMaximumSize(QtCore.QSize(1000, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.personas_button.setFont(font)
        self.personas_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.personas_button.setStyleSheet("QPushButton {\n"
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
        icon_personas = QtGui.QIcon()
        icon_personas.addPixmap(QtGui.QPixmap("app/gui/icons/personas.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.personas_button.setIcon(icon_personas)
        self.personas_button.setIconSize(QtCore.QSize(19, 19))
        self.personas_button.setCheckable(False)
        self.personas_button.setObjectName("personas_button")
        self.tabWidget_options.addTab(self.configuration_tab, "")
        self.system_tab = QtWidgets.QWidget()
        self.system_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.system_tab.setStyleSheet("")
        self.system_tab.setObjectName("system_tab")
        self.system_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.language_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.language_title_label.setGeometry(QtCore.QRect(10, 10, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.language_title_label.setFont(font)
        self.language_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.language_title_label.setObjectName("language_title_label")
        self.comboBox_program_language = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_program_language.setGeometry(QtCore.QRect(20, 80, 131, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_program_language.setFont(font)
        self.comboBox_program_language.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_program_language.setStyleSheet("""
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
        self.comboBox_program_language.setObjectName("comboBox_program_language")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_program_language.setGraphicsEffect(shadow)
        self.comboBox_program_language.addItem("")
        self.comboBox_program_language.addItem("")
        self.separator_options_2 = QtWidgets.QFrame(parent=self.system_tab)
        self.separator_options_2.setGeometry(QtCore.QRect(20, 130, 1070, 3))
        self.separator_options_2.setMaximumSize(QtCore.QSize(16777215, 3))
        self.separator_options_2.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_options_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_2.setObjectName("separator_options_2")
        self.devices_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.devices_title_label.setGeometry(QtCore.QRect(10, 150, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.devices_title_label.setFont(font)
        self.devices_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.devices_title_label.setObjectName("devices_title_label")
        self.input_device_label = QtWidgets.QLabel(parent=self.system_tab)
        self.input_device_label.setGeometry(QtCore.QRect(20, 200, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.input_device_label.setFont(font)
        self.input_device_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.input_device_label.setObjectName("input_device_label")
        self.comboBox_input_devices = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_input_devices.setGeometry(QtCore.QRect(20, 220, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_input_devices.setFont(font)
        self.comboBox_input_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_input_devices.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_input_devices.setGraphicsEffect(shadow)
        self.comboBox_input_devices.setObjectName("comboBox_input_devices")
        self.output_device_label = QtWidgets.QLabel(parent=self.system_tab)
        self.output_device_label.setGeometry(QtCore.QRect(20, 270, 140, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.output_device_label.setFont(font)
        self.output_device_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.output_device_label.setObjectName("output_device_label")
        self.comboBox_output_devices = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_output_devices.setGeometry(QtCore.QRect(20, 290, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_output_devices.setFont(font)
        self.comboBox_output_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_output_devices.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_output_devices.setGraphicsEffect(shadow)
        self.comboBox_output_devices.setObjectName("comboBox_output_devices")
        self.program_language_label = QtWidgets.QLabel(parent=self.system_tab)
        self.program_language_label.setGeometry(QtCore.QRect(20, 60, 221, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.program_language_label.setFont(font)
        self.program_language_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.program_language_label.setObjectName("program_language_label")
        self.translator_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.translator_title_label.setGeometry(QtCore.QRect(10, 360, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.translator_title_label.setFont(font)
        self.translator_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.translator_title_label.setObjectName("translator_title_label")
        self.separator_options_3 = QtWidgets.QFrame(parent=self.system_tab)
        self.separator_options_3.setGeometry(QtCore.QRect(20, 340, 1070, 3))
        self.separator_options_3.setMaximumSize(QtCore.QSize(16777215, 3))
        self.separator_options_3.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_options_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_3.setObjectName("separator_options_3")
        self.choose_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.choose_translator_label.setGeometry(QtCore.QRect(20, 410, 181, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_translator_label.setFont(font)
        self.choose_translator_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_translator_label.setObjectName("choose_translator_label")
        self.comboBox_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_translator.setGeometry(QtCore.QRect(19, 431, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_translator.setFont(font)
        self.comboBox_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_translator.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_translator.setGraphicsEffect(shadow)
        self.comboBox_translator.setObjectName("comboBox_translator")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.target_language_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.target_language_translator_label.setGeometry(QtCore.QRect(220, 410, 141, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.target_language_translator_label.setFont(font)
        self.target_language_translator_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.target_language_translator_label.setObjectName("target_language_translator_label")
        self.comboBox_target_language_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_target_language_translator.setGeometry(QtCore.QRect(220, 430, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_target_language_translator.setFont(font)
        self.comboBox_target_language_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_target_language_translator.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_target_language_translator.setGraphicsEffect(shadow)
        self.comboBox_target_language_translator.setObjectName("comboBox_target_language_translator")
        self.comboBox_target_language_translator.addItem("")
        self.comboBox_mode_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_mode_translator.setGeometry(QtCore.QRect(380, 430, 161, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_mode_translator.setFont(font)
        self.comboBox_mode_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_mode_translator.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_mode_translator.setGraphicsEffect(shadow)
        self.comboBox_mode_translator.setObjectName("comboBox_mode_translator")
        self.comboBox_mode_translator.addItem("")
        self.comboBox_mode_translator.addItem("")
        self.comboBox_mode_translator.addItem("")
        self.mode_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.mode_translator_label.setGeometry(QtCore.QRect(380, 410, 131, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.mode_translator_label.setFont(font)
        self.mode_translator_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.mode_translator_label.setObjectName("mode_translator_label")
        self.computer_specs_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.computer_specs_title_label.setGeometry(QtCore.QRect(10, 500, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.computer_specs_title_label.setFont(font)
        self.computer_specs_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.computer_specs_title_label.setObjectName("computer_specs_title_label")
        self.separator_options_5 = QtWidgets.QFrame(parent=self.system_tab)
        self.separator_options_5.setGeometry(QtCore.QRect(20, 480, 1070, 3))
        self.separator_options_5.setMaximumSize(QtCore.QSize(16777215, 3))
        self.separator_options_5.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_options_5.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_5.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_5.setObjectName("separator_options_5")
        self.ram_label = QtWidgets.QLabel(parent=self.system_tab)
        self.ram_label.setGeometry(QtCore.QRect(50, 547, 201, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.ram_label.setFont(font)
        self.ram_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.ram_label.setScaledContents(False)
        self.ram_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.ram_label.setObjectName("ram_label")
        self.ram_label_icon = QtWidgets.QLabel(parent=self.system_tab)
        self.ram_label_icon.setGeometry(QtCore.QRect(20, 553, 20, 20))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.ram_label_icon.setFont(font)
        self.ram_label_icon.setStyleSheet("color: rgb(227, 227, 227);")
        self.ram_label_icon.setText("")
        self.ram_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/memory.png"))
        self.ram_label_icon.setScaledContents(True)
        self.ram_label_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.ram_label_icon.setObjectName("ram_label_icon")
        self.gpu_label_icon = QtWidgets.QLabel(parent=self.system_tab)
        self.gpu_label_icon.setGeometry(QtCore.QRect(20, 587, 20, 20))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.gpu_label_icon.setFont(font)
        self.gpu_label_icon.setStyleSheet("color: rgb(227, 227, 227);")
        self.gpu_label_icon.setText("")
        self.gpu_label_icon.setPixmap(QtGui.QPixmap("app/gui/icons/gpu.png"))
        self.gpu_label_icon.setScaledContents(True)
        self.gpu_label_icon.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.gpu_label_icon.setObjectName("gpu_label_icon")
        self.gpu_label = QtWidgets.QLabel(parent=self.system_tab)
        self.gpu_label.setGeometry(QtCore.QRect(50, 582, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.gpu_label.setFont(font)
        self.gpu_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.gpu_label.setScaledContents(False)
        self.gpu_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.gpu_label.setObjectName("gpu_label")

        self.tabWidget_options.addTab(self.system_tab, "")
        self.llm_tab = QtWidgets.QWidget()
        self.llm_tab.setObjectName("llm_tab")
        self.llm_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.llm_options_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_options_label.setGeometry(QtCore.QRect(20, 60, 150, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.llm_options_label.setFont(font)
        self.llm_options_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.llm_options_label.setObjectName("llm_options_label")
        self.llm_title_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_title_label.setGeometry(QtCore.QRect(10, 10, 301, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.llm_title_label.setFont(font)
        self.llm_title_label.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.llm_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.llm_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.llm_title_label.setObjectName("llm_title_label")
        self.choose_llm_device_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.choose_llm_device_label.setGeometry(QtCore.QRect(20, 128, 101, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_llm_device_label.setFont(font)
        self.choose_llm_device_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_llm_device_label.setObjectName("choose_llm_device_label")
        self.comboBox_llm_devices = QtWidgets.QComboBox(parent=self.llm_tab)
        self.comboBox_llm_devices.setGeometry(QtCore.QRect(20, 155, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_llm_devices.setFont(font)
        self.comboBox_llm_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_llm_devices.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_llm_devices.setGraphicsEffect(shadow)
        self.comboBox_llm_devices.setObjectName("comboBox_llm_devices")
        self.comboBox_llm_devices.addItem("")
        self.comboBox_llm_devices.addItem("")
        self.gpu_layers_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.gpu_layers_label.setGeometry(QtCore.QRect(20, 203, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.gpu_layers_label.setFont(font)
        self.gpu_layers_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.gpu_layers_label.setObjectName("gpu_layers_label")
        self.checkBox_enable_mlock = QtWidgets.QCheckBox(parent=self.llm_tab)
        self.checkBox_enable_mlock.setGeometry(QtCore.QRect(20, 328, 131, 41))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_mlock.setFont(font)
        self.checkBox_enable_mlock.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_mlock.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_mlock.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_mlock.setObjectName("checkBox_enable_mlock")
        self.context_size_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.context_size_label.setGeometry(QtCore.QRect(20, 266, 161, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.context_size_label.setFont(font)
        self.context_size_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.context_size_label.setObjectName("context_size_label")
        self.line_llm = QtWidgets.QFrame(parent=self.llm_tab)
        self.line_llm.setGeometry(QtCore.QRect(20, 388, 1070, 3))
        self.line_llm.setMaximumSize(QtCore.QSize(16777215, 3))
        self.line_llm.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.line_llm.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_llm.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_llm.setObjectName("line_llm")
        self.llm_title_label_2 = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_title_label_2.setGeometry(QtCore.QRect(10, 400, 401, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.llm_title_label_2.setFont(font)
        self.llm_title_label_2.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.llm_title_label_2.setStyleSheet("color: rgb(227, 227, 227);")
        self.llm_title_label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.llm_title_label_2.setObjectName("llm_title_label_2")
        self.reapet_penalty_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.reapet_penalty_label.setGeometry(QtCore.QRect(290, 448, 151, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.reapet_penalty_label.setFont(font)
        self.reapet_penalty_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.reapet_penalty_label.setObjectName("reapet_penalty_label")
        self.temperature_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.temperature_label.setGeometry(QtCore.QRect(20, 448, 131, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.temperature_label.setFont(font)
        self.temperature_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.temperature_label.setObjectName("temperature_label")
        self.temperature_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.temperature_horizontalSlider.setGeometry(QtCore.QRect(20, 468, 160, 22))
        self.temperature_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.temperature_horizontalSlider.setMinimum(0)
        self.temperature_horizontalSlider.setMaximum(20)
        self.temperature_horizontalSlider.setSingleStep(1)
        self.temperature_horizontalSlider.setProperty("value", 10)
        self.temperature_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.temperature_horizontalSlider.setObjectName("temperature_horizontalSlider")
        self.temperature_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.temperature_value_label.setGeometry(QtCore.QRect(190, 448, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.temperature_value_label.setFont(font)
        self.temperature_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.temperature_value_label.setObjectName("temperature_value_label")
        self.top_p_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.top_p_label.setGeometry(QtCore.QRect(20, 500, 51, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.top_p_label.setFont(font)
        self.top_p_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.top_p_label.setObjectName("top_p_label")
        self.top_p_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.top_p_horizontalSlider.setGeometry(QtCore.QRect(20, 518, 160, 22))
        self.top_p_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.top_p_horizontalSlider.setMinimum(0)
        self.top_p_horizontalSlider.setMaximum(10)
        self.top_p_horizontalSlider.setSingleStep(1)
        self.top_p_horizontalSlider.setPageStep(0)
        self.top_p_horizontalSlider.setProperty("value", 10)
        self.top_p_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.top_p_horizontalSlider.setObjectName("top_p_horizontalSlider")
        self.top_p_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.top_p_value_label.setGeometry(QtCore.QRect(190, 499, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.top_p_value_label.setFont(font)
        self.top_p_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.top_p_value_label.setObjectName("top_p_value_label")
        self.gpu_layers_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.gpu_layers_horizontalSlider.setGeometry(QtCore.QRect(20, 225, 160, 22))
        self.gpu_layers_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.gpu_layers_horizontalSlider.setMinimum(1)
        self.gpu_layers_horizontalSlider.setMaximum(100)
        self.gpu_layers_horizontalSlider.setSingleStep(1)
        self.gpu_layers_horizontalSlider.setProperty("value", 1)
        self.gpu_layers_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.gpu_layers_horizontalSlider.setObjectName("gpu_layers_horizontalSlider")
        self.context_size_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.context_size_horizontalSlider.setGeometry(QtCore.QRect(20, 288, 160, 22))
        self.context_size_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.context_size_horizontalSlider.setMinimum(512)
        self.context_size_horizontalSlider.setMaximum(16384)
        self.context_size_horizontalSlider.setSingleStep(64)
        self.context_size_horizontalSlider.setPageStep(0)
        self.context_size_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.context_size_horizontalSlider.setObjectName("context_size_horizontalSlider")
        self.repeat_penalty_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.repeat_penalty_horizontalSlider.setGeometry(QtCore.QRect(290, 468, 160, 22))
        self.repeat_penalty_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.repeat_penalty_horizontalSlider.setMinimum(10)
        self.repeat_penalty_horizontalSlider.setMaximum(20)
        self.repeat_penalty_horizontalSlider.setSingleStep(1)
        self.repeat_penalty_horizontalSlider.setPageStep(0)
        self.repeat_penalty_horizontalSlider.setProperty("value", 10)
        self.repeat_penalty_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.repeat_penalty_horizontalSlider.setObjectName("repeat_penalty_horizontalSlider")
        self.max_tokens_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.max_tokens_label.setGeometry(QtCore.QRect(290, 500, 150, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.max_tokens_label.setFont(font)
        self.max_tokens_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.max_tokens_label.setObjectName("max_tokens_label")
        self.max_tokens_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.max_tokens_horizontalSlider.setGeometry(QtCore.QRect(290, 518, 160, 22))
        self.max_tokens_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"    background-color: #333;\n"
"    height: 8px;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::sub-page:horizontal {\n"
"    background-color: #555;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::add-page:horizontal {\n"
"    background-color: #2b2b2b;\n"
"    border-radius: 4px;\n"
"}\n"
"\n"
"QSlider::handle:horizontal {\n"
"    background-color: #e0e0e0;\n"
"    width: 16px;\n"
"    height: 16px;\n"
"    margin: -4px 0;\n"
"    border-radius: 8px;\n"
"    border: 2px solid #333;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: #ffffff;\n"
"    border: 2px solid #555;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: #cccccc;\n"
"    border: 2px solid #2b2b2b;\n"
"}\n"
"\n"
"QSlider::groove:horizontal:disabled {\n"
"    background-color: #444;\n"
"}\n"
"\n"
"QSlider::handle:horizontal:disabled {\n"
"    background-color: #666;\n"
"    border: 2px solid #444;\n"
"}")
        self.max_tokens_horizontalSlider.setMinimum(16)
        self.max_tokens_horizontalSlider.setMaximum(2048)
        self.max_tokens_horizontalSlider.setSingleStep(12)
        self.max_tokens_horizontalSlider.setPageStep(0)
        self.max_tokens_horizontalSlider.setProperty("value", 16)
        self.max_tokens_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.max_tokens_horizontalSlider.setObjectName("max_tokens_horizontalSlider")
        self.repeat_penalty_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.repeat_penalty_value_label.setGeometry(QtCore.QRect(460, 448, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.repeat_penalty_value_label.setFont(font)
        self.repeat_penalty_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.repeat_penalty_value_label.setObjectName("repeat_penalty_value_label")
        self.max_tokens_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.max_tokens_value_label.setGeometry(QtCore.QRect(460, 499, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.max_tokens_value_label.setFont(font)
        self.max_tokens_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.max_tokens_value_label.setObjectName("max_tokens_value_label")
        self.context_size_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.context_size_value_label.setGeometry(QtCore.QRect(190, 266, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.context_size_value_label.setFont(font)
        self.context_size_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.context_size_value_label.setObjectName("context_size_value_label")
        self.gpu_layers_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.gpu_layers_value_label.setGeometry(QtCore.QRect(190, 203, 61, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.gpu_layers_value_label.setFont(font)
        self.gpu_layers_value_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.gpu_layers_value_label.setObjectName("gpu_layers_value_label")
        self.lineEdit_gpuLayers = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_gpuLayers.setGeometry(QtCore.QRect(190, 225, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_gpuLayers.setFont(font)
        self.lineEdit_gpuLayers.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_gpuLayers.setText("")
        self.lineEdit_gpuLayers.setReadOnly(False)
        self.lineEdit_gpuLayers.setObjectName("lineEdit_gpuLayers")
        self.lineEdit_contextSize = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_contextSize.setGeometry(QtCore.QRect(190, 288, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_contextSize.setFont(font)
        self.lineEdit_contextSize.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_contextSize.setText("")
        self.lineEdit_contextSize.setObjectName("lineEdit_contextSize")
        self.lineEdit_temperature = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_temperature.setGeometry(QtCore.QRect(190, 468, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_temperature.setFont(font)
        self.lineEdit_temperature.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_temperature.setText("")
        self.lineEdit_temperature.setObjectName("lineEdit_temperature")
        self.lineEdit_topP = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_topP.setGeometry(QtCore.QRect(190, 518, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_topP.setFont(font)
        self.lineEdit_topP.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_topP.setText("")
        self.lineEdit_topP.setObjectName("lineEdit_topP")
        self.lineEdit_repeatPenalty = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_repeatPenalty.setGeometry(QtCore.QRect(460, 468, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_repeatPenalty.setFont(font)
        self.lineEdit_repeatPenalty.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_repeatPenalty.setText("")
        self.lineEdit_repeatPenalty.setObjectName("lineEdit_repeatPenalty")
        self.lineEdit_maxTokens = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_maxTokens.setGeometry(QtCore.QRect(460, 518, 60, 24))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_maxTokens.setFont(font)
        self.lineEdit_maxTokens.setStyleSheet("QLineEdit {\n"
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
"}")
        self.lineEdit_maxTokens.setText("")
        self.lineEdit_maxTokens.setObjectName("lineEdit_maxTokens")
        self.choose_llm_gpu_device_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.choose_llm_gpu_device_label.setGeometry(QtCore.QRect(150, 128, 111, 21))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_llm_gpu_device_label.setFont(font)
        self.choose_llm_gpu_device_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_llm_gpu_device_label.setObjectName("choose_llm_gpu_device_label")
        self.comboBox_llm_gpu_devices = QtWidgets.QComboBox(parent=self.llm_tab)
        self.comboBox_llm_gpu_devices.setGeometry(QtCore.QRect(150, 155, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_llm_gpu_devices.setFont(font)
        self.comboBox_llm_gpu_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_llm_gpu_devices.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_llm_gpu_devices.setGraphicsEffect(shadow)
        self.comboBox_llm_gpu_devices.setObjectName("comboBox_llm_gpu_devices")
        self.comboBox_llm_gpu_devices.addItem("")
        self.comboBox_llm_gpu_devices.addItem("")
        self.checkBox_enable_flash_attention = QtWidgets.QCheckBox(parent=self.llm_tab)
        self.checkBox_enable_flash_attention.setGeometry(QtCore.QRect(170, 328, 181, 41))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_flash_attention.setFont(font)
        self.checkBox_enable_flash_attention.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_flash_attention.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_flash_attention.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_flash_attention.setObjectName("checkBox_enable_flash_attention")

        self.lineEdit_server = QtWidgets.QLineEdit(parent=self.llm_tab)
        self.lineEdit_server.setGeometry(QtCore.QRect(20, 85, 241, 27))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(8)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_server.setFont(font)
        self.lineEdit_server.setStyleSheet("QLineEdit {\n"
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
        self.lineEdit_server.setDragEnabled(False)
        self.lineEdit_server.setReadOnly(True)
        self.lineEdit_server.setObjectName("lineEdit_server")
        self.system_prompt_button = QtWidgets.QPushButton(parent=self.llm_tab)
        self.system_prompt_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.system_prompt_button.setGeometry(QtCore.QRect(20, 570, 190, 35))
        self.system_prompt_button.setMinimumSize(QtCore.QSize(25, 25))
        self.system_prompt_button.setMaximumSize(QtCore.QSize(1000, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.system_prompt_button.setFont(font)
        self.system_prompt_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.system_prompt_button.setStyleSheet("QPushButton {\n"
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
        icon_system_prompt = QtGui.QIcon()
        icon_system_prompt.addPixmap(QtGui.QPixmap("app/gui/icons/system_prompt.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.system_prompt_button.setIcon(icon_system_prompt)
        self.system_prompt_button.setIconSize(QtCore.QSize(21, 21))
        self.system_prompt_button.setCheckable(False)
        self.system_prompt_button.setObjectName("system_prompt_button")
        self.lorebook_editor_button = QtWidgets.QPushButton(parent=self.llm_tab)
        self.lorebook_editor_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lorebook_editor_button.setGeometry(QtCore.QRect(220, 570, 181, 35))
        self.lorebook_editor_button.setMinimumSize(QtCore.QSize(25, 25))
        self.lorebook_editor_button.setMaximumSize(QtCore.QSize(1000, 35))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lorebook_editor_button.setFont(font)
        self.lorebook_editor_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.lorebook_editor_button.setStyleSheet("QPushButton {\n"
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
        icon_lorebook = QtGui.QIcon()
        icon_lorebook.addPixmap(QtGui.QPixmap("app/gui/icons/lorebook.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.lorebook_editor_button.setIcon(icon_lorebook)
        self.lorebook_editor_button.setIconSize(QtCore.QSize(21, 21))
        self.lorebook_editor_button.setCheckable(False)
        self.lorebook_editor_button.setObjectName("lorebook_editor_button")
        self.tabWidget_options.addTab(self.llm_tab, "")
        self.sow_system_tab = QtWidgets.QWidget()
        self.sow_system_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sow_system_tab.setObjectName("sow_system_tab")
        self.sow_system_tab.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scrollArea_modules = QtWidgets.QScrollArea(parent=self.sow_system_tab)
        self.scrollArea_modules.setEnabled(True)
        self.scrollArea_modules.setStyleSheet("QScrollArea {\n"
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
        self.scrollArea_modules.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_modules.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_modules.setWidgetResizable(True)
        self.scrollArea_modules.setObjectName("scrollArea_modules")

        self.scrollAreaWidgetContents_modules = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_modules.setObjectName("scrollAreaWidgetContents_modules")

        self.choose_live2d_mode_label = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.choose_live2d_mode_label.setGeometry(QtCore.QRect(20, 97, 141, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_live2d_mode_label.setFont(font)
        self.choose_live2d_mode_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_live2d_mode_label.setObjectName("choose_live2d_mode_label")
        self.comboBox_live2d_mode = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_live2d_mode.setGeometry(QtCore.QRect(20, 120, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_live2d_mode.setFont(font)
        self.comboBox_live2d_mode.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_live2d_mode.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_live2d_mode.setGraphicsEffect(shadow)
        self.comboBox_live2d_mode.setObjectName("comboBox_live2d_mode")
        self.comboBox_live2d_mode.addItem("")
        self.comboBox_live2d_mode.addItem("")
        self.checkBox_enable_sow_system = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContents_modules)
        self.checkBox_enable_sow_system.setGeometry(QtCore.QRect(20, 60, 291, 22))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkBox_enable_sow_system.sizePolicy().hasHeightForWidth())
        self.checkBox_enable_sow_system.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_sow_system.setFont(font)
        self.checkBox_enable_sow_system.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_sow_system.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_sow_system.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_sow_system.setIconSize(QtCore.QSize(16, 16))
        self.checkBox_enable_sow_system.setObjectName("checkBox_enable_sow_system")
        self.sow_system_title_label = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.sow_system_title_label.setGeometry(QtCore.QRect(10, 10, 211, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.sow_system_title_label.setFont(font)
        self.sow_system_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.sow_system_title_label.setObjectName("sow_system_title_label")
        self.separator_options = QtWidgets.QFrame(parent=self.scrollAreaWidgetContents_modules)
        self.separator_options.setGeometry(QtCore.QRect(20, 290, 1060, 3))
        self.separator_options.setMaximumSize(QtCore.QSize(16777215, 3))
        self.separator_options.setStyleSheet("QFrame {\n"
"        background-color: rgba(10, 10, 10, 80);\n"
"        border-radius: 2px;\n"
"        height: 1px;\n"
"}")
        self.separator_options.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options.setObjectName("separator_options")
        self.sow_system_modules_title_label = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.sow_system_modules_title_label.setGeometry(QtCore.QRect(10, 310, 171, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.sow_system_modules_title_label.setFont(font)
        self.sow_system_modules_title_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.sow_system_modules_title_label.setObjectName("sow_system_modules_title_label")
        self.speech_to_text_method_label = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.speech_to_text_method_label.setGeometry(QtCore.QRect(21, 360, 151, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.speech_to_text_method_label.setFont(font)
        self.speech_to_text_method_label.setStyleSheet("color: rgb(227, 227, 227);")
        self.speech_to_text_method_label.setObjectName("speech_to_text_method_label")
        self.comboBox_speech_to_text_method = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(20, 380, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_speech_to_text_method.setFont(font)
        self.comboBox_speech_to_text_method.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_speech_to_text_method.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_speech_to_text_method.setGraphicsEffect(shadow)
        self.comboBox_speech_to_text_method.setObjectName("comboBox_speech_to_text_method")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.choose_model_fps = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.choose_model_fps.setGeometry(QtCore.QRect(180, 97, 151, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_model_fps.setFont(font)
        self.choose_model_fps.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_model_fps.setObjectName("choose_model_fps")
        self.comboBox_model_fps = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_model_fps.setGeometry(QtCore.QRect(180, 120, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_model_fps.setFont(font)
        self.comboBox_model_fps.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_model_fps.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_model_fps.setGraphicsEffect(shadow)
        self.comboBox_model_fps.setObjectName("comboBox_model_fps")
        self.comboBox_model_fps.addItem("")
        self.comboBox_model_fps.addItem("")
        self.comboBox_model_fps.addItem("")
        
        self.comboBox_model_background = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_model_background.setGeometry(QtCore.QRect(20, 190, 151, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_model_background.setFont(font)
        self.comboBox_model_background.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_model_background.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_model_background.setGraphicsEffect(shadow)
        self.comboBox_model_background.setObjectName("comboBox_model_background")
        self.comboBox_model_background.addItem("")
        self.comboBox_model_background.addItem("")
        self.choose_model_background = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.choose_model_background.setGeometry(QtCore.QRect(20, 167, 161, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_model_background.setFont(font)
        self.choose_model_background.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_model_background.setObjectName("choose_model_background")
        self.comboBox_model_bg_color = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_model_bg_color.setGeometry(QtCore.QRect(190, 190, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_model_bg_color.setFont(font)
        self.comboBox_model_bg_color.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_model_bg_color.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_model_bg_color.setGraphicsEffect(shadow)
        self.comboBox_model_bg_color.setObjectName("comboBox_model_bg_color")
        self.comboBox_model_bg_color.addItem("")
        self.comboBox_model_bg_color.addItem("")
        self.comboBox_model_bg_color.addItem("")
        self.comboBox_model_bg_color.addItem("")
        self.comboBox_model_bg_color.addItem("")
        self.comboBox_model_bg_color.addItem("")
        self.choose_model_bg_color = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.choose_model_bg_color.setGeometry(QtCore.QRect(190, 167, 181, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_model_bg_color.setFont(font)
        self.choose_model_bg_color.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_model_bg_color.setObjectName("choose_model_bg_color")
        self.choose_model_bg_image = QtWidgets.QLabel(parent=self.scrollAreaWidgetContents_modules)
        self.choose_model_bg_image.setGeometry(QtCore.QRect(190, 167, 181, 16))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.choose_model_bg_image.setFont(font)
        self.choose_model_bg_image.setStyleSheet("color: rgb(227, 227, 227);")
        self.choose_model_bg_image.setObjectName("choose_model_bg_image")
        self.comboBox_model_bg_image = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_model_bg_image.setGeometry(QtCore.QRect(190, 190, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_model_bg_image.setFont(font)
        self.comboBox_model_bg_image.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_model_bg_image.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_model_bg_image.setGraphicsEffect(shadow)
        self.comboBox_model_bg_image.setObjectName("comboBox_model_bg_image")
        self.pushButton_reload_bg_image = QtWidgets.QPushButton(parent=self.scrollAreaWidgetContents_modules)
        self.pushButton_reload_bg_image.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_bg_image.setGeometry(QtCore.QRect(380, 190, 30, 30))
        self.pushButton_reload_bg_image.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_reload_bg_image.setMaximumSize(QtCore.QSize(30, 30))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_reload_bg_image.setFont(font)
        self.pushButton_reload_bg_image.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_reload_bg_image.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 15px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(30, 30, 30); \n"
"    border-style: solid; \n"
"    border-radius: 15px;\n"
"}")
        self.pushButton_reload_bg_image.setText("")
        icon_reload = QtGui.QIcon()
        icon_reload.addPixmap(QtGui.QPixmap("app/gui/icons/reload.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_reload_bg_image.setIcon(icon_reload)
        self.pushButton_reload_bg_image.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_reload_bg_image.setCheckable(False)
        self.pushButton_reload_bg_image.setAutoExclusive(True)
        self.pushButton_reload_bg_image.setObjectName("pushButton_reload_bg_image")

        self.pushButton_reload_ambient = QtWidgets.QPushButton(parent=self.scrollAreaWidgetContents_modules)
        self.pushButton_reload_ambient.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_reload_ambient.setGeometry(QtCore.QRect(390, 240, 30, 30))
        self.pushButton_reload_ambient.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_reload_ambient.setMaximumSize(QtCore.QSize(30, 30))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_reload_ambient.setFont(font)
        self.pushButton_reload_ambient.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_reload_ambient.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 15px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(30, 30, 30); \n"
"    border-style: solid; \n"
"    border-radius: 15px;\n"
"}")
        self.pushButton_reload_ambient.setText("")
        icon_reload = QtGui.QIcon()
        icon_reload.addPixmap(QtGui.QPixmap("app/gui/icons/reload.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_reload_ambient.setIcon(icon_reload)
        self.pushButton_reload_ambient.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_reload_ambient.setCheckable(False)
        self.pushButton_reload_ambient.setAutoExclusive(True)
        self.pushButton_reload_ambient.setObjectName("pushButton_reload_ambient")
        self.comboBox_ambient_mode = QtWidgets.QComboBox(parent=self.scrollAreaWidgetContents_modules)
        self.comboBox_ambient_mode.setGeometry(QtCore.QRect(200, 240, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.comboBox_ambient_mode.setFont(font)
        self.comboBox_ambient_mode.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_ambient_mode.setStyleSheet("""
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)        
        self.comboBox_ambient_mode.setGraphicsEffect(shadow)
        self.comboBox_ambient_mode.setObjectName("comboBox_ambient_mode")
        self.checkBox_enable_ambient = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContents_modules)
        self.checkBox_enable_ambient.setGeometry(QtCore.QRect(20, 244, 171, 22))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkBox_enable_ambient.sizePolicy().hasHeightForWidth())
        self.checkBox_enable_ambient.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_ambient.setFont(font)
        self.checkBox_enable_ambient.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_ambient.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_ambient.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_ambient.setIconSize(QtCore.QSize(16, 16))
        self.checkBox_enable_ambient.setObjectName("checkBox_enable_ambient")
        self.checkBox_enable_memory = QtWidgets.QCheckBox(parent=self.scrollAreaWidgetContents_modules)
        self.checkBox_enable_memory.setGeometry(QtCore.QRect(20, 440, 221, 22))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.checkBox_enable_memory.sizePolicy().hasHeightForWidth())
        self.checkBox_enable_memory.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.checkBox_enable_memory.setFont(font)
        self.checkBox_enable_memory.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_memory.setStyleSheet("QCheckBox {\n"
"    color: #e0e0e0;\n"
"    spacing: 5px;\n"
"}\n"
"\n"
"QCheckBox::indicator {\n"
"    border: 2px solid #333;\n"
"    width: 18px;\n"
"    height: 18px;\n"
"    border-radius: 11px;\n"
"    background-color: #2b2b2b;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 2px solid #555;\n"
"    background-color: #3a3a3a;\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 2px solid #555;\n"
"    background-color: #444;\n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 18px;\n"
"    height: 18px;\n"
"}\n"
"\n"
"QCheckBox::indicator:disabled {\n"
"    border: 2px solid #444;\n"
"    background-color: #555;\n"
"}\n"
"\n"
"QCheckBox:disabled {\n"
"    color: #888;\n"
"}")
        self.checkBox_enable_memory.setIconSize(QtCore.QSize(16, 16))
        self.checkBox_enable_memory.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.checkBox_enable_memory.setObjectName("checkBox_enable_memory")

        self.scrollArea_modules.setWidget(self.scrollAreaWidgetContents_modules)
        tab_layout = QtWidgets.QVBoxLayout(self.sow_system_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)
        tab_layout.addWidget(self.scrollArea_modules)

        self.tabWidget_options.addTab(self.sow_system_tab, "")
        self.gridLayout.addWidget(self.tabWidget_options, 0, 0, 1, 1)
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
"    background-color: rgb(27,27,27);\n"
"    border: none;\n"
"}\n"
"\n"
"#user_name { \n"
"    color: rgb(179, 179, 179);\n"
"    font: 600 12pt \"Segoe UI\";\n"
"}\n"
"\n"
"#user_image {\n"
"    border: 1px solid rgb(30, 32, 33);\n"
"    background-color: rgb(47, 48, 50);\n"
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
        self.user_information_frame.setStyleSheet("")
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
        
        self.pushButton_change_chat_background = PushButton()
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
        self.pushButton_author_notes = PushButton()
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
        self.pushButton_more = PushButton()
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
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 2) 
        self.frame_separator_chat.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_separator_chat.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_separator_chat.setGraphicsEffect(shadow)
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
        self.frame_send_message_full.setStyleSheet("background-color: rgb(27,27,27); border: none;")
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
        #frame_send_message { 
                background-color: rgb(47, 48, 50);
                border-radius: 20px;
        }

        #frame_send_message QPushButton {
                background-color: rgb(76, 77, 80);
                border-radius: 15px;
                background-repeat: no-repeat;
                background-position: center;
        }

        #frame_send_message QPushButton:hover {
                background-color: rgb(81, 82, 86);
        }

        #frame_send_message QPushButton:pressed {
                background-color: rgb(16, 17, 18);
        }

        #frame_send_message QTextEdit {
                background-color: transparent;
                border: none;
                padding-top: 7px;
                padding-left: 15px;
                padding-right: 15px;
                background-repeat: none;
                background-position: left center;
                color: rgb(225, 225, 225);
        }

        #frame_send_message QTextEdit:focus {
                color: rgb(165, 165, 165);
        }

        #frame_send_message QScrollBar:vertical {
                background-color: #2b2b2b;
                width: 12px;
                margin: 0px;
                border-radius: 5px;
        }

        #frame_send_message QScrollBar::handle:vertical {
                background-color: #383838;
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
        }

        #frame_send_message QScrollBar::handle:vertical:hover {
                background-color: #454545;
        }

        #frame_send_message QScrollBar::handle:vertical:pressed {
                background-color: #424242;
        }

        #frame_send_message QScrollBar::add-line:vertical,
        #frame_send_message QScrollBar::sub-line:vertical {
                border: none;
                background: none;
        }

        #frame_send_message QScrollBar::add-page:vertical,
        #frame_send_message QScrollBar::sub-page:vertical {
                background: none;
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
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.frame_models_hub_search)
        self.horizontalLayout_8.setContentsMargins(30, 0, 30, 0)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")

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
        self.pushButton_models_hub_recommendations.setStyleSheet("QPushButton {\n"
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
"}\n"
"\n"
"QPushButton:checked {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #999999;\n"
"    font-weight: bold;\n"
"}")
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
        self.pushButton_models_hub_popular.setStyleSheet("QPushButton {\n"
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
"}\n"
"\n"
"QPushButton:checked {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #999999;\n"
"    font-weight: bold;\n"
"}")
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
        self.pushButton_models_hub_my_models.setStyleSheet("QPushButton {\n"
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
"}\n"
"\n"
"QPushButton:checked {\n"
"    background-color: qlineargradient(\n"
"        spread: pad,\n"
"        x1: 0, y1: 0, x2: 0, y2: 1,\n"
"        stop: 0 #4a4a4a,\n"
"        stop: 1 #3a3a3a\n"
"    );\n"
"    border: 2px solid #999999;\n"
"    font-weight: bold;\n"
"}")
        icon_my_models = QtGui.QIcon()
        icon_my_models.addPixmap(QtGui.QPixmap("app/gui/icons/models.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_models_hub_my_models.setIcon(icon_my_models)
        self.pushButton_models_hub_my_models.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_models_hub_my_models.setCheckable(True)
        self.pushButton_models_hub_my_models.setChecked(True)
        self.pushButton_models_hub_my_models.setAutoExclusive(True)
        self.pushButton_models_hub_my_models.setObjectName("pushButton_models_hub_my_models")
        self.horizontalLayout_8.addWidget(self.pushButton_models_hub_my_models)
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
        self.pushButton_reload_models.setStyleSheet("QPushButton {\n"
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
        self.pushButton_reload_models.setText("")
        icon_reload_models = QtGui.QIcon()
        icon_reload_models.addPixmap(QtGui.QPixmap("app/gui/icons/reload.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_reload_models.setIcon(icon_reload_models)
        self.pushButton_reload_models.setObjectName("pushButton_reload_models")
        self.horizontalLayout_8.addWidget(self.pushButton_reload_models)
        spacerItem31 = QtWidgets.QSpacerItem(612, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem31)
        
        self.lineEdit_search_model = QtWidgets.QLineEdit(parent=self.frame_models_hub_search)
        self.lineEdit_search_model.setMinimumSize(QtCore.QSize(250, 33))
        self.lineEdit_search_model.setMaximumSize(QtCore.QSize(250, 33))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(9)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.lineEdit_search_model.setFont(font)
        self.lineEdit_search_model.setStyleSheet("QLineEdit {\n"
"    background-color: #2b2b2b;\n"
"    color: #e0e0e0;\n"
"    border: 2px solid #333;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: #ffffff;\n"
"    selection-background-color: #4a90d9;\n"
"}\n"
"QLineEdit::placeholder {\n"
"    color: #888888;\n"
"}\n"
"\n"
"QLineEdit:hover {\n"
"    border: 2px solid #444;\n"
"}")
        self.lineEdit_search_model.setObjectName("lineEdit_search_model")
        self.horizontalLayout_8.addWidget(self.lineEdit_search_model)
        self.pushButton_search_model = QtWidgets.QPushButton(parent=self.frame_models_hub_search)
        self.pushButton_search_model.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_search_model.setMinimumSize(QtCore.QSize(27, 27))
        self.pushButton_search_model.setMaximumSize(QtCore.QSize(27, 27))
        font = QtGui.QFont()
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferAntialias)
        self.pushButton_search_model.setFont(font)
        self.pushButton_search_model.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_search_model.setStyleSheet("QPushButton { background-color: rgba(255, 255, 255, 0); border: none;  border-radius: 13px; }\n"
"QPushButton:hover { background-color: rgb(50, 50, 50); border-style: solid; border-radius: 13px; }\n"
"QPushButton:pressed { background-color: rgb(23, 23, 23); border-style: solid; border-radius: 13px; }\n"
"")
        icon_search = QtGui.QIcon()
        icon_search.addPixmap(QtGui.QPixmap("app/gui/icons/search.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_search_model.setIcon(icon_search)
        self.pushButton_search_model.setIconSize(QtCore.QSize(16, 16))
        self.pushButton_search_model.setFlat(True)
        self.pushButton_search_model.setObjectName("pushButton_search_model")
        self.horizontalLayout_8.addWidget(self.pushButton_search_model)
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
                color: #dcdcdc;
                outline: 0px;
                padding-left: 100px;
                padding-right: 100px;
                border: none;
            }

            QListWidget::item {
                background-color: rgb(40, 40, 40);
                margin-top: 10px;
                border: 1px solid rgb(50, 50, 50);
                border-radius: 10px;
            }

            QListWidget::item:hover {
                background-color: rgb(80, 80, 80);
                border: none;
            }

            QListWidget::item:selected {
                color: #dcdcdc;
                border: none;
            }
                                                 
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
        self.label_logotype.setMaximumSize(QtCore.QSize(185, 75))
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
        self.pushButton_turn_off_llm = QtWidgets.QPushButton(parent=self.SideBar_Left)
        self.pushButton_turn_off_llm.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_turn_off_llm.sizePolicy().hasHeightForWidth())
        self.pushButton_turn_off_llm.setSizePolicy(sizePolicy)
        self.pushButton_turn_off_llm.setMinimumSize(QtCore.QSize(0, 40))
        self.pushButton_turn_off_llm.setMaximumSize(QtCore.QSize(16777215, 40))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_turn_off_llm.setFont(font)
        self.pushButton_turn_off_llm.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_turn_off_llm.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #2f2f2f,
                    stop: 0.5 #1e1e1e,
                    stop: 1 #2f2f2f
                );
                color: rgb(227, 227, 227);
                border-radius: 5px;
                padding: 2px;
            }

            QPushButton:hover {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #343434,
                    stop: 0.5 #222222,
                    stop: 1 #343434
                );
                border: 2px solid #666666;
                border-top: 2px solid #777777;
                border-bottom: 2px solid #555555;
            }

            QPushButton:pressed {
                background-color: qlineargradient(
                    spread: pad,
                    x1: 0, y1: 0,
                    x2: 0, y2: 1,
                    stop: 0 #4a4a4a,
                    stop: 1 #3a3a3a
                );
                border: 2px solid #888888;
            }
""")
        self.pushButton_turn_off_llm.setIcon(icon5)
        self.pushButton_turn_off_llm.setIconSize(QtCore.QSize(13, 13))
        self.pushButton_turn_off_llm.setObjectName("pushButton_turn_off_llm")
        self.verticalLayout_2.addWidget(self.pushButton_turn_off_llm)
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
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setContentsMargins(10, 5, 10, 5)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_github = QtWidgets.QPushButton(parent=self.SideBar_Left)
        self.pushButton_github.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_github.setMinimumSize(QtCore.QSize(35, 35))
        self.pushButton_github.setMaximumSize(QtCore.QSize(35, 35))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_github.setFont(font)
        self.pushButton_github.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_github.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(50, 50, 50); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}")
        self.pushButton_github.setText("")
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap("app/gui/icons/github.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_github.setIcon(icon10)
        self.pushButton_github.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_github.setCheckable(False)
        self.pushButton_github.setAutoExclusive(True)
        self.pushButton_github.setObjectName("pushButton_github")
        self.horizontalLayout.addWidget(self.pushButton_github)
        self.pushButton_discord = QtWidgets.QPushButton(parent=self.SideBar_Left)
        self.pushButton_discord.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_discord.setMinimumSize(QtCore.QSize(35, 35))
        self.pushButton_discord.setMaximumSize(QtCore.QSize(35, 35))
        self.pushButton_discord.setBaseSize(QtCore.QSize(0, 0))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_discord.setFont(font)
        self.pushButton_discord.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_discord.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(50, 50, 50); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}")
        self.pushButton_discord.setText("")
        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap("app/gui/icons/discord.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_discord.setIcon(icon11)
        self.pushButton_discord.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_discord.setCheckable(False)
        self.pushButton_discord.setAutoExclusive(True)
        self.pushButton_discord.setObjectName("pushButton_discord")
        self.horizontalLayout.addWidget(self.pushButton_discord)
        self.pushButton_youtube = QtWidgets.QPushButton(parent=self.SideBar_Left)
        self.pushButton_youtube.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_youtube.setMinimumSize(QtCore.QSize(35, 35))
        self.pushButton_youtube.setMaximumSize(QtCore.QSize(35, 35))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.pushButton_youtube.setFont(font)
        self.pushButton_youtube.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_youtube.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(50, 50, 50); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}")
        self.pushButton_youtube.setText("")
        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap("app/gui/icons/youtube.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_youtube.setIcon(icon12)
        self.pushButton_youtube.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_youtube.setCheckable(False)
        self.pushButton_youtube.setAutoExclusive(True)
        self.pushButton_youtube.setObjectName("pushButton_youtube")
        self.horizontalLayout.addWidget(self.pushButton_youtube)
        self.about_btn = QtWidgets.QPushButton(parent=self.SideBar_Left)
        self.about_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.about_btn.setMinimumSize(QtCore.QSize(35, 35))
        self.about_btn.setMaximumSize(QtCore.QSize(35, 35))
        self.about_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.about_btn.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(30, 30, 30); \n"
"    border-style: solid; \n"
"    border-radius: 17px;\n"
"}")
        self.about_btn.setText("")
        icon22 = QtGui.QIcon()
        icon22.addPixmap(QtGui.QPixmap("app/gui/icons/information.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.about_btn.setIcon(icon22)
        self.about_btn.setIconSize(QtCore.QSize(23, 23))
        self.about_btn.setObjectName("about_btn")
        self.horizontalLayout.addWidget(self.about_btn)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_color = QtGui.QColor(27, 27, 27)
        self._end_color = QtGui.QColor(81, 82, 86)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._animation = QtCore.QVariantAnimation(
            startValue=self._start_color,
            endValue=self._end_color,
            valueChanged=self._on_value_changed,
            duration=300
        )
        self._update_stylesheet(self._start_color)

    def _on_value_changed(self, color):
        self._update_stylesheet(color)

    def _update_stylesheet(self, color):
        self.setStyleSheet(
            """
            QPushButton {
                background-color: %s;
                color: white;
                border: none;
                font-size: 14px;
                font-family: 'Inter Tight ExtraBold';
                border-radius: 20px;
            }
            """
            % color.name()
        )

    def enterEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Forward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Backward)
        self._animation.start()
        super().leaveEvent(event)

class PushButton_2(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_color = QtGui.QColor(67, 68, 70)
        self._end_color = QtGui.QColor(80, 83, 86)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._animation = QtCore.QVariantAnimation(
            startValue=self._start_color,
            endValue=self._end_color,
            valueChanged=self._on_value_changed,
            duration=200
        )
        self._update_stylesheet(self._start_color)

    def _on_value_changed(self, color):
        self._update_stylesheet(color)

    def _update_stylesheet(self, color):
        self.setStyleSheet(
            """
            QPushButton {
                background-color: %s;
                background-repeat: no-repeat;
	        background-position: center;
                color: white;
                border: none;
                font-size: 14px;
                font-family: 'Inter Tight ExtraBold';
                border-radius: 15px;
            }
            """
            % color.name()
        )

    def enterEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Forward)
        self._animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setDirection(QtCore.QAbstractAnimation.Direction.Backward)
        self._animation.start()
        super().leaveEvent(event)

class CharacterCard(QListWidget):
    def __init__(self, name, image_path, parent=None):
        super().__init__(parent)
        self.setFixedSize(150, 200)
        self.name = name
        self.image_path = image_path

        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setColor(QColor(0, 0, 0, 100))
        self.shadow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self.shadow_effect)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel(self)
        pixmap = QPixmap(image_path).scaled(
            130, 130,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(pixmap)
        self.image_label.setStyleSheet("border-radius: 5px; background-color: #333;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        self.name_label = QLabel(name, self)
        self.name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.name_label.setStyleSheet("""
            color: white;
            padding: 5px;
            border-radius: 5px;
            background-color: #2b2b2b;
        """)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self.animation = QPropertyAnimation(self.shadow_effect, b"offset")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: none;
                border-radius: 10px;
            }
        """)

    def enterEvent(self, event):
        self.animation.setStartValue(QPointF(0, 0))
        self.animation.setEndValue(QPointF(5, 5))
        self.animation.start()
        self.setStyleSheet("""
            QListWidget {
                background-color: #3a3a3a;
                border: none;
                border-radius: 10px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.animation.setStartValue(QPointF(5, 5))
        self.animation.setEndValue(QPointF(0, 0))
        self.animation.start()
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                border: none;
                border-radius: 10px;
            }
        """)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
