import math
import random

from PyQt6 import QtCore, QtGui, QtWidgets, QtOpenGLWidgets
from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QLinearGradient, QPen

class C:
    # backgrounds
    ROOT        = "#08080e"
    PANEL       = "#0c0c0c"
    CARD        = "rgba(16,16,16,220)"
    CARD_BORDER = "rgba(255,255,255,10)"
    TITLEBAR    = "rgba(13,13,24,0)"

    # text
    T_PRIMARY   = "#e8e8f0"
    T_SECONDARY = "rgba(160,160,188,200)"
    T_MUTED     = "rgba(100,100,128,190)"

    # accent
    STOPPED     = QColor(75,  75,  90)
    LISTENING   = QColor(52,  211, 153)
    PROCESSING  = QColor(251, 191, 36)
    SPEAKING    = QColor(96,  165, 250)

    RING = {
        "STOPPED":
            "background:transparent;"
            "border:2px solid rgba(80,80,100,110);"
            "border-radius:32px;",
        "LISTENING":
            "background:transparent;"
            "border:2px solid rgba(52,211,153,190);"
            "border-radius:32px;",
        "PROCESSING":
            "background:transparent;"
            "border:2px solid rgba(251,191,36,190);"
            "border-radius:32px;",
        "SPEAKING":
            "background:transparent;"
            "border:2px solid rgba(96,165,250,190);"
            "border-radius:32px;",
    }

    BTN_IDLE = (
        "QPushButton#pushButton_play{"
        "background:qradialgradient(cx:0.5,cy:0.5,radius:0.5,"
        "fx:0.5,fy:0.5,stop:0 rgba(52,211,153,230),"
        "stop:1 rgba(16,185,129,200));"
        "border:1px solid rgba(52,211,153,120);"
        "border-radius:27px;}"
        "QPushButton#pushButton_play:hover{"
        "background:rgba(52,211,153,255);"
        "border:1px solid rgba(52,211,153,200);}"
        "QPushButton#pushButton_play:pressed{"
        "background:rgba(16,185,129,255);}"
    )
    BTN_ACTIVE = (
        "QPushButton#pushButton_play{"
        "background:qradialgradient(cx:0.5,cy:0.5,radius:0.5,"
        "fx:0.5,fy:0.5,stop:0 rgba(239,68,68,230),"
        "stop:1 rgba(185,28,28,200));"
        "border:1px solid rgba(239,68,68,120);"
        "border-radius:27px;}"
        "QPushButton#pushButton_play:hover{"
        "background:rgba(239,68,68,255);"
        "border:1px solid rgba(239,68,68,200);}"
        "QPushButton#pushButton_play:pressed{"
        "background:rgba(185,28,28,255);}"
    )


def _card_css(name: str, radius: int = 14) -> str:
    return (
        f"QFrame#{name}{{"
        f"background-color:{C.CARD};"
        f"border:1px solid {C.CARD_BORDER};"
        f"border-radius:{radius}px;}}"
    )


def _font(family: str, size: int) -> QFont:
    f = QFont(family, size)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def _lbl(text: str, family: str, size: int, color: str,
         parent=None) -> QtWidgets.QLabel:
    w = QtWidgets.QLabel(text, parent)
    w.setFont(_font(family, size))
    w.setStyleSheet(f"color:{color};background:transparent;border:none;")
    return w


def _wm_btn(icon: str, icon_sz: int, hover: str,
            parent=None) -> QtWidgets.QPushButton:
    css = (
        "QPushButton{background:rgba(255,255,255,0);border:none;border-radius:7px;}"
        f"QPushButton:hover{{background:{hover};}}"
        "QPushButton:pressed{background:rgba(255,255,255,4);}"
    )
    b = QtWidgets.QPushButton(parent)
    b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    b.setFixedSize(28, 28)
    b.setCursor(QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
    b.setStyleSheet(css)
    ico = QtGui.QIcon()
    ico.addPixmap(QtGui.QPixmap(icon))
    b.setIcon(ico)
    b.setIconSize(QtCore.QSize(icon_sz, icon_sz))
    return b


class WaveformWidget(QtWidgets.QWidget):
    N = 32

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._state = "STOPPED"
        self._phase = 0.0
        self._bars  = [0.05] * self.N
        self._live_volume = 0.0
        self._volume_decay = 0.82
        t = QtCore.QTimer(self)
        t.timeout.connect(self._tick)
        t.start(52)
        self._timer = t

    def set_state(self, s: str):
        self._state = s
    
    def push_volume(self, value: float):
        self._live_volume = value

    def _tick(self):
        self._phase += 0.20
        self._live_volume *= self._volume_decay

        p, n = self._phase, self.N
        if self._state == "LISTENING":
            for i in range(self.N):
                base = math.sin(self._phase + i * 0.44) * 0.12 + 0.14
                live = self._live_volume * math.sin(self._phase * 3.1 + i * 0.9) * 0.6
                self._bars[i] = max(0.05, base + abs(live))
        elif self._state == "SPEAKING":
            for i in range(self.N):
                base = math.sin(self._phase * 1.7 + i * 0.72) * 0.44 + 0.50
                noise = random.uniform(-0.05, 0.05)
                self._bars[i] = max(0.08, min(1.0, base + noise))
        elif self._state == "PROCESSING":
            cx = n/2.0; pulse = math.sin(p*2.3)*0.5+0.5
            self._bars = [max(0.04, pulse*(1-(abs(i-cx)/cx)**1.3)*0.88)
                          for i in range(n)]
        else:
            self._bars = [max(0.03, 0.05+math.sin(p*0.22+i*0.6)*0.013)
                          for i in range(n)]
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, n = self.width(), self.height(), self.N
        bw  = 2.8
        gap = (w - n*bw) / (n+1)
        cols = {
            "LISTENING":  C.LISTENING,
            "SPEAKING":   C.SPEAKING,
            "PROCESSING": C.PROCESSING,
            "STOPPED":    C.STOPPED,
        }
        base = cols.get(self._state, C.STOPPED)
        p.setPen(Qt.PenStyle.NoPen)
        for i, v in enumerate(self._bars):
            x  = gap + i*(bw+gap)
            bh = max(3.0, v*(h-6))
            y  = (h-bh)/2.0
            c  = QColor(base)
            c.setAlpha(min(255, int(100 + v*155)))
            p.setBrush(QBrush(c))
            p.drawRoundedRect(QtCore.QRectF(x, y, bw, bh), 1.4, 1.4)
        p.end()


class StateIndicatorLabel(QtWidgets.QLabel):
    _MAP = {
        "46, 204, 113": "LISTENING",
        "241, 196, 15": "PROCESSING",
        "52, 152, 219": "SPEAKING",
        "80, 80, 80":   "STOPPED",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ring = self._wave = self._btn = None

    def link(self, ring, wave, btn):
        self._ring = ring; self._wave = wave; self._btn = btn

    def setStyleSheet(self, css):
        super().setStyleSheet(css)
        st = next((v for k,v in self._MAP.items() if k in css), "STOPPED")
        if self._ring:  self._ring.setStyleSheet(C.RING.get(st, C.RING["STOPPED"]))
        if self._wave:  self._wave.set_state(st)
        if self._btn:
            self._btn.setStyleSheet(C.BTN_IDLE if st == "STOPPED" else C.BTN_ACTIVE)


class CallTimerLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__("00:00", parent)
        self._s = 0
        self._t = QtCore.QTimer(self)
        self._t.timeout.connect(self._tick)

    def start(self):
        self._s = 0; self.setText("00:00"); self._t.start(1000)

    def stop(self):
        self._t.stop()

    def _tick(self):
        self._s += 1
        m, s = divmod(self._s, 60)
        self.setText(f"{m:02d}:{s:02d}")


class SOW_System(QMainWindow):
    """
    Soul of Waifu System — Living Call Interface
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Soul of Waifu System")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag = False
        self._drag_off = None
        self.setupUi()

    def setupUi(self):
        self.setObjectName("SOW_System")
        self.resize(1140, 740)
        ico = QtGui.QIcon()
        ico.addPixmap(QtGui.QPixmap("app/gui/icons/logotype.ico"))
        self.setWindowIcon(ico)
        self.setStyleSheet("border:none;background:transparent;")

        self.centralwidget = QtWidgets.QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setStyleSheet(f"""
            QWidget#centralwidget {{
                background-color: {C.ROOT};
                border: 1px solid rgba(255,255,255,14);
                border-radius: 16px;
            }}
        """)
        self.setCentralWidget(self.centralwidget)

        self._root = QtWidgets.QHBoxLayout(self.centralwidget)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._build_left_panel()
        self._build_model_area()

        self.voice_indicator.link(
            ring=self.avatar_ring,
            wave=self.waveform_widget,
            btn=self.pushButton_play,
        )

        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.close_app_btn.clicked.connect(self.close)
        self._build_grips()

    #  LEFT PANEL
    # =========================================================================
    def _build_left_panel(self):
        self.left_panel = QtWidgets.QWidget()
        self.left_panel.setObjectName("left_panel")
        self.left_panel.setFixedWidth(345)
        self.left_panel.setStyleSheet(f"""
            QWidget#left_panel {{
                background-color: {C.PANEL};
                border-right: 1px solid rgba(255,255,255,8);
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
            }}
        """)
        col = QtWidgets.QVBoxLayout(self.left_panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)

        self._build_titlebar(col)

        inner = QtWidgets.QWidget()
        inner.setStyleSheet("background:transparent;")
        cards = QtWidgets.QVBoxLayout(inner)
        cards.setContentsMargins(16, 16, 16, 12)
        cards.setSpacing(10)

        self._build_char_card(cards)
        self._build_status_row(cards)
        self._build_waveform_card(cards)
        
        self._build_chat_section(cards)

        col.addWidget(inner, stretch=1)
        self._build_mic_bar(col)
        self._root.addWidget(self.left_panel)

    def _build_chat_section(self, parent):
        hdr = _lbl("Conversation", "Inter Tight Medium", 10, C.T_MUTED)
        hdr.setContentsMargins(4, 0, 0, 0)
        parent.addWidget(hdr)

        self.scrollArea_chat = QtWidgets.QScrollArea()
        self.scrollArea_chat.setObjectName("scrollArea_chat")
        self.scrollArea_chat.setWidgetResizable(True)
        self.scrollArea_chat.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scrollArea_chat.setStyleSheet(f"""
            QScrollArea{{
                background-color:{C.CARD};
                border:1px solid {C.CARD_BORDER};
                border-radius:14px;
            }}
            QScrollBar:vertical{{
                width:4px;background:transparent;margin:3px 2px;
            }}
            QScrollBar::handle:vertical{{
                background:rgba(255,255,255,28);
                border-radius:2px;min-height:22px;
            }}
            QScrollBar::handle:vertical:hover{{background:rgba(255,255,255,48);}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}
            QScrollBar::sub-page:vertical,QScrollBar::add-page:vertical{{background:none;}}
        """)

        self.scrollAreaWidgetContents_chat = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_chat.setObjectName("scrollAreaWidgetContents_chat")
        self.scrollAreaWidgetContents_chat.setStyleSheet("background:transparent;border:none;")
        self.scrollArea_chat.setWidget(self.scrollAreaWidgetContents_chat)
        
        parent.addWidget(self.scrollArea_chat, stretch=1)

    def _build_titlebar(self, parent):
        bar = QtWidgets.QFrame()
        bar.setObjectName("titlebar")
        bar.setFixedHeight(48)
        bar.setStyleSheet("""
            QFrame#titlebar{
                background:transparent;
                border-bottom:1px solid rgba(255,255,255,7);
            }
        """)
        self._tb = bar

        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 10, 0)
        row.setSpacing(8)

        logo = QtWidgets.QLabel()
        logo.setFixedSize(15, 15)
        logo.setStyleSheet("background:transparent;border:none;")
        px = QtGui.QPixmap("app/gui/icons/logotype.ico")
        if not px.isNull():
            logo.setPixmap(px.scaled(15, 15,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        row.addWidget(logo)

        self.title_label = _lbl(
            "Soul of Waifu System",
            "Inter Tight Medium", 10,
            "rgba(160,160,192,140)",
        )
        row.addWidget(self.title_label)
        row.addStretch()

        self.minimize_btn  = _wm_btn("app/gui/icons/minimize.png", 12,
                                     "rgba(255,255,255,11)")
        self.maximize_btn  = _wm_btn("app/gui/icons/maximize.png",  11,
                                     "rgba(255,255,255,11)")
        self.close_app_btn = _wm_btn("app/gui/icons/close.png",     11,
                                     "rgba(215,30,30,200)")
        for b in (self.minimize_btn, self.maximize_btn, self.close_app_btn):
            row.addWidget(b)
        parent.addWidget(bar)

    def _build_char_card(self, parent):
        card = QtWidgets.QFrame()
        card.setObjectName("char_card")
        card.setStyleSheet(f"""
            QFrame#char_card{{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(22,22,22,220),
                    stop:1 rgba(12,12,12,220));
                border:1px solid rgba(255,255,255,10);
                border-radius:16px;
            }}
        """)
        row = QtWidgets.QHBoxLayout(card)
        row.setContentsMargins(16, 16, 16, 16)
        row.setSpacing(14)

        wrap = QtWidgets.QWidget()
        wrap.setFixedSize(64, 64)
        wrap.setStyleSheet("background:transparent;")

        self.character_avatar_label = QtWidgets.QLabel(parent=wrap)
        self.character_avatar_label.setObjectName("character_avatar_label")
        self.character_avatar_label.setGeometry(5, 5, 54, 54)
        self.character_avatar_label.setStyleSheet(
            "background:#1e1e38;border-radius:27px;border:none;"
        )
        self.character_avatar_label.setScaledContents(True)
        self.character_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.avatar_ring = QtWidgets.QLabel(parent=wrap)
        self.avatar_ring.setObjectName("avatar_ring")
        self.avatar_ring.setGeometry(0, 0, 64, 64)
        self.avatar_ring.setStyleSheet(C.RING["STOPPED"])
        self.avatar_ring.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.avatar_ring.raise_()
        row.addWidget(wrap)

        info = QtWidgets.QVBoxLayout()
        info.setSpacing(4)
        info.setContentsMargins(0, 2, 0, 2)

        self.character_name_label = _lbl("—", "Inter Tight SemiBold", 14, C.T_PRIMARY)
        info.addWidget(self.character_name_label)

        self.character_description_label = _lbl("—", "Inter Tight Medium", 10, C.T_SECONDARY)
        info.addWidget(self.character_description_label)
        info.addStretch()

        row.addLayout(info)
        row.addStretch()
        parent.addWidget(card)

    def _build_status_row(self, parent):
        frame = QtWidgets.QFrame()
        frame.setObjectName("status_frame")
        frame.setFixedHeight(64)
        frame.setStyleSheet(_card_css("status_frame", 14))

        row = QtWidgets.QHBoxLayout(frame)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(8) 

        self.voice_indicator = StateIndicatorLabel()
        self.voice_indicator.setObjectName("voice_indicator")
        self.voice_indicator.setFixedSize(10, 10)
        self.voice_indicator.setStyleSheet(
            "background-color:rgb(80,80,80);border-radius:5px;"
        )
        row.addWidget(self.voice_indicator, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)

        text_container = QtWidgets.QFrame()
        text_container.setObjectName("text_container")
        text_container.setStyleSheet("background:transparent;border:none;")
        
        vb = QtWidgets.QVBoxLayout(text_container)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(1)
        vb.addWidget(_lbl("Status", "Inter Tight Medium", 9, C.T_MUTED))

        self.status_label = _lbl("Paused", "Inter Tight SemiBold", 13, C.T_SECONDARY)
        vb.addWidget(self.status_label)
        
        row.addWidget(text_container, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        row.addStretch()

        self.call_timer = CallTimerLabel()
        self.call_timer.setFont(_font("Inter Tight Medium", 11))
        self.call_timer.setStyleSheet(f"color:{C.T_MUTED};background:transparent;border:none;")
        row.addWidget(self.call_timer, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        parent.addWidget(frame)

    def _build_waveform_card(self, parent):
        frame = QtWidgets.QFrame()
        frame.setObjectName("wave_frame")
        frame.setFixedHeight(78)
        frame.setStyleSheet(_card_css("wave_frame", 14))

        col = QtWidgets.QVBoxLayout(frame)
        col.setContentsMargins(14, 10, 14, 10)
        col.setSpacing(4)

        col.addWidget(_lbl("Voice activity", "Inter Tight Medium", 9, C.T_MUTED))

        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setStyleSheet("background:transparent;")
        col.addWidget(self.waveform_widget)
        parent.addWidget(frame)

    def _build_mic_bar(self, parent):
        bar = QtWidgets.QFrame()
        bar.setObjectName("mic_bar")
        bar.setFixedHeight(82)
        bar.setStyleSheet("""
            QFrame#mic_bar{
                background:transparent;
                border-top:1px solid rgba(255,255,255,7);
                border-bottom-left-radius:16px;
            }
        """)
        row = QtWidgets.QHBoxLayout(bar)
        row.setContentsMargins(20, 0, 20, 0)
        row.setSpacing(14)

        text_container = QtWidgets.QFrame()
        text_container.setObjectName("text_container")
        text_container.setStyleSheet("background:transparent;border:none;")
        
        lv = QtWidgets.QVBoxLayout(text_container)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(3)
        lv.addWidget(_lbl("Voice call", "Inter Tight SemiBold", 13, C.T_PRIMARY))
        lv.addWidget(_lbl("Tap to start or stop", "Inter Tight Medium", 9, C.T_MUTED))
        
        row.addWidget(text_container, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        row.addStretch()

        self.pushButton_play = QtWidgets.QPushButton()
        self.pushButton_play.setObjectName("pushButton_play")
        self.pushButton_play.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.pushButton_play.setFixedSize(54, 54)
        self.pushButton_play.setCursor(
            QtGui.QCursor(Qt.CursorShape.PointingHandCursor))
        self.pushButton_play.setStyleSheet(C.BTN_IDLE)
        ico = QtGui.QIcon()
        ico.addPixmap(QtGui.QPixmap("app/gui/icons/play.png"))
        self.pushButton_play.setIcon(ico)
        self.pushButton_play.setIconSize(QtCore.QSize(22, 22))

        row.addWidget(self.pushButton_play, 0, QtCore.Qt.AlignmentFlag.AlignVCenter)
        
        parent.addWidget(bar)

    def _build_model_area(self):
        mroot = QtWidgets.QWidget()
        mroot.setObjectName("model_root")
        mroot.setStyleSheet("background:transparent;")

        lo = QtWidgets.QVBoxLayout(mroot)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)

        self.stackedWidget_main = QtWidgets.QStackedWidget(parent=mroot)
        self.stackedWidget_main.setObjectName("stackedWidget_main")
        self.stackedWidget_main.setStyleSheet("background:transparent;")
        lo.addWidget(self.stackedWidget_main)

        self.page_avatar = QtWidgets.QWidget()
        self.page_avatar.setObjectName("page_avatar")
        self.page_avatar.setStyleSheet("background:transparent;")

        _lo = QtWidgets.QVBoxLayout(self.page_avatar)
        _lo.setContentsMargins(0, 0, 0, 0)
        _lo.setSpacing(0)

        self.avatar_widget = QtWidgets.QWidget(parent=self.page_avatar)
        self.avatar_widget.setObjectName("avatar_widget")
        self.avatar_widget.setStyleSheet("background:transparent;")

        _lo2 = QtWidgets.QVBoxLayout(self.avatar_widget)
        _lo2.setContentsMargins(0, 0, 0, 0)
        _lo2.setSpacing(0)

        self.avatar_label = QtWidgets.QLabel(parent=self.avatar_widget)
        self.avatar_label.setObjectName("avatar_label")
        self.avatar_label.setStyleSheet("background:transparent;border:none;")
        self.avatar_label.setText("")
        self.avatar_label.setScaledContents(False)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        _lo2.addWidget(self.avatar_label)
        _lo.addWidget(self.avatar_widget)
        self.stackedWidget_main.addWidget(self.page_avatar)

        # ── page: Live2D
        self.page_live2d_model = QtWidgets.QWidget()
        self.page_live2d_model.setObjectName("page_live2d_model")
        self.page_live2d_model.setStyleSheet("background:transparent;")

        _lo = QtWidgets.QVBoxLayout(self.page_live2d_model)
        _lo.setContentsMargins(0, 0, 0, 0)
        _lo.setSpacing(0)

        self.live2d_widget = QtWidgets.QWidget(parent=self.page_live2d_model)
        self.live2d_widget.setObjectName("live2d_widget")
        self.live2d_widget.setStyleSheet("background:transparent;border:none;")

        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.live2d_widget)
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_5.setSpacing(0)

        self.live2d_openGL_widget = QtOpenGLWidgets.QOpenGLWidget(
            parent=self.live2d_widget)
        self.live2d_openGL_widget.setObjectName("live2d_openGL_widget")
        self.live2d_openGL_widget.setStyleSheet(
            "background:transparent;border:none;")

        self.verticalLayout_5.addWidget(self.live2d_openGL_widget)
        _lo.addWidget(self.live2d_widget)
        self.stackedWidget_main.addWidget(self.page_live2d_model)

        # ── page: VRM
        self.page_vrm_model = QtWidgets.QWidget()
        self.page_vrm_model.setObjectName("page_vrm_model")
        self.page_vrm_model.setStyleSheet("background:transparent;")

        _lo = QtWidgets.QVBoxLayout(self.page_vrm_model)
        _lo.setContentsMargins(0, 0, 0, 0)
        _lo.setSpacing(0)

        self.vrm_widget = QtWidgets.QWidget(parent=self.page_vrm_model)
        self.vrm_widget.setObjectName("vrm_widget")
        self.vrm_widget.setStyleSheet("background:transparent;border:none;")

        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.vrm_widget)
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_6.setSpacing(0)

        _lo.addWidget(self.vrm_widget)
        self.stackedWidget_main.addWidget(self.page_vrm_model)

        self._root.addWidget(mroot, stretch=1)

    def _build_grips(self):
        self._grips = []
        for cur in [Qt.CursorShape.SizeFDiagCursor,
                    Qt.CursorShape.SizeBDiagCursor,
                    Qt.CursorShape.SizeBDiagCursor,
                    Qt.CursorShape.SizeFDiagCursor]:
            g = QtWidgets.QSizeGrip(self.centralwidget)
            g.resize(10, 10)
            g.setStyleSheet("background:transparent;border:none;")
            g.setCursor(QtGui.QCursor(cur))
            g.show()
            g.raise_()
            self._grips.append(g)
        QtCore.QTimer.singleShot(0, self._repos_grips)

    def _repos_grips(self):
        if not getattr(self, '_grips', None):
            return
        w, h, s = self.centralwidget.width(), self.centralwidget.height(), 10
        for g, (x, y) in zip(self._grips,
                              [(0,0),(0,h-s),(w-s,0),(w-s,h-s)]):
            g.move(x, y)

    def start_call_timer(self):
        self.call_timer.start()

    def stop_call_timer(self):
        self.call_timer.stop()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._repos_grips()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if e.pos().y() <= self._tb.height() and e.pos().x() <= self.left_panel.width():
                self._drag = True
                self._drag_off = e.pos()

    def mouseMoveEvent(self, e):
        if self._drag and self._drag_off:
            self.move(self.pos() + e.pos() - self._drag_off)

    def mouseReleaseEvent(self, e):
        self._drag = False

    def _toggle_maximize(self):
        if self.isMaximized():
            ico = QtGui.QIcon()
            ico.addPixmap(QtGui.QPixmap("app/gui/icons/maximize.png"))
            self.maximize_btn.setIcon(ico)
            self.showNormal()
        else:
            ico = QtGui.QIcon()
            ico.addPixmap(QtGui.QPixmap("app/gui/icons/maximize_minimize.png"))
            self.maximize_btn.setIcon(ico)
            self.showMaximized()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.showNormal() if self.isMaximized() else self.close()
        elif e.key() == Qt.Key.Key_F11:
            self._toggle_maximize()
        super().keyPressEvent(e)

    def closeEvent(self, e: QtGui.QCloseEvent):
        if hasattr(self, 'waveform_widget'):
            self.waveform_widget._timer.stop()
        if hasattr(self, 'call_timer'):
            self.call_timer.stop()
        app = QtWidgets.QApplication.instance()
        if hasattr(app, 'main_window'):
            mw = app.main_window
            mw.setVisible(True); mw.raise_(); mw.activateWindow()
        e.accept()
