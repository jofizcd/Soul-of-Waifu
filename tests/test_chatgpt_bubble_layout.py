"""Exercise message/composer geometry with real Qt and synthetic text only."""
import ast
import asyncio
import os
from pathlib import Path
import re
from types import MethodType, SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6 import QtCore, QtGui, QtTest, QtWidgets


def load_layout_methods():
    root = Path(__file__).parents[1]
    scope = {**vars(QtWidgets), **vars(QtGui), "QtCore": QtCore, "QtGui": QtGui,
             "QtWidgets": QtWidgets, "Qt": QtCore.Qt, "asyncio": asyncio, "re": re,
             "uuid": uuid, "os": os, "logger": Mock(),
             "QPropertyAnimation": QtCore.QPropertyAnimation, "QEasingCurve": QtCore.QEasingCurve}
    path = root / "app/gui/custom_widgets.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    frame = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SmoothMessageFrame")
    exec(compile(ast.Module(body=[frame], type_ignores=[]), str(path), "exec"), scope)
    path = root / "app/gui/interface_signals.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "InterfaceSignals")
    methods = [n for n in owner.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in {"add_message", "get_chat_appearance", "_adjust_frame_height"}]
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), "exec"), scope)
    return scope


class ChatBubbleLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.scope = load_layout_methods()

    def setUp(self):
        self.window = QtWidgets.QWidget()
        self.window.resize(900, 450)
        outer = QtWidgets.QVBoxLayout(self.window)
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll)
        self.chat = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(self.chat)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scroll.setWidget(self.chat)
        full = QtWidgets.QFrame()
        composer_layout = QtWidgets.QVBoxLayout(full)
        composer_layout.setContentsMargins(0, 0, 0, 0)
        composer = QtWidgets.QFrame()
        editor_layout = QtWidgets.QVBoxLayout(composer)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor = QtWidgets.QTextEdit()
        editor_layout.addWidget(editor)
        composer_layout.addWidget(composer)
        outer.addWidget(full)
        full.setFixedHeight(40)
        composer.setFixedHeight(40)
        char = {"conversation_method": "ChatGPT", "character_avatar": "",
                "selected_persona": None, "current_chat": "default",
                "chats": {"default": {"chat_content": {}}}}
        self.owner = SimpleNamespace(
            configuration_characters=SimpleNamespace(load_configuration=lambda: {"character_list": {"Test": char}}),
            configuration_settings=SimpleNamespace(get_user_data=lambda k: {}, get_main_setting=lambda k: None),
            messages={}, message_order=[], user_avatar="", chat_container=layout, main_window=self.window,
            ui=SimpleNamespace(scrollArea_chat=self.scroll, textEdit_write_user_message=editor,
                               frame_send_message=composer, frame_send_message_full=full),
            get_last_character_message_index=lambda c: None, get_current_variant_index=lambda n: -1,
            _wire_thinking_toggle=lambda label, text, *args: label.setText(text))
        for name in ("add_message", "get_chat_appearance", "_adjust_frame_height"):
            setattr(self.owner, name, MethodType(self.scope[name], self.owner))
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def add_before_layout(self, text):
        pending = self.owner.add_message("Test", text, True, None, defer_layout=True)
        try:
            with self.assertRaises(StopIteration) as finished:
                pending.send(None)
            return finished.exception.value
        finally:
            pending.close()

    def test_deferred_add_initializes_text_without_yielding_an_empty_bubble(self):
        text = "A complete message before the first layout pass. " * 20
        result = self.add_before_layout(text)
        self.assertEqual(result["label"].text(), text)
        self.assertEqual(self.owner.messages[result["message_id"]]["text"], text)
        self.app.processEvents()
        self.app.processEvents()
        geometry = result["frame"].geometry()
        self.assertGreater(result["label"].height(), 30)
        QtTest.QTest.qWait(120)
        self.assertEqual(result["frame"].geometry(), geometry)

    def test_send_clear_stops_typing_resize_and_keeps_composer_geometry_stable(self):
        ui = self.owner.ui
        ui.textEdit_write_user_message.setPlainText("A multi-line draft\n" * 8)
        self.owner._adjust_frame_height()
        self.assertEqual(self.owner._resize_animation_group.state(), QtCore.QAbstractAnimation.State.Running)
        QtTest.QTest.qWait(20)
        self.owner._chat_send_layout = True
        ui.textEdit_write_user_message.clear()
        self.owner._adjust_frame_height()
        self.owner._chat_send_layout = False
        self.assertEqual(self.owner._resize_animation_group.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.app.processEvents()
        initial = (ui.frame_send_message.height(), ui.frame_send_message_full.height(), self.scroll.height())
        QtTest.QTest.qWait(140)
        self.assertEqual((ui.frame_send_message.height(), ui.frame_send_message_full.height(), self.scroll.height()), initial)
        self.assertEqual(ui.frame_send_message.minimumHeight(), ui.frame_send_message.maximumHeight())

    def test_normal_typing_still_uses_resize_animation(self):
        self.owner.ui.textEdit_write_user_message.setPlainText("A multi-line draft\n" * 8)
        self.owner._adjust_frame_height()
        self.assertEqual(self.owner._resize_animation_group.state(), QtCore.QAbstractAnimation.State.Running)
        QtTest.QTest.qWait(140)
        self.assertGreater(self.owner.ui.frame_send_message.height(), 40)


if __name__ == "__main__":
    unittest.main()
