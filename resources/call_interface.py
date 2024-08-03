import math

from PyQt6.QtWidgets import QWidget
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QBrush, QColor, QRadialGradient, QPainterPath


class Call_MainWindow(object):
    def setupUi(self, MainWindow):
        self.original_geometry = {}
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(531, 691)
        MainWindow.setMinimumSize(QtCore.QSize(531, 691))
        MainWindow.setMaximumSize(QtCore.QSize(531, 691))
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("SoW_Logo.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        MainWindow.setWindowIcon(QtGui.QIcon("./resources/icons/Logotype.ico"))
        MainWindow.setStyleSheet("background-color: rgb(30, 37, 47);")
        MainWindow.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        MainWindow.setWindowTitle("Soul of Waifu - Call Mode")
        MainWindow.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.pulsating_circle_widget = PulsatingCircleWidget()
        self.pulsating_circle_widget.setGeometry(QtCore.QRect(0, -100, 531, 691))
        self.pulsating_circle_widget.setParent(self.centralwidget)

        self.label_speaker = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_speaker.setGeometry(QtCore.QRect(0, 460, 531, 41))
        self.label_speaker.setObjectName("label_speaker")
        self.label_speaker.setText("")
        self.label_speaker.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_speaker.setStyleSheet("background: transparent;")

        self.label = QtWidgets.QLabel(parent=self.centralwidget)
        self.label.setGeometry(QtCore.QRect(190, 90, 151, 150))
        self.label.setStyleSheet("border-radius: 73px;")
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("SoW_Logo.png"))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")
        
        self.label_2 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(0, 270, 531, 31))
        font = QtGui.QFont()
        font.setFamily("Muli Black")
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: rgb(255, 255, 255)")
        self.label_2.setObjectName("label_2")
        self.label_2.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_2.setStyleSheet("background: transparent;")
        
        self.pushButton_Mute = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton_Mute.setGeometry(QtCore.QRect(80, 520, 100, 100))
        self.pushButton_Mute.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_Mute.setStyleSheet("QPushButton {\n"
                                           "background-color:rgb(0, 0, 0);\n"
                                           "border-radius: 50px;\n"
                                           "}\n"
                                           "QPushButton:hover {\n"
                                           "background-color:rgb(50, 50, 50);\n"
                                           "}")
        self.pushButton_Mute.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap("./resources/icons/Mute_Light.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_Mute.setIcon(icon1)
        self.pushButton_Mute.setIconSize(QtCore.QSize(50, 50))
        self.pushButton_Mute.setObjectName("pushButton_Mute")
        
        self.pushButton_HangUp = QtWidgets.QPushButton(parent=self.centralwidget)
        self.pushButton_HangUp.setGeometry(QtCore.QRect(351, 520, 101, 100))
        self.pushButton_HangUp.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.pushButton_HangUp.setStyleSheet("QPushButton {\n"
                                             "background-color:rgb(0, 0, 0);\n"
                                             "border-radius: 50px;\n"
                                             "}\n"
                                             "QPushButton:hover {\n"
                                             "background-color:rgb(50, 50, 50);\n"
                                             "}")
        self.pushButton_HangUp.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap("./resources/icons/HangUp_Red.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        self.pushButton_HangUp.setIcon(icon2)
        self.pushButton_HangUp.setIconSize(QtCore.QSize(100, 100))
        self.pushButton_HangUp.setObjectName("pushButton_HangUp")

        self.label_3 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(69, 630, 131, 21))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(12)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_3.setObjectName("label_3")
        
        self.label_4 = QtWidgets.QLabel(parent=self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(353, 630, 141, 21))
        font = QtGui.QFont()
        font.setFamily("Muli")
        font.setPointSize(12)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_4.setObjectName("label_4")
        
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        
        self.label_2.setText("Call with Character")
        self.label_3.setText("Mute microphone")
        self.label_4.setText("Hang up call")
        
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

class PulsatingCircleWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.color_phase = 0
        self.audio_amplitude = 0
        self.smooth_amplitude = 0
        self.base_radius = min(self.width(), self.height()) / 3

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(20)
        self.painter = QPainter()

    def update_animation(self):
        base_speed = 0.2
        amplitude_speed_factor = 0.1
        self.angle += base_speed + amplitude_speed_factor * self.smooth_amplitude
        self.color_phase += 0.005
        if self.color_phase > 1:
            self.color_phase = 0
        self.update()

    def interpolate_color(self, phase):
        light_blue = QColor(64, 140, 220)
        dark_blue = QColor(64, 111, 186)

        if phase < 0.5:
            phase = phase * 2
            r = int(light_blue.red() + (dark_blue.red() - light_blue.red()) * phase)
            g = int(light_blue.green() + (dark_blue.green() - light_blue.green()) * phase)
            b = int(light_blue.blue() + (dark_blue.blue() - light_blue.blue()) * phase)
            a = 127
        else:
            phase = (phase - 0.5) * 2
            r = int(dark_blue.red() + (light_blue.red() - dark_blue.red()) * phase)
            g = int(dark_blue.green() + (light_blue.green() - dark_blue.green()) * phase)
            b = int(dark_blue.blue() + (light_blue.blue() - dark_blue.blue()) * phase)
            a = 127

        return QColor(r, g, b, a)

    def paintEvent(self, event):
        self.painter.begin(self)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        center = QPointF(self.width() / 2, self.height() / 2)
        pulsate_radius = self.base_radius + self.smooth_amplitude * 5

        self.draw_glow(self.painter, center, pulsate_radius)

        current_color = self.interpolate_color(self.color_phase)
        brush = QBrush(current_color)
        self.painter.setBrush(brush)
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.drawEllipse(center, pulsate_radius, pulsate_radius)

        self.draw_waves_on_edge(self.painter, center, pulsate_radius)
        self.painter.end()

    def draw_glow(self, painter, center, radius):
        num_layers = 5
        for i in range(num_layers):
            glow_radius = radius * (1.2 + 0.1 * i)
            alpha = 100 - (20 * i)
            glow_gradient = QRadialGradient(center, glow_radius)
            glow_gradient.setColorAt(0, QColor(255, 255, 255, alpha))
            glow_gradient.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, glow_radius, glow_radius)

    def draw_waves_on_edge(self, painter, center, radius):
        wave_count = 8
        wave_width = 6
        for i in range(wave_count):
            wave_radius = radius + i * wave_width
            wave_angle = self.angle * (i + 1) / wave_count
            wave_color = self.interpolate_color(self.color_phase)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(wave_color))
            path = self.create_wave_path(center, wave_radius, wave_angle)
            painter.drawPath(path)

    def create_wave_path(self, center, radius, angle):
        path = QPainterPath()
        num_points = 80
        smooth_factor = 0.7
        for i in range(num_points):
            theta = 2 * math.pi * i / num_points
            wave_effect = (self.smooth_amplitude * 0.5 + 10) * smooth_factor * math.sin(4 * theta + angle)
            x = center.x() + (radius + wave_effect) * math.cos(theta)
            y = center.y() + (radius + wave_effect) * math.sin(theta)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        return path