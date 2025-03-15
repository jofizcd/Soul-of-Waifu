from PyQt6 import QtCore, QtGui, QtWidgets

class sow_System(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowFlags(QtCore.Qt.WindowType.Window)
        self.setupUi()
        self.translate = QtCore.QCoreApplication.translate

    def setupUi(self):
        # --- Main window settings ---
        self.setObjectName("SOW_SYSTEM")
        self.resize(1350, 713)
        self.setMinimumSize(QtCore.QSize(1350, 713))
        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("resources/icons/logotype.ico"),
                       QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        
        # Icon and stylesheet
        self.setWindowIcon(icon)
        self.setStyleSheet("background-color: black;")

        # --- Central Widget ---
        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        
        # Vertical Layout for central layout
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout_2.setSpacing(5)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.setCentralWidget(self.centralwidget)

        self.stackedWidget_sow_system = QtWidgets.QStackedWidget(self.centralwidget)
        self.stackedWidget_sow_system.setStyleSheet(
            "background-color: rgb(27,27,27); border-radius: 10px;"
        )
        self.stackedWidget_sow_system.setObjectName("stackedWidget_sow_system")
        self.verticalLayout_2.addWidget(self.stackedWidget_sow_system)

        # --- Page 1: Avatar ---
        self.avatar_page = QtWidgets.QWidget()
        self.avatar_page.setObjectName("avatar_page")
        self.setupAvatarPage(self.avatar_page)
        self.stackedWidget_sow_system.addWidget(self.avatar_page)

        # --- Page 2: Expression Image ---
        self.image_page = QtWidgets.QWidget()
        self.image_page.setObjectName("image_page")
        self.setupImagePage(self.image_page)
        self.stackedWidget_sow_system.addWidget(self.image_page)

        # --- Page 3: Live2D ---
        self.live2d_page = QtWidgets.QWidget()
        self.live2d_page.setObjectName("live2d_page")
        self.setupLive2DPage(self.live2d_page)
        self.stackedWidget_sow_system.addWidget(self.live2d_page)

        self.stackedWidget_sow_system.setCurrentIndex(0)

        self.retranslateUi()
        QtCore.QMetaObject.connectSlotsByName(self)

    def setupAvatarPage(self, page):
        # --- Main Layout ---
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- Frame: Information about character ---
        self.frame_character = QtWidgets.QFrame(page)
        self.frame_character.setMaximumHeight(60)
        self.frame_character.setStyleSheet(
            "#frame_character { border-radius: 10px; border: none; }"
            "#character_name_page1 { color: rgb(179, 179, 179); font: 600 12pt 'Segoe UI'; }"
            "#character_avatar_label_page1 { border: 1px solid rgb(30, 32, 33); background-color: rgb(47, 48, 50); border-radius: 20px; }"
        )
        frame_char_layout = QtWidgets.QHBoxLayout(self.frame_character)
        frame_char_layout.setContentsMargins(10, 0, 10, 0)
        frame_char_layout.setSpacing(10)

        # --- Frame with user information ---
        self.user_information_frame_page1 = QtWidgets.QFrame(self.frame_character)
        self.user_information_frame_page1.setStyleSheet("border: none;")
        ui_layout = QtWidgets.QVBoxLayout(self.user_information_frame_page1)
        ui_layout.setContentsMargins(5, 5, 5, 5)
        ui_layout.setSpacing(3)
        
        # Timer
        self.timer_page1 = QtWidgets.QLabel(self.user_information_frame_page1)
        font_timer = QtGui.QFont()
        font_timer.setFamily("Muli Medium")
        font_timer.setPointSize(12)
        self.timer_page1.setFont(font_timer)
        self.timer_page1.setStyleSheet("border: none; color: white;")
        ui_layout.addWidget(self.timer_page1)
        
        frame_char_layout.addWidget(self.user_information_frame_page1)

        spacerItem = QtWidgets.QSpacerItem(40, 20, 
                                        QtWidgets.QSizePolicy.Policy.Expanding,
                                        QtWidgets.QSizePolicy.Policy.Minimum
        )
        frame_char_layout.addItem(spacerItem)

        self.character_name_page1 = QtWidgets.QLabel(self.frame_character)
        self.character_name_page1.setMinimumHeight(22)
        font_name = QtGui.QFont()
        font_name.setFamily("Muli ExtraBold")
        font_name.setPointSize(12)
        font_name.setBold(True)
        font_name.setWeight(75)
        self.character_name_page1.setFont(font_name)
        self.character_name_page1.setStyleSheet("color: rgb(255, 255, 255); border: none;")
        self.character_name_page1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout.addWidget(self.character_name_page1)

        self.character_avatar_label_page1 = QtWidgets.QLabel(self.frame_character)
        self.character_avatar_label_page1.setMinimumSize(50, 50)
        self.character_avatar_label_page1.setMaximumSize(50, 50)
        self.character_avatar_label_page1.setStyleSheet("background-color: transparent; border-radius: 25px;")
        self.character_avatar_label_page1.setScaledContents(True)
        self.character_avatar_label_page1.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout.addWidget(self.character_avatar_label_page1)

        layout.addWidget(self.frame_character)

        self.frame_main = QtWidgets.QFrame(page)
        main_layout = QtWidgets.QHBoxLayout(self.frame_main)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        self.avatar_widget = QtWidgets.QWidget(self.frame_main)
        self.avatar_widget.setStyleSheet("background-color: rgb(23, 23, 23); border: 2px solid rgb(42, 42, 42);")
        avatar_layout = QtWidgets.QVBoxLayout(self.avatar_widget)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        self.avatar_label = QtWidgets.QLabel(self.avatar_widget)
        self.avatar_label.setStyleSheet("border: none;")
        self.avatar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(self.avatar_label)

        main_layout.addWidget(self.avatar_widget, 3)

        self.scrollArea_chat_page1 = QtWidgets.QScrollArea(self.frame_main)
        self.scrollArea_chat_page1.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page1.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page1.setStyleSheet(
            "background-color: rgb(23, 23, 23); padding: 5px; border-radius: 10px;"
        )
        self.scrollArea_chat_page1.setWidgetResizable(True)
        chat_widget = QtWidgets.QWidget()
        self.chat_container_page1 = QtWidgets.QVBoxLayout(chat_widget)
        self.chat_container_page1.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.chat_container_page1.setSpacing(5)
        self.chat_container_page1.addStretch()
        self.scrollArea_chat_page1.setWidget(chat_widget)
        main_layout.addWidget(self.scrollArea_chat_page1, 2)

        layout.addWidget(self.frame_main)

        self.frame_bar = QtWidgets.QFrame(page)
        self.frame_bar.setMaximumHeight(50)
        bar_layout = QtWidgets.QHBoxLayout(self.frame_bar)
        bar_layout.setContentsMargins(500, 5, 500, 5)
        bar_layout.setSpacing(6)

        self.pushButton_hang_up_page1 = QtWidgets.QPushButton(self.frame_bar)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        self.pushButton_hang_up_page1.setSizePolicy(sizePolicy)
        font_btn = QtGui.QFont()
        font_btn.setFamily("Muli Medium")
        font_btn.setPointSize(12)
        self.pushButton_hang_up_page1.setFont(font_btn)
        self.pushButton_hang_up_page1.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_hang_up_page1.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(172,57,57); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(190,60,60); }"
            "QPushButton:pressed { background-color: rgb(150,50,50); }"
        )
        self.pushButton_hang_up_page1.clicked.connect(self.hangUpReturnMain)
        bar_layout.addWidget(self.pushButton_hang_up_page1)

        self.pushButton_start_page1 = QtWidgets.QPushButton(self.frame_bar)
        self.pushButton_start_page1.setSizePolicy(sizePolicy)
        self.pushButton_start_page1.setFont(font_btn)
        self.pushButton_start_page1.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_start_page1.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(80,80,80); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(100,100,100); }"
            "QPushButton:pressed { background-color: rgb(60,60,60); }"
        )
        self.pushButton_start_page1.setText(("Start"))
        bar_layout.addWidget(self.pushButton_start_page1)

        layout.addWidget(self.frame_bar)

    def setupImagePage(self, page):
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.frame_character_2 = QtWidgets.QFrame(page)
        self.frame_character_2.setMaximumHeight(60)
        self.frame_character_2.setStyleSheet(
            "#frame_character_2 { border-radius: 10px; border: none; }"
            "#character_name_page2 { color: rgb(179, 179, 179); font: 600 12pt 'Segoe UI'; }"
            "#character_avatar_label_page2 { border: 1px solid rgb(30, 32, 33); background-color: rgb(47, 48, 50); border-radius: 20px; }"
        )
        frame_char_layout2 = QtWidgets.QHBoxLayout(self.frame_character_2)
        frame_char_layout2.setContentsMargins(10, 0, 10, 0)
        frame_char_layout2.setSpacing(10)
        self.user_information_frame_page2 = QtWidgets.QFrame(self.frame_character_2)
        self.user_information_frame_page2.setStyleSheet("border: none;")
        ui_layout2 = QtWidgets.QVBoxLayout(self.user_information_frame_page2)
        ui_layout2.setContentsMargins(5, 5, 5, 5)
        ui_layout2.setSpacing(3)
        self.timer_page2 = QtWidgets.QLabel(self.user_information_frame_page2)
        font_timer = QtGui.QFont()
        font_timer.setFamily("Muli Medium")
        font_timer.setPointSize(12)
        self.timer_page2.setFont(font_timer)
        self.timer_page2.setStyleSheet("border: none; color: white;")
        ui_layout2.addWidget(self.timer_page2)
        frame_char_layout2.addWidget(self.user_information_frame_page2)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                            QtWidgets.QSizePolicy.Policy.Minimum)
        frame_char_layout2.addItem(spacerItem1)
        self.character_name_page2 = QtWidgets.QLabel(self.frame_character_2)
        self.character_name_page2.setMinimumHeight(22)
        font_name2 = QtGui.QFont()
        font_name2.setFamily("Muli ExtraBold")
        font_name2.setPointSize(12)
        font_name2.setBold(True)
        font_name2.setWeight(75)
        self.character_name_page2.setFont(font_name2)
        self.character_name_page2.setStyleSheet("color: rgb(255, 255, 255); border: none;")
        self.character_name_page2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout2.addWidget(self.character_name_page2)
        self.character_avatar_label_page2 = QtWidgets.QLabel(self.frame_character_2)
        self.character_avatar_label_page2.setMinimumSize(50, 50)
        self.character_avatar_label_page2.setMaximumSize(50, 50)
        self.character_avatar_label_page2.setStyleSheet("background-color: transparent; border-radius: 25px;")
        self.character_avatar_label_page2.setScaledContents(True)
        self.character_avatar_label_page2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout2.addWidget(self.character_avatar_label_page2)
        layout.addWidget(self.frame_character_2)
        
        self.frame_main_image = QtWidgets.QFrame(page)
        main_layout2 = QtWidgets.QHBoxLayout(self.frame_main_image)
        main_layout2.setContentsMargins(0, 0, 0, 0)
        main_layout2.setSpacing(10)
        self.image_widget = QtWidgets.QWidget(self.frame_main_image)
        self.image_widget.setStyleSheet("background-color: rgb(23, 23, 23); border: 2px solid rgb(42,42,42);")
        image_layout = QtWidgets.QVBoxLayout(self.image_widget)
        image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_label = QtWidgets.QLabel(self.image_widget)
        self.image_label.setStyleSheet("border: none;")
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        image_layout.addWidget(self.image_label)
        main_layout2.addWidget(self.image_widget, 3)
        self.scrollArea_chat_page2 = QtWidgets.QScrollArea(self.frame_main_image)
        self.scrollArea_chat_page2.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page2.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page2.setStyleSheet(
            "background-color: rgb(23, 23, 23); padding: 5px; border-radius: 10px;"
        )
        self.scrollArea_chat_page2.setWidgetResizable(True)
        chat_widget2 = QtWidgets.QWidget()
        self.chat_container_page2 = QtWidgets.QVBoxLayout(chat_widget2)
        self.chat_container_page2.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.chat_container_page2.setSpacing(5)
        self.chat_container_page2.addStretch()
        self.scrollArea_chat_page2.setWidget(chat_widget2)
        main_layout2.addWidget(self.scrollArea_chat_page2, 2)
        layout.addWidget(self.frame_main_image)
        
        self.frame_bar_2 = QtWidgets.QFrame(page)
        self.frame_bar_2.setMaximumHeight(50)
        bar_layout2 = QtWidgets.QHBoxLayout(self.frame_bar_2)
        bar_layout2.setContentsMargins(500, 4, 500, 4)
        bar_layout2.setSpacing(6)
        self.pushButton_hang_up_page2 = QtWidgets.QPushButton(self.frame_bar_2)
        self.pushButton_hang_up_page2.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        )
        font_btn = QtGui.QFont()
        font_btn.setFamily("Muli Medium")
        font_btn.setPointSize(12)
        self.pushButton_hang_up_page2.setFont(font_btn)
        self.pushButton_hang_up_page2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_hang_up_page2.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(172,57,57); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(190,60,60); }"
            "QPushButton:pressed { background-color: rgb(150,50,50); }"
        )
        self.pushButton_hang_up_page2.clicked.connect(self.hangUpReturnMain)
        bar_layout2.addWidget(self.pushButton_hang_up_page2)

        self.pushButton_start_page2 = QtWidgets.QPushButton(self.frame_bar_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        self.pushButton_start_page2.setSizePolicy(sizePolicy)
        self.pushButton_start_page2.setFont(font_btn)
        self.pushButton_start_page2.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_start_page2.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(80,80,80); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(100,100,100); }"
            "QPushButton:pressed { background-color: rgb(60,60,60); }"
        )
        self.pushButton_start_page2.setText("Start")
        bar_layout2.addWidget(self.pushButton_start_page2)
        
        layout.addWidget(self.frame_bar_2)
    
    def setupLive2DPage(self, page):
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        self.frame_character_3 = QtWidgets.QFrame(page)
        self.frame_character_3.setMaximumHeight(60)
        self.frame_character_3.setStyleSheet(
            "#frame_character_3 { border-radius: 10px; border: none; }"
            "#user_name { color: rgb(179,179,179); font: 600 12pt 'Segoe UI'; }"
            "#user_image { border: 1px solid rgb(30,32,33); background-color: rgb(47,48,50); border-radius: 20px; }"
        )
        frame_char_layout3 = QtWidgets.QHBoxLayout(self.frame_character_3)
        frame_char_layout3.setContentsMargins(10, 0, 10, 0)
        frame_char_layout3.setSpacing(10)
        self.user_information_frame_page3 = QtWidgets.QFrame(self.frame_character_3)
        self.user_information_frame_page3.setStyleSheet("border: none;")
        ui_layout3 = QtWidgets.QVBoxLayout(self.user_information_frame_page3)
        ui_layout3.setContentsMargins(5, 5, 5, 5)
        ui_layout3.setSpacing(3)
        self.timer_page3 = QtWidgets.QLabel(self.user_information_frame_page3)
        font_timer3 = QtGui.QFont()
        font_timer3.setFamily("Muli Medium")
        font_timer3.setPointSize(12)
        self.timer_page3.setFont(font_timer3)
        self.timer_page3.setStyleSheet("border: none; color: white;")
        ui_layout3.addWidget(self.timer_page3)
        frame_char_layout3.addWidget(self.user_information_frame_page3)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding,
                                             QtWidgets.QSizePolicy.Policy.Minimum)
        frame_char_layout3.addItem(spacerItem2)
        self.character_name_page3 = QtWidgets.QLabel(self.frame_character_3)
        self.character_name_page3.setMinimumHeight(22)
        font_name3 = QtGui.QFont()
        font_name3.setFamily("Muli ExtraBold")
        font_name3.setPointSize(12)
        font_name3.setBold(True)
        font_name3.setWeight(75)
        self.character_name_page3.setFont(font_name3)
        self.character_name_page3.setStyleSheet("color: rgb(255,255,255); border: none;")
        self.character_name_page3.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout3.addWidget(self.character_name_page3)
        self.character_avatar_label_page3 = QtWidgets.QLabel(self.frame_character_3)
        self.character_avatar_label_page3.setMinimumSize(50, 50)
        self.character_avatar_label_page3.setMaximumSize(50, 50)
        self.character_avatar_label_page3.setStyleSheet("background-color: transparent; border-radius: 25px;")
        self.character_avatar_label_page3.setScaledContents(True)
        self.character_avatar_label_page3.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        frame_char_layout3.addWidget(self.character_avatar_label_page3)
        layout.addWidget(self.frame_character_3)
        
        self.frame_main_live2d = QtWidgets.QFrame(page)
        self.main_layout3 = QtWidgets.QHBoxLayout(self.frame_main_live2d)
        self.main_layout3.setContentsMargins(0, 0, 0, 0)
        self.main_layout3.setSpacing(10)
        self.scrollArea_chat_page3 = QtWidgets.QScrollArea(self.frame_main_live2d)
        self.scrollArea_chat_page3.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page3.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea_chat_page3.setStyleSheet(
            "background-color: rgb(23,23,23); padding: 5px; border-radius: 10px;"
        )
        self.scrollArea_chat_page3.setWidgetResizable(True)
        chat_widget3 = QtWidgets.QWidget()
        self.chat_container_page3 = QtWidgets.QVBoxLayout(chat_widget3)
        self.chat_container_page3.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self.chat_container_page3.setSpacing(5)
        self.chat_container_page3.addStretch()
        self.scrollArea_chat_page3.setWidget(chat_widget3)
        self.main_layout3.addWidget(self.scrollArea_chat_page3, 2)
        layout.addWidget(self.frame_main_live2d)
        
        self.frame_bar_3 = QtWidgets.QFrame(page)
        self.frame_bar_3.setMaximumHeight(50)
        bar_layout3 = QtWidgets.QHBoxLayout(self.frame_bar_3)
        bar_layout3.setContentsMargins(500, 4, 500, 4)
        bar_layout3.setSpacing(6)
        self.pushButton_hang_up_page3 = QtWidgets.QPushButton(self.frame_bar_3)
        self.pushButton_hang_up_page3.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        )
        font_btn = QtGui.QFont()
        font_btn.setFamily("Muli Medium")
        font_btn.setPointSize(12)
        self.pushButton_hang_up_page3.setFont(font_btn)
        self.pushButton_hang_up_page3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_hang_up_page3.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(172,57,57); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(190,60,60); }"
            "QPushButton:pressed { background-color: rgb(150,50,50); }"
        )
        self.pushButton_hang_up_page3.clicked.connect(self.hangUpReturnMain)
        bar_layout3.addWidget(self.pushButton_hang_up_page3)

        self.pushButton_start_page3 = QtWidgets.QPushButton(self.frame_bar_3)
        self.pushButton_start_page3.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Preferred)
        )
        self.pushButton_start_page3.setFont(font_btn)
        self.pushButton_start_page3.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_start_page3.setStyleSheet(
            "QPushButton { color: white; background-color: rgb(80,80,80); border: none; padding: 5px; border-radius: 5px; }"
            "QPushButton:hover { background-color: rgb(100,100,100); }"
            "QPushButton:pressed { background-color: rgb(60,60,60); }"
        )
        self.pushButton_start_page3.setText("Start")
        bar_layout3.addWidget(self.pushButton_start_page3)
        
        layout.addWidget(self.frame_bar_3)
    
    def retranslateUi(self):
        self.setWindowTitle("Soul of Waifu System")
        # Avatar Page
        self.timer_page1.setText("00:00")
        self.character_name_page1.setText("Character name")
        self.pushButton_hang_up_page1.setText("Hang Up")
        self.pushButton_start_page1.setText("Start")
        # Image Expressions Page
        self.timer_page2.setText("00:00")
        self.character_name_page2.setText("Character name")
        self.pushButton_hang_up_page2.setText("Hang Up")
        self.pushButton_start_page2.setText("Start")
        # Live2D Page
        self.timer_page3.setText("00:00")
        self.character_name_page3.setText("Character name")
        self.pushButton_hang_up_page3.setText("Hang Up")
        self.pushButton_start_page3.setText("Start")
    
    def closeEvent(self, event: QtGui.QCloseEvent):
        if self.parent_window is not None:
            self.parent_window.setEnabled(True)
            self.parent_window.show()
        event.accept()

    def hangUpReturnMain(self):
        self.close()
        self.deleteLater()