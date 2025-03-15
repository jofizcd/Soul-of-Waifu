from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_MainWindow(QtWidgets.QMainWindow):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1296, 795)
        MainWindow.setMinimumSize(QtCore.QSize(1296, 807))
        MainWindow.setMaximumSize(QtCore.QSize(1296, 807))
        MainWindow.setBaseSize(QtCore.QSize(1064, 774))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/sowInterface/logotype.ico"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet("")
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setStyleSheet("#centralwidget {    \n"
"    background-color: rgb(9,9,9);\n"
"}\n"
"\n"
"")
        self.centralwidget.setObjectName("centralwidget")
        self.SideBar_Left = QtWidgets.QWidget(parent=self.centralwidget)
        self.SideBar_Left.setGeometry(QtCore.QRect(5, 4, 221, 751))
        self.SideBar_Left.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.SideBar_Left.setStyleSheet("#SideBar_Left {\n"
"    background: qlineargradient(spread: pad, x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 rgba(35, 35, 35, 255),stop: 1 rgba(50, 50, 50, 255));\n"
"    border-radius: 10px;\n"
"    border: 1px solid rgb(42, 42, 42);\n"
"}\n"
"\n"
"QPushButton {\n"
"    color: rgb(243, 243, 243);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(24,24,24);\n"
"    border-radius: 10px;\n"
"    border: 1px solid rgb(39, 44, 54);\n"
"    padding: px;\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(9,9,9);\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(9,9,9);\n"
"    color: rgb(255, 255, 255);\n"
"}"
"\n"
"QPushButton:checked {\n"
"	background-color: rgb(9,9,9);\n"
"	color: rgb(255, 255, 255);\n"
"	border-radius: 10px;\n"
"	border: 1px solid rgb(39, 44, 54);\n"
"	padding: px;\n"
"}\n"
)
        self.SideBar_Left.setObjectName("SideBar_Left")
        self.label_logotype = QtWidgets.QLabel(parent=self.SideBar_Left)
        self.label_logotype.setGeometry(QtCore.QRect(0, 0, 221, 131))
        self.label_logotype.setMinimumSize(QtCore.QSize(0, 0))
        self.label_logotype.setMaximumSize(QtCore.QSize(1000, 1000))
        self.label_logotype.setToolTip("")
        self.label_logotype.setStyleSheet("padding: 10px;\n"
"")
        self.label_logotype.setText("")
        self.label_logotype.setPixmap(QtGui.QPixmap(":/sowInterface/logotitle.png"))
        self.label_logotype.setScaledContents(True)
        self.label_logotype.setObjectName("label_logotype")
        self.separator_left_bar = QtWidgets.QFrame(parent=self.SideBar_Left)
        self.separator_left_bar.setGeometry(QtCore.QRect(10, 580, 203, 16))
        self.separator_left_bar.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_left_bar.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_left_bar.setObjectName("separator_left_bar")
        self.layoutWidget = QtWidgets.QWidget(parent=self.SideBar_Left)
        self.layoutWidget.setGeometry(QtCore.QRect(9, 166, 211, 191))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton_main = QtWidgets.QPushButton(parent=self.layoutWidget)
        self.pushButton_main.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_main.sizePolicy().hasHeightForWidth())
        self.pushButton_main.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        font.setStrikeOut(False)
        font.setKerning(True)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.pushButton_main.setFont(font)
        self.pushButton_main.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_main.setMouseTracking(False)
        self.pushButton_main.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.pushButton_main.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_main.setAutoFillBackground(False)
        self.pushButton_main.setStyleSheet("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/sowInterface/home.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_main.setIcon(icon1)
        self.pushButton_main.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_main.setCheckable(True)
        self.pushButton_main.setChecked(True)
        self.pushButton_main.setAutoExclusive(True)
        self.pushButton_main.setAutoDefault(False)
        self.pushButton_main.setDefault(False)
        self.pushButton_main.setFlat(False)
        self.pushButton_main.setObjectName("pushButton_main")
        self.verticalLayout.addWidget(self.pushButton_main)
        self.pushButton_create_character = QtWidgets.QPushButton(parent=self.layoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_create_character.sizePolicy().hasHeightForWidth())
        self.pushButton_create_character.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_create_character.setFont(font)
        self.pushButton_create_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character.setStyleSheet("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/sowInterface/addCharacter.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_create_character.setIcon(icon2)
        self.pushButton_create_character.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_create_character.setCheckable(True)
        self.pushButton_create_character.setChecked(False)
        self.pushButton_create_character.setAutoExclusive(True)
        self.pushButton_create_character.setObjectName("pushButton_create_character")
        self.verticalLayout.addWidget(self.pushButton_create_character)
        self.pushButton_characters_gateway = QtWidgets.QPushButton(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_characters_gateway.setFont(font)
        self.pushButton_characters_gateway.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_characters_gateway.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_characters_gateway.setStyleSheet("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap(":/sowInterface/gateway.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_characters_gateway.setIcon(icon3)
        self.pushButton_characters_gateway.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_characters_gateway.setCheckable(True)
        self.pushButton_characters_gateway.setChecked(False)
        self.pushButton_characters_gateway.setAutoExclusive(True)
        self.pushButton_characters_gateway.setObjectName("pushButton_characters_gateway")
        self.verticalLayout.addWidget(self.pushButton_characters_gateway)
        self.pushButton_options = QtWidgets.QPushButton(parent=self.layoutWidget)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_options.setFont(font)
        self.pushButton_options.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_options.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_options.setStyleSheet("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap(":/sowInterface/options.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_options.setIcon(icon4)
        self.pushButton_options.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_options.setCheckable(True)
        self.pushButton_options.setAutoExclusive(True)
        self.pushButton_options.setObjectName("pushButton_options")
        self.verticalLayout.addWidget(self.pushButton_options)
        self.layoutWidget1 = QtWidgets.QWidget(parent=self.SideBar_Left)
        self.layoutWidget1.setGeometry(QtCore.QRect(9, 602, 201, 141))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_2.setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetDefaultConstraint)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 10)
        self.verticalLayout_2.setSpacing(15)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pushButton_youtube = QtWidgets.QPushButton(parent=self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_youtube.setFont(font)
        self.pushButton_youtube.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_youtube.setStyleSheet("")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap(":/sowInterface/youtube.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_youtube.setIcon(icon5)
        self.pushButton_youtube.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_youtube.setCheckable(False)
        self.pushButton_youtube.setAutoExclusive(True)
        self.pushButton_youtube.setObjectName("pushButton_youtube")
        self.verticalLayout_2.addWidget(self.pushButton_youtube)
        self.pushButton_discord = QtWidgets.QPushButton(parent=self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_discord.setFont(font)
        self.pushButton_discord.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_discord.setStyleSheet("")
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap(":/sowInterface/discord.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_discord.setIcon(icon6)
        self.pushButton_discord.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_discord.setCheckable(False)
        self.pushButton_discord.setAutoExclusive(True)
        self.pushButton_discord.setObjectName("pushButton_discord")
        self.verticalLayout_2.addWidget(self.pushButton_discord)
        self.pushButton_github = QtWidgets.QPushButton(parent=self.layoutWidget1)
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_github.setFont(font)
        self.pushButton_github.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_github.setStyleSheet("")
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap(":/sowInterface/github.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_github.setIcon(icon7)
        self.pushButton_github.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_github.setCheckable(False)
        self.pushButton_github.setAutoExclusive(True)
        self.pushButton_github.setObjectName("pushButton_github")
        self.verticalLayout_2.addWidget(self.pushButton_github)
        self.SideBar_Right = QtWidgets.QWidget(parent=self.centralwidget)
        self.SideBar_Right.setGeometry(QtCore.QRect(230, 4, 1061, 751))
        self.SideBar_Right.setStyleSheet("#SideBar_Right {\n"
"    background-color: rgb(27,27,27);\n"
"    border-radius: 10px;\n"
"    border: 1px solid rgb(34, 34, 34);\n"
"}")
        self.SideBar_Right.setObjectName("SideBar_Right")
        self.stackedWidget = QtWidgets.QStackedWidget(parent=self.SideBar_Right)
        self.stackedWidget.setGeometry(QtCore.QRect(9, 9, 1043, 733))
        self.stackedWidget.setStyleSheet("")
        self.stackedWidget.setObjectName("stackedWidget")
        self.main_no_characters_page = QtWidgets.QWidget()
        self.main_no_characters_page.setStyleSheet("background-color: rgb(27,27,27);")
        self.main_no_characters_page.setObjectName("main_no_characters_page")
        self.main_no_characters_advice_label = QtWidgets.QLabel(parent=self.main_no_characters_page)
        self.main_no_characters_advice_label.setGeometry(QtCore.QRect(0, 270, 1041, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(14)
        font.setBold(False)
        font.setWeight(50)
        self.main_no_characters_advice_label.setFont(font)
        self.main_no_characters_advice_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.main_no_characters_advice_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_no_characters_advice_label.setObjectName("main_no_characters_advice_label")
        self.pushButton_create_character_2 = QtWidgets.QPushButton(parent=self.main_no_characters_page)
        self.pushButton_create_character_2.setGeometry(QtCore.QRect(430, 370, 181, 41))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_create_character_2.sizePolicy().hasHeightForWidth())
        self.pushButton_create_character_2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_create_character_2.setFont(font)
        self.pushButton_create_character_2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_2.setStyleSheet("QPushButton {\n"
"    background-color: rgb(51,51,51);\n"
"    color: rgb(255, 255, 255);\n"
"    border: 1px solid rgb(39, 44, 54);\n"
"    border-radius: 10px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(39, 44, 54);\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(39, 44, 54);\n"
"    color: rgb(255, 255, 255);\n"
"}")
        self.pushButton_create_character_2.setIcon(icon2)
        self.pushButton_create_character_2.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_create_character_2.setCheckable(False)
        self.pushButton_create_character_2.setChecked(False)
        self.pushButton_create_character_2.setAutoExclusive(True)
        self.pushButton_create_character_2.setObjectName("pushButton_create_character_2")
        self.main_no_characters_description_label = QtWidgets.QLabel(parent=self.main_no_characters_page)
        self.main_no_characters_description_label.setGeometry(QtCore.QRect(0, 100, 1041, 51))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.main_no_characters_description_label.setFont(font)
        self.main_no_characters_description_label.setAcceptDrops(False)
        self.main_no_characters_description_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.main_no_characters_description_label.setScaledContents(False)
        self.main_no_characters_description_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.main_no_characters_description_label.setWordWrap(True)
        self.main_no_characters_description_label.setObjectName("main_no_characters_description_label")
        self.welcome_label = QtWidgets.QLabel(parent=self.main_no_characters_page)
        self.welcome_label.setGeometry(QtCore.QRect(40, 30, 640, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.welcome_label.setFont(font)
        self.welcome_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.welcome_label.setObjectName("welcome_label")
        self.frame_main_navigation = QtWidgets.QFrame(parent=self.main_no_characters_page)
        self.frame_main_navigation.setGeometry(QtCore.QRect(780, 10, 275, 41))
        self.frame_main_navigation.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-radius: 10px;")
        self.frame_main_navigation.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_main_navigation.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_main_navigation.setObjectName("frame_main_navigation")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.frame_main_navigation)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        spacerItem = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem)
        self.main_navigation_label = QtWidgets.QLabel(parent=self.frame_main_navigation)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.main_navigation_label.setFont(font)
        self.main_navigation_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.main_navigation_label.setObjectName("main_navigation_label")
        self.horizontalLayout_8.addWidget(self.main_navigation_label)
        spacerItem1 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem1)
        self.welcome_separator = QtWidgets.QFrame(parent=self.main_no_characters_page)
        self.welcome_separator.setGeometry(QtCore.QRect(20, 24, 261, 31))
        self.welcome_separator.setStyleSheet("border: 3px solid rgb(39, 44, 54);\n"
"border-radius: 15px;\n"
"\n"
"")
        self.welcome_separator.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.welcome_separator.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.welcome_separator.setObjectName("welcome_separator")
        self.welcome_separator.raise_()
        self.main_no_characters_advice_label.raise_()
        self.pushButton_create_character_2.raise_()
        self.main_no_characters_description_label.raise_()
        self.welcome_label.raise_()
        self.frame_main_navigation.raise_()
        self.stackedWidget.addWidget(self.main_no_characters_page)
        self.main_characters_page = QtWidgets.QWidget()
        self.main_characters_page.setStyleSheet("background-color: rgb(27,27,27);")
        self.main_characters_page.setObjectName("main_characters_page")
        self.frame_main_navigation_2 = QtWidgets.QFrame(parent=self.main_characters_page)
        self.frame_main_navigation_2.setGeometry(QtCore.QRect(780, 10, 275, 41))
        self.frame_main_navigation_2.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-radius: 10px;")
        self.frame_main_navigation_2.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_main_navigation_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_main_navigation_2.setObjectName("frame_main_navigation_2")
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout(self.frame_main_navigation_2)
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        spacerItem2 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem2)
        self.main_navigation_label_2 = QtWidgets.QLabel(parent=self.frame_main_navigation_2)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(17)
        font.setBold(True)
        font.setWeight(75)
        self.main_navigation_label_2.setFont(font)
        self.main_navigation_label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.main_navigation_label_2.setObjectName("main_navigation_label_2")
        self.horizontalLayout_12.addWidget(self.main_navigation_label_2)
        spacerItem3 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem3)
        self.welcome_label_2 = QtWidgets.QLabel(parent=self.main_characters_page)
        self.welcome_label_2.setGeometry(QtCore.QRect(100, 30, 640, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.welcome_label_2.setFont(font)
        self.welcome_label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.welcome_label_2.setObjectName("welcome_label_2")
        self.ListWidget_character_list = QtWidgets.QListWidget(parent=self.main_characters_page)
        self.ListWidget_character_list.setGeometry(QtCore.QRect(10, 120, 1021, 601))
        self.ListWidget_character_list.setStyleSheet("background-color: rgb(27,27,27);\n"
"border: none;")
        self.ListWidget_character_list.setObjectName("ListWidget_character_list")
        self.user_avatar_label = QtWidgets.QLabel(parent=self.main_characters_page)
        self.user_avatar_label.setGeometry(QtCore.QRect(20, 10, 51, 51))
        self.user_avatar_label.setMinimumSize(QtCore.QSize(51, 51))
        self.user_avatar_label.setMaximumSize(QtCore.QSize(51, 51))
        self.user_avatar_label.setStyleSheet("")
        self.user_avatar_label.setText("")
        self.user_avatar_label.setPixmap(QtGui.QPixmap(":/sowInterface/person.png"))
        self.user_avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.user_avatar_label.setObjectName("user_avatar_label")
        self.welcome_separator_2 = QtWidgets.QFrame(parent=self.main_characters_page)
        self.welcome_separator_2.setGeometry(QtCore.QRect(80, 24, 261, 31))
        self.welcome_separator_2.setStyleSheet("border: 3px solid rgb(39, 44, 54);\n"
"border-radius: 15px;\n"
"\n"
"")
        self.welcome_separator_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.welcome_separator_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.welcome_separator_2.setObjectName("welcome_separator_2")
        self.welcome_separator_2.raise_()
        self.frame_main_navigation_2.raise_()
        self.user_avatar_label.raise_()
        self.ListWidget_character_list.raise_()
        self.welcome_label_2.raise_()
        self.stackedWidget.addWidget(self.main_characters_page)
        self.create_character_page = QtWidgets.QWidget()
        self.create_character_page.setObjectName("create_character_page")
        self.add_character_title_label = QtWidgets.QLabel(parent=self.create_character_page)
        self.add_character_title_label.setGeometry(QtCore.QRect(0, 200, 1041, 101))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(16)
        font.setBold(False)
        font.setWeight(50)
        self.add_character_title_label.setFont(font)
        self.add_character_title_label.setStyleSheet("color: rgb(255, 255, 255);\n"
"")
        self.add_character_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.add_character_title_label.setObjectName("add_character_title_label")
        self.add_character_id_label = QtWidgets.QLabel(parent=self.create_character_page)
        self.add_character_id_label.setGeometry(QtCore.QRect(130, 310, 101, 91))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.add_character_id_label.setFont(font)
        self.add_character_id_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.add_character_id_label.setMidLineWidth(0)
        self.add_character_id_label.setObjectName("add_character_id_label")
        self.character_id_lineEdit = QtWidgets.QLineEdit(parent=self.create_character_page)
        self.character_id_lineEdit.setGeometry(QtCore.QRect(230, 340, 651, 31))
        self.character_id_lineEdit.setStyleSheet("QLineEdit {\n"
"    color: rgb(255, 255, 255);\n"
"    padding-left: 5px;    \n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    background-color: rgb(51,51,51);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.character_id_lineEdit.setObjectName("character_id_lineEdit")
        self.pushButton_add_character = QtWidgets.QPushButton(parent=self.create_character_page)
        self.pushButton_add_character.setGeometry(QtCore.QRect(800, 380, 81, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_add_character.setFont(font)
        self.pushButton_add_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_add_character.setStyleSheet("QPushButton {\n"
"background-color: rgb(51,51,51);\n"
"color: rgb(255, 255, 255);\n"
"border: 1px solid rgb(39, 44, 54);\n"
"border-radius: 10px;\n"
"background-repeat: no-repeat;\n"
"background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(39, 44, 54);\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(39, 44, 54);\n"
"    color: rgb(255, 255, 255);\n"
"}")
        self.pushButton_add_character.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_add_character.setAutoExclusive(True)
        self.pushButton_add_character.setObjectName("pushButton_add_character")
        self.frame_create_character = QtWidgets.QFrame(parent=self.create_character_page)
        self.frame_create_character.setGeometry(QtCore.QRect(780, 10, 275, 41))
        self.frame_create_character.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-radius: 7px;")
        self.frame_create_character.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_create_character.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_create_character.setObjectName("frame_create_character")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout(self.frame_create_character)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        spacerItem4 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem4)
        self.create_character_label = QtWidgets.QLabel(parent=self.frame_create_character)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.create_character_label.setFont(font)
        self.create_character_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.create_character_label.setObjectName("create_character_label")
        self.horizontalLayout_13.addWidget(self.create_character_label)
        spacerItem5 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem5)
        self.stackedWidget.addWidget(self.create_character_page)
        self.create_character_page_2 = QtWidgets.QWidget()
        self.create_character_page_2.setStyleSheet("")
        self.create_character_page_2.setObjectName("create_character_page_2")
        self.frame_create_character_2 = QtWidgets.QFrame(parent=self.create_character_page_2)
        self.frame_create_character_2.setGeometry(QtCore.QRect(780, 10, 275, 41))
        self.frame_create_character_2.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-radius: 7px;")
        self.frame_create_character_2.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_create_character_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_create_character_2.setObjectName("frame_create_character_2")
        self.horizontalLayout_15 = QtWidgets.QHBoxLayout(self.frame_create_character_2)
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        spacerItem6 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_15.addItem(spacerItem6)
        self.create_character_label_2 = QtWidgets.QLabel(parent=self.frame_create_character_2)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.create_character_label_2.setFont(font)
        self.create_character_label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.create_character_label_2.setObjectName("create_character_label_2")
        self.horizontalLayout_15.addWidget(self.create_character_label_2)
        spacerItem7 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_15.addItem(spacerItem7)
        self.scrollArea_character_building = QtWidgets.QScrollArea(parent=self.create_character_page_2)
        self.scrollArea_character_building.setGeometry(QtCore.QRect(0, 50, 1041, 681))
        self.scrollArea_character_building.setStyleSheet("QScrollArea {\n"
"    border: none;\n"
"}\n"
"\n"
"QScrollBar:vertical {\n"
"    background-color: rgb(39, 44, 54);\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"    border-radius: 5px;"
"}\n"
"\n"
"QScrollBar::handle:vertical {\n"
"    background-color: rgb(50, 55, 65);\n"
"    min-height: 20px;\n"
"    border-radius: 5px;\n"
"}\n"
"\n"
"QScrollBar::handle:vertical:hover {\n"
"    background-color: rgb(50, 55, 65);\n"
"}\n"
"\n"
"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {\n"
"                border: none;\n"
"                background: none;\n"
"            }\n"
"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"                background: none;\n"
"            }\n"
"")
        self.scrollArea_character_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scrollArea_character_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_character_building.setWidgetResizable(True)
        self.scrollArea_character_building.setObjectName("scrollArea_character_building")
        self.scrollAreaWidgetContents_character_building = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_building.setGeometry(QtCore.QRect(0, 0, 1031, 1138))
        self.scrollAreaWidgetContents_character_building.setStyleSheet("background-color: rgb(27,27,27);\n"
"")
        self.scrollAreaWidgetContents_character_building.setObjectName("scrollAreaWidgetContents_character_building")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents_character_building)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.frame_character_building = QtWidgets.QFrame(parent=self.scrollAreaWidgetContents_character_building)
        self.frame_character_building.setMinimumSize(QtCore.QSize(0, 1120))
        self.frame_character_building.setStyleSheet("background-color: rgb(27,27,27); border: none;")
        self.frame_character_building.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_character_building.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_character_building.setObjectName("frame_character_building")
        self.addcharacter_title_Label_2 = QtWidgets.QLabel(parent=self.frame_character_building)
        self.addcharacter_title_Label_2.setGeometry(QtCore.QRect(1280, 350, 10000, 2019))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.addcharacter_title_Label_2.setFont(font)
        self.addcharacter_title_Label_2.setStyleSheet("color: rgb(243, 243, 243);\n"
"")
        self.addcharacter_title_Label_2.setObjectName("addcharacter_title_Label_2")
        self.addcharacter_title_Label_3 = QtWidgets.QLabel(parent=self.frame_character_building)
        self.addcharacter_title_Label_3.setGeometry(QtCore.QRect(1290, 350, 10000, 2516))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.addcharacter_title_Label_3.setFont(font)
        self.addcharacter_title_Label_3.setStyleSheet("color: rgb(255, 255, 255);\n"
"")
        self.addcharacter_title_Label_3.setObjectName("addcharacter_title_Label_3")
        self.addcharacter_title_Label_4 = QtWidgets.QLabel(parent=self.frame_character_building)
        self.addcharacter_title_Label_4.setGeometry(QtCore.QRect(1300, 350, 10000, 3348))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.addcharacter_title_Label_4.setFont(font)
        self.addcharacter_title_Label_4.setStyleSheet("color: rgb(255, 255, 255);\n"
"")
        self.addcharacter_title_Label_4.setObjectName("addcharacter_title_Label_4")
        self.addcharacter_title_Label_5 = QtWidgets.QLabel(parent=self.frame_character_building)
        self.addcharacter_title_Label_5.setGeometry(QtCore.QRect(1290, 360, 10000, 5010))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        font.setBold(False)
        font.setWeight(50)
        self.addcharacter_title_Label_5.setFont(font)
        self.addcharacter_title_Label_5.setStyleSheet("color: rgb(255, 255, 255);\n"
"")
        self.addcharacter_title_Label_5.setObjectName("addcharacter_title_Label_5")
        self.separator_create_character = QtWidgets.QFrame(parent=self.frame_character_building)
        self.separator_create_character.setGeometry(QtCore.QRect(20, 20, 121, 41))
        self.separator_create_character.setStyleSheet("border: 3px solid rgb(39, 44, 54);\n"
"border-radius: 15px;\n"
"\n"
"")
        self.separator_create_character.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_create_character.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_create_character.setObjectName("separator_create_character")
        self.pushButton_import_character_card = QtWidgets.QPushButton(parent=self.frame_character_building)
        self.pushButton_import_character_card.setGeometry(QtCore.QRect(840, 20, 161, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Light")
        font.setPointSize(11)
        self.pushButton_import_character_card.setFont(font)
        self.pushButton_import_character_card.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_import_character_card.setStyleSheet("QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    border-radius: 10px;\n"
"    border-color: rgb(255, 255, 255);\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    background: transparent;\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(54, 54, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(39, 44, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap(":/sowInterface/import.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_card.setIcon(icon8)
        self.pushButton_import_character_card.setObjectName("pushButton_import_character_card")
        self.pushButton_import_character_image = QtWidgets.QPushButton(parent=self.frame_character_building)
        self.pushButton_import_character_image.setGeometry(QtCore.QRect(210, 80, 91, 91))
        font = QtGui.QFont()
        font.setFamily("Muli Light")
        font.setPointSize(10)
        self.pushButton_import_character_image.setFont(font)
        self.pushButton_import_character_image.setStyleSheet("QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    border-radius: 10px;\n"
"    border-color: rgb(255, 255, 255);\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    background: transparent;\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(54, 54, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.pushButton_import_character_image.setText("")
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap(":/sowInterface/addImage.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_import_character_image.setIcon(icon9)
        self.pushButton_import_character_image.setIconSize(QtCore.QSize(32, 32))
        self.pushButton_import_character_image.setObjectName("pushButton_import_character_image")
        self.character_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.character_building_label.setGeometry(QtCore.QRect(50, 30, 211, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.character_building_label.setFont(font)
        self.character_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.character_building_label.setObjectName("character_building_label")
        self.character_image_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.character_image_building_label.setGeometry(QtCore.QRect(50, 80, 151, 51))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        self.character_image_building_label.setFont(font)
        self.character_image_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.character_image_building_label.setObjectName("character_image_building_label")
        self.character_name_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.character_name_building_label.setGeometry(QtCore.QRect(50, 190, 151, 51))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        self.character_name_building_label.setFont(font)
        self.character_name_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.character_name_building_label.setObjectName("character_name_building_label")
        self.lineEdit_character_name_building = QtWidgets.QLineEdit(parent=self.frame_character_building)
        self.lineEdit_character_name_building.setGeometry(QtCore.QRect(210, 200, 291, 31))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_character_name_building.setFont(font)
        self.lineEdit_character_name_building.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.lineEdit_character_name_building.setInputMask("")
        self.lineEdit_character_name_building.setText("")
        self.lineEdit_character_name_building.setObjectName("lineEdit_character_name_building")
        self.character_description_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.character_description_building_label.setGeometry(QtCore.QRect(50, 260, 181, 51))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        self.character_description_building_label.setFont(font)
        self.character_description_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.character_description_building_label.setObjectName("character_description_building_label")
        self.textEdit_character_description_building = QtWidgets.QTextEdit(parent=self.frame_character_building)
        self.textEdit_character_description_building.setGeometry(QtCore.QRect(250, 250, 741, 221))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.textEdit_character_description_building.setFont(font)
        self.textEdit_character_description_building.setStyleSheet("QTextEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"\n"
"\n"
"")
        self.textEdit_character_description_building.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.textEdit_character_description_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_description_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_description_building.setObjectName("textEdit_character_description_building")
        self.character_personality_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.character_personality_building_label.setGeometry(QtCore.QRect(50, 510, 181, 51))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        self.character_personality_building_label.setFont(font)
        self.character_personality_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.character_personality_building_label.setObjectName("character_personality_building_label")
        self.textEdit_character_personality_building = QtWidgets.QTextEdit(parent=self.frame_character_building)
        self.textEdit_character_personality_building.setGeometry(QtCore.QRect(250, 500, 741, 301))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.textEdit_character_personality_building.setFont(font)
        self.textEdit_character_personality_building.setStyleSheet("QTextEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"\n"
"\n"
"")
        self.textEdit_character_personality_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_personality_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_character_personality_building.setObjectName("textEdit_character_personality_building")
        self.first_message_building_label = QtWidgets.QLabel(parent=self.frame_character_building)
        self.first_message_building_label.setGeometry(QtCore.QRect(110, 840, 201, 51))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setPointSize(12)
        self.first_message_building_label.setFont(font)
        self.first_message_building_label.setStyleSheet("color: rgb(250, 250, 250)")
        self.first_message_building_label.setObjectName("first_message_building_label")
        self.textEdit_first_message_building = QtWidgets.QTextEdit(parent=self.frame_character_building)
        self.textEdit_first_message_building.setGeometry(QtCore.QRect(250, 830, 741, 181))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.textEdit_first_message_building.setFont(font)
        self.textEdit_first_message_building.setStyleSheet("QTextEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QTextEdit:vertical {\n"
"    width: 10px;\n"
"    margin: 15px 0 15px 0;\n"
"}\n"
"\n"
"QTextEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"\n"
"")
        self.textEdit_first_message_building.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_first_message_building.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textEdit_first_message_building.setObjectName("textEdit_first_message_building")
        self.pushButton_create_character_3 = QtWidgets.QPushButton(parent=self.frame_character_building)
        self.pushButton_create_character_3.setGeometry(QtCore.QRect(790, 1040, 191, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.pushButton_create_character_3.setFont(font)
        self.pushButton_create_character_3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_create_character_3.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_create_character_3.setAutoFillBackground(False)
        self.pushButton_create_character_3.setStyleSheet("QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    border-radius: 10px;\n"
"    border-color: rgb(255, 255, 255);\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    background: transparent;\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(54, 54, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(39, 44, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap(":/sowInterface/addCharacter2.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_create_character_3.setIcon(icon10)
        self.pushButton_create_character_3.setIconSize(QtCore.QSize(19, 19))
        self.pushButton_create_character_3.setObjectName("pushButton_create_character_3")
        self.verticalLayout_5.addWidget(self.frame_character_building)
        self.scrollArea_character_building.setWidget(self.scrollAreaWidgetContents_character_building)
        self.scrollArea_character_building.raise_()
        self.frame_create_character_2.raise_()
        self.stackedWidget.addWidget(self.create_character_page_2)
        self.charactersgateway_page = QtWidgets.QWidget()
        self.charactersgateway_page.setObjectName("charactersgateway_page")
        self.frame_characters_gateway = QtWidgets.QFrame(parent=self.charactersgateway_page)
        self.frame_characters_gateway.setGeometry(QtCore.QRect(760, 10, 275, 41))
        self.frame_characters_gateway.setStyleSheet("background-color: rgb(27, 27, 27);\n"
"border-radius: 7px;")
        self.frame_characters_gateway.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_characters_gateway.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_characters_gateway.setObjectName("frame_characters_gateway")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.frame_characters_gateway)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem8 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem8)
        self.characters_gateway_label = QtWidgets.QLabel(parent=self.frame_characters_gateway)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.characters_gateway_label.setFont(font)
        self.characters_gateway_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.characters_gateway_label.setObjectName("characters_gateway_label")
        self.horizontalLayout_4.addWidget(self.characters_gateway_label)
        spacerItem9 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem9)
        self.lineEdit_search_character = QtWidgets.QLineEdit(parent=self.charactersgateway_page)
        self.lineEdit_search_character.setGeometry(QtCore.QRect(317, 50, 371, 33))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_search_character.setFont(font)
        self.lineEdit_search_character.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.lineEdit_search_character.setObjectName("lineEdit_search_character")
        self.pushButton_search_character = QtWidgets.QPushButton(parent=self.charactersgateway_page)
        self.pushButton_search_character.setGeometry(QtCore.QRect(690, 50, 31, 31))
        self.pushButton_search_character.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_search_character.setStyleSheet("QPushButton {\n"
"    border-radius: 14px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(150, 150, 150);\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(39, 44, 54);\n"
"    color: rgb(255, 255, 255);\n"
"}")
        self.pushButton_search_character.setText("")
        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap(":/sowInterface/loupe.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_search_character.setIcon(icon11)
        self.pushButton_search_character.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_search_character.setFlat(True)
        self.pushButton_search_character.setObjectName("pushButton_search_character")
        self.tabWidget_characters_gateway = QtWidgets.QTabWidget(parent=self.charactersgateway_page)
        self.tabWidget_characters_gateway.setGeometry(QtCore.QRect(0, 80, 1040, 657))
        self.tabWidget_characters_gateway.setStyleSheet("QTabWidget::pane {\n"
"    border-top: 1px solid #333;\n"
"    background-color: rgb(27,27,27);\n"
"    border-radius: 5px;\n"
"}\n"
"            \n"
"QTabWidget::tab-bar {\n"
"    left: 5px;\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #333;\n"
"    font-size: 14px;\n"
"    font-weight: bold;\n"
"    color: #eee;\n"
"    padding: 10px;\n"
"    border-top-left-radius: 5px;\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom: 2px solid #333;\n"
"    min-width: 100px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    font-size: 15px;\n"
"    background-color: #444;\n"
"    border-bottom-color: #555;\n"
"}\n"
"\n"
"QTabBar::tab:hover {\n"
"    background-color: #444;\n"
"}\n"
"           \n"
"QTabBar::tab:disabled {\n"
"    background-color: #333;\n"
"    color: #888;\n"
"}")
        self.tabWidget_characters_gateway.setObjectName("tabWidget_characters_gateway")
        self.tab_character_ai = QtWidgets.QWidget()
        self.tab_character_ai.setObjectName("tab_character_ai")
        self.stackedWidget_character_ai = QtWidgets.QStackedWidget(parent=self.tab_character_ai)
        self.stackedWidget_character_ai.setGeometry(QtCore.QRect(0, 10, 1039, 605))
        self.stackedWidget_character_ai.setObjectName("stackedWidget_character_ai")
        self.character_ai_page = QtWidgets.QWidget()
        self.character_ai_page.setObjectName("character_ai_page")
        self.scrollArea_character_ai_page = QtWidgets.QScrollArea(parent=self.character_ai_page)
        self.scrollArea_character_ai_page.setGeometry(QtCore.QRect(10, 0, 1020, 595))
        self.scrollArea_character_ai_page.setStyleSheet("")
        self.scrollArea_character_ai_page.setWidgetResizable(True)
        self.scrollArea_character_ai_page.setObjectName("scrollArea_character_ai_page")
        self.scrollAreaWidgetContents_character_ai = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_ai.setGeometry(QtCore.QRect(0, 0, 1018, 593))
        self.scrollAreaWidgetContents_character_ai.setObjectName("scrollAreaWidgetContents_character_ai")
        self.scrollArea_character_ai_page.setWidget(self.scrollAreaWidgetContents_character_ai)
        self.stackedWidget_character_ai.addWidget(self.character_ai_page)
        self.character_ai_search_page = QtWidgets.QWidget()
        self.character_ai_search_page.setObjectName("character_ai_search_page")
        self.scrollArea_character_ai_search_page = QtWidgets.QScrollArea(parent=self.character_ai_search_page)
        self.scrollArea_character_ai_search_page.setGeometry(QtCore.QRect(10, 0, 1020, 595))
        self.scrollArea_character_ai_search_page.setStyleSheet("")
        self.scrollArea_character_ai_search_page.setWidgetResizable(True)
        self.scrollArea_character_ai_search_page.setObjectName("scrollArea_character_ai_search_page")
        self.scrollAreaWidgetContents_character_ai_search = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_ai_search.setGeometry(QtCore.QRect(0, 0, 1018, 593))
        self.scrollAreaWidgetContents_character_ai_search.setObjectName("scrollAreaWidgetContents_character_ai_search")
        self.scrollArea_character_ai_search_page.setWidget(self.scrollAreaWidgetContents_character_ai_search)
        self.stackedWidget_character_ai.addWidget(self.character_ai_search_page)
        self.tabWidget_characters_gateway.addTab(self.tab_character_ai, "")
        self.tab_character_cards = QtWidgets.QWidget()
        self.tab_character_cards.setObjectName("tab_character_cards")
        self.stackedWidget_character_card_gateway = QtWidgets.QStackedWidget(parent=self.tab_character_cards)
        self.stackedWidget_character_card_gateway.setGeometry(QtCore.QRect(0, 10, 1039, 605))
        self.stackedWidget_character_card_gateway.setObjectName("stackedWidget_character_card_gateway")
        self.character_card_page = QtWidgets.QWidget()
        self.character_card_page.setObjectName("character_card_page")
        self.scrollArea_character_card = QtWidgets.QScrollArea(parent=self.character_card_page)
        self.scrollArea_character_card.setGeometry(QtCore.QRect(10, 0, 1020, 595))
        self.scrollArea_character_card.setWidgetResizable(True)
        self.scrollArea_character_card.setObjectName("scrollArea_character_card")
        self.scrollAreaWidgetContents_character_card = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_card.setGeometry(QtCore.QRect(0, 0, 1018, 593))
        self.scrollAreaWidgetContents_character_card.setObjectName("scrollAreaWidgetContents_character_card")
        self.scrollArea_character_card.setWidget(self.scrollAreaWidgetContents_character_card)
        self.stackedWidget_character_card_gateway.addWidget(self.character_card_page)
        self.character_card_search_page = QtWidgets.QWidget()
        self.character_card_search_page.setObjectName("character_card_search_page")
        self.scrollArea_character_card_search = QtWidgets.QScrollArea(parent=self.character_card_search_page)
        self.scrollArea_character_card_search.setGeometry(QtCore.QRect(10, 0, 1020, 595))
        self.scrollArea_character_card_search.setWidgetResizable(True)
        self.scrollArea_character_card_search.setObjectName("scrollArea_character_card_search")
        self.scrollAreaWidgetContents_character_card_search = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_character_card_search.setGeometry(QtCore.QRect(0, 0, 1018, 593))
        self.scrollAreaWidgetContents_character_card_search.setObjectName("scrollAreaWidgetContents_character_card_search")
        self.scrollArea_character_card_search.setWidget(self.scrollAreaWidgetContents_character_card_search)
        self.stackedWidget_character_card_gateway.addWidget(self.character_card_search_page)
        self.tabWidget_characters_gateway.addTab(self.tab_character_cards, "")
        self.stackedWidget.addWidget(self.charactersgateway_page)
        self.options_page = QtWidgets.QWidget()
        self.options_page.setObjectName("options_page")
        self.frame_options = QtWidgets.QFrame(parent=self.options_page)
        self.frame_options.setGeometry(QtCore.QRect(820, 10, 275, 41))
        self.frame_options.setStyleSheet("""background-color: rgb(27, 27, 27); border-radius: 7px;""")
        self.frame_options.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_options.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_options.setObjectName("frame_options")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.frame_options)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        spacerItem10 = QtWidgets.QSpacerItem(302, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem10)
        self.options_label = QtWidgets.QLabel(parent=self.frame_options)
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.options_label.setFont(font)
        self.options_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.options_label.setObjectName("options_label")
        self.horizontalLayout_6.addWidget(self.options_label)
        spacerItem11 = QtWidgets.QSpacerItem(292, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem11)
        self.tabWidget_options = QtWidgets.QTabWidget(parent=self.options_page)
        self.tabWidget_options.setGeometry(QtCore.QRect(0, 50, 1041, 700))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.tabWidget_options.setFont(font)
        self.tabWidget_options.setStyleSheet("QTabWidget::pane {\n"
"    border-top: 1px solid #333;\n"
"    background-color: rgb(27,27,27);\n"
"    border-radius: 5px;\n"
"}\n"
"            \n"
"QTabWidget::tab-bar {\n"
"    left: 5px;\n"
"}\n"
"\n"
"QTabBar::tab {\n"
"    background-color: #333;\n"
"    font-size: 14px;\n"
"    font-weight: bold;\n"
"    color: #eee;\n"
"    padding: 10px;\n"
"    border-top-left-radius: 5px;\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom: 2px solid #333;\n"
"    min-width: 100px;\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    background-color: #444;\n"
"    border-bottom-color: #555;\n"
"    font-size: 15px;\n"
"}\n"
"\n"
"QTabBar::tab:hover {\n"
"    background-color: #444;\n"
"}\n"
"           \n"
"QTabBar::tab:disabled {\n"
"    background-color: #333;\n"
"    color: #888;\n"
"}")
        self.tabWidget_options.setObjectName("tabWidget_options")
        self.configuration_tab = QtWidgets.QWidget()
        self.configuration_tab.setStyleSheet("")
        self.configuration_tab.setObjectName("configuration_tab")
        self.conversation_method_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_title_label.setGeometry(QtCore.QRect(10, 10, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.conversation_method_title_label.setFont(font)
        self.conversation_method_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.conversation_method_title_label.setObjectName("conversation_method_title_label")
        self.conversation_method_token_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_token_title_label.setGeometry(QtCore.QRect(10, 108, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.conversation_method_token_title_label.setFont(font)
        self.conversation_method_token_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.conversation_method_token_title_label.setObjectName("conversation_method_token_title_label")
        self.lineEdit_api_token_options = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_api_token_options.setGeometry(QtCore.QRect(130, 100, 361, 33))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(8)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_api_token_options.setFont(font)
        self.lineEdit_api_token_options.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.lineEdit_api_token_options.setObjectName("lineEdit_api_token_options")
        self.separator_options = QtWidgets.QFrame(parent=self.configuration_tab)
        self.separator_options.setGeometry(QtCore.QRect(10, 350, 1021, 20))
        self.separator_options.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options.setObjectName("separator_options")
        self.sow_system_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.sow_system_title_label.setGeometry(QtCore.QRect(10, 370, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.sow_system_title_label.setFont(font)
        self.sow_system_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.sow_system_title_label.setObjectName("sow_system_title_label")
        self.checkBox_enable_sow_system = QtWidgets.QCheckBox(parent=self.configuration_tab)
        self.checkBox_enable_sow_system.setGeometry(QtCore.QRect(10, 413, 211, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.checkBox_enable_sow_system.setFont(font)
        self.checkBox_enable_sow_system.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_sow_system.setStyleSheet("QCheckBox{\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"QCheckBox::indicator {\n"
"    border: 3px solid rgb(52, 59, 72);\n"
"    width: 15px;\n"
"    height: 15px;\n"
"    border-radius: 10px;\n"
"    background-color: #333;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 3px solid rgb(58, 66, 81);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 3px solid rgb(52, 59, 72);    \n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 15;\n"
"    height: 15;\n"
"}\n"
"\n"
"")
        self.checkBox_enable_sow_system.setObjectName("checkBox_enable_sow_system")
        self.conversation_method_options_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.conversation_method_options_label.setGeometry(QtCore.QRect(10, 60, 141, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.conversation_method_options_label.setFont(font)
        self.conversation_method_options_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.conversation_method_options_label.setObjectName("conversation_method_options_label")
        self.comboBox_conversation_method = QtWidgets.QComboBox(parent=self.configuration_tab)
        self.comboBox_conversation_method.setGeometry(QtCore.QRect(160, 53, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_conversation_method.setFont(font)
        self.comboBox_conversation_method.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_conversation_method.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_conversation_method.setObjectName("comboBox_conversation_method")
        self.comboBox_conversation_method.addItem("")
        self.comboBox_conversation_method.addItem("")
        self.comboBox_conversation_method.addItem("")
        self.choose_live2d_mode_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.choose_live2d_mode_label.setGeometry(QtCore.QRect(10, 460, 201, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_live2d_mode_label.setFont(font)
        self.choose_live2d_mode_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_live2d_mode_label.setObjectName("choose_live2d_mode_label")
        self.comboBox_live2d_mode = QtWidgets.QComboBox(parent=self.configuration_tab)
        self.comboBox_live2d_mode.setGeometry(QtCore.QRect(210, 453, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_live2d_mode.setFont(font)
        self.comboBox_live2d_mode.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_live2d_mode.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_live2d_mode.setObjectName("comboBox_live2d_mode")
        self.comboBox_live2d_mode.addItem("")
        self.comboBox_live2d_mode.addItem("")
        self.pushButton_choose_user_avatar = QtWidgets.QPushButton(parent=self.configuration_tab)
        self.pushButton_choose_user_avatar.setGeometry(QtCore.QRect(145, 295, 41, 41))
        self.pushButton_choose_user_avatar.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_choose_user_avatar.setStyleSheet("QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    border-radius: 10px;\n"
"    border-color: rgb(255, 255, 255);\n"
"    border: 2px solid rgb(39, 44, 54);\n"
"    background: transparent;\n"
"    font-size: 11px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(54, 54, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(39, 44, 54);\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.pushButton_choose_user_avatar.setText("")
        self.pushButton_choose_user_avatar.setIcon(icon9)
        self.pushButton_choose_user_avatar.setObjectName("pushButton_choose_user_avatar")
        self.choose_your_avatar_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.choose_your_avatar_label.setGeometry(QtCore.QRect(10, 300, 131, 31))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_your_avatar_label.setFont(font)
        self.choose_your_avatar_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_your_avatar_label.setObjectName("choose_your_avatar_label")
        self.separator_options_4 = QtWidgets.QFrame(parent=self.configuration_tab)
        self.separator_options_4.setGeometry(QtCore.QRect(10, 140, 1021, 20))
        self.separator_options_4.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_4.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_4.setObjectName("separator_options_4")
        self.speech_to_text_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.speech_to_text_title_label.setGeometry(QtCore.QRect(10, 160, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.speech_to_text_title_label.setFont(font)
        self.speech_to_text_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.speech_to_text_title_label.setObjectName("speech_to_text_title_label")
        self.speech_to_text_method_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.speech_to_text_method_label.setGeometry(QtCore.QRect(10, 210, 171, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.speech_to_text_method_label.setFont(font)
        self.speech_to_text_method_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.speech_to_text_method_label.setObjectName("speech_to_text_method_label")
        self.comboBox_speech_to_text_method = QtWidgets.QComboBox(parent=self.configuration_tab)
        self.comboBox_speech_to_text_method.setGeometry(QtCore.QRect(170, 203, 181, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_speech_to_text_method.setFont(font)
        self.comboBox_speech_to_text_method.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_speech_to_text_method.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_speech_to_text_method.setObjectName("comboBox_speech_to_text_method")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.comboBox_speech_to_text_method.addItem("")
        self.choose_your_name_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.choose_your_name_label.setGeometry(QtCore.QRect(210, 300, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_your_name_label.setFont(font)
        self.choose_your_name_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_your_name_label.setObjectName("choose_your_name_label")
        self.choose_your_description_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.choose_your_description_label.setGeometry(QtCore.QRect(540, 300, 151, 31))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_your_description_label.setFont(font)
        self.choose_your_description_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_your_description_label.setObjectName("choose_your_description_label")
        self.lineEdit_user_description_options = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_user_description_options.setGeometry(QtCore.QRect(690, 300, 311, 33))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(8)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_user_description_options.setFont(font)
        self.lineEdit_user_description_options.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.lineEdit_user_description_options.setObjectName("lineEdit_user_description_options")
        self.user_building_title_label = QtWidgets.QLabel(parent=self.configuration_tab)
        self.user_building_title_label.setGeometry(QtCore.QRect(10, 260, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.user_building_title_label.setFont(font)
        self.user_building_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.user_building_title_label.setObjectName("user_building_title_label")
        self.separator_options_5 = QtWidgets.QFrame(parent=self.configuration_tab)
        self.separator_options_5.setGeometry(QtCore.QRect(10, 240, 1021, 20))
        self.separator_options_5.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_5.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_5.setObjectName("separator_options_5")
        self.lineEdit_user_name_options = QtWidgets.QLineEdit(parent=self.configuration_tab)
        self.lineEdit_user_name_options.setGeometry(QtCore.QRect(330, 300, 181, 33))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(8)
        font.setBold(True)
        font.setWeight(75)
        self.lineEdit_user_name_options.setFont(font)
        self.lineEdit_user_name_options.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid rgb(28, 56, 85);\n"
"}")
        self.lineEdit_user_name_options.setObjectName("lineEdit_user_name_options")
        self.tabWidget_options.addTab(self.configuration_tab, "")
        self.system_tab = QtWidgets.QWidget()
        self.system_tab.setStyleSheet("")
        self.system_tab.setObjectName("system_tab")
        self.language_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.language_title_label.setGeometry(QtCore.QRect(10, 10, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.language_title_label.setFont(font)
        self.language_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.language_title_label.setObjectName("language_title_label")
        self.comboBox_program_language = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_program_language.setGeometry(QtCore.QRect(140, 50, 121, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_program_language.setFont(font)
        self.comboBox_program_language.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_program_language.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_program_language.setObjectName("comboBox_program_language")
        self.comboBox_program_language.addItem("")
        self.comboBox_program_language.addItem("")
        self.separator_options_2 = QtWidgets.QFrame(parent=self.system_tab)
        self.separator_options_2.setGeometry(QtCore.QRect(10, 100, 1021, 20))
        self.separator_options_2.setStyleSheet("")
        self.separator_options_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_2.setObjectName("separator_options_2")
        self.devices_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.devices_title_label.setGeometry(QtCore.QRect(10, 120, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.devices_title_label.setFont(font)
        self.devices_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.devices_title_label.setObjectName("devices_title_label")
        self.input_device_label = QtWidgets.QLabel(parent=self.system_tab)
        self.input_device_label.setGeometry(QtCore.QRect(10, 170, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.input_device_label.setFont(font)
        self.input_device_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.input_device_label.setObjectName("input_device_label")
        self.comboBox_input_devices = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_input_devices.setGeometry(QtCore.QRect(100, 163, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_input_devices.setFont(font)
        self.comboBox_input_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_input_devices.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_input_devices.setObjectName("comboBox_input_devices")
        self.output_device_label = QtWidgets.QLabel(parent=self.system_tab)
        self.output_device_label.setGeometry(QtCore.QRect(10, 220, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.output_device_label.setFont(font)
        self.output_device_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.output_device_label.setObjectName("output_device_label")
        self.comboBox_output_devices = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_output_devices.setGeometry(QtCore.QRect(110, 213, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_output_devices.setFont(font)
        self.comboBox_output_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_output_devices.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_output_devices.setObjectName("comboBox_output_devices")
        self.program_language_label = QtWidgets.QLabel(parent=self.system_tab)
        self.program_language_label.setGeometry(QtCore.QRect(10, 57, 131, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.program_language_label.setFont(font)
        self.program_language_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.program_language_label.setObjectName("program_language_label")
        self.translator_title_label = QtWidgets.QLabel(parent=self.system_tab)
        self.translator_title_label.setGeometry(QtCore.QRect(10, 280, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.translator_title_label.setFont(font)
        self.translator_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.translator_title_label.setObjectName("translator_title_label")
        self.separator_options_3 = QtWidgets.QFrame(parent=self.system_tab)
        self.separator_options_3.setGeometry(QtCore.QRect(10, 260, 1021, 20))
        self.separator_options_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.separator_options_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.separator_options_3.setObjectName("separator_options_3")
        self.choose_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.choose_translator_label.setGeometry(QtCore.QRect(10, 330, 121, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_translator_label.setFont(font)
        self.choose_translator_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_translator_label.setObjectName("choose_translator_label")
        self.comboBox_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_translator.setGeometry(QtCore.QRect(130, 323, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_translator.setFont(font)
        self.comboBox_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_translator.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_translator.setObjectName("comboBox_translator")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.comboBox_translator.addItem("")
        self.target_language_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.target_language_translator_label.setGeometry(QtCore.QRect(10, 380, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.target_language_translator_label.setFont(font)
        self.target_language_translator_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.target_language_translator_label.setObjectName("target_language_translator_label")
        self.comboBox_target_language_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_target_language_translator.setGeometry(QtCore.QRect(130, 373, 141, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_target_language_translator.setFont(font)
        self.comboBox_target_language_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_target_language_translator.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_target_language_translator.setObjectName("comboBox_target_language_translator")
        self.comboBox_target_language_translator.addItem("")
        self.mode_translator_label = QtWidgets.QLabel(parent=self.system_tab)
        self.mode_translator_label.setGeometry(QtCore.QRect(10, 430, 51, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.mode_translator_label.setFont(font)
        self.mode_translator_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.mode_translator_label.setObjectName("mode_translator_label")
        self.comboBox_mode_translator = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_mode_translator.setGeometry(QtCore.QRect(60, 423, 161, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_mode_translator.setFont(font)
        self.comboBox_mode_translator.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_mode_translator.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_mode_translator.setObjectName("comboBox_mode_translator")
        self.comboBox_mode_translator.addItem("")
        self.comboBox_mode_translator.addItem("")
        self.comboBox_mode_translator.addItem("")
        self.tabWidget_options.addTab(self.system_tab, "")
        self.llm_tab = QtWidgets.QWidget()
        self.llm_tab.setObjectName("llm_tab")
        self.comboBox_llms = QtWidgets.QComboBox(parent=self.llm_tab)
        self.comboBox_llms.setGeometry(QtCore.QRect(100, 53, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_llms.setFont(font)
        self.comboBox_llms.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_llms.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_llms.setObjectName("comboBox_llms")
        self.llm_options_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_options_label.setGeometry(QtCore.QRect(10, 60, 81, 16))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.llm_options_label.setFont(font)
        self.llm_options_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.llm_options_label.setObjectName("llm_options_label")
        self.llm_title_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_title_label.setGeometry(QtCore.QRect(10, 10, 301, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.llm_title_label.setFont(font)
        self.llm_title_label.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.llm_title_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.llm_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.llm_title_label.setObjectName("llm_title_label")
        self.choose_llm_device_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.choose_llm_device_label.setGeometry(QtCore.QRect(10, 115, 101, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.choose_llm_device_label.setFont(font)
        self.choose_llm_device_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.choose_llm_device_label.setObjectName("choose_llm_device_label")
        self.comboBox_llm_devices = QtWidgets.QComboBox(parent=self.llm_tab)
        self.comboBox_llm_devices.setGeometry(QtCore.QRect(120, 110, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Muli ExtraBold")
        font.setBold(True)
        font.setWeight(75)
        self.comboBox_llm_devices.setFont(font)
        self.comboBox_llm_devices.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.comboBox_llm_devices.setStyleSheet("QComboBox {\n"
"    background-color: #353535;\n"
"    color: #ffffff;\n"
"    border-radius: 5px;\n"
"    border: 2px solid rgb(33, 37, 43);\n"
"    padding: 5px;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QComboBox:hover {\n"
"    border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"\n"
"QComboBox QAbstractItemView {\n"
"    color: #ffffff;\n"
"    background-color: rgb(33, 37, 43);\n"
"    padding: 10px;\n"
"    selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 18px;\n"
"    border-left: 1px solid  rgb(39, 44, 54);\n"
"    background-color:  rgb(39, 44, 54);\n"
"    border-top-right-radius: 5px;\n"
"    border-bottom-right-radius: 5px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}\n"
"\n"
"QComboBox::down-arrow:hover {\n"
"    width: 12px;\n"
"    height: 12px;\n"
"    image: url(:/sowInterface/arrowDown.png);\n"
"}")
        self.comboBox_llm_devices.setObjectName("comboBox_llm_devices")
        self.comboBox_llm_devices.addItem("")
        self.comboBox_llm_devices.addItem("")
        self.gpu_layers_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.gpu_layers_label.setGeometry(QtCore.QRect(10, 170, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.gpu_layers_label.setFont(font)
        self.gpu_layers_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.gpu_layers_label.setObjectName("gpu_layers_label")
        self.checkBox_enable_mlock = QtWidgets.QCheckBox(parent=self.llm_tab)
        self.checkBox_enable_mlock.setGeometry(QtCore.QRect(10, 230, 131, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.checkBox_enable_mlock.setFont(font)
        self.checkBox_enable_mlock.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.checkBox_enable_mlock.setStyleSheet("QCheckBox{\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"QCheckBox::indicator {\n"
"    border: 3px solid rgb(52, 59, 72);\n"
"    width: 15px;\n"
"    height: 15px;\n"
"    border-radius: 10px;\n"
"    background-color: #333;\n"
"}\n"
"\n"
"QCheckBox::indicator:hover {\n"
"    border: 3px solid rgb(58, 66, 81);\n"
"}\n"
"\n"
"QCheckBox::indicator:checked {\n"
"    border: 3px solid rgb(52, 59, 72);    \n"
"    image: url(:/sowInterface/checked.png);\n"
"    width: 15;\n"
"    height: 15;\n"
"}\n"
"\n"
"")
        self.checkBox_enable_mlock.setObjectName("checkBox_enable_mlock")
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.context_size_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.context_size_label.setGeometry(QtCore.QRect(10, 291, 91, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.context_size_label.setFont(font)
        self.context_size_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.context_size_label.setObjectName("context_size_label")
        self.line = QtWidgets.QFrame(parent=self.llm_tab)
        self.line.setGeometry(QtCore.QRect(10, 350, 1031, 20))
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.llm_title_label_2 = QtWidgets.QLabel(parent=self.llm_tab)
        self.llm_title_label_2.setGeometry(QtCore.QRect(10, 380, 401, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.llm_title_label_2.setFont(font)
        self.llm_title_label_2.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.llm_title_label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.llm_title_label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.llm_title_label_2.setObjectName("llm_title_label_2")
        self.reapet_penalty_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.reapet_penalty_label.setGeometry(QtCore.QRect(10, 500, 111, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.reapet_penalty_label.setFont(font)
        self.reapet_penalty_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.reapet_penalty_label.setObjectName("reapet_penalty_label")
        self.temperature_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.temperature_label.setGeometry(QtCore.QRect(10, 420, 91, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.temperature_label.setFont(font)
        self.temperature_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.temperature_label.setObjectName("temperature_label")
        self.temperature_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.temperature_horizontalSlider.setGeometry(QtCore.QRect(100, 420, 160, 22))
        self.temperature_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.temperature_horizontalSlider.setMinimum(0)
        self.temperature_horizontalSlider.setMaximum(20)
        self.temperature_horizontalSlider.setSingleStep(1)
        self.temperature_horizontalSlider.setProperty("value", 10)
        self.temperature_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.temperature_horizontalSlider.setObjectName("temperature_horizontalSlider")
        self.temperature_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.temperature_value_label.setGeometry(QtCore.QRect(270, 420, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.temperature_value_label.setFont(font)
        self.temperature_value_label.setStyleSheet("color: white;")
        self.temperature_value_label.setObjectName("temperature_value_label")
        self.top_p_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.top_p_label.setGeometry(QtCore.QRect(10, 460, 51, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.top_p_label.setFont(font)
        self.top_p_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.top_p_label.setObjectName("top_p_label")
        self.top_p_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.top_p_horizontalSlider.setGeometry(QtCore.QRect(60, 460, 160, 22))
        self.top_p_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.top_p_horizontalSlider.setMinimum(0)
        self.top_p_horizontalSlider.setMaximum(10)
        self.top_p_horizontalSlider.setSingleStep(1)
        self.top_p_horizontalSlider.setPageStep(0)
        self.top_p_horizontalSlider.setProperty("value", 10)
        self.top_p_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.top_p_horizontalSlider.setObjectName("top_p_horizontalSlider")
        self.top_p_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.top_p_value_label.setGeometry(QtCore.QRect(230, 460, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.top_p_value_label.setFont(font)
        self.top_p_value_label.setStyleSheet("color: white;")
        self.top_p_value_label.setObjectName("top_p_value_label")
        self.gpu_layers_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.gpu_layers_horizontalSlider.setGeometry(QtCore.QRect(100, 170, 160, 22))
        self.gpu_layers_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.gpu_layers_horizontalSlider.setMinimum(1)
        self.gpu_layers_horizontalSlider.setMaximum(100)
        self.gpu_layers_horizontalSlider.setSingleStep(1)
        self.gpu_layers_horizontalSlider.setProperty("value", 1)
        self.gpu_layers_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.gpu_layers_horizontalSlider.setObjectName("gpu_layers_horizontalSlider")
        self.context_size_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.context_size_horizontalSlider.setGeometry(QtCore.QRect(100, 290, 160, 22))
        self.context_size_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.context_size_horizontalSlider.setMinimum(512)
        self.context_size_horizontalSlider.setMaximum(8192)
        self.context_size_horizontalSlider.setSingleStep(64)
        self.context_size_horizontalSlider.setPageStep(0)
        self.context_size_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.context_size_horizontalSlider.setObjectName("context_size_horizontalSlider")
        self.repeat_penalty_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.repeat_penalty_horizontalSlider.setGeometry(QtCore.QRect(117, 500, 160, 22))
        self.repeat_penalty_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.repeat_penalty_horizontalSlider.setMinimum(10)
        self.repeat_penalty_horizontalSlider.setMaximum(20)
        self.repeat_penalty_horizontalSlider.setSingleStep(1)
        self.repeat_penalty_horizontalSlider.setPageStep(0)
        self.repeat_penalty_horizontalSlider.setProperty("value", 10)
        self.repeat_penalty_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.repeat_penalty_horizontalSlider.setObjectName("repeat_penalty_horizontalSlider")
        self.max_tokens_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.max_tokens_label.setGeometry(QtCore.QRect(13, 540, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.max_tokens_label.setFont(font)
        self.max_tokens_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.max_tokens_label.setObjectName("max_tokens_label")
        self.max_tokens_horizontalSlider = QtWidgets.QSlider(parent=self.llm_tab)
        self.max_tokens_horizontalSlider.setGeometry(QtCore.QRect(100, 540, 160, 22))
        self.max_tokens_horizontalSlider.setStyleSheet("QSlider::groove:horizontal {\n"
"background-color: #ddd;\n"
"height: 8px;\n"
"border-radius: 4px;\n"
"}\n"
"QSlider::handle:horizontal {\n"
"background-color: #353535;\n"
"width: 20px;\n"
"height: 20px;\n"
"margin: -6px 0; /* Смещение ручки */\n"
"border-radius: 10px;\n"
"}\n"
"QSlider::sub-page:horizontal {\n"
"background-color: rgb(33, 37, 43);\n"
"border-radius: 4px;\n"
"}")
        self.max_tokens_horizontalSlider.setMinimum(16)
        self.max_tokens_horizontalSlider.setMaximum(2048)
        self.max_tokens_horizontalSlider.setSingleStep(12)
        self.max_tokens_horizontalSlider.setPageStep(0)
        self.max_tokens_horizontalSlider.setProperty("value", 16)
        self.max_tokens_horizontalSlider.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.max_tokens_horizontalSlider.setObjectName("max_tokens_horizontalSlider")
        self.repeat_penalty_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.repeat_penalty_value_label.setGeometry(QtCore.QRect(290, 500, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.repeat_penalty_value_label.setFont(font)
        self.repeat_penalty_value_label.setStyleSheet("color: white;")
        self.repeat_penalty_value_label.setObjectName("repeat_penalty_value_label")
        self.max_tokens_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.max_tokens_value_label.setGeometry(QtCore.QRect(270, 540, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.max_tokens_value_label.setFont(font)
        self.max_tokens_value_label.setStyleSheet("color: white;")
        self.max_tokens_value_label.setObjectName("max_tokens_value_label")
        self.context_size_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.context_size_value_label.setGeometry(QtCore.QRect(270, 290, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.context_size_value_label.setFont(font)
        self.context_size_value_label.setStyleSheet("color: white;")
        self.context_size_value_label.setObjectName("context_size_value_label")
        self.gpu_layers_value_label = QtWidgets.QLabel(parent=self.llm_tab)
        self.gpu_layers_value_label.setGeometry(QtCore.QRect(270, 170, 81, 21))
        font = QtGui.QFont()
        font.setFamily("Muli SemiBold")
        font.setBold(True)
        font.setWeight(75)
        self.gpu_layers_value_label.setFont(font)
        self.gpu_layers_value_label.setStyleSheet("color: white;")
        self.gpu_layers_value_label.setObjectName("gpu_layers_value_label")
        self.tabWidget_options.addTab(self.llm_tab, "")
        self.stackedWidget.addWidget(self.options_page)
        self.chat_page = QtWidgets.QWidget()
        self.chat_page.setObjectName("chat_page")
        self.top = QtWidgets.QFrame(parent=self.chat_page)
        self.top.setGeometry(QtCore.QRect(0, 0, 1040, 60))
        self.top.setMinimumSize(QtCore.QSize(0, 60))
        self.top.setMaximumSize(QtCore.QSize(16777215, 60))
        self.top.setStyleSheet("#top {\n"
"    background-color: rgb(39, 44, 54);\n"
"    border-radius: 10px;\n"
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
"}\n"
"\n"
"\n"
"")
        self.top.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.top.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.top.setObjectName("top")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.top)
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
        font.setFamily("Muli ExtraBold")
        font.setPointSize(12)
        font.setBold(True)
        font.setItalic(False)
        font.setWeight(75)
        self.character_name_chat.setFont(font)
        self.character_name_chat.setStyleSheet("color: rgb(255, 255, 255);")
        self.character_name_chat.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.character_name_chat.setObjectName("character_name_chat")
        self.verticalLayout_4.addWidget(self.character_name_chat)
        self.character_description_chat = QtWidgets.QLabel(parent=self.user_information_frame)
        font = QtGui.QFont()
        font.setFamily("Muli Light")
        self.character_description_chat.setFont(font)
        self.character_description_chat.setStyleSheet("background: transparent;\n"
"color: rgb(216, 216, 216)")
        self.character_description_chat.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.character_description_chat.setObjectName("character_description_chat")
        self.verticalLayout_4.addWidget(self.character_description_chat)
        self.horizontalLayout_2.addWidget(self.user_information_frame)
        spacerItem12 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem12)
        self.pushButton_more = QtWidgets.QPushButton(parent=self.top)
        self.pushButton_more.setMinimumSize(QtCore.QSize(40, 40))
        self.pushButton_more.setMaximumSize(QtCore.QSize(40, 40))
        self.pushButton_more.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_more.setStyleSheet("QPushButton {\n"
"    background-color: rgb(39, 44, 54);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(69, 77, 94);\n"
"}\n"
"\n"
"QPushButton:pressed {\n"
"    background-color: rgb(50, 60, 70);\n"
"}")
        self.pushButton_more.setText("")
        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap(":/sowInterface/more.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_more.setIcon(icon12)
        self.pushButton_more.setObjectName("pushButton_more")
        self.horizontalLayout_2.addWidget(self.pushButton_more)
        self.scrollArea_chat = QtWidgets.QScrollArea(parent=self.chat_page)
        self.scrollArea_chat.setGeometry(QtCore.QRect(0, 70, 1041, 611))
        self.scrollArea_chat.setStyleSheet("""
    QScrollArea {
        background-color: rgb(27,27,27);
        border: none;
        padding: 5px;
        border-radius: 10px;
    }
    QScrollBar:vertical {
        width: 0px;
        background: transparent;
    }
    QScrollBar::handle:vertical {
        background: transparent;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        background: none;  /* Убираем фон для всех элементов скроллбара */
        border: none;  /* Убираем границы */
    }
""")
        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scrollAreaWidgetContents_messages = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_messages.setGeometry(QtCore.QRect(0, 0, 1029, 599))
        self.scrollAreaWidgetContents_messages.setObjectName("scrollAreaWidgetContents_messages")
        self.scrollArea_chat.setWidget(self.scrollAreaWidgetContents_messages)
        self.frame_send_message = QtWidgets.QFrame(parent=self.chat_page)
        self.frame_send_message.setGeometry(QtCore.QRect(180, 690, 681, 41))
        self.frame_send_message.setStyleSheet("#frame_send_message { \n"
"    background-color: rgb(47, 48, 50);\n"
"    border-radius: 20px;\n"
"}\n"
"\n"
"#frame_send_message QPushButton {\n"
"    background-color: rgb(76, 77, 80);\n"
"    border-radius: 15px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"#frame_send_message QPushButton:hover {\n"
"    background-color: rgb(81, 82, 86);\n"
"}\n"
"#frame_send_message QPushButton:pressed {\n"
"    background-color: rgb(16, 17, 18);\n"
"}\n"
"#textEdit_write_user_message {\n"
"    background-color: transparent;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(39, 62, 135);\n"
"    border: none;\n"
"    padding-top: 7px;\n"
"    padding-left: 15px;\n"
"    padding-right: 15px;\n"
"    background-repeat: none;\n"
"    background-position: left center;\n"
"    font: 10pt \"Segoe UI\";\n"
"    color: rgb(255, 255, 255);\n"
"}\n"
"#textEdit_write_user_message:focus {\n"
"    color: rgb(165, 165, 165);\n"
"}")
        self.frame_send_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_send_message.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_send_message.setObjectName("frame_send_message")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.frame_send_message)
        self.horizontalLayout_3.setContentsMargins(5, 0, 5, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.pushButton_call = QtWidgets.QPushButton(parent=self.frame_send_message)
        self.pushButton_call.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_call.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_call.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_call.setText("")
        icon13 = QtGui.QIcon()
        icon13.addPixmap(QtGui.QPixmap("resources/icons/sowsystem.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_call.setIcon(icon13)
        self.pushButton_call.setIconSize(QtCore.QSize(50, 38))
        self.pushButton_call.setObjectName("pushButton_call")
        self.horizontalLayout_3.addWidget(self.pushButton_call)
        self.textEdit_write_user_message = QtWidgets.QTextEdit(parent=self.frame_send_message)
        self.textEdit_write_user_message.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.textEdit_write_user_message.setInputMethodHints(QtCore.Qt.InputMethodHint.ImhMultiLine)
        self.textEdit_write_user_message.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.textEdit_write_user_message.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.textEdit_write_user_message.setAutoFormatting(QtWidgets.QTextEdit.AutoFormattingFlag.AutoNone)
        self.textEdit_write_user_message.setObjectName("textEdit_write_user_message")
        self.horizontalLayout_3.addWidget(self.textEdit_write_user_message)
        self.pushButton_send_message = QtWidgets.QPushButton(parent=self.frame_send_message)
        self.pushButton_send_message.setMinimumSize(QtCore.QSize(30, 30))
        self.pushButton_send_message.setMaximumSize(QtCore.QSize(30, 30))
        self.pushButton_send_message.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_send_message.setText("")
        icon14 = QtGui.QIcon()
        icon14.addPixmap(QtGui.QPixmap(":/sowInterface/send.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_send_message.setIcon(icon14)
        self.pushButton_send_message.setObjectName("pushButton_send_message")
        self.horizontalLayout_3.addWidget(self.pushButton_send_message)
        self.stackedWidget.addWidget(self.chat_page)
        self.bottom_bar = QtWidgets.QFrame(parent=self.centralwidget)
        self.bottom_bar.setGeometry(QtCore.QRect(5, 756, 1280, 16))
        self.bottom_bar.setMinimumSize(QtCore.QSize(1280, 16))
        self.bottom_bar.setMaximumSize(QtCore.QSize(1275, 26))
        self.bottom_bar.setStyleSheet("background-color: rgb(9,9,9);")
        self.bottom_bar.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottom_bar.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottom_bar.setObjectName("bottom_bar")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.bottom_bar)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.creator_label = QtWidgets.QLabel(parent=self.bottom_bar)
        self.creator_label.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creator_label.setFont(font)
        self.creator_label.setStyleSheet("padding-left: 5px;\n"
"color: rgb(190, 190, 190);")
        self.creator_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creator_label.setObjectName("creator_label")
        self.horizontalLayout_7.addWidget(self.creator_label)
        self.version_label = QtWidgets.QLabel(parent=self.bottom_bar)
        font = QtGui.QFont()
        font.setFamily("Muli Medium")
        self.version_label.setFont(font)
        self.version_label.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_label.setObjectName("version_label")
        self.horizontalLayout_7.addWidget(self.version_label)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1296, 21))
        self.menubar.setObjectName("menubar")
        self.menu_sow = QtWidgets.QMenu(parent=self.menubar)
        self.menu_sow.setObjectName("menu_sow")
        self.menu_help = QtWidgets.QMenu(parent=self.menubar)
        self.menu_help.setObjectName("menu_help")
        MainWindow.setMenuBar(self.menubar)
        self.action_about_program = QtGui.QAction(parent=MainWindow)
        icon15 = QtGui.QIcon()
        icon15.addPixmap(QtGui.QPixmap(":/sowInterface/information.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.action_about_program.setIcon(icon15)
        self.action_about_program.setShortcutVisibleInContextMenu(False)
        self.action_about_program.setObjectName("action_about_program")
        self.action_get_token_from_character_ai = QtGui.QAction(parent=MainWindow)
        icon16 = QtGui.QIcon()
        icon16.addPixmap(QtGui.QPixmap(":/sowInterface/characterai.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.action_get_token_from_character_ai.setIcon(icon16)
        self.action_get_token_from_character_ai.setObjectName("action_get_token_from_character_ai")
        self.action_create_new_character = QtGui.QAction(parent=MainWindow)
        self.action_create_new_character.setIcon(icon2)
        self.action_create_new_character.setObjectName("action_create_new_character")
        self.action_options = QtGui.QAction(parent=MainWindow)
        self.action_options.setIcon(icon4)
        self.action_options.setObjectName("action_options")
        self.action_discord = QtGui.QAction(parent=MainWindow)
        self.action_discord.setIcon(icon6)
        self.action_discord.setObjectName("action_discord")
        self.action_github = QtGui.QAction(parent=MainWindow)
        self.action_github.setIcon(icon7)
        self.action_github.setObjectName("action_github")
        self.action_faq = QtGui.QAction(parent=MainWindow)
        icon17 = QtGui.QIcon()
        icon17.addPixmap(QtGui.QPixmap(":/sowInterface/faq.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.action_faq.setIcon(icon17)
        self.action_faq.setObjectName("action_faq")
        self.menu_sow.addAction(self.action_about_program)
        self.menu_sow.addSeparator()
        self.menu_sow.addAction(self.action_get_token_from_character_ai)
        self.menu_sow.addAction(self.action_create_new_character)
        self.menu_sow.addSeparator()
        self.menu_sow.addAction(self.action_options)
        self.menu_help.addAction(self.action_discord)
        self.menu_help.addAction(self.action_github)
        self.menu_help.addSeparator()
        self.menu_help.addAction(self.action_faq)
        self.menubar.addAction(self.menu_sow.menuAction())
        self.menubar.addAction(self.menu_help.menuAction())

        self.stackedWidget.setCurrentIndex(0)
        self.tabWidget_options.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        