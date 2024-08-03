from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QVBoxLayout
import resources.rc_resource

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1059, 772)
        MainWindow.setWindowTitle("Soul of Waifu")
        MainWindow.setMinimumSize(QtCore.QSize(1059, 772))
        MainWindow.setMaximumSize(QtCore.QSize(1059, 772))
        MainWindow.setBaseSize(QtCore.QSize(1064, 774))
        MainWindow.setStyleSheet("")
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setStyleSheet("#centralwidget {    \n"
"    background-color: rgb(52, 58, 67);\n"
"    border: 1px solid rgb(44, 49, 58);\n"
"}\n"
"\n"
"#")
        self.centralwidget.setObjectName("centralwidget")
        self.SideBar_Menu = QtWidgets.QWidget(parent=self.centralwidget)
        self.SideBar_Menu.setGeometry(QtCore.QRect(0, 0, 239, 751))
        self.SideBar_Menu.setStyleSheet("#SideBar_Menu {\n"
"    background-color: rgb(43, 53, 68);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border: none;\n"
"    background-color: transparent;\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(63, 92, 186);\n"
"    color: rgb(0, 0, 0);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(63, 92, 186);\n"
"    color: rgb(0, 0, 0);\n"
"}")
        self.SideBar_Menu.setObjectName("SideBar_Menu")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.SideBar_Menu)
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.logotype = QtWidgets.QLabel(parent=self.SideBar_Menu)
        self.logotype.setMinimumSize(QtCore.QSize(221, 161))
        self.logotype.setMaximumSize(QtCore.QSize(221, 161))
        self.logotype.setText("")
        self.logotype.setPixmap(QtGui.QPixmap("./resources/icons/Title.png"))
        self.logotype.setScaledContents(True)
        self.logotype.setObjectName("logotype")
        self.logotype.setStyleSheet("padding: 10px;")
        self.verticalLayout_3.addWidget(self.logotype)
        spacerItem = QtWidgets.QSpacerItem(20, 3, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_3.addItem(spacerItem)
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setSpacing(15)
        self.verticalLayout.setObjectName("verticalLayout")
        self.pushButton_Home = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        self.pushButton_Home.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_Home.sizePolicy().hasHeightForWidth())
        self.pushButton_Home.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        font.setStrikeOut(False)
        font.setKerning(True)
        font.setStyleStrategy(QtGui.QFont.StyleStrategy.PreferDefault)
        self.pushButton_Home.setFont(font)
        self.pushButton_Home.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_Home.setMouseTracking(False)
        self.pushButton_Home.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.DefaultContextMenu)
        self.pushButton_Home.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_Home.setAutoFillBackground(False)
        self.pushButton_Home.setStyleSheet("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("./resources/icons/Homepage_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon1.addPixmap(QtGui.QPixmap("./resources/icons/Homepage_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_Home.setIcon(icon1)
        self.pushButton_Home.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_Home.setCheckable(True)
        self.pushButton_Home.setChecked(False)
        self.pushButton_Home.setAutoExclusive(True)
        self.pushButton_Home.setObjectName("pushButton_Home")
        self.verticalLayout.addWidget(self.pushButton_Home)
        self.pushButton_CreateCharacter = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_CreateCharacter.sizePolicy().hasHeightForWidth())
        self.pushButton_CreateCharacter.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_CreateCharacter.setFont(font)
        self.pushButton_CreateCharacter.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_CreateCharacter.setStyleSheet("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("./resources/icons/Add_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon2.addPixmap(QtGui.QPixmap("./resources/icons/Add_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_CreateCharacter.setIcon(icon2)
        self.pushButton_CreateCharacter.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_CreateCharacter.setCheckable(True)
        self.pushButton_CreateCharacter.setChecked(False)
        self.pushButton_CreateCharacter.setAutoExclusive(True)
        self.pushButton_CreateCharacter.setObjectName("pushButton_CreateCharacter")
        self.verticalLayout.addWidget(self.pushButton_CreateCharacter)
        self.pushButton_ListOfCharacters = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_ListOfCharacters.setFont(font)
        self.pushButton_ListOfCharacters.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_ListOfCharacters.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_ListOfCharacters.setStyleSheet("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(QtGui.QPixmap("./resources/icons/ListofCharacter_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon3.addPixmap(QtGui.QPixmap("./resources/icons/ListofCharacter_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_ListOfCharacters.setIcon(icon3)
        self.pushButton_ListOfCharacters.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_ListOfCharacters.setCheckable(True)
        self.pushButton_ListOfCharacters.setChecked(False)
        self.pushButton_ListOfCharacters.setAutoExclusive(True)
        self.pushButton_ListOfCharacters.setObjectName("pushButton_ListOfCharacters")
        self.verticalLayout.addWidget(self.pushButton_ListOfCharacters)
        self.pushButton_Options = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_Options.setFont(font)
        self.pushButton_Options.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_Options.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_Options.setStyleSheet("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(QtGui.QPixmap("./resources/icons/Settings_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon4.addPixmap(QtGui.QPixmap("./resources/icons/Settings_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_Options.setIcon(icon4)
        self.pushButton_Options.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_Options.setCheckable(True)
        self.pushButton_Options.setAutoExclusive(True)
        self.pushButton_Options.setObjectName("pushButton_Options")
        self.verticalLayout.addWidget(self.pushButton_Options)
        self.verticalLayout_3.addLayout(self.verticalLayout)
        spacerItem1 = QtWidgets.QSpacerItem(20, 328, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.verticalLayout_3.addItem(spacerItem1)
        self.line = QtWidgets.QFrame(parent=self.SideBar_Menu)
        self.line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line.setObjectName("line")
        self.verticalLayout_3.addWidget(self.line)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setSpacing(20)
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 10)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.pushButton_Youtube = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_Youtube.setFont(font)
        self.pushButton_Youtube.setStyleSheet("")
        icon5 = QtGui.QIcon()
        icon5.addPixmap(QtGui.QPixmap("./resources/icons/YouTube_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon5.addPixmap(QtGui.QPixmap("./resources/icons/YouTube_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_Youtube.setIcon(icon5)
        self.pushButton_Youtube.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_Youtube.setCheckable(False)
        self.pushButton_Youtube.setAutoExclusive(True)
        self.pushButton_Youtube.setObjectName("pushButton_Youtube")
        self.verticalLayout_2.addWidget(self.pushButton_Youtube)
        self.pushButton_Discord = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_Discord.setFont(font)
        self.pushButton_Discord.setStyleSheet("")
        icon6 = QtGui.QIcon()
        icon6.addPixmap(QtGui.QPixmap("./resources/icons/Discord_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon6.addPixmap(QtGui.QPixmap("./resources/icons/Discord_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_Discord.setIcon(icon6)
        self.pushButton_Discord.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_Discord.setCheckable(False)
        self.pushButton_Discord.setAutoExclusive(True)
        self.pushButton_Discord.setObjectName("pushButton_Discord")
        self.verticalLayout_2.addWidget(self.pushButton_Discord)
        self.pushButton_Github = QtWidgets.QPushButton(parent=self.SideBar_Menu)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_Github.setFont(font)
        self.pushButton_Github.setStyleSheet("")
        icon7 = QtGui.QIcon()
        icon7.addPixmap(QtGui.QPixmap("./resources/icons/Github_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        icon7.addPixmap(QtGui.QPixmap("./resources/icons/Github_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
        self.pushButton_Github.setIcon(icon7)
        self.pushButton_Github.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_Github.setCheckable(False)
        self.pushButton_Github.setAutoExclusive(True)
        self.pushButton_Github.setObjectName("pushButton_Github")
        self.verticalLayout_2.addWidget(self.pushButton_Github)
        self.verticalLayout_3.addLayout(self.verticalLayout_2)
        self.MainWindow_2 = QtWidgets.QWidget(parent=self.centralwidget)
        self.MainWindow_2.setGeometry(QtCore.QRect(240, 0, 841, 751))
        self.MainWindow_2.setObjectName("MainWindow_2")
        self.stackedWidget = QtWidgets.QStackedWidget(parent=self.MainWindow_2)
        self.stackedWidget.setGeometry(QtCore.QRect(-1, 50, 821, 711))
        self.stackedWidget.setStyleSheet("#main_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#create_character_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#list_of_characters_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#options_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#chat_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#main2_page{\n"
"    background-color: rgb(30, 37, 47);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"")
        self.stackedWidget.setObjectName("stackedWidget")
        self.main_page = QtWidgets.QWidget()
        self.main_page.setObjectName("main_page")
        self.bottomBar = QtWidgets.QFrame(parent=self.main_page)
        self.bottomBar.setGeometry(QtCore.QRect(0, 680, 821, 22))
        self.bottomBar.setMinimumSize(QtCore.QSize(0, 22))
        self.bottomBar.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottomBar.setStyleSheet("#bottomBar {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}")
        self.bottomBar.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottomBar.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottomBar.setObjectName("bottomBar")
        self.horizontalLayout_5 = QtWidgets.QHBoxLayout(self.bottomBar)
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.creditsLabel = QtWidgets.QLabel(parent=self.bottomBar)
        self.creditsLabel.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creditsLabel.setFont(font)
        self.creditsLabel.setStyleSheet("#creditsLabel {\n"
"    padding-left: 5px;\n"
"    color: rgb(190, 190, 190);\n"
"}")
        self.creditsLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creditsLabel.setObjectName("creditsLabel")
        self.horizontalLayout_5.addWidget(self.creditsLabel)
        self.version = QtWidgets.QLabel(parent=self.bottomBar)
        self.version.setStyleSheet("color: rgb(190, 190, 190);")
        self.version.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version.setObjectName("version")
        self.horizontalLayout_5.addWidget(self.version)
        self.frame_size_grip = QtWidgets.QFrame(parent=self.bottomBar)
        self.frame_size_grip.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip.setObjectName("frame_size_grip")
        self.horizontalLayout_5.addWidget(self.frame_size_grip)
        self.NoneCharacter_Label = QtWidgets.QLabel(parent=self.main_page)
        self.NoneCharacter_Label.setGeometry(QtCore.QRect(30, 230, 771, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.NoneCharacter_Label.setFont(font)
        self.NoneCharacter_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.NoneCharacter_Label.setObjectName("NoneCharacter_Label")
        self.pushButton_CreateCharacter2 = QtWidgets.QPushButton(parent=self.main_page)
        self.pushButton_CreateCharacter2.setGeometry(QtCore.QRect(310, 330, 219, 25))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_CreateCharacter2.sizePolicy().hasHeightForWidth())
        self.pushButton_CreateCharacter2.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_CreateCharacter2.setFont(font)
        self.pushButton_CreateCharacter2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_CreateCharacter2.setStyleSheet("QPushButton {\n"
"    color: rgb(255, 255, 255);\n"
"    background-position: left center;\n"
"    background-repeat: no-repeat;\n"
"    border-radius: 10px;\n"
"    background-color: rgb(52, 66, 116);\n"
"    text-align: left;\n"
"    padding-left: 10px;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(52, 63, 102);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"")
        self.pushButton_CreateCharacter2.setIcon(icon2)
        self.pushButton_CreateCharacter2.setIconSize(QtCore.QSize(25, 25))
        self.pushButton_CreateCharacter2.setCheckable(False)
        self.pushButton_CreateCharacter2.setChecked(False)
        self.pushButton_CreateCharacter2.setAutoExclusive(True)
        self.pushButton_CreateCharacter2.setObjectName("pushButton_CreateCharacter2")
        self.frame_3 = QtWidgets.QFrame(parent=self.main_page)
        self.frame_3.setGeometry(QtCore.QRect(0, 2, 820, 51))
        self.frame_3.setStyleSheet("background-color: rgb(43, 53, 68);\n"
"border-radius: 10px;")
        self.frame_3.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_3.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_3.setObjectName("frame_3")
        self.horizontalLayout_8 = QtWidgets.QHBoxLayout(self.frame_3)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        spacerItem2 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem2)
        self.MainNavigation_Label = QtWidgets.QLabel(parent=self.frame_3)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.MainNavigation_Label.setFont(font)
        self.MainNavigation_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.MainNavigation_Label.setObjectName("MainNavigation_Label")
        self.horizontalLayout_8.addWidget(self.MainNavigation_Label)
        spacerItem3 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_8.addItem(spacerItem3)
        self.stackedWidget.addWidget(self.main_page)
        self.main2_page = QtWidgets.QWidget()
        self.main2_page.setObjectName("main2_page")
        self.bottomBar_5 = QtWidgets.QFrame(parent=self.main2_page)
        self.bottomBar_5.setGeometry(QtCore.QRect(0, 680, 821, 22))
        self.bottomBar_5.setMinimumSize(QtCore.QSize(0, 22))
        self.bottomBar_5.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottomBar_5.setStyleSheet("background-color: rgb(52, 58, 67);\n"
"border-radius: 10px;")
        self.bottomBar_5.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottomBar_5.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottomBar_5.setObjectName("bottomBar_5")
        self.horizontalLayout_7 = QtWidgets.QHBoxLayout(self.bottomBar_5)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.creditsLabel_2 = QtWidgets.QLabel(parent=self.bottomBar_5)
        self.creditsLabel_2.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creditsLabel_2.setFont(font)
        self.creditsLabel_2.setStyleSheet("padding-left: 5px;\n"
"color: rgb(190, 190, 190);")
        self.creditsLabel_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creditsLabel_2.setObjectName("creditsLabel_2")
        self.horizontalLayout_7.addWidget(self.creditsLabel_2)
        self.version_2 = QtWidgets.QLabel(parent=self.bottomBar_5)
        self.version_2.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_2.setObjectName("version_2")
        self.horizontalLayout_7.addWidget(self.version_2)
        self.frame_size_grip_2 = QtWidgets.QFrame(parent=self.bottomBar_5)
        self.frame_size_grip_2.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip_2.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip_2.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip_2.setObjectName("frame_size_grip_2")
        self.horizontalLayout_7.addWidget(self.frame_size_grip_2)
        self.frame_4 = QtWidgets.QFrame(parent=self.main2_page)
        self.frame_4.setGeometry(QtCore.QRect(-1, 2, 821, 51))
        self.frame_4.setStyleSheet("background-color: rgb(43, 53, 68);\n"
"border-radius: 10px;")
        self.frame_4.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_4.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_4.setObjectName("frame_4")
        self.horizontalLayout_12 = QtWidgets.QHBoxLayout(self.frame_4)
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        spacerItem4 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem4)
        self.MainNavigation2_Label = QtWidgets.QLabel(parent=self.frame_4)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.MainNavigation2_Label.setFont(font)
        self.MainNavigation2_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.MainNavigation2_Label.setObjectName("MainNavigation2_Label")
        self.horizontalLayout_12.addWidget(self.MainNavigation2_Label)
        spacerItem5 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_12.addItem(spacerItem5)
        self.HomeUser_Label = QtWidgets.QLabel(parent=self.main2_page)
        self.HomeUser_Label.setGeometry(QtCore.QRect(30, 60, 771, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.HomeUser_Label.setFont(font)
        self.HomeUser_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.HomeUser_Label.setObjectName("HomeUser_Label")
        self.user_avatar_label = QtWidgets.QLabel(parent=self.main2_page)
        self.user_avatar_label.setGeometry(QtCore.QRect(100, 100, 100, 100))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.user_avatar_label.setFont(font)
        self.user_avatar_label.setStyleSheet("color: rgb(255, 255, 255);")
        self.user_avatar_label.setObjectName("user_avatar_label")
        self.stackedWidget.addWidget(self.main2_page)
        self.create_character_page = QtWidgets.QWidget()
        self.create_character_page.setObjectName("create_character_page")
        self.bottomBar_2 = QtWidgets.QFrame(parent=self.create_character_page)
        self.bottomBar_2.setGeometry(QtCore.QRect(0, 680, 821, 22))
        self.bottomBar_2.setMinimumSize(QtCore.QSize(0, 22))
        self.bottomBar_2.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottomBar_2.setStyleSheet("#bottomBar {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_2 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}")
        self.bottomBar_2.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottomBar_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottomBar_2.setObjectName("bottomBar_2")
        self.horizontalLayout_9 = QtWidgets.QHBoxLayout(self.bottomBar_2)
        self.horizontalLayout_9.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_9.setSpacing(0)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.creditsLabel_5 = QtWidgets.QLabel(parent=self.bottomBar_2)
        self.creditsLabel_5.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creditsLabel_5.setFont(font)
        self.creditsLabel_5.setStyleSheet("padding-left: 5px;\n"
"color: rgb(190, 190, 190);\n"
"")
        self.creditsLabel_5.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creditsLabel_5.setObjectName("creditsLabel_5")
        self.horizontalLayout_9.addWidget(self.creditsLabel_5)
        self.version_5 = QtWidgets.QLabel(parent=self.bottomBar_2)
        self.version_5.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_5.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_5.setObjectName("version_5")
        self.horizontalLayout_9.addWidget(self.version_5)
        self.frame_size_grip_5 = QtWidgets.QFrame(parent=self.bottomBar_2)
        self.frame_size_grip_5.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip_5.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip_5.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip_5.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip_5.setObjectName("frame_size_grip_5")
        self.horizontalLayout_9.addWidget(self.frame_size_grip_5)
        self.label_4 = QtWidgets.QLabel(parent=self.create_character_page)
        self.label_4.setGeometry(QtCore.QRect(300, 190, 271, 101))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("color: rgb(255, 255, 255);\n"
"")
        self.label_4.setObjectName("label_4")
        self.label_7 = QtWidgets.QLabel(parent=self.create_character_page)
        self.label_7.setGeometry(QtCore.QRect(50, 270, 101, 81))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_7.setFont(font)
        self.label_7.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_7.setMidLineWidth(0)
        self.label_7.setObjectName("label_7")
        self.character_id_lineEdit = QtWidgets.QLineEdit(parent=self.create_character_page)
        self.character_id_lineEdit.setGeometry(QtCore.QRect(150, 300, 611, 21))
        self.character_id_lineEdit.setStyleSheet("padding-left: 5px;\n"
"border-radius: 5px;\n"
"border: 1px solid #ccc;")
        self.character_id_lineEdit.setObjectName("character_id_lineEdit")
        self.pushButton_AddCharacter = QtWidgets.QPushButton(parent=self.create_character_page)
        self.pushButton_AddCharacter.setGeometry(QtCore.QRect(630, 330, 131, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_AddCharacter.setFont(font)
        self.pushButton_AddCharacter.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_AddCharacter.setStyleSheet("QPushButton {\n"
"background-color: rgb(76, 77, 80);\n"
"border-radius: 15px;\n"
"background-repeat: no-repeat;\n"
"background-position: center;\n"
"}\n"
"\n"
"QPushButton:hover {\n"
"    background-color: rgb(27, 27, 27);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"QPushButton:pressed {    \n"
"    background-color: rgb(63, 92, 186);\n"
"    color: rgb(0, 0, 0);\n"
"}\n"
"\n"
"QPushButton:clicked {\n"
"    background-color: rgb(63, 92, 186);\n"
"    color: rgb(0, 0, 0);\n"
"}")
        icon8 = QtGui.QIcon()
        icon8.addPixmap(QtGui.QPixmap("./resources/icons/Add_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_AddCharacter.setIcon(icon8)
        self.pushButton_AddCharacter.setIconSize(QtCore.QSize(20, 20))
        self.pushButton_AddCharacter.setAutoExclusive(True)
        self.pushButton_AddCharacter.setObjectName("pushButton_AddCharacter")
        self.frame_5 = QtWidgets.QFrame(parent=self.create_character_page)
        self.frame_5.setGeometry(QtCore.QRect(0, 2, 820, 51))
        self.frame_5.setStyleSheet("background-color: rgb(43, 53, 68);\n"
"border-radius: 10px;")
        self.frame_5.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_5.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_5.setObjectName("frame_5")
        self.horizontalLayout_13 = QtWidgets.QHBoxLayout(self.frame_5)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        spacerItem6 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem6)
        self.MainNavigation2_Label_2 = QtWidgets.QLabel(parent=self.frame_5)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.MainNavigation2_Label_2.setFont(font)
        self.MainNavigation2_Label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.MainNavigation2_Label_2.setObjectName("MainNavigation2_Label_2")
        self.horizontalLayout_13.addWidget(self.MainNavigation2_Label_2)
        spacerItem7 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_13.addItem(spacerItem7)
        self.stackedWidget.addWidget(self.create_character_page)
        self.list_of_characters_page = QtWidgets.QWidget()
        self.list_of_characters_page.setObjectName("list_of_characters_page")
        self.bottomBar_3 = QtWidgets.QFrame(parent=self.list_of_characters_page)
        self.bottomBar_3.setGeometry(QtCore.QRect(0, 680, 821, 22))
        self.bottomBar_3.setMinimumSize(QtCore.QSize(0, 22))
        self.bottomBar_3.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottomBar_3.setStyleSheet("#bottomBar {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_2 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_3 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}")
        self.bottomBar_3.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottomBar_3.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottomBar_3.setObjectName("bottomBar_3")
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout(self.bottomBar_3)
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_10.setSpacing(0)
        self.horizontalLayout_10.setObjectName("horizontalLayout_10")
        self.creditsLabel_6 = QtWidgets.QLabel(parent=self.bottomBar_3)
        self.creditsLabel_6.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creditsLabel_6.setFont(font)
        self.creditsLabel_6.setStyleSheet("padding-left: 5px;\n"
"color: rgb(190, 190, 190);\n"
"")
        self.creditsLabel_6.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creditsLabel_6.setObjectName("creditsLabel_6")
        self.horizontalLayout_10.addWidget(self.creditsLabel_6)
        self.version_6 = QtWidgets.QLabel(parent=self.bottomBar_3)
        self.version_6.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_6.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_6.setObjectName("version_6")
        self.horizontalLayout_10.addWidget(self.version_6)
        self.frame_size_grip_6 = QtWidgets.QFrame(parent=self.bottomBar_3)
        self.frame_size_grip_6.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip_6.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip_6.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip_6.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip_6.setObjectName("frame_size_grip_6")
        self.horizontalLayout_10.addWidget(self.frame_size_grip_6)
        self.frame = QtWidgets.QFrame(parent=self.list_of_characters_page)
        self.frame.setGeometry(QtCore.QRect(0, 2, 820, 51))
        self.frame.setStyleSheet("background-color: rgb(43, 53, 68);\n"
"border-radius: 10px;")
        self.frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout_4 = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem8 = QtWidgets.QSpacerItem(279, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem8)
        self.ListOfCharacters_Label = QtWidgets.QLabel(parent=self.frame)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.ListOfCharacters_Label.setFont(font)
        self.ListOfCharacters_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.ListOfCharacters_Label.setObjectName("ListOfCharacters_Label")
        self.horizontalLayout_4.addWidget(self.ListOfCharacters_Label)
        spacerItem9 = QtWidgets.QSpacerItem(270, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem9)
        
        self.list_of_characters_layout = QVBoxLayout()
        self.characterlistWidget = QtWidgets.QListWidget(parent=self.list_of_characters_page)
        self.characterlistWidget.setGeometry(QtCore.QRect(0, 51, 821, 631))
        self.characterlistWidget.setStyleSheet("background-color: rgb(61, 61, 61);\n"
"border: none;")
        self.characterlistWidget.setObjectName("characterlistWidget")
        self.list_of_characters_layout.addWidget(self.characterlistWidget)
        
        self.stackedWidget.addWidget(self.list_of_characters_page)
        self.options_page = QtWidgets.QWidget()
        self.options_page.setObjectName("options_page")
        self.bottomBar_4 = QtWidgets.QFrame(parent=self.options_page)
        self.bottomBar_4.setGeometry(QtCore.QRect(0, 680, 821, 22))
        self.bottomBar_4.setMinimumSize(QtCore.QSize(0, 22))
        self.bottomBar_4.setMaximumSize(QtCore.QSize(16777215, 22))
        self.bottomBar_4.setStyleSheet("#bottomBar {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_2 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_3 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_4 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"#bottomBar_5 {\n"
"    background-color: rgb(52, 58, 67);\n"
"    border-radius: 10px;\n"
"}")
        self.bottomBar_4.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.bottomBar_4.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.bottomBar_4.setObjectName("bottomBar_4")
        self.horizontalLayout_11 = QtWidgets.QHBoxLayout(self.bottomBar_4)
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_11.setSpacing(0)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.creditsLabel_7 = QtWidgets.QLabel(parent=self.bottomBar_4)
        self.creditsLabel_7.setMaximumSize(QtCore.QSize(16777215, 16))
        font = QtGui.QFont()
        font.setFamily("Segoe UI")
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.creditsLabel_7.setFont(font)
        self.creditsLabel_7.setStyleSheet("padding-left: 5px;\n"
"color: rgb(190, 190, 190);\n"
"")
        self.creditsLabel_7.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.creditsLabel_7.setObjectName("creditsLabel_7")
        self.horizontalLayout_11.addWidget(self.creditsLabel_7)
        self.version_7 = QtWidgets.QLabel(parent=self.bottomBar_4)
        self.version_7.setStyleSheet("color: rgb(190, 190, 190);")
        self.version_7.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight|QtCore.Qt.AlignmentFlag.AlignTrailing|QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.version_7.setObjectName("version_7")
        self.horizontalLayout_11.addWidget(self.version_7)
        self.frame_size_grip_7 = QtWidgets.QFrame(parent=self.bottomBar_4)
        self.frame_size_grip_7.setMinimumSize(QtCore.QSize(20, 0))
        self.frame_size_grip_7.setMaximumSize(QtCore.QSize(20, 16777215))
        self.frame_size_grip_7.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_size_grip_7.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_size_grip_7.setObjectName("frame_size_grip_7")
        self.horizontalLayout_11.addWidget(self.frame_size_grip_7)
        self.frame_2 = QtWidgets.QFrame(parent=self.options_page)
        self.frame_2.setGeometry(QtCore.QRect(0, 2, 820, 51))
        self.frame_2.setStyleSheet("background-color: rgb(43, 53, 68);\n"
"border-radius: 10px;")
        self.frame_2.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.frame_2.setObjectName("frame_2")
        self.horizontalLayout_6 = QtWidgets.QHBoxLayout(self.frame_2)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        spacerItem10 = QtWidgets.QSpacerItem(302, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem10)
        self.Options_Label = QtWidgets.QLabel(parent=self.frame_2)
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.Options_Label.setFont(font)
        self.Options_Label.setStyleSheet("color: rgb(255, 255, 255);")
        self.Options_Label.setObjectName("Options_Label")
        self.horizontalLayout_6.addWidget(self.Options_Label)
        spacerItem11 = QtWidgets.QSpacerItem(292, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_6.addItem(spacerItem11)
        self.tabWidget = QtWidgets.QTabWidget(parent=self.options_page)
        self.tabWidget.setGeometry(QtCore.QRect(10, 60, 801, 611))
        self.tabWidget.setStyleSheet("QTabWidget {\n"
"    border-radius: 10px;\n"
"}\n"
"\n"
"QTabWidget::tab-bar {\n"
"     left: 5px;\n"
"     right: 5px;\n"
"}\n"
"\n"
"QTabWidget::tab-bar QTabBar::tab {\n"
"     background-color: #333;\n"
"     border-radius: 5px;\n"
"     color: #eee;\n"
"     padding: 10px;\n"
"}\n"
"\n"
"QTabWidget::tab-bar QTabBar::tab:selected {\n"
"     background-color: #444;\n"
"     border-bottom: 2px solid #555;\n"
"}")
        self.tabWidget.setObjectName("tabWidget")
        self.config_tab = QtWidgets.QWidget()
        self.config_tab.setObjectName("config_tab")
        self.label_8 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_8.setGeometry(QtCore.QRect(10, 0, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.label_9 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_9.setGeometry(QtCore.QRect(10, 50, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.lineEdit_apiToken = QtWidgets.QLineEdit(parent=self.config_tab)
        self.lineEdit_apiToken.setGeometry(QtCore.QRect(120, 40, 401, 34))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.lineEdit_apiToken.setFont(font)
        self.lineEdit_apiToken.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 1px solid #555;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid #fff;\n"
"            }")
        self.lineEdit_apiToken.setObjectName("lineEdit_apiToken")
        self.label_10 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_10.setGeometry(QtCore.QRect(10, 100, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.label_10.setFont(font)
        self.label_10.setObjectName("label_10")
        self.line_2 = QtWidgets.QFrame(parent=self.config_tab)
        self.line_2.setGeometry(QtCore.QRect(10, 80, 781, 20))
        self.line_2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_2.setObjectName("line_2")
        self.label_11 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_11.setGeometry(QtCore.QRect(10, 150, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_11.setFont(font)
        self.label_11.setObjectName("label_11")
        self.comboBox_TTS = QtWidgets.QComboBox(parent=self.config_tab)
        self.comboBox_TTS.setGeometry(QtCore.QRect(100, 141, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_TTS.setFont(font)
        self.comboBox_TTS.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_TTS.setObjectName("comboBox_TTS")
        self.comboBox_TTS.addItem("")
        self.comboBox_TTS.setItemText(0, "None")
        self.comboBox_TTS.addItem("")
        self.comboBox_TTS.addItem("")
        self.comboBox_TTS.addItem("")
        self.label_12 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_12.setGeometry(QtCore.QRect(10, 200, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_12.setFont(font)
        self.label_12.setObjectName("label_12")
        self.comboBox_TTS_Lang = QtWidgets.QComboBox(parent=self.config_tab)
        self.comboBox_TTS_Lang.setGeometry(QtCore.QRect(130, 190, 201, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_TTS_Lang.setFont(font)
        self.comboBox_TTS_Lang.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_TTS_Lang.setObjectName("comboBox_TTS_Lang")
        self.comboBox_TTS_Lang.addItem("")
        self.comboBox_TTS_Lang.addItem("")
        self.label_13 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_13.setGeometry(QtCore.QRect(10, 250, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_13.setFont(font)
        self.label_13.setObjectName("label_13")
        self.comboBox_TTS_Device = QtWidgets.QComboBox(parent=self.config_tab)
        self.comboBox_TTS_Device.setGeometry(QtCore.QRect(110, 240, 221, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_TTS_Device.setFont(font)
        self.comboBox_TTS_Device.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_TTS_Device.setObjectName("comboBox_TTS_Device")
        self.comboBox_TTS_Device.addItem("")
        self.comboBox_TTS_Device.addItem("")
        self.label_14 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_14.setGeometry(QtCore.QRect(360, 140, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_14.setFont(font)
        self.label_14.setObjectName("label_14")
        self.lineEdit_ElevenToken = QtWidgets.QLineEdit(parent=self.config_tab)
        self.lineEdit_ElevenToken.setGeometry(QtCore.QRect(470, 140, 281, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.lineEdit_ElevenToken.setFont(font)
        self.lineEdit_ElevenToken.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 1px solid #555;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid #fff;\n"
"            }")
        self.lineEdit_ElevenToken.setObjectName("lineEdit_ElevenToken")
        self.label_elevenlabs_voice_id = QtWidgets.QLabel(parent=self.config_tab)
        self.label_elevenlabs_voice_id.setGeometry(QtCore.QRect(360, 190, 111, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_elevenlabs_voice_id.setFont(font)
        self.label_elevenlabs_voice_id.setObjectName("label_elevenlabs_voice_id")
        self.lineEdit_ElevenToken_voiceID = QtWidgets.QLineEdit(parent=self.config_tab)
        self.lineEdit_ElevenToken_voiceID.setGeometry(QtCore.QRect(460, 190, 291, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.lineEdit_ElevenToken_voiceID.setFont(font)
        self.lineEdit_ElevenToken_voiceID.setStyleSheet("QLineEdit {\n"
"    background-color: #333;\n"
"    color: #eee;\n"
"    border: 1px solid #555;\n"
"    border-radius: 5px;\n"
"    padding: 5px;\n"
"}\n"
"\n"
"QLineEdit:focus {\n"
"    border: 1px solid #fff;\n"
"            }")
        self.lineEdit_ElevenToken_voiceID.setObjectName("lineEdit_ElevenToken_voiceID")
        self.label_15 = QtWidgets.QLabel(parent=self.config_tab)
        self.label_15.setGeometry(QtCore.QRect(10, 300, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_15.setFont(font)
        self.label_15.setObjectName("label_15")
        self.comboBox_TTS_Voice = QtWidgets.QComboBox(parent=self.config_tab)
        self.comboBox_TTS_Voice.setGeometry(QtCore.QRect(110, 290, 221, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_TTS_Voice.setFont(font)
        self.comboBox_TTS_Voice.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_TTS_Voice.setObjectName("comboBox_TTS_Voice")
        self.tabWidget.addTab(self.config_tab, "")
        self.system_tab = QtWidgets.QWidget()
        self.system_tab.setObjectName("system_tab")
        self.label_16 = QtWidgets.QLabel(parent=self.system_tab)
        self.label_16.setGeometry(QtCore.QRect(10, 0, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.label_16.setFont(font)
        self.label_16.setObjectName("label_16")
        self.comboBox_Language = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_Language.setGeometry(QtCore.QRect(10, 40, 331, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_Language.setFont(font)
        self.comboBox_Language.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_Language.setObjectName("comboBox_Language")
        self.comboBox_Language.addItem("")
        self.comboBox_Language.addItem("")
        self.line_3 = QtWidgets.QFrame(parent=self.system_tab)
        self.line_3.setGeometry(QtCore.QRect(10, 80, 781, 20))
        self.line_3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        self.line_3.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.line_3.setObjectName("line_3")
        self.label_17 = QtWidgets.QLabel(parent=self.system_tab)
        self.label_17.setGeometry(QtCore.QRect(10, 100, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.label_17.setFont(font)
        self.label_17.setObjectName("label_17")
        self.label_18 = QtWidgets.QLabel(parent=self.system_tab)
        self.label_18.setGeometry(QtCore.QRect(10, 160, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_18.setFont(font)
        self.label_18.setObjectName("label_18")
        self.comboBox_InputDevice = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_InputDevice.setGeometry(QtCore.QRect(100, 150, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_InputDevice.setFont(font)
        self.comboBox_InputDevice.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_InputDevice.setObjectName("comboBox_InputDevice")
        self.label_19 = QtWidgets.QLabel(parent=self.system_tab)
        self.label_19.setGeometry(QtCore.QRect(10, 210, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_19.setFont(font)
        self.label_19.setObjectName("label_19")
        self.comboBox_OutputDevice = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_OutputDevice.setGeometry(QtCore.QRect(120, 200, 231, 31))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_OutputDevice.setFont(font)
        self.comboBox_OutputDevice.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_OutputDevice.setObjectName("comboBox_OutputDevice")
        self.label_stt = QtWidgets.QLabel(parent=self.system_tab)
        self.label_stt.setGeometry(QtCore.QRect(10, 250, 261, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(11)
        font.setBold(True)
        font.setWeight(75)
        self.label_stt.setFont(font)
        self.label_stt.setObjectName("label_stt")
        self.label_stt.setText("Speech-To-Text")
        self.label_stt_2 = QtWidgets.QLabel(parent=self.system_tab)
        self.label_stt_2.setGeometry(QtCore.QRect(10, 290, 111, 16))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(10)
        self.label_stt_2.setFont(font)
        self.label_stt_2.setObjectName("label_stt_2")
        self.label_stt_2.setText("Speech To Text:")
        self.comboBox_SpeechToText = QtWidgets.QComboBox(parent=self.system_tab)
        self.comboBox_SpeechToText.setGeometry(QtCore.QRect(120, 280, 231, 31))
        self.comboBox_SpeechToText.addItem("Google")
        self.comboBox_SpeechToText.addItem("Whisper")
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(9)
        self.comboBox_SpeechToText.setFont(font)
        self.comboBox_SpeechToText.setStyleSheet("background-color: #333;\n"
"color: #eee;\n"
"border: 1px solid #555;\n"
"border-radius: 5px;\n"
"padding: 5px;")
        self.comboBox_SpeechToText.setObjectName("comboBox_SpeechToText")
        self.tabWidget.addTab(self.system_tab, "")
        self.stackedWidget.addWidget(self.options_page)
        self.chat_page = QtWidgets.QWidget()
        self.chat_page.setObjectName("chat_page")
        self.send_message_frame = QtWidgets.QFrame(parent=self.chat_page)
        self.send_message_frame.setGeometry(QtCore.QRect(2, 660, 817, 40))
        self.send_message_frame.setStyleSheet("#send_message_frame { \n"
"    background-color: rgb(47, 48, 50);\n"
"    border-radius: 20px;\n"
"}\n"
"\n"
"#send_message_frame QPushButton {\n"
"    background-color: rgb(76, 77, 80);\n"
"    border-radius: 15px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"\n"
"#send_message_frame QPushButton:hover {\n"
"    background-color: rgb(81, 82, 86);\n"
"}\n"
"\n"
"#send_message_frame QPushButton:pressed {\n"
"    background-color: rgb(16, 17, 18);\n"
"}\n"
"#line_edit_message {\n"
"    background-color: transparent;\n"
"    selection-color: rgb(255, 255, 255);\n"
"    selection-background-color: rgb(149, 199, 0);\n"
"    border: none;\n"
"    padding-left: 15px;\n"
"    padding-right: 15px;\n"
"    background-repeat: none;\n"
"    background-position: left center;\n"
"    font: 10pt \"Segoe UI\";\n"
"    color: rgb(94, 96, 100);\n"
"}\n"
"#line_edit_message:focus {\n"
"    color: rgb(165, 165, 165);\n"
"}")
        self.send_message_frame.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.send_message_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.send_message_frame.setObjectName("send_message_frame")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout(self.send_message_frame)
        self.horizontalLayout_3.setContentsMargins(5, 0, 5, 0)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.btn_call = QtWidgets.QPushButton(parent=self.send_message_frame)
        self.btn_call.setMinimumSize(QtCore.QSize(30, 30))
        self.btn_call.setMaximumSize(QtCore.QSize(30, 30))
        self.btn_call.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_call.setText("")
        icon9 = QtGui.QIcon()
        icon9.addPixmap(QtGui.QPixmap("./resources/icons/Phone_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_call.setIcon(icon9)
        self.btn_call.setObjectName("btn_call")
        self.horizontalLayout_3.addWidget(self.btn_call)
        self.line_edit_message = QtWidgets.QLineEdit(parent=self.send_message_frame)
        self.line_edit_message.setMinimumSize(QtCore.QSize(0, 40))
        self.line_edit_message.setObjectName("line_edit_message")
        self.horizontalLayout_3.addWidget(self.line_edit_message)
        self.btn_send_message = QtWidgets.QPushButton(parent=self.send_message_frame)
        self.btn_send_message.setMinimumSize(QtCore.QSize(30, 30))
        self.btn_send_message.setMaximumSize(QtCore.QSize(30, 30))
        self.btn_send_message.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_send_message.setText("")
        icon10 = QtGui.QIcon()
        icon10.addPixmap(QtGui.QPixmap("./resources/icons/Send_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_send_message.setIcon(icon10)
        self.btn_send_message.setObjectName("btn_send_message")
        self.horizontalLayout_3.addWidget(self.btn_send_message)
        self.top = QtWidgets.QFrame(parent=self.chat_page)
        self.top.setGeometry(QtCore.QRect(0, 0, 821, 60))
        self.top.setMinimumSize(QtCore.QSize(0, 60))
        self.top.setMaximumSize(QtCore.QSize(16777215, 60))
        self.top.setStyleSheet("#top {\n"
"    background-color: rgb(30, 32, 33);\n"
"    border-radius: 10px;\n"
"}\n"
"#user_name { \n"
"    color: rgb(179, 179, 179);\n"
"    font: 600 12pt \"Segoe UI\";\n"
"}\n"
"#user_image {\n"
"    border: 1px solid rgb(30, 32, 33);\n"
"    background-color: rgb(47, 48, 50);\n"
"    border-radius: 20px;\n"
"}\n"
"#top QPushButton {\n"
"    background-color: rgb(47, 48, 50);\n"
"    border-radius: 20px;\n"
"    background-repeat: no-repeat;\n"
"    background-position: center;\n"
"}\n"
"#top QPushButton:hover {\n"
"    background-color: rgb(61, 62, 65);\n"
"}\n"
"#top QPushButton:pressed {\n"
"    background-color: rgb(16, 17, 18);\n"
"}\n"
"#btn_attachment_top {    \n"
"    background-image: url(:/icons_svg/images/icons_svg/icon_attachment.svg);\n"
"}\n"
"#btn_more_top {    \n"
"    background-image: url(:/icons_svg/images/icons_svg/icon_more_options.svg);\n"
"}")
        self.top.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.top.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.top.setObjectName("top")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.top)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.character_image = QtWidgets.QLabel(parent=self.top)
        self.character_image.setMinimumSize(QtCore.QSize(40, 40))
        self.character_image.setMaximumSize(QtCore.QSize(40, 40))
        self.character_image.setText("")
        self.character_image.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.character_image.setObjectName("character_image")
        self.horizontalLayout_2.addWidget(self.character_image)
        self.user_information_frame = QtWidgets.QFrame(parent=self.top)
        self.user_information_frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.user_information_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        self.user_information_frame.setObjectName("user_information_frame")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.user_information_frame)
        self.verticalLayout_4.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.character_name = QtWidgets.QLabel(parent=self.user_information_frame)
        self.character_name.setMinimumSize(QtCore.QSize(0, 22))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.character_name.setFont(font)
        self.character_name.setStyleSheet("color: rgb(255, 255, 255);")
        self.character_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeading|QtCore.Qt.AlignmentFlag.AlignLeft|QtCore.Qt.AlignmentFlag.AlignTop)
        self.character_name.setObjectName("character_name")
        self.verticalLayout_4.addWidget(self.character_name)
        self.character_description = QtWidgets.QLabel(parent=self.user_information_frame)
        font = QtGui.QFont()
        font.setFamily("Muli Light")
        self.character_description.setFont(font)
        self.character_description.setStyleSheet("background: transparent;\n"
"color: rgb(216, 216, 216)")
        self.character_description.setObjectName("character_description")
        self.verticalLayout_4.addWidget(self.character_description)
        self.horizontalLayout_2.addWidget(self.user_information_frame)
        spacerItem12 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem12)
        self.btn_more_chat = QtWidgets.QPushButton(parent=self.top)
        self.btn_more_chat.setMinimumSize(QtCore.QSize(40, 40))
        self.btn_more_chat.setMaximumSize(QtCore.QSize(40, 40))
        self.btn_more_chat.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.btn_more_chat.setText("")
        icon11 = QtGui.QIcon()
        icon11.addPixmap(QtGui.QPixmap("./resources/icons/More_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.btn_more_chat.setIcon(icon11)
        self.btn_more_chat.setObjectName("btn_more_chat")
        self.horizontalLayout_2.addWidget(self.btn_more_chat)
        self.scrollArea_chat = QtWidgets.QScrollArea(parent=self.chat_page)
        self.scrollArea_chat.setGeometry(QtCore.QRect(0, 60, 821, 601))
        self.scrollArea_chat.setStyleSheet("""
QScrollBar:vertical {
    border: none;
    background: rgb(50, 50, 50);
    width: 5px;
    margin: 0px 0px 0px 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: rgb(35, 35, 35);
    min-height: 20px;
    border-radius: 6px;
}

QScrollBar::add-line:vertical {
    border: none;
    background: #c4c4c4;
    height: 0px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}

QScrollBar::sub-line:vertical {
    border: none;
    background: #c4c4c4;
    height: 0px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}

QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
""")
        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_content.setGeometry(QtCore.QRect(0, 0, 801, 601))
        self.scroll_content.setObjectName("scroll_content")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.scrollArea_chat.setWidget(self.scroll_content)
        self.stackedWidget.addWidget(self.chat_page)
        self.widget = QtWidgets.QWidget(parent=self.MainWindow_2)
        self.widget.setGeometry(QtCore.QRect(-3, 1, 873, 51))
        self.widget.setStyleSheet("background-color: rgb(52, 58, 67);\n"
"")
        self.widget.setObjectName("widget")
        self.label_mainWords = QtWidgets.QLabel(parent=self.widget)
        self.label_mainWords.setGeometry(QtCore.QRect(190, 10, 467, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_mainWords.setFont(font)
        self.label_mainWords.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_mainWords.setObjectName("label_mainWords")
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1059, 21))
        self.menubar.setObjectName("menubar")
        self.menuSoW = QtWidgets.QMenu(parent=self.menubar)
        self.menuSoW.setObjectName("menuSoW")
        self.menuHelp = QtWidgets.QMenu(parent=self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        MainWindow.setMenuBar(self.menubar)
        self.actionAbout_program = QtGui.QAction(parent=MainWindow)
        icon12 = QtGui.QIcon()
        icon12.addPixmap(QtGui.QPixmap("./resources/icons/About_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionAbout_program.setIcon(icon12)
        self.actionAbout_program.setShortcutVisibleInContextMenu(False)
        self.actionAbout_program.setObjectName("actionAbout_program")
        self.actionGet_Token_from_Character_AI = QtGui.QAction(parent=MainWindow)
        icon13 = QtGui.QIcon()
        icon13.addPixmap(QtGui.QPixmap("./resources/icons/CharacterAI_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionGet_Token_from_Character_AI.setIcon(icon13)
        self.actionGet_Token_from_Character_AI.setObjectName("actionGet_Token_from_Character_AI")
        self.actionCreate_new_character = QtGui.QAction(parent=MainWindow)
        icon14 = QtGui.QIcon()
        icon14.addPixmap(QtGui.QPixmap("./resources/icons/Add_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionCreate_new_character.setIcon(icon14)
        self.actionCreate_new_character.setObjectName("actionCreate_new_character")
        self.actionSettings = QtGui.QAction(parent=MainWindow)
        icon15 = QtGui.QIcon()
        icon15.addPixmap(QtGui.QPixmap("./resources/icons/Settings_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionSettings.setIcon(icon15)
        self.actionSettings.setObjectName("actionSettings")
        self.actionGet_support_from_Discord = QtGui.QAction(parent=MainWindow)
        icon16 = QtGui.QIcon()
        icon16.addPixmap(QtGui.QPixmap("./resources/icons/Discord_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionGet_support_from_Discord.setIcon(icon16)
        self.actionGet_support_from_Discord.setObjectName("actionGet_support_from_Discord")
        self.actionGet_support_from_GitHub = QtGui.QAction(parent=MainWindow)
        icon17 = QtGui.QIcon()
        icon17.addPixmap(QtGui.QPixmap("./resources/icons/Github_Dark.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.actionGet_support_from_GitHub.setIcon(icon17)
        self.actionGet_support_from_GitHub.setObjectName("actionGet_support_from_GitHub")
        self.menuSoW.addAction(self.actionAbout_program)
        self.menuSoW.addSeparator()
        self.menuSoW.addAction(self.actionGet_Token_from_Character_AI)
        self.menuSoW.addAction(self.actionCreate_new_character)
        self.menuSoW.addSeparator()
        self.menuSoW.addAction(self.actionSettings)
        self.menuHelp.addAction(self.actionGet_support_from_Discord)
        self.menuHelp.addAction(self.actionGet_support_from_GitHub)
        self.menubar.addAction(self.menuSoW.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.stackedWidget.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        