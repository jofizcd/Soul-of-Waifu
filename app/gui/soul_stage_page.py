import os
import re
import copy
import json
import uuid
import yaml
import random
import datetime

from typing import Optional

from pathlib import Path
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QPainterPath, QIcon
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QStackedWidget,
    QLineEdit, QTextEdit, QComboBox, QFileDialog, QMessageBox,
)

from app.gui.custom_widgets import SowSelectDialog, SowInputDialog, SowConfirmDialog, SceneFolderCard, sow_toast

SOUL_STAGE_DIR = Path(".soul_stage")
SCENES_FILE    = SOUL_STAGE_DIR / "scenes.json"
TRANSLATIONS_DIR = Path("app/translations")
SOUL_STAGE_DIR.mkdir(exist_ok=True)
if not SCENES_FILE.exists():
    SCENES_FILE.write_text(json.dumps({"scenes": {}}, ensure_ascii=False, indent=2))

COMBO_STYLE = """
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

def _load_translations() -> dict:
    """Loads translation YAML based on program language setting."""
    try:
        from app.configuration import configuration
        lang = configuration.ConfigurationSettings().get_main_setting("program_language") or 0
    except Exception:
        lang = 0
    lang_code = {0: "en", 1: "ru"}.get(int(lang), "en")
    path = f"app/translations/{lang_code}.yaml"
    if os.path.exists(path) and yaml:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}

def _load_scenes() -> dict:
    try:
        return json.loads(SCENES_FILE.read_text("utf-8"))
    except Exception:
        return {"scenes": {}}

def _save_scenes(data: dict):
    SCENES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

def _get_scene_groups() -> dict:
    data = _load_scenes()
    groups = data.get("scene_groups", {})
    existing_scenes = set(data.get("scenes", {}).keys())
    dirty = False
    clean_groups = {}
    for g_name, members in groups.items():
        if isinstance(members, list):
            valid = [m for m in members if m in existing_scenes]
            if len(valid) != len(members):
                dirty = True
            clean_groups[g_name] = valid
        else:
            clean_groups[g_name] = []
    if dirty:
        data["scene_groups"] = clean_groups
        _save_scenes(data)
    return clean_groups

def _save_scene_groups(groups: dict):
    data = _load_scenes()
    data["scene_groups"] = groups
    _save_scenes(data)

def _get_grouped_scenes() -> set:
    groups = _get_scene_groups()
    grouped = set()
    for members in groups.values():
        grouped.update(members)
    return grouped

def _get_assets(folder: str, exts: list) -> list:
    try:
        return ["None"] + sorted(
            f for f in os.listdir(folder)
            if any(f.lower().endswith(e) for e in exts)
        )
    except Exception:
        return ["None"]

def append_to_scene_log(scene_id: str, entries: list):
    d = _load_scenes()
    if scene_id not in d["scenes"]:
        return
    log = d["scenes"][scene_id].setdefault("chat_log", [])
    log.extend(entries)
    d["scenes"][scene_id]["chat_log"] = log[-400:]
    _save_scenes(d)

def _get_char_avatar_pixmap(char_name: str) -> QPixmap:
    try:
        from app.configuration import configuration
        cfg = configuration.ConfigurationCharacters()
        data = cfg.load_configuration()
        c_info = data.get("character_list", {}).get(char_name, {})
        avatar_path = c_info.get("character_avatar", "")
        if avatar_path:
            px = QPixmap(avatar_path)
            if not px.isNull():
                return px
    except Exception:
        pass
    return QPixmap("app/gui/icons/logotype.png")

def _round_pixmap(px: QPixmap, size: int) -> QPixmap:
    scaled = px.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                       Qt.TransformationMode.SmoothTransformation)
    cx = (scaled.width()  - size) // 2
    cy = (scaled.height() - size) // 2
    cropped = scaled.copy(cx, cy, size, size)
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result

def _rpg_divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(255,255,255,0),
                stop:0.3 rgba(255,255,255,0.12),
                stop:0.7 rgba(255,255,255,0.12),
                stop:1 rgba(255,255,255,0));
            border: none;
        }
    """)
    return line

def _rpg_primary_btn(text: str, color_rgb: str = "80,120,255") -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(_font("Inter Tight SemiBold", 12))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setFixedHeight(38)
    r, g, b = color_rgb.split(",")
    btn.setStyleSheet(f"""
        QPushButton {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba({r},{g},{b},0.75),
                stop:1 rgba({r},{g},{b},0.55));
            border: 1px solid rgba({r},{g},{b},0.50);
            border-top: 1px solid rgba({r},{g},{b},0.80);
            border-radius: 10px;
            color: white;
            padding: 0 22px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba({r},{g},{b},0.90),
                stop:1 rgba({r},{g},{b},0.70));
            border-color: rgba({r},{g},{b},0.70);
        }}
        QPushButton:pressed {{ background: rgba({r},{g},{b},0.45); }}
        QPushButton:disabled {{ background: rgba(60,60,70,0.40); color: rgba(255,255,255,0.25); border-color: transparent; }}
    """)
    return btn


def _rpg_ghost_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFont(_font("Inter Tight Medium", 12))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    btn.setFixedHeight(38)
    btn.setStyleSheet("""
        QPushButton {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 10px;
            color: rgba(200,200,210,0.80);
            padding: 0 18px;
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.09);
            border-color: rgba(255,255,255,0.22);
            color: #fff;
        }
        QPushButton:pressed { background: rgba(255,255,255,0.14); }
    """)
    return btn

def _font(family="Inter Tight Medium", size=12, bold=False, italic=False) -> QFont:
    f = QFont(family, size)
    if bold:   f.setWeight(QFont.Weight.Bold)
    if italic: f.setStyle(QFont.Style.StyleItalic)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


def _shadow(blur=20, y=6, alpha=100) -> QtWidgets.QGraphicsDropShadowEffect:
    s = QtWidgets.QGraphicsDropShadowEffect()
    s.setBlurRadius(blur); s.setOffset(0, y); s.setColor(QColor(0, 0, 0, alpha))
    return s

SCROLLBAR = """
    QScrollArea { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 4px; margin: 0; }
    QScrollBar::handle:vertical {
        background: rgba(255,255,255,0.15); border-radius: 2px; min-height: 28px;
    }
    QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.30); }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QToolTip {
        background-color: rgba(25, 25, 30, 0.95); 
        color: #E0E0E0; 
        border: 1px solid rgba(255, 255, 255, 0.15); 
        border-radius: 6px; 
        padding: 6px 10px; font-size: 13px; 
        font-family: 'Inter Tight SemiBold';
    }
"""

INPUT = """
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-top: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 10px;
        color: rgba(240, 240, 240, 0.95);
        font-family: 'Inter Tight Medium'; 
        font-size: 13px;
        padding: 8px 14px;
        padding-right: 28px;
        selection-background-color: rgba(255, 255, 255, 0.15);
    }

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid rgba(255, 255, 255, 0.25);
        background: rgba(255, 255, 255, 0.05);
    }

    QComboBox::drop-down { border: none; width: 30px; }
    QComboBox::down-arrow { image: url(app/gui/icons/arrow_down.png); width: 12px; height: 12px; }
    QComboBox QAbstractItemView {
        background: #0d0d0f; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px; 
        color: rgba(240, 240, 240, 0.95);
        selection-background-color: rgba(255, 255, 255, 0.1); 
        padding: 4px;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 22px;
        height: 16px;
        background: transparent;
        border: none;
        margin-top: 3px;
        margin-right: 4px;
        border-top-right-radius: 8px;
    }

    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 22px;
        height: 16px;
        background: transparent;
        border: none;
        margin-bottom: 3px;
        margin-right: 4px;
        border-bottom-right-radius: 8px;
    }

    QSpinBox::up-button:hover, QSpinBox::down-button:hover,
    QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
        background: rgba(255, 255, 255, 0.08);
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: url(app/gui/icons/up_arrow.png);
        width: 10px; 
        height: 10px;
    }

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        image: url(app/gui/icons/down_arrow.png);
        width: 10px; 
        height: 10px;
    }
    QToolTip {
        background-color: rgba(25, 25, 30, 0.95); 
        color: #E0E0E0; 
        border: 1px solid rgba(255, 255, 255, 0.15); 
        border-radius: 6px; 
        padding: 6px 10px; font-size: 13px; 
        font-family: 'Inter Tight SemiBold';
    }
"""

CB_STYLE = """
    QCheckBox { color: rgba(200,200,200,0.9); spacing: 10px; }
    QCheckBox::indicator {
        width: 18px; height: 18px; border-radius: 5px;
        border: 1px solid rgba(255,255,255,0.15); background: rgba(0,0,0,0.4);
    }
    QCheckBox::indicator:checked {
        background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4);
    }
    QToolTip {
        background-color: rgba(25, 25, 30, 0.95); 
        color: #E0E0E0; 
        border: 1px solid rgba(255, 255, 255, 0.15); 
        border-radius: 6px; 
        padding: 6px 10px; font-size: 13px; 
        font-family: 'Inter Tight SemiBold';
    }
"""

class _Btn(QPushButton):
    def __init__(self, text="", primary=False, danger=False, dim=False, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFont(_font("Inter Tight SemiBold", 11))
        
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(75, 184, 255, 0.08);
                    border: 1px solid rgba(75, 184, 255, 0.25);
                    border-top: 1px solid rgba(75, 184, 255, 0.45);
                    border-radius: 10px;
                    color: #82CDFF;
                    padding: 8px 20px;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background-color: rgba(75, 184, 255, 0.16);
                    border-color: rgba(75, 184, 255, 0.55);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: rgba(75, 184, 255, 0.04);
                    border-color: rgba(75, 184, 255, 0.35);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.01);
                    border-color: rgba(255, 255, 255, 0.03);
                    color: rgba(255, 255, 255, 0.2);
                }
            """)
        elif danger:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(196, 64, 64, 0.08);
                    border: 1px solid rgba(196, 64, 64, 0.20);
                    border-top: 1px solid rgba(196, 64, 64, 0.35);
                    border-radius: 10px;
                    color: #EE7777;
                    padding: 8px 20px;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background-color: rgba(196, 64, 64, 0.16);
                    border-color: rgba(196, 64, 64, 0.45);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: rgba(196, 64, 64, 0.04);
                    border-color: rgba(196, 64, 64, 0.28);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.01);
                    border-color: rgba(255, 255, 255, 0.03);
                    color: rgba(255, 255, 255, 0.2);
                }
            """)
        elif dim:
            self.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 8px;
                    color: rgba(255, 255, 255, 0.35);
                    padding: 6px 14px;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.03);
                    border-color: rgba(255, 255, 255, 0.05);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.01);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-top: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 10px;
                    color: rgba(255, 255, 255, 0.65);
                    padding: 8px 20px;
                    letter-spacing: 0.5px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.06);
                    border-color: rgba(255, 255, 255, 0.22);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.01);
                    border-color: rgba(255, 255, 255, 0.12);
                }
                QPushButton:disabled {
                    background-color: rgba(255, 255, 255, 0.005);
                    border-color: rgba(255, 255, 255, 0.02);
                    color: rgba(255, 255, 255, 0.15);
                }
            """)

class _Divider(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet("background: rgba(255,255,255,0.08); border: none;")

class _FieldLabel(QLabel):
    def __init__(self, text, hint=None, parent=None):
        super().__init__(text, parent)
        self.setFont(_font("Inter Tight Medium", 12))
        self.setStyleSheet("color: rgba(200,200,200,0.85); background:transparent; border:none;")
        if hint:
            self.setToolTip(hint)

class _GlassSection(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-top: 1px solid rgba(255,255,255,0.10);
                border-radius: 16px;
            }
        """)
        self.setGraphicsEffect(_shadow(30, 8, 80))
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(24, 18, 24, 22)
        self._root.setSpacing(14)
        lbl = QLabel(title)
        lbl.setFont(_font("Inter Tight SemiBold", 10, True))
        lbl.setStyleSheet("color: rgba(160,160,160,0.75); letter-spacing:1.5px; background:transparent; border:none;")
        self._root.addWidget(lbl)

    def section_layout(self) -> QVBoxLayout:
        return self._root

class _PartyCharCard(QFrame):
    toggled = pyqtSignal()

    _BASE = """
        QFrame#pcard {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.07);
            border-top: 1px solid rgba(255,255,255,0.11);
            border-radius: 14px;
        }
    """
    _HOVER = """
        QFrame#pcard {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.18);
            border-top: 1px solid rgba(255,255,255,0.24);
            border-radius: 14px;
        }
    """
    _SELECTED = """
        QFrame#pcard {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(120,140,255,0.22), stop:1 rgba(90,110,255,0.10));
            border: 1px solid rgba(150,168,255,0.60);
            border-top: 1px solid rgba(175,190,255,0.80);
            border-radius: 14px;
        }
    """

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._checked = False
        self.setObjectName("pcard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        name_font = _font("Inter Tight Medium", 11)
        fm = QtGui.QFontMetrics(name_font)
        text_rect = fm.boundingRect(
            QtCore.QRect(0, 0, 128, 300),
            int(Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignCenter),
            name
        )
        text_height = max(18, text_rect.height() + 4)

        card_height = max(112, 10 + 52 + 8 + text_height + 10)
        self.setFixedSize(148, card_height)

        self.setStyleSheet(self._BASE)
        self.setGraphicsEffect(_shadow(18, 5, 60))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        av_wrap = QWidget(self)
        av_wrap.setFixedSize(52, 52)

        self.avatar_lbl = QLabel(av_wrap)
        self.avatar_lbl.setGeometry(0, 0, 52, 52)
        px = _get_char_avatar_pixmap(name)
        self.avatar_lbl.setPixmap(_round_pixmap(px, 52))
        self.avatar_lbl.setStyleSheet("background: transparent; border: none;")

        self.check_badge = QLabel(av_wrap)
        self.check_badge.setGeometry(52 - 18, 52 - 18, 18, 18)
        self.check_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check_badge.setText("✓")
        self.check_badge.setFont(_font("Inter Tight SemiBold", 9, True))
        self.check_badge.setStyleSheet("""
            background: #6C86FF; color: white; border-radius: 9px;
            border: 2px solid #14141a;
        """)
        self.check_badge.hide()

        av_row = QHBoxLayout()
        av_row.addStretch()
        av_row.addWidget(av_wrap)
        av_row.addStretch()
        lay.addLayout(av_row)

        self.name_lbl = QLabel(name)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.name_lbl.setFont(name_font)
        self.name_lbl.setStyleSheet("color: rgba(230,230,235,0.92); background: transparent; border:none; line-height: 1.2;")
        self.name_lbl.setWordWrap(True)
        lay.addWidget(self.name_lbl)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool):
        value = bool(value)
        if value == self._checked:
            return
        self._checked = value
        self._refresh_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._refresh_style()
            self.toggled.emit()
        super().mousePressEvent(event)

    def enterEvent(self, e):
        if not self._checked:
            self.setStyleSheet(self._HOVER)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._refresh_style()
        super().leaveEvent(e)

    def _refresh_style(self):
        if self._checked:
            self.setStyleSheet(self._SELECTED)
            self.check_badge.show()
        else:
            self.setStyleSheet(self._BASE)
            self.check_badge.hide()

class SceneCard(QFrame):
    play_clicked   = pyqtSignal(str)
    edit_clicked   = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    export_clicked = pyqtSignal(str)

    _N = "QFrame#sc { background: rgba(28, 28, 35, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); border-top: 1px solid rgba(255, 255, 255, 0.12); border-radius: 20px; }"
    _H = "QFrame#sc { background: rgba(40, 40, 50, 0.7); border: 1px solid rgba(255, 255, 255, 0.15); border-top: 1px solid rgba(255, 255, 255, 0.3); border-radius: 20px; }"

    def __init__(self, scene_id: str, scene_data: dict, parent=None):
        super().__init__(parent)
        self.scene_id = scene_id
        self.scene_data = scene_data
        self.setObjectName("sc")
        
        self.setFixedHeight(160) 
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(self._N)
        self.setGraphicsEffect(_shadow(35, 12, 90))

        self.translations = _load_translations()

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        self.scene_icon = QLabel()
        scene_px = QPixmap("app/gui/icons/d20.png")
        if scene_px.isNull():
            self.scene_icon.setText("◈")
            self.scene_icon.setStyleSheet("color: #50C878; font-size: 20px; font-weight: bold;")
        else:
            self.scene_icon.setPixmap(scene_px.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header_layout.addWidget(self.scene_icon)

        title = QLabel(scene_data.get("title", self.translations.get("new_adventure", "New Adventure")))
        title.setFont(_font("Inter Tight SemiBold", 15, bold=True))
        title.setStyleSheet("color: #FFFFFF; background: transparent;")
        header_layout.addWidget(title, 1)

        actions_container = QHBoxLayout()
        actions_container.setSpacing(8)

        btn_folder = QPushButton()
        btn_folder.setFixedSize(30, 30)
        btn_folder.setIcon(QIcon("app/gui/icons/folder.png"))
        btn_folder.setIconSize(QtCore.QSize(18, 18))
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_folder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_folder.setToolTip(self.translations.get("move_to_folder_btn", "Move to folder"))
        btn_folder.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.03); border-radius: 15px; border: none; }
            QPushButton:hover { background: rgba(255,255,255,0.12); }
        """)
        btn_folder.clicked.connect(lambda: self._on_move_to_folder(btn_folder))
        actions_container.addWidget(btn_folder)

        actions = [
            ("app/gui/icons/export.png", self.export_clicked, "rgba(255,255,255,0.4)"),
            ("app/gui/icons/edit.png", self.edit_clicked, "rgba(255,255,255,0.4)"),
            ("app/gui/icons/delete.png", self.delete_clicked, "rgba(255,80,80,0.6)")
        ]

        for icon_path, signal, _ in actions:
            btn = QPushButton()
            btn.setFixedSize(30, 30)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet("""
                QPushButton { background: rgba(255,255,255,0.03); border-radius: 15px; border: none; }
                QPushButton:hover { background: rgba(255,255,255,0.12); }
            """)
            btn.clicked.connect(lambda _, s=signal: s.emit(self.scene_id))
            actions_container.addWidget(btn)
        
        header_layout.addLayout(actions_container)
        root.addLayout(header_layout)

        desc_text = scene_data.get("description", self.translations.get("no_description", "No description set."))
        desc = QLabel(desc_text)
        desc.setFont(_font("Inter Tight Medium", 11))
        desc.setStyleSheet("color: rgba(255, 255, 255, 0.45); padding: 2px 0;")
        desc.setWordWrap(True)
        desc.setMaximumHeight(40)
        root.addWidget(desc)

        root.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        party = scene_data.get("party", [])
        party_wrapper = QWidget()
        party_layout = QHBoxLayout(party_wrapper)
        party_layout.setContentsMargins(0, 0, 0, 0)
        party_layout.setSpacing(-10)
        
        for name in party[:5]:
            p_av = QLabel()
            px = _get_char_avatar_pixmap(name)
            
            avatar_img_size = 28 
            
            border_thickness = 2
            widget_size = avatar_img_size + (border_thickness * 2)
            
            p_av.setPixmap(_round_pixmap(px, avatar_img_size))
            p_av.setFixedSize(widget_size, widget_size)
            p_av.setToolTip(name)
            
            border_radius = widget_size // 2
            p_av.setStyleSheet(f"""
                QLabel {{
                    border: {border_thickness}px solid #1c1c23; 
                    border-radius: {border_radius}px; 
                    background: transparent;
                }}
            """)
            party_layout.addWidget(p_av)
        
        bottom_row.addWidget(party_wrapper)
        bottom_row.addStretch()

        self.play_btn = QPushButton(f"  {self.translations.get('play', 'Play')}")
        self.play_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.play_btn.setIcon(QIcon("app/gui/icons/play.png"))
        self.play_btn.setIconSize(QtCore.QSize(14, 14))
        self.play_btn.setFixedHeight(36)
        self.play_btn.setMinimumWidth(110)
        self.play_btn.setFont(_font("Inter Tight SemiBold", 11))
        
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(80, 220, 140, 0.15), 
                    stop:1 rgba(40, 180, 100, 0.1));
                border: 1px solid rgba(80, 220, 140, 0.25);
                border-top: 1px solid rgba(80, 220, 140, 0.45);
                border-radius: 12px;
                color: #A0FFD2;
                padding: 0 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
                    stop:0 rgba(80, 220, 140, 0.25), 
                    stop:1 rgba(40, 180, 100, 0.2));
                border-color: rgba(80, 220, 140, 0.6);
                color: #FFFFFF;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.scene_id))
        bottom_row.addWidget(self.play_btn)

        root.addLayout(bottom_row)

    def _on_move_to_folder(self, btn_widget):
        groups = _get_scene_groups()
        parent_lobby = self.window().findChild(SoulStageLobbyView)

        if not groups:
            dlg = SowConfirmDialog(
                parent=self.window(),
                title=self.translations.get("no_folders_title", "No folders"),
                text=self.translations.get("no_folders_prompt_scenes", "No folders yet. Create one?"),
                confirm_text=self.translations.get("create", "Create"),
                danger=False
            )
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                if parent_lobby:
                    parent_lobby._open_create_folder_dialog()
            return

        folder_menu = QtWidgets.QMenu(self)
        folder_menu.setStyleSheet("""
            QMenu {
                background: #14141a; border: 1px solid rgba(255,255,255,0.1);
                border-radius: 10px; padding: 5px; color: white; font-size: 12px;
            }
            QMenu::item { padding: 7px 16px; border-radius: 5px; }
            QMenu::item:selected { background: rgba(0, 230, 118, 0.18); color: #00E676; }
        """)

        current_group = None
        for g, members in groups.items():
            if self.scene_id in members:
                current_group = g
                break

        if current_group:
            remove_act = QtGui.QAction(
                f"✕  {self.translations.get('remove_from_folder', 'Remove from folder')}", folder_menu
            )
            def _remove():
                grps = _get_scene_groups()
                if self.scene_id in grps.get(current_group, []):
                    grps[current_group].remove(self.scene_id)
                    _save_scene_groups(grps)
                    if parent_lobby:
                        parent_lobby.refresh()
            remove_act.triggered.connect(_remove)
            folder_menu.addAction(remove_act)
            folder_menu.addSeparator()

        for g in groups.keys():
            act = QtGui.QAction(f"📁  {g}", folder_menu)
            if g == current_group:
                act.setEnabled(False)
            def _move(checked=False, gname=g):
                grps = _get_scene_groups()
                for og, om in grps.items():
                    if self.scene_id in om:
                        om.remove(self.scene_id)
                grps.setdefault(gname, [])
                if self.scene_id not in grps[gname]:
                    grps[gname].append(self.scene_id)
                _save_scene_groups(grps)
                if parent_lobby:
                    parent_lobby.refresh()
            act.triggered.connect(_move)
            folder_menu.addAction(act)

        folder_menu.exec(btn_widget.mapToGlobal(QtCore.QPoint(0, btn_widget.height() + 4)))

    def enterEvent(self, e):
        self.setStyleSheet(self._H)
        self.setGraphicsEffect(_shadow(45, 12, 120))

    def leaveEvent(self, e):
        self.setStyleSheet(self._N)
        self.setGraphicsEffect(_shadow(35, 12, 90))

class SoulStageLobbyView(QWidget):
    create_new   = pyqtSignal()
    open_scene   = pyqtSignal(str)
    edit_scene   = pyqtSignal(str)
    delete_scene = pyqtSignal(str)
    import_scene = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._cards: dict[str, SceneCard] = {}
        self._folder_cards: list = []
        self._current_opened_folder: Optional[str] = None
        self._folder_header_widget: Optional[QWidget] = None

        self.translations = _load_translations()

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(40, 24, 40, 20)
        self.root_layout.setSpacing(16)

        self.hdr = QHBoxLayout()
        self.title_lbl = QLabel(self.translations.get("soul_stage_title", "Soul Stage"))
        self.title_lbl.setFont(_font("Inter Tight SemiBold", 22, True))
        self.title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); background:transparent; border:none;")
        self.hdr.addWidget(self.title_lbl, 1)

        self.btn_new_folder = _Btn(self.translations.get("new_folder", "📁 New Folder"), dim=False)
        self.btn_new_folder.clicked.connect(self._open_create_folder_dialog)
        self.hdr.addWidget(self.btn_new_folder)

        self.btn_import = _Btn(self.translations.get("import_scene", "Import"), dim=False)
        self.btn_import.clicked.connect(self.import_scene)
        self.hdr.addWidget(self.btn_import)

        self.btn_new = _Btn(self.translations.get("new_scene", "＋ New Scene"), primary=True)
        self.btn_new.clicked.connect(self.create_new)
        self.hdr.addWidget(self.btn_new)
        self.root_layout.addLayout(self.hdr)

        self.search = QLineEdit()
        self.search.setPlaceholderText(self.translations.get("search_scenes", "Search scenes..."))
        self.search.setFixedHeight(36)
        self.search.setStyleSheet(INPUT)
        self.search.textChanged.connect(self._filter)
        self.root_layout.addWidget(self.search)

        self.root_layout.addWidget(_Divider())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet(SCROLLBAR)

        self.grid_w = QWidget()
        self.grid_w.setStyleSheet("background:transparent;")
        self.grid_container = QVBoxLayout(self.grid_w)
        self.grid_container.setContentsMargins(0, 4, 8, 20)
        self.grid_container.setSpacing(16)
        self.grid_container.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.folders_section_w = QWidget()
        self.folders_section_w.setStyleSheet("background:transparent;")
        self.folders_section_w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        self.folders_section_lay = QVBoxLayout(self.folders_section_w)
        self.folders_section_lay.setContentsMargins(0, 0, 0, 0)
        self.folders_section_lay.setSpacing(10)
        self.folders_section_lay.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.folders_title = QLabel(self.translations.get("lobby_folders_section", "SCENE FOLDERS"))
        self.folders_title.setFont(_font("Inter Tight SemiBold", 11, True))
        self.folders_title.setStyleSheet("color: rgba(0, 230, 118, 0.85); letter-spacing: 1.5px;")
        self.folders_section_lay.addWidget(self.folders_title)

        self.folders_grid = QGridLayout()
        self.folders_grid.setContentsMargins(0, 0, 0, 0)
        self.folders_grid.setSpacing(12)
        self.folders_grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.folders_section_lay.addLayout(self.folders_grid)

        self.folders_divider = _Divider()

        self.grid_container.addWidget(self.folders_section_w)
        self.grid_container.addWidget(self.folders_divider)

        self.scenes_section_w = QWidget()
        self.scenes_section_w.setStyleSheet("background:transparent;")
        self.scenes_section_w.setSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        self.scenes_section_lay = QVBoxLayout(self.scenes_section_w)
        self.scenes_section_lay.setContentsMargins(0, 0, 0, 0)
        self.scenes_section_lay.setSpacing(10)

        self.scenes_title = QLabel(self.translations.get("lobby_scenes_section", "SCENARIOS"))
        self.scenes_title.setFont(_font("Inter Tight SemiBold", 11, True))
        self.scenes_title.setStyleSheet("color: rgba(255, 255, 255, 0.5); letter-spacing: 1.5px;")
        self.scenes_section_lay.addWidget(self.scenes_title)

        self.scenes_grid = QGridLayout()
        self.scenes_grid.setContentsMargins(0, 0, 0, 0)
        self.scenes_grid.setSpacing(12)
        self.scenes_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scenes_section_lay.addLayout(self.scenes_grid)

        self.grid_container.addWidget(self.scenes_section_w)
        self.grid_container.addStretch()

        self.scroll.setWidget(self.grid_w)
        self.root_layout.addWidget(self.scroll, 1)

        self.empty_lbl = QLabel(self.translations.get("no_scenes", "No scenes yet.\nClick  ＋ New Scene  to start your first story."))
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_lbl.setFont(_font("Inter Tight Medium", 14))
        self.empty_lbl.setStyleSheet("color: rgba(120,120,120,0.5); background:transparent; border:none;")
        
        self.refresh()

    def _get_scene_groups(self) -> dict:
        return _get_scene_groups()

    def _save_scene_groups(self, groups: dict):
        _save_scene_groups(groups)

    def refresh_lobby(self):
        self.refresh()

    def refresh(self):
        for c in list(self._cards.values()):
            self.scenes_grid.removeWidget(c)
            c.deleteLater()
        self._cards.clear()

        for fc in self._folder_cards:
            self.folders_grid.removeWidget(fc)
            fc.deleteLater()
        self._folder_cards.clear()

        scenes = _load_scenes().get("scenes", {})
        groups = _get_scene_groups()
        grouped_scenes = _get_grouped_scenes()

        if not scenes and not groups:
            self.folders_section_w.hide()
            self.folders_divider.hide()
            self.scenes_section_w.hide()
            if self.empty_lbl.parent() != self.grid_w:
                self.grid_container.insertWidget(0, self.empty_lbl)
            self.empty_lbl.show()
            return

        self.empty_lbl.hide()

        if self._current_opened_folder and self._current_opened_folder in groups:
            self.folders_section_w.hide()
            self.folders_divider.hide()
            self.scenes_title.hide()
            self.scenes_section_w.show()

            members = groups[self._current_opened_folder]
            row, col = 0, 0
            for sid in members:
                if sid in scenes:
                    card = SceneCard(sid, scenes[sid])
                    card.play_clicked.connect(self.open_scene)
                    card.edit_clicked.connect(self.edit_scene)
                    card.delete_clicked.connect(self.delete_scene)
                    card.export_clicked.connect(self._on_export_scene)
                    self._cards[sid] = card
                    self.scenes_grid.addWidget(card, row, col, Qt.AlignmentFlag.AlignTop)
                    col += 1
                    if col >= 2:
                        col = 0
                        row += 1
            return

        self.scenes_title.show()

        if groups:
            self.folders_section_w.show()
            self.folders_divider.show()

            row_f, col_f = 0, 0
            max_folder_cols = 4

            for g_name, members in groups.items():
                preview_bgs = []
                for sid in members[:4]:
                    bg = scenes.get(sid, {}).get("starting_bg")
                    if bg and bg != "None":
                        preview_bgs.append(f"assets/backgrounds/{bg}")

                folder_card = SceneFolderCard(
                    group_name=g_name,
                    scene_count=len(members),
                    preview_bgs=preview_bgs,
                    soul_stage_page=self,
                    parent=self.grid_w
                )
                self._folder_cards.append(folder_card)
                self.folders_grid.addWidget(folder_card, row_f, col_f, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                col_f += 1
                if col_f >= max_folder_cols:
                    col_f = 0
                    row_f += 1
        else:
            self.folders_section_w.hide()
            self.folders_divider.hide()

        ungrouped_scenes = [
            (sid, sdata) for sid, sdata in scenes.items() if sid not in grouped_scenes
        ]
        
        if ungrouped_scenes:
            self.scenes_section_w.show()
            sorted_s = sorted(ungrouped_scenes, key=lambda kv: kv[1].get("last_played") or "", reverse=True)
            row_s, col_s = 0, 0
            for sid, sdata in sorted_s:
                card = SceneCard(sid, sdata)
                card.play_clicked.connect(self.open_scene)
                card.edit_clicked.connect(self.edit_scene)
                card.delete_clicked.connect(self.delete_scene)
                card.export_clicked.connect(self._on_export_scene)
                self._cards[sid] = card
                self.scenes_grid.addWidget(card, row_s, col_s, Qt.AlignmentFlag.AlignTop)
                col_s += 1
                if col_s >= 2:
                    col_s = 0
                    row_s += 1
        else:
            if groups:
                self.scenes_section_w.hide()
            else:
                self.scenes_section_w.show()

    def _open_folder_view(self, group_name: str):
        self._current_opened_folder = group_name
        self._show_folder_header(group_name)
        self.refresh()

    def _close_folder_view(self):
        self._current_opened_folder = None
        if self._folder_header_widget:
            self.root_layout.removeWidget(self._folder_header_widget)
            self._folder_header_widget.deleteLater()
            self._folder_header_widget = None
            self.hdr.setEnabled(True)
            self.search.show()
        self.refresh()

    def _show_folder_header(self, group_name: str):
        if self._folder_header_widget:
            self.root_layout.removeWidget(self._folder_header_widget)
            self._folder_header_widget.deleteLater()
            self._folder_header_widget = None

        header = QWidget()
        header.setFixedHeight(45)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        back_btn = QPushButton("←")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedHeight(30)
        back_btn.setFont(_font("Inter Tight Medium", 11))
        back_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.15); border-radius: 15px; padding: 0 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
        """)
        back_btn.clicked.connect(self._close_folder_view)

        title_lbl = QLabel(f"📁 {group_name}")
        title_lbl.setFont(_font("Inter Tight SemiBold", 16, bold=True))
        title_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.95);")

        groups = _get_scene_groups()
        count_lbl = QLabel(f"{len(groups.get(group_name, []))} {self.translations.get('folder_scenes_label', 'scenes')}")
        count_lbl.setFont(_font("Inter Tight Medium", 12))
        count_lbl.setStyleSheet("color: rgba(0, 230, 118, 0.65);")

        edit_btn = QPushButton(self.translations.get("folder_edit_btn", "Edit"))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setFixedHeight(28)
        edit_btn.setFont(_font("Inter Tight Medium", 12))
        edit_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 7px; padding: 0 12px;
            }
            QPushButton:hover { background: rgba(0, 230, 118, 0.15); border-color: rgba(0, 230, 118, 0.4); color: #00E676; }
        """)
        edit_btn.clicked.connect(lambda: self._open_folder_editor(group_name))

        layout.addWidget(back_btn)
        layout.addWidget(title_lbl)
        layout.addWidget(count_lbl)
        layout.addStretch()
        layout.addWidget(edit_btn)

        self._folder_header_widget = header
        self.root_layout.insertWidget(2, header)

    def _open_create_folder_dialog(self):
        scenes = _load_scenes().get("scenes", {})
        groups = _get_scene_groups()

        dialog = QtWidgets.QDialog(self.window())
        dialog.setWindowTitle(self.translations.get("folder_create_title_scene", "Create Scene Folder"))
        dialog.setFixedSize(480, 560)
        dialog.setStyleSheet("""
            QDialog { background: #0c0c10; }
            QLabel { color: rgba(255,255,255,0.85); background: transparent; }
            QLineEdit {
                background: rgba(255,255,255,0.04); color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px;
            }
            QListWidget {
                background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px; color: white; padding: 6px;
            }
            QListWidget::item { padding: 6px; min-height: 28px; }
            QPushButton#createBtn {
                background: rgba(0, 230, 118, 0.15); border: 1px solid rgba(0, 230, 118, 0.4);
                border-radius: 8px; color: #00E676; padding: 10px; font-weight: bold;
            }
            QPushButton#createBtn:hover { background: rgba(0, 230, 118, 0.3); color: white; }
        """)

        lyt = QVBoxLayout(dialog)
        lyt.setContentsMargins(24, 24, 24, 24)
        lyt.setSpacing(14)

        t_lbl = QLabel(self.translations.get("folder_create_title_scene", "Create Scene Folder"))
        t_lbl.setFont(_font("Inter Tight SemiBold", 16, True))
        lyt.addWidget(t_lbl)

        name_in = QLineEdit()
        name_in.setPlaceholderText(self.translations.get("folder_name_placeholder", "Folder name..."))
        lyt.addWidget(name_in)

        pick_lbl = QLabel(self.translations.get("folder_select_scenes_label", "Select Scenes to include:"))
        pick_lbl.setFont(_font("Inter Tight Medium", 11))
        lyt.addWidget(pick_lbl)

        list_w = QtWidgets.QListWidget()
        list_w.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        for sid, sdata in scenes.items():
            it = QtWidgets.QListWidgetItem(f"🎬 {sdata.get('title', 'Untitled')}")
            it.setData(Qt.ItemDataRole.UserRole, sid)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            list_w.addItem(it)
        lyt.addWidget(list_w, 1)

        btn_create = QPushButton(self.translations.get("folder_create_btn", "Create Folder"))
        btn_create.setObjectName("createBtn")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        lyt.addWidget(btn_create)

        def _do_create():
            name = name_in.text().strip()
            if not name:
                return
            if name in groups:
                sow_toast(self.window(), "Error", "A folder with this name already exists!", "error")
                return
            selected_ids = []
            for idx in range(list_w.count()):
                it = list_w.item(idx)
                if it.checkState() == Qt.CheckState.Checked:
                    selected_ids.append(it.data(Qt.ItemDataRole.UserRole))
            groups[name] = selected_ids
            _save_scene_groups(groups)
            dialog.accept()
            self.refresh()

        btn_create.clicked.connect(_do_create)
        dialog.exec()

    def _open_folder_editor(self, group_name: str):
        scenes = _load_scenes().get("scenes", {})
        groups = _get_scene_groups()
        members = list(groups.get(group_name, []))

        dialog = QtWidgets.QDialog(self.window())
        dialog.setWindowTitle(f"Edit Folder — {group_name}")
        dialog.setFixedSize(480, 560)
        dialog.setStyleSheet("""
            QDialog { background: #0c0c10; }
            QLabel { color: rgba(255,255,255,0.85); background: transparent; }
            QLineEdit {
                background: rgba(255,255,255,0.04); color: white;
                border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px;
            }
            QListWidget {
                background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px; color: white; padding: 6px;
            }
            QListWidget::item { padding: 6px; min-height: 28px; }
            QPushButton#saveBtn {
                background: rgba(0, 230, 118, 0.15); border: 1px solid rgba(0, 230, 118, 0.4);
                border-radius: 8px; color: #00E676; padding: 10px; font-weight: bold;
            }
            QPushButton#saveBtn:hover { background: rgba(0, 230, 118, 0.3); color: white; }
            QPushButton#delBtn {
                background: rgba(244, 67, 54, 0.1); border: 1px solid rgba(244, 67, 54, 0.3);
                border-radius: 8px; color: #F44336; padding: 10px;
            }
            QPushButton#delBtn:hover { background: rgba(244, 67, 54, 0.25); color: white; }
        """)

        lyt = QVBoxLayout(dialog)
        lyt.setContentsMargins(24, 24, 24, 24)
        lyt.setSpacing(14)

        edit_folder_tr = self.translations.get("folder_select_scenes_title", "Edit Folder: ")
        t_lbl = QLabel(f"{edit_folder_tr} {group_name}")
        t_lbl.setFont(_font("Inter Tight SemiBold", 16, True))
        lyt.addWidget(t_lbl)

        name_in = QLineEdit(group_name)
        lyt.addWidget(name_in)

        pick_lbl = QLabel(self.translations.get("folder_select_scenes_label", "Scenes inside this folder:"))
        pick_lbl.setFont(_font("Inter Tight Medium", 11))
        lyt.addWidget(pick_lbl)

        list_w = QtWidgets.QListWidget()
        for sid, sdata in scenes.items():
            it = QtWidgets.QListWidgetItem(f"🎬 {sdata.get('title', 'Untitled')}")
            it.setData(Qt.ItemDataRole.UserRole, sid)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if sid in members else Qt.CheckState.Unchecked)
            list_w.addItem(it)
        lyt.addWidget(list_w, 1)

        btn_row = QHBoxLayout()
        btn_del = QPushButton(self.translations.get("delete_folder", "Delete Folder"))
        btn_del.setObjectName("delBtn")
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_save = QPushButton(self.translations.get("save_changes", "Save Changes"))
        btn_save.setObjectName("saveBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_save)
        lyt.addLayout(btn_row)

        def _do_save():
            new_name = name_in.text().strip()
            if not new_name:
                return
            new_selected = []
            for idx in range(list_w.count()):
                it = list_w.item(idx)
                if it.checkState() == Qt.CheckState.Checked:
                    new_selected.append(it.data(Qt.ItemDataRole.UserRole))
            groups[group_name] = new_selected
            if new_name != group_name and new_name not in groups:
                groups[new_name] = groups.pop(group_name)
                self._current_opened_folder = new_name

            _save_scene_groups(groups)
            dialog.accept()
            if self._current_opened_folder:
                self._show_folder_header(self._current_opened_folder)
            self.refresh()

        def _do_delete():
            dlg = SowConfirmDialog(
                parent=dialog,
                title=self.translations.get("delete_folder", "Delete Folder"),
                text=f"Delete folder '{group_name}'? (Scenes will not be deleted)",
                confirm_text=self.translations.get("delete", "Delete"),
                danger=True
            )
            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                groups.pop(group_name, None)
                _save_scene_groups(groups)
                dialog.accept()
                self._close_folder_view()

        btn_save.clicked.connect(_do_save)
        btn_del.clicked.connect(_do_delete)
        dialog.exec()

    def _filter(self, text: str):
        q = text.lower().strip()
        
        visible_scenes = 0
        for sid, card in self._cards.items():
            t = card.scene_data.get("title", "").lower()
            d = card.scene_data.get("description", "").lower()
            match = not q or q in t or q in d
            card.setVisible(match)
            if match:
                visible_scenes += 1

        visible_folders = 0
        for fc in self._folder_cards:
            match = not q or q in fc.group_name.lower()
            fc.setVisible(match)
            if match:
                visible_folders += 1

        if self.folders_section_w.isVisible():
            self.folders_title.setVisible(visible_folders > 0)
        if self.scenes_section_w.isVisible():
            self.scenes_title.setVisible(visible_scenes > 0)

    def _on_export_scene(self, scene_id: str):
        data = _load_scenes()
        scene_data = data.get("scenes", {}).get(scene_id)
        if not scene_data:
            return

        export_data = {
            "title": scene_data.get("title", ""),
            "description": scene_data.get("description", ""),
            "world_context": scene_data.get("world_context", ""),
            "starting_location": scene_data.get("starting_location", ""),
            "time_of_day": scene_data.get("time_of_day", "day"),
            "opening_narration": scene_data.get("opening_narration", ""),
            "first_message": scene_data.get("first_message", ""),
            "party": scene_data.get("party", []),
            "gm_tone": scene_data.get("gm_tone", "epic_fantasy"),
            "narrator_style": scene_data.get("narrator_style", "Standard evocative present-tense prose"),
            "conversation_method": scene_data.get("conversation_method", "Local LLM"),
            "persona": scene_data.get("persona", "None"),
            "lorebook": scene_data.get("lorebook", []),
            "lock_bg": scene_data.get("lock_bg", False),
            "disable_ambient": scene_data.get("disable_ambient", False),
        }

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.translations.get("export_title", "Export Scene"),
            f"{scene_data.get('title', 'scene')}.json",
            "JSON Files (*.json)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

class SceneEditorView(QWidget):
    saved    = pyqtSignal(str)
    canceled = pyqtSignal()

    def __init__(self, all_characters: list, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self._editing_id: str = None
        self._char_checks: dict[str, "_PartyCharCard"] = {}

        self.translations = _load_translations()

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 24, 40, 20)
        root.setSpacing(12)

        hdr = QHBoxLayout(); hdr.setSpacing(12)
        self.btn_back = _Btn(self.translations.get("back", "← Back"), dim=True)
        self.btn_back.clicked.connect(self.canceled)
        self.title_lbl = QLabel(self.translations.get("new_scene", "New Scene"))
        self.title_lbl.setFont(_font("Inter Tight SemiBold", 18, True))
        self.title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); background:transparent; border:none;")
        hdr.addWidget(self.btn_back); hdr.addSpacing(6); hdr.addWidget(self.title_lbl); hdr.addStretch()
        self.btn_save = _Btn(self.translations.get("save_launch", "Save & Launch  ▶"), primary=True)
        self.btn_save.clicked.connect(self._on_save)
        hdr.addWidget(self.btn_save)
        root.addLayout(hdr)
        root.addWidget(_Divider())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(SCROLLBAR)

        form = QWidget(); form.setStyleSheet("background:transparent;")
        fly = QVBoxLayout(form); fly.setContentsMargins(0, 4, 16, 24); fly.setSpacing(16)

        sec1 = _GlassSection(self.translations.get("section_identity", "I.  SCENE IDENTITY"))
        ly1 = sec1.section_layout()
        r1 = QHBoxLayout(); r1.setSpacing(16)
        c1 = QVBoxLayout(); c1.setSpacing(6)
        c1.addWidget(_FieldLabel(self.translations.get("title", "Title  *")))
        self.f_title = QLineEdit(); self.f_title.setPlaceholderText(self.translations.get("title_placeholder", "e.g. The Obsidian Citadel")); self.f_title.setFixedHeight(38); self.f_title.setStyleSheet(INPUT); c1.addWidget(self.f_title)
        self.f_title.setFont(_font("Inter Tight Medium", 13))
        c2 = QVBoxLayout(); c2.setSpacing(6)
        c2.addWidget(_FieldLabel(self.translations.get("short_description", "Short Description")))
        self.f_desc = QLineEdit(); self.f_desc.setPlaceholderText(self.translations.get("desc_placeholder", "Brief summary for the list")); self.f_desc.setFixedHeight(38); self.f_desc.setStyleSheet(INPUT); c2.addWidget(self.f_desc)
        self.f_desc.setFont(_font("Inter Tight Medium", 13))
        r1.addLayout(c1, 4); r1.addLayout(c2, 6); ly1.addLayout(r1)
        fly.addWidget(sec1)

        sec2 = _GlassSection(self.translations.get("section_world", "II.  WORLD STATE & ENVIRONMENT"))
        ly2 = sec2.section_layout()
        ly2.addWidget(_FieldLabel(self.translations.get("world_context", "World Context / Scenario  *"), self.translations.get("world_context_hint", "Injected into every AI prompt as background truth.")))
        self.f_world = AutoResizingTextEdit(); self.f_world.setPlaceholderText(self.translations.get("world_placeholder", "Lore, current tension, rules of magic or physics...")); self.f_world.setFixedHeight(90); self.f_world.setStyleSheet(INPUT); ly2.addWidget(self.f_world)

        r_env = QHBoxLayout(); r_env.setSpacing(16)
        cl = QVBoxLayout(); cl.setSpacing(6); cl.addWidget(_FieldLabel(self.translations.get("starting_location", "Starting Location")))
        self.f_location = QLineEdit(); self.f_location.setPlaceholderText(self.translations.get("location_placeholder", "e.g. The Golden Dragon Tavern")); self.f_location.setFixedHeight(38); self.f_location.setStyleSheet(INPUT); cl.addWidget(self.f_location)
        self.f_location.setFont(_font("Inter Tight Medium", 13))

        ct = QVBoxLayout(); ct.setSpacing(6); ct.addWidget(_FieldLabel(self.translations.get("time_of_day", "Time of Day")))
        self.f_time = QComboBox(); self.f_time.addItems([self.translations.get("morning", "Morning"), self.translations.get("day", "Day"), self.translations.get("evening", "Evening"), self.translations.get("night", "Night")]); self.f_time.setCurrentIndex(1); self.f_time.setFixedHeight(38); self.f_time.setStyleSheet(INPUT); ct.addWidget(self.f_time)
        self.f_time.setStyleSheet(COMBO_STYLE)

        cn = QVBoxLayout(); cn.setSpacing(6); cn.addWidget(_FieldLabel(self.translations.get("gm_tone", "GM Tone")))
        self.f_tone = QComboBox(); 
        self.f_tone.addItems([self.translations.get("epic_fantasy", "Epic Fantasy"), self.translations.get("slice_of_life", "Slice of Life"), self.translations.get("mystery_noir", "Mystery & Noir"), self.translations.get("romance", "Romance"), self.translations.get("horror", "Horror"), self.translations.get("comedy", "Comedy"), self.translations.get("sci_fi", "Sci-Fi")]); 
        self.f_tone.setFixedHeight(38); 
        self.f_tone.setStyleSheet(INPUT); 
        self.f_tone.setEditable(True)
        cn.addWidget(self.f_tone)
        self.f_tone.setStyleSheet(COMBO_STYLE)
        r_env.addLayout(cl, 4); r_env.addLayout(ct, 2); r_env.addLayout(cn, 3)
        ly2.addLayout(r_env)

        c_style = QVBoxLayout()
        c_style.setSpacing(6)
        c_style.addWidget(_FieldLabel(
            self.translations.get("narrator_style", "Narrator Style"), 
            self.translations.get("narrator_style_hint", "Directs the specific prose style, author voice, or pacing of the narrator.")
        ))
        self.f_narrator_style = QComboBox()
        self.f_narrator_style.setStyleSheet(COMBO_STYLE)
        self.f_narrator_style.setEditable(True)
        self.f_narrator_style.addItems([
            "Standard evocative present-tense prose",
            "Stephen King (suspenseful, detailed character focus)",
            "H.P. Lovecraft (cosmic dread, archaic and complex vocabulary)",
            "Ernest Hemingway (minimalist, short and punchy sentences, objective)",
            "J.R.R. Tolkien (poetic, high-detailed description of nature and history)"
        ])
        self.f_narrator_style.setFixedHeight(38)
        self.f_narrator_style.setFont(_font("Inter Tight Medium", 13))
        c_style.addWidget(self.f_narrator_style)
        ly2.addLayout(c_style)

        r_env2 = QHBoxLayout(); r_env2.setSpacing(16)
        bg_choices  = _get_assets("assets/backgrounds", [".jpg", ".png", ".jpeg"])
        amb_choices = _get_assets("assets/ambient", [".mp3", ".wav", ".ogg"])

        cb = QVBoxLayout(); cb.setSpacing(6)
        cb.addWidget(_FieldLabel(self.translations.get("starting_background", "Starting Background"), self.translations.get("starting_background_hint", "The Planner can change this dynamically during the scene.")))
        self.f_bg_image = QComboBox()
        self.f_bg_image.setStyleSheet(COMBO_STYLE)
        self.f_bg_image.addItems(bg_choices)
        self.f_bg_image.setFixedHeight(38)
        cb.addWidget(self.f_bg_image)

        ca = QVBoxLayout(); ca.setSpacing(6)
        ca.addWidget(_FieldLabel(self.translations.get("starting_ambient", "Starting Ambient"), self.translations.get("starting_ambient_hint", "Background audio for this scene. The Planner can switch it dynamically.")))
        self.f_ambient = QComboBox()
        self.f_ambient.setStyleSheet(COMBO_STYLE)
        self.f_ambient.addItems(amb_choices)
        self.f_ambient.setFixedHeight(38)
        ca.addWidget(self.f_ambient)

        r_env2.addLayout(cb, 5)
        r_env2.addLayout(ca, 5)
        ly2.addLayout(r_env2)

        lock_row = QHBoxLayout()
        lock_row.setSpacing(16)

        self.f_lock_bg = QtWidgets.QCheckBox(
            self.translations.get("lock_background", "🔒 Lock background (prevent auto-change)")
        )
        self.f_lock_bg.setFont(_font("Inter Tight Medium", 12))
        self.f_lock_bg.setStyleSheet(CB_STYLE)
        self.f_lock_bg.setToolTip(
            self.translations.get(
                "lock_background_hint",
                "When enabled, the background image stays fixed and will NOT change "
                "automatically during the scene — even if the location changes."
            )
        )
        lock_row.addWidget(self.f_lock_bg)

        self.f_disable_ambient = QtWidgets.QCheckBox(
            self.translations.get("disable_ambient", "🔇 Disable ambient audio (play in silence)")
        )
        self.f_disable_ambient.setFont(_font("Inter Tight Medium", 12))
        self.f_disable_ambient.setStyleSheet(CB_STYLE)
        self.f_disable_ambient.setToolTip(
            self.translations.get(
                "disable_ambient_hint",
                "When enabled, no ambient audio will play during the scene. "
                "Useful when you want silence or when you have limited audio assets."
            )
        )
        lock_row.addWidget(self.f_disable_ambient)

        ly2.addLayout(lock_row)

        fly.addWidget(sec2)

        sec3 = _GlassSection(self.translations.get("section_opening", "III.  STORY OPENING"))
        ly3 = sec3.section_layout()
        ly3.addWidget(_FieldLabel(self.translations.get("opening_narration", "Opening Narration  *"), self.translations.get("opening_narration_hint", "The Narrator's first words — places the player in the scene.")))
        self.f_opening = AutoResizingTextEdit(); self.f_opening.setPlaceholderText(self.translations.get("opening_placeholder", "The rain hammers cobblestones as you push open the heavy iron door...")); self.f_opening.setFixedHeight(84); self.f_opening.setStyleSheet(INPUT); ly3.addWidget(self.f_opening)
        ly3.addWidget(_FieldLabel(self.translations.get("first_message", "First Character Message  (optional)")))
        self.f_first_msg = AutoResizingTextEdit(); self.f_first_msg.setPlaceholderText(self.translations.get("first_msg_placeholder", "Optional greeting from the first party member.")); self.f_first_msg.setFixedHeight(64); self.f_first_msg.setStyleSheet(INPUT); ly3.addWidget(self.f_first_msg)
        fly.addWidget(sec3)

        bot = QHBoxLayout()
        bot.setSpacing(16)
        bot.setContentsMargins(0, 0, 0, 0)

        sec4a = _GlassSection(self.translations.get("section_party", "IV.  PARTY MEMBERS"))
        sec4a.setFixedHeight(480)
        ly4a = sec4a.section_layout()
        ly4a.setSpacing(10)

        party_hdr = QHBoxLayout()
        party_hdr.addWidget(_FieldLabel(self.translations.get("select_characters", "Select characters for this scene")))
        party_hdr.addStretch()
        self.party_count_lbl = QLabel(self.translations.get("party_member_selected", "0 selected").replace("{n}", "0"))
        self.party_count_lbl.setFont(_font("Inter Tight SemiBold", 10, True))
        self.party_count_lbl.setStyleSheet(
            "color: rgba(150,168,255,0.85); background: rgba(120,140,255,0.12); "
            "border: 1px solid rgba(150,168,255,0.30); border-radius: 9px; padding: 3px 10px;"
        )
        party_hdr.addWidget(self.party_count_lbl)
        ly4a.addLayout(party_hdr)

        self.char_scroll = QScrollArea()
        self.char_scroll.setWidgetResizable(True)
        self.char_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.char_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.char_scroll.setStyleSheet(
            SCROLLBAR + "QScrollArea { background: rgba(0,0,0,0.22); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; }"
        )

        self.char_inner = QWidget()
        self.char_inner.setStyleSheet("background: transparent;")
        self.char_grid = QGridLayout(self.char_inner)
        self.char_grid.setContentsMargins(10, 10, 10, 10)
        self.char_grid.setSpacing(10)
        self.char_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.char_scroll.setWidget(self.char_inner)
        ly4a.addWidget(self.char_scroll, 1)

        bot.addWidget(sec4a, 6)

        sec4b = _GlassSection(self.translations.get("section_engine", "V.  ENGINE SETTINGS"))
        sec4b.setFixedHeight(480)
        ly4b = sec4b.section_layout()
        ly4b.setSpacing(8)

        ly4b.addWidget(_FieldLabel(self.translations.get("conversation_method", "Conversation Method")))
        self.f_method = QComboBox()
        self.f_method.addItems([
            "Local LLM", "Open AI", "Anthropic", "Google Gemini", 
            "DeepSeek", "Grok", "Qwen", "Z.AI", "Mistral AI", "OpenRouter", "Player2"
        ])
        self.f_method.setFixedHeight(36)
        self.f_method.setStyleSheet(COMBO_STYLE)
        ly4b.addWidget(self.f_method)

        ly4b.addWidget(_FieldLabel(self.translations.get("user_persona", "User Persona"), self.translations.get("user_persona_hint", "Name and avatar shown in the chat for your messages.")))
        self.f_persona = QComboBox()
        self.f_persona.setStyleSheet(COMBO_STYLE)
        self.f_persona.setFixedHeight(36)
        ly4b.addWidget(self.f_persona)

        ly4b.addWidget(_FieldLabel(
            self.translations.get("max_actor_depth", "Max Actors Per Turn"),
            self.translations.get("max_actor_depth_hint", "How many party members and NPCs may speak in a single turn (1-6, default 3).")
        ))
        from PyQt6.QtWidgets import QSpinBox
        self.f_max_actor_depth = QSpinBox()
        self.f_max_actor_depth.setRange(1, 6)
        self.f_max_actor_depth.setValue(3)
        self.f_max_actor_depth.setFixedHeight(36)
        self.f_max_actor_depth.setStyleSheet(INPUT)
        ly4b.addWidget(self.f_max_actor_depth)

        self._selected_lorebooks = []
        ly4b.addWidget(_FieldLabel(self.translations.get("lorebooks_soul_stage_page", "Lorebooks  (optional)")))
        self.btn_lorebook = QPushButton("None")
        self.btn_lorebook.setFixedHeight(36)
        self.btn_lorebook.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lorebook.setStyleSheet("""
            QPushButton {
                background-color: rgba(15, 15, 18, 0.4);
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                padding: 6px 12px;
                text-align: left;
                font-family: 'Inter Tight Medium';
                font-size: 13px;
            }
            QPushButton:hover {
                border: 1px solid rgba(255, 255, 255, 0.4);
                background: rgba(255, 255, 255, 0.08);
            }
        """)
        self.btn_lorebook.clicked.connect(self._open_lorebook_selector)
        ly4b.addWidget(self.btn_lorebook)

        ly4b.addWidget(_FieldLabel(
            self.translations.get("dice_rolls", "Dice Rolls"),
            self.translations.get("dice_rolls_hint", "Lets the GM call for d20/2d6/3d6 checks on risky or contested actions.")
        ))
        self.f_dice_enabled = QtWidgets.QCheckBox(
            self.translations.get("dice_rolls_enable", "🎲 Enable Dice Rolls for this scene")
        )
        self.f_dice_enabled.setFont(_font("Inter Tight Medium", 12))
        self.f_dice_enabled.setStyleSheet(CB_STYLE)
        ly4b.addWidget(self.f_dice_enabled)

        ly4b.addStretch()
        bot.addWidget(sec4b, 4)

        fly.addLayout(bot)

        scroll.setWidget(form)
        root.addWidget(scroll, 1)
        self.rebuild_char_list(all_characters)

    def _update_lorebook_button_text(self):
        selected = self._selected_lorebooks
        if not selected:
            self.btn_lorebook.setText("None")
        elif len(selected) == 1:
            self.btn_lorebook.setText(selected[0])
        else:
            self.btn_lorebook.setText(f"Selected: {len(selected)}")

    def _open_lorebook_selector(self):
        from app.configuration import configuration
        from app.gui.custom_widgets import MultiSelectDialog
        
        config = configuration.ConfigurationSettings().load_configuration()
        user_data = config.get("user_data", {})
        all_lorebooks = sorted(list(user_data.get("lorebooks", {}).keys()))
        
        dialog = MultiSelectDialog(
            self.translations.get("lorebook_selector_title", "Select Lorebooks"),
            all_lorebooks,
            self._selected_lorebooks,
            self.translations,
            self.window()
        )
        
        if dialog.exec():
            self._selected_lorebooks = dialog.get_selected_items()
            self._update_lorebook_button_text()

    def rebuild_char_list(self, characters: list):
        while self.char_grid.count():
            item = self.char_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._char_checks.clear()

        if not characters:
            lbl = QLabel(self.translations.get("no_characters", "No characters found."))
            lbl.setStyleSheet("color: rgba(120,120,120,0.6); font-size:13px; background:transparent; border:none;")
            self.char_grid.addWidget(lbl, 0, 0)
            self._update_party_count()
            return

        cols = 3
        for i, name in enumerate(characters):
            card = _PartyCharCard(name)
            card.toggled.connect(self._update_party_count)
            self._char_checks[name] = card
            self.char_grid.addWidget(card, i // cols, i % cols)

        self._update_party_count()

    def _update_party_count(self):
        n = sum(1 for cb in self._char_checks.values() if cb.isChecked())
        label = self.translations.get("party_member_selected", "{n} selected").format(n=n)
        self.party_count_lbl.setText(label)

    def load_scene(self, scene_id: str, scene_data: dict):
        self._editing_id = scene_id
        self.title_lbl.setText(self.translations.get("edit_scene", "Edit Scene"))
        self.btn_save.setText(self.translations.get("save_changes", "Save Changes"))
        self.f_title.setText(scene_data.get("title", ""))
        self.f_desc.setText(scene_data.get("description", ""))
        self.f_world.setPlainText(scene_data.get("world_context", ""))
        self.f_location.setText(scene_data.get("starting_location", ""))
        self.f_opening.setPlainText(scene_data.get("opening_narration", ""))
        self.f_first_msg.setPlainText(scene_data.get("first_message", ""))
        self.f_time.setCurrentIndex({"morning": 0, "day": 1, "evening": 2, "night": 3}.get(scene_data.get("time_of_day", "day"), 1))
        self.f_tone.setCurrentText(scene_data.get("gm_tone", "Epic Fantasy"))
        self.f_method.setCurrentIndex({
            "Local LLM": 0, "Open AI": 1, "Anthropic": 2, "Google Gemini": 3,
            "DeepSeek": 4, "Grok": 5, "Qwen": 6, "Z.AI": 7, "Mistral AI": 8, "OpenRouter": 9,
            "Player2": 10
        }.get(scene_data.get("conversation_method", "Local LLM"), 0))
        self.f_persona.setCurrentText(scene_data.get("persona", "None"))
        self.f_narrator_style.setCurrentText(scene_data.get("narrator_style", "Standard evocative present-tense prose"))
        self.f_max_actor_depth.setValue(int(scene_data.get("max_actor_depth", 3)))
        self.f_dice_enabled.setChecked(bool(scene_data.get("dice_rolls_enabled", False)))

        self.f_lock_bg.setChecked(bool(scene_data.get("lock_bg", False)))
        self.f_disable_ambient.setChecked(bool(scene_data.get("disable_ambient", False)))
        
        lb_data = scene_data.get("lorebook", [])
        if isinstance(lb_data, str):
            if lb_data and lb_data != "None":
                self._selected_lorebooks = [lb_data]
            else:
                self._selected_lorebooks = []
        else:
            self._selected_lorebooks = lb_data if lb_data else []
        self._update_lorebook_button_text()
        
        party = scene_data.get("party", [])
        for name, cb in self._char_checks.items():
            cb.setChecked(name in party)
        self._update_party_count()

        bg_val = scene_data.get("starting_bg", "None")
        idx = self.f_bg_image.findText(bg_val)
        self.f_bg_image.setCurrentIndex(idx if idx >= 0 else 0)

        amb_val = scene_data.get("starting_ambient", "None")
        idx = self.f_ambient.findText(amb_val)
        self.f_ambient.setCurrentIndex(idx if idx >= 0 else 0)

    def clear_form(self):
        self._editing_id = None
        self.title_lbl.setText(self.translations.get("new_scene", "New Scene"))
        self.btn_save.setText(self.translations.get("save_launch", "Save & Launch  ▶"))
        for w in [self.f_title, self.f_desc, self.f_location]: w.clear()
        for w in [self.f_world, self.f_opening, self.f_first_msg]: w.clear()
        self.f_time.setCurrentIndex(1)
        self.f_tone.setCurrentIndex(0)
        self.f_method.setCurrentIndex(0)
        self.f_narrator_style.setCurrentIndex(0)
        self.f_max_actor_depth.setValue(3)
        self.f_dice_enabled.setChecked(False)
        self.f_lock_bg.setChecked(False)
        self.f_disable_ambient.setChecked(False)
        self.f_bg_image.setCurrentIndex(0)
        self.f_ambient.setCurrentIndex(0)
        self._selected_lorebooks = []
        self._update_lorebook_button_text()
        for cb in self._char_checks.values(): cb.setChecked(False)
        self._update_party_count()

    def load_personas(self, personas_dict):
        self.f_persona.clear()
        self.f_persona.addItem("None")
        for p in personas_dict.keys():
            self.f_persona.addItem(p)

    def load_from_import(self, import_data: dict):
        self.clear_form()
        self._editing_id = None
        self.title_lbl.setText(self.translations.get("import_file", "Import Scene"))
        self.f_title.setText(import_data.get("title", ""))
        self.f_desc.setText(import_data.get("description", ""))
        self.f_world.setPlainText(import_data.get("world_context", ""))
        self.f_location.setText(import_data.get("starting_location", ""))
        self.f_opening.setPlainText(import_data.get("opening_narration", ""))
        self.f_first_msg.setPlainText(import_data.get("first_message", ""))
        self.f_time.setCurrentIndex({"morning": 0, "day": 1, "evening": 2, "night": 3}.get(import_data.get("time_of_day", "day"), 1))
        self.f_tone.setCurrentText(import_data.get("gm_tone", "Epic Fantasy"))
        self.f_method.setCurrentIndex({
            "Local LLM": 0, "Open AI": 1, "Anthropic": 2, "Google Gemini": 3,
            "DeepSeek": 4, "Grok": 5, "Qwen": 6, "Z.AI": 7, "Mistral AI": 8, "OpenRouter": 9,
            "Player2": 10
        }.get(import_data.get("conversation_method", "Local LLM"), 0))
        self.f_persona.setCurrentText(import_data.get("persona", "None"))
        self.f_narrator_style.setCurrentText(import_data.get("narrator_style", "Standard evocative present-tense prose"))
        self.f_dice_enabled.setChecked(bool(import_data.get("dice_rolls_enabled", False)))
        self.f_lock_bg.setChecked(bool(import_data.get("lock_bg", False)))
        self.f_disable_ambient.setChecked(bool(import_data.get("disable_ambient", False)))

        party = import_data.get("party", [])
        for name, cb in self._char_checks.items():
            cb.setChecked(name in party)
        self._update_party_count()

        lb_data = import_data.get("lorebook", [])
        if isinstance(lb_data, str):
            if lb_data and lb_data != "None":
                self._selected_lorebooks = [lb_data]
            else:
                self._selected_lorebooks = []
        else:
            self._selected_lorebooks = lb_data if lb_data else []
        self._update_lorebook_button_text()

    def _on_save(self):
        title   = self.f_title.text().strip()
        opening = self.f_opening.toPlainText().strip()
        party   = [n for n, cb in self._char_checks.items() if cb.isChecked()]
        ok = True
        err   = INPUT + "QLineEdit { border-color: rgba(255,60,60,0.6); }"
        err_t = INPUT + "QTextEdit { border-color: rgba(255,60,60,0.6); }"
        err_scroll = SCROLLBAR + "QScrollArea { background: rgba(0,0,0,0.18); border: 1px solid rgba(255,60,60,0.6); border-radius: 14px; }"
        ok_scroll  = SCROLLBAR + "QScrollArea { background: rgba(0,0,0,0.18); border: 1px solid rgba(255,255,255,0.06); border-radius: 14px; }"
        if not title:   self.f_title.setStyleSheet(err);   ok = False
        else:           self.f_title.setStyleSheet(INPUT)
        if not opening: self.f_opening.setStyleSheet(err_t); ok = False
        else:           self.f_opening.setStyleSheet(INPUT)
        if not party:   self.char_scroll.setStyleSheet(err_scroll); ok = False
        else:           self.char_scroll.setStyleSheet(ok_scroll)
        if not party or not ok: return
        tod  = ["morning", "day", "evening", "night"][self.f_time.currentIndex()]
        now  = datetime.datetime.now().isoformat()
        data = _load_scenes(); sid = self._editing_id or str(uuid.uuid4())
        exist = data["scenes"].get(sid, {})
        data["scenes"][sid] = {
            "title":            title,
            "description":      self.f_desc.text().strip(),
            "world_context":    self.f_world.toPlainText().strip(),
            "starting_location": self.f_location.text().strip() or "Unknown",
            "time_of_day":      tod,
            "opening_narration": opening,
            "first_message":    self.f_first_msg.toPlainText().strip(),
            "party":            party,
            "gm_tone":          self.f_tone.currentText(),
            "narrator_style": self.f_narrator_style.currentText(),
            "conversation_method": self.f_method.currentText(),
            "persona":          self.f_persona.currentText(),
            "lorebook":         self._selected_lorebooks,
            "max_actor_depth":  int(self.f_max_actor_depth.value()),
            "dice_rolls_enabled": self.f_dice_enabled.isChecked(),
            "starting_bg":      self.f_bg_image.currentText(),
            "starting_ambient": self.f_ambient.currentText(),
            "lock_bg":          self.f_lock_bg.isChecked(),
            "disable_ambient":  self.f_disable_ambient.isChecked(),
            "created_at":       exist.get("created_at", now),
            "last_played":      exist.get("last_played", ""),
            "chat_log":         exist.get("chat_log", []),
        }
        _save_scenes(data); self.saved.emit(sid)

class _BaseChatBubble(QFrame):
    def __init__(self, name: str, avatar_path: str, bg_color: str, parent=None):
        super().__init__(parent)
        from app.configuration import configuration
        self.cfg = configuration.ConfigurationSettings()
        s = self.cfg.get_main_setting("chat_appearance") or {}
        text_color = s.get("text_color", "#DCDCDC")
        font_size = s.get("font_size", 14)
        r = s.get("border_radius", 15)
        op = s.get("bubble_opacity", 100)
        alpha = round(op / 100.0, 2)
        
        if bg_color.startswith("#"):
            h = bg_color.lstrip("#")
            try:
                bg_color = f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {alpha})"
            except Exception:
                pass

        self.setStyleSheet("background: transparent; border: none;")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 5, 10, 5)
        main_layout.setSpacing(0)
        
        self.bubble_frame = QFrame()
        self.bubble_frame.setObjectName("bubble_frame")
        
        radius_css = (
            f"border-top-right-radius: {r}px; border-bottom-right-radius: {r}px; "
            f"border-top-left-radius: {r}px; border-bottom-left-radius: 0px;"
        )
        
        self.bubble_frame.setStyleSheet(f"""
            QFrame#bubble_frame {{
                background-color: {bg_color};
                {radius_css}
                margin: 5px;
            }}
        """)

        bubble_width = s.get("max_width", 750)
        self.bubble_frame.setFixedWidth(bubble_width)
        
        bubble_layout = QVBoxLayout(self.bubble_frame)
        bubble_layout.setContentsMargins(14, 12, 14, 12)
        bubble_layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        raw_pixmap = QPixmap(avatar_path)
        if raw_pixmap.isNull():
            raw_pixmap = QPixmap("app/gui/icons/logotype.png")

        target_size = 64
        label_size  = 26

        scaled_pixmap = raw_pixmap.scaled(
            target_size, target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        crop_x = (scaled_pixmap.width()  - target_size) // 2
        crop_y = (scaled_pixmap.height() - target_size) // 2
        square_pixmap = scaled_pixmap.copy(crop_x, crop_y, target_size, target_size)

        final_avatar_pixmap = QPixmap(target_size, target_size)
        final_avatar_pixmap.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QPainter(final_avatar_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        path = QPainterPath()
        path.addEllipse(0, 0, target_size, target_size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, square_pixmap)
        painter.end()

        self.avatar_label = QLabel()
        self.avatar_label.setPixmap(final_avatar_pixmap)
        self.avatar_label.setFixedSize(label_size, label_size)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")
        header_layout.addWidget(self.avatar_label)
        
        self.header_label = QLabel(name)
        font = QtGui.QFont("Inter Tight SemiBold", max(11, font_size - 2), QtGui.QFont.Weight.Bold)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.header_label.setFont(font)
        self.header_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: {max(11, font_size - 2)}px;
                font-weight: bold;
                background: transparent;
                border: none;
            }}
        """)
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()
        
        bubble_layout.addLayout(header_layout)
        
        self._text_label = QLabel()
        self._text_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        self._text_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        
        font_text = QtGui.QFont("Inter Tight Medium", font_size)
        font_text.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        self._text_label.setFont(font_text)
        
        self._text_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: {font_size}px;
                background: transparent;
                border: none;
                line-height: 1.4;
            }}
        """)
        bubble_layout.addWidget(self._text_label)
        
        main_layout.addStretch()
        main_layout.addWidget(self.bubble_frame)
        main_layout.addStretch()

    def append_text(self, chunk: str):
        self._text_label.setText(self._text_label.text() + chunk)

    def set_text(self, text: str):
        self._text_label.setText(text)

    @property
    def text_label(self):
        return self._text_label

def format_dice_dict(d: dict) -> str:
    label = d.get("label", "Check")
    notation = d.get("notation", "1d20")
    modifier = d.get("modifier", 0) or 0
    total = d.get("total", 0)
    dc = d.get("dc")
    success = d.get("success")
    mod_str = f"{'+' if modifier >= 0 else ''}{modifier}" if modifier else ""
    base = f"{label} ({notation}{mod_str}) = {total}"
    if dc is None:
        return base
    outcome = "Success" if success else "Failure"
    return f"{base} vs DC {dc} — {outcome}"


class SoulStageDiceCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        from app.configuration import configuration
        s = configuration.ConfigurationSettings().get_main_setting("chat_appearance") or {}
        bubble_width = s.get("max_width", 750)

        self.setStyleSheet("background: transparent; border: none;")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 2, 10, 2)
        outer.setSpacing(0)
        outer.addStretch()

        self.card = QFrame()
        self.card.setObjectName("dice_card")
        self.card.setFixedWidth(bubble_width)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(10)

        self.icon_lbl = QLabel("🎲")
        self.icon_lbl.setStyleSheet("background: transparent; border: none; font-size: 16px;")
        card_layout.addWidget(self.icon_lbl)

        self.text_label = QLabel("Rolling…")
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text_label.setStyleSheet("""
            QLabel {
                color: rgba(240, 235, 220, 0.92);
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        card_layout.addWidget(self.text_label, 1)

        outer.addWidget(self.card)
        outer.addStretch()

        self._apply_accent(None)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._ticks_left = 0
        self._final_text = ""
        self._final_success = None
        self._roll_sides = 20

    def _apply_accent(self, success):
        if success is True:
            border = "rgba(90, 220, 130, 0.60)"
        elif success is False:
            border = "rgba(230, 90, 90, 0.60)"
        else:
            border = "rgba(255, 210, 90, 0.60)"
        self.card.setStyleSheet(f"""
            QFrame#dice_card {{
                background: rgba(24, 22, 18, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 4px solid {border};
                border-radius: 10px;
            }}
        """)

    def animate_to(self, result_text: str, success, sides: int = 20) -> None:
        self._final_text = result_text
        self._final_success = success
        self._roll_sides = max(2, sides)
        self._ticks_left = 6
        self._timer.start(55)

    def set_final(self, result_text: str, success) -> None:
        self._timer.stop()
        self.text_label.setText(result_text)
        self._apply_accent(success)

    def _tick(self):
        self._ticks_left -= 1
        if self._ticks_left <= 0:
            self._timer.stop()
            self.text_label.setText(self._final_text)
            self._apply_accent(self._final_success)
        else:
            self.text_label.setText(str(random.randint(1, self._roll_sides)))

class SoulStageNPCBubble(_BaseChatBubble):
    def __init__(self, npc_name: str, archetype: str, avatar_path: str = None, parent=None):
        if not avatar_path:
            avatar_path = "app/gui/icons/logotype.png"
        super().__init__(
            name=f"{npc_name.upper()}  ·  {archetype}",
            avatar_path=avatar_path,
            bg_color="rgba(25, 25, 30, 0.85)", 
            parent=parent
        )

class SoulStageEventCard(_BaseChatBubble):
    _EVENT_THEMES = {
        "encounter": ("ENCOUNTER", "rgba(60, 15, 10, 0.85)"),
        "discovery": ("DISCOVERY", "rgba(45, 35, 5, 0.85)"),
        "visitor":   ("VISITOR", "rgba(20, 15, 55, 0.85)"),
        "twist":     ("PLOT TWIST", "rgba(5, 35, 45, 0.85)"),
        "romance":   ("MOMENT", "rgba(50, 10, 30, 0.85)"),
        "none":      ("NARRATOR", "rgba(35, 28, 15, 0.85)"),
    }

    def __init__(self, event_type: str = "none", parent=None):
        event_type = event_type if event_type in self._EVENT_THEMES else "none"
        label, bg_color = self._EVENT_THEMES[event_type]
        super().__init__(
            name=label,
            avatar_path="app/gui/icons/d20.png",
            bg_color=bg_color,
            parent=parent
        )

class InventoryHUD(QWidget):
    open_full_requested = pyqtSignal()

    _ITEM_ICONS = {
        "sword": "sword.svg", "knife": "sword.svg", "blade": "sword.svg",
        "gun": "pistol.svg", "pistol": "pistol.svg", "rifle": "rifle.svg",
        "bow": "bow.svg", "axe": "axe.svg", "club": "hammer.svg", "spear": "spear.svg",
        "apple": "food.svg", "bread": "food.svg", "meat": "food.svg", "food": "food.svg",
        "potion": "potion.svg", "medicine": "medicine-pills.svg", "аптечка": "medicine-pills.svg",
        "water": "water.svg", "flask": "potion.svg", "canteen": "water.svg",
        "key": "key.svg", "map": "map.svg", "torch": "torch.svg", "flashlight": "flashlight.svg",
        "rope": "rope.svg", "book": "book.svg", "note": "document.svg", "document": "document.svg",
        "coin": "coins.svg", "gold": "gold-bar.svg", "money": "money.svg",
        "lock": "padlock.svg", "bag": "bag.svg", "radio": "pocket-radio.svg", "phone": "smartphone.svg",
    }
    _DEFAULT_ICON = "box.svg"

    def __init__(self, text_input, parent=None):
        super().__init__(parent)
        self._text_input = text_input
        self._items: list[str] = []
        self.translations = _load_translations()

        self.setObjectName("inv_hud")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget#inv_hud {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(16,16,18,0.95),
                    stop:1 rgba(10,10,12,0.98));
                border: 1px solid rgba(255,255,255,0.08);
                border-top: 1px solid rgba(255,255,255,0.15);
                border-radius: 12px;
            }
        """)
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18); shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.setGraphicsEffect(shadow)

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 7, 10, 9)
        self._root.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(6)
        bag = QLabel()
        bag.setPixmap(QIcon(str(Path("app/gui/icons/soul_stage/bag.svg"))).pixmap(12, 12))
        hdr.addWidget(bag)
        inv_lbl = QLabel(self.translations.get("inventory", "INVENTORY"))
        inv_lbl.setFont(_font("Inter Tight SemiBold", 7, bold=True))
        inv_lbl.setStyleSheet("color: rgba(255,255,255,0.60); letter-spacing:2px;")
        hdr.addWidget(inv_lbl, 1)
        open_btn = QPushButton()
        open_btn.setIcon(QIcon(str(Path("app/gui/icons/soul_stage/expand.svg"))))
        open_btn.setIconSize(QtCore.QSize(10, 10))
        open_btn.setFixedSize(18, 18)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        open_btn.setToolTip(self.translations.get("tooltip_open_inventory", "Open full inventory"))
        open_btn.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,0.05); border: none;
                border-radius: 4px; }
            QPushButton:hover { background: rgba(255,255,255,0.15); }
        """)
        open_btn.clicked.connect(self.open_full_requested.emit)
        hdr.addWidget(open_btn)
        self._root.addLayout(hdr)

        self._tags_w = QWidget()
        self._tags_w.setStyleSheet("background: transparent;")
        self._tags_l = QVBoxLayout(self._tags_w)
        self._tags_l.setContentsMargins(0, 0, 0, 0)
        self._tags_l.setSpacing(5)
        self._root.addWidget(self._tags_w)

        self.hide()

    @classmethod
    def _item_icon(cls, item: str) -> str:
        il = item.lower()
        for keyword, icon in cls._ITEM_ICONS.items():
            if keyword in il:
                return icon
        return cls._DEFAULT_ICON

    def update_items(self, items: list[str]):
        self._items = items
        while self._tags_l.count():
            child = self._tags_l.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        if not items:
            self.hide()
            return
        for item in items[:6]:
            icon_file = self._item_icon(item)
            icon_path = str(Path("app/gui/icons/soul_stage") / icon_file)
            btn = QPushButton(f" {item}")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QtCore.QSize(14, 14))
            btn.setFont(_font("Inter Tight Medium", 10))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedHeight(28)
            btn.setToolTip(self.translations.get("tooltip_use_item", "Use: {item}").replace("{item}", item))
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.03);
                    border: none;
                    border-radius: 6px;
                    color: rgba(255,255,255,0.85);
                    text-align: left;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.08);
                    color: white;
                }
            """)
            btn.clicked.connect(lambda _, it=item: self._use_item(it))
            self._tags_l.addWidget(btn)
        if len(items) > 6:
            more = QLabel(self.translations.get("more_items", "+{count} more").replace("{count}", str(len(items) - 6)))
            more.setFont(_font("Inter Tight Medium", 9))
            more.setStyleSheet("color: rgba(255,255,255,0.40); padding: 0 4px;")
            self._tags_l.addWidget(more)
        self._tags_l.addStretch()
        self.adjustSize()
        self.show()
        self.raise_()

    def _use_item(self, item: str):
        action = f"*uses {item}*"
        cur = self._text_input.toPlainText().strip()
        self._text_input.setPlainText(f"{cur} {action}".strip())
        c = self._text_input.textCursor()
        c.movePosition(c.MoveOperation.End)
        self._text_input.setTextCursor(c)
        self._text_input.setFocus()

    def reposition(self, parent_size):
        self.adjustSize()
        self.move(20, max(0, parent_size.height() - self.height() - 18))
        self.raise_()

class InventoryPanel(QtWidgets.QDialog):
    item_used    = pyqtSignal(str)   
    item_dropped = pyqtSignal(str)   

    _CATEGORIES = {
        "Weapons":["sword","knife","blade","gun","rifle","bow","axe","club","spear","меч","нож","пистолет","ружьё"],
        "Consumables":["apple","bread","meat","food","potion","medicine","water","flask","canteen","еда","яблоко","аптечка","вода"],
        "Tools":["key","map","torch","rope","book","note","lock","radio","phone","ключ","карта","фонарь","верёвка","книга"],
        "Valuables":["coin","gold","gem","ring","деньги","монета","золото","кольцо"],
        "Quest Items":["letter","document","journal","relic","artifact","письмо","документ","дневник"],
        "Other":[],
    }

    def __init__(self, world_state, parent=None):
        super().__init__(parent)
        self.world_state = world_state
        self.translations = _load_translations()
        
        self.setWindowTitle(self.translations.get("inventory_full_title", "Inventory"))
        self.setMinimumSize(540, 560)
        self.setStyleSheet("""
            QDialog { 
                background-color: #0c0c0e; 
                color: #e8e8e8; 
            }
            QLabel { background: transparent; border: none; }
            
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollArea { background: transparent; border: none; }
        """)
        self._build_ui()

    def _set_font(self, widget, family="Inter Tight Medium", size=12, bold=False):
        f = QtGui.QFont(family, size)
        if bold:
            f.setWeight(QtGui.QFont.Weight.Bold)
        f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        widget.setFont(f)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        self._set_font(lbl, "Inter Tight SemiBold", 10, bold=True)
        lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); letter-spacing: 2px; background: transparent; border: none;")
        return lbl

    def _categorize(self, items: list[str]) -> dict:
        cats = {k:[] for k in self._CATEGORIES}
        for item in items:
            il = item.lower()
            placed = False
            for cat, keywords in self._CATEGORIES.items():
                if cat == "Other":
                    continue
                if any(kw in il for kw in keywords):
                    cats[cat].append(item)
                    placed = True
                    break
            if not placed:
                cats["Other"].append(item)
        return {k: v for k, v in cats.items() if v}

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        hdr = QFrame()
        hdr.setObjectName("inv_header")
        hdr.setFixedHeight(64)
        hdr.setStyleSheet("QFrame#inv_header { background: rgba(20, 20, 24, 0.8); border: none; }")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(14)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(str(Path("app/gui/icons/soul_stage/bag.svg"))).pixmap(24, 24))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(icon_lbl)
        
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        title_lbl = QLabel(self.translations.get("inventory", "INVENTORY").upper())
        self._set_font(title_lbl, "Inter Tight SemiBold", 13, bold=True)
        title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); letter-spacing: 1.5px; background: transparent; border: none;")
        title_col.addWidget(title_lbl)
        
        ws = self.world_state
        count_lbl = QLabel(self.translations.get("items_count", "{count} items").replace("{count}", str(len(ws.player_inventory))))
        self._set_font(count_lbl, "Inter Tight Medium", 10)
        count_lbl.setStyleSheet("color: rgba(255,255,255,0.40); background: transparent; border: none;")
        title_col.addWidget(count_lbl)
        
        hl.addLayout(title_col, 1)
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        il = QVBoxLayout(inner)
        il.setContentsMargins(28, 24, 28, 24)
        il.setSpacing(20)

        items = ws.player_inventory
        if not items:
            empty_lbl = QLabel(self.translations.get("inventory_empty", "Your inventory is empty."))
            self._set_font(empty_lbl, "Inter Tight Medium", 13)
            empty_lbl.setStyleSheet("color: rgba(255,255,255,0.25); background: transparent; border: none;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            il.addWidget(empty_lbl)
        else:
            cats = self._categorize(items)
            cat_map = {
                "Weapons": self.translations.get("category_weapons", "Weapons"),
                "Consumables": self.translations.get("category_consumables", "Consumables"),
                "Tools": self.translations.get("category_tools", "Tools"),
                "Valuables": self.translations.get("category_valuables", "Valuables"),
                "Quest Items": self.translations.get("category_quest_items", "Quest Items"),
                "Other": self.translations.get("category_other", "Other"),
            }
            for cat_name, cat_items in cats.items():
                cat_lbl = self._section_label(cat_map.get(cat_name, cat_name))
                il.addWidget(cat_lbl)
                
                grid_w = QWidget()
                grid_w.setStyleSheet("background: transparent;")
                grid = QGridLayout(grid_w)
                grid.setContentsMargins(0, 0, 0, 0)
                grid.setSpacing(10)
                
                for idx, item in enumerate(cat_items):
                    card = self._make_item_card(item)
                    grid.addWidget(card, idx // 2, idx % 2)
                il.addWidget(grid_w)

        il.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        footer = QFrame()
        footer.setObjectName("inv_footer")
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame#inv_footer { background: rgba(20, 20, 24, 0.5); border: none; border-top: 1px solid rgba(255,255,255,0.03); }")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.addStretch()
        
        close_btn = QPushButton(self.translations.get("update_available_close", "Close"))
        self._set_font(close_btn, "Inter Tight Medium", 12)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_btn.setFixedHeight(38)
        close_btn.setFixedWidth(120)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        close_btn.clicked.connect(self.accept)
        fl.addWidget(close_btn)
        
        root.addWidget(footer)

    def _make_item_card(self, item: str) -> QFrame:
        card = QFrame()
        card.setObjectName("inv_item_card")
        card.setFixedHeight(54)
        card.setStyleSheet("""
            QFrame#inv_item_card {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid transparent;
                border-radius: 10px;
            }
            QFrame#inv_item_card:hover { 
                background: rgba(255, 255, 255, 0.08); 
                border: 1px solid rgba(255, 255, 255, 0.15); 
            }
        """)
        cl = QHBoxLayout(card)
        cl.setContentsMargins(12, 0, 12, 0)
        cl.setSpacing(10)

        icon_file = InventoryHUD._item_icon(item)
        ic_lbl = QLabel()
        ic_lbl.setPixmap(QIcon(str(Path("app/gui/icons/soul_stage") / icon_file)).pixmap(20, 20))
        ic_lbl.setFixedWidth(22)
        ic_lbl.setStyleSheet("background: transparent; border: none;")
        cl.addWidget(ic_lbl)

        name_lbl = QLabel(item)
        self._set_font(name_lbl, "Inter Tight SemiBold", 12)
        name_lbl.setStyleSheet("color: rgba(255,255,255,0.9); background: transparent; border: none;")
        name_lbl.setWordWrap(True)
        cl.addWidget(name_lbl, 1)

        btn_use = QPushButton(self.translations.get("btn_use", "Use"))
        btn_use.setFixedSize(48, 28)
        btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_use.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._set_font(btn_use, "Inter Tight Medium", 10)
        btn_use.setStyleSheet("""
            QPushButton { 
                background: rgba(255,255,255,0.05); 
                border: 1px solid transparent;
                border-radius: 6px; 
                color: rgba(255,255,255,0.85); 
            }
            QPushButton:hover { 
                background: rgba(255,255,255,0.15); 
                color: white; 
                border-color: rgba(255,255,255,0.3); 
            }
        """)
        btn_use.clicked.connect(lambda _, it=item: (self.item_used.emit(it), self.accept()))
        cl.addWidget(btn_use)

        btn_drop = QPushButton("✕")
        btn_drop.setFixedSize(28, 28)
        btn_drop.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_drop.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._set_font(btn_drop, "Inter Tight Medium", 11)
        btn_drop.setToolTip(self.translations.get("tooltip_drop", "Drop item"))
        btn_drop.setStyleSheet("""
            QPushButton { 
                background: rgba(255,255,255,0.03); 
                border: 1px solid transparent;
                border-radius: 6px; 
                color: rgba(255,255,255,0.40); 
            }
            QPushButton:hover { 
                background: rgba(255,60,60,0.15); 
                border-color: rgba(255,60,60,0.3); 
                color: rgba(255,100,100,0.90); 
            }
        """)
        btn_drop.clicked.connect(lambda _, it=item: self._drop_item(it))
        cl.addWidget(btn_drop)
        return card

    def _drop_item(self, item: str):
        self.item_dropped.emit(item)
        if item in self.world_state.player_inventory:
            self.world_state.player_inventory.remove(item)
        self.accept()
        new_panel = InventoryPanel(self.world_state, self.parent())
        new_panel.item_used.connect(self.item_used)
        new_panel.item_dropped.connect(self.item_dropped)
        new_panel.exec()

class ChoicesBar(QFrame):
    choice_selected = pyqtSignal(str)

    _THEMES = {
        "encounter": {
            "accent": "#FF5555",
            "bg_accent": "rgba(255, 85, 85, 0.14)",
            "border": "rgba(255, 85, 85, 0.45)",
            "icon": "⚔️",
            "label": "TACTICAL CHOICE",
        },
        "discovery": {
            "accent": "#FFD15C",
            "bg_accent": "rgba(255, 209, 92, 0.14)",
            "border": "rgba(255, 209, 92, 0.45)",
            "icon": "✦",
            "label": "DISCOVERY",
        },
        "visitor": {
            "accent": "#A080FF",
            "bg_accent": "rgba(160, 128, 255, 0.14)",
            "border": "rgba(160, 128, 255, 0.45)",
            "icon": "👤",
            "label": "RESPONSE",
        },
        "twist": {
            "accent": "#50E3C2",
            "bg_accent": "rgba(80, 227, 194, 0.14)",
            "border": "rgba(80, 227, 194, 0.45)",
            "icon": "⚡",
            "label": "PLOT TWIST",
        },
        "romance": {
            "accent": "#FF65A3",
            "bg_accent": "rgba(255, 101, 163, 0.14)",
            "border": "rgba(255, 101, 163, 0.45)",
            "icon": "♥",
            "label": "INTIMATE MOMENT",
        },
        "none": {
            "accent": "#70A0FF",
            "bg_accent": "rgba(112, 160, 255, 0.14)",
            "border": "rgba(112, 160, 255, 0.45)",
            "icon": "◈",
            "label": "CHOOSE YOUR ACTION",
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("choices_bar")
        self._event_type = "none"
        self.translations = _load_translations()

        self.setStyleSheet("""
            QFrame#choices_bar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0.00 rgba(14, 14, 18, 0.0),
                    stop:0.20 rgba(12, 12, 16, 0.88),
                    stop:0.80 rgba(10, 10, 14, 0.88),
                    stop:1.00 rgba(8, 8, 12, 0.0));
                border-top: 1px solid rgba(255, 255, 255, 0.08);
                border-bottom: none;
                margin-bottom: 6px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 12, 24, 22)
        root.setSpacing(10)

        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(0, 0, 0, 0)
        hdr_row.setSpacing(8)

        self._badge_icon = QLabel("◈")
        self._badge_icon.setFont(_font("Inter Tight SemiBold", 10))
        self._badge_icon.setStyleSheet("background: transparent; border: none;")
        hdr_row.addWidget(self._badge_icon)

        self._hint_lbl = QLabel(self.translations.get("choice_hint_none", "CHOOSE YOUR ACTION  —  OR TYPE YOUR OWN"))
        self._hint_lbl.setFont(_font("Inter Tight SemiBold", 9, bold=True))
        self._hint_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.50); letter-spacing: 1.5px; background: transparent; border: none;")
        hdr_row.addWidget(self._hint_lbl)
        hdr_row.addStretch()

        self._btn_dismiss = QPushButton("✕")
        self._btn_dismiss.setFixedSize(20, 20)
        self._btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_dismiss.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._btn_dismiss.setToolTip("Hide choices")
        self._btn_dismiss.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                border: none;
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.40);
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.12);
                color: rgba(255, 255, 255, 0.90);
            }
        """)
        self._btn_dismiss.clicked.connect(self.clear_choices)
        hdr_row.addWidget(self._btn_dismiss)

        root.addLayout(hdr_row)

        self._grid_w = QWidget()
        self._grid_w.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_w)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(10)

        root.addWidget(self._grid_w)
        self.hide()

    def show_choices(self, choices: list[str], event_type: str = "none"):
        if not choices:
            self.hide()
            return

        self._event_type = event_type if event_type in self._THEMES else "none"
        theme = self._THEMES[self._event_type]

        self._badge_icon.setText(theme["icon"])
        self._badge_icon.setStyleSheet(f"color: {theme['accent']}; font-size: 13px; background: transparent; border: none;")

        hint_text = self.translations.get(f"choice_hint_{self._event_type}", f"{theme['label']}  —  OR TYPE YOUR OWN ACTION")
        self._hint_lbl.setText(hint_text.upper())
        self._hint_lbl.setStyleSheet(f"color: {theme['accent']}; letter-spacing: 1.5px; background: transparent; border: none;")

        while self._grid_layout.count():
            child = self._grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        acc = theme["accent"]
        bg_acc = theme["bg_accent"]
        border_acc = theme["border"]

        btn_style = f"""
            QPushButton {{
                background: rgba(20, 20, 26, 0.80);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 3px solid {acc};
                border-radius: 10px;
                color: rgba(240, 240, 245, 0.92);
                font-family: 'Inter Tight Medium';
                font-size: 12px;
                padding: 10px 16px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {bg_acc};
                border-color: {border_acc};
                border-left: 5px solid {acc};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.12);
            }}
        """

        num_choices = min(len(choices), 4)
        for i in range(num_choices):
            text = choices[i]
            btn = QPushButton(f"  [{i + 1}]   {text}")
            btn.setFont(_font("Inter Tight Medium", 12))
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setMinimumHeight(42)

            shadow = QtWidgets.QGraphicsDropShadowEffect()
            shadow.setBlurRadius(14)
            shadow.setOffset(0, 3)
            shadow.setColor(QColor(0, 0, 0, 90))
            btn.setGraphicsEffect(shadow)

            btn.clicked.connect(lambda checked, t=text: self._on_choice_clicked(t))

            row = i // 2
            col = i % 2

            if num_choices == 1 or (i == 2 and num_choices == 3):
                self._grid_layout.addWidget(btn, row, col, 1, 2)
            else:
                self._grid_layout.addWidget(btn, row, col)

        self.show()
        self.adjustSize()

    def clear_choices(self):
        while self._grid_layout.count():
            child = self._grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.hide()

    def _on_choice_clicked(self, text: str):
        self.clear_choices()
        self.choice_selected.emit(text)

class RPGOpenSceneDialog(QtWidgets.QDialog):
    def __init__(self, scene_title: str, entry_count: int, parent=None):
        super().__init__(parent)
        self.result_action = "cancel"
        self.translations = _load_translations()
        self.setWindowTitle(self.translations.get("open_scene_title", "Soul Stage — Open Scene"))
        self.setMinimumWidth(480)
        self.setFixedHeight(280)
        self.setStyleSheet("""
            QDialog { background-color: #0d0d10; color: #e8e8e8; }
            QLabel { background: transparent; border: none; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        title_row = QHBoxLayout()
        title_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        scene_name = QLabel(scene_title)
        scene_name.setFont(_font("Inter Tight SemiBold", 15))
        scene_name.setStyleSheet("color: #ffffff;")
        title_col.addWidget(scene_name)
        sub = QLabel(self.translations.get("open_scene_has_history", "This scene has saved history"))
        sub.setFont(_font("Inter Tight Medium", 10))
        sub.setStyleSheet("color: rgba(255,255,255,0.45);")
        title_col.addWidget(sub)
        title_row.addLayout(title_col, 1)
        root.addLayout(title_row)
        root.addSpacing(20)
        root.addWidget(_rpg_divider())
        root.addSpacing(16)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(10)

        def make_choice_card(icon_path, label, desc, color_rgb, action):
            card = QFrame()
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            r, g, b = color_rgb.split(",")
            card.setStyleSheet(f"""
                QFrame {{
                    background: rgba({r},{g},{b},0.08);
                    border: 1px solid rgba({r},{g},{b},0.25);
                    border-top: 1px solid rgba({r},{g},{b},0.40);
                    border-radius: 12px;
                    padding: 2px;
                }}
                QFrame:hover {{
                    background: rgba({r},{g},{b},0.16);
                    border-color: rgba({r},{g},{b},0.50);
                }}
            """)
            card_l = QVBoxLayout(card)
            card_l.setContentsMargins(14, 12, 14, 12)
            card_l.setSpacing(4)
            ic = QLabel()
            px = QPixmap(icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            ic.setPixmap(px)
            ic.setStyleSheet("background:transparent; border:none;")
            card_l.addWidget(ic)
            lbl_w = QLabel(label)
            lbl_w.setFont(_font("Inter Tight SemiBold", 11))
            lbl_w.setStyleSheet(f"color: rgba({r},{g},{b},1.0); background:transparent; border:none;")
            card_l.addWidget(lbl_w)
            desc_w = QLabel(desc)
            desc_w.setFont(_font("Inter Tight Medium", 9))
            desc_w.setWordWrap(True)
            desc_w.setStyleSheet("color: rgba(200,200,210,0.55); background:transparent; border:none;")
            card_l.addWidget(desc_w)

            def click_handler(ev, a=action):
                if ev.button() == Qt.MouseButton.LeftButton:
                    self.result_action = a
                    self.accept()
            card.mousePressEvent = click_handler
            return card

        cards_row.addWidget(make_choice_card(
            "app/gui/icons/play.png", 
            self.translations.get("continue_session", "Continue"), 
            self.translations.get("open_scene_continue_desc", "Load {count} saved messages and continue").replace("{count}", str(entry_count)),
            "80,160,255", "continue"
        ))
        cards_row.addWidget(make_choice_card(
            "app/gui/icons/regen.png", 
            self.translations.get("new_session", "New Session"), 
            self.translations.get("open_scene_new_desc", "Start fresh — history will be cleared"),
            "255,120,60", "new"
        ))
        root.addLayout(cards_row, 1)
        root.addSpacing(16)

        cancel_row = QHBoxLayout()
        cancel_row.addStretch()
        btn_cancel = _rpg_ghost_btn(self.translations.get("cancel", "Cancel"))
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        cancel_row.addWidget(btn_cancel)
        root.addLayout(cancel_row)

    @staticmethod
    def ask(scene_title: str, entry_count: int, parent=None) -> str:
        dlg = RPGOpenSceneDialog(scene_title, entry_count, parent)
        dlg.exec()
        return dlg.result_action

class RPGMemorySelectDialog(QtWidgets.QDialog):
    def __init__(self, party_names: list, parent=None):
        super().__init__(parent)
        self._selected = ""
        self.translations = _load_translations()
        
        self.setWindowTitle(self.translations.get("memory_select_title", "Soul Memory"))
        self.setMinimumWidth(420)
        
        base_height = 180
        self.setFixedHeight(base_height + len(party_names) * 58)
        
        self.setStyleSheet("""
            QDialog { background-color: #0d0d10; color: #e8e8e8; }
            QLabel { background: transparent; border: none; }
        """)

        def _set_font(widget, family="Inter Tight Medium", size=12, bold=False):
            f = QtGui.QFont(family, size)
            if bold:
                f.setWeight(QtGui.QFont.Weight.Bold)
            f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
            widget.setFont(f)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(0)

        header_row = QHBoxLayout()
        header_row.setSpacing(14)
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon("app/gui/icons/soulMemory.png").pixmap(26, 26))
        header_row.addWidget(icon_lbl)
        
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        
        title_lbl = QLabel("SOUL MEMORY")
        _set_font(title_lbl, "Inter Tight SemiBold", 13, bold=True)
        title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); letter-spacing: 1.5px;")
        title_col.addWidget(title_lbl)
        
        sub_lbl = QLabel(self.translations.get("memory_select_query", "Whose memories would you like to view?"))
        _set_font(sub_lbl, "Inter Tight Medium", 10)
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.45);")
        title_col.addWidget(sub_lbl)
        
        header_row.addLayout(title_col, 1)
        root.addLayout(header_row)
        
        root.addSpacing(16)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: rgba(255,255,255,0.05); border: none;")
        root.addWidget(divider)
        
        root.addSpacing(16)

        for name in party_names:
            card = QFrame()
            card.setObjectName("memory_card")
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setFixedHeight(50)
            card.setStyleSheet("""
                QFrame#memory_card {
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 10px;
                }
                QFrame#memory_card:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-color: rgba(255, 255, 255, 0.2);
                }
            """)
            card_l = QHBoxLayout(card)
            card_l.setContentsMargins(12, 0, 16, 0)
            card_l.setSpacing(12)

            av_lbl = QLabel()
            av_px = _get_char_avatar_pixmap(name)
            av_lbl.setPixmap(_round_pixmap(av_px, 30))
            av_lbl.setFixedSize(30, 30)
            card_l.addWidget(av_lbl)

            name_lbl = QLabel(name)
            _set_font(name_lbl, "Inter Tight SemiBold", 12)
            name_lbl.setStyleSheet("color: #ffffff;")
            card_l.addWidget(name_lbl, 1)

            arrow = QLabel("→")
            _set_font(arrow, "Inter Tight Medium", 14)
            arrow.setStyleSheet("color: rgba(255,255,255,0.25);")
            card_l.addWidget(arrow)

            def on_card_click(ev, n=name):
                if ev.button() == Qt.MouseButton.LeftButton:
                    self._selected = n
                    self.accept()
            card.mousePressEvent = on_card_click
            root.addWidget(card)
            root.addSpacing(8)

        root.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
        _set_font(btn_cancel, "Inter Tight Medium", 12)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_cancel.setFixedSize(110, 38)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)
        
        root.addLayout(btn_row)

    @staticmethod
    def ask(party_names: list, parent=None) -> str:
        if len(party_names) == 1:
            return party_names[0]
        dlg = RPGMemorySelectDialog(party_names, parent)
        dlg.exec()
        return dlg._selected

class WorldInfoDialog(QtWidgets.QDialog):
    world_state_changed = pyqtSignal(dict)

    _TAB_ACTIVE = """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                        stop:0 rgba(255, 255, 255, 0.1), 
                                        stop:1 rgba(255, 255, 255, 0.04));
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-radius: 10px;
            font-family: 'Inter Tight SemiBold'; 
            font-size: 13px;
            padding: 12px 16px;
            margin: 3px 0;
            text-align: left;
        }
    """
    
    _TAB_IDLE = """
        QPushButton {
            background: transparent;
            border: 1px solid transparent;
            border-radius: 10px;
            color: rgba(255, 255, 255, 0.45);
            font-family: 'Inter Tight SemiBold'; 
            font-size: 13px;
            padding: 12px 16px;
            margin: 3px 0;
            text-align: left;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.04);
            color: rgba(255, 255, 255, 0.8);
        }
    """

    def __init__(self, world_state, npc_registry=None, parent=None):
        super().__init__(parent)
        self.world_state  = world_state
        self.npc_registry = npc_registry
        self.translations = _load_translations()
        self.setWindowTitle(self.translations.get("world_state_title", "World State — Soul Stage"))
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0c0e;
                color: #e8e8e8;
            }
            QLabel { background: transparent; border: none; }
            
            QLineEdit, QTextEdit {
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                color: rgba(240, 240, 240, 0.95);
                font-family: 'Inter Tight Medium'; font-size: 13px;
                padding: 10px 14px;
                selection-background-color: rgba(255, 255, 255, 0.20);
            }
            QLineEdit:focus, QTextEdit:focus {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.25);
            }
            
            QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.15); border-radius: 3px; min-height: 24px; }
            QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.3); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollArea { background: transparent; border: none; }
        """)
        self._build_ui()
        self._populate()

    def _create_font(self, family="Inter Tight Medium", size=12, bold=False):
        f = QtGui.QFont(family, size)
        if bold:
            f.setWeight(QtGui.QFont.Weight.Bold)
        f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
        return f

    def _set_font(self, widget, family="Inter Tight Medium", size=12, bold=False):
        widget.setFont(self._create_font(family, size, bold))

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        self._set_font(lbl, "Inter Tight SemiBold", 10, bold=True)
        lbl.setStyleSheet("color: rgba(255, 255, 255, 0.45); letter-spacing: 2px;")
        return lbl

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("world_header")
        header.setFixedHeight(64)
        header.setStyleSheet("QFrame#world_header { background: rgba(20, 20, 24, 0.8); border: none; }")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(14)

        world_icon = QLabel()
        world_icon.setPixmap(QIcon(str(Path("app/gui/icons/soul_stage/world.svg"))).pixmap(26, 26))
        world_icon.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(world_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_lbl = QLabel(self.translations.get("world_state_title", "WORLD STATE"))
        self._set_font(title_lbl, "Inter Tight SemiBold", 13, bold=True)
        title_lbl.setStyleSheet("color: rgba(255,255,255,0.95); letter-spacing: 1.5px; background: transparent; border: none;")
        title_col.addWidget(title_lbl)

        self._header_sub = QLabel("")
        self._set_font(self._header_sub, "Inter Tight Medium", 10)
        self._header_sub.setStyleSheet("color: rgba(255,255,255,0.4); background: transparent; border: none;")
        title_col.addWidget(self._header_sub)
        hl.addLayout(title_col, 1)

        root.addWidget(header)

        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("world_sidebar")
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet("""
            QFrame#world_sidebar {
                background-color: rgba(15, 15, 18, 0.5);
                border: none;
                border-right: 1px solid rgba(255, 255, 255, 0.03);
            }
        """)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 20, 12, 20)
        sl.setSpacing(0)

        self._tabs = QStackedWidget()
        self._tabs.setStyleSheet("background: transparent;")
        self._tab_buttons: list[QPushButton] = []

        tab_defs =[
            (self.translations.get("tab_scene", "Scene"), self._build_scene_tab),
            (self.translations.get("tab_facts", "Key Facts"), self._build_facts_tab),
            (self.translations.get("tab_inventory", "Inventory"), self._build_inventory_tab),
            (self.translations.get("tab_status", "Status"), self._build_status_tab),
            (self.translations.get("tab_resources", "Resources"), self._build_resources_tab),
            (self.translations.get("tab_lore", "Lore Cards"), self._build_lore_tab),
            (self.translations.get("tab_campaign", "Campaign Board"), self._build_campaign_tab),
            (self.translations.get("tab_arcs", "Story Arcs"), self._build_arcs_tab),
            (self.translations.get("tab_relationships", "Relationships"), self._build_relationships_tab),
            (self.translations.get("tab_character_states", "Character States"), self._build_overlays_tab),
            (self.translations.get("tab_npcs", "Active NPCs"), self._build_npcs_tab),
        ]
        
        for i, (label, builder) in enumerate(tab_defs):
            btn = QPushButton(label)
            self._set_font(btn, "Inter Tight SemiBold", 13)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(self._TAB_ACTIVE if i == 0 else self._TAB_IDLE)
            btn.clicked.connect(lambda _, idx=i: self._switch_tab(idx))
            sl.addWidget(btn)
            self._tab_buttons.append(btn)
            self._tabs.addWidget(builder())

        sl.addStretch()
        body_layout.addWidget(sidebar)

        content_wrap = QWidget()
        content_wrap.setStyleSheet("background: transparent;")
        cw_l = QVBoxLayout(content_wrap)
        cw_l.setContentsMargins(0, 0, 0, 0)
        cw_l.addWidget(self._tabs)
        body_layout.addWidget(content_wrap, 1)

        root.addLayout(body_layout, 1)

        footer = QFrame()
        footer.setObjectName("world_footer")
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame#world_footer { background: rgba(20, 20, 24, 0.5); border: none; border-top: 1px solid rgba(255,255,255,0.03); }")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.setSpacing(12)
        
        btn_cancel = QPushButton(self.translations.get("cancel", "Cancel"))
        self._set_font(btn_cancel, "Inter Tight Medium", 12)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_cancel.setFixedHeight(38)
        btn_cancel.setFixedWidth(120)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.5);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.2);
                color: rgba(255, 255, 255, 0.9);
            }
        """)
        btn_cancel.clicked.connect(self.reject)
        fl.addWidget(btn_cancel)
        
        fl.addStretch()
        
        btn_save = QPushButton(self.translations.get("btn_apply_changes", "Apply Changes"))
        self._set_font(btn_save, "Inter Tight SemiBold", 12)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_save.setFixedHeight(38)
        btn_save.setFixedWidth(180)
        btn_save.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
                color: rgba(255, 255, 255, 0.95);
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                border-color: rgba(255, 255, 255, 0.3);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 0.05);
            }
        """)
        btn_save.clicked.connect(self._on_save)
        fl.addWidget(btn_save)
        
        root.addWidget(footer)

    def _switch_tab(self, idx: int):
        self._tabs.setCurrentIndex(idx)
        for i, btn in enumerate(self._tab_buttons):
            btn.setStyleSheet(self._TAB_ACTIVE if i == idx else self._TAB_IDLE)

    def _scroll_wrap(self, widget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sa.setWidget(widget)
        return sa

    def _inner_widget(self) -> tuple:
        w = QWidget()
        w.setStyleSheet("background: transparent; background-color: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(32, 28, 32, 28)
        l.setSpacing(20)
        return w, l

    def _field_col(self, layout, label_text: str, widget, hint_text: str = ""):
        col = QVBoxLayout()
        col.setSpacing(6)
        
        lbl = QLabel(label_text)
        self._set_font(lbl, "Inter Tight Medium", 11)
        lbl.setStyleSheet("color: rgba(255,255,255,0.55);")
        col.addWidget(lbl)
        
        if hint_text:
            hint = QLabel(hint_text)
            self._set_font(hint, "Inter Tight Medium", 9)
            hint.setStyleSheet("color: rgba(255,255,255,0.3); margin-top: -4px;")
            col.addWidget(hint)
            
        col.addWidget(widget)
        layout.addLayout(col)

    def _build_scene_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_environment", "Environment Setup")))
        
        self.edit_location = QLineEdit()
        self.edit_location.setFixedHeight(42)
        self._set_font(self.edit_location, "Inter Tight Medium", 13)
        self._field_col(l, self.translations.get("field_location", "Location"), self.edit_location)
        
        self.edit_time = QLineEdit()
        self.edit_time.setFixedHeight(42)
        self._set_font(self.edit_time, "Inter Tight Medium", 13)
        self._field_col(l, self.translations.get("field_time", "Time of day"), self.edit_time)
        
        self.edit_atmosphere = QLineEdit()
        self.edit_atmosphere.setFixedHeight(42)
        self._set_font(self.edit_atmosphere, "Inter Tight Medium", 13)
        self._field_col(l, self.translations.get("field_atmosphere", "Atmosphere"), self.edit_atmosphere)
        
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_facts_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_memory", "World Memory")))
        
        self.edit_facts = QTextEdit()
        self.edit_facts.setPlaceholderText("danger level: high\nbridge: destroyed\nbonfire: burning")
        self.edit_facts.setMinimumHeight(240)
        self._set_font(self.edit_facts, "Inter Tight Medium", 13)
        
        self._field_col(l, self.translations.get("tab_facts", "Key Facts"), self.edit_facts, self.translations.get("field_facts_hint", 'Format: "key: value" (one per line)'))
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_inventory_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_player_items", "Player Items")))
        
        self.edit_inventory = QTextEdit()
        self.edit_inventory.setPlaceholderText("rusty sword\n3 apples\nmap of the area")
        self.edit_inventory.setMinimumHeight(240)
        self._set_font(self.edit_inventory, "Inter Tight Medium", 13)
        
        self._field_col(l, self.translations.get("tab_inventory", "Inventory"), self.edit_inventory, self.translations.get("field_inventory_hint", "One item per line"))
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_status_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_player_conditions", "Player Conditions")))
        
        self.edit_status = QTextEdit()
        self.edit_status.setPlaceholderText("wounded in shoulder\nexhausted\npoisoned")
        self.edit_status.setMinimumHeight(240)
        self._set_font(self.edit_status, "Inter Tight Medium", 13)
        
        self._field_col(l, self.translations.get("field_status_effects", "Status Effects"), self.edit_status, self.translations.get("field_status_hint", "One condition per line"))
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_resources_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_resources", "Resources & Skills")))

        self.edit_resources = QTextEdit()
        self.edit_resources.setPlaceholderText("health: 8/10\nenergy: 4/6\nstress: 2/6")
        self.edit_resources.setMinimumHeight(140)
        self._set_font(self.edit_resources, "Inter Tight Medium", 13)
        self._field_col(
            l, self.translations.get("field_resources", "Resources"), self.edit_resources,
            self.translations.get("field_resources_hint", 'Format: "name: current/max" (one per line)')
        )

        self.edit_skills = QTextEdit()
        self.edit_skills.setPlaceholderText("stealth: +3\npersuasion: +1\nathletics: -1")
        self.edit_skills.setMinimumHeight(140)
        self._set_font(self.edit_skills, "Inter Tight Medium", 13)
        self._field_col(
            l, self.translations.get("field_skills", "Skills"), self.edit_skills,
            self.translations.get("field_skills_hint", 'Format: "skill: modifier" (-5 to +10, one per line)')
        )

        l.addStretch()
        return self._scroll_wrap(w)

    def _build_lore_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_lore", "Campaign Lore")))

        hint = QLabel(self.translations.get(
            "hint_lore_format",
            "One card per block, separated by a blank line. Cards are injected into the "
            "story only when their triggers appear in the scene."
        ))
        self._set_font(hint, "Inter Tight Medium", 10)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-bottom: 4px;")
        l.addWidget(hint)

        self.edit_lore = QTextEdit()
        self.edit_lore.setPlaceholderText(
            "### King Alaric\n"
            "category: npc\n"
            "triggers: king, alaric, throne\n"
            "visibility: party\n"
            "He secretly poisoned his brother to take the throne.\n"
        )
        self.edit_lore.setMinimumHeight(320)
        self._set_font(self.edit_lore, "Inter Tight Medium", 12)
        l.addWidget(self.edit_lore)
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_campaign_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_campaign", "Campaign Board")))

        self.edit_objectives = QTextEdit()
        self.edit_objectives.setPlaceholderText(
            "Find the missing heir | 1/3 | active | Rumors point toward the northern port.\n"
            "Win the king's trust | 3/3 | complete | \n"
        )
        self.edit_objectives.setMinimumHeight(180)
        self._set_font(self.edit_objectives, "Inter Tight Medium", 12)
        self._field_col(
            l, self.translations.get("field_objectives", "Objectives"), self.edit_objectives,
            self.translations.get("field_objectives_hint",
                'Format: "title | current/max | status | description" (status: active/complete/failed)')
        )

        self.edit_clocks = QTextEdit()
        self.edit_clocks.setPlaceholderText(
            "Guards Alerted | 0/4 | Rises each time the party is seen doing something suspicious.\n"
            "Ritual Completes | 2/6 | The cultists need six nights of moonlight.\n"
        )
        self.edit_clocks.setMinimumHeight(180)
        self._set_font(self.edit_clocks, "Inter Tight Medium", 12)
        self._field_col(
            l, self.translations.get("field_clocks", "Clocks"), self.edit_clocks,
            self.translations.get("field_clocks_hint", 'Format: "title | current/max | description"')
        )

        l.addStretch()
        return self._scroll_wrap(w)

    def _build_arcs_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_arcs", "Story Arcs")))

        hint = QLabel(self.translations.get(
            "hint_arcs_format",
            "This is where you gate your plot. An arc in \"locked\" stage does not exist for "
            "any character — nobody will mention it or hint at it. Set it to \"available\" once "
            "the player has found the lead that should unlock it, or \"active\" once it's fully "
            "underway. \"trigger\" is a note to the GM about what should cause the unlock — it is "
            "never shown to characters."
        ))
        self._set_font(hint, "Inter Tight Medium", 10)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-bottom: 4px;")
        l.addWidget(hint)

        self.edit_arcs = QTextEdit()
        self.edit_arcs.setPlaceholderText(
            "### Investigation into the Theft\n"
            "stage: locked\n"
            "trigger: player finds the torn ledger page in the quartermaster's room\n"
            "notes: The quartermaster has been skimming coin from the payroll for months.\n"
        )
        self.edit_arcs.setMinimumHeight(320)
        self._set_font(self.edit_arcs, "Inter Tight Medium", 12)
        l.addWidget(self.edit_arcs)
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_relationships_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_relationships", "Relationships")))

        hint = QLabel(self.translations.get(
            "hint_relationships_format",
            "How one character feels about and perceives another — usually a party member or "
            "NPC's view of PLAYER, but it can be between any two actors. This is injected "
            "directly into that character's own prompt, so it's never forgotten. Affinity runs "
            "-100 (hostile) to 100 (devoted). \"role\" is how the subject currently sees the "
            "target's status or title — independent of affinity."
        ))
        self._set_font(hint, "Inter Tight Medium", 10)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-bottom: 4px;")
        l.addWidget(hint)

        self.edit_relationships = QTextEdit()
        self.edit_relationships.setPlaceholderText(
            "Garen -> PLAYER | 45 | captain | respects_authority, owes_debt\n"
            "Vivy -> Holo | -15 | rival | distrustful\n"
        )
        self.edit_relationships.setMinimumHeight(280)
        self._set_font(self.edit_relationships, "Inter Tight Medium", 12)
        self._field_col(
            l, self.translations.get("field_relationships", "Relationships"), self.edit_relationships,
            self.translations.get("field_relationships_hint",
                'Format: "subject -> target | affinity(-100..100) | role_view | tag1, tag2"')
        )
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_overlays_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_character_states", "Character States")))

        hint = QLabel(self.translations.get(
            "hint_overlays_format",
            "A character's own evolving state — their current role/title and any personal "
            "facts worth tracking (loyalty, a secret, an internal conflict). This travels with "
            "the character and shows up in their own prompt, separate from the static "
            "character card."
        ))
        self._set_font(hint, "Inter Tight Medium", 10)
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(255,255,255,0.35); margin-bottom: 4px;")
        l.addWidget(hint)

        self.edit_overlays = QTextEdit()
        self.edit_overlays.setPlaceholderText(
            "### Garen\n"
            "role: captain\n"
            "arc: reconciled\n"
            "loyalty: torn between duty and player\n"
            "secret: knows about the theft but hasn't reported it\n"
        )
        self.edit_overlays.setMinimumHeight(320)
        self._set_font(self.edit_overlays, "Inter Tight Medium", 12)
        l.addWidget(self.edit_overlays)
        l.addStretch()
        return self._scroll_wrap(w)

    def _build_npcs_tab(self) -> QWidget:
        w, l = self._inner_widget()
        l.addWidget(self._section_label(self.translations.get("section_npcs", "Characters in Scene")))
        
        hint = QLabel(self.translations.get("hint_npc_readonly", "NPCs currently spawned by the engine (read-only)"))
        hint.setObjectName("hint")
        self._set_font(hint, "Inter Tight Medium", 10)
        l.addWidget(hint)
        
        npcs_container_widget = QWidget()
        npcs_container_widget.setObjectName("npcs_container")
        
        self.npcs_container = QVBoxLayout(npcs_container_widget)
        self.npcs_container.setSpacing(8)
        self.npcs_container.setContentsMargins(0, 0, 0, 0)
        
        l.addWidget(npcs_container_widget)
        l.addStretch()

        hint.setStyleSheet("color: rgba(255,255,255,0.40); background: transparent; background-color: transparent; margin-bottom: 4px;")
        npcs_container_widget.setStyleSheet("QWidget#npcs_container { background: transparent; background-color: transparent; }")
        
        return self._scroll_wrap(w)

    @staticmethod
    def _format_resources(resources: dict) -> str:
        return "\n".join(f"{name}: {pool.get('current', 0)}/{pool.get('max', 0)}" for name, pool in resources.items())

    @staticmethod
    def _parse_resources(text: str, existing: dict) -> dict:
        result = copy.deepcopy(existing)
        for line in text.splitlines():
            if ":" not in line:
                continue
            name, _, rest = line.partition(":")
            name = name.strip().lower()
            rest = rest.strip()
            if not name or "/" not in rest:
                continue
            cur_s, _, max_s = rest.partition("/")
            try:
                cur, mx = int(cur_s.strip()), int(max_s.strip())
            except ValueError:
                continue
            mx = max(1, min(999, mx))
            cur = max(0, min(mx, cur))
            result[name] = {"current": cur, "max": mx}
        return result

    @staticmethod
    def _format_skills(skills: dict) -> str:
        return "\n".join(f"{name}: {value:+d}" for name, value in skills.items())

    @staticmethod
    def _parse_skills(text: str) -> dict:
        result = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            name, _, value = line.partition(":")
            name = name.strip().lower()
            if not name:
                continue
            try:
                result[name] = max(-5, min(10, int(value.strip())))
            except ValueError:
                continue
        return result

    @staticmethod
    def _format_lore_cards(cards: list) -> str:
        blocks = []
        for c in cards:
            lines = [f"### {c.get('title', 'Untitled')}"]
            lines.append(f"category: {c.get('category', 'Lore')}")
            lines.append(f"triggers: {', '.join(c.get('triggers', []))}")
            lines.append(f"visibility: {c.get('visibility', 'party')}")
            if not c.get("enabled", True):
                lines.append("enabled: false")
            lines.append(str(c.get("content", "")))
            lines.append(f"[id: {c.get('id', '')}]")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_lore_cards(text: str) -> list:
        cards = []
        blocks = re.split(r"\n\s*\n(?=###\s)", text.strip())
        for block in blocks:
            block = block.strip()
            if not block.startswith("###"):
                continue
            lines = block.splitlines()
            title = lines[0][3:].strip()
            data = {"title": title, "category": "Lore", "triggers": [], "visibility": "party", "enabled": True}
            content_lines = []
            for line in lines[1:]:
                stripped = line.strip()
                m_id = re.match(r"^\[id:\s*(.*?)\]$", stripped)
                if m_id:
                    if m_id.group(1).strip():
                        data["id"] = m_id.group(1).strip()
                    continue
                if stripped.lower().startswith("category:"):
                    data["category"] = stripped.split(":", 1)[1].strip()
                elif stripped.lower().startswith("triggers:"):
                    data["triggers"] = [t.strip() for t in stripped.split(":", 1)[1].split(",") if t.strip()]
                elif stripped.lower().startswith("visibility:"):
                    data["visibility"] = stripped.split(":", 1)[1].strip()
                elif stripped.lower().startswith("enabled:"):
                    data["enabled"] = stripped.split(":", 1)[1].strip().lower() not in ("false", "0", "no")
                else:
                    content_lines.append(line)
            data["content"] = "\n".join(content_lines).strip()
            if data["title"] or data["content"]:
                cards.append(data)
        return cards

    @staticmethod
    def _format_campaign_entries(entries: list, is_clock: bool) -> str:
        lines = []
        for e in entries:
            if is_clock:
                lines.append(f"{e.get('title','')} | {e.get('current',0)}/{e.get('max',4)} | {e.get('description','')}")
            else:
                lines.append(f"{e.get('title','')} | {e.get('current',0)}/{e.get('max',1)} | {e.get('status','active')} | {e.get('description','')}")
        return "\n".join(lines)

    @staticmethod
    def _parse_campaign_entries(text: str, is_clock: bool) -> list:
        entries = []
        for line in text.splitlines():
            if not line.strip() or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            title = parts[0]
            if not title:
                continue
            cur, mx = 0, (4 if is_clock else 1)
            if len(parts) > 1 and "/" in parts[1]:
                cur_s, _, mx_s = parts[1].partition("/")
                try:
                    cur, mx = int(cur_s.strip()), int(mx_s.strip())
                except ValueError:
                    pass
            if is_clock:
                description = parts[2] if len(parts) > 2 else ""
                entries.append({"title": title, "current": cur, "max": mx, "description": description})
            else:
                status = parts[2].strip().lower() if len(parts) > 2 and parts[2].strip() else "active"
                description = parts[3] if len(parts) > 3 else ""
                entries.append({"title": title, "current": cur, "max": mx, "status": status, "description": description})
        return entries

    @staticmethod
    def _format_arcs(arcs: list) -> str:
        blocks = []
        for a in arcs:
            lines = [f"### {a.get('title', 'Untitled arc')}"]
            lines.append(f"stage: {a.get('stage', 'locked')}")
            lines.append(f"trigger: {a.get('trigger_hint', '')}")
            if a.get("gm_notes"):
                lines.append(f"notes: {a.get('gm_notes', '')}")
            lines.append(f"[id: {a.get('id', '')}]")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_arcs(text: str) -> list:
        arcs = []
        blocks = re.split(r"\n\s*\n(?=###\s)", text.strip())
        for block in blocks:
            block = block.strip()
            if not block.startswith("###"):
                continue
            lines = block.splitlines()
            title = lines[0][3:].strip()
            if not title:
                continue
            data = {"title": title, "stage": "locked", "trigger_hint": ""}
            notes_lines = []
            for line in lines[1:]:
                stripped = line.strip()
                m_id = re.match(r"^\[id:\s*(.*?)\]$", stripped)
                if m_id:
                    if m_id.group(1).strip():
                        data["id"] = m_id.group(1).strip()
                    continue
                if stripped.lower().startswith("stage:"):
                    stage = stripped.split(":", 1)[1].strip().lower()
                    data["stage"] = stage if stage in ("locked", "available", "active", "resolved") else "locked"
                elif stripped.lower().startswith("trigger:"):
                    data["trigger_hint"] = stripped.split(":", 1)[1].strip()
                elif stripped.lower().startswith("notes:"):
                    notes_lines.append(stripped.split(":", 1)[1].strip())
                elif stripped:
                    notes_lines.append(line)
            data["gm_notes"] = "\n".join(notes_lines).strip()
            arcs.append(data)
        return arcs

    @staticmethod
    def _format_relationships(rels: list) -> str:
        lines = []
        for r in rels:
            tags = ", ".join(r.get("tags", []))
            lines.append(f"{r.get('subject','')} -> {r.get('target','')} | {r.get('affinity',0)} | {r.get('role_view','')} | {tags}")
        return "\n".join(lines)

    @staticmethod
    def _parse_relationships(text: str) -> list:
        rels = []
        for line in text.splitlines():
            line = line.strip()
            if not line or "->" not in line:
                continue
            left, _, rest = line.partition("->")
            subject = left.strip()
            parts = [p.strip() for p in rest.split("|")]
            target = parts[0] if parts else ""
            if not subject or not target:
                continue
            affinity = 0
            if len(parts) > 1 and parts[1]:
                try:
                    affinity = max(-100, min(100, int(parts[1])))
                except ValueError:
                    pass
            role_view = parts[2] if len(parts) > 2 else ""
            tags = [t.strip() for t in parts[3].split(",")] if len(parts) > 3 and parts[3] else []
            tags = [t for t in tags if t]
            rels.append({"subject": subject, "target": target, "affinity": affinity, "role_view": role_view, "tags": tags})
        return rels

    @staticmethod
    def _format_overlays(overlays: list) -> str:
        blocks = []
        for o in overlays:
            lines = [f"### {o.get('name', '')}"]
            if o.get("current_role"):
                lines.append(f"role: {o['current_role']}")
            if o.get("arc_stage"):
                lines.append(f"arc: {o['arc_stage']}")
            for k, v in o.get("mutable_facts", {}).items():
                lines.append(f"{k.replace('_', ' ')}: {v}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    @staticmethod
    def _parse_overlays(text: str) -> list:
        overlays = []
        blocks = re.split(r"\n\s*\n(?=###\s)", text.strip())
        for block in blocks:
            block = block.strip()
            if not block.startswith("###"):
                continue
            lines = block.splitlines()
            name = lines[0][3:].strip()
            if not name:
                continue
            data = {"name": name, "current_role": "", "arc_stage": "", "mutable_facts": {}}
            for line in lines[1:]:
                stripped = line.strip()
                if not stripped or ":" not in stripped:
                    continue
                key, _, value = stripped.partition(":")
                key_l = key.strip().lower()
                value = value.strip()
                if key_l == "role":
                    data["current_role"] = value
                elif key_l == "arc":
                    data["arc_stage"] = value
                else:
                    data["mutable_facts"][key.strip()] = value
            overlays.append(data)
        return overlays

    def _populate(self):
        ws = self.world_state
        
        location_text = ws.location if ws.location else "Unknown"
        time_text = ws.time_of_day if ws.time_of_day else "Unknown"
        self._header_sub.setText(f"{location_text}  ·  {time_text}")

        self.edit_location.setText(ws.location)
        self.edit_time.setText(ws.time_of_day)
        self.edit_atmosphere.setText(ws.atmosphere)
        self.edit_facts.setPlainText("\n".join(f"{k}: {v}" for k, v in ws.key_facts.items()))
        self.edit_inventory.setPlainText("\n".join(ws.player_inventory))
        self.edit_status.setPlainText("\n".join(ws.player_status))
        self.edit_resources.setPlainText(self._format_resources(ws.resources))
        self.edit_skills.setPlainText(self._format_skills(ws.player_skills))
        self.edit_lore.setPlainText(self._format_lore_cards(ws.lore_registry.to_dict()))
        board = ws.campaign_board.to_dict()
        self.edit_objectives.setPlainText(self._format_campaign_entries(board.get("objectives", []), is_clock=False))
        self.edit_clocks.setPlainText(self._format_campaign_entries(board.get("clocks", []), is_clock=True))
        self.edit_arcs.setPlainText(self._format_arcs(ws.arc_registry.to_dict()))
        self.edit_relationships.setPlainText(self._format_relationships(ws.relationship_graph.to_dict()))
        self.edit_overlays.setPlainText(self._format_overlays(ws.overlay_registry.to_dict()))

        if self.npc_registry:
            npcs = self.npc_registry.list_active()
            if npcs:
                for i, npc in enumerate(npcs):
                    card = QFrame()
                    card.setObjectName(f"npc_card_{i}")
                    card.setFixedHeight(54)
                    card.setStyleSheet(f"""
                        QFrame#npc_card_{i} {{
                            background: rgba(255,255,255,0.03);
                            border: 1px solid rgba(255,255,255,0.06);
                            border-radius: 10px;
                        }}
                    """)
                    card_l = QHBoxLayout(card)
                    card_l.setContentsMargins(16, 0, 16, 0)
                    card_l.setSpacing(12)

                    name_lbl = QLabel(npc.name)
                    name_lbl.setObjectName("npc_name_lbl")
                    self._set_font(name_lbl, "Inter Tight SemiBold", 13)
                    name_lbl.setStyleSheet("QLabel#npc_name_lbl { color: #ffffff; background: transparent; }")
                    card_l.addWidget(name_lbl, 1)

                    arch_lbl = QLabel(npc.archetype.upper())
                    arch_lbl.setObjectName("npc_arch_lbl")
                    self._set_font(arch_lbl, "Inter Tight Medium", 10)
                    arch_lbl.setStyleSheet("QLabel#npc_arch_lbl { color: rgba(255,255,255,0.4); letter-spacing: 1px; background: transparent; }")
                    card_l.addWidget(arch_lbl)

                    self.npcs_container.addWidget(card)
            else:
                no_npc = QLabel(self.translations.get("no_active_npcs", "No active NPCs in this scene"))
                no_npc.setObjectName("npc_empty_lbl")
                self._set_font(no_npc, "Inter Tight Medium", 12)
                no_npc.setStyleSheet("QLabel#npc_empty_lbl { color: rgba(255,255,255,0.25); margin-top: 10px; background: transparent; }")
                self.npcs_container.addWidget(no_npc)

    def _on_save(self):
        ws = self.world_state
        ws.location    = self.edit_location.text().strip() or ws.location
        ws.time_of_day = self.edit_time.text().strip() or ws.time_of_day
        ws.atmosphere  = self.edit_atmosphere.text().strip()
        new_facts = {}
        for line in self.edit_facts.toPlainText().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                k, v = k.strip(), v.strip()
                if k:
                    new_facts[k] = v
        ws.key_facts = new_facts
        ws.player_inventory =[
            it.strip() for it in self.edit_inventory.toPlainText().splitlines() if it.strip()
        ]
        ws.player_status =[
            st.strip() for st in self.edit_status.toPlainText().splitlines() if st.strip()
        ]

        ws.resources = self._parse_resources(self.edit_resources.toPlainText(), ws.resources)
        ws.player_skills = self._parse_skills(self.edit_skills.toPlainText())

        parsed_cards = self._parse_lore_cards(self.edit_lore.toPlainText())
        ws.lore_registry.cards = {}
        for card_data in parsed_cards:
            ws.lore_registry.upsert(card_data)

        parsed_objectives = self._parse_campaign_entries(self.edit_objectives.toPlainText(), is_clock=False)
        parsed_clocks = self._parse_campaign_entries(self.edit_clocks.toPlainText(), is_clock=True)
        ws.campaign_board.objectives = []
        for obj_data in parsed_objectives:
            ws.campaign_board.upsert_objective(obj_data)
        ws.campaign_board.clocks = []
        for clk_data in parsed_clocks:
            ws.campaign_board.upsert_clock(clk_data)

        ws.arc_registry.arcs = {}
        for arc_data in self._parse_arcs(self.edit_arcs.toPlainText()):
            ws.arc_registry.upsert(arc_data)

        ws.relationship_graph.replace_all(self._parse_relationships(self.edit_relationships.toPlainText()))

        ws.overlay_registry.overlays = {}
        for ov_data in self._parse_overlays(self.edit_overlays.toPlainText()):
            ws.overlay_registry.replace(
                ov_data["name"], ov_data["current_role"], ov_data["arc_stage"], ov_data["mutable_facts"]
            )

        self.world_state_changed.emit({
            "location": ws.location, "time_of_day": ws.time_of_day,
            "atmosphere": ws.atmosphere, "key_facts": ws.key_facts,
            "player_inventory": ws.player_inventory, "player_status": ws.player_status,
            "resources": ws.resources, "player_skills": ws.player_skills,
            "lore_cards": ws.lore_registry.to_dict(), "campaign_board": ws.campaign_board.to_dict(),
            "story_arcs": ws.arc_registry.to_dict(), "relationships": ws.relationship_graph.to_dict(),
            "character_overlays": ws.overlay_registry.to_dict(),
        })
        self.accept()

class TextEditUserMessage(QTextEdit):
    handle_enter_key = pyqtSignal()
    
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.handle_enter_key.emit()
                event.accept()
        else:
            super().keyPressEvent(event)


class SoulStageChatView(QFrame):
    interrupted       = pyqtSignal()
    exit_clicked      = pyqtSignal()
    open_memory       = pyqtSignal()
    world_info_clicked = pyqtSignal()
    continue_plot     = pyqtSignal()
    choice_made         = pyqtSignal(str)
    export_clicked      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("soul_stage_chat_view")
        self.setStyleSheet("")
        self.scene_data: dict = {}
        self._scene_id: str = ""

        self.translations = _load_translations()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top_bar = QFrame(self)
        self.top_bar.setObjectName("ss_top_bar")
        self.top_bar.setMinimumSize(QtCore.QSize(0, 60))
        self.top_bar.setMaximumSize(QtCore.QSize(16777215, 60))
        self.top_bar.setStyleSheet("""
            QFrame#ss_top_bar {
                background-color: rgba(20, 20, 20, 180);
                border-bottom: 1px solid rgba(255, 255, 255, 15);
            }
            QLabel#scene_title {
                color: rgb(227, 227, 227);
                background: transparent;
            }
        """)
        self.top_bar.setFrameShape(QFrame.Shape.NoFrame)
        self.top_bar.setFrameShadow(QFrame.Shadow.Raised)

        tl = QHBoxLayout(self.top_bar)
        tl.setContentsMargins(20, 9, 20, 9)
        tl.setSpacing(8)

        self.btn_back = QPushButton("←")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_back.setFixedHeight(30)
        self.btn_back.setFont(_font("Inter Tight Medium", 11, bold=True))
        self.btn_back.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,0.7);
                border: 1px solid rgba(255,255,255,0.15); border-radius: 15px; padding: 0 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.1); color: white; }
        """)
        self.btn_back.clicked.connect(self.exit_clicked.emit)
        tl.addWidget(self.btn_back)

        dv0 = QFrame(); dv0.setFrameShape(QFrame.Shape.VLine); dv0.setFixedWidth(1)
        dv0.setStyleSheet("background: rgba(255,255,255,0.08); margin: 10px 4px;")
        tl.addWidget(dv0)

        self.scene_title_lbl = QLabel(self.translations.get("soul_stage_title", "Soul Stage"))
        self.scene_title_lbl.setFont(_font("Inter Tight SemiBold", 12))
        self.scene_title_lbl.setStyleSheet("color: rgba(255,255,255,0.90);")
        tl.addWidget(self.scene_title_lbl)

        dv1 = QFrame(); dv1.setFrameShape(QFrame.Shape.VLine); dv1.setFixedWidth(1)
        dv1.setStyleSheet("background: rgba(255,255,255,0.08); margin: 10px 4px;")
        tl.addWidget(dv1)

        self.party_container = QWidget()
        self.party_container.setStyleSheet("background: transparent;")
        self._party_row = QHBoxLayout(self.party_container)
        self._party_row.setContentsMargins(0, 0, 0, 0)
        self._party_row.setSpacing(4)
        tl.addWidget(self.party_container)

        dv2 = QFrame(); dv2.setFrameShape(QFrame.Shape.VLine); dv2.setFixedWidth(1)
        dv2.setStyleSheet("background: rgba(255,255,255,0.08); margin: 10px 4px;")
        tl.addWidget(dv2)

        combo_style = """
            QComboBox {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 8px;
                color: rgba(255,255,255,0.75);
                font-family: 'Inter Tight Medium';
                font-size: 11px;
                padding: 3px 10px;
                min-height: 22px;
            }
            QComboBox:hover { background: rgba(255,255,255,0.09); border-color: rgba(255,255,255,0.2); }
            QComboBox::drop-down { border: none; width: 16px; }
            QComboBox QAbstractItemView {
                background-color: #1a1a1e; color: #e8e8e8;
                selection-background-color: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.1);
                outline: none;
            }
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem(self.translations.get("mode_say", "💬 Say"), "say")
        self.mode_combo.addItem(self.translations.get("mode_do", "⚔ Do"), "do")
        self.mode_combo.addItem(self.translations.get("mode_think", "💭 Think"), "think")
        self.mode_combo.addItem(self.translations.get("mode_director", "🎬 Director"), "director")
        self.mode_combo.setFixedWidth(110)
        self.mode_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_combo.setStyleSheet(combo_style)
        self.mode_combo.setToolTip(self.translations.get(
            "mode_tooltip",
            "Say: spoken aloud · Do: an action · Think: silent inner thought · "
            "Director: an out-of-character note to the GM (advances the plot, not spoken by you)"
        ))
        tl.addWidget(self.mode_combo)

        target_lbl = QLabel(self.translations.get("target_next_label", "Next:"))
        target_lbl.setFont(_font(size=11))
        target_lbl.setStyleSheet("color: rgba(255,255,255,0.35);")
        tl.addWidget(target_lbl)

        self.target_combo = QtWidgets.QComboBox()
        self.target_combo.addItem(self.translations.get("target_auto", "Auto"), None)
        self.target_combo.setFixedWidth(140)
        self.target_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.target_combo.setStyleSheet(combo_style)
        self.target_combo.setToolTip(self.translations.get(
            "target_tooltip", "Manually choose who speaks next instead of letting the GM decide."
        ))
        tl.addWidget(self.target_combo)

        self.whisper_checkbox = QtWidgets.QCheckBox(self.translations.get("whisper_label", "Private"))
        self.whisper_checkbox.setFont(_font(size=11))
        self.whisper_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.whisper_checkbox.setStyleSheet("""
            QCheckBox { color: rgba(255,255,255,0.55); spacing: 6px; }
            QCheckBox::indicator { width: 14px; height: 14px; border-radius: 4px;
                border: 1px solid rgba(255,255,255,0.25); background: rgba(255,255,255,0.04); }
            QCheckBox::indicator:checked { background: rgba(150,130,255,0.6); border-color: rgba(150,130,255,0.8); }
            QToolTip { 
                background-color: rgba(25, 25, 30, 0.95); 
                color: #E0E0E0; 
                border: 1px solid rgba(255, 255, 255, 0.15); 
                border-radius: 6px; 
                padding: 6px 10px; font-size: 12px; 
                font-weight: 500; 
            }
        """)
        self.whisper_checkbox.setToolTip(self.translations.get(
            "whisper_tooltip",
            "When checked, your message becomes private knowledge only the selected "
            "character has — the rest of the party won't know."
        ))
        tl.addWidget(self.whisper_checkbox)

        tl.addStretch()

        def _icon_btn(icon_path: str, tooltip: str, color_rgb: str = "255,255,255", alpha_normal: float = 0.08) -> QPushButton:
            btn = QPushButton()
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QtCore.QSize(18, 18))
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.10),
                        stop:1 rgba(255, 255, 255, 0.04));
                    border: 1px solid rgba(255, 255, 255, 0.12);
                    border-top: 1px solid rgba(255, 255, 255, 0.22);
                    border-radius: 18px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba({color_rgb}, 0.18),
                        stop:1 rgba({color_rgb}, 0.08));
                    border: 1px solid rgba({color_rgb}, 0.25);
                    border-top: 1px solid rgba({color_rgb}, 0.40);
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.04),
                        stop:1 rgba(255, 255, 255, 0.10));
                    border: 1px solid rgba(255, 255, 255, 0.08);
                }}
                QToolTip {{
                    background-color: rgba(25, 25, 30, 0.95); 
                    color: #E0E0E0; 
                    border: 1px solid rgba(255, 255, 255, 0.15); 
                    border-radius: 6px; 
                    padding: 6px 10px; font-size: 12px; 
                    font-weight: 500; 
                }}
            """)
            return btn

        self.btn_memory = _icon_btn("app/gui/icons/soulMemory.png", "Soul Memory", "120,160,255")
        self.btn_memory.clicked.connect(self.open_memory.emit)
        tl.addWidget(self.btn_memory)

        self.btn_world_info = _icon_btn("app/gui/icons/map.png", "World State", "60,200,140")
        self.btn_world_info.clicked.connect(self.world_info_clicked.emit)
        tl.addWidget(self.btn_world_info)

        self.btn_continue_plot = _icon_btn("app/gui/icons/play.png", "Continue Plot", "180,80,220")
        self.btn_continue_plot.clicked.connect(self.continue_plot.emit)
        tl.addWidget(self.btn_continue_plot)

        self.btn_export = _icon_btn("app/gui/icons/export.png", "Export to Markdown", "255,210,90")
        self.btn_export.clicked.connect(self.export_clicked.emit)
        tl.addWidget(self.btn_export)   

        self.btn_interrupt = _icon_btn("app/gui/icons/stop.png", "Intervene (stop AI turn)", "255,180,50")
        self.btn_interrupt.clicked.connect(self.interrupted)
        tl.addWidget(self.btn_interrupt)

        root.addWidget(self.top_bar)

        self.chat_page = QWidget()
        self.chat_page.setObjectName("chat_content_area")
        cl = QVBoxLayout(self.chat_page)
        cl.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea(parent=self.chat_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
        )

        self.chat_container = QVBoxLayout()
        self.chat_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_container.setContentsMargins(0, 20, 0, 30)
        self.chat_container.setSpacing(0)

        self.chat_messages_widget = QWidget()
        self.chat_messages_widget.setStyleSheet("background: transparent;")
        self.chat_messages_widget.setLayout(self.chat_container)
        self.chat_messages_widget.setMaximumWidth(850)

        self.chat_wrapper_layout = QHBoxLayout()
        self.chat_wrapper_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_wrapper_layout.setSpacing(0)
        self.chat_wrapper_layout.addStretch()
        self.chat_wrapper_layout.addWidget(self.chat_messages_widget)
        self.chat_wrapper_layout.addStretch()

        self._chat_w = QWidget()
        self._chat_w.setStyleSheet("background: transparent;")
        self._chat_w.setLayout(self.chat_wrapper_layout)

        self.scroll_area.setWidget(self._chat_w)
        cl.addWidget(self.scroll_area)
        root.addWidget(self.chat_page, 1)

        self.frame_send_message_full = QFrame()
        self.frame_send_message_full.setObjectName("ss_input_full")
        self.frame_send_message_full.setMinimumSize(QtCore.QSize(0, 45))
        self.frame_send_message_full.setMaximumSize(QtCore.QSize(16777215, 45))

        self.frame_send_message_full.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frame_send_message_full.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.frame_send_message_full.setStyleSheet("background-color: transparent; border: none;")

        input_full_layout = QHBoxLayout(self.frame_send_message_full)
        input_full_layout.setContentsMargins(0, 0, 0, 5)
        input_full_layout.setSpacing(0)

        self.frame_send_message = QFrame()
        self.frame_send_message.setEnabled(True)
        ssp = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred,
            QtWidgets.QSizePolicy.Policy.Preferred
        )
        self.frame_send_message.setSizePolicy(ssp)
        self.frame_send_message.setMinimumSize(QtCore.QSize(0, 40))
        self.frame_send_message.setMaximumSize(QtCore.QSize(681, 40))
        self.frame_send_message.setObjectName("ss_frame_send_message")
        self.frame_send_message.setStyleSheet("""
            QFrame#ss_frame_send_message {
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
        self.frame_send_message.setFrameShape(QFrame.Shape.StyledPanel)
        self.frame_send_message.setFrameShadow(QFrame.Shadow.Raised)

        il = QHBoxLayout(self.frame_send_message)
        il.setContentsMargins(5, 0, 5, 0)
        il.setSpacing(0)

        self.text_input = TextEditUserMessage()
        font = QtGui.QFont()
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.text_input.setFont(font)
        self.text_input.textChanged.connect(self._on_user_typing)
        self.text_input.textChanged.connect(self._adjust_input_height)
        self.text_input.setMinimumHeight(40)
        self.text_input.setMaximumHeight(610)
        self.text_input.setPlaceholderText(self.translations.get("input_placeholder", "Direct the story or speak to someone..."))
        self.text_input.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.9);
                font-family: 'Inter Tight Medium';
                font-size: 13px;
                padding-top: 6px;
                padding-left: 10px;
                padding-right: 10px;
                selection-background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.text_input.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.text_input.setAcceptRichText(False)

        self.btn_send = QPushButton()
        self.btn_send.setFixedSize(32, 32)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_send.setIcon(QIcon("app/gui/icons/send.png"))
        self.btn_send.setIconSize(QtCore.QSize(16, 16))
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.08); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 0.14); }
        """)

        self.btn_stop = QPushButton()
        self.btn_stop.setFixedSize(32, 32)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_stop.setIcon(QIcon("app/gui/icons/stop.png"))
        self.btn_stop.setIconSize(QtCore.QSize(14, 14))
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: rgba(255, 80, 80, 0.15); }
            QPushButton:pressed { background-color: rgba(255, 80, 80, 0.25); }
        """)
        self.btn_stop.hide()

        il.addWidget(self.text_input)
        il.addWidget(self.btn_send)
        il.addWidget(self.btn_stop)

        spacer_left = QtWidgets.QSpacerItem(
            200, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum
        )
        input_full_layout.addItem(spacer_left)
        input_full_layout.addWidget(self.frame_send_message)
        spacer_right = QtWidgets.QSpacerItem(
            200, 20, QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Minimum
        )
        input_full_layout.addItem(spacer_right)

        self.choices_bar = ChoicesBar()
        self.choices_bar.choice_selected.connect(self._on_choice_selected)
        root.addWidget(self.choices_bar)

        self.setStyleSheet("""
            QMenu {
                background-color: #1E1E1E;
                color: #D4D4D4;
                border: 1px solid #383838;
                border-radius: 8px;
            }
            QMenu::item { padding: 6px 20px; background-color: transparent; }
            QMenu::item:selected {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border-radius: 4px;
            }
        """)

        root.addWidget(self.frame_send_message_full)

        self.inventory_hud = InventoryHUD(
            text_input=self.text_input,
            parent=self.chat_page,
        )
        self.inventory_hud.hide()

    def set_actor_options(self, party_names: list, npc_names: Optional[list] = None):
        current = self.target_combo.currentData()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem(self.translations.get("target_auto", "Auto"), None)
        for name in list(party_names or []) + list(npc_names or []):
            self.target_combo.addItem(name, name)
        idx = self.target_combo.findData(current)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_combo.blockSignals(False)

    def compose_message(self, raw_text: str) -> dict:
        mode = self.mode_combo.currentData() or "say"
        text = (raw_text or "").strip()

        if mode == "do":
            formatted = text if text.startswith("*") else f"*{text}*"
        elif mode == "think":
            formatted = f"*(silently thinking to myself) {text}*" if text else text
        elif mode == "director":
            formatted = f"[SYSTEM DIRECTIVE — DIRECTOR NOTE]: {text}" if text else text
        else:
            formatted = text

        target = self.target_combo.currentData()
        manual_next_actor = target if (mode != "director" and target) else None
        private_recipient = target if (self.whisper_checkbox.isChecked() and target) else None

        return {
            "text": formatted,
            "manual_next_actor": manual_next_actor,
            "private_recipient": private_recipient,
            "mode": mode,
        }

    def load_scene(self, scene_data: dict, scene_id: str):
        self.scene_data = scene_data
        self._scene_id  = scene_id
        title = scene_data.get("title", self.translations.get("soul_stage_title", "Soul Stage"))
        self.scene_title_lbl.setText(title)

        while self._party_row.count():
            item = self._party_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for name in scene_data.get("party", [])[:5]:
            av_lbl = QLabel()
            av_px  = _get_char_avatar_pixmap(name)
            av_lbl.setPixmap(_round_pixmap(av_px, 32))
            av_lbl.setFixedSize(32, 32)
            av_lbl.setStyleSheet("background: transparent; border: none;")
            av_lbl.setToolTip(name)
            self._party_row.addWidget(av_lbl)

        bg_val = scene_data.get("starting_bg", "None")
        if bg_val and bg_val != "None":
            bg_path = f"assets/backgrounds/{bg_val}".replace("\\", "/")
            if os.path.exists(bg_path):
                self.chat_page.setStyleSheet(f"QWidget#chat_content_area {{ border-image: url({bg_path}) 0 0 0 0 stretch stretch; }}")
            else:
                self.chat_page.setStyleSheet("QWidget#chat_content_area { background: transparent; }")
        else:
            self.chat_page.setStyleSheet("QWidget#chat_content_area { background: transparent; }")

    def scroll_to_bottom(self):
        QtCore.QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()))

    def clear_chat(self):
        while self.chat_container.count():
            item = self.chat_container.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget(): child.widget().deleteLater()
        
        self.clear_choices()
        self.inventory_hud.hide()
    
    def show_choices(self, choices: list, event_type: str = "none"):
        self.choices_bar.show_choices(choices, event_type)

    def clear_choices(self):
        self.choices_bar.clear_choices()
    
    def _on_user_typing(self):
        if self.choices_bar.isVisible():
            if self.text_input.toPlainText().strip():
                self.choices_bar.clear_choices()

    def _on_choice_selected(self, text: str):
        self.text_input.setPlainText(text)
        cursor = self.text_input.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_input.setTextCursor(cursor)
        self.choice_made.emit(text)
    
    def _adjust_input_height(self):
        doc_height = self.text_input.document().size().height()
        padding_vertical = 16
        target_height = int(doc_height + padding_vertical)

        target_height = max(40, min(target_height, 400))

        current_height = self.frame_send_message.height()

        if current_height == target_height:
            return

        if hasattr(self, '_input_anim_group') and self._input_anim_group.state() == QtCore.QAbstractAnimation.State.Running:
            self._input_anim_group.stop()

        self._input_anim_group = QtCore.QParallelAnimationGroup(self)
        duration = 100

        anim1 = QPropertyAnimation(self.frame_send_message, b"minimumHeight")
        anim1.setDuration(duration)
        anim1.setStartValue(current_height)
        anim1.setEndValue(target_height)
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim2 = QPropertyAnimation(self.frame_send_message, b"maximumHeight")
        anim2.setDuration(duration)
        anim2.setStartValue(current_height)
        anim2.setEndValue(target_height)
        anim2.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim3 = QPropertyAnimation(self.frame_send_message_full, b"minimumHeight")
        anim3.setDuration(duration)
        anim3.setStartValue(current_height)
        anim3.setEndValue(target_height)
        anim3.setEasingCurve(QEasingCurve.Type.OutQuad)

        anim4 = QPropertyAnimation(self.frame_send_message_full, b"maximumHeight")
        anim4.setDuration(duration)
        anim4.setStartValue(current_height)
        anim4.setEndValue(target_height)
        anim4.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._input_anim_group.addAnimation(anim1)
        self._input_anim_group.addAnimation(anim2)
        self._input_anim_group.addAnimation(anim3)
        self._input_anim_group.addAnimation(anim4)

        anim1.valueChanged.connect(lambda val: self.scroll_to_bottom())

        self._input_anim_group.start()

    def update_inventory_hud(self, items: list):
        self.inventory_hud.update_items(items)
        if items:
            self.inventory_hud.reposition(self.chat_page.size())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "inventory_hud") and self.inventory_hud.isVisible():
            self.inventory_hud.reposition(self.chat_page.size())

class SoulStagePage(QWidget):
    launch_scene = pyqtSignal(str, dict, bool)
    open_memory_requested = pyqtSignal(list)

    IDX_LOBBY  = 0
    IDX_EDITOR = 1
    IDX_CHAT   = 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("soul_stage_page")
        self.setStyleSheet("background: transparent;")

        self.translations = _load_translations()

        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        self.inner_stack = QStackedWidget(); self.inner_stack.setStyleSheet("background: transparent;")

        all_chars = self._get_character_names()
        self.lobby_view  = SoulStageLobbyView()
        self.editor_view = SceneEditorView(all_characters=all_chars)
        self.chat_view   = SoulStageChatView()
        self.inner_stack.addWidget(self.lobby_view)
        self.inner_stack.addWidget(self.editor_view)
        self.inner_stack.addWidget(self.chat_view)
        layout.addWidget(self.inner_stack)

        self.lobby_view.create_new.connect(self._on_create_new)
        self.lobby_view.open_scene.connect(self._on_open_scene)
        self.lobby_view.edit_scene.connect(self._on_edit_scene)
        self.lobby_view.delete_scene.connect(self._on_delete_scene)
        self.lobby_view.import_scene.connect(self._on_import_scene)
        self.editor_view.saved.connect(self._on_scene_saved)
        self.editor_view.canceled.connect(self._go_lobby)
        self.chat_view.exit_clicked.connect(self._go_lobby)
        self.chat_view.open_memory.connect(self._on_memory_clicked)

    def _go_lobby(self):
        self.lobby_view.refresh()
        self.inner_stack.setCurrentIndex(self.IDX_LOBBY)

    def _go_editor(self): self.inner_stack.setCurrentIndex(self.IDX_EDITOR)
    def _go_chat(self):   self.inner_stack.setCurrentIndex(self.IDX_CHAT)

    def _on_create_new(self):
        self.editor_view.clear_form()
        self.editor_view.rebuild_char_list(self._get_character_names())
        self._go_editor()

    def _on_edit_scene(self, scene_id: str):
        data = _load_scenes(); sdata = data["scenes"].get(scene_id)
        if sdata:
            self.editor_view.rebuild_char_list(self._get_character_names())
            self.editor_view.load_scene(scene_id, sdata)
            self._go_editor()

    def _on_scene_saved(self, scene_id: str):
        data = _load_scenes(); sdata = data["scenes"].get(scene_id, {})
        self._launch_scene(scene_id, sdata, restore=False)

    def _on_open_scene(self, scene_id: str):
        data  = _load_scenes()
        sdata = data["scenes"].get(scene_id, {})
        if not sdata:
            return
        chat_log = sdata.get("chat_log", [])
        if chat_log:
            action = RPGOpenSceneDialog.ask(
                scene_title=sdata.get("title", "Scene"),
                entry_count=len(chat_log),
                parent=self,
            )
            if action == "continue":
                self._launch_scene(scene_id, sdata, restore=True, is_new_session=False)
            elif action == "new":
                d = _load_scenes()
                d["scenes"][scene_id]["chat_log"] = []
                d["scenes"][scene_id].pop("world_state", None)
                d["scenes"][scene_id].pop("active_npcs", None)
                _save_scenes(d)
                
                sdata["chat_log"] = []
                sdata.pop("world_state", None)
                sdata.pop("active_npcs", None)
                
                self._launch_scene(scene_id, sdata, restore=False, is_new_session=True)
        else:
            self._launch_scene(scene_id, sdata, restore=False, is_new_session=True)

    def _launch_scene(self, scene_id: str, scene_data: dict, restore: bool = False, is_new_session: bool = False):
        d = _load_scenes()
        if scene_id in d["scenes"]:
            d["scenes"][scene_id]["last_played"] = datetime.datetime.now().isoformat()
            _save_scenes(d)
        self.chat_view.load_scene(scene_data, scene_id)
        self._go_chat()
        self.launch_scene.emit(scene_id, scene_data, is_new_session)

    def _on_delete_scene(self, scene_id: str):
        data   = _load_scenes()
        sdata  = data["scenes"].get(scene_id, {})
        title  = sdata.get("title", "this scene")
        log_n  = len(sdata.get("chat_log",[]))
        
        if log_n:
            detail_template = self.translations.get("delete_scene_detail", '"{title}" · {count} saved messages will be lost')
            detail = detail_template.replace("{title}", title).replace("{count}", str(log_n))
        else:
            detail = f'"{title}"'

        message = self.translations.get("delete_scene_confirm", "Permanently delete this scene?")
        full_text = f"{message}<br><span style='color: rgba(255,255,255,0.4); font-size: 9pt;'>{detail}</span>"

        parent_win = self.window() if hasattr(self, "window") else self

        dialog = SowConfirmDialog(
            parent=parent_win,
            title=self.translations.get("delete_scene_title", "Delete Scene"),
            text=full_text,
            confirm_text=self.translations.get("delete", "Delete"),
            danger=True
        )

        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            data["scenes"].pop(scene_id, None)
            _save_scenes(data)
            self.lobby_view.refresh()

    def _on_import_scene(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translations.get("import_title", "Import Scene"),
            "",
            "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    import_data = json.load(f)

                if not import_data.get("title"):
                    QMessageBox.warning(self, self.translations.get("import_error", "Import Error"), self.translations.get("import_error", "Failed to import scene. Invalid file format."))
                    return

                self.editor_view.clear_form()
                self.editor_view.rebuild_char_list(self._get_character_names())
                self.editor_view.load_from_import(import_data)
                self._go_editor()

            except Exception as e:
                QMessageBox.warning(self, self.translations.get("import_error", "Import Error"), f"{self.translations.get('import_error', 'Failed to import scene. Invalid file format.')}\n{str(e)}")

    def _on_memory_clicked(self):
        party = self.chat_view.scene_data.get("party", [])
        if party:
            self.open_memory_requested.emit(party)

    def on_page_shown(self):
        self.lobby_view.refresh()
        self.editor_view.rebuild_char_list(self._get_character_names())

        try:
            from app.configuration import configuration
            personas = configuration.ConfigurationSettings().get_user_data("personas") or {}
            self.editor_view.load_personas(personas)
        except Exception as e:
            print(f"Error loading personas in Soul Stage: {e}")

        self._go_lobby()

    def update_character_list(self):
        self.editor_view.rebuild_char_list(self._get_character_names())

    @staticmethod
    def _get_character_names() -> list:
        try:
            from app.configuration import configuration
            return list(configuration.ConfigurationCharacters().load_configuration().get("character_list", {}).keys())
        except Exception:
            return []

class AutoResizingTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._min_h = 80
        self._max_h = 320
        self.setMinimumHeight(self._min_h)
        self.setMaximumHeight(self._max_h)

        self.setFont(_font("Inter Tight Medium", 13)) 
        
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self.adjust_height)
        QtCore.QTimer.singleShot(0, self.adjust_height)

    def adjust_height(self):
        self.blockSignals(True)
        try:
            doc_height = self.document().size().height()
            margins = self.contentsMargins()
            frame = self.frameWidth() * 2
            new_height = int(doc_height + margins.top() + margins.bottom() + frame + 12)
            
            new_height = max(self._min_h, min(new_height, self._max_h))

            if new_height != self.height():
                self.setFixedHeight(new_height)
                self.updateGeometry()
        finally:
            self.blockSignals(False)
