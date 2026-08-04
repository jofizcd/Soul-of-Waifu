from __future__ import annotations

import json
import re
import logging
from typing import Optional, Callable

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QLineEdit, QTextEdit, QStackedWidget, QListWidget, QListWidgetItem,
    QScrollArea, QWidget, QCheckBox, QButtonGroup, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QColor, QIcon

try:
    from PyQt6.sip import isdeleted
except ImportError:
    def isdeleted(obj):
        try:
            obj.parent()
            return False
        except RuntimeError:
            return True

try:
    from qasync import asyncSlot
except ImportError:
    def asyncSlot(*_a, **_kw):
        def _decorator(fn):
            return fn
        return _decorator

logger = logging.getLogger("Character AI Assistant")

SURF0 = "#070709"
SURF1 = "#0B0B0F"
SURF2 = "#111118"
SURF3 = "#171723"
SURF4 = "#1E1E2C"

TEXT      = "#E6E8EE"
TEXT_S     = "#9B9BA4"
TEXT_FAINT = "#5E5E68"

BORDER   = "rgba(255, 255, 255, 0.06)"
BORDER_M = "rgba(255, 255, 255, 0.11)"
BORDER_H = "rgba(255, 255, 255, 0.18)"

ACC       = "#A855F7"
ACC_BRT   = "#C084FC"
ACC_MUT   = "rgba(168, 85, 247, 0.14)"
ACC_GLO   = "rgba(168, 85, 247, 0.32)"
ACC_SOFT  = "rgba(168, 85, 247, 0.08)"

BLUE      = "#4BB8FF"
BLUE_BRT  = "#82CDFF"
GREEN     = "#4ADE80"
GREEN_BRT = "#6EE7A0"
RED       = "#F87171"
AMBER     = "#FBBF24"

def _mk_font(family: str, size: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    f = QFont(family, size, weight)
    f.setHintingPreference(QtGui.QFont.HintingPreference.PreferNoHinting)
    return f


FONT_TITLE  = _mk_font("Inter Tight", 16, QFont.Weight.DemiBold)
FONT_SUB    = _mk_font("Inter Tight", 10, QFont.Weight.Medium)
FONT_LABEL  = _mk_font("Inter Tight", 11, QFont.Weight.Medium)
FONT_INPUT  = _mk_font("Inter Tight", 10, QFont.Weight.Medium)
FONT_BTN    = _mk_font("Inter Tight", 10, QFont.Weight.DemiBold)
FONT_MONO   = _mk_font("Consolas", 9, QFont.Weight.Normal)
FONT_STEP   = _mk_font("Inter Tight", 10, QFont.Weight.DemiBold)
FONT_STEP_NUM = _mk_font("Inter Tight", 11, QFont.Weight.Bold)

CHAT_PROVIDERS = [
    ("Local LLM", "Local LLM", "app/gui/icons/local_llm.png", None),
    ("OpenAI / Custom", "Open AI", "app/gui/icons/openai.png", "OPEN_AI_API_TOKEN"),
    ("Anthropic Claude", "Anthropic", "app/gui/icons/anthropic.png", "ANTHROPIC_API_TOKEN"),
    ("Google Gemini", "Google Gemini", "app/gui/icons/gemini.png", "GEMINI_API_TOKEN"),
    ("DeepSeek", "DeepSeek", "app/gui/icons/deepseek.png", "DEEPSEEK_API_TOKEN"),
    ("xAI Grok", "Grok", "app/gui/icons/grok.png", "GROK_API_TOKEN"),
    ("Qwen", "Qwen", "app/gui/icons/qwen.png", "QWEN_API_TOKEN"),
    ("Z.AI", "Z.AI", "app/gui/icons/zai.png", "ZAI_API_TOKEN"),
    ("Player2", "Player2", "app/gui/icons/player2.png", None),
    ("Mistral AI", "Mistral AI", "app/gui/icons/mistralai.png", "MISTRAL_AI_API_TOKEN"),
    ("OpenRouter", "OpenRouter", "app/gui/icons/openrouter.png", "OPENROUTER_API_TOKEN"),
]

FIELD_DEFS = {
    "name": {
        "label_key": "ai_asst_field_name_label",
        "hint_key":  "ai_asst_field_name_hint",
        "default_on": True,
        "multiline": False,
    },
    "description": {
        "label_key": "ai_asst_field_description_label",
        "hint_key":  "ai_asst_field_description_hint",
        "default_on": True,
        "multiline": True,
    },
    "personality": {
        "label_key": "ai_asst_field_personality_label",
        "hint_key":  "ai_asst_field_personality_hint",
        "default_on": True,
        "multiline": True,
    },
    "scenario": {
        "label_key": "ai_asst_field_scenario_label",
        "hint_key":  "ai_asst_field_scenario_hint",
        "default_on": True,
        "multiline": True,
    },
    "first_message": {
        "label_key": "ai_asst_field_first_message_label",
        "hint_key":  "ai_asst_field_first_message_hint",
        "default_on": True,
        "multiline": True,
    },
    "alternate_greetings": {
        "label_key": "ai_asst_field_alt_greetings_label",
        "hint_key":  "ai_asst_field_alt_greetings_hint",
        "default_on": False,
        "multiline": True,
        "is_list": True,
    },
    "example_messages": {
        "label_key": "ai_asst_field_example_messages_label",
        "hint_key":  "ai_asst_field_example_messages_hint",
        "default_on": False,
        "multiline": True,
    },
    "creator_notes": {
        "label_key": "ai_asst_field_creator_notes_label",
        "hint_key":  "ai_asst_field_creator_notes_hint",
        "default_on": False,
        "multiline": True,
    },
}

FIELD_ORDER = ["name", "description", "personality", "scenario",
               "first_message", "alternate_greetings", "example_messages", "creator_notes"]


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, spacing=8):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QtCore.QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QtCore.QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QtCore.QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x, y = rect.x(), rect.y()
        line_height = 0
        for item in self._items:
            wid = item.widget()
            space_x, space_y = self._spacing, self._spacing
            next_x = x + wid.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + wid.sizeHint().width() + space_x
                line_height = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), wid.sizeHint()))
            x = next_x
            line_height = max(line_height, wid.sizeHint().height())
        return y + line_height - rect.y()


class ChipButton(QPushButton):
    def __init__(self, text, removable=False, on_remove=None, parent=None):
        super().__init__(text, parent)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCheckable(not removable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(FONT_BTN)
        self._removable = removable
        self._on_remove = on_remove
        self._apply_style()
        if removable:
            self.clicked.connect(self._remove_self)

    def _remove_self(self, _checked=False):
        if self._on_remove:
            self._on_remove(self)
        self.setParent(None)
        self.deleteLater()

    def _apply_style(self):
        base = (
            f"QPushButton {{"
            f"  background-color: {SURF3}; color: {TEXT_S};"
            f"  border: 1px solid {BORDER_M}; border-radius: 14px;"
            f"  padding: 6px 14px;"
            f"}}"
            f"QPushButton:hover {{ background-color: {SURF4}; color: {TEXT}; border-color: {BORDER_H}; }}"
        )
        if not self._removable:
            base += (
                f"QPushButton:checked {{"
                f"  background-color: {ACC_MUT}; color: {ACC_BRT}; border: 1px solid {ACC_GLO};"
                f"}}"
                f"QPushButton:checked:hover {{ background-color: {ACC_GLO}; }}"
            )
        else:
            base = (
                f"QPushButton {{"
                f"  background-color: {ACC_MUT}; color: {ACC_BRT};"
                f"  border: 1px solid {ACC_GLO}; border-radius: 14px; padding: 6px 12px 6px 14px;"
                f"}}"
                f"QPushButton:hover {{ background-color: rgba(248, 113, 113, 0.18); color: {RED}; border-color: {RED}; }}"
            )
        self.setStyleSheet(base)


class ChipSelector(QWidget):
    """Multi-select of tags + ability to add a custom variant by hand."""
    def __init__(self, options: list[str], allow_custom=True,
                 custom_placeholder: str = "", custom_tooltip: str = "",
                 parent=None):
        super().__init__(parent)
        self._buttons: dict[str, ChipButton] = {}
        self._custom_chips: list[ChipButton] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        flow_host = QWidget()
        self._flow = FlowLayout(flow_host, spacing=8)
        for opt in options:
            btn = ChipButton(opt)
            self._flow.addWidget(btn)
            self._buttons[opt] = btn
        outer.addWidget(flow_host)

        self._custom_host = QWidget()
        self._custom_flow = FlowLayout(self._custom_host, spacing=8)
        outer.addWidget(self._custom_host)

        if allow_custom:
            add_row = QHBoxLayout()
            add_row.setSpacing(8)
            self.custom_input = QLineEdit()
            self.custom_input.setPlaceholderText(custom_placeholder or "Custom… (Enter to add)")
            if custom_tooltip:
                self.custom_input.setToolTip(custom_tooltip)
            self.custom_input.setFixedHeight(36)
            self.custom_input.setFont(FONT_INPUT)
            self.custom_input.setStyleSheet(
                f"QLineEdit {{ background-color: {SURF2}; color: {TEXT}; border: 1px solid {BORDER};"
                f" border-radius: 8px; padding: 6px 10px; }}"
                f"QLineEdit:focus {{ border-color: {ACC_GLO}; background-color: {SURF3}; }}"
                f"QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: 'Inter Tight SemiBold';}}"
            )
            self.custom_input.returnPressed.connect(self._add_custom)

            self.add_btn = QPushButton("+")
            self.add_btn.setFixedSize(36, 36)
            self.add_btn.setAutoDefault(False)
            self.add_btn.setDefault(False)
            self.add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.add_btn.setFont(FONT_BTN)
            self.add_btn.setToolTip(custom_tooltip or "Add custom tag")
            self.add_btn.setStyleSheet(
                f"QPushButton {{ background-color: {ACC_MUT}; color: {ACC_BRT};"
                f" border: 1px solid {ACC_GLO}; border-radius: 8px; font-size: 16px; }}"
                f"QPushButton:hover {{ background-color: {ACC_GLO}; color: {TEXT}; }}"
                f"QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: 'Inter Tight SemiBold';}}"
            )
            self.add_btn.clicked.connect(self._add_custom)

            add_row.addWidget(self.custom_input, 1)
            add_row.addWidget(self.add_btn, 0)
            outer.addLayout(add_row)

    def _remove_custom_chip(self, chip):
        if chip in self._custom_chips:
            self._custom_chips.remove(chip)

    def _add_custom(self):
        text = self.custom_input.text().strip()
        if not text:
            return

        self._custom_chips = [c for c in self._custom_chips if not isdeleted(c)]

        existing = {opt.lower() for opt in self._buttons}
        existing |= {c.text().lower() for c in self._custom_chips}

        if text.lower() in existing:
            self.custom_input.clear()
            return

        chip = ChipButton(text, removable=True, on_remove=self._remove_custom_chip)
        self._custom_flow.addWidget(chip)
        self._custom_chips.append(chip)
        self.custom_input.clear()
        self.custom_input.setFocus()

    def selected(self) -> list[str]:
        self._custom_chips = [c for c in self._custom_chips if not isdeleted(c)]
        result = [name for name, btn in self._buttons.items() if btn.isChecked()]
        result += [c.text() for c in self._custom_chips]
        return result

    def set_selected(self, values: list[str]):
        for name, btn in self._buttons.items():
            btn.setChecked(name in values)


class AutoTextEdit(QTextEdit):
    def __init__(self, placeholder="", min_h=70, max_h=220, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self._min_h = min_h
        self._max_h = max_h
        self.setFixedHeight(min_h)
        self.textChanged.connect(self._resize)
        self.setFont(FONT_INPUT)

    def _resize(self):
        doc_h = int(self.document().size().height()) + 16
        self.setFixedHeight(max(self._min_h, min(self._max_h, doc_h)))


INPUT_STYLE = (
    f"QLineEdit, QTextEdit {{"
    f"  background-color: {SURF2}; color: {TEXT}; border: 1px solid {BORDER};"
    f"  border-radius: 8px; padding: 10px; selection-background-color: {ACC_MUT};"
    f"}}"
    f"QLineEdit:focus, QTextEdit:focus {{ border-color: {ACC_GLO}; background-color: {SURF3}; }}"
)


def make_card(title_text: Optional[str] = None, subtitle: Optional[str] = None,
              tooltip: Optional[str] = None):
    card = QFrame()
    card.setObjectName("AICard")
    if tooltip:
        card.setToolTip(tooltip)
    card.setStyleSheet(
        f"QFrame#AICard {{"
        f"  background-color: {SURF1};"
        f"  border: 1px solid {BORDER};"
        f"  border-left: 2px solid {ACC};"
        f"  border-radius: 10px;"
        f"}}"
        f"QFrame#AICard QLabel {{ background: transparent; border: none; }}"
        f"QFrame#AICard QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: 'Inter Tight SemiBold';}}"
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(22, 18, 22, 18)
    layout.setSpacing(10)
    if title_text:
        t = QLabel(title_text)
        t.setFont(FONT_LABEL)
        t.setStyleSheet(f"color: {TEXT}; font-family: 'Inter Tight'; font-size: 14px; font-weight: 600;")
        layout.addWidget(t)
    if subtitle:
        s = QLabel(subtitle)
        s.setWordWrap(True)
        s.setFont(FONT_SUB)
        s.setStyleSheet(f"color: {TEXT_S}; font-size: 11px;")
        layout.addWidget(s)
    return card, layout


def field_label(text, required=False, tooltip: Optional[str] = None):
    lbl = QLabel((text + " *") if required else text)
    lbl.setFont(FONT_LABEL)
    if tooltip:
        lbl.setToolTip(tooltip)
    color = TEXT if required else TEXT_S
    lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
    return lbl


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json|md|markdown)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


def parse_ai_json(raw_text: str, expected_keys: list[str]) -> Optional[dict]:
    """Tries to parse JSON out of a model response. Returns None on failure."""
    cleaned = _strip_code_fences(raw_text)
    candidates = [cleaned]

    brace_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if brace_match:
        candidates.append(brace_match.group(0))

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return {k: v for k, v in data.items() if k in expected_keys}
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def parse_ai_markdown(raw_text: str, expected_keys: list[str]) -> dict:
    """Fallback parser: looks for headers like '### name' / '## Name' / 'Name:'."""
    result: dict = {}
    text = _strip_code_fences(raw_text)

    aliases = {
        "name": ["name", "имя", "имя персонажа"],
        "description": ["description", "описание"],
        "personality": ["personality", "личность", "характер"],
        "scenario": ["scenario", "сценарий"],
        "first_message": ["first_message", "первое сообщение", "приветствие"],
        "alternate_greetings": ["alternate_greetings", "альтернативные приветствия"],
        "example_messages": ["example_messages", "примеры диалогов", "пример диалога"],
        "creator_notes": ["creator_notes", "заметки автора"],
    }

    pattern = re.compile(
        r"^\s{0,3}(?:#{1,4}\s*|\*\*)\s*([A-Za-zА-Яа-яЁё_ ]{2,40})\s*(?:\*\*)?\s*:?\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    for i, m in enumerate(matches):
        header = m.group(1).strip().lower()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip(" \n:-")
        for key in expected_keys:
            if key not in result and header in [a.lower() for a in aliases.get(key, [key])]:
                result[key] = body
                break

    return result


def normalize_field_value(key: str, value) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        items = [str(v).strip() for v in value if str(v).strip()]
        if key == "alternate_greetings":
            return "\n\n<GREETING>\n\n".join(items)
        return "\n".join(items)
    return str(value).strip()


class CharacterAIAssistantDialog(QDialog):
    """
    AI character card creation wizard.

    character_generated(dict, str) - emitted on "Apply to editor".
        dict: {field_key: text_value} - only fields the user kept checked.
        str:  apply mode - "overwrite" or "empty_only".
    """

    character_generated = pyqtSignal(dict, str)

    STEP_TITLE_KEYS = [
        "ai_asst_step_1",
        "ai_asst_step_2",
        "ai_asst_step_3",
        "ai_asst_step_4",
        "ai_asst_step_5",
        "ai_asst_step_6",
    ]

    def __init__(self, translations: dict, configuration_settings, configuration_api,
                 ai_factory, default_provider: str = "Local LLM",
                 gen_kwargs_func: Optional[Callable[[str], dict]] = None,
                 parent=None):
        super().__init__(parent)
        self.translations = translations or {}
        self.configuration_settings = configuration_settings
        self.configuration_api = configuration_api
        self.ai_factory = ai_factory
        self.gen_kwargs_func = gen_kwargs_func
        self.selected_provider = default_provider

        self._answers = {}
        self._generated_raw = ""
        self._parsed_fields: dict = {}
        self._field_checkboxes: dict[str, QCheckBox] = {}
        self._review_widgets: dict[str, QTextEdit] = {}
        self._review_include: dict[str, QCheckBox] = {}
        self._apply_mode = "overwrite"

        self.setWindowTitle(self.tr_("ai_asst_window_title", "AI Assistant — Character Creator"))
        self.setModal(True)
        self.resize(1000, 720)
        self.setStyleSheet(
            f"QDialog {{ background-color: {SURF0}; }}"
        )

        self._build_ui()
        self._go_to_step(0)

    def tr_(self, key, default=""):
        return self.translations.get(key, default)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("AIHeader")
        header.setStyleSheet(
            f"QFrame#AIHeader {{"
            f"  background-color: {SURF1};"
            f"  border-bottom: 1px solid {BORDER};"
            f"}}"
        )
        header.setFixedHeight(76)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        h_layout.setSpacing(0)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel(self.tr_("ai_asst_header_title", "AI Character Assistant"))
        title.setFont(FONT_TITLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {TEXT}; background: transparent; border: none; padding: 0; margin: 0;")

        subtitle = QLabel(self.tr_("ai_asst_header_subtitle",
                                    "Answer a few questions — the neural network handles the rest"))
        subtitle.setFont(FONT_SUB)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {TEXT_S}; background: transparent; border: none; padding: 0; margin: 0;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        h_layout.addStretch()
        h_layout.addLayout(title_box)
        h_layout.addStretch()

        root.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        stepper_host = QFrame()
        stepper_host.setObjectName("StepperHost")
        stepper_host.setFixedWidth(240)
        stepper_host.setStyleSheet(
            f"QFrame#StepperHost {{ background-color: {SURF1}; border-right: 1px solid {BORDER}; }}"
        )
        stepper_layout = QVBoxLayout(stepper_host)
        stepper_layout.setContentsMargins(14, 20, 14, 20)
        stepper_layout.setSpacing(6)

        stepper_title = QLabel(self.tr_("ai_asst_stepper_title", "STEPS"))
        stepper_title.setFont(_mk_font("Inter Tight", 8, QFont.Weight.Bold))
        stepper_title.setStyleSheet(
            f"color: {TEXT_FAINT}; padding-left: 10px; letter-spacing: 1.4px;"
            f" background: transparent; border: none;"
        )
        stepper_layout.addWidget(stepper_title)
        stepper_layout.addSpacing(6)

        self.stepper_list = QListWidget()
        self.stepper_list.setObjectName("StepperList")
        self.stepper_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stepper_list.setStyleSheet(
            f"QListWidget#StepperList {{ background-color: transparent; border: none; outline: none; }}"
            f"QListWidget#StepperList::item {{ color: {TEXT_FAINT}; padding: 10px 12px; border-radius: 8px; margin-bottom: 2px; }}"
            f"QListWidget#StepperList::item:selected {{ background-color: {ACC_MUT}; color: {ACC_BRT}; }}"
            f"QListWidget#StepperList::item:hover {{ color: {TEXT_S}; }}"
        )
        self._step_items: list[QListWidgetItem] = []
        for i, key in enumerate(self.STEP_TITLE_KEYS):
            label = self.tr_(key, f"Step {i + 1}")
            item = QListWidgetItem(f"  {i + 1}.   {label}")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
            self.stepper_list.addItem(item)
            self._step_items.append(item)
        stepper_layout.addWidget(self.stepper_list)
        stepper_layout.addStretch()
        body.addWidget(stepper_host)

        right_col = QVBoxLayout()
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: transparent; width: 8px; margin: 4px; }"
            f"QScrollBar::handle:vertical {{ background: {BORDER_M}; min-height: 30px; border-radius: 4px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {BORDER_H}; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }"
        )
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.stack)
        right_col.addWidget(self.scroll)

        footer = QFrame()
        footer.setObjectName("AIFooter")
        footer.setFixedHeight(72)
        footer.setStyleSheet(
            f"QFrame#AIFooter {{"
            f"  background-color: {SURF1};"
            f"  border-top: 1px solid {BORDER};"
            f"}}"
        )
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)

        self.btn_back = self._nav_button(
            self.tr_("ai_asst_btn_back", "←  Back"), primary=False,
            tooltip=self.tr_("ai_asst_btn_back_tooltip", "Go back to the previous step")
        )
        self.btn_back.clicked.connect(self._on_back)
        f_layout.addWidget(self.btn_back)
        f_layout.addStretch()

        self.step_indicator = QLabel("")
        self.step_indicator.setFont(FONT_SUB)
        self.step_indicator.setStyleSheet(f"color: {TEXT_FAINT}; background: transparent; border: none;")
        f_layout.addWidget(self.step_indicator)
        f_layout.addStretch()

        self.btn_next = self._nav_button(
            self.tr_("ai_asst_btn_next", "Next  →"), primary=True,
            tooltip=self.tr_("ai_asst_btn_next_tooltip", "Continue to the next step")
        )
        self.btn_next.clicked.connect(self._on_next)
        f_layout.addWidget(self.btn_next)

        right_col.addWidget(footer)
        body.addLayout(right_col)
        root.addLayout(body)

        self.stack.addWidget(self._build_page_concept())
        self.stack.addWidget(self._build_page_personality())
        self.stack.addWidget(self._build_page_background())
        self.stack.addWidget(self._build_page_relationship())
        self.stack.addWidget(self._build_page_extras_and_fields())
        self.stack.addWidget(self._build_page_generate())

    def _nav_button(self, text, primary=True, tooltip=""):
        btn = QPushButton(text)
        btn.setFixedHeight(42)
        btn.setMinimumWidth(130)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFont(FONT_BTN)
        if tooltip:
            btn.setToolTip(tooltip)
        if primary:
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {ACC}; color: #0A0512; border: none; border-radius: 8px; padding: 0 18px; }}"
                f"QPushButton:hover {{ background-color: {ACC_BRT}; }}"
                f"QPushButton:pressed {{ background-color: #9333EA; }}"
                f"QPushButton:disabled {{ background-color: {SURF3}; color: {TEXT_FAINT}; }}"
                f"QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: 'Inter Tight SemiBold';}}"
            )
        else:
            btn.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {TEXT_S}; border: 1px solid {BORDER_M}; border-radius: 8px; padding: 0 18px; }}"
                f"QPushButton:hover {{ background-color: {SURF3}; color: {TEXT}; border-color: {BORDER_H}; }}"
                f"QPushButton:pressed {{ background-color: {SURF4}; }}"
                f"QPushButton:disabled {{ color: {TEXT_FAINT}; border-color: {BORDER}; }}"
                f"QToolTip {{ background-color: rgba(25, 25, 30, 0.95); color: #E0E0E0; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 6px; padding: 6px 10px; font-size: 13px; font-family: 'Inter Tight SemiBold';}}"
            )
        return btn

    def _page_container(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)
        return page, layout

    def _build_page_concept(self):
        page, layout = self._page_container()

        concept_tooltip = self.tr_("ai_asst_concept_field_tooltip",
                                    "Required. The AI uses this as the seed for every other field.")

        card, cl = make_card(
            self.tr_("ai_asst_concept_card_title", "Who is your character?"),
            self.tr_("ai_asst_concept_card_subtitle",
                     "Describe the main idea in free form — the rest can be refined below."),
            tooltip=concept_tooltip,
        )
        cl.addWidget(field_label(
            self.tr_("ai_asst_concept_field_label", "Brief character idea"),
            required=True, tooltip=concept_tooltip
        ))
        self.q_concept = AutoTextEdit(
            placeholder=self.tr_("ai_asst_concept_field_placeholder",
                "e.g.: «A former mercenary elf tired of war, now running a tavern on the kingdom's edge and hiding a dark past»…"),
            min_h=90, max_h=180
        )
        self.q_concept.setToolTip(concept_tooltip)
        self.q_concept.setStyleSheet(INPUT_STYLE)
        cl.addWidget(self.q_concept)
        layout.addWidget(card)

        card2, cl2 = make_card(
            self.tr_("ai_asst_genre_card_title", "Setting / Genre"),
            self.tr_("ai_asst_genre_card_subtitle", "Pick one or several — or add your own"),
        )
        self.chip_genre = ChipSelector(
            [
                self.tr_("ai_asst_genre_fantasy", "Fantasy"),
                self.tr_("ai_asst_genre_scifi", "Sci-Fi"),
                self.tr_("ai_asst_genre_modern", "Modern"),
                self.tr_("ai_asst_genre_historical", "Historical"),
                self.tr_("ai_asst_genre_anime", "Anime / Manga"),
                self.tr_("ai_asst_genre_postapoc", "Post-apocalypse"),
                self.tr_("ai_asst_genre_cyberpunk", "Cyberpunk"),
                self.tr_("ai_asst_genre_horror", "Horror"),
                self.tr_("ai_asst_genre_sliceoflife", "Slice of life"),
            ],
            custom_placeholder=self.tr_("ai_asst_custom_placeholder", "Custom variant… (press Enter to add)"),
            custom_tooltip=self.tr_("ai_asst_custom_tooltip",
                                     "Type a value and press Enter — it becomes a chip you can toggle."),
        )
        cl2.addWidget(self.chip_genre)
        layout.addWidget(card2)

        card3, cl3 = make_card(
            self.tr_("ai_asst_role_card_title", "Character's Role"),
            self.tr_("ai_asst_role_card_subtitle", "How does this character fit into the story?"),
        )
        self.chip_role = ChipSelector(
            [
                self.tr_("ai_asst_role_companion", "Companion"),
                self.tr_("ai_asst_role_mentor", "Mentor"),
                self.tr_("ai_asst_role_antagonist", "Antagonist"),
                self.tr_("ai_asst_role_love", "Love interest"),
                self.tr_("ai_asst_role_rival", "Rival"),
                self.tr_("ai_asst_role_assistant", "Assistant"),
                self.tr_("ai_asst_role_stranger", "Mysterious stranger"),
                self.tr_("ai_asst_role_friend", "Friend"),
            ],
            custom_placeholder=self.tr_("ai_asst_custom_placeholder", "Custom variant… (press Enter to add)"),
            custom_tooltip=self.tr_("ai_asst_custom_tooltip",
                                     "Type a value and press Enter — it becomes a chip you can toggle."),
        )
        cl3.addWidget(self.chip_role)
        layout.addWidget(card3)

        layout.addStretch()
        return page

    def _build_page_personality(self):
        page, layout = self._page_container()

        card, cl = make_card(
            self.tr_("ai_asst_traits_card_title", "Personality Traits"),
            self.tr_("ai_asst_traits_card_subtitle", "Pick several or add your own"),
        )
        self.chip_traits = ChipSelector(
            [
                self.tr_("ai_asst_trait_kind", "Kind"),
                self.tr_("ai_asst_trait_tsundere", "Tsundere"),
                self.tr_("ai_asst_trait_sarcastic", "Sarcastic"),
                self.tr_("ai_asst_trait_shy", "Shy"),
                self.tr_("ai_asst_trait_confident", "Confident"),
                self.tr_("ai_asst_trait_cold", "Cold"),
                self.tr_("ai_asst_trait_playful", "Playful"),
                self.tr_("ai_asst_trait_serious", "Serious"),
                self.tr_("ai_asst_trait_chaotic", "Chaotic"),
                self.tr_("ai_asst_trait_loyal", "Loyal"),
                self.tr_("ai_asst_trait_manipulative", "Manipulative"),
                self.tr_("ai_asst_trait_naive", "Naive"),
                self.tr_("ai_asst_trait_wise", "Wise"),
                self.tr_("ai_asst_trait_energetic", "Energetic"),
                self.tr_("ai_asst_trait_calm", "Calm"),
                self.tr_("ai_asst_trait_caring", "Caring"),
            ],
            custom_placeholder=self.tr_("ai_asst_custom_placeholder", "Custom variant… (press Enter to add)"),
            custom_tooltip=self.tr_("ai_asst_custom_tooltip",
                                     "Type a value and press Enter — it becomes a chip you can toggle."),
        )
        cl.addWidget(self.chip_traits)
        layout.addWidget(card)

        card2, cl2 = make_card(
            self.tr_("ai_asst_speech_card_title", "Speech Style"),
            self.tr_("ai_asst_speech_card_subtitle", "How does the character talk?"),
        )
        self.chip_speech = ChipSelector(
            [
                self.tr_("ai_asst_speech_formal", "Formal"),
                self.tr_("ai_asst_speech_slang", "Casual / Slang"),
                self.tr_("ai_asst_speech_poetic", "Poetic"),
                self.tr_("ai_asst_speech_direct", "Direct"),
                self.tr_("ai_asst_speech_teasing", "Teasing"),
                self.tr_("ai_asst_speech_archaic", "Archaic"),
                self.tr_("ai_asst_speech_accent", "Accent / Speech quirk"),
                self.tr_("ai_asst_speech_emoji", "With emojis"),
            ],
            custom_placeholder=self.tr_("ai_asst_custom_placeholder", "Custom variant… (press Enter to add)"),
            custom_tooltip=self.tr_("ai_asst_custom_tooltip",
                                     "Type a value and press Enter — it becomes a chip you can toggle."),
        )
        cl2.addWidget(self.chip_speech)
        layout.addWidget(card2)

        card3, cl3 = make_card(
            self.tr_("ai_asst_motive_card_title", "Inner Motive"),
            self.tr_("ai_asst_motive_card_subtitle", "What drives the character? Fear, goal, secret…"),
        )
        self.q_motive = AutoTextEdit(
            placeholder=self.tr_("ai_asst_motive_placeholder",
                "e.g.: «Afraid of losing someone again, so keeps people at a distance»…"),
            min_h=80, max_h=160
        )
        self.q_motive.setStyleSheet(INPUT_STYLE)
        cl3.addWidget(self.q_motive)
        layout.addWidget(card3)

        layout.addStretch()
        return page

    def _build_page_background(self):
        page, layout = self._page_container()

        hint = QLabel(self.tr_("ai_asst_bg_skip_hint",
            "This step is optional — skip it and the AI will invent the details."))
        hint.setFont(FONT_SUB)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {TEXT_FAINT}; padding: 4px 0;")
        layout.addWidget(hint)

        card, cl = make_card(self.tr_("ai_asst_age_card_title", "Age & Species / Race"))
        self.q_age_species = QLineEdit()
        self.q_age_species.setPlaceholderText(self.tr_("ai_asst_age_placeholder",
            "e.g.: «24 years old, human» or «unknown, ancient vampire»"))
        self.q_age_species.setFixedHeight(42)
        self.q_age_species.setFont(FONT_INPUT)
        self.q_age_species.setStyleSheet(INPUT_STYLE)
        cl.addWidget(self.q_age_species)
        layout.addWidget(card)

        card2, cl2 = make_card(
            self.tr_("ai_asst_appearance_card_title", "Appearance"),
            self.tr_("ai_asst_appearance_card_subtitle", "Key details — the AI will fill the rest"),
        )
        self.q_appearance = AutoTextEdit(
            placeholder=self.tr_("ai_asst_appearance_placeholder",
                "Hair/eye color, build, clothing style, distinctive marks…"),
            min_h=80, max_h=160
        )
        self.q_appearance.setStyleSheet(INPUT_STYLE)
        cl2.addWidget(self.q_appearance)
        layout.addWidget(card2)

        card3, cl3 = make_card(self.tr_("ai_asst_backstory_card_title", "Backstory"))
        self.q_backstory = AutoTextEdit(
            placeholder=self.tr_("ai_asst_backstory_placeholder",
                "Key past events that shaped the character…"),
            min_h=90, max_h=180
        )
        self.q_backstory.setStyleSheet(INPUT_STYLE)
        cl3.addWidget(self.q_backstory)
        layout.addWidget(card3)

        layout.addStretch()
        return page

    def _build_page_relationship(self):
        page, layout = self._page_container()

        card, cl = make_card(
            self.tr_("ai_asst_rel_card_title", "Who is the character to you ({{user}})?"),
            self.tr_("ai_asst_rel_card_subtitle", "Pick the option that best fits the dynamic"),
        )
        self.chip_relationship = ChipSelector(
            [
                self.tr_("ai_asst_rel_stranger", "Stranger"),
                self.tr_("ai_asst_rel_friend", "Friend"),
                self.tr_("ai_asst_rel_partner", "Romantic partner"),
                self.tr_("ai_asst_rel_family", "Family member"),
                self.tr_("ai_asst_rel_enemy", "Rival / Enemy"),
                self.tr_("ai_asst_rel_mentor", "Mentor / Student"),
                self.tr_("ai_asst_rel_boss", "Boss / Subordinate"),
                self.tr_("ai_asst_rel_chance", "Chance encounter"),
            ],
            custom_placeholder=self.tr_("ai_asst_custom_placeholder", "Custom variant… (press Enter to add)"),
            custom_tooltip=self.tr_("ai_asst_custom_tooltip",
                                     "Type a value and press Enter — it becomes a chip you can toggle."),
        )
        cl.addWidget(self.chip_relationship)
        layout.addWidget(card)

        card2, cl2 = make_card(
            self.tr_("ai_asst_meeting_card_title", "How does the first meeting happen?"),
            self.tr_("ai_asst_meeting_card_subtitle",
                     "This becomes the basis for the «Scenario» field and the first message"),
        )
        self.q_first_meeting = AutoTextEdit(
            placeholder=self.tr_("ai_asst_meeting_placeholder",
                "e.g.: «{{user}} enters the tavern late at night, the character is just closing up»…"),
            min_h=90, max_h=180
        )
        self.q_first_meeting.setStyleSheet(INPUT_STYLE)
        cl2.addWidget(self.q_first_meeting)
        layout.addWidget(card2)

        card3, cl3 = make_card(self.tr_("ai_asst_tone_card_title", "Story Tone"))
        self.chip_tone = ChipSelector(
            [
                self.tr_("ai_asst_tone_light", "Light / Friendly"),
                self.tr_("ai_asst_tone_romance", "Romance (no explicit scenes)"),
                self.tr_("ai_asst_tone_drama", "Drama / Dark themes"),
                self.tr_("ai_asst_tone_comedy", "Comedy"),
                self.tr_("ai_asst_tone_adventure", "Adventure / Action"),
                self.tr_("ai_asst_tone_mystery", "Mystery / Detective"),
            ],
            allow_custom=False,
        )
        cl3.addWidget(self.chip_tone)
        layout.addWidget(card3)

        layout.addStretch()
        return page

    def _build_page_extras_and_fields(self):
        page, layout = self._page_container()

        card, cl = make_card(
            self.tr_("ai_asst_extra_card_title", "What else must be considered?"),
            self.tr_("ai_asst_extra_card_subtitle",
                     "Special phrases, lore, references, constraints — anything that matters for accuracy"),
        )
        self.q_extra = AutoTextEdit(
            placeholder=self.tr_("ai_asst_extra_placeholder", "Free text…"),
            min_h=90, max_h=200
        )
        self.q_extra.setStyleSheet(INPUT_STYLE)
        cl.addWidget(self.q_extra)
        layout.addWidget(card)

        card2, cl2 = make_card(
            self.tr_("ai_asst_fields_card_title", "Which fields to fill?"),
            self.tr_("ai_asst_fields_card_subtitle",
                     "Mark only what the AI should generate. Other fields stay untouched."),
        )
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        for i, key in enumerate(FIELD_ORDER):
            meta = FIELD_DEFS[key]
            label = self.tr_(meta["label_key"], key)
            hint  = self.tr_(meta["hint_key"], "")
            cb = QCheckBox(label)
            cb.setChecked(meta["default_on"])
            cb.setFont(FONT_INPUT)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cb.setToolTip(hint)
            cb.setStyleSheet(
                f"QCheckBox {{ color: {TEXT}; spacing: 8px; background: transparent; }}"
                f"QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px;"
                f"  border: 1px solid {BORDER_M}; background: {SURF2}; }}"
                f"QCheckBox::indicator:checked {{ background-color: {ACC}; border-color: {ACC}; }}"
                f"QCheckBox:hover {{ color: {TEXT}; }}"
            )
            self._field_checkboxes[key] = cb
            grid.addWidget(cb, i // 2, i % 2)
        cl2.addLayout(grid)

        btn_row = QHBoxLayout()
        btn_all = QPushButton(self.tr_("ai_asst_btn_select_all", "Select all"))
        btn_none = QPushButton(self.tr_("ai_asst_btn_select_none", "Clear all"))
        for b in (btn_all, btn_none):
            b.setAutoDefault(False)
            b.setDefault(False)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFixedHeight(30)
            b.setFont(FONT_SUB)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {ACC_BRT}; border: none; padding: 0 4px; }}"
                f"QPushButton:hover {{ color: {TEXT}; }}"
            )
        btn_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._field_checkboxes.values()])
        btn_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._field_checkboxes.values()])
        btn_row.addWidget(btn_all)
        btn_row.addWidget(btn_none)
        btn_row.addStretch()
        cl2.addLayout(btn_row)
        layout.addWidget(card2)

        card3, cl3 = make_card(self.tr_("ai_asst_mode_card_title", "Apply Mode"))
        self.mode_group = QButtonGroup(page)
        self.mode_group.setExclusive(True)
        rb_overwrite = QtWidgets.QRadioButton(
            self.tr_("ai_asst_mode_overwrite", "Overwrite selected fields completely"))
        rb_empty = QtWidgets.QRadioButton(
            self.tr_("ai_asst_mode_empty", "Fill only empty fields (keep existing content)"))
        for rb in (rb_overwrite, rb_empty):
            rb.setFont(FONT_INPUT)
            rb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setToolTip(self.tr_("ai_asst_mode_tooltip",
                "Choose how the generated values are applied to the editor."))
            rb.setStyleSheet(
                f"QRadioButton {{ color: {TEXT}; spacing: 8px; padding: 4px 0; background: transparent; }}"
                f"QRadioButton::indicator {{ width: 16px; height: 16px; border-radius: 8px;"
                f"  border: 1px solid {BORDER_M}; background: {SURF2}; }}"
                f"QRadioButton::indicator:checked {{ background-color: {ACC}; border-color: {ACC}; }}"
            )
        rb_overwrite.setChecked(True)
        self.mode_group.addButton(rb_overwrite, 0)
        self.mode_group.addButton(rb_empty, 1)
        cl3.addWidget(rb_overwrite)
        cl3.addWidget(rb_empty)
        layout.addWidget(card3)

        layout.addStretch()
        return page

    def _build_page_generate(self):
        page, layout = self._page_container()

        card, cl = make_card(
            self.tr_("ai_asst_provider_card_title", "Language Model (provider)"),
            self.tr_("ai_asst_provider_card_subtitle",
                     "Uses the same provider that is configured in the app"),
        )
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        self.provider_btn_group = QButtonGroup(page)
        self.provider_btn_group.setExclusive(True)
        cols = 3
        for i, (name, value, icon_path, token_key) in enumerate(CHAT_PROVIDERS):
            btn = QPushButton(f"  {name}")
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QtCore.QSize(16, 16))
            btn.setCheckable(True)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedHeight(42)
            btn.setFont(FONT_BTN)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(self.tr_("ai_asst_provider_tooltip",
                "Click to select this provider for generation."))
            btn.setProperty("provider_value", value)
            btn.setProperty("token_key", token_key)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {SURF2}; color: {TEXT_S}; border: 1px solid {BORDER};"
                f" border-radius: 8px; text-align: left; padding-left: 12px; }}"
                f"QPushButton:hover {{ background-color: {SURF3}; color: {TEXT}; border-color: {BORDER_M}; }}"
                f"QPushButton:checked {{ background-color: {ACC_MUT}; border: 1px solid {ACC_GLO}; color: {ACC_BRT}; }}"
            )
            if value == self.selected_provider:
                btn.setChecked(True)
            self.provider_btn_group.addButton(btn)
            grid.addWidget(btn, i // cols, i % cols)
        if not self.provider_btn_group.checkedButton() and self.provider_btn_group.buttons():
            self.provider_btn_group.buttons()[0].setChecked(True)
        cl.addLayout(grid)

        self.provider_status_lbl = QLabel("")
        self.provider_status_lbl.setWordWrap(True)
        self.provider_status_lbl.setFont(FONT_SUB)
        self.provider_status_lbl.setStyleSheet(f"color: {TEXT_FAINT};")
        cl.addWidget(self.provider_status_lbl)
        layout.addWidget(card)

        gen_row = QHBoxLayout()
        self.btn_generate = QPushButton(self.tr_("ai_asst_btn_generate", "✨  Generate card"))
        self.btn_generate.setFixedHeight(46)
        self.btn_generate.setAutoDefault(False)
        self.btn_generate.setDefault(False)
        self.btn_generate.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_generate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate.setFont(FONT_BTN)
        self.btn_generate.setToolTip(self.tr_("ai_asst_btn_generate_tooltip",
            "Send the collected answers to the selected provider and generate the card fields."))
        self.btn_generate.setStyleSheet(
            f"QPushButton {{ background-color: {ACC}; color: #0A0512; border: none; border-radius: 10px; padding: 0 20px; }}"
            f"QPushButton:hover {{ background-color: {ACC_BRT}; }}"
            f"QPushButton:pressed {{ background-color: #9333EA; }}"
            f"QPushButton:disabled {{ background-color: {SURF3}; color: {TEXT_FAINT}; }}"
        )
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        gen_row.addWidget(self.btn_generate)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        self.stream_card, stream_cl = make_card(self.tr_("ai_asst_stream_card_title", "Model response"))
        self.stream_output = QTextEdit()
        self.stream_output.setReadOnly(True)
        self.stream_output.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.stream_output.setFixedHeight(140)
        self.stream_output.setFont(FONT_MONO)
        self.stream_output.setStyleSheet(
            f"QTextEdit {{ background-color: {SURF2}; color: {TEXT_S}; border: 1px solid {BORDER}; border-radius: 8px; padding: 10px; }}"
        )
        stream_cl.addWidget(self.stream_output)
        self.stream_card.hide()
        layout.addWidget(self.stream_card)

        self.review_card, self.review_cl = make_card(
            self.tr_("ai_asst_review_card_title", "Review & apply"),
            self.tr_("ai_asst_review_card_subtitle",
                     "You can edit the text manually before applying. Unchecking a field excludes it from applying."),
        )
        self.review_fields_host = QVBoxLayout()
        self.review_fields_host.setSpacing(14)
        self.review_cl.addLayout(self.review_fields_host)
        self.review_card.hide()
        layout.addWidget(self.review_card)

        apply_row = QHBoxLayout()
        self.btn_apply = QPushButton(self.tr_("ai_asst_btn_apply", "Apply to editor"))
        self.btn_apply.setFixedHeight(46)
        self.btn_apply.setAutoDefault(False)
        self.btn_apply.setDefault(False)
        self.btn_apply.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_apply.setFont(FONT_BTN)
        self.btn_apply.setToolTip(self.tr_("ai_asst_btn_apply_tooltip",
            "Apply the checked fields to the character editor and close this dialog."))
        self.btn_apply.setStyleSheet(
            f"QPushButton {{ background-color: {GREEN}; color: #052E16; border: none; border-radius: 10px; padding: 0 20px; }}"
            f"QPushButton:hover {{ background-color: {GREEN_BRT}; }}"
            f"QPushButton:pressed {{ background-color: #22C55E; }}"
        )
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        self.btn_apply.hide()
        apply_row.addWidget(self.btn_apply)
        apply_row.addStretch()
        layout.addLayout(apply_row)

        layout.addStretch()
        return page

    def _go_to_step(self, index: int):
        index = max(0, min(index, self.stack.count() - 1))
        self.stack.setCurrentIndex(index)
        for i, item in enumerate(self._step_items):
            label_key = self.STEP_TITLE_KEYS[i]
            label = self.tr_(label_key, f"Step {i + 1}")
            if i == index:
                item.setText(f"  ●  {i + 1}.   {label}")
            else:
                item.setText(f"     {i + 1}.   {label}")
        self.step_indicator.setText(
            self.tr_("ai_asst_step_indicator", "Step {n} of {total}")
                .replace("{n}", str(index + 1))
                .replace("{total}", str(len(self.STEP_TITLE_KEYS)))
        )
        self.btn_back.setEnabled(index > 0)
        self.btn_next.setText(self.tr_("ai_asst_btn_done", "Done") if index == self.stack.count() - 1
                              else self.tr_("ai_asst_btn_next", "Next  →"))
        self.btn_next.setVisible(index != self.stack.count() - 1)

    def _on_back(self):
        self._go_to_step(self.stack.currentIndex() - 1)

    def _on_next(self):
        current = self.stack.currentIndex()
        if current == 0 and not self.q_concept.toPlainText().strip():
            self._flash_required(self.q_concept)
            return
        self._go_to_step(current + 1)

    def _flash_required(self, widget):
        widget.setStyleSheet(INPUT_STYLE.replace(f"border: 1px solid {BORDER}", f"border: 1px solid {RED}"))
        QtCore.QTimer.singleShot(1200, lambda: widget.setStyleSheet(INPUT_STYLE))

    def _collect_answers(self) -> dict:
        return {
            "concept": self.q_concept.toPlainText().strip(),
            "genre": self.chip_genre.selected(),
            "role": self.chip_role.selected(),
            "traits": self.chip_traits.selected(),
            "speech_style": self.chip_speech.selected(),
            "motive": self.q_motive.toPlainText().strip(),
            "age_species": self.q_age_species.text().strip(),
            "appearance": self.q_appearance.toPlainText().strip(),
            "backstory": self.q_backstory.toPlainText().strip(),
            "relationship": self.chip_relationship.selected(),
            "first_meeting": self.q_first_meeting.toPlainText().strip(),
            "tone": self.chip_tone.selected(),
            "extra": self.q_extra.toPlainText().strip(),
        }

    def _selected_field_keys(self) -> list[str]:
        return [k for k, cb in self._field_checkboxes.items() if cb.isChecked()]

    def _build_prompt(self, answers: dict, field_keys: list[str]) -> list[dict]:
        system_prompt = self.tr_("ai_asst_prompt_system",
            "You are an experienced screenwriter and game designer helping the user of a roleplay "
            "AI-chat program build a fictional character card. You work ONLY with fiction. Reply "
            "STRICTLY with valid JSON — no explanations, no preamble, no ``` markdown wrappers, no "
            "comments — just the JSON object itself. Write in the SAME language as the user's answers "
            "(default: Russian). Use the placeholder {{user}} to refer to the user and {{char}} to "
            "refer to the character itself in dialogue examples."
        )

        header = self.tr_("ai_asst_prompt_user_header",
            "Here is the character information collected from the user via the questionnaire:\n")
        lines = [header]

        def _join(lst):
            return ", ".join(lst) if isinstance(lst, list) else str(lst)

        L_CONCEPT = self.tr_("ai_asst_prompt_l_concept", "Basic idea")
        L_GENRE   = self.tr_("ai_asst_prompt_l_genre", "Setting/genre")
        L_ROLE    = self.tr_("ai_asst_prompt_l_role", "Character's role")
        L_TRAITS  = self.tr_("ai_asst_prompt_l_traits", "Personality traits")
        L_SPEECH  = self.tr_("ai_asst_prompt_l_speech", "Speech manner")
        L_MOTIVE  = self.tr_("ai_asst_prompt_l_motive", "Inner motive/fear/goal")
        L_AGE     = self.tr_("ai_asst_prompt_l_age", "Age/species")
        L_LOOK    = self.tr_("ai_asst_prompt_l_appearance", "Appearance")
        L_BACK    = self.tr_("ai_asst_prompt_l_backstory", "Backstory")
        L_REL     = self.tr_("ai_asst_prompt_l_relationship", "Relationship to {{user}}")
        L_MEET    = self.tr_("ai_asst_prompt_l_meeting", "Circumstances of meeting")
        L_TONE    = self.tr_("ai_asst_prompt_l_tone", "Story tone")
        L_EXTRA   = self.tr_("ai_asst_prompt_l_extra", "Additional wishes/constraints")

        if answers["concept"]:
            lines.append(f"- {L_CONCEPT}: {answers['concept']}")
        if answers["genre"]:
            lines.append(f"- {L_GENRE}: {_join(answers['genre'])}")
        if answers["role"]:
            lines.append(f"- {L_ROLE}: {_join(answers['role'])}")
        if answers["traits"]:
            lines.append(f"- {L_TRAITS}: {_join(answers['traits'])}")
        if answers["speech_style"]:
            lines.append(f"- {L_SPEECH}: {_join(answers['speech_style'])}")
        if answers["motive"]:
            lines.append(f"- {L_MOTIVE}: {answers['motive']}")
        if answers["age_species"]:
            lines.append(f"- {L_AGE}: {answers['age_species']}")
        if answers["appearance"]:
            lines.append(f"- {L_LOOK}: {answers['appearance']}")
        if answers["backstory"]:
            lines.append(f"- {L_BACK}: {answers['backstory']}")
        if answers["relationship"]:
            lines.append(f"- {L_REL}: {_join(answers['relationship'])}")
        if answers["first_meeting"]:
            lines.append(f"- {L_MEET}: {answers['first_meeting']}")
        if answers["tone"]:
            lines.append(f"- {L_TONE}: {_join(answers['tone'])}")
        if answers["extra"]:
            lines.append(f"- {L_EXTRA}: {answers['extra']}")

        keys_header = self.tr_("ai_asst_prompt_field_keys_header",
            "\nGenerate JSON with the FOLLOWING keys (and only them):")
        lines.append(keys_header)
        for key in field_keys:
            meta = FIELD_DEFS[key]
            value_type_word = (self.tr_("ai_asst_prompt_l_array", "array of strings")
                                if meta.get("is_list")
                                else self.tr_("ai_asst_prompt_l_string", "string"))
            hint = self.tr_(meta["hint_key"], key)
            lines.append(f'  "{key}" ({value_type_word}): {hint}')

        footer = self.tr_("ai_asst_prompt_user_footer",
            "\nReturn exactly one JSON object with these keys. No text before or after the JSON. "
            "Do not leave fields empty — if data is missing, invent logically consistent details "
            "that agree with the already-specified information."
        )
        lines.append(footer)

        user_prompt = "\n".join(lines)
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _build_refine_prompt(self, field_key: str) -> list[dict]:
        """Prompt for regenerating ONE field, taking already-approved others into account."""
        base_messages = self._build_prompt(self._answers, [field_key])
        context_bits = []
        for k, widget in self._review_widgets.items():
            if k == field_key:
                continue
            text = widget.toPlainText().strip()
            if text:
                label = self.tr_(FIELD_DEFS[k]["label_key"], k)
                context_bits.append(f"{label}: {text}")
        if context_bits:
            addition_header = self.tr_("ai_asst_prompt_refine_addition",
                "\n\nAlready approved parts of the card (for consistency, do not rewrite them):\n")
            base_messages[1]["content"] += addition_header + "\n".join(context_bits)
        return base_messages

    def _get_checked_provider(self):
        btn = self.provider_btn_group.checkedButton()
        if not btn:
            return None, None
        return btn.property("provider_value"), btn.property("token_key")

    def _check_provider_ready(self, provider_value: str, token_key: Optional[str]) -> tuple[bool, str]:
        if token_key is None:
            return True, ""
        token = ""
        try:
            token = self.configuration_api.get_token(token_key) or ""
        except Exception as e:
            logger.warning(f"Cannot read token for {provider_value}: {e}")
        if not token.strip():
            return False, self.tr_("ai_asst_status_no_token",
                "⚠ No API token set for «{provider}». Configure it in Options → API, then come back."
            ).replace("{provider}", str(provider_value))
        return True, ""

    @asyncSlot()
    async def _on_generate_clicked(self):
        provider_value, token_key = self._get_checked_provider()
        if not provider_value:
            return

        ready, msg = self._check_provider_ready(provider_value, token_key)
        self.provider_status_lbl.setText(msg)
        self.provider_status_lbl.setStyleSheet(f"color: {RED if not ready else TEXT_FAINT};")
        if not ready:
            return

        field_keys = self._selected_field_keys()
        if not field_keys:
            self.provider_status_lbl.setText(
                self.tr_("ai_asst_status_no_fields",
                    "⚠ Select at least one field to generate on the previous step."))
            self.provider_status_lbl.setStyleSheet(f"color: {RED};")
            return

        self._answers = self._collect_answers()
        self.selected_provider = provider_value
        self._apply_mode = "overwrite" if self.mode_group.checkedId() == 0 else "empty_only"

        messages = self._build_prompt(self._answers, field_keys)
        await self._run_generation(messages, field_keys, target="full")

    async def _run_generation(self, messages: list[dict], field_keys: list[str], target: str):
        """target == 'full' -> refresh the whole review block; else == field name for single regen."""
        self.btn_generate.setEnabled(False)
        self.stream_card.show()
        self.stream_output.clear()

        try:
            provider = self.ai_factory.get_provider(self.selected_provider)
        except Exception as e:
            logger.error(f"AIFactory.get_provider failed: {e}")
            provider = None

        if provider is None:
            self.stream_output.setPlainText(
                self.tr_("ai_asst_err_provider",
                    "Error: failed to get provider. Check Options settings."))
            self.btn_generate.setEnabled(True)
            return

        gen_kwargs = {}
        if self.gen_kwargs_func:
            try:
                gen_kwargs = self.gen_kwargs_func(self.selected_provider)
            except Exception:
                gen_kwargs = {}
        gen_kwargs.setdefault("temperature", 0.9)
        gen_kwargs.setdefault("max_tokens", 2200)

        full_text = ""
        try:
            async for chunk in provider.generate_stream(messages, **gen_kwargs):
                if chunk:
                    full_text += chunk
                    self.stream_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
                    self.stream_output.insertPlainText(chunk)
                    self.stream_output.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        except Exception as e:
            logger.error(f"Generation failed: {e}", exc_info=True)
            err_text = self.tr_("ai_asst_err_generation", "[Generation failed: {error}]")
            self.stream_output.append("\n\n" + err_text.replace("{error}", str(e)))
            self.btn_generate.setEnabled(True)
            return

        self._generated_raw = full_text
        self.btn_generate.setEnabled(True)

        parsed = parse_ai_json(full_text, field_keys)
        if not parsed:
            parsed = parse_ai_markdown(full_text, field_keys)
        if not parsed:
            self.stream_output.append(
                self.tr_("ai_asst_err_parse",
                    "\n\n[Could not parse the model response as JSON or Markdown. "
                    "Try another provider or simplify the request.]"))
            return

        if target == "full":
            self._parsed_fields = parsed
            self._build_review_ui(field_keys)
        else:
            value = normalize_field_value(target, parsed.get(target, ""))
            if target in self._review_widgets and value:
                self._review_widgets[target].setPlainText(value)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _build_review_ui(self, field_keys: list[str]):
        self._clear_layout(self.review_fields_host)
        self._review_widgets.clear()
        self._review_include.clear()

        for key in field_keys:
            meta = FIELD_DEFS[key]
            label = self.tr_(meta["label_key"], key)
            value = normalize_field_value(key, self._parsed_fields.get(key, ""))

            block = QFrame()
            block.setStyleSheet(
                f"QFrame {{ background-color: {SURF2}; border: 1px solid {BORDER}; border-radius: 10px; }}"
                f"QFrame QLabel {{ background: transparent; border: none; }}")

            b_layout = QVBoxLayout(block)
            b_layout.setContentsMargins(14, 12, 14, 12)
            b_layout.setSpacing(8)

            head = QHBoxLayout()
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setFont(FONT_LABEL)
            cb.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.setToolTip(self.tr_(meta["hint_key"], ""))
            cb.setStyleSheet(
                f"QCheckBox {{ color: {TEXT}; spacing: 8px; background: transparent; }}"
                f"QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px;"
                f"  border: 1px solid {BORDER_M}; background: {SURF1}; }}"
                f"QCheckBox::indicator:checked {{ background-color: {GREEN}; border-color: {GREEN}; }}"
            )
            self._review_include[key] = cb
            head.addWidget(cb)
            head.addStretch()

            regen_btn = QPushButton(self.tr_("ai_asst_btn_regen", "🔄 Regenerate"))
            regen_btn.setAutoDefault(False)
            regen_btn.setDefault(False)
            regen_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            regen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            regen_btn.setFont(FONT_SUB)
            regen_btn.setToolTip(self.tr_("ai_asst_btn_regen_tooltip",
                "Regenerate only this field, keeping the others as approved context."))
            regen_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {ACC_BRT}; border: none; padding: 0 4px; }}"
                f"QPushButton:hover {{ color: {TEXT}; }}"
            )
            regen_btn.clicked.connect(lambda _=False, k=key: self._on_regenerate_field(k))
            head.addWidget(regen_btn)
            b_layout.addLayout(head)

            text_edit = AutoTextEdit(min_h=60, max_h=220)
            text_edit.setPlainText(value)
            text_edit.setStyleSheet(INPUT_STYLE)
            self._review_widgets[key] = text_edit
            b_layout.addWidget(text_edit)

            self.review_fields_host.addWidget(block)

        self.review_card.show()
        self.btn_apply.show()

    @asyncSlot(str)
    async def _on_regenerate_field(self, field_key: str):
        messages = self._build_refine_prompt(field_key)
        await self._run_generation(messages, [field_key], target=field_key)

    def _on_apply_clicked(self):
        result = {}
        for key, cb in self._review_include.items():
            if cb.isChecked():
                result[key] = self._review_widgets[key].toPlainText().strip()

        if not result:
            return

        self.character_generated.emit(result, self._apply_mode)
        self.accept()
