from PyQt6 import QtCore, QtGui, QtWidgets, QtOpenGLWidgets
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

class SOW_System(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Soul of Waifu System")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setupUi()

        self.draggable = False
        self.offset = None

    def setupUi(self):
        self.setObjectName("SOW_System")
        self.resize(720, 700)

        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.setWindowIcon(icon)
        self.setStyleSheet("border: none; background: transparent;")

        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setStyleSheet("background-color: rgb(27, 27, 27);")
        self.centralwidget.setObjectName("centralwidget")
        
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        
        self.mainwidget = QtWidgets.QWidget(parent=self.centralwidget)
        self.mainwidget.setMinimumSize(QtCore.QSize(500, 700))
        self.mainwidget.setMaximumSize(QtCore.QSize(500, 16777215))
        self.mainwidget.setStyleSheet("border-top: 1px solid rgb(50, 50, 55);\n"
"border-left: 1px solid rgb(50, 50, 55);\n"
"border-bottom: 1px solid rgb(50, 50, 55);")
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.mainwidget.setGraphicsEffect(shadow)
        self.mainwidget.setObjectName("mainwidget")
        
        self.gridLayout_2 = QtWidgets.QGridLayout(self.mainwidget)
        self.gridLayout_2.setContentsMargins(0, 0, 0, 10)
        self.gridLayout_2.setSpacing(0)
        self.gridLayout_2.setObjectName("gridLayout_2")
        
        # --- CHARACTER INFORMATION PANEL ---
        self.frame_character = QtWidgets.QFrame(parent=self.mainwidget)
        self.frame_character.setMinimumSize(QtCore.QSize(0, 60))
        self.frame_character.setMaximumSize(QtCore.QSize(16777215, 60))
        self.frame_character.setStyleSheet("background-color: rgb(27,27,27);\n"
"border-bottom: none;\n"
"border-right: none;\n"
"border-top: none;\n"
"\n"
"\n"
"")
        self.frame_character.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_character.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character.setObjectName("frame_character")
        
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame_character)
        self.horizontalLayout.setContentsMargins(20, 10, 20, 10)
        self.horizontalLayout.setSpacing(10)
        self.horizontalLayout.setObjectName("horizontalLayout")
        
        self.character_avatar_label = QtWidgets.QLabel(parent=self.frame_character)
        self.character_avatar_label.setMinimumSize(QtCore.QSize(40, 40))
        self.character_avatar_label.setMaximumSize(QtCore.QSize(40, 40))
        self.character_avatar_label.setStyleSheet("background: transparent;\n"
"border-radius: 30px;\n"
"border: none;")
        self.character_avatar_label.setText("")
        self.character_avatar_label.setScaledContents(True)
        self.character_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.character_avatar_label.setObjectName("character_avatar_label")
        self.horizontalLayout.addWidget(self.character_avatar_label)
        
        self.frame_character_information = QtWidgets.QFrame(parent=self.frame_character)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_character_information.sizePolicy().hasHeightForWidth())
        self.frame_character_information.setSizePolicy(sizePolicy)
        self.frame_character_information.setMinimumSize(QtCore.QSize(0, 45))
        self.frame_character_information.setStyleSheet("background: transparent; border: none;")
        self.frame_character_information.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_information.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_information.setObjectName("frame_character_information")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.frame_character_information)
        self.verticalLayout.setContentsMargins(5, 0, 5, 5)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName("verticalLayout")
        
        self.character_name_label = QtWidgets.QLabel(parent=self.frame_character_information)
        self.character_name_label.setMinimumSize(QtCore.QSize(0, 22))
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_name_label.setFont(font)
        self.character_name_label.setStyleSheet("color: rgb(210, 210, 210); border: none;")
        self.character_name_label.setTextFormat(QtCore.Qt.TextFormat.AutoText)
        self.character_name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.character_name_label.setObjectName("character_name_label")
        self.verticalLayout.addWidget(self.character_name_label, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        
        self.character_description_label = QtWidgets.QLabel(parent=self.frame_character_information)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setItalic(False)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.character_description_label.setFont(font)
        self.character_description_label.setStyleSheet("background: transparent; color: rgb(216, 216, 216)")
        self.character_description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.character_description_label.setObjectName("character_description_label")
        self.verticalLayout.addWidget(self.character_description_label, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        self.horizontalLayout.addWidget(self.frame_character_information)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        
        self.status_label = QtWidgets.QLabel(parent=self.frame_character)
        font = QtGui.QFont()
        font.setFamily("Inter Tight Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("border: none; color: rgb(210, 210, 210);")
        self.status_label.setObjectName("status_label")
        self.horizontalLayout.addWidget(self.status_label)
        
        self.pushButton_play = QtWidgets.QPushButton(parent=self.frame_character)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_play.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_play.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_play.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_play.setStyleSheet("QPushButton { \n"
"    background-color: rgba(255, 255, 255, 0); \n"
"    text-align: center;\n"
"    border: none;  \n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QPushButton:hover { \n"
"    background-color: rgb(60, 60, 60); \n"
"    border-style: solid; \n"
"    border-radius: 20px;\n"
"}\n"
"\n"
"QPushButton:pressed { \n"
"    background-color: rgb(30, 30, 30); \n"
"    border-style: solid; \n"
"    border-radius: 20px;\n"
"}")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("app/gui/icons/play.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_play.setIcon(icon)
        self.pushButton_play.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_play.setObjectName("pushButton_play")
        self.horizontalLayout.addWidget(self.pushButton_play)
        self.gridLayout_2.addWidget(self.frame_character, 1, 0, 1, 1)
        
        # --- MENUBAR ---
        self.menu_bar = QtWidgets.QFrame(parent=self.mainwidget)
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
        self.menu_bar.setStyleSheet("background-color: rgb(27,27,27);\n"
"border-bottom: none;\n"
"border-right: none;\n"
"")
        self.menu_bar.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.menu_bar.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.menu_bar.setObjectName("menu_bar")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.menu_bar)
        self.horizontalLayout_7.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        
        self.frame_title = QtWidgets.QFrame(parent=self.menu_bar)
        self.frame_title.setMinimumSize(QtCore.QSize(0, 0))
        self.frame_title.setStyleSheet("border-right: none;")
        self.frame_title.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_title.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_title.setObjectName("frame_title")
        
        self.title_label = QtWidgets.QLabel(parent=self.frame_title)
        self.title_label.setGeometry(QtCore.QRect(0, -8, 143, 41))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.title_label.sizePolicy().hasHeightForWidth())
        self.title_label.setSizePolicy(sizePolicy)
        self.title_label.setMinimumSize(QtCore.QSize(100, 0))
        font = QtGui.QFont()
        font.setFamily("Inter Tight SemiBold")
        font.setBold(False)
        font.setWeight(50)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.title_label.setFont(font)
        self.title_label.setStyleSheet("color: rgb(190, 190, 190);")
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.title_label.setIndent(5)
        self.title_label.setMargin(10)
        self.title_label.setObjectName("title_label")
        self.horizontalLayout_7.addWidget(self.frame_title)
        
        self.right_buttons = QtWidgets.QFrame(parent=self.menu_bar)
        self.right_buttons.setMinimumSize(QtCore.QSize(0, 0))
        self.right_buttons.setMaximumSize(QtCore.QSize(150, 16777215))
        self.right_buttons.setStyleSheet("border-left: none;")
        self.right_buttons.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.right_buttons.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.right_buttons.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.right_buttons.setObjectName("right_buttons")

        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.right_buttons)
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        
        self.minimize_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.minimize_btn.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("app/gui/icons/minimize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.minimize_btn.setIcon(icon1)
        self.minimize_btn.setIconSize(QtCore.QSize(12, 12))
        self.minimize_btn.setObjectName("minimize_btn")
        self.horizontalLayout_6.addWidget(self.minimize_btn)
        
        self.maximize_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.maximize_btn.setMinimumSize(QtCore.QSize(35, 25))
        self.maximize_btn.setMaximumSize(QtCore.QSize(35, 25))
        self.maximize_btn.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.maximize_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        self.maximize_btn.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("app/gui/icons/maximize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.maximize_btn.setIcon(icon2)
        self.maximize_btn.setIconSize(QtCore.QSize(11, 11))
        self.maximize_btn.setObjectName("maximize_btn")
        self.horizontalLayout_6.addWidget(self.maximize_btn)
        
        self.close_app_btn = QtWidgets.QPushButton(parent=self.right_buttons)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_app_btn.setMinimumSize(QtCore.QSize(35, 25))
        self.close_app_btn.setMaximumSize(QtCore.QSize(35, 25))
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
        self.close_app_btn.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("app/gui/icons/close.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.close_app_btn.setIcon(icon3)
        self.close_app_btn.setIconSize(QtCore.QSize(11, 11))
        self.close_app_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_app_btn.setObjectName("close_app_btn")
        self.horizontalLayout_6.addWidget(self.close_app_btn)
        self.horizontalLayout_7.addWidget(self.right_buttons, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        self.gridLayout_2.addWidget(self.menu_bar, 0, 0, 1, 1)
        
        # --- CHAT ---
        self.frame_chat = QtWidgets.QFrame(parent=self.mainwidget)
        self.frame_chat.setStyleSheet("border: none;")
        self.frame_chat.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_chat.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_chat.setObjectName("frame_chat")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frame_chat)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.scrollArea_chat = QtWidgets.QScrollArea(parent=self.frame_chat)
        self.scrollArea_chat.setMinimumSize(QtCore.QSize(500, 0))
        self.scrollArea_chat.setMaximumSize(QtCore.QSize(500, 16777215))
        
        self.scrollArea_chat.setStyleSheet("""
                QScrollArea {
                    background-color: rgb(23, 23, 23);
                    border-top: 2px solid rgb(42, 42, 42);
                    border-bottom: 2px solid rgb(42, 42, 42);
                    border-right: 2px solid rgb(42, 42, 42);
                    border-top-right-radius: 10px;
                    border-bottom-right-radius: 10px;
                    padding: 5px;
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
        """)

        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scrollAreaWidgetContents_chat = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_chat.setGeometry(QtCore.QRect(0, 0, 386, 591))
        self.scrollAreaWidgetContents_chat.setStyleSheet("border: none;")
        self.scrollAreaWidgetContents_chat.setObjectName("scrollAreaWidgetContents_chat")
        self.scrollArea_chat.setWidget(self.scrollAreaWidgetContents_chat)
        self.verticalLayout_3.addWidget(self.scrollArea_chat)
        self.gridLayout_2.addWidget(self.frame_chat, 2, 0, 1, 1)
        self.horizontalLayout_3.addWidget(self.mainwidget)
        
        # --- STACKED WIDGET ---
        self.stackedWidget_main = QtWidgets.QStackedWidget(parent=self.centralwidget)
        self.stackedWidget_main.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-top: 1px solid rgb(50, 50, 55);\n"
"border-right: 1px solid rgb(50, 50, 55);\n"
"border-bottom: 1px solid rgb(50, 50, 55);\n"
"")
        self.stackedWidget_main.setObjectName("stackedWidget_main")
        
        # --- AVATAR AND EXPRESSIONS IMAGES PAGE ---
        self.page_avatar = QtWidgets.QWidget()
        self.page_avatar.setObjectName("page_avatar")

        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.page_avatar)
        self.verticalLayout_4.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        
        self.avatar_widget = QtWidgets.QWidget(parent=self.page_avatar)
        self.avatar_widget.setMinimumSize(QtCore.QSize(300, 0))
        self.avatar_widget.setStyleSheet("border-top-right-radius: 10px;\n"
"border-top-left-radius: 10px;\n"
"border-bottom-right-radius: 10px;\n"
"border-bottom-left-radius: 10px;")
        self.avatar_widget.setObjectName("avatar_widget")
        
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.avatar_widget)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        
        self.avatar_label = QtWidgets.QLabel(parent=self.avatar_widget)
        self.avatar_label.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.avatar_label.sizePolicy().hasHeightForWidth())
        self.avatar_label.setSizePolicy(sizePolicy)
        self.avatar_label.setMinimumSize(QtCore.QSize(300, 0))
        self.avatar_label.setBaseSize(QtCore.QSize(0, 0))
        self.avatar_label.setStyleSheet("background: transparent;\n"
"border: none;")
        self.avatar_label.setText("")
        self.avatar_label.setScaledContents(False)
        self.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setWordWrap(False)
        self.avatar_label.setObjectName("avatar_label")
        
        self.verticalLayout_2.addWidget(self.avatar_label)
        self.verticalLayout_4.addWidget(self.avatar_widget)
        self.stackedWidget_main.addWidget(self.page_avatar)
        
        # --- LIVE2D PAGE ---
        self.page_live2d_model = QtWidgets.QWidget()
        self.page_live2d_model.setObjectName("page_live2d_model")

        self.verticalLayout_page_live2d = QtWidgets.QVBoxLayout(self.page_live2d_model)
        self.verticalLayout_page_live2d.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_page_live2d.setSpacing(0)
        self.verticalLayout_page_live2d.setObjectName("verticalLayout_page_live2d")
        
        self.live2d_widget = QtWidgets.QWidget(parent=self.page_live2d_model)
        self.live2d_widget.setGeometry(QtCore.QRect(10, 10, 300, 681))
        self.live2d_widget.setMinimumSize(QtCore.QSize(300, 0))
        self.live2d_widget.setStyleSheet("border-top-right-radius: 10px;\n"
"border-top-left-radius: 10px;\n"
"border-bottom-right-radius: 10px;\n"
"border-bottom-left-radius: 10px;")
        self.live2d_widget.setObjectName("live2d_widget")
        
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.live2d_widget)
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_5.setSpacing(0)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        
        self.live2d_openGL_widget = QtOpenGLWidgets.QOpenGLWidget(parent=self.live2d_widget)
        self.live2d_openGL_widget.setStyleSheet("background: transparent;\n"
"border: none;")
        self.live2d_openGL_widget.setObjectName("live2d_openGL_widget")
        
        self.verticalLayout_5.addWidget(self.live2d_openGL_widget)
        self.verticalLayout_page_live2d.addWidget(self.live2d_widget)
        self.stackedWidget_main.addWidget(self.page_live2d_model)
        
        # --- VRM PAGE ---
        self.page_vrm_model = QtWidgets.QWidget()
        self.page_vrm_model.setStyleSheet("border-image: url(:/sowInterface/bg_horizontal.jpg);\n")
        self.page_vrm_model.setObjectName("page_vrm_model")
        
        self.verticalLayout_page_vrm = QtWidgets.QVBoxLayout(self.page_vrm_model)
        self.verticalLayout_page_vrm.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout_page_vrm.setSpacing(0)
        self.verticalLayout_page_vrm.setObjectName("verticalLayout_page_vrm")

        self.vrm_widget = QtWidgets.QWidget(parent=self.page_vrm_model)
        self.vrm_widget.setGeometry(QtCore.QRect(10, 10, 300, 671))
        self.vrm_widget.setMinimumSize(QtCore.QSize(300, 0))
        self.vrm_widget.setStyleSheet("background: transparent;\n"
"border: none;")
        self.vrm_widget.setObjectName("vrm_widget")
        
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.vrm_widget)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setSpacing(0)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        
        self.stackedWidget_main.addWidget(self.page_vrm_model)
        self.verticalLayout_page_vrm.addWidget(self.vrm_widget)
        self.horizontalLayout_3.addWidget(self.stackedWidget_main)
        self.setCentralWidget(self.centralwidget)
        
        # --- SIGNALS ---
        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_maximize)
        self.close_app_btn.clicked.connect(self.close)

        self.create_size_grips()
        QtCore.QTimer.singleShot(0, self.update_size_grip_positions)

    def create_size_grips(self):
        mw = self.mainwidget

        self.top_left_grip = QtWidgets.QSizeGrip(mw)
        self.bottom_left_grip = QtWidgets.QSizeGrip(mw)
        self.top_right_grip = QtWidgets.QSizeGrip(mw)
        self.bottom_right_grip = QtWidgets.QSizeGrip(mw)

        for grip in [self.top_left_grip, self.bottom_left_grip,
                    self.top_right_grip, self.bottom_right_grip]:
            grip.resize(8, 8)
            grip.setStyleSheet("""
                QSizeGrip {
                    background-color: transparent;
                    width: 0px;
                    height: 0px;
                    margin: 0px;
                    padding: 0px;
                    border: none;
                }
            """)
            grip.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)
            grip.show()
            grip.raise_()

        self.top_left_grip.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)
        self.bottom_left_grip.setCursor(QtCore.Qt.CursorShape.SizeBDiagCursor)
        self.top_right_grip.setCursor(QtCore.Qt.CursorShape.SizeBDiagCursor)
        self.bottom_right_grip.setCursor(QtCore.Qt.CursorShape.SizeFDiagCursor)

    def update_size_grip_positions(self):
        mw = self.mainwidget
        w, h = mw.width(), mw.height()
        size = 8

        self.top_left_grip.move(0, 0)
        self.bottom_left_grip.move(0, h - size)
        self.top_right_grip.move(w - size, 0)
        self.bottom_right_grip.move(w - size, h - size)

    def resizeEvent(self, event):
        """
        Handles the resize event and delegates it to Interface Signals.
        """
        super().resizeEvent(event)
        self.update_size_grip_positions()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if event.pos().y() <= self.frame_title.height():
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
            self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
            self.maximize_btn.setIcon(icon_maximize)
            self.showNormal()
        else:
            icon_maximize = QtGui.QIcon()
            icon_maximize.addPixmap(QtGui.QPixmap("app/gui/icons/maximize_minimize.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
            self.maximize_btn.setIcon(icon_maximize)
            self.showMaximized()

    def closeEvent(self, event: QtGui.QCloseEvent):
        app = QtWidgets.QApplication.instance()
        if hasattr(app, 'main_window'):
            main_window = app.main_window
            main_window.setVisible(True)
            main_window.raise_()
            main_window.activateWindow()
        event.accept()
